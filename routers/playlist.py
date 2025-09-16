
from fastapi import APIRouter, Form, BackgroundTasks
import db_operations
from fastapi.responses import RedirectResponse
from spotify_importer.importer import import_playlist_and_sync
from db_worker import db_worker

router = APIRouter()






@router.post("/add_playlist")
def add_playlist(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form(...),
):
    background_tasks.add_task(import_playlist_and_sync, url, mode)
    return RedirectResponse(url="/", status_code=303)



@router.get("/playlists")
def list_playlists():
    return db_worker.submit(db_operations.get_playlists)
