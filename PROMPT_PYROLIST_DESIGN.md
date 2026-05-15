# PROMPT DE DISEÑO — PYROLIST

## Lenguaje Visual Moderno · PySide6 + QPainter + QPropertyAnimation

## Actualización completa de UI/UX sin tocar la lógica de negocio

---

## ROL Y CONTEXTO

Eres un diseñador de interfaces y desarrollador Python especializado en crear UIs de escritorio de nivel profesional con PySide6. Tu tarea es **actualizar completamente el lenguaje visual de Pyrolist** — un cliente de YouTube Music en Python/Qt — sin modificar ningún módulo de lógica de negocio (`api/`, `audio/`, `db/`, `config/`, `system/`).

Solo tocas el directorio `ui/` y sus subdirectorios. Cada widget que crees debe ser autocontenido, reutilizable y animado. El resultado debe verse como una aplicación nativa de 2026, no como una app Qt genérica.

---

## PRINCIPIOS DE DISEÑO — LEE ESTO ANTES DE ESCRIBIR UNA SOLA LÍNEA

### Identidad visual

- **Oscuro profundo** como base. No negro puro (#000) sino capas de oscuro: `#0A0A14` (fondo base), `#10101E` (superficie), `#16162A` (superficie elevada), `#1E1E38` (superficie alta).
- **Violeta como acento primario** (`#A78BFA` / `#8B5CF6`). Secundario cyan eléctrico (`#22D3EE`) para estados activos.
- **Glassmorphism sutil** en paneles flotantes: fondo semitransparente + `blur` + borde con `rgba` de baja opacidad.
- **Esquinas muy redondeadas**: `border-radius` de 12px para tarjetas, 20px para botones, 28px para pills, 999px para toggles.
- **Tipografía:** Inter o Nunito como fuente principal. Pesos: 400 (normal), 500 (medium), 600 (semibold), 700 (bold). Nunca usar la fuente del sistema Qt por defecto.
- **Sombras suaves** con `QGraphicsDropShadowEffect` en todos los elementos elevados.
- **Micro-interacciones** en cada elemento clickable: hover con cambio de color suave (150ms), press con scale down (95%), release con spring back.

### Filosofía de animación

- Usar **`QPropertyAnimation`** con `QEasingCurve` para TODOS los cambios de estado visual.
- Curvas permitidas: `OutCubic` (movimientos de entrada), `InCubic` (salidas), `OutBack` (elementos que "aparecen" con spring), `OutElastic` para efectos de rebote especiales.
- Duración estándar: 150ms (micro), 250ms (estándar), 400ms (transiciones de pantalla), 600ms (animaciones llamativas).
- NUNCA usar cambios instantáneos de visibilidad. Todo aparece y desaparece con fade + slide.
- **`QSequentialAnimationGroup`** y **`QParallelAnimationGroup`** para animaciones compuestas.

---

## SISTEMA DE FUENTES

```python
# src/pyrolist/ui/design/fonts.py
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
import os


def load_fonts() -> None:
    """
    Carga las fuentes Inter y Nunito desde assets/fonts/.
    Descargar desde:
    - Inter: https://fonts.google.com/specimen/Inter
    - Nunito: https://fonts.google.com/specimen/Nunito
    Archivos necesarios:
      assets/fonts/Inter-Regular.ttf
      assets/fonts/Inter-Medium.ttf
      assets/fonts/Inter-SemiBold.ttf
      assets/fonts/Inter-Bold.ttf
      assets/fonts/Nunito-Regular.ttf
      assets/fonts/Nunito-SemiBold.ttf
      assets/fonts/Nunito-Bold.ttf
      assets/fonts/Nunito-ExtraBold.ttf
    """
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "fonts")
    for filename in os.listdir(fonts_dir):
        if filename.endswith(".ttf") or filename.endswith(".otf"):
            QFontDatabase.addApplicationFont(os.path.join(fonts_dir, filename))


class AppFont:
    """Fábrica de fuentes con tamaños y pesos predefinidos."""

    FAMILY = "Nunito"
    FAMILY_BODY = "Inter"

    @staticmethod
    def display(size: int = 32) -> QFont:
        """Títulos grandes — portada del full player, pantalla de bienvenida."""
        f = QFont(AppFont.FAMILY, size, QFont.Weight.ExtraBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.5)
        return f

    @staticmethod
    def heading(size: int = 20) -> QFont:
        """Encabezados de sección."""
        f = QFont(AppFont.FAMILY, size, QFont.Weight.Bold)
        return f

    @staticmethod
    def title(size: int = 16) -> QFont:
        """Nombre de canción en mini player, títulos de tarjetas."""
        f = QFont(AppFont.FAMILY, size, QFont.Weight.Bold)
        return f

    @staticmethod
    def body(size: int = 14) -> QFont:
        """Texto de cuerpo general."""
        f = QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Normal)
        return f

    @staticmethod
    def label(size: int = 12) -> QFont:
        """Artista, metadatos, etiquetas."""
        f = QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Medium)
        return f

    @staticmethod
    def caption(size: int = 10) -> QFont:
        """Timestamps, bytes, info secundaria."""
        f = QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Normal)
        return f

    @staticmethod
    def mono(size: int = 13) -> QFont:
        """Tiempo de reproducción, códigos."""
        f = QFont("JetBrains Mono", size, QFont.Weight.Medium)
        f.setStyleHint(QFont.StyleHint.Monospace)
        return f
```

---

## SISTEMA DE COLORES Y TOKENS

```python
# src/pyrolist/ui/design/tokens.py
from dataclasses import dataclass
from PySide6.QtGui import QColor


@dataclass(frozen=True)
class ColorScheme:
    # Fondos (de más oscuro a más claro)
    bg_base: str       # #0A0A14 — fondo de ventana
    bg_surface: str    # #10101E — superficie normal
    bg_elevated: str   # #16162A — tarjetas, sidebar
    bg_high: str       # #1E1E38 — menús flotantes, tooltips
    bg_overlay: str    # rgba(10,10,20,0.85) — overlays modales

    # Acentos
    accent: str        # #A78BFA — acento principal (violeta)
    accent_bright: str # #8B5CF6 — hover del acento
    accent_dim: str    # rgba(167,139,250,0.15) — fondo de acento suave
    secondary: str     # #22D3EE — acento secundario (cyan)
    secondary_dim: str # rgba(34,211,238,0.15)

    # Texto
    text_primary: str  # #F1F0FF — texto principal
    text_secondary: str # #9B9BC0 — texto secundario
    text_disabled: str # #4A4A6A — deshabilitado
    text_on_accent: str # #0A0A14 — texto sobre botones de acento

    # Bordes
    border: str        # rgba(167,139,250,0.12)
    border_focus: str  # rgba(167,139,250,0.5)

    # Estados
    success: str       # #34D399
    warning: str       # #FBBF24
    error: str         # #F87171
    info: str          # #60A5FA

    # Especiales
    like_color: str    # #F472B6 — corazón / like


DARK = ColorScheme(
    bg_base="#0A0A14",
    bg_surface="#10101E",
    bg_elevated="#16162A",
    bg_high="#1E1E38",
    bg_overlay="rgba(10,10,20,0.85)",
    accent="#A78BFA",
    accent_bright="#8B5CF6",
    accent_dim="rgba(167,139,250,0.15)",
    secondary="#22D3EE",
    secondary_dim="rgba(34,211,238,0.15)",
    text_primary="#F1F0FF",
    text_secondary="#9B9BC0",
    text_disabled="#4A4A6A",
    text_on_accent="#0A0A14",
    border="rgba(167,139,250,0.12)",
    border_focus="rgba(167,139,250,0.50)",
    success="#34D399",
    warning="#FBBF24",
    error="#F87171",
    info="#60A5FA",
    like_color="#F472B6",
)

# El esquema activo. Cambiar esto aplica el tema globalmente.
CURRENT = DARK
```

---

## WIDGET 1 — `AnimatedToggle` (interruptor moderno)

Reemplaza **todos** los `QCheckBox` en la pantalla de configuración.

```python
# src/pyrolist/ui/widgets/animated_toggle.py
from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import (
    Qt, QSize, QPointF, QRectF, QEasingCurve,
    QPropertyAnimation, QSequentialAnimationGroup,
    Property, Slot
)
from PySide6.QtGui import (
    QColor, QPainter, QPaintEvent, QBrush, QPen
)


class AnimatedToggle(QCheckBox):
    """
    Toggle switch animado que reemplaza QCheckBox.
    Usa QPropertyAnimation para animar el thumb y el track.

    Uso:
        toggle = AnimatedToggle(
            track_color="#4A4A6A",
            active_color="#A78BFA",
            thumb_color="#FFFFFF",
            pulse_color="rgba(167,139,250,0.3)"
        )
        toggle.toggled.connect(mi_slot)
    """

    def __init__(
        self,
        parent=None,
        track_color: str = "#4A4A6A",
        active_color: str = "#A78BFA",
        thumb_color: str = "#FFFFFF",
        pulse_color: str = "rgba(167,139,250,0.3)",
    ):
        super().__init__(parent)

        self._track_color = QColor(track_color)
        self._active_color = QColor(active_color)
        self._thumb_color = QColor(thumb_color)
        self._pulse_color = QColor(pulse_color)

        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Posición del thumb: 0.0 = izquierda (off), 1.0 = derecha (on)
        self._thumb_pos = 0.0
        # Radio del pulso al hacer click
        self._pulse_radius = 0.0

        # Animación del thumb
        self._thumb_anim = QPropertyAnimation(self, b"thumb_position", self)
        self._thumb_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._thumb_anim.setDuration(280)

        # Animación del pulso
        self._pulse_anim = QPropertyAnimation(self, b"pulse_radius", self)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pulse_anim.setDuration(350)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)

        # Grupo secuencial: primero pulso, luego thumb
        self._anim_group = QSequentialAnimationGroup(self)
        # En realidad los corremos en paralelo
        self.stateChanged.connect(self._animate)

    # ─── Propiedades Qt animables ──────────────────────────────────

    def _get_thumb_pos(self) -> float:
        return self._thumb_pos

    def _set_thumb_pos(self, pos: float) -> None:
        self._thumb_pos = pos
        self.update()

    thumb_position = Property(float, _get_thumb_pos, _set_thumb_pos)

    def _get_pulse(self) -> float:
        return self._pulse_radius

    def _set_pulse(self, r: float) -> None:
        self._pulse_radius = r
        self.update()

    pulse_radius = Property(float, _get_pulse, _set_pulse)

    # ─── Animación ────────────────────────────────────────────────

    @Slot(int)
    def _animate(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        end = 1.0 if checked else 0.0

        self._thumb_anim.stop()
        self._thumb_anim.setStartValue(self._thumb_pos)
        self._thumb_anim.setEndValue(end)
        self._thumb_anim.start()

        self._pulse_anim.stop()
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.start()

    # ─── Pintado ──────────────────────────────────────────────────

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        track_w, track_h = w, h
        thumb_r = h / 2 - 3
        thumb_x = 4 + self._thumb_pos * (track_w - thumb_r * 2 - 8)
        thumb_y = h / 2

        # ── Track ──
        track_color = self._track_color.copy() if not self.isChecked() \
            else self._active_color.copy()
        # Interpolación de color entre off y on
        t = self._thumb_pos
        r = int(self._track_color.red()   + t * (self._active_color.red()   - self._track_color.red()))
        g = int(self._track_color.green() + t * (self._active_color.green() - self._track_color.green()))
        b = int(self._track_color.blue()  + t * (self._active_color.blue()  - self._track_color.blue()))
        track_color = QColor(r, g, b)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(QRectF(0, 0, track_w, track_h), h / 2, h / 2)

        # ── Pulso ──
        if self._pulse_radius > 0:
            pulse_alpha = int(180 * (1 - self._pulse_radius))
            pulse_r_px = thumb_r * 1.8 * self._pulse_radius
            pc = QColor(self._pulse_color)
            pc.setAlpha(pulse_alpha)
            p.setBrush(QBrush(pc))
            p.drawEllipse(
                QPointF(thumb_x + thumb_r, thumb_y),
                pulse_r_px, pulse_r_px
            )

        # ── Thumb ──
        p.setBrush(QBrush(self._thumb_color))
        # Sombra del thumb (simulada con círculo más oscuro desplazado)
        shadow = QColor(0, 0, 0, 60)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(
            QPointF(thumb_x + thumb_r + 0.5, thumb_y + 1),
            thumb_r, thumb_r
        )
        p.setBrush(QBrush(self._thumb_color))
        p.drawEllipse(
            QPointF(thumb_x + thumb_r, thumb_y),
            thumb_r, thumb_r
        )

        p.end()

    def sizeHint(self) -> QSize:
        return QSize(52, 28)
```

---

## WIDGET 2 — `RippleButton` (botón con efecto ripple)

Reemplaza todos los `QPushButton` de acción.

```python
# src/pyrolist/ui/widgets/ripple_button.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import (
    Qt, QTimer, QPointF, QPropertyAnimation,
    QEasingCurve, Property
)
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor, QBrush,
    QRadialGradient, QMouseEvent, QFont
)


class RippleButton(QPushButton):
    """
    Botón con efecto ripple al hacer click.
    Esquinas completamente redondeadas, hover animado.

    Variantes: "primary", "secondary", "ghost", "danger"
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "primary",
        icon_name: str = "",
        parent=None
    ):
        super().__init__(text, parent)
        self.variant = variant
        self._ripple_pos = QPointF(0, 0)
        self._ripple_opacity = 0.0
        self._ripple_radius = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

        # Animación del ripple
        self._ripple_anim = QPropertyAnimation(self, b"ripple_opacity")
        self._ripple_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ripple_anim.setDuration(500)
        self._ripple_anim.setStartValue(0.35)
        self._ripple_anim.setEndValue(0.0)

        self._radius_anim = QPropertyAnimation(self, b"ripple_rad")
        self._radius_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._radius_anim.setDuration(500)

        self._apply_style()

    def _apply_style(self) -> None:
        styles = {
            "primary": """
                QPushButton {
                    background-color: #A78BFA;
                    color: #0A0A14;
                    border: none;
                    border-radius: 20px;
                    padding: 10px 28px;
                    font-family: 'Nunito';
                    font-size: 14px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #BBA4FC;
                }
                QPushButton:pressed {
                    background-color: #8B5CF6;
                }
                QPushButton:disabled {
                    background-color: #2A2A4A;
                    color: #4A4A6A;
                }
            """,
            "secondary": """
                QPushButton {
                    background-color: rgba(167,139,250,0.12);
                    color: #A78BFA;
                    border: 1px solid rgba(167,139,250,0.3);
                    border-radius: 20px;
                    padding: 10px 28px;
                    font-family: 'Nunito';
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(167,139,250,0.2);
                    border-color: rgba(167,139,250,0.6);
                }
                QPushButton:pressed {
                    background-color: rgba(167,139,250,0.3);
                }
            """,
            "ghost": """
                QPushButton {
                    background-color: transparent;
                    color: #9B9BC0;
                    border: none;
                    border-radius: 20px;
                    padding: 10px 20px;
                    font-family: 'Inter';
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.06);
                    color: #F1F0FF;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: rgba(248,113,113,0.12);
                    color: #F87171;
                    border: 1px solid rgba(248,113,113,0.3);
                    border-radius: 20px;
                    padding: 10px 28px;
                    font-family: 'Nunito';
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(248,113,113,0.2);
                }
            """,
        }
        self.setStyleSheet(styles.get(self.variant, styles["primary"]))

    # ─── Propiedades animables ─────────────────────────────────────

    def _get_opacity(self) -> float: return self._ripple_opacity
    def _set_opacity(self, v: float) -> None:
        self._ripple_opacity = v
        self.update()
    ripple_opacity = Property(float, _get_opacity, _set_opacity)

    def _get_rad(self) -> float: return self._ripple_radius
    def _set_rad(self, v: float) -> None:
        self._ripple_radius = v
        self.update()
    ripple_rad = Property(float, _get_rad, _set_rad)

    # ─── Eventos ──────────────────────────────────────────────────

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self._ripple_pos = QPointF(e.position())
        max_r = max(self.width(), self.height()) * 1.5

        self._radius_anim.stop()
        self._radius_anim.setStartValue(10.0)
        self._radius_anim.setEndValue(max_r)
        self._radius_anim.start()

        self._ripple_anim.stop()
        self._ripple_anim.start()

        super().mousePressEvent(e)

    def paintEvent(self, e: QPaintEvent) -> None:
        super().paintEvent(e)

        if self._ripple_opacity > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setClipRect(self.rect())

            ripple_color = QColor(255, 255, 255)
            ripple_color.setAlphaF(self._ripple_opacity)

            grad = QRadialGradient(self._ripple_pos, self._ripple_radius)
            grad.setColorAt(0, ripple_color)
            grad.setColorAt(1, QColor(255, 255, 255, 0))

            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(
                self._ripple_pos,
                self._ripple_radius,
                self._ripple_radius
            )
            p.end()
```

---

## WIDGET 3 — `GlassPanel` (panel glassmorphism flotante)

Para menús contextuales, tooltips, y paneles de opciones.

```python
# src/pyrolist/ui/widgets/glass_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QPoint
from PySide6.QtGui import QPainter, QPaintEvent, QColor, QBrush, QPen, QLinearGradient


class GlassPanel(QWidget):
    """
    Panel flotante con efecto glassmorphism.
    Fondo semitransparente + borde degradado + sombra difusa.
    Usa para: menús de contexto, paneles de cola, tooltips ricos.

    Uso:
        panel = GlassPanel(parent=self)
        panel.layout().addWidget(mi_contenido)
        panel.popup_at(QPoint(x, y))
    """

    def __init__(self, parent=None, blur_radius: int = 20):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._blur_radius = blur_radius
        self._opacity = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Sombra exterior
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        # Animación de entrada (fade + slide up)
        self._opacity_anim = QPropertyAnimation(self, b"panel_opacity")
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_anim.setDuration(200)

        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pos_anim.setDuration(200)

    def _get_opacity(self) -> float: return self._opacity
    def _set_opacity(self, v: float) -> None:
        self._opacity = v
        self.setWindowOpacity(v)
    panel_opacity = Property(float, _get_opacity, _set_opacity)

    def popup_at(self, pos: QPoint) -> None:
        """Muestra el panel con animación de entrada."""
        self.move(pos.x(), pos.y() + 10)
        self.show()

        # Animación: slide up + fade in
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        self._pos_anim.setStartValue(QPoint(pos.x(), pos.y() + 10))
        self._pos_anim.setEndValue(pos)
        self._pos_anim.start()

    def dismiss(self) -> None:
        """Cierra el panel con animación de salida."""
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.close)
        self._opacity_anim.start()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 16.0

        # Fondo semitransparente oscuro
        p.setBrush(QBrush(QColor(22, 22, 42, 230)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, radius, radius)

        # Borde con degradado sutil (simula luz desde arriba)
        border_grad = QLinearGradient(0, 0, 0, self.height())
        border_grad.setColorAt(0, QColor(167, 139, 250, 80))
        border_grad.setColorAt(0.5, QColor(167, 139, 250, 20))
        border_grad.setColorAt(1, QColor(167, 139, 250, 10))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QBrush(border_grad), 1.0))
        p.drawRoundedRect(rect, radius, radius)

        p.end()
```

---

## WIDGET 4 — `FadeStackedWidget` (transiciones entre pantallas)

Reemplaza el `QStackedWidget` estándar con transiciones animadas.

```python
# src/pyrolist/ui/widgets/fade_stack.py
from PySide6.QtWidgets import QStackedWidget, QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    Property
)


class FadeStackedWidget(QStackedWidget):
    """
    QStackedWidget con transición fade entre pantallas.
    Anima: fade out de la pantalla actual + slide + fade in de la nueva.

    Uso directo (reemplaza QStackedWidget en MainWindow):
        self.stack = FadeStackedWidget()
        self.stack.addWidget(home)
        self.stack.setCurrentIndexAnimated(1)
    """

    DURATION = 300  # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animating = False

    def setCurrentIndexAnimated(self, index: int) -> None:
        if self._animating or index == self.currentIndex():
            return

        current = self.currentWidget()
        next_w = self.widget(index)

        if not current or not next_w:
            self.setCurrentIndex(index)
            return

        self._animating = True

        # Efecto de opacidad en el widget ACTUAL (fade out)
        out_effect = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(out_effect)

        # Efecto de opacidad en el widget NUEVO (fade in)
        in_effect = QGraphicsOpacityEffect(next_w)
        next_w.setGraphicsEffect(in_effect)

        # Fade out
        fade_out = QPropertyAnimation(out_effect, b"opacity")
        fade_out.setDuration(self.DURATION // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade in
        fade_in = QPropertyAnimation(in_effect, b"opacity")
        fade_in.setDuration(self.DURATION // 2)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Cuando termina el fade out, cambiar la pantalla y hacer fade in
        def _switch():
            self.setCurrentIndex(index)
            fade_in.start()

        def _done():
            self._animating = False
            next_w.setGraphicsEffect(None)
            current.setGraphicsEffect(None)

        fade_out.finished.connect(_switch)
        fade_in.finished.connect(_done)
        fade_out.start()
```

---

## WIDGET 5 — `SkeletonLoader` (pantalla de carga tipo skeleton)

Para mostrar mientras cargan las listas de canciones, artistas, etc.

```python
# src/pyrolist/ui/widgets/skeleton_loader.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    Property, QSequentialAnimationGroup
)
from PySide6.QtGui import QPainter, QPaintEvent, QColor, QLinearGradient, QBrush


class SkeletonBlock(QWidget):
    """Bloque individual de skeleton con animación shimmer."""

    def __init__(self, width: int, height: int, radius: int = 8, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._radius = radius
        self._shimmer_pos = -1.0   # posición del brillo (0.0 a 1.0)

        shimmer_anim = QPropertyAnimation(self, b"shimmer", self)
        shimmer_anim.setStartValue(-0.3)
        shimmer_anim.setEndValue(1.3)
        shimmer_anim.setDuration(1500)
        shimmer_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        shimmer_anim.setLoopCount(-1)   # infinito
        shimmer_anim.start()

    def _get_shimmer(self) -> float: return self._shimmer_pos
    def _set_shimmer(self, v: float) -> None:
        self._shimmer_pos = v
        self.update()
    shimmer = Property(float, _get_shimmer, _set_shimmer)

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo base
        p.setBrush(QBrush(QColor(30, 30, 56)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), self._radius, self._radius)

        # Brillo que barre de izquierda a derecha
        w = self.width()
        shimmer_w = w * 0.4
        x = self._shimmer_pos * (w + shimmer_w) - shimmer_w

        grad = QLinearGradient(x, 0, x + shimmer_w, 0)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.5, QColor(167, 139, 250, 30))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.setBrush(QBrush(grad))
        p.drawRoundedRect(self.rect(), self._radius, self._radius)
        p.end()


def make_song_skeleton(parent=None) -> QWidget:
    """Crea un skeleton de fila de canción (artwork + título + artista)."""
    w = QWidget(parent)
    row = QHBoxLayout(w)
    row.setContentsMargins(12, 8, 12, 8)
    row.setSpacing(12)

    row.addWidget(SkeletonBlock(48, 48, radius=8))  # artwork cuadrado

    info = QVBoxLayout()
    info.setSpacing(6)
    info.addWidget(SkeletonBlock(180, 14, radius=7))   # título
    info.addWidget(SkeletonBlock(110, 11, radius=7))   # artista
    row.addLayout(info)
    row.addStretch()
    row.addWidget(SkeletonBlock(50, 11, radius=7))   # duración

    return w


def make_card_skeleton(parent=None) -> QWidget:
    """Skeleton para tarjeta de álbum/playlist (imagen + título)."""
    w = QWidget(parent)
    col = QVBoxLayout(w)
    col.setContentsMargins(8, 8, 8, 8)
    col.setSpacing(8)

    col.addWidget(SkeletonBlock(160, 160, radius=12))  # artwork cuadrado
    col.addWidget(SkeletonBlock(140, 14, radius=7))    # título
    col.addWidget(SkeletonBlock(90, 11, radius=7))     # subtítulo

    return w


class SkeletonListLoader(QWidget):
    """
    Lista de N skeletons para mostrar mientras carga el contenido.
    Se reemplaza automáticamente cuando los datos están listos.
    """

    def __init__(self, row_count: int = 6, skeleton_factory=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        factory = skeleton_factory or make_song_skeleton
        for _ in range(row_count):
            layout.addWidget(factory(self))
        layout.addStretch()
```

---

## WIDGET 6 — `AnimatedProgressBar` (barra de progreso del player)

```python
# src/pyrolist/ui/widgets/animated_progress.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    Qt, Property, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QPainter, QPaintEvent, QMouseEvent, QColor,
    QLinearGradient, QBrush
)
from typing import Callable


class AnimatedProgressBar(QWidget):
    """
    Barra de progreso interactiva con:
    - Animación suave de actualización de posición
    - Hover: muestra thumb circular
    - Click/drag: permite seek
    - Glow effect en el extremo del progreso

    Uso:
        bar = AnimatedProgressBar()
        bar.set_value(0.35)
        bar.on_seek = lambda pct: player.seek(pct * duration_ms)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)   # altura de la zona interactiva
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._value = 0.0          # 0.0 a 1.0
        self._display_value = 0.0  # animado
        self._hover = False
        self._dragging = False
        self._hover_pos = 0.0

        self.on_seek: Callable[[float], None] | None = None

        self._anim = QPropertyAnimation(self, b"display_val")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(200)

        self.setMouseTracking(True)

    def set_value(self, value: float, animated: bool = True) -> None:
        if self._dragging:
            return
        v = max(0.0, min(1.0, value))
        self._value = v
        if animated:
            self._anim.stop()
            self._anim.setStartValue(self._display_value)
            self._anim.setEndValue(v)
            self._anim.start()
        else:
            self._display_value = v
            self.update()

    def _get_display(self) -> float: return self._display_value
    def _set_display(self, v: float) -> None:
        self._display_value = v
        self.update()
    display_val = Property(float, _get_display, _set_display)

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        bar_h = 4 if not self._hover else 6  # se engrosa al hacer hover
        bar_y = (h - bar_h) / 2
        radius = bar_h / 2

        # Track
        p.setBrush(QBrush(QColor(42, 42, 74)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, bar_y, w, bar_h, radius, radius)

        # Fill con degradado
        fill_w = int(w * self._display_value)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor(139, 92, 246))   # violeta oscuro
            grad.setColorAt(1.0, QColor(167, 139, 250))  # violeta claro
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, bar_y, fill_w, bar_h, radius, radius)

            # Glow en el extremo del fill
            glow_color = QColor(167, 139, 250, 120)
            glow_grad = QLinearGradient(fill_w - 20, 0, fill_w + 5, 0)
            glow_grad.setColorAt(0, QColor(167, 139, 250, 0))
            glow_grad.setColorAt(1, glow_color)
            p.setBrush(QBrush(glow_grad))
            p.drawRoundedRect(
                max(0, fill_w - 20), bar_y, 25, bar_h, radius, radius
            )

        # Thumb (solo visible en hover o drag)
        if self._hover or self._dragging:
            thumb_x = w * (self._hover_pos if self._dragging else self._display_value)
            thumb_r = 7
            # Sombra del thumb
            p.setBrush(QBrush(QColor(0, 0, 0, 60)))
            p.drawEllipse(
                int(thumb_x - thumb_r + 1), int(h / 2 - thumb_r + 1),
                thumb_r * 2, thumb_r * 2
            )
            # Thumb blanco
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(
                int(thumb_x - thumb_r), int(h / 2 - thumb_r),
                thumb_r * 2, thumb_r * 2
            )

        p.end()

    def enterEvent(self, e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, e) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self._dragging = True
        self._seek_from_event(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        pct = max(0.0, min(1.0, e.position().x() / self.width()))
        self._hover_pos = pct
        if self._dragging:
            self._seek_from_event(e)
        self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._dragging = False
        self._seek_from_event(e)

    def _seek_from_event(self, e: QMouseEvent) -> None:
        pct = max(0.0, min(1.0, e.position().x() / self.width()))
        self._display_value = pct
        if self.on_seek:
            self.on_seek(pct)
        self.update()
```

---

## WIDGET 7 — `ToastNotification` (notificaciones flotantes)

Reemplaza los diálogos de error/éxito bloqueantes.

```python
# src/pyrolist/ui/widgets/toast.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    Property, QPoint
)
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor, QBrush, QFont
)


class ToastNotification(QWidget):
    """
    Notificación flotante no bloqueante.
    Aparece en la esquina inferior derecha, se autodestruye.

    Tipos: "success", "error", "info", "warning"

    Uso:
        Toast.show(parent_window, "Canción añadida a la cola", "success")
    """

    _COLORS = {
        "success": ("#34D399", "#0A2E1E"),
        "error":   ("#F87171", "#2E0A0A"),
        "info":    ("#60A5FA", "#0A1A2E"),
        "warning": ("#FBBF24", "#2E1E0A"),
    }
    _ICONS = {
        "success": "✓",
        "error": "✕",
        "info": "ℹ",
        "warning": "⚠",
    }

    def __init__(self, parent: QWidget, message: str, kind: str = "info"):
        super().__init__(parent, Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        accent, bg = self._COLORS.get(kind, self._COLORS["info"])
        icon = self._ICONS.get(kind, "ℹ")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 20, 12)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Nunito", 16, QFont.Weight.Bold))
        icon_label.setStyleSheet(f"color: {accent};")

        msg_label = QLabel(message)
        msg_label.setFont(QFont("Inter", 13))
        msg_label.setStyleSheet("color: #F1F0FF;")
        msg_label.setWordWrap(True)
        msg_label.setMaximumWidth(280)

        layout.addWidget(icon_label)
        layout.addWidget(msg_label)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {accent}40;
                border-radius: 14px;
            }}
        """)
        self.adjustSize()
        self._opacity = 0.0
        self.setWindowOpacity(0.0)

        # Posicionar en esquina inferior derecha
        parent_rect = parent.rect()
        x = parent_rect.width() - self.width() - 20
        y = parent_rect.height() - self.height() - 90  # sobre el mini player
        self.move(x, y)
        self.show()
        self.raise_()

        # Fade in
        self._in_anim = QPropertyAnimation(self, b"windowOpacity")
        self._in_anim.setDuration(300)
        self._in_anim.setStartValue(0.0)
        self._in_anim.setEndValue(1.0)
        self._in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._in_anim.start()

        # Auto-dismiss después de 3.5s
        QTimer.singleShot(3500, self._dismiss)

    def _dismiss(self) -> None:
        out = QPropertyAnimation(self, b"windowOpacity")
        out.setDuration(400)
        out.setStartValue(1.0)
        out.setEndValue(0.0)
        out.setEasingCurve(QEasingCurve.Type.InCubic)
        out.finished.connect(self.deleteLater)
        out.start()

    @staticmethod
    def show(parent: QWidget, message: str, kind: str = "info") -> "ToastNotification":
        return ToastNotification(parent, message, kind)
```

---

## WIDGET 8 — `IconButton` (botón circular de ícono animado)

Para los controles del mini player y full player.

```python
# src/pyrolist/ui/widgets/icon_button.py
from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve,
    Property
)
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor, QBrush,
    QIcon, QMouseEvent, QEnterEvent
)


class IconButton(QPushButton):
    """
    Botón circular con ícono. Estados: normal, hover, pressed, active.
    Animación de hover con fondo circular que aparece/desaparece.

    Parámetros:
        icon_name: nombre del ícono de Material Symbols (usar QIcon)
        size: diámetro del botón
        active_color: color cuando el botón está activo (ej: shuffle on)
    """

    def __init__(
        self,
        icon: QIcon | None = None,
        size: int = 40,
        active_color: str = "#A78BFA",
        parent=None
    ):
        super().__init__(parent)
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(size - 12, size - 12))
        self._active_color = QColor(active_color)
        self._is_active = False
        self._bg_opacity = 0.0
        self._scale = 1.0

        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        self._bg_anim = QPropertyAnimation(self, b"bg_opacity")
        self._bg_anim.setDuration(150)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def _get_bg(self) -> float: return self._bg_opacity
    def _set_bg(self, v: float) -> None:
        self._bg_opacity = v
        self.update()
    bg_opacity = Property(float, _get_bg, _set_bg)

    def enterEvent(self, e: QEnterEvent) -> None:
        self._bg_anim.stop()
        self._bg_anim.setStartValue(self._bg_opacity)
        self._bg_anim.setEndValue(1.0)
        self._bg_anim.start()

    def leaveEvent(self, e) -> None:
        self._bg_anim.stop()
        self._bg_anim.setStartValue(self._bg_opacity)
        self._bg_anim.setEndValue(0.0)
        self._bg_anim.start()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo circular con opacidad animada
        if self._bg_opacity > 0:
            color = self._active_color if self._is_active else QColor(255, 255, 255)
            color.setAlphaF(self._bg_opacity * 0.12)
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect())

        # Punto de color si está activo (debajo del ícono)
        if self._is_active:
            dot_color = self._active_color
            p.setBrush(QBrush(dot_color))
            p.drawEllipse(
                self.width() // 2 - 3,
                self.height() - 6,
                6, 4
            )

        p.end()
        # Renderizar el ícono normalmente encima
        super().paintEvent(e)
```

---

## PANTALLA DE CONFIGURACIÓN — DISEÑO COMPLETO

```python
# src/pyrolist/ui/screens/settings/__init__.py
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea,
    QLabel, QFrame, QButtonGroup, QPushButton,
    QComboBox, QSlider, QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.ui.design.fonts import AppFont
from pyrolist.config.settings import AppSettings


class SettingsRow(QWidget):
    """
    Fila estándar de configuración:
    [Ícono]  [Título]          [Widget de control]
             [Descripción]
    """

    def __init__(
        self,
        title: str,
        description: str = "",
        control: QWidget | None = None,
        parent=None
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(AppFont.body(14))
        title_label.setStyleSheet("color: #F1F0FF;")

        text_col.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setFont(AppFont.label(12))
            desc_label.setStyleSheet("color: #6B6B9B;")
            desc_label.setWordWrap(True)
            text_col.addWidget(desc_label)

        layout.addLayout(text_col)
        layout.addStretch()

        if control:
            layout.addWidget(control)

        self.setStyleSheet("""
            SettingsRow {
                border-radius: 12px;
            }
            SettingsRow:hover {
                background-color: rgba(167, 139, 250, 0.05);
            }
        """)


class SettingsSection(QWidget):
    """Grupo de filas de configuración con título de sección."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 12)
        self._layout.setSpacing(0)

        header = QLabel(title.upper())
        header.setFont(AppFont.label(11))
        header.setStyleSheet(
            "color: #6B6B9B; letter-spacing: 1.5px; "
            "padding: 16px 20px 8px 20px;"
        )
        self._layout.addWidget(header)

        self._card = QFrame()
        self._card.setStyleSheet("""
            QFrame {
                background-color: #16162A;
                border-radius: 16px;
                border: 1px solid rgba(167,139,250,0.08);
            }
        """)
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(0, 4, 0, 4)
        self._card_layout.setSpacing(0)
        self._layout.addWidget(self._card)

    def add_row(self, row: SettingsRow) -> None:
        if self._card_layout.count() > 0:
            # Separador entre filas
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: rgba(167,139,250,0.06);")
            self._card_layout.addWidget(sep)
        self._card_layout.addWidget(row)


class AccentColorPicker(QWidget):
    """
    Selector visual de colores de acento con círculos predefinidos
    + botón para color personalizado.
    """
    color_changed = Signal(str)

    PRESETS = [
        "#A78BFA",  # violeta (default)
        "#60A5FA",  # azul
        "#34D399",  # verde
        "#F472B6",  # rosa
        "#FB923C",  # naranja
        "#FBBF24",  # amarillo
        "#22D3EE",  # cyan
        "#F87171",  # rojo
    ]

    def __init__(self, current: str = "#A78BFA", parent=None):
        super().__init__(parent)
        self._current = current
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for color in self.PRESETS:
            btn = self._make_swatch(color)
            layout.addWidget(btn)

        # Botón de color personalizado
        custom_btn = QPushButton("+")
        custom_btn.setFixedSize(28, 28)
        custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_btn.setStyleSheet("""
            QPushButton {
                border: 2px dashed rgba(167,139,250,0.4);
                border-radius: 14px;
                color: #9B9BC0;
                font-size: 16px;
                background: transparent;
            }
            QPushButton:hover {
                border-color: #A78BFA;
                color: #A78BFA;
            }
        """)
        custom_btn.clicked.connect(self._pick_custom)
        layout.addWidget(custom_btn)
        layout.addStretch()

    def _make_swatch(self, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        is_active = color == self._current
        ring = f"box-shadow: 0 0 0 2px #0A0A14, 0 0 0 4px {color};" if is_active else ""
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: 14px;
                border: none;
                {ring}
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
        """)
        btn.clicked.connect(lambda checked, c=color: self.color_changed.emit(c))
        return btn

    def _pick_custom(self) -> None:
        color = QColorDialog.getColor(QColor(self._current), self)
        if color.isValid():
            self.color_changed.emit(color.name())


class SettingsScreen(QWidget):
    """
    Pantalla de configuración completa.
    Sidebar izquierda con categorías + área de contenido derecha.
    """

    CATEGORIES = [
        ("🎨", "Apariencia"),
        ("🎵", "Reproductor"),
        ("🎛", "Ecualizador"),
        ("🔗", "Cuentas"),
        ("💾", "Almacenamiento"),
        ("ℹ", "Acerca de"),
    ]

    def __init__(self, settings: AppSettings, on_settings_changed=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.on_settings_changed = on_settings_changed
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── Sidebar de categorías ────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #10101E;
                border-right: 1px solid rgba(167,139,250,0.08);
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        title = QLabel("Ajustes")
        title.setFont(AppFont.heading(18))
        title.setStyleSheet("color: #F1F0FF; padding: 0 8px 12px 8px;")
        sidebar_layout.addWidget(title)

        self._stack = FadeStackedWidget()  # usa el FadeStackedWidget del prompt anterior
        self._cat_buttons: list[QPushButton] = []

        for i, (icon, name) in enumerate(self.CATEGORIES):
            btn = self._make_cat_button(icon, name, i)
            self._cat_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        root.addWidget(sidebar)

        # ─── Área de contenido ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #0A0A14; }")

        content = QWidget()
        content.setStyleSheet("background: #0A0A14;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(0)

        # Páginas de configuración
        pages = [
            self._build_appearance_page(),
            self._build_player_page(),
            self._build_eq_page(),
            self._build_accounts_page(),
            self._build_storage_page(),
            self._build_about_page(),
        ]

        self._page_stack = QWidget()
        page_layout = QVBoxLayout(self._page_stack)
        for page in pages:
            page_layout.addWidget(page)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # Mostrar primera categoría
        self._select_category(0)

    def _make_cat_button(self, icon: str, name: str, index: int) -> QPushButton:
        btn = QPushButton(f"  {icon}  {name}")
        btn.setCheckable(True)
        btn.setFont(AppFont.body(13))
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 0 12px;
                border: none;
                border-radius: 10px;
                color: #9B9BC0;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(167,139,250,0.08);
                color: #F1F0FF;
            }
            QPushButton:checked {
                background: rgba(167,139,250,0.15);
                color: #A78BFA;
                font-weight: 600;
            }
        """)
        btn.clicked.connect(lambda: self._select_category(index))
        return btn

    def _select_category(self, index: int) -> None:
        for i, btn in enumerate(self._cat_buttons):
            btn.setChecked(i == index)

    def _build_appearance_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(0)

        title = QLabel("Apariencia")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF; margin-bottom: 24px;")
        layout.addWidget(title)

        # ── Sección: Tema ──────────────────────────────────────────────
        theme_section = SettingsSection("Tema")

        # Color de acento
        picker = AccentColorPicker(self.settings.appearance.accent_color)
        picker.color_changed.connect(self._on_accent_changed)
        theme_section.add_row(SettingsRow(
            "Color de acento",
            "Color principal de la interfaz",
            picker
        ))

        # Color dinámico
        dynamic_toggle = AnimatedToggle()
        dynamic_toggle.setChecked(self.settings.appearance.use_dynamic_color)
        dynamic_toggle.toggled.connect(
            lambda v: setattr(self.settings.appearance, "use_dynamic_color", v)
        )
        theme_section.add_row(SettingsRow(
            "Color dinámico",
            "Cambia el acento según el artwork de la canción actual",
            dynamic_toggle
        ))

        # Modo oscuro/claro
        mode_combo = QComboBox()
        mode_combo.addItems(["Oscuro", "Claro", "Seguir sistema"])
        mode_combo.setStyleSheet("""
            QComboBox {
                background: #1E1E38;
                color: #F1F0FF;
                border: 1px solid rgba(167,139,250,0.2);
                border-radius: 8px;
                padding: 6px 12px;
                font-family: 'Inter';
                min-width: 140px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1E1E38;
                color: #F1F0FF;
                selection-background-color: rgba(167,139,250,0.2);
            }
        """)
        theme_section.add_row(SettingsRow("Tema", "", mode_combo))

        layout.addWidget(theme_section)

        # ── Sección: Layout ────────────────────────────────────────────
        layout_section = SettingsSection("Interfaz")

        compact_toggle = AnimatedToggle()
        compact_toggle.setChecked(self.settings.appearance.compact_sidebar)
        layout_section.add_row(SettingsRow(
            "Sidebar compacta",
            "Reduce la barra lateral solo a íconos",
            compact_toggle
        ))

        blur_toggle = AnimatedToggle()
        blur_toggle.setChecked(self.settings.appearance.show_artwork_blur_bg)
        layout_section.add_row(SettingsRow(
            "Fondo difuminado",
            "Muestra el artwork del álbum como fondo en el reproductor",
            blur_toggle
        ))

        layout.addWidget(layout_section)
        layout.addStretch()
        return page

    def _build_player_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Reproductor")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF; margin-bottom: 24px;")
        layout.addWidget(title)

        section = SettingsSection("Audio")

        # Normalización
        norm_toggle = AnimatedToggle()
        norm_toggle.setChecked(self.settings.player.normalize_audio)
        norm_toggle.toggled.connect(
            lambda v: setattr(self.settings.player, "normalize_audio", v)
        )
        section.add_row(SettingsRow(
            "Normalizar volumen",
            "Iguala el volumen entre canciones",
            norm_toggle
        ))

        # Skip silencio
        silence_toggle = AnimatedToggle()
        silence_toggle.setChecked(self.settings.player.skip_silence)
        section.add_row(SettingsRow(
            "Saltar silencios",
            "Omite las partes silenciosas de las canciones",
            silence_toggle
        ))

        # Crossfade
        crossfade_toggle = AnimatedToggle()
        crossfade_toggle.setChecked(self.settings.player.crossfade_enabled)
        section.add_row(SettingsRow(
            "Crossfade",
            "Transición suave entre canciones",
            crossfade_toggle
        ))

        # Reanudar al iniciar
        resume_toggle = AnimatedToggle()
        resume_toggle.setChecked(self.settings.player.resume_on_startup)
        section.add_row(SettingsRow(
            "Reanudar al iniciar",
            "Continúa la última sesión al abrir la app",
            resume_toggle
        ))

        layout.addWidget(section)
        layout.addStretch()
        return page

    def _build_eq_page(self) -> QWidget:
        # La pantalla del ecualizador tiene sus propios sliders verticales
        # Implementada en ui/screens/settings/equalizer.py
        page = QLabel("→ Ver ui/screens/settings/equalizer.py")
        return page

    def _build_accounts_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Cuentas")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF; margin-bottom: 24px;")
        layout.addWidget(title)

        # ── YouTube Music ───────────────────────────────────────────────
        yt_section = SettingsSection("YouTube Music")

        # Estado de la cuenta (nombre del usuario si está logueado)
        status_label = QLabel("No conectado")
        status_label.setStyleSheet("color: #6B6B9B; font-family: 'Inter'; font-size: 13px;")

        login_btn = RippleButton("Conectar cuenta", "primary")
        logout_btn = RippleButton("Cerrar sesión", "danger")
        logout_btn.setVisible(False)

        yt_section.add_row(SettingsRow("Cuenta de Google", "", status_label))
        yt_section.add_row(SettingsRow("", "", login_btn))
        layout.addWidget(yt_section)

        # ── Last.fm ─────────────────────────────────────────────────────
        lastfm_section = SettingsSection("Last.fm")

        lastfm_toggle = AnimatedToggle()
        lastfm_toggle.setChecked(self.settings.integrations.lastfm_enabled)
        lastfm_section.add_row(SettingsRow(
            "Scrobbling",
            "Registra las canciones que escuchas en Last.fm",
            lastfm_toggle
        ))

        layout.addWidget(lastfm_section)

        # ── Discord ─────────────────────────────────────────────────────
        discord_section = SettingsSection("Discord")

        discord_toggle = AnimatedToggle()
        discord_toggle.setChecked(self.settings.integrations.discord_rpc_enabled)
        discord_section.add_row(SettingsRow(
            "Rich Presence",
            "Muestra lo que escuchas en tu perfil de Discord",
            discord_toggle
        ))

        layout.addWidget(discord_section)
        layout.addStretch()
        return page

    def _build_storage_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Almacenamiento")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF; margin-bottom: 24px;")
        layout.addWidget(title)
        layout.addStretch()
        return page

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        name = QLabel("Pyrolist")
        name.setFont(AppFont.display(32))
        name.setStyleSheet("color: #A78BFA;")

        version = QLabel("Versión 1.0.0")
        version.setFont(AppFont.body(14))
        version.setStyleSheet("color: #9B9BC0;")

        desc = QLabel(
            "Cliente de escritorio de código abierto para YouTube Music.\n"
            "Construido con Python y Qt."
        )
        desc.setFont(AppFont.body(14))
        desc.setStyleSheet("color: #9B9BC0;")
        desc.setWordWrap(True)

        github_btn = RippleButton("Ver en GitHub", "secondary")

        layout.addWidget(name)
        layout.addWidget(version)
        layout.addSpacing(16)
        layout.addWidget(desc)
        layout.addSpacing(16)
        layout.addWidget(github_btn)
        layout.addStretch()
        return page

    def _on_accent_changed(self, color: str) -> None:
        self.settings.appearance.accent_color = color
        if self.on_settings_changed:
            self.on_settings_changed(self.settings)
```

---

## QSS ACTUALIZADO — `ui/stylesheet.py`

```python
# src/pyrolist/ui/stylesheet.py
PYROLIST_QSS = """

/* ─── Fuentes globales ───────────────────────────────────── */
* {
    font-family: 'Inter', 'Nunito', sans-serif;
}

/* ─── Ventana y fondo ────────────────────────────────────── */
QMainWindow, QDialog, QWidget#root {
    background-color: #0A0A14;
    color: #F1F0FF;
}

/* ─── Sidebar ────────────────────────────────────────────── */
#navSidebar {
    background-color: #10101E;
    border-right: 1px solid rgba(167,139,250,0.07);
    min-width: 220px;
    max-width: 220px;
}

/* ─── Mini Player ────────────────────────────────────────── */
#miniPlayer {
    background-color: #10101E;
    border-top: 1px solid rgba(167,139,250,0.07);
    min-height: 80px;
    max-height: 80px;
}

/* ─── Scroll Bars ────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(167,139,250,0.2);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(167,139,250,0.5);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 5px; }
QScrollBar::handle:horizontal {
    background: rgba(167,139,250,0.2);
    border-radius: 3px;
}

/* ─── QComboBox ──────────────────────────────────────────── */
QComboBox {
    background: #1E1E38;
    color: #F1F0FF;
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 10px;
    padding: 7px 14px;
    font-family: 'Inter';
    font-size: 13px;
}
QComboBox:hover { border-color: rgba(167,139,250,0.4); }
QComboBox:focus { border-color: #A78BFA; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1E1E38;
    color: #F1F0FF;
    selection-background-color: rgba(167,139,250,0.2);
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 10px;
    padding: 4px;
}

/* ─── QLineEdit (inputs) ─────────────────────────────────── */
QLineEdit {
    background: #16162A;
    color: #F1F0FF;
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 12px;
    padding: 10px 16px;
    font-family: 'Inter';
    font-size: 14px;
    selection-background-color: rgba(167,139,250,0.3);
}
QLineEdit:focus {
    border-color: #A78BFA;
    background: #1A1A30;
}
QLineEdit::placeholder { color: #4A4A6A; }

/* ─── QSlider (volumen, EQ) ──────────────────────────────── */
QSlider::groove:horizontal {
    background: #2A2A4A;
    height: 4px;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #8B5CF6, stop:1 #A78BFA
    );
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
    border: 2px solid #A78BFA;
}
QSlider::handle:horizontal:hover {
    background: #A78BFA;
    border-color: #FFFFFF;
}

QSlider::groove:vertical {
    background: #2A2A4A;
    width: 4px;
    border-radius: 2px;
}
QSlider::sub-page:vertical {
    background: #A78BFA;
    border-radius: 2px;
}
QSlider::handle:vertical {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: 0 -5px;
    border: 2px solid #A78BFA;
}

/* ─── QTabWidget ─────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #6B6B9B;
    padding: 10px 20px;
    border: none;
    font-family: 'Nunito';
    font-size: 14px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #A78BFA;
    border-bottom: 2px solid #A78BFA;
}
QTabBar::tab:hover { color: #F1F0FF; }

/* ─── QMenu ──────────────────────────────────────────────── */
QMenu {
    background: #1E1E38;
    color: #F1F0FF;
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 14px;
    padding: 6px;
    font-family: 'Inter';
    font-size: 13px;
}
QMenu::item {
    padding: 8px 20px;
    border-radius: 10px;
}
QMenu::item:selected {
    background: rgba(167,139,250,0.15);
    color: #A78BFA;
}
QMenu::separator {
    height: 1px;
    background: rgba(167,139,250,0.08);
    margin: 4px 8px;
}

/* ─── QToolTip ───────────────────────────────────────────── */
QToolTip {
    background: #1E1E38;
    color: #F1F0FF;
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 8px;
    padding: 6px 12px;
    font-family: 'Inter';
    font-size: 12px;
}

/* ─── Etiquetas genéricas ────────────────────────────────── */
QLabel.sectionTitle {
    font-family: 'Nunito';
    font-size: 22px;
    font-weight: 800;
    color: #F1F0FF;
}
QLabel.artistName {
    font-family: 'Nunito';
    font-size: 14px;
    font-weight: 600;
    color: #9B9BC0;
}
QLabel.timestamp {
    font-family: 'JetBrains Mono';
    font-size: 12px;
    color: #6B6B9B;
}

/* ─── Tarjeta de canción ─────────────────────────────────── */
.SongRow {
    background: transparent;
    border-radius: 10px;
}
.SongRow:hover { background: rgba(167,139,250,0.06); }

/* ─── Tarjeta de álbum/playlist ─────────────────────────── */
.AlbumCard {
    background: #16162A;
    border-radius: 16px;
    border: 1px solid rgba(167,139,250,0.06);
}
.AlbumCard:hover {
    background: #1C1C34;
    border-color: rgba(167,139,250,0.2);
}
"""
```

---

## ANIMACIONES GLOBALES DE PANTALLA

```python
# src/pyrolist/ui/design/animations.py
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QPoint
)
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


def fade_in(widget: QWidget, duration: int = 250) -> QPropertyAnimation:
    """Anima el widget de 0 a opacidad total."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start()
    return anim


def slide_in_from_right(
    widget: QWidget,
    duration: int = 350,
    offset: int = 60
) -> QParallelAnimationGroup:
    """
    Hace slide + fade del widget entrando desde la derecha.
    Para transiciones entre pantallas.
    """
    start_pos = widget.pos() + QPoint(offset, 0)
    end_pos = widget.pos()

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    fade = QPropertyAnimation(effect, b"opacity")
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    slide = QPropertyAnimation(widget, b"pos")
    slide.setDuration(duration)
    slide.setStartValue(start_pos)
    slide.setEndValue(end_pos)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    group = QParallelAnimationGroup()
    group.addAnimation(fade)
    group.addAnimation(slide)
    group.finished.connect(lambda: widget.setGraphicsEffect(None))
    group.start()
    return group


def pop_in(widget: QWidget, duration: int = 300) -> QPropertyAnimation:
    """
    Efecto de "aparición" con spring: el widget escala de 0.8 a 1.0
    con una curva OutBack (rebote suave).
    Implementado via windowOpacity + QGraphicsEffect de escala.
    """
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutBack)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start()
    return anim


def pulse(widget: QWidget, color_start: str = "#A78BFA") -> None:
    """
    Destella el fondo del widget brevemente para llamar atención.
    Útil para: canción añadida a cola, like, error.
    """
    original = widget.styleSheet()
    widget.setStyleSheet(
        original + f"background-color: {color_start}20;"
    )
    from PySide6.QtCore import QTimer
    QTimer.singleShot(200, lambda: widget.setStyleSheet(original))
```

---

## SISTEMA DE ÍCONOS — MATERIAL SYMBOLS (GOOGLE FONTS)

### REGLA ABSOLUTA E INNEGOCIABLE

**PROHIBIDO usar emojis como íconos en cualquier parte de la interfaz.**
Esto incluye: botones, sidebar, menús, toasts, etiquetas, títulos, tooltips, y cualquier otro elemento visual. Los emojis se renderizan de forma inconsistente entre sistemas operativos, tienen tamaños no controlables y se ven completamente fuera de lugar en una UI profesional.

**La única fuente de íconos permitida es Material Symbols de Google Fonts**, cargada como fuente de iconos `.ttf` (variable font) directamente en Qt.

---

### Descarga e instalación

Descarga la fuente variable de Material Symbols:

```
URL: https://fonts.google.com/icons
Variante a descargar: Material Symbols Rounded (la más suave y moderna)
Archivo: MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf
```

Colócala en:

```
assets/fonts/MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf
```

Regístrala en `load_fonts()` junto con Inter y Nunito — ya está incluida en la función de carga de fuentes del módulo `fonts.py`.

---

### Módulo de íconos

```python
# src/pyrolist/ui/design/icons.py
"""
Sistema centralizado de íconos usando Material Symbols Rounded.
USO CORRECTO: Icon.get("play_arrow")  → devuelve el carácter Unicode del ícono
USO INCORRECTO: usar emojis como "▶", "⏸", "🎵", "❤️", "⚙" etc. NUNCA.

Todos los íconos disponibles en: https://fonts.google.com/icons
Busca el nombre en snake_case y úsalo con Icon.get() o Icon.label().
"""
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont


# Nombre de la fuente tal como Qt la registra tras cargarla
MATERIAL_FONT = "Material Symbols Rounded"

# Tabla de codepoints Unicode de los íconos usados en Pyrolist.
# Cada ícono tiene un codepoint único en la fuente Material Symbols.
# Referencia completa: https://fonts.google.com/icons
CODEPOINTS: dict[str, str] = {
    # ── Reproducción ──────────────────────────────────────────────────
    "play_arrow":          "\ue037",
    "pause":               "\ue034",
    "stop":                "\ue047",
    "skip_next":           "\ue044",
    "skip_previous":       "\ue045",
    "replay":              "\ue042",
    "shuffle":             "\ue043",
    "repeat":              "\ue040",
    "repeat_one":          "\ue041",
    "queue_music":         "\ue03d",
    "playlist_add":        "\ue03b",
    "playlist_play":       "\ue05f",
    "playlist_remove":     "\ueb80",
    "library_music":       "\ue030",
    "music_note":          "\ue405",
    "album":               "\ue019",
    "artist":              "\ueb99",
    "mic":                 "\ue029",
    "lyrics":              "\uec0b",
    "speed":               "\ue9c4",
    "timer":               "\ue425",
    "sleep":               "\ue4c2",

    # ── Volumen ────────────────────────────────────────────────────────
    "volume_up":           "\ue050",
    "volume_down":         "\ue04d",
    "volume_off":          "\ue04f",
    "volume_mute":         "\ue04e",

    # ── Like / Valoración ──────────────────────────────────────────────
    "favorite":            "\ue87d",
    "favorite_border":     "\ue87e",
    "thumb_up":            "\ue8dc",
    "thumb_down":          "\ue8db",

    # ── Navegación (sidebar) ───────────────────────────────────────────
    "home":                "\ue88a",
    "home_filled":         "\ue9b2",
    "search":              "\ue8b6",
    "explore":             "\ue87a",
    "library_add":         "\ue02e",
    "download":            "\uf090",
    "download_done":       "\ueb9d",
    "cloud_download":      "\ue2c0",
    "history":             "\ue889",
    "bar_chart":           "\ue26b",
    "settings":            "\ue8b8",
    "settings_outlined":   "\ue8b8",

    # ── Acciones generales ─────────────────────────────────────────────
    "add":                 "\ue145",
    "remove":              "\ue15b",
    "close":               "\ue5cd",
    "check":               "\ue5ca",
    "check_circle":        "\ue86c",
    "error":               "\ue000",
    "warning":             "\ue002",
    "info":                "\ue88e",
    "more_vert":           "\ue5d4",
    "more_horiz":          "\ue5d3",
    "edit":                "\ue3c9",
    "delete":              "\ue872",
    "share":               "\ue80d",
    "open_in_new":         "\ue89e",
    "copy":                "\ue14d",
    "link":                "\ue157",
    "refresh":             "\ue5d5",
    "sort":                "\ue164",
    "filter_list":         "\ue152",
    "drag_indicator":      "\ue945",

    # ── Cuenta y ajustes ───────────────────────────────────────────────
    "account_circle":      "\ue853",
    "person":              "\ue7fd",
    "logout":              "\ue9ba",
    "login":               "\uea77",
    "key":                 "\ue73c",
    "vpn_key":             "\ue0da",
    "palette":             "\ue40a",
    "dark_mode":           "\ue51c",
    "light_mode":          "\ue518",
    "contrast":            "\ueb37",
    "text_fields":         "\ue262",
    "tune":                "\ue429",
    "equalizer":           "\ue01d",
    "graphic_eq":          "\ue1b8",
    "notifications":       "\ue7f4",
    "notifications_off":   "\ue7f6",
    "storage":             "\ue1db",
    "folder":              "\ue2c7",
    "folder_open":         "\ue2c8",

    # ── Reproductor / Pantalla completa ────────────────────────────────
    "expand_less":         "\ue5ce",
    "expand_more":         "\ue5cf",
    "fullscreen":          "\ue5d0",
    "fullscreen_exit":     "\ue5d1",
    "chevron_left":        "\ue5cb",
    "chevron_right":       "\ue5cc",
    "arrow_back":          "\ue5c4",
    "arrow_forward":       "\ue5c8",
    "arrow_upward":        "\ue5d8",
    "arrow_downward":      "\ue5db",

    # ── Red y conexión ─────────────────────────────────────────────────
    "wifi":                "\ue63e",
    "wifi_off":            "\ue648",
    "sync":                "\ue627",
    "sync_disabled":       "\ue628",
    "cloud":               "\ue2bd",
    "cloud_off":           "\ue2c1",

    # ── Integraciones externas ─────────────────────────────────────────
    "discord":             "\uea6c",   # puede no estar — usar SVG alternativo
    "radio":               "\ue03e",
    "podcasts":            "\uef04",
    "new_releases":        "\ue031",
    "trending_up":         "\ue8e8",
    "star":                "\ue838",
    "star_border":         "\ue83a",
    "verified":            "\ue8e8",
}


class Icon:
    """
    Interfaz de acceso a íconos Material Symbols.

    Ejemplos de uso:

        # En un QLabel (más control de tamaño/color):
        label = Icon.label("play_arrow", size=28, color="#A78BFA")

        # Como string para insertar en botón con setFont:
        btn.setText(Icon.get("shuffle"))
        btn.setFont(Icon.font(24))

        # En código que dibuja con QPainter:
        painter.setFont(Icon.font(20))
        painter.drawText(rect, Qt.AlignCenter, Icon.get("favorite"))
    """

    @staticmethod
    def get(name: str) -> str:
        """
        Devuelve el carácter Unicode del ícono.
        Si el nombre no existe, devuelve "?" para que sea evidente el error
        en lugar de crashear silenciosamente.
        """
        char = CODEPOINTS.get(name)
        if char is None:
            import warnings
            warnings.warn(
                f"Icon '{name}' not found in CODEPOINTS. "
                f"Check https://fonts.google.com/icons for the correct name.",
                stacklevel=2
            )
            return "?"
        return char

    @staticmethod
    def font(size: int = 20, filled: bool = True) -> QFont:
        """
        Fuente Material Symbols lista para aplicar a cualquier QLabel o QPushButton.
        filled=True activa el estilo relleno (más reconocible).
        """
        font = QFont(MATERIAL_FONT, size)
        # Configurar ejes de la variable font:
        # FILL: 1 = relleno, 0 = contorno
        # wght: 400 = normal (no cambiar para íconos)
        # opsz: 24 = tamaño óptico estándar
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        return font

    @staticmethod
    def label(
        name: str,
        size: int = 20,
        color: str = "#F1F0FF",
        filled: bool = True,
        parent=None
    ) -> QLabel:
        """
        Crea un QLabel listo para usar como ícono.

        Ejemplo:
            play_icon = Icon.label("play_arrow", size=32, color="#A78BFA")
            layout.addWidget(play_icon)
        """
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt

        lbl = QLabel(Icon.get(name), parent)
        lbl.setFont(Icon.font(size, filled))
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(size + 8, size + 8)
        return lbl
```

---

### Configuración de la fuente variable (ejes FILL y wght)

Material Symbols es una **variable font** con cuatro ejes. Para activar el estilo
relleno (filled) en todos los íconos, añade esto al `load_fonts()`:

```python
# En src/pyrolist/ui/design/fonts.py — añadir al final de load_fonts()

def load_fonts() -> None:
    # ... carga de Inter y Nunito ...

    # Cargar Material Symbols Rounded
    font_path = os.path.join(fonts_dir, "MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf")
    if os.path.exists(font_path):
        fid = QFontDatabase.addApplicationFont(font_path)
        if fid == -1:
            import warnings
            warnings.warn("Material Symbols font failed to load. Icons will be broken.")
        else:
            families = QFontDatabase.applicationFontFamilies(fid)
            logger.info(f"Material Symbols loaded as: {families}")
    else:
        raise FileNotFoundError(
            "Material Symbols font not found at assets/fonts/. "
            "Download from https://fonts.google.com/icons"
        )
```

---

### Ejemplos de uso en los widgets del proyecto

```python
# ── En NavSidebar — sustituye los strings de texto por íconos ──────────

from pyrolist.ui.design.icons import Icon

NAV_ITEMS = [
    ("home",         "Inicio",     "/home"),
    ("search",       "Buscar",     "/search"),
    ("library_music","Biblioteca", "/library"),
    ("download",     "Descargas",  "/downloads"),
    ("settings",     "Ajustes",    "/settings"),
]

for icon_name, label_text, route in NAV_ITEMS:
    btn = QPushButton()
    btn_layout = QHBoxLayout(btn)
    btn_layout.setContentsMargins(12, 0, 12, 0)
    btn_layout.setSpacing(12)

    # Ícono Material Symbols
    icon_lbl = Icon.label(icon_name, size=22, color="#9B9BC0")
    icon_lbl.setObjectName("navIcon")

    # Texto
    text_lbl = QLabel(label_text)
    text_lbl.setFont(AppFont.body(14))

    btn_layout.addWidget(icon_lbl)
    btn_layout.addWidget(text_lbl)
    btn_layout.addStretch()


# ── En MiniPlayerWidget — controles de reproducción ───────────────────

prev_btn = IconButton(size=36)
prev_btn.setText(Icon.get("skip_previous"))
prev_btn.setFont(Icon.font(22))
prev_btn.setStyleSheet("color: #9B9BC0; border: none; background: transparent;")

play_btn = IconButton(size=48)
play_btn.setText(Icon.get("play_arrow"))    # cambia a "pause" al reproducir
play_btn.setFont(Icon.font(32))
play_btn.setStyleSheet("color: #A78BFA; border: none; background: transparent;")

next_btn = IconButton(size=36)
next_btn.setText(Icon.get("skip_next"))
next_btn.setFont(Icon.font(22))

shuffle_btn = IconButton(size=32)
shuffle_btn.setText(Icon.get("shuffle"))
shuffle_btn.setFont(Icon.font(18))

repeat_btn = IconButton(size=32)
repeat_btn.setText(Icon.get("repeat"))     # cambia a "repeat_one" según estado
repeat_btn.setFont(Icon.font(18))

like_btn = IconButton(size=32, active_color="#F472B6")
like_btn.setText(Icon.get("favorite_border"))  # "favorite" cuando está liked
like_btn.setFont(Icon.font(18))

volume_btn = IconButton(size=32)
volume_btn.setText(Icon.get("volume_up"))
volume_btn.setFont(Icon.font(18))

queue_btn = IconButton(size=32)
queue_btn.setText(Icon.get("queue_music"))
queue_btn.setFont(Icon.font(18))


# ── En ToastNotification — sustituye los emojis de tipo ───────────────

# ANTES (MAL): icon_label.setText("✓")
# DESPUÉS (BIEN):
TOAST_ICONS = {
    "success": ("check_circle", "#34D399"),
    "error":   ("error",        "#F87171"),
    "info":    ("info",         "#60A5FA"),
    "warning": ("warning",      "#FBBF24"),
}

icon_name, icon_color = TOAST_ICONS.get(kind, TOAST_ICONS["info"])
icon_lbl = Icon.label(icon_name, size=20, color=icon_color)
layout.addWidget(icon_lbl)


# ── En SettingsScreen — sustituye los emojis de categorías ────────────

# ANTES (MAL):
# CATEGORIES = [("🎨", "Apariencia"), ("🎵", "Reproductor"), ...]

# DESPUÉS (BIEN):
CATEGORIES = [
    ("palette",    "Apariencia"),
    ("graphic_eq", "Reproductor"),
    ("equalizer",  "Ecualizador"),
    ("person",     "Cuentas"),
    ("storage",    "Almacenamiento"),
    ("info",       "Acerca de"),
]

for icon_name, label_text in CATEGORIES:
    btn = QPushButton()
    row = QHBoxLayout(btn)
    row.addWidget(Icon.label(icon_name, size=18, color="#9B9BC0"))
    row.addWidget(QLabel(label_text))
    row.addStretch()


# ── En AccentColorPicker — botón de color personalizado ───────────────

# ANTES (MAL): custom_btn.setText("+")
# DESPUÉS (BIEN):
custom_btn.setText(Icon.get("add"))
custom_btn.setFont(Icon.font(18))


# ── Cambiar ícono de play/pause dinámicamente al cambiar estado ────────

def update_play_icon(is_playing: bool) -> None:
    play_btn.setText(
        Icon.get("pause") if is_playing else Icon.get("play_arrow")
    )

# Cambiar ícono de repeat según el modo:
def update_repeat_icon(mode: RepeatMode) -> None:
    icons = {
        RepeatMode.OFF: ("repeat",     "#6B6B9B"),   # gris = inactivo
        RepeatMode.ALL: ("repeat",     "#A78BFA"),   # violeta = activo
        RepeatMode.ONE: ("repeat_one", "#A78BFA"),   # repeat_one = activo
    }
    icon_name, color = icons[mode]
    repeat_btn.setText(Icon.get(icon_name))
    repeat_btn.setStyleSheet(f"color: {color}; border: none; background: transparent;")

# Cambiar ícono de volumen según nivel:
def update_volume_icon(volume: int) -> None:
    if volume == 0:
        icon = "volume_off"
    elif volume < 50:
        icon = "volume_down"
    else:
        icon = "volume_up"
    volume_btn.setText(Icon.get(icon))
```

---

### Estructura de archivos de fuentes actualizada

```
assets/fonts/
├── Inter-Regular.ttf
├── Inter-Medium.ttf
├── Inter-SemiBold.ttf
├── Inter-Bold.ttf
├── Nunito-Regular.ttf
├── Nunito-SemiBold.ttf
├── Nunito-Bold.ttf
├── Nunito-ExtraBold.ttf
└── MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf   ← NUEVO
```

Descarga directa de la fuente variable:

```
https://github.com/google/material-design-icons/tree/master/variablefont
Archivo: MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf
```

O desde Google Fonts:

```
https://fonts.google.com/icons
→ Seleccionar "Material Symbols Rounded"
→ Download family → descomprimir → coger el .ttf variable
```

---

## CHECKLIST DE IMPLEMENTACIÓN

### Widgets custom (implementar en este orden)

- [ ] `AnimatedToggle` — sustituye TODOS los QCheckBox de settings
- [ ] `RippleButton` — sustituye TODOS los QPushButton de acción
- [ ] `IconButton` — controles del player (prev, play, next, shuffle, repeat, like)
- [ ] `AnimatedProgressBar` — barra de progreso del mini player y full player
- [ ] `GlassPanel` — menú contextual de canciones, menú de cola
- [ ] `FadeStackedWidget` — transiciones entre Home/Search/Library/Settings
- [ ] `SkeletonLoader` — carga de listas (HomeScreen, SearchScreen, LibraryScreen)
- [ ] `ToastNotification` — mensajes de éxito/error (canción añadida, error de red)
- [ ] `AccentColorPicker` — selector de color en Settings > Apariencia

### Animaciones a implementar en cada pantalla

- [ ] **HomeScreen:** `fade_in` en cada sección al cargar, `slide_in_from_right` al navegar
- [ ] **SearchScreen:** dropdown de sugerencias con `GlassPanel.popup_at()`
- [ ] **Mini Player:** `pop_in` al cambiar de canción en el título y artwork
- [ ] **Full Player:** `slide_in_from_right` al abrirse como panel/dialog
- [ ] **Sidebar:** animación de `width` al colapsar/expandir (220px → 64px)
- [ ] **Queue Panel:** slide desde la derecha al activar/desactivar
- [ ] **Settings:** `fade_in` al cambiar de categoría

### Archivos de fuentes a descargar

```
assets/fonts/
├── Inter-Regular.ttf
├── Inter-Medium.ttf
├── Inter-SemiBold.ttf
├── Inter-Bold.ttf
├── Nunito-Regular.ttf
├── Nunito-SemiBold.ttf
├── Nunito-Bold.ttf
└── Nunito-ExtraBold.ttf
```

Fuentes gratuitas de Google Fonts:

- Inter: https://fonts.google.com/specimen/Inter
- Nunito: https://fonts.google.com/specimen/Nunito

### Reglas de implementación que NO se pueden romper

1. Todo cambio de visibilidad usa animación. Cero `.setVisible(True)` directos.
2. Todo botón tiene cursor `PointingHandCursor`.
3. Todo `QCheckBox` en Settings se reemplaza por `AnimatedToggle`.
4. Todo `QPushButton` de acción se reemplaza por `RippleButton`.
5. Las transiciones de pantalla siempre usan `FadeStackedWidget.setCurrentIndexAnimated()`.
6. Los mensajes de éxito/error usan `ToastNotification.show()`, nunca `QMessageBox`.
7. Las listas que cargan datos remotos muestran `SkeletonListLoader` hasta que los datos lleguen.
8. Los menús contextuales usan `GlassPanel`, nunca `QMenu` sin estilizar.

---

---

## WIDGET 9 — `CollapsibleSidebar` (sidebar animada 220px → 64px)

```python
# src/pyrolist/ui/widgets/collapsible_sidebar.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, Property, Signal
)
from PySide6.QtGui import QFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont


NAV_ITEMS = [
    ("home",          "Inicio",      "/home"),
    ("search",        "Buscar",      "/search"),
    ("library_music", "Biblioteca",  "/library"),
    ("download",      "Descargas",   "/downloads"),
    ("history",       "Historial",   "/history"),
    ("settings",      "Ajustes",     "/settings"),
]


class NavButton(QPushButton):
    """
    Botón de navegación que muestra ícono + texto en modo expandido
    y solo ícono en modo colapsado, con transición animada.
    """

    def __init__(self, icon_name: str, label: str, route: str, parent=None):
        super().__init__(parent)
        self.route = route
        self.icon_name = icon_name
        self._label_text = label
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)   # visible en modo colapsado

        layout = QVBoxLayout(self)  # usamos overlay manual
        self.setLayout(None)

        self._icon_lbl = Icon.label(icon_name, size=20, color="#9B9BC0")
        self._text_lbl = QLabel(label)
        self._text_lbl.setFont(AppFont.body(13))
        self._text_lbl.setStyleSheet("color: #9B9BC0; background: transparent;")

        from PySide6.QtWidgets import QHBoxLayout
        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.setSpacing(12)
        hl.addWidget(self._icon_lbl)
        hl.addWidget(self._text_lbl)
        hl.addStretch()

        self._apply_style(active=False)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        color = "#A78BFA" if active else "#9B9BC0"
        self._icon_lbl.setStyleSheet(
            f"color: {color}; background: transparent;"
        )
        self._text_lbl.setStyleSheet(
            f"color: {color}; background: transparent;"
            + (" font-weight: 700;" if active else "")
        )
        self._apply_style(active)

    def set_collapsed(self, collapsed: bool) -> None:
        """Oculta/muestra el texto según el estado de colapso."""
        self._text_lbl.setVisible(not collapsed)

    def _apply_style(self, active: bool) -> None:
        bg = "rgba(167,139,250,0.12)" if active else "transparent"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 12px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(167,139,250,0.08);
            }}
        """)


class CollapsibleSidebar(QWidget):
    """
    Sidebar con animación de colapso/expansión.
    Expandida: 220px (ícono + texto)
    Colapsada: 64px  (solo ícono, tooltip con nombre)
    """

    navigate = Signal(str)

    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 64

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self._current_route = "/home"
        self._nav_buttons: list[NavButton] = []

        self.setObjectName("navSidebar")
        self.setFixedWidth(self.EXPANDED_WIDTH)

        self._width_anim = QPropertyAnimation(self, b"minimumWidth")
        self._width_anim.setDuration(280)
        self._width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._max_anim = QPropertyAnimation(self, b"maximumWidth")
        self._max_anim.setDuration(280)
        self._max_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(4)

        # ── Logo / título ──────────────────────────────────────────────
        self._logo_row = QWidget()
        logo_layout = QVBoxLayout(self._logo_row)
        logo_layout.setContentsMargins(8, 0, 8, 12)
        logo_layout.setSpacing(0)

        self._app_icon = Icon.label("music_note", size=26, color="#A78BFA")
        self._app_title = QLabel("Pyrolist")
        self._app_title.setFont(AppFont.heading(18))
        self._app_title.setStyleSheet("color: #A78BFA;")

        from PySide6.QtWidgets import QHBoxLayout
        logo_hl = QHBoxLayout()
        logo_hl.setSpacing(10)
        logo_hl.addWidget(self._app_icon)
        logo_hl.addWidget(self._app_title)
        logo_hl.addStretch()
        logo_layout.addLayout(logo_hl)

        layout.addWidget(self._logo_row)

        # ── Botones de navegación ──────────────────────────────────────
        for icon_name, label, route in NAV_ITEMS:
            btn = NavButton(icon_name, label, route)
            btn.clicked.connect(lambda checked, r=route: self._on_navigate(r))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # ── Botón colapsar/expandir ────────────────────────────────────
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedHeight(40)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
                color: #6B6B9B;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.05);
                color: #F1F0FF;
            }
        """)
        self._update_toggle_icon()
        self._toggle_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self._toggle_btn)

        # Seleccionar primera ruta
        self._select(self._current_route)

    def toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        target = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH

        self._width_anim.setStartValue(self.minimumWidth())
        self._width_anim.setEndValue(target)
        self._width_anim.start()

        self._max_anim.setStartValue(self.maximumWidth())
        self._max_anim.setEndValue(target)
        self._max_anim.start()

        for btn in self._nav_buttons:
            btn.set_collapsed(self._collapsed)

        self._app_title.setVisible(not self._collapsed)
        self._update_toggle_icon()

    def _update_toggle_icon(self) -> None:
        icon_name = "chevron_left" if not self._collapsed else "chevron_right"
        self._toggle_btn.setText(Icon.get(icon_name))
        self._toggle_btn.setFont(Icon.font(20))

    def _on_navigate(self, route: str) -> None:
        self._select(route)
        self.navigate.emit(route)

    def _select(self, route: str) -> None:
        self._current_route = route
        for btn in self._nav_buttons:
            btn.set_active(btn.route == route)
```

---

## WIDGET 10 — `ScrollingLabel` (texto con scroll para títulos largos)

Para nombres de canciones que no caben en el mini player.

```python
# src/pyrolist/ui/widgets/scrolling_label.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRect, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPaintEvent, QColor, QFont, QLinearGradient, QBrush


class ScrollingLabel(QWidget):
    """
    Label que hace scroll horizontal automático cuando el texto
    no cabe en el ancho disponible. Pausa al inicio y al final.

    Uso:
        lbl = ScrollingLabel("título muy largo de una canción increíble")
        lbl.setFont(AppFont.title(14))
        lbl.setColor("#F1F0FF")
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._text = text
        self._offset = 0.0        # píxeles de desplazamiento actual
        self._color = QColor("#F1F0FF")
        self._font = QFont("Nunito", 14, QFont.Weight.Bold)
        self._scrolling = False
        self._paused = False
        self.setFixedHeight(22)

        self._anim = QPropertyAnimation(self, b"scroll_offset")
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.finished.connect(self._on_anim_finished)

        # Timer de pausa al inicio/final
        self._pause_timer = QTimer(self)
        self._pause_timer.setSingleShot(True)
        self._pause_timer.timeout.connect(self._start_scroll)

        self._check_overflow()

    def _get_offset(self) -> float: return self._offset
    def _set_offset(self, v: float) -> None:
        self._offset = v
        self.update()
    scroll_offset = Property(float, _get_offset, _set_offset)

    def setText(self, text: str) -> None:
        self._text = text
        self._offset = 0.0
        self._anim.stop()
        self._check_overflow()
        self.update()

    def setColor(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def setFont(self, font: QFont) -> None:
        self._font = font
        self._check_overflow()
        self.update()

    def _check_overflow(self) -> None:
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._text)
        self._scrolling = text_w > self.width()
        if self._scrolling:
            self._pause_timer.start(1500)  # pausa 1.5s antes de empezar

    def _start_scroll(self) -> None:
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._text)
        distance = text_w - self.width() + 20
        duration = int(distance * 18)   # ~18ms por píxel = velocidad suave

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(distance))
        self._anim.setDuration(duration)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        # Pausa al final, luego reinicia
        self._pause_timer.start(1200)
        self._offset = 0.0

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(self._font)
        p.setPen(self._color)
        p.setClipRect(self.rect())

        p.drawText(
            int(-self._offset), 0,
            self.width() + int(self._offset) + 200, self.height(),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text
        )

        # Degradado de desvanecimiento en el borde derecho
        if self._scrolling:
            fade = QLinearGradient(self.width() - 30, 0, self.width(), 0)
            fade.setColorAt(0, QColor(0, 0, 0, 0))
            fade.setColorAt(1, QColor(16, 16, 30, 255))
            p.setBrush(QBrush(fade))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(self.width() - 30, 0, 30, self.height())

        p.end()
```

---

## WIDGET 11 — `ArtworkWidget` (artwork con sombra y esquinas redondeadas)

```python
# src/pyrolist/ui/widgets/artwork_widget.py
import httpx
import asyncio
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QSize, QRect, QRectF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor, QPixmap, QBrush,
    QPainterPath, QImage
)
from loguru import logger


class ArtworkWidget(QWidget):
    """
    Widget de artwork con:
    - Esquinas redondeadas (radio configurable)
    - Sombra difusa con QGraphicsDropShadowEffect
    - Fade-in animado al cargar la imagen
    - Placeholder mientras carga (degradado animado)
    - Soporte para carga async de URL

    Uso:
        art = ArtworkWidget(size=200, corner_radius=16)
        await art.load_url("https://...")
        # o sincrono:
        art.set_pixmap(mi_pixmap)
    """

    def __init__(self, size: int = 56, corner_radius: int = 10, parent=None):
        super().__init__(parent)
        self._size = size
        self._radius = corner_radius
        self._pixmap: QPixmap | None = None
        self._opacity = 0.0
        self.setFixedSize(QSize(size, size))

        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(size // 3)
        shadow.setOffset(0, size // 12)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        # Animación de fade-in de la imagen
        self._fade_anim = QPropertyAnimation(self, b"img_opacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)

    def _get_opacity(self) -> float: return self._opacity
    def _set_opacity(self, v: float) -> None:
        self._opacity = v
        self.update()
    img_opacity = Property(float, _get_opacity, _set_opacity)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self._size, self._size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self._pixmap = scaled
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    async def load_url(self, url: str) -> None:
        """Descarga y muestra la imagen desde una URL."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(url)
            img = QImage()
            img.loadFromData(r.content)
            if not img.isNull():
                self.set_pixmap(QPixmap.fromImage(img))
        except Exception as e:
            logger.debug(f"Artwork load failed: {e}")

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self._size, self._size)

        if self._pixmap and self._opacity > 0:
            # Clip redondeado
            path = QPainterPath()
            path.addRoundedRect(rect, self._radius, self._radius)
            p.setClipPath(path)

            p.setOpacity(self._opacity)
            p.drawPixmap(0, 0, self._pixmap)
            p.setOpacity(1.0)
        else:
            # Placeholder: rectángulo oscuro redondeado
            p.setBrush(QBrush(QColor(30, 30, 56)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, self._radius, self._radius)

            # Ícono de nota musical centrado
            p.setPen(QColor(74, 74, 106))
            p.setFont(Icon.font(self._size // 3))
            p.drawText(
                QRect(0, 0, self._size, self._size),
                Qt.AlignmentFlag.AlignCenter,
                Icon.get("music_note")
            )

        p.end()
```

---

## PANTALLA — `FullPlayerDialog` (reproductor pantalla completa)

```python
# src/pyrolist/ui/widgets/full_player.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.artwork_widget import ArtworkWidget
from pyrolist.ui.widgets.animated_progress import AnimatedProgressBar
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.widgets.scrolling_label import ScrollingLabel
from pyrolist.ui.design.animations import fade_in


class FullPlayerDialog(QDialog):
    """
    Panel de reproducción completo que se abre sobre la ventana principal.
    Layout de dos columnas en pantallas anchas:
    [Artwork grande + info]  [Letras sincronizadas]
    """

    def __init__(self, player, queue, lyrics_client, parent=None):
        super().__init__(parent)
        self.player = player
        self.queue = queue
        self.lyrics_client = lyrics_client

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(parent.size() if parent else None or (1200, 800))

        self._lyrics_lines = []
        self._current_lyric_index = -1
        self._bg_color = QColor("#0A0A14")

        self._build()
        self._connect_player()
        fade_in(self, duration=300)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Fondo con blur y color dinámico ──────────────────────────────
        self._bg_panel = _BlurredBackground(self)
        self._bg_panel.setGeometry(self.rect())

        # ── Contenido sobre el fondo ──────────────────────────────────────
        content = QWidget(self)
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(48)

        # ── Columna izquierda: artwork + controles ─────────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(24)
        left_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Botón cerrar
        close_btn = IconButton(size=40)
        close_btn.setText(Icon.get("expand_more"))
        close_btn.setFont(Icon.font(28))
        close_btn.setStyleSheet("color: #9B9BC0; border: none; background: transparent;")
        close_btn.clicked.connect(self._close_animated)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        left_col.addLayout(close_row)

        # Artwork grande
        self._artwork = ArtworkWidget(size=320, corner_radius=24)
        left_col.addWidget(self._artwork, alignment=Qt.AlignmentFlag.AlignCenter)

        # Título y artista
        self._title_lbl = ScrollingLabel()
        self._title_lbl.setFont(AppFont.title(20))
        self._title_lbl.setColor("#F1F0FF")
        self._title_lbl.setFixedWidth(320)

        self._artist_lbl = QLabel()
        self._artist_lbl.setFont(AppFont.label(14))
        self._artist_lbl.setStyleSheet("color: #9B9BC0;")

        # Like
        self._like_btn = IconButton(size=32, active_color="#F472B6")
        self._like_btn.setText(Icon.get("favorite_border"))
        self._like_btn.setFont(Icon.font(20))
        self._like_btn.setStyleSheet("color: #6B6B9B; border: none; background: transparent;")

        info_row = QHBoxLayout()
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.addWidget(self._title_lbl)
        info_col.addWidget(self._artist_lbl)
        info_row.addLayout(info_col)
        info_row.addStretch()
        info_row.addWidget(self._like_btn)
        left_col.addLayout(info_row)

        # Barra de progreso
        self._progress = AnimatedProgressBar()
        self._progress.setFixedWidth(320)

        time_row = QHBoxLayout()
        self._time_current = QLabel("0:00")
        self._time_current.setFont(AppFont.mono(11))
        self._time_current.setStyleSheet("color: #6B6B9B;")
        self._time_total = QLabel("0:00")
        self._time_total.setFont(AppFont.mono(11))
        self._time_total.setStyleSheet("color: #6B6B9B;")
        time_row.addWidget(self._time_current)
        time_row.addStretch()
        time_row.addWidget(self._time_total)

        left_col.addWidget(self._progress)
        left_col.addLayout(time_row)

        # Controles principales
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._shuffle_btn = IconButton(size=36)
        self._shuffle_btn.setText(Icon.get("shuffle"))
        self._shuffle_btn.setFont(Icon.font(20))
        self._shuffle_btn.setStyleSheet("color: #6B6B9B; border: none; background: transparent;")

        self._prev_btn = IconButton(size=44)
        self._prev_btn.setText(Icon.get("skip_previous"))
        self._prev_btn.setFont(Icon.font(30))
        self._prev_btn.setStyleSheet("color: #F1F0FF; border: none; background: transparent;")

        self._play_btn = IconButton(size=64, active_color="#A78BFA")
        self._play_btn.setText(Icon.get("play_arrow"))
        self._play_btn.setFont(Icon.font(42))
        self._play_btn.setStyleSheet("""
            IconButton {
                background: #A78BFA;
                border-radius: 32px;
                color: #0A0A14;
                border: none;
            }
            IconButton:hover { background: #BBA4FC; }
            IconButton:pressed { background: #8B5CF6; }
        """)

        self._next_btn = IconButton(size=44)
        self._next_btn.setText(Icon.get("skip_next"))
        self._next_btn.setFont(Icon.font(30))
        self._next_btn.setStyleSheet("color: #F1F0FF; border: none; background: transparent;")

        self._repeat_btn = IconButton(size=36)
        self._repeat_btn.setText(Icon.get("repeat"))
        self._repeat_btn.setFont(Icon.font(20))
        self._repeat_btn.setStyleSheet("color: #6B6B9B; border: none; background: transparent;")

        controls.addWidget(self._shuffle_btn)
        controls.addWidget(self._prev_btn)
        controls.addWidget(self._play_btn)
        controls.addWidget(self._next_btn)
        controls.addWidget(self._repeat_btn)
        left_col.addLayout(controls)
        left_col.addStretch()
        content_layout.addLayout(left_col)

        # ── Columna derecha: letras sincronizadas ──────────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        lyrics_header = QLabel("Letra")
        lyrics_header.setFont(AppFont.heading(18))
        lyrics_header.setStyleSheet("color: #F1F0FF;")
        right_col.addWidget(lyrics_header)

        self._lyrics_scroll = QScrollArea()
        self._lyrics_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._lyrics_scroll.setWidgetResizable(True)
        self._lyrics_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._lyrics_container = QWidget()
        self._lyrics_container.setStyleSheet("background: transparent;")
        self._lyrics_layout = QVBoxLayout(self._lyrics_container)
        self._lyrics_layout.setSpacing(8)
        self._lyrics_layout.setContentsMargins(0, 8, 0, 80)

        self._lyrics_scroll.setWidget(self._lyrics_container)
        right_col.addWidget(self._lyrics_scroll)

        content_layout.addLayout(right_col, stretch=1)
        root.addWidget(content)

    def set_track(self, title: str, artist: str, artwork_url: str, duration_ms: int) -> None:
        self._title_lbl.setText(title)
        self._artist_lbl.setText(artist)
        self._time_total.setText(self._fmt(duration_ms))
        import asyncio
        asyncio.ensure_future(self._artwork.load_url(artwork_url))
        asyncio.ensure_future(self._load_lyrics_async(title, artist))

    async def _load_lyrics_async(self, title: str, artist: str) -> None:
        result = await self.lyrics_client.get_lyrics(title, artist)
        if result:
            self._lyrics_lines = result.lines
            self._render_lyrics()

    def _render_lyrics(self) -> None:
        # Limpiar líneas anteriores
        while self._lyrics_layout.count():
            item = self._lyrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._lyric_labels: list[QLabel] = []
        for line in self._lyrics_lines:
            lbl = QLabel(line.text)
            lbl.setFont(AppFont.body(16))
            lbl.setStyleSheet("color: #4A4A6A; background: transparent; padding: 4px 0;")
            lbl.setWordWrap(True)
            lbl.setProperty("lyric_index", len(self._lyric_labels))
            self._lyrics_layout.addWidget(lbl)
            self._lyric_labels.append(lbl)

        self._lyrics_layout.addStretch()

    def highlight_lyric(self, position_ms: int) -> None:
        """Llamado desde el callback de posición del player."""
        if not self._lyrics_lines or not self._lyric_labels:
            return

        new_index = 0
        for i, line in enumerate(self._lyrics_lines):
            if line.time_ms <= position_ms:
                new_index = i

        if new_index == self._current_lyric_index:
            return

        # Desactivar línea anterior
        if 0 <= self._current_lyric_index < len(self._lyric_labels):
            prev = self._lyric_labels[self._current_lyric_index]
            prev.setStyleSheet(
                "color: #4A4A6A; background: transparent; padding: 4px 0;"
            )

        # Activar línea actual
        self._current_lyric_index = new_index
        if new_index < len(self._lyric_labels):
            curr = self._lyric_labels[new_index]
            curr.setStyleSheet(
                "color: #F1F0FF; background: transparent; "
                "padding: 4px 0; font-size: 18px; font-weight: 700;"
            )
            # Scroll automático a la línea activa
            self._lyrics_scroll.ensureWidgetVisible(curr, 0, 80)

    def update_position(self, position_ms: int, duration_ms: int) -> None:
        self._progress.set_value(
            position_ms / duration_ms if duration_ms > 0 else 0.0
        )
        self._time_current.setText(self._fmt(position_ms))
        self.highlight_lyric(position_ms)

    def _connect_player(self) -> None:
        self.player.on("position_changed", lambda s: self.update_position(
            s.position_ms, s.duration_ms
        ))

    def _close_animated(self) -> None:
        from pyrolist.ui.design.animations import fade_in
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.close)
        anim.start()

    @staticmethod
    def _fmt(ms: int) -> str:
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"


class _BlurredBackground(QWidget):
    """
    Fondo del full player: degradado que mezcla el color dominante
    del artwork con el color base de la app. Se actualiza via set_color().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#1A1040")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        c = self._color
        c.setAlpha(200)
        grad.setColorAt(0.0, c)
        grad.setColorAt(1.0, QColor("#0A0A14"))
        p.fillRect(self.rect(), grad)
        p.end()
```

---

## PANTALLA — `EqualizerScreen` (10 sliders verticales + presets)

```python
# src/pyrolist/ui/screens/settings/equalizer.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.tokens import CURRENT as C
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.config.themes import EQ_PRESETS, EQ_BAND_LABELS


class EqBandSlider(QWidget):
    """Slider vertical para una banda del ecualizador con etiqueta."""

    value_changed = Signal(int, float)   # (band_index, gain_db)

    def __init__(self, band_index: int, label: str, parent=None):
        super().__init__(parent)
        self.band_index = band_index
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Valor en dB (arriba del slider)
        self._val_label = QLabel("0 dB")
        self._val_label.setFont(AppFont.caption(10))
        self._val_label.setStyleSheet("color: #6B6B9B;")
        self._val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._val_label)

        # Slider vertical: -12 a +12 dB (×10 para precisión de enteros Qt)
        self._slider = QSlider(Qt.Orientation.Vertical)
        self._slider.setRange(-120, 120)
        self._slider.setValue(0)
        self._slider.setFixedHeight(180)
        self._slider.setFixedWidth(28)
        self._slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #2A2A4A;
                width: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:vertical {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #8B5CF6, stop:1 #A78BFA
                );
                border-radius: 2px;
            }
            QSlider::add-page:vertical {
                background: #2A2A4A;
                border-radius: 2px;
            }
            QSlider::handle:vertical {
                background: #FFFFFF;
                width: 16px; height: 16px;
                border-radius: 8px;
                margin: 0 -6px;
                border: 2px solid #A78BFA;
            }
            QSlider::handle:vertical:hover {
                background: #A78BFA;
                border-color: #FFFFFF;
            }
        """)
        self._slider.valueChanged.connect(self._on_value)
        layout.addWidget(self._slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Línea de 0 dB (referencia visual)
        zero_line = QFrame()
        zero_line.setFrameShape(QFrame.Shape.HLine)
        zero_line.setStyleSheet("color: rgba(167,139,250,0.2); max-height: 1px;")
        layout.addWidget(zero_line)

        # Etiqueta de frecuencia (abajo)
        freq_label = QLabel(label)
        freq_label.setFont(AppFont.caption(9))
        freq_label.setStyleSheet("color: #4A4A6A;")
        freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(freq_label)

    def _on_value(self, value: int) -> None:
        db = value / 10.0
        self._val_label.setText(
            f"{'+' if db > 0 else ''}{db:.1f} dB"
        )
        color = "#A78BFA" if db != 0 else "#6B6B9B"
        self._val_label.setStyleSheet(f"color: {color};")
        self.value_changed.emit(self.band_index, db)

    def set_value(self, db: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(int(db * 10))
        self._slider.blockSignals(False)
        self._val_label.setText(
            f"{'+' if db > 0 else ''}{db:.1f} dB"
        )


class EqualizerScreen(QWidget):
    """
    Pantalla completa del ecualizador.
    10 bandas con sliders verticales + selector de presets + toggle on/off.
    """

    eq_changed = Signal(float, list)   # (preamp, [10 gains])

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._band_sliders: list[EqBandSlider] = []
        self._build()
        self._load_from_settings()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # ── Cabecera ────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel("Ecualizador")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF;")

        self._enabled_toggle = AnimatedToggle()
        self._enabled_toggle.setChecked(self.settings.equalizer.enabled)
        self._enabled_toggle.toggled.connect(self._on_enabled)

        enabled_label = QLabel("Activado")
        enabled_label.setFont(AppFont.body(13))
        enabled_label.setStyleSheet("color: #9B9BC0;")

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(enabled_label)
        header_row.addWidget(self._enabled_toggle)
        layout.addLayout(header_row)

        # ── Selector de presets ─────────────────────────────────────────
        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset")
        preset_label.setFont(AppFont.body(13))
        preset_label.setStyleSheet("color: #9B9BC0;")

        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(EQ_PRESETS.keys()))
        self._preset_combo.setCurrentText(self.settings.equalizer.preset_name)
        self._preset_combo.currentTextChanged.connect(self._apply_preset)
        self._preset_combo.setMinimumWidth(160)

        reset_btn = RippleButton("Reiniciar", "ghost")
        reset_btn.setFixedHeight(36)
        reset_btn.clicked.connect(self._reset)

        preset_row.addWidget(preset_label)
        preset_row.addWidget(self._preset_combo)
        preset_row.addStretch()
        preset_row.addWidget(reset_btn)
        layout.addLayout(preset_row)

        # ── Preamp ──────────────────────────────────────────────────────
        preamp_row = QHBoxLayout()
        preamp_label = QLabel("Preamp")
        preamp_label.setFont(AppFont.body(13))
        preamp_label.setStyleSheet("color: #9B9BC0; min-width: 60px;")

        self._preamp_slider = QSlider(Qt.Orientation.Horizontal)
        self._preamp_slider.setRange(-120, 120)
        self._preamp_slider.setValue(0)
        self._preamp_slider.setFixedHeight(28)

        self._preamp_val = QLabel("0.0 dB")
        self._preamp_val.setFont(AppFont.mono(12))
        self._preamp_val.setStyleSheet("color: #A78BFA; min-width: 56px;")
        self._preamp_slider.valueChanged.connect(
            lambda v: (
                self._preamp_val.setText(
                    f"{'+' if v/10 > 0 else ''}{v/10:.1f} dB"
                ),
                self._emit_eq()
            )
        )

        preamp_row.addWidget(preamp_label)
        preamp_row.addWidget(self._preamp_slider)
        preamp_row.addWidget(self._preamp_val)
        layout.addLayout(preamp_row)

        # ── Card de los 10 sliders ──────────────────────────────────────
        bands_card = QFrame()
        bands_card.setStyleSheet("""
            QFrame {
                background: #16162A;
                border-radius: 20px;
                border: 1px solid rgba(167,139,250,0.08);
            }
        """)
        bands_layout = QHBoxLayout(bands_card)
        bands_layout.setContentsMargins(24, 20, 24, 20)
        bands_layout.setSpacing(12)

        for i, freq_label in enumerate(EQ_BAND_LABELS):
            slider = EqBandSlider(i, freq_label)
            slider.value_changed.connect(lambda idx, db: self._emit_eq())
            self._band_sliders.append(slider)
            bands_layout.addWidget(slider)

        layout.addWidget(bands_card)
        layout.addStretch()

    def _load_from_settings(self) -> None:
        eq = self.settings.equalizer
        self._preamp_slider.setValue(int(eq.preamp * 10))
        for i, gain in enumerate(eq.bands[:10]):
            self._band_sliders[i].set_value(gain)

    def _apply_preset(self, name: str) -> None:
        preamp, bands = EQ_PRESETS.get(name, (0.0, [0.0] * 10))
        self._preamp_slider.setValue(int(preamp * 10))
        for i, gain in enumerate(bands):
            self._band_sliders[i].set_value(gain)
        self.settings.equalizer.preset_name = name
        self._emit_eq()

    def _reset(self) -> None:
        self._apply_preset("Flat")
        self._preset_combo.setCurrentText("Flat")

    def _on_enabled(self, enabled: bool) -> None:
        self.settings.equalizer.enabled = enabled
        self._emit_eq()

    def _emit_eq(self) -> None:
        preamp = self._preamp_slider.value() / 10.0
        bands = [s._slider.value() / 10.0 for s in self._band_sliders]
        self.settings.equalizer.preamp = preamp
        self.settings.equalizer.bands = bands
        self.eq_changed.emit(preamp, bands)
```

---

## MENÚ CONTEXTUAL DE CANCIÓN (GlassPanel)

```python
# src/pyrolist/ui/widgets/song_context_menu.py
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, Signal, QPoint
from pyrolist.ui.widgets.glass_panel import GlassPanel
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont


class SongContextMenu(GlassPanel):
    """
    Menú contextual glassmorphism que reemplaza QMenu para canciones.
    Se abre con popup_at(QPoint) y emite señales para cada acción.

    Acciones disponibles:
    - play_next: reproducir a continuación
    - add_to_queue: añadir al final de la cola
    - add_to_playlist: añadir a playlist
    - go_to_album: ir al álbum
    - go_to_artist: ir al artista
    - download: descargar
    - share: compartir enlace
    - like / unlike
    """

    play_next = Signal()
    add_to_queue = Signal()
    add_to_playlist = Signal()
    go_to_album = Signal()
    go_to_artist = Signal()
    download = Signal()
    share = Signal()
    like_toggled = Signal(bool)

    _ACTIONS = [
        ("play_arrow",    "Reproducir a continuación",  "play_next"),
        ("playlist_add",  "Añadir a la cola",           "add_to_queue"),
        ("add",           "Añadir a playlist",          "add_to_playlist"),
        None,   # separador
        ("album",         "Ir al álbum",                "go_to_album"),
        ("artist",        "Ir al artista",              "go_to_artist"),
        None,
        ("download",      "Descargar",                  "download"),
        ("share",         "Compartir",                  "share"),
    ]

    def __init__(self, video_id: str, is_liked: bool = False, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self._is_liked = is_liked
        self.setMinimumWidth(260)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        for action in self._ACTIONS:
            if action is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(
                    "color: rgba(167,139,250,0.08); max-height: 1px; margin: 4px 8px;"
                )
                layout.addWidget(sep)
                continue

            icon_name, label_text, signal_name = action
            btn = self._make_action_btn(icon_name, label_text, signal_name)
            layout.addWidget(btn)

        # Like (estado dinámico)
        like_icon = "favorite" if self._is_liked else "favorite_border"
        like_text = "Quitar me gusta" if self._is_liked else "Me gusta"
        like_color = "#F472B6" if self._is_liked else "#9B9BC0"
        self._like_btn = self._make_action_btn(
            like_icon, like_text, "like_toggled",
            icon_color=like_color
        )
        layout.addWidget(self._like_btn)

    def _make_action_btn(
        self,
        icon_name: str,
        label_text: str,
        signal_name: str,
        icon_color: str = "#9B9BC0"
    ) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
                text-align: left;
                padding: 0 8px;
                color: #F1F0FF;
                font-family: 'Inter';
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(167,139,250,0.10);
                color: #A78BFA;
            }
        """)

        from PySide6.QtWidgets import QHBoxLayout
        hl = QHBoxLayout(btn)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(12)

        icon_lbl = Icon.label(icon_name, size=16, color=icon_color)
        text_lbl = QLabel(label_text)
        text_lbl.setFont(AppFont.body(13))
        text_lbl.setStyleSheet("color: inherit; background: transparent;")
        text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        hl.addWidget(icon_lbl)
        hl.addWidget(text_lbl)
        hl.addStretch()

        # Conectar con la señal correspondiente
        if hasattr(self, signal_name):
            sig = getattr(self, signal_name)
            if signal_name == "like_toggled":
                btn.clicked.connect(
                    lambda: sig.emit(not self._is_liked)
                )
            else:
                btn.clicked.connect(lambda: (sig.emit(), self.dismiss()))

        return btn
```

---

## BARRA DE BÚSQUEDA CON SUGERENCIAS ANIMADAS

```python
# src/pyrolist/ui/widgets/search_bar.py
import asyncio
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.glass_panel import GlassPanel
from pyrolist.ui.widgets.icon_button import IconButton


class SearchBar(QWidget):
    """
    Barra de búsqueda con:
    - Ícono de lupa (Material Symbols, no emoji)
    - Sugerencias en tiempo real via GlassPanel
    - Debounce de 350ms para no spamear la API
    - Botón de limpiar animado
    """

    search_submitted = Signal(str)
    suggestion_selected = Signal(str)

    def __init__(self, yt_client, parent=None):
        super().__init__(parent)
        self.yt_client = yt_client
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._fetch_suggestions)
        self._suggestions_panel: GlassPanel | None = None
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Contenedor visual de la barra
        container = QWidget()
        container.setObjectName("searchContainer")
        container.setStyleSheet("""
            #searchContainer {
                background: #16162A;
                border-radius: 28px;
                border: 1px solid rgba(167,139,250,0.15);
            }
            #searchContainer:focus-within {
                border-color: #A78BFA;
                background: #1A1A30;
            }
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(16, 0, 8, 0)
        container_layout.setSpacing(8)

        # Ícono lupa
        search_icon = Icon.label("search", size=18, color="#6B6B9B")
        container_layout.addWidget(search_icon)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Buscar canciones, artistas, álbumes...")
        self._input.setFont(AppFont.body(14))
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #F1F0FF;
            }
            QLineEdit::placeholder { color: #4A4A6A; }
        """)
        self._input.setFixedHeight(44)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_enter)
        container_layout.addWidget(self._input)

        # Botón limpiar (oculto por defecto)
        self._clear_btn = IconButton(size=28)
        self._clear_btn.setText(Icon.get("close"))
        self._clear_btn.setFont(Icon.font(16))
        self._clear_btn.setStyleSheet(
            "color: #6B6B9B; border: none; background: transparent;"
        )
        self._clear_btn.setVisible(False)
        self._clear_btn.clicked.connect(self._clear)
        container_layout.addWidget(self._clear_btn)

        layout.addWidget(container)

    def _on_text_changed(self, text: str) -> None:
        self._clear_btn.setVisible(bool(text))
        if len(text) >= 2:
            self._debounce.stop()
            self._debounce.start()
        else:
            self._dismiss_suggestions()

    def _on_enter(self) -> None:
        self._dismiss_suggestions()
        q = self._input.text().strip()
        if q:
            self.search_submitted.emit(q)

    def _clear(self) -> None:
        self._input.clear()
        self._dismiss_suggestions()

    def _fetch_suggestions(self) -> None:
        query = self._input.text().strip()
        if query:
            asyncio.ensure_future(self._async_suggestions(query))

    async def _async_suggestions(self, query: str) -> None:
        try:
            suggestions = await self.yt_client.search_suggestions(query)
            self._show_suggestions(suggestions[:6])
        except Exception:
            pass

    def _show_suggestions(self, suggestions: list[str]) -> None:
        self._dismiss_suggestions()
        if not suggestions:
            return

        panel = GlassPanel(self.window())
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(2)

        for text in suggestions:
            from PySide6.QtWidgets import QPushButton
            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding: 0 12px;
                    color: #F1F0FF;
                    font-family: 'Inter';
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: rgba(167,139,250,0.10);
                    color: #A78BFA;
                }
            """)

            from PySide6.QtWidgets import QHBoxLayout
            hl = QHBoxLayout(btn)
            hl.setContentsMargins(8, 0, 8, 0)
            hl.setSpacing(10)
            hl.addWidget(Icon.label("search", size=14, color="#6B6B9B"))
            hl.addWidget(QLabel(text))
            hl.addStretch()

            btn.clicked.connect(
                lambda _, t=text: (
                    self._input.setText(t),
                    self._dismiss_suggestions(),
                    self.search_submitted.emit(t),
                )
            )
            panel_layout.addWidget(btn)

        # Posicionar debajo de la barra de búsqueda
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        panel.setMinimumWidth(self.width())
        panel.popup_at(global_pos)
        self._suggestions_panel = panel

    def _dismiss_suggestions(self) -> None:
        if self._suggestions_panel:
            self._suggestions_panel.dismiss()
            self._suggestions_panel = None
```

---

_Prompt de diseño puro para Pyrolist. No modifica lógica de negocio. Solo `ui/`._
_PySide6 · QPropertyAnimation · QEasingCurve · QPainter · QGraphicsEffect · Material Symbols Rounded_
