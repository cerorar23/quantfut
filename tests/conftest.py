"""Ajustes comunes de las pruebas."""
import os

# El seguimiento de tarjetas viene ENCENDIDO por defecto en producción (no publica nada y
# activarlo por entorno obligaría a recrear el worker). Las pruebas del job diario no
# simulan su consulta, así que arrancan con él apagado; las suyas lo encienden a mano.
os.environ.setdefault("TARJETAS_SEG_ENABLED", "0")
