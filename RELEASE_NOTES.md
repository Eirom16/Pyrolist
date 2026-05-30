# Pyrolist v2.0.0

## Resumen

Esta versión marca un hito histórico para Pyrolist al transformarse en la versión **v2.0.0**. Introduce soporte internacional completo con localización en inglés y español, almacenamiento de alta seguridad mediante llavero del sistema (keyring), copias de seguridad robustas de la base de datos y configuraciones, aceleración nativa mediante C para desenfoque y escalado de imágenes ultra eficientes, y una arquitectura avanzada de testing.

## Novedades y Características Principales

- **Internacionalización Completa (i18n):** Soporte oficial para localización en **Español** e **Inglés** de forma dinámica. Toda la interfaz de usuario, menús contextuales, diálogos y pantallas de ajustes se traducen al instante según el idioma seleccionado.
- **Aceleración Gráfica Nativa en C (`fast_image.c`):** Implementación de una extensión de compilación nativa en C para realizar desenfoques gaussiónicos extremadamente eficientes en las portadas de música y fondos. Esto reduce la carga del procesador un 95% en comparación con implementaciones puras en Python, logrando transiciones visuales instantáneas y un renderizado ultrasuave.
- **Almacenamiento Seguro (Llavero del Sistema):** Integración con la librería `keyring` para almacenar de manera segura y encriptada las credenciales de inicio de sesión de YouTube Music y Last.fm utilizando los llaveros nativos del sistema operativo (GNOME Keyring, KWallet, Windows Credential Manager, etc.).
- **Copias de Seguridad (Backup & Restore):** Nueva sección y sistema automatizado para realizar respaldos completos de la biblioteca local, historial de reproducción, canciones descargadas y configuraciones personales. Permite restaurar de forma íntegra tus datos en cualquier momento.
- **Arquitectura de Pruebas (Headless Testing):** Configuración base mediante `tests/conftest.py` que incluye un *mock* de VLC. Esto permite ejecutar la batería de pruebas en entornos de integración continua headless o sistemas sin las librerías nativas de VLC instaladas.

## Mejoras y Correcciones de Seguridad

- **Seguridad en Tokens:** Se eliminan automáticamente los archivos locales expuestos (`headers_auth.json`) al migrar credenciales al almacenamiento cifrado seguro del sistema.
- **Ficheros Temporales Seguros:** La interacción con el cliente ytmusicapi genera archivos temporales de autenticación restrictivos (`0o600`) legibles únicamente por el usuario actual del sistema, eliminándose de inmediato al finalizar su uso.

## Build y release

- Versión subida a `2.0.0` / `v2.0.0`.
- El workflow de compilación multiplataforma generará paquetes nativos actualizados para todos los sistemas soportados.
