# NBA: completar y validar históricos — 6 de octubre de 2026

Se recuperó el censo completo de fuentes de boxscores previsto y se validaron **6.149/6.150 regulares y 71/71 pretemporadas**. La versión aceptada contiene **164.190 filas**, con los rosters devueltos por NBA, incluidos DNP explícitos. El partido regular restante tiene sus fuentes conservadas y una excepción documentada del contrato de minutos; no se rellena con segundos inventados.

| Datos del censo de esta investigación | Antes de este lote | Resultado | Pendiente real |
|---|---:|---:|---|
| Boxscores regulares, 2021–22 a 2025–26 | 6.056 / 6.150 | 6.149 / 6.150 aceptados; fuentes de 6.150 capturadas | 1 excepción del normalizador |
| Pretemporada 2025–26 | 67 / 71 | 71 / 71 | 0 |
| Rotaciones regulares | 5.493 / 6.150 | 6,113 / 6.150 | 37 del censo |
| Tramos cronológicos por equipo | 231.075 | 258,137 | Solo quintetos aceptados |
| Fechas de reportes médicos del censo | 486 / 816 | 816 / 816; 80.932 filas | Intradía completo y recepción histórica original no acreditados |
| Nombres médicos vinculados | 13 nombres pendientes conocidos | 70.941 filas nominales con ID | 0 nombres pendientes en este censo |
| Props históricos | 2.961 pares de rebotes / 20 juegos | 3.756 pares: 2.961 rebotes + 603 puntos + 192 asistencias | Histórico de temporadas/mercados incompleto |

El censo médico cubre las 816 fechas previstas en esta investigación, no todos los PDFs emitidos por la NBA en cinco años. Los puntos/asistencias nuevos cubren solo dos partidos y dos cortes por partido; los rebotes anteriores cubren veinte partidos. Un par representa Over/Under de una casa, jugador, mercado, línea y corte, no un partido adicional.

## Recuperación y validación

Basketball Reference devolvió las 83 fechas solicitadas mediante ZenRows. Se incorporan 93 regulares y cuatro pretemporadas: 2.621 filas nuevas. Se conserva la totalidad de las 161.569 filas anteriores. El scraper upstream y el parser propio se contrastaron con NBAStats; los cambios de nombre usan alias oficiales explícitamente pareados con el ID. No se asignan personas por sus puntos/rebotes/asistencias. Los comentarios DNP se conservan del source; una ausencia sin comentario no se convierte automáticamente en DNP. Thomas Bryant 0022300810 usa el `didNotPlay` explícito de ESPN, con recibo, equipo y nombre completo corroborados.

Las referencias antiguas de localía/marcador se corrigen en overlays separados respaldados por calendario NBA, NBAStats y ESPN/BRef. Los Parquet originales permanecen intactos. El acta NBA de Oklahoma City–Charlotte confirma 11:00 para Branden Carlson frente a 10:60 del JSON: se preserva el valor inválido y se cita la fuente nueva. Las diferencias de formato o un segundo frente a las actas también se registran; los controles y tolerancias de producción permanecen congelados.

**Tony Bradley, 0022400942, 11-mar-2025:** NBAStats y BRef conservan 00:00 y un rebote. El CDN PBP tiene IDs explícitos de entrada y rebote con 0,2 segundos restantes del segundo cuarto, salida al inicio del tercero y otro intercambio administrativo sin avance del reloj al final del cuarto. GameRotation confirma exactamente 0,2 segundos positivos: IN_TIME_REAL 14398 y OUT_TIME_REAL 14400, en décimas de segundo. El normalizador congelado interpreta MM:SS cero como no participación y rechaza PRA positivos: se documenta esta limitación, conservando el roster de 28 filas y todas las pruebas en `nba_complete_box_exception_v3_20261006/source_consistent_game.json`. Este partido no entra en el dataset aceptado.

Rotaciones: +338 mediante V2/V3 y +191 mediante IDs explícitos de entrada/salida del CDN; la fuente GameRotation añade 91 partidos adicionales. Los quintetos cumplen cinco IDs únicos del equipo, períodos completos, relojes y minutos individuales. Las tandas de sustituciones se procesan en bloques consecutivos, preservando los eventos intermedios incluso cuando comparten reloj. La traducción ordenada dentro de una tanda no afirma qué entrante reemplazó causalmente a cada saliente. Se exige contraste con los stints publicados por Ramiro. Los nuevos intervalos oficiales GameRotation se contrastan además con puntos individuales, PBP y límites de entrada/salida. Son fuentes que pueden compartir origen NBA, no proveedores independientes de tracking.

En algunos boxscores, MM:SS cero y PRA cero coexisten con intervalos oficiales positivos de hasta un segundo. Para auditar esas rotaciones se usa una copia con participación acreditada por esos intervalos explícitos; el boxscore canónico permanece intacto. Se rechazan DNP explícitos, intervalos superiores a un segundo sin minutos y contradicciones de estadísticas. Cada overlay conserva el ID, los intervalos y el valor original; no se inventan jugadores iniciales.

