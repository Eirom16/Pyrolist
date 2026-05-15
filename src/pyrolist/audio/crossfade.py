import asyncio
from loguru import logger


class CrossfadeManager:

    def __init__(self, enabled: bool = True, duration_sec: int = 5):
        self.enabled = enabled
        self.duration_sec = duration_sec

    async def apply_crossfade(self, player, next_url: str, next_video_id: str) -> None:
        if not self.enabled:
            await player.play_url(next_url, next_video_id)
            return

        fade_start_ms = max(0, player.status.duration_ms - (self.duration_sec * 1000))
        if player.status.position_ms < fade_start_ms:
            await asyncio.sleep(
                (fade_start_ms - player.status.position_ms) / 1000.0
            )

        for step in range(self.duration_sec):
            vol = max(0, player.status.volume - int(200 / (self.duration_sec * 4)))
            player.set_volume(vol)
            await asyncio.sleep(0.25)

        await player.play_url(next_url, next_video_id)

        for step in range(self.duration_sec * 4):
            vol = min(200, player.status.volume + int(200 / (self.duration_sec * 4)))
            player.set_volume(vol)
            await asyncio.sleep(0.25)
