# Importación histórica FotMob — 13 de octubre de 2026

El usuario autorizó importar el archivo histórico y confirmó explícitamente la
transferencia, el importador, la migración y las verificaciones en el VPS
`quantfut`. No se realizan nuevas consultas a proveedores deportivos.

## Archivo y correspondencias

Archivo: `.local/fotmob-history/2024-01-01_2026-10-03/`. Se valida cada original
comprimido contra su SHA-256 sin comprimir y recibo, competición, IDs de equipos,
fecha y estado terminado. Se aceptan **22.456 partidos de 25 competiciones**;
faltan tres originales Championship (4520607–4520609), y dos Brasil A
(4732649, 4732669) discrepan en fecha y quedan excluidos.

Cuatro originales contienen estadísticas de jugadores con `id=0`: los partidos
4217712, 4436186, 4436209 y 4436417 se conservan; solo se omiten esos registros
individuales sin identidad. El original completo sigue disponible.

Los clubes se resuelven por nombre o alias exacto dentro del mismo país, incluso
si ascendieron o descendieron. Tres encuentros independientes con rival,
marcador y fecha coincidentes corroboran variantes de nombres. No se aprueba
ninguna asociación difusa automáticamente. El plan revisado reutiliza Arsenal,
Athletic de Bilbao, Athletico-PR y Chapecoense, y da de alta únicamente once
clubes domésticos históricos ausentes: cuatro Chile y siete Brasil B. Nunca
se crean clubes bajo Champions/Europa League.

Los encuentros existentes necesitan equipos, competición, fecha dentro de 36
horas, resultado terminado y marcador coincidentes. Los partidos nuevos requieren
equipos resueltos y ausencia de un encuentro cercano de esos clubes en la misma
competición. La base se vuelve a comprobar durante la carga; una discrepancia
conserva el original sin tocar el partido canónico.

## Almacenamiento y tiempo de recepción

`db/062_historico_futbol_fuentes.sql` añade cuatro tablas:

- `historical_football_matches`: original comprimido, metadatos, hash, fecha de
  recepción, métricas y asociación canónica o motivo pendiente.
- `historical_football_lineups`: XI y suplentes con IDs propios del proveedor.
- `historical_football_player_stats`: estadísticas individuales; ausente es
  `NULL`, no cero, y los IDs FotMob no se mezclan con API-Football.
- `historical_football_absences`: bajas declaradas al consultar el histórico.

La observación se congela por `(provider, source_match_id)`; un hash o recibo
distinto provoca rechazo. Las correspondencias son únicas por proveedor y
partido. Los datos verificados sin correspondencia también se guardan completos.

El xG rellena únicamente parejas canónicas vacías, con `xg_source='fotmob'` y
la recepción real del 3 de octubre; no cambia xG existente. Los conteos de
tiros/córners solo rellenan valores ausentes. El control temporal del modelo
se extiende a toda fuente con procedencia: no se utiliza xG antes de su recibo.
El replay secuencial Kalman conserva goles hasta disponer de eventos de llegada.

Las nuevas tablas de XI, jugadores y bajas son históricas: la importación no
las convierte en capturas anteriores al encuentro ni integra automáticamente
sus IDs en los consumidores existentes de API-Football. Su aprovechamiento
modelístico requiere adaptación y validación posterior. No se activa ninguna
liga, captura pagada, candidato, entrenamiento, publicación o alerta Telegram.

## Pruebas y evidencia

Pruebas específicas: originales, IDs inválidos, promociones, países, marcador,
ambigüedad, duplicados y disponibilidad temporal. Prueba PostgreSQL con 53
encuentros que cubren todos los tipos de asociación: segunda carga con cero
escrituras y reversión exterior confirmada. El arnés final pasa con 1.007
pruebas aprobadas, 24 omitidas y dos avisos; Docker local no está disponible.

El respaldo completo de 20.816 partidos y el estado previo quedan en
`/srv/quantfut/artifacts/imports/fotmob-20261013/` dentro del worker; la imagen
anterior es `quantfut-worker:fotmob-before-20261013`. Se guarda el worker actual
sin reconstruir desde el checkout del VPS, preservando los despliegues ajenos.

SHA-256 del archivo normalizado:
`266e222c97f38d0bafa0fcbfe01506bb16c146766d0781eb7872e01c90c7a4a6`.

## Resultado confirmado

Carga completada el 13-oct a las 20:06 UTC (14:06 CDMX), en 9 minutos y 47
segundos. Verificación posterior a las 20:09 UTC:

- 22.456 originales persistidos, 568.351.577 bytes comprimidos.
- 44.912 alineaciones de equipo, 940.386 registros de estadísticas individuales
  y 48.571 declaraciones históricas de bajas.
- 19.631 originales con pareja xG; 14.629 parejas incorporadas a partidos
  canónicos previamente vacíos.
