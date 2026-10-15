# Carga de OddsPapi — 15-oct-2026

El usuario pidió expresamente cargar los datos recuperados en la base.
La carga quedó confirmada: **2.918 cierres reconstruidos, 8.754 cuotas**, más
**25 referencias conservadas para revisión**. Los 2.943 registros y su procedencia
están en la base; solo los 2.918 aprobados alimentan los consumidores de cierre.
Los huecos de Pinnacle desde 2024 bajaron de **6.185 a 3.267**.

No se certifican como cierres oficiales: se mantiene `close_verified=false` en
la procedencia y `source='oddspapi_reconstructed'` en las cuotas. La carga no
reentrenó ni activó modelos; el activo sigue siendo `2026.09.27-010508`.

## Validación y tratamiento de referencias

Se comprobaron los 2.943 cuerpos originales completos contra sus SHA-256,
se recalcularon sus precios 1X2 y se revisaron las identidades contra producción.
Todos corresponden a partidos finalizados existentes, con equipos, marcador y
horario de la base sin cambios desde la asociación inicial; ninguno tenía ya
un cierre Pinnacle. No se crearon equipos ni partidos.

Las 23 ternas con `quality=review` tienen al menos un precio de más de una hora;
cuatro tampoco tienen historial posterior al corte. Además, seis registros
tienen el corte de la fuente después del kickoff que conserva nuestra base:
cuatro ya estaban entre las 23 y dos son adicionales. Por eso se retienen **25**.
No se cambian horarios ni se introducen sus cuotas en `odds_snapshots`.

Estas referencias se guardan exclusivamente en `historical_odds_backfills`:
algunos consumidores existentes seleccionan el último precio sin filtrar
`window_tag`; introducirlas allí con otra etiqueta también contaminaría el cierre.
La nueva tabla conserva el extracto original íntegro del mercado 101 comprimido,
su hash, el hash del cuerpo original completo, URL sin clave, recepción real,
identidad, razones de revisión y normalización. Se protege contra UPDATE/DELETE.

Los 2.918 aprobados se insertan como ternas completas del mismo momento efectivo:
`captured_at` es el corte reconstruido de fuente menos un microsegundo;
`book_updated_at` conserva el cambio real de cada selección. `mins_to_kickoff`
se calcula respecto al horario existente de la base, sin inventar cero minutos.
La recepción real del archivo queda separada en `received_at` y en los recibos.
Se validó `book_updated_at < captured_at < kickoff_utc` para todas las cuotas.

## Respaldo y comprobación transaccional

Antes de confirmar se ejecutó la carga dentro de una transacción de ensayo:
8.754 cuotas y 2.943 filas de procedencia; repetir insertó cero de ambas.
Se revirtió todo y se comprobó la ausencia de la tabla nueva y la conservación
exacta de las cuotas anteriores. Los saltos normales de secuencia no se revierten.

La carga definitiva bloqueó brevemente las inserciones concurrentes de cuotas,
guardó el respaldo completo antes de escribir y confirmó todo en una transacción.
Se verificaron de nuevo todas las ternas almacenadas, su redondeo REAL, fechas,
selecciones y referencias; la repetición insertó cero. Los hashes de partidos,
equipos, predicciones, picks, modelos y cuotas previas permanecieron iguales
dentro de la transacción; los triggers de inmutabilidad siguen activos.

El respaldo completo contiene **444.756 snapshots previos** y permanece en el
volumen persistente de artefactos del servidor:
`/srv/quantfut/artifacts/imports/oddspapi-20261015/odds_snapshots_before.copy.gz`.
Se verificaron allí su SHA-256, CRC de gzip y cabecera COPY binaria de Postgres.
La revisión automática rechazó descargar la tabla completa al equipo local por
no existir autorización específica para esa exportación; no se descargó ni se
intentó otra vía. Esto no impidió respaldar, verificar y completar la carga.

## Evidencia y reproducción

- `data/pinnacle_recovery/20261014_oddspapi/carga_20261015.json`: recuentos,
  idempotencia, estado de producción y comprobante del respaldo.
- `data/pinnacle_recovery/20261014_oddspapi/carga_resultado.csv`: estado de las
  2.943 filas y razones de las 25 referencias.
- `.local/oddspapi_import_20261015/`: validación local, paquete revisado y
  resultados del ensayo/aplicación; sin copia del respaldo completo.
- En el servidor, el mismo directorio de importación conserva entrada, extractos,
  manifiesto, ensayo, aplicación y recibos. El manifiesto de 2.946 archivos se
  comprobó después de transferirlo.
- `db/070_historical_odds_backfills.sql` y `scripts/import_oddspapi_closes.py`:
  procedencia e importador; por defecto solo planifica. No aplicar otra vez sin
  revisar primero el resultado y conservar el respaldo original.

Pruebas: **1.237 pasaron, 60 omitidas**, además del ensayo real de Postgres,
reversión, repetición sin duplicados y consultas posteriores al commit.
