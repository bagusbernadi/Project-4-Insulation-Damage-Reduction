[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 4: Before–After Defect Reduction (QCC Insulation Damage)

**Status: Design (rancangan).**

Halaman rancangan: https://bagusbernadi.github.io/Project-4-Insulation-Damage-Reduction/

## Tujuan

Membuktikan dengan data apakah penurunan insulation damage pada perakitan wire harness setelah perbaikan QCC benar-benar nyata, signifikan, dan stabil, sehingga perbaikan yang terbukti efektif dapat dijadikan standar dan nilai penghematannya dapat dilaporkan ke manajemen.

| | |
|---|---|
| Kategori | Manufaktur (wire harness otomotif) |
| Tingkat | Mudah |
| Data | Data simulasi buatan sendiri (3 tipe harness, 2 shift, Jan–Okt 2026) |
| Tools | SQL (DuckDB), Python (pandas, NumPy, SciPy, statsmodels), Excel (cek silang), Jupyter, Streamlit + Plotly, GitHub |

## 1. Problem

Pertanyaan utama: apakah penurunan insulation damage setelah countermeasure QCC benar-benar signifikan dan stabil, dan berapa unit serta biaya yang dihemat per tahun?

Pertanyaan ini dipecah menjadi 14 pertanyaan (9 prioritas utama) dalam 6 tema: before vs after, signifikansi, stabilitas, penyebab, dampak, dan validitas data. Daftar lengkap ada di halaman rancangan.

## 2. Data

- Sumber data: data simulasi buatan sendiri, dibuat oleh skrip `scripts/generate_data.py` (Versi: -; Tanggal dibuat: -). Pola kasus diadaptasi dari pengalaman QCC; data dan istilah disamarkan untuk menjaga privasi perusahaan.
- 4 tabel: `production_daily`, `ng_log`, `countermeasure_log`, `dim_operator`.
- Ukuran perkiraan: ±1.300 baris produksi harian dan ±2.500 baris catatan NG. Jumlah pasti diketahui setelah data dibuat.
- Fakta yang sengaja ditanam (ground truth) dan 2–3% data kotor dipakai untuk menguji apakah analisis berhasil menemukannya.

Belum dikerjakan.

## 3. Analysis

Metode: defect rate per periode, z-test dua proporsi, 95% confidence interval selisih rate, jumlah sampel minimum, dan p-chart mingguan dengan garis tanggal tiap countermeasure.

Belum dikerjakan.

## 4. Recommendation

Belum dikerjakan.

## 5. Impact

Estimasi unit terselamatkan = (rate lama − rate baru) × volume; penghematan = unit terselamatkan × biaya per unit (asumsi tertulis). Semua angka dampak akan diberi label `estimated` / `simulated`.

Belum dikerjakan.

## Batasan yang sudah diketahui

- Data simulasi: hasil akhir membuktikan metode, bukan kondisi pabrik sebenarnya.
- Before–after bukan eksperimen: operator makin terampil, volume naik, dan sumber bracket berganti pada periode yang sama.
- z-test menganggap setiap unit independen; control chart dipakai sebagai pemeriksaan kedua.
- QCC dimulai saat defect sedang tinggi, sehingga sebagian penurunan bisa terjadi dengan sendirinya (kembali ke rata-rata).

## Struktur repository

```
index.html   Halaman rancangan project (GitHub Pages)
README.md    Dokumen ini
```

Struktur lengkap yang direncanakan (docs/, scripts/, sql/, notebooks/, dashboard/, outputs/) ada di bagian "Project Outputs" pada halaman rancangan.
