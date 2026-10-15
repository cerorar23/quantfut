# QuantFut — cómo está construido de verdad el motor y los picks (15-oct-2026)

Documento verificado contra el **código de `main` (commit 5a85376)** y contra **producción en solo lectura**
(worker, API y base de datos del VPS, 15-oct-2026). No parte del README: donde el README, un comentario o un
docstring dicen otra cosa que el código, se marca en la sección 10.

Convención: **[código]** = leído en el repo; **[prod]** = consultado en el servidor; **[no verificado]** = lo digo
pero no lo comprobé en esta pasada.

---

## 1. Resumen ejecutivo

1. **El modelo propio (Dixon-Coles) no genera hoy ningún pick publicado.** Sus salidas alimentan
   `predictions` (probabilidades selladas) y, en la app, el 1X2 de la agenda, la «tarjeta del modelo» que
   acompaña a un pronóstico visible y la lista de mercados del partido. Los pronósticos que el usuario ve como
   producto salen de **cuotas de Pinnacle sin margen** [código + prod].
2. **Hay tres familias de producto y solo una usa el modelo de goles como base de precio:**
   - *Picks de valor* (casa blanda vs. Pinnacle, tabla `picks`): **apagados** (`PUBLISH_PICKS_ENABLED=0`),
     tabla vacía [prod].
   - *Pronósticos de probabilidad* (alta probabilidad, ampliada, escalera, parley): **encendidos** y son lo
     que alimenta la app hoy [prod]. Su probabilidad viene del mercado sharp, no del modelo.
   - *Seguimiento sin publicar*: `tarjetas_seg`, sombra de picks de valor (`sharp_shadow_*`) [prod].
3. **El modelo no le gana al mercado**: RPS 0,1991 frente a 0,1935 del mercado en 1.149 partidos; sí le gana
   a Elo (0,1993) por un margen mínimo [prod, `val_metrics` del artefacto activo]. El peso óptimo modelo/mercado
   medido es 0,108 y la mezcla está **apagada** (`META_BLEND_ENABLED=0`).
4. **La señales nuevas (alineaciones, bajas, clima, árbitro, tiros) se capturan pero NO entran al modelo
   principal.** Las bajas y alineaciones se guardan y se muestran en la ficha; el árbitro solo afecta al modelo de
   tarjetas; el clima no tiene captura en el cron de producción. El único «challenger» de alineaciones está en
   `status: collecting` [prod].
5. **La garantía anti-fraude funciona pero nada se publica fuera del servidor**: 17 lotes sellados, 0 con
   `published_ref` (`CHAIN_GIT_REMOTE` vacío) [prod]. Un sellado que solo vive en la misma base que sella
   demuestra consistencia interna, no inmutabilidad frente a terceros.
6. **Puerta comercial de picks de valor: lejos.** Hay 171 picks «publicables» en sombra, 142 con cierre justo;
   EV al cierre +3,46 % pero sin IC95 (muestra <300), ROI −9,2 % (ruido) y **ninguna liga con n ≥ 30** [prod].

---

## 2. Mapa de datos: de dónde entra cada cosa

### 2.1 Fuentes y cadencia (cron del worker, `scripts/crontab`) [código]

