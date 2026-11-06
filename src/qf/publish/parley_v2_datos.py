"""Lote propio del parley v2 (fase 3): barrera de fuentes, selección a las 03:35 y sellado.

Orden: predecir → sellar (lote diario, 09:00 UTC) → ESTE módulo: seleccionar → sellar (cadena propia).
No modifica ``seal()``, ``prediction_batches`` ni el cron diario; cada lote guarda el hash del
lote diario que lo precede. Está apagado salvo ``PARLEY_V2_ENABLED=1``.

* Decisión a las 03:35 America/Mexico_City = 09:35 UTC (México no tiene horario de verano). Si la
  barrera de fuentes no se cumple, reintenta cada 5 minutos hasta las 04:00 (10:00 UTC).
* Barrera: lote diario de fútbol sellado, recibo íntegro del archivo de tenis y de cuotas, y
  artefacto de calibración aprobado. Antes del límite se espera a que estén TODAS las fuentes; en el
  límite se publican solo los tickets factibles con las fuentes que sí llegaron, o se abstiene.
* Sin artefacto aprobado y con ``PARLEY_V2_REFERENCIA=1`` se sella igual, pero todo ticket queda
  ``solo_referencia`` (evidencia en sombra); sin esa bandera no se selecciona nada.
* Idempotente: una sola fila por estrategia, versión y día; un lote sellado no se recalcula.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable

from ..db import conn, query, query_one
from . import hashchain
from . import parley_v2 as v2
from .escalera import Opcion

log = logging.getLogger(__name__)

HORA_DECISION = time(9, 35)          # UTC = 03:35 America/Mexico_City
LIMITE = time(10, 0)                 # UTC = 04:00 America/Mexico_City
REINTENTO = timedelta(minutes=5)
DEPORTES_DIARIOS = ("futbol", "tenis")      # NBA va por partido (parley_nba)


@dataclass(frozen=True)
class Recibo:
    fuente: str
    estado: str                      # 'complete' solo si el productor terminó íntegro
    termino: datetime | None
    job_id: str = ""
    version: str = ""

    def valido(self, now: datetime) -> bool:
        return self.estado == "complete" and self.termino is not None and self.termino <= now


@dataclass
class Barrera:
    ok: bool
    razones: list[str] = field(default_factory=list)
    deportes: tuple[str, ...] = ()
    completa: bool = False           # todas las fuentes esperadas llegaron

    def como_dict(self) -> dict:
        return {"ok": self.ok, "razones": self.razones, "deportes": list(self.deportes), "completa": self.completa}


def ventana(dia: date) -> tuple[datetime, datetime]:
    base = datetime.combine(dia, time(0, 0), tzinfo=timezone.utc)
    return base.replace(hour=HORA_DECISION.hour, minute=HORA_DECISION.minute), base.replace(hour=LIMITE.hour, minute=LIMITE.minute)


def siguiente_intento(now: datetime) -> datetime | None:
    """Próximo reintento (cada 5 min) hasta el límite de las 04:00 de México; None si ya pasó."""
    inicio, limite = ventana(now.astimezone(timezone.utc).date())
    if now >= limite:
        return None
    if now < inicio:
        return inicio
    pasos = int((now - inicio) / REINTENTO) + 1
    return min(inicio + pasos * REINTENTO, limite)


def barrera(now: datetime, recibos: dict[str, Recibo], lote_diario: str | None,
            artefacto: dict | None, modo_referencia: bool = False) -> Barrera:
    razones: list[str] = []
    deportes = []
    if lote_diario:
        deportes.append("futbol")
    else:
        razones.append("lote diario de fútbol sin sellar")
    r = recibos.get("tenis")
    if r is not None and r.valido(now):
        deportes.append("tenis")
    else:
        razones.append("recibo íntegro de tenis ausente o incompleto")
    c = recibos.get("cuotas")
    cuotas_ok = c is not None and c.valido(now)
    if not cuotas_ok:
        razones.append("recibo de cuotas ausente o incompleto")
    aprobado = bool(artefacto and artefacto.get("aprobado"))
    if not aprobado and not modo_referencia:
        razones.append("artefacto de calibración no aprobado")
    ok = cuotas_ok and bool(deportes) and (aprobado or modo_referencia)
    return Barrera(ok, razones, tuple(deportes), completa=ok and len(deportes) == len(DEPORTES_DIARIOS))


# ------------------------------------------------------------------ lote
def _pata(o: Opcion) -> dict:
    evento = getattr(o, "evento", ())
    jugador = getattr(o, "jugador", ())
    deporte = getattr(o, "deporte", "") or "futbol"
    # El id de fútbol es el match_id completo (lleva ':'); en tenis y NBA el prefijo es el deporte.
    evento_id = o.match_id if deporte == "futbol" else o.match_id.split(":", 1)[-1]
    return {"deporte": deporte, "evento_id": evento_id,
            "match_id": o.match_id, "mercado": o.cand.market, "seleccion": o.cand.selection, "linea": o.cand.line,
            "jugador_id": jugador[0] if jugador else None, "jugador": jugador[1] if jugador else None,
            "prob": round(o.cand.prob, 6), "cuota": o.price, "casa": o.book, "fuente_cuota": o.odds_source,
            "cuota_en": o.odds_as_of.isoformat() if o.odds_as_of else None,
            "inicio_utc": evento[2].isoformat() if len(evento) > 2 else None,
            "n_casas_ref": getattr(o, "n_casas_ref", 0) or None, "referencia": getattr(o, "referencia", "") or None,
            "evento": list(map(str, evento)) if evento else []}


def construir_lote(plan: v2.Plan, now: datetime, dia: date, br: Barrera, lote_diario: str | None,
                   prev: str, ambito: str = "diario", evento_id: str | None = None) -> dict:
    """Lote sellable: carga canónica, hashes y clave de idempotencia. No toca la base de datos."""
    tickets = []
    for t in sorted(plan.tickets, key=lambda x: x.target):
        r = v2.resumen(t)
        r["patas"] = [_pata(o) for o in t.legs]
        tickets.append(r)
    clave = f"{v2.ESTRATEGIA}|{v2.VERSION}|{ambito}|{evento_id or dia.isoformat()}"
    payload = {"estrategia": v2.ESTRATEGIA, "version": v2.VERSION, "dia": dia.isoformat(), "ambito": ambito,
               "evento_id": evento_id, "decidido_at": now.astimezone(timezone.utc).isoformat(),
               "barrera": br.como_dict(), "lote_diario_sha256": lote_diario, "tickets": tickets,
               "abstenciones": [{"target": a.target, "motivo": a.motivo} for a in plan.abstenciones]}
    cuerpo = hashchain.canonical_json(payload)
    payload_sha = hashchain.sha256_hex(cuerpo)
    return {"clave": clave, "dia": dia, "ambito": ambito, "evento_id": evento_id, "decidido_at": now,
            "payload": payload, "payload_sha256": payload_sha, "prev_sha256": prev,
            "chain_sha256": hashchain.sha256_hex(prev + payload_sha), "lote_diario_sha256": lote_diario}


# ------------------------------------------------------------------ base de datos (se parchean en pruebas)
def _lote_diario(dia: date) -> str | None:
    fila = query_one("SELECT chain_sha256 FROM prediction_batches WHERE batch_date = %s", (dia,))
    return fila["chain_sha256"] if fila else None


def _existe(clave: str) -> bool:
    return query_one("SELECT 1 AS x FROM parley_v2_lotes WHERE clave = %s", (clave,)) is not None


def _prev() -> str:
    fila = query_one("SELECT chain_sha256 FROM parley_v2_lotes ORDER BY sellado_at DESC, lote_id DESC LIMIT 1")
    return fila["chain_sha256"] if fila else hashchain.GENESIS


def _guardar(lote: dict) -> bool:
    """Lote, tickets y patas en UNA transacción con candado por clave. False si otro proceso ya lo selló."""
    p = lote["payload"]
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lote["clave"],))
        cur.execute("SELECT 1 AS x FROM parley_v2_lotes WHERE clave = %s", (lote["clave"],))
        if cur.fetchone():
            return False
        cur.execute(
            """INSERT INTO parley_v2_lotes (dia, estrategia, version, clave, ambito, evento_id, decidido_at, barrera,
                                           lote_diario_sha256, payload_sha256, prev_sha256, chain_sha256)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING lote_id""",
            (lote["dia"], p["estrategia"], p["version"], lote["clave"], lote["ambito"], lote["evento_id"],
             lote["decidido_at"], json.dumps(p["barrera"]), lote["lote_diario_sha256"], lote["payload_sha256"],
             lote["prev_sha256"], lote["chain_sha256"]))
        lote_id = cur.fetchone()["lote_id"]
        for t in p["tickets"]:
            cur.execute(
                """INSERT INTO parley_v2_tickets (lote_id, target, tipo, estado, n_patas, cuota_total, prob_conjunta,
                                                  prob_prudente, p_bajo, p_alto, motivos)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING ticket_id""",
                (lote_id, t["target"], t["tipo"], t["estado"], t["n_patas"], t["cuota_total"],
                 t["probabilidad_conjunta"], t.get("probabilidad_prudente"),
                 (t["incertidumbre"] or [None, None])[0], (t["incertidumbre"] or [None, None])[1],
                 json.dumps(t["motivos"])))
            ticket_id = cur.fetchone()["ticket_id"]
            for pt in t["patas"]:
                cur.execute(
                    """INSERT INTO parley_v2_patas (ticket_id, deporte, evento_id, mercado, seleccion, linea, jugador_id,
                                                    jugador, prob, price, book, odds_source, odds_as_of, inicio_utc,
                                                    n_casas_ref, referencia, evento)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (ticket_id, pt["deporte"], pt["evento_id"], pt["mercado"], pt["seleccion"], pt["linea"],
                     pt["jugador_id"], pt["jugador"], pt["prob"], pt["cuota"], pt["casa"], pt["fuente_cuota"],
                     pt["cuota_en"], pt["inicio_utc"] or lote["decidido_at"], pt["n_casas_ref"], pt["referencia"],
                     json.dumps(pt["evento"])))
    return True


