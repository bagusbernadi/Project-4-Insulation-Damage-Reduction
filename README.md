[← Back to portfolio](https://bagusbernadi.github.io/)

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
- 4 tabel: `production_daily` (1.254 baris bersih), `ng_log` (2.538), `countermeasure_log`, `dim_operator`.
- Data kotor yang ditanam: 100 baris (2,7% produksi, 2,6% NG). Semuanya ditemukan dan ditangani (`project/docs/cleaning_log.md`).

## 3. Analysis

- Rate insulation damage: before **3,04%**, after **2,14%**, turun 29,8% relatif.
- z-test dua proporsi: z = 6,69, p-value < 0,001; CI 95% selisih 0,65 sampai 1,16 poin.
- Volume after naik 31% sehingga jumlah NG per bulan hanya turun 8%; hanya melihat jumlah NG menyesatkan.
- p-chart mingguan: tidak ada minggu after di luar batas kendali.
- Sumber: cara perakitan (ID-01) turun 0,54 poin, tepi bracket (ID-02) turun 0,35 poin.
- Tiga perlakuan data kotor memberi kesimpulan sama. Cek silang: 348/348 pandas dan 66/66 Excel PASS.

## 4. Recommendation

Jadikan ketiga countermeasure standar dan pantau dengan p-chart mingguan memakai batas after. Laporkan defect sebagai rate dengan p-value atau CI.

## 5. Impact

Estimated / simulated: sekitar 71 harness per bulan, 855 per tahun, penghematan Rp 128 juta per tahun pada biaya Rp 150.000 per harness (asumsi; rentang CI Rp 92–165 juta).

## Batasan

- Data simulasi: hasil membuktikan metode, bukan kondisi pabrik.
- 4 dari 5 fakta yang ditanam ditemukan penuh; tanggal tiap countermeasure tidak semuanya terlihat (CM1 dan CM2 hanya berjarak 19 hari).
- Before–after bukan eksperimen: operator makin terampil, volume naik, bracket berganti bersamaan.
- Cek silang Excel dihitung ulang oleh LibreOffice, bukan Microsoft Excel. Dashboard belum di-deploy.

## Menjalankan

```
pip install -r project/requirements.txt
cd project/code/1-data-preparation/python && python 01_generate_data.py && python 02_clean_data.py && python 03_build_db.py
cd ../../2-analysis/python && for s in 04 05 06 07 08; do python ${s}_*.py; done
cd ../../3-presentation/python && for s in 09 10 11 12; do python ${s}_*.py; done
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
