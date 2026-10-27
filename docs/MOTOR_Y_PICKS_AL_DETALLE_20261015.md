# QuantFut — cómo está construido de verdad el motor y los picks (15-oct-2026)

Documento verificado contra el **código de `main` (commit 5a85376)** y contra **producción en solo lectura**
(worker, API y base de datos del VPS, 15-oct-2026). No parte del README: donde el README, un comentario o un
docstring dicen otra cosa que el código, se marca en la sección 11.

Convención: **[código]** = leído en el repo; **[prod]** = consultado en el servidor; **[no verificado]** = lo digo
pero no lo comprobé en esta pasada.

---

## 1. La idea central: no hay un motor, hay tres

QuantFut no tiene «un modelo que pronostica y de ahí salen los picks». Tiene **tres motores que corren por
separado**, con datos distintos, y cada producto se alimenta de uno u otro:

| | **Motor A — Modelo propio** | **Motor B — Mercado sharp** | **Motor C — Estadístico de córners y tarjetas** |
|---|---|---|---|
| **Qué es** | Dixon-Coles (cuasi-Poisson) entrenado con goles y xG. | La cuota de Pinnacle sin margen (Shin), traducida a probabilidades de cualquier mercado. | Binomial negativa con decaimiento, priors y factor de árbitro. |
| **De dónde sale la probabilidad** | De la fuerza de ataque/defensa de cada equipo. | Del precio que Pinnacle ya fijó. **No pronostica: traduce.** | De los córners y tarjetas históricos de cada equipo y árbitro. |
| **Código** | `model/dixon_coles.py`, `calibration.py`, `pricing.py`, `train.py`, `publish/daily.py::generate_predictions` | `model/devig.py`, `model/market_anchor.py`, `publish/alta_prob*.py`, `escalera*.py`, `parley*.py`, `picks.py` | `model/estadisticas_mercado.py`, `publish/tarjetas_seg.py` |
| **Qué produce** | `predictions` (sellada): ~150 mercados por partido | Alta probabilidad, ampliada, escalera, parley y el precio justo de los picks de valor | Líneas de córners y tarjetas |
| **Cobertura** | 13 de 23 ligas activas | Todas las ligas con cuota Pinnacle | Solo líneas validadas |
| **¿Gana al mercado?** | **No** (RPS 0,1991 vs 0,1935) | Es el mercado: no hay nada que ganarle | Se recorta al mercado cuando hay cuota |
| **Estado en producción** | **Encendido** | **Encendido** | **Encendido** (dentro de B) |

**Conclusiones que se desprenden** [código + prod]:

1. **Los pronósticos que el usuario compra o ve como producto vienen del Motor B** (y del C para córners). El
   Motor A **no decide ningún pronóstico publicado**.
2. **El Motor A solo se ve en la app** en el 1X2 de la agenda, en la «tarjeta del modelo» junto a un pronóstico
   visible y en la lista de mercados del partido de las ligas con modelo.
3. **Los motores comparten herramientas, no datos ni decisiones.** Los tres usan la misma matriz de marcadores
   (`price_all_markets`). El Motor B toma del A **un único número**: ρ de Dixon-Coles (−0,0613), leído del
   artefacto activo (`alta_prob_datos._rho_activo`). La mezcla de A con B existe (`meta.py`) pero está
   **apagada**.
4. **Un mismo partido puede mostrar dos probabilidades distintas** (1X2 del A en la agenda, probabilidad del B en
   el pronóstico). No es un error: son dos fuentes.
5. **Las señales nuevas** (alineaciones, bajas, clima, árbitro, tiros) **no alimentan el Motor A**: se capturan y
   se muestran. El árbitro solo influye en el Motor C. El clima no tiene captura en el cron de producción.

Estado comercial: **picks de valor apagados** (`PUBLISH_PICKS_ENABLED=0`, tabla `picks` vacía). El sello de la
cadena de hashes funciona, pero **nada se publica fuera del servidor** (17 lotes, 0 con referencia externa).

---

## 2. Capa común: datos que entran

