<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="https://play-lh.googleusercontent.com/cShys-AmJ93dB0SV8kE6Fl5eSaf4-qMMZdwEDKI5VEmKAXfzOqbiaeAsqqrEBCTdIEs=w240-h480-rw" alt="Spotify Logo"></a>
</p>

<h3 align="center">Spotify Scrapper</h3>

<p align="center"> Project aimed to learn web scraping techniques and data extraction from the Spotify platform.
    <br> 
</p>

## 🧐 About <a name = "about"></a>
Welcome to the Spotify Scraper repository, an educational resource designed to provide insight into web scraping techniques and data extraction from the Spotify platform. This repository serves as a learning tool for individuals interested in understanding how to programmatically access and retrieve information from Spotify's vast database of music tracks, albums, artists, and playlists.

## 🏁 Getting Started <a name = "getting_started"></a>
The following link provide access to the official documentation for the Spotify Web API, which is the primary resource used to access and retrieve data from the Spotify platform. The documentation provides a comprehensive overview of the API's capabilities, including the various endpoints and methods available for accessing and retrieving data from the Spotify platform.

- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api/tutorials/getting-started)

In this repository, you will find a collection of Python scripts and accompanying documentation that demonstrate various methods for scraping data from Spotify's web interface. Whether you're a beginner looking to explore the fundamentals of web scraping or an experienced developer seeking to enhance your skills, this repository aims to provide clear examples and explanations to aid your learning journey.

I'm assuming here that you have a basic understanding of Python and web scraping, also
that you have an access token from Spotify API. If you don't have one, you can get it [here](https://developer.spotify.com/documentation/web-api/concepts/access-token).

It's important to note that while web scraping can be a powerful tool for data acquisition, it's essential to adhere to Spotify's terms of service and usage policies. This repository encourages responsible scraping practices and respects Spotify's guidelines regarding data access and usage. Also this repository is for educational purposes only, and the scripts provided are intended to be used as learning tools to explore the process of web scraping and data extraction.

Whether you're interested in building your own music recommendation system, conducting research on music trends, or simply curious about the process of web scraping, this repository provides a valuable resource to help you get started.

Happy scraping, and enjoy exploring the world of music data with Spotify Scraper!

Since I'm Brazilian, I'm going to gather the playlists of the musics most listened to in Brazil and the cities where the artists are most listened to. There's a group of playlists for a large amount of cities called Top 50 - City Name, from Sound of Cities user. I'm going to gather all the playlists from this user and save the information in a database.

An important thing to note that's all the connections with database are made
to a PostgreSQL database, but to showcase in Streamlit I'm using a SQLite database, since there's not a lot of data to showcase.

## 📜 Scripts <a name = "scripts"></a>
The following is a list of the scripts available in this repository, along with a brief description of each script's purpose and functionality.

- `main.py`: This script calls the other scripts to gather data from Spotify's web interface. It provides a high-level overview of the scraping process and demonstrates how to access and retrieve data from Spotify's platform.

- `get_album_info.py`: This script demonstrates how to extract data from a specific album on Spotify. It provides examples of how to access and retrieve information about an album, including its name, release date, and tracklist.

    - `save_albums_info()`: This function demonstrates how to save the information of a list of albums in database.

- `get_artist_info.py`: This script demonstrates how to extract data from a specific artist on Spotify. It provides examples of how to access and retrieve information about an artist, including their name, popularity, and top tracks.

    - `get_insta_followers_livecounts_nl()`: This function demonstrates how to get the number of followers of an artist on Instagram.
    - `get_insta_followers_instrack()`: This function demonstrates how to get the number of followers of an artist on Instagram.
    - `get_insta_followers_tucktools()`: This function demonstrates how to get the number of followers of an artist on Instagram.
    - `extract_socialmedia_followers()`: This function demonstrates how to get the number of followers of an artist on many social medias.
    - `save_socials_info()`: This function demonstrates how to save the information of the artist's social medias.
    - `save_social_media_followers()`: This function demonstrates how to save the number of followers of an artist on many social medias.
    - `save_genres_info()`: This function demonstrates how to save the genres of an artist and by consequence of the platform.
    - `save_cities_info()`: This function demonstrates how to save the cities where the artist is most listened to and by consequence of the platform.
    - `save_artists_info()`: This function demonstrates how to save the information of a list of artists in database.
    - `save_related_artists_info()`: This function demonstrates how to save the related artists of an artist in database.

- `get_playlist_info.py`: This script demonstrates how to extract data from a specific playlist on Spotify. It provides examples of how to access and retrieve information about a playlist, including its name, description, and tracklist.
  - `save_playlists_info()`: This function demonstrates how to save the information of a list of playlists in database. The selected playlists are from Brazil and many cities in Brazil most listened to.

- `get_track_info.py`: This script demonstrates how to extract data from a specific track on Spotify. It provides examples of how to access and retrieve information about a track, including its name, duration, and popularity.
    - `insert_artist_playlist()`: This function demonstrates how to insert the relation between an artist and a playlist in database.
    - `save_tracks_info()`: This function demonstrates how to save the information of a list of tracks in database.