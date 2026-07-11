from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "2.1.2"
CURRENT_CHANGELOG_SUMMARY = (
    "¡Pyrolist v2.1.2 ya está aquí! Esta es una actualización menor de mantenimiento que optimiza la gestión "
    "de versiones en compilaciones y corrige pequeños detalles en los diálogos de actualización."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Correcciones y Mantenimiento",
        (
            "Gestión de versiones: Sincronización automática de versiones a través de todos los binarios durante las compilaciones multiplataforma.",
            "Diálogos UI: Mejoras menores y prevención de cierre accidental mientras se descargan las actualizaciones.",
        ),
    ),
)