- 20.502 asociaciones existentes y 1.554 partidos nuevos; once equipos nuevos.
- 400 originales conservados sin vínculo utilizable: 379 identidades pendientes
  en copas y 21 conflictos de asociación/marcador. No se fuerzan esas uniones.
- 8.537 partidos completados en conteos de tiros/córners ausentes.
- Se cotejaron los 20.816 partidos del respaldo: competición, equipos, temporada,
  estado, resultado, xG y conteos previos no vacíos y todas las claves externas
  anteriores conservados. Cero conflictos entre vínculos persistidos y resultados.
- Todos los originales se comprobaron antes de su inserción; además se releen
  25 originales de PostgreSQL, uno por competición, con hash coincidente.
- Las 14.629 parejas FotMob están excluidas antes del 3-oct y disponibles tras
  su recepción. Esto no acredita mejoras retrospectivas en backtests.
- XI y estadísticas antiguas API-Football conservan 9.112 y 156.470 filas.
  Durante la importación corrió el cron de lesiones ya existente a las 20:00:
  añadió 324 observaciones (20:00:06–20:01:08), explicando el cambio de 16.033
  a 16.357 en `injuries`. El importador nunca escribe en esa tabla ni modifica
  ese cron.
- Ligas/model_enabled/captura_completa y lotes sellados coinciden con el estado
  previo. Sigue activo `2026.09.27-010508`; API interna y pública responden 200
  y devuelven esa misma versión. No se lanza otro entrenamiento.

## Cobertura persistida por competición

«Enlazados» incluye encuentros existentes y nuevos; la cobertura restante
permanece guardada íntegra. Las bajas son declaraciones recibidas al consultar
el histórico, sin garantía de exhaustividad o recepción anterior al encuentro.

| Competición | Originales | Enlazados | xG en fuente | XI ambos | Estadísticas ambos | Partidos con bajas |
|---|---:|---:|---:|---:|---:|---:|

| ar.primera | 1.296 | 1.291 | 1.296 | 1.296 | 1.296 | 781 |
| br.serie_a | 1.036 | 1.036 | 1.036 | 1.036 | 1.036 | 680 |
| br.serie_b | 1.066 | 1.064 | 686 | 1.066 | 1.066 | 140 |
| ch.super_league | 630 | 630 | 630 | 630 | 630 | 482 |
| cl.primera | 662 | 661 | 0 | 662 | 661 | 117 |
| de.bundesliga | 810 | 810 | 810 | 810 | 810 | 727 |
| de.bundesliga2 | 819 | 819 | 819 | 819 | 819 | 649 |
| dk.superliga | 531 | 531 | 531 | 531 | 531 | 415 |
| es.laliga | 1.029 | 1.029 | 1.028 | 1.029 | 1.028 | 820 |
| es.laliga2 | 1.252 | 1.252 | 549 | 1.252 | 1.252 | 843 |
| eu.ucl | 425 | 283 | 425 | 425 | 425 | 377 |
| eu.uel | 441 | 195 | 441 | 441 | 441 | 341 |
| fr.ligue_1 | 810 | 810 | 810 | 810 | 810 | 601 |
| fr.ligue_2 | 862 | 862 | 370 | 862 | 862 | 89 |
| gb.championship | 1.461 | 1.461 | 1.461 | 1.461 | 1.461 | 1.250 |
| gb.premier_league | 994 | 994 | 994 | 994 | 994 | 870 |
| it.serie_a | 1.010 | 1.010 | 1.010 | 1.010 | 1.010 | 897 |
| it.serie_b | 1.028 | 1.028 | 441 | 1.028 | 970 | 781 |
| mx.liga_mx | 923 | 923 | 923 | 923 | 923 | 625 |
| nl.eredivisie | 846 | 846 | 846 | 846 | 846 | 691 |
| no.eliteserien | 647 | 647 | 647 | 647 | 647 | 265 |
| pt.primeira | 845 | 845 | 845 | 845 | 845 | 660 |
| se.allsvenskan | 656 | 653 | 656 | 656 | 656 | 301 |
| tr.super_lig | 911 | 911 | 911 | 910 | 911 | 677 |
| us.mls | 1.466 | 1.465 | 1.466 | 1.466 | 1.466 | 729 |

Chile sigue sin xG en esta fuente. LaLiga 2, Ligue 2, Serie B y Brasil B tienen
xG parcial, por lo que la importación no elimina todos sus huecos.

Evidencia local: `.local/fotmob_import_20261013/verified/` y
`.local/fotmob_import_20261013/public-model-card.json`; equivalente dentro de
`/srv/quantfut/artifacts/imports/fotmob-20261013/` en el worker.

SHA-256 del paquete de evidencia:
`914992f5b0fc822c2cce86a7d9341c3730d92b6d7efba33ce6daa1796f868862`.
