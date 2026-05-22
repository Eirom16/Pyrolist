from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pyrolist.db.database import Base
from datetime import datetime


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String, default="")
    duration_ms = Column(Integer, default=0)
    thumbnail_url = Column(String, default="")
    is_liked = Column(Boolean, default=False, index=True)
    last_played = Column(DateTime, nullable=True, index=True)
    play_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Song {self.title} by {self.artist}>"


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, autoincrement=True)
    browse_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    year = Column(String, nullable=True)
    thumbnail_url = Column(String, default="")


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    thumbnail_url = Column(String, default="")


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    thumbnail_url = Column(String, default="")
    is_local = Column(Boolean, default=False)


class PlayHistory(Base):
    __tablename__ = "play_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    played_at = Column(DateTime, default=datetime.utcnow, index=True)
    duration_ms = Column(Integer, default=0)


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String, default="")
    file_path = Column(String, nullable=False)
    thumbnail_url = Column(String, default="")
    duration_ms = Column(Integer, default=0)
    downloaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    parent_playlist_id = Column(String, nullable=True)
    parent_playlist_title = Column(String, nullable=True)
    parent_playlist_thumbnail_url = Column(String, nullable=True)


class CachedArtwork(Base):
    __tablename__ = "cached_artwork"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    local_path = Column(String, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)
