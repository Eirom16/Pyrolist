# Pyrolist v2.1.1 (Hotfix)

## Resumen

¡Pyrolist v2.1.1 ya está aquí! Esta es una actualización menor de corrección de errores (Hotfix) centrada en solucionar un fallo crítico con el sistema de actualizaciones en sistemas operativos Linux.

## Mejoras y Correcciones de Errores

- **Actualizador en Linux:** Se ha corregido un error crítico donde la aplicación se cerraba a los 2 segundos de iniciar la actualización, matando el diálogo de autenticación (Polkit) antes de que pudieses colocar tu contraseña. Ahora el actualizador esperará pacientemente a que se complete la elevación de permisos mediante `pkexec`.
- **Seguridad en Elevación de Privilegios:** Se ha eliminado un parche anterior inestable para el ingreso de la contraseña (SudoPasswordDialog) y ahora se delega el 100% de la elevación de permisos a las herramientas nativas y seguras del sistema operativo de Linux (Polkit).

## Build y release

- Versión subida a `2.1.1` / `v2.1.1`.
- El workflow de compilación multiplataforma generará paquetes nativos actualizados para todos los sistemas soportados.
