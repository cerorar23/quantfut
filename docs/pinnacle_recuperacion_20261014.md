# Recuperación de Pinnacle — 14 de octubre de 2026

**0 cierres nuevos recuperados; siguen pendientes 6.185 partidos.** No hubo
escrituras en producción, nuevas altas, entrenamiento ni activación de modelos.
La descarga funciona, pero las fuentes examinadas no devolvieron las cuotas que
faltan. La recuperación no está completada.

## CSV gratuitos: corrección del diagnóstico

Instantánea de producción a las 19:01:51 UTC, transacción `REPEATABLE READ READ ONLY`:
20.855 partidos terminados desde 2024, 23 competiciones activas, 6.185 sin cierre
completo. De estos, 1.457 corresponden a México, Argentina, Brasil y MLS.

Se descargaron 60 CSV: cuatro temporadas (2324–2627) de las 13 ligas principales
y los archivos completos de las ocho ligas extra. Todos respondieron correctamente.
Se guardaron originales, URL, recepción real y SHA-256.

Las **14.381 ternas explícitas PSCH/PSCD/PSCA válidas desde 2024 ya estaban en
la base**. El ensayo encontró cero candidatos nuevos, cero asociaciones rechazadas
y cero precios contradictorios entre duplicados de fuente. No se aceptaron cuotas
de apertura como cierre. Se exigieron nombres/alias exactos normalizados del mismo
país, partido único de la misma competición a ±36 horas y marcador final igual.

| Archivo | Filas totales | Con Pinnacle completo | Última fecha con Pinnacle |
| --- | ---: | ---: | --- |
| México | 4.752 | 4.437 | 2025-10-27 |
| Argentina | 6.414 | 5.928 | 2025-12-14 |
| Brasil | 5.619 | 5.275 | 2025-12-07 |
| MLS | 6.236 | 5.800 | 2025-12-06 |

Los 4.437 mexicanos son cobertura de TODO el histórico. **No prueban que los
1.457 huecos recientes se puedan recuperar reimportando estos archivos.**
El importador general omite partidos existentes y existe un cargador específico
`completar_cierres`, pero en este ensayo todos los cierres disponibles ya estaban
almacenados. No se ejecutó ninguna carga de cuotas.

Además, la propia fuente advierte que las cuotas de Pinnacle, incluidas las de
cierre, pueden estar desactualizadas desde el 23-jul-2025. Una columna poblada
no certifica frescura respecto al cierre real. No se revalidó la elegibilidad
de todos los cierres existentes.
[Advertencia de Football-data](https://www.football-data.co.uk/data.php).

## OddsHarvester y ZenRows

Se añadió `scripts/oddsharvester_zenrows.py`: usa la clave existente en memoria
y conecta Playwright por CDP a Browser Sessions, con IP según país y sesión.
No requiere una lista de proxies HTTP. No se compraron planes ni créditos.
La primera navegación tuvo un error de certificado del destino; se resolvió
con una opción explícita limitada al navegador remoto. WSS conserva validación TLS.

La instalación antigua 0.15.0 permanece intacta. Las pruebas CA/CL y Champions
usaron una copia aislada de la versión actual **0.20.0**, commit `5bbc046`.

| Prueba | Resultado |
| --- | --- |
| Premier 2025/26, una página, GB | 51 enlaces históricos |
| Tres partidos Premier, GB, Pinnacle FT e historia | Tres fichas; cero ternas Pinnacle |
| Crystal Palace–Arsenal, 24-may-2026, CA | Otras casas visibles; cero Pinnacle |
| Mismo partido, CL y espejo CuotasAhora | Otras casas visibles; cero Pinnacle |
| Champions 2024/25, una página, CA | 50 enlaces históricos |
| PSG–Inter, 31-may-2025, CA | Equipos, fecha y 5–0 correctos; cero Pinnacle |

Se conservaron los HTML renderizados y recibos por hash. Estos resultados no
prueban ausencia en toda región, cuenta o fecha de OddsPortal. Sí muestran que
las muestras no acreditan cobertura para lanzar el lote completo. Un éxito de
OddsHarvester al leer una ficha puede contener cero cuotas de la casa pedida.
El adaptador ahora cuenta las ternas Pinnacle FT válidas y termina con código 3
si el JSON solicitado para Pinnacle no contiene ninguna. No se sustituyó la casa.

Documentación: [OddsHarvester](https://github.com/jordantete/OddsHarvester),
[ZenRows con Playwright](https://docs.zenrows.com/browser-sessions/get-started/playwright),
[país](https://docs.zenrows.com/browser-sessions/features/country) y
[duración de sesión](https://docs.zenrows.com/browser-sessions/features/session-ttl).

## Archivos entregados

Directorio: `.local/pinnacle_recovery_20261014/`.

- `pinnacle_cierres_fuente_emparejados.csv`: 14.381 filas con cuotas publicadas
  por la fuente, todas ya presentes en la base. No son incorporaciones nuevas.
- `pinnacle_pendientes.csv`: 6.185 partidos pendientes de conseguir precio.
- `pinnacle_cierres_recuperables.csv`: encabezado, cero candidatos nuevos.
- `informe.json`, `database-before.json`, originales, recibos y JSON/HTML de
  OddsPortal: evidencia y reproducción del ensayo.

El CSV de precios lleva league_id del catálogo, kickoff UTC canónico, nombres
de la fuente, home/draw/away decimales, Pinnacle, origen, URL y recepción real.
Se conservan fecha/hora originales por separado sin inventar su zona horaria.
La fecha de descarga no acredita disponibilidad previa al partido histórico.
El CSV se comprobó también con la librería de hojas de cálculo incluida.

Pruebas nuevas: exclusión de apertura y precios inválidos, resultado
contradictorio, asociación ambigua, cierre parcial, cierre ya completo, corrupción
de originales y falsa equivalencia entre éxito del scraper y cobertura Pinnacle.
Verificación final del proyecto: 1.123 pruebas pasaron y 36 quedaron omitidas,
incluidas las integraciones que requieren servicios externos. Los ocho casos
nuevos pasaron. Los 60 originales y los tres CSV finales tienen hashes verificados
en `verification.json`; ninguna credencial aparece en los archivos nuevos versionables.

Saldo observado de la cuenta existente a las 19:16:54 UTC: límite 5.000, usados
4.548, restantes 452. Es una cuenta compartida: no se atribuye todo el consumo
a esta tarea. Una comprobación de arranque de la CLI sin clave creó accidentalmente
una cuenta gratuita separada y guardó su credencial fuera del repositorio. No se
usó para obtener datos; las pruebas de scraping usaron la clave existente.

Pendiente: una fuente o acceso que entregue Pinnacle para estas fechas, una muestra
validada y presupuesto suficiente antes de procesar los 6.185. No se generaron
precios estimados ni se declaró desbloqueado el modelo de residuo.
