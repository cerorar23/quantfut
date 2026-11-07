"""Carga de SofaScore (tenis, evidencia RETRO) desde el archivo local, en dos pasadas.

Pasada 1: analiza el JSON de cada evento sin estadística ni punto a punto; decide rechazo/exclusión (la decisión es la
misma que en la pasada 2, porque la estadística y el punto a punto solo añaden avisos) y acumula torneos y ediciones
(primer valor en orden de inicio; cada valor distinto queda como conflicto).
Pasada 2: por lotes, una transacción por lote: recibos (un original por fichero cargado), torneos, ediciones,
jugadores (resolutor inyectable), partidos nuevos, programa, resultado, estadística y punto a punto.

Cada evento cuenta en una sola categoría: leídos = cargados + ya_cargado + rechazos + excluidos + duplicados.
Los avisos (informativos, p. ej. punto a punto no derivable) van al CSV con `tipo = aviso` y no son descartes.
"""
import csv
import gzip
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tenis.recibo import nuevo_recibo

from . import sofascore_escritor as w
from . import sofascore_reglas as r
from .sofascore_parseo import analizar, resumen
from .sofascore_resolutor import ResolutorPorId

FUENTE = "sofascore"
TAMANO_LOTE = 250
CABECERA_RECHAZOS = ["tipo", "recurso", "evento_id", "motivo", "valores"]
SIN_FECHA = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Entrada:
    """Un evento del índice: rutas relativas a la raíz del archivo y la hora de observación (recibido_en)."""
    evento_id: int
    recurso: str
    observado: datetime
    sha_indice: str | None
    recurso_estadistica: str | None
    recurso_pbp: str | None
    motivo_sin_datos: str | None = None


def leer_indice(ruta_csv: Path) -> list[Entrada]:
    """Una entrada por fila del índice de tenis. Las filas sin event.json u observación se marcan para excluir."""
    entradas = []
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            ficheros = set((fila.get("ficheros_evento") or "").split(";"))
            carpeta = fila["archivo_origen"].rsplit("/", 1)[0]
            motivo = None
            if fila["fuente_evento"] != "events" or fila["carpeta_evento_existe"] != "True" \
                    or "event.json.gz" not in ficheros:
                motivo = "sin_event_json"
            elif not fila["observed_at_utc"]:
                motivo = "sin_observacion"
            entradas.append(Entrada(
                evento_id=int(fila["event_id"]), recurso=f"{carpeta}/event.json.gz",
                observado=datetime.fromisoformat(fila["observed_at_utc"]) if fila["observed_at_utc"] else SIN_FECHA,
                sha_indice=fila["sha256_event_json"] or None,
                recurso_estadistica=f"{carpeta}/statistics.json.gz" if "statistics.json.gz" in ficheros else None,
                recurso_pbp=f"{carpeta}/point_by_point.json.gz" if "point_by_point.json.gz" in ficheros else None,
                motivo_sin_datos=motivo))
    return entradas


def leer_gz_desde(raiz: Path):
    """Lector real: bytes descomprimidos del fichero `rel` bajo `raiz`."""
    def leer(rel: str) -> bytes:
        return gzip.decompress((raiz / rel).read_bytes())
    return leer


class _Rechazos:
    def __init__(self, ruta: Path | None):
        self._f = open(ruta, "w", newline="", encoding="utf-8") if ruta else None
        self._w = csv.writer(self._f) if self._f else None
        if self._w:
            self._w.writerow(CABECERA_RECHAZOS)

    def add(self, tipo: str, recurso: str, evento_id, motivo: str, valores: str = "") -> None:
        if self._w:
            self._w.writerow([tipo, recurso, evento_id, motivo, valores])

    def cerrar(self) -> None:
        if self._f:
            self._f.close()


