"""Indicadores derivados — transformam séries brutas em decisões.

Combina as duas integrações:
  * PIB municipal (REST/SIDRA, valores nominais) é deflacionado pelo IPCA
    real (SOAP/BCB) → crescimento econômico de verdade, sem efeito inflação.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

# ------------------------------------------------------------------
# Utilidades numéricas
# ------------------------------------------------------------------

def cagr(inicial: float, final: float, anos: float) -> float | None:
    if anos <= 0 or inicial <= 0:
        return None
    try:
        return (final / inicial) ** (1 / anos) - 1
    except (OverflowError, ZeroDivisionError):
        return None

def variacao(inicial: float | None, final: float | None) -> float | None:
    if not inicial or final is None:
        return None
    return final / inicial - 1

def classificar(crescimento: float | None, bom: float, ruim: float) -> str:
    """'excelente' | 'boa' | 'estavel' | 'ruim'."""
    if crescimento is None:
        return "nulo"
    if crescimento >= bom:
        return "excelente"
    if crescimento >= ruim:
        return "estavel"
    return "ruim"

# ------------------------------------------------------------------
# Deflacionador — IPCA (SOAP do BCB) → índice de preços
# ------------------------------------------------------------------

class Deflator:
    """Índice de preços a partir do IPCA mensal (SOAP/BCB).

    ``I(ano)`` = produto cumulativo até o dezembro do ano.
    Converter valores do ano X para preços do ano-base B:
      ``valor(X) × I(base) / I(X)``  (multiplique PELA inflação entre X e B).
    """

    def __init__(self, pontos_ipca: list[dict[str, Any]]) -> None:
        self._cumul: dict[int, float] = {}
        fator = 1.0
        datas = []
        for p in pontos_ipca:
            try:
                datas.append((dt.date.fromisoformat(p["data"]), float(p["valor"])))
            except (KeyError, ValueError, TypeError):
                continue
        datas.sort()
        for data, valor in datas:
            fator *= 1.0 + valor / 100.0
            if data.month == 12:
                self._cumul[data.year] = fator
        self._base = max(self._cumul) if self._cumul else None

    def ativo(self) -> bool:
        return self._base is not None

    def ano_base(self) -> int | None:
        return self._base

    def deflacionar(self, serie: dict[int, float]) -> dict[int, float]:
        """Converte para preços de dezembro do último ano completo da série IPCA."""
        if not self.ativo() or not serie:
            return dict(serie)
        ano_base = self._base
        f_base = self._cumul[ano_base]
        saida: dict[int, float] = {}
        for ano, valor in serie.items():
            f_ano = self._cumul.get(ano)
            if f_ano is None or f_ano <= 0:
                continue  # ano sem dezembro na série IPCA — fica de fora
            saida[ano] = valor * f_base / f_ano
        return dict(sorted(saida.items()))

# ------------------------------------------------------------------
# Painel executivo de um município
# ------------------------------------------------------------------

def painel_indicadores(
    populacao: dict[int, float],
    pib_nominal: dict[int, float],
    pib_real: dict[int, float],
    empresas: dict[str, Any],
    rank_pib: tuple[int | None, int | None],
    participacao: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resumo com taxas que alimentam cards, gráficos e insights."""
    pop_ano = max(populacao) if populacao else None
    pop_valor = populacao.get(pop_ano) if pop_ano else None
    pop_antes = populacao.get(pop_ano - 5) if pop_ano else None
    pop_cresc = variacao(pop_antes, pop_valor)

    pib_ano = max(pib_nominal) if pib_nominal else None
    pib_valor = pib_nominal.get(pib_ano) if pib_ano else None
    pop_ref = populacao.get(pib_ano) or pop_valor if pib_ano else None
    pib_pc = pib_valor / pop_ref if (pib_valor and pop_ref) else None

    real_ano = max(pib_real) if pib_real else None
    real_base = pib_real.get(real_ano - 5) if real_ano else None
    pib_real_5a = cagr(real_base, pib_real.get(real_ano, 0), 5.0) if real_base else None

    emp_n = empresas.get("empresas")
    emprego_n = empresas.get("empregos")
    assalariados_n = empresas.get("assalariados")
    salarios_mil = empresas.get("salarios")
    
    empresas_pc = emp_n / pop_valor * 1000 if emp_n and pop_valor else None
    empregos_empresa = emprego_n / emp_n if emp_n and emprego_n else None
    
    # Salário médio mensal estimado em R$
    salario_medio = (salarios_mil * 1000 / 12) / assalariados_n if (salarios_mil and assalariados_n and assalariados_n > 0) else None

    return {
        "populacao": {
            "ano": pop_ano, "valor": pop_valor, "cresc_5a": pop_cresc,
            "tag": classificar(pop_cresc, 0.02, 0.0),
        },
        "pib": {
            "ano": pib_ano, "valor": pib_valor,
            "cresc_real_5a": pib_real_5a,
            "tag": classificar(pib_real_5a, 0.02, 0.0),
        },
        "pib_pc": {"ano": pib_ano, "valor": pib_pc},
        "empresas": {
            "ano": empresas.get("ano"), "n": emp_n, "empregos": emprego_n,
            "assalariados": assalariados_n,
            "salarios": salarios_mil,
            "salario_medio": salario_medio,
            "por_mil_hab": empresas_pc, "empregos_por_empresa": empregos_empresa,
        },
        "rank": {"posicao": rank_pib[0], "de": rank_pib[1]},
        "participacao": participacao or {},
    }
