"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import DB_PATH, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, cs, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, esc, gbars, hbars,  # noqa: E402
                        legend, lines, pill, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Pendukung", 3: "Pendukung", 4: "Utama", 5: "Utama", 6: "Tambahan", 7: "Utama", 8: "Pendukung",
        9: "Utama", 10: "Pendukung", 11: "Utama", 12: "Utama", 13: "Utama", 14: "Utama"}
QT = {1: "Berapa insulation damage rate sebelum dan sesudah perbaikan, dan berapa persen penurunannya?",
      2: "Apakah kesimpulan berbeda jika hanya melihat jumlah NG, tanpa membagi dengan jumlah input?",
      3: "Apakah penurunan terjadi di ketiga tipe harness (A, B, dan C)?",
      4: "Apakah penurunan itu signifikan secara statistik, atau masih mungkin terjadi karena kebetulan?",
      5: "Berapa rentang penurunan yang paling mungkin, dari nilai terendah sampai tertinggi?",
      6: "Berapa lama data after harus dikumpulkan agar penurunan yang lebih kecil tetap bisa dibuktikan?",
      7: "Setelah perbaikan, apakah ada minggu di mana defect tiba-tiba melonjak?",
      8: "Kapan penurunan mulai terlihat, dan apakah waktunya cocok dengan tanggal pemasangan tiap countermeasure?",
      9: "Sumber insulation damage mana yang paling banyak turun: cara perakitan di assembly board atau tepi bracket yang tajam?",
      10: "Apakah penurunan NG disebabkan oleh operator baru yang semakin terampil, bukan oleh penerapan countermeasure?",
      11: "Berapa harness yang terselamatkan per bulan dan per tahun?",
      12: "Berapa estimasi penghematan biaya per tahun?",
      13: "Berapa persen data yang tidak valid, dan apakah hasil uji berubah jika data itu dibuang atau dikoreksi?",
      14: "Apakah angka defect rate dari database sama persis dengan hitungan manual di Excel?"}
WARN = set()      # pertanyaan yang dijawab dengan catatan (dipakai chip, ringkasan, dan tabel evaluasi)


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
pv = lambda p: "&lt; 0,001" if p < 0.001 else D(p, 3)
MONTH = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "Mei", "06": "Jun", "07": "Jul", "08": "Agu", "09": "Sep", "10": "Okt"}
TGL = lambda s: f"{int(str(s)[8:10])} {MONTH[str(s)[5:7]]}"

# ---------------------------------------------------------------- data
per, wk, mon = R("period.csv").set_index("period"), R("pchart.csv"), R("month.csv")
Z, dim, cause, cmo = R("ztest.csv").set_index("scope"), R("dim.csv"), R("cause.csv"), R("cause_month.csv")
brk, stn, vr, ss = R("bracket.csv"), R("station.csv"), R("volume_vs_rate.csv").set_index("metric"), R("sample_size.csv")
cmx, cps, cpt, mdl = R("cm_effect.csv"), R("cm_steps.csv"), R("changepoint.csv").iloc[0], R("model.csv")
imp, sens, gtc = R("impact.csv"), R("sensitivity.csv"), R("ground_truth_check.csv")
cx, ce = R("crosscheck.csv"), R("crosscheck_excel.csv")
rows, dq, cons, ctest, clog = R("table_rows.csv"), R("data_quality_summary.csv"), R("consistency_checks.csv"), R("constraint_tests.csv"), R("cleaning_log.csv")
gt = json.loads((REPO / "project" / "data" / "ground_truth.json").read_text(encoding="utf-8"))
dash = pd.read_csv(RES_PRESENT / "dash_rows.csv")
cmlog = pd.read_csv(REPO / "project" / "data" / "raw" / "countermeasure_log.csv") if (REPO / "project" / "data" / "raw" / "countermeasure_log.csv").exists() else dash.iloc[0:0]
con = duckdb.connect(str(DB_PATH), read_only=True)
dbc = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("production_daily", "ng_log", "dim_operator", "countermeasure_log")}
cm = con.execute("SELECT cm_id, cm_name, station, start_date FROM countermeasure_log ORDER BY cm_id").df()
ndays, nop, nnew = con.execute("SELECT count(DISTINCT date) FROM production_daily").fetchone()[0], dbc["dim_operator"], con.execute("SELECT count(*) FROM dim_operator WHERE status='baru'").fetchone()[0]
sample = con.execute("""SELECT date, shift, harness_type, operator_id, input_qty, ok_qty, ng_qty FROM production_daily WHERE date BETWEEN '2026-04-06' AND '2026-04-06' ORDER BY shift, harness_type""").fetchall()
con.close()

z0 = Z.loc["Insulation damage (ID-01+02+03)"]
zall = Z.loc["Semua NG (termasuk defect lain)"]
pb, pt, pa = per.loc["before"], per.loc["transisi"], per.loc["after"]
vol, ngm, rt = vr.loc["Input per bulan"], vr.loc["NG insulation damage per bulan"], vr.loc["Insulation damage rate"]
imp_p = imp[imp.biaya_per_unit == 150_000].set_index("skenario")
ipt, ilo, ihi = imp_p.loc["titik (hasil uji)"], imp_p.loc["batas bawah (CI 95%)"], imp_p.loc["batas atas (CI 95%)"]
inp_all = pb.input_qty + pt.input_qty + pa.input_qty
ng_all = int(dash[["ng_id01", "ng_id02", "ng_id03", "ng_other"]].sum().sum())
bad_total = int(dq.bad_rows.iloc[-1])
c3 = cause.pivot(index="defect_code", columns="period", values="rate")
dc = {k: Z.loc[v] for k, v in (("ID-01", "ID-01 Perakitan"), ("ID-02", "ID-02 Tepi bracket"), ("ID-03", "ID-03 Lain-lain"))}
ZT = {t: Z.loc[f"Harness tipe {t}"] for t in "ABC"}
mrate = mon.set_index("month")

# ---- hitungan turunan dari data
wk["week_start"] = pd.to_datetime(wk.week_start)
out_wk = wk[wk.out.notna()]
out_after = out_wk[out_wk.period == "after"]
run8 = wk[wk.run_below_before_cl >= 8].iloc[0]
run8_start = wk.loc[run8.name - 7, "week_start"]
n_after_wk = int((wk.period == "after").sum())
cmx = cmx.set_index("cm_id")
st1 = cps[cps.series == "Insulation damage (semua)"].set_index("term")
st_id1, st_id2 = cps[(cps.series == "ID-01 Perakitan") & (cps.term == "cm2")].iloc[0], cps[(cps.series == "ID-02 Tepi bracket") & (cps.term == "cm3")].iloc[0]
m_adj, m_raw = mdl[(mdl.model.str.startswith("Disesuaikan")) & (mdl.term == "after")].iloc[0], mdl[(mdl.model == "Tanpa penyesuaian")].iloc[0]
m_new = mdl[(mdl.model.str.startswith("Disesuaikan")) & (mdl.term == "op_baru")].iloc[0]
sd = dim[dim.dim == "shift_status"].pivot(index="val", columns="period", values="rate_id")
sh = dim[dim.dim == "shift"].pivot(index="val", columns="period", values="rate_id")
gap_b, gap_a = sh.loc["Shift 2", "before"] - sh.loc["Shift 1", "before"], sh.loc["Shift 2", "after"] - sh.loc["Shift 1", "after"]
lama, baru = Z.loc["Operator lama"], Z.loc["Operator baru"]
mde = ss.iloc[-1]
s10, s15 = ss[ss.rel_drop == 0.10].iloc[0], ss[ss.rel_drop == 0.15].iloc[0]
s05 = ss[ss.rel_drop == 0.05].iloc[0]
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
gtm = gtc.set_index("fact_no")
cm_dates = {int(r.cm_id): pd.Timestamp(r.start_date) for r in cm.itertuples()}
gap_cm = (cm_dates[2] - cm_dates[1]).days
n_cm12 = int(dash[(dash.date >= str(cm_dates[1].date())) & (dash.date < str(cm_dates[2].date()))].input_qty.sum())

