"""Langkah 10: dampak (unit terselamatkan, estimasi penghematan, Q11-Q12) dan pencocokan lima fakta yang ditanam (ground truth).
Keluaran: results/2-analysis/{impact,ground_truth_check}.csv. Semua angka dampak adalah estimated/simulated."""
import json
import sys
from pathlib import Path

import pandas as pd
from statsmodels.stats.proportion import proportions_ztest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from kpi_pandas import prepare  # noqa: E402

R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
Z, vr, cause, cmx, cp = R("ztest.csv").set_index("scope"), R("volume_vs_rate.csv").set_index("metric"), R("cause.csv"), R("cm_effect.csv"), R("changepoint.csv")
z = Z.loc["Insulation damage (ID-01+02+03)"]
vol = vr.loc["Input per bulan", "after"]                          # volume rata-rata per bulan pada periode after
# ---- dampak
rows = []
for label, d in (("batas bawah (CI 95%)", z.ci_low), ("titik (hasil uji)", z["diff"]), ("batas atas (CI 95%)", z.ci_high)):
    saved_m = d * vol
    for cost in C.COST_SCENARIOS:
        rows.append(dict(skenario=label, selisih_rate=d, volume_per_bulan=vol, unit_per_bulan=saved_m, unit_per_tahun=saved_m * 12, biaya_per_unit=cost,
                         hemat_per_tahun=saved_m * 12 * cost, label="estimated/simulated"))
imp = pd.DataFrame(rows); imp.to_csv(C.RES_ANALYSIS / "impact.csv", index=False)

# ---- ground truth
gt = json.loads(C.GROUND_TRUTH.read_text(encoding="utf-8"))
prod, ng, op, cm = prepare()
cl = pd.read_csv(C.RES_PREP / "cleaning_log.csv").set_index("rule")
c = cause.pivot(index="defect_code", columns="period", values="rate")
dr = (c.before - c.after)
dim = R("dim.csv"); sh = dim[dim.dim == "shift"].pivot(index="val", columns="period", values="rate_id")
gap_b, gap_a = sh.loc["Shift 2", "before"] - sh.loc["Shift 1", "before"], sh.loc["Shift 2", "after"] - sh.loc["Shift 1", "after"]
ins = ng[ng.is_insulation]
# ID-02 sebelum vs sesudah bracket in-house (Sep-Okt dibanding Jan-Agu)
cm3 = cm.loc[cm.cm_id == 3, "start_date"].iloc[0]
pre, post = prod[(prod.date < cm3) & (prod.date >= cm3 - pd.Timedelta(days=90))], prod[prod.date >= cm3 + pd.Timedelta(days=10)]
x_pre, x_post = ((ng.defect_code == "ID-02") & ng.date.isin(pre.date) & (ng.date < cm3)).sum(), ((ng.defect_code == "ID-02") & (ng.date >= cm3 + pd.Timedelta(days=10))).sum()
zz, pp = proportions_ztest([x_pre, x_post], [pre.input_qty.sum(), post.input_qty.sum()])
cm_ok = cmx.within_7_days.sum()
vol_chg = vr.loc["Input per bulan", "change"]
raw_n = gt["raw_rows"]; inj = gt["dirty_injected"]
found = {"ng_gt_input": int(cl.loc["P4", "rows_fixed"]), "date": int(cl.loc["P1", "rows_dropped"] + cl.loc["N1", "rows_dropped"]), "dup": int(cl.loc["P2", "rows_dropped"] + cl.loc["N2", "rows_dropped"]),
         "typo": int(cl.loc["N3", "rows_fixed"]), "shift": int(cl.loc["P3", "rows_fixed"] + cl.loc["N4", "rows_fixed"])}
planted = {"ng_gt_input": inj["prod_ng_gt_input"], "date": inj["prod_date_out_of_period"] + inj["ng_date_out_of_period"], "dup": inj["prod_duplicate"] + inj["ng_duplicate"],
           "typo": inj["ng_code_typo"], "shift": inj["prod_shift_blank"] + inj["ng_shift_blank"]}