# ------------------------------------------------------------------ lectura pública (API, web y app)
def _texto(mercado: str, sel: str, linea, local: str | None, visita: str | None, jugador: str | None) -> str:
    """Texto en español de respaldo; la app redacta el suyo en cada idioma desde mercado/selección/línea."""
    lado = {"home": local or "Local", "away": visita or "Visitante", "draw": "Empate", "over": "Más de",
            "under": "Menos de", "yes": "Sí", "no": "No"}.get(sel, sel)
    suf = "" if linea is None else f" {float(linea):g}"
    if jugador:
        return f"{jugador} · {mercado.replace('player_', '')}: {lado}{suf}"
    return f"{mercado}: {lado}{suf}" if sel in ("over", "under") else f"{lado}{suf}"


def informe_publico_v2(dias: int = 30) -> dict:
    """Tickets sellados del parley v2 con la forma del parley actual (escalón = índice del target)."""
    objetivos = {t: i for i, t in enumerate(v2.TARGETS, 1)}
    filas = query(
        """SELECT l.lote_id, l.dia, l.ambito, l.evento_id AS lote_evento, l.chain_sha256, l.lote_diario_sha256, l.decidido_at,
                  t.ticket_id, t.target, t.tipo, t.estado, t.n_patas, t.cuota_total, t.prob_conjunta, t.prob_prudente,
                  t.p_bajo, t.p_alto, t.motivos, r.outcome, r.factor_pago
           FROM parley_v2_lotes l JOIN parley_v2_tickets t ON t.lote_id = l.lote_id
           LEFT JOIN parley_v2_resultados r ON r.ticket_id = t.ticket_id
           WHERE l.dia >= CURRENT_DATE - %s ORDER BY l.dia DESC, l.ambito, t.target""", (dias,))
    patas = query(
        """SELECT p.ticket_id, p.deporte, p.evento_id, p.mercado, p.seleccion, p.linea, p.jugador, p.prob, p.price,
                  p.book, p.inicio_utc, p.evento, rp.outcome, rp.valor,
                  COALESCE(th.display_name, th.canonical_name) AS local_f, COALESCE(ta.display_name, ta.canonical_name) AS visita_f
           FROM parley_v2_patas p
           JOIN parley_v2_tickets t ON t.ticket_id = p.ticket_id
           JOIN parley_v2_lotes l ON l.lote_id = t.lote_id
           LEFT JOIN matches m ON p.deporte = 'futbol' AND m.match_id = p.evento_id
           LEFT JOIN teams th ON th.team_id = m.home_team_id LEFT JOIN teams ta ON ta.team_id = m.away_team_id
           LEFT JOIN parley_v2_resultados_pata rp ON rp.pata_id = p.pata_id
           WHERE l.dia >= CURRENT_DATE - %s ORDER BY p.inicio_utc, p.evento_id""", (dias,))
    por_ticket: dict = {}
    for p in patas:
        ev = p["evento"] if isinstance(p["evento"], list) else json.loads(p["evento"] or "[]")
        local = p["local_f"] or (ev[3] if len(ev) > 3 else None)
        visita = p["visita_f"] or (ev[4] if len(ev) > 4 else None)
        por_ticket.setdefault(p["ticket_id"], []).append({
            "deporte": p["deporte"], "evento_id": p["evento_id"], "kickoff_utc": p["inicio_utc"], "local": local,
            "visitante": visita, "market": p["mercado"], "selection": p["seleccion"],
            "line": None if p["linea"] is None else float(p["linea"]), "jugador": p["jugador"],
            "texto": _texto(p["mercado"], p["seleccion"], p["linea"], local, visita, p["jugador"]),
            "prob": round(float(p["prob"]), 2), "price": float(p["price"]), "book": p["book"],
            "outcome": p["outcome"], "valor": p["valor"]})
    salida: list[dict] = []
    for t in filas:
        clave = (t["dia"], t["ambito"], t["lote_evento"])
        if not salida or salida[-1]["_k"] != clave:
            salida.append({"_k": clave, "dia": t["dia"], "ambito": t["ambito"], "evento_id": t["lote_evento"],
                           "chain_sha256": t["chain_sha256"], "lote_diario_sha256": t["lote_diario_sha256"], "tickets": []})
        salida[-1]["tickets"].append({
            "escalon": objetivos.get(round(float(t["target"]), 2), 0), "target": float(t["target"]), "tipo": t["tipo"],
            "estado": t["estado"], "n_patas": t["n_patas"], "cuota_total": float(t["cuota_total"]),
            "prob_total": None if t["prob_conjunta"] is None else round(float(t["prob_conjunta"]), 4),
            "prob_prudente": None if t["prob_prudente"] is None else round(float(t["prob_prudente"]), 4),
            "incertidumbre": None if t["p_bajo"] is None else [round(float(t["p_bajo"]), 4), round(float(t["p_alto"]), 4)],
            "motivos": t["motivos"], "outcome": t["outcome"],
            "factor_pago": None if t["factor_pago"] is None else float(t["factor_pago"]),
            "patas": por_ticket.get(t["ticket_id"], [])})
    for d in salida:
        d.pop("_k")
    return {"activo": habilitado(), "estrategia": v2.ESTRATEGIA, "version": v2.VERSION,
            "reglas": {"escalones": [{"escalon": i, "cuota_min": round(t * (1 - v2.TARGET_TOLERANCE), 3),
                                      "cuota_max": round(t * (1 + v2.TARGET_TOLERANCE), 3), "target": t}
                                     for t, i in objetivos.items()]},
            "dias": salida}


