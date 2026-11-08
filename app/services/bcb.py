from __future__ import annotations

import asyncio
import datetime as dt
import logging
import time
from typing import Any

import httpx
from lxml import etree

from app.config import BCB_ENDPOINT, BCB_REST_FALLBACK, SERIES_BCB, TTL_BCB
from app.services import monitor
from app.services.cache import CACHE

_log = logging.getLogger("radar.bcb")

NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_SER = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
NS_SOAPENC = "http://schemas.xmlsoap.org/soap/encoding/"
NS_XSD = "http://www.w3.org/2001/XMLSchema"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

_soap_ok: bool | None = None

def _estilizar_xml(xml: str) -> str:

    try:
        return etree.tostring(etree.fromstring(xml), pretty_print=True).decode()
    except Exception:
        return xml

def _cabecalho(metodo: str, corpo: str) -> str:
    return (
        '<soapenv:Envelope '
        f'xmlns:soapenv="{NS_SOAPENV}" xmlns:ser="{NS_SER}" '
        f'xmlns:soapenc="{NS_SOAPENC}" xmlns:xsd="{NS_XSD}" xmlns:xsi="{NS_XSI}">'
        f'<soapenv:Body><ser:{metodo} soapenv:encodingStyle="{NS_SOAPENC}">'
        f"{corpo}</ser:{metodo}></soapenv:Body></soapenv:Envelope>"
    )

async def _chamar(metodo: str, corpo: str) -> tuple[Any, Any]:

    envelope = _cabecalho(metodo, corpo)
    enviado = _estilizar_xml(envelope)
    ini = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=45.0) as cli:
            resp = await cli.post(
                BCB_ENDPOINT,
                content=envelope,
                headers={"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": metodo},
            )
        duracao = (time.perf_counter() - ini) * 1000
        raiz = etree.fromstring(resp.content)
    except (httpx.HTTPError, etree.XMLSyntaxError) as erro:
        status = getattr(getattr(erro, "response", None), "status_code", None)
        monitor.registrar(
            "SOAP", metodo,
            status=f"HTTP {status} · falha de rede/leitura" if status
                   else f"erro · {type(erro).__name__}",
            duracao_ms=(time.perf_counter() - ini) * 1000,
            enviado=enviado, recebido=str(erro),
        )
        raise
    recebido = _estilizar_xml(etree.tostring(raiz, pretty_print=True).decode())
    falha = raiz.find(f".//{{{NS_SOAPENV}}}Fault")
    if falha is not None:
        monitor.registrar(
            "SOAP", metodo,
            status=f"HTTP {resp.status_code} · Fault",
            duracao_ms=duracao,
            enviado=enviado, recebido=recebido,
        )
        raise RuntimeError(f"SOAP Fault: {''.join(falha.itertext())[:200]}")
    resposta = raiz.find(f".//{{{NS_SER}}}{metodo}Response")
    if resposta is None:
        monitor.registrar(
            "SOAP", metodo,
            status=f"HTTP {resp.status_code} · sem Response",
            duracao_ms=duracao, enviado=enviado, recebido=recebido,
        )
        raise RuntimeError(f"Resposta SOAP sem {metodo}Response")
    monitor.registrar(
        "SOAP", metodo,
        status=f"HTTP {resp.status_code}",
        duracao_ms=duracao, enviado=enviado, recebido=recebido,
    )
    return raiz, resposta

def _montar_mapa(raiz: Any) -> dict[str, Any]:
    return {mr.get("id", ""): mr for mr in raiz.iter("multiRef")}

def _alvo(e: Any, refs: dict[str, Any], vistos: frozenset = frozenset()) -> Any:

    xsi = (e.get(f"{{{NS_XSI}}}type") or "")
    nome_tipo = xsi.rsplit(":", 1)[-1]
    texto = (e.text or "").strip()

    escalares = {"decimal", "int", "long", "string", "boolean",
                 "float", "double", "integer", "short"}
    if texto and (xsi.startswith("xsd:") or nome_tipo in escalares):
        return texto

    filhos = list(e)
    todos_item = bool(filhos) and all(
        etree.QName(c).localname == "item" for c in filhos
    )
    if "Array" in xsi or todos_item:
        saida: list[Any] = []
        for ch in filhos:
            href = ch.get("href")
            if href:
                rid = href[1:]
                alvo = refs.get(rid)
                saida.append(
                    None if (alvo is None or rid in vistos)
                    else _alvo(alvo, refs, vistos | {rid})
                )
            else:
                saida.append(_alvo(ch, refs, vistos))
        return saida

    if not filhos:
        return texto or None

    registro: dict[str, Any] = {}
    for ch in filhos:
        tag = etree.QName(ch).localname
        href = ch.get("href")
        if href:
            rid = href[1:]
            alvo = refs.get(rid)
            registro[tag] = (
                None if (alvo is None or rid in vistos)
                else _alvo(alvo, refs, vistos | {rid})
            )
        elif ch.get(f"{{{NS_XSI}}}nil") == "true":
            registro[tag] = None
        else:

            registro[tag] = _alvo(ch, refs, vistos)
    return registro

def _retorna(raiz: Any, resposta: Any, nome: str) -> Any:
    refs = _montar_mapa(raiz)
    for ch in resposta:
        if etree.QName(ch).localname == nome:
            href = ch.get("href")
            alvo = refs.get(href[1:]) if href else ch
            return _alvo(alvo, refs) if alvo is not None else None
    return None

