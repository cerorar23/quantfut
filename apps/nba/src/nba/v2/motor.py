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
import sys

import psycopg

from . import motor_equipo, pit, sellado
from .sellado import PronosticoNuevo

ET = ZoneInfo("America/New_York")
MINUTOS_ANTES = 60
HOLGURA_HISTORIA_DIAS = 7                 # más que la pausa del Juego de Estrellas
MERCADO = "equipo"
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
    resumen = {"ahora": ahora.isoformat(), "version_modelo": motor_equipo.VERSION_MODELO, "simulacro": simulacro,
               "sellados": [], "omitidos": [], "sin_hora": [], "errores": []}
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
            if _ya_sellado(db, pid, corte):
                continue
            inst = pit.instantanea(db, pid, corte)
            if not inst.historia or inst.historia[-1][0] < fecha - timedelta(days=HOLGURA_HISTORIA_DIAS):
                resumen["omitidos"].append({"partido": pid, "razon": "historia_atrasada"})
                db.rollback()
                continue
            esc, dist = motor_equipo.pronosticar(inst)
            if simulacro:
                resumen["sellados"].append({"partido": pid, "p_local": dist["p_local"], "mu": dist["mu"], "version_datos": inst.version_datos[:12]})
            else:
                h = sellado.sellar(db, PronosticoNuevo(pid, MERCADO, motor_equipo.VERSION_MODELO, inst.version_datos, corte, esc, dist))
                db.commit()
                resumen["sellados"].append({"partido": pid, "hash": h, "p_local": dist["p_local"]})
        except Exception as e:                               # un partido roto no impide sellar los demás
            db.rollback()
            resumen["errores"].append({"partido": pid, "error": f"{type(e).__name__}: {e}"[:300]})
    return resumen


def _ya_sellado(db, pid: int, corte: datetime) -> bool:
    hay = db.execute("SELECT 1 FROM nba.pronostico WHERE partido_id = %s AND mercado = %s AND periodo = 0 AND entidad_id IS NULL "
                     "AND version_modelo = %s AND objetivo_en = %s", (pid, MERCADO, motor_equipo.VERSION_MODELO, corte)).fetchone()
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
    print(json.dumps(resumen, ensure_ascii=False))
    return 1 if resumen["errores"] else 0


if __name__ == "__main__":
    sys.exit(main())
