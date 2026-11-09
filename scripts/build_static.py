"""Build the fast Vue frontend into _site/ (the root of the GitHub Pages site).

Every page reads JSON computed here, so nothing heavy is downloaded in the
browser (important on phones): one file for home, charts, the city list,
"then vs now" and the search index, and one small file per city, artist,
track and album. It reads the slimmed database that build_pages.py puts in
_site/streamlit/data/, so both frontends show the same data.

Usage: python scripts/build_pages.py && python scripts/build_static.py
"""
import gzip
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLIM = ROOT / "_site" / "streamlit" / "data" / "spotify.db.gz"
OUT = ROOT / "_site"
SRC = ROOT / "static_site"

# GitHub Pages serves only the root 404.html: send Streamlit routes
# (/streamlit/artist) to the Streamlit app, anything else to the home
NOT_FOUND = r"""<!doctype html><meta charset="utf-8"><script>
const m = location.pathname.match(/^(.*?\/)streamlit\/([^/]+)\/?$/);
location.replace(m ? m[1] + "streamlit/?page=" + m[2] : location.pathname.replace(/\/streamlit\/.*$|\/[^/]*$/, "/"));
</script>"""

IMAGE_PREFIX = "https://i.scdn.co/image/"
ARTISTS = ("GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || "
           "a.art_ultimonome), ', ') artists")


def rows(conn, sql, params=()):
    cur = conn.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def home(conn, snap):
    counts = rows(conn,
        "SELECT (SELECT COUNT(*) FROM art_artista WHERE coleta = ?1) artists,"
        " (SELECT COUNT(*) FROM fai_faixa WHERE coleta = ?1) tracks,"
        " (SELECT COUNT(*) FROM alb_album WHERE coleta = ?1) albums,"
        " (SELECT COUNT(*) FROM ply_playlist WHERE coleta = ?1) playlists",
        (snap,))[0]
    reach_stats = rows(conn,
        "SELECT COUNT(DISTINCT c.cid_codigo) cities, "
        "COUNT(DISTINCT a.apy_art_codigo) artists FROM cid_cidade c "
        "LEFT JOIN ply_playlist p ON p.ply_nome LIKE 'Viral ' || c.cid_nome "
        "|| ' BR' AND p.coleta = c.coleta LEFT JOIN apy_artistaplaylist a "
        "ON a.apy_ply_codigo = p.ply_codigo AND a.coleta = c.coleta "
        "WHERE c.coleta = ?", (snap,))[0]
    podium = rows(conn,
        "SELECT c.chr_posicao pos, c.chr_fai_codigo id, c.chr_streams streams,"
        f" f.fai_nome name, i.image_url img, {ARTISTS} FROM chr_chart c "
        "LEFT JOIN fai_faixa f ON f.fai_codigo = c.chr_fai_codigo "
        "AND f.coleta = c.chr_coleta LEFT JOIN faixas_images i "
        "ON i.fai_codigo = c.chr_fai_codigo LEFT JOIN afx_artistafaixa x "
        "ON x.afx_fai_codigo = c.chr_fai_codigo AND x.coleta = c.chr_coleta "
        "LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo "
        "AND a.coleta = c.chr_coleta WHERE c.chr_coleta = ? "
        "AND c.chr_tipo = 'daily' AND c.chr_posicao <= 4 "
        "GROUP BY c.chr_posicao ORDER BY c.chr_posicao", (snap,))
    top = rows(conn,
        "SELECT a.art_codigo id, TRIM(a.art_primeironome || ' ' || "
        "a.art_ultimonome) name, a.art_seguidores followers, i.image_url img "
        "FROM art_artista a LEFT JOIN artists_images i "
        "ON i.art_codigo = a.art_codigo WHERE a.coleta = ?1 AND a.art_codigo "
        "IN (SELECT afx_art_codigo FROM afx_artistafaixa WHERE coleta = ?1) "
        "ORDER BY a.art_popularidade DESC, a.art_seguidores DESC LIMIT 12",
        (snap,))
    reach = rows(conn,
        "SELECT p.apy_art_codigo id, TRIM(a.art_primeironome || ' ' || "
        "a.art_ultimonome) name, COUNT(DISTINCT p.apy_ply_codigo) playlists, "
        "i.image_url img FROM apy_artistaplaylist p JOIN art_artista a "
        "ON a.art_codigo = p.apy_art_codigo AND a.coleta = p.coleta "
        "LEFT JOIN artists_images i ON i.art_codigo = p.apy_art_codigo "
        "WHERE p.coleta = ? GROUP BY p.apy_art_codigo "
        "ORDER BY playlists DESC LIMIT 10", (snap,))
    return {"counts": counts, "reach_stats": reach_stats, "podium": podium,
            "top": top, "reach": reach}


