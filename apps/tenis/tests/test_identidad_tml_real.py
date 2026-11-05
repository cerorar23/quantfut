"""Identidad sobre TML real (un año cargado con el cargador de TML) y simulación de SofaScore.

- Verificación independiente: pandas calcula las parejas (circuito, nombre normalizado, país) con más de un id a partir
  del CSV, excluyendo las filas que el cargador rechazó antes de crear jugadores; debe coincidir con `medir`.
- Simulación: se generan registros de SofaScore a partir de jugadores reales de TML (fecha de nacimiento = fecha del
  torneo − edad de TML, con nombres en otro orden y con tildes, y algún ruido de días) y 20 homónimos inventados de
  otro país. Deben unirse los verdaderos, no unirse los homónimos y no haber uniones contradictorias.
"""
import csv
import random
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from db_util import nuevo_recibo, ts
from tenis.carga.tml_cli import ejecutar
from tenis.identidad import enlazar
from tenis.identidad.normalizar import nombre_clave
from tenis.identidad.resolver import ResolutorMultifuente

TML = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\full_20261016\tml\originals")
MANIFIESTO = TML.parents[1] / "download_manifest.json"
FICHEROS = ["2025.csv", "2025_wta.csv", "2026.csv", "2026_wta.csv"]   # 2026 trae los ids alternos 3xxxxx de WTA
RECIBIDO = "2026-01-05"


@pytest.fixture
def snap(tmp_path):
    """Carpeta con solo los ficheros de 2025 (los hashes siguen coincidiendo con el manifiesto)."""
    if not (TML / FICHEROS[0]).exists() or not MANIFIESTO.exists():
        pytest.skip("snapshot de TML no disponible")
    carpeta = tmp_path / "snap"
    carpeta.mkdir()
    for n in FICHEROS:
        shutil.copyfile(TML / n, carpeta / n)
    return carpeta


EQUIVALENCIAS_REPO = Path(__file__).resolve().parents[1] / "config" / "equivalencias.csv"


@pytest.fixture
def cargado(esquema, snap, tmp_path, dsn):
    """Carga con el cargador real y SIN equivalencias: cada id de TML queda con su propio jugador."""
    eq = tmp_path / "eq_vacio.csv"
    eq.write_text("fuente,id_alias,id_principal,evidencia\n", encoding="utf-8")
    res = ejecutar(snap, dsn, esquema.nombre, MANIFIESTO, tmp_path / "almacen", tmp_path / "rechazos.csv",
                   equivalencias=eq)
    assert res["cuadra"]
    return res


def _equivalencias_aplicables(snap, tmp_path) -> tuple[Path, int]:
    """Filas del repo que esta muestra puede aplicar: principal y alias presentes, y el principal en un fichero anterior.

    La carga completa aplica todo el CSV (el principal de 2007 existe antes de cualquier alias de 2026); una muestra de
    2025-2026 no tiene esos principales, y el cargador, con razón, se niega a cargar un alias sin principal.
    """
    from tenis.carga.tml_cli import _orden
    primero = {}
    for f in enlazar.filas_tml([snap / n for n in FICHEROS]):
        clave, orden = (f["circ"], f["id"]), _orden(f["fichero"])
        if clave not in primero or orden < primero[clave]:
            primero[clave] = orden
    ruta, n = tmp_path / "eq_aplicables.csv", 0
    with open(EQUIVALENCIAS_REPO, encoding="utf-8", newline="") as src, \
            open(ruta, "w", encoding="utf-8", newline="") as dst:
        escritor = csv.writer(dst)
        escritor.writerow(["fuente", "id_alias", "id_principal", "evidencia"])
        for r in csv.DictReader(src):
            if any((c, r["id_principal"]) in primero and (c, r["id_alias"]) in primero
                   and primero[(c, r["id_principal"])] < primero[(c, r["id_alias"])] for c in ("atp", "wta")):
                escritor.writerow([r["fuente"], r["id_alias"], r["id_principal"], r["evidencia"]])
                n += 1
    return ruta, n


