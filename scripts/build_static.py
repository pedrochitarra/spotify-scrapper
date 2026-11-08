"""Build the fast public frontend from the local SQLite snapshot."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "spotify.db"
OUT = ROOT / "_site"

def main():
    conn = sqlite3.connect(DB)
    snap = conn.execute("select max(col_codigo) from col_coleta").fetchone()[0]
    stats = dict(conn.execute("select 'artists',count(*) from art_artista where coleta=? union all select 'tracks',count(*) from fai_faixa where coleta=? union all select 'albums',count(*) from alb_album where coleta=? union all select 'playlists',count(*) from ply_playlist where coleta=?", (snap, snap, snap, snap)).fetchall())
    cities = []
    for code, name in conn.execute("select cid_codigo,cid_nome from cid_cidade where coleta=? order by cid_nome", (snap,)):
        artists = [{"name": a, "score": score, "tracks": tracks} for a, score, tracks in conn.execute("select lfm_artista,lfm_score,lfm_faixas from lfm_artist_city_score where coleta=? and cid_codigo=? order by lfm_score desc limit 25", (snap, code))]
        cities.append({"id": code, "name": name, "artists": artists})
    payload = {"snapshot": snap, "stats": stats, "cities": cities}
    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (OUT / "index.html").write_text((ROOT / "static_site" / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "app.js").write_text((ROOT / "static_site" / "app.js").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "styles.css").write_text((ROOT / "static_site" / "styles.css").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Static site: {len(cities)} cities, snapshot {snap}")

if __name__ == "__main__": main()
