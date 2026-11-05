"""Reglas puras de la exportación PIT: superficie del modelo, formato del set decisivo, unión de intervalos de
visibilidad y fusión TML–SofaScore sobre tablas pequeñas (sin base de datos)."""
import pandas as pd
import pytest

from tenis.datos import reglas
from tenis.datos.fusion import fusionar
from tenis.datos.visibilidad import _union_intervalos


def ts(x):
    return pd.Timestamp(x, tz="UTC")


@pytest.mark.parametrize("sup, indoor, esperado", [
    ("clay", True, ("Clay", True, None)),           # tierra bajo techo: Clay con indoor
    ("clay", None, ("Clay", None, "indoor_desconocido")),
    ("hard", True, ("Indoor", True, None)),
    ("hard", False, ("Hard", False, None)),
    ("hard", None, ("Hard", None, "indoor_desconocido")),
    ("grass", False, ("Grass", False, None)),
    ("carpet", None, ("Indoor", True, "moqueta_indoor_supuesto")),
    ("carpet", False, (None, False, "moqueta_exterior")),
    (None, None, (None, None, "superficie_desconocida")),
])
def test_superficie_modelo(sup, indoor, esperado):
    assert reglas.superficie_modelo(sup, indoor) == esperado


@pytest.mark.parametrize("cat, nombre, anio, ronda, formato", [
    ("GS", "Australian Open", 2018, "R128", "ventaja"),
    ("GS", "Australian Open", 2019, "F", "tiebreak_10"),
    ("GS", "Roland Garros", 2021, "F", "ventaja"),
    ("GS", "Roland Garros", 2022, "R32", "tiebreak_10"),
    ("GS", "Wimbledon", 2018, "F", "ventaja"),
    ("GS", "Wimbledon", 2019, "F", "desconocido"),     # tiebreak a 7 en 12-12: fuera del catálogo
    ("GS", "Us Open", 2021, "F", "tiebreak_7"),
    ("GS", "US Open", 2023, "F", "tiebreak_10"),
    ("GS", "Us Open", 2015, "Q2", "desconocido"),      # previas antes de 2022: sin regla verificada
    ("GS", "Us Open", 2024, "QL", "tiebreak_10"),
    ("GS", "Torneo Raro", 2015, "F", "desconocido"),
    ("M1000", "Miami Masters", 2010, "F", "tiebreak_7"),
    ("Challenger", "Bergamo CH", 2012, "F", "tiebreak_7"),
    ("Finales", "Tour Finals", 2015, "F", "tiebreak_7"),
    ("Finales", "NextGen Finals", 2019, "F", "desconocido"),
    ("equipos", "Laver Cup", 2019, "RR", "supertiebreak_10"),
    ("equipos", "Davis Cup WG", 2010, "RR", "desconocido"),
    ("JJOO", "Olympics", 2012, "F", "desconocido"),
    (None, "Sin nivel", 2012, "F", "tiebreak_7"),        # categoría vacía en TML (nivel cambió entre años)
    (None, "Seoul Olympics", 2012, "F", "desconocido"),
    (None, "Davis Cup WG", 2012, "RR", "desconocido"),
    (None, "Australian Championships", 2012, "F", "ventaja"),
    ("GS", "Australian Championships", 2020, "F", "tiebreak_10"),
    (None, "Sin nivel", 1985, "F", "desconocido"),
    ("250", "Antiguo", 1985, "F", "desconocido"),
])
def test_formato_decisivo(cat, nombre, anio, ronda, formato):
    assert reglas.formato_decisivo(cat, nombre, anio, ronda)[0] == formato
    assert reglas.formato_decisivo(cat, nombre, anio, ronda)[0] in reglas.FORMATOS


