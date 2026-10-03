"""
La alerta de bajas saltó del 28-sep al 1-oct y no la vio nadie: el aviso iba
a Telegram sin token (solo un WARNING), y el log del cron vivía dentro del
contenedor y se borraba en cada despliegue. Estos tests fijan lo mínimo para
que un fallo del chequeo diario deje rastro.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

from qf.ingest import health
from qf.publish import telegram


def test_el_chequeo_diario_guarda_su_resultado(monkeypatch):
    guardado = []
    monkeypatch.setattr(health, "CHECKS", [("uno", lambda: (False, "roto")),
                                           ("dos", lambda: (True, "bien"))])
    monkeypatch.setattr(health, "execute",
                        lambda sql, params=None: guardado.append((sql, params)) or 1)
    res = health.run(alert_on_fail=False, persist=True)
    assert not res["ok"]
    assert len(guardado) == 1
    sql, params = guardado[0]
    assert "INSERT INTO health_runs" in sql
    assert params[0] is False and '"roto"' in params[1]


def test_el_panel_no_escribe_historial(monkeypatch):
    monkeypatch.setattr(health, "CHECKS", [("uno", lambda: (True, "bien"))])
    monkeypatch.setattr(health, "execute",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("escribió")))
    assert health.run(alert_on_fail=False)["ok"]


def test_si_no_se_puede_guardar_igual_avisa(monkeypatch):
    avisos = []
    monkeypatch.setattr(health, "CHECKS", [("uno", lambda: (False, "roto"))])
    monkeypatch.setattr(health, "execute",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db caída")))
    monkeypatch.setattr(telegram, "alert", avisos.append)
    health.run(alert_on_fail=True, persist=True)
    assert avisos and "roto" in avisos[0]


def test_alerta_sin_telegram_queda_como_error_con_su_texto(monkeypatch, caplog):
    # settings es un dataclass congelado: se sustituye entero.
    monkeypatch.setattr(telegram, "settings",
                        SimpleNamespace(tg_bot_token="", tg_alert_chat=""))
    with caplog.at_level(logging.WARNING):
        telegram.alert("Chequeo diario con fallos: X")
    registro = [r for r in caplog.records if "Chequeo diario con fallos: X" in r.getMessage()]
    assert registro and registro[0].levelno == logging.ERROR


def test_el_mensaje_de_bajas_no_da_por_hecho_que_es_el_proveedor(monkeypatch):
    monkeypatch.setattr(health, "query", lambda sql, params=None: [
        {"league_id": "us.mls", "checked": 17, "total_reported": 0}])
    ok, msg = health.check_injuries_coverage()
    assert not ok and "us.mls" in msg
    assert "error nuestro" in msg


def test_la_alerta_escapa_html(monkeypatch):
    enviados = []
    monkeypatch.setattr(telegram, "settings",
                        SimpleNamespace(tg_bot_token="t", tg_alert_chat="1"))
    monkeypatch.setattr(telegram, "_send", lambda chat, text, **k: enviados.append(text))
    telegram.alert("CLV con muestra insuficiente (5 < 300) & <otra>")
    assert "5 &lt; 300" in enviados[0] and "&amp;" in enviados[0]
    assert "<b>QUANTFUT</b>" in enviados[0]


def test_si_telegram_falla_la_alerta_no_tumba_el_job(monkeypatch, caplog):
    monkeypatch.setattr(telegram, "settings",
                        SimpleNamespace(tg_bot_token="t", tg_alert_chat="1"))

    def falla(*a, **k):
        raise RuntimeError("telegram caído")

    monkeypatch.setattr(telegram, "_send", falla)
    telegram.alert("algo grave")
    assert any("algo grave" in r.getMessage() and r.levelno == logging.ERROR
               for r in caplog.records)
