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


def test_lineup_ids_are_resolved_in_their_original_provider_namespace():
    player = {"player_id": 191210, "name": "Mike Maignan", "src": "sofascore"}
    assert imagenes.lineup_photo(player) == "/web/imagenes/jugadores/sofascore/191210.webp"
    assert imagenes.lineup_photo({**player, "src": "api_football"}) == "/web/imagenes/jugadores/futbol/191210.png"
    assert imagenes.lineup_photo({"player_id": 874}) == "/web/imagenes/jugadores/futbol/874.png"
    assert imagenes.lineup_photo({**player, "src": "fotmob"}) is None
    assert imagenes.lineup_photo({**player, "src": "unknown"}) is None


def test_sofascore_uses_its_own_url_and_webp_cache(tmp_path, monkeypatch):
    import base64
    body = base64.b64decode("UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA")
    calls = []
    def reply(request):
        calls.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "image/webp"}, content=body)
    transport(monkeypatch, reply)
    path = imagenes.cached_portrait("sofascore", 191210, tmp_path)
    assert path.suffix == ".webp" and path.read_bytes() == body
    assert calls == ["https://img.sofascore.com/api/v1/player/191210/image"]


def test_confirmed_and_historical_lineups_keep_the_provider_when_creating_photo_urls(monkeypatch):
    from qf.api import fichas
    players = [{"name": "Sofa player", "player_id": 191210, "src": "sofascore"},
               {"name": "Legacy player", "player_id": 874}]
    row = {"side": "home", "match_id": "test", "kickoff_utc": "2026-10-28", "competicion": "test",
           "rival": "test", "formation": "4-4-2", "starters": players, "captured_at": "2026-10-28"}
    monkeypatch.setattr(fichas, "query", lambda *args: [row])
    expected = ["/web/imagenes/jugadores/sofascore/191210.webp", "/web/imagenes/jugadores/futbol/874.png"]
    assert [p["foto"] for p in fichas._formatear_once(row)["titulares"]] == expected
    assert [p["foto"] for p in fichas._alineaciones("test")["home"]["titulares"]] == expected