| Dato | Módulo | Cadencia (UTC) | Tabla destino |
|---|---|---|---|
| Cuotas 1X2 y totales de ~20 casas (The Odds API) | `ingest/odds_worker.py` | cada 10 min; `--solo-cierre` en :05-:59/10 | `odds_snapshots` (inmutable) |
| Cuotas API-Football (1X2, goles, goles por equipo) | `ingest/af_odds.py` | :20 de cada hora | `af_odds_snapshots` |
| Ráfagas de latencia de casas blandas | `ingest/rafagas.py` | cada 5 min | tablas de ráfagas |
| Calendario | `ingest/fixtures.py` | 05:15 y 17:15 | `matches` |
| Resultados + estadísticas de partido | `ingest/results.py` | cada 3 h (:45) | `matches` (+ estadísticas) |
| Marcador en vivo | `ingest/live.py` | cada 45 min | `matches.live_*` |
| Clasificación | `ingest/standings.py` | 06:40 y 22:40 | tabla de posiciones |
| Alineaciones confirmadas | `ingest/lineups.py` | cada 5 min | alineaciones |
| Bajas/lesiones | `ingest/injuries.py` | cada 4 h | bajas |
| xG (API-Football) | `ingest/xg_api_football.py` | 12:10 | xG con `xg_recorded_at` |
| xG de respaldo (PitchAPI) | `ingest/pitchapi_respaldo.py` | 12:40 | respaldo/verificación |
| xG histórico + Copas UEFA | `ingest/xg_worldfootball.py`, `uefa_cups.py` | martes 04:00 / 04:30 | `matches` |
| Captura de ofertas para la sombra | `publish/shadow_sharp.py capture` | :25 de cada hora | `sharp_shadow_offers` |
| Salud | `ingest/health.py` | 07:00 | `health_runs` |
| CLV | `eval/clv.py` | 02:30 / 10:30 / 18:30 | CLV por pick |
| Pipeline diario | `publish/daily.py` | **09:00** | ver §5 |
| Verificación de la cadena | `publish/hashchain.py verify` | 06:00 | — |
| Entrenamiento | `model/train.py` | día 1, 03:00 (y `--bootstrap` el resto) | `model_artifacts` |

### 2.2 Histórico y volumen actual [prod]

- `matches`: **93.058** partidos (2012-03-10 → 2026-11-05); 92.353 jugados, 704 programados, 1 aplazado.
- `odds_snapshots`: **460.070** filas (football_data 286.623 · the_odds_api 161.201 ·
  oddspapi_reconstructed 8.754 · the_odds_api_hist 3.492). Las `oddspapi_reconstructed` a >5 min del inicio
  **ya no cuentan como cierre** (`eval/cierre.py::es_cierre_real`, aplicado en entrenamiento, CLV y sombra).
- `predictions`: 281 filas (27-sep → 15-oct), solo 13 ligas con modelo (§3).
- Ligas activas: 23; **con modelo habilitado: 13** (Argentina, Brasil A, Bundesliga, LaLiga, Champions,
  Europa League, Ligue 1, Premier, Serie A, Liga MX, Eredivisie, Primeira, MLS). Las otras 10 (Suiza,
  Bundesliga 2, Dinamarca, LaLiga 2, Ligue 2, Championship, Serie B, Noruega, Suecia, Turquía) tienen cuotas y
  sombra pero **no predicción propia**.

### 2.3 Qué datos usa de verdad el núcleo del modelo [código]

Solo cuatro: **goles, xG (mezcla 0,65), fecha del partido y liga**. Nada más entra en las lambdas:
no hay alineaciones, bajas, clima, árbitro, tiros, valor de jugadores ni ratings Kalman en la predicción
diaria. `model/kalman.py` solo lo importa `eval/early_vs_close.py` (evaluación); `meta.py` y `residual.py`
existen y están entrenados pero apagados.

El mercado entra al **entrenamiento** (como referencia para comparar y para el peso `w_model`) y al
**precio de los productos** (§6), no a las lambdas del modelo.

---

## 3. El modelo, paso a paso [código + prod]

1. **Datos de entrenamiento** (`train.py::load_training_data`): 12 años de `matches` unidos al cierre de
   Pinnacle (`window_tag='close'`, filtrado por `es_cierre_real()`).
2. **Dixon-Coles cuasi-Poisson** (`dixon_coles.py`): ataque/defensa por equipo, ventaja de local y base de goles
   **por liga**, con encogimiento parcial (`POOL_HOME_ADV 25`, `POOL_BASE 25`, `POOL_STRENGTH 300`,
   `SUM_ZERO 1000`, ridge 0,02). Vida media del peso temporal: **180 días**. Equipos indexados por
   (liga, nombre). Guarda de muestra efectiva (`MIN_EFFECTIVE_MATCHES 5`). Lambdas recortadas a ≤ 6.
