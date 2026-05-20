import asyncio
import hashlib
from pathlib import Path
from pyrolist.config.paths import AppDirs
from loguru import logger
import io


class ImageCache:
    MAX_ENTRIES = 200
    MAX_SIZE_MB = 50

    def __init__(self):
        self._cache_dir = AppDirs.artwork_cache
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def _is_valid_url(self, url: str) -> bool:
        if not isinstance(url, str):
            return False
        if not url:
            return False
        if url.startswith("data:"):
            return False
        if not url.startswith(("http://", "https://")):
            return False
        return True

    def _get_filename(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest() + ".jpg"

    def get(self, url: str) -> Path | None:
        if not self._is_valid_url(url):
            return None
        filename = self._get_filename(url)
        if url in self._memory_cache:
            path = Path(self._memory_cache[url])
            if path.exists():
                return path
        path = self._cache_dir / filename
        if path.exists():
            self._memory_cache[url] = str(path)
            return path
        return None

    async def download(self, url: str) -> Path | None:
        if not self._is_valid_url(url):
            return None

        async with self._lock:
            existing = self.get(url)
            if existing:
                return existing

            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    r = await client.get(url)
                    if r.status_code != 200:
                        return None
                    
                    from PIL import Image
                    img = Image.open(io.BytesIO(r.content))
                    
                    # Robustly convert ANY mode to RGB for JPEG
                    if img.mode != 'RGB':
                        try:
                            # Handle transparency by compositing onto dark bg
                            if img.mode in ('RGBA', 'LA', 'PA'):
                                background = Image.new('RGB', img.size, (30, 30, 46))
                                if img.mode == 'PA':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1])
                                img = background
                            elif img.mode == 'P':
                                # Palette mode - try converting through RGBA first
                                img = img.convert('RGBA')
                                background = Image.new('RGB', img.size, (30, 30, 46))
                                background.paste(img, mask=img.split()[-1])
                                img = background
                            else:
                                img = img.convert('RGB')
                        except Exception:
                            # Last resort
                            img = img.convert('RGB')
                    
                    filename = self._get_filename(url)
                    path = self._cache_dir / filename
                    img.save(path, "JPEG", quality=85)
                    
                    self._memory_cache[url] = str(path)
                    logger.debug(f"Cached artwork: {url[:40]}...")
                    return path
            except Exception as e:
                logger.debug(f"Failed to cache artwork: {e}")
                return None

    def clear(self) -> None:
        for path in self._cache_dir.glob("*.jpg"):
            path.unlink()
        self._memory_cache.clear()