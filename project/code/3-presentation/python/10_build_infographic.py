"""Langkah 11: one-sheet infografik (PDF dan PNG) dari CSV hasil. Dibuat sebagai HTML lalu dicetak dengan Chromium (Playwright)."""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT.parent / "design-and-report" / "src"))
import common as C  # noqa: E402
from report_lib import BLUE, GREY, HI, SOFT, bars, lines  # noqa: E402

R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
z = R("ztest.csv").set_index("scope").loc["Insulation damage (ID-01+02+03)"]
imp = R("impact.csv"); imp = imp[imp.biaya_per_unit == C.COST_PER_HARNESS].set_index("skenario")
wk = R("pchart.csv"); cause = R("cause.csv").pivot(index="defect_code", columns="period", values="rate")
pc = lambda v, d=1: f"{v * 100:.{d}f}".replace(".", ",") + "%"
fmt_i = lambda v: f"{v:,.0f}".replace(",", ".")
pct = lambda v: f"{v * 100:.1f}".replace(".", ",") + "%"
chart = lines([d[5:] for d in wk.week_start], [("UCL", HI, 1.5, wk.ucl.tolist()), ("Garis tengah", GREY, 1.5, wk.cl.tolist()), ("Rate mingguan", BLUE, 2.5, wk.p.tolist())],
              lambda v: pc(v, 1), "p-chart mingguan insulation damage rate", h=240, zero=True)
ids = [("ID-01", "Perakitan"), ("ID-02", "Tepi bracket"), ("ID-03", "Lain-lain")]
cbar = bars([(f"{c} {p}", cause.loc[c, p], col, f"{c} {p}: {pc(cause.loc[c, p], 2)}") for c, n in ids for p, col in (("before", GREY), ("after", BLUE))],
            lambda v: pc(v, 1), "Rate per sumber penyebab, before vs after", h=250, rot=30, small=True)
assert not (wk[wk.period == "after"].out.fillna("") != "").any(), "ada minggu after di luar batas kendali"
pv = "< 0,001" if z.p_value < 0.001 else f"{z.p_value:.3f}".replace(".", ",")
html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Infografik Project 4</title><style>
@page{{size:1100px 1500px;margin:0}}*{{box-sizing:border-box}}body{{margin:0;font:16px/1.5 "Source Sans 3",Calibri,Arial,sans-serif;color:#202124;background:#F8F9FA;width:1156px;padding:28px}}
h1{{margin:0;font-size:30px;color:#174EA6}}.sub{{color:#5F6368;margin:2px 0 18px}}.row{{display:grid;gap:14px;margin-bottom:14px}}.r3{{grid-template-columns:repeat(3,1fr)}}.r2{{grid-template-columns:1fr 1fr}}
.c{{background:#fff;border:1px solid #DADCE0;border-radius:16px;padding:16px 20px}}.k b{{display:block;font-size:40px;line-height:1.1;color:#1A73E8}}.k span{{color:#5F6368;font-size:14px}}
h3{{margin:0 0 6px;font-size:18px;color:#174EA6}}.rc svg{{width:100%;height:auto}}.rc svg text{{fill:#5F6368;font-size:12px}}.v{{background:#E6F4EA;border:1px solid #A8DAB5;color:#0D652D}}.v b{{color:#0D652D}}
.w{{background:#FEF7E0;border:1px solid #FDD663;font-size:14px}}.f{{color:#5F6368;font-size:13px;margin-top:10px}}</style></head><body>
<h1>Insulation damage turun {pct(z.rel_drop)} setelah QCC, dan penurunannya terbukti</h1>
<div class="sub">Project 4: Before–After Defect Reduction (QCC Insulation Damage, wire harness). Data simulasi Jan–Okt 2026.</div>
<div class="row r3"><div class="c k"><b>{pc(z.rate_before, 2)} → {pc(z.rate_after, 2)}</b><span>defect rate before (Jan–Jun) → after (Agu–Okt)</span></div>
<div class="c k"><b>p {pv}</b><span>z-test dua proporsi; CI 95% selisih {pc(z.ci_low, 2)} s.d. {pc(z.ci_high, 2)} (poin persentase)</span></div>
<div class="c k"><b>±{fmt_i(imp.loc['titik (hasil uji)', 'unit_per_tahun'])}</b><span>harness terselamatkan per tahun (estimated)</span></div></div>
<div class="row"><div class="c v"><b>Kesimpulan:</b> penurunan nyata secara statistik dan stabil di p-chart (tidak ada minggu after di luar batas kendali). Perbaikan layak dijadikan standar. Hasil ini membuktikan metode pada data simulasi, bukan kondisi pabrik.</div></div>
<div class="row r2"><div class="c"><h3>Stabilitas: p-chart mingguan</h3>{chart}</div><div class="c"><h3>Penurunan per sumber penyebab</h3>{cbar}</div></div>
<div class="row r2"><div class="c"><h3>Estimasi penghematan per tahun (estimated)</h3><p>Titik: <b>Rp {fmt_i(imp.loc['titik (hasil uji)', 'hemat_per_tahun'] / 1e6)} juta</b> (biaya Rp {fmt_i(C.COST_PER_HARNESS)} per harness, asumsi).<br>Rentang CI 95%: Rp {fmt_i(imp.loc['batas bawah (CI 95%)', 'hemat_per_tahun'] / 1e6)}–{fmt_i(imp.loc['batas atas (CI 95%)', 'hemat_per_tahun'] / 1e6)} juta.</p></div>
<div class="c w"><h3>Perhatikan</h3>Before–after bukan eksperimen: operator makin terampil, volume naik, dan bracket berganti pada periode yang sama. Pengaruh tiap countermeasure belum bisa dipisahkan dengan pasti.</div></div>
<div class="f">Sumber: project/results/2-analysis (ztest.csv, pchart.csv, cause.csv, impact.csv). Semua angka berasal dari data simulasi buatan sendiri.</div></body></html>"""
out = C.RES_PRESENT
tmp = out / "infographic.html"
tmp.write_text(html, encoding="utf-8")
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1156, "height": 1000})
    pg.goto(tmp.as_uri()); pg.wait_for_timeout(500)
    h = pg.evaluate("document.body.scrollHeight")
    pg.set_viewport_size({"width": 1156, "height": h}); pg.screenshot(path=str(out / "infographic.png"))
    pg.pdf(path=str(out / "infographic.pdf"), width="1156px", height=f"{h + 4}px", print_background=True)
    b.close()
tmp.unlink()
print("infographic.png/pdf", h)
