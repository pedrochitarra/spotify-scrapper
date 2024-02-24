"""Functions to get artist info from the Spotify API and save it in the
database. Also here are functions to get the number of followers from
social media and save it in the database."""
from typing import Union
import requests

import psycopg2

import src.get_album_info as get_album_info


def get_insta_followers_livecounts_nl(username: str) -> Union[int, None]:
    """Get the number of followers from the Instagram username using the
    livecounts.nl website.

    Args:
        username (str): Instagram username.
    Returns:
        int: Number of followers.
    """
    response = requests.get(
        f"https://backend.mixerno.space/instagram/test/{username}",
        headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/119.0.0.0 Safari/537.36")}
    )
    if response.status_code == 200:
        followers = response.json()["user"]["followerCount"]
        print("livecounts nl", followers)
        return followers
    else:
        print("Error in request livecounts nl", response.status_code)
        return None


def get_insta_followers_instrack(username: str) -> Union[int, None]:
    """Get the number of followers from the Instagram username using the
    instrack.app website.

    Args:
        username (str): Instagram username.
    Returns:
        int: Number of followers."""
    response = requests.get(
        f"https://instrack.app/api/account/{username}",
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://instrack.app/instagram/{username}/stats"
        }
    )
    if response.status_code == 200:
        followers = response.json()["followers_count"]
        print("instrack", followers)
        return followers
    else:
        print("Error in request instrack", response.status_code)
        return None


def get_insta_followers_tucktools(username: str) -> Union[int, None]:
    """Get the number of followers from the Instagram username using the
    tucktools.com website.

    Args:
        username (str): Instagram username.
    Returns:
        int: Number of followers.
    """
    response = requests.get(
        f"https://instaskull.com/tucktools_new?username={username}",
        headers={
            "Host": "instaskull.com",
            "Origin": "https://www.tucktools.com",
            "Referer": "https://www.tucktools.com/",
            "Sec-Fetch-Site": "cross-site"}
    )
    if response.status_code != 200:
        print("Error in request tucktools", response.status_code)
    response_json = response.json()
    print(response, username)
    if "code" in response_json and response_json["code"] == 404:
        print("Error in request response_json")
        followers = None
    elif "code" in response_json and response_json["code"] == 429:
        print(response.headers)
        followers = None
    else:
        followers = response_json["user_followers"]

    return followers


