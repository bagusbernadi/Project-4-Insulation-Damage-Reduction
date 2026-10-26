"""Langkah 6: menjalankan view SQL dan menyimpan hasilnya sebagai CSV (Q1-Q3, Q9-Q10)."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
C.RES_ANALYSIS.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())
OUT = {"period.csv": "v_rate_period", "week.csv": "v_rate_week", "month.csv": "v_rate_month", "dim.csv": "v_rate_dim",
       "cause.csv": "v_rate_cause", "bracket.csv": "v_bracket", "station.csv": "v_station", "cause_month.csv": "v_rate_cause_month"}
for f, v in OUT.items():
    df = con.execute(f"SELECT * FROM {v}").df()
    df.to_csv(C.RES_ANALYSIS / f, index=False)
    print(f, len(df))
con.close()
