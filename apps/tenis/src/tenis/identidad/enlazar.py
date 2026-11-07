"""Medición del enlace entre fuentes ya cargadas (plan B.1) y lectura de las edades de TML.

No resuelve nada: `medir` solo lee la base. Las edades de TML no se guardan en la evidencia (el cargador no las
persiste), así que `edades_para_resolutor` las reconstruye desde los CSV, pasando por los alias de TML ya cargados.
"""
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from tenis.carga.tml_parseo import analizar_fila

from .normalizar import nombre_clave

EDAD_MIN, EDAD_MAX = 14, 50          # fuera de este rango, la edad de TML es basura (p. ej. 3387 años en ids alternos)
_VIGENTE = ("SELECT a.fuente, a.id_fuente, a.jugador_id, a.metodo FROM jugador_alias a "
            "WHERE NOT EXISTS (SELECT 1 FROM jugador_alias x WHERE x.anula_a = a.alias_id)")


def edad_valida(valor) -> bool:
    return valor is not None and EDAD_MIN <= valor <= EDAD_MAX


def filas_tml(rutas: list[Path]):
    """Una fila por jugador y partido ACEPTADO por el cargador de TML: circuito, id, nombre, país, fecha, edad y fichero.

    Las filas que el cargador rechaza (o son dobles) no crean jugador; si se contaran, un principal podría parecer
    cargado antes de existir. Por eso se usa su mismo análisis (`analizar_fila`).
    """
    for ruta in rutas:
        circuito = "wta" if "_wta" in ruta.name else "atp"
        with open(ruta, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                a = analizar_fila(fila, ruta.name)
                if a.doble or a.motivo is not None:
                    continue
                fecha = date(int(fila["tourney_date"][:4]), int(fila["tourney_date"][4:6]), int(fila["tourney_date"][6:8]))
                for lado in ("winner", "loser"):
                    nombre = fila[f"{lado}_name"].strip()
                    id_ = fila[f"{lado}_id"].strip()
                    if not nombre or not id_ or "/" in nombre:
                        continue
                    edad = fila[f"{lado}_age"].strip()
                    yield {"circ": circuito, "id": id_, "nombre": nombre, "pais": fila[f"{lado}_ioc"].strip(),
                           "fecha": fecha, "edad": float(edad) if edad else None, "fichero": ruta.name}


def edades_para_resolutor(cur, filas) -> callable:
    """Función `edades(jugador_id)` para el resolutor, a partir de filas de TML y los alias 'tml' vigentes."""
    cur.execute(_VIGENTE + " AND a.fuente = 'tml'")
    mapa = {id_: jid for _, id_, jid, _ in cur.fetchall()}
    cur.execute("SELECT jugador_id, circuito FROM jugador")
    circ_de = dict(cur.fetchall())
    datos = defaultdict(list)
    for f in filas:
        if not edad_valida(f["edad"]):
            continue
        jid = mapa.get(f["id"])
        if jid is not None and circ_de.get(jid) == f["circ"]:
            datos[jid].append((f["fecha"], f["edad"]))
    return lambda jugador_id: datos.get(jugador_id, ())


def medir(cur, *, fuente: str = "sofascore", referencia: str = "tml") -> dict:
    """Mide el enlace de `fuente` con `referencia` sobre lo cargado. Solo lectura."""
    cur.execute(f"SELECT fuente, id_fuente, jugador_id, metodo FROM ({_VIGENTE}) v WHERE v.fuente = %s", (fuente,))
    vigentes = cur.fetchall()
    ids = {r[1] for r in vigentes}
    cur.execute(f"SELECT DISTINCT v.jugador_id FROM ({_VIGENTE}) v WHERE v.fuente = %s", (referencia,))
    jug_ref = {r[0] for r in cur.fetchall()}
    unidos = {r[1] for r in vigentes if r[2] in jug_ref}
    metodos = Counter(r[3] for r in vigentes)
    cur.execute("SELECT motivo, count(DISTINCT id_fuente) FROM sin_resolver WHERE fuente = %s GROUP BY motivo", (fuente,))
    sin = dict(cur.fetchall())
    cur.execute("SELECT count(*) FROM (SELECT id_fuente FROM ({v}) v WHERE v.fuente = %s "
                "GROUP BY id_fuente HAVING count(DISTINCT v.jugador_id) > 1) c".format(v=_VIGENTE), (fuente,))
    contradictorios = cur.fetchone()[0]
    pares = pares_con_varios_jugadores(cur, referencia, jug_ref)
    cur.execute("SELECT DISTINCT id_fuente FROM sin_resolver WHERE fuente = %s", (fuente,))
    ids_sin = {r[0] for r in cur.fetchall()}
    total = len(ids)
    return {
        "fuente": fuente, "referencia": referencia,
        "ids_fuente": total, "jugadores_fuente": len({r[2] for r in vigentes}),
        "unidos_a_referencia": len(unidos), "tasa_unidos": round(len(unidos) / total, 4) if total else None,
        "metodos": dict(metodos), "sin_resolver_motivos_ids": sin,
        "tasa_sin_resolver": round(len(ids & ids_sin) / total, 4) if total else None,
        "homonimos_confirmados": sin.get("confirmado_distinto", 0),
        "uniones_contradictorias": contradictorios,
        "pares_referencia_nombre_pais_varios_jugadores": len(pares), "pares_detalle": sorted(pares),
    }


def pares_con_varios_jugadores(cur, referencia: str = "tml", jugadores=None) -> set:
    """(circuito, nombre normalizado, país) con más de un jugador de la referencia. Se compara con pandas en la prueba."""
    if jugadores is None:
        cur.execute(f"SELECT DISTINCT v.jugador_id FROM ({_VIGENTE}) v WHERE v.fuente = %s", (referencia,))
        jugadores = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT j.jugador_id, j.circuito, a.campo, a.valor FROM jugador_asercion a "
                "JOIN jugador j ON j.jugador_id = a.jugador_id "
                "WHERE a.fuente = %s AND a.campo IN ('nombre', 'pais')", (referencia,))
    nombres, paises, circ = defaultdict(set), defaultdict(set), {}
    for jid, c, campo, valor in cur.fetchall():
        if jid not in jugadores:
            continue
        circ[jid] = c
        (nombres if campo == "nombre" else paises)[jid].add(valor)
    grupos = defaultdict(set)
    for jid in jugadores:
        for n in nombres.get(jid, ()):
            for p in paises.get(jid, ()):
                grupos[(circ[jid], nombre_clave(n), p)].add(jid)
    return {k for k, v in grupos.items() if len(v) > 1}


def csv_auditoria(cur, ruta: Path, fuente: str = "sofascore", referencia: str = "tml") -> int:
    """Una fila por id de `fuente`: jugador, método, motivo de cola y si está unido a la referencia."""
    cur.execute(f"SELECT v.id_fuente, v.jugador_id, v.metodo, j.circuito FROM ({_VIGENTE}) v "
                "JOIN jugador j ON j.jugador_id = v.jugador_id WHERE v.fuente = %s ORDER BY v.id_fuente", (fuente,))
    vig = cur.fetchall()
    cur.execute(f"SELECT DISTINCT v.jugador_id FROM ({_VIGENTE}) v WHERE v.fuente = %s", (referencia,))
    jug_ref = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT id_fuente, motivo FROM sin_resolver WHERE fuente = %s ORDER BY sin_id", (fuente,))
    motivo = {}
    for id_, m in cur.fetchall():
        motivo[id_] = m
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fuente", "id_fuente", "jugador_id", "circuito", "metodo", "motivo_cola", "unido_a_referencia"])
        for id_, jid, met, circ in vig:
            w.writerow([fuente, id_, jid, circ, met, motivo.get(id_, ""), jid in jug_ref])
    return len(vig)
