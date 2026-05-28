# Pyrolist v1.2.1

## Resumen

Esta versión optimiza significativamente la latencia al reproducir música local, introduce mejoras estéticas de carga con pantallas de carga tipo esqueleto (skeleton loaders) y animaciones de transición en las descargas, añade nuevos indicadores visuales y corrige varios problemas en la barra de búsqueda y el historial.

## Novedades

- **Carga optimizada de música local:** Se reduce la latencia de carga para archivos locales en el reproductor de audio de 0.5 segundos a 0.01 segundos, permitiendo una reproducción instantánea.
- **Mejoras visuales en Descargas:**
  - Nuevas pantallas de carga tipo esqueleto (*skeleton loaders*) interactivos en forma de lista y rejilla al acceder a la pantalla de descargas.
  - Efecto de animación suave con transición de desvanecimiento (*fade-in*) al cargar la lista y rejilla de descargas.
  - Nuevo indicador de canciones favoritas ("Me gusta") directamente visible en las canciones descargadas.
- **Movimiento fluido en Paneles Glass:** Transición de movimiento suave mediante animación cuando el panel flotante ya está visible, evitando saltos bruscos al cambiar su posición.

## Correcciones y bugs solucionados

- **Corrección de estadísticas:** Solucionado el error al desempaquetar el historial que provocaba fallos de carga en la pantalla de estadísticas.
- **Optimización de Búsqueda Global:**
  - Se detienen correctamente los temporizadores de sugerencias en segundo plano al ocultar, limpiar o confirmar una búsqueda, evitando posibles fugas de recursos.
  - Se valida que las sugerencias recibidas coincidan exactamente con la búsqueda activa para evitar la sobreescritura con resultados lentos obsoletos.

## Build y release

- Versión subida a `1.2.1` / `v1.2.1`.
- El workflow de compilación construirá paquetes para Arch (.pkg.tar.zst), Debian/Ubuntu (.deb), Fedora/RHEL (.rpm), openSUSE (.rpm) y Windows (.exe).
