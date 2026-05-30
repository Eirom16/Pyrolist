# src/pyrolist/native/Makefile
# Compila los módulos nativos C de Pyrolist

CC        = gcc
CFLAGS    = -O2 -Wall -Wextra -shared -fPIC
TARGET    = fast_image.so
SOURCE    = fast_image.c

.PHONY: all clean check

all: $(TARGET)

$(TARGET): $(SOURCE)
	@echo "Compilando módulo nativo Pyrolist..."
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) -lm
	@echo "✓ $(TARGET) compilado correctamente"
	@echo "  Reinicia Pyrolist para activar la aceleración nativa"

clean:
	rm -f $(TARGET)
	@echo "✓ Limpiado"

check:
	@if [ -f "$(TARGET)" ]; then \
		echo "✓ $(TARGET) existe"; \
		python3 -c "from pyrolist.native.bindings import _NATIVE_AVAILABLE; \
		            print('✓ Módulo activo' if _NATIVE_AVAILABLE else '✗ No cargado')"; \
	else \
		echo "✗ $(TARGET) no compilado. Ejecuta: make"; \
	fi
