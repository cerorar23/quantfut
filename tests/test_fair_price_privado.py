"""
`/fair-price` no es público: dice qué casa paga por encima del precio justo
en cada partido, que es el criterio de picks. Vive en `/v1` con
`SERVICE_TOKEN`, y sin él responde 404 como el resto de rutas privadas.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_fair_price_exige_el_token_de_servicio(monkeypatch):
    from qf.api import main

    monkeypatch.setattr(main, "r", None)
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(main, "SERVICE_TOKEN", "token-de-prueba")
    monkeypatch.setattr(main, "query_one", lambda *a, **k: None)
    cliente = TestClient(main.app)

    assert cliente.get("/fair-price/x").status_code == 404          # ruta pública retirada
    assert cliente.get("/v1/fair-price/x").status_code == 404       # sin token
    assert cliente.get("/v1/fair-price/x",
                       headers={"X-Service-Token": "otro"}).status_code == 404
    r = cliente.get("/v1/fair-price/x", headers={"X-Service-Token": "token-de-prueba"})
    assert r.status_code == 404 and r.json()["detail"] == "Partido no encontrado"
