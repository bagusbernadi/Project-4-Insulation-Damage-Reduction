"""Langkah 3: membuat data simulasi Jan-Okt 2026 (wire harness, insulation damage) dengan seed tetap.

Keluaran (project/data/raw/): production_daily.csv, ng_log.csv, countermeasure_log.csv, dim_operator.csv
Referensi (project/data/reference/): dim_defect.csv ; project/data/ground_truth.json
Parameter countermeasure (tanggal, pengali penurunan) ada di code/common.py dan bisa ditimpa lewat argumen:
    python 01_generate_data.py --cm1 2026-07-20 --cm2 2026-08-10 --cm3 2026-09-07
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--cm1"), ap.add_argument("--cm2"), ap.add_argument("--cm3")
args = ap.parse_args()
CMS = [dict(c) for c in C.CM]
for c, a in zip(CMS, (args.cm1, args.cm2, args.cm3)):
    if a:
        c["start_date"] = a
rng = np.random.default_rng(C.SEED)
C.RAW_DIR.mkdir(parents=True, exist_ok=True)
C.REF_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- operator
ops = []
for i in range(1, 21):
    shift = "Shift 1" if i <= 10 else "Shift 2"
    new = i in (9, 10) or i >= 15                      # 2 operator baru di Shift 1, 6 di Shift 2
    hire = (pd.Timestamp("2026-01-12") + pd.Timedelta(days=int(rng.integers(0, 90)))) if new else \
           (pd.Timestamp("2018-03-01") + pd.Timedelta(days=int(rng.integers(0, 2400))))
    ops.append(dict(operator_id=f"OP{i:02d}", shift=shift, hire_date=hire.date().isoformat(), status="baru" if new else "lama"))
dim_op = pd.DataFrame(ops)
op_eff = dict(zip(dim_op.operator_id, rng.lognormal(0, 0.10, len(dim_op))))   # perbedaan individu

# ---------------------------------------------------------------- baris produksi harian
days = pd.bdate_range(C.START_DATE, C.END_DATE)
days = days[~days.isin(pd.to_datetime(C.HOLIDAYS))]
ndays = days.to_series().groupby(days.month).size().to_dict()
rows = []
for d in days:
    for t, share in C.HARNESS.items():
        for s in C.SHIFTS:
            emp = dim_op[(dim_op["shift"] == s) & (pd.to_datetime(dim_op.hire_date) <= d)]
            op = emp.operator_id.iloc[int(rng.integers(0, len(emp)))]
            mean = C.MONTH_VOLUME[d.month] * share * 0.5 / ndays[d.month]
            rows.append((d, s, t, op, int(rng.poisson(mean))))
prod = pd.DataFrame(rows, columns=["date", "shift", "harness_type", "operator_id", "input_qty"])
prod = prod.merge(dim_op[["operator_id", "hire_date", "status"]], on="operator_id")
prod["hire_date"] = pd.to_datetime(prod.hire_date)

# ---------------------------------------------------------------- rate per baris
def ramp(d, start, days_):
    return np.clip((d - pd.Timestamp(start)).dt.days / days_, 0, 1).to_numpy()

rm = {c["cm_id"]: ramp(prod.date, c["start_date"], c["ramp"]) for c in CMS}
age = (prod.date - prod.hire_date).dt.days.to_numpy()
excess = np.where(prod.status == "baru", C.NEW_OP_EXCESS * np.exp(-age / C.NEW_OP_TAU), 0.0)
excess = excess * (1 - C.SOP_REDUCES_EXCESS * rm[2])
opm = (1 + excess) * prod.operator_id.map(op_eff).to_numpy() * prod.harness_type.map(C.HARNESS_MULT).to_numpy()


def cm_factor(code):
    f = np.ones(len(prod))
    for c in CMS:
        if code in c["mult"]:
            f *= 1 - (1 - c["mult"][code]) * rm[c["cm_id"]]
    return f


unit = {k: v / 100 * opm * cm_factor(k) for k, v in C.BASE_ID.items()}
before = (prod.date < pd.Timestamp(C.BEFORE_END) + pd.Timedelta(days=1)).to_numpy()
exp_rate = sum((u * prod.input_qty.to_numpy())[before].sum() for u in unit.values()) / prod.input_qty.to_numpy()[before].sum()
k = C.TARGET_BEFORE / exp_rate                           # kalibrasi agar rata-rata before = 3,0%
rate = {c: u * k for c, u in unit.items()}
for c, b in C.BASE_OTHER.items():
    rate[c] = np.full(len(prod), b) * prod.harness_type.map(C.HARNESS_MULT).to_numpy() ** 0.5
codes = list(rate)

# ---------------------------------------------------------------- NG per baris dan kode
inp = prod.input_qty.to_numpy()
counts = {c: rng.binomial(inp, np.minimum(rate[c], 0.5)) for c in codes}
prod["ng_qty"] = sum(counts.values())
prod["ok_qty"] = prod.input_qty - prod.ng_qty
prod["date"] = prod.date.dt.date.astype(str)
cause = {"ID-01": "Perakitan", "ID-02": "Tepi bracket"}
STN = {"ID-01": (["Electrical Test", "Visual Inspection", "Taping"], [.55, .40, .05]),
       "ID-02": (["Electrical Test", "Visual Inspection", "Assembly Board"], [.50, .45, .05]),
       "ID-03": (["Visual Inspection", "Electrical Test"], [.65, .35]),
       "OT-01": (["Crimping", "Electrical Test"], [.45, .55]), "OT-02": (["Visual Inspection", "Sub-assembly"], [.80, .20]),
       "OT-03": (["Taping", "Visual Inspection"], [.55, .45])}
cm1, cm3 = pd.Timestamp(CMS[0]["start_date"]), pd.Timestamp(CMS[2]["start_date"])
ng = []
for i, r in enumerate(prod.itertuples()):
    d = pd.Timestamp(r.date)
    p_in = float(np.clip((d - cm3).days / CMS[2]["ramp"], 0, 1))
    for c in codes:
        for _ in range(counts[c][i]):
            st, pr = STN[c]
            if c == "ID-03" and d >= cm1 and rng.random() < 0.15:
                s_found = "Wire Cutting & Stripping"
            else:
                s_found = st[int(rng.choice(len(st), p=pr))]
            ng.append((r.date, r.shift, r.harness_type, r.operator_id, s_found, c, cause.get(c, "Lainnya"),
                       "In-house" if rng.random() < p_in else "Supplier"))
ngl = pd.DataFrame(ng, columns=["date", "shift", "harness_type", "operator_id", "station_found", "defect_code", "cause_source", "bracket_source"])
ngl = ngl.sort_values(["date", "shift", "harness_type", "operator_id"], kind="stable").reset_index(drop=True)
ngl.insert(0, "ng_id", [f"NG-{i + 1:06d}" for i in range(len(ngl))])
assert len(ngl) == prod.ng_qty.sum()
clean_prod, clean_ng = prod[["date", "shift", "harness_type", "operator_id", "input_qty", "ok_qty", "ng_qty"]].copy(), ngl.copy()

# ---------------------------------------------------------------- data kotor (2-3%)
dirty = {}
P, N = clean_prod.copy(), clean_ng.copy()
pick = lambda n, size: rng.choice(n, size=size, replace=False)

i_ng = pick(len(P), 10)                                  # ng_qty > input_qty (ok_qty tetap benar)
P.loc[i_ng, "ng_qty"] = P.loc[i_ng, "input_qty"] + rng.integers(1, 9, 10)
dirty["prod_ng_gt_input"] = 10
i_sh = pick(len(P), 8); P.loc[i_sh, "shift"] = ""
dirty["prod_shift_blank"] = 8
extra_p = P.sample(8, random_state=7).copy()             # baris ganda
extra_p2 = pd.DataFrame({"date": ["2025-12-29", "2025-12-30", "2026-11-02", "2026-11-03", "2027-01-04", "2025-12-31", "2026-11-04", "2026-12-01"],
                         "shift": rng.choice(C.SHIFTS, 8), "harness_type": rng.choice(list(C.HARNESS), 8),
                         "operator_id": rng.choice(dim_op.operator_id, 8), "input_qty": rng.integers(30, 70, 8)})
extra_p2["ng_qty"] = rng.integers(0, 3, 8); extra_p2["ok_qty"] = extra_p2.input_qty - extra_p2.ng_qty
dirty["prod_duplicate"] = 8
dirty["prod_date_out_of_period"] = 8
P = pd.concat([P, extra_p, extra_p2], ignore_index=True)

typo = {"ID-01": ["ID-1", "id-01", "ID01", "ID-O1"], "ID-02": ["ID-2", "id-02", "ID02", "ID-O2"], "ID-03": ["ID-3", "id-03", "ID03", "ID-O3"]}
cand = N.index[N.defect_code.isin(typo)].to_numpy()
i_ty = rng.choice(cand, 30, replace=False)
for j in i_ty:
    N.at[j, "defect_code"] = rng.choice(typo[N.at[j, "defect_code"]])
dirty["ng_code_typo"] = 30
i_s2 = rng.choice(np.setdiff1d(np.arange(len(N)), i_ty), 10, replace=False); N.loc[i_s2, "shift"] = ""
dirty["ng_shift_blank"] = 10
extra_n = N.sample(20, random_state=11).copy()
extra_n2 = N.sample(6, random_state=13).copy()
extra_n2["ng_id"] = [f"NG-X{i + 1:04d}" for i in range(6)]
extra_n2["date"] = ["2025-12-28", "2025-12-30", "2026-11-05", "2026-11-09", "2027-01-05", "2026-12-02"]
dirty["ng_duplicate"] = 20
dirty["ng_date_out_of_period"] = 6
N = pd.concat([N, extra_n, extra_n2], ignore_index=True)
P = P.sample(frac=1, random_state=3).reset_index(drop=True) if False else P

P.to_csv(C.RAW_DIR / "production_daily.csv", index=False)
N.to_csv(C.RAW_DIR / "ng_log.csv", index=False)
dim_op.to_csv(C.RAW_DIR / "dim_operator.csv", index=False)
cmdf = pd.DataFrame([{k_: c[k_] for k_ in ("cm_id", "cm_name", "target_cause", "station", "start_date")} for c in CMS])
cmdf.to_csv(C.RAW_DIR / "countermeasure_log.csv", index=False)
pd.DataFrame([("ID-01", "Insulation damage akibat cara perakitan", "Perakitan", True), ("ID-02", "Insulation damage akibat tepi bracket tajam", "Tepi bracket", True),
              ("ID-03", "Insulation damage lain-lain", "Lainnya", True), ("OT-01", "Terminal longgar", "Lainnya", False),
              ("OT-02", "Salah posisi konektor", "Lainnya", False), ("OT-03", "Taping kurang rapat", "Lainnya", False)],
             columns=["defect_code", "description", "cause_source", "is_insulation_damage"]).to_csv(C.DIM_DEFECT_CSV, index=False)

n_dirty = sum(dirty.values())
truth = {
    "seed": C.SEED, "period": [C.START_DATE, C.END_DATE], "working_days": len(days),
    "clean_rows": {"production_daily": len(clean_prod), "ng_log": len(clean_ng)},
    "clean_totals": {"input": int(clean_prod.input_qty.sum()), "ng": int(clean_prod.ng_qty.sum())},
    "raw_rows": {"production_daily": len(P), "ng_log": len(N)},
    "dirty_injected": dirty, "dirty_pct": {"production_daily": round((10 + 8 + 8 + 8) / len(P) * 100, 2), "ng_log": round((30 + 10 + 20 + 6) / len(N) * 100, 2)},
    "facts": {
        "1_rate_before_target": C.TARGET_BEFORE, "1_rate_after_approx": 0.022,
        "2_volume_after_vs_before": "sekitar +30%",
        "3_countermeasure_dates": {c["cm_name"]: c["start_date"] for c in CMS},
        "4_biggest_drop": "ID-01 (Perakitan); ID-02 (Tepi bracket) turun setelah bracket in-house; Shift 2 lebih tinggi di before lalu mengecil",
        "5_dirty": "2-3% data kotor: NG>input, tanggal di luar periode, baris ganda, kode salah ketik, shift kosong"},
}
Path(C.GROUND_TRUTH).write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"hari kerja {len(days)}; production {len(clean_prod)} -> raw {len(P)}; ng_log {len(clean_ng)} -> raw {len(N)}; kalibrasi k={k:.3f}")
bm = clean_prod.date < "2026-07-01"; am = clean_prod.date >= "2026-08-01"
cn = clean_ng.assign(ins=clean_ng.defect_code.str.startswith("ID"))
print(f"input before {clean_prod[bm].input_qty.sum()} after {clean_prod[am].input_qty.sum()}")
print("rate ID before", round(cn[cn.date < "2026-07-01"].ins.sum() / clean_prod[bm].input_qty.sum() * 100, 3),
      "after", round(cn[cn.date >= "2026-08-01"].ins.sum() / clean_prod[am].input_qty.sum() * 100, 3))
