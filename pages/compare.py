"""Then vs now: the two snapshots side by side."""
import altair as alt
import pandas as pd
import streamlit as st

from src.utils import streamlit_utils as ui

options = sorted(ui.coletas())
if len(options) < 2:
    ui.note("Only one snapshot available, nothing to compare yet.")
    st.stop()
old, new = options[0], options[-1]
OLD, NEW = ui.coleta_label(old), ui.coleta_label(new)

ui.title("Then vs now", f"{ui.coleta_badge(old)} vs {ui.coleta_badge(new)}")
ui.note(
    "The <b>Viral city playlists</b> stopped being updated in May 2024 (they "
    "were maintained by the Every Noise at Once project), so playlist-based "
    f"numbers labelled {NEW} reflect what was viral around May 2024. "
    "Popularity, followers and the Top 200 chart are current.")
COLORS = alt.Scale(domain=[old, new], range=["#f5a623", "#1ed760"])

profile = ui.query(
    "SELECT coleta, COUNT(*) tracks, AVG(fai_duracao) / 1000.0 seconds, "
    "AVG(fai_explicita) explicit, AVG(fai_popularidade) popularity "
    "FROM fai_faixa WHERE coleta IN (?, ?) GROUP BY coleta",
    (old, new)).set_index("coleta")
a, b = profile.loc[old], profile.loc[new]
st.html("<div style='height:18px'></div>")
ui.stats([
    ("Tracks", f"{int(b.tracks):,}",
     ui.delta_html(b.tracks - a.tracks) + f" vs {OLD}"),
    ("Average length", f"{int(b.seconds // 60)}:{int(b.seconds % 60):02d}",
     ui.delta_html(b.seconds - a.seconds, lambda v: f"{v:.0f}", "s")),
    ("Explicit tracks", f"{b.explicit:.0%}",
     ui.delta_html((b.explicit - a.explicit) * 100, lambda v: f"{v:.1f}",
                   " pp")),
    ("Avg. track popularity", f"{b.popularity:.0f}",
     ui.delta_html(b.popularity - a.popularity, lambda v: f"{v:.1f}")),
])

# Release age ------------------------------------------------------------------
ui.section("How old are the songs?", "release age when collected")
ages = ui.query(
    "SELECT fa.coleta, CAST(SUBSTR(fa.coleta, 1, 4) AS INTEGER) - "
    "CAST(SUBSTR(b.alb_lancamento, 1, 4) AS INTEGER) AS age "
    "FROM fal_faixaalbum fa JOIN alb_album b ON b.alb_codigo = "
    "fa.fal_alb_codigo AND b.coleta = fa.coleta "
    "WHERE fa.coleta IN (?, ?) AND b.alb_lancamento IS NOT NULL", (old, new))
order = ["Same year", "1", "2–3", "4–5", "6–10", "11–20", "20+"]
ages["bucket"] = pd.cut(ages["age"], [-99, 0, 1, 3, 5, 10, 20, 999],
                        labels=order).astype(str)
ages = ages[ages["bucket"].isin(order)]
share = (ages.groupby(["coleta", "bucket"]).size()
         / ages.groupby("coleta").size()).rename("share").reset_index()
st.altair_chart(
    alt.Chart(share).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("bucket:N", sort=order, title="Years since release",
                axis=alt.Axis(labelAngle=0)),
        xOffset="coleta:N",
        y=alt.Y("share:Q", axis=alt.Axis(format="%"), title=None),
        color=alt.Color("coleta:N", scale=COLORS, title=None,
                        legend=alt.Legend(orient="top")),
        tooltip=["coleta", "bucket", alt.Tooltip("share", format=".1%")])
    .properties(height=300), width="stretch")

# Genres -----------------------------------------------------------------------
genres = ui.query(
    "SELECT g.coleta, g.gen_nome, COUNT(DISTINCT ag.age_art_codigo) artists "
    "FROM age_artistagenero ag JOIN gen_genero g ON g.gen_codigo = "
    "ag.age_gen_codigo AND g.coleta = ag.coleta "
    "JOIN apy_artistaplaylist p ON p.apy_art_codigo = ag.age_art_codigo "
    "AND p.coleta = ag.coleta WHERE ag.coleta IN (?, ?) "
    "GROUP BY g.coleta, g.gen_nome", (old, new))
if not genres.empty:
    ui.section("Genres", "share of genre tags of the artists in the playlists")
    genres["share"] = genres["artists"] / genres.groupby(
        "coleta")["artists"].transform("sum")
    top = genres.groupby("gen_nome")["share"].max().nlargest(12).index
    st.altair_chart(
        alt.Chart(genres[genres["gen_nome"].isin(top)]).mark_bar(
            cornerRadiusEnd=4).encode(
            y=alt.Y("gen_nome:N", sort=list(top), title=None),
            yOffset="coleta:N",
            x=alt.X("share:Q", axis=alt.Axis(format="%"), title=None),
            color=alt.Color("coleta:N", scale=COLORS, title=None,
                            legend=alt.Legend(orient="top")),
            tooltip=["coleta", "gen_nome", "artists",
                     alt.Tooltip("share", format=".1%")])
        .properties(height=480), width="stretch")

# Arrivals and departures --------------------------------------------------------
reach = ui.query(
    "SELECT p.coleta, p.apy_art_codigo art_codigo, a.art_primeironome, "
    "a.art_ultimonome, COUNT(DISTINCT p.apy_ply_codigo) playlists, "
    "i.image_url FROM apy_artistaplaylist p JOIN art_artista a "
    "ON a.art_codigo = p.apy_art_codigo AND a.coleta = p.coleta "
    "LEFT JOIN artists_images i ON i.art_codigo = p.apy_art_codigo "
    "WHERE p.coleta IN (?, ?) GROUP BY p.coleta, p.apy_art_codigo",
    (old, new))
before = reach[reach["coleta"] == old].set_index("art_codigo")
after = reach[reach["coleta"] == new].set_index("art_codigo")
arrived = after[~after.index.isin(before.index)].nlargest(12, "playlists")
left_ = before[~before.index.isin(after.index)].nlargest(12, "playlists")


def artist_tile(r):
    return ui.tile_html(r.image_url,
                        ui.artist_name(r.art_primeironome, r.art_ultimonome),
                        f"{r.playlists} playlists", round_image=True)


ui.section(f"New in {NEW}", "not in any playlist before")
ui.tiles(arrived.reset_index(), "cmp_new", "artist", "art_codigo",
         artist_tile)
ui.section(f"Gone since {OLD}", "in many playlists then, none now")
# These artists may not exist in the newest snapshot: open them in the old
with st.container():
    for start in range(0, len(left_), 6):
        cols = st.columns(6)
        for col, r in zip(cols, list(left_.reset_index().itertuples())[
                start:start + 6]):
            with col, st.container(key=f"lnk_cmp_left_{r.art_codigo}"):
                st.html(artist_tile(r))
                if st.button("Open", key=f"btn_cmp_left_{r.art_codigo}"):
                    st.switch_page("pages/artist.py", query_params={
                        "snap": old, "id": r.art_codigo})
