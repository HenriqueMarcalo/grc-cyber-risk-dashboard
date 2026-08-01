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
# 1. Configuração Executiva da Página
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Enterprise GRC & Risk Prioritization")

st.title("Enterprise Cyber Risk & GRC Governance")
st.info("**Plataforma de Governação e Priorização de Risco:** Simulação avançada de alocação de orçamento com base no impacto financeiro, nível de ameaça, apetite ao risco e custo de remediação.")
st.write("")

if "assets_editados" not in st.session_state:
    st.session_state["assets_editados"] = assets_default

# -----------------------------------------------------------------------------
# 4. Painel Lateral (Sidebar)
# -----------------------------------------------------------------------------
st.sidebar.header("Filtros de Visão")
# Proteção contra valores nulos (NaN) ao criar a lista de departamentos
deps_brutos = [asset.get("dept") for asset in st.session_state["assets_editados"]]
lista_departamentos = list(set([str(d).strip() for d in deps_brutos if pd.notna(d) and str(d).strip() not in ("", "nan")]))

departamentos_opcoes = ["Todos os Departamentos"] + sorted(lista_departamentos)
dept_selecionado = st.sidebar.selectbox("Focar Análise no Departamento:", departamentos_opcoes)

st.sidebar.divider()

st.sidebar.header("Parametrização de Negócio")
faturacao_anual = st.sidebar.number_input("Faturação Anual (€)", value=5000000, step=1000000)

maturidade = st.sidebar.selectbox(
    "Nível de Controlo Interno (Probabilidade):",
    options=["Baixo (Incidente 50%)", "Médio (Incidente 30%)", "Alto (Incidente 15%)"],
    index=1
)
prob_dict = {"Baixo (Incidente 50%)": 0.50, "Médio (Incidente 30%)": 0.30, "Alto (Incidente 15%)": 0.15}
probabilidade_incidente = prob_dict[maturidade]

gravidade_rgpd = st.sidebar.radio(
    "Cenário de Exposição RGPD:",
    options=["Infração Standard (2%)", "Infração Grave (4%)"]
)
multiplicador_rgpd = 0.04 if gravidade_rgpd == "Infração Grave (4%)" else 0.02

st.sidebar.divider()

st.sidebar.header("Apetite & Alocação de Capital")
apetite_risco = st.sidebar.number_input("Apetite ao Risco (€ Máx Aceitável)", value=50000, step=10000)
orcamento_global = st.sidebar.number_input("Orçamento Disponível para Remediação (€)", min_value=0, value=120000, step=10000)
eficacia_remediacao = st.sidebar.slider("Eficácia Esperada dos Controlos (%)", 10, 100, 90)

st.sidebar.divider()

st.sidebar.header("Origem dos Dados")
ficheiro_ativos = st.sidebar.file_uploader("Importar ativos (CSV/Excel)", type=["csv", "xlsx"])
template_csv = pd.DataFrame(assets_default).to_csv(index=False).encode("utf-8")
st.sidebar.download_button(label="Descarregar modelo CSV", data=template_csv, file_name="modelo_ativos.csv", mime="text/csv")

if st.sidebar.button("Repor dados de demonstração", width="stretch"):
    st.session_state["usar_demo"] = True
    st.session_state["origem_ident"] = ("demo", None)
    st.session_state["assets_editados"] = assets_default
    if "editor_ativos" in st.session_state:
        del st.session_state["editor_ativos"]
    st.rerun()

if "usar_demo" in st.session_state:
    usar_demo = st.sidebar.checkbox("Usar dados de demonstração", key="usar_demo")
else:
    usar_demo = st.sidebar.checkbox("Usar dados de demonstração", value=(ficheiro_ativos is None), key="usar_demo")

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
# 5. Motor Analítico Global (aplicação)
# -----------------------------------------------------------------------------
df_grc_completo = processar_priorizacao_risco(
    st.session_state["assets_editados"], probabilidade_incidente, faturacao_anual, orcamento_global, multiplicador_rgpd, eficacia_remediacao, apetite_risco
)

tab_analise, tab_registo = st.tabs(["📊 Análise Executiva", "🗂️ Master Registry"])

