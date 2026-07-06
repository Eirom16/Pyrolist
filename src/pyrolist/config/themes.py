import io
import httpx
from PIL import Image
from loguru import logger

EQ_PRESETS: dict[str, tuple[float, list[float]]] = {
    "Flat":         (0.0,  [0.0]*10),
    "Bass Boost":   (2.0,  [6.0, 5.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    "Treble Boost": (0.0,  [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 4.0, 5.0, 6.0, 6.0]),
    "Vocal":        (0.0,  [-2.0,-1.0, 0.0, 2.0, 4.0, 4.0, 3.0, 2.0, 1.0, 0.0]),
    "Classical":    (0.0,  [4.0, 3.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 3.0, 4.0]),
    "Electronic":   (2.0,  [4.0, 3.0, 0.0, 2.0, 0.0, 0.0, 2.0, 3.0, 4.0, 4.0]),
    "Hip-Hop":      (2.0,  [5.0, 4.0, 2.0, 3.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0]),
    "Rock":         (1.0,  [4.0, 3.0, 2.0, 0.0,-1.0,-1.0, 0.0, 2.0, 3.0, 4.0]),
    "Jazz":         (0.0,  [3.0, 2.0, 1.0, 2.0, 0.0, 0.0, 1.0, 2.0, 3.0, 3.0]),
    "Pop":          (0.0,  [-1.0, 0.0, 2.0, 3.0, 4.0, 3.0, 2.0, 0.0,-1.0,-1.0]),
}

EQ_BAND_LABELS = [
    "60Hz", "170Hz", "310Hz", "600Hz", "1kHz",
    "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"
]


async def extract_dominant_color(image_url: str) -> str | None:
    """
    Extrae el color dominante de un artwork para usarlo como acento de tema.
    Usa módulos nativos Rust si están disponibles; fallback a Python.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(image_url)
        image_bytes = r.content

        # ── Intento con módulos nativos Rust ──────────────────────────────────
        try:
            from pyrolist.native_rs import average_center_zone, adjust_hsv
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = img.resize((50, 50), Image.LANCZOS)
            raw = img.tobytes()
            w, h = img.size
            rgb = average_center_zone(list(raw), w, h)
            if rgb:
                adjusted = adjust_hsv(rgb[0], rgb[1], rgb[2],
                                      min_saturation=0.5, min_value=0.6)
                return f"#{adjusted[0]:02x}{adjusted[1]:02x}{adjusted[2]:02x}"
        except ImportError:
            pass

        # ── Fallback Python original ──────────────────────────────────────────
        from PIL import Image
        import io
        import colorsys

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((50, 50), Image.LANCZOS)
        pixels = list(img.getdata())
        w, h = img.size

        center_pixels = [
            pixels[y * w + x]
            for y in range(int(h * 0.25), int(h * 0.75))
            for x in range(int(w * 0.25), int(w * 0.75))
        ]

        if not center_pixels:
            return None

        r_val = sum(p[0] for p in center_pixels) // len(center_pixels)
        g_val = sum(p[1] for p in center_pixels) // len(center_pixels)
        b_val = sum(p[2] for p in center_pixels) // len(center_pixels)

        h_val, s_val, v_val = colorsys.rgb_to_hsv(r_val/255, g_val/255, b_val/255)
        s_val = max(s_val, 0.5)
        v_val = max(v_val, 0.6)
        r2, g2, b2 = colorsys.hsv_to_rgb(h_val, s_val, v_val)

        return f"#{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}"

    except Exception as e:
        logger.debug(f"Color extraction failed: {e}")
        return None
