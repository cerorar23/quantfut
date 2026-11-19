"""Avisos operativos: deduplicación que sobrevive entre pasadas, menos ruido del motor y salud del calendario."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tenis import alertas, motor, salud

UTC = timezone.utc


@pytest.fixture(autouse=True)
def memoria_limpia(monkeypatch):
    monkeypatch.delenv("TG_BOT_TOKEN", raising=False)          # nunca se sale a la red en las pruebas
    monkeypatch.delenv("TG_ALERT_CHAT", raising=False)
    monkeypatch.delenv(alertas.ENV_ESTADO, raising=False)
    alertas.sembrar_alertas()
    yield
    alertas.sembrar_alertas()


# ------------------------------------------------------------------------------------------- estado persistente
def test_el_aviso_no_se_repite_aunque_el_proceso_sea_nuevo(tmp_path, monkeypatch):
    ruta = tmp_path / "estado" / "alertas.json"
    monkeypatch.setenv(alertas.ENV_ESTADO, str(ruta))
    assert alertas.enviar_alerta("sello_tardio", "x", partido_id=7)["estado"] == "registrada_local"
    assert ruta.is_file() and json.loads(ruta.read_text())[0][:2] == ["sello_tardio", 7]
    alertas.sembrar_alertas()                                   # «proceso nuevo»: la memoria empieza vacía
    assert alertas.cargar_estado() == 1
    assert alertas.enviar_alerta("sello_tardio", "x", partido_id=7)["estado"] == "omitida_deduplicada"
    assert alertas.enviar_alerta("sello_tardio", "x", partido_id=8)["estado"] == "registrada_local"   # otro partido sí avisa


def test_estado_antiguo_corrupto_o_sin_configurar(tmp_path, monkeypatch):
    ruta = tmp_path / "alertas.json"
    viejo = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d")
    hoy = alertas.hoy_utc()
    ruta.write_text(json.dumps([["a", 1, viejo], ["b", None, hoy]]))
    monkeypatch.setenv(alertas.ENV_ESTADO, str(ruta))
    alertas.cargar_estado()
    alertas.guardar_estado()
    assert json.loads(ruta.read_text()) == [["b", None, hoy]]       # lo de hace 10 días se olvida
    ruta.write_text("{no es json")
    alertas.sembrar_alertas()
    assert alertas.cargar_estado() == 0                             # ilegible: empieza vacío, sin error
    monkeypatch.delenv(alertas.ENV_ESTADO)
    assert alertas.cargar_estado() == 0 and alertas.guardar_estado() is None


# ------------------------------------------------------------------------------------------- menos ruido del motor
def _partido(inicio, visto, pid=1):
    return {"partido_id": pid, "circuito": "atp", "superficie": "hard", "mejor_de": 3, "inicio_programado_utc": inicio,
            "programa_visto_desde": visto}


def test_sello_tardio_solo_avisa_si_se_pudo_evitar(monkeypatch):
    avisos = []
    monkeypatch.setattr(motor, "enviar_alerta", lambda tipo, msg, **k: avisos.append((tipo, k.get("partido_id"))) or {})
    inicio = datetime.now(UTC) - timedelta(minutes=10)
    # el horario llegó 3 h antes del corte: se podía sellar, es un fallo
    r = motor.simular_y_sellar_partido(db=None, partido=_partido(inicio, inicio - timedelta(hours=4)), version_modelo="v",
                                       version_datos="d", parametros={})
    assert r["estado"] == "omitido_tardio" and r["evitable"] is True and avisos == [("sello_tardio", 1)]
    # el horario llegó 20 min antes del inicio (40 min tras el corte): imposible, solo log
    avisos.clear()
    r = motor.simular_y_sellar_partido(db=None, partido=_partido(inicio, inicio - timedelta(minutes=20), pid=2), version_modelo="v",
                                       version_datos="d", parametros={})
    assert r["estado"] == "omitido_tardio" and r["evitable"] is False and avisos == []


def test_motivos_esperados_no_avisan_y_los_graves_si(monkeypatch):
    avisos = []
    monkeypatch.setattr(motor, "enviar_alerta", lambda tipo, msg, **k: avisos.append(tipo) or {})
    p = _partido(datetime.now(UTC) + timedelta(minutes=30), None)
    params = {"circuitos": {"atp": {"psi_r": {}, "psi_p": {}}}}
    for motivo in sorted(motor.MOTIVOS_ESPERADOS):
        r = motor.simular_y_sellar_partido(db=None, partido=p, version_modelo="v", version_datos="d", parametros=params,
                                           forzar_corte=datetime.now(UTC) - timedelta(hours=1),
                                           inferencia={"ok": False, "motivo": motivo})
        assert r["estado"] == "omitido_sin_modelo"
    assert avisos == []
    for motivo, tipo in (("sin_historia_ni_ranking", "jugador_sin_historia"), ("sin_parametros_del_circuito", "sin_pronostico")):
        motor.simular_y_sellar_partido(db=None, partido=p, version_modelo="v", version_datos="d", parametros=params,
                                       forzar_corte=datetime.now(UTC) - timedelta(hours=1),
                                       inferencia={"ok": False, "motivo": motivo})
    assert avisos == ["jugador_sin_historia", "sin_pronostico"]


# ------------------------------------------------------------------------------------------------ salud con base
psycopg = pytest.importorskip("psycopg")
from db_util import cargar_minimo, nuevo_recibo, ts  # noqa: E402


def _recibo_calendario(db, hace_horas):
    sha = f"{abs(hash(hace_horas)):064x}"[-64:]
    db.execute("INSERT INTO recibo (fuente, recurso, recibido_en, sha256, ruta_objeto, bytes, lote, retro) "
               "VALUES ('propline', '/v1/sports/tennis/odds#calendario', %s, %s, %s, 10, 'prueba', false)",
               (datetime.now(UTC) - timedelta(hours=hace_horas), sha, f"objetos/{sha[:2]}/{sha}.json.gz"))


def test_salud_del_calendario(esquema, monkeypatch):
    avisos = []
    monkeypatch.setattr(salud, "enviar_alerta", lambda tipo, msg, **k: avisos.append(tipo) or {})
    with esquema.conectar() as db:
        cargar_minimo(db)
        assert salud.comprobar_calendario(db) == {"estado": "sin_datos"} and avisos == []          # aún no se puso en marcha
        _recibo_calendario(db, 5)                                                                    # el último recibo es de hace 5 h
        r = salud.comprobar_calendario(db)
        assert r["estado"] == "alerta" and r["horas_antiguedad"] >= 4.9 and avisos == ["colector_parado"]
        _recibo_calendario(db, 0.5)                                                                  # llega uno nuevo: el último manda
        assert salud.comprobar_calendario(db)["estado"] == "ok" and avisos == ["colector_parado"]


def test_artefacto_en_carpeta_y_main_con_codigo_de_salida(esquema, tmp_path, monkeypatch, capsys):
    from tenis.modelo import hiperparametros as hp
    avisos = []
    monkeypatch.setattr(salud, "enviar_alerta", lambda tipo, msg, **k: avisos.append(tipo) or {})
    carpeta = tmp_path / "artefactos"
    carpeta.mkdir()
    contenido = {"circuitos": {"atp": {"x": 1}}}
    hp.escribir(carpeta / "uno.json", contenido)
    hp.escribir(carpeta / "dos.json", {"otro": 2})
    with esquema.conectar() as db:
        cargar_minimo(db)
        sha = hp.huella(contenido)
        db.execute("INSERT INTO artefacto (sha256, tipo, version_modelo) VALUES (%s, 'modelo', 'v2')", (sha,))
        db.execute("INSERT INTO artefacto_activo (sha256, aprobado_en_chat, imagen) VALUES (%s, 'chat', 'tenis-motor:v2')", (sha,))
        assert salud.comprobar_artefacto_activo(db, carpeta)["estado"] == "ok"                      # una de las dos coincide
        assert avisos == []
        vacia = tmp_path / "vacia"
        vacia.mkdir()
        assert salud.comprobar_artefacto_activo(db, vacia)["estado"] == "descuadre_huella" and avisos == ["contrato_roto"]
    args = ["--dsn", esquema.dsn, "--esquema", esquema.nombre, "--artefactos", str(carpeta)]
    codigo = salud.main(args)
    informe = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert {"cadena", "frescura", "calendario", "identidad", "artefacto"} <= set(informe)
    assert informe["artefacto"]["estado"] == "ok" and informe["cadena"]["estado"] == "ok" and codigo in (0, 1)
    assert salud.main(["--dsn", esquema.dsn, "--esquema", "no valido!"]) == 1
