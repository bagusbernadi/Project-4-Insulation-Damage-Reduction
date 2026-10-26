-- Memuat data bersih (dijalankan dari folder project/). Urutan: tabel induk dulu, baru tabel anak.
INSERT INTO dim_operator        SELECT * FROM read_csv('data/clean/dim_operator.csv', header = true, dateformat = '%Y-%m-%d');
INSERT INTO countermeasure_log  SELECT * FROM read_csv('data/clean/countermeasure_log.csv', header = true, dateformat = '%Y-%m-%d');
INSERT INTO production_daily    SELECT date, shift, harness_type, operator_id, input_qty, ok_qty, ng_qty FROM read_csv('data/clean/production_daily.csv', header = true, dateformat = '%Y-%m-%d');
INSERT INTO ng_log              SELECT ng_id, date, shift, harness_type, operator_id, station_found, defect_code, cause_source, bracket_source FROM read_csv('data/clean/ng_log.csv', header = true, dateformat = '%Y-%m-%d');
