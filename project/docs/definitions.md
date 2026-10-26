# Definisi dan keputusan sebelum analisis

Ditetapkan di langkah 1 (sebelum melihat hasil uji) supaya analisis tidak bisa "diatur".

## Periode
| Periode | Tanggal | Cara menurunkan dari `countermeasure_log` |
|---|---|---|
| before | 1 Jan – 30 Jun 2026 | tanggal lebih awal dari awal bulan countermeasure pertama |
| transisi | 1 – 31 Jul 2026 | di antara before dan after; tidak dipakai di uji utama karena countermeasure baru dipasang sebagian |
| after | 1 Agu – 31 Okt 2026 | tanggal sejak awal bulan countermeasure kedua |

Hari kerja: Senin–Jumat, minus 8 hari libur (209 hari kerja).

## Metrik
- **Insulation damage rate** = jumlah NG berkode ID-01, ID-02, ID-03 dibagi `input_qty`.
- Defect lain (OT-01, OT-02, OT-03) dikelompokkan sebagai "Lainnya" agar total NG tetap lengkap.
- **Penurunan relatif** = (rate before − rate after) / rate before.
- **Unit terselamatkan** = (rate before − rate after) × volume. **Penghematan** = unit terselamatkan × biaya per harness NG (asumsi Rp 150.000, estimated).

## Uji statistik
- z-test dua proporsi (varians gabungan), dua sisi, batas signifikansi α = 0,05. 95% confidence interval selisih memakai metode Wald.
- Jumlah sampel minimum: power 80%, α 0,05, effect size Cohen's h.
- p-chart mingguan: batas 3σ, dihitung terpisah untuk before dan after. Minggu dengan input kurang dari 500 harness (hanya 2 Jan) dibuang dari p-chart.
- Efek tiap countermeasure: regresi logistik (binomial) dengan indikator langkah kumulatif, disesuaikan status operator, shift, dan tipe harness.

## Kode defect
| Kode | Arti | cause_source |
|---|---|---|
| ID-01 | Insulation damage akibat cara perakitan | Perakitan |
| ID-02 | Insulation damage akibat tepi bracket tajam | Tepi bracket |
| ID-03 | Insulation damage lain-lain | Lainnya |
| OT-01 | Terminal longgar | Lainnya |
| OT-02 | Salah posisi konektor | Lainnya |
| OT-03 | Taping kurang rapat | Lainnya |
