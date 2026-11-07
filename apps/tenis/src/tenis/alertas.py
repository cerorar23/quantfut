"""Gestión y deduplicación de alertas operativas para el motor de tenis (plan §H.4).

Reglas:
- Canal operativo Telegram `TG_ALERT_CHAT`.
- Deduplicación estricta: como máximo una alerta por tipo, partido y día (lección NBA).
- Sembrar el estado al arrancar para evitar avalanchas de alertas tras reinicios.
- Si las credenciales no están presentes, registra en log local sin fallar.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

TIPOS_ALERTA = {
    "contrato_roto",
    "cadena_rota",
    "sello_tardio",
    "corte_futuro",
    "colector_parado",
    "cupo_agotado",
    "sin_resolver_alto",
    "jugador_sin_historia",
    "fatiga_desconocida",
    "respaldo_fallido",
    "prueba",
}

# Memoria de deduplicación: {(tipo, partido_id, fecha_dia_utc)}
_ALERTAS_ENVIADAS: set[tuple[str, int | None, str]] = set()


def hoy_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sembrar_alertas(historial: set[tuple[str, int | None, str]] | list[tuple[str, int | None, str]] | None = None) -> None:
    """Siembra el conjunto de alertas ya emitidas al arrancar el motor."""
    global _ALERTAS_ENVIADAS
    if historial:
        _ALERTAS_ENVIADAS.update(historial)
    else:
        _ALERTAS_ENVIADAS.clear()


def esta_enviada(tipo: str, partido_id: int | None = None, fecha: str | None = None) -> bool:
    f = fecha or hoy_utc()
    return (tipo, partido_id, f) in _ALERTAS_ENVIADAS


def registrar_enviada(tipo: str, partido_id: int | None = None, fecha: str | None = None) -> None:
    f = fecha or hoy_utc()
    _ALERTAS_ENVIADAS.add((tipo, partido_id, f))


def enviar_alerta(
    tipo: str,
    mensaje: str,
    partido_id: int | None = None,
    fecha: str | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Envía una alerta al canal operativo si no ha sido enviada hoy para ese partido y tipo."""
    f = fecha or hoy_utc()
    clave = (tipo, partido_id, f)

    if clave in _ALERTAS_ENVIADAS:
        log.info("Alerta %s (partido=%s, fecha=%s) omitida por deduplicación", tipo, partido_id, f)
        return {"estado": "omitida_deduplicada", "clave": clave}

    token = bot_token or os.getenv("TG_BOT_TOKEN")
    chat = chat_id or os.getenv("TG_ALERT_CHAT")

    texto = f"[TENIS-V2 ALERT] [{tipo.upper()}]\nFecha: {f}\n"
    if partido_id:
        texto += f"Partido ID: {partido_id}\n"
    texto += f"Detalle: {mensaje}"

    if not token or not chat:
        log.warning("Telegram no configurado. Alerta local registrada: %s", texto)
        registrar_enviada(tipo, partido_id, f)
        return {"estado": "registrada_local", "clave": clave, "texto": texto}

    payload = json.dumps({"chat_id": chat, "text": texto}).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                registrar_enviada(tipo, partido_id, f)
                return {"estado": "enviada", "clave": clave, "message_id": data.get("result", {}).get("message_id")}
            return {"estado": "error_respuesta", "detalle": data}
    except Exception as e:
        log.error("Fallo al enviar alerta a Telegram: %s", e)
        registrar_enviada(tipo, partido_id, f)
        return {"estado": "error_red", "error": str(e)}