class _Agregado:
    """Torneos y ediciones. Primer valor en orden de inicio; cada valor distinto queda como conflicto."""

    def __init__(self, rechazos: _Rechazos):
        self.torneos: dict = {}
        self.ediciones: dict = {}
        self._rechazos = rechazos

    def sumar(self, rs: dict, recurso: str, evento_id: int) -> None:
        t = self.torneos.setdefault((rs["circuito"], rs["clave"]), {"nombre": rs["nombre"], "cats": []})
        if rs["categoria"] not in t["cats"]:
            t["cats"].append(rs["categoria"])
        clave = (rs["circuito"], rs["clave"], rs["temporada"])
        dia = r.dia_utc(rs["inicio_partido"])
        e = self.ediciones.get(clave)
        if e is None:
            self.ediciones[clave] = {"inicio_torneo": rs["inicio_torneo"], "fin_torneo": rs["fin_torneo"],
                                     "superficie": rs["superficie"], "indoor": rs["indoor"],
                                     "equipos": rs["equipos"], "max_fecha": dia}
            return
        # Inicio y fin de la edición: el clasificatorio y el cuadro principal traen fechas de torneo distintas
        # (12.680 conflictos medidos). Se toma el MÍNIMO de inicios y el MÁXIMO de fines (nunca un fin anterior al
        # último partido: el fin alimenta la regla retro por semana).
        for campo, elegir in (("inicio_torneo", min), ("fin_torneo", max)):
            valor = rs[campo]
            if valor is not None:
                e[campo] = valor if e[campo] is None else elegir(e[campo], valor)
        for campo in ("superficie", "indoor"):
            valor = rs[campo]
            if e[campo] is None and valor is not None:
                e[campo] = valor
            elif valor is not None and e[campo] != valor:
                self._rechazos.add("conflicto", recurso, evento_id, f"edicion_conflicto:{campo}",
                                   f"{clave};{e[campo]}!={valor}")
        e["max_fecha"] = max(e["max_fecha"], dia)

    def categoria_torneo(self, clave_t) -> str | None:
        cats = self.torneos[clave_t]["cats"]
        return cats[0] if len(cats) == 1 else None

    def conflictos_torneo(self, recurso_por_torneo: dict) -> None:
        for clave_t, t in self.torneos.items():
            if len(t["cats"]) > 1:
                self._rechazos.add("conflicto", recurso_por_torneo.get(clave_t, ""), "", "categoria_conflicto",
                                   f"{clave_t};{'|'.join(map(str, t['cats']))}")


def _fecha_fin(e: dict):
    """Fin de la edición: fin del torneo (UTC) o el último partido + 1 día si falta."""
    ultimo_partido = e["max_fecha"] + timedelta(days=1)
    if e["fin_torneo"] is not None:
        return max(r.dia_utc(e["fin_torneo"]), ultimo_partido)   # nunca antes del último partido + 1 día
    return ultimo_partido


def _lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def _lote(observado: datetime) -> str:
    return "sofascore_" + observado.astimezone(timezone.utc).strftime("%Y%m%d")


def _canon(lado_local: int, invertido: bool) -> int:
    return 3 - lado_local if invertido else lado_local


def _sets_canon(sets, invertido: bool):
    if sets is None or not invertido:
        return sets
    return [[gv, gl, tbv, tbl] for (gl, gv, tbl, tbv) in sets]


def _recibo_dict(recurso: str, cuerpo: bytes, observado: datetime, almacen: Path, lote: str) -> dict:
    rec = nuevo_recibo(almacen, fuente=FUENTE, recurso=recurso, parametros={}, recibido_en=observado,
                       cuerpo=cuerpo, retro=True)
    return {**rec.model_dump(exclude={"retro", "parametros", "estado_http"}), "lote": lote}


