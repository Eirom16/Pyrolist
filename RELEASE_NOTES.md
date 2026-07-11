# Pyrolist v2.1.3

## Resumen

Pyrolist v2.1.3 es un hotfix crítico del actualizador automático. Corrige el caso donde una instalación exitosa podía seguir reportándose como desactualizada porque el paquete instalado conservaba metadatos internos de una versión anterior.

## Correcciones

- **Versión instalada:** `CURRENT_VERSION` ahora se deriva de `pyrolist.__version__`, evitando duplicar versiones entre el actualizador y el paquete instalado.
- **Paquetes Arch:** El `PKGBUILD` inyecta `pkgver` en `src/pyrolist/__init__.py` y `pyproject.toml` dentro del tarball descargado antes de empaquetar, evitando que el binario quede con una versión interna antigua.
- **Workflow multiplataforma:** Las builds actualizan `__version__` y `pyproject.toml` como fuentes de versión, en lugar de editar una constante del actualizador que ya no existe.
- **Acerca de / Actualizaciones:** Limpieza de diagnósticos menores en la pantalla de ajustes relacionada con notificaciones de actualización.

## Build y release

- Versión subida a `2.1.3` / `v2.1.3`.
- Esta versión debe reemplazar a `v2.1.2` como release recomendada para cortar el ciclo de actualización repetida.
