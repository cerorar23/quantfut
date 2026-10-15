# Mejoras de los tres motores — plan tras el 1-nov

Fecha: 2026-10-15. Origen: documento del usuario «QuantFut — Recomendaciones para
mejorar los tres motores» (15-oct), contrastado con el código de `main` y con
producción. Decisión del usuario: **no se toca el motor hasta el reentrenamiento
del 1-nov**; todo lo de aquí se ejecuta después, en el orden de la sección 4.
Arquitectura de partida: `docs/MOTOR_Y_PICKS_AL_DETALLE_20261015.md` (PR #7).

## 1. Qué del documento ya existe o ya está planificado

| Recomendación | Estado verificado |
|---|---|
| Factores dentro de λ/μ antes de la matriz de marcadores, aprendidos y con respaldo si falta el dato | Diseño de la capa de ajuste (F1, `qf.model.ajuste`): `λ = λ_base·exp(...)`, un bloque entra solo si gana fuera de muestra en ≥2 ligas |
| Alineación y calidad del once / reemplazos | F4 (bloque `xi`); el XI simple ya pasa la puerta de F1 |
| Lesiones, sanciones, regresos | F3 (bloque `bajas`, minutos perdidos) |
| Árbitro, faltas, tarjetas | F5 (bloque `arbitro`) |
| Clima, altitud, viaje, sede | F6 (bloque `sede_clima`, incluye viaje × pocos días de descanso) |
| Revisar al confirmarse el once sin reescribir lo vendido | F7 (sello tardío, un lote por partido) |
| Anclaje de B solo con 1X2 (3 parámetros, 2 grados de libertad) | **No aplica**: `alta_prob.py:186` ajusta con 1X2 **y** la línea de goles de Pinnacle, con ρ fijo del modelo activo |
| Parley/escalera con patas del mismo partido | **No aplica**: un partido por pata (`parley.py`, `escalera.py`) |
| Alternativas por partido en vez de descartarlo | Existe en alta probabilidad: por partido se evalúan 1X2, doble oportunidad, goles, marca un equipo, ambos marcan, hándicap y córners, y se publica el de menor probabilidad dentro de la banda |
| Medir rentabilidad aparte del acierto | Existe: `alta_prob.historial()` → `rendimiento_ref` (ROI a cuota de referencia) |

## 2. Medición de producción (15-oct, solo picks con cuota de referencia)

| Producto | n | Prometido | Real | Cuota media | ROI a referencia |
|---|---|---|---|---|---|
| Alta probabilidad base | 91 | 82,6 % | 83,5 % | 1,164 | −2,96 % |
| Ampliada, banda 73–95 % | 223 | 81,4 % | 78,0 % | 1,190 | −7,52 % |

Esperado por diseño: la línea es de **acierto**, no de valor (decisión del
2026-10-05; histórico football-data ROI −2,4 %). La probabilidad es Pinnacle sin
margen y la cuota de la casa lleva margen. Solo información que el mercado no
tenga (sección 3, F8) puede cambiar el signo. La ampliada en este subconjunto
queda 3,4 puntos por debajo de lo prometido: vigilarla con el control semanal.

## 3. Fases nuevas

### F8 — Conectar el modelo propio con los picks (mezcla aprendida)

Problema: mejorar A no cambia ningún pick vendido; alta probabilidad, escalera
y parley salen de B. Propuesta:
- Mezcla entre la distribución de A (con los bloques aprobados) y la de B,
  con peso **aprendido** por familia de mercado (1X2/doble oportunidad, goles,
  ambos marcan/marca un equipo, hándicap), sin subdividir hasta muestras
  pequeñas. Punto de partida: `model/meta.py` (hoy `META_BLEND_ENABLED=0`,
  `w_model` 0,1083 solo en 1X2). Preferible mezclar a nivel de λ/μ para que todos
  los mercados derivados sigan siendo coherentes.
- Sin doble conteo: el peso se estima con la cuota de mercado **del mismo
  instante** que las señales (una baja ya descontada por Pinnacle no debe sumar
  otra vez). Alternativa a probar: modelo de residuo frente al mercado
  (`model/residual.py`, hoy apagado).
- Ningún reparto fijo (tipo 70/30). Peso cero es un resultado válido.
- Se mide con la evaluación de F9; se activa por bandera, no por defecto.

### F9 — Evaluación de picks a volumen constante (requisito de activación)

La puerta de F1 mide probabilidades (RPS, log-loss, ECE). Falta medir picks:
- Tres versiones sobre las mismas jornadas: actual · con contexto · con
  contexto + nueva selección. Mismo número de picks por jornada cuando haya
  oferta elegible, mezcla parecida de mercados y cuotas; excepciones registradas.
- Validación cronológica con un periodo final reservado que no se usa para
  elegir ajustes. Solo datos conocidos a la hora de publicar (el cierre es
  comparación posterior, nunca entrada). Reproducir la hora real de publicación
  (corrida de las 03:00 y, con F7, el sello tardío).
- Métricas separadas: acierto y calibración por banda; ROI a cuota tomada y
  CLV frente al cierre. Incertidumbre agrupada por partido/jornada (150 mercados
  de un partido no son 150 observaciones).
- Criterios de activación fijados **antes** de ver el resultado final: mejora
  fuera de muestra, volumen conservado, calibración aceptable y ningún deterioro
  material en mercados relevantes.
- Ablación: añadir y quitar grupos (XI, bajas, fatiga, clima, árbitro).

### F10 — Selección y diversidad

- Con F7/F8, si cambia la estimación de un partido, recalcular sus mercados y
  compararlos con el resto de la jornada antes de descartarlo; registrar la
  decisión (qué candidato ganó y por qué).
- Correlación entre partidos en parley y escalera (misma liga/hora/escenario);
  hoy solo se impide repetir partido.
- Volumen como métrica operativa diaria en `/control`, junto al acierto y al ROI.

### F11 — Lo que ve el usuario en la app (no toca el motor)

- Etiquetar la fuente de cada cifra: probabilidad del modelo, referencia de
  mercado y probabilidad usada para el pick. Hoy la agenda muestra el 1X2 de A y
  el pronóstico la de B sin decirlo.
- Indicador de **calidad de datos** separado de la probabilidad (once
  confirmado o no, clima/árbitro disponibles, liga con modelo o solo mercado).
- Todo texto nuevo en los 6 idiomas en el mismo cambio (`l10n_add.py`,
  `api/mensajes.py`).

### F12 — Factores sin fase todavía (candidatos, misma puerta)

| Factor | Datos | Nota |
|---|---|---|
| Descanso y partidos acumulados del equipo | Calendario propio (`matches`) | Barato; separar de viaje (F6) y de minutos por jugador (F4) |
| Ida/vuelta y marcador global | Champions y Europa League | Incentivos verificables, no "motivación" subjetiva |
| Necesidad de puntos / clasificación | Tablas derivadas de `matches` | Igual que lo anterior |
| Entrenador (antigüedad, cambio) | **Sin fuente verificada** | Sin bono automático por técnico nuevo (regresión a la media) |
| Estilos (bandas, centros, balón parado) | Estadísticas de equipo/jugador (`estadisticas`, `estadisticas_jugador`) | Prioridad en córners (motor C) |
| Motor C ampliado: faltas, jugadores previstos, rival | `estadisticas_jugador`, árbitro (F5) | Mantener la binomial negativa como referencia; mejorar media **y** dispersión |
| Portero, fichajes, cambio de estadio | Por decidir | Reducir el peso del historial directo cuando cambian plantillas |

### Tarea suelta antes de encender picks de valor

`picks.select_daily()` recorre `predictions` (13 ligas con modelo); la sombra
mide 22. Alinear la cobertura o acotar la sombra antes de
`PUBLISH_PICKS_ENABLED=1`, para que lo medido sea lo que se publicaría.

## 4. Orden después del 1-nov

1. Revisar el reentrenamiento; reejecutar `python -m qf.model.ajuste`; 527
   snapshots de The Odds API (con visto bueno del usuario).
2. **F7** sello tardío (ya acordado como siguiente).
3. **F9** evaluación a volumen constante: hace falta para juzgar todo lo demás.
4. **F8** conexión A→picks con los bloques que ya hayan pasado (XI simple).
5. F3, F6, F5, F4 (orden ya acordado); cada bloque se mide con F9 y llega a los
   picks a través de F8.
6. F10, después F12 por coste: descanso/calendario y ida/vuelta primero.
7. F11 puede adelantarse en cualquier momento si el usuario lo pide: es app y
   API de presentación, no motor.

Regla general: todo factor puede evaluarse; solo recibe peso el que aporte
información comprobable fuera de muestra, y ese peso puede ser pequeño o cero.
Ninguna señal se convierte en filtro que elimine pronósticos.