def extract_socialmedia_followers(username: str,
                                  socialmedia: str) -> Union[int, None]:
    """Extract the number of followers from the social media username.

    Args:
        username (str): Social media username.
        socialmedia (str): Social media name.
    Returns:
        int: Number of followers.
    """
    if socialmedia == "facebook":
        # # For now, do nothing for facebook.
        pass
    # ! Get cookie every time we restart the kernel
    elif socialmedia in ["twitter"]:
        response = requests.get(
            (f"https://api.livecounts.io/twitter-live-follower-counter"
             f"/stats/{username}"),
            headers={
                "Host": "api.livecounts.io",
                "Origin": "https://livecounts.io",
                "Referer": "https://livecounts.io/",
                "Sec-Fetch-Site": "cross-site",
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/119.0.0.0 Safari/537.36")}
        )
        if response.status_code != 200:
            print("Error in request response")
            print(response.status_code)
            return None
        else:
            response = response.json()
            followers = response["followerCount"]
            return followers

    elif socialmedia in ["instagram"]:
        # Try first with instrack
        followers = get_insta_followers_instrack(username)
        if followers is None:
            followers = get_insta_followers_livecounts_nl(username)
            # Try with livecounts.nl
            followers = get_insta_followers_livecounts_nl(username)
            if followers is None:
                # Try with tucktools
                followers = get_insta_followers_tucktools(username)

        return followers


def save_socials_info(artist_id: str, links: list,
                      connection: psycopg2.extensions.connection):
    """Save social media info in the database.

    Args:
        artist_id (str): Artist id from the Spotify API.
        links (list): List of social media links from the Spotify API.
        connection (psycopg2.extensions.connection): Connection to the
            database.
    """
    for external_link in links:
        social = external_link["name"].lower()

        # Insert social info
        cursor = connection.cursor()
        cursor.execute(
            f"""INSERT INTO spotify.soc_redesocial
            (soc_art_codigo, soc_url, soc_seguidores, soc_tipo)
            VALUES
            ('{artist_id}', '{external_link["url"]}', 0,
            '{social}')
            ON CONFLICT (soc_art_codigo, soc_tipo) DO NOTHING
            ;
            """
        )
        connection.commit()


def save_social_media_followers(connection: psycopg2.extensions.connection):
    """Save the number of followers from the social media in the database.

    Args:
        connection (psycopg2.extensions.connection): Connection to the
            database.
        socialblade_cookie (str): Cookie to make a request to the
            socialblade website.
    """
    cursor = connection.cursor()
    cursor.execute(
        """SELECT soc_art_codigo, soc_url, soc_tipo
        FROM spotify.soc_redesocial
        WHERE soc_seguidores = 0
        AND soc_tipo != 'facebook'
        AND soc_tipo != 'wikipedia'
        ORDER BY random();
        """
    )
    socials = cursor.fetchall()
    cursor.close()

    for social in socials:
        url = social[1]
        socialmedia = social[2]

        if "wikipedia" not in url:
            print(f"URL: {social[1]}")
            # Get string after ".com/"
            username = url.split(".com/")[1]
            username = username.split("/")[0]

            followers = extract_socialmedia_followers(
                username, socialmedia)
            print(
                f"Username: {username} Social: {socialmedia}",
                f"Followers: {followers}",
                f"URL: {social[1]}")
            if followers is not None:
                cursor = connection.cursor()
                cursor.execute(
                    f"""UPDATE spotify.soc_redesocial
                    SET soc_seguidores = {followers}
                    WHERE soc_art_codigo = '{social[0]}'
                    AND soc_tipo = '{social[2]}';
                    """
                )
            connection.commit()
            cursor.close()


def save_genres_info(artist_id: str, genres: list,
                     connection: psycopg2.extensions.connection,
                     cursor: psycopg2.extensions.cursor):
    """Save musical genres info in the database."""
    inserted_genres = []
    # TODO: Instead of using inserted genres, insert the genre and then find
    # its id by the name and save into the table.
    # Insert genres info
    for genre in genres:
        cursor.execute(
            f"""INSERT INTO spotify.gen_genero
            (gen_nome)
            VALUES
            ('{genre}')
            ON CONFLICT (gen_nome) DO NOTHING
            RETURNING gen_codigo;
            """
        )
        if cursor.rowcount > 0:
            inserted_genres.append(cursor.fetchone()[0])
        connection.commit()

    # Insert artists_genres info
    # Select genre by name
    for genre in genres:
        cursor.execute(
            f"""SELECT gen_codigo FROM spotify.gen_genero
            WHERE gen_nome = '{genre}';
            """
        )
        genre_id = cursor.fetchone()[0]
        cursor.execute(
            f"""INSERT INTO spotify.age_artistagenero
            (age_art_codigo, age_gen_codigo)
            VALUES
            ('{artist_id}', '{genre_id}')
            ON CONFLICT (age_art_codigo, age_gen_codigo) DO NOTHING;
            """
        )
        connection.commit()


def save_cities_info(artist_id: str, cities: list,
                     connection: psycopg2.extensions.connection,
                     cursor: psycopg2.extensions.cursor):
    """Save cities info and artists related in the database."""
    inserted_cities = []
    for city in cities:
        cursor.execute(
            f"""INSERT INTO spotify.cid_cidade
            (cid_nome, cid_pais, cid_regiao)
            VALUES
            ('{city['city']}', '{city['country']}',
            '{city['region']}')
            ON CONFLICT (cid_nome, cid_pais, cid_regiao)
            DO NOTHING
            RETURNING *;
            """
        )
        if cursor.rowcount > 0:
            inserted_cities.append(cursor.fetchone())
        connection.commit()

    # Insert artists_cities info
    # TODO: Instead of using inserted cities, insert the city and then find
    # its id by name, country and region and save into the table.
    for city in cities:
        cursor.execute(
            f"""SELECT cid_codigo FROM spotify.cid_cidade
            WHERE cid_nome = '{city['city']}'
            AND cid_pais = '{city['country']}'
            AND cid_regiao = '{city['region']}';
            """
        )
        city_id = cursor.fetchone()[0]
        cursor.execute(
            f"""INSERT INTO spotify.arc_artistacidade
            (arc_art_codigo, arc_cid_codigo, arc_ouvintes)
            VALUES
            ('{artist_id}', '{city_id}', {city['numberOfListeners']})
            ON CONFLICT (arc_art_codigo, arc_cid_codigo)
            DO NOTHING;
            """
        )
        connection.commit()


def save_artists_info(artist_ids: list,
                      connection: psycopg2.extensions.connection,
                      headers_api: dict, headers_browser: str):
    """Save artists info in the database. By the artist_ids, make a request
    to the API and save the info in the database defined in the connection
    parameter. The headers_api is the headers to make a request to the API.

    Args:
        artist_ids (list): List of artists ids from the Spotify API.
        connection (psycopg2.extensions.connection): Connection to the
            database.
        headers_api (dict): Headers to make a request to the API.
    """
    # For every 50 artists, concat the elements in a string with commas
    # and make a request to the API
    for i in range(0, len(artist_ids), 50):
        artists_ids_string = ",".join(artist_ids[i:i+50])
        artists_response = requests.get(
            f"https://api.spotify.com/v1/artists?ids={artists_ids_string}",
            headers=headers_api
        )

        if artists_response.status_code != 200:
            print("Error in request artists_response")
            print(artists_response.status_code)
            print(artists_response.headers)
        else:
            artists_response = artists_response.json()["artists"]

        for artist_response in artists_response:
            try:
                cursor = connection.cursor()
                artist_id = artist_response["id"]
                artist_name = artist_response["name"]
                artist_popularity = artist_response["popularity"]
                artist_followers = artist_response["followers"]["total"]

                print(f"Artist: {artist_id}")

                # Check if artist is already in the database
                cursor.execute(
                    f"""SELECT art_codigo FROM spotify.art_artista
                    WHERE art_codigo = '{artist_id}';
                    """
                )
                if cursor.rowcount > 0:
                    print(f"\t Artist {artist_id} already in the database.")
                elif cursor.rowcount == 0:
                    general_artist_info_response = requests.get(
                        (f"https://api-partner.spotify.com/pathfinder/v1/"
                         "query?operationName=queryArtistOverview&variables=%"
                         f"7B%22uri%22%3A%22spotify%3Aartist%3A{artist_id}%"
                         "22%2C%22locale%22%3A%22intl-pt%22%2C%22include"
                         "Prerelease%22%3Atrue%7D&extensions=%7B%22"
                         "persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha"
                         "256Hash%22%3A%2235648a112beb1794e39ab931365f6ae4a8d"
                         "45e65396d641eeda94e4003d41497%22%7D%7D"),
                        headers=headers_browser)
                    if general_artist_info_response.status_code != 200:
                        print("Error in request general_artist_info_response")
                        print(general_artist_info_response.status_code)
                        print(general_artist_info_response.headers)
                    else:
                        general_artist_info_response = \
                            general_artist_info_response.json()[
                                "data"]["artistUnion"]

                    stats = general_artist_info_response["stats"]
                    artist_monthly_listeners = stats["monthlyListeners"]
                    if artist_monthly_listeners is None:
                        artist_monthly_listeners = 0

                    # Insert artist info
                    art_ultimo_nome = " ".join(artist_name.split(
                        " ")[1:]).replace("'", '')
                    cursor.execute(
                        f"""INSERT INTO spotify.art_artista
                        (art_codigo, art_primeironome, art_ultimonome,
                        art_seguidores, art_popularidade, art_ouvintes)
                        VALUES
                        ('{artist_id}',
                        '{artist_name.split(' ')[0].replace("'", "")}',
                        '{art_ultimo_nome}',
                        {artist_followers},
                        {artist_popularity}, {artist_monthly_listeners})
                        ON CONFLICT (art_codigo) DO NOTHING;
                        """
                    )
                    connection.commit()

                    artist_genres = artist_response["genres"]
                    save_genres_info(
                        artist_id, artist_genres, connection, cursor)

                    # Insert cities info
                    cities = stats["topCities"]["items"]
                    save_cities_info(artist_id, cities, connection, cursor)

                    artist_albums_response = requests.get(
                        (f"https://api.spotify.com/v1/artists/"
                         f"{artist_id}/albums"),
                        headers=headers_api, params={"limit": 50, "offset": 0}
                    )
                    if artist_albums_response.status_code != 200:
                        print("Error in request artist_albums_response")
                        print(artist_albums_response.status_code)
                        print(artist_albums_response.headers)
                    else:
                        artist_albums_response = \
                            artist_albums_response.json()
                    albums_ids = [ele["id"] for ele in
                                  artist_albums_response["items"]]
                    while artist_albums_response["next"] is not None:
                        artist_albums_response = requests.get(
                            artist_albums_response["next"],
                            headers=headers_api).json()
                        albums_ids.extend(
                            [ele["id"] for ele in
                             artist_albums_response["items"]])

                    # If the album is not in the database, insert the album
                    # info.
                    get_album_info.save_albums_info(
                        albums_ids, connection, headers_api, headers_browser)

                    # Insert artists_albums info
                    for album_id in albums_ids:
                        cursor.execute(
                            f"""INSERT INTO spotify.aal_artistaalbum
                            (aal_art_codigo, aal_alb_codigo)
                            VALUES
                            ('{artist_id}', '{album_id}')
                            ON CONFLICT (aal_art_codigo, aal_alb_codigo)
                            DO NOTHING;
                            """
                        )
                        connection.commit()

                    profile = general_artist_info_response["profile"]
                    external_links = profile["externalLinks"]["items"]
                    save_socials_info(artist_id, external_links, connection)
            except ValueError as e:
                connection.rollback()
                print(e)
            finally:
                cursor.close()


def save_related_artists_info(artist_id: str,
                              connection: psycopg2.extensions.connection,
                              headers_api: dict,
                              headers_browser: dict):
    """Save related artists info in the database. By the artist_id, make a
    request to the API and save the info in the database defined in the
    connection parameter. The headers_api is the headers to make a request
    to the API. Run this after all the artists are inserted in the database."""
    cursor = connection.cursor()
    related_artists_response = requests.get(
        f"https://api.spotify.com/v1/artists/{artist_id}/related-artists",
        headers=headers_api
    ).json()["artists"]
    related_artists_ids = [ele["id"] for ele in related_artists_response]

    # Check which artists are already in the database
    cursor.execute(
        """
        SELECT art_codigo FROM spotify.art_artista;
        """
    )
    artists = cursor.fetchall()
    artists_ids = [artist[0] for artist in artists]

    related_artists_ids = set(related_artists_ids)
    # Keep the original list of related artists ids to save the relationship
    # between artists later.
    save_related_artists_ids = [ele for ele in related_artists_ids]
    artists_ids = set(artists_ids)
    related_artists_ids = related_artists_ids - artists_ids
    # Get the difference between the original list of related artists ids and
    # the artists already in the database.
    related_artists_ids = list(related_artists_ids)

    if len(related_artists_ids) > 0:
        print(
            (f"\tFound {len(related_artists_ids)} related "
             "artists for {artist_id}."))
        save_artists_info(
            related_artists_ids, connection, headers_api, headers_browser)
    else:
        print(
            f"\tAll related artists for {artist_id} already in the database.")

    print(f"\tSaving relationship between artists for artist {artist_id}.")
    for related_artist_id in save_related_artists_ids:
        # Insert artists_related info
        cursor.execute(
            f"""INSERT INTO spotify.aa_artistaartista
            (aa_art_a_codigo, aa_art_b_codigo)
            VALUES
            ('{artist_id}', '{related_artist_id}')
            ON CONFLICT (aa_art_a_codigo, aa_art_b_codigo)
            DO NOTHING;
            """
        )
        connection.commit()
    cursor.close()
