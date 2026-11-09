from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DIR_DADOS = Path(__file__).resolve().parent.parent / "data"

_MALHA_BRASIL_CACHE: dict[str, Any] | None = None
_COORDENADAS_CACHE: dict[int, list[float]] | None = None

def carregar_malha_brasil() -> dict[str, Any]:
    global _MALHA_BRASIL_CACHE
    if _MALHA_BRASIL_CACHE is None:
        caminho = _DIR_DADOS / "malha_estados.json"
        if caminho.is_file():
            with open(caminho, "r", encoding="utf-8") as f:
                _MALHA_BRASIL_CACHE = json.load(f)
            for feicao in _MALHA_BRASIL_CACHE.get("features", []):
                props = feicao.setdefault("properties", {})
                props["name"] = props.get("UF") or props.get("codarea", "")
        else:
            _MALHA_BRASIL_CACHE = {"type": "FeatureCollection", "features": []}
    return _MALHA_BRASIL_CACHE

def carregar_coordenadas() -> dict[int, list[float]]:
    global _COORDENADAS_CACHE
    if _COORDENADAS_CACHE is None:
        caminho = _DIR_DADOS / "coordenadas_municipios.json"
        if caminho.is_file():
            with open(caminho, "r", encoding="utf-8") as f:
                bruto = json.load(f)
                _COORDENADAS_CACHE = {int(k): v for k, v in bruto.items()}
        else:
            _COORDENADAS_CACHE = {}
    return _COORDENADAS_CACHE

def obter_coordenada_municipio(id_mun: int) -> dict[str, float] | None:
    coords = carregar_coordenadas().get(int(id_mun))
    if coords:
        return {"lat": coords[0], "lon": coords[1]}
    return None

def obter_coordenadas_uf(uf_id: str | int) -> dict[int, dict[str, float]]:
    coords = carregar_coordenadas()
    prefixo = str(uf_id)
    return {
        cod: {"lat": c[0], "lon": c[1]}
        for cod, c in coords.items()
        if str(cod).startswith(prefixo)
    }

