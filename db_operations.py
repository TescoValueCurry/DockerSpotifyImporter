from sqlalchemy.orm import Session
import models


def add_playlist(db: Session, url: str, mode: str, name: str = None, snapshot_id: str = None):
    """
    Add a new playlist to the DB or update an existing one.
    Updates mode, name, and snapshot_id if the playlist already exists.
    """
    existing = db.query(models.Playlist).filter(models.Playlist.url == url).first()
    if existing:
        existing.mode = mode
        if name:
            existing.name = name
        if snapshot_id is not None:
            existing.snapshot_id = snapshot_id
        db.commit()
        db.refresh(existing)
        return existing

    pl = models.Playlist(url=url, mode=mode, name=name, snapshot_id=snapshot_id)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return pl


def get_playlists(db: Session):
    """
    Return all playlists in the DB as dictionaries.
    Includes snapshot_id for change detection.
    """
    playlists = db.query(models.Playlist).all()
    return [
        {
            "id": p.id,
            "url": p.url,
            "name": p.name,
            "mode": p.mode,
            "import_status": p.import_status,
            "snapshot_id": p.snapshot_id,
        }
        for p in playlists
    ]


def get_playlist_by_url(db: Session, url: str):
    """
    Return a single playlist object by its URL.
    """
    return db.query(models.Playlist).filter(models.Playlist.url == url).first()


def add_wanted_track(db: Session, song_name: str, artist_name: str, album_name: str):
    """
    Add a track to the wanted tracks table if it doesn't already exist.
    """
    existing = db.query(models.WantedTrack).filter_by(
        song_name=song_name,
        artist_name=artist_name,
        album_name=album_name
    ).first()

    if existing:
        return existing

    new_track = models.WantedTrack(
        song_name=song_name,
        artist_name=artist_name,
        album_name=album_name,
        path=None,
        downloaded=False,
        attempts=0
    )
    db.add(new_track)
    db.commit()
    db.refresh(new_track)
    return new_track

def add_local_track(db: Session, song_name: str, artist_name: str, album_name: str, path: str):
    """
    Update an existing track's path and downloaded status if it exists.
    Returns the track object, or None if not found.
    """
    existing = db.query(models.WantedTrack).filter_by(
        song_name=song_name,
        artist_name=artist_name,
        album_name=album_name
    ).first()

    if existing:
        return existing

    new_track = models.WantedTrack(
        song_name=song_name,
        artist_name=artist_name,
        album_name=album_name,
        path=path,
        downloaded=True,
        attempts=0
    )
    db.add(new_track)
    db.commit()
    db.refresh(new_track)
    return new_track

def get_track_by_path(db: Session, path: str, song_name: str, artist_name: str, album_name: str):
    """
    Check if a track exists in the DB by its path.
    If no match by path, check by song_name, artist_name, and album_name.

    Returns:
        The track object if found, else None
    """
    # First, try to find a track by path
    track = db.query(models.WantedTrack).filter(models.WantedTrack.path == path).first()
    if track:
        return track

    # If no match by path, check by song_name, artist_name, and album_name
    track = db.query(models.WantedTrack).filter_by(
        song_name=song_name,
        artist_name=artist_name,
        album_name=album_name
    ).first()

    return track

def does_similar_song_exist(db: Session, song_name: str, artist_name: str, album_name: str | None = None):
    """
    Detect if a 'similar' song already exists.
    Similar = same base title (before ' - ') for same artist.
    """

    # canonical by splitting on first " - "
    def canonical(name: str):
        parts = name.split(" - ", 1)
        return parts[0].strip().lower()

    base = canonical(song_name)

    q = db.query(models.WantedTrack).filter(
        models.WantedTrack.artist_name == artist_name
    )

    # optional album constraint (not required for correctness)
    if album_name is not None:
        q = q.filter(models.WantedTrack.album_name == album_name)

    tracks = q.all()

    for t in tracks:
        if canonical(t.song_name) == base:
            return t  # similar found

    return None  # no similar

# Write operations (need commit)
add_playlist.requires_commit = True
add_wanted_track.requires_commit = True
add_local_track.requires_commit = True

# Read-only operations (do NOT commit)
get_playlists.requires_commit = False
get_playlist_by_url.requires_commit = False
get_track_by_path.requires_commit = False
does_similar_song_exist.requires_commit = False
