"""Langkah 11: membuat dan menjalankan notebook analisis Q1-Q14 (results/3-presentation/analysis.ipynb) dari CSV hasil."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

M, K = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    M("# Project 4: Before–After Defect Reduction (QCC Insulation Damage)\n\nAnalisis Q1–Q14. Semua tabel dibaca dari `results/` (hasil skrip SQL dan Python). Data adalah simulasi buatan sendiri. "
      "Before = Jan–Jun, transisi = Jul (tidak dipakai di uji), after = Agu–Okt 2026."),
    K("""from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
ROOT = Path.cwd()
while not (ROOT / 'results').exists():
    ROOT = ROOT.parent
R = lambda f: pd.read_csv(next((ROOT / 'results' / d / f) for d in ('1-data-preparation', '2-analysis', '3-presentation') if (ROOT / 'results' / d / f).exists()))
pd.options.display.float_format = '{:.4f}'.format
plt.rcParams.update({'figure.figsize': (9, 3.6), 'axes.spines.top': False, 'axes.spines.right': False})
BLUE, GREY, ORANGE = '#1A73E8', '#9AA0A6', '#E8710A'
z = R('ztest.csv').set_index('scope')"""),
    M("## Q1. Rate before dan after\nDefect rate = jumlah NG insulation damage (ID-01, ID-02, ID-03) dibagi input."),
    K("p = R('period.csv'); p"),
    K("m = R('month.csv'); c = m.period.map({'before': GREY, 'transisi': '#AECBFA', 'after': BLUE})\nplt.bar(m.month, m.rate_id * 100, color=c); plt.ylabel('rate (%)'); plt.title('Insulation damage rate per bulan'); plt.show()"),
    M("## Q2. Jumlah NG vs rate\nVolume after lebih tinggi, jadi jumlah NG turun jauh lebih sedikit daripada rate."),
    K("R('volume_vs_rate.csv')"),
    M("## Q3. Per tipe harness"),
    K("d = R('dim.csv'); d[d.dim == 'harness_type'].pivot(index='val', columns='period', values='rate_id')[['before', 'transisi', 'after']]"),
    K("z.loc[['Harness tipe A', 'Harness tipe B', 'Harness tipe C'], ['rate_before', 'rate_after', 'rel_drop', 'z', 'p_value', 'ci_low', 'ci_high']]"),
    M("## Q4. Uji signifikansi (z-test dua proporsi)\nH0: rate before = rate after. α = 0,05, varians gabungan."),
    K("z.loc[['Insulation damage (ID-01+02+03)'], ['n_before', 'x_before', 'rate_before', 'n_after', 'x_after', 'rate_after', 'z', 'p_value', 'significant']]"),
    M("## Q5. Confidence interval selisih rate (95%, Wald)"),
    K("z.loc[['Insulation damage (ID-01+02+03)'], ['diff', 'ci_low', 'ci_high', 'rel_drop']]"),
    M("## Q6. Jumlah sampel minimum\nPower 80%, α 0,05. Baris terakhir: penurunan terkecil yang masih terdeteksi dengan data after saat ini."),
    K("R('sample_size.csv')"),
    M("## Q7. Stabilitas: p-chart mingguan\nBatas 3σ terpisah untuk before dan after. Titik di luar batas ditandai."),
    K("w = R('pchart.csv'); x = pd.to_datetime(w.week_start)\nplt.plot(x, w.p * 100, '-o', ms=3, color=BLUE, label='rate mingguan'); plt.plot(x, w.cl * 100, '--', color='green', label='garis tengah')\nplt.plot(x, w.ucl * 100, ':', color=ORANGE, label='UCL/LCL'); plt.plot(x, w.lcl * 100, ':', color=ORANGE)\nfor r in pd.read_csv(ROOT / 'data' / 'clean' / 'countermeasure_log.csv').itertuples() if (ROOT / 'data' / 'clean').exists() else []:\n    plt.axvline(pd.Timestamp(r.start_date), color='#5F6368', ls='--', lw=1); plt.text(pd.Timestamp(r.start_date), plt.ylim()[1] * .95, f'CM{r.cm_id}')\nplt.ylabel('rate (%)'); plt.legend(); plt.show()\nw[w.out.notna()][['week_start', 'period', 'p', 'ucl', 'lcl', 'out']]"),
    M("## Q8. Kapan penurunan mulai terlihat\nTitik ubah terkuat pada deret mingguan dan efek tiap countermeasure (regresi logistik dengan indikator langkah, disesuaikan operator, shift, tipe)."),
    K("display(R('changepoint.csv')); display(R('cm_effect.csv')); R('cm_steps.csv')"),
    M("## Q9. Sumber penyebab"),
    K("c = R('cause.csv'); c.pivot(index='defect_code', columns='period', values='rate')[['before', 'transisi', 'after']]"),
    K("z.loc[['ID-01 Perakitan', 'ID-02 Tepi bracket', 'ID-03 Lain-lain'], ['rate_before', 'rate_after', 'diff', 'rel_drop', 'p_value']]"),
    M("## Q10. Apakah operator baru yang makin terampil penyebabnya?\nPenurunan juga terjadi pada operator lama, dan efek after tetap besar setelah disesuaikan."),
    K("display(z.loc[['Operator lama', 'Operator baru', 'Shift 1', 'Shift 2'], ['rate_before', 'rate_after', 'rel_drop', 'p_value']]); R('model.csv')"),
    M("## Q11–Q12. Dampak (estimated / simulated)\nUnit terselamatkan = selisih rate × volume per bulan. Biaya per harness adalah asumsi."),
    K("R('impact.csv')"),
    M("## Q13. Kualitas data dan sensitivitas"),
    K("display(R('cleaning_log.csv')); display(R('data_quality_summary.csv')); R('sensitivity.csv')[['scope', 'rate_before', 'rate_after', 'diff', 'z', 'p_value']]"),
    M("## Q14. Cek silang SQL, pandas, dan Excel"),
    K("a, b = R('crosscheck.csv'), R('crosscheck_excel.csv')\nprint(f'pandas: {(a.status == \"PASS\").sum()} dari {len(a)} PASS; Excel: {(b.status == \"PASS\").sum()} dari {len(b)} PASS')"),
    M("## Validasi: lima fakta yang ditanam"),
    K("R('ground_truth_check.csv')[['fact_no', 'fakta', 'ditemukan', 'hasil']]"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = C.RES_PRESENT / "analysis.ipynb"
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(C.ROOT)}}).execute()
nbf.write(nb, out)
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
print("notebook", out.name, len(nb.cells), "sel;", len(errs), "error")
assert not errs
