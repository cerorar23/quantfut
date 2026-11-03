"""Proceso `nba-motor`: sella el pronóstico de cada partido 60 minutos antes del salto (predecir → sellar → publicar).

Se ejecuta cada pocos minutos (cron con candado). Para cada partido cuyo salto programado está entre ahora y 60 minutos:
  1. el corte de los datos es `inicio − 60 min` (fijo, no la hora en que corrió el proceso): si el cron se retrasa, el pronóstico
     sigue usando exactamente los mismos datos y G-fuga sigue valiendo;
  2. nunca se sella después del salto; un partido que empezó sin sello queda registrado como omitido, no se rellena a posteriori;
  3. nunca se pronostica con la historia atrasada (captura caída): se omite y se informa en vez de sellar con ratings viejos;
  4. un partido que falla no impide sellar los demás; cada sello es su propia transacción.
Sin hora de salto conocida no hay corte: el partido se lista en `sin_hora` y no se sella.
"""
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo
import argparse
import json
import os
from pathlib import Path
import sys

import psycopg

from . import alertas, equipo_jugadores, identidad, motor_equipo, motor_jugadores, parametros, pit, sellado
from ..contratos.validar import ContratoIncumplido, validar_equipo, validar_jugador
from .plantilla_pit import plantilla
from .sellado import PronosticoNuevo

ET = ZoneInfo("America/New_York")
MINUTOS_ANTES = 60
HOLGURA_HISTORIA_DIAS = 7                 # más que la pausa del Juego de Estrellas
MERCADO = "equipo"
PARAMETROS_PROPS = parametros.cargar_props()
PARAMETROS_IMPACTO = parametros.cargar_impacto()
VERSION_EQUIPO_JUGADORES = equipo_jugadores.version(PARAMETROS_IMPACTO)
VERSION_PROPS = f"props-2.0;{PARAMETROS_PROPS.version};k={PARAMETROS_PROPS.k_minutos};dec={PARAMETROS_PROPS.decaimiento}"
DIAS_MAXIMOS_SIN_JUGAR = 10                # más que la pausa del Juego de Estrellas: un equipo sin resultados por más tiempo es un hueco de datos
DIAS_DE_GRACIA_INICIO = 21                 # pasadas tres semanas de temporada, un equipo sin ningún resultado también lo es
HORAS_DE_AVISO_TRAS_EL_SALTO = 3           # pasado esto, un partido sin sello deja de repetirse en el informe

CANDIDATOS = """
SELECT e.entidad_id, e.fecha_juego_et, ini.valor
FROM nba.entidad e
LEFT JOIN LATERAL (
    SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id)
    WHERE d.partido_id = e.entidad_id AND m.nombre = 'inicio_programado_utc' AND d.recibido_en <= %(ahora)s
    ORDER BY d.recibido_en DESC, d.dato_id DESC LIMIT 1
) ini ON true
WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id AND e.fecha_juego_et BETWEEN %(desde)s AND %(hasta)s
  AND e.entidad_id = (SELECT min(x.entidad_id) FROM nba.entidad x WHERE x.tipo = 'partido' AND x.canonica_id = x.entidad_id AND x.fecha_juego_et = e.fecha_juego_et AND x.atributos->>'local' = e.atributos->>'local' AND x.atributos->>'visitante' = e.atributos->>'visitante')
  AND NOT EXISTS (SELECT 1 FROM nba.dato f JOIN nba.metrica mf USING (metrica_id)
                  WHERE f.partido_id = e.entidad_id AND mf.nombre = 'estado_partido' AND f.etiqueta = 'final' AND f.recibido_en <= %(ahora)s)
ORDER BY e.fecha_juego_et, e.entidad_id
"""


def ejecutar(db, ahora: datetime | None = None, simulacro: bool = False) -> dict:
    ahora = ahora or datetime.now(UTC)
    hoy = ahora.astimezone(ET).date()
    resumen = {"ahora": ahora.isoformat(), "version_modelo": VERSION_EQUIPO_JUGADORES, "version_props": VERSION_PROPS, "simulacro": simulacro,
               "sellados": [], "props": [], "omitidos": [], "sin_hora": [], "errores": []}
    filas = db.execute(CANDIDATOS, {"ahora": ahora, "desde": hoy - timedelta(days=1), "hasta": hoy + timedelta(days=1)}).fetchall()
    db.rollback()
    for pid, fecha, inicio_epoch in filas:
        if inicio_epoch is None:
            resumen["sin_hora"].append(pid)
            continue
        inicio = datetime.fromtimestamp(inicio_epoch, UTC)
        corte = inicio - timedelta(minutes=MINUTOS_ANTES)
        if ahora < corte:
            continue
        if ahora >= inicio:
            if ahora < inicio + timedelta(hours=HORAS_DE_AVISO_TRAS_EL_SALTO) and not _ya_sellado(db, pid, corte):
                resumen["omitidos"].append({"partido": pid, "razon": "ya_empezo_sin_sello"})
            continue
        try:
            equipo_hecho, props_hechos = _ya_sellado(db, pid, corte), _ya_sellado(db, pid, corte, props=True)
            if equipo_hecho and props_hechos:
                continue
            inst = pit.instantanea(db, pid, corte)
            if not inst.historia or inst.historia[-1][0] < fecha - timedelta(days=HOLGURA_HISTORIA_DIAS):
                resumen["omitidos"].append({"partido": pid, "razon": "historia_atrasada"})
                db.rollback()
                continue
            razon = equipo_atrasado(inst)
            if razon:
                resumen["omitidos"].append({"partido": pid, "razon": razon})
                db.rollback()
                continue
            pl = plantilla(db, inst)
            if not equipo_hecho:
                version, esc, dist = equipo_jugadores.pronosticar(inst, pl, PARAMETROS_IMPACTO, PARAMETROS_PROPS)
                vd = (inst.version_datos + pl.version_datos)[:64] if version == VERSION_EQUIPO_JUGADORES else inst.version_datos
                validar_equipo(dist)                              # frontera: lo que incumple el contrato no se sella
                if simulacro:
                    resumen["sellados"].append({"partido": pid, "version": version.split(";")[0], "p_local": dist["p_local"], "mu": dist["mu"],
                                                "version_datos": vd[:12]})
                else:
                    h = sellado.sellar(db, PronosticoNuevo(pid, MERCADO, version, vd, corte, esc, dist))
                    db.commit()
                    resumen["sellados"].append({"partido": pid, "hash": h, "version": version.split(";")[0], "p_local": dist["p_local"]})
            if not props_hechos:
                items = _solo_validos(motor_jugadores.pronosticar(pl, PARAMETROS_PROPS), pid, resumen)
                if simulacro:
                    resumen["props"].append({"partido": pid, "jugadores": len({x["jugador"] for x in items}), "pronosticos": len(items)})
                elif items:
                    vd = pl.version_datos + inst.version_datos
                    with db.transaction():                           # todo el partido o nada: un fallo deshace los sellos de sus jugadores
                        for x in items:
                            sellado.sellar(db, PronosticoNuevo(pid, x["mercado"], VERSION_PROPS, vd[:64], corte, x["escenarios"], x["distribucion"],
                                                               entidad_id=x["jugador"]))
                    db.commit()
                    resumen["props"].append({"partido": pid, "jugadores": len({x["jugador"] for x in items}), "pronosticos": len(items)})
        except Exception as e:                               # un partido roto no impide sellar los demás
            db.rollback()
            resumen["errores"].append({"partido": pid, "error": f"{type(e).__name__}: {e}"[:300]})
    return resumen


