# Kamus data

Empat tabel di `harness_qcc.duckdb`. Data simulasi, dibuat oleh `code/1-data-preparation/python/01_generate_data.py`.

```
dim_operator (operator_id PK) ──< production_daily (date, shift, harness_type PK; operator_id FK) ──< ng_log (ng_id PK; date+shift+harness_type FK)
countermeasure_log (cm_id PK)   [dipakai untuk menurunkan periode before / transisi / after]
```

## production_daily (1 baris = satu tipe harness, satu shift, satu hari; satu operator)
| Kolom | Arti |
|---|---|
| date | Tanggal produksi (Jan–Okt 2026) |
| shift | Shift 1 / Shift 2 |
| harness_type | A, B, C |
| operator_id | Operator yang bertugas pada baris ini |
| input_qty | Jumlah harness yang diproduksi |
| ok_qty, ng_qty | Jumlah OK dan NG (ok_qty + ng_qty = input_qty) |

## ng_log (1 baris = satu harness NG)
| Kolom | Arti |
|---|---|
| ng_id | Nomor NG (NG-000001, ...) |
| date, shift, harness_type | Kunci ke baris produksi |
| operator_id | Operator pada baris produksi tersebut |
| station_found | Stasiun tempat NG ditemukan (8 tahap produksi) |
| defect_code | ID-01, ID-02, ID-03 (insulation damage), OT-01, OT-02, OT-03 (lainnya) |
| cause_source | Perakitan / Tepi bracket / Lainnya |
| bracket_source | Supplier / In-house (sumber bracket yang dipakai pada tanggal itu) |

## countermeasure_log (1 baris = satu countermeasure QCC)
`cm_id`, `cm_name`, `target_cause`, `station`, `start_date` (tanggal disamarkan).

## dim_operator (1 baris = satu operator)
`operator_id`, `shift`, `hire_date`, `status` (baru = masuk 2026, lama = sebelumnya).

## Aturan di database
PRIMARY KEY, FOREIGN KEY, dan CHECK (ng ≤ input, ok + ng = input, shift/tipe/kode valid, tanggal dalam periode). Sepuluh uji penolakan ada di `results/1-data-preparation/constraint_tests.csv`.
