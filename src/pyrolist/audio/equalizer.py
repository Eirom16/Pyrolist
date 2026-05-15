from pyrolist.config.settings import AppSettings
from pyrolist.config.themes import EQ_PRESETS


class EqualizerManager:

    def __init__(self, settings: AppSettings):
        self._settings = settings

    @property
    def presets(self) -> dict[str, tuple[float, list[float]]]:
        return EQ_PRESETS

    def apply_preset(self, name: str) -> tuple[float, list[float]]:
        if name in EQ_PRESETS:
            preamp, bands = EQ_PRESETS[name]
            self._settings.equalizer.preset_name = name
            self._settings.equalizer.preamp = preamp
            self._settings.equalizer.bands = list(bands)
            return preamp, list(bands)
        return 0.0, [0.0] * 10

    def is_enabled(self) -> bool:
        return self._settings.equalizer.enabled

    def get_settings(self) -> tuple[bool, float, list[float]]:
        return (
            self._settings.equalizer.enabled,
            self._settings.equalizer.preamp,
            list(self._settings.equalizer.bands),
        )
