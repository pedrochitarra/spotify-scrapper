"""Artist page: ?id=<spotify artist id>"""
import streamlit as st

from src.utils import streamlit_utils as ui

coleta = ui.snapshot_switch()
other = ui.other_coleta(coleta)
artist_id = ui.selected_id()

if not artist_id:
    ui.title("Artists", "Pick one, or use Search · " + ui.coleta_badge(coleta))
    top = ui.query(
        "SELECT a.art_codigo, a.art_primeironome, a.art_ultimonome, "
        "a.art_seguidores, i.image_url FROM art_artista a "
        "LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo "
        "WHERE a.coleta = ?1 AND a.art_codigo IN (SELECT afx_art_codigo "
        "FROM afx_artistafaixa WHERE coleta = ?1) "
        "ORDER BY a.art_popularidade DESC LIMIT 24", (coleta,))
    ui.tiles(top, "pick", "artist", "art_codigo",
             lambda r: ui.tile_html(
                 r.image_url,
                 ui.artist_name(r.art_primeironome, r.art_ultimonome),
                 f"{ui.number(r.art_seguidores)} followers",
                 round_image=True))
    st.stop()

found = ui.query(
    "SELECT a.*, i.image_url FROM art_artista a LEFT JOIN artists_images i "
    "ON i.art_codigo = a.art_codigo WHERE a.art_codigo = ? AND a.coleta = ?",
    (artist_id, coleta))
if found.empty:
    ui.note(f"This artist is not in the {ui.coleta_label(coleta)} snapshot. "
            "Try the other one in the switch above.")
    st.stop()
info = found.iloc[0]
name = ui.artist_name(info["art_primeironome"], info["art_ultimonome"])

previous = ui.query(
    "SELECT art_seguidores, art_popularidade FROM art_artista "
    "WHERE art_codigo = ? AND coleta = ?", (artist_id, other)) \
    if other else None
prev = previous.iloc[0] if previous is not None and not previous.empty \
    else None

genres = ui.query(
    "SELECT DISTINCT g.gen_nome FROM age_artistagenero ag JOIN gen_genero g "
    "ON g.gen_codigo = ag.age_gen_codigo WHERE ag.age_art_codigo = ? "
    "AND ag.coleta = ?", (artist_id, coleta))["gen_nome"]
playlists = ui.query(
    "SELECT COUNT(DISTINCT apy_ply_codigo) n FROM apy_artistaplaylist "
    "WHERE apy_art_codigo = ? AND coleta = ?", (artist_id, coleta)).iloc[0, 0]

hero_stats = [
    ("Followers", ui.number(info["art_seguidores"])),
    ("Popularity", "—" if info["art_popularidade"] is None
     else int(info["art_popularidade"])),
    ("Viral city playlists", playlists),
]
if info["art_ouvintes"] is not None and info["art_ouvintes"] == \
        info["art_ouvintes"]:
    hero_stats.append(("Monthly listeners", ui.number(info["art_ouvintes"])))
meta = ui.coleta_badge(coleta)
if prev is not None:
    meta += (f" &nbsp; popularity {ui.delta_html(ui.delta(info['art_popularidade'], prev['art_popularidade']))}"
             f" · followers {ui.delta_html(ui.delta(info['art_seguidores'], prev['art_seguidores']))}"
             f" since {ui.coleta_label(other)}")
ui.hero(info["image_url"], "Artist", name, meta, hero_stats,
        round_image=True)
if len(genres):
    st.html(f"<div style='margin-top:14px'>"
            f"{ui.chips(g.title() for g in genres)}</div>")

