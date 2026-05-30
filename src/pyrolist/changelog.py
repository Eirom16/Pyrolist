from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "2.0.0"
CURRENT_CHANGELOG_SUMMARY = (
    "¡Pyrolist v2.0.0 ha llegado! Una actualización masiva y trascendental que introduce soporte multiidioma (i18n), "
    "aceleración gráfica con código nativo C para desenfoques ultrarrápidos, almacenamiento seguro de credenciales con llavero "
    "del sistema (keyring) y copias de seguridad de la biblioteca."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Novedades",
        (
            "Soporte Multiidioma Completo (i18n): Localización nativa completa de la interfaz en español e inglés.",
            "Aceleración Nativa en C (fast_image.c): Procesamiento y difuminado de portadas ultrarrápido compilado al vuelo para un rendimiento gráfico excepcional.",
            "Almacenamiento Seguro (Llavero del Sistema): Integración de 'keyring' para resguardar credenciales de YouTube Music y Last.fm de forma cifrada.",
            "Copias de Seguridad (Backup & Restore): Función completa para respaldar y restaurar la biblioteca local de canciones, descargas y configuraciones.",
            "Arquitectura de Testing: Configuración base con conftest y mock de VLC para realizar pruebas en sistemas headless o sin VLC nativo.",
        ),
    ),
    (
        "Correcciones",
        (
            "Migración automática y eliminación segura de archivos locales de credenciales expuestos al configurar el almacenamiento cifrado.",
            "Permisos restrictivos temporales ultra-seguros al procesar tokens de inicio de sesión de YouTube.",
        ),
    ),
)
