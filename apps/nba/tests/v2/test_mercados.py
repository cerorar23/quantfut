from datetime import date, datetime, timedelta, UTC
from statistics import NormalDist

import numpy as np
import psycopg
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from scipy.stats import poisson

from nba.api import app as api
from nba.api import mercados
from nba.v2 import identidad, motor_equipo, pit, sellado
from nba.v2.carga import DatoNuevo, guardar_datos
from nba.v2.sellado import PronosticoNuevo
from test_sellado_pit import liga


def equipo_dist(mu=(112.0, 108.0), sigma=12.0):
    """Distribución de equipo válida y monótona alrededor de los puntos esperados."""
    def q(media):
        return [NormalDist(media, sigma).inv_cdf(i * 0.005) for i in range(1, 200)]
    local, visit = mu
    return {"p_local": 0.55, "mu": [local, visit], "paso_cuantil": 0.005,
            "margen": q(local - visit), "total": q(local + visit),
            "puntos_local": q(local), "puntos_visitante": q(visit)}


def jugador_dist(media=27.5, techo=70, p_juega=0.95):
    pmf = poisson.pmf(np.arange(techo + 1), media)
    pmf = pmf / pmf.sum()
    acum = np.cumsum(pmf)
    return {"pmf": [round(float(x), 6) for x in pmf], "media": round(float(media), 4),
            "p10": int(np.searchsorted(acum, 0.10)), "p50": int(np.searchsorted(acum, 0.50)),
            "p90": int(np.searchsorted(acum, 0.90)), "p_juega": p_juega, "minutos_esperados": 34.0}


