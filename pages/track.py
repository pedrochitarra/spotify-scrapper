"""This module is responsible for the track page."""
import pandas as pd
import streamlit as st
import sqlite3

import src.utils.streamlit_utils as st_utils


st.title("Tracks")
# Connect to the database
conn = sqlite3.connect('data/spotify.db')
cursor = conn.cursor()
artist = st_utils.arist_selectbox()

# List the artist's tracks
cursor.execute(
    f"""SELECT ff.fai_codigo, ff.fai_nome, ff.fai_popularidade,
    ff.fai_reproducoes, art.art_primeironome, art.art_ultimonome,
    fai_img.image_url
    FROM fai_faixa ff
    INNER JOIN afx_artistafaixa afx ON ff.fai_codigo = afx.afx_fai_codigo
    INNER JOIN art_artista art ON afx.afx_art_codigo = art.art_codigo
    INNER JOIN faixas_images fai_img ON
    fai_img.fai_codigo = ff.fai_codigo
    WHERE art.art_codigo = '{artist[0]}';""")
tracks = cursor.fetchall()

# Select the track
track = st.selectbox(
    'Select a track', tracks,
    format_func=lambda x: x[1])

track_image = track[-1]

if track_image is None:
    track_image = ("https://i.scdn.co/image/"
                   "ab6761610000517458efbed422ab46484466822b")

# Get artists involved
artists = cursor.execute(
    f"""
    SELECT art_primeironome, art_ultimonome
    FROM afx_artistafaixa
    INNER JOIN art_artista
    ON afx_artistafaixa.afx_art_codigo = art_artista.art_codigo
    WHERE afx_fai_codigo = '{track[0]}';
    """).fetchall()

artists = [artist[0] + " " + artist[1] if artist[1] else artist[0]
           for artist in artists]

artist_name = artist[1] + " " + artist[2] if artist[2] else artist[1]
image_track_col, text_info_col = st.columns(2)
with image_track_col:
    st.image(track_image, width=300, use_column_width="auto")
with text_info_col:
    st.write("Track:")
    st.subheader(track[1])
    st.write("Artists:")
    for artist in artists:
        st.subheader(artist)
    st.metric("Popularity (from 100):", track[2])
    formatted_plays = "{:,}".format(track[3])
    st.metric("Plays:", formatted_plays)

# Get in which playlists the track is
playlists = cursor.execute(
    f"""
    SELECT ply.ply_codigo, ply.ply_nome, ply.ply_descricao, ply.ply_seguidores,
    ply_img.image_url
    FROM fxp_faixaplaylist fxp
    INNER JOIN ply_playlist ply
    ON fxp.fxp_ply_codigo = ply.ply_codigo
    INNER JOIN playlists_images ply_img
    ON ply_img.ply_codigo = ply.ply_codigo
    WHERE fxp.fxp_fai_codigo = '{track[0]}';
    """).fetchall()

playlists_df = pd.DataFrame(
    playlists, columns=["ID", "Name", "Description", "Followers", "Image"])

load_playlists_images = st.checkbox("Load playlists images", value=False)
if load_playlists_images:
    column_order = ["Image", "Name", "Followers", "Description"]
else:
    column_order = ["Name", "Followers", "Description"]

st.data_editor(
    playlists_df,
    column_config={
        "ID": None,
        "Image": st.column_config.ImageColumn("")
    },
    column_order=column_order,
    hide_index=True,
    use_container_width=True
)
