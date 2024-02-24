"""Main file for the Streamlit app"""
import streamlit as st
from st_pages import Page, show_pages


st.title('Spotify Brazil Showcase')
# Specify what pages should be shown in the sidebar, and what their titles
# and icons should be
show_pages(
    [
        Page("frontend.py", "Showcase", "🏠"),
        Page("pages/artist.py", "Artist", ":microphone:"),
    ]
)
