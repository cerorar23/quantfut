#!/bin/sh
# Carga en producción (idempotente) el CSV de `python -m qf.ingest.cuota_historica` en futbol.cuota_historica (db/101).
# Uso, desde la raíz del repo en Git Bash:  scripts/rediseno_futbol/cargar_cuota_historica.sh [CSV.gz]
# Todo en UNA transacción: si falla una clave foránea o un tipo, no queda nada a medias. Repetirlo no duplica
# (ON CONFLICT DO NOTHING sobre la clave única). Verifica al final y no toca odds_snapshots.
# El CSV de pandas en Windows termina las líneas con CR+LF; se quita el CR porque el marcador de fin de datos
# que se añade aquí usa solo LF y Postgres rechaza mezclar los dos.
set -eu
CSV=${1:-.local/betsapi_futbol/cuota_historica.csv.gz}
COLS="match_id,fuente,casa,mercado,seleccion,linea,linea_texto,cuota,momento,precio_en,recibido_en,retroactiva,minutos_al_saque,minuto_juego,marcador,corners_vivo,id_en_fuente"
{
  printf 'BEGIN;\nCREATE TEMP TABLE stg (LIKE futbol.cuota_historica INCLUDING DEFAULTS) ON COMMIT DROP;\n'
  printf 'COPY stg (%s) FROM STDIN WITH (FORMAT csv, HEADER true);\n' "$COLS"
  gunzip -c "$CSV" | tr -d '\015'
  printf '\\.\n'
  printf 'SELECT count(*) AS filas_a_cargar FROM stg;\n'
  printf 'INSERT INTO futbol.cuota_historica (%s) SELECT %s FROM stg ON CONFLICT DO NOTHING;\n' "$COLS" "$COLS"
  printf 'SELECT fuente, momento, count(*) FROM futbol.cuota_historica GROUP BY 1,2 ORDER BY 1,2;\nCOMMIT;\n'
} | gzip | ssh quantfut 'gunzip -c | docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -v ON_ERROR_STOP=1'
