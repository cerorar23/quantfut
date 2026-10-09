# NBA — complemento de pretemporada y arranque

**Versión:** 1.0 · **Fecha del cliente:** 4 de octubre de 2026.
**Estado:** diseño listo para iniciar preparación local; implementación pendiente.

Complementa [el plan maestro F0–F9](nba_plan_fases_auditable.md) y su
[registro de auditoría](nba_plan_fases_auditoria.json). No sustituye sus
criterios ni declara fases aprobadas. El registro conserva los hashes de la
base original y añade este documento como complemento versionado.

## Objetivo inmediato

Aprovechar la pretemporada para capturar observaciones actuales, probar el
pipeline y generar pronósticos experimentales cuando existan datos y un
baseline válido. La pretemporada empezó el 3 de octubre; la temporada regular
comienza el 20 de octubre de 2026. [Fechas oficiales NBA](https://www.nba.com/news/key-dates?os=w).

Antes del inicio se busca un MVP prepartido reducido: minutos y una familia
de estadísticas individuales. No se garantiza completar F0–F6 en los días
disponibles. Una captura utilizable o un prototipo local son entregas parciales
que deben identificarse como tales, sin anunciar operación completa.

## Orden de implementación y evidencia

| Paso | Fases del maestro | Entrega comprobable |
|---|---|---|
| 1. Preparación | F0/F1 | Arnés operativo, configuración NBA y almacenamiento aislados; decisiones pendientes identificadas |
| 2. Acceso y cobertura | F2/F3 | Ensayo real de descarga, inventario de partidos/fuentes, raw versionado y reanudación comprobada |
| 3. Históricos y captura actual | F3 | Box scores/minutos recientes; calendario, equipos y disponibilidad actuales; pretemporada etiquetada |
| 4. Pronóstico básico | F4/F5 | Baselines de minutos y una estadística, evaluación temporal, incertidumbre y abstenciones registradas |
| 5. Ensayo de entrega | F6 | Pronósticos registrados antes del resultado y notificaciones experimentales cuando el destino esté configurado |
| 6. Confirmación | F7 | Candidato congelado, evidencia prospectiva y revisión durante la temporada regular |

Antes de escribir código debe resolverse el arnés exigido por `CLAUDE.md`.
No se supone que acceso a documentación implica acceso real a datos.

Priorizar históricos deportivos 2023–24 a 2025–26; ampliar a 2021–22 según
cobertura y recursos. La captura actual puede avanzar mientras se completa
el histórico. PBP, tracking, cuotas y noticias históricas tienen inventarios
de cobertura propios; su ausencia no debe representarse como cero ni como
datos reconstruidos auténticos.

No empezar buscando rendimiento en todos los mercados. Escoger la primera
familia por cobertura, registrar la elección y evaluar después. Se pueden
estudiar pronósticos deportivos sin cuotas históricas, pero no atribuirles una
ventaja respecto a precios que no se observaron.

## Tratamiento estadístico de pretemporada

- Guardar `season_id`, `season_type`, IDs de partido/jugador/equipo, fuente,
  primera recepción UTC y versiones de las observaciones. Separar
  `preseason`, `regular_season` y `playoffs` en datasets y métricas.
- Usar la pretemporada para observar disponibilidad, roles y rotaciones.
  No convertir los minutos de un amistoso directamente en minutos esperados
  de temporada regular. Las restricciones deben tener fuente y fecha.
- Si hay pretemporadas históricas comparables, contrastar una variante sin
  pretemporada y otra que incorpore esas señales. Elegir variables y peso
  con cortes temporales anteriores; no ajustar con los resultados futuros.
- Si esa cobertura falta, usar las observaciones para escenarios de contexto
  y declarar su incertidumbre. No afirmar mejora predictiva por incorporarlas.
- Evaluar minutos y distribución de la estadística con baselines sobre el
  mismo universo, pérdidas predictivas e intervalos. Informar DNP, faltantes
  y abstenciones; no excluir errores después de observar el resultado.
- Mantener las métricas de pretemporada separadas. Sus pruebas de entrega
  no sustituyen la confirmación del modelo para temporada regular en F7.

Cada pronóstico conserva su corte temporal, versiones de datos/modelo y
registro previo al resultado. Los datos históricos recibidos hoy no prueban
qué noticia estaba disponible antes de un partido pasado. Un replay sigue
siendo retrospectivo, aunque su salida tenga hash.

## Decisiones y límites operativos

Se puede iniciar trabajo local con fuentes de acceso permitido, inventario
de cobertura y salidas a archivos. Presupuesto/proveedores de pago,
operadores y destino/credenciales de Telegram se resuelven antes del trabajo
que dependa de ellos. Estos pendientes no bloquean el diseño ni el ensayo
local; tampoco autorizan gasto o envío a un destino supuesto.

Aplicación, datos, dependencias y credenciales NBA siguen separados de
fútbol. Los experimentos avanzados se mantienen en el backlog. Cada fallo de
acceso, falta de datos o criterio incumplido debe constar en su ejecución y
en la decisión de puerta correspondiente. El calendario no rebaja un criterio.

**Criterio de preparación del plan:** orden de tareas, entregas, evidencia,
dependencias y pendientes documentados. **Criterio de funcionamiento del
sistema:** ejecuciones reales y puertas aprobadas para el alcance anunciado.
El primero está documentado; el segundo todavía está pendiente.
