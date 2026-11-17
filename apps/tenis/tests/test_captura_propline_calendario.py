"""Calendario de PropLine hacia partido/programa: filtro, torneo y superficie, jugadores exactos, idempotencia,
reprogramación, y que el exportador y la inferencia del motor vean esos partidos."""
from datetime import date, datetime, timedelta, timezone

import pytest

from tenis.captura import propline_calendario as pc

UTC = timezone.utc
AHORA = datetime(2026, 11, 17, 22, 30, tzinfo=UTC)
RECIBIDO = "2026-11-17T22:07:57+00:00"
SHA = "a" * 64


def ev(id_, local, visita, torneo="ATP Drummondville Challenger", tour="Challenger", inicio="2026-11-18T13:00:00Z", **extra):
    return {"id": id_, "home_team": local, "away_team": visita, "tournament": torneo, "tour": tour,
            "commence_time": inicio, "live": False, "is_outright": False} | extra


# ------------------------------------------------------------------------------------------------ filtro (sin base)
def test_analizar_descarta_lo_que_el_modelo_no_cubre():
    eventos = [
        ev("1", "A B", "C D"),
        ev("2", "A B", "C D", tour="ITF", torneo="ITF M25 Heraklion"),
        ev("3", "A B / E F", "C D / G H", torneo="Challenger Kobe, Doubles"),
        ev("4", "A B", "C D", live=True),
        ev("5", "A B", "C D", inicio="2026-11-17T22:32:00Z"),                       # empieza en 2 min: no se alcanza a sellar
        ev("6", "A B", "C D", inicio="2026-11-25T10:00:00Z"),                       # fuera de las 72 h
        ev("7", "A B", "C D", torneo="Australian Open Men Singles", tour="ATP"),
        ev("8", "A B", "C D", torneo="ATP Next Gen Finals", tour="ATP"),
        ev("9", "A B", "C D", tour=None),
        ev("10", "", "C D"),
        ev("1", "A B", "C D"),                                                       # id repetido
        ev("11", "A B", "C D", is_outright=True),
        ev("12", "Z Z", "Y Y", torneo="WTA 125K Colina, Chile Women Singles", tour="WTA"),
    ]
    cands, desc = pc.analizar(eventos, AHORA)
    assert [(c.evento_id, c.circuito, c.challenger) for c in cands] == [("1", "atp", True), ("12", "wta", False)]
    assert dict(desc) == {"tour_no_cubierto": 2, "dobles": 1, "en_vivo": 1, "ya_empezado": 1, "fuera_de_horizonte": 1,
                          "torneo_no_soportado": 2, "evento_incompleto": 1, "evento_repetido": 1, "outright": 1}


# ------------------------------------------------------------------------------------------- torneo (sin base)
def _torneo(tid, nombre, categoria, ediciones, circ="atp"):
    from tenis.identidad.normalizar import tokens
    return {"torneo_id": tid, "circuito": circ, "nombre": nombre, "categoria": categoria, "base": tuple(tokens(nombre)),
            "ediciones": sorted(ediciones, reverse=True)}


def _cand(torneo, tour="Challenger", dia="2026-11-18"):
    circuito, challenger = pc.TOURS[tour.upper()]
    return pc.Candidato("x", datetime.fromisoformat(f"{dia}T13:00:00+00:00"), "A B", "C D", torneo, circuito, challenger)


def test_torneo_por_ciudad_semana_y_superficie_de_la_edicion_mas_reciente():
    idx = {"atp": [
        _torneo(1, "Drummondville", "Challenger", [(date(2025, 11, 17), "hard", True), (date(2024, 11, 11), "hard", True)]),
        _torneo(2, "Kobe", "Challenger", [(date(2025, 11, 10), "hard", True)]),
        _torneo(3, "Paris", None, [(date(2025, 11, 3), "hard", True)]),
        _torneo(4, "Finales", "Finales", [(date(2025, 11, 10), "hard", True)]),
    ]}
    t, motivo = pc.resolver_torneo(idx, _cand("ATP Drummondville Challenger"))
    assert motivo is None and (t["torneo_id"], t["superficie"], t["indoor"]) == (1, "hard", True)
    assert pc.resolver_torneo(idx, _cand("Challenger Atlantis"))[1] == "torneo_sin_historial"
    # un Challenger no se resuelve contra un torneo de gira con categoría (Metz es ATP 250 en TML) y al revés
    idx["atp"].append(_torneo(5, "Metz", "250", [(date(2025, 11, 3), "hard", True)]))
    assert pc.resolver_torneo(idx, _cand("ATP Challenger Metz, France Men Singles"))[1] == "torneo_sin_historial"
    assert pc.resolver_torneo(idx, _cand("ATP Kobe Challenger", tour="ATP", dia="2026-11-10"))[1] == "torneo_sin_historial"
    # categoría vacía en TML (el nivel cambió entre años, como Montevideo): sirve para Challenger
    idx["atp"].append(_torneo(6, "Montevideo", None, [(date(2025, 11, 10), "clay", False)]))
    t, _ = pc.resolver_torneo(idx, _cand("ATP Challenger Montevideo, Uruguay Men Singles"))
    assert (t["torneo_id"], t["superficie"]) == (6, "clay")
    assert pc.resolver_torneo(idx, _cand("ATP Paris Masters", tour="ATP", dia="2026-11-03"))[0]["torneo_id"] == 3
    # la misma ciudad en otra época del año no es el mismo torneo
    assert pc.resolver_torneo(idx, _cand("ATP Drummondville Challenger", dia="2026-06-10"))[1] == "torneo_fuera_de_calendario"
    # las Finales se reconocen por la palabra, pero no en un Challenger
    assert pc.resolver_torneo(idx, _cand("ATP World Tour Finals Men Singles", tour="ATP"))[0]["torneo_id"] == 4
    assert pc.resolver_torneo(idx, _cand("Challenger Finals", tour="Challenger"))[1] == "torneo_sin_historial"