3. **Objetivo mezclado**: goles reales y xG con `XG_BLEND=0,65` (artefacto: `xg_blend 0.65`, `halflife 180`).
4. **Copas** (Champions/Europa): `matches.league_id` es la competición y `teams.league_id` la liga doméstica; el
   término `strength` entre ligas se cancela exactamente en partidos domésticos (probado a 1e-9).
5. **ρ de Dixon-Coles** global: −0,0613.
6. **Calibrador afín en log-lambda** (`calibration.py`): activo en producción (`cal_2026.09.27-010508.pkl`,
   `validated=True`): a0=0,046, a1=0,882 (local), b0=−0,056, b1=0,965 (visita). Mejora de validación mínima:
   RPS 0,21611 → 0,21588 y log-loss 1,0507 → 1,0481 sobre 1.245 partidos. Si no supera la validación se usa
   la identidad. (El JSON `val_metrics` del artefacto muestra `validated:false` porque se guardó antes de la
   validación; el `.pkl` que se aplica sí está validado.)
7. **Precio**: `pricing.price_all_markets(lam, mu, rho)` construye **una** matriz de marcadores (≈13×13) con la
   corrección τ y de ahí salen **~150 mercados** (1X2, doble oportunidad, EMA, totales, BTTS, hándicap, equipos,
   marcador exacto…). Todos coherentes entre sí.
8. **Mezcla con el mercado** (`meta.py`) y **GBM de residuo** (`residual.py`): entrenados cada mes, **apagados**.
   El peso medido del modelo es 0,1083; la mezcla (RPS 0,18466) casi iguala al mercado (0,18458) y no lo bate.
9. **Activación**: `promotion.py` exige batir a Elo con las mismas filas y datos de mercado frescos. El artefacto
   activo (**2026.09.27-010508**) cumple eso (`promote:true`), no bate al mercado (`beats_market:false`) y no está
   listo para vender picks (`ready_for_commercial_picks:false`, motivo «CLV con muestra insuficiente (0 < 300)»).
   Se entrenaron artefactos posteriores (01-oct, 11-oct, 12-oct) que **no se activaron** [prod].

Benchmarks de validación (n = 1.149) [prod]:

| Modelo | RPS | Log-loss | Brier | ECE |
|---|---|---|---|---|
| Mercado (Pinnacle sin margen) | 0,19345 | 0,96809 | 0,57605 | 0,00914 |
| Dixon-Coles | 0,19910 | 0,98841 | 0,58893 | 0,00744 |
| Elo | 0,19932 | 0,99374 | 0,59152 | 0,01375 |

Lectura honesta: el modelo está bien calibrado (ECE bajo) pero **discrimina menos que el mercado**; no hay
ventaja predictiva demostrada sobre el cierre de Pinnacle.

---

## 4. De-vig y precio justo [código]

- `devig.py`: método por defecto **Shin** (`DEVIG_METHOD=shin`), con `consensus_devig` que pondera casas sharp
  (peso 0,6 para `SHARP_BOOK=pinnacle`).
- `market_anchor.py`: ajusta (λ, μ, ρ) a la terna 1X2 sin margen para derivar goles/hándicap/etc. desde el
  precio sharp en lugar de desde la fuerza de los equipos. Puede devolver `None` si Dixon-Coles no representa la
  terna; entonces no se fuerza.
- Esto es la base de **todos** los pronósticos de probabilidad de §6.

---

## 5. Pipeline diario (`publish/daily.py`, 09:00 UTC = 03:00 CDMX) [código]

Orden estricto, no alterable sin decisión explícita:

