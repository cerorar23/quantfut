import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import web

app = FastAPI()
app.include_router(web.router)
client = TestClient(app)


def manifest():
    return json.loads((web.IMAGES_DIR / "manifiesto.json").read_text(encoding="utf-8"))


def test_manifest_and_credits_are_served():
    response = client.get("/web/imagenes/manifiesto.json")
    assert response.status_code == 200
    assert response.json()["version"] == 1
    credits = client.get("/web/imagenes/creditos")
    assert credits.status_code == 200
    assert "Wikimedia Commons" in credits.text and "TheSportsDB" in credits.text
    assert "<script" not in credits.text
    assert "default-src 'none'" in credits.headers["Content-Security-Policy"]


def test_every_manifest_entry_has_its_file_with_real_image_bytes():
    m = manifest()
    assert len(m["nba"]) == 30
    assert len(m["tenis"]) > 100
    for carpeta in ("nba", "tenis"):
        for clave, entry in m[carpeta].items():
            response = client.get(f"/web/imagenes/{carpeta}/{entry['f']}")
            assert response.status_code == 200, clave
            assert response.headers["content-type"] in ("image/png", "image/jpeg")
            assert response.content.startswith((b"\x89PNG", b"\xff\xd8")), clave
            assert len(response.content) <= 300_000, clave


def test_every_tennis_photo_credits_author_and_a_cc_licence():
    for clave, entry in manifest()["tenis"].items():
        assert entry["a"].strip(), clave
        if entry.get("fuente") == "API-Tennis":
            assert entry["l"] == "Imagen del proveedor"
            assert entry["p"].startswith("https://api.api-tennis.com/logo-tennis/")
            continue
        assert entry["l"].startswith(("CC BY", "CC0", "Public domain", "Dominio")), (clave, entry["l"])
        assert entry["p"].startswith("https://commons.wikimedia.org/"), clave


def test_only_known_folders_and_plain_file_names_are_served():
    nba_file = next(iter(manifest()["nba"].values()))["f"]
    assert client.get(f"/web/imagenes/otra/{nba_file}").status_code == 404
    assert client.get("/web/imagenes/nba/..%2fmanifiesto.json").status_code == 404
    assert client.get("/web/imagenes/nba/%2e%2e/manifiesto.json").status_code == 404
    assert client.get("/web/imagenes/nba/manifiesto.json").status_code == 404
    assert client.get("/web/imagenes/nba/NO-EXISTE.png").status_code == 404
    assert client.get("/web/imagenes/nba/script.js").status_code == 404


def test_portrait_route_uses_only_fixed_providers_and_serves_the_new_assets(monkeypatch, tmp_path):
    from qf.api import imagenes
    calls = []
    def image(sport, player_id, directory):
        calls.append((sport, player_id))
        return web.IMAGES_DIR / "nba" / "BOS.png" if (sport, player_id) == ("nba", "2544") else None
    monkeypatch.setattr(imagenes, "cached_portrait", image)
    portrait = client.get("/web/imagenes/jugadores/nba/2544.png")
    assert portrait.status_code == 200 and portrait.headers["content-type"] == "image/png"
    assert calls == [("nba", "2544")]
    missing = client.get("/web/imagenes/jugadores/nba/0.png")
    assert missing.status_code == 404 and missing.headers["cache-control"] == "no-store"
    for path in ("/sport-images.js", "/sport-images.css", "/web/imagenes/futbol/85064.png"):
        assert client.get(path).status_code == 200


# --- F7b: fotos de tenistas de SofaScore ---------------------------------------

def test_tenis_sofascore_bloque_y_archivos_webp():
    m = manifest()
    bloque = m["tenis_sofascore"]
    assert len(bloque) > 1000 and "tenis" in m  # el bloque viejo se conserva
    for clave, v in bloque.items():
        for e in (v if isinstance(v, list) else [v]):
            assert set(e) == {"id", "f", "pais", "genero", "ranking"}, clave
            ext = e["f"].rsplit(".", 1)[1]
            cab = (web.IMAGES_DIR / "tenis" / e["f"]).read_bytes()[:12]
            png, jpg = bytes([0x89, 0x50, 0x4E, 0x47]), bytes([0xFF, 0xD8, 0xFF])
            assert {"webp": cab[8:12] == b"WEBP", "png": cab[:4] == png, "jpg": cab[:3] == jpg}[ext], clave


def test_tenis_sofascore_se_sirve_como_webp_y_claves_normalizadas():
    bloque = manifest()["tenis_sofascore"]
    entrada = bloque["jannik sinner"]
    r = client.get(f"/web/imagenes/tenis/{entrada['f']}")
    assert r.status_code == 200 and r.headers["content-type"] in ("image/webp", "image/png")
    assert all(k == k.lower() and k == k.strip() for k in bloque)


def test_tenis_sofascore_duplicados_son_lista_con_archivos_distintos():
    dups = {k: v for k, v in manifest()["tenis_sofascore"].items() if isinstance(v, list)}
    assert "coleman wong" in dups
    for v in dups.values():
        assert len({e["f"] for e in v}) == len(v) and len({e["id"] for e in v}) == len(v)


def test_construir_ignora_sin_archivo_y_normaliza_nombre():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "imagenes"))
    import tenistas_sofascore as t
    filas = [{"id": 1, "nombre": "Novak Đoković", "archivo": "a.webp", "pais_codigo": "RS", "genero": "M", "posicion": 1},
             {"id": 2, "nombre": "Sin Foto", "archivo": "b.webp"}]
    bloque, copias = t.construir(filas, lambda f: "webp" if f == "a.webp" else None)
    assert list(bloque) == ["novak đokovic"]
    assert t.extension(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0])) == "png"
    assert t.extension(b"abcd") is None
    assert copias == [("a.webp", next(iter(bloque.values()))["f"])]
