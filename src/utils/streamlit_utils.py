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
    retries = 0
    if item_type == "faixa":
        item_type = "track"
    while not url and retries < 3:
        try:
            st.write(
                f"https://open.spotify.com/oembed?url="
                f"https://open.spotify.com/{item_type}/{item_id}")
            response = requests.get(
                f"https://open.spotify.com/oembed?url="
                f"https://open.spotify.com/{item_type}/{item_id}",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/119.0.0.0 Safari/537.36"),
                    "Origin": "https://open.spotify.com",
                    "Referer": "https://open.spotify.com/"})
            response = response.json()
            url = response["thumbnail_url"]
        except (requests.exceptions.JSONDecodeError, KeyError):
            # st.write(response, response.text)
            # Default image
            if retries == 2:
                url = ("https://i.scdn.co/image/"
                       "ab6761610000517458efbed422ab46484466822b")
            else:
                print("Error!", response, "\n")
                url = None
                retries += 1
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
