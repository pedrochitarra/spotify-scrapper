"""Functions to get and save track info from Spotify API."""
import requests

import psycopg2

import src.get_artist_info as get_artist_info
import src.get_album_info as get_album_info


def insert_artist_playlist(connection: psycopg2.extensions.connection,
                           cursor: psycopg2.extensions.cursor,
                           playlist_id: str, artist_id: str):
    """Insert artist and the playlist relationship in the database.

    Args:
        connection: psycopg2.extensions.connection: Connection to
            the database.
        cursor: psycopg2.extensions.cursor: Cursor to execute
            commands in the database.
        playlist_id: str: Playlist id.
        artist_id: str: Artist id.
    """
    cursor.execute(
        f"""SELECT * FROM spotify.apy_artistaplaylist
        WHERE apy_art_codigo = '{artist_id}'
        AND apy_ply_codigo = '{playlist_id}';
        """
    )
    apy_artistaplaylist = cursor.fetchall()
    if len(apy_artistaplaylist) == 0:
        # Insert the artist in the playlist
        cursor.execute(
            f"""INSERT INTO spotify.apy_artistaplaylist
            (apy_art_codigo, apy_ply_codigo, apy_quantidade)
            VALUES
            ('{artist_id}', '{playlist_id}', 1);
            """
        )
        connection.commit()
    else:
        # Update the artist in the playlist
        cursor.execute(
            f"""UPDATE spotify.apy_artistaplaylist
            SET apy_quantidade = apy_quantidade + 1
            WHERE apy_art_codigo = '{artist_id}'
            AND apy_ply_codigo = '{playlist_id}';
            """
        )
        connection.commit()