left, right = st.columns([3, 2], gap="large")
with left:
    tracks = ui.query(
        "SELECT f.fai_codigo, i.image_url, f.fai_nome, f.fai_popularidade, "
        "f.fai_duracao, (SELECT COUNT(*) FROM fxp_faixaplaylist p WHERE "
        "p.fxp_fai_codigo = f.fai_codigo AND p.coleta = f.coleta) playlists "
        "FROM afx_artistafaixa x JOIN fai_faixa f ON f.fai_codigo = "
        "x.afx_fai_codigo AND f.coleta = x.coleta LEFT JOIN faixas_images i "
        "ON i.fai_codigo = f.fai_codigo WHERE x.afx_art_codigo = ? "
        "AND x.coleta = ? ORDER BY f.fai_popularidade DESC LIMIT 10",
        (artist_id, coleta))
    ui.section("Popular", "tracks in the playlists and charts")
    if tracks.empty:
        ui.note("No tracks of this artist were collected in this snapshot.")
    ui.rows(tracks, "a_tracks", "track", "fai_codigo",
            lambda i, r: ui.row_html(
                i, r.image_url, r.fai_nome,
                f"{r.playlists} playlists · {ui.duration(r.fai_duracao)}",
                ui.pop_bar(r.fai_popularidade)))
with right:
    ui.section("Listen")
    ui.spotify_embed("artist", artist_id, height=380)

albums = ui.query(
    "SELECT b.alb_codigo, i.image_url, b.alb_nome, b.alb_tipo, "
    "SUBSTR(b.alb_lancamento, 1, 4) year FROM aal_artistaalbum aa "
    "JOIN alb_album b ON b.alb_codigo = aa.aal_alb_codigo AND b.coleta = "
    "aa.coleta LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo "
    "WHERE aa.aal_art_codigo = ? AND aa.coleta = ? "
    "ORDER BY b.alb_lancamento DESC LIMIT 12", (artist_id, coleta))
if not albums.empty:
    ui.section("Discography")
    ui.tiles(albums, "a_albums", "album", "alb_codigo",
             lambda r: ui.tile_html(r.image_url, r.alb_nome,
                                    f"{r.year} · {ui.esc(r.alb_tipo)}"))

similar = ui.query(
    "SELECT a.art_codigo, i.image_url, a.art_primeironome, "
    "a.art_ultimonome, s.aa_similaridade, s.aa_fonte FROM aa_artistaartista s "
    "JOIN art_artista a ON a.art_codigo = s.aa_art_b_codigo AND a.coleta = "
    "s.coleta LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo "
    "WHERE s.aa_art_a_codigo = ? AND s.coleta = ? "
    "ORDER BY s.aa_similaridade DESC NULLS LAST, a.art_popularidade DESC "
    "LIMIT 12", (artist_id, coleta))
if not similar.empty:
    source = ("Last.fm" if similar["aa_fonte"].iloc[0] == "lastfm"
              else "Spotify related artists (retired in 2024)")
    ui.section("Fans also like", source)
    ui.tiles(similar, "a_similar", "artist", "art_codigo",
             lambda r: ui.tile_html(
                 r.image_url,
                 ui.artist_name(r.art_primeironome, r.art_ultimonome),
                 f"{r.aa_similaridade:.0%} similar"
                 if r.aa_similaridade == r.aa_similaridade
                 and r.aa_similaridade is not None else "Related",
                 round_image=True))

cities = ui.query(
    "SELECT c.cid_nome, c.cid_regiao, c.cid_pais, r.arc_ouvintes "
    "FROM arc_artistacidade r JOIN cid_cidade c ON c.cid_codigo = "
    "r.arc_cid_codigo WHERE r.arc_art_codigo = ? AND r.coleta = ? "
    "ORDER BY r.arc_ouvintes DESC LIMIT 10", (artist_id, coleta))
if not cities.empty:
    ui.section("Where people listen", "monthly listeners by city")
    top_listeners = cities["arc_ouvintes"].max() or 1
    st.html("".join(
        f"<div class='row' style='grid-template-columns:34px minmax(0,1fr) "
        f"auto'><div class='n'>{i}</div><div><div class='t'>"
        f"{ui.esc(r.cid_nome)}</div><div class='s'>{ui.esc(r.cid_regiao)}, "
        f"{ui.esc(r.cid_pais)}</div></div><div class='r'><b>"
        f"{ui.number(r.arc_ouvintes)}</b><span class='pop'><i style='width:"
        f"{100 * r.arc_ouvintes / top_listeners:.0f}%'></i></span></div></div>"
        for i, r in enumerate(cities.itertuples(), 1)))