Los 330 PDFs médicos faltantes estaban disponibles a las 17:30 ET aunque las URLs de 13:30 anteriores fallaban. Se recuperaron directamente de NBA, sin coste ZenRows. Se contrastaron las filas con el parser de mrees; 27 PDFs tenían una última página vacía con encabezado/pie, reconocida sin eliminar filas de datos. Se resolvieron los 13 nombres pendientes originales y los 19 nuevos nombres ambiguos mediante nombres completos, generaciones, alias NBA/GLeague explícitos y rangos oficiales FROM_YEAR/TO_YEAR. Se preservan todas las afirmaciones médicas previas. Vincular un ID no demuestra roster histórico o disponibilidad deportiva por inferencia. Algunos PDFs de tarde son posteriores al inicio de partidos; no se usan como si fueran la última información prepartido de esos juegos.

## ZenRows y cuotas

Se ejecutó ZenRows en tráfico real: durante las 83 capturas BRef se observó un incremento de 83 créditos en la cuenta. El límite preventivo BRef era 2.500; para GameRotation se reservó un máximo conjunto de 3.200, incluyendo resultados inciertos de timeouts. La contabilidad final registra 967.0 créditos confirmados y 400 reservados por cargos no confirmados. Los trabajos Batch cerrados recuperaron 86 capturas válidas por 695 créditos confirmados. Se guardan por solicitud o trabajo el coste confirmado del proveedor y la reserva; una respuesta vacía o un timeout no prueban coste cero. El transporte de PDFs conserva bytes originales; no se importa como oficial un PDF generado a partir de HTML. Uso observado final 1059/5000 créditos. No hubo compras, cambios de suscripción o instalación global adicional.

La instalación del MCP en Claude no redirige automáticamente las librerías Python/R ni garantiza acceso a todos los endpoints. Hubo 422, timeouts y una interrupción temporal de conectividad; se conservaron. Batch procesó los IDs no intentados y luego reintentó los fallidos dentro del presupuesto liberado por costes confirmados, manteniendo la reserva de cargos inciertos. Algunas respuestas cobradas como exitosas contenían HTML de error NBA en vez de JSON: se rechazan y conservan sus bytes originales por separado. Los originales útiles se validan antes de importarse.

The Odds API: cuatro solicitudes nuevas de puntos/asistencias consumen 80 créditos, completando el límite local de 500. Ocho controles rechazan snapshots posteriores al inicio. Las [reglas oficiales de histórico de The Odds API](https://the-odds-api.com/liveapi/guides/v4/#get-historical-event-odds) sitúan los props históricos después de 2023-05-03T05:30:00Z, con snapshots cada cinco minutos y acceso de pago. Por ello, este proveedor no completa props de 2021–22. Ampliar partidos exige definir censo, casas, cortes y presupuesto; las reglas de liquidación por casa todavía deben verificarse antes de evaluar apuestas. No se afirma cobertura total ni rentabilidad.

## Artefactos y comprobaciones

- Boxscores: `apps/nba/.local/normalized/nba_complete_boxes_final_v4_20261006/player_games.jsonl.gz`.
- Excepción regular: `apps/nba/.local/normalized/nba_complete_box_exception_v3_20261006/source_consistent_game.json`.
- Rotaciones: `apps/nba/.local/normalized/nba_complete_official_rotations_final_20261006/combined_games.jsonl.gz`.
- Reportes médicos: `apps/nba/.local/normalized/nba_complete_injury_final_20261006/reports.jsonl.gz`.
- Props combinados: `apps/nba/.local/normalized/nba_complete_validation_20261006/props_all_markets.jsonl.gz`.
- Verificación/cobertura/pendientes: `apps/nba/.local/normalized/nba_complete_validation_20261006/verification.json`, `transport_summary.json`, `recovery_inventory.json`.
- Capturas y recibos: `apps/nba/.local/raw/nba_complete_20261006/`.

Se revalidaron los 97 nuevos rosters completos con el normalizador sin modificar; controles de corrupción de PRA, DNP, duplicados, minutos e intervalos oficiales. 21 controles adversariales, 435 manifiestos/recibos raw verificados, 340 evidencias previas y 39 archivos NBA de producción intactos. Harness 706 antes / 706 después; Docker no disponible. Los scripts auxiliares y fuentes se conservan; sus versiones de salida rechazadas/iteraciones intermedias también permanecen como diagnóstico.

Se registra NBA-RUN-039 en el ledger local. Auto revisión, sin revisor independiente ni anclaje externo. No se modificaron entrenamiento, modelo, puertas o picks. Los repos usados y los revisados sin ejecución se documentaron anteriormente en `docs/nba_github_scrapers_recuperacion_20261006.md`; esta ejecución amplía recuperación/parseo, no convierte índices o proyectos de pronósticos en scrapers completos. Reproducción: usar los scripts archivados en `apps/nba/.local/code_snapshots/nba_complete_20261006/`, con nuevas carpetas de salida; los comandos rechazan sobrescritura. Los scripts de cada stage conservados reflejan sus parámetros; los otros scripts iterados se archivan en su versión final, sin atribuir ese hash retrospectivamente a cada intento anterior.
