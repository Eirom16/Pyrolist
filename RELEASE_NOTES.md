# Pyrolist v1.3.0

## Resumen

Esta versión representa una de las actualizaciones de rendimiento y estabilidad estructural más importantes de Pyrolist. Introduce la centralización de hilos mediante pools de E/S y CPU, implementa un sistema inteligente de caché en memoria de 5 minutos para metadatos, optimiza drásticamente la latencia y la eficiencia de descarga de portadas, y añade mejoras críticas para evitar micro-congelamientos de la interfaz gráfica al cargar contenido masivo.

## Novedades y Mejoras de Rendimiento

- **Pools de Hilos Centralizados:** Consolidación estructural de subprocesos en pools administrados globales (`IO_POOL` de 6 hilos para descargas/escalado y `CPU_POOL` de 2 hilos para análisis de color y cálculo computacional). Esto reduce de forma masiva el consumo de memoria al evitar la creación descontrolada de hilos.
- **Caché de Metadatos de 5 Minutos:** Implementación de un sistema de caché en memoria de corto plazo (300 segundos) para consultas de álbumes, artistas y listas de reproducción. Las transiciones entre pantallas ahora son instantáneas sin necesidad de llamadas redundantes a la API de YouTube Music.
- **Reducción de Consumo de CPU (AmbientBackground):** El fondo dinámico fluido de la interfaz ahora limita su refresco de renderizado a un máximo de **20 FPS** (intervalo de 50ms) en lugar de intentar ejecutarse a 60 FPS. Esto ahorra una enorme cantidad de ciclos de CPU y prolonga la vida útil de la batería en ordenadores portátiles.
- **Persistencia de Sesión HTTP (Reutilización de Sockets):** El gestor de imágenes (`ImageCache`) ahora utiliza un cliente HTTP asíncrono persistente (`httpx.AsyncClient`) con límites optimizados. Se elimina la sobrecarga de apertura y cierre de sockets TCP/TLS en cada descarga de portada, haciendo que las imágenes se carguen de manera fluida y ultrarrápida.
- **Carga Asíncrona sin Bloqueos (Event Loop Yielding):** Al cargar las pantallas de álbumes y listas de reproducción, la interfaz ahora cede control al bucle de eventos de Qt cada 5 canciones. Esto elimina por completo las micro-congelaciones al cargar álbumes o listas masivas de más de 50 elementos.
- **Caché Estática de Stylesheets:** Las tarjetas de acceso rápido (`QuickAccessTile`) y banners principales (`SpotlightBanner`) ahora almacenan su hoja de estilo en memoria caché estática. Se evitan costosas e innecesarias lecturas y parses repetitivos de CSS por parte del motor de Qt al cambiar de tema o navegar.

## Correcciones de Errores

- **Restablecimiento del Ecualizador de VLC:** Corregida la desactivación del ecualizador del reproductor aplicando una limpieza nativa real (`set_equalizer(None)`) en lugar de recrear un ecualizador vacío.
- **Resolución Automática de Playlists "VL":** Se añade soporte y conversión automatizada en la barra principal para identificadores de playlist con el prefijo nativo `"VL"`.
- **Datos en Tarjetas de Playlists:** Las tarjetas de playlists en la pantalla de inicio ahora muestran correctamente la descripción o autor real en su campo secundario en lugar de un nombre de artista erróneo.

## Build y release

- Versión subida a `1.3.0` / `v1.3.0`.
- El workflow de compilación multiplataforma generará paquetes nativos actualizados para todos los sistemas soportados.
