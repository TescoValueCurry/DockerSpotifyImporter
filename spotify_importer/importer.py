import time

import requests

from spotify_downloader.downloader import download_playlist
from .spotify_api import get_spotify_token, get_playlist_tracks, get_all_album_tracks, get_artist_albums, \
    get_spotify_playlist_info
from sqlalchemy.orm import Session
import db_operations
from db_operations import add_wanted_track
from db_operations import get_playlists
from database import SessionLocal



def get_spotify_playlist_info_with_retries(url, token, retries=3, backoff=2):
    for attempt in range(1, retries + 1):
        try:
            return get_spotify_playlist_info(url, token)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                print(f"Attempt {attempt} failed with {e}. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2  # exponential backoff
            else:
                raise
    raise Exception("Max retries reached for fetching playlist info")


def import_playlist_and_sync(url: str, mode: str, db: Session):
    db = SessionLocal()
    playlists = get_playlists(db)

    for playlist in playlists:
        print(f"Importing playlist: {playlist['name']} ({playlist['url']})")
        import_playlist(playlist["url"], playlist["mode"], db)
        download_playlist(playlist["name"])



def import_playlist(url: str, mode: str, db: Session):
    token = get_spotify_token()

    playlist_info = get_spotify_playlist_info_with_retries(url, token)
    playlist_name = playlist_info.get("name", "Unknown Playlist")

    playlist = db_operations.add_playlist(db, url, mode, name=playlist_name)

    playlist_tracks = get_playlist_tracks(url, token)
    wanted = []

    if mode == "playlist_only":
        for track in playlist_tracks:
            album_id = track["album"]["id"]
            album_name = track["album"]["name"]
            artist_name = track["artists"][0]["name"]
            album_tracks = get_all_album_tracks(album_id, token)

            for t in album_tracks:
                wanted.append({
                    "track_name": t["name"],
                    "album_name": album_name,
                    "artist_name": artist_name
                })

    elif mode == "full_artist":
        for track in playlist_tracks:
            artist = track["artists"][0]
            artist_id = artist["id"]
            artist_name = artist["name"]
            albums = get_artist_albums(artist_id, token)
            seen_albums = set()

            for album in albums:
                if album["id"] in seen_albums:
                    continue
                seen_albums.add(album["id"])
                album_tracks = get_all_album_tracks(album["id"], token)
                for t in album_tracks:
                    wanted.append({
                        "track_name": t["name"],
                        "album_name": album["name"],
                        "artist_name": artist_name
                    })

    # Add all wanted tracks
    for track in wanted:
        add_wanted_track(
            db=db,
            song_name=track["track_name"],
            artist_name=track["artist_name"],
            album_name=track["album_name"],
        )

    playlist.import_status = "imported"

    db.commit()
