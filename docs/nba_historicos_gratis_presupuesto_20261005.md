# Históricos gratuitos NBA y presupuesto de cuotas — 2026-10-05

Sí podemos emplear los patrones de los scrapers revisados para descargar estadísticas históricas gratuitas y completar huecos. Esto no convierte un histórico de resultados en un histórico de precios: ambos datasets son necesarios para evaluar picks con cuotas reales.

| Datos | Fuente y estado | Créditos The Odds API |
| --- | --- | --- |
| Registros individuales y resultados | Archivos gratuitos SportsDataverse y llimllib ya capturados; patrón masivo nba_api como complemento | 0 |
| Jugadas y tiros | Archivos shufinskiy ya descargados; reconstrucción/auditoría pendiente para algunos usos | 0 |
| Quintetos y rotaciones | PBP Stats y reconstrucción PBP; piloto limitado y validación específica | 0 |
| Lesiones conocidas antes del partido | Requieren archivos con fecha de publicación verificable; los módulos revisados no ofrecen ese archivo completo | No resuelto por estos scrapers |
| Líneas, precios Over/Under y evolución histórica de props | The Odds API o archivos de otra fuente con precios y timestamps auténticos; no se acreditó tal dataset en estos dos repos | Presupuesto separado |

## Cobertura aceptada de temporada regular

El dataset individual aceptado contiene 154,058 filas de distintos tipos de competición en las cinco temporadas recientes. Para temporada regular, el contraste con el calendario capturado da:

| Temporada | Partidos aceptados | Partidos del calendario | Pendientes |
| --- | ---: | ---: | ---: |
| 2021–22 | 1,171 | 1,230 | 59 |
| 2022–23 | 1,175 | 1,230 | 55 |
| 2023–24 | 1,159 | 1,230 | 71 |
| 2024–25 | 1,179 | 1,230 | 51 |
| 2025–26 | 1,146 | 1,230 | 84 |
| Total | 5,830 | 6,150 | 320 |

“Pendientes” incluye registros ausentes y partidos excluidos por validación; no significa necesariamente que el archivo fuente no contenga datos. Un histórico completo solo se acredita después de verificar ese censo y reconciliar minutos, puntos, rebotes, asistencias e identidades. No se cambian umbrales para declarar cobertura completa.

## Prueba gratuita real

Se consultó `https://stats.nba.com/stats/leaguegamelog` para jugadores de 2025–26, temporada regular, con parámetros NBA explícitos. Se agotó el tiempo de espera de lectura de 20 segundos. Se conservó el manifiesto, sin reintentos automáticos, consultas a The Odds API, instalación de dependencias o ejecución de los proyectos externos. No se recibieron ni importaron nuevas filas.

Una muestra fallida no prueba que nba_api no funcione desde otra conexión o en otra ocasión. Sí impide afirmar que la descarga masiva oficial quedó funcionando aquí. Las fuentes gratuitas ya recibidas siguen siendo el punto de partida.

## Política de consumo para continuar

1. Completar primero los 320 partidos pendientes de estadísticas regulares con fuentes gratuitas; comparar por ID NBA y no duplicar filas aceptadas. Preservar versiones originales, capturas, hashes y errores. Separar regular, playoffs y pretemporada.
2. Conservar sin cambios la cuota real ya recibida de The Odds API. No ejecutar el backfill externo que asigna precios supuestos de -110 ni usar la fecha de captura como fecha de partido.
3. Para históricos de props, preparar una muestra acotada y reutilizable: 100 partidos × un snapshot × rebotes × una región serían aproximadamente 1,000 créditos si el mercado devuelve datos, más descubrimiento de eventos si hiciera falta. Dos snapshots duplican ese coste. [Tarifa oficial de históricos por evento](https://the-odds-api.com/liveapi/guides/v4/#get-historical-event-odds).
4. Guardar las respuestas de cuotas para reutilizarlas entre experimentos, evitar solicitudes idénticas y coordinar el presupuesto compartido con fútbol. El cliente NBA persistente y la reserva coordinada siguen pendientes; no se declara que ese control esté implementado.
5. Capturar en adelante cambios reales de líneas y noticias permite construir nuestro propio archivo prospectivo; no recupera retrospectivamente lo que no se archivó.

No se promete un porcentaje de ahorro: nuestros históricos estadísticos ya se obtuvieron sin gastar créditos de The Odds API, y el mayor coste restante corresponde a cuotas. En esta revisión se gastaron **cero créditos** y las puertas de validación permanecen pendientes.
