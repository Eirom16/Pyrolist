import asyncio
from pypresence import AioPresence
from loguru import logger


class DiscordRPC:

    def __init__(self):
        self._rpc: AioPresence | None = None

    async def connect(self) -> None:
        try:
            self._rpc = AioPresence("1395462809164263495")
            await self._rpc.connect()
            logger.info("Discord RPC connected")
        except Exception as e:
            logger.warning(f"Discord RPC connection failed: {e}")
            self._rpc = None

    async def disconnect(self) -> None:
        if self._rpc:
            try:
                await self._rpc.close()
                logger.info("Discord RPC disconnected")
            except Exception as e:
                logger.debug(f"Discord RPC disconnect error: {e}")

    async def update(
        self,
        title: str,
        artist: str,
        album: str = "",
        is_playing: bool = False,
    ) -> None:
        if not self._rpc:
            return
        try:
            state = f"by {artist}" if artist else "YouTube Music"
            details = f"{title}"
            await self._rpc.update(
                state=state,
                details=details,
                large_image="music",
                large_text=album if album else "Pyrolist",
                small_image="play" if is_playing else "pause",
                small_text="Playing" if is_playing else "Paused",
            )
        except Exception as e:
            logger.debug(f"Discord RPC update failed: {e}")
