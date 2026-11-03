# Rediseño del motor NBA — Informe final de la Fase 4 y propuesta de promoción (2026-11-03)

Para el titular. Resume lo que existe, lo que se midió, qué compuertas se cumplen y cuáles no, los riesgos y los pasos que propongo para pasar de «piloto en prueba» a «producto». La decisión de promover y la de retirar v1 son suyas.

## 1. Resumen en diez líneas

1. Hay un sistema nuevo, **v2**, en producción en el VPS: base única `nba_datos` con recepción real de cada dato, colectores programados, un motor que cada 5 minutos sella el pronóstico de cada partido 60 minutos antes del salto, API de lectura y web en 6 idiomas (la web **aún no está publicada**).
2. Cada pronóstico (equipo y jugador) es una **distribución completa**, sellada en una cadena de hashes que se puede verificar y que se restaura, se manipula y se detecta (probado).
3. Funciona hacia adelante sin fugas: 100 partidos de equipo y 60 de jugadores reproducidos desde la base real con **0 diferencias** y 0 violaciones de contrato en 5.852 distribuciones.
4. Los props de jugador pasan de un rango del 80 % que cubría el **73 %** (v1.5) a **80,0–81,1 %**; el error frente a la media de 5 partidos es entre 3,7 % y 4,8 % menor (MASE 0,952–0,963) en los dos orígenes con cierres de props.
5. Las probabilidades del equipo son **coherentes** entre mercados (0 violaciones) y están razonablemente calibradas; los jugadores ayudan en las tres temporadas de prueba.
6. **No hay ventaja sobre el mercado**: el modelo es peor que el cierre de bet365 en las tres temporadas de prueba y en todos los mercados, con intervalos que no cruzan 0 (ganador +0,0099 de Brier [+0,0071, +0,0127]; con jugadores +0,0068 [+0,0044, +0,0092]).
7. Con el impacto S3c (RAPM de quintetos) en producción, la mezcla se acerca algo más (margen 14,329 → 14,289 de RMSE; Brier del ganador 0,2035 → 0,2026), sigue sin alcanzar el cierre (14,036; 0,1981).
8. Valor del producto, dicho sin adornos: **pronóstico honesto, calibrado y verificable**, no una ventaja de apuestas. Es coherente con la decisión del titular de que el mercado sea solo referencia.
9. Hay una **dependencia oculta**: el colector de ESPN de v2 lee el libro de `run57`, que escribe un contenedor de v1 (`nba-research-capture-run68-v2`). Retirar v1 sin sustituir eso detendría el calendario y los resultados de v2.
10. Recomiendo promover v2 **por etapas con un periodo prospectivo de evaluación** (sección 7) y retirar v1 solo al final, con la lista exacta de la sección 8.

## 2. Qué se construyó

| Capa | Contenido | Estado en producción |
|---|---|---|
| Datos | `nba_datos` (Postgres 16 propio): 5,45 M datos, 4,33 M cuotas, 17.861 entidades, 6.436 eventos; solo-anexar con disparadores de inmutabilidad; lectura punto en el tiempo; fuentes con prioridad nba_oficial > sofascore > espn; 6.738 partidos con marcador y 142.942 filas jugador-partido resueltas para entrenar | Activa; respaldo cada 6 h + copia diaria al PC |
| Captura | Colectores programados (ESPN, partes de lesiones, cdn.nba.com por Scrapfly con tope de 25 créditos/día, cuotas); cada original con hash | Activa (crons) |
| Modelos | Núcleo de equipo (ratings con descanso), minutos y disponibilidad, impacto por jugador (S3c), props con binomial negativa; entrenados en local, artefactos versionados por huella | Activa (`nba-motor:d73c7c5`) |
| Motor | `nba-motor`: corte fijo a `salto − 60 min`, nunca sella tras el salto, valida contratos, omite y alerta si falta historia, hora o resultados de un equipo | Activa cada 5 min |
| Sellado | Cadena de hashes con candado; verificación pública por API | 192 pronósticos sellados hasta hoy (solo versiones anteriores; los de S3c llegan con el 4-nov) |
| API y web | `/nba/v1` (solo lectura, valida contratos) y `/nba/v2/` en es, en, pt, fr, it, de | **Sin desplegar** |
| Calidad | 235 pruebas de v2; G-fuga contra la base real; contratos Pydantic en las fronteras | — |

## 3. Resultados medidos (origen móvil: 2023-24, 2024-25 y 2025-26)

Diferencias de Brier frente al cierre del mercado (positivo = el modelo peor), conjunto de los tres orígenes:

| | Ganador | Hándicap | Total |
|---|---|---|---|
| Equipo (núcleo) | +0,0099 [+0,0071, +0,0127] | +0,0110 [+0,0075, +0,0144] | +0,0098 [+0,0066, +0,0131] |
| Equipo + jugadores (media) | +0,0068 [+0,0044, +0,0092] | +0,0080 [+0,0050, +0,0110] | +0,0089 [+0,0056, +0,0122] |

