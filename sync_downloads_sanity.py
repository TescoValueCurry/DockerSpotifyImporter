#!/usr/bin/env python3
import os
from db_worker import db_worker
import db_operations
from config import settings
from models import WantedTrack

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac", ".ogg", ".wav")


def get_all_db_tracks():
    """Return all WantedTrack entries from the DB."""
    return db_worker.submit(lambda db: db.query(WantedTrack).all())


def find_files_on_disk():
    """
    Scan DOWNLOADS_PATH for audio files.
    Returns a dict keyed by (artist_name, song_name) -> full_path
    """
    disk_tracks = {}
    for artist_name in os.listdir(settings.DOWNLOADS_PATH):
        artist_dir = os.path.join(settings.DOWNLOADS_PATH, artist_name)
        if not os.path.isdir(artist_dir):
            continue

        for album_name in os.listdir(artist_dir):
            album_dir = os.path.join(artist_dir, album_name)
            if not os.path.isdir(album_dir):
                continue

            for filename in os.listdir(album_dir):
                if filename.lower().endswith(AUDIO_EXTENSIONS):
                    song_name = os.path.splitext(filename)[0]
                    full_path = os.path.join(album_dir, filename)
                    key = (artist_name, song_name)
                    disk_tracks[key] = full_path
    return disk_tracks


def sync_orphaned_and_missing_tracks():
    added_count = 0
    fixed_count = 0
    skipped_count = 0

    # --- Step 1: Get all files on disk ---
    disk_tracks = find_files_on_disk()

    # --- Step 2: Get all tracks from DB ---
    db_tracks = get_all_db_tracks()
    for track in db_tracks:
        key = (track.artist_name, track.song_name)
        file_path = disk_tracks.get(key)

        # Track marked as downloaded but file missing
        if track.downloaded and not file_path:
            track.downloaded = False
            track.path = None
            db_worker.submit(lambda db, t=track: db.commit())
            fixed_count += 1
            print(f"File missing for DB entry: {track.song_name} - {track.artist_name}, marked as undownloaded", flush=True)

        # Track not marked as downloaded but file exists
        elif not track.downloaded and file_path:
            track.downloaded = True
            track.path = file_path
            db_worker.submit(lambda db, t=track: db.commit())
            fixed_count += 1
            print(f"File exists for DB entry: {track.song_name} - {track.artist_name}, marked as downloaded", flush=True)

        else:
            skipped_count += 1

    # --- Step 3: Add orphaned files (exist on disk, not in DB at all) ---
    for (artist_name, song_name), path in disk_tracks.items():
        exists_in_db = db_worker.submit(
            db_operations.get_wanted_track_by_artist_and_name,
            artist_name,
            song_name
        )
        if not exists_in_db:
            db_worker.submit(
                db_operations.add_wanted_track,
                song_name,
                artist_name,
                album_name=None,
                downloaded=True,
                path=path
            )
            added_count += 1
            print(f"Added orphaned track to DB: {song_name} - {artist_name}", flush=True)

    print(f"Sanity check complete. Added: {added_count}, Fixed: {fixed_count}, Skipped: {skipped_count}", flush=True)


if __name__ == "__main__":
    sync_orphaned_and_missing_tracks()
