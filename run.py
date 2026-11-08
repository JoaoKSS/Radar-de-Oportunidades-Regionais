"""Ponto de entrada: python run.py [porta]  →  http://127.0.0.1:8000

* Se as dependências não estiverem instaladas no Python atual, reexecuta
  automaticamente com o interpretador do .venv local.
* Se a porta já estiver ocupada, avisa com clareza em vez de stack trace.
"""
import os
import socket
import sys
from pathlib import Path

PORTA_PADRAO = 8000


def _garanta_venv() -> None:
    try:
        import uvicorn  # noqa: F401
    except ModuleNotFoundError:
        venv_python = (Path(__file__).resolve().parent / ".venv" / "bin" / "python").resolve()
        if venv_python.exists() and Path(sys.executable).resolve() != venv_python:
            os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])
        print(
            "Dependências ausentes. Monte o ambiente uma vez:\n"
            "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
        )
        raise SystemExit(1)


def _porta() -> int:
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            print(f"Porta inválida: {sys.argv[1]!r} — use um número (ex.: python run.py 8010)")
            raise SystemExit(1)
    return PORTA_PADRAO


def _porta_livre(porta: int) -> bool:
    s = socket.socket()
    # SO_REUSEADDR evita falso positivo por TIME_WAIT de conexões recentes
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", porta))
        return True
    except OSError:
        return False
    finally:
        s.close()


_garanta_venv()

import uvicorn  # noqa: E402

if __name__ == "__main__":
    porta = _porta()
    if not _porta_livre(porta):
        print(f"A porta {porta} já está em uso. Opções:")
        print(f"  1. Encerre o servidor anterior:  fuser -k {porta}/tcp")
        print(f"  2. Use outra porta:              python run.py {porta + 1}")
        raise SystemExit(1)
    print(f"Radar de Oportunidades Regionais → http://127.0.0.1:{porta}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=porta)
