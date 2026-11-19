"""Registro de artefactos: validación previa, anexado en la base, carga estricta por huella y pasada real del motor."""
import json
import shutil
from pathlib import Path

import pytest

from tenis import artefactos as art
from tenis.modelo import hiperparametros as hp

ARTEFACTO = Path(__file__).resolve().parents[1] / "artefactos" / "tenis-2.1-capa-edad.json"
ARTEFACTO_22 = Path(__file__).resolve().parents[1] / "artefactos" / "tenis-2.2-capa-edad.json"


def _informe(contenido, pasa=True, capa=True, base=None):
    g = {"G_linea_base": {"pasa": pasa}, "G_cordura": {"pasa": True}, "G_calibracion": {"pasa": False}, "G_recalibracion": {},
         "G_capa_edad": {"capa_activa": capa}}
    circ = {"compuertas": g, "n_evaluados": 100, "no_fuga": {"violaciones": 0}, "calibracion": {"pi_lado1": {"pendiente": 0.9}}}
    return {"sha256_hiperparametros": hp.huella(base or art._base_sin_capa(contenido)), "eval_rango": [2019, 2024],
            "sha256_predicciones_total": "0" * 64, "circuitos": {c: circ for c in contenido["circuitos"]}}


def _escribir(tmp_path, informe):
    ruta = tmp_path / "informe.json"
    ruta.write_text(json.dumps(informe), encoding="utf-8")
    return ruta


def test_el_artefacto_del_repo_es_valido_y_trae_la_capa_en_los_dos_circuitos(tmp_path):
    contenido = hp.leer(ARTEFACTO)
    plan = art.validar(ARTEFACTO, _escribir(tmp_path, _informe(contenido)), menor=1)
    assert plan["sha256"] == json.loads(ARTEFACTO.read_text(encoding="utf-8"))["sha256_contenido"]
    assert plan["version_modelo"] == f"tenis-2.1+{plan['sha256'][:12]}"
    assert set(plan["capa_edad"]) == {"atp", "wta"} and all(plan["capa_edad"].values())
    assert any("G_calibracion" in x for x in plan["advertencias"])          # advierte, no bloquea


def test_el_artefacto_2_2_es_valido_y_comparte_la_base_con_el_2_1(tmp_path):
    c21, c22 = hp.leer(ARTEFACTO), hp.leer(ARTEFACTO_22)
    assert art._base_sin_capa(c21) == art._base_sin_capa(c22)                 # mismos hiperparámetros base: solo cambia la capa
    plan = art.validar(ARTEFACTO_22, _escribir(tmp_path, _informe(c22)), menor=2)
    assert plan["version_modelo"] == f"tenis-2.2+{plan['sha256'][:12]}" and plan["sha256"] != art.validar(
        ARTEFACTO, _escribir(tmp_path, _informe(c21)))["sha256"]
    assert all(plan["capa_edad"][c]["beta"] < 0 and plan["capa_edad"][c]["pendiente"] > 0.9 for c in ("atp", "wta"))


def test_validar_rechaza_lo_que_no_debe_registrarse(tmp_path):
    contenido = hp.leer(ARTEFACTO)
    with pytest.raises(ValueError, match="no corresponde"):
        art.validar(ARTEFACTO, _escribir(tmp_path, _informe(contenido, base={"otro": 1})))
    with pytest.raises(ValueError, match="G_linea_base"):
        art.validar(ARTEFACTO, _escribir(tmp_path, _informe(contenido, pasa=False)))
    with pytest.raises(ValueError, match="G_capa_edad"):
        art.validar(ARTEFACTO, _escribir(tmp_path, _informe(contenido, capa=False)))
    alterado = tmp_path / "alterado.json"
    d = json.loads(ARTEFACTO.read_text(encoding="utf-8")); d["circuitos"]["atp"]["c_inf"] = 0.5
    alterado.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="alterado"):
        art.validar(alterado, _escribir(tmp_path, _informe(contenido)))


