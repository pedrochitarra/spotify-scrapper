"""Cities: what each city has in its Viral playlist ("Viral <city> BR")."""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
ui.title("City pulse", "What each city has in its Spotify Viral playlist · "
         + ui.coleta_badge(coleta))

cities = ui.query(
    "SELECT c.cid_codigo, c.cid_nome, c.cid_regiao, p.ply_codigo, "
    "COUNT(x.fxp_fai_codigo) tracks FROM cid_cidade c JOIN ply_playlist p "
    "ON p.ply_nome = 'Viral ' || c.cid_nome || ' BR' AND p.coleta = c.coleta "
    "JOIN fxp_faixaplaylist x ON x.fxp_ply_codigo = p.ply_codigo "
    "AND x.coleta = p.coleta WHERE c.coleta = ? GROUP BY c.cid_codigo "
    "ORDER BY c.cid_nome", (coleta,))
if cities.empty:
    ui.note("No Viral city playlists in this snapshot.")
    st.stop()

# The selectbox can be typed into, so it doubles as the city search
labels = (cities["cid_nome"] + " · " + cities["cid_regiao"].fillna("")).tolist()
default = next((i for i, n in enumerate(cities["cid_nome"])
                if n == "São Paulo"), 0)
choice = st.selectbox("City", labels, index=default,
                      placeholder="Search a city", label_visibility="collapsed")
city = cities.iloc[labels.index(choice)]
playlist = city.ply_codigo

if coleta == max(ui.coletas()):
    ui.note("The Viral city playlists stopped being updated in May 2024, so "
            f"this is what was viral in {ui.esc(city.cid_nome)} then.")

artists = ui.query(
    "SELECT a.art_codigo, TRIM(a.art_primeironome || ' ' || "
    "a.art_ultimonome) name, i.image_url, p.apy_quantidade tracks, "
    "(SELECT COUNT(*) FROM arc_artistacidade r WHERE r.arc_art_codigo = "
    "a.art_codigo AND r.coleta = a.coleta) cities FROM apy_artistaplaylist p "
    "JOIN art_artista a ON a.art_codigo = p.apy_art_codigo "
    "AND a.coleta = p.coleta LEFT JOIN artists_images i "
    "ON i.art_codigo = a.art_codigo WHERE p.coleta = ? "
    "AND p.apy_ply_codigo = ? "
    "ORDER BY p.apy_quantidade DESC, a.art_popularidade DESC",
    (coleta, playlist))
ui.stats([
    ("Tracks", f"{int(city.tracks):,}",
     f"in the Viral {ui.esc(city.cid_nome)} playlist"),
    ("Artists", f"{len(artists):,}", "with a track in the playlist")])

# Local favorites: in this playlist and in few other cities
local = artists[artists["cities"] < len(cities) / 4].sort_values(
    ["cities", "tracks"], ascending=[True, False]).head(6)
if not local.empty:
    ui.section("Local favorites", "in this playlist and in few other cities")
    ui.tiles(local, "c_local", "artist", "art_codigo",
             lambda r: ui.tile_html(
                 r.image_url, r.name,
                 "only here" if r.cities == 1 else f"in {r.cities} cities",
                 round_image=True))

left, right = st.columns(2, gap="large")
with left:
    ui.section("Top artists", "most tracks in the playlist")
    ui.rows(artists.head(20), "c_artists", "artist", "art_codigo",
            lambda i, r: ui.row_html(
                i, r.image_url, r.name,
                f"only in {ui.esc(city.cid_nome)}" if r.cities == 1
                else f"viral in {r.cities} cities",
                f"<b>{r.tracks}</b> track{'s' if r.tracks != 1 else ''}",
                round_image=True))
with right:
    tracks = ui.query(
        "SELECT f.fai_codigo, f.fai_nome, i.image_url, f.fai_popularidade, "
        "GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || a.art_ultimonome), "
        "', ') artists FROM fxp_faixaplaylist x JOIN fai_faixa f "
        "ON f.fai_codigo = x.fxp_fai_codigo AND f.coleta = x.coleta "
        "LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo "
        "LEFT JOIN afx_artistafaixa ax ON ax.afx_fai_codigo = f.fai_codigo "
        "AND ax.coleta = f.coleta LEFT JOIN art_artista a "
        "ON a.art_codigo = ax.afx_art_codigo AND a.coleta = f.coleta "
        "WHERE x.coleta = ? AND x.fxp_ply_codigo = ? GROUP BY f.fai_codigo "
        "ORDER BY f.fai_popularidade DESC LIMIT 20", (coleta, playlist))
    ui.section("Tracks", "by Spotify popularity")
    ui.rows(tracks, "c_tracks", "track", "fai_codigo",
            lambda i, r: ui.row_html(i, r.image_url, r.fai_nome,
                                     ui.esc(r.artists),
                                     ui.pop_bar(r.fai_popularidade)))
