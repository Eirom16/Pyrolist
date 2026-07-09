from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "2.1.1"
CURRENT_CHANGELOG_SUMMARY = (
    "¡Pyrolist v2.1.1 ya está aquí! Esta es una actualización de corrección de errores (Hotfix) que soluciona problemas "
    "con el actualizador automático en sistemas Linux."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Correcciones",
        (
            "Actualizador en Linux: Se ha corregido un error crítico donde la aplicación se cerraba antes de que pudieras introducir la contraseña de Polkit durante las actualizaciones automáticas.",
            "Seguridad de Actualizaciones: Se ha eliminado el parche de contraseña manual y ahora se delega toda la elevación de privilegios al sistema nativo (pkexec) de forma segura y robusta.",
        ),
    ),
    (
        "Notas Adicionales",
        (
            "Esta versión incluye todas las novedades de la v2.1.0 (Vista de Artistas, notificaciones de sistema, mejoras de UI, etc.).",
        ),
    ),
)
