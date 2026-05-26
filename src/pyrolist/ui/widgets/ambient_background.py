import math
import random
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QVariantAnimation, QPointF, QEasingCurve
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QPainterPath

import concurrent.futures
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="ambient")

def extract_colors_from_image(image_data: bytes) -> list[QColor]:
    """Extrait 3 colores dominantes de los bytes de una imagen usando PIL."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_data))
        img = img.convert("RGB")
        
        # Redimensionar a muy pequeño para promediar zonas
        img = img.resize((3, 3), Image.Resampling.LANCZOS)
        
        # Obtener color predominante de diferentes áreas
        pixels = img.load()
        c1 = pixels[0, 0] # top-left
        c2 = pixels[2, 2] # bottom-right
        c3 = pixels[1, 1] # center
        
        # Asegurarse de que no sean idénticos, o agregar algo de variación
        return [
            QColor(c1[0], c1[1], c1[2]),
            QColor(c2[0], c2[1], c2[2]),
            QColor(c3[0], c3[1], c3[2])
        ]
    except Exception as e:
        from loguru import logger
        logger.warning(f"Error extracting colors: {e}")
        # Colores por defecto si falla
        return [QColor(20, 20, 20), QColor(40, 40, 40), QColor(30, 30, 30)]

class AmbientBlob:
    def __init__(self, color: QColor, x_ratio: float, y_ratio: float, radius_ratio: float):
        self.target_color = color
        self.current_color = color
        self.x_ratio = x_ratio
        self.y_ratio = y_ratio
        self.target_x_ratio = x_ratio
        self.target_y_ratio = y_ratio
        self.radius_ratio = radius_ratio

class AmbientBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        
        self._blobs = [
            AmbientBlob(QColor(10, 10, 10), 0.2, 0.2, 0.8),
            AmbientBlob(QColor(15, 15, 15), 0.8, 0.8, 0.9),
            AmbientBlob(QColor(20, 20, 20), 0.5, 0.5, 1.0)
        ]
        self._raw_colors = []
        
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(15000) # 15 seconds for a full fluid movement cycle
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1) # infinite
        self._anim.valueChanged.connect(self._on_anim_step)
        
        # Fade animation for color transitions
        self._color_anim = QVariantAnimation(self)
        self._color_anim.setDuration(2000)
        self._color_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._color_anim.valueChanged.connect(self._on_color_fade)
        
        self._generate_new_targets()
        self._anim.start()
        self.update_theme_styles()

    def _generate_new_targets(self):
        """Genera nuevas posiciones objetivo para que los blobs se muevan suavemente."""
        for blob in self._blobs:
            blob.target_x_ratio = random.uniform(0.1, 0.9)
            blob.target_y_ratio = random.uniform(0.1, 0.9)

    def _on_anim_step(self, val):
        # Mover lentamente los blobs hacia su objetivo
        dt = 0.005
        reached_targets = 0
        for blob in self._blobs:
            dx = blob.target_x_ratio - blob.x_ratio
            dy = blob.target_y_ratio - blob.y_ratio
            
            blob.x_ratio += dx * dt
            blob.y_ratio += dy * dt
            
            if abs(dx) < 0.05 and abs(dy) < 0.05:
                reached_targets += 1
                
        if reached_targets == len(self._blobs):
            self._generate_new_targets()
            
        self.update()

    def _on_color_fade(self, progress: float):
        for blob in self._blobs:
            # Interpolar color actual hacia el objetivo
            r = int(blob.current_color.red() + (blob.target_color.red() - blob.current_color.red()) * progress)
            g = int(blob.current_color.green() + (blob.target_color.green() - blob.current_color.green()) * progress)
            b = int(blob.current_color.blue() + (blob.target_color.blue() - blob.current_color.blue()) * progress)
            blob.current_color = QColor(r, g, b)
        self.update()

    def update_theme_styles(self):
        """Refreshes the dynamic blob colors when the theme changes."""
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        is_light = QColor(tokens.CURRENT.bg_base).lightness() > 128
        
        if getattr(self, "_using_default_colors", True) or not getattr(self, "_raw_colors", None):
            self._using_default_colors = True
            if is_light:
                self._raw_colors = [QColor(230, 230, 250), QColor(240, 248, 255), QColor(245, 245, 250)]
            else:
                self._raw_colors = [QColor(30, 20, 50), QColor(20, 40, 50), QColor(40, 20, 40)]
        
        self._set_colors(self._raw_colors)

    def set_image(self, image_data: bytes):
        """Actualiza el fondo extrayendo colores de los bytes de la imagen."""
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        is_light = QColor(tokens.CURRENT.bg_base).lightness() > 128
        
        if not image_data:
            self._using_default_colors = True
            if is_light:
                default_colors = [QColor(230, 230, 250), QColor(240, 248, 255), QColor(245, 245, 250)]
            else:
                default_colors = [QColor(30, 20, 50), QColor(20, 40, 50), QColor(40, 20, 40)]
            self._raw_colors = default_colors
            self._set_colors(default_colors)
            return
            
        def on_done(future):
            try:
                colors = future.result()
            except Exception:
                if is_light:
                    colors = [QColor(230, 230, 250), QColor(240, 248, 255), QColor(245, 245, 250)]
                else:
                    colors = [QColor(30, 20, 50), QColor(20, 40, 50), QColor(40, 20, 40)]
            
            # Ejecutar en hilo principal
            import shiboken6
            if shiboken6.isValid(self):
                from PySide6.QtCore import QTimer
                def apply_colors():
                    self._using_default_colors = False
                    self._raw_colors = colors
                    self._set_colors(colors)
                QTimer.singleShot(0, self, apply_colors)

        future = _executor.submit(extract_colors_from_image, image_data)
        future.add_done_callback(on_done)

    def _set_colors(self, colors: list[QColor]):
        from pyrolist.ui.design import tokens
        is_light = QColor(tokens.CURRENT.bg_base).lightness() > 128
        
        if len(colors) >= len(self._blobs):
            for i, blob in enumerate(self._blobs):
                c = colors[i]
                # Convert to HSV to manipulate
                h, s, v, a = c.getHsv()
                
                if is_light:
                    # Light mode: bright, soft pastel colors
                    s = min(80, int(s * 0.4))       # Low saturation (pastel)
                    v = max(220, int(255 - (255 - v) * 0.3)) # High brightness
                    alpha = 100                     # Subtle opacity for blending
                else:
                    # Dark mode: vibrant, visible glowing aura
                    s = max(100, min(255, int(s * 1.5))) # Boost saturation for rich depth
                    v = max(55, min(115, int(v * 0.8)))   # Make it bright enough to be visible, but dark enough to keep text readable
                    alpha = 150                     # Ideal opacity for dark atmospheric glow
                
                new_color = QColor.fromHsv(h, s, v)
                new_color.setAlpha(alpha)
                blob.target_color = new_color
                
            self._color_anim.stop()
            self._color_anim.setStartValue(0.0)
            self._color_anim.setEndValue(1.0)
            self._color_anim.start()

    def paintEvent(self, event):
        from pyrolist.ui.design import tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base background: dynamic base theme color
        painter.fillRect(self.rect(), QColor(tokens.CURRENT.bg_base))
        
        w = self.width()
        h = self.height()
        
        # Draw blobs
        for blob in self._blobs:
            cx = w * blob.x_ratio
            cy = h * blob.y_ratio
            # Reduce radius slightly to create more distinct light pools
            radius = max(w, h) * (blob.radius_ratio * 0.7)
            
            grad = QRadialGradient(QPointF(cx, cy), radius)
            grad.setColorAt(0, blob.current_color)
            
            # Fade out to fully transparent
            transparent_color = QColor(blob.current_color)
            transparent_color.setAlpha(0)
            grad.setColorAt(1, transparent_color)
            
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            
        # Añadir un overlay de ruido oscuro sutil si se desea, o simplemente desenfoque extra
        # Se asume que el radial gradient ya se ve desenfocado.
