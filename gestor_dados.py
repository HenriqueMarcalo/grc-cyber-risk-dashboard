# -----------------------------------------------------------------------------
# Gestor de Dados
# Processamento: dados de demonstração, importação de ficheiros (CSV/Excel),
# aliases/normalização e mapeamentos do editor.
# -----------------------------------------------------------------------------
import pandas as pd
import streamlit as st

assets_default = [
    {"asset_name": "ERP SAP Core", "dept": "Financeiro", "asset_value": 450000, "vulnerability": "Acesso Admin sem MFA", "framework": "ISO 27001 A.8.5", "rgpd": True, "threat_level": 4, "mitigation_cost": 20000},
    {"asset_name": "Gateway API Pagamentos", "dept": "Financeiro", "asset_value": 300000, "vulnerability": "TLS 1.0 Obsoleto", "framework": "PCI-DSS v4 4.1", "rgpd": True, "threat_level": 3, "mitigation_cost": 15000},
    {"asset_name": "Servidor de Faturação", "dept": "Financeiro", "asset_value": 120000, "vulnerability": "Sem Backups Diários", "framework": "ISO 27001 A.8.13", "rgpd": False, "threat_level": 3, "mitigation_cost": 5000},
    {"asset_name": "Portal Workday Cloud", "dept": "Recursos Humanos", "asset_value": 180000, "vulnerability": "Permissões de Ex-Colaboradores", "framework": "ISO 27001 A.6.8", "rgpd": True, "threat_level": 2, "mitigation_cost": 8000},
    {"asset_name": "BD Avaliação Desempenho", "dept": "Recursos Humanos", "asset_value": 60000, "vulnerability": "Dados não cifrados", "framework": "NIST CSF PR.DS-1", "rgpd": True, "threat_level": 2, "mitigation_cost": 12000},
    {"asset_name": "Plataforma E-Commerce", "dept": "Operações", "asset_value": 650000, "vulnerability": "Sem Patches Críticos", "framework": "NIST CSF PR.PS-1", "rgpd": True, "threat_level": 5, "mitigation_cost": 50000},
    {"asset_name": "Servidor Logística", "dept": "Operações", "asset_value": 220000, "vulnerability": "Ausência de SIEM", "framework": "ISO 27001 A.8.16", "rgpd": False, "threat_level": 3, "mitigation_cost": 40000},
    {"asset_name": "Repositório Git (CI/CD)", "dept": "Operações", "asset_value": 140000, "vulnerability": "Credenciais API Hardcoded", "framework": "OWASP CI/CD Flaws", "rgpd": False, "threat_level": 4, "mitigation_cost": 25000},
    {"asset_name": "Website (WordPress)", "dept": "Marketing", "asset_value": 40000, "vulnerability": "Plugins Desatualizados", "framework": "ISO 27001 A.8.8", "rgpd": False, "threat_level": 4, "mitigation_cost": 4000},
    {"asset_name": "CRM HubSpot Sync", "dept": "Marketing", "asset_value": 210000, "vulnerability": "Exportação sem Logs", "framework": "RGPD Artigo 32º", "rgpd": True, "threat_level": 3, "mitigation_cost": 18000},
    {"asset_name": "Servidor de Patentes", "dept": "I&D", "asset_value": 500000, "vulnerability": "Rede Wi-Fi não segregada", "framework": "ISO 27001 A.8.20", "rgpd": False, "threat_level": 4, "mitigation_cost": 30000},
    {"asset_name": "Estações CAD Engenharia", "dept": "I&D", "asset_value": 90000, "vulnerability": "Antivírus desativado", "framework": "NIST CSF PR.RE-1", "rgpd": False, "threat_level": 2, "mitigation_cost": 6000},
]

ALIASES_COLUNAS = {
    "asset_name": ["asset_name", "ativo", "ativo auditado", "nome do ativo", "name"],
    "dept": ["dept", "departamento"],
    "asset_value": ["asset_value", "valor do ativo", "valor do ativo (€)", "valor", "value"],
    "vulnerability": ["vulnerability", "vulnerabilidade"],
    "framework": ["framework", "norma", "norma/framework"],
    "rgpd": ["rgpd", "gdpr", "dados pessoais"],
    "threat_level": ["threat_level", "nivel de ameaca", "nível de ameaça", "ameaca", "threat"],
    "mitigation_cost": ["mitigation_cost", "custo de correcao", "custo de correção", "custo", "cost"],
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
            st.error("Para importar ficheiros Excel (xlsx) é necessário instalar o openpyxl: `pip install openpyxl`. Use um ficheiro CSV ou os dados de demonstração entretanto.")
        else:
            st.error(f"Não foi possível ler o ficheiro: {erro}")
        return assets_default, True
    except Exception as erro:
        st.error(f"Não foi possível ler o ficheiro: {erro}")
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
        st.error(f"Faltam colunas no ficheiro: {', '.join(faltam)}")
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
            df_importado[coluna] = "N/D"
        df_importado[coluna] = df_importado[coluna].fillna("N/D")

    return df_importado.to_dict("records"), False


MAPA_EDITOR_PARA_RAW = {"Ativo Auditado": "asset_name", "Departamento": "dept", "Valor do Ativo (€)": "asset_value", "Vulnerabilidade": "vulnerability", "Norma/Framework": "framework", "Severidade da Ameaça (1-5)": "threat_level", "Custo de Correção (€)": "mitigation_cost"}
COLUNAS_RAW = ["asset_name", "dept", "asset_value", "vulnerability", "framework", "rgpd", "threat_level", "mitigation_cost"]


def _registos_iguais(a, b):
    if len(a) != len(b):
        return False
    return sorted(tuple(sorted(r.items())) for r in a) == sorted(tuple(sorted(r.items())) for r in b)
