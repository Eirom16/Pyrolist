# Pyrolist v2.1.2

## Resumen

¡Pyrolist v2.1.2 ya está aquí! Esta es una actualización menor de mantenimiento enfocada en optimizar nuestros flujos de compilación y mejorar la estabilidad de la interfaz en los diálogos de actualización.

## Mejoras y Correcciones de Errores

- **Mantenimiento Interno:** Se ha implementado la sincronización automática de versiones en el workflow multiplataforma, asegurando que todos los componentes (incluidos `__init__.py` y `updater.py`) siempre reflejen la versión correcta del tag del lanzamiento sin necesidad de intervención manual.
- **Diálogos de Actualización:** Corrección de la obtención de la ventana padre (`parentWidget()`) y prevención de cierre del diálogo si una descarga de actualización ya ha comenzado.

## Build y release

- Versión subida a `2.1.2` / `v2.1.2`.
- El workflow de compilación multiplataforma generará paquetes nativos actualizados para todos los sistemas soportados.
