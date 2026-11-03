"""Alertas operativas del motor por el canal privado existente (Telegram, `TG_ALERT_CHAT`; decisión del titular del 2-oct-2026).

Solo avisan de lo que requiere atención: un partido que falló, un partido que empezó sin sello, o la historia atrasada (captura caída).
Cada alerta se manda una vez por (tipo, partido) y día: el estado se guarda en un JSON para que el cron de cada 5 minutos no repita.
Sin canal configurado (`NBA_ALERTA_TG_TOKEN` y `NBA_ALERTA_CHAT`) no envía nada y devuelve los mensajes para el registro.
"""
from datetime import datetime, UTC
import json
from pathlib import Path
import urllib.parse
import urllib.request

RAZONES = {"ya_empezo_sin_sello": "empezó sin pronóstico sellado", "historia_atrasada": "no se sella: la captura de resultados está atrasada",
          "equipo_sin_resultados_recientes": "no se sella: a uno de sus equipos le faltan resultados recientes"}


def mensajes(resumen: dict) -> list[tuple[str, str]]:
    """[(clave de deduplicación, texto)] para lo que merece alerta en un resumen del motor."""
    salida = []
    for e in resumen.get("errores", []):
        salida.append((f"error:{e['partido']}", f"NBA motor: error en el partido {e['partido']}: {e['error'][:200]}"))
    for o in resumen.get("omitidos", []):
        salida.append((f"{o['razon']}:{o['partido']}", f"NBA motor: el partido {o['partido']} {RAZONES.get(o['razon'], o['razon'])}"))
    return salida


def _enviar_telegram(token: str, chat: str, texto: str) -> None:
    datos = urllib.parse.urlencode({"chat_id": chat, "text": texto}).encode()
    urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=datos), timeout=15).read()


def procesar(resumen: dict, estado: Path | None, token: str | None, chat: str | None, enviar=_enviar_telegram, ahora: datetime | None = None) -> list[str]:
    """Manda las alertas nuevas del día y devuelve los textos (enviados o pendientes de canal)."""
    dia = (ahora or datetime.now(UTC)).date().isoformat()
    vistos = {}
    if estado and estado.exists():
        try:
            vistos = json.loads(estado.read_text(encoding="utf8"))
        except ValueError:
            vistos = {}
    nuevos = []
    for clave, texto in mensajes(resumen):
        if vistos.get(clave) == dia:
            continue
        nuevos.append(texto)
        if token and chat:
            enviar(token, chat, texto)
        vistos[clave] = dia
    if estado and nuevos:
        estado.write_text(json.dumps({k: v for k, v in vistos.items() if v == dia}), encoding="utf8")
    return nuevos
