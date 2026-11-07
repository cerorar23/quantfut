"""Pruebas unitarias de las rutas de API FastAPI /tenis/v2 (Sprint 6)."""
import pytest
from fastapi.testclient import TestClient

from qf.api import main
from qf.api.main import app


class _FakeRedis:
    def __init__(self):
        self._data: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    def expire(self, key: str, seconds: int) -> None:
        pass


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    monkeypatch.setattr(main, "r", _FakeRedis())


@pytest.fixture
def client():
    return TestClient(app)


def test_cartelera_fecha_invalida_responde_400(client):
    r = client.get("/tenis/v2/cartelera?fecha=no-es-fecha")
    assert r.status_code == 400
    assert r.json() == {"detail": "fecha_invalida"}


def test_partido_inexistente_responde_404(client, monkeypatch):
    # Mock query_one para simular que no existe en base de datos
    from qf.api import tenis_v2
    monkeypatch.setattr(tenis_v2, "query_one", lambda *args, **kwargs: None)

    r = client.get("/tenis/v2/partido/999999999")
    assert r.status_code == 404
    assert r.json() == {"detail": "partido_no_encontrado"}


def test_metodologia_responde_200_con_transparencia_y_sesgos(client):
    r = client.get("/tenis/v2/metodologia")
    assert r.status_code == 200
    data = r.json()
    assert "version_modelo" in data
    assert "arquitectura" in data
    assert "principios_inmutables" in data
    assert "compuertas_validadas" in data
    assert "sesgos_conocidos_declarados" in data

    # Verificación de sesgos empíricos declarados
    sesgos = data["sesgos_conocidos_declarados"]
    assert "+0.736" in sesgos["totales_juegos_sesgo_iid"]
    assert "+0.608" in sesgos["totales_juegos_sesgo_iid"]
    assert "phi_1 aprox 0" in sesgos["fatiga_intratorneo"]
