import sqlite3
from .config import CHANNELS_DB, MOVIES_DB

def init_db():
    # Kanallar bazasini yaratish
    conn_channels = sqlite3.connect(CHANNELS_DB)
    cursor_channels = conn_channels.cursor()
    cursor_channels.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL UNIQUE,
            url TEXT NOT NULL,
            title TEXT NOT NULL
        )
    """)
    conn_channels.commit()
    conn_channels.close()

    # Kinolar bazasini yaratish
    conn_movies = sqlite3.connect(MOVIES_DB)
    cursor_movies = conn_movies.cursor()
    cursor_movies.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT
        )
    """)
    conn_movies.commit()
    conn_movies.close()

def add_channel(channel_id, url, title):
    conn = sqlite3.connect(CHANNELS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO channels (channel_id, url, title) VALUES (?, ?, ?)", (channel_id, url, title))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Kanal allaqachon mavjud
    finally:
        conn.close()

def get_channels():
    conn = sqlite3.connect(CHANNELS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, url, title FROM channels")
    channels = [{'channel_id': row[0], 'url': row[1], 'title': row[2]} for row in cursor.fetchall()]
    conn.close()
    return channels

def delete_channel(channel_id):
    conn = sqlite3.connect(CHANNELS_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def add_movie(code, file_id, caption=None):
    conn = sqlite3.connect(MOVIES_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO movies (code, file_id, caption) VALUES (?, ?, ?)", (code, file_id, caption))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Kino kodi allaqachon mavjud
    finally:
        conn.close()

def get_movie(code):
    conn = sqlite3.connect(MOVIES_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
    movie = cursor.fetchone()
    conn.close()
    if movie:
        return {'file_id': movie[0], 'caption': movie[1]}
    return None

def delete_movie(code):
    conn = sqlite3.connect(MOVIES_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
