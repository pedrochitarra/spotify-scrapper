"""Collect Spotify data for Brazil into data/spotify.db.

Usage:
    python main.py                      # full run for the current month
    python main.py --coleta 2026-11     # resume/redo a specific coleta
    python main.py --steps charts tracks
    python main.py --discography        # also fetch every artist's albums

Each step only fetches what is still missing, so after an error (rate
limit, network) just run the same command again.
"""
import argparse
import datetime
import logging
import sys

from src import collect, db
from src.clients import Lastfm, SourceError, Spotify, load_credentials, \
    spotify_keys

STEPS = ["playlists", "playlist_tracks", "charts", "tracks", "albums",
         "artists", "similar", "counts"]

log = logging.getLogger("main")


def run(coleta: str, steps: list, discography: bool):
    creds = load_credentials()
    sp = Spotify(spotify_keys(creds))
    lastfm = Lastfm(creds["lastfm_api_key"]) \
        if creds.get("lastfm_api_key") else None

    conn = db.connect()
    db.migrate(conn)
    collect.start(conn, coleta)

    actions = {
        "playlists": lambda: collect.playlists(conn, sp, coleta),
        "playlist_tracks": lambda: collect.playlist_tracks(conn, sp, coleta),
        "charts": lambda: collect.charts(conn, coleta),
        "tracks": lambda: collect.tracks(conn, sp, coleta),
        "albums": lambda: collect.albums(conn, sp, coleta),
        "artists": lambda: collect.artists(conn, sp, coleta),
        "similar": lambda: collect.similar_artists(conn, lastfm, coleta)
        if lastfm else log.warning("No lastfm_api_key, skipping similar"),
        "counts": lambda: collect.artist_playlist_counts(conn, coleta),
    }
    for step in steps:
        log.info("== %s ==", step)
        actions[step]()
        if step == "artists" and discography:
            collect.discography(conn, sp, coleta)

    if steps == STEPS:
        collect.finish(conn, coleta)
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--coleta", default=datetime.date.today()
                        .strftime("%Y-%m"), help="YYYY-MM (default: today)")
    parser.add_argument("--steps", nargs="+", choices=STEPS, default=STEPS)
    parser.add_argument("--discography", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.coleta == db.LEGACY_COLETA:
        parser.error(f"{db.LEGACY_COLETA} is the archived 2023 data")
    try:
        run(args.coleta, args.steps, args.discography)
    except SourceError as e:
        log.error("%s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        log.warning("Interrupted. Progress is saved; run again to resume.")
        sys.exit(130)


if __name__ == "__main__":
    main()
