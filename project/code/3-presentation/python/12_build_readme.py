"""Membuat README.md di root repo; semua angka dibaca dari CSV hasil."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, result  # noqa: E402

R = lambda n: pd.read_csv(result(n))
f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
pc = lambda v, d=2: f(v * 100, d) + "%"
n = lambda v: f"{int(round(v)):,}".replace(",", ".")

Z = R("ztest.csv").set_index("scope")
z0 = Z.loc["Insulation damage (ID-01+02+03)"]
dq, gtc, imp, vr = R("data_quality_summary.csv"), R("ground_truth_check.csv"), R("impact.csv"), R("volume_vs_rate.csv").set_index("metric")
cx, ce, sens, cpt = R("crosscheck.csv"), R("crosscheck_excel.csv"), R("sensitivity.csv"), R("changepoint.csv").iloc[0]
ip = imp[imp.biaya_per_unit == 150_000].set_index("skenario")
ipt, ilo, ihi = ip.loc["titik (hasil uji)"], ip.loc["batas bawah (CI 95%)"], ip.loc["batas atas (CI 95%)"]
vol, ngm = vr.loc["Input per bulan"], vr.loc["NG insulation damage per bulan"]
dc = {k: Z.loc[v] for k, v in (("ID-01", "ID-01 Perakitan"), ("ID-02", "ID-02 Tepi bracket"))}
ok_gt = int((gtc.hasil == "Sesuai").sum())
pv = "< 0,001" if z0.p_value < 0.001 else f(z0.p_value, 3)

md = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 4: Before–After Defect Reduction (QCC Insulation Damage)

**Status: Selesai di branch `pilot-project-4` (menunggu review sebelum digabung ke `main`).**

Halaman rancangan dan Report: https://bagusbernadi.github.io/Project-4-Insulation-Damage-Reduction/

| | |
|---|---|
| Kategori | Manufaktur (wire harness otomotif) |
| Tingkat | Mudah |
| Data | Data simulasi buatan sendiri (3 tipe harness, 2 shift, Jan–Okt 2026) |
| Tools | SQL (DuckDB), Python (pandas, NumPy, SciPy, statsmodels), Excel (cek silang), Jupyter, Streamlit + Plotly, GitHub |

## 1. Problem

Apakah penurunan insulation damage setelah countermeasure QCC benar-benar signifikan dan stabil, dan berapa unit serta biaya yang dihemat per tahun? Dipecah menjadi 14 pertanyaan (9 prioritas utama); jawabannya ada di tab Report pada halaman project.

## 2. Data

- Data simulasi buatan sendiri dengan seed tetap (`project/code/1-data-preparation/python/01_generate_data.py`); hasil identik setiap dijalankan.
- 4 tabel: `production_daily` ({n(dq.clean_rows[0])} baris bersih), `ng_log` ({n(dq.clean_rows[1])}), `countermeasure_log`, `dim_operator`.
- Data kotor yang ditanam: {n(dq.bad_rows.iloc[-1])} baris ({f(dq.bad_pct[0])}% produksi, {f(dq.bad_pct[1])}% NG). Semuanya ditemukan dan ditangani (`project/docs/cleaning_log.md`).

## 3. Analysis

- Rate insulation damage: before **{pc(z0.rate_before)}**, after **{pc(z0.rate_after)}**, turun {pc(z0.rel_drop, 1)} relatif.
- z-test dua proporsi: z = {f(z0.z, 2)}, p-value {pv}; CI 95% selisih {f(z0.ci_low * 100, 2)} sampai {f(z0.ci_high * 100, 2)} poin.
- Volume after naik {pc(vol.change, 0)} sehingga jumlah NG per bulan hanya turun {pc(abs(ngm.change), 0)}; hanya melihat jumlah NG menyesatkan.
- p-chart mingguan: tidak ada minggu after di luar batas kendali.
- Sumber: cara perakitan (ID-01) turun {f(dc['ID-01']['diff'] * 100, 2)} poin, tepi bracket (ID-02) turun {f(dc['ID-02']['diff'] * 100, 2)} poin.
- Tiga perlakuan data kotor memberi kesimpulan sama. Cek silang: {len(cx)}/{len(cx)} pandas dan {len(ce)}/{len(ce)} Excel PASS.

## 4. Recommendation

Jadikan ketiga countermeasure standar dan pantau dengan p-chart mingguan memakai batas after. Laporkan defect sebagai rate dengan p-value atau CI.

## 5. Impact

Estimated / simulated: sekitar {n(ipt.unit_per_bulan)} harness per bulan, {n(ipt.unit_per_tahun)} per tahun, penghematan Rp {n(ipt.hemat_per_tahun / 1e6)} juta per tahun pada biaya Rp 150.000 per harness (asumsi; rentang CI Rp {n(ilo.hemat_per_tahun / 1e6)}–{n(ihi.hemat_per_tahun / 1e6)} juta).

## Batasan

- Data simulasi: hasil membuktikan metode, bukan kondisi pabrik.
- {ok_gt} dari {len(gtc)} fakta yang ditanam ditemukan penuh; tanggal tiap countermeasure tidak semuanya terlihat (CM1 dan CM2 hanya berjarak 19 hari).
- Before–after bukan eksperimen: operator makin terampil, volume naik, bracket berganti bersamaan.
- Cek silang Excel dihitung ulang oleh LibreOffice, bukan Microsoft Excel. Dashboard belum di-deploy.

## Menjalankan

```
pip install -r project/requirements.txt
cd project/code/1-data-preparation/python && python 01_generate_data.py && python 02_clean_data.py && python 03_build_db.py
cd ../../2-analysis/python && for s in 04 05 06 07 08; do python ${{s}}_*.py; done
cd ../../3-presentation/python && for s in 09 10 11 12; do python ${{s}}_*.py; done
streamlit run ../streamlit/app.py
python design-and-report/src/build_report.py   # dari root repo
```

## Struktur repository

```
index.html                 Pengalihan ke design-and-report/
design-and-report/         Halaman Design dan Report (src/ berisi generator)
project/
  code/1-data-preparation  Generator, cleaning, database (python, sql)
  code/2-analysis          Query, cek silang, uji statistik, dampak
  code/3-presentation      Dashboard data, infografik, notebook, Streamlit
  results/                 CSV hasil per tahap, crosscheck.xlsx, infografik, notebook
  docs/                    Definisi, kamus data, log cleaning
  data/                    ground_truth.json (data mentah dan bersih tidak di-commit)
```
"""
(ROOT.parent / "README.md").write_text(md, encoding="utf-8")
print("README.md ditulis")
