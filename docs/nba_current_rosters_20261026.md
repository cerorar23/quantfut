# NBA: plantillas oficiales y fuerza individual — 26-oct-2026

Solicitud del usuario: corregir el efecto de las salidas y llegadas de estrellas y recalibrar los pronósticos en vivo. Base de implementación: `03f4ada`, productor 1.5.0; la copia inicial del chat tenía código antiguo.

## Corrección de datos

Captura pública de las 30 páginas oficiales NBA de equipo: **521 identidades únicas**; **121** tienen equipo distinto al último partido del historial local. Esta cifra compara dos observaciones; no fecha 121 traspasos ni acredita por sí sola disponibilidad.

`current_rosters.py` valida fuente NBA, IDs de equipo/jugador, temporada, cobertura y duplicados. Cada cohorte archiva las páginas originales y recibos con recepción real y hash. Caché de hasta una hora, sin volver a fechar un recibo. Una captura caducada, ambigua o fallida detiene el sellado; no vuelve al equipo antiguo. El lector del panel comprueba la evidencia y la pertenencia de cada jugador.

Con `options.official_rosters=true`, el equipo de un jugador proviene de la plantilla vigente; su historial estadístico sigue al ID oficial aunque aún no haya debutado en el destino. Una salida impide seguir pronosticándolo para el antiguo equipo, incluso si conserva una cotización. Se puede generar el umbral estadístico antes del debut si hay historial personal suficiente. No se equipara pertenencia con salud o minutos confirmados. Las entradas del reporte que contradicen la plantilla se excluyen y se cuentan.

## Candidato de fuerza: resultado medido, sin promoción

Protocolo anterior al cálculo: `apps/nba/nba_roster_strength_protocol.json`. `roster_strength.py` ajusta por separado margen y total a los minutos de cada jugador, con regularización y decaimiento temporal. El valor sigue al jugador, sin transportar el Elo de su antiguo equipo. La rotación dispone de 240 minutos y cada jugador de un máximo de 48; un jugador sin historial tiene una expectativa de minutos de 12 y coeficiente de fuerza cero (media de la liga), con sus minutos desconocidos contabilizados. No es RAPM causal.

La corrección compara la nueva rotación con la rotación de los últimos 20 partidos ya representada en la forma del equipo; evita sumar dos veces toda la producción de una estrella. La selección usa 2024-25; 2025-26 solo evalúa la configuración seleccionada. Todos los partidos de una fecha se predicen antes de observar cualquiera de sus resultados.

Configuración seleccionada: ridge 25, peso 0,25. Evaluación de 2025-26, 1.206 partidos (2.412 observaciones para puntos de equipo):

| Mercado | Brier referencia | Brier candidato | Diferencia | IC95 de la diferencia |
| --- | ---: | ---: | ---: | --- |
| Ganador | 0,200488 | 0,200359 | −0,000129 | [−0,000681; +0,000319] |
| Puntos de equipo | 0,221799 | 0,221667 | −0,000131 | [−0,000452; +0,000217] |
| Total | 0,230782 | 0,230616 | −0,000166 | [−0,000732; +0,000430] |

La regla exige cota superior negativa en ganador y ausencia de empeoramiento concluyente en puntos y total. **No se cumple.** Los primeros 30 días mejoran en ganador (−0,000986) y total (−0,000891), pero empeoran en puntos de equipo (+0,000382). Esos subgrupos son descriptivos y no cambian la regla.

2025-26 ya fue observada en otros estudios. Faltan plantillas históricas acreditadas antes del primer partido: la reconstrucción histórica solo detecta jugadores después de aparecer con su equipo nuevo; sin partido de esta temporada marca la rotación como no observada y usa corrección cero. Las plantillas oficiales actuales resuelven esa pertenencia en vivo, pero no demuestran retrospectivamente la precisión de la corrección antes del debut.

El candidato se guarda en `roster_strength_shadow` (`experimental=true`, `accepted=false`, `affects_published_forecasts=false`) si se activa esa opción. Contiene referencia, candidato y diagnóstico de rotación con el mismo sello temporal; el panel sigue leyendo solo `forecasts`. Esto produce evidencia prospectiva con plantillas actuales sin convertir una mejora pequeña y no concluyente en una mejora validada.

## Validación y operación

Las pruebas cubren transferencia al rival, salida de ambos equipos, equipo cambiado antes del debut, plantilla caducada/duplicada/incompleta, fecha real, caché manipulada, integridad del original, capacidad de minutos, salida/llegada de estrella y exclusión de resultados futuros. La calibración publicada conserva los parámetros del modelo anterior: la corrección de pertenencia es un cambio de datos, no una promoción de fuerza.

La revisión automática rechazó copiar desde el servidor el modelo desplegado y sus partidos a esta carpeta por considerar esa exportación no autorizada. No se realizó. La comparación y el ensayo se preparan para ejecutarse dentro del servidor.

Desplegado como 1.6.0 el 26-oct a las 23:32 UTC, main `74a05cc`, con comparación exacta y ensayo de 542 pronósticos. Registro y reversión en `DEPLOYS.md`. La instrucción posterior del titular requiere activar la fuerza individual, entrenar con la temporada actual y recalcular las publicaciones con nueva versión y fecha; la condición de sombra de este documento describe exclusivamente la 1.6.0.
