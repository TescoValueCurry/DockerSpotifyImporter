from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    name = Column(String)
    mode = Column(String)  # 'songs' or 'artist'
    import_status = Column(String, default="importing")  # 'importing', 'imported', or 'failed'



class WantedTrack(Base):
    __tablename__ = "wanted_tracks"
    id = Column(Integer, primary_key=True, index=True)
    song_name = Column(String)
    artist_name = Column(String)
    album_name = Column(String)
    path = Column(String, nullable=True)
    downloaded = Column(Boolean, default=False)
    downloading = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
