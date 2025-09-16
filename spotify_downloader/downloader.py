import os
import threading
import subprocess
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from database import SessionLocal
from config import settings
from models import WantedTrack

# Global lock for DB writes (will still use queue for safer writes)
db_write_lock = threading.Lock()

# Queue for DB updates
write_queue = Queue()


def db_writer():
    """Thread that processes DB write tasks sequentially."""
    db = SessionLocal()
    while True:
        task = write_queue.get()
        if task is None:  # Sentinel to stop the writer thread
            break

        track_entry, downloaded, reset_downloading, attempts_increment = task
        try:
            if downloaded:
                track_entry.downloaded = True
            if reset_downloading:
                track_entry.downloading = False
            if attempts_increment:
                track_entry.attempts += 1
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"DB write failed: {e}")
        finally:
            write_queue.task_done()
            print(f"DB write completed for: {track_entry.song_name}")
    db.close()


def download_audio(track):
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

        # Mark as downloading and increment attempts via writer queue
        write_queue.put((track_entry, False, True, True))

        artist_dir = os.path.join(settings.DOWNLOADS_PATH, track_entry.artist_name)
        album_dir = os.path.join(artist_dir, track_entry.album_name)
        os.makedirs(album_dir, exist_ok=True)

        search_query = f"{track_entry.song_name} - {track_entry.artist_name}"
        print(f"Downloading: {search_query}")

        # Run SpotDL CLI
        result = subprocess.run(
            ["spotdl", "download", search_query, "--output", album_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            # print("=" * 60)
            print(f"SpotDL failed for: {search_query}")
            print(f"Exit Code: {result.returncode}")
            # if result.stdout.strip():
            #     print("\n--- STDOUT ---")
            #     print(result.stdout.strip())
            # if result.stderr.strip():
            #     print("\n--- STDERR ---")
            #     print(result.stderr.strip())
            # print("=" * 60)

            # Reset downloading flag via writer queue
            write_queue.put((track_entry, False, True, False))
            return

        # Successful download
        write_queue.put((track_entry, True, True, False))
        print(f"Successfully downloaded: {search_query}")

    except Exception as e:
        print(f"Download failed for {track['song_name']}: {e}")
        if track_entry:
            # Reset downloading flag via writer queue
            write_queue.put((track_entry, False, True, False))
    finally:
        db.close()


def download_playlist(playlist_name: str):
    print(f"Starting download for playlist: {playlist_name}")
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

    # Start the writer thread
    writer_thread = threading.Thread(target=db_writer, daemon=True)
    writer_thread.start()

    # Download tracks in parallel
    with ThreadPoolExecutor() as executor:
        executor.map(download_audio, track_dicts)

    # Wait for all write tasks to finish
    write_queue.join()
    # Stop writer thread
    write_queue.put(None)
    writer_thread.join()
    print(f"Finished downloading playlist: {playlist_name}")
