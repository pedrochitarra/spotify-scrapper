// Spotify Showcase, Vue version of the Streamlit app (same pages and look).
// Every page reads small JSON files made by scripts/build_static.py, so
// nothing heavy is downloaded (the Streamlit version loads the database).
const { createApp, reactive, computed, watch, ref } = Vue;

const IMAGE_PREFIX = "https://i.scdn.co/image/";
const PLACEHOLDER = "https://i.scdn.co/image/ab6761610000517458efbed422ab46484466822b";
const LEGACY = "2023-11";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// --- data ---------------------------------------------------------------------

const cache = {};
const json = (name) => (cache[name] ??= fetch(name).then((r) => {
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
  return r.json();
}));

// Run an async loader for a page; state.data / state.err feed the template
function load(fn) {
  const state = reactive({ data: null, err: null });
  fn().then((d) => (state.data = d)).catch((e) => { console.error(e); state.err = String(e.message || e); });
  return state;
}

// --- formatting ---------------------------------------------------------------

const fold = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
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
const blocks = { Loading, Err, Row, Tile, Stats, Hero, Sec, Embed };
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
    // One small file per city, loaded when it is picked (kept in the URL)
    const detail = reactive({ data: null, err: null });
    watch(city, (c) => {
      if (!c) return;
      history.replaceState(null, "", link("cities", { city: c.id }));
      detail.data = null;
      json(`city/${snap.value}/${c.id}.json`).then((d) => { if (city.value === c) detail.data = d; })
        .catch((e) => (detail.err = String(e.message || e)));
    });
    // Accent-insensitive filter of the city list ("sao" finds São Paulo)
    const term = ref("");
    const matches = computed(() => {
      const t = fold(term.value.trim());
      return t ? (state.data || []).filter((c) => fold(c.name).includes(t)) : [];
    });
    const pick = (c) => { selected.value = String(c.id); term.value = ""; };
    return { state, selected, city, detail, term, matches, pick };
  },
  template: `<div>
    <p class="title">City pulse</p>
    <p class="sub" v-html="'What each city has in its Spotify Viral playlist · ' + badge(snap)"></p>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <div v-else-if="!state.data.length" class="note">No Viral city playlists in this snapshot.</div>
    <template v-else>
      <div class="city-search">
        <input class="search" v-model="term" :placeholder="'Search ' + state.data.length + ' cities…'" @keydown.enter="matches[0] && pick(matches[0])">
        <div v-if="term.trim()" class="city-results">
          <button v-for="c in matches.slice(0, 12)" :key="c.id" @click="pick(c)">{{ c.name }} <small>{{ c.region }}</small></button>
          <div v-if="!matches.length" class="none">No city matches “{{ term }}”.</div>
        </div>
      </div>
      <template v-if="city">
        <p class="title" style="font-size:clamp(1.6rem,4vw,2.4rem)">{{ city.name }} <span class="sub" style="font-size:1rem">{{ city.region }}</span></p>
        <div style="height:12px"></div>
        <Stats :items="[['Tracks', thousands(city.tracks), 'in the Viral ' + city.name + ' playlist'], ['Artists', thousands(city.artists), 'with a track in the playlist']]"/>
        <div v-if="snap !== snapshots[0]" class="note">The Viral city playlists stopped being updated in May 2024, so this is what was viral in {{ city.name }} then.</div>
        <Err v-if="detail.err" :err="detail.err"/>
        <Loading v-else-if="!detail.data"/>
        <template v-else>
          <template v-if="detail.data.local.length">
            <Sec small="in this playlist and in few other cities">Local favorites</Sec>
            <div class="tiles"><Tile v-for="a in detail.data.local" :key="a.id" :img="a.img" :title="a.name" round
              :sub="a.cities === 1 ? 'only here' : 'in ' + a.cities + ' cities'" :to="link('artist', {id: a.id})"/></div>
          </template>
          <div class="cols">
            <div><Sec small="most tracks in the playlist">Top artists</Sec>
              <Row v-for="(a, i) in detail.data.artists" :key="a.id" :n="i + 1" :img="a.img" :title="a.name" round
                :sub="a.cities === 1 ? 'only in ' + city.name : 'viral in ' + a.cities + ' cities'"
                :right="'<b>' + a.tracks + '</b> ' + (a.tracks === 1 ? 'track' : 'tracks')" :to="link('artist', {id: a.id})"/></div>
            <div><Sec small="by Spotify popularity">Tracks</Sec>
              <Row v-for="(t, i) in detail.data.tracks" :key="t.id" :n="i + 1" :img="t.img" :title="t.name" :sub="esc(t.artists)"
                :right="popBar(t.pop)" :to="link('track', {id: t.id})"/></div>
          </div>
        </template>
      </template>
    </template></div>`,
});

