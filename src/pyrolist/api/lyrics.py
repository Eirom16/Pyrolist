import asyncio
from concurrent.futures import ThreadPoolExecutor
import syncedlyrics
from loguru import logger


class LyricsClient:

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lyrics")

    def _sync_search(self, title: str, artist: str, album: str = "") -> str | None:
        try:
            result = syncedlyrics.search(
                f"{title} {artist}",
                plain_only=False,
            )
            return result
        except Exception as e:
            logger.debug(f"Lyrics search failed: {e}")
            return None

    async def get_lyrics(
        self, title: str, artist: str, album: str = ""
    ) -> syncedlyrics.Lyrics | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_search, title, artist, album
        )

    async def get_plain_lyrics(self, title: str, artist: str) -> str | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_search, title, artist
        )
