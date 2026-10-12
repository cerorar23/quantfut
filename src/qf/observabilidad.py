"""Sentry para el backend y los trabajos del worker: solo errores, sin datos personales.

Se activa únicamente si existe `SENTRY_DSN` (en el `.env` del servidor, nunca en el repo).
Decisiones deliberadas, porque este servicio maneja contraseñas, tokens de sesión, enlaces de
correo y claves de proveedores dentro de URLs:

- sin PII (`data_collection`), sin cuerpo de petición, sin datos de consultas SQL y sin
  variables locales en los frames;
- sin migas de pan (`max_breadcrumbs=0`): las de httpx/logging llevan URLs completas;
- sin tracing ni profiling;
- `before_send` descarta cabeceras, cookies, query string, usuario y variables de entorno.
"""
from __future__ import annotations

import logging
import os

_iniciado = False

# Claves que nunca deben salir de aquí aunque aparezcan en los "extra" de un evento.
_SENSIBLES = ("token", "secret", "password", "contrasena", "authorization", "cookie",
              "api_key", "apikey", "dsn", "key")


def _limpiar(valor, profundidad: int = 0):
    if profundidad > 6:
        return "[recortado]"
    if isinstance(valor, dict):
        return {k: ("[oculto]" if any(s in str(k).lower() for s in _SENSIBLES)
                    else _limpiar(v, profundidad + 1)) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_limpiar(v, profundidad + 1) for v in valor]
    return valor


def antes_de_enviar(event: dict, hint: dict | None = None) -> dict | None:
    """Quita de un evento todo lo que pueda identificar a una persona o dar acceso."""
    request = event.get("request")
    if isinstance(request, dict):
        # La URL puede traer `?token=` de los enlaces de correo: se deja solo el camino.
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = url.split("?", 1)[0]
        for campo in ("headers", "cookies", "data", "query_string", "env"):
            request.pop(campo, None)
    event.pop("user", None)
    event.pop("server_name", None)
    for campo in ("extra", "contexts"):
        if campo in event:
            event[campo] = _limpiar(event[campo])
    if isinstance(event.get("extra"), dict):
        event["extra"].pop("sys.argv", None)  # argumentos de la línea de comandos
    return event


def iniciar(**opciones) -> bool:
    """Inicializa Sentry una sola vez. Sin `SENTRY_DSN` no hace nada (y no importa el SDK).

    `opciones` se pasa tal cual a `sentry_sdk.init` (las pruebas inyectan un transporte)."""
    global _iniciado
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if _iniciado or not dsn:
        return _iniciado
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE") or None,
        data_collection={"user_info": False, "http_bodies": [], "database_query_data": False,
                         "stack_frame_variables": False},
        max_breadcrumbs=0,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        # Los ERROR del log llegan como evento; nada de INFO como miga de pan.
        integrations=[LoggingIntegration(level=None, event_level=logging.ERROR)],
        before_send=antes_de_enviar,
        **opciones,
    )
    _iniciado = True
    return True
