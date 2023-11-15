"""Script to execute all steps to gather information about songs in Spotify
and save in a database."""
import src.get_playlist_info as get_playlist_info
import src.get_track_info as get_track_info
import src.get_artist_info as get_artist_info
import requests
import json
import psycopg2


def main():
    """Execute all steps to gather information about songs in Spotify and save
    in a database."""
    # Scrap or not the playlists (this script will be executed many times,
    # but the playlists will not change)
    LOAD_PLAYLISTS = False
    # Load credentials
    with open("connection_credentials.json", "r") as f:
        connection_credentials = json.load(f)

    user = connection_credentials["user"]
    password = connection_credentials["password"]
    port = connection_credentials["port"]
    host = connection_credentials["host"]
    db_name = connection_credentials["db_name"]

    conn = psycopg2.connect(
        database=db_name, user=user, password=password,
        host=host, port=port
    )

    # Load spotify credentials and get token to execute requests
    LYRICS_CREDENTIALS = "get_lyrics_credentials.json" #23695
    TRACKS_CREDENTIALS = "get_tracks_credentials.json" #12198
    MUSICS_CREDENTIALS = "get_musics_credentials.json" #7643
    ALBUMS_CREDENTIALS = "get_albums_credentials.json" #16980
    DISCS_CREDENTIALS = "get_discs_credentials.json" #66752
    ARTISTS_CREDENTIALS = "get_artists_credentials.json" #71061
    with open(LYRICS_CREDENTIALS, "r") as f:
        spotify_credentials = json.load(f)

    token_response = requests.post("https://accounts.spotify.com/api/token",
                                   data=spotify_credentials).json()
    token = token_response["access_token"]

    # Requests directly to the API
    headers_api = {"Authorization": f"Bearer {token}"}

    with open("browser_credentials.json", "r") as f:
        browswe_credentials = json.load(f)
    # Requests to HTML page (get every time a new token)
    temporary_token = browswe_credentials["temporary_token"]
    headers_browser = {
        "Authorization": f"Bearer {temporary_token}"
    }

    # Load social blade credentials
    with open("socialblade_credentials.json", "r") as f:
        socialblade_credentials = json.load(f)

    socialblade_cookie = socialblade_credentials["cookie"]

    if LOAD_PLAYLISTS:
        get_playlist_info.save_playlists_info(conn, headers_api)

    # Select ply_codigo from playlists table
    cursor = conn.cursor()
    cursor.execute("SELECT ply_codigo FROM spotify.ply_playlist;")
    playlists = cursor.fetchall()
    cursor.close()

    for playlist in playlists:
        print(f"Playlist: {playlist[0]}")
        # Check if playlist was already saved
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT ply_scrapped FROM spotify.ply_playlist
            WHERE ply_codigo = '{playlist[0]}'
            AND ply_scrapped = TRUE;"""
        )
        ply_scrapped = cursor.fetchone()
        cursor.close()
        print("Playlist scrapped", ply_scrapped)

        # Check if there's a playlist that's not in artists_playlists table
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT count(1) FROM spotify.apy_artistaplaylist
            WHERE apy_ply_codigo = '{playlist[0]}';"""
        )
        apy_count = cursor.fetchone()[0]
        cursor.close()
        print("apy_count", apy_count)

        if apy_count == 0:
            playlist_id = playlist[0]
            tracks_response = requests.get(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                headers=headers_api,
                params={"limit": 50, "offset": 0}
            )

            # Select count from ply_playlist where ply_codigo = playlist_id
            # If the amount of tracks related to the playlist is the same as the
            # total number of tracks in the playlist, the playlist was already
            # saved and the script can continue to the next playlist.
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT count(1) FROM spotify.fxp_faixaplaylist
                WHERE fxp_ply_codigo = '{playlist_id}';"""
            )
            count = cursor.fetchone()[0]
            cursor.close()

            if tracks_response.status_code != 200:
                print("Error in request tracks_response")
                print(tracks_response.status_code)
                print(tracks_response.headers)
            else:
                tracks_response = tracks_response.json()
            tracks = tracks_response["items"]
            # Save tracks to file
            # tracks_test = [track["track"]["id"] for track in tracks]
            # with open("tracks.json", "w") as f:
            #     json.dump(tracks_test, f, indent=4)
            print("Total tracks:", tracks_response["total"])

            print("Count:", count, "Total", tracks_response["total"] - 1)

            if apy_count == 0:
                print("apy_count == 0")
                track_ids = [track["track"]["id"] for track in tracks
                            if track["track"]]

                while tracks_response["next"] is not None:
                    tracks_response = requests.get(
                        tracks_response["next"],
                        headers=headers_api).json()
                    track_ids.extend(
                        [ele["track"]["id"] for ele in tracks_response["items"]
                        if ele["track"]])

                # Get track info
                get_track_info.save_tracks_info(
                    track_ids, playlist_id, conn, headers_api, headers_browser,
                    socialblade_cookie)
            # Add 1 as tolerance to avoid reexecuting the script
            elif count >= tracks_response["total"] - 1:
                print(f"Playlist {playlist_id} already saved")
                # Update ply_scrapped
                cursor = conn.cursor()
                cursor.execute(
                    f"""UPDATE spotify.ply_playlist
                    SET ply_scrapped = TRUE
                    WHERE ply_codigo = '{playlist_id}';"""
                )
                conn.commit()
                cursor.close()

        elif ply_scrapped is not None:
            print(f"Playlist {playlist[0]} already scrapped")

    # # Save followers info
    # get_artist_info.save_social_media_followers(
    #     conn, socialblade_cookie
    # )

    # Save related artists info only for artists that are in playlists.
    # Selct artists that aren't in related artists table.
    cursor = conn.cursor()
    cursor.execute("""SELECT apy_art_codigo
                      from spotify.apy_artistaplaylist
                      where apy_art_codigo not in
                      (select aa.aa_art_a_codigo from
                       spotify.aa_artistaartista aa);
                   """)
    artists_ids = cursor.fetchall()
    artists_ids = [artist_id[0] for artist_id in artists_ids]
    for artist_id in artists_ids:
        print(f"\tGetting related artists info for artist {artist_id}")
        get_artist_info.save_related_artists_info(
            artist_id, conn, headers_api, headers_browser, socialblade_cookie
        )
    cursor.close()


# TODO: Calcular a quantidade de vezes de cada artista em cada playlist
# fazendo joins. Ao reexecutar varias vezes pode ter dado erro. Verificar.
if __name__ == "__main__":
    main()
