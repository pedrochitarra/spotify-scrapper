"""Collection steps. Each step reads what is still missing for the coleta from
the database, fetches it and commits, so an interrupted run can be resumed.
"""
import datetime
import logging
import re
import sqlite3

from src import db
from src.clients import Lastfm, SourceError, Spotify, kworb_chart

log = logging.getLogger(__name__)

PLAYLISTS_USER = "thesoundsofspotifycities"
CITY_PLAYLIST = re.compile(r"^Viral (.+) BR$")


def _image(obj: dict):
    images = obj.get("images") or []
    # Prefer a medium image (~300px), images come sorted largest first
    return (images[1] if len(images) > 1 else images[0])["url"] \
        if images else None


def _split_name(name: str) -> tuple:
    first, _, last = name.partition(" ")
    return first, last


def _city_name(playlist_name: str) -> str | None:
    """Extract the Brazilian city encoded by the playlist title."""
    match = CITY_PLAYLIST.match(playlist_name.strip())
    return match.group(1).strip() if match else None


def _save_playlist_city(conn: sqlite3.Connection, playlist_name: str,
                        coleta: str):
    city = _city_name(playlist_name)
    if not city:
        return
    existing = conn.execute(
        "SELECT cid_codigo FROM cid_cidade WHERE cid_nome = ? "
        "AND cid_pais = 'BR' ORDER BY coleta LIMIT 1", (city,)).fetchone()
    code = existing[0] if existing else conn.execute(
        "SELECT COALESCE(MAX(cid_codigo), 0) + 1 FROM cid_cidade").fetchone()[0]
    db.upsert(conn, "cid_cidade", [{
        "cid_codigo": code, "cid_nome": city, "cid_pais": "BR",
        "cid_regiao": None, "coleta": coleta}],
        ["cid_nome", "cid_pais", "cid_regiao", "coleta"])


def _missing(conn: sqlite3.Connection, wanted_sql: str, table: str,
             key: str, coleta: str) -> list:
    """Ids returned by wanted_sql that have no row in table for coleta."""
    return [row[0] for row in conn.execute(
        f"SELECT DISTINCT id FROM ({wanted_sql}) w WHERE id IS NOT NULL "
        f"AND id NOT IN (SELECT {key} FROM {table} WHERE coleta = ?)",
        (coleta, coleta))]


def start(conn: sqlite3.Connection, coleta: str):
    conn.execute(
        "INSERT INTO col_coleta (col_codigo, col_inicio, col_observacao) "
        "VALUES (?, ?, ?) ON CONFLICT (col_codigo) DO NOTHING",
        (coleta, datetime.date.today().isoformat(),
         "Official Spotify Web API + kworb.net charts + Last.fm similar "
         "artists. No plays per track or listeners per city."))
    conn.commit()


def finish(conn: sqlite3.Connection, coleta: str):
    conn.execute("UPDATE col_coleta SET col_fim = ? WHERE col_codigo = ?",
                 (datetime.date.today().isoformat(), coleta))
    conn.commit()


