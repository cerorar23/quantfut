"""API de lectura de la web NBA v2 (solo SELECT, transacción de solo lectura por petición).

* GET /nba/v1/cartelera?fecha=AAAA-MM-DD     partidos del día con su pronóstico sellado más reciente y el estado del sello
* GET /nba/v1/partido/{id}                   resumen y distribuciones de equipo (cuantiles de 0,5 % a 99,5 %)
* GET /nba/v1/partido/{id}/estadisticas      forma, récord, cara a cara y clasificación a la fecha del partido (marcadores finales de la temporada regular)
* GET /nba/v1/partido/{id}/mercados          todas las líneas evaluables, cuotas, casas, resultados finales y proyecciones de jugadores
* GET /nba/v1/partido/{id}/linea             P(más / menos de una línea) para margen, total o puntos de un equipo
* GET /nba/v1/partido/{id}/jugador/{id}      pronósticos de jugador sellados (cuando existan)
* GET /nba/v1/sello/{hash}                   verificación pública del sello y su lugar en la cadena
* GET /nba/v1/calibracion                    «Cómo acertamos»: backtest histórico y registro prospectivo
La web estática vive en /nba/v2/. Errores como {"codigo": ...}: la web los traduce a los 6 idiomas; el servidor no manda texto visible.
"""
from datetime import date, datetime, timedelta, UTC
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import psycopg

from ..contratos.validar import ContratoIncumplido, validar_equipo, validar_jugador
from ..v2 import props, sellado
from ..v2.contratos_apuesta import ProbabilidadesContrato, desde_masas
from ..v2.equipos import TRICODES
from . import estadisticas
from .comun import PARTIDOS, prob_mas_de, contrato_linea

ESTATICOS = Path(__file__).parent / "static"
CALIBRACION = Path(os.environ.get("NBA_CALIBRACION_JSON", Path(__file__).parent / "calibracion_v2.json"))
MERCADOS_LINEA = {"margen", "total", "puntos_local", "puntos_visitante"}
MINUTOS_ANTES_DEL_SELLO = 60


def calibracion_por_version(filas, version_actual: str | None) -> dict:
    """Una observación por partido y versión; ninguna cifra de otra versión acredita la vigente."""
    from collections import defaultdict
    grupos = defaultdict(dict)
    for identificador, partido, version, prob, a, b in filas:
        if partido not in grupos[version] or identificador > grupos[version][partido][0]:
            grupos[version][partido] = (identificador, prob, a, b)
    def resumir(version):
        datos = list(grupos[version].values())
        completos = [(p, float(a > b)) for _, p, a, b in datos if a is not None and b is not None and a != b]
        r = {"version_modelo": version, "sellados": len(datos), "con_resultado": len(completos),
             "brier_ganador": None, "logloss_ganador": None, "fiabilidad": [],
             "estado_evidencia": "descriptiva" if completos else "sin_muestra", "calibracion_certificada": False}
        if completos:
            p, y = np.asarray(completos, float).T
            if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
                raise ValueError("probabilidades inválidas en el seguimiento")
            r['brier_ganador'] = float(np.mean((p - y) ** 2))
            pc = np.clip(p, np.finfo(float).eps, 1 - np.finfo(float).eps)
            r['logloss_ganador'] = float(np.mean(-y * np.log(pc) - (1 - y) * np.log1p(-pc)))
            tramos = np.minimum((p * 5).astype(int), 4)
            r['fiabilidad'] = [{"desde": t / 5, "hasta": (t + 1) / 5, "n": int((tramos == t).sum()),
                               "prob_media": float(p[tramos == t].mean()), "tasa_observada": float(y[tramos == t].mean())}
                              for t in range(5) if (tramos == t).any()]
        return r
    versiones = {v: resumir(v) for v in sorted(grupos)}
    vigente = resumir(version_actual) if version_actual else {
        "version_modelo": None, "sellados": 0, "con_resultado": 0, "brier_ganador": None, "logloss_ganador": None,
        "fiabilidad": [], "estado_evidencia": "version_actual_no_configurada", "calibracion_certificada": False}
    return {"prospectivo": vigente, "por_version": versiones}


