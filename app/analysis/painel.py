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

        # Disparo paralelo (asyncio.gather) de todas as integrações REST e SOAP
        tarefas = [
            bcb.contexto_financeiro(anos=26),
            ibge.serie_populacao(id_mun),
            ibge.serie_pib(id_mun),
            ibge.composicao_setorial_pib(id_mun),
            ibge.participacao_pib(id_mun),
            ibge.indicadores_empresas(id_mun),
            ibge.pib_rank_uf(id_mun, muni["uf"]) if muni.get("uf") else asyncio.sleep(0, result=(None, None)),
            ibge.centro_municipio(id_mun),
            ibge.metadados_territoriais(id_mun),
        ]

        # Se tiver UF, dispara também os dados do mapa em paralelo
        tem_mapa = bool(muni.get("uf_id") and muni.get("uf"))
        if tem_mapa:
            tarefas.extend([
                ibge.centros_uf(muni["uf_id"]),
                ibge.pib_municipios_uf(muni["uf"]),
                ibge.lista_municipios(),
            ])

        resultados = await asyncio.gather(*tarefas)

        contexto = resultados[0]
        pop = resultados[1]
        pib = resultados[2]
        vab_setorial = resultados[3]
        participacao_pib = resultados[4]
        empresas = resultados[5]
        rank = resultados[6]
        geo = resultados[7]
        territorio = resultados[8]

        deflator = Deflator(contexto["ipca"]["pontos"])

        # Processa dados do mapa de vizinhos a partir dos resultados já baixados
        vizinhos: list[dict[str, Any]] = []
        bbox: dict[str, float] | None = None
        if tem_mapa and len(resultados) >= 12:
            try:
                centros = resultados[9] or {}
                pibs = resultados[10] or {}
                todos_munis = resultados[11] or []
                nomes = {m["id"]: m["nome"] for m in todos_munis if m.get("uf") == muni["uf"]}
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
                pass

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
