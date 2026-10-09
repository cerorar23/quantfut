# NBA: rotaciones e intradía médico — 6 de octubre de 2026

**6.147/6.150 rotaciones regulares validadas; quedan tres. Se añadieron 815 reportes médicos: 1.631 versiones y 165.729 filas en total.** Los boxscores del censo 2021–22 a 2025–26 siguen completos: 6.150 regulares y 71 pretemporadas 2025–26. Las 164.218 filas conservadas incluyen también los 85 playoffs, seis play-in y una final Cup adquiridos anteriormente; no acreditan cobertura completa de esas categorías ni de toda la historia NBA.

| Datos | NBA-RUN-040 | NBA-RUN-041 |
|---|---:|---:|
| Rotaciones regulares aceptadas | 6.141 | 6.147 |
| Tramos cronológicos por equipo | 259.416 | 259.687 |
| Rotaciones pendientes | 9 | 3 |
| Versiones de reporte médico | 816 | 1.631 |
| Filas médicas | 80.932 | 165.729 |
| Pares de precios de props | 3.756 | 3.756 |

## Rotaciones y tres conflictos abiertos

Se recuperaron 0022100151, 0022100353, 0022201007, 0022201040, 0022201205 y 0022400831. Cuatro casos requieren titulares silenciosos de la primera prórroga: Danny Green, Paolo Banchero/Max Strus, Tre Jones y Saddiq Bey. El endpoint oficial con `RangeType=2,StartRange=28800,EndRange=31800` devuelve una exposición de equipo de 300,2–305 segundos, incluyendo un pequeño borde del período anterior. Se conserva ese dato. La prueba exige identidad/equipo/nombre exactos, coherencia de suma de minutos, exposición individual prácticamente completa y ausencia de evento entrante del jugador en el período; solo completa un conjunto que resulte en cinco titulares. Los intentos de rango de cinco segundos y `RangeType=0` no acreditaban esta prueba y se conservaron sin usarlos como titulares.

El replay mantiene relojes y orden original, verifica minutos y cinco IDs únicos durante todo tiempo positivo y compara con los stints de Ramiro. Esas fuentes pueden compartir origen NBA. Bol Bol y Steven Adams tienen intervalos oficiales administrativos con entrada igual a salida: pueden aparecer en acciones sin cubrir tiempo positivo. Esos intervalos se aceptan únicamente tras validar GameRotation completo, y el replay rechaza cualquier minuto positivo para ellos o una acción alejada del instante acreditado. Los valores canónicos previos de minutos/participación permanecen intactos; esto no decide la liquidación de una apuesta con reglas de aparición en cancha.

**Pendientes: 0022100074 (SAC–NOP, 29-oct-2021), 0022200793 (WAS–BKN, 4-feb-2023) y 0022401211 (BKN–MEM, 13-dic-2024).** Hay sustituciones con Hernangómez, Taj Gibson y Trendon Watford que entran en conflicto con la participación canónica. Los tres GameRotation solicitados no devolvieron contenido. Se descargaron tres PDFs oficiales de una sola página con boxscore; las variantes `_book.pdf` con el acta completa agotaron el tiempo de espera. Estos boxscores no prueban los límites de sustitución ni resuelven el conflicto. No se eliminaron eventos ni se inventaron segundos.

## Lesiones: un corte adicional por fecha

Se intentaron 816 cortes adicionales de las mismas fechas del censo médico. **815 PDFs válidos**, 84.797 filas nuevas y **75.451 filas de jugadores con ID NBA resuelto**. Se preservan exactamente los 816 reportes anteriores. Son principalmente cortes de 16:30 ET con nombres de archivo legados `_04PM.pdf`; desde el cambio de nomenclatura se capturó `_04_00PM.pdf`, 16:00 ET. Se valida el encabezado real, no se deduce la hora del nombre del archivo. El corte 24-oct-2023 sigue ausente: HTTP403 directo y RESP001 por ZenRows, cero créditos confirmados para ese reintento. No se recuperaron todas las versiones intradía.

El adaptador auxiliar conserva las continuaciones de página. Veintiséis PDFs inicialmente rechazados terminaban en una fila de equipo «NOT YET SUBMITTED» o una fila de jugador, algunas con motivo en dos líneas. Se incorporan esas filas con su contexto heredado, columnas y página de origen, con controles estrictos de geometría y comparación independiente de entidades/estados. Los casos reparados también comparan equipos sin reporte. La última fila nombrada reparada debe coincidir en su motivo con el segundo parser. Algunas razones multilínea de otras páginas están mal ordenadas por el parser upstream: se conservan sus diferencias y la lectura por coordenadas, en lugar de reemplazar los textos. Se inspeccionaron visualmente encabezados y páginas de continuación.

Once filas de «Yongxi, Cui» conservaron su texto original y recibieron ID1642385 mediante el nombre completo exacto «Cui Yongxi», explícitamente asociado a ese ID en el archivo canónico NBA previamente validado. No se invirtieron nombres por una regla general ni se dedujo la identidad de estadísticas o de un apellido. El original sin resolución y la nueva versión con pruebas permanecen separados. Los 3,859 cambios observados contienen 3,651 cambios de estado y 208 cambios solo de motivo; son comparaciones retrospectivas, no señales acreditadas de apuestas.

