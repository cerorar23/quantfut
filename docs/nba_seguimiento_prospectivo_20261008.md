# NBA-RUN-065: props conectados al modelo y piloto prospectivo

El usuario autorizó ejecutar el seguimiento en simulación y aceptó las fuentes
US/AU como referencia. Se conectaron precios reales PTS/REB/AST a pronósticos
condicionados a participación, registrados antes de los partidos. El piloto
exploratorio está activo como registro local; la confirmación científica F7/G7
y la operación comercial conservan sus requisitos pendientes.

Fecha local: 8 de octubre de 2026. Capturas y sellos: 9 de octubre UTC. No se
retrofechan los registros. Los hashes y diarios SQLite son pruebas locales de
integridad, sin anclaje externo de tiempo ni revisión independiente.

## Ejecución comprobada

| Medida | Resultado |
|---|---:|
| Pares Over/Under recibidos, contando ambas capturas | 51 |
| Consultas The Odds API | 12 |
| Créditos: lote inicial + comprobación integrada | 12 + 4 = 16 |
| Pronósticos registrados, contando versiones | 21 |
| Casos únicos evento/jugador/mercado | 15 |
| Jugadores / eventos del proveedor | 5 / 3 |
| Casos únicos por PTS, REB y AST | 5 / 5 / 5 |
| Casos con precio fresco al sellar, en cohorte final | 6 |
| Entradas hipotéticas / apuestas reales | 2 / 0 |
| Resultados futuros oficiales evaluados | 0 |

Los cinco jugadores son Jayson Tatum, Cade Cunningham, Jalen Brunson,
Shai Gilgeous-Alexander y Victor Wembanyama. La primera captura aportó 36
pares y quince pronósticos. Durante la conexión se detectaron filas históricas
corregidas sin campo de namespace: la identidad se recupera exclusivamente de
etiquetas NBA previamente verificadas, después del cruce exacto de
partido/jugador/fecha/temporada/equipo. Se registró la reparación antes de
sellar pronósticos; la primera ejecución fallida permanece como evidencia.

Al sellar esos primeros registros, los precios ya superaban 60 segundos.
Quedaron como referencias, con cero entradas. Después de probar la reparación
se anunció y fijó un máximo adicional de cuatro créditos: `paper-run`
prevalidó el histórico, recibió quince pares de un partido y selló seis
versiones recientes en una sola operación. Sus precios tenían entre 53,75 y
53,98 segundos de antigüedad al sello. Esto acredita frescura en ese momento,
no vigencia actual ni una cotización próxima al inicio del partido.

Las dos entradas son ejercicios de una unidad sobre AST y PTS de Cade
Cunningham. Sus precios proceden de Sportsbet AU; se aplica un contrato
hipotético declarado de participación/DNP-void/prórroga/push. No son tickets,
no acreditan disponibilidad final, acceso de una cuenta mexicana ni reglas
reales de liquidación. No se afirma beneficio obtenido: los resultados están
pendientes. Las tres entradas potenciales de Tatum se excluyeron por su
coincidencia nominal con el feed de incidencias ESPN recibido; la coincidencia
es un candidato sin cruce NBA verificado, y el reporte no acredita su estado
en el evento futuro. El otro mercado de Cade no superó el umbral prefijado.

`evaluation_cohort.json` congela antes de resultados qué versión se evaluará:
las seis recientes para el primer evento y las nueve originales para los
otros dos. Hay quince unidades, no veintiuna observaciones independientes.
Las distintas casas tampoco aumentan el tamaño de muestra.

## Modelo y controles

El protocolo fija Gamma-Poisson de conteos con exposición empírica de partido
completo, incluyendo prórrogas pasadas. Usa las veinte últimas apariciones
positivas, mínimo diez, temporada anterior y actual antes de la fecha UTC
real del sello. No incorpora resultados del mismo día ni datos futuros.
Los 159.075 registros históricos de exposición verificada se cruzaron con
boxscores corregidos para puntos, rebotes y asistencias. El baseline Poisson
usa la media de los diez conteos anteriores.