1. **Predecir** (`generate_predictions`): lee el artefacto activo, calibrador, meta, residual; para cada partido
   de la ventana (`ventana.py`, margen 60 min) calcula lambdas → calibra → `price_all_markets` → guarda en
   `predictions` (inmutable por trigger). Un fallo por partido no detiene el resto.
2. **Seleccionar picks de valor** solo si `PUBLISH_PICKS_ENABLED` y la puerta comercial está abierta.
   **Hoy: no se ejecuta.**
3. **Productos derivados** (cada uno tras su flag): alta probabilidad, ampliada, tarjetas en seguimiento,
   escalera, parley.
4. **Sellar** (`hashchain.seal`): un lote por día en `prediction_batches` con `payload_sha256`, `prev_sha256`,
   `chain_sha256`. Entra al lote: predicciones, picks, `alta_prob_picks`, `alta_prob_ext`, `escalera_retos`
   (+ tickets/patas del parley).
5. **Publicar** (Telegram, best-effort; el negocio no usa Telegram para picks).

Estado de la cadena [prod]: **17 lotes**, último 15-oct, 0 con referencia externa. Los lotes se regeneran desde
la base solo en 9 de 17 (por el borrado de Chile/Brasil B y reprogramaciones); los archivos están íntegros y
`verify` pasa.

---

## 6. Los productos, uno por uno

### 6.1 Picks de valor (`publish/picks.py`) — APAGADO [código + prod]

- Idea: casa blanda paga más que el precio justo de Pinnacle (Shin). **Solo 1X2.** Edge mínimo 2 %.
  `model_prob` es solo diagnóstico, no decide.
- Prior de persistencia por casa mezclado con la sombra; `EDGE_SHRINKAGE=0,55`.
- Stake: Kelly 0,20 con tope 2 u, factor de incertidumbre Baker-McHale, topes de cartera.
- Reparto: `assign_tiers()` — los 2 mejores del día (`FREE_PICKS_PER_DAY=2`) son free, el resto paid.
- Entrega: `picks_for_tiers` (`comercial/entrega.py`), ordenado por `edge_pct`.
- Estado: `PUBLISH_PICKS_ENABLED=0`; **tabla `picks` con 0 filas** [prod]. `/app/v1/picks` devuelve lista vacía
  y `publicacion_activa:false`.

### 6.2 Sombra de picks de valor (`publish/shadow_sharp.py`) [código + prod]

- Cada hora (:25) captura todas las ofertas de las próximas 72 h y decide como si fuera a publicar.
  «Publicable» = primera oferta con stake por partido. Se liquida contra el cierre sharp.
- Totales [prod]: 1.498 ofertas, 1.356 liquidadas; **171 publicables, 142 con cierre justo**.
  `edge_early` +4,83 %, `ev_close` +3,46 %, `roi` −9,2 %, `ev_close_ci95: null`.
- **Puerta** (`promotion.evaluate_clv_gate`): n ≥ 300, límite inferior del IC95 de `ev_close` > 0 y ≥ 3 ligas con
  n ≥ 30. Hoy: n = 171; la liga más grande tiene 14 (MLS). **No está cerca.** Ritmo ≈ 8 publicables/día
  → 300 hacia finales de octubre; pero 3 ligas con 30 cada una no antes de mediados de noviembre y probablemente
  después. Esto corrige mi estimación anterior («~10-nov»), que ignoraba el requisito de ligas.
- **Desajuste de política**: la sombra decide a cualquier antelación; la publicación real ocurriría una vez al día
  a las 09:00. Lo medido en sombra no es idéntico a lo que se publicaría (es lo que busca resolver F7).

### 6.3 Alta probabilidad y ampliada (`alta_prob*.py`) — ENCENDIDO [código + prod]

- Probabilidad: **Pinnacle sin margen**. Goles/hándicap/equipos con lambdas ancladas al mercado
  (`market_anchor`); córners con el modelo estadístico (binomial negativa, `estadisticas_mercado.py`)
  recortado al mercado.
