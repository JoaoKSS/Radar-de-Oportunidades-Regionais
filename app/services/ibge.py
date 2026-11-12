from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.services import geo, monitor

from app.config import (
    SIDRA_MUNICIPIOS_CATALOGO,
    UF_NOMES,
    UF_CODIGOS,
    SIDRA_URL,
    SIDRA_URL_S_PERIODO,
    TAB_POPULACAO,
    TAB_PIB,
    TAB_EMPRESAS,
    TAB_AREA,
    VAR_POPULACAO,
    VAR_PIB,
    VAR_PIB_PART_UF,
    VAR_PIB_PART_BR,
    VAR_AREA,
    VARS_VAB_SETORIAL,
    TTL_LOCALIDADES,
    TTL_SIDRA,
)
from app.services.cache import CACHE

_client: httpx.AsyncClient | None = None

def http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            headers={"User-Agent": "radar-oportunidades/1.0"},
        )
    return _client

def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()

def _rotulo_url(url: str) -> str:
    p = urlsplit(url)
    rotulo = p.netloc + p.path + (f"?{p.query}" if p.query else "")
    return rotulo if len(rotulo) <= 72 else rotulo[:69] + "…"

def _pedido_legivel(url: str) -> str:
    p = urlsplit(url)
    alvo = p.path + (f"?{p.query}" if p.query else "")
    return f"GET {alvo}\nHost: {p.netloc}"

def _resumo_json(texto: str) -> str:
    try:
        dados = json.loads(texto)
        return json.dumps(dados, ensure_ascii=False, indent=2)
    except (ValueError, TypeError):
        return texto

async def _consulta(url: str) -> httpx.Response:

    ini = time.perf_counter()
    try:
        resp = await http().get(url)
        resp.raise_for_status()
        monitor.registrar(
            "REST", _rotulo_url(url),
            status=f"HTTP {resp.status_code}",
            duracao_ms=(time.perf_counter() - ini) * 1000,
            enviado=_pedido_legivel(url),
            recebido=_resumo_json(resp.text),
            url=url,
        )
        return resp
    except httpx.HTTPError as erro:
        status_http = getattr(getattr(erro, "response", None), "status_code", None)
        monitor.registrar(
            "REST", _rotulo_url(url),
            status=f"HTTP {status_http} · erro" if status_http
                   else f"erro de rede · {type(erro).__name__}",
            duracao_ms=(time.perf_counter() - ini) * 1000,
            enviado=_pedido_legivel(url), recebido=str(erro),
            url=url,
        )
        raise

_UF_SIGLA_PARA_ID = {sigla: int(cod) for cod, sigla in UF_CODIGOS.items()}

async def lista_municipios() -> list[dict[str, Any]]:

    async def _baixar() -> list[dict[str, Any]]:
        resp = await _consulta(SIDRA_MUNICIPIOS_CATALOGO)
        linhas = resp.json()
        saida = []
        for r in linhas[1:]:
            d1c = r.get("D1C")
            d1n = r.get("D1N", "")
            if not d1c or not str(d1c).isdigit():
                continue
            m = re.search(r"^(.*?)\s*[-–(]\s*([A-Z]{2})\)?$", d1n)
            if not m:
                continue
            nome = m.group(1).strip()
            uf_sigla = m.group(2).strip()
            uf_id = _UF_SIGLA_PARA_ID.get(uf_sigla)
            uf_info = UF_NOMES.get(uf_sigla, (uf_sigla, "Brasil"))
            saida.append({
                "id": int(d1c),
                "nome": nome,
                "uf": uf_sigla,
                "uf_id": uf_id,
                "uf_nome": uf_info[0],
                "regiao": uf_info[1],
            })
        return saida

    return await CACHE.get_or_set("ibge:municipios", TTL_LOCALIDADES, _baixar)

async def busca_municipios(q: str, limite: int = 10) -> list[dict[str, Any]]:
    if not q or not q.strip():
        return []
    qf = _normalizar(q)
    munis = await lista_municipios()
    prefixo, contendo = [], []
    for m in munis:
        n = _normalizar(m["nome"])
        if n.startswith(qf):
            prefixo.append(m)
        elif qf in n:
            contendo.append(m)
    return (prefixo + contendo)[:limite]

async def municipio_por_id(id_municipio: int) -> dict[str, Any] | None:
    for m in await lista_municipios():
        if m["id"] == id_municipio:
            return m
    return None

def _num(v: Any) -> float | None:
    if v is None:
        return None
    v = str(v).replace("..", "").replace("...", "").strip()
    if not v or v.startswith("X"):
        return None
    try:
        return float(v)
    except ValueError:
        return None