Todo lo de esta sección es compartido; la sección 3 a 5 dice qué motor usa qué.

### 2.1 Fuentes y cadencia (cron del worker, `scripts/crontab`) [código]

| Dato | Módulo | Cadencia (UTC) | Tabla destino | Lo usa |
|---|---|---|---|---|
| Cuotas 1X2 y totales de ~20 casas (The Odds API) | `ingest/odds_worker.py` | cada 10 min; `--solo-cierre` en :05-:59/10 | `odds_snapshots` (inmutable) | B, sombra, entrenamiento de A (referencia) |
| Cuotas API-Football (1X2, goles, goles por equipo) | `ingest/af_odds.py` | :20 de cada hora | `af_odds_snapshots` | B |
| Ráfagas de latencia de casas blandas | `ingest/rafagas.py` | cada 5 min | tablas de ráfagas | sombra |
| Calendario | `ingest/fixtures.py` | 05:15 y 17:15 | `matches` | A, B, C |
| Resultados + estadísticas de partido | `ingest/results.py` | cada 3 h (:45) | `matches` (+ estadísticas) | A (goles), C (córners/tarjetas) |
| Marcador en vivo | `ingest/live.py` | cada 45 min | `matches.live_*` | solo app |
| Clasificación | `ingest/standings.py` | 06:40 y 22:40 | posiciones | solo ficha |
| Alineaciones confirmadas | `ingest/lineups.py` | cada 5 min | alineaciones | solo ficha |
| Bajas/lesiones | `ingest/injuries.py` | cada 4 h | bajas | solo ficha |
| xG (API-Football) | `ingest/xg_api_football.py` | 12:10 | xG con `xg_recorded_at` | A |
| xG de respaldo (PitchAPI) | `ingest/pitchapi_respaldo.py` | 12:40 | respaldo/verificación | verificación |
| xG histórico + Copas UEFA | `ingest/xg_worldfootball.py`, `uefa_cups.py` | martes 04:00 / 04:30 | `matches` | A |
| Captura de ofertas para la sombra | `publish/shadow_sharp.py capture` | :25 de cada hora | `sharp_shadow_offers` | sombra |
| Salud | `ingest/health.py` | 07:00 | `health_runs` | operación |
| CLV | `eval/clv.py` | 02:30 / 10:30 / 18:30 | CLV por pick | puerta comercial |
| Pipeline diario | `publish/daily.py` | **09:00** | ver §7 | todos |
| Verificación de la cadena | `publish/hashchain.py verify` | 06:00 | — | sello |
| Entrenamiento | `model/train.py` | día 1, 03:00 (y `--bootstrap` el resto) | `model_artifacts` | A |

### 2.2 Volumen actual [prod]

- `matches`: **93.058** partidos (2012-03-10 → 2026-11-05); 92.353 jugados, 704 programados, 1 aplazado.
- `odds_snapshots`: **460.070** filas (football_data 286.623 · the_odds_api 161.201 ·
  oddspapi_reconstructed 8.754 · the_odds_api_hist 3.492). Las `oddspapi_reconstructed` a >5 min del inicio
  **ya no cuentan como cierre** (`eval/cierre.py::es_cierre_real`, aplicado en entrenamiento, CLV y sombra).
- `predictions`: 281 filas (27-sep → 15-oct).
- Ligas activas: 23. **Con modelo (Motor A) habilitado: 13** (Argentina, Brasil A, Bundesliga, LaLiga,
  Champions, Europa League, Ligue 1, Premier, Serie A, Liga MX, Eredivisie, Primeira, MLS). Las otras 10 (Suiza,
  Bundesliga 2, Dinamarca, LaLiga 2, Ligue 2, Championship, Serie B, Noruega, Suecia, Turquía) tienen cuotas y
  sombra pero **no predicción propia**.

---

## 3. Motor A — Modelo propio (Dixon-Coles)

### 3.1 Datos que usa de verdad [código]

