import sqlite3
from tqdm import tqdm

import utils.streamlit_utils as st_utils


def get_items_with_no_image(item_type: str) -> list:
    """Get the artists with no image.

    Args:
        item_type (str): The type of the item (can be "artist", "album",
        "playlist").

    Returns:
        list: The items with no image.
    """
    conn = sqlite3.connect('data/spotify.db')
    cursor = conn.cursor()
    # Create table if it doesn't exist
    if item_type == "artist":
        item_key = "art.art_codigo"
        subquery = "art.art_codigo FROM art_artista art"
        table_key = "art_codigo"
    elif item_type == "album":
        item_key = "alb.alb_codigo"
        subquery = "alb.alb_codigo FROM alb_album alb"
        table_key = "alb_codigo"
    elif item_type == "playlist":
        item_key = "ply.ply_codigo"
        subquery = "ply.ply_codigo FROM ply_playlist ply"
        table_key = "ply_codigo"
    elif item_type == "faixa":
        item_key = "fai.fai_codigo"
        subquery = "fai.fai_codigo FROM fai_faixa fai"
        table_key = "fai_codigo"

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {item_type}s_images (
            {table_key} TEXT,
            image_url TEXT
        );"""
    )

    cursor.execute(
        f"""
        SELECT {subquery}
        WHERE
        {item_key} NOT IN (SELECT {table_key} FROM {item_type}s_images)
        OR
        {table_key} IN (SELECT {table_key} FROM {item_type}s_images
        WHERE image_url IS NULL);
        """)
    items = cursor.fetchall()
    conn.close()
    return items


def save_items_with_no_image(items: list, item_type: str,
                             table_key: str) -> None:
    """Save the items with no image. Get the image URL and save it in the
    database.

    Args:
        items (list): The items IDs with no image.
        item_type (str): The type of the item (can be "artist", "album",
            "playlist").
        table_key (str): The name of the column that is the key of the table
            (e.g. "art_codigo" for the artist table).
    """
    conn = sqlite3.connect('data/spotify.db')
    for item in tqdm(items):
        image_url = st_utils.try_to_get_browser_image_url(item, item_type)
        print(image_url)
        # Insert the image URL into the database
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {item_type}s_images ({table_key}, image_url)
                VALUES (?, ?);
                """, (item, image_url))
            conn.commit()
        except Exception as e:
            print(e)
            conn.rollback()

    conn.close()


artists_no_image = get_items_with_no_image("artist")
artists_no_image = [artist[0] for artist in artists_no_image]
print(f"There are {len(artists_no_image)} artists with no image.")
save_items_with_no_image(artists_no_image, "artist", "art_codigo")

playlists_no_image = get_items_with_no_image("playlist")
playlists_no_image = [playlist[0] for playlist in playlists_no_image]
print(f"There are {len(playlists_no_image)} playlists with no image.")
save_items_with_no_image(playlists_no_image, "playlist", "ply_codigo")

tracks_no_image = get_items_with_no_image("faixa")
tracks_no_image = [track[0] for track in tracks_no_image]
print(f"There are {len(tracks_no_image)} tracks with no image.")
save_items_with_no_image(tracks_no_image, "faixa", "fai_codigo")

albums_no_image = get_items_with_no_image("album")
albums_no_image = [album[0] for album in albums_no_image]
print(f"There are {len(albums_no_image)} albums with no image.")
save_items_with_no_image(albums_no_image, "album", "alb_codigo")
