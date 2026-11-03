"""API de lectura de la web NBA v2 (solo SELECT, transacción de solo lectura por petición).

* GET /nba/v1/cartelera?fecha=AAAA-MM-DD     partidos del día con su pronóstico sellado más reciente y el estado del sello
* GET /nba/v1/partido/{id}                   resumen y distribuciones de equipo (cuantiles de 0,5 % a 99,5 %)
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

ESTATICOS = Path(__file__).parent / "static"
CALIBRACION = Path(os.environ.get("NBA_CALIBRACION_JSON", Path(__file__).parent / "calibracion_v2.json"))
MERCADOS_LINEA = {"margen", "total", "puntos_local", "puntos_visitante"}
MINUTOS_ANTES_DEL_SELLO = 60


def prob_mas_de(cuantiles: list[float], linea: float, paso: float = 0.005) -> tuple[float, bool]:
    """P(X > línea) a partir de los cuantiles (199 valores, niveles paso…1-paso). Fuera del rango se acota a [paso, 1-paso]
    y se marca como extremo. Interpolación lineal del nivel entre cuantiles contiguos."""
    q = np.asarray(cuantiles, float)
    niveles = paso * np.arange(1, len(q) + 1)
    if linea <= q[0]:
        return 1.0 - paso, True
    if linea >= q[-1]:
        return paso, True
    # np.interp exige abscisas crecientes: se desempata con una mota para cuantiles repetidos (distribución discreta)
    xs = q + np.arange(len(q)) * 1e-9
    return float(1.0 - np.interp(linea, xs, niveles)), False


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
        pid, fecha, local, visit, nl, nv = fila
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

    PARTIDOS = ("SELECT e.entidad_id, e.fecha_juego_et, tl.id_en_fuente, tv.id_en_fuente, tl.nombre, tv.nombre FROM nba.entidad e "
                "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                "WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id "
                "AND e.entidad_id = (SELECT min(x.entidad_id) FROM nba.entidad x WHERE x.tipo = 'partido' AND x.canonica_id = x.entidad_id AND x.fecha_juego_et = e.fecha_juego_et AND x.atributos->>'local' = e.atributos->>'local' AND x.atributos->>'visitante' = e.atributos->>'visitante')")

    @app.get("/nba/v1/cartelera")
    def cartelera(fecha: date = Query(...)):
        with conexion() as db:
            filas = db.execute(PARTIDOS + " AND e.fecha_juego_et = %s ORDER BY e.entidad_id", (fecha,)).fetchall()
            return {"fecha": fecha.isoformat(), "partidos": [resumen_partido(db, f) for f in filas]}

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

    @app.get("/nba/v1/partido/{partido_id}/linea")
    def linea(partido_id: int, mercado: str = Query(...), valor: float = Query(...)):
        if mercado not in MERCADOS_LINEA:
            raise HTTPException(422, {"codigo": "mercado_desconocido"})
        with conexion() as db:
            p = ultimo_pronostico(db, partido_id)
            if p is None:
                raise HTTPException(404, {"codigo": "sin_pronostico"})
            d = _equipo_valido(p[7])
            mas, extremo = prob_mas_de(d[mercado], valor, d["paso_cuantil"])
            return {"mercado": mercado, "linea": valor, "p_mas": round(mas, 4), "p_menos": round(1 - mas, 4), "extremo": extremo, "hash": p[0]}

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

    @app.get("/nba/v1/partido/{partido_id}/jugador/{jugador_id}/linea")
    def linea_jugador(partido_id: int, jugador_id: int, mercado: str = Query(...), valor: float = Query(...)):
        if mercado not in props.ESTADISTICAS:
            raise HTTPException(422, {"codigo": "mercado_desconocido"})
        with conexion() as db:
            p = ultimo_pronostico(db, partido_id, f"jugador:{mercado}", jugador_id)
        if p is None:
            raise HTTPException(404, {"codigo": "sin_pronostico_jugador"})
        pmf = np.asarray(_jugador_valido(p[7])["pmf"], float)
        mas = float(props.prob_mas_de(pmf[None, :], np.array([valor]))[0])
        return {"mercado": mercado, "linea": valor, "p_mas": round(mas, 4), "p_menos": round(1 - mas, 4), "p_juega": p[7]["p_juega"],
                "extremo": bool(mas in (0.001, 0.999)), "hash": p[0]}

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
                "SELECT p.pronostico_id, (p.distribucion->>'p_local')::float, rl.valor, rv.valor FROM nba.pronostico p "
                "JOIN nba.entidad e ON e.entidad_id = p.partido_id "
                "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                "LEFT JOIN LATERAL (SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = e.entidad_id AND d.entidad_id = tl.entidad_id "
                "  AND m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' ORDER BY d.recibido_en DESC LIMIT 1) rl ON true "
                "LEFT JOIN LATERAL (SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = e.entidad_id AND d.entidad_id = tv.entidad_id "
                "  AND m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' ORDER BY d.recibido_en DESC LIMIT 1) rv ON true "
                "WHERE p.mercado = 'equipo' AND p.entidad_id IS NULL").fetchall()
        con_resultado = [(p, 1.0 if a > b else 0.0) for _, p, a, b in filas if a is not None and b is not None]
        pros = {"sellados": len(filas), "con_resultado": len(con_resultado), "brier_ganador": None, "fiabilidad": []}
        if con_resultado:
            p = np.array([x[0] for x in con_resultado])
            y = np.array([x[1] for x in con_resultado])
            pros["brier_ganador"] = round(float(np.mean((p - y) ** 2)), 4)
            tramos = np.minimum((p * 5).astype(int), 4)
            pros["fiabilidad"] = [{"desde": t / 5, "hasta": (t + 1) / 5, "n": int((tramos == t).sum()), "prob_media": round(float(p[tramos == t].mean()), 3),
                                   "tasa_observada": round(float(y[tramos == t].mean()), 3)} for t in range(5) if (tramos == t).any()]
        return {"historico": historico, "prospectivo": pros}

    @app.get("/nba/v2")
    def raiz():
        return RedirectResponse("/nba/v2/")

    app.mount("/nba/v2", StaticFiles(directory=ESTATICOS, html=True), name="web")
    return app


def app_desde_entorno() -> FastAPI:
    return crear_app()
