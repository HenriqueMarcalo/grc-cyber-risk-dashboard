import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from motor_risco import COLUNAS_DISPLAY, processar_priorizacao_risco, resolver_mochila_01

# ---------------------------------------------------------------------------
# 1) Motor: casos extremos (blindagem contra crash)
# ---------------------------------------------------------------------------
assert resolver_mochila_01([10000], [100], -50000) == []
assert resolver_mochila_01([10000, 20000], [100, 200], 0) == []
assert resolver_mochila_01([20000, -5000], [100, 200], 100000) == [0]
assert resolver_mochila_01([0, 20000], [500, 200], 100000) == [1, 0]
assert resolver_mochila_01([-5, -10], [100, 200], 100000) == []
assert resolver_mochila_01([10000, 20000], [100, 200], 100000) == [1, 0]
assert resolver_mochila_01([10000, 20000], [100, 200], 300000) == [0, 1]
assert resolver_mochila_01([10000, -5000], [100, 200], 300000) == [0]
print("1) motor casos extremos OK")

# ---------------------------------------------------------------------------
# 2) Empty -> df com COLUNAS_DISPLAY (editor continua a renderizar)
# ---------------------------------------------------------------------------
df_vazio = processar_priorizacao_risco([], 0.30, 5000000, 120000, 0.02, 90, 50000)
assert set(df_vazio.columns) == set(COLUNAS_DISPLAY), list(df_vazio.columns)
assert df_vazio.empty
print("2) empty df OK ->", len(df_vazio.columns), "colunas")

# ---------------------------------------------------------------------------
# 3) Processamento normal + terminologia GRC
# ---------------------------------------------------------------------------
SAMPLE = [
    {"asset_name": "ERP SAP Core", "dept": "Financeiro", "asset_value": 450000, "vulnerability": "Acesso Admin sem MFA", "framework": "ISO 27001 A.8.5", "rgpd": True, "threat_level": 4, "mitigation_cost": 20000},
    {"asset_name": "Plataforma E-Commerce", "dept": "Operações", "asset_value": 650000, "vulnerability": "Sem Patches Críticos", "framework": "NIST CSF PR.PS-1", "rgpd": True, "threat_level": 5, "mitigation_cost": 50000},
    {"asset_name": "Website (WordPress)", "dept": "Marketing", "asset_value": 40000, "vulnerability": "Plugins Desatualizados", "framework": "ISO 27001 A.8.8", "rgpd": False, "threat_level": 4, "mitigation_cost": 4000},
]
df = processar_priorizacao_risco(SAMPLE, 0.30, 5000000, 120000, 0.02, 90, 50000)
assert len(df) == 3
assert (df["Risco Inerente (€)"] > 0).all()

assert "Severidade da Ameaça (1-5)" in COLUNAS_DISPLAY
assert "Nível de Ameaça (1-5)" not in COLUNAS_DISPLAY
decisoes = set(df["Decisão Estratégica"])
assert decisoes <= {"Mitigação Financiada", "Risco Aceite (Não Financiado)"}, decisoes
assert "Financiado (Remediar)" not in decisoes
assert set(df["Tolerância (Apetite)"]) <= {"Dentro do Apetite", "Fora do Apetite"}
print("3) processamento + terminologia OK -> decisões:", sorted(decisoes))

# ---------------------------------------------------------------------------
# 4) Residual: mitigado < inerente; aceite == inerente
# ---------------------------------------------------------------------------
for _, row in df.iterrows():
    if row["Decisão Estratégica"] == "Mitigação Financiada":
        assert row["Risco Residual (€)"] < row["Risco Inerente (€)"]
    else:
        assert row["Risco Residual (€)"] == row["Risco Inerente (€)"]
print("4) risco residual OK (mitigado reduz, aceite mantém)")

print("ALL MOTOR TESTS PASSED")
