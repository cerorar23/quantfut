# Fuerza por jugador — diseño

Fecha: 2026-09-29. Aprobado por el usuario sección a sección.
Relación: evolución del challenger de XI (Fase 4, `model/lineup_challenger.py`).

## Objetivo

Cuantificar cuánto cambia la fuerza de un equipo según QUIÉN juega, no solo
cuántos titulares habituales faltan. La señal actual (`missing_regulars`)
trata igual la baja de la estrella y la del suplente. El resultado es un
brazo nuevo del challenger de XI que compite, sobre los mismos partidos, con
el XI simple.

Éxito: el brazo nuevo mejora RPS, log-loss y calibración (ECE) fuera de
muestra en ≥2 ligas Y mejora al XI simple. Si no lo supera, no se usa. Si se
valida, se mide en sombra contra el cierre de Pinnacle; nada se publica sin
esa prueba.

## Calendario (decisión del usuario)

- Ahora: tabla, descarga histórica y captura diaria.
- Después del reentreno del 1-oct-2026 (que valida o no el XI simple):
  valores por jugador, brazo nuevo, validación y, si pasa, sombra.

## 1. Datos

Tabla `estadisticas_jugador` (migración nueva), una fila por jugador y
partido:

| columna | contenido |
|---|---|
| match_id, side | partido y lado (home/away) |
| player_id, nombre, posicion | de API-Football |
| minutos, titular | titular = estaba en el XI inicial |
| goles, asistencias, tiros, tiros_puerta, pases_clave, regates | ataque |
| entradas, intercepciones, duelos_ganados, paradas | defensa |
| nota_proveedor | nota 0-10 de API-Football |
| fetched_at | hora de descarga |

Fuente: `/fixtures/players` (1 petición por partido).

- Histórico: los 4.555 partidos de `lineups_historicas` (último año, 11 ligas
  con modelo). Módulo reanudable con la misma reserva de cuota que
  `ingest/lineups_historicas.py`. ~4.600 peticiones, 1-2 días.
- En adelante: `ingest/results.py` la pide al cerrar cada partido de ligas con
  modelo (~150 peticiones/día en fin de semana).
- Partido sin estadísticas: se registra "sin datos" para no repetir la
  petición y no cuenta en los valores.

Punto en el tiempo: no hace falta excepción. Son datos de partidos jugados;
para un partido del día D solo cuentan estadísticas de partidos anteriores a
D. La nota del proveedor puede revisarse días después: por eso `fetched_at` y
por eso es solo comparación.

## 2. Valor de cada jugador (`model/player_ratings.py`)

Antes de cada partido, dos valores por jugador, calculados SOLO con partidos
anteriores:

- Ofensivo por 90: combinación de tiros, tiros a puerta, pases clave, goles y
  asistencias. Pesos estimados con los datos, no puestos a mano: regresión
  de Poisson de los goles del equipo en un partido sobre la suma, en su XI,
  de cada estadística por 90 (calculada con partidos PREVIOS). Se ajusta solo
  con el 70 % de entrenamiento; el 30 % de validación nunca toca los pesos.
  El defensivo, igual con los goles encajados.
- Defensivo por 90: entradas, intercepciones, duelos ganados y, en porteros,
  paradas. Se espera que pese poco: las estadísticas defensivas son débiles.

Ajustes:
1. Decaimiento temporal con la vida media del modelo de equipos (180 días,
   `settings.decay_halflife_days`).
2. Encogimiento hacia la media de su posición según minutos jugados.
3. Separado por posición (G/D/M/F).

Jugador sin historial: media de su posición. El módulo solo calcula valores;
no modifica el modelo de equipos.

## 3. Señal y validación

Once habitual = titulares más frecuentes en los 5 partidos previos (misma
regla que `build_lineup_features`). Por equipo:

- `valor_ofensivo_delta` = valor ofensivo del XI de hoy − el del habitual
- `valor_defensivo_delta` = lo mismo en defensa
- y los mismos dos con la nota del proveedor, solo para comparar.

Brazos, sobre los mismos partidos y la misma base:

| brazo | señal |
|---|---|
| base | modelo sin XI |
| XI simple | titulares habituales que faltan (actual) |
| XI con valor | deltas de valor ofensivo/defensivo (nuevo) |
| XI con nota | deltas con la nota del proveedor (comparación) |

Mismo mecanismo que el XI simple: corrección Poisson sobre log(lambda) de cada
equipo con la base como offset (`_fit_poisson_offset`). Validación: 70 %
antiguo para ajustar, 30 % reciente para validar, sin mezclar; mismas
métricas y la condición extra de superar al XI simple.

## 4. En vivo, errores y pruebas

En vivo: con el XI confirmado (T-60), la sombra (`model/shadow.py`) registra
el brazo "XI con valor" junto a los demás, con valores calculados solo con
partidos anteriores. No se publica nada.

Errores:
- Jugador sin historial: media de su posición.
- Proveedor sin estadísticas de un partido: "sin datos", no se repite.
- Más de 3 titulares desconocidos en un equipo: ese brazo no predice el
  partido.

Pruebas:
1. Punto en el tiempo: el valor para el día D no cambia al añadir partidos
   posteriores a D.
2. Encogimiento: pocos minutos → cerca de la media de posición.
3. Señal: XI habitual → deltas 0; falta el mejor delantero → valor ofensivo
   perdido.
4. Aislamiento: ni la predicción diaria ni lo sellado leen
   `lineups_historicas`.

## Fuera de alcance

- Plus-minus regularizado (necesita minutos exactos de cada cambio, otra
  petición por partido, y es muy ruidoso con esta muestra).
- xG por jugador (API-Football no lo da).
- Publicar picks basados en esto sin validación en sombra contra el cierre.
