import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor
from loguru import logger


class PipedClient:
    """Client for Piped API - fast YouTube Music streaming."""

    INSTANCES = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.yt",
        "https://watchapi.whatever.social",
    ]

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="piped")
        self._base_url = self.INSTANCES[0]
        self._client = httpx.AsyncClient(timeout=15.0)

    async def _get(self, endpoint: str) -> dict:
        try:
            resp = await self._client.get(f"{self._base_url}{endpoint}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Piped API error: {e}")
        return {}

    async def _get_sync(self, endpoint: str) -> dict:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self._base_url}{endpoint}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Piped API error: {e}")
        return {}

    def _run(self, func):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(self._executor, func)

    async def get_streams(self, video_id: str) -> dict:
        """Get stream URLs and metadata for a video."""

        def _fetch():
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self._base_url}/streams/{video_id}")
                return resp.json() if resp.status_code == 200 else {}

        try:
            return await self._run(_fetch)
        except Exception as e:
            logger.error(f"get_streams error: {e}")
            return {}

    async def search(self, query: str, limit: int = 20) -> list:
        """Search for videos using Piped."""

        def _search():
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{self._base_url}/search",
                    params={"q": query, "filter": "videos", "limit": limit}
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                items = data.get("items", [])
                results = []
                for item in items:
                    if item.get("type") == "video":
                        results.append({
                            "videoId": item.get("videoId"),
                            "title": item.get("title", "Unknown"),
                            "artists": [{"name": item.get("uploaderName", "Unknown")}],
                            "thumbnails": self._extract_thumbnails(item.get("thumbnail")),
                            "duration": item.get("duration", 0),
                            "resultType": "song",
                        })
                return results

        try:
            return await self._run(_search)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def _extract_thumbnails(self, thumbnail_url: str) -> list:
        """Convert thumbnail URL to YouTube-style thumbnail list."""
        if not thumbnail_url:
            return []
        return [{"url": thumbnail_url, "preference": 0}]

    async def get_trending(self, limit: int = 20) -> list:
        """Get trending music videos."""

        def _trending():
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{self._base_url}/trending",
                    params={"type": "music", "limit": limit}
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                results = []
                for item in data:
                    if item.get("type") == "video":
                        results.append({
                            "videoId": item.get("videoId"),
                            "title": item.get("title", "Unknown"),
                            "artists": [{"name": item.get("uploaderName", "Unknown")}],
                            "thumbnails": self._extract_thumbnails(item.get("thumbnail")),
                            "duration": item.get("duration", 0),
                            "resultType": "song",
                        })
                return results

        try:
            return await self._run(_trending)
        except Exception as e:
            logger.error(f"Trending error: {e}")
            return []

    async def close(self):
        await self._client.aclose()
        self._executor.shutdown(wait=False)