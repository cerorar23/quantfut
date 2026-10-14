# Eliminación de Chile y Brasil B — 13 de octubre de 2026

El titular pidió eliminar ambas competiciones por completo y confirmó
expresamente el borrado del historial protegido tras conocer sus dependencias.
Se ejecutó la eliminación física en PostgreSQL el 14-oct a las 01:49 UTC
(13-oct, 19:49 de México). Brasileirão Série A permanece activa.

## Resultado

| Datos eliminados | Filas |
| --- | ---: |
| Ligas del catálogo | 2 |
| Partidos canónicos, terminados y futuros | 1.806 |
| Clubes cuya liga doméstica era una de las retiradas | 36 |
| Alias de esos clubes | 49 |
| Clasificación | 36 |
| Originales históricos FotMob/SofaScore en la base | 1.784 |
| XI históricos | 3.518 |
| Estadísticas históricas de jugadores | 73.414 |
| Bajas históricas | 465 |
| Cuotas de API-Football | 71.866 |
| Otras cuotas guardadas | 9.216 |
| Registros de captura de cuotas | 198 |
| Alta probabilidad original / ampliada | 19 / 74 |
| Resultados de alta probabilidad original / ampliada | 18 / 74 |
| Ofertas de sombra sharp / resultados | 159 / 157 |

Había dos pasos de escalera y una pata de parley directamente relacionados
con las ligas retiradas. Para no dejar productos incompletos se eliminaron
los **dos retos afectados completos** (seis pasos y cinco resultados) y el
**ticket de parley afectado completo** (tres patas, tres resultados de pata y
un resultado de ticket). Eso incluye cuatro pasos y dos patas de otras ligas
dentro de esas combinaciones; sus partidos y registros independientes se
conservaron. Las tablas genéricas `predictions` y `picks` no tenían filas
de Chile o Brasil B y no se eliminaron filas de ellas.

Después de confirmar la transacción: **cero ligas, partidos, originales o
clubes de estas competiciones en sus tablas operativas**. Quedan 23 ligas,
13 con modelo habilitado y diez adicionales sin modelo. Los huecos de xG
desde enero de 2024 pasan de 3.118 a 2.073 por retirar estas competiciones;
esa reducción no representa recuperación de xG.

## Protecciones y comprobaciones

- Se seleccionaron las dependencias mediante claves foráneas, incluidas las
  claves compuestas de originales y los grupos completos de retos/parley.
- Se comprobó que ningún club doméstico que se eliminaría era usado por
  partidos de otra competición. Los clubes compartidos de Brasil registrados
  bajo Série A y sus alias no se incluyeron en la eliminación.
- Respaldo anterior al borrado: 25 archivos COPY binarios comprimidos,
  **45.427.123 bytes**, con hash y orden de restauración.
- Una única transacción, bloqueo exclusivo y límites de espera. Solo se
  desactivaron temporalmente triggers `deny_mutation` en tablas con filas
  seleccionadas, bajo la excepción explícitamente autorizada. Cada trigger
  se restauró antes de confirmar; no se cambió la función de inmutabilidad.
- Primera eliminación y repetición dentro de una transacción revertida:
  conteos esperados, segunda eliminación cero escrituras y reversión completa.
- La eliminación real coincidió con la prueba. Todas las filas ajenas a la
  selección de las 40 tablas relacionadas conservaron conteo y huella de su
  contenido; modelo activo y filas de lotes sellados se conservaron.
- Los **15 archivos originales sellados verifican su cadena**. No se
  reescribieron, reseñaron ni eliminaron sus JSON/recibos. La base operativa
  ya no contiene las selecciones retiradas; los archivos y el respaldo son
  evidencia histórica, no entradas disponibles para nueva captura o pronóstico.
- API interna y pública `/leagues` y `/model-card`: HTTP 200. Catálogo de
  23 ligas y modelo `2026.09.27-010508`. `/mobile/v1/home` público: HTTP 200,
  sin IDs de las dos ligas en su respuesta.
- Série A conserva `active`, `model_enabled` y `captura_completa` habilitados,
  junto con sus partidos y datos. No se entrenó ni activó otro modelo.

Los porcentajes de acierto o CLV recalculados desde la base después de este
retiro tienen otra población: no deben presentarse como una mejora del modelo
ni compararse directamente con el histórico anterior sin explicar el cambio.

## Retirada permanente

`db/063_retirar_chile_brasil_b.sql` deja únicamente las dos identificaciones
en `retired_leagues`, con razón y fecha, y bloquea su reintroducción en el
catálogo o los partidos. Esa lista contiene metadatos del retiro, no partidos
ni observaciones deportivas. En una instalación nueva también retira los
clubes/alias de las semillas anteriores cuando no existe historia que purgar.

Se quitaron las competiciones de los catálogos de FotMob y SofaScore. Los
normalizadores, el emparejador y el importador rechazan archivos de las ligas
retiradas. Reanudar un manifest anterior descarta sus partidos antes de
descargar detalles; el recolector soccerdata omite ligas ausentes/inactivas.

Los recolectores se desplegaron sobre fuentes del worker contrastadas con
HEAD, sin reconstruir desde el checkout viejo del VPS y sin reiniciar
servicios. Imagen de recuperación:
`quantfut-worker:before-remove-chile-brasil-b-20261013`
(`sha256:a6b57d30c989c33c654bb675cd342d59419b2c4ac98fe00dc04009e67d5eb794`).
Imagen final persistida como `quantfut-worker:latest`:
`sha256:5cc77eb31138e7716627fa58f346f708bcb5c9cd5a2f2d9574dc1e977033d2a4`.
La recuperación completa requeriría también restaurar la base desde los COPY;
restaurar solo la imagen no recupera los datos eliminados.

Pruebas: **1.049 aprobadas, 24 omitidas**, dos avisos, sintaxis aprobada.
Docker no está instalado localmente; la eliminación/reversión/protecciones se
comprobaron además en el PostgreSQL real del VPS.

## Evidencia

- Local: `.local/remove_chile_brasil_b_20261013/verified/`, con hashes
  cotejados de los 25 respaldos; `public-verification.json` y manifiesto de
  despliegue en su carpeta superior.
- Worker: `/srv/quantfut/artifacts/maintenance/remove-chile-brasil-b-20261013/`.
- Copia en el host: `/home/qf/quantfut/deployments/remove-chile-brasil-b-20261013/verified.tar.gz`.
- `backup.json`, `rollback.json`, `result.json`, `verification.json` y COPY
  por tabla permiten revisar el alcance y recuperar lo retirado si se autoriza.

Los informes actuales de cobertura en `.local/coverage_audit_20261013/` ya
excluyen las dos ligas. Las instantáneas, descargas antiguas y publicaciones
selladas permanecen como respaldo y evidencia anterior; sus menciones no
reintroducen esas competiciones en el sistema. No se enviaron mensajes
externos ni se consumieron nuevas cuotas deportivas durante la retirada.
