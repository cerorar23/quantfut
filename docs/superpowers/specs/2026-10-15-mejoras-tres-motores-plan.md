# Mejoras de los tres motores — plan tras el 1-nov

Fecha: 2026-10-15. Origen: dos documentos del usuario del mismo día,
«Recomendaciones para mejorar los tres motores» y «Revisión del plan de mejora»
(correcciones al primero), contrastados con el código de `main` y con
producción. Decisión del usuario: **no se toca el motor hasta el reentrenamiento
del 1-nov**; todo lo de aquí se ejecuta después, en el orden de la sección 6.
Arquitectura de partida: `docs/MOTOR_Y_PICKS_AL_DETALLE_20261015.md` (PR #7).

## 1. Qué ya existe o ya está planificado

| Recomendación | Estado verificado |
|---|---|
| Factores dentro de λ/μ antes de la matriz de marcadores, aprendidos y con respaldo si falta el dato | Diseño de la capa de ajuste (F1, `qf.model.ajuste`): `λ = λ_base·exp(...)` |
| Alineación y calidad del once / reemplazos | F4 (bloque `xi`); el XI simple ya pasa la puerta de F1 (ΔRPS −0,0013, 9 de 12 ligas) **frente al A anterior, no frente a B** |
| Lesiones, sanciones, regresos | F3 (bloque `bajas`); no repetir una ausencia ya reflejada en la fuerza del equipo |
| Árbitro, faltas, tarjetas | F5 (bloque `arbitro`), evaluado en el motor y el mercado que le corresponden |
| Clima, altitud, viaje, sede | F6 (bloque `sede_clima`), solo con datos disponibles al publicar |
| Revisar al confirmarse el once sin reescribir lo vendido | F7 (sello tardío, un lote por partido, versiones con hora) |
| Anclaje de B solo con 1X2 | **Resuelto**: `alta_prob.py:186` ajusta con 1X2 **y** la línea de goles de Pinnacle, ρ fijo del modelo activo |
| Parley/escalera con patas del mismo partido | **Resuelto** dentro del ticket (un partido por pata). Queda medir la exposición al mismo partido **entre productos** (F10) |
| Alternativas por partido en vez de descartarlo | Existe en alta probabilidad: por partido compite toda la familia de mercados y se publica el de menor probabilidad dentro de la banda |
| Medir rentabilidad aparte del acierto | Existe: `alta_prob.historial()` → `rendimiento_ref` |

## 2. Rentabilidad medida y cómo interpretarla

Producción, 15-oct, solo picks con cuota de referencia guardada:

| Producto | n | Prometido | Real | Cuota media | ROI a referencia | Equilibrio a esa cuota |
|---|---|---|---|---|---|---|
| Alta probabilidad base | 91 | 82,6 % | 83,5 % | 1,164 | −2,96 % | ≈85,9 % |
| Ampliada, banda 73–95 % | 223 | 81,4 % | 78,0 % | 1,190 | −7,52 % | ≈84,0 % |

- Compatible con el margen de la casa (la probabilidad es Pinnacle sin margen;
  línea de **acierto** decidida el 2026-10-05), pero la tabla sola no prueba la
  causa: también caben variación, calibración, diferencia entre cuota de
  referencia y cuota accesible, y sesgo del subconjunto.
- **Sesgo del subconjunto, causa conocida:** la cuota de referencia de doble
  oportunidad se captura desde el 12-oct y la de hándicap asiático desde el
  14-oct (`ingest/af_odds.py`). Los picks anteriores de esos mercados no tienen
  `ref_price` (49 hándicap y 28 doble oportunidad solo en la base). El
  subconjunto con cuota está cargado hacia goles y córners.
- Antes de concluir: calcular apuesta a apuesta (no acierto medio × cuota
  media); reglas exactas de nulos y medias liquidaciones en hándicap y totales
  asiáticos; apuesta fija frente a importes variables; si el cliente podía tomar
  esa cuota a esa hora; incertidumbre agrupada por partido y jornada.
- 223 picks no bastan para afirmar un deterioro estable de la ampliada, y 91 no
  prueban una calibración perfecta de la base. Se vigila con el control semanal.
- **Dos vías de rentabilidad:** mejor probabilidad (F8) o mejor precio para la
  misma probabilidad. La segunda ya está en los picks de valor y la sombra. La
  comparación de precios entra en la evaluación (F9), **no** como filtro nuevo.
- Los informes separan tres cosas: precisión probabilística, porcentaje de
  acierto y rentabilidad a precios realmente disponibles. El CLV es diagnóstico,
  no garantía de ganancia.

## 3. Fases nuevas

### F8 — Conectar el modelo propio con los picks (mezcla aprendida)

Sin una ruta hacia B, mejorar A no cambia ningún pick vendido. Pero encender
`meta.py` no basta: la combinación tiene que demostrar información **adicional a
B contemporáneo**, no solo mejorar al A anterior. Una mezcla bien entrenada puede
aprender a bajar el peso de A, pero **no evita el doble conteo por sí misma**:
una lesión puede estar a la vez en la cuota y en la fuerza estimada.

Condiciones:
- Predicciones honestas: pesos aprendidos con predicciones históricas generadas
  sin conocer el resultado ni partidos futuros.
- Mismo momento: A y B con la información disponible a la misma hora de
  publicación (03:00 o sello de F7).
- Peso cero permitido por familia de mercado (1X2/doble oportunidad, goles,
  ambos marcan/marca un equipo, hándicap), sin subdividir hasta muestras pequeñas.
- Periodo final reservado: pesos y variantes se eligen sin tocarlo.
- Coherencia entre mercados: combinar distribuciones de marcadores (nivel λ/μ),
  no pesos independientes que hagan incompatibles 1X2, doble oportunidad y
  hándicap; si no, comprobar y corregir la coherencia.
- Córners y tarjetas: C se evalúa junto a su propio mercado; el A de goles no se
  traslada automáticamente a esos productos.
- Alternativa a probar: residuo frente al mercado (`model/residual.py`, apagado).
- Antecedente metodológico: Egidi, Pauli y Torelli (combinar históricos y cuotas);
  respalda probarlo, no demuestra que funcione aquí.
- Se evalúa **en paralelo sin cambiar los picks vendidos**; se activa por
  bandera al final de la secuencia (sección 6).

### F9 — Evaluación en dos preguntas, a volumen constante

1. ¿Mejoran las probabilidades sobre los mismos partidos, mercados y horarios,
   sin cambiar la selección?
2. ¿Mejora lo publicado al comparar políticas de selección con la misma
   cantidad diaria y una distribución comparable de cuotas y mercados?

Cambiar a la vez horario, modelo y selección impide saber qué produjo la mejora.
Versiones:

| Versión | Qué mide |
|---|---|
| B con horario actual (03:00) | Referencia de la operación actual |
| B actualizado al horario de F7 | Efecto de publicar más cerca del partido |
| A con contexto + B, al horario de F7 | Aporte del modelo frente a un mercado igual de actualizado (**prueba decisiva**) |
| Lo anterior + nueva selección | Aporte de elegir otros picks con volumen y condiciones comparables |

- Ganar a una referencia antigua puede ser solo ventaja de información temporal.
- Volumen comparable no obliga a inventar probabilidades altas si la oferta del
  día es peor: se registran los días con cobertura insuficiente y se comparan
  versiones sobre el mismo universo disponible.
- Validación cronológica, periodo final reservado, solo datos conocidos al
  publicar (el cierre es comparación posterior).
- Acierto y calibración por banda separados de ROI a cuota accesible y CLV;
  incertidumbre agrupada por partido/jornada (150 mercados de un partido no son
  150 observaciones). Ablación por grupo (XI, bajas, descanso, clima, árbitro).
- **Puerta reforzada** (la regla «≥2 ligas» queda como comprobación inicial):
  magnitud de la mejora con su intervalo y número de partidos; estabilidad en
  periodos posteriores distintos y sin deterioros relevantes por liga;
  comparación con una alternativa sencilla; registro de cuántos factores y
  configuraciones se probaron (selección múltiple); criterios fijados antes de
  ver el periodo reservado.
- Alcance: el volumen constante se exige a cambios que alteren probabilidades o
  selección. Trazabilidad (F7) y etiquetas de la app (F11) solo necesitan
  verificación funcional y de claridad.

### F10 — Selección y exposición

- Con F7/F8, si cambia la estimación de un partido, recalcular sus mercados y
  compararlos con el resto de la jornada antes de descartarlo; registrar qué
  candidato ganó y por qué.
- Exposición al mismo partido **entre productos** (alta probabilidad, escalera,
  parley): medirla y mostrarla, sin convertirla en límite de cantidad.
- Correlación entre partidos en parley/escalera (misma liga, hora, escenario).
- Volumen diario en `/control` junto al acierto y al ROI.

### F11 — Lo que ve el usuario en la app (no toca el motor)

- Origen de cada cifra: modelo deportivo, mercado o combinación validada.
- Indicador de datos **descriptivo**, no otra probabilidad. Nada de «calidad
  92 %» sin definición verificable:

| Dimensión | Ejemplo |
|---|---|
| Confirmación | Alineación confirmada o probable; bajas confirmadas o pendientes |
| Actualidad | Hora de la última actualización de los datos relevantes |
| Cobertura | Jugadores, descanso, clima y demás factores usados o ausentes |
| Origen | Modelo, mercado o combinación |

- Los 6 idiomas en el mismo cambio, incluidos los estados «falta el dato» e
  «información pendiente».

### F12 — Factores sin fase todavía

| Factor | Datos | Nota |
|---|---|---|
| **Descanso y partidos acumulados** (candidato cercano, bajo coste) | Calendario; **falta** el de copas y otras competiciones (sección 5) | Empezar por descanso y carga del equipo; minutos individuales cuando haya cobertura. Sin calendario completo un equipo que jugó Libertadores parece descansado |
| Ida/vuelta y marcador global | Ronda en el original de FotMob; global derivable | Guardar global, condición de local y reglas de la competición y temporada. Remontar = contexto de escenarios, no bono de victoria |
| Necesidad de puntos / clasificación | Derivable de `matches` | Reglas de cada torneo (Apertura/Clausura, conferencias, playoffs) |
| Entrenador | **Está en el original de FotMob por partido** (id, nombre) | Sin bono automático por técnico nuevo (regresión a la media). Ver qué se mide antes de usarlo |
| Estilos | Estadísticas por partido en el archivo FotMob (centros, posesión, faltas, balón largo, xG a balón parado, toques en el área) | Prioridad en córners (C). Sin puntuaciones subjetivas sacadas de noticias |
| Motor C ampliado | Archivo FotMob + árbitro (F5) | Binomial negativa como referencia; mejorar media **y** dispersión |
| Portero, fichajes, cambio de estadio | Por decidir | Menos peso al historial directo si cambian plantillas |

### Tarea suelta antes de encender picks de valor

`picks.select_daily()` recorre `predictions` (13 ligas con modelo); la sombra
mide 22. Alinear la cobertura antes de `PUBLISH_PICKS_ENABLED=1`.

## 4. Versiones y exposición

Con F7 se conserva la predicción original, la información disponible al
publicarla y las revisiones posteriores; ninguna revisión reemplaza el historial
vendido.

## 5. Datos: qué tenemos y qué falta descargar (medido 15-oct)

Cobertura en las 13 ligas con modelo, partidos jugados desde julio de 2023:

| Dato en tablas del motor | 23-24 | 24-25 | 25-26 |
|---|---|---|---|
| XI (`lineups_historicas`/`lineups`) | 0 % | 0 % | 87 % |
| Minutos de jugador (`estadisticas_jugador`) | 0 % | 2 % | 91 % |
| Pinnacle 1X2 al cierre | 98 % | 98 % | 59 % |
| Pinnacle 1X2 a T-15/120 min | 0 % | 0 % | 33 % (98 % en los últimos 30 días) |

Por liga (desde 2023): xG 77–100 %, árbitro 61–100 %, coordenadas de sede
71–88 %, córners y amarillas 72–100 %; bajas consultadas antes del inicio ≈0 %.

**A. Ya descargado, falta llevarlo a las tablas del motor (sin coste):** el
archivo FotMob (`historical_football_*`, enero-2024 → hoy, ≈20.700 partidos)
trae alineaciones (41.760 lados), minutos y estadísticas por jugador (874.760
filas), bajas con motivo y valor de mercado (48.669), entrenador y ronda por
partido, y estadísticas de estilo (20.726 partidos). Es el insumo de F3, F4 y
F12. Matiz de tiempo: las bajas del archivo se guardaron después del partido; son
una reconstrucción, válida solo como «sabido a T-60» en el régimen de F7 y
marcada como tal.

**B. Falta descargar:**

| Dato | Para qué | Fuente | Coste |
|---|---|---|---|
| Calendario de copas nacionales, Conference League, Libertadores, Sudamericana, Concachampions, Leagues Cup y fechas FIFA (desde 2024, equipos de las 13 ligas) | Descanso y carga (F12) | FotMob (calendario por equipo) | Sin coste de API; peticiones con ZenRows si hace falta |
| Minutos con selección nacional | Fatiga individual (segunda etapa) | FotMob (jugador) | Pesado; después |
| Clima histórico por partido | F6 | Copernicus ERA5 | Gratis; **falta tu token de CDS** |
| Altitud de las 758 sedes | F6 | Open-Meteo Elevation | Trivial |
| Cuotas Pinnacle a la hora de publicar / T-60 en temporadas pasadas | Probar «B contemporáneo» hacia atrás | The Odds API histórico | 24-25: ≈14.000 créditos (madrugada, 1X2) o ≈31.000 (T-60, 1X2). **No recomendado**: se evalúa hacia delante con la captura propia (98 % a T-60) |
| Ya en el plan | — | — | 527 snapshots de cierres (≈5.270 créditos), 1.219 huecos de xG |

**C. Captura en vivo (corregido el 15-oct):** el 38 % / 55 % de 30 días mezclaba
semanas anteriores al 21-sep, cuando los partidos aún no tenían id de
API-Football. En los últimos 18 días: bajas consultadas antes del inicio 100 %,
XI previo 100 % salvo Argentina y Liga MX (67 %), minutos de jugador ~100 %.
Huecos reales que quedan:
- API-Football no reporta ninguna baja en Argentina, Liga MX ni Portugal (0 %
  con bajas pese a consultarse el 100 %). Fuente candidata: la lista de no
  disponibles de FotMob antes del partido, que además es la misma fuente que el
  histórico de entrenamiento.
- El archivo FotMob fue una importación puntual (última el 13-oct): de lo jugado
  en 18 días cubre MLS 9 %, Argentina 10 %, Liga MX 25 %, UCL 54 %. Hace falta
  una captura diaria posterior al partido.
- Del 21-sep al 8-oct no hubo jornadas europeas de liga: lo confirman `matches` y
  el archivo FotMob; no es un hueco.

## 6. Orden después del 1-nov

| # | Trabajo | Condición para avanzar |
|---|---|---|
| 0 | Revisar el reentrenamiento; `python -m qf.model.ajuste`; 527 snapshots (visto bueno del usuario) | — |
| 1 | **F7** con versiones, horarios y registro de lo publicado; huecos de captura de 5.C | Trazabilidad fiel por partido, historial original intacto |
| 2 | **F9** + evaluación de **F8** en paralelo, sin cambiar los picks vendidos | Incluye B actualizado al mismo momento |
| 3 | Descanso y calendario (F12, primero descargar 5.B) | Cobertura verificada y aporte fuera de muestra |
| 4 | Llevar el archivo FotMob (5.A) a las tablas; F3 → F6 → F5 → F4 | Orden pactado; cada aporte con la puerta reforzada |
| 5 | **Activar F8** con los factores validados; F10 | Calidad y selección a volumen comparable |
| — | F11 puede adelantarse | Verificación funcional y de idiomas |

La pausa hasta el 1-nov es una decisión operativa; la fecha no demuestra una
mejora ni justifica activar nada sin evaluación. Todo factor puede evaluarse;
solo recibe peso el que aporte información comprobable fuera de muestra, y ese
peso puede ser cero. Ninguna señal se convierte en filtro que elimine pronósticos.