with tab_analise:
    if df_grc_completo.empty:
        st.warning("Não existem dados para processar. Adicione ativos no registo de conformidade abaixo.")
    else:
        if dept_selecionado == "Todos os Departamentos":
            df_grc_view = df_grc_completo
        else:
            df_grc_view = df_grc_completo[df_grc_completo["Departamento"] == dept_selecionado]

        # -----------------------------------------------------------------------------
        # 6. KPIs Executivos
        # -----------------------------------------------------------------------------
        risco_inerente_total = df_grc_view["Risco Inerente (€)"].sum()
        risco_residual_total = df_grc_view["Risco Residual (€)"].sum()
        risco_mitigado_total = risco_inerente_total - risco_residual_total
        df_financiados = df_grc_view[df_grc_view["Decisão Estratégica"] == "Mitigação Financiada"]
        financiados = len(df_financiados)
        orcamento_gasto = df_financiados["Custo de Correção (€)"].sum() if not df_financiados.empty else 0
        roi_real = ((risco_mitigado_total - orcamento_gasto) / orcamento_gasto) * 100 if orcamento_gasto > 0 else 0

        st.subheader("Sumário Executivo de Exposição")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Risco Inerente", f"€ {risco_inerente_total:,.0f}")
        col2.metric("Risco Residual", f"€ {risco_residual_total:,.0f}", f"-€ {risco_mitigado_total:,.0f} Mitigado")
        col3.metric("Ações Financiadas", f"{financiados} / {len(df_grc_view)} Ativos")
        col4.metric(f"ROI do Orçamento", f"{roi_real:.0f}%", f"Gasto: € {orcamento_gasto:,.0f}")

        if dept_selecionado == "Todos os Departamentos":
            percentagem_gasta = (orcamento_gasto / orcamento_global) if orcamento_global > 0 else 0
            st.progress(percentagem_gasta, text=f"Utilização de Orçamento Global: {percentagem_gasta*100:.1f}% (€ {orcamento_gasto:,.0f} de € {orcamento_global:,.0f})")

        riscos_ativos_perigosos = df_grc_view[(df_grc_view["Decisão Estratégica"] == "Risco Aceite (Não Financiado)") & (df_grc_view["Tolerância (Apetite)"] == "Fora do Apetite")]
        if not riscos_ativos_perigosos.empty:
            top_perigos = riscos_ativos_perigosos.sort_values(by="Risco Residual (€)", ascending=False).head(2)
            alert_text = "**ALERTA DA ADMINISTRAÇÃO:** Os seguintes ativos críticos ficaram sem financiamento e excedem o nosso apetite ao risco:\n"
            for _, row in top_perigos.iterrows():
                alert_text += f"- **{row['Ativo Auditado']}** ({row['Departamento']}): Exposição de **€ {row['Risco Residual (€)']:,.0f}**\n"
            st.error(alert_text)
        elif orcamento_gasto > 0:
            st.success("Todos os riscos críticos não financiados estão contidos dentro do limite de apetite ao risco estabelecido.")

        # -----------------------------------------------------------------------------
        # 6.1 Avisos de Qualidade de Dados
        # -----------------------------------------------------------------------------
        problemas_qualidade = []
        if (df_grc_view["Valor do Ativo (€)"] <= 0).any():
            problemas_qualidade.append(f"{int((df_grc_view['Valor do Ativo (€)'] <= 0).sum())} ativo(s) com valor do ativo igual ou abaixo de 0")
        if (df_grc_view["Custo de Correção (€)"] < 0).any():
            problemas_qualidade.append(f"{int((df_grc_view['Custo de Correção (€)'] < 0).sum())} ativo(s) com custo de correção negativo")
        if (df_grc_view["Departamento"] == "Sem Departamento").any():
            problemas_qualidade.append(f"{int((df_grc_view['Departamento'] == 'Sem Departamento').sum())} ativo(s) sem departamento definido")
        if problemas_qualidade:
            st.warning("**Qualidade dos dados:** " + "; ".join(problemas_qualidade))
        st.divider()

        # -----------------------------------------------------------------------------
        # 7. Visualização de Dados
        # -----------------------------------------------------------------------------
        st.subheader("Análise Analítica de Exposição")
        col_chart1, col_chart2 = st.columns(2)
        paleta_cores_departamentos = {"Financeiro": "#3366CC", "Recursos Humanos": "#DC3912", "Operações": "#FF9900", "Marketing": "#109618", "I&D": "#990099"}

        with col_chart1:
            if not df_grc_view.empty:
                fig_scatter = px.scatter(df_grc_view, x="Risco Inerente (€)", y="Severidade da Ameaça (1-5)", size="Risco Inerente (€)", color="Departamento", color_discrete_map=paleta_cores_departamentos, hover_name="Ativo Auditado", size_max=35)
                fig_scatter.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), xaxis=dict(tickformat="€,.0f", title="Impacto Financeiro (€)"), yaxis=dict(tickvals=[1, 2, 3, 4, 5]))
                fig_scatter.update_traces(hovertemplate="<b>%{hovertext}</b><br>Impacto: € %{x:,.0f}<br>Ameaça: %{y}<extra></extra>")
                st.plotly_chart(fig_scatter, width="stretch")

        with col_chart2:
            if not df_grc_view.empty:
                fig_pie = px.pie(df_grc_view, names="Decisão Estratégica", values="Risco Inerente (€)", color="Decisão Estratégica", color_discrete_map={"Mitigação Financiada": "#109618", "Risco Aceite (Não Financiado)": "#FF9900"}, hole=0.4)
                fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>Exposição: € %{value:,.0f}<br>%{percent:.1%}<extra></extra>")
                fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pie, width="stretch")
        st.divider()

        # -----------------------------------------------------------------------------
        # 8. Business Case
        # -----------------------------------------------------------------------------
        if dept_selecionado == "Todos os Departamentos":
            col_biz1, col_biz2 = st.columns([1, 2])
            with col_biz1:
                metrics_df = pd.DataFrame({"Métrica": ["Risco Inicial", "Mitigado", "Residual Final", "Orçamento Gasto", "Retorno (ROI)"], "Valor Estimado": [f"€ {risco_inerente_total:,.0f}", f"€ {risco_mitigado_total:,.0f}", f"€ {risco_residual_total:,.0f}", f"€ {orcamento_gasto:,.0f}", f"{roi_real:.1f}%"]})
                st.dataframe(metrics_df, width="stretch", hide_index=True)
            with col_biz2:
                dept_comparison = df_grc_view.groupby("Departamento")[["Risco Inerente (€)", "Risco Residual (€)"]].sum().reset_index()
                fig_melted = pd.melt(dept_comparison, id_vars=["Departamento"], value_vars=["Risco Inerente (€)", "Risco Residual (€)"], var_name="Cenário", value_name="Exposição (€)")
                fig_compare = px.bar(fig_melted, x="Departamento", y="Exposição (€)", color="Cenário", barmode="group", template="plotly_white", color_discrete_sequence=["#DC3912", "#109618"])
                fig_compare.update_traces(hovertemplate="<b>%{x}</b> - %{fullData.name}<br>Exposição: € %{y:,.0f}<extra></extra>")
                fig_compare.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(tickformat="€,.0f"))
                st.plotly_chart(fig_compare, width="stretch")
            st.divider()

