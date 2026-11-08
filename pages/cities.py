"""Current Last.fm city affinity rankings."""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
ui.title("City pulse", "Current Last.fm metro charts · " + ui.coleta_badge(coleta))

cities = ui.query(
    "SELECT c.cid_codigo, c.cid_nome, COUNT(t.lfm_faixa) tracks "
    "FROM cid_cidade c LEFT JOIN lfm_city_track_chart t "
    "ON t.cid_codigo = c.cid_codigo AND t.coleta = c.coleta "
    "WHERE c.coleta = ? GROUP BY c.cid_codigo ORDER BY c.cid_nome",
    (coleta,))
if cities.empty:
    ui.note("No Last.fm city charts have been collected for this snapshot yet.")
    st.stop()

labels = cities.apply(
    lambda r: f"{r.cid_nome} · {int(r.tracks)} tracks", axis=1).tolist()
choice = st.selectbox("City", labels, label_visibility="collapsed")
city_id = int(cities.iloc[labels.index(choice)].cid_codigo)
city_name = cities.iloc[labels.index(choice)].cid_nome

summary = ui.query(
    "SELECT COUNT(DISTINCT lfm_artista) artists, "
    "COUNT(*) tracks FROM lfm_city_track_chart "
    "WHERE coleta = ? AND cid_codigo = ?", (coleta, city_id)).iloc[0]
ui.stats([
    ("Artists ranked", f"{int(summary.artists):,}", "Last.fm chart artists"),
    ("Tracks ranked", f"{int(summary.tracks):,}", "current metro chart")])

ui.section(city_name, "artist affinity from the current Last.fm chart")
ranking = ui.query(
    "SELECT lfm_artista artist, lfm_score score, lfm_faixas tracks "
    "FROM lfm_artist_city_score WHERE coleta = ? AND cid_codigo = ? "
    "ORDER BY lfm_score DESC LIMIT 30", (coleta, city_id))
if ranking.empty:
    ui.note("Last.fm returned no artist ranking for this city.")
else:
    rows = "".join(
        f"<div class='city-rank'><span class='city-pos'>{i}</span>"
        f"<div class='city-name'>{ui.esc(r.artist)}</div>"
        f"<span class='city-tracks'>{int(r.tracks)} tracks</span>"
        f"<b>{int(r.score)}</b></div>"
        for i, r in enumerate(ranking.itertuples(index=False), 1))
    st.html("<div class='city-ranking'>" + rows + "</div>")

ui.section("Top tracks", "the raw Last.fm signal behind the ranking")
tracks = ui.query(
    "SELECT lfm_posicao position, lfm_faixa track, lfm_artista artist "
    "FROM lfm_city_track_chart WHERE coleta = ? AND cid_codigo = ? "
    "ORDER BY lfm_posicao LIMIT 20", (coleta, city_id))
st.dataframe(tracks, hide_index=True, use_container_width=True,
             column_config={"position": "#", "track": "Track",
                            "artist": "Artist"})
