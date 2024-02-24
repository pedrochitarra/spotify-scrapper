"""Module with utility functions for Streamlit."""
import requests

import streamlit as st
import sqlite3


def try_to_get_browser_image_url(item_id: str, item_type: str) -> str:
    """Try to get the image of an item from Spotify. Since the API is not
    official, it may not work. So this function tries to get the image and
    returns None if it fails.

    Args:
        item_id (str): The ID of the item.
        item_type (str): The type of the item.

    Returns:
        str: The URL of the image.
    """
    url = None
    try:
        url = requests.get(
            f"https://open.spotify.com/oembed?url="
            f"https://open.spotify.com/{item_type}/{item_id}").json()[
                "thumbnail_url"]
    except requests.exceptions.JSONDecodeError:
        None
    return url


def arist_selectbox():
    """Show a selectbox with the artists from the database."""
    conn = sqlite3.connect('data/spotify.db')
    cursor = conn.cursor()

    # Get the artists
    cursor.execute(
        """SELECT art_codigo, art_primeironome, art_ultimonome
        FROM art_artista;""")

    # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

    artists = cursor.fetchall()
    # st.write(artists)

    # Select the artist
    artist = st.selectbox(
        'Select an artist', artists,
        format_func=lambda x: x[1] + " " + x[2] if x[2] else x[1])

    return artist