with tab_registo:
    st.subheader("Registo de Conformidade Corporativa (Master Registry)")
    st.caption("Edite, adicione ou remova linhas. As alterações recalculam automaticamente os riscos.")

    # A formatação em "C-style" garante que não aparecem os tais caracteres `0f..`
    df_tabela_editada = st.data_editor(
        df_grc_completo,
        num_rows="dynamic",
        key="editor_ativos",
        hide_index=True,
        width="stretch",
        column_config={
            "Valor do Ativo (€)": st.column_config.NumberColumn("Valor do Ativo (€)", min_value=0, step=1000, format="€ %d"),
            "Custo de Correção (€)": st.column_config.NumberColumn("Custo de Correção (€)", min_value=0, step=1000, format="€ %d"),
            "rgpd": st.column_config.CheckboxColumn("RGPD"),
            "Severidade da Ameaça (1-5)": st.column_config.NumberColumn("Severidade da Ameaça (1-5)", min_value=1, max_value=5, step=1),
            "Risco Inerente (€)": st.column_config.NumberColumn("Risco Inerente (€)", disabled=True, format="€ %d"),
            "Risco Residual (€)": st.column_config.NumberColumn("Risco Residual (€)", disabled=True, format="€ %d"),
            "Decisão Estratégica": st.column_config.TextColumn("Decisão Estratégica", disabled=True),
            "Tolerância (Apetite)": st.column_config.TextColumn("Tolerância (Apetite)", disabled=True),
        },
    )

    df_extracao = df_tabela_editada.rename(columns=MAPA_EDITOR_PARA_RAW)
    df_extracao = df_extracao[[c for c in COLUNAS_RAW if c in df_extracao.columns]]

    # Proteções contra linhas em branco introduzidas pelo utilizador
    df_extracao["asset_name"] = df_extracao["asset_name"].fillna("").astype(str)
    df_extracao = df_extracao[df_extracao["asset_name"].str.strip() != ""]

    df_extracao["asset_value"] = pd.to_numeric(df_extracao["asset_value"], errors="coerce").fillna(0).astype(int)
    df_extracao["mitigation_cost"] = pd.to_numeric(df_extracao["mitigation_cost"], errors="coerce").fillna(0).astype(int)
    df_extracao["threat_level"] = pd.to_numeric(df_extracao["threat_level"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    df_extracao["rgpd"] = df_extracao["rgpd"].fillna(False).astype(bool)
    df_extracao["vulnerability"] = df_extracao["vulnerability"].fillna("N/D").astype(str)
    df_extracao["framework"] = df_extracao["framework"].fillna("N/D").astype(str)

    df_extracao["dept"] = df_extracao["dept"].fillna("Sem Departamento").astype(str)
    df_extracao.loc[df_extracao["dept"].str.strip().isin(["", "nan"]), "dept"] = "Sem Departamento"
    df_extracao["asset_name"] = df_extracao["asset_name"].astype(str)

    novos_ativos_raw = df_extracao.to_dict("records")

    if not _registos_iguais(novos_ativos_raw, st.session_state["assets_editados"]):
        st.session_state["assets_editados"] = novos_ativos_raw
        st.rerun()

    csv_export = df_tabela_editada.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descarregar Master Registry (CSV)",
        data=csv_export,
        file_name="master_registry_grc.csv",
        mime="text/csv",
        width="stretch",
    )
