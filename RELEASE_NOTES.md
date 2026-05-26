# Pyrolist v1.2.0

## Resumen

Esta versión añade un changelog visible desde Acerca de, mejora la reproducción de álbumes y refuerza la estabilidad visual de la aplicación. También deja preparado el workflow para publicar estas notas en el apartado de Releases junto con los paquetes compilados.

## Novedades

- Nuevo apartado Changelog en Acerca de con los cambios de la versión instalada.
- Reproducción de álbumes con acciones de reproducir y mezclar desde la cola.
- Transición dinámica de tema para aplicar cambios visuales con menos cortes.
- Menú contextual en descargas y ajustes de consistencia para iconos, tarjetas y navegación.

## Correcciones y bugs solucionados

- Se corrigieron bloqueos visuales al aplicar estilos y cambios de tema.
- Se ajustó la sincronización de cola y modo aleatorio para evitar estados desactualizados.
- Se mejoró la legibilidad de letras sincronizadas en temas claros y oscuros.
- Se corrigieron detalles de interacción en paneles glass, búsqueda global y componentes de descarga.
- Se redujeron inconsistencias de espaciado y renderizado entre pantallas de biblioteca, álbumes, playlists y reproducción.

## Build y release

- Versión subida a `1.2.0` / `v1.2.0`.
- El workflow de GitHub Actions ahora usa este informe como cuerpo del release y mantiene las notas automáticas generadas por GitHub.
- Se corrigió la instalación de dependencias del build openSUSE para evitar conflictos entre `busybox-gawk` y `rpm-build`.
