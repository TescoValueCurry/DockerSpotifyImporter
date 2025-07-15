import json
import os

CONFIG_PATH = os.getenv("CONFIG_PATH", "/config/config.json")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)


class Settings:
    SPOTIFY_CLIENT_ID = config["spotify_client_id"]
    SPOTIFY_CLIENT_SECRET = config["spotify_client_secret"]
    APP_PORT = config["app_port"]
    SYNC_INTERVAL_HOURS = config["sync_interval_hours"]
    DATABASE_URL = f"sqlite:///{config['database_path']}"
    DOWNLOADS_PATH = config["downloads_path"]


settings = Settings()
