"""Track page: ?id=<spotify track id>"""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
track_id = ui.selected_id()

if not track_id:
    ui.title("Tracks", "The most popular tracks in the playlists · "
                       + ui.coleta_badge(coleta))
    top = ui.query(
        "SELECT f.fai_codigo, i.image_url, f.fai_nome, f.fai_popularidade, "
        "GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || a.art_ultimonome), "
        "', ') artists FROM fai_faixa f LEFT JOIN faixas_images i "
        "ON i.fai_codigo = f.fai_codigo LEFT JOIN afx_artistafaixa x "
        "ON x.afx_fai_codigo = f.fai_codigo AND x.coleta = f.coleta "
        "LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo "
        "AND a.coleta = f.coleta WHERE f.coleta = ? GROUP BY f.fai_codigo "
        "ORDER BY f.fai_popularidade DESC LIMIT 30", (coleta,))
    ui.rows(top, "pick", "track", "fai_codigo",
            lambda i, r: ui.row_html(i, r.image_url, r.fai_nome,
                                     ui.esc(r.artists),
                                     ui.pop_bar(r.fai_popularidade)))
    st.stop()

found = ui.query(
    "SELECT f.*, i.image_url FROM fai_faixa f LEFT JOIN faixas_images i "
    "ON i.fai_codigo = f.fai_codigo WHERE f.fai_codigo = ? AND f.coleta = ?",
    (track_id, coleta))
if found.empty:
    ui.note(f"This track is not in the {ui.coleta_label(coleta)} snapshot. "
            "Try the other one in the switch above.")
    st.stop()
track = found.iloc[0]

artists = ui.query(
    "SELECT a.art_codigo, a.art_primeironome, a.art_ultimonome, "
    "a.art_seguidores, i.image_url FROM afx_artistafaixa x "
    "JOIN art_artista a ON a.art_codigo = x.afx_art_codigo AND a.coleta = "
    "x.coleta LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo "
    "WHERE x.afx_fai_codigo = ? AND x.coleta = ? "
    "ORDER BY x.afx_principal DESC", (track_id, coleta))
album = ui.query(
    "SELECT b.alb_codigo, b.alb_nome, SUBSTR(b.alb_lancamento, 1, 4) year "
    "FROM fal_faixaalbum fa JOIN alb_album b ON b.alb_codigo = "
    "fa.fal_alb_codigo AND b.coleta = fa.coleta WHERE fa.fal_fai_codigo = ? "
    "AND fa.coleta = ?", (track_id, coleta))
chart = ui.query(
    "SELECT chr_tipo, chr_posicao, chr_streams, chr_total_streams "
    "FROM chr_chart WHERE chr_fai_codigo = ? AND chr_coleta = ?",
    (track_id, coleta)).set_index("chr_tipo")

names = ", ".join(ui.artist_name(f, l) for f, l in
                  zip(artists["art_primeironome"], artists["art_ultimonome"]))
explicit = " · 🅴" if track["fai_explicita"] in (1, True) else ""
album_text = (f" · {ui.esc(album.iloc[0]['alb_nome'])} "
              f"({album.iloc[0]['year']})") if not album.empty else ""
hero_stats = [("Popularity", "—" if track["fai_popularidade"] is None
               else int(track["fai_popularidade"]))]
if "daily" in chart.index:
    hero_stats += [("Top 200 today", f"#{chart.at['daily', 'chr_posicao']}"),
                   ("Streams today",
                    ui.number(chart.at["daily", "chr_streams"])),
                   ("Streams in Brazil",
                    ui.number(chart.at["daily", "chr_total_streams"]))]
if track["fai_reproducoes"] is not None and track["fai_reproducoes"] == \
        track["fai_reproducoes"]:
    hero_stats.append(("Plays", ui.number(track["fai_reproducoes"])))
ui.hero(track["image_url"], "Track", track["fai_nome"],
        f"<b>{ui.esc(names)}</b>{album_text} · "
        f"{ui.duration(track['fai_duracao'])}{explicit} · "
        f"{ui.coleta_badge(coleta)}", hero_stats)

st.html("<div style='height:16px'></div>")
ui.spotify_embed("track", track_id)

left, right = st.columns([2, 3], gap="large")
with left:
    ui.section("Artists")
    ui.rows(artists, "t_artists", "artist", "art_codigo",
            lambda i, r: ui.row_html(
                "", r.image_url,
                ui.artist_name(r.art_primeironome, r.art_ultimonome),
                f"{ui.number(r.art_seguidores)} followers",
                round_image=True))
    if not album.empty:
        ui.section("Album")
        ui.rows(album.assign(image_url=track["image_url"]), "t_album",
                "album", "alb_codigo",
                lambda i, r: ui.row_html("", r.image_url, r.alb_nome,
                                         r.year))
with right:
    playlists = ui.query(
        "SELECT p.ply_nome, p.ply_seguidores FROM fxp_faixaplaylist x "
        "JOIN ply_playlist p ON p.ply_codigo = x.fxp_ply_codigo "
        "AND p.coleta = x.coleta WHERE x.fxp_fai_codigo = ? "
        "AND x.coleta = ? ORDER BY p.ply_seguidores DESC", (track_id, coleta))
    ui.section("Viral in", f"{len(playlists)} city playlists")
    if playlists.empty:
        ui.note("Not in any Viral city playlist; it is here because of the "
                "Top 200 chart.")
    else:
        cities = [n.removeprefix("Viral ").removesuffix(" BR")
                  for n in playlists["ply_nome"]]
        st.html(ui.chips(cities))