psycopg = pytest.importorskip("psycopg")
from db_util import cargar_minimo  # noqa: E402
from inferencia_util import partido_futuro, ranking  # noqa: E402
from tenis import motor  # noqa: E402


def _plan(tmp_path):
    contenido = hp.leer(ARTEFACTO)
    return art.validar(ARTEFACTO, _escribir(tmp_path, _informe(contenido)))


def test_registrar_anexa_exige_aprobacion_y_el_motor_lo_carga(esquema, tmp_path):
    plan = _plan(tmp_path)
    with esquema.conectar() as db:
        cargar_minimo(db)                                                   # ya hay un artefacto activo de prueba
        with pytest.raises(ValueError, match="OK del titular"):
            art.registrar(db, plan, "tenis-motor:v21", "  ")
        with pytest.raises(ValueError, match="tenis-motor"):
            art.registrar(db, plan, "v21", "OK en el chat")
        antes = db.execute("SELECT count(*) FROM artefacto_activo").fetchone()[0]
        res = art.registrar(db, plan, "tenis-motor:v21", "OK del titular 17-nov")
        assert res["sha256"] == plan["sha256"] and res["anterior"]["version_modelo"] == "v1"
        assert db.execute("SELECT count(*) FROM artefacto_activo").fetchone()[0] == antes + 1
        info = db.execute("SELECT informe_compuertas FROM artefacto WHERE sha256 = %s", (plan["sha256"],)).fetchone()[0]
        assert info["circuitos"]["atp"]["G_capa_edad"]["capa_activa"] is True
        with pytest.raises(ValueError, match="ya está activo"):
            art.registrar(db, plan, "tenis-motor:v21", "OK otra vez")
        carga = motor.cargar_artefacto_activo(db, ARTEFACTO.parent)         # la huella registrada coincide con el fichero de la imagen
        assert carga["sha256"] == plan["sha256"] and carga["parametros"]["circuitos"]["atp"]["capa_edad"]["beta"] < 0
        # vuelta atrás: otra fila que apunta al artefacto anterior; nunca un UPDATE
        previo = res["anterior"]["sha256"]
        vuelta = art.reactivar(db, previo, "tenis-motor:v1", "OK vuelta atrás")
        assert vuelta["sha256"] == previo and vuelta["anterior"]["sha256"] == plan["sha256"]
        with pytest.raises(ValueError, match="no está registrado"):
            art.reactivar(db, "f" * 64, "tenis-motor:v1", "OK")


def test_cargador_estricto_sin_fichero_con_esa_huella(esquema, tmp_path):
    with esquema.conectar() as db:
        cargar_minimo(db)                                                   # el artefacto activo es de prueba: no existe fichero
        shutil.copy(ARTEFACTO, tmp_path / "otro.json")                      # un JSON válido pero con OTRA huella NO se usa
        with pytest.raises(FileNotFoundError, match="huella"):
            motor.cargar_artefacto_activo(db, tmp_path)
        assert motor.ejecutar_pasada_motor(db, dry_run=True)["error"]      # sin artefacto verificable no se sella nada


def test_main_una_pasada_real_y_codigos_de_salida(esquema, tmp_path, monkeypatch, capsys):
    plan = _plan(tmp_path)
    monkeypatch.setattr(motor, "enviar_alerta", lambda *a, **k: {})
    monkeypatch.setenv("TENIS_ARTEFACTOS_DIR", str(ARTEFACTO.parent))
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        ranking(db, m["jugadores"][1], 80)
    args = ["--dry-run", "--dsn", esquema.dsn, "--esquema", esquema.nombre]
    assert motor.main(args) == 1                                            # el artefacto activo de prueba no tiene fichero
    assert "error" in capsys.readouterr().out
    with esquema.conectar() as db:
        art.registrar(db, plan, "tenis-motor:v21", "OK del titular")
    assert motor.main(args) == 0
    salida = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert salida["version_modelo"] == plan["version_modelo"] and salida["error"] is None
    assert motor.main(["--dry-run", "--dsn", esquema.dsn, "--esquema", "no valido!"]) == 1