Solo cuatro: **goles, xG (mezcla 0,65), fecha del partido y liga**. Nada más entra en las lambdas: no hay
alineaciones, bajas, clima, árbitro, tiros, valor de jugadores ni ratings Kalman en la predicción diaria.
`model/kalman.py` solo lo importa `eval/early_vs_close.py` (evaluación). `meta.py` y `residual.py` existen,
se entrenan cada mes y están **apagados** (`META_BLEND_ENABLED=0`, `RESIDUAL_ENABLED=0`).

El mercado entra al **entrenamiento** solo como referencia para comparar y para medir el peso `w_model`; no entra
a las lambdas.

### 3.2 Cómo se construye, paso a paso [código + prod]

1. **Datos de entrenamiento** (`train.py::load_training_data`): 12 años de `matches` unidos al cierre de
   Pinnacle (`window_tag='close'`, filtrado por `es_cierre_real()`).
2. **Dixon-Coles cuasi-Poisson** (`dixon_coles.py`): ataque/defensa por equipo, ventaja de local y base de goles
   **por liga**, con encogimiento parcial (`POOL_HOME_ADV 25`, `POOL_BASE 25`, `POOL_STRENGTH 300`,
   `SUM_ZERO 1000`, ridge 0,02). Vida media del peso temporal: **180 días**. Equipos indexados por (liga,
   nombre). Guarda de muestra efectiva (`MIN_EFFECTIVE_MATCHES 5`). Lambdas recortadas a ≤ 6.
3. **Objetivo mezclado**: goles reales y xG con `XG_BLEND=0,65`.
4. **Copas** (Champions/Europa): `matches.league_id` es la competición y `teams.league_id` la liga doméstica; el
   término `strength` entre ligas se cancela exactamente en partidos domésticos (probado a 1e-9).
5. **ρ de Dixon-Coles** global: −0,0613.
6. **Calibrador afín en log-lambda** (`calibration.py`): activo (`cal_2026.09.27-010508.pkl`, `validated=True`):
   a0=0,046, a1=0,882 (local), b0=−0,056, b1=0,965 (visita). Mejora mínima en validación: RPS 0,21611 →
   0,21588 y log-loss 1,0507 → 1,0481 sobre 1.245 partidos. Si no superara la validación se usaría la identidad.
   (El JSON `val_metrics` del artefacto dice `validated:false` porque se guardó antes de validar; el `.pkl` que se
   aplica sí está validado.)
7. **Precio**: `pricing.price_all_markets(lam, mu, rho)` construye **una** matriz de marcadores (≈13×13) con la
   corrección τ y de ahí salen **~150 mercados** (1X2, doble oportunidad, EMA, totales, BTTS, hándicap, equipos,
   marcador exacto…), coherentes entre sí.
8. **Mezcla con el mercado** (`meta.py`) y **GBM de residuo** (`residual.py`): apagados. El peso medido del
   modelo es 0,1083; la mezcla (RPS 0,18466) casi iguala al mercado (0,18458) y no lo bate.
9. **Activación** (`promotion.py`): exige batir a Elo con las mismas filas y datos de mercado frescos. El
   artefacto activo (**2026.09.27-010508**) cumple (`promote:true`), no bate al mercado (`beats_market:false`) y
   no está listo para vender picks (`ready_for_commercial_picks:false`, motivo «CLV con muestra insuficiente
   (0 < 300)»). Se entrenaron artefactos posteriores (01-oct, 11-oct, 12-oct) que **no se activaron** [prod].

### 3.3 Qué tan bueno es (validación, n = 1.149) [prod]

| Modelo | RPS | Log-loss | Brier | ECE |
|---|---|---|---|---|
| Mercado (Pinnacle sin margen) | 0,19345 | 0,96809 | 0,57605 | 0,00914 |
| **Motor A (Dixon-Coles)** | 0,19910 | 0,98841 | 0,58893 | 0,00744 |
| Elo | 0,19932 | 0,99374 | 0,59152 | 0,01375 |

Lectura honesta: está bien calibrado (ECE bajo) pero **discrimina menos que el mercado**. No hay ventaja
predictiva demostrada sobre el cierre de Pinnacle.

### 3.4 Qué hace con su salida [código + prod]

