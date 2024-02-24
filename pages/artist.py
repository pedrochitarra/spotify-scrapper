"""Page to show the artist's information."""
import requests

import streamlit as st
import sqlite3
from geopy.geocoders import Nominatim
import pandas as pd


st.title('Artists')

# Connect to the database
conn = sqlite3.connect('data/spotify.db')
cursor = conn.cursor()

# Get the artists
cursor.execute("""SELECT art_codigo, art_primeironome, art_ultimonome
               FROM art_artista;""")

# cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

artists = cursor.fetchall()
# st.write(artists)

# Select the artist
artist = st.selectbox(
    'Select an artist', artists,
    format_func=lambda x: x[1] + " " + x[2] if x[2] else x[1])

st.write(artist[0])

# Get the artist's info
cursor.execute(f"""SELECT *
                FROM art_artista
                WHERE art_codigo = '{artist[0]}';""")
artist_info = cursor.fetchone()

artist_genre_info = cursor.execute(
    f"""
    WITH numbered_gen_genero AS (
        SELECT
            gen_nome,
            ROW_NUMBER() OVER () AS gen_num
        FROM gen_genero
    )
    SELECT gen_nome from numbered_gen_genero
    INNER JOIN age_artistagenero
    ON numbered_gen_genero.gen_num = age_artistagenero.age_gen_codigo
    INNER JOIN art_artista
    ON age_artistagenero.age_art_codigo = art_artista.art_codigo
    WHERE age_art_codigo = '{artist[0]}';
    """).fetchall()
artist_genres = [genre[0] for genre in artist_genre_info]

st.header("Artist Info")

image_artist_col, text_info_col = st.columns(2)

with image_artist_col:

    # Request the browser information
    browser_info = requests.get(
        ("https://open.spotify.com/oembed?url="
         f"https://open.spotify.com/artist/{artist_info[0]}"),
        headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/119.0.0.0 Safari/537.36")})
    artist_image = browser_info.json()["thumbnail_url"]
    st.image(artist_image, width=300, use_column_width="auto")

with text_info_col:
    artist_full_name = (artist_info[1] + " " + artist_info[2] if
                        artist_info[2] else artist_info[1])
    st.subheader(artist_full_name)
    formatted_followers = "{:,}".format(artist_info[3])
    st.metric("Followers", formatted_followers)
    st.metric("Popularity (from 100)", artist_info[4])
    formatted_listeners = "{:,}".format(artist_info[5])
    st.metric("Listeners", formatted_listeners)
    st.subheader("Genres")
    for genre in artist_genres:
        st.write(genre.capitalize())

st.subheader("Cities with the most listeners")
cities = cursor.execute(
    f"""
    WITH numbered_cid_cidade AS (
        SELECT
            *, ROW_NUMBER() OVER () AS cid_num
            FROM cid_cidade
    )
    SELECT cid_nome, cid_pais, cid_regiao, arc_ouvintes FROM
    numbered_cid_cidade
    INNER JOIN arc_artistacidade
    ON numbered_cid_cidade.cid_num = arc_artistacidade.arc_cid_codigo
    INNER JOIN art_artista
    ON art_artista.art_codigo = arc_artistacidade.arc_art_codigo
    WHERE art_artista.art_codigo = '{artist[0]}'
    """).fetchall()


def get_geolocation(city_name):
    geolocator = Nominatim(user_agent="Geopy Library")
    location = geolocator.geocode(city_name)
    return location


cities_df = pd.DataFrame(cities,
                         columns=["City", "Country", "Region", "Listeners"])

# ! COMMENTED, because it takes too long to run
# cities_df["latitude"] = None
# cities_df["longitude"] = None

# for i, city in cities_df.iterrows():
#     # st.write(city)
#     city_name = f"{city['City'], city['Region'], city['Country']}"
#     local = get_geolocation(city_name)
#     # st.write(local)
#     cities_df.at[i, "latitude"] = local.latitude
#     cities_df.at[i, "longitude"] = local.longitude

# cities_df_show_case = pd.DataFrame()
# cities_df_show_case["City"] = cities_df.apply(
#     lambda x: f"{x['City']}, {x['Region']}, {x['Country']}", axis=1)
# cities_df_show_case["Listeners"] = cities_df["Listeners"]
# st.dataframe(cities_df_show_case, hide_index=True)

# # Normalize to 100 the listeners
# cities_df["Listeners"] = (100_000 * cities_df["Listeners"] /
#                           cities_df["Listeners"].max())
# st.map(cities_df, size="Listeners", use_container_width=True)
# ! COMMENTED, because it takes too long to run

st.subheader("Top tracks")
st.write(artist[0])
top_tracks = cursor.execute(
    f"""
    SELECT fai_codigo, fai_nome, fai_popularidade, fai_reproducoes
    FROM fai_faixa
    INNER JOIN afx_artistafaixa
    ON afx_artistafaixa.afx_fai_codigo = fai_faixa.fai_codigo
    INNER JOIN art_artista
    ON art_artista.art_codigo = afx_artistafaixa.afx_art_codigo
    WHERE afx_artistafaixa.afx_art_codigo = '{artist[0]}'
    ORDER BY fai_popularidade DESC
    LIMIT 5;
    """).fetchall()
top_tracks_df = pd.DataFrame(top_tracks,
                             columns=["ID", "Track", "Popularity (from 100)",
                                      "Plays"])
top_tracks_df["Image"] = top_tracks_df.apply(
    lambda x: requests.get(
        f"https://open.spotify.com/oembed?url="
        f"https://open.spotify.com/track/{x['ID']}").json()[
        "thumbnail_url"], axis=1)

# st.dataframe(top_tracks_df, hide_index=True)

st.data_editor(
    top_tracks_df,
    column_config={
        "ID": None,
        "Image": st.column_config.ImageColumn("")
    },
    column_order=["Image", "Track", "Popularity (from 100)", "Plays"],
    hide_index=True
)
