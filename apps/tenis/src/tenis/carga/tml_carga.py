"""Pipeline de la carga TML: pasada 1 (valores de torneo y edición) y pasada 2 (escritura por fichero).

Cada fichero es una transacción: si el proceso cae, repetir la carga es idempotente (claves naturales y ON CONFLICT).
Todo lo no cargado queda en el CSV de rechazos con su motivo; los contadores cuadran: leídas = cargadas + rechazadas
+ duplicadas + dobles.
"""
import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from tenis.recibo import nuevo_recibo

from . import tml_escritor as w
from .tml_agregado import Agregado
from .tml_orientar import orientar
from .tml_parseo import analizar_fila
from .tml_reglas import fecha_fin, inicio_visible, lunes_semana_fin


@dataclass
class Fichero:
    nombre: str
    raw: bytes
    entrada: dict | None     # fila del manifiesto
    motivo: str | None       # no None = fichero rechazado entero


def filas(raw: bytes):
    lector = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    for fila in lector:
        yield fila, lector.line_num


class Rechazos:
    """CSV de rechazos y conflictos: fichero, fila, motivo, valores clave."""

    def __init__(self, ruta):
        self._f = open(ruta, "w", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        self._w.writerow(["fichero", "fila", "motivo", "valores"])

    def add(self, fichero: str, fila: int, motivo: str, valores: str = "") -> None:
        self._w.writerow([fichero, fila, motivo, valores])

    def cerrar(self) -> None:
        self._f.close()


def _valores(fila: dict) -> str:
    return f"tourney_id={fila.get('tourney_id', '')};round={fila.get('round', '')};score={fila.get('score', '')}"


def _pasada_agregados(ficheros: list[Fichero], rechazos: Rechazos) -> Agregado:
    agg = Agregado()
    for f in ficheros:
        if f.motivo is None:
            for fila, _ in filas(f.raw):
                a = analizar_fila(fila, f.nombre)
                if not a.doble and a.motivo is None:
                    agg.sumar(a)
    for conflicto in agg.finalizar():
        rechazos.add("(agregado)", 0, conflicto.split(";")[0], conflicto)
    return agg


def _torneos_ediciones(cur, ok, agg, tor, edi, rid, rec_dt) -> None:
    nuevos_t = {}
    for _, a in ok:
        k = (a.circuito, a.clave)
        if k not in tor and k not in nuevos_t:
            t = agg.torneos[k]
            nuevos_t[k] = {"circuito": a.circuito, "clave": a.clave, "nombre": t["nombre"] or a.clave,
                           "categoria": t["categoria"], "recibo_id": rid, "recibido_en": rec_dt}
    tor.update(w.insertar_torneos(cur, list(nuevos_t.values())))
    nuevas = {}
    for _, a in ok:
        ek = (tor[(a.circuito, a.clave)], a.anio)
        if ek not in edi and ek not in nuevas:
            e = agg.ediciones[(a.circuito, a.clave, a.anio)]
            nuevas[ek] = {"torneo_id": ek[0], "temporada": a.anio,
                          "lunes_semana": lunes_semana_fin(e["inicio"], e["dias"]),
                          "fecha_fin": fecha_fin(e["inicio"], e["dias"]), "superficie": e["superficie"],
                          "indoor": e["indoor_v"], "por_equipos": e["equipos"], "recibo_id": rid,
                          "recibido_en": rec_dt, "visible_desde": inicio_visible(e["inicio"])}
    edi.update(w.insertar_ediciones(cur, list(nuevas.values())))


def _jugadores(cur, ok, jug, equivalencias, rid, rec_dt) -> None:
    pendientes = {}
    for _, a in ok:
        for s in (0, 1):
            k = (a.circuito, a.ids[s])
            if k not in jug and k not in pendientes:
                pendientes[k] = a.nombres[s]
    for (circ, id_), nombre in list(pendientes.items()):
        if id_ in equivalencias:
            principal = equivalencias[id_]
            jid = jug.get((circ, principal))
            if jid is None:
                # El principal aún no se ha cargado (aparece en un fichero posterior): se crea ahora con el nombre
                # del alias (es la misma persona por la equivalencia) y sus propias filas lo completarán después.
                # Antes esto era un error; así nunca se parte a una persona en dos.
                jid = w.crear_jugadores(cur, [(circ, principal, nombre)], rid, rec_dt)[0]
                jug[(circ, principal)] = jid
                pendientes.pop((circ, principal), None)
            w.alias(cur, id_, jid, rid, rec_dt)
            jug[(circ, id_)] = jid
            del pendientes[(circ, id_)]
    lista = [(c, i, n) for (c, i), n in pendientes.items()]
    ids = w.crear_jugadores(cur, lista, rid, rec_dt)
    jug.update({(c, i): j for (c, i, _), j in zip(lista, ids)})


def _aserciones(cur, ok, jug, ult, rid, rec_dt) -> None:
    nuevas = []
    for _, a in ok:
        for s in (0, 1):
            j = jug[(a.circuito, a.ids[s])]
            for campo, v in (("nombre", a.nombres[s]), ("mano", a.manos[s]),
                             ("altura_cm", a.alturas[s]), ("pais", a.paises[s])):
                if v and ult.get((j, campo)) != v:
                    ult[(j, campo)] = v
                    nuevas.append((j, campo, v))
    w.asercion(cur, nuevas, rid, rec_dt)


def _escribir_partidos(cur, orient, cont, rechazos, f, visto, rid, rec_dt) -> None:
    """Escribe partido, resultado y estadísticas de la primera aparición de cada partido (la primera gana)."""
    nuevos, claves = [], []
    for linea, a, o in orient:
        p = o["partido"]
        k = (p["edicion_id"], p["ronda"], p["jugador_1"], p["jugador_2"])
        if k in visto:
            cont["duplicado"] += 1
            rechazos.add(f.nombre, linea, "partido_duplicado", f"{a.circuito};{a.clave};{a.anio};{a.ronda}")
            continue
        visto.add(k)
        cont["cargado"] += 1
        nuevos.append({**p, "recibo_id": rid, "recibido_en": rec_dt})
        claves.append((k, o))
    mapa = w.partidos(cur, nuevos)
    res, est = [], []
    for k, o in claves:
        pid = mapa[k]
        res.append({**o["resultado"], "partido_id": pid, "recibo_id": rid, "recibido_en": rec_dt})
        est += [{**e, "partido_id": pid, "recibo_id": rid, "recibido_en": rec_dt} for e in o["estadisticas"]]
    w.resultados(cur, res)
    w.estadisticas(cur, est)


def _ranking(cur, orient, rk, cont, rechazos, f, rid, rec_dt) -> None:
    filas_rk = []
    for linea, a, o in orient:
        for lunes, jug_id, pos, pts in o["ranking"]:
            clave = (a.circuito, lunes, jug_id)
            if clave not in rk:
                rk[clave] = (pos, pts)
                filas_rk.append({"circuito": a.circuito, "fecha_publicacion": lunes, "jugador_id": jug_id,
                                 "posicion": pos, "puntos": pts, "recibo_id": rid, "recibido_en": rec_dt,
                                 "visible_desde": inicio_visible(lunes)})
            elif rk[clave] != (pos, pts):
                cont["conflicto_ranking"] += 1
                rechazos.add(f.nombre, linea, "ranking_conflicto", f"{clave[0]};{lunes};{jug_id}")
    w.ranking(cur, filas_rk)


def cargar(conn, ficheros: list[Fichero], almacen, lote: str, rechazos: Rechazos, equivalencias: dict) -> Counter:
    cont: Counter = Counter()
    agg = _pasada_agregados(ficheros, rechazos)
    cur = conn.cursor()
    jug, tor, edi = w.jugadores_existentes(cur), w.torneos_existentes(cur), w.ediciones_existentes(cur)
    visto, rk, ult = set(), {}, {}
    for f in ficheros:
        if f.motivo is not None:
            for _ in filas(f.raw):
                cont["leidas"] += 1
                cont[f"rechazo:{f.motivo}"] += 1
            rechazos.add(f.nombre, 0, f.motivo, "fichero entero rechazado")
            continue
        rec_dt = datetime.fromisoformat(f.entrada["received_at"])
        rec = nuevo_recibo(almacen, fuente="tml", recurso=f.nombre, parametros={}, recibido_en=rec_dt,
                           cuerpo=f.raw, retro=True, extension=".csv.gz")
        rid = w.recibo(cur, {**rec.model_dump(exclude={"retro"}), "lote": lote})
        ok = []
        for fila, linea in filas(f.raw):
            cont["leidas"] += 1
            a = analizar_fila(fila, f.nombre)
            if a.doble:
                cont["doble"] += 1
                continue
            if a.motivo is not None:
                cont[f"rechazo:{a.motivo}"] += 1
                rechazos.add(f.nombre, linea, a.motivo, _valores(fila))
                continue
            for av in a.avisos:
                cont[f"aviso:{av}"] += 1
            if a.stat_motivo is not None:
                cont[f"estadistica:{a.stat_motivo}"] += 1
                rechazos.add(f.nombre, linea, f"estadistica:{a.stat_motivo}", _valores(fila))
            ok.append((linea, a))
        _torneos_ediciones(cur, ok, agg, tor, edi, rid, rec_dt)
        _jugadores(cur, ok, jug, equivalencias, rid, rec_dt)
        _aserciones(cur, ok, jug, ult, rid, rec_dt)
        orient = []
        for linea, a in ok:
            e = agg.ediciones[(a.circuito, a.clave, a.anio)]
            ed = edi[(tor[(a.circuito, a.clave)], a.anio)]
            orient.append((linea, a, orientar(a, jug[(a.circuito, a.ids[0])], jug[(a.circuito, a.ids[1])],
                                              ed, e["inicio"], e["dias"], frozenset(e["rondas"]))))
        _escribir_partidos(cur, orient, cont, rechazos, f, visto, rid, rec_dt)
        _ranking(cur, orient, rk, cont, rechazos, f, rid, rec_dt)
        conn.commit()
    return cont
