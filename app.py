import streamlit as st
import pandas as pd
import plotly.express as px

from motor_risco import processar_priorizacao_risco
from gestor_dados import (
    assets_default,
    carregar_ativos_do_upload,
    MAPA_EDITOR_PARA_RAW,
    COLUNAS_RAW,
    _registos_iguais,
)

# -----------------------------------------------------------------------------
# 1. Executive Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Enterprise GRC & Risk Prioritization")

st.title("Enterprise Cyber Risk & GRC Governance")
st.info("**Governance, Risk & Compliance platform:** Advanced simulation of budget allocation based on financial impact, threat level, risk appetite and remediation cost.")
st.write("")

if "assets_editados" not in st.session_state:
    st.session_state["assets_editados"] = assets_default

# -----------------------------------------------------------------------------
# 4. Sidebar
# -----------------------------------------------------------------------------
st.sidebar.header("View Filters")
# Guard against null (NaN) values when building the department list
deps_brutos = [asset.get("dept") for asset in st.session_state["assets_editados"]]
lista_departamentos = list(set([str(d).strip() for d in deps_brutos if pd.notna(d) and str(d).strip() not in ("", "nan")]))

departamentos_opcoes = ["All Departments"] + sorted(lista_departamentos)
dept_selecionado = st.sidebar.selectbox("Focus Analysis on Department:", departamentos_opcoes)

st.sidebar.divider()

st.sidebar.header("Business Parameters")
faturacao_anual = st.sidebar.number_input("Annual Revenue (€)", value=5000000, step=1000000)

maturidade = st.sidebar.selectbox(
    "Internal Control Level (Probability):",
    options=["Low (50% incident)", "Medium (30% incident)", "High (15% incident)"],
    index=1
)
prob_dict = {"Low (50% incident)": 0.50, "Medium (30% incident)": 0.30, "High (15% incident)": 0.15}
probabilidade_incidente = prob_dict[maturidade]

gravidade_rgpd = st.sidebar.radio(
    "GDPR Exposure Scenario:",
    options=["Standard Breach (2%)", "Severe Breach (4%)"]
)
multiplicador_rgpd = 0.04 if gravidade_rgpd == "Severe Breach (4%)" else 0.02

st.sidebar.divider()

st.sidebar.header("Risk Appetite & Capital Allocation")
apetite_risco = st.sidebar.number_input("Risk Appetite (€ Max Acceptable)", value=50000, step=10000)
orcamento_global = st.sidebar.number_input("Remediation Budget Available (€)", min_value=0, value=120000, step=10000)
eficacia_remediacao = st.sidebar.slider("Expected Control Effectiveness (%)", 10, 100, 90)

st.sidebar.divider()

st.sidebar.header("Data Source")
ficheiro_ativos = st.sidebar.file_uploader("Import assets (CSV/Excel)", type=["csv", "xlsx"])
template_csv = pd.DataFrame(assets_default).to_csv(index=False).encode("utf-8")
st.sidebar.download_button(label="Download CSV template", data=template_csv, file_name="asset_template.csv", mime="text/csv")

if st.sidebar.button("Reset demo data", width="stretch"):
    st.session_state["usar_demo"] = True
    st.session_state["origem_ident"] = ("demo", None)
    st.session_state["assets_editados"] = assets_default
    if "editor_ativos" in st.session_state:
        del st.session_state["editor_ativos"]
    st.rerun()

if "usar_demo" in st.session_state:
    usar_demo = st.sidebar.checkbox("Use demo data", key="usar_demo")
else:
    usar_demo = st.sidebar.checkbox("Use demo data", value=(ficheiro_ativos is None), key="usar_demo")

if ficheiro_ativos is not None and not usar_demo:
    ativos_base, erro_importacao = carregar_ativos_do_upload(ficheiro_ativos)
    origem_ident = ("upload", getattr(ficheiro_ativos, "file_id", id(ficheiro_ativos)))
else:
    ativos_base = assets_default
    origem_ident = ("demo", None)

if st.session_state.get("origem_ident") != origem_ident:
    st.session_state["origem_ident"] = origem_ident
    st.session_state["assets_editados"] = ativos_base
    if "editor_ativos" in st.session_state:
        del st.session_state["editor_ativos"]

# -----------------------------------------------------------------------------
# 5. Global Analytical Engine (application)
# -----------------------------------------------------------------------------
df_grc_completo = processar_priorizacao_risco(
    st.session_state["assets_editados"], probabilidade_incidente, faturacao_anual, orcamento_global, multiplicador_rgpd, eficacia_remediacao, apetite_risco
)

tab_analise, tab_registo = st.tabs(["📊 Executive Analysis", "🗂️ Master Registry"])