def mapear_dimensoes(header: dict[str, str]) -> dict[str, str | None]:

    col: dict[str, str | None] = {"mun": None, "ano": None, "var": None}
    for chave, rotulo in header.items():
        if not chave.endswith("N") or chave in ("NC", "NN", "MC", "MN"):
            continue
        r = rotulo.lower()
        if r == "variável":
            col["var"] = chave
        elif r == "ano":
            col["ano"] = chave
        elif r.startswith("município"):
            col["mun"] = chave
    return col

def serie_por_ano(header: dict[str, str], linhas: list[dict[str, str]], var_prefixo: str) -> dict[int, float]:

    dim = mapear_dimensoes(header)
    var_col, ano_col = dim["var"], dim["ano"]
    saida: dict[int, float] = {}
    for r in linhas:
        if var_col is None or ano_col is None:
            continue
        nome = r.get(var_col, "")
        if isinstance(nome, str) and nome.startswith(var_prefixo[:40]):
            ano = _num(r.get(ano_col))
            val = _num(r.get("V"))
            if ano is not None and val is not None:
                saida[int(ano)] = val
    return dict(sorted(saida.items()))

async def sidra(tabela: int, ids: Any, var: str = "all", periodo: str = "") -> tuple[dict[str, str], list[dict[str, str]]]:

    template = SIDRA_URL if periodo else SIDRA_URL_S_PERIODO
    if isinstance(ids, (list, tuple)):
        ids = ",".join(str(i) for i in ids)
    url = template.format(tabela=tabela, ids=ids, vars_=var, periodos=periodo)
    resp = await _consulta(url)
    dados = resp.json()
    if not isinstance(dados, list) or len(dados) < 2:
        return {}, []
    return dados[0], dados[1:]

async def malha_brasil() -> dict[str, Any]:
    return geo.carregar_malha_brasil()

async def centro_municipio(id_mun: int) -> dict[str, float] | None:
    return geo.obter_coordenada_municipio(id_mun)

async def metadados_territoriais(id_mun: int) -> dict[str, Any]:

    async def _baixar() -> dict[str, Any]:
        try:
            _, linhas = await sidra(TAB_AREA, id_mun, var=str(VAR_AREA), periodo="last")
            if linhas:
                val = _num(linhas[0].get("V"))
                if val:
                    return {"area_km2": val, "unidade": "km2"}
        except Exception:
            pass

        return {"area_km2": None, "unidade": "km2"}

    return await CACHE.get_or_set(f"ibge:meta-territorio:{id_mun}", TTL_LOCALIDADES, _baixar)

async def serie_populacao(id_mun: int) -> dict[int, float]:
    header, linhas = await sidra(TAB_POPULACAO, id_mun, var=str(VAR_POPULACAO), periodo="all")
    return serie_por_ano(header, linhas, "População residente estimada")

async def serie_pib(id_mun: int) -> dict[int, float]:
    header, linhas = await sidra(TAB_PIB, id_mun, var=str(VAR_PIB), periodo="all")
    return serie_por_ano(header, linhas, "Produto Interno Bruto a preços correntes")

async def composicao_setorial_pib(id_mun: int) -> dict[str, Any]:

    async def _baixar() -> dict[str, Any]:
        vars_str = ",".join(VARS_VAB_SETORIAL.values())
        header, linhas = await sidra(TAB_PIB, id_mun, var=vars_str, periodo="all")
        dim = mapear_dimensoes(header)
        ano_col = dim.get("ano")
        var_col = dim.get("var")

        anos_map: dict[int, dict[str, float]] = {}
        var_inv = {v: k for k, v in VARS_VAB_SETORIAL.items()}

        for r in linhas:
            val = _num(r.get("V"))
            ano_val = _num(r.get(ano_col)) if ano_col else None
            var_code = r.get("D3C") or r.get("D2C") or r.get(var_col)

            chave = var_inv.get(str(var_code))
            if not chave and var_col:
                v_nome = str(r.get(var_col, "")).lower()
                if "agropecu" in v_nome:
                    chave = "agro"
                elif "indústria" in v_nome:
                    chave = "industria"
                elif "exclusive administração" in v_nome:
                    chave = "servicos"
                elif "administração" in v_nome:
                    chave = "admin"

            if val is not None and ano_val and chave:
                ano_int = int(ano_val)
                anos_map.setdefault(ano_int, {})[chave] = val

        anos_validos = sorted([a for a, s in anos_map.items() if len(s) >= 3])
        if not anos_validos:
            return {"ano": None, "setores": {}}
        ultimo_ano = anos_validos[-1]
        setores = anos_map[ultimo_ano]
        total = sum(setores.values())
        pcts = {k: (v / total * 100 if total > 0 else 0) for k, v in setores.items()}

        return {
            "ano": ultimo_ano,
            "valores_mil": setores,
            "total_vab_mil": total,
            "participacao_pct": pcts,
        }

    return await CACHE.get_or_set(f"sidra:vab-setorial:{id_mun}", TTL_SIDRA, _baixar)

