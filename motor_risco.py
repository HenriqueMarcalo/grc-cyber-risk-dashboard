# -----------------------------------------------------------------------------
# Risk Engine
# Pure mathematics (no Streamlit dependency): prioritization and capital allocation.
# -----------------------------------------------------------------------------
import pandas as pd

COLUNAS_DISPLAY = ["Asset", "Department", "Asset Value (€)", "Vulnerability", "Framework", "Threat Severity (1-5)", "Mitigation Cost (€)", "rgpd", "Inherent Risk (€)", "Strategic Decision", "Residual Risk (€)", "Risk Appetite Tolerance"]


def resolver_mochila_01(custos, valores, capacidade):
    capacidade = int(capacidade)
    if capacidade <= 0:
        return []
    n = len(custos)
    if capacidade > 250000:
        ordem = sorted(range(n), key=lambda i: (valores[i] / custos[i]) if custos[i] > 0 else 0, reverse=True)
        escolhidos = []
        resto = capacidade
        for i in ordem:
            if custos[i] <= 0:
                continue
            if custos[i] <= resto:
                escolhidos.append(i)
                resto -= custos[i]
        return escolhidos

    dp = [0] * (capacidade + 1)
    escolha = [[False] * (capacidade + 1) for _ in range(n)]
    for i in range(n):
        if custos[i] < 0:
            continue
        for w in range(capacidade, custos[i] - 1, -1):
            candidato = dp[w - custos[i]] + valores[i]
            if candidato > dp[w]:
                dp[w] = candidato
                escolha[i][w] = True

    escolhidos = []
    w = capacidade
    for i in range(n - 1, -1, -1):
        if escolha[i][w]:
            escolhidos.append(i)
            w -= custos[i]
    return escolhidos


def processar_priorizacao_risco(assets, prob, faturacao, orcamento_disponivel, mult_rgpd, eficacia, apetite):
    if not assets:
        return pd.DataFrame(columns=COLUNAS_DISPLAY)

    potencial_multa_rgpd_empresa = faturacao * mult_rgpd
    oper_risks = [asset.get("asset_value", 0) * prob for asset in assets]
    total_oper_rgpd = sum(op for asset, op in zip(assets, oper_risks) if asset.get("rgpd", False))

    evaluated = []
    for i, asset in enumerate(assets):
        risco_operacional = oper_risks[i]
        if asset.get("rgpd", False) and total_oper_rgpd > 0:
            coima_alocada = potencial_multa_rgpd_empresa * (oper_risks[i] / total_oper_rgpd)
        else:
            coima_alocada = 0
        risco_total_ativo = risco_operacional + (coima_alocada * prob)

        evaluated.append({
            "Asset": asset.get("asset_name", ""),
            "Department": asset.get("dept", ""),
            "Asset Value (€)": asset.get("asset_value", 0),
            "Vulnerability": asset.get("vulnerability", ""),
            "Framework": asset.get("framework", ""),
            "Threat Severity (1-5)": asset.get("threat_level", 3),
            "Mitigation Cost (€)": asset.get("mitigation_cost", 0),
            "rgpd": asset.get("rgpd", False),
            "Inherent Risk (€)": risco_total_ativo
        })

    df = pd.DataFrame(evaluated)
    if df.empty:
        return df

    custos = df["Mitigation Cost (€)"].astype(int).tolist()
    valores = (df["Inherent Risk (€)"] * (eficacia / 100.0)).astype(int).tolist()
    ativos_financiados = resolver_mochila_01(custos, valores, orcamento_disponivel)

    decisoes = ["Risk Accepted (Not Funded)"] * len(df)
    for idx in ativos_financiados:
        decisoes[idx] = "Funded Mitigation"
    df["Strategic Decision"] = decisoes

    fator_residual_pos_mitigacao = 1.0 - (eficacia / 100.0)
    df["Residual Risk (€)"] = df.apply(
        lambda x: x["Inherent Risk (€)"] * fator_residual_pos_mitigacao if x["Strategic Decision"] == "Funded Mitigation" else x["Inherent Risk (€)"],
        axis=1
    )
    df["Risk Appetite Tolerance"] = df.apply(
        lambda x: "Within Appetite" if x["Residual Risk (€)"] <= apetite else "Outside Appetite",
        axis=1
    )
    return df
