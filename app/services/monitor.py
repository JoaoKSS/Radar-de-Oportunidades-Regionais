from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque

MAX_EVENTOS = 80
MAX_CARACTERES = 6_000

_eventos: Deque[dict[str, Any]] = deque(maxlen=MAX_EVENTOS)

def _cortar(texto: str) -> str:
    return str(texto or "")

def registrar(
    protocolo: str,
    operacao: str,
    *,
    status: str = "",
    duracao_ms: float | None = None,
    enviado: str = "",
    recebido: str = "",
    url: str = "",
) -> None:

    try:
        _eventos.appendleft({
            "protocolo": protocolo,
            "operacao": operacao,
            "url": url,
            "status": str(status or ""),
            "duracao_ms": round(duracao_ms) if duracao_ms is not None else None,
            "t": time.strftime("%H:%M:%S"),
            "enviado": _cortar(enviado),
            "recebido": _cortar(recebido),
        })
    except Exception:
        pass

def ultimos(protocolo: str | None = None) -> list[dict[str, Any]]:
    nome = (protocolo or "").strip().upper()
    if nome in ("REST", "SOAP"):
        return [e for e in _eventos if e["protocolo"] == nome]
    return list(_eventos)
