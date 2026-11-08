// Spotify Showcase, Vue version of the Streamlit app (same pages and look).
// Home, Top 200 and cities read JSON from build_static.py; the other pages
// query the SQLite database in the browser with sql.js.
const { createApp, reactive, computed, watch, ref } = Vue;

const DB_URL = "streamlit/data/spotify.db.gz";
const SQLJS = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/";
const PLACEHOLDER = "https://i.scdn.co/image/ab6761610000517458efbed422ab46484466822b";
const LEGACY = "2023-11";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// --- data ---------------------------------------------------------------------

const cache = {};
const json = (name) => (cache[name] ??= fetch(name).then((r) => {
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
  return r.json();
}));

let dbPromise = null;
function db() {
  return (dbPromise ??= (async () => {
    const [SQL, buf] = await Promise.all([
      initSqlJs({ locateFile: (f) => SQLJS + f }),
      fetch(DB_URL).then((r) => {
        if (!r.ok) throw new Error(`database: HTTP ${r.status}`);
        return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
      }),
    ]);
    return new SQL.Database(new Uint8Array(buf));
  })());
}

async function q(sql, params = []) {
  const stmt = (await db()).prepare(sql);
  stmt.bind(params);
  const out = [];
  while (stmt.step()) out.push(stmt.getAsObject());
  stmt.free();
  return out;
}

// Run an async loader for a page; state.data / state.err feed the template
function load(fn) {
  const state = reactive({ data: null, err: null });
  fn().then((d) => (state.data = d)).catch((e) => { console.error(e); state.err = String(e.message || e); });
  return state;
}

// --- formatting ---------------------------------------------------------------

const esc = (t) => (t == null ? "" : String(t).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`));
const img = (u) => u || PLACEHOLDER;
const name = (first, last) => (last ? `${first} ${last}`.trim() : String(first ?? ""));
function number(v) {
  if (v == null || Number.isNaN(+v)) return "—";
  v = +v;
  for (const [u, s] of [["B", 1e9], ["M", 1e6], ["K", 1e3]])
    if (Math.abs(v) >= s) return `${(v / s).toFixed(1).replace(".0", "")}${u}`;
  return Math.round(v).toLocaleString("en-US");
}
const thousands = (v) => (+v).toLocaleString("en-US");
function label(s) {
  if (!String(s).includes("-")) return String(s);
  const [y, m] = s.split("-");
  return `${MONTHS[+m - 1]} ${y}`;
}
const badge = (s) => `<span class="badge${s === LEGACY ? " old" : ""}">${label(s)}</span>`;
function delta(change, fmt = number, suffix = "") {
  if (change == null || Number.isNaN(change)) return "";
  const css = change > 0 ? "up" : change < 0 ? "down" : "";
  const arrow = change > 0 ? "▲" : change < 0 ? "▼" : "•";
  return `<span class="${css}">${arrow} ${fmt(Math.abs(change))}${suffix}</span>`;
}
const popBar = (v) => (v == null ? "" : `${v}<span class="pop"><i style="width:${v}%"></i></span>`);
function duration(ms) {
  if (ms == null) return "";
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
const pct = (v, d = 0) => `${(v * 100).toFixed(d)}%`;

// --- routing (hash: #/artist?id=...&snap=...) ---------------------------------

const route = reactive({ page: "overview", params: {}, key: "" });
function parse() {
  const [path, qs] = location.hash.replace(/^#\/?/, "").split("?");
  route.page = path || "overview";
  route.params = Object.fromEntries(new URLSearchParams(qs || ""));
  route.key = location.hash;
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", parse);
parse();

const snapshots = ref([]);
const snap = computed(() => (snapshots.value.includes(route.params.snap)
  ? route.params.snap : snapshots.value.at(-1)));
const other = computed(() => snapshots.value.find((s) => s !== snap.value));

function link(page, params = {}) {
  const p = { ...params };
  if (!("snap" in p) && route.params.snap) p.snap = route.params.snap;
  const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v != null && v !== "")).toString();
  return `#/${page}${qs ? "?" + qs : ""}`;
}

const helpers = { esc, img, number, thousands, label, badge, delta, popBar, duration, pct, link, name };

// --- building blocks ----------------------------------------------------------

const Loading = {
  props: { text: { default: "Loading…" } },
  template: `<div class="loading"><div><div class="eq"><span></span><span></span><span></span><span></span></div>{{ text }}</div></div>`,
};
const DbLoading = { components: { Loading }, template: `<Loading text="Loading the database (about 25 MB, only the first time)…"/>` };
const Err = { props: ["err"], template: `<div class="note">Something went wrong: {{ err }}</div>` };