def climbers(conn, old, new):
    return rows(conn,
        "SELECT n.art_codigo id, TRIM(n.art_primeironome || ' ' || "
        "n.art_ultimonome) name, o.art_popularidade pop_old, "
        "n.art_popularidade pop_new, i.image_url img FROM art_artista n "
        "JOIN art_artista o ON o.art_codigo = n.art_codigo AND o.coleta = ?1 "
        "LEFT JOIN artists_images i ON i.art_codigo = n.art_codigo "
        "WHERE n.coleta = ?2 AND n.art_popularidade IS NOT NULL "
        "AND o.art_popularidade IS NOT NULL "
        "ORDER BY n.art_popularidade - o.art_popularidade DESC LIMIT 10",
        (old, new))


def charts(conn, snap):
    out = {}
    for kind, date in conn.execute(
            "SELECT chr_tipo, MAX(chr_data) FROM chr_chart WHERE chr_coleta = ?"
            " GROUP BY chr_tipo ORDER BY chr_tipo", (snap,)).fetchall():
        out[kind] = {"date": date, "rows": rows(conn,
            "SELECT c.chr_posicao pos, c.chr_fai_codigo id, c.chr_streams "
            "streams, c.chr_total_streams total, f.fai_nome name, "
            f"i.image_url img, {ARTISTS} FROM chr_chart c "
            "LEFT JOIN fai_faixa f ON f.fai_codigo = c.chr_fai_codigo "
            "AND f.coleta = c.chr_coleta LEFT JOIN faixas_images i "
            "ON i.fai_codigo = c.chr_fai_codigo LEFT JOIN afx_artistafaixa x "
            "ON x.afx_fai_codigo = c.chr_fai_codigo AND x.coleta = c.chr_coleta"
            " LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo "
            "AND a.coleta = c.chr_coleta WHERE c.chr_coleta = ? "
            "AND c.chr_tipo = ? GROUP BY c.chr_posicao ORDER BY c.chr_posicao",
            (snap, kind))}
    return out


# A city's playlist is "Viral <city> BR"
CITY_PLAYLIST = ("JOIN ply_playlist pl ON pl.ply_nome = 'Viral ' || c.cid_nome "
                 "|| ' BR' AND pl.coleta = c.coleta")


def cities(conn, snap):
    """Index of the cities with a Viral playlist, and one file per city."""
    index = rows(conn,
        "SELECT c.cid_codigo id, c.cid_nome name, c.cid_regiao region, "
        "pl.ply_codigo playlist, COUNT(x.fxp_fai_codigo) tracks "
        "FROM cid_cidade c "
        f"{CITY_PLAYLIST} JOIN fxp_faixaplaylist x "
        "ON x.fxp_ply_codigo = pl.ply_codigo AND x.coleta = pl.coleta "
        "WHERE c.coleta = ? GROUP BY c.cid_codigo ORDER BY c.cid_nome",
        (snap,))
    # In how many cities each artist is: few cities = a local favorite
    reach = dict(conn.execute(
        "SELECT arc_art_codigo, COUNT(*) FROM arc_artistacidade "
        "WHERE coleta = ? GROUP BY arc_art_codigo", (snap,)).fetchall())
    details = {}
    for city in index:
        playlist = city.pop("playlist")
        artists = rows(conn,
            "SELECT a.art_codigo id, TRIM(a.art_primeironome || ' ' || "
            "a.art_ultimonome) name, i.image_url img, p.apy_quantidade "
            "tracks, a.art_popularidade pop FROM apy_artistaplaylist p "
            "JOIN art_artista a ON a.art_codigo = p.apy_art_codigo "
            "AND a.coleta = p.coleta LEFT JOIN artists_images i "
            "ON i.art_codigo = a.art_codigo WHERE p.coleta = ? "
            "AND p.apy_ply_codigo = ? ORDER BY p.apy_quantidade DESC, "
            "a.art_popularidade DESC", (snap, playlist))
        for a in artists:
            a["cities"] = reach.get(a["id"], 1)
        local = sorted((a for a in artists if a["cities"] < len(index) / 4),
                       key=lambda a: (a["cities"], -a["tracks"],
                                      -(a["pop"] or 0)))[:6]
        tracks = rows(conn,
            "SELECT f.fai_codigo id, f.fai_nome name, i.image_url img, "
            f"f.fai_popularidade pop, {ARTISTS} FROM fxp_faixaplaylist x "
            "JOIN fai_faixa f ON f.fai_codigo = x.fxp_fai_codigo "
            "AND f.coleta = x.coleta LEFT JOIN faixas_images i "
            "ON i.fai_codigo = f.fai_codigo LEFT JOIN afx_artistafaixa ax "
            "ON ax.afx_fai_codigo = f.fai_codigo AND ax.coleta = f.coleta "
            "LEFT JOIN art_artista a ON a.art_codigo = ax.afx_art_codigo "
            "AND a.coleta = f.coleta WHERE x.coleta = ? "
            "AND x.fxp_ply_codigo = ? GROUP BY f.fai_codigo "
            "ORDER BY f.fai_popularidade DESC LIMIT 20", (snap, playlist))
        city["artists"] = len(artists)
        details[city["id"]] = {"artists": artists[:20], "local": local,
                               "tracks": tracks}
    return index, details


