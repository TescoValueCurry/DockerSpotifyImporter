from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Keep this for SQLite, ignore if not using SQLite
    pool_size=10,         # increase pool size (default is 5)
    max_overflow=20,      # allow more connections to temporarily overflow
    pool_timeout=30,      # wait time before giving up on connection
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