const Row = {
  props: ["n", "img", "title", "sub", "right", "to", "round"],
  template: `<component :is="to ? 'a' : 'div'" :href="to" class="row" :class="{round, noimg: img === false}">
    <div class="n">{{ n }}</div><img v-if="img !== false" :src="img || '${PLACEHOLDER}'" alt="" loading="lazy">
    <div style="min-width:0"><div class="t">{{ title }}</div><div class="s" v-html="sub"></div></div>
    <div class="r" v-html="right"></div></component>`,
};
const Tile = {
  props: ["img", "title", "sub", "to", "round", "rank"],
  template: `<a :href="to" class="tile" :class="{round}"><span v-if="rank" class="rank">#{{ rank }}</span>
    <img :src="img || '${PLACEHOLDER}'" alt="" loading="lazy">
    <div class="t">{{ title }}</div><div class="s" v-html="sub"></div></a>`,
};
const Stats = {
  props: ["items"],
  template: `<div class="grid g4"><div v-for="s in items" class="card stat">
    <div class="l">{{ s[0] }}</div><div class="v">{{ s[1] }}</div><div v-if="s[2]" class="d" v-html="s[2]"></div></div></div>`,
};
const Hero = {
  props: ["img", "kind", "name", "meta", "stats", "round"],
  template: `<div class="hero" :class="{round}"><img :src="img || '${PLACEHOLDER}'" alt="">
    <div style="min-width:0"><div class="kind">{{ kind }}</div><div class="name">{{ name }}</div>
    <div class="meta" v-html="meta"></div>
    <div v-if="stats && stats.length" class="hero-stats"><div v-for="s in stats"><div class="v">{{ s[1] }}</div><div class="l">{{ s[0] }}</div></div></div>
    </div></div>`,
};
const Sec = {
  props: ["small"],
  template: `<div class="section"><slot/><small v-if="small" v-html="small"></small></div>`,
};
const Embed = {
  props: ["kind", "id", "height"],
  template: `<iframe class="embed" :src="'https://open.spotify.com/embed/' + kind + '/' + id + '?utm_source=generator&theme=0'"
    :height="height || 152" loading="lazy" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe>`,
};
const blocks = { Loading, DbLoading, Err, Row, Tile, Stats, Hero, Sec, Embed };
const page = (def) => ({ components: blocks, ...def, setup() {
  const extra = def.setup ? def.setup() : {};
  return { ...helpers, snap, other, route, snapshots, ...extra };
} });

// --- pages --------------------------------------------------------------------

const Overview = page({
  setup() {
    const state = load(() => json("home.json"));
    const view = computed(() => state.data && {
      now: state.data.home[snap.value], before: other.value && state.data.home[other.value],
      climbers: state.data.climbers, snaps: state.data.snapshots,
    });
    return { state, view };
  },
  template: `<div>
    <p class="title">What Brazil is streaming</p>
    <p class="sub" v-html="'Artists, tracks and albums behind the Viral city playlists and the national Top 200 · ' + badge(snap)"></p>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!view"/>
    <template v-else>
      <Stats :items="[['Artists','artists'],['Tracks','tracks'],['Albums','albums'],['Playlists','playlists']].map(([l, f]) =>
        [l, thousands(view.now.counts[f]), view.before ? delta(view.now.counts[f] - view.before.counts[f]) + ' vs ' + label(other) : ''])"/>
      <div class="grid g2"><Stats :items="[['Cities represented', thousands(view.now.reach_stats.cities), 'Viral city playlists'],
        ['Artists with city reach', thousands(view.now.reach_stats.artists), 'presence across at least one city']]"/></div>
      <template v-if="view.now.podium.length">
        <Sec small="Spotify daily Top 200 Brazil">Top of the chart</Sec>
        <div class="tiles big"><Tile v-for="r in view.now.podium" :key="r.id" :img="r.img" :title="r.name" :rank="r.pos"
          :sub="esc(r.artists) + ' · ' + number(r.streams) + ' streams'" :to="link('track', {id: r.id})"/></div>
      </template>
      <Sec small="Spotify popularity score, 0–100">Most popular artists</Sec>
      <div class="tiles"><Tile v-for="r in view.now.top" :key="r.id" :img="r.img" :title="r.name" round
        :sub="number(r.followers) + ' followers'" :to="link('artist', {id: r.id})"/></div>
      <div class="cols">
        <div><Sec small="in the most Viral city playlists">Everywhere at once</Sec>
          <Row v-for="(r, i) in view.now.reach" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" round
            :sub="pct(r.playlists / (view.now.counts.playlists || 1)) + ' of the cities'"
            :right="'<b>' + r.playlists + '</b> playlists'" :to="link('artist', {id: r.id})"/></div>
        <div v-if="view.climbers.length"><Sec :small="'popularity ' + label(view.snaps[0]) + ' → ' + label(view.snaps.at(-1))">Biggest climbers</Sec>
          <Row v-for="(r, i) in view.climbers" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" round
            :sub="r.pop_old + ' → ' + r.pop_new" :right="delta(r.pop_new - r.pop_old)" :to="link('artist', {id: r.id})"/></div>
      </div>
    </template></div>`,
});

