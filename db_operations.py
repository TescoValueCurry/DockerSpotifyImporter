from sqlalchemy.orm import Session
import models


def add_playlist(db: Session, url: str, mode: str, name: str = None):
    existing = db.query(models.Playlist).filter(models.Playlist.url == url).first()
    if existing:
        existing.mode = mode  # Update the mode
        if name:
            existing.name = name
        db.commit()
        db.refresh(existing)
        return existing
    pl = models.Playlist(url=url, mode=mode, name=name)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return pl


def get_playlists(db: Session):
    playlists = db.query(models.Playlist).all()
    return [
        {
            "id": p.id,
            "url": p.url,
            "name": p.name,                # <-- add this line
            "mode": p.mode,
            "import_status": p.import_status
        }
        for p in playlists
    ]


def add_wanted_track(db: Session, song_name: str, artist_name: str, album_name: str):
    # check if track already exists
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
