"""Home: what Brazil is listening to, and how the snapshots differ."""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
other = ui.other_coleta(coleta)

ui.title("What Brazil is streaming",
         f"Artists, tracks and albums behind the Viral city playlists and the "
         f"national Top 200 · {ui.coleta_badge(coleta)}")


def counts(c):
    return ui.query(
        "SELECT (SELECT COUNT(*) FROM art_artista WHERE coleta = ?1) artists,"
        " (SELECT COUNT(*) FROM fai_faixa WHERE coleta = ?1) tracks,"
        " (SELECT COUNT(*) FROM alb_album WHERE coleta = ?1) albums,"
        " (SELECT COUNT(*) FROM ply_playlist WHERE coleta = ?1) playlists",
        (c,)).iloc[0]


now = counts(coleta)
if now["artists"] == 0:
    ui.note("This snapshot is still empty. Run <code>python main.py</code>.")
    st.stop()
before = counts(other) if other else None
ui.stats([
    (label, f"{now[field]:,}",
     ui.delta_html(ui.delta(now[field], before[field]))
     + f" vs {ui.coleta_label(other)}" if before is not None else "")
    for label, field in [("Artists", "artists"), ("Tracks", "tracks"),
                         ("Albums", "albums"), ("Playlists", "playlists")]])

# City reach is a relative signal from the Viral city playlists, not a count
# of Spotify listeners. It is deliberately labeled as reach in the UI.
city_stats = ui.query(
    "SELECT COUNT(DISTINCT c.cid_codigo) cities, "
    "COUNT(DISTINCT a.apy_art_codigo) artists_with_city_reach "
    "FROM cid_cidade c LEFT JOIN ply_playlist p "
    "ON p.ply_nome LIKE 'Viral ' || c.cid_nome || ' BR' "
    "AND p.coleta = c.coleta LEFT JOIN apy_artistaplaylist a "
    "ON a.apy_ply_codigo = p.ply_codigo AND a.coleta = c.coleta "
    "WHERE c.coleta = ?", (coleta,)).iloc[0]
ui.stats([
    ("Cities represented", f"{int(city_stats.cities):,}",
     "Viral city playlists"),
    ("Artists with city reach", f"{int(city_stats.artists_with_city_reach):,}",
     "presence across at least one city")])

# Top 200 podium (2026+) ------------------------------------------------------
chart = ui.query(
    "SELECT c.chr_posicao, c.chr_fai_codigo, c.chr_streams, f.fai_nome, "
    "i.image_url, GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || "
    "a.art_ultimonome), ', ') artists FROM chr_chart c "
    "LEFT JOIN fai_faixa f ON f.fai_codigo = c.chr_fai_codigo "
    "AND f.coleta = c.chr_coleta LEFT JOIN faixas_images i "
    "ON i.fai_codigo = c.chr_fai_codigo LEFT JOIN afx_artistafaixa x "
    "ON x.afx_fai_codigo = c.chr_fai_codigo AND x.coleta = c.chr_coleta "
    "LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo "
    "AND a.coleta = c.chr_coleta WHERE c.chr_coleta = ? "
    "AND c.chr_tipo = 'daily' AND c.chr_posicao <= 4 "
    "GROUP BY c.chr_posicao ORDER BY c.chr_posicao", (coleta,))
if not chart.empty:
    ui.section("Top of the chart", "Spotify daily Top 200 Brazil")
    ui.tiles(chart, "podium", "track", "chr_fai_codigo",
             lambda r: ui.tile_html(
                 r.image_url, r.fai_nome,
                 f"{ui.esc(r.artists)} · {ui.number(r.chr_streams)} streams",
                 rank=r.chr_posicao), columns=4)

# Artists ----------------------------------------------------------------------
top = ui.query(
    "SELECT a.art_codigo, a.art_primeironome, a.art_ultimonome, "
    "a.art_popularidade, a.art_seguidores, i.image_url FROM art_artista a "
    "LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo "
    "WHERE a.coleta = ?1 AND a.art_codigo IN (SELECT afx_art_codigo FROM "
    "afx_artistafaixa WHERE coleta = ?1) "
    "ORDER BY a.art_popularidade DESC, a.art_seguidores DESC LIMIT 12",
    (coleta,))
ui.section("Most popular artists", "Spotify popularity score, 0–100")
ui.tiles(top, "top", "artist", "art_codigo",
         lambda r: ui.tile_html(
             r.image_url, ui.artist_name(r.art_primeironome, r.art_ultimonome),
             f"{ui.number(r.art_seguidores)} followers", round_image=True))

reach = ui.query(
    "SELECT p.apy_art_codigo art_codigo, a.art_primeironome, "
    "a.art_ultimonome, COUNT(DISTINCT p.apy_ply_codigo) playlists, "
    "i.image_url FROM apy_artistaplaylist p JOIN art_artista a "
    "ON a.art_codigo = p.apy_art_codigo AND a.coleta = p.coleta "
    "LEFT JOIN artists_images i ON i.art_codigo = p.apy_art_codigo "
    "WHERE p.coleta = ? GROUP BY p.apy_art_codigo "
    "ORDER BY playlists DESC LIMIT 10", (coleta,))
total_playlists = int(now["playlists"]) or 1
left, right = st.columns(2, gap="large")
with left:
    ui.section("Everywhere at once", "in the most Viral city playlists")
    ui.rows(reach, "reach", "artist", "art_codigo",
            lambda i, r: ui.row_html(
                i, r.image_url,
                ui.artist_name(r.art_primeironome, r.art_ultimonome),
                f"{r.playlists / total_playlists:.0%} of the cities",
                f"<b>{r.playlists}</b> playlists", round_image=True))

if not other:
    st.stop()

old, new = sorted([coleta, other])
compare = ui.query(
    "SELECT n.art_codigo, n.art_primeironome, n.art_ultimonome, "
    "o.art_popularidade pop_old, n.art_popularidade pop_new, i.image_url "
    "FROM art_artista n JOIN art_artista o ON o.art_codigo = n.art_codigo "
    "AND o.coleta = ?1 LEFT JOIN artists_images i "
    "ON i.art_codigo = n.art_codigo WHERE n.coleta = ?2 "
    "AND n.art_popularidade IS NOT NULL", (old, new))
compare["change"] = compare["pop_new"] - compare["pop_old"]

with right:
    ui.section("Biggest climbers", f"popularity {ui.coleta_label(old)} → "
                                   f"{ui.coleta_label(new)}")
    ui.rows(compare.nlargest(10, "change"), "rise", "artist", "art_codigo",
            lambda i, r: ui.row_html(
                i, r.image_url,
                ui.artist_name(r.art_primeironome, r.art_ultimonome),
                f"{int(r.pop_old)} → {int(r.pop_new)}",
                ui.delta_html(r.change), round_image=True))
