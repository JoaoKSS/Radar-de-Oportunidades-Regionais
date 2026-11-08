from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

class Cache:
    def __init__(self) -> None:
        self._dados: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, chave: str, ttl: float, fabrica: Callable[[], Awaitable[Any]]) -> Any:
        async with self._lock:
            hit = self._dados.get(chave)
            if hit and time.monotonic() - hit[0] < ttl:
                return hit[1]

        valor = await fabrica()
        async with self._lock:
            self._dados[chave] = (time.monotonic(), valor)
        return valor

CACHE = Cache()
