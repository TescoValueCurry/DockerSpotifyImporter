import time

import requests

from spotify_downloader.downloader import download_playlist
from .spotify_api import get_spotify_token, get_playlist_tracks, get_all_album_tracks, get_artist_albums, \
    get_spotify_playlist_info
import db_operations
from db_worker import db_worker


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


def import_playlist_and_sync(url: str, mode: str):
    import_playlist(url, mode)
    playlists = db_worker.submit(db_operations.get_playlists)
    if not playlists:
        playlists = []
    for playlist in playlists:
        print(f"Importing playlist: {playlist['name']} ({playlist['url']})")
        download_playlist(playlist["name"])


def import_playlist(url: str, mode: str):
    token = get_spotify_token()
    playlist_info = get_spotify_playlist_info_with_retries(url, token)
    playlist_name = playlist_info.get("name", "Unknown Playlist")
    playlist = db_worker.submit(db_operations.add_playlist, url, mode, playlist_name)
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
    # add all wanted tracks
    for track in wanted:
        if "live at" in track["track_name"].lower():
            print(f"Skipping live track: {track['track_name']} by {track['artist_name']}")
            continue
        db_worker.submit(db_operations.add_wanted_track, track["track_name"], track["artist_name"], track["album_name"])
    if playlist:
        playlist.import_status = "imported" # pyright ignore reportattributeaccessissue
    print(f"playlist {playlist_name} imported successfully with {len(wanted)} tracks")