const Charts = page({
  setup() {
    const state = load(() => json(`charts-${snap.value}.json`));
    const kind = ref(null), filter = ref(""), start = ref(0);
    const kinds = computed(() => (state.data ? Object.keys(state.data) : []));
    watch(kinds, (k) => { if (!kind.value) kind.value = k[0]; }, { immediate: true });
    watch([kind, filter], () => (start.value = 0));
    const rows = computed(() => {
      if (!state.data || !kind.value) return [];
      const f = filter.value.trim().toLowerCase();
      return state.data[kind.value].rows.filter((r) => !f
        || (r.name || "").toLowerCase().includes(f) || (r.artists || "").toLowerCase().includes(f));
    });
    return { state, kind, kinds, filter, rows, start, PAGE: 50 };
  },
  template: `<div>
    <p class="title">Top 200 Brazil</p>
    <p class="sub" v-html="'The most streamed songs in Brazil on Spotify · ' + badge(snap)"></p>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <div v-else-if="!kinds.length" class="note">There is no chart in this snapshot: charts were added in the 2026 collection.</div>
    <template v-else>
      <div class="toolbar">
        <div class="pills"><button v-for="k in kinds" :class="{active: kind === k}" @click="kind = k">{{ k[0].toUpperCase() + k.slice(1) }}</button></div>
        <input class="search" v-model="filter" placeholder="Filter by track or artist">
      </div>
      <p class="sub">Chart of {{ state.data[kind].date }} · source kworb.net</p>
      <div v-if="rows.length > PAGE" class="pills">
        <button v-for="s in Array.from({length: Math.ceil(rows.length / PAGE)}, (_, i) => i * PAGE)"
          :class="{active: start === s}" @click="start = s">{{ s + 1 }}–{{ Math.min(s + PAGE, rows.length) }}</button>
      </div>
      <Row v-for="r in rows.slice(start, start + PAGE)" :key="r.pos" :n="r.pos" :img="r.img" :title="r.name" :sub="esc(r.artists)"
        :right="'<b>' + number(r.streams) + '</b> ' + (kind === 'daily' ? 'today' : 'this week') + ' · ' + number(r.total) + ' total'"
        :to="link('track', {id: r.id})"/>
      <div v-if="!rows.length" class="note">No track matches the filter.</div>
    </template></div>`,
});

const Cities = page({
  setup() {
    const state = load(() => json(`cities-${snap.value}.json`));
    const selected = ref(route.params.city || null);
    watch(() => state.data, (d) => {
      if (d && !d.some((c) => String(c.id) === String(selected.value)))
        selected.value = String((d.find((c) => c.name === "São Paulo") || d[0] || {}).id);
    });
    const city = computed(() => state.data?.find((c) => String(c.id) === String(selected.value)));
    return { state, selected, city };
  },
  template: `<div>
    <p class="title">City pulse</p>
    <p class="sub" v-html="'Current Last.fm metro charts · ' + badge(snap)"></p>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <div v-else-if="!state.data.length" class="note">No Last.fm city charts have been collected for this snapshot yet.</div>
    <template v-else>
      <select v-model="selected"><option v-for="c in state.data" :value="String(c.id)">{{ c.name }} · {{ c.n_tracks }} tracks</option></select>
      <template v-if="city">
        <Stats :items="[['Artists ranked', thousands(city.n_artists), 'Last.fm chart artists'], ['Tracks ranked', thousands(city.n_tracks), 'current metro chart']]"/>
        <div class="cols c32">
          <div><Sec small="artist affinity from the current Last.fm chart">{{ city.name }}</Sec>
            <div v-if="!city.artists.length" class="note">Last.fm returned no artist ranking for this city.</div>
            <div v-else class="city-ranking"><div v-for="(a, i) in city.artists" class="city-rank">
              <span class="p">{{ i + 1 }}</span><div class="nm">{{ a[0] }}</div><span class="tr">{{ a[2] }} tracks</span><b>{{ Math.round(a[1]) }}</b></div></div></div>
          <div><Sec small="the raw Last.fm signal">Top tracks</Sec>
            <Row v-for="(t, i) in city.tracks" :key="i" :n="i + 1" :img="false" :title="t[0]" :sub="esc(t[1])"/></div>
        </div>
      </template>
    </template></div>`,
});

const ARTIST_TILE = "SELECT a.art_codigo id, TRIM(a.art_primeironome || ' ' || a.art_ultimonome) name, a.art_seguidores followers, i.image_url img FROM art_artista a LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo";
const ARTISTS = "GROUP_CONCAT(TRIM(a.art_primeironome || ' ' || a.art_ultimonome), ', ') artists";

