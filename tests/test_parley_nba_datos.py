from datetime import datetime, timedelta, timezone

import pytest

from qf.publish import parley_nba as nba
from qf.publish import parley_nba_datos as nd
from qf.publish import parley_v2 as v2
from qf.publish import parley_v2_datos as base
from qf.publish.alta_prob import Candidato
from qf.publish.parley_ext import OpcionExterna

INICIO = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc)
SELLO = INICIO - timedelta(hours=4)
AHORA = INICIO - timedelta(minutes=55)


def op(mercado, sel, linea, prob, price, jugador=()):
    return OpcionExterna(match_id="nba:9", cand=Candidato(mercado, sel, linea, prob), price=price, book="b",
                         odds_source="t", odds_as_of=AHORA, deporte="nba", jugador=jugador,
                         evento=("9", "basketball_nba", INICIO, "L", "V"))


OPS = [op("h2h", "home", None, .70, 1.45), op("totals", "over", 220.5, .55, 1.75),
       op("player_points", "over", 24.5, .60, 1.70, ("11", "A"))]


def ctx(**kw):
    base_ = dict(inicio=INICIO, estado_jugadores={"11": "active"}, cuotas={v2._clave(o): o.price for o in OPS})
    base_.update(kw)
    return nba.Contexto(**base_)


@pytest.fixture
def entorno(monkeypatch):
    guardados = []
    monkeypatch.setenv("PARLEY_V2_ENABLED", "1")
    monkeypatch.setattr(base, "_existe", lambda clave: False)
    monkeypatch.setattr(base, "_prev", lambda: "0" * 64)
    monkeypatch.setattr(base, "_guardar", lambda lote: guardados.append(lote) or True)
    return guardados


def correr(now=AHORA, sellado=SELLO, ops=None, contexto=None, **kw):
    return nd.ejecutar_partido(now, "9", INICIO, sellado, lambda n, e: OPS if ops is None else ops,
                               lambda n, e: contexto or ctx(), **kw)


def test_espera_el_sellado_y_no_selecciona_pasado_inicio_menos_30(entorno):
    assert correr(sellado=None)["estado"] == "esperando"
    assert correr(now=INICIO - timedelta(minutes=90))["estado"] == "esperando"
    assert correr(now=INICIO - timedelta(minutes=29))["estado"] == "fuera_de_ventana"
    assert not entorno


def test_sella_un_same_game_como_solo_referencia_con_cadena_y_clave_unica(entorno):
    r = correr()
    assert r["estado"] == "elegido" and r["tipo"] == "same_game" and r["ticket_estado"] == "solo_referencia"
    lote = entorno[0]
    assert lote["clave"] == "parley_objetivo|v2.1|partido|9" and lote["ambito"] == "partido" and lote["evento_id"] == "9"
    t = lote["payload"]["tickets"][0]
    assert t["tipo"] == "same_game" and t["probabilidad_conjunta"] is None and len(t["patas"]) == 2
    assert all(p["evento_id"] == "9" and p["deporte"] == "nba" for p in t["patas"])


def test_con_cuota_de_paquete_y_modelo_conjunto_es_publicable(entorno):
    r = correr(cuota_paquete=2.9, prob_conjunta=.36)
    assert r["ticket_estado"] == "publicado" and r["cuota_total"] == 2.9


def test_es_idempotente_por_partido(monkeypatch, entorno):
    monkeypatch.setattr(base, "_existe", lambda clave: True)
    assert correr()["estado"] == "ya_elegido"
    monkeypatch.setattr(base, "_existe", lambda clave: False)
    monkeypatch.setattr(base, "_guardar", lambda lote: False)
    assert correr()["estado"] == "ya_elegido"


def test_jugador_fuera_anula_y_cambio_de_horario_recalcula_una_vez(entorno):
    r = correr(contexto=ctx(estado_jugadores={"11": "out"}), ops=[o for o in OPS if o.jugador] + [OPS[0]])
    assert r["estado"] == "anulado" and any("out" in m for m in r["motivos"]) and not entorno
    llamadas = []

    def leer(now, e):
        llamadas.append(1)
        return ctx(inicio=INICIO + timedelta(minutes=30))
    r = nd.ejecutar_partido(AHORA, "9", INICIO, SELLO, lambda n, e: OPS, leer)
    assert r["estado"] == "anulado" and len(llamadas) == 2 and not entorno            # recalculó una vez y sigue mal


def test_sin_patas_compatibles_se_abstiene_y_desactivado_no_hace_nada(monkeypatch, entorno):
    assert correr(ops=[OPS[0]])["estado"] == "abstencion"
    monkeypatch.delenv("PARLEY_V2_ENABLED")
    assert correr()["estado"] == "desactivado"
    assert correr(dry_run=True)["estado"] == "elegido" and not entorno


def test_anular_un_ticket_sellado_marca_sus_patas_void(monkeypatch):
    anuladas = []
    monkeypatch.setattr(nd, "_patas_del_ticket", lambda t: [{"pata_id": "a"}, {"pata_id": "b"}])
    monkeypatch.setattr(nd, "_anular", lambda p, f: anuladas.append((p, f)) or 1)
    assert nd.anular_publicado("t1", ["A: out"]) == 2
    assert anuladas == [("a", "anulado: A: out"), ("b", "anulado: A: out")]
