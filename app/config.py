"""Configurações centrais do Radar de Oportunidades Regionais."""
from __future__ import annotations

# ---------------------------------------------------------------
# IBGE — REST
# ---------------------------------------------------------------
IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
IBGE_MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas"

# Malha oficial do Brasil por UF (GeoJSON simplificado — ~98 KB)
MALHA_BRASIL = f"{IBGE_MALHAS}/paises/BR?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima"
MALHA_MUNICIPIO = f"{IBGE_MALHAS}/municipios/{{id}}?formato=application/vnd.geo+json&qualidade=minima"
MALHA_MUNICIPIO_METADADOS = f"{IBGE_MALHAS}/municipios/{{id}}/metadados"
MALHA_ESTADO = f"{IBGE_MALHAS}/estados/{{uf_id}}?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima"

# Código IBGE da UF (2 dígitos) → sigla — usado para nomear a malha
UF_CODIGOS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

SIDRA_URL = (
    "https://apisidra.ibge.gov.br/values"
    "/t/{tabela}/n6/{ids}/v/{vars_}/p/{periodos}?formato=json"
)
SIDRA_URL_S_PERIODO = (
    "https://apisidra.ibge.gov.br/values"
    "/t/{tabela}/n6/{ids}/v/{vars_}?formato=json"
)

# Tabelas SIDRA utilizadas
TAB_POPULACAO = 6579   # População residente estimada (municipal, anual)
TAB_PIB = 5938         # PIB dos Municípios (ınício em 2002)
TAB_EMPRESAS = 6449    # CEMPRE — empresas, pessoal e salários (municipal)

VAR_POPULACAO = 9324   # População residente estimada (pessoas)
VAR_PIB = 37           # PIB a preços correntes (mil R$)
VAR_PIB_PART_UF = 497  # Participação do PIB no PIB da Unidade da Federação (%)
VAR_PIB_PART_BR = 496  # Participação do PIB no PIB do Brasil (%)

# Variáveis do Valor Adicionado Bruto (VAB Setorial na Tab 5938)
VARS_VAB_SETORIAL = {
    "agro": "513",        # Agropecuária
    "industria": "517",   # Indústria
    "servicos": "6575",   # Serviços (exclusive Adm. Pública)
    "admin": "525",       # Adm., defesa, educ. e saúde públicas
}

# ---------------------------------------------------------------
# Banco Central — SOAP (FachadaWSSGS / SGS)
# ---------------------------------------------------------------
BCB_WSDL = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?wsdl"
BCB_ENDPOINT = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
BCB_REST_FALLBACK = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"

# Códigos oficiais de séries do SGS
SERIES_BCB = {
    "ipca": 433,              # IPCA — variação % mensal
    "ipca_12m": 13522,        # IPCA — acumulado 12 meses (%)
    "selic": 432,             # Meta Selic definida pelo Copom (% a.a.)
    "cambio": 1,              # Câmbio — livre — US$ (compra) — diário
    "inadimplencia_pj": 21086,# Inadimplência da carteira de crédito - PJ (%)
    "juros_giro": 20749,      # Taxa média de juros - PJ - Capital de giro (% a.a.)
}

# ---------------------------------------------------------------
# TTL do cache interno (segundos)
# ---------------------------------------------------------------
TTL_LOCALIDADES = 24 * 3600   # lista de municípios
TTL_SIDRA = 6 * 3600          # séries municipais
TTL_BCB = 30 * 60             # séries financeiras (SOAP)