clean_prod, clean_ng = len(prod), len(ng)
dirty_ok = found == planted and clean_prod == gt["clean_rows"]["production_daily"] and clean_ng == gt["clean_rows"]["ng_log"]
G = [
    dict(fact_no=1, fakta="Rate insulation damage turun dari sekitar 3,0% menjadi sekitar 2,2% dan signifikan",
         ditanam=f"before {gt['facts']['1_rate_before_target']:.1%}, after sekitar {gt['facts']['1_rate_after_approx']:.1%}",
         ditemukan=f"before {z.rate_before:.2%}, after {z.rate_after:.2%}, p = {z.p_value:.1e}", hasil="Sesuai" if abs(z.rate_before - .03) <= .0015 and abs(z.rate_after - .022) <= .0025 and z.significant else "Tidak"),
    dict(fact_no=2, fakta="Volume produksi after sekitar 30% lebih tinggi, sehingga jumlah NG turun lebih sedikit dari rate",
         ditanam="volume after sekitar +30%", ditemukan=f"volume per bulan {vol_chg:+.1%}; NG per bulan {vr.loc['NG insulation damage per bulan', 'change']:+.1%}; rate {vr.loc['Insulation damage rate', 'change']:+.1%}",
         hasil="Sesuai" if 0.25 <= vol_chg <= 0.35 and vr.loc['NG insulation damage per bulan', 'change'] > vr.loc['Insulation damage rate', 'change'] else "Tidak"),
    dict(fact_no=3, fakta="Tiga countermeasure dipasang bertahap; tiap tanggal menimbulkan penurunan yang terlihat (selisih paling lama 1 minggu)",
         ditanam="CM1 " + cm.start_date.iloc[0].date().isoformat() + ", CM2 " + cm.start_date.iloc[1].date().isoformat() + ", CM3 " + cm.start_date.iloc[2].date().isoformat(),
         ditemukan="titik ubah mingguan: " + "; ".join(f"CM{r.cm_id} {r.offset_days:+d} hari" for r in cmx.itertuples()), hasil="Sesuai" if cm_ok == 3 else "Sebagian" if cm_ok else "Tidak"),
    dict(fact_no=4, fakta="Penurunan terbesar pada ID-01 (perakitan); ID-02 (tepi bracket) turun setelah bracket in-house; Shift 2 lebih tinggi di before lalu selisihnya mengecil",
         ditanam="ID-01 turun paling besar; ID-02 turun setelah CM3; selisih Shift 2 vs Shift 1 mengecil",
         ditemukan=f"turun ID-01 {dr['ID-01'] * 100:.2f} poin vs ID-02 {dr['ID-02'] * 100:.2f} poin; ID-02 90 hari sebelum vs setelah CM3 p = {pp:.2f}; selisih Shift 2 {gap_b * 100:+.2f} poin (before) menjadi {gap_a * 100:+.2f} (after)",
         hasil="Sesuai" if dr["ID-01"] > dr["ID-02"] and gap_a < gap_b and x_post / post.input_qty.sum() < x_pre / pre.input_qty.sum() else "Sebagian"),
    dict(fact_no=5, fakta="Sekitar 2-3% data kotor disisipkan (NG > input, tanggal di luar periode, baris ganda, kode salah ketik, shift kosong)",
         ditanam=f"{sum(inj.values())} baris bermasalah ({gt['dirty_pct']['production_daily']}% production, {gt['dirty_pct']['ng_log']}% ng_log)",
         ditemukan=f"{sum(found.values())} baris ditemukan dan ditangani; baris bersih {clean_prod} + {clean_ng} sama dengan data asal", hasil="Sesuai" if dirty_ok else "Tidak"),
]
pd.DataFrame(G).to_csv(C.RES_ANALYSIS / "ground_truth_check.csv", index=False)
print(imp[imp.biaya_per_unit == C.COST_PER_HARNESS].round(1).to_string(index=False)); print(pd.DataFrame(G)[["fact_no", "ditemukan", "hasil"]].to_string(index=False))