assert z0.significant and abs(z0.rate_before - 0.03) < 0.0015 and abs(z0.rate_after - 0.022) < 0.0025
assert gtc.hasil.tolist() == ["Sesuai", "Sesuai", "Sebagian", "Sesuai", "Sesuai"], gtc.hasil.tolist()
assert (cx.status == "PASS").all() and (ce.status == "PASS").all() and (ctest.outcome == "ditolak").all() and (cons.violations == 0).all()
assert len(out_after) == 0 and (z0.p_value < 0.001) and all(ZT[t].significant for t in "ABC") and dc["ID-03"].p_value > 0.05
assert dc["ID-01"]["diff"] > dc["ID-02"]["diff"] and gap_a < gap_b and lama.significant and baru.significant
assert abs(vol.change - 0.31) < 0.03 and ngm.change > rt.change

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(dbc["production_daily"]), "baris production_daily", f"Dari {I(dq.raw_rows[0])} baris mentah. Satu baris = satu tipe harness, satu shift, satu hari."),
    kp("amber", I(dbc["ng_log"]), "baris ng_log", f"Dari {I(dq.raw_rows[1])} baris mentah. Satu baris = satu harness NG. Sesuai perkiraan rancangan (±2.500)."),
    kp("teal", I(inp_all), "harness diproduksi", f"Jan–Okt 2026: before {I(pb.input_qty)}, transisi {I(pt.input_qty)}, after {I(pa.input_qty)}."),
    kp("plum", I(ndays), "hari kerja", f"Senin sampai Jumat, 8 hari libur dikeluarkan. {I(nop)} operator ({I(nnew)} baru)."),
    kp("rose", I(bad_total), "baris kotor ditemukan", f"{I(dq.bad_rows[0])} di production_daily ({D(dq.bad_pct[0], 2)}%), {I(dq.bad_rows[1])} di ng_log ({D(dq.bad_pct[1], 2)}%). Semua ditangani."),
    kp("sky", I(ng_all), "harness NG", f"{I(pb.ng_id + pt.ng_id + pa.ng_id)} insulation damage, sisanya defect lain. Tidak ada kolom yang kosong."),
    '</div><h3>1.1 Data simulasi (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Cuplikan production_daily (6 April 2026)</h4>' + table(
    ["date", "shift", "harness_type", "operator_id", "input_qty", "ok_qty", "ng_qty"],
    [[str(r[0]), r[1], r[2], r[3], I(r[4]), I(r[5]), I(r[6])] for r in sample]) + \
    '<p>Contoh baris tabel bersih. Data dibuat oleh skrip dengan seed tetap, jadi cuplikan ini sama setiap dijalankan ulang.</p></div>'
label = {"P1": "Tanggal di luar periode", "P2": "Baris ganda", "P3": "Shift kosong", "P4": "ng_qty lebih besar dari input_qty",
         "N1": "Tanggal di luar periode", "N2": "Baris ganda", "N3": "Kode defect salah ketik", "N4": "Shift kosong"}
rp1 += '<div class="card"><h4>Tabel 1.1. Baris mentah, bersih, dan bermasalah per tabel (Q13)</h4>' + table(
    ["Tabel", "Mentah", "Bersih", "Bermasalah", "% bermasalah"],
    [[f"<code>{r.table}</code>", I(r.raw_rows), I(r.clean_rows), I(r.bad_rows), D(r.bad_pct, 2) + "%"] for r in dq.itertuples()]) + \
    table(["Aturan", "Masalah", "Tabel", "Ditemukan", "Ditanam generator", "Keputusan"],
          [[r.rule, label[r.rule], f"<code>{r.table}</code>", I(r.rows_found),
            I({"P1": gt["dirty_injected"]["prod_date_out_of_period"], "P2": gt["dirty_injected"]["prod_duplicate"], "P3": gt["dirty_injected"]["prod_shift_blank"],
               "P4": gt["dirty_injected"]["prod_ng_gt_input"], "N1": gt["dirty_injected"]["ng_date_out_of_period"], "N2": gt["dirty_injected"]["ng_duplicate"],
               "N3": gt["dirty_injected"]["ng_code_typo"], "N4": gt["dirty_injected"]["ng_shift_blank"]}[r.rule]), r.decision] for r in clog.itertuples() if r.rule != "P5"])
rp1 += Q(13, f"{D(dq.bad_pct[0], 2)}% baris production_daily dan {D(dq.bad_pct[1], 2)}% baris ng_log tidak valid. Semuanya ditemukan ({I(bad_total)} baris, sama dengan jumlah yang ditanam) dan ditangani: "
             f"{I(clog.rows_dropped.sum())} baris dibuang, {I(clog.rows_fixed.sum())} diperbaiki. Hasil tidak berubah secara berarti: rate before dan after bergeser paling banyak "
             f"{D(max(abs(sens.rate_before - z0.rate_before).max(), abs(sens.rate_after - z0.rate_after).max()) * 100, 2)} poin dan kesimpulan uji sama pada tiga perlakuan (Tabel 2.9a).")
