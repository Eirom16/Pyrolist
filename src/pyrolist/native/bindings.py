# src/pyrolist/native/bindings.py
"""
Bindings ctypes para fast_image.so — módulo nativo C de Pyrolist.

Carga automáticamente fast_image.so si está disponible.
Si no lo está (sin compilar, arquitectura no soportada, etc.),
todas las funciones devuelven None y el código Python original
sirve de fallback transparente.

NO importar este módulo directamente desde la UI o la lógica de negocio.
Usar siempre las funciones de alto nivel de bindings.py que ya incluyen el fallback.
"""
from __future__ import annotations

import ctypes
import os
import threading
from pathlib import Path
from loguru import logger

# ─── Carga de la librería y Sincronización ────────────────────────────────────

_lib: ctypes.CDLL | None = None
_LIB_PATH = Path(__file__).parent / "fast_image.so"
_NATIVE_AVAILABLE = False
_lock = threading.Lock()  # Lock to guarantee thread safety when calling ctypes functions concurrently


def _load_library() -> None:
    global _lib, _NATIVE_AVAILABLE

    if not _LIB_PATH.exists():
        logger.debug(
            f"Native library not found at {_LIB_PATH}. "
            "Run 'cd src/pyrolist/native && make' to compile it."
        )
        return

    try:
        _lib = ctypes.CDLL(str(_LIB_PATH))

        # ── extract_n_colors ──────────────────────────────────────────────
        _lib.extract_n_colors.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # pixels
            ctypes.c_int,                     # width
            ctypes.c_int,                     # height
            ctypes.c_int,                     # n_colors
            ctypes.POINTER(ctypes.c_uint8),  # colors_out
        ]
        _lib.extract_n_colors.restype = None

        # ── average_center_zone ───────────────────────────────────────────
        _lib.average_center_zone.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # pixels
            ctypes.c_int,                     # width
            ctypes.c_int,                     # height
            ctypes.POINTER(ctypes.c_uint8),  # out_r
            ctypes.POINTER(ctypes.c_uint8),  # out_g
            ctypes.POINTER(ctypes.c_uint8),  # out_b
        ]
        _lib.average_center_zone.restype = None

        # ── adjust_hsv ────────────────────────────────────────────────────
        _lib.adjust_hsv.argtypes = [
            ctypes.c_uint8,   # in_r
            ctypes.c_uint8,   # in_g
            ctypes.c_uint8,   # in_b
            ctypes.c_double,  # min_saturation
            ctypes.c_double,  # min_value
            ctypes.POINTER(ctypes.c_uint8),  # out_r
            ctypes.POINTER(ctypes.c_uint8),  # out_g
            ctypes.POINTER(ctypes.c_uint8),  # out_b
        ]
        _lib.adjust_hsv.restype = None

        # ── update_blobs ──────────────────────────────────────────────────
        _lib.update_blobs.argtypes = [
            ctypes.POINTER(ctypes.c_double),  # xs (in/out)
            ctypes.POINTER(ctypes.c_double),  # ys (in/out)
            ctypes.POINTER(ctypes.c_double),  # target_xs
            ctypes.POINTER(ctypes.c_double),  # target_ys
            ctypes.c_int,                      # n
            ctypes.c_double,                   # dt
            ctypes.c_double,                   # threshold_sq
        ]
        _lib.update_blobs.restype = ctypes.c_int

        _NATIVE_AVAILABLE = True
        logger.info("✓ Módulos nativos C cargados correctamente")

    except Exception as e:
        logger.warning(f"Failed to load native library: {e}. Using Python fallback.")
        _lib = None
        _NATIVE_AVAILABLE = False


_load_library()


# ─── API pública ──────────────────────────────────────────────────────────────