- **Daily**: guarda en `predictions` (inmutable por trigger) una fila por partido de la ventana en las 13 ligas.
  281 filas desde el 27-sep: Argentina 47, MLS 46, Brasil 24, LaLiga/Premier/Serie A 20 cada una,
  Primeira/Bundesliga/Champions/Ligue 1/Eredivisie 18, Liga MX 12, Europa League 2.
- **App**: el 1X2 de la agenda (`/mobile/v1/home`), la «tarjeta del modelo» (1X2, +1,5/+2,5, ambos marcan) que
  solo sale junto a un pronóstico visible, y la lista de mercados del partido (`partido_mercados`).
- **Picks de valor** (apagados): lo usa como *lista de partidos candidatos* y como diagnóstico (`model_prob`),
  nunca para decidir (ver §4.5).
- **API**: `/matches/{id}` (recortado a 1X2 y totales 2,5) y `/v1/matches/{id}/predictions` (completo, con token
  de servicio).

---

## 4. Motor B — Mercado sharp (Pinnacle sin margen)

### 4.1 Idea [código]

Pinnacle es la casa de referencia (`SHARP_BOOK=pinnacle`). Su cuota, sin margen, es la mejor estimación
disponible de la probabilidad real. El Motor B **no estima fuerza de equipos**: toma ese precio y lo convierte en
probabilidades de otros mercados. Por eso funciona en las 22 ligas con cuota, no solo en las 13 con modelo.

### 4.2 Datos que usa [código]

Cuotas de Pinnacle (y de otras casas para el consenso) de `odds_snapshots` y `af_odds_snapshots`. De A solo toma
ρ. Para córners, el Motor C.

### 4.3 Cómo se construye [código]

1. **De-vig** (`devig.py`): método **Shin** (`DEVIG_METHOD=shin`); `consensus_devig` pondera casas sharp (peso 0,6
   para Pinnacle).
2. **Anclaje** (`market_anchor.py`): ajusta (λ, μ, ρ) a la terna 1X2 sin margen para derivar goles, hándicap,
   equipos, etc. con la **misma matriz de marcadores** que usa el Motor A, pero con lambdas ajustadas al mercado.
   Puede devolver `None` si Dixon-Coles no representa la terna; entonces no se fuerza.
3. **Productos**: cada uno elige distinto qué mostrar (§4.4).

### 4.4 Productos del Motor B

**Alta probabilidad y ampliada** (`alta_prob*.py`) — ENCENDIDO [código + prod]
- Probabilidad: Pinnacle sin margen. Goles/hándicap/equipos con lambdas ancladas al mercado; córners con el
  Motor C recortado al mercado.
- Sellado base 80-95 %; ampliada (`ALTA_PROB_EXT_ENABLED=1`) desde 62 %. **La app solo muestra 73-95 %**
  (`mobile.HIGH_MIN/HIGH_MAX`): es un filtro de lectura; las filas inmutables no se tocan.
- Control de calidad: pausa por desviación (z ≤ −4 / IC99).
- Volumen [prod]: base **172** picks (8 → 15-oct: 136 aciertos, 29 fallos, 4 nulos, 3 pendientes); ampliada
  **751** (514 / 180 / 25 / 32).
- Acierto vs. prometido [prod]: base 82,4 % real vs 82,4 % prometido (n = 165); ampliada total 74,1 % vs 77,2 %
  (n = 694), pero **en el tramo que ve la app (73-95 %) 81,9 % vs 82,3 % (n = 452)**. Lo que cae por debajo de
  73 % rinde por debajo de lo prometido y ya no se muestra. Muestra de **una semana**: indicio, no prueba.
- Mercados de la base: hándicap 50 · totales 31 · doble oportunidad 28 · córners 33 (18+10+5) · goles de equipo
  25 · 1X2 5.

**Escalera** (`escalera*.py`) — ENCENDIDO [código + prod]
- Retos de 3-6 escalones, cuotas 1,25-1,40, se elige el escalón **más probable**; **sin filtro de valor**.
  Freeroll 2,5×, stake 10. 4 retos en total.
