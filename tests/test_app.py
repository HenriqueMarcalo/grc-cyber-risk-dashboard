import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from streamlit.testing.v1 import AppTest


def _launch():
    at = AppTest.from_file(os.path.join(PROJ, "app.py"), default_timeout=30)
    at.run()
    return at


def test_smoke_no_exceptions():
    at = _launch()
    assert not at.exception, at.exception[0] if at.exception else None
    assert len(at.dataframe) >= 2, "data_editor and business case must be present"
    assert len(at.download_button) >= 1, "must have a download button"
    assert len(at.button) >= 1, "must have the reset button"
    assert len(at.tabs) == 2, "must have the 2 tabs (Executive Analysis / Master Registry)"
    assert len(at.metric) >= 4, "must have the 4 KPIs"
    assert len(at.get("plotly_chart")) >= 1, "must have charts"


def test_reset_demo_data():
    at = _launch()
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception[0] if at.exception else None
    assert at.session_state["usar_demo"] is True
    assert len(at.session_state["assets_editados"]) == 12


def test_department_filter_does_not_break():
    at = _launch()
    at.selectbox[0].select("Finance").run()
    assert not at.exception, at.exception[0] if at.exception else None
    assert at.selectbox[0].value == "Finance"
