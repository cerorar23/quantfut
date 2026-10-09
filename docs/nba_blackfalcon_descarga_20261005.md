# Black Falcon ESPN NBA: descarga y evaluación

Se ejecutó `blackfalcondata/espn-nba-scraper` desde la sesión Apify existente para diez candidatos pendientes: seis regulares, dos playoffs, un play-in y un partido de pretemporada. La ejecución terminó correctamente con **282 filas**, **226 participantes** y **56 DNP explícitos**. Coste mostrado en Apify: **US$0.142**. No se consumieron créditos de The Odds API.

[Ejecución en Apify](https://console.apify.com/actors/c5KjRa7LhBz2Z9j7q/runs/T6I23rByjmvXbCpL2). Dataset `h6KQYI8YQc2NmGnkT`; build `WojHySaScM5AbKTxn`. Límite configurado US$0.25, 400 resultados y 120 segundos; tiempo mostrado de siete segundos. Captura UTC 2026-10-06, fecha local 2026-10-05.

## Qué se comprobó

- Diez IDs ESPN solicitados y recibidos, 282 claves jugador/partido únicas; equipos y fecha NBA compatibles al convertir los instantes UTC ESPN a `America/New_York`. Cuatro fechas UTC corresponden al día siguiente; no se compararon como si fueran fechas locales.
- Sumas individuales de puntos, rebotes y asistencias concordantes con los totales de ambos equipos en los diez candidatos. Los puntos por cuarto más la prórroga combinada suman el marcador; esto no aporta posesiones ni rotaciones cronológicas.
- En los nueve partidos con filas individuales NBA previas se encontraron 247 candidatos únicos por nombre/equipo dentro del partido. **Ninguna discrepancia P/R/A entre participantes**. Hay 53 diferencias raw entre cero NBA y null ESPN para DNP explícitos: se conservaron sin convertir null a cero.
- Las 247 filas de esos nueve partidos ya estaban en el archivo ESPN descargado previamente; sus P/R/A coinciden. Las 35 filas del partido de pretemporada son nuevas respecto de ese archivo.
- `playerActive=false` aparece en 126 filas con participación. No sirve como evidencia de lesión o disponibilidad conocida antes del partido.

## Por qué no completa el histórico validado

Todos los minutos observados son enteros; no hay segundos que permitan reemplazar con precisión los valores NBA malformados como `30:60`. Los totales de minutos enteros llegan a 238, 239 o 241 en equipos de partidos de 48 minutos; que alguno sume exactamente 240 tampoco acredita precisión individual. No se añadieron segundos `:00` ni se modificaron tolerancias.

El candidato de pretemporada `0012500008` / ESPN `401812480`, NYK–PHI del 2025-10-02 en Abu Dhabi, tiene marcador y equipos concordantes pero la referencia NBA etiqueta a ambos como visitantes; falta corroborar la localía y las identidades individuales NBA. `0022500050` conserva la referencia temporal inválida de 47.983333 minutos. Ambos siguen separados.

Black Falcon y el archivo anterior proceden de ESPN: no son corroboración independiente. La descarga histórica tampoco demuestra cuándo estaban disponibles las noticias o datos antes de cada partido. Este piloto no aporta cuotas históricas, reportes médicos originales ni quintetos por segundo.

Por tanto, se conserva todo como **capturado y auditado, sin importación**. El dataset aceptado permanece en **157,375 filas y 5,989/6,150 partidos regulares (97.38%)**. Restan **161 regulares y 75 de otras competiciones conocidos**. El modelo y las puertas de validación no se promovieron.

## Evidencia y continuación

El JSON íntegro está en `apps/nba/.local/raw/apify/blackfalcon_pilot_20261005/items.json`: 927,312 bytes, SHA256 `ad00806ead96f140e955a8d2546d1abea467ad202ac993b37bcec1bdec044796`. En esa carpeta se conservan entrada, plan, log, recibo y captura de pantalla. Auditoría final: `apps/nba/.local/reports/blackfalcon_pilot_audit_v2_20261005.json`; scripts de investigación congelados por hash y ejecución anotada en el registro NBA. La primera auditoría conservada precede a las verificaciones adicionales de DNP y cuartos; el primer intento también detectó la diferencia UTC/local, corregida mediante conversión explícita, no ampliando ventanas de emparejamiento.

El harness completo pasó antes y después: **609 pruebas** en cada ejecución; Docker no está disponible. No hubo cambios en el código del modelo NBA o de fútbol. Revisión propia, sin revisor independiente y sin anclaje externo del registro.

No se amplió a una descarga masiva: el piloto confirmó duplicación de los nueve partidos y la misma limitación de minutos del archivo gratuito. El siguiente paso útil es recuperar minutos con segundos de otra fuente y corroborar la referencia de pretemporada. Black Falcon queda disponible como fuente auxiliar de estadísticas y marcadores, con coste controlado, para huecos que sí aporte.
