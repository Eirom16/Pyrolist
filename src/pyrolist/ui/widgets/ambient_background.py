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

    def set_image(self, image_data: bytes):
        """Actualiza el fondo extrayendo colores de los bytes de la imagen."""
        if not image_data:
            self._set_colors([QColor(10, 10, 10), QColor(15, 15, 15), QColor(20, 20, 20)])
            return
            
        def on_done(future):
            try:
                colors = future.result()
            except Exception:
                colors = [QColor(20, 20, 20), QColor(40, 40, 40), QColor(30, 30, 30)]
            
            # Ejecutar en hilo principal
            import shiboken6
            if shiboken6.isValid(self):
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self, lambda: self._set_colors(colors))

        future = _executor.submit(extract_colors_from_image, image_data)
        future.add_done_callback(on_done)

    def _set_colors(self, colors: list[QColor]):
        if len(colors) >= len(self._blobs):
            # Saturar y oscurecer ligeramente los colores para que queden bien de fondo
            for i, blob in enumerate(self._blobs):
                c = colors[i]
                # Aumentar saturación, reducir valor para que el texto sea legible
                h, s, v, a = c.getHsv()
                s = min(255, int(s * 1.5))
                v = min(150, int(v * 0.8)) # max brightness 150/255 for dark mode legibility
                blob.target_color = QColor.fromHsv(h, s, v)
                
            self._color_anim.stop()
            self._color_anim.setStartValue(0.0)
            self._color_anim.setEndValue(1.0)
            self._color_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo base super oscuro
        painter.fillRect(self.rect(), QColor(5, 5, 5))
        
        w = self.width()
        h = self.height()
        
        for blob in self._blobs:
            cx = w * blob.x_ratio
            cy = h * blob.y_ratio
            radius = max(w, h) * blob.radius_ratio
            
            grad = QRadialGradient(QPointF(cx, cy), radius)
            grad.setColorAt(0, blob.current_color)
            grad.setColorAt(1, QColor(0, 0, 0, 0)) # Transparente en los bordes
            
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            
        # Añadir un overlay de ruido oscuro sutil si se desea, o simplemente desenfoque extra
        # Se asume que el radial gradient ya se ve desenfocado.