- Sellado base 80-95 %; ampliada (`ALTA_PROB_EXT_ENABLED=1`) desde 62 %. **La app solo muestra 73-95 %**
  (`mobile.HIGH_MIN/HIGH_MAX`): es un filtro de lectura, las filas inmutables no se tocan.
- Control de calidad: pausa por desviación (z ≤ −4 / IC99).
- Volumen [prod]: base **172** picks (8 → 15-oct: 136 aciertos, 29 fallos, 4 nulos, 3 pendientes); ampliada **751** (514 / 180 / 25 / 32).
- Acierto vs. prometido [prod]: base 82,4 % real vs 82,4 % prometido (n = 165); ampliada total 74,1 % vs 77,2 %
  (n = 694), pero **en el tramo que ve la app (73-95 %) 81,9 % vs 82,3 % (n = 452)**. Lo que cae por debajo
  de 73 % rinde por debajo de lo prometido y ya no se muestra. Muestra de **una semana**: es indicio, no prueba.
- Mercados de la base: hándicap 50 · totales 31 · doble oportunidad 28 · córners 33 (18+10+5) ·
  goles de equipo 25 · 1X2 5.

### 6.4 Escalera (`escalera*.py`) — ENCENDIDO [código + prod]

- Retos de 3-6 escalones, cuotas 1,25-1,40, se elige el escalón **más probable**; **no hay filtro de valor**.
  Freeroll 2,5×, stake 10. 4 retos en total [prod].
- La app muestra escalones con probabilidad 75-90 %; uno gratis por lote, el resto con candado.

### 6.5 Parley (`parley*.py`) — ENCENDIDO [código + prod]

- 1 a 5 parlays al día, escalones de cuota 1,90-5,00, patas de cuota 1,20-1,80, elegido por probabilidad, no por
  valor. 10 tickets y 9 resultados hasta hoy [prod]. Gratis el de menor escalón; los liquidados se ven siempre.
- Expuesto en `/parley` (API pública). **La app Flutter lo consume** (`product/live_parley.dart` llama a `/parley`; se verificó con `grep` del código Dart) con el mismo acceso (`plus` por Bearer).

### 6.6 Tarjetas en seguimiento (`tarjetas_seg.py`) [código + prod]

- Seguimiento sin publicar (3 filas). Usa el modelo de árbitro: el único sitio donde el árbitro influye.

### 6.7 Modelo de córners/tarjetas (`estadisticas_mercado.py`) [código]

- Binomial negativa con decaimiento, priors y factor de árbitro (`PRIOR_ARBITRO 10`) solo para tarjetas. Solo se
  usan líneas validadas (`LINEAS_HABILITADAS`).

---

## 7. Qué recibe cada consumidor

| Consumidor | Endpoint | Auth | Contenido real hoy |
|---|---|---|---|
| **App Flutter** | `/mobile/v1/home` | opcional (Bearer) | agenda 7 días con 1X2 del modelo; alta probabilidad (libres + candados); escalera; planes |
| App | `/mobile/v1/matches/{id}` | opcional | ficha (forma, H2H, alineaciones, bajas, tabla), pronósticos del partido, «tarjeta del modelo», mercados |
| App | `/parley` | opcional (Bearer) | parlays del día (1 gratis, resto VIP) e historial prometido vs. real |
| App | `/mobile/v1/markets/history` | ninguna | pronósticos resueltos (acertó/falló) |
| App | `/mobile/v1/rewards*`, `/app/v1/auth*`, `/app/v1/me`, `/app/v1/firebase*` | cuenta | recompensas, sesión, notificaciones |
| Web demo | `/`, `/web/partidos`, `/web/partidos/{id}` | ninguna | agenda y fichas |
| API pública | `/alta-probabilidad`, `/escalera`, `/parley`, `/track-record`, `/calibration`, `/chain`, `/model-card`, `/picks/free`, `/matches/{id}` | ninguna (`/parley` opcional) | los mismos productos; `/matches/{id}` recorta a 1X2 y totales 2,5 |
| API de servicio | `/v1/picks`, `/v1/fair-price/{id}`, `/v1/matches/{id}/predictions`, `/v1/fixtures` | `X-Service-Token` | todo sin recorte, incluido el precio justo y el consenso |
| Admin | `/admin/*` | `X-Admin-Token` | salud, alias, lanzar trabajos, auditoría de sombra |
| Panel | `/control/*` | consola | usuarios, suscripciones, anuncios, recompensas, config de la app |
| Cuentas | `/app/v1/picks` | cuenta | picks de valor por tier (hoy vacío) |

