# Motor de tenis: diseño matemático y requisitos de datos

Fecha: 16 de octubre de 2026. Estado inicial: especificación. Actualización: se implementó y ejecutó una primera versión local, con extracción completa y evaluación retrospectiva. Ver [resultados y límites actuales](tenis_primera_version_y_resultados_20261016.md); el candidato aún no supera la referencia Elo.

## Material revisado y alcance

Actualización de fuentes: se revisaron los repositorios adicionales propuestos por el usuario y se comprobaron muestras de TennisMyLife con estadísticas de ATP, Challenger y WTA de 2026. Es un candidato para ampliar el historial, pendiente de normalización y auditoría temporal. Ver [verificación de fuentes](tenis_fuentes_y_repositorios_20261016.md).

Se leyó completo el archivo adjunto `Texto pegado.txt` (322 líneas), una conversación de siete intercambios. No contiene una tesis adjunta, código del motor, datos de entrenamiento ni resultados reproducibles. Conservamos su objetivo: tenis individual antes del partido, probabilidades coherentes para múltiples mercados y evaluación frente a cuotas disponibles en ese momento.

El usuario eligió The Odds API para las cuotas y Match Charting Project para los datos deportivos. Se descargó y auditó una selección de archivos de una versión fija de Match Charting Project: 11.738 partidos superan los controles iniciales, con 23.476 observaciones jugador-partido. Falta resolver cobertura reciente, agenda completa, equivalencias y permiso comercial. Ver [auditoría de datos](../data/tennis/mcp_20261016/AUDIT_README.md). La documentación local describe un sistema existente de fútbol y un módulo de NBA; este documento define la extensión de tenis sin modificar esos motores.

El planteamiento del adjunto es cuantitativo, bayesiano y markoviano. No describe un algoritmo cuántico. La complejidad o el nombre del método no certifican calidad doctoral: hacen falta hipótesis explícitas, experimentos reproducibles y resultados fuera de muestra.

## Correcciones necesarias al planteamiento original

| Afirmación del adjunto | Corrección para el proyecto |
|---|---|
| El tenis es el deporte más sencillo de predecir | Su puntuación permite una estructura matemática útil; eso no demuestra superioridad predictiva ni económica frente a otros deportes. |
| Las variables subjetivas generan 90% de ruido; el motor supera al 95% de apostadores | El adjunto no aporta evidencia verificable para esos porcentajes. No se utilizarán. |
| Comprimir todas las variables en dos parámetros elimina el ruido | Reduce la dimensión de la salida; no elimina errores, sobreajuste ni incertidumbre. |
| Kalman/Glicko permiten conocer el estado anímico | Pueden representar variación de rendimiento; no identifican su causa psicológica. |
| Defender puntos implica motivación extra | Es una hipótesis a probar; el signo y tamaño del efecto no se fijan de antemano. |
| Usar la cuota de cierre como entrada antes del partido | Solo se permiten precios disponibles al emitir la predicción. El cierre posterior sirve para evaluación. |
| 500 apuestas consolidan la rentabilidad | No existe ese umbral universal. Depende de ventaja, varianza, dependencia y selección de oportunidades. |
| Batir el cierre garantiza ganancias | Es una referencia informativa, no una garantía; depende también de la calidad del cierre y de costes y reglas de liquidación. |
| La columna de ventaja es diferencia de probabilidades y también `p × cuota − 1` | Son cantidades distintas y tendrán columnas separadas. |
| Todos los mercados del mismo partido son oportunidades independientes | Comparten resultados y riesgos; su dependencia debe conservarse. |
| Hay que tener punto a punto para empezar un motor de Markov | Los conteos agregados de saque permiten una primera estimación; el punto a punto ayuda a comprobar supuestos y estudiar contexto dentro del partido. |

## Base académica localizada

