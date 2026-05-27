import asyncio
import hashlib
from pathlib import Path
from pyrolist.config.paths import AppDirs
from loguru import logger
import io


class ImageCache:
    MAX_ENTRIES = 200
    MAX_SIZE_MB = 50
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._cache_dir = AppDirs.artwork_cache
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = {}
        self._initialized = True

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

        # Check memory or disk cache first without acquiring any lock
        existing = self.get(url)
        if existing:
            return existing

        # Get or create an asyncio.Lock for this specific URL to prevent duplicate downloads
        lock = self._locks.get(url)
        if not lock:
            lock = asyncio.Lock()
            self._locks[url] = lock

        async with lock:
            # Check again inside the lock in case another task finished downloading it
            existing = self.get(url)
            if existing:
                self._locks.pop(url, None)
                return existing

            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    r = await client.get(url)
                    if r.status_code != 200:
                        self._locks.pop(url, None)
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
                    self._locks.pop(url, None)
                    return path
            except Exception as e:
                logger.debug(f"Failed to cache artwork: {e}")
                self._locks.pop(url, None)
                return None

    def clear(self) -> None:
        for path in self._cache_dir.glob("*.jpg"):
            path.unlink()
        self._memory_cache.clear()


import concurrent.futures

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def load_scaled_async(path, width: int, height: int, context_qobject, callback) -> None:
    """Loads and scales an image from path on a background thread pool, invoking callback(bytes_data) on the GUI thread of context_qobject."""
    def load_fn():
        from PIL import Image
        import io
        try:
            with Image.open(str(path)) as img:
                w, h = img.size
                if w <= 0 or h <= 0:
                    return None
                
                scale = max(width / w, height / h)
                new_w = int(round(w * scale))
                new_h = int(round(h * scale))
                
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    try:
                        resample_filter = Image.LANCZOS
                    except AttributeError:
                        resample_filter = Image.ANTIALIAS
                
                img_resized = img.resize((new_w, new_h), resample_filter)
                
                buf = io.BytesIO()
                if img_resized.mode != 'RGB':
                    img_resized.save(buf, format="PNG")
                else:
                    img_resized.save(buf, format="JPEG", quality=90)
                return buf.getvalue()
        except Exception as e:
            from loguru import logger
            logger.debug(f"Failed to load/scale image asynchronously: {e}")
            return None

    def done_callback(future):
        try:
            bytes_data = future.result()
        except Exception:
            bytes_data = None
        
        import shiboken6
        if shiboken6.isValid(context_qobject):
            from PySide6.QtCore import QTimer
            # Schedule the callback to execute on the main thread (thread of context_qobject)
            QTimer.singleShot(0, context_qobject, lambda: callback(bytes_data))

    future = _executor.submit(load_fn)
    future.add_done_callback(done_callback)