**Qué ve el usuario de la app** [código `mobile.py`]:
- *Alta probabilidad gratis*: **un pronóstico por mercado**, el de **mayor cuota publicada** con tope 1,60
  (sin piso), y como mucho **4 abiertos a la vez** (`FREE_MAX`). Se fija por lote en `mobile_free_allocations`
  y solo se **añade**, nunca se retira uno ya mostrado. El resto va con candado y solo muestra categoría y cuota.
- *VIP* (`plus` o desbloqueo por recompensa): ve todo, con probabilidad redondeada a 2 decimales, cuota de
  publicación, `fair_price = 1/prob` y las λ implícitas (`xg`).
- *Escalera gratis*: un escalón pendiente entre todos los retos.
- La **tarjeta del modelo** (probabilidades de 1X2, +1,5/+2,5, ambos marcan) solo sale junto a un pronóstico
  visible. En ligas sin modelo propio sale de las λ del ajuste a Pinnacle y se etiqueta `fuente: mercado`.
- Secciones activas en la app [prod]: agenda, alta probabilidad, escalera, estadísticas, H2H/alineaciones/bajas,
  VIP. Apagadas: NBA, comunidad, notificaciones, balance, medición, idiomas, compras.

---

## 8. Matriz componente × dato

| Componente | Goles | xG | Cuotas Pinnacle | Cuotas casas blandas | Bajas/XI | Árbitro | Clima | Estadísticas (córners/tarjetas) |
|---|---|---|---|---|---|---|---|---|
| Dixon-Coles (lambdas) | ✔ | ✔ (0,65) | — (solo entrenamiento/referencia) | — | ✘ | ✘ | ✘ | ✘ |
| Calibrador | ✔ (derivado) | ✔ | — | — | ✘ | ✘ | ✘ | ✘ |
| Picks de valor (apagado) | — | — | ✔ (precio justo) | ✔ (oferta) | ✘ | ✘ | ✘ | ✘ |
| Alta probabilidad | — | — | ✔ (probabilidad) | — (cuota de referencia) | ✘ | ✘ | ✘ | ✔ (córners) |
| Escalera | — | — | ✔ | — | ✘ | ✘ | ✘ | ✔ |
| Parley | — | — | ✔ | — | ✘ | ✘ | ✘ | ✔ |
| Tarjetas (seguimiento) | — | — | ✔ | — | ✘ | ✔ | ✘ | ✔ |
| Ficha del partido | ✔ | — | — | — | ✔ (solo mostrar) | — | — | ✔ (mostrar) |

---

## 9. Estado real de producción (15-oct-2026) [prod]

- Contenedores: `quantfut-worker-1` (imagen `quantfut-worker`), `quantfut-api-1` (`quantfut-api-admob:20261015a`),
  db (Postgres 16), cache (Redis 7), grafana, caddy. Además corren tres contenedores NBA ajenos a este documento.
