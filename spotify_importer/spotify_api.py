import requests
import base64
import json
import time
from typing import List, Dict

CONFIG_PATH = "config/config.json"


def get_spotify_token(config_path: str = CONFIG_PATH) -> str:
    """
    Get OAuth token using Client Credentials Flow
    """
    with open(config_path) as f:
        config = json.load(f)
    client_id = config["spotify_client_id"]
    client_secret = config["spotify_client_secret"]

    auth_str = f"{client_id}:{client_secret}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    resp = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]


def spotify_get_with_retry(url: str, headers: dict, max_retries=5) -> dict:
    """
    GET request with handling for 429 rate limiting from Spotify API.
    Retries up to max_retries times with respect to Retry-After header.
    """
    retries = 0
    while True:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            print(f"Rate limited. Sleeping for {retry_after} seconds before retrying...")
            time.sleep(retry_after)
            retries += 1
            if retries >= max_retries:
                raise Exception(f"Max retries reached ({max_retries}) for rate limiting.")
            continue
        resp.raise_for_status()
        return resp.json()


def get_playlist_tracks(playlist_url: str, token: str) -> List[Dict]:
    """
    Return list of track objects from a Spotify playlist URL.
    Handles pagination and rate limits.
    """
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

    tracks = []
    while url:
        data = spotify_get_with_retry(url, headers)
        for item in data["items"]:
            track = item.get("track")
            if track:
                tracks.append(track)
        url = data.get("next")
    return tracks


def get_all_album_tracks(album_id: str, token: str) -> List[Dict]:
    """
    Return all tracks in an album by album_id, with rate-limit handling.
    """
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    data = spotify_get_with_retry(url, headers)
    return data["items"]


def get_spotify_playlist_info(playlist_url: str, token: str):
    # Extract playlist ID from URL
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()  # Contains playlist name, description, etc.


def get_artist_albums(artist_id: str, token: str) -> List[Dict]:
    """
    Return all albums and singles by an artist by artist_id.
    Handles pagination and rate limits.
    """
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album,single&limit=50"
    headers = {"Authorization": f"Bearer {token}"}

    albums = []
    while url:
        data = spotify_get_with_retry(url, headers)
        albums.extend(data["items"])
        url = data.get("next")
    return albums
