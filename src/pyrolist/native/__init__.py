# src/pyrolist/native/__init__.py
"""
Módulos nativos C de Pyrolist.
Se cargan automáticamente al importar cualquier función de bindings.py.
Si fast_image.so no está compilado, todas las funciones devuelven None
y el código Python original actúa como fallback transparente.

Para compilar el módulo nativo:
    cd src/pyrolist/native
    make

Para verificar que está activo:
    python -c "from pyrolist.native.bindings import _NATIVE_AVAILABLE; print(_NATIVE_AVAILABLE)"
"""
from pyrolist.native.bindings import _NATIVE_AVAILABLE

__all__ = ["_NATIVE_AVAILABLE"]
