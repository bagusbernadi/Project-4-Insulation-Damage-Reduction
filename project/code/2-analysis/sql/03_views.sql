-- Langkah 6: view defect rate. Periode diturunkan dari countermeasure_log:
--   before    = tanggal < awal bulan countermeasure pertama
--   after     = tanggal >= awal bulan countermeasure kedua
--   transisi  = di antaranya
-- Metrik utama: insulation damage rate = jumlah NG berkode ID-xx / input_qty.
CREATE OR REPLACE VIEW v_prod AS
SELECT p.*, o.status AS op_status,
       CASE WHEN p.date < (SELECT date_trunc('month', min(start_date)) FROM countermeasure_log) THEN 'before'
            WHEN p.date >= (SELECT date_trunc('month', start_date) FROM countermeasure_log WHERE cm_id = 2) THEN 'after'
            ELSE 'transisi' END AS period,
       CAST(date_trunc('week', p.date) AS DATE) AS week_start,
       strftime(p.date, '%Y-%m') AS month
FROM production_daily p JOIN dim_operator o USING (operator_id);

CREATE OR REPLACE VIEW v_ng AS
SELECT n.*, v.period, v.week_start, v.month, v.op_status,
       n.defect_code LIKE 'ID-%' AS is_insulation
FROM ng_log n JOIN v_prod v USING (date, shift, harness_type);

-- per periode
CREATE OR REPLACE VIEW v_rate_period AS
WITH a AS (SELECT period, sum(input_qty) AS input_qty, count(*) AS rows FROM v_prod GROUP BY period),
     b AS (SELECT period, count(*) AS ng_all, count(*) FILTER (WHERE is_insulation) AS ng_id FROM v_ng GROUP BY period)
SELECT period, input_qty, ng_all, ng_id, ng_id * 1.0 / input_qty AS rate_id, ng_all * 1.0 / input_qty AS rate_all
FROM a JOIN b USING (period);

-- per minggu (untuk p-chart)
CREATE OR REPLACE VIEW v_rate_week AS
WITH a AS (SELECT week_start, min(period) AS period, sum(input_qty) AS input_qty FROM v_prod GROUP BY week_start),
     b AS (SELECT week_start, count(*) FILTER (WHERE is_insulation) AS ng_id FROM v_ng GROUP BY week_start)
SELECT week_start, period, input_qty, coalesce(ng_id, 0) AS ng_id, coalesce(ng_id, 0) * 1.0 / input_qty AS rate_id
FROM a LEFT JOIN b USING (week_start) ORDER BY week_start;

-- per bulan
CREATE OR REPLACE VIEW v_rate_month AS
WITH a AS (SELECT month, min(period) AS period, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_all FROM v_prod GROUP BY month),
     b AS (SELECT month, count(*) FILTER (WHERE is_insulation) AS ng_id FROM v_ng GROUP BY month)
SELECT month, period, input_qty, ng_all, ng_id, ng_id * 1.0 / input_qty AS rate_id
FROM a JOIN b USING (month) ORDER BY month;

-- per dimensi (tipe harness, shift, status operator): dipakai Q3 dan Q10
CREATE OR REPLACE VIEW v_rate_dim AS
WITH a AS (SELECT period, 'harness_type' AS dim, harness_type AS val, sum(input_qty) AS input_qty FROM v_prod GROUP BY ALL
           UNION ALL SELECT period, 'shift', shift, sum(input_qty) FROM v_prod GROUP BY ALL
           UNION ALL SELECT period, 'shift_status', shift || ' / ' || op_status, sum(input_qty) FROM v_prod GROUP BY ALL),
     b AS (SELECT period, 'harness_type' AS dim, harness_type AS val, count(*) AS ng_id FROM v_ng WHERE is_insulation GROUP BY ALL
           UNION ALL SELECT period, 'shift', shift, count(*) FROM v_ng WHERE is_insulation GROUP BY ALL
           UNION ALL SELECT period, 'shift_status', shift || ' / ' || op_status, count(*) FROM v_ng WHERE is_insulation GROUP BY ALL)
SELECT dim, val, period, input_qty, coalesce(ng_id, 0) AS ng_id, coalesce(ng_id, 0) * 1.0 / input_qty AS rate_id
FROM a LEFT JOIN b USING (period, dim, val) ORDER BY dim, val, period;

-- per kode defect / sumber penyebab (Q9)
CREATE OR REPLACE VIEW v_rate_cause AS
WITH i AS (SELECT period, sum(input_qty) AS input_qty FROM v_prod GROUP BY period)
SELECT n.period, n.defect_code, n.cause_source, count(*) AS ng, i.input_qty, count(*) * 1.0 / i.input_qty AS rate
FROM v_ng n JOIN i USING (period) GROUP BY n.period, n.defect_code, n.cause_source, i.input_qty ORDER BY n.defect_code, n.period;

-- sumber bracket untuk NG tepi bracket (ID-02)
CREATE OR REPLACE VIEW v_bracket AS
SELECT period, bracket_source, count(*) AS ng_id02 FROM v_ng WHERE defect_code = 'ID-02' GROUP BY ALL ORDER BY period, bracket_source;

-- stasiun tempat NG insulation damage ditemukan
CREATE OR REPLACE VIEW v_station AS
SELECT period, station_found, count(*) AS ng_id FROM v_ng WHERE is_insulation GROUP BY ALL ORDER BY period, ng_id DESC;

-- rate per kode defect per bulan (Q8, Q9)
CREATE OR REPLACE VIEW v_rate_cause_month AS
WITH i AS (SELECT month, sum(input_qty) AS input_qty FROM v_prod GROUP BY month)
SELECT n.month, n.defect_code, count(*) AS ng, i.input_qty, count(*) * 1.0 / i.input_qty AS rate
FROM v_ng n JOIN i USING (month) GROUP BY n.month, n.defect_code, i.input_qty ORDER BY n.defect_code, n.month;
