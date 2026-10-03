"""
Publicación en Telegram.

Dos canales:
  - FREE: 1-2 picks al día + el hash del lote. Es tu marketing y tu prueba
    pública. Todo el mundo ve el track record, incluidas las rachas malas.
  - PAID: el resto de picks, con cuota aconsejada y stake.

Regla de oro: el mensaje SIEMPRE se publica antes del kickoff y nunca se edita
después. Telegram permite editar mensajes; no lo hagas. El hash del lote es lo
que demuestra que no lo hiciste.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from .picks import Candidate

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"

MARKET_ES = {
    "h2h": "1X2",
    "totals": "Total goles",
    "spreads": "Hándicap asiático",
    "btts": "Ambos anotan",
    "double_chance": "Doble oportunidad",
    "team_totals_home": "Total local",
    "team_totals_away": "Total visitante",
}
SEL_ES = {"home": "Local", "away": "Visitante", "draw": "Empate",
          "over": "Más de", "under": "Menos de", "yes": "Sí", "no": "No"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def _send(chat_id: str, text: str, disable_preview: bool = True) -> dict:
    if not settings.tg_bot_token or not chat_id:
        log.warning("Telegram no configurado; mensaje omitido.")
        return {}
    with httpx.Client(timeout=20) as c:
        r = c.post(
            API.format(token=settings.tg_bot_token, method="sendMessage"),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": disable_preview},
        )
        r.raise_for_status()
        return r.json()


def alert(text: str) -> None:
    """Alerta operativa (fallo de cron, scraper roto, cuota de API agotada)."""
    if not settings.tg_bot_token or not settings.tg_alert_chat:
        # Un WARNING genérico ("mensaje omitido") escondió del 28-sep al
        # 1-oct-2026 la alerta de bajas: sin canal, el texto queda al menos
        # como ERROR en el log.
        log.error("ALERTA sin canal (Telegram no configurado): %s", text)
        return
    try:
        # parse_mode HTML: un "5 < 300" sin escapar hace que Telegram rechace
        # el mensaje entero.
        _send(settings.tg_alert_chat, f"⚠️ <b>QUANTFUT</b>\n{html.escape(text)}")
    except Exception as exc:  # noqa: BLE001 — avisar no puede tumbar el job
        log.error("ALERTA no enviada (%s): %s", exc, text)


def format_pick(c: Candidate, teams: tuple[str, str], show_stake: bool = True) -> str:
    home, away = teams
    mkt = MARKET_ES.get(c.market, c.market)
    sel = SEL_ES.get(c.selection, c.selection)
    line = "" if c.line is None else f" {c.line:+g}"
    ko = c.kickoff_utc.strftime("%d/%m %H:%M UTC") if c.kickoff_utc else ""

    lines = [
        f"⚽ <b>{home} vs {away}</b>",
        f"🕐 {ko}",
        f"🎯 {mkt}: <b>{sel}{line}</b>",
        f"💰 Cuota aconsejada: <b>{c.best_price:.2f}</b> ({c.best_book})",
        # Liga "solo sharp" (db/023): el modelo no la precia, no hay prob.
        f"📊 Prob. modelo: "
        f"{'—' if c.model_prob is None else f'{c.model_prob*100:.1f}%'}  |  "
        f"Prob. mercado: {c.market_prob*100:.1f}%",
        f"📈 Edge: <b>{c.shrunk_edge:+.1f}%</b>",
    ]
    if show_stake:
        lines.append(f"🔢 Stake: <b>{c.stake_units:.2f} u</b> (Kelly "
                     f"{settings.kelly_fraction:g})")
    return "\n".join(lines)


def publish_batch(picks: list[Candidate], team_names: dict[str, tuple[str, str]],
                  chain_hash: str, free_count: int = 2) -> dict:
    """
    Publica el lote del día. Los `free_count` de mayor edge van al canal
    gratuito; el resto al de pago.
    """
    if not picks:
        return {"free": 0, "paid": 0}

    stamp = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    free, paid = picks[:free_count], picks[free_count:]

    header = (f"📅 <b>Picks {stamp}</b>\n"
              f"🔒 Hash del lote: <code>{chain_hash[:16]}…</code>\n"
              f"Verificable en el registro público antes del kickoff.\n"
              f"{'─' * 24}")

    if free:
        body = "\n\n".join(format_pick(c, team_names[c.match_id], show_stake=False)
                           for c in free)
        footer = ("\n\n<i>Esto no es asesoría financiera. Apuesta solo lo que "
                  "puedas permitirte perder. Track record completo y auditable "
                  "en el registro público.</i>")
        _send(settings.tg_channel_free, f"{header}\n\n{body}{footer}")

    if paid:
        body = "\n\n".join(format_pick(c, team_names[c.match_id], show_stake=True)
                           for c in paid)
        total = sum(c.stake_units for c in paid)
        footer = (f"\n\n{'─' * 24}\n💼 Exposición total: {total:.2f} u"
                  f"\n\n<i>Esto no es asesoría financiera. Gestiona tu banca.</i>")
        _send(settings.tg_channel_paid, f"{header}\n\n{body}{footer}")

    return {"free": len(free), "paid": len(paid)}


def publish_results(summary: dict) -> None:
    """Resumen semanal. Se publica SIEMPRE, incluidas las semanas en pérdida."""
    sign = "🟢" if summary.get("profit_units", 0) >= 0 else "🔴"
    text = (
        f"📊 <b>Resumen semanal</b>\n{'─' * 24}\n"
        f"Picks liquidados: {summary.get('n', 0)}\n"
        f"CLV medio: <b>{summary.get('avg_clv', 0):+.2f}%</b>\n"
        f"% que batió el cierre: {summary.get('pct_beat_close', 0):.0f}%\n"
        f"{sign} P&L: <b>{summary.get('profit_units', 0):+.2f} u</b> "
        f"(ROI {summary.get('roi', 0):+.2f}%)\n\n"
        f"<i>El CLV es la métrica que importa: mide si tomamos mejor precio que "
        f"el cierre del mercado. El P&L a corto plazo es ruido.</i>"
    )
    _send(settings.tg_channel_free, text)
