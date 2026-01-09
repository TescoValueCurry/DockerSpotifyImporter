# DockerSpotifyImporter

DockerSpotifyImporter is a tool for downloading and importing Spotify playlists, designed to run in a Dockerised environment. It manages playlists, downloads tracks using `spotdl`, and organizes them into a local directory structure. The project uses a SQLite database to track wanted tracks and download status.

## Features
- Download Spotify playlists and tracks
- Track download status and attempts in a database
- Organize downloads by artist and album
- Web interface
- Docker and docker-compose support for easy deployment

## Directory Structure
```
DockerSpotifyImporter/
├── build.bat                # Windows build script
├── config.py                # Configuration settings
├── database.py              # Database setup and models
├── db_operations.py         # Database operations
├── db_worker.py             # Threaded DB worker
├── docker-compose.yml       # Docker Compose file
├── dockerfile               # Dockerfile for building the app
├── main.py                  # Main entry point
├── models.py                # SQLAlchemy models
├── playlists.db             # SQLite database file
├── requirements.txt         # Python dependencies
├── sync.py                  # Sync logic
├── config/                  # Additional config files
├── download/                # Downloaded music (created at runtime)
├── routers/                 # API routers (e.g., playlist)
├── spotify_downloader/      # Download logic
├── spotify_importer/        # Import logic and Spotify API
├── static/                  # Static files (JS, CSS)
├── templates/               # HTML templates
```

## Setup Instructions

### Prerequisites
- Docker and Docker Compose installed
- Python 3.10+ (for local development)
- `spotdl` installed (if running outside Docker)

### Environment and Paths
- The downloads directory is set by `settings.DOWNLOADS_PATH` in `config.py` (default: `download/`).
- The SQLite database is `playlists.db` in the project root.
- Ensure the `download/` directory exists or will be created at runtime.


### Example Docker Compose Service

Here is a generic example of how you might configure a service for this project in your `docker-compose.yml`:

```yaml
spotify-sync:
   image: yourusername/yourimage:latest   # Replace with your built image name
   build: .
   ports:
      - "5000:5000"
   volumes:
      - ./config:/config         # Config files mounted here
      - ./data:/data             # SQLite DB and other data
      - /path/to/your/music:/downloads   # Music downloads folder (change to your path)
   environment:
      - PORT=5000
      - PUID=1000
      - PGID=1000
      - CONFIG_PATH=/config/config.json
   restart: unless-stopped
```

> **Note:** Replace the volume paths with your actual directories. The `/downloads` path inside the container should match the `DOWNLOADS_PATH` in your config.

---
1. Build the Docker image:
    ```powershell
    docker-compose build
    ```
2. Start the services:
    ```powershell
    docker-compose up
    ```
3. The web interface will be available at the port specified in `docker-compose.yml` (default: 80 or 8000).

### Running Locally (Without Docker)
1. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Install `spotdl`:
   ```powershell
   pip install spotdl
   ```
3. Run the main application:
   ```powershell
   python main.py
   ```

## Usage
- Add playlists or tracks via the web interface or API.
- The app will download tracks and update their status in the database.
- Downloaded files are organized by artist and album in the `download/` directory.

## Notes
- If you encounter issues with permissions, ensure the `download/` directory is writable by the app.
- The app will skip tracks that have failed to download 3 times.
- You can customize settings in `config.py`.

## Example Build Script (Windows)

If you want to automatically increment a build number each time you build, you can use a batch script like this:

```bat
@echo off
cd /d "<your-project-directory>"

REM If build_number.py doesn't exist, create it with 1
if not exist build_number.py echo BUILD_NUMBER = 1 > build_number.py

REM Extract the build number from build_number.py
for /f "tokens=3" %%A in ('findstr /b /c:"BUILD_NUMBER = " build_number.py') do set BUILDNUM=%%A
set /a BUILDNUM=BUILDNUM+1

REM Write the incremented build number back to build_number.py
>build_number.py echo BUILD_NUMBER = %BUILDNUM%

echo Build number updated to: %BUILDNUM%
echo (build_number.py has been changed)

echo Building Docker image...
docker build -t yourimage:latest .

echo Tagging Docker image...
docker tag yourimage:latest yourimage:latest

echo Pushing Docker image...
docker push yourimage:latest

echo Done!
pause
```

- Replace `<your-project-directory>` with your actual project path.
- This script will increment the build number in `build_number.py` and print the new version each time you build.

## License
MIT License
