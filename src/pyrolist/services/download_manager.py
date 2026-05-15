import asyncio
import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from loguru import logger
import yt_dlp

from pyrolist.config.paths import AppDirs
from pyrolist.db.repository import DownloadRepository

class DownloadTask:
    def __init__(self, video_id: str, title: str, artist: str, thumbnail_url: str, parent_playlist_id: str = None, parent_playlist_title: str = None):
        self.video_id = video_id
        self.title = title
        self.artist = artist
        self.thumbnail_url = thumbnail_url
        self.parent_playlist_id = parent_playlist_id
        self.parent_playlist_title = parent_playlist_title
        self.status = "queued" # queued, downloading, completed, error
        self.progress = 0.0
        self.speed = ""
        self._cancel_flag = False

    def cancel(self):
        self._cancel_flag = True

class DownloadManager(QObject):
    download_queued = Signal(object) # DownloadTask
    download_started = Signal(str) # video_id
    download_progress = Signal(str, float, str) # video_id, progress (0-100), speed
    download_completed = Signal(str, str) # video_id, filepath
    download_error = Signal(str, str) # video_id, error_msg

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DownloadManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._queue = asyncio.Queue()
        self._tasks = {} # video_id -> DownloadTask
        self._workers = []
        self._running = False
        self._repo = DownloadRepository()

    def start(self, max_concurrent: int = 3):
        if self._running:
            return
        self._running = True
        for _ in range(max_concurrent):
            worker = asyncio.ensure_future(self._worker())
            self._workers.append(worker)

    def stop(self):
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    def add_download(self, video_id: str, title: str, artist: str, thumbnail_url: str, parent_playlist_id: str = None, parent_playlist_title: str = None) -> bool:
        if video_id in self._tasks:
            return False # already queued/downloading
        
        task = DownloadTask(video_id, title, artist, thumbnail_url, parent_playlist_id, parent_playlist_title)
        self._tasks[video_id] = task
        self.download_queued.emit(task)
        self._queue.put_nowait(task)
        return True

    def cancel_download(self, video_id: str):
        if video_id in self._tasks:
            self._tasks[video_id].cancel()

    async def _worker(self):
        while self._running:
            try:
                task = await self._queue.get()
                if task._cancel_flag:
                    self._queue.task_done()
                    continue
                
                await self._process_download(task)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Download worker error: {e}")

    async def _process_download(self, task: DownloadTask):
        task.status = "downloading"
        self.download_started.emit(task.video_id)
        
        loop = asyncio.get_event_loop()
        
        def progress_hook(d):
            if task._cancel_flag:
                raise Exception("CANCELLED")
                
            if d['status'] == 'downloading':
                try:
                    percent_str = d.get('_percent_str', '0%').replace('%', '').replace('\x1b[0;94m', '').replace('\x1b[0m', '').strip()
                    percent = float(percent_str) if percent_str else 0.0
                    speed = d.get('_speed_str', '')
                    
                    task.progress = percent
                    task.speed = speed
                    # emit in main thread
                    loop.call_soon_threadsafe(self.download_progress.emit, task.video_id, percent, speed)
                except ValueError:
                    pass

        url = f"https://www.youtube.com/watch?v={task.video_id}"
        out_dir = AppDirs.downloads
        
        # Determine path structure
        if task.parent_playlist_title:
            out_dir = out_dir / task.parent_playlist_title
            
        out_dir.mkdir(parents=True, exist_ok=True)
        
        out_tmpl = str(out_dir / f"{task.artist} - {task.title}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_tmpl,
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    # Get actual filepath
                    return ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            filepath = await loop.run_in_executor(None, _download)
            
            if task._cancel_flag:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return
                
            task.status = "completed"
            
            # Save to DB
            await self._repo.add_download(
                video_id=task.video_id,
                title=task.title,
                artist=task.artist,
                album="",
                file_path=filepath,
                thumbnail_url=task.thumbnail_url,
                duration_ms=0,
                parent_playlist_id=task.parent_playlist_id,
                parent_playlist_title=task.parent_playlist_title
            )
            
            self.download_completed.emit(task.video_id, filepath)
            
        except Exception as e:
            if str(e) == "CANCELLED":
                logger.info(f"Download cancelled: {task.title}")
            else:
                logger.error(f"Download failed for {task.video_id}: {e}")
                task.status = "error"
                self.download_error.emit(task.video_id, str(e))
        finally:
            if task.video_id in self._tasks:
                del self._tasks[task.video_id]