@pytest.fixture(params=["sin_equivalencias", "con_equivalencias_del_repo"])
def cargado_sim(request, esquema, snap, tmp_path, dsn):
    """Igual que `cargado`, pero también con las equivalencias del repo que la muestra puede aplicar."""
    eq = tmp_path / "eq_vacio.csv"
    eq.write_text("fuente,id_alias,id_principal,evidencia\n", encoding="utf-8")
    etiqueta = request.param
    if request.param == "con_equivalencias_del_repo":
        eq, n = _equivalencias_aplicables(snap, tmp_path)
        etiqueta = f"repo_aplicables_{n}"
    res = ejecutar(snap, dsn, esquema.nombre, MANIFIESTO, tmp_path / "almacen", tmp_path / "rechazos_sim.csv",
                   equivalencias=eq)
    assert res["cuadra"]
    res["equivalencias"] = etiqueta
    return res


def _excluidas(ruta) -> set:
    """Filas (fichero, línea) que el cargador rechazó antes de crear sus jugadores."""
    salida = set()
    with open(ruta, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fila, motivo = int(r["fila"]), r["motivo"]
            if fila == 0 or motivo in ("partido_duplicado", "ranking_conflicto") or motivo.startswith("estadistica:"):
                continue
            salida.add((r["fichero"], fila))
    return salida


def test_parejas_con_varios_ids_coinciden_con_pandas(esquema, cargado, snap, tmp_path):
    import pandas as pd
    excluidas = _excluidas(tmp_path / "rechazos.csv")
    filas = []
    for nombre in FICHEROS:
        circ = "wta" if "_wta" in nombre else "atp"
        with open(snap / nombre, encoding="utf-8", newline="") as f:
            lector = csv.DictReader(f)
            for fila in lector:
                if (nombre, lector.line_num) in excluidas:
                    continue
                for lado in ("winner", "loser"):
                    filas.append((circ, fila[f"{lado}_id"].strip(), fila[f"{lado}_name"].strip(),
                                  fila[f"{lado}_ioc"].strip()))
    df = pd.DataFrame(filas, columns=["circ", "id", "nombre", "pais"])
    df = df[(df.id != "") & (df.nombre != "") & ~df.nombre.str.contains("/") & df.pais.str.fullmatch("[A-Z]{3}")]
    df = df.assign(nk=df.nombre.map(nombre_clave))
    conteo = df.groupby(["circ", "nk", "pais"]).id.nunique()
    esperado = set(conteo[conteo > 1].index)

    db = esquema.conectar()
    cur = db.cursor()
    obtenido = enlazar.pares_con_varios_jugadores(cur)
    assert len(esperado) > 0
    assert obtenido == esperado, (len(obtenido), len(esperado), sorted(obtenido ^ esperado)[:10])


def _persona_tml_con_edad(snap):
    """Jugadores reales de TML con país y una fila de edad válida: (circ, id, nombre, pais, fecha, edad)."""
    personas = {}
    for f in enlazar.filas_tml([snap / n for n in FICHEROS]):
        if not (14 <= (f["edad"] or 0) <= 50) or len(f["pais"]) != 3:
            continue
        personas.setdefault((f["circ"], f["id"]), (f["circ"], f["id"], f["nombre"], f["pais"], f["fecha"], f["edad"]))
    return personas


def _nombre_sofascore(nombre: str, rng: random.Random) -> str:
    partes = nombre.split()
    if len(partes) == 2 and rng.random() < 0.5:
        partes = partes[::-1]                       # «Apellido Nombre»
    unida = " ".join(partes)
    return unida.replace("e", "é", 1) if "e" in unida and rng.random() < 0.3 else unida   # con tilde


def test_simulacion_sofascore_une_verdaderos_y_separa_homonimos(esquema, cargado_sim, snap):
    rng = random.Random(20261105)
    db = esquema.conectar()
    cur = db.cursor()
    jid_de = {(c, i): j for c, i, j in _alias_tml(cur)}
    # Solo jugadores que el cargador creó: las filas rechazadas antes no tienen jugador.
    personas = {k: v for k, v in _persona_tml_con_edad(snap).items() if k in jid_de}
    claves = sorted(personas)
    elegidas = rng.sample(claves, 150)
    homonimos = rng.sample([c for c in claves if c not in elegidas], 20)
    filas = list(enlazar.filas_tml([snap / n for n in FICHEROS]))

    rid = nuevo_recibo(db, "sofascore", RECIBIDO)
    r = ResolutorMultifuente(db, edades=enlazar.edades_para_resolutor(cur, filas))

    verdaderos = []
    for n, clave in enumerate(elegidas):
        circ, id_, nombre, pais, fecha, edad = personas[clave]
        nac = fecha - timedelta(days=round(edad * 365.25) + (rng.randint(-60, 60) if n % 10 == 0 else 0))
        jid = r.resolver(fuente="sofascore", id_fuente=f"SS{n}", circuito=circ,
                         nombre=_nombre_sofascore(nombre, rng), fecha_nacimiento=nac.isoformat(), pais=pais,
                         mano=None, altura_cm=None, recibo_id=rid, recibido_en=ts(RECIBIDO))
        verdaderos.append((jid_de[clave], jid, r.ultimo))

    for n, clave in enumerate(homonimos):
        circ, id_, nombre, _, fecha, _ = personas[clave]
        r.resolver(fuente="sofascore", id_fuente=f"HM{n}", circuito=circ, nombre=nombre,
                   fecha_nacimiento=(fecha - timedelta(days=9000)).isoformat(), pais="XKX",
                   mano=None, altura_cm=None, recibo_id=rid, recibido_en=ts(RECIBIDO))
        assert r.ultimo == ("nuevo", "confirmado_distinto"), (nombre, r.ultimo)
        assert jid_de[clave] != _jid_de_hm(cur, n)

    uniones_ok = sum(1 for esperado, obtenido, ult in verdaderos if obtenido == esperado)
    uniones_mal = [(e, o, u) for e, o, u in verdaderos if u[0] not in ("nuevo", "existente") and o != e]
    assert not uniones_mal, uniones_mal[:5]
    assert uniones_ok >= 0.9 * len(elegidas), (uniones_ok, len(elegidas))

    medido = enlazar.medir(cur, fuente="sofascore")
    print(f"\nSIMULACION equivalencias={cargado_sim['equivalencias']} verdaderos={len(elegidas)} unidos_ok={uniones_ok} "
          f"motivos_no_unidos={[u for e, o, u in verdaderos if o != e]} homonimos=20")
    print(f"MEDIDO {medido}")
    assert medido["uniones_contradictorias"] == 0
    assert medido["homonimos_confirmados"] == 20
    assert medido["unidos_a_referencia"] == uniones_ok

    antes = db.execute("SELECT count(*) FROM jugador_alias").fetchone()[0]
    r2 = ResolutorMultifuente(db, edades=enlazar.edades_para_resolutor(cur, filas))
    for n, clave in enumerate(elegidas):
        circ, id_, nombre, pais, fecha, edad = personas[clave]
        r2.resolver(fuente="sofascore", id_fuente=f"SS{n}", circuito=circ, nombre=nombre, fecha_nacimiento=None,
                    pais=pais, mano=None, altura_cm=None, recibo_id=rid, recibido_en=ts(RECIBIDO))
    assert db.execute("SELECT count(*) FROM jugador_alias").fetchone()[0] == antes


def _alias_tml(cur):
    cur.execute("SELECT j.circuito, a.id_fuente, a.jugador_id FROM jugador_alias a JOIN jugador j "
                "ON j.jugador_id = a.jugador_id WHERE a.fuente = 'tml' AND NOT EXISTS "
                "(SELECT 1 FROM jugador_alias x WHERE x.anula_a = a.alias_id)")
    return cur.fetchall()


def _jid_de_hm(cur, n):
    cur.execute("SELECT jugador_id FROM jugador_alias WHERE fuente = 'sofascore' AND id_fuente = %s", (f"HM{n}",))
    return cur.fetchone()[0]
