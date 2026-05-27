import random
from dataclasses import dataclass, field
from enum import Enum


class RepeatMode(Enum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


@dataclass
class QueueItem:
    video_id: str
    title: str
    artist: str
    album: str
    duration_ms: int
    thumbnail_url: str
    stream_url: str | None = None
    stream_expires_at: float = 0.0
    is_local: bool = False
    local_path: str | None = None


class PlayQueue:

    def __init__(self):
        self._queue: list[QueueItem] = []
        self._original: list[QueueItem] = []
        self._index: int = -1
        self.repeat_mode: RepeatMode = RepeatMode.OFF
        self.shuffle_enabled: bool = False

    @property
    def current(self) -> QueueItem | None:
        if 0 <= self._index < len(self._queue):
            return self._queue[self._index]
        return None

    @property
    def next_item(self) -> QueueItem | None:
        next_i = self._index + 1
        if next_i < len(self._queue):
            return self._queue[next_i]
        if self.repeat_mode == RepeatMode.ALL and self._queue:
            return self._queue[0]
        return None

    @property
    def items(self) -> list[QueueItem]:
        return self._queue.copy()

    @property
    def current_index(self) -> int:
        return self._index

    @current_index.setter
    def current_index(self, value: int) -> None:
        if 0 <= value < len(self._queue):
            self._index = value
        elif value < 0:
            self._index = 0

    def set_queue(self, items: list[QueueItem], start_index: int = 0) -> None:
        self._original = items.copy()
        if self.shuffle_enabled:
            shuffled = items.copy()
            current = shuffled.pop(start_index)
            random.shuffle(shuffled)
            self._queue = [current] + shuffled
            self._index = 0
        else:
            self._queue = items.copy()
            self._index = start_index

    def add_next(self, item: QueueItem) -> None:
        pos = self._index + 1
        self._queue.insert(pos, item)
        self._original.insert(pos, item)

    def add_to_end(self, item: QueueItem) -> None:
        self._queue.append(item)
        self._original.append(item)

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self._queue):
            self._queue.pop(index)
            if index <= self._index and self._index > 0:
                self._index -= 1

    def move_item(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self._queue) and 0 <= to_index < len(self._queue):
            item = self._queue.pop(from_index)
            self._queue.insert(to_index, item)
            if from_index == self._index:
                self._index = to_index

    def advance(self) -> QueueItem | None:
        if self.repeat_mode == RepeatMode.ONE:
            return self.current
        if self._index + 1 < len(self._queue):
            self._index += 1
        elif self.repeat_mode == RepeatMode.ALL and self._queue:
            self._index = 0
        else:
            return None
        return self.current

    def go_back(self) -> QueueItem | None:
        if self._index > 0:
            self._index -= 1
        return self.current

    def jump_to(self, index: int) -> QueueItem | None:
        if 0 <= index < len(self._queue):
            self._index = index
            return self.current
        return None

    def toggle_shuffle(self) -> bool:
        self.shuffle_enabled = not self.shuffle_enabled
        current = self.current
        if self.shuffle_enabled:
            remaining = [i for i in self._queue if i is not current]
            random.shuffle(remaining)
            self._queue = ([current] + remaining) if current else remaining
            self._index = 0
        else:
            self._queue = self._original.copy()
            if current:
                try:
                    self._index = next(
                        i for i, item in enumerate(self._queue)
                        if item.video_id == current.video_id
                    )
                except StopIteration:
                    self._index = 0
        return self.shuffle_enabled

    def toggle_repeat(self) -> RepeatMode:
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        current_i = modes.index(self.repeat_mode)
        self.repeat_mode = modes[(current_i + 1) % len(modes)]
        return self.repeat_mode

    def clear(self) -> None:
        self._queue.clear()
        self._original.clear()
        self._index = -1
