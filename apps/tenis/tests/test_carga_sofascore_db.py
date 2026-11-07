"""Carga de SofaScore contra Postgres en esquema aislado, con eventos sintéticos gzip.

Cubre: recibos retro, orientación canónica (jugador_1 < jugador_2 por id), idempotencia (0 filas nuevas al repetir),
duplicados, rechazos con motivo, conflictos de edición, PIT (corte posterior a 12 h antes del inicio y anterior al fin
estimado; corte de 2023 sobre datos cargados en 2026) y que ningún campo prohibido llega a la evidencia.
"""
import csv
import gzip
import hashlib
import json
from datetime import datetime, timezone

import psycopg
import pytest

from tenis.carga.sofascore_carga import Entrada, cargar
from test_carga_sofascore_parseo import evento, estadistica_json, pbp_desde, sets_de

OBSERVADO = datetime(2026, 11, 4, 21, 0, tzinfo=timezone.utc)
TABLAS = ["recibo", "jugador", "jugador_asercion", "jugador_alias", "torneo", "edicion", "partido", "programa",
          "resultado", "estadistica", "juego_pbp"]
INICIO_2023 = int(datetime(2023, 6, 1, 13, 0, tzinfo=timezone.utc).timestamp())


class Lote:
    """Constructor de un lote de eventos: guarda los ficheros comprimidos y devuelve las entradas del índice."""

    def __init__(self):
        self.almacen: dict[str, bytes] = {}
        self.entradas: list[Entrada] = []

    def add(self, ev: dict, est: dict | None = None, pbp: dict | None = None, observado=OBSERVADO,
            sha_indice: bool = True, evento_id: int | None = None):
        eid = evento_id if evento_id is not None else ev["id"]
        carpeta = f"events/{eid}"
        recurso = f"{carpeta}/event.json.gz"
        cuerpo = json.dumps(ev).encode("utf-8")
        self.almacen[recurso] = gzip.compress(cuerpo)
        rec_est = rec_pbp = None
        if est is not None:
            rec_est = f"{carpeta}/statistics.json.gz"
            self.almacen[rec_est] = gzip.compress(json.dumps(est).encode("utf-8"))
        if pbp is not None:
            rec_pbp = f"{carpeta}/point_by_point.json.gz"
            self.almacen[rec_pbp] = gzip.compress(json.dumps(pbp).encode("utf-8"))
        self.entradas.append(Entrada(
            evento_id=eid, recurso=recurso, observado=observado,
            sha_indice=hashlib.sha256(cuerpo).hexdigest() if sha_indice else None,
            recurso_estadistica=rec_est, recurso_pbp=rec_pbp))

    def leer(self, rel: str) -> bytes:
        return gzip.decompress(self.almacen[rel])


def _conn(esquema):
    conn = psycopg.connect(esquema.dsn, autocommit=False)
    conn.execute(f"SET search_path TO {esquema.nombre}, public")
    conn.commit()
    return conn


def _cargar(esquema, lote: Lote, almacen, rechazos=None):
    with _conn(esquema) as conn:
        cont = cargar(conn, lote.entradas, lote.leer, almacen, rechazos)
    return cont


def _cuentas(esquema) -> dict:
    with _conn(esquema) as conn:
        return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLAS}


def _evento_completo(eid, id_local=101, id_visitante=202, ronda="Round of 32", nombre_local="Ana Uno",
                     nombre_visitante="Bea Dos", con_stats=True, con_pbp=True, **kw):
    e = evento(evento_id=eid, id_local=id_local, id_visitante=id_visitante, ronda=ronda,
               nombre_local=nombre_local, nombre_visitante=nombre_visitante, **kw)
    sets = sets_de(e)
    return e, (estadistica_json() if con_stats else None), (pbp_desde(sets) if con_pbp else None)


@pytest.fixture
def almacen(tmp_path):
    return tmp_path / "almacen"


