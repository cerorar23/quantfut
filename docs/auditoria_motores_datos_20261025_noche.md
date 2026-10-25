# Auditoría de los tres motores y de sus datos: en vivo, cierres y completitud (25-oct-2026, 18–20 h UTC)

Pedido del titular: auditar a fondo los tres motores, las fases del Motor A y los demás motores; comprobar si los datos
llegan (en vivo, cierres, completos) y **arreglar en el momento** lo que falle, también al desplegar. Continúa
`docs/auditoria_motores_20261025.md` y `docs/auditoria_datos_motores_20261025.md` (mismo día, ya cerradas en #118–#131).
Medido en producción con SELECT en transacción de solo lectura, los registros del worker, ensayos sin guardar
(`dry_run=True`) y peticiones de prueba a Copernicus y FotMob. Worker `d2a1b5e` (= `main` `d7ed031`).

## Resumen

| # | Gravedad | Hallazgo | Arreglo |
|---|---|---|---|
| 1 | media | **La API corre código viejo**: 37 archivos distintos de `main` y 33 que faltan (imagen `3babeb4` construida sobre una API anterior; DEPLOYS.md decía que solo difería `config.py`). Viejos: `estadisticas_mercado`, `alta_prob`, `escalera_datos`, `health` (el panel y `/admin/health` calculaban la salud con los chequeos de antes), `panel`, `meta_capi`, `metricas`. Comprobado antes de cambiar: las 118 rutas son las mismas y la ficha del partido da la misma lista de mercados (solo córners totales) | API desplegada desde `main` |
| 2 | **alta** | **La sombra del XI (F1/F4, cuatro brazos) no registra nada desde el 22-oct**: solo admite cuotas `post_xi`, que daba The Odds API; PropLine captura `hourly:*` | Admite la foto horaria posterior al XI, anterior a T-15 y de menos de 75 min (`model/shadow.py`) |
| 3 | **alta** | **ERA5 (F6, clima)**: 175 de 177 celdas rechazadas (`CDS rejected`) cada día desde el ~20-oct, y creciendo. Comprobado: las mismas celdas pedidas de una en una salen bien; Copernicus rechaza las simultáneas | `CONCURRENCIA = 1` (`ingest/era5_clima.py`) |
| 4 | media | El lector de cuotas de PropLine solo miraba los alias `odds_api`; los que aprende el calendario/resultados de PropLine (`propline`) no servían (causa de los 19 partidos sin precio de esta mañana) | `match_events(..., otras_fuentes=("propline",))` en la carga horaria y en la de cierres |
| 5 | media | Chequeo de salud en rojo 3 días seguidos por nombres de ligas retiradas, con mensaje de bajas desfasado («SofaScore pendiente de conectar») y ciego a la falta de cierres (22–25 oct) y a la cobertura del xG (decía «al día» con el 26 %) | Chequeos nuevos: `cierres`, `cobertura del xG`, bajas/once de SofaScore; nombres solo de ligas activas vistos en 14 días; cuotas de PropLine a 6 h |
| 7 | **alta** | **Cierres que nunca se piden**: el recolector liquida todo `soccer_*` de PropLine en el orden del catálogo, con 3 peticiones por partido (cierre, props liquidadas y estadísticas) y tope de 300 al día. El 24-oct el tope se agotó con J-League (20), Conference (20), Saudí, A-League… y 26 partidos nuestros jugados se quedaron sin documento de cierre (Arsenal–Everton, Chelsea–Tottenham, Lazio–Parma, Köln–Schalke…) | La liquidación de fútbol solo pide las 15 ligas + 2 copas del catálogo y no pide `results` (props de fútbol: nadie las lee): 2 peticiones por partido (`sports_by_prefix`, `results_prefixes`). Los del 23–25 oct entran en las próximas pasadas (miran 3 días atrás) |
| 8 | **alta** | **Presupuesto de PropLine agotado al final del día UTC**: ~1.650 de ~3.700 peticiones diarias son de competiciones que ningún motor usa (J-League, Conference, Eerste Divisie, Mundial…); al llegar a la reserva de 500 el recolector se para hasta las 00:00 UTC. El 24-oct la pasada de las 23:07 se cortó (Liga MX, MLS y Argentina juegan a esas horas); el 25-oct a las 19:14 quedaban 790 | Las competiciones sin motor se siguen archivando, pero cada 3 h (`priority_sports`, `other_sports_every_hours`); NBA, tenis y las 17 nuestras, cada hora |
| 6 | baja | 5 nombres del feed sin alias (Tromso IL, Sarpsborg 08, Botafogo FR RJ, New York RB, COL Rapids) | Alias dados de alta (ver DEPLOYS.md); `SBV Excelsior` ya lo resuelve el punto 4 |

## Qué llega y qué no (medido)

- **Cuotas (PropLine horario):** 404.000 filas en 3 días, última a las 18:15 UTC. Próximas 48 h: Pinnacle 1X2 en 26 de 27
  partidos de ligas activas, todos refrescados en las últimas 3 h. Ensayo del Motor B con los partidos restantes:
  **0 sin precio** (esta mañana eran 19).
- **Cierres (PropLine `/odds/closing` → `close`):** 25.437 filas cargadas a las 16:24 (Pinnacle 1X2, totales, córners,
  tarjetas). De los terminados desde el 22-oct: cierre 1X2 en 75–100 % de las ligas activas (los de esta tarde entran a
  partir de las 6 h). Serie B y LaLiga 2 casi sin cierre: se retiran esta noche (088).
- **En vivo (FotMob, cada 5 min):** entre 9 y 16 partidos en juego enlazados en cada pasada de 17:55 a 18:20; todos los partidos de hoy tienen referencia de
  FotMob. Aldosivi–Belgrano no muestra marcador porque FotMob no lo da como empezado (sin cobertura en vivo de ese partido).
  Entre el final y el cierre del resultado (PropLine `/scores` cada 3 h; mediana 3–6 h) la app no muestra marcador.
- **Resultados:** 0 huérfanos de más de 6 h en ligas activas.
- **Completitud de terminados (>36 h, ligas activas):** goles, descanso, xG, córners, tarjetas, árbitro y tiros al
  100 %; `stats` falta en 6 partidos (los rellenados solo por FotMob). Últimas 36 h: xG 100 % salvo LaLiga 2 y
  Allsvenskan (retiradas) y 13/14 en MLS.
- **Bajas y once (SofaScore):** previsto o bajas en todos los partidos de las próximas 48 h de las ligas activas; once
  oficial en 49 de 61 empezados hoy hasta las 18:20 (faltan sobre todo MLS 4 de 7, Liga MX 2 de 2 y Brasil 1 de 1:
  MLS y Liga MX entraron en SofaScore a las 16:25 con #127, después de capturar esos partidos; los próximos sí tienen
  previsto).
- **Motor A:** todos los partidos de hoy de ligas con modelo tienen predicción (41 diarias y 32 finales del sello
  tardío, F7); 0 equipos desconocidos. Cadena verificada (52 lotes).
- **Motor B/C:** 28 de alta probabilidad, 385 de la ampliada, 133 de tarjetas, escalera y parley el 25-oct.

## Fases del Motor A

| Fase | Estado medido |
|---|---|
| F1 ajuste del XI | En sombra; Δ RPS +0,0012 hacia adelante (no listo). La sombra de cuatro brazos estaba parada (hallazgo 2) |
| F2 cierres | Vuelven a entrar desde PropLine; el histórico pendiente sigue en la compra del 1-nov |
| F3 bajas | Llegan de SofaScore; el modelo aún no las usa (falta historia con ids de SofaScore; `availability` compara solo onces de la misma fuente) |
| F6 clima | ERA5 parado por los rechazos (hallazgo 3) |
| F7 sello tardío | Funciona: 32 lotes por partido hoy, sin fallos |
| F9, F12, F5, F4 | Sin empezar (sin cambios) |

## Lo que no se cambia y por qué

- **Marcador final en la app entre el pitido y el resultado oficial:** mostrarlo exige un estado `FT` que la app actual
  no sabe pintar (lo pondría como «en juego»); va con la próxima versión de la app.
- **Cierre de resultados desde FotMob antes de las 6 h:** FotMob es respaldo por decisión del titular; adelantar la
  fuente es una decisión, no un error.
- **`SOFT_BOOKS`, licencia de BetsAPI, tope de Apify:** dependen del titular (PENDIENTES.md).
