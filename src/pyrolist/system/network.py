import asyncio
import platform
from loguru import logger

if platform.system() == "Linux":
    try:
        import psutil
        HAS_PSUTIL = True
    except ImportError:
        HAS_PSUTIL = False


class NetworkMonitor:

    def __init__(self, on_connectivity_change):
        self.on_connectivity_change = on_connectivity_change
        self._is_connected = True
        self._task = None
        
    async def start(self):
        self._is_connected = await self.check_connectivity()
        self._task = asyncio.create_task(self._monitor())
        logger.info("Network monitor started")

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def check_connectivity(self) -> bool:
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False

    async def _monitor(self):
        while True:
            await asyncio.sleep(30)
            was_connected = self._is_connected
            self._is_connected = await self.check_connectivity()
            
            if was_connected != self._is_connected:
                logger.info(f"Network connectivity changed: {self._is_connected}")
                if self.on_connectivity_change:
                    self.on_connectivity_change(self._is_connected)

    @property
    def is_connected(self) -> bool:
        return self._is_connected