"""Langkah 4: memeriksa dan membersihkan data mentah. Setiap aturan dicatat di results/1-data-preparation/cleaning_log.csv dan docs/cleaning_log.md.

Aturan (urutan penting):
N1 ng_log tanggal di luar periode -> dibuang      N2 ng_log baris ganda -> dibuang (simpan satu)
N3 kode defect salah ketik -> diperbaiki          N4 shift kosong -> diisi dari dim_operator
P1 production tanggal di luar periode -> dibuang  P2 baris ganda -> dibuang (simpan satu)
P3 shift kosong -> diisi dari dim_operator        P4 ng_qty > input_qty -> ng_qty dihitung ulang dari jumlah baris ng_log
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
C.RES_PREP.mkdir(parents=True, exist_ok=True)
prod = pd.read_csv(C.RAW_DIR / "production_daily.csv", keep_default_na=False)
ng = pd.read_csv(C.RAW_DIR / "ng_log.csv", keep_default_na=False)
dim_op = pd.read_csv(C.RAW_DIR / "dim_operator.csv")
valid = set(pd.read_csv(C.DIM_DEFECT_CSV).defect_code)
op_shift = dict(zip(dim_op.operator_id, dim_op["shift"]))
raw_n = {"production_daily": len(prod), "ng_log": len(ng)}
log = []


def rec(rule, table, issue, found, decision, dropped=0, fixed=0):
    log.append(dict(rule=rule, table=table, issue=issue, rows_found=int(found), decision=decision, rows_dropped=int(dropped), rows_fixed=int(fixed)))


inp = lambda d: (d >= C.START_DATE) & (d <= C.END_DATE)
# ---- ng_log
bad = ~inp(ng.date); rec("N1", "ng_log", "tanggal di luar Jan-Okt 2026", bad.sum(), "dibuang", bad.sum()); ng = ng[~bad]
dup = ng.duplicated(keep="first"); rec("N2", "ng_log", "baris ganda (semua kolom sama)", dup.sum(), "dibuang, simpan satu", dup.sum()); ng = ng[~dup]


def fix_code(c):
    t = re.sub(r"\s", "", str(c)).upper().replace("O", "0")
    m = re.fullmatch(r"(ID|OT)-?0?(\d)", t)
    return f"{m.group(1)}-0{m.group(2)}" if m else c


new = ng.defect_code.map(fix_code); chg = new != ng.defect_code
rec("N3", "ng_log", "kode defect salah ketik (ID-1, id-01, ID01, ID-O1, ...)", chg.sum(), "diperbaiki ke format ID-0n", 0, chg.sum()); ng = ng.assign(defect_code=new)
assert set(ng.defect_code) <= valid, set(ng.defect_code) - valid
blank = ng["shift"].eq(""); rec("N4", "ng_log", "shift kosong", blank.sum(), "diisi dari shift operator (dim_operator)", 0, blank.sum())
ng.loc[blank, "shift"] = ng.loc[blank, "operator_id"].map(op_shift)
# ---- production_daily
bad = ~inp(prod.date); rec("P1", "production_daily", "tanggal di luar Jan-Okt 2026", bad.sum(), "dibuang", bad.sum()); prod = prod[~bad]
dup = prod.duplicated(keep="first"); rec("P2", "production_daily", "baris ganda (semua kolom sama)", dup.sum(), "dibuang, simpan satu", dup.sum()); prod = prod[~dup]
blank = prod["shift"].eq(""); rec("P3", "production_daily", "shift kosong", blank.sum(), "diisi dari shift operator (dim_operator)", 0, blank.sum())
prod.loc[blank, "shift"] = prod.loc[blank, "operator_id"].map(op_shift)
cnt = ng.groupby(["date", "shift", "harness_type"]).size().rename("ng_log_n").reset_index()
prod = prod.merge(cnt, how="left", on=["date", "shift", "harness_type"]).fillna({"ng_log_n": 0})
gt = prod.ng_qty > prod.input_qty
rec("P4", "production_daily", "ng_qty lebih besar dari input_qty", gt.sum(), "ng_qty dihitung ulang dari jumlah baris ng_log (ok_qty + ng_qty = input_qty terpenuhi)", 0, gt.sum())
prod.loc[gt, "ng_qty"] = prod.loc[gt, "ng_log_n"].astype(int)
resid = ((prod.ok_qty + prod.ng_qty != prod.input_qty) | (prod.ng_qty != prod.ng_log_n)).sum()
rec("P5", "production_daily", "ng_qty tidak sama dengan jumlah baris ng_log atau ok+ng tidak sama dengan input (setelah P4)", resid, "tidak ada sisa", 0, 0)
prod = prod.drop(columns="ng_log_n").astype({"ng_qty": int})
assert resid == 0
prod = prod.sort_values(["date", "shift", "harness_type"]).reset_index(drop=True)
ng = ng.sort_values("ng_id").reset_index(drop=True)
prod.to_csv(C.CLEAN_DIR / "production_daily.csv", index=False)
ng.to_csv(C.CLEAN_DIR / "ng_log.csv", index=False)
for f in ("dim_operator", "countermeasure_log"):
    pd.read_csv(C.RAW_DIR / f"{f}.csv").to_csv(C.CLEAN_DIR / f"{f}.csv", index=False)

L = pd.DataFrame(log); L.to_csv(C.RES_PREP / "cleaning_log.csv", index=False)
aff = {t: int(L[(L.table == t) & L.rule.ne("P5")].eval("rows_dropped + rows_fixed").sum()) for t in raw_n}
q = pd.DataFrame([dict(table=t, raw_rows=raw_n[t], bad_rows=aff[t], bad_pct=round(aff[t] / raw_n[t] * 100, 2), clean_rows=len({"production_daily": prod, "ng_log": ng}[t]))
                  for t in raw_n])
q.loc[len(q)] = ["total", q.raw_rows.sum(), q.bad_rows.sum(), round(q.bad_rows.sum() / q.raw_rows.sum() * 100, 2), q.clean_rows.sum()]
q.to_csv(C.RES_PREP / "data_quality_summary.csv", index=False)
md = ["# Cleaning log", "", "Dibuat oleh `02_clean_data.py`. Setiap baris bermasalah diputuskan dibuang atau diperbaiki; keputusan dibuat sebelum melihat hasil uji (lihat `definitions.md`).", "",
      "| Aturan | Tabel | Masalah | Baris ditemukan | Keputusan | Dibuang | Diperbaiki |", "|---|---|---|---:|---|---:|---:|"]
md += [f"| {r.rule} | {r.table} | {r.issue} | {r.rows_found} | {r.decision} | {r.rows_dropped} | {r.rows_fixed} |" for r in L.itertuples()]
md += ["", "## Ringkasan", "", "| Tabel | Baris mentah | Baris bermasalah | % | Baris bersih |", "|---|---:|---:|---:|---:|"]
md += [f"| {r.table} | {r.raw_rows} | {r.bad_rows} | {r.bad_pct} | {r.clean_rows} |" for r in q.itertuples()]
(C.DOCS_DIR / "cleaning_log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(L[["rule", "rows_found", "rows_dropped", "rows_fixed"]].to_string(index=False)); print(q.to_string(index=False))
