# Ampliación del motor de tenis: datos, calibración y seguimiento

Fecha: 17 de octubre de 2026. Complementa la auditoría anterior. Las nuevas piezas se implementaron y ejecutaron localmente. Se conserva el candidato de ganador anterior; el experimento dinámico no logró justificar su sustitución.

## Cuenta y presupuesto confirmados

El titular confirmó **The Odds API de pago** y autorizó **2.000 créditos mensuales para tenis**. La configuración persistente vive en `apps/tennis/config/operations.json`. Se conserva la reserva original de **6.000** para los demás motores; los 200 adicionales que se habían recomendado como margen de tenis se reasignaron tras la autorización. Esto sustituye el límite inicial de 80 y la reserva conservadora de 6.200.

Se probaron de verdad los endpoints de histórico de pago: un snapshot ATP Shanghai y otro WTA Wuhan, con Pinnacle, ganador/hándicaps/totales. Coste confirmado: **30 + 30 = 60 créditos**. Se obtuvieron **5 eventos y 26 cotizaciones** en total; no todos los eventos traían los tres mercados. El libro confirma 77 créditos de tenis acumulados, incluidos los 17 de la fase anterior; la contabilidad conservadora reserva 89. El saldo observado a las 20:38 UTC fue **6.038**; mientras se preserve la reserva, en ese momento solo había 38 créditos utilizables, aunque el presupuesto mensual de tenis sea 2.000. El catálogo es gratuito y permite refrescar el saldo antes de cada solicitud pagada.

Los snapshots están solicitados para el 16-oct-2026 a las 10:00 UTC; el proveedor devolvió su observación de las 09:55:36 UTC. **No se etiquetan automáticamente como cierres.** El código histórico valida fecha, circuito, límites, reservas y recibos sin persistir la clave.

## Calendario oficial: resueltos los dos encuentros actuales

Se descargaron, archivaron y revisaron visualmente ambos órdenes de juego oficiales:

| Final | Pareja confirmada | Hora oficial «no antes de» | UTC | Hora del centro de México |
|---|---|---|---|---|
| Shanghai, 18-oct | Alejandro Davidovich Fokina / Rafael Jodar | 16:30 en China | 08:30 | 02:30 |
| Wuhan, 18-oct | Maja Chwalinska / Sonay Kartal | 18:30 en China | 10:30 | 04:30 |

