"""Langkah 5: membuat file DuckDB, memuat data bersih, lalu menguji bahwa data salah ditolak dan data konsisten.
Keluaran: project/harness_qcc.duckdb (tidak di-commit), results/1-data-preparation/{table_rows,constraint_tests,consistency_checks}.csv"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
if C.DB_PATH.exists():
    C.DB_PATH.unlink()
con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_PREP / "01_schema.sql").read_text())
con.execute((C.SQL_PREP / "02_load.sql").read_text())
rows = pd.DataFrame([(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in ["dim_operator", "countermeasure_log", "production_daily", "ng_log"]], columns=["table", "clean_rows"])
rows.to_csv(C.RES_PREP / "table_rows.csv", index=False)

tests = [
    ("ng_qty lebih besar dari input_qty", "INSERT INTO production_daily VALUES ('2026-02-02','Shift 1','A','OP01',50,40,60)"),
    ("ok_qty + ng_qty tidak sama dengan input_qty", "INSERT INTO production_daily VALUES ('2026-02-03','Shift 1','A','OP01',50,40,5)"),
    ("operator tidak ada di dim_operator", "INSERT INTO production_daily VALUES ('2026-02-03','Shift 1','A','OP99',50,48,2)"),
    ("shift kosong", "INSERT INTO production_daily VALUES ('2026-02-03','','A','OP01',50,48,2)"),
    ("tipe harness tidak dikenal", "INSERT INTO production_daily VALUES ('2026-02-03','Shift 1','Z','OP01',50,48,2)"),
    ("tanggal di luar periode", "INSERT INTO production_daily VALUES ('2025-12-30','Shift 1','A','OP01',50,48,2)"),
    ("baris ganda (primary key)", "INSERT INTO production_daily SELECT * FROM production_daily LIMIT 1"),
    ("kode defect salah ketik di ng_log", "INSERT INTO ng_log VALUES ('NG-TEST1','2026-02-02','Shift 1','A','OP01','Visual Inspection','ID-1','Perakitan','Supplier')"),
    ("ng_log tanpa baris produksi induk", "INSERT INTO ng_log VALUES ('NG-TEST2','2026-01-01','Shift 1','A','OP01','Visual Inspection','ID-01','Perakitan','Supplier')"),
    ("ng_id ganda", "INSERT INTO ng_log SELECT * FROM ng_log LIMIT 1"),
]
out = []
for name, sql in tests:
    try:
        con.execute(sql); out.append((name, "DITERIMA (salah)"))
    except Exception as e:
        out.append((name, "ditolak"))
ct = pd.DataFrame(out, columns=["test", "outcome"]); ct.to_csv(C.RES_PREP / "constraint_tests.csv", index=False)

checks = [
    ("jumlah ng_qty = jumlah baris ng_log", "SELECT abs((SELECT sum(ng_qty) FROM production_daily) - (SELECT count(*) FROM ng_log))"),
    ("per baris produksi: ng_qty = jumlah ng_log", "SELECT count(*) FROM production_daily p LEFT JOIN (SELECT date, shift, harness_type, count(*) n FROM ng_log GROUP BY ALL) n USING (date, shift, harness_type) WHERE p.ng_qty <> coalesce(n.n, 0)"),
    ("operator di ng_log sama dengan operator baris produksi", "SELECT count(*) FROM ng_log n JOIN production_daily p USING (date, shift, harness_type) WHERE n.operator_id <> p.operator_id"),
    ("shift baris produksi sama dengan shift operator", "SELECT count(*) FROM production_daily p JOIN dim_operator o USING (operator_id) WHERE p.shift <> o.shift"),
    ("operator sudah bekerja saat tanggal produksi", "SELECT count(*) FROM production_daily p JOIN dim_operator o USING (operator_id) WHERE p.date < o.hire_date"),
    ("cause_source sesuai defect_code", "SELECT count(*) FROM ng_log WHERE (defect_code='ID-01' AND cause_source<>'Perakitan') OR (defect_code='ID-02' AND cause_source<>'Tepi bracket') OR (defect_code NOT IN ('ID-01','ID-02') AND cause_source<>'Lainnya')"),
    ("tanggal countermeasure berurutan dan di dalam periode", "SELECT count(*) FROM countermeasure_log a JOIN countermeasure_log b ON b.cm_id = a.cm_id + 1 WHERE b.start_date <= a.start_date"),
]
cons = pd.DataFrame([(n, con.execute(q).fetchone()[0]) for n, q in checks], columns=["check", "violations"])
cons.to_csv(C.RES_PREP / "consistency_checks.csv", index=False)
print(rows.to_string(index=False)); print(ct.to_string(index=False)); print(cons.to_string(index=False))
assert (ct.outcome == "ditolak").all() and (cons.violations == 0).all()
con.close()
