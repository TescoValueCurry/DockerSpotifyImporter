import time
from db_operations import get_playlists
from db_worker import db_worker
from config import settings
from spotify_downloader.downloader import download_playlist
from spotify_importer.importer import import_playlist


def run_sync_job():
    print("Running sync job...")
    playlists = db_worker.submit(get_playlists)
    if not playlists:
        playlists = []
    for playlist in playlists:
        print(f"Importing playlist: {playlist['name']} ({playlist['url']})")
        import_playlist(playlist["url"], playlist["mode"])
        download_playlist(playlist["name"])


def start_scheduler():
    while True:
        run_sync_job()
        time.sleep(settings.SYNC_INTERVAL_HOURS * 3600)
