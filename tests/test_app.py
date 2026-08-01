import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# 1) Smoke: a app corre sem exceções e expõe os widgets core
# ---------------------------------------------------------------------------
at = AppTest.from_file(os.path.join(PROJ, "app.py"), default_timeout=30)
at.run()
assert not at.exception, at.exception[0] if at.exception else None
assert len(at.dataframe) >= 2, "deve existir o editor (data_editor) e o business case"
assert len(at.download_button) >= 1, "deve existir o botão de descarregar"
assert len(at.button) >= 1, "deve existir o botão de reset"
assert len(at.tabs) == 2, "devem existir as 2 tabs (Análise / Master Registry)"
assert len(at.metric) >= 4, "devem existir os 4 KPIs"
assert len(at.get("plotly_chart")) >= 1, "devem existir gráficos"
print("1) smoke OK ->",
      f"dataframes={len(at.dataframe)}, buttons={len(at.button)}, metrics={len(at.metric)}, charts={len(at.get('plotly_chart'))}")
print("   -> tabs:", len(at.tabs), "| download_buttons:", len(at.download_button))

# ---------------------------------------------------------------------------
# 2) Reset de dados de demonstração continua funcional
# ---------------------------------------------------------------------------
at.button[0].click()
at.run()
assert not at.exception, at.exception[0] if at.exception else None
assert at.session_state["usar_demo"] is True
assert len(at.session_state["assets_editados"]) == 12
print("2) reset demo OK ->", len(at.session_state["assets_editados"]), "ativos")

# ---------------------------------------------------------------------------
# 3) Filtro por departamento não quebra a página
# ---------------------------------------------------------------------------
at.selectbox[0].select("Financeiro").run()
assert not at.exception, at.exception[0] if at.exception else None
assert at.selectbox[0].value == "Financeiro"
print("3) filtro departamento OK ->", at.selectbox[0].value)

print("ALL APP TESTS PASSED")