- La app muestra escalones con probabilidad 75-90 %; uno gratis por lote, el resto con candado.

**Parley** (`parley*.py`) — ENCENDIDO [código + prod]
- 1 a 5 parlays al día, escalones de cuota 1,90-5,00, patas de cuota 1,20-1,80, elegido por probabilidad, no por
  valor. 10 tickets y 9 resultados hasta hoy. Gratis el de menor escalón; los liquidados se ven siempre.
- Expuesto en `/parley`; **la app lo consume** (`product/live_parley.dart` llama a `/parley`).

### 4.5 Picks de valor (`publish/picks.py`) — APAGADO [código + prod]

Es el producto del Motor B que *no* busca probabilidad alta sino **cuota mal puesta**.

- Idea: una casa blanda paga más que el precio justo de Pinnacle. **Solo 1X2.** Edge mínimo 2 %. `model_prob`
  (Motor A) es solo diagnóstico y no decide.
- Prior de persistencia por casa mezclado con la sombra; `EDGE_SHRINKAGE=0,55`.
- Stake: Kelly 0,20 con tope 2 u, factor de incertidumbre Baker-McHale, topes de cartera.
- Reparto: `assign_tiers()` — los 2 mejores del día (`FREE_PICKS_PER_DAY=2`) son free, el resto paid.
- Entrega: `picks_for_tiers` (`comercial/entrega.py`), ordenado por `edge_pct`.
- **Dependencia oculta del Motor A**: `select_daily(predictions)` itera sobre filas de `predictions`. Si se
  encendiera tal cual, **solo se evaluarían partidos de las 13 ligas con modelo**, mientras que la sombra mide
  22 ligas. Es un desajuste que conviene resolver antes de encender (ver §11).
- Estado: `PUBLISH_PICKS_ENABLED=0`; **tabla `picks` con 0 filas**. `/app/v1/picks` devuelve lista vacía y
  `publicacion_activa:false`.

### 4.6 Sombra y puerta comercial (`publish/shadow_sharp.py`) [código + prod]

- Cada hora (:25) captura todas las ofertas de las próximas 72 h y decide como si fuera a publicar.
  «Publicable» = primera oferta con stake por partido. Se liquida contra el cierre sharp.
- Totales [prod]: 1.498 ofertas, 1.356 liquidadas; **171 publicables, 142 con cierre justo**. `edge_early`
  +4,83 %, `ev_close` +3,46 %, `roi` −9,2 %, `ev_close_ci95: null`.
- **Puerta** (`promotion.evaluate_clv_gate`): n ≥ 300, límite inferior del IC95 de `ev_close` > 0 y ≥ 3 ligas
  con n ≥ 30. Hoy n = 171 y la liga más grande tiene 14 (MLS). Ritmo ≈ 8 publicables/día → 300 hacia finales de
  octubre; 3 ligas con 30 cada una no antes de mediados de noviembre y probablemente después. (Corrige mi
  estimación anterior de «~10-nov», que ignoraba el requisito de ligas.)
- **Desajuste de política**: la sombra decide a cualquier antelación; la publicación real ocurriría una vez al
  día a las 09:00. Lo medido en sombra no es idéntico a lo que se publicaría (es lo que busca resolver F7).

---

## 5. Motor C — Estadístico de córners y tarjetas

### 5.1 Qué es y qué datos usa [código]

`model/estadisticas_mercado.py`: binomial negativa (φ propia) con decaimiento temporal, priors y, **solo para
tarjetas**, factor de árbitro encogido (`PRIOR_ARBITRO 10`, `usar_arbitro=True`). Datos: córners y tarjetas de
cada partido jugado (`matches` + estadísticas de `results.py`) y el árbitro (`matches.referee`). Solo usa líneas
validadas (`LINEAS_HABILITADAS`): cambiarlas exige repetir la prueba.

### 5.2 Dónde se usa [código + prod]