# ------------------------------------------------------------------ orquestación
def habilitado() -> bool:
    return os.getenv("PARLEY_V2_ENABLED", "0") == "1"


def ejecutar(now: datetime, cargar_ops: Callable[[datetime, tuple[str, ...]], list[Opcion]],
             recibos: dict[str, Recibo], artefacto: dict | None = None, modo_referencia: bool | None = None,
             dry_run: bool = False) -> dict:
    """Un intento de las 03:35. ``cargar_ops(now, deportes)`` entrega las patas de los deportes disponibles."""
    from ..eval.parley_calibracion import Calibrador, filtrar_calibradas
    if not habilitado() and not dry_run:
        return {"estado": "desactivado"}
    now = now.astimezone(timezone.utc)
    dia = now.date()
    inicio, limite = ventana(dia)
    if now < inicio:
        return {"estado": "antes_de_hora", "siguiente_intento": inicio.isoformat()}
    clave = f"{v2.ESTRATEGIA}|{v2.VERSION}|diario|{dia.isoformat()}"
    if not dry_run and _existe(clave):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}
    ref = os.getenv("PARLEY_V2_REFERENCIA", "0") == "1" if modo_referencia is None else modo_referencia
    diario = _lote_diario(dia)
    br = barrera(now, recibos, diario, artefacto, ref)
    en_limite = now >= limite
    if not br.ok or (not br.completa and not en_limite):
        sig = siguiente_intento(now)
        if sig is None and not br.ok:
            return {"estado": "abstencion", "razones": br.razones, "dia": dia.isoformat()}
        if sig is not None:
            return {"estado": "esperando", "razones": br.razones, "siguiente_intento": sig.isoformat()}
    ops = cargar_ops(now, br.deportes)
    calibracion = None
    if artefacto and artefacto.get("aprobado"):
        calibracion = Calibrador(artefacto).para_opciones(ops)
        ops = filtrar_calibradas(ops, calibracion)              # abstención por categoría
    plan = v2.armar_plan(ops, calibracion=calibracion, ahora=now)
    resumen = {"estado": "elegido" if plan.tickets else "abstencion", "dia": dia.isoformat(),
               "deportes": list(br.deportes), "completa": br.completa, "candidatas": len(ops),
               "tickets": [{"target": t.target, "estado": t.estado, "patas": len(t.legs)} for t in plan.tickets],
               "abstenciones": [a.target for a in plan.abstenciones]}
    if dry_run:
        return resumen
    lote = construir_lote(plan, now, dia, br, diario, _prev())
    if not _guardar(lote):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}
    log.info("Parley v2 sellado: %s", {k: v for k, v in resumen.items() if k != "tickets"})
    return {**resumen, "chain": lote["chain_sha256"][:16]}