def _equipo_valido(dist: dict) -> dict:
    """Frontera de salida: nada que incumpla el contrato llega al navegador (los sellos son inmutables; si uno está mal, se dice y no se sirve)."""
    try:
        validar_equipo(dist)
    except ContratoIncumplido:
        raise HTTPException(502, {"codigo": "datos_invalidos"}) from None
    return dist


def _jugador_valido(dist: dict) -> dict:
    try:
        validar_jugador(dist)
    except ContratoIncumplido:
        raise HTTPException(502, {"codigo": "datos_invalidos"}) from None
    return dist


def crear_app(dsn: str | None = None) -> FastAPI:
    app = FastAPI(title="NBA v2 — lectura", docs_url=None, redoc_url=None, openapi_url=None)

    def conexion():
        cadena = dsn or os.environ["NBA_DB_DSN_LECTOR"]
        db = psycopg.connect(cadena, autocommit=False, options="-c default_transaction_read_only=on")
        return db

    def ultimo_pronostico(db, partido_id: int, mercado: str = "equipo", entidad_id: int | None = None):
        return db.execute(
            "SELECT hash, hash_previo, version_modelo, version_datos, objetivo_en, sellado_en, escenarios, distribucion, pronostico_id "
            "FROM nba.pronostico WHERE partido_id = %s AND mercado = %s AND entidad_id IS NOT DISTINCT FROM %s "
            "ORDER BY sellado_en DESC, pronostico_id DESC LIMIT 1", (partido_id, mercado, entidad_id)).fetchone()

    def resumen_partido(db, fila) -> dict:
        pid, fecha, _ent_local, _ent_visit, nl, nv, local, visit = fila
        inicio = db.execute("SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = %s "
                            "AND m.nombre = 'inicio_programado_utc' ORDER BY d.recibido_en DESC LIMIT 1", (pid,)).fetchone()
        inicio_utc = datetime.fromtimestamp(inicio[0], UTC) if inicio and inicio[0] else None
        res = db.execute("SELECT max(CASE WHEN d.entidad_id = tl.entidad_id THEN d.valor END), max(CASE WHEN d.entidad_id = tv.entidad_id THEN d.valor END) "
                         "FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                         "JOIN nba.entidad e ON e.entidad_id = d.partido_id "
                         "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                         "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                         "WHERE d.partido_id = %s AND m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' "
                         "AND d.entidad_id IN (tl.entidad_id, tv.entidad_id)", (pid,)).fetchone()
        p = ultimo_pronostico(db, pid)
        salida = {"id": pid, "fecha": fecha.isoformat(), "local": {"codigo": local, "nombre": nl}, "visitante": {"codigo": visit, "nombre": nv},
                  "inicio_utc": inicio_utc.isoformat() if inicio_utc else None,
                  "sello_previsto": (inicio_utc - timedelta(minutes=MINUTOS_ANTES_DEL_SELLO)).isoformat() if inicio_utc else None,
                  "resultado": {"local": res[0], "visitante": res[1]} if res and res[0] is not None and res[1] is not None else None,
                  "pronostico": None}
        if p:
            h, hp, vm, vd, obj, sel, esc, dist, _ = p
            _equipo_valido(dist)
            salida["pronostico"] = {"hash": h, "version_modelo": vm, "objetivo_en": obj.isoformat(), "sellado_en": sel.isoformat(),
                                    "p_local": dist["p_local"], "mu": dist["mu"], "escenarios": esc,
                                    "margen_p10_p90": [dist["margen"][19], dist["margen"][179]],
                                    "total_p10_p90": [dist["total"][19], dist["total"][179]],
                                    "mediana": {"margen": dist["margen"][99], "total": dist["total"][99]}}
        return salida


    @app.get("/nba/v1/cartelera")
    def cartelera(fecha: date = Query(...)):
        with conexion() as db:
            filas = db.execute(PARTIDOS + " AND e.fecha_juego_et = %s ORDER BY e.entidad_id", (fecha,)).fetchall()
            return {"fecha": fecha.isoformat(), "partidos": [resumen_partido(db, f) for f in filas]}

    @app.get("/nba/v1/mercados")
    def mercados(fecha: date = Query(...)):
        from .mercados import mercados_del_dia
        return mercados_del_dia(dsn or os.environ["NBA_DB_DSN_LECTOR"], fecha)

    @app.get("/nba/v1/partido/{partido_id}")
    def partido(partido_id: int):
        with conexion() as db:
            f = db.execute(PARTIDOS + " AND e.entidad_id = %s", (partido_id,)).fetchone()
            if f is None:
                raise HTTPException(404, {"codigo": "partido_inexistente"})
            r = resumen_partido(db, f)
            p = ultimo_pronostico(db, partido_id)
            if p:
                d = p[7]
                r["distribuciones"] = {k: d[k] for k in ("margen", "total", "puntos_local", "puntos_visitante")}
                r["distribuciones"]["paso_cuantil"] = d["paso_cuantil"]
            return r

    PUNTOS_FINALES = ("(SELECT d.valor AS valor FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'puntos' "
                      "JOIN nba.fuente f ON f.fuente = d.fuente WHERE d.partido_id = e.entidad_id AND d.entidad_id = {equipo}.entidad_id "
                      "AND d.periodo = 0 AND d.fase = 'final' AND d.valor IS NOT NULL ORDER BY f.prioridad, d.recibido_en DESC, d.dato_id DESC LIMIT 1)")

    @app.get("/nba/v1/partido/{partido_id}/estadisticas")
    def estadisticas_partido(partido_id: int):
        """Forma, récord, cara a cara y clasificación «a la fecha» del partido: solo marcadores finales de la temporada regular anteriores a su día."""
        with conexion() as db:
            f = db.execute("SELECT e.fecha_juego_et, e.temporada, (e.atributos->>'local')::bigint, (e.atributos->>'visitante')::bigint, tl.id_en_fuente, tv.id_en_fuente "
                           "FROM nba.entidad e JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                           "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                           "WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id AND e.entidad_id = %s", (partido_id,)).fetchone()
            if f is None:
                raise HTTPException(404, {"codigo": "partido_inexistente"})
            fecha, temporada, id_local, id_visitante, local, visitante = f
            if not (estadisticas.ventana_regular(temporada)[0] <= fecha) or local not in TRICODES or visitante not in TRICODES:
                raise HTTPException(404, {"codigo": "sin_estadisticas"})
            filas = db.execute(
                "SELECT DISTINCT ON (e.fecha_juego_et, tl.entidad_id, tv.entidad_id) e.fecha_juego_et, e.temporada, tl.id_en_fuente, tv.id_en_fuente, pl.valor, pv.valor "
                "FROM nba.entidad e JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                f"CROSS JOIN LATERAL {PUNTOS_FINALES.format(equipo='tl')} AS pl CROSS JOIN LATERAL {PUNTOS_FINALES.format(equipo='tv')} AS pv "
                "WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id AND e.fecha_juego_et < %(fecha)s "
                "AND (e.temporada IN (%(actual)s, %(pasada)s) OR (tl.entidad_id = %(a)s AND tv.entidad_id = %(b)s) OR (tl.entidad_id = %(b)s AND tv.entidad_id = %(a)s)) "
                "ORDER BY e.fecha_juego_et, tl.entidad_id, tv.entidad_id, e.entidad_id",
                {"fecha": fecha, "actual": temporada, "pasada": estadisticas.temporada_anterior(temporada), "a": id_local, "b": id_visitante}).fetchall()
        previos = [estadisticas.Marcador(d, t, a, b, pl, pv) for d, t, a, b, pl, pv in filas if a in TRICODES and b in TRICODES]
        return estadisticas.estadisticas(temporada, fecha, local, visitante, previos)

    @app.get("/nba/v1/partido/{partido_id}/mercados")
    def mercados_partido(partido_id: int):
        from .mercados_partido import consultar
        with conexion() as db:
            fila = db.execute(PARTIDOS + " AND e.entidad_id = %s", (partido_id,)).fetchone()
            if fila is None:
                raise HTTPException(404, {"codigo": "partido_inexistente"})
            try:
                return consultar(db, fila)
            except ContratoIncumplido:
                raise HTTPException(502, {"codigo": "datos_invalidos"}) from None

    @app.get("/nba/v1/partido/{partido_id}/linea")
    def linea(partido_id: int, mercado: str = Query(...), valor: float = Query(..., allow_inf_nan=False)):
        if mercado not in MERCADOS_LINEA:
            raise HTTPException(422, {"codigo": "mercado_desconocido"})
        with conexion() as db:
            p = ultimo_pronostico(db, partido_id)
            if p is None:
                raise HTTPException(404, {"codigo": "sin_pronostico"})
            d = _equipo_valido(p[7])
            contrato = contrato_linea(d, mercado, valor)
            return {"mercado": mercado, "linea": valor, **contrato, "hash": p[0]}

    @app.get("/nba/v1/partido/{partido_id}/jugador/{jugador_id}")
    def jugador(partido_id: int, jugador_id: int):
        with conexion() as db:
            filas = db.execute("SELECT DISTINCT ON (mercado) mercado, hash, sellado_en, escenarios, distribucion FROM nba.pronostico "
                               "WHERE partido_id = %s AND entidad_id = %s ORDER BY mercado, sellado_en DESC, pronostico_id DESC",
                               (partido_id, jugador_id)).fetchall()
            if not filas:
                raise HTTPException(404, {"codigo": "sin_pronostico_jugador"})
            return {"partido_id": partido_id, "jugador_id": jugador_id,
                    "mercados": {m: {"hash": h, "sellado_en": s.isoformat(), "escenarios": e, "distribucion": _jugador_valido(d)} for m, h, s, e, d in filas}}

    @app.get("/nba/v1/partido/{partido_id}/jugadores")
    def jugadores(partido_id: int):
        with conexion() as db:
            filas = db.execute("SELECT DISTINCT ON (entidad_id, mercado) entidad_id, mercado, escenarios, distribucion FROM nba.pronostico "
                               "WHERE partido_id = %s AND entidad_id IS NOT NULL ORDER BY entidad_id, mercado, sellado_en DESC, pronostico_id DESC",
                               (partido_id,)).fetchall()
        por_jugador: dict = {}
        for jid, mercado, esc, dist in filas:
            _jugador_valido(dist)
            j = por_jugador.setdefault(jid, {"id": jid, "nombre": esc.get("nombre"), "lado": esc.get("lado"), "estado": esc.get("estado"),
                                             "p_juega": esc.get("p_juega"), "minutos_si_juega": esc.get("minutos_si_juega"),
                                             "minutos_esperados": dist.get("minutos_esperados"), "mercados": {}})
            j["mercados"][mercado.split(":", 1)[1]] = {"media": dist["media"], "p10": dist["p10"], "p50": dist["p50"], "p90": dist["p90"]}
        orden = sorted(por_jugador.values(), key=lambda j: -(j["minutos_esperados"] or 0))
        return {"partido_id": partido_id, "jugadores": orden}

    @app.get("/nba/v1/partido/{partido_id}/disponibilidad")
    def disponibilidad(partido_id: int):
        with conexion() as db:
            fila = db.execute(PARTIDOS + " AND e.entidad_id = %s", (partido_id,)).fetchone()
            if fila is None:
                raise HTTPException(404, {"codigo": "partido_inexistente"})
            pid, fecha, id_local, id_visitante, nombre_local, nombre_visitante, cod_local, cod_visitante = fila

            captura = db.execute(
                "SELECT c.objetivo, c.recibido_en FROM nba.captura c "
                "JOIN nba.dato d USING (captura_id) "
                "WHERE d.partido_id = %s AND d.fuente = 'nba_oficial' "
                "ORDER BY d.recibido_en DESC, d.dato_id DESC LIMIT 1", (pid,)).fetchone()
            reporte_url = captura[0] if captura else None
            reporte_fecha = captura[1].isoformat() if captura and captura[1] else None

            no_env = db.execute(
                "SELECT d.entidad_id FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                "WHERE d.partido_id = %s AND m.nombre = 'reporte_no_enviado' AND d.valor = 1.0 "
                "AND d.recibido_en = (SELECT max(recibido_en) FROM nba.dato WHERE partido_id = %s AND fuente = 'nba_oficial')",
                (pid, pid)).fetchall()
            no_enviados = {r[0] for r in no_env}

            filas_jug = db.execute(
                "SELECT DISTINCT ON (d.entidad_id) "
                "  d.entidad_id, j.nombre, j.id_en_fuente, d.etiqueta, dm.etiqueta, d.recibido_en "
                "FROM nba.dato d "
                "JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'estado_disponibilidad' "
                "JOIN nba.entidad j ON j.entidad_id = d.entidad_id "
                "LEFT JOIN LATERAL ( "
                "  SELECT dm.etiqueta FROM nba.dato dm JOIN nba.metrica mm ON mm.metrica_id = dm.metrica_id AND mm.nombre = 'motivo_disponibilidad' "
                "  WHERE dm.partido_id = d.partido_id AND dm.entidad_id = d.entidad_id "
                "  ORDER BY dm.recibido_en DESC, dm.dato_id DESC LIMIT 1 "
                ") dm ON true "
                "WHERE d.partido_id = %s AND d.fuente = 'nba_oficial' "
                "ORDER BY d.entidad_id, d.recibido_en DESC, d.dato_id DESC", (pid,)).fetchall()

            jug_ids = [r[0] for r in filas_jug]
            lados_pron = {}
            equipos_jug = {}
            nba_ids = {}
            if jug_ids:
                eq_filas = db.execute(
                    "SELECT j.entidad_id, "
                    "       COALESCE( "
                    "           (SELECT t.valor::bigint FROM nba.dato t "
                    "            JOIN nba.metrica mt ON mt.metrica_id = t.metrica_id AND mt.nombre = 'equipo_del_jugador' "
                    "            JOIN nba.entidad e ON e.entidad_id = t.partido_id "
                    "            WHERE t.entidad_id = j.entidad_id AND e.fecha_juego_et <= %s "
                    "            ORDER BY e.fecha_juego_et DESC, t.dato_id DESC LIMIT 1), "
                    "           (SELECT t.valor::bigint FROM nba.dato t "
                    "            JOIN nba.metrica mt ON mt.metrica_id = t.metrica_id AND mt.nombre = 'equipo_del_jugador' "
                    "            JOIN nba.entidad e ON e.entidad_id = t.partido_id "
                    "            JOIN nba.entidad o ON o.entidad_id = t.entidad_id "
                    "            WHERE (o.atributos->>'nombre_norm' = j.atributos->>'nombre_norm' OR lower(o.nombre) = lower(j.nombre)) "
                    "              AND e.fecha_juego_et <= %s "
                    "            ORDER BY e.fecha_juego_et DESC, t.dato_id DESC LIMIT 1) "
                    "       ) "
                    "FROM nba.entidad j WHERE j.entidad_id = ANY(%s)",
                    (fecha, fecha, jug_ids)).fetchall()
                equipos_jug = {r[0]: r[1] for r in eq_filas if r[1] is not None}

                fotos_filas = db.execute(
                    "SELECT j.entidad_id, "
                    "       COALESCE( "
                    "           (SELECT o.id_en_fuente FROM nba.entidad o "
                    "            WHERE o.tipo = 'jugador' AND o.fuente = 'nba_oficial' "
                    "              AND (o.canonica_id = j.entidad_id OR o.entidad_id = j.entidad_id) "
                    "              AND o.id_en_fuente ~ '^[0-9]{1,8}$' LIMIT 1), "
                    "           (SELECT o.id_en_fuente FROM nba.entidad o "
                    "            WHERE o.tipo = 'jugador' AND o.fuente = 'nba_oficial' "
                    "              AND (o.atributos->>'nombre_norm' = j.atributos->>'nombre_norm' OR lower(o.nombre) = lower(j.nombre)) "
                    "              AND o.id_en_fuente ~ '^[0-9]{1,8}$' LIMIT 1) "
                    "       ) "
                    "FROM nba.entidad j WHERE j.entidad_id = ANY(%s)",
                    (jug_ids,)).fetchall()
                nba_ids = {r[0]: int(r[1]) for r in fotos_filas if r[1] and r[1].isdigit()}

                lados_filas = db.execute(
                    "SELECT DISTINCT ON (entidad_id) entidad_id, escenarios->>'lado' "
                    "FROM nba.pronostico WHERE partido_id = %s AND entidad_id = ANY(%s) "
                    "AND escenarios->>'lado' IS NOT NULL", (pid, jug_ids)).fetchall()
                lados_pron = dict(lados_filas)

            jugadores_local = []
            jugadores_visitante = []
            for jid, jnombre, jid_fuente, jestado, jmotivo, _ in filas_jug:
                lado = lados_pron.get(jid)
                eq_id = equipos_jug.get(jid)
                es_local = (lado == 'local') if lado else (eq_id == id_local) if eq_id == id_local else (False if eq_id == id_visitante else None)
                item = {
                    "id": jid,
                    "nba_id": nba_ids.get(jid),
                    "nombre": jnombre,
                    "estado": jestado,
                    "motivo": jmotivo or "Sin motivo detallado"
                }
                if es_local is True:
                    jugadores_local.append(item)
                elif es_local is False:
                    jugadores_visitante.append(item)
                else:
                    if len(jugadores_local) <= len(jugadores_visitante):
                        jugadores_local.append(item)
                    else:
                        jugadores_visitante.append(item)

            p = ultimo_pronostico(db, pid)
            metricas_bajas = None
            if p and isinstance(p[7], dict):
                metricas_bajas = p[7].get("availability")

            return {
                "partido_id": pid,
                "estado": "reporte_aplicado" if (filas_jug or reporte_url) else "sin_reporte",
                "reporte_url": reporte_url,
                "reporte_timestamp_utc": reporte_fecha,
                "local": {
                    "id": id_local,
                    "nombre": nombre_local,
                    "codigo": cod_local,
                    "reporte_no_enviado": id_local in no_enviados,
                    "jugadores": jugadores_local
                },
                "visitante": {
                    "id": id_visitante,
                    "nombre": nombre_visitante,
                    "codigo": cod_visitante,
                    "reporte_no_enviado": id_visitante in no_enviados,
                    "jugadores": jugadores_visitante
                },
                "metricas_bajas": metricas_bajas,
                "resumen": {
                    "total_local": len(jugadores_local),
                    "total_visitante": len(jugadores_visitante),
                    "total_jugadores": len(filas_jug)
                }
            }

    @app.get("/nba/v1/partido/{partido_id}/jugador/{jugador_id}/linea")
    def linea_jugador(partido_id: int, jugador_id: int, mercado: str = Query(...), valor: float = Query(..., allow_inf_nan=False)):
        if mercado not in props.ESTADISTICAS:
            raise HTTPException(422, {"codigo": "mercado_desconocido"})
        with conexion() as db:
            p = ultimo_pronostico(db, partido_id, f"jugador:{mercado}", jugador_id)
        if p is None:
            raise HTTPException(404, {"codigo": "sin_pronostico_jugador"})
        pmf = np.asarray(_jugador_valido(p[7])["pmf"], float)
        contrato = desde_masas(np.arange(len(pmf)), pmf, valor)
        return {"mercado": mercado, "linea": valor, **contrato.salida(p[7]["p_juega"]), "p_juega": p[7]["p_juega"],
                "extremo": contrato.gana == 0 or contrato.pierde == 0, "hash": p[0]}

    @app.get("/nba/v1/sello/{hash_}")
    def sello(hash_: str, cadena: bool = False):
        if len(hash_) != 64 or any(c not in "0123456789abcdef" for c in hash_):
            raise HTTPException(422, {"codigo": "hash_invalido"})
        with conexion() as db:
            f = db.execute("SELECT pronostico_id, partido_id, mercado, periodo, entidad_id, version_modelo, version_datos, objetivo_en, sellado_en, "
                           "escenarios, distribucion, hash_previo, hash FROM nba.pronostico WHERE hash = %s", (hash_,)).fetchone()
            if f is None:
                raise HTTPException(404, {"codigo": "sello_inexistente"})
            (pid, partido_id, mercado, periodo, entidad, vm, vd, obj, sel, esc, dist, hp, h) = f
            recalculado = sellado.calcular_hash(partido_id, mercado, periodo, entidad, vm, vd, obj, sel, esc, dist, hp)
            anterior = db.execute("SELECT hash FROM nba.pronostico WHERE pronostico_id < %s ORDER BY pronostico_id DESC LIMIT 1", (pid,)).fetchone()
            enlazado = (anterior[0] if anterior else sellado.GENESIS) == hp
            posicion = db.execute("SELECT count(*) FROM nba.pronostico WHERE pronostico_id <= %s", (pid,)).fetchone()[0]
            salida = {"valido": recalculado == h and enlazado and obj <= sel, "contenido_integro": recalculado == h, "enlazado": enlazado,
                      "posicion": posicion, "partido_id": partido_id, "mercado": mercado, "version_modelo": vm, "version_datos": vd,
                      "objetivo_en": obj.isoformat(), "sellado_en": sel.isoformat(), "hash_previo": hp}
            if cadena:
                try:
                    salida["cadena_verificada"] = sellado.verificar_cadena(db)
                except ValueError as e:
                    salida["cadena_verificada"] = None
                    salida["cadena_error"] = str(e)
            return salida

    @app.get("/nba/v1/calibracion")
    def calibracion():
        historico = json.loads(CALIBRACION.read_text(encoding="utf8")) if CALIBRACION.exists() else None
        with conexion() as db:
            filas = db.execute(
                "SELECT p.pronostico_id, p.partido_id, p.version_modelo, (p.distribucion->>'p_local')::float, rl.valor, rv.valor FROM nba.pronostico p "
                "JOIN nba.entidad e ON e.entidad_id = p.partido_id "
                "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                "LEFT JOIN LATERAL (SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = e.entidad_id AND d.entidad_id = tl.entidad_id "
                "  AND m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' ORDER BY d.recibido_en DESC LIMIT 1) rl ON true "
                "LEFT JOIN LATERAL (SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = e.entidad_id AND d.entidad_id = tv.entidad_id "
                "  AND m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' ORDER BY d.recibido_en DESC LIMIT 1) rv ON true "
                "WHERE p.mercado = 'equipo' AND p.entidad_id IS NULL").fetchall()
        actual = os.environ.get("NBA_VERSION_MODELO_ACTIVA")
        if not actual:
            from ..v2 import equipo_jugadores, parametros
            actual = equipo_jugadores.version(parametros.cargar_impacto())
        resumen = calibracion_por_version(filas, actual)
        identidad_historica = historico.get('version_modelo') if historico else None
        return {"historico": historico, "historico_version_modelo": identidad_historica,
                "historico_acredita_version_actual": bool(actual and identidad_historica == actual and historico.get('hashes_entradas')),
                **resumen}

    @app.get("/nba/v2")
    def raiz():
        return RedirectResponse("/nba/v2/")

    app.mount("/nba/v2", StaticFiles(directory=ESTATICOS, html=True), name="web")
    return app


def app_desde_entorno() -> FastAPI:
    return crear_app()
