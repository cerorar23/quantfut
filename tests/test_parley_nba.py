from datetime import datetime, timedelta, timezone

import pytest

from qf.publish import parley_nba as nba
from qf.publish import parley_v2 as v2
from qf.publish.alta_prob import Candidato
from qf.publish.parley_ext import OpcionExterna

INICIO = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc)
NOW = INICIO - timedelta(hours=3)


def op(mercado, sel, linea, prob, price, jugador=(), match="nba:9"):
    return OpcionExterna(match_id=match, cand=Candidato(mercado, sel, linea, prob), price=price, book="b",
                         odds_source="t", odds_as_of=NOW, deporte="nba", jugador=jugador)


def test_ejecucion_es_el_maximo_entre_inicio_menos_60_y_el_sellado():
    antes = INICIO - timedelta(hours=5)
    despues = INICIO - timedelta(minutes=45)
    assert nba.momento_ejecucion(INICIO, antes) == INICIO - timedelta(minutes=60)
    assert nba.momento_ejecucion(INICIO, despues) == despues


def test_ventana_de_seleccion_y_limite_de_30_minutos():
    sello = INICIO - timedelta(hours=4)
    assert nba.puede_ejecutarse(INICIO - timedelta(minutes=61), INICIO, sello)[0] is False
    assert nba.puede_ejecutarse(INICIO - timedelta(minutes=60), INICIO, sello)[0] is True
    assert nba.puede_ejecutarse(INICIO - timedelta(minutes=31), INICIO, sello)[0] is True
    ok, motivo = nba.puede_ejecutarse(INICIO - timedelta(minutes=30), INICIO, sello)
    assert ok is False and "30" in motivo
    assert nba.puede_ejecutarse(NOW, INICIO, None) == (False, "esperando el sellado oficial del pronóstico NBA")


def test_clave_idempotente_depende_de_partido_estrategia_y_version():
    a = nba.clave_idempotente("9")
    assert a == nba.clave_idempotente("9") and a != nba.clave_idempotente("10")
    assert a != nba.clave_idempotente("9", version="v9") and a != nba.clave_idempotente("9", estrategia="otra")


def _ctx(**kw):
    base = dict(inicio=INICIO, estado_jugadores={"11": "active"}, cuotas={})
    base.update(kw)
    return nba.Contexto(**base)


def test_revalidar_horario_jugador_y_cuota():
    pata = op("player_points", "over", 24.5, .6, 1.70, ("11", "A"))
    ctx = _ctx(cuotas={v2._clave(pata): 1.70})
    assert nba.revalidar([pata], INICIO, ctx)[0] == "ok"
    assert nba.revalidar([pata], INICIO, _ctx(inicio=INICIO + timedelta(minutes=30), cuotas=ctx.cuotas))[0] == "recalcular"
    assert nba.revalidar([pata], INICIO, _ctx(estado_jugadores={"11": "out"}, cuotas=ctx.cuotas))[0] == "anular"
    assert nba.revalidar([pata], INICIO, _ctx(estado_jugadores={}, cuotas=ctx.cuotas))[0] == "anular"
    assert nba.revalidar([pata], INICIO, _ctx(titulares={"11": False}, cuotas=ctx.cuotas))[0] == "anular"
    assert nba.revalidar([pata], INICIO, _ctx(minutos_esperados={"11": 8.0}, cuotas=ctx.cuotas))[0] == "anular"
    assert nba.revalidar([pata], INICIO, _ctx(cuotas={v2._clave(pata): 1.50}))[0] == "recalcular"
    assert nba.revalidar([pata], INICIO, _ctx())[0] == "recalcular"                  # sin cuota vigente


def test_parley_de_partido_es_same_game_solo_referencia_sin_paquete_ni_modelo_conjunto():
    ops = [op("h2h", "home", None, .70, 1.45), op("totals", "over", 220.5, .55, 1.75),
           op("player_points", "over", 24.5, .60, 1.70, ("11", "A")),
           op("player_points", "under", 24.5, .40, 1.70, ("11", "A")), op("h2h", "home", None, .7, 1.4, match="nba:10")]
    t = nba.parley_partido(ops, "9")
    assert t.tipo == "same_game" and t.estado == "solo_referencia" and len(t.legs) == 2
    assert all(o.match_id == "nba:9" for o in t.legs)
    ejecutable = nba.parley_partido(ops, "9", cuota_paquete=2.9, prob_conjunta=.36)
    assert ejecutable.estado == "publicado" and ejecutable.quote == 2.9


def test_no_combina_patas_incompatibles_ni_inventa_si_faltan_patas():
    solo_mismo_jugador = [op("player_points", "over", 24.5, .6, 1.7, ("11", "A")),
                          op("player_points", "under", 24.5, .4, 1.7, ("11", "A"))]
    assert nba.parley_partido(solo_mismo_jugador, "9") is None
    with pytest.raises(ValueError):
        nba.parley_partido(solo_mismo_jugador, "9", n_patas=5)
