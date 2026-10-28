"""
Cadena de hashes: prueba criptográfica de que no revisas predicciones.

Es lo que te separa de los canales de Telegram que borran los fallos, y para
un producto B2C de picks es literalmente el producto.

Flujo diario, antes del primer kickoff:
  1. Serializar todas las predicciones y picks del día a JSON canónico.
  2. sha256(payload) -> payload_hash
  3. chain_hash = sha256(prev_chain_hash || payload_hash)
  4. Escribir a disco. Al repo público va SOLO el compromiso: recibo
     (`*.receipt.json`) y `LEDGER.md`, con los hashes.
  5. Publicar el chain_hash en un canal con timestamp externo (GitHub, X).

Comprometer-revelar (decisión 2026-10-18): el JSON del lote lleva los picks de
pago, así que publicarlo antes de los partidos los regalaría. El JSON se sube
al repo solo cuando todos los partidos que cita ya terminaron (`revelables`).
Entonces cualquiera puede descargarlo, recalcular el hash y comprobar que
coincide con el compromiso publicado antes de los partidos.

Verificación por terceros:  python -m qf.publish.hashchain verify
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..config import settings
from ..db import execute, query, query_one

log = logging.getLogger(__name__)

GENESIS = "0" * 64

# El JSON se revela cuando pasó esto desde el último saque de los partidos que
# cita (cubre prórroga y retrasos de datos), y todos constan como terminados.
REVELAR_TRAS = timedelta(hours=4)
# Tope: un partido aplazado sin fecha nueva no retiene el lote para siempre.
REVELAR_TOPE = timedelta(days=7)


def canonical_json(obj) -> str:
    """JSON determinista: claves ordenadas, sin espacios, floats estables."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prev_chain_hash() -> str:
    row = query_one(
        "SELECT chain_sha256 FROM prediction_batches ORDER BY seq DESC LIMIT 1"
    )
    return row["chain_sha256"] if row else GENESIS


# Desde esta fecha el lote no lleva `market_consensus` (decisión del usuario,
# auditoría 2026-10-03): es el precio justo sin margen y, si el JSON se
# publica antes de los partidos, deja reconstruir el criterio de picks. Los
# lotes anteriores conservan su formato: regenerarlos desde la base tiene que
# dar el mismo hash que el día que se sellaron.
LOTE_SIN_CONSENSO_DESDE = date(2026, 10, 3)

# Desde esta fecha el lote lleva la línea de alta probabilidad
# (publish/alta_prob.py). None = todavía no desplegada: los lotes no cambian.
# Se fija a la fecha del despliegue en ese mismo commit; los lotes anteriores
# se regeneran igual que se sellaron.
LOTE_ALTA_PROB_DESDE: date | None = date(2026, 10, 7)   # primer lote sin sellar al desplegar (06-oct ya selló a las 08:00 UTC)


# Desde esta fecha el lote lleva el reto escalera (publish/escalera.py): los
# retos creados y los escalones decididos ese día. Misma regla que la de alta
# probabilidad: None hasta desplegar, y luego la fecha del primer lote sin sellar.
LOTE_ESCALERA_DESDE: date | None = date(2026, 10, 9)   # primer lote sin sellar al desplegar (08-oct ya selló a las 08:00 UTC)


def lote_lleva_escalera(dia: date) -> bool:
    return LOTE_ESCALERA_DESDE is not None and dia >= LOTE_ESCALERA_DESDE


# Desde esta fecha el lote lleva el parley del día (publish/parley.py). Misma
# regla: None hasta desplegar, y luego la fecha del primer lote sin sellar.
LOTE_PARLEY_DESDE: date | None = date(2026, 10, 12)   # primer lote sin sellar al desplegar (11-oct ya selló a las 08:00 UTC)


def lote_lleva_parley(dia: date) -> bool:
    return LOTE_PARLEY_DESDE is not None and dia >= LOTE_PARLEY_DESDE


