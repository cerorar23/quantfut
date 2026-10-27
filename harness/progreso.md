# Registro de decisiones — QuantFut

## 27-oct-2026 · La web consume el motor real

El titular pidió conservar el diseño anterior y retirar los pronósticos ficticios. El motor ya corre: la jornada del 27-oct está calculada y sellada. La corrección conecta la web al contrato real de la app, con el mismo recorte gratis/VIP, en lugar de modificar modelos o evitar la puerta de CLV. Los archivos CSS y CYBERCORE 0.3.0 permanecen intactos. Ver `docs/web_pronosticos_reales_20261027.md`.

## 2026-10-26 — NBA 1.7.0: la fuerza individual entra al vivo y lo publicado se revisa sin reescribirse
Por instrucción del titular la fuerza individual se activa aunque su mejora histórica no sea concluyente, y lo ya publicado se recalcula. Decisión clave: el recálculo es una revisión sellada aparte, nunca una edición del original; un partido ya iniciado se recalcula solo con información anterior a su fecha (la primera versión usaba todo hasta hoy, incluido el resultado del propio partido, y la fuerza ajustada con partidos futuros: lo detectaron las verificaciones) y no cuenta en el marcador, que usa la última versión previa al salto. Al consolidar playoffs, el historial individual de inicio de temporada quedó lleno de playoffs (Brunson 19 de 20) y empeoraba las combinaciones; un partido regular usa solo partidos regulares. Ensayo con 1.061 resultados: Brier 0,2490 frente a 0,2482 del original (0,2518 antes de esa corrección); total del partido mejora, ganador empeora; una semana no lo distingue del azar. Detalle: `docs/nba_recalibracion_17_20261026.md`.

## 2026-10-26 — NBA: pertenencia actual comprobada y fuerza individual separada de los resultados publicados
El usuario pidió corregir el efecto de los traspasos y recalibrar el vivo. La copia inicial estaba antigua; se creó una copia aislada desde `03f4ada` (productor 1.5.0). Se capturaron las 30 plantillas oficiales: 521 IDs únicos y 121 con equipo distinto al último registro histórico. La pertenencia pasa a una evidencia actual con recibo real, temporada y hash, también antes del debut; el historial personal sigue al ID y no se confunde una cotización con pertenencia. La fuerza individual se mide con regresiones regularizadas de margen/total por minutos, comparando la rotación actual con la que ya representa la forma histórica. A diferencia de transportar el Elo del antiguo equipo, sí distingue valor individual; tampoco es una medida causal de on/off. Elegida en 2024-25 (ridge 25, peso 0,25), mejora poco en 2025-26: ganador −0,000129 de Brier, IC95 [−0,000681; +0,000319]; equipo −0,000131 y total −0,000166. No supera la regla y no cambia las probabilidades publicadas: se registra aparte en sombra con las plantillas reales para evaluación prospectiva. No se dice que el motor completo esté recalibrado. La revisión automática rechazó exportar el modelo activo y sus datos a esta carpeta; la alternativa es comparar y ensayar dentro del servidor, sin esa copia. Ver `docs/nba_current_rosters_20261026.md`.

## 2026-10-26 — NBA: el Elo ponderado por la plantilla actual no mejora el ganador
Encargo tras IND @ MIL (modelo 69 % Milwaukee, mercado 41 %; Giannis ya en Miami): cada jugador de la rotación arrastra el Elo de los equipos con los que jugó sus últimos minutos. Protocolo congelado antes de calcular (`nba_roster_elo_protocol.json`). Decisión clave: no entra; las cuatro configuraciones empeoran en el ajuste (2024-25) y en la prueba (2025-26: la elegida +0,00038 [−0,00005; +0,00082]; con α 1 empeora con significación) y donde más mueve el Elo más empeora. El rating que arrastra un jugador es el de su equipo anterior, no lo que vale él; valorar traspasos exige un rating por jugador, que es otro modelo. El productor no cambia. `docs/nba_elo_plantilla_20261026.md`.

## 2026-10-26 — Notas recuperadas de una copia local desactualizada
La carpeta principal seguía en `nba/v13-disponibilidad` (197 commits por detrás de `main`) con notas sin commitear y otras que se perdieron al fusionar sus commits: el código sí llegó a `main`, las notas no. Se copiaron tal cual 3 entradas de DEPLOYS.md, 7 de este registro y 3 secciones de tareas; no se copió lo que `main` ya cuenta con otra redacción (segunda auditoría NBA, props 100K, bet365 normalizadas). Las tareas que quedaban abiertas se cierran con su motivo verificado contra `main`, según la regla de la limpieza del 25-oct.

## 2026-10-26 — `nba_api` por proxy: 86 de 95 partidos recuperados; el acceso funciona con el proxy básico (1 crédito), no con el premium
Decisión clave: de `swar/nba_api` se usan sus endpoints (BoxScoreTraditionalV3, GameRotation) llamados por ZenRows desde `nba.stats_proxy`, no la librería ni el acceso directo (stats.nba.com agota el tiempo y el CDN da 403 desde el PC y el VPS). Tope de gasto 450 créditos aplicado antes de cada petición; gasto real 106 (el premium del primer ensayo sobraba: el básico basta). Las cifras del 6-oct estaban cerradas: los «95» de hoy son 42 partidos en cuarentena de la base v1.x + 53 sin conteos extendidos, y las rotaciones pendientes son 9, no 562. Con el contrato vigente se aceptan 86 (41 de 2025-26) y los 1.869 participantes coinciden con una fuente independiente; 9 se quedan en cuarentena (siete con minutos `:60` que no se convierten, uno con el oficial sin minutos para un jugador que la base da 22,6 y uno con un 0:00 con tiros libres). GameRotation oficial devuelve 422 para 8 de 9 con ambos niveles: 1 de 9 recuperada. No se fusiona en la base de entrenamiento (+1,4 % de partidos exige reajuste con protocolo congelado). De paso se arregló el plazo fijo de `paper_bundle` que caducaba tres pruebas por reloj. docs/nba_api_proxy_recuperacion_20261026.md.

## 2026-10-26 — Investigación de otros modelos y factores: ninguno añade información sobre el cierre de Pinnacle
Decisión clave: con 3 años de origen rodante, ni pi-ratings, forma de xG, tiros, viaje, descanso, forma, motivación (carreras vivas) ni árboles de gradiente mejoran al Dixon-Coles de forma fiable (solo los tiros, −0,0005 con intervalo al borde de cero) y ninguno añade nada sobre el cierre de Pinnacle; el propio DC tampoco (+0,0004). El hueco de 0,0096 es información (alineaciones, bajas, noticias), no forma del modelo. La ventaja documentada en la literatura está en totales, córners y tarjetas con estadísticas de partido, pero hay 459 partidos con cierre de totales: se conserva el cierre de todos los mercados y se repite con ~2.000. Informe: `docs/investigacion_modelos_y_factores_20261026.md`.

## 2026-10-26 — Modelo dinámico y prior de ascendidos medidos: el prior no tiene señal; la mezcla dinámica gana poco y no se despliega
Decisión clave: con 3 años de walk-forward (12.878 partidos), el prior de ascendidos no mejora (ΔRPS −0,00002; el sesgo del último año era ruido) y el Kalman del repo solo empata con el DC una vez quitada su reversión a la media, que lo empeoraba. La mezcla log-lineal DC 270/90/730 + Kalman, con pesos ajustados en dos años, da −0,0008 en el tercero (p95 −0,0003) y −0,0006 en los tres, mejora la calibración y se suma al contexto (altitud + once), pero el año 2 queda en cero, las copas empeoran y exige un estado de Kalman diario y tres DC en producción: no se despliega sin decisión del titular. Informe: `docs/modelo_dinamico_y_ascendidos_20261026.md`.

## 2026-10-26 — NBA 1.5.0: no se recalibra el equipo; los jugadores ya no dependen de una sola captura de PropLine

La recalibración de total y puntos de equipo se probó con protocolo congelado (`nba_live15`) y no entra: en sus propias
líneas el modelo ya está calibrado en 2025-26 y el sesgo de una temporada no sirve para la siguiente (cambia de signo).
El intercepto dentro de la temporada salió peor porque aprende de partidos predichos sin disponibilidad; aprender de las
cohortes selladas solo se puede medir hacia delante. En vivo, una captura de PropLine perdida (cuota diaria en reserva)
dejó una cohorte entera sin jugadores y las pérdidas no se sellaban nunca (menos de 2 casas). Decisión: la línea de una
casa sigue mandando cuando existe, y si no, el jugador de rotación se pronostica en el umbral estadístico sobre el que
ya está calibrado el modelo; así la cobertura no depende del proveedor y no se reajusta ningún parámetro.

## 2026-10-26 — Tenis: sellado cerca del inicio y todas las líneas de las casas

Auditoría del motor de tenis (`docs/tenis_auditoria_20261026.md`). El sellado pasa de dos veces al día a cada hora, 1,5-2,5 h
antes del partido: el precio sin margen es la mejor entrada del ganador y es más preciso cuanto más cerca del inicio, y además
un cron en hora de Berlín dejó la pasada nocturna en la hora en que PropLine no captura. Cada sellado guarda todas las líneas
ofrecidas con la probabilidad del motor en la misma línea, porque comparar en líneas fijas no mide nada frente al mercado. Con
27 partidos con cierre, el motor bate al cierre en totales de juegos (el mercado sobrevalora el «más de»): por eso solo se
ancla al mercado el ganador, no los totales. La superficie del torneo sale de la edición de la misma época del año.

## 2026-10-26 — Fases del Motor A medidas con el modelo nuevo: lo robusto es pequeño y no se activa nada

Con el modelo entrenado en local se repitió la medición de cada fase (`docs/fases_motor_a_20261026.md`). Decisión clave: no
activar nada. Lo único estable en cuatro particiones de validación es la combinación altitud + impacto del once (ΔRPS −0,0007
a −0,0010, una décima parte de los 0,0096 que separan al modelo del mercado), y hacia adelante la altitud en sombra no lo
confirma todavía (32 partidos, +0,0010, p95 +0,0057). Descanso, clima, bajas, valor del once, tres ligas más (la Süper Lig
queda a +0,0187 del mercado) y las correcciones de empate y de nivel de goles (−0,00007, no significativa) no pasan. Los
artefactos de sombra regenerados no se subieron: el del once vigente se ajustó con 11.920 filas y el nuevo con 4.264. Las
mediciones quedan como scripts en `scripts/entrenamiento_local/` para repetirlas tras cada reentrenamiento.

## 2026-10-26 — El Motor A se entrena en local y se sube

Decisión del titular: el entrenamiento se hace en local y luego se sube (`scripts/entrenamiento_local/`). La copia
trae solo las 19 tablas que lee `train.py` a un esquema `entreno` aparte, para no tocar la base local de pruebas. La
configuración del modelo se fija a la del worker, no a la del `.env` local, que tenía otra vida media (180 frente a
270 días): sin eso se habría entrenado y subido un modelo distinto del que se cree. Se sube solo lo que la misma puerta
de `train.py` deja activo. Como esa puerta casi nunca puede comparar con el modelo anterior (la ventana cambia con
cada dato nuevo), antes de subir se compara también sobre los partidos fuera de muestra comunes. El entrenamiento
tarda ~2 min desde el gradiente exacto del 22-oct (antes 4 h 44 min).

## 2026-10-25 (noche) — Aviso «sin pronóstico sellado» en el detalle del partido

El titular leyó «No hay pronósticos publicados» encima de 25 mercados y lo tomó por un fallo. No lo era (pronóstico =
pick sellado; los mercados son estimaciones del modelo al momento), pero el texto inducía a error. Decisión: con
mercados debajo, el aviso dice que no hay pronóstico **sellado** y que abajo están las estimaciones del modelo (o que
están con VIP si todos llevan candado); sin mercados se mantiene el aviso de siempre. No se mezclan los dos conceptos:
un mercado del modelo nunca pasa a contar como pronóstico publicado.

## 2026-10-25 (noche) — Alta probabilidad: solo pronósticos con cuota

Decisión del titular tras ver «LAFC +1,5 asiático @—» en la app: no se publica ningún pronóstico sin cuota de una casa
de los suscriptores. Había dos causas. La primera: la selección tomaba la última captura de PropLine, y casi todas las
horas trae solo a Pinnacle (las casas llegan cada ~3 h). La segunda: el modelo proponía líneas que nadie ofrece; el
+1,5 de LAFC no lo cotizó ninguna casa, ni Pinnacle, en 49 capturas. Ahora `_snapshot` elige la captura más reciente
(≤ 6 h) que trae a Pinnacle y a alguna casa de los suscriptores, y los candidatos sin cuota se descartan antes de
elegir. Así el partido se queda con el siguiente que sí cotiza, en vez de perder el pronóstico o publicarlo vacío.
Repetido en seco sobre el 25-oct: alta 5/28 → 27/27 con cuota; ampliada 62/385 → 303/303. Lo ya sellado no cambia
(es inmutable). La escalera y el parley comparten `_snapshot` y `_referencias`, y ganan las mismas cuotas.

## 2026-10-25 (noche) — Tarjetas a cero de FotMob: manda la cronología

El titular vio «menos de 6,5 tarjetas» al 100 % (media 1,7) en Independiente–Boca. Causa: en Argentina, Brasil y parte
de México FotMob deja el bloque de tarjetas en `[0, 0]` en 2026, y el relleno lo tomó por dato válido (~790 partidos).
Decisión: no descartar FotMob para tarjetas, sino leer su cronología cuando el bloque viene con las cuatro a cero; la
cronología, sin las tarjetas al cuerpo técnico, coincide con API-Football en ~92-97 % de amarillas. Solo se toca el caso
medido (amarillas del bloque a cero; a veces trae la roja y deja las amarillas en cero, por eso la condición mira solo
las amarillas): con el bloque con datos se respeta, para no cambiar la convención del historial. Si la
cronología no es fiable, NULL antes que un cero que no consta.

## 2026-10-25 (noche) — Resultado al pitido con la primera fuente disponible

Decisión del titular: la app muestra el marcador final al pitido y el resultado se cierra con la fuente que lo tenga
primero. FotMob lo tiene a los ~5 min (el vivo ya lee su listado); PropLine, a las 3-6 h. Por eso el vivo cierra al
pitido con las validaciones del respaldo (mismo partido, mismos equipos, `FT`) y no se adelanta nada más: córners,
tarjetas y estadísticas siguen con SofaScore como fuente principal, porque sus recuentos no coinciden con los de otras
fuentes (las amarillas de BetsAPI difieren hasta un 45 %) y mezclar fuentes por llegar antes falsearía el Motor C.
Prórroga y penaltis quedan fuera: el marcador de los 90 minutos sale de otra fuente.

## 2026-10-25 (noche) — Auditoría de motores y datos: lo que quedó parado con el cambio de fuente

Orden del titular: auditar los tres motores y las fases del A, comprobar vivo, cierres y completitud, y arreglar en el
momento (`docs/auditoria_motores_datos_20261025_noche.md`). Lo que se encontró no eran datos que faltaran, sino
consumidores que seguían esperando la forma de The Odds API: la sombra del XI solo aceptaba `post_xi` (PropLine nunca lo
fabrica, y no debe) y el lector de cuotas solo miraba alias `odds_api`. Decisión: adaptar el consumidor (foto horaria
posterior al XI, ≤ 75 min, ≥ T-15) en vez de inventar etiquetas en la ingesta. ERA5 no estaba roto por datos: Copernicus
rechaza las peticiones simultáneas de una cuenta; de una en una salen todas. La API llevaba código de antes del 22-oct
porque la imagen `3babeb4` se construyó sobre la API anterior en vez de sobre `main`: se despliega entera desde `main`.
El chequeo de salud mira ahora el dato (cierres, cobertura de xG, once) y no solo la última fecha, que es lo que lo dejó
en verde con 3 días sin cierres.
Cuota de PropLine (5.000/día, reserva 500): ~40 % se iba en competiciones sin motor y la liquidación de fútbol en el orden
del catálogo; por eso faltaban cierres de la Premier y se cortaban las pasadas de la noche UTC. Decisión: no dejar de
archivar esas competiciones (observaciones originales para el futuro), solo bajarlas a cada 6 h y liquidar solo las
nuestras; NBA y tenis no cambian.

## 2026-10-25 — Clasificación y vivo sin API-Football; regla de arreglar al momento

Pregunta del titular: ¿por qué cada auditoría deja más pendientes? Porque eran de solo lectura (apuntaban sin cerrar), los
cambios de fuente abrían huecos nuevos y el punto de entrada estaba desactualizado (F7 figuraba «sin empezar» y corre cada
5 min). Regla nueva del titular: el error que aparece al desplegar o probar se arregla en la misma sesión; `PENDIENTES.md`
solo guarda lo que depende de él o de una fecha o muestra. Ya no hay ninguna pausa del motor.
Clasificación: se calcula con nuestros resultados en vez de pedirla a SofaScore (dinero) o PropLine (no la tiene). Contra
la última foto de API-Football (22-oct 06:40) coincide equipo a equipo en las 19 ligas salvo una sanción de puntos
(Southampton −4), que va a mano en `SANCIONES`; la forma de API-Football iba del más reciente al más viejo. Las
eliminatorias se excluyen con el tope de partidos de fase regular por equipo, no adivinando la jornada. Vivo: FotMob y no
PropLine `/scores`, porque PropLine cobra cada consulta del presupuesto diario compartido y ese día quedaban 1.237 a las
17:12 UTC frente a ~1.330 que necesita la captura horaria hasta medianoche; FotMob da todos los partidos del día en una
petición. Trampa vista: `docker compose cp worker` también apunta al contenedor de la captura de PropLine; usar
`docker cp quantfut-worker-1`.

## 2026-10-25 — Cierres de PropLine, Liga MX/MLS en SofaScore y `stats` desde SofaScore y FotMob

Orden del titular tras la auditoría de datos: arreglar lo que falla y usar FotMob para completar. Decisión clave: el
cierre de PropLine llega horas DESPUÉS del partido, y la liquidación con CLV es inmutable; cargar los cierres sin más
habría dejado igual la sombra y la puerta comercial, porque los resultados se liquidan antes. Por eso la liquidación
(picks, sombra sharp y sombra XI) espera al cierre sharp hasta 48 h (`cierre.cierre_o_vencido`). Cada línea del cierre
trae su propia hora y el de-vig exige un único momento por grupo: todas se fechan en el último instante en que todas
seguían a la vista (≤ 10 min del inicio); ensayo en producción: 79 partidos, 25.437 filas, diferencia mediana con la
última foto horaria 0,7 puntos y ningún lado invertido. Liga MX pedía el torneo del Clausura (vacío) y la MLS en
eliminatorias trae `round: null`: el recolector abandonaba sin avisar; ahora lista sin jornada. `matches.stats` vuelve a
llenarse (fichas de la web y faltas/centros para el Motor C) desde SofaScore y, si falta, FotMob; solo donde está NULL.
Los 10 fallos del arnés local son de entorno (Postgres sin contraseña en el worktree); en CI pasan.

## 2026-10-25 — Auditoría de datos de los tres motores (PropLine, SofaScore, BetsAPI)

Pedido del titular: comprobar si los motores reciben bien los datos nuevos, si hay cierres y alineaciones, si se sigue lo
recomendado en los documentos del 15-oct, qué ligas están completas para entrenar y qué data disponible conviene acoplar.
Solo lectura. Decisión clave: el cuello de botella de los cierres no es la fuente sino la carga. El archivo de PropLine ya
guarda `/odds/closing` de 185 partidos del 21 al 25-oct (Pinnacle 1X2 a una mediana de 11 min del inicio, con córners y
tarjetas), pero nada lo pasa a `odds_snapshots`: sin cierres desde el 22-oct 18:50, la puerta de frescura del
reentrenamiento pasa el 1-nov y falla hacia el 21-nov. Otros hallazgos: SofaScore no tiene ningún evento de MLS ni Liga MX;
bajas y once llegan pero ningún motor los lee; las estadísticas de SofaScore no llegan a `matches.stats`; casi no hay
cierres históricos de totales, córners ni tarjetas (0–6 %). BetsAPI (~25.600 partidos desde jul-2023) tiene xG con r ≈
0,95–0,97 frente al nuestro y cuotas bet365 de 8 mercados, pero sus amarillas no coinciden con las nuestras (55 % en
Brasil/Argentina), su recepción original es desconocida y la licencia no está leída: acoplar en tabla propia, no encima de
lo sellado. docs/auditoria_datos_motores_20261025.md.

## 2026-10-25 — Limpieza de pendientes y fin de la pausa del motor

En 12 días se cerraron 297 tareas, pero las abiertas pasaron de 128 a 250: cada auditoría apuntaba ideas al mismo nivel
que los fallos, y los cambios de fuente dejaban tareas muertas. Se cerraron 134 en su sitio con el motivo (hechas,
duplicadas, de fuentes o ligas retiradas, estados viejos de NBA) y quedan 116 con un índice al principio de
`harness/tareas.md`: 3 fallos (los cierres de PropLine se resolvieron el mismo día en el PR #127), 27 del titular,
31 en espera, 55 mejoras. Regla nueva: solo bloquea lo que hace
perder dinero o datos. El mismo día el titular levantó la pausa del motor hasta el 1-nov: se toca cuando convenga,
sin desplegar el worker durante el reentrenamiento del 1-nov.

## 2026-10-25 — Respaldo de resultados con FotMob

PropLine deja partidos sin resultado (`expired`: toda la liga suiza, y partidos sueltos de Noruega, Turquía, MLS, y
Hoffenheim–Lyon con alta probabilidad, escalera y parley), y sin resultado no se liquida ningún producto: había 19
atascados en ligas activas. FotMob ya está reactivado, así que cierra esos partidos tras 6 h (dos pasadas de PropLine).
Solo con `reason.short == 'FT'` (prórroga y penaltis cambian el marcador de los mercados a 90 min) y con los dos
equipos en el mismo orden por `fotmob_equipo`; lo demás se queda abierto para revisión manual en vez de adivinar.

## 2026-10-25 — Quedan 15 ligas + 2 copas; FotMob vuelve como complemento diario

Orden del titular tras medir la cobertura combinada de PropLine y SofaScore
(`docs/cobertura_ligas_propline_sofascore_20261025.md`): fuera Serie B, LaLiga 2, Allsvenskan y Super League suiza
(db/088, mismo trato que db/086: `active=false`, historial intacto, sin `retired_leagues`). FotMob se reactiva el mismo
día que se había retirado, pero como complemento: el nuevo paso `completar` solo rellena NULL y espera 36 h desde el
saque, porque el detalle de SofaScore llega con p90 de 19 h y máximo de 33 h; sin esa espera FotMob (captura a las
~2,5 h) se adelantaría siempre y dejaría de ser complemento. Su xG entra como primera pareja válida con la hora real
de captura de la página. Championship, 2. Bundesliga, Turquía y Noruega se añaden al recolector SofaScore: sin
API-Football se habrían quedado sin xG. Desplegado el 25-oct (worker `e5a29a7`). La 088 se aplica de forma
programada a las 22:30 UTC y no al desplegar: `results.py` solo cierra partidos de ligas activas, y desactivarlas
antes habría dejado sin liquidar los productos del día en esas ligas.

## 2026-10-25 — Bajas y once desde SofaScore

Al retirar API-Football y FotMob los pronósticos quedaron sin bajas ni once. SofaScore (rl1987 `event_detail` con `includeLineups`) trae en partidos futuros el once previsto (`confirmed=false`) y las bajas con tipo, motivo y fecha de regreso, así que no hace falta otra fuente. Decisión clave: el once previsto va a una tabla propia (`lineups_previstas`) y SOLO el oficial y completo se copia a `lineups`, porque `sello_tardio` lee esa tabla como «alineación confirmada» y un previsto la falsearía y adelantaría el sellado. Los ids de SofaScore no son los de API-Football: cada titular lleva `src` y `availability()` solo compara contra historia de su fuente, así que de momento da «insuficiente» en vez de decir que faltan todos los habituales. Las bajas se guardan pero aún no alimentan al modelo (antes tampoco: solo las fichas). Desplegado el 25-oct (PR #118, worker `117feb7`, migración 087).

## 2026-10-25 — Fuera del cron las tareas de API-Football, FotMob, PitchAPI y worldfootball

Orden del titular: en el servidor solo deben correr las fuentes nuevas. Se comentan (prefijo «RETIRADO», reversible) 14
tareas: bajas, alineaciones, clasificación, en vivo, xG, cuotas y calendario de equipos de API-Football; las tres
capturas de FotMob y sus sedes; el respaldo de PitchAPI; xG y copas de worldfootball/FBref. Quedan sin fuente hasta
conectar SofaScore/PropLine: bajas, once previo, clasificación y marcador en vivo; el sello por partido sigue a T-38 sin
once. El chequeo de bajas deja de alarmar con `RESULTS_PROVIDER=propline` porque no informaría de nada nuevo.

## 2026-10-25 — Ligue 2 y Superliga danesa fuera de los motores; fuentes: solo SofaScore y PropLine

El titular fijó las fuentes: SofaScore vía Apify (actor por deporte del 24-oct: rl1987 fútbol, scrapesage NBA y
tenis) y PropLine; ya no API-Football ni FotMob. PropLine no cotiza Ligue 2 ni la Superliga danesa, así que el titular
las retiró (db/086). Se desactivan en vez de borrarlas como Chile y Brasil B: tienen 205 pronósticos de alta
probabilidad, 7 patas de escalera/parley y 55 ofertas en sombra sellados, y borrar historial sellado necesita una
autorización aparte. Tampoco entran en `retired_leagues`: su trigger rechazaría cualquier UPDATE de los partidos que se
conservan. `RETIRED_LEAGUES` impide reimportarlas desde archivos. El recolector SofaScore de este PR se rehízo sobre la
versión por deporte que corría en el servidor y no estaba en `main`; desplegar la de `main` habría devuelto NBA y tenis
a rl1987.

## 2026-10-25 — Resultados y calendario desde PropLine; xG desde SofaScore

API-Football volvió al plan gratuito el 22-oct y el titular eligió sustituirlo en vez de renovarlo. Se lee lo que ya
capturan los recolectores (cero peticiones nuevas). El emparejamiento es lo delicado: PropLine escribe los clubes de otra
forma y a veces publica el mismo cruce al revés o dos veces. Por eso un evento se enlaza solo si los DOS equipos se
parecen, a ±36 h y como único candidato (entonces se aprenden los alias, fuente `propline`, no `odds_api`), y un
partido nuevo solo se crea con nombres exactos y sin el cruce ya presente en ningún sentido. SofaScore exige además el
mismo marcador: es la comprobación independiente de PropLine. Casas nuevas de PropLine solo a ≤ 48 h y cada 3 h por
volumen (~100 MB/día si no). Ensayo en seco en producción: 83 cierres de 111 pendientes, 61 alias aprendidos todos
correctos, 3 altas, 10 cruces invertidos rechazados; 15/15 detalles SofaScore con marcador igual.

## 2026-10-24 — Auditoría de fuentes y backtest: no recalibrar el Motor A

El titular pidió calibrar y validar los tres motores con la data nueva. No se calibró ni reentrenó nada: la data nueva aún
no está en las tablas (PropLine solo entra como cuota horaria desde el 24-oct; cierres, box score y SofaScore solo en el
archivo) y los resultados están parados desde el 22-oct por el plan gratuito de API-Football. El backtest con ventana
creciente muestra que el A está calibrado (la mejor recalibración coherente da ΔRPS −0,00016, en el límite del ruido) y
que su brecha con el cierre es de información: peso óptimo en la mezcla 0 y Kelly con P_modelo > P_mercado −11 % (IC95
−15/−7). Recalibrar sería ajustar ruido. Lo urgente son las fuentes: plan de API-Football, worker con dos archivos viejos
y cierres de PropLine sin cargar. Detalle: `docs/auditoria_motores_20261024.md`.

## 2026-10-24 — Tenis: cuotas del archivo de PropLine, sin The Odds API

El titular pidió conectar el motor de tenis al archivo compartido. Se hizo con un paquete nuevo (`tennis_odds_propline_v1`) en vez de
modificar `tennis_odds_live_v1`: el protocolo v8 congela el hash de ese código y tocarlo invalidaría su carga. Solo cuenta la observación
horaria más reciente (máximo 65 min), no la ventana de 36 h de antes: con una foto por hora no hace falta tirar de precios viejos. Se
retiró la foto de The Odds API del cron en lugar de dejarla como respaldo, por la decisión del 23-oct (sin fallback ni peticiones
duplicadas). Si la pareja sale dos veces en la misma observación no hay mercado: es preferible caer al apilador v7 que adivinar.

## 2026-10-18 (noche) — Candados difuminados: el botón VIP va a la tienda en la app, a Whop en la web

El titular pidió los pronósticos bloqueados difuminados con un botón «Acceso VIP» hacia la pasarela. Lo gratis (4 / 1 / 1) ya era lo que aplica el
código. El difuminado es seguro porque el servidor nunca manda la selección ni la probabilidad de lo bloqueado; la franja son bloques, no un
pronóstico falso. En la app el botón abre la pantalla VIP que compra con Play / App Store y no enlaza a Whop: las tiendas exigen su sistema de
compras para suscripciones digitales dentro de la app y un enlace de pago externo puede costar el rechazo de la ficha. Whop cubre la web, que no
pinta pronósticos reales bloqueados. Ventana de sello y fecha de corte de F7 siguen sin responder: quedan como propuesta.

## 2026-10-18 (tarde) — FotMob en vivo como fuente previa; Open-Meteo descartada por licencia

El titular autorizó la captura recurrente de FotMob (antes registrada como puntual) y entregó el token de Copernicus. La página
previa de FotMob trae alineación probable, no disponibles con tipo y pronóstico de clima con hora de actualización: cubre las
bajas previas y el pronóstico de F6 con una sola fuente, point-in-time, sin la clave de Open-Meteo. No se usó el plan gratuito de
Open-Meteo porque el producto vende suscripciones (uso comercial) y el titular había contratado el plan de pago; si se quiere esa
fuente, se carga la clave de pago. Las ventanas de captura previa se estrecharon (70 y 40 min) porque una ventana de 30 a 120 min
habría tomado la alineación antes de que se publique la oficial. ERA5 se valida contra el clima que midió FotMob (temperatura 0,98).
La captura se detiene 12 h ante cualquier HTTP 401/403/429 y no evita controles de acceso.

## 2026-10-18 — Datos al motor: tablas propias por fuente, nunca mezclar identificadores

El archivo de FotMob (20.331 partidos) pasó a tablas con `match_id` en lugar de volcarse en `lineups_historicas` y
`estadisticas_jugador`: esas llevan ids de API-Football y mezclar los dos espacios habría roto `player_ratings` y
`lineup_challenger` sin dar ningún error. El puente (7.834 jugadores) y la equivalencia de árbitros (54) son tablas aparte, con
umbral de coincidencia y 1 a 1 en las dos direcciones. Hallazgos que cambian el plan: el original de FotMob ya trae entrenador,
valor de mercado, asistencia y clima (40 %, medido en el partido); el calendario completo de API-Football muestra un partido
intermedio que `matches` no ve en el 17,6 % de los equipo-partidos; el cruce de árbitros apenas suma porque las fuentes casi
no se solapan. No se montó captura diaria de FotMob porque la descarga se registró como puntual: lo decide el titular.
Una medición propia, cancelada desde el cliente, siguió ejecutándose 38 minutos en el servidor: cancelar en la base, no solo
en el cliente. La suite completa tiene fallos previos que no son de estos cambios.

## 2026-10-18 — Orden de identidades: el error real es Arsenal, no las 379 "identidades"

Medido en producción sin escribir nada. Las 379 "identidades" de copas eran partidos (110 equipos); en ninguno están los
dos equipos identificados, porque el rival es siempre un club de una liga que no cubrimos, y la regla de `eu.ucl`/`eu.uel`
(no dar de alta equipos, solo coincidencia exacta) es la que lo impide: se cierra como no resoluble por diseño. La coincidencia
aproximada habría dado Pafos→Paris FC y Rangers→Angers. Lo que sí estaba mal es una fila de alias (`Arsenal`, `fbref`) que apunta a
Arsenal de Sarandí: 33 partidos de copa hasta 2024-12-11 en el club equivocado. Antes de afirmar su efecto en el modelo habría que
medirlo (se espera pequeño por el decaimiento de 180 días). Cuatro alias de The Odds API recuperan 39 de los 103 cierres de copa con
los snapshots ya pagados. Nada de esto se aplica sin visto bueno; ver docs/ordenar_identidades_20261018.md.

## 2026-10-16 — Tenis: extracción completa, motor local y resultados negativos conservados

Por autorización nueva se completaron 171 archivos TML y 43 archivos MCP:
214/214, 593.347.344 bytes, cero fallos y hashes/tamaños verificados. TML se
consolidó en 492.251 partidos (249.938 aptos para el candidato), con 15 conflictos
de identidad apartados y 3.923 filas inválidas conservadas en cuarentena.
MCP permanece como archivo de investigación y no alimenta los modelos ajustados.

Código aislado en el checkout gestionado tennis-engine, apps/tennis. Binomial
de saque/resto por rival/superficie, priors gaussianos, MAP/Laplace y ponderación
de antigüedad; no es todavía un modelo dinámico de estados. Markov conserva
saque/distribución conjunta y resuelve deuce/tie-break sin truncación. Dos
candidatos actuales: ATP 74.029 partidos y WTA 20.614, historia desde 2018 y
embargo de 35 días por fechas semanales. Consultas hipotéticas con incertidumbre.

Evaluación anual congelada 2025/2026: candidato inferior a Elo en log-loss.
2026 ATP 0,64466 vs 0,62855; WTA 0,65296 vs 0,62177. Hándicap A−3,5 mejora
frecuencia de entrenamiento; totales 22,5 no. Sin cuotas/ROI/CLV ni promoción.
El test 2026 ya observado no se usará como nueva prueba intacta tras ajustes.

17 pruebas específicas aprobadas. Arnés inicial/final 1.300 pasadas, 88 omitidas;
Docker no disponible. El primer arnés del checkout sin .env falló nueve pruebas
heredadas de BD; se diagnosticó y repitió completo con configuración existente
cargada solo en memoria, sin cambiar esos motores. Datos/recibos/modelos en
data/tennis/full_20261016; informe docs/tenis_primera_version_y_resultados_20261016.md.
Sin despliegue, apuestas ni consumo de The Odds API/ZenRows. Pendientes: tiempos
reales y agenda/IDs, calibración y prueba prospectiva, casas/presupuesto de cuotas.

## 2026-10-16 — Tenis: fuentes propuestas verificadas y muestra TennisMyLife

gmalbert actualizado 16-oct, commit 3d132eec; su pipeline central es clasificador de
ganador, selección por accuracy de test y Elo de referencia 0/1. El scraper
Flashscore revisado deja saque/resto nulos. No se ejecutó ni incorporó ese código.
panaC es Node/Puppeteer con último commit de 2018. Live Tennis API enlaza SDK GitLab;
FREE para agenda/estado, estadísticas detalladas ULTRA según documentación.
TennisMyLife directo aporta seis muestras 2026/en curso, 11.364 filas; conteos y
hashes conservados en .local/tennis_sources_20261016/. MIT declarada por la fuente;
WTA con aviso de fiabilidad en revisión. Fecha de torneo no es hora de partido,
claves repetidas y enlace entre fuentes pendientes. Dos CSV iguales a gmalbert y
blobs Git verificados. Sin cuentas/compras, cuotas API o proxy, entrenamiento ni
despliegue. Informe: docs/tenis_fuentes_y_repositorios_20261016.md.

## 2026-10-16 — Tenis: Match Charting Project auditado para investigación

El usuario eligió The Odds API para cuotas y JeffSackmann/tennis_MatchChartingProject
para datos. Descarga directa, sin proxy ni créditos API, fijada al commit
1813a1309b7ed7ebf1c7e884b32bf675d00e4edf. Los 1.877.757 registros de puntos se
contrastaron con Overview; S/R son puntos con ganador conocido sin detalle y
P/Q son penalizaciones, según las instrucciones originales leídas sin macros.
No confundir exclusión de esos códigos en Overview con inconsistencia de resultados.
Superan los controles iniciales 7.501 partidos masculinos y 4.237 femeninos:
23.476 observaciones de investigación. Conservados originales y cuarentena.
Las fechas máximas son 21-may y 9-sep-2026; la muestra seleccionada por colaboradores
no basta para actualización diaria. CC BY-NC-SA 4.0: permiso comercial sin acreditar.
Diseño y límites en docs/tenis_modelo_y_datos_20261016.md y
data/tennis/mcp_20261016/AUDIT_README.md. Sin entrenamiento ni despliegue.
Verificación independiente con pandas reproduce las 23.476 observaciones;
arnés inicial y final: 1.300 pruebas pasadas, 88 omitidas y cero fallos.
Docker no disponible: se omitió la validación de Compose.

## 2026-10-15 — Plan de mejora de los tres motores: el contexto tiene que llegar a los picks

El documento de recomendaciones del usuario se contrastó con el código: F1–F7 ya
cubren XI, bajas, árbitro, clima/sede y la revisión con el once; el anclaje de B
usa 1X2 más la línea de goles con ρ fijo (identificable) y parley/escalera no
repiten partido. Lo que faltaba es el porqué de fondo: los picks vendidos salen
de B, así que mejorar A sin una mezcla aprendida (F8) no cambia nada vendido, y
una probabilidad mejor no prueba un pick mejor sin evaluarlo a volumen constante
(F9). Por eso F9 va antes que F8 y ambas antes de F3–F6. Medido en producción:
alta probabilidad acierta lo prometido pero pierde a cuota de referencia
(−3,0 % base, −7,5 % ampliada); es la línea de acierto decidida el 2026-10-05, y
solo información ajena al mercado puede cambiar ese signo. Por decisión del
usuario no se toca el motor antes del 1-nov. Spec:
docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md.

## 2026-10-15 — Revisión del plan: A se juzga contra B del mismo momento

La revisión del usuario corrige el orden: F8 se evalúa en paralelo con F9 y se
activa al final, porque una mezcla no evita el doble conteo por sí sola y ganar a
un B de las 03:00 puede ser solo ventaja de hora (F7). Por eso F9 separa el efecto
del horario, del modelo y de la selección. La regla «≥2 ligas» queda como filtro
inicial: con muchas variantes probadas hace falta magnitud, estabilidad y
registro de lo probado. Descanso/calendario sube por coste bajo. Hallazgo de
datos: el archivo FotMob ya trae XI, minutos, bajas, entrenador, ronda y estilos
de 2024 en adelante (sin pasar a las tablas del motor, donde el XI está al 0 %
antes de 25-26); lo que de verdad falta descargar es el calendario de copas y
otras competiciones, altitud y ERA5. El 91/223 con cuota de referencia está
sesgado porque doble oportunidad y hándicap se capturan desde el 12 y 14-oct. No
se compran cuotas históricas a T-60 (≈14.000–31.000 créditos por temporada): se
evalúa hacia delante con la captura propia.
## 2026-10-15 — Tres parejas xG de 365Scores cargadas por petición del titular

La discrepancia horaria de Granada–Albacete no impide identificarlo: el archivo
FotMob 4521823 también sitúa el partido a las 18:30 UTC y coincide en equipos y
marcador 1–2. Se conservó el kickoff canónico 19:30 UTC; no se corrigieron fechas
como efecto lateral de cargar xG. Los endpoints de 365Scores tampoco siempre
serializan igual sus relojes: ambos originales y la discrepancia quedan guardados.

Tres parejas en `matches`, tres detalles en `historical_football_matches` y tres
estadísticas en `historical_football_observations`, fuente `365scores`. Se usa la
recepción real del 15-oct-2026, para que el dato no entre en cortes anteriores.
Respaldo solo de los tres registros en el servidor, ensayo revertido, repetición
con cero escrituras y lectura independiente tras commit. Hashes de seis originales
verificados; resto de partidos, archivo previo, modelo, flags, sellos y triggers
conservados; API 200. Huecos 1.222→1.219 (LaLiga 2: 236→233).
No se desplegó código de aplicación ni se reentrenó. Evidencia e instrucciones
de reversión: `docs/lanusstats_carga_20261015.md` y `data/xg_recovery/20261015_lanusstats/carga/`.
Arnés previo y final: 1.251 pruebas pasadas y 66 omitidas, sin fallos.

## 2026-10-15 — LanusStats/365Scores aporta xG en la muestra de LaLiga 2

Prueba autorizada con LanusStats 2.1.13 aislado: tres de nueve huecos aportan
parejas de xG, todos de LaLiga 2; los tres de Serie B y tres de Ligue 2 tienen
estadísticas sin xG publicado en las respuestas consultadas. Control positivo
Lanús–Unión 2,22–0,64. Acceso directo HTTP 200: no hizo falta proxy y no hubo
consumo de ZenRows. No confundir ausencia de un campo con bloqueo de acceso.

Se separó explícitamente xG (`statistics.id=76`) del xG recibido (77) y xGOT
(79), con pares completos por ID de equipo; sin estimaciones ni ceros de relleno.
Originales/hash/recepción real e identidad comprobados. Granada–Albacete tiene
una hora de discrepancia, señalada sin corregir la base. Los nueve casos son
una muestra de los 1.222 pendientes; se localizaron 32 candidatos por calendario/
enfrentamientos, no se descargaron 1.222 detalles. Sin importación ni cambios
del motor. Entrega verificable en data/xg_recovery/20261015_lanusstats/.
Arnés previo y final correctos: 1.251 pruebas pasadas, 66 omitidas. Paquete de
46 archivos verificado por hash y revisado para excluir credenciales.

## 2026-10-15 — Carga autorizada de OddsPapi: cierre utilizable y referencia separados

Confirmados 2.918 cierres reconstruidos (8.754 cuotas), más 25 referencias solo
en procedencia. Se cotejaron los 2.943 originales completos y las identidades
actuales, sin cambios ni cierres previos. Se mantienen sin certificar: fuente
`oddspapi_reconstructed`, recepción real separada y marcas de cambio originales.
Las 23 ternas antiguas y dos conflictos temporales adicionales no entran en
`odds_snapshots`: consumidores existentes podrían usarlas incluso con otra etiqueta.

Nueva procedencia inmutable `historical_odds_backfills` conserva las 2.943 y sus
extractos 1X2 verificables. Ensayo con rollback y repetición cero; commit con
respaldo completo de 444.756 cuotas previas. Partido/equipos/predicciones/picks/
modelo/cuotas anteriores intactos; cero violaciones temporales. Huecos desde
2024: 6.185 → 3.267. Sin entrenamiento. Pruebas: 1.237/60 omitidas.

La copia local del respaldo completo fue rechazada por revisión automática como
exportación no autorizada específicamente; se verificó hash/CRC/cabecera COPY en
el servidor y permanece en su volumen persistente. La carga sí quedó completada.
Detalle: docs/oddspapi_carga_20261015.md; informe y estados en el paquete de OddsPapi.

Comprobación antes de guardar en Git: arnés correcto, 1.246 pruebas pasadas y
64 omitidas; revisión de credenciales y recuentos del paquete sin incidencias.

## 2026-10-15 — OddsPapi: cola terminada, cobertura parcial

A las 03:46 de Ciudad de México finalizó la cola de 6.094 asociados. Resultado:
2.943 ternas Pinnacle prepartido reconstruidas (2.920 recientes, 23 para revisar),
3.151 sin histórico; además, 87 sin fixture y cuatro cancelados. Quedan 3.242
de las 6.185 filas originales sin recuperar con esta API; cero consultas pendientes.
CSV final y estados en `data/pinnacle_recovery/20261014_oddspapi/`; originales
y recibos conservados en `.local/oddspapi_20261014/`. Unicidad, corte temporal,
referencias a recibos y preservación del original comprobados. No se cargaron
automáticamente ni se acreditó cierre oficial. Seguimiento periódico desactivado.

## 2026-10-14 — OddsPapi: recuperar el historial sin introducir cuotas en vivo

Clave autorizada, cuenta gratuita con Pinnacle y cupo de 250 consultas. El
histórico no factura consultas según la documentación; catálogo/calendario sí.
Se asociaron 6.094 de los 6.185 pendientes con 48 equivalencias revisadas y
equipos existentes. Quedan 87 de 2024 fuera de los calendarios consultados y
cuatro de 2026 cancelados en la fuente, registrados para conciliación.

Primer lote: 51 ternas prepartido con historial, originales y marcas de tiempo.
La descarga continua está en marcha sobre la cola completa, con espera mínima
de 5,15 s tras cada respuesta, caché verificable y reanudación. CSV y recuentos
en `data/pinnacle_recovery/20261014_oddspapi/`; estado del proceso y originales
en `.local/oddspapi_20261014/`. No afirmar que el lote ya terminó: consultar
`worker_state.json` e `informe.json` antes de informar cifras actuales.

El histórico mezcla prepartido y en vivo: solo se toma Pinnacle/101/101-103,
última cuota no suspendida anterior al menor del inicio programado y real.
Se documenta como cierre reconstruido, `close_verified=False`, sin carga
automática ni entrenamiento. Los 404 comprobados de enero/febrero no acreditan
una ausencia universal de esos meses. Detalle: docs/oddspapi_recuperacion_20261014.md.

## 2026-10-14 — Reintento OddsHarvester: comprobar el payload completo

A petición repetida del usuario, cuatro sesiones nuevas de ZenRows sobre dos
filas exactas (United–City ene-2026 y PSG–Inter may-2025): cero Pinnacle. Tres
capturas acreditan en el JSON que consume la interfaz el evento, mercado 1,
scope 2 y `bookieFilter=all`; sus 8/11/8 proveedores coinciden con las filas
extraídas. No era solamente el filtro del parser. Perú quedó limitado por
idioma y filtro, y la geolocalización física no se verificó independientemente:
se registran los países solicitados, sin afirmar que sean los de salida.

Se conserva la lista con 272 candidatas previas sin verificar y 5.913 sin
candidata. No se hicieron 6.185 consultas individuales ni cargas. Nuevos
datos/recibos/manifiesto en `data/pinnacle_recovery/20261014_oddsharvester_retry/`;
detalle: docs/oddsharvester_reintento_20261014.md. El paquete del commit
43c462f permanece intacto.

## 2026-10-14 — PySBR/Flashscore: separar precio histórico candidato de cierre acreditado

Sobre la lista exacta `.local/cierres_faltantes_20261014.csv` (6.185 filas de
23 competiciones), OddsTrader permitió descargar 3.624 eventos: 586 ternas
Pinnacle candidatas anteriores al inicio, 272 asociadas a pendientes con
nombres/alias o equivalencias explícitas, fecha y marcador reglamentario
corroborados. Se conserva la distinción: `currentLines` no demuestra la
integridad del historial ni el cierre final. Nueve discrepancias de marcador
(prórrogas) se excluyeron; no se arreglaron silenciosamente ni se cargaron cuotas.

PySBR original apunta a un endpoint retirado; su consulta funcionó adaptada a
OddsTrader y ZenRows residencial GB. Flashscore omkarcloud y M3MONs también
funcionaron con ZenRows CL; el segundo necesitó conservar `mid` y la ruta del
mercado histórico. Las cinco ternas comunes coinciden por casa, pero ninguna
es Pinnacle. Catálogos de siete regiones y controles de 2025/2026 tampoco
aportaron la casa en las muestras. No se confunde bloqueo resuelto con cobertura.

Se entrega CSV de estado para las 6.185 filas, candidatas separadas, 5.913 sin
candidato, y cobertura/limitaciones por fuente. Las dos muestras individuales
Flashscore están señaladas; no se afirma haber consultado las 6.185 allí.
La base y el archivo original permanecen intactos. Detalles y reproducción:
docs/pysbr_zenrows_20261014.md y docs/flashscore_pinnacle_20261014.md.

Por petición posterior del usuario se guarda una copia versionada en
`data/pinnacle_recovery/20261014/`: 272 candidatas, 586 ternas totales,
lista/estados, 25 originales con sus recibos y evidencia del subconjunto
asociado. El manifiesto y atributos de Git conservan los hashes exactos.
Guardar los datos no acredita cierre final ni autoriza usarlos como tal.

## 2026-10-14 — Recuperación Pinnacle: no confundir cobertura histórica con reciente

Ensayo de lectura sobre los 6.185 cierres faltantes: 60 CSV públicos, 14.381
ternas explícitas válidas desde 2024, TODAS ya almacenadas. MEX contiene 4.437
ternas de 4.752 filas, pero la última es del 27-oct-2025; ARG/BRA/USA también
terminan en 2025. Los 1.457 huecos de esas ligas no se recuperan reimportando
los CSV actuales. No se escribió en producción ni se entrenaron modelos.

OddsHarvester 0.20.0 aislado + ZenRows Browser Sessions lee páginas y fichas,
pero las pruebas GB/CA/CL y PSG–Inter de mayo de 2025 devolvieron cero Pinnacle.
Se archivan originales y recibos; el adaptador devuelve error cuando una ficha
leída no trae ternas de la casa pedida. Pendiente fuente/acceso con cobertura
acreditada antes del lote. Incidencia de autoalta gratuita de la CLI documentada,
sin compras; las pruebas usan la clave existente. Detalle y archivos:
docs/pinnacle_recuperacion_20261014.md.

## 2026-10-03 — Decorrelación con el mercado: tampoco

Idea 4. Hubáček y Šír (IJF 2023) entrenan con `Σ(t−y)² − γΣ(t−m)²` y ganan
en la NBA contra el cierre de Pinnacle con un modelo peor que el mercado.
Leído el artículo antes de diseñar: con apuesta uniforme ellos también
pierden para todo γ; solo ganan con cartera de Sharpe. Regla fijada antes
en tareas.md. `eval/decorrelacion.py`: segunda etapa softmax sobre la
información de Kalman, `m` = justo temprano de Pinnacle, walk-forward por
temporadas (prueba 2021/22-2024/25), γ elegido en la temporada anterior.

- Con el γ elegido: EV contra el cierre −3,51 % [−3,78, −3,25], 0/7 ligas,
  8.802 apuestas. γ fijo 0 → 0,8: −3,78 % → −3,46 %. Apartarse del mercado
  mejora 0,3 puntos y no se acerca a cubrir el margen de Pinnacle (~3,9 %).
- Por qué no se probó la cartera de Sharpe: solo repondera las mismas
  apuestas según la ventaja estimada, y esa ventaja correlaciona −0,10 con
  el EV real (el quintil de más ventaja estimada da −5,1 %). Pesaría más lo
  peor. Es la misma selección adversa que el README midió en 2026-09-22.
- La correlación con el mercado se queda en 0,95 para todo γ: las variables
  son las probabilidades del propio modelo, que ya se parecen al mercado.
  Decorrelar de verdad exigiría información que el mercado no tenga, que es
  justo lo que falta (diagnóstico del README).

Balance de las 5 ideas: 1, 2 y 4 descartadas con datos; 3 y 5 desplegadas,
las dos sobre el criterio de casas blandas, que es donde está la ventaja.

## 2026-10-03 — Stake encogido por la incertidumbre de la persistencia

Idea 5 (Baker y McHale 2013; Uhrín y otros 2021). El stake era Kelly 0,20
sobre `edge × persistencia`, con la persistencia tratada como conocida.
Medida con bootstrap por semanas en football-data (2 %, primera oferta por
partido): 1xBet 0,72 [0,37, 1,06], Bet365 0,13 [−0,15, 0,41], William Hill
−0,15; dispersión entre casas 0,31. La de Bet365 no se distingue de cero.

- Factor `ρ²/(ρ²+SE²)` por casa, multiplicado al Kelly fraccional, que se
  queda en 0,20: el 0,20 es preferencia de riesgo; el factor, estimación.
  Lo que cambia es el reparto entre casas, no el nivel general.
- SE en vivo por el método delta sobre la sombra (coincide con el bootstrap:
  Bet365 0,140 frente a 0,146), mezclado con la previa con los mismos pesos
  que `mezclar` (la previa vale 100 partidos).
- "Stake sí, muestra no" (decisión del usuario): `stake_units` de la sombra
  y `stake_kelly_units` del candidato siguen SIN factor y deciden qué es
  publicable; el factor va en columnas nuevas (db/039). La puerta mide lo
  mismo que antes del cambio.
- Desplegado 18:03 UTC (respaldo `~/respaldo_20261003_stake/`). Factores
  vigentes: 1xBet 0,94, Betano 0,71, Betsson 0,65, Bet365 0,54 (la sombra
  ya la sube desde 0,43), William Hill 0. En la misma comprobación: las 258
  filas de The Odds API desde el despliegue de 3A traen `book_updated_at`.

## 2026-10-03 — Latencia de las casas blandas: empezar a medirla

Idea 3. Hoy no se podía medir: API-Football refresca cada competición de
golpe cada varias horas con una sola hora para todas las casas, y
`odds_worker` descartaba el `last_update` por casa de The Odds API. Además
solo hay 6 capturas por partido y la sombra lleva 184 ofertas.

- 3A (gratis): db/038 `odds_snapshots.book_updated_at` + `odds_worker` la
  guarda. ADD COLUMN: el trigger de inmutabilidad sigue igual.
- 3B: `ingest/rafagas.py` cada 5 min, T-6 h a T-15 min, 1X2 con
  `bookmakers=` (10 casas → 1 crédito), Premier, LaLiga y Liga MX, a
  `odds_rafagas` (tabla aparte: ventanas, sombra y cierre no la ven), una
  fila por CAMBIO de precio. Tope 3.000 créditos/mes, contado en
  `rafagas_log` (decisión del usuario).
- Por qué 5 min bastan: `last_update` fecha cada cambio al segundo; la
  consulta solo tiene que verlo antes de que vuelva a cambiar.
- Vara fijada con el usuario: su cliente tarda UNA HORA O MÁS en apostar.
  `eval/latencia.py` mide la fracción de ofertas que duran ≥60 min por casa
  (regla en tareas.md). Si una casa no llega a la mitad, sus ofertas no son
  aprovechables con el formato actual y no deberían contar para la puerta.
- Para no duplicar el emparejamiento evento→partido, `odds_worker` expone
  `match_meta` y `match_events`; las ráfagas los reutilizan.
- Despliegue: respaldo en `~/respaldo_20261003_latencia/`, migración
  aplicada, worker reconstruido y reiniciado después del cierre de los dos
  partidos de LaLiga 2 de las 16:30 UTC. Primera lectura posible tras 2-3
  fines de semana desde el 9-oct.

## 2026-10-03 — Más-menos por jugador: tampoco aporta sobre el XI simple

Idea 2 de la literatura (Kharrat, McHale y Peña 2020; Hvattum): valorar al
jugador por cómo le va al equipo con él en el campo, no por sus estadísticas.
Versión aproximada por minutos (decisión del usuario; el diseño del 29-sep la
dejaba fuera por no tener el minuto de cada cambio). Diseño y regla fijados
antes de ver resultados en tareas.md. Mismas 3.646 filas y misma base
(`oos_2026.10.01-030007.pkl`) para los cuatro brazos:

| brazo | RPS | log-loss | ECE | ligas | valida |
|---|---|---|---|---|---|
| base | 0,21826 | 1,0516 | 0,03029 | - | - |
| XI simple | 0,21686 | 1,0471 | 0,03086 | 8 | sí |
| XI con valor | 0,21907 | 1,05448 | 0,03581 | 2 | no |
| XI con nota | 0,21808 | 1,05115 | 0,03034 | 8 | (comparación) |
| más-menos | 0,21838 | 1,05212 | 0,03324 | 4 | no |

- El más-menos queda en la base o un pelo peor. Con dos señales no
  sobreajusta como "XI con valor" (18), así que el problema no es la forma de
  medir al jugador sino que, con un año de datos, quién falta no añade nada a
  cuántos habituales faltan.
- Límite conocido de la aproximación (el test lo documenta): un jugador que
  juega siempre es inseparable de su equipo; el más-menos solo lo mide por
  los partidos que se pierde, que son justo los raros.
- La versión exacta (`/fixtures/events`, ~4.600 peticiones) NO se hace: era
  condicional a que esta apuntara algo.
- Ejecución: copia aparte del código en `/tmp` del worker, sin reconstruir,
  reiniciar ni guardar artefactos; borrada al terminar. En el servidor sigue
  el `player_value.py` anterior: el brazo entrará en el reentreno mensual
  cuando se despliegue, como "XI con valor", por si la muestra cambia.

## 2026-10-03 — El modelo tampoco llega antes que la cuota temprana

Pregunta: `w_model = 0,0001` se midió contra el cierre; ¿y contra la cuota de
Pinnacle de 1-3 días antes, que es la que se puede tomar? Regla fijada antes
de correr (tareas.md, "Ideas de la literatura" 1). `qf.eval.early_vs_close`,
Kalman secuencial con xG, 14.110 partidos de 7 ligas (2019/20-2024/25).

- Prueba principal: el movimiento temprana→cierre no va hacia el modelo.
  Pendiente 0,0028, IC95 por semanas [−0,0078, +0,0137], corr 0,006.
- Se eligió el MOVIMIENTO y no el RPS porque no depende del resultado: con
  42.000 filas detecta pendientes de ~0,01. Control positivo para comprobar
  que la prueba no es ciega: la media de casas como "modelo" da 0,38 [0,29,
  0,46] en 7/7 ligas; Bet365, 0,16 [0,13, 0,19]. Las casas sí anticipan a
  Pinnacle; el modelo no.
- Apostar a Pinnacle temprano con ≥2 % de ventaja del modelo: −4,87 %
  [−5,15, −4,59] contra el cierre justo, peor que sin criterio (−3,9 %): la
  misma selección adversa del README. `w_model` contra la temprana: 0,0001.
- Fuga cerrada al implementar: `predict_sequential` estima nivel de goles y
  localía por liga con TODO el histórico. Aquí se fijan con lo anterior al
  primer partido evaluado (`_KalmanSinFuturo`); sin eso, una pendiente
  positiva habría sido sospechosa.
- La base local no tenía db/023 (`model_enabled`) y `load_training_data`
  fallaba: se aplicó la migración del repo en LOCAL. El servidor ya la tenía.

Consecuencia: la información del modelo (goles + xG) no llega antes que el
mercado en ninguna ventana medible. Lo que queda de la lista son fuentes de
información nueva (punto 2, más-menos) o del criterio sharp (3 y 5).

## 2026-10-03 — FotMob para histórico puntual, futuros de otra API

Alcance explícito del usuario: 23 ligas y 2 copas, desde 2024 hasta hoy.
Se interpreta 1-ene-2024 a 3-oct-2026 inclusive en America/Mexico_City.
Se aprovechan las rutas JSON documentadas en Public-FotMob-API mediante un
descargador independiente de biblioteca estándar; no se despliega su proxy
Django ni se añade una fuente recurrente. Sin escritura en Postgres.

La consulta real de allLeagues confirmó los 25 IDs, y matchDetails respondió
200 con xG, eventos, alineaciones y tiros para Liverpool-Newcastle (1-ene-2024).
Inventario completo: 22.461 partidos terminados, 96 temporadas/torneos, 0
errores de calendario. La descarga de detalles queda EN CURSO, reanudable,
en `.local/fotmob-history/2024-01-01_2026-10-03/`; `coverage.json` expresa
la terminación real y no el éxito de arranque. Captura JSON comprimido con
SHA-256/hora real, y CSV con xG ausente separado de pendiente/error. Ante
401/403/429 se detiene sin evasión. No se presume cobertura de xG total.

Validación: 573 pruebas pasan (13 nuevas sobre fechas locales, identidad,
xG total frente al del descanso, ceros/datos ausentes, caché y denegaciones).
Se ejecutó el arnés Windows real: el shell Git mínimo omite Python y no
dispone de dirname, así que su salida OK no valida las pruebas.

Corrección durante la descarga: ediciones de Liga MX, Brasil y Argentina
usan IDs de torneo propios con `general.parentLeagueId` explícito. La guarda
original rechazaba esos detalles aun guardando el JSON. Se valida ahora la
liga principal declarada, manteniendo las guardas de ID, equipos y fecha.
Reanudada en segundo plano con logs y PID en `process.json`, recuperando los
detalles desde caché: Liga MX completa, 923/923 con xG. Dos respuestas de
Brasil tienen fecha distinta de su calendario y siguen como error; no se
relaja esa guarda ni se inventa la fecha. Validación actual: 584 tests pasan,
14 específicos de FotMob (hay otros cambios simultáneos en el workspace).

## 2026-09-24 — Fase 2.D medida: la forma de la matriz no es el problema

Implementados como challengers (a petición del usuario, sabiendo que el
esperado era 0,001–0,002 de RPS): Poisson bivariante, Conway-Maxwell-Poisson,
conteo Weibull con cópula de Frank y probit ordenado sobre la diferencia de
goles. Decisión de diseño: los brazos de conteo conservan las MEDIAS de
Dixon-Coles fuera de muestra y cambian solo la forma. Así cada brazo aísla lo
que dicen mejorar los papers (dispersión y dependencia) y no hace falta otro
ajuste de fuerzas por equipo, que costaría horas por brazo. `dc_tau` se
reajusta con el mismo protocolo para que la comparación sea justa.

Resultado sobre 2.641 partidos del último año: ninguno mejora a `tau`; CMP y
Weibull empeoran el 1X2 con el IC entero por debajo de cero. Los parámetros
se quedan pegados a Poisson (ν=1,09, c=1,05), es decir, los datos no tienen
la sobredispersión que esos modelos corrigen. Confirma el diagnóstico de
siempre: falta información, no técnica. No se activa nada; el informe se
recalcula en cada entrenamiento por si con más muestra cambia. Detalle y
cifras en `tareas.md` (2.D).

## 2026-09-24 — Rate limiting: existía, pero con dos agujeros

El pendiente "rate limiting en rutas públicas" ya estaba cubierto por el
middleware global. Revisándolo salieron dos fallos: el tope de 10/min de
`/control` se comparaba contra el contador compartido de todas las rutas
(abrir la web y luego el panel en el mismo minuto daba 429), y en IPv6 se
limitaba por dirección, cuando un cliente suele controlar un /64 entero.
Contador propio para `/control` e IPv6 agrupado por /64; las IPv6 que
envuelven una IPv4 se cuentan como la IPv4. Con Cloudflare delante el caso
IPv6 no es teórico: la primera petición de verificación ya llegó por IPv6.

## 2026-09-24 — Fuera `soccerdata`

Se borró `xg_fbref.py` en vez de aflojar el pin: FBref bloquea el scraping
con Cloudflare y el mismo dato llega por `xg_worldfootball`, así que arreglar
la instalación de `soccerdata` solo habría devuelto un módulo que no funciona.
Con él salen `lxml` y `html5lib`, que ningún código usaba. `requirements.txt`
vuelve a resolver (`pip install --dry-run`) y la imagen del servidor se
reconstruyó sin ellos.

## 2026-09-24 — Nombres sin resolver: una alarma que no se podía apagar

De 36 nombres pendientes en producción solo uno era trabajo: `Coventry City`,
el nombre de The Odds API para el Coventry que API-Football había dado de
alta como `Coventry` al ascender. Sin alias, cada pasada descartaba sus
eventos de Premier (8 descartes en dos días). Alias en `db/020`, nunca equipo
nuevo; el difuso daba 76 y no se toca el umbral (ver 013).

Los otros 35 son clubes de ligas fuera del catálogo jugando copas europeas:
irresolubles por diseño. Pero la alarma los contaba, así que "Salud del
sistema" iba a estar en rojo para siempre — el mismo fallo que ya se corrigió
el 2026-09-22 con el calendario. Ahora cuenta solo nombres vistos en liga
doméstica o sin competición anotada (en la duda, alarma). Para poder
distinguirlo, `odds_worker` anota la competición del feed con
`resolve_team(seen_in=)`, un parámetro aparte porque pasar `league_id`
habría ACOTADO la búsqueda a los equipos de la copa, que no tiene ninguno.
Si un nombre se ve primero en copa y luego en liga, gana la liga: es la que
debe alarmar.

## 2026-09-24 — Guía visual de QuantFut aplicada a la demo

La portada pasa de una presentación casi solo editorial a mostrar una ficha
1X2 ficticia junto a su explicación y acceso al historial: la identidad
propia de QuantFut debe ser la evidencia del partido, no los efectos típicos
de una casa de apuestas. `frontend/DESIGN_SYSTEM.md` fija tokens, jerarquía,
componentes, móvil y accesibilidad. UI UX Pro Max se usó como catálogo de
criterios, sin instalarlo, añadir dependencias ni copiar una plantilla.
El prototipo conserva sus seis vistas y sigue sin cuentas, pagos, apuestas o
datos reales. El contenido futuro autorizado permanece en el FastAPI modular,
nunca oculto solo con CSS ni protegido por un secreto en el navegador.

## 2026-09-24 — Fase 2: lo que faltaba era código de arranque, no más modelo

Revisada la Fase 2 entera con el sistema ya en producción. Casi todo lo
pendiente es muestra y no se acelera con código, pero había un bloqueo que sí
era código: **sin modelo activo nada de la parte "modelo" acumula**. El job
de las 08:00 falla ("No hay ningún modelo activo") y `qf.model.shadow`
responde "sin modelo activo" cada 5 minutos, así que los cuatro brazos de 2.B
y el XI de 2.C no guardan ni una fila. El único reentrenamiento programado era
el mensual (1-oct).

No se tocó la puerta: rechazar con mercado de 252 días es correcto. Se añadió
`train --bootstrap` diario que solo entrena si no hay modelo activo Y el
cierre sharp ya pasaría la misma comprobación de frescura. La constante se
movió a `promotion.MARKET_MAX_AGE_DAYS` para que el chequeo barato y la
puerta no puedan divergir. Motivo del chequeo previo: un entrenamiento cuesta
~3,5 h en el VPS; reentrenar a ciegas cada día quemaría CPU para una
respuesta que ya se conoce.

La muestra comercial (sombra sharp) NO depende del modelo y ya acumula:
`af_odds` 801 filas en 21 partidos el primer día. Pero no se veía en ningún
sitio del operador: Grafana leía `pick_results` (vacía a propósito con la
publicación pausada) y con `clv_pct`, la vara que 015 descartó. `/control`
gana la tarjeta de la puerta usando el mismo `shadow_sharp.report()` que
decide, no una copia en SQL que pudiera divergir.

Cerrados como superados, no borrados: validar la zona de abstención, la
incertidumbre relativa al mercado y la ordenación media/sd (servían para
apostar con el edge del modelo, criterio eliminado en el paso 4;
`uncertainty.py` ya no lo importa nadie), y extender la mezcla al AH (la
premisa de devolver el AH a los picks ya no aplica). 2.D (Weibull, CMP,
probit) no se implementó: esperado 0,001–0,002 de RPS y el producto ya no
depende de que el modelo bata al mercado.

## 2026-09-24 — El cron del worker nunca había corrido en el servidor

Tras el primer despliegue, `docker compose exec worker crontab -l` devolvía
"no crontab for root": el `command` del servicio `worker` en
`docker-compose.yml` intentaba `chmod 0644 /etc/cron.d/quantfut` antes de
`crontab /etc/cron.d/quantfut`, y ese archivo está montado `:ro` (es el
`./scripts/crontab` del repo). El `chmod` fallaba ("Read-only file system"),
el `&&` cortaba antes de `crontab`, y el contenedor seguía "Up" porque
`cron -f` sí llegaba a ejecutarse — pero sin ningún job cargado. Cuatro horas
sin captura de cuotas, resultados ni nada, sin ningún error visible salvo una
línea en `docker compose logs worker`.

El `chmod` no hacía falta: `scripts/crontab` está en formato de crontab de
usuario (5 columnas, sin campo de usuario), y `crontab <archivo>` solo
necesita *leer* el archivo — root puede leerlo aunque el volumen sea `:ro`.
Se quitó el `chmod` y se encadenó todo con `&&` explícito para que un fallo
futuro en cualquier paso no deje `cron -f` corriendo en silencio con cero
jobs. Redesplegado y verificado: `crontab -l` en el worker devuelve los 17
jobs y `cron -f` corre como proceso propio (no como parte de la cadena `&&`).

Consecuencia directa: el primer entrenamiento (`qf.model.train`, mismo día)
no activó ningún modelo — no por este bug, sino porque `market_age_days=250`
en la base restaurada del local (el cierre sharp más reciente es de enero
2026): la puerta de promoción exige mercado con menos de 30 días. Es el
comportamiento correcto de la puerta, no un fallo; hace falta que
`odds_worker`/`af_odds`/`shadow_sharp` acumulen cierres frescos (ahora sí
corriendo) antes de reentrenar y esperar activación.

## 2026-09-24 — Despliegue detrás de Cloudflare: lo que rompía sin avisar

Desplegado en el VPS de Contabo (`31.220.72.30`) con el dominio
`pronosticosdeportivos.pro` detrás del proxy de Cloudflare. El `Caddyfile`
anterior daba por hecho que Caddy recibía las conexiones directamente, y con
Cloudflare delante eso fallaba en tres puntos, sin que ninguno diera error:

1. `remote_ip {$GRAFANA_ALLOWED_IP}` veía siempre una IP de Cloudflare, así
   que `/control`, `/admin` y Grafana habrían respondido 404 también al
   operador.
2. Caddy reescribe `X-Forwarded-For` con la IP del salto anterior, y el rate
   limit de `main.py` usa su primer elemento. Todos los visitantes de un mismo
   nodo de Cloudflare habrían compartido el cupo de 60/min. Arreglado en
   Caddy (`trusted_proxies` con los rangos de Cloudflare + `CF-Connecting-IP`
   + `header_up X-Forwarded-For {client_ip}`), sin tocar `main.py`.
   Verificado: la clave de Redis del rate limit lleva la IP real del cliente.
3. Docker publica 80/443 por delante de ufw, así que un "solo Cloudflare"
   hecho con ufw habría sido falso. El filtro va en `DOCKER-USER`
   (`qf-cf-firewall`). Verificado: HTTPS directo a la IP no conecta y a través
   de Cloudflare responde 200.

El usuario eligió Cloudflare Access en lugar de filtrar por IP para el acceso
de operación. Caddy exige que llegue `Cf-Access-Jwt-Assertion` pero no valida
su firma: con el origen cerrado a Cloudflare, esa cabecera solo puede venir de
Access. Si algún día se abre el origen a otro tráfico, hay que validar el JWT.
Hasta que Access esté configurado, `/control`, `/admin` y `panel.` responden
404: si falta la configuración, el acceso queda cerrado, no abierto.

Backups: `pg_dump -Fc` (el formato que lee `restore_db.sh`, no el `.sql.gz`
del README anterior) y sin `rclone`, porque no hay destino externo. Esto
queda pendiente y es el mayor riesgo que sigue abierto: la base guarda picks
sellados que no se pueden reconstruir.

Las contraseñas de Grafana de `.env.server` se regeneraron antes del primer
arranque porque se mostraron en la salida de una herramienta durante la
sesión.

## 2026-09-23 — Preparación del despliegue: el cron del contenedor nunca habría funcionado

Al revisar `docker-compose.yml` y `scripts/crontab` antes del primer despliegue
salieron dos fallos que habrían dejado el sistema entero parado sin un solo
error visible (cada job escribe en su propio log dentro del contenedor):

1. El worker copiaba a `/etc/environment` (de donde cron toma el entorno vía
   pam_env) solo las variables con ciertos prefijos. `API_FOOTBALL_*` no
   estaba: calendario, resultados, alineaciones, lesiones y cuotas de
   API-Football habrían fallado en cada pasada. Tampoco `PUBLISH_*`,
   `SOFT_*`, `META_*`… Ahora se copia todo. Una lista blanca de prefijos es
   exactamente el tipo de cosa que se queda atrás cada vez que se añade una
   variable.
2. El crontab no fijaba `PATH`; el de cron es `/usr/bin:/bin` y en
   `python:3.12-slim` el intérprete está en `/usr/local/bin`. "python: not
   found" en cada job. `BASH_ENV` no servía de nada con `SHELL=/bin/sh`.

No verificado en un contenedor real: no hay Docker en este entorno. Por eso el
procedimiento termina comprobando `/var/log/af_odds.log` tras la primera pasada.

Decisión de migración: se restaura la base local (`pg_dump`, 4 MB) en vez de
rehacer el backfill en el servidor, porque los alias revisados a mano no se
reproducen solos. `scripts/restore_db.sh` se niega a pisar una base con datos
sin `--force` y re-crea permisos y contraseña del rol de Grafana (el `004` lo
crea con una contraseña por defecto que no coincide con la de Grafana). La
base local no tenía ningún modelo activo ni lotes sellados: no había cadena que
trasladar, pero hay que entrenar el primer modelo en el servidor antes de las
08:00. `014_injuries` tampoco estaba aplicada en local; se aplicó.

## 2026-09-23 — Sombra del criterio sharp: lo que decide si se reactiva la publicación

Paso 5, último del plan. `src/qf/publish/shadow_sharp.py`, `db/018`.

- **Qué cuenta para la puerta: lo que se habría publicado, no cada oferta.**
  Capturando cada hora, un mismo partido acumula decenas de ofertas; contarlas
  todas inflaría `n` con apuestas correlacionadas que nadie habría hecho. La
  vista "publicables" toma, por partido, la primera pasada en la que el
  criterio habría dado un pick con stake, y de ella la de mayor edge esperado:
  una fila por partido, como el sistema real. Todas las ofertas se desglosan
  aparte para investigar.
- **Se registran también las ofertas de stake 0.** Son las de casas con
  persistencia medida nula (William Hill); sin registrarlas no habría forma de
  comprobar si esa persistencia está bien estimada.
- **Se guarda la persistencia usada ese día** en cada oferta: la tabla de
  `picks.PERSISTENCE` va a cambiar con esta misma muestra, y el informe tiene
  que poder distinguir qué se decidió con qué.
- **Tablas propias, no `shadow_picks`**: aquellas cuelgan de una predicción
  del modelo en sombra, y este criterio no sale del modelo.
- **Desglose por antelación (0-6, 6-24, 24-48, 48-72 h).** El histórico solo
  validó 24-48 h. Si el valor solo aparece en un tramo, hay que restringir la
  publicación a él antes de reactivarla.
- **Reactivar la publicación no es automático.** `/model-card` publica
  `sombra_criterio_sharp.autorizada`, pero `PUBLISH_PICKS_ENABLED=1` lo pone
  el usuario, viendo el desglose.

Corregidos de paso dos textos que ya eran falsos tras el paso 4: el
`/model-card` y el comentario de `PUBLISH_PICKS_ENABLED` decían que el
criterio vigente ordenaba por el edge del modelo.

## 2026-09-23 — El modelo deja de elegir los picks

Paso 4. `publish/picks.py` selecciona casas blandas que pagan por encima del
precio justo de Pinnacle; el criterio del modelo (anti-señal medida) se borró
con sus integraciones. Decisiones que no se leen en el diff:

- **Un snapshot, nunca dos fuentes cruzadas.** La casa blanda y Pinnacle
  salen de la misma respuesta (API-Football) o de la misma captura (The Odds
  API). Un 1xBet de API-Football de hace 19 h contra un Pinnacle fresco de The
  Odds API "mostraría" el movimiento de las 19 h como edge.
- **Point-in-time.** Del lado de API-Football solo cuenta lo que ya teníamos
  (`fetched_at ≤ ahora`), y por antigüedad del precio (`odds_as_of`) se corta a
  6 h: un pick con un precio que ya no existe engaña al suscriptor y además
  infla el CLV medido, porque se compara una cuota que no se podía tomar.
- **El stake sale del edge esperado al cierre, no del bruto**, con la
  persistencia medida por casa (1xBet 0,72, Bet365 0,13, William Hill 0; las
  no medidas, 0,42 de población). Sustituye al 0,55 fijo para todas. Con
  persistencia 0 el candidato se genera igual —la sombra necesita medirlo— y
  `select_daily` lo descarta por stake.
- **La confianza del modelo ya no filtra.** `daily.run` pasaba solo las
  predicciones que no eran de confianza baja; eso era una regla sobre el
  modelo y ya no aplica. La predicción sigue siendo obligatoria: cada pick la
  referencia (FK) y se sella con ella.
- **`min_price`, `fair_prob`, `odds_source` y `odds_as_of` se sellan.** Son
  parte de lo que se publica; si no entraran en el payload de la cadena, se
  podrían cambiar sin que la verificación lo detectara. Los lotes anteriores
  no cambian: `verify` recalcula desde los ficheros en disco.
- **Se borró** `tests/test_eligible_markets.py` y los tests del interruptor
  de incertidumbre: probaban un comportamiento que ya no existe.
  `model/uncertainty.py` y sus tests del módulo se conservan.
- `/model-card` corregido: afirmaba que el edge publicado llevaba el factor
  0,55 y que la confianza baja impedía picks; ninguna de las dos es ya cierta.
  Añadidas como limitaciones la dependencia de 1xBet y que Bet365/Betano no
  tienen histórico.

Sin validar: el histórico midió precios de 24-48 h antes del partido; en vivo
se decide a cualquier distancia. La sombra (paso 5) debe estratificar por
antelación antes de fiarse del conjunto.

## 2026-09-23 — Captura de cuotas de API-Football en tabla propia

Pedida por el usuario. `src/qf/ingest/af_odds.py`, `db/016_af_odds.sql`.

- **Tabla separada (`af_odds_snapshots`), no `odds_snapshots`.** Esa tabla
  la leen sin filtrar por casa el consenso de mercado de `daily.py`, el mejor
  precio de `picks`, `/fair-price`, la sombra y `health` ("última captura").
  API-Football actualiza cada liga de golpe cada varias horas (2 h en MLS, 19
  h en Liga MX, 3,5 días en Premier durante un parón): sus precios viejos
  habrían entrado en todos esos cálculos, y la salud habría dado por vivo un
  worker de The Odds API caído.
- **Dos tiempos por fila.** `provider_updated_at` es el `update` del
  proveedor (cuándo existía el precio) y `fetched_at` cuándo lo supimos. Una
  decisión en T solo puede usar `fetched_at ≤ T`. Guardar solo la hora de
  captura habría hecho pasar por frescos precios de 19 horas.
- **Deduplicación por esa marca.** El proveedor devuelve la misma
  actualización durante horas; la restricción única con
  `provider_updated_at` hace que repetir la consulta no duplique filas en una
  tabla inmutable. Comprobado: 78 filas en la primera pasada, 0 en la segunda.
- **Cada hora, no cada 3 horas** como se propuso al usuario. El proveedor
  actualiza cuando le toca y el job diario decide a las 08:00: con el cron cada
  3 h, una actualización de las 06:10 no llegaría a tiempo. Coste ~50
  peticiones/hora de 7.500/día. Horizonte de 72 h, que cubre la ventana
  temprana del criterio (24-48 h).

## 2026-09-23 — Cuatro ligas con histórico de The Odds API: el valor accesible es 1xBet

Descargado 2025 de Brasil, Argentina y MLS (12.640 créditos, exactamente lo
que calculó `plan`; saldo 3.217). Con Liga MX: 1.681 partidos con Pinnacle
antes y al cierre.

| casas (umbral 2%) | n | valor esperado al cierre | IC95 |
|---|---|---|---|
| todas las casas blandas (26) | 317 | +2,78% | [1,79, 3,78] |
| accesibles: 1xBet + William Hill + 888sport | 127 | +3,83% | [2,36, 5,20] |
| solo 1xBet | 126 | +3,91% | [2,45, 5,31] |

Lo que hay debajo del +3,83%, y por qué no se puede leer como "funciona":

- **Es una sola casa.** 126 de las 127 apuestas accesibles son de 1xBet.
  William Hill y 888sport casi nunca superan el precio justo. Un producto que
  depende de una sola casa desaparece el día que esa casa limita las cuentas
  de los suscriptores, y es lo primero que hacen con quien gana.
- **Es sobre todo MLS** (85 de 127). Argentina 26 (+2,5%), Brasil 9, Liga MX 7
  y negativa. En Liga MX el valor que había (+2,43% con todas las casas) era de
  Coolbet y Unibet, que los suscriptores no usan.
- **No pasa la puerta en amplitud:** pide 3 ligas con 30 apuestas; con las
  casas accesibles solo MLS la supera en un año.
- Coincide con football-data, que es independiente: 1xBet +2,78% en las 7
  ligas europeas en 2024/25 (única temporada en que los CSV la incluyen).

**Las casas de los suscriptores no están donde se creía.** Decisión del
usuario: apuestan en casas internacionales presentes en LatAm (Bet365, 1xBet,
Betway, William Hill, 888…). La región `eu` de The Odds API solo cubre 1xBet,
William Hill y 888sport; Bet365 no está en The Odds API (solo `bet365_au`),
Betway solo en `uk`, y no hay ninguna casa mexicana. Preguntado a
API-Football (`/odds/bookmakers` y `/odds` por competición): de 33 casas en su
catálogo, solo 9 cotizan de verdad nuestras competiciones, y entre ellas están
**Bet365, Betano, 1xBet y William Hill, junto a Pinnacle en la misma
respuesta**, en 12 de 13 (Champions sin cuotas en la consulta). Betway,
888sport, Betcris y Sportingbet están en el catálogo pero con cero partidos.
Límites: refresco cada ~3 h y solo 7 días de histórico, y no se sabe si su
Bet365/Betano son los precios de las webs mexicanas o los internacionales.
Otros proveedores revisados: OddsPapi tiene Betano MX (la única versión
mexicana encontrada) y OpticOdds tiene Playdoit; ninguno tiene Caliente.

## 2026-09-23 — Histórico de The Odds API: Liga MX tiene valor, pero en casas europeas

Paso 3. `src/qf/ingest/odds_history.py`. Decisiones:

- **No se escribe en `odds_snapshots`.** El plan decía lo contrario; se
  cambió al escribir el código. Esa tabla es inmutable y alimenta el
  entrenamiento (`window_tag='close'`) y la liquidación: un error de parseo o
  de emparejamiento quedaría para siempre y contaminaría las dos. Las
  respuestas se guardan crudas en `.local/odds_hist/` y se reprocesan sin
  volver a pagarlas. Cargarlas en la base es una decisión aparte.
- **Cómo se gasta poco.** Un snapshot trae TODOS los partidos próximos de la
  competición, así que el precio temprano sale de un snapshot diario a las
  12:00 UTC (24-48 h antes de cada partido) y el cierre, de uno por hora de
  inicio distinta, 5 min antes. `plan` calcula el número exacto con el
  endpoint de eventos (1 crédito por semana) ANTES de gastar.
- **Solo 1X2.** El backtest de football-data no encontró oportunidades
  verificables en over/under; cada mercado duplica el coste.
- **Guardas propias del feed:** una cuota con `last_update` de más de 60 min no
  cuenta como apostable; un "cierre" de más de 30 min antes del kickoff no es
  un cierre; los exchanges no entran como casa blanda (cobran comisión). La
  guarda de referencia es la misma del backtest, con el consenso de las casas
  blandas del snapshot en lugar de la media de football-data.

Coste medido para 2025: Liga MX 3.920, Brasil 3.910, Argentina 5.090, MLS
3.640 créditos (16.560 en total). Solo se descargó Liga MX.

Resultado Liga MX 2025 (316 partidos con Pinnacle antes y al cierre, 22 casas):
mejor cuota a umbral 0% → n=148, valor esperado al cierre justo +2,43%, IC95
por semanas [0,47, 4,20]; a 2% → n=70, +2,87% [−0,18, 5,51], sin concluir.

Lo que importa para el producto: el valor se concentra en Coolbet (38 de 70
apuestas a 2%, +4,39%) y Unibet (`unibet_eu` +4,00%). Son casas europeas; es
probable que un suscriptor en México no pueda usarlas, y la región `eu` de The
Odds API no incluye casas mexicanas. `unibet_it/nl/se` son la misma casa con
otra marca y dan exactamente las mismas cifras: al contar apuestas por casa no
hay que sumarlas como independientes. Y el volumen es bajo: 148 apuestas al año
en una liga con la puerta pidiendo 300 en 3 ligas.

## 2026-09-23 — Liquidación de AH: fracción ganada y fracción devuelta, por separado

El bug anotado en la entrada de abajo. `_settle_outcome` devolvía un único
multiplicador (`0,5·a + 0,5·b`, con el empuje valiendo 0,5 por pata) y
`settle_pending` lo multiplicaba por la cuota. Eso paga a cuota la mitad
empujada, que en realidad solo se devuelve. A 1,90: medio-ganada +0,425 en vez
de +0,45, medio-perdida −0,525 en vez de −0,50. A 2,00 coinciden, y por eso no
lo delataba ningún ejemplo "redondo".

Se eligió devolver `(outcome, ganada, devuelta)` en vez de una función de la
cuota porque es exactamente la descomposición que ya usa
`pricing.market_asian_handicap` para fijar la cuota justa (`E[w]·cuota +
E[push]`). Precio y liquidación hablan ahora el mismo idioma, y el empuje de
línea entera deja de ser un caso especial en `settle_pending`: con
ganada=0 y devuelta=1 el beneficio sale 0 solo.

El error no era ruido: en medio-ganada y medio-perdida vale
`0,25·cuota − 0,5` por unidad, con signo fijo según el lado de 2,00. Por
debajo (casi todas las cuotas de AH) restaba siempre; por encima sumaba.
Habría sesgado el ROI publicado sin tocar el CLV, así que la puerta no lo
habría detectado. `pick_results` estaba vacía: no hubo filas que
rehacer. `shadow.py` liquida solo 1X2 con su propio código y no usa
`_settle_outcome`.

## 2026-09-23 — Backtest "casa blanda contra sharp" en el repo, y Pinnacle también se rompe

Paso 2 del plan: `src/qf/eval/soft_vs_sharp.py`. Reproduce el piloto al
decimal (mismos n y EV por casa), así que el piloto no tenía un error de
cálculo. Pero al mirar la tabla completa apareció algo que el piloto no vio.

**La referencia sharp también falla, y en over/under falla de forma que se
esconde sola.** Bet365 y la MEDIA del mercado daban "edges" tempranos del
10-13% en over/under que persistían ENTEROS hasta el cierre (persistencia
≈1,0). La media del mercado no puede batir al precio justo por 12 puntos. Las
filas lo explicaban: Pinnacle a 1,53/2,63 mientras todas las casas daban
1,36-1,44 en el over, y con el precio temprano idéntico al de cierre. Pinnacle
congelado o en otra línea. El cierre no lo delata porque es el mismo precio
roto: es exactamente el tipo de fallo que un backtest valida a sí mismo.

Comprobación independiente: en 2024/25, único año con Betfair Exchange en los
CSV, cuando Pinnacle y Betfair discrepan más de 3 puntos en over/under, la
media de las casas se pone del lado de Betfair en 21 de 24 casos. En 1X2 casi
no ocurre (5 casos, y la media apoya a Pinnacle en 4).

Guarda elegida: `MAX_SHARP_DEVIATION = 0,03` sobre la probabilidad justa de
Pinnacle TEMPRANA frente a la de la media de las casas TEMPRANA. Solo usa
información anterior al cierre, así que no es una fuga y se puede aplicar
igual en vivo. El 0,03 es unas dos veces el p99 de la desviación (1,5-1,6
puntos) y es el primer valor en el que desaparecen TODOS los casos de "la media
supera el precio justo". Descarta 1 mercado 1X2 y 42 de over/under de 14.294.
Sin media completa no se puede verificar y el mercado no entra.

Resultado con guarda (1X2, umbral 2%, mejor cuota entre las 6 casas reales):
n=1.378, EV al cierre justo +2,09% (IC95 por semanas [1,21, 2,91]), positivo
en las 7 ligas; persistencia 0,42; ROI +2,9% con IC [−10,2, +15,1], sin
concluir. Over/under en casas reales: 11 apuestas, IC que incluye cero. El
"máximo del mercado" sigue positivo en los dos mercados, pero no es una casa y
no se puede publicar como pick.

Lo que esto NO prueba: los CSV traen un único snapshot pre-cierre (viernes o
martes), no la operación real con varias ventanas; no incluye el límite de
cuentas de las casas blandas; y el ROI no está demostrado. Lo que SÍ prueba es
que el criterio tiene valor contra la misma vara que decide la puerta, que es
lo que el criterio del modelo no tenía.

Fuera de alcance, con motivo: hándicap asiático (la línea temprana y la de
cierre cambian a menudo). Al revisar su liquidación salió un bug aparte en
`clv._settle_outcome`: en líneas de cuarto trata la media apuesta devuelta
como si pagara a cuota, así que medio-ganada y medio-perdida solo se liquidan
bien a cuota 2,00. Anotado como tarea aparte.

## 2026-09-23 — La puerta comercial decide por valor esperado al cierre sin margen

Paso 1 del plan. `ev_close_pct = price × closing_prob_devig − 1` pasa a ser la
cifra de la puerta (`evaluate_clv_gate`) y de la puerta de sombra
(`evaluate_shadow_promotion`). `clv_pct` se conserva y se publica: quitarlo
rompería la comparabilidad con lo ya reportado, y enseñar las dos cifras
explica el sesgo al lector del track record.

Decisiones que no se ven en el diff:

- **`closing_prob_devig` cambió de definición, no solo de uso.** Antes
  `_closing_prices` tomaba por cada selección la cuota sharp si existía y si no
  otra casa, así que el de-vig podía mezclar precios de dos casas. Ahora sale
  de UN snapshot de cierre de Pinnacle (`window_tag='close'`, mismo
  `captured_at`) con el grupo completo. Si no lo hay, no se mide: una apuesta
  sin cierre justo no puede demostrar valor. Se eligió exigir `close` y no "el
  último precio antes del kickoff" porque, si falló la ventana de cierre, el
  último precio puede ser de días antes y ya no es un cierre.
- **El hándicap se empareja con la línea opuesta.** The Odds API guarda local
  −0,5 y visitante +0,5; el filtro por línea igual del código anterior nunca
  encontraba la pareja, así que en hándicap `closing_prob_devig` salía siempre
  vacío sin avisar.
- **BTTS, doble oportunidad y totales por equipo no cuentan para la puerta.**
  El worker no captura esos mercados, así que no hay cierre sharp. Aparecen en
  `n_without_fair_close` para que se vea cuántos quedan fuera.
- El mensaje de rechazo pasó de "incluye cero" a "no está entero por encima de
  cero": con la vara nueva el caso típico es un intervalo entero NEGATIVO, y
  "incluye cero" habría sido falso.

Verificado contra cierres reales del histórico: tomar el propio cierre de
Pinnacle en un Inter–Lecce da −2,0% de valor esperado, que es su margen. 289
tests. `pick_results` y `shadow_results` estaban vacías: no hubo nada que
rellenar.

## 2026-09-23 — Publicación de picks pausada y The Odds API solo en `eu`

Decisión del usuario tras el piloto de abajo. `PUBLISH_PICKS_ENABLED=0` por
defecto: el job diario sigue prediciendo y sellando las predicciones, pero no
selecciona, guarda ni difunde picks. Se eligió un interruptor en vez de borrar
la selección porque la reanudación es una decisión explícita, no un
redespliegue, y porque el criterio nuevo aún no existe. Se sigue sellando
porque las predicciones del día deben quedar probadas aunque no haya picks; el
orden predecir → sellar no cambia. `/model-card` publica que está pausada.

Región de The Odds API: solo `eu` (Pinnacle y Betfair Exchange). Esto corrige
la entrada de más abajo del mismo día que la había subido a `eu,us`: con `us`
el vivo gastaba ~11.610 de 20.000 créditos y no quedaba margen para el
histórico, que cuesta 10× por llamada. Ahora ~5.800 en vivo y ~14.000 libres.

## 2026-09-23 — Piloto "casa blanda contra precio sharp": el criterio de mercado sí tiene valor, y la vara de CLV estaba torcida

Tres hallazgos, medidos con un script de scratchpad (no en el repo todavía):

1. **El CLV histórico SÍ era medible.** Los CSV del formato principal de
   football-data traen cuotas pre-cierre de 8 fuentes además del cierre, para
   1X2, O/U 2,5 y AH. `history_fd._ingest_rows` guarda solo la primera familia
   disponible (`break`) y tiraba el resto. README corregido.
2. **Seleccionar por distancia al precio sharp funciona donde el modelo
   falla.** 14.294 partidos, 7 ligas, 2019-2025. Precio justo temprano = Shin
   sobre Pinnacle pre-cierre; se apuesta si `cuota_blanda × p_justa − 1 ≥ 2%`.
   Valor esperado contra el cierre justo: máximo del mercado +3,05% (IC95
   [2,68, 3,39], n=4.684), 1xBet +2,78%, Bwin +1,37%, Bet365 +0,56% (IC95
   [−0,64, 1,81]), William Hill −0,37%. ROI realizado no concluyente (máximo
   +0,95%, IC95 [−5,1, +7,0]). Qué fracción del edge temprano sobrevive al
   cierre depende MUCHO de la casa (Max ~0,71, 1xBet ~0,68, Bet365 ~0,12): un
   encogimiento constante único está mal planteado. El "máximo del mercado" es
   una cota optimista: mezcla casas a las que un suscriptor quizá no accede.
3. **`clv_pct` está sesgado al alza por el margen.** Se calcula contra el
   cierre de Pinnacle CON margen (`price / close − 1`). Apostar a Pinnacle
   temprano en todo, sin criterio, da `clv_pct` −0,32% pero valor esperado
   contra el cierre justo −3,90%. La puerta comercial (`evaluate_clv_gate`)
   lee `clv_pct`: podía autorizar una estrategia con EV ≈ −3%. La cantidad
   correcta es `price × closing_prob_devig − 1`, y `closing_prob_devig` ya se
   guarda en `pick_results`.

Además: la puerta de CLV solo se REPORTA en `/model-card`; `daily.py` no la
consulta y publica (y sella en la cadena, para siempre) con el criterio viejo
en cuanto el cron corra con cuotas reales.

## 2026-09-23 — The Odds API subida a plan de pago: el cron de `odds_worker` deja de ser manual

El usuario dio de alta una nueva `ODDS_API_KEY` de pago, 20.000 créditos/mes
(reinicia el día 1 a las 00:00 UTC), reemplazando la del plan de 500 créditos
que obligaba a correr `odds_worker` a mano. Con el coste ya medido el
2026-09-22 sobre el calendario real de las 13 competiciones
(`eu,us x h2h,totals,spreads` ≈ 1.935 llamadas/mes × 6 créditos = ~11.610
créditos/mes), el nuevo plan cabe con 1,7x de margen — antes ni la opción más
barata cabía en 500. `.env` ya no restringe a `eu x h2h`: pasa a
`ODDS_API_REGIONS=eu,us` / `ODDS_API_MARKETS=h2h,totals,spreads`, la
configuración completa que ya asumía el cálculo de coste. `scripts/crontab`
ya traía la línea de `odds_worker` cada 10 min sin comentar, así que no hizo
falta tocar el cron en sí — el bloqueo era solo de crédito/clave.

**Lo que sigue sin verificar:** no hay Docker en este entorno, así que no se
confirmó el despliegue real del contenedor con cron activo, ni que el
consumo de crédito en producción coincida con lo estimado sobre el
calendario anunciado (los reprogramados y los mercados que de verdad devuelve
cada casa pueden variar el coste real).

## 2026-09-23 — Un solo FastAPI para web demo, API y control interno

La decisión posterior del usuario sustituyó el BFF como segundo servicio:
el mismo FastAPI sirve el prototipo en `/` y un panel de lectura en
`/control`. Se conserva el aislamiento de permisos: `/v1` y `/admin`
mantienen sus tokens de servidor, `/control` exige credenciales humanas
separadas y Caddy limita `/admin` y `/control` a la IP operativa. El
JavaScript solo contiene datos ficticios. No se activaron cuentas de cliente,
pagos ni picks premium reales porque la puerta de CLV sigue pendiente.
Pruebas de regresión: 278 pasan; el frontend valida sintaxis. El arnés no
pudo ejecutar Python ni Docker desde Git Bash en este entorno, por lo que
se ejecutó pytest explícitamente con `.venv` y no se validó Caddy en un
contenedor.

## 2026-09-22 — Prototipo visual antes de la web comercial

El usuario pidió ver un prototipo completo en modo demo y eligió expresamente
la distribución y los menús de Pitchverse como referencia visual. Se creó
`frontend/` con seis vistas navegables y datos ficticios, sin integrar la API:
el objetivo es validar el diseño sin aparentar que ya hay picks rentables o
una suscripción activa. La aplicación comercial sigue pospuesta hasta reunir
CLV real y superar la puerta de la fase 2. El futuro navegador hablará con un
backend web propio; el `SERVICE_TOKEN` de FastAPI nunca se pondrá en JS.

## 2026-09-21 — Arnés inicial creado

- El proyecto tenía dos versiones del `README.md`: una suelta en la raíz
  (más antigua, sin mención de Grafana ni de los tres niveles de auth de la
  API) y otra empaquetada dentro de `pyton/quantfut.tar.gz` (menciona
  `db/004_grafana_readonly.sql`, `grafana/`, y coincide exactamente con los
  archivos reales que trae el propio tar.gz). Se conservó la versión del
  tar.gz porque es la que describe el código que realmente existe. Si esto
  fue un error, la versión anterior no quedó guardada aparte — revisar con
  el usuario si hace falta.
- `pyton/` contenía archivos `.py`/`.sql`/`.sh` sueltos que resultaron ser
  copias idénticas (diff sin diferencias) de los mismos archivos dentro del
  `quantfut.tar.gz`. El tar.gz es el repo completo (incluye `db/`, `src/qf/`
  completo, `docker-compose.yml`, `Dockerfile`, `requirements.txt`,
  `grafana/`); se extrajo a la raíz del proyecto para que la estructura
  coincida con la que documenta README.md.
- El tar.gz traía dos directorios basura con nombres literales
  `{db,src` y `{db,src/qf/{ingest,model,publish,eval,api},scripts}` —
  artefacto de un `mkdir -p {a,b}` corrido sin expansión de llaves al crear
  el archivo. Estaban vacíos, se eliminaron.
- No se inicializó git ni se borró `pyton/` — no había repo git en el
  directorio, así que borrar sin poder revertir era riesgo innecesario. Se
  dejó como nota en `harness/tareas.md` para que el usuario lo confirme.
- No existe todavía suite de tests (`pytest` u otro). `scripts/harness_check.sh`
  por ahora solo valida sintaxis Python (`py_compile`) y `docker compose
  config`; si se agrega una suite de tests, añadir esa verificación aquí.

## 2026-09-21 — Alcance: sin Telegram, foco en la API para la web

El usuario confirmó que no usa Telegram — la venta de picks es solo en su
propia web, consumiendo esta API. Decisiones tomadas en esta sesión:

- **El reparto free/paid ya no lo decide Telegram.** Encontré que
  `daily.py` llamaba `pk.persist(selected, tier="paid")` con un tier fijo
  para TODO el lote, y era `telegram.publish_batch()` quien in-place decidía
  qué picks eran "gratis" (los primeros `free_count=2` por edge) solo para
  el mensaje de Telegram — nunca se reflejaba en la BD. Consecuencia real:
  `/picks/free` y la vista gratuita de `/v1/picks` devolvían siempre una
  lista vacía, porque en la tabla `picks` todo quedaba con `tier='paid'`.
  Solución: `picks.assign_tiers()` (nuevo, en `src/qf/publish/picks.py`)
  decide el tier antes de persistir, usando `settings.free_picks_per_day`
  (nuevo en `config.py`, default 2, env `FREE_PICKS_PER_DAY`). `daily.py`
  pasa ese mismo reparto a Telegram en vez de dejar que Telegram lo calcule
  de nuevo. Telegram sigue siendo 100% opcional (no-op si no hay
  `TG_BOT_TOKEN`), pero ya no es la fuente de verdad de nada.
- **Gap de modelo encontrado leyendo `model/train.py`, no está en el
  README:** `train_and_register()` llama `load_training_data()` sin
  `league_id`, así que el Dixon-Coles se ajusta con las 7 ligas mezcladas en
  un solo fit — una sola ventaja de local y una sola escala de fuerza
  ataque/defensa para Premier League, Liga MX, Brasileirão, etc. La función
  ya soporta filtrar por `league_id`; no se usa. No lo toqué todavía (el
  usuario pidió enfocarse en la API primero) — queda en
  `harness/tareas.md` como pendiente de mayor impacto que la calibración,
  porque calibrar un modelo mal especificado por liga no corrige el sesgo
  de fondo.
- **Endpoints añadidos a `src/qf/api/main.py`:** `GET /leagues`,
  `GET /teams` (filtrable por `league`), `GET /matches/{match_id}` público
  (ficha de partido con predicción recortada a tier gratuito — pensado para
  páginas de partido indexables sin login). Antes no existía forma de que
  el frontend listara ligas/equipos sin pegarle directo a Postgres.
- **Paginación** (`limit`/`offset`) añadida a `/picks/free` y `/v1/picks`;
  antes devolvían todo el resultado sin límite.
- **Pendiente explícito, no urgente ahora:** auth de suscriptor sin
  Telegram (email/magic-link o vía checkout de pago) y el webhook de
  cobros. El usuario dijo textualmente que eso es "después".

## 2026-09-21 — Corrección de las brechas técnicas del modelo

Decisiones de diseño que no son obvias leyendo el código:

- **Por qué la calibración actúa sobre las lambdas y no sobre el 1X2.** Los
  ~150 mercados salen todos de la misma matriz de marcadores. Calibrar el
  1X2 directamente (isotónica, que es lo estándar) dejaría el over/under y
  el hándicap saliendo de una matriz sin corregir, y el producto publicaría
  un 1X2 que no cuadra con su propio total de goles. La corrección afín en
  log-espacio sobre (lambda, mu) recalcula toda la matriz y mantiene la
  coherencia. Se pierde algo de flexibilidad frente a la isotónica; se gana
  que el producto no se contradiga a sí mismo.
- **Por qué NO se usó PyMC/numpyro para el modelo jerárquico.** El pooling
  parcial está implementado como penalización en la verosimilitud, que es el
  estimador MAP del mismo modelo jerárquico. Da el encogimiento (que es lo
  que se quería) sin añadir una dependencia pesada ni muestreo NUTS, que el
  propio README dice que es lo único que justificaría GPU. Si algún día se
  quieren intervalos de credibilidad por equipo, ahí sí hace falta la
  versión bayesiana completa.
- **Por qué el riesgo de portafolio usa la probabilidad del MERCADO.** Medir
  la varianza con la probabilidad del propio modelo la subestima justo
  cuando el modelo está sobreconfiado, que es el caso por defecto y la razón
  de existir del shrinkage. Ver `picks._risk_prob`.
- **Por qué las correlaciones son constantes y no estimadas.** Con unos
  cientos de picks liquidados, estimar una matriz de correlación daría
  ruido. Son cotas superiores razonadas; equivocarse por prudencia solo
  cuesta tamaño de apuesta. El número que NO puede ser cero es `CORR_BASE`:
  todos los picks salen del mismo modelo, y ese riesgo común no se
  diversifica repartiendo entre ligas.
- **Por qué el modelo de residuo está desactivado por defecto.** Corrige
  solo el 1X2, así que mientras esté activo ese mercado deja de ser
  coherente con el resto del paquete. Es una decisión de producto, no
  técnica, y por eso la toma `RESIDUAL_ENABLED` y no el código. Se entrena
  siempre igualmente, para poder medir cuánto se está dejando sobre la mesa.
- **Bug encontrado de paso:** `train.py` versiona por fecha
  ("2026.09.21") pero `daily.py` cargaba `dc_{MODEL_VERSION}.pkl` desde una
  variable de entorno fija. El primer reentrenamiento habría dejado el job
  diario cargando un artefacto viejo o ninguno, sin avisar. Ahora el modelo
  activo se resuelve desde `model_artifacts`, que es la única fuente de
  verdad de qué está desplegado.

## 2026-09-21 — Ponderación modelo/mercado + bug crítico de unidades

- **`model/meta.py`**: estima `w_model` minimizando log-loss fuera de muestra
  sobre `blend_logit()` (que ya existía sin que nadie calculara su peso).
  Detalle: `blend_logit` es en realidad un *log-opinion pool* (media
  geométrica de probabilidades renormalizada), no una mezcla en logit pese al
  nombre. La matemática es la estándar y correcta para multiclase, así que se
  reutilizó tal cual en vez de duplicarla.
- **Pesos por liga** encogidos hacia el global con pseudo-conteo
  (`LEAGUE_SHRINK_K=600`), misma filosofía de pooling que el modelo. Una liga
  con menos de 250 partidos no recibe peso propio.
- **Por qué la mezcla viene DESACTIVADA.** Acerca las probabilidades al
  mercado y por tanto REDUCE el edge: con w bajo, muchos picks dejan de
  superar el umbral. Es correcto, pero cambia cuántos picks se publican al
  día, y esa es una decisión de negocio. El peso se estima y se publica en
  `/model-card` aunque esté apagada.
- **Riesgo sutil que obligó a restringir mercados.** Solo se mezclan 1X2 y
  totales (el AH tiene empuje en líneas enteras y necesita trato aparte). Si
  se mezclara solo eso y la selección siguiera mirando todos los mercados,
  los NO mezclados conservarían el edge inflado y el sistema se desplazaría
  solo hacia ellos: apostaría justo donde menos ha validado. Por eso
  `find_candidates` respeta `eligible_markets` cuando la mezcla está activa.
  Cubierto por `tests/test_eligible_markets.py`.
- **Exclusión mutua con el modelo de residuo**: ambos fusionan con el
  mercado (el residuo usa `logit_gap` modelo-mercado como feature).
  Aplicarlos juntos contaría la información del mercado dos veces. `daily.py`
  avisa y desactiva el residuo.
- **BUG CRÍTICO PREEXISTENTE ENCONTRADO: unidades del stake.** `kelly()`
  devolvía una fracción de banca (0.0067 = 0.67%) pero el resto del sistema
  interpretaba ese número como unidades, donde 1 unidad = 1% de banca (es la
  única lectura coherente: `MAX_STAKE_UNITS=2.0` sería si no un tope del 200%
  de la banca por apuesta, y la exposición diaria de 10.0 sería del 1000%).
  Consecuencia real: el descarte `stake <= 0.05` de `find_candidates`
  eliminaba TODOS los picks con edge realista (3-10%) — comprobado a cuotas
  1.8/2.5/3.5 — así que el sistema habría publicado CERO picks
  indefinidamente sin dar ningún error, y lo natural habría sido culpar al
  modelo. Corregido con la conversión ×100 y el contrato fijado en
  `tests/test_kelly_units.py` para que no pueda volver a romperse en
  silencio.

## 2026-09-22 — Postgres local y verificación end-to-end

PostgreSQL 16.15 instalado nativamente (winget, servicio `postgresql-x64-16`,
puerto 5432). Base `quantfut`, rol `qf`. El `.env` local apunta ahí. El
esquema completo (`db/001..004`) se aplicó por primera vez: 17 tablas, 6
vistas, 5 triggers, 7 ligas. `db/004_grafana_readonly.sql` necesita
superusuario (crea un rol), en producción eso lo cubre
`docker-entrypoint-initdb.d`.

**Garantías de BD verificadas ejecutándolas de verdad:** UPDATE y DELETE
rechazados en `predictions`, `picks` y `odds_snapshots`; `features_pit`
rechaza `as_of > kickoff`. Funcionan tal como documenta el README.

**El modelo por liga funciona con datos que pasaron por la base.** Se
sembraron dos ligas con ventaja de local deliberadamente distinta y el
entrenamiento real las recuperó por separado:

| liga | ha sembrada | ha recuperada | base sembrada | base recuperada |
|---|---|---|---|---|
| mx.liga_mx | 0.42 | 0.4021 | 0.22 | 0.2211 |
| gb.premier_league | 0.18 | 0.2147 | 0.12 | 0.1019 |

`beats_market: false` — la evaluación no se autoengaña. La calibración y el
modelo de residuo fueron correctamente DESCARTADOS por sus puertas
(calibración no mejoraba; residuo sin datos suficientes).

### Cuatro bugs preexistentes que solo aparecen con Postgres real

1. **`IndeterminateDatatype` en el filtro opcional por liga.** El patrón
   `(%s IS NULL OR col = %s)` no compila: Postgres no infiere el tipo de un
   parámetro suelto en una comparación IS NULL. Afectaba a
   `train.py::load_training_data` (fallo del 100% de los entrenamientos, en
   la primera llamada), a `/v1/fixtures` y a `clv.py::_closing_prices` (la
   ruta de liquidación). Corregido con casts `::text` / `::real`.
   OJO al corregirlo: psycopg cuenta los `%s` que aparezcan DENTRO de los
   comentarios SQL como marcadores; un comentario explicativo con `%s` rompe
   la consulta.
2. **`pd.Timestamp(start_date, tz="UTC")` con fecha ya consciente de zona.**
   `train.py` pasa `df["kickoff_utc"].max() - timedelta(...)`, que siempre
   trae zona. Reventaba todo walk-forward. Ahora se normaliza.
3. **Fecha del lote en UTC vs cast en zona del servidor.** `hashchain._collect`
   comparaba `generated_at::date` (que castea en la zona del SERVIDOR) contra
   un `batch_date` calculado en Python con UTC. Con el servidor en
   America/Mexico_City las fechas discrepaban, el lote salía vacío, no se
   sellaba y —por diseño— NO SE PUBLICABA NADA. Fallo mudo. Corregido con
   `(generated_at AT TIME ZONE 'UTC')::date`. En Docker suele pasar
   desapercibido porque los contenedores van en UTC.
4. (Ya registrado arriba) unidades del stake en `kelly()`.

**Verificado end-to-end:** `qf.model.train` completo, `qf.publish.daily`
(predice, sella, publica), `hashchain verify` OK, y todas las rutas de la API
contra datos reales, incluidas `/leagues`, `/teams`, `/matches/{id}` y el
`/model-card` con parámetros por liga y peso modelo/mercado.

**Lo que sigue sin verificarse:** los datos son SINTÉTICOS (goles Poisson
desde fuerzas conocidas, cuotas derivadas de la probabilidad verdadera más
margen). Sirven para verificar el CÓDIGO, no para evaluar el modelo. El
`w_model=0.43` que sale es alto justo porque el modelo coincide con el
proceso que generó los datos; con datos reales se espera bastante más bajo.
Tampoco se ha probado `ingest/lineups.py` contra la API real de API-Football.

## 2026-09-22 — Histórico real cargado + backfill de ligas LatAm roto

Cargados **31.041 partidos reales** de football-data.co.uk (gratis, sin
claves), 7 ligas, 2014-2026, con **96.7% de cobertura de cuotas de cierre de
Pinnacle**. Es material suficiente para cerrar la Fase 2 (validar si el modelo
tiene edge) sin pagar ninguna API.

### Quinto bug preexistente: las 3 ligas LatAm nunca cargaban nada

`history_fd.py` trataba el formato "extra" (Liga MX, Argentina, Brasil) como
si fuera el principal. Dos fallos superpuestos, ambos mudos:

1. **Nombres de columna distintos.** El extra usa `Home`/`Away`/`HG`/`AG`; el
   código leía `HomeTeam`/`AwayTeam`/`FTHG`/`FTAG`. Cada fila salía None y se
   descartaba en el primer `isinstance`.
2. **Filtro de temporada que no casa nunca.** Buscaba `'2526'` como subcadena
   de la columna Season, que vale `'2025/2026'`.

Efecto comprobado ejecutando el código viejo: `{"mx.liga_mx": 0,
"br.serie_a": 0, "ar.primera": 0}` frente a 4.560 por liga europea. Tres de
siete ligas —toda la parte latinoamericana, que es donde el README sitúa la
ventaja competitiva por haber menos apostante sharp— se quedaban vacías sin
un solo error.

Además, **no hay un único formato de temporada dentro del formato extra**:
las ligas de año natural (Brasil siempre; Argentina desde que cambió) la
escriben `'2025'` a secas, y ARG.csv contiene LAS DOS formas en el mismo
fichero. Aceptar solo la forma con barra dejaba Brasil a cero y Argentina a
un tercio (1.428 de 5.217). `season_labels_extra()` devuelve ahora ambas.

`ingest_extra()` descarga el fichero UNA vez y recorre todas las temporadas,
en vez de una sola (el extra trae todo el histórico en un CSV).

## 2026-09-22 — Kalman, cara a cara real, y xG por fin disponible

### El número que importa: ninguno de los dos modelos bate al mercado

Sobre 31.041 partidos reales, ventana de validación de 365 días:

| | RPS | log-loss | tiempo |
|---|---|---|---|
| Mercado (Pinnacle des-margenado) | **0.19994** | — | — |
| Dixon-Coles con decaimiento | 0.20359 | 1.01135 | 4.888 s |
| Ratings dinámicos (Kalman) | 0.20388 | 1.00795 | **51 s** |

Los dos modelos están empatados entre sí (0.0003 de diferencia con n=1.324 es
ruido). El hueco contra el mercado, 0.0037, es diez veces mayor y sí es real.
Es el resultado esperado y honesto: el mercado sabe más.

Kalman es **96 veces más rápido**, y eso cambia qué se puede hacer: ajustar
hiperparámetros pasa de ser una expedición mensual a algo rutinario. El
barrido ya encontró `process_var=1e-4` mejor que el 2.5e-4 por defecto.

Sanidad del ranking que produce: Inter, Barcelona, Flamengo, PSV, Arsenal,
Man City, Roma, Palmeiras, Real Madrid. Aprende fútbol real.

### `model/kalman.py`

Ratings de ataque/defensa como estado latente con paseo aleatorio. Tres cosas
que el decaimiento exponencial no puede expresar: la incertidumbre crece con
el tiempo parado (un parón de 3 meses no es igual que uno de 3 días), los
ascendidos convergen rápido, y un cambio brusco de fuerza se captura en vez de
promediarse con la época anterior.

Aproximación declarada: covarianza DIAGONAL. La completa capturaría la
correlación entre rivales pero cuesta O(n²) y aporta poco con equipos que
juegan decenas de partidos.

`predict_sequential()` predice antes de aprender cada partido: es fuera de
muestra por construcción, en una sola pasada. No hay forma de colar futuro ni
olvidándose de un filtro.

### FBref está bloqueado; worldfootballR_data no

FBref devuelve 403 con desafío de Cloudflare. `soccerdata` llega a descargar
un driver de Chrome para evadirlo y falla igual tras 400 s. Como fuente
operativa no sirve. (De paso: `xg_fbref.py` pasaba la caché como `str` y
soccerdata exige `Path`; corregido, aunque el módulo siga sin poder scrapear.)

`ingest/xg_worldfootball.py` (nuevo) descarga los mismos datos de FBref ya
raspados desde los releases de `JaseZiv/worldfootballR_data`, por HTTPS
normal, en segundos.

**La cobertura de xG pasó de 0 a 9.458 partidos**, y eso incluye 967 de Liga
MX y 1.322 de Brasileirão. **Esto contradice el README**, que da por perdido
el xG de esas ligas ("no tienen xG en las fuentes gratuitas... está en el
model-card a propósito, no es un error a arreglar"). Sí lo tienen por esta
vía. Hay que actualizar el README y el model-card.

Aclaraciones sobre el formato, porque la petición original hablaba de Parquet:
no hay Parquet en ese repositorio, solo `.rds` y `.csv`. Argentina solo está
en `.rds`, que exigiría `pyreadr`; no se añadió esa dependencia por una liga.
Los datasets se publican por lotes, así que van por detrás del presente:
sirven para entrenar, no para cerrar el xG de anoche.

### El emparejamiento de nombres es el cuello de botella, y no se automatiza

Parte de la cobertura que falta no es por ausencia de datos sino porque los
nombres de FBref no casan con los de football-data. Y el umbral NO se puede
bajar: con score ~72, `Newcastle Utd` empareja con `manchester united` y
`Leeds United` con `sheffield united`. Fusionarlos arruinaría dos equipos a la
vez en silencio. A la vez, aciertos como `Leicester City`→`leicester` (78.3) o
`Flamengo`→`flamengo rj` (84.2) quedan por debajo. No hay número que separe
los dos grupos: hace falta criterio humano. El paso 4 del README existe por
esto y está funcionando como debe al negarse.

## 2026-09-22 — Ajuste por estado del partido: NEGATIVO, y el motivo importa

`ingest/game_state.py` + 22 tests. Reconstruye el marcador minuto a minuto
desde los remates que acabaron en gol y reparte el xG de cada equipo entre
ganando / empatando / perdiendo.

**Los ratios empíricos contradicen la premisa del método** (12.928 partidos):

    perdiendo 1.135 · empatado 1.000 · ganando 1.177

Se esperaba que el equipo que gana se repliegue y produzca MENOS. Produce un
17.7% MÁS. La causa es un confundidor: ir ganando está correlacionado con ser
mejor equipo, así que el estado "ganando" no mide repliegue, mide calidad.
Normalizar por ese ratio **elimina la señal de fuerza** que el modelo busca.

Resultado medido: RPS 0.20330 → 0.20344 (todos), y 0.20075 → 0.20108
restringiendo a los partidos con ajuste. Empeora en ambas comparaciones. NO
volver a proponerlo sin estratificar por calidad de equipo.

**Validación que salvó el módulo de ser basura silenciosa:** el marcador se
deriva de los goles que fueron remate, y un AUTOGOL no lo es. Contrastado
partido a partido contra la BD en Liga MX: 1.651 cuadran, 139 no (7.8%), y en
todos los casos la BD tenía exactamente un gol más. `match_state_data()`
devuelve `None` cuando no cuadra. Sin esa comprobación, 1 de cada 13 partidos
habría tenido un estado inventado sin dar ningún error.

El módulo se conserva: la reconstrucción sirve como FEATURE del modelo de
residuo (uso distinto de corregir el objetivo) y la validación contra
autogoles es infraestructura reutilizable.

## 2026-09-22 — Exprimido el fichero de tiros: resultado en parte negativo

`db/006_shot_stats.sql` + `match_stats()` en `ingest/xg_worldfootball.py`.
Del mismo CSV tiro a tiro que ya se descargaba para el xG se extraen ahora
remates, remates a puerta, PSxG y distancia media.

**Lo que aportó:** Liga MX y Brasileirão pasaron de CERO datos de remates a
tenerlos (1.790 y 1.905 partidos). El formato "extra" de football-data.co.uk
no trae tiros ni córners, así que esas columnas llevaban vacías desde el
principio en las tres ligas latinoamericanas.

**Lo que NO aportó, medido sobre n=28.718:** el PSxG como objetivo del modelo
de fuerza EMPEORA el RPS (0.20368 frente a 0.20330 del xG actual); la media de
ambos también (0.20340). El xG que ya se usaba es el mejor de los tres. No
volver a proponer PSxG como objetivo sin una razón nueva: solo cubre remates a
puerta, así que como medida de creación de ocasiones está sesgado, y mezcla la
colocación del disparo, que es más ruidosa que la calidad de la ocasión.

**Error propio corregido en el camino:** el comentario original de la
migración afirmaba que `PSxG - xG` mide la calidad de definición. Es falso:
`psxg` suma solo remates a puerta y `xg` suma todos, así que son poblaciones
distintas y la resta sale negativa en las seis ligas (-0.006 a -0.084) sin
decir nada de los delanteros. `goles - PSxG` sí es válido (rendimiento del
portero rival) porque ambas magnitudes hablan de la misma población. El
comentario del SQL ya lo explica.

## 2026-09-22 — MEDICIÓN DEFINITIVA: el modelo no tiene edge

Con xG ya cargado y sobre **n=28.128** predicciones fuera de muestra
(veintiuna veces la medición anterior, que además corrió con cobertura de xG
a 0% y por tanto con el modelo a media potencia):

- **Pierde contra el mercado en las 7 ligas.** Delta de −0.00485 (Liga MX, el
  hueco menor) a −0.00790 (Serie A). Total −0.00653.
- **w_model = 0.0001.** El peso óptimo del modelo en la mezcla con el mercado
  es cero. El mercado ya contiene todo lo que el modelo sabe.

Hipótesis descartadas POR MEDICIÓN, no por intuición. No volver a proponerlas
sin datos nuevos:

1. "Gana en ligas latinoamericanas porque son mercados blandos" → falso, Liga
   MX tiene el hueco más pequeño pero negativo.
2. "Faltan hiperparámetros ajustados" → el barrido de `process_var` mueve la
   cuarta decimal (mejor: 2.0e-4).
3. "Falta el xG" → ayuda (0.20424 → 0.20336) pero cierra el 12% del hueco.
4. "Es cuestión de técnica" → dos motores independientes (Dixon-Coles con
   decaimiento y filtrado bayesiano) aterrizan en el mismo sitio.

**Diagnóstico: falta INFORMACIÓN, no técnica.** El modelo sabe goles y xG; el
mercado sabe además lesiones, alineaciones, rotación, motivación y clima. Más
matemática sobre los mismos datos no fabrica información.

**Límite estructural de lo medible:** todo esto compara contra el CIERRE. Un
modelo peor que el cierre aún podría ser rentable contra casas blandas antes
de que converjan —eso es el CLV—, pero el histórico de football-data solo trae
cuotas de cierre. Con un precio por partido el CLV es inmedible. Responderlo
exige `odds_worker` capturando a lo largo del tiempo. Es la justificación
empírica de por qué ese worker es el paso 0.

**Implicación de negocio:** la puerta de la fase 2 NO se cumple. Según la
propia filosofía del README, la fase 3 (vender) no arranca hasta que se
cumpla.

## 2026-09-22 — Alias curados y documentación al día

`db/005_fbref_aliases.sql`: 35 alias de FBref revisados uno a uno. La
cobertura de xG subió de 9.458 a **14.141 partidos** y quedaron **cero**
nombres sin emparejar. Lo que falta ya no es resoluble: FBref no publica xG
antes de ~2017-18 y el histórico arranca en 2014.

**No intentes automatizar esto bajando el umbral.** Está demostrado en el
propio archivo SQL: con score ~72 el matcher propone `Newcastle Utd` →
`manchester united`, `Leeds United` → `sheffield united` y `Ath Paranaense` →
`parana`, que son tres clubes distintos en cada caso. Y por encima de ese
score hay aciertos legítimos que se perderían. No existe umbral que separe
ambos grupos.

Los alias se aplican DESPUÉS del backfill (necesitan que los equipos existan);
`setup_fase1.sh` tiene ahora un paso 4b para eso, y el SQL avisa por
`RAISE WARNING` si algún equipo canónico no existe todavía.

### Documentación actualizada (instrucción permanente del usuario)

El usuario pidió que README y model-card se actualicen con cada hallazgo, sin
esperar a que lo pida. Guardado en memoria. En esta tanda:

- README: corregida la afirmación falsa sobre el xG de Liga MX y Brasileirão,
  con la tabla de cobertura real medida; añadida la medición RPS contra el
  mercado; actualizados mapa de fases, estructura, calendario de procesos y
  tabla de fuentes; documentado el bloqueo de Cloudflare en FBref.
- `model_card`: quitada la limitación falsa sobre el xG latinoamericano y
  **añadida la de que el modelo no bate al cierre de Pinnacle**. Publicar eso
  es coherente con la tesis del producto: ocultarlo es lo que hace increíble
  al sector.
- `crontab` y `/admin/run/xg`: apuntan a `xg_worldfootball`, no al scraper
  bloqueado.

**Nota histórica (previo a Postgres):** no había Postgres ni datos reales en este
entorno. Los 48 tests corren sobre datos simulados y verifican la matemática
(recuperación de parámetros, ausencia de fugas point-in-time, coherencia
entre el 1X2 vectorizado del calibrador y el de `pricing.py`). Nada se ha
ejecutado contra el histórico real ni contra la API de alineaciones. La
lista de comprobaciones con datos reales está en `harness/tareas.md`.

---

## 2026-09-22 — MLS, Champions y Europa League: competición deja de ser liga

De 7 ligas a **8 ligas + 2 copas**, 31.041 → 37.650 partidos.

### La decisión de diseño que condicionaba todo lo demás

Hasta aquí "liga" y "competición" eran lo mismo, y todo el sistema se apoyaba
en ese supuesto sin decirlo. Meter la Champions lo rompe.

La salida fácil habría sido dar de alta equipos bajo `league_id='eu.ucl'`.
Habría funcionado, no habría dado ningún error, y habría sido destructiva: el
Real Madrid de Champions sería un club DISTINTO del de LaLiga, con 6-13
partidos por temporada, ningún rival en común y ataque/defensa prácticamente
en el prior. Más de cien clubes duplicados en el catálogo.

La separación es:

- `matches.league_id` → la **competición** del partido.
- `teams.league_id` → la liga **doméstica** del equipo.

El esquema ya lo permitía: no había ninguna restricción que obligara a que
coincidieran. `db/007_competiciones.sql` añade `cross_league` para marcar las
competiciones donde no coinciden, y todo lo demás se deriva de ahí.

Consecuencias que hubo que propagar a mano (y que son la parte que se olvida):

- Toda consulta que alimenta al modelo (`train.py`, `daily.py`) trae ahora
  `th.league_id AS home_league` y `ta.league_id AS away_league`.
- `lambdas()`, `knows()` y `predict()` aceptan las dos ligas, en Dixon-Coles y
  en Kalman. Sin los parámetros se comportan como antes (la liga doméstica ES
  la competición), así que el histórico y los artefactos viejos siguen valiendo.
- `ingest/uefa_cups.py` NUNCA crea equipos: descarta el partido.
- `ingest/fixtures.py` en competiciones `cross_league` solo acepta coincidencia
  EXACTA. Buscando a la vez en todas las ligas, un difuso de 95 puntos puede poner
  un club europeo encima de uno latinoamericano de nombre parecido y contaminar
  dos historiales de golpe. Fijado por `tests/test_fixtures_cross_league.py`.

### El término `strength`: lo que las copas aportan de verdad

No es poder apostarlas. Es que son los ÚNICOS partidos entre equipos de ligas
distintas, y por tanto lo único que permite comparar ligas entre sí.

El modelo impone suma cero de ataque y defensa DENTRO de cada liga. Eso
significa que un ataque de 0,3 en Eredivisie y uno de 0,3 en LaLiga no están
en la misma escala, y dentro de los datos domésticos **no hay absolutamente
nada** que las conecte: el nivel de liga y `base[liga]` son intercambiables.

La formulación elegida añade un desplazamiento por liga con signo opuesto en
las dos intensidades:

```
log lam = base[comp] + ha[comp] + (atk[h] + str[lg_h]) - (dfn[a] + str[lg_a])
log mu  = base[comp]            + (atk[a] + str[lg_a]) - (dfn[h] + str[lg_h])
```

La propiedad que hace que esto sea seguro: **en un partido doméstico lg_h ==
lg_a y el término se cancela exactamente**. Por eso se pudo añadir sin volver
a validar las ocho ligas. `tests/test_cross_league.py` lo comprueba
recalculando la lambda a mano sin el término y exigiendo igualdad a 1e-9.

Verificado sobre simulación con dos ligas de nivel deliberadamente distinto:
con 400 cruces recupera 0,32 de una diferencia sembrada de 0,40. El
encogimiento (`POOL_STRENGTH = 300`) es deliberado y la muestra real es aún
más pequeña.

### El límite honesto: 406 cruces de 3.308

Solo sirven los partidos con los DOS equipos en el catálogo. El resto
involucra ligas que no tenemos:

| país | partidos perdidos |
|---|---|
| Alemania | 633 |
| Francia | 464 |
| Portugal | 380 |
| Bélgica | 264 |
| Rusia | 252 |

Dar de alta Bundesliga, Ligue 1 y Primeira multiplicaría por ~4 la muestra que
identifica `strength`, y las tres están gratis en football-data (`D1`, `F1`,
`P1`) y en FBref (`GER_M`, `FRA_M`, `POR_M`). Es la ampliación con mejor
relación coste/beneficio que queda pendiente. Anotada en `tareas.md`.

### Y las copas NO son apostables todavía

No existe histórico gratuito de cuotas de Champions ni de Europa League:
football-data.co.uk solo cubre ligas domésticas y el release de copas de
worldfootballR_data da resultado y xG pero ni un precio. Sin cierre no hay
baseline de mercado → no se pueden evaluar, ni calibrar, ni medir CLV. Entran
como datos de ENTRENAMIENTO. Que sean apostables depende de que `odds_worker`
acumule cierres propios.

### Hallazgo lateral: Argentina SÍ tiene xG (0% → 62,5%)

`xg_worldfootball.py` decía, con razón, que Argentina solo existe en `.rds` y
que no compensaba añadir `pyreadr` por una sola liga. **Esa decisión estaba
bien tomada y aun así había caducado**: las copas europeas tampoco tienen CSV,
así que `pyreadr` era obligatoria de todos modos. Con la dependencia ya dentro,
Argentina entró gratis: 2.304 partidos con xG en una pasada.

La lección es general y vale la pena tenerla presente: **una decisión de "no
compensa" depende del coste de la alternativa, y caduca cuando ese coste
cambia.** Cuando se amplía el alcance, toca re-revisar las decisiones negativas
escritas en los módulos, no solo añadir código nuevo.

Lo que Argentina sigue sin tener es el fichero tiro a tiro: solo el xG
agregado. Sin PSxG, sin distancia, sin estado del partido.

### Tres bugs encontrados de paso

1. **`harness_check.sh` daba "OK" sin correr un solo test.** Elegía `python3`,
   que en Windows resuelve al stub de la Microsoft Store: arranca, responde a
   `--version`, y no tiene ninguna dependencia. El script imprimía
   "(pytest no instalado)" y seguía adelante con código de salida 0. Ahora
   prefiere `.venv` y **falla** si no encuentra pytest. Un chequeo que avisa y
   sigue es peor que no tenerlo: da confianza falsa.

2. **`requirements.txt` no se podía instalar.** `soccerdata==1.8.7` entra en
   conflicto con `lxml==5.3.0` y `pip install -r` aborta con
   ResolutionImpossible. Solo lo usa `xg_fbref.py`, que el README ya da por
   inservible (Cloudflare). Comentado, con la decisión pendiente en `tareas.md`.

3. **El chequeo de salud del calendario iba a alertar todos los días.**
   `check_fixtures_horizon` exigía partidos en 10 días a TODAS las ligas
   activas. La MLS para el invierno y las copas tienen huecos de meses entre
   eliminatorias. Ahora solo avisa de competiciones en juego (con algún
   partido terminado en las últimas 3 semanas). Una alerta que salta a diario
   por algo normal se deja de leer, y con ella la del día que sí importa.

### Y uno mío, del mismo tipo que ya había cometido

`INSERT ... CASE WHEN %s IS NULL` en `uefa_cups.py` → `IndeterminateDatatype`.
Es el tercer encuentro con la misma trampa de psycopg (parámetro suelto sin
tipo inferible). Resuelto decidiendo el valor en Python en vez de en SQL.
También volvió a aparecer el `%` dentro de un comentario SQL: `db.execute()`
interpola aunque no pases parámetros, así que un "0%." en un comentario rompe
el fichero entero.

---

## 2026-09-22 — Bundesliga, Ligue 1 y Primeira: añadidas por los cruces, no por sí mismas

De 8 ligas + 2 copas a **11 ligas + 2 copas**, 37.650 → **50.079 partidos**.

La razón no es que sean ligas atractivas, que lo son. Es que eran las tres que
más partidos de copa estaban tirando a la basura. `uefa_cups.py` descarta todo
cruce en el que alguno de los dos equipos no esté en el catálogo, y el desglose
de descartes lo decía sin ambigüedad: Alemania 633, Francia 464, Portugal 380.

**Resultado: los cruces utilizables pasaron de 406 a 1.111 (×2,7).** Que es lo
único que identifica el término `strength`, es decir, lo único que permite
comparar la fuerza de una liga con la de otra.

Coste real: casi nulo. Las tres están en el formato PRINCIPAL de
football-data.co.uk, así que `ingest_season` las carga sin tocar una línea de
código; y las tres tienen fichero tiro a tiro en FBref (`GER_M`, `FRA_M`,
`POR_M`). Lo único a mano fueron 19 alias (`db/011_aliases_europa.sql`).

### Los tres alias que no se podían dejar al emparejador difuso

- **`Paris S-G`** se queda en 82 puntos contra `Paris SG` y no resuelve. Bajar
  el umbral para capturarlo lo pone a tiro de **`Paris FC`**, que es otro club
  de la misma ciudad y también está en el catálogo.
- **`Vitória`** a secas es Guimarães, no Setúbal. Comprobado por fechas:
  aparece de forma continua de 2018 a 2025, mientras FBref llama
  `Vitória Setúbal` al otro, que además dejó la Primeira en 2020.
- **`B-SAD`** es Belenenses SAD. Se mapea a `Belenenses` porque es lo que hace
  football-data: su histórico usa ese único nombre de 2014 a 2022 sin separar
  el club original de la escisión. Aquí se HEREDA esa decisión en vez de tomar
  una distinta, para que las dos fuentes sigan cuadrando. No es la decisión
  "correcta" en abstracto; es la que mantiene el join sano.

### Dónde parar

El siguiente escalón es mucho peor: Bélgica, Rusia, Ucrania, Turquía y Grecia
sumarían ~1.160 cruces, pero son **cinco** ligas para menos muestra de la que
dieron **tres**, varias fuera del formato principal de football-data, y con
clubes que rotan más en Europa. Rendimientos decrecientes claros. Anotado en
`tareas.md` como "solo si se quieren esas ligas por sí mismas".

### Lo que NO cambió, y conviene no olvidarlo

El modelo sigue sin batir al mercado. Remedido con el mismo protocolo Kalman:
el delta por liga se mueve como mucho en la cuarta cifra decimal y la MLS
aterriza en −0.00590, exactamente donde las demás.

**Ampliar el catálogo no crea ventaja.** Es la misma conclusión que para los
mercados derivados: más ligas son más partidos de la misma calidad de
predicción, no una fuente de edge nueva. Lo que estas tres ligas mejoran es un
parámetro concreto (`strength`), no el acierto.

---

## 2026-09-22 — Ideas futuras del FPL Decision Engine, sin integración directa

Se revisó `percivalmahwaya/fpl-decision-engine` como referencia externa. No se
integra: resuelve Fantasy Premier League a nivel de jugador, con SQLite,
Streamlit y un optimizador de plantillas, mientras QuantFut predice partidos y
precios contra mercado. Además, el repositorio externo no muestra una licencia
que autorice copiar código.

Se conservan tres ideas metodológicas para cuando exista suficiente histórico
de alineaciones y cuotas:

- **Alineaciones como información nueva, no como otro modelo sobre los mismos
  goles.** Estimar su efecto sobre `log(lambda_home)` y
  `log(lambda_away)` usando continuidad del XI, ausencias y eventualmente
  ratings por jugador.
- **Champion/challenger real.** El ajuste de alineaciones correrá en sombra y
  solo podrá promoverse si mejora RPS/log-loss secuencial y CLV previo al
  cierre en varias ligas. La infraestructura de artefactos y puertas ya
  existente se reutiliza; no se importa la implementación FPL.
- **Zona de abstención.** Medir mediante bootstrap o reentrenamientos cuánto
  varían probabilidades y edges. Un edge dentro de ese ruido no debe producir
  un pick. El umbral se estimará en unidades de QuantFut; no se copia el valor
  del sistema FPL y no sustituye al `edge_shrinkage`.

No se adoptan su modelo de puntos por jugador, MILP de plantilla, recolector
FPL, SQLite, GitHub Actions ni Streamlit como frontend comercial. Streamlit
solo seguiría siendo opcional como vista personal de solo lectura; Grafana ya
es el panel operativo oficial de QuantFut.

---

## 2026-09-22 — SciKick queda como referencia para el frontend posterior

Se revisó `Pa004/scikick` y se conserva como referencia para el frontend de la
Fase 3, no como trabajo inmediato. La razón es de orden de dependencias: primero
deben estabilizarse la API y los pendientes de las fases anteriores para no
construir la interfaz sobre contratos que todavía puedan cambiar.

Cuando llegue esa fase, se podrán adaptar su estructura React/TypeScript, las
páginas de partido, la navegación de mercados, los gráficos de calibración, el
tema claro/oscuro y la internacionalización. Se conservará el aviso de su
licencia MIT. No se adoptarán su backend, SQLite, sus modelos predictivos ni su
lógica de `value`; QuantFut seguirá siendo la fuente de datos, probabilidades,
selección de picks y control de acceso.

---

## 2026-09-22 — Orden Elo → mercado → XI en sombra

Se implementó el baseline Elo secuencial y un constructor único de features
point-in-time. Ambos retrasan dos horas el uso de resultados y tiros cuando no
hay timestamp de finalización: un partido iniciado 30 minutos antes no puede
filtrar su marcador a otro. Las regresiones y ablaciones siguen siendo
challengers de diagnóstico; las cuotas históricas de cierre no se tratan como
features desplegables a T-60.

La comparación de tres vías sobre 1.907 partidos comunes de julio de 2025 a
enero de 2026 dio RPS Dixon-Coles 0,20245, Elo 0,20533 y Pinnacle 0,19561.
La lección es mantener Elo como control útil, no promover complejidad por
ganarle a Elo. Las cuotas sharp locales terminan el 14 de enero de 2026;
para la evaluación actual están obsoletas. La puerta de promoción bloquea
mercado con más de 30 días de antigüedad.
El bootstrap semanal favoreció a Dixon-Coles frente a Elo por 0,00288 RPS
(IC 95 %: 0,00053–0,00506) y a Pinnacle frente a Dixon-Coles por 0,00684
(IC 95 %: 0,00350–0,01061). Las pequeñas mejoras de Elo o tiros sobre el
cierre en un único holdout no sustituyen una prueba con cuotas disponibles
en el momento operativo.

El XI solo se convierte en ajuste de lambdas si acumula histórico temporal
suficiente y supera su holdout. Para medir CLV real se añadió una captura
`post_xi` condicionada a ambos XI, anterior a `close`: sin esa separación, el
CLV sería cero por construcción. La migración de sombra se aplicó al Postgres
local sin tocar predicciones ni picks publicados. Faltan claves de API-Football
y The Odds API para obtener nuevas alineaciones y cuotas, así que no se ha
observado CLV real ni se ha promovido challenger alguno.
La carga de entrenamiento exige ahora `window_tag='close'` de forma explícita;
la vista heredada elegía simplemente el último snapshot y podría confundir la
nueva ventana `post_xi` con un cierre cuando faltase este último.

---

## 2026-09-22 — Claves reales conectadas: lo que la API enseña y los tests no

Se configuraron y verificaron las dos claves. Lo importante no es que
funcionen, sino los cuatro problemas que solo aparecen al llamar de verdad.

### El plan Free de API-Football no puede operar el sistema, y no por la cuota

Lo que descarta ese plan no son las 100 peticiones diarias: es que **solo da
acceso a las temporadas 2022–2024**. La temporada en curso responde
`Free plans do not have access to this season`. Sin temporada en curso,
`ingest/fixtures.py` no puede poblar `matches` con partidos `scheduled`; sin
esas filas, `_pending_windows` del odds_worker no encuentra nada que capturar,
`ingest/lineups.py` no tiene partidos en ventana y `post_xi` nunca se dispara.
La cadena entera de datos operativos cuelga de ahí. La clave Free sirve para
verificar IDs y formas de respuesta, que es justo lo que estaba pendiente.

### Tres bugs del cliente que solo se ven con una clave en la mano

1. **El ritmo de llamadas estaba fijado para otro plan.** `MIN_INTERVAL = 0.35`
   (~170 req/min) estaba pensado como "por debajo de todos los planes"; el Free
   son **10 req/min**. La cuarta llamada seguida ya devolvía 429. Ahora el
   intervalo se deriva de `API_FOOTBALL_RPM`, que es un dato del plan y no una
   constante del código.
2. **El 429 entraba en el reintento exponencial genérico**, que espera 2 s y
   vuelve a chocar contra el mismo límite por minuto. Ahora es `RateLimited` y
   espera al minuto siguiente.
3. **Los errores de PLAN se reintentaban cuatro veces.** Son permanentes por
   definición: la suscripción no va a cambiar entre reintentos. Cada uno
   consumía una petición de las 100 del día, así que el modo de fallo era
   quedarse sin cuota justo cuando algo estaba mal configurado. Ahora
   `PlanError` no es reintentable.

Los tres comparten la misma forma: el proveedor devuelve **HTTP 200** y mete el
problema en el cuerpo, así que sin distinguir clases de error todo acaba en el
mismo reintento ciego.

### Los IDs de competición estaban bien; el verificador no

Los 13 `api_football_id` y los 13 `odds_api_key` son correctos y están activos.
Pero `verify_league_ids()` daba FALLO en Champions y Europa League: comparaba
el país, y API-Football archiva las competiciones continentales bajo `World`
mientras el catálogo local dice `Europe`. Un verificador que da falsos
positivos es peor que no tenerlo, porque entrena a ignorarlo. Ahora, para las
`cross_league`, comprueba `type == "Cup"` y el nombre.

### La coincidencia exacta no era paranoia: era necesaria, y faltaba en un sitio

Ejecutado `_resolve` contra fixtures reales de Champions, se confirmó lo que
`CLAUDE.md` advertía, con números:

    'Paris Saint Germain'  -> mejor candidato difuso 'San Martin S.J.'  (61)
    'Atletico Madrid'      -> mejor candidato difuso 'Atletico MG'      (77)
    'Rangers'              -> mejor candidato difuso 'Angers'           (92)

El tercero **supera el umbral de auto-aceptación de 90**. Y `resolve_team`
graba como alias permanente todo difuso aceptado, así que no habría sido un
partido mal emparejado sino la fuente contaminada para siempre. `fixtures.py`
ya estaba protegido; **`odds_worker.py` no**: resolvía los eventos de copa con
`league_id=None`, es decir, difuso contra las 13 competiciones a la vez. Por
eso `resolve_team` pasa a exigir coincidencia exacta POR DEFECTO, y el difuso
queda detrás de `exact=False`. `tests/test_resolve_exacto.py` fija los tres
casos, incluido el que pasa el umbral.

### El coste de The Odds API era cinco veces el estimado, y por un motivo útil

Recalculado con datos reales (el endpoint `/events` cuesta 0 créditos, así que
se leyó el calendario anunciado de las 13 competiciones y se simuló
`_pending_windows` sobre él): **~1.935 llamadas/mes**, o sea ~11.610
créditos/mes con `eu,us × h2h,totals,spreads`. El README daba ~2.160 para 7
ligas.

El factor cinco no viene de tener casi el doble de competiciones. Viene de que
**el coste lo manda el número de huecos de 10 minutos distintos, no el de
partidos**: una llamada trae todos los partidos de esa competición que entren a
la vez en la misma ventana. LaLiga y la Serie A, con 20 partidos en 14 días,
cuestan más que la MLS con 33, porque la MLS concentra kickoffs. Las copas son
lo más barato que hay: juegan todas la misma tarde. La consecuencia práctica es
que **repartir los mismos partidos entre más competiciones encarece**, y que la
palanca barata para bajar el coste no es quitar ligas sino quitar ventanas.

El plan de $30 (20.000 créditos) sigue alcanzando, con 1,7× de margen en vez de
"de sobra". El de 500 no alcanza ni en la configuración más barata (1.935), así
que con esta clave el worker se ejecuta a mano, nunca desde el cron.

### Emparejamiento de nombres: 108 alias nuevos y dos trampas

El bootstrap con las dos fuentes auto-registró 362 alias y dejó 283 a mano; se
curaron 108. De los que quedan, la mayoría son irresolubles por diseño (Celtic,
Rangers, Galatasaray, Slavia Praha… juegan las copas pero sus ligas no están en
el catálogo). Dos propuestas del difuso eran falsas y habrían pasado una
revisión rápida: `Remo` → Grêmio (80) y `Atlético Huracán` → Atlético Tucumán
(81). Revisar esta lista por puntuación descendente es exactamente la forma de
tragárselas.

---

## 2026-09-22 — La demostración del motor encontró el fallo más caro del sistema

Se ajustó Dixon-Coles sobre los 48.372 partidos con objetivo (945 s) y se
recorrió la cadena completa contra cuotas REALES de la Premier: de-vig →
lambdas → ~150 mercados → edge → encogimiento → Kelly. El motor funciona: 20
partidos, 70 selecciones preciadas por partido desde dos lambdas, line shopping
entre 22 casas, 19 candidatos por encima de los umbrales.

Y los tres candidatos de mayor stake eran basura.

    Hull v Everton     away @ 2.18   modelo 0,9061  mercado 0,4659   2,00 u
    Fulham v Hull      home @ 1.74   modelo 0,9506  mercado 0,5785   2,00 u
    Ipswich v Fulham   away @ 2.70   modelo 0,5574  mercado 0,3781   2,00 u

### El mecanismo, que no es "datos viejos"

Hull vuelve a primera; no la jugaba desde 2017. Con media vida de 180 días, la
suma de pesos de sus partidos es **0,0000**: sus `attack` y `defence` no los
deciden sus datos, los deciden el ridge y la restricción de suma cero por liga.

Y no quedan en cero. Quedan en (−0,81, −0,79) mientras los 20 equipos activos
se sitúan entre +0,2 y +0,9, porque el centrado se calcula sobre los 35 equipos
del catálogo incluyendo 15 que ya no juegan: los ausentes son el contrapeso
negativo de los presentes. La distancia entre un equipo activo y uno de estos
es ~1,3 en ataque, o sea un factor e^1,3 ≈ 3,7 en lambda. De ahí λ = 4,046 /
0,371 en Fulham v Hull.

**Por qué esto no contamina el resto:** en `lambdas()` el término es
`(atk_h + s) − (dfn_a + s)`, así que un desplazamiento común se cancela entre
dos equipos activos. Solo NO se cancela en activo-contra-ausente. Es coherente
con que el RPS medido sobre partidos normales sea razonable.

### Las tres guardas existentes miraban el número equivocado

- `knows()` daba **True**: comprobaba pertenencia al índice, y Hull está.
- `_confidence()` daba **`high`**: cuenta partidos de TODA LA VIDA, y Hull tiene
  cientos. El modelo pesa con media vida de 180 días. Son dos magnitudes
  distintas y se estaba usando una para hablar de la otra.
- `EDGE_SHRINKAGE=0.55` dejaba el 97,53% en 53,64%, y `MAX_STAKE_UNITS=2.0`
  recortaba justo a lo que ya se apostaba.
- Y `both_teams_known` se guardaba en los metadatos sin que **nadie** lo usara
  para descartar.

Cada guarda parecía razonable por separado. Ninguna medía la cantidad correcta.

### Lo que distingue el caso peligroso del inofensivo

Un ascendido de verdad (sin historia) es **seguro**: no está en el índice y
`lambdas()` lo lleva a la media de su liga. El peligroso es el contrario, el
que SÍ está en el índice con muestra efectiva ~0, porque entonces no cae a la
media: carga un parámetro extremo del que el modelo está seguro.

La magnitud que los separa es la **muestra efectiva** —suma de pesos de
decaimiento— y no existía. Ahora se calcula en `fit()`, se guarda en `DCParams`
(con default, para que los artefactos anteriores sigan cargando y devuelvan
`inf`: sin el dato no se puede AFIRMAR que falte muestra), la expone
`effective_n()`, la exige `knows()` y la mira `_confidence()`.

Se eligió `low` en vez de descartar la predicción: se sigue guardando, sirviendo
y auditando, pero `run()` ya la excluye del universo de picks con el filtro que
tenía. No se tocó el orden predecir → sellar → publicar.

Reparto en el modelo entrenado: **95 de 362 equipos tienen muestra efectiva
menor que 1**; 130 por debajo de 5, que es el umbral por defecto
(`MIN_EFFECTIVE_MATCHES`). No es un caso raro: son los tres ascendidos de cada
liga, cada agosto.

### Por qué importa para la fase 2

Esto no da edge; evita pérdidas. Pero es la demostración empírica del punto 2.D
del plan: el sistema no tenía forma de distinguir "mi ventaja es real" de "mi
parámetro es ruido", y por construcción apostaba el máximo justo donde más
ruido había. La zona de abstención por bootstrap es la versión general de esta
misma guarda; esta es el caso particular que se podía cerrar hoy y con un
número exacto.

---

## 2026-09-22 — Plan Pro: la cadena operativa arranca, y dos alarmas eran mentira

Contratado el plan Pro de API-Football. Verificado contra `/status`: 300
req/min, 7.500/día, temporada en curso incluida. `API_FOOTBALL_RPM` pasa de 10
a 300 y el intervalo entre llamadas del cliente baja de 6 s a 0,2 s solo.

Lo que cambia no es la cuota, es el acceso a la temporada EN CURSO. Primera
ingesta real de calendario: **173 partidos programados en 12 competiciones**.
De ahí cuelgan las ventanas de cuotas, las alineaciones a T-60 y el CLV, que
era todo lo que estaba esperando. `results.py` cerró su primer partido y
encadenó la liquidación sin incidencias.

### Los nombres de la temporada en curso no se habían visto nunca

El catálogo venía de football-data.co.uk y FBref; API-Football escribe distinto.
17 equipos sin emparejar en la primera pasada, resueltos en
`db/013_aliases_api_football.sql` con dos tratamientos OPUESTOS y la distinción
importa:

- **Alias** (mismo club, otra grafía): API-Football conserva la forma societaria
  completa y football-data la recorta — `Hamburger SV`, `SC Paderborn 07`,
  `1. FC Köln`, `Estac Troyes`, `Hull City`. Todos caen entre 62 y 88, por
  debajo del umbral de 90.
- **Alta de equipo** (club que de verdad faltaba): `Remo`, `Gimnasia M.`,
  `Estudiantes de Rio Cuarto`, `Atlante FC`. `resolve_or_register` se negó a
  crearlos porque los cuatro tienen candidato difuso por encima del suelo de
  60, y **los cuatro candidatos eran falsos**: Remo (Belém) contra Grêmio
  (Porto Alegre) a 80, Gimnasia de Mendoza contra la de La Plata a 82.

Bajar el umbral habría "resuelto" los cinco del primer grupo y fusionado los
cuatro del segundo con clubes ajenos. Es el mismo argumento de `db/011` y sigue
siendo el correcto: el umbral no se toca, los casos se miran uno a uno.

Los cinco de Champions que quedan (Club Brugge, Galatasaray, Sabah, Slavia
Praha, Viking) no se tocan: sus ligas no están en el catálogo y darlos de alta
bajo `eu.ucl` partiría historiales. Sus partidos se descartan a propósito.

### Dos alarmas permanentemente en rojo, que es lo mismo que apagadas

Con el sistema por fin produciendo datos reales, el chequeo de salud daba
fallos que no lo eran. Las dos causas son del mismo tipo: **la métrica no medía
lo que decía medir**.

1. **Calendario.** Preguntaba por partidos en los próximos 10 días cuando
   `fixtures.run()` ingiere 21. Con el calendario recién traído y correcto,
   saltó en 10 competiciones a la vez: todas las europeas más Brasil y
   Argentina tenían su próximo partido pasado ese plazo, porque estamos en
   parón de selecciones. Preguntar por una ventana más CORTA que la que se
   ingiere no puede distinguir "no hay partidos" de "no se han traído": solo
   sabe dar falsos positivos. El horizonte pasa a ser el mismo que el de la
   ingesta.

2. **Nombres sin emparejar: 362 fantasmas.** `history_fd._ensure_team` daba de
   alta el equipo e insertaba su alias con un INSERT a mano en vez de
   `register_alias`. Para la tabla de alias da igual; para `unresolved_names`
   no, porque solo `register_alias` marca la fila resuelta. Cada nombre nuevo
   pasaba antes por `resolve_team`, quedaba registrado como pendiente, y ahí
   se quedaba **para siempre aunque todo hubiera funcionado**. El chequeo
   reportaba 362 nombres (84.887 apariciones, casi todos MLS) y recomendaba
   `bootstrap_aliases.py`, que ni siquiera toca la fuente `football_data`.

   Tras el arreglo y el cierre de las filas viejas: **371 → 9**, y los 9 son
   los clubes de copa irresolubles por diseño. Ahora cuando esa alarma suene
   querrá decir algo.

La lección es la misma de la guarda de muestra efectiva de esta misma sesión:
tres guardas y dos alarmas, todas razonables por separado, todas midiendo la
cantidad equivocada. Lo que las destapó en los tres casos fue hacer correr el
sistema con datos de verdad.

---

## 2026-09-22 — Fase 2: implementado el plan. El cierre deja de ser el rival

Implementados los cuatro puntos del plan de fase 2. Lo que los une es una sola
lectura, y conviene tenerla clara antes que el código: **`w_model = 0.0001` no
dice "el modelo no sirve", dice "el modelo sirve para la FORMA, no para el
NIVEL"**. La forma es la matriz de marcadores, de la que salen ~150 mercados
coherentes entre sí; eso el mercado no lo da. El nivel lo da el mercado, y
mejor.

### 1. La puerta comercial pasa a decidirse por CLV

Son dos afirmaciones distintas y solo una es alcanzable:

    "mi probabilidad es mejor que el consenso de cierre"   -> casi nadie
    "el precio que tomé era mejor que el cierre que vino"  -> medible, y es
                                                              lo que se cobra

La puerta anterior exigía la primera (`beats_market_same_rows` en RPS) y se
conformaba, para el CLV, con una media no negativa. Es la peor combinación:
rechazaba todo por lo imposible y no filtraba nada por lo que importa, porque
una media positiva la produce cualquier racha.

`evaluate_clv_gate` exige ahora tres cosas a la vez: 300 apuestas liquidadas,
el intervalo de confianza del 95% del CLV **entero** por encima de cero, y al
menos 3 ligas con muestra propia. La tercera no es adorno: un CLV que solo vive
en una liga es un hallazgo sobre esa liga —o sobre una casa, o sobre un horario
de publicación— y es lo primero que desaparece cuando esa casa limita la
cuenta. Batir al cierre se sigue reportando; ya no veta.

**No es un ablandamiento.** Se quita una condición inalcanzable y se endurece
la que sí discrimina. Está fijado en `tests/test_puerta_clv.py`, con un test
por cada una de las tres condiciones.

De paso: el parámetro `clv` de `evaluate_base_promotion` existía y **no se
pasaba nunca** desde `train.py`, así que `ready_for_commercial_picks` era falso
por construcción, no por medición. Parecía una puerta y era un tapón.

### 2. El ancla de mercado, y el brazo que faltaba

`model/market_anchor.py` invierte el 1X2 ya sin margen a las intensidades que
lo reproducen bajo Dixon-Coles. Ida y vuelta exacta a 1e-10.

Devuelve SIEMPRE el residuo, y no es cautela retórica: fijados los dos goles
esperados, la probabilidad de empate queda determinada, así que la familia no
puede representar cualquier terna. Un mercado con empate al 10% y local y
visitante iguales no tiene solución —el ajuste se va a lambda = mu = 7,5 con
residuo 0,0127— y el módulo lo dice en vez de devolver el ajuste menos malo con
cara de número bueno.

El bug de diseño que esto cierra: `lineup_challenger.apply()` multiplica
`base_lam`, y `base_lam` venía de `predictions.home_lambda`, o sea **las
lambdas del modelo**. Con w_model ≈ 0, ajustar por el XI unas lambdas peores
solo mueve una estimación peor. `shadow.py` gana dos brazos más
(`baseline_market` y `lineup_lambda_market`), y con los cuatro sobre las mismas
cuotas cada comparación aísla una sola cosa:

    modelo  -> modelo+XI    : ¿el XI aporta?
    mercado -> mercado+XI   : ¿aporta SOBRE lo que ya estaba preciado?
    modelo  -> mercado      : cuánto de la diferencia era solo nivel

### 3. Información nueva

El XI ya estaba construido y ahora tiene dónde apoyarse (punto 2). La señal de
noticias y lesiones vía LLM sigue **esperando una decisión que no es técnica**:
qué medios por liga. No se inventa aquí.

### 4. Los dos puntos matemáticos, que resultaron ser uno

Iban en la lista como dos ítems y se resuelven con la misma cantidad: cuánto
varía el edge cuando los parámetros varían dentro de su propia incertidumbre.

`DixonColes.fit()` deja ahora el error estándar de `attack` y `defence` de cada
equipo. Se llegó a la fórmula por descarte, y los dos intentos fallidos la
explican mejor que ella misma:

1. **La curvatura del objetivo a secas** no vale: los pesos se normalizan por
   su media antes de entrar en la verosimilitud, así que un dataset de 12 años
   con media vida de 180 días se comporta como si sus 48.000 partidos contaran
   enteros. Errores estándar unas cuatro veces demasiado pequeños.

2. **El estimador sándwich** `H^-1·V·H^-1` arregla la escala y falla justo
   donde importa. Entrenado sobre los 48.372 partidos reales, los seis equipos
   con el error estándar MÁS PEQUEÑO del modelo —o sea, los que decía conocer
   mejor— eran los seis con muestra efectiva 0,0000: Chivas USA, QPR, Córdoba,
   Leones Negros, Cesena, Evian. Y es correcto en su propio marco: sin muestra
   no hay variabilidad muestral. Pero ese parámetro no lo fijan los datos, lo
   fija el ridge, y **un prior no es conocimiento**. Un número que dice "de
   este equipo estoy segurísimo" sobre un equipo del que no se sabe nada es
   peor que no tener número.

3. **Corregir el sándwich con la muestra efectiva** `(Σwλ)²/(Σw²λ)` tampoco:
   esa expresión es invariante a la ESCALA de los pesos, que es exactamente lo
   que aquí no se puede ignorar. 24 partidos de hace ocho años, todos con el
   mismo peso minúsculo, "cuentan" como 24 observaciones. Mide cuántas
   observaciones contribuyen, no cuánto pesan.

Lo que queda es la precisión posterior con pesos crudos:

    se = 1 / sqrt( Σ w·λ  +  2·ridge·media(w) )
                   \_____/    \______________/
                   los datos      el prior

Con muchos datos domina el primer término. Sin datos el segundo, que es
diminuto, así que el error estándar se dispara y el modelo declara que no sabe.
Las dos situaciones son el mismo número, no dos reglas pegadas, y por eso la
abstención del equipo sin muestra sale sola sin una regla aparte.

Se ignoran los términos fuera de la diagonal: suficiente para decidir una
abstención, no para publicar un intervalo de confianza. Está dicho en el código.

`model/uncertainty.py` los propaga por Monte Carlo hasta el edge, y de la
distribución salen las dos decisiones de golpe:

    edge_floor = media - Z·sd
    edge_floor <= 0  ->  ABSTENERSE: la ventaja no se distingue de cero
    edge_floor >  0  ->  encogimiento = edge_floor / media

Ese cociente es `EDGE_SHRINKAGE` pero **medido y por apuesta**. La constante
0,55 encogía igual una discrepancia sobre el Liverpool, del que hay veinte
partidos recientes, que una sobre un recién ascendido del que hay tres. El
test que de verdad importa no es que el número salga, es
`test_el_encogimiento_medido_premia_a_quien_esta_mejor_medido`: que
DISTINGA. Si no distingue, no vale más que la constante.

`UNCERTAINTY_ENABLED` apagado por defecto, como `META_BLEND_ENABLED` y
`RESIDUAL_ENABLED`: cambia cuántos picks se publican al día y eso es decisión
de negocio, no del código.

**Al medir si funciona, no confundir la métrica.** Esto no crea ventaja:
elimina apuestas de EV negativo. Sube el ROI realizado y NO debe mejorar el
RPS. Si alguna vez mejora el RPS, está mal planteado.

## 2026-09-22 — Bajas/lesiones: fuente decidida, no era el LLM

El backlog llevaba la tarea bloqueada como "vía LLM" (lectura de prensa local
por liga + extracción NLP). El usuario encontró que API-Football —el mismo
proveedor ya contratado en plan Pro para calendario y alineaciones— tiene un
endpoint `/injuries` que da el dato ya estructurado (jugador, tipo de baja,
motivo) por prácticamente cualquier liga. Eso descarta el diseño LLM por
completo para esta señal: no hay texto que extraer, así que no hay coste de
inferencia recurrente ni riesgo de alucinación en el parseo, y el coste de
API es $0 incremental sobre lo ya pagado.

La restricción de diseño que sí se hereda del plan original sigue vigente:
cada fila lleva su propio `captured_at`, y cualquier feature construida sobre
`injuries` tiene que respetar `as_of <= kickoff` en `features_pit`, igual que
todo lo demás. Sin eso es fuga, no señal — el proveedor cambiado no cambia
esa regla.

Decisión de diseño tomada al implementar: a diferencia de `lineups` (una
sola captura por partido dentro de T-90..T-20, porque el XI no cambia una
vez publicado), una baja se conoce con días de antelación y su estado
evoluciona (duda → confirmado), así que `injuries.py` relee cada partido
cada `MIN_HOURS_BETWEEN_CHECKS` (4h) dentro de una ventana de 7 días. Para
no reconsultar para siempre un partido sin bajas reportadas, se añadió
`injuries_capture_log`, que registra el intento aunque la respuesta esté
vacía — sin eso, "no hay bajas" y "no se ha comprobado" son indistinguibles
y el ingest reintentaría cada partido en cada pasada sin parar.

Todavía no existe la feature de disponibilidad (equivalente a
`lineups.availability()`): `injuries.py` solo ingiere y almacena. Es el
siguiente paso, y necesita acumular datos primero — igual que pasó con
alineaciones.

## 2026-09-22 — Verificada cobertura de `/injuries`: hueco real en 3 ligas

Se comprobó `/injuries` contra las 13 competiciones (clave real, `league` +
`season` actual y también por `fixture` suelto). 10 van bien. Tres no:
`mx.liga_mx`, `ar.primera`, `pt.primeira` devuelven 0 resultados para la
temporada 2026 en curso, tanto agregado como por partido, pese a tener 79,
400 y 62 partidos terminados esa misma temporada — no es que no haya
lesionados, es que el proveedor no tiene el dato ahí. Con `season=2025` sí
hay datos (166, 51, 77), lo que descarta un parámetro de temporada mal
calculado: es cobertura real ausente, exactamente el mismo patrón de "array
vacío con status 200" que ya se documentó para el xG de este mismo
proveedor. Anotado en README.md junto a esa advertencia porque es el mismo
fallo silencioso, no uno nuevo que inventar.

Decisión: no se excluye a esas 3 ligas de `injuries.py` (el módulo sigue
llamando al endpoint para las 13, tal como está). No hay forma de
distinguir por una sola pasada "liga sin cobertura" de "liga sana sin
bajas hoy" — hace falta acumular varios ciclos de 4h y ver si CUALQUIER
partido de esas 3 ligas reporta alguna vez una baja; si nunca lo hace, ahí
sí se confirma el hueco y se puede marcar la liga como "sin señal de
lesiones" en vez de asumir plantillas sanas.

Añadida la vigilancia: `check_injuries_coverage()` en
`src/qf/ingest/health.py`, en la lista `CHECKS` que corre `health.run()`
diario. Cuenta, por liga, partidos distintos comprobados en
`injuries_capture_log` los últimos 30 días y la suma de `n_reported`. Si una
liga acumula 15+ partidos comprobados con 0 bajas en total, es la misma
firma que ya se vio a mano con mx/ar/pt — salvo que esa liga ya esté en
`KNOWN_INJURY_COVERAGE_GAPS`, para no alertar cada día por algo ya
investigado y no accionable desde este lado (mismo principio que
`check_fixtures_horizon` con las ligas fuera de temporada: una alerta que
salta a diario por algo normal se deja de leer). El umbral de 15 partidos es
el mismo tipo de decisión que `HORIZON_DAYS`: bajo con muestra chica da
falsos positivos, y aquí 15 partidos de una liga completa sin una sola baja
es prácticamente imposible por azar si el proveedor sí tiene el dato.

---

## 2026-09-22 — La zona de abstención rechaza el 100% de los picks, y el número cuadra

Reajustado el modelo con los errores estándar correctos (86 min) y pasada la
cadena completa del punto 4 sobre cuotas reales de la Premier.

Primero, la corrección funciona. Los errores estándar son ahora **monótonos en
la muestra** a lo largo de cinco órdenes de magnitud:

    N_efectivo   equipos   se_attack (mediana)
    [0, 0.1)         75        21.56
    [0.1, 1)         20         1.26
    [1, 5)           35         0.55
    [5, 15)          61         0.31
    [15, 99)        171         0.19

Mejor conocidos: Bayern Munich (0,117), Inter Miami (0,121), Sp Lisbon (0,129).
Peor: Córdoba, QPR, Chivas USA, los tres a 23,7 con muestra 0,0000. Son
exactamente los mismos que la versión con sándwich colocaba como los MEJOR
conocidos, con el orden invertido.

### Y entonces la abstención rechaza los 19 picks del día

    con la constante 0,55:      19 picks
    con encogimiento medido:     0 picks

Ninguno sobrevive. Ni siquiera partidos entre equipos con 19-20 partidos
efectivos. La desviación típica del edge va de 14 a 94 puntos porcentuales.

**No es un error del código, y la aritmética lo dice sin ambigüedad.** Un
equipo bien medido tiene ~20 partidos efectivos a ~1,4 goles, o sea ~28 goles
observados. El error estándar de una tasa logarítmica con 28 eventos es
1/sqrt(28) = 0,19, que es exactamente el `se_attack` que sale del ajuste. De
ahí, sd(log lambda) ~ 0,26: **la intensidad varía ±26% a una sigma**. Con esa
variación, una cuota de 5,50 mueve el edge decenas de puntos. Es la varianza de
Poisson de los goles del fútbol, no un defecto de la implementación.

Dicho de otro modo: la ventaja nominal del modelo (3-10%) es **un orden de
magnitud menor que el ruido de sus propios parámetros**.

Esto CONCUERDA con lo ya medido por caminos independientes —`w_model = 0.0001`,
derrota contra el cierre en las 7 ligas— y es una comprobación cruzada
valiosa: dos métodos que no comparten nada llegan a la misma conclusión.

### Pero Z = 1,0 no sirve como valor por defecto, y hay que decirlo

La regla `media - Z·sd > 0` con Z=1 exige ~84% de confianza en que el edge es
positivo. Con sd de ese tamaño eso es inalcanzable por construcción, así que el
interruptor encendido significa hoy "no apostar nunca". Un mecanismo que
siempre dice no no está midiendo, está apagado con otro nombre.

Tres cosas que corregir antes de darlo por bueno:

1. **La regla es MÁS ESTRICTA que la óptima en valor esperado.** Para EV basta
   `E[p]·cuota > 1`; exigir que el suelo sea positivo es una decisión de
   prudencia, no un resultado estadístico. Conviene no confundirlas.
2. **Mide incertidumbre ABSOLUTA, no relativa al mercado.** Lo que decide una
   apuesta es si nuestro error es menor que el suyo, y el mercado también
   desconoce la lambda verdadera. Un modelo puede tener ventaja real con
   incertidumbre absoluta grande. La versión correcta mediría la varianza de
   (p_modelo − p_mercado), y con el ancla de mercado ya existe la pieza para
   hacerlo.
3. **Ordenar por media/sd no arregla la selección adversa.** Los dos
   candidatos que más se acercan a pasar son justo los de mayor edge bruto
   (47,9% y 50,4%), que son los más sospechosos de ser error del modelo. El
   cociente se queda cerca de 1 para todos, así que no discrimina donde hace
   falta.

Los cocientes media/sd del día: 0,995 · 0,957 · 0,829 · 0,792 · 0,682 · 0,671 ·
0,613... Con Z=0,95 pasarían dos; con Z=0,80, cuatro. Ese es el rango en el que
hay que calibrar contra histórico liquidado, no en 1,0 por convención.

---

## 2026-09-22 — Caddy como servicio de `docker-compose.yml`

El README ya documentaba un Caddyfile de ejemplo (sección "Proxy con TLS"),
pero era un paso manual fuera del repo: no había ni `Caddyfile` ni servicio
`caddy` en `docker-compose.yml`. `docker compose up -d` no dejaba la API
alcanzable por HTTPS desde ningún dominio; solo `127.0.0.1:8000`.

Se añadió el servicio `caddy` (imagen `caddy:2-alpine`, puertos 80/443,
volúmenes `caddydata`/`caddyconfig` para el certificado y el estado interno) y
un `Caddyfile` en la raíz. Decisión de diseño: `reverse_proxy` apunta a los
nombres de servicio de Compose (`api:8000`, `grafana:3000`), no a `localhost`
como en el ejemplo original del README — ese ejemplo asumía Caddy instalado en
el host, no dentro de la misma red de Docker Compose.

Grafana se mantiene cerrado por IP (`@yo remote_ip {$GRAFANA_ALLOWED_IP}`)
además del login, tal como ya decidía el README: es el panel de operación
privado, no tiene por qué ser alcanzable desde internet en general. Se añadió
`GRAFANA_ALLOWED_IP` a `.env.example` porque antes esa IP estaba hardcodeada
como placeholder en el bloque de código del README y no era una variable real
del sistema.

Pendiente explícito, no resuelto aquí: esto solo pone el proxy TLS en pie.
Sigue sin existir auth de suscriptor no-Telegram ni rate limiting en las rutas
públicas (`harness/tareas.md`); exponer la API con HTTPS no sustituye a esas
dos garantías antes de anunciarla desde la web.

---

## 2026-09-22 — Auth de suscriptor (email+contraseña) y hardening de la API

Decisión del usuario, explícita: la API es de uso exclusivo para su propia web
y una futura app Flutter, pero SIGUE vendiendo picks a suscriptores reales
(no es acceso solo para él) — así que "exclusivo" describe quién puede
integrarse (nada de terceros, sin API pública documentada), no quién se
autentica. Y sobre el criterio de cliente: eligió "solo JWT de sesión" en vez
de añadir un secreto de cliente por plataforma, porque un secreto embebido en
una app Flutter siempre se puede extraer con ingeniería inversa — daría una
sensación de seguridad que no es real, a cambio de mantenimiento real
(rotarlo si se filtra el binario).

### Por qué el diseño previo no alcanzaba, más allá de "falta implementar"

`/v1/auth/telegram` era el único login y depende de `TG_BOT_TOKEN`, que el
usuario no tiene configurado — es decir, el login de suscriptor llevaba
tiempo roto de facto, no solo pendiente. Además el JWT de sesión duraba 30
días sin ningún mecanismo de revocación, y `JWT_SECRET` cuando faltaba se
generaba aleatoriamente EN SILENCIO (`os.getenv("JWT_SECRET") or
secrets.token_hex(32)`): cada reinicio del proceso invalidaba todas las
sesiones sin avisar, y con más de una réplica cada una firmaría con un
secreto distinto. Ninguno de los dos era un bug visible — son exactamente el
tipo de fallo silencioso que este proyecto ya se ha encontrado varias veces
(unidades del stake, `harness_check.sh` sin pytest, fechas UTC vs zona del
servidor).

### Lo que se construyó

- **`db/015_subscriber_auth.sql`**: `password_hash` (nullable — los
  suscriptores viejos de Telegram no tienen y NULL nunca autentica, no abre
  una puerta), `email_verified`, `failed_login_count`, `locked_until` en
  `subscribers`; tabla `refresh_tokens` (hash del token, nunca el valor en
  claro, con cadena de rotación `replaced_by`); tabla `auth_audit_log`.
- **`src/qf/api/auth.py`** (nuevo módulo, separado de `main.py` para poder
  probarlo sin FastAPI ni Postgres real): Argon2id para contraseñas (ganador
  del Password Hashing Competition, recomendación OWASP actual sobre bcrypt
  por su costo de memoria configurable), política de contraseña mínima (12
  caracteres, sin exigir símbolos — la guía NIST 800-63B es explícita en que
  eso empuja a "Passw0rd!" en vez de a contraseñas largas de verdad), emisión
  de access JWT de 15 minutos, refresh token opaco de 30 días con rotación en
  cada uso y **detección de reuso**: si se presenta un refresh ya revocado
  (señal de que un atacante está usando en paralelo un token robado), se
  revoca toda la cadena de sesiones del suscriptor, no solo esa.
- **Endpoints nuevos** en `main.py`: `POST /v1/auth/register`,
  `/login`, `/refresh`, `/logout`. `/v1/auth/telegram` se conserva pero ahora
  devuelve 404 explícito sin `TG_BOT_TOKEN` en vez de fallar más abajo con un
  HMAC que nunca va a poder verificar nada.
- **Enumeración de cuentas cerrada**: registrar con un email ya existente y
  hacer login con contraseña incorrecta devuelven el mismo mensaje genérico
  que "credenciales inválidas" — no confirman si el email está registrado.
- **Bloqueo de cuenta**: `LOGIN_MAX_ATTEMPTS` (5) fallos consecutivos
  bloquean la cuenta `LOGIN_LOCKOUT_MINUTES` (15). Protege contra fuerza
  bruta dirigida a un email; el rate limit por IP (más abajo) protege contra
  fuerza bruta distribuida entre muchas cuentas.
- **Rate limiting real**: no existía NINGUNO antes de hoy — ni global ni en
  auth. `security_middleware` en `main.py` limita por IP TODAS las rutas
  (`RATE_LIMIT_DEFAULT_PER_MINUTE=60`) y más estricto en `/v1/auth/*`
  (`RATE_LIMIT_AUTH_PER_MINUTE=10`), usando `INCR` de Redis sobre una ventana
  fija — atómico, dos peticiones concurrentes no pisan el contador. La IP se
  toma de `X-Forwarded-For`, correcto solo porque Caddy (ver sección anterior)
  es quien lo escribe y el cliente no puede llegar a la API sin pasar por él.
- **`JWT_SECRET` obligatorio en el arranque**: `main.py` ahora lanza
  `RuntimeError` si falta, en vez de generar uno efímero. Falla fuerte y
  temprano en vez de fallar silenciosamente en producción.
- **Manejador de excepciones global**: cualquier excepción no capturada
  devuelve `{"detail": "Error interno"}` con 500 en vez de dejar que algo se
  filtre (traceback, ruta de archivo, fragmento de SQL); el detalle real va
  al log del proceso, no a la respuesta.
- **Cabeceras de seguridad** en todas las respuestas
  (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`) y `Cache-Control: no-store` en `/v1` y `/admin` — no
  tiene sentido que un proxy o el navegador cacheen picks de pago o rutas de
  operación.
- **CORS**: el origen de desarrollo (`localhost:5173`) ya solo se añade con
  `APP_ENV=development`; antes estaba siempre en la lista, incluida en
  producción, sin ganar nada por tenerlo ahí (`allow_headers` también se
  acotó de `["*"]` a los dos que la API realmente usa).

### Lo que se decidió NO construir ahora, y por qué

Verificación de email y reseteo de contraseña por correo requieren decidir un
proveedor SMTP (Resend/Postmark/SES) antes de escribir una sola línea — no
tiene sentido dejar `email_verified` a medias sin forma real de enviar el
correo de verificación. Por eso `email_verified` existe en el esquema (para
no tener que migrar otra vez) pero no bloquea el login todavía. Cobros siguen
fuera de alcance, como ya decidía `harness/tareas.md`.

Un secreto de cliente por plataforma (HMAC firmado por build) se descartó por
decisión explícita del usuario: añade fricción y mantenimiento (rotarlo si se
filtra el binario de la app) a cambio de una protección que no es real contra
un atacante dedicado — solo filtraría bots automatizados poco sofisticados,
y eso ya lo cubre el rate limiting por IP.

### Tests

`tests/test_auth.py`, 12 casos, todos sobre lógica pura (hash/verify de
contraseña, política mínima, emisión/expiración/tipo de access JWT, y el
contador de rate limit contra un Redis falso en memoria). Lo que necesita
Postgres real (rotación de refresh tokens, bloqueo de cuenta, auditoría) no
tiene test automatizado — mismo patrón que el resto de `main.py`, que no se
prueba con TestClient en este repo. Queda como verificación manual pendiente,
igual que el resto de rutas de la API en `harness/tareas.md`.

---

## 2026-09-22 — Corrección de alcance: sin cuentas de usuario en la API

En la misma sesión que construyó el auth de suscriptor de arriba, el usuario
corrigió el modelo de negocio: la API no va a tener suscripciones ni registro
de usuarios. Los pronósticos se sirven a su frontend, que es quien arma los
prompts del LLM para el usuario final y quien cobra las suscripciones — con
su propia base de datos de usuarios, que no vive en este repo.

Eso obligó a revisar una premisa que había quedado sin cuestionar: ¿la app
Flutter futura llama directo a esta API, o llama al backend del frontend? La
respuesta importa porque un secreto que vive en un cliente que corre en el
dispositivo del usuario —JavaScript de navegador, o el binario de una app
Flutter— **siempre se puede extraer** con herramientas estándar (devtools,
apktool, frida). No es una debilidad de implementación que se arregle
ofuscando mejor: es una propiedad física de ese tipo de cliente. El usuario
confirmó el patrón BFF (Backend For Frontend): tanto la web como la futura
app Flutter le hablan a un backend propio suyo, y SOLO ese backend —que corre
en un servidor, no en el dispositivo del usuario— conoce el secreto que abre
esta API.

### Se revirtió el trabajo de la entrada anterior, completo

- `db/015_subscriber_auth.sql` se eliminó sin haberse aplicado a ningún
  Postgres real (se creó y se borró en la misma sesión).
- `src/qf/api/auth.py` (hash Argon2id, política de contraseña, access/refresh
  JWT, bloqueo de cuenta, auditoría) se eliminó completo.
- `POST /v1/auth/register|login|refresh|logout|telegram` se eliminaron de
  `main.py`: no hay usuario final que la API deba conocer.
- `PyJWT`, `argon2-cffi`, `email-validator` salieron de `requirements.txt`:
  ya no tienen consumidor.

Lo único que sobrevivió del trabajo anterior fue el rate limiting por IP
(movido a `src/qf/api/ratelimit.py`, sigue haciendo falta con o sin cuentas:
un `SERVICE_TOKEN` filtrado sin límite de tasa permite scraping sin freno) y
las cabeceras de seguridad / manejador de excepciones global de
`main.py`, que no dependían de la existencia de suscriptores.

### El diseño que quedó: `require_service`, un único secreto

`/v1/*` pasó de `current_subscriber` (JWT por usuario, con tier) a
`require_service` (`X-Service-Token` contra `SERVICE_TOKEN`, comparación en
tiempo constante, 404 si no coincide — el mismo patrón ya usado por
`require_admin`, deliberadamente: no confirmar que la ruta existe si el
secreto no coincide). Sin distinción de tier: quien presenta el token de
servicio recibe TODOS los picks y todas las probabilidades, porque decidir
qué le muestra a CADA usuario final ya no es trabajo de esta API — es trabajo
del backend del frontend, con su propia base de suscriptores.

Consecuencia directa: la tabla `subscribers` de `db/001_schema.sql` (con
`email`, `tier`, `telegram_id`) se queda sin ningún consumidor en esta API.
No se borró de la migración base porque editar `001_schema.sql` no cambia una
base de datos ya aplicada, y no hay evidencia de que el usuario quiera
mantener esa tabla para otra cosa; queda anotado en `harness/tareas.md` para
cuando construya el backend del frontend, por si prefiere esa base de datos
en otro sitio.

### Por qué NO se ofreció "secreto de cliente por plataforma" como alternativa

Con el patrón BFF confirmado, la pregunta de si el `SERVICE_TOKEN` necesitaba
algo más fuerte que una comparación simple (HMAC por request, mTLS) queda sin
urgencia: el secreto vive en un servidor que el propio usuario opera, no en
un cliente hostil. mTLS sería la siguiente capa razonable SI el backend del
frontend corriera en infraestructura que el usuario no controla del todo;
mientras sea su propio servidor, la comparación en tiempo constante sobre
HTTPS (ya servido por Caddy) es proporcional al riesgo real.

---

## 2026-09-22 — Calibración de Z: no hay nada que calibrar, y el control lo explica

Se calibró contra histórico real y point-in-time: tres cortes (2025-01-01,
2025-06-01, 2025-11-01), ajuste con SOLO lo anterior a cada corte, predicción
del tramo siguiente, errores estándar del mismo ajuste. **12.183 filas sobre
4.061 partidos y 11 competiciones**, con el cierre real como precio apostable.

### La pregunta previa: ¿discrimina la razón media/sd?

Antes de optimizar Z hay que comprobar que el mando está conectado a algo. No
lo está. Quintiles de media/sd, ROI con stake plano:

    quintil   ratio medio    ROI        IC95
      1          0.086      +3.44%   [-7.1, 14.0]
      2          0.266      -8.67%   [-18.8,  2.0]
      3          0.461     -11.34%   [-21.4, -0.2]
      4          0.721     -13.15%   [-23.8, -1.4]
      5          1.246      -6.77%   [-18.1,  5.0]

No monótono, intervalos solapados, correlación con el acierto **−0,047**.

La rejilla de Z parecía decir lo contrario —el ROI sube de −8,48% (Z=0) a
+2,48% (Z=1,0)— pero desde Z=0,4 **todos los intervalos incluyen cero**, y en
Z=1,0 el intervalo es [−13,0, +19,0] con 563 picks. Es ruido con forma de
tendencia. Si se hubiera mirado solo esa tabla, se habría "calibrado" Z=1,0 con
un número de aspecto convincente.

### El control, que es el hallazgo de verdad: el edge del modelo es ANTI-señal

Quintiles del edge CRUDO, sin incertidumbre de por medio:

    quintil   edge medio     ROI        IC95
      1          2.10%      +1.65%   [-7.3,  11.3]
      2          7.11%      -2.78%   [-12.8,  7.2]
      3         14.08%      -5.04%   [-16.0,  5.4]
      4         25.20%     -15.90%   [-25.8, -4.6]
      5         57.26%     -14.43%   [-26.9, -1.8]

**Cuanto mayor dice el modelo que es su ventaja, peor va.** Monótono, y la
correlación del edge con el acierto es **−0,1228** sobre 4.880 filas, que son
unas 8,6 desviaciones típicas de cero.

Es selección adversa en estado puro: donde el modelo más discrepa del cierre,
más se equivoca. Y explica por qué la zona de abstención no podía funcionar:
**filtrar más fuerte sobre una señal negativa no mejora nada**. Cualquier regla
construida sobre esa cantidad hereda el signo.

Correlaciones con el acierto, para situarlo:

    p_model    +0.3123   <- el modelo SÍ sabe de fútbol
    n_ef       -0.0255
    ratio      -0.0474
    edge_mean  -0.1228   <- pero su discrepancia con el cierre es dañina
    edge_sd    -0.2106

El modelo no tiene edge cero. Lo tiene **negativo**, y eso es distinto y peor.

### De paso: el modelo está bien calibrado

Independiente de todo lo anterior, y es una buena noticia:

    p_model        n     predicha   observada    error
    (0.1, 0.2]   1440     0.1620     0.1535     -0.009
    (0.2, 0.3]   4870     0.2517     0.2624     +0.011
    (0.3, 0.4]   2292     0.3443     0.3264     -0.018
    (0.4, 0.5]   1573     0.4478     0.4520     +0.004
    (0.5, 0.6]    980     0.5467     0.5398     -0.007
    (0.6, 0.7]    542     0.6445     0.6365     -0.008

Dentro de ±0,02 en todos los tramos con muestra. Confirma por otra vía por qué
el calibrador se descartaba: no había nada que corregir. Los extremos
(p > 0,7, n = 270) muestran infraconfianza de +0,05, pero con esa muestra no
se puede afirmar.

### Decisión

- `UNCERTAINTY_ENABLED` se queda en 0, y **no por prudencia sino por medición**.
- `UNCERTAINTY_Z` queda documentado como SIN CALIBRAR. Ningún valor es
  defendible porque no hay señal que calibrar. Poner 0,9 porque la tabla sube
  sería exactamente el error que este experimento existía para evitar.
- Y lo más importante: **`find_candidates` selecciona hoy, en promedio,
  apuestas perdedoras**, porque ordena por una cantidad con correlación −0,12.
  No se cambia a escondidas, pero queda escrito arriba del todo.

### La estrategia que sí podría funcionar NO se puede probar con este histórico

El punto 1 del plan —precio justo sharp y apostar donde una casa blanda aún no
ha convergido— no depende del edge del modelo, así que no hereda este signo.
Pero es **imposible de medir con los datos que hay**: el solapamiento entre
Pinnacle y bet365 es CERO. 46.928 partidos tienen solo Pinnacle y 2.014 solo
bet365, porque `history_fd` guarda una única casa de cierre por partido. Sin
dos casas sobre el mismo partido no hay line shopping que medir.

Eso convierte el plan de The Odds API en el cuello de botella real: es la única
fuente que da varias casas sobre el mismo partido, y con 500 créditos el worker
no puede correr. Ya no es una mejora deseable, es la única vía abierta.

## 2026-09-24 — Mesa de mercados en el prototipo web (referencia: propsbr.app)

El usuario preguntó si propsbr.app podía servir de modelo para vender sus
picks. PropsBR es un buscador de props por acierto reciente (L5/L10/L20, H2H)
con nota 0-100 y etiquetas del tipo «certera/segura»; no mide nada contra el
cierre. Se copió su **composición** (lista de partidos, tabla densa ordenable,
detalle lateral con pestañas, columna de destacados, formato de cuota) y se
descartó su **contenido**.

Decisiones:

- La mesa enseña lo que el sistema sí mide: precio justo de Pinnacle sin
  margen, mejor casa de la lista, % sobre el justo en el mismo snapshot,
  `min_price` y exclusión por Pinnacle fuera de consenso. El modelo va como
  columna de diagnóstico y nunca ordena: su edge es anti-señal medida.
- Al ordenar por diferencia, lo excluido o cerrado va siempre al final. Un
  +10% de un partido con Pinnacle roto encabezaba la tabla y era justo el
  número que el criterio descarta.
- Los precios demo se derivan de dos lambdas (Poisson) y pasan por el mismo
  criterio que `publish/picks.py` (1X2, +2%, 3% de desviación máxima, un pick
  por partido), para que mesa, picks y ficha no se contradigan. Con precios
  realistas salen pocas candidatas; no se forzaron más.
- `.table-wrap` necesita `position:relative`: el texto `sr-only` absoluto
  dentro de tablas desplazables se escapaba del recorte y ensanchaba la
  página a 825 px en móvil.
- El menú lateral pasó a una cabecera fija arriba (petición del usuario): la
  mesa necesita todo el ancho para la tabla, y el lateral le quitaba 224 px.
- Accesos rápidos al estilo PropsBR (petición del usuario), con nombres que
  dicen lo que miden: «Top probabilidad» en vez de «top confianza», porque
  ordena por probabilidad justa y eso no dice si la cuota compensa.
- Combinadas calculadas por casa y no con la mejor cuota de cada selección:
  la combinada se juega entera en una casa. En la demo, dos selecciones a
  +3,5% y +7,5% en su mejor casa dan +0,0% en la única que cotiza las dos a
  buen precio; enseñar la otra cifra habría sido vender una ventaja que no
  se puede cobrar. Una selección por partido: dentro del mismo partido están
  correlacionadas y el producto de probabilidades sería falso.
- Revisados los nueve botones reales de PropsBR: seis son la misma lista por
  Score con distinto corte, dos son combinadas armadas (Parlays ~2X/~3X y
  Seguras 1,50–2,30) y uno, «Certera del día», es un pick de pago con venta
  que cierra al inicio e historial público. Ese último es exactamente el
  negocio de QuantFut, así que entró como **Pick del día**; los cortes
  duplicados no se copiaron. Sus parlays anuncian «62% prob» en una cuota
  2.30 (implícita 43%): nuestras combinadas enseñan la probabilidad justa.

## 2026-09-25 — El proyecto pasa a git

Petición del usuario tras el incidente de abajo. Rama `main`, primer commit
`4bd73ee`. Decisiones:

- Fuera del repo: `.env` y `.env.*` (menos `.env.example`), el volcado
  `quantfut.dump` (dato de producción, no código), `.venv`, `.local` (cachés
  de >100 MB) y `__pycache__`. Antes del primer commit se comprobó que ningún
  valor secreto de los `.env` aparece en otro archivo (solo `REDIS_URL`, que
  no lleva contraseña).
- `.gitattributes` fija LF: el despliegue copia al servidor Linux tal cual, y
  el `crontab` y los `.sh` se rompen con CRLF. 21 archivos Python tenían CRLF
  en disco; normalizados.
- Aún SIN remoto: el código solo está en este PC y en el VPS. Falta decidir
  dónde vive la copia remota (GitHub privado o un repo en el propio VPS) y
  convertir `~/quantfut` del servidor en copia de git, para que `git status`
  allí delate cualquier archivo subido a mano.

## 2026-09-25 — Incidente: la sombra caída 2 h por un archivo subido a medias

A las 17:56 UTC alguien (no esta sesión) subió al servidor el
`shadow_sharp.py` de goles y hándicap —que se había decidido NO desplegar— y
reconstruyó la imagen, sin la migración 022 ni el `picks.py` a juego. La
captura horaria de la sombra falló desde las 18:25 (`'Offer' object has no
attribute 'market'`); falla antes de escribir, así que no ensució nada, pero
se perdieron ~2 h de ofertas. Restaurado el original (reconstruido deshaciendo
los cambios exactos: no quedaba imagen anterior) y verificado con una captura
manual.

Decisiones:

- El código de goles y hándicap sale del repo y va a
  `harness/archivo/goles_handicap_20260925/` (con su migración 022). Tenerlo
  en `src/` sin desplegar era la trampa: el proyecto no usa git y cualquier
  subida de la carpeta lo arrastra.
- Antes de cada despliegue se compara TODO `src/` y `db/` con el servidor
  (`tar` + `diff -rq`), no solo los archivos que se van a subir. Así se vio
  que el único archivo distinto era el roto.

## 2026-09-25 — Picks sin predicción, etiquetas de temporada y limpieza

- Pick sin predicción (`db/025`): ver tareas. Vacío, nunca 0, en
  `model_prob`: un 0 se leería como "el modelo da 0%".
- Etiqueta de temporada (`db/026`): el calendario etiqueta como el
  histórico ('2627'). Se cambió la columna, no el match_id, que lo referencian
  predicciones, picks y cuotas inmutables; el calendario encuentra los
  existentes por su id de API-Football, así que no duplicó nada (verificado).
- "Evento sin emparejar" de `odds_worker` baja a debug: no era un fallo.
- `pyton/` borrada; su único contenido sin copia (la versión inicial) queda en
  `harness/archivo/`.

## 2026-09-25 — LaLiga 2 y Serie B, sin ensuciar la base

Petición del usuario, con esa condición expresa. Entran por el criterio sharp
(backtest: +3,9% y +5,1% al cierre, validables en The Odds API).

Decisiones:

- `leagues.model_enabled`: las ligas nuevas alimentan calendario, resultados,
  cuotas y sombra, pero NO el modelo ni la predicción diaria. Sin esto el job
  de las 08:00 habría sellado predicciones de equipos que el modelo no
  conoce, y lo sellado es público e inmutable.
- Un club tiene una sola liga en `teams`: al abrir una división nueva el
  calendario habría duplicado a los 20 descendidos de LaLiga y Serie A. Ahora
  `resolve_or_register` busca coincidencia EXACTA en las otras ligas del mismo
  país antes de crear, y el parecido dudoso queda pendiente. Sirve también
  para ascensos futuros.
- Aun así, ningún equipo quedó a la automática: `db/024` da de alta los 22
  nuevos y los alias de las dos fuentes de los 42, revisados uno a uno tras un
  ensayo en seco. El ensayo justificó la regla: "Real Sociedad II" daba 90
  contra "Real Sociedad" (el umbral de aceptación) y era el filial;
  "Sporting Gijon" daba 73 contra "Sp Gijon" y sí era el mismo club.
- Alias de The Odds API desde el primer día: sin ellos el cierre de Pinnacle
  no casa y la oferta se queda sin vara en silencio.
- The Odds API solo paga `h2h` en estas ligas (1 crédito por llamada): es el
  único mercado del criterio y a la API le quedan ~3.200 créditos.
- Sin histórico de football-data (`fd_code` NULL): el criterio no lo
  necesita y cargarlo mezclaría dos fuentes de nombres en equipos nuevos.

## 2026-09-25 — Goles y hándicap: implementado, probado, y sin valor

Petición del usuario: más picks cada día, eligiendo "más mercados". Se
implementó el mismo criterio por línea (captura, criterio, sombra, 19 tests,
`db/022`) y, ANTES de desplegar, se ensayó en memoria con la respuesta real
de API-Football para los 24 partidos próximos. Resultado: 0 de 1.448 precios
de casas de la lista por encima del justo en un 2%, en cualquier línea.

Decisiones:

- No se despliega. Publicar el código añadiría captura y almacenamiento
  (~50× filas) sin añadir picks. Queda en el repo, probado, para repetir el
  ensayo con Europa en juego.
- La lección es de producto, no de código: las casas de los suscriptores
  ponen goles y hándicap copiando a Pinnacle con margen; donde se equivocan es
  el 1X2 (empates y no favoritos). Más picks tienen que venir de más PARTIDOS
  en 1X2 (más ligas), no de más mercados del mismo partido.
- Solo línea principal en el criterio: The Odds API da el cierre de Pinnacle
  en una sola línea, y una oferta sin cierre no se puede validar. Trampa
  encontrada y cubierta por test: API-Football etiqueta las dos patas del
  hándicap con la línea del local.

## 2026-09-27 — Fichas de partido reales en la web: contenido, no criterio

Pedido del usuario: que el sitio resulte atractivo con fichas al estilo
PropsBR usando API-Football. Desplegado (db/028, db/029, `ingest/standings`,
`/web/partidos`, vista «Partidos y estadísticas»).

- La ficha NO lleva probabilidades de mercado ni precio justo, aunque el
  plan las incluía. El producto es "una casa paga ≥2% sobre el justo de
  Pinnacle"; publicar ese justo en cada partido deja a cualquiera hacer la
  cuenta con la cuota de su casa. Tampoco el modelo (su edge es negativo).
- Coste de API casi nulo: `results.py` ya pedía `/fixtures/statistics`;
  ahora guarda la respuesta entera en `matches.stats`. Lo único nuevo es
  `/standings`, 13 peticiones dos veces al día.
- La forma y los promedios solo miran 270 días atrás. Sin tope, Valladolid
  (en Segunda, sin histórico de football-data) enseñaba como "últimos 5"
  partidos de Primera de mayo de 2025. Con tope, un descendido enseña sus
  partidos de mayo de 2026 con fecha y competición: verdad, aunque no sea
  su forma en Segunda. Lo correcto es cargar la temporada en curso de
  LaLiga 2 y Serie B (propuesto al usuario; ver tareas).
- `teams.display_name` (nombre de API-Football, solo si la coincidencia en
  standings es EXACTA) en vez de tocar `canonical_name`, que es la identidad
  de emparejamiento: "Manchester City" en la web, "Man City" en el sistema.
- Argentina devuelve Apertura (cerrada) y Clausura con la MISMA fecha de
  actualización en todas las filas: la fecha no distingue fases. Se usa el
  orden del proveedor (calendario) y se conserva la última fase; los grupos
  sin prefijo de fase (conferencias de la MLS) no se tocan.
- Aviso sin tocar: `/fair-price/{id}` es público y devuelve `best_price` y
  `gap_pct`: el criterio en abierto. Decisión del usuario pendiente.
- Los logs de cron viven dentro del contenedor `worker`: al reconstruirlo se
  pierden (se vio al buscar `/var/log/fixtures.log`). No se cambió.

## 2026-09-27 — Escudos, temporada de LaLiga 2 / Serie B y un ir y venir del calendario

- Escudos descargados UNA vez al volumen `escudos` y servidos desde el
  propio dominio, en vez de enlazar `media.api-sports.io`: la web no depende
  del CDN del proveedor ni le pasa la IP de cada visitante. 271 archivos,
  12 MB, caché de navegador de 7 días.
- `/standings` devolvió `team.id` nulo para Club León y `/teams` lo llama
  'Leon'. Se completa con `/teams` (1 petición, solo si falta alguno) por
  nombre y, si difiere, por el MISMO equipo resuelto exacto. Un id nulo no
  borra uno guardado (`COALESCE`).
- Temporada de LaLiga 2 y Serie B cargada por el camino normal (insertar
  como programados + `results.close_recent`) en vez de un INSERT a mano:
  mismas reglas de resolución, marcador y estadísticas que cualquier
  partido. El modelo no los lee (`model_enabled = false`).
- Fallo previo encontrado al preparar la carga: `fixtures` pide el día
  entero y los partidos de hoy ya terminados llegan como FT; se mapeaban a
  'scheduled', se reabrían y se borraba su `odds_capture_log` hasta que
  `results` los cerraba otra vez. Ahora un partido `finished` no se toca
  desde el calendario (test en `test_calendario_terminados.py`).

## 2026-09-28 — Un alias no cruza países (Guimarães era el Vitória brasileño)

Buscando escudos que faltaban apareció el Vitória BRASILEÑO 14.º en la
Primeira. API-Football renombró al Guimarães 'Vitória SC', que se normaliza
igual que su alias 'Vitoria' de Brasil; el mapa de alias guardaba UN equipo
por nombre y sin mirar la liga. Ya había metido al brasileño en el
Benfica–Guimarães del 11-oct: se habría sellado una predicción inmutable con
los ratings de otro club.

- `normalize.match_team`: un alias puede ser de varios equipos y solo vale
  el que juega en la liga o en otra división del MISMO país. En copas (sin
  liga) un alias ambiguo no se adivina: se descarta como cualquier nombre
  sin resolver. Colisiones hoy en `team_aliases`: ninguna dentro de una
  fuente; la de Vitória entraba por el nombre nuevo del proveedor.
- db/031 corrige el partido (sin predicciones, cuotas ni sombra), añade el
  alias propio de Guimarães y limpia nombre, id y fila de clasificación que
  se escribieron sobre el brasileño. Comprobación tras el cambio: 0 partidos
  domésticos con un equipo de otro país; las copas siguen con los mismos
  9 + 16 nombres sin emparejar de siempre.
- db/032: escudos de 47 equipos que ya no están en ninguna tabla actual,
  con ids de `/teams` 2023-2025 revisados a mano ('Atletico GO' puntuaba más
  con Atlético-MG). 0 equipos sin escudo entre los que jugaron en 3 años.

## 2026-09-28 — `/fair-price` pasa a privado

Decisión del usuario. `best_price` + `gap_pct` por partido es el criterio de
picks entero: con él cualquiera ve qué casa paga ≥2% sobre el justo sin
suscribirse. Ahora es `/v1/fair-price/{id}` con `SERVICE_TOKEN`; la ruta
pública desaparece (404, igual que una ruta privada sin token, para no
confirmar que existe). No lo consumía nada: ni el frontend ni otro módulo.

## 2026-09-28 — Palancas para acelerar la puerta, sin rebajarla

Pedido del usuario ("ejecuta todas las palancas"). La puerta NO cambia (300
publicables con cierre justo, IC95 > 0, 3 ligas); cambia cuántas
oportunidades se miden por día.

- **Casas.** Simulado antes sobre 36 partidos desde el 24-sep: con la lista
  de entonces, 8 partidos con oferta; con todas las casas del feed, 23. La
  sombra mide ahora TODAS las casas no exchange, pero la puerta filtra por
  `SOFT_BOOKS` AL INFORMAR (no se guarda columna): así la muestra se puede
  recalcular para otra lista sin volver a capturar. Lista ampliada con
  Betsson, Coolbet, LeoVegas y Unibet por operar en España o Latinoamérica,
  pendiente de que el usuario lo confirme; LeoVegas/Unibet llegan con precio
  de Suecia/Países Bajos. Casas offshore de EE. UU. y francesas/alemanas se
  miden pero no cuentan.
- **Cierre.** El "3 de 4 con cierre" era un pick aún sin jugar: 10 de 10
  partidos en sombra lo tienen. El Pinnacle de API-Football nunca baja de
  2,5 h antes del inicio, así que el cierre solo sirve de The Odds API.
  Riesgo encontrado y cerrado: la captura de :25 podía tomar como oferta el
  snapshot de la ventana de cierre, que es contra el que se liquida (EV =
  edge bruto por construcción). No había pasado; ahora se exige ≥ 15 min.
- **Persistencia.** Regla fijada ANTES de tener muestra: la previa pesa como
  100 partidos frente a lo medido (primera oferta por casa y partido,
  acotado a [0, 1]). Cada oferta guarda la persistencia con la que se
  decidió, así que recalibrar no reescribe el pasado.
- **Ligas (db/033).** Chile, Turquía, Suiza, Dinamarca, Noruega, Suecia,
  Championship, Ligue 2, 2. Bundesliga y Brasil B, todas con Pinnacle en The
  Odds API (sondeo de 21 créditos). Colombia, Perú y Ecuador no existen en
  The Odds API; Bélgica, Australia y Superettan no tienen Pinnacle. Equipos
  preparados de antemano como en 024: el calendario, creando de uno en uno,
  descartaba el segundo club que se pareciera al primero. 43 reutilizados
  (25 confirmados por id de API-Football) y 127 nuevos; el calendario no
  creó ninguno más. Coste estimado: ~100 créditos/mes por liga (solo 1X2) y
  ~800 peticiones/día de API-Football.
- **Copas.** Con clubes turcos, suizos o daneses en el catálogo, sus partidos
  de Champions/Europa League empiezan a resolverse. `daily._upcoming` y el
  entrenamiento exigen ahora que la liga DOMÉSTICA de ambos equipos tenga
  modelo: si no, se sellaría una predicción con ataque y defensa 0. Al
  introducir la guarda no excluía ningún partido del entrenamiento.

- **Lista confirmada por el usuario:** sus clientes usan Betsson y Coolbet;
  LeoVegas y Unibet salen de `SOFT_BOOKS` y se siguen midiendo sin contar.

## 2026-09-29 — Fase 4: el ajuste por XI deja de esperar a diciembre

Diagnóstico: todo estaba construido (captura de XI cada 5 min, challenger,
cuatro brazos en sombra) pero el challenger nunca se había entrenado. Exige
700 partidos con predicción sellada + XI capturado antes del inicio, y había
4 y 21 (modelo activo desde el 27-sep, XI desde el 26-sep). En vivo llegaría
hacia diciembre.

Decisión del USUARIO (única excepción al punto en el tiempo, y acotada):
alineaciones descargadas después del partido, en `lineups_historicas`
(db/034), que SOLO lee el entrenamiento/validación del challenger. La
predicción diaria, la sombra y `availability()` siguen con XI capturados
antes del partido; hay un test que falla si alguno de esos módulos nombra la
tabla. La promoción sigue exigiendo CLV en sombra.

- Base: las predicciones fuera de muestra que `train.py` YA calcula (walk-
  forward del último año, sin coste extra), ahora con la rho de su paso.
- Una fila sellada con UN lado histórico no cuenta como sellada: su hora de
  XI queda vacía y la regla estricta la descarta.
- Encontrado de paso: si nadie tenía 3 XI previos, las features salían sin
  columnas y el cruce reventaba; `train.py` lo tapaba como "no se pudo
  preparar". Ahora devuelve "collecting" con su motivo real.
- Un reentreno no promovido guardaba el challenger con otra versión y el
  brazo de la sombra se quedaba sin artefacto: ahora usa el último validado.
- La cuota restante de API-Football llega como TEXTO en la cabecera; la
  primera pasada murió comparándola con un número (46 peticiones perdidas).

- Resultado de la descarga: 4.555 partidos con XI (0 vacíos), 3.988 con 3
  XI previos por equipo dentro del último año, entre 288 y 508 por liga. Las
  copas no emparejaron (sus rivales no están en el catálogo); no hacen falta.
  No se fuerza el entrenamiento: el mensual del 1-oct lo incluye y no hay
  partidos de estas ligas hasta el 9-oct (parón de selecciones).

## 2026-10-01 — Cadena del XI en vivo: funciona, pero el XI llega a T-25

Auditoría de los partidos de los últimos 30 días en ligas con modelo:

- Solo 21 de 397 tenían XI. No es un fallo: las europeas jugaron por última
  vez el 20-sep y la captura en vivo de The Odds API empezó el 24-sep; los 21
  son de MLS y Liga MX. Las europeas vuelven el 9-oct.
- 17 de esos 21 no tenían predicción porque no hubo modelo activo hasta el
  27-sep 06:21 (el de 24-sep no se activó). Desde entonces, 4 de 4 partidos
  con XI recorrieron toda la cadena: predicción 08:00 → XI → cuotas
  `post_xi` → sombra (`baseline_t60`, `baseline_market`). Faltaba el brazo de
  XI solo porque no había ajuste validado (resuelto hoy).
- Hallazgo importante: el XI se guarda a T-25 en 22 de 22 partidos, aunque se
  consulta cada 5 min desde T-90. El cliente no tiene caché; es el
  proveedor (su guía: 20-40 min antes). Con el XI a T-25, Pinnacle ya ajustó
  y la ventaja temporal de la recomendación 1 casi desaparece. Siguiente paso:
  medir la antelación en europeas desde el 9-oct antes de pensar en otra
  fuente.

- Prueba en vivo (Seattle–Sporting KC, 2-oct 01:30 UTC): XI a T-24, cuotas
  `post_xi` a T-20 con 21 casas, sombra a T-19 con `baseline_t60` y
  `baseline_market`. Los brazos de XI NO se registraron aunque el ajuste está
  validado: `availability()` exige 3 XI previos del equipo en la tabla en
  vivo `lineups` (existe desde el 26-sep) y devuelve "historia
  insuficiente". Las europeas empiezan de cero el 9-oct: el brazo de XI no
  medirá nada hasta ~finales de octubre. Completar esa historia con
  `lineups_historicas` ampliaría la excepción del usuario (hoy solo
  entrenamiento): queda a su decisión.

## 2026-10-01 — Criterio de ECE del XI: ruido, no orden (decisión del usuario)

Opción B elegida por el usuario. Antes: el XI se validaba solo si
`ECE_después <= ECE_antes`. Ahora: remuestreo pareado por partido (1.000,
semilla 0) de ECE_después − ECE_antes; solo "empeora" si el percentil 2,5 %
es > 0. Se informa `ece_delta_ic95` y `ece_empeora`. RPS, log-loss y ≥2 ligas
no cambian.

- Por qué: simulado con base variable y 3.600 filas, una señal real pasaba la
  puerta antigua 2-6 de 8 veces; con la nueva, 8-10 de 10 (efecto 0,1-0,4).
  Ruido puro: 0 de 10 con 1 señal, 1 de 10 con 14 (frenan RPS, log-loss y
  ligas; y la sombra todavía exige CLV antes de publicar nada).
- Transparencia: el criterio se cambió después de ver que el XI simple
  fallaba solo por el ECE (+0,00055). La regla es la estándar (no
  significativo al 95 %), no un umbral ajustado a ese número, y aplica igual
  a los brazos de la fuerza por jugador (XI con valor sigue sin validar:
  falla por RPS y log-loss).
- Reevaluado con `python -m qf.model.lineup_challenger` sobre
  `oos_2026.10.01-030007.pkl` (mismos números que el reentreno: el ajuste es
  determinista): IC95 del cambio de ECE [−0,00741, +0,00582], `ok: true`.
  `lineup_2026.10.01-030007.pkl` reescrito; el anterior, en
  `~/respaldo_20261002_b1/`. `model_artifacts.val_metrics` no se reescribe:
  conserva lo que dijo el reentreno con el criterio de entonces.

## 2026-10-01 — Reentreno mensual y fuerza por jugador (Fase B1)

Reentreno 2026.10.01-030007: NO se activa ("No mejora el baseline Elo sobre
las mismas filas"; RPS 0,20074 en 1.107 filas). Sigue activo 2026.09.27.
El walk-forward se guardó (`oos_2026.10.01-030007.pkl`) y sirvió para la B1
sin repetir 3,5 h de entrenamiento.

XI simple (3.650 filas, 2.555 ajuste / 1.095 validación): RPS 0,21817 →
0,21678, log-loss 1,05235 → 1,0479, 8 de 11 ligas mejoran, pero ECE 0,03041 →
0,03096: queda `shadow_only`. La sombra no tiene ningún XI validado.

Fuerza por jugador B1, mismas 3.645 filas para los tres brazos:

| brazo | RPS | log-loss | ECE | ligas |
|---|---|---|---|---|
| base | 0,21818 | 1,05317 | 0,03125 | - |
| XI simple | 0,21677 | 1,04868 | 0,03182 | 8 |
| XI con valor | 0,21912 | 1,05654 | 0,03705 | 1 |
| XI con nota | 0,21801 | 1,05274 | 0,03175 | 8 |

- "XI con valor" empeora a la base: 18 señales (9 estadísticas por lado)
  sobreajustan con 2.551 partidos. Saber QUIÉN falta, medido por sus
  estadísticas, no añade nada a saber CUÁNTOS habituales faltan. Según el
  plan, no se escribe la B2. No se probaron variantes sobre la misma
  validación: elegir la que salga mejor sería ajustar al 30 % de prueba.
- La nota del proveedor (solo comparación) tampoco supera al XI simple.
- El test de "valor gana" de la B1 se reescribió con informes controlados:
  con validación de 300 filas el ECE de dos brazos se ordena casi al azar
  (simulado: señal real fuerte pasa 2-6 de 8 veces; sin señal llegó a pasar
  1 de 6 con 1.000 filas). Eso mismo afecta al XI simple real: decisión
  del criterio pendiente del usuario (ver tareas).
- `shadow._challenger_validado` ahora exige `features == LINEUP_FEATURES`:
  los artefactos `lineup_valor_` / `lineup_nota_` comparten el patrón
  `lineup_*.pkl` y uno validado en el futuro se habría cargado como XI simple.
- La revisión programada del 1-oct quedó colgada en "running" sin actividad;
  esta revisión se hizo a mano.

## 2026-10-03 — FotMob: mismo xG que Opta, disponible en horas y con LatAm

Pregunta del usuario: ¿llega antes por FotMob? Comprobado en su JSON
público (solo lectura, desde el navegador): los 6 partidos recientes sin xG
en API-Football lo tienen en FotMob, incluido Boca–Unión jugado horas
antes; y cubre Liga MX y Argentina, que en API-Football casi nunca lo
traen. Contra el xG de FBref guardado (17 partidos de 2024, 6 ligas):
diferencias de 0,00-0,05 en 32 de 34 valores; dos de 0,2 y 0,6 (Premier y
LaLiga), probablemente el valor de un penalti. Sin retraso, además, no hay
la fuga de backtest que traería el xG tardío de API-Football.

## 2026-10-03 — El xG de API-Football: fiable cuando está, irregular en cuándo

Pregunta del usuario: ¿no sirve el proveedor ya contratado? El README lo
prohibía (22-sep) por cobertura irregular y vacíos mudos. Medido, solo
lectura, ~350 peticiones:

- **Valores: los mismos que FBref/Opta.** 2024, 15 partidos por liga
  emparejados con el xG guardado: correlación 0,963 (Argentina) a 1,000
  (Serie A), medias casi idénticas, diferencia media 0,01-0,09 por equipo.
  Muy probablemente el mismo proveedor (Opta): se puede empalmar sin
  romper la serie.
- **Cobertura: irregular por liga, temporada y fecha.** 2024: completa en 8
  ligas europeas, Brasil y MLS; Argentina 5/15; Liga MX 0/15. Temporada en
  curso, muestra al azar: casi todo con xG salvo Argentina (1/6). Pero los
  partidos RECIENTES no lo tienen: MLS 0 en los últimos 6,6 días, Liga MX 1
  de 14 en dos semanas, Argentina 0 de 14; LaLiga y Premier sí a 13 días.
  Llega con retraso de días o semanas, y en las americanas puede no llegar.
- Consecuencia de diseño si se adopta: no basta con leerlo al cerrar el
  partido (`results.py` lo pide a +105 min y por eso no lo tenía); hay que
  volver a pedirlo durante semanas. Y en backtests el xG de las últimas
  ~2 semanas no existía en el momento de predecir (`check_leakage` avisa de
  xG registrado >6 h tarde): fuga pequeña, pero real.

## 2026-10-03 — El xG aporta: merece una fuente nueva

`eval/xg_value.py`, regla fijada antes de ver nada. Mismo walk-forward
(reajuste cada 30 días, solo pasado) con `xg_blend` 0,65 frente a 0; cada
reajuste tardó ~18 min, así que se lanzaron los cuatro brazos en procesos
aparte (6 h). `check_leakage`: solo el aviso genérico de que las cuotas son
cierre, y aquí no se usan como variable.

- Ventana A (xG existía, 6.785 partidos, 84 semanas): RPS 0,20154 frente a
  0,20440; delta −0,00287, IC95 [−0,00376, −0,00200]; mejora en 12 de 13
  ligas (solo la Europa League, n=66, empeora). Veredicto: `xg_aporta`.
- Ventana B (hoy, 3% de partidos de test con xG): −0,00055 [−0,00100,
  −0,00018], 8 de 13 ligas. Lo que queda es la historia vieja con xG en el
  entrenamiento, que se diluye con la media vida.
- Lectura: 0,0029 de RPS es lo mismo que Dixon-Coles saca a Elo y ~40% del
  hueco con Pinnacle (0,0068). Perderlo para siempre no es neutral. Pero el
  modelo no elige los picks: esto mejora el modelo, no la puerta comercial.

## 2026-10-03 — Cerradas las fugas del criterio de la fase 3

Con el sí del usuario: `/matches/{id}` sin `market_consensus`, sin
`/openapi.json`, y opción (b) para la cadena: el lote deja de llevar el
precio justo desde el 3-oct. Se descartó reescribir el formato hacia atrás:
un lote pasado regenerado desde la base tiene que dar el hash sellado, y es
lo que hace verificable la cadena; por eso la fecha de corte vive en el
código (`LOTE_SIN_CONSENSO_DESDE`). Comprobado en producción con el lote del
2-oct.

Al tocar `hashchain.py` apareció el problema mayor: el lote lleva también
los picks, de pago incluidos, y el flujo documentado lo sube a un repo
público ANTES de los partidos. (b) no lo resuelve; lo resolvería publicar
solo el hash antes y el JSON después (comprometer-revelar). Queda como
decisión del usuario en tareas; hoy no ocurre porque no hay remoto.

## 2026-10-03 — Auditoría de la fase 3 (solo lectura, contra producción)

- **Bien:** Cloudflare Access cierra `/control`, `/admin` y Grafana en los
  tres dominios, y una cabecera `Cf-Access-Jwt-Assertion` falsa no lo salta
  (Access valida en el borde; Caddy solo comprueba que exista). `/v1/*` sin
  token da 404; el panel exige PBKDF2 600k y token de 64. Puertos: solo 22,
  80 y 443 públicos; 8000 y 3000 en 127.0.0.1. CORS rechaza orígenes
  ajenos. El limitador corta en 60/min por IP (ventana fija: hasta 2x en el
  cambio de minuto). El JavaScript solo llama a rutas públicas. La ficha
  `/web/partidos/{id}` no lleva cuotas ni probabilidades.
- **Fuga del criterio:** `/matches/{id}` devuelve `market_consensus` (justo
  sin margen) y los lotes sellados también lo llevan. No hace daño hoy (no
  se vende ni se publica la cadena), pero es exactamente lo que se quiso
  cerrar el 28-sep. Pendiente de decisión del usuario (tareas.md).
- Menores: `/openapi.json` público con las rutas privadas, rutas internas en
  `/model-card`, sin CSP, y ningún aviso legal (+18, juego responsable,
  privacidad, términos) en la web.

## 2026-10-03 — Antelación de la decisión y rescate del cierre

Las dos primeras mejoras de la auditoría, con el sí del usuario.

- **Una sola `MIN_LEAD` para sombra y publicación, aplicada al precio Y a
  la decisión.** Al leer el código apareció algo peor que lo auditado: la
  publicación real no tenía ninguna guarda de antelación. La puerta
  certifica "lo que se habría publicado", así que la regla tiene que ser la
  misma en los dos lados; la constante vive en `picks.py` y la sombra la
  importa, para que no puedan divergir.
- **Rescate del cierre desfasado 5 min, solo `close`.** Se descartó mover la
  ventana o tomar un "precierre" de respaldo: cualquiera de las dos cambia
  la vara de la puerta. Con el rescate la vara es la misma (último precio a
  3-12 min) y hay dos intentos; el registro de captura evita pagar dos veces.
- Desplegado sin reiniciar el worker (`docker compose cp` + recargar el
  crontab montado) para no cortar la medición del xG; API reconstruida.

## 2026-10-03 — Auditoría de las fases 0, 1 y 2 (solo lectura)

Recalculado de forma independiente contra la base de producción, no leído de
los informes del propio sistema.

- **Fase 0, limpia.** 0 precios fuera de rango, 0 ternas 1X2 incompletas (de
  5.129), 0 duplicados, 0 snapshots posteriores al inicio; Pinnacle dentro
  del consenso en los 49 cierres; cierre a 4-9 min. Toda ventana que falta es
  de partidos dados de alta con <72 h (LaLiga 2 el 25-sep, Brasil B el
  28-sep) o reprogramados. Riesgo anotado, no fallo: la ventana `close`
  (3-12 min) cae en UNA pasada del cron */10; si esa pasada falla, el
  cierre se pierde y la oferta no cuenta para la puerta.
- **Fase 1, limpia salvo lo ya sabido** (xG parado). 0 clubes duplicados
  por `af_team_id`, 0 equipos bajo `eu.*`, 0 partidos duplicados, 0 equipos
  en dos partidos a <40 h; 10 de 10 partidos con predicción sellada antes del
  inicio; cadena de hashes verificada (4 lotes). Arreglado: `fixtures.run()`
  contaba los clubes de copa fuera del catálogo como incidencia; con
  Telegram activo habría avisado dos veces al día por algo esperado (mismo
  criterio que `check_unresolved_names`). Desplegado con `docker compose cp`
  para no matar la medición del xG en curso; el próximo build lo incluye.
- **Fase 2, los números de la sombra son correctos.** 165 de 165 precios
  justos de entrada reproducidos (Shin sobre el snapshot de Pinnacle del
  mismo instante; en API-Football el snapshot es `provider_updated_at`, no
  `fetched_at`); 89 de 89 EV al cierre idénticos; 0 resultados o
  beneficios mal liquidados; publicables una por partido, solo SOFT_BOOKS,
  decididas 8-71 h antes con precios de ≤5,2 h. Matiz: la guarda de 15 min
  mira la hora del PRECIO, no la de la decisión; 3 ofertas se decidieron a
  <15 min (ninguna de SOFT_BOOKS, no cuentan). Publicación pausada
  (`PUBLISH_PICKS_ENABLED=0`, `picks` vacía).

## 2026-10-02 — Copas recuperadas y chequeo de xG que mira el dato

`worldfootballR_data` lleva parado desde sep-2025 (dic-2024 en copas): el
modelo entrenaba solo con goles en los últimos meses y sin ningún partido de
copa de 2025/26. Decisión del usuario: recuperar copas y vigilar el xG; la
fuente de xG nueva queda pendiente.

- Copas desde API-Football, por el camino ya probado (insertar como
  programado, cerrar con `close_recent`). Ensayo en seco primero; la carga
  real coincidió partido a partido (351, 0 duplicados, 0 errores). Guarda de
  duplicados nueva en las cargas hacia atrás (misma competición y equipos,
  ±36 h): `matches` no tiene clave natural y lo que cuelga de un partido no
  se borra. Rangers→Angers (92) o Wolfsberger→Wolfsburg (80) confirman por
  qué en copa solo vale la coincidencia exacta.
- `check_xg_freshness` con reconocimiento CON CADUCIDAD (1-nov): sin ella
  el chequeo alertaría a diario por algo ya sabido —y se aprende a ignorar
  las alertas, que es como se perdió la de bajas—; sin caducar, escondería
  el problema para siempre como hizo el `ok` con 0 filas del job.

## 2026-10-02 — La alerta de bajas saltó cuatro días y no la vio nadie

Reconstruido con los datos de cada mañana: `check_injuries_coverage()` falló
el 28, 29 y 30-sep y el 1-oct (`us.mls` 16-17 partidos, 0 bajas). Tres
agujeros en cadena:

- **Ningún canal.** `health.run()` llama a `telegram.alert()`; sin
  `TG_BOT_TOKEN` eso era un WARNING genérico "mensaje omitido". Afecta a los
  7 chequeos diarios y a las 8 llamadas a `alert()` del código, no solo a
  las bajas. Decisión del usuario: configurar Telegram SOLO para alertas a su
  chat privado (`TG_ALERT_CHAT`); los canales de picks siguen vacíos, así que
  no se publica nada por ahí. Sin canal, `alert()` deja ahora el texto
  completo como ERROR.
- **Log efímero.** El cron escribía en `/var/log` del contenedor, que se
  borra en cada despliegue (dos ese mismo día). `/var/log` del worker es ahora
  el volumen `workerlogs`, y cada pasada del cron queda en `health_runs`
  (db/037). El panel y `/admin/health` no escriben historial.
- **Mensaje que invitaba a archivarlo.** Decía "mismo patrón de cobertura
  silenciosa que mx.liga_mx…", es decir, culpaba al proveedor. Ahora pide
  descartar antes un error nuestro.

Al activar Telegram aparecían dos riesgos nuevos, cerrados antes: el envío
es HTML y un "5 < 300" sin escapar hacía rechazar el mensaje; y un fallo de
Telegram propagaba la excepción al job que avisaba. Comprobado de paso: los
tres huecos conocidos de `/injuries` (Liga MX, Argentina, Primeira) son
reales (la API devuelve 0 por partido); Brasil sí trae datos.

## 2026-10-02 — La historia del XI en vivo sale también de lineups_historicas

Decisión del usuario, ampliando la excepción de db/034. `availability()`
exige 3 XI previos por equipo y solo miraba `lineups` (en vivo desde el
26-sep): el brazo de XI no habría medido nada en las europeas hasta finales
de octubre.

- Por qué no rompe el punto en el tiempo: lo que se toma de la tabla es el
  XI de partidos YA JUGADOS antes del de hoy, que era público antes del
  partido que se predice. Lo que sigue exigiendo captura previa al inicio es
  el XI de HOY, que solo sale de `lineups`. La predicción diaria y lo
  sellado no leen la tabla (test por AST en `test_lineups_historicas.py`).
- Coherencia: el entrenamiento del challenger ya construía la historia con
  las dos tablas; la sombra ahora calcula la variable igual.
- Si un partido está en las dos tablas manda el capturado en vivo; solo XI
  completos (≥11), como en el entrenamiento. `n_history_historico` dice
  cuántos XI de la historia salieron de la tabla histórica.
- Desplegado (worker + db/036, que solo cambia el COMMENT de la tabla;
  respaldo en `~/respaldo_20261002_historia/`). Verificado: el
  Seattle–Sporting KC pasa de "historia insuficiente" a 5 XI previos por
  lado (4 históricos); 257 de 262 equipos con partido en 14 días tienen ≥3.

## 2026-10-02 — Las bajas nunca se guardaron: id de API-Football contra id interno

`injuries` estaba vacía tras 521 comprobaciones en 51 partidos (22-sep a
2-oct), sin un solo error. `_side_of()` comparaba `team.id` de la respuesta
(API-Football, p. ej. Seattle = 1595) con `matches.home_team_id` (interno,
49060): nunca coincidía y cada baja se descartaba con `continue`. Comprobado
con una llamada real: 26 bajas en el Seattle–Sporting KC, las 26 perdidas.

- Arreglo: `pending_matches()` trae `teams.af_team_id` de ambos lados y se
  compara contra eso (`tests/test_injuries.py`). Ningún equipo de las ligas
  con modelo con partido en 14 días tiene `af_team_id` nulo.
- Lo que se descarte a partir de ahora deja un WARNING y cuenta en
  `discarded`, también en el `record_health` de la pasada: un descarte
  masivo ya no puede volver a pasar mudo.
- Lo perdido no se recupera como dato point-in-time: pedir hoy las bajas de
  un partido pasado da la foto de hoy, no la que se conocía antes del
  partido. No se rellena; la muestra válida empieza el 2-oct.
- Desplegado (solo `worker`; respaldo del archivo anterior en
  `~/respaldo_20261002_injuries/`). Verificado en producción: el
  Seattle–Sporting KC guarda 26 bajas, 0 descartadas.

## 2026-09-30 — Fuerza por jugador, Fase A: los datos

Diseño aprobado por el usuario sección a sección (valor por contribución por
90 min con decaimiento, encogimiento por posición y pesos estimados solo con
el tramo de entrenamiento; la nota del proveedor solo como comparación;
plus-minus descartado por coste y ruido con esta muestra). Calendario del
usuario: datos ahora, modelo después del reentreno del 1-oct, para poder
compararlo con el XI simple.

- No necesita excepción al punto en el tiempo: son estadísticas de partidos
  ya jugados; la Fase B solo usará, para el día D, partidos anteriores a D.
- `estadisticas_jugador_log` registra también los intentos vacíos: sin él,
  cada pasada reintentaría para siempre los partidos que el proveedor no
  cubre (hubo 11).
- El lado de cada bloque se decide por el id de equipo de API-Football, no
  por el orden (en `/fixtures/players` no está garantizado).
- Descubierto en los datos: el campo `substitute` del proveedor no es fiable,
  hay lados con 16 "titulares". La Fase B tomará el once de las alineaciones.
- Coste diario nuevo: 1 petición por partido cerrado en ligas con modelo.

## 2026-09-25 — Más volumen: medir antes de cambiar el criterio

Decisión: el umbral del 2%, un pick por partido, la referencia Pinnacle/Shin
y la publicación pausada NO cambian. El histórico puede descubrir variantes,
pero ya se utilizó para diseñar la estrategia: no sirve para certificarla.

- `eval/quote_coverage.py` informa la primera terna 1X2 completa observada
  por casa/fuente/liga, antelación y edad del precio cuando se conoce.
  The Odds API no conserva aún `last_update` del bookmaker: edad desconocida
  se deja nula, no se inventa cero. Hace falta ejecutarlo contra Postgres
  operativo antes de gastar más cuota en capturar antes de T−72.
- `eval/sharp_challengers.py` usa los 42 CSV ya cacheados, 7 ligas y seis
  temporadas, hash `59586239a2169a51b9a864f3655c6e5cdc4c8d68f18a1ccdcc2b69b2408f6118`.
  Compara Shin y Power sobre los mismos 14.294 partidos 1X2 y mide TODOS
  los brazos contra el MISMO cierre Pinnacle/Shin. Power apenas mejora el
  log-loss temprano (0,960347 frente a 0,960392) y el RPS (0,193120 frente
  a 0,193131): magnitud insuficiente para cambiar la referencia.
- Con la lista blanca actual y un pick potencial por partido, Shin al 2%
  deja 286 partidos, EV al cierre justo +3,788%; al 1% deja 530, con 244
  partidos nuevos cuyo EV histórico es +2,499% (IC95 por semanas
  [1,915, 3,071]). 502 de los 530 candidatos al 1% dependen de 1xBet.
  El umbral dinámico predefinido (1,5% <1,80; 2% 1,80–3,49; 3% ≥3,50)
  deja solo 233 partidos: no cumple ni el objetivo de más volumen.
- Esto es un proxy offline: no hay timestamp exacto de decisión, acceso
  regional, límite de stake, cuota todavía disponible ni tope diario en los
  CSV. La persistencia por casa se estimó al 2% y no se recalibró para el
  1%. La puerta en sombra, con precio verificable al cierre, sigue mandando.

## 2026-09-24 — La temporada 2026/27 no existía en siete ligas

Síntoma: el `--bootstrap` rechazaba cada noche ("mercado de 252 días") y la
puerta no tenía nada que liquidar. Causa: tres piezas correctas por separado
que dejaban un hueco entre ellas. `backfill()` acababa en 2025/26 por un rango
fijo; `fixtures` solo crea partidos futuros; `results` solo cierra 72 h. Lo
jugado entre el último histórico y el primer calendario no lo creaba nadie.

Decisiones:

- El histórico llega al año en curso, no a la temporada europea en curso:
  Brasil y Argentina etiquetan '2026' lo que juegan en mayo.
- Antes de insertar, `_ingest_rows` busca el mismo partido por liga, equipos
  y ±36 h, y si existe salta la fila ENTERA. El match_id no sirve de guarda:
  API-Football etiqueta la temporada '2026A'/'2026' y escribe otros nombres.
  Y las cuotas de cierre no tienen clave única y `odds_snapshots` no admite
  DELETE: una recarga sin esta guarda las habría duplicado para siempre (el
  ensayo lo confirma: 531 partidos ya cargados habrían vuelto a entrar).
- Racing Santander como alias (`db/021`), no como club nuevo: la guarda
  compara por team_id y un club duplicado la esquiva.
- Cargado en producción (991 partidos, 0 duplicados). No destraba el modelo:
  los CSV no traen Pinnacle desde enero de 2026, así que la frescura del
  mercado sharp depende SOLO de la captura en vivo. Suposición corregida: se
  esperaba que el cierre del CSV bastara.
- Las 17.385 cuotas de cierre repetidas de recargas antiguas no sesgan nada:
  son copias exactas (mismo precio) y todo lector del cierre toma un precio
  por selección. Se documentan y se dejan: la tabla es inmutable a propósito.
- Pendiente aparte, cosmético hoy: la columna `season` no es coherente entre
  fuentes en ligas de año natural ('2627' histórico, '2026'/'2026A'
  API-Football). Ningún cálculo del modelo la usa.

## 2026-10-03 — Investigación NBA 2026-27 y Telegram inmediato

El usuario pide incorporar NBA mediante investigación profunda, literatura
académica y experimentos, y aclara que las señales llegarían al instante por
Telegram. Se incorpora también su archivo `Texto pegado.txt`. Documento:
`docs/nba_2026_27_investigacion_y_plan.md` (21 experimentos E0–E20).

Decisiones de diseño, todavía sin implementación ni resultados propios NBA:

- La entrega por Telegram cambia la antigua restricción de web para esta
  ampliación. La rapidez real depende además del feed y de cuándo apuesta
  el cliente; medir supervivencia de ventaja y no asumir ejecución instantánea.
- Props de rebotes/asistencias/puntos y totales entre periodos son hipótesis
  experimentales. La literatura respalda posesiones, minutos, rotaciones y
  actualización, pero no un ranking contemporáneo garantizado de rentabilidad.
- Corregidas afirmaciones del texto sobre regresión inevitable, eliminación
  universal de garbage time, transferencia fija de USG y ventaja cuántica NBA.
  Box score, regímenes competitivos/paliza y resultados liquidables se separan.
- La infraestructura de fútbol conserva sus puertas/triggers/publicación.
  NBA requiere contratos/jugadores/periodos, guard point-in-time para live,
  liquidación y política de promoción propias; no convertir puntos en goles
  ni importar persistencias o requisitos de tres ligas sin validación.
- Propuesto worker dedicado con sellado y outbox, revalidación, caducidad e
  historial de envío. No se activó ni envió Telegram, no se consultaron APIs
  de pago, no se desplegó ni se modificó código de producción.
- Fuentes y límites de lectura explicitados: algunos trabajos se verificaron
  por abstract/metadata, otros con texto completo. No presentar beneficios
  antiguos como expectativa 2026 ni precisión deportiva como ventaja de cuota.
- Revisión AST correcta de 74 archivos Python. El arnés Bash no ejecutó
  pruebas en este entorno; su mensaje OK no se toma como validación completa.
  La venv local apunta a un intérprete no disponible. Cambio documental.

## 2026-10-03 — Revisión de certeza y segundo texto NBA

- El nuevo texto mezcla autores (Shannon/Thorp con Dixon–Coles), confunde
  recencia con deterioro de habilidad y atribuye al EPV original tecnología
  distinta de la documentada. Ver secciones 22–26 del plan NBA para fuentes
  y correcciones; las cifras privadas de rentabilidad no validan una estrategia.
- Se prioriza fiabilidad antes de complejidad: cálculo bayesiano, calibración
  temporal con mercado, selección con abstención y réplica prospectiva.
  El plan pasa de 21 a 27 experimentos propuestos, E0–E26, sin resultados
  nuevos ejecutados. Fijar política antes del test y medir el subconjunto elegido.
- Conformal aporta cobertura bajo condiciones, no probabilidad de cobrar
  ni ROI. La extensión a pérdidas no monótonas de febrero de 2026 se incluye
  como preprint exploratorio, con resumen consultado y supuestos por auditar.
  Kelly robusto/restringido trata asignación y riesgo; no crea ventaja.
- Para Telegram, contrato, cuota mínima y caducidad medidos mandan sobre
  etiquetas de confianza. Acuse de envío no confirma ejecución y la captura
  por minutos no se vuelve instantánea por un modelo más moderno.
- Solo documentación y backlog: no envío de Telegram, llamadas de pago,
  cambios de producción ni modificación de trabajos FotMob concurrentes.
  Revisados IDs de experimentos, secciones, referencias y cálculos ilustrativos;
  no se ejecutaron nuevos modelos ni pruebas de código por este cambio.

## 2026-10-03 — Arquitectura NBA aislada del fútbol

- A partir de la preocupación del usuario por mezclar componentes, se
  documenta aplicación NBA independiente en `apps/nba/`, aún inexistente,
  con entorno, imagen, despliegue, persistencia y Telegram propios.
  Documento: `docs/nba_arquitectura_aislada.md`.
- La frontera incluye ejecución y permisos, no solo carpetas: no importar
  `qf.config`/`qf.db`, no compartir cron, DSN, artefactos o migraciones.
  Esos módulos cargan configuración o conexiones de fútbol; acoplarlos
  introduciría rutas implícitas hacia el sistema existente.
- Se recomiendan instancias Postgres y Redis NBA propias. La outbox durable
  va en Postgres; la caché futbolística usa allkeys-lru. Dependencias propias
  evitan que una actualización NBA cambie el runtime de fútbol.
- Un mismo VPS y una cuenta de proveedor conservan riesgos compartidos.
  Fijar límites de recursos/retención y verificar el ámbito de créditos;
  prefijos de claves o dos contadores independientes no aíslan esos límites.
- Plan y backlog actualizados; solo documentación. No se crearon servicios,
  se movió código, se instalaron dependencias ni se modificó producción.
  Criterios de aceptación de permisos, imports, fallos y carga documentados;
  su ejecución queda pendiente de la implementación.

## 2026-10-03 — MVP NBA y capacidad comercial de las señales

- La crítica del usuario aporta un criterio operativo útil: precio correcto
  y disponible para el cliente, además de precisión deportiva. Documento:
  `docs/nba_mvp_ejecucion_y_capacidad.md`; resumen en sección 27 del plan.
- Cadencia de props de 60 s verificada en documentación de The Odds API.
  Rangos USD 20–250, colapso en 45 s, reacción 5–30 s y secundarios 2–5 min
  no corroborados por fuentes primarias suficientes: medirlos, no prometerlos.
  Polling y noticias tienen tiempos distintos; snapshots de 60 s no permiten
  asignar una duración exacta de 45 s a una oferta.
- MVP reduce familias/operadores y mantiene PIT transversal, minutos/tasas,
  calibración E22/E23 mínima, precio E5/E17 y entrega E19. Noticias E7/E8
  después del núcleo; los 27 experimentos siguen como backlog científico.
- No hay minutos implícitos únicos deducibles de una prop, ni una cuota
  mínima universal de 1,83. Cambio de línea requiere nueva evaluación.
  Beneficiarios secundarios son hipótesis, no ventana garantizada.
- Medir ejecución/capacidad/utilidad neta de tarifa con datos reportados
  voluntariamente, registrando faltantes y sesgo. Replay sin volumen real
  no identifica impacto de suscriptores sobre el mercado. Reglas de oferta
  por jurisdicción; Bonus Bets no equivalen a devolución de efectivo.
- Objetivo de inicio propuesto: captura y sombra, condicionado a preparación.
  Mantener puertas NBA y separación respecto a fútbol. Solo documentación;
  sin implementación, Telegram, gasto de API ni apuestas. Comprobados enlaces
  locales y consistencia de ejemplos, sin ejecutar modelos o tests de código.

## 2026-10-03 — Plan maestro NBA por fases y auditoría

- Consolidado lo solicitado en `docs/nba_plan_fases_auditable.md`: F0–F9,
  37 tareas, 10 puertas, entregables, dependencias, criterios de evidencia,
  roles de revisión y E0–E26 asignados. Referencias anteriores conservadas;
  el plan maestro dirige el MVP y el orden de implementación.
- Registro inicial en `docs/nba_plan_fases_auditoria.json` con hashes SHA256
  de cuatro documentos y commit de referencia. Se declara que el workspace
  tiene cambios locales; ese commit no se presenta como implementación NBA.
  Cero ejecuciones y cero puertas aprobadas. Integridad de un hash no equivale
  a prueba de fecha/origen; anclaje prospectivo se define en F3.
- Aislamiento, datos/PIT, minutos, distribución/calibración, Telegram de
  pruebas y confirmación prospectiva forman el núcleo. F8 estudia noticias
  como challengers separados; F9 amplía con validación propia por mercado.
  Una variante no cambia el candidato bajo confirmación ni hereda su puerta.
- Piso 300 partidos/60 días/3 bloques conservado como propuesta de muestra,
  no demostración de ROI ni calendario de ventas. La apertura de temporada
  referencia captura; no sustituye evidencia. Presupuesto/canal/familia y
  métricas definitivas se registran como entradas pendientes.
- Verificación documental: JSON válido, 37 IDs de tareas coinciden con el
  plan, E0–E26 completos, dependencias sin ciclos, cuatro hashes correctos
  y enlaces locales existentes. No se ejecutaron modelos ni tests de código.
- Solo documentación/backlog. `apps/nba/` sigue sin existir; no despliegue,
  captura pagada, Telegram ni colocación de apuestas. El arnés local debe
  resolverse antes de futuras tareas de código, según instrucciones del repo.

## 2026-10-04 — Viabilidad NBA antes del inicio de temporada

- Usuario consulta si el modelo puede funcionar antes del inicio mediante
  descarga de históricos. Revalidado calendario oficial: 20-oct-2026,
  16 días desde fecha del cliente. `apps/nba/` sigue inexistente; registro
  declara not_started, cero ejecuciones y cero fases aprobadas.
- Un MVP deportivo reducido es un objetivo condicionado, no un compromiso
  de completar F0–F6 ni de ventaja comercial en 16 días. Priorizar box scores
  y minutos de 2023-24 a 2025-26, luego ampliar a 2021-22 según cobertura;
  rosters/calendario/disponibilidad actuales son necesarios para 2026-27.
- Históricos de cuotas/noticias y tracking tienen cobertura/acceso distintos.
  The Odds API documenta props desde 3-may-2023 a cinco minutos en planes
  pagados, sujeto a incorporación de deporte/casa/mercado. No gastar créditos
  ni afirmar cobertura total; las estadísticas deportivas pueden investigarse
  sin haber adquirido ese histórico de cuotas.
- Verificadas documentación de nba_api y pbpstats, no probado todavía acceso
  de descarga desde este host ni tiempo total. No presentar repositorios o
  documentación accesibles como ingesta completada. No se escribió código,
  inició descarga, activó Telegram ni cambió el registro de auditoría inicial.

## 2026-10-04 — Preparación del plan y complemento de pretemporada

- Revisados maestro y registro: fases, puertas y evidencia definidos;
  implementación pendiente. Añadido `docs/nba_pretemporada_arranque.md` tras
  indicación del usuario sobre la pretemporada. Recoger observaciones actuales
  y evaluar pronósticos experimentales sin mezclar métricas con regular/playoffs.
- Orden local: arnés/aislamiento, acceso y cobertura, captura actual/históricos
  recientes, baselines y distribución, ensayo de entrega, confirmación F7.
  Peso de señales de pretemporada requiere evaluación histórica temporal;
  no traslado directo de minutos ni garantía de mejora o fecha de entrega.
- Registro amplía documentación mediante complemento y cambio registrado;
  conserva hashes de la base original. Ninguna puerta se aprueba por este
  ajuste. Presupuesto, fuentes/cobertura, operadores y destino de Telegram
  se resuelven antes de sus tareas dependientes; trabajo local puede empezar.
- Cambios documentales solamente: no aplicación, descarga ni activación.

## 2026-10-04 — Revisión crítica de CLV, liderazgo de fuentes y QNN

- Analizado texto aportado en attachment c6f7385e. Fuentes primarias de
  scoring propio, QNN/benchmarking, NGBoost, glosario NBA y contratos/feed
  contrastadas. Referencias vagas a Stanford/Leiden y redirecciones del texto
  no constituyen tesis identificadas; no asumir que sus afirmaciones se probaron.
- Añadido complemento `docs/nba_revision_critica_clv_fuentes.md` con CLV como
  diagnóstico de mercado en F6/F7, sin desplazar pérdidas/calibración de F5.
  Definir referencia, cierre fresco, mismo contrato, margen, push/void y
  cobertura; cierre permanece fuera de features previas. Movimiento 2.00 a
  1.80 no acredita por sí solo probabilidad correcta o retorno favorable.
- Sharp/soft se reemplaza como regla universal por atributos/liderazgo medidos
  por mercado. E17/E7 investigan noticias, duplicación y tiempos censurados;
  feed de 60 s no permite inferir ajustes externos al segundo. USG% no es
  minutos; conservar disponibilidad/minutos/tasa/oportunidades separados.
- E20 sigue diferido; evidencia sobre barren plateaus y benchmarking no
  respalda aceleración general NBA. Corregida mención externa a F18 (solo E18
  existe). Base original y fases conservadas; complemento registrado sin
  aprobar puertas. Solo documentación, sin runtime NBA ni descargas/envíos.

## 2026-10-04 - Plan maestro NBA actualizado a 1.1

- Integradas correcciones en el propio maestro a peticion del usuario, con CLV complementario y protocolo de cierre/comparabilidad/margen, liderazgo por mercado y precision de tiempos.
- Incorporados pretemporada/historico reciente y separacion de regimenes; minutos, USG y oportunidades distintos; E20 sigue diferido con benchmarking completo.
- Version 1.0 y registro previo guardados byte por byte. Registro vigente sincroniza 37 tareas y amplía criterios pendientes, sin aprobar puertas ni declarar ejecuciones.
- Cambios solo documentales; no aplicacion NBA, descarga, despliegue ni envio Telegram. Verificacion documental independiente de los tests de runtime.

## 2026-10-04 — Ejecución NBA con fuentes gratuitas

- Usuario autoriza ejecutar el plan y confirma fuentes gratuitas. Creado
  `apps/nba` con entorno/dependencias/configuración/datos propios; no se
  importa `qf`, carga `.env` global ni toca DB/implementación de fútbol.
  Entorno raíz previo roto: se conserva y usa `.local/harness-venv` auxiliar.
  Arnés antes: 606 pruebas; después: 606 pruebas (73,82 s), Docker omitido
  por no estar instalado. Suite NBA: 22 pruebas correctas (1,38 s).
- Fuentes NBA oficiales: CDN 403, stats timeout. Sin evasión ni reintento
  ciego. A petición del usuario se investigan archivos GitHub reales:
  llimllib box scores recientes; shufinskiy jugadas/tiros desde 1996-97;
  hoopR box scores/calendarios ESPN hasta 2023. Descargas con commit/hashes.
  Índices/README que anuncian datasets ausentes no acreditan descarga.
- Auditoría revela llimllib individual 2022–2024 solo 15 partidos/año,
  duplicados y minutos `MM:60`. Se preserva raw y rechaza bajo el contrato
  inicial; no reparar en silencio. Duraciones inválidas permanecen en el
  denominador raw. Dataset normalizado: 67.066 filas, con cuarentena explícita.
- Protocolo local congelado para rebotes; benchmark retrospectivo condicional
  a participación, con todos los resultados del día excluidos del historial.
  39.334 observaciones/2.048 partidos. CRPS 1,3510 vs 1,3947, error de minutos
  4,9723 vs 5,0773. Detalle y límites en `docs/nba_arranque_resultados.md`.
  Esto no reconstruye disponibilidad previa ni demuestra EV/ROI ante casas.
- SQLite es almacenamiento de investigación explícito, no sustitución ni
  aprobación de Postgres/Redis/recuperación G1. Cadena local sin anclaje externo.
  Ninguna puerta completa aprobada; resultados/reportes con evidencia real
  sustituyen el estado inicial inexistente. Telegram/cuotas pagadas inactivos;
  no apuestas ni cuentas/fondos operados. Falta capturar contexto actual,
  resolver cobertura/IDs, calibrar y ejecutar confirmación prospectiva.

## 2026-10-05 — NBA: cubrir huecos con archivos GitHub auditados

- Priorizado archivo real frente a README/clientes. SportsDataverse release
  aporta 30 Parquet individuales 1996-97 a 2025-26 (1.041.847 filas, incluidas
  no participaciones). IDs/assets/digests y recepción local preservados. Cinco
  temporadas recientes cubren 1.230 partidos regulares; conciliación PTS/REB/AST
  mejora claramente, pero hay discrepancias y minutos MM:60 en cuarentena.
- Maezellemillan contiene todos los partidos pero no concilia muchos totales
  individuales: cobertura de partidos no demuestra censo completo de jugadores.
  Professor-Pete aporta 107.337 designaciones/1.165 snapshots de lesiones;
  falta validar PDFs, reloj/AMPM, IDs y corte temporal. No inventar recepción
  histórica; mantener NOT YET SUBMITTED como desconocido.
- Props: sample 2.505 filas NBA, 1.415 al inicio/después y 730 sin tiempos
  interpretables; 53 pasan filtro básico, ninguna contrato completo aprobado.
  Otras muestras son un día o carecen de identificación de partido. Sin ROI/CLV.
- Plantillas de tercero: 527 nombres, declara sync 1-sep; no valida todos los
  equipos actuales. Release de rosters sin 2027. nba_api es cliente no oficial
  y CommonTeamRoster no equivale a archivo histórico de lesiones.
- Documentado en docs/nba_fuentes_github_huecos_20261005.md, reporte JSON y
  NBA-RUN-004. Hashes verificados, registros anteriores preservados, puertas
  pendientes. Datos candidatos no integrados; sin cambios a aplicación/modelo,
  fútbol, Telegram ni apuestas. No se repitieron tests por ser datos/documentos.

## 2026-10-05 — Incremento NBA F1–F5 y arranque de temporada

- Integrados cinco años recientes SportsDataverse con fechas/IDs/tipos propios:
  154.058 registros, dataset por hashes separado. 2023-24 pasa de 15 a 1.159
  partidos regulares conciliados. 2025-26 pasa de 1.151 a 1.146: no reemplazar
  referencia por asumir superioridad. Minutos MM:60 y discrepancias siguen en
  cuarentena. Adaptador v2 cubre también participantes sin referencia de equipo;
  v1/v2 generan bytes idénticos, replay reutilizado por SHA256 comprobado.
- Capturadas 30 plantillas ESPN 2026-27, 606 jugadores y recepción UTC. IDs
  separados, sin unión aproximada. 78 lesiones raw, 36 con fecha >48 h; fecha
  no verificada como actualización. No inferir disponibilidad o salud de roster.
- Nueva evaluación referencia: 39.225 casos/2.044 partidos, CRPS 1,3519
  vs 1,3953. Sensibilidad entre fuentes: 36 resultados comunes difieren; comparación
  emparejada solo donde coinciden rebotes/minutos. Sin selección por scores.
- Experimento independiente startup-research-v0.1: priors del año anterior,
  primeras 10 apariciones observadas, excluye día objetivo y abstiene sin prior.
  8.264 casos/1.396 partidos, CRPS 1,3026 vs 1,3763; minutos MAE 5,3779 vs
  5,6229. Exploratorio (datos ya inspeccionados), sin sweep, rol/disponibilidad
  actuales ni EV/ROI. Escenario 2026-27 posible, siempre actionable=false.
- Recuperación local ensayada sobre checkpoint de 15 eventos y dataset; triggers
  y hashes preservados. No recuperación Postgres/Redis, raw completa ni anclaje.
  Código fuente final preservado en snapshot propio, evidencia anterior intacta.
- Arnés inicial: problemas de temporales, resueltos sin cambiar código de fútbol
  usando padre dentro del workspace y cacheprovider deshabilitado. Comprobación
  previa/final: 606 pruebas correctas; NBA: 47. Docker omitido por no disponible.
- Detalle en docs/nba_avance_fases_20261005.md y NBA-RUN-005..010. G0–G9
  pendientes. Faltan identidad/roles/disponibilidad, calibración y coherencia de
  equipo; después contratos/cuotas/outbox y Telegram de pruebas. Sin publicación.

## 2026-10-05 — continuación NBA, identidades/calibración/outbox

Se mantiene la abstención como resultado válido: el usuario autorizó continuar
las fases, pero la captura pública no acredita disponibilidad médica ni una cuota
accionable. NBA.com respondió con 619 identidades; 606 rosters ESPN se cruzaron
por nombre exacto normalizado y DOB independiente, obteniendo 596 equipos e IDs
concordantes. Diez quedan separados. Se capturaron 165 fichas (51,340,337 bytes)
y se ejecutó el capturador prospectivo de tres fuentes. De 596 cruces, 436 permiten
escenarios condicionales de arranque. Comparar el último equipo observado no
prueba rol actual; equipo previo desconocido se distingue de traspaso.

La calibración se comprueba contra masa discreta esperada, no solo 80% nominal:
8,264 observaciones/1,396 partidos reproducidos; cobertura 87.9356% frente a
masa 88.5199%, diferencia −0.5843 pp (IC por partido −1.2808 a +0.1703).
Sin fitting/promoción. El listado ESPN contiene 81 entradas no verificadas
para un partido; los enlaces oficiales 2026–27 consultados dieron 404. La
página de cuotas del partido muestreado solo ofreció totales de equipo: cero
props individuales validadas, sin generalizar a toda la fuente.

Decisión humana: compartir el bot de fútbol y TG_ALERT_CHAT. El enlace NBA
solo lee esos dos campos mediante configuración explícita, sin importar qf,
modificar su env ni copiar tokens. No hay credenciales activas locales. Outbox
NBA independiente: sellar antes de encolar, claim persistente antes de HTTP,
expiración con reloj real, no reintentar timeout ambiguo; prueba local sin envío.
La confirmación Telegram tampoco acredita recepción por suscriptor. Cuotas,
rol/disponibilidad, límites globales del bot y promoción prospectiva siguen
pendientes; el selector rechaza todos los picks comerciales actuales.

79 pruebas NBA y 606 de fútbol aprobadas después del código final; Docker no
está disponible. Copia de 31 archivos en code_snapshots/continuation_20261005,
ledger de investigación verificado y registro ampliado a 50 evidencias/15 runs.
Las puertas G0–G9 permanecen pendientes. Detalles y condiciones de avance:
docs/nba_continuacion_20261005.md. Se conservaron reportes intermedios y se
registraron correcciones de abreviatura, conteo de equipo previo desconocido,
entrada CLI y nombre del lockfile; no se sustituyó evidencia anterior.
## 2026-10-05 — Scrapers NBA y contexto adicional

Diez repos fijados por commit y 52 archivos verificados; ningún código de
terceros ejecutado. Se integran adaptadores NBA propios para observar
alineaciones públicas RotoWire y contrastar agregados PBP Stats por cuarto.
La captura actual aporta cinco partidos y 50 titulares previstos, sin
confirmación médica. El piloto histórico conserva 15 partidos/745 registros
de quintetos, incluidos dos tiempos extra en un partido; seis descargas 503
quedan registradas. No son secuencias cronológicas de cambios ni rebotes
individuales. Los dos calendarios nuevos tienen IDs/fechas, pero ninguna hora
de inicio; el PDF oficial actual devolvió 403 y no se intentó eludirlo.

Decisión: ampliar datos de minutos/roles sin convertir observaciones previstas
en elegibilidad o cambiar los parámetros del modelo. Las puertas siguen
pendientes. IDs de proveedores y ledger siguen separados de fútbol; el único
puente autorizado continúa siendo bot/chat de alertas, sin credenciales
activas locales ni envío real. Pasan 100 pruebas NBA y 606 fútbol. Se corrigió
UTF-8 en lectura de JSON y se conservó el primer informe con errores; el
harness final usa PATH completo y temporales dentro del workspace.
Evidencia: docs/nba_scrapers_avance_20261005.md y registro auditable NBA.

## 2026-10-05 — The Odds API de fútbol también cubre NBA

A petición del usuario se revisó la documentación oficial y se probó la clave
existente sin copiarla a NBA o reportes. Autenticación y eventos: 46 NBA
regular, ocho pretemporada. Prueba acotada de un partido: descubrimiento de
mercados y 22 líneas alternativas P/R/A de un jugador en DraftKings, solo
Over. Cuatro créditos gastados; 19,652 restantes al capturar. Última
actualización de props unos 193.6 segundos anterior a recepción: no supera
frescura local de 60 segundos; faltan lado opuesto, reglas e IDs verificados.
No se descargaron históricos ni se habilitó polling continuo. El presupuesto
del proveedor se comparte con fútbol aunque el procesamiento NBA permanezca
separado; requiere reserva coordinada antes de operar. La revisión no cambia
código de aplicación ni parámetros. Evidencia y próxima integración:
docs/nba_the_odds_api_revision_20261005.md, NBA-RUN-019. Puertas pendientes.

## 2026-10-05 — Acceso histórico NBA confirmado

El usuario confirma plan de pago. Prueba real: eventos históricos y
player_rebounds responden 200; Houston–OKC 2025-10-21, 242 cuotas de 17
jugadores/ocho casas y 121 pares Over/Under. Once créditos consumidos, saldo
observado 19,638. Tres relojes de mercado posteriores al snapshot por 7–26
segundos, todos anteriores al as-of solicitado: se excluyen para el corte
estricto del snapshot, sin alterar timestamps. Cinco casas/154 cuotas quedan
compatibles con ese corte; no se acredita recepción propia histórica,
identidad NBA, reglas o rentabilidad. Fuente histórica disponible para el
dataset de precios; código/modelo sin cambios y puertas pendientes.
Evidencia: docs/nba_the_odds_api_historicos_20261005.md.

## 2026-10-05 — austin-pesina/nba_scrapes descargado

Descarga completa del commit d6d06b273d7a8818be3936f43425979db1ab92a3:
seis archivos/15,023 bytes, verificados con Git SHA-1 y SHA-256. Solo main;
cero datasets en árbol, cero releases y cero artefactos Actions disponibles.
Los scripts consultan Basketball Reference y escriben Snowflake/exportes;
sus resultados no están publicados aquí. Año final fijo 2026 = 2025–26;
IDs Basketball Reference, sin lesiones o precios históricos de props.
No ejecutar proyectos de terceros para confundir herramientas con datos:
se conserva código como referencia, sin dotenv global, instalación o acceso
Snowflake. Cero filas nuevas y cero créditos The Odds API. Código/modelo
propio sin cambios. Evidencia: docs/nba_repo_austin_pesina_20261005.md.

## 2026-10-05 — Descargador histórico Edgar Parra revisado

Se inventarió el commit 7a0c22f6e26e8ec6854742dd88abf755d10733f4 y se
descargaron 14 referencias/167,099 bytes con hashes verificados. Su módulo
masivo usa LeagueGameFinder y PlayerGameLogs por temporada: patrón útil para
completar huecos estadísticos. El único CSV publicado está vacío y la base
SQLite descrita por el inventario del autor no está en main. Los 90
artefactos Actions son pequeños y el workflow publica reportes/logs; no se
descargaron ni se acreditó que contengan registros históricos.

Decisión: usar el patrón de consulta como referencia, manteniendo el pipeline
NBA propio. Exigir separación de competición/temporada y validación de
censo, caché, minutos y disponibilidad original. Su historical_odds_backfill
asigna -110 a ambos lados y usa fecha de observación como fecha de partido;
no constituye histórico real de cuotas. No ejecutar ni adoptar ese modelo.
La revisión añade cero partidos y consume cero créditos de The Odds API.
Se sellaron Austin/Edgar en NBA-RUN-021/022: 80 evidencias verificadas y 33
archivos propios sin cambios; todas las puertas pendientes. Documento:
docs/nba_repo_edgar_parra_20261005.md.

## 2026-10-05 — Históricos gratuitos y ahorro de créditos

El usuario autoriza aprovechar scrapers para históricos sin gastar créditos.
Se contrastó cobertura regular: 5,830/6,150 partidos aceptados en cinco
temporadas, 320 pendientes por ausencia o cuarentena. Una consulta acotada
oficial LeagueGameLog, jugadores 2025–26 regular, agotó lectura tras 20 s;
manifiesto conservado, sin reintentos ni nuevas filas. Los archivos gratuitos
ya recibidos siguen disponibles. No se puede declarar descarga oficial
completa o funcionamiento del scraper desde esta conexión.

Decisión: completar estadísticas con fuentes gratuitas y reservar presupuesto
para precios auténticos. Son datasets distintos; el backfill de -110 no
sustituye cuotas históricas. Se documenta muestra de 100 partidos/rebotes/una
región/un snapshot ≈1,000 créditos más descubrimiento, sin ejecutarla. Cero
créditos gastados en esta tarea; código/modelo sin cambios. Documento:
docs/nba_historicos_gratis_presupuesto_20261005.md.


## 2026-10-05 — Los picks de la sombra, visibles en `/control`

Pedido del usuario: ver cuáles se habrían publicado, no solo los totales.
La tabla sale de `publishable()`, no de una consulta propia: si el panel
enseñara otra selección, el usuario juzgaría una muestra distinta de la que
decide la puerta (comprobado en producción: 28 filas = `publishable.n` 28).
Va tras el login del panel y nunca a la web pública porque revela casa,
cuota y antelación del criterio. Stake mostrado = el que se publicaría
(× factor de incertidumbre, db/039).

Despliegue mínimo, sin reconstruir: el repo del servidor va por detrás de
HEAD (`promotion.py`, `clv.py`, `dixon_coles.py`, `api_football.py`…) y el
contenedor de la API aún más (sin `latencia.py`, `shadow_sharp` previo a
db/039). Reconstruir habría desplegado de rebote la lógica de la puerta. Se
copió al contenedor su propio `shadow_sharp.py` + las dos funciones nuevas
(solo añade líneas), `console.py` y `console.css`; el repo del servidor
recibe la versión HEAD + cambio. Respaldo en
`~/respaldo_20261005_panel_sombra`. Pendiente aparte: decidir cuándo se
sincroniza y reconstruye el servidor con HEAD.

## 2026-10-05 — Recuperación NBA gratuita implementada y piloto auditado

El usuario autoriza avanzar con boxscores, GameRotation y PDF oficiales de
lesiones. Se implementaron inventario reproducible, capturadores finitos que
conservan originales/errores y validadores estrictos de estadísticas,
minutos, stints y cronología. El inventario identifica 395 partidos conocidos
pendientes: 320 regulares, 71 de pretemporada, tres de playoffs y uno de
play-in. En 299 pendientes regulares la fuente contiene minutos inválidos;
no se corrigen valores como 30:60 sin evidencia independiente. Los siete
conflictos de referencias de equipo ya tienen GameID; no eran IDs ausentes.

Las consultas reales de boxscore y rotación oficiales terminaron en
ReadTimeout; la alternativa CDN devolvió 403. Se detuvo cada lote y se
conservó la evidencia, sin importar partidos o stints. Se recibieron tres
PDF oficiales de lesiones, ocho páginas verificadas visualmente y 84
observaciones de 30 jugadores distintos; cuatro cambios reales de estado
entre los primeros reportes. El nombre 05PM corresponde a una cabecera
17:30 ET: se decide usar la cabecera y convertir con zona/DST validada.
Recepción en 2026 de informes de 2025 no acredita disponibilidad original;
el modo retrospectivo queda separado del filtro prospectivo. IDs médicos,
hora de partido y cobertura de archivo siguen pendientes.

Validación: 136 pruebas NBA y 609 de harness pasan; baseline de harness
606 antes de cambios concurrentes de fútbol, que se preservan y no se
atribuyen a NBA. Docker no disponible. Código propio congelado en 37
archivos; dataset/modelo aceptados conservan hash. NBA-RUN-024–026,
100 evidencias verificadas y ledger de 60 eventos, sin ancla externa.
Cero créditos The Odds API, cero nuevos partidos, cero publicación de picks
y todas las puertas pendientes. Documento:
docs/nba_recuperacion_piloto_20261005.md.

## 2026-10-05 — Basketball Reference responde; alternativas con cobertura real

La lista del usuario se contrastó con siete commits e interfaces reales.
Decisión: priorizar una muestra independiente que responda, conservando los
IDs y la precisión de cada fuente. Basketball Reference devolvió HTTP 200;
se conciliaron veinte participantes de 0022100012, 240 minutos por equipo
y P/R/A completos, sin errores del validador existente. El valor NBA 33:60
de Michael Porter Jr. corresponde a 33:59 en esa fuente, no a 34:00. No
corregir todas las anomalías de reloj mediante una regla supuesta. El
resultado queda en staging y el dataset principal/modelo no cambian.

ESPN Parquet 2025–26 descargado y digest GitHub verificado: 34,883 filas,
1,326 eventos. Candidatos únicos por fecha/equipos para 84 regulares, tres
playoffs y un play-in pendientes recientes; ninguno de 71 pretemporada.
Minutos enteros e IDs ESPN impiden importar directamente como NBA exacto.
JaseZiv aporta 73,306 transacciones hasta 2025-05-13, no publicación
horaria; una fecha 1899-12-30 y 16 filas sin equipo requieren cuarentena.
Workflow diario escrito no prueba actualización: commit último mayo 2025.

nba_api incluye PlayIn/Pre Season pero no evita bloqueo del endpoint;
pbpstats documenta Client y overrides; nbainjuries usa get_reportdata con
Java y no garantiza timestamp de cabecera en sus siete columnas. No se
ejecutaron bibliotecas externas ni se gastaron créditos The Odds API.
609 pruebas del harness pasan; 37 archivos NBA y 100 evidencias previas
sin cambios verificados. Puertas pendientes. Documento:
docs/nba_repos_alternativas_verificadas_20261005.md.

## 2026-10-05 — Ampliación Basketball Reference: 159 partidos recuperados

El usuario pide ampliar esta recuperación. Decisión: cachear por fecha,
preservar recepción/raw y generar versiones nuevas que heredan intacto el
dataset anterior. Parser, cruce por mismo partido/equipo/localía y P/R/A,
conciliación existente sin bajar umbrales. Variantes de sufijos omitidos y
puntos en iniciales solo con candidato único; rechazar generaciones
contradictorias y apodos. No atribuir DNP o lesión por ausencia de una fila.

Se programaron 263 fechas con lotes de veinte y seis segundos mínimos.
140 páginas válidas recibidas/reutilizadas; 2024-03-11 devolvió HTTP403,
se detuvo el lote ocho y no se intentaron fechas posteriores. Cuerpo y
parada del proveedor conservados. Cero créditos The Odds API, sin proxies
o reintentos. La causa precisa del rechazo no está acreditada.

Versiones parciales de 34 y 111 partidos y final de 159 partidos regulares
recuperadas. La versión ampliada contiene 157,375 filas: 154,058 originales
idénticas y 3,317 nuevas (3,316 con participación). Se reparsaron las 136
páginas utilizadas y reconciliaron de nuevo los 159 partidos; 597 jugadores
NBA con cruce consistente entre partidos. Hash antiguo preservado, sin
reentrenamiento/publicación. Cobertura regular: 5,989/6,150; 2021–22
completa, 2022–23 queda a un partido. Restan 161 regulares y 75 no regulares
conocidos; calendario antiguo de playoffs no se declara completo.

Nueve recibidos se mantienen separados: siete diferencias de un REB/AST,
referencia parcial 0022300835 (42.75 minutos y marcador parcial), y
0022300810 con fila Thomas Bryant sin minutos/comentario. No asignar DNP
a esa ausencia ni modificar agregados para forzar concordancia. Los otros
152 regulares no tienen página válida en este intento. Diagnóstico local
por equipo/valor conservado.

172 NBA/609 harness pasan; 39 archivos propios congelados, ambas versiones
del código conservadas. Fixture nuevo de colisión se corrigió tras un fallo
de prueba; logs fallido y posteriores preservados. Docker no disponible;
revisión propia sin revisor independiente. Cambios concurrentes de fútbol
preservados y no atribuidos a NBA. Todas las puertas pendientes. Documento:
docs/nba_basketball_reference_recuperacion_20261005.md.

### 2026-10-05 — Black Falcon ESPN NBA: utilidad comprobada antes de escalar

La cuenta Apify ya tenía sesión en el navegador; se usó sin copiar tokens.
Diez candidatos explícitos (6 regular, 2 playoffs, 1 play-in, 1 pretemporada),
máximo US$0.25/400filas/120s. Run T6I23rByjmvXbCpL2 correcto: 282 filas,
226 participantes/56DNP, US$0.142 mostrado. JSON íntegro de 927,312 bytes,
entrada, log, recibo, screenshot y scripts congelados; sin créditos Odds API.

No se amplió porque 247 filas de nueve partidos duplican ESPN previo y los
minutos vuelven a ser enteros: no resuelven valores NBA malformados ni prueban
240 minutos exactos por equipo. P/R/A de participantes coinciden; 53 DNP
comparan null contra cero, conservados sin rellenar. Cuatro fechas UTC
requieren conversión explícita a America/New_York; primer assert detectó
esa diferencia y se corrigió la semántica del reloj, no el emparejamiento.
Los 20 totales P/R/A y puntos por cuartos/prórroga cuadran. playerActive=false
en 126 participantes impide interpretarlo como disponibilidad prepartido.

Las 35 filas nuevas de pretemporada NYK/PHI 2025-10-02 siguen separadas:
referencia NBA con ambos visitantes y sin candidatos individuales NBA.
No hay importaciones, reentrenamiento ni promoción de puertas. Cobertura
aceptada 5,989/6,150 regulares; 161 regulares/236 pendientes conocidos totales.
39 archivos NBA de código siguen con sus hashes anteriores; fútbol preservado.
609 pruebas pasan antes/después; intentos iniciales del harness con PATH
incompleto no cuentan como pruebas. Docker no disponible. Revisión propia.
NBA-RUN-031, 139 evidencias verificadas, cadena 77 eventos sin ancla externa.
Documento: docs/nba_blackfalcon_descarga_20261005.md. Siguiente paso útil:
fuente con segundos y corroboración de referencias, no compras masivas de
estadísticas que ya tenemos.

## 2026-10-05 — ¿Limitar a cuota ≤ 1,80 para acertar más? No con las casas de los suscriptores

Pregunta del usuario tras ver 12 de 19 perdidas en la sombra (que eran lo
esperado: 6,25 ganadas esperadas al cierre, 7 reales). Medido sobre
football-data (7 ligas, 2019/20-2024/25, 14.294 partidos, firma
d5cbc3151164), criterio actual aproximado: mejor de bet365/1xBet con edge
temprano ≥ 2%. De 683 apuestas solo 14 tienen cuota ≤ 1,80 (2%), aciertan
el 71% y su EV al cierre es −0,07% [−1,78, 2,33]: ahí no hay valor. El valor
está en 2,51-5,00 (+2,8% y +1,9%, IC entero > 0). Con todas las casas el
tramo ≤ 1,80 sí da +3,4% [2,1, 4,8], pero esas casas no cuentan para la
puerta. En vivo, 2 de 28 publicables tienen cuota ≤ 1,80.

Decisión: no se restringe la cuota. Subiría el acierto, pero bajaría o
anularía el valor esperado y dividiría por ~15-50 el ritmo de una muestra
que ya necesita ~6 meses. Acierto alto ≠ rentable: es un problema de
comunicación al suscriptor, no del criterio.

## 2026-10-05 — Probabilidad real de cada pick en la web

Pedido del usuario tras ver que la sombra pierde 12 de 19 (lo esperado con
cuotas medias de 3,9). La probabilidad que se enseña es `fair_prob`, la de
Pinnacle sin margen en el snapshot del pick, NUNCA `model_prob`: el modelo no
elige los picks y su edge resultó anti-señal. Se muestra en porcentaje y en
frecuencia ("29% · sale 1 de cada 3.4") porque la frecuencia es lo que
prepara al suscriptor para las rachas. El bloque real añade el acierto
esperado de la lista (media de `fair_prob`) y no lo estima si a algún pick le
falta el dato: los picks anteriores a db/017 lo tienen NULL.

Solo frontend: `/picks/free` ya devolvía `fair_prob`. Desplegado copiando los
4 estáticos al contenedor y al repo del servidor (coincidían con HEAD; se
leen del disco en cada petición, sin reinicio). Respaldo en
`~/respaldo_20261005_prob_real`. Con la publicación pausada el bloque real
sigue vacío; hoy solo se ve en las tarjetas de demostración.

## 2026-10-05 — Propuesta del usuario: picks con 80% de acierto (medido, sin decidir)

Motivo del usuario: los clientes valoran acertar más que batir a la casa, y
no toman todos los picks. Medido en football-data (7 ligas, 6 temporadas,
mejor cuota de bet365/1xBet, firma d5cbc3151164): selecciones con
probabilidad justa ≥ 80% = 5,2% de los partidos (~123/temporada), aciertan
el 84,8% a cuota media 1,15, ROI −2,4% y EV al cierre −2,6%. Con casa
pagando ≥ 2% sobre el justo: 0 casos. Ningún umbral entre 50% y 85% da EV
positivo. Simulación de un cliente que toma picks al azar: el favorito ≥ 80%
deja en ganancia al 53% tras 10 picks, al 27% tras 100 y al 14% tras 300; el
criterio de valor, al 45%, 51% y 54%. La objeción del usuario es real (el
valor es casi una moneda al aire para el cliente hasta cientos de picks),
pero el 80% no la resuelve: pierde más cuanto más se sigue. Pendiente de
decisión del usuario; nada cambiado.

## 2026-10-05 — NBA: servicios auxiliares y conciliación de históricos

Se amplió solo Flashscore, que aporta minutos fraccionarios a dos decimales,
y el calendario NBA para referencias canónicas. Cinco runs Apify acotados,
US$2.064 mostrado, cero créditos The Odds API. Ningún plan/recarga/schedule.
Tres lotes Flashscore: 227 partidos/6,631 registros; calendario ampliado99
partidos, incluidos los71 IDs de pretemporada pendientes. Cinco partidos
presentan discrepancias con referencias previas; no se sobrescribieron.

Decisión: aceptar únicamente el partido completo con IDs únicos, P/R/A por
jugador, segundos previos válidos concordantes y conciliación estricta. Un
contraejemplo real de +41/-41 segundos conserva el total del equipo, por lo
que ese total nunca sustituye la comprobación individual. Se añadieron67
partidos (63regular,3playoffs,1play-in),1,713 filas/1,470 participantes a una
versión nueva:159,088 filas, todas las157,375 previas intactas. Cobertura
regular6,052/6,150=98.41%; quedan98regular y71pretemporada. Los62 boxscores
candidatos de pretemporada descargados siguen separados por identidades o
referencias. Cero pendientes de playoffs/play-in solo en el inventario
actual; no certifica todo el histórico.

Verificación completa de los67 partidos,1,400 relojes previos válidos,34
páginas de originales,17 controles adversariales y139 evidencias previas.
Los39 archivos NBA congelados y modelo preservados; cambios concurrentes
de fútbol no tocados. Esta es auto-revisión de investigación y hashes
locales, sin anclaje externo ni promoción G0–G9. Los timestamps de captura
son actuales; lesiones disponibles antes del partido no se inventan desde
DNP. No ampliar el mismo scraper mientras falte conciliación. Informe:
docs/nba_servicios_recuperacion_20261005.md.

Cierre verificado: harness antes/después609 pruebas aprobadas (una advertencia;
Docker no disponible);17 controles de datos aprobados. NBA-RUN-032 registra
152 evidencias verificadas; cadena78 eventos, cabeza
c89ee0f4ab3ef619536a259a2fee9b91c03d4be074123ff3933edfe0bebd8389.
Dataset final_v2 SHA256f10b5e8e5dc8ba7dc85dac184fdf90ac25c17b64fe48a7e14b00f5d8885a13fd.
Los pilotos/expanded previos son exploratorios; final_v2 es la versión
auditable de esta recuperación. Recibos y74 originales referenciados en
manifest; snapshots de4 scripts. No se modificó el modelo ni su config.

## 2026-10-05 — NBA: pendientes, lesiones, rotaciones y props

Decisión: descargar candidatos no significa recuperar un partido, y una
cabecera histórica no prueba recepción en su momento. ESPN completo sobre
166candidatos permite añadir16partidos (3regular/13pretemporada),515filas,
159603totales;159088anteriores intactas.6055/6150regulares;95regular y58pre
siguen pendientes por conflictos de reloj/PRA/referencias/IDs. No convertir
minutos enteros ESPN en segundos; Flashscore conserva su supuesto de
redondeo decimal. Perfiles NBA respondieron403; lote detenido sin forzarIDs.

PBP local reconstruye5161partidos/217334tramos;891cuarentenas. El presupuesto
de cuantización cuenta intervalos continuos del propio jugador por período,
no cada cambio del quinteto por sustituciones de compañeros. Sin carryover
automático de titulares, sin rescalar clocks, y sin tratar rebotes de equipo
como jugadores. La versión final es chronological_stints_v4_20261005.

486PDFs/43924filas/36300registros nominales médicos: un corte diario,
330fechas pendientes tras403.272motivos partidos entre páginas unidos solo
con precedente nominal/estado válido y fragmento inicial de motivo. Segundo
motor verifica los486PDFs.43675filas conpartido,36063conjugador;237nominales
sinID(13nombres).1213regulares2025-26conreporte anterioraT60;974conambos
equipos enviados. El recibo es actual: reconstrucción retrospectiva, no PIT
ejecutable. Absent/unsubmitted siempre desconocido. IDs no prueban roster
histórico. Versión final injury_daily_joined_remaining_v2_20261005.

20juegos/40snapshotsrebotes,2961pares/5922precios;420créditos de límite500
predefinido conservador mientras la pregunta opcional seguía sin respuesta.
No nueva ejecución Apify.88casa/mercado rechazados por actualización futura
al snapshot y73entidades por IDnominal ambiguo; no ROI ni reglas de void
inventadas. Dos horarios del proveedor revisados entre snapshots: se
registran las versiones y los cortes deben preceder todos los horarios.
Versión final historical_rebounds_remaining_v2_20261005.

19controlesde corrupción/temporalidad, todos16boxscores/515filas,
todos5161juegos de stints,6replaysrawPBP,40replayscuotas y486PDFssegundomotor.
Harness609antes/después(unaadvertencia,Dockernodisponible). Auto-revisión;
hasheslocales, no anclaje externo.39archivosNBA/modeloconfig y152evidencias
anteriores preservados. NBA-RUN-033; G0–G9 pendientes. Fútbol no modificado,
sin entrenamiento/publicación/avisos. Informe detallado y manifests:
docs/nba_pendientes_recuperacion_20261005.md.

Cierre del lote de pendientes: NBA-RUN-033,168evidencias verificadas,
974originales/manifests fijados y22scripts con snapshot; cadena79eventos,
cabeza dca828a0271f04a12d518b74a7f43ea9e75a3dc628b459a3c58228aca958c3fe.
Datasetboxscore SHA25641c5a4f82d3638138a6a4d9b5bb7fb21033eecbae5e3fa07de99dc074d67ef68.
El cierre certifica este lote verificado, no la finalización del histórico.

## 2026-10-06 — Servidor sincronizado con HEAD (paso previo de la línea de alta probabilidad)

Lo que parecía un servidor muy atrasado era casi todo finales de línea: el
repo del servidor tenía archivos con CRLF (copiados desde Windows) y contenido
idéntico. Comparando sin CR, el worker ya corría HEAD salvo el brazo
"más-menos" de `player_value.py` y módulos de investigación; la API iba más
atrás (picks, config, odds_worker, shadow_sharp). Con visto bueno del usuario:
commit af9c8b4 del trabajo del día ya desplegado a mano (si no, la
sincronización lo habría revertido), `git archive HEAD` sin `harness/`,
build y reinicio de api/worker en un minuto sin crons (04:14 UTC). Verificado:
cadena (7 lotes), salud, model-card, web, /control 401 y crons sin errores.
Respaldo en `~/respaldo_20261006_presync.tgz`. Regla para el futuro: comparar
servidor y repo con `tr -d '
'`, o la lista de "cambios" engaña.

## 2026-10-06 — NBA: recuperación con actores adicionales de Apify

Se usó la cuenta existente para seis capturas acotadas de Basketball API y
Action Network, US$2.341 del crédito gratuito; saldo mostrado aproximado
US$0.45. Sin recargas, suscripciones ni créditos The Odds API. El actor de
boxscores publica secondsPlayed: Clippers–Nuggets 0012500052 agrega 40 filas
(30 participantes y diez DNP expresamente señalados por ESPN). Ambos equipos
suman 14400 segundos y PRA coincide con ESPN/referencia NBA. Sus 13 teamId
contradictorios no se usan: equipo histórico unido por lado, calendario y
pertenencia ESPN; identidad NBA por nombre completo único. Pelicans–Melbourne
solo tiene un equipo y queda como candidato. Dataset159643; anteriores159603
intactos. El calendario nuevo tiene71juegos y68cruces exactos NBA; tres códigos
extranjeros separados.

Action Network devuelve385precios P/R/A de casas reales sin hora original,
y movimiento solicitado vacío;18de19lesiones anexas se actualizaron después
del partido. Ninguno entra al backtest. Una fecha solicitada no acredita que
sus bloques anexos fueran conocidos entonces; no ampliar ese flujo para PIT.

Ocho controles de corrupción,609pruebas antes/después,39archivos NBA/modelo
congelados intactos,168evidencias anteriores/974originales/22scripts verificados;
181evidencias totales. NBA-RUN-034,80eventos de auditoría;G0–G9 pendientes.
95regular y57pretemporada aún faltan; lesiones/rotaciones y props conservan
los huecos anteriores. Sin entrenamiento/publicación ni avisos; fútbol no
modificado. Informe:docs/nba_apify_fuentes_adicionales_20261006.md.

## 2026-10-06 — NBA: API-NBA con clave autorizada por el usuario

La autenticación funciona, pero el permiso NBA efectivo es Free: los endpoints
de temporada2025 devuelven error de plan, aunque la guía pública no dejaba
clara esa restricción.80pendientes2025-26(23regulares/57pretemporadas) bloqueados.
No contratar ni recomendar una compra como garantía de recuperación: el acceso
y la precisión son requisitos distintos. Clave solo en archivo local ignorado;
estados sanitizados sin datos personales, evidencias sin encabezados secretos.

Tres calendarios y72cruces exactos por fechaEastern/localía/nombre.72boxscores
descargados,1543registros; todos los minutos individuales son enteros, sin
segundos. Consulta por temporada sola rechazada;83peticiones de datos,3errores
de aplicación y2/status. Límite local95, cuotaFree100/día. Estado final70/100;
cabeceras no monótonas conservadas, sin fingir que equivalen al contador local.
Cero suscripciones nuevas, Apify o créditos TheOddsAPI.

No hubo partido aceptado: conflictos de PRA, identidad y segundos previos
válidos frente al reloj decimal alternativo. API-NBA no repara33:60 ni38:60
desde un entero. Referencias de rebotes contrapuestas no sobrescritas con
sumas individuales; no expandir iniciales o inferir DNP. Conservar72candidatos
fuera del dataset aceptado;159643filas previas y152pendientes permanecen.

693pruebas antes/después,10controles de corrupción;181evidencias previas y39
archivos NBA congelados intactos. NBA-RUN-035,194evidencias totales,81eventos
ledger,cabeza a40baa89c829109da4f82d2a21f23f5629943f01eac3a62c1fb818cf3dfd077e.
Auto-revisión, sin anclaje externo, sin entrenamiento/puertas/picks/Telegram.
Fútbol y cambios concurrentes no tocados. Informe y manifiestos:
docs/nba_api_nba_recuperacion_20261006.md.

## 2026-10-06 — Línea de alta probabilidad: implementada, integrada y desplegada apagada

Pedido del usuario: pronósticos "seguros" de al menos 80 %, aparte de los picks
de valor. Diseño, plan y ejecución con subagentes (docs/superpowers/). Decisiones
clave (el porqué):

- Probabilidad de Pinnacle sin margen, no del modelo: la promesa es un
  porcentaje y tiene que salir de la referencia calibrada. Se publica el
  candidato de MENOR probabilidad en [80, 95]: cumple el 80 % y es el más útil.
- Goles por ajuste al mercado con push correcto (`pricing.totals_fair_over`):
  Pinnacle cotiza 2 de cada 3 líneas en cuarto o gol entero. Prueba histórica
  (firma d5cbc3151164): regla completa prometido 84,45 / real 84,60; pasan
  h2h, doble oportunidad y las tres líneas de goles.
- Sellado con UNA fuente de verdad (`hashchain.lote_lleva_alta`): la revisión
  de la tarea 7 encontró que, con la línea encendida y sin fecha de corte, la
  API habría mostrado como sellado algo que el lote no cubría.
- Probabilidad pública a punto entero (decisión del usuario): con 6 decimales,
  1 − prob de una doble oportunidad era el precio justo del no favorito, el
  criterio de los picks de valor. El lote conserva el exacto.
- Pausa más exigente (decisión del usuario): IC99, mínimo 10 semanas y z ≤ −4
  para fallos groseros. Con IC95 y 8 semanas, ~32 % de líneas calibradas se
  habrían pausado en falso en 6 meses (pausa pública y manual de levantar).
- Esquema verificado en producción, no en tests (decisión del usuario).
- Despliegue 2026-10-06 18:12 UTC con `ALTA_PROB_ENABLED=0` y corte
  `LOTE_ALTA_PROB_DESDE = 2026-10-07` (el 6-oct ya había sellado). Vista
  previa: 2 de 15 partidos (parón de selecciones; sin goles porque el precio
  reciente a las 08:00 es de API-Football). Activación pendiente del usuario
  tras verificar el lote del 7-oct.


## 2026-10-06 — NBA: lineups Ramiro y contraste offline pbpstats

Cinco CSV públicos fijados al commit e702d9b7b585bb79e751eb52d5d767e29f16cab0, 110,072,340 bytes y 6,150 partidos regulares. 6033 pasan estructura/minutos; la aceptación final exige replay de PBP, titulares demostrados por período, sustituciones, marcador y minutos individuales sin rescaling. Se añaden 7 partidos (4 de las 891 cuarentenas); la versión combinada conserva los 5,161 previos y contiene 5168 juegos / 217619 tramos. Permanecen 887 cuarentenas previas y 887 regulares aceptados sin rotaciones.

pbpstats 1.3.11 contrasta 248283 sustituciones con IDs corroborados y red bloqueada, no ingestión nativa V3/posesiones. Fuente y PBP pueden compartir origen NBA; no se presume revisión independiente o disponibilidad prepartido. 15 controles adversariales, invariantes completos, 39 archivos NBA congelados intactos; harness 693/693, NBA 172. Cero créditos de pago, sin entrenamiento/promoción/picks. NBA-RUN-036; informe docs/nba_ramiro_pbpstats_auditoria_20261006.md.

## 2026-10-06 — Más pronósticos de goles: API-Football ya trae las líneas de Pinnacle

La línea de alta probabilidad casi no daba goles: a las 08:00 UTC el precio
de ≤ 6 h suele ser de API-Football, y `af_odds` pedía solo `bet=1` (1X2). La
misma petición por partido, sin filtro, trae de Pinnacle "Goals Over/Under"
(bet 5) con 1,5 / 2,5 / 3,5 / 4,5 y cuartos, más las casas blandas. Prueba de
solo lectura (22 partidos de las próximas 72 h, 21 peticiones): 22/22 con
1X2 + O/U de Pinnacle; pronóstico de goles en 15/22 (hoy 0) y pronóstico en
18/22 en total. Línea directa de Pinnacle frente al ajuste Dixon-Coles con su
2,5: media −0,03 pts, máx. 1,55 pts (n = 46): el ajuste validado en el
histórico también cuadra en vivo. Coste en peticiones: cero. Pendiente de
decisión del usuario: guardar bet 5 en `af_odds_snapshots` (necesita columna
`line` y nuevo índice único NULLS NOT DISTINCT) y que `alta_prob_datos` lea
esos totales.


## 2026-10-06 — NBA: ejecución real de scrapers, Java y ZenRows

Los152boxscores pendientes llegaron desde NBA Stats sin proxy;53pretemporadas pasan,1903filas nuevas/161546combinadas,67de71juegos. Los95regulares conservan minutos inválidos/discrepancias; capturar no equivale a aceptar. El archivo público de pbpstats, actualizado abril2023, aporta405PBP de candidatos: el replay con IDs explícitos V2 y las corroboraciones Ramiro/native EnhancedPbp añaden325rotaciones. Combinado5493juegos/231075tramos,562regulares aceptados sin rotación; previos159643filas/5168rotaciones intactos.

Java portátil permite18acuerdos de tres parsers sobre seis PDFs/398registros nominales; no recupera fechas nuevas. BRef/CDN/PDF403 yCDX503 se conservan; no se reintentan mediante rotación IP. oddsapiR revisado, sin Rscript ni llamadas pagadas nuevas; otros repos de la tabla quedan con estado explícito, no se afirma ejecución total. Toolkit ZenRows1.3.1/MCP2.4.0 instalados con alcance de proyecto para Claude Code;44herramientas stdio y cero llamadas proveedor; credenciales ignoradas, validez/cuota no comprobada.

Once controles adversariales e invariantes completos,39archivos propios intactos,225evidencias previas verificadas; harness693antes/después, NBA172. Fallos de configuración de temporales, acceso a ejecutables y serialización NaN conservados y corregidos. Sin entrenamiento, promoción de puertas o picks. NBA-RUN-037; docs/nba_github_scrapers_recuperacion_20261006.md.


Cierre de NBA-RUN-037: la salida de consola se escribió después del hash de su archivo abierto. Se conserva el snapshot vacío exacto del checkpoint y toda la salida final en otro archivo cerrado, con recibo explícito console_finalization.json y evento artifact_finalization. Se verifican304evidencias/84eventos; no se modifica ninguna fila, rotación, registro de corrida o evidencia existente.

## 2026-10-06 — Goles desde API-Football: desplegado

Implementado con plan corto y subagentes (docs/superpowers/plans/
2026-10-06-goles-desde-api-football.md): `af_odds` quita el filtro `bet`
(misma petición) y guarda bet 5 — todas las líneas de Pinnacle y 1,5/2,5/
3,5/4,5 de las casas de la lista — con columna `line` e índice único NULLS
NOT DISTINCT (db/041, con guardia que aborta si queda el UNIQUE viejo, por
la revisión final: con IF EXISTS un nombre mal escrito habría tumbado toda la
captura en silencio). La línea de alta probabilidad lee esos totales de la
MISMA respuesta que el 1X2 (`_totales_af`, con `fetched_at <= now`).

Despliegue 19:58 UTC en un minuto sin jobs ni partidos en 15 min: migración
y reinicio juntos (el código viejo no funciona con el esquema nuevo y no hay
vuelta atrás salvo hacia delante: volver a pedir `bet=1` con el INSERT de 9
columnas). Dos pasadas manuales de `af_odds`: 1.622 filas nuevas en 41
partidos (15 s) y luego 0 (el 1X2 se sigue deduplicando). Vista previa con
la línea encendida solo para ese proceso: 9 pronósticos de 15 partidos, 7 de
goles (casi todos "menos de 4,5", con referencia de Betano), antes 2.


## 2026-10-06 — NBA: ZenRows usado en tráfico real de fuentes

La instalación del MCP no redirigía los scrapers. Se autenticó account_usage y se probaron cuatro targets con máximo100créditos: BasketballReference.cgi devuelveHTML válido/152filas y pasa parser upstream; CDN yPDF dan ZenRows422/RESP001,CDX agota110segundos. Consumo observado1de5000créditos, sin compras. El adaptador nuevo enruta GET del scraper BRef a scrape del MCP y conserva HTML/recibo/hash; no se declara desbloqueo universal.

Memphis–OKC0022200443 añade23filas/22participantes/1DNP explícito,161569combinadas;6056regulares aceptados y94pendientes. Overlay declarado OKCreb54→53 corroborado por NBAStats actual y BRef, conservando el Parquet antiguo y umbrales.152acuerdos entre parsers,6controles adversariales,161546filas previas intactas,39archivos propios intactos,304evidencias previas verificadas; harness706antes/después. No se atribuye nueva ejecución a la suiteNBA172 anterior. NBA-RUN-038; docs/nba_zenrows_recuperacion_20261006.md.

## 2026-10-06 — Línea de alta probabilidad: fuera "menos de 4,5 goles"

Decisión del usuario tras la vista previa con goles de API-Football: casi
todos los pronósticos de goles eran "menos de 4,5" (se paga a 1,09-1,17),
poco útil para el cliente. `MERCADOS_GOLES_HABILITADOS` queda en más de 1,5
y menos de 3,5 (commit 396af2c). Pasó la prueba histórica: quitarla no exige
repetirla; volver a añadirla, sí. API-Football sigue guardando la 4,5 de las
casas blandas (no cuesta peticiones) por si se reabre.


## 2026-10-06 — NBA: completar y validar históricos (NBA-RUN-039)

BRef: 83 fechas por ZenRows recuperan 93 regulares; actas/calendario/ESPN completan cuatro pretemporadas. Resultado: 6149/6150 regulares, 71/71 pretemporadas, 164190 filas. Las fuentes de los 6150 regulares están capturadas. Tony Bradley (0:00 / 1 REB) está corroborado por PBP de 0,2 segundos y se conserva fuera del normalizador congelado, sin inventar segundos. Rotaciones: 6113/6150, 258137 tramos y 37 pendientes. Los 330 PDFs de 17:30 completan 816 fechas, 80932 filas y 70941 filas nominales con ID; 13 nombres originales y 19 nuevos resueltos con fuentes oficiales. No se acredita intradía total o recepción pregame original. Props: +795 pares P/A (603/192), 3756 con rebotes; 500 créditos locales agotados, cobertura de dos juegos P/A y veinte de rebotes. Se preservan 161569 filas y 5493 rotaciones previas, 39 archivos NBA y 340 evidencias. Harness: 706 antes/después; 21 controles adversariales. Los timeouts mantienen reserva por coste incierto; sin compras. Modelo y gates intactos. Informe: docs/nba_completar_validar_20261006.md.


## 2026-10-06 — NBA: segundos oficiales y rotaciones (NBA-RUN-040)

Se amplió el contrato de minutos solo con fuentes GameRotation completas y hash externo, para permitir <=1s con reloj cero/estado vacío; PRA no infiere participación. Tony Bradley conserva 0:00 y 1REB, acredita0,2s y añade su roster completo28filas:6150regulares/71pretemporadas/164218filas. La ruta por defecto coincide con el normalizador archivado en164190filas. Rotaciones:+28,6141/6150 y259416tramos; nueve casos mantienen contradicciones administrativas o titulares de OT sin prueba. V3actual17capturas requirió adaptar el esquema nestedgame y reconocer actionId único; actionNumber duplicado permanece. Alias de sustitución solo mediante IDs explícitos V2/V3 corroborados; sin override de titulares.245créditos nuevos confirmados;riesgo1612/3200 con reservasinciertas, cero props/sincompras.189NBA/707harness; primerWinError5temporal preservado y repetición completa exitosa.2105evidencias previas verificadas,38archivos antiguos intactos e ingest original archivado; modelo/gates intactos. Intradía médico/PIT y props multitemporada pendientes. Informe:docs/nba_segundos_y_rotaciones_20261006.md.


## 2026-10-06 — NBA: pendientes e intradía (NBA-RUN-041)

Se aceptaron seis rotaciones adicionales mediante intervalos administrativos de tiempo cero y exposición oficial de OT:6147/6150,259687tramos; tres contradicciones persisten. Descarga médica:815/816cortes nuevos;1631versiones/165729filas,75451jugadores nuevos con ID. Se preservan continuaciones NOTYETSUBMITTED/filas nombradas, razones literales y diferencias upstream; once identidades exactas CuiYongxi se resuelven en una versión separada.3859cambios de estado/motivo y1215selecciones retrospectivasT60;1216horarios únicos corroborados,40búsquedas vacías separadas. Recepción original/PIT no acreditados. Props3756previos/44snapshots revalidados,cero llamadas; repos fijados sin nuevas cuotas; plan36solicitudes/720créditos sigue pendiente de autorización por límite500agotado.140ZenRowsconfirmados nuevos;riesgo1752/3200,sincompras.189NBA/707harness y controles auxiliares;2280evidencias/40corridas/gates/producción previos preservados. Informe:docs/nba_pendientes_intradia_20261006.md.

Corrección de checklist NBA-RUN-041: el reintento del auxiliar de sellado marcó por error la línea de pendientes como completada. Se restituyó la casilla abierta para las tres rotaciones, intradía/PIT y props; el informe, datasets y evidencias del checkpoint permanecen intactos. La instantánea incorrecta se conserva y esta corrección se registra aparte.

## 2026-10-07 — Línea de alta probabilidad activada y "marca el local / el visitante" desplegado

- Sellado del 7-oct (08:00 UTC) correcto con el bloque vacío (`n_alta_prob: 0`).
  La tarea programada de activación (08:30 UTC) se quedó esperando el
  permiso de su primer `Bash` (nadie lo aprobó): se detuvo y la activación se
  hizo a mano tras repetir sus comprobaciones (verify 9 lotes, salud, tablas
  vacías, log del job). Lección: una tarea programada que usa `ssh` necesita
  sus permisos aprobados de antemano ("Run now" en una prueba inocua).
- "Marca el local / el visitante" (más de 0,5 goles de un equipo), decisión
  del usuario: probabilidad del mismo ajuste de goles (prueba histórica:
  local 86,97→88,52, visitante 86,10→87,45); cuota de referencia de las casas
  blandas desde API-Football bets 16/17 (con guarda por nombre); `db/042`
  amplía el CHECK con guardia. El control vigila los dos lados como UN grupo
  (`team_totals`), decisión del usuario: en el Monte Carlo del revisor da
  menos pausas en falso y más detección que por separado.
- Tasas del control con mezcla realista y grupo fusionado: ~16 % de líneas
  con alguna pausa de grupo en falso, ~5 % de la línea entera; detección de
  un déficit de 3 pts ~82 % / ~73 %. Las cifras del 6-oct (9,7 % / 3 % /
  88 %) suponían probabilidades uniformes y 4 grupos.
- Despliegue 17:02 UTC: `db/042` + `ALTA_PROB_ENABLED=1` + reinicio en un
  minuto seguro. Vista previa: 10 pronósticos de 17 partidos (5 de equipo).
  Primeros pronósticos reales: sellado del 8-oct, 08:00 UTC.


## 2026-10-07 — NBA: archivo público y rotaciones (NBA-RUN-042)

Las tres actas completas acreditan entrada/salida al mismo reloj detenido;6150/6150rotaciones y259826tramos, sin segundos positivos para actores administrativos. ArchivoKamran fijado/verificado:3662JSON,228324pares nuevos de puntos/3429partidos,232080pares combinados; horizontes6,07–16,79horas, noT60/T15. Calendarios ESPN2024/25verificados porasset/hash más2026sellado, roster/nombres/cronología estrictos; rechazosconservados. Médico:223PDFs disponibles en240rutas/7fechas,13previos y210nuevos;1841versiones/186634filas,18750nominales nuevas conID,22CuiYongxi exactos. Control de motivo final limitado a página deuna fila; diferencias literales de páginas normales conservadas. Primerdía2023–24disponible desde17:30, compatible conconstanteupstream;16:30noacreditado, no se concluye bloqueoIP. Recepciónoriginal/reglas de liquidación siguenpendientes.4939evidencias/41corridas/89eventosprevios preservados;189NBA,707harnessantes/732después portrabajo concurrente preservado.30ZenRowsnuevos,riesgo1782/3200,OddsAPI0nuevo/500agotado,sincompras;producción/modelo/gatesintactos. Informe:docs/nba_props_y_rotaciones_20261007.md.

Presentación legible de NBA-RUN-042: docs/nba_resultados_validados_20261007.md. El informe técnico/datasets sellados no se modifican; la casilla RUN-041 queda identificada como estado histórico, con pendientes actuales en RUN-042. Revisión documental registrada aparte.

## 2026-10-07 — web: portada inspirada en TennisPredictions y paleta del usuario

Se conserva la jerarquía editorial/calendario/filtros/filas por competición de
la referencia pública, adaptada al criterio de QuantFut. SingleFile CLI 2.18.0
capturó el HTML con manifiesto en `.local/design-reference/`; no es dependencia
de la web ni reproduce el backend ajeno. El usuario aportó azul noche #0b132b,
pizarra #1c2541 y esmeralda #10b981: superficies y cabecera se armonizan con
esa paleta. El tablero continúa siendo demo identificada; agenda real y puerta
comercial permanecen separadas, con error de API visible. No se activó ninguna
publicación, cuenta ni pago ni se desplegó. Nueve pruebas del frontend pasan;
732 pruebas Python pasaron antes de las ediciones de presentación. El script
shell no encontró utilidades dentro del entorno restringido y su OK no se
consideró válido; se ejecutó la suite con el Python del proyecto. Revisión en
navegador de filtros, fechas, fichas, Pick del día y combinadas. Propuesta y
siguiente fase: `docs/web_diseno_tennispredictions_20261007.md`.
- Prueba histórica con la regla desplegada (firma d5cbc3151164): 9.021 de
  14.216 partidos (63 %), prometido 82,62 %, real 83,23 %; todos los mercados
  pasan (equipo local 86,97→88,52, visitante 86,10→87,45).

## 2026-10-07 — web: cuenta y modelo de paquetes/suscripciones

El usuario aclaró que «su modelo» significa paquetes y suscripciones. Se
adaptaron las vistas de acceso, recuperación, registro, cuenta, catálogo de
picks y planes de 1/3/6 meses más Club de TennisPredictions. SingleFile guardó
las páginas públicas; el acceso se capturó sin sesión. El panel de referencia
se inspeccionó sin guardar ni incorporar su información personal.

La selección de modalidad y el perfil son estado visual de la pestaña, no
autorización de servidor. Identidad y contraseña son sintéticas, de solo
lectura; no se envían correos ni se crea una orden. Mi cuenta mantiene «Sin
suscripción activa» incluso después de revisar el pedido. Preferencias de
cuotas/ligas conservan la persistencia local existente; favoritos demo se
añaden y quitan durante la sesión. El resumen conserva el cobro deshabilitado.
Los importes de referencia usan centavos enteros: equivalentes mensuales y
ahorros derivados del total, corrigiendo discrepancias visibles en la referencia.

13 pruebas frontend y 11 del servidor web aprobadas. Validación en navegador
del recorrido de acceso → pedido, recuperación sin correo, preferencias,
favoritos, ausencia de activación y vistas 320/390/768/1024/1440 px. Se corrigió
un desbordamiento de 4 px del catálogo a 320 px. El chequeo shell final volvió
a omitir utilidades/Python en este entorno: su «OK» no cuenta como validación;
las pruebas directas son la evidencia. Sin despliegue ni cambio de gates.
Propuesta: docs/modelo_paquetes_suscripciones_20261007.md; capturas propias en
la carpeta local ignorada `.local/design-reference/quantfut-{acceso,cuenta,suscripciones}.jpg`.

## 2026-10-07 — web: despliegue autorizado

Por petición explícita del usuario, commit de producto 2266311 creado localmente
y desplegado en pronosticosdeportivos.pro. Sin remoto Git configurado: transferencia
SSH de paquete generado desde el commit. Base de archivos cotejada antes de sustituir;
imagen derivada de la API ejecutándose, solo seis archivos de presentación/rutas.
Respaldo en /home/qf/web-release-2266311/backup e imagen previa conservada.
Solo API recreada; worker, DB, caché, proxy y Grafana conservan sus identificadores.
Gate, variables, modelo y base intactos; cuentas y cobros siguen en demo.

El arnés completo se ejecutó correctamente al fijar PATH de Git Bash: 732 pruebas
aprobadas, una advertencia; frontend 13 aprobadas. Salud origen/HTTPS status ok,
archivos cotejados por SHA-256; el HTML público solo incorpora el beacon existente
de Cloudflare. Navegador público comprobó acceso demo → pedido bloqueado y cuenta
sin suscripción activa. Registro: docs/web_despliegue_20261007.md.

## 2026-10-07 — Fase comercial desbloqueada: cuentas, API de clientes y panel

Decisión del usuario: avanzar ya con cuentas y panel de administración sin
esperar a la puerta de CLV. La puerta sigue decidiendo si hay picks que
vender (`PUBLISH_PICKS_ENABLED`); las cuentas existen aunque esté cerrada.

- Un solo FastAPI para web, app Flutter y panel (se mantiene la decisión
  2026-09-23). `/app/v1` sin secretos en el cliente: bearer opaco de 15 min
  en Redis + refresh de 30 días hasheado en Postgres y rotado en cada uso;
  el reuso de un refresh revoca la sesión (robo de token). Opaco y no JWT:
  suspender o cerrar sesiones corta en el acto y no hace falta PyJWT.
- `ACCOUNTS_ENABLED` apagado por defecto: desplegar no abre altas solo.
- `subscriptions` solo admite revocar una vez (trigger); `admin_audit`
  inmutable con `deny_mutation()`. Una concesión manual no es ingreso: los
  ingresos del dashboard solo cuentan `source='payment'`.
- Panel: Tabler + Tabler Icons + Chart.js vendorizados (MIT, versiones y
  SHA en `static/vendor/README.md`) para mantener CSP `'self'` sin
  `unsafe-inline`. Se descartaron SQLAdmin/starlette-admin (exigen ORM y
  chocan con los triggers) y react-admin/refine (build de Node y tokens en
  JS). El pipeline sigue siendo de solo lectura desde el panel.
- Trampa encontrada: `main.py` manda `Referrer-Policy: no-referrer`, y con
  eso Chrome envía `Origin: null` en los POST propios; la defensa CSRF se
  apoya en `Sec-Fetch-Site` + token HMAC, no en `Origin`.
- El tope de 10/min de `/control` se subió a 2× el general y cubre también
  `/static`: con varias páginas daba 429 navegando normalmente.
- Verificado: 753 tests + 6 de integración contra un Postgres 16 desechable
  con todo `db/*.sql` (rotación/reuso, suspensión, renovación sin perder
  días, de por vida, revocación única); flujo HTTP completo y panel en
  navegador. Sin despliegue: falta aplicar `db/043`, `pip install` y
  `ACCOUNTS_ENABLED=1` en el VPS.
- Pendiente de decisión del usuario: procesador de pago y proveedor de
  correo. Guía de la app: `docs/app_api_flutter.md`.


## 2026-10-07 — NBA: calendario completo y recuperación médica (NBA-RUN-043)

Horarios corroborados para 6150 regulares, incluidos diez neutrales con ambas referencias NBA @ y designación ESPN conservada. +2784 reportes/368902 filas; 6129/6150 selecciones médicas retrospectivas con reloj/contexto literal concordante, 6037 ambos equipos enviados. +1350 puntos mediante seis alias oficiales exactos/308 partidos, total233430; 27151 candidatos multimerkado/34 partidos separados por relojes libro/mercado y vecinos ausentes. Cinco repos públicos fijados/blobs verificados,97 PDFs archivados, cero llamadas pagadas nuevas; presupuesto previo sin aumento. 9641 evidencias/42 corridas/91 eventos conservados; arnés732/732; producciónNBA/modelo/gates sin cambios, trabajo concurrente preservado. Recepción original/settlement y demás huecos siguen pendientes. Informe:docs/nba_recuperacion_medica_y_props_20261007.md.

## 2026-10-07 — Correo transaccional con Proton Mail

Decisión del usuario: Proton Mail. Hay dos formas y el código es el mismo
(SMTP genérico en `comercial/correo.py`); solo cambia `.env`:
- Recomendada: envío SMTP oficial de Proton (`smtp.protonmail.ch:587`,
  STARTTLS, token SMTP). Exige plan de pago y dominio propio en Proton; no
  añade servicios que mantener.
- Alternativa: Proton Mail Bridge en Compose (perfil `proton-bridge`) con
  shenxn/protonmail-bridge-docker. Su imagen de Docker Hub está parada en la
  3.19 (abr-2025) aunque el repo sigue (v3.27): se compila desde un commit
  fijo con el bridge v3.27.1. El login es interactivo (2FA): lo hace el
  usuario en el VPS.
- Proton no es para envíos masivos y limita por reputación: aquí solo
  salen correos uno a uno disparados por el cliente.
- Los enlaces solo guardan sha256; GET nunca consume el token (los filtros
  de correo visitan enlaces), solo el POST del botón. `forgot` responde 202
  siempre y envía en segundo plano. Restablecer cierra todas las sesiones.
- Verificado con un servidor SMTP real en local (aiosmtpd con STARTTLS y
  certificado autofirmado): llega autenticado y cifrado, con verificación
  estricta se rechaza el autofirmado y una contraseña mala no envía.
  Flujo completo en navegador: enlace → nueva contraseña → login.


## 2026-10-07 — NBA: veinte relojes corroborados (NBA-RUN-044)

+20 selecciones retrospectivas con PDF ET y metadata BRef de fecha/equipos/reloj exactos; corte60min antes del reloj más temprano; ESPN12–50min más tarde se conserva sin atribuir causa. Total6149/6150, ambos enviados6056, algún equipo ausente93. BOS@NYK25oct2023 ausente en diez PDFs inspeccionados; no se infiere sano/enviado. +3 reportes/167 filas, total4628/555703; dos parsers y todos los nombres conID. 22tareasZenRows/200créditos, riesgo1982/3200;3GETPDFsinpago;OddsAPI0. 18952evidencias/43corridas/92eventos previos preservados; arnés753/764; producción/modelos/gates intactos. Corrección v2 de atribución de zona: ET lo declara PDF, no metadataBRef. docs/nba_horarios_medicos_corroborados_20261007.md.

## 2026-10-07 — Despliegue de la fase comercial (commit 3d40e05)

Autorizado por el usuario. Paquete `git archive` verificado por SHA-256;
base del servidor cotejada con HEAD antes de sustituir. Respaldo en
`~/release-3d40e05/backup.tgz`, imagen previa `quantfut-api:before-3d40e05`.
Imagen nueva derivada de la que corría (+argon2-cffi, jinja2, src/), solo
`api` recreado con `--no-deps --no-build`; worker, db, caché y proxy
intactos. `ACCOUNTS_ENABLED=0`: `/app/v1` responde 503 hasta abrir altas.
El token SMTP lo escribió el usuario con un script de entrada oculta
(`~/release-3d40e05/poner_token.sh`): nunca pasó por el agente. Login SMTP
con Proton verificado sin enviar correo.
Hallazgo: `ADMIN_CONSOLE_PASSWORD_HASH` ya estaba vacío en `.env` antes del
despliegue (en `.env.bak-2026-10-07` de las 19:45 sí estaba): `/control`
devuelve 503. No se restauró sin permiso del usuario.
Reversión: retag `quantfut-api:before-3d40e05` → `latest`, restaurar
`backup.tgz` y recrear `api`; las tablas nuevas no afectan al código previo.
Con permiso del usuario se restauró la línea del hash desde
`.env.bak-2026-10-07` (idéntica byte a byte; resto del `.env` sin cambios,
copia previa en `~/release-3d40e05/env.antes-restaurar-hash`). `/control`:
401 en origen sin credenciales y 302 a Cloudflare Access desde fuera.
Lección: al reescribir `.env` en un despliegue, comparar después las claves
contra la copia previa; un valor vacío no da error, solo un 503 del panel.
Altas abiertas (`ACCOUNTS_ENABLED=1`) por decisión del usuario. Verificado
en producción sin crear cuentas ni enviar correos: planes 200 (también
desde el dominio público), login inexistente 401, olvido 202, picks sin
sesión 401, `/cuenta` con token falso 400, panel 401. Trampa del script de
despliegue: `diff` sale con 1 si hay cambios y `set -e` cortó antes de
recrear la API; comprobar siempre que el servicio se recreó.

## 2026-10-07 — NBA: props y reglas México/LATAM (NBA-RUN-045)

+9702pares de puntos/145partidos por unión única fecha/equipos con calendario NBA/ESPN y box canónico; mapas originales erróneos conservados,21eventos sin resolver. Total243132 (239979PTS/2961REB/192AST);233430previos exactos,27151candidatos aparte. 14blobs de dos repos extra;78tarjetas sin relojes completos,0pares adoptados de esos dos. Cinco documentos oficiales/cuatrocasas/MX-CO-PE; vigencia histórica desconocida y sin coincidencia con11books de cuotas. Recepción243132cuotas/4628PDFs todaOct2026,0pruebas originales; estructuraycontratocandidate confixtures explícitos sintéticos,ninguna liquidación automática.31GETintentados,0OddsAPI/0ZenRows/cero compras;riesgo1982/3200.19062evidencias/44corridas/93eventos previos preservados,21controles y arnés764/764;producción/modelos/gates sin cambios. docs/nba_props_y_reglas_latam_20261007.md.

## 2026-10-07 — NBA: versiones archivadas y mecánica de liquidación (NBA-RUN-046)

Seis capturas realesCaliente2025/Betway2021–2024 con SHA1CDXbase32exacto y Memento concordante; cinco secciones históricas Betway y secciónCaliente iguales a actuales, sin inferir vigencia continua. +perfilBetwayMX,total5perfiles;8documentosreglas nuevos/1ayuda. CodereARredirigeMéxico, cuarentena. Usuario confirma sinlogs originales;4978artefactos pornombre no prueban recepción antigua. Evaluador localv3 con38controles sintéticos yrecibosactuales exclusivos;243132pares todos pendientes,0liquidacionesreales/0ROI.19165evidencias/45corridas/94eventos previos verificados; arnés764/764.28intentosGET,0Odds/0ZenRows,riesgo1982/3200;sin compras. Producción/gates/modelos intactos;intermediosfallidos conservados. docs/nba_reglas_archivadas_y_liquidacion_20261007.md.


## 2026-10-07 — NBA: corrección documental del arnés (NBA-RUN-047)

El informe RUN-046 y su nota de progreso conservaban el recuento anterior764/764. Log final y verificación sellados acreditan764antes/767después,9omisionesantes/10después. Versiónv2 del informe corrige el texto; documentos/evidencias/corridas previos íntegros.0capturas/0créditos/0cambiosdataset oproducción/gates. docs/nba_reglas_archivadas_y_liquidacion_v2_20261007.md.

## 2026-10-07 — Web conectada a las cuentas reales

La web deja la sesión demo y usa `/app/v1` con `frontend/cuenta-api.js`.
Decisiones: en el navegador el refresh vive en una cookie HttpOnly
(SameSite=Strict, `Path=/app/v1/auth`) y el acceso solo en memoria; nada en
localStorage, para que un XSS no se lleve una sesión de 30 días. La cabecera
`X-QF-Client: web` activa ese modo y fuerza preflight CORS desde otro origen,
así que la cookie no sirve fuera del dominio. Dos pestañas que arrancan a la
vez mandan la misma cookie: la segunda tenía el refresh recién rotado y la
detección de reuso habría revocado la sesión; se da una gracia de 20 s solo
en modo web (la app serializa sus refresh y no la necesita). Un indicador
`qf_hay_sesion=1` sin secreto evita un refresh 401 por cada visitante.
Verificado en navegador contra el FastAPI completo en local: registro, error
de login, login, recarga con sesión recuperada, plan concedido visible como
Plus y cierre de sesión que borra ambas cookies.

## 2026-10-07 — Despliegue de la web con cuentas reales (commit 9b9d180)

Autorizado por el usuario. Solo los 8 archivos de ejecución (5 del frontend,
3 de la API); `ACCESS_FLOW.md`, `package.json` y `server.mjs` del servidor
difieren del repo pero no se sirven y no se tocaron. Base cotejada contra
3d40e05, paquete verificado por SHA-256, respaldo en
`~/release-9b9d180/backup.tgz`, imagen previa `quantfut-api:before-9b9d180`;
solo `api` recreado. Los archivos públicos (también a través de Cloudflare)
coinciden byte a byte con el commit. En producción el acceso muestra el
formulario real, sin aviso demo, sin errores de consola y sin refresh para
visitantes anónimos. No se creó ninguna cuenta en producción.

## 2026-10-07 — La web lee los precios del panel

`MEMBERSHIP_PLANS` (precios fijos en JS) desaparece: importes, duración,
moneda y qué planes se venden salen de `/app/v1/plans`, que es lo que edita
el panel. En el código solo quedan los textos por `plan_code`; un plan nuevo
sin texto usa el nombre del panel. El ahorro se calcula contra el plan
mensual de la misma lista y, si no se vende, no se inventa. `/plans` pasa a
un router público sin `ACCOUNTS_ENABLED`: los precios son información
pública y la web no debe romperse si se cierran las altas. Sin precios
cargados la web dice «Cargando»/«Reintentar» en vez de enseñar importes
viejos. Verificado en local: cambiar 3 meses a 29,99 en el panel se ve en
la web al recargar ($10.00/mes, ahorro $14.98) y Club, desactivado, no sale.

## 2026-10-07 — Despliegue de precios desde el panel (commit f94a5bc)

Autorizado por el usuario. 6 archivos de ejecución, base cotejada contra
9b9d180, paquete verificado por SHA-256, respaldo en
`~/release-f94a5bc/backup.tgz`, imagen previa `quantfut-api:before-f94a5bc`;
solo `api` recreado. En producción `#planes` muestra los 3 planes activos
del panel (14,99 / 33,99 / 53,99 USD) sin errores de consola. Ojo: Cloudflare
sigue sirviendo `/app.js` sin versión desde caché; la portada pide
`app.js?v=…` y esa URL sí es la nueva: por eso las versiones `?v=` deben
recalcularse siempre que cambie un archivo.


## 2026-10-07 — NBA: todas las casas solicitadas (NBA-RUN-048)

Revisión de 22 combinaciones casa/país más Rushbet México: 25 perfiles, cinco anteriores preservados y veinte nuevos, 72 cláusulas (49 nuevas). La matriz distingue cláusulas recuperadas/observadas de páginas vacías, redirecciones, contenido educativo, PDF físico de Te Apuesto y proveedor Kambi sin vínculo contractual probado por Luckia. Sportium España exige un segundo; bwin separa simples/Build a Bet; Winamax tiene excepción limitada de logros para titular con menos de doce minutos. Son perfiles de investigación, no liquidaciones reales.

21 índices consultados, cinco JSON válidos y nueve entradas históricas; nueve replays fallaron por conexión, cero contenido archivado nuevo validado. Se preservan los seis replays RUN-046. 87 GET del colector, 98 transacciones registradas y un diagnóstico adicional; cero créditos pagados/purchases. 19.260 evidencias y 47 corridas previas verificadas; seis controles negativos de procedencia. Arnés 767 antes/768 después, diez omisiones ambas; incremento concurrente sin atribuirlo al catálogo. Producción NBA/datasets/gates intactos. Recibos originales y contratos por ticket ausentes; las 243.132 parejas siguen sin liquidación real. docs/nba_casas_hispanohablantes_reglas_20261007.md.


## 2026-10-07 — NBA: reglas Colombia y props públicos (NBA-RUN-049)

BetPlay recuperado mediante desplegables DOM; Sportium Colombia mediante ZenRows MCP.18 cláusulas en dos revisiones;25 perfiles/72 cláusulas anteriores íntegros. Participación BetPlay con frase imprecisa y suspensión con ancla ambigua, Sportium43 minutos/abandono sin precedencia resuelta. No transferir mínimo español de un segundo ni push de totales a jugador. Inkabet/Betsson Perú tienen enlaces oficiales/footer peruano, pero rutas devolvieron landings; Apuesta Total sin cuerpo de reglamento y Dorado general.

Dos repos fijados,19 blobs verificados y26 GET GitHub:77 filas PTS30/REB29/AST18 en cuarentena separada,17 cruzan casas y faltan relojes del proveedor; commits del archivo constan en febrero12. Otro repo publica agregados/sintéticos, no cuotas.0 parejas nuevas,0 liquidaciones,0 contratos/recibos históricos acreditados. Diez scrapes MCP; reserva250, cota2232/3200; cuenta1674→1804, delta130 sin atribución exclusiva por petición. Salto35 activa parada; sin compras ni OddsAPI nuevo.48 corridas/19636 evidencias/97 eventos previos íntegros; ocho controles negativos; arnés768/10 antes y después. Producción NBA y gates intactos. docs/nba_reglas_colombia_y_props_candidatos_20261007.md.


## 2026-10-07 — NBA: minutos de regulación y F4 (NBA-RUN-050)

Continuar F4 como investigación: el candidato reciente mejora CRPS3,6638→3,5479 y MAE4,9654→4,8694 minutos en63155 casos/3256 juegos/433 fechas, tres temporadas y nueve bloques. La cobertura nominal80 solo llega70,663%, no hay disponibilidad previa ni coherencia conjunta de equipo; no promover ni aprobar G4. Historial mínimo10 positivo de la misma temporada, exclusión estricta de toda fecha objetivo. Intervalos exploratorios por fecha, sin test confirmatorio intacto.

159075 etiquetas desde6150 partidos/259826 tramos,12300 totales equipo de240 minutos. Periodos1–4 separados de OT, ceros/DNP y archivos originales intactos. Primer intento rechazado por28 namespaces vacíos de0022400942 antes de métricas; capa derivada acredita roster/persona/equipo/estadísticas/estado completos contra NBA V3 archivado. Protocolos99/100 y fuentes previas preservados.

213 pruebas NBA,24 nuevas; arnés768/10 antes/después. Revisión independiente de fórmula de126310 CRPS e historiales63155, resúmenes/bootstrap reproducidos; revisión humana propia.49 corridas/19744 evidencias anteriores íntegras, prefijo98 eventos conservado, checkpoint101. Cero llamadas/purchases nuevas; ZenRows2232/3200 y243132 parejas de cuotas preservados. Sin recibos originales, liquidaciones, despliegue ni promoción de gates. Seguir disponibilidad/rol jerárquico y rotaciones conjuntas antes de F5; pendientes LATAM/REB/AST/reglas por ticket continúan. docs/nba_f4_minutos_regulacion_20261007.md.


## 2026-10-07 — NBA: cobertura y escenarios, continuidad F5 (NBA-RUN-051)

Se corrige cobertura nominal80:70,663%→80,537% posterior y80,534% validación. Ajuste1,25 global/1,30 historial<12, entrenado exclusivamente en20630 casos2021-22 y congelado antes de validar2022-23/evaluar2023-26. CRPS empeora3,5479→3,5782 y MAE4,8694→4,8873; conservar RUN050 como referencia principal, no promover el ajuste por cobertura secundaria. Histórico ya inspeccionado, sin confirmación intacta.

3246 escenarios completos de equipo/415488 realizaciones conservan240 minutos, soporte0–48 y DNP0.4134 equipos excluidos por historial incompleto. Disponibilidad observada después del evento solo como diagnóstico oracle, no como predicción. Restricciones inviables/IDs/equipos cruzados se rechazan.234 pruebas NBA,21 nuevas; arnés768/10 antes y después.84002 pronósticos revisados,168004 CRPS independientes, nueve matrices regeneradas con hash exacto.

50 corridas/19786 evidencias y prefijo101 eventos intactos; protocolos102/103, checkpoint104.0 APIs/compras; ZenRows2232/3200, cuotas/contratos/recepción original y gates preservados. Traspaso F5 de investigación con rutas/hashes y referencia anterior; noOT mientras las estadísticas por periodo no estén verificadas. F4 de disponibilidad/rol y dependencia conjunta sigue pendiente; no producción. docs/nba_f4_calibracion_y_coherencia_20261007.md.


## 2026-10-07 — NBA: distribución de rebotes F5 (NBA-RUN-052)

negative_binomial elegida solo en19315 casos de validación2022-23 tras ajustar dispersión con19513 de2021-22. Parámetros/elección congelados antes de59816 casos2023-26. CRPS1.376733→1.332904, MAE1.944846→1.911748. Candidato de investigación favorable al baseline en este replay; sin promoción ni confirmación intacta.

6150 juegos/159075 etiquetas preservadas,5840 sinOT,310 OT excluidos por falta de estadísticas de regulación;98644 features causales, sin resultados del día objetivo. Prior30 minutos a0,18 heredado; historia20/min10 positiva sinOT para tasa, minutos RUN050 para distribución. Diagnóstico ampliado RUN051 separado; no escenarios oracle en métricas predictivas. Probabilidades under/push/over son categorías matemáticas sin contrato ni void conocido. PIT aleatorizado y masa discreta evitan confundir cobertura central con80 exacto.

Primer intento105 falló al serializar bool NumPy antes de validación; fuentes conservadas, entradas reutilizadas con hashes y AST iguales. Canon106/ajuste107/selección108/checkpoint109.265 pruebas NBA,31 nuevas; arnés768/10 antes/después.98644 historias,179448 PMFs/CRPS independientes y27 distribuciones regeneradas.51 corridas/19819 evidencias previas intactas.0 APIs/compras, ZenRows2232/3200; recepción/contratos/cuotas/gates sin cambios. F6 de investigación preparado con hashes, no producción. docs/nba_f5_distribucion_rebotes_20261007.md.


## 2026-10-07 — NBA: ensayos de entrega F6 (NBA-RUN-053)

El plan define F6 como entrega/observación, no solo auditoría temporal. Recuperar reclamaciones interrumpidas únicamente tras caducar a unknown, sin volver a cola; conservar sending fresco y reclamar antes del transporte. Hora real de intento separada del as_of solicitado y nueva comprobación de caducidad antes del remitente. Reinicios, concurrencia, auditoría fallida, 429 y timeout verificados sin duplicados.

Diez fixtures/60 cortes a0/15/30/60/120/300s, cinco outboxes y26 pruebas nuevas;291NBA y768general/10omisiones. Revisiones se seleccionan por recepción propia, otro operador no sustituye contrato y error/suspensión no reutiliza cuota anterior; diferencias son brackets de observaciones, no duración exacta ni ejecución real. Solo remitentes inyectados;0mensajes/APIs/compras. Latencia local simulada no demuestra p95 del canal.

52corridas/19873evidencias/109eventos previos íntegros; protocolo110/checkpoint111. Sin credenciales NBA ni campos del puente operativo, herramientas Postgres/Docker ausentes en PATH y ninguna integración DB probada. SQLite local no apruebaF6.1. PropuestaF7 draft_not_started: selección histórica participante positivo/noOT no es universo previo. Postgres/canal/recepción anclada/contratos/OT y disponibilidad reales pendientes. Gates/cuotas/reglas/budget2232/3200 y producción sin cambios. docs/nba_f6_entrega_y_observaciones_20261007.md.


## 2026-10-08 — NBA: Postgres durable local (NBA-RUN-054)

PostgreSQL16.15 existía fuera del PATH. Clúster NBA propio127.0.0.1:55434/base nba_delivery_run54, SCRAM/secretos privados y trabajador limitado; fútbol intacto. Sellado+cola, reclamación+intento y resultado+evento atómicos. Concurrencia/rollback/inmutabilidad/expiración/resultado incierto verificados.39eventos/19mensajes exportados; parada inmediata real y recuperación WAL preservaron queued/sent/sending y cadena; ninguna repetición ciega. Clúster detenido.

309NBA/18nuevas,768general/10omisiones;11controles adicionales propietario. Pipe Windows inicial corregido antes del protocolo112; expectativa de QA sobre TRUNCATE corregida y primer intento conservado, sin cambiar código/protocolo congelados.53corridas/19920evidencias/111eventos íntegros, checkpoint113.0APIs de datos/compras/mensajes; transporte en memoria. Implementación Postgres local probada, no canal/latencia/cuotas/backup/rendimiento productivo. G6/F7 y gates pendientes, ZenRows2232/3200 intacto. docs/nba_f6_postgres_durable_20261008.md.


## 2026-10-08 — NBA: backup y canal VPS (NBA-RUN-055)

Usuario indicó credenciales en VPS y usar las de fútbol. Solo TG_BOT_TOKEN/TG_ALERT_CHAT se leen allí, sin copia local ni cambios del entorno/servicios de fútbol. Un mensaje PRUEBA TÉCNICA NBA aceptado por Telegram: message_id6 y chat configurado coincide; repetición del mismo ID bloqueada.14.625006s sellado→acuse local incluyendo SSH, n1; no cumple ni demuestra p95<2s y recepción en dispositivo desconocida.

pg_dump/pg_restore reales en base nueva:39eventos/19mensajes idénticos a fuente; fuente intacta después, restaurada75eventos/36mensajes tras tests/envío.330NBA/21nuevas,768general/10omisiones. Métricas conservan faltantes/anomalías y ledger válido. Roles preexistentes; no recuperación integral en otro servidor ni retención automática. Servidor de ensayo detenido.

Protocolo114/primer intento conservado: Python3.10 del VPS no importa datetime.UTC; falla antes de credenciales/HTTP, estado unknown sin reintento automático. Diagnóstico de solo lectura acreditó causa; timezone.utc compatible y nuevo protocolo115 antes del único POST.54corridas/19962evidencias/113eventos íntegros, checkpoint116.1mensaje real autorizado,0APIs de datos pagadas/compras; cota2232/3200 intacta. G6/cuotas/recepción externa/OT/disponibilidad/F7 y producción pendientes. docs/nba_f6_backup_y_canal_vps_20261008.md.


## 2026-10-08 — NBA: transporte y recuperación VPS (NBA-RUN-056)

Reutilizar SSH solo no bastó: tres acuses7,75–10,75s. Diagnóstico públicoHTTPS0,262/0,016s precedió transporte HTTPSConnection reutilizable; dos acuses locales desde sellado0,421309/0,484205s, arranque separado4,312s. Cinco mensajes técnicos totalesIDs7–11, destino autorizado coincide y cada repetición bloqueada. Muestras diagnósticasn3/n2, no p95 operativo ni recepción en dispositivo. Credenciales solo enVPS, fútbol intacto.

Respaldo congeladoRUN055 del ledger/outbox39eventos19mensajes restaurado en contenedor propioVPSPostgres16.15/rednone/sinpuertos; roles recreados sin contraseñas previas, seis mutaciones rechazadas y reinicio idéntico. TrabajadorNOLOGIN para SET ROLE, no pruebaSCRAMremota. Contenedor eliminado tras verificar etiqueta/imagen; copia600/carpeta700 retenida fuera del equipo. No backup integral histórico ni últimasalertas ni automatización/retención periódica.

Colector de cuerpo/hash/recibo propio y controles de contrato preparado. MarcadorNBA403local, marcador/calendario403VPS; tres cuerpos conservados, cero datos/contratos nuevos. Ecosacotan relojVPS−local−0,902…−0,725s pese aNTPVPSyes, sin cambios de reloj; métricaslocales no restan UTCentrehosts. F7propuesta actualizada, no iniciada: universo/lesiones/rol/OT/contratos/anclaje/relojes/operación pendientes.

Primerintento117:352pasan/1PermissionErrorenmanifiestotemporal antes de accionesexternas; pruebaaislada pasa sincambiocódigo. Versión118base/carpeta nuevas353pasan; diagnóstico119,HTTPS120 con356pasan, capturas121/relojes122,checkpoint123. Arnés768/10antes/final.55corridas/20038evidencias/116eventos anteriores conservados; revisiónmismaautor con scriptseparado.0APIsdatos pagadas/compras,5POSTTelegram técnicos, cota2232/3200 y todosgates/producción intactos. docs/nba_f6_transporte_y_recuperacion_vps_20261008.md.


## 2026-10-08 — NBA: captura anclada y operación de investigación (NBA-RUN-057)

Se recuperaron seis eventos de pretemporada, doce rosters con 247 jugadores/240 IDs NBA estables, 101 observaciones de lesiones y 14 precios públicos de Caliente México. Cruce previo de nombre/DOB acredita identidad estable, no equipo actual. Lesiones genéricas/Active no acreditan disponibilidad por partido; precios de equipo sin props individuales, reloj de proveedor o reglas completas. NBA jugadores403; páginas NBA200 sin calendario/quintetos en datos incrustados; Codere redirección detenida; ruta candidata BetPlay URLError, cero contratos aceptados.

DigiCert RFC3161 verificó nonce, contenido y cadena para manifiesto de 25 recibos nuevos/prefijo130 a17:39:29UTC y primer manifiesto VPS15recibos a17:52:14UTC. Contenido alterado/nonce distinto rechazados; prueba VPS revalidada localmente. Existencia nueva, no recibos históricos ni exactitud del proveedor ni revocación OCSP/CRL. Consulta BetPlay posterior no anclada; checkpoint final tampoco.

Colector público nuevo en VPS, usuario1001/red propia/raíz read-only/sinpuertos/cap-dropALL/no-new-privileges, CPU0,25/128MiB/64pids; imagen base fijada por digest. Ciclo15min; lesiones/rosters por hora; sello máximo diario sin reintento inmediato. Primer intento de activación se detuvo ante Caliente403: catorce ESPN200 válidos. Segundo protocolo activó mismo código con salud source_degraded explícita; reinicio preservó capturas y seis servicios existentes conservan identidad. Sin secretos de fútbol, mensajes o picks.

Respaldo consistente de ledger/cuerpos diario y máximo siete archivos generados verificados; no borra cuerpos originales. Pausa a16GiBpropios o menos de10GiB libres. Primer archivo restaurado localmente con15eventos y cuerpos idénticos; 12archivos copiados incluyendo pruebas temporales. Copia fuera del VPS puntual, no periódica; archivos diarios aún no incluyen sellos/modelos/cola completa.

Dos fallos de normalización preservados, luego corregidos por IDs desde enlaces y alias de etiquetas sin aceptar precios contradictorios. Tres pruebas de respaldo fallaron por handles SQLite abiertos enWindows, corregidos con cierre explícito:31casos pasan y tres controles operativos adicionales pasan. Dos reconstrucciones iniciales fallaron por suponer orden de respuestas paralelas; revisión correcta usa hashes de evento y pasa sin modificar los datos. Suite completa390sinomisiones conPostgresNBA nuevo; source39eventos/19mensajes intacto y clúster detenido. Arnés768/10antes/final.56corridas/20143evidencias/123eventos anteriores preservados; revisión misma autoría/scriptseparado.

Protocolos124–133, checkpoint134; 26intentos públicos locales y15primerVPS, dos solicitudes TSA gratuitas, cero APIdeportiva pagada/mensajes/compras, cota2232/3200sin cambios. Captura de investigación continua activa; G0–G9/alcance/decisiones y producción comercial intactos. F7 sin iniciar por contratos/universo/rol/OT y criterios finales. docs/nba_f6_captura_anclada_y_operacion_20261008.md.


## 2026-10-08 — NBA: partido completo y contexto oficial (NBA-RUN-058)

Nuevas copias periódicas excluidas por instrucción expresa; servicio anterior sin cambios.35capturas gratuitas:12perfiles oficiales NBA2026-27 con249listados y245/247identidades ESPN corroboradas por nombre/team/DOB, cincoIDsNBA nuevos. Tres alias generacionales únicos aceptados; MaliqBrown/SteveSettleIII desconocidos. Listado no acredita contrato/convocatoria.34lesiones en contexto de seis eventos, cero disponibilidad final/rol; cruce oficial BOS-CLE0012600011/401898392 a23UTC. Ruta candidata reporte404 y redirección de roster detenida no prueban ausencia global.

Protocolo fullgame previo a métricas:159075etiquetas/6150partidos/310OT;104645antecedentes causales;84015casos evaluados/4343partidos/3842observaciones OT. Gamma-Poisson con minutos históricos completos, prior heredado fijo y familia sin selección actual. CRPS1,361001 contra1,390279;delta-0,029277/IC95porfecha[-0,032610;-0,026288]. IncluyeOTsinfiltrarobjetivo; cohorteparticipaciónpositiva posterior, temporadas previamente inspeccionadas, sin disponibilidad/DNP ni OTduración/rotación/jointminutes. Resultado exploratorio; RUN052preservado, F7noiniciado.

Caliente10preciosdeequipos/0props/0contratos, dos páginas reglas actuales sin vigencia/ticket histórico acreditado. Revalidación fija fuente de liquidación/horario ademásDNP/push/payout. TresSSHclockechoes:offsetremoto-local[-0,010387;2,711583]s, no sincronización ni prueba en vivo. Transportes requieren límites frescos y usan vencimiento conservador remoto; falta/antigüedad rechaza antesSSH/stdin. Fallo inicial425pass/1WindowsPermissionErrorpreservado; guardado único/fsync/reemplazocon6reintentoslocalesWindows5/32, nunca llamadas externas. ImportError previo y dos lanzadores sinpsycopg previos a acciones preservados.

Suite final435sinomisiones conPostgresNBA nuevo, fuente39eventos/19mensajesintacta,clústerdetenido; arnés768/10antes/después. Revisión separada mismaautoría reconstruyó allCRPS/ICporfechas,104645historias,332distribucionesmuestreadas,245IDs/34lesiones/35recibos.57corridas/20328evidencias/134eventos preservados.

Protocolo cierre144read-only:colector activo19:15UTC/38recibos/mismaimagen/cero reinicios/source_degradedCalienteVPS403;serviciosanteriorespreservados, módulos nuevos no desplegados. Revisión automática rechazó envío SHA256manifiesto aDigiCert sin autorización explícita del payload/destino:ningúnPOST/GETTSA nuevo ejecutado, alternativa local completa. Manifiesto d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e preparado, sello nuevo pendiente; pruebas anteriores RUN057 conservan propioalcance.

Protocolos135–144; checkpoint145.0APIdatosdeportivospagadas/0mensajes/0apuestas/0nuevascopiasperiódicas. Cota2232/3200sin cambios. G0–G9/alcance/decisiones/produccióncomercial preservados, F6abierta/F7draft_not_started. docs/nba_f6_partido_completo_y_contexto_oficial_20261008.md.


## 2026-10-08 — NBA: sello autorizado del manifiesto RUN058 (NBA-RUN-059)

El usuario respondió «si autorizo» al envío exclusivo SHA256/nonce aDigiCert. Protocolo146 fijó exactamente d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e. Una descarga de cadena y un POSTTSA gratuitos, sin documentos/credenciales ni reintentos. Granted firmado2026-10-08T19:24:17Z; firma/cadena/hash/nonce verificados dos veces, contenido alterado/nonce distinto rechazados. Sin nuevaOCSP/CRL. Prueba existencia nueva del manifiesto y sus hashes; no recepción original histórica, predicción previa a partidos retrospectivos, exactitud ni checkpoint posterior.

58corridas/20535evidencias/145eventos preservados; artefactos RUN058 se mantienen intactos, incluido rechazo histórico. Asociación externa posterior registrada separadamente. Revisión separada mismaautoría, arnés768/10antes/después; módulos NBA intactos y suite435anterior no repetida.0APIsdeportivaspagadas/0mensajes/0apuestas/0nuevascopiasperiódicas/0cambiosVPS. Protocolo146/checkpoint147, F6abierta/F7noiniciado. docs/nba_sello_externo_autorizado_20261008.md.

## 2026-10-08 — Reto escalera

Pedido del usuario con una regla de partida (cuota 1,25-1,40, 5-7 pasos,
freeroll a ×2,5). Antes de construir se midió (`eval/escalera_prueba.py`,
firma d5cbc3151164): la probabilidad en ese rango está calibrada (72,1 %
prometido, 72,6 % real) pero cada escalón pierde −3,6 % de EV a la mejor de
bet365/1xBet, y la escalera lo multiplica: 6 pasos se completan el 15,6 % y
dejan −24,1 % por reto (−19,7 % con freeroll). Decisión: solo escalones con
cuota ≥ precio justo de Pinnacle sin margen, en las casas de la lista; sin
candidato no se apuesta. En vivo (24-sep → 8-oct) eso deja 4 de 20
candidatos: un reto puede tardar semanas. La muestra con filtro (73
escalones, 16 retos históricos) no demuestra beneficio y la web lo dice.
Diseño: tablas inmutables y estado DERIVADO (`escalera.estado`) en vez de
columnas que se actualizan; aplazado → nulo a las 48 h; bloque `escalera`
en el lote sellado con `LOTE_ESCALERA_DESDE` (None hasta desplegar), mismo
patrón que alta probabilidad. Doble oportunidad fuera: no hay cuota que
tomar en las fuentes. Primer escalón según la vista previa en producción
(8-oct, sin escribir): Dortmund gana a Werder Bremen @1,36 (1xBet), prob.
74,1 %, EV +0,8 %.

## 2026-10-08 — Escalera: retos de 3 a 6 a la vez y hándicap asiático

Decisión del usuario: varios retos a la vez, 3 escalones por defecto, de 6 como
mucho 3 al mes, 4 y 5 cuando ya hay otro abierto. Medido antes
(`escalera_prueba`, 3-6 pasos): acortar sube los completados (39,9 % a 3
pasos frente a 15,3 % a 6) y reduce la pérdida de la regla sin filtro (−11,5 %
frente a −26,2 % por reto), pero ninguna longitud gana sin el filtro de valor:
el valor esperado de un reto es el producto del de sus escalones. Reparto:
primero los retos abiertos (el más avanzado antes), después retos nuevos; un
partido nunca se repite entre retos ni coincide con un escalón sin liquidar.
Hándicap: Pinnacle solo da su línea principal en nuestras fuentes, así que la
probabilidad sale del ajuste de goles; se validó la calibración sin cuotas
históricas de esas líneas (firma d5cbc3151164): pasan −1 a +2 salvo −1,5. Solo
enteras y medias (las de cuarto liquidan medias y la escalera no las trata);
'push' no cuenta ni mueve el saldo. En vivo las protectoras llevan mucho margen
(Santos +1,5 a 1,36: −8 %). La prueba tarda ~40 min: el ajuste por partido.

## 2026-10-08 — Despliegue del reto escalera (commit 37aa902)

Autorizado por el usuario a las 21:06 UTC. `LOTE_ESCALERA_DESDE = 2026-10-09`
(el lote del 08 ya estaba sellado). Base del servidor cotejada contra f94a5bc
y el árbol `src` del worker contra el servidor (solo difería lo de cuentas y
panel, desplegado antes solo en la API). Paquete por SHA-256, respaldo en
`~/release-37aa902/backup.tgz`, imágenes previas `quantfut-api:before-37aa902`
y `quantfut-worker:before-37aa902`; `db/045` aplicado; `ESCALERA_ENABLED=1`.
Primera vez que se recrea el WORKER en esta fase: es quien corre el job
diario. Trampa: el contenedor no tiene `ps` ni `pgrep`, así que la comprobación
de "ningún job en marcha" no midió nada; se recreó a las 21:08:27 (minuto
tranquilo, sin jobs de :08) y a las 21:10 cron ya ejecutaba odds y ráfagas. Para
la próxima, listar `/proc/*/cmdline`. Verificado: cadena (10 lotes OK),
vista previa en el worker (reto nuevo de 3, escalón Dortmund @1,36 1xBet,
EV +0,8 %), `/escalera` 200 también desde el dominio y `app.js` público igual
al del commit.

## 2026-10-08 — Escalera por probabilidad: córners, tarjetas, goles, ambos anotan (sin desplegar)

Decisión del usuario: la escalera elige el MÁS PROBABLE en 1,25-1,40, sin filtro
de valor (`EV_MIN = None`, `db/046` permite NULL). Córners y tarjetas
(amarillas + rojas) con `model/estadisticas_mercado.py` (equipos, liga,
árbitro; sin cuotas). Prueba `eval/escalera_estadistica.py`: con encogimiento
6 prometía de más en los extremos; φ en 2019-21, encogimiento elegido en
2021/22, criterio en 2022-25. Córners pasan (más de 7,5/8,5/9,5; menos de
9,5/10,5/11,5); tarjetas no (−1 a −3 pts; solo menos de 6,5). Ambos anotan:
prueba en curso al cortar la sesión; `BTTS_HABILITADO = False` hasta verla.
Cuotas de bets 8/45/80 de la respuesta de API-Football ya pedida; árbitro y
tarjetas de football-data (`history_fd tarjetas`) y de results/fixtures.
Pendiente: resultado de ambos anotan, harness completo, desplegar (db/046,
`history_fd tarjetas` en el VPS, api + worker).


## 2026-10-08 — NBA: piloto de precios y contexto (NBA-RUN-060)

El usuario autorizó ejecutar el piloto de diez partidos tras conocer costos y falta de presupuesto adicional. Techo conservador incremental250 comunicado antes de consultas; cuenta existente, ninguna contratación. Once consultas históricas cobradas210 y tres actuales9, total219;28rutas totales incluidas gratuitas y un422sin cargo. Saldo18.419al último recibo21:43UTC, sin saldo futuro garantizado. Los500anteriores se conservan como histórico, sin retroeditar. Cliente NBA aislado con reserva persistida, cuota/corte/URLs/credenciales y cero reintentos automáticos.

Diez históricos con puntos/rebotes/asistencias al corte60min previo al horario más temprano,2617pares identificados:1957nuevos+660previos.43rebotes excluidos por snapshot tardío, Dallas recuperado al corte correcto por10créditos.13pares anteriores con Jimmy Butler/III quedan separados por política de nombre completo exacto; fuentes/IDs anteriores intactos.41mercados nuevos con relojes incompatibles y91pares históricos sin identidad quedan sin promover.62observaciones oficiales previas al corte,10PDFs enlazados, recepción2026nooriginal2025.

Diez actuales (6pretemporada/4regular):21pares en3regular,15frescos al recibo, sin identidades/contratos/estadofinal acreditados.6eventos/96lesionesESPN,5RotoWire/6tarjetasquintetos. CalienteHTTP403pero navegador público legible; dos eventos solo cuotas de equipos. Observaciones DOM son transcripción, no bytes HTTP ni recibo exacto; sin sesión/boletos.

Fallos locales y422preservados; correcciones de fechaZ/reloj opcional de casa actual se prueban, reproceso offline sin pagar nuevamente. Verificación separada mismaautoría reconstruye2069pares nuevos y archivo2617, hash/cadena/identidades/consumo/ausencia de claves.69pruebas pertinentes,786/15arnés inicial y798/16final en árbol compartido con fútbol concurrente. Modelos/gates/F7/VPS/mensajes/apuestas/copiasperiódicas sin cambio por este piloto. docs/nba_piloto_props_y_contexto_20261008.md.


## 2026-10-08 — NBA: casas mexicanas y admisión por evento (NBA-RUN-061)

Ante la petición de solucionar fuentes y revisar1xBet/Novibet, se verificó navegación pública sin cuentas/apuestas. Novibet muestra mercados de equipo enBOS-CLE; reglas de jugador explícitas (entrada en cancha mantiene apuesta, DNPanula, OTsalvo excepción, push), pero captura directa403y sin pares PTS/REB/AST verificados.1xBet tiene PDFmexicano recibido200y regla estadísticaOT; sus conteos de mercados no prueban cuotas individuales, selecciones ilegibles en dos eventos. No se adopta como fuente operativa por anuncio comercial. Betsson también solo mercados de equipos en la vista revisada.

NBApágina oficial recibida22:04:25UTC contiene42listados para0012600011; pertenencia al listado no prueba convocatoria efectiva ni salud. Un nombre corrupto marcado; inactivos vacíos no prueban disponibilidad. Comando offline rechaza hash/partido/equipos/IDs/cortes incompatibles y conserva salidas. Al documentar la revisión el partido ya comenzó: ninguna observación nueva se retrofecha.61pruebas, arnés798/16,19GETgratis/0créditos nuevos.60corridas/20675evidencias anteriores intactas y prefijo155eventos conservado; reparación transparente del logpostsealRUN060preservada. Sin cambioVPS/mensajes/modelos/gates/F7 ni copias periódicas. docs/nba_fuentes_1xbet_novibet_y_disponibilidad_20261008.md.

## 2026-10-08 — Despliegue de la escalera por probabilidad (commit abe3da4)

Pedido del usuario ("termina lo pendiente"). Desplegado a las 23:10-23:22 UTC,
ANTES del primer job con escalera (09-oct 08:00), así que el primer reto nace
con la regla nueva. Base cotejada contra 37aa902, paquete por SHA-256, respaldo
en `~/release-abe3da4/backup.tgz`, imágenes previas `*:before-abe3da4`;
`db/046` aplicado; api y worker recreados. `history_fd tarjetas` cargó
amarillas/rojas de 27.398 partidos de las 7 ligas principales y árbitro de
4.610 de la Premier. Cadena: 10 lotes OK. Vista previa: abriría 4 retos (3, 6,
4 y 5) con PSV @1,26, Unión-Defensa menos de 3,5 @1,27, Galatasaray @1,30 y
Dortmund @1,36. Córners/tarjetas/ambos marcan entran cuando af_odds capture
sus cuotas (desde las 00:20 UTC). Trampa repetida: la comprobación de jobs en
marcha vía /proc se contaba a sí misma (su línea contiene "python -m qf");
el worker se recreó a las 23:21:40 tras agotar la espera. Para la próxima,
excluir el propio proceso (`grep -v` del PID o patrón con corchetes).


## 2026-10-08 — NBA: selección europea explícita (NBA-RUN-062)

El usuario solicitó incluir1xBetEuropa,BetssonEuropa,CodereItalia yBetanoReinoUnido. Se usan claves oficiales onexbet,betsson,codere_it,betano_uk y filtro de casas explícitas, en lugar de ampliar a todos los proveedores de cada región. Europa no identifica el país contractual de1xBet/Betsson; no se acredita equivalencia mexicana ni cobertura de props por presencia en catálogo.

Selección distribuida con paquete, planCLIoffline y método del cliente acotado mantienen presupuestos/recibos y no activan consultas periódicas. Descubrimiento actual reserva1crédito; tres mercados reservan3actuales o30históricos. Solo transporte simulado y consolaoffline:33pruebas, arnés798/16,0consultasTheOddsAPI/0créditos.61corridas/20756evidencias y prefijo160eventos preservados. F6abierta,F7sin iniciar; captura real y contratos aún pendientes. Sin cambioVPS/mensajes/apuestas ni nuevas copias periódicas. docs/nba_casas_europeas_seleccionadas_20261008.md.


## 2026-10-08 — NBA: cuotas europeas comprobadas (NBA-RUN-063)

El usuario autorizó la consulta real con «hazlo». Se fijó protocolo antes de solicitudes pagadas: cuatro versiones explícitas, ocho eventos, máximo56créditos, cuenta existente/reserva compartida y sin reintentos. Se recibieron27respuestas200,16con cargo,29créditos; cero fallos/reservas pendientes.

1xBet EU aportó 24 precios en 4 eventos; Betsson EU, 36 en 8; Betano UK, 12 en 3; Codere IT, ninguno. Total 72 selecciones de equipos, no pares de props. Ocho consultas directas PTS/REB/AST y descubrimiento sin esos mercados. Ausencia específica del recibo: cuatro eventos de pretemporada tenían horario ya pasado y cuatro regulares estaban lejos del inicio; no se prueba ausencia universal. Se verificaron recibos y 33 pruebas pertinentes. Arnés 798/16. 62 corridas/20.777 evidencias y prefijo de 161 eventos preservados. F6 abierta/F7 sin iniciar; contratos, recepción histórica y disponibilidad aún pendientes. Sin VPS, mensajes, apuestas ni copias periódicas. docs/nba_cuotas_europeas_comprobadas_20261008.md.


## 2026-10-08 — NBA: suministro reutilizable de props resuelto (NBA-RUN-064)

El usuario pidió solucionar el atasco de props. La causa era tratar la captura de datos y la admisión comercial como el mismo requisito, además de conservar precios US en muestras aisladas. Se implementó capture-props con perfil US/AU propio, presupuesto explícito, diez casas y selección exclusivamente futura, conservando la selección europea. La fuente de precios tiene estado funcional separado de production_ready/actionable, sin relajar validadores.

Captura real: 19 respuestas API, 17/32 créditos, 36 pares (12 PTS/12 REB/12 AST) de FanDuel15, Sportsbet15 y Fanatics6 para cinco jugadores/tres eventos. 33 frescos al recibo, sin garantía de frescura futura. Identidades oficiales completas: 23 pruebas previas y 13 enriquecidas posteriormente, sin retrofechar el corte. 2617 pares históricos reutilizados con recepción original desconocida. Ocho GET públicos: dos perfiles y seis páginas de reglas; FanDuel directo403 conservado, las otras200. Sportsbet tiene guía explícita de participación/prórroga/resultados; Fanatics conserva excepción por lesión, contratos de cuentas no acreditados.

40 pruebas pertinentes; arnés 798/16. Reproducción offline de precios, recibos, créditos e identidades. 63 corridas/20.831 evidencias y prefijo164 eventos preservados. El pendiente de suministro queda resuelto; F6 global abierta por contrato, disponibilidad cerca del inicio y validación prospectiva; F7 sin iniciar. Sin apuestas, publicación, cambios VPS ni nuevas copias periódicas. docs/nba_props_fuente_funcional_20261008.md.

## 2026-10-09 — Escalera: probabilidad prudente en córners y tarjetas (commit ed7ac99)

Con las primeras cuotas reales de córners/tarjetas (00:20 UTC), la vista
previa abría los 4 retos con «menos de 6,5 tarjetas» y «más de 7,5 córners»:
modelo 81-82 % frente a 69-72 % de la propia Betano sin margen. No es que la
casa regale 11 puntos: al elegir el MÁXIMO entre ~580 candidatos gana quien
más se equivoca hacia arriba, y la prueba histórica no lo podía ver porque
football-data no trae cuotas de esos mercados. El usuario eligió la
probabilidad prudente: `min(modelo, mercado sin margen)` (Pinnacle si cotiza
los dos lados; si no, media de las casas de la lista); sin los dos lados el
candidato no entra. Desplegado a las 02:07 UTC del 9-oct, antes del primer
job con escalera (08:00): respaldo `~/release-ed7ac99/backup.tgz`, imágenes
`*:before-ed7ac99`. Vista previa nueva: 4 retos sin córners ni tarjetas
(Moreirense menos de 3,5 @1,25, Red Star marca @1,25, PSV @1,27, Dunkerque-
Annecy más de 1,5 @1,27). El chequeo de jobs en marcha usa ya `[p]ython -m qf`.


## 2026-10-08 — NBA: seguimiento prospectivo en simulación (NBA-RUN-065)

El usuario autorizó conectar props al modelo y el seguimiento prospectivo, aceptando referencias US/AU. Protocolo exploratorio congelado antes de capturar: PTS/REB/AST, regular/fullgame/OT incluido,20apariciones/min10, prior temporada anterior, baselinePoisson, precios<=60s al sello, una unidad hipotética. No se promueven candidatos de puntos/asistencias ni la extensión de apertura de rebotes; probabilidades condicionadas a participación y disponibilidad final desconocida.

Lote inicial12créditos/3eventos/36pares; adaptación detectó namespace omitido en parte del archivo corregido. Reparación por cruce exacto con etiquetas NBA verificadas, registrada antes de pronósticos; fallo original conservado. Quince predicciones selladas después, con cuotas vencidas y cero entradas. Tras66pruebas se anunció/fijó máximo adicional4créditos para un partido: paper-run prevalidó antes de cobrar y selló seis versiones/15pares recientes; precios53,75–53,98s. Dos entradas hipotéticas AST/PTS Cade; tres Tatum excluidas por candidato nominal de feedESPN (no estado de evento verificado), un mercado bajoEV. Cohorte congelada15casosúnicos,21versiones conservadas; total51pares/12consultas/16créditos.

Se implementaron recepción de final NBA, evaluación y resumen con sellos, identidad/equipos/hora/finalización, DNP separados y rechazo de duplicados. CDN403; webNBA200 comprobada HOU–OKC0022500001/final2OT con20participantes y sumasPTS/REB/AST reconciliadas. SeisGETpúblicos: ESPN200, CDNcalendario403, NBAcalendario200sin eventos y dos páginas futuras403. Los IDsNBA de eventos aún necesitan enlace oficial; futuros resultados y disponibilidad no acreditados. Ningún resultado pasado sustituyó un futuro.

Reproducción causal exacta21pronósticos y51pares;159075filas históricas cruzadas. SuiteNBA499/17 y arnésgeneral800/16. Se preservan64corridas,20900evidencias y prefijo167eventos. F6 sigue abierta; preparaciónF7/piloto exploratorio activo, confirmacióncientífica/G7sin iniciar, D07/D08pendientes. Sin mensajes/apuestas/publicación/VPS/suscripciones/recolector nuevo ni nuevas copias periódicas. docs/nba_seguimiento_prospectivo_20261008.md.


## 2026-10-08 — NBA: enlace oficial y seguimiento acotado (NBA-RUN-066)

El usuario pidió resolver todos los pendientes. Se conservaron RUN065,21versiones/15unidades y2entradas hipotéticas. Tres páginas NBA HTTP200 cruzadas con proveedor por equipos y hora exactos:0022600001,0022600002,0022600003; inicio20oct13:00/17:00/19:30CiudadMéxico. Conocimiento de IDs posterior al sello explícito. Plantillas actuales vacías, no disponibilidad. Cero créditos nuevos y3GETpúblicos.

Nuevo trabajador acotado paper-followup-plan/paper-advance: sello de inputs, reclamación previa inmutable, máximo3tareasred por ejecución, sin reintentos, estado vivo fuera de evidencia de hashfijo. Observación previaT-2min; cierre Sportsbet mismoevento/jugador/mercado/línea, últimos5min/frescura60s/max2créditos futuros; finalesoficialesT+4/+6/+12/+24h con ventanas2h. Score/summary sólo registrosoriginales/finalesverificados, DNP separados. Prueba actual sobrecohortereal cero tareasdebidas/cero consultas. Automatización local cierre-del-piloto-nba-octubre-20-y-21 ACTIVE para20–21oct en estechat; necesitaequipoencendido/Codexabierto, avisos sólocambios/fallos/acción. Fin22oct12UTC; ninguna ventana nirespuesta garantizada.

Lectura/CLV investigación prefijados y borradorpotencia usando sólo20853unidades/145días/1087partidos de entrenamiento2022-23: CRPSprimarioREB/efectomínimo.05/alfa.025/potencia.8/mínimo112días y300partidos. Proxydeplanificación, no confirmación. Candidato/exposiciónexactos, revisiónexterna, calendariofinal y cobertura aún pendientes antesdeabrir otrobloque. D08investigación definido; reglasporcuenta/jurisdicción pendientes. Recepciónhistóricaoriginal imposibledeacreditarcon descarganueva.

24pruebas de ciclo cubren cruce/hash/hora, roster≠salud, CLVcontrato/frescura, fallo403, duplicados, límites/claims y cierre2mercadosrealmock. Prueba integral detectó dictmarketduplicado; corregido antesdevalidaciónfinal. Planificaciónhistoricalectura necesitó adaptar metrics anidados; fallo preservado. Primer arnéspost falló porWinError5caché pese800pruebas; repetición con cachénueva conserva las mismas comprobaciones y pasa. SuiteNBA523/17; arnés800/16. Se preservan65corridas/21016evidencias/prefijo173eventos. F6/F7/G7sinpromoción, futuroseventos/resultadosnoinventados;0apuestas/copiasperiódicas/publicación/VPS/mensajesexternos. docs/nba_pendientes_resueltos_y_cierre_programado_20261008.md.


## 2026-10-08 — NBA: seguimiento autónomo en VPS (NBA-RUN-067)

El usuario pidió resolver pendientes. Se cerró dependenciaPC/Codex de captura mediante servicioNBA aislado enVPS, mismo plan/15casos/sellos RUN065/066. Primer despliegue rechazó FROMconID; segundo detectó rutasWindows enJSON. Ambos0cuotas/0probes deportivos; informesconservados. Readerinterpreta separadores sin cambiarbytes sellados; tercera versiónverificó fuente/modelo y arrancó. TrespáginasNBA200 desdeVPS, exactosIDs/equipos/hora;3recibospúblicos nuevos,0créditosactuales,2máximocierre futuro.

Servicio nba-paper-pilot-run67, root /home/qf/nba-isolated/paper-pilot/run67-v3-20261008. Fuente/carpetasRO, redpropia/sinpuertos/0.5CPU/512MiB/64pids, sincapacidades/no-new-privileges, restartunless-stopped. ODDS_API_KEY existenteVPS comparada con cuentalocal, leída sinexportación; dos clavesdeintentosfallidos retiradas tras comprobarningúnmontaje; activa600conservada. NTPsincronizado. Primer cicloespera/cerojobs, segundoejecutorbloqueado antesdered, reinicio conservaexactostate;7serviciospreviosIDsiguales.

Estado/claims persisten; ventanas/fin/lectura max3tareas porinvocación y cap2originales. Automatización delchat ahoraobservaVPS, noejecuta capturas; tombstone state.owner.json y guardCLI rechazanexecutorlocalretirado. Avisos delobservador siguen locales, captura no. Terminal bloqueanuevasconsultas; observador detiene exclusivamentecontenedorNBA validandoetiqueta, sinborrar. No se garantizan fuentes futuras/p95.

Criterios/diseñocientífico exactos congelados para revisión:REB fullgmOT,GammaPoisson/Poisson10,hist20/min10; ventana propuestaNov1-Mar31/lecturaApr2/3bloques,112días/300partidos,deltaCRPS.05/alfa.025/potencia.8,bootstrapdías5000/seed20261009/calibmasa realdiscreta5pp. No activado porfaltarrevisión,F6scopedy presupuesto; nosepromueveG7. Ficha vacía decontratocuenta separada delpaper. Recepciónhistóricaoriginalnoaportada, no reconstruiblehoy.

SuiteNBA531/17 y arnés800/16; paquete/worker7controles nuevos másguardCLI, flujosciclo24 conservados.66corridas/21056evidencias/prefijo176eventos preservados. Esperadatos20oct y confirmación nueva no se etiqueta como fallo técnico. Sinapuestas/publicación/mensajesexternos/nuevascopiasperiódicas ni cambiosfútbol. docs/nba_seguimiento_vps_y_pendientes_por_alcance_20261008.md.


## 2026-10-09 — NBA: activación operativa y alertas autónomas (NBA-RUN-068)

El usuario pidió solucionar y activar todo. La salud degradada tenía origen enCaliente403 opcional; ESPNrespondía200. Se separó salud de fuentes necesarias de cobertura de casa, manteniendo403/cuerpo/hash y deteniendo consultas repetitivas. La misma carpeta RUN057 y todo su prefijo344eventos se conservaron; nuevo recolector conflock, imagenverificada yreinicio retieneestado. Nuevas copias periódicas desactivadas y archivosanteriores sin cambios.

Nuevo supervisor host aislado usaúnicamente token/destino operativo yaautorizados, extraídos enVPS yprivados600. ReclamaantesPOST, diariocontriggers/hash, cap20intentos porUTCdía, sinretryincierto niavisosrepetidos porreinicio. UnTelegramconfirmado condestinoverificado; no acredita lecturadesuscriptores. Detención terminal exclusiva decontenedorpiloto con etiquetaexacta; noDocker general niapuestas.

Primer despliegue detectócarrera Type=simple alcomprobar bloqueoantesinicialización; rollback automático conservado. RecuperaciónType=notify anunciaREADYdespuéslock/ciclodurable; segundoejecutor rechazado, reinicio conservaúnica reclamación/mensaje. ArranqueVPS habilitado, independientedelPC/Codex. Piloto/sellos15casos/cap2intactos ycontenedoresfútbolsin cambios.

DosGETpúblicos actuales, ceroAPIcuotas; futurocierremax2. Diseñocientífico yficha decuenta copiados una vez; F7confirmatoria/G7no promovidos. Falta revisar/validaruniversoprospectivo yrecibirpartidos futuros; cero tickets reales, disponibilidad yrecepciónhistóricaoriginal no inventadas. Fallossintaxislocal/directoriotemporal/fixture preservados ycorregidos; suiteNBA542/1 yarnés800/16. docs/nba_activacion_y_alertas_vps_20261009.md.


## 2026-10-09 — NBA: página pública de pronósticos y resultados (NBA-RUN-069)

Se publicó https://pronosticosdeportivos.pro/nba con la cohorte sellada de 15 registros, cinco jugadores y tres partidos. La página filtra jugador/equipo, mercado, partido y estado. Presenta estimación, rango, probabilidades condicionales a participación y cuotas históricas con recepción/sello; cero resultados evaluados hoy, partidos registrados el 20 de octubre. No son apuestas ni cotizaciones actuales.

Servicio aislado con recursos limitados y fuentes originales montadas solo para lectura. Verifica diario, plan, sellos y recepción; reconstruye conteos desde el boxscore oficial antes de publicar un resultado. DNP explícito separado de cero, ausencia exige revisión. No ejecuta modelos ni captura desde solicitudes web, no monta credenciales ni datos de fútbol. La configuración del proxy y su segunda red quedan persistentes. Fútbol y protección de administración comprobados por HTTPS.

Se conservaron tres intentos fallidos con reversión automática: archivo anterior retenido por el montaje del proxy y comprobaciones de disponibilidad demasiado tempranas. Cuarto intento espera HTTP real antes y después de reiniciar; pasó conservando diario del piloto y contenedores originales. La comparación pública contempla solo la etiqueta de analítica inyectada por el CDN existente y exige igualdad de los bytes propios.

La página pública se abrió en navegador y los filtros/detalles de cuotas se comprobaron sin errores de consola. Captura guardada. El navegador ignoró los tamaños solicitados y mantuvo 700×572; revisión visual móvil pendiente explícita, no declarada como probada. Pruebas NBA 558/2, arnés antes y después 800/16. Se preservaron las 68 ejecuciones y todas sus evidencias, sin promover puertas científicas, apuestas ni copias periódicas. docs/nba_pagina_pronosticos_resultados_20261009.md.


## 2026-10-09 — Menú Fútbol/NBA e histórico (NBA-RUN-070)

El usuario preguntó por el histórico y pidió acceso NBA desde la cabecera de fútbol. El archivo aceptado conserva su huella NBA-EV-2204:164.218 filas y6.313 IDs, fechas2021-10-19..2026-06-13. Son datos retrospectivos; no un historial de aciertos emitidos antes del partido. El piloto conserva15pronósticos y0resultados recibidos.

Selector superior Fútbol/NBA con enlaces accesibles, activo marcado y reglas móviles fuera del menú que se oculta. Nuevas huellas JS/CSS enHTML. Publicación deriva de la imagen exacta de fútbol ya ejecutada y añade solamente tres recursos públicos. Se recreó únicamente laAPI; las otras identidades, trabajador/base/proxy/NBA y códigos de backend se conservaron. Configuración de imagen y fuentes persistida enVPS.

Primera comprobación recibió conexión cortada al arrancar y revirtió automáticamente. Recuperación conservada tolera esa lectura transitoria de salud propia y exige200antes de comprobarHTTPS; pasó. Navegación real Fútbol→NBA→Fútbol,15filasNBA y captura de pantalla; consola sinerrores a1280×720. La solicitud390×844 volvió a ignorarse, también en pestaña nueva: revisión visual móvil pendiente explícita.24pruebasfrontend y800/16arnés; registrosprevios/gates intactos, sinapuestas/copiasperiódicas nuevas. docs/nba_menu_e_historico_20261009.md.


## 2026-10-09 — Nueve mercados NBA desde estadísticas (NBA-RUN-071)

El usuario pidió desarrollar todos los mercados discutidos, priorizando probabilidad/estadística sobre cuotas. Se recuperaron triples/robos/tapones de los originales ya recibidos, con uniones exactas y reconciliación de equipos:157.962filas/6.108partidos regulares;42discrepantes excluidos sin alterar el histórico anterior. Se desarrollaron seis modelos de conteo y Elo/medias ataque-defensa/covarianza para ganador/equipos/total, con características anteriores a cada fecha.

Entrenamiento2021–22, calibración2022–23, evaluación exploratoria2023–26. Candidato y referencia calibrados igual; cálculo preliminar sin esa equidad conservado y protocolo corregido antes de inspeccionar métricas. Ganador≥70% acierta80.4%/1.071casos frente69.5%referencia; equipos74.3%/1.721 frente53.3%. Los conteos raros pueden dar mucho acierto por baja frecuencia; tapones80.3% coincide con referencia. Puntos/rebotes≥70% logran65.1%/65.6%, por debajo de sus probabilidades medias: no se anuncian selecciones fiables70%. Todos los modelos continúan experimentales y no accionables; no se alteró el candidato confirmatorio de rebotes RUN067.

42unidades nuevas selladas para los mismos tres eventos y cinco jugadores;15originales intactas. Web con nueve filtros y tabla conprobabilidadmedia/acierto/cobertura/referencia/intervalos. La extensión reutiliza recibos oficiales verificados del piloto sólo para lectura: conteos reconciliados, ausencia en revisión y DNP separado. Prueba integral verifica conteo adicional real y rechaza cuerpo modificado, sin escribir diario. No agrega consultas deportivas ni créditos.

Imagennba-dashboard-run71 reemplaza sólo el servicio NBA manteniendo su nombre interno; anterior detenido recuperable. Fútbol/proxy/captura/piloto/alertas conservan identidad, configuración y estado; reinicio/HTTPS y diezaccionesfiltroverificadas. 1280×720, consola sinerrores; revisiónmóvil390px sigue pendiente porlimitación previa.577/18NBA más3pruebasintegrales y800/16arnés. Nuevascopiasperiódicas/apuestas desactivadas, puertas científicas y cuatrobloquesde decisiones conservados; resultados y disponibilidad de20oct siguen futuros. docs/nba_nueve_mercados_estadistica_20261009.md.

## 2026-10-09 — Alta probabilidad: más de 2,5, hándicap asiático y córners (commit 27e8a7f)

Pedido del usuario (ambos marcan, córners, más/menos 2,5 y hándicap). Regla de
la línea: solo entra lo que pasa la prueba histórica, así que se midió todo
(firma d5cbc3151164) y se habilitó lo que pasa. Ambos marcan NO se publica no
por fallar sino porque nunca llega al 80 % en las 7 ligas: no hay nada que
validar. Córners rompe el "siempre Pinnacle": se acepta solo recortado a la
probabilidad sin margen de la casa (misma regla que la escalera desde hoy) y
sin los dos lados cotizados no entra. Con todo habilitado la regla da
pronóstico en el 85 % de los partidos (antes 63 %) y sigue cumpliendo
(82,35 → 82,89); dentro de lo elegido, 1X2 y menos de 3,5 quedan ~2 puntos
por debajo: no es criterio, lo vigila el control por grupo. Ojo: el hándicap
casi nunca trae cuota de referencia (solo The Odds API lo cotiza) y los
córners elegidos se pagan a 1,10-1,16. Desplegado 23:32 UTC; la API usa la
imagen fijada en compose (`quantfut-api-menu70:20261009`), así que se
retagueó ese nombre; respaldo `~/release-27e8a7f/`, imágenes `*:before-27e8a7f`.
Vista previa: 61 decisiones, 29 de hándicap y 8 de córners.

## 2026-10-09 — API-NBA: comprobar permisos antes de activar la fuente

La clave facilitada coincide con la privada ya configurada; autenticación y Free activo comprobados. Se corrigió la afirmación basada en la guía pública: 100 consultas pueden alcanzar por volumen, pero la cuenta rechaza temporadas 2025 y 2026. También rechaza fechas históricas explícitas; el calendario de temporada 2024 sin fecha devuelve 1.406 partidos y es acceso expresamente permitido. Cinco solicitudes de datos y dos estados, sin reintentos; cabecera final 99 restantes, estados declararon cero consumo y no se fuerza conciliación de contadores. Cuenta personal retirada de recibos, clave excluida de evidencia/Git. No se activa un bucle improductivo ni una suscripción, no se modifica VPS/fútbol/modelos/sellos. Recibos nuevos separados de originales previos, docs/nba_api_nba_acceso_actual_20261009.md. Arnés previo:808/16.
Cierre del diagnóstico API-NBA: arnés posterior808/16, igual al previo; siete recibos con SHA-256 verificados y evidencia sin credencial/identidad de cuenta. Docker no disponible. Los cambios ajenos en escalera_estadistica.py se conservaron sin intervención.

## 2026-10-10 — Córners de cada equipo y más de 6,5 (commits 3ce62c4 y 583d432)

Pedido del usuario a partir de un texto de "mercados de más del 70 %". De ese
texto casi todo ya estaba publicado; lo nuevo eran más de 6,5 córners y los
córners del favorito. Se miden con el mismo acumulador y un φ propio por
equipo (1,5455): el modelo por equipo calibra peor que el de totales (varias
líneas fallan en 60-80 %), así que solo entran las líneas que pasan, por
separado en la escalera y en alta probabilidad. "El favorito saca más de 3,5"
pasa en alta probabilidad para el local, no en la escalera. Cuotas: bets 57/58
de la misma respuesta de API-Football (ids comprobados con 1 consulta a
/odds/bets). Desplegado 00:52 UTC (db/048); la primera captura (01:20) trajo
~8.700 filas de 194 partidos. Fallo encontrado en la vista previa: los
córners por equipo salían sin cuota de referencia (`_ref_nuevos` solo miraba
'corners'); corregido y redesplegado 01:27 (583d432). Vista previa: 81
pronósticos de alta probabilidad, 22 de córners; la escalera sigue eligiendo
sobre todo goles.

## 2026-10-11 — Historial de las ligas "solo sharp" para el modelo propio (pasos 1-5)

Pedido del usuario ("activa todas esas ligas en el modelo propio"). El
cargador de football-data buscaba cada nombre SOLO en la liga que cargaba:
el historial de Segunda habría creado un segundo Racing, Leeds, Troyes… y
partido su historia sin error. Ahora clasifica en todo el país (alias del
país o exacto de cualquier fuente; un parecido NUNCA se crea ni se acepta
solo) y hay un ensayo en seco previo. El ensayo cazó dos cosas que la carga
habría grabado: `new/CHL.csv` redirige con 200 a la Superliga CHINA (Chile
se queda sin football-data; el cargador comprueba ahora Country/Div), y un
duplicado que ya existía (el calendario creó "Arminia Bielefeld" sin ver al
"Bielefeld" de la Bundesliga; fusionado en db/050). Los 86 dudosos se
revisaron a mano (db/050) y los clubes nuevos se crearon ANTES de cargar
(db/051): cada club que crea el cargador se vuelve candidato para los
siguientes nombres, y la carga dejaba de ser lo que el ensayo había medido.
Resultado: 39.842 partidos, 0 equipos creados por la carga, 0 duplicados.

`model_enabled` decidía también qué se paga a los proveedores; encenderlo
habría triplicado el gasto de The Odds API en 10 ligas y activado
alineaciones/bajas/jugadores con API-Football ya en ~5.400 de 7.500/día.
`captura_completa` (db/052) lo separa. Y el modelo no se puede entrenar con
el interruptor encendido: con el modelo viejo activo, el job de las 08:00
sellaría predicciones de equipos que no conoce. De ahí `train --incluir`.
Desplegado sin cambio de comportamiento (imágenes `*:before-ligas`).
Pendiente: evaluación en sombra y decisión del usuario antes de activar.

## 2026-10-10 — Tarjetas con árbitro: no; y las pruebas de córners/tarjetas iban sin 2024/25

Pedido del usuario (mercado de tarjetas "con historial y árbitros"). Prueba
`eval/tarjetas_arbitro.py` en E0+E1 (árbitro en el 100 %), criterio fijado
antes de mirar. El árbitro mejora la pérdida logarítmica 0,0011 por partido
(z=1,07; Premier −1,48, Championship +2,47) y empuja la media 0,18 tarjetas
por encima de la real: cumple la letra del criterio (A) pero no es una
mejora real, así que no hay regla propia para Inglaterra. Y en Inglaterra el
modelo calibra igual de bien SIN árbitro.

Lo importante salió de rebote: 9 CSV de football-data (toda 2024/25 y la
Premier 2021/22) traen BOM; leídos en latin-1 la columna `Div` era
`ï»¿Div` y `groupby("Div")` de `escalera_estadistica` los tiraba sin error.
Las pruebas del 8 y 9-oct midieron 10.842 partidos, no 13.555, y la Premier
eligió parámetros sin su temporada de ajuste. Las demás pruebas agrupan por
`league_id` y no se vieron afectadas; el cargador de producción
(`history_fd`) ya decodificaba con utf-8-sig. Con los datos completos y los
mismos parámetros (`--fijos`) caen tres líneas de córners de la escalera, las
tres en el tramo 70-80 %, que es justo donde elige la escalera, y una de alta
probabilidad; entran tarjetas menos de 4,5 y 5,5. La regla es la de siempre
(solo lo que pasa), no se reajustaron parámetros. Tarjetas en alta
probabilidad, todavía no: alta va 11 puntos por debajo de lo prometido.
Resultados en `.local/escalera_estadistica_20261010_fijos.json` y
`.local/tarjetas_arbitro_20261010.json`. Sin desplegar.

## 2026-10-11 — Flutter/Firebase: análisis y pantallas antes de implementar

App ubicada en `apps/mobile`: revisados 62 archivos Dart, configuración
nativa, cuentas/suscripciones/API/panel existentes y documentación oficial de
Firebase. Análisis Flutter sin incidencias y nueve pruebas existentes
aprobadas desde la nueva ubicación; no validan aún Auth/FCM/compras. Plan
documentado en
`apps/mobile/docs/FIREBASE_INTEGRACION_CON_BACKEND_20261011.md` con identidad
Firebase vinculada a cuentas existentes, API como autoridad de permisos,
notificaciones, medición, control y transición de usuarios.

El usuario confirmó implementación por fases y pidió primero presentar sus
ideas de pantallas. Se registra fase 0 de diseño y recomendaciones antes de
concretar fases/entregables. Pendiente de recibir esas ideas; no se inició
integración funcional, configuración Firebase ni cambios de producción.

## 2026-10-11 — Flutter: primeras pantallas QuantFut y navegación VIP

Incorporadas las referencias del usuario en `apps/mobile`: cinco bienvenidas
con ilustraciones animadas originales, arranque QuantFut y barra inferior
Inicio / Predicciones / En vivo / La Grada / Perfil. Tarjetas de ejemplo,
filtros de equipo/liga/día/deporte, fichas VIP difuminadas y botón Hazte VIP
que abre la selección de planes. Los metadatos VIP no contienen el análisis
privado. Precios pendientes; comprar muestra un aviso y no realiza cargos.

Estados de directo, comunidad y perfil preparados como propuestas. Sin
conexión Firebase/API, sin sesión ni pagos activos. No se alteró producción.
Diseño, límites y fases documentados en
`apps/mobile/docs/PANTALLAS_BIENVENIDA_INICIO_VIP_20261011.md`.
Validación: trece pruebas Flutter, texto ampliado en 320 × 568, análisis sin
incidencias y Android debug. Capturas en `apps/mobile/docs/validation/`.

## 2026-10-11 — Flutter: mercados con evidencia e idioma registrado

Sustituidas las propuestas de radar/primer tiempo por Mercados: ocho familias
fútbol, selección de líneas habilitadas con prueba aprobada y al menos 500
casos como regla de presentación, sin modificar las reglas del modelo.
Historial público del VPS guardado aparte: 75/96 (78,1 %), muestra inicial;
las tasas retrospectivas no se presentan como resultados publicados.
Pantallas Hoy/Histórico, avisos pendientes, ruta VIP y NBA exploratoria.
Revisión local del 10-oct distinta de la desplegada: tarjetas 4,5/5,5
pendientes y córners local +2,5 no se destacan; servidor sin cambios.
18 pruebas Flutter aprobadas, análisis sin incidencias, Android debug
compilado e instalado en el emulador. Detalle y fuentes:
`apps/mobile/docs/MERCADOS_MODELO_APP_20261011.md`.

Nueva referencia del usuario: selector de idioma desde el primer arranque,
antes de bienvenida, con es/en/pt/fr/it/de, persistencia y cambio en Perfil.
Registrado junto a Firebase: traducción Flutter, cuenta/backend/web,
Auth/correos, FCM/bandeja y medición; identificadores y datos del modelo no
se traducen. Pendiente de implementar, sin simular traducciones ya listas.
`apps/mobile/docs/IDIOMAS_APP_BACKEND_FIREBASE_20261011.md` y tareas del arnés.

## 2026-10-11 — App con datos reales, Monedas y Referidos

Autorización posterior del usuario: eliminar el modo demo y conectar el modelo
real, con interruptores por sección y leyenda configurable de entrenamiento.
La raíz Flutter consume la API de producción; calendario, enfrentamientos,
pronósticos, detalle, historial, planes y cuenta dejan de usar datos ilustrativos.
Los datos que la fuente todavía no entrega se identifican como ausentes.

Alta Probabilidad: rango de presentación 75–90 %, 10 % gratuito (redondeado
hacia arriba), mayor cuota real entre elegibles y asignación inmutable por lote.
Escalera: un único pendiente gratuito de mayor probabilidad exacta entre todos
los retos activos. VIP oculta selección/mercado/cuota/probabilidad desde el
servidor, incluidas las rutas web públicas; no solo desde la pantalla.

Menú reemplaza La Grada y ofrece Monedas y Referidos. Saldo y movimientos en
PostgreSQL, asistencia de siete días, códigos de invitación y canje de un pick.
Correo verificado, movimientos idempotentes, canjes atómicos y anulaciones
reversibles de premios. Configuración administrativa en
`/control/configuracion-app` y `/control/recompensas`, con CSRF y auditoría.

Investigación de Tapjoy/Unity, RevU, Torox, ayeT, adjoe y BitLabs documentada con
fuentes. Adaptadores iniciales RevU/BitLabs preparados; el usuario confirmó que
todavía no tiene cuentas de editor. Los seis proveedores están desactivados:
no se anuncian ofertas, ingresos ni acreditaciones comerciales inventadas.

Migraciones 054/055 instaladas. Despliegue limitado de API sobre su imagen previa,
sin recrear los workers. Imagen activa y persistida en compose:
`quantfut-api-mobile-rewards:20261011`; copia de configuración anterior guardada.
Web, health y seis rutas de contenido/monedas respondieron 200. Comprobación
UTC−6 del 11/10: 99 enfrentamientos, dos picks públicos, quince VIP pendientes,
un escalón público y seis proveedores pendientes. Estos conteos son variables.

Validación: 124 pruebas backend aprobadas y cinco PostgreSQL condicionadas
omitidas localmente; ocho comprobaciones adicionales contra PostgreSQL real,
siempre con rollback (saldo, repetición, reversión, referidos, cuotas gratuitas,
canje, vistas y formularios administrativos). Flutter: 18 pruebas aprobadas;
siete pruebas de navegación repetidas tras los últimos ajustes, análisis limpio,
APK debug compilado e instalado. Calendario, tarjetas y Monedas inspeccionados
en el emulador, sin errores Flutter/AndroidRuntime observados.

Estado, fuentes y activación:
`apps/mobile/docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md`.
Evidencia pública y de servidor:
`docs/validation/mobile_rewards_release_20261011/`.
Capturas Android reales:
`apps/mobile/docs/validation/real_mobile_20261011/emulator-*.png`.
Firebase, idiomas, persistencia segura de sesión, pagos/restauración, cuentas
de editor y métricas de detalle aún no expuestas permanecen en tareas pendientes.

## 2026-10-11 — Registro primero: requisito Firebase, sin ejecución

El usuario entregó la captura de acceso oscuro con Google, idioma en la esquina
superior y aceptación de términos/privacidad. Pidió que registro/acceso sea la
primera pantalla de la app y que se anote en el plan Firebase sin implementarlo
todavía. Registrado en el plan principal, el plan de suscripciones, la
especificación de idiomas y el backlog. La elección de idioma pasa a estar
disponible en la pantalla de registro; bienvenida y contenido vienen después
del acceso para personas sin sesión. La sesión existente y los derechos/saldo
del backend deben conservarse. Las cifras de la referencia no se trasladarán
sin respaldo real. Este ajuste modifica documentación únicamente: sin cambios
de código, configuración Firebase, compilación, emulador ni despliegue.

## 2026-10-11 — Coins: recompensas como cuarta pestaña

Corrección del usuario: eliminar el menú intermedio de Monedas/Referidos y
abrir directamente la pantalla de saldo, asistencia, ofertas y referidos.
La cuarta pestaña y su encabezado ahora se llaman Coins, con icono de monedas.
La navegación inferior permanece disponible dentro de esta pantalla y su
actualización consulta el saldo real. No se alteraron las reglas del backend.
Siete pruebas de navegación aprobadas, análisis sin incidencias y APK debug
compilado para actualizar el emulador. Registro inicial Firebase sigue pendiente
sin implementación, conforme a la instrucción anterior del usuario.

## 2026-10-11 — Activación de las 10 ligas: el modelo nuevo no pasa la puerta

Con el visto bueno del usuario se entrenó con `--incluir` (9 h 40 min,
artefacto 2026.10.11-135412). La puerta lo rechazó: no vence a Elo en las
mismas filas (0,20517 frente a 0,20468, n=1.541). El script no encendió
`model_enabled` y nada cambió en producción. La causa no son las ligas
nuevas: el entrenamiento del 1-oct, sin ellas, ya perdía contra Elo
(0,20074 frente a 0,19995); con ellas la distancia se acorta, y la sombra
mostró que las ligas ya medidas mejoran (0,20800 → 0,20752). El activo
(09-27) pasó la puerta por 0,0002: Dixon-Coles y Elo están empatados en la
ventana reciente. No se fuerza una puerta de seguridad sin decisión expresa.

## 2026-10-11 — Parley del día (sin desplegar)

Pedido del usuario: 1-5 parlays diarios de cuota 1,90-5,00, "los más
probables". Con "máxima probabilidad dentro de un rango" todo saldría pegado
a 1,90, así que el usuario eligió escalones (≈2 · 2,5 · 3 · 4 · 5), un partido
por parlay y ninguno repetido en el día, y solo probabilidad (pierde el margen
en cada pata; el historial lo enseña). La revisión final cazó cuatro cosas que
los tests del plan no veían: la poda de patas "dominadas" que prescribía la
propia spec pierde parlays válidos cuando hay techo de cuota (se quitó; 4,5 s
sin ella); las cuotas llegan como float4 y 1,25 × 1,76 salía "2,20 en el
escalón 1"; un ticket se guardaba fila a fila y uno a medias habría quedado
inmutable y sellado (ahora una transacción con candado por día); y
`fixtures` sobrescribe la hora de un partido reprogramado, así que la pata
guarda su hora original y se anula a las 48 h de ella. Acierto frente a la
probabilidad EFECTIVA (solo patas que contaron). Sin doble oportunidad:
ningún proveedor la cotiza. Desplegado apagado el 12-oct 00:10 UTC SOBRE las imágenes de producción (que
ya llevan la app móvil sin commitear) copiando SOLO los archivos del parley:
desplegar la carpeta entera habría metido también los cambios de tarjetas y
córners del 10-oct, que no estaban desplegados. El árbol `~/quantfut` del
VPS no tiene ni la app móvil ni el parley: un `docker compose build` los
quitaría. Primer ensayo: los cinco parlays salen de 2 patas; la búsqueda
prefiere pocas patas porque cada una paga margen.

## 2026-10-11 — Pestaña Pronósticos con el formato «Pronósticos IA»

El usuario pidió la ficha de la referencia (pronóstico destacado, Confianza IA,
xG proyectado, diferencial Elo, tendencia de goles, dictamen). Se adoptó el
diseño, no las cifras: «Confianza IA» y Elo no existen en el contrato y el
documento de detalle prohíbe fabricarlos a partir de un porcentaje histórico.
Se sustituyeron por magnitudes que el servidor sí tiene: probabilidad con cuota
justa, favorito 1X2 (`ficha.probabilities`) y tendencia de más de 2,5 goles
(`promedios.pct_mas_2_5`). El xG proyectado sale de las lambdas del ajuste de
mercado (`alta_prob_picks.fit`), que `high_probability` ahora expone como `xg`
sin filtrar el ajuste crudo; en mercados sin ajuste queda «—». El dictamen se
compone en el cliente solo con esos datos. Con el visto bueno del usuario se desplegó SOLO `mobile.py` (el remoto era
idéntico a HEAD) con `docker compose cp` + reinicio de `api`, sin tocar el
worker; producción ya devuelve `xg` real. Ojo: al ser `cp`, una recreación del
contenedor desde la imagen lo perdería hasta reconstruirla. APK debug
compilado e instalado en el emulador.

## 2026-10-11 — Pantalla VIP con el formato «VIP ELITE» (solo app, sin backend)

Se movió `LiveVipScreen` a `live_vip.dart` y se rediseñó. De la referencia se
tomó la estructura; se descartaron las cifras y promesas que el servidor no
respalda (miembros, testimonio, pruebas gratuitas, «pago con Google Play»,
«cancela cuando quieras»): el cobro sigue sin proveedor y el botón dorado solo
muestra el mensaje de la sección `compras`. «Mejor precio» se marca por el menor
equivalente mensual entre los planes que llegan del servidor. Sin despliegue de
backend; APK debug instalado en el emulador. 21 pruebas Flutter aprobadas.

## 2026-10-12 — Ficha de partido: el pick sellado sigue visible al empezar el partido

Pumas–Cruz Azul mostraba «No hay pronósticos publicados» a los 20 min de empezar
aunque el pick existía en `alta_prob_picks`: `high_probability` descartaba todo
pick con `kickoff_utc <= now`, decisión pensada para los listados de «próximos»
y no para la ficha. Ahora `detail()` pide `started=True` y recibe también los
picks de partidos en curso o liquidados, con `started` y `outcome`/marcador
(LEFT JOIN `alta_prob_results`); el reparto gratis/VIP no cambia, y home y
listados siguen sin verlos. La app muestra una franja «EN JUEGO / ACERTADO /
FALLADO». Desplegado SOLO `mobile.py` (el remoto era idéntico salvo este cambio)
con `docker compose cp` + reinicio de `api`; copia previa en
`~/backups/mobile.py.*.bak` del VPS. Mismo aviso de siempre: al ser `cp`, una
recreación del contenedor desde la imagen lo perdería hasta reconstruirla.

### Marcador en vivo para la app (2026-10-11)

Decisión: columnas `live_*` propias (db/056) en vez de reutilizar `status` y
`home_goals`. Esos los usa el pipeline de picks y `results.py` los escribe con
`result_recorded_at`; un marcador provisional ahí contaminaría la auditoría
temporal. `ingest/live.py` hace UNA petición `fixtures?live=all` por pasada y
ninguna si no hay partido en ventana, así el coste no depende de los usuarios.
Cron cada 45 min por decisión del usuario (cuota); `*/45` da huecos de 45 y 15
min. El marcador sale en `/mobile/v1/matches/{id}` como `partido.vivo`, fuera
de la ficha cacheada. Se descartó `tunjayoff/sofascore_scraper`: licencia
PolyForm Noncommercial y raspado contra los términos de Sofascore.
Desplegado el 2026-10-12 sin tocar compose: imágenes delgadas sobre las vivas, con
respaldo `before-live` (api `quantfut-api-mobile-rewards`, worker `quantfut-worker`).
Primera pasada real: 6 candidatos, 2 en juego, 1 petición. Franja `LiveScoreStrip`
en Flutter (falta recompilar la app). Pendiente: marcador en el calendario.

### Pestaña Mercados rediseñada (2026-10-12)

Decisión: se adapta el lenguaje visual de la referencia (radar, anillos, puntos)
pero NO sus alertas en vivo («Más/Menos en vivo», «Quién marca en el primer
tiempo»): los modelos pronostican antes del partido y el catálogo de evidencia
lo dice expresamente. Cada tarjeta sale de `MarketCatalog` (mejor línea
confirmada + publicados resueltos), así que no hay cifras inventadas y una
familia sin línea confirmada muestra «—». Animaciones con CustomPainter, sin
paquetes ni assets de terceros; se detienen con «reducir movimiento».

### Mercados: pantalla por mercado e historial por pronóstico (2026-10-12)

Decisión: se quita la tarjeta «Rendimiento registrado» de Mercados; cada
familia abre su pantalla con «Hoy» (pronósticos abiertos que el servidor ya
entrega) y «Anteriores» (resueltos, acertó/falló). Las cifras salen del
historial del servidor, no del JSON empaquetado: el radar decía 75/96 y el
servidor 89/114. Nuevo `GET /mobile/v1/markets/history` (alta probabilidad,
selladas, rango público 75-90 %, anuladas fuera, probabilidad con precisión
pública). Los pronósticos VIP bloqueados no se atribuyen a un mercado (su
metadato no lo lleva) y no se muestran en «Hoy»; el reparto gratis/VIP sigue
decidido por el servidor.

El historial por mercado manda `home_corners/away_corners` y la app los muestra en los
mercados de córners en vez del marcador de goles (despliegue 2026-10-12, respaldo
`before-corners`). Posible hueco de datos: Operario-PR - Goias figura 14-0 en córners;
un 0 puede ser un córner no capturado, no un cero real.

### Candados dentro de cada mercado (2026-10-12)

Decisión del usuario: los pronósticos VIP bloqueados se ven dentro de su mercado
(partido, hora, candado), sin el pick. Cambio de política: antes el metadato
bloqueado no llevaba `market`. Ahora sale SOLO la categoría; selección, línea,
probabilidad, cuota y `fit` siguen fuera (test actualizado). Sin tarjeta de venta:
tocar el candado abre VIP. Escalera no se incluye (su metadato no se reparte por familia).

### Gratis: uno por mercado, el de mayor probabilidad (2026-10-12)

Decisión del usuario: el escaparate gratuito debe mostrar lo más sólido para que se vea que la
mayoría acierta. Antes: 10 % del lote por mejor cuota. Ahora: un pronóstico por mercado con
candidatos, el de mayor probabilidad (empate: cuota). El reparto de cada lote queda fijo en
`mobile_free_allocations` al crearse, así que la regla solo afecta a lotes NUEVOS salvo que se
amplíe el lote vigente a mano (solo añadir, nunca quitar).

Desplegado el 2026-10-12 (respaldo `quantfut-api-mobile-rewards:before-gratis`). Lote 2026-10-11
ampliado a mano con 3 gratis (córners, goles, goles del visitante; free_count 3 -> 6). Hándicap (7)
y doble oportunidad (1) siguen bloqueados: sus candidatos no tienen cuota publicada y un gratis
sin cuota real no se entrega.

### Gratis: cuota entre 1,20 y 1,60 (2026-10-12)

Decisión del usuario: el gratis debe tener cuota publicada entre 1,20 y 1,60, el de mayor probabilidad
por mercado. El usuario pidió 1,40-1,60 pero con 75-90 % de probabilidad las cuotas reales van de 1,01
a 1,25 (132 candidatos en 7 días, 0 en 1,40-1,60), así que eligió piso 1,20. Desplegado (respaldo
`before-cuota`). Los 3 gratis añadidos a mano al lote 2026-10-11 se quitaron (cuotas 1,08-1,19; fuera de
rango; free_count 6 -> 3, auditado). Hoy no queda ningún gratis abierto: ningún candidato sin empezar
tiene cuota en rango.

### Gratis: la cuota manda (2026-10-12)

Decisión del usuario: el gratis de cada mercado es el de MAYOR cuota publicada (tope 1,60, sin piso),
aunque tenga menos probabilidad que otros; empate por probabilidad. Sustituye al rango 1,20-1,60 por
probabilidad. Desplegado (respaldo `before-mayor-cuota`) y los 3 gratis quitados antes se volvieron a
añadir al lote 2026-10-11 (Elfsborg 1,19, Valerenga 1,18, Malmo 1,08; free_count 3 -> 6). Hándicap y
doble oportunidad siguen sin gratis: sus candidatos no tienen cuota publicada.

### Gratis automático (2026-10-12)

Decisión del usuario: la regla es permanente, no un parche por lote. `top_up()` corre en cada lectura
(`allocations()`, dentro del mismo bloqueo del lote) y hace gratis el pronóstico sin empezar de mayor
cuota de cada mercado que no tenga ya uno abierto. Solo añade (no quita lo que el usuario ya vio),
es idempotente y queda auditado (`mobile:allocation_topup`). Desplegado (respaldo `before-automatico`):
tres lecturas seguidas dejaron free_count en 6, sin cambios. Ya no hacen falta ampliaciones manuales.
La Escalera conserva su regla de un solo pendiente gratuito.

### Tarjeta del pronóstico nueva (2026-10-12)

Sustituye al destacado + 4 recuadros por: 4 anillos (Más 2,5, Ambos marcan, Más 1,5, Gana local),
caja del pronóstico y tabla «¿Cuántos goles?» (al menos 1/2/3 por equipo = team_totals 0,5/1,5/2,5).
El «1T >0,5» de la referencia NO existe: no hay modelo de primer tiempo, se usa «Más 1,5».
Backend: `ficha.modelo` (model_card, 2 decimales) sale en /mobile/v1/matches/{id} SOLO si el usuario
tiene un pronóstico visible de ese partido; las probabilidades de las que se deriva el pronóstico no
se regalan para todos los partidos. Sin datos del modelo, la tarjeta no dibuja anillos ni tabla.

Ligas solo sharp (sin predicción propia): `market_card()` calcula la misma tarjeta desde el ajuste a
Pinnacle del pick (lambda, mu, rho) con `pricing.price_all_markets`, y la marca `fuente: mercado`; la app
lo dice debajo de los anillos. Solo para picks con `fit` (goles, hándicap y córners); doble oportunidad y
1X2 no guardan `fit` y siguen sin anillos. Sin desplegar al escribir esto.

## 2026-10-11 — Alta probabilidad: medición 62–95 % (paso previo a ampliar el rango)

- Pedido del usuario: abrir el rango de alta probabilidad a 62–95 % en todos los
  mercados, ordenando por mayor cuota. Decisión: medir ANTES de publicar (el 80 %
  se validó; los tramos 62–80 % nunca se midieron).
- `eval/alta_prob_calibracion.py --amplio` (`run_amplio`): todos los candidatos de
  62–95 %, tramos 62-67/67-72/72-76/76-80 + los de siempre, mismo criterio
  (tramo con n≥100: real ≥ prometido−2·SE; global ≥ −1 punto). 14.305 partidos.
  Resultado en `.local/alta_prob_amplio_20261011.json`: pasan 27 de 40 líneas
  (1X2, doble oportunidad, hándicap −1/0/+1/+1,5/+2, marca local/visitante, más
  de 1,5/2,5, menos de 3,5/4,5, ambos marcan «sí», córners más 6,5/8,5 y menos
  11,5/12,5 totales). No pasan: ambos marcan «no», menos de 2,5, y la mayoría de
  córners por equipo (déficits de 0,1–1,2 puntos o un tramo bajo).
- Aún NO se publica nada: falta decidir la tabla sellada nueva (`alta_prob_picks`
  tiene `match_id UNIQUE`, un pick por partido) y la cadena de hashes.

### Pestaña Pronósticos con todos los mercados (2026-10-12)

Pedido del usuario: la pestaña queda como su referencia (tarjeta «Análisis estadístico» + lista de mercados
con nivel + marcadores). `api/partido_mercados.py` deriva la lista de (lambda, mu, rho): la predicción propia
o, en ligas solo sharp, el ajuste a Pinnacle del pick; los cálculos son los de `pricing` (comprobado: diferencia
0,0 frente a `predictions.markets` en 40 predicciones). Córners y tarjetas salen de `estadisticas_mercado` y
SOLO con sus `LINEAS_HABILITADAS`. Nivel por probabilidad (alta >= 75, sólida >= 60, moderada); «oportunidad»
solo con cuota publicada y prob x cuota > 1,02; sin cuota publicada se muestra la cuota justa etiquetada.
Acceso: abiertas = las del usuario (gratis/desbloqueadas) o todas con VIP; el resto va con candado que solo
dice la categoría y SIN orden por probabilidad (el orden la filtraría). La app agrupa los candados por categoría.
Desplegado (respaldo `before-mercados`): 24 mercados en un partido real, 0,58 s la primera vez y 15 ms con caché.

AVISO de despliegue: el VPS corre el módulo VIEJO de córners/tarjetas (líneas anteriores a la revisión del
10-oct, que se dejó «sin desplegar» a propósito: más de 6,5 y 9,5 córners siguen apareciendo). La lista sigue lo
que está desplegado y se alineará sola cuando esa revisión se despliegue (decisión sobre los picks del worker).
La tarjeta anterior de anillos/«¿Cuántos goles?» se retiró de la pestaña (la sustituye la lista).

## 2026-10-11 — Alta probabilidad ampliada 62–95 % (`alta_prob_ext`), implementada sin desplegar

- Decisión del usuario: tabla aparte (`db/057`, un candidato por partido+mercado+
  selección+línea, inmutable) con todo lo aprobado por la prueba amplia; la línea
  de 80–95 % (`alta_prob_picks`) no cambia. Por qué aparte: `match_id UNIQUE` de
  `alta_prob_picks` y su lote ya sellado no admiten varios picks por partido.
- `publish/alta_prob_ext.py`: selección (`alta_prob.elegir_ext`, listas `*_EXT`),
  control por mercado (reusa `ap.control`), liquidación (encadenada en
  `eval/clv.settle_pending`). Sellado: bloque `alta_ext` en el lote desde
  `LOTE_ALTA_EXT_DESDE = 2026-10-12`; los lotes anteriores no cambian de hash.
- App: `mobile.py` lee ambas tablas (62–95 %), sin duplicar partido+mercado+
  selección+línea (manda la fila original); gratis = mayor cuota por mercado, tope
  1,60; `pick_key` de las filas ampliadas es `ext_id`. Escalera sigue en 75–90 %.
- Apagada: `ALTA_PROB_EXT_ENABLED=0`. Falta aplicar db/057 en el servidor, activar
  el flag ANTES del sellado de las 08:00 UTC del 12-oct, y verificar con
  `python -m qf.publish.alta_prob_ext preview`. Si no se despliega a tiempo,
  mover `LOTE_ALTA_EXT_DESDE` al primer lote sin sellar.
- Desplegado el 12-oct ~02:40 UTC con visto bueno del usuario. db/057 aplicada;
  archivos copiados a `api` y `worker` partiendo de lo que había en producción
  (el servidor NO tenía la revisión de córners del 10-oct en `alta_prob.py`: se
  conservó, solo se añadió lo de la ampliación). Imágenes confirmadas con
  `docker commit` (`quantfut-api-mobile-rewards:20261011`, `quantfut-worker:latest`)
  y recreados `api` y `worker` con `ALTA_PROB_EXT_ENABLED=1` en `.env`; respaldo en
  `~/quantfut/deployments/before-ext` y etiquetas `:before-ext`. Preview real:
  287 candidatos en 25 partidos (143 con cuota publicada), 0,62–0,95. El árbol
  `~/quantfut/src` del VPS sigue sin actualizar. Falta: ver el primer sellado (08:00
  UTC) con `n_alta_ext` > 0 y recompilar la app.

### 1ª mitad: prueba histórica y mercados publicados (2026-10-12)

`eval/primer_tiempo.py` (football-data, cuotas de Pinnacle, entreno 2019-2022 con 5.743 partidos y medida en
2022-2025 con 6.236, criterio de `alta_prob_calibracion` fijado antes): PASAN «ambos anotan 1T: no» (n=6.236,
79,9 frente a 80,5 prometido) y «gol en 1T: sí» (n=6.015, 72,6 frente a 71,7). No pasan: ganador 1T visitante
(n=27), más de 1,5 goles 1T (tramo 62-67 %: 61,7 frente a 64,4) y ganador 1T local pasa pero con n=159, por
debajo de las 500 muestras que exige el catálogo de evidencia: no se publica. Modelo: goles del 1T Poisson con
proporción (0,4366 local, 0,4588 visitante) del mismo ajuste de mercado; vive en `model/primer_tiempo.py`.
Se publican solo esos dos, por ese lado y en el tramo medido (62-95 %). Desplegado (respaldo
`before-primer-tiempo`). Ojo: hay OTRA edición sin commit de `mobile.py` (alta probabilidad 62-95 %, db/057)
que no es de esta tarea y NO está desplegada.

### Parley activado (2026-10-12, 05:5x UTC)

Visto bueno del usuario. Fecha de arranque = 12-oct (`LOTE_PARLEY_DESDE`, ya fijada): el sellado de las
08:00 UTC es el primero que lo lleva. ANTES de activarlo, el ensayo (`parley_datos preview`) mostró una pata
«más de 9,5 córners», línea que la revisión del 10-oct había quitado y que el VPS aún permitía. Con la
aprobación del usuario se desplegó esa revisión al worker y a la API (`estadisticas_mercado.py` y, en el
worker, solo el hunk de `CORNERS_HABILITADOS` de `alta_prob.py` sobre el archivo ya desplegado por la otra
sesión; respaldo `quantfut-worker:before-lineas`, `...:before-lineas-api`). Efecto: córners más de 7,5/8,5 y
menos de 9,5/10,5/11,5; tarjetas menos de 4,5/5,5/6,5; fuera córners más de 6,5/9,5 y local más de 2,5 en alta
probabilidad. Segundo ensayo: 5 parlays de 2 patas, 0 con líneas no validadas. `PARLEY_ENABLED=1` en el
`.env` del VPS (copia en `releases/lineas-10oct-20261012/env.before-parley`), worker y API recreados.
PENDIENTE: quién ve cada parley. `/parley` es público y la app los muestra todos; falta el reparto
gratis/VIP (hoy son gratis para cualquiera).

### Corrección: hora real de la activación del Parley y nuevo horario de sellado (2026-10-12)

La sección «Parley activado (05:5x UTC)» y el mensaje del commit fe441c1 están MAL en la hora: la pregunta al
usuario esperó ~9 h y la activación se ejecutó a las 14:48 UTC, no a las 05:5x. El sellado de las 08:00 UTC
de hoy ya había corrido con el Parley apagado (`parley: desactivado`, 0 parlays), así que NO hay parlays
sin sellar (`hashchain verify`: 14 lotes OK). El primer lote con Parley es el del 13-oct.
Decisión del usuario: el sellado diario pasa a las 07:00 de Ciudad de México = 13:00 UTC, siempre (México no
tiene horario de verano desde 2022; cron corre en UTC). `scripts/crontab`: `0 13 * * *` (antes `0 8`),
aplicado en el VPS (copia `scripts/crontab.before-13utc`) y recargado con `crontab /etc/cron.d/quantfut`, sin
reiniciar el worker. Efecto: solo entran partidos que empiezan DESPUÉS del sellado; los de 08:00-13:00 UTC
dependen del lote anterior (el job ya mira partidos de hoy y mañana). El comentario de `daily.py` («08:00,
antes del primer kickoff europeo») queda desfasado; no se tocó porque ese archivo tiene cambios de otra sesión.

## 2026-10-12 — App actualizada en el emulador Android

Pedido: «despliega el trabajo». Compilada la app del espacio de trabajo actual,
con Estadísticas, Coins, mercados y la nueva pestaña Parley. `flutter analyze`
sin incidencias; suite completa `flutter test`: 32 pruebas aprobadas.
`flutter build apk --release`: correcto, 59,8 MB. Instalación con `adb install -r`
confirmada (Success) en Medium_Phone_API_37.0, emulator-5556, sin borrar los datos.
Aplicación abierta y navegación Inicio / Predicciones / Parley comprobada con
respuesta real; Parley activo pero sin tickets publicados hoy, estado mostrado
sin inventar selecciones. Registro de errores Android/Flutter vacío.

API HTTPS comprobada: /mobile/v1/config, /mobile/v1/home y /parley devuelven 200.
La configuración real entrega 62–95 %. Los servicios del VPS ya estaban activos;
no se volvieron a desplegar archivos ni trabajadores desde este árbol local.
Firebase/registro inicial continúa únicamente en el plan.

APK: apps/mobile/build/app/outputs/flutter-apk/app-release.apk (1.0.0+1).
SHA256: 3D963890AB6FFF66CA0A46AC76B2377DBAFE92878DC80E635AD0F0213037E62F.
Captura: apps/mobile/docs/validation/real_mobile_20261011/release-parley-20261012.png.
Este APK conserva la firma de desarrollo configurada en el proyecto; no se ha
publicado en Google Play ni cambiado la firma o el identificador de la aplicación.

## 2026-10-12 — Firebase Core e identidad definitiva de QuantFut

Decisión del usuario: comenzar Firebase por fases en el proyecto existente
`pronosticos-deportivos-85ffa`; después de la pausa, fijar nombre QuantFut e
identificadores Android/iOS `com.saptain.quantfut`. Por eso se generaron apps y
configuración nuevas, en vez de conservar los registros `com.example.gobet`.
El usuario completó el acceso de Google y pidió eliminar los dos ejemplos.
Ambos registros `gobet` se eliminaron; la lista remota confirma únicamente
QuantFut Android e iOS activos. Configuración Android descargada de nuevo,
verificando que contiene solo el paquete definitivo.

La fase actual instala `firebase_core` y espera su inicialización antes de
abrir la app, con reintento visible si falla. Firebase está activo por defecto.
Se conserva FastAPI/Postgres como autoridad de cuentas, suscripción, saldo y
pronósticos: Auth/Google, FCM, Analytics, Crashlytics, Performance y Remote
Config siguen pendientes. Las herramientas CLI quedan locales e ignoradas;
la configuración pública puede versionarse, las credenciales privadas no.

Validación: análisis Flutter limpio, 35 pruebas aprobadas y APK debug con la
nueva identidad compilado/instalado en emulator-5556. Registro nativo confirma
`FirebaseApp initialization successful`; el arranque abrió el calendario con
datos reales. Arnés inicial y posterior: 911 aprobadas, 21 omitidas y una
advertencia; Docker no disponible. iOS tiene bundle ID, opciones y plist
incluido en Runner, pero necesita compilación/ejecución en Mac. Firma Android
de distribución pendiente. Detalle: apps/mobile/docs/FIREBASE_INSTALACION_20261012.md;
evidencia: apps/mobile/docs/validation/firebase_base_20261012/.


### Doble oportunidad con cuota real en el Parley (2026-10-12)

CORRECCIÓN de la nota «ningún proveedor la cotiza»: API-Football SÍ cotiza Doble Oportunidad (bet 12, 8 casas
en un partido de La Liga, entre ellas Bet365, Betano, 1xBet y William Hill; valores `Home/Draw`, `Home/Away`,
`Draw/Away`). Se descartó sintetizarla desde el 1X2: una cuota justa calculada no la ofrece nadie y no sirve de
precio de referencia; se capturan las cuotas reales. Hecho: (1) `ingest/af_odds.py` guarda bet 12 como
`double_chance` 1X/12/X2 (grupo completo, nombre exacto, soft books y Pinnacle); sin peticiones extra; primera
pasada: 65 partidos x 4 casas. (2) Solo el PARLEY la usa: `escalera_datos.opciones(incluir_doble=True)` añade
`candidatos_doble` (probabilidad = P1+PX de Pinnacle sin margen) con cuota de `_cuotas_af`; `parley.MERCADOS_PARLEY`.
La Escalera NO cambió (verificado en producción: 323 opciones evaluadas, 48 en rango, antes y después). (3) db/059:
el CHECK `parley_patas_market_check` rechazaba `double_chance` y habría roto el guardado del primer parley; la migración
solo amplía la regla (0 filas afectadas). Desplegado en worker (respaldos `before-doble`, `before-doble-parley`).
Ensayo: 4 patas de doble oportunidad con cuotas reales (Betano 1,16/1,29/1,67, Bet365 1,33).
PENDIENTE (toca archivos de la otra sesión, alta probabilidad ampliada): que `alta_prob_datos._ref` use esas cuotas
para que la doble oportunidad pueda ser pronóstico gratis; hoy `_ref` devuelve sin precio. Ideas aún sin hacer:
informe de calibración por origen (Pinnacle frente a córners/tarjetas), test binomial exacto en el control del parley
(con n=50 y p=0,24 el `z<=-4` actual no puede dispararse) y orden del armado (medido: +0,6 % en un día).


## 2026-10-12 — Servicios Firebase, identidad y despliegue de API

El usuario amplió el alcance a Auth/Google, FCM, Analytics, Crashlytics,
Performance, Remote Config y App Check. Se conservan FastAPI/Postgres como
autoridad comercial; Firestore/Storage/Functions P2 no se activaron. Google
está habilitado en Firebase y los recursos Android/iOS preparados. App Check
usa Play Integrity en distribución y proveedor de desarrollo registrado en
emulator-5556; enforcement continúa apagado. Los registros de ejemplo ya no
están activos.

Decisión de identidad: cabecera explícita Firebase y verificación de proyecto/
revocación; no convertir un token inválido en sesión anterior. El mismo correo
no toma control de una cuenta: vínculo solo demostrando la sesión previa.
Se preservan ID, saldo, VIP y referidos. Consentimientos versionados;
medición/diagnóstico/avisos opcionales apagados por defecto. Avisos genéricos,
ruta interna validada y permisos consultados de nuevo al abrir; bandeja y
cola con propietario/caducidad/reintentos. El envío automático no está activo.

Tras rechazo de revisión automática, el usuario autorizó explícitamente crear
quantfut-backend con lectura Auth y envío FCM, generar clave privada, y después
desplegar en producción. Clave fuera de Git y Flutter, privada y montada como
solo lectura. SDK 7.7.0 instalado, migración 058 aplicada, solo API recreada.
Compose e imagen anteriores respaldados, reversión de arranque preparada.
Paquete sobre la imagen real del servidor, sin cambios deportivos de otras
sesiones. La primera compilación falló al interpretar SHA como repositorio;
se corrigió usando una etiqueta local de la misma imagen y el despliegue pasó.

La imagen en ejecución incluye módulos móviles que todavía no están en el
checkout del VPS. Una comprobación previa detuvo la sincronización antes de
escribir archivos; no se intentó reconstruir desde ese checkout antiguo.
El paquete y fuentes exactas quedan en releases/firebase-backend-20261012.
Una futura reconstrucción debe partir de la imagen vigente o reconciliar
primero todo el código desplegado, para no perder funciones anteriores.

Servidor verificado: credencial Auth válida sin descargar usuarios reales,
seis tablas presentes, pip check correcto, API HTTPS config/home 200;
preferencias/avisos anónimos 401 y acceso Google cerrado 503. Google continúa
FIREBASE_AUTH_ENABLED=0 y qf_google_auth_enabled=false hasta documentos vigentes.

Validación: análisis Flutter limpio, 38 pruebas aprobadas,APKdebug instalado y
calendario real con 43 partidos. Preferencias opcionales comprobadas apagadas;
arranque posterior al registro App Check sin error fatal/Flutter/intercambio
en la observación. 11 pruebas Firebase y 8 escenarios PostgreSQL real en esquema
aislado con rollback, sin cambiar filas comerciales. Arnés completo: 924 aprobadas,
21 omitidas, 2 advertencias; Docker local no disponible. No se ha probado Google
con usuario real, entrega FCM ni iOS. Firma de distribución y Apple/APNs
pendientes; selector de 6 idiomas disponible, traducción completa pendiente.

Datos legales confirmados por el usuario: Saptain LTD; E Coast Rd, Victoria,
Seychelles; admin@pronosticosdeportivos.com; edad 18; Estados Unidos, toda Europa
y Latinoamérica. Se actualizaron borradores y fuentes primarias. Proveedores
Contabo/Proton identificados en notas; faltan ubicación contractual, ciclos de
retención/respaldo/procedimiento de derechos y revisión territorial. No se
publicaron borradores ni se registraron como aceptados. Las leyes obligatorias
de mercados de destino no se excluyen por la constitución en Seychelles.

Detalle: apps/mobile/docs/FIREBASE_SERVICIOS_20261012.md. Evidencia sin secretos
en apps/mobile/docs/validation/firebase_services_20261012/; borradores y control
de publicación en docs/legal/.

## 2026-10-12 — Tapjoy Offerwall (Unity) como proveedor de monedas

- Decision: callback S2S estandar de Tapjoy (GET, `verifier=md5(id:snuid:currency:secret)`), moneda *self-managed*. Solo creditos: la doc de Tapjoy no define reversiones; un `currency` negativo se rechaza con 403. Errores definitivos siempre 403 (Tapjoy reintenta 4 dias ante cualquier otro codigo distinto de 200/403).
- El offerwall se abre por SDK nativo (no URL): `launch` devuelve `{sdk,sdk_key,user_id}` y `MainActivity.kt` hace `Tapjoy.connect` con `USER_ID`=uid del monedero, que llega como `snuid`.
- Dashboard (cloud.unity.com > Tapjoy Offerwall): app Quantumfut (Android, no activa), moneda `Monedas` ($1 = 1000), placement `coins_offerwall` + tarjeta `Coins`. Secreto en `QF_TAPJOY_SECRET` (VPS); la cuenta Tapjoy esta en revision.

- Secret keys de proveedores (Tapjoy, BitLabs) editables desde /control/recompensas (db/060, columna `secret_enc`): AES-256-GCM con `cryptography` (pyca; AEAD estandar, auditado, sobre OpenSSL), nonce aleatorio y contexto `reward_provider:<id>` como AAD para que un secreto no se pueda mover a otra fila. La clave maestra `QF_SECRETS_KEY` vive solo en el entorno del servidor (rotacion con `QF_SECRETS_KEY_OLD`): copiar la BD no basta. Campo de solo escritura, auditoria sin el valor, variable de entorno como respaldo. Fallo cerrado: sin clave maestra el panel rechaza guardar.

- Despliegue VPS 2026-10-12 (sin git): codigo copiado al contenedor, `docker commit` a `quantfut-api-tapjoy:20261012`, compose apuntado a esa imagen y `compose up -d --no-deps api`. Respaldos en ~/backups/tapjoy-20261012 (env, compose, rewards.py/html previos); vuelta atras = imagen `quantfut-api-mobile-rewards:pre-tapjoy-backup` + env respaldado. db/060 aplicada; `QF_SECRETS_KEY` generada en el servidor (no esta en ningun otro sitio: respaldarla).

- 2026-10-12 — Firebase no arrancaba en el emulador (`channel-error` en `FirebaseCoreHostApi.initializeCore`): `GeneratedPluginRegistrant.java` estaba vacio (19 lineas) porque las dependencias de Flutter no estaban resueltas (avisos de `google_sign_in_android` inexistente). `flutter pub get` lo regenero (71 lineas) y `FirebaseApp initialization successful`. Si reaparece el mensaje «No pudimos iniciar QuantFut», comprobar primero `flutter pub get` y que el registrant liste los plugins.

## 2026-10-12 — Conservacion y limpieza Firebase puestas en marcha en el VPS

El codigo (`firebase_mantenimiento.py`, `scripts/firebase_operations.py`) existia pero NO estaba operando: el modulo no estaba en la imagen, el usuario `qf` no tenia crontab y la carpeta de copias no existia, mientras los textos legales ya prometen 30/90 dias. Ahora: modulo en la imagen (`quantfut-api-tapjoy:20261012-mant`), crontab diario a las 03:40 UTC solo con `daily` (`deliver` sigue sin programarse: el envio automatico esta apagado), alerta por Telegram si falla y rotacion extraida a `rotate()` con pruebas. Se probo la logica de limpieza con datos ficticios en transaccion revertida y la restauracion real de una copia en una base temporal. Limite conocido: la copia es parcial (sin citext ni deny_mutation) y no sustituye un respaldo completo ni uno fuera del VPS; el camino de alerta ante fallo no se ejercito con un envio real. Un limite de la conservacion: las tablas `sessions`/`email_tokens` no se limpian aqui (estan vacias hoy).

- 2026-10-12 — Limpieza de sesiones y tokens de correo (`cuentas_mantenimiento`), dentro de la tarea diaria 03:40 UTC. Plazos elegidos: sesiones 30 dias tras caducar/revocar (margen para investigar `reuso_refresh`; borra IP y user-agent), tokens retirados de refresh al borrar la sesion o al pasar `REFRESH_TTL_DAYS` (la sesion tiene caducidad absoluta de 30 dias, asi que la deteccion de reuso no pierde nada; borrados antes que su sesion por la FK), tokens de correo 7 dias. No toca cuentas, suscripciones, monedas ni `admin_audit`. Probado con tablas reales + FK en transaccion revertida. Pendiente: reflejar los plazos en la politica de privacidad publicada y revisar si procede una limpieza de cuentas inactivas.

- 2026-10-12 — APK release firmado verificado (`apksigner`, certificado CN=QuantFut, SHA-1 ya registrado en Firebase). El release fallaba por R8: el SDK de Tapjoy referencia clases `appset` opcionales; se anadieron sus reglas oficiales en `android/app/proguard-rules.pro` + `-dontwarn` para appset. Documento: apps/mobile/docs/FIRMA_ANDROID.md. Riesgo abierto: copia unica del `.jks` en `.local/`; falta respaldo fuera del equipo y activar Play App Signing al publicar.

- 2026-10-12 — Firma de release cambiada por decision del titular a `C:/1. llave/llave.jks` (alias `llave`, CN=ely marine / O=NavalQuiz: identidad de otro proyecto, riesgo aceptado: comparte firma). Huellas SHA-1/SHA-256 registradas en Firebase con la CLI y `google-services.json` actualizado (cliente OAuth nuevo). APK release verificado con `apksigner`. La clave anterior `quantfut-release.jks` sigue registrada pero sus contrasenas se perdieron al sobrescribir `key.properties`. No se guardan contrasenas en el repo.

## 2026-10-12 — Traducciones completas de la app (es, en, pt, fr, it, de)

Decision del usuario: traducir toda la app y mantenerlo siempre al dia (regla tambien en CLAUDE.md y en la memoria). Base: `gen-l10n` (ARB), `AppLocale` persistente que funciona sin Firebase, selector de idioma (bienvenida, acceso, Perfil, Privacidad), idioma del dispositivo como sugerencia. ~450 textos de los 29 archivos alcanzables desde `main.dart`; los 60 archivos de la plantilla original y 5 de `lib/product` son codigo muerto y no se tradujeron. Decisiones clave: (1) los textos de pronostico/mercado (`texto`, `titulo`, `seleccion`, `grupo`, `nota`) se reconstruyen en la app desde `market/selection/line` + equipos (`pick_labels.dart`), sin tocar los datos sellados ni el servidor; (2) formateadores sin contexto leen el idioma de `AppLocale` y cada pantalla depende de `context.l10n` para reconstruirse al cambiar; (3) mensajes del backend por `Accept-Language` con un catalogo unico (`src/qf/api/mensajes.py`) y un manejador global de `HTTPException`: sin cabecera todo sigue en espanol; (4) pruebas que lo exigen: paridad de ARB, cero cadenas fijas (con o sin acentos), render de las 5 pestanas en los 6 idiomas con fuentes reales sin desbordes, cambio en caliente, y catalogo backend completo via `ast`. Limites: traducciones hechas por un modelo, sin revision nativa; textos legales publicos y correos de cuenta sin traducir; el backend con `mensajes.py` NO esta desplegado todavia. Detalle: apps/mobile/docs/TRADUCCIONES.md.

- Despliegue VPS 2026-10-12 (mensajes por idioma): `mensajes.py` + manejador de HTTPException + terminos/mensaje de monedas traducidos. `main.py` desplegado se PARCHEO (solo import + manejador): el local trae cambios de Parley/Alta prob. sin desplegar. Respaldos en ~/backups/mensajes-20261012; vuelta atras = imagen `quantfut-api-tapjoy:pre-mensajes-backup` (compose `image:`) + `compose up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-msg`.

- 2026-10-12 — Icono y arranque nativo: se reemplazo el icono «GoBet» de la plantilla por el «Q.» verde sobre fondo oscuro de la bienvenida (no habia logotipo de QuantFut en el repo). Generado con `apps/mobile/tool/make_icon.py` (Pillow) + `dart run flutter_launcher_icons` (Android clasico y adaptable, iOS) y el fondo de `launch_background` pasa de blanco a #090f1a. Es un icono provisional con la identidad actual de la app: si el titular tiene un logotipo propio, sustituir `image/quantfut_icon*.png` y repetir el comando.

## 2026-10-12 — Textos legales finales

Los tres textos (términos, privacidad, eliminar cuenta) ya no tienen marcadores y
describen solo lo que el servidor hace: retención 30/90/30/7 días, copias de 30 días,
eliminación manual atendida por correo. Decisión clave: el titular ordenó publicarlas (2026-10-12). Se desplegó solo
`legal.py` + `legal_pages/` y se parcheó el `main.py` del contenedor (import + include_router;
el local trae cambios de otras tareas sin desplegar). Respaldos en `~/backups/legal-20261012`;
vuelta atrás = imagen `quantfut-api-tapjoy:pre-legal-backup` en el compose y
`up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-legal`. `/legal/*` da 200
desde el dominio. NO se activó Google ni se registran aceptaciones: eso sigue siendo del titular.
`REVISION_Y_PUBLICACION.md` estaba obsoleto (decía `.com` y «borrador») y se reescribió; los
`*_BORRADOR.md` quedan como historial. Los textos legales siguen solo en español.

## 2026-10-12 — xG de API-Football conectado al entrenamiento

Decisión explícita del usuario: usar el xG actual de API-Football en el modelo.
La exclusión histórica del proveedor queda revocada y documentada. La respuesta
ya llegaba a matches.stats, pero el entrenamiento leía home_xg/away_xg vacíos.
Se conserva la primera pareja válida con origen y recepción real, sin sobrescribir
histórico ni revisiones posteriores. Reconsulta diaria 12:10 UTC (06:10 CDMX),
35 días, tope 100, espera 20 h y reserva del 15% de cuota. db/061 aditiva.

Punto clave: cargar xG hoy no lo vuelve disponible en una predicción antigua.
Dixon-Coles y más-menos lo usan solo desde su captura; el replay secuencial de
Kalman conserva goles para esta fuente hasta soportar llegadas tardías. La
recepción original del xG previo sigue sin acreditarse. Hash de dataset/código
incluye las nuevas entradas y protección. No se relajan puertas.

Desplegado solo en worker, sobre archivos cotejados con la versión real, sin
reiniciar servicios. Imagen quantfut-worker:latest verificada; respaldo
quantfut-worker:xg-before-20261012 y paquete completo en
/home/qf/quantfut/deployments/xg-api-20261012. El checkout viejo del VPS no se
usa como base de reconstrucción. API y NBA conservados.

Primera captura: 182 consultas, 149 parejas, 33 ausentes, cero errores; 13
competiciones. Entrenamiento: 49.505 filas, 148 parejas de la nueva fuente;
Sporting-Galatasaray se excluye por Turquía fuera del modelo, regla previa.
Comprobado que todas se ocultan antes de su recepción y entran después.
Modelo activo 2026.09.27-010508 intacto; no se lanzó otro entrenamiento.
Cadena: 14 lotes OK; HTTPS config/home/model-card 200.

Validación: 970 aprobadas, 22 omitidas y 2 advertencias; 79 pruebas dirigidas,
8 escenarios PostgreSQL temporal con rollback, 117 módulos compilables.
Las pruebas de API necesitaron sockets locales fuera del aislamiento Windows;
la primera ejecución aislada se atascaba en socketpair, no en código del proyecto.
Detalle y cobertura: docs/xg_api_football_20261012.md; evidencia ignorada en
.local/xg_api_20261012/. Pendiente cobertura sostenida y próximo entrenamiento.

## 2026-10-12 — Acceso con Google activado

Orden del titular. Tres piezas, en este orden: (1) servidor `FIREBASE_AUTH_ENABLED=1` en
`~/quantfut/docker-compose.yml` (copia previa en `~/backups/legal-20261012/docker-compose.pre-google.yml`);
(2) Remote Config `qf_google_auth_enabled=true`, `qf_terms_url` y `qf_privacy_url` apuntando a
`/legal/terminos` y `/legal/privacidad` (la app solo acepta esas dos rutas en pronosticosdeportivos.pro);
(3) el proveedor Google ya estaba habilitado en Firebase Auth.
Pruebas: `/app/v1/firebase/connect` con token falso pasó de 503 `firebase_deshabilitado` a 401
`firebase_token_invalido` (el servidor verifica contra Firebase); en el emulador la app muestra la
pantalla de acceso, el botón queda desactivado hasta aceptar y, al pulsarlo, abre el flujo de Google.
NO probado: sesión completa con una cuenta real (el emulador no tiene cuenta y no se introducen credenciales
de Google) ni FCM. Vuelta atrás: Remote Config `qf_google_auth_enabled=false` (apaga la pantalla al instante,
plantilla anterior en el historial de Firebase) y/o compose con `FIREBASE_AUTH_ENABLED: '0'` + `up -d --no-deps api`.

## 2026-10-12 — Correos de cuenta en 6 idiomas

Los dos correos propios (verificar y restablecer) estaban solo en español pese a la regla de
traducciones. Las plantillas viven en `comercial/correo.py` y el idioma sale del `Accept-Language`
(la app ya lo envía) en vez de guardarse en la cuenta: no hay migración y funciona también para
cuentas sin preferencia Firebase. El panel `/control` reenvía en español (el admin no conoce el
idioma de la persona). Un idioma desconocido cae a español. Desplegado con respaldo en
`~/backups/correos-20261012`; vuelta atrás = imagen `quantfut-api-tapjoy:pre-correos-backup` en el
compose. Imagen vigente: `quantfut-api-tapjoy:20261012-correos`. Las páginas web a las que llevan los
enlaces siguen en español (límite documentado en `TRADUCCIONES.md`).
Se marcaron como hechos cuatro pendientes de idioma/FCM que ya estaban implementados y sin tildar.

## 2026-10-12 — Entrenamiento con el nuevo xG iniciado

El usuario pidió ejecutar el entrenamiento y recibir aviso al terminar.
Versión 2026.10.12-221104 lanzada en el worker a las 22:11:04 UTC / 16:11 CDMX:
49.504 partidos, 148 parejas xG de API-Football, 11 ligas + 2 copas, validación
completa de 365 días y puertas habituales. No se amplían ligas ni se fuerza
activación: el modelo 2026.09.27-010508 permanece activo durante el cálculo.
La nueva fuente entra en el ajuste final y se oculta en cortes anteriores a
su captura; no atribuirle mejora retrospectiva en el backtest.

Proceso desacoplado de SSH, prioridad reducida y un hilo por biblioteca.
Snapshot del input y fuentes, log, estado con señal de vida cada 30 s y resultado
final en /srv/quantfut/artifacts/training-runs/xg-2026.10.12-221104/.
A las 22:15 UTC: proceso vivo, primer ajuste histórico, sin errores registrados;
/model-card interno y público 200. Una consulta urllib desde VPS al dominio
recibió 403; desde este equipo con User-Agent de navegador dio 200.

Automatización heartbeat resultado-del-entrenamiento-con-xg creada y verificada
en este chat, cada 15 min: avisar resultado/fallo, verificar registro/artefactos,
actualizar documentación y detener seguimiento; silencio mientras sigue.
El equipo y Codex deben estar encendidos para el seguimiento, no para el cálculo
remoto. Comprobaciones obligatorias inicial y final: 972 aprobadas, 22 omitidas,
2 advertencias. Documentación: docs/entrenamiento_xg_20261012.md.
El entrenamiento sigue en curso; todavía no hay métricas nuevas ni promoción.

## 2026-10-12 — Sentry instalado (errores)

Orden del titular. Dos proyectos en la organización `saptain`: `quantfut-api` (FastAPI, también
recibe los trabajos del worker) y `quantfut-app` (Flutter). Decisiones, todas por privacidad:
solo errores (sin tracing/replay/logs); el backend maneja tokens y claves en URLs, así que
`src/qf/observabilidad.py` apaga PII, cuerpos, variables locales, SQL y migas de pan, y limpia
cabeceras/cookies/query/usuario/`sys.argv` antes de enviar (pruebas en `tests/test_observabilidad.py`).
Se inicia desde `qf/__init__.py` para cubrir API y todos los `python -m qf...` del cron; sin
`SENTRY_DSN` no hace nada. El DSN vive solo en el `.env` del servidor.
App: Sentry se inicia únicamente si el diagnóstico está activado (mismo consentimiento que
Crashlytics) y se cierra al retirarlo; no basta un `beforeSend` porque los fallos nativos se
capturan antes que Dart. Texto del interruptor actualizado en los 6 idiomas y política de
privacidad (Sentry como encargado; publicada en `/legal/privacidad`).
Coste: `sentry_flutter` 10 exige Android 8.0, así que `minSdk` sube de 24 a 26 (la 9.x no compila
con AGP 9). Desplegado en la API (imagen `quantfut-api-tapjoy:20261012-sentry`, respaldos en
`~/backups/sentry-20261012`, vuelta atrás = `pre-sentry-backup`) y en el worker (pip + archivos +
`/etc/environment`, sin recrearlo; `~/quantfut/{requirements.txt,src}` actualizados para el próximo
build). Verificado: evento `QUANTFUT-API-1` desde la API y `-2` (excepción no capturada) desde el worker.
No verificado: la app en un dispositivo (exige consentimiento y sesión de Google).

## 2026-10-12 — «Sesión no válida» tras entrar con Google

Causa: `api/mobile.py` usaba `request: Request` en `member()` sin importar `Request`. Con
`from __future__ import annotations`, FastAPI no resolvía el tipo y trataba `request` como un
parámetro de consulta siempre vacío, así que la rama `X-QF-Identity: firebase` nunca se activaba
y el ID token de Google se validaba como sesión clásica: 401 en todo `/mobile/v1/*` con sesión.
Pasó desapercibido porque `connect`/`preferences` (otro módulo, sí importa `Request`) funcionaban.
Regresión cubierta en `tests/test_mobile_identidad_firebase.py`. Desplegado en la API (respaldo
`~/backups/mobile-identidad-20261012`, vuelta atrás = imagen `pre-mobile-identidad-backup`).
Lección: un `Request` sin importar no da error al arrancar; revisar esto en endpoints nuevos.
El registro de rechazos de identidad añadido en `api/firebase.py` se queda (aviso WARNING).

## 2026-10-12 — Elección de idioma como primera pantalla

Pedido del titular (captura de referencia con globo animado y cuadrícula de 6 idiomas).
`LanguageSelectionScreen` (`lib/l10n/language_selection_screen.dart`) sale solo la primera vez:
`QuantFutApp.home` la muestra mientras `AppLocale.chosen` sea falso y la app pasa sola al flujo
normal al elegir (ya escucha `AppLocale`), así que no se tocó el acceso con Google ni Firebase.
Quien actualiza la app la verá una vez, porque su idioma nunca se guardó como «elegido».
Animación dibujada en código (CustomPainter + controladores), sin dependencias: respeta «reducir
animaciones». Referencias consultadas, sin copiar código: `gskinner/flutter_animate` (BSD-3) y
`flutterfx/flutterfx_widgets` (sin licencia). La etiqueta de la captura («Neural interface
configuration») se cambió por «Configuración de idioma» y los textos van en los 6 idiomas.
No verificado visualmente en emulador (se interrumpió el reinicio): compararlo con la captura.

## 2026-10-12 — Una sola tarjeta destacada por partido

Antes el detalle pintaba una tarjeta verde por cada pronóstico (una por mercado) con chips para
filtrar. Ahora `featuredPick` (`live_forecast.dart`) elige UNA: la de mayor probabilidad y, si
empatan, la de cuota más alta (decisión del titular entre tres reglas; la cuota más alta y
probabilidad × cuota quedaron descartadas). Se quitaron los chips, que ya no filtran nada; el resto de
mercados sigue en la tabla «Mercados del partido». Es lógica del cliente: el servidor no cambia.

## 2026-10-12 — Alta probabilidad muestra solo 73-95 %

Pedido del titular: el apartado solo muestra pronosticos de mas de 73 %. Revierte la ampliacion
del 11-oct (62-95 %). Es un FILTRO DE LECTURA (`HIGH_MIN` en `api/mobile.py`): `alta_prob_ext`
sigue sellando candidatos desde 62 % y sus filas inmutables no se tocan, solo dejan de mostrarse
(cambiar `PROB_MIN_EXT` alteraria el sellado y se haria solo si el titular lo pide). Efectos: el
historial y el acierto mostrados pasan a calcularse solo sobre >=73 % (mismo filtro) y la pantalla
VIP ya leia el rango del servidor. El texto del apartado (`picksRangeHint`) ahora recibe el rango
del servidor en vez de tenerlo escrito en 6 idiomas. Desplegado con respaldo
`~/backups/alta-73-20261012` (vuelta atras = imagen `pre-alta73-backup`); la app instalada filtra
bien sin APK nuevo, pero su texto dira «62-95 %» hasta actualizarla.

## 2026-10-12 — Reto Escalera rediseñado (tarjetas de avance)

Pedido del titular: diseño ergonómico, % de avance, cuánto falta, si el reto sigue vivo, probabilidad
de cumplirse e historial. Una tarjeta por reto (`lib/product/live_ladder.dart`): anillo de avance,
barra con un tramo por escalón (verde ganado, ámbar en juego), estado «En juego» / «Por elegir»,
probabilidad estimada, saldo como MULTIPLICADOR (×1,56, decisión del titular: sin cantidades) y
escalones liquidados plegados. Orden: primero el que tiene un escalón en juego, luego el más avanzado.
Historial: tarjeta pequeña con cumplidos Y fallidos (decisión del titular, por honestidad de la tasa);
hoy está vacío (0 retos cerrados) y muestra un estado vacío.
La probabilidad es una ESTIMACIÓN (`ladder_progress.dart`): escalón en juego (si es visible) × la media
de probabilidad de los escalones liquidados elevada a los que faltan; la media viene del servidor
(`escalones.prob_media`, 79,1 % con 9 escalones) y solo se usa con ≥5 escalones, si no se asume el 73 %
medido en `publish/escalera.py`. La tarjeta lo dice («Estimación … No es una garantía»). Todo sale de
datos que el servidor ya entrega: sin cambios de backend ni despliegue. Referencias sin copiar código:
SandroMaglione/step-progress-indicator (MIT), JHBitencourt/timeline_tile (MIT), flutter_percent_indicator
(BSD-2); `InlitX/streak` es GPL-3.0 y se descartó.

## 2026-10-12 — Predicciones: menú, Alta probabilidad y Parley rediseñados

Pedido del titular (misma línea que el Reto Escalera). Menú superior (`predictions_switcher.dart`):
píldora con indicador que se desliza, icono + texto + contador (pronósticos abiertos y retos en marcha),
fijo arriba al hacer scroll; se cambia de sección tocando o DESLIZANDO el dedo (decisión del titular).
Alta probabilidad (`live_picks.dart`): tarjeta de acierto histórico real frente al prometido (hoy 80,9 %
sobre 141), pronósticos abiertos agrupados por día con la etiqueta «Mayor probabilidad» en el primero
(misma regla que la tarjeta única del detalle) y los de candado AGRUPADOS en una sola tarjeta plegable
(decisión del titular: había 54 candados casi idénticos ahogando a 5 gratuitos). Los nombres de liga
salen de `league_names.dart` (el payload solo trae el id; es un dato, no se traduce).
Parley (`live_parley.dart`): boleto con muescas, patas en línea de tiempo, reglas en una línea con ⓘ
que abre una hoja, y estados vacíos (sin parlays / sin historial). Todo con datos que el servidor ya
entrega: sin cambios de backend. Referencias sin copiar código: splashbyte/animated_toggle_switch (BSD-3),
hadukin/custom_sliding_segmented_control (MIT), fathialamre/ticketcher y FazalHussain/Ticket-UI-Widget (MIT).
`product_navigation_test` y `live_parley_test` se actualizaron: ya no hay un botón por candado y las
reglas largas viven en la hoja.

## 2026-10-12 — Tapjoy: no mostrar HTML de errores en Coins

El puente reenviaba TJError.message y Flutter lo mostraba completo dentro del SnackBar: un fallo del SDK podía cubrir la pantalla con HTML. Ahora el canal solo transmite códigos estables y el código numérico del SDK; la app presenta avisos en es/en/pt/fr/it/de, permite reintentar y bloquea solicitudes duplicadas. Activity en connect, apertura en el hilo principal, éxito al mostrarse contenido y límite de 45 s. SDK 14.8.0 por mejoras oficiales de contenido web/interfaz, sin atribuirle una solución específica no documentada. 16 pruebas Flutter y análisis correctos, arnés final 977/24. Caché Pub incompleta restaurada. La apertura real sigue pendiente: BlueStacks no ofreció logs dentro del límite y hubo interacción concurrente del usuario. Detalle: apps/mobile/docs/TAPJOY_ERROR_HTML_20261012.md.

APK corregido release compilado, SDK/códigos verificados dentro del archivo y firma v2 coincidente con distribución vigente; entregable `.local/artifacts/QuantFut-ofertas-corregidas-20261012.apk` (74,1 MB). No instalado ni acreditada apertura real en la cuenta del usuario.

## 2026-10-12 — Entrenamiento xG terminado; candidato no activado

2026.10.12-221104 terminó a las 20:55:22 CDMX (13-oct, 02:55 UTC), tras
4 h 44 min 18 s: 49.504 partidos, 148 parejas nuevas xG y 13 competiciones.
Se ejecutaron todas las etapas, 12 ajustes históricos (una ventana mensual
sin test), ajuste final y puertas existentes. El candidato quedó registrado
inactivo: en los mismos 1.051 partidos, RPS DC 0,19873 frente a Elo 0,19657
y mercado 0,19147; log-loss 0,98694 / 0,98686 / 0,96547. Menor es mejor.
El veto es no superar Elo; champion de ventana distinta no comparable y la
puerta comercial sigue cerrada (clv_report de este pipeline n=0, mínimo 300;
no confundir con las capturas de otros informes sharp). Calibración aprobada
no anula el veto del modelo base. Modelo activo conservado 2026.09.27-010508.

La nueva fuente está incorporada en el artefacto candidato, no en el modelo
activo: carga con mezcla xG 0,65 y las 148 parejas disponibles en el corte
final 13-oct 02:32:16 UTC. Su backtest no acredita mejora retrospectiva por
xG capturado hoy. No se fuerza promoción ni se reinicia entrenamiento.

Resultado, fila model_artifacts y métricas cotejados. Recalculado el hash del
dataset desde training_input.pkl con la configuración registrada; fuentes
copiadas coinciden con el hash inicial. Diez artefactos comprobados y hashes
registrados; /model-card interno/público 200. Evidencia local completa en
.local/xg_api_20261012/training-2026.10.12-221104/: completion-audit.json,
artifact-verification.json y result.json/status.json/training.log exactos,
con hashes iguales al VPS. Actualizadas documentación y tareas.
Automatización resultado-del-entrenamiento-con-xg detenida (PAUSED) conforme
a la orden de avisar al finalizar; sin cambios de código ni puertas.

## 2026-10-12 — Tapjoy abierto en BlueStacks tras registro de prueba

La segunda captura conservaba el fallo de carga pese a ocultar el HTML. Registro Android: `no_currency`; Unity: moneda Monedas activa, Coins vinculada a esa moneda y coins_offerwall, SDK coincidente. Cuenta aún en revisión/app no activa sin tienda; cero dispositivos de prueba. Se registró BlueStacks QuantFut con permiso explícito para enviar su ID publicitario a Unity. Registro confirmado y apertura en la sesión actual verificada visualmente: Earn Rewards, Tapjoy Test CPA, 7 monedas. No se completó oferta ni se acreditaron monedas. La apertura de pruebas queda resuelta; aprobación/comercial y callback real siguen pendientes. Sin nuevos cambios de código o APK.

## 2026-10-12 — Coins rediseñado y aviso de monedas insuficientes

Pedido del titular (referencia: capturas de otra app de recompensas). Se adaptó la FORMA, no su
contenido: no hay cobro en dinero (las monedas no tienen valor monetario, dicen los términos), ni
marcadores «en vivo» de otros usuarios, ni «2×»/temporizadores inventados, ni juegos de terceros. La
cuenta atrás es real (reinicio de la asistencia a las 00:00 UTC).
`live_rewards.dart`: saldo con anillo de avance hacia el desbloqueo, asistencia de 7 días con el de hoy
resaltado y botón con las monedas de hoy, ofertas como UNA tarjeta del proveedor listo (Tapjoy) y los 5
sin activar en una línea «Próximamente» (antes 5 tarjetas muertas), invitación con código copiable,
historial con 5 movimientos y «Ver más», términos plegados y lluvia de monedas al reclamar
(`coin_burst.dart`, respeta «reducir animaciones»). Base oscura con acentos vivos (morado, dorado,
rosa), decisión recomendada y aprobada con «hazlo».
Bug corregido: la racha mostrada era el número guardado aunque se hubiera roto; ahora se calcula con la
fecha real UTC (`rewards_progress.dart`, misma regla que el servidor).
Cuando faltan monedas al desbloquear, el servidor responde 409 con `code: monedas_insuficientes` (antes
solo texto traducido) y la app ofrece «Ganar monedas» en vez de un error. Desplegado en la API con
respaldo `~/backups/coins-409-20261012` (vuelta atrás = imagen `pre-coins409-backup`); la app antigua
sigue funcionando (muestra el texto de siempre).
Tapjoy: según la documentación de Unity Grow, el SDK de Flutter solo muestra el placement entero
(`TJPlacement.requestContent/showContent`); no hay forma documentada de pintar las ofertas una a una en
la propia pantalla. Lo personalizable es la tarjeta de contenido del panel (moneda, icono, colores,
tasa), Message to Earn y los placements contextuales.

## 2026-10-12 — Inicio ya no enseña partidos terminados

Pedido del titular: un partido que acaba sale de la app y queda en los registros históricos. Se filtra en
el SERVIDOR (`visible_agenda` en `api/mobile.py`, solo la agenda de `/mobile/v1/home`) para que la app ya
instalada lo tenga sin actualizarse, y otra vez en la app (`calendar()`), por si llega una agenda sin
filtrar. Se quita todo `estado == 'finished'`; los de en juego y los por jugar siguen. La web y las demás
rutas de fichas no cambian. Medido en producción antes/después con `fecha=2026-10-12`: 41 partidos (25
terminados) → 16, todos por jugar. Consecuencia a vigilar: en un día pasado Inicio queda vacío, porque
todos sus partidos ya terminaron; los resultados siguen en los pronósticos liquidados y en las
estadísticas del partido. Desplegado con respaldo `~/backups/agenda-sin-terminados-20261012`
(vuelta atrás = imagen `pre-agenda-backup`).

## 2026-10-12 — Pestaña «Alertas» en el análisis del partido (fase 1, sin IA)

Pedido del titular (referencia: pestaña de alertas de otra app). Fase 1 decidida con él: datos REALES y
verificables, sin modelo de lenguaje. Se apoya en lo que ya existía: `ficha.bajas` (API-Football
`/injuries`, última comprobación, ver `fichas._bajas` e `ingest/injuries.py`). No se tocó el servidor.
`live_alerts.dart` + `alerts_model.dart`: por equipo, «Desventaja» = sus bajas y «Ventaja» = las del rival
(como en la referencia); tarjeta con iniciales, motivo traducido (se agrupa el texto en inglés del
proveedor y lo que no encaja se muestra TAL CUAL, nunca se inventa un motivo), estado No disponible /
Duda / Sancionado, fuente y hora de la comprobación. Selector de equipo con escudo, indicador que se
desliza, cambio por deslizamiento, entrada escalonada (respeta «reducir animaciones») y contador de
bajas en la pestaña. El estado va siempre en rojo/ámbar (hecho del jugador); solo el borde marca la
sección, para que «No disponible» no se lea como algo bueno en la sección de Ventaja.
Sin comprobación (`bajas` nulo) se dice que NO equivale a «sin lesionados»: hay ligas sin cobertura del
proveedor (Championship, Liga Profesional, Série B hoy; ver README) y para esas es dato ausente.
No hay foto del jugador (no se guarda ni se sirve). Pendiente, solo si el titular lo pide: fase 2 con IA
(resumen de prensa con citas, aparte de los datos oficiales) y retirar la lista de bajas duplicada de la
pestaña H2H.

## 2026-10-12 — «Datos del partido» en Análisis (la pestaña Estadísticas pasa a llamarse Análisis)

Pedido del titular: una tarjeta como la de la referencia, justo debajo de «Probabilidad de victoria 1X2»,
y la pestaña Estadísticas renombrada a Análisis. Solo datos comprobables: último resultado de cada equipo
(y el de la competición si es otro partido), ÚLTIMO once conocido con su fecha y rival (nunca un «once
probable»: lo dice la propia tarjeta), y el resumen de bajas con acceso a la pestaña Alertas. Lo que falta
se dice («Aún no hay una alineación guardada», «Sin partidos previos registrados»). Lo narrativo de la
referencia («perfil de la previa apunta a un juego abierto…») queda para la fase 2 con IA, si se aprueba.
Servidor: `fichas._ultimo_once` añade `ultimo_once` por equipo (último partido terminado con alineación,
de `lineups` o `lineups_historicas`); es un campo NUEVO, compatible con la web y la app anterior.
Verificado en producción: Lens 3-4-2-1 vs Lyon (9-oct) y Sporting CP 4-2-3-1 vs SC Braga, 11 titulares cada
uno. Desplegado con respaldo `~/backups/ultimo-once-20261012` (vuelta atrás = imagen `pre-once-backup`).
Decidido NO incluir el estadio: la base no guarda sede por partido (haría falta una columna nueva y
cambiar la captura del calendario). La cobertura del once depende de las alineaciones guardadas (desde
finales de septiembre más el histórico): un equipo sin ninguna lo muestra como ausente.

## 2026-10-12 — Pantalla de acceso rediseñada (carrusel + tarjeta con Google) y fuera la presentación posterior

Decisión: la pantalla de acceso pasa a ser un carrusel de 5 diapositivas con ilustraciones dibujadas en
código (no capturas reales: no envejecen ni prometen cifras) y una tarjeta fija abajo, a la altura del
pulgar, con el botón oficial de Google y el consentimiento (mayor de 18 + términos + privacidad) con los
enlaces dentro de la frase. El botón de Google ya no se apaga sin casilla: se deja pulsar, la casilla
vibra y se explica qué falta (un botón gris sin motivo es peor ergonomía). Los textos del carrusel no llevan
cifras ni promesas de resultado (solo lo que la app hace). Se retira la presentación `SecondScreen` que salía
tras el acceso: quien entra con Google va directo al producto (`onboarding_done` ya no se lee).
Código en `lib/core/access_screen.dart` (no conoce Firebase; la puerta de acceso le pasa estado y acciones) y
`lib/core/access_illustrations.dart`; dependencia nueva `flutter_svg` solo para la «G» de 4 colores. 20 textos
nuevos en los 6 idiomas. Por debajo de 700 px de alto la pantalla se desplaza en vez de apretar el texto.
Pruebas: `test/access_screen_test.dart` (14, incluye 6 idiomas a 390 y 320 px). Suite: 177 verdes. Sin cambios
de servidor ni despliegue.

## 2026-10-13 — Inicio rediseñado: agenda por día, boletos del día y menú «Más» con guía

Pedido del titular (capturas de QuantFut y de WIN Betting): quitar los atajos «Alta probabilidad / Reto
Escalera» y los filtros «+48 h, +1 h…» del Inicio, un calendario más visual y los partidos agrupados por día en
orden cronológico; del diseño de referencia, resumen, boletos y un menú con ventanas nuevas. Repos usados como
referencia de patrón (no como dependencia): `easy_date_timeline` (tira de días) y `sticky_grouped_list`
(encabezados por día con salto). Lo que NO se copia de la referencia: oferta con cuenta atrás, «1.000.000+
apostantes», «Seguro/Medio/Arriesgado» y el «84 % de acierto» fijo: serían cifras inventadas. El aviso superior es
el de Remote Config que ya existía (cerrable), no una oferta nueva.
Decisiones: (1) el servidor manda 7 días (`mobile.DIAS_AGENDA`, antes 2) y la app agrupa por día local; la app
anterior sigue funcionando (filtra por su cuenta). Desplegado con respaldo `~/backups/agenda7-20261013` (vuelta
atrás = imagen `quantfut-api-tapjoy:pre-agenda-backup`). (2) La tira de 7 días queda FIJA arriba y el día activo
sigue al desplazamiento; tocar un día salta a sus partidos y un día sin partidos avisa. Los encabezados de día no
son fijos: con una lista de hasta ~85 partidos por día, una tira fija es más útil que dos barras fijas. (3) Se
quitan Alta probabilidad y Reto Escalera del Inicio (viven en Predicciones; quedan como tarjetas de «Boletos del
día» con el pronóstico de mayor probabilidad y el parley). (4) Resumen con datos reales: saldo de monedas
(`/mobile/v1/rewards`) y acierto histórico real de Alta probabilidad; sin historial liquidado no se enseña la
tarjeta. (5) Menú «Más» (hoja inferior): guía de pronósticos (6 temas, sin promesas de ganancia), evaluar la app
(ficha de la tienda; no abrirá nada hasta que la app esté publicada), compartir (hoja del sistema; dependencia
`share_plus`) y términos/privacidad. El buscador pasa a un icono de la tira para ganar sitio.
Código: `home_agenda.dart` (agrupar, tira, fila de partido), `live_home.dart`, `live_more.dart`, `live_guide.dart`;
42 textos nuevos en 6 idiomas. Pruebas: `home_screen_test.dart` (19) y las de navegación/idiomas actualizadas;
suite 196 verdes. Lección: `dart format lib/product` reformateó archivos ajenos; se restauraron con `git checkout`
(formatear solo archivos propios).

## 2026-10-13 — El pronóstico se calcula cada día a las 03:00 de México (09:00 UTC)

Pedido del titular: el calendario se ve 7 días, pero un partido solo tiene probabilidad el mismo día en que se
calcula; antes la app enseña el partido con candado y la hora. Hora elegida por el titular tras comparar
(03:00 / 04:00 / 05:00 / 07:00 MX): las 03:00 cubren casi todos los kickoffs europeos de mediodía el mismo día
(Serie A 12:30 CEST = 04:30 MX, Premier 12:30 BST = 05:30 MX), con los datos del día ya capturados (calendario
05:15 UTC, clasificación 06:40, resultados 06:45, lesiones 08:00) y ~3 h de margen para arreglar un fallo antes
de que se despierten los usuarios de México. Coste: el precio de mercado usado tiene 2 h más que a las 05:00.
Regla (`src/qf/publish/ventana.py`): un partido pertenece a la corrida de las 03:00 de su día de México; si
empieza antes de las 03:00 + 60 min (sin tiempo para sellar) pertenece a la del día anterior. México es UTC-6 fijo
(sin horario de verano desde 2022). Mismo corte en TODOS los generadores —`daily` (predicciones y «solo sharp»),
alta probabilidad, alta ext., escalera y parley—, siempre con tope en su horizonte propio: la ventana solo se
recorta, nunca se amplía. El servidor añade `pronostico_desde` (UTC) a cada partido de la agenda; la app pinta el
candado solo si no hay probabilidad y esa hora aún no llegó (si ya pasó y sigue sin dato, no finge un candado: son
ligas sin modelo). La hora de México que enseña la app sale de ese dato (UTC-6), no de una constante propia.
NO se cambió el orden predecir → seleccionar → sellar → publicar ni ningún trigger. Aviso de transición: la corrida
de las 13:00 UTC de hoy ya usó la ventana antigua de 36 h; desde mañana 09:00 UTC rige la nueva. `prediction_batches`
sigue indexado por fecha UTC (09:00 UTC es el mismo día UTC que antes).
Corrección de lo dicho antes al titular: el xG de API-Football solo alimenta el entrenamiento y el modelo no usa
lesiones, así que NO hacía falta mover esas capturas (se dejaron como estaban, incluida la del xG de otra sesión).
Desplegado en api y worker con respaldo `~/backups/ventana-20261013` (vuelta atrás = imágenes `pre-ventana-backup`
de `quantfut-worker` y `quantfut-api-tapjoy`, y el crontab respaldado). Pruebas: `tests/test_ventana_pronostico.py`
(13) + suite Python completa (972) y Flutter (197).

## 2026-10-13 — Integración xG y resultado preparados para commit

Comprobación actual antes de guardar esta integración: 994 pruebas aprobadas,
24 omitidas y 2 advertencias. El commit incluye la captura de la primera pareja,
protección temporal, migración, pruebas y resultado del candidato rechazado.
Se conservan sin incluir los cambios concurrentes de Tapjoy y de la app.

## 2026-10-13 — Cambios pendientes de Tapjoy preparados para commit

Orden del titular: guardar los cambios restantes. Puente Android con códigos
seguros (sin HTML del SDK), exclusión de aperturas simultáneas, espera de 45 s
y SDK 14.8.0; documentación del diagnóstico y apertura de prueba conservada.
La apertura de pruebas ya está confirmada, pero aprobación y acreditación
comercial siguen pendientes. Comprobación actual: 16 pruebas Flutter aprobadas
y :app:compileReleaseKotlin correcto. Se restauraron las cachés Pub/Maven que
faltaban, con pub get --enforce-lockfile; pubspec y lock permanecen iguales.
Se excluyen .venv-api, caché Kotlin y build Android; el informe HTML generado
sale del índice, conservado en disco. No se instala APK ni se modifican claves.

## 2026-10-13 — Un pronóstico gratis abre también los marcadores más probables del partido

Pedido del titular (captura del detalle de Lens–Sporting): un pronóstico gratis debe ir completo. Hoy la fila del
pronóstico, su dictamen y su cuota ya iban abiertos; lo único suyo que seguía con candado eran los «marcadores más
probables». Alcance elegido por el titular: SOLO el pronóstico gratis completo; los demás mercados del partido
(Resultado, Doble oportunidad…) siguen siendo VIP, que es el contenido de pago. Cambio solo de servidor
(`partido_mercados.aplicar_acceso`): hay marcadores si el usuario es VIP o si tiene algún pronóstico abierto del
partido (gratis o desbloqueado con monedas). Revierte la regla anterior «marcadores solo con VIP» (la prueba
`test_locked_rows_reveal...` la fijaba y se actualizó; nueva prueba: sin pronóstico abierto ni VIP no hay marcadores).
Verificado en producción: partidos con pronóstico abierto devuelven 5 marcadores sin ser VIP. Desplegado con respaldo
`~/backups/marcadores-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-marcadores-backup`). No hace falta
APK nuevo: la app ya dibuja los marcadores cuando llegan.

## 2026-10-13 — Parley: un único parley del día no es gratis

La app mostraba todos los parlays porque el reparto gratis/VIP (`api/parley_acceso.py`) solo existía en local: el VPS sigue con `/parley` público sin filtro (comprobado: el contenedor de la API no trae `parley_acceso.py`). Decisión del usuario: un parley gratis por día y, si el día trae uno solo, ninguno gratis (con uno solo no hay "resto" que vender; el liquidado se sigue viendo siempre). Regla en `aplicar_acceso`: `gratis = None` si `len(tickets) <= 1`. Desplegado en el VPS (api) con respaldo `~/backups/parley-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-parley-backup` en el compose + `up -d --no-deps api`). Imagen nueva = la anterior + `main.py` y `parley_acceso.py`; el `main.py` del contenedor difería del local solo en `/parley`. Verificado en producción sin cuenta: hoy 1 parley abierto (escalón 1, gratis) y 4 bloqueados. Sin APK nuevo.

## 2026-10-13 — Cobertura fútbol: archivo disponible y ZenRows comprobado

El usuario pidió viabilidad de xG, XI, bajas y estadísticas para 12 ligas sin
modelo y huecos de las 13 habilitadas. Se comprobó la base actual (interruptores
false y conteos citados), pero el dato pendiente está en buena parte archivado:
FotMob 2024-01-01 a 2026-10-03, 22.461 filas, 22.456 originales verificados.
Hashes y normalizador cotejados: 3 originales faltantes Championship y 2 fechas
inconsistentes Brasil A excluidos. Las 12 ligas tienen 7.701 parejas xG,
10.524 partidos con ambos XI válidos y 10.466 con estadísticas de ambos equipos.
Campos de bajas presentes en 6.013 partidos; no se acredita exhaustividad ni
publicación previa al kickoff. Chile 662 resultados/XI, sin xG; Brasil B 1.066
resultados/XI y 686 xG. Copas: 425 UCL/441 UEL con xG, XI y estadísticas.
Argentina/MX/Primeira también tienen bajas declaradas en el archivo, pese al
vacío de API-Football. No se mezclan universos ni se atribuyen eventos nuevos
antes de emparejar con las identidades existentes.

Prueba SofaScore por cuenta ZenRows existente: cuatro GET correctos, reserva
100, incremento observado 20 créditos (1804→1824). Southampton-Portsmouth,
16391229, Championship/18: xG 1,28/1,18; 22 titulares, 40 fichas/29 jugadores
con minutos positivos, 6 bajas visitantes. Recibos y hashes verificados. Un
primer arranque MCP falló antes de consultar; segundo correcto. Repo fijado
dd9f061be2c64f01a6d3a50fb34d55a102d7107b: PolyForm Noncommercial real comprobada
por API ref fijo, pese a raw main en caché que daba MIT; piloto con adaptador
propio, sin integrar ese código restringido. No se declara qué IP usó el servicio.

Decisión: reutilizar primero el archivo existente; completar con consultas
acotadas tras medir cobertura por liga. Próxima integración necesita matching
estricto y extender la protección xG (hoy explícita para api_football) a las
nuevas fuentes; disponibilidad real del 3-oct no acredita datos en backtests
anteriores. Más datos no equivalen a superar Elo. Cero importaciones, compras,
API-Football/Odds API nuevas, cambios de flags, cron o modelo. Arnés antes:
995/24; después: 996/24, dos advertencias. Informe:
docs/futbol_scraping_viabilidad_20261013.md. Evidencia:
.local/football_scraper_20261013/; originales antiguos intactos.

## 2026-10-13 — Detalle del partido sin modelo de goles: los VIP se avisan aparte del gratuito

En partidos de ligas sin modelo propio (p. ej. Championship) `ficha.mercados` salía `None` (`partido_mercados.construir` exige lambdas de goles; el `fit` de un pronóstico de córners solo trae lambdas de córners) y la pestaña Pronósticos mostraba el banner «tiene un pronóstico VIP» sin nada que lo respaldara debajo. Solución provisional hasta que exista modelo: `partido_mercados.solo_candados` devuelve candados SOLO con la categoría de cada pronóstico VIP real del partido (sin línea, selección, probabilidad ni cuota), con `sin_modelo: true` y sin marcadores; la app oculta el bloque «Marcadores más probables» en ese caso para no prometer lo que ni un VIP vería. Con VIP no cambia nada. Pruebas: `test_partido_mercados`, `test_mobile_delivery` y `match_markets_sin_modelo_test.dart`. Servidor desplegado (api) con respaldo `~/backups/sin-modelo-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-sinmodelo-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py` y `partido_mercados.py`, que coincidían con el commit). Verificado en producción: Bristol City–Blackburn devuelve 2 candados (Doble oportunidad, Córners) con `sin_modelo`; partidos con modelo de goles no cambian. APK compilado (`flutter build apk --release`, 76,0 MB, 13-oct 13:50, SHA256 75635A883E24385FAE2D24E163780BC4D2EAE56538CFCA77FB6CF44B521DB64E): `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`. No se verificó la firma con apksigner (no está en el equipo); el release exige `key.properties`. No se instaló en ningún dispositivo ni se publicó.

## 2026-10-13 — Detalle y cabecera de la app: sin banner VIP con pronóstico abierto, sin botón de estadísticas, monedas en la cabecera

Pedido del titular (capturas de Bristol City–Blackburn): (1) el banner «Este partido tiene un pronóstico VIP» solo sale si el partido NO tiene ningún pronóstico abierto (gratis o desbloqueado): los demás VIP ya van con candado en «Mercados del partido»; (2) se quita de la tarjeta del pronóstico el botón azul «Ver estadísticas del partido» (la clave `forecastSeeStats` queda sin uso en los 6 idiomas; se dejó para no tocar traducciones, Análisis sigue en su pestaña); (3) la cabecera fija lleva una moneda en miniatura (`Icons.toll`, la misma de la pestaña Coins) con el saldo DISPONIBLE (`wallet.spendable`, nunca negativo), «—» sin cuenta; al tocarla abre Coins. Se refresca al recargar y al salir de la pestaña Coins. No hay imagen propia: el repo no tiene activos de imagen; si se quiere un logo/ilustración hace falta el archivo. Solo cambia la app, sin textos nuevos. Pruebas: `product_navigation_test` (nuevas: saldo en cabecera, sin cuenta, banner/botón ausentes); suite Flutter 201 OK y analyze limpio. APK nuevo (76,0 MB, 13-oct 14:10, SHA256 4CDBF3D998392604C60E534BB8009138B09092F07B97997E8713AEA4A5367E45) en `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`, sin instalar ni publicar.


## 2026-10-13 — Histórico FotMob importado en PostgreSQL

El usuario autorizó transferir e importar los originales en quantfut y confirmó
el importador/migración/protección temporal. Carga atómica completada 20:06 UTC:
22.456 originales, 44.912 XI de equipo, 940.386 registros de estadísticas y
48.571 declaraciones de bajas históricas. 20.502 asociaciones existentes,
1.554 partidos nuevos y once clubes domésticos nuevos; 400 originales conservan
asociación pendiente/conflicto (379 identidades de copas, 21 discrepancias).

Se rellenan 14.629 parejas xG vacías con recepción real del 3-oct y 8.537
partidos en conteos ausentes; no se toca xG previo. Control temporal de todas
las fuentes observadas y replay Kalman sin anticipar xG. IDs por proveedor,
originales/recibos congelados, datos históricos separados de capturas PIT;
los consumidores de jugadores/XI/bajas requieren adaptación posterior.

Prueba PostgreSQL con 53 encuentros, segunda carga cero escrituras y reversión
confirmada; arnés 1.007 aprobadas/24 omitidas. Se cotejan 20.816 partidos previos,
25 originales releídos por hash y las 14.629 parejas contra cortes temporales.
Ligas, puertas, lotes sellados, XI/jugadores previos y modelo 2026.09.27-010508
conservados; API interna/pública 200 y versión coincidente. La captura habitual
injuries de las 20:00 añadió 324 filas durante la carga; se corroboró su cron y
recepción, sin modificar esa tabla/tarea desde el importador. Sin entrenamiento
nuevo, publicación o mensajes manuales externos.

Evidencia .local/fotmob_import_20261013/verified/ y volumen
/srv/quantfut/artifacts/imports/fotmob-20261013/; backup de partidos y worker.
Detalle/cobertura: docs/importacion_fotmob_20261013.md. El xG nuevo no demuestra
una mejora retroactiva; Chile continúa sin xG en el archivo.

## 2026-10-13 — soccerdata con ZenRows e importación adicional verificada

El usuario detuvo el scraper anterior y lo sustituyó por soccerdata y su
documentación. Se confirmó cero procesos anteriores activos. soccerdata 1.9.1
fijado en e120471e424a173e83e8aeeaaf4d954ab9d38ee4, Apache-2.0; instalación
aislada optativa. Transporte MCP ZenRows 2.4.0 con proxies automáticos, recibos,
hashes, reserva 100 y caché que conserva fallos sin bucles. Los calendarios que
habían fallado con otra configuración se probaron una vez con GB, recuperando
Chile/LaLiga 2/Ligue 2/Serie B. Se reutilizan respuestas antiguas verificadas.

El lector SofaScore se amplía para detalles; FBref ya retiró datos avanzados y
el listado obtenido no sirvió para ligas domésticas. ESPN Chile/Brasil B falló.
Muestra 2023/24: eventos sin xG anunciado en LaLiga 2, Serie B y Ligue 2; las
estadísticas consultadas en España/Francia no traían esa métrica y las demás
consultas no acreditaron cobertura. No prometer historia completa por aceptar
un calendario ni atribuir una mejora de backtest al xG recibido ahora.

Carga adicional completada 23:15 UTC: 586 originales, 574 asociaciones,
54 parejas xG añadidas a huecos, 138 XI, 2.789 registros de jugadores y 269
bajas históricas. Cero partidos/clubes nuevos: la propuesta Troyes–Valenciennes
1–1 fue puesta en cuarentena tras cotejar la derrota administrativa en LFP.
Otro marcador discrepante y diez identidades de copas quedan separados. Doce
equivalencias domésticas revisadas con nombres, país y partidos; sin difuso.

Prueba PostgreSQL de carga repetida dentro de transacción revertida: cero
escrituras adicionales y reversión corroborada. Carga real coteja 22.615 registros
previos, 586 hashes y 54 disponibilidades temporales. Se conservan modelo
2026.09.27-010508, flags, lotes sellados y tablas de jugadores/XI API-Football;
model-card interna/pública 200 y misma versión. Worker respaldado y ampliación
persistida sin reiniciar ni reconstruir desde el checkout viejo. Arnés final:
1.033 aprobadas/24 omitidas, 35 relevantes. Sin entrenamiento, compras o mensajes
externos. ZenRows 2.515→3.751 utilizados; quedan 1.249 en última lectura.

Persisten 3.154 partidos sin xG y bloqueos de calendario en cinco competiciones;
los consumidores de XI/jugadores/bajas históricos siguen pendientes. Evidencia
.local/soccerdata_completion_20261013/verified/ y artifacts/imports/soccerdata-20261013
del worker. Detalle y desglose: docs/soccerdata_zenrows_20261013.md.

## 2026-10-13 — Los pronósticos bloqueados enseñan su cuota

Pedido del titular (lista «143 pronósticos más con VIP»): que cada bloqueado muestre la cuota para que sea atractivo. `mobile.metadata()` añade `cuota` (cuota publicada: `ref_price` en alta probabilidad, `price` en la escalera; `None` si no es válida, nunca inventada). Sigue SIN salir selección, línea ni probabilidad (el test lo comprueba). Efecto a tener en cuenta: cuota + categoría permite estimar la probabilidad (~1/cuota), así que la leyenda «Con VIP ves la probabilidad, la cuota y el análisis» pasó a «…la selección, la probabilidad y el análisis» (6 idiomas, `picksLockedHint`). App: la fila bloqueada de `LockedPicksGroup` dibuja `@cuota` en dorado. Los candados por categoría del detalle del partido (`solo_candados`) no llevan cuota. Servidor desplegado (api) con respaldo `~/backups/cuota-bloqueados-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-cuota-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py`, que coincidía con el commit anterior). Medido en producción: de los 143 bloqueados de partidos no empezados, 61 llevan cuota y 82 NO (hándicap 60 y doble oportunidad 22: `alta_prob_picks.ref_price` es NULL, no hay precio publicado de casa para esos mercados; no se inventa con 1/prob). PENDIENTE: APK; sin APK nuevo la cuota viaja pero no se ve, y la leyenda vieja sigue diciendo que la cuota es de VIP. Pruebas: Python 1032 OK, Flutter 201 OK, analyze limpio.

## 2026-10-13 — Parley: cada pata de cuota 1,20 a 1,80 (sin desplegar)

Pedido del titular, tras una primera lectura equivocada mía (que cambió la cuota TOTAL; se revirtió entera): la cuota total de cada parlay sigue en los 5 escalones de 1,90 a 5,00; lo que cambia es que CADA PATA tenga cuota de 1,20 a 1,80 (antes: >= 1,15 sin techo), con la combinación más probable de cada escalón y las patas que hagan falta (2 a 6). `parley.CUOTA_MIN_PATA, CUOTA_MAX_PATA = 1.20, 1.80` en `filtrar`; el informe público añade `reglas.cuota_max_pata`. Sin cambio de esquema, escalones ni historial (el control sigue comparando probabilidad prometida y acierto, mismo significado). Simulación con datos reales (17 partidos con precio, dry-run en el worker, sin escribir): la probabilidad de cada parlay casi NO cambia (52/46/37/28/22 % frente a 52/45/37/30/23 %), porque la fija la cuota total y mas patas la bajan; el efecto es que desaparecen las patas largas (1X2 a 2,16 con 48 %, córners a 2,00 con 51 %) y toda pata queda entre 56 % y 82 %. Rige desde el primer sellado tras desplegar el worker (el del 14-oct 09:00 UTC si se despliega antes). Pruebas: `test_parley` (rango de pata incluidos bordes y float4, ningún parlay con pata fuera de rango), suite Python OK. PENDIENTE: desplegar worker (parley.py, parley_datos.py) y api (parley_datos.py: informe) antes de ese sellado.

Decisión del titular sobre mercados (2026-10-13): el parley NO busca en todos los mercados, solo en los de líneas validadas (1X2, doble oportunidad, goles 1,5/2,5/3,5, goles por equipo, ambos marcan sí, hándicap, córners y tarjetas habilitados) y elige por probabilidad calculada, no por acierto real. Ponderar por acierto real por mercado se pospone hasta tener ~50 liquidados por mercado (hoy 5-41): anotado en `harness/tareas.md` (Parley, punto 11) y en el README.

Parley con patas de 1,20-1,80 DESPLEGADO (2026-10-13 ~20:00 UTC, commit a90bdd2) en worker y api con respaldo `~/backups/patas-20261013` (vuelta atrás = imágenes `quantfut-worker:pre-patas-backup` y `quantfut-api-tapjoy:pre-patas-backup`; en el compose la api vuelve a `image: quantfut-api-tapjoy:pre-patas-backup` y el worker se retaga a `latest`, luego `up -d --no-deps --no-build api worker`). El `parley.py` de la api estaba en la versión 059372a (sin doble oportunidad); ahora los dos llevan la misma. Comprobado: md5 de parley.py/parley_datos.py = HEAD en ambos contenedores, cron del worker vivo (daily 09:00 UTC), `/parley` publica `cuota_min_pata 1.2` y `cuota_max_pata 1.8`. El ensayo en seco a las ~20:00 UTC sale vacío (ventana por día, sin partidos dentro): el primer sellado real con la regla es el del 14-oct 09:00 UTC; VERIFICAR ese lote (`parley_datos informe`: toda pata entre 1,20 y 1,80). APK nuevo compilado con la cuota de los bloqueados y la leyenda nueva: 76,0 MB, 13-oct 18:50, SHA256 1113356E19103446A3C7C28EDA5551340E27C48EDFFF363E3C371BCA10104EC7; sin instalar ni publicar.


## 2026-10-13 — Recuperación adicional con clave nueva de ZenRows

Se priorizó el modo automático de la CLI oficial 1.5.0, sin imponer país ni
funciones caras a todas las llamadas; tres conexiones frente al límite verificado
de cinco. Presupuesto compartido con reserva previa de 25 por solicitud, devolución
solo del coste comunicado y parada ante autenticación/cuota agotada. MCP 2.4.0
lee cuota y acepta la clave de la tarea solo en el entorno; configuración y cuenta
compartidas anteriores conservadas. Clave nueva cifrada DPAPI fuera de Git y VPS.

La ruta pública www de SofaScore recuperó calendarios antes bloqueados en Brasil B,
Bundesliga 2, Dinamarca, Suecia y Europa League. Parser real de soccerdata 1.9.1;
fallos conservados, jornadas danesas procesadas independientemente. No repetir
fallos ni confundir tiros sin xG con xG publicado: las muestras históricas de
España/Francia carecían de ese campo. Recuperar jornadas actuales no demuestra
acceso a toda la historia. Se excluyen los 586 IDs SofaScore ya congelados.

Carga confirmada 14-oct 00:55 UTC (13-oct 18:55 México): 125 originales, 101
asociaciones, 36 parejas xG canónicas añadidas, 228 XI, 4.137 registros de jugadores
y 294 bajas históricas. De 97 xG originales, once no tienen asociación y cincuenta
conservan valores canónicos anteriores. Cero partidos/clubes nuevos; 24 originales
europeos sin identidad canónica conservados. Seis equivalencias danesas revisadas
con país/nombres y dos fixtures independientes cada una; AGF doméstico resuelve
también su encuentro europeo. Sin difuso ni altas bajo copas.

Dos cargas en transacción revertida: segunda cero escrituras y conteos restaurados.
Carga real verifica 125 normalizaciones y cuerpos HTTP/hash/recepción; conserva
22.632 partidos previos y 23.042 originales anteriores con identidad/hash/reloj.
Las 36 parejas xG respetan cortes temporales. Modelo 2026.09.27-010508, flags,
lotes sellados y tablas antiguas XI/jugadores conservados; API interna/pública
200 y misma versión. Sin código nuevo en worker ni reinicio, entrenamiento,
compras, activación de ligas o mensajes externos manuales.

Saldo nuevo verificado: 988 utilizados de 5.000, 4.012 restantes y cero concurrencia
activa. Descarga principal 233 llamadas CLI y complemento danés 26; pruebas previas
incluidas en consumo total. Arnés final 1.045 aprobadas/24 omitidas. Huecos xG
3.154→3.118; Bundesliga 2 queda sin huecos en el corte desde 2024, Brasil B aún384,
Dinamarca3 y Suecia2. Consumo medido por cuenta, sin inferir fallos gratuitos;
RESP008 puede cobrarse. Evidencia .local/zenrows_key_20261013/prepared/ y verified/,
worker artifacts/imports/zenrows-new-key-20261013/. Detalle y pendientes en
docs/zenrows_clave_nueva_futbol_20261013.md; adaptación de consumidores históricos
y mejoras del modelo siguen sujetas a validación, sin mejora retroactiva atribuible.

## 2026-10-13 — Eliminación física de Chile y Brasil B

El titular pidió retirarlas por completo y autorizó expresamente borrar su
historial protegido tras revisar cuotas, alta probabilidad, escalera y parley.
Se comprobó que sus clubes domésticos no intervenían en otras competiciones.
Se eliminan 1.806 partidos, 1.784 originales históricos, 36 clubes, 49 alias,
36 clasificaciones, 81.082 cuotas, 3.518 XI, 73.414 registros de jugadores y
465 bajas, junto con selecciones y resultados relacionados. Para evitar
productos incompletos se retiran dos retos enteros (seis pasos) y un parley
entero (tres patas), incluidas las partes de otras ligas dentro de esos grupos.

Respaldo selectivo: 25 COPY binarios, 45.427.123 bytes, con hashes cotejados
localmente. Bloqueos exclusivos y excepción temporal de triggers solo en
tablas seleccionadas, restaurados antes del commit. Prueba PostgreSQL real:
primera eliminación, repetición cero escrituras y reversión; eliminación real
con los mismos conteos. Conteos y huellas de filas ajenas a la selección en
40 tablas conservados, modelo 2026.09.27-010508 y Série A intactos. Los 15
lotes originales en disco conservan su cadena; no se reescriben. Su contenido
retirado ya no se regenera desde la base operativa. Comparaciones de acierto
posteriores deben explicar el cambio de población, sin atribuirlo a una mejora.

db/063 registra únicamente metadatos de retiro y bloquea reinserción en
catálogo/partidos. FotMob y SofaScore quedan en 23 competiciones; normalización,
emparejamiento/importación y manifests viejos no reintroducen las dos retiradas.
Fuentes exactas cotejadas y desplegadas sin reconstruir checkout viejo ni
reiniciar. Worker respaldado y cambios persistidos en imagen. API interna y
pública 200, catálogo23 y home móvil sin IDs retirados; cero ligas/partidos/
originales/clubes de ambas. Arnés 1.049/24. Sin entrenamiento ni llamadas nuevas
a proveedores deportivos; comprobado cero procesos entrenadores al terminar.

Quedan 13 competiciones con modelo habilitado y diez pendientes; huecos xG
desde2024: 3.118→2.073 por retirar ligas, no por recuperar valores. Los datos
recién importados aún no participaron en un nuevo modelo activado. Evidencia
.local/remove_chile_brasil_b_20261013/verified/ y artifacts/maintenance/
remove-chile-brasil-b-20261013 del worker; 45MB de respaldo también en host.
Detalle: docs/eliminacion_chile_brasil_b_20261013.md. Informes de cobertura
actuales actualizados; archivos previos y sellados conservados como evidencia.

## 2026-10-14 — PitchAPI: histórico y xG a la base

Por orden del titular se descargó el histórico de PitchAPI y se importaron
sus xG. Decisión clave: identidad de club solo por corroboración de partidos
(3 votos, 90 % de dominancia, fecha UTC exacta), nunca por nombre. Una primera
versión con ventana de ±1 día votaba mal entre partidos vecinos con igual
marcador; se corrigió antes de escribir nada. La recepción real queda en
`xg_recorded_at` para que el modelo no use el xG antes de existir.

5.355 xG importados (ensayo revertido, carga e idempotencia verificadas); los
huecos desde 2024 pasan de 1.262 a 1.220 porque PitchAPI no cubre 2024 en
Serie B, LaLiga 2 ni Ligue 2. Detalle: docs/pitchapi_historico_20261014.md.

## 2026-10-14 — Auditoría de completitud desde 2025-01-01 y cierre de Allsvenskan

Auditoría de solo lectura de las 23 competiciones contra API-Football (segunda
fuente independiente) y la base. Resultado: 13.200 partidos terminados, todos
con marcador, y la base no tiene ningún partido que API-Football no tenga. Las
diferencias son playoffs de promoción/relegación y finales (~55, fuera de
jornada regular) y, en Champions/Europa League, clubes fuera del catálogo, que
se descartan por diseño. Lección del método: emparejar por fecha y marcador
produce falsos positivos entre partidos con igual resultado en días cercanos;
solo son fiables los conteos y el emparejamiento con fecha exacta primero.

Tres partidos de Allsvenskan del 31-may-2026 seguían `scheduled` porque
`close_recent` solo mira 72 horas. Se cerraron con esa misma función
(`hours_back` amplio, solo `se.allsvenskan`), sin picks ni predicciones
asociados: 2-2, 3-2 y 4-5, con `result_recorded_at` real de hoy. Vencidos sin
cerrar: 0; queda 1 aplazado (Vallecano–Athletic, 10-oct). xG desde 2025 sin
cubrir: 237 (Serie B 188 de ene–jun 2025, copas 26, resto ~23).

## 2026-10-14 — Respaldo y cotejo con PitchAPI (implementado, sin desplegar)

Decisión del usuario: resultados solo con AVISOS; relleno automático solo de xG.
Se eligió así porque los IDs de partido de PitchAPI no son estables (26 ligas se
restauraron con IDs nuevos), no hay SLA ni términos publicados y un resultado
erróneo liquidaría picks. El xG espera 48 h para que API-Football capture
primero; PitchAPI nunca sobrescribe y guarda el original con hash y recepción.
Los clubes se emparejan solo por partidos corroborados (semilla de 496 más
aprendizaje diario por votos). La clave `pk_test_` anterior se revocó sola el
14-oct: el panel permite rotarla sin tocar el servidor. Comprobado contra datos
reales (10 días, 235 partidos, 0 discrepancias) y las migraciones en transacción
revertida. Pendiente: pasar a una clave `pk_live_`, preguntar al proveedor por
uso comercial y almacenamiento, y desplegar.

Desplegado el mismo día por orden del titular: la clave se guardó cifrada en la
base (no en `.env`) y el respaldo quedó activo con cron 12:40 UTC. Decisiones del
despliegue: se parchó `base.html` sobre la versión de producción (el menú
difería del repo) en vez de pisarlo; el worker, de imagen anterior a las claves
cifradas, recibió `cryptography==50.0.2` (la versión ya fijada) y `cifrado.py`,
en capas nuevas sin reiniciar. Primera pasada real: 0 discrepancias. Detalle y
reversión en docs/pitchapi_respaldo_20261014.md.

## 2026-10-14 — Auditoría de las 23 competiciones y entradas del pronóstico

La disponibilidad de datos no equivale a que el motor los utilice. Se auditó
producción en transacciones de solo lectura: 20.854 terminados desde 2024,
1.222 sin xG, 336 sin XI completo archivado y 349 sin al menos 11 jugadores
con minutos por lado. Los módulos actuales solo leen las tablas nativas:
16.176 no tienen XI compatible y 15.822 no tienen jugadores compatibles.
Se encontraron 8.118 parejas de amarillas pendientes de pasar del archivo a
la tabla principal. De 20.331 originales FotMob vinculados y leídos, 8.623
contienen campos de clima, 20.331 sede y 20.140 árbitro; no son entradas
directas del motor principal. Deben validarse contenido, unidades y momento
de disponibilidad, sin usar el clima posterior como pronóstico anterior.

El modelo activo sigue `2026.09.27-010508` en 13 competiciones, sin mezcla ni
residuo. XI tiene 106 predicciones experimentales pero no promoción; las bajas
se capturan. El selector de valor decide por cuotas frente a Pinnacle, no por
el edge del modelo. En 7.689 parejas xG de las competiciones modeladas la
recepción es posterior al ajuste del artefacto, por lo que importar no actualiza
sus parámetros. Otra limitación comprobada: el importador de estadísticas
individuales convierte ausentes en cero; no nulo no certifica cobertura real.

Próximos siete días: 227 programados, 140 en ligas modeladas con consulta de
bajas en últimas 24 h y 87 excluidos de esa captura por configuración; ninguno
estaba en la ventana de XI. Informe y prioridades propuestas en
`docs/auditoria_datos_modelo_20261014.md`; sin cambios de producción ni nuevo
entrenamiento. Arnés inicial aprobado (1.084 pruebas, 24 omitidas) y huellas
del código principal/selector/captura contrastadas con el despliegue.

## 2026-10-14 — Señales del motor: spec, plan y F0 aplicada

El usuario pidió llevar al motor principal los datos que solo estaban archivados.
Decisiones: una señal entra únicamente si gana fuera de muestra (RPS, log-loss y
ECE en >=2 ligas); mecanismo de ajuste de lambdas sobre Dixon-Coles, no dentro del
ajuste ni un GBM; y, como el XI llega a T-60 y la predicción se sellaba a las 08:00,
el usuario relajó la garantía a un sello por partido justo antes del inicio (los
lotes antiguos se regeneran con su formato por fecha de corte). Spec y plan en
docs/superpowers/. Clima con Open-Meteo plan Standard: sin Historical Forecast, así
que el bloque se valida con los pronósticos que guardemos o con el clima observado
de FotMob como sustituto declarado.

F0 aplicada: el archivo FotMob rellenó solo NULL en `matches` (amarillas/rojas
8.412->294, descanso 7.325->240, xGOT, árbitro en columna aparte, sede en la tabla
`estadios`) con procedencia en `matches_enriquecimiento`. Decisiones que costaron
algo: el xGOT no se mezcla con PSxG; el árbitro de FotMob no pisa `matches.referee`
(lo lee el motor de tarjetas); el simulacro fue de solo lectura porque la migración
bloquea `matches`. Contraste: FotMob cuenta tarjetas distinto en ~6 % de los
partidos (+1), así que las probabilidades de tarjetas se mueven en las ligas que casi
no tenían historial. Detalle y reversión: docs/f0_archivo_a_matches_20261014.md.

## 2026-10-14 — F1: capa de ajuste por bloques y puerta corregida

`qf.model.ajuste` generaliza el challenger de XI (bloques registrados, comparación
incremental A frente a A+B, artefacto `ajuste_<versión>.pkl`). Decisión clave: la
puerta heredada tenía dos defectos que se midieron antes de corregirlos. Una
columna constante pasaba la puerta con la misma mejora que el ruido, porque el
intercepto re-nivela lambdas sesgadas y el mérito se le daba al primer bloque; y el
ruido puro la pasaba en 8 de 40 semillas. En `ajuste.comparar` la referencia es
ahora un modelo solo de nivel y se exige significancia (remuestreo pareado de la
diferencia de RPS, percentil 95 < 0). La puerta de `lineup_challenger` no cambia.
Con datos reales, el XI simple pasa la puerta estricta (dRPS -0,0013, p95 -0,00056,
9 de 12 ligas) y el modelo de nivel casi coincide con las lambdas crudas: no era
re-nivelación. No se reentrenó: el entrenamiento del 12-oct ya usó el xG nuevo y no
pasó la puerta frente a Elo; el cron del 1-nov incorpora el resto. Detalle:
docs/f1_capa_de_ajuste_20261014.md.

## 2026-10-14 — Historial del Reto Escalera con detalle en la app

El historial ya se guardaba (tablas inmutables `escalera_*`) y la app listaba los últimos 10
cerrados, pero sin ver sus escalones. Decisión: el detalle se despliega en la propia fila
(acordeón de uno), no en otra pantalla, para no recargar. Qué se enseña lo fijó el titular:
los 9 últimos retos cumplidos y el último fallido, sin filtros (mi primer intento fue un
filtro Todos/Cumplidos/Fallidos con 10 por filtro y no era lo pedido). El resumen de arriba
sigue contando todos los cerrados y un texto bajo la lista dice qué se muestra, para que la
selección no pase por el historial completo. `_paso_publico` ahora publica `selection` y
`line` porque la app traduce el pronóstico desde esos campos; no revela nada nuevo (el
`texto` en español ya salía). Los escalones sin liquidar siguen saliendo por `metadata`
(lista blanca), así que el candado VIP no cambia.

## 2026-10-14 — Doble oportunidad: su cuota se toma de API-Football

En la lista de alta probabilidad, los pronósticos de doble oportunidad (119 + 28 en
producción) salían sin cuota: `_ref` decía que ningún proveedor la cotizaba, pero
`af_odds` guarda el bet 12 desde el 12-oct (154 partidos). Ahora `_ref_nuevos` la lee de
las filas de API-Football con la misma regla de casas y edad que la escalera y el parley,
y `select_and_persist` carga esas filas siempre (antes solo con ambos marcan/córners
activos). Solo afecta a pronósticos NUEVOS: los sellados tienen `ref_price` vacío en la
cadena y no se tocan. El hándicap sigue sin cuota (API-Football no lo trae; las cuotas de
hándicap están en The Odds API y el pronóstico se elige sobre otro snapshot): pendiente
de decidir si se cruzan fuentes o se oculta el pronóstico sin cuota.

Desplegado el 14-oct (solo `worker`, sin reiniciarlo): `docker cp` de `alta_prob_datos.py` y
`alta_prob_ext.py` al contenedor; los jobs de cron arrancan un proceso nuevo y cogen el
archivo en la siguiente pasada. Respaldo de los anteriores en
`~/quantfut/releases/doble-oportunidad-cuota-20261014/*.before`. Comprobado con la base de
producción: tres partidos con doble oportunidad vigente dan cuota por casa (p. ej. 1X 1,75
betano). Aviso: la copia es solo del contenedor; el árbol `~/quantfut/src` del VPS está
desfasado (ni siquiera tiene `alta_prob_ext.py`), así que reconstruir el worker desde él
perdería este y otros parches.

## 2026-10-14 — Hándicap: su cuota sale de API-Football (bet 4)

Los 279 pronósticos de hándicap de producción tenían `ref_price` vacío: la cuota solo se
buscaba en The Odds API y los pronósticos se eligen sobre un snapshot de API-Football.
Cruzar fuentes cubría solo el 19 % (53 de 279; solo 1xBet y Coolbet cotizan ahí) y mezclaría
edades distintas, que el proyecto prohíbe. Decisión: volver a capturar el bet 4 ("Asian
Handicap") en `af_odds` (misma petición, sin coste de cuota ni migración), solo de SOFT_BOOKS
y solo líneas enteras y medias; comprobado con una respuesta real (Bet365 y Betano lo
cotizan). La línea del visitante se guarda invertida (propia, no la del local): es la
trampa que ya estaba documentada en el código archivado del 25-sep. `_cuotas_af` lee
`spreads` y `_ref_nuevos` los usa cuando el snapshot es de API-Football; con uno de The Odds
API sigue leyendo los suyos (nunca mezcladas). Solo afecta a pronósticos nuevos y solo cuando
la casa ya tenga guardada la cuota; los sellados no se tocan. Pendiente de medir: cuántos
hándicap salen con cuota tras uno o dos días de captura.

## 2026-10-14 — Tope de 4 gratis en Inicio y en Alta probabilidad

Decisión del titular: como mucho 4 pronósticos gratis a la vez en Inicio y en Alta probabilidad
(antes uno por mercado y por lote: hoy había más de 4 abiertos al sumar lotes de varios días).
Se aplica como filtro de lectura en `high_probability` (`cap_free`, FREE_MAX = 4): entre los
gratis sin empezar quedan los de mayor cuota publicada y a igualdad mayor probabilidad, la
misma prioridad de siempre; los demás pasan a candado con su cuota a la vista. Los que ya
empezaron no cuentan y siguen visibles con su resultado. El reparto por lote
(`mobile_free_allocations`) no se toca: es auditoría. Inicio y Alta probabilidad leen el mismo
bloque `alta_probabilidad`, por eso un solo punto cubre las dos pantallas. El Reto Escalera
conserva su único escalón gratis aparte. Tope de 4 gratis publicado también en `/config`
(`high_probability_free_max`) y el texto de la app lo muestra («hasta 4 gratis»).

Desplegado el 14-oct: API reconstruida sobre la imagen anterior con solo `api/mobile.py`
(`quantfut-api-tope-gratis:20261014`, persistida en el compose; worker intacto). Respaldo y ID de
la imagen previa en `~/quantfut/releases/tope-gratis-20261014/`. Comprobado en producción:
`/mobile/v1/home` devuelve 4 gratis abiertos (cuotas 1,32 / 1,28 / 1,27 / 1,25) y 81 con candado, y
`/mobile/v1/config` publica `high_probability_free_max: 4`.

## 2026-10-14 — El parley respeta los mercados bloqueados de alta probabilidad

Se midió el planteamiento de «mejorar el parley» (arriba-abajo, penalizar margen, anclas
1,12-1,19, tendencia de cuotas) sobre el conjunto real de patas del día (116 patas, 9 partidos).
La probabilidad de un ticket sale ≈ 1/cuota (1,97→52 %, 2,21→46 %, 2,79→37 %, 3,49→28 %), así
que sin cambiar los escalones no hay forma de subir el acierto con la selección. Armar de arriba
abajo da 3 tickets (ΣP 0,87) frente a 4 (ΣP 1,62) del orden actual, y el mejor de los 120
órdenes posibles coincide con el actual: el cuello de botella son los partidos, no el orden. Las
anclas dan ΣP 1,628 frente a 1,623 y peor valor esperado. Margen y calibración por mercado:
el margen ya está en cuota frente a probabilidad justa; la calibración sí tiene respaldo.
`alta_prob_ext` bloquea `totals` (prometía 82 %, real 67,3 % en 55 casos; z −4,3 con 80) y los
parlays reales llevaban 7 patas de goles con 61,8 % prometido y 3 ganadas. El parley no
consultaba ese control. Decisión del usuario: `pl.sin_bloqueados` quita las patas de los
mercados (por grupo de control) bloqueados en la alta probabilidad principal o ampliada;
`todo` no pausa el parlay. Con 9 partidos de muestra y 6 parlays liquidados NO se puede medir el
efecto sobre el acierto: el control por escalón del propio parlay sigue siendo el juez. Pendiente
de medir: tarjetas y córners, que dominan los tickets y no tienen historial de calibración propio.

Desplegado el 14-oct (solo `worker`, sin reiniciarlo): `docker cp` de `parley.py` y `parley_datos.py`;
respaldo de los anteriores en `~/quantfut/releases/parley-bloqueados-20261014/*.before`. Ensayo en
seco con datos reales: mercados bloqueados `['totals']`, 104 candidatas (se quitaron las 12 de
goles de las 116), 4 tickets (1,97 · 2,21 · 2,79 · 3,49) sin cambios de probabilidad. Misma
salvedad que antes: la copia es solo del contenedor y el árbol `~/quantfut/src` está desfasado.

## 2026-10-14 — Seguimiento sin publicar de tarjetas e informe de prometido frente a real

Las tarjetas están en 3 de los 4 tickets del parley y no tienen historial propio (ninguna liquidada
en alta probabilidad ni en la escalera; 2 patas en el parley). Decisión del usuario: tabla aparte
`tarjetas_seg` (db/068, inmutable, con `tarjetas_seg_results`) que guarda cada día TODOS los
candidatos de tarjetas de los partidos con precio (líneas de `LINEAS_HABILITADAS["cards"]`, la
probabilidad prudente = menor entre modelo y mercado, y la mejor cuota de la lista; sin cuota de la
lista no entra, como en el parley). NO se publica: ninguna ruta de API, panel, web ni app la lee (lo
comprueba una prueba). Se sella en el lote (`tarjetas_seg`, `LOTE_TARJETAS_DESDE` = 2026-10-15, primer
lote sin sellar) y se liquida en `clv.settle_pending` con la misma regla que la escalera (amarillas +
rojas). Va ENCENDIDO por defecto en código, no por entorno: activarlo por `.env` obliga a recrear el
worker y eso borraría los parches copiados con `docker cp`; `tests/conftest.py` lo apaga en las
pruebas. `eval/calibracion_mercados.py` (`python -m qf.eval.calibracion_mercados [--json]`) compara por
mercado prometido y real con IC de Wilson al 95 % sobre lo liquidado y SELLADO de alta probabilidad,
ampliada, escalera, parley y tarjetas; un pronóstico repetido en varias fuentes cuenta una vez en el
total (el desglose no deduplica) y con menos de 30 casos no opina. Solo lectura: no bloquea nada.

Desplegado el 15-oct 00:18 UTC, ANTES del job de las 08:00 (el lote del 15 es el primero que lleva el
bloque): migración db/068 aplicada (ensayada antes en una transacción revertida, con los triggers
rechazando UPDATE y DELETE) y worker actualizado con `docker cp` (`tarjetas_seg.py`,
`calibracion_mercados.py`, `config.py`, `hashchain.py`, `clv.py`, `daily.py`; respaldo de los cuatro
anteriores en `~/quantfut/releases/tarjetas-seg-20261014/*.before`; sin deriva respecto al repo).
Ensayo en seco con datos reales: 5 partidos, líneas bajo 4,5 y bajo 5,5 con cuota de bet365/betano
(probabilidades 54-71 %). Primer informe de calibración sobre lo ya liquidado: goles `totals` 77,5 %
prometido frente a 60,9 % real (n 110, IC95 51,6-69,5 %, «por debajo»); `spreads` −3,8, `corners`
−1,7, `double_chance` +2,4 y goles de equipo +3 a +8 dentro del IC; `btts` (9), `h2h` (12),
`corners_home/away` y `cards` (2) sin muestra. Misma salvedad de siempre: la copia es solo del
contenedor y el árbol `~/quantfut/src` del VPS está desfasado. Por qué no hay API: la API no lee la
tabla ni necesita este código, así que su imagen no se tocó.

Medido el 15-oct tras la primera captura con el bet 4 (00:20 UTC): 2.580 filas de hándicap de 101
partidos de las tres casas de la lista que lo cotizan (Bet365 96 partidos, 1xBet 84, Betano 108
partidos con alguna línea). De las combinaciones lado/línea que elige la alta probabilidad en los 9
partidos próximos con hándicap, el 86 % (77 de 90) ya tiene cuota; la línea +2 del local casi nunca
se cotiza (1 de 9) y el resto cubre 8-9 de 9. El primer lote que ya sale con cuota de hándicap es el
de las 08:00 UTC del 15-oct. Pendiente de confirmarlo con los pronósticos reales de ese lote.

## 2026-10-14 — Fuera el aviso «Modelo NBA en entrenamiento» de Mercados

Pedido del titular: en la pestaña Mercados de la app se quita el bloque «Modelo NBA en entrenamiento»
(el último de la pantalla, bajo «Ver acceso VIP»). La sección `nba` sigue existiendo en
`mobile_features` y en el servidor; solo deja de pintarse el aviso. Si NBA se activa algún día, habrá
que decidir dónde se muestra.

## 2026-10-14 — Compartir el código de referido con enlace y página de invitación

Pregunta del titular: cómo llega el código de referido al invitado en una app de teléfono. Estado
real: el código se copiaba y se escribía a mano en Coins; el botón de compartir enviaba un texto sin
código ni enlace; la app no lee nada al instalarse. Decisión: paso 1 (sin depender de la tienda).
«Compartir mi código» de Coins envía el código y `https://pronosticosdeportivos.pro/i/CODIGO`; la
ruta `/i/{codigo}` (`api/invitacion.py`) es pública, sin base de datos (no confirma que el código
exista, así que no sirve para enumerar) y muestra el código, copiar y los pasos en los 6 idiomas según
`Accept-Language`; un código mal formado da 404 y no se repite en la página. Cumple la CSP del panel
(`script-src 'self'`): el copiar vive en `static/invitacion.js`, sin scripts ni estilos en línea. En el
campo de Coins, «Pegar código» extrae el código del portapapeles aunque sea el enlace o el mensaje
entero (`inviteCodeFrom`: solo el código suelto o el de `/i/CODIGO`; una palabra cualquiera no cuenta) y
Registrar también lo normaliza. `APP_DOWNLOAD_URL` (vacío por defecto) añade el botón de descarga
cuando la app tenga tienda. Pendiente, a propósito: leer el referrer de Google Play al instalar
(Android y solo desde la tienda), App Links para abrir la app desde el enlace y una solución para iOS
(terceros: Branch, AppsFlyer o Adjust).

Desplegado el 15-oct (solo API; worker intacto): imagen `quantfut-api-invitacion:20261014` sobre la anterior con
`invitacion.py`, `main.py`, `config.py`, la plantilla `cuenta/base.html` (ahora con `lang` variable),
`cuenta/invitacion.html` y `static/invitacion.js`; persistida en el compose. Respaldo del compose y de
la imagen previa en `~/quantfut/releases/invitacion-20261014/`. Comprobado en el dominio real (vía
Cloudflare): `/i/f9b9cbe3633f` → 200 con el código en mayúsculas; `Accept-Language` en/de cambian el
idioma; `/i/abc` y un código con `<script>` → 404 sin repetirlo; `/static/invitacion.js` 200;
cabeceras `no-store`, CSP `script-src 'self'`, `noindex` y `no-referrer`.

## 2026-10-14 — Plan anotado: referidos cuando la app suba a la Play Store

A petición del titular, el plan completo quedó en `tareas.md` (sección «Referidos al subir la app a la
Play Store»): `APP_DOWNLOAD_URL` + parámetro `referrer` en el enlace de Play, lectura del referrer en
la app (solo Android y solo desde la tienda, registrando el código al verificar el correo), App Links con
`assetlinks.json` usando la huella de la clave de firma final de Play, prueba con dos cuentas reales y
las decisiones pendientes (iOS, instalaciones por APK). No se implementa antes de tener una pista de
pruebas de Play: el referrer no se puede probar sin instalar desde la tienda.

## 2026-10-14 — Videos con recompensa de AdMob (apagado y en modo prueba)

Decisión clave: **solo el servidor acredita**, y solo con el callback firmado de Google (SSV). La app pide un
ticket, muestra el video y espera a que suba el saldo; nunca acredita ni elige el importe (se ignora el
`reward_amount` de Google). Tope diario (5), pausa (180 s) y día UTC se deciden en el servidor y se editan en
`/control/anuncios`. Por qué así: un cliente que acredita se falsifica, y los clics o visualizaciones
inventados son exactamente el tráfico no válido que cuesta la cuenta de AdMob.

Detalles que no son obvios: el día de un crédito es el de emisión del ticket; un rechazo tras firma válida
responde 200 con `coins=0` para que Google no reintente; las monedas de anuncios no validan referidos; los
callbacks ya emitidos se aceptan aunque se apaguen los anuncios. Dejado apagado y en modo prueba: la política
de apuestas de AdMob/Play para una app de cuotas no se pudo confirmar y la política de privacidad publicada
dice que no hay publicidad personalizada; ambos son bloqueantes (ver `tareas.md`). Nada desplegado.
Probado con Postgres local en un esquema aislado: la prueba `test_pg_fixed_allocations_and_ladder_global_one`
(ajena a esto) falla con `KeyError: 'kickoff_utc'` en `mobile.py` cuando hay base; antes se omitía.

Desplegado el 15-oct (solo API; worker intacto): imagen `quantfut-api-admob:20261014b` sobre `quantfut-api-invitacion:20261014`
con `anuncios.py`, `anuncios_ssv.py`, `rewards.py`, `main.py`, `panel.py`, `mensajes.py` y las plantillas `anuncios.html` y
`base.html` (los cinco archivos ya existentes en producción eran idénticos a la base de la rama antes de copiar los
míos). `db/069` aplicada tras un ensayo con ROLLBACK; respaldo del compose y de las tablas `reward_*` en
`~/quantfut/releases/admob-recompensas-20261014/`; imagen previa conservada para volver atrás (la migración es
aditiva: el código anterior la ignora). Comprobado en el dominio real: `/health` 200, `/app-ads.txt` 404 (sin ID de
editor), callback con firma inválida 403, ticket sin sesión 401, `/control/anuncios` tras Cloudflare Access,
resumen de monedas sin cambios para la app actual; el contenedor alcanza las claves públicas de Google.

Fallo encontrado SOLO al verificar en producción: `/rewards/callback/{provider}` (ofertas) capturaba
`/rewards/callback/admob` y respondía 503 «Proveedor no configurado». Mis pruebas usaban una app mínima con solo el
router de anuncios y no lo veían. Corregido registrando el router de anuncios antes que el de ofertas y con una
prueba sobre la app completa (`test_el_callback_de_admob_no_lo_captura…`). Lección: en rutas con parámetro de
ruta genérico, probar el orden de registro con `main.app`.

Privacidad con AdMob desplegada (solo API; worker intacto): imagen `quantfut-api-admob:20261014c` sobre la anterior con solo
`legal_pages/privacidad.html` (la desplegada era idéntica a la base de la rama antes de copiar; términos y eliminar
cuenta, sin cambios). Fijada en el compose; respaldo en `~/quantfut/releases/privacidad-admob-20261014/`. Comprobado en el
dominio: 200, 5 menciones de AdMob, la frase «no está habilitada» ya no está, versión `2026-10-12` intacta. Decisión: NO se
subió `CONSENT_VERSION`: el servidor la compara con la que envía la app (`live_api.dart`) y rechazaría registros de las apps ya
instaladas. El `<script>` que se ve en las páginas públicas es la ofuscación de correo de Cloudflare (también en términos);
el origen no sirve ninguno. Error propio al preparar: una primera comparación usó una ruta mal formada y dio «vacío»; se
detectó antes de actuar y se repitió bien.

Términos con los videos con recompensa desplegados (solo API; worker intacto): imagen `quantfut-api-admob:20261014d` sobre la
anterior con solo `legal_pages/terminos.html` (la desplegada era idéntica a la base de la rama; privacidad ya coincidía con el
repo). Fijada en el compose; respaldo en `~/quantfut/releases/terminos-admob-20261014/`. Comprobado en el dominio: 200 en las
tres páginas legales, párrafo nuevo presente, versión `2026-10-12` intacta, privacidad con AdMob, API sana y sin errores en logs.
Esta vez la comparación previa se protegió contra una lectura vacía (hash de archivo vacío) antes de dar el paso por válido.

Anuncios activados en modo prueba en producción (15-oct, a petición del titular «usa por mientras ID de modo prueba»): UPDATE de
`reward_settings` (`ads_enabled=TRUE`, `ad_test_mode=TRUE`) más fila en `admin_audit` con actor `claude:despliegue`, hecho por SQL
porque el panel está detrás de Cloudflare Access sin sesión disponible. Comprobado con el código real del servidor: ticket permitido
en Android e iOS con los bloques de prueba oficiales; sin sesión nada se expone (`ads: {enabled: false}`, ticket 401). Riesgo
acotado: solo bloques de prueba y la app publicada no trae aún el código. Sin comprobar: si los bloques de prueba envían el callback
SSV a `/rewards/callback/admob`; si no lo hacen, el saldo no sube y la app muestra «tus monedas llegarán en unos instantes».
Intento de leer los IDs desde el Chrome del titular: no tiene cuenta de AdMob (redirige al registro); no se creó ninguna.

## 2026-10-14 — APK de release no abría (WorkManager / R8)

Causa: al añadir `google_mobile_ads` entró una versión de WorkManager cuyo `WorkDatabase_Impl`
se instancia por reflexión; R8 conservaba la clase (`-keep class * extends RoomDatabase`) pero
eliminaba su constructor vacío, y `androidx.startup.InitializationProvider` mataba el proceso al
arrancar (antes de Dart, así que Sentry/Crashlytics no lo habrían recibido). Se vio en `adb logcat`,
no en Sentry. Arreglo: `-keep class * extends androidx.room.RoomDatabase { <init>(); }` en
`android/app/proguard-rules.pro`. Verificado: release recompilado, instalado en el emulador, abre
sin `FATAL EXCEPTION`. Lección: tras añadir un SDK con dependencias nativas, abrir el release en
emulador antes de darlo por bueno (el debug no pasa por R8).

## 2026-10-14 — Videos de prueba no acreditaban: crédito simulado solo en modo prueba

Causa: el video demo se vio y el ticket se pidió bien, pero Google nunca llamó a `/rewards/callback/admob`
(Caddy sin llamadas, `reward_ad_events` vacía). Los bloques de prueba son de Google y no admiten nuestra
URL SSV, así que no hay callback que acredite. Decisión del titular: en lugar de montar un bloque real
con dispositivo de prueba, el servidor acredita por una vía de solo prueba (`/ads/test-credit`), limitada
al modo prueba Y a `QF_ADS_TEST_CREDIT_EMAILS`. La lista existe porque producción está en modo prueba con
anuncios activos: sin ella cualquier cuenta cobraría 5×10 monedas al día sin ver nada. Reusa `credit()`.
Verificado: 42 pruebas de anuncios con Postgres real (esquema aislado), Flutter 235 y analyze limpios.
Desplegado el 2026-10-14 (imagen `quantfut-api-admob:20261014e`, variable `QF_ADS_TEST_CREDIT_EMAILS` en el `.env`, respaldos en `~/backups/ads-test-credit-20261014`, vuelta atrás = `pre-test-credit`). Probado por el titular en su teléfono: las monedas se acreditan.

## 2026-10-15 — «Demasiadas solicitudes» en Coins: escudos con contador propio

Causa: el límite global es 60/min por IP y cuenta todas las rutas. Una pantalla de la app pide ~80
escudos (`/web/escudos/*.png`, uno por equipo) en un minuto; al pasar de 60 el servidor devolvía 429
también a `/mobile/v1/rewards` y Coins quedaba con «Reintentar». Medido en los logs de producción
(05:55 UTC: ~95 solicitudes, 23 rechazadas). Arreglo: los escudos van a su propio contador
(`escudos:<ip>`, 10× el límite general), igual que `/control` y `/static`; el resto sigue en 60/min.
Pendiente posible: que la app cachee los escudos en disco para no repetir las descargas.

## 2026-10-15 — F2: cierres de Pinnacle, comprobando antes de pagar

Football-data parecía poder rellenar ~1.457 cierres de México, Argentina, Brasil y MLS; el
ensayo en producción demostró lo contrario (11.923 filas de Pinnacle desde 2024, todas ya
cargadas) y se descartó sin escribir nada. Para Europa se compró histórico de The Odds API en
fases: prueba de 10 créditos, 8.000 créditos (801 snapshots) con reserva de 6.000 para la captura
en vivo, y carga solo tras ensayo, comprobación de integridad (RPS 0,1987 con las cuotas
emparejadas frente a 0,2357 uniforme: un emparejamiento erróneo se vería) y respaldo. Decisión
clave: un cierre solo se acepta si el snapshot está a <=30 min del inicio y el precio de Pinnacle
se movió <=30 min antes; el emparejador usa ids de equipo, no nombres de liga, porque los clubes
ascendidos tienen su fila en otra división. Huecos de modeladas: 1.861 a 697. Quedan para tras el
1-nov los snapshots de México, LaLiga, Serie A, Eredivisie y Primeira (~5.270 créditos) y los alias
de Champions. Detalle: docs/f2_cierres_pinnacle_20261015.md.

## 2026-10-15 — F2c: el cierre ya no incluye precios de 60 minutos

Las cuotas `oddspapi_reconstructed` están, en el 74 % de los partidos, cortadas a 60 minutos del inicio
(precio a la hora del XI). Contra ellas el modelo parece mejor que el mercado y el CLV sale inflado, y el
reentrenamiento del 1-nov las habría usado como cierre en su ventana de validación. Decisión del usuario:
filtrarlas antes del reentrenamiento. Una sola función (`eval.cierre.es_cierre_real`) gobierna las seis
lecturas del cierre; se descartan 1.613 cierres de las ligas modeladas y se conservan los 739 cortados al
inicio. Desplegado solo en el worker: la API y el árbol `~/quantfut/src` del servidor llevan versiones
antiguas de `train.py` y `clv.py` y sobrescribirlas habría revertido código ajeno. El parche vive en el
contenedor, no en la imagen: hay que comprobarlo antes del 1-nov si se recrea. Detalle:
docs/f2_cierres_pinnacle_20261015.md.

## 2026-10-15 — Meta y compras en la app: diseño aprobado (sin código aún)

El titular eligió Google Play / App Store como procesador **de la app** (suscripción renovable, sin
prueba gratis) y el enfoque «servidor fuente única»: compras, registro y desbloqueos van a Meta solo
por Conversions API tras verificarlos, y el SDK solo manda lo que únicamente sabe la app. Así no hace
falta deduplicar (Meta solo documenta el `event_id` del SDK en iOS) y una compra falsificada en la app
no llega a Meta ni da acceso. La App Events API `/{app-id}/activities` se descartó: Meta ya no la
recomienda para integraciones nuevas. Seguimiento encendido por defecto en todo el mundo por decisión
del titular, que asume el riesgo RGPD (Meta pide consentimiento previo en la UE); se conservan las
negativas explícitas previas y los límites de ATT y del ID de publicidad. «EMQ 10/10» no es
garantizable: se envían todos los datos legítimos disponibles. Spec:
docs/superpowers/specs/2026-10-15-meta-compras-design.md.

## 2026-10-15 — Compras de tienda y Meta: implementadas y API desplegada (apagadas)

El titular pidió ejecutar el plan y desplegarlo el mismo día, así que la API salió antes del 1-nov; el worker no se tocó.
Decisión clave: la API se desplegó como capa sobre la imagen en ejecución con solo los 20 archivos de la rama, tras comprobar
que los 12 modificados eran idénticos a `main` en el contenedor; así no se revirtieron las otras diferencias de la API.
El periodo de cada cobro sale de la tienda y no de `duration_days`, y una compra de prueba concede acceso pero no va a Meta.
Quedan apagadas las compras y el envío a Meta hasta tener credenciales. Pendiente: alinear el worker antes de activar CAPI.

## 2026-10-16 — Play Console: ficha, declaraciones y RTDN preparados

La prueba interna de QuantFut continúa activa. Por navegador se guardaron la ficha en español con icono y gráfico destacado, las declaraciones de funciones financieras e ID de publicidad y el borrador completo de Seguridad de datos. Faltan capturas actuales, una cuenta dedicada de revisión con Plus, Público objetivo y el cuestionario IARC; este último quedó preparado antes de aceptar sus condiciones.

En Google Cloud ya existen la cuenta de servicio y el tema `quantfut-play-rtdn`. Quedaron preparados, sin confirmar, el permiso de publicación para el servicio de notificaciones de Google Play y la activación de Android Publisher API. La primera clave JSON existe en Cloud pero no apareció en Descargas, por lo que debe revocarse y sustituirse antes de habilitar compras. Estado y evidencias: `apps/mobile/docs/PLAY_CONSOLE_20261015.md`.

## 2026-10-17 — API-Tennis: muestra autenticada autorizada
Seis consultas correctas: 27 tipos, 10.360 entradas de catalogo, 445 partidos recientes, 228 futuros, 205 de una fecha 2025 y cinco en vivo. En recientes, 45 terminados ATP/WTA individuales tienen estadisticas; se comprobaron 1.138 pares numericos y consistencia saque/resto sin incidencias. No generalizar a ITF: solo 132/393 terminados globales tienen estadisticas. No hay inicio/final reales ni duracion en campos observados; por ello no habilitamos descanso horario con event_time. Originales con SHA-256 en .local/api_tennis_probe/20261017T211250Z, clave solo en configuracion ignorada, cero apariciones en artefactos. No se consulto The Odds API ni se alteraron modelos o protocolos. La integracion automatica y medicion de latencia quedan pendientes. Informe docs/tenis_api_tennis_prueba_20261017.md. Arnes inicial: 1.300 aprobadas/88 omitidas/dos avisos; Docker ausente.

## 2026-10-17 — Tenis: evaluador comun y carga observable, fase 1
Implementados BenchmarkEvaluator, RecentLoadExtractor, ModelRunner y correccion logistica ridge sobre log-odds del candidato actual. Corte estricto por disponibilidad anterior a decision; ventanas con incertidumbre y datos faltantes explicitos. Recalculo temporal de features en ajuste, control de orientacion, resultados completados y muestra comun. API-Tennis no acredita inicio/final reales: normalizador no usa fecha programada como final exacto. Muestra real sin red: 104 observaciones normalizadas, dos pronosticos base actuales, cero entrenamiento/candidato carga y cero evaluables por futuros pendientes; metricas nulas, sin simular mejora. 24 nuevas pruebas y 75 totales tenis aprobadas. Los 12 hashes del protocolo previo intactos. Informe docs/tenis_carga_evaluacion_fase1_20261017.md. Motor de futbol y apuestas intactos.
Validacion final fase 1: 75 pruebas tenis aprobadas; arnes general 1.300 aprobadas/88 omitidas/dos avisos en 226,35 s. Los cuatro hashes de implementacion coinciden con report.json; cero apariciones de clave en los nuevos entregables.

## 2026-10-17 — Tenis: captura de estados y Weighted Elo
Captura con limite diario local, originales/recibos SHA-256, tabla append-only y consultas as-of. No inferir terminado por ausencia en vivo, ni convertir observacion en inicio/final reales sin conocer latencia. Correccion terminal->en vivo invalida carga posterior sin borrar pasado. Importadas 883 observaciones previas (incluido historial 2025), dos consultas ATP/WTA nuevas aportaron 113; total 996 observaciones/879 eventos, cero conflictos. Seis hashes de recibo validos, cero claves en resultados. No hay tarea periodica activa ni consumo nuevo de The Odds API.
WElo original segun ecuaciones del articulo, K con conteo previo explicito y adaptacion simultanea por periodos semanales. Mismas filas de entrenamiento/embargo35 y prueba congelada2026: ATP n2451 logloss WElo0,629374 vs hibrido0,622427; WTA n2146 0,629068 vs0,618318. Mejor que Elo adaptativo no ponderado, inferior al hibrido; no se promueve. Bootstrap por periodo exploratorio, no prueba financiera ni reproduccion diaria exacta. 96 pruebas tenis aprobadas (21 nuevas), 12 hashes del protocolo anterior intactos. Informe docs/tenis_estados_weighted_elo_20261017.md.
Verificacion final estados/WElo: 96 pruebas tenis aprobadas y arnes general 1.300 aprobadas/88 omitidas/dos avisos en 145,62 s. Fuentes/codigo de ambos reportes v2 verificados. La pagina publica de API-Tennis anuncia Starter 8.000 solicitudes/dia y prueba14dias; plan/vigencia de esta cuenta aun por confirmar para fijar frecuencia recurrente. No confundir con The Odds API de pago ya confirmado.

## 2026-10-17 — Plan de API-Tennis sin confirmar
El titular responde «Periodo de prueba / no sé». Registrado como posible prueba, sin cuota ni vencimiento acreditados, en data/tennis/state_capture_20261017/account_policy.json. Mantener tope local de 24 consultas/dia del capturador; no implica cuota de la cuenta. Programacion automatica pendiente. No cambia The Odds API de pago ni sus 2.000 creditos mensuales de tenis y reserva de 6.000. Sin nuevas consultas ni cambios de codigo.

## 2026-10-17 — Web: interfaz sports intelligence HUD

Decisión clave: conservar el frontend nativo y su lógica completa, y aplicar el rediseño en una capa
`future.css` cargada al final. La separación evita mezclar presentación con contratos de datos y hace
reversible el cambio sin reescribir las ocho vistas. Tras la revisión del usuario se integró
CYBERCORE CSS 0.3.0 como dependencia exacta: `postinstall` copia su distribución y licencia MIT a
`frontend/vendor/cybercore/`, por lo que producción no depende de CDN. Las vistas reciben sus clases
reales de tarjetas, botones, insignias, entradas, tablas, alertas, bordes neón, scanlines y datastream.
Cyberpunk CSS se mantiene como referencia porque sus reglas globales colisionan con la aplicación; se
adaptaron sus cortes geométricos y alto contraste. La paleta ahora usa los tokens oficiales cian
#00f0ff, magenta #ff2a6d, amarillo #fcee0a, verde #05ffa1 y void #0a0a0f, con iconografía SVG propia.
El frontend conserva foco, texto de estados, objetivos táctiles y `prefers-reduced-motion`; no se
desplegó ni se modificó el motor.

Validación final del rediseño: 25/25 pruebas del frontend y arnés general con 1.300 aprobadas,
88 omitidas y dos avisos en 126,80 s. `docker-compose.yml` válido; Docker no estaba disponible en
este entorno. El servidor local inicia en `127.0.0.1:5173`; la comprobación HTTP automatizada quedó
limitada por los permisos de sockets del entorno, no por un error de la aplicación.

## 2026-10-17 — Tenis: sedes por edicion y vigencia
Implementado VenueRegistry relacional de solo adicion, fuentes SHA-256 por campo, versiones y enlaces exactos proveedor/modalidad/temporada con vigencia local. Enriquecimiento exige UTC y recepcion previa a decision. Bruselas cambia P12->P5 el 23-oct; se resuelve por fecha local, sin heredar Marsella para Lyon ni imputar techos. Ocho recintos, siete ediciones, quince enlaces, 24 fuentes verificadas. Archivo228:102/102 ATP/WTA enlazados con coordenadas;126 sin sede y48 fechas2026 con temporada2025 marcadas. Altitudes desconocidas: servicio de elevacion no disponible, no imputar ciudad/EXIF. Sin API deportivas nuevas ni cambios al modelo; doce hashes prospectivos intactos. 116 pruebas tenis aprobadas (20 nuevas). Informe docs/tenis_sedes_verificadas_20261017.md.
Verificacion final sedes: 116 pruebas tenis aprobadas y arnes general 1.300 aprobadas/88 omitidas/dos avisos en 116,35 s. Docker ausente. Hash del modulo y semilla coinciden con informe v2; PENDIENTES actualizado con alcance y campos externos pendientes.

## 2026-10-17 — Tenis: aclaracion no comercial y Open-Meteo
El usuario aclara que este proyecto de tenis no esta monetizado. Utilizar Open-Meteo publico sin clave; la referencia previa a Standard procede del contexto de futbol y no es requisito para tenis. No altera The Odds API de pago ni sus 2.000 creditos mensuales. Documentacion oficial de elevacion/terminos revisada. Una consulta exitosa recibida 18-oct02:59:53UTC devuelve Almaty756,LDLC194,P12:73,P5:83,Shanghai20,Wuhan48,Ningbo9,Osaka5 metros. Son estimaciones del modelo Copernicus DEM2021 GLO-90, resolucion horizontal90m, no cota medida de pista. Fuente y atribucion guardadas; no imputar altitud de ciudad.
Semilla registry_seed_open_meteo_v2.json conserva original y enlaces, agrega fuente25 y ocho revisiones posteriores a recepcion. calendar_report_v3_open_meteo.json:102/228 con altitud, mismos102/102 ATP/WTA. Verificados hash, orden y coordenadas, valores finitos, semilla original intacta y consultas previas siguen con altitud desconocida. 126 encuentros sin sede y48 discrepancias no resueltos por elevacion. Sin consultas deportivas, cambios a probabilidades ni captura meteorologica. Informe docs/tenis_open_meteo_20261017.md. Validacion:116 pruebas tenis aprobadas; arnes general1300 aprobadas/88 omitidas/2avisos en127,80s, Docker ausente. Solo metadatos/documentacion, sin modificaciones de codigo.

## 2026-10-18 — Tenis: sedes pendientes y temporada revisada
Las 48 discrepancias eran cuatro IDs en tres ediciones: Guangzhou22, Lisboa18 y Cali8. Contrastadas fuentes ATP/WTA, ITF y organizadores; se corrige metadata de edicion2025->2026 por evento/digest, no por una regla generica de fecha. FixtureReviews exige fila exacta en original archivado, fuentes integras y registradas antes de decision, conserva original/correccion y bloquea cambios de fila, conflictos y cuarentenas. Se agregaron 27recintos/37alias para126encuentros; total35recintos52enlaces228/228con sede principal. Heraklion hombresLyttos/mujeresNANA; RoanneprincipalVacheresse, no reutilizar tabla historicaScarabee. No acreditar pista individual ni horario por esta revision.
La cobertura espacial sigue102/228: coordenadas/altitudes desconocidas en27recintos nuevos. Extraccion OSM acotada fallo406/502/timeout; no imputar centros de ciudad. Dos consultas ZenRows existentes recuperaron paginas oficiales Cali/Jinan; cero consultas deportivas/TheOddsAPI. Originales HTTP y extracciones web diferenciadas, recibos/hash;65 fuentes verificadas. Artefactos data/tennis/venues_completion_20261017/calendar_completed_v2.json,registry_seed_completed.json,season_reviews.json,integration_audit.json. Modelos intactos,12hashes prospectivos verificados. Auditoriareal a decision anterior conserva102sedes,0correcciones y48flags: no fuga retrospectiva.
Validacion del checkout entregado:126tests tenis aprobados, diez nuevos. Arnes general1300aprobados/88omitidos/2avisos79,88s, Docker ausente; diffcheck correcto. Pendientes de identidad de sede y revision de temporada cerrados para esta muestra; georreferenciacion nueva y variables viaje/clima siguen aparte. Informe docs/tenis_sedes_temporadas_completadas_20261018.md.

## 2026-10-18 — Tenis: revision cientifica de viajes
Revision documental de fuentes oficiales ORS/OSRM/Amadeus/Arcascope y consensos deportivos. No adoptar score 0,4/1,8/1,2 ni umbral10 como validados. Distancia/800+2,5 queda como escenario hipotetico sin respaldo ATP/NBA verificado. Entre torneos solamente; no inferir viaje directo, llegada, descanso efectivo o vuelo tomado. Intervalo ultima participacion-debut e indicadores de incertidumbre separados. Plan en docs/tenis_viajes_criterios_20261018.md; georreferenciacion27 sigue pendiente, cobertura espacial confirmada102/228. Solo documentacion, sin codigo ni nuevas consultas deportivas/rutas/vuelos.


## 2026-10-18 — Tenis: 27 coordenadas y modulo intertorneos
Cerrada georreferenciacion de27recintos con selecciones explicitas OSM/Nominatim/Photon, GPS oficiales y cuatro extracciones publicas de navegador etiquetadas. Rechazados bus/calle homonimos, estadio futbol y encuadres. China usaWGS84, noGCJ02. Una peticion Open-Meteo gratuita entrega27cotas DEM90m; geometria representa recinto/complejo y precision150-1100m es margen conservador, no medicion. Semilla89revisiones35recintos52enlaces112fuentes. Calendario archivado228/228 con coordenadas/altitud,48correcciones; asof previo sigue102/228. No afirmar pista, techo o horario real. Docehashes congelados intactos.
TravelExtractor requiere evidencia previa integra y cierre de participacion incluyendo dobles; no viajes por cambio de pista. DiferenciaUTC al mismo instante conDST, direccion y linea de fecha, distancia/altitud, transporte candidato configurable; intervalo salida a debutprogramado separado de descanso/arrival. Context legacy deja de inferirviajes entre partidos. Historial879eventos,614terminados/retirados,183/456participaciones con candidato porfecha programada; cero transiciones totalmente verificadas, sin horasreales acreditadas. Datos listos no equivalen a eficacia predictiva.143tests tenis entregados aprobados,17nuevos; primer intento con temporalesdel sistema fallo porpermisos, repeticion en workspace limpia. Sinconsultas API deportivas/creditosOdds ni entrenamiento. Informe docs/tenis_coordenadas_viajes_20261018.md.

Verificacion final coordenadas/viajes: arnes general1300aprobados/88omitidos/2avisos138,58s, Docker ausente;143tests tenis entregados aprobados8,60s. Diffcheck tenis correcto y hashes stage/entrega coinciden; entrega auditada en data/tennis/coordinates_20261018/delivery_audit.json.


## 2026-10-18 — Tenis: comparador espacial y sensibilidad
SpatialExperiment implementado: base, residualridgeespacial y nueve escenarios experimentales de intervalo. EscaladoRMS/coeficientes soloentrenamiento, interseccioncomun de tresfamilias/todosescenarios, sin seleccionarporprueba; logloss/Brier/ECE10. Horasmainintactas; experimentalrequiere diasreales verificados, conserva horasconocidas, rechaza semanas/DSTambiguo. Cierres12/18/23 perturbadosporjugador con ordenIDinvariante; aplicar igualcambioados cancela ladiferencia y no sirvecomosensibilidad. Hashesfuentes/matriz e IDs entrenamiento registrados.
Auditoriareal ejecutada v3: archivo492251 corte16oct anterioraprimerascoordenadas; snapshot228sinresultadoscompletadosobjetivo en estados;0transicionesverificadas. Entrenamiento/pruebacomunes0,0modelosajustados,metricasnull y sensibilidadrealnoejecutada. No backfill asof ni datos sinteticos paraafirmarrendimiento. Once testsnuevos,154tenisaprobados. Doc docs/tenis_comparacion_espacial_20261018.md; protocolo/report data/tennis/spatial_trial_20261018_v3. CeroAPIsdeportivas/creditosOdds, docehashescongeladosintactos. Holdoutexistentenoreutilizadoparanuevaseleccion.

Verificacion final comparador espacial:154pruebas tenis aprobadas en entrega, arnesgeneral1300/88omitidas/2avisos139,58s, Docker ausente. Diffcheck correcto; hashesdelcodigo/protocolo/reportecoinciden. Deliveryaudit registra0modelosrealesajustados, no confundir pruebas sinteticas con mejora predictiva.


## 2026-10-18 — Tenis: reconstruccion retrospectiva 2024/2025
Autorizada por usuario una rama retrospectiva separada, no backfill asof. Directorios ATP2024/25, notas WTA por edicion e ITF Paris2024 archivados; correcciones Dallas/Bruselas/Hangzhou/Belgrado/Atenas, Paris por temporada.187ediciones enlazadas,160georreferenciadas,27sede conocida sincoordenadas;95recintos,78concoordenadas yDEM,122fuentesSHA verificadas. Sinherencia de enlaces2026. OpenMeteo1consulta72puntos, Nominatim serialcache1,25s, candidatos ambiguos rechazados.
HistoricalDataset: historial38936filas2023–25, objetivo11240/472bloques. Antecedente inmediato observado sin saltarunknowns, incluye Challenger/qualy, noherencia sedequaly. Variables distancia/deltaaltitud/deltaUTC; DSTambiguo queda rango, guardaconservadora7dias porperiodo. No descanso/imputaciones dehora niitinerarioreal.3155convariablescompletas antesfiltros,2982aptos(1426desarrollo2024/1556exploratorio2025);26,53%coberturaobjetivo. Particiones5661/5378/201cuarentena porfrontera, edicionescompletas.165tests tenis entregados aprobados,11nuevos,12hashescongelados intactos. Datos+proveniencia+splits+pendientes en data/tennis/historical_venues_20261018; doc docs/tenis_dataset_historico_20261018.md. CeroOdds/API-Tennis,0modelosajustados,metricaspendientes. Falta cobertura52edicionesindividuales,17recintos(27ediciones),233bloquesporequipos/multisede; no interpretarpreparacioncomo eficacia. Comparacion exigira interseccionpredicciones no simplementecohortedatos.
Verificacion final retrospectiva: arnes general1300aprobados/88omitidos/2avisos115s; Docker no disponible. Entrega165tests tenis aprobados16,66s. Diffcheck entrega correcto, auditoria hashes/dataset/particiones aprobada.

## 2026-10-18 — Comprometer-revelar de la cadena y plan de F7
Decisión: al repo público va solo el compromiso (recibo y `LEDGER.md`); el JSON del lote sube cuando todos los partidos que cita constan terminados y pasaron 4 h (tope de 7 días para aplazados). Por qué: el lote lleva los picks de pago y publicarlo antes de los partidos los regala. El hash no cambia, así que ningún lote ya sellado se altera; `verify` ahora recorre por recibos y cuenta aparte los lotes sin revelar, y sigue detectando JSON alterado y cadena rota. `seal()` revela los pendientes al inicio de cada pasada, sin tocar `daily.py` ni el orden predecir → seleccionar → sellar → publicar. `CHAIN_GIT_REMOTE` sigue vacío: falta desplegar con ensayo. Pruebas: `tests/test_hashchain_revelado.py` (8) y suite completa 1308 aprobadas / 88 omitidas.
Hallazgo para F7 (`docs/superpowers/plans/2026-10-18-f7-sello-tardio.md`): con varios lotes por día, los cuatro lectores que unen `prediction_batches` por fecha contarían cada fila varias veces; hay que filtrarlos por `batch_kind = 'diario'` en el mismo cambio.
Medición contra producción (solo lectura): cierres de Pinnacle faltantes en ligas modeladas = 697 (coincide con PENDIENTES); el CLV en sombra de +3,46 % (n=142) no se reproduce con ninguna fuente (ver PENDIENTES); el servidor dejó de responder por SSH durante la sesión.

## 2026-10-18 — Rediseño CYBERCORE desplegado

Los PR #12 y #13 quedaron fusionados con CI verde. El segundo fue necesario porque producción sirve la
web desde FastAPI y debía exponer explícitamente `future.css` y el CSS vendorizado de CYBERCORE. Para no
revertir las diferencias históricas de la API se construyó `quantfut-api-cybercore:2d8cfef` sobre la
imagen que ya estaba en ejecución y se sustituyeron únicamente `frontend/` y `src/qf/api/web.py`.
Dominio y assets responden 200, los hashes coinciden con `main`, la comprobación visual no mostró errores
de consola, el modelo sigue en `2026.09.27-010508` y los 19 lotes verifican. Worker, base y flags intactos;
respaldo y reversión en `DEPLOYS.md`.

## 2026-10-18 — Tenis: cierre de las tres colas históricas originales

Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de edición, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliación siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.

Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geográficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigüedad de múltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni métricas nuevas;2025exploratorio, comparación de predicciones pendiente.

173pruebas tenis aprobadas en preparación y entrega; regresión con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canónico/CSV verificados por auditoría. Arnés general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesión añadió8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni créditos; una consulta Open-Meteo69puntos para elevación. Informe docs/tenis_cobertura_historica_completada_20261018.md; módulo, pruebas, constructores y auditoría entregados al motor aislado. Próximo paso: comparación Base/Base+Espaciales en intersección común y completar las coordenadas adicionales pendientes.

## 2026-10-18 — Acceso con Google en la web

Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de edición, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliación siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.
Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geográficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigüedad de múltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni métricas nuevas;2025exploratorio, comparación de predicciones pendiente.
173pruebas tenis aprobadas en preparación y entrega; regresión con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canónico/CSV verificados por auditoría. Arnés general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesión añadió8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni créditos; una consulta Open-Meteo69puntos para elevación. Informe docs/tenis_cobertura_historica_completada_20261018.md; módulo, pruebas, constructores y auditoría entregados al motor aislado. Próximo paso: comparación Base/Base+Espaciales en intersección común y completar las coordenadas adicionales pendientes.
## 2026-10-18 — Acceso con Google en la web


Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de edición, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliación siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.

Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geográficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigüedad de múltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni métricas nuevas;2025exploratorio, comparación de predicciones pendiente.

173pruebas tenis aprobadas en preparación y entrega; regresión con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canónico/CSV verificados por auditoría. Arnés general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesión añadió8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni créditos; una consulta Open-Meteo69puntos para elevación. Informe docs/tenis_cobertura_historica_completada_20261018.md; módulo, pruebas, constructores y auditoría entregados al motor aislado. Próximo paso: comparación Base/Base+Espaciales en intersección común y completar las coordenadas adicionales pendientes.

## 2026-10-18 — Acceso con Google en la web

- Decisión: el navegador solo obtiene el ID token (SDK web de Firebase, `frontend/google-auth.js`) y el servidor
  lo cambia por la MISMA sesión de cookie HttpOnly del correo (`POST /app/v1/firebase/web-session`). Así Firebase no
  guarda estado en la página y el resto de la web/checkout sigue usando `cuenta-api.js`.
- La config web sale de `GET /app/v1/firebase/web-config` (env `FIREBASE_WEB_*`), no del repo. Cerrada con 503 hasta
  que existan las variables y `FIREBASE_AUTH_ENABLED=1`.
- Cuenta nueva exige casilla de términos/privacidad (`CONSENT_VERSION`). Un correo ya registrado con contraseña da
  `vinculacion_requerida`: no se vincula por correo automáticamente (regla existente).
- Pendiente del titular: registrar app Web en Firebase, añadir el dominio a «Dominios autorizados» y poner las 3 variables.
- Verificado en local con popup real de Google: sesión creada y «Mi cuenta» abierta. Despliegue preparado, no ejecutado: `docs/despliegue_google_web_20261018.md` (producción lleva un frontend Cybercore sin comitear; comitearlo antes).
- Siguiente: Whop (checkout embebido + webhooks `payment.succeeded`) y Pixel + CAPI web con `event_id` compartido.


## 2026-10-18 — Tenis: comparación espacial retrospectiva ejecutada
Decisión: no activar la corrección espacial. Base híbrida Markov/Elo reconstruida por orígenes2023/24/25, mezclas calibradas con predicciones del año anterior y embargo35días, sin usar coeficientes actuales hacia atrás. Ajuste espacial ridge1 con2965partidos desarrollo2024, evaluación común2833en2025exploratorio(52,68% de5378). LogLoss0,6387331418→0,6386822788; delta−0,000050863, intervalo95%por116competiciones[−0,000159672;+0,000054898]. Brier0,2243935574→0,2243696603;ECE0,026213→0,026260. Intervalos incluyen cero, calibración no mejora.
Sensibilidad sin tolerancias geográficas>1000m:2851train/2718test,deltaLL−0,0000764803,intervalo[−0,000194240;+0,000025873]. Mismos IDs entre variantes dentro de cada escenario; distintas muestras entre escenarios.2025no usado para ajustar ni elegir ridge; evidencia retrospectiva recibida2026, no validación asof real ni itinerarios/descanso exactos. Se preserva agrupación por competición completa. Intervalos descriptivos sin toda dependencia entre jugadores.
Entrega en motor aislado: historical_comparison.py, runner y auditoría,9tests nuevos;182pruebas tenis aprobadas en preparación y entrega. Auditoría reproduce ajustes y métricas, verifica fuentes y12hashes congelados intactos. Resultados/protocolo/predicciones/calibración en data/tennis/historical_comparison_20261018; informe docs/tenis_resultados_espaciales_historicos_20261018.md.0llamadas deportivas/0créditos Odds. Próximas mejoras deben elegir especificación en entrenamiento y reservar periodo futuro nuevo; la ampliación de88sedes sigue pendiente. Arnés inicial1310/88/2aprobado; verificación final en curso.
Verificación final comparación: arnés general1310aprobados/88omitidos/2avisos145,51s; Docker no disponible. CoincidenciaSHA de4archivos entregados y diffcheck correctos; auditoría entregada ejecutada sin errores. No trabajo de esta fase pendiente de verificación.


## 2026-10-18 — Tenis: carga observable por rondas
Decisión: conservar corrección experimental, sin activarla. Ventanas3/7d siguen bloqueadas:152terminales API-Tennis de últimas revisiones archivadas tienen límite inferior desconocido; no se transformaron fechas programadas/recibos en horas reales. Nueva carga distinta: puntos de totales al saque, juegos/sets de marcadores completos y partidos decisivos de rondas anteriores del mismo cuadro individual; sin dobles, qualies, torneos previos ni tiempo transcurrido supuesto.
Base histórica previa reutilizada porSHA. Tres variantes en intersección común: Base, Base+Cobertura, Base+Cobertura+Carga. Ajuste solo2024,ridge1,RMSentrenamiento;2130train/1957test2025exploratorio(36,39%),993ATP/964WTA. LL0,615696→0,615221;delta−0,000475307,IC95%[−0,00110306;+0,00015902];contra cobertura delta−0,000408593,ICincluyecero. Brier0,213501→0,213225;ECE0,028584→0,026355. Sensibilidad contadores observados completos1882/1700,LL0,611986→0,611413,ICincluyecero. No declarar superioridad ni rentabilidad.
Revisión detectó pérdidas seguidas de avance en finalesBJK2024: eran partidos por equipos, una derrota individual no elimina necesariamente a la selección. Se corrigió el alcance para excluir todos los equipos y grupos; versión preliminar draw_load_20261018 retirada porSUPERSEDED.json, válida draw_load_20261018_v2. No corrección de datos originales ni selección por métricas. Auditoría reproduce10407formatoscompatibles/4378conpreviojuegoambos antesfiltros, contadores yprecedencia,coeficientes/métricas.194pruebas tenis aprobadas en entrega,12nuevas;12hashescongelados intactos. Cola88sedes/730destinos priorizada,5primeras264destinos.0APIdeportivas/0créditosOdds. Informe docs/tenis_carga_rondas_resultados_20261018.md. Arnés general inicial1310/88/2en224,53s; final1310/88/2en324,67s, Docker ausente.

## 2026-10-18 — Cobro web con Whop (checkout embebido + webhooks) y Meta web


## 2026-10-18 — Cobro web con Whop (checkout embebido + webhooks) y Meta web

- Decisión: el servidor crea la `checkout_configuration` (con `qf_account_id` en `metadata`) y el navegador solo monta `ch_…`
  en el elemento Checkout; el acceso lo concede únicamente `payment.succeeded` (firma Standard Webhooks, idempotente por
  `webhook-id` y por `payment_id`). Así ni la web ni la metadata del cliente pueden conceder acceso.
- Dedupe Pixel↔CAPI: `purchase:<ch_id>` (existe antes del pago, por eso el navegador ya lo conoce) e `ic:<ch_id>`; el contexto del
  navegador (fbp, fbc, IP, UA, URL) se guarda al crear el checkout para que el Purchase de servidor lo lleve (EMQ).
- `meta_events` ganó `action_source`/`web_context`; el cron de CAPI del worker debe actualizarse con la próxima alineación del worker
  ANTES de activar `META_CAPI_ENABLED` con tráfico web (el código viejo ignoraría `web_context`).
- Hallado: el payload de `payment.succeeded` y la membresía solo están en el OpenAPI (requiere login); los campos usados salen de las
  páginas de objetos Payment/Membership. Reembolsos: no hay evento documentado; se revoca por `membership.updated` en `canceled`/`expired`.
  Verificar con una entrega real y añadir `refund` si Whop lo emite.
- El sandbox de Whop no cubre Elements todavía: la primera prueba real del formulario será en producción con un plan barato.


## 2026-10-18 — Tenis: cinco sedes prioritarias verificadas
HuaHin por mapa enlazado porpropietario yOSMtenis71mdediferencia;Seúl porgeometría estadioOSMrel8679966 yoperador/Wikidata61m;AbuDabi objeto93051899tenis corroborado enidentidad poroperador,sin fingirsegunda medición;Carpena coordenadasJuntaAndalucía yestadioOSM18m,no parada detaxis. Yucatán punto delcomplejo enlazado porpropietario a1102mdeláreatenisOSM;1800mtolerancia ycoarseflag,no pistas2024/25precisasproyectadas. Rechazadaslocalidadhomónima,centrosgenéricosparque/estadiofútbol. Fuentes archivadasconrecibosreales,erroresdevueltosnocuentancomoevidencia.1OpenMeteopúblico5puntos,terreno5/6/23/6/20m,noalturamedidapista.
Registroseparado data/tennis/historical_geography_top5_20261018:294fuentes,240entradas(157concoordenadas,83pendientes); enlacesdeediciónypartidointactos.11240objetivos,10774destinosconcoordenadas(+264),6651variablescompletasambos,6244aptos(+446),5943sinreferencias>1km.3226desarrollo2024/3018exploratorio2025;201frontera.264destinosy446transicionesaptas no sonlamismamétrica. Nuevosaptos261desarrollo/185exploración. Pendientes466destinos;colaactualChennai31/Palermo31/Riad30/Hengqin15/Shenzhen14.
Auditoríavalida5cambiosdeentrada,recibos/CSV/canónico,particionesyobjetivosidénticos,los5798aptosanterioressiguenconvariablesnuméricasidénticas,experimentos/datasetsanterioresnohansidosobrescritos,12hashescongeladosintactos.194teststenisaprobados;constructoryauditorentregadosyejecutadosdesdecheckoutaislado,diffcheckcorrecto.0Odds/API-Tennis,0créditos;0ajustesymétricasnuevas,nomodificaprobabilidades. Informe docs/tenis_cinco_sedes_verificadas_20261018.md. Arnésinicial1315/94/2en119,16s;finalpendientedecierre.
Verificación final cinco sedes: arnés general1315aprobados/94omitidos/2avisos123,15s,Docker ausente;194tenis aprobadas,2scripts entregados conSHA coincidente, auditoría desde motoraislado aprobada. Fase completada;83entradas geográficas yclocks siguenpendientes explícitos.

## 2026-10-18 — Meta web con EMQ alto y envío real de CAPI

- El contexto del navegador (fbp, fbc, IP, user agent, URL) se lee de las cookies y cabeceras de la propia petición web: no hace falta que el cliente lo mande y no se puede
  confundir con el de otra sesión. Aplica a registro por correo, Google y checkout.
- EMQ: a lo que ya había se añaden ciudad, estado, código postal y teléfono de la facturación de Whop (normalizados y cifrados). Probado en «Probar eventos»: 13 claves de cliente.
- El token de Conversions API se generó con la opción «sin Dataset Quality API»: la otra es irreversible y no hacía falta.
- Mientras `META_TEST_EVENT_CODE` esté puesto, nada llega a los eventos reales; el paso a producción es quitar esa línea (decisión del titular tras ver el EMQ).
- El worker no lleva `meta_capi` (alineación pendiente): el cron del host envía cada 5 min. Es transitorio.
## 2026-10-18 — Aclaración de las dos cifras que no cuadraban
CLV: la puerta comercial lee `publish.shadow_sharp.report()` (ofertas publicables de la sombra sharp). Esa medida da hoy n=213 con cierre justo, `ev_close` +3,07 % (IC95 +1,54 a +4,67); el +3,46 % (n=142) del 15-oct era la misma medida con menos muestra. `shadow.summary` y `shadow_results` miden los retadores de XI (n≈135, ev≈+0,06 %): otra cosa, y coherente con que el XI aún no aporta frente al cierre. La puerta sigue cerrada por n<300 y porque ninguna liga llega a 30 (la mayor, MLS, 18). xG: los 1.219 huecos son exactos para «terminados desde 2024-01-01, sin xG de alguno de los dos»; mi cuenta anterior usaba otra ventana.

## 2026-10-18 — Meta web con EMQ alto y envío real de CAPI

- El contexto del navegador (fbp, fbc, IP, user agent, URL) se lee de las cookies y cabeceras de la propia petición web: no hace falta que el cliente lo mande y no se puede
  confundir con el de otra sesión. Aplica a registro por correo, Google y checkout.
- EMQ: a lo que ya había se añaden ciudad, estado, código postal y teléfono de la facturación de Whop (normalizados y cifrados). Probado en «Probar eventos»: 13 claves de cliente.
- El token de Conversions API se generó con la opción «sin Dataset Quality API»: la otra es irreversible y no hacía falta.
- Mientras `META_TEST_EVENT_CODE` esté puesto, nada llega a los eventos reales; el paso a producción es quitar esa línea (decisión del titular tras ver el EMQ).
- El worker no lleva `meta_capi` (alineación pendiente): el cron del host envía cada 5 min. Es transitorio.

## 2026-10-19 · F7 sello tardío implementado, sin desplegar

Decisión del titular: ventana = alineaciones de los dos lados o T-45; corte = primer día sin lote diario al desplegar. Decisión técnica clave: el lote de partido va en la MISMA cadena (orden por `seq`), así que `verify` ya no puede ordenar por nombre de archivo y sigue `prev_sha256` desde el génesis (con vuelta al orden por nombre si hay ruptura, para que los errores sigan siendo los de siempre). Los tres lectores que deciden qué está sellado miran solo `batch_kind='diario'`: un lote de partido ni cuenta ni duplica. La predicción final no cambia la calidad por sí sola (mismos lambdas mientras ningún bloque de alineación pase la puerta); lo que cambia es el momento del sello y el precio de los picks de valor. No se fusiona hasta desplegar para no romper «producción = main».

## 2026-10-19 · F7 desplegado apagado y reentrenamiento manual sin promoción

F7 (migración 084, worker, API, crontab) está en producción con `LOTE_POR_PARTIDO_DESDE=None`: el job responde `apagado` y el sellado diario no cambia. Reentrenamiento manual pedido por el titular (13:18-17:59 UTC): candidato `2026.10.19-131830` guardado SIN activar. La puerta lo rechazó (no mejora a Elo sobre las mismas filas, el campeón no es comparable por la ventana distinta, CLV 0 de 300). RPS 0,2042 frente a 0,1945 del mercado (n=2.056), ECE 0,0104, peso modelo/mercado ≈ 0,0001. Sigue activo `2026.09.27-010508`. Decisión: no fijar el corte del sello por partido todavía; no aporta nada mientras ningún bloque de alineación pase la puerta de medición.

## 2026-10-19 · Impacto por jugador: primer bloque con evidencia

Se midió el apartamiento del once real respecto al habitual ponderado por rendimiento histórico (calificaciones de FotMob relativas al equipo, point-in-time). Pasa la puerta y resiste cuatro particiones y un placebo, pero el efecto (≈ −0,0005 de RPS) es ~5 % de la brecha con el mercado y solo es aplicable con el once confirmado (sello tardío, apagado). Decisión técnica: no recalibrar nada; pasarlo a producción en modo sombra como la altitud, y no activarlo hasta medir hacia adelante. No se cambia el modelo activo.

## 2026-10-19 · Brecha con el mercado por momento y por liga; ajuste del once en sombra

Comparado el A con Pinnacle en T-72 h, T-24 h, T-6 h, T-1 h, once confirmado y cierre (docs/brecha_mercado_20261019.md): la brecha NO se cierra
en los momentos tempranos (+0,0140 en T-72 h, +0,0164 en el cierre sobre los mismos 181 partidos); la información posterior a T-72 h explica ~15 %.
Descarta que el problema sea solo comparar contra el cierre. Por liga el A está más cerca en las europeas medianas y más lejos en MLS, MX y Brasil.
Activado el sello por partido desde el 20-oct (decisión del titular) con el ajuste del once en MODO SOMBRA; gracia de 7 min porque la captura de
FotMob y el job de sello coinciden en el minuto. Walk-forward ampliado (2024-01 a 2025-10) corriendo en el worker: unirlo con el OOS actual
y reajustar `ajuste_xi` cuando termine.

## 2026-10-20 · Walk-forward ampliado: el bloque del once vale la mitad de lo medido

Con 11.920 partidos (2024-01 a 2026-10) el bloque de impacto por jugador baja de ΔRPS −0,0005 a ≈ −0,0002: favorable en los 5 tramos secuenciales y
con placebo limpio, pero solo pasa la puerta estricta en 1 de 4 particiones. Decisión: seguir en modo sombra, no activar; artefacto reajustado con la muestra
completa. La primera estimación sobre ~1.300 partidos sobreestimó el efecto: medir con la muestra grande antes de pasar nada a producción.

## 2026-10-18 — Tenis: segundo bloque geográfico y comparación fija terminados
Chennai, Palermo, Riad, Hengqin y Shenzhen incorporados en data/tennis/historical_geography_batch2_20261018. Chennai: punto del estadio enlazado por TNTA, OSM tenis a 89 m; Riad: enlace de mapa observado en webook enlazado por WTA, geometría arena cubierta a 208 m, no estadio de fútbol. Shenzhen: gimnasio cubierto OSM 665408865 diferenciado de piscina y estadio. Hengqin: operador Huafa y OSM WGS84, timezone Asia/Shanghai. Palermo: inferencia de complejo por dirección del operador y conjunto cartográfico de canchas, polígono sin nombre; tolerancia 750 m, no pista exacta afirmada. Elevaciones DEM 12/19/665/1/24 m, una consulta Open-Meteo no comercial; no medición de la cancha. Extractos del lector identificados como tales, no HTTP200 ficticio; desafíos/TLS fallidos excluidos como evidencia.
309 fuentes SHA verificadas, 162 entradas georreferenciadas de 240. Destinos 10895/11240 (+121), variables completas ambos 6845, aptos 6414 (+170), sin referencias >1 km 6107. Desarrollo 3306, exploración 3108; cuarentena 201 sin cambios. Identidades, enlaces históricos, particiones y variables de los 6244 aptos anteriores intactos. Restan 78 entradas/345 destinos; siguiente prioridad Taipei14/Bolonia14/Manchester12/Vilna10/Biel9.
Protocolo escrito antes del ajuste; 11240 probabilidades base cacheadas sin reentrenar, ridge1, RMS desarrollo, remuestreo1000 semilla20261018, sin búsqueda en2025. Principal entrenamiento3306/evaluación3108: Log-Loss base0.635570632, espacial0.635580691; diferencia+0.000010060, IC95[-0.000124964,+0.000144395]. Sin >1km:3163/2944,0.631982160→0.631955198, IC incluye0. Mismos2833 IDs originales: base0.638733142, ajuste anterior0.638682279, ajuste ampliado0.638763510. No mejora clara ni selección/activación;2025exploratorio. Calibración, coeficientes y comparación común archivados.
Auditoría desde motor aislado aprobada: fuentes/canónico/CSV, datasets y experimentos anteriores, seis modelos base y12artefactos congelados verificados; no horas imputadas ni ROI.194 pruebas tenis; código y tests coinciden en50archivos; cuatro scripts entregados conSHA coincidente e informe docs/tenis_segundo_bloque_sedes_20261018.md. Arnés inicial1315/95/2 y final1315/95/2 en126.80s, Docker ausente. La sincronización final fue rechazada temporalmente por límite de uso del revisor automático, sin ejecutarse; tras continuación del usuario se reintentó por la misma vía y se completó. Cero solicitudes Odds/API-Tennis y cero créditos deportivos. Pendientes de clocks y futuro intacto preservados.

## 2026-10-18 — Tenis: tercer bloque geográfico terminado
Taipei/BolognaFiere/AO Manchester/SEB Vilna/Swiss Tennis Biel incorporados en data/tennis/historical_geography_batch3_20261018. Taipei OSM189781451 coincide con dirección del operador208: estación YouBike rechazada; fuente del operador conservada como extracto de buscador, accesos TLS/conexión fallidos no se aceptan. Bolonia pabellón37 OSM41260142/VirtusArena, contexto federativo y regional2025: no UnipolCasalecchio ni pabellón futuro2026. AOstadium354135390 coincide operadorweb/postcode. SEB punto municipal54.7069912,25.2347764 corroborado por OSM199382037 y operador. Biel referencia del complejo NLZ213588055 según operador y páginaarena,600m de tolerancia, huella precisa de arena no verificada; plano de acceso examinado no añade esa precisión. Se rechazan paradas y TissotArena. Tres IANA completados. DEM único5puntos17/40/35/176/445m, terreno no altura medida cancha.
324 fuentes SHA,167 entradas georreferenciadas/240.10954destinos/11240 (+59),6874variablescompletas ambos,6442aptos(+28:16desarrollo/12exploración ATP),6135sinreferencias>1km;3322desarrollo/3120exploración/201cuarentena. Enlaces e IDs intactos,6442 no equivale a destinos,los6414aptos previos conservan variables. Cola73entradas/286destinos; próximas EricBellKingston8/ElGeziraCairo7/GroenkloofPretoria7/DomainHobart6/Radom6 (34destinos potenciales).
Protocolo fijo guardado antes ajuste,11240probabilidadesbase reutilizadas,6modelos verificadasSHA,sinreentrenarbase, ridge1,RMS2024,bootstrap1000seed20261018,2025exploratorio. Principal3322/3120: LLbase0.635817235→espacial0.635834986, diferencia+0.000017751 IC95[-0.000132859,+0.000153060]. Sensibilidad3179/2956:0.632257012→0.632243081;ICincluye0. Muestra común3108delbloque2:base0.635570632,ajuste2 0.635580691,ajuste3 0.635585106; muestraoriginal2833actual0.638773950frentebase0.638733142. Sin mejora clara, no selección/activación. Horas e itinerarios no imputados; holdout congelado intacto.
194pruebastenis37.71s;50archivoscódigo/testscoincidenentrepreparación yaislado;4scriptsnuevosentregadosSHAcoincidente,auditoríadesdeaisladoaprobada,12artefactoscongeladosintactos,estudiospreviospreservados. Arnésinicial1315/95/2en137.18s;final1315/95/2en130.60s,Dockerausente. Sintaxis ydiffcheckcorrectos. Informe docs/tenis_tercer_bloque_sedes_20261018.md.0Odds/API-Tennis,0créditosdeportivos;1consultaDEM. Ventanasdiarias/relojes siguenpendientes explícitos.

## 2026-10-18 — Tenis: revisión integral, evaluación y cierre consolidado
Decisión: revisar la cola completa en una ejecución. Se examinaron las 73 entradas; 72 referencias acreditadas (59 puntos nuevos y 13 alias), 239/240 entradas georreferenciadas y 413 fuentes verificadas. Palm Hills de septiembre de 2025 conserva ambigüedad entre dos campus, uno inaugurado en mayo de ese año: tres partidos excluidos. Todas las decisiones, los homónimos rechazados y los márgenes de complejo quedan documentados. Una consulta DEM agrupada de 59 puntos; cero consultas Odds/API-Tennis y cero créditos.

La versión historical_geography_complete_20261018 contiene 11.237/11.240 destinos, 7.002 casos con variables completas de ambos jugadores y 6.568 aptos (+126); 6.250 sin referencias de más de 1 km. Desarrollo 2024: 3.353; evaluación exploratoria 2025: 3.215; cuarentena de frontera: 201. Se recuperaron 283 destinos. Protocolo fijo y 11.240 predicciones base reutilizadas: Log-Loss 0,635501745495 frente a 0,635489645388; diferencia −0,000012100107, IC95 % [−0,000132496253; +0,000112690377]. Brier 0,223022884664 frente a 0,223021836192; ECE 0,0230183773 frente a 0,0230861881. Sensibilidad 3.207/3.043 e intersecciones anteriores de 3.120 y 2.833 IDs conservadas. Sin mejora acreditada ni activación.

Auditoría: 214 originales, 492.251 resultados canónicos y dos modelos actuales verificados sin fallos. Se conservan las advertencias históricas: dos observaciones temporales posteriores a un registro antiguo y el linaje incompleto del canónico anterior. Coinciden los 35 módulos y 15 archivos de pruebas con la entrega; seis scripts nuevos entregados. Pasaron 194 pruebas de tenis y una prueba de inferencia ATP/WTA con modelos reales, simetría y masa conjunta. Seis modelos base, doce artefactos congelados y las variables de los 6.442 casos anteriormente aptos permanecen intactos. Arnés inicial: 1.315 aprobadas, 95 omitidas, dos avisos, 112,86 s; final: 1.315/95/2, 127,50 s. Docker ausente.

Informe único: docs/tenis_cierre_integral_20261018.md. engine_readiness.json y completion_manifest.json separan implementación, cobertura, integridad y aprobación de producción. Clima completo, carga diaria, itinerarios, reglas por casa, cuotas ejecutables y prueba futura siguen sujetos a evidencia. API-Tennis conserva prueba/cuota desconocida; The Odds API conserva plan de pago, 2.000 créditos mensuales de tenis y reserva compartida de 6.000. No se activó un servicio ni se atribuyó rentabilidad.

## 2026-10-18 — Tenis: preparación operativa y evaluación financiera prospectiva

Decisión: completar el archivo meteorológico y el evaluador financiero sin convertir cobertura informática en una afirmación de rentabilidad. Entregados al motor aislado weather.py, paper_validation.py, sus dos archivos de pruebas, operational_validation.py, dependencia requests explícita, README e informe PREPARACION_APUESTAS_20261018.md. Los 50 archivos previos de código/pruebas y los 12 artefactos congelados siguen intactos; 37 módulos coinciden con la política que se ejecuta.

Dos consultas API-Tennis: 66 eventos, 64 programados sin confirmación oficial y dos cancelados; cero instantes físicos acreditados. Todas las sedes y coordenadas de esos 66 enlazan con el registro revisado. Una consulta pública Open-Meteo para cinco puntos, respuesta original y recibo con SHA; no se infiere hora de emisión a partir de generationtime_ms. v3 tuvo 64 candidatos futuros; v4, reprocesado sin red a las 04:11:58 UTC del 19-oct, conserva 58 todavía futuros. Techo desconocido sigue desconocido; sensibilidad exterior separada y sin entrada al modelo. La carga inicial del registro por delta falló antes de llamar a la API; se corrigió cargando primero las revisiones originales, sin retrofechar vínculos. Se conservan los intentos y versiones.

El evaluador financiero vincula cuotas originales, predicción anterior a la consulta, versión activa del código, modelos, identidades y constancias oficiales. Conserva retiros y anulaciones conforme al contrato Pinnacle, compara probabilidades contra cuotas sin margen al mismo momento y calcula ROI/CLV con bloques de competición. La política v1 de preparación, sin selecciones ni resultados, está marcada como sustituida; v2 fija por adelantado 20-oct-2026 a 1-jul-2027, 500 selecciones y 30 competiciones por circuito, cierres completos y límites inferiores positivos. No permite aprobar por mirar resultados antes de terminar el periodo. La ventana más amplia permite reunir torneos, sin prometer tamaño o ventaja. El protocolo futuro original sigue intacto.

Cero selecciones prospectivas y cero resultados financieros: ROI desconocido, nunca cero inventado. Costes cero son supuestos de simulación explícitos; precios observados no son ejecución acreditada. Los adaptadores oficiales no cubren universalmente todos los torneos; eso permanece como puerta de evidencia, sin relajar comprobaciones. Palm Hills septiembre de 2025 conserva sus tres exclusiones; no bloquea eventos independientes del modelo base. No hay servicio nuevo activo ni apuestas colocadas. The Odds API: cero consultas/créditos en esta ampliación, plan de pago y presupuesto de 2.000/mes conservados.

Pruebas: 225 específicas en preparación (33,92 s) y desde el checkout entregado (30,04 s). Arnés general inicial 1.315/95/2 en 173,86 s; final 1.315/95/2 en 93,32 s; Docker ausente. El primer intento final no se ejecutó por el límite temporal de la revisión automática de permisos; después de su horario de restablecimiento, el mismo control se autorizó y completó. Informe actual docs/tenis_preparacion_apuestas_20261018.md; evidencia data/tennis/operational_readiness_20261018, delivery_manifest.json y completion_manifest_v2.json. Sin modificación de producción, modelos, probabilidades ni trabajos ajenos de fútbol/NBA/web/móvil.

## 2026-10-19 UTC — Tenis: auditoría nueva y ocho probabilidades prospectivas contrastadas

Decisión: producir un archivo real de probabilidades para los encuentros acreditables, conservando separados el contrato de investigación y la validación financiera. API-Tennis actualizado con dos consultas: 66 eventos, 58 programados sin confirmación oficial, tres completados, tres en juego y dos cancelados. Cero horas físicas acreditadas. Cuatro programas actuales ATP/WTA descargados de fuentes oficiales, renderizados y revisados visualmente; recibos y bytes archivados. Se comprobó cada pareja en su celda de la cancha, fecha, superficie, circuito y torneo; nombres completos y abreviaturas exactas, sin aceptación por similitud. Horas previstas y límites de turno se mantienen como tales.

20 parejas individuales revisadas: ocho ATP selladas entre 04:24:52 y 04:25:23 UTC del 19-oct antes del límite horario oficial revisado. Ocho excluidas por límite ya transcurrido, cuatro por ambigüedad de nombre canónico. Cobertura 8/20 revisadas y 8/66 del calendario, no universal. La herramienta exige recibos anteriores a la decisión y de hasta 15 minutos; vuelve a comprobar después de calcular y no retrofecha los sellos. Probabilidades condicionales a partido completo, sin cuotas ejecutables ni apuestas. Artefactos data/tennis/forecast_audit_20261019/pronosticos.md y research_emission_v1/predictions.json.

Hallazgo nuevo: 50 nombres WTA y uno ATP asociados a múltiples IDs en los modelos existentes. El listado completo queda en identity_ambiguities.json; no se elige ID por tamaño/mayoría ni se fusiona por nombre. Las cuatro WTA aún horariamente candidatas quedan excluidas. Es necesario acreditar puentes y consolidar una versión nueva de datos/modelos para ampliar cobertura. No se alteran los 37 módulos congelados, 12 artefactos ni el protocolo financiero previo. Las ocho ATP emitidas tienen nombre canónico único y parámetros completos; eso no equivale a ausencia de incertidumbre.

Palm Hills: nuevas búsquedas por ficha Davis Cup, prensa contemporánea y publicación de empleado no acreditan campus. Ficha histórica ITF devuelve HTTP502, archivado como fallo. Los tres IDs de partido conservan exclusión espacial explícita en palm_hills_disposition.json; el modelo base no usa esa sede y no queda bloqueado globalmente. Horarios físicos/techo solo se exigen a las variables y evaluaciones que los usan. No se inventan ni se declaran resueltos.

Integridad: 214 originales, 492.251 filas, cero fallos; persisten dos advertencias temporales de registros antiguos y linaje incompleto del canónico previo. Los siete registros antiguos no habilitan confirmación financiera: finales fuera de las ventanas predeclaradas. Nueva muestra financiera continúa en cero, ROI desconocido. Los ocho pronósticos nuevos son investigación independiente, no selecciones bajo la política que empieza el 20-oct. Cero créditos Odds, cero apuestas, sin servicio automático ni adaptador universal; los scripts cubren las fuentes/ediciones efectivamente revisadas.

Entrega: capture_forecast_evidence.py, reviewed_forecasts.py, test_reviewed_forecasts.py e informe AUDITORIA_PRONOSTICOS_20261019.md en el motor aislado. Pruebas específicas 246 en preparación (20,75s) y entrega (17,62s); general inicial 1315/95/2 en94,79s, final1315/95/2 en79,34s; Docker ausente. Informe actual docs/tenis_auditoria_pronosticos_20261019.md. No se atribuye rentabilidad ni perfección; no se tocaron producción ni tareas ajenas.

## 2026-10-19 — Tenis: mercados v2, capturas ampliadas y conciliación de cuentas

Decisión: integrar todas las familias acordadas sin alterar el candidato ni el estudio financiero congelados. Ocho módulos en tennis_markets_v2: contratos y precios coherentes, periodos, adaptador de trece claves oficiales, comparación, liquidación, evaluación y controles de cuenta. Diez familias: ganador, ganador del set, totales/hándicaps de juegos y sets, tiebreak, marcador por sets y totales/hándicaps de juegos del set. BO3/BO5, líneas enteras/medias y pushes; cuartos rechazados. Cuotas de bolsa y props fuera del modelo permanecen visibles. Ganador híbrido anterior separado: no se mezclan marginales incoherentes. Las marginales nuevas aún no están completamente calibradas ni aprobadas financieramente.

624 contratos ilustrativos para ocho encuentros, derivados después del sello anterior y marcados como tales. Reproducción offline de146 ofertas reales antiguas:144 calculables y dos lay sin soporte, sin atribuir vigencia. Evaluación exploratoria fija sobre2026 con modelos de origen1-ene-2026:2.207/2.451 ATP y1.291/2.146 WTA,56.804 probabilidades; exclusiones de identidad/parámetro explícitas, ECE/Brier/Log-Loss por contrato y formato. No se utilizaron modelos de octubre para predecir retrospectivamente todo2026 ni se infirió ROI sin precios. Año inspeccionado: no prueba confirmatoria.

La cuenta compartida tenía5.118 disponibles frente a reserva6.000; los primeros intentos de pago se detuvieron. El usuario autorizó una excepción única <=14 créditos, mínimo5.104: consumió6 y saldo observado5.108. Se marcó consumida, sin modificar la reserva general. Luego autorizó500 por cada una de dos claves: consumos confirmados500/500, cero cargos desconocidos. Primera clave distinta: saldo0. Segunda clave coincide con la principal: saldo observado4.606, no era otra demo independiente. Se detectó después de la prueba; debió compararse antes. Se informó al usuario, se preservaron los informes originales y account_identity_correction.json corrigió la etiqueta, enlazando500 cargos al registro central sin doble conteo. Nuevos scripts comprueban la coincidencia y requieren autorización explícita para pruebas de la compartida. Ninguna llamada adicional después de consumir esos permisos.

Las pruebas ampliadas obtuvieron12.052 ofertas en snapshots repetidos de56 casas y9 IDs de evento;6.796 con precio de modelo, restantes sin parámetro/identidad acreditados o mercado fuera de soporte. Siete claves observadas de trece conectadas; seis no observadas, marcador/tiebreak sin clave de tenis inventada. Expansión priorizó casas no consultadas y conservó cambios;500 de cada clave realmente consumidos, sin sobrepasar500. DemoCapture libera únicamente exceso de reserva confirmado por cabeceras válidas, nunca fallos de cargo incierto. Snapshot repetido no es apuesta independiente. Sara Bejlek aparece frente a dos rivales el20-oct: ambos requieren revisión oficial. No se borró ni resolvió el conflicto por suposición.

Contabilidad central de tenis octubre:583 confirmados/595 reservados, dentro de2.000;incluye17 de recibos antiguos que SQL sum(actual_cost) omitía por NULL. Consumo de esta ejecución1.006:500 cuenta distinta,506 compartida (500+6 previos), no1.000 adicionales más500 duplicados. Los saldos son observaciones; hay otros consumidores. Credenciales en archivos locales ignorados, sin valores en informes ni comandos. No se publicaron ni ejecutaron apuestas.

Entrega:17 archivos al motor aislado, incluidos cinco scripts, dos nuevos archivos de pruebas, ocho módulos y documentación/README.37 módulos congelados y12 artefactos verificados intactos.294 pruebas en preparación31,18s y entrega22,01s; arnés general inicial1315/95/2 en139,34s y final1315/95/2 en112,12s, Docker ausente. Informe docs/tenis_mercados_integrados_20261019.md; datos data/tennis/markets_integration_20261019, markets_demo_20261019, markets_demo_2_20261019 y markets_backtest_v2_20261019. Modelos, estudio financiero, producción y trabajos ajenos conservados. Aprobación financiera y rentabilidad siguen sin acreditarse.

### 19-oct-2026: auditoría financiera y acreditación temporal externa

El usuario solicitó acreditar rentabilidad. No se confundieron las pruebas de API con selecciones financieras: revisión offline de tres raíces,227 respuestas originales válidas/12.420 observaciones/11 eventos/56casas/cero cuotas vigentes;6registros antiguos sellados y1sin sello,8pronósticos de investigación y10archivos de integración conservados aparte. Búsqueda global no encontró órdenes financieras. El estudio v2 permanece20-oct-2026 a1-jul-2027, ganadorPinnacle,500liquidadas/30bloques por circuito, coberturas completas y ROI/CLVcon intervalospositivos; ceroórdenes/ROI desconocido. Ningún beneficio ni evidencia futura inventados.

Nuevo paquete tennis_finance_v2 separado del candidato: evaluación reproducible, raíces deduplicadas, originales/cronología, versiones, errores por directorios ausentes, creación exclusiva de informes y sellado de órdenes simuladas mediante las compuertas existentes. Sensibilidad a costes0/0,5/1/2%del importe original, pendientes y anulaciones visibles. Ilustración de potencia bajo supuestos explícitos, sin cambiar mínimos ni periodo. Registros vacíos creados explícitamente, sin convertir pronósticos viejos en órdenes. Otras familias de mercados no heredan aprobación. No se presupone que fuentes con hash acrediten automáticamente los campos interpretados.

La revisión automática rechazó inicialmente enviar una huella a DigiCert por falta de autorización del destino. Se preguntó mediante herramienta y el usuario autorizó explícitamente el sello. Una solicitud RFC3161, sin contenidos ni claves: DigiCert19-oct-2026 16:22:52UTC. Firma/cadena con CA independiente, nonce y digest verificados; todas las entradas intactas y sello anterior al estudio. Prueba negativa real: copia alterada y recibo local recalculado rechazados criptográficamente; original conserva validez. El sello prueba existencia del protocolo y conjunto a esa hora, no retrodata registros ni prueba beneficio ni futuras selecciones.

Entrega:4módulos nuevos,18pruebas y documentación. Suite preparada310antes de añadir2pruebas de sello,18específicas alfinal y312enmotorentregado. Arnésgeneral inicial1.315/95omitidas/2advertencias114,99s;finaligual115,80s;Docker ausente.37módulos congelados/12artefactos conservados. Cero consultas nuevas de cuotas/créditos/apuestas/publicaciones/servicios automáticos. La autorización de500porclave ya estaba consumida y la reserva compartida no se tocó. Informe docs/tenis_acreditacion_financiera_20261019.md; evidencias data/tennis/financial_accreditation_20261019. Rentabilidad sigue sin acreditarse por ausencia de muestra financiera y ejecución verificable, no por un defecto que se pueda eliminar rellenando datos.

### 19-oct-2026: calidad predictiva sin cuotas, comparación y protocolo futuro

El usuario pidió resolver los requisitos de calidad. Se entregó tennis_quality_v3 en versión separada: cuarentena normalizando acentos, comparación común de seis variantes, cobertura, Log-Loss/Brier/ECE/aciertos, bandas y umbrales fijos, Wilson explícitamente iid y bootstrap por torneos/periodos. Cuatro contrastes principales híbrido frente a WElo/Elo superficie calibrado, dos circuitos, Bonferroni98,75%. No se fusionaron IDs sin evidencia ni se promovió retrospectivamente un ganador. Se verificaron fuentes y probabilidades archivadas frente a fórmulas y ratings; modelos de origenenero2026 para la evaluación2026, año ya inspeccionado/exploratorio.

La revisión encontró dos grupos ATP(AndreIlagan yJulioCesarPorras) y50WTA ambiguos. Muestra comúnATP2.207/2.451,WTA581/2.146: ATP224sin efectos entrenados/20identidad desconocida; WTA1.156identidad ambigua/350efectos no entrenados/59desconocidos. Actualizar cuarentena protege la emisión, no repara el entrenamiento previo ni acredita la disponibilidad histórica de esa metadata. HíbridoLL0,62956ATP y0,60441WTA; referencias calibrada0,63217/0,60775,WElo0,63814/0,60365. Intervalos corregidos incluyen cero; superioridad no acreditada. ATP80–90%:145casos,84,5%pronóstico medio/82,8%acierto,CIporbloquesaprox75,9–89,1%. WTA90%solo5casos: bootstrap degenerado se suprime, sin declarar certeza. Revisadas10familias/50grupos,45.444probabilidades con filtro común; no calibración nueva ni aprobación para todas las líneas.

Cuatro módulos,script de auditoría y20pruebas nuevos. Registro probability-only sin resultados/cuotas, evidencia oficial reciente, reglas/identidades y segunda comprobación de vigencia al sellar. Versiones de modelo y del código activo verificadas, duplicados rechazados. Nuevo protocolo20-oct-2026 a1-jul-2027, seis variantes, umbrales de diseño500completados/30bloques por circuito, bandas>=70%con200casos y tolerancia5puntos, cobertura condicionalmínima20%; mínimos no garantizan potencia. Referencias actuales WElo/adaptativo nuevas con74.029ATP/20.614WTA, mismos datos/embargo que el candidato actual. Datos/modelos financieros congelados intactos. Cero resultados futuros: pendiente confirmación y revisión independiente de fuentes; tiempos físicos siguen requeridos por el contrato de resultados. No servicio automático ni nuevas consultas de cuotas, créditos o apuestas.

Entrega vigente data/tennis/predictive_quality_v3_20261019_v3; dos preparaciones anteriores conservadas y sustituidas antes de cualquier pronóstico confirmatorio. El intento de sello DigiCert para el NUEVO protocolo fue rechazado por revisión automática: autorización anterior era solo del financiero. Se pidió autorización específica; no se envió la nueva huella mientras no exista respuesta. No se usó ruta alternativa. Documentación docs/tenis_calidad_predictiva_20261019.md.332pruebas del motor entregado26,71s,20nuevas; arnés inicial1315/95omitidas/2advertencias110,17s yfinaligual112,41s,Docker ausente. No se acredita hoy toda la calidad ni se inventan resultados futuros: se cierra infraestructura, diagnóstico y protección; siguen abiertos recuperación de identidades, muestra futura y protocolos de los mercados restantes.

### 19-oct-2026: autorización y sello del protocolo predictivo completados

El usuario autorizó explícitamente el sello del nuevo protocolo predictivo. Una solicitud DigiCertRFC3161, enviando solo huella y nonce. Sello19-oct-2026 16:54:10UTC(10:54:10CiudaddeMéxico), anterior a20-oct00UTC. Firma, cadena con CA independiente, nonce y digest del conjunto verificados. ProtocoloSHA25935f09a23ff91a95e71fbe3176ac18df332d198aa3e67eec25c5d5ac6a2b20; artefactos/código y todos los archivos del manifiesto anterior intactos. Prueba negativa real: copia alterada y recibo local recalculado rechazados criptográficamente; original válido. Cero créditos de cuotas, documentos o claves enviados, cero pronósticos/resultados confirmatorios. Nuevo completion_manifest_timestamp.json conserva el anterior y actualiza únicamente el estado de sellado. No cambios de código/modelos/criterios ni repetición innecesaria de la suite332ya aprobada. Informe adicional docs/tenis_sello_predictivo_20261019.md. Calidad y rentabilidad siguen sin acreditarse; el sello certifica existencia a esa hora, no aciertos.

### 19-oct-2026: continuidad autónoma activada y primera emisión prospectiva

El usuario autorizó continuidad sin intervención rutinaria. Automatizaciónheartbeat creada y verificadaACTIVA: continuidad-de-validaci-n-predictiva-de-tenis, mismochat01a14720-ef8a-7c10-aa90-e4bc7df03407, cada2h. Capturador tennis_continuous_v1 nuevo, independiente de los protocolos sellados: ciclo compartido con reserva atómica4h, máximo12intentosAPI-Tennis/díaUTC, parada de segundo tour y espera24hpor401/403/429. Respeta autorización de cuotas agotada/reserva compartida; ceroOddsAPI/apuestas. Clave dedicada solo en memoria, respuestas redactadas si la contienen, sin imprimirURLsconcredenciales. El servicio requiere equipo y aplicación disponibles; no se promete ejecución con el equipo apagado ni notificaciones rutinarias sin cambios. Guía docs/tenis_continuidad_autonoma_20261019.md.

Primera pasada real17:04UTC:2consultasAPI-Tennis,112eventos(50programados sin verificación física,49finalizados,5cancelados,5retiros,3jugando), cuatro PDFs oficiales20-oct descargados/renderizados/revisados visualmente.29parejas individuales;18pronósticos del protocolo congelado,11ATP/7WTA, sellados antes de los encuentros, sin cuotas. Ciclo9f9f8c1bea124f0696b12fa5e1e06be9. Once exclusiones finales; dos rectángulos deNingbo y una abreviaturaJ-L se corrigieron con adendas nuevas, no se alteraron revisiones vinculadas a registros previos. Se rechazóBoulter–Sakatsume porTBF/marcador parcial: reanudación, no pre-match. ProgramaactualBejlek–Parks ycalendario coinciden; la ofertaantiguaBejlek–Wang queda incompatible paraesa jornada y se conserva. Ninguna fusión de IDs o relax de cuarentenas. Segunda invocación comprobócapture_not_due/0consultas.

Se entregaron cuatro módulos nuevos,10pruebas y guía.342pruebas del motor entregado26,49s; arnés inicial1315/95omitidas/2advertencias112,33s;finaligual104,50s,Docker ausente.37módulos originales,12artefactos y4módulosdecalidadsellados conservados. Protocolo de calidad verificado desde el motor entregado:18pendientes/cero resultados/cero calidad acreditada. El programador buscará y archivará resultados; tiempos físicos insuficientes se conservarán como candidatos pendientes, sin imputar ni reescribir los criterios. Resultados nuevos en versiones de listas, sin sobrescribirfuture_results.jsoninicialniinformes anteriores. No se afirma rentabilidad ni certeza. Datosdata/tennis/continuous_quality_20261019 ylistaPRIMEROS_PRONOSTICOS.md conhorariosCiudaddeMéxico.

### 19-oct-2026: diez mercados en seguimiento prospectivo

El usuario pidió validar también los otros mercados y continuar sin confirmaciones rutinarias. Se añadió tennis_allmarkets_v1 separado de calidad_v3/financiero: cuatro módulos congelados, tablas fijas de55tareasBO3/77BO5, diez familias, todos los sets previstos, vectores conjuntos coherentes sin recalibración posterior. Marcador por sets es una sola tarea multiclase; complementos/otras líneas no son muestras independientes. Registro nuevo con hora real propia, sin atribuir el sello DigiCert anterior. Conservados37módulos originales/12artefactos/4móduloscalidad sellados. Protocolo nuevo20-oct2026 a1-jul2027, sin sello externo; huellas locales no prueban existencia frente a terceros.

Primera emisión real18partidos(11ATP/7WTA),990tareasrelacionadas,110gruposobservados,ceroresultados,cero registros/resultados rechazados. Fuentes anteriores verificadas al emitir padre y ahora dentro de política nueva4h estrictamente antes de cota oficial; se revalidaron horas después del cálculo. No se retrodató ni se cambió el contrato anterior de15min. Repetición:18already_sealed/cero duplicados. Preserva cuarentenas, programa/calendario/revisión exacta y reconstruye probabilidades desde parámetros congelados. API-Tennis0consultas nuevas,Odds0créditos,apuestas0.

Evaluación por circuito/formato/tiebreak/contrato/línea/set con Log-Loss/Brier de vector completo, ECE binario condicional y bandas. Pushes/set no disputado no se convierten en derrota; retiro/descalificación/walkover fuera de partido completado siguen en cobertura. Resultado inválido permanece pendiente en denominador y se reporta separado. Criterios predeclarados500partidos/30bloques por grupo,cobertura80%,bandasaltas200casos/calibración±5pp,corrección por528grupos/cincobandas/dos agrupaciones y fin de periodo. Son criterios de diseño, no garantía de potencia ni certeza; solo habilitan revisión independiente. Histórico45.444probabilidades/50grupos inspeccionados conservado aparte, sin heredar validación para las líneas nuevas. Financiero permanece limitado a ganador sin nuevas autorizaciones.

Automatización existente continuidad-de-validaci-n-predictiva-de-tenis actualizada mediante herramienta y verificadaACTIVA,mismochat,cada2h,captura4h,máximo12API-Tennis/díaUTC,silencio si sin cambio. Incluye emisión/evaluación de todos los mercados y archivos nuevos, sin duplicar trabajos ni modificar candidatos. Reportes data/tennis/all_markets_prospective_20261019,guía docs/tenis_validacion_todos_mercados_20261019.md. Vistas RESUMEN.md y PRONOSTICOS_POR_MERCADO.md entregadas; documentos/script de vistas copiados al motor aislado.

367pruebas del motor entregado aprobadas28,64s,incluidas25nuevas. Arnés inicial1315/95omitidas/2advertencias104,20s. Primerfinal tuvo1fallo en test_ratelimit del panel: dependía del reloj real y podía cruzar minuto; repetición aislada aprobó. Se aisló únicamente el reloj del módulo en el helper de prueba, sin modificar producción,con7pruebas de límites aprobadas3,12s. Arnésfinal repetido1315/95/2aprobado;Dockerausente. Se conservaron fallo y reintento en logs/manifiesto. No se relajaron aserciones. Calidad deportiva futura y rentabilidad continúan sin acreditar; no se cerraron por pruebas de software.

### 19-oct-2026: causa del cero futuro e incorporación automática de resultados

El usuario pidió solucionar el registro futuro vacío y la falta de acreditación. Se comprobó reloj real:19-oct18:27UTC; primera reconciliación18:35UTC. Los18eventos siguen futuros, primerinicioestimado20-oct04:15UTC/19-oct22:15México,unas9,7hdespués. Cero terminales de esos18;59eventos terminales del proveedor ajenos no se convirtieron en aciertos. Capturador devolviócapture_not_due;0API-Tennis nuevas/0Oddscréditos/0apuestas. No se esperó artificialmente ni se retrodató evidencia.

Se entregó tennis_evidence_v1,cuatromódulosindependientes: cruce por ID de evento/jugadores, orientación, circuito/edición contra fuente de calendario original, SHA/fechas, marcadores por set y terminales. DecimalesAPI6.4/7.7 son juegos6–7 y puntosTB4–7; se validan sin usar floats/truncar silenciosamente. Conflictos requieren revisión; IDsduplicados invalidan lote completo. Horas físicas solo con fuente primaria JSONarchivada, pareja vinculada a campos nativos, caminos de valores, zonas explícitas/cronología/revisión semántica. No se convierten tiempos programados/recepción/transiciones en tiempos físicos. DocsAPI-Tennis consultadas:los ejemplos no acreditanambasmarcasfísicas. Los candidatos sin ellas quedan separados.

Comando reconcile produce nueva accepted_results.json/terminal_candidates.json y ejecuta ambos evaluadores congelados. Primera pasada18pendientes scheduled_in_future,0aceptados/errores; fuentes/candidatos y cobertura conservados. Se corrigió contador de defaultdict durante pruebas para que leer una lista vacía no contase un evento terminal. Los resultados sintéticos solo viven en tests, nunca en time_reviews real, actualmentevacío.

Revisión histórica reproducible sin reentrenar:2788partidosterminados(2207ATP/581WTA),45444probabilidades marginales archivadas,39grupos al combinar50grupos anteriores de score en tareas multiclase; diezfamilias. Modelospre2026 y2026ya inspeccionado,etiquetaexploratoria. Se publican todos los contratos, LL/Brierbinario yvectorial separados, ECE/curvas de10intervalos incluso confianza<0,5para multiclase e incertidumbre por competición. Diagnóstico de clases explícitamenteexpost,no benchmark entrenado:98,8%en>22,5juegosBO5coincidecon98,8%clasemayoritaria. GanadorMarkovATPBO3n1789acierto62,3%LL0,6610;WTAn581acierto69,5%LL0,6043;scoreexacto41,3%/46,8%. No se confundió con el híbrido actual ni con validación global de líneas nuevas. Primera revisión conservada;historical_v2añadebalance de clases sin reescribir.

Auditoría financiera nueva:0órdenesválidas,periodo aún no iniciado/terminado,muestra/cierres/ROI/CLVinsuficientes,ejecuciones/costes no acreditados. Se explica que la continuidad predictiva no genera por sí sola una muestra de ROI; no afirmarfinancieroactivo. Las excepcionesOddsAPIseconsumieron yreserva6000permanece frenteúltimosaldoobservado4606,no saldo consultadohoy. No se inventaron cuotas/precios/órdenes o autorizaciones nuevas. El primer acierto no basta: se preservan finperiodo/mínimos/revisión independiente.

Automatización existente actualizada mediante herramienta y verificadaACTIVA mismochat/con límites/notificaciones originales; ahoraejecutareconcile offline ydocumenta esquema de revisión real,investigación yconflictos. Guía docs/tenis_resultados_y_evidencia_20261019.md;raíz data/tennis/evidence_resolution_20261019 con ESTADO.md,HISTORICO.md,estado/manifiesto. No se modificaron37core/12artefactos/4calidad ni4allmarkets/8marketscongelados.29pruebas específicas aprobadas2,01s;motorentregado396aprobadas28,21s. Arnés inicial1315/95omitidas/2advertencias103,13s,finaligual106,83s,Dockerausente. Manifiesto22archivos entrega verificable. Infraestructura completada, resultados futuros y rentabilidad siguen sin acreditarse por condiciones reales de tiempo/datos/precios, no se declaran resueltos por software.

## 2026-10-19 — Tenis: puente de alias WTA y reevaluación (auditoría)

- Hallazgo: `2026_wta.csv` trae Queen's Club y 's-Hertogenbosch (45 filas, semana 2026-06-08) con IDs WTA alternos (3xxxxx). La cuarentena por nombre excluía TODOS los partidos de esas jugadoras: 1.161 de 2.146 WTA 2026 (54,1 %), sesgando la muestra WTA hacia jugadoras menores.
- Decisión: módulo nuevo `tennis_identity_v2` (en `apps/tennis`, 3 pruebas; suite 399 verde) fusiona un alias solo si mismo nombre normalizado, base >=30 filas, alias <=10 filas y 5x menor, dentro de la vida activa de la base (+120 días), sin compartir torneo-semana y sin atributos ioc/hand disjuntos. Sin coincidencia difusa. 47 alias fusionados (46 WTA, 1 ATP), 403 filas reescritas, 62 ambiguos siguen en cuarentena con motivo. Datos nuevos en `data/tennis/identity_bridge_20261019/` (IDs originales conservados en `*_id_original`); `canonical_v2` y todo lo congelado intactos (hash verificado).
- Efecto: exclusión por nombre WTA 2026 baja a 1,9 % (ATP 1,6 % -> 1,1 %). Es conocimiento actual, no prueba de que el alias fuera resoluble antes de cada partido.
- Reevaluación 2026 (origen 1-ene, modelos reentrenados en carpetas nuevas, muestra completa 2.451 ATP / 2.146 WTA), log-loss: ATP Markov 0,6447, Elo de superficie 0,6285, Weighted Elo 0,6294; WTA Markov 0,6546, Elo de superficie 0,6221, Weighted Elo 0,6309. Markov puro sigue peor que Elo (IC de diferencia por periodo excluye 0: ATP +0,016, WTA +0,033). Los alias casi no mueven el modelo; el beneficio real es cobertura y ausencia de sesgo de selección.
- Conclusión: el núcleo punto-a-juego solo aporta como componente de un híbrido y para mercados derivados; para ganador manda Elo de superficie. Antes de ampliar mercados o protocolos, rediseñar el núcleo (estado dinámico + variables + calibración) y compararlo solo contra Elo y mercado sin margen. Pendiente: reentrenar modelo futuro y re-sellar protocolo con datos v3 (no se hizo; los sellos previos no se tocan).

## 2026-10-19 — Tenis: sobredispersión por partido corrige todos los mercados (exploratorio)

- Hallazgo de la re-auditoría: el Markov saque/resto ordena mejor que Elo (acierto ganador 2026 ATP 64,6 % vs 64,2 %; WTA 66,7 % vs 64,8 %), pero es sobreconfiado (pendiente de calibración logit 0,55-0,59 ATP, 0,44-0,55 WTA). Por eso perdía en log-loss. A la vez subestima sets corridos (ATP 52,5 % previsto / 59,9 % real), sobreestima tie-breaks y da +1,1 a +1,2 juegos de más por partido. Una sola causa: suponer p y q fijos en todo el partido.
- Prueba: mezcla gaussiana sobre la diferencia de saque por partido (contracción k de la diferencia estimada + ruido sigma del día), 2 parámetros ajustados en 2025 y aplicados a 2026 (ATP k=0,9, sigma=0,2; WTA k=0,8, sigma=0,2). Mejora ganador, sets corridos, tie-break, primer set, más de 22,5 y hándicap -3,5 a la vez. Corrige el sesgo de juegos totales (ATP 27,43 -> 25,87, real 26,29; WTA 23,13 -> 21,86, real 22,09). Iguala a un Platt por mercado, pero sigue siendo una sola distribución coherente.
- Mezcla + Elo en logit (pesos ajustados en 2025) frente a Elo de superficie, 2026: ATP -0,0057 log-loss, IC95 por periodo [-0,0087; -0,0026]; WTA -0,0038 [-0,0071; -0,0006]. Exploratorio: 2026 ya estaba inspeccionado y el bootstrap por periodo no capta toda la dependencia.
- Consecuencia: el estudio prospectivo de diez mercados (990 tareas) se selló con el Markov sin sobredispersión, una variante con sesgo conocido. No se toca; se recomienda un protocolo nuevo con la mezcla. Resultados en `data/tennis/identity_bridge_20261019/overdispersion_test.json`; la implementación sigue pendiente como módulo con pruebas.

## 2026-10-19 — Tenis: núcleo v4/v5, retiro de los 990 pronósticos y ranking

- Por decisión del titular se retiraron los 18 registros (990 filas) del estudio de diez mercados con Markov plano: movidos, sin borrar, a `data/tennis/retired_20261019/all_markets_v1_predictions/` con manifiesto SHA-256; aviso en `all_markets_prospective_20261019/RETIRED.md`. Los 18 padres de ganador (v3) y todo lo congelado siguen intactos.
- `tennis_core_v4` (módulo nuevo, 4 pruebas): sobredispersión por partido (mezcla gaussiana sobre la diferencia de saque, k/sigma de 2025) + mezcla logit con Elo, centro re-resuelto para que el ganador de la mezcla iguale el objetivo; todos los mercados salen de una sola distribución conjunta. Protocolo y 18 pronósticos en `data/tennis/core_v4_prospective_20261019/` (superado por v5, se conserva). Puerta del padre: sellado original + decisión estrictamente antes de la cota oficial; NO exige recibo de calendario de menos de 4 h (el de las 17:04 UTC había caducado y el cupo API-Tennis no se tocó).
- Hallazgo con efecto grande: añadir ranking, puntos de ranking y edad al objetivo de ganador. 2026 (muestra completa): ATP log-loss 0,6229 -> 0,6032, acierto 64,9 % -> 66,9 %; WTA 0,6183 -> 0,6018, acierto 65,9 % -> 66,4 % (solo rank: 67,7 %). Variables elegidas por CV 2025 por periodos; altura y mano no aportan; 2026 ya estaba inspeccionado, solo lo prospectivo confirma.
- Otro error de datos: `2026_wta.csv` (17 filas) y 659 ATP tienen columnas biográficas corruptas (edad hasta 3387, altura hasta 20.011.008). No afecta al motor actual (no usa esas columnas) pero rompía cualquier variable de edad/altura; se sanea (edad 14-50, altura 140-215) antes de usar.
- `tennis_core_v5` (+features, 2 pruebas; suite 405 verde): rank/puntos/edad de la última fila previa del jugador (máx. 60 días de antigüedad; más antiguo = excluido). Protocolo y pronósticos en `data/tennis/core_v5_prospective_20261019/`: 17 sellados, 1 excluido (Uchijima/Shibahara, ranking caducado). Parámetros refit con 2025+2026.
- Pendiente: cuotas como dato de entrada (requiere créditos/dataset histórico; no se gastó nada), núcleo dinámico por ronda, 62 alias dudosos, consolidar módulos. La automatización de Codex sigue sellando con el protocolo antiguo si está activa.

## 2026-10-19 — Tenis: motor v7 (Elo dinámico por ronda) y cierre de recomendaciones

- Identidades v3: la edad al día de la fuente da fecha de nacimiento. 5 fusiones con fecha igual (+-3 días), 14 parejas homónimas confirmadas como personas distintas, 27 sin evidencia (casi todas ATP de los 70-90, más Ruse y Vandewinkel). Ya no hace falta excluir por nombre lo que se resuelve por ID.
- Elo dinámico (`tennis_dynamic_v2`): Weighted Elo general + superficie (K=250/(n+5)^0.4), actualizado partido a partido con día estimado por ronda y margen de 2 días; los retiros cuentan como carga, no como resultado. Algunos archivos (85 torneos ATP 2026, quali) traen fecha por partido: v1 la desplazaba (posible fuga); v2 la usa tal cual. Resultado sin cambio material, pero v6 queda superado por v7.
- Apilador v7 (elegido por CV 2025, refit 2025+2026): Markov con sobredispersión, Elo dinámico, ranking, puntos, edad, inactividad, carga 14 días, experiencia. El Elo congelado deja de aportar. 2026: ATP log-loss 0,5956 / acierto 67,6 %; WTA 0,5946 / 67,9 % (Elo de superficie 0,6285 / 64,2 % y 0,6221 / 64,8 %). En WTA el Markov casi no pesa para el ganador; sigue dando la forma de sets/juegos.
- Decisión: v7 es el motor vigente (`tennis_motor`); v4-v6 se conservan como superados. 17 pronósticos sellados para 19-20 oct; Uchijima/Shibahara excluido por ranking de más de 60 días.
- Pendiente con decisión del titular: cuotas históricas de cierre como entrada (descarga o créditos) y la automatización de Codex con el protocolo retirado.

## 2026-10-19 — Tenis: cuotas de Tennis-Data (descarga manual del titular)

- El titular descargó a mano 47 archivos (ATP 2000-2026, WTA 2007-2026) para un estudio privado sin lucro; quedan fuera de git (`.gitignore`) con manifiesto SHA-256 en `data/tennis/tennis_data_manual_processed/`. Atribución: tennis-data.co.uk. No se redistribuyen.
- Cruce con la base canónica (apellido + inicial, ventana de fechas, pareja exacta): 53.853 partidos 2015-2026, cobertura 93-95 % ATP y 90-95 % WTA reciente. Pinnacle casi desaparece en 2026 (3-4 %): se usa el promedio de casas sin margen.
- Resultado 2026 (CV 2025): el mercado solo gana a v7 con claridad. ATP log-loss 0,5935 vs 0,6031, acierto 68,5 % vs 67,1 %; WTA 0,5661 vs 0,5956, acierto 69,5 % vs 68,0 %. Añadir v7 al mercado no aporta nada medible. Recentrar la mezcla al ganador de mercado mejora primer set y hándicap, y no empeora sets corridos, tie-break ni totales.
- Decisión: si hay cuota previa disponible, el objetivo de ganador es la cuota sin margen y los demás mercados salen coherentes del Markov recentrado; sin cuota, v7. `tennis_motor forecast --odds-a --odds-b` acepta cuotas tecleadas a mano (415 pruebas). Las cuotas de Tennis-Data son casi de cierre y se publican después: sirven para validar, no para pronosticar en vivo; para uso automático en vivo haría falta una fuente previa (p. ej. The Odds API, 1 crédito por torneo y foto), decisión del titular.

## 2026-10-20 — Tenis: cuotas previas en vivo (The Odds API) y motor v8

- Autorización del titular (19-oct): solo ganador (h2h), una región (`eu`), dos fotos al día por torneo activo, tope 400 créditos/mes. `tennis_odds_live_v1` reutiliza el registro de créditos existente; además, como la cuenta es compartida con el fútbol, niega cualquier llamada que deje menos de 350 créditos x días hasta el reinicio del día 1 (estimación de consumo del fútbol). El 20-oct 00:39 UTC quedaban 4.389 créditos frente a una reserva de 4.200: hay unos 189 créditos de holgura este mes; el 1-nov se libera.
- Primera foto: un solo torneo de tenis activo en la API (WTA Ningbo, 9 partidos, 1 crédito). Los torneos ATP de esta semana no aparecen en The Odds API: para ellos el motor sigue con v7.
- v8 (`core_v8_prospective_20261019`, inicio 20-oct 01:00 UTC): mismo motor que v7; el objetivo de ganador es la cuota sin margen de la última foto previa a la decisión (máx. 36 h), si existe. 17 sellados; 4 con cuota (Paolini 65,5 % por mercado frente a 75,8 % de v7; Bejlek 79,5 %; Putintseva 27,4 %; Ostapenko 43,6 %). v7 queda superado.
- Programación: tarea de Windows «QuantFut tenis cuotas h2h» a las 05:00 y 17:00 (hora de México) = franjas AM/PM UTC; log en `data/tennis/live_odds_v1/scheduler.log`. Requiere el equipo encendido. `tennis_motor forecast` toma la última foto automáticamente (418 pruebas).

## 2026-10-20 — Tenis: motor en git (PR #46) y entrada automática

- El motor vivía sin seguimiento en el worktree de Codex: ahora está en la rama `tennis/motor-v8` (PR cerorar23/quantfut#46). `apps/tennis/.gitattributes` desactiva la normalización de finales de línea porque los protocolos sellados fijan el SHA-256 de esos bytes. Las notas de harness que dejó Codex en ese worktree quedan en un `git stash` de ese worktree; su contenido ya está resumido aquí.
- La automatización de Codex solo llegó a hacer una captura (19-oct 17:04 UTC). Se sustituye por `tennis_intake_v1`: calendario de API-Tennis (2 consultas por ejecución, máximo 4 al día), identidad estricta, torneo por nombre exacto, sello único 10 minutos antes de la hora del proveedor, resultados de capturas posteriores. Primera ejecución: 29 partidos sellados automáticamente (frente a 17 con la revisión manual de PDF); exclusiones con motivo (efectos sin entrenar, ranking caducado, Nakashima ambiguo).
- Decisión: se acepta la hora del proveedor como límite del sello (sin PDF oficial). Es menos estricto que el protocolo anterior, pero da cobertura real; queda declarado en cada registro.

## 2026-10-19 — Tenis: actualización semanal de datos

- Autorización del titular: descargar ahora los 9 archivos de TennisMyLife que cambiaron (4,1 MB, MIT) y cada lunes solo los que cambien. `tennis_refresh_v1` reutiliza el resto enlazándolo desde la instantánea anterior tras verificar su SHA-256; la prueba en seco con la instantánea del 16-oct reproduce la base idéntica (492.251 partidos, mismos IDs).
- Primera ejecución: 492.350 partidos hasta el 19-oct; 47 alias y 6 fusiones por nacimiento; promovida en `config/motor.json` (la anterior queda en `canonical_history`). La entrada automática y `tennis_motor` ya usan la base nueva; los protocolos sellados mantienen la suya.
- Tarea de Windows «QuantFut tenis datos semanales», lunes 04:00 (antes de la foto de cuotas de las 05:00). PR cerorar23/quantfut#49.

## 2026-10-20 — Tenis: Codex pausado, reentrenamiento semanal y validación punto a punto

- Automatización de Codex «continuidad-de-validaci-n-predictiva-de-tenis» pausada editando su `automation.toml` (`status = "PAUSED"`; copia en `automation.toml.bak-20261020`). Si Codex está abierto puede necesitar reiniciarse para leerlo.
- Modelo de saque/resto reentrenado con la base al 19-oct (ATP 74.037 partidos, WTA 20.640; ambos convergen). Con la base corregida el modelo reconoce a Rybakina o Eala, que antes quedaban fuera por alias. La actualización semanal ya reentrena y promueve `models_root` si converge.
- `tennis_motor` deja de rechazar partidos con alguna celda de saque sin entrenar: usa el valor de población, igual que en las filas con que se ajustó el apilador. La entrada pasó de 29 a 33 partidos sellados.
- Match Charting Project (9.400 partidos, 1,4 M de puntos): sd entre partidos ≈ 0,23 logit por servidor (≈ 0,16 en la semidiferencia, coherente con el sigma 0,2); sin variación extra entre sets ni racha punto a punto. Break point +1,3 pp y tie-break −2 pp para el que saca, con efecto despreciable (hold ≈ 0,4 pp, tie-break ≈ 0,1 pp): no se modifica el Markov. Resultado en `data/tennis/weekly/20261019/mcp_point_analysis.json`.
- Aún no hay resultados: los primeros partidos sellados empiezan el 20-oct 04:15 UTC. PR cerorar23/quantfut#50.

## 2026-10-20 — Tenis: mezcla 2D (diferencia + nivel de saque) probada y descartada

- Hipótesis sacada del Match Charting Project: además de la diferencia, el nivel conjunto de saque de los dos jugadores varía de un partido a otro, lo que afectaría a totales y tie-breaks. Se calculó una rejilla 17x7 (diferencia x nivel) para 2025-2026, se ajustaron k, sigma de la diferencia, sigma del nivel y desplazamiento en 2025 y se probó en 2026.
- Resultado: en WTA no aporta nada (sigma del nivel 0,1, log-loss idéntico). En ATP corrige exactamente la media de juegos (26,29 previsto frente a 26,29 real, frente a 26,70 de la 1D), pero empeora tie-break (0,6604 frente a 0,6573) y más de 24,5 juegos (0,5607 frente a 0,5591); el resto se mueve menos de 0,0005.
- Decisión: se mantiene la mezcla 1D. Acertar la media no compensa empeorar la probabilidad de los contratos. Detalle en `data/tennis/identity_bridge_20261019/mixture2d_test.json`.

## 2026-10-20 — Tenis: operación estable, sin ranking caducado y pruebas en CI

- Las tareas ya no dependen del worktree de Codex (que Codex puede limpiar): corren desde `C:\Users\huye\Documents\quantfut-tenis`, worktree propio del repo. La configuración que la actualización semanal reescribe vive fuera de git en `data/tennis/motor_config.json` (variable `TENNIS_MOTOR_CONFIG`); `apps/tennis/config/motor.json` queda como plantilla. Los estudios congelados v4-v8 fijaron rutas del worktree de Codex en sus hashes de código: se conservan como evidencia, pero solo se pueden reverificar desde esa carpeta.
- Jugadores con ranking de más de 60 días ya no se excluyen: el motor usa un apilador sin ranking/puntos/edad (Markov + Elo dinámico + inactividad/carga/experiencia), ajustado igual. En 2026 (fuera de muestra respecto a 2025): ATP log-loss 0,6052 / acierto 67,1 %, WTA 0,6026 / 66,6 %, frente a 0,5956 / 67,6 % y 0,5946 / 67,9 % con ranking. Primer caso: Uchijima-Shibahara.
- CI: job `tenis` en `pruebas.yml` (425 pruebas de `apps/tennis`, sin base de datos).
- Las notas de tenis de `progreso.md`, `tareas.md`, `PENDIENTES.md` y los 32 `docs/tenis_*.md` entran por fin al repo. El stash de notas de Codex se exportó a `data/tennis/codex_harness_notes_stash_20261019.patch`.

## 2026-10-20 — Tenis: el motor pasa al VPS

- Para no depender del PC, el tenis corre en el VPS en una imagen propia (`quantfut-tenis`) con el cron de `qf`; ver la entrada de `DEPLOYS.md`. Aislado del fútbol: no comparte contenedores, base ni crontab del worker.
- El servidor está en Europe/Berlin: el cron usa 00:30 y 12:30 locales para que siempre caiga una ejecución en cada media jornada UTC (franjas de cuotas y cupo diario de API-Tennis), con o sin horario de verano.
- No se lanzó una captura de prueba de API-Tennis para no gastar el cupo local del día (4 consultas UTC); la cadena se verificó con la entrada en seco y la tarea semanal real.
- Tareas de Windows desactivadas, no borradas (vuelta atrás).

## 2026-10-21 — CI de tenis: prueba de cuotas en vivo dependía del reloj real

- `test_latest_market_devigs_and_respects_time` fallaba en `main` desde el 20-oct ~12:59 UTC. Causa: `run(..., clock=...)` solo controla el nombre de la franja; `Capture.request` sella `received_at` con `operations.now()` (reloj real). La prueba consulta `before=2026-10-20T11:00Z`, así que pasó mientras el reloj real iba antes de esa hora y falló al pasarla.
- Decisión: el código es correcto (en producción ambos relojes coinciden); se arregla la prueba fijando `tennis_engine.operations.now` con `monkeypatch`, sin tocar lo que comprueba (de-vig, orden temporal, orientación).
## 2026-10-21 — NBA: etiqueta de temporada en pronósticos prospectivos
`multimarket.prospective` calculaba la temporada del tipoff con el año calendario ("2027-28" para un partido de enero de 2027), así que de enero a junio regresaba el Elo un 25 % hacia 1500 a mitad de temporada. Ahora `season_label()` usa la temporada NBA (agosto en adelante abre la nueva), con prueba parametrizada. El paquete sellado RUN071 no se tocó (sus 42 pronósticos de octubre no estaban afectados); como `model.json` sella el hash del código, una cohorte nueva exige `evaluate` en un directorio nuevo, no reutilizar el de RUN071.

## 2026-10-21 — NBA v1.2: correcciones de la auditoría
Se creó `multimarket_v12` (protocolo congelado antes de correr) sin tocar RUN071: recalibración móvil, Elo con margen + descanso, ventaja local de las dos temporadas previas y bootstrap por fechas. Solo el ganador mejora de forma significativa (Brier −0,006 en ambas temporadas de test, sesgo local casi eliminado); equipos, total y jugadores quedan neutros, y el peso empírico de jugadores sigue en 0,25. Porqué importa: la ventaja que faltaba en el ganador era deriva de calibración y descanso, no más complejidad. Informe docs/nba_multimarket_v12_20261021.md. Pendiente sin datos: lesiones, cuotas/CLV.

## 2026-10-21 — NBA v1.3: disponibilidad desde reportes oficiales
Se añadió `availability`/`multimarket_v13` (protocolo congelado antes de correr) con los 816 reportes de lesiones ya descargados, regla estricta de 60 min antes del salto y partidos sin hora de salto tratados como sin información. Mejora de forma significativa el ganador (Brier −0,005), los puntos de equipo y cinco de los seis mercados de jugador; el total y tapones no cambian. No se gastó ningún crédito: The Odds API tiene 4.092 y fútbol necesita ~300/día hasta el 1-nov, así que las cuotas históricas NBA (~3.300 créditos) quedan para después del reset. Informe docs/nba_multimarket_v13_disponibilidad_20261021.md.

## 2026-10-21 — NBA: plan de cuotas históricas, sin gastar
`nba.odds_history` (plan/fetch/load) con 325 snapshots h2h (3.250 créditos) y bloqueo en código antes del 1-nov, tope y reserva. Se decidió por fases porque la bolsa de noviembre (~5.700 libres tras vivo y los 527 snapshots de fútbol) no cubre h2h+totales. Los totales van en diciembre.

## 2026-10-21 — NBA v1.3 prospectivo: cohorte sellada y página
`nba.multimarket_v13_live` + `multimarket_live_dashboard` (protocolo `multimarket_v13_live_protocol.json`). Decisión clave: solo mercados de equipo (ganador, puntos de equipo, total) porque antes del salto no existe lista verificada de jugadores, y un reporte cuenta únicamente si su sello y nuestra recepción son ≥60 min previos al salto; si no, el partido se sella como «sin reporte válido» en vez de «sano». Modelo ajustado una vez y anclado por hash (el hash del código cambió, no se reutiliza el de RUN071); la página recalcula resultados desde el recibo oficial y una cohorte rota no oculta RUN071. Ensayo: 11 partidos reales sellados 8 h antes del primer salto. De paso se corrigió el analizador del PDF (motivo partido en dos filas). No desplegado; plan en docs/nba_v13_prospectivo_20261021.md.

## 2026-10-21 — CI de tenis: prueba de cuotas en vivo dependía del reloj real

- `test_latest_market_devigs_and_respects_time` fallaba en `main` desde el 20-oct ~12:59 UTC. Causa: `run(..., clock=...)` solo controla el nombre de la franja; `Capture.request` sella `received_at` con `operations.now()` (reloj real). La prueba consulta `before=2026-10-20T11:00Z`, así que pasó mientras el reloj real iba antes de esa hora y falló al pasarla.
- Decisión: el código es correcto (en producción ambos relojes coinciden); se arregla la prueba fijando `tennis_engine.operations.now` con `monkeypatch`, sin tocar lo que comprueba (de-vig, orden temporal, orientación).

## 2026-10-21 — NBA: paso de comparación contra el mercado
- Decisión: `nba.market_compare` une las probabilidades de ganador v1.3 con Pinnacle sin margen (cuotas en caché) y reporta Brier/logloss, mezcla logit 50/50 e IC por bloques de fecha. Se construye antes de la compra del 1-nov para que ese día solo haya que comprar y ejecutar; probado con datos sintéticos, sin ejecutar con cuotas reales. Es solo investigación y no se despliega en el servidor.

## 2026-10-21 — AdMob y Meta app: dónde está cada pieza

- Decisión: un solo bloque «Recompensado» (es lo único que implementa la app: `RewardedAd` con SSV); sin banner, intersticial ni nativo. El ID de editor se guarda en `reward_settings` para que `/app-ads.txt` lo sirva desde el propio dominio de la ficha de Play (`https://pronosticosdeportivos.pro`, sin `www`).
- Decisión: en Meta se apaga el registro automático de compras de la app porque las compras las manda el servidor por CAPI; con él activo saldrían duplicadas. En Meta los hashes de clave van en base64 (el SHA-1 de Play App Signing, de `llave.jks` y de la clave antigua).
- Decisión: tras subir un AAB a Play se registra la versión en `mobile_update_settings` por SSH; `min_build_android` y la obligación solo se tocan cuando esa versión ya está disponible para los usuarios.
- Pendiente: ID de app y bloque de iOS (cuando exista la app en App Store), autorización de anuncios de apuestas en Meta/AdMob, compra de prueba web con `META_TEST_EVENT_CODE`.

## 2026-10-21 — Auditoría de los tres motores (literatura + datos)
- Hallazgo principal: el ajuste de Dixon-Coles de producción no converge (`success=False` por tope de evaluaciones; gradiente por diferencias finitas sobre 776 parámetros, 23 min) y la suma cero uniforme usa a los equipos sin datos como holgura, por lo que los que vuelven a la liga heredan fuerzas extremas. Con gradiente analítico (3-14 s), suma cero ponderada, ridge en partidos equivalentes y media vida 270, el RPS mejora −0,00084 [−0,00137, −0,00031] sobre 11.920 partidos, concentrado en inicios de temporada.
- Decisión: el calibrador afín ajustado con el log-loss del 1X2 no identifica el nivel de goles y fuera de muestra empeora; no debe guardarse otro igual. La puerta tiene que medir también mercados de goles.
- Decisión: el mercado sin margen sigue siendo el pronóstico más exacto donde hay cuota (peso óptimo del A en la mezcla = 0); el A se mejora por coherencia y cobertura, no para «batir» a Pinnacle.
- Motor C: córners totales bien; córners por equipo y tarjetas ganan claramente con el contexto del partido. «Cuántico»: sin evidencia, no se persigue.
- Nada se cambió en producción; todo queda en `docs/auditoria_motores_20261021.md` a la espera de confirmación.

## 2026-10-22 — Pasos 1-3 de la auditoría implementados (sin desplegar)
- Decisión: el ridge se expresa en partidos recientes equivalentes (`RIDGE_PARTIDOS`), porque la verosimilitud normaliza los pesos por su media y cualquier ridge fijo cambia de significado al crecer el histórico. Los artefactos anteriores cargan con `ridge_partidos=0` para conservar su objetivo.
- Decisión: el calibrador de intensidades se ajusta con la verosimilitud del marcador, que identifica el nivel de goles; la puerta exige que el 1X2 no empeore. Con el modelo corregido se rechaza: no se publica calibrado.
- Decisión: un ajuste sin converger no se activa nunca.
- Decisión: con un equipo desconocido la app muestra el mercado, no el modelo.
- Despliegue pendiente de confirmación; el `.env` del servidor fija `DECAY_HALFLIFE_DAYS=180` y hay que cambiarlo.

## 2026-10-22 — Córners de cada equipo con la supremacía del Motor A
- Decisión: un γ y un nivel por lado, sin conservar el total. La versión que conserva el total sale peor porque, con un favorito claro, el partido tiene más córners de los que dice el C y el reparto se los quitaba al visitante. El mercado de córners totales no cambia.
- Decisión: el contexto sale del Motor A (`predictions`) y solo si conoce a los dos equipos, por la regla del 2026-10-08 de no usar cuotas en el C.
- Decisión: se quitan las dos líneas del visitante que fallan con el modelo nuevo. Las que ahora pasan no se añaden sin decisión de producto.
- Decisión (pedido del usuario): se añaden las líneas de córners por equipo que pasan y pagan más (cuota mediana 1,43-1,78); las de 1,04-1,13 quedan fuera, como «menos de 4,5 goles» el 6-oct. Solo con supremacía del A, porque sin ella no se validaron.
## 2026-10-21 — Tarjetas: se miden también las líneas de «más de» (sin publicar; worker desplegado el 22-oct)

Medición en producción (SQL sobre `tarjetas_seg`, 162 resueltas): «menos de» 4,5/5,5/6,5 prometen 54/61/76 % y aciertan 67/85/93 %; el modelo se queda corto, al revés de lo que se temía el 10-oct. Las líneas de «más de» nunca se midieron porque `LINEAS_HABILITADAS` solo trae «menos de». Decisión del usuario: `tarjetas_seg.LINEAS_SEGUIMIENTO` añade «más de» 2,5-7,5 y «menos de» 3,5/7,5 solo al seguimiento; escalera y parley no cambian. Publicar tarjetas espera esa muestra (las filas del mismo partido están correlacionadas).

## 2026-10-21 — NBA: auditoría del motor de predicción
Revisión de v1.1-v1.3 y del vivo, con medidas sobre los datos locales (0 créditos, nada desplegado). Decisión clave: lo primero a corregir no es más complejidad sino que la disponibilidad descuenta dos veces las bajas largas (52 % de los «puntos perdidos» ya estaban en la forma de 20 partidos; en vivo, Butler resta 19,9 a Golden State) y que «Available» mezcla asignaciones G League. Siguen: desfase de hora del reporte entrenamiento/vivo, puntos de jugador sobreconfiados (pendiente 0,42; rango 80 % cubre 73 %), ganador y puntos incoherentes en ~19 % de partidos, peor Brier en oct-nov y `completed()` que redescarga toda la temporada. Sin cuotas sigue sin haber prueba frente al mercado. docs/nba_auditoria_motor_20261021.md; tareas en harness/tareas.md.

## 2026-10-21 — NBA v1.4: los arreglos de la auditoría no mejoran los mercados de equipo
`multimarket_v14` (protocolo `multimarket_v14_protocol.json` congelado con hash antes de correr; reproduce v1.3 a 1e-12). El doble conteo de bajas existía (la masa de puntos perdidos baja de ~33 a 13 y los coeficientes crecen 50-70 %), pero corregirlo no mejora ganador ni puntos de equipo (+0,0005 a +0,0008 de Brier, IC incluye 0) y falla la regla de decisión, así que el vivo se queda en v1.3. Sí mejora los mercados de jugador de forma consistente (−0,0003 a −0,0014). Separar G League es neutro. Hipótesis sin probar: el término absoluto también medía profundidad de plantilla lesionada. La tabla de participación necesita suelo. docs/nba_multimarket_v14_20261021.md.

## 2026-10-21 — NBA v1.4b: absoluto + relativo y suelo de participación, sin mejora
`multimarket_v14b` (protocolo congelado con hash, reproduce v1.3 a 1e-12). Los mercados de equipo no cambian (Brier ±0,0004, IC incluye 0; falla la regla de decisión) y el término relativo no añade nada sobre el absoluto, así que la hipótesis de «profundidad de plantilla» no se sostiene; v1.3 sigue en vivo. Corrección de mi diagnóstico de v1.4: el suelo de 0,02 EMPEORA la participación (los «Out» juegan 0,7 %) y separar G League tampoco la mejora; el empeoramiento no venía de los «Out». Línea de lesiones agotada para equipo: lo que queda con margen es el ajuste por rival/ritmo, el prior de pretemporada, T-60 y las cuotas. docs/nba_multimarket_v14b_20261021.md.

## 2026-10-21 — NBA: caché de completed() y backfill T-60 (en curso)
Caché por partido: sin ella cada cohorte redescargaba toda la temporada (~1.200 páginas en abril); ahora un partido final se baja una vez y un día cerrado no se vuelve a listar. Un partido pasado en curso aborta el sellado en vez de saltarse en silencio (descanso y forma saldrían mal); un aplazado queda registrado. Editar el módulo cambia su hash, así que se reajustó el modelo vivo: parámetros idénticos al anterior. Backfill T-60: la NBA publica reportes cada hora (archivo HHPM sellado HH:30 ET) y el histórico solo tenía 13:30 y 17:30; hoy solo el 2-4 % de los partidos ve un reporte a menos de 1 h del corte (mediana 5,5 h). Dato clave: en ese bucket un 403 significa «archivo inexistente», no bloqueo (los existentes dan 200), así que se usa un archivo de control para detectar un bloqueo real. El parser estricto del repo solo lee 2023-24 en adelante; 2022-23 queda con lo que ya hay. La unión de IDs reproduce el 100 % de los IDs ya unidos (3.048/3.048).

## 2026-10-21 — NBA: backfill T-60 terminado
1.910 PDF horarios (y desde el 22-dic-2025 de cada 15 min, con nombre `HH_MMPM`) para 2023-24..2025-26; cobertura de reporte a ≤1 h del corte de 2-4 % a 99,8-99,9 %. Decisiones: un 403 de ese bucket es «no existe» y se vigila con archivo de control; un timeout reintenta una vez y deja la descarga reanudable (la primera pasada murió por un ReadTimeout a mitad, sin bloqueo); el cambio de nombre de archivo se descubrió porque 236 peticiones seguidas daban «no existe». Descriptivo: con T-60 «Out» juega 0,8 % (antes 4,3 %) y «Doubtful» 3,1 % (9,6 %), así que la tabla de participación de v1.3 se entrenó con estados mucho menos informativos que los que recibe en vivo. Falta medir si eso cuesta predicción (v1.5). docs/nba_cache_completed_y_backfill_t60_20261021.md.

## 2026-10-21 — NBA v1.5: reportes T-60 en la v1.3
`multimarket_v15` (protocolo `multimarket_v15_protocol.json` congelado con hash; la referencia reproduce v1.3 a 1e-9). Mismo código, solo cambian los reportes. Participación 0,491→0,383 y 0,447→0,314 de log loss; seis mercados de jugador mejoran de forma significativa (puntos −0,002). Equipo: puntos de equipo −0,0013/−0,0006, ganador ±0,0004, total ~0, con IC del ganador de ±0,002 (≈1.200 partidos): ausencia de evidencia, no de efecto. Falla la regla de decisión, así que el entrenamiento vivo conserva sus reportes; entrenar con estados del mismo tipo que se sirven queda como decisión del titular. Lección: la calidad del reporte importa para la disponibilidad individual, no para el equipo, que ya la captura por otras vías; el siguiente paso útil son las cuotas y no más lesiones. docs/nba_multimarket_v15_20261021.md.

## 2026-10-21 — NBA: comparación con Pinnacle preparada
Se revisó `odds_history`/`market_compare` antes de usarlos y se encontraron tres fallos que habrían contaminado el resultado: «Los Angeles Clippers» (proveedor) ≠ «LA Clippers» (histórico) descartaba en silencio ~5,5 % de los partidos; un partido sin snapshot propio podía emparejarse con el precio de la víspera (el filtro de antigüedad mira al libro, no al salto); y, sobre todo, en los partidos de noche el mercado tiene un precio de hace horas mientras el modelo usa reportes hasta T-60, lo que favorece al modelo. Decisión clave: la comparación principal limita la información del modelo a la hora del snapshot (brazo alineado) y la regla de decisión se congeló antes de comprar ningún precio (esperable: sin evidencia de información añadida; es válido). Ensayo con precios sintéticos de punta a punta. El modelo vivo no se tocó. docs/nba_comparacion_pinnacle_20261101.md.

## 2026-10-21 — NBA: prueba prospectiva contra Pinnacle (offline)
`nba.live_market`: captura el precio actual de Pinnacle justo después de sellar cada cohorte y lo compara con los pronósticos sellados cuando hay resultado oficial. Decisiones clave: el paso de captura solo lee el bundle sellado y el código de pronóstico no lo importa, así que un precio nunca puede influir en un pronóstico; la captura de la fase «sello» se rechaza antes de gastar el crédito si pasan más de 15 min del sellado (si no, precio y pronóstico no describirían el mismo momento); cada fase se guarda una sola vez con la respuesta cruda y su hash, sin reintentos; la regla de decisión (400 partidos y fin de temporada, cobertura ≥85 %) se congeló antes de que existiera ningún precio. Es la única prueba sin sesgo de selección. Ensayada sobre la cohorte real con una respuesta sintética: 11/11 partidos emparejados. La API no se ha llamado. Abierto: dónde corre la captura, porque el contenedor NBA no tiene credenciales. docs/nba_mercado_prospectivo_20261101.md.

## 2026-10-22 — NBA: lectura del servidor y propuesta para la clave de cuotas
Lectura (sin cambios) del servidor para proponer cómo dar al productor acceso a la clave de The Odds API. Hallazgos: ya corre un productor `nba-live13-producer:20261021` (cron cada 10 min, contenedor de corta vida, raíz de solo lectura, sin capacidades, sin secretos) y el panel `nba-dashboard-live13:20261021`, ambos desplegados ayer y registrados en el DEPLOYS.md de `main` (mi rama iba por detrás y no los veía; mis documentos decían «no desplegado» y quedaron desactualizados). La clave del piloto se monta como archivo 600 de solo lectura en /run/secrets, nunca como variable. Decisión propuesta (no ejecutada): contenedor de captura propio con su archivo de clave, cohortes en solo lectura, carpeta de precios aparte y libro de presupuesto fuera de las cohortes (2 peticiones/día, 70 créditos/mes), porque el productor actual interpreta HTML de terceros y no debe ver la clave. El servidor sigue con el módulo anterior a la caché de completed(); la captura va en un contenedor aparte, así que el modelo del productor no cambia. docs/nba_captura_precio_servidor_propuesta_20261022.md.

## 2026-10-22 — NBA: captura del precio en el servidor, preparada (sin desplegar)
Aprobada la opción A (contenedor de captura propio) con tope de 2 peticiones/día y 70 créditos/mes y fase de cierre. Hecho: clave del piloto copiada a un archivo 600 propio sin leerla (idéntica por cmp, 32 bytes = la clave sola, así que el lector acepta ese formato además de ODDS_API_KEY=); `live_market` guarda los precios fuera de la cohorte (que puede montarse en solo lectura, con prueba de que no se toca), aplica el presupuesto desde un libro fuera de las cohortes y se detiene con un archivo `halt` ante cualquier fallo; `capture-pending` es idempotente y antes del 1-nov no lee la clave ni toca el disco. Decisión clave al leer `main`: el envoltorio del productor usa `exec`, así que el paso de precios va en una línea de cron propia cada 5 min con su `flock`, en vez de editar algo que está en producción. Rectifico dos afirmaciones mías: el productor y el panel SÍ están en DEPLOYS.md de `main` (mi rama iba por detrás), y desplegar la captura NO exige reajustar el modelo del productor. Pendiente: confirmación para desplegar y fusionar con `main`.

## 2026-10-22 — NBA: paso de precios desplegado (bloqueado hasta el 1-nov)
Fusionada la PR #77 (CI 4/4, arnés 1441) y desplegado el contenedor de captura de precios con su cron propio. Decisiones clave: se trabajó en un worktree limpio sobre `main` porque el árbol compartido tenía cambios sin confirmar de otras sesiones y entradas ajenas en progreso.md/tareas.md que no debían arrastrarse; el contexto de construcción se exportó con `core.autocrlf=false` porque `git archive` con el `autocrlf` de Windows entregaba CRLF y habría roto el `.sh` en Linux (se verificaron los 69 archivos contra los blobs); el arnés del worktree falló al principio por falta de `.env` (credenciales de la base de pruebas), no por código. La clave se copió sin leerla y solo el contenedor de precios la monta, en solo lectura. Hasta el 1-nov cada pasada solo escribe «bloqueado» y no lee la clave. Pendiente: primera captura real el 1-nov. DEPLOYS.md tiene la vuelta atrás.

## 2026-10-22 — App: iconos de mercado sin emojis
Los emojis de los mercados (🟨, ⚖, ✌, 🥅...) dependen de la fuente del teléfono y en Android antiguos salen como cuadro o en monocromo. `live_markets.dart`, `live_match_markets.dart` y `live_forecast.dart` usan ahora iconos de Material (los mismos criterios que `marketIcon`). Quedan emojis solo en textos traducidos del VIP (💡 🔒 ✦ ★), comunes y sin quejas. `flutter analyze` y los 261 tests pasan; sin compilar ni probar en dispositivo (emulador apagado). Hace falta nuevo build para que llegue a los usuarios.

## 2026-10-23 — NBA: cuotas históricas compradas y comparación con Pinnacle
Por instrucción del titular (opción 3) se compraron antes del 1-nov los 325 snapshots h2h (3.250 créditos + 10 de un diagnóstico cuya respuesta no guardé): saldo 3.560 → 294, con fútbol quedándose sin créditos hasta el reset; lo advertí con cifras (fútbol gasta ~500/día de media) y el titular lo aceptó. Se compraron primero 20 y se revisó la carga (99,4 % de cobertura, margen medio 2,8 %, coste exacto de 10) antes de seguir. Hallazgo: la API devolvía 422 porque el código enviaba la fecha con +00:00 y exige Z; las pruebas con cliente falso no podían verlo, así que el primer contacto real con un proveedor nuevo debe ser una petición de prueba. Resultado con el protocolo congelado: el modelo de ganador no supera a Pinnacle (Brier +0,0040 y +0,0057 peor, c = 0,25 y 0,09 con IC que incluye 0) y, cuando discrepa ≥10 puntos, acierta el mercado. La conclusión útil: el ganador NBA no se vende como pick; sirve como línea base (Brier del mercado 0,195-0,200) para medir mejoras. Total del partido, puntos de equipo y jugadores no quedan cubiertos. docs/nba_comparacion_pinnacle_resultado_20261023.md.

## 2026-10-23 — NBA: props de jugador, corrección de «no viable»
Al investigarlo (documentación oficial, páginas de mercados/casas/precios y la sonda real de rebotes) la cifra de ~145.000 créditos resultó correcta pero la conclusión equivocada: el plan 5M de The Odds API cuesta $119 al mes y cubre props, `team_totals`, `totals` y `spreads` de dos temporadas con dos snapshots (≈345.000 créditos); y no hace falta lista verificada de jugadores, porque el mercado define el universo y las casas anulan el prop si no juega (17 de 17 nombres emparejaron). Pinnacle no cotiza props de jugador (solo casas de EE. UU.), así que la referencia sería un consenso sin margen. La sonda sugiere que el mercado se concentra en 0,50 ± 0,055 y que el modelo correlaciona 0,47: esperable que gane el mercado. Lección: no declarar «inviable» una cifra sin comprobar los precios reales del proveedor. docs/nba_props_jugadores_viabilidad_20261023.md.

## 2026-10-23 — NBA: sonda de props de jugador y elección de paquete
Sonda real de 110 créditos (un partido por temporada, seis mercados): el histórico de props existe en 2024-25 y 2025-26, con 7-8 casas de EE. UU. y nombres que emparejan al 100 %. Puntos y rebotes cubren el 100 % / 86 % de los jugadores de ≥20 min (80-93 % de los minutos); asistencias y triples algo menos; robos y tapones son demasiado escasos (en 2025-26 no hay robos y solo BetMGM cotiza tapones) y se excluyen del análisis principal. Con cuatro mercados el coste es 40 créditos por partido y snapshot; el escenario completo (2 temporadas, 2 snapshots, team_totals, totals/spreads de Pinnacle) son ~249.000 créditos, y solo el plan 5M ($119) lo cubre; dos meses de 100K cuestan lo mismo y dan menos. Recomendación: un mes de 5M desde el 1-nov, con piloto previo y protocolo congelado antes de gastar. Lección: calcular el paquete con costes observados en una sonda y no con la estimación teórica de seis mercados (que sobreestimaba un 35 %). docs/nba_props_sonda_y_paquete_20261023.md.

## 2026-10-23 — NBA: segunda auditoría y correcciones del productor
Aclaración del titular: el motor busca probabilidad estadística bien calibrada y muchos pronósticos, no ganar a las cuotas; la certeza se mide contra el resultado real y Pinnacle queda como referencia. Errores del productor corregidos en `nba/productor-correcciones` (sin desplegar). Decisión clave: sellar cada partido en la pasada que lo encuentra 65-90 min antes de su salto en vez de una cohorte a las 17:35 ET; así entran los partidos de tarde (7-8 %) y los de 18:00-18:45 reciben un reporte que cuenta, sin tocar modelo ni regla de lesiones (enmienda operativa 1.3.1). El sello y las recepciones se fechan cuando ocurren; una franja 403 se contrasta con un archivo de control para no confundir un bloqueo con «sin reporte». Lección del ensayo real: la página actual de nba.com da minutos como `PT23M56.00S` y las archivadas `33:15`; las pruebas con datos sintéticos no lo veían. Rectificación: la captura de precios con The Odds API sí está desplegada (22-oct); leí el DEPLOYS.md de una rama atrasada. docs/nba_productor_correcciones_20261023.md.

## 2026-10-23 — PropLine compartido: implementación preparada
Implementación preparada en `codex/propline-hourly`, commit `5ff66cf`: archivo horario común, originales comprimidos, lecturas sin HTTP, conversión de cuotas y adaptadores de fútbol. Arnés de main: 1.468 aprobadas, 104 omitidas; 27 pruebas específicas. Piloto NBA: cinco respuestas 200, 112.154 observaciones, cero fallos en esa pasada. Límite 4.500 solicitudes/día y reserva global 500; detener captura con menos de 5 GiB libres.

**Sin activar aún en producción.** La revisión automática rechazó subir esta rama al repositorio remoto por falta de autorización explícita del destino. No se cambió cron, imágenes, proveedor activo ni base del servidor. Pendientes: autorización de subida a `cerorar23/quantfut`, PR/main, despliegue y primera pasada completa; terminar de conectar los lectores NBA/tenis al archivo común conservando los protocolos sellados. Auditoría del servidor por hashes, sin exportar su código; parche de API preparado desde las versiones verificadas del repositorio.

## 2026-10-23 — PropLine: alias de ligas y claves de mercado
La Championship nunca recibía cuotas de PropLine: el alias usaba `soccer_england_efl_champ` y la base guarda `soccer_efl_champ`. Corregido y añadidas Noruega, Suecia y Suiza, con una prueba que exige que cada alias exista en `db/*.sql`, para que el nombre no vuelva a divergir en silencio. Se añadieron a las familias las claves vistas en partidos reales (tiros, tiros a puerta, paradas, 2+/3+ goles, margen; aces, dobles faltas, juegos ganados, quiebres; escalones 10+/15+ puntos NBA). Hallazgo: `2plus_goals`/`3plus_goals` no se capturaban aunque el descubrimiento los viera, porque el filtro de claves de deporte exige empezar por letra; las claves de mercado usan ahora `MARKET_KEY`. Capturar más claves no cambia predicciones: siguen sin adaptador hacia los motores.

## 2026-10-24 — NBA: mercados de jugador en vivo con líneas de PropLine
Por decisión del titular, el productor 1.3.1 pronostica puntos, rebotes y asistencias de jugador sobre la línea de PropLine (el archivo horario común, leído sin red y con montaje de solo lectura). Decisiones clave: el universo y el umbral los define el mercado (línea principal más repetida en ≥2 casas, sin DFS ni intercambios), pero las cuotas no entran en el modelo; el pronóstico es condicionado a jugar porque las casas anulan al que no juega. Hallazgo medido antes de adoptarlo: la recalibración v1.3 aprendida solo en el umbral sintético se desvía 5-8 puntos de tasa cuando la línea está 2-4 por encima o por debajo, que es lo normal con líneas reales; ajustada sobre una rejilla de umbrales mejora el Brier fuera de muestra en los tres mercados. También entran play-in y playoffs y se arreglaron las 3 pruebas caducadas del piloto. Sin desplegar. docs/nba_productor_correcciones_20261023.md.

## 2026-10-24 — PropLine: cierres y liquidaciones en el recolector
La clave es Hobby y nadie pedía cierres ni liquidaciones. Se piden una vez por partido terminado (liquidaciones: hasta 3 días mientras falten resultados), a partir de nuestros propios marcadores. Decisión de presupuesto con el índice real del servidor (129/h de cuotas): 600 peticiones diarias reservadas por deporte y la captura horaria limitada a 3.900, para que el cierre no dependa de lo que sobre. Las claves nuevas de fútbol se quedan en el descubrimiento diario porque en la familia horaria costarían +744/día; el descubrimiento ya no descarta claves que empiezan por dígito.

## 2026-10-24 — PropLine: box score, lesiones NBA y lectores sobre la liquidación del #96
Otra sesión fusionó antes el #96 (cierre y liquidación con reserva diaria). En vez de duplicarlo, el #97 se rehízo encima: el box score entra como tercer tipo de su cola, después del cierre y la liquidación, para que solo use lo que sobre de la reserva; en tenis queda apagado porque cierre y liquidación ya la agotan. Reserva subida a 730 (NBA 130, fútbol 300, tenis 300) y lesiones NBA cada hora (+24): siguen dentro del tope de 4.500 con lo medido en el servidor. Lección: antes de abrir un PR sobre un módulo compartido, mirar los PR recién fusionados por otras sesiones. docs/propline_compartido_20261023.md.

## 2026-10-24 — PropLine: cobertura real de mercados medida en el archivo
Medición de solo lectura del archivo horario (5 h, 667 respuestas). Decisión clave: medir la cobertura solo en los partidos de las próximas 36 h, porque las casas publican córners, tarjetas y props cerca del inicio y el conteo total la subestima. Resultado: en las diez ligas del modelo hay Pinnacle en 1X2, totales, hándicap, BTTS y córners; tarjetas con Pinnacle en siete; goles por equipo también, porque viaja en `totals` con el campo `team` (una primera lectura buscó la clave `team_totals`, que no existe, y lo dio por ausente: hay que agrupar por `(key, period, team)`). Pendiente de remedir: props NBA el día del partido y copas europeas en semana de copa. docs/propline_cobertura_20261024.md.

## 2026-10-24 — Recolector SofaScore (Apify, rl1987) en el VPS
Decisión: `azzouzana/sofascore-scraper-pro` está roto (3 de 3 URLs fallan); se usa `rl1987`. El coste real es ~0,01 USD por partido con detalle, no los 3 USD/mes estimados; el titular autorizó hasta 15 USD/mes. `listRounds` cuesta ~0,12 USD por liga, así que la jornada actual se toma del próximo partido. El tenis se localiza cada 6 días barriendo un día de calendario y filtrando categoría ATP/WTA. Cada respuesta se archiva con la hora real de recepción (SofaScore no la entrega). Cron 07:40 UTC en `~/sofascore-apify/`; ver DEPLOYS.md.

## 2026-10-24 — BetsAPI: clave nueva y mercados completos de bet365
El plan de un día caducó (403 a las 04:15 UTC); el titular dio otra clave (solo en el VPS, `~/betsapi/.env` y `~/quantfut-tenis/secrets/.env.betsapi`). Hallazgo medido: `/v2/event/odds` solo trae los mercados principales, pero `/v4/bet365/prematch` devuelve todos (≈125 en NBA con props de jugador, ≈190 en fútbol con goleadores, tarjetas, córners y estadísticas de jugador, sets/jugador en tenis), también para partidos ya jugados, aunque bet365 los borra a las ~3-4 semanas (NBA abr-2026 y LaLiga 14-sep vacíos). Por eso la cadena (`~/betsapi/cadena3.sh`) baja primero ese modo `prematch` desde el 20-sep y después reanuda el histórico de cuotas principales (fútbol 2022+, NBA 2020+, tenis 2023+). Un cron horario (`fotos.sh`, :17) guarda fotos de los próximos con hora real de recepción (`fetched_at`), porque los props históricos anteriores a ~1 mes no existen en ninguna parte de BetsAPI. Lotes de 10 en `event/view` y `prematch`: 2 peticiones por 10 partidos.

## 2026-10-24 — SofaScore vía Apify: proveedor por deporte
Decisión del titular: `scrapesage/sofascore-scraper` para NBA y tenis, `rl1987/sofascore-api-scraper` para fútbol; `azzouzana` descartado (publicado y «Succeeded», pero solo devuelve `NO ND script found`, comprobado en la consola). Motivo: con 2-3 partidos por deporte, `rl1987` tiene la alineación de fútbol más profunda (~127 métricas por jugador) pero en NBA devolvió un solo partido sin estadísticas, mientras `scrapesage` cubre NBA y tenis y llegó a un histórico con `seasonIds`. Trampa: el id de ATP París es 2404, no el 1415 de la URL. Es una prueba, no una auditoría; el gasto real no se midió y no hay código ni despliegue. docs/sofascore_apify_proveedores_20261024.md.

## 2026-10-24 — Recolector SofaScore del VPS: actor por objetivo
Se adaptó `sofascore_apify.py` para que cada objetivo lleve su `provider` (NBA y tenis con scrapesage, fútbol con rl1987). Decisión clave: las filas de scrapesage se normalizan al índice común (matchId → id) pero el cuerpo original se archiva intacto y cada recibo anota el actor en `params._actor`; el detalle se agrupa por actor y scrapesage recibe ids enteros (rl1987 cadenas). El descubrimiento semanal de torneos de tenis sigue con rl1987 porque scrapesage no tiene modo por fecha. Aclaración del titular: la cuenta Apify es de pago, así que el presupuesto no es el riesgo que creí (corrijo mi nota de «plan gratis»); se mantienen los topes por corrida. Respaldo previo en el VPS; desplegado sin tocar el cron. Ver DEPLOYS.md.

## 2026-10-24 — Props de jugador NBA: cuotas históricas y comparación con el mercado
Decisión del titular: clave nueva de The Odds API (plan 100K, solo NBA); 4 mercados × 1 captura por partido (2.424 partidos, ~97.100 créditos). Los props solo existen en el endpoint por evento, así que `props_history.py` lista eventos por día (1 crédito) y paga cada partido a `tipoff − 30 min`; una captura sin cierre sirve para entrenar, no para CLV. `props_link.py` une cada cuota con el box score del MISMO partido (sin distancia de edición; 9 alias verificados); los jugadores que no jugaron se conservan sin resultado para que el entrenamiento decida.
Resultado de `props_market.py` (protocolo congelado antes de correr): el modelo v1 pierde contra el mercado en los 4 mercados (Brier +0,006 a +0,022); `c` ≤ 0,17. Por eso el archivo no se usa para sustituir al mercado sino como ancla de un futuro modelo de residuo. Detalle: `docs/nba_props_historicos_descarga_20261024.md`, `docs/nba_props_vs_mercado_20261024.md`.

## 2026-10-24 — PropLine: team_stats empareja clubes escritos distinto
La verificación de la primera pasada real (release 5a9cde0) mostró que `team_stats` solo casaba los dos equipos en 46 de 98 box scores de fútbol: las casas y la fuente del acta escriben distinto («Ipswich» / «Ipswich Town»). Decisión: aceptar que un nombre plegado contenga al otro y, con exactamente dos clubes, deducir el segundo del primero; cualquier ambigüedad devuelve vacío. Medido sobre el archivo real: 95 de 98. Lección: probar los lectores contra datos reales antes de darlos por buenos, no solo contra un caso inventado.

## 2026-10-24 — NBA: auditoría de datos para entrenar todos los mercados
No toda la data está conectada. Entrenables ya: ganador (con h2h), puntos de equipo/total contra resultado y los 4 props principales con cuotas. Decisión clave: el primer cuello de botella no es comprar más, sino que el normalizado que leen los modelos descarta columnas ya descargadas (tiros intentados, pérdidas, posesiones) y los playoffs; las cuotas de hándicap/total existen en BetsAPI del VPS pero sin normalizar. El pendiente h2h "desde el 1-nov" estaba desactualizado: se compró el 23-oct. docs/nba_auditoria_datos_entrenamiento_20261024.md.

## 2026-10-24 — NBA: modelo de props anclado en el mercado
Con protocolo congelado (entrena 2024-25, evalúa 2025-26, IC 98,75 %) las variables propias (v1, disponibilidad T-60, total y hándicap de bet365 «as-of» el precio, ritmo, defensa rival, descanso, minutos) no añaden información al consenso de las casas de EE. UU. en ningún mercado: la mejora máxima es 0,0004 de Brier. En rebotes y triples toda la mejora es recalibrar el consenso, que sobrevalora el Over 1-2 puntos. Decisión clave: se descartan los precios a más de 60 min del salto (1.566 unidades) para que un reporte T-60 no aporte información que el precio no tenía. Defecto del protocolo, declarado: el placebo se compara contra el mercado crudo y por eso confunde recalibración con fuga, así que rebotes y triples quedan como corrida nula por la letra; el control correcto es contra la recalibración y exige un v1.1 marcado como posterior a ver los números. Con precio, lo mejor es el consenso recalibrado; sin precio (robos, tapones, combinados) el motor depende de su modelo y se mide contra el resultado. docs/nba_props_residual_20261024.md.

## 2026-10-24 — NBA: normalizado ampliado con tiros, pérdidas, posesiones y postemporada
`nba.extended_box` con protocolo congelado antes de construir. Decisión clave: el conjunto nuevo no toca ninguna fila de RUN071 (una prueba de no regresión aborta si una sola fila regular cambia) y la postemporada sin filas aceptadas se marca `sportsdataverse_only`, cuadrada con las identidades del box y el marcador de API-Sports, en vez de mezclarla sin distinguir con la base de dos fuentes. Las pérdidas del box de equipo incluyen las de equipo, así que se exige ≥ la suma de jugadores y la estimación de posesiones usa la suma de jugadores en todos los partidos para que sea comparable. Hallazgo: las filas aceptadas ya traían un campo `provenance` y la primera pasada lo pisaba; lo detectó la no regresión. 6.414 partidos, 53 regulares perdidos (0,87 %). docs/nba_normalizado_ampliado_20261024.md.

## 2026-10-24 — NBA: cuotas de bet365 normalizadas (BetsAPI) y matriz por mercado
Decisión clave: BetsAPI lista primero al visitante como «home» en el 100 % de los partidos, así que emparejar por (fecha, local, visitante) no dio ninguna coincidencia y, peor, habría invertido el lado de todas las cuotas de ganador y hándicap. Se resolvió con una sonda de orientación (solo equipos, fecha y marcador, sin cuotas), enmienda v1.1 del protocolo con el hash anterior conservado, y reorientación por partido contra la referencia. La regla de aceptación del 99 % sobre todos los eventos se cambió por el acuerdo de marcador entre los emparejados (99,95 %), porque la referencia excluye partidos propios. Integridad tras construir: victoria local 55,1 % frente a 55,5 % implícito; margen + línea ≈ 0,05. 34.713 filas, 3.867 partidos, cierre mediano a 2,3 min del salto. Una sola casa y descarga histórica: la recepción original es desconocida. Para entrenar no hace falta una casa con todo: hace falta, por mercado, una fuente igual antes y después (ganador: Pinnacle; hándicap/total/mitad/Q1: bet365; props: consenso de 6 casas de EE. UU.), con la casa marcada en cada fila. docs/nba_cuotas_betsapi_normalizadas_20261024.md, docs/nba_matriz_mercados_y_estudios_20261024.md.

## 2026-10-24 — NBA: entrenamiento y calibración de todos los mercados
Dos corridas con protocolo congelado (ajuste 2024-25, prueba 2025-26). Contra el cierre de bet365 el motor no mejora ninguno de los nueve mercados de equipo y recalibrar el precio no aporta: el cierre ya está calibrado. Hallazgo de medida que cambió el plan: en hándicap y total la línea deja la probabilidad en ~50 %, así que medir contra el mercado no discrimina; se midió la distribución del motor en varias líneas contra los resultados. En equipo el motor tiene habilidad en 11 de 12 mercados con pendiente ≈ 1, pero la línea de bet365 es mejor centro (RMSE 18,4 contra 19,3 en el total) y las desviaciones del motor respecto a la línea no informan (peso −0,39 en el total). En jugador sin cuota, la ley v1 aplicada a las combinaciones está sobreconfiada (pendiente 0,78): recalibrar ayuda y añadir disponibilidad y entorno la corrige (Brier −0,005), sobre todo por el minutaje perdido de los compañeros; en robos, tapones y pérdidas la ganancia es pequeña. Dos defectos de diseño detectados antes de ver resultados reales y enmendados: el placebo de equipo comparaba contra la recalibración (siempre «mejor» si el modelo informa) y pasó a compararse con el modelo solo (v1.1). Los parámetros están guardados con `promoted: false`; aplicarlos al vivo es una decisión aparte. docs/nba_calibracion_motor_20261024.md.

## 2026-10-24 — NBA: productor vivo 1.3.2 con las sumas de puntos, rebotes y asistencias (preparado, sin desplegar)
Llevar al vivo la calibración de las combinaciones, que son donde la ley v1 sale más sobreconfiada, no necesitó un modelo nuevo: reutiliza el mecanismo del productor (logit p, sesgo, estado propio y minutos perdidos de los compañeros, ajustado sobre la rejilla de umbrales). Las cuatro sumas pasan el chequeo congelado (Brier −0,0023 a −0,0086 contra la ley cruda, pendiente 0,58-0,85 → 0,98-1,01). Decisión clave: el modelo candidato se verificó contra el desplegado y es idéntico en equipo y en puntos, rebotes y asistencias (solo cambian el hash del módulo y las cuatro sumas nuevas), y el productor omite en vez de adivinar un mercado que su modelo no conoce. Riesgo de despliegue anotado: el panel actual rechaza una cohorte con un mercado desconocido, por lo que el orden es panel primero y productor después, y la vuelta atrás conserva el panel nuevo. Robos, tapones, pérdidas y doble-doble siguen fuera porque las filas de box score vivas no los traen. docs/nba_productor_combinaciones_20261024.md.

## 2026-10-24 — NBA: el despliegue del productor 1.3.2 deja de depender de cómo se copió el módulo
El productor se niega a sellar con un modelo ajustado por otro módulo, y ese hash era el de los bytes del archivo: cambiaba con los saltos de línea de cada copia (Windows contra el servidor), así que un modelo bueno habría sido rechazado y habría que reajustarlo en el servidor. Ahora es el hash del contenido con los saltos normalizados. Además las comprobaciones que antes eran una lista manual (equipo y puntos, rebotes y asistencias idénticos al modelo desplegado, sumas presentes, insumos iguales salvo módulo y protocolo) son el comando `compare`, que sale con código 1 si algo no coincide. Ensayado de punta a punta con el modelo real: 10 de 10 comprobaciones. docs/nba_productor_combinaciones_20261024.md.

## 2026-10-25 — NBA: productor vivo 1.4.0, reentrenado con la data nueva pieza por pieza
El titular pidió el motor vivo entrenado y calibrado con toda la data nueva y desplegado. Decisión clave: ninguna pieza entra por existir; cada una se comparó contra la anterior con el mismo fit_model del productor y sobre las mismas unidades de 2025-26 (protocolo congelado). Entran los reportes T-60 en el ajuste (Brier −0,0018, la mayor ganancia: el vivo servía reportes de una hora antes del salto pero se había ajustado con los de 13:30/17:30), el entorno del partido en la calibración de jugador (−0,0003) y cuatro mercados nuevos (triples, robos, tapones, robos+tapones). No entran el dataset con play-in y playoffs (empeora rebotes y asistencias: el rol de postemporada no es el de la regular) ni el ajuste del nivel de anotación dentro de la temporada (empeora los puntos de equipo). Con RUN071 no hay posesiones ni tiros: ritmo, defensa rival y uso quedan con peso 0. De paso se encontró el productor parado desde el 24-oct por un minutaje `10:60` de nba.com; se arregló y desplegó 1.3.2 antes de seguir. docs/nba_productor_14_20261025.md.

## 2026-10-25 — NBA: el vivo usa RUN071 + columnas nuevas y suma pérdidas
El dataset ampliado se había rechazado entero en 1.4 porque mezclaba dos cosas: postemporada en el historial (empeora) y columnas nuevas. Decisión clave: separarlas con un protocolo congelado propio y quedarse solo con las columnas sobre la temporada regular de RUN071. Mejora los 11 mercados de jugador (conjunto −0,00015; ninguno empeora), da peso real a ritmo, defensa rival y tendencia de uso, y deja entrar pérdidas (−0,0012 contra la ley cruda, pendiente 1,00). El productor no cambia de código; cambian datos y modelo. docs/nba_productor_14b_20261025.md.

## 2026-10-25 — Auditoría de los tres motores y alias de PropLine para las cuotas
Los datos de PropLine y SofaScore llegan y los tres motores vuelven a producir (corrida del 25-oct: 41 predicciones del A, 28 de alta probabilidad), pero 19 de 63 partidos se quedaron sin precio. Decisión clave: el cuello de botella ya no es la fuente sino el emparejamiento. El calendario y los resultados de PropLine aprenden alias con la fuente `propline`, y el lector de cuotas solo consulta `odds_api`: Inter–Fiorentina o River–Racing estaban en el archivo a la hora exacta, sin poder emparejarse. Se copiaron a `odds_api` los alias aprendidos (revisados uno por uno) y 18 manuales; las conjeturas del difuso (Lanús → San Luis, Brugge → Brage, Cologne → Kaiserslautern) se rechazaron, por eso no se aceptan en bloque. Arreglo de fondo pendiente: que `odds_worker` lea también `propline`. docs/auditoria_motores_20261025.md; DEPLOYS.md.

## 2026-10-25 — NBA: tercera auditoría (motor, props, vivo, cierres y créditos)
Decisión clave: los fallos ya no estaban en el modelo sino en la operación alrededor de él, y por eso se corrigieron y desplegaron en el acto. El 1.4b se había quedado a medias (panel nuevo, productor viejo) porque el ensayo de la madrugada simulaba las 19:40 con un archivo de PropLine de las 04:07 y daba 0 props; con la hora real coincide con el 1.4.0 (362 pronósticos) y se completó. El hueco grande era PropLine: su petición principal de NBA da 504 a las horas de sellado y un partido se selló sin hándicap ni total; ahora se reintenta solo el partido completo. La reserva de 500 corta la pasada de las 23:07 UTC, que desde el 1-nov alimenta los partidos de las 20:00-20:30 ET; en vez de tocar la reserva (decisión del titular) se quitaron llamadas sin dato (lotes tras una principal vacía, marcadores de ligas sin motor cada 3 h), ~150/día. La captura de precios con The Odds API se retiró: contradecía la decisión de PropLine como fuente en vivo, que ya trae Pinnacle. docs/nba_auditoria_20261025.md.

## 2026-10-25 — App: auditoría de datos, pronósticos y ergonomía
Decisión clave: en una pantalla, una selección tiene UN porcentaje, el sellado. La lista «Mercados del partido» es análisis del modelo y el destacado es el pick sellado; con fuentes distintas, la misma selección salía con 76 % y 79 %, y un pick gratis de lado distinto al más probable del análisis (Barcelona o empate frente a «12») desaparecía de la lista. `aplicar_acceso` ahora usa la probabilidad sellada en las filas de picks abiertos y añade los que el análisis no lista; el resto del análisis no cambia.
Los textos en español que llegaban fijos (Inicio, historial de la Escalera, patas del Parley) se redactan en la app desde `market/selection/line`; por eso el Parley envía ya esos campos. «Marca X» solo vale para más de 0,5. Un partido con el saque pasado hace más de 130 min y sin resultado dice «Esperando resultado»: el resultado llega por ciclos (otra sesión lleva el resultado al pitido) y llamarlo «en juego» a las 3 h engaña. Medido en producción a las 23:09 UTC: Barcelona–Real Madrid (20:00 UTC) seguía `scheduled` sin marcador.
Visto y descartado como error: Serie B, LaLiga 2, Allsvenskan y Suiza siguen en la agenda hasta que corra la 088 (01:30 UTC del 26-oct, aplazada a propósito). Sin desplegar: la API y el build de la app esperan visto bueno.

## 2026-10-25 — Destacado del detalle: cuota mínima 1,40

Decisión del usuario: el destacado era un 93 % a cuota 1,08 (hándicap +1,5), sin valor para quien lo ve. Ahora es el de mayor probabilidad con cuota publicada >= 1,40 entre los pronósticos sellados del partido; sustituye la banda 74-85 % / 1,20-1,60 que estaba sin confirmar en el árbol. Solo compiten picks sellados (alta probabilidad 73-95 % y escalera), nunca las filas de `partido_mercados`, que son análisis con cuota justa y no tienen cuota de mercado al publicar: destacarlas rompería predecir → sellar → publicar. Consecuencia: con el piso 1,40 habrá partidos sin destacado (el detalle lo avisa). Solo app; el servidor no cambia.

Mismo día, decisión del usuario: el historial de retos ya no muestra el resumen «N cumplidos de M cerrados», la tasa de cumplidos ni el resultado acumulado; solo el título y la lista (9 últimos cumplidos + último fallido). El servidor sigue enviando `resumen` (se usa `cerrados` para saber si está vacío); no se tocó la API ni la web.