def compare(conn, old, new):
    """Then vs now: track profile, release age, genres, arrivals and
    departures between the oldest and the newest snapshot."""
    profile = {r["coleta"]: r for r in rows(conn,
        "SELECT coleta, COUNT(*) tracks, AVG(fai_duracao) / 1000.0 seconds, "
        "AVG(fai_explicita) explicit, AVG(fai_popularidade) popularity "
        "FROM fai_faixa WHERE coleta IN (?, ?) GROUP BY coleta", (old, new))}
    buckets = {s: [0] * 7 for s in (old, new)}
    for coleta, age, n in conn.execute(
            "SELECT fa.coleta, CAST(SUBSTR(fa.coleta, 1, 4) AS INTEGER) - "
            "CAST(SUBSTR(b.alb_lancamento, 1, 4) AS INTEGER), COUNT(*) "
            "FROM fal_faixaalbum fa JOIN alb_album b ON b.alb_codigo = "
            "fa.fal_alb_codigo AND b.coleta = fa.coleta WHERE fa.coleta IN "
            "(?, ?) AND b.alb_lancamento IS NOT NULL GROUP BY 1, 2",
            (old, new)):
        if age is None:
            continue
        # Same year, 1, 2-3, 4-5, 6-10, 11-20, 20+
        i = next(i for i, top in enumerate((0, 1, 3, 5, 10, 20, 10 ** 6))
                 if age <= top)
        buckets[coleta][i] += n
    ages = {s: [n / (sum(b) or 1) for n in b] for s, b in buckets.items()}
    genres = rows(conn,
        "SELECT g.coleta, g.gen_nome name, COUNT(DISTINCT ag.age_art_codigo) "
        "artists FROM age_artistagenero ag JOIN gen_genero g ON g.gen_codigo "
        "= ag.age_gen_codigo AND g.coleta = ag.coleta JOIN "
        "apy_artistaplaylist p ON p.apy_art_codigo = ag.age_art_codigo "
        "AND p.coleta = ag.coleta WHERE ag.coleta IN (?, ?) "
        "GROUP BY g.coleta, g.gen_nome", (old, new))
    totals = {s: sum(g["artists"] for g in genres if g["coleta"] == s) or 1
              for s in (old, new)}
    share = {}
    for g in genres:
        share.setdefault(g["name"], {old: 0, new: 0})[g["coleta"]] = \
            g["artists"] / totals[g["coleta"]]
    top_genres = sorted(share.items(), key=lambda kv: -max(kv[1].values()))
    reach = rows(conn,
        "SELECT p.coleta, p.apy_art_codigo id, TRIM(a.art_primeironome || "
        "' ' || a.art_ultimonome) name, COUNT(DISTINCT p.apy_ply_codigo) "
        "playlists, i.image_url img FROM apy_artistaplaylist p JOIN "
        "art_artista a ON a.art_codigo = p.apy_art_codigo AND a.coleta = "
        "p.coleta LEFT JOIN artists_images i ON i.art_codigo = "
        "p.apy_art_codigo WHERE p.coleta IN (?, ?) GROUP BY p.coleta, "
        "p.apy_art_codigo ORDER BY playlists DESC", (old, new))
    ids = {s: {r["id"] for r in reach if r["coleta"] == s} for s in (old, new)}

    def moved(here, there):
        return [{k: r[k] for k in ("id", "name", "playlists", "img")}
                for r in reach if r["coleta"] == here
                and r["id"] not in ids[there]][:12]

    return {"old": old, "new": new, "profile": profile, "ages": ages,
            "genres": top_genres[:12], "arrived": moved(new, old),
            "gone": moved(old, new)}


