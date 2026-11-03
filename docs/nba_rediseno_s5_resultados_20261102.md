# NBA v2 — Sprint 5: referencia de mercado, evaluación única, sellado en cadena y G-fuga (2026-11-02)

Módulos nuevos en `nba.v2`: `referencia`, `evaluacion`, `pit`, `motor_equipo`, `sellado`. Scripts: `apps/nba/ops/evaluar_s5.py` (método de margen) y `apps/nba/ops/g_fuga.py` (solo lectura).

## Qué se construyó

- **`referencia.quitar_margen`:** tres métodos (proporcional, potencia, Shin) para cuotas de dos o más resultados; la referencia pública se acota a [10 %, 90 %] (`limitar_publicacion`).
- **`evaluacion`:** módulo único de métricas (RMSE, Brier, log-pérdida, pendiente e intercepto de calibración, diferencia de Brier con intervalo bootstrap, `informe_binario` con base y estratos, `informe_conteo` con cobertura 80/50 por PIT aleatorizado, MASE y Mincer-Zarnowitz). `evaluar_s3.py`, `evaluar_s3b.py` y `evaluar_s4.py` ya las importan de aquí en vez de definir las suyas (los números de los sprints anteriores no cambian).
- **`pit.instantanea`:** lo que se sabía de un partido en un corte, con huella `version_datos` (sha256). Historia = resultados finales de partidos de fecha anterior; filas propias = solo las visibles en el corte y nunca las de fase `final`. Supuesto explícito: las cajas históricas (`pit = reconstruido`, con `recibido_en` = fecha de adquisición del archivo) se aceptan para partidos de fechas anteriores al pronosticado.
- **`motor_equipo.pronosticar`:** núcleo del Sprint 3 sobre una instantánea; determinista (semilla = id del partido); se niega a pronosticar sin historia.
- **`sellado`:** cadena de hashes en `nba.pronostico` con candado de aviso de Postgres; `objetivo_en` no puede ser posterior al sello; `sellado_en` lo fija el reloj de la base; sellar dos veces lo mismo devuelve el hash existente; `verificar_cadena` detecta alteraciones y enlaces rotos. La base ya rechaza UPDATE/DELETE/TRUNCATE.

## Método de quitado de margen (cierres 2021-26)

Log-pérdida por método (proporcional / potencia / Shin): bet365 ganador (n 3.857) 0,58247 / 0,58230 / 0,58214; hándicap (n 3.603) 0,69259 / 0,69260 / 0,69260; total (n 3.618) 0,69141 / 0,69133 / 0,69136; Pinnacle ganador (n 551) 0,55532 / 0,55381 / 0,55429. Las diferencias son de 0,0002 o menos y los intervalos de Brier incluyen 0: en mercados de dos resultados el método casi no importa. Se fija **proporcional** (más simple, auditable) y queda registrado en `version_modelo`. El sesgo favorito-improbable existe (Shin y potencia ganan algo en favoritos fuertes) pero no es significativo con estos datos.

## G-fuga

200 partidos de 2025-26 en la base real, corte a las 12:00 UTC de cada fecha. Resultado de la primera corrida: 0 diferencias de repetibilidad (misma huella y misma distribución al pedir dos veces la instantánea), 0 fugas de historia, 0 filas finales propias, Brier del ganador 0,210 (sin la alarma de 0,18). La comparación contra una implementación independiente (consulta distinta, sin función punto-en-el-tiempo, ratings por fecha) encontró **1 partido distinto de 200**: el primero de la temporada 2025-26, donde el motor no aplicaba el arrastre de fin de temporada porque el partido pronosticado no estaba en la historia. Corregido en `motor_equipo._ratings` (con prueba); resultado de la repetición abajo.

**Repetición tras la corrección (G-fuga aprobada):** 200 partidos, 0 diferencias de repetibilidad, 0 fugas de historia, 0 filas finales propias, diferencia máxima de la media esperada frente a la implementación independiente 5·10⁻⁵ puntos (el redondeo a 4 decimales del sello), Brier del ganador 0,2103. Corre en el VPS dentro de una transacción de solo lectura con la imagen `nba-motor:df8a151` (`python:3.12-slim` + numpy 2.1.3 + scipy 1.14.1 + el código v2).

## Lo que esta compuerta no cubre

- Es G-fuga del **motor de equipo**; el modelo con jugadores (S3b) y los props (S4) todavía no leen de la instantánea: necesitan alineaciones y minutos esperados dentro de la huella. Se conectan en el Sprint 6 junto con la API, y G-fuga se repite con ellos.
- No se selló ningún pronóstico en `nba.pronostico` de producción: el sellado se probó solo en bases desechables. El primer sellado real será el del motor por partido (`nba-motor`), con la hora de corte definida.
- Las filas históricas `reconstruido` se aceptan por fecha del partido, no por hora real de recepción (límite documentado en `pit.py`).