def cargar(conn, entradas: list[Entrada], leer, almacen: Path, rechazos_ruta: Path | None = None,
           tamano_lote: int = TAMANO_LOTE, fabrica_resolutor=None) -> Counter:
    """Carga los eventos de `entradas` con la conexión `conn` (search_path ya fijado). `leer(recurso) -> bytes`
    devuelve el contenido descomprimido. Devuelve los contadores (ver el encabezado del módulo).

    `fabrica_resolutor(conn) -> resolutor` permite inyectar el resolutor multifuente (une jugadores con los de TML);
    sin él se usa `ResolutorPorId` (un jugador por id de SofaScore, sin unión entre fuentes)."""
    rechazos = _Rechazos(rechazos_ruta)
    cont: Counter = Counter()
    cont["leidas"] = len(entradas)
    vistos_evento: set[int] = set()
    candidatos = []
    agg = _Agregado(rechazos)
    recurso_torneo: dict = {}

    # Pasada 1: decisión por evento y agregados de torneo y edición.
    for e in entradas:
        if e.motivo_sin_datos:
            cont[f"excluido:{e.motivo_sin_datos}"] += 1
            rechazos.add("excluido", e.recurso, e.evento_id, e.motivo_sin_datos)
            continue
        if e.evento_id in vistos_evento:
            cont["duplicado:evento"] += 1
            rechazos.add("duplicado", e.recurso, e.evento_id, "evento_duplicado")
            continue
        vistos_evento.add(e.evento_id)
        cuerpo = leer(e.recurso)
        if e.sha_indice and hashlib.sha256(cuerpo).hexdigest() != e.sha_indice:
            cont["rechazo:sha_indice_no_coincide"] += 1
            rechazos.add("rechazo", e.recurso, e.evento_id, "sha_indice_no_coincide")
            continue
        ev = json.loads(cuerpo)
        a = analizar(ev, None, None)
        if a["excluido"]:
            cont[f"excluido:{a['excluido']}"] += 1
            rechazos.add("excluido", e.recurso, e.evento_id, a["excluido"])
            continue
        if a["rechazo"]:
            cont[f"rechazo:{a['rechazo']}"] += 1
            rechazos.add("rechazo", e.recurso, e.evento_id, a["rechazo"])
            continue
        rs = resumen(ev)
        candidatos.append((rs["inicio_partido"], e.evento_id, e, rs))
    candidatos.sort(key=lambda c: (c[0], c[1]))
    for _, evento_id, e, rs in candidatos:
        agg.sumar(rs, e.recurso, evento_id)
        recurso_torneo.setdefault((rs["circuito"], rs["clave"]), e.recurso)
    agg.conflictos_torneo(recurso_torneo)

    cur = conn.cursor()
    resolutor = fabrica_resolutor(conn) if fabrica_resolutor is not None else ResolutorPorId(cur, FUENTE)
    cur.execute("SELECT torneo_id, circuito, clave FROM torneo")
    tor = {(c, k): t for (t, c, k) in cur.fetchall()}
    edi = w.ediciones_existentes(cur)
    visto_partido: set = set()
    conn.commit()

    # Pasada 2: escritura por lotes.
    for ini in range(0, len(candidatos), tamano_lote):
        aceptados = []
        for _, _, e, _ in candidatos[ini: ini + tamano_lote]:
            cuerpo = leer(e.recurso)
            ev = json.loads(cuerpo)
            cuerpo_est = leer(e.recurso_estadistica) if e.recurso_estadistica else None
            cuerpo_pbp = leer(e.recurso_pbp) if e.recurso_pbp else None
            est = json.loads(cuerpo_est) if cuerpo_est is not None else None
            pbp = json.loads(cuerpo_pbp) if cuerpo_pbp is not None else None
            a = analizar(ev, est, pbp)
            for av in a["avisos"]:
                cont[f"aviso:{av.split(':')[0]}"] += 1
                rechazos.add("aviso", e.recurso, e.evento_id, av)
            if a["rechazo"]:
                cont[f"rechazo:{a['rechazo']}"] += 1
                rechazos.add("rechazo", e.recurso, e.evento_id, a["rechazo"])
                continue
            aceptados.append((e, a, cuerpo, cuerpo_est, cuerpo_pbp))
        if not aceptados:
            continue

        # Recibos: un original por fichero cargado.
        escritos = []
        for e, a, cuerpo, cuerpo_est, cuerpo_pbp in aceptados:
            lote = _lote(e.observado)
            rid = w.recibo(cur, _recibo_dict(e.recurso, cuerpo, e.observado, almacen, lote))
            rid_est = rid_pbp = None
            if cuerpo_est is not None:
                rid_est = w.recibo(cur, _recibo_dict(e.recurso_estadistica, cuerpo_est, e.observado, almacen, lote))
            if cuerpo_pbp is not None:
                rid_pbp = w.recibo(cur, _recibo_dict(e.recurso_pbp, cuerpo_pbp, e.observado, almacen, lote))
            escritos.append((e, a, rid, rid_est, rid_pbp))

        # Torneos y ediciones nuevos: el recibo es el del primer evento del lote que los trae.
        nuevos_t: dict = {}
        for e, a, rid, _, _ in escritos:
            kt = (a["torneo"]["circuito"], a["torneo"]["clave"])
            if kt not in tor and kt not in nuevos_t:
                nuevos_t[kt] = {"circuito": kt[0], "clave": kt[1],
                                "nombre": agg.torneos[kt]["nombre"] or kt[1],
                                "categoria": agg.categoria_torneo(kt), "recibo_id": rid,
                                "recibido_en": e.observado}
        tor.update(w.torneos(cur, list(nuevos_t.values())))
        nuevas_e: dict = {}
        for e, a, rid, _, _ in escritos:
            kt = (a["torneo"]["circuito"], a["torneo"]["clave"])
            ke = (tor[kt], a["edicion"]["temporada"])
            if ke not in edi and ke not in nuevas_e:
                ag = agg.ediciones[(kt[0], kt[1], a["edicion"]["temporada"])]
                fin = _fecha_fin(ag)
                visible = (datetime.fromtimestamp(ag["inicio_torneo"], tz=timezone.utc) - timedelta(days=7)
                           if ag["inicio_torneo"] is not None else None)
                nuevas_e[ke] = {"torneo_id": ke[0], "temporada": ke[1], "lunes_semana": _lunes_de(fin),
                                "fecha_fin": fin, "superficie": ag["superficie"], "indoor": ag["indoor"],
                                "por_equipos": ag["equipos"], "recibo_id": rid, "recibido_en": e.observado,
                                "visible_desde": visible}
        edi.update(w.ediciones(cur, list(nuevas_e.values())))

        # Jugadores, orientación canónica y partidos.
        pendientes, filas_p = [], []
        for e, a, rid, rid_est, rid_pbp in escritos:
            kt = (a["torneo"]["circuito"], a["torneo"]["clave"])
            ed = edi[(tor[kt], a["edicion"]["temporada"])]
            ids = []
            for lado in ("local", "visitante"):
                j = a["jugadores"][lado]
                ids.append(resolutor.resolver(
                    fuente=FUENTE, id_fuente=j["id_fuente"], circuito=a["circuito"], nombre=j["nombre"],
                    fecha_nacimiento=j["fecha_nacimiento"], pais=j["pais"], mano=j["mano"],
                    altura_cm=j["altura_cm"], recibo_id=rid, recibido_en=e.observado,
                    contexto={"evento": e.evento_id}))
            jl, jv = ids
            if jl == jv:
                cont["rechazo:mismo_jugador"] += 1
                rechazos.add("rechazo", e.recurso, e.evento_id, "mismo_jugador")
                continue
            invertido = jl > jv
            j1, j2 = (jv, jl) if invertido else (jl, jv)
            clave = (ed, a["partido"]["ronda"], j1, j2)
            if clave in visto_partido:
                cont["duplicado:partido"] += 1
                rechazos.add("duplicado", e.recurso, e.evento_id, "partido_duplicado",
                             f"{a['circuito']};{kt[1]};{a['partido']['ronda']}")
                continue
            visto_partido.add(clave)
            pendientes.append((clave, e, a, rid, rid_est, rid_pbp, invertido))
            filas_p.append({"edicion_id": ed, "ronda": a["partido"]["ronda"], "jugador_1": j1, "jugador_2": j2,
                            "mejor_de": a["partido"]["mejor_de"], "recibo_id": rid, "recibido_en": e.observado,
                            "visible_desde": a["partido"]["visible_desde"]})

        existentes = w.partidos_existentes(cur, list({f["edicion_id"] for f in filas_p}))
        nuevas = [f for f in filas_p if (f["edicion_id"], f["ronda"], f["jugador_1"], f["jugador_2"])
                  not in existentes]
        claves_nuevas = {(f["edicion_id"], f["ronda"], f["jugador_1"], f["jugador_2"]) for f in nuevas}
        ids_partido = {**existentes, **w.partidos(cur, nuevas)}

        filas_prog, filas_res, filas_est, filas_pbp = [], [], [], []
        for clave, e, a, rid, rid_est, rid_pbp, invertido in pendientes:
            if clave not in claves_nuevas:
                cont["ya_cargado"] += 1
                continue
            cont["cargado"] += 1
            pid = ids_partido[clave]
            res = a["resultado"]
            fin = res["visible_desde"]
            filas_prog.append({"partido_id": pid,
                               "inicio": datetime.fromtimestamp(a["partido"]["inicio"], tz=timezone.utc),
                               "recibo_id": rid, "recibido_en": e.observado,
                               "visible_desde": a["partido"]["visible_desde"]})
            filas_res.append({
                "partido_id": pid, "estado": res["estado"],
                "ganador": _canon(res["ganador"], invertido) if res["ganador"] else None,
                "retira": _canon(res["retira"], invertido) if res["retira"] else None,
                "sets": _sets_canon(res["sets"], invertido), "sets_completos": res["sets_completos"],
                "duracion_min": res["duracion_min"], "recibo_id": rid, "recibido_en": e.observado,
                "visible_desde": fin})
            if rid_est is not None:
                for lado_txt, lado_local in (("local", 1), ("visitante", 2)):
                    fila = a["estadistica"][lado_txt]
                    if fila is not None:
                        filas_est.append({"partido_id": pid, "lado": _canon(lado_local, invertido), **fila,
                                          "recibo_id": rid_est, "recibido_en": e.observado, "visible_desde": fin})
            if a["pbp"] and rid_pbp is not None:
                for p in a["pbp"]:
                    filas_pbp.append({"partido_id": pid, "set_n": p["set_n"], "juego_n": p["juego_n"],
                                      "sacador": _canon(p["sacador"], invertido), "puntos": p["puntos"],
                                      "es_tiebreak": p["es_tiebreak"], "recibo_id": rid_pbp,
                                      "recibido_en": e.observado, "visible_desde": fin})
        w.programas(cur, filas_prog)
        w.resultados(cur, filas_res)
        w.estadisticas(cur, filas_est)
        w.pbp(cur, filas_pbp)
        conn.commit()
    rechazos.cerrar()
    return cont
