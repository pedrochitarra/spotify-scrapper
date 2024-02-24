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
    ]
)

st.write("Welcome to the Spotify Showcase!"
         "Here you can explore some data from Spotify."
         "The data is focused on artists, albums, and tracks that are"
         "trending in Brazil.")

st.write("To start, select a page from the sidebar.")
