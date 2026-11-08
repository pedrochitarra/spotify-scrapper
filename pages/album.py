"""Album page: ?id=<spotify album id>"""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
album_id = ui.selected_id()

if not album_id:
    ui.title("Albums", "Albums of the tracks in the playlists · "
                       + ui.coleta_badge(coleta))
    top = ui.query(
        "SELECT b.alb_codigo, i.image_url, b.alb_nome, "
        "SUBSTR(b.alb_lancamento, 1, 4) year, b.alb_tipo FROM alb_album b "
        "LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo "
        "WHERE b.coleta = ?1 AND b.alb_codigo IN (SELECT fal_alb_codigo "
        "FROM fal_faixaalbum WHERE coleta = ?1) AND b.alb_tipo = 'album' "
        "ORDER BY b.alb_popularidade DESC LIMIT 24", (coleta,))
    ui.tiles(top, "pick", "album", "alb_codigo",
             lambda r: ui.tile_html(r.image_url, r.alb_nome,
                                    f"{r.year} · {ui.esc(r.alb_tipo)}"))
    st.stop()

found = ui.query(
    "SELECT b.*, i.image_url FROM alb_album b LEFT JOIN albums_images i "
    "ON i.alb_codigo = b.alb_codigo WHERE b.alb_codigo = ? AND b.coleta = ?",
    (album_id, coleta))
if found.empty:
    ui.note(f"This album is not in the {ui.coleta_label(coleta)} snapshot. "
            "Try the other one in the switch above.")
    st.stop()
album = found.iloc[0]

artists = ui.query(
    "SELECT a.art_codigo, a.art_primeironome, a.art_ultimonome, i.image_url "
    "FROM aal_artistaalbum aa JOIN art_artista a ON a.art_codigo = "
    "aa.aal_art_codigo AND a.coleta = aa.coleta LEFT JOIN artists_images i "
    "ON i.art_codigo = a.art_codigo WHERE aa.aal_alb_codigo = ? "
    "AND aa.coleta = ?", (album_id, coleta))
names = ", ".join(ui.artist_name(f, l) for f, l in
                  zip(artists["art_primeironome"], artists["art_ultimonome"]))
ui.hero(album["image_url"], album["alb_tipo"], album["alb_nome"],
        f"<b>{ui.esc(names)}</b> · {ui.esc(album['alb_lancamento'] or '')} · "
        f"{int(album['alb_qtdmusicas'])} tracks · {ui.coleta_badge(coleta)}",
        [("Popularity", "—" if album["alb_popularidade"] is None
          else int(album["alb_popularidade"]))])

left, right = st.columns([3, 2], gap="large")
with left:
    ui.section("Listen")
    ui.spotify_embed("album", album_id, height=420)
with right:
    tracks = ui.query(
        "SELECT f.fai_codigo, i.image_url, f.fai_nome, f.fai_popularidade, "
        "f.fai_duracao FROM fal_faixaalbum fa JOIN fai_faixa f "
        "ON f.fai_codigo = fa.fal_fai_codigo AND f.coleta = fa.coleta "
        "LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo "
        "WHERE fa.fal_alb_codigo = ? AND fa.coleta = ? "
        "ORDER BY f.fai_popularidade DESC", (album_id, coleta))
    if not tracks.empty:
        ui.section("In the playlists")
        ui.rows(tracks, "al_tracks", "track", "fai_codigo",
                lambda i, r: ui.row_html(i, r.image_url, r.fai_nome,
                                         ui.duration(r.fai_duracao),
                                         ui.pop_bar(r.fai_popularidade)))
    ui.section("Artists")
    ui.rows(artists, "al_artists", "artist", "art_codigo",
            lambda i, r: ui.row_html(
                "", r.image_url,
                ui.artist_name(r.art_primeironome, r.art_ultimonome),
                "Artist", round_image=True))