- Flags relevantes: `PUBLISH_PICKS_ENABLED=0` · `META_BLEND_ENABLED=0` · `RESIDUAL_ENABLED=0` ·
  `ALTA_PROB_ENABLED=1` · `ALTA_PROB_EXT_ENABLED=1` · `ESCALERA_ENABLED=1` · `PARLEY_ENABLED=1` ·
  `DEVIG_METHOD=shin` · `SHARP_BOOK=pinnacle` · `XG_BLEND=0.65` · `KELLY_FRACTION=0.20` ·
  `EDGE_SHRINKAGE=0.55` · `CHAIN_GIT_REMOTE=` (vacío).
- Modelo activo: `2026.09.27-010508`.
- Cuentas registradas: 2.
- Predicciones por liga (27-sep → 15-oct): Argentina 47, MLS 46, Brasil 24, LaLiga/Premier/Serie A 20 cada una,
  Primeira/Bundesliga/Champions/Ligue 1/Eredivisie 18, Liga MX 12, Europa League 2.

---

## 10. Discrepancias encontradas (README/comentarios vs. código)

1. **Hora del pipeline diario**: un comentario menciona las 13:00; el cron real es `0 9 * * *` (**09:00 UTC**).
2. **Docstring de `/alta-probabilidad`** (`api/main.py`) dice «filtrados al 75–90 %, 10 % gratuito por lote». El
   código usa **73–95 %** y el gratis es **un pronóstico por mercado, hasta 4 abiertos, cuota ≤ 1,60**.
3. **Mezcla modelo/mercado**: el peso medido (0,108) existe, pero la mezcla está **apagada**; los productos no
   usan «probabilidad del modelo» sino la del mercado.
4. **«El modelo predice los picks»**: falso hoy. Los picks de valor usan `model_prob` solo como diagnóstico y están
   apagados; los productos activos no usan el modelo de goles para decidir.
5. **Estimación de la puerta comercial** (mía, anterior): «~10-nov» omitía el requisito de ≥ 3 ligas con n ≥ 30.
6. **`model_artifacts.val_metrics.calibration.params.validated`** aparece `false` aunque el `.pkl` aplicado es
   `validated=True` (se serializa antes de validar).
7. **Kalman** (`kalman.py`): citado como «existe», pero no interviene en ninguna predicción diaria.

---

## 11. Limitaciones y riesgos reales

- **Ventaja predictiva no demostrada**: el modelo pierde con el mercado en RPS. El valor comercial depende de
  encontrar casas lentas (sombra) o de vender análisis/probabilidades de mercado, no del modelo.
- **Muestras cortas**: el acierto de alta probabilidad cubre una semana; la sombra, tres. Los IC aún no cierran.
- **Sello sin ancla externa**: nadie fuera del servidor puede comprobar que un lote no se reescribió. Antes de
  configurar `CHAIN_GIT_REMOTE` conviene decidir si se publica el hash «a ciegas» (commit-reveal) para no filtrar
  contenido premium.
- **Pronósticos de 62-73 %** rinden por debajo de lo prometido; hoy no se muestran.
- **Cobertura de modelo**: 10 de 23 ligas activas no tienen predicción propia (solo cuotas/sombra).
- **Desajuste sombra vs. publicación real** (§6.2).
- **Dependencia de pocas casas**: el valor medido en sombra viene muy concentrado (Ligue 1 y Champions aportan
  los EV más altos; hay ligas con EV negativo).
- **La app no consume la sombra de picks de valor** ni la tabla `picks` (que está vacía); lo que muestra sale de los productos de §6.3-6.5.

---

## 12. Qué no verifiqué en esta pasada

- Contenido interno de `escalera_datos.py`, `hashchain._collect` más allá de las tablas que sella, `meta.py`,
  `residual.py`, `elo.py`; las citas sobre ellos vienen de la lectura previa y de los artefactos [no verificado
  línea a línea hoy].
- Código Dart de la app: confirmé qué endpoints llama (`grep`), no cómo pinta cada pantalla.
- No consulté el contenido de `.env` ni de secretos; los flags se leyeron del entorno del contenedor con los
  secretos enmascarados.
