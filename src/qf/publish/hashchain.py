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
           WHERE (p.generated_at AT TIME ZONE 'UTC')::date = %s
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
                  freeroll_x, created_at
           FROM escalera_retos
           WHERE (created_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY reto_id""",
        (batch_date,),
    ) if con_escalera else []
    escalones = query(
        """SELECT paso_id, reto_id, paso, match_id, market, selection, line, prob,
                  fair_price, price, book, odds_source, odds_as_of, decided_at
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
        "SELECT batch_id, chain_sha256 FROM prediction_batches WHERE batch_date = %s",
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
        f.write(f"| {r['batch_date']} | {r['n_predictions']} | {r['n_picks']} "
                f"| `{r['payload_sha256'][:16]}…` | `{r['chain_sha256'][:16]}…` |\n")


def _git(out_dir: Path, *cmd: str) -> None:
    subprocess.run(["git", *cmd], cwd=out_dir, check=True,
                   env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                   capture_output=True, timeout=120)


def _git_comprometer(out_dir: Path, batch_date: date, chain_hash: str) -> None:
    """Sube SOLO el compromiso (recibos y registro). El JSON del lote se queda sin versionar."""
    try:
        recibos = sorted(p.name for p in out_dir.glob("????-??-??.receipt.json"))
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


def _git_revelar(out_dir: Path, ahora: datetime | None = None, estado=_estado_partidos) -> list[date]:
    """Sube el JSON de los lotes que ya se pueden revelar."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        fechas = revelables(out_dir, ahora, estado)
        if not fechas:
            return []
        for d in fechas:
            _git(out_dir, "add", "--", f"{d.isoformat()}.json")
        _git(out_dir, "commit", "-m",
             "revelado " + ", ".join(d.isoformat() for d in fechas))
        _git(out_dir, "push", "origin", "HEAD")
        log.info("Lotes revelados: %s", [d.isoformat() for d in fechas])
        return fechas
    except subprocess.CalledProcessError as exc:
        log.error("Fallo al revelar lotes: %s", exc.stderr.decode()[:400])
        return []


def verify(chain_dir: str | None = None) -> tuple[bool, list[str]]:
    """
    Recalcula la cadena. Se recorre por recibos: un lote aún sin revelar (sin
    JSON) enlaza igual por su compromiso y se cuenta aparte; uno revelado debe
    cuadrar con el hash comprometido.
    """
    d = Path(chain_dir or settings.chain_dir)
    recibos = sorted(d.glob("????-??-??.receipt.json"))
    prev, errors, sin_revelar = GENESIS, [], 0

    for rf in recibos:
        r = json.loads(rf.read_text(encoding="utf-8"))
        nombre = rf.name.removesuffix(".receipt.json")
        chain_hash = sha256_hex(prev + r["payload_sha256"])
        body = d / f"{nombre}.json"
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

    for body in sorted(d.glob("????-??-??.json")):
        if not (d / f"{body.stem}.receipt.json").exists():
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
