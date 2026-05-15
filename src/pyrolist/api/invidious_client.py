import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor
from loguru import logger


class InvidiousClient:
    """Fast YouTube client using Invidious API with automatic fallback."""

    INSTANCES = [
        "https://invidious.fdn.fr",
        "https://invidious.snopyta.org",
        "https://yewtu.be",
        "https://invidious.kavin.rocks",
    ]

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="invidious")
        self._client = httpx.AsyncClient(timeout=15.0)
        self._current_instance = None

    async def _get_with_fallback(self, endpoint: str) -> dict:
        """Try multiple instances until one works."""
        for instance in self.INSTANCES:
            try:
                url = f"{instance}{endpoint}"
                resp = await self._client.get(url)
                if resp.status_code == 200:
                    self._current_instance = instance
                    return resp.json()
            except Exception as e:
                logger.debug(f"Invidious {instance} failed: {e}")
                continue
        return {}

    async def search(self, query: str, limit: int = 20) -> list:
        """Search using Invidious - much faster than yt-dlp."""

        async def _search():
            results = await self._get_with_fallback(f"/api/v1/search?q={query}&type=video&limit={limit}")
            if not results:
                return []
            
            tracks = []
            for item in results:
                if item.get('videoId'):
                    thumbnails = item.get('thumbnails', [])
                    thumb_url = thumbnails[-1].get('url', '') if thumbnails else ''
                    duration = item.get('lengthSeconds', 0)
                    tracks.append({
                        'videoId': item.get('videoId'),
                        'title': item.get('title', 'Unknown'),
                        'artists': [{'name': item.get('author', 'Unknown')}],
                        'thumbnails': [{'url': f"https://{self._current_instance}{thumb_url}"}] if thumb_url else [],
                        'duration': duration,
                        'resultType': 'song',
                    })
            return tracks

        try:
            return await _search()
        except Exception as e:
            logger.error(f"Invidious search error: {e}")
            return []

    async def get_stream(self, video_id: str) -> dict:
        """Get stream URL from Invidious - very fast."""

        async def _get_stream():
            data = await self._get_with_fallback(f"/api/v1/videos/{video_id}")
            if not data:
                return {}
            
            adaptive_formats = data.get('adaptiveStreams', [])
            if not adaptive_formats:
                return {}
            
            for fmt in adaptive_formats:
                if fmt.get('type', '').startswith('audio'):
                    return {
                        'url': fmt.get('url', ''),
                        'format': 'm4a',
                        'quality': fmt.get('bitrate', 128000) // 1000,
                        'duration': data.get('lengthSeconds', 0),
                    }
            return {}

        try:
            return await _get_stream()
        except Exception as e:
            logger.error(f"Invidious stream error: {e}")
            return {}

    async def get_trending(self, limit: int = 20) -> list:
        """Get trending music."""
        return await self.search('music', limit)

    async def close(self):
        await self._client.aclose()
        self._executor.shutdown(wait=False)