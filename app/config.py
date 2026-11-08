from __future__ import annotations

IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
IBGE_MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas"

MALHA_BRASIL = f"{IBGE_MALHAS}/paises/BR?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima"
MALHA_MUNICIPIO = f"{IBGE_MALHAS}/municipios/{{id}}?formato=application/vnd.geo+json&qualidade=minima"
MALHA_MUNICIPIO_METADADOS = f"{IBGE_MALHAS}/municipios/{{id}}/metadados"
MALHA_ESTADO = f"{IBGE_MALHAS}/estados/{{uf_id}}?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima"

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

TAB_POPULACAO = 6579
TAB_PIB = 5938
TAB_EMPRESAS = 6449

VAR_POPULACAO = 9324
VAR_PIB = 37
VAR_PIB_PART_UF = 497
VAR_PIB_PART_BR = 496

VARS_VAB_SETORIAL = {
    "agro": "513",
    "industria": "517",
    "servicos": "6575",
    "admin": "525",
}

BCB_WSDL = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?wsdl"
BCB_ENDPOINT = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
BCB_REST_FALLBACK = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"

SERIES_BCB = {
    "ipca": 433,
    "ipca_12m": 13522,
    "selic": 432,
    "cambio": 1,
    "inadimplencia_pj": 21086,
    "juros_giro": 20749,
}

TTL_LOCALIDADES = 24 * 3600
TTL_SIDRA = 6 * 3600
TTL_BCB = 30 * 60
