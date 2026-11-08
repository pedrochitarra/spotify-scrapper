"""Shared look and data helpers for the Streamlit pages.

The pages draw their content as HTML (cards, lists, heroes) instead of the
default Streamlit widgets. Clickable cards are a transparent st.button over
the HTML: in stlite (Python in the browser) following a real link reloads
the page and restarts Python, a button only reruns the script.
"""
import gzip
import html
import shutil
import sqlite3

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.db import DB_PATH, LEGACY_COLETA

PLACEHOLDER_IMAGE = ("https://i.scdn.co/image/"
                     "ab6761610000517458efbed422ab46484466822b")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800;900&display=swap');
:root {
  --bg: #07140e; --surface: #10251a; --surface-2: #173524; --surface-3: #235038;
  --border: rgba(255,255,255,.07); --text: #f5f5f5; --muted: #a3a3a8;
  --green: #1ed760; --amber: #f5a623; --red: #f15e6c; --blue: #509bf5;
}
body, .stApp, .stMarkdown, .stHtml, button p, input, label p {
  font-family: 'Figtree', system-ui, sans-serif !important; }
.stApp { background: radial-gradient(1100px 520px at 50% -260px,
           rgba(30,215,96,.36), transparent 70%),
           radial-gradient(800px 500px at 100% 35%, rgba(30,215,96,.10), transparent 70%), var(--bg); }
.block-container { max-width: 1160px; padding-top: 4.2rem; }
header[data-testid="stHeader"] { background: rgba(11,11,12,.85);
  backdrop-filter: blur(10px); }
a, a:visited { color: inherit; text-decoration: none; }
h1, h2, h3 { font-family: 'Figtree', sans-serif !important; font-weight: 800 !important;
  letter-spacing: -.02em; }

.sx-title { font-weight: 900; font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1.05;
  letter-spacing: -.03em; margin: 0; }
.sx-sub { color: var(--muted); margin: 6px 0 22px; font-size: 1.02rem; }
.sx-section { font-weight: 800; font-size: 1.45rem; letter-spacing: -.02em;
  margin: 34px 0 14px; display: flex; align-items: baseline; gap: 10px; }
