# Cascada de cuotas: PropLine → The Odds API → SportsAPIPro

Decisión del titular, 9-nov-2026: si PropLine no tiene la cuota de un mercado, se busca en The Odds API y, si tampoco
(o se le acaban los créditos), en SportsAPIPro. Vale para fútbol, NBA y tenis. **Sustituye** la frase de `CLAUDE.md`
«The Odds API no es fallback automático de las cuotas en vivo»: ahora lo es, solo para los huecos y solo en la capa de
consulta. Otras dos decisiones del mismo día: el fútbol queda en capa de consulta (el motor sigue leyendo PropLine puro) y
SportsAPIPro va **sin tope diario propio** (`CUOTAS_SPORTSAPIPRO_DIARIO=0`).

## Qué cambia y qué no

| | Antes | Ahora |
|---|---|---|
| NBA, tenis (cuota de referencia web) | PropLine; The Odds API histórico por lotes, apagado | PropLine → The Odds API histórico → SportsAPIPro |
| Fútbol, cuota de casas en la ficha del partido | PropLine | PropLine → The Odds API (cuota actual de la liga) → SportsAPIPro |
| Motor de fútbol, picks, escalera, alta probabilidad, destacado | PropLine (`odds_snapshots.source='propline'`) | **Igual.** No se escribe nada en `odds_snapshots` |
| Regla de publicación de tenis | cuota de PropLine/respaldo | ignora las cuotas de SportsAPIPro (`post_sello`) |

El respaldo vive en cachés JSON (`cuotas_respaldo.json` para NBA/tenis, `cuotas_respaldo_futbol.json` para fútbol) que
escribe un comando por lotes y que la API **solo lee**: ningún endpoint web gasta créditos ni cupo.

## Los tres niveles

1. **PropLine** (archivo horario compartido): siempre gana. Un hueco es una fila sellada (NBA/tenis) o un partido de las
   próximas 36 h (fútbol) sin precio de ninguna casa elegible.
2. **The Odds API**: NBA y tenis, histórico a la hora del sello (cumple `as_of <= sealed_at`); fútbol, cuota actual de
   toda la liga en una petición (`mercados × regiones` créditos). Mismos topes que antes: 100 por pasada, 300 al día,
   suelo de 500 créditos. Si falta la clave, no hay presupuesto o el saldo cae bajo el suelo a mitad de pasada, **lo que
   falte pasa al nivel 3 en la misma pasada**.
3. **SportsAPIPro** (`ingest/cuotas_sportsapipro.py`): lo que siga sin cuota. Ver límites abajo.

Cada hueco se intenta como mucho 2 veces por nivel con 1 h entre intentos (en fútbol, por bloque de 6 h). Antes el
respaldo repetía la misma petición de pago cada 10 min mientras el hueco existiera. Los intentos se guardan en
`<caché>.intentos.json`.

## Qué es SportsAPIPro aquí (medido el 9-nov-2026, plan gratuito)

- `GET /v2/{deporte}/api/match/{id}/odds/pre-match`: **una sola casa** (`odds/1`), cuotas fraccionarias, solo prepartido
  y solo el precio de ahora. Sin histórico ni cierre.
- Por eso su recepción es siempre **posterior al sello**: la entrada lleva `post_sello: true` y `src: "sportsapipro"`, se
  muestra con su hora real y `regla_publicacion._precio_publicable` la ignora. Solo se piden partidos que aún no han
  empezado.
- Mercados traducidos (todos verificados con respuestas reales del 9-nov-2026): ganador (`marketId` 1; en fútbol 1X2
  con «1»/«X»/«2»); totales (tenis «Total games won» `marketId` 12, baloncesto «Game total» 18, fútbol «Match goals»
  `marketId` 9, una entrada por línea); en fútbol además «Both teams to score» (`btts`), «Double chance» y «Corners
  2-Way» (`corners`). El periodo del fútbol llega como «Full-time» (con guion). En fútbol también se traduce el
  «Asian handicap» (`spreads`; la opción llega como «(-0.5) Equipo», línea del propio equipo, igual que en
  `odds_snapshots`; solo si se conocen los nombres de los dos equipos y el equipo se reconoce sin ambigüedad). **No hay
  hándicap de juegos de tenis**: se comprobó en 3 partidos reales de ATP/WTA/Challenger (solo ganador, primer set y
  total). «Point spread» de baloncesto existe pero la NBA no sella ese mercado. «Draw no bet», primera parte y
  «First team to score» no se traducen. Sin props de jugador ni tarjetas.
- Resolución de partido: NBA y tenis por el calendario `/schedule/{fecha}` (día de Nueva York; una petición por deporte
  y fecha por pasada), con equipos de nombre exacto y jugadores por apellido + inicial, comienzo a ±30 min y candidato
  único. Fútbol: id de SofaScore del calendario que ya archiva el módulo del once (cero peticiones extra).
- Los originales se archivan con su recepción real en `<artifact_dir>/sportsapipro_cuotas` (índice aparte del del once).
- **Cupo:** el plan gratuito da 100 peticiones al día compartidas con el once de fútbol (40) y tenis. Con «sin tope» el
  respaldo puede consumirlas; el 429 o un `x-ratelimit-remaining` en 0 paran la pasada. Si se agota el cupo antes de las
  alineaciones, `CUOTAS_SPORTSAPIPRO_DIARIO` lo acota sin tocar código.

## Alertas

