import platform
from loguru import logger

_DBUS_OK = False
if platform.system() == "Linux":
    try:
        import dbus
        import dbus.service
        import dbus.mainloop.glib
        _DBUS_OK = True
    except ImportError:
        logger.warning("dbus-python not available. MPRIS2 disabled.")

MPRIS2_IFACE = "org.mpris.MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
BUS_NAME = "org.mpris.MediaPlayer2.pyrolist"
OBJECT_PATH = "/org/mpris/MediaPlayer2"


class MprisPlayer:
    def __init__(self, player, queue):
        self.player = player
        self.queue = queue
        self._bus = None
        self._service = None
        self._active = False

    def start(self) -> None:
        if not _DBUS_OK:
            return
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SessionBus()
            self._bus.request_name(BUS_NAME)
            self._active = True
            logger.info(f"MPRIS2 registered as {BUS_NAME}")
        except Exception as e:
            logger.error(f"MPRIS2 registration failed: {e}")
            self._active = False

    def update_metadata(
        self,
        title: str,
        artist: str,
        album: str,
        duration_us: int,
        artwork_url: str,
    ) -> None:
        if not self._active:
            return
        try:
            if not self._bus:
                return
            obj = self._bus.get_object("org.freedesktop.DBus.Properties", OBJECT_PATH)
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
            metadata = dbus.Dictionary({
                "mpris:trackid": dbus.ObjectPath(f"/track/{title[:20].replace(' ','_')}"),
                "mpris:length": dbus.Int64(duration_us),
                "xesam:title": title,
                "xesam:artist": dbus.Array([artist], signature="s"),
                "xesam:album": album,
            }, signature="sv")
            if artwork_url:
                metadata["mpris:artUrl"] = artwork_url
            props.Set(MPRIS2_IFACE, "Metadata", metadata)
            props.Set(PLAYER_IFACE, "PlaybackStatus", "Playing")
        except dbus.exceptions.DBusException as e:
            if "not activatable" not in str(e).lower() and "unknown object" not in str(e).lower():
                logger.debug(f"MPRIS2 metadata update failed: {e}")
        except Exception as e:
            logger.debug(f"MPRIS2 metadata update failed: {e}")

    def update_playback_status(self, is_playing: bool) -> None:
        if not self._active:
            return
        try:
            if not self._bus:
                return
            obj = self._bus.get_object("org.freedesktop.DBus.Properties", OBJECT_PATH)
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
            status = "Playing" if is_playing else "Paused"
            props.Set(PLAYER_IFACE, "PlaybackStatus", status)
        except dbus.exceptions.DBusException:
            pass
        except Exception as e:
            logger.debug(f"MPRIS2 playback status update failed: {e}")

    def update_position(self, position_ms: int) -> None:
        if not self._active:
            return
        # MPRIS2 position is in microseconds
        # Position updates are typically done via Seeked signal, not polling
        # We store it for property queries
        self._position_us = position_ms * 1000

    def stop(self) -> None:
        if not self._active:
            return
        try:
            if self._bus:
                self._bus.release_name(BUS_NAME)
        except Exception:
            pass
        self._active = False