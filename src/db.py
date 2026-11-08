"""SQLite database access and schema migration.

Every data table has a ``coleta`` column (``YYYY-MM``) that identifies the
scraping run the row belongs to, so data from different years can live side
by side and be compared.
"""
import logging
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "spotify.db"
LEGACY_COLETA = "2023-11"

log = logging.getLogger(__name__)

# table -> columns that identify a row inside a coleta
TABLE_KEYS = {
    "ply_playlist": ["ply_codigo"],
    "fai_faixa": ["fai_codigo"],
    "alb_album": ["alb_codigo"],
    "art_artista": ["art_codigo"],
    "gen_genero": ["gen_nome"],
    "cid_cidade": ["cid_nome", "cid_pais", "cid_regiao"],
    "soc_redesocial": ["soc_art_codigo", "soc_tipo"],
    "fxp_faixaplaylist": ["fxp_fai_codigo", "fxp_ply_codigo"],
    "afx_artistafaixa": ["afx_art_codigo", "afx_fai_codigo"],
    "fal_faixaalbum": ["fal_fai_codigo", "fal_alb_codigo"],
    "aal_artistaalbum": ["aal_art_codigo", "aal_alb_codigo"],
    "apy_artistaplaylist": ["apy_art_codigo", "apy_ply_codigo"],
    "age_artistagenero": ["age_art_codigo", "age_gen_codigo"],
    "arc_artistacidade": ["arc_art_codigo", "arc_cid_codigo"],
    "aa_artistaartista": ["aa_art_a_codigo", "aa_art_b_codigo"],
}

IMAGE_TABLES = {
    "artists_images": "art_codigo",
    "albums_images": "alb_codigo",
    "playlists_images": "ply_codigo",
    "faixas_images": "fai_codigo",
}

NEW_TABLES = """
CREATE TABLE IF NOT EXISTS chr_chart (
    chr_coleta TEXT NOT NULL,
    chr_tipo TEXT NOT NULL,          -- 'daily' | 'weekly'
    chr_data TEXT,                   -- chart date as published
    chr_posicao INTEGER NOT NULL,
    chr_fai_codigo TEXT NOT NULL,
    chr_streams INTEGER,
    chr_total_streams INTEGER,
    PRIMARY KEY (chr_coleta, chr_tipo, chr_posicao)
);
CREATE TABLE IF NOT EXISTS col_coleta (
    col_codigo TEXT PRIMARY KEY,
    col_inicio TEXT,
    col_fim TEXT,
    col_observacao TEXT
);
-- Last.fm geo.gettoptracks ignores the city and returns the country chart,
-- so these per-city tables only held copies of it. Cities now come from the
-- Viral city playlists.
DROP TABLE IF EXISTS lfm_city_track_chart;
DROP TABLE IF EXISTS lfm_artist_city_score;
"""

EXTRA_COLUMNS = {
    "gen_genero": [("gen_codigo", "INTEGER")],
    "cid_cidade": [("cid_codigo", "INTEGER"), ("cid_latitude", "REAL"),
                   ("cid_longitude", "REAL")],
    "aa_artistaartista": [("aa_similaridade", "REAL"),
                          ("aa_fonte", "TEXT DEFAULT 'spotify'")],
}


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> list:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _dedupe(conn: sqlite3.Connection, table: str, keys: list):
    cols = ", ".join(keys)
    removed = conn.execute(
        f"DELETE FROM {table} WHERE rowid NOT IN "
        f"(SELECT MIN(rowid) FROM {table} GROUP BY {cols})").rowcount
    if removed:
        log.info("%s: removed %d duplicated rows", table, removed)


def migrate(conn: sqlite3.Connection):
    """Bring a database to the current schema. Safe to run many times."""
    for table, keys in TABLE_KEYS.items():
        cols = _columns(conn, table)
        if "coleta" not in cols:
            log.info("%s: adding coleta column", table)
            conn.execute(f"ALTER TABLE {table} ADD COLUMN coleta TEXT "
                         f"NOT NULL DEFAULT '{LEGACY_COLETA}'")
        for name, kind in EXTRA_COLUMNS.get(table, []):
            if name not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
        _dedupe(conn, table, keys + ["coleta"])
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{table} "
            f"ON {table} ({', '.join(keys + ['coleta'])})")

    # Genres and cities used to be referenced by their (unordered) row
    # number. Freeze that number in an explicit code column.
    conn.execute("UPDATE gen_genero SET gen_codigo = rowid "
                 "WHERE gen_codigo IS NULL")
    conn.execute("UPDATE cid_cidade SET cid_codigo = rowid "
                 "WHERE cid_codigo IS NULL")
    conn.execute("UPDATE aa_artistaartista SET aa_fonte = 'spotify' "
                 "WHERE aa_fonte IS NULL")

    for table, key in IMAGE_TABLES.items():
        _dedupe(conn, table, [key])
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{table} "
                     f"ON {table} ({key})")

    conn.executescript(NEW_TABLES)
    conn.execute(
        "INSERT OR IGNORE INTO col_coleta VALUES (?, ?, ?, ?)",
        (LEGACY_COLETA, "2023-11-01", "2023-11-11",
         "Original scrape: Spotify API + unofficial web player endpoints "
         "(plays, cities) + editorial playlists."))

    for idx in ("afx_artistafaixa(afx_fai_codigo)",
                "aal_artistaalbum(aal_alb_codigo)",
                "fxp_faixaplaylist(fxp_ply_codigo)",
                "fal_faixaalbum(fal_alb_codigo)"):
        name = "ix_" + idx.split("(")[0] + "_" + idx.split("(")[1][:-1]
        conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {idx}")
    conn.commit()


def upsert(conn: sqlite3.Connection, table: str, rows: list,
           conflict: list = None):
    """Insert dicts into table, replacing rows that hit a unique index."""
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    if conflict:
        updates = [c for c in cols if c not in conflict]
        action = (f"DO UPDATE SET " + ", ".join(
            f"{c} = excluded.{c}" for c in updates)) if updates else \
            "DO NOTHING"
        sql += f" ON CONFLICT ({', '.join(conflict)}) {action}"
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