# Desde esta fecha el lote lleva la alta probabilidad ampliada, 62-95 %
# (`alta_prob_ext`, db/057). Misma regla: primer lote sin sellar al desplegar.
LOTE_ALTA_EXT_DESDE: date | None = date(2026, 10, 12)


def lote_lleva_alta_ext(dia: date) -> bool:
    return LOTE_ALTA_EXT_DESDE is not None and dia >= LOTE_ALTA_EXT_DESDE


# Desde esta fecha el lote lleva el seguimiento sin publicar de tarjetas (`tarjetas_seg`,
# db/068). Misma regla: primer lote sin sellar al desplegar (el del 14-oct ya selló a las
# 08:00 UTC). Se sella aunque no se publique: así queda probado que no se fabricó después.
LOTE_TARJETAS_DESDE: date | None = date(2026, 10, 15)


def lote_lleva_tarjetas(dia: date) -> bool:
    return LOTE_TARJETAS_DESDE is not None and dia >= LOTE_TARJETAS_DESDE


def lote_lleva_alta(dia: date) -> bool:
    """
    ¿El lote de `dia` lleva el bloque de alta probabilidad? Única fuente de
    verdad: el escritor (elegir), el lote (`_collect`) y el lector (informe
    público) la usan. Lee la constante en cada llamada.
    """
    return LOTE_ALTA_PROB_DESDE is not None and dia >= LOTE_ALTA_PROB_DESDE