def test_carga_basica_crea_filas_y_recibos_retro(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(1001)
    e2, s2, p2 = _evento_completo(1002, id_local=303, id_visitante=404, ronda="Quarterfinals",
                                  nombre_local="Carla Tres", nombre_visitante="Dora Cuatro")
    lote.add(e1, s1, p1)
    lote.add(e2, s2, p2)
    cont = _cargar(esquema, lote, almacen)
    cuentas = _cuentas(esquema)
    assert cont["cargado"] == 2 and cont["leidas"] == 2
    assert cuentas["partido"] == 2 and cuentas["resultado"] == 2 and cuentas["programa"] == 2
    assert cuentas["estadistica"] == 4                       # dos lados por partido
    assert cuentas["juego_pbp"] > 0
    assert cuentas["recibo"] == 6                            # event + statistics + pbp, por evento
    with _conn(esquema) as conn:
        retro = conn.execute("SELECT count(*) FROM recibo WHERE retro AND fuente = 'sofascore' "
                             "AND recibido_en = %s", (OBSERVADO,)).fetchone()[0]
        lote_txt = conn.execute("SELECT DISTINCT lote FROM recibo").fetchall()
    assert retro == 6 and lote_txt == [("sofascore_20261104",)]


def test_orientacion_canonica_con_id_de_home_mayor(esquema, almacen):
    lote = Lote()
    # El evento 1 crea a «V» (id 202) primero: su jugador tiene id interno menor.
    e1, s1, p1 = _evento_completo(2001, id_local=202, id_visitante=505, nombre_local="Vera Dos",
                                  nombre_visitante="Ines Cinco")
    # El evento 2 pone a «N» (id 303, nuevo, jugador mayor) como LOCAL: el partido debe guardarse con V como jugador_1.
    e2, s2, p2 = _evento_completo(2002, id_local=303, id_visitante=202, nombre_local="Nora Tres",
                                  nombre_visitante="Vera Dos", ronda="Quarterfinals")
    e2["winnerCode"] = 1                                     # gana el local (N)
    lote.add(e1, s1, p1)
    lote.add(e2, s2, p2)
    _cargar(esquema, lote, almacen)
    with _conn(esquema) as conn:
        fila = conn.execute(
            "SELECT p.jugador_1, p.jugador_2, r.ganador, r.sets, a.id_fuente "
            "FROM partido p JOIN resultado r ON r.partido_id = p.partido_id "
            "JOIN jugador_alias a ON a.jugador_id = p.jugador_1 AND a.fuente = 'sofascore' "
            "WHERE p.ronda = 'QF'").fetchone()
    j1, j2, ganador, sets, id_j1 = fila
    assert j1 < j2
    assert id_j1 == "202"                                    # jugador_1 es V
    assert ganador == 2                                      # en canónico, el ganador (N) es el jugador_2
    assert sets[0][0] == 3 and sets[0][1] == 6               # el set 6-3 del local aparece como 3-6 canónico


def test_idempotencia_repetir_la_carga_no_anade_filas(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(3001)
    lote.add(e1, s1, p1)
    _cargar(esquema, lote, almacen)
    antes = _cuentas(esquema)
    cont = _cargar(esquema, lote, almacen)
    despues = _cuentas(esquema)
    assert antes == despues
    assert cont["cargado"] == 0 and cont["ya_cargado"] == 1


def test_duplicados_de_evento_y_de_partido(esquema, almacen, tmp_path):
    lote = Lote()
    e1, s1, p1 = _evento_completo(4001)
    lote.add(e1, s1, p1)
    lote.add(e1, s1, p1)                                     # mismo evento dos veces
    e2, s2, p2 = _evento_completo(4002)                      # mismo partido (mismos jugadores, ronda, edición)
    lote.add(e2, s2, p2)
    rech = tmp_path / "rechazos.csv"
    cont = _cargar(esquema, lote, almacen, rech)
    assert cont["duplicado:evento"] == 1 and cont["duplicado:partido"] == 1 and cont["cargado"] == 1
    tipos = [(f["tipo"], f["motivo"]) for f in csv.DictReader(open(rech, encoding="utf-8"))]
    assert ("duplicado", "evento_duplicado") in tipos and ("duplicado", "partido_duplicado") in tipos


def test_rechazos_con_motivo_y_bucket_cuadra(esquema, almacen, tmp_path):
    lote = Lote()
    ok, s, p = _evento_completo(5001)
    lote.add(ok, s, p)
    sin_ronda, _, _ = _evento_completo(5002, ronda=None, id_local=611, id_visitante=612)
    lote.add(sin_ronda, None, None)
    bo4 = evento(evento_id=5003, mejor_de=4, id_local=621, id_visitante=622)
    lote.add(bo4, None, None)
    mismo = evento(evento_id=5004, id_local=631, id_visitante=631)
    lote.add(mismo, None, None)
    futbol = evento(evento_id=5005, deporte="football")
    lote.add(futbol, None, None)
    absurdo = evento(evento_id=5006, sets=((6, 3, None, None), (6, 3, None, None)), ganador=2,
                     id_local=641, id_visitante=642)
    lote.add(absurdo, None, None)
    rech = tmp_path / "rechazos.csv"
    cont = _cargar(esquema, lote, almacen, rech)
    assert cont["rechazo:ronda_desconocida"] == 1
    assert cont["rechazo:mejor_de_no_valido"] == 1
    assert cont["rechazo:mismo_jugador"] == 1
    assert cont["excluido:no_tenis"] == 1
    assert cont["rechazo:completado_incoherente"] == 1
    assert cont["cargado"] == 1
    categorias = sum(v for k, v in cont.items() if k.startswith(("rechazo:", "excluido:", "duplicado:")))
    assert cont["leidas"] == cont["cargado"] + cont["ya_cargado"] + categorias
    filas = list(csv.DictReader(open(rech, encoding="utf-8")))
    assert {f["motivo"] for f in filas if f["tipo"] == "rechazo"} >= {"ronda_desconocida", "mejor_de_no_valido",
                                                                     "mismo_jugador", "completado_incoherente"}


def test_sha_del_indice_que_no_coincide_se_rechaza(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(6001)
    lote.add(e1, s1, p1, sha_indice=False)
    lote.entradas[0] = Entrada(**{**lote.entradas[0].__dict__, "sha_indice": "0" * 64})
    cont = _cargar(esquema, lote, almacen)
    assert cont["rechazo:sha_indice_no_coincide"] == 1 and cont["cargado"] == 0


def test_conflicto_de_superficie_en_la_edicion_queda_registrado(esquema, almacen, tmp_path):
    lote = Lote()
    a, sa, pa = _evento_completo(7001, id_local=701, id_visitante=702)
    b, sb, pb = _evento_completo(7002, id_local=703, id_visitante=704, ronda="Quarterfinals")
    b["groundType"] = "Hardcourt outdoor"
    b["tournament"]["uniqueTournament"]["groundType"] = "Hardcourt outdoor"
    lote.add(a, sa, pa)
    lote.add(b, sb, pb)
    rech = tmp_path / "rechazos.csv"
    _cargar(esquema, lote, almacen, rech)
    motivos = [f["motivo"] for f in csv.DictReader(open(rech, encoding="utf-8"))]
    assert "edicion_conflicto:superficie" in motivos
    with _conn(esquema) as conn:
        sup = conn.execute("SELECT superficie FROM edicion").fetchone()[0]
    assert sup == "clay"                                    # gana el primero en orden de inicio


def test_edicion_con_fin_del_torneo_y_lunes_coherente(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(8001)
    lote.add(e1, s1, p1)
    _cargar(esquema, lote, almacen)
    with _conn(esquema) as conn:
        fila = conn.execute("SELECT fecha_fin, lunes_semana, visible_desde, superficie, indoor, por_equipos "
                            "FROM edicion").fetchone()
    fecha_fin, lunes, visible, sup, indoor, equipos = fila
    assert fecha_fin.isoformat() == "2026-06-07" and lunes.isoformat() == "2026-06-01"
    # Inicio del torneo 2026-05-24 menos 7 días
    assert visible == datetime(2026, 5, 17, tzinfo=timezone.utc)
    assert sup == "clay" and indoor is False and equipos is False


def test_pit_corte_antes_durante_y_despues_del_partido(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(9001)
    lote.add(e1, s1, p1)
    _cargar(esquema, lote, almacen)
    inicio = datetime.fromtimestamp(e1["startTimestamp"], tz=timezone.utc)
    antes = inicio.replace(microsecond=0)
    from datetime import timedelta
    durante = inicio - timedelta(hours=11)                  # tras (inicio − 12 h), antes del fin estimado
    despues = inicio + timedelta(hours=12)
    with _conn(esquema) as conn:
        ver = lambda corte, tabla: conn.execute(f"SELECT count(*) FROM {tabla}_a_las(%s)", (corte,)).fetchone()[0]
        assert ver(inicio - timedelta(hours=13), "partido") == 0
        assert ver(durante, "partido") == 1
        assert ver(durante, "resultado") == 0               # el resultado aún no existía
        assert ver(despues, "resultado") == 1
        assert ver(antes, "resultado") == 0


def test_pit_retro_de_2023_ve_datos_cargados_en_2026(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(9101)
    e1["startTimestamp"] = INICIO_2023
    e1["time"]["currentPeriodStartTimestamp"] = INICIO_2023 + 2400
    e1["tournament"]["startTimestamp"] = INICIO_2023 - 3 * 86400
    e1["tournament"]["endTimestamp"] = INICIO_2023 + 10 * 86400
    lote.add(e1, s1, p1)                                    # observado en 2026, partido de 2023
    _cargar(esquema, lote, almacen)
    corte = datetime.fromtimestamp(INICIO_2023 + 86400 * 2, tz=timezone.utc)
    with _conn(esquema) as conn:
        assert conn.execute("SELECT count(*) FROM partido_a_las(%s)", (corte,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM resultado_a_las(%s)", (corte,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM partido_a_las(%s)", (datetime(2023, 5, 1, tzinfo=timezone.utc),)
                            ).fetchone()[0] == 0


def test_ningun_campo_prohibido_llega_a_la_evidencia(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(9201)
    e1["firstToServe"] = 1
    lote.add(e1, s1, p1)
    _cargar(esquema, lote, almacen)
    with _conn(esquema) as conn:
        for tabla in TABLAS:
            if tabla == "recibo":
                continue
            texto = conn.execute(f"SELECT coalesce(string_agg(t::text, ' '), '') FROM {tabla} t").fetchone()[0]
            assert "3444788" not in texto and "4321" not in texto and "userCount" not in texto


def test_nombres_y_alias_de_jugadores(esquema, almacen):
    lote = Lote()
    e1, s1, p1 = _evento_completo(9301, id_local=801, id_visitante=802)
    lote.add(e1, s1, p1)
    _cargar(esquema, lote, almacen)
    with _conn(esquema) as conn:
        alias = conn.execute("SELECT id_fuente, metodo FROM jugador_alias WHERE fuente = 'sofascore' "
                             "ORDER BY id_fuente").fetchall()
        nombres = conn.execute("SELECT valor FROM jugador_asercion WHERE campo = 'nombre' ORDER BY valor").fetchall()
    assert alias == [("801", "id_exacto"), ("802", "id_exacto")]
    assert nombres == [("Ana Uno",), ("Bea Dos",)]
