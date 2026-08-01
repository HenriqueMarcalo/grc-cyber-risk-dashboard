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

# ---------------------------------------------------------------------------
# 1) _registos_iguais: robusta a ordem de chaves e tipos
# ---------------------------------------------------------------------------
rec_a = [{"asset_name": "A", "dept": "X", "asset_value": 100, "rgpd": True}]
rec_b = [{"rgpd": True, "asset_value": 100, "dept": "X", "asset_name": "A"}]
assert _registos_iguais(rec_a, rec_b)
rec_c = [{"asset_name": "A", "dept": "X", "asset_value": 101, "rgpd": True}]
assert not _registos_iguais(rec_a, rec_c)
assert not _registos_iguais(rec_a, [])
print("1) _registos_iguais OK")

# ---------------------------------------------------------------------------
# 2) Upload real: cache (hash por file_id), validação, aliases PT, fallback
# ---------------------------------------------------------------------------
def uf(name, csv_text, fid):
    rec = UploadedFileRec(file_id=fid, name=name, type="text/csv", data=csv_text.encode("utf-8"))
    return UploadedFile(rec, FileURLsProto())

csv_ok = """asset_name,dept,asset_value,vulnerability,framework,rgpd,threat_level,mitigation_cost
Teste A,Financeiro,100000,Bug X,ISO 27001,True,4,10000
Teste B,Operações,50000,Bug Y,NIST CSF,False,2,3000
"""
df_imp = _ler_ficheiro_upload(uf("ativos.csv", csv_ok, "f1"))
assert len(df_imp) == 2
print("2a) cache file_id hash OK")

recs, erro = carregar_ativos_do_upload(uf("ativos.csv", csv_ok, "f1"))
assert erro is False and len(recs) == 2
assert recs[0]["asset_name"] == "Teste A" and recs[0]["rgpd"] is True and recs[0]["threat_level"] == 4
assert recs[1]["rgpd"] is False
print("2b) CSV válido OK ->", len(recs), "ativos")

csv_pt = """Ativo,Departamento,Valor do Ativo,Vulnerabilidade,GDPR,Ameaca,Custo
Srv A,Compras,80000,Vuln Z,N,3,5000
"""
recs2, erro2 = carregar_ativos_do_upload(uf("pt.csv", csv_pt, "f2"))
assert erro2 is False
assert recs2[0]["asset_name"] == "Srv A" and recs2[0]["dept"] == "Compras"
assert recs2[0]["rgpd"] is False and recs2[0]["framework"] == "N/D"
print("2c) CSV alias PT OK")

recs3, erro3 = carregar_ativos_do_upload(uf("errado.csv", "foo,bar\n1,2\n", "f3"))
assert erro3 is True and recs3 is assets_default
print("2d) CSV colunas em falta -> fallback OK")

recs4, erro4 = carregar_ativos_do_upload(None)
assert recs4 is assets_default and erro4 is True
print("2e) Sem ficheiro -> demo OK")

# ---------------------------------------------------------------------------
# 3) Sync do editor: round-trip sem edições e com edição
# ---------------------------------------------------------------------------
def _extrair(df_tabela):
    df_e = df_tabela.rename(columns=MAPA_EDITOR_PARA_RAW)
    df_e = df_e[[c for c in COLUNAS_RAW if c in df_e.columns]]
    df_e["asset_name"] = df_e["asset_name"].fillna("").astype(str)
    df_e = df_e[df_e["asset_name"].str.strip() != ""]
    df_e["asset_value"] = pd.to_numeric(df_e["asset_value"], errors="coerce").fillna(0).astype(int)
    df_e["mitigation_cost"] = pd.to_numeric(df_e["mitigation_cost"], errors="coerce").fillna(0).astype(int)
    df_e["threat_level"] = pd.to_numeric(df_e["threat_level"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    df_e["rgpd"] = df_e["rgpd"].fillna(False).astype(bool)
    df_e["vulnerability"] = df_e["vulnerability"].fillna("N/D").astype(str)
    df_e["framework"] = df_e["framework"].fillna("N/D").astype(str)
    df_e["dept"] = df_e["dept"].fillna("Sem Departamento").astype(str)
    df_e.loc[df_e["dept"].str.strip().isin(["", "nan"]), "dept"] = "Sem Departamento"
    df_e["asset_name"] = df_e["asset_name"].astype(str)
    return df_e.to_dict("records")

records = carregar_ativos_do_upload(None)[0]
df_grc = processar_priorizacao_risco(records, 0.30, 5000000, 120000, 0.02, 90, 50000)
assert _registos_iguais(_extrair(df_grc), records), "round-trip sem edições deve ser estável (sem rerun espúrio)"
df_editado = df_grc.copy()
df_editado.loc[0, "Valor do Ativo (€)"] = 999999
assert not _registos_iguais(_extrair(df_editado), records), "edição deve ser detetada (rerun acionado)"
print("3) sync editor OK -> round-trip estável e edição detetada")

print("ALL GESTOR TESTS PASSED")
