import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
from streamlit.proto.Common_pb2 import FileURLs as FileURLsProto

from motor_risco import processar_priorizacao_risco
from gestor_dados import (
    assets_default,
    carregar_ativos_do_upload,
    _ler_ficheiro_upload,
    MAPA_EDITOR_PARA_RAW,
    COLUNAS_RAW,
    _registos_iguais,
)


def _uf(name, csv_text, fid):
    rec = UploadedFileRec(file_id=fid, name=name, type="text/csv", data=csv_text.encode("utf-8"))
    return UploadedFile(rec, FileURLsProto())


def test_registos_iguais_robust_to_key_order_and_types():
    rec_a = [{"asset_name": "A", "dept": "X", "asset_value": 100, "rgpd": True}]
    rec_b = [{"rgpd": True, "asset_value": 100, "dept": "X", "asset_name": "A"}]
    assert _registos_iguais(rec_a, rec_b)
    rec_c = [{"asset_name": "A", "dept": "X", "asset_value": 101, "rgpd": True}]
    assert not _registos_iguais(rec_a, rec_c)
    assert not _registos_iguais(rec_a, [])


def test_upload_valid_csv_cached_by_file_id():
    csv_ok = """asset_name,dept,asset_value,vulnerability,framework,rgpd,threat_level,mitigation_cost
Test A,Finance,100000,Bug X,ISO 27001,True,4,10000
Test B,Operations,50000,Bug Y,NIST CSF,False,2,3000
"""
    df_imp = _ler_ficheiro_upload(_uf("assets.csv", csv_ok, "f1"))
    assert len(df_imp) == 2

    recs, erro = carregar_ativos_do_upload(_uf("assets.csv", csv_ok, "f1"))
    assert erro is False and len(recs) == 2
    assert recs[0]["asset_name"] == "Test A" and recs[0]["rgpd"] is True and recs[0]["threat_level"] == 4
    assert recs[1]["rgpd"] is False


def test_upload_accepts_portuguese_headers():
    csv_pt = """Ativo,Departamento,Valor do Ativo,Vulnerabilidade,GDPR,Ameaca,Custo
Srv A,Compras,80000,Vuln Z,N,3,5000
"""
    recs, erro = carregar_ativos_do_upload(_uf("pt.csv", csv_pt, "f2"))
    assert erro is False
    assert recs[0]["asset_name"] == "Srv A" and recs[0]["dept"] == "Compras"
    assert recs[0]["rgpd"] is False and recs[0]["framework"] == "N/A"


def test_upload_fallback_on_missing_columns():
    recs, erro = carregar_ativos_do_upload(_uf("wrong.csv", "foo,bar\n1,2\n", "f3"))
    assert erro is True and recs is assets_default


def test_no_file_returns_demo_data():
    recs, erro = carregar_ativos_do_upload(None)
    assert recs is assets_default and erro is True


def _extrair(df_tabela):
    df_e = df_tabela.rename(columns=MAPA_EDITOR_PARA_RAW)
    df_e = df_e[[c for c in COLUNAS_RAW if c in df_e.columns]]
    df_e["asset_name"] = df_e["asset_name"].fillna("").astype(str)
    df_e = df_e[df_e["asset_name"].str.strip() != ""]
    df_e["asset_value"] = pd.to_numeric(df_e["asset_value"], errors="coerce").fillna(0).astype(int)
    df_e["mitigation_cost"] = pd.to_numeric(df_e["mitigation_cost"], errors="coerce").fillna(0).astype(int)
    df_e["threat_level"] = pd.to_numeric(df_e["threat_level"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    df_e["rgpd"] = df_e["rgpd"].fillna(False).astype(bool)
    df_e["vulnerability"] = df_e["vulnerability"].fillna("N/A").astype(str)
    df_e["framework"] = df_e["framework"].fillna("N/A").astype(str)
    df_e["dept"] = df_e["dept"].fillna("No Department").astype(str)
    df_e.loc[df_e["dept"].str.strip().isin(["", "nan"]), "dept"] = "No Department"
    df_e["asset_name"] = df_e["asset_name"].astype(str)
    return df_e.to_dict("records")


def test_editor_round_trip_is_stable_but_detects_changes():
    records = carregar_ativos_do_upload(None)[0]
    df_grc = processar_priorizacao_risco(records, 0.30, 5000000, 120000, 0.02, 90, 50000)
    assert _registos_iguais(_extrair(df_grc), records), "round-trip without edits must be stable (no spurious rerun)"

    df_editado = df_grc.copy()
    df_editado.loc[0, "Asset Value (€)"] = 999999
    assert not _registos_iguais(_extrair(df_editado), records), "an edit must be detected (rerun triggered)"
