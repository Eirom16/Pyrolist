import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from pyrolist.config.paths import AppDirs
from pyrolist.config.settings import AppSettings
import yt_dlp


class YouTubeAPI:
    """API wrapper using yt-dlp for YouTube Music access."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="yt")

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, lambda: func(*args, **kwargs)
        )

    def _get_ydl_opts(self, username=None, password=None):
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        if username and password:
            opts['username'] = username
            opts['password'] = password
        return opts

    async def search(self, query: str, limit: int = 20) -> list:
        """Search YouTube Music for videos."""

        def _search():
            ydl = yt_dlp.YoutubeDL(self._get_ydl_opts())
            results = ydl.extract_info(
                f"ytsearch{limit}:{query}",
                download=False
            )
            return results.get('entries', []) if results else []

        try:
            results = await self._run(_search)
            tracks = []
            for entry in results:
                if entry.get('duration'):
                    tracks.append({
                        'videoId': entry.get('id'),
                        'title': entry.get('title'),
                        'artist': entry.get('artist') or entry.get('uploader', 'Unknown'),
                        'thumbnail': entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None,
                        'duration': entry.get('duration'),
                    })
            return tracks
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_stream_url(self, video_id: str) -> str:
        """Get direct stream URL for a video."""

        def _get_url():
            ydl = yt_dlp.YoutubeDL(self._get_ydl_opts())
            info = ydl.extract_info(
                f"https://music.youtube.com/watch?v={video_id}",
                download=False
            )
            if info and info.get('formats'):
                for fmt in info['formats']:
                    if fmt.get('url') and fmt.get('ext') == 'm4a':
                        return fmt['url']
                return info['formats'][0].get('url', '')
            return ''

        try:
            return await self._run(_get_url) or ''
        except Exception as e:
            logger.error(f"Stream URL error: {e}")
            return ''

    async def get_video_info(self, video_id: str) -> dict:
        """Get video information."""

        def _get_info():
            ydl = yt_dlp.YoutubeDL(self._get_ydl_opts())
            info = ydl.extract_info(
                f"https://music.youtube.com/watch?v={video_id}",
                download=False
            )
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'artist': info.get('artist') or info.get('uploader'),
                'album': info.get('album'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None,
            }

        try:
            return await self._run(_get_info) or {}
        except Exception as e:
            logger.error(f"Video info error: {e}")
            return {}