const Search = page({
  setup() {
    const term = ref(route.params.q || "");
    const state = reactive({ data: null, err: null, busy: false });
    let timer, seq = 0;
    watch(term, (t) => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        history.replaceState(null, "", link("search", { q: t.trim() || null }));
        if (t.trim().length < 2) { state.data = null; return; }
        const my = ++seq, like = `%${t.trim()}%`, c = snap.value;
        state.busy = true;
        try {
          const [artists, tracks, albums] = await Promise.all([
            q(`${ARTIST_TILE} WHERE a.coleta = ? AND (a.art_primeironome || ' ' || a.art_ultimonome) LIKE ? ORDER BY a.art_popularidade DESC LIMIT 12`, [c, like]),
            q(`SELECT f.fai_codigo id, i.image_url img, f.fai_nome name, f.fai_duracao dur, ${ARTISTS} FROM fai_faixa f LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo LEFT JOIN afx_artistafaixa x ON x.afx_fai_codigo = f.fai_codigo AND x.coleta = f.coleta LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo AND a.coleta = f.coleta WHERE f.coleta = ? AND f.fai_nome LIKE ? GROUP BY f.fai_codigo ORDER BY f.fai_popularidade DESC LIMIT 10`, [c, like]),
            q(`SELECT b.alb_codigo id, i.image_url img, b.alb_nome name, b.alb_tipo type, SUBSTR(b.alb_lancamento, 1, 4) year FROM alb_album b LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo WHERE b.coleta = ? AND b.alb_nome LIKE ? ORDER BY b.alb_popularidade DESC LIMIT 12`, [c, like]),
          ]);
          if (my === seq) state.data = { artists, tracks, albums };
        } catch (e) { state.err = String(e.message || e); }
        if (my === seq) state.busy = false;
      }, 250);
    }, { immediate: true });
    db();
    return { term, state };
  },
  template: `<div>
    <p class="title">Search</p><p class="sub" v-html="badge(snap)"></p>
    <input class="search" v-model="term" placeholder="What do you want to find?" autofocus>
    <Err v-if="state.err" :err="state.err"/>
    <div v-else-if="term.trim().length < 2" class="note">Type at least two characters: an artist, a track or an album.</div>
    <DbLoading v-else-if="!state.data"/>
    <div v-else-if="!state.data.artists.length && !state.data.tracks.length && !state.data.albums.length" class="note">Nothing found for “{{ term }}” in this snapshot.</div>
    <template v-else>
      <template v-if="state.data.tracks.length"><Sec>Tracks</Sec>
        <Row v-for="(r, i) in state.data.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="esc(r.artists)" :right="duration(r.dur)" :to="link('track', {id: r.id})"/></template>
      <template v-if="state.data.artists.length"><Sec>Artists</Sec>
        <div class="tiles"><Tile v-for="r in state.data.artists" :key="r.id" :img="r.img" :title="r.name" round :sub="number(r.followers) + ' followers'" :to="link('artist', {id: r.id})"/></div></template>
      <template v-if="state.data.albums.length"><Sec>Albums</Sec>
        <div class="tiles"><Tile v-for="r in state.data.albums" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div></template>
    </template></div>`,
});

