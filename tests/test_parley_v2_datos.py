from datetime import date, datetime, timedelta, timezone

import pytest

from qf.eval import parley_calibracion as pc
from qf.publish import hashchain
from qf.publish import parley_v2 as v2
from qf.publish import parley_v2_datos as pd_
from qf.publish.alta_prob import Candidato
from qf.publish.parley_ext import OpcionExterna

DIA = date(2026, 11, 6)


def hora(h, m=0):
    return datetime(2026, 11, 6, h, m, tzinfo=timezone.utc)


def recibo(f, ok=True, fin=None):
    return pd_.Recibo(f, "complete" if ok else "partial", fin or hora(9, 20), "job-1", "v1")


RECIBOS = {"tenis": recibo("tenis"), "cuotas": recibo("cuotas")}
APROBADO = {"aprobado": True, "categorias": {}, "nombre": "x"}


def ops(n=14):
    precios = [1.40, 1.50, 1.70, 1.80, 1.70, 1.70, 1.70, 1.70] + [1.65] * 7
    return [OpcionExterna(match_id=f"{'tenis' if i % 2 else 'futbol'}:{i}", cand=Candidato("h2h", "home", None, .7),
                          price=p, book="b", odds_source="t", odds_as_of=hora(9, 0), deporte="tenis" if i % 2 else "futbol",
                          evento=(str(i), "tennis", hora(14), "L", "V")) for i, p in enumerate(precios[:n])]


@pytest.fixture
def entorno(monkeypatch):
    guardados = []
    monkeypatch.setenv("PARLEY_V2_ENABLED", "1")
    monkeypatch.setattr(pd_, "_lote_diario", lambda dia: "d" * 64)
    monkeypatch.setattr(pd_, "_existe", lambda clave: False)
    monkeypatch.setattr(pd_, "_prev", lambda: hashchain.GENESIS)
    monkeypatch.setattr(pd_, "_guardar", lambda lote: guardados.append(lote) or True)
    return guardados


def test_ventana_y_reintentos_cada_5_minutos_hasta_las_0400_de_mexico():
    assert pd_.ventana(DIA) == (hora(9, 35), hora(10, 0))
    assert pd_.siguiente_intento(hora(9, 0)) == hora(9, 35)
    assert pd_.siguiente_intento(hora(9, 35)) == hora(9, 40)
    assert pd_.siguiente_intento(hora(9, 41)) == hora(9, 45)
    assert pd_.siguiente_intento(hora(9, 56)) == hora(10, 0)
    assert pd_.siguiente_intento(hora(10, 0)) is None


def test_barrera_exige_lote_diario_recibos_y_artefacto_aprobado():
    ok = pd_.barrera(hora(9, 36), RECIBOS, "h", APROBADO)
    assert ok.ok and ok.completa and ok.deportes == ("futbol", "tenis")
    sin_artefacto = pd_.barrera(hora(9, 36), RECIBOS, "h", None)
    assert not sin_artefacto.ok and "artefacto de calibración no aprobado" in sin_artefacto.razones
    assert pd_.barrera(hora(9, 36), RECIBOS, "h", None, modo_referencia=True).ok
    sin_tenis = pd_.barrera(hora(9, 36), {**RECIBOS, "tenis": recibo("tenis", ok=False)}, "h", APROBADO)
    assert sin_tenis.ok and not sin_tenis.completa and sin_tenis.deportes == ("futbol",)
    futuro = pd_.barrera(hora(9, 36), {**RECIBOS, "cuotas": recibo("cuotas", fin=hora(9, 50))}, "h", APROBADO)
    assert not futuro.ok                                      # un recibo posterior a la decisión no vale
    assert not pd_.barrera(hora(9, 36), RECIBOS, None, APROBADO).deportes.count("futbol")


def test_desactivado_y_antes_de_hora(monkeypatch):
    monkeypatch.delenv("PARLEY_V2_ENABLED", raising=False)
    assert pd_.ejecutar(hora(9, 36), lambda n, d: [], RECIBOS)["estado"] == "desactivado"
    monkeypatch.setenv("PARLEY_V2_ENABLED", "1")
    assert pd_.ejecutar(hora(9, 0), lambda n, d: [], RECIBOS, modo_referencia=True)["estado"] == "antes_de_hora"


