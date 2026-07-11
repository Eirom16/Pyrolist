from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "2.1.3"
CURRENT_CHANGELOG_SUMMARY = (
    "Pyrolist v2.1.3 corrige un problema crítico del actualizador donde una instalación exitosa "
    "podía seguir reportándose como desactualizada por metadatos internos de versión antiguos."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Correcciones críticas",
        (
            "Actualizador: La versión usada para comparar con GitHub ahora se deriva de pyrolist.__version__, evitando inconsistencias entre pantallas y lógica interna.",
            "Paquetes Arch: El PKGBUILD inyecta pkgver en el código empaquetado para que los binarios generados desde tags siempre reporten la versión correcta.",
            "Pantalla Acerca de: Limpieza de diagnósticos menores en el flujo de búsqueda manual de actualizaciones.",
        ),
    ),
)
