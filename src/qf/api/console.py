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


def _alta_card() -> dict:
    """Estado de la línea de alta probabilidad: lo mismo que ve la web, sin la lista."""
    from ..publish import alta_prob_datos

    informe = alta_prob_datos.informe_publico()
    return {"estado": informe["estado"], "motivos": informe["motivos"],
            "proximos_sellados": len(informe["proximos"]),
            "historial": informe["historial"]}


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
        "Línea de alta probabilidad": _read(_alta_card),
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


_SELECCION = {"home": "Local", "draw": "Empate", "away": "Visita"}
_RESULTADO = {"win": "Ganada", "loss": "Perdida", "push": "Nula"}


def _num(x, dec: int = 2, signo: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x:{'+' if signo else ''}.{dec}f}".replace(".", ",")


def _clase(x) -> str:
    return "" if x is None or x == 0 else (' class="pos"' if x > 0 else ' class="neg"')


def _shadow_table(rows: list[dict] | dict) -> str:
    """Las que se habrían publicado. Aquí y no en la web: enseña el criterio."""
    title = '<h2>Picks que se habrían publicado (sombra del criterio sharp)</h2>'
    if isinstance(rows, dict):  # la tarjeta falló cerrada en `_read`
        body = f"<pre>{html.escape(json.dumps(rows, ensure_ascii=False))}</pre>"
    elif not rows:
        body = "<p>Todavía no hay ninguna.</p>"
    else:
        head = ("Inicio (UTC)", "Liga", "Partido", "Apuesta", "Casa", "Cuota",
                "Cuota mín.", "Cierre Pinnacle", "Edge esperado", "Stake",
                "Antelación", "EV al cierre", "Resultado", "P/L (1 u)")
        trs = []
        for r in rows:
            ko = r["kickoff_utc"]
            ko = ko.strftime("%d-%m-%Y %H:%M") if hasattr(ko, "strftime") else str(ko)
            res = _RESULTADO.get(r["outcome"], r["outcome"]) if r["outcome"] else "Pendiente"
            if r["marcador"]:
                res = f"{res} ({r['marcador']})"
            celdas = (
                (ko, ""), (r["league_id"], ""), (r["partido"], ""),
                (_SELECCION.get(r["selection"], r["selection"]), ""), (r["book"], ""),
                (_num(r["price"]), ""), (_num(r["min_price"]), ""),
                (_num(r["closing_price"]), ""),
                (_num(r["expected_edge_pct"], signo=True) + " %", ""),
                (_num(r["stake_units"]), ""),
                (_num(r["lead_minutes"] / 60, 1) + " h", ""),
                (_num(r["ev_close_pct"], signo=True) + (" %" if r["ev_close_pct"] is not None else ""),
                 _clase(r["ev_close_pct"])),
                (res, ""),
                (_num(r["profit_units"], signo=True), _clase(r["profit_units"])),
            )
            trs.append("<tr>" + "".join(f"<td{c}>{html.escape(str(v))}</td>" for v, c in celdas)
                       + "</tr>")
        body = ('<p class="nota">Una por partido: la primera pasada con stake y, de ella, '
                'la de mayor edge esperado. Es la muestra que cuenta la puerta; solo las que '
                'tienen cierre de Pinnacle entran en el CLV.</p><div class="tabla"><table><thead><tr>'
                + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
                + "".join(trs) + "</tbody></table></div>")
    return f'<section class="card wide">{title}{body}</section>'


def _shadow_picks() -> list[dict]:
    from ..publish.shadow_sharp import publishable_list

    return publishable_list()


def _page(data: dict, sombra: list[dict] | dict | None = None) -> str:
    cards = "".join(
        f'<section class="card"><h2>{html.escape(title)}</h2>'
        f'<pre>{html.escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))}</pre>'
        "</section>"
        for title, value in data.items()
    )
    if sombra is not None:
        cards = _shadow_table(sombra) + cards
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
    return HTMLResponse(_page(_snapshot(), _read(_shadow_picks)), headers={
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    })
