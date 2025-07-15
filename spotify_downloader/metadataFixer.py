from mutagen.id3 import ID3, APIC, error
from mutagen.mp3 import MP3
import requests
import os
from spotify_importer import spotify_api  # reuse your code
from mutagen.id3 import TIT2, TPE1, TALB, TRCK, TDRC


def apply_metadata_from_spotify(filepath, song_name, artist_name):
    token = spotify_api.get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Search for the track
    query = f"{artist_name} {song_name}"
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["tracks"]["items"]
    if not results:
        print(f"No results found on Spotify for: {query}")
        return

    track = results[0]

    # Extract metadata
    title = track["name"]
    artist = ", ".join([a["name"] for a in track["artists"]])
    album = track["album"]["name"]
    release_date = track["album"]["release_date"]
    track_num = track["track_number"]
    album_art_url = track["album"]["images"][0]["url"] if track["album"]["images"] else None

    # Load MP3 file
    audio = MP3(filepath, ID3=ID3)
    try:
        audio.add_tags()
    except error:
        pass

    audio["TIT2"] = TIT2(encoding=3, text=title)  # Title
    audio["TPE1"] = TPE1(encoding=3, text=artist)  # Artist
    audio["TALB"] = TALB(encoding=3, text=album)  # Album
    audio["TRCK"] = TRCK(encoding=3, text=str(track_num))  # Track number
    audio["TDRC"] = TDRC(encoding=3, text=release_date)  # Release year

    if album_art_url:
        img_data = requests.get(album_art_url).content
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc=u'Cover',
                data=img_data
            )
        )

    audio.save()
    print(f"Metadata applied to: {os.path.basename(filepath)}")
