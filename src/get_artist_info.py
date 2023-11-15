import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import psycopg2
import src.get_album_info as get_album_info


def get_insta_followers_livecounts_nl(username):
    response = requests.get(
        f"https://backend.mixerno.space/instagram/test/{username}",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    )
    if response.status_code == 200:
        followers = response.json()["user"]["followerCount"]
        print("livecounts nl", followers)
        return followers
    else:
        print("Error in request livecounts nl", response.status_code)
        return None


def get_insta_followers_instrack(username):
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


def get_insta_followers_tucktools(username):
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


def extract_socialmedia_followers(username: str, socialmedia: str,
                                  socialblade_cookie: str) -> int:
    # TODO: Encontrar forma de extrair o número de seguidores do facebook
    if socialmedia == "facebook":
        # # For now, do nothing for facebook.
        # response = requests.get(
        #     f"https://socialblade.com/facebook/page/{username}/",
        #     headers={
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        #         "Cookie": "PHPSESSXX=h22ofj9bn5e98ho1n3e8agn8u8",
        #         "Referer": "https://socialblade.com/"
        #     })
        # print("facebook", response.status_code)
        # if response.status_code != 200:
        #     print("Error in request socialblade")
        #     print(response.status_code)
        # html = BeautifulSoup(response.content, "html.parser")
        # paragraphs = html.find_all("p")
        # for paragraph in paragraphs:
        #     if "page likes" in paragraph.text:
        #         print(paragraph)
        #         # Extract digits from string
        #         likes = int("".join([ele for ele in
        #                              paragraph.text if ele.isdigit()]))
        #         print("facebook", likes)
        #         return likes
        pass
    # ! Get cookie every time we restart the kernel
    elif socialmedia in ["twitter"]:
        # https://livecounts.io/twitter-live-follower-counter/
        # https://socialcounts.org/twitter-live-follower-count/

        # Alternative:
        # https://socialcounts.org/_next/data/OynEq0Qj5drZPg6PG2EKL/twitter-live-follower-count/username.json?media=twitter-live-follower-count&id=username
        # [pageProps][counters][0]
        response = requests.get(
            f"https://api.livecounts.io/twitter-live-follower-counter/stats/{username}",
            headers={
                "Host": "api.livecounts.io",
                "Origin": "https://livecounts.io",
                "Referer": "https://livecounts.io/",
                "Sec-Fetch-Site": "cross-site",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
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


def save_socials_info(artist_id: str, links: list, connection):
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


def save_social_media_followers(connection, socialblade_cookie):
    # Select * from soc_redesocial where soc_seguidores = 0;
    cursor = connection.cursor()
    cursor.execute(
        f"""SELECT soc_art_codigo, soc_url, soc_tipo
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
                username, socialmedia, socialblade_cookie)
            print(
                f"Username: {username} Social: {socialmedia} Followers: {followers}",
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


def save_genres_info(artist_id, genres, connection, cursor):
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


def save_cities_info(artist_id, cities, connection, cursor):
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


    # for city in inserted_cities:
    #     # Get city from inserted_cities where city, country
    #     # and region match
    #     for top_city in cities:
    #         if top_city["city"] == city[1] and \
    #                 top_city["country"] == city[2] and \
    #                     top_city["region"] == city[3]:
    #             listeners = top_city["numberOfListeners"]

    #     cursor.execute(
    #         f"""INSERT INTO spotify.arc_artistacidade
    #         (arc_art_codigo, arc_cid_codigo, arc_ouvintes)
    #         VALUES
    #         ('{artist_id}', '{city[0]}', {listeners})
    #         ON CONFLICT (arc_art_codigo, arc_cid_codigo)
    #         DO NOTHING;
    #         """
    #     )
    #     connection.commit()

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


def save_artists_info(artist_ids: list, connection,
                      headers_api: str, headers_browser: str,
                      socialblade_cookie: str):

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
                        f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryArtistOverview&variables=%7B%22uri%22%3A%22spotify%3Aartist%3A{artist_id}%22%2C%22locale%22%3A%22intl-pt%22%2C%22includePrerelease%22%3Atrue%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%2235648a112beb1794e39ab931365f6ae4a8d45e65396d641eeda94e4003d41497%22%7D%7D",
                        headers=headers_browser)
                    if general_artist_info_response.status_code != 200:
                        print("Error in request general_artist_info_response")
                        print(general_artist_info_response.status_code)
                        print(general_artist_info_response.headers)
                    else:
                        general_artist_info_response = \
                            general_artist_info_response.json()["data"]["artistUnion"]

                    stats = general_artist_info_response["stats"]
                    artist_monthly_listeners = stats["monthlyListeners"]
                    if artist_monthly_listeners is None:
                        artist_monthly_listeners = 0

                    # Insert artist info
                    cursor.execute(
                        f"""INSERT INTO spotify.art_artista
                        (art_codigo, art_primeironome, art_ultimonome,
                        art_seguidores, art_popularidade, art_ouvintes)
                        VALUES
                        ('{artist_id}',
                        '{artist_name.split(' ')[0].replace("'", "")}',
                        '{" ".join(artist_name.split(" ")[1:]).replace("'", '')}',
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
                        f"https://api.spotify.com/v1/artists/{artist_id}/albums",
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


# TODO: Run this after all the artists are inserted in the database.
def save_related_artists_info(artist_id, connection, headers_api,
                              headers_browser, socialblade_cookie):
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
            f"\tFound {len(related_artists_ids)} related artists for {artist_id}.")
        save_artists_info(
            related_artists_ids, connection, headers_api, headers_browser,
            socialblade_cookie)
    else:
        print(f"\tAll related artists for {artist_id} already in the database.")

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