def _collect(batch_date: date) -> dict:
    consenso = ("p.market_consensus,"
                if batch_date < LOTE_SIN_CONSENSO_DESDE else "")
    preds = query(
        f"""SELECT p.prediction_id, p.match_id, p.model_version, p.generated_at,
                  p.home_lambda, p.away_lambda, p.rho, p.confidence_tier,
                  p.markets -> '1x2'    AS m_1x2,
                  p.markets -> 'totals' AS m_totals,
                  {consenso}
                  m.kickoff_utc, m.league_id,
                  th.canonical_name AS home_team, ta.canonical_name AS away_team
           FROM predictions p
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           -- El cast a fecha DEBE hacerse en UTC explícitamente. Un
           -- `generated_at::date` a secas usa la zona horaria del servidor,
           -- y `batch_date` se calcula en Python con UTC: si el servidor no
           -- está en UTC las dos fechas discrepan varias horas al día, el
           -- lote sale vacío, el sellado se salta y —por diseño— NO SE
           -- PUBLICA NADA. Un fallo mudo, no un error.
           WHERE (p.generated_at AT TIME ZONE 'UTC')::date = %s AND p.etapa = 'diaria'
           ORDER BY p.generated_at, p.prediction_id""",
        (batch_date,),
    )
    picks = query(
        """SELECT pick_id, prediction_id, match_id, market, selection, line,
                  model_prob, advised_price, bookmaker, edge_pct, raw_edge_pct,
                  stake_units, tier, published_at,
                  fair_prob, min_price, odds_source, odds_as_of
           FROM picks
           WHERE (published_at AT TIME ZONE 'UTC')::date = %s
             AND prediction_id IN (SELECT prediction_id FROM predictions WHERE etapa = 'diaria')
           ORDER BY published_at, pick_id""",
        (batch_date,),
    )
    con_alta = lote_lleva_alta(batch_date)
    alta = query(
        """SELECT alta_id, match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit, decided_at
           FROM alta_prob_picks
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, alta_id""",
        (batch_date,),
    ) if con_alta else []
    con_ext = lote_lleva_alta_ext(batch_date)
    alta_ext = query(
        """SELECT ext_id, match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit, decided_at
           FROM alta_prob_ext
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, ext_id""",
        (batch_date,),
    ) if con_ext else []
    con_escalera = lote_lleva_escalera(batch_date)
    retos = query(
        """SELECT reto_id, stake_inicial, pasos_objetivo, cuota_min, cuota_max, ev_min,
                  freeroll_x, created_at, prob_objetivo, dias_max
           FROM escalera_retos
           WHERE (created_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY reto_id""",
        (batch_date,),
    ) if con_escalera else []
    escalones = query(
        """SELECT paso_id, reto_id, paso, match_id, market, selection, line, prob,
                  fair_price, price, book, odds_source, odds_as_of, decided_at,
                  deporte, evento_id, evento_sport, evento_inicio, evento_local, evento_visitante
           FROM escalera_pasos
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, paso_id""",
        (batch_date,),
    ) if con_escalera else []
    con_parley = lote_lleva_parley(batch_date)
    parley_tickets = query(
        """SELECT ticket_id, dia, escalon, cuota_total, prob_total, n_patas, decided_at
           FROM parley_tickets
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, ticket_id""",
        (batch_date,),
    ) if con_parley else []
    parley_patas = query(
        """SELECT p.pata_id, p.ticket_id, p.match_id, p.market, p.selection, p.line, p.prob,
                  p.fair_price, p.price, p.book, p.odds_source, p.odds_as_of, p.kickoff_utc
           FROM parley_patas p
           JOIN parley_tickets t ON t.ticket_id = p.ticket_id
           WHERE (t.decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY t.decided_at, p.ticket_id, p.pata_id""",
        (batch_date,),
    ) if con_parley else []
    con_tarjetas = lote_lleva_tarjetas(batch_date)
    tarjetas_seg = query(
        """SELECT seg_id, match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit, decided_at
           FROM tarjetas_seg
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, seg_id""",
        (batch_date,),
    ) if con_tarjetas else []
    payload = {
        "batch_date": batch_date.isoformat(),
        "model_version": settings.model_version,
        "fs_version": settings.fs_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_predictions": len(preds),
        "n_picks": len(picks),
        "predictions": preds,
        "picks": picks,
    }
    if con_alta:
        payload["n_alta_prob"] = len(alta)
        payload["alta_probabilidad"] = alta
    if con_ext:
        payload["n_alta_ext"] = len(alta_ext)
        payload["alta_ext"] = alta_ext
    if con_tarjetas:
        payload["n_tarjetas_seg"] = len(tarjetas_seg)
        payload["tarjetas_seg"] = tarjetas_seg
    if con_escalera:
        payload["escalera"] = {"retos": retos, "pasos": escalones}
    if con_parley:
        payload["parley"] = {"tickets": parley_tickets, "patas": parley_patas}
    return payload