def test_union_intervalos():
    a, b, c = ts("2024-01-01"), ts("2024-01-05"), ts("2024-01-09")
    assert _union_intervalos([(a, None)]) == (a, True)
    assert _union_intervalos([(a, b), (b, None)]) == (a, True)
    assert _union_intervalos([]) == (pd.NaT, True) or _union_intervalos([])[1]
    lim, mono = _union_intervalos([(a, b), (c, None)])        # hueco: deja de verse y vuelve
    assert not mono and pd.isna(lim)
    lim, mono = _union_intervalos([(a, b)])                    # visible y luego nunca más
    assert not mono


def _tml(pid, ed, ronda, j1, j2, ini, dias=7):
    return {"partido_id": pid, "edicion_id": ed, "ronda": ronda, "jugador_1": j1, "jugador_2": j2,
            "ventana_ini": ts(ini), "ventana_fin": ts(ini) + pd.Timedelta(days=dias)}


def _sofa(pid, ed, ronda, j1, j2, inicio):
    return {"partido_id": pid, "edicion_id": ed, "ronda": ronda, "jugador_1": j1, "jugador_2": j2, "inicio": ts(inicio)}


def test_fusion_par_repetido_en_torneos_consecutivos():
    """Misma pareja y ronda en dos semanas seguidas: cada fila de SofaScore va con su semana (la ventana lo impide)."""
    tml = pd.DataFrame([_tml(1, 10, "R32", 5, 6, "2024-03-04"), _tml(2, 11, "R32", 5, 6, "2024-03-11")])
    sofa = pd.DataFrame([_sofa(101, 20, "R32", 5, 6, "2024-03-05 12:00"), _sofa(102, 21, "R32", 5, 6, "2024-03-12 12:00")])
    pares, cont = fusionar(tml, sofa)
    assert set(zip(pares["pid_tml"], pares["pid_sofa"])) == {(1, 101), (2, 102)}
    # Falta TML de la segunda semana: la fila de SofaScore NO se fusiona con la de la semana anterior.
    pares, cont = fusionar(tml.iloc[:1], sofa)
    assert set(zip(pares["pid_tml"], pares["pid_sofa"])) == {(1, 101)}


def test_fusion_ambigua_no_se_fusiona():
    tml = pd.DataFrame([_tml(1, 10, "R32", 5, 6, "2024-03-04", 14), _tml(2, 11, "R32", 5, 6, "2024-03-11")])
    sofa = pd.DataFrame([_sofa(101, 20, "R32", 5, 6, "2024-03-12 12:00")])   # cae en las dos ventanas
    pares, cont = fusionar(tml, sofa)
    assert pares.empty and cont["ambiguos_estricta"] > 0


def test_fusion_edicion_desalineada_y_ql():
    """TML fecha la edición en la semana del clasificatorio: el cuadro cae fuera de su ventana. Las fusiones estrictas
    del clasificatorio enlazan las ediciones y el resto se fusiona por enlace; QL ↔ ronda Q más alta de TML."""
    tml = pd.DataFrame([_tml(1, 10, "Q1", 1, 2, "2024-03-04"), _tml(2, 10, "Q2", 1, 3, "2024-03-04"),
                        _tml(3, 10, "R32", 1, 4, "2024-03-04"), _tml(4, 10, "F", 1, 5, "2024-03-04")])
    sofa = pd.DataFrame([_sofa(101, 20, "Q1", 1, 2, "2024-03-08 10:00"), _sofa(102, 20, "QL", 1, 3, "2024-03-09 10:00"),
                         _sofa(103, 20, "R32", 1, 4, "2024-03-12 10:00"), _sofa(104, 20, "F", 1, 5, "2024-03-17 10:00")])
    pares, cont = fusionar(tml, sofa)
    assert dict(zip(pares["pid_tml"], pares["metodo"])) == {1: "estricta", 2: "estricta", 3: "edicion_enlazada",
                                                            4: "edicion_enlazada"}
    assert dict(zip(pares["pid_tml"], pares["pid_sofa"])) == {1: 101, 2: 102, 3: 103, 4: 104}
    # Sin ninguna fusión estricta no hay enlace: nada se fusiona fuera de la ventana.
    pares, _ = fusionar(tml.iloc[2:], sofa.iloc[2:])
    assert pares.empty
