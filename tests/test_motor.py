import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from motor_risco import COLUNAS_DISPLAY, processar_priorizacao_risco, resolver_mochila_01


def test_knapsack_edge_cases():
    assert resolver_mochila_01([10000], [100], -50000) == []
    assert resolver_mochila_01([10000, 20000], [100, 200], 0) == []
    assert resolver_mochila_01([20000, -5000], [100, 200], 100000) == [0]
    assert resolver_mochila_01([0, 20000], [500, 200], 100000) == [1, 0]
    assert resolver_mochila_01([-5, -10], [100, 200], 100000) == []
    assert resolver_mochila_01([10000, 20000], [100, 200], 100000) == [1, 0]
    assert resolver_mochila_01([10000, 20000], [100, 200], 300000) == [0, 1]
    assert resolver_mochila_01([10000, -5000], [100, 200], 300000) == [0]


def test_empty_input_returns_display_columns():
    df_vazio = processar_priorizacao_risco([], 0.30, 5000000, 120000, 0.02, 90, 50000)
    assert set(df_vazio.columns) == set(COLUNAS_DISPLAY), list(df_vazio.columns)
    assert df_vazio.empty


def test_processing_and_grc_terminology():
    SAMPLE = [
        {"asset_name": "ERP SAP Core", "dept": "Finance", "asset_value": 450000, "vulnerability": "Admin Access without MFA", "framework": "ISO 27001 A.8.5", "rgpd": True, "threat_level": 4, "mitigation_cost": 20000},
        {"asset_name": "E-Commerce Platform", "dept": "Operations", "asset_value": 650000, "vulnerability": "Missing Critical Patches", "framework": "NIST CSF PR.PS-1", "rgpd": True, "threat_level": 5, "mitigation_cost": 50000},
        {"asset_name": "Website (WordPress)", "dept": "Marketing", "asset_value": 40000, "vulnerability": "Outdated Plugins", "framework": "ISO 27001 A.8.8", "rgpd": False, "threat_level": 4, "mitigation_cost": 4000},
    ]
    df = processar_priorizacao_risco(SAMPLE, 0.30, 5000000, 120000, 0.02, 90, 50000)
    assert len(df) == 3
    assert (df["Inherent Risk (€)"] > 0).all()

    assert "Threat Severity (1-5)" in COLUNAS_DISPLAY
    assert "Severidade da Ameaça (1-5)" not in COLUNAS_DISPLAY
    decisoes = set(df["Strategic Decision"])
    assert decisoes <= {"Funded Mitigation", "Risk Accepted (Not Funded)"}, decisoes
    assert "Mitigação Financiada" not in decisoes
    assert set(df["Risk Appetite Tolerance"]) <= {"Within Appetite", "Outside Appetite"}


def test_residual_mitigated_reduces_risk():
    SAMPLE = [
        {"asset_name": "ERP SAP Core", "dept": "Finance", "asset_value": 450000, "vulnerability": "Admin Access without MFA", "framework": "ISO 27001 A.8.5", "rgpd": True, "threat_level": 4, "mitigation_cost": 20000},
        {"asset_name": "E-Commerce Platform", "dept": "Operations", "asset_value": 650000, "vulnerability": "Missing Critical Patches", "framework": "NIST CSF PR.PS-1", "rgpd": True, "threat_level": 5, "mitigation_cost": 50000},
        {"asset_name": "Website (WordPress)", "dept": "Marketing", "asset_value": 40000, "vulnerability": "Outdated Plugins", "framework": "ISO 27001 A.8.8", "rgpd": False, "threat_level": 4, "mitigation_cost": 4000},
    ]
    df = processar_priorizacao_risco(SAMPLE, 0.30, 5000000, 120000, 0.02, 90, 50000)
    for _, row in df.iterrows():
        if row["Strategic Decision"] == "Funded Mitigation":
            assert row["Residual Risk (€)"] < row["Inherent Risk (€)"]
        else:
            assert row["Residual Risk (€)"] == row["Inherent Risk (€)"]