// Detail page: the item's JSON (artist/<snap>/<id>.json), or the pick list
// of the section when there is no id. A missing file = not in this snapshot.
function loadItem(kind) {
  const id = route.params.id;
  return load(async () => {
    if (!id) return { list: (await json(`lists-${snap.value}.json`))[kind + "s"] };
    const r = await fetch(`${kind}/${snap.value}/${encodeURIComponent(id)}.json`);
    if (r.status === 404) return { missing: true };
    if (!r.ok) throw new Error(`${kind}: HTTP ${r.status}`);
    return { item: await r.json() };
  });
}

const fullImg = (u) => (u && !u.startsWith("http") ? IMAGE_PREFIX + u : u);

const Search = page({
  setup() {
    const term = ref(route.params.q || "");
    const index = load(async () => {
      const d = await json(`search-${snap.value}.json`);
      // Lowercase, accent-free names for matching ("joao" finds João)
      // Tracks also match by artist ("anitta" finds her songs)
      const keyed = (list, text) => list.map((r) => ({ r, key: fold(text(r)) }));
      // markRaw: thousands of rows, no need for Vue to watch them
      return Vue.markRaw({
        artists: keyed(d.artists, (r) => r[1]),
        tracks: keyed(d.tracks, (r) => `${r[1]} ${r[3] || ""}`),
        albums: keyed(d.albums, (r) => r[1]),
      });
    });
    const results = computed(() => {
      const t = fold(term.value.trim());
      if (!index.data || t.length < 2) return null;
      const find = (list, n) => { const out = []; for (const x of list) { if (x.key.includes(t)) out.push(x.r); if (out.length === n) break; } return out; };
      return {
        artists: find(index.data.artists, 12).map(([id, name, img, followers]) => ({ id, name, img: fullImg(img), followers })),
        tracks: find(index.data.tracks, 10).map(([id, name, img, artists, dur]) => ({ id, name, img: fullImg(img), artists, dur })),
        albums: find(index.data.albums, 12).map(([id, name, img, type, year]) => ({ id, name, img: fullImg(img), type, year })),
      };
    });
    let timer;
    watch(term, (t) => {
      clearTimeout(timer);
      timer = setTimeout(() => history.replaceState(null, "", link("search", { q: t.trim() || null })), 300);
    });
    return { term, index, results };
  },
  template: `<div>
    <p class="title">Search</p><p class="sub" v-html="badge(snap)"></p>
    <input class="search" v-model="term" placeholder="What do you want to find?" autofocus>
    <Err v-if="index.err" :err="index.err"/>
    <div v-else-if="term.trim().length < 2" class="note">Type at least two characters: an artist, a track or an album.</div>
    <Loading v-else-if="!results"/>
    <div v-else-if="!results.artists.length && !results.tracks.length && !results.albums.length" class="note">Nothing found for “{{ term }}” in this snapshot.</div>
    <template v-else>
      <template v-if="results.tracks.length"><Sec>Tracks</Sec>
        <Row v-for="(r, i) in results.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="esc(r.artists)" :right="duration(r.dur)" :to="link('track', {id: r.id})"/></template>
      <template v-if="results.artists.length"><Sec>Artists</Sec>
        <div class="tiles"><Tile v-for="r in results.artists" :key="r.id" :img="r.img" :title="r.name" round :sub="number(r.followers) + ' followers'" :to="link('artist', {id: r.id})"/></div></template>
      <template v-if="results.albums.length"><Sec>Albums</Sec>
        <div class="tiles"><Tile v-for="r in results.albums" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div></template>
    </template></div>`,
});