def group(pairs):
    out = {}
    for key, value in pairs:
        out.setdefault(key, []).append(value)
    return out


def entities(conn, snap, other):
    """One JSON per artist, track and album of the snapshot, plus the lists
    of the pick pages and the search index. Everything is read in bulk and
    joined here: one query per item would take far too long."""
    def images(table, key):
        return dict(conn.execute(f"SELECT {key}, image_url FROM {table}"))
    art_img = images("artists_images", "art_codigo")
    fai_img = images("faixas_images", "fai_codigo")
    alb_img = images("albums_images", "alb_codigo")

    artists = {r["art_codigo"]: r for r in rows(conn,
        "SELECT * FROM art_artista WHERE coleta = ?", (snap,))}
    for a in artists.values():
        a["name"] = " ".join(filter(None, (a["art_primeironome"],
                                           a["art_ultimonome"]))).strip()
    previous = {code: [p, f] for code, p, f in conn.execute(
        "SELECT art_codigo, art_popularidade, art_seguidores FROM art_artista "
        "WHERE coleta = ?", (other,))} if other else {}
    tracks = {r["fai_codigo"]: r for r in rows(conn,
        "SELECT * FROM fai_faixa WHERE coleta = ?", (snap,))}
    albums = {r["alb_codigo"]: r for r in rows(conn,
        "SELECT * FROM alb_album WHERE coleta = ?", (snap,))}

    track_artists = group((f, a) for a, f in conn.execute(
        "SELECT afx_art_codigo, afx_fai_codigo FROM afx_artistafaixa "
        "WHERE coleta = ? ORDER BY afx_principal DESC", (snap,)))
    artist_tracks = group((a, f) for f, a_list in track_artists.items()
                          for a in a_list)
    track_album = dict(conn.execute(
        "SELECT fal_fai_codigo, fal_alb_codigo FROM fal_faixaalbum "
        "WHERE coleta = ?", (snap,)))
    album_tracks = group((b, f) for f, b in track_album.items())
    album_artists = group(conn.execute(
        "SELECT aal_alb_codigo, aal_art_codigo FROM aal_artistaalbum "
        "WHERE coleta = ?", (snap,)))
    artist_albums = group((a, b) for b, a_list in album_artists.items()
                          for a in a_list)
    genres = group(conn.execute(
        "SELECT DISTINCT ag.age_art_codigo, g.gen_nome FROM "
        "age_artistagenero ag JOIN gen_genero g ON g.gen_codigo = "
        "ag.age_gen_codigo AND g.coleta = ag.coleta WHERE ag.coleta = ?",
        (snap,)))
    artist_playlists = dict(conn.execute(
        "SELECT apy_art_codigo, COUNT(DISTINCT apy_ply_codigo) FROM "
        "apy_artistaplaylist WHERE coleta = ? GROUP BY apy_art_codigo",
        (snap,)))
    track_playlists = group(conn.execute(
        "SELECT x.fxp_fai_codigo, p.ply_nome FROM fxp_faixaplaylist x "
        "JOIN ply_playlist p ON p.ply_codigo = x.fxp_ply_codigo AND p.coleta "
        "= x.coleta WHERE x.coleta = ? ORDER BY p.ply_seguidores DESC",
        (snap,)))
    similar = group((a, (b, sim, src)) for a, b, sim, src in conn.execute(
        "SELECT aa_art_a_codigo, aa_art_b_codigo, aa_similaridade, aa_fonte "
        "FROM aa_artistaartista WHERE coleta = ?", (snap,)))
    cities = group((a, (name, region, country, listeners))
                   for a, name, region, country, listeners in conn.execute(
        "SELECT r.arc_art_codigo, c.cid_nome, c.cid_regiao, c.cid_pais, "
        "r.arc_ouvintes FROM arc_artistacidade r JOIN cid_cidade c ON "
        "c.cid_codigo = r.arc_cid_codigo AND c.coleta = r.coleta "
        "WHERE r.coleta = ?", (snap,)))
    chart = group((f, (kind, pos, streams, total))
                  for f, kind, pos, streams, total in conn.execute(
        "SELECT chr_fai_codigo, chr_tipo, chr_posicao, chr_streams, "
        "chr_total_streams FROM chr_chart WHERE chr_coleta = ?", (snap,)))

    def score(value):
        return value if value is not None else -1

    def names(codes):
        return ", ".join(artists[a]["name"] for a in codes if a in artists)

    def track_row(f):
        t = tracks[f]
        return {"id": f, "name": t["fai_nome"], "img": fai_img.get(f),
                "pop": t["fai_popularidade"], "dur": t["fai_duracao"],
                "artists": names(track_artists.get(f, [])),
                "playlists": len(track_playlists.get(f, []))}

    def artist_row(a):
        return {"id": a, "name": artists[a]["name"], "img": art_img.get(a),
                "followers": artists[a]["art_seguidores"]}

    def album_row(b):
        r = albums[b]
        return {"id": b, "name": r["alb_nome"], "img": alb_img.get(b),
                "type": r["alb_tipo"],
                "year": (r["alb_lancamento"] or "")[:4]}

    out = {"artist": {}, "track": {}, "album": {}}
    # Album pages: albums of the tracks, and the discography the artist
    # pages show (the full 2023 discographies have 100k+ albums)
    page_albums = {b for b in album_tracks if b in albums}
    for code, a in artists.items():
        mine = sorted((f for f in artist_tracks.get(code, []) if f in tracks),
                      key=lambda f: -score(tracks[f]["fai_popularidade"]))
        discography = sorted(
            (b for b in artist_albums.get(code, []) if b in albums),
            key=lambda b: albums[b]["alb_lancamento"] or "", reverse=True)[:12]
        page_albums.update(discography)
        alike = sorted((s for s in similar.get(code, []) if s[0] in artists),
                       key=lambda s: (-score(s[1]),
                                      -score(artists[s[0]]["art_popularidade"])))
        where = sorted(cities.get(code, []), key=lambda c: -(c[3] or 0))[:10]
        out["artist"][code] = {
            "name": a["name"], "img": art_img.get(code),
            "followers": a["art_seguidores"], "pop": a["art_popularidade"],
            "listeners": a["art_ouvintes"], "prev": previous.get(code),
            "genres": [g.title() for g in genres.get(code, [])],
            "playlists": artist_playlists.get(code, 0),
            "tracks": [track_row(f) for f in mine[:10]],
            "albums": [album_row(b) for b in discography],
            "similar": [{**artist_row(b), "sim": sim}
                        for b, sim, _ in alike[:12]],
            "similar_source": alike[0][2] if alike else None,
            "cities": [{"name": n, "region": r, "country": c, "listeners": n_}
                       for n, r, c, n_ in where],
        }
    for f, t in tracks.items():
        b = track_album.get(f)
        out["track"][f] = {
            "name": t["fai_nome"], "img": fai_img.get(f),
            "pop": t["fai_popularidade"], "dur": t["fai_duracao"],
            "explicit": bool(t["fai_explicita"]), "plays": t["fai_reproducoes"],
            "artists": [artist_row(a) for a in track_artists.get(f, [])
                        if a in artists],
            "album": album_row(b) if b in albums else None,
            "chart": {k: {"pos": p, "streams": s, "total": n}
                      for k, p, s, n in chart.get(f, [])},
            "cities": [n.removeprefix("Viral ").removesuffix(" BR")
                       for n in track_playlists.get(f, [])],
        }
    for b in page_albums:
        r = albums[b]
        out["album"][b] = {
            **album_row(b), "date": r["alb_lancamento"],
            "count": r["alb_qtdmusicas"], "pop": r["alb_popularidade"],
            "artists": [artist_row(a) for a in album_artists.get(b, [])
                        if a in artists],
            "tracks": sorted((track_row(f) for f in album_tracks.get(b, [])
                              if f in tracks), key=lambda t: -score(t["pop"])),
        }

    with_tracks = sorted((a for a in artists if a in artist_tracks),
                         key=lambda a: -score(artists[a]["art_popularidade"]))
    track_list = sorted(tracks,
                        key=lambda f: -score(tracks[f]["fai_popularidade"]))
    album_list = sorted((b for b in album_tracks if b in albums),
                        key=lambda b: -score(albums[b]["alb_popularidade"]))
    lists = {
        "artists": [artist_row(a) for a in with_tracks[:24]],
        "tracks": [track_row(f) for f in track_list[:30]],
        "albums": [album_row(b) for b in album_list
                   if albums[b]["alb_tipo"] == "album"][:24],
    }
    # Search index as compact arrays, most popular first; images without
    # the common prefix (app.js adds it back)
    def short(url):
        return url.removeprefix(IMAGE_PREFIX) if url else None
    search = {
        "artists": [[a, artists[a]["name"], short(art_img.get(a)),
                     artists[a]["art_seguidores"]] for a in sorted(
            artists, key=lambda a: -score(artists[a]["art_popularidade"]))],
        "tracks": [[f, tracks[f]["fai_nome"], short(fai_img.get(f)),
                    names(track_artists.get(f, [])), tracks[f]["fai_duracao"]]
                   for f in track_list],
        "albums": [[b, albums[b]["alb_nome"], short(alb_img.get(b)),
                    albums[b]["alb_tipo"],
                    (albums[b]["alb_lancamento"] or "")[:4]]
                   for b in album_list],
    }
    return out, lists, search


