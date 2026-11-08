# Radar de Oportunidades Regionais

Sistema de investigação econômica por município: o usuário escolhe uma cidade e
recebe indicadores, evolução histórica, comparativo entre municípios e
**pontos de atenção para novos negócios** — não é um painel estatístico, é um
mecanismo de análise comparativa.

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python run.py          # → http://127.0.0.1:8000
```

A primeira requisição de um município demora (~20 s) porque puxa e cacheia as
séries; as suivantentes são instantâneas (cache TTL em memória).

## Rotas

| Rota | Papel |
|---|---|
| `/` | Busca do município (autocomplete) + visão geral das integrações |
| `/municipio/{id}` | Painel completo do município |
| `/comparar?ids=1,2,3` | Comparador de 2 a 4 municípios |
| `/api/localidades?q=` | Autocomplete (IBGE Localidades, cache 24 h) |
| `/api/diagnostico` | Saúde das integrações: `{bcb_soap, bcb_reserva_rest, ibge_rest}` |

## Integrações obrigatórias

| Protocolo | Fonte | O que traz |
|---|---|---|
| **REST/API** | IBGE — Localidades (`/api/v1/localidades/municipios`) | Catálogo dos 5.570 municípios |
| **REST/API** | IBGE — SIDRA (`apisidra.ibge.gov.br`) | t6579 população · t5938 PIB municipal · t6449 CEMPRE (empresas/empregos) |
| **SOAP** | Banco Central — FachadaWSSGS (`/wssgs/services/FachadaWSSGS`) | IPCA mensal (433), IPCA 12m (13522), Meta Selic (432), Câmbio (1) |

O serviço SOAP usa envelope `rpc/encoded` do Apache Axis 1.2 (2005), com
`soapenc:Array` sem modelo de conteúdo e referências `multiRef` (id/href)
recorrentes — serializers automáticos quebram nesse formato (zeep falha no
`ArrayOfflong`). Por isso o cliente SOAP em `app/services/bcb.py` constrói o
envelope à mão e resolve o grafo de referências com um walker recursivo.

Se o endpoint SOAP estiver fora, o sistema degrada para a API REST legada do
SGS e **marca a fonte na tela** (`SOAP` / `REST`).

## Motor de análise

1. **População** — evolução estimada anual (SIDRA t6579) → crescimento em
   janela de 5 anos.
2. **PIB real** — o PIB municipal nominal (t5938, mil R$) é deflacionado pelo
   **IPCA real do BCB via SOAP** → crescimento real ≙ economia de verdade,
   sem o efeito dos preços. O deflator age com índice cumulativo mensal até o
   dezembro do último ano completo.
3. **Saturação de mercado** — empresas ativas (CEMPRE t6449) por mil
   habitantes e empregados por empresa.
4. **Posição estadual** — ranking de PIB do município dentro da própria UF
   (busca em lote de todas as unidades do estado no SIDRA).
5. **Contexto financeiro (SOAP)** — IPCA 12m, Selic meta, câmbio; alimentam
   cards e heurísticas.
6. **Pontos de atenção** — heurísticas com tags `potencial`/`atenção`/`risco`
   por tipo de empreendimento (demografia, economia real, concorrência, mão
   de obra, posição estadual, inflação e juro — `app/analysis/insights.py`).

## Estrutura

```
app/
├── main.py              rotas + filtros pt-BR + payloads de gráficos
├── config.py            URLs, séries SGS, TTFs de cache
├── services/
│   ├── ibge.py          REST — IBGE Localidades + SIDRA (parsing por cabeçalho)
│   ├── bcb.py           SOAP — FachadaWSSGS (walker rpc/encoded) + reserva REST
│   └── cache.py         cache TTL assíncrono
├── analysis/
│   ├── indicators.py    deflator IPCA, CAGR, painel de indicadores
│   ├── insights.py      heurísticas de Pontos de atenção
│   └── painel.py        montador das visões (REST × SOAP combinados)
└── ui/
    ├── templates/       página inicial, painel, comparador (Jinja2, SSR)
    └── static/          CSS próprio + ECharts local (sem CDN)
```

## Notas de robustez

* O SIDRA **alterna a ordem das dimensões** (D2↔D3) entre respostas; as
  colunas são mapeadas pelo cabeçalho, não pela posição (`mapear_dimensoes`).
* A janela SOAP que não possui pontos (ex.: IPCA de outubro ainda não
  publicado) dispara `Fault "Value(s) not found"` — tratada como série vazia
  e suprida pela reserva REST.
* Empresas e população são de bases com defasagens diferentes — cada medida
  exibe o próprio ano de referência.