def seal(batch_date: date | None = None, git_push: bool = True) -> dict:
    """Sella el lote del día. Idempotente por fecha."""
    batch_date = batch_date or datetime.now(timezone.utc).date()

    if git_push and settings.chain_git_remote:
        _git_revelar(Path(settings.chain_dir))

    existing = query_one(
        "SELECT batch_id, chain_sha256 FROM prediction_batches WHERE batch_date = %s AND batch_kind = 'diario'",
        (batch_date,),
    )
    if existing:
        log.warning("El lote de %s ya está sellado (%s). No se re-sella.",
                    batch_date, existing["chain_sha256"][:16])
        return existing

    payload = _collect(batch_date)
    if payload["n_predictions"] == 0:
        log.info("Sin predicciones para %s, no se sella nada.", batch_date)
        return {}

    body = canonical_json(payload)
    payload_hash = sha256_hex(body)
    prev = _prev_chain_hash()
    chain_hash = sha256_hex(prev + payload_hash)

    out_dir = Path(settings.chain_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{batch_date.isoformat()}.json").write_text(body, encoding="utf-8")

    receipt = {
        "batch_date": batch_date.isoformat(),
        "payload_sha256": payload_hash,
        "prev_sha256": prev,
        "chain_sha256": chain_hash,
        "n_predictions": payload["n_predictions"],
        "n_picks": payload["n_picks"],
        **({"n_alta_prob": payload["n_alta_prob"]} if "n_alta_prob" in payload else {}),
        **({"n_alta_ext": payload["n_alta_ext"]} if "n_alta_ext" in payload else {}),
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / f"{batch_date.isoformat()}.receipt.json").write_text(
        canonical_json(receipt), encoding="utf-8"
    )
    _append_ledger(out_dir / "LEDGER.md", receipt)

    execute(
        """INSERT INTO prediction_batches
             (batch_date, n_predictions, n_picks, payload_sha256,
              prev_sha256, chain_sha256)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (batch_date, payload["n_predictions"], payload["n_picks"],
         payload_hash, prev, chain_hash),
    )

    if git_push and settings.chain_git_remote:
        _git_comprometer(out_dir, batch_date, chain_hash)

    log.info("Lote %s sellado. chain=%s", batch_date, chain_hash[:16])
    return receipt


# F7 (sello tardío): cada partido se sella solo, minutos antes del saque, con su predicción final y sus picks de valor.
# El lote diario de las 08:00 UTC sigue igual. `None` = no hay sello por partido (nada cambia hasta fijar el corte al desplegar).
# Primer día sin lote diario sellado al activarlo (el del 19-oct ya selló a las 09:00 UTC). Decisión del titular, 2026-10-19.
LOTE_POR_PARTIDO_DESDE: date | None = date(2026, 10, 20)


def lote_por_partido(dia: date) -> bool:
    """¿Los partidos de `dia` (UTC) se sellan uno a uno? Única fuente de verdad del escritor y del lector."""
    return LOTE_POR_PARTIDO_DESDE is not None and dia >= LOTE_POR_PARTIDO_DESDE


def _ruta_partido(match_id: str, dia: date) -> str:
    """Ruta relativa del lote de un partido. El id sale de la base, pero se valida antes de usarlo como nombre de archivo;
    ':' (frecuente en los ids) se cambia por '_' para que el repo público se pueda clonar en Windows, y un sufijo del hash
    del id evita que dos ids distintos acaben en el mismo archivo."""
    seguro = (match_id or "").replace(":", "_")
    if not seguro or not all(c.isalnum() or c in "-_." for c in seguro) or ".." in seguro:
        raise ValueError(f"match_id no apto como nombre de archivo: {match_id!r}")
    return f"partido/{dia.isoformat()}/{seguro}-{sha256_hex(match_id)[:6]}"


def _collect_partido(match_id: str) -> dict:
    """Predicción final del partido y los picks de valor que salen de ella. El pick y su precio quedan en el lote."""
    preds = query(
        """SELECT p.prediction_id, p.match_id, p.model_version, p.generated_at,
                  p.home_lambda, p.away_lambda, p.rho, p.confidence_tier,
                  p.markets -> '1x2'    AS m_1x2,
                  p.markets -> 'totals' AS m_totals,
                  -- momento y motivo del sello y factor del once en sombra: queda en el JSON que se revela y se verifica
                  p.data_completeness -> 'sello_tardio' AS sello_tardio,
                  m.kickoff_utc, m.league_id,
                  th.canonical_name AS home_team, ta.canonical_name AS away_team
           FROM predictions p
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE p.match_id = %s AND p.etapa = 'final'
           ORDER BY p.generated_at, p.prediction_id""", (match_id,))
    picks = query(
        """SELECT pick_id, prediction_id, match_id, market, selection, line,
                  model_prob, advised_price, bookmaker, edge_pct, raw_edge_pct,
                  stake_units, tier, published_at,
                  fair_prob, min_price, odds_source, odds_as_of
           FROM picks
           WHERE match_id = %s AND prediction_id IN (SELECT prediction_id FROM predictions WHERE etapa = 'final')
           ORDER BY published_at, pick_id""", (match_id,))
    return {
        "batch_kind": "partido",
        "match_id": match_id,
        "model_version": settings.model_version,
        "fs_version": settings.fs_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_predictions": len(preds),
        "n_picks": len(picks),
        "predictions": preds,
        "picks": picks,
    }


def seal_partido(match_id: str, git_push: bool = True) -> dict:
    """Sella el lote de un partido. Idempotente por partido (índice único en la base). Requiere su predicción final."""
    existing = query_one(
        "SELECT batch_id, chain_sha256 FROM prediction_batches WHERE batch_kind = 'partido' AND match_id = %s",
        (match_id,))
    if existing:
        log.warning("El lote del partido %s ya está sellado (%s).", match_id, existing["chain_sha256"][:16])
        return existing

    payload = _collect_partido(match_id)
    if payload["n_predictions"] == 0:
        log.info("Sin predicción final para %s, no se sella nada.", match_id)
        return {}
    dia = payload["predictions"][0]["kickoff_utc"].astimezone(timezone.utc).date()
    ruta = _ruta_partido(match_id, dia)

    body = canonical_json(payload)
    payload_hash = sha256_hex(body)
    prev = _prev_chain_hash()
    chain_hash = sha256_hex(prev + payload_hash)

    out_dir = Path(settings.chain_dir)
    (out_dir / ruta).parent.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{ruta}.json").write_text(body, encoding="utf-8")
    receipt = {
        "batch_kind": "partido",
        "batch_date": dia.isoformat(),
        "match_id": match_id,
        "payload_sha256": payload_hash,
        "prev_sha256": prev,
        "chain_sha256": chain_hash,
        "n_predictions": payload["n_predictions"],
        "n_picks": payload["n_picks"],
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / f"{ruta}.receipt.json").write_text(canonical_json(receipt), encoding="utf-8")
    _append_ledger(out_dir / "LEDGER.md", receipt)

    execute(
        """INSERT INTO prediction_batches
             (batch_date, batch_kind, match_id, n_predictions, n_picks, payload_sha256, prev_sha256, chain_sha256)
           VALUES (%s, 'partido', %s, %s, %s, %s, %s, %s)""",
        (dia, match_id, payload["n_predictions"], payload["n_picks"], payload_hash, prev, chain_hash))

    if git_push and settings.chain_git_remote:
        _git_comprometer(out_dir, dia, chain_hash)
    log.info("Lote del partido %s sellado. chain=%s", match_id, chain_hash[:16])
    return receipt


def _append_ledger(path: Path, r: dict) -> None:
    if not path.exists():
        path.write_text(
            "# Registro público de predicciones\n\n"
            "Cada fila enlaza con la anterior mediante SHA-256. Alterar una "
            "predicción pasada rompe todos los hashes posteriores.\n\n"
            "Verificar: `python -m qf.publish.hashchain verify`\n\n"
            "| Fecha | Preds | Picks | payload_sha256 | chain_sha256 |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as f:
        f.write(f"| {r['batch_date']}{' ' + r['match_id'] if r.get('match_id') else ''} | {r['n_predictions']} | {r['n_picks']} "
                f"| `{r['payload_sha256'][:16]}…` | `{r['chain_sha256'][:16]}…` |\n")


def _git(out_dir: Path, *cmd: str) -> None:
    subprocess.run(["git", *cmd], cwd=out_dir, check=True,
                   env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                   capture_output=True, timeout=120)


def _git_comprometer(out_dir: Path, batch_date: date, chain_hash: str) -> None:
    """Sube SOLO el compromiso (recibos y registro). El JSON del lote se queda sin versionar."""
    try:
        recibos = sorted(p.name for p in out_dir.glob("????-??-??.receipt.json"))
        recibos += sorted(p.relative_to(out_dir).as_posix() for p in out_dir.glob("partido/????-??-??/*.receipt.json"))
        _git(out_dir, "add", "--", "LEDGER.md", *recibos)
        _git(out_dir, "commit", "-m",
             f"compromiso {batch_date.isoformat()} chain={chain_hash[:16]}")
        _git(out_dir, "push", "origin", "HEAD")
        log.info("Compromiso de la cadena publicado en el repo público.")
    except subprocess.CalledProcessError as exc:
        log.error("Fallo al publicar el compromiso: %s", exc.stderr.decode()[:400])


def _ids_de_partidos(payload: dict) -> list[str]:
    """Todos los partidos que cita el lote, de cualquier bloque."""
    escalera = payload.get("escalera") or {}
    parley = payload.get("parley") or {}
    filas = [*payload.get("predictions", []), *payload.get("picks", []),
             *payload.get("alta_probabilidad", []), *payload.get("alta_ext", []),
             *payload.get("tarjetas_seg", []), *escalera.get("pasos", []),
             *parley.get("patas", [])]
    return sorted({f["match_id"] for f in filas if f.get("match_id")})


def _estado_partidos(ids: list[str]) -> tuple[datetime | None, bool]:
    """(último saque, ¿todos terminados?) leído de la base."""
    if not ids:
        return None, True
    row = query_one(
        """SELECT max(kickoff_utc) AS ultimo,
                  bool_and(status IN ('finished', 'cancelled')) AS todos
           FROM matches WHERE match_id = ANY(%s)""", (ids,))
    return (row["ultimo"], bool(row["todos"])) if row else (None, False)


def revelables(out_dir: Path, ahora: datetime, estado=_estado_partidos) -> list[date]:
    """Lotes sellados cuyo JSON ya no regala picks y aún no está en el repo."""
    try:
        subidos = set(subprocess.run(
            ["git", "ls-files", "--", "????-??-??.json"], cwd=out_dir, check=True,
            capture_output=True, timeout=60).stdout.decode().split())
    except (subprocess.CalledProcessError, OSError):
        return []
    due: list[date] = []
    for f in sorted(out_dir.glob("????-??-??.json")):
        if f.name in subidos:
            continue
        ultimo, terminados = estado(_ids_de_partidos(json.loads(f.read_text(encoding="utf-8"))))
        if ultimo is None:
            continue
        pasado = ahora - ultimo
        if (terminados and pasado >= REVELAR_TRAS) or pasado >= REVELAR_TOPE:
            due.append(date.fromisoformat(f.stem))
    return due


def _jsons_de_partido(out_dir: Path) -> list[Path]:
    return sorted(f for f in out_dir.glob("partido/????-??-??/*.json") if not f.name.endswith(".receipt.json"))


def revelables_partido(out_dir: Path, ahora: datetime, estado=_estado_partidos) -> list[str]:
    """Lotes de partido (ruta relativa) cuyo partido ya terminó y cuyo JSON aún no está en el repo."""
    try:
        subidos = set(subprocess.run(
            ["git", "ls-files", "--", "partido"], cwd=out_dir, check=True,
            capture_output=True, timeout=60).stdout.decode().split())
    except (subprocess.CalledProcessError, OSError):
        return []
    due: list[str] = []
    for f in _jsons_de_partido(out_dir):
        rel = f.relative_to(out_dir).as_posix()
        if rel in subidos:
            continue
        ultimo, terminados = estado(_ids_de_partidos(json.loads(f.read_text(encoding="utf-8"))))
        if ultimo is None:
            continue
        pasado = ahora - ultimo
        if (terminados and pasado >= REVELAR_TRAS) or pasado >= REVELAR_TOPE:
            due.append(rel)
    return due


def _git_revelar(out_dir: Path, ahora: datetime | None = None, estado=_estado_partidos) -> list[date]:
    """Sube el JSON de los lotes (diarios y de partido) que ya se pueden revelar. Devuelve las fechas de los diarios."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        fechas = revelables(out_dir, ahora, estado)
        partidos = revelables_partido(out_dir, ahora, estado)
        if not fechas and not partidos:
            return []
        for d in fechas:
            _git(out_dir, "add", "--", f"{d.isoformat()}.json")
        for rel in partidos:
            _git(out_dir, "add", "--", rel)
        _git(out_dir, "commit", "-m",
             "revelado " + ", ".join([d.isoformat() for d in fechas] + [r.removesuffix(".json") for r in partidos]))
        _git(out_dir, "push", "origin", "HEAD")
        log.info("Lotes revelados: %s", [d.isoformat() for d in fechas])
        return fechas
    except subprocess.CalledProcessError as exc:
        log.error("Fallo al revelar lotes: %s", exc.stderr.decode()[:400])
        return []


def _recibos_en_orden(d: Path) -> list[tuple[Path, dict]]:
    """Recibos (diarios y de partido) en el orden de la cadena.

    Con lotes de partido entre los diarios el nombre ya no da el orden: se sigue el enlace `prev_sha256` desde el génesis.
    Si el recorrido no cubre todos los recibos (cadena rota o bifurcada) se vuelve al orden por nombre, y las comprobaciones
    de `verify` señalan el enlace roto.
    """
    archivos = [*sorted(d.glob("????-??-??.receipt.json")), *sorted(d.glob("partido/????-??-??/*.receipt.json"))]
    todos = [(f, json.loads(f.read_text(encoding="utf-8"))) for f in archivos]
    por_prev: dict[str, list] = {}
    for f, r in todos:
        por_prev.setdefault(r.get("prev_sha256"), []).append((f, r))
    orden, prev = [], GENESIS
    while len(por_prev.get(prev, [])) == 1 and len(orden) < len(todos):
        f, r = por_prev[prev][0]
        orden.append((f, r))
        prev = r["chain_sha256"]
    return orden if len(orden) == len(todos) else todos


def verify(chain_dir: str | None = None) -> tuple[bool, list[str]]:
    """
    Recalcula la cadena. Se recorre por recibos: un lote aún sin revelar (sin
    JSON) enlaza igual por su compromiso y se cuenta aparte; uno revelado debe
    cuadrar con el hash comprometido.
    """
    d = Path(chain_dir or settings.chain_dir)
    recibos = _recibos_en_orden(d)
    prev, errors, sin_revelar = GENESIS, [], 0

    for rf, r in recibos:
        nombre = rf.name.removesuffix(".receipt.json")
        chain_hash = sha256_hex(prev + r["payload_sha256"])
        body = rf.with_name(f"{nombre}.json")
        if body.exists():
            payload_hash = sha256_hex(body.read_text(encoding="utf-8"))
            if r["payload_sha256"] != payload_hash:
                errors.append(f"{body.name}: CONTENIDO ALTERADO "
                              f"(esperado {r['payload_sha256'][:16]}, "
                              f"obtenido {payload_hash[:16]})")
        else:
            sin_revelar += 1
        if r["prev_sha256"] != prev:
            errors.append(f"{rf.name}: CADENA ROTA en el enlace anterior")
        if r["chain_sha256"] != chain_hash:
            errors.append(f"{rf.name}: hash de cadena inconsistente")
        prev = r["chain_sha256"]

    for body in [*sorted(d.glob("????-??-??.json")), *_jsons_de_partido(d)]:
        if not body.with_name(f"{body.stem}.receipt.json").exists():
            errors.append(f"{body.name}: falta el recibo")

    ok = not errors
    print(f"{'OK' if ok else 'FALLO'}: {len(recibos)} lotes verificados"
          f" ({len(recibos) - sin_revelar} revelados, {sin_revelar} solo con compromiso)")
    for e in errors:
        print("  !", e)
    return ok, errors


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        ok, _ = verify()
        sys.exit(0 if ok else 1)
    print(canonical_json(seal()))