def extract_n_colors_native(
    image_bytes: bytes,
    n_colors: int = 3,
    resize_to: int = 60,
) -> list[tuple[int, int, int]] | None:
    """
    Extrae n_colors colores dominantes de image_bytes (JPEG/PNG/cualquier formato PIL).

    Devuelve lista de tuplas (r, g, b) con valores 0-255.
    Devuelve None si el módulo nativo no está disponible — usar fallback Python.
    """
    if not _NATIVE_AVAILABLE:
        return None

    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((resize_to, resize_to))
        raw = img.tobytes()
        w, h = img.size

        pixels_arr = (ctypes.c_uint8 * len(raw)).from_buffer_copy(raw)
        out = (ctypes.c_uint8 * (n_colors * 3))()

        with _lock:
            _lib.extract_n_colors(pixels_arr, w, h, n_colors, out)

        return [(int(out[i * 3]), int(out[i * 3 + 1]), int(out[i * 3 + 2]))
                for i in range(n_colors)]

    except Exception as e:
        logger.debug(f"extract_n_colors_native failed: {e}")
        return None


def average_center_zone_native(
    image_bytes: bytes,
    resize_to: int = 50,
) -> tuple[int, int, int] | None:
    """
    Calcula el color promedio de la zona central (25%-75%) de image_bytes.
    Equivalente al bucle Python en themes.extract_dominant_color().

    Devuelve (r, g, b) o None si no disponible.
    """
    if not _NATIVE_AVAILABLE:
        return None

    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((resize_to, resize_to))
        raw = img.tobytes()
        w, h = img.size

        pixels_arr = (ctypes.c_uint8 * len(raw)).from_buffer_copy(raw)
        out_r = ctypes.c_uint8(0)
        out_g = ctypes.c_uint8(0)
        out_b = ctypes.c_uint8(0)

        with _lock:
            _lib.average_center_zone(
                pixels_arr, w, h,
                ctypes.byref(out_r),
                ctypes.byref(out_g),
                ctypes.byref(out_b),
            )

        return (int(out_r.value), int(out_g.value), int(out_b.value))

    except Exception as e:
        logger.debug(f"average_center_zone_native failed: {e}")
        return None


def adjust_hsv_native(
    r: int, g: int, b: int,
    min_saturation: float = 0.5,
    min_value: float = 0.6,
) -> tuple[int, int, int] | None:
    """
    Ajusta saturación y brillo de un color RGB.
    Reemplaza el bloque colorsys en themes.extract_dominant_color().

    Devuelve (r, g, b) ajustados o None si no disponible.
    """
    if not _NATIVE_AVAILABLE:
        return None

    try:
        out_r = ctypes.c_uint8(0)
        out_g = ctypes.c_uint8(0)
        out_b = ctypes.c_uint8(0)

        with _lock:
            _lib.adjust_hsv(
                ctypes.c_uint8(r),
                ctypes.c_uint8(g),
                ctypes.c_uint8(b),
                ctypes.c_double(min_saturation),
                ctypes.c_double(min_value),
                ctypes.byref(out_r),
                ctypes.byref(out_g),
                ctypes.byref(out_b),
            )

        return (int(out_r.value), int(out_g.value), int(out_b.value))

    except Exception as e:
        logger.debug(f"adjust_hsv_native failed: {e}")
        return None


def update_blobs_native(
    xs: list[float],
    ys: list[float],
    target_xs: list[float],
    target_ys: list[float],
    dt: float = 0.005,
    threshold_sq: float = 0.0025,
) -> tuple[list[float], list[float], int] | None:
    """
    Actualiza posiciones de los blobs del fondo animado.
    Reemplaza el bucle Python en AmbientBackgroundWidget._on_anim_step().

    Devuelve (new_xs, new_ys, reached_count) o None si no disponible.
    """
    if not _NATIVE_AVAILABLE:
        return None

    try:
        n = len(xs)
        c_xs  = (ctypes.c_double * n)(*xs)
        c_ys  = (ctypes.c_double * n)(*ys)
        c_txs = (ctypes.c_double * n)(*target_xs)
        c_tys = (ctypes.c_double * n)(*target_ys)

        with _lock:
            reached = _lib.update_blobs(
                c_xs, c_ys, c_txs, c_tys,
                ctypes.c_int(n),
                ctypes.c_double(dt),
                ctypes.c_double(threshold_sq),
            )

        return list(c_xs), list(c_ys), int(reached)

    except Exception as e:
        logger.debug(f"update_blobs_native failed: {e}")
        return None
