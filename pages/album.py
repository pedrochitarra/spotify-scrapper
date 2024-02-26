"""This module is responsible for the album page."""
import datetime

import streamlit as st
import sqlite3

import src.utils.streamlit_utils as st_utils


st.title("Albums")
# Connect to the database
conn = sqlite3.connect('data/spotify.db')
cursor = conn.cursor()
artist = st_utils.arist_selectbox()

# Check if the search include singles
include_singles = st.checkbox("Include singles", value=True)

# List the artist's albums
cursor.execute(
    f"""SELECT alb.alb_codigo, alb.alb_nome, alb.alb_lancamento, alb.alb_tipo,
    alb.alb_popularidade, alb_img.image_url
    FROM alb_album alb
    INNER JOIN aal_artistaalbum aal ON alb.alb_codigo = aal.aal_alb_codigo
    INNER JOIN art_artista art ON aal.aal_art_codigo = art.art_codigo
    INNER JOIN albums_images alb_img ON
    alb_img.alb_codigo = alb.alb_codigo
    WHERE aal.aal_art_codigo = '{artist[0]}';""")
albums = cursor.fetchall()

if not include_singles:
    albums = [album for album in albums if album[3] != "single"]

# Select the album
album = st.selectbox(
    'Select an album', albums,
    format_func=lambda x: x[1])

album_image = album[-1]

if album_image is None:
    album_image = ("https://i.scdn.co/image/"
                   "ab6761610000517458efbed422ab46484466822b")

image_album_col, text_info_col = st.columns(2)
with image_album_col:
    st.image(album_image, width=300, use_column_width="auto")
with text_info_col:
    st.subheader(album[1])
    album_date = datetime.datetime.strptime(album[2], "%Y-%m-%d")
    st.write(album[3].capitalize())
    st.date_input("Release Date:", album_date, disabled=True)
    st.metric("Popularity (from 100):", album[4])