def equipo_atrasado(inst) -> str | None:
    """Razón por la que a uno de los dos equipos le faltan resultados recientes (captura caída solo para él), o None. Un ratings viejo no se sella."""
    temporada = identidad.temporada(inst.fecha)
    esta = [h for h in inst.historia if identidad.temporada(h[0]) == temporada]
    if not esta:                                          # apertura de temporada: no hay nada que comparar
        return None
    inicio = min(h[0] for h in esta)
    for tri in (inst.local, inst.visitante):
        propios = [h[0] for h in esta if tri in (h[2], h[3])]
        if propios and (inst.fecha - max(propios)).days > DIAS_MAXIMOS_SIN_JUGAR:
            return "equipo_sin_resultados_recientes"
        if not propios and (inst.fecha - inicio).days > DIAS_DE_GRACIA_INICIO:
            return "equipo_sin_resultados_recientes"
    return None


def _solo_validos(items: list[dict], pid: int, resumen: dict) -> list[dict]:
    """Descarta (y avisa) los pronósticos de jugador que incumplen el contrato; nunca se sella uno inválido ni se completa con un valor inventado."""
    validos = []
    for x in items:
        try:
            validar_jugador(x["distribucion"])
            validos.append(x)
        except ContratoIncumplido as e:
            resumen["errores"].append({"partido": pid, "error": f"ContratoIncumplido: jugador {x['jugador']} {x['mercado']}: {e}"[:300]})
    return validos


def _ya_sellado(db, pid: int, corte: datetime, props: bool = False) -> bool:
    if props:
        hay = db.execute("SELECT 1 FROM nba.pronostico WHERE partido_id = %s AND mercado LIKE 'jugador:%%' AND version_modelo = %s "
                         "AND objetivo_en = %s LIMIT 1", (pid, VERSION_PROPS, corte)).fetchone()
    else:
        hay = db.execute("SELECT 1 FROM nba.pronostico WHERE partido_id = %s AND mercado = %s AND periodo = 0 AND entidad_id IS NULL "
                         "AND version_modelo LIKE 'equipo-%%' AND objetivo_en = %s", (pid, MERCADO, corte)).fetchone()
    db.rollback()
    return hay is not None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="nba.v2.motor")
    ap.add_argument("--simulacro", action="store_true", help="calcula y muestra, no sella")
    ap.add_argument("--ahora", help="hora ISO con zona (solo con --simulacro): mira la base como si fuera esa hora")
    args = ap.parse_args(argv)
    ahora = datetime.fromisoformat(args.ahora) if args.ahora else None
    if ahora is not None and (ahora.tzinfo is None or not args.simulacro):
        print(json.dumps({"error": "--ahora exige zona horaria y --simulacro"}), file=sys.stderr)
        return 2
    dsn = os.environ.get("NBA_DB_DSN")
    if not dsn:
        print(json.dumps({"error": "falta NBA_DB_DSN"}), file=sys.stderr)
        return 2
    with psycopg.connect(dsn) as db:
        resumen = ejecutar(db, ahora, simulacro=args.simulacro)
    if not args.simulacro:
        directorio = os.environ.get("NBA_MOTOR_DIR")
        try:
            resumen["alertas"] = alertas.procesar(resumen, Path(directorio) / "estado_alertas.json" if directorio else None,
                                                  os.environ.get("NBA_ALERTA_TG_TOKEN"), os.environ.get("NBA_ALERTA_CHAT"))
        except Exception as e:                               # una alerta que no sale no debe esconder lo sellado
            resumen["alertas_error"] = f"{type(e).__name__}"[:80]
    print(json.dumps(resumen, ensure_ascii=False))
    return 1 if resumen["errores"] else 0


if __name__ == "__main__":
    sys.exit(main())