- **Demetris Spanias, doctorado de Imperial College London, otorgado en 2015**, *Professional Tennis: Quantitative Models and Ranking Algorithms*. Se consultó la ficha y el resumen institucional, no toda la tesis. Estudia modelos de puntos al saque, rivales comunes y rankings; fundamenta ajustar la calidad de los oponentes. [Repositorio doctoral](https://spiral.imperial.ac.uk/entities/publication/f44f8351-5bdc-4c69-b789-22d7ed3c24da).
- **Martin Ingram, NESSIS 2017**, *A point-based Bayesian hierarchical model to predict the outcome of tennis matches*. Se consultó el texto de la presentación: plantea conteos binomiales, habilidades de saque/resto, superficie, torneo y evolución temporal. Es una presentación científica, no una tesis doctoral. [Presentación](https://nessis.org/nessis17/Ingram.pdf).
- **Stephanie Kovalchik, 2016**, *Searching for the GOAT of tennis win prediction*. Se verificó la referencia en el repositorio institucional; no se completó la lectura del artículo por un fallo de acceso al PDF. No atribuimos a este trabajo las afirmaciones generales sobre ruido del adjunto. [Referencia institucional](https://vuir.vu.edu.au/34652/).

La siguiente formulación es una propuesta de implementación del proyecto; no una réplica empírica ya conseguida de esos trabajos.

## Modelo matemático propuesto

Para cada jugador i, rival j, partido m, superficie s y fecha t:

`Y_i,m | N_i,m, p_i,m ~ Binomial(N_i,m, p_i,m)`

`logit(p_i,m) = μ_circuito + S_i,t − R_j,t + U_i,s − V_j,s + C_torneo,edición + βᵀ X_i,j,m`

- `Y`: puntos ganados al saque; `N`: puntos disputados al saque.
- `S` y `R`: habilidades latentes de saque y resto.
- `U` y `V`: desviaciones específicas de superficie, con información compartida para jugadores con pocos partidos.
- `C`: condiciones del torneo/edición, estimadas solo con información disponible antes del corte.
- `X`: covariables observables anteriores al partido.
- `β`: efectos con regularización hacia cero. Un prior centrado en cero no implica coeficientes exactamente nulos ni selección por significancia automática.

Las habilidades evolucionan con el tiempo. Una opción inicial es una caminata aleatoria gaussiana cuya varianza dependa del tiempo transcurrido. Deben imponerse restricciones de identificación, por ejemplo centrado de efectos, para distinguir intercepto, saque y resto. ATP y WTA tendrán parámetros de población distintos.

La binomial y las probabilidades constantes dentro del encuentro son supuestos iniciales. Se verificarán con predicciones posteriores y análisis de residuos; cualquier extensión de dispersión, fatiga o efecto del marcador se incorporará después de compararla fuera de muestra.

El motor conservará muestras conjuntas de la distribución posterior de `p_A` y `p_B`. Para un mercado M:

`P(M | datos anteriores) = E_posterior[P(M | p_A, p_B, reglas)]`

Esto propaga incertidumbre. En general, evaluar Markov con las medias de p y q no equivale a promediar las probabilidades finales.

### Puntuación y distribución conjunta

Estados mínimos: sets, juegos, puntos, jugador al saque, posición en la secuencia de tie-break y reglas aplicables. Se requieren formato al mejor de 3/5 sets, ventaja/no-ad y configuración de desempates por set y edición. El primer sacador desconocido se marginaliza, sin asignarlo siempre a A.

La programación dinámica produce una distribución conjunta de ganadores, marcadores, juegos por jugador, sets y tie-breaks. Las probabilidades son exactas respecto del modelo y sus supuestos; no son certezas sobre el partido real. Los ciclos de deuce se resuelven analíticamente o mediante estados absorbentes; una truncación numérica debe declarar su error.

Mercados derivados: ganador, ganador de set, marcador en sets, total de sets, hándicap de sets, totales y hándicaps de juegos, juegos por jugador, marcador de set y existencia/número de tie-breaks. Los mercados condicionales de sets que podrían no disputarse requieren sus propias reglas de anulación. Aces, dobles faltas y duración necesitan variables y modelos adicionales: p y q no los determinan.

Retiros, walkovers, descalificaciones y suspensiones deben identificarse. Una distribución de partidos completados no basta para valorar mercados con liquidación distinta ante abandono. La primera versión declarará esa limitación y conservará los eventos excepcionales en los informes de cobertura.

### Variables por prioridad

1. **Base:** saque/resto, calidad del rival, superficie, circuito, evolución temporal, formato y edición del torneo.
2. **Extensiones medibles:** minutos y sets en 7/14/28 días, descanso, inactividad, edad, lateralidad, desplazamiento entre sedes, cambio horario y altitud.
3. **Contexto condicionado a cobertura:** previsión de clima conocida al pronosticar, pista indoor/techo, velocidad de pista con fuente identificada y noticias oficiales de lesión con fecha de publicación.
4. **Hipótesis experimentales:** estilos, H2H regularizado, presión de marcador, puntos defendidos y localía. Cada grupo debe demostrar mejora incremental.

Los desplazamientos entre torneos son aproximaciones, no itinerarios personales conocidos. No se inferirán conflictos familiares ni diagnósticos emocionales de los resultados. Las ausencias de datos tendrán indicadores explícitos; no equivalen a cero cansancio o ausencia de lesión.

## The Odds API: alcance confirmado en documentación

La página específica de tenis enumera Grand Slams, ATP 1000/500 y WTA 1000/500. Ofrece principalmente ganador; hándicaps y totales de juegos tienen cobertura limitada según la casa. No asumimos cobertura de ATP 250, Challenger, ITF o clasificaciones por el solo hecho de contratar el servicio. Las cuotas actuales están disponibles en sus planes y el histórico requiere un plan de pago; la profundidad depende del torneo. [Cobertura de tenis](https://the-odds-api.com/sports/tennis-odds.html).

| Mercado del proyecto | Clave documentada | Tratamiento |
|---|---|---|
| Ganador del partido | `h2h` | Prioridad inicial |
| Hándicap de juegos del partido | `spreads` | Activar donde haya oferta verificable |
| Total de juegos del partido | `totals` | Activar donde haya oferta verificable |
| Ganador del primer/segundo set | `h2h_s1`, `h2h_s2` | Mercado adicional, comprobar por evento |
| Hándicap de juegos del primer set | `spreads_s1` | Comprobar por evento |
| Total de juegos del primer set | `totals_s1` | Comprobar por evento |
| Líneas alternativas de hándicap/total de sets | `alternate_set_spreads`, `alternate_set_totals` | Comprobar por evento |
| Totales alternativos de juegos de sets 1/2 | `alternate_totals_s1`, `alternate_totals_s2` | Comprobar por evento |
| Marcador exacto y habrá tie-break | Sin cobertura confirmada en esta revisión | Mostrar probabilidad del modelo; no inventar cuota ni ventaja |

Que una clave exista en el catálogo no garantiza una oferta para cada partido o casa. [Catálogo oficial de mercados](https://the-odds-api.com/sports-odds-data/betting-markets.html).

### Captura prevista

- Descubrir torneos con `/v4/sports`; no fijar permanentemente una lista de torneos activos.
- Capturar `h2h,spreads,totals` con `/v4/sports/{sport}/odds`.
- Consultar `/v4/sports/{sport}/events/{eventId}/markets` para mercados recientemente vistos por casa y `/events/{eventId}/odds` para sus cuotas. El inventario puede crecer al acercarse el comienzo.
- Consultar los endpoints históricos si el plan los permite. Los snapshots devueltos son los disponibles en o antes de la hora solicitada; registrar su hora real.
- Guardar `event_id`, torneo, nombres originales, inicio previsto, casa, mercado, selección, línea, cuota decimal, actualización del proveedor, recepción propia, estado, respuesta original y versión de normalización.
- Registrar las cabeceras de consumo y limitar frecuencia según plan, torneos, regiones y mercados. No se fija un presupuesto de llamadas sin conocer la cuenta.

Fuentes: [API v4](https://the-odds-api.com/liveapi/guides/v4/), [histórico de cuotas](https://the-odds-api.com/historical-odds-data/).

## Datos deportivos que faltan

The Odds API queda asignada a precios y eventos. La documentación revisada no acredita la historia completa de saque/resto necesaria para entrenar esta formulación. Se necesita un segundo conjunto de datos o proveedor.

| Bloque | Campos requeridos | Prioridad |
|---|---|---|
| Identidad | ID estable de jugador, nombre, circuito; equivalencias entre fuentes | Indispensable |
| Encuentro | ID, torneo/edición, fecha/hora con zona, ronda, participantes, superficie, indoor, formato y reglas | Indispensable |
| Resultados | Marcador por set, ganador, estado final, retiro/walkover y correcciones | Indispensable |
| Saque de cada jugador | Puntos de servicio disputados y ganados; preferentemente primeros servicios dentro, puntos ganados con primero/segundo y sus denominadores | Indispensable |
| Estadística adicional | Aces, dobles faltas, juegos de servicio, break points enfrentados/salvados; definición de cada campo | Deseable |
| Carga | Inicio/fin real o duración, partidos anteriores incluyendo qualies cuando estén disponibles | Segunda etapa |
| Perfil y sedes | Nacimiento, lateralidad, altura; coordenadas y altitud de la sede | Segunda etapa |
| Punto a punto | Orden, sacador, ganador del punto, marcador, desempate y correcciones | Validación de supuestos y extensiones |
| Trazabilidad | Publicación/actualización en origen, primera recepción propia y versión | Indispensable para auditoría temporal |
| Condiciones | Previsión meteorológica archivada y hora de emisión; lesión oficial con fecha | Extensiones |

Pedir inicialmente 5–10 temporadas si están disponibles, desglosando cobertura por circuito, torneo, año y campo. Es una meta de adquisición, no un mínimo que garantice precisión. Los porcentajes sin denominadores son insuficientes para ponderar correctamente la evidencia.

**Fuentes a evaluar:** Sportradar documenta resultados, estadísticas y secuencias de puntos con profundidad variable por competición. API-Tennis documenta calendario/resultados, estadísticas y punto a punto; sus ejemplos incluyen puntos ganados al primer saque con numerador y denominador. En ambos casos faltan muestras reales, presupuesto, historia efectiva y derechos de uso del plan. [Sportradar](https://developer.sportradar.com/tennis/docs/tennis-ig-overview), [API-Tennis](https://api-tennis.com/documentation).

El adjunto sugiere el repositorio ATP de Jeff Sackmann; su URL original no fue accesible en la primera revisión. Posteriormente el usuario indicó Match Charting Project, que sí fue accesible directamente. Se contrastaron metadatos, puntos y estadísticas de esa fuente. Su licencia publicada es CC BY-NC-SA 4.0; no se acredita permiso para el servicio comercial. Tampoco sustituye un historial completo y reciente del circuito. Detalle en la auditoría enlazada al inicio.

## Probabilidades, cuotas y evaluación

Para resultados exhaustivos y mutuamente excluyentes del mismo mercado, línea, casa y momento, una referencia básica sin margen es `q_k = (1/o_k) / Σ_j(1/o_j)`. Es una aproximación; se compararán métodos de eliminación de margen. No se normalizan selecciones de líneas diferentes.

Se reportan por separado:

- Diferencia de probabilidades: `p_modelo − q_mercado`, en puntos porcentuales.
- Retorno esperado por unidad: `p_gana × (cuota − 1) − p_pierde`, descontando costes aplicables. Con solo ganar/perder se reduce a `p × cuota − 1`.
- Probabilidad de devolución/anulación, cuando corresponda. Líneas de cuarto se descomponen en las dos apuestas subyacentes.

El panel del adjunto confunde esas dos primeras medidas: con p = 0,61 y cuota = 1,95, el retorno esperado simple es 18,95%, mientras que la diferencia respecto de 1/1,95 es aproximadamente 9,72 puntos porcentuales. Además, 1/cuota aún incluye el margen de la casa.

La validación debe incluir:

1. Entrenamiento y prueba en orden temporal; ajuste de variables e hiperparámetros dentro de ventanas anteriores al test final.
2. Referencias: ranking, Elo general, Elo por superficie y probabilidades de mercado disponibles al corte. No se trasladan resultados de fútbol a tenis.
3. Log-loss, Brier y calibración por circuito/superficie/mercado; calidad de distribuciones de juegos y sets, no solo ganador.
4. Pruebas de eliminación de grupos de variables; regularización y control de múltiples búsquedas para no seleccionar mejoras por azar.
5. Intervalos de incertidumbre que respeten dependencia entre mercados de un partido y entre encuentros cercanos; bootstrap por bloques como opción.
6. Evaluación económica con cuotas realmente disponibles, reglas de abandono, comisiones, precio ejecutable y latencia. Cierre y rentabilidad se reportan como métricas distintas.
7. Periodo prospectivo con predicciones guardadas antes del inicio, sin presentar un resultado retrospectivo como desempeño operativo.

Un histórico adquirido hoy no demuestra por sí solo cuándo estuvo disponible cada corrección. Si no hay fecha real del encuentro, no se usará el orden de las filas para simular conocimiento cronológico. Nunca usar clima observado después como si fuera la previsión disponible antes.

Las probabilidades de varios mercados se derivarán de la misma distribución conjunta; calibrarlas independientemente puede romper esa coherencia. Cualquier ajuste deberá preservar restricciones o medirse explícitamente por coherencia.

## Entregables de construcción y condiciones de aceptación

1. **Auditoría de cobertura:** muestra de cuotas y estadísticas, tasa de campos ausentes, equivalencias y consumo estimado. No entrenar un modelo rico si faltan sus variables esenciales.
2. **Motor de puntuación:** pruebas de normalización, simetría al intercambiar jugadores, continuidad del saque, desempates, formatos y comparación con simulación independiente. La lógica matemática puede desarrollarse con ejemplos sintéticos identificados como tales.
3. **Modelo base entrenado:** parámetros guardados, cortes temporales, semillas, versiones de datos y comparación con referencias simples.
4. **Extensiones experimentales:** añadir grupos de variables solo cuando aporten una mejora estable fuera de muestra.
5. **Panel de varios mercados:** probabilidad, incertidumbre, cuota justa, cuota observada, hora, diferencia de probabilidades, retorno esperado y calidad de datos. Estados separados: sin cuota, datos insuficientes, evaluable y señal experimental.

La implementación posterior ya dispone de candidatos entrenados ATP/WTA y evaluaciones iniciales; no hay rentabilidad demostrada ni candidato aprobado para publicar picks. The Odds API sigue siendo la fuente elegida de precios, pendiente de integración y presupuesto de consultas. Los resultados efectivos y las limitaciones prevalecen sobre este diseño inicial.

## Información que debe aportar el usuario

- Nombre del plan de The Odds API, créditos mensuales y si dispone de histórico.
- Casas que desea comparar y país de uso, para elegir cobertura efectiva.
- Si ya posee datos de tenis o una API de estadísticas: nombre, documentación y una muestra sin credenciales.
- Si dispone de otro estudio/documento distinto de la conversación adjunta: archivo o enlace y resultados que desea reproducir.

La clave de API será necesaria para una prueba autenticada, pero no hace falta pegarla en el chat para elegir la arquitectura. Puede configurarse después en el entorno local sin mostrarla en informes.
