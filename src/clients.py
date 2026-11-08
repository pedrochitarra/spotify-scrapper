"""HTTP clients for the data sources: Spotify Web API, Last.fm and kworb."""
import json
import logging
import re
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json"
# Longest Retry-After we are willing to sleep through. Spotify sometimes
# answers with hours when an app is rate limited hard; better stop and resume.
MAX_RETRY_AFTER = 120


class SourceError(RuntimeError):
    """A data source failed in a way retrying will not fix."""


class RateLimited(SourceError):
    """The source asked us to wait longer than MAX_RETRY_AFTER."""


def load_credentials(path: Path = CREDENTIALS_PATH) -> dict:
    if not path.exists():
        raise SourceError(
            f"{path.name} not found. Create it with client_id, client_secret "
            "and (optionally) lastfm_api_key. See README.")
    with open(path, encoding="utf-8") as f:
        creds = json.load(f)
    keys = spotify_keys(creds)
    if not keys:
        raise SourceError(f"{path.name} has no client_id/client_secret")
    return creds


def spotify_keys(creds: dict) -> list:
    """Spotify keys: the top-level pair plus any in "spotify_keys"."""
    keys = list(creds.get("spotify_keys", []))
    if "client_id" in creds and "client_secret" in creds:
        keys.insert(0, {"client_id": creds["client_id"],
                        "client_secret": creds["client_secret"]})
    return [k for k in keys if k.get("client_id") and k.get("client_secret")]


def _request(session: requests.Session, method: str, url: str,
             retries: int = 5, **kwargs) -> requests.Response:
    """Send a request, retrying network errors, 429 and 5xx responses."""
    for attempt in range(1, retries + 1):
        try:
            response = session.request(method, url, timeout=30, **kwargs)
        except requests.RequestException as e:
            wait = 2 ** attempt
            log.warning("%s %s failed (%s), retry in %ds", method, url, e,
                        wait)
            time.sleep(wait)
            continue

        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 2 ** attempt))
            if wait > MAX_RETRY_AFTER:
                raise RateLimited(
                    f"Rate limited for {wait}s by {url.split('/')[2]}. "
                    "Run again later; progress is saved.")
            log.warning("Rate limited, sleeping %ds", wait)
            time.sleep(wait + 1)
            continue
        if response.status_code >= 500:
            wait = 2 ** attempt
            log.warning("%s on %s, retry in %ds", response.status_code, url,
                        wait)
            time.sleep(wait)
            continue
        return response
    raise SourceError(f"Giving up on {url} after {retries} attempts")


class Spotify:
    API = "https://api.spotify.com/v1/"

    def __init__(self, keys: list):
        """keys: [{client_id, client_secret}]. When one key gets rate
        limited the next one is used. Keys from the same developer account
        share one quota, so only keys from different accounts help."""
        if not keys:
            raise SourceError("No Spotify keys")
        self._keys = keys
        self._key = 0
        self._session = requests.Session()
        self._expires_at = 0.0

    def _refresh_token(self):
        key = self._keys[self._key]
        response = _request(self._session, "POST",
                            "https://accounts.spotify.com/api/token",
                            data={"grant_type": "client_credentials", **key})
        if response.status_code != 200:
            raise SourceError(
                f"Spotify authentication failed ({response.status_code}): "
                f"{response.text[:200]}")
        body = response.json()
        self._session.headers["Authorization"] = \
            f"Bearer {body['access_token']}"
        self._expires_at = time.time() + body["expires_in"] - 60

    def get(self, path: str, **params):
        """GET an API path. Returns the JSON body, or None on 404."""
        while True:
            try:
                return self._get(path, **params)
            except RateLimited as e:
                if self._key + 1 >= len(self._keys):
                    raise
                self._key += 1
                self._expires_at = 0.0
                log.warning("%s Switching to Spotify key %d/%d", e,
                            self._key + 1, len(self._keys))

    def _get(self, path: str, **params):
        if time.time() >= self._expires_at:
            self._refresh_token()
        url = path if path.startswith("http") else self.API + path
        response = _request(self._session, "GET", url, params=params or None)
        if response.status_code == 401:
            self._refresh_token()
            response = _request(self._session, "GET", url,
                                params=params or None)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise SourceError(f"Spotify {response.status_code} on {url}: "
                              f"{response.text[:200]}")
        return response.json()

    def paginate(self, path: str, **params):
        """Yield every item of a paginated endpoint."""
        page = self.get(path, **params)
        while page:
            yield from (item for item in page["items"] if item)
            page = self.get(page["next"]) if page.get("next") else None

    def several(self, kind: str, ids: list, size: int):
        """Fetch tracks/albums/artists in batches. Yields found objects."""
        for i in range(0, len(ids), size):
            body = self.get(kind, ids=",".join(ids[i:i + size]))
            if body:
                yield from (obj for obj in body[kind] if obj)


class Lastfm:
    API = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str):
        self._key = api_key
        self._session = requests.Session()

    def similar_artists(self, name: str, limit: int = 20) -> list:
        """Return [(name, match)] of artists similar to name."""
        response = _request(self._session, "GET", self.API, params={
            "method": "artist.getsimilar", "artist": name, "limit": limit,
            "autocorrect": 1, "api_key": self._key, "format": "json"})
        body = response.json() if response.ok else {}
        if "error" in body or not response.ok:
            log.debug("Last.fm has no similar artists for %s", name)
            return []
        return [(a["name"], float(a["match"]))
                for a in body.get("similarartists", {}).get("artist", [])]


# Daily and weekly pages have different columns; these exist in both.
KWORB_REQUIRED = {"Pos", "Streams", "Total"}


def kworb_chart(kind: str = "daily", country: str = "br") -> tuple:
    """Parse a Spotify country chart mirrored by kworb.net.

    Returns (chart_date, [{position, track_id, streams, total_streams}]).
    """
    url = f"https://kworb.net/spotify/country/{country}_{kind}.html"
    response = _request(requests.Session(), "GET", url)
    if response.status_code != 200:
        raise SourceError(f"kworb {response.status_code} on {url}")
    response.encoding = "utf-8"
    html = response.text

    header = re.findall(r"<th(?:\s[^>]*)?>(.*?)</th>", html)
    if not KWORB_REQUIRED <= set(header):
        raise SourceError(f"kworb page layout changed at {url}: {header}")

    date = re.search(r"Chart - [^-]+ - (\d{4}/\d{2}/\d{2})", html)
    rows = []
    for tr in re.findall(r"<tr(?:\s[^>]*)?>(.*?)</tr>", html, re.S):
        track = re.search(r"track/([A-Za-z0-9]{22})", tr)
        if not track:
            continue
        cells = [re.sub(r"<[^>]+>", "", c).replace(",", "").strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        rows.append({
            "position": int(row["Pos"]),
            "track_id": track.group(1),
            "streams": _to_int(row["Streams"]),
            "total_streams": _to_int(row["Total"]),
        })
    if not rows:
        raise SourceError(f"kworb page layout changed, no rows at {url}")
    return (date.group(1).replace("/", "-") if date else None), rows


def _to_int(value: str):
    return int(value) if value.isdigit() else None
