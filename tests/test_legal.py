from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api.legal import router
from qf.comercial.firebase import CONSENT_VERSION


def test_anonymous_legal_pages_match_consent_and_have_no_tracking():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    for slug in ("terminos", "privacidad", "eliminar-cuenta"):
        response = client.get(f"/legal/{slug}")
        assert response.status_code == 200
        assert CONSENT_VERSION in response.text
        assert "admin@pronosticosdeportivos.pro" in response.text
        assert "admin@pronosticosdeportivos.com" not in response.text
        assert "[CONFIRMAR" not in response.text and "Borrador" not in response.text
        assert "<script" not in response.text
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/legal/arbitrary-file").status_code == 404