- **Córners** dentro de alta probabilidad, escalera y parley, **recortados al mercado** cuando hay cuota.
- **Tarjetas en seguimiento** (`tarjetas_seg.py`): sin publicar, 3 filas en producción. Es el único sitio donde
  el árbitro influye en algo.
- **Lista de mercados del partido** (`partido_mercados`): líneas de córners y tarjetas.

---

## 6. Cómo se combinan los tres en cada producto

| Producto | Motor A (propio) | Motor B (mercado) | Motor C (córners/tarjetas) | Estado |
|---|---|---|---|---|
| Agenda de la app (1X2) | **✔ fuente** | — | — | encendido |
| Tarjeta del modelo | **✔** (ligas con modelo) | ✔ (ligas sin modelo, `fuente: mercado`) | — | encendido |
| Lista de mercados del partido | ✔ lambdas del A en ligas con modelo | ✔ lambdas ancladas en ligas sin modelo | ✔ córners y tarjetas | encendido |
| Alta probabilidad / ampliada | solo ρ | **✔ fuente** | ✔ córners | encendido |
| Escalera | solo ρ | **✔ fuente** | ✔ córners | encendido |
| Parley | solo ρ | **✔ fuente** | ✔ córners | encendido |
| Picks de valor | lista de partidos + `model_prob` diagnóstico | **✔ decide** | — | **apagado** |
| Sombra de picks de valor | — | **✔** | — | encendido (solo medición) |
| Tarjetas en seguimiento | — | ✔ | **✔ fuente** | solo seguimiento |
| Sello (cadena de hashes) | ✔ (`predictions`) | ✔ (alta, ampliada, escalera, parley) | indirecto | encendido |

**Dónde pueden contradecirse**: en la app, la agenda enseña el 1X2 del A y el pronóstico enseña la probabilidad
del B. Si difieren, no hay error, pero el usuario puede notarlo. Opciones para decidir más adelante: etiquetar la
fuente en pantalla o mostrar solo una.

---

## 7. Pipeline diario (`publish/daily.py`, 09:00 UTC = 03:00 CDMX) [código]

Orden estricto, no alterable sin decisión explícita:

1. **Motor A predice** (`generate_predictions`): artefacto activo, calibrador, meta, residual; para cada partido
   de la ventana (`ventana.py`, margen 60 min) calcula lambdas → calibra → `price_all_markets` → `predictions`.
   Un fallo por partido no detiene el resto.
2. **Picks de valor** solo si `PUBLISH_PICKS_ENABLED` y la puerta está abierta. **Hoy no se ejecuta.**
3. **Productos del Motor B** (cada uno tras su flag): alta probabilidad, ampliada, escalera, parley; y el
   seguimiento de tarjetas (Motor C).
4. **Sellar** (`hashchain.seal`): un lote por día en `prediction_batches` con `payload_sha256`, `prev_sha256`,
   `chain_sha256`. Entra: predicciones, picks, `alta_prob_picks`, `alta_prob_ext`, `escalera_retos` (+ tickets y
   patas del parley).
5. **Publicar** (Telegram, best-effort; el negocio no usa Telegram para picks).

Estado de la cadena [prod]: **17 lotes**, último 15-oct, 0 con referencia externa (`CHAIN_GIT_REMOTE` vacío).
Los lotes se regeneran desde la base solo en 9 de 17 (por el borrado de Chile/Brasil B y reprogramaciones); los
archivos están íntegros y `verify` pasa. Un sello que vive en la misma base que sella demuestra consistencia
interna, no inmutabilidad frente a terceros.

---

## 8. Qué recibe cada consumidor

