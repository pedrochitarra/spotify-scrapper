"""Page to show the artist's information."""
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

# Get the artist's info
cursor.execute(f"""SELECT *
                FROM art_artista art
                INNER JOIN artists_images art_img
                ON art.art_codigo = art_img.art_codigo
                WHERE art.art_codigo = '{artist[0]}';""")
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

artist_image = None
artist_image = artist_info[7]

if artist_image is None:
    artist_image = ("https://i.scdn.co/image/"
                    "ab6761610000517458efbed422ab46484466822b")

with image_artist_col:
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


def get_geolocation(city_name: str):
    """Get the geolocation (latitude and longitude) of a city.

    Args:
        city_name (str): The name of the city.

    Returns:
        Nominatim.location: The location of the city.
    """
    geolocator = Nominatim(user_agent="Geopy Library")
    location = geolocator.geocode(city_name)
    return location


cities_df = pd.DataFrame(
    cities, columns=["City", "Country", "Region", "Listeners"])

with st.spinner("Getting the geolocation of the cities..."):
    cities_df["latitude"] = None
    cities_df["longitude"] = None

    for i, city in cities_df.iterrows():
        # st.write(city)
        city_name = f"{city['City'], city['Region'], city['Country']}"
        local = get_geolocation(city_name)
        # st.write(local)
        cities_df.at[i, "latitude"] = local.latitude
        cities_df.at[i, "longitude"] = local.longitude

    cities_df_show_case = pd.DataFrame()
    cities_df_show_case["City"] = cities_df.apply(
        lambda x: f"{x['City']}, {x['Region']}, {x['Country']}", axis=1)
    cities_df_show_case["Listeners"] = cities_df["Listeners"]
    st.dataframe(cities_df_show_case, hide_index=True)

    # Normalize to 100 the listeners
    cities_df["Listeners"] = (100_000 * cities_df["Listeners"] /
                              cities_df["Listeners"].max())
    st.map(cities_df, size="Listeners", use_container_width=True)


st.subheader("Top tracks")
top_tracks = cursor.execute(
    f"""
    SELECT ff.fai_codigo, ff.fai_nome, ff.fai_popularidade, ff.fai_reproducoes,
    faixas_images.image_url
    FROM fai_faixa ff
    INNER JOIN afx_artistafaixa
    ON afx_artistafaixa.afx_fai_codigo = ff.fai_codigo
    INNER JOIN art_artista
    ON art_artista.art_codigo = afx_artistafaixa.afx_art_codigo
    INNER JOIN faixas_images
    ON ff.fai_codigo = faixas_images.fai_codigo
    WHERE afx_artistafaixa.afx_art_codigo = '{artist[0]}'
    ORDER BY ff.fai_popularidade DESC
    LIMIT 5;
    """).fetchall()
top_tracks_df = pd.DataFrame(top_tracks,
                             columns=["ID", "Track", "Popularity (from 100)",
                                      "Plays", "Image"])

st.data_editor(
    top_tracks_df,
    column_config={
        "ID": None,
        "Image": st.column_config.ImageColumn("")
    },
    column_order=["Image", "Track", "Popularity (from 100)", "Plays"],
    hide_index=True,
    use_container_width=True
)

st.subheader("Top albums")
top_albums = cursor.execute(
    f"""
    SELECT alb.alb_codigo, alb.alb_nome, alb.alb_popularidade,
    albums_images.image_url
    FROM alb_album alb
    INNER JOIN aal_artistaalbum
    ON aal_artistaalbum.aal_alb_codigo = alb.alb_codigo
    INNER JOIN art_artista
    ON art_artista.art_codigo = aal_artistaalbum.aal_art_codigo
    INNER JOIN albums_images
    ON alb.alb_codigo = albums_images.alb_codigo
    WHERE aal_artistaalbum.aal_art_codigo = '{artist[0]}'
    ORDER BY alb_popularidade DESC
    LIMIT 5;
    """).fetchall()
top_albums_df = pd.DataFrame(
    top_albums, columns=["ID", "Album", "Popularity (from 100)", "Image"])

st.data_editor(
    top_albums_df,
    column_config={
        "ID": None,
        "Image": st.column_config.ImageColumn("")
    },
    column_order=["Image", "Album", "Popularity (from 100)"],
    hide_index=True,
    use_container_width=True
)

# Get related artists
st.subheader("Related artists")
st.write("Tip: since there are many artists, you can refresh the page to "
         "get new random artists if you want to see more beyond the most "
         "popular ones")

order_by_popularity = st.checkbox("Order by popularity", value=False)
order_query = None
if order_by_popularity:
    order_query = "art.art_popularidade DESC"
else:
    order_query = "RANDOM()"

related_artists = cursor.execute(
    f"""
    SELECT art.art_codigo, art.art_primeironome, art.art_ultimonome,
    art.art_popularidade, art_img.image_url
    FROM art_artista art
    INNER JOIN artists_images art_img
    ON art.art_codigo = art_img.art_codigo
    WHERE art.art_codigo IN (
        SELECT aa_art_b_codigo
        FROM aa_artistaartista
        WHERE aa_art_a_codigo = '{artist[0]}'
    )
    ORDER BY {order_query}
    LIMIT 5;
    """).fetchall()

related_artists_df = pd.DataFrame(
    related_artists, columns=["ID", "First Name", "Last Name",
                              "Popularity (from 100)", "Image"])
related_artists_df["Artist"] = related_artists_df.apply(
    lambda x: x["First Name"] + " " + x["Last Name"] if x["Last Name"] else
    x["First Name"], axis=1)

st.data_editor(
    related_artists_df,
    column_config={
        "ID": None,
        "Image": st.column_config.ImageColumn("")
    },
    column_order=["Image", "Artist", "Popularity (from 100)"],
    hide_index=True,
    use_container_width=True
)
