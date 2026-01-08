#!/usr/bin/env python3
import os
from db_worker import db_worker
import db_operations
from config import settings
from models import WantedTrack

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac", ".ogg", ".wav")


def get_all_db_tracks():
    """
    Return all WantedTrack entries from the DB.
    """
    return db_worker.submit(lambda db: db.query(WantedTrack).all())


def sync_orphaned_and_missing_tracks():
    added_count = 0
    fixed_count = 0
    skipped_count = 0

    # --- Step 1: Build a set of all files on disk ---
    disk_tracks = set()
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
                    disk_tracks.add((song_name, artist_name, album_name))

    # --- Step 2: Sync DB with disk files ---
    db_tracks = get_all_db_tracks()
    for track in db_tracks:
        key = (track.song_name, track.artist_name, track.album_name)
        file_exists = key in disk_tracks

        # Track marked as downloaded but file missing
        if track.downloaded and not file_exists:
            track.downloaded = False
            db_worker.submit(lambda db, t=track: db.commit())
            fixed_count += 1
            print(f"File missing for DB entry: {track.song_name} - {track.artist_name} ({track.album_name}), marked as undownloaded", flush=True)

        # Track not in DB but exists on disk → add it
        if not track.downloaded and file_exists:
            track.downloaded = True
            db_worker.submit(lambda db, t=track: db.commit())
            fixed_count += 1
            print(f"File exists for DB entry: {track.song_name} - {track.artist_name} ({track.album_name}), marked as downloaded", flush=True)

    # --- Step 3: Add orphaned files (exist on disk, not in DB at all) ---
    for song_name, artist_name, album_name in disk_tracks:
        exists_in_db = db_worker.submit(
            db_operations.get_wanted_track_by_names,
            song_name,
            artist_name,
            album_name
        )
        if not exists_in_db:
            db_worker.submit(
                db_operations.add_wanted_track,
                song_name,
                artist_name,
                album_name,
                downloaded=True
            )
            added_count += 1
            print(f"Added orphaned track to DB: {song_name} - {artist_name} ({album_name})", flush=True)
        else:
            skipped_count += 1

    print(f"Sanity check complete. Added: {added_count}, Fixed: {fixed_count}, Skipped: {skipped_count}", flush=True)


if __name__ == "__main__":
    sync_orphaned_and_missing_tracks()
