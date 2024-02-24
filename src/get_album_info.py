"""Save albums info in the database."""
import requests

import psycopg2


def save_albums_info(albums_ids: list,
                     connection: psycopg2.extensions.connection,
                     headers_api: dict):
    """Save albums info in the database. By the albums_ids, make a request
    to the API and save the info in the database defined in the connection
    parameter. The headers_api is the headers to make a request to the API.

    Args:
        albums_ids (list): List of albums ids from the Spotify API.
        connection (psycopg2.extensions.connection): Connection to the
            database.
        headers_api (dict): Headers to make a request to the API.
    """
    # For every 20 albums, concat the elements in a string with commas
    # and make a request to the API
    for i in range(0, len(albums_ids), 20):
        albums_ids_string = ",".join(albums_ids[i:i+20])
        albums_response = requests.get(
            f"https://api.spotify.com/v1/albums?ids={albums_ids_string}",
            headers=headers_api
        )
        if albums_response.status_code != 200:
            print("Error in request albums_response")
            print(albums_response.status_code)
            print(albums_response.headers)
        else:
            albums_response = albums_response.json()["albums"]

        for album_response in albums_response:
            album_id = album_response["id"]
            album_type = album_response["album_type"]
            album_name = album_response["name"]
            album_popularity = album_response["popularity"]
            album_release_date = album_response["release_date"]
            album_total_tracks = album_response["total_tracks"]

            # If the release date is only the year, add "-01-01" to the end
            if len(album_release_date) == 4:
                album_release_date += "-01-01"

            if album_release_date == "0000-01-01":
                album_release_date = "2000-01-01"

            # Insert album info
            try:
                cursor = connection.cursor()
                cursor.execute(
                    f"""INSERT INTO spotify.alb_album
                    (alb_codigo, alb_nome, alb_lancamento, alb_tipo,
                    alb_qtdmusicas, alb_popularidade)
                    VALUES
                    ('{album_id}', '{album_name.replace("'", "")}',
                    '{album_release_date}',
                    '{album_type}', {album_total_tracks}, {album_popularity})
                    ON CONFLICT (alb_codigo) DO NOTHING;
                    """
                )
                connection.commit()
            except ValueError as e:
                print(e)
                connection.rollback()
            finally:
                cursor.close()
