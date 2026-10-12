"""Sentry del backend: solo con DSN y sin datos personales (src/qf/observabilidad.py)."""
import json

import pytest

from qf import observabilidad


def test_sin_dsn_no_hace_nada(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr(observabilidad, "_iniciado", False)
    assert observabilidad.iniciar() is False


def test_antes_de_enviar_quita_lo_identificable():
    evento = {
        "request": {"url": "https://x.pro/cuenta/verificar?token=SECRETO", "method": "GET",
                    "headers": {"Authorization": "Bearer abc"}, "cookies": {"s": "1"},
                    "data": {"password": "p"}, "query_string": "token=SECRETO", "env": {"A": "b"}},
        "user": {"email": "a@b.com", "ip_address": "1.2.3.4"},
        "server_name": "vps-1",
        "extra": {"cuenta": 5, "api_key": "k", "nested": {"refresh_token": "t", "ok": 1}},
    }
    limpio = observabilidad.antes_de_enviar(evento)
    texto = json.dumps(limpio)
    for secreto in ("SECRETO", "Bearer", "a@b.com", "1.2.3.4", "vps-1", '"k"', '"t"', '"p"'):
        assert secreto not in texto, secreto
    assert limpio["request"]["url"] == "https://x.pro/cuenta/verificar"
    assert limpio["extra"]["cuenta"] == 5 and limpio["extra"]["nested"]["ok"] == 1


def _transporte():
    from sentry_sdk.transport import Transport

    class Falso(Transport):
        def __init__(self, options=None):
            super().__init__(options)
            self.enviados = []

        def capture_envelope(self, envelope):
            self.enviados.append(envelope)

    return Falso()


def test_un_error_llega_limpio_y_sin_migas(monkeypatch):
    sentry_sdk = pytest.importorskip("sentry_sdk")
    monkeypatch.setenv("SENTRY_DSN", "https://clave@o0.ingest.sentry.io/0")
    monkeypatch.setattr(observabilidad, "_iniciado", False)
    transporte = _transporte()
    assert observabilidad.iniciar(transport=transporte) is True
    try:
        secreto = "-".join(["clave", "dinamica", "XYZ"])
        raise ValueError(f"fallo {len(secreto)}")
    except ValueError:
        sentry_sdk.capture_exception()
    assert len(transporte.enviados) == 1
    carga = b"".join(bytes(i.payload.get_bytes()) for i in transporte.enviados[0].items).decode()
    assert "-".join(["clave", "dinamica", "XYZ"]) not in carga          # sin variables locales
    assert '"breadcrumbs":{"values":[]}' in carga
    assert "sys.argv" not in carga
    assert "ValueError" in carga
    sentry_sdk.get_client().close()
    monkeypatch.setattr(observabilidad, "_iniciado", False)
