"""Almacén de originales por contenido y recibos: idempotencia, atomicidad, corrupción y secretos."""
import gzip
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from tenis.almacen import guardar_objeto, leer_objeto
from tenis.recibo import nuevo_recibo

AHORA = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
CUERPO = b'{"partidos": [1, 2, 3]}'


def _archivos(raiz: Path):
    return sorted(p for p in (raiz / "objetos").rglob("*") if p.is_file())


def test_mismo_contenido_dos_veces_deja_un_objeto_y_dos_recepciones(tmp_path):
    sha1, ruta1, creado1 = guardar_objeto(tmp_path, CUERPO)
    sha2, ruta2, creado2 = guardar_objeto(tmp_path, CUERPO)
    assert sha1 == sha2 and ruta1 == ruta2
    assert creado1 is True and creado2 is False
    assert len(_archivos(tmp_path)) == 1
    r1 = nuevo_recibo(tmp_path, fuente="tml", recurso="x.csv", parametros={"anio": 2025},
                      recibido_en=AHORA, cuerpo=CUERPO, retro=True)
    r2 = nuevo_recibo(tmp_path, fuente="tml", recurso="x.csv", parametros={"anio": 2025},
                      recibido_en=AHORA.replace(hour=10), cuerpo=CUERPO, retro=True)
    assert r1.sha256 == r2.sha256 == sha1 and r1.recibido_en != r2.recibido_en
    assert len(_archivos(tmp_path)) == 1


def test_ruta_y_gzip_sin_marca_de_tiempo(tmp_path):
    sha, ruta, _ = guardar_objeto(tmp_path, CUERPO)
    assert ruta == f"objetos/{sha[:2]}/{sha}.json.gz"
    assert (tmp_path / ruta).read_bytes() == gzip.compress(CUERPO, mtime=0)


def test_proceso_interrumpido_antes_del_enlace_no_deja_objeto_truncado(tmp_path, monkeypatch):
    def interrumpido(origen, destino):
        raise RuntimeError("corte simulado antes de publicar")
    monkeypatch.setattr(os, "link", interrumpido)
    with pytest.raises(RuntimeError):
        guardar_objeto(tmp_path, CUERPO)
    import hashlib
    sha = hashlib.sha256(CUERPO).hexdigest()
    assert not (tmp_path / f"objetos/{sha[:2]}/{sha}.json.gz").exists()
    with pytest.raises(FileNotFoundError):
        leer_objeto(tmp_path, sha)
    assert not [p for p in _archivos(tmp_path) if p.name.endswith(".json.gz")]


def test_objeto_truncado_en_disco_se_detecta_al_leer(tmp_path):
    sha, ruta, _ = guardar_objeto(tmp_path, CUERPO)
    destino = tmp_path / ruta
    destino.write_bytes(destino.read_bytes()[:10])
    with pytest.raises(ValueError, match="objeto corrupto"):
        leer_objeto(tmp_path, sha)


def test_objeto_corrupto_en_disco_se_detecta_al_escribir_de_nuevo(tmp_path):
    sha, ruta, _ = guardar_objeto(tmp_path, CUERPO)
    (tmp_path / ruta).write_bytes(gzip.compress(b"otro contenido", mtime=0))
    with pytest.raises(ValueError, match="objeto corrupto"):
        guardar_objeto(tmp_path, CUERPO)


def test_objeto_que_no_es_gzip_se_detecta_al_leer(tmp_path):
    sha, ruta, _ = guardar_objeto(tmp_path, CUERPO)
    (tmp_path / ruta).write_bytes(b"no soy gzip")
    with pytest.raises(ValueError, match="objeto corrupto"):
        leer_objeto(tmp_path, sha)


def test_leer_verifica_el_contenido_original(tmp_path):
    sha, _, _ = guardar_objeto(tmp_path, CUERPO)
    assert leer_objeto(tmp_path, sha) == CUERPO


@pytest.mark.parametrize("nombre", ["api_key", "apiKey", "Token", "client_secret", "PASSWORD", "x-auth"])
def test_parametros_con_nombre_de_secreto_se_rechazan_sin_escribir(tmp_path, nombre):
    with pytest.raises(ValueError):
        nuevo_recibo(tmp_path, fuente="propline", recurso="odds", parametros={nombre: "abc"},
                     recibido_en=AHORA, cuerpo=CUERPO, retro=False)
    assert not (tmp_path / "objetos").exists()


def test_recibo_con_fecha_naive_se_rechaza(tmp_path):
    with pytest.raises(ValidationError):
        nuevo_recibo(tmp_path, fuente="tml", recurso="x", parametros={}, recibido_en=datetime(2026, 1, 1),
                     cuerpo=CUERPO, retro=True)


def test_recibo_guarda_fuente_tamano_retro_y_hash(tmp_path):
    r = nuevo_recibo(tmp_path, fuente="sofascore", recurso="/event/1", parametros={"liga": "atp", "p": 2.5, "x": None},
                     recibido_en=AHORA, cuerpo=CUERPO, retro=False, estado_http=200)
    assert r.bytes == len(CUERPO) and r.retro is False and r.estado_http == 200
    assert len(r.sha256) == 64 and r.ruta_objeto.endswith(f"{r.sha256}.json.gz")
    assert leer_objeto(tmp_path, r.sha256) == CUERPO

