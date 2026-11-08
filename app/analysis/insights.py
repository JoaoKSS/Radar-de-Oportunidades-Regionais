"""Pontos de atenção — heurísticas orientadas a tipos de empreendimento.

Cada insight tem uma tag visual ('positiva' | 'cuidado' | 'risco') e um
texto claro. Nada aqui é oráculo: são sinais para investigar antes de
investir.
"""
from __future__ import annotations

from typing import Any

def gerar(dados: dict[str, Any]) -> list[dict[str, str]]:
    ind = dados["indicators"]
    insights: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # Demografia — demanda presente e futura
    # ------------------------------------------------------------------
    pop = ind["populacao"]
    cresc = pop["cresc_5a"]
    if cresc is None:
        insights.append({
            "tag": "cuidado",
            "categoria": "Demografia",
            "metrica": "Série incompleta",
            "texto": "Dados populacionais insuficientes para o intervalo recente. Recomenda-se confrontar com a microrregião imediata."
        })
    elif cresc >= 0.02:
        insights.append({
            "tag": "positiva",
            "categoria": "Demografia",
            "metrica": f"+{cresc*100:.1f}% em 5 anos",
            "texto": "Expansão demográfica consistente. Ambiente favorável para escala em bens de consumo, serviços locais e varejo essencial."
        })
    elif cresc <= 0:
        insights.append({
            "tag": "cuidado",
            "categoria": "Demografia",
            "metrica": f"-{abs(cresc)*100:.1f}% em 5 anos",
            "texto": "Contração populacional no período. Exige foco em produtos de maior tíquete médio, serviços B2B ou negócios com operação regional/digital."
        })
    else:
        insights.append({
            "tag": "cuidado",
            "categoria": "Demografia",
            "metrica": f"{cresc*100:+.1f}% em 5 anos",
            "texto": "População estabilizada. Mercado com pouca tração de novos entrantes por volume; diferenciação e retenção são prioritárias."
        })

    # ------------------------------------------------------------------
    # Economia real (PIB deflacionado pelo IPCA)
    # ------------------------------------------------------------------
    pib = ind["pib"]
    cresc_real = pib["cresc_real_5a"]
    if cresc_real is None:
        insights.append({
            "tag": "cuidado",
            "categoria": "Economia Real",
            "metrica": "Série não deflacionada",
            "texto": "Histórico de PIB insuficiente para deflação por IPCA; números nominais podem refletir apenas repasse inflacionário."
        })
    elif cresc_real >= 0.02:
        insights.append({
            "tag": "positiva",
            "categoria": "Economia Real",
            "metrica": f"+{cresc_real*100:.1f}% a.a. real",
            "texto": "Crescimento econômico real acima da inflação. Geração líquida de renda e demanda com potencial de absorção para novos negócios."
        })
    elif cresc_real <= 0:
        insights.append({
            "tag": "risco",
            "categoria": "Economia Real",
            "metrica": f"-{abs(cresc_real)*100:.1f}% a.a. real",
            "texto": "Recuo do PIB em termos reais. Poder de compra sob pressão; recomendam-se estruturas de custo enxutas e modelos anticíclicos."
        })
    else:
        insights.append({
            "tag": "cuidado",
            "categoria": "Economia Real",
            "metrica": "Variação real neutra",
            "texto": "Atividade econômica estagnada no quinquênio. Crescimento viável principalmente por captura de fatia de mercado existente."
        })

    # ------------------------------------------------------------------
    # Saturação de mercado — empresas por mil habitantes
    # ------------------------------------------------------------------
    emp = ind["empresas"]
    if emp["por_mil_hab"] is not None:
        if emp["por_mil_hab"] >= 40:
            insights.append({
                "tag": "cuidado",
                "categoria": "Concorrência",
                "metrica": f"{emp['por_mil_hab']:.1f} emp./mil hab.",
                "texto": "Alta densidade de estabelecimentos comerciais. Mercado saturado em segmentos tradicionais; indispensável posicionamento nichado."
            })
        elif emp["por_mil_hab"] <= 10:
            insights.append({
                "tag": "positiva",
                "categoria": "Concorrência",
                "metrica": f"{emp['por_mil_hab']:.1f} emp./mil hab.",
                "texto": "Baixa oferta empresarial relativa. Janela de oportunidade em serviços básicos, sujeita à validação de demanda efetiva."
            })
        else:
            insights.append({
                "tag": "cuidado",
                "categoria": "Concorrência",
                "metrica": f"{emp['por_mil_hab']:.1f} emp./mil hab.",
                "texto": "Densidade competitiva em nível mediano. Estratégia viável desde que amparada em pesquisa setorial de gargalos locais."
            })

    # ------------------------------------------------------------------
    # Intensidade de mão de obra
    # ------------------------------------------------------------------
    if emp["empregos_por_empresa"] is not None:
        if emp["empregos_por_empresa"] > 8:
            insights.append({
                "tag": "positiva",
                "categoria": "Mão de Obra",
                "metrica": f"~{emp['empregos_por_empresa']:.0f} vagas/empresa",
                "texto": "Presença expressiva de empresas de médio porte. Mercado de trabalho formal estruturado para absorção operacional."
            })
        elif emp["empregos_por_empresa"] < 2.5:
            insights.append({
                "tag": "cuidado",
                "categoria": "Mão de Obra",
                "metrica": f"~{emp['empregos_por_empresa']:.1f} vagas/empresa",
                "texto": "Prevalência acentuada de microempresas e autônomos. Contratações com qualificação técnica exigirão recrutamento especializado."
            })

    # ------------------------------------------------------------------
    # Poder de Compra / Renda Média (CEMPRE)
    # ------------------------------------------------------------------
    salario_medio = emp.get("salario_medio")
    if salario_medio is not None:
        if salario_medio >= 3500:
            insights.append({
                "tag": "positiva",
                "categoria": "Poder de Compra",
                "metrica": f"R$ {salario_medio:,.0f}/mês".replace(",", "."),
                "texto": "Massa salarial formal acima da média. Mercado receptivo a tíquetes mais altos, produtos de conveniência e serviços especializados."
            })
        elif salario_medio <= 2000:
            insights.append({
                "tag": "cuidado",
                "categoria": "Poder de Compra",
                "metrica": f"R$ {salario_medio:,.0f}/mês".replace(",", "."),
                "texto": "Renda média formal mais sensível a preço. Modelos de negócio de desconto, atacarejo e consumo essencial apresentam maior aderência."
            })

    # ------------------------------------------------------------------
    # Vocação Econômica (VAB Setorial do PIB)
    # ------------------------------------------------------------------
    vab = dados.get("vab_setorial") or {}
    pcts = vab.get("participacao_pct") or {}
    if pcts:
        serv = pcts.get("servicos", 0)
        ind_pct = pcts.get("industria", 0)
        agro_pct = pcts.get("agro", 0)
        admin_pct = pcts.get("admin", 0)

        if serv >= 60:
            insights.append({
                "tag": "positiva",
                "categoria": "Perfil Econômico",
                "metrica": f"{serv:.0f}% Serviços",
                "texto": "Economia predominantemente terciária. Forte circulação de comércio e serviços com ecossistema propício para negócios B2B e varejo."
            })
        elif ind_pct >= 35:
            insights.append({
                "tag": "positiva",
                "categoria": "Perfil Econômico",
                "metrica": f"{ind_pct:.0f}% Indústria",
                "texto": "Forte polo de transformação industrial. Alta demanda por manutenção, logística técnica e fornecedores corporativos."
            })
        elif agro_pct >= 25:
            insights.append({
                "tag": "positiva",
                "categoria": "Perfil Econômico",
                "metrica": f"{agro_pct:.0f}% Agro",
                "texto": "Economia com base no agronegócio. Janela estratégica para insumos agrícolas, maquinário, assistência técnica e serviços de apoio rural."
            })
        elif admin_pct >= 40:
            insights.append({
                "tag": "risco",
                "categoria": "Perfil Econômico",
                "metrica": f"{admin_pct:.0f}% Setor Público",
                "texto": "Elevada dependência do setor público e transferências governamentais. Mercado privado autônomo restrito a orçamentos municipais."
            })

    # ------------------------------------------------------------------
    # Posição na economia estadual
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Posição na economia estadual e nacional (Participação no PIB)
    # ------------------------------------------------------------------
    part_pib = dados.get("participacao_pib") or {}
    part_uf = part_pib.get("part_uf")
    part_br = part_pib.get("part_br")
    if part_uf is not None and part_br is not None:
        if part_uf >= 5.0 or part_br >= 0.5:
            insights.append({
                "tag": "positiva",
                "categoria": "Peso no PIB",
                "metrica": f"{part_uf:.2f}% UF · {part_br:.2f}% BR",
                "texto": f"Alta concentração de riqueza: gera {part_uf:.2f}% de todo o PIB estadual e {part_br:.2f}% do nacional. Mercado de alta liquidez e escala."
            })
        elif part_uf >= 1.0 or part_br >= 0.1:
            insights.append({
                "tag": "positiva",
                "categoria": "Peso no PIB",
                "metrica": f"{part_uf:.2f}% UF · {part_br:.2f}% BR",
                "texto": f"Polo de relevância regional: responde por {part_uf:.2f}% do PIB estadual e {part_br:.2f}% do PIB nacional, atuando como polo de atração econômico."
            })
        else:
            insights.append({
                "tag": "cuidado",
                "categoria": "Peso no PIB",
                "metrica": f"{part_uf:.2f}% UF · {part_br:.2f}% BR",
                "texto": f"Economia local com peso de {part_uf:.2f}% no estado e {part_br:.2f}% no país. Demanda foco em nichos ou integração com polos vizinhos."
            })

    rank = ind["rank"]
    if rank["posicao"] is not None and rank["de"]:
        pos, de = rank["posicao"], rank["de"]
        if pos <= 10:
            insights.append({
                "tag": "positiva",
                "categoria": "Relevância Estadual",
                "metrica": f"{pos}º de {de} municípios",
                "texto": "Principal polo econômico do estado. Concentração logística estratégica, liquidez de mercado e densidade de consumo."
            })
        elif pos / de > 0.75:
            insights.append({
                "tag": "risco",
                "categoria": "Relevância Estadual",
                "metrica": f"{pos}º de {de} municípios",
                "texto": "Posicionamento no quartil inferior do PIB estadual. Atenção a limitações de infraestrutura viária e fluxo local de capital."
            })

    # ------------------------------------------------------------------
    # Contexto financeiro nacional (SOAP do Banco Central)
    # ------------------------------------------------------------------
    contexto = dados.get("contexto", {})
    ipca12 = contexto.get("ipca_12m")
    if ipca12 and ipca12.get("pontos"):
        ultimo = ipca12["pontos"][-1]["valor"]
        if ultimo >= 6:
            insights.append({
                "tag": "risco",
                "categoria": "Macro / BCB",
                "metrica": f"IPCA 12m: {ultimo:.1f}%",
                "texto": "Inflação acima da meta central. Pressão sobre custos operacionais e margem bruta; requer repasse ágil e controle de estoque."
            })
        elif ultimo < 4:
            insights.append({
                "tag": "positiva",
                "categoria": "Macro / BCB",
                "metrica": f"IPCA 12m: {ultimo:.1f}%",
                "texto": "Inflação controlada no âmbito nacional. Cenário de maior previsibilidade para formação de preços e planejamento de custos."
            })
    selic = contexto.get("selic")
    if selic and selic.get("pontos"):
        taxa = selic["pontos"][-1]["valor"]
        if taxa >= 12:
            insights.append({
                "tag": "cuidado",
                "categoria": "Macro / BCB",
                "metrica": f"Selic: {taxa:.2f}% a.a.",
                "texto": "Custo de capital e taxas de crédito elevados. Desestimula alavancagem excessiva; favorece projetos com baixo investimento inicial."
            })

    # Inadimplência e Crédito Empresarial (SOAP BCB)
    inadimplencia = contexto.get("inadimplencia_pj")
    if inadimplencia and inadimplencia.get("pontos"):
        taxa_inad = inadimplencia["pontos"][-1]["valor"]
        if taxa_inad >= 3.5:
            insights.append({
                "tag": "risco",
                "categoria": "Crédito / BCB",
                "metrica": f"Inadimplência PJ: {taxa_inad:.2f}%",
                "texto": "Inadimplência de empresas em nível elevado no país. Negócios B2B devem adotar maior rigor em vendas a prazo e análise de clientes."
            })
        else:
            insights.append({
                "tag": "positiva",
                "categoria": "Crédito / BCB",
                "metrica": f"Inadimplência PJ: {taxa_inad:.2f}%",
                "texto": "Índice de solvência corporativa saudável no país, favorecendo operações de crédito e fornecimento a prazo."
            })

    juros_giro = contexto.get("juros_giro")
    if juros_giro and juros_giro.get("pontos"):
        taxa_giro = juros_giro["pontos"][-1]["valor"]
        if taxa_giro >= 25.0:
            insights.append({
                "tag": "cuidado",
                "categoria": "Crédito / BCB",
                "metrica": f"Capital de Giro: {taxa_giro:.1f}% a.a.",
                "texto": "Financiamento de curto prazo custoso para empresas. Fundamental projetar fluxo de caixa positivo sem depender de crédito rotativo."
            })

    return insights
