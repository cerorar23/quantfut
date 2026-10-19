"""Sello tardío por partido (F7): cada partido se predice de nuevo y se sella solo, minutos antes del saque.

Mismo orden de siempre, por partido: predecir (etapa `final`) -> seleccionar picks de valor (si la puerta de CLV está abierta)
-> sellar (`hashchain.seal_partido`) -> publicar el compromiso. El lote diario de las 09:00 UTC no cambia y conserva sus
productos de varios partidos.

Cuándo se sella: cuando están capturadas las alineaciones de los dos lados (y faltan ≤ 90 min), o a T-45, lo primero.
Sin alineación se sella igual y queda anotado en `data_completeness.sello_tardio`. Un partido sin predicción diaria (liga sin
modelo) no se sella aquí.

Se ejecuta cada 5 minutos desde el cron (con flock: el índice único de la base evita duplicados, el flock evita carreras en la
cadena). No hace nada mientras `hashchain.LOTE_POR_PARTIDO_DESDE` sea None.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..db import query, query_one
from . import daily, hashchain
from . import picks as pk
from . import telegram as tg

log = logging.getLogger(__name__)

VENTANA_SELLO = timedelta(minutes=45)       # sin alineación se sella a T-45
VENTANA_XI = timedelta(minutes=90)          # con las dos alineaciones se sella en cuanto entra en esta ventana
AVISO_SIN_SELLAR = timedelta(minutes=15)    # si a T-15 sigue sin sellar, avisa


def toca_sellar(kickoff: datetime, ahora: datetime, lados_xi: int) -> bool:
    falta = kickoff - ahora
    if falta <= timedelta(0):
        return False
    return falta <= VENTANA_SELLO or (lados_xi >= 2 and falta <= VENTANA_XI)


def candidatos(ahora: datetime) -> list[dict]:
    """Partidos próximos con predicción diaria y sin lote de partido."""
    return query(
        """SELECT m.match_id, m.kickoff_utc,
                  (SELECT count(DISTINCT l.side) FROM lineups l WHERE l.match_id = m.match_id) AS lados_xi
           FROM matches m
           WHERE m.status = 'scheduled' AND m.kickoff_utc > %s AND m.kickoff_utc <= %s
             AND EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.match_id AND p.etapa = 'diaria')
             AND NOT EXISTS (SELECT 1 FROM prediction_batches b
                             WHERE b.batch_kind = 'partido' AND b.match_id = m.match_id)
           ORDER BY m.kickoff_utc""",
        (ahora, ahora + VENTANA_XI))


def _picks_de_valor(preds: list[dict]) -> int:
    """Picks de valor de la predicción final, con las cuotas de este momento. Misma puerta de CLV que el lote diario."""
    if not settings.publish_picks_enabled:
        return 0
    gate_ok, razones = daily._shadow_gate_allows_publication()
    if not gate_ok:
        log.info("Picks de valor bloqueados por la puerta de CLV: %s", razones)
        return 0
    seleccion = pk.select_daily(preds)
    return pk.persist(pk.assign_tiers(seleccion)) if seleccion else 0


def sellar(m: dict, ahora: datetime) -> dict:
    """Predice (final) y sella un partido. Devuelve el recibo, o {} si no se pudo."""
    mid, ko = m["match_id"], m["kickoff_utc"]
    ya_final = query_one("SELECT 1 AS x FROM predictions WHERE match_id = %s AND etapa = 'final'", (mid,))
    if not ya_final:        # si una pasada anterior cayó entre predecir y sellar, se reutiliza la final ya guardada
        info = {"minutos_al_saque": round((ko - ahora).total_seconds() / 60, 1), "lados_con_alineacion": int(m["lados_xi"]),
                "disparo": "alineacion" if m["lados_xi"] >= 2 and ko - ahora > VENTANA_SELLO else "t-45"}
        preds = daily.generate_predictions(solo_partido=mid, etapa="final", hasta=ko + timedelta(hours=1), info_final=info)
        if not preds:
            log.error("Sin predicción final para %s", mid)
            return {}
        _picks_de_valor(preds)
    return hashchain.seal_partido(mid)


def run(ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    if hashchain.LOTE_POR_PARTIDO_DESDE is None:
        return {"estado": "apagado"}
    hechos, fallos = [], []
    for m in candidatos(ahora):
        if not hashchain.lote_por_partido(m["kickoff_utc"].astimezone(timezone.utc).date()):
            continue
        if toca_sellar(m["kickoff_utc"], ahora, int(m["lados_xi"])):
            try:
                recibo = sellar(m, ahora)
            except Exception:  # noqa: BLE001 — un partido caído no detiene a los demás
                log.exception("Fallo al sellar %s", m["match_id"])
                recibo = {}
            (hechos if recibo else fallos).append(m["match_id"])
        if m["match_id"] in fallos and m["kickoff_utc"] - ahora <= AVISO_SIN_SELLAR:
            tg.alert(f"PARTIDO SIN SELLAR a T-{int((m['kickoff_utc'] - ahora).total_seconds() // 60)} min: {m['match_id']}")
    return {"sellados": hechos, "fallos": fallos}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
