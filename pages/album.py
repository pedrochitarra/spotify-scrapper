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
    f"""SELECT alb_codigo, alb_nome, alb_lancamento, alb_tipo,
    alb_popularidade
    FROM alb_album
    INNER JOIN aal_artistaalbum ON alb_codigo = aal_alb_codigo
    INNER JOIN art_artista ON aal_art_codigo = art_codigo
    WHERE aal_art_codigo = '{artist[0]}';""")
albums = cursor.fetchall()

if not include_singles:
    albums = [album for album in albums if album[3] != "single"]

# Select the album
album = st.selectbox(
    'Select an album', albums,
    format_func=lambda x: x[1])

album_image = st_utils.try_to_get_browser_image_url(album[0], "album")

image_album_col, text_info_col = st.columns(2)
with image_album_col:
    st.image(album_image, width=300, use_column_width="auto")
with text_info_col:
    st.subheader(album[1])
    album_date = datetime.datetime.strptime(album[2], "%Y-%m-%d")
    st.write(album[3].capitalize())
    st.date_input("Release Date:", album_date, disabled=True)
    st.metric("Popularity (from 100):", album[4])
