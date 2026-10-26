"""Langkah 11: menyiapkan data ringkas untuk dashboard (satu baris = satu baris produksi harian, jumlah NG per kelompok kode).
Keluaran: results/3-presentation/dash_rows.csv (di-commit supaya dashboard bisa jalan tanpa membuat ulang database)."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
C.RES_PRESENT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(C.DB_PATH), read_only=False)
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())
df = con.execute("""
SELECT p.date, p.week_start, p.month, p.period, p.shift, p.harness_type, p.op_status, p.input_qty,
       count(*) FILTER (WHERE n.defect_code = 'ID-01') AS ng_id01, count(*) FILTER (WHERE n.defect_code = 'ID-02') AS ng_id02,
       count(*) FILTER (WHERE n.defect_code = 'ID-03') AS ng_id03, count(*) FILTER (WHERE NOT n.is_insulation) AS ng_other
FROM v_prod p LEFT JOIN v_ng n USING (date, shift, harness_type) GROUP BY ALL ORDER BY p.date, p.shift, p.harness_type""").df()
df.to_csv(C.RES_PRESENT / "dash_rows.csv", index=False)
con.execute("SELECT cm_id, cm_name, start_date FROM countermeasure_log ORDER BY cm_id").df().to_csv(C.RES_PRESENT / "dash_countermeasure.csv", index=False)
print(len(df), "baris;", int(df[["ng_id01", "ng_id02", "ng_id03"]].sum().sum()), "NG insulation damage")