def write_json(name, payload):
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False,
                                       separators=(",", ":")),
                            encoding="utf-8")


def main():
    packed = SLIM if SLIM.exists() else ROOT / "data" / "spotify.db.gz"
    temp = Path(tempfile.mkdtemp()) / "spotify.db"
    with gzip.open(packed, "rb") as src, open(temp, "wb") as dst:
        shutil.copyfileobj(src, dst)
    conn = sqlite3.connect(temp)
    snaps = [s for (s,) in conn.execute(
        "SELECT col_codigo FROM col_coleta ORDER BY col_codigo")]
    OUT.mkdir(exist_ok=True)
    data = {"snapshots": snaps,
            "home": {s: home(conn, s) for s in snaps},
            "climbers": climbers(conn, snaps[0], snaps[-1])
            if len(snaps) > 1 else []}
    write_json("home.json", data)
    if len(snaps) > 1:
        write_json("compare.json", compare(conn, snaps[0], snaps[-1]))
    for s in snaps:
        write_json(f"charts-{s}.json", charts(conn, s))
        index, details = cities(conn, s)
        write_json(f"cities-{s}.json", index)
        (OUT / "city" / s).mkdir(parents=True, exist_ok=True)
        for code, detail in details.items():
            write_json(f"city/{s}/{code}.json", detail)
        other = next((o for o in snaps if o != s), None)
        pages, lists, search = entities(conn, s, other)
        write_json(f"lists-{s}.json", lists)
        write_json(f"search-{s}.json", search)
        for kind, items in pages.items():
            (OUT / kind / s).mkdir(parents=True, exist_ok=True)
            for code, item in items.items():
                write_json(f"{kind}/{s}/{code}.json", item)
        print(f"{s}: " + ", ".join(f"{len(v)} {k}s" for k, v in pages.items()))
    conn.close()
    shutil.rmtree(temp.parent)
    for f in SRC.iterdir():
        shutil.copy2(f, OUT / f.name)
    # Version the assets so browsers do not keep an old app.js after a deploy
    page = (OUT / "index.html").read_text(encoding="utf-8")
    for asset in ("app.js", "styles.css"):
        version = hashlib.md5((OUT / asset).read_bytes()).hexdigest()[:8]
        page = page.replace(f'"{asset}"', f'"{asset}?v={version}"')
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    (OUT / "404.html").write_text(NOT_FOUND, encoding="utf-8")
    sizes = {p.name: p.stat().st_size // 1024 for p in OUT.glob("*.json")}
    print(f"Static site: snapshots {snaps}, JSON KB {sizes}")


if __name__ == "__main__":
    main()