def main() -> None:                                   # pragma: no cover - cableado de producción
    """Cron: ``python -m qf.publish.parley_v2_datos`` cada 5 min entre 09:35 y 10:00 UTC."""
    from ..config import settings
    from ..eval.parley_calibracion import Calibrador  # noqa: F401
    from ..ingest import propline_shared as ps
    from . import parley_datos as pd_
    from . import parley_ext as ext
    now = datetime.now(timezone.utc)
    ruta = os.getenv("PARLEY_V2_ARTEFACTO")
    artefacto = json.loads(open(ruta, encoding="utf-8").read()) if ruta and os.path.isfile(ruta) else None

    def recibo(sport: str, fuente: str) -> Recibo:
        _, rc = ps.newest(settings.propline_archive, f"/v1/sports/{sport}/odds", now)
        if not rc:
            return Recibo(fuente, "ausente", None)
        return Recibo(fuente, "complete", ps.parse_time(rc["received_at"]), str(rc.get("request_id", "")), "propline")

    recibos = {"tenis": recibo("tennis", "tenis"), "cuotas": recibo("tennis", "cuotas")}

    def cargar(ahora, deportes):
        ops = []
        if "futbol" in deportes:
            ops += v2.consolidar(pd_.candidatas(ahora, v2_activo=True)[0])
        if "tenis" in deportes:
            ops += ext.candidatos({"tenis": ext.cargar(ahora)["tenis"]}, ahora)
        return ops

    print(json.dumps(ejecutar(now, cargar, recibos, artefacto), ensure_ascii=False, default=str))


if __name__ == "__main__":                            # pragma: no cover
    main()
