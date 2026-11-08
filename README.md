<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="https://play-lh.googleusercontent.com/cShys-AmJ93dB0SV8kE6Fl5eSaf4-qMMZdwEDKI5VEmKAXfzOqbiaeAsqqrEBCTdIEs=w240-h480-rw" alt="Spotify Logo"></a>
</p>

<h3 align="center">Spotify Scrapper</h3>

<p align="center"> Project aimed to learn web scraping techniques, data extraction from the Spotify platform and
    data visualization using Streamlit.
    <br> 
</p>

## 🧐 About <a name = "about"></a>
Welcome to the Spotify Scraper repository, an educational resource designed to provide insight into web scraping techniques and data extraction from the Spotify platform. This repository serves as a learning tool for individuals interested in understanding how to programmatically access and retrieve information from Spotify's vast database of music tracks, albums, artists, and playlists.

## You can check a webapp for the data scrapped at [Spotify Scraper](https://spotify-showcase.streamlit.app/).

<span style="color:red;"> ⚠️ Disclaimer: The data can contain some bad words and inappropriate names, since it's the name of the musics and artists, so be aware of that. </span>

## 📅 Snapshots
The database keeps every collection side by side, identified by the `coleta`
column (`YYYY-MM`) present in every table:

| Snapshot | Sources | Notes |
|---|---|---|
| `2023-11` (archive) | Spotify Web API, unofficial web player endpoints, editorial playlists | Has plays per track, listeners per city and Spotify related artists. |
| `2026-11` | Spotify Web API, [kworb.net](https://kworb.net/spotify/country/br_daily.html) Top 200 Brazil, [Last.fm](https://www.last.fm/api) similar artists | Spotify retired related artists and editorial playlist access for new apps in 2024; plays and city listeners are no longer collected. |

The app has a snapshot selector and an overview comparing artists present in both.

## 🏁 Getting Started
1. Install the dependencies: `pip install -r requirements.txt`
2. Create a Spotify app at the [developer dashboard](https://developer.spotify.com/dashboard)
   (Web API, redirect URI `http://127.0.0.1:8888/callback`) and, optionally, a
   [Last.fm API account](https://www.last.fm/api/account/create).
3. Create `credentials.json` in the project root (ignored by git):

```json
{
  "client_id": "...",
  "client_secret": "...",
  "lastfm_api_key": "...",
  "spotify_keys": [{"client_id": "...", "client_secret": "..."}]
}
```

`spotify_keys` is optional: extra keys are used when the first one gets rate
limited. Since July 2026 Spotify counts quota per developer account, so only
keys from different accounts add capacity.

4. Collect: `python main.py` (current month) or `python main.py --coleta 2026-11`.
   Every step only fetches what is missing, so after an error run it again to resume.
   `--steps` runs specific steps, `--discography` also fetches every artist's albums.
5. Optional, once: `python -m src.geocode` stores city coordinates for the map.
6. Run the app: `streamlit run frontend.py`

## 📜 Structure
- `main.py`: command line entry point for the collection.
- `src/clients.py`: Spotify, Last.fm and kworb clients with retries, backoff and key rotation.
- `src/collect.py`: collection steps (playlists, playlist tracks, charts, tracks, albums, artists, similar artists, artist/playlist counts).
- `src/db.py`: SQLite schema and migration of the 2023 data.
- `frontend.py`, `pages/`: Streamlit app.
- `data/spotify.db`: the database. `data/*.sql`: original 2023 PostgreSQL dumps.

This repository is for educational purposes; respect the
[Spotify Developer Terms](https://developer.spotify.com/terms).
