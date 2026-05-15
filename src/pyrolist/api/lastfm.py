import asyncio
from concurrent.futures import ThreadPoolExecutor
import pylast
from loguru import logger


class LastFmScrobbler:

    def __init__(
        self, api_key: str, api_secret: str, session_key: str
    ):
        self._network = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
            session_key=session_key,
        )
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lastfm")

    def _now_playing(self, artist: str, title: str, album: str = "") -> None:
        try:
            self._network.update_now_playing(artist, title, album=album)
        except Exception as e:
            logger.warning(f"Last.fm now-playing failed: {e}")

    def _scrobble(self, artist: str, title: str, timestamp: int, album: str = "") -> None:
        try:
            self._network.scrobble(artist, title, timestamp, album=album)
        except Exception as e:
            logger.warning(f"Last.fm scrobble failed: {e}")

    async def update_now_playing(
        self, artist: str, title: str, album: str = ""
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor, self._now_playing, artist, title, album
        )

    async def scrobble(
        self, artist: str, title: str, album: str = ""
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor, self._scrobble, artist, title, int(__import__("time").time()), album
        )
