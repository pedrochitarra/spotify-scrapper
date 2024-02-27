"""Main file for the Streamlit app"""
import streamlit as st
from st_pages import Page, show_pages


st.title('Spotify Showcase')
# Specify what pages should be shown in the sidebar, and what their titles
# and icons should be
show_pages(
    [
        Page("frontend.py", "Showcase", "🏠"),
        Page("pages/artist.py", "Artist", ":microphone:"),
        Page("pages/album.py", "Album", ":cd:"),
        Page("pages/track.py", "Track", ":musical_note:"),
    ]
)

st.write("Welcome to the Spotify Showcase!"
         "Here you can explore some data from Spotify."
         "The data is focused on artists, albums, and tracks that are"
         "trending in Brazil.")

st.write("To start, select a page from the sidebar.")

st.write(
    "In the Artist page, you can see the artists "
    "that are trending in Brazil and the information about them available "
    "in the Spotify API. You can also see the albums and tracks of the "
    "artist.")

st.write(
    "In the Album page, you can see the albums from the artists that are "
    "trending in Brazil and the information about them available in the "
    "Spotify API.")

st.write(
    "In the Track page, you can see the tracks from the artists that are "
    "trending in Brazil and the information about them available in the "
    "Spotify API.")

st.markdown(
    "<span style='color:red;'> ⚠️ Disclaimer: The data can contain some bad "
    "words and inappropriate names, since it's the name of the musics and "
    "artists, so be aware of that. </span>"
)
