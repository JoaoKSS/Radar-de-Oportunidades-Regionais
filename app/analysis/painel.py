from __future__ import annotations

import asyncio
from typing import Any

from app.services import bcb, ibge
from app.analysis import insights
from app.analysis.indicators import Deflator, painel_indicadores
from app.services.cache import CACHE

TTL_PAINEL = 3600

async def dados_municipio(id_mun: int) -> dict[str, Any]:
    async def _montar() -> dict[str, Any]:
        muni = await ibge.municipio_por_id(id_mun)
        if muni is None:
            raise KeyError(f"Município {id_mun} não encontrado no IBGE")

        tarefas = [
            bcb.contexto_financeiro(anos=26),
            ibge.serie_populacao(id_mun),
            ibge.serie_pib(id_mun),
            ibge.composicao_setorial_pib(id_mun),
            ibge.participacao_pib(id_mun),
            ibge.indicadores_empresas(id_mun),
            ibge.pib_municipios_uf(muni["uf"]) if muni.get("uf") else asyncio.sleep(0, result={}),
            ibge.centro_municipio(id_mun),
            ibge.metadados_territoriais(id_mun),
        ]

        tem_mapa = bool(muni.get("uf_id") and muni.get("uf"))
        if tem_mapa:
            tarefas.extend([
                ibge.centros_uf(muni["uf_id"]),
                ibge.lista_municipios(),
            ])

        resultados = await asyncio.gather(*tarefas)

        contexto = resultados[0]
        pop = resultados[1]
        pib = resultados[2]
        vab_setorial = resultados[3]
        participacao_pib = resultados[4]
        empresas = resultados[5]
        pibs_uf = resultados[6] or {}
        geo = resultados[7]
        territorio = resultados[8]

        rank: tuple[int | None, int | None] = (None, None)
        if id_mun in pibs_uf and pibs_uf:
            ordenado = sorted(pibs_uf.values(), reverse=True)
            rank = (ordenado.index(pibs_uf[id_mun]) + 1, len(pibs_uf))

        deflator = Deflator(contexto["ipca"]["pontos"])

        vizinhos: list[dict[str, Any]] = []
        bbox: dict[str, float] | None = None
        if tem_mapa and len(resultados) >= 11:
            try:
                centros = resultados[9] or {}
                todos_munis = resultados[10] or []
                nomes = {m["id"]: m["nome"] for m in todos_munis if m.get("uf") == muni["uf"]}
                for cod, c in centros.items():
                    if cod == id_mun or not c:
                        continue
                    pib_v = pibs_uf.get(cod)
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
