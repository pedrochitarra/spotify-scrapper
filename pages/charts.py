"""Top 200 Brazil (kworb.net mirror of Spotify Charts)."""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()

available = ui.query("SELECT chr_tipo, MAX(chr_data) chr_data FROM chr_chart "
                     "WHERE chr_coleta = ? GROUP BY chr_tipo", (coleta,))
ui.title("Top 200 Brazil", "The most streamed songs in Brazil on Spotify · "
                           + ui.coleta_badge(coleta))
if available.empty:
    ui.note("There is no chart in this snapshot: charts were added in the "
            "2026 collection.")
    st.stop()

kinds = available.set_index("chr_tipo")["chr_data"].to_dict()
c1, c2 = st.columns([1, 2])
with c1:
    kind = st.segmented_control(
        "Chart", list(kinds), default=list(kinds)[0], key="chart_kind",
        format_func=str.capitalize, label_visibility="collapsed") \
        or list(kinds)[0]
with c2:
    search = st.text_input("Filter", placeholder="Filter by track or artist",
                           label_visibility="collapsed")

chart = ui.query(
    "SELECT c.chr_posicao, c.chr_fai_codigo, c.chr_streams, "
    "c.chr_total_streams, f.fai_nome, f.fai_duracao, i.image_url, "
    "GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || a.art_ultimonome), ', ') "
    "artists FROM chr_chart c "
    "LEFT JOIN fai_faixa f ON f.fai_codigo = c.chr_fai_codigo "
    "AND f.coleta = c.chr_coleta "
    "LEFT JOIN faixas_images i ON i.fai_codigo = c.chr_fai_codigo "
    "LEFT JOIN afx_artistafaixa x ON x.afx_fai_codigo = c.chr_fai_codigo "
    "AND x.coleta = c.chr_coleta "
    "LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo "
    "AND a.coleta = c.chr_coleta "
    "WHERE c.chr_coleta = ? AND c.chr_tipo = ? "
    "GROUP BY c.chr_posicao ORDER BY c.chr_posicao", (coleta, kind))
if search:
    chart = chart[chart["fai_nome"].str.contains(search, case=False, na=False)
                  | chart["artists"].str.contains(search, case=False,
                                                  na=False)]

period = "today" if kind == "daily" else "this week"
st.html(f"<p class='sx-sub'>Chart of {kinds[kind]} · source kworb.net</p>")

PAGE = 50
pages = max(1, -(-len(chart) // PAGE))
if pages > 1:
    start = st.segmented_control(
        "Positions", [i * PAGE for i in range(pages)], default=0,
        key=f"chart_page_{kind}", label_visibility="collapsed",
        format_func=lambda s: f"{s + 1}–{min(s + PAGE, len(chart))}") or 0
else:
    start = 0

ui.rows(chart.iloc[start:start + PAGE], f"chart_{kind}", "track",
        "chr_fai_codigo",
        lambda i, r: ui.row_html(
            r.chr_posicao, r.image_url, r.fai_nome, ui.esc(r.artists),
            f"<b>{ui.number(r.chr_streams)}</b> {period} · "
            f"{ui.number(r.chr_total_streams)} total"))
if chart.empty:
    ui.note("No track matches the filter.")
