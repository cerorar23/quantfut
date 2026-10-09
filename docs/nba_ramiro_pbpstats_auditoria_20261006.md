# NBA: auditoría Ramiro y contraste pbpstats — 6 de octubre de 2026

Se descargaron cinco archivos públicos y se reprodujeron los PBP locales. **Se agregan 7 partidos de rotaciones a una versión separada**, preservando los 5161 anteriores. Es investigación retrospectiva; no se entrenó el modelo ni se habilitaron picks.

## Resultado verificado

| Componente | Resultado |
|---|---:|
| Temporadas regulares | 2021–22 a 2025–26 |
| Archivos fuente / tamaño | 5 CSV / 110,072,340 bytes |
| Partidos / filas de fuente | 6,150 / 374,364 |
| Boxscores regulares aceptados usados | 6,055 |
| Fuente sin boxscore aceptado | 95 |
| Partidos que pasan estructura y minutos de fuente | 6,033 |
| Acuerdos con rotaciones anteriores | 5,149 |
| Partidos corroborados por replay raw | 5,156 |
| Nuevos partidos de rotaciones | 7 |
| Recuperados de las 891 cuarentenas anteriores | 4 |
| Regulares aceptados después del lote anterior de PBP, ahora procesados | 3 |
| Versión combinada: partidos / tramos cronológicos por equipo | 5,168 / 217,619 |
| Cuarentenas anteriores aún pendientes | 887 |
| Boxscores regulares aceptados aún sin rotación aceptada | 887 |
| Sustituciones contrastadas con pbpstats | 248,283 |
| Pruebas fútbol antes / después | 693 / 693 |
| Pruebas NBA / controles adversariales | 172 / 15 |

Los cuatro rechazos nominales recuperados corresponden a Brandon Boston, cuyo ID NBA `1630527` aparece con el nombre completo Brandon Boston Jr. en la fuente. Se conserva el nombre canónico previo; el sufijo aporta una etiqueta única para verificar la entrada del PBP. Los siete incrementos coinciden en quintetos y extremos de reloj con la fuente, sin usar la tolerancia de un segundo.

| GameID | Fecha | Tramos por equipo | Motivo del incremento |
|---|---|---:|---|
| 0022200067 | 2022-10-27 | 49 | Sufijo nominal corroborado |
| 0022300658 | 2024-01-29 | 44 | Sufijo nominal corroborado |
| 0022300827 | 2024-02-25 | 41 | Sufijo nominal corroborado |
| 0022301156 | 2024-04-09 | 37 | Sufijo nominal corroborado |
| 0022400015 | 2024-11-15 | 50 | Boxscore añadido después del lote anterior |
| 0022400376 | 2024-12-21 | 41 | Boxscore añadido después del lote anterior |
| 0022401190 | 2025-04-13 | 23 | Boxscore añadido después del lote anterior |

## Fuentes y reglas

