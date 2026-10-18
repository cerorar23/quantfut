import math
from datetime import datetime, timedelta, timezone

from qf.ingest.era5_clima import caracteristicas, celda, humedad_relativa, leer_csv

CABECERA = "valid_time,u10,v10,d2m,t2m,tcc,tp,latitude,longitude\n"


def _csv(horas, t=283.15, td=278.15, u=3.0, v=4.0, tcc=0.5, tp=0.0001):
    filas = [f"{h:%Y-%m-%d %H:%M:%S},{u},{v},{td},{t},{tcc},{tp},51.5,0.0" for h in horas]
    return CABECERA + "\n".join(filas) + "\n"


def _horas(desde, n):
    return [desde + timedelta(hours=i) for i in range(n)]


SAQUE = datetime(2026, 3, 1, 15, 30, tzinfo=timezone.utc)
H0 = datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)


def test_celda_y_humedad():
    assert celda(51.555, -0.108) == (51.5, -0.0)
    assert celda(19.3029, -99.1505) == (19.25, -99.25)
    assert humedad_relativa(10.0, 10.0) == 100.0                # punto de rocío = temperatura
    assert 60 < humedad_relativa(10.0, 5.0) < 75                # ~71 %
    assert humedad_relativa(10.0, 40.0) == 100.0                # acotada


def test_caracteristicas_convierte_unidades():
    serie = leer_csv(_csv(_horas(H0 - timedelta(hours=2), 8)))
    x = caracteristicas(serie, SAQUE)
    assert x["temperatura_c"] == 10.0
    assert x["viento_ms"] == 5.0                                 # hipotenusa de 3 y 4
    assert x["nubosidad_pct"] == 50.0
    assert math.isclose(x["precipitacion_mm"], 0.3, abs_tol=1e-6)  # 3 horas × 0,1 mm
    assert 60 < x["humedad_pct"] < 75


def test_cero_lluvia_es_un_dato_real():
    x = caracteristicas(leer_csv(_csv(_horas(H0 - timedelta(hours=2), 8), tp=0.0)), SAQUE)
    assert x["precipitacion_mm"] == 0.0


def test_si_falta_una_hora_no_hay_fila():
    horas = [h for h in _horas(H0 - timedelta(hours=2), 8) if h != H0 + timedelta(hours=3)]
    assert caracteristicas(leer_csv(_csv(horas)), SAQUE) is None
    assert caracteristicas({}, SAQUE) is None


def test_lee_con_ruido_sin_romper():
    texto = CABECERA + "2026-03-01 00:00:00,1,1,270,280,0.5,0.0,51.5,0.0\nbasura\n2026-03-01 01:00:00,1,1,NaN,280,0.5,0,51.5,0.0\n"
    assert list(leer_csv(texto)) == [datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)]


def test_cds_reintenta_un_502_pero_no_un_403():
    import io
    import json
    import urllib.error
    from unittest.mock import patch

    from qf.ingest.era5_clima import Cds

    def http(codigo):
        return urllib.error.HTTPError("https://x", codigo, "e", {}, io.BytesIO(b""))

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, *a):
            return b'{"ok": 1}'

    cds = Cds("token")
    with patch("qf.ingest.era5_clima.urllib.request.urlopen", side_effect=[http(502), Resp()]) as op, \
            patch("qf.ingest.era5_clima.json.load", side_effect=lambda f: {"ok": 1}):
        assert cds._call("https://x", espera_base_s=0) == {"ok": 1}
    assert op.call_count == 2
    with patch("qf.ingest.era5_clima.urllib.request.urlopen", side_effect=http(403)) as op:
        try:
            cds._call("https://x", espera_base_s=0)
            assert False
        except urllib.error.HTTPError:
            pass
    assert op.call_count == 1


def test_incremental_no_reutiliza_un_archivo_que_no_cubre_el_partido_nuevo(tmp_path):
    """El defecto que había: un archivo viejo de la celda hacía creer que ya estaba todo."""
    import gzip
    from unittest.mock import MagicMock

    from qf.ingest import era5_clima as e

    viejo = _csv(_horas(datetime(2026, 3, 1, 0, tzinfo=timezone.utc), 48))
    (tmp_path / "era5_+51.50_+0.000.csv.gz").write_bytes(gzip.compress(viejo.encode()))
    k = (51.5, 0.0)
    nuevo = {"match_id": "n", "stadium_id": 1, "kickoff_utc": datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc)}
    cubierto = {"match_id": "v", "stadium_id": 1, "kickoff_utc": datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)}
    c = MagicMock()
    serie = e._serie_guardada(tmp_path, k)
    guardados, faltan = e.procesar_celda(c, k, [cubierto, nuevo], serie)
    assert [p["match_id"] for p in faltan] == ["n"]           # el nuevo queda pendiente de pedir
    assert e._archivos(tmp_path, k)[0].name == "era5_+51.50_+0.000.csv.gz"