- La distancia se achica con más temporadas de entrenamiento (ganador +0,0119, +0,0099, +0,0078).
- Los jugadores bajan el error del margen en las tres temporadas (14,25 → 14,15; 14,02 → 13,86; 14,49 → 14,33). Con S3c, en 2025-26: 14,329 → 14,289.
- Props (2024-25 y 2025-26): cobertura 80,0–81,1 %, error 0,952–0,963 de la media de 5, Brier +0,003 a +0,013 sobre el mercado.
- Una recalibración del ganador con temporadas previas no mejora (pendiente cercana a 1 en promedio); se descartó.

**Frente a v1.5** (2025-26, otro conjunto de partidos, así que solo orientativo): el error del margen de v1.5 era 14,23 y el del total 19,27; el núcleo v2 da 14,49 y 19,08 en 2025-26 (14,55 y 18,96 con todos los partidos del Sprint 3) y con jugadores el margen baja a 14,33 (14,29 con S3c). **v2 no es más preciso que v1.5 en el margen**; sí lo es en el total, en la cobertura de los props (73 % → 81 %) y en coherencia, trazabilidad y reproducibilidad, que v1.5 no tenía.

## 4. Compuertas del plan (estado)

| Compuerta | Estado | Evidencia |
|---|---|---|
| G-fuga | **Cumplida** | 100 partidos de equipo y 60 de jugadores: 0 diferencias de repetibilidad, 0 fugas, mezcla igual a un cálculo independiente (3·10⁻⁴ puntos); 0 violaciones de contrato en 5.852 distribuciones |
| G-coherencia | **Cumplida** | 0 violaciones en los tres orígenes y en las pruebas de propiedades |
| G-equipo | **Parcial** | Ganador: pendiente 1,03–1,19 (equipo) y 1,04–1,18 (mezcla): compatible con 1 dentro del error (≈ 0,1), pero 3 de 6 valores superan 1,1; la recalibración no ayuda. Hándicap y total: pendiente ≈ 0 (el modelo no aporta información que la línea no tenga). Comparación con v1.5: no formalizable (otro conjunto). Diferencia con el cierre: consistentemente peor |
| G-props | **Cumplida** | Cobertura 80,0–81,1 % ∈ [77, 83] y error relativo 0,952–0,963 (≤ 1,00) en los dos orígenes con cierres de props |
| G-disponibilidad | **Cumplida** | Probabilidad de jugar medida con los partes (Brier 0,0266 frente a 0,0289 de la convención inicial); las distribuciones de props se condicionan a jugar y se publican con `p_juega` aparte |
| G-operación | **Cumplida con reservas** | Restauración en 47 s, vuelta atrás en 1 s, alteraciones de la cadena detectadas, simulación de 100.000 trayectorias en ≈ 6 ms por partido, respaldo cada 6 h y copia diaria al PC. Reservas: un solo servidor, alertas nunca vistas salir (solo se comprobaron credenciales) |
| Monte Carlo | **Cumplida** (con cambio) | 100.000 simulaciones: error del 1 % peor 0,43 pp; reproducible bit a bit entre Windows y Linux |
| Estrés | **Cumplida** | Día de 15 partidos con fuentes caídas, estadísticas ausentes, minutos corruptos y 8 procesos sellando a la vez: nada se imputa como 0 ni se sella con datos viejos (3 huecos hallados y corregidos) |

## 5. Lo que cambió respecto del plan (decisiones y correcciones)

- Se cargó SofaScore completo (6 temporadas): 93 partidos nuevos, titulares y la temporada en curso; identidad de jugadores por huella de la caja y auditoría contra la caja oficial (detalle en el informe de la carga).
- Contratos Pydantic estrictos en las fronteras (motor antes de sellar, API antes de servir); el Paso A se definió por sus salidas, de modo que una red neuronal o un boosting serían un retador más, sujeto a las mismas compuertas.
- Equipo a 100.000 simulaciones; props sin Monte Carlo (analíticos).
- Impacto S3c (RAPM de quintetos) aprobado por el titular para producción.
- Compuerta de calibración reformulada: pendiente conjunta compatible con 1 dentro del error, no «en cada temporada».

## 6. Riesgos y límites (de más a menos importante)