def test_torneos_numerados_con_distinta_superficie_son_ambiguos_si_no_se_distinguen():
    mismo = lambda tid, sup: _torneo(tid, f"Hersonissos {tid}", "Challenger", [(date(2025, 11, 17), sup, False)])
    idx = {"atp": [mismo(1, "hard"), mismo(2, "clay")]}
    assert pc.resolver_torneo(idx, _cand("Challenger Hersonissos"))[1] == "torneo_ambiguo"
    idx = {"atp": [mismo(1, "hard"), mismo(2, "hard")]}                 # misma superficie: da igual cuál
    assert pc.resolver_torneo(idx, _cand("Challenger Hersonissos"))[0]["superficie"] == "hard"


def test_semana_y_ediciones_de_dos_semanas():
    assert pc.lunes_de(date(2026, 11, 18)) == date(2026, 11, 16)
    assert pc.lunes_de(date(2026, 11, 22)) == date(2026, 11, 16)
    assert pc.lunes_de(date(2026, 11, 23)) == date(2026, 11, 23)


# -------------------------------------------------------------------------------------------------- con base
psycopg = pytest.importorskip("psycopg")
from db_util import insertar, nuevo_recibo, ts  # noqa: E402
from inferencia_util import params_prueba, ranking  # noqa: E402
from tenis import inferencia as inf  # noqa: E402
from tenis import motor  # noqa: E402
from tenis.identidad.resolver import ResolutorMultifuente  # noqa: E402


def mundo(db):
    r = nuevo_recibo(db, "tml", "2025-12-01", retro=True)
    t = insertar(db, "INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) VALUES "
                     "('atp', '7235', 'Drummondville', 'Challenger', 'tml', %s, %s) RETURNING torneo_id", (r, ts("2025-12-01")))
    db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, indoor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 2025, '2025-11-17', 'hard', true, 'tml', %s, %s)", (t, r, ts("2025-12-01")))
    ids = {}
    for nombre, n in (("Carlos Test", 1), ("Daniil Prueba", 1), ("Igual Nombre", 2)):
        for _ in range(n):
            j = insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES ('atp', %s, %s) RETURNING jugador_id",
                         (r, ts("2025-12-01")))
            db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 'nombre', %s, 'tml', %s, %s)", (j, nombre, r, ts("2025-12-01")))
            ids.setdefault(nombre, []).append(j)
    return t, ids


def doc(eventos, sha=SHA, recibido=RECIBIDO):
    return {"recibido_en": recibido, "sha256": sha, "eventos": eventos}


def conteos(db):
    return {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("partido", "programa", "enlace_evento", "sin_resolver", "edicion")}


