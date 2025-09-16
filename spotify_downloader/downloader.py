
import os
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
from config import settings
from models import WantedTrack
from db_worker import db_worker



def get_track_entry(db, track):
    return db.query(WantedTrack).filter_by(
        song_name=track["song_name"],
        artist_name=track["artist_name"],
        album_name=track["album_name"]
    ).first()

def mark_downloading(db, track_entry):
    track_entry.downloading = True
    track_entry.attempts += 1

def mark_downloaded(db, track_entry):
    track_entry.downloaded = True
    track_entry.downloading = False

def reset_downloading(db, track_entry):
    track_entry.downloading = False

def download_audio(track):
    # get track entry from db
    track_entry = db_worker.submit(get_track_entry, track)
    if not track_entry:
        print(f"Track not found: {track}")
        return
    if track_entry.downloaded:
        print(f"Already downloaded: {track_entry.song_name}")
        return
    if track_entry.downloading:
        print(f"Already downloading: {track_entry.song_name}")
        return
    if track_entry.attempts >= 3:
        print(f"Skipping {track_entry.song_name} (3 attempts reached)")
        return

    # mark as downloading and increment attempts
    db_worker.submit(mark_downloading, track_entry)

    artist_dir = os.path.join(settings.DOWNLOADS_PATH, track_entry.artist_name)
    album_dir = os.path.join(artist_dir, track_entry.album_name)
    os.makedirs(album_dir, exist_ok=True)

    search_query = f"{track_entry.song_name} - {track_entry.artist_name}"
    # print(f"Downloading: {search_query}")

    # download it with spotdl
    try:
        result = subprocess.run(
            ["spotdl", "download", search_query, "--output", album_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"Download failed for {track['song_name']}: {result.returncode}")
            db_worker.submit(reset_downloading, track_entry)
            return
        print(f"Successfully downloaded: {search_query}")
        db_worker.submit(mark_downloaded, track_entry)
    except Exception as e:
        print(f"Download failed for {track['song_name']}: {e}")
        db_worker.submit(reset_downloading, track_entry)


def get_tracks_for_download(db):
    return db.query(WantedTrack).filter(
        WantedTrack.downloaded == False,
        WantedTrack.downloading == False,
        WantedTrack.attempts < 3,
    ).all()

def download_playlist(playlist_name: str):
    print(f"Starting download for playlist: {playlist_name}")
    tracks = db_worker.submit(get_tracks_for_download)
    if not tracks:
        tracks = []
    track_dicts = [
        {
            "song_name": t.song_name,
            "artist_name": t.artist_name,
            "album_name": t.album_name
        }
        for t in tracks
    ]
    with ThreadPoolExecutor() as executor:
        executor.map(download_audio, track_dicts)
    print(f"Finished downloading playlist: {playlist_name}")
