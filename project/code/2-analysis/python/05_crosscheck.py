"""Langkah 7a: cek silang hasil SQL (results/2-analysis/*.csv) dengan hitungan pandas dari CSV bersih. Semua baris harus PASS."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from kpi_pandas import prepare  # noqa: E402

prod, ng, op, cm = prepare()
rows = []


def cmp(name, key, a, b):
    ok = np.isclose(float(a), float(b), rtol=0, atol=1e-12)
    rows.append((name, key, float(a), float(b), "PASS" if ok else "FAIL"))


R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
inp = lambda g: g.input_qty.sum()
ins = ng[ng.is_insulation]
# period
for r in R("period.csv").itertuples():
    p, n = prod[prod.period == r.period], ng[ng.period == r.period]
    cmp("period.input", r.period, r.input_qty, inp(p)); cmp("period.ng_all", r.period, r.ng_all, len(n))
    cmp("period.ng_id", r.period, r.ng_id, n.is_insulation.sum()); cmp("period.rate_id", r.period, r.rate_id, n.is_insulation.sum() / inp(p))
# week, month
for name, col, f in (("week", "week_start", "week.csv"), ("month", "month", "month.csv")):
    g = prod.groupby(col).input_qty.sum(); k = ins.groupby(col).size()
    for r in R(f).itertuples():
        key = getattr(r, col); key = pd.Timestamp(key) if name == "week" else key
        cmp(f"{name}.input", str(key)[:10], r.input_qty, g[key]); cmp(f"{name}.ng_id", str(key)[:10], r.ng_id, k.get(key, 0))
# dimensi
prod["shift_status"] = prod["shift"] + " / " + prod.op_status; ins = ins.assign(shift_status=ins["shift"] + " / " + ins.op_status)
for r in R("dim.csv").itertuples():
    p = prod[(prod.period == r.period) & (prod[r.dim] == r.val)]; n = ins[(ins.period == r.period) & (ins[r.dim] == r.val)]
    cmp(f"dim.{r.dim}.input", f"{r.val}|{r.period}", r.input_qty, inp(p)); cmp(f"dim.{r.dim}.ng_id", f"{r.val}|{r.period}", r.ng_id, len(n))
# penyebab
tot = prod.groupby("period").input_qty.sum()
for r in R("cause.csv").itertuples():
    n = ng[(ng.period == r.period) & (ng.defect_code == r.defect_code)]
    cmp("cause.ng", f"{r.defect_code}|{r.period}", r.ng, len(n)); cmp("cause.rate", f"{r.defect_code}|{r.period}", r.rate, len(n) / tot[r.period])
for r in R("cause_month.csv").itertuples():
    n = ng[(ng.month == r.month) & (ng.defect_code == r.defect_code)]
    cmp("cause_month.ng", f"{r.defect_code}|{r.month}", r.ng, len(n)); cmp("cause_month.rate", f"{r.defect_code}|{r.month}", r.rate, len(n) / prod[prod.month == r.month].input_qty.sum())
for r in R("bracket.csv").itertuples():
    cmp("bracket.ng_id02", f"{r.period}|{r.bracket_source}", r.ng_id02, len(ng[(ng.period == r.period) & (ng.bracket_source == r.bracket_source) & (ng.defect_code == "ID-02")]))
for r in R("station.csv").itertuples():
    cmp("station.ng_id", f"{r.period}|{r.station_found}", r.ng_id, len(ins[(ins.period == r.period) & (ins.station_found == r.station_found)]))
df = pd.DataFrame(rows, columns=["check", "key", "sql", "pandas", "status"])
df.to_csv(C.RES_ANALYSIS / "crosscheck.csv", index=False)
print(f"{(df.status == 'PASS').sum()} dari {len(df)} PASS")
assert (df.status == "PASS").all()
