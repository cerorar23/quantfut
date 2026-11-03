"""F4.4 — Ensayo operativo sobre una COPIA restaurada de la base (nunca sobre producción).

    NBA_DB_DSN=postgresql://admin:...@nba-db:5432/nba_ensayo python ensayo_operativo.py

1. Salud de la copia: tablas, filas, disparadores de inmutabilidad (un UPDATE a nba.dato debe fallar) y lectura punto en el tiempo.
2. La cadena de sellos restaurada se verifica entera.
3. Manipulación: con los disparadores desactivados (solo en la copia) se altera el contenido de un sello y después se rompe un eslabón borrando
   otro; `verificar_cadena` debe detectar las dos cosas con el mensaje correcto.
"""
import json
import os
import sys
import time

import psycopg

from nba.v2 import sellado


def main():
    dsn = os.environ["NBA_DB_DSN"]
    if "ensayo" not in dsn.rsplit("/", 1)[-1]:
        raise SystemExit("este script solo corre contra una base cuyo nombre contiene «ensayo»")
    salida = {}
    with psycopg.connect(dsn, autocommit=True) as db:
        tablas = ["entidad", "captura", "dato", "cuota", "evento", "pronostico"]
        salida["filas"] = {t: db.execute(f"SELECT count(*) FROM nba.{t}").fetchone()[0] for t in tablas}
        salida["disparadores_inmutabilidad"] = sorted(r[0] for r in db.execute(
            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgname LIKE '%inmutable'").fetchall())
        try:
            with db.transaction():
                db.execute("UPDATE nba.dato SET valor = valor WHERE false")
            salida["update_a_dato"] = "PERMITIDO (mal)"
        except psycopg.Error as e:
            salida["update_a_dato"] = "rechazado: " + str(e).splitlines()[0][:80]
        salida["dato_a_las_ahora"] = db.execute("SELECT count(*) FROM nba.dato_a_las(now()) WHERE partido_id IS NOT NULL").fetchone()[0]
        t0 = time.perf_counter()
        salida["cadena_verificada"] = sellado.verificar_cadena(db)
        salida["segundos_verificar_cadena"] = round(time.perf_counter() - t0, 2)
        n = salida["filas"]["pronostico"]
        if n >= 3:
            medio = db.execute("SELECT pronostico_id FROM nba.pronostico ORDER BY pronostico_id OFFSET %s LIMIT 1", (n // 2,)).fetchone()[0]
            db.execute("ALTER TABLE nba.pronostico DISABLE TRIGGER pronostico_inmutable")
            db.execute("UPDATE nba.pronostico SET distribucion = jsonb_set(distribucion, '{p_local}', '0.999'::jsonb) WHERE pronostico_id = %s AND distribucion ? 'p_local'", (medio,))
            if db.execute("SELECT NOT (distribucion ? 'p_local') FROM nba.pronostico WHERE pronostico_id = %s", (medio,)).fetchone()[0]:
                db.execute("UPDATE nba.pronostico SET version_modelo = version_modelo || 'X' WHERE pronostico_id = %s", (medio,))   # sello de jugador: se altera la versión
            try:
                sellado.verificar_cadena(db)
                salida["alteracion_de_contenido"] = "NO DETECTADA (mal)"
            except ValueError as e:
                salida["alteracion_de_contenido"] = "detectada: " + str(e)[:90]
            previo = db.execute("SELECT pronostico_id FROM nba.pronostico WHERE pronostico_id < %s ORDER BY pronostico_id DESC LIMIT 1", (medio,)).fetchone()[0]
            db.execute("DELETE FROM nba.pronostico WHERE pronostico_id = %s", (previo,))
            try:
                sellado.verificar_cadena(db)
                salida["eslabon_roto"] = "NO DETECTADO (mal)"
            except ValueError as e:
                salida["eslabon_roto"] = "detectado: " + str(e)[:90]
    print(json.dumps(salida, ensure_ascii=False, indent=1))
    return 0 if all("mal" not in str(v) for v in salida.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
