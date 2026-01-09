import requests
import base64
import json
import time
from typing import List, Dict

CONFIG_PATH = "/config/config.json"


def get_spotify_token(config_path: str = CONFIG_PATH) -> str:
    """
    get oauth token using client credentials flow
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
    get request with handling for 429 rate limiting from spotify api
    retries up to max_retries times with respect to retryafter header
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


def get_playlist_track_ids(playlist_url: str, token: str):
    """
    Return list of track objects from a Spotify playlist URL.
    Handles pagination and rate limits.
    """
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    headers = {"Authorization": f"Bearer {token}"}

    # only gets track ids and other relevant fields
    url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?limit=100"
        "&fields=items(added_at,track(id,name,artists(id,name),album(id,name))),next"
    )

    tracks = []
    while url:
        data = spotify_get_with_retry(url, headers)
        tracks.extend(
            {
                "id": item["track"]["id"],
                "added_at": item["added_at"],
                "name": item["track"]["name"],
                "artists": item["track"].get("artists", []),
                "album": item["track"].get("album", {}),
            }
            for item in data["items"]
            if item.get("track") and item["track"].get("id")
        )
        url = data.get("next")

    return tracks


def get_all_album_tracks(album_id: str, token: str) -> List[Dict]:
    """
    Return all tracks in an album by album_id, with rate-limit handling and pagination.
    """
    url = (
        f"https://api.spotify.com/v1/albums/{album_id}/tracks"
        "?limit=50"
        "&fields=items(id,name,track_number),next"
    )
    headers = {"Authorization": f"Bearer {token}"}

    tracks = []
    while url:
        data = spotify_get_with_retry(url, headers)
        tracks.extend(data["items"])
        url = data.get("next")

    return tracks


def get_spotify_playlist_info(playlist_url: str, token: str):
    # extract playlist id from url
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    headers = {"Authorization": f"Bearer {token}"}
    url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}"
        "?fields=id,name,description,snapshot_id,tracks.total"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()  # contains playlist name description etc


def get_artist_albums(artist_id: str, token: str) -> List[Dict]:
    """
    Return all albums and singles by an artist by artist_id.
    Handles pagination and rate limits.
    """
    url = (
        f"https://api.spotify.com/v1/artists/{artist_id}/albums"
        "?include_groups=album,single"
        "&limit=50"
        "&fields=items(id,name,release_date,album_type),next"
    )
    headers = {"Authorization": f"Bearer {token}"}

    albums = []
    while url:
        data = spotify_get_with_retry(url, headers)
        albums.extend(data["items"])
        url = data.get("next")

    return albums