def test_espera_si_falta_una_fuente_y_publica_lo_factible_en_el_limite(entorno):
    sin_tenis = {**RECIBOS, "tenis": recibo("tenis", ok=False)}
    espera = pd_.ejecutar(hora(9, 36), lambda n, d: ops(), sin_tenis, modo_referencia=True)
    assert espera["estado"] == "esperando" and espera["siguiente_intento"] == hora(9, 40).isoformat() and not entorno
    visto = []
    limite = pd_.ejecutar(hora(10, 0), lambda n, d: visto.append(d) or [o for o in ops() if o.deporte in d],
                          sin_tenis, modo_referencia=True)
    assert limite["estado"] == "elegido" and limite["deportes"] == ["futbol"] and visto == [("futbol",)] and entorno


def test_sin_fuentes_en_el_limite_se_abstiene_sin_sellar(entorno):
    r = pd_.ejecutar(hora(10, 5), lambda n, d: ops(), {"cuotas": recibo("cuotas", ok=False)}, modo_referencia=True)
    assert r["estado"] == "abstencion" and not entorno


def test_sella_un_lote_con_cadena_hash_y_estado_solo_referencia_en_sombra(entorno):
    r = pd_.ejecutar(hora(9, 36), lambda n, d: ops(), RECIBOS, modo_referencia=True)
    assert r["estado"] == "elegido" and len(r["tickets"]) == 4 and all(t["estado"] == "solo_referencia" for t in r["tickets"])
    lote = entorno[0]
    p = lote["payload"]
    assert p["estrategia"] == "parley_objetivo" and p["lote_diario_sha256"] == "d" * 64
    assert lote["chain_sha256"] == hashchain.sha256_hex(hashchain.GENESIS + lote["payload_sha256"])
    assert lote["payload_sha256"] == hashchain.sha256_hex(hashchain.canonical_json(p))
    pata = p["tickets"][0]["patas"][0]
    assert {"deporte", "evento_id", "mercado", "cuota", "casa", "cuota_en", "inicio_utc"} <= set(pata)
    assert all(pt["cuota_en"] <= p["decidido_at"] for t in p["tickets"] for pt in t["patas"])
    assert lote["clave"] == "parley_objetivo|v2.1|diario|2026-11-06"


def test_es_idempotente_y_no_recalcula_un_lote_sellado(monkeypatch, entorno):
    monkeypatch.setattr(pd_, "_existe", lambda clave: True)
    r = pd_.ejecutar(hora(9, 36), lambda n, d: pytest.fail("no se vuelve a calcular"), RECIBOS, modo_referencia=True)
    assert r["estado"] == "ya_elegido"
    monkeypatch.setattr(pd_, "_existe", lambda clave: False)
    monkeypatch.setattr(pd_, "_guardar", lambda lote: False)        # otro proceso lo selló entre medias
    assert pd_.ejecutar(hora(9, 36), lambda n, d: ops(), RECIBOS, modo_referencia=True)["estado"] == "ya_elegido"


def test_con_artefacto_aprobado_se_abstiene_por_categoria_sin_calibracion(entorno):
    # Aprobado pero sin categorías calibradas: ninguna pata pasa el filtro → abstención sellada sin tickets.
    r = pd_.ejecutar(hora(9, 36), lambda n, d: ops(), RECIBOS, artefacto=APROBADO)
    assert r["estado"] == "abstencion" and r["tickets"] == [] and entorno[0]["payload"]["tickets"] == []


def test_dry_run_no_guarda_ni_exige_habilitar(monkeypatch, entorno):
    monkeypatch.delenv("PARLEY_V2_ENABLED", raising=False)
    r = pd_.ejecutar(hora(9, 36), lambda n, d: ops(), RECIBOS, modo_referencia=True, dry_run=True)
    assert r["estado"] == "elegido" and not entorno
