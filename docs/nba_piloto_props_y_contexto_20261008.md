# NBA-RUN-060 — piloto de props históricos, actuales y contexto

Se ejecutó la solución autorizada por el usuario («ejecutalo»): **diez partidos históricos con puntos, rebotes y asistencias, y contexto médico oficial anterior al corte**. El conjunto reúne **2.617 pares Over/Under con identidad NBA**, combinando nuevos precios y capturas anteriores elegibles. La consulta actual de diez eventos produjo **21 pares de props en tres partidos de temporada regular**. El consumo fue **219 créditos del plan existente**, dentro del nuevo límite puntual de 250. No se contrataron servicios.

Estos resultados completan la muestra de investigación de precios/contexto. **No completan contratos mexicanos, disponibilidad final ni validación comercial**. F6 permanece abierta; F7 no inicia.

| Resultado comprobado | Alcance |
| --- | --- |
| Históricos con tres mercados al corte común | 10 partidos del 21–22 de octubre de 2025, los primeros diez del piloto anterior fijado antes de consultar |
| Pares históricos nuevos con identidad NBA | 1.957 |
| Pares de rebotes anteriores reutilizados y elegibles | 660 |
| Total histórico identificado | 2.617 pares / 5.234 precios individuales; no jugadores distintos |
| Contexto médico oficial reutilizado | 10 partidos / 62 observaciones anteriores al corte; PDFs y hashes comprobados |
| Props actuales | 21 pares / 3 partidos NBA regular; siete por mercado de puntos, rebotes y asistencias |
| Eventos actuales consultados | 10: 6 pretemporada y 4 regular; los seis de pretemporada no devolvieron los mercados estándar solicitados |
| Antigüedad actual al recibir la respuesta | 15 de 21 pares tenían actualización de mercado≤60 segundos; no se presentan como precios vigentes después de la captura |
| Contexto público actual | 6 partidos ESPN, 96 observaciones de lesiones ESPN, 5 filas RotoWire y 6 tarjetas de quintetos |
| Caliente México | Solicitud directa 403; navegador público accesible. Dos partidos revisados: mercados de equipo, cero props individuales observados |
| Consumo API nuevo | 219 créditos: 210 históricos y 9 actuales; 28 solicitudes totales, incluyendo rutas gratuitas y un 422 sin cargo |
| Saldo compartido al último recibo | 18.419 créditos a las 21:43 UTC del 08 de octubre de 2026; no es un saldo garantizado posterior ni cuota exclusiva NBA |
| Contratos de jugador promovidos / disponibilidad final acreditada | 0 / 0 |
| Pruebas pertinentes | 69 aprobadas; 23 del nuevo cliente/normalizador y 46 de fuentes/contexto existentes |
| Arnés general posterior | 798 aprobadas / 16 omisiones en el árbol compartido; resultado completo conservado |

## Datos listos para revisar

Los archivos están en `apps/nba/.local/normalized/nba_f6_run60_20261008/`:

- `accepted_historical_pairs_v2.json`: 2.617 pares de precios identificados, con corte, reloj del proveedor, recepción propia real y vínculo a los bytes originales. La validación se limita a precios/identidad/cronología; las reglas siguen desconocidas.
- `game_bundles_v2.json`: diez paquetes por partido con conteos de los tres mercados y selección médica oficial/PDF/hash anterior al corte.
- `candidate_current_pairs.json`: 21 pares actuales en estado candidato; sin identidad NBA, contrato mexicano o disponibilidad final acreditados.
- `coverage.json`, `capture_result.json` y versiones posteriores: resultados intermedios preservados; `game_bundles_v2.json` y `final_capture_result_v2.json` son el alcance final corregido.
- `quarantine_v2.json` y `alignment_quarantine.json`: mercados con relojes incompatibles; 91 pares nuevos históricos conservan identidad desconocida y no entran al conjunto identificado. La revisión separada excluye además 13 pares anteriores de Jimmy Butler porque el nombre canónico contiene III y este piloto exige nombre completo normalizado exacto; no se cambia el ID ni la evidencia anterior.
- `reused_rebounds_excluded.json`: 43 pares anteriores que no cumplen el nuevo corte común; no se alteraron sus capturas originales.
- `caliente_browser_observations.json`: transcripción estructurada de lo observado en el navegador, con selección/mercado/precio de la muestra regular. No se presenta como cuerpo HTTP original ni recibo exacto del navegador.
- `manual_prop_template.json`: formulario de datos para futuras capturas reales mexicanas; campos desconocidos permanecen vacíos y no generan un contrato aceptado.
- `verification.json`: reconstrucción offline separada de precios, identidades, consumo, recibos y cadena. Misma autoría; no constituye revisión humana independiente.

Los cuerpos originales nuevos y cabeceras sin credenciales están en cuatro carpetas `apps/nba/.local/raw/nba_props_*run60*_20261008/`. Sus manifiestos preservan solicitudes, consumo y fallos. Los reportes médicos se reutilizan de la versión sellada de RUN044; no se les asigna recepción original anterior al partido.

## Cómo se controló el gasto y el tiempo