def _ponto(vo: Any) -> dict[str, Any] | None:
    try:
        return {
            "data": dt.date(int(vo["ano"]), int(vo["mes"]), int(vo["dia"])).isoformat(),
            "valor": float(str(vo["valor"]).replace(",", ".")),
        }
    except (KeyError, TypeError, ValueError):
        return None

async def _ultimo(serie: int) -> dict[str, Any]:
    raiz, resposta = await _chamar(
        "getUltimoValorVO", f'<in0 xsi:type="xsd:long">{serie}</in0>'
    )
    vo = _retorna(raiz, resposta, "getUltimoValorVOReturn")
    if not isinstance(vo, dict):
        return {}
    uv = vo.get("ultimoValor")
    if not isinstance(uv, dict):
        return {}
    p = _ponto(uv)
    return p or {}

async def _series_vo(codigos: list[int], inicio: dt.date, fim: dt.date) -> list[list[dict[str, Any]]]:
    itens = "".join(f"<item>{c}</item>" for c in codigos)
    corpo = (
        f'<in0 xsi:type="soapenc:Array" soapenc:arrayType="xsd:long[{len(codigos)}]">{itens}</in0>'
        f'<in1 xsi:type="soapenc:string">{inicio:%d/%m/%Y}</in1>'
        f'<in2 xsi:type="soapenc:string">{fim:%d/%m/%Y}</in2>'
    )
    try:
        raiz, resposta = await _chamar("getValoresSeriesVO", corpo)
    except RuntimeError as erro:
        if "Value(s) not found" in str(erro):
            return [[] for _ in codigos]
        raise
    ret = _retorna(raiz, resposta, "getValoresSeriesVOReturn")
    lista = ret if isinstance(ret, list) else []
    saida: list[list[dict[str, Any]]] = []
    for vo in lista:
        valores = vo.get("valores") if isinstance(vo, dict) else None
        pontos = [p for p in (_ponto(v) for v in (valores or [])) if p]
        pontos.sort(key=lambda p: p["data"])
        saida.append(pontos)
    return saida

async def status() -> bool:

    global _soap_ok
    if _soap_ok is None:
        try:
            _soap_ok = (await _ultimo(SERIES_BCB["ipca"])).get("valor") is not None
            if _soap_ok:
                _log.info("SOAP FachadaWSSGS operacional")
        except Exception as erro:
            _soap_ok = False
            _log.warning("SOAP indisponível; reserva REST acionada: %s", erro)
    return _soap_ok

async def serie_sgs(serie: int, inicio: dt.date, fim: dt.date) -> dict[str, Any]:

    fonte = "SOAP"
    dados: list[dict[str, Any]] = []
    try:
        blocos = await _series_vo([serie], inicio, fim)
        dados = blocos[0] if blocos else []
    except Exception as erro:
        _log.warning("SOAP falhou para série %s: %s", serie, erro)
    if not dados:
        try:
            reservas = await _serie_rest(serie, inicio, fim)
            if reservas:
                fonte = "REST"
                dados = reservas
        except httpx.HTTPStatusError as erro:
            _log.info("REST também sem dados para série %s (%s)", serie, erro.response.status_code)
    return {"serie": serie, "fonte": fonte, "pontos": dados}

async def _serie_rest(serie: int, inicio: dt.date, fim: dt.date) -> list[dict[str, Any]]:

    url = BCB_REST_FALLBACK.format(serie=serie)
    tudo: dict[str, float] = {}
    cursor = inicio
    async with httpx.AsyncClient(timeout=30.0) as cli:
        while cursor <= fim:
            trecho = min(dt.timedelta(days=2909), fim - cursor)
            fim_bloco = cursor + trecho
            resp = await cli.get(url, params={
                "formato": "json",
                "dataInicial": f"{cursor:%d/%m/%Y}",
                "dataFinal": f"{fim_bloco:%d/%m/%Y}",
            })
            resp.raise_for_status()
            for p in resp.json():
                d, m, a = p["data"].split("/")
                tudo[f"{a}-{m}-{d}"] = float(p["valor"])
            cursor = fim_bloco + dt.timedelta(days=1)
    return [{"data": k, "valor": v} for k, v in sorted(tudo.items())]

async def contexto_financeiro(anos: int = 10) -> dict[str, Any]:

    hoje = dt.date.today()
    inicio_longo = hoje.replace(year=hoje.year - anos)
    inicio_recente = hoje.replace(year=hoje.year - 1)

    alcance = {
        "ipca": inicio_longo,
        "ipca_12m": inicio_recente,
        "selic": inicio_recente,
        "cambio": inicio_recente,
        "inadimplencia_pj": inicio_longo,
        "juros_giro": inicio_longo,
    }

    async def _obter(nome: str, cod: int) -> tuple[str, dict[str, Any]]:
        ini = alcance.get(nome, inicio_recente)
        ttl = TTL_BCB
        res = await CACHE.get_or_set(
            f"bcb:{nome}:{ini.year}", ttl,
            lambda: serie_sgs(cod, ini, hoje),
        )
        return nome, res

    tarefas = [_obter(nome, cod) for nome, cod in SERIES_BCB.items()]
    pares = await asyncio.gather(*tarefas)
    return dict(pares)
