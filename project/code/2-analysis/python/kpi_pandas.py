"""Hitungan pandas dari CSV bersih (tanpa SQL). Dipakai untuk cek silang terhadap hasil SQL dan untuk uji statistik."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402


def load():
    prod = pd.read_csv(C.CLEAN_DIR / "production_daily.csv", parse_dates=["date"])
    ng = pd.read_csv(C.CLEAN_DIR / "ng_log.csv", parse_dates=["date"])
    op = pd.read_csv(C.CLEAN_DIR / "dim_operator.csv")
    cm = pd.read_csv(C.CLEAN_DIR / "countermeasure_log.csv", parse_dates=["start_date"])
    return prod, ng, op, cm


def period_of(d, cm):
    first = cm.start_date.min().to_period("M").to_timestamp()
    second = cm.loc[cm.cm_id == 2, "start_date"].iloc[0].to_period("M").to_timestamp()
    return pd.Series(["before" if x < first else "after" if x >= second else "transisi" for x in d], index=d.index)


def prepare():
    prod, ng, op, cm = load()
    prod = prod.merge(op[["operator_id", "status"]].rename(columns={"status": "op_status"}), on="operator_id")
    prod["period"] = period_of(prod.date, cm)
    prod["week_start"] = prod.date - pd.to_timedelta(prod.date.dt.weekday, unit="D")
    prod["month"] = prod.date.dt.strftime("%Y-%m")
    ng = ng.merge(prod[["date", "shift", "harness_type", "period", "week_start", "month", "op_status"]], on=["date", "shift", "harness_type"])
    ng["is_insulation"] = ng.defect_code.str.startswith("ID-")
    return prod, ng, op, cm
