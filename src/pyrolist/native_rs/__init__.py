# Pyrolist native Rust acceleration module.
#
# Re-exports all symbols from the compiled `native_rs.abi3.so` (installed
# by `maturin develop`).  If the .so is missing, all imports from here
# will raise ImportError — Python callers have their own fallback logic.

from native_rs import *  # noqa: F401, F403

_NATIVE_AVAILABLE = True