with tab_analise:
    if df_grc_completo.empty:
        st.warning("No data available to process. Add assets in the compliance registry below.")
    else:
        if dept_selecionado == "All Departments":
            df_grc_view = df_grc_completo
        else:
            df_grc_view = df_grc_completo[df_grc_completo["Department"] == dept_selecionado]

        # -----------------------------------------------------------------------------
        # 6. Executive KPIs
        # -----------------------------------------------------------------------------
        risco_inerente_total = df_grc_view["Inherent Risk (€)"].sum()
        risco_residual_total = df_grc_view["Residual Risk (€)"].sum()
        risco_mitigado_total = risco_inerente_total - risco_residual_total
        df_financiados = df_grc_view[df_grc_view["Strategic Decision"] == "Funded Mitigation"]
        financiados = len(df_financiados)
        orcamento_gasto = df_financiados["Mitigation Cost (€)"].sum() if not df_financiados.empty else 0
        roi_real = ((risco_mitigado_total - orcamento_gasto) / orcamento_gasto) * 100 if orcamento_gasto > 0 else 0

        st.subheader("Executive Exposure Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Inherent Risk", f"€ {risco_inerente_total:,.0f}")
        col2.metric("Residual Risk", f"€ {risco_residual_total:,.0f}", f"-€ {risco_mitigado_total:,.0f} Mitigated")
        col3.metric("Funded Actions", f"{financiados} / {len(df_grc_view)} Assets")
        col4.metric("Budget ROI", f"{roi_real:.0f}%", f"Spent: € {orcamento_gasto:,.0f}")

        if dept_selecionado == "All Departments":
            percentagem_gasta = (orcamento_gasto / orcamento_global) if orcamento_global > 0 else 0
            st.progress(percentagem_gasta, text=f"Global Budget Utilization: {percentagem_gasta*100:.1f}% (€ {orcamento_gasto:,.0f} of € {orcamento_global:,.0f})")

        riscos_ativos_perigosos = df_grc_view[(df_grc_view["Strategic Decision"] == "Risk Accepted (Not Funded)") & (df_grc_view["Risk Appetite Tolerance"] == "Outside Appetite")]
        if not riscos_ativos_perigosos.empty:
            top_perigos = riscos_ativos_perigosos.sort_values(by="Residual Risk (€)", ascending=False).head(2)
            alert_text = "**ADMINISTRATION ALERT:** The following critical assets are unfunded and exceed our risk appetite:\n"
            for _, row in top_perigos.iterrows():
                alert_text += f"- **{row['Asset']}** ({row['Department']}): Exposure of **€ {row['Residual Risk (€)']:,.0f}**\n"
            st.error(alert_text)
        elif orcamento_gasto > 0:
            st.success("All critical unfunded risks are contained within the established risk appetite limit.")

        # -----------------------------------------------------------------------------
        # 6.1 Data Quality Warnings
        # -----------------------------------------------------------------------------
        problemas_qualidade = []
        if (df_grc_view["Asset Value (€)"] <= 0).any():
            problemas_qualidade.append(f"{int((df_grc_view['Asset Value (€)'] <= 0).sum())} asset(s) with asset value equal to or below 0")
        if (df_grc_view["Mitigation Cost (€)"] < 0).any():
            problemas_qualidade.append(f"{int((df_grc_view['Mitigation Cost (€)'] < 0).sum())} asset(s) with negative mitigation cost")
        if (df_grc_view["Department"] == "No Department").any():
            problemas_qualidade.append(f"{int((df_grc_view['Department'] == 'No Department').sum())} asset(s) without department assigned")
        if problemas_qualidade:
            st.warning("**Data quality:** " + "; ".join(problemas_qualidade))
        st.divider()

        # -----------------------------------------------------------------------------
        # 7. Data Visualization
        # -----------------------------------------------------------------------------
        st.subheader("Analytical Exposure Analysis")
        col_chart1, col_chart2 = st.columns(2)
        paleta_cores_departamentos = {"Finance": "#3366CC", "Human Resources": "#DC3912", "Operations": "#FF9900", "Marketing": "#109618", "R&D": "#990099"}

        with col_chart1:
            if not df_grc_view.empty:
                fig_scatter = px.scatter(df_grc_view, x="Inherent Risk (€)", y="Threat Severity (1-5)", size="Inherent Risk (€)", color="Department", color_discrete_map=paleta_cores_departamentos, hover_name="Asset", size_max=35)
                fig_scatter.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), xaxis=dict(tickformat="€,.0f", title="Financial Impact (€)"), yaxis=dict(tickvals=[1, 2, 3, 4, 5]))
                fig_scatter.update_traces(hovertemplate="<b>%{hovertext}</b><br>Impact: € %{x:,.0f}<br>Threat: %{y}<extra></extra>")
                st.plotly_chart(fig_scatter, width="stretch")

        with col_chart2:
            if not df_grc_view.empty:
                fig_pie = px.pie(df_grc_view, names="Strategic Decision", values="Inherent Risk (€)", color="Strategic Decision", color_discrete_map={"Funded Mitigation": "#109618", "Risk Accepted (Not Funded)": "#FF9900"}, hole=0.4)
                fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>Exposure: € %{value:,.0f}<br>%{percent:.1%}<extra></extra>")
                fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pie, width="stretch")
        st.divider()

        # -----------------------------------------------------------------------------
        # 8. Business Case
        # -----------------------------------------------------------------------------
        if dept_selecionado == "All Departments":
            col_biz1, col_biz2 = st.columns([1, 2])
            with col_biz1:
                metrics_df = pd.DataFrame({"Metric": ["Initial Risk", "Mitigated", "Final Residual", "Budget Spent", "Return (ROI)"], "Estimated Value": [f"€ {risco_inerente_total:,.0f}", f"€ {risco_mitigado_total:,.0f}", f"€ {risco_residual_total:,.0f}", f"€ {orcamento_gasto:,.0f}", f"{roi_real:.1f}%"]})
                st.dataframe(metrics_df, width="stretch", hide_index=True)
            with col_biz2:
                dept_comparison = df_grc_view.groupby("Department")[["Inherent Risk (€)", "Residual Risk (€)"]].sum().reset_index()
                fig_melted = pd.melt(dept_comparison, id_vars=["Department"], value_vars=["Inherent Risk (€)", "Residual Risk (€)"], var_name="Scenario", value_name="Exposure (€)")
                fig_compare = px.bar(fig_melted, x="Department", y="Exposure (€)", color="Scenario", barmode="group", template="plotly_white", color_discrete_sequence=["#DC3912", "#109618"])
                fig_compare.update_traces(hovertemplate="<b>%{x}</b> - %{fullData.name}<br>Exposure: € %{y:,.0f}<extra></extra>")
                fig_compare.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(tickformat="€,.0f"))
                st.plotly_chart(fig_compare, width="stretch")
            st.divider()

