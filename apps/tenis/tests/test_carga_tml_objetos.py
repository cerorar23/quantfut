"""Carga TML: el almacén y el recibo admiten el original CSV comprimido (.csv.gz) y no cambian el .json.gz."""
import gzip
from datetime import datetime, timezone

from tenis.almacen import guardar_objeto, leer_objeto
from tenis.recibo import nuevo_recibo

CUERPO = b"tourney_id,score\n2025-9900,6-3 6-4\n"


def test_carga_tml_csv_gz_ruta_y_lectura(tmp_path):
    sha, ruta, creado = guardar_objeto(tmp_path, CUERPO, ".csv.gz")
    assert creado is True and ruta == f"objetos/{sha[:2]}/{sha}.csv.gz"
    assert (tmp_path / ruta).read_bytes() == gzip.compress(CUERPO, mtime=0)
    assert leer_objeto(tmp_path, sha, ".csv.gz") == CUERPO


def test_carga_tml_recibo_csv_gz_cumple_la_ruta_de_la_base(tmp_path):
    r = nuevo_recibo(tmp_path, fuente="tml", recurso="2025.csv", parametros={},
                     recibido_en=datetime(2026, 11, 2, tzinfo=timezone.utc), cuerpo=CUERPO, retro=True,
                     extension=".csv.gz")
    assert r.ruta_objeto == f"objetos/{r.sha256[:2]}/{r.sha256}.csv.gz" and r.retro is True


def test_carga_tml_json_gz_sigue_siendo_el_defecto(tmp_path):
    sha, ruta, _ = guardar_objeto(tmp_path, b'{"a": 1}')
    assert ruta.endswith(".json.gz") and leer_objeto(tmp_path, sha) == b'{"a": 1}'
