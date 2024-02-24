"""Script to gather information about popular playlists in Brazil from
Spotify API and insert into a database."""
import requests

import pandas as pd
import psycopg2


def save_playlists_info(connection: psycopg2.extensions.connection,
                        headers_api: dict):
    """Get information about popular playlists in Brazil from Spotify API and
    insert into a database."""
    # Get The Sounds of Spotify Cities playlists. It gathers many cities around
    # the world and the most popular songs in each city
    user_id = "thesoundsofspotifycities"
    sounds_cities = requests.get(
        f"https://api.spotify.com/v1/users/{user_id}/playlists",
        headers=headers_api,
        params={"limit": 50}
    ).json()

    df_cities_playlists = pd.DataFrame()
    df_cities_playlists["ply_codigo"] = None
    df_cities_playlists["ply_nome"] = None
    # The request returns only 50 playlists at a time. To get all playlists, we
    # need to make requests with offset. The total playlists are 8120.
    for offset in range(0, 8300, 50):
        sounds_cities = requests.get(
            f"https://api.spotify.com/v1/users/{user_id}/playlists",
            headers=headers_api,
            params={"limit": 50, "offset": offset}
        ).json()
        for playlist in sounds_cities["items"]:
            # Keep only playlists with "viral" in the name and ending in "BR"
            if ("viral" in playlist["name"].lower() and
                    playlist["name"].endswith("BR")):
                df_cities_playlists = pd.concat([
                    df_cities_playlists,
                    pd.DataFrame({
                        "ply_codigo": [playlist["id"]],
                        "ply_nome": [playlist["name"]]
                    }, index=[0])
                ])

    # Add the most popular playlists in Brazil

    # Playlist top50 Brasil
    TOP50_BRASIL_ID = "37i9dQZEVXbMXbN3EUUhlg"
    top50_brasil_response = requests.get(
        f"https://api.spotify.com/v1/playlists/{TOP50_BRASIL_ID}",
        headers=headers_api
    ).json()

    # Playlist top Brasil
    TOP_BRASIL_ID = "37i9dQZF1DX0FOF1IUWK1W"
    top_brasil_response = requests.get(
        f"https://api.spotify.com/v1/playlists/{TOP_BRASIL_ID}",
        headers=headers_api
    ).json()

    # Playlist Viral Brasil
    VIRAL_BRASIL_ID = "37i9dQZEVXbMOkSwG072hV"
    viral_brasil_response = requests.get(
        f"https://api.spotify.com/v1/playlists/{VIRAL_BRASIL_ID}",
        headers=headers_api
    ).json()

    df_cities_playlists = pd.concat([
        df_cities_playlists,
        pd.DataFrame({
            "ply_codigo": [TOP50_BRASIL_ID],
            "ply_nome": [top50_brasil_response["name"]]
        }, index=[0])
    ])

    df_cities_playlists = pd.concat([
        df_cities_playlists,
        pd.DataFrame({
            "ply_codigo": [TOP_BRASIL_ID],
            "ply_nome": [top_brasil_response["name"]]
        }, index=[0])
    ])

    df_cities_playlists = pd.concat([
        df_cities_playlists,
        pd.DataFrame({
            "ply_codigo": [VIRAL_BRASIL_ID],
            "ply_nome": [viral_brasil_response["name"]]
        }, index=[0])
    ])

    df_cities_playlists["ply_descricao"] = None
    df_cities_playlists["ply_seguidores"] = None
    df_cities_playlists.reset_index(drop=True, inplace=True)
    for i, row in df_cities_playlists.iterrows():
        playlist_id = row["ply_codigo"]
        playlist_response = requests.get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}",
            headers=headers_api
        ).json()
        df_cities_playlists.loc[
            i, "ply_descricao"] = playlist_response["description"]
        df_cities_playlists.loc[
            i, "ply_seguidores"] = playlist_response["followers"]["total"]

    # Batch insert into database
    try:
        table_name = "ply_playlist"
        df_columns = df_cities_playlists.columns.to_list()
        values_list = [tuple(row) for row in
                       df_cities_playlists.to_numpy()]
        insert_query = f"""INSERT INTO spotify.{table_name}
                        ({', '.join(df_columns)})
                        VALUES ({', '.join(['%s' for _ in df_columns])})
                        ON CONFLICT (ply_codigo) DO NOTHING;
                        """
        cursor = connection.cursor()
        cursor.executemany(insert_query, values_list)
        connection.commit()
    except ValueError as e:
        print(e)
        connection.rollback()
    finally:
        cursor.close()
