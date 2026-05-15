"""Background download manager for Pyrolist.

Downloads songs from YouTube using yt-dlp, saves them with metadata and thumbnail
to the local downloads directory.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import dataclass, field

import yt_dlp
from loguru import logger
from PySide6.QtCore import QObject, Signal

from pyrolist.config.paths import AppDirs
from pyrolist.api.stream_extractor import StreamExtractor


@dataclass
class DownloadTask:
    video_id: str
    title: str
    artist: str
    thumbnail_url: str = ""
    status: str = "pending"   # pending, downloading, done, error
    progress: float = 0.0
    error: str = ""
    file_path: str = ""


class DownloadManager(QObject):
    """Manages background downloads of songs."""

    # Signals
    download_started = Signal(str)      # video_id
    download_progress = Signal(str, float)  # video_id, progress 0-100
    download_finished = Signal(str, str)    # video_id, file_path
    download_error = Signal(str, str)       # video_id, error_message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dl")
        self._queue: list[DownloadTask] = []
        self._active: dict[str, DownloadTask] = {}
        self._download_dir = AppDirs.downloads
        self._download_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, video_id: str, title: str, artist: str, thumbnail_url: str = ""):
        """Add a song to the download queue."""
        # Skip if already queued or downloaded
        if video_id in self._active:
            logger.info(f"Already downloading: {title}")
            return
        
        # Check if already downloaded
        safe_name = self._safe_filename(f"{artist} - {title}")
        for ext in ['.m4a', '.mp3', '.opus', '.webm']:
            if (self._download_dir / f"{safe_name}{ext}").exists():
                logger.info(f"Already downloaded: {title}")
                return

        task = DownloadTask(
            video_id=video_id,
            title=title,
            artist=artist,
            thumbnail_url=thumbnail_url,
        )
        self._queue.append(task)
        self._active[video_id] = task
        logger.info(f"Queued download: {title} by {artist}")
        
        asyncio.ensure_future(self._process_queue())

    async def _process_queue(self):
        """Process the next item in the download queue."""
        if not self._queue:
            return

        task = self._queue.pop(0)
        task.status = "downloading"
        self.download_started.emit(task.video_id)

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._download_sync, task
            )
            
            if result:
                task.status = "done"
                task.file_path = result
                self.download_finished.emit(task.video_id, result)
                logger.info(f"Download complete: {task.title} -> {result}")
                
                # Also download thumbnail
                if task.thumbnail_url:
                    await self._save_thumbnail(task)
            else:
                task.status = "error"
                task.error = "Download returned no file"
                self.download_error.emit(task.video_id, task.error)

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            self.download_error.emit(task.video_id, str(e))
            logger.error(f"Download failed for {task.title}: {e}")

        finally:
            self._active.pop(task.video_id, None)
            # Process next in queue
            if self._queue:
                asyncio.ensure_future(self._process_queue())

    def _download_sync(self, task: DownloadTask) -> str:
        """Synchronous download using yt-dlp. Runs in thread pool."""
        safe_name = self._safe_filename(f"{task.artist} - {task.title}")
        output_template = str(self._download_dir / f"{safe_name}.%(ext)s")

        cookie_opts = StreamExtractor._load_cookie_opts()

        opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegMetadata',
            }],
            **cookie_opts,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={task.video_id}",
                    download=True
                )
                if not info:
                    return ""

                # Find the actual downloaded file
                ext = info.get('ext', 'm4a')
                downloaded_path = self._download_dir / f"{safe_name}.{ext}"
                if downloaded_path.exists():
                    return str(downloaded_path)

                # Fallback: look for any file with the safe_name
                for f in self._download_dir.glob(f"{safe_name}.*"):
                    if f.suffix in ['.m4a', '.mp3', '.opus', '.webm', '.ogg']:
                        return str(f)

                return ""
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return ""

    async def _save_thumbnail(self, task: DownloadTask):
        """Download and save the song's thumbnail alongside the audio file."""
        try:
            import httpx
            from PIL import Image
            import io

            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(task.thumbnail_url)
                if r.status_code != 200:
                    return

                img = Image.open(io.BytesIO(r.content))
                if img.mode in ('RGBA', 'P', 'LA'):
                    bg = Image.new('RGB', img.size, (30, 30, 46))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                safe_name = self._safe_filename(f"{task.artist} - {task.title}")
                thumb_path = self._download_dir / f"{safe_name}.jpg"
                img.save(thumb_path, "JPEG", quality=85)
                logger.debug(f"Saved thumbnail for: {task.title}")
        except Exception as e:
            logger.debug(f"Failed to save thumbnail: {e}")

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Make a filename safe for all platforms."""
        chars_to_remove = '<>:"/\\|?*'
        for ch in chars_to_remove:
            name = name.replace(ch, '')
        # Limit length
        return name[:200].strip()
