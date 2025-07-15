import time
from db_operations import get_playlists
from database import SessionLocal
from config import settings
from spotify_downloader.downloader import download_playlist
from spotify_importer.importer import import_playlist


def run_sync_job():
    print("Running sync job...")

    db = SessionLocal()
    playlists = get_playlists(db)

    for playlist in playlists:
        print(f"Importing playlist: {playlist['name']} ({playlist['url']})")
        import_playlist(playlist["url"], playlist["mode"], db)
        download_playlist(playlist["name"])

    db.close()


def start_scheduler():
    while True:
        run_sync_job()
        time.sleep(settings.SYNC_INTERVAL_HOURS * 3600)
