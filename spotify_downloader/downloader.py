import os
import threading
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from database import SessionLocal
from config import settings
from models import WantedTrack
from spotify_downloader.metadataFixer import apply_metadata_from_spotify


# Global lock for DB writes
db_write_lock = threading.Lock()


def download_audio(track):
    downloaded = False
    db = SessionLocal()
    track_entry = None
    try:
        track_entry = db.query(WantedTrack).filter_by(
            song_name=track["song_name"],
            artist_name=track["artist_name"],
            album_name=track["album_name"]
        ).first()

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

        # Lock all writes to the DB to prevent concurrency issues
        with db_write_lock:
            track_entry.downloading = True
            track_entry.attempts += 1
            db.commit()

        artist_dir = os.path.join(settings.DOWNLOADS_PATH, track_entry.artist_name)
        album_dir = os.path.join(artist_dir, track_entry.album_name)
        os.makedirs(album_dir, exist_ok=True)

        filename = f"{track_entry.song_name}"
        download_path = os.path.join(album_dir, filename)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": download_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch:{track_entry.artist_name} {track_entry.song_name}"])

        with db_write_lock:
            track_entry.path = download_path + ".mp3"
            track_entry.downloaded = True
            track_entry.downloading = False
            db.commit()

        downloaded = True

    except Exception as e:
        print(f"Download failed for {track['song_name']}: {e}")
        if track_entry:
            try:
                with db_write_lock:
                    db.rollback()
                    track_entry.downloading = False
                    db.commit()
            except Exception as e2:
                print(f"Failed to reset downloading flag: {e2}")
                db.rollback()
    finally:
        if track_entry:
            path = track_entry.path
            song_name = track_entry.song_name
            artist_name = track_entry.artist_name
        else:
            path = song_name = artist_name = None

        db.close()

        if downloaded and path and song_name and artist_name:
            try:
                apply_metadata_from_spotify(path, song_name, artist_name)
            except Exception as e:
                print(f"Metadata application failed: {e}", flush=True)


def download_playlist(playlist_name: str):
    with SessionLocal() as db:
        tracks = db.query(WantedTrack).filter(
            WantedTrack.downloaded == False,
            WantedTrack.downloading == False,
            WantedTrack.attempts < 3,
        ).all()

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
