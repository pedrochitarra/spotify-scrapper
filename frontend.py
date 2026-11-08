"""Entry point of the Streamlit app. Run with: streamlit run frontend.py"""
import streamlit as st

from src.utils import streamlit_utils as ui

st.set_page_config(page_title="Spotify Showcase", page_icon="🎧",
                   layout="wide", initial_sidebar_state="collapsed")
ui.inject_css()

pages = [
    st.Page("pages/overview.py", title="Home", icon=":material/home:",
            url_path="overview", default=True),
    st.Page("pages/compare.py", title="Then vs now",
            icon=":material/compare_arrows:", url_path="compare"),
    st.Page("pages/charts.py", title="Top 200", icon=":material/trending_up:",
            url_path="charts"),
    st.Page("pages/cities.py", title="Cities", icon=":material/location_city:",
            url_path="cities"),
    st.Page("pages/search.py", title="Search", icon=":material/search:",
            url_path="search"),
    st.Page("pages/artist.py", title="Artist", icon=":material/person:",
            url_path="artist"),
    st.Page("pages/album.py", title="Album", icon=":material/album:",
            url_path="album"),
    st.Page("pages/track.py", title="Track", icon=":material/music_note:",
            url_path="track"),
]
nav = st.navigation(pages, position="top")

# Direct links on GitHub Pages: index.html turns /repo/artist?id=1 into
# ?page=artist&id=1, because stlite cannot route by path in a subfolder.
target = st.query_params.get("page")
if target:
    rest = {k: v for k, v in st.query_params.to_dict().items() if k != "page"}
    page = next((p for p in pages if p.url_path == target), None)
    if page:
        st.switch_page(page, query_params=rest)
    st.query_params.from_dict(rest)

nav.run()

st.html("<p class='sx-foot'>Educational project, not affiliated with Spotify. "
        "Data: Spotify Web API, kworb.net, Last.fm. Names come straight "
        "from Spotify and may contain explicit words.</p>")