Hay **1.215 selecciones retrospectivas de reporte a T−60** para juegos con horario programado corroborado. El control separado cuenta 1.216 horarios únicos: uno carece de reporte elegible; 40 claves adicionales carecen de horario. El campo `known_scheduled_games` del agregador inicial incluía esas búsquedas vacías; `medical_chronology_review.json` separa explícitamente los conteos y reclasifica los motivos. Cada selección exige encabezado anterior o igual a T−60. Algunos reportes de tarde ya siguen al inicio de un partido: no se califican globalmente como prepartido. Se conoce la recepción actual, **no la recepción histórica original**, ni se afirma hora real del salto inicial. `prospective_PIT_eligible=false`, `pregame_availability_verified=false` y `actionable=false` siguen vigentes.

## Props, repositorios y ampliación preparada

Se reauditaron 44 snapshots guardados contra los rosters completos y los controles originales de cronología. Se conservaron exactamente 3.756 pares: 2.961 rebotes, 603 puntos y 192 asistencias. Los rebotes cubren 20 partidos piloto; puntos y asistencias solo dos. **Cero llamadas nuevas a The Odds API y cero créditos nuevos.** El límite local500 está agotado.

Se fijaron commits y verificaron archivos seleccionados de `m4nr44j/nba-betting`, `goosewolf98-netizen/nba-props-model` y `RayKang8/propsbasket`. Las fuentes examinadas aportan adaptadores o plantillas, sin nuevas cotizaciones históricas utilizables; el CSV de props examinado en el segundo contiene solo encabezados. El API público de `wippa-studios/wippa-nba-data` respondió404. Se conservaron árboles, respuestas y hashes Git/SHA256; no se ejecutó código de esos repos adicionales.

El plan concreto contiene **36 solicitudes**, dos cortes T−60/T−15 para los 18 partidos del piloto que aún no tienen puntos/asistencias. Pide ambos mercados y reserva hasta **720 créditos**, con límite local propuesto1.220 y sin compras. La autorización de aumento sigue pendiente; el plan no se ejecutó. Los históricos de props de este proveedor empiezan el3-may-2023, por lo que ese plan tampoco cubre2021–22 ni temporadas completas. Fuente: [documentación oficial de históricos por evento](https://the-odds-api.com/liveapi/guides/v4/#get-historical-event-odds).

Las reglas históricas de liquidación por casa, jurisdicción y fecha siguen pendientes. Una regla actual de Nueva York no prueba las reglas aplicables a todas las cotizaciones históricas. FanDuel respondió403 en la captura directa; esa respuesta no se presenta como texto de reglas recuperado. La documentación y páginas actuales revisadas tampoco justifican por sí solas liquidar históricos o entrenar/backtestear con disponibilidad prepartido.

## Costes, pruebas y evidencias

**140 créditos ZenRows nuevos confirmados**, cinco capturas del primer lote, cuatro del segundo y cinco del tercero; el reintento médico terminó con cero. Los ocho intentos del tercer lote incluyen tres fallos, conservados. Riesgo conservador **1.752/3.200**, incluyendo las reservas previas por cargos inciertos. Uso de cuenta observado al final: 1444/5000; no es saldo en tiempo real. Sin compras, cambios de plan ni exceso de límites. ZenRows se usa explícitamente como transporte de estas consultas; instalar el MCP no redirige automáticamente todos los scrapers.

**189 pruebas NBA pasaron; el arnés general pasó 707 antes y 707 después del trabajo.** La primera ejecución del arnés dentro del sandbox no pudo acceder al Python y se preservó junto al reintento válido. Los controles auxiliares verifican hashes, preservación exacta, fuente/rango/ID incorrectos, exposición positiva administrativa, página de continuación alterada y cronología médica/props. Los primeros fallos de aserciones auxiliares por censo incompleto de categorías y representación nula de nombre se conservaron y se corrigieron contra datos observados. No se modificó código NBA de producción en esta corrida.

Las **2.280 evidencias previas**, 40 corridas, gates y cadena local anterior se verificaron y preservaron. Los scripts y errores intermedios se conservan, y los auxiliares se archivan en su versión final sin atribuir ese hash retrospectivamente a cada ejecución. Registro local NBA-RUN-041, auto revisión; sin revisor independiente ni anclaje externo. No se promovieron entrenamiento, modelo, puertas o picks.

## Artefactos y trabajo restante

- Rotaciones: `apps/nba/.local/normalized/nba_pending41_rotations_20261006/combined_games.jsonl.gz`.
- Médicos con IDs y originales preservados: `apps/nba/.local/normalized/nba_pending41_injury_identified_20261006/reports.jsonl.gz`.
- Cortes, diferencias y selecciones por encabezado: `apps/nba/.local/normalized/nba_pending41_injury_20261006/`.
- Props y plan acotado: `apps/nba/.local/normalized/nba_pending41_props_20261006/`.
- Verificación, presupuestos y checkpoint: `apps/nba/.local/normalized/nba_pending41_validation_20261006/`.

Restan corroborar las tres rotaciones, conseguir el corte médico ausente y todas las versiones intradía/recepción histórica original, autorizar o sustituir el backfill de props y acreditar reglas históricas de liquidación. La investigación avanzó; el histórico completo y un backtest sin filtración siguen pendientes.
