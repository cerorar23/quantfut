"""
Verificación del backfill histórico de football-data.co.uk.

Existe por un fallo mudo real: las tres ligas latinoamericanas (Liga MX,
Argentina, Brasil) viven en el formato "extra", que usa OTROS nombres de
columna y escribe la temporada como '2025/2026'. El código las leía con los
nombres del formato principal y filtraba buscando '2526', así que cargaba
CERO partidos en las tres, sin dar ningún error y sin que nada lo notara.

No se toca la red aquí: se prueban el mapeo de columnas y la conversión de
etiqueta de temporada, que es donde estaba el fallo.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from qf.ingest.history_fd import (
    COLS_EXTRA,
    COLS_MAIN,
    _ingest_rows,
    _parse_date,
    default_seasons,
    season_labels_extra,
)


# ---------------------------------------------------------------------------
# Etiqueta de temporada
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("corta,larga", [
    ("2526", "2025/2026"),
    ("1415", "2014/2015"),
    ("1920", "2019/2020"),
    ("2425", "2024/2025"),
])
def test_acepta_la_forma_de_temporada_europea(corta, larga):
    assert larga in season_labels_extra(corta)


@pytest.mark.parametrize("corta,anio", [
    ("2223", "2022"),
    ("2526", "2025"),
    ("1415", "2014"),
])
def test_acepta_la_forma_de_ano_natural(corta, anio):
    """
    Brasil siempre, y Argentina desde que cambió de formato, escriben la
    temporada como un año suelto. Aceptar solo la forma con barra dejaba esas
    ligas a cero (Brasil) o a medias (Argentina) sin ningún aviso.
    """
    assert anio in season_labels_extra(corta)


def test_las_etiquetas_casan_con_las_reales_de_los_csv():
    # MEX.csv / ARG.csv antiguos
    for etiqueta in ["2019/2020", "2022/2023", "2025/2026"]:
        corta = f"{etiqueta[2:4]}{etiqueta[7:9]}"
        assert etiqueta in season_labels_extra(corta)
    # BRA.csv y ARG.csv modernos
    for etiqueta in ["2022", "2023", "2024", "2025"]:
        corta = f"{etiqueta[2:4]}{int(etiqueta[2:4]) + 1:02d}"
        assert etiqueta in season_labels_extra(corta)
    # La comprobación que demuestra el bug original:
    assert "2526" not in "2025/2026"


# ---------------------------------------------------------------------------
# Mapeo de columnas
# ---------------------------------------------------------------------------

def test_los_dos_formatos_usan_columnas_distintas():
    assert COLS_MAIN["home"] == "HomeTeam"
    assert COLS_EXTRA["home"] == "Home"
    assert COLS_MAIN["hg"] == "FTHG"
    assert COLS_EXTRA["hg"] == "HG"
    assert COLS_MAIN["home"] != COLS_EXTRA["home"]


def test_el_formato_extra_declara_ausentes_las_columnas_que_no_tiene():
    """
    El extra no trae tiros, córners ni goles al descanso. Deben ser None
    explícito, no el nombre del principal: leerlos con el nombre equivocado es
    lo que vaciaba la carga entera.
    """
    for key in ("hg_ht", "ag_ht", "hs", "as", "hst", "ast", "hc", "ac"):
        assert COLS_EXTRA[key] is None, f"{key} debería ser None en el extra"
        assert COLS_MAIN[key] is not None


def test_las_columnas_del_extra_existen_en_una_fila_real():
    """Fila con la forma exacta que devuelve MEX.csv."""
    fila = pd.Series({
        "Country": "Mexico", "League": "Liga MX", "Season": "2025/2026",
        "Date": "12/07/2025", "Time": "19:00", "Home": "America",
        "Away": "Cruz Azul", "HG": 2.0, "AG": 1.0, "Res": "H",
        "PSCH": 2.1, "PSCD": 3.4, "PSCA": 3.6,
    })
    assert isinstance(fila.get(COLS_EXTRA["home"]), str)
    assert isinstance(fila.get(COLS_EXTRA["away"]), str)
    assert pd.notna(fila.get(COLS_EXTRA["hg"]))
    # Con el mapeo del formato principal, todo sale vacío:
    assert fila.get(COLS_MAIN["home"]) is None
    assert fila.get(COLS_MAIN["hg"]) is None


def test_la_fecha_del_extra_se_parsea():
    fila = pd.Series({"Date": "12/07/2025", "Time": "19:00"})
    ko = _parse_date(fila)
    assert ko is not None
    assert (ko.year, ko.month, ko.day, ko.hour) == (2025, 7, 12, 19)
    assert ko.tzinfo is not None


def test_fecha_sin_hora_cae_a_las_19_utc():
    ko = _parse_date(pd.Series({"Date": "12/07/2025", "Time": ""}))
    assert ko is not None and ko.hour == 19


def test_fecha_invalida_devuelve_none():
    assert _parse_date(pd.Series({"Date": "no es fecha", "Time": ""})) is None


# ---------------------------------------------------------------------------
# Temporada en curso y recargas (fallo real, 2026-09-24)
# ---------------------------------------------------------------------------
#
# `backfill()` tenía el rango fijo 2014..2025: la temporada 2026/27 no se
# cargaba nunca, y como `fixtures` solo crea partidos futuros y `results` solo
# cierra las últimas 72 h, lo jugado antes del primer calendario (Premier,
# LaLiga, Serie A, Eredivisie, Liga MX, Brasil, Argentina) no existía.

def test_el_backfill_por_defecto_llega_a_la_temporada_en_curso():
    septiembre = datetime(2026, 9, 24, tzinfo=timezone.utc)
    assert default_seasons(septiembre)[-1] == "2627"
    assert default_seasons(septiembre)[0] == "1415"


def test_en_primavera_incluye_la_temporada_de_ano_natural_que_ya_empezo():
    """
    En mayo de 2026 la temporada europea en curso es 2025/26, pero Brasil y
    Argentina ya juegan la de 2026, que el formato extra etiqueta '2026' y
    solo casa con '2627'.
    """
    mayo = datetime(2026, 5, 10, tzinfo=timezone.utc)
    assert "2026" in season_labels_extra(default_seasons(mayo)[-1])


def _fila_extra(home="America", away="Cruz Azul"):
    return pd.DataFrame([{
        "Season": "2026/2027", "Date": "20/09/2026", "Time": "02:00",
        "Home": home, "Away": away, "HG": 2.0, "AG": 1.0,
        "PSCH": 2.1, "PSCD": 3.4, "PSCA": 3.6,
    }])


@pytest.fixture
def base_falsa(monkeypatch):
    """Sustituye la base por un registro de sentencias; `existe` decide si ya
    hay un partido equivalente en `matches`."""
    import qf.ingest.history_fd as hfd

    estado = {"existe": False, "sentencias": []}
    monkeypatch.setattr(hfd, "_ensure_team", lambda league, raw: {"America": 1, "Cruz Azul": 2}[raw])
    monkeypatch.setattr(hfd, "query_one",
                        lambda sql, params=None: {"x": 1} if estado["existe"] else None)
    monkeypatch.setattr(hfd, "execute",
                        lambda sql, params=None: estado["sentencias"].append(sql) or 1)
    return estado


def test_no_duplica_un_partido_que_ya_creo_el_calendario(base_falsa):
    """
    API-Football etiqueta la temporada distinto ('2026A', '2026') y escribe
    otros nombres: el match_id del histórico no coincidiría y el partido
    quedaría dos veces, con sus cuotas de cierre duplicadas para siempre
    (odds_snapshots no admite DELETE).
    """
    base_falsa["existe"] = True
    assert _ingest_rows("mx.liga_mx", "2627", _fila_extra(), COLS_EXTRA) == 0
    assert base_falsa["sentencias"] == []


def test_recargar_una_temporada_no_reinserta_sus_cuotas(base_falsa):
    base_falsa["existe"] = True   # el propio partido del histórico ya está
    _ingest_rows("mx.liga_mx", "2627", _fila_extra(), COLS_EXTRA)
    assert not any("odds_snapshots" in s for s in base_falsa["sentencias"])


def test_un_partido_nuevo_se_inserta_con_su_cierre(base_falsa):
    assert _ingest_rows("mx.liga_mx", "2627", _fila_extra(), COLS_EXTRA) == 1
    assert sum("INSERT INTO matches" in s for s in base_falsa["sentencias"]) == 1
    assert sum("odds_snapshots" in s for s in base_falsa["sentencias"]) == 3


def _csv(**extra):
    base = {"Date": ["20/09/2025"], "Home": ["A"], "Away": ["B"], "PSCH": [2.1], "PSCD": [3.3], "PSCA": [3.6]}
    base.update({k: [v] for k, v in extra.items()})
    return pd.DataFrame(base)


def test_ternas_pinnacle_toma_la_terna_completa():
    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    t = ternas_pinnacle(_csv(), COLS_EXTRA, datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert len(t) == 1 and t[0]["home"] == "A" and t[0]["away"] == "B"
    assert t[0]["price"] == {"home": 2.1, "draw": 3.3, "away": 3.6}
    assert t[0]["ko"].year == 2025


def test_ternas_pinnacle_descarta_cuotas_invalidas_o_incompletas():
    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    desde = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for malo in (dict(PSCD=1.0), dict(PSCH=float("nan")), dict(PSCA=float("inf")), dict(PSCH=-3.0)):
        assert ternas_pinnacle(_csv(**malo), COLS_EXTRA, desde) == []
    assert ternas_pinnacle(_csv().drop(columns=["PSCA"]), COLS_EXTRA, desde) == []


def test_ternas_pinnacle_respeta_el_desde():
    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    assert ternas_pinnacle(_csv(), COLS_EXTRA, datetime(2026, 1, 1, tzinfo=timezone.utc)) == []


def test_completar_cierres_usa_el_csv_correcto_por_formato_y_es_ensayo_por_defecto(monkeypatch):
    from qf.ingest import history_fd as h

    pedidos, llamadas = [], []
    csv_extra = pd.DataFrame({"Date": ["20/09/2025"], "Home": ["A"], "Away": ["B"],
                              "PSCH": [2.1], "PSCD": [3.3], "PSCA": [3.6]})
    csv_main = pd.DataFrame({"Date": ["20/09/2025"], "HomeTeam": ["C"], "AwayTeam": ["D"],
                             "PSCH": [1.9], "PSCD": [3.5], "PSCA": [4.0]})
    monkeypatch.setattr(h, "_fetch_csv", lambda url: pedidos.append(url) or (
        csv_extra if "/new/" in url else csv_main))
    monkeypatch.setattr(h, "_ligas_con_csv", lambda ligas: [
        {"league_id": "mx.liga_mx", "fd_code": "MEX", "fd_extra": True},
        {"league_id": "es.laliga", "fd_code": "SP1", "fd_extra": False}])

    class Con:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("qf.db.conn", lambda: Con())
    monkeypatch.setattr(h, "cargar_ternas", lambda c, liga, ternas, resolver, aplicar:
                        llamadas.append((liga, [t["home"] for t in ternas], aplicar)) or {"ok": 1})
    out = h.completar_cierres(seasons=["2526"])
    assert any(u.endswith("/new/MEX.csv") for u in pedidos)
    assert any(u.endswith("/mmz4281/2526/SP1.csv") for u in pedidos)
    assert out == {"mx.liga_mx": {"ok": 1}, "es.laliga": {"ok": 1}}
    assert llamadas == [("mx.liga_mx", ["A"], False), ("es.laliga", ["C"], False)]
    h.completar_cierres(seasons=["2526"], aplicar=True)
    assert llamadas[-1][2] is True


def test_el_resolutor_de_cierres_solo_lee_y_exige_coincidencia_exacta(monkeypatch):
    from qf.ingest import history_fd as h

    escrituras = []
    monkeypatch.setattr(h, "match_team", lambda raw, src, liga: (7, "x", 100.0) if raw == "Exacto" else (7, "x", 92.0))
    monkeypatch.setattr(h, "query_one", lambda sql, params=(): {"canonical_name": "Canonico"})
    monkeypatch.setattr(h, "execute", lambda *a, **k: escrituras.append(a))
    assert h._resolver_lectura("Exacto", "L") == "Canonico"
    assert h._resolver_lectura("Difuso", "L") is None
    assert escrituras == []
