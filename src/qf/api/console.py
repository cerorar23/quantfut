"""Panel interno de lectura. Nunca ejecuta jobs ni publica picks."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..db import query, query_one


router = APIRouter(prefix="/control", include_in_schema=False)
_basic = HTTPBasic(auto_error=False)
_log = logging.getLogger(__name__)
_ITERATIONS = 600_000


def verify_password(password: str, encoded: str) -> bool:
    """Acepta únicamente el formato de hash generado por scripts/hash_admin_password.py."""
    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split("$")
        if scheme != "pbkdf2_sha256" or rounds != str(_ITERATIONS):
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) < 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, UnicodeError):
        return False


def require_console(credentials: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    username = os.getenv("ADMIN_CONSOLE_USER", "")
    password_hash = os.getenv("ADMIN_CONSOLE_PASSWORD_HASH", "")
    if not username or not password_hash:
        raise HTTPException(503, "Panel no configurado")
    if credentials is None:
        raise HTTPException(401, "Autenticación necesaria",
                            headers={"WWW-Authenticate": 'Basic realm="QuantFut control"'})
    user_ok = hmac.compare_digest(credentials.username, username)
    pass_ok = verify_password(credentials.password, password_hash)
    if not (user_ok and pass_ok):
        raise HTTPException(401, "Credenciales incorrectas",
                            headers={"WWW-Authenticate": 'Basic realm="QuantFut control"'})


def _read(check):
    try:
        return check()
    except Exception:  # noqa: BLE001 - cada tarjeta debe fallar cerrada y sin traza pública
        _log.exception("Fallo al cargar tarjeta del panel")
        return {"estado": "No disponible; revisar logs del servidor"}


def _commercial_gate() -> dict:
    """La misma evaluación que decide reactivar la publicación, no una copia."""
    from ..publish.shadow_sharp import report

    r = report()
    counts = query_one(
        """SELECT count(*) AS capturadas, count(res.offer_id) AS liquidadas,
                  count(*) FILTER (WHERE o.stake_units > 0) AS con_stake
           FROM sharp_shadow_offers o
           LEFT JOIN sharp_shadow_results res USING (offer_id)""")
    pub = r.get("publishable", {})
    return {"autorizada": r["gate"]["authorized"],
            "motivos": r["gate"]["reasons"],
            "ofertas": counts,
            "publicables": {k: v for k, v in pub.items() if k != "by_league"},
            "publicables_por_liga": pub.get("by_league")}


def _last_training() -> dict | None:
    row = query_one(
        """SELECT model_version, trained_at, is_active, notes
           FROM model_artifacts ORDER BY trained_at DESC LIMIT 1""")
    if row and isinstance(row.get("notes"), str):
        try:
            row["notes"] = json.loads(row["notes"])
        except ValueError:
            pass
    return row


def _snapshot() -> dict:
    from ..ingest.health import run as health_run
    from ..normalize import pending_report
    from ..publish.shadow_sharp import audit as shadow_audit

    return {
        "Puerta comercial (sombra del criterio sharp)": _read(_commercial_gate),
        "Recorrido de la sombra por liga": _read(shadow_audit),
        "Último entrenamiento": _read(_last_training),
        "Salud del sistema": _read(lambda: health_run(alert_on_fail=False)),
        "Nombres sin resolver": _read(pending_report),
        "Picks pendientes de liquidación": _read(lambda: query(
            """SELECT p.pick_id, p.match_id, p.market, p.selection, m.kickoff_utc
               FROM picks p JOIN matches m USING (match_id)
               LEFT JOIN pick_results res USING (pick_id)
               WHERE res.pick_id IS NULL AND m.kickoff_utc < now()
               ORDER BY m.kickoff_utc LIMIT 100""")),
        "Modelo activo": _read(lambda: query_one(
            "SELECT model_version, trained_at FROM model_artifacts WHERE is_active LIMIT 1")),
    }


def _page(data: dict) -> str:
    cards = "".join(
        f'<section class="card"><h2>{html.escape(title)}</h2>'
        f'<pre>{html.escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))}</pre>'
        "</section>"
        for title, value in data.items()
    )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>QuantFut · Control</title><link rel="stylesheet" href="/console.css">'
        '</head><body><header><a href="/">QuantFut</a><span>Control interno · solo lectura</span>'
        '</header><main><div class="intro"><p class="eyebrow">OPERACIÓN</p>'
        '<h1>Estado del sistema</h1><p>Datos en vivo del servidor. Esta vista no ejecuta jobs, '
        'no publica picks ni modifica modelos.</p></div><div class="grid">'
        + cards + '</div></main></body></html>'
    )


@router.get("", dependencies=[Depends(require_console)])
@router.get("/", dependencies=[Depends(require_console)])
def dashboard() -> HTMLResponse:
    return HTMLResponse(_page(_snapshot()), headers={
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    })
