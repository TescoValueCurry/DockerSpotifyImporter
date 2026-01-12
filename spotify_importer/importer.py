import time

import requests

from spotify_downloader.downloader import download_playlist
from .spotify_api import get_spotify_token, get_playlist_track_ids, get_all_album_tracks, get_artist_albums, \
    get_spotify_playlist_info
import db_operations
from db_worker import db_worker


def get_spotify_playlist_info_with_retries(url, token, retries=3, backoff=2):
    for attempt in range(1, retries + 1):
        try:
            return get_spotify_playlist_info(url, token)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                print(f"Attempt {attempt} failed with {e}. Retrying in {backoff} seconds...", flush=True)
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
        print(f"Importing playlist: {playlist['name']} ({playlist['url']})", flush=True)
        download_playlist(playlist["name"])


def import_playlist(url: str, mode: str):
    token = get_spotify_token()

    # --- STEP 1: Fetch minimal playlist info (snapshot + total tracks) ---
    playlist_info = get_spotify_playlist_info_with_retries(url, token)
    playlist_name = playlist_info.get("name", "Unknown Playlist")
    playlist_snapshot = playlist_info.get("snapshot_id")
    playlist_total_tracks = playlist_info.get("tracks", {}).get("total", 0)

    # --- STEP 2: Load previous snapshot from DB if available ---
    prev_playlist = db_worker.submit(db_operations.get_playlist_by_url, url)
    if prev_playlist and getattr(prev_playlist, "snapshot_id", None) == playlist_snapshot:
        print(f"No changes detected for playlist '{playlist_name}', skipping import.", flush=True)
        return  # nothing changed, skip heavy processing

    # --- STEP 3: Update/add playlist in DB ---
    playlist = db_worker.submit(
        db_operations.add_playlist,
        url,
        mode,
        playlist_name,
        snapshot_id=playlist_snapshot  # save current snapshot
    )

    # --- STEP 4: Fetch playlist tracks (paginated, minimal fields) ---
    playlist_tracks = get_playlist_track_ids(url, token)  # see helper below

    # --- STEP 5: Prepare track list ---
    wanted = []

    # Cache for albums & artists to avoid redundant fetches
    album_cache = {}
    artist_cache = {}

    if mode == "playlist_only":
        for track in playlist_tracks:
            album_id = track["album"]["id"]
            album_name = track["album"]["name"]
            artist_name = track["artists"][0]["name"]

            # Use cache to skip repeated album fetches
            if album_id not in album_cache:
                album_cache[album_id] = get_all_album_tracks(album_id, token)
            album_tracks = album_cache[album_id]

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

            # Cache artist albums
            if artist_id not in artist_cache:
                artist_cache[artist_id] = get_artist_albums(artist_id, token)
            albums = artist_cache[artist_id]

            seen_albums = set()
            for album in albums:
                if album["id"] in seen_albums:
                    continue
                seen_albums.add(album["id"])

                # Cache album tracks
                if album["id"] not in album_cache:
                    album_cache[album["id"]] = get_all_album_tracks(album["id"], token)
                album_tracks = album_cache[album["id"]]

                for t in album_tracks:
                    wanted.append({
                        "track_name": t["name"],
                        "album_name": album["name"],
                        "artist_name": artist_name
                    })

    # --- STEP 6: Add tracks to DB ---
    for track in wanted:
        if "live at" in track["track_name"].lower():
            print(
                f"Skipping live track: {track['track_name']} by {track['artist_name']}", flush=True
            )
            continue
        similar = db_operations.does_similar_song_exist(track["track_name"], track["artist_name"])
        if similar:
            print("Skipping variant of already indexed song:", track["track_name"])
            continue
        db_worker.submit(
            db_operations.add_wanted_track,
            track["track_name"],
            track["artist_name"],
            track["album_name"]
        )

    # --- STEP 7: Update playlist import status ---
    if playlist:
        playlist.import_status = "imported"  # pyright ignore reportattributeaccessissue

    print(f"Playlist '{playlist_name}' imported successfully with {len(wanted)} tracks", flush=True)
