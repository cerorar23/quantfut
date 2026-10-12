"""QuantFut."""
from . import observabilidad

# Cubre la API y todos los trabajos del worker (`python -m qf...`); sin SENTRY_DSN no hace nada.
observabilidad.iniciar()
