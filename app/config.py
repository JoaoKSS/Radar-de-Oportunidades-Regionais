from __future__ import annotations

UF_CODIGOS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

UF_NOMES = {
    "RO": ("Rondônia", "Norte"), "AC": ("Acre", "Norte"), "AM": ("Amazonas", "Norte"),
    "RR": ("Roraima", "Norte"), "PA": ("Pará", "Norte"), "AP": ("Amapá", "Norte"),
    "TO": ("Tocantins", "Norte"), "MA": ("Maranhão", "Nordeste"), "PI": ("Piauí", "Nordeste"),
    "CE": ("Ceará", "Nordeste"), "RN": ("Rio Grande do Norte", "Nordeste"),
    "PB": ("Paraíba", "Nordeste"), "PE": ("Pernambuco", "Nordeste"), "AL": ("Alagoas", "Nordeste"),
    "SE": ("Sergipe", "Nordeste"), "BA": ("Bahia", "Nordeste"), "MG": ("Minas Gerais", "Sudeste"),
    "ES": ("Espírito Santo", "Sudeste"), "RJ": ("Rio de Janeiro", "Sudeste"),
    "SP": ("São Paulo", "Sudeste"), "PR": ("Paraná", "Sul"), "SC": ("Santa Catarina", "Sul"),
    "RS": ("Rio Grande do Sul", "Sul"), "MS": ("Mato Grosso do Sul", "Centro-Oeste"),
    "MT": ("Mato Grosso", "Centro-Oeste"), "GO": ("Goiás", "Centro-Oeste"),
    "DF": ("Distrito Federal", "Centro-Oeste"),
}

SIDRA_MUNICIPIOS_CATALOGO = (
    "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/last%201?formato=json"
)

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
TAB_AREA = 1301

VAR_POPULACAO = 9324
VAR_PIB = 37
VAR_AREA = 615

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
