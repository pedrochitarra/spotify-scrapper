"""Search artists, tracks and albums of the selected snapshot."""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
ui.title("Search", ui.coleta_badge(coleta))

term = st.text_input("Search", placeholder="What do you want to find?",
                     label_visibility="collapsed", key="search_term")
if len(term.strip()) < 2:
    ui.note("Type at least two characters: an artist, a track or an album.")
    st.stop()

like = f"%{term.strip()}%"
artists = ui.query(
    "SELECT a.art_codigo, i.image_url, a.art_primeironome, a.art_ultimonome, "
    "a.art_popularidade, a.art_seguidores FROM art_artista a "
    "LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo "
    "WHERE a.coleta = ? AND (a.art_primeironome || ' ' || a.art_ultimonome) "
    "LIKE ? ORDER BY a.art_popularidade DESC LIMIT 12", (coleta, like))
tracks = ui.query(
    "SELECT f.fai_codigo, i.image_url, f.fai_nome, f.fai_duracao, "
    "f.fai_popularidade, GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || "
    "a.art_ultimonome), ', ') artists FROM fai_faixa f "
    "LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo "
    "LEFT JOIN afx_artistafaixa x ON x.afx_fai_codigo = f.fai_codigo "
    "AND x.coleta = f.coleta LEFT JOIN art_artista a ON a.art_codigo = "
    "x.afx_art_codigo AND a.coleta = f.coleta WHERE f.coleta = ? "
    "AND f.fai_nome LIKE ? GROUP BY f.fai_codigo "
    "ORDER BY f.fai_popularidade DESC LIMIT 10", (coleta, like))
albums = ui.query(
    "SELECT b.alb_codigo, i.image_url, b.alb_nome, b.alb_tipo, "
    "SUBSTR(b.alb_lancamento, 1, 4) year FROM alb_album b "
    "LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo "
    "WHERE b.coleta = ? AND b.alb_nome LIKE ? "
    "ORDER BY b.alb_popularidade DESC LIMIT 12", (coleta, like))

if artists.empty and tracks.empty and albums.empty:
    ui.note(f"Nothing found for “{ui.esc(term)}” in this snapshot.")
    st.stop()

if not tracks.empty:
    ui.section("Tracks")
    ui.rows(tracks, "s_tracks", "track", "fai_codigo",
            lambda i, r: ui.row_html(i, r.image_url, r.fai_nome,
                                     ui.esc(r.artists),
                                     ui.duration(r.fai_duracao)))
if not artists.empty:
    ui.section("Artists")
    ui.tiles(artists, "s_artists", "artist", "art_codigo",
             lambda r: ui.tile_html(
                 r.image_url,
                 ui.artist_name(r.art_primeironome, r.art_ultimonome),
                 f"{ui.number(r.art_seguidores)} followers",
                 round_image=True))
if not albums.empty:
    ui.section("Albums")
    ui.tiles(albums, "s_albums", "album", "alb_codigo",
             lambda r: ui.tile_html(r.image_url, r.alb_nome,
                                    f"{r.year} · {ui.esc(r.alb_tipo)}"))
