from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from database import SessionLocal
import db_operations
from fastapi.responses import RedirectResponse
from spotify_importer.importer import import_playlist_and_sync
from fastapi import BackgroundTasks, Form

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/add_playlist")
def add_playlist(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form(...),
    db: Session = Depends(get_db)
):
    background_tasks.add_task(import_playlist_and_sync, url, mode, db)
    return RedirectResponse(url="/", status_code=303)


@router.get("/playlists")
def list_playlists(db: Session = Depends(get_db)):
    return db_operations.get_playlists(db)