Telegram operativo (`TG_ALERT_CHAT`), como mucho una vez cada 6 h por fuente (estado en `<caché>.alertas.json`; nunca
lanza): SportsAPIPro se detiene (429, tope propio o cupo agotado) y TheRundown se detiene (401/403 = clave rechazada o sin
permiso; 429 o poca reserva = cupo diario de 20.000 puntos). `cuotas_respaldo.avisa()`.

## Qué no hace (límites honestos)

- «Todos los mercados» es lo que cada fuente entrega y lo que ya se traduce: The Odds API aporta ganador, totales,
  hándicap y props NBA de puntos/rebotes/asistencias/triples; SportsAPIPro, ganador, totales y, en fútbol, ambos marcan,
  doble oportunidad y córners totales. Tarjetas y hándicap siguen dependiendo de PropLine y The Odds API.
- No hay cierre (`close`) ni «cuota al sello» de SportsAPIPro: no sirve para CLV ni para entrenar.
- El fútbol no usa el respaldo en `destacado_web.congelar` (`con_respaldo=False`): el pronóstico destacado se sigue
  decidiendo solo con cuotas de PropLine.

## Operación

`~/quantfut/releases/cuotas-cascada-20261109/run.sh`: contenedor efímero con la imagen del worker, los archivos nuevos
montados de solo lectura y los montajes de lectura de las cohortes NBA y los sellos de tenis (el worker no los tiene).
Cron del usuario `qf`: `*/10`, con `flock`, `run.sh python -m qf.ingest.cuotas_respaldo --auto`.
`CUOTAS_RESPALDO_AUTO=1` va en el propio `run.sh`. Seco: `run.sh python -m qf.ingest.cuotas_respaldo` y
`run.sh python -m qf.ingest.cuotas_respaldo_futbol`.

Vuelta atrás: quitar la línea de cron. La API deja de mostrar el respaldo borrando las dos cachés JSON.

## Cuarto nivel: TheRundown (cuenta Free)

Decisión del titular (9-nov-2026): último respaldo cuando PropLine, The Odds API y SportsAPIPro no encuentran la cuota,
para fútbol, NBA y tenis. Código: `ingest/cuotas_therundown.py` (cliente y traductor), `nivel4_therundown` en
`cuotas_respaldo.py` (NBA y tenis) y `nivel4` en `cuotas_respaldo_futbol.py`. Guía: https://docs.therundown.io.

Medido el 9-nov-2026 con la clave del titular:
- Base `https://therundown.io/api/v2`, cabecera `X-TheRundown-Key`. `GET /sports/{id}/events/{AAAA-MM-DD}?market_ids=1,2,3&main_line=true` (fecha UTC).
- Plan Free: 20.000 puntos al día y 200.000 al mes, 1 petición por segundo, 5 minutos de retraso, **solo tres casas de
  EE. UU.** (`betmgm,fanduel,draftkings`), **solo partido completo**, sin WebSocket.
- **Sin cuota de entrada ni de salida**: `openers` y `closing` (y todo el histórico) responden 403 «requires a Starter plan
  or higher». Tampoco hay props de jugador (Starter). Solo existe el prepartido de ahora, así que su recepción es
  posterior al sello: `post_sello`, la regla de publicación la ignora.
- Costes: 8 eventos NBA con `main_line=true` = 147 puntos; **sin `main_line` = 3.495** (todas las líneas alternativas). Por eso
  solo se encuentra una línea si es la principal de la casa. Con la reserva de 2.000 puntos el nivel 4 se detiene.
- Cuotas en formato americano (se convierten a decimal); `0.0001` es «fuera del tablero». Participantes: equipos
  `TYPE_TEAM` con nombre completo; Over/Under como `TYPE_RESULT`; en fútbol el 1X2 es el mercado 1 con tres participantes
  (la forma del empate NO está verificada: ese día no había partidos de las ligas del catálogo).
- Sports: NBA 4; tenis ATP 38 y WTA 39 (se prueba ATP y luego WTA); fútbol por `leagues.odds_api_key` → 11 EPL, 12 Ligue 1,
  13 Bundesliga, 14 LaLiga, 15 Serie A, 16 Champions, 17 Europa League, 34 Liga MX, 10 MLS. Resto de ligas: sin cobertura.
- Mercados traducidos: ganador/1X2, totales, hándicap (tenis y fútbol). Sin BTTS, doble oportunidad, córners, tarjetas ni props.

**Licencia** (docs.therundown.io/licensing-and-attribution): Free es «uso interno o personal», **no permite mostrar los datos a
usuarios finales**, limita el almacenamiento a 24 h y excluye backtesting/entrenamiento. El titular decidió mostrarlas
igualmente (9-nov-2026) y asumió el riesgo (TheRundown podría revocar la clave). Mitigaciones: no se archiva nada (ni
originales) y las entradas caducan a las 24 h (se podan al escribir y no se sirven al leer); para ocultarlas sin
reiniciar ni tocar la caché: crear el archivo `cuotas_therundown_oculto` en el volumen de la caché
(`/srv/quantfut/artifacts/`; actúa en ≤5 s y se revierte borrándolo) o definir `CUOTAS_THERUNDOWN_MOSTRAR=0` (esto último exige
recrear el contenedor de la API y perdería los archivos copiados con `docker cp`). Atribución («Data provided by TheRundown») solo la exige el plan que permite mostrar.

Operación: la clave `THERUNDOWN_API_KEY` va en `~/quantfut/releases/cuotas-cascada-20261109/therundown.env` (modo 600), aparte
del `.env` general; reserva `CUOTAS_THERUNDOWN_RESERVA` (2.000). Pausa del nivel 4: dejar la clave vacía en ese archivo.