const Artist = page({
  setup() {
    const state = loadItem("artist");
    const view = computed(() => {
      const a = state.data?.item;
      if (!a) return null;
      const stats = [["Followers", number(a.followers)], ["Popularity", a.pop ?? "—"], ["Viral city playlists", a.playlists]];
      if (a.listeners != null) stats.push(["Monthly listeners", number(a.listeners)]);
      let meta = badge(snap.value);
      if (a.prev) meta += ` &nbsp; popularity ${delta(a.pop - a.prev[0])} · followers ${delta(a.followers - a.prev[1])} since ${label(other.value)}`;
      const top = Math.max(1, ...a.cities.map((c) => c.listeners || 0));
      return { ...a, stats, meta, top };
    });
    return { state, view, id: route.params.id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Artists</p><p class="sub" v-html="'Pick one, or use Search · ' + badge(snap)"></p>
      <div class="tiles"><Tile v-for="r in state.data.list" :key="r.id" :img="r.img" :title="r.name" round :sub="number(r.followers) + ' followers'" :to="link('artist', {id: r.id})"/></div>
    </template>
    <div v-else-if="state.data.missing" class="note">This artist is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="view.img" kind="Artist" :name="view.name" :meta="view.meta" :stats="view.stats" round/>
      <div v-if="view.genres.length" style="margin-top:14px"><span v-for="g in view.genres" class="chip">{{ g }}</span></div>
      <div class="cols c32">
        <div><Sec small="tracks in the playlists and charts">Popular</Sec>
          <div v-if="!view.tracks.length" class="note">No tracks of this artist were collected in this snapshot.</div>
          <Row v-for="(r, i) in view.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name"
            :sub="r.playlists + ' playlists · ' + duration(r.dur)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/></div>
        <div><Sec>Listen</Sec><Embed kind="artist" :id="id" height="380"/></div>
      </div>
      <template v-if="view.albums.length"><Sec>Discography</Sec>
        <div class="tiles"><Tile v-for="r in view.albums" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div></template>
      <template v-if="view.similar.length">
        <Sec :small="view.similar_source === 'lastfm' ? 'Last.fm' : 'Spotify related artists (retired in 2024)'">Fans also like</Sec>
        <div class="tiles"><Tile v-for="r in view.similar" :key="r.id" :img="r.img" :title="r.name" round
          :sub="r.sim != null ? pct(r.sim) + ' similar' : 'Related'" :to="link('artist', {id: r.id})"/></div></template>
      <template v-if="view.cities.length"><Sec :small="view.cities[0].listeners ? 'monthly listeners by city' : 'Viral city playlists with this artist'">Where people listen</Sec>
        <Row v-for="(r, i) in view.cities" :key="i" :n="i + 1" :img="false" :title="r.name" :sub="esc(r.region) + ', ' + esc(r.country)"
          :right="r.listeners ? '<b>' + number(r.listeners) + '</b><span class=pop><i style=width:' + Math.round(100 * r.listeners / view.top) + '%></i></span>' : ''"/></template>
    </template></div>`,
});

const Album = page({
  setup() {
    const state = loadItem("album");
    const meta = computed(() => {
      const a = state.data?.item;
      return a && `<b>${esc(a.artists.map((x) => x.name).join(", "))}</b> · ${esc(a.date || "")} · ${a.count} tracks · ${badge(snap.value)}`;
    });
    return { state, meta, id: route.params.id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Albums</p><p class="sub" v-html="'Albums of the tracks in the playlists · ' + badge(snap)"></p>
      <div class="tiles"><Tile v-for="r in state.data.list" :key="r.id" :img="r.img" :title="r.name" :sub="r.year + ' · ' + esc(r.type)" :to="link('album', {id: r.id})"/></div>
    </template>
    <div v-else-if="state.data.missing" class="note">This album is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="state.data.item.img" :kind="state.data.item.type" :name="state.data.item.name" :meta="meta"
        :stats="[['Popularity', state.data.item.pop ?? '—']]"/>
      <div class="cols c32">
        <div><Sec>Listen</Sec><Embed kind="album" :id="id" height="420"/></div>
        <div>
          <template v-if="state.data.item.tracks.length"><Sec>In the playlists</Sec>
            <Row v-for="(r, i) in state.data.item.tracks" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="duration(r.dur)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/></template>
          <Sec>Artists</Sec>
          <Row v-for="r in state.data.item.artists" :key="r.id" n="" :img="r.img" :title="r.name" sub="Artist" round :to="link('artist', {id: r.id})"/>
        </div>
      </div>
    </template></div>`,
});

const Track = page({
  setup() {
    const state = loadItem("track");
    const view = computed(() => {
      const t = state.data?.item;
      if (!t) return null;
      const stats = [["Popularity", t.pop ?? "—"]];
      const daily = t.chart.daily;
      if (daily) stats.push(["Top 200 today", `#${daily.pos}`], ["Streams today", number(daily.streams)], ["Streams in Brazil", number(daily.total)]);
      if (t.plays != null) stats.push(["Plays", number(t.plays)]);
      const albumText = t.album ? ` · ${esc(t.album.name)} (${t.album.year})` : "";
      const meta = `<b>${esc(t.artists.map((a) => a.name).join(", "))}</b>${albumText} · ${duration(t.dur)}${t.explicit ? " · 🅴" : ""} · ${badge(snap.value)}`;
      return { ...t, stats, meta };
    });
    return { state, view, id: route.params.id };
  },
  template: `<div>
    <Err v-if="state.err" :err="state.err"/>
    <Loading v-else-if="!state.data"/>
    <template v-else-if="state.data.list">
      <p class="title">Tracks</p><p class="sub" v-html="'The most popular tracks in the playlists · ' + badge(snap)"></p>
      <Row v-for="(r, i) in state.data.list" :key="r.id" :n="i + 1" :img="r.img" :title="r.name" :sub="esc(r.artists)" :right="popBar(r.pop)" :to="link('track', {id: r.id})"/>
    </template>
    <div v-else-if="state.data.missing" class="note">This track is not in the {{ label(snap) }} snapshot. Try the other one in the switch above.</div>
    <template v-else>
      <Hero :img="view.img" kind="Track" :name="view.name" :meta="view.meta" :stats="view.stats"/>
      <div style="height:16px"></div>
      <Embed kind="track" :id="id"/>
      <div class="cols c23">
        <div><Sec>Artists</Sec>
          <Row v-for="r in view.artists" :key="r.id" n="" :img="r.img" :title="r.name" :sub="number(r.followers) + ' followers'" round :to="link('artist', {id: r.id})"/>
          <template v-if="view.album"><Sec>Album</Sec>
            <Row n="" :img="view.album.img || view.img" :title="view.album.name" :sub="view.album.year" :to="link('album', {id: view.album.id})"/></template></div>
        <div><Sec :small="view.cities.length + ' city playlists'">Viral in</Sec>
          <div v-if="!view.cities.length" class="note">Not in any Viral city playlist; it is here because of the Top 200 chart.</div>
          <span v-for="c in view.cities" class="chip">{{ c }}</span></div>
      </div>
    </template></div>`,
});

const AGE_BUCKETS = ["Same year", "1", "2–3", "4–5", "6–10", "11–20", "20+"];

const Compare = page({
  setup() {
    const state = load(async () => {
      const d = await json("compare.json");
      const a = d.profile[d.old], b = d.profile[d.new];
      const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
      d.stats = [
        ["Tracks", thousands(b.tracks), delta(b.tracks - a.tracks) + ` vs ${label(d.old)}`],
        ["Average length", mmss(b.seconds), delta(b.seconds - a.seconds, (v) => v.toFixed(0), "s")],
        ["Explicit tracks", pct(b.explicit), delta((b.explicit - a.explicit) * 100, (v) => v.toFixed(1), " pp")],
        ["Avg. track popularity", b.popularity.toFixed(0), delta(b.popularity - a.popularity, (v) => v.toFixed(1))],
      ];
      d.ageMax = Math.max(...Object.values(d.ages).flat());
      d.genreMax = Math.max(...d.genres.flatMap(([, v]) => Object.values(v)));
      return d;
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
      <Loading v-else-if="!state.data"/>
      <template v-else>
        <div style="height:6px"></div>
        <Stats :items="state.data.stats"/>
        <Sec small="release age when collected">How old are the songs?</Sec>
        <div class="bars">
          <div class="legend"><span><i class="c-old"></i>{{ label(state.data.old) }}</span><span><i class="c-new"></i>{{ label(state.data.new) }}</span></div>
          <div v-for="(b, i) in AGE_BUCKETS" class="bar-row"><span>{{ i === 0 ? b : b + ' yrs' }}</span><div>
            <div v-for="s in [state.data.old, state.data.new]" class="bar"><i :class="s === state.data.old ? 'c-old' : 'c-new'"
              :style="{width: 85 * state.data.ages[s][i] / state.data.ageMax + '%'}"></i>{{ pct(state.data.ages[s][i], 1) }}</div></div></div>
        </div>
        <template v-if="state.data.genres.length">
          <Sec small="share of genre tags of the artists in the playlists">Genres</Sec>
          <div class="bars">
            <div class="legend"><span><i class="c-old"></i>{{ label(state.data.old) }}</span><span><i class="c-new"></i>{{ label(state.data.new) }}</span></div>
            <div v-for="[g, v] in state.data.genres" class="bar-row"><span :title="g">{{ g }}</span><div>
              <div v-for="s in [state.data.old, state.data.new]" class="bar"><i :class="s === state.data.old ? 'c-old' : 'c-new'"
                :style="{width: 85 * v[s] / state.data.genreMax + '%'}"></i>{{ pct(v[s], 1) }}</div></div></div>
          </div>
        </template>
        <Sec small="not in any playlist before">New in {{ label(state.data.new) }}</Sec>
        <div class="tiles"><Tile v-for="r in state.data.arrived" :key="r.id" :img="r.img" :title="r.name" round :sub="r.playlists + ' playlists'" :to="link('artist', {id: r.id, snap: state.data.new})"/></div>
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