const Artist = page({
  setup() {
    const id = route.params.id, c = snap.value, o = other.value;
    const state = load(async () => {
      if (!id) return { list: await q(`${ARTIST_TILE} WHERE a.coleta = ?1 AND a.art_codigo IN (SELECT afx_art_codigo FROM afx_artistafaixa WHERE coleta = ?1) ORDER BY a.art_popularidade DESC LIMIT 24`, [c]) };
      const [info] = await q("SELECT a.*, i.image_url FROM art_artista a LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo WHERE a.art_codigo = ? AND a.coleta = ?", [id, c]);
      if (!info) return { missing: true };
      const [prev] = o ? await q("SELECT art_seguidores, art_popularidade FROM art_artista WHERE art_codigo = ? AND coleta = ?", [id, o]) : [];
      const [genres, [{ n: playlists }], tracks, albums, similar, cities] = await Promise.all([
        q("SELECT DISTINCT g.gen_nome g FROM age_artistagenero ag JOIN gen_genero g ON g.gen_codigo = ag.age_gen_codigo WHERE ag.age_art_codigo = ? AND ag.coleta = ?", [id, c]),
        q("SELECT COUNT(DISTINCT apy_ply_codigo) n FROM apy_artistaplaylist WHERE apy_art_codigo = ? AND coleta = ?", [id, c]),
        q("SELECT f.fai_codigo id, i.image_url img, f.fai_nome name, f.fai_popularidade pop, f.fai_duracao dur, (SELECT COUNT(*) FROM fxp_faixaplaylist p WHERE p.fxp_fai_codigo = f.fai_codigo AND p.coleta = f.coleta) playlists FROM afx_artistafaixa x JOIN fai_faixa f ON f.fai_codigo = x.afx_fai_codigo AND f.coleta = x.coleta LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo WHERE x.afx_art_codigo = ? AND x.coleta = ? ORDER BY f.fai_popularidade DESC LIMIT 10", [id, c]),
        q("SELECT b.alb_codigo id, i.image_url img, b.alb_nome name, b.alb_tipo type, SUBSTR(b.alb_lancamento, 1, 4) year FROM aal_artistaalbum aa JOIN alb_album b ON b.alb_codigo = aa.aal_alb_codigo AND b.coleta = aa.coleta LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo WHERE aa.aal_art_codigo = ? AND aa.coleta = ? ORDER BY b.alb_lancamento DESC LIMIT 12", [id, c]),
        q("SELECT a.art_codigo id, i.image_url img, TRIM(a.art_primeironome || ' ' || a.art_ultimonome) name, s.aa_similaridade sim, s.aa_fonte src FROM aa_artistaartista s JOIN art_artista a ON a.art_codigo = s.aa_art_b_codigo AND a.coleta = s.coleta LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo WHERE s.aa_art_a_codigo = ? AND s.coleta = ? ORDER BY s.aa_similaridade DESC NULLS LAST, a.art_popularidade DESC LIMIT 12", [id, c]),
        q("SELECT c.cid_nome name, c.cid_regiao region, c.cid_pais country, r.arc_ouvintes listeners FROM arc_artistacidade r JOIN cid_cidade c ON c.cid_codigo = r.arc_cid_codigo WHERE r.arc_art_codigo = ? AND r.coleta = ? ORDER BY r.arc_ouvintes DESC LIMIT 10", [id, c]),
      ]);
      const stats = [["Followers", number(info.art_seguidores)], ["Popularity", info.art_popularidade ?? "—"], ["Viral city playlists", playlists]];
      if (info.art_ouvintes != null) stats.push(["Monthly listeners", number(info.art_ouvintes)]);
      let meta = badge(c);
      if (prev) meta += ` &nbsp; popularity ${delta(info.art_popularidade - prev.art_popularidade)} · followers ${delta(info.art_seguidores - prev.art_seguidores)} since ${label(o)}`;
      const topListeners = Math.max(1, ...cities.map((r) => r.listeners || 0));
      return { info, name: name(info.art_primeironome, info.art_ultimonome), meta, stats, genres, tracks, albums, similar, cities, topListeners };
    });
    return { state, id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <DbLoading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Artists</p><p class="sub" v-html="'Pick one, or use Search · ' + badge(snap)"></p>
      <div class="tiles"><Tile v-for="r in state.data.list" :key="r.id" :img="r.img" :title="r.name" round :sub="number(r.followers) + ' followers'" :to="link('artist', {id: r.id})"/></div>
    </template>
    <div v-else-if="state.data.missing" class="note">This artist is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="state.data.info.image_url" kind="Artist" :name="state.data.name" :meta="state.data.meta" :stats="state.data.stats" round/>
      <div v-if="state.data.genres.length" style="margin-top:14px"><span v-for="g in state.data.genres" class="chip">{{ g.g.replace(/\\b\\w/g, (m) => m.toUpperCase()) }}</span></div>
      <div class="cols c32">
        <div><Sec small="tracks in the playlists and charts">Popular</Sec>
          <div v-if="!state.data.tracks.length" class="note">No tracks of this artist were collected in this snapshot.</div>
          <Row v-for="(r, i) in state.data.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name"
            :sub="r.playlists + ' playlists · ' + duration(r.dur)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/></div>
        <div><Sec>Listen</Sec><Embed kind="artist" :id="id" height="380"/></div>
      </div>
      <template v-if="state.data.albums.length"><Sec>Discography</Sec>
        <div class="tiles"><Tile v-for="r in state.data.albums" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div></template>
      <template v-if="state.data.similar.length">
        <Sec :small="state.data.similar[0].src === 'lastfm' ? 'Last.fm' : 'Spotify related artists (retired in 2024)'">Fans also like</Sec>
        <div class="tiles"><Tile v-for="r in state.data.similar" :key="r.id" :img="r.img" :title="r.name" round
          :sub="r.sim != null ? pct(r.sim) + ' similar' : 'Related'" :to="link('artist', {id: r.id})"/></div></template>
      <template v-if="state.data.cities.length"><Sec small="monthly listeners by city">Where people listen</Sec>
        <Row v-for="(r, i) in state.data.cities" :key="i" :n="i + 1" :img="false" :title="r.name" :sub="esc(r.region) + ', ' + esc(r.country)"
          :right="'<b>' + number(r.listeners) + '</b><span class=pop><i style=width:' + Math.round(100 * r.listeners / state.data.topListeners) + '%></i></span>'"/></template>
    </template></div>`,
});

const Album = page({
  setup() {
    const id = route.params.id, c = snap.value;
    const state = load(async () => {
      if (!id) return { list: await q("SELECT b.alb_codigo id, i.image_url img, b.alb_nome name, SUBSTR(b.alb_lancamento, 1, 4) year, b.alb_tipo type FROM alb_album b LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo WHERE b.coleta = ?1 AND b.alb_codigo IN (SELECT fal_alb_codigo FROM fal_faixaalbum WHERE coleta = ?1) AND b.alb_tipo = 'album' ORDER BY b.alb_popularidade DESC LIMIT 24", [c]) };
      const [album] = await q("SELECT b.*, i.image_url FROM alb_album b LEFT JOIN albums_images i ON i.alb_codigo = b.alb_codigo WHERE b.alb_codigo = ? AND b.coleta = ?", [id, c]);
      if (!album) return { missing: true };
      const [artists, tracks] = await Promise.all([
        q("SELECT a.art_codigo id, TRIM(a.art_primeironome || ' ' || a.art_ultimonome) name, i.image_url img FROM aal_artistaalbum aa JOIN art_artista a ON a.art_codigo = aa.aal_art_codigo AND a.coleta = aa.coleta LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo WHERE aa.aal_alb_codigo = ? AND aa.coleta = ?", [id, c]),
        q("SELECT f.fai_codigo id, i.image_url img, f.fai_nome name, f.fai_popularidade pop, f.fai_duracao dur FROM fal_faixaalbum fa JOIN fai_faixa f ON f.fai_codigo = fa.fal_fai_codigo AND f.coleta = fa.coleta LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo WHERE fa.fal_alb_codigo = ? AND fa.coleta = ? ORDER BY f.fai_popularidade DESC", [id, c]),
      ]);
      const meta = `<b>${esc(artists.map((a) => a.name).join(", "))}</b> · ${esc(album.alb_lancamento || "")} · ${album.alb_qtdmusicas} tracks · ${badge(c)}`;
      return { album, artists, tracks, meta };
    });
    return { state, id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <DbLoading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Albums</p><p class="sub" v-html="'Albums of the tracks in the playlists · ' + badge(snap)"></p>
      <div class="tiles"><Tile v-for="r in state.data.list" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div>
    </template>
    <div v-else-if="state.data.missing" class="note">This album is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="state.data.album.image_url" :kind="state.data.album.alb_tipo" :name="state.data.album.alb_nome" :meta="state.data.meta"
        :stats="[['Popularity', state.data.album.alb_popularidade ?? '—']]"/>
      <div class="cols c32">
        <div><Sec>Listen</Sec><Embed kind="album" :id="id" height="420"/></div>
        <div>
          <template v-if="state.data.tracks.length"><Sec>In the playlists</Sec>
            <Row v-for="(r, i) in state.data.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="duration(r.dur)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/></template>
          <Sec>Artists</Sec>
          <Row v-for="r in state.data.artists" :key="r.id" n="" :img="r.img" :title="r.name" sub="Artist" round :to="link('artist', {id: r.id})"/>
        </div>
      </div>
    </template></div>`,
});

const Track = page({
  setup() {
    const id = route.params.id, c = snap.value;
    const state = load(async () => {
      if (!id) return { list: await q(`SELECT f.fai_codigo id, i.image_url img, f.fai_nome name, f.fai_popularidade pop, ${ARTISTS} FROM fai_faixa f LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo LEFT JOIN afx_artistafaixa x ON x.afx_fai_codigo = f.fai_codigo AND x.coleta = f.coleta LEFT JOIN art_artista a ON a.art_codigo = x.afx_art_codigo AND a.coleta = f.coleta WHERE f.coleta = ? GROUP BY f.fai_codigo ORDER BY f.fai_popularidade DESC LIMIT 30`, [c]) };
      const [track] = await q("SELECT f.*, i.image_url FROM fai_faixa f LEFT JOIN faixas_images i ON i.fai_codigo = f.fai_codigo WHERE f.fai_codigo = ? AND f.coleta = ?", [id, c]);
      if (!track) return { missing: true };
      const [artists, album, chart, playlists] = await Promise.all([
        q("SELECT a.art_codigo id, TRIM(a.art_primeironome || ' ' || a.art_ultimonome) name, a.art_seguidores followers, i.image_url img FROM afx_artistafaixa x JOIN art_artista a ON a.art_codigo = x.afx_art_codigo AND a.coleta = x.coleta LEFT JOIN artists_images i ON i.art_codigo = a.art_codigo WHERE x.afx_fai_codigo = ? AND x.coleta = ? ORDER BY x.afx_principal DESC", [id, c]),
        q("SELECT b.alb_codigo id, b.alb_nome name, SUBSTR(b.alb_lancamento, 1, 4) year FROM fal_faixaalbum fa JOIN alb_album b ON b.alb_codigo = fa.fal_alb_codigo AND b.coleta = fa.coleta WHERE fa.fal_fai_codigo = ? AND fa.coleta = ?", [id, c]),
        q("SELECT chr_tipo, chr_posicao, chr_streams, chr_total_streams FROM chr_chart WHERE chr_fai_codigo = ? AND chr_coleta = ?", [id, c]),
        q("SELECT p.ply_nome FROM fxp_faixaplaylist x JOIN ply_playlist p ON p.ply_codigo = x.fxp_ply_codigo AND p.coleta = x.coleta WHERE x.fxp_fai_codigo = ? AND x.coleta = ? ORDER BY p.ply_seguidores DESC", [id, c]),
      ]);
      const stats = [["Popularity", track.fai_popularidade ?? "—"]];
      const daily = chart.find((r) => r.chr_tipo === "daily");
      if (daily) stats.push(["Top 200 today", `#${daily.chr_posicao}`], ["Streams today", number(daily.chr_streams)], ["Streams in Brazil", number(daily.chr_total_streams)]);
      if (track.fai_reproducoes != null) stats.push(["Plays", number(track.fai_reproducoes)]);
      const albumText = album[0] ? ` · ${esc(album[0].name)} (${album[0].year})` : "";
      const meta = `<b>${esc(artists.map((a) => a.name).join(", "))}</b>${albumText} · ${duration(track.fai_duracao)}${track.fai_explicita ? " · 🅴" : ""} · ${badge(c)}`;
      const cities = playlists.map((p) => p.ply_nome.replace(/^Viral /, "").replace(/ BR$/, ""));
      return { track, artists, album, stats, meta, cities };
    });
    return { state, id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <DbLoading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Tracks</p><p class="sub" v-html="'The most popular tracks in the playlists · ' + badge(snap)"></p>
      <Row v-for="(r, i) in state.data.list" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="esc(r.artists)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/>
    </template>
    <div v-else-if="state.data.missing" class="note">This track is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="state.data.track.image_url" kind="Track" :name="state.data.track.fai_nome" :meta="state.data.meta" :stats="state.data.stats"/>
      <div style="height:16px"></div>
      <Embed kind="track" :id="id"/>
      <div class="cols c23">
        <div><Sec>Artists</Sec>
          <Row v-for="r in state.data.artists" :key="r.id" n="" :img="r.img" :title="r.name" :sub="number(r.followers) + ' followers'" round :to="link('artist', {id: r.id})"/>
          <template v-if="state.data.album.length"><Sec>Album</Sec>
            <Row v-for="r in state.data.album" :key="r.id" n="" :img="state.data.track.image_url" :title="r.name" :sub="r.year" :to="link('album', {id: r.id})"/></template></div>
        <div><Sec :small="state.data.cities.length + ' city playlists'">Viral in</Sec>
          <div v-if="!state.data.cities.length" class="note">Not in any Viral city playlist; it is here because of the Top 200 chart.</div>
          <span v-for="c in state.data.cities" class="chip">{{ c }}</span></div>
      </div>
    </template></div>`,
});

const AGE_BUCKETS = ["Same year", "1", "2–3", "4–5", "6–10", "11–20", "20+"];
const ageBucket = (a) => (a <= 0 ? 0 : a <= 1 ? 1 : a <= 3 ? 2 : a <= 5 ? 3 : a <= 10 ? 4 : a <= 20 ? 5 : 6);

const Compare = page({
  setup() {
    const state = load(async () => {
      const [old, now] = [snapshots.value[0], snapshots.value.at(-1)];
      const [profile, ages, genres, reach] = await Promise.all([
        q("SELECT coleta, COUNT(*) tracks, AVG(fai_duracao) / 1000.0 seconds, AVG(fai_explicita) explicit, AVG(fai_popularidade) popularity FROM fai_faixa WHERE coleta IN (?, ?) GROUP BY coleta", [old, now]),
        q("SELECT fa.coleta, CAST(SUBSTR(fa.coleta, 1, 4) AS INTEGER) - CAST(SUBSTR(b.alb_lancamento, 1, 4) AS INTEGER) age, COUNT(*) n FROM fal_faixaalbum fa JOIN alb_album b ON b.alb_codigo = fa.fal_alb_codigo AND b.coleta = fa.coleta WHERE fa.coleta IN (?, ?) AND b.alb_lancamento IS NOT NULL GROUP BY 1, 2", [old, now]),
        q("SELECT g.coleta, g.gen_nome name, COUNT(DISTINCT ag.age_art_codigo) artists FROM age_artistagenero ag JOIN gen_genero g ON g.gen_codigo = ag.age_gen_codigo AND g.coleta = ag.coleta JOIN apy_artistaplaylist p ON p.apy_art_codigo = ag.age_art_codigo AND p.coleta = ag.coleta WHERE ag.coleta IN (?, ?) GROUP BY g.coleta, g.gen_nome", [old, now]),
        q("SELECT p.coleta, p.apy_art_codigo id, TRIM(a.art_primeironome || ' ' || a.art_ultimonome) name, COUNT(DISTINCT p.apy_ply_codigo) playlists, i.image_url img FROM apy_artistaplaylist p JOIN art_artista a ON a.art_codigo = p.apy_art_codigo AND a.coleta = p.coleta LEFT JOIN artists_images i ON i.art_codigo = p.apy_art_codigo WHERE p.coleta IN (?, ?) GROUP BY p.coleta, p.apy_art_codigo", [old, now]),
      ]);
      const a = profile.find((r) => r.coleta === old), b = profile.find((r) => r.coleta === now);
      const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
      const stats = [
        ["Tracks", thousands(b.tracks), delta(b.tracks - a.tracks) + ` vs ${label(old)}`],
        ["Average length", mmss(b.seconds), delta(b.seconds - a.seconds, (v) => v.toFixed(0), "s")],
        ["Explicit tracks", pct(b.explicit), delta((b.explicit - a.explicit) * 100, (v) => v.toFixed(1), " pp")],
        ["Avg. track popularity", b.popularity.toFixed(0), delta(b.popularity - a.popularity, (v) => v.toFixed(1))],
      ];
      // share of tracks per release-age bucket, for each snapshot
      const ageShare = {};
      for (const s of [old, now]) {
        const counts = Array(AGE_BUCKETS.length).fill(0);
        for (const r of ages) if (r.coleta === s && r.age != null && r.age > -99) counts[ageBucket(r.age)] += r.n;
        const total = counts.reduce((x, y) => x + y, 0) || 1;
        ageShare[s] = counts.map((n) => n / total);
      }
      const genreTotal = {};
      for (const g of genres) genreTotal[g.coleta] = (genreTotal[g.coleta] || 0) + g.artists;
      const share = {};
      for (const g of genres) (share[g.name] ??= { [old]: 0, [now]: 0 })[g.coleta] = g.artists / genreTotal[g.coleta];
      const topGenres = Object.entries(share).sort((x, y) => Math.max(...Object.values(y[1])) - Math.max(...Object.values(x[1]))).slice(0, 12);
      const by = (s) => new Map(reach.filter((r) => r.coleta === s).map((r) => [r.id, r]));
      const before = by(old), after = by(now);
      const top12 = (list) => list.sort((x, y) => y.playlists - x.playlists).slice(0, 12);
      return {
        old, now, stats, ageShare, topGenres,
        ageMax: Math.max(...Object.values(ageShare).flat()),
        genreMax: Math.max(...topGenres.flatMap(([, v]) => Object.values(v))),
        arrived: top12([...after.values()].filter((r) => !before.has(r.id))),
        gone: top12([...before.values()].filter((r) => !after.has(r.id))),
      };
    });
    return { state, AGE_BUCKETS };
  },
  template: `<div>
    <div v-if="snapshots.length < 2" class="note">Only one snapshot available, nothing to compare yet.</div>
    <template v-else>
      <p class="title">Then vs now</p>
      <p class="sub" v-html="badge(snapshots[0]) + ' vs ' + badge(snapshots.at(-1))"></p>
      <div class="note">The <b>Viral city playlists</b> stopped being updated in May 2024 (they were maintained by the Every Noise at Once project),
        so playlist-based numbers labelled {{ label(snapshots.at(-1)) }} reflect what was viral around May 2024. Popularity, followers and the Top 200 chart are current.</div>
      <Err v-if="state.err" :err="state.err"/>
      <DbLoading v-else-if="!state.data"/>
      <template v-else>
        <div style="height:6px"></div>
        <Stats :items="state.data.stats"/>
        <Sec small="release age when collected">How old are the songs?</Sec>
        <div class="bars">
          <div class="legend"><span><i class="c-old"></i>{{ label(state.data.old) }}</span><span><i class="c-new"></i>{{ label(state.data.now) }}</span></div>
          <div v-for="(b, i) in AGE_BUCKETS" class="bar-row"><span>{{ i === 0 ? b : b + ' yrs' }}</span><div>
            <div v-for="s in [state.data.old, state.data.now]" class="bar"><i :class="s === state.data.old ? 'c-old' : 'c-new'"
              :style="{width: 85 * state.data.ageShare[s][i] / state.data.ageMax + '%'}"></i>{{ pct(state.data.ageShare[s][i], 1) }}</div></div></div>
        </div>
        <template v-if="state.data.topGenres.length">
          <Sec small="share of genre tags of the artists in the playlists">Genres</Sec>
          <div class="bars">
            <div class="legend"><span><i class="c-old"></i>{{ label(state.data.old) }}</span><span><i class="c-new"></i>{{ label(state.data.now) }}</span></div>
            <div v-for="[g, v] in state.data.topGenres" class="bar-row"><span :title="g">{{ g }}</span><div>
              <div v-for="s in [state.data.old, state.data.now]" class="bar"><i :class="s === state.data.old ? 'c-old' : 'c-new'"
                :style="{width: 85 * v[s] / state.data.genreMax + '%'}"></i>{{ pct(v[s], 1) }}</div></div></div>
          </div>
        </template>
        <Sec small="not in any playlist before">New in {{ label(state.data.now) }}</Sec>
        <div class="tiles"><Tile v-for="r in state.data.arrived" :key="r.id" :img="r.img" :title="r.name" round :sub="r.playlists + ' playlists'" :to="link('artist', {id: r.id, snap: state.data.now})"/></div>
        <Sec small="in many playlists then, none now">Gone since {{ label(state.data.old) }}</Sec>
        <div class="tiles"><Tile v-for="r in state.data.gone" :key="r.id" :img="r.img" :title="r.name" round :sub="r.playlists + ' playlists'" :to="link('artist', {id: r.id, snap: state.data.old})"/></div>
      </template>
    </template></div>`,
});

// --- app ----------------------------------------------------------------------

const PAGES = { overview: Overview, compare: Compare, charts: Charts, cities: Cities, search: Search, artist: Artist, album: Album, track: Track };
const NAV = [
  { page: "overview", label: "Home" }, { page: "compare", label: "Then vs now" }, { page: "charts", label: "Top 200" },
  { page: "cities", label: "Cities" }, { page: "search", label: "Search" }, { page: "artist", label: "Artists" },
  { page: "album", label: "Albums" }, { page: "track", label: "Tracks" },
];

json("home.json").then((d) => {
  snapshots.value = d.snapshots;
  createApp({
    setup() {
      const view = computed(() => PAGES[route.page] || Overview);
      return { route, snapshots, snap, view, nav: NAV, link, label };
    },
  }).mount("#app");
}).catch((e) => {
  document.getElementById("app").outerHTML = `<div class="note" style="margin:40px">Could not load the site data: ${esc(e.message)}</div>`;
});