1. **Dependencia oculta de v1** (nueva): el colector de ESPN de v2 lee `run57-20261008/data/captures/receipts.sqlite`, que escribe el contenedor `nba-research-capture-run68-v2` (v1). De él salen el calendario, la hora de salto y los marcadores finales. Si se detiene, v2 deja de recibir partidos nuevos y de sellar.
2. **No hay ventaja sobre el mercado.** Cualquier comunicación del producto debe decir «probabilidad calibrada con rangos y sello verificable», no «ventaja» ni «picks».
3. **Pocos sellos todavía**: 192, ninguno aún con S3c ni con los arreglos del estrés; la evidencia prospectiva está por construir (el 3-nov no hubo partidos por las elecciones).
4. **Artefactos estáticos**: impacto y props entrenados con datos hasta el 2-nov-2026; sin reentrenos periódicos se degradan (jugadores nuevos entran con impacto 0).
5. **Hora de salto**: el motor sella solo partidos con hora de salto conocida y nunca después del salto; si la hora llega tarde o no llega, el partido queda sin pronóstico (el motor lo omite y lo informa).
6. **Cobertura de cajas hacia adelante**: las cajas oficiales de cdn.nba.com se capturan solo hacia adelante y con un tope de 25 créditos/día en Scrapfly; el resto de la historia sale de SofaScore.
7. **Un servidor y un disco** (65 % usado); la web y el motor comparten VPS con el fútbol. Mitigado con respaldo de 6 h y copia en el PC.
8. **Alertas por Telegram** configuradas pero no probadas de extremo a extremo (requiere un mensaje de prueba autorizado por el titular).
9. **Proceso**: el 3-nov se desplegó una imagen que arrastraba un artefacto de otra sesión sin que el titular lo hubiera aprobado (se avisó y se regularizó: el titular decidió mantener S3c y se desplegó `d73c7c5`). Regla adoptada: antes de activar una imagen, revisar los commits que lleva dentro.
10. Combinaciones de varios mercados (p. ej. prop + total) no se pueden obtener multiplicando probabilidades (se midió dependencia entre props y total, ver `ops/f42_correlacion_props.py`); el producto no las ofrece.

## 7. Propuesta de promoción por etapas

**Etapa A — Evidencia prospectiva (≈ 5–6 semanas, sin publicar nada nuevo)**
- Dejar sellar todos los partidos de la temporada regular (≈ 1.230 al año, unos 190 al mes) con la versión actual. Cerrada la etapa, medir sobre lo sellado: cobertura del 80 %, calibración con intervalos, Brier frente al cierre, y confirmar que el motor no omitió partidos por causas evitables.
- Criterios de salida propuestos: ≥ 250 partidos de equipo sellados; cobertura de props en [77 %, 83 %]; pendiente conjunta del ganador compatible con 1; 0 violaciones de contrato; < 3 % de partidos con hora conocida omitidos por el motor; alertas probadas.
- En paralelo, **sustituir la dependencia de v1** (riesgo 1): hacer que el colector de ESPN de v2 deje de leer el libro de `run57` y escriba su propio registro, probarlo en paralelo durante una semana contra el origen antiguo y conservar el libro archivado antes de desactivar nada.

**Etapa B — Publicación de la web v2 (tras decidir ruta y cuentas)**
- Elegir la ruta pública (p. ej. `/nba/v2`), integrar con cuentas y bloqueo de pago como el fútbol, crear el usuario de solo lectura de la base, desplegar `nba-api` y revisar el boceto con el titular. Mostrar siempre rangos y «si juega», sin «picks» ni apuestas.
- v1 sigue visible en `/nba` mientras tanto.

**Etapa C — Retiro de v1 (solo con aprobación del titular)** — ver sección 8.

**Etapa D — Mantenimiento**: reentrenar impacto y props cada mes (o cada vez que se incorpore una cantidad relevante de partidos), con origen móvil y G-fuga antes de cada despliegue; revisar cada trimestre el informe de calibración prospectiva; pasar a Fase 4 de nuevo si cambia el mercado o los datos.

## 8. Retiro de v1 — qué se quita y qué NO

**Candidato a retirar** (tras la etapa A y con aprobación): el contenedor `nba-dashboard-run69` y la ruta `/nba` de Caddy (cuando la web v2 la sustituya), el productor `live13` (cron cada 10 min; 1,3 GB de cohortes), `paper-pilot` y la publicación de estadísticas de equipos si v2 las sustituye. Antes de borrar, archivar en el PC (comprimido) `live13`, `paper-pilot`, `dashboard`, `releases`, `operations`.

**No retirar hasta sustituirlo:** el contenedor `nba-research-capture-run68-v2` y `research-capture/run57-20261008` (alimentan el colector de ESPN de v2); el colector de PropLine usa el archivo compartido del fútbol (tampoco se toca).

**Vuelta atrás del retiro:** el archivo en el PC y el respaldo de la base permiten reconstruir v1 en cualquier momento; el retiro se hace en pasos (detener, esperar una semana, borrar).

## 9. Qué necesito del titular

1. ¿Aprueba la **etapa A** (periodo prospectivo de 5–6 semanas con los criterios de salida propuestos)?
2. ¿Aprueba que sustituya la dependencia de ESPN (riesgo 1) antes de cualquier retiro?
3. Cuándo quiere decidir la **ruta y las cuentas de la web v2** (etapa B) y su visto bueno al boceto.
4. ¿Autoriza un **mensaje de alerta de prueba** a su chat privado?
5. La decisión de **retirar v1** se toma al cierre de la etapa A con las evidencias; no se retira antes.
