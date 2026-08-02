# -----------------------------------------------------------------------------
# Data Manager
# Processing: demo data, file import (CSV/Excel), aliases/normalization and
# data-editor mappings.
# -----------------------------------------------------------------------------
import pandas as pd
import streamlit as st

assets_default = [
    {"asset_name": "ERP SAP Core", "dept": "Finance", "asset_value": 450000, "vulnerability": "Admin Access without MFA", "framework": "ISO 27001 A.8.5", "rgpd": True, "threat_level": 4, "mitigation_cost": 20000},
    {"asset_name": "Payments API Gateway", "dept": "Finance", "asset_value": 300000, "vulnerability": "Obsolete TLS 1.0", "framework": "PCI-DSS v4 4.1", "rgpd": True, "threat_level": 3, "mitigation_cost": 15000},
    {"asset_name": "Billing Server", "dept": "Finance", "asset_value": 120000, "vulnerability": "No Daily Backups", "framework": "ISO 27001 A.8.13", "rgpd": False, "threat_level": 3, "mitigation_cost": 5000},
    {"asset_name": "Workday Cloud Portal", "dept": "Human Resources", "asset_value": 180000, "vulnerability": "Former Employee Permissions", "framework": "ISO 27001 A.6.8", "rgpd": True, "threat_level": 2, "mitigation_cost": 8000},
    {"asset_name": "Performance Review DB", "dept": "Human Resources", "asset_value": 60000, "vulnerability": "Unencrypted Data", "framework": "NIST CSF PR.DS-1", "rgpd": True, "threat_level": 2, "mitigation_cost": 12000},
    {"asset_name": "E-Commerce Platform", "dept": "Operations", "asset_value": 650000, "vulnerability": "Missing Critical Patches", "framework": "NIST CSF PR.PS-1", "rgpd": True, "threat_level": 5, "mitigation_cost": 50000},
    {"asset_name": "Logistics Server", "dept": "Operations", "asset_value": 220000, "vulnerability": "No SIEM Coverage", "framework": "ISO 27001 A.8.16", "rgpd": False, "threat_level": 3, "mitigation_cost": 40000},
    {"asset_name": "Git Repository (CI/CD)", "dept": "Operations", "asset_value": 140000, "vulnerability": "Hardcoded API Credentials", "framework": "OWASP CI/CD Flaws", "rgpd": False, "threat_level": 4, "mitigation_cost": 25000},
    {"asset_name": "Website (WordPress)", "dept": "Marketing", "asset_value": 40000, "vulnerability": "Outdated Plugins", "framework": "ISO 27001 A.8.8", "rgpd": False, "threat_level": 4, "mitigation_cost": 4000},
    {"asset_name": "HubSpot CRM Sync", "dept": "Marketing", "asset_value": 210000, "vulnerability": "Export Without Logs", "framework": "GDPR Art. 32", "rgpd": True, "threat_level": 3, "mitigation_cost": 18000},
    {"asset_name": "Patent Server", "dept": "R&D", "asset_value": 500000, "vulnerability": "Non-segregated Wi-Fi Network", "framework": "ISO 27001 A.8.20", "rgpd": False, "threat_level": 4, "mitigation_cost": 30000},
    {"asset_name": "CAD Engineering Stations", "dept": "R&D", "asset_value": 90000, "vulnerability": "Antivirus Disabled", "framework": "NIST CSF PR.RE-1", "rgpd": False, "threat_level": 2, "mitigation_cost": 6000},
]

ALIASES_COLUNAS = {
    "asset_name": ["asset_name", "asset", "asset name", "ativo", "ativo auditado", "nome do ativo", "name"],
    "dept": ["dept", "department", "departamento"],
    "asset_value": ["asset_value", "asset value", "asset value (€)", "valor do ativo", "valor do ativo (€)", "valor", "value"],
    "vulnerability": ["vulnerability", "vulnerabilidades", "vulnerabilidade"],
    "framework": ["framework", "norma", "norma/framework", "standard"],
    "rgpd": ["rgpd", "gdpr", "dados pessoais", "personal data"],
    "threat_level": ["threat_level", "threat severity", "threat severity (1-5)", "threat", "nivel de ameaca", "nível de ameaça", "ameaca"],
    "mitigation_cost": ["mitigation_cost", "mitigation cost", "mitigation cost (€)", "custo de correcao", "custo de correção", "custo", "cost"],
}


def _normalizar_nome(col):
    return str(col).strip().lower()


def _parse_bool(valor):
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "sim", "s", "yes", "y", "verdadeiro")
    return bool(valor)


@st.cache_data
def _ler_ficheiro_upload(uploaded_file):
    nome_ficheiro = uploaded_file.name.lower()
    if nome_ficheiro.endswith((".xlsx", ".xls")):
        import openpyxl
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def carregar_ativos_do_upload(uploaded_file):
    if uploaded_file is None:
        return assets_default, True

    try:
        df_importado = _ler_ficheiro_upload(uploaded_file)
    except ModuleNotFoundError as erro:
        if "openpyxl" in str(erro):
            st.error("To import Excel files (xlsx) you need to install openpyxl: `pip install openpyxl`. Use a CSV file or the demo data in the meantime.")
        else:
            st.error(f"Could not read the file: {erro}")
        return assets_default, True
    except Exception as erro:
        st.error(f"Could not read the file: {erro}")
        return assets_default, True

    renomear = {}
    for coluna in df_importado.columns:
        nome = _normalizar_nome(coluna)
        for chave, aliases in ALIASES_COLUNAS.items():
            if nome in aliases:
                renomear[coluna] = chave
                break
    df_importado = df_importado.rename(columns=renomear)

    obrigatorias = ["asset_name", "dept", "asset_value", "mitigation_cost"]
    faltam = [c for c in obrigatorias if c not in df_importado.columns]
    if faltam:
        st.error(f"Missing columns in the file: {', '.join(faltam)}")
        return assets_default, True

    df_importado["asset_value"] = pd.to_numeric(df_importado["asset_value"], errors="coerce").fillna(0)
    df_importado["mitigation_cost"] = pd.to_numeric(df_importado["mitigation_cost"], errors="coerce").fillna(0)

    if "threat_level" in df_importado.columns:
        df_importado["threat_level"] = pd.to_numeric(df_importado["threat_level"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    else:
        df_importado["threat_level"] = 3

    if "rgpd" in df_importado.columns:
        df_importado["rgpd"] = df_importado["rgpd"].map(_parse_bool)
    else:
        df_importado["rgpd"] = False

    for coluna in ["vulnerability", "framework"]:
        if coluna not in df_importado.columns:
            df_importado[coluna] = "N/A"
        df_importado[coluna] = df_importado[coluna].fillna("N/A")

    return df_importado.to_dict("records"), False


MAPA_EDITOR_PARA_RAW = {"Asset": "asset_name", "Department": "dept", "Asset Value (€)": "asset_value", "Vulnerability": "vulnerability", "Framework": "framework", "Threat Severity (1-5)": "threat_level", "Mitigation Cost (€)": "mitigation_cost"}
COLUNAS_RAW = ["asset_name", "dept", "asset_value", "vulnerability", "framework", "rgpd", "threat_level", "mitigation_cost"]


def _registos_iguais(a, b):
    if len(a) != len(b):
        return False
    return sorted(tuple(sorted(r.items())) for r in a) == sorted(tuple(sorted(r.items())) for r in b)