with tab_registo:
    st.subheader("Corporate Compliance Registry (Master Registry)")
    st.caption("Edit, add or remove rows. Changes recalculate all risks in real time.")

    # "C-style" formatting avoids the stray `0f..` characters in displayed values
    df_tabela_editada = st.data_editor(
        df_grc_completo,
        num_rows="dynamic",
        key="editor_ativos",
        hide_index=True,
        width="stretch",
        column_config={
            "Asset Value (€)": st.column_config.NumberColumn("Asset Value (€)", min_value=0, step=1000, format="€ %d"),
            "Mitigation Cost (€)": st.column_config.NumberColumn("Mitigation Cost (€)", min_value=0, step=1000, format="€ %d"),
            "rgpd": st.column_config.CheckboxColumn("GDPR"),
            "Threat Severity (1-5)": st.column_config.NumberColumn("Threat Severity (1-5)", min_value=1, max_value=5, step=1),
            "Inherent Risk (€)": st.column_config.NumberColumn("Inherent Risk (€)", disabled=True, format="€ %d"),
            "Residual Risk (€)": st.column_config.NumberColumn("Residual Risk (€)", disabled=True, format="€ %d"),
            "Strategic Decision": st.column_config.TextColumn("Strategic Decision", disabled=True),
            "Risk Appetite Tolerance": st.column_config.TextColumn("Risk Appetite Tolerance", disabled=True),
        },
    )

    df_extracao = df_tabela_editada.rename(columns=MAPA_EDITOR_PARA_RAW)
    df_extracao = df_extracao[[c for c in COLUNAS_RAW if c in df_extracao.columns]]

    # Protections against blank rows introduced by the user
    df_extracao["asset_name"] = df_extracao["asset_name"].fillna("").astype(str)
    df_extracao = df_extracao[df_extracao["asset_name"].str.strip() != ""]

    df_extracao["asset_value"] = pd.to_numeric(df_extracao["asset_value"], errors="coerce").fillna(0).astype(int)
    df_extracao["mitigation_cost"] = pd.to_numeric(df_extracao["mitigation_cost"], errors="coerce").fillna(0).astype(int)
    df_extracao["threat_level"] = pd.to_numeric(df_extracao["threat_level"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    df_extracao["rgpd"] = df_extracao["rgpd"].fillna(False).astype(bool)
    df_extracao["vulnerability"] = df_extracao["vulnerability"].fillna("N/A").astype(str)
    df_extracao["framework"] = df_extracao["framework"].fillna("N/A").astype(str)

    df_extracao["dept"] = df_extracao["dept"].fillna("No Department").astype(str)
    df_extracao.loc[df_extracao["dept"].str.strip().isin(["", "nan"]), "dept"] = "No Department"
    df_extracao["asset_name"] = df_extracao["asset_name"].astype(str)

    novos_ativos_raw = df_extracao.to_dict("records")

    if not _registos_iguais(novos_ativos_raw, st.session_state["assets_editados"]):
        st.session_state["assets_editados"] = novos_ativos_raw
        st.rerun()

    csv_export = df_tabela_editada.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Master Registry (CSV)",
        data=csv_export,
        file_name="master_registry_grc.csv",
        mime="text/csv",
        width="stretch",
    )
