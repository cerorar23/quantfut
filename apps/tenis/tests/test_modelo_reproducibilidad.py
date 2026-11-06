"""REPRODUCIBILIDAD: dos corridas del filtro sobre datos reales dan el mismo sha256 de predicciones; la huella del
fichero de hiperparámetros detecta cualquier alteración."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from tenis.modelo import datos as dm
from tenis.modelo import hiperparametros as hp
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import psi_prueba, tablas_prueba


def sha(d, s) -> str:
    df = pd.DataFrame({"k": d.p.partido_key, "pi": s.pi, "rho": s.rho, "v": s.var_rho, "f1": s.f1, "f2": s.f2})
    return hashlib.sha256(df.to_csv(index=False, float_format="%.12g").encode()).hexdigest()


def test_dos_corridas_mismo_sha256():
    if not (dm.RUTA_EXPORT / "partidos.parquet").exists():
        pytest.skip("exportación PIT no disponible")
    p, e = dm.cargar_export(hasta=2007)
    d1 = dm.preparar(p, e, "wta", 2007)
    d2 = dm.preparar(p.sample(frac=1.0, random_state=3), e.sample(frac=1.0, random_state=4), "wta", 2007)
    a, b = sha(d1, filtrar(d1, psi_prueba(), tablas_prueba())), sha(d2, filtrar(d2, psi_prueba(), tablas_prueba()))
    assert a == b


def test_huella_de_hiperparametros():
    ruta = dm.RUTA_EXPORT.parent / "modelo_s3" / "prueba_huella_tests.json"
    contenido = {"circuitos": {"atp": {"psi_r": psi_prueba().como_dict()}}, "x": [1.0, 2.5]}
    sha1 = hp.escribir(ruta, contenido)
    assert hp.leer(ruta) == json.loads(json.dumps(contenido)) and hp.huella(contenido) == sha1
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["x"][0] = 1.0001
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ValueError):
        hp.leer(ruta)
    ruta.unlink()
    assert np.isclose(hp.psi_desde_vector([0.0] * 13, {"sigma_eps": 0.2, "rho_eps": -0.4, "lbar": [0.5] * 4,
                                                        "lam": 0.75, "f90": 100.0}).tau_theta, 1.0)