Los PDF coinciden con los horarios de The Odds API. Resuelven el bloqueo anterior por cruce y hora no confirmados; la noticia de Wuhan con otra franja horaria queda sustituida por el orden de juego oficial posterior. Fuente: [ATP Shanghai OP](https://www.protennislive.com/posting/2026/5014/op.pdf), [WTA Wuhan OP](https://wtafiles.wtatennis.com/pdf/draws/2026/1075/OP.pdf).

Se añadió un adaptador estricto para esos dos documentos/edición. Comprueba pareja de nombres completos, rivalidad explícita, fecha, superficie y única hora «no antes de», convierte China UTC+8 a UTC y genera el recibo con hash. Ante otro diseño, fecha o pareja, rechaza la interpretación. El registro de las 20:38:31 UTC pasó los controles de calendario e identidad para los dos eventos; la consulta de cuotas permanece a la espera de sus ventanas T−120 y T−15.

`--refresh-official` vuelve a observar los documentos en cada ejecución. La publicación de un orden de juego no acredita estado en vivo después de su hora «no antes de»: a partir de ella el control exige una fuente de estado en vivo. El adaptador actual no cubre automáticamente todos los torneos ni fechas futuras. Los identificadores externos nuevos siguen necesitando vinculación revisada.

## Calibración de mercados secundarios ejecutada

Se generaron predicciones fuera del ajuste de puntos para 2025 y se ajustaron calibradores por contrato con esos resultados. Se aplicaron a las predicciones 2026 previamente archivadas. Los cuatro contratos se declararon antes del ajuste: Over 22,5 juegos, hándicap A −3,5 juegos, habrá tie-break y ganador del primer set. La escala y el intercepto tienen regularización; primer set mantiene intercepto cero para conservar la simetría entre jugadores.

Menor log-loss es mejor:

| Circuito | Contrato | Original | Calibrado |
|---|---|---:|---:|
| ATP, n=2.451 | Over 22,5 juegos | 0,57289 | **0,56164** |
| ATP | A −3,5 juegos | 0,59428 | **0,57678** |
| ATP | Habrá tie-break | 0,66275 | **0,65977** |
| ATP | Ganador del primer set | 0,65500 | **0,65053** |
| WTA, n=2.146 | Over 22,5 juegos | 0,68594 | **0,66546** |
| WTA | A −3,5 juegos | 0,61992 | **0,59692** |
| WTA | Habrá tie-break | 0,55460 | **0,54868** |
| WTA | Ganador del primer set | 0,66466 | **0,65268** |

Brier también bajó en los ocho casos. Los intervalos exploratorios por bloques fueron favorables en siete; el de tie-break ATP incluye cero. Los mismos partidos alimentan cuatro contratos relacionados, por lo que las filas no son muestras independientes. Las comparaciones múltiples y la dependencia entre jugadores limitan estos intervalos.

Esto es desarrollo retrospectivo: 2026 ya había sido observado. La mejora se refiere al modelo original y **no demuestra ventaja frente a cuotas ni ganancias**. Los coeficientes no se trasladan a Over 23,5, −3,0 ni otras líneas sin prueba. El adaptador añade las probabilidades calibradas experimentales como campos separados; conserva las probabilidades originales y no las presenta como una distribución conjunta calibrada de todos los mercados. Las selecciones opuestas del mismo contrato mantienen probabilidades complementarias.

## Habilidades dinámicas y contexto: experimento terminado

Se implementó un filtro de estados gaussianos para saque/resto. La varianza de las habilidades aumenta con el tiempo transcurrido; cada periodo se asimila en bloque para no inventar el orden dentro de la semana. Se ajusta un MAP binomial por bloque y se conserva una aproximación diagonal de la covarianza. La optimización usa coordenadas estandarizadas por el prior para resolver el mal condicionamiento numérico del primer intento.

Se contrastaron dos versiones, con y sin edad/lateralidad/indoor e indicadores de datos ausentes. Los parámetros y el ruido de proceso se fijaron antes de ajustar. También se hicieron controles que calibran o mezclan sus salidas con Elo usando solo 2025. El embargo temporal de 35 días se mantuvo. Los resultados 2026 son:

| Candidato | ATP log-loss | WTA log-loss |
|---|---:|---:|
| Híbrido anterior | **0,62243** | **0,61832** |
| Dinámico sin contexto, sin calibrar | 0,75997 | 0,82344 |
| Dinámico con contexto, sin calibrar | 0,76254 | 0,84252 |
| Dinámico con contexto + Elo, mezcla aprendida en 2025 | 0,62543 | 0,61846 |

**No se promueve el filtro dinámico.** La aproximación mostró exceso de confianza y su mezcla calibrada no superó al candidato anterior. La diferencia WTA final es pequeña y tampoco justifica sustitución. El código, parámetros y resultados se conservan para investigación; implementar una variable no demuestra que ayude.

## Fatiga, viajes y clima: cálculo con controles temporales

La nueva capa de contexto puede calcular minutos/sets observados en 7/14/30 días, descanso desde el último final, distancia entre sedes, cambio de huso/altitud/superficie. Exige inicios y finales UTC reales, recibo anterior a la decisión y fuente cuyo hash coincida. Rechaza fechas semanales. Una historia parcial se etiqueta como parcial: una suma observada no implica carga completa y los datos ausentes no se convierten en cero fatiga.

La distancia entre sedes es una aproximación de desplazamiento, no un itinerario personal. El clima requiere un pronóstico archivado antes de emitir la predicción; el código rechaza reanálisis presentado como pronóstico. Si no se sabe si la pista está cubierta, mantiene el clima como desconocido. Estas variables tienen código y pruebas, pero todavía no se ajustan en el candidato de operación por falta de historia temporal adecuada.

## Evaluación futura y CLV preparados

Se congeló un protocolo independiente para partidos del **18-oct-2026 al 31-dic-2026**, con hashes de ambos modelos, mezcla, control Elo calibrado y calibradores de mercados. El evaluador rechaza cambios de versión, pronósticos posteriores al inicio, fases mal etiquetadas, fuentes incongruentes y resultados sin evidencia. Desduplica el registro previo/posterior a cuotas dentro de cada evento/fase.

Los controles incluyen híbrido, Markov, Elo de superficie y Elo calibrado. Los resultados de retiros/W.O. permanecen en cobertura; los scores de probabilidad de este candidato se declaran condicionados a partidos completos. La economía debe pasar por el libro de liquidación completo, conservando todas las apuestas. El objetivo de 500 encuentros por circuito es de planificación, no una garantía estadística.

El cálculo de CLV exige el mismo evento, mercado, selección, línea y contrato de liquidación; compara entrada con una referencia anterior al inicio, capturada/actualizada en los últimos 30 minutos. Separa razón de precios y referencia sin margen de ganancia realmente liquidada. Una línea distinta o una cuota posterior al inicio no se acepta como cierre comparable.

Hoy el informe prospectivo tiene **cero observaciones puntuables y métricas no disponibles**. Es el resultado correcto antes de reunir los partidos del periodo. Los controles de fechas no sustituyen una certificación externa de hora; los archivos locales siguen siendo recibos con hash.

## Correcciones al documento recibido

- El plan del titular es de pago y ya se probó su acceso histórico. No se planifica tenis sobre el nivel gratuito de 500 créditos.
- `tourney_date` de Sackmann/TML puede ser la semana del torneo; no habilita sumas diarias exactas de fatiga ni calendario con horas por sí solo.
- p y q de este motor son probabilidades de **punto ganado al saque** por cada jugador. Retención y quiebre de juegos se derivan de ellas; no se intercambian sus definiciones.
- Punto a punto ayuda a evaluar supuestos, pero los conteos de saque permiten el Markov inicial. No hace falta volver a descargar MCP para la primera calibración de líneas.
- [Tennis-Data](https://www.tennis-data.co.uk/data.php) declara que sus archivos son para particulares y excluye productos comerciales o entrenamiento automatizado con bots/IA. No se incorporaron esos archivos; el intento inicial de acceso no obtuvo datos. Se usa la API de pago autorizada.
- [Open-Meteo](https://open-meteo.com/en/pricing) restringe el servicio gratuito al uso no comercial. Datos meteorológicos y condiciones de uso deben distinguirse. No se contrató otro servicio ni se supuso un uso comercial ilimitado gratuito.

## Reproducción y evidencia

Datos nuevos: `data/tennis/extension_20261017/`.

- `ATP_calibration_v2/`, `WTA_calibration_v2/`: protocolo, predicciones 2025, coeficientes y evaluación 2026.
- `ATP_dynamic_v2/`, `WTA_dynamic_v2/`: protocolo, estados y predicciones; `calibrated_controls.json` conserva la comparación adicional con Elo.
- `future_protocol.json`, `future_results.json`, `prospective_report.json`: protocolo congelado, resultados futuros y evaluación.
- `operations_20261016/historical_*.json` y `snapshots/*`: originales/recibos de la muestra histórica de pago.
- `operations_20261016/official/3ccbb75309a84f0bb7582cfdaa38a57f/`: ambos PDF oficiales, texto, hashes y calendario reconciliado.
- `operations_20261016/shadow/2026-10-17T20-38-31.161449+00-00/`: registro con dos controles oficiales aprobados y calibradores adjuntos.

Comandos y requisitos se añadieron al README del módulo. Verificación final: **51 pruebas específicas de tenis aprobadas**, **1.300 pruebas generales aprobadas**, 88 omitidas y dos avisos; el arnés general tardó 75,45 segundos. Docker no está disponible y su comprobación se omitió. Los 12 hashes de artefactos congelados coinciden; el escaneo encontró cero apariciones de la clave en código, recibos e informes.

La comprobación integrada final a las 20:46:19 UTC confirmó dos calendarios oficiales, control Elo calibrado, calibradores adjuntos y coincidencia con los hashes del protocolo. Capturas pagadas de esa comprobación: cero. Saldo actualizado observado: **6.033**. El resumen verificable está en `data/tennis/extension_20261017/verification.json` y la vista local en `resumen.html`.

## Lo que aún depende de datos o de operación futura

1. Ampliar el adaptador oficial a otros torneos y disponer de estado en vivo para retrasos más allá de la hora «no antes de»; revisar nuevas identidades.
2. Reunir inicios/finales reales y sedes históricas para ajustar fatiga/viajes/clima; las herramientas ya rechazan las aproximaciones no acreditadas.
3. Recoger los resultados futuros, cuotas de entrada/cierre y reglas de las casas utilizadas para evaluar beneficio, costes y exposición.
4. Mejorar la aproximación del modelo dinámico en desarrollo, con otra prueba futura si se cambia el candidato.
5. Supervisar una ejecución continua y definir la interfaz diaria/producción. Esta ampliación prepara herramientas locales; no activa por sí sola un servicio, una automatización ni publicación de apuestas.
