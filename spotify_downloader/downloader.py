

import os
import subprocess
import time
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
    global download_counter, download_start_time, download_total_tracks
    # get track entry from db
    track_entry = db_worker.submit(get_track_entry, track)
    if not track_entry:
        print(f"Track not found: {track}", flush=True)
        return
    if track_entry.downloaded:
        print(f"Already downloaded: {track_entry.song_name}", flush=True)
        return
    if track_entry.downloading:
        print(f"Already downloading: {track_entry.song_name}", flush=True)
        return
    if track_entry.attempts >= 3:
        print(f"Skipping {track_entry.song_name} (3 attempts reached)", flush=True)
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
            print(f"Download failed for {track['song_name']}: {result.returncode}", flush=True)
            db_worker.submit(reset_downloading, track_entry)
            return
        download_counter += 1
        elapsed = time.time() - download_start_time if download_start_time else 0
        rate = (download_counter / elapsed * 60) if elapsed > 0 else 0
        songs_left = download_total_tracks - download_counter if download_total_tracks is not None else '?'
        msg = f"Successfully downloaded: {search_query} ({download_counter} downloaded this session)"
        if download_counter % 5 == 0:
            if rate > 0 and isinstance(songs_left, int) and songs_left > 0:
                eta_min = songs_left / rate
                eta_str = f" ~{int(eta_min)} min left"
            else:
                eta_str = ""
            msg += f" | {rate:.2f} songs/min, {songs_left} left{eta_str}"
        print(msg, flush=True)
        db_worker.submit(mark_downloaded, track_entry)
    except Exception as e:
        print(f"Download failed for {track['song_name']}: {e}", flush=True)
        db_worker.submit(reset_downloading, track_entry)


def get_tracks_for_download(db):
    return db.query(WantedTrack).filter(
        WantedTrack.downloaded == False,
        WantedTrack.downloading == False,
        WantedTrack.attempts < 3,
    ).all()

def reset_all_downloading(db):
    db.query(WantedTrack).update({WantedTrack.downloading: False})
    db.commit()

def download_playlist(playlist_name: str):
    global download_counter, download_start_time, download_total_tracks
    download_counter = 0
    download_start_time = time.time()
    print(f"Starting download for playlist: {playlist_name}", flush=True)

    # clear the downloading flags for all tracks to fix stuck ones
    db_worker.submit(reset_all_downloading)

    tracks = db_worker.submit(get_tracks_for_download)
    if not tracks:
        tracks = []
    download_total_tracks = len(tracks)
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
    print(f"Finished downloading playlist: {playlist_name}", flush=True)