def cotizar(db, partido, mercado, linea, casa, lado, cuota, recibido, entidad=None, fase="pre", periodo=0):
    db.execute(
        "INSERT INTO nba.cuota (partido_id, fuente, casa, mercado, periodo, entidad_id, linea, lado, cuota, contrato_id, "
        "fase, recibido_en) VALUES (%s,'propline',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (partido, casa, mercado, periodo, entidad, linea, lado, cuota, f"{mercado}|{linea}|{casa}|{lado}", fase, recibido))


@pytest.fixture
def partido_con_mercados(base_migrada_dsn):
    """Un partido con sello de equipo y de un jugador, y cuotas de dos casas antes del sello."""
    with psycopg.connect(base_migrada_dsn) as db:
        ids, partidos = liga(db, 25)
        db.commit()
        pid, fecha, local, visit = partidos[15]
        corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
        inst = pit.instantanea(db, pid, corte)
        esc, dist = motor_equipo.pronosticar(inst)
        sellado.sellar(db, PronosticoNuevo(pid, "equipo", motor_equipo.VERSION_MODELO, inst.version_datos, corte, esc, dist))
        jugador = identidad.jugador(db, "nba_oficial", "2544", "LeBron James")
        sellado.sellar(db, PronosticoNuevo(pid, "jugador:puntos", "props-t", "d" * 64, corte,
                                           {"nombre": "LeBron James", "lado": "local"},
                                           jugador_dist(), entidad_id=jugador))
        for i, (previo, fecha_previa, _, _) in enumerate(partidos[12:15]):
            guardar_datos(db, [DatoNuevo(partido_id=previo, entidad_id=jugador, metrica="puntos", fase="final",
                                         fuente="nba_oficial", recibido_en=datetime(2026, 11, 2, tzinfo=UTC),
                                         valor=20.0 + i, pit="reconstruido")])
        antes = corte - timedelta(minutes=30)
        despues = corte + timedelta(minutes=5)
        # total del partido: pinnacle y fanduel, ambos con los dos lados
        cotizar(db, pid, "totals", 200.5, "pinnacle", "over", 1.95, antes)
        cotizar(db, pid, "totals", 200.5, "pinnacle", "under", 1.90, antes)
        cotizar(db, pid, "totals", 200.5, "fanduel", "over", 1.91, antes)
        cotizar(db, pid, "totals", 200.5, "fanduel", "under", 1.91, antes)
        # una casa con un solo lado no cuenta
        cotizar(db, pid, "totals", 200.5, "draftkings", "over", 9.99, antes)
        # línea extrema y línea posterior al sello: no deben elegirse
        cotizar(db, pid, "totals", 400.5, "caesars", "over", 9.0, antes)
        cotizar(db, pid, "totals", 400.5, "caesars", "under", 1.01, antes)
        cotizar(db, pid, "totals", 210.5, "caesars", "over", 1.90, despues)
        cotizar(db, pid, "totals", 210.5, "caesars", "under", 1.90, despues)
        # puntos por equipo (local)
        cotizar(db, pid, "team_totals", 100.5, "caesars", "over", 1.88, antes, entidad=ids[local])
        cotizar(db, pid, "team_totals", 100.5, "caesars", "under", 1.92, antes, entidad=ids[local])
        # props de puntos del jugador
        cotizar(db, pid, "player_points", 20.5, "pinnacle", "over", 1.90, antes, entidad=jugador)
        cotizar(db, pid, "player_points", 20.5, "pinnacle", "under", 1.90, antes, entidad=jugador)
        cotizar(db, pid, "player_points", 20.5, "caesars", "over", 1.95, antes, entidad=jugador)
        cotizar(db, pid, "player_points", 20.5, "caesars", "under", 1.85, antes, entidad=jugador)
        db.commit()
    return TestClient(api.crear_app(base_migrada_dsn)), pid, fecha, jugador


def test_lado_y_probabilidad_elige_el_lado_mas_probable():
    assert mercados.lado_y_probabilidad(0.62) == ("over", 0.62)
    assert mercados.lado_y_probabilidad(0.38) == ("under", 0.62)
    assert mercados.lado_y_probabilidad(0.5) is None
    assert mercados.lado_y_probabilidad(1.0) is None and mercados.lado_y_probabilidad(float("nan")) is None
    # Banda publicable: ni una certeza de 0,99 ni un empate disfrazado.
    assert mercados.lado_y_probabilidad(0.99) is None and mercados.lado_y_probabilidad(0.55) is None
    assert mercados.lado_y_probabilidad(0.96) is None


def test_cuota_publicable_descarta_alternativas_lejanas():
    assert mercados._cuota_publicable({"precio": 1.87}) == {"precio": 1.87}
    assert mercados._cuota_publicable({"precio": 26.0}) is None
    assert mercados._cuota_publicable({"precio": 1.01}) is None
    assert mercados._cuota_publicable(None) is None


def test_mejor_cuota_exige_los_dos_lados_y_desempata_por_casa():
    grupo = {"casas": {"pinnacle": {"over": 1.95, "under": 1.90},
                       "fanduel": {"over": 1.95, "under": 1.91},
                       "solo_un_lado": {"over": 3.0}},
             "recibido_en": datetime(2026, 1, 1, tzinfo=UTC)}
    q = mercados.mejor_cuota(grupo)
    assert q["precio"] == 1.95 and q["casa"] == "fanduel" and q["casas"] == 2
    assert mercados.mejor_cuota({"casas": {"x": {"over": 2.0}}, "recibido_en": None}) is None


def test_under_usa_la_cuota_under_y_el_ultimo_precio():
    t=datetime(2026,1,1,tzinfo=UTC)
    filas=[('totals',None,220.5,'under','a',2.5,t),
           ('totals',None,220.5,'under','a',1.8,t+timedelta(minutes=1)),
           ('totals',None,220.5,'over','a',3.0,t),
           ('totals',None,220.5,'under','b',1.9,t),
           ('totals',None,220.5,'over','b',1.4,t)]
    g=mercados.casas_por_linea(filas)[('totals',None,220.5)]
    assert mercados.mejor_cuota(g,'under')['casa']=='b'
    assert mercados.mejor_cuota(g,'under')['precio']==1.9
    assert mercados.mejor_cuota(g,'over')['precio']==3.0


def test_mercados_no_usa_interpolacion_si_existe_masa_exacta():
    d=equipo_dist()
    d['masas']={'total':{'soporte':[200,220,240],'pmf':[.1,.7,.2]}}
    t=datetime(2026,1,1,tzinfo=UTC)
    casas=mercados.casas_por_linea([('totals',None,220.,s,'a',1.9,t) for s in ('over','under')])
    c=mercados.candidatos_equipo('totals','total_partido',d,casas,{})
    assert len(c)==1 and c[0]['lado']=='over' and c[0]['probabilidad']==pytest.approx(2/3,abs=1e-4)


def test_elegir_una_sola_seleccion_determinista():
    filas = [{"probabilidad": 0.61, "linea": 27.5, "lado": "over"}, {"probabilidad": 0.61, "linea": 24.5, "lado": "over"},
             {"probabilidad": 0.58, "linea": 30.5, "lado": "under"}]
    assert mercados.elegir(filas)["linea"] == 24.5
    assert mercados.elegir([]) is None


def test_mercados_del_dia_da_una_seleccion_por_familia(partido_con_mercados):
    c, pid, fecha, jugador = partido_con_mercados
    r = c.get("/nba/v1/mercados", params={"fecha": fecha.isoformat()})
    assert r.status_code == 200
    juego = next(p for p in r.json()["partidos"] if p["id"] == pid)
    familias = juego["familias"]
    assert set(familias) == {"puntos", "total_partido", "puntos_equipo"}
    total = familias["total_partido"]
    assert total["linea"] == 200.5 and total["lado"] in ("over", "under")
    assert 0.5 < total["probabilidad"] < 1
    # gana la mejor cuota de las casas con ambos lados; draftkings queda fuera por cotizar un solo lado
    assert total["cuota"]["precio"] == 1.95 and total["cuota"]["casa"] == "pinnacle"
    assert total["cuota"]["casas"] == 2
    puntos = familias["puntos"]
    assert puntos["jugador"] == "LeBron James" and puntos["jugador_id"] == jugador
    assert puntos["cuota"]["precio"] == 1.95 and puntos["cuota"]["casa"] == "caesars"
    equipo = familias["puntos_equipo"]
    assert equipo["linea"] == 100.5 and equipo["lado_equipo"] == "local"
    # últimos cinco partidos del jugador, solo anteriores a este partido
    assert puntos["ultimos"] == [22.0, 21.0, 20.0]
    assert equipo["ultimos"] == []


def test_sin_cuota_no_hay_familia(partido_con_mercados):
    c, pid, fecha, _ = partido_con_mercados
    familias = c.get("/nba/v1/mercados", params={"fecha": fecha.isoformat()}).json()["partidos"]
    juego = next(p for p in familias if p["id"] == pid)
    assert "rebotes" not in juego["familias"] and "asistencias" not in juego["familias"]


def test_fecha_sin_partidos_y_fecha_invalida(partido_con_mercados):
    c, _, _, _ = partido_con_mercados
    assert c.get("/nba/v1/mercados", params={"fecha": "2030-01-01"}).json()["partidos"] == []
    assert c.get("/nba/v1/mercados", params={"fecha": "no-es-fecha"}).status_code == 422


def test_cuota_posterior_al_sello_no_se_usa(base_migrada_dsn):
    """La cuota de una línea posterior al sello no puede elegirse (sería información del futuro)."""
    with psycopg.connect(base_migrada_dsn) as db:
        ids, partidos = liga(db, 25)
        db.commit()
        pid, fecha, local, visit = partidos[15]
        corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
        sellado.sellar(db, PronosticoNuevo(pid, "equipo", "equipo-t", "d" * 64, corte, {"a": 1}, equipo_dist()))
        cotizar(db, pid, "totals", 200.5, "caesars", "over", 1.90, corte + timedelta(minutes=1))
        cotizar(db, pid, "totals", 200.5, "caesars", "under", 1.90, corte + timedelta(minutes=1))
        db.commit()
        c = TestClient(api.crear_app(base_migrada_dsn))
        juego = next(p for p in c.get("/nba/v1/mercados", params={"fecha": fecha.isoformat()}).json()["partidos"]
                     if p["id"] == pid)
    assert "total_partido" not in juego["familias"]
