"""Pengaturan bersama untuk semua skrip. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi mentah (tidak di-commit)
CLEAN_DIR = DATA / "clean"                             # data bersih (tidak di-commit)
REF_DIR = DATA / "reference"
DIM_DEFECT_CSV = REF_DIR / "dim_defect.csv"
GROUND_TRUTH = DATA / "ground_truth.json"
DB_PATH = ROOT / "harness_qcc.duckdb"
CODE = ROOT / "code"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
HTML_DIR = CODE / "3-presentation" / "html"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"

SEED = 20261004
START_DATE, END_DATE = "2026-01-01", "2026-10-31"
HOLIDAYS = ["2026-01-01", "2026-03-19", "2026-03-20", "2026-04-03", "2026-05-01", "2026-05-14", "2026-06-01", "2026-08-17"]
HARNESS = {"A": 0.45, "B": 0.35, "C": 0.20}            # porsi volume per tipe harness
HARNESS_MULT = {"A": 1.00, "B": 0.90, "C": 1.25}       # pengali defect per tipe
SHIFTS = ["Shift 1", "Shift 2"]
STATIONS = ["Wire Cutting & Stripping", "Crimping", "Sub-assembly", "Assembly Board", "Taping",
            "Electrical Test", "Visual Inspection", "Packing"]
MONTH_VOLUME = {1: 5800, 2: 5900, 3: 5700, 4: 6100, 5: 6200, 6: 6300, 7: 6900, 8: 7700, 9: 7800, 10: 7900}

# Countermeasure QCC (parameter yang bisa diubah). mult = pengali rate defect setelah efek penuh, ramp = hari menuju efek penuh
CM = [
    dict(cm_id=1, cm_name="Cek isolasi di Wire Cutting & Stripping", target_cause="Isolasi tergores sejak awal", station="Wire Cutting & Stripping", start_date="2026-07-15",
         ramp=7, mult={"ID-01": 0.97, "ID-02": 0.97, "ID-03": 0.85}),
    dict(cm_id=2, cm_name="Jig routing + SOP di assembly board", target_cause="Cara perakitan", station="Assembly Board", start_date="2026-08-03",
         ramp=7, mult={"ID-01": 0.74}),
    dict(cm_id=3, cm_name="Bracket in-house dengan deburring", target_cause="Tepi bracket tajam", station="Assembly Board", start_date="2026-09-01",
         ramp=10, mult={"ID-02": 0.74}),
]
# rate dasar (before, rata-rata ~3,0% untuk tiga kode insulation damage) dan defect lain (tidak terkait QCC)
BASE_ID = {"ID-01": 1.70, "ID-02": 1.10, "ID-03": 0.20}   # proporsi relatif; diskalakan agar rata-rata before = 3,0%
TARGET_BEFORE = 0.030
BASE_OTHER = {"OT-01": 0.0050, "OT-02": 0.0035, "OT-03": 0.0025}
NEW_OP_EXCESS, NEW_OP_TAU = 1.00, 60.0                  # operator baru: excess awal 100%, meluruh dengan tau 60 hari
SOP_REDUCES_EXCESS = 0.50                               # CM2 mengurangi excess operator baru sebesar 50%

BEFORE_END, AFTER_START = "2026-06-30", "2026-08-01"    # turunan dari countermeasure_log (lihat docs/definitions.md)
ALPHA = 0.05
COST_PER_HARNESS = 150_000                              # Rp per harness NG (asumsi, estimated)
COST_SCENARIOS = [100_000, 150_000, 250_000]


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
