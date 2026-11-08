"""Radar de Oportunidades Regionais — servidor FastAPI.

REST  (IBGE)  → território, população, PIB, empresas (SIDRA).
SOAP  (BCB)   → IPCA, Selic, câmbio (FachadaWSSGS via zeep).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analysis.painel import dados_comparador, dados_municipio
from app.services import bcb, ibge, monitor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("radar.main")


async def _aquecer_cache():
    """Pré-aquecimento assíncrono em segundo plano dos dados gerais e cidades em destaque."""
    await asyncio.sleep(0.5)  # Breve pausa para o uvicorn subir 100%
    try:
        _log.info("Pré-aquecendo catálogo de municípios e contexto financeiro...")
        await asyncio.gather(
            ibge.lista_municipios(),
            bcb.contexto_financeiro(anos=26),
            return_exceptions=True,
        )
        _log.info("Aquecendo cidades em destaque da página inicial...")
        for id_mun, nome, uf in ATALHOS:
            try:
                await dados_municipio(id_mun)
                _log.info(f"Cache pronto: {nome} ({uf})")
            except Exception as erro:
                _log.warning(f"Falha ao pré-aquecer {nome}: {erro}")
        _log.info("Pré-aquecimento concluído: todas as cidades em destaque já estão em memória.")
    except Exception as erro:
        _log.warning(f"Erro no pré-aquecimento geral: {erro}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dispara a tarefa em background sem segurar a subida do servidor
    tarefa = asyncio.create_task(_aquecer_cache())
    yield
    tarefa.cancel()


class StaticFilesComCache(StaticFiles):
    """Serve arquivos estáticos com cabeçalho de cache agressivo (7 dias)."""
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        # 7 dias de cache no cliente para CSS, JS e imagens
        response.headers["Cache-Control"] = "public, max-age=604800, immutable"
        return response


app = FastAPI(
    title="Radar de Oportunidades Regionais",
    docs_url=None, redoc_url=None, openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
_AQUI = Path(__file__).resolve().parent
app.mount("/static", StaticFilesComCache(directory=_AQUI / "ui" / "static"), name="static")
templates = Jinja2Templates(directory=_AQUI / "ui" / "templates")
templates.env.globals["ano_atual"] = lambda: dt.date.today().year

# Municípios de atalho da página inicial
ATALHOS = [
    (3143302, "Montes Claros", "MG"),
    (3550308, "São Paulo", "SP"), (3304557, "Rio de Janeiro", "RJ"),
    (3106200, "Belo Horizonte", "MG"), (4106902, "Curitiba", "PR"),
    (2611606, "Recife", "PE"), (2304400, "Fortaleza", "CE"),
    (1302603, "Manaus", "AM"),
]

# ------------------------------------------------------------------
# Formatação pt-BR nos templates
# ------------------------------------------------------------------

def _presente(v: Any) -> bool:
    return v is not None

def _sep(valor: float, dec: int) -> str:
    return (
        f"{valor:,.{dec}f}"
        .replace(",", "\u00b7")
        .replace(".", ",")
        .replace("\u00b7", ".")
    )

def _fmt_num(v: Any, dec: int = 0) -> str:
    if not _presente(v):
        return "—"
    try:
        return _sep(float(v), dec)
    except (ValueError, TypeError, OverflowError):
        return "—"

def _fmt_pib(v: Any) -> str:
    """v em mil de reais (SIDRA) → 'R$ 418,5 bi' / 'R$ 312 mi'."""
    if not _presente(v):
        return "—"
    reais = float(v) * 1000
    if abs(reais) >= 1e9:
        return f"R$ {_sep(reais / 1e9, 1)} bi"
    if abs(reais) >= 1e6:
        return f"R$ {_sep(reais / 1e6, 0)} mi"
    return f"R$ {_sep(reais, 0)}"

def _fmt_pct(v: Any, com_sinal: bool = True) -> str:
    if not _presente(v):
        return "—"
    s = _sep(abs(float(v)) * 100, 1)
    if com_sinal:
        s = ("+" if float(v) >= 0 else "−") + s
    return s + "%"

templates.env.filters["num"] = _fmt_num
templates.env.filters["pib"] = _fmt_pib
templates.env.filters["pct"] = _fmt_pct

def _render(request: Request, nome: str, ctx: dict[str, Any], status: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, nome, ctx, status_code=status)

# ------------------------------------------------------------------
# Página inicial
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def pagina_inicial(request: Request) -> HTMLResponse:
    return _render(request, "index.html", {"atalhos": ATALHOS})

# ------------------------------------------------------------------
# APIs de suporte (autocomplete e diagnóstico)
# ------------------------------------------------------------------

@app.get("/api/localidades")
async def api_localidades(q: str = Query("")) -> JSONResponse:
    return JSONResponse(await ibge.busca_municipios(q, limite=10))

@app.get("/api/diagnostico")
async def api_diagnostico() -> JSONResponse:
    """Observabilidade das integrações: o SOAP do BCB está vivo?"""
    return JSONResponse({
        "bcb_soap": await bcb.status(),
        "bcb_reserva_rest": True,
        "ibge_rest": True,
    })

@app.get("/health")
async def health() -> JSONResponse:
    """Alias simples do diagnóstico (polling de monitoramento)."""
    return await api_diagnostico()

@app.get("/api/malha/brasil")
async def api_malha_brasil() -> JSONResponse:
    """GeoJSON oficial do Brasil por UF (IBGE Malhas) — para o mapa ECharts."""
    return JSONResponse(await ibge.malha_brasil())

@app.get("/api/monitor")
async def api_monitor() -> JSONResponse:
    """Inspecionar integrações: as últimas requisições REST/SOAP registradas."""
    return JSONResponse({"eventos": monitor.ultimos()})

# ------------------------------------------------------------------
# Painel do município
# ------------------------------------------------------------------

def _grafia_data(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if len(iso) == 10 else ""

def _contexto_resumo(contexto: dict[str, Any]) -> list[dict[str, str]]:
    """Mini-cards nacionais alimentados pelo SOAP do BCB."""
    saida: list[dict[str, str]] = []
    rotulos = {
        "ipca_12m":         ("IPCA 12 meses · BCB", "pct2"),
        "selic":            ("Meta Selic · BCB", "pct2"),
        "cambio":           ("Câmbio US$ · BCB", "rs"),
        "inadimplencia_pj": ("Inadimplência PJ · BCB", "pct2"),
        "juros_giro":       ("Juros Cap. Giro · BCB", "pct2"),
    }
    for chave, (rotulo, _tipo) in rotulos.items():
        pts = contexto.get(chave, {}).get("pontos") or []
        if not pts:
            continue
        ultimo = pts[-1]
        if chave == "cambio":
            valor = f"US$ 1 = R$ {_sep(ultimo['valor'], 2)}"
        else:
            valor = f"{_sep(ultimo['valor'], 2)}%"
        saida.append({
            "rotulo": rotulo,
            "valor": valor,
            "data": _grafia_data(ultimo.get("data", "")),
        })
    return saida

def _payload_graficos(dados: dict[str, Any]) -> dict[str, Any]:
    """Conjuntos que o ECharts renderiza na página do município."""
    pop = dados["pop_serie"]
    pib_nom = dados["pib_serie"]["nominal"]
    pib_real: dict[int, float] = dict(dados["pib_serie"]["real"])
    ipca = dados["contexto"]["ipca"]["pontos"][-24:]
    ipca12 = dados["contexto"]["ipca_12m"]["pontos"]
    cred_giro = dados["contexto"].get("juros_giro", {}).get("pontos", [])[-24:]
    inad_pj = dados["contexto"].get("inadimplencia_pj", {}).get("pontos", [])[-24:]

    def rotulo(iso: str) -> str:
        return iso[5:7] + "/" + iso[2:4]  # "07/24"

    return {
        "pop": {"anos": [a for a, _ in pop], "valores": [v for _, v in pop]},
        "geo": dados.get("geo"),
        "mapa": dados.get("mapa"),
        "nome": dados["info"]["nome"],
        "uf": dados["info"]["uf"],
        "pib": {
            "anos": [a for a, _ in pib_nom],
            "nominal": [v for _, v in pib_nom],
            "real": [pib_real.get(a) for a, _ in pib_nom],
        },
        "ipca": {
            "meses": [rotulo(p["data"]) for p in ipca],
            "variacao": [p["valor"] for p in ipca],
        },
        "ipca12": {
            "meses": [rotulo(p["data"]) for p in ipca12],
            "valores": [p["valor"] for p in ipca12],
        },
        "credito": {
            "meses": [rotulo(p["data"]) for p in cred_giro],
            "juros_giro": [p["valor"] for p in cred_giro],
            "inadimplencia": [p["valor"] for p in inad_pj],
        },
        "vab": dados.get("vab_setorial"),
        "tem_pib_real": len(pib_real) >= 2,
    }

@app.get("/municipio/{id_mun:int}", response_class=HTMLResponse)
async def pagina_municipio(request: Request, id_mun: int) -> HTMLResponse:
    try:
        dados = await dados_municipio(id_mun)
    except KeyError:
        raise HTTPException(404, "Município não encontrado")
    return _render(request, "municipio.html", {
        "dados": dados,
        "payload": json.dumps(_payload_graficos(dados), ensure_ascii=False),
        "contexto": _contexto_resumo(dados["contexto"]),
    })

# ------------------------------------------------------------------
# Comparador de municípios
# ------------------------------------------------------------------

def _valor_em(d: dict[str, Any], *caminho: str) -> Any:
    t: Any = d["indicators"]
    for c in caminho:
        if not isinstance(t, dict):
            return None
        t = t.get(c)
    return t

@app.get("/comparar", response_class=HTMLResponse)
async def pagina_comparar(
    request: Request,
    ids: str = Query("", description="ids separados por vírgula (2 a 4)"),
) -> HTMLResponse:
    lista: list[int] = []
    for bruto in [x for x in ids.split(",") if x.strip()]:
        try:
            iv = int(bruto)
            if iv and iv not in lista:
                lista.append(iv)
        except ValueError:
            continue
    lista = lista[:4]

    chips: list[dict[str, Any]] = []
    for iv in lista:
        muni = await ibge.municipio_por_id(iv)
        chips.append({
            "id": iv,
            "rotulo": f'{muni["nome"]} · {muni["uf"]}' if muni else str(iv),
        })

    cabecalho: list[str] = []
    linhas: list[dict[str, Any]] = []
    graficos: dict[str, Any] = {"labels": [], "pib_pc": [], "cresc_pop": []}

    if len(lista) >= 2:
        per = await dados_comparador(lista)
        cabecalho = [f'{d["info"]["nome"]} · {d["info"]["uf"]}' for d in per]

        def lin(nome: str, fmt: Any, tag: Any = None) -> dict[str, Any]:
            return {"nome": nome,
                    "valores": [(fmt(d), tag(d) if tag else None) for d in per]}

        linhas = [
            lin("População (última estimativa)",
                lambda d: _fmt_num(_valor_em(d, "populacao", "valor"))),
            lin("Crescimento populacional · 5 anos",
                lambda d: _fmt_pct(_valor_em(d, "populacao", "cresc_5a")),
                lambda d: _valor_em(d, "populacao", "tag")),
            lin("PIB municipal (nominal)",
                lambda d: f'{_fmt_pib(_valor_em(d, "pib", "valor"))} '
                          f'({ _valor_em(d, "pib", "ano") or "—"})'),
            lin("Crescimento real do PIB · 5 anos (deflacionado pelo IPCA)",
                lambda d: f'{_fmt_pct(_valor_em(d, "pib", "cresc_real_5a"))} a.a.',
                lambda d: _valor_em(d, "pib", "tag")),
            lin("PIB per capita",
                lambda d: _fmt_pib(_valor_em(d, "pib_pc", "valor"))),
            lin("Salário médio formal (estimado)",
                lambda d: (f'{_fmt_pib(_valor_em(d, "empresas", "salario_medio"))} /mês'
                           if _valor_em(d, "empresas", "salario_medio") else "—")),
            lin("Empresas ativas · CEMPRE",
                lambda d: f'{_fmt_num(_valor_em(d, "empresas", "n"))}'
                          + (f' ({_valor_em(d, "empresas", "ano")})'
                             if _valor_em(d, "empresas", "ano") else "")),
            lin("Empresas por mil habitantes",
                lambda d: _fmt_num(_valor_em(d, "empresas", "por_mil_hab"), 1)),
            lin("Empregados por empresa",
                lambda d: _fmt_num(_valor_em(d, "empresas", "empregos_por_empresa"), 1)),
            lin("Posição do PIB no estado",
                lambda d: (f'{_valor_em(d, "rank", "posicao")}º '
                           f'de {_valor_em(d, "rank", "de")}')
                          if _valor_em(d, "rank", "posicao") else "—"),
            lin("Participação no PIB estadual",
                lambda d: (f'{_valor_em(d, "participacao", "part_uf"):.2f}% da UF'
                           if _valor_em(d, "participacao", "part_uf") is not None else "—")),
            lin("Participação no PIB do Brasil",
                lambda d: (f'{_valor_em(d, "participacao", "part_br"):.2f}% do BR'
                           if _valor_em(d, "participacao", "part_br") is not None else "—")),
        ]
        graficos = {
            "labels": cabecalho,
            "pib_pc": [round(_valor_em(d, "pib_pc", "valor") or 0) for d in per],
            "cresc_pop": [
                round((_valor_em(d, "populacao", "cresc_5a") or 0) * 100, 1) for d in per
            ],
            "vab": [
                {
                    "cidade": cabecalho[idx],
                    "servicos": round(d.get("vab_setorial", {}).get("participacao_pct", {}).get("servicos") or 0, 1),
                    "industria": round(d.get("vab_setorial", {}).get("participacao_pct", {}).get("industria") or 0, 1),
                    "admin": round(d.get("vab_setorial", {}).get("participacao_pct", {}).get("admin") or 0, 1),
                    "agro": round(d.get("vab_setorial", {}).get("participacao_pct", {}).get("agro") or 0, 1),
                }
                for idx, d in enumerate(per)
            ]
        }

    contexto_cards: list[dict[str, str]] = []
    if lista:
        contexto_raw = await bcb.contexto_financeiro()
        contexto_cards = _contexto_resumo(contexto_raw)

    return _render(request, "comparar.html", {
        "tabela": {"cabecalho": cabecalho, "linhas": linhas} if cabecalho else None,
        "graficos": json.dumps(graficos, ensure_ascii=False),
        "chips": chips,
        "ids": lista,
        "contexto": contexto_cards,
    })