rp1 += '<p class="note">Pembahasan lengkap Q13 (perbandingan tiga perlakuan) ada di <a href="#sec29">2.9</a>.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>harness_qcc.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["production_daily", I(dbc["production_daily"]), "Hasil harian per tipe harness, shift, tanggal. Kunci utama (date, shift, harness_type)."],
     ["ng_log", I(dbc["ng_log"]), "Satu baris per harness NG. Kunci asing ke production_daily dan dim_operator."],
     ["countermeasure_log", I(dbc["countermeasure_log"]), "Tanggal pemasangan tiap countermeasure; dipakai menurunkan periode before, transisi, after."],
     ["dim_operator", I(dbc["dim_operator"]), "Shift, tanggal masuk, dan status (baru atau lama) tiap operator."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(
    ["Baris salah yang dicoba dimasukkan", "Hasil"], [[r.test, OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Kesepuluh jenis data salah ditolak oleh database. Setelah cleaning, {I(len(cons))} pemeriksaan konsistensi antar tabel menghasilkan 0 pelanggaran.</p></div>'
FILES = {"period": ("Rate per periode (before, transisi, after)", "Q1, Q2"), "week": ("Rate per minggu", "Q7, Q8"), "month": ("Rate per bulan", "Q1, Q2"),
         "dim": ("Rate per tipe harness, shift, status operator", "Q3, Q10"), "cause": ("Rate per kode defect dan periode", "Q9"), "cause_month": ("Rate per kode defect per bulan", "Q8, Q9"),
         "bracket": ("NG tepi bracket menurut sumber bracket", "Q9"), "station": ("Stasiun tempat NG ditemukan", "Q9"), "ztest": ("z-test dua proporsi dan CI per kelompok", "Q3, Q4, Q5, Q9, Q10"),
         "volume_vs_rate": ("Jumlah NG vs rate vs volume", "Q2"), "sample_size": ("Jumlah sampel minimum", "Q6"), "pchart": ("p-chart mingguan dengan batas kendali", "Q7"),
         "cm_effect": ("Titik ubah mingguan per countermeasure", "Q8"), "cm_steps": ("Efek langkah per countermeasure (regresi logistik)", "Q8, Q9"),
         "changepoint": ("Titik ubah terkuat seluruh deret", "Q8"), "model": ("Regresi logistik faktor operator", "Q10"), "impact": ("Skenario unit terselamatkan dan penghematan", "Q11, Q12"),
         "sensitivity": ("Tiga perlakuan data kotor", "Q13"), "crosscheck": ("SQL vs pandas", "Q14"), "crosscheck_excel": ("SQL/Python vs Excel", "Q14"),
         "ground_truth_check": ("Fakta ditanam vs temuan", "validasi"), "cleaning_log": ("Log cleaning per aturan", "Q13"), "data_quality_summary": ("Ringkasan data kotor", "Q13"),
         "table_rows": ("Baris per tabel", "Q13"), "consistency_checks": ("Pemeriksaan konsistensi", "Q13"), "constraint_tests": ("Uji constraint database", "Q13")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"],
    [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI (definisi di <code>project/docs/definitions.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["Defect rate (insulation damage)", "NG berkode ID-xx ÷ input", f"before {P(z0.rate_before, 2)}, after {P(z0.rate_after, 2)}", f"{I(z0.n_before)} dan {I(z0.n_after)} harness"],
     ["Penurunan relatif", "(before − after) ÷ before", P(z0.rel_drop, 1), f"{I(z0.x_before)} dan {I(z0.x_after)} NG"],
     ["p-value", "z-test dua proporsi, α = 0,05", pv(z0.p_value), f"z = {D(z0.z, 2)}"],
     ["Unit terselamatkan", "selisih rate × volume per bulan × 12", f"{I(ipt.unit_per_tahun)} per tahun", f"volume {I(vol.after)} per bulan"],
     ["Estimasi penghematan (estimated)", "unit terselamatkan × biaya per harness (asumsi)", f"Rp {I(ipt.hemat_per_tahun / 1e6)} juta per tahun", "biaya Rp 150.000 per harness"]]) + \
    f'<p>Rate turun {D(z0["diff"] * 100, 2)} poin ({P(z0.rel_drop)} relatif). Karena volume after {P(vol.change)} lebih tinggi, jumlah NG per bulan hanya turun {P(abs(ngm.change))}.</p></div>'

# ---------------------------------------------------------------- 2. business questions
cmap = {"before": GREY, "transisi": SOFT, "after": BLUE}
mlab = lambda m: MONTH[m[5:7]]
s21 = mk('<h3 id="sec21">2.1 Rate before dan after, dan pengaruh volume <span class="qlist">Q1, Q2</span></h3><div class="card">',
         Q(1, f"Rate insulation damage before (Jan–Jun) {P(z0.rate_before, 2)} ({I(z0.x_before)} dari {I(z0.n_before)} harness), after (Agu–Okt) {P(z0.rate_after, 2)} ({I(z0.x_after)} dari {I(z0.n_after)}). "
              f"Turun {D(z0['diff'] * 100, 2)} poin atau {P(z0.rel_drop)} relatif. Bulan transisi (Jul) {P(pt.rate_id, 2)}, berada di antara keduanya."),
         Q(2, f"Ya, berbeda. Jumlah NG insulation damage per bulan hanya turun {P(abs(ngm.change))} ({D(ngm.before)} menjadi {D(ngm.after)}), sedangkan rate turun {P(abs(rt.change))}. "
              f"Penyebabnya volume produksi per bulan naik {P(vol.change)} ({I(vol.before)} menjadi {I(vol.after)} harness). Hanya melihat jumlah NG membuat perbaikan tampak jauh lebih kecil dari kenyataan."),
         '<h4>Grafik 2.1a. Insulation damage rate per bulan</h4>',
         bars([(mlab(m), r.rate_id, cmap[r.period], f"{m}: {P(r.rate_id, 2)} ({I(r.ng_id)} dari {I(r.input_qty)} harness), {r.period}") for m, r in mrate.iterrows()],
              lambda v: P(v, 1), "Rate per bulan", rot=0, small=True),
         legend([(GREY, "Before"), (SOFT, "Transisi (tidak dipakai di uji)"), (BLUE, "After")]),
         '<h4>Tabel 2.1b. Rate per periode</h4>',
         table(["Periode", "Input (harness)", "NG insulation damage", "Rate", "NG semua kode", "Rate semua NG"],
               [[k, I(r.input_qty), I(r.ng_id), P(r.rate_id, 2), I(r.ng_all), P(r.rate_all, 2)] for k, r in (("Before (Jan–Jun)", pb), ("Transisi (Jul)", pt), ("After (Agu–Okt)", pa))]),
         '<h4>Tabel 2.1c. Jumlah NG, volume, dan rate (rata-rata per bulan)</h4>',
         table(["Ukuran", "Before", "After", "Perubahan"],
               [["Input per bulan", I(vol.before), I(vol.after), f"+{P(vol.change)}"], ["NG insulation damage per bulan", D(ngm.before), D(ngm.after), f"−{P(abs(ngm.change))}"],
                ["Rate", P(rt.before, 2), P(rt.after, 2), f"−{P(abs(rt.change))}"]]),
         '<p>Rate = NG insulation damage ÷ input. Periode diturunkan dari tabel <code>countermeasure_log</code> (definisi di <code>project/docs/definitions.md</code>).</p></div>')
s22 = mk('<h3 id="sec22">2.2 Tiga tipe harness <span class="qlist">Q3</span></h3><div class="card">',
         Q(3, f"Ya, turun di ketiganya dan semuanya signifikan: tipe A {P(ZT['A'].rate_before, 2)} menjadi {P(ZT['A'].rate_after, 2)} (−{P(ZT['A'].rel_drop)}), "
              f"tipe B {P(ZT['B'].rate_before, 2)} menjadi {P(ZT['B'].rate_after, 2)} (−{P(ZT['B'].rel_drop)}), tipe C {P(ZT['C'].rate_before, 2)} menjadi {P(ZT['C'].rate_after, 2)} (−{P(ZT['C'].rel_drop)}). "
              f"Tipe C paling tinggi sebelum dan sesudah, tetapi sampelnya paling kecil ({I(ZT['C'].n_after)} harness after)."),
         '<h4>Grafik 2.2a. Rate per tipe harness, before vs after</h4>',
         gbars([f"Tipe {t}" for t in "ABC"], [("Before", GREY, [ZT[t].rate_before for t in "ABC"]), ("After", BLUE, [ZT[t].rate_after for t in "ABC"])], lambda v: P(v, 1), "Rate per tipe harness", rot=0),
         legend([(GREY, "Before"), (BLUE, "After")]),
         '<h4>Tabel 2.2b. z-test per tipe harness</h4>',
         table(["Tipe", "Rate before", "Rate after", "Penurunan relatif", "z", "p-value", "CI 95% selisih (poin)"],
               [[f"Tipe {t}", P(ZT[t].rate_before, 2), P(ZT[t].rate_after, 2), P(ZT[t].rel_drop), D(ZT[t].z, 2), pv(ZT[t].p_value), f"{D(ZT[t].ci_low * 100, 2)} s.d. {D(ZT[t].ci_high * 100, 2)}"] for t in "ABC"]), '</div>')
s23 = mk('<h3 id="sec23">2.3 Uji signifikansi dan rentang penurunan <span class="qlist">Q4, Q5</span></h3><div class="card">',
         Q(4, f"Signifikan. z-test dua proporsi memberi z = {D(z0.z, 2)} dan p-value {pv(z0.p_value)}, jauh di bawah batas 0,05. Kemungkinan penurunan ini hanya kebetulan sangat kecil."),
         Q(5, f"Selisih rate paling mungkin berada di antara {D(z0.ci_low * 100, 2)} dan {D(z0.ci_high * 100, 2)} poin (CI 95%), dengan titik tengah {D(z0['diff'] * 100, 2)} poin. "
              f"Dalam relatif, itu sekitar {D(z0.ci_low / z0.rate_before * 100, 0)}% sampai {D(z0.ci_high / z0.rate_before * 100, 0)}% dari rate before. Batas bawah tetap di atas nol."),
         '<h4>Grafik 2.3a. Selisih rate (poin persentase) per kelompok; CI 95% ada di tooltip dan Tabel 2.3b</h4>',
         hbars([(k, Z.loc[k]["diff"] * 100, BLUE if Z.loc[k].significant else HI,
                 f"{k}: selisih {D(Z.loc[k]['diff'] * 100, 2)} poin, CI 95% {D(Z.loc[k].ci_low * 100, 2)} s.d. {D(Z.loc[k].ci_high * 100, 2)}, p {pv(Z.loc[k].p_value)}")
                for k in ["Insulation damage (ID-01+02+03)", "Semua NG (termasuk defect lain)", "ID-01 Perakitan", "ID-02 Tepi bracket", "ID-03 Lain-lain"]],
               lambda v: D(v, 2), "Selisih rate per kelompok", 1.5),
         legend([(BLUE, "Signifikan (p < 0,05)"), (HI, "Belum signifikan")]),
         '<h4>Tabel 2.3b. z-test dua proporsi dan CI 95% (Wald)</h4>',
         table(["Kelompok", "Rate before", "Rate after", "Selisih (poin)", "z", "p-value", "CI 95% selisih (poin)"],
               [[k, P(r.rate_before, 2), P(r.rate_after, 2), D(r["diff"] * 100, 2), D(r.z, 2), pv(r.p_value), f"{D(r.ci_low * 100, 2)} s.d. {D(r.ci_high * 100, 2)}"]
                for k, r in Z.loc[["Insulation damage (ID-01+02+03)", "Semua NG (termasuk defect lain)", "ID-01 Perakitan", "ID-02 Tepi bracket", "ID-03 Lain-lain"]].iterrows()]),
         '<p>Hipotesis nol: rate before sama dengan rate after. Varians gabungan, dua sisi, α = 0,05. Kode ID-03 sangat jarang, sehingga penurunannya belum signifikan.</p></div>')
s24 = mk('<h3 id="sec24">2.4 Jumlah data after yang dibutuhkan <span class="qlist">Q6</span></h3><div class="card">',
         Q(6, f"Dengan {I(pa.input_qty)} harness after (3 bulan), penurunan relatif terkecil yang masih terbukti (power 80%) adalah {P(mde.rel_drop)} (rate after {P(mde.rate_after, 2)}). "
              f"Penurunan 15% butuh sekitar {I(s15.n_per_group)} harness per kelompok ({D(s15.months_after)} bulan after), 10% butuh {I(s10.n_per_group)} ({D(s10.months_after)} bulan), "
              f"dan 5% butuh {I(s05.n_per_group)} ({D(s05.months_after, 1)} bulan). Penurunan sebesar hasil project ini ({P(z0.rel_drop)}) sudah terbukti dengan kurang dari 1 bulan data."),
         '<h4>Tabel 2.4a. Jumlah sampel minimum per kelompok (power 80%, α = 0,05)</h4>',
         table(["Penurunan relatif", "Rate before", "Rate after", "n per kelompok", "Bulan data after", "Power dengan data saat ini"],
               [[P(r.rel_drop), P(r.rate_before, 2), P(r.rate_after, 2), I(r.n_per_group), D(r.months_after, 1), P(r.power_actual)] for r in ss.itertuples()]),
         '<p>Baris terakhir: penurunan terkecil yang masih terdeteksi dengan data after saat ini. Volume after rata-rata per bulan: '
         f'{I(vol.after)} harness.</p></div>')
cmband = [i for i, w in enumerate(wk.week_start) for d in cm_dates.values() if w <= d < w + pd.Timedelta(days=7)]
s25 = mk('<h3 id="sec25">2.5 Stabilitas dan waktu penurunan <span class="qlist">Q7, Q8</span></h3><div class="card">',
         Q(7, f"Tidak ada. Dari {I(n_after_wk)} minggu after, 0 minggu berada di luar batas kendali p-chart, dan semuanya berada di bawah garis tengah before. "
              f"Di periode before hanya {I(len(out_wk))} minggu di luar batas ({TGL(out_wk.week_start.iloc[0].date())}, {D(out_wk.p.iloc[0] * 100, 2)}%, minggu libur dengan input kecil). Proses after stabil."),
         Q(8, f"Penurunan mulai terlihat pada minggu {TGL(cpt.changepoint_week)} (titik ubah terkuat; {abs(int(cpt.offset_days))} hari sebelum CM1 pada {TGL(cm_dates[1].date())}). "
              f"Delapan minggu berturut-turut di bawah garis tengah before tercapai pada {TGL(run8.week_start.date())}, dan rangkaian itu dimulai {TGL(run8_start.date())}. "
              f"Waktu tiap countermeasure tidak seluruhnya cocok: titik ubah CM1 {int(cmx.loc[1].offset_days):+d} hari, CM2 {int(cmx.loc[2].offset_days):+d} hari, CM3 {int(cmx.loc[3].offset_days):+d} hari. "
              f"CM1 dan CM2 hanya berjarak {I(gap_cm)} hari ({I(n_cm12)} harness), sehingga efek keduanya tidak bisa dipisahkan. Regresi menunjuk CM1 (OR {D(st1.loc['cm1'].odds_ratio, 2)}) dan CM3 (OR {D(st1.loc['cm3'].odds_ratio, 2)}), bukan CM2 (OR {D(st1.loc['cm2'].odds_ratio, 2)}, p {D(st1.loc['cm2'].p_value, 2)}).", warn=True),
         '<h4>Grafik 2.5a. p-chart mingguan dengan batas 3σ (area kuning: minggu pemasangan countermeasure)</h4>',
         lines([TGL(w.date()) for w in wk.week_start], [("UCL", HI, 1.3, list(wk.ucl)), ("LCL", HI, 1.3, list(wk.lcl)), ("Garis tengah", GREY, 1.5, list(wk.cl)), ("Rate mingguan", BLUE, 2.5, list(wk.p))],
               lambda v: P(v, 1), "p-chart mingguan", zero=True, bands=cmband, band_label="CM dipasang minggu"),
         legend([(BLUE, "Rate mingguan"), (GREY, "Garis tengah (before, lalu after)"), (HI, "UCL dan LCL (3σ)")]),
         f'<p>Batas kendali dihitung terpisah: before memakai rate {P(pb.rate_id, 2)}, after {P(pa.rate_id, 2)}; minggu transisi dinilai dengan batas before. Minggu dengan input kurang dari 500 harness (hanya 2 Jan) dibuang.</p>',
         '<h4>Tabel 2.5b. Titik ubah mingguan per countermeasure (deret mingguan penyebab sasaran, ±9 minggu)</h4>',
         table(["Countermeasure", "Tanggal pasang", "Deret yang dilihat", "Titik ubah (minggu)", "Selisih (hari)", "Dalam 7 hari?"],
               [[f"CM{i}: {cm.cm_name[i - 1]}", TGL(cm_dates[i].date()), cmx.loc[i].series, TGL(cmx.loc[i].changepoint_week), f"{int(cmx.loc[i].offset_days):+d}", OK("Ya") if cmx.loc[i].within_7_days else NO("Tidak")] for i in (1, 2, 3)]),
         '<h4>Tabel 2.5c. Efek tiap countermeasure (regresi logistik, indikator langkah kumulatif, disesuaikan operator, shift, tipe harness)</h4>',
         table(["Deret", "Langkah", "Odds ratio", "CI 95%", "p-value"],
               [[r.series, f"CM{r.term[-1]}", D(r.odds_ratio, 2), f"{D(r.or_low, 2)} s.d. {D(r.or_high, 2)}", D(r.p_value, 3)] for r in cps.itertuples()]),
         '<p>Odds ratio di bawah 1 berarti rate turun setelah tanggal itu. Tiap langkah dihitung berurutan, jadi CM1 dan CM2 yang berdekatan saling menutupi.</p></div>')
bk = brk.pivot(index="period", columns="bracket_source", values="ng_id02").fillna(0)
m02 = cmo[cmo.defect_code == "ID-02"].set_index("month")
s26 = mk('<h3 id="sec26">2.6 Sumber penyebab <span class="qlist">Q9</span></h3><div class="card">',
         Q(9, f"Cara perakitan (ID-01) turun paling banyak: {P(c3.loc['ID-01', 'before'], 2)} menjadi {P(c3.loc['ID-01', 'after'], 2)} (−{D(dc['ID-01']['diff'] * 100, 2)} poin, −{P(dc['ID-01'].rel_drop)}). "
              f"Tepi bracket (ID-02) turun {P(c3.loc['ID-02', 'before'], 2)} menjadi {P(c3.loc['ID-02', 'after'], 2)} (−{D(dc['ID-02']['diff'] * 100, 2)} poin, −{P(dc['ID-02'].rel_drop)}), dan baru turun jelas setelah bracket in-house dipakai "
              f"(Agu {P(m02.loc['2026-08'].rate, 2)}, Sep {P(m02.loc['2026-09'].rate, 2)}, Okt {P(m02.loc['2026-10'].rate, 2)}). Kode lain-lain (ID-03) kecil dan tidak berubah signifikan (p {D(dc['ID-03'].p_value, 2)})."),
         '<h4>Grafik 2.6a. Rate per kode insulation damage, before vs after</h4>',
         gbars(["ID-01 Perakitan", "ID-02 Tepi bracket", "ID-03 Lain-lain"], [("Before", GREY, [c3.loc[c, "before"] for c in c3.index[:3]]), ("After", BLUE, [c3.loc[c, "after"] for c in c3.index[:3]])],
               lambda v: P(v, 2), "Rate per sumber penyebab", rot=0),
         legend([(GREY, "Before"), (BLUE, "After")]),
         '<h4>Tabel 2.6b. Rate ID-02 (tepi bracket) per bulan dan sumber bracket</h4>',
         table(["Bulan", "Rate ID-02", "NG ID-02 sumber Supplier", "NG ID-02 sumber In-house"],
               [[mlab(m), P(r.rate, 2), I(((brk[(brk.period == per_) & (brk.bracket_source == "Supplier")].ng_id02.sum()) if False else 0)) if False else "", ""] for m, r in []]) if False else
         table(["Bulan", "Rate ID-02", "Rate ID-01"],
               [[mlab(m), P(m02.loc[m].rate, 2), P(cmo[(cmo.defect_code == "ID-01") & (cmo.month == m)].rate.iloc[0], 2)] for m in m02.index]),
         '<h4>Tabel 2.6c. NG ID-02 menurut sumber bracket dan periode</h4>',
         table(["Periode", "Supplier", "In-house"], [[p_, I(bk.loc[p_].get("Supplier", 0)), I(bk.loc[p_].get("In-house", 0))] for p_ in ("before", "transisi", "after")]), '</div>')
sdl = lambda k: sd.loc[k]
s27 = mk('<h3 id="sec27">2.7 Operator baru dan shift <span class="qlist">Q10</span></h3><div class="card">',
         Q(10, f"Sebagian. Operator baru memang lebih tinggi (rate before {P(baru.rate_before, 2)} vs operator lama {P(lama.rate_before, 2)}) dan turunnya lebih besar (−{P(baru.rel_drop)} vs −{P(lama.rel_drop)}), "
               f"jadi pembelajaran operator ikut berperan. Namun operator lama juga turun signifikan (p {pv(lama.p_value)}), dan efek periode after tetap besar setelah disesuaikan status operator, shift, dan tipe harness "
               f"(odds ratio {D(m_adj.odds_ratio, 2)} vs {D(m_raw.odds_ratio, 2)} tanpa penyesuaian). Selisih Shift 2 − Shift 1 mengecil dari {D(gap_b * 100, 2)} poin (before) menjadi {D(gap_a * 100, 2)} poin (after). "
               f"Pengaruh operator tidak bisa dipisahkan sepenuhnya dari countermeasure karena keduanya berubah bersamaan.", warn=True),
         '<h4>Grafik 2.7a. Rate per shift dan status operator, before vs after</h4>',
         gbars(list(sd.index), [("Before", GREY, list(sd.before)), ("After", BLUE, list(sd.after))], lambda v: P(v, 1), "Rate per shift dan status operator"),
         legend([(GREY, "Before"), (BLUE, "After")]),
         '<h4>Tabel 2.7b. Regresi logistik (rate after dibanding before, disesuaikan)</h4>',
         table(["Model", "Variabel", "Odds ratio", "CI 95%", "p-value"],
               [[r.model, {"after": "Periode after", "op_baru": "Operator baru", "shift2": "Shift 2", "type_B": "Tipe B", "type_C": "Tipe C"}[r.term], D(r.odds_ratio, 2), f"{D(r.or_low, 2)} s.d. {D(r.or_high, 2)}", pv(r.p_value) if r.p_value < 0.001 else D(r.p_value, 3)] for r in mdl.itertuples()]),
         '<p>Data transisi tidak dipakai. Satu baris produksi = satu pengamatan binomial (NG dari input).</p></div>')
imp_t = imp.copy()
s28 = mk('<h3 id="sec28">2.8 Dampak <span class="qlist">Q11, Q12</span></h3><div class="card">',
         Q(11, f"Sekitar {I(ipt.unit_per_bulan)} harness terselamatkan per bulan dan {I(ipt.unit_per_tahun)} per tahun (rentang CI 95%: {I(ilo.unit_per_tahun)} sampai {I(ihi.unit_per_tahun)} per tahun), "
               f"dihitung dari selisih rate {D(z0['diff'] * 100, 2)} poin × volume after {I(vol.after)} harness per bulan. Angka ini estimated, dari data simulasi."),
         Q(12, f"Dengan biaya Rp 150.000 per harness NG (asumsi), penghematan sekitar Rp {I(ipt.hemat_per_tahun / 1e6)} juta per tahun (rentang Rp {I(ilo.hemat_per_tahun / 1e6)} sampai {I(ihi.hemat_per_tahun / 1e6)} juta). "
               f"Biaya per unit adalah asumsi, bukan data aktual; skenario Rp 100.000 dan Rp 250.000 ada di Tabel 2.8a.", warn=True),
         '<h4>Tabel 2.8a. Skenario unit terselamatkan dan penghematan per tahun (estimated, simulated)</h4>',
         table(["Selisih rate yang dipakai", "Selisih (poin)", "Harness / bulan", "Harness / tahun", "Biaya per harness (Rp)", "Penghematan / tahun (Rp juta)"],
               [[r.skenario, D(r.selisih_rate * 100, 2), I(r.unit_per_bulan), I(r.unit_per_tahun), I(r.biaya_per_unit), I(r.hemat_per_tahun / 1e6)] for r in imp_t.itertuples()]),
         '<p>Unit terselamatkan = selisih rate × volume per bulan × 12. Semua angka berlabel estimated / simulated.</p></div>')
sens_l = {0: "A. Data mentah apa adanya", 1: "B. Baris bermasalah dibuang semua", 2: "C. Cleaning sesuai log (dipakai)"}
xl = ce.groupby("scope").status.apply(lambda s: (s == "PASS").all())
s29 = mk('<h3 id="sec29">2.9 Validitas data dan cek silang <span class="qlist">Q13, Q14</span></h3><div class="card">',
         Q(13, f"Ya, tiga perlakuan memberi kesimpulan sama: signifikan dengan p-value {pv(sens.p_value.max())}. Rate before {P(sens.rate_before.min(), 2)} sampai {P(sens.rate_before.max(), 2)} dan after {P(sens.rate_after.min(), 2)} sampai {P(sens.rate_after.max(), 2)}; "
               f"selisihnya {D(sens['diff'].min() * 100, 2)} sampai {D(sens['diff'].max() * 100, 2)} poin. Data mentah tanpa cleaning memberi rate sedikit lebih rendah karena kode salah ketik tidak terhitung sebagai insulation damage dan baris di luar periode ikut terhitung."),
         Q(14, f"Ya. {I(len(cx))} dari {I(len(cx))} pemeriksaan SQL vs pandas dan {I(len(ce))} dari {I(len(ce))} pemeriksaan SQL/Python vs Excel menghasilkan PASS (rate, z, p-value, CI). "
               f"Rumus Excel (SUMIFS, COUNTIFS, NORM.S.DIST) dihitung ulang oleh LibreOffice, bukan Microsoft Excel."),
         '<h4>Tabel 2.9a. Tiga perlakuan data kotor (Q13)</h4>',
         table(["Perlakuan", "Rate before", "Rate after", "Selisih (poin)", "z", "p-value"],
               [[sens_l[i], P(r.rate_before, 2), P(r.rate_after, 2), D(r["diff"] * 100, 2), D(r.z, 2), pv(r.p_value)] for i, r in sens.iterrows()]),
         '<h4>Tabel 2.9b. Lima fakta yang ditanam vs temuan</h4>',
         table(["No", "Fakta", "Ditemukan", "Hasil"], [[I(r.fact_no), cs(r.fakta), cs(r.ditemukan), OK("Sesuai") if r.hasil == "Sesuai" else PART(r.hasil)] for r in gtc.itertuples()]),
         '<h4>Tabel 2.9c. Cek silang SQL, pandas, dan Excel (Q14)</h4>',
         table(["Pembanding", "Pemeriksaan", "PASS", "Isi"],
               [["SQL vs pandas", I(len(cx)), I((cx.status == "PASS").sum()), "input, NG, rate per periode, minggu, bulan, tipe, shift, penyebab, bracket, stasiun"],
                ["SQL/Python vs Excel", I(len(ce)), I((ce.status == "PASS").sum()), "input, NG, rate, z, p-value, CI 95% untuk 6 kelompok, rate 3 kode penyebab"]]),
         '<p>Dari lima fakta, empat ditemukan penuh. Fakta 3 (tanggal tiap countermeasure terlihat dalam 1 minggu) hanya sebagian: penjelasannya di Q8.</p></div>')
QTITLES = {}
SEC = {1: "21", 2: "21", 3: "22", 4: "23", 5: "23", 6: "24", 7: "25", 8: "25", 9: "26", 10: "27", 11: "28", 12: "28", 13: "29", 14: "29"}
rp2_body = mk(s21, s22, s23, s24, s25, s26, s27, s28, s29)
qn_all = sorted(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body))
qn_uniq = sorted(set(qn_all) | {13})
assert qn_uniq == list(range(1, 15)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = mk('<div class="qchips">', "".join(
    f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 15)), '</div>')
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per grafik atau tabel bukti (2.1 sampai 2.9). Q13 muncul di Tabel 1.1 dan Tabel 2.9a.</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
ndash = len(list(RES_PRESENT.glob("dash_*.csv")))
npy = len(list((REPO / "project/code").rglob("*.py")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / "project/code").rglob("*.py"))
nsql = len(list((REPO / "project/code").rglob("*.sql")))
fm = lambda r: OK("Ditemukan") if r == "Sesuai" else PART(r)
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan dan dibuat ulang dengan seed tetap. Perbedaan: tanggal countermeasure dan besar efeknya disetel beberapa kali agar rate before 3,0% dan rate after sekitar 2,2%, '
         'fakta 3 (tanggal tiap countermeasure terlihat di control chart) hanya sebagian terbukti, dan efek operator baru ditambahkan sebagai faktor pengganggu. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, skrip generate_data.py", "Skrip <code>01_generate_data.py</code>, seed tetap, hasil identik setiap dijalankan; tanggal countermeasure bisa diubah lewat argumen", OK("Sesuai")],
             ["Ukuran", "3 tipe harness, 2 shift, ±20 operator, ±210 hari kerja", f"3 tipe harness, 2 shift, {I(nop)} operator, {I(ndays)} hari kerja", OK("Sesuai")],
             ["Volume", "6.000–8.000 harness per bulan", f"{I(mon.input_qty.min())} sampai {I(mon.input_qty.max())} per bulan; after {P(vol.change)} lebih tinggi dari before", OK("Sesuai")],
             ["production_daily", "±1.300 baris", f"{I(dq.raw_rows[0])} mentah, {I(dq.clean_rows[0])} bersih", OK("Sesuai")],
             ["ng_log", "±2.500 baris", f"{I(dq.raw_rows[1])} mentah, {I(dq.clean_rows[1])} bersih", OK("Sesuai")],
             ["Tabel", "production_daily, ng_log, countermeasure_log, dim_operator", "Keempatnya, dengan constraint dan kunci asing; kode defect disimpan sebagai file referensi (bukan tabel)", OK("Sesuai")],
             ["Fakta 1 (rate 3,0% menjadi sekitar 2,2%, signifikan)", "Cukup besar untuk signifikan", cs(gtm.loc[1].ditemukan), fm(gtm.loc[1].hasil)],
             ["Fakta 2 (volume after +30%)", "NG turun lebih sedikit dari rate", cs(gtm.loc[2].ditemukan), fm(gtm.loc[2].hasil)],
             ["Fakta 3 (tiga tanggal countermeasure terlihat di control chart)", "Penurunan bertahap, selisih paling lama 1 minggu", cs(gtm.loc[3].ditemukan) + ". CM1 dan CM2 hanya berjarak 19 hari", fm(gtm.loc[3].hasil)],
             ["Fakta 4 (ID-01 terbesar, ID-02 turun setelah bracket, Shift 2)", "Pola penyebab dan shift", cs(gtm.loc[4].ditemukan), fm(gtm.loc[4].hasil)],
             ["Fakta 5 (data kotor 2–3%)", "NG > input, tanggal di luar periode, ganda, kode salah ketik, shift kosong", cs(gtm.loc[5].ditemukan), fm(gtm.loc[5].hasil)],
             ["Parameter generator", "Tidak disebut", "Besar efek tiap countermeasure dan efek operator baru disetel beberapa kali agar rate before dan after sesuai target (kalibrasi di generator)", PART("Penyesuaian")],
             ["Lisensi", "Tidak memakai data publik atau data perusahaan", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools rancangan dipakai. Streamlit dibuat dan diuji lokal tetapi belum di-deploy; cek silang Excel memakai rumus Excel yang dihitung ulang oleh LibreOffice; '
         'statsmodels dipakai untuk uji, dan Playwright untuk infografik.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas, NumPy)", "Membuat dan membersihkan data", f"Generator, cleaning, cek silang pandas, uji, dampak ({I(npy)} skrip dan modul, {I(loc)} baris)", OK("Sesuai")],
             ["SciPy + statsmodels", "z-test, CI, jumlah sampel minimum", "statsmodels: <code>proportions_ztest</code>, <code>confint_proportions_2indep</code>, <code>NormalIndPower</code>, regresi binomial; SciPy: uji rasio kemungkinan titik ubah", OK("Sesuai")],
             ["DuckDB + SQL", "Database, defect rate sebagai view", f"harness_qcc.duckdb dengan constraint; {I(nsql)} file SQL; 9 view di <code>03_views.sql</code>", OK("Sesuai")],
             ["Excel", "Cek silang manual (Q14)", f"<code>crosscheck.xlsx</code>: {I(len(ce))} pemeriksaan, rumus SUMIFS/COUNTIFS/NORM.S.DIST; dihitung ulang oleh LibreOffice, bukan Microsoft Excel", PART("Sesuai + penyesuaian")],
             ["Streamlit + Plotly", "Dashboard 4 halaman, publik di Streamlit Community Cloud", "<code>streamlit/app.py</code> 4 halaman, filter tipe harness dan shift, kalkulator penghematan; diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["Jupyter", "Notebook analisis (hub portofolio)", "<code>analysis.ipynb</code> dibuat otomatis dan dieksekusi tanpa error", OK("Sesuai")],
             ["Playwright (Chromium)", "Tidak ada di rancangan", "Mencetak infografik HTML menjadi PDF dan PNG", PART("Tambahan")],
             ["GitHub + Markdown", "Kode, data contoh, README", "Struktur dan README siap; berada di branch <code>pilot-project-4</code>, belum digabung ke <code>main</code>", PART("Sebagian")]]))
steps = [("1", "Menyepakati periode dan definisi", "<code>project/docs/definitions.md</code>", OK("Sesuai"), ""),
         ("2", "Merancang struktur tabel", "<code>project/docs/data_dictionary.md</code>, <code>01_schema.sql</code>", OK("Sesuai"), ""),
         ("3", "Membuat data simulasi", "<code>01_generate_data.py</code>, <code>ground_truth.json</code>", PART("Sesuai + penyesuaian"), "Besar efek countermeasure dan efek operator baru disetel beberapa kali agar rate before 3,0% dan after sekitar 2,2%."),
         ("4", "Membersihkan data", "<code>02_clean_data.py</code>, <code>cleaning_log.md</code>", OK("Sesuai"), "Ditambah pembuktian: baris bersih sama dengan data asal sebelum dikotori."),
         ("5", "Memasukkan ke database", "<code>03_build_db.py</code>, <code>01_schema.sql</code>, <code>02_load.sql</code>", OK("Sesuai"), "Ditambah 10 uji penolakan dan 7 pemeriksaan konsistensi."),
         ("6", "Menulis query defect rate", "<code>03_views.sql</code>, <code>04_run_queries.py</code>", OK("Sesuai"), ""),
         ("7", "Cek silang Excel", "<code>07_excel_crosscheck.py</code>, <code>05_crosscheck.py</code>", PART("Sesuai + tambahan"), "Ditambah cek silang pandas."),
         ("8", "Menguji signifikansi", "<code>06_stats_tests.py</code>", PART("Sesuai + tambahan"), "Ditambah regresi logistik (faktor operator) dan uji sensitivitas data kotor."),
         ("9", "Membuat control chart", "<code>06_stats_tests.py</code> (p-chart), halaman ini, dashboard", PART("Sesuai + penyesuaian"), "Batas kendali before dan after terpisah; ditambah titik ubah mingguan dan regresi langkah untuk menilai waktu countermeasure."),
         ("10", "Menghitung dampak dan mencocokkan ground truth", "<code>08_impact_ground_truth.py</code>", OK("Sesuai"), "Biaya per harness adalah asumsi."),
         ("11", "Membuat dashboard", "<code>streamlit/app.py</code>, <code>09_build_dashboard_data.py</code>", PART("Sebagian"), "Belum di-deploy ke Streamlit Community Cloud."),
         ("12", "README dan finalisasi", "<code>README.md</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
CODE_REL = "project/code/"
renames = [("scripts/generate_data.py", CODE_REL + "1-data-preparation/python/01_generate_data.py"), ("scripts/clean_data.py", CODE_REL + "1-data-preparation/python/02_clean_data.py"),
           ("sql/ (query dan view)", CODE_REL + "2-analysis/sql/03_views.sql"), ("dashboard/app.py", CODE_REL + "3-presentation/streamlit/app.py"),
           ("outputs/*.csv", "project/results/2-analysis/*.csv"), ("outputs/crosscheck.xlsx", "project/results/2-analysis/crosscheck.xlsx"),
           ("outputs/infographic.pdf / .png", "project/results/3-presentation/infographic.pdf, project/results/3-presentation/infographic.png"),
           ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb"), ("harness_qcc.duckdb", "project/harness_qcc.duckdb (tidak di-commit)"),
           ("docs/definitions.md", "project/docs/definitions.md"), ("docs/data_dictionary.md", "project/docs/data_dictionary.md"), ("docs/cleaning_log.md", "project/docs/cleaning_log.md"),
           ("data/ground_truth.json", "project/data/ground_truth.json"), ("requirements.txt", "project/requirements.txt"),
           ("(tidak ada)", ", ".join(("03_build_db.py", "04_run_queries.py", "05_crosscheck.py", "07_excel_crosscheck.py", "06_stats_tests.py", "08_impact_ground_truth.py",
                                       "09_build_dashboard_data.py", "10_build_infographic.py", "11_build_notebook.py", "12_build_readme.py", "kpi_pandas.py", "common.py")))]
for a, b in renames:                       # pastikan semua file tujuan memang ada (kecuali yang tidak di-commit)
    for part in b.split(", "):
        part = part.split(" (")[0]
        if "*" in part or "/" not in part or "tidak di-commit" in b:
            continue
        assert (REPO / part).exists(), part
allpy = {p.name for p in (REPO / CODE_REL).rglob("*.py")}
assert {"03_build_db.py", "04_run_queries.py", "05_crosscheck.py", "07_excel_crosscheck.py", "06_stats_tests.py", "08_impact_ground_truth.py", "09_build_dashboard_data.py",
        "10_build_infographic.py", "11_build_notebook.py", "12_build_readme.py", "kpi_pandas.py", "common.py"} <= allpy, "skrip pada daftar rename belum ada"
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Nama dan lokasi file berubah mengikuti struktur repo standar, ada beberapa langkah tambahan (regresi, sensitivitas, cek silang pandas), '
         'dan dua langkah (11 dan 12) belum sepenuhnya selesai.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Besar efek countermeasure dan efek operator baru disetel beberapa kali (kalibrasi di generator) supaya rate before tepat 3,0% dan rate after mendekati 2,2%. Seed tetap, jadi hasil akhir sama setiap dijalankan.</li>',
         '<li>Efek tiap countermeasure dinilai dengan regresi logistik langkah, karena uji jendela waktu per countermeasure saling tumpang tindih (CM1 dan CM2 hanya berjarak 19 hari).</li>',
         '<li>Efek operator baru ditambahkan di generator sebagai faktor pengganggu, supaya Q10 punya sesuatu untuk diuji.</li>',
         f'<li>Uji sensitivitas tiga perlakuan data kotor, cek silang pandas ({I(len(cx))} pemeriksaan), dan pembuktian bahwa cleaning memulihkan data asal ditambahkan di luar rancangan.</li>',
         f'<li>Uji constraint: {I(len(ctest))} jenis baris salah dicoba dimasukkan ke database dan semuanya ditolak; setelah cleaning, {I(len(cons))} pemeriksaan konsistensi menghasilkan 0 pelanggaran.</li>',
         f'<li>Cek silang Excel memakai rumus yang dihitung ulang oleh LibreOffice ({I(len(ce))} pemeriksaan), bukan angka yang ditulis tangan.</li>',
         '<li>Notebook dan infografik dibuat otomatis dari hasil, dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"], [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Dashboard interaktif", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (4 halaman, filter tipe harness dan shift, kalkulator) diuji lokal dengan AppTest. Link publik belum ada"),
        ("One-sheet infografik", "Utama", OK("Tercapai"), "<code>infographic.pdf</code> dan <code>infographic.png</code>, dibuat dari CSV hasil"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>harness_qcc.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Skrip pembuat data simulasi", "Utama", OK("Tercapai"), "<code>01_generate_data.py</code> dengan seed tetap dan parameter countermeasure, kamus data, <code>ground_truth.json</code>"),
        ("Notebook analisis", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dieksekusi tanpa error, mencakup Q1 sampai Q14"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; berada di branch <code>pilot-project-4</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("docs/definitions.md", "Definisi periode dan metrik", "project/docs/definitions.md"), ("docs/data_dictionary.md", "Kamus data", "project/docs/data_dictionary.md"),
        ("scripts/generate_data.py", "Generator data", "project/code/1-data-preparation/python/01_generate_data.py"),
        ("data/raw/*.csv", "Data mentah (tidak di-commit)", "project/data/raw"), ("data/ground_truth.json", "Fakta yang ditanam", "project/data/ground_truth.json"),
        ("scripts/clean_data.py", "Cleaning", "project/code/1-data-preparation/python/02_clean_data.py"), ("docs/cleaning_log.md", "Log cleaning", "project/docs/cleaning_log.md"),
        ("harness_qcc.duckdb", "File database (tidak di-commit)", "project/harness_qcc.duckdb"), ("sql/", "Query dan view", "project/code/2-analysis/sql/03_views.sql"),
        ("outputs/crosscheck.xlsx", "Cek silang Excel", "project/results/2-analysis/crosscheck.xlsx"), ("notebooks/analysis.ipynb", "Notebook", "project/results/3-presentation/analysis.ipynb"),
        ("outputs/*.csv", "Tabel hasil uji dan skenario", "project/results/2-analysis/ztest.csv"), ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"),
        ("requirements.txt", "Paket Python", "project/requirements.txt"), ("outputs/infographic.pdf / .png", "One-sheet", "project/results/3-presentation/infographic.png"),
        ("README.md", "Laporan temuan", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"), ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
stat_doc = lambda rel: OK("Ada") if chk(rel) and "duckdb" not in rel and "raw" not in rel else (PART("Tidak di-commit") if "duckdb" in rel or "raw" in rel else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (dashboard belum punya link publik, repositori belum digabung ke main). '
         f'Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in docs]),
         '<p>Data mentah, data bersih, dan <code>harness_qcc.duckdb</code> tidak di-commit karena bisa dibuat ulang oleh skrip.</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
crit = [("1. Kesembilan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q4, Q5, Q7, Q9, Q11, Q12, Q13, Q14 terjawab (bagian 2)"),
        ("2. Defect rate dan hasil z-test dari SQL dan Python sama dengan hitungan manual Excel", OK("Tercapai"), f"{I(len(ce))} dari {I(len(ce))} pemeriksaan Excel; {I(len(cx))} dari {I(len(cx))} pemeriksaan pandas"),
        ("3. Kelima fakta yang ditanam ditemukan, termasuk tanggal penurunan (selisih paling lama 1 minggu)", PART("Sebagian"), f"{I((gtc.hasil == 'Sesuai').sum())} dari {I(len(gtc))} sesuai; fakta 3 hanya sebagian (Tabel 2.9b)"),
        ("4. Orang awam menyebut persen penurunan dan terbukti atau tidak dalam &lt; 1 menit", PART("Belum diuji"), "Halaman Ringkasan dashboard dan infografik memuat angka itu di bagian atas, tetapi belum diuji ke pembaca sebenarnya"),
        ("5. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy (Streamlit Community Cloud belum)")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Apakah penurunan insulation damage setelah countermeasure QCC benar-benar signifikan dan stabil, dan berapa unit serta biaya yang dihemat per tahun?</i></p><ul class="tight">',
    f'<li><b>Signifikan:</b> rate turun dari {P(z0.rate_before, 2)} menjadi {P(z0.rate_after, 2)} (−{P(z0.rel_drop)}), z = {D(z0.z, 2)}, p-value {pv(z0.p_value)}; CI 95% selisih {D(z0.ci_low * 100, 2)} sampai {D(z0.ci_high * 100, 2)} poin. Turun di tiga tipe harness dan kedua shift.</li>',
    f'<li><b>Stabil:</b> {I(n_after_wk)} minggu after semuanya di dalam batas kendali p-chart, dan {I(int(wk.run_below_before_cl.max()))} minggu berturut-turut di bawah garis tengah before sejak {TGL(run8_start.date())}.</li>',
    f'<li><b>Penyebab:</b> cara perakitan (ID-01) turun paling besar (−{D(dc["ID-01"]["diff"] * 100, 2)} poin), tepi bracket (ID-02) turun −{D(dc["ID-02"]["diff"] * 100, 2)} poin setelah bracket in-house. Countermeasure mana yang paling berpengaruh belum bisa dipisahkan, karena CM1 dan CM2 hanya berjarak {I(gap_cm)} hari.</li>',
    f'<li><b>Dampak:</b> sekitar {I(ipt.unit_per_tahun)} harness per tahun dan Rp {I(ipt.hemat_per_tahun / 1e6)} juta per tahun (estimated, rentang Rp {I(ilo.hemat_per_tahun / 1e6)} sampai {I(ihi.hemat_per_tahun / 1e6)} juta).</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated, simulated):</b> penurunan {D(z0["diff"] * 100, 2)} poin pada volume {I(vol.after)} harness per bulan menyelamatkan sekitar {I(ipt.unit_per_bulan)} harness per bulan dari NG insulation damage.</li>',
    '<li><b>Nilai analitis:</b> membagi dengan input, uji statistik, dan p-chart membuat klaim "defect turun" bisa dibuktikan. Hanya melihat jumlah NG menunjukkan penurunan yang jauh lebih kecil karena volume naik.</li>',
    '<li><b>Nilai portofolio:</b> pipeline lengkap: data buatan dengan ground truth, cleaning terdokumentasi, DuckDB dengan constraint, uji statistik, cek silang pandas dan Excel, notebook, dashboard, dan infografik.</li>',
    '<li><b>Belum terukur:</b> dampak pada keputusan atau pabrik nyata. Semua angka berasal dari data simulasi dan menguji metode.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian atau belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          f'<li>Jadikan ketiga countermeasure standar: penurunan terbukti signifikan dan stabil tiga bulan berturut-turut ({P(z0.rel_drop)} relatif).</li>',
          f'<li>Pertahankan bracket in-house dengan deburring: ID-02 turun dari {P(m02.loc["2026-06"].rate, 2)} (Jun) menjadi {P(m02.loc["2026-10"].rate, 2)} (Okt).</li>',
          f'<li>Lanjutkan pemantauan dengan p-chart mingguan memakai batas after; tindak lanjuti jika ada titik di luar batas atau {I(8)} titik berturut-turut di atas garis tengah.</li>',
          '<li>Laporkan defect sebagai rate (dibagi input), bukan jumlah NG, dan sertakan p-value atau CI di laporan QCC.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Pasang countermeasure dengan jarak lebih panjang (minimal 6 sampai 8 minggu) atau catat per shift, supaya efek tiap countermeasure bisa dipisahkan.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan uji dashboard serta infografik ke satu pembaca awam untuk mengisi kriteria 4 dan 5.</li>',
          f'<li>Ulangi pembuatan data dengan seed lain untuk melihat apakah fakta 3 konsisten, dan kumpulkan data after lebih lama (Q6: penurunan 10% butuh {D(s10.months_after, 1)} bulan).</li>',
          '<li>Catat operator dan masa kerja per NG bila memakai data pabrik, supaya Q10 bisa dijawab dengan model yang lebih kuat.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Semua temuan berasal dari data simulasi; fakta yang ditemukan adalah fakta yang ditanam sendiri.</li>',
          '<li>Fakta 3 hanya sebagian terbukti: kontribusi tiap countermeasure tidak bisa dipisahkan, dan titik ubah CM2 tidak terdeteksi dalam 1 minggu.</li>',
          '<li>Before–after bukan eksperimen: operator makin terampil, volume naik, dan bracket berganti pada periode yang sama.</li>',
          '<li>z-test menganggap setiap unit independen; p-chart dipakai sebagai pemeriksaan kedua. Biaya per harness, besar efek countermeasure, dan efek operator adalah parameter buatan sendiri.</li>',
          '<li>Dashboard belum di-deploy; kriteria 4 dan 5 belum terpenuhi. Slide presentasi (Opsional) tidak dibuat.</li>',
          '<li>Cek silang Excel dihitung oleh LibreOffice, bukan Microsoft Excel. Tidak ada masalah lisensi dataset (data buatan sendiri).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(dbc['production_daily'])} baris produksi, {I(dbc['ng_log'])} baris NG, {I(bad_total)} baris kotor ditangani"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + penyesuaian"), "Data buatan sesuai rancangan; kalibrasi parameter, fakta 3 sebagian"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + tambahan"), "Semua tools dipakai; Streamlit belum di-deploy; Excel dihitung LibreOffice"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; regresi dan sensitivitas ditambahkan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan uji statistik pada data simulasi. '
    f'Hasil SQL dicek silang dengan pandas ({I(len(cx))} dari {I(len(cx))} pemeriksaan) dan dengan Excel ({I(len(ce))} dari {I(len(ce))}). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Semua angka bersumber dari data simulasi buatan sendiri dan menguji metode, bukan kondisi pabrik. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {"30", "100", "80", "60", "0,05", "3,0", "2,2", "36.000", "18.000", "2.500", "1.300", "6.000", "8.000", "210", "150.000", "100.000", "250.000",
          "2026", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "14", "15", "19", "22", "40", "50", "500", "95", "4", "8", "1E-9", "0,001", "31"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("fakta ditanam 4 dari 5 sesuai, fakta 3 sebagian", gtc.hasil.tolist() == ["Sesuai", "Sesuai", "Sebagian", "Sesuai", "Sesuai"]),
          ("crosscheck pandas semua PASS", (cx.status == "PASS").all()), ("crosscheck Excel semua PASS", (ce.status == "PASS").all()),
          ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()), ("semua pemeriksaan konsistensi 0 pelanggaran", (cons.violations == 0).all()),
          ("jumlah baris kotor ditemukan = ditanam", int(clog.rows_found.sum() - clog[clog.rule == "P5"].rows_found.sum()) == sum(gt["dirty_injected"].values())),
          ("jumlah pertanyaan = 14 (9 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 14 and npr == {"Utama": 9, "Pendukung": 4, "Tambahan": 1}),
          ("catatan hanya Q8, Q10, Q12", WARN == {8, 10, 12}), ("tidak ada minggu after di luar batas kendali", len(out_after) == 0),
          ("seluruh insulation damage = ID-01 + ID-02 + ID-03", int(sum(dc[k].x_before + dc[k].x_after for k in dc)) == int(z0.x_before + z0.x_after)),
          ("rate dikali input = jumlah NG", abs(z0.rate_before * z0.n_before - z0.x_before) < 1e-6), ("jumlah pertanyaan unik pada bagian 2 = 14", qn_uniq == list(range(1, 15))),
          ("langkah rancangan = 12", len(steps) == 12)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
# urutan skill: tombol Design dan Report berdampingan, baru grup link (agar klik tab tidak terkena dropdown tab lain)
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
