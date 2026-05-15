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
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(image_url)
            img = Image.open(io.BytesIO(r.content)).convert("RGB")

        img = img.resize((50, 50), Image.LANCZOS)
        pixels = list(img.getdata())
        w, h = img.size

        center_pixels = [
            pixels[y * w + x]
            for y in range(int(h*0.25), int(h*0.75))
            for x in range(int(w*0.25), int(w*0.75))
        ]

        if not center_pixels:
            return None

        r = sum(p[0] for p in center_pixels) // len(center_pixels)
        g = sum(p[1] for p in center_pixels) // len(center_pixels)
        b = sum(p[2] for p in center_pixels) // len(center_pixels)

        import colorsys
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        s_val = max(s_val, 0.5)
        v_val = max(v_val, 0.6)
        r2, g2, b2 = colorsys.hsv_to_rgb(h_val, s_val, v_val)

        return f"#{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}"

    except Exception as e:
        logger.debug(f"Color extraction failed: {e}")
        return None
