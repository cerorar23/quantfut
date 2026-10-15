# Recuperación con OddsPapi — 14-oct-2026

**Carga autorizada y confirmada el 15-oct:** 2.918 cierres reconstruidos
(8.754 cuotas) en producción; 25 referencias guardadas exclusivamente para revisión.
Todos los 2.943 registros tienen procedencia en la base. Cierres completos pendientes
desde 2024: 3.267. Ver `carga_20261015.json`, `carga_resultado.csv` y
`docs/oddspapi_carga_20261015.md`. El resto documenta la recuperación anterior a la carga.

La consulta terminó el 15-oct-2026 a las 03:46, hora de Ciudad de México:
6.094 eventos consultados, 2.943 ternas reconstruidas (2.920 `recent` y 23 `review`),
3.151 sin histórico, 87 sin fixture y cuatro cancelados en la fuente. Se recorrió
toda la cola; siguen 3.242 filas de la lista original sin recuperar con esta API.
`informe.json` y los CSV contienen el resultado final.

- `pinnacle_recuperado.csv`: ternas Pinnacle 1X2 anteriores al inicio, asociadas
  exclusivamente a partidos de la lista original. Incluye identidad de fuente,
  fechas de cada precio, fecha de captura, corte utilizado y hash del original.
- `lista_resultado.csv`: las 6.185 filas originales con el estado de búsqueda.
  Las columnas originales de cierre permanecen intactas; las ternas recuperadas
  están en el archivo anterior para su revisión antes de cualquier carga.
- `reviewed_names.json` y `name_review_receipt.json`: equivalencias explícitas
  con equipos existentes y evidencia de la revisión. No se crean clubes ni partidos.
- `exclusions.json`: cuatro filas que OddsPapi marca como canceladas; requieren
  conciliación con la base antes de utilizar cualquier precio.

## Qué significa el precio

Se consulta exclusivamente `bookmakers=pinnacle`, mercado 101 (Full Time Result),
resultados 101/102/103 y jugador 0. Se elige la última cotización activa anterior
al menor del inicio programado y el inicio real de OddsPapi, si este existe.
Se excluyen suspensiones y todos los precios iguales o posteriores a ese corte.
`active=null` se admite como indica el ejemplo publicado por el proveedor.

Es un **cierre reconstruido del historial**, con un corte conservador; la API v4
no etiqueta un registro como cierre oficial certificado. Por ello se conserva
`close_verified=False`. El campo `quality=recent` exige además menos de una hora
de antigüedad, historial posterior al corte y una suma de probabilidades plausible.
Los registros con `quality=review` requieren revisión adicional. La carga autorizada
del 15-oct insertó 2.918 cierres reconstruidos y retuvo 25 referencias, como se
detalla al inicio de este documento. No se han entrenado modelos.

El horario de nuestro CSV se interpreta como UTC, tal como indica su encabezado.
Se conserva por separado el horario de OddsPapi: hay diferencias de una hora en
algunas competiciones. El emparejamiento exige nombres/alias revisados, misma
competición y una única coincidencia dentro de ±36 h.

## Originales y proceso

Por volumen, los originales completos comprimidos, recibos, índice de partidos,
progreso del proceso y credencial cifrada permanecen fuera de Git en
`.local/oddspapi_20261014/`. Los originales están en `originals/`; sus recibos
contienen la URL sin clave, estado HTTP, fecha de captura y SHA-256 de los bytes
descomprimidos. Los cuatro sondeos iniciales señalan su conversión desde PowerShell.

El CSV original sigue intacto; su SHA-256 esperado es
`3a418b365b51409bed24842cb7897ae5dea146b1740f4d778c80cbedaf9b1eaf`.

El proceso consulta cada evento, respeta una pausa mínima de 5,15 s después de
cada respuesta de histórico, guarda también los 404 y reanuda desde los recibos
sin repetir éxitos ni ausencias. Una cerradura del sistema impide dos recolectores
simultáneos sobre esta carpeta. Reintenta errores transitorios con espera;
los fallos persistentes quedan en `worker_state.json` y conservan lo descargado.

El primer lote recuperó 51 ternas con calidad `recent`. Tras revisar 48 equivalencias,
se asociaron 6.094 partidos; quedan 87 sin fixture en el índice y cuatro cancelados
en OddsPapi. Estos números de asociación no son números de cuotas recuperadas.

## Documentación utilizada

- [Historial v4](https://oddspapi.io/us/docs/get-historical-odds).
- [Cupo: histórico gratuito, calendario facturable](https://oddspapi.io/us/docs/requests-and-quota).
- [Extracción del cierre anterior al inicio](https://oddspapi.io/blog/team-ratings-from-closing-odds/).

La suscripción comprobada es gratuita, con 250 consultas facturables. No se ha
comprado ni cambiado ningún plan. La clave está cifrada con DPAPI, fuera de Git;
el recolector la recibe por entorno y no la registra en sus recibos.