| Consumidor | Endpoint | Auth | Contenido real hoy | Motor |
|---|---|---|---|---|
| **App Flutter** | `/mobile/v1/home` | opcional (Bearer) | agenda 7 días con 1X2; alta probabilidad (libres + candados); escalera; planes | A + B |
| App | `/mobile/v1/matches/{id}` | opcional | ficha (forma, H2H, alineaciones, bajas, tabla), pronósticos, tarjeta del modelo, mercados | A + B + C |
| App | `/parley` | opcional (Bearer) | parlays del día (1 gratis, resto VIP) e historial prometido vs. real | B + C |
| App | `/mobile/v1/markets/history` | ninguna | pronósticos resueltos (acertó/falló) | B + C |
| App | `/mobile/v1/rewards*`, `/app/v1/auth*`, `/app/v1/me`, `/app/v1/firebase*` | cuenta | recompensas, sesión, notificaciones | — |
| Web demo | `/`, `/web/partidos`, `/web/partidos/{id}` | ninguna | agenda y fichas | A |
| API pública | `/alta-probabilidad`, `/escalera`, `/parley`, `/track-record`, `/calibration`, `/chain`, `/model-card`, `/picks/free`, `/matches/{id}` | ninguna (`/parley` opcional) | los mismos productos; `/matches/{id}` recorta a 1X2 y totales 2,5 | A + B |
| API de servicio | `/v1/picks`, `/v1/fair-price/{id}`, `/v1/matches/{id}/predictions`, `/v1/fixtures` | `X-Service-Token` | todo sin recorte, incluido precio justo y consenso | A + B |
| Admin | `/admin/*` | `X-Admin-Token` | salud, alias, lanzar trabajos, auditoría de sombra | — |
| Panel | `/control/*` | consola | usuarios, suscripciones, anuncios, recompensas, config de la app | — |
| Cuentas | `/app/v1/picks` | cuenta | picks de valor por tier (hoy vacío) | B |

**Qué ve el usuario de la app** [código `mobile.py`]:
- *Alta probabilidad gratis* (desde 2026-10-27): el **10 % de los publicados en el lote del día, redondeado hacia
  arriba** (`FREE_FRACTION`), los de **mayor probabilidad**, sin rango de cuota (solo exige cuota
  publicada). Se fija por lote en `mobile_free_allocations`; `top_up` completa el
  cupo y `cap_free` lo recorta al leer (los ya empezados siguen visibles y cuentan en el cupo). El resto va con
  candado y solo muestra categoría y cuota. Antes: uno por mercado, mayor cuota ≤ 1,60, hasta 4 abiertos.
- *VIP* (`plus` o desbloqueo por recompensa): ve todo, con probabilidad a 2 decimales, cuota de publicación,
  `fair_price = 1/prob` y las λ implícitas (`xg`).
- *Escalera gratis*: un escalón pendiente entre todos los retos.
- Secciones activas en la app [prod]: agenda, alta probabilidad, escalera, estadísticas, H2H/alineaciones/bajas,
  VIP. Apagadas: NBA, comunidad, notificaciones, balance, medición, idiomas, compras.
- La app **no consume la sombra** ni la tabla `picks` (vacía).

---

## 9. Matriz motor × dato

| Dato | A (propio) | B (mercado) | C (córners/tarjetas) | Solo mostrar |
|---|---|---|---|---|
| Goles | ✔ | — | — | ✔ |
| xG (mezcla 0,65) | ✔ | — | — | ✔ |
| Cuotas Pinnacle | solo entrenamiento/referencia | ✔ (decide) | recorte | — |
| Cuotas casas blandas | — | ✔ (oferta de picks de valor) | — | — |
| Córners / tarjetas históricos | — | — | ✔ | ✔ |
| Árbitro | ✘ | ✘ | ✔ (solo tarjetas) | — |
| Alineaciones / bajas | ✘ | ✘ | ✘ | ✔ |
| Clima | ✘ | ✘ | ✘ | ✘ (sin captura) |
| Tiros / PSxG | ✘ | ✘ | ✘ | ✘ |
| Valor de jugadores | ✘ | ✘ | ✘ | ✘ (challenger en `collecting`) |
| ρ de Dixon-Coles | origen | ✔ (lo toma del A) | — | — |

---

## 10. Estado real de producción (15-oct-2026) [prod]

- Contenedores: `quantfut-worker-1` (imagen `quantfut-worker`), `quantfut-api-1` (`quantfut-api-admob:20261015a`),
  db (Postgres 16), cache (Redis 7), grafana, caddy. Además corren tres contenedores NBA ajenos a este documento.
