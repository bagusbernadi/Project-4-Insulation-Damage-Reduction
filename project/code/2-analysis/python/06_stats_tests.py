"""Langkah 8-9: uji signifikansi (Q4-Q6), p-chart dan waktu penurunan (Q7-Q8), faktor operator (Q10), sensitivitas data kotor (Q13).
Keluaran: results/2-analysis/{ztest,volume_vs_rate,sample_size,pchart,cm_effect,model,sensitivity}.csv"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_effectsize, proportions_ztest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from kpi_pandas import prepare, period_of  # noqa: E402

prod, ng, op, cm = prepare()
ins = ng[ng.is_insulation]
A = C.ALPHA


def test(scope, nb, xb, na, xa):
    """z-test dua proporsi (varians gabungan) + 95% CI selisih (Wald)."""
    z, p = proportions_ztest([xb, xa], [nb, na])
    lo, hi = confint_proportions_2indep(xb, nb, xa, na, compare="diff", method="wald")
    pb, pa = xb / nb, xa / na
    return dict(scope=scope, n_before=int(nb), x_before=int(xb), rate_before=pb, n_after=int(na), x_after=int(xa), rate_after=pa, diff=pb - pa,
                rel_drop=(pb - pa) / pb, z=z, p_value=p, ci_low=lo, ci_high=hi, significant=bool(p < A))


def scope_test(label, pm, nm):
    b, a = pm.period == "before", pm.period == "after"
    return test(label, pm[b].input_qty.sum(), nm[nm.period == "before"].shape[0], pm[a].input_qty.sum(), nm[nm.period == "after"].shape[0])


rows = [scope_test("Insulation damage (ID-01+02+03)", prod, ins), scope_test("Semua NG (termasuk defect lain)", prod, ng)]
for t in "ABC":
    rows.append(scope_test(f"Harness tipe {t}", prod[prod.harness_type == t], ins[ins.harness_type == t]))
for s in C.SHIFTS:
    rows.append(scope_test(s, prod[prod["shift"] == s], ins[ins["shift"] == s]))
for st in ("lama", "baru"):
    rows.append(scope_test(f"Operator {st}", prod[prod.op_status == st], ins[ins.op_status == st]))
for code, lab in (("ID-01", "ID-01 Perakitan"), ("ID-02", "ID-02 Tepi bracket"), ("ID-03", "ID-03 Lain-lain")):
    rows.append(scope_test(lab, prod, ng[ng.defect_code == code]))
Z = pd.DataFrame(rows); Z.to_csv(C.RES_ANALYSIS / "ztest.csv", index=False)

# ---- Q2: jumlah NG vs rate
m = prod.groupby("period").agg(input=("input_qty", "sum"), months=("month", "nunique")).join(ins.groupby("period").size().rename("ng_id"))
m["input_per_month"], m["ng_per_month"] = m.input / m.months, m.ng_id / m.months
m["rate"] = m.ng_id / m.input
vb, va = m.loc["before"], m.loc["after"]
pd.DataFrame([dict(metric="Input per bulan", before=vb.input_per_month, after=va.input_per_month, change=va.input_per_month / vb.input_per_month - 1),
              dict(metric="NG insulation damage per bulan", before=vb.ng_per_month, after=va.ng_per_month, change=va.ng_per_month / vb.ng_per_month - 1),
              dict(metric="Insulation damage rate", before=vb.rate, after=va.rate, change=va.rate / vb.rate - 1)]).to_csv(C.RES_ANALYSIS / "volume_vs_rate.csv", index=False)

# ---- Q6: jumlah sampel minimum
pw = NormalIndPower()
nb_, na_ = int(vb.input), int(va.input)
pb = vb.rate
srows = []
for rel in (0.05, 0.10, 0.15, 0.20, 0.27):
    pa = pb * (1 - rel); es = proportion_effectsize(pb, pa)
    n1 = pw.solve_power(effect_size=es, alpha=A, power=0.8, ratio=1)
    srows.append(dict(rel_drop=rel, rate_before=pb, rate_after=pa, n_per_group=int(np.ceil(n1)), months_after=n1 / va.input_per_month,
                      power_actual=pw.power(effect_size=es, nobs1=na_, alpha=A, ratio=nb_ / na_)))
h = pw.solve_power(effect_size=None, nobs1=na_, alpha=A, power=0.8, ratio=nb_ / na_)
p_min = np.sin((2 * np.arcsin(np.sqrt(pb)) - h) / 2) ** 2
srows.append(dict(rel_drop=(pb - p_min) / pb, rate_before=pb, rate_after=p_min, n_per_group=na_, months_after=3.0, power_actual=0.8))
S = pd.DataFrame(srows); S["kind"] = ["skenario"] * 5 + ["minimum terdeteksi dengan data after saat ini"]
S.to_csv(C.RES_ANALYSIS / "sample_size.csv", index=False)

# ---- Q7: p-chart mingguan, batas terpisah before dan after
wk = prod.groupby("week_start").agg(period=("period", "min"), n=("input_qty", "sum")).join(ins.groupby("week_start").size().rename("x")).fillna({"x": 0}).reset_index()
wk = wk[wk.n >= 500].reset_index(drop=True)          # minggu parsial (hanya 2 Jan) dibuang dari p-chart
wk["p"] = wk.x / wk.n
cl = {k: wk[wk.period == k].x.sum() / wk[wk.period == k].n.sum() for k in ("before", "after")}
wk["base"] = np.where(wk.period == "after", "after", "before")
wk["cl"] = wk.base.map(cl)
wk["ucl"] = wk.cl + 3 * np.sqrt(wk.cl * (1 - wk.cl) / wk.n); wk["lcl"] = (wk.cl - 3 * np.sqrt(wk.cl * (1 - wk.cl) / wk.n)).clip(lower=0)
wk["out"] = np.where(wk.p > wk.ucl, "di atas UCL", np.where(wk.p < wk.lcl, "di bawah LCL", ""))
# aturan 8 titik berurutan di bawah garis tengah before (pergeseran proses)
below = (wk.p < cl["before"]).astype(int); run = below.groupby((below == 0).cumsum()).cumsum()
wk["run_below_before_cl"] = run
wk.to_csv(C.RES_ANALYSIS / "pchart.csv", index=False)

# ---- Q8: waktu penurunan vs tanggal countermeasure (deret mingguan penyebab sasaran)
full = wk[wk.n > 1000].reset_index(drop=True)             # buang minggu parsial (libur) agar rate stabil
TARGET = {1: ("Semua insulation damage", ins), 2: ("ID-01 (cara perakitan)", ng[ng.defect_code == "ID-01"]), 3: ("ID-02 (tepi bracket)", ng[ng.defect_code == "ID-02"])}


def best_cp(nvec, xvec):
    """Satu titik ubah (level tetap sebelum/sesudah) dengan log-likelihood binomial maksimum."""
    ll = lambda x, n: 0 if x in (0, n) else x * np.log(x / n) + (n - x) * np.log(1 - x / n)
    best = (None, -np.inf)
    for i in range(3, len(nvec) - 2):
        v = ll(xvec[:i].sum(), nvec[:i].sum()) + ll(xvec[i:].sum(), nvec[i:].sum())
        if v > best[1]:
            best = (i, v)
    return best[0], best[1] - ll(xvec.sum(), nvec.sum())


crow = []
for _, c in cm.iterrows():
    label, src = TARGET[c.cm_id]
    w = prod.groupby("week_start").input_qty.sum().rename("n").to_frame().join(src.groupby("week_start").size().rename("x")).fillna(0).reset_index()
    w = w[w.n > 1000]
    win = w[(w.week_start >= c.start_date - pd.Timedelta(days=63)) & (w.week_start <= c.start_date + pd.Timedelta(days=63))].reset_index(drop=True)
    i, gain = best_cp(win.n.to_numpy(), win.x.to_numpy())
    cp = win.week_start[i]
    crow.append(dict(cm_id=int(c.cm_id), cm_name=c.cm_name, start_date=c.start_date.date().isoformat(), series=label, changepoint_week=cp.date().isoformat(),
                     offset_days=int((cp - c.start_date).days), within_7_days=abs(int((cp - c.start_date).days)) <= 7, lr_p_value=float(chi2.sf(2 * gain, 1))))
pd.DataFrame(crow).to_csv(C.RES_ANALYSIS / "cm_effect.csv", index=False)
# titik ubah tunggal terkuat pada seluruh deret mingguan insulation damage
i, gain = best_cp(full.n.to_numpy(), full.x.to_numpy())
pd.DataFrame([dict(changepoint_week=full.week_start[i].date().isoformat(), rate_before=full.x[:i].sum() / full.n[:i].sum(), rate_after=full.x[i:].sum() / full.n[i:].sum(),
                   nearest_cm=int(cm.loc[(cm.start_date - full.week_start[i]).abs().idxmin(), "cm_id"]),
                   offset_days=int((full.week_start[i] - cm.loc[(cm.start_date - full.week_start[i]).abs().idxmin(), "start_date"]).days))]).to_csv(C.RES_ANALYSIS / "changepoint.csv", index=False)

# ---- Q10: regresi logistik (binomial) dengan penyesuaian operator, shift, tipe harness
d = prod.merge(ins.groupby(["date", "shift", "harness_type"]).size().rename("x").reset_index(), how="left", on=["date", "shift", "harness_type"]).fillna({"x": 0})
d = d[d.period != "transisi"].copy()
d["after"] = (d.period == "after").astype(int); d["op_baru"] = (d.op_status == "baru").astype(int); d["shift2"] = (d["shift"] == "Shift 2").astype(int)
d["type_B"], d["type_C"] = (d.harness_type == "B").astype(int), (d.harness_type == "C").astype(int)
y = np.column_stack([d.x, d.input_qty - d.x])
mrows = []
for name, cols in (("Tanpa penyesuaian", ["after"]), ("Disesuaikan (operator, shift, tipe)", ["after", "op_baru", "shift2", "type_B", "type_C"])):
    f = sm.GLM(y, sm.add_constant(d[cols]), family=sm.families.Binomial()).fit()
    ci = f.conf_int()
    for t in cols:
        mrows.append(dict(model=name, term=t, coef=f.params[t], odds_ratio=np.exp(f.params[t]), or_low=np.exp(ci.loc[t, 0]), or_high=np.exp(ci.loc[t, 1]), p_value=f.pvalues[t]))
pd.DataFrame(mrows).to_csv(C.RES_ANALYSIS / "model.csv", index=False)

# ---- Q8/Q9: efek tiap countermeasure (indikator langkah kumulatif, disesuaikan operator, shift, tipe harness)
dd = prod.copy()
for _, c in cm.iterrows():
    dd[f"cm{int(c.cm_id)}"] = (dd.date >= c.start_date).astype(int)
dd["op_baru"], dd["shift2"] = (dd.op_status == "baru").astype(int), (dd["shift"] == "Shift 2").astype(int)
dd["type_B"], dd["type_C"] = (dd.harness_type == "B").astype(int), (dd.harness_type == "C").astype(int)
srow = []
for lab, src in (("Insulation damage (semua)", ins), ("ID-01 Perakitan", ng[ng.defect_code == "ID-01"]), ("ID-02 Tepi bracket", ng[ng.defect_code == "ID-02"])):
    e = dd.merge(src.groupby(["date", "shift", "harness_type"]).size().rename("x").reset_index(), how="left", on=["date", "shift", "harness_type"]).fillna({"x": 0})
    cols = ["cm1", "cm2", "cm3", "op_baru", "shift2", "type_B", "type_C"]
    f = sm.GLM(np.column_stack([e.x, e.input_qty - e.x]), sm.add_constant(e[cols]), family=sm.families.Binomial()).fit(); ci = f.conf_int()
    for t in cols[:3]:
        srow.append(dict(series=lab, term=t, odds_ratio=np.exp(f.params[t]), or_low=np.exp(ci.loc[t, 0]), or_high=np.exp(ci.loc[t, 1]), p_value=f.pvalues[t]))
pd.DataFrame(srow).to_csv(C.RES_ANALYSIS / "cm_steps.csv", index=False)

# ---- Q13: sensitivitas terhadap data kotor
rp = pd.read_csv(C.RAW_DIR / "production_daily.csv", keep_default_na=False); rn = pd.read_csv(C.RAW_DIR / "ng_log.csv", keep_default_na=False)
per = lambda s: np.where(s < "2026-07-01", "before", np.where(s >= "2026-08-01", "after", "transisi"))
rp["period"], rn["period"] = per(rp.date), per(rn.date)
sc = []
rn_ok = rn.defect_code.isin(["ID-01", "ID-02", "ID-03"])
sc.append(test("A. Data mentah apa adanya (tanpa cleaning)", rp[rp.period == "before"].input_qty.sum(), (rn_ok & (rn.period == "before")).sum(),
               rp[rp.period == "after"].input_qty.sum(), (rn_ok & (rn.period == "after")).sum()))
inperiod = lambda s: (s >= C.START_DATE) & (s <= C.END_DATE)
bad_p = (~inperiod(rp.date)) | rp.duplicated(keep="first") | rp["shift"].eq("") | (rp.ng_qty > rp.input_qty)
bad_n = (~inperiod(rn.date)) | rn.duplicated(keep="first") | rn["shift"].eq("") | ~rn.defect_code.isin(["ID-01", "ID-02", "ID-03", "OT-01", "OT-02", "OT-03"])
pp, nn = rp[~bad_p], rn[~bad_n]
sc.append(test("B. Semua baris bermasalah dibuang", pp[pp.period == "before"].input_qty.sum(), nn[(nn.period == "before") & nn.defect_code.str.startswith("ID-")].shape[0],
               pp[pp.period == "after"].input_qty.sum(), nn[(nn.period == "after") & nn.defect_code.str.startswith("ID-")].shape[0]))
sc.append(Z.iloc[0].to_dict() | {"scope": "C. Cleaning sesuai log (dibuang + diperbaiki)"})
sens = pd.DataFrame(sc); sens.to_csv(C.RES_ANALYSIS / "sensitivity.csv", index=False)

pd.set_option("display.width", 250, "display.max_columns", 30)
print(Z[["scope", "rate_before", "rate_after", "rel_drop", "z", "p_value", "ci_low", "ci_high"]].round(5).to_string(index=False))
print(pd.read_csv(C.RES_ANALYSIS / "volume_vs_rate.csv").round(4)); print(S.round(4).to_string(index=False))
print(wk[["week_start", "period", "p", "cl", "ucl", "lcl", "out", "run_below_before_cl"]].round(4).to_string(index=False))
print(pd.DataFrame(crow).round(4).to_string(index=False)); print(pd.DataFrame(srow).round(4).to_string(index=False)); print(pd.read_csv(C.RES_ANALYSIS / "changepoint.csv"))
print(pd.DataFrame(mrows).round(4).to_string(index=False)); print(sens[["scope", "rate_before", "rate_after", "diff", "z", "p_value"]].round(5).to_string(index=False))
