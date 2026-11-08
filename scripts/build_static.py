"""Build the fast Vue frontend into _site/ (the root of the GitHub Pages site).

The pages that everyone opens first (home, Top 200, cities) come as JSON
computed here, so they show up at once; each city has its own small file. Artist, album, track, search and
"then vs now" query the database in the browser with sql.js, using the
gzipped copy that build_pages.py puts in _site/streamlit/data/.

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
DB = ROOT / "data" / "spotify.db"
OUT = ROOT / "_site"
SRC = ROOT / "static_site"

# GitHub Pages serves only the root 404.html: send Streamlit routes
# (/streamlit/artist) to the Streamlit app, anything else to the home
NOT_FOUND = r"""<!doctype html><meta charset="utf-8"><script>
const m = location.pathname.match(/^(.*?\/)streamlit\/([^/]+)\/?$/);
location.replace(m ? m[1] + "streamlit/?page=" + m[2] : location.pathname.replace(/\/streamlit\/.*$|\/[^/]*$/, "/"));
</script>"""

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


def write_json(name, payload):
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False,
                                       separators=(",", ":")),
                            encoding="utf-8")


def main():
    source = DB
    temp = None
    if not source.exists():
        temp = Path(tempfile.mkdtemp()) / "spotify.db"
        with gzip.open(ROOT / "data" / "spotify.db.gz", "rb") as src, \
                open(temp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        source = temp
    conn = sqlite3.connect(source)
    snaps = [s for (s,) in conn.execute(
        "SELECT col_codigo FROM col_coleta ORDER BY col_codigo")]
    OUT.mkdir(exist_ok=True)
    data = {"snapshots": snaps,
            "home": {s: home(conn, s) for s in snaps},
            "climbers": climbers(conn, snaps[0], snaps[-1])
            if len(snaps) > 1 else []}
    write_json("home.json", data)
    for s in snaps:
        write_json(f"charts-{s}.json", charts(conn, s))
        index, details = cities(conn, s)
        write_json(f"cities-{s}.json", index)
        (OUT / "city" / s).mkdir(parents=True, exist_ok=True)
        for code, detail in details.items():
            write_json(f"city/{s}/{code}.json", detail)
    conn.close()
    if temp:
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
