import json
from unittest.mock import patch

import pytest

from qf.ingest import estadios_altitud as ea


def test_altitud_valida_descarta_lo_imposible_y_no_confunde_cero():
    assert ea.altitud_valida(2281.4) == 2281.4
    assert ea.altitud_valida(0) == 0.0          # el nivel del mar es un dato real
    assert ea.altitud_valida(-12) == -12.0      # bajo el nivel del mar también
    for malo in (None, "2000", True, float("nan"), float("inf"), 9000, -1000):
        assert ea.altitud_valida(malo) is None


class _Resp:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return json.dumps(self.cuerpo).encode()


def test_pedir_mantiene_el_orden_y_marca_los_puntos_sin_elevacion():
    cuerpo = {"status": "OK", "results": [{"elevation": 2281.0}, {"elevation": None}, {"elevation": 12.5}]}
    with patch("qf.ingest.estadios_altitud.urllib.request.urlopen", return_value=_Resp(cuerpo)), \
            patch("qf.ingest.estadios_altitud.json.load", side_effect=lambda f: cuerpo):
        assert ea.pedir([(19.3, -99.1), (0.0, 0.0), (53.4, -2.9)]) == [2281.0, None, 12.5]


def test_pedir_rechaza_una_respuesta_de_otro_tamano():
    cuerpo = {"status": "OK", "results": [{"elevation": 1.0}]}
    with patch("qf.ingest.estadios_altitud.urllib.request.urlopen", return_value=_Resp(cuerpo)), \
            patch("qf.ingest.estadios_altitud.json.load", side_effect=lambda f: cuerpo):
        with pytest.raises(ValueError):
            ea.pedir([(1.0, 1.0), (2.0, 2.0)])
