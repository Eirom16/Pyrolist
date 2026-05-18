from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pyrolist.db.database import get_session
from pyrolist.db.models import Song, PlayHistory, Download


class SongRepository:

    async def upsert_song(self, **kwargs) -> Song:
        async with get_session() as session:
            video_id = kwargs.get("video_id")
            result = await session.execute(
                select(Song).where(Song.video_id == video_id)
            )
            song = result.scalar_one_or_none()
            if song:
                for k, v in kwargs.items():
                    setattr(song, k, v)
            else:
                song = Song(**kwargs)
                session.add(song)
            await session.commit()
            await session.refresh(song)
            return song

    async def get_song(self, video_id: str) -> Song | None:
        async with get_session() as session:
            result = await session.execute(
                select(Song).where(Song.video_id == video_id)
            )
            return result.scalar_one_or_none()

    async def get_liked_songs(self) -> list[Song]:
        async with get_session() as session:
            result = await session.execute(
                select(Song).where(Song.is_liked == True).order_by(Song.last_played.desc())
            )
            return list(result.scalars().all())

    async def get_liked_video_ids(self) -> set[str]:
        """Return a set of video_ids for all liked songs (efficient for batch UI checks)."""
        async with get_session() as session:
            result = await session.execute(
                select(Song.video_id).where(Song.is_liked == True)
            )
            return set(result.scalars().all())

    async def record_play(self, video_id: str) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(Song).where(Song.video_id == video_id)
            )
            song = result.scalar_one_or_none()
            if song:
                from datetime import datetime
                song.play_count += 1
                song.last_played = datetime.utcnow()
                await session.commit()

    async def toggle_like(self, video_id: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(Song).where(Song.video_id == video_id)
            )
            song = result.scalar_one_or_none()
            if song:
                song.is_liked = not song.is_liked
                liked = song.is_liked
                await session.commit()
                return liked
            return False


class HistoryRepository:

    async def add_entry(self, video_id: str, title: str, artist: str, duration_ms: int) -> None:
        async with get_session() as session:
            entry = PlayHistory(
                video_id=video_id, title=title, artist=artist, duration_ms=duration_ms
            )
            session.add(entry)
            await session.commit()

    async def get_history(self, limit: int = 100) -> list[PlayHistory]:
        async with get_session() as session:
            result = await session.execute(
                select(PlayHistory).order_by(PlayHistory.played_at.desc()).limit(limit)
            )
            return list(result.scalars().all())


class DownloadRepository:

    async def get_download(self, video_id: str) -> Download | None:
        async with get_session() as session:
            result = await session.execute(
                select(Download).where(Download.video_id == video_id)
            )
            return result.scalar_one_or_none()

    async def add_download(self, **kwargs) -> Download:
        async with get_session() as session:
            video_id = kwargs.get("video_id")
            result = await session.execute(
                select(Download).where(Download.video_id == video_id)
            )
            download = result.scalar_one_or_none()
            if download:
                for k, v in kwargs.items():
                    setattr(download, k, v)
            else:
                download = Download(**kwargs)
                session.add(download)
            await session.commit()
            await session.refresh(download)
            return download

    async def get_downloads(self) -> list[Download]:
        async with get_session() as session:
            result = await session.execute(select(Download).order_by(Download.downloaded_at.desc()))
            return list(result.scalars().all())

    async def remove_download(self, video_id: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(Download).where(Download.video_id == video_id)
            )
            download = result.scalar_one_or_none()
            if download:
                await session.delete(download)
                await session.commit()
                return True
            return False
