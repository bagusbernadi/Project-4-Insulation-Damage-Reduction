-- Langkah 5: skema database DuckDB. Aturan CHECK / PRIMARY KEY / FOREIGN KEY mencegah data salah masuk.
CREATE TABLE dim_operator (
    operator_id VARCHAR PRIMARY KEY,
    shift       VARCHAR NOT NULL CHECK (shift IN ('Shift 1', 'Shift 2')),
    hire_date   DATE    NOT NULL,
    status      VARCHAR NOT NULL CHECK (status IN ('baru', 'lama'))
);
CREATE TABLE countermeasure_log (
    cm_id        INTEGER PRIMARY KEY,
    cm_name      VARCHAR NOT NULL,
    target_cause VARCHAR,
    station      VARCHAR NOT NULL,
    start_date   DATE    NOT NULL
);
CREATE TABLE production_daily (
    date         DATE    NOT NULL CHECK (date BETWEEN DATE '2026-01-01' AND DATE '2026-10-31'),
    shift        VARCHAR NOT NULL CHECK (shift IN ('Shift 1', 'Shift 2')),
    harness_type VARCHAR NOT NULL CHECK (harness_type IN ('A', 'B', 'C')),
    operator_id  VARCHAR NOT NULL REFERENCES dim_operator (operator_id),
    input_qty    INTEGER NOT NULL CHECK (input_qty > 0),
    ok_qty       INTEGER NOT NULL CHECK (ok_qty >= 0),
    ng_qty       INTEGER NOT NULL CHECK (ng_qty >= 0),
    PRIMARY KEY (date, shift, harness_type),
    CHECK (ng_qty <= input_qty),
    CHECK (ok_qty + ng_qty = input_qty)
);
CREATE TABLE ng_log (
    ng_id          VARCHAR PRIMARY KEY,
    date           DATE    NOT NULL,
    shift          VARCHAR NOT NULL,
    harness_type   VARCHAR NOT NULL,
    operator_id    VARCHAR NOT NULL REFERENCES dim_operator (operator_id),
    station_found  VARCHAR NOT NULL,
    defect_code    VARCHAR NOT NULL CHECK (defect_code IN ('ID-01', 'ID-02', 'ID-03', 'OT-01', 'OT-02', 'OT-03')),
    cause_source   VARCHAR NOT NULL CHECK (cause_source IN ('Perakitan', 'Tepi bracket', 'Lainnya')),
    bracket_source VARCHAR NOT NULL CHECK (bracket_source IN ('Supplier', 'In-house')),
    FOREIGN KEY (date, shift, harness_type) REFERENCES production_daily (date, shift, harness_type)
);