[ramirobentes/nba_pbp_data](https://github.com/ramirobentes/nba_pbp_data/tree/e702d9b7b585bb79e751eb52d5d767e29f16cab0) queda fijado al commit `e702d9b7b585bb79e751eb52d5d767e29f16cab0`. Se verificaron tamaño, SHA256 y SHA1 de Git de los cinco CSV. El manifiesto conserva URL y recepción UTC. Las carpetas seleccionadas contienen temporada regular; no acreditan pretemporada ni playoffs.

La identidad de cada quinteto se une por cinco IDs NBA distintos y participantes del boxscore aceptado, nunca por similitud estadística. Se contrastan ambos equipos, localía del calendario, espejo del oponente, períodos y prórrogas, continuidad y puntos finales. Los relojes de fuente conservan centésimas/décimas cuando existen; los intervalos de duración cero quedan raw y no generan minutos artificiales.

El replay utiliza los cinco archivos NBA V3 locales del commit `e829d4678be1e075f99e5d41a1c5f97089be446b` de shufinskiy. Prueba cinco titulares por equipo y período mediante primera acción de cancha o primera salida anterior a una entrada. No usa el quinteto de Ramiro como override inicial. Exige orden temporal, actor en cancha, salida/entrada coherentes y marcador final correcto. Los nombres completos publicados pueden aportar variantes ligadas al mismo ID cuando coinciden con el nombre canónico, permitiendo un sufijo generacional ausente pero nunca contradictorio. Las etiquetas ambiguas siguen rechazadas.

Los minutos individuales mantienen el presupuesto existente: un segundo por intervalo continuo del propio jugador dentro de cada período, sin contar los cambios de compañeros como intervalos adicionales. No se escalan relojes ni se reparten diferencias. Los quintetos coalescidos deben coincidir entre fuente y replay, con máximo un segundo de diferencia por extremo; las diferencias quedan registradas.

`pbpstats==1.3.11` se conserva como wheel con hash de PyPI y se ejecuta en una carpeta aislada. Se reproduce cada sustitución con los IDs ya corroborados mediante `StatsSubstitution.current_players`. **Esto valida la transformación del quinteto, no una ingestión nativa completa de V3, posesiones o datos adicionales.** La dependencia requests tiene la red bloqueada durante el audit. No se instalaron dependencias en el entorno principal NBA.

Ramiro y el PBP pueden compartir origen NBA. La concordancia no acredita procedencia independiente ni constituye revisión externa. Los quintetos se reconstruyen con datos posteriores al partido; no representan disponibilidad prepartido ni seguimiento físico exacto.

## Discrepancias conservadas

- source_structure: lineup ID absent or DNP in canonical box: 9 registros de diagnóstico.
- source_structure: individual source minute mismatch: 3 registros de diagnóstico.
- source_structure: source/calendar locality mismatch: 10 registros de diagnóstico.
- previous_rotation_compare: PBP/source stint count mismatch: 1 registros de diagnóstico.
- raw_pbp_replay: PBP ambiguous substitution in label: 376 registros de diagnóstico.
- raw_pbp_replay: PBP final score mismatch: 4 registros de diagnóstico.
- raw_pbp_replay: PBP exact five starters not proven: 78 registros de diagnóstico.
- raw_pbp_replay: PBP mismatched substitution out label: 413 registros de diagnóstico.
- raw_pbp_replay: PBP substitution contradicts quintet: 1 registros de diagnóstico.
- raw_pbp_replay: PBP individual minute mismatch: 3 registros de diagnóstico.
- raw_pbp_replay: PBP off-court actor: 1 registros de diagnóstico.
- raw_pbp_replay: PBP/source stint count mismatch: 1 registros de diagnóstico.

Los conteos anteriores son registros de diagnóstico: un partido puede figurar en distintos contrastes. `report.json` conserva IDs, etapa y motivo. Las discrepancias de Ramiro no sobrescriben las rotaciones aceptadas anteriores. Los 95 juegos sin boxscore aceptado no se incorporan solo porque tengan lineups.

## Verificación y artefactos

`verification.json` verifica los cinco blobs fuente, outputs y PBP, todos los quintetos/períodos/minutos de la versión combinada y la igualdad de los 5161 registros previos. Sus 15 controles adversariales rechazan IDs desconocidos/duplicados, equipo/localía, partido, oponente incompleto, duración, gaps, marcador, DNP, minutos individuales y reloj no finito. Los 39 archivos propios NBA congelados permanecen intactos. El harness pasó antes/después; Docker no estaba disponible. La suite NBA terminó con código cero y 172 casos recolectados.

Resultado final: `apps/nba/.local/normalized/ramiro_pbpstats_v3_20261006/`. `new_games.jsonl.gz` contiene solo el incremento; `combined_games.jsonl.gz` conserva la referencia previa y añade únicamente el incremento corroborado. `corroborated_games.jsonl.gz` conserva todos los acuerdos de este lote. El SHA256 de la versión combinada es `d835c08a9481b13ec37ca98aa82407f8db045fc55807af610568371c09cd11d9`.

Las carpetas exploratorias `ramiro_pbpstats_20261006` y `ramiro_pbpstats_v2_20261006` corresponden a intentos incompletos del adaptador; no son resultados aceptados. La versión final es v3. Las fuentes, scripts, snapshots y diagnósticos quedan sellados en NBA-RUN-036. Cero créditos de cuotas, cero suscripciones, sin promoción de puertas. La integridad usa hashes locales sin anclaje externo.
