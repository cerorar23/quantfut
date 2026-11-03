# NBA — `nba_api` por proxy: 86 de 95 partidos recuperados con conteos extendidos (26-oct-2026)

Encargo del titular: probar `swar/nba_api` por proxy, con un tope de gasto, solo para los 95 partidos regulares y las rotaciones
pendientes, con el contrato de aceptación vigente. **No se usa la librería**: lo que sirve son los endpoints que ella consume
(`BoxScoreTraditionalV3`, `GameRotation`), llamado a través de ZenRows desde `nba.stats_proxy`. No entrena ni promueve nada.

## Acceso
| Ruta | Resultado el 26-oct |
| --- | --- |
| `stats.nba.com` directo (PC y VPS) | sin respuesta tras 20-35 s |
| `cdn.nba.com` directo (PC y VPS) | 403 |
| ZenRows, proxy básico (1 crédito) | BoxScoreTraditionalV3: 95/95 en ~1,3 s cada uno |
| ZenRows, proxy premium (10 créditos) | BoxScoreTraditionalV3 correcto; GameRotation de partidos antiguos: 422 |

El proxy básico basta para los boxscores: el premium del primer ensayo (10 créditos) era innecesario. `proxy_country` solo se
admite con premium (error de parámetro, 0 créditos).

**Tope de gasto fijado: 450 créditos** (Free, 5.000/mes, 1.212 libres al empezar). Gasto real **106**: 10 (ensayo premium) + 95
(boxscores) + 1 (rotación). Quedan 1.106 hasta el 6-nov. El tope se aplica dentro de `capture()` antes de cada petición y la
captura se detiene tras dos fallos seguidos; sin reintentos en bucle. La clave se lee de `.zenrows/secrets.json` o de
`ZENROWS_API_KEY` y no aparece en recibos ni en el informe.

## Qué eran los «95» y las «rotaciones pendientes»
Mi resumen anterior arrastraba cifras del 6-oct que ya estaban cerradas (NBA-RUN-040: 6.150/6.150 boxscores, rotaciones 6.141/6.150).
Los huecos reales de hoy son otros:

- **95 partidos regulares sin conteos extendidos** (tiros, libres, rebote ofensivo/defensivo, pérdidas, faltas, +/-): 42 puestos en
  cuarentena en la base de v1.x (`nba_f6_run71`, 6.108 de 6.150) y 53 que están en la base pero no en `nba_extended_box_20261024`.
  Las dos fuentes secundarias discrepaban o faltaba la referencia de equipo.
- **Rotaciones**: pendientes **9** (no 562): 0022100074, 0022100151, 0022100353, 0022200793, 0022201007, 0022201040, 0022201205,
  0022400831, 0022401211.

## Resultado: boxscores (contrato de aceptación)
Cada caja oficial se acepta solo si cumple, sin imputar nada: identidad de partido y de los dos equipos; localía; minutos `MM:SS`
válidos (**`:60` nunca se convierte**); suma de jugadores = total de equipo en 15 conteos; identidades de puntos/rebotes/tiros por
jugador; minutos de equipo = 240 + 25·prórrogas (tolerancia 0,15); sin empate; y acuerdo con las filas base en puntos, rebotes,
asistencias y minutos (tolerancia 0,25 min) de todo participante.

**86 aceptados (2.264 filas)**: 41 de 2025-26, 31 de 2024-25, 10 de 2023-24, 4 de 2022-23; 39 de los 42 fuera de la base y 47 de los 53.
Contraste independiente: los **1.869 participantes** coinciden en los 16 conteos con al menos una de las dos fuentes secundarias
(ninguna discrepancia). Esas fuentes no habían podido arbitrar porque faltaban o chocaban en otros jugadores del mismo partido.

**9 rechazados, se quedan en cuarentena:**
| Partido | Motivo |
| --- | --- |
| 0022300176, 0022300835, 0022400802, 0022400919, 0022400928, 0022500802, 0022500835 | la fuente oficial trae minutos `:60` y la suma del equipo no cuadra; el contrato prohíbe convertirlos |
| 0022300860 | la caja oficial deja a Lester Quiñones sin minutos ni puntos, la base lo da con 22,6 min y 6 puntos |
| 0022100151 | Bol Bol figura con `0:00` y 2 tiros libres fallados; la base lo marca no participante. Es probablemente un participante legítimo, pero aceptarlo cambia la semántica de `participated` y queda decidirlo |

## Resultado: rotaciones
`GameRotation` oficial devuelve **422 (RESP001) para 8 de las 9** con ambos niveles de proxy, 0 créditos cobrados; se paró sin
bucles. Se recuperó **0022100151** y pasa la comprobación de cinco en cancha durante todo el partido sin solapes, con puntos y
minutos coherentes (`validate_rotation`). Quedan 8 rotaciones sin fuente accesible por esta vía.

## Estado y límites
- Las 86 cajas **no están fusionadas** en `nba_extended_box` ni en la base de entrenamiento: cambiaría el conjunto de entrenamiento
  (+1,4 % de partidos; 41 de ellos de la temporada en curso) y exige reajuste con protocolo congelado. Salida lista en
  `apps/nba/.local/normalized/nba_stats_proxy_recovery_20261026/` (`players.jsonl.gz`, `games.json`, `report.json`). Originales y
  recibos con SHA-256 en `apps/nba/.local/raw/nba_stats_proxy_20261026_basic/`.
- `possessions` y `pace` quedan `None` en los equipos recuperados (la caja tradicional no los trae); `possessions_estimate` sí se deriva.
- Es la misma procedencia NBA que las demás fuentes, no un proveedor independiente.
- Los datos de NBA.com tienen sus términos de uso: úsese como respaldo interno de entrenamiento, no se muestran tal cual en la web.
- El motor en vivo no usa rotaciones; no hay urgencia por las 8 restantes.

## Código
`apps/nba/src/nba/stats_proxy.py` (captura con tope, `validate`, `validate_rotation`, `recover`) y
`apps/nba/tests/test_stats_proxy.py` (18 pruebas: caja válida, 7 corrupciones, desacuerdo con la base, empate, rotación, tope de
créditos, parada tras dos fallos). Cliente HTTP: `httpx`.

## Error corregido de paso
Tres pruebas de `test_paper_bundle.py` caducaban por reloj: el plazo `2026-10-22` estaba fijo en `paper_bundle.build_bundle` y las
pruebas usan la hora real. Ahora es la constante `DEADLINE_UTC` y las pruebas la fijan relativa a su reloj. Suite NBA completa en verde.
