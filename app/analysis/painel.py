"""Monta o objeto completo de cada visão (município / comparador).

Coordena REST (IBGE) e SOAP (BCB) e devolve já com indicadores e insights.
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.services import bcb, ibge
from app.analysis import insights
from app.analysis.indicators import Deflator, painel_indicadores
from app.services.cache import CACHE

TTL_PAINEL = 3600  # 1 h


async def dados_municipio(id_mun: int) -> dict[str, Any]:
    async def _montar() -> dict[str, Any]:
        muni = await ibge.municipio_por_id(id_mun)
        if muni is None:
            raise KeyError(f"Município {id_mun} não encontrado no IBGE")

        contexto = await bcb.contexto_financeiro(anos=26)
        deflator = Deflator(contexto["ipca"]["pontos"])

        pop = await ibge.serie_populacao(id_mun)
        pib = await ibge.serie_pib(id_mun)
        vab_setorial = await ibge.composicao_setorial_pib(id_mun)
        participacao_pib = await ibge.participacao_pib(id_mun)
        empresas = await ibge.indicadores_empresas(id_mun)
        rank = await ibge.pib_rank_uf(id_mun, muni["uf"]) if muni["uf"] else (None, None)
        geo = await ibge.centro_municipio(id_mun)
        territorio = await ibge.metadados_territoriais(id_mun)

        # mapa-bolha do estado: todos os municípios com centro + PIB (2023)
        vizinhos: list[dict[str, Any]] = []
        bbox: dict[str, float] | None = None
        try:
            if muni.get("uf_id"):
                centros = await ibge.centros_uf(muni["uf_id"])
                pibs = await ibge.pib_municipios_uf(muni["uf"])
                nomes = {m["id"]: m["nome"] for m in await ibge.lista_municipios() if m["uf"] == muni["uf"]}
                for cod, c in centros.items():
                    if cod == id_mun or not c:
                        continue
                    pib_v = pibs.get(cod)
                    if not pib_v:
                        continue
                    vizinhos.append({
                        "id": cod,
                        "nome": nomes.get(cod, str(cod)),
                        "lon": c["lon"], "lat": c["lat"],
                        "pib": pib_v,
                    })
                lons = [v["lon"] for v in vizinhos] + ([geo["lon"]] if geo else [])
                lats = [v["lat"] for v in vizinhos] + ([geo["lat"]] if geo else [])
                if lons:
                    bbox = {
                        "min_lon": min(lons), "max_lon": max(lons),
                        "min_lat": min(lats), "max_lat": max(lats),
                    }
        except Exception:
            pass  # o mapa é enfeite analítico — nunca derruba o painel

        pib_real = deflator.deflacionar(pib)
        ind = painel_indicadores(pop, pib, pib_real, empresas, rank, participacao_pib)

        dados: dict[str, Any] = {
            "info": muni,
            "geo": geo,
            "territorio": territorio,
            "mapa": {"vizinhos": vizinhos, "bbox": bbox},
            "pop_serie": sorted(pop.items()),
            "pib_serie": {"nominal": sorted(pib.items()), "real": sorted(pib_real.items())},
            "vab_setorial": vab_setorial,
            "participacao_pib": participacao_pib,
            "contexto": contexto,
            "indicators": ind,
        }
        dados["insights"] = insights.gerar(dados)
        return dados

    return await CACHE.get_or_set(f"painel:{id_mun}", TTL_PAINEL, _montar)


async def dados_comparador(ids: list[int]) -> list[dict[str, Any]]:
    return list(await asyncio.gather(*(dados_municipio(i) for i in ids)))
