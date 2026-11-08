"""Store latitude/longitude of the cities so the app does not geocode on
every page view. Run once: python -m src.geocode"""
import logging
import time

from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

from src import db

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    conn = db.connect()
    db.migrate(conn)
    geolocator = Nominatim(user_agent="spotify-scrapper-showcase")
    cities = conn.execute(
        "SELECT DISTINCT cid_nome, cid_regiao, cid_pais FROM cid_cidade "
        "WHERE cid_latitude IS NULL").fetchall()
    log.info("%d cities to geocode", len(cities))
    for name, region, country in cities:
        try:
            location = geolocator.geocode(
                ", ".join(p for p in (name, region, country) if p),
                timeout=10)
        except GeopyError as e:
            log.warning("%s: %s", name, e)
            location = None
        if location:
            conn.execute(
                "UPDATE cid_cidade SET cid_latitude = ?, cid_longitude = ? "
                "WHERE cid_nome = ? AND cid_regiao IS ? AND cid_pais IS ?",
                (location.latitude, location.longitude, name, region,
                 country))
            conn.commit()
        else:
            log.warning("Not found: %s, %s, %s", name, region, country)
        time.sleep(1)  # Nominatim usage policy: 1 request per second


if __name__ == "__main__":
    main()