def playlists(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    """'Viral <city> BR' playlists from The Sounds of Spotify Cities."""
    done = {row[0] for row in conn.execute(
        "SELECT ply_codigo FROM ply_playlist WHERE coleta = ?", (coleta,))}
    found = [p for p in sp.paginate(f"users/{PLAYLISTS_USER}/playlists",
                                    limit=50)
             if p["name"].startswith("Viral ") and p["name"].endswith(" BR")]
    if not found:
        raise SourceError(f"No Viral BR playlists returned for "
                          f"{PLAYLISTS_USER}; the API may be failing, retry.")
    todo = [p for p in found if p["id"] not in done]
    log.info("Playlists: %d Viral BR found, %d new", len(found), len(todo))

    for i, item in enumerate(todo, 1):
        playlist = sp.get(f"playlists/{item['id']}",
                          fields="id,name,description,followers.total,images")
        if not playlist:
            log.warning("Playlist %s disappeared", item["id"])
            continue
        db.upsert(conn, "ply_playlist", [{
            "ply_codigo": playlist["id"], "ply_nome": playlist["name"],
            "ply_descricao": playlist["description"],
            "ply_seguidores": (playlist.get("followers") or {}).get("total"),
            "ply_scrapped": False, "coleta": coleta}],
            ["ply_codigo", "coleta"])
        _save_playlist_city(conn, playlist["name"], coleta)
        _save_image(conn, "playlists_images", "ply_codigo", playlist)
        if i % 50 == 0:
            conn.commit()
            log.info("  %d/%d playlists", i, len(todo))
    conn.commit()


def playlist_tracks(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    todo = [row[0] for row in conn.execute(
        "SELECT ply_codigo FROM ply_playlist WHERE coleta = ? "
        "AND NOT ply_scrapped", (coleta,))]
    log.info("Playlist tracks: %d playlists to read", len(todo))
    for i, playlist_id in enumerate(todo, 1):
        rows = [{"fxp_fai_codigo": item["track"]["id"],
                 "fxp_ply_codigo": playlist_id, "coleta": coleta}
                for item in sp.paginate(
                    f"playlists/{playlist_id}/tracks", limit=100,
                    fields="next,items(track(id,type))")
                if item.get("track") and item["track"].get("id")
                and item["track"].get("type") == "track"]
        db.upsert(conn, "fxp_faixaplaylist", rows,
                  ["fxp_fai_codigo", "fxp_ply_codigo", "coleta"])
        conn.execute("UPDATE ply_playlist SET ply_scrapped = TRUE "
                     "WHERE ply_codigo = ? AND coleta = ?",
                     (playlist_id, coleta))
        conn.commit()
        if i % 50 == 0:
            log.info("  %d/%d playlists", i, len(todo))


def charts(conn: sqlite3.Connection, coleta: str):
    """Top 200 Brazil (daily and weekly) from kworb.net."""
    for kind in ("daily", "weekly"):
        try:
            date, rows = kworb_chart(kind)
        except SourceError as e:
            log.error("Chart %s skipped: %s", kind, e)
            continue
        conn.execute("DELETE FROM chr_chart WHERE chr_coleta = ? "
                     "AND chr_tipo = ?", (coleta, kind))
        db.upsert(conn, "chr_chart", [{
            "chr_coleta": coleta, "chr_tipo": kind, "chr_data": date,
            "chr_posicao": r["position"], "chr_fai_codigo": r["track_id"],
            "chr_streams": r["streams"],
            "chr_total_streams": r["total_streams"]} for r in rows])
        conn.commit()
        log.info("Chart %s (%s): %d tracks", kind, date, len(rows))


def tracks(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    todo = _missing(
        conn,
        "SELECT fxp_fai_codigo AS id FROM fxp_faixaplaylist "
        "WHERE coleta = ?1 UNION SELECT chr_fai_codigo FROM chr_chart "
        "WHERE chr_coleta = ?1",
        "fai_faixa", "fai_codigo", coleta)
    log.info("Tracks: %d to fetch", len(todo))
    for n, track in enumerate(sp.several("tracks", todo, 50), 1):
        artists = [a["id"] for a in track["artists"] if a.get("id")]
        db.upsert(conn, "fai_faixa", [{
            "fai_codigo": track["id"], "fai_nome": track["name"],
            "fai_explicita": track["explicit"],
            "fai_popularidade": track.get("popularity"),
            "fai_duracao": track["duration_ms"], "fai_reproducoes": None,
            "coleta": coleta}], ["fai_codigo", "coleta"])
        db.upsert(conn, "afx_artistafaixa", [{
            "afx_art_codigo": artist_id, "afx_fai_codigo": track["id"],
            "afx_principal": i == 0, "coleta": coleta}
            for i, artist_id in enumerate(artists)],
            ["afx_art_codigo", "afx_fai_codigo", "coleta"])
        album = track.get("album") or {}
        if album.get("id"):
            db.upsert(conn, "fal_faixaalbum", [{
                "fal_fai_codigo": track["id"], "fal_alb_codigo": album["id"],
                "coleta": coleta}],
                ["fal_fai_codigo", "fal_alb_codigo", "coleta"])
            _save_image(conn, "faixas_images", "fai_codigo",
                        {"id": track["id"], "images": album.get("images")})
        if n % 500 == 0:
            conn.commit()
            log.info("  %d/%d tracks", n, len(todo))
    conn.commit()


def albums(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    todo = _missing(
        conn, "SELECT fal_alb_codigo AS id FROM fal_faixaalbum "
              "WHERE coleta = ?1 UNION SELECT aal_alb_codigo FROM "
              "aal_artistaalbum WHERE coleta = ?1",
        "alb_album", "alb_codigo", coleta)
    log.info("Albums: %d to fetch", len(todo))
    for n, album in enumerate(sp.several("albums", todo, 20), 1):
        release = album.get("release_date") or ""
        if len(release) == 4:
            release += "-01-01"
        elif len(release) == 7:
            release += "-01"
        db.upsert(conn, "alb_album", [{
            "alb_codigo": album["id"], "alb_nome": album["name"],
            "alb_lancamento": release or None,
            "alb_tipo": album["album_type"],
            "alb_qtdmusicas": album["total_tracks"],
            "alb_popularidade": album.get("popularity"), "coleta": coleta}],
            ["alb_codigo", "coleta"])
        db.upsert(conn, "aal_artistaalbum", [{
            "aal_art_codigo": a["id"], "aal_alb_codigo": album["id"],
            "coleta": coleta} for a in album["artists"] if a.get("id")],
            ["aal_art_codigo", "aal_alb_codigo", "coleta"])
        _save_image(conn, "albums_images", "alb_codigo", album)
        if n % 500 == 0:
            conn.commit()
            log.info("  %d/%d albums", n, len(todo))
    conn.commit()


def artists(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    todo = _missing(
        conn, "SELECT afx_art_codigo AS id FROM afx_artistafaixa "
              "WHERE coleta = ?1",
        "art_artista", "art_codigo", coleta)
    log.info("Artists: %d to fetch", len(todo))
    genre_codes = dict(conn.execute(
        "SELECT gen_nome, MIN(gen_codigo) FROM gen_genero GROUP BY gen_nome"))
    for n, artist in enumerate(sp.several("artists", todo, 50), 1):
        first, last = _split_name(artist["name"])
        db.upsert(conn, "art_artista", [{
            "art_codigo": artist["id"], "art_primeironome": first,
            "art_ultimonome": last,
            "art_seguidores": (artist.get("followers") or {}).get("total"),
            "art_popularidade": artist.get("popularity"),
            "art_ouvintes": None, "coleta": coleta}],
            ["art_codigo", "coleta"])
        for genre in artist.get("genres") or []:
            if genre not in genre_codes:
                genre_codes[genre] = max(genre_codes.values(), default=0) + 1
            db.upsert(conn, "gen_genero", [{
                "gen_nome": genre, "gen_codigo": genre_codes[genre],
                "coleta": coleta}], ["gen_nome", "coleta"])
            db.upsert(conn, "age_artistagenero", [{
                "age_art_codigo": artist["id"],
                "age_gen_codigo": genre_codes[genre], "coleta": coleta}],
                ["age_art_codigo", "age_gen_codigo", "coleta"])
        _save_image(conn, "artists_images", "art_codigo", artist)
        if n % 500 == 0:
            conn.commit()
            log.info("  %d/%d artists", n, len(todo))
    conn.commit()


def discography(conn: sqlite3.Connection, sp: Spotify, coleta: str):
    """Every album/single of the collected artists (slow: 1+ call each)."""
    # Artists with a single album row only have the one found via a track
    todo = [row[0] for row in conn.execute(
        "SELECT art_codigo FROM art_artista WHERE coleta = ?1 AND art_codigo "
        "NOT IN (SELECT aal_art_codigo FROM aal_artistaalbum WHERE "
        "coleta = ?1 GROUP BY aal_art_codigo HAVING COUNT(*) > 1)",
        (coleta,))]
    log.info("Discography: %d artists", len(todo))
    for i, artist_id in enumerate(todo, 1):
        rows = [{"aal_art_codigo": artist_id, "aal_alb_codigo": album["id"],
                 "coleta": coleta}
                for album in sp.paginate(f"artists/{artist_id}/albums",
                                         include_groups="album,single",
                                         limit=50)]
        db.upsert(conn, "aal_artistaalbum", rows,
                  ["aal_art_codigo", "aal_alb_codigo", "coleta"])
        conn.commit()
        if i % 100 == 0:
            log.info("  %d/%d artists", i, len(todo))
    albums(conn, sp, coleta)


def similar_artists(conn: sqlite3.Connection, lastfm: Lastfm, coleta: str):
    """Similar artists from Last.fm, kept only when they are in the coleta."""
    artists_by_name = {}
    for code, first, last in conn.execute(
            "SELECT art_codigo, art_primeironome, art_ultimonome "
            "FROM art_artista WHERE coleta = ?", (coleta,)):
        artists_by_name[f"{first} {last}".strip().casefold()] = code
    names = {code: name for name, code in artists_by_name.items()}
    done = {row[0] for row in conn.execute(
        "SELECT DISTINCT aa_art_a_codigo FROM aa_artistaartista "
        "WHERE coleta = ?", (coleta,))}
    todo = [code for code in names if code not in done]
    log.info("Similar artists: %d artists to query on Last.fm", len(todo))

    for i, code in enumerate(todo, 1):
        rows = [{"aa_art_a_codigo": code, "aa_art_b_codigo": other,
                 "aa_similaridade": match, "aa_fonte": "lastfm",
                 "coleta": coleta}
                for name, match in lastfm.similar_artists(names[code])
                if (other := artists_by_name.get(name.casefold()))
                and other != code]
        db.upsert(conn, "aa_artistaartista", rows,
                  ["aa_art_a_codigo", "aa_art_b_codigo", "coleta"])
        if i % 100 == 0:
            conn.commit()
            log.info("  %d/%d artists", i, len(todo))
    conn.commit()


def artist_playlist_counts(conn: sqlite3.Connection, coleta: str):
    """Rebuild apy_artistaplaylist: how many tracks of each artist are in
    each playlist."""
    # Backfill city rows for playlists collected before city normalization was
    # added, so resuming an existing coleta is enough to populate the model.
    for (playlist_name,) in conn.execute(
            "SELECT ply_nome FROM ply_playlist WHERE coleta = ?", (coleta,)):
        _save_playlist_city(conn, playlist_name, coleta)

    conn.execute("DELETE FROM apy_artistaplaylist WHERE coleta = ?",
                 (coleta,))
    conn.execute(
        "INSERT INTO apy_artistaplaylist (apy_art_codigo, apy_ply_codigo, "
        "apy_quantidade, coleta) SELECT afx_art_codigo, fxp_ply_codigo, "
        "COUNT(*), ?1 FROM fxp_faixaplaylist JOIN afx_artistafaixa "
        "ON afx_fai_codigo = fxp_fai_codigo AND afx_artistafaixa.coleta = ?1 "
        "WHERE fxp_faixaplaylist.coleta = ?1 "
        "GROUP BY afx_art_codigo, fxp_ply_codigo", (coleta,))
    # The city is encoded in the playlist title ("Viral <city> BR"). Keep a
    # normalized artist/city relation so the UI can answer city questions
    # without parsing labels on every page.
    conn.execute("DELETE FROM arc_artistacidade WHERE coleta = ?", (coleta,))
    conn.execute(
        "INSERT INTO arc_artistacidade (arc_art_codigo, arc_cid_codigo, "
        "arc_ouvintes, coleta) "
        "SELECT DISTINCT p.apy_art_codigo, c.cid_codigo, NULL, ? "
        "FROM apy_artistaplaylist p "
        "JOIN ply_playlist pl ON pl.ply_codigo = p.apy_ply_codigo "
        "AND pl.coleta = p.coleta "
        "JOIN cid_cidade c ON c.cid_nome = TRIM(SUBSTR(pl.ply_nome, 7, "
        "LENGTH(pl.ply_nome) - 9)) AND c.cid_pais = 'BR' "
        "AND c.coleta = p.coleta WHERE p.coleta = ?", (coleta, coleta))
    conn.commit()


def _save_image(conn: sqlite3.Connection, table: str, key: str, obj: dict):
    url = _image(obj)
    if url:
        db.upsert(conn, table, [{key: obj["id"], "image_url": url}], [key])
