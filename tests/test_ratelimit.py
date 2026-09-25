"""
Rate limiting (`qf.api.ratelimit`): contador de ventana fija sobre un Redis
falso mínimo, sin levantar un Redis real.
"""
from __future__ import annotations

from qf.api import ratelimit


class _FakeRedis:
    """INCR/EXPIRE mínimo en memoria, suficiente para probar la ventana fija."""

    def __init__(self):
        self._data: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    def expire(self, key: str, seconds: int) -> None:
        pass  # no hace falta expirar de verdad para el test


def test_rate_limited_permite_hasta_el_limite():
    redis_fake = _FakeRedis()
    for _ in range(5):
        assert not ratelimit.rate_limited(redis_fake, "1.2.3.4", limit=5)


def test_rate_limited_bloquea_al_superar_el_limite():
    redis_fake = _FakeRedis()
    for _ in range(5):
        ratelimit.rate_limited(redis_fake, "1.2.3.4", limit=5)
    assert ratelimit.rate_limited(redis_fake, "1.2.3.4", limit=5)


def test_rate_limited_no_mezcla_claves_distintas():
    redis_fake = _FakeRedis()
    for _ in range(5):
        ratelimit.rate_limited(redis_fake, "ip-a", limit=5)
    assert not ratelimit.rate_limited(redis_fake, "ip-b", limit=5)


def _app(monkeypatch):
    from fastapi.testclient import TestClient
    from qf.api import main
    monkeypatch.setattr(main, "r", _FakeRedis())
    monkeypatch.delenv("ADMIN_CONSOLE_USER", raising=False)
    monkeypatch.delenv("ADMIN_CONSOLE_PASSWORD_HASH", raising=False)
    return main, TestClient(main.app)


def test_visitar_la_web_no_agota_el_cupo_del_panel(monkeypatch):
    main, client = _app(monkeypatch)
    for _ in range(15):
        client.get("/", headers={"X-Forwarded-For": "1.2.3.4"})
    # Sin credenciales configuradas el panel responde 503; lo que no puede es 429.
    assert client.get("/control", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 503


def test_el_panel_tiene_su_propio_tope(monkeypatch):
    main, client = _app(monkeypatch)
    tope = min(main.settings.rate_limit_default_per_minute, 10)
    codes = [client.get("/control", headers={"X-Forwarded-For": "1.2.3.4"}).status_code
             for _ in range(tope + 1)]
    assert codes[-1] == 429 and 429 not in codes[:-1]


def test_ipv6_se_agrupa_por_64_e_ipv4_no_cambia(monkeypatch):
    from starlette.requests import Request
    from qf.api import main

    def key(ip):
        return main._client_key(Request({"type": "http", "headers": [
            (b"x-forwarded-for", ip.encode())], "client": ("127.0.0.1", 1)}))
    assert key("2001:db8:1:2::a") == key("2001:db8:1:2:ffff::1") == "2001:db8:1:2::/64"
    assert key("2001:db8:1:3::a") != key("2001:db8:1:2::a")
    assert key("203.0.113.7") == "203.0.113.7"
    assert key("::ffff:203.0.113.7") == "203.0.113.7"
    assert key("no-es-ip") == "no-es-ip"
