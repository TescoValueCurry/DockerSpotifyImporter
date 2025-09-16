# Copilot Instructions for DockerSpotifyImporter

## Project Overview
- **Purpose:** Automates importing Spotify playlists, downloading tracks (via spotdl), and managing them in a local SQLite database. Provides a FastAPI web UI for playlist management.
- **Major Components:**
  - `main.py`: FastAPI app entrypoint, sets up API, static files, templates, and background sync thread.
  - `routers/playlist.py`: API endpoints for adding/listing playlists, triggers background import/sync.
  - `spotify_importer/`: Spotify API integration and playlist import logic.
  - `spotify_downloader/`: Handles track downloads and DB update queue.
  - `db_operations.py`, `models.py`, `database.py`: SQLAlchemy models and DB helpers.
  - `static/`, `templates/`: Frontend assets and Jinja2 HTML templates.

## Key Workflows
- **Run Locally:**
  - Use `docker-compose up --build` (see `docker-compose.yml`).
  - App runs on port 8000 by default; config via `/config/config.json` (see `config.py`).
- **Config:**
  - All secrets/paths in `/config/config.json` (mounted by Docker).
  - Example keys: `spotify_client_id`, `spotify_client_secret`, `database_path`, `downloads_path`, `cookies_path`.
- **Database:**
  - Uses SQLite by default, path from config.
  - Models: `Playlist`, `WantedTrack` (see `models.py`).
- **Playlist Import:**
  - POST `/add_playlist` (via form or API) triggers background import and download.
  - Downloaded tracks are managed via a queue and a dedicated DB writer thread for safe concurrent updates.
- **Frontend:**
  - Main UI at `/` (see `templates/index.html`).
  - Playlists list auto-refreshes via JS (`static/scripts.js`).

## Patterns & Conventions
- **Background Tasks:**
  - Use FastAPI `BackgroundTasks` for async playlist import.
  - Long-running sync jobs run in daemon threads (see `main.py`, `sync.py`).
- **DB Writes:**
  - All DB updates for downloads are queued and processed by a single thread (`spotify_downloader/downloader.py`).
- **Error Handling:**
  - Spotify API calls use retry/backoff for robustness (`spotify_importer/spotify_api.py`).
- **Extending:**
  - Add new API endpoints in `routers/` and register in `main.py`.
  - Add new config options to `/config/config.json` and `config.py`.
- **Comments:**
  - Code is commented for clarity.
  - Comments should always be in all lowercase and feature minimal sentence complexity and punctiation.
  - If you come accross a comment that does not follow these rules, please edit it to do so.
  - Use UK spelling conventions.


## External Dependencies
- **Python:** See `requirements.txt` (FastAPI, SQLAlchemy, yt-dlp, mutagen, etc).
- **Docker:** Used for deployment and config isolation.

## Examples
- To add a playlist: POST to `/add_playlist` with `url` and `mode` (see `index.html` form).
- To list playlists: GET `/playlists` (returns JSON).

---
For questions about architecture or extending, see the referenced files for patterns. Keep all config and secrets out of source code—use `/config/config.json`.
