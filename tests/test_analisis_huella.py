"""La huella del resumen ignora las cifras vivas (`datos`) y sí cambia con el pronóstico sellado."""
from qf.api import analisis_futbol as ia


def _hechos(datos, prob=80):
    return {"partido": "A vs B", "pronostico": "Más de 2.5", "mercado": "total", "probabilidad_pct": prob,
            "datos": datos, "significado": "Más de 2,5 goles"}


def test_cifras_vivas_no_cambian_la_huella():
    a = ia._hash(_hechos([{"id": "forma", "valor": 3}]))
    b = ia._hash(_hechos([{"id": "forma", "valor": 4}]))
    assert a == b


def test_el_pronostico_sellado_si_cambia_la_huella():
    assert ia._hash(_hechos([], prob=80)) != ia._hash(_hechos([], prob=81))
    assert ia._hash(_hechos([])) != ia._hash({**_hechos([]), "pronostico": "Menos de 2.5"})


def test_resumen_para_busca_con_la_huella_estable(monkeypatch):
    vistos = []
    monkeypatch.setattr(ia, "_leer", lambda m, c, h: vistos.append(h) or {"es": "texto"})
    monkeypatch.setattr(ia, "_config", lambda: None)
    ia.resumen_para("1", "tenis|x", _hechos([{"v": 1}]))
    ia.resumen_para("1", "tenis|x", _hechos([{"v": 2}]))
    assert vistos[0] == vistos[1]