async def indicadores_empresas(id_mun: int) -> dict[str, Any]:

    async def _baixar() -> dict[str, Any]:
        header, linhas = await sidra(TAB_EMPRESAS, id_mun, var="all", periodo="last")
        dim = mapear_dimensoes(header)
        var_col = dim["var"]
        col_cnae = next(
            (k for k, v in header.items()
             if k.endswith("N") and isinstance(v, str) and v.startswith("Classificação Nacional")),
            None,
        )
        caso: dict[str, Any] = {
            "empresas": None, "empregos": None,
            "assalariados": None, "salarios": None, "ano": None,
        }
        mapeia = {
            "Número de empresas e outras organizações": "empresas",
            "Pessoal ocupado total": "empregos",
            "Pessoal ocupado assalariado": "assalariados",
            "Salários e outras remunerações": "salarios",
        }
        if var_col is None:
            return caso
        for r in linhas:
            if col_cnae and str(r.get(col_cnae, "")).lower() != "total":
                continue
            nome = r.get(var_col, "")
            key = mapeia.get(nome if isinstance(nome, str) else "")
            if key is None:
                continue
            val = _num(r.get("V"))
            ano_val = _num(r.get(dim["ano"])) if dim["ano"] else None
            if val is not None:
                caso[key] = val
                caso["ano"] = int(ano_val) if ano_val else None
        return caso

    return await CACHE.get_or_set(f"sidra:empresas:{id_mun}", TTL_SIDRA, _baixar)

async def centros_uf(uf_id: str | int) -> dict[int, dict[str, float]]:
    return geo.obter_coordenadas_uf(uf_id)

async def pib_municipios_uf(uf: str, ano: str = "2023") -> dict[int, float]:

    async def _baixar() -> dict[int, float]:
        cod_uf = next((k for k, v in UF_CODIGOS.items() if v == uf), None)
        if cod_uf:
            url = f"https://apisidra.ibge.gov.br/values/t/{TAB_PIB}/n6/in%20n3%20{cod_uf}/v/{VAR_PIB}/p/{ano}?formato=json"
            try:
                resp = await _consulta(url)
                dados = resp.json()
                if isinstance(dados, list) and len(dados) > 1:
                    valores: dict[int, float] = {}
                    for r in dados[1:]:
                        val = _num(r.get("V"))
                        idc = r.get("D1C")
                        if val is not None and idc and str(idc).isdigit():
                            valores[int(idc)] = val
                    if valores:
                        return valores
            except Exception:
                pass

        munis = [m["id"] for m in await lista_municipios() if m["uf"] == uf]
        passada = 100
        lotes = [munis[i:i + passada] for i in range(0, len(munis), passada)]

        tarefas = [sidra(TAB_PIB, lote, var=str(VAR_PIB), periodo=ano) for lote in lotes]
        respostas = await asyncio.gather(*tarefas)

        valores: dict[int, float] = {}
        for _, linhas in respostas:
            for r in linhas:
                val = _num(r.get("V"))
                idc = r.get("D1C")
                if val is not None and idc and str(idc).isdigit():
                    valores[int(idc)] = val
        return valores

    return await CACHE.get_or_set(f"sidra:pib-uf:{uf}:{ano}", TTL_SIDRA, _baixar)

async def pib_rank_uf(id_mun: int, uf: str, ano: str = "2023") -> tuple[int | None, int | None]:

    valores = await pib_municipios_uf(uf, ano)
    if id_mun not in valores or not valores:
        return (None, None)
    ordenado = sorted(valores.values(), reverse=True)
    return (ordenado.index(valores[id_mun]) + 1, len(valores))

async def participacao_pib(id_mun: int) -> dict[str, Any]:

    async def _baixar() -> dict[str, Any]:
        vars_str = f"{VAR_PIB_PART_UF},{VAR_PIB_PART_BR}"
        header, linhas = await sidra(TAB_PIB, id_mun, var=vars_str, periodo="last")
        dim = mapear_dimensoes(header)
        ano_col = dim.get("ano")
        var_col = dim.get("var")

        resultado: dict[str, Any] = {
            "ano": None,
            "part_uf": None,
            "part_br": None,
        }

        for r in linhas:
            val = _num(r.get("V"))
            ano_val = _num(r.get(ano_col)) if ano_col else None
            var_code = str(r.get("D2C") or r.get("D3C") or r.get(var_col, ""))
            var_nome = str(r.get(var_col, "")).lower()

            if ano_val:
                resultado["ano"] = int(ano_val)

            if val is not None:
                if str(VAR_PIB_PART_UF) in var_code or "unidade da federação" in var_nome:
                    resultado["part_uf"] = val
                elif str(VAR_PIB_PART_BR) in var_code or "brasil" in var_nome:
                    resultado["part_br"] = val

        return resultado

    return await CACHE.get_or_set(f"sidra:pib-participacao:{id_mun}", TTL_SIDRA, _baixar)
