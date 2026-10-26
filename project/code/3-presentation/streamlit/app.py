"""Dashboard Streamlit (4 halaman): Ringkasan, Uji Signifikansi, Control Chart, Penyebab dan Dampak.
Jalankan dari folder project/:  streamlit run code/3-presentation/streamlit/app.py
Membaca data ringkas yang sudah di-commit di results/3-presentation/ (tidak perlu database). Semua data adalah simulasi."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"
st.set_page_config(page_title="Project 4: Before–After Defect Reduction", layout="wide")


@st.cache_data
def load():
    d = pd.read_csv(RES / "3-presentation" / "dash_rows.csv", parse_dates=["date", "week_start"])
    d["ng_id"] = d.ng_id01 + d.ng_id02 + d.ng_id03
    cm = pd.read_csv(RES / "3-presentation" / "dash_countermeasure.csv", parse_dates=["start_date"])
    return d, cm


data, cm = load()
BLUE, ORANGE, GREY = "#1A73E8", "#E8710A", "#9AA0A6"
st.sidebar.header("Filter")
types = st.sidebar.multiselect("Tipe harness", ["A", "B", "C"], default=["A", "B", "C"])
shifts = st.sidebar.multiselect("Shift", ["Shift 1", "Shift 2"], default=["Shift 1", "Shift 2"])
page = st.sidebar.radio("Halaman", ["1. Ringkasan", "2. Uji Signifikansi", "3. Control Chart", "4. Penyebab dan Dampak"])
st.sidebar.caption("Data simulasi buatan sendiri. Angka dampak berlabel estimated.")
d = data[data.harness_type.isin(types) & data["shift"].isin(shifts)]
if d.empty:
    st.warning("Pilih minimal satu tipe harness dan satu shift."); st.stop()
g = d.groupby("period").agg(n=("input_qty", "sum"), x=("ng_id", "sum"))
if not {"before", "after"} <= set(g.index):
    st.warning("Filter ini tidak memiliki data before atau after."); st.stop()
nb, xb, na, xa = g.loc["before", "n"], g.loc["before", "x"], g.loc["after", "n"], g.loc["after", "x"]
pb, pa = xb / nb, xa / na
z, p = proportions_ztest([xb, xa], [nb, na])
lo, hi = confint_proportions_2indep(xb, nb, xa, na, compare="diff", method="wald")
st.title("Project 4: Before–After Defect Reduction")
st.caption("QCC insulation damage pada perakitan wire harness. Before = Jan–Jun, transisi = Jul (tidak dipakai di uji), after = Agu–Okt 2026.")

if page.startswith("1"):
    c = st.columns(4)
    c[0].metric("Rate before", f"{pb:.2%}"); c[1].metric("Rate after", f"{pa:.2%}", f"{pa - pb:+.2%}".replace("%", " poin"), delta_color="inverse")
    c[2].metric("Penurunan relatif", f"{(pb - pa) / pb:.1%}"); c[3].metric("p-value (z-test)", "< 0,001" if p < 0.001 else f"{p:.3f}")
    m = d.groupby(["month", "period"]).agg(n=("input_qty", "sum"), x=("ng_id", "sum")).reset_index(); m["rate"] = m.x / m.n
    col = {"before": GREY, "transisi": "#AECBFA", "after": BLUE}
    f = go.Figure(go.Bar(x=m.month, y=m.rate, marker_color=m.period.map(col), text=(m.rate * 100).round(2).astype(str) + "%", textposition="outside"))
    f.update_layout(title="Insulation damage rate per bulan", yaxis_tickformat=".1%", height=380, margin=dict(t=50, b=20))
    st.plotly_chart(f, use_container_width=True)
    m["ng"], m["volume"] = m.x, m.n
    f2 = go.Figure([go.Bar(x=m.month, y=m.volume, name="Input (harness)", marker_color="#AECBFA"), go.Scatter(x=m.month, y=m.ng, name="Jumlah NG", yaxis="y2", line=dict(color=ORANGE, width=3))])
    f2.update_layout(title="Jumlah NG dan volume produksi: jumlah NG tidak cukup, bagi dengan input", yaxis2=dict(overlaying="y", side="right"), height=360, margin=dict(t=50, b=20))
    st.plotly_chart(f2, use_container_width=True)
elif page.startswith("2"):
    st.subheader("z-test dua proporsi (before vs after)")
    c = st.columns(4)
    c[0].metric("z", f"{z:.2f}"); c[1].metric("p-value", "< 0,001" if p < 0.001 else f"{p:.3f}")
    c[2].metric("Selisih rate", f"{(pb - pa) * 100:.2f} poin"); c[3].metric("CI 95% selisih", f"{lo * 100:.2f} s.d. {hi * 100:.2f} poin")
    st.success("Penurunan signifikan pada α = 0,05." if p < 0.05 else "Penurunan belum signifikan: data after belum cukup. Pemantauan perlu dilanjutkan.")
    st.markdown(f"Data: before {int(nb):,} harness ({int(xb):,} NG), after {int(na):,} harness ({int(xa):,} NG).".replace(",", "."))
    st.subheader("Simulasi: kapan penurunan yang sama menjadi terbukti")
    a, b = st.columns(2)
    r2 = a.slider("Rate after (%)", 1.0, 3.0, 2.2, 0.1) / 100; n2 = b.slider("Jumlah harness after", 2000, 40000, 18000, 1000)
    zz, pp = proportions_ztest([0.03 * 36000, r2 * n2], [36000, n2])
    st.write(f"Before 3,0% dari 36.000 harness. Penurunan relatif {(0.03 - r2) / 0.03:.1%}, p-value {pp:.4f}. Angka contoh, bukan hasil dari data.")
    st.dataframe(pd.read_csv(RES / "2-analysis" / "sample_size.csv")[["rel_drop", "n_per_group", "months_after", "power_actual"]].rename(columns={"rel_drop": "penurunan relatif", "n_per_group": "n per kelompok", "months_after": "bulan data after", "power_actual": "power dengan data saat ini"}))
elif page.startswith("3"):
    w = d.groupby(["week_start"]).agg(n=("input_qty", "sum"), x=("ng_id", "sum"), period=("period", "min")).reset_index()
    w = w[w.n >= w.n.max() * 0.2]; w["p"] = w.x / w.n
    cl = np.where(w.period == "after", pa, pb)
    sd = np.sqrt(cl * (1 - cl) / w.n)
    f = go.Figure()
    f.add_trace(go.Scatter(x=w.week_start, y=w.p, mode="lines+markers", name="Rate mingguan", line=dict(color=BLUE)))
    f.add_trace(go.Scatter(x=w.week_start, y=cl, name="Garis tengah", line=dict(color="#188038", dash="dash")))
    f.add_trace(go.Scatter(x=w.week_start, y=cl + 3 * sd, name="UCL", line=dict(color=ORANGE, dash="dot")))
    f.add_trace(go.Scatter(x=w.week_start, y=np.maximum(cl - 3 * sd, 0), name="LCL", line=dict(color=ORANGE, dash="dot")))
    for r in cm.itertuples():
        f.add_vline(x=r.start_date.timestamp() * 1000, line_dash="dash", line_color="#5F6368", annotation_text=f"CM{r.cm_id}", annotation_position="top")
    f.update_layout(title="p-chart mingguan (batas terpisah before dan after)", yaxis_tickformat=".1%", height=480, margin=dict(t=60))
    st.plotly_chart(f, use_container_width=True)
    out = ((w.p > cl + 3 * sd) | (w.p < cl - 3 * sd)).sum()
    st.info(f"{out} minggu berada di luar batas kendali. Titik-titik after yang berada di dalam batas menunjukkan proses stabil, bukan kebetulan satu-dua minggu.")
else:
    c = d.groupby("period")[["ng_id01", "ng_id02", "ng_id03", "input_qty"]].sum()
    names = {"ng_id01": "ID-01 Perakitan", "ng_id02": "ID-02 Tepi bracket", "ng_id03": "ID-03 Lain-lain"}
    f = go.Figure()
    for per, col in (("before", GREY), ("after", BLUE)):
        f.add_trace(go.Bar(name=per, x=list(names.values()), y=[c.loc[per, k] / c.loc[per, "input_qty"] for k in names], marker_color=col))
    f.update_layout(barmode="group", title="Rate per sumber penyebab", yaxis_tickformat=".2%", height=380, margin=dict(t=50))
    st.plotly_chart(f, use_container_width=True)
    st.subheader("Kalkulator penghematan (estimated)")
    a, b, e = st.columns(3)
    vol = a.number_input("Volume per bulan (harness)", 1000, 50000, int(round(na / 3, -2)), 100)
    cost = b.number_input("Biaya per harness NG (Rp, asumsi)", 10_000, 1_000_000, 150_000, 10_000)
    which = e.selectbox("Selisih rate yang dipakai", ["Titik (hasil uji)", "Batas bawah CI 95%", "Batas atas CI 95%"])
    dd = {"Titik (hasil uji)": pb - pa, "Batas bawah CI 95%": lo, "Batas atas CI 95%": hi}[which]
    saved = dd * vol
    k = st.columns(3)
    k[0].metric("Harness terselamatkan / bulan", f"{saved:,.0f}".replace(",", ".")); k[1].metric("Harness terselamatkan / tahun", f"{saved * 12:,.0f}".replace(",", "."))
    k[2].metric("Estimasi penghematan / tahun", f"Rp {saved * 12 * cost / 1e6:,.0f} juta".replace(",", "."))
    st.caption("Estimated / simulated. Biaya per harness adalah asumsi, bukan data aktual.")
