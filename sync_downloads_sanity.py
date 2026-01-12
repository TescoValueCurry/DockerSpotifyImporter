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
    Assumes filename format: "{artist} - {song}.{ext}"
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
                if not filename.lower().endswith(AUDIO_EXTENSIONS):
                    continue

                name, _ext = os.path.splitext(filename)

                # Expect: "Artist - Song"
                if " - " not in name:
                    continue  # skip unexpected formats

                file_artist, song_name = name.split(" - ", 1)

                # Trust directory artist name over filename
                key = (artist_name, song_name)
                full_path = os.path.join(album_dir, filename)
                disk_tracks[key] = full_path

    return disk_tracks

def get_path_from_track(track):
    """
    Build the expected full path for a track.
    Matches spotdl default naming: "{artist} - {song}.mp3"
    """
    artist_dir = os.path.join(settings.DOWNLOADS_PATH, track.artist_name)
    album_dir = os.path.join(artist_dir, track.album_name)

    filename = f"{track.artist_name} - {track.song_name}.mp3"
    return os.path.join(album_dir, filename)

def sync_orphaned_and_missing_tracks():
    added_count = 0
    fixed_count = 0

    # --- Step 1: Get all files on disk ---
    disk_tracks = find_files_on_disk()

    # --- Step 2: Get all tracks from DB ---
    db_tracks = get_all_db_tracks()
    for track in db_tracks:
        path = get_path_from_track(track)
        existed = True

        # Track marked as downloaded but file missing
        if track.downloaded:
            # see if we can find the file in the disk tracks
            if os.path.exists(path):
                # if its there see set the tracks path to it
                track.path = path
                track.downloaded = True
            else:
                # if not set it to undownloaded, set download attempts to 0, set path to null
                track.path = None
                track.downloaded = False
                track.attempts = 0
                existed = False
                print(path)

            db_worker.submit(lambda db, t=track: db.commit())
            fixed_count += 1
            if existed:
                print(f"File found path corrected for DB entry: {track.song_name} - {track.artist_name}", flush=True)
            else:
                print(f"File not found marked as undownloaded for DB entry: {track.song_name} - {track.artist_name}", flush=True)

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

    print(f"Sanity check complete. Added: {added_count}, Fixed: {fixed_count}", flush=True)


if __name__ == "__main__":
    sync_orphaned_and_missing_tracks()
