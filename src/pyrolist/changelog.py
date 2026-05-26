from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "1.2.0"
CURRENT_CHANGELOG_SUMMARY = (
    "Esta versión reúne mejoras de reproducción, ajustes visuales y "
    "correcciones de estabilidad incluidas desde v1.1.9."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Novedades",
        (
            "Nuevo apartado de changelog en Acerca de para revisar los cambios de la versión instalada.",
            "Reproducción de álbumes con acciones de reproducir y mezclar desde la cola.",
            "Transición dinámica de tema para que los cambios visuales se apliquen de forma más fluida.",
            "Menú contextual en descargas y mejoras de consistencia en iconos y tarjetas.",
        ),
    ),
    (
        "Correcciones",
        (
            "Se corrigieron bloqueos visuales al aplicar estilos y cambios de tema.",
            "Se ajustó la sincronización de cola y modo aleatorio para evitar estados desactualizados.",
            "Se mejoró la legibilidad de letras sincronizadas en temas claros y oscuros.",
            "Se corrigieron detalles de interacción en paneles glass y componentes de búsqueda global.",
            "Se ajustó el build openSUSE para evitar conflictos al instalar rpm-build.",
        ),
    ),
)