La instrucción de ejecución autorizó este piloto después de explicar la necesidad de ampliar el límite anterior consumido y los costos por mercado. Se fijó un máximo **incremental de 250 créditos**. Los 500 anteriores permanecen registrados como histórico; el consumo nuevo se registra aparte. El cliente limita su gasto al menor de su techo y 10% del saldo inicial observado, deja al menos 1.000 créditos en la cuenta compartida y conserva reservas antes de solicitar datos. Un timeout o cuota desconocida detiene la captura sin reintento automático. La ejecución comprobada gastó 219 y dejó cero reservas inciertas.

Se pidió un corte de 60 minutos antes del horario más temprano entre el horario ESPN archivado y el inicio del proveedor. En Dallas–San Antonio, el proveedor indicaba 01:40 UTC y ESPN 01:47 UTC. El corte común 00:40 UTC dejó fuera 43 pares de rebotes cuyo snapshot anterior era posterior. Se descargó una vez el corte correcto de rebotes, por 10 créditos. Los tres mercados finales respetan el mismo corte por partido; no se movieron horarios para salvar datos.

Otros 41 mercados históricos de las nuevas capturas de puntos/asistencias tenían actualizaciones posteriores al snapshot y quedaron excluidos. El nombre de jugador se enlaza únicamente por nombre completo normalizado único dentro del boxscore canónico de ese partido. Ese boxscore es una referencia retrospectiva de identidad; **no reconstruye el universo disponible antes del partido**.

Los endpoints actuales de The Odds API omiten el reloj general de la casa y sí contienen reloj por mercado. Se corrigió el parser para conservar el reloj general como desconocido y validar el del mercado; la corrección se aplicó offline a respuestas ya recibidas, sin volver a pagar consultas. Los históricos conservan el control del reloj general cuando corresponde. [Documentación V4](https://the-odds-api.com/liveapi/guides/v4/).

## Fallos conservados y límites de la muestra

El primer driver falló al pasar un objeto de fecha a una función que esperaba texto; había recibido solo la lista gratuita de deportes, sin gasto. La primera reconstrucción offline omitió un campo de identidad desconocida y se detuvo ante la comparación de preservación. Una solicitud adicional de alineación de rebotes devolvió422 porque el proveedor rechazó `+00:00` en el parámetro de fecha; confirmó cero cargo. Se normalizó a UTC con `Z` y la solicitud corregida fue registrada separadamente. El primer verificador separado omitió la normalización de puntuación en nombres prevista por el protocolo y falló; se conservó y luego aplicó la política declarada. Ningún fallo incierto de red generó un reintento automático.

Las fuentes actuales de lesiones/quintetos no acreditan participación definitiva ni rol. No se interpreta la ausencia en una lista de lesiones como jugador sano. Los 62 registros oficiales históricos permiten analizar lo publicado antes del corte, pero se descargaron retrospectivamente; no prueban recepción propia en 2025.

El navegador permitió leer [Boston–Cleveland](https://sports.caliente.mx/es_MX/e/33506702/Boston-Celtics-%40-Cleveland-Cavaliers), el [catálogo NBA regular](https://sports.caliente.mx/es_MX/NBA) y [Philadelphia–NewYork](https://sports.caliente.mx/es_MX/e/32677797/Philadelphia-76ers-%40-New-York-Knicks). Se observó acceso público, sin sesión ni modificación de boletos. Eso **no resuelve una captura automática continua desde el VPS** ni demuestra que Caliente carezca de props en todos sus eventos. No se usó ZenRows nuevo ni se rotaron IPs en esta prueba.

La muestra usa una región estadounidense y casas devueltas por la API; no se sustituyen cuotas mexicanas con estos precios. Los históricos ya habían sido inspeccionados: este piloto es ampliación y verificación de investigación, sin resultados de rentabilidad, nuevo entrenamiento o confirmación futura.

## Lo que todavía requiere evidencia real

Faltan props de casas/jurisdicciones objetivo con período, prórroga, participación, push, correcciones y versión de reglas aplicables; disponibilidad/rol por partido; recepción original histórica ausente según el usuario; y la muestra operativa completa exigida para F6. Las descargas, contratos y sellos existentes no fabrican esas entradas. El nuevo conjunto no tiene un sello temporal externo propio; la firma de RUN059 cubre exclusivamente el manifiesto anterior de RUN058.

Se conservaron 59 corridas previas,20.563 evidencias y147 eventos anteriores. Modelos, gates, canales y servicios permanecen en su estado anterior. No hubo apuestas, publicación comercial, mensajes, cambios VPS ni nuevas copias periódicas.

El arnés general inicial aprobó786 pruebas con15 omisiones; el posterior,798con16 omisiones. El resultado posterior completo queda en `apps/nba/.local/reports/nba_run60_post_final_20261008.log`; el checkpoint de RUN060 registra su resultado y los 69 casos pertinentes. El árbol compartido contiene trabajo de fútbol de otras sesiones, que este piloto no modifica; la diferencia de conteos corresponde a ese árbol cambiante, no a pruebas NBA omitidas en el grupo pertinente.