La extensión de rebotes al inicio de otra temporada y los candidatos nuevos
de puntos/asistencias son exploratorios. No se atribuye a ellos la validación
de otros modelos. No se ajustaron numéricamente lesiones, cambios de rol o
rotación; la disponibilidad final es desconocida y todas las probabilidades
son condicionadas a participación. Ausencia del feed médico no significa
estar sano o convocado.

Se conserva protocolo, historia utilizada, distribuciones completas,
baseline, precio, recibo, edad al sello, exclusiones y fuente de identidad.
El diario rechaza UPDATE/DELETE y el lector comprueba los hashes de los
archivos sellados. La revisión reprodujo exactamente las 21 predicciones y
los 51 pares desde bytes originales. Los comandos no sustituyen salidas
previas ni activan captura periódica.

## Evaluación posterior disponible

`paper-capture-result`, `paper-score` y `paper-summary` permiten recibir un
boxscore oficial, evaluar cada caso y reunir eventos terminados. Se exige ID
NBA, equipos, hora de inicio exacta, jugador, estado final y sello anterior al
inicio. Un jugador ausente del boxscore no se inventa como DNP. Se separan
DNP/inactivos de los conteos condicionados. Los resúmenes rechazan duplicados
y archivos modificados; reportan CRPS, NLL, MAE, cobertura del 80% y Brier
frente al baseline. El beneficio es únicamente hipotético, con CLV ausente.

El CDN oficial respondió 403. Se implementó una alternativa de página oficial
NBA que respondió 200 y se comprobó con HOU–OKC `0022500001`, final con dos
prórrogas: veinte participantes, DNP/inactivos explícitos y sumas de PTS/REB/AST
reconciliadas contra los dos equipos. Esa comprobación de formato es
histórica; no se sustituyó por resultados de los partidos futuros. Las
peticiones futuras con `--game-slug` conservan el mismo ID NBA y el recibo
original. Un HTTP fallido queda registrado y nunca cuenta como resultado.

Se realizaron seis GET públicos: feed ESPN 200, calendario CDN 403, página
de calendario 200 sin datos de los eventos, boxscore histórico NBA 200 y dos
páginas futuras de juegos 403. Los tres eventos conservan IDs del proveedor;
su vínculo oficial NBA y hora deben reconciliarse antes de evaluar. No se
adivinó un ID NBA a partir del nombre de los equipos.

El proveedor fecha DET–BOS y NYK–PHI el 20 de octubre, y SAS–OKC el 21 de
octubre de 2026. Los resultados y disponibilidad cerca del inicio todavía
no se pueden acreditar. La lectura descriptiva del piloto se fija a cincuenta
casos completados o treinta días desde el primer sello. Potencia, efecto
mínimo, reglas de lectura e incertidumbre confirmatoria D07, así como CLV
comparable D08 y contratos aplicables, permanecen pendientes. No se aprueba
G6/G7 ni se cambia una fase a completada por este piloto.

## Archivos y uso

- Seguimiento: `apps/nba/.local/normalized/nba_f6_run65_20261008/tracking.json`.
- Cohorte congelada: `evaluation_cohort.json` en la misma carpeta.
- Referencias iniciales: `registration/`; versiones recientes: `fresh_pilot/registration/`.
- Protocolo: `apps/nba/src/nba/paper_protocol.json`.
- Instrucciones reutilizables: sección de seguimiento prospectivo en `apps/nba/README.md`.

Validación: 66 pruebas pertinentes; suite NBA completa 499 aprobadas y 17
omitidas; arnés general 800 aprobadas y 16 omitidas, final correcto. Se
conservan las 64 corridas anteriores, 20.900 evidencias y prefijo de 167 eventos
del diario general. Sin apuestas, publicación, mensajes, cambios VPS,
suscripciones nuevas ni nuevas copias periódicas. No se instaló un recolector
automático: la recepción, registro y evaluación son operaciones explícitas.
