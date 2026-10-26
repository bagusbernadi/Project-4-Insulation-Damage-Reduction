# Data

Tidak ada dataset publik atau data perusahaan. Semua data dibuat oleh `code/1-data-preparation/python/01_generate_data.py` dengan seed tetap (`SEED` di `code/common.py`), sehingga hasilnya sama setiap dijalankan. Pola kasus diadaptasi dari pengalaman QCC; data dan istilah disamarkan. Tidak ada masalah lisensi.

- `raw/` : data simulasi mentah beserta data kotor (tidak di-commit, dibuat ulang)
- `clean/` : data setelah `02_clean_data.py` (tidak di-commit, dibuat ulang)
- `reference/dim_defect.csv` : daftar kode defect (di-commit)
- `ground_truth.json` : fakta yang sengaja ditanam dan jumlah data kotor yang disisipkan (di-commit)

Parameter countermeasure (tanggal, besar penurunan) ada di `code/common.py` dan bisa ditimpa lewat argumen `--cm1/--cm2/--cm3` pada skrip generator.