- Flags relevantes: `PUBLISH_PICKS_ENABLED=0` · `META_BLEND_ENABLED=0` · `RESIDUAL_ENABLED=0` ·
  `ALTA_PROB_ENABLED=1` · `ALTA_PROB_EXT_ENABLED=1` · `ESCALERA_ENABLED=1` · `PARLEY_ENABLED=1` ·
  `DEVIG_METHOD=shin` · `SHARP_BOOK=pinnacle` · `XG_BLEND=0.65` · `KELLY_FRACTION=0.20` ·
  `EDGE_SHRINKAGE=0.55` · `CHAIN_GIT_REMOTE=` (vacío).
- Modelo activo (Motor A): `2026.09.27-010508`.
- Cuentas registradas: 2.

---

## 11. Discrepancias, limitaciones y riesgos

### 11.1 Discrepancias entre README/comentarios y código

1. **Hora del pipeline diario**: un comentario menciona las 13:00; el cron real es `0 9 * * *` (**09:00 UTC**).
2. **Docstring de `/alta-probabilidad`** (`api/main.py`) dice «filtrados al 75–90 %, 10 % gratuito por lote». El
   código usa **73–95 %**; el gratis vuelve a ser el **10 % por lote** (desde 2026-10-27), por mayor probabilidad.
3. **«El modelo predice los picks»**: falso hoy. Los picks de valor usan `model_prob` solo como diagnóstico y
   están apagados; los productos activos salen del Motor B.
4. **Mezcla modelo/mercado**: el peso medido (0,108) existe, pero la mezcla está **apagada**.
5. **Estimación de la puerta comercial** (mía, anterior): «~10-nov» omitía el requisito de ≥ 3 ligas con n ≥ 30.
6. **`model_artifacts.val_metrics.calibration.params.validated`** aparece `false` aunque el `.pkl` aplicado es
   `validated=True`.
7. **Kalman** (`kalman.py`): no interviene en ninguna predicción diaria, solo en evaluación.
8. **Cobertura de los picks de valor**: `select_daily(predictions)` solo vería las 13 ligas con modelo; la sombra
   mide 22. Lo medido en sombra no equivale a lo que se publicaría tal cual está el código.

### 11.2 Limitaciones y riesgos reales

- **Ventaja predictiva no demostrada** en el Motor A: pierde con el mercado en RPS. El valor comercial depende de
  encontrar casas lentas (sombra) o de vender probabilidades de mercado bien presentadas, no del modelo propio.
- **Muestras cortas**: el acierto de alta probabilidad cubre una semana; la sombra, tres. Los IC aún no cierran.
- **Sello sin ancla externa**: nadie fuera del servidor puede comprobar que un lote no se reescribió. Antes de
  configurar `CHAIN_GIT_REMOTE` conviene decidir si se publica el hash «a ciegas» (commit-reveal) para no filtrar
  contenido premium.
- **Pronósticos de 62-73 %** rinden por debajo de lo prometido; hoy no se muestran.
- **Cobertura del Motor A**: 10 de 23 ligas activas no tienen predicción propia (solo cuotas/sombra).
- **Desajuste sombra vs. publicación real** (§4.6).
- **Dependencia de pocas casas**: el valor medido en sombra está concentrado (Ligue 1 y Champions aportan los EV
  más altos; hay ligas con EV negativo).
- **Dos probabilidades por partido en la app** (agenda del A, pronóstico del B), sin etiqueta de fuente salvo
  `fuente: mercado` en la tarjeta de ligas sin modelo.

### 11.3 Qué no verifiqué en esta pasada

- Contenido interno de `escalera_datos.py`, `hashchain._collect` más allá de las tablas que sella, `meta.py`,
  `residual.py`, `elo.py`; las citas vienen de la lectura previa y de los artefactos [no verificado línea a línea
  hoy].
- Código Dart de la app: confirmé qué endpoints llama (`grep`), no cómo pinta cada pantalla.
- No consulté `.env` ni secretos; los flags se leyeron del entorno del contenedor con los secretos enmascarados.