def test_captura_completa_idempotencia_y_reprogramacion(esquema, tmp_path):
    with esquema.conectar() as db:
        db.execute(f"SET search_path TO {esquema.nombre}, {esquema.nombre_op}, public")
        t, ids = mundo(db)
        res = ResolutorMultifuente(db)
        base = conteos(db)
        eventos = [ev("1", "Carlos Test", "Daniil Prueba"),
                   ev("2", "Carlos Test", "Nadie Conocido"),
                   ev("3", "Igual Nombre", "Carlos Test"),
                   ev("4", "Carlos Test", "Daniil Prueba", torneo="Challenger Atlantis"),
                   ev("5", "Carlos Test", "Daniil Prueba", tour="ITF", torneo="ITF M15 Hua Hin")]
        r1 = pc.capturar(db, doc(eventos), tmp_path, res, AHORA)
        assert (r1.estado, r1.partidos_nuevos, r1.programas_nuevos, r1.sin_resolver) == ("escrito", 1, 1, 3)
        assert r1.descartes == {"tour_no_cubierto": 1}
        c = conteos(db)
        assert c["partido"] - base["partido"] == 1 and c["programa"] == 1 and c["enlace_evento"] == 1
        assert c["sin_resolver"] - base["sin_resolver"] == 3 and c["edicion"] - base["edicion"] == 1
        motivos = sorted(x[0] for x in db.execute("SELECT motivo FROM sin_resolver WHERE fuente = 'propline'").fetchall())
        assert motivos == ["jugador_ambiguo", "jugador_sin_resolver", "torneo_sin_historial"]

        # Edición y partido: superficie copiada, orden canónico, sin ronda conocida, recepción real, no retro
        sup, indoor, lunes, temporada, rec_en = db.execute(
            "SELECT superficie, indoor, lunes_semana, temporada, recibido_en FROM edicion WHERE fuente = 'propline'").fetchone()
        assert (sup, indoor, lunes, temporada) == ("hard", True, date(2026, 11, 16), 2026) and rec_en == ts(RECIBIDO)
        j1, j2, ronda, mejor = db.execute("SELECT jugador_1, jugador_2, ronda, mejor_de FROM partido WHERE fuente = 'propline'").fetchone()
        assert (j1, j2) == tuple(sorted([ids["Carlos Test"][0], ids["Daniil Prueba"][0]])) and (ronda, mejor) == ("R", 3)
        assert db.execute("SELECT retro FROM recibo WHERE fuente = 'propline'").fetchone()[0] is False

        # El mismo archivo otra vez: no hace nada. Otro archivo con lo mismo: nada nuevo (ni sin_resolver repetidos)
        assert pc.capturar(db, doc(eventos), tmp_path, res, AHORA).estado == "sin_cambios"
        r2 = pc.capturar(db, doc(eventos, sha="b" * 64, recibido="2026-11-17T23:08:00+00:00"), tmp_path, res, AHORA)
        assert (r2.partidos_nuevos, r2.programas_nuevos, r2.sin_resolver) == (0, 0, 0)
        assert conteos(db) == c | {"edicion": c["edicion"]}

        # Reprogramación: misma edición y partido, un horario nuevo (el motor usa el último)
        movido = [ev("1", "Carlos Test", "Daniil Prueba", inicio="2026-11-18T14:30:00Z")]
        r3 = pc.capturar(db, doc(movido, sha="c" * 64, recibido="2026-11-18T08:08:00+00:00"), tmp_path, res, AHORA)
        assert (r3.partidos_nuevos, r3.programas_nuevos) == (0, 1)
        pend = [x for x in motor.buscar_partidos_pendientes(db, "vx", AHORA) if x["circuito"] == "atp"]
        assert len(pend) == 1 and pend[0]["inicio_programado_utc"] == ts("2026-11-18T14:30:00Z")
        assert pend[0]["superficie"] == "hard"

        # Un partido que empezó hace más de 45 min ya no es pendiente (no se avisa para siempre)
        assert motor.buscar_partidos_pendientes(db, "vx", ts("2026-11-18T15:30:00Z")) == []


def test_el_exportador_y_la_inferencia_ven_el_partido_de_propline(esquema, tmp_path):
    with esquema.conectar() as db:
        db.execute(f"SET search_path TO {esquema.nombre}, {esquema.nombre_op}, public")
        t, ids = mundo(db)
        a, b = ids["Carlos Test"][0], ids["Daniil Prueba"][0]
        ranking(db, a, 120), ranking(db, b, 45)
        pc.capturar(db, doc([ev("1", "Carlos Test", "Daniil Prueba")]), tmp_path, ResolutorMultifuente(db), AHORA)
        pend = next(x for x in motor.buscar_partidos_pendientes(db, "vx", AHORA) if x["circuito"] == "atp")

        p, e, s = inf.conjunto_desde_db(db)
        fila = p[p.partido_id_sofascore == pend["partido_id"]].iloc[0]           # «sofascore» = fuente con hora real
        assert fila.excluir_motivo is None or fila.excluir_motivo != fila.excluir_motivo
        assert fila.corte_utc == ts("2026-11-18T12:00:00Z") and fila.superficie == "Indoor" and fila.categoria == "Challenger"

        r = inf.inferir(db, params_prueba(), [pend])[pend["partido_id"]]
        assert r["ok"], r
        assert (r["pi_lado1"] > 0.5) == (pend["jugador_1"] == b)                  # el de ranking 45 es el favorito
        # el motor sella (en seco) con el corte forzado y deja trazas de la fuente
        res = motor.simular_y_sellar_partido(db=db, partido=pend, version_modelo="vx", version_datos="d", parametros=params_prueba(),
                                             forzar_corte=ts("2026-11-18T12:00:00Z"), dry_run=True, inferencia=r)
        assert res["estado"] == "dry_run_ok"


def test_sin_los_dos_jugadores_o_sin_historial_el_motor_no_recibe_nada(esquema, tmp_path):
    with esquema.conectar() as db:
        db.execute(f"SET search_path TO {esquema.nombre}, {esquema.nombre_op}, public")
        mundo(db)
        r = pc.capturar(db, doc([ev("1", "Carlos Test", "Nadie Conocido")]), tmp_path, ResolutorMultifuente(db), AHORA)
        assert (r.partidos_nuevos, r.sin_resolver) == (0, 1)
        assert [x for x in motor.buscar_partidos_pendientes(db, "vx", AHORA) if x["circuito"] == "atp"] == []
        with pytest.raises(ValueError):
            pc.capturar(db, {"recibido_en": "no es fecha", "sha256": "x", "eventos": []}, tmp_path, ResolutorMultifuente(db), AHORA)
