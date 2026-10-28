from pathlib import Path

import httpx
import pytest

from qf.api import imagenes

REAL_CLIENT = httpx.Client
PNG = (Path(__file__).resolve().parents[1] / "frontend/imagenes/nba/BOS.png").read_bytes()


@pytest.fixture(autouse=True)
def clear_misses():
    imagenes._missing.clear()
    yield
    imagenes._missing.clear()


def transport(monkeypatch, handler):
    monkeypatch.setattr(imagenes.httpx, "Client", lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw))


def test_only_fixed_sports_and_numeric_ids_are_accepted(tmp_path, monkeypatch):
    transport(monkeypatch, lambda request: pytest.fail("Invalid identity must never reach the network"))
    for sport, value in [("tenis", 12), ("nba", "../2544"), ("nba", "https://private/"), ("futbol", 0), ("nba", 1610612738)]:
        assert imagenes.photo_url(sport, value) is None
        assert imagenes.cached_portrait(sport, value, tmp_path) is None
    assert imagenes.photo_url("nba", 2544) == "/web/imagenes/jugadores/nba/2544.png"


def test_real_image_is_cached_and_reused_without_a_second_request(tmp_path, monkeypatch):
    calls = []
    def reply(request):
        calls.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "image/png"}, content=PNG)
    transport(monkeypatch, reply)
    path = imagenes.cached_portrait("nba", "2544", tmp_path)
    assert path.read_bytes() == PNG
    assert imagenes.cached_portrait("nba", "2544", tmp_path) == path
    assert calls == ["https://cdn.nba.com/headshots/nba/latest/260x190/2544.png"]
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("status,mime,body", [(404, "image/png", PNG), (200, "text/html", b"<html>error</html>"), (302, "image/png", PNG), (200, "image/png", PNG[:30]), (200, "image/png", b"x" * 512_001)], ids=["missing", "html", "redirect", "truncated", "oversized"])
def test_failures_and_invalid_images_are_not_saved_or_retried_in_a_loop(tmp_path, monkeypatch, status, mime, body):
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(status, headers={"content-type": mime, "location": "http://127.0.0.1/private"}, content=body)
    transport(monkeypatch, reply)
    assert imagenes.cached_portrait("futbol", 874, tmp_path) is None
    assert imagenes.cached_portrait("futbol", 874, tmp_path) is None
    assert len(calls) == 1
    assert not list(tmp_path.rglob("*.png"))


def test_corrupt_existing_cache_is_replaced(tmp_path, monkeypatch):
    target = tmp_path / "futbol/874.png"
    target.parent.mkdir()
    target.write_bytes(b"corrupt")
    transport(monkeypatch, lambda request: httpx.Response(200, headers={"content-type": "image/png"}, content=PNG))
    assert imagenes.cached_portrait("futbol", 874, tmp_path).read_bytes() == PNG