def save_tracks_info(track_ids: str, playlist_id: str,
                     connection: psycopg2.extensions.connection,
                     headers_api: dict,
                     headers_browser: dict, socialblade_cookie: str):
    """Save tracks info into the database.

    Args:
        track_ids: str: List of track ids.
        playlist_id: str: Playlist id.
        connection: psycopg2.extensions.connection: Connection to
            the database.
        headers_api: dict: Headers to make requests to the Spotify API.
        headers_browser: dict: Headers to make requests to the Spotify
            API.
        socialblade_cookie: str: Cookie to make requests to the
            SocialBlade API.
    """
    # For every 50 tracks, concat the elements in a string with commas
    # and make a request to the API
    for i in range(0, len(track_ids), 50):
        track_ids_string = ",".join(track_ids[i:i+50])
        tracks_response = requests.get(
            f"https://api.spotify.com/v1/tracks?ids={track_ids_string}",
            headers=headers_api
        )
        if tracks_response.status_code != 200:
            print("Error in request tracks_response")
            print(tracks_response.status_code)
            print(tracks_response.headers)
        else:
            tracks_response = tracks_response.json()["tracks"]

        for track_response in tracks_response:
            try:
                cursor = connection.cursor()
                track_id = track_response["id"]
                print(f"Track: {track_id}")
                track_name = track_response["name"]
                track_popularity = track_response["popularity"]
                track_duration = track_response["duration_ms"]
                track_explicit = track_response["explicit"]
                track_artists_ids = [ele["id"] for ele in
                                     track_response["artists"]]

                # Check if track is already in the database
                cursor.execute(
                    f"""SELECT fai_codigo FROM spotify.fai_faixa
                    WHERE fai_codigo = '{track_id}';
                    """
                )
                if cursor.rowcount > 0:
                    print(f"\t Track {track_id} already in the database.")

                    # Even if the track is already in the database, the artists
                    # may not be.
                    cursor.execute(
                        f"""SELECT afx_art_codigo FROM spotify.afx_artistafaixa
                        WHERE afx_fai_codigo = '{track_id}';
                        """
                    )
                    artists_ids = cursor.fetchall()
                    artists_ids = [ele[0] for ele in artists_ids]
                    artists_ids = set(artists_ids)
                    artists_ids = list(artists_ids)
                    # Even if there's info about artist_track, the artist may
                    # not be in artist_playlist
                    for artist_id in artists_ids:
                        print(
                            (f"\t Inserting artist {artist_id} "
                             "into artist_playlist"))
                        # Insert artists_playlists info
                        insert_artist_playlist(
                            connection, cursor, playlist_id, artist_id)

                elif cursor.rowcount == 0:
                    # Gather info from browser in order to get the playcount
                    general_track_info = requests.get(
                        ("https://api-partner.spotify.com/pathfinder/v1/query"
                         "?operationName=getTrack&variables=%7B%22uri%22%3A"
                         f"%22spotify%3Atrack%3A{track_id}%22%7D&extensions=%"
                         "7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22"
                         "sha256Hash%22%3A%22e101aead6d78faa11d75bec5e36385a07"
                         "b2f1c4a0420932d374d89ee17c70dd6%22%7D%7D"),
                        headers=headers_browser)

                    if general_track_info.status_code != 200:
                        print("Error in request general_track_info")
                        print(general_track_info.status_code)
                        print(general_track_info.headers)
                    else:
                        general_track_info = general_track_info.json()[
                            "data"]["trackUnion"]

                    play_count = general_track_info["playcount"]

                    # Insert track info
                    cursor.execute(
                        f"""INSERT INTO spotify.fai_faixa
                        (fai_codigo, fai_nome, fai_explicita, fai_popularidade,
                        fai_duracao, fai_reproducoes)
                        VALUES
                        ('{track_id}', '{track_name.replace("'", '')}',
                        {track_explicit}, {track_popularity}, {track_duration},
                        {play_count})
                        ON CONFLICT (fai_codigo) DO NOTHING;
                        """
                    )
                    connection.commit()

                    # Insert artists info
                    get_artist_info.save_artists_info(
                        track_artists_ids, connection, headers_api,
                        headers_browser, socialblade_cookie)

                    # Main artist
                    main_artist_id = general_track_info[
                        "firstArtist"]["items"][0]["id"]

                    # Even if the track is already in the database, the artists
                    # may not be. Also, we need to update the artists_playlists
                    # table
                    for artist_id in track_artists_ids:
                        is_main_artist = artist_id == main_artist_id
                        # Insert artists_tracks info
                        cursor.execute(
                            f"""INSERT INTO spotify.afx_artistafaixa
                            (afx_art_codigo, afx_fai_codigo, afx_principal)
                            VALUES
                            ('{artist_id}', '{track_id}', {is_main_artist})
                            ON CONFLICT (afx_art_codigo, afx_fai_codigo)
                            DO NOTHING;
                            """
                        )
                        connection.commit()

                        # Insert artists_playlists info
                        insert_artist_playlist(
                            connection, cursor, playlist_id, artist_id)

                album_id = track_response["album"]["id"]
                # Check if album is already in the database
                cursor.execute(
                    f"""SELECT alb_codigo FROM spotify.alb_album
                    WHERE alb_codigo = '{album_id}';
                    """
                )
                if cursor.rowcount > 0:
                    print(f"\t Album {album_id} already in the database.")
                elif cursor.rowcount == 0:
                    # Insert album info
                    get_album_info.save_albums_info(
                        [album_id], connection, headers_api, headers_browser)

                # Even if the track is already in the database, the
                # tracks_albums table may not be updated
                # Insert tracks_albums info
                cursor.execute(
                    f"""INSERT INTO spotify.fal_faixaalbum
                    (fal_fai_codigo, fal_alb_codigo)
                    VALUES
                    ('{track_id}', '{album_id}')
                    ON CONFLICT (fal_fai_codigo, fal_alb_codigo)
                    DO NOTHING;
                    """
                )
                connection.commit()

                # Even if the track is already in the database, the
                # tracks_playlists table may not be updated
                # Insert tracks_playlists info
                cursor.execute(
                    f"""INSERT INTO spotify.fxp_faixaplaylist
                    (fxp_fai_codigo, fxp_ply_codigo)
                    VALUES
                    ('{track_id}', '{playlist_id}')
                    ON CONFLICT (fxp_fai_codigo, fxp_ply_codigo)
                    DO NOTHING;
                    """
                )
                connection.commit()

            except ValueError as e:
                print(e)
                connection.rollback()
            finally:
                cursor.close()