.sx-section small { color: var(--muted); font-weight: 500; font-size: .85rem; }
.sx-grid { display: grid; gap: 14px; }
.g2 { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.g4 { grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.card { background: linear-gradient(145deg, rgba(30,215,96,.12), var(--surface-2) 42%, var(--surface));
  border: 1px solid var(--border); border-radius: 16px; padding: 18px; color: var(--text); }
.stat .v { font-weight: 900; font-size: 2.3rem; line-height: 1; letter-spacing: -.03em; }
.stat .l { color: var(--muted); font-size: .78rem; text-transform: uppercase;
  letter-spacing: .08em; font-weight: 700; margin-bottom: 8px; }
.stat .d { font-size: .82rem; font-weight: 700; margin-top: 8px; color: var(--muted); }
.up { color: var(--green) !important; } .down { color: var(--red) !important; }
.note { color: var(--muted); border: 1px dashed var(--border); border-radius: 12px;
  padding: 12px 14px; font-size: .9rem; }
.badge { display: inline-block; border-radius: 99px; padding: 2px 10px; font-size: .72rem;
  font-weight: 800; letter-spacing: .04em; text-transform: uppercase;
  background: rgba(30,215,96,.14); color: var(--green); border: 1px solid rgba(30,215,96,.35); }
.badge.old { background: rgba(245,166,35,.14); color: var(--amber);
  border-color: rgba(245,166,35,.35); }
.chip { display: inline-block; background: var(--surface-3); border: 1px solid var(--border);
  border-radius: 99px; padding: 4px 12px; margin: 0 6px 6px 0; font-size: .82rem; font-weight: 600; }
.city-ranking { overflow: hidden; border: 1px solid var(--border); border-radius: 16px;
  background: linear-gradient(145deg, rgba(30,215,96,.12), var(--surface)); }
.city-rank { display: grid; grid-template-columns: 44px minmax(0,1fr) auto 70px;
  gap: 14px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.city-rank:last-child { border-bottom: 0; }
.city-rank:hover { background: rgba(30,215,96,.10); }
.city-pos { color: var(--green); font-size: 1.15rem; font-weight: 900; text-align: center; }
.city-name { font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.city-tracks { color: var(--muted); font-size: .82rem; }
.city-rank b { color: var(--green); text-align: right; }

/* hero */
.hero { display: flex; gap: 28px; align-items: flex-end; padding: 28px;
  border-radius: 20px; border: 1px solid var(--border);
  background: radial-gradient(700px 320px at 0% 0%, rgba(30,215,96,.40), transparent 70%),
              linear-gradient(180deg, var(--surface-2), var(--surface)); }
.hero img { width: 200px; height: 200px; object-fit: cover; border-radius: 10px;
  box-shadow: 0 18px 48px rgba(0,0,0,.6); flex-shrink: 0; }
.hero.round img { border-radius: 50%; }
.hero .kind { text-transform: uppercase; font-size: .75rem; font-weight: 800;
  letter-spacing: .12em; color: var(--muted); }
.hero .name { font-weight: 900; font-size: clamp(2rem, 6vw, 4.2rem); line-height: 1;
  letter-spacing: -.04em; margin: 6px 0 10px; }
.hero .meta { color: var(--muted); font-weight: 500; }
.hero .meta b { color: var(--text); }
.hero-stats { display: flex; gap: 28px; margin-top: 16px; flex-wrap: wrap; }
.hero-stats .v { font-weight: 900; font-size: 1.6rem; line-height: 1; }
.hero-stats .l { color: var(--muted); font-size: .72rem; text-transform: uppercase;
  letter-spacing: .08em; font-weight: 700; margin-top: 4px; }

/* list rows (tracks, rankings) */
.row { display: grid; grid-template-columns: 34px 48px minmax(0,1fr) auto; gap: 14px;
  align-items: center; padding: 8px 12px; border-radius: 10px; color: var(--text); }
.row .n { color: var(--muted); font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
.row img { width: 48px; height: 48px; border-radius: 6px; object-fit: cover; }
.row.round img { border-radius: 50%; }
.row .t { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row .s { color: var(--muted); font-size: .86rem; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.row .r { color: var(--muted); font-size: .88rem; font-weight: 600; text-align: right;
  font-variant-numeric: tabular-nums; }
.row .r b { color: var(--text); }
.pop { display: inline-block; width: 64px; height: 5px; border-radius: 99px;
  background: var(--surface-3); vertical-align: middle; margin-left: 8px; overflow: hidden; }
.pop i { display: block; height: 100%; background: var(--green); }

/* cover / artist tiles */
.tile { padding: 14px; border-radius: 14px; background: var(--surface);
  border: 1px solid var(--border); color: var(--text); height: 100%; }
.tile img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0,0,0,.45); }
.tile.round img { border-radius: 50%; }
.tile .t { font-weight: 700; margin-top: 12px; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.tile .s { color: var(--muted); font-size: .84rem; margin-top: 2px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.podium { position: relative; }
.podium .rank { position: absolute; top: 22px; left: 22px; background: var(--green);
  color: #000; font-weight: 900; border-radius: 8px; padding: 2px 10px; font-size: 1.1rem; }

/* clickable blocks: transparent button on top */
div[class*="st-key-lnk_"] { position: relative; gap: 0 !important; }
div[class*="st-key-lnk_"] div[data-testid="stElementContainer"]:has(.stButton) {
  position: absolute !important; inset: 0; z-index: 3; margin: 0 !important; width: 100% !important; }
div[class*="st-key-lnk_"] .stButton, div[class*="st-key-lnk_"] .stButton button {
  width: 100%; height: 100%; }
div[class*="st-key-lnk_"] .stButton button { opacity: 0; cursor: pointer; }
div[class*="st-key-lnk_"] .row, div[class*="st-key-lnk_"] .tile {
  transition: background .15s, transform .15s, border-color .15s; }
div[class*="st-key-lnk_"]:hover .row { background: var(--surface-2); }
div[class*="st-key-lnk_"]:hover .tile { background: var(--surface-2); transform: translateY(-3px);
  border-color: rgba(30,215,96,.35); }

/* widgets */
div[data-testid="stTextInput"] input { border-radius: 99px; padding: 12px 20px;
  background: var(--surface-2); }
div[data-testid="stSegmentedControl"] button { border-radius: 99px !important; }
div[data-testid="stVegaLiteChart"] { background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 12px; }
iframe { border-radius: 12px; }
.sx-foot { text-align: center; color: var(--muted); font-size: .8rem; margin-top: 48px; }

@media (max-width: 700px) {
  .hero { flex-direction: column; align-items: flex-start; padding: 20px; }
  .hero img { width: 150px; height: 150px; }
  .row { grid-template-columns: 24px 42px minmax(0,1fr); }
  .row .r { display: none; }
  .row img { width: 42px; height: 42px; }
}
</style>
"""


def inject_css():
    st.html(CSS)
    alt.themes.register("showcase", _altair_theme)
    alt.themes.enable("showcase")


def _altair_theme():
    return {"config": {
        "background": "transparent",
        "font": "Figtree",
        "view": {"stroke": None},
        "axis": {"labelColor": "#a3a3a8", "titleColor": "#a3a3a8",
                 "gridColor": "#ffffff14", "domainColor": "#ffffff22",
                 "tickColor": "#ffffff22", "labelFontSize": 12,
                 "titleFontWeight": 600},
        "legend": {"labelColor": "#f5f5f5", "titleColor": "#a3a3a8"},
        "range": {"category": ["#1ed760", "#f5a623", "#509bf5", "#f15e6c"]},
    }}


# --- data -------------------------------------------------------------------

@st.cache_resource
def _connection() -> sqlite3.Connection:
    packed = DB_PATH.with_name(DB_PATH.name + ".gz")
    if not DB_PATH.exists() and packed.exists():
        # The web build (GitHub Pages / stlite) ships the database gzipped
        with st.spinner("Unpacking the database…"):
            with gzip.open(packed, "rb") as src, open(DB_PATH, "wb") as dst:
                shutil.copyfileobj(src, dst)
    if not DB_PATH.exists():
        st.error(f"Database not found at `{DB_PATH}`. Run `python main.py` "
                 "first.")
        st.stop()
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True,
                           check_same_thread=False)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a read-only query. On failure show the error and stop the page."""
    try:
        return pd.read_sql_query(sql, _connection(), params=params)
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        st.error(f"Database query failed: {e}")
        st.stop()


def coletas() -> list:
    df = query("SELECT col_codigo FROM col_coleta ORDER BY col_codigo DESC")
    return df["col_codigo"].tolist() or [LEGACY_COLETA]


def coleta() -> str:
    """Selected snapshot: ?snap= in the URL, else the most recent."""
    options = coletas()
    wanted = st.query_params.get("snap")
    return wanted if wanted in options else options[0]


def snapshot_switch():
    """Pill switch between snapshots, kept in the URL (?snap=)."""
    options = coletas()
    current = coleta()
    if len(options) < 2:
        return current
    choice = st.segmented_control(
        "Snapshot", sorted(options), default=current, key="snap_switch",
        format_func=coleta_label, label_visibility="collapsed")
    if choice and choice != current:
        st.query_params["snap"] = choice
        st.rerun()
    return current


def other_coleta(current: str):
    others = [c for c in coletas() if c != current]
    return others[0] if others else None


def coleta_label(value: str) -> str:
    if "-" not in str(value):
        return str(value)
    year, month = value.split("-")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
              "Oct", "Nov", "Dec"]
    return f"{months[int(month) - 1]} {year}"


def coleta_badge(value: str) -> str:
    css = "badge old" if value == LEGACY_COLETA else "badge"
    return f"<span class='{css}'>{coleta_label(value)}</span>"


# --- formatting -------------------------------------------------------------

def esc(text) -> str:
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) \
        else html.escape(str(text))


def artist_name(first, last) -> str:
    return f"{first} {last}".strip() if last else str(first)


def img(url) -> str:
    return esc(url) if isinstance(url, str) and url else PLACEHOLDER_IMAGE


def number(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(value) >= size:
            return f"{value / size:.1f}{unit}".replace(".0", "")
    return f"{value:,.0f}"


def delta(now, before):
    if now is None or before is None or pd.isna(now) or pd.isna(before):
        return None
    return float(now) - float(before)


def delta_html(change, fmt=number, suffix="") -> str:
    if change is None:
        return ""
    css = "up" if change > 0 else "down" if change < 0 else ""
    arrow = "▲" if change > 0 else "▼" if change < 0 else "•"
    return f"<span class='{css}'>{arrow} {fmt(abs(change))}{suffix}</span>"


def pop_bar(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{int(value)}<span class='pop'><i style='width:{int(value)}%'></i></span>"


def duration(ms) -> str:
    if ms is None or pd.isna(ms):
        return ""
    minutes, seconds = divmod(int(ms) // 1000, 60)
    return f"{minutes}:{seconds:02d}"


# --- building blocks ----------------------------------------------------------

def title(text: str, sub: str = ""):
    st.html(f"<p class='sx-title'>{text}</p>"
            + (f"<p class='sx-sub'>{sub}</p>" if sub else ""))


def section(text: str, small: str = ""):
    st.html(f"<div class='sx-section'>{text}"
            + (f"<small>{small}</small>" if small else "") + "</div>")


def note(text: str):
    st.html(f"<div class='note'>{text}</div>")


def stats(items: list):
    """items: [(label, value, delta_html)]"""
    cards = "".join(
        f"<div class='card stat'><div class='l'>{label}</div>"
        f"<div class='v'>{value}</div>"
        + (f"<div class='d'>{d}</div>" if d else "") + "</div>"
        for label, value, d in items)
    st.html(f"<div class='sx-grid g4'>{cards}</div>")


def hero(image, kind: str, name: str, meta: str = "", hero_stats=None,
         round_image: bool = False):
    numbers = "".join(f"<div><div class='v'>{v}</div><div class='l'>{l}</div>"
                      f"</div>" for l, v in (hero_stats or []))
    st.html(
        f"<div class='hero{' round' if round_image else ''}'>"
        f"<img src='{img(image)}' alt=''><div style='min-width:0'>"
        f"<div class='kind'>{kind}</div><div class='name'>{esc(name)}</div>"
        f"<div class='meta'>{meta}</div>"
        + (f"<div class='hero-stats'>{numbers}</div>" if numbers else "")
        + "</div></div>")


def chips(values) -> str:
    return "".join(f"<span class='chip'>{esc(v)}</span>" for v in values)


def row_html(n, image, title_text, sub, right="", round_image=False) -> str:
    return (f"<div class='row{' round' if round_image else ''}'>"
            f"<div class='n'>{n}</div><img src='{img(image)}' alt=''>"
            f"<div style='min-width:0'><div class='t'>{esc(title_text)}</div>"
            f"<div class='s'>{sub}</div></div><div class='r'>{right}</div></div>")


def tile_html(image, title_text, sub, round_image=False, rank=None) -> str:
    badge = f"<span class='rank'>#{rank}</span>" if rank else ""
    return (f"<div class='tile{' round' if round_image else ''}"
            f"{' podium' if rank else ''}'>{badge}<img src='{img(image)}' alt=''>"
            f"<div class='t'>{esc(title_text)}</div><div class='s'>{sub}</div>"
            f"</div>")


def link(key: str, block: str, page: str = None, **params):
    """Draw an HTML block and make all of it clickable: opens page with
    params in the URL (the snapshot goes along)."""
    with st.container(key=f"lnk_{key}"):
        st.html(block)
        if st.button("Open", key=f"btn_{key}"):
            params = {"snap": coleta(), **params}
            st.switch_page(f"pages/{page}.py", query_params=params)


def tiles(df: pd.DataFrame, key: str, page: str, id_col: str, make,
          columns: int = 6):
    """Grid of clickable tiles; make(row) -> html."""
    rows = list(df.itertuples(index=False))
    for start in range(0, len(rows), columns):
        cols = st.columns(columns)
        for col, row in zip(cols, rows[start:start + columns]):
            with col:
                link(f"{key}_{getattr(row, id_col)}", make(row), page,
                     id=getattr(row, id_col))


def rows(df: pd.DataFrame, key: str, page: str, id_col: str, make):
    """Vertical list of clickable rows; make(index, row) -> html."""
    for i, row in enumerate(df.itertuples(index=False), 1):
        link(f"{key}_{i}_{getattr(row, id_col)}", make(i, row), page,
             id=getattr(row, id_col))


def spotify_embed(kind: str, item_id: str, height: int = 152):
    """Official Spotify embed player (30s previews without login)."""
    components.iframe(f"https://open.spotify.com/embed/{kind}/{item_id}"
                      f"?utm_source=generator&theme=0", height=height)


def selected_id():
    return st.query_params.get("id")
