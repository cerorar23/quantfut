# NBA: recuperación y validación — 7 de octubre de 2026

Se completaron las **6.150 rotaciones regulares del censo 2021–22 a 2025–26**, se añadieron **228.324 pares de precios de puntos para 3.429 partidos** y se incorporaron **210 reportes médicos intradía**. Los datos anteriores se preservaron exactamente. Es la corrida NBA-RUN-042.

| Datos | Resultado validado |
|---|---:|
| Rotaciones regulares | 6.150 / 6.150 |
| Tramos por equipo | 259.826 |
| Pares de precios de props, combinados | 232.080 |
| Versiones de reporte médico | 1.841 |
| Filas médicas | 186.634 |

Los boxscores siguen en 164.218 filas. El censo regular incluye cinco temporadas; las otras categorías adquiridas antes tienen cobertura parcial. Estos resultados no equivalen a toda la historia NBA.

## Rotaciones completadas

Las actas oficiales completas resolvieron los tres casos pendientes: SAC–NOP del 29-oct-2021, WAS–BKN del 4-feb-2023 y BKN–MEM del 13-dic-2024. Hernangómez, Taj Gibson y Trendon Watford tienen entradas y salidas con el mismo reloj detenido. Se cruzaron las abreviaturas del PDF con IDs explícitos V2/V3, equipo y roster canónicos. Morris se resolvió dentro de su equipo para evitar confundirlo con el Morris del rival.

El replay conserva los eventos originales y exige cinco IDs únicos, continuidad y minutos corroborados. Los jugadores administrativos quedan documentados con cero exposición y no cubren ningún tramo positivo. Se preservan exactamente las 6.147 rotaciones previas y se añaden 139 tramos en los tres juegos. Esto no decide cómo una casa liquida una apuesta cuando hubo una aparición sin tiempo positivo.

## Precios recuperados sin nuevos créditos de The Odds API

Se descargaron y verificaron 3.662 JSON del [archivo público de NBA-Propositions-Forecasting-App](https://github.com/KamranSHussain/NBA-Propositions-Forecasting-App/tree/a95be8924f3c4fe08b44dcfd940269610ca49501). Se fijó el commit y se comprobaron hashes Git/SHA256; no se ejecutaron sus modelos o entrenamiento. El mapa de eventos se contrastó con rosters NBA, fechas, equipos, localía y horarios ESPN independientes, cuyos archivos nuevos se verificaron contra los hashes publicados de [sportsdataverse](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_player_boxscores).

| Temporada | Partidos con puntos nuevos | Pares nuevos |
|---|---:|---:|
| 2023–24 | 1.141 | 102.223 |
| 2024–25 | 1.155 | 42.299 |
| 2025–26 | 1.133 | 83.802 |

Los 228.324 pares nuevos son Over/Under de puntos de 11 casas. El total combinado contiene 228.927 pares de puntos, 2.961 de rebotes y 192 de asistencias. La fuente nueva no amplía rebotes o asistencias.

**Las capturas están entre 6,07 y 16,79 horas antes del horario corroborado; no son cortes T−60/T−15.** Se conserva ese horizonte real. Solo se aceptan actualizaciones de casa y mercado anteriores o iguales al snapshot, con captura anterior a los horarios de inicio del proveedor y de ESPN. También se exigen precios decimales válidos, línea compatible, par exacto y nombre completo único en el roster del mismo juego. Eventos sin mapa, fechas contradictorias, mercados actualizados después de la captura y nombres ambiguos quedan en cuarentena.

## Reportes médicos

Se inventariaron 240 rutas candidatas de siete fechas. Había 223 PDFs disponibles: 13 previos y **210 nuevos**, con 20.905 filas y 18.750 filas nominales con ID. Se resolvieron 22 filas de Cui Yongxi mediante su nombre completo e ID ya acreditados. Los 1.631 reportes anteriores permanecen intactos.

Las fechas de muestra fueron 24-oct-2023; 1-nov de 2021, 2022, 2023, 2024 y 2025; y 1-feb-2026. El primer día de 2023–24 tiene siete cortes disponibles de 17:30 a 23:30 ET, compatibles con el inicio documentado por nbainjuries. Las rutas anteriores devolvieron 403: no prueban que el corte de 16:30 existiera ni acreditan un bloqueo general de IP. Las otras cinco fechas legadas tienen 24 PDFs cada una; febrero de 2026 tiene 96 candidatos disponibles.

Ambos lectores concuerdan en entidades, estados y equipos sin reporte. Se conservan motivos literales y diferencias de orden de líneas del lector independiente. El control estricto de motivos para una continuación de una fila se mantiene; se corrigió su aplicación indebida a páginas normales con muchas filas. Este es un inventario de la nomenclatura documentada en siete fechas, no de todas las versiones históricas.

Hay 1.216 horarios médicos únicos corroborados y 1.215 selecciones retrospectivas T−60. Encabezados antiguos y recepción actual no prueban recepción prepartido original. La elegibilidad prospectiva y `actionable` siguen en falso.

## Validación y límites

Pasaron **189 pruebas NBA** y el arnés general: 707 antes y 732 después. El aumento del arnés corresponde al trabajo concurrente de fútbol, conservado. No se cambió producción NBA. Se comprobaron las 4.939 evidencias, 41 corridas y 89 eventos previos; el checkpoint original termina con 9.636 evidencias y 90 eventos. Los controles rechazan fuentes alteradas, exposición administrativa positiva, horarios futuros, localía incorrecta, pares duplicados, precios/líneas inválidos y nombres ambiguos.

Se usaron **30 créditos ZenRows**, con riesgo conservador acumulado de 1.782/3.200. Hubo **cero llamadas o créditos nuevos de The Odds API**; su límite local de 500 está agotado. No se compraron créditos ni se cambió de plan. La ampliación propuesta de 720 créditos permanece sin autorización y sin ejecutar.

Los datos son de investigación: las reglas históricas de liquidación y la disponibilidad prepartido original siguen sin acreditar. No se promovieron modelos, gates, picks o ROI. El registro es local, con auto revisión y sin anclaje externo.

## Archivos y trabajo restante

- [Rotaciones completas](../apps/nba/.local/normalized/nba_pending42_rotations_final_20261007/combined_games.jsonl.gz).
- [Cuotas combinadas](../apps/nba/.local/normalized/nba_pending42_props_v2_20261007/quotes.jsonl.gz).
- [Reportes médicos con IDs](../apps/nba/.local/normalized/nba_pending42_medical_identified_20261007/reports.jsonl.gz).
- [Verificación y checkpoint](../apps/nba/.local/normalized/nba_pending42_validation_20261007/).
- [Informe técnico original sellado](nba_props_y_rotaciones_20261007.md).

Restan rebotes/asistencias a escala, puntos en los eventos o temporadas faltantes, cortes T−60/T−15, intradía de las demás fechas, recepción histórica original y reglas de liquidación por casa, fecha y jurisdicción. Las rotaciones regulares del censo ya están completas. Esta nota mejora la presentación del informe; el informe técnico y los datasets sellados permanecen intactos, y la revisión documental se registra por separado.
