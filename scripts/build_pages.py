"""Build _site/ for GitHub Pages: the app runs in the browser with stlite
(Streamlit + Pyodide), so the site is only static files.

- index.html loads stlite and mounts the app with the files in FILES
- the database goes as a slimmed, gzipped copy (data/spotify.db.gz); the app
  unpacks it on start
- 404.html is a copy of index.html so page routes open the app

Output goes to _site/streamlit/; the fast Vue site (build_static.py) is the
root of the site.

Usage: python scripts/build_pages.py   (then: python -m http.server -d _site)
"""
import gzip
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site" / "streamlit"
STLITE = "1.12.0"
DB = ROOT / "data" / "spotify.db"
WEB_DB = "data/spotify.db.gz"


def _py(pattern: str) -> list:
    return sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern))


FILES = ["frontend.py", *_py("pages/*.py"), *_py("src/*.py"),
         *_py("src/utils/*.py"), WEB_DB]

# Same theme as .streamlit/config.toml (stlite takes the config via mount)
CONFIG = {
    "theme.base": "dark",
    "theme.primaryColor": "#1ed760",
    "theme.backgroundColor": "#121212",
    "theme.secondaryBackgroundColor": "#1f1f1f",
    "theme.textColor": "#f2f2f2",
    "client.toolbarMode": "viewer",
}

INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#121212">
  <title>Spotify Showcase</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎧</text></svg>">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@__STLITE__/build/stlite.css">
  <style>
    html, body { margin: 0; background: #121212; color: #f2f2f2; font-family: system-ui, sans-serif; }
    #loading { position: fixed; inset: 0; display: grid; place-items: center; text-align: center; padding: 16px; }
    #loading .bars { display: flex; gap: 6px; justify-content: center; height: 48px; align-items: flex-end; }
    #loading .bars span { width: 8px; background: #1ed760; border-radius: 4px; animation: eq 1s ease-in-out infinite; }
    #loading .bars span:nth-child(2) { animation-delay: .2s; }
    #loading .bars span:nth-child(3) { animation-delay: .4s; }
    #loading .bars span:nth-child(4) { animation-delay: .6s; }
    #loading p { color: #a7a7a7; margin-top: 16px; }
    @keyframes eq { 0%, 100% { height: 12px; } 50% { height: 48px; } }
  </style>
</head>
<body>
  <div id="loading"><div>
    <div class="bars"><span></span><span></span><span></span><span></span></div>
    <p>Loading Spotify Showcase…<br><small>Python runs in your browser; the first visit takes about 30 seconds.</small></p>
  </div></div>
  <div id="root"></div>
  <script type="module">
    import { mount } from "https://cdn.jsdelivr.net/npm/@stlite/browser@__STLITE__/build/stlite.js";
    // Site base (e.g. /spotify-scrapper/) so files load from any route
    // /repo/artist -> /repo/ and /repo/artist/ -> /repo/
    const base = location.pathname.replace(/[^/]*$/, "")
      .replace(/\\/(__ROUTES__)\\/$/, "/");
    const route = location.pathname.slice(base.length).replace(/\/$/, "");
    if (route) {
      const q = new URLSearchParams(location.search);
      q.set("page", route);
      history.replaceState(null, "", base + "?" + q.toString());
    }
    const files = Object.fromEntries(__FILES__.map((f) => [f, { url: base + f }]));
    mount({
      requirements: ["pandas", "altair"],
      entrypoint: "frontend.py",
      files,
      streamlitConfig: __CONFIG__,
    }, document.getElementById("root"));
    new MutationObserver((_, obs) => {
      if (document.querySelector('[data-testid="stApp"]')) { document.getElementById("loading").remove(); obs.disconnect(); }
    }).observe(document.getElementById("root"), { childList: true, subtree: true });
  </script>
</body>
</html>
"""


def slim_database(target: Path):
    """Copy of the database without what the app does not show: unique
    indexes used only by the scraper, and the full discography of 2023
    artists that have no track in the playlists."""
    source = DB
    tmp = None
    if not source.exists() and source.with_suffix(".db.gz").exists():
        tmp = Path(tempfile.mkdtemp()) / "spotify.db"
        with gzip.open(source.with_suffix(".db.gz"), "rb") as f, \
                open(tmp, "wb") as out:
            shutil.copyfileobj(f, out)
        source = tmp
    if not source.exists():
        sys.exit(f"Database not found: {DB}")

    work = target.with_suffix("")
    shutil.copy2(source, work)
    conn = sqlite3.connect(work)
    conn.execute(
        "DELETE FROM aal_artistaalbum WHERE coleta = '2023-11' AND "
        "aal_art_codigo NOT IN (SELECT afx_art_codigo FROM afx_artistafaixa "
        "WHERE coleta = '2023-11')")
    conn.execute(
        "DELETE FROM alb_album WHERE NOT EXISTS (SELECT 1 FROM "
        "aal_artistaalbum a WHERE a.aal_alb_codigo = alb_album.alb_codigo "
        "AND a.coleta = alb_album.coleta) AND NOT EXISTS (SELECT 1 FROM "
        "fal_faixaalbum f WHERE f.fal_alb_codigo = alb_album.alb_codigo "
        "AND f.coleta = alb_album.coleta)")
    conn.execute("DELETE FROM albums_images WHERE alb_codigo NOT IN "
                 "(SELECT alb_codigo FROM alb_album)")
    # Unique indexes only matter for the scraper's upserts
    for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND name LIKE 'ux_%'").fetchall():
        conn.execute(f"DROP INDEX {name}")
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    with open(work, "rb") as f, gzip.open(target, "wb", compresslevel=9) as g:
        shutil.copyfileobj(f, g)
    print(f"Database: {work.stat().st_size / 1e6:.1f} MB, "
          f"gzipped {target.stat().st_size / 1e6:.1f} MB")
    work.unlink()
    if tmp:
        shutil.rmtree(tmp.parent)


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    for f in FILES:
        (SITE / f).parent.mkdir(parents=True, exist_ok=True)
        if f == WEB_DB:
            slim_database(SITE / f)
        else:
            shutil.copy2(ROOT / f, SITE / f)
    html = (INDEX.replace("__STLITE__", STLITE)
            .replace("__FILES__", json.dumps(FILES))
            .replace("__ROUTES__", "|".join(
                Path(f).stem for f in FILES if f.startswith("pages/")))
            .replace("__CONFIG__", json.dumps(CONFIG)))
    (SITE / "index.html").write_text(html, encoding="utf-8")
    (SITE / "404.html").write_text(html, encoding="utf-8")
    total = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
    print(f"{len(FILES)} files, {total / 1e6:.1f} MB in {SITE}")


if __name__ == "__main__":
    main()
