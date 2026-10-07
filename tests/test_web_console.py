"""El prototipo y el panel no convierten el navegador en cliente privilegiado."""
import hashlib
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import console, web


def _client(monkeypatch):
    app = FastAPI()
    app.include_router(console.router)
    app.include_router(web.router)
    monkeypatch.setattr(console, "_snapshot", lambda: {"Estado": {"ok": True}})
    monkeypatch.setattr(console, "_shadow_picks", lambda: [])
    return TestClient(app)


def test_web_demo_se_sirve_sin_secreto(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
    assert "QuantFut" in response.text
    assert client.get("/styles.css").status_code == 200
    assert client.get("/app.js").status_code == 200
    assert client.get("/public-data.js").status_code == 200
    assert client.get("/membership.js").status_code == 200
    assert client.get("/membership.css").status_code == 200
    assert client.get("/package.json").status_code == 404
    assert client.get("/server.mjs").status_code == 404
    assert "X-Service-Token" not in Path(web.FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    assert "/v1/" not in Path(web.FRONTEND_DIR / "public-data.js").read_text(encoding="utf-8")
    membership = Path(web.FRONTEND_DIR / "membership.js").read_text(encoding="utf-8")
    assert "/v1/" not in membership
    assert "X-Service-Token" not in membership


def test_panel_falla_cerrado_sin_configuracion(monkeypatch):
    monkeypatch.delenv("ADMIN_CONSOLE_USER", raising=False)
    monkeypatch.delenv("ADMIN_CONSOLE_PASSWORD_HASH", raising=False)
    assert _client(monkeypatch).get("/control").status_code == 503


def test_panel_exige_credenciales_y_escapa_datos(monkeypatch):
    password = "contrasena-de-prueba-larga"
    salt = b"1234567890abcdef"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    encoded = f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"
    monkeypatch.setenv("ADMIN_CONSOLE_USER", "operador")
    monkeypatch.setenv("ADMIN_CONSOLE_PASSWORD_HASH", encoded)
    client = _client(monkeypatch)
    monkeypatch.setattr(console, "_snapshot", lambda: {"<script>": "<img src=x onerror=alert(1)>"})

    unauth = client.get("/control")
    assert unauth.status_code == 401
    assert unauth.headers["www-authenticate"].startswith("Basic")
    assert client.get("/control", auth=("operador", "incorrecta")).status_code == 401

    response = client.get("/control", auth=("operador", password))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "&lt;script&gt;" in response.text
    assert "&lt;img src=x" in response.text
    assert encoded not in response.text


def test_hash_malformado_no_se_acepta():
    assert not console.verify_password("clave", "pbkdf2_sha256$999999999$00$00")
    assert not console.verify_password("clave", "")


def test_montaje_real_no_abre_rutas_privadas(monkeypatch):
    from qf.api import main

    limits = []

    def allow(_redis, _key, limit):
        limits.append(limit)
        return False

    monkeypatch.setattr(main.ratelimit, "rate_limited", allow)
    monkeypatch.delenv("ADMIN_CONSOLE_USER", raising=False)
    monkeypatch.delenv("ADMIN_CONSOLE_PASSWORD_HASH", raising=False)
    client = TestClient(main.app)
    assert client.get("/").status_code == 200
    assert client.get("/control").status_code == 503
    assert limits[-1] == min(main.settings.rate_limit_default_per_minute, 10)
    assert client.get("/v1/picks").status_code == 404
    assert client.get("/admin/health").status_code == 404
    assert client.get("/admin/shadow-audit").status_code == 404


def test_auditoria_json_solo_para_admin(monkeypatch):
    from qf.api import main
    from qf.publish import shadow_sharp

    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_args: False)
    monkeypatch.setattr(main, "ADMIN_TOKEN", "test-secret")
    monkeypatch.setattr(shadow_sharp, "audit", lambda: {
        "total": {"captured": 2}, "by_league": {"us.mls": {"captured": 2}}})
    client = TestClient(main.app)
    assert client.get("/admin/shadow-audit").status_code == 404
    response = client.get("/admin/shadow-audit",
                          headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["by_league"]["us.mls"]["captured"] == 2


def test_tarjeta_de_puerta_usa_el_mismo_report_que_decide(monkeypatch):
    from qf.publish import shadow_sharp
    gate = {"authorized": False, "reasons": ["CLV con muestra insuficiente (4 < 300)"]}
    monkeypatch.setattr(shadow_sharp, "report", lambda: {
        "gate": gate, "publishable": {"n": 4, "by_league": {"x": {}}}})
    monkeypatch.setattr(console, "query_one", lambda sql: {"capturadas": 9})
    card = console._commercial_gate()
    assert card["autorizada"] is False and card["motivos"] == gate["reasons"]
    assert "by_league" not in card["publicables"]
    assert card["publicables_por_liga"] == {"x": {}}


def test_model_card_no_anuncia_picks_activos_si_sombra_no_aprueba(monkeypatch):
    from qf.api import main
    from qf.publish import shadow_sharp

    monkeypatch.setattr(main, "query_one", lambda *_args: None)
    monkeypatch.setattr(main, "clv_report", lambda **_kwargs: {"n": 0})
    monkeypatch.setattr(main, "evaluate_clv_gate", lambda _report: (False, ["Sin muestra"]))
    monkeypatch.setattr(main, "settings", replace(main.settings, publish_picks_enabled=True))
    shadow_gate = {"authorized": False, "reasons": ["Aún sin CLV"]}
    monkeypatch.setattr(shadow_sharp, "report", lambda: {
        "gate": shadow_gate, "publishable": {"n": 2}, "n_offers": 4})

    card = main.model_card()
    assert card["puerta_comercial"]["publicacion_de_picks"].startswith("pausada")
    assert card["puerta_comercial"]["sombra_criterio_sharp"]["ofertas_registradas"] == 4

    shadow_gate["authorized"] = True
    assert main.model_card()["puerta_comercial"]["publicacion_de_picks"] == "activa"


def test_ultimo_entrenamiento_muestra_motivos_legibles(monkeypatch):
    monkeypatch.setattr(console, "query_one", lambda sql: {
        "model_version": "v", "is_active": False,
        "notes": '{"promote": false, "reasons": ["Mercado sharp demasiado antiguo"]}'})
    assert console._last_training()["notes"]["reasons"] == ["Mercado sharp demasiado antiguo"]


def _fila_sombra(**changes):
    from datetime import datetime, timezone
    base = {"kickoff_utc": datetime(2026, 10, 3, 21, 30, tzinfo=timezone.utc),
            "league_id": "br.serie_b", "partido": "Avai - Ceara", "selection": "draw",
            "book": "1xbet", "price": 3.38, "min_price": 3.3, "closing_price": 3.11,
            "expected_edge_pct": 1.96, "stake_units": 0.17, "lead_minutes": 4320,
            "ev_close_pct": 4.33, "outcome": "loss", "profit_units": -1.0, "marcador": "0-1"}
    return {**base, **changes}


def test_tabla_de_sombra_escapa_y_marca_pendientes():
    html_ = console._shadow_table([
        _fila_sombra(partido="<script>alert(1)</script> - X"),
        _fila_sombra(closing_price=None, ev_close_pct=None, outcome=None,
                     profit_units=None, marcador=None)])
    assert "<script>alert" not in html_ and "&lt;script&gt;" in html_
    assert "Empate" in html_ and "Perdida (0-1)" in html_ and "Pendiente" in html_
    assert '<td class="pos">+4,33 %</td>' in html_
    assert '<td class="neg">-1,00</td>' in html_
    assert "72,0 h" in html_


def test_tabla_de_sombra_falla_cerrada():
    assert "No disponible" in console._shadow_table({"estado": "No disponible"})
    assert "Todavía no hay ninguna" in console._shadow_table([])
