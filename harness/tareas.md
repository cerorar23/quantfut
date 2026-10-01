# Backlog — QuantFut

Orden de dependencia (ver "Huecos concretos que quedan" en README.md).
No reordenar sin razón: cada ítem depende del anterior.

## Decisión de alcance (2026-09-21)

El usuario **no usa Telegram**. La venta de picks es 100% en su web propia.
El bot de Telegram y el auth por Telegram quedan fuera de alcance (no se
borran, pero no se desarrollan más). Prioridad actual: la API que sirve
predicciones a la web. Auth de suscriptor no-Telegram y cobros son "después",
no ahora.

## Pendientes 🔴

## Más picks sin relajar la puerta comercial (2026-09-25)

Orden experimental solicitado; ningún resultado cambia `publish/picks.py`,
`SOFT_MIN_EDGE_PCT` ni activa `PUBLISH_PICKS_ENABLED` por sí solo.

- [x] Instrumentar en solo lectura primera cuota observada, edad conocida y
      cobertura por fuente, casa y liga (`eval/quote_coverage.py`).
      `first_seen` no equivale a apertura real; The Odds API no conserva aquí
      la hora propia del bookmaker, y se reporta desconocida, nunca cero.
- [ ] Ejecutar esa auditoría en el Postgres operativo y decidir con esos
      datos si merece ampliar la captura más allá de T−72.
- [x] Comparar Shin/Power y umbrales 1–3% sobre las mismas cuotas pre-cierre
      1X2; cierre justo fijo, hash del dataset, muestra por casa e IC agrupado
      por semana (`eval/sharp_challengers.py`). Resultado exploratorio en
      `progreso.md`; no demuestra que las cuotas sigan disponibles.
- [ ] Ensayar un consenso multifuente solo cuando haya snapshots
      sincronizados, horquilla y liquidez verificables.
- [ ] Validar prospectivamente cualquier variante contra el 2% actual en
      sombra: CLV justo, cuota alcanzable, ligas/casas y riesgo. No optimizar
      y certificar sobre los mismos partidos.
- [ ] Reabrir un mercado derivado solo si una nueva muestra con la misma
      línea y cierre sharp contradice el ensayo negativo archivado.
- [ ] Ensayar filtro de acuerdo Dixon-Coles/mercado solo como ablación
      condicional; no subir stakes antes de evidencia incremental.

## Plan de integración web + administración en un solo FastAPI (2026-09-23)

Decisión del usuario posterior al prototipo: avanzar hacia **un backend
FastAPI modular único** para API, web y administración. Esto sustituye la
necesidad de un BFF como segundo servicio, no la separación de permisos:
el navegador nunca verá `SERVICE_TOKEN` ni `ADMIN_TOKEN`.

- [x] Servir el prototipo de `frontend/` desde el FastAPI existente, sin
      cambiar su carácter de demo ni llamar a rutas privadas desde JS.
- [x] Añadir un panel de operación inicial de solo lectura, con autenticación
      humana independiente del token de API y sin credenciales predeterminadas.
- [x] Restringir `/admin` y el panel también en Caddy por IP, como Grafana.
- [x] Probar el aislamiento de rutas y actualizar despliegue/documentación.
- [ ] Fase comercial posterior: cuentas, sesiones, suscripciones y cobros
      dentro de este mismo backend, solo tras superar la puerta de CLV.

- [x] **API — sin cuentas de usuario, servicio único para el frontend
      (2026-09-22).** El usuario corrigió el alcance más temprano el mismo
      día: la API NO gestiona suscriptores, login ni cobros. Los pronósticos se sirven a un único cliente de confianza — el
      backend de su frontend (BFF) — que es quien maneja usuarios, pagos y
      arma los prompts del LLM. Ni el navegador ni la futura app Flutter le
      hablan a esta API directamente: le hablan al backend del frontend, y
      solo ese backend conoce el secreto de esta API. Motivo: un secreto
      embebido en un cliente que corre en el dispositivo del usuario (JS de
      navegador, binario Flutter) siempre se puede extraer con ingeniería
      inversa; uno que vive solo en un servidor, no.
      - Se revirtió por completo el trabajo de auth de suscriptor de la
        entrada anterior (`db/015_subscriber_auth.sql` eliminado antes de
        aplicarse a ningún Postgres real; `src/qf/api/auth.py` eliminado).
      - `/v1/*` ahora se protege con `require_service` (`X-Service-Token`
        contra `SERVICE_TOKEN` en `.env`, comparación en tiempo constante,
        404 si no coincide — mismo patrón que `require_admin`). Sin recorte
        de tier: quien presenta el token de servicio recibe TODOS los picks;
        el recorte free/paid para cada usuario final lo decide el backend
        del frontend con su propia base de datos, no esta API.
      - `POST /v1/auth/*` (register/login/refresh/logout/telegram)
        eliminados: no hay usuario final que autenticar a nivel de API.
      - Rate limiting por IP se mantiene (`src/qf/api/ratelimit.py`,
        movido desde el `auth.py` eliminado) — sigue haciendo falta aunque no
        haya cuentas: sin él, un service token filtrado permite scraping sin
        límite.
      - `PyJWT`, `argon2-cffi` y `email-validator` se quitaron de
        `requirements.txt`: dependencias que ya no tienen ningún consumidor.
      **Nota para cuando construyas el backend del frontend:** la tabla
      `subscribers` de `db/001_schema.sql` (con `email`, `tier`, `telegram_id`)
      ya no tiene ningún consumidor en esta API — si vas a manejar cuentas de
      pago, esa base de datos vive en tu backend de frontend, no aquí.
- [ ] **API — cobros.** Webhook del procesador de pago → `UPDATE subscribers`.
      Cero código hoy. Pospuesto.
- [x] **API — rate limiting** en las rutas públicas (revisado 2026-09-24).
      Ya existía como middleware global (todas las rutas, 60/min, Redis).
      Dos fallos corregidos: `/control` comparaba su tope de 10 contra el
      MISMO contador que la web y sus estáticos (el panel daba 429 al
      operador), y en IPv6 se contaba por dirección, esquivable rotando dentro
      del /64 del cliente. Ahora `/control` tiene contador propio e IPv6 se
      agrupa por /64. Verificado en producción con una petición IPv6 real.
- [x] **Proxy TLS (Caddy) como servicio de `docker-compose.yml`.** Antes solo
      estaba documentado como paso manual en el host (README). Ahora hay un
      `Caddyfile` en la raíz y un servicio `caddy` que expone 80/443, resuelve
      certificado solo, y proxea `api:8000` / `grafana:3000` por la red interna
      de Compose. Requiere `DOMAIN` y `GRAFANA_ALLOWED_IP` en `.env`
      (`.env.example` actualizado). Grafana sigue cerrado por IP + login.
- [x] **Ingesta de bajas/lesiones.** Decidido 2026-09-22: FUENTE es el
      endpoint `/injuries` de API-Football (mismo proveedor ya contratado,
      plan Pro), no un LLM leyendo prensa — dato ya estructurado, coste
      incremental $0. Implementado en `src/qf/ingest/injuries.py` +
      `db/014_injuries.sql`, en crontab cada 4h. Ver harness/progreso.md.
- [ ] **Feature de disponibilidad a partir de bajas.** `injuries.py` solo
      ingiere y almacena, igual que hizo `lineups.py` en su fase inicial.
      Falta un equivalente a `lineups.availability()` que combine bajas +
      XI confirmado en una feature de `residual.py`. Requiere haber
      acumulado datos primero.
- [x] **Vigilancia del hueco de cobertura de `/injuries`.**
      `health.check_injuries_coverage()` detecta si alguna liga acumula
      `INJURIES_MIN_MATCHES` (15) partidos comprobados en 30 días sin NINGUNA
      baja reportada — la misma firma de "array vacío con status 200" que el
      xG. `mx.liga_mx`/`ar.primera`/`pt.primeira` ya confirmadas
      (`KNOWN_INJURY_COVERAGE_GAPS`) no vuelven a alertar cada día; una liga
      NUEVA con el mismo patrón sí dispara el chequeo diario.
- [x] **HECHO (2026-09-29, decisión del usuario: "sí, con límites") —
      Entrenar YA el ajuste por XI con alineaciones históricas.** 4.555 XI
      descargados (11 ligas; copas sin emparejar), 3.988 partidos útiles en
      el último año (se exigen 700). Se entrena en el reentreno mensual del
      1-oct 03:00 UTC: comprobar `val["lineup_challenger"]` (ok, n_fit,
      RPS/log-loss/ECE antes y después, ligas que mejoran) y que la sombra
      muestre `lineup_challenger_available: true` desde el 9-oct. Bloqueo
      medido: el challenger exige 700 partidos con predicción sellada + XI
      capturado antes del inicio; había 4 y 21 (modelo activo desde el
      27-sep, XI desde el 26-sep): llegaría hacia diciembre. Plan:
      1. [x] db/034 `lineups_historicas`, tabla APARTE: ni la sombra ni la
         predicción diaria la leen; solo el entrenamiento/validación del
         challenger. El XI se descarga tras el partido (el publicado a T-60
         casi siempre coincide): esa es la excepción al punto en el tiempo
         que el usuario autorizó, y no va más allá.
      2. [x] `ingest/lineups_historicas.py`: empareja los partidos del último
         año de las ligas con modelo con su fixture de API-Football (por
         `af_team_id` o alias exacto, ±36 h) y baja su XI. Reanudable, con
         reserva de cuota para la operación diaria.
      3. [x] El challenger se entrena con las predicciones fuera de muestra
         que `train.py` YA calcula (walk-forward del último año, ahora con su
         rho) + esos XI, además de los partidos en vivo. Mismas exigencias de
         validación (RPS, log-loss, ECE, ≥2 ligas) y promoción solo con CLV
         en sombra.
      4. [x] La sombra usa el último challenger validado si el del modelo
         activo no existe (un reentreno no promovido dejaba el brazo sin
         artefacto).
- [ ] **Fuerza por jugador (diseño aprobado 2026-09-29,
      `docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md`).**
      - [x] Fase A, datos (plan `docs/superpowers/plans/2026-09-29-fuerza-por-jugador-fase-a-datos.md`):
        db/035, `ingest/estadisticas_jugador.py`, captura al cerrar en
        `results.py`. Histórico descargado el 30-sep: 4.556 partidos, 141.458
        filas de jugador, 11 partidos sin datos.
      - [x] Fase B1, valores y comparación offline (plan
        `docs/superpowers/plans/2026-09-30-fuerza-por-jugador-fase-b1-valores.md`),
        hecha el 1-oct. "XI con valor" EMPEORA a la base (RPS 0,21818 →
        0,21912) y no gana al XI simple: no se valida. La comparación queda
        en el reentreno mensual (`val["player_value"]`) por si la muestra
        cambia la lectura.
      - [ ] ~~Fase B2, sombra en vivo~~ DESCARTADA mientras el reentreno
        mensual no muestre `player_value.valor.gana_al_simple = true`.
- [x] **HECHO (1-oct, decisión del usuario: opción B) — criterio de ECE
      del XI.** Ahora la calibración no puede empeorar más allá de su propio
      ruido (remuestreo pareado). El XI simple del reentreno del 1-oct queda
      validado y la sombra lo usa desde el 9-oct (vuelta de las ligas).
      Comprobar entonces `lineup_challenger_available: true` y que se
      registren los cuatro brazos; nada se publica sin CLV en sombra.
- [ ] **Validar el ajuste de XI con datos nuevos.** El challenger que estima
      ajustes separados sobre `log(lambda_home)` y `log(lambda_away)` y su
      ejecución en sombra ya existen, pero las tablas de predicciones y XI
      locales están vacías. Activar la captura, acumular muestra y exigir
      mejora fuera de muestra, calibración y CLV frente al baseline T-60 en
      varias ligas antes de promoverlo. Ratings por jugador quedan para una
      iteración posterior si el volumen lo permite.
- [ ] **Umbral de abstención basado en incertidumbre.** Antes de publicar un
      pick, distinguir edge medible de diferencias dentro del ruido del
      modelo. Estimar un umbral propio mediante bootstrap o variación entre
      reentrenamientos; no copiar constantes de otros sistemas ni confundir
      este filtro con el `edge_shrinkage` existente. Requiere suficiente
      histórico de predicciones point-in-time y cierres.
- [ ] **Fase 2 — superar el mercado sharp actual.** Elo ya está implementado
      y medido sobre las mismas 1.907 observaciones que Dixon-Coles/Pinnacle:
      RPS 0,20533 / 0,20245 / 0,19561. El baseline mejora, pero el mercado
      sigue delante y sus últimas cuotas locales son de enero de 2026.
      Reformulado por 2.A (abajo): el objetivo ya no es batir al cierre en RPS
      sino la puerta de CLV sobre la sombra sharp. Lo que queda es muestra.
- [x] **Poner el cron en marcha de verdad (2026-09-23).** Plan Pro de
      API-Football ya viable. The Odds API se subió al plan de pago de 20.000
      créditos/mes (nueva `ODDS_API_KEY` en `.env`). Configuración final:
      solo `eu` x `h2h,totals,spreads` (~5.800 créditos/mes), para dejar
      ~14.000 al endpoint histórico. `scripts/crontab`
      ya traía `odds_worker` cada 10 min sin comentar — con clave y crédito
      reales, `odds_worker` puede dejar de ejecutarse a mano. Pendiente real:
      desplegar el contenedor/cron de verdad (no se puede verificar Docker en
      este entorno) y confirmar en la práctica que no se agota el crédito
      antes de fin de mes.
- [~] **Extender la mezcla al hándicap asiático.** Superado (2026-09-24): la
      premisa era que ampliarlo "devolvería el AH al universo de picks", pero
      desde el paso 4 los picks salen del criterio sharp, solo 1X2, y no de
      las probabilidades mezcladas. Con `META_BLEND_ENABLED=0` y
      `w_model≈0` no cambia nada publicable. Reabrir solo si se vuelve a
      querer AH en el criterio sharp (entonces es trabajo de `find_candidates`,
      no de `_apply_blend`).
- [ ] **Frontend de la web (Fase 3, posterior).** El prototipo visual vive en
      `frontend/`; la aplicación comercial todavía no existe y consumirá la
      API cuando los pendientes de las fases anteriores estén estabilizados.
      Se tomó Pitchverse como referencia de composición visual y navegación,
      sin copiar su código, modelos ni contenido. `Pa004/scikick` queda como
      referencia adicional para posibles páginas de partido, mercados,
      calibración, temas e i18n. El frontend final deberá adaptarse a los
      endpoints y criterios de selección propios de QuantFut.
      - [x] Prototipo navegable en modo demo: seis vistas (inicio, picks
        gratuitos, ficha de partido, historial verificable, planes y área de
        suscriptor), inspirado visualmente en la navegación de Pitchverse,
        sin cobros, login real ni acceso a `/v1/*` desde el navegador.
      - [x] Definir guía visual propia (tokens, componentes, móvil y
        accesibilidad) y aplicarla a las seis vistas del prototipo, usando
        `ui-ux-pro-max-skill` solo como catálogo de referencia, no como
        dependencia ni como sustituto de la arquitectura FastAPI.
      - [x] **Mesa de mercados y rediseño de las seis vistas (2026-09-24).**
        Tras analizar propsbr.app (buscador de props por acierto L5/L10),
        se adopta su COMPOSICIÓN —lista de partidos por fecha y liga, tabla
        densa ordenable con minigráfico, detalle lateral con pestañas,
        columna de destacados, formato de cuota— pero NO su contenido:
        nada de "certeras/seguras" ni notas 0-100 sin calibrar. La mesa
        enseña lo que el sistema de verdad mide: precio justo de Pinnacle
        sin margen, mejor casa blanda de la lista, % sobre el justo en el
        mismo snapshot, `min_price`, exclusión por Pinnacle fuera de
        consenso y la sombra del criterio (solo 1X2, publicación pausada).
        El modelo aparece como diagnóstico, no como selector. Los precios
        demo salen de dos lambdas (Poisson) para que todas las vistas
        cuadren entre sí. Sigue siendo demo: sin API, sin cobros.
      - [ ] Integración comercial posterior: suscriptores, pagos y
        autorización en módulos del mismo FastAPI; condicionada a la puerta
        de validación del producto. El BFF separado de la decisión anterior
        queda sustituido por el plan 2026-09-23 de esta página.
- [ ] **Fase 5 — movimiento de línea.** Requiere 12 meses de snapshots.
- [x] **`soccerdata` retirado (2026-09-24, decisión del usuario).** Borrado
      `src/qf/ingest/xg_fbref.py` (nadie lo importaba) y quitados de
      `requirements.txt` `soccerdata`, `lxml` y `html5lib` (ningún código
      usaba los dos últimos). Los alias con fuente `fbref` se QUEDAN: los usan
      `xg_worldfootball` y `uefa_cups`. Texto original:
      Está fijado a 1.8.7, entra en
      conflicto con `lxml==5.3.0` y `pip install -r requirements.txt` falla con
      ResolutionImpossible. Queda comentado. Solo lo usa `xg_fbref.py`, que el
      README ya da por inservible (Cloudflare). O se borra el módulo o se
      afloja el pin.
- [ ] **¿Bélgica, Rusia, Ucrania, Turquía, Grecia?** Sumarían ~1.160 cruces
      europeos más, pero son cinco ligas para menos muestra de la que dieron
      tres. Rendimientos decrecientes claros: hacerlo solo si se quieren esas
      ligas por sí mismas, no por el término `strength`.

## Plan de la Fase 2 (2026-09-22) — replantear la puerta, no atacarla más fuerte

Punto de partida, ya medido y no discutible sin datos nuevos: sobre n=28.128
predicciones fuera de muestra el modelo pierde en las 7 ligas y
**`w_model = 0.0001`**. El peso óptimo del modelo en la mezcla con el mercado
es CERO. Dos motores independientes (Dixon-Coles con decaimiento y filtrado
bayesiano) aterrizan en el mismo sitio. El diagnóstico del `progreso.md` es
correcto: falta INFORMACIÓN, no técnica.

De ahí se sigue que **más matemática sobre los mismos datos no cierra el
hueco**, y que la puerta actual ("RPS del modelo < RPS del cierre") pide algo
que casi nadie consigue y que además no es lo que hace falta para vender.

### 2.A — Cambiar el objetivo: el cierre no es el rival ✅ IMPLEMENTADO

Son dos afirmaciones distintas y solo una es alcanzable:

  1. "Mi probabilidad es mejor que el consenso de cierre."  -> inalcanzable.
  2. "El precio que puedo tomar AHORA es peor que el cierre que vendrá."
     -> alcanzable, medible, y es exactamente el CLV.

Propuesta: la puerta de la fase 2 pasa a ser **CLV positivo con intervalo de
confianza sobre el precio realmente disponible**, y el precio justo se
construye del **consenso sharp de-vigado (Pinnacle + Betfair)**, no de
Dixon-Coles. El modelo deja de ser la fuente del edge y pasa a ser filtro y
desempate.

Cambia el producto, y conviene decirlo en voz alta: QuantFut deja de afirmar
"nuestro modelo bate a Pinnacle" y pasa a afirmar "detectamos casas blandas que
todavía no han convergido al precio sharp". Es honesto, es medible y **toda la
maquinaria ya existe**: 22 casas vía The Odds API, `consensus_devig` con peso
sharp, y el line shopping de `_best_prices`.

Límite real de ese negocio, para no descubrirlo tarde: no lo acota el modelo,
lo acota que las casas blandas limitan cuentas. Eso es operación, no código.

- [x] Puerta redefinida: `promotion.evaluate_clv_gate`. Exige IC del 95% del
      CLV entero por encima de cero, 300 apuestas y 3 ligas con muestra. Batir
      al cierre en RPS se sigue REPORTANDO pero ya no veta.
- [x] `eval/clv.clv_report` / `summarize_clv`: CLV con IC bootstrap y desglose
      por liga.
- [x] `GET /fair-price/{match_id}`: consenso sharp sin margen, intensidades
      implícitas y distancia de la mejor casa al precio justo.
- [x] `/model-card` publica si la puerta comercial está autorizada y por qué no.
- [ ] Frontend que consuma `/fair-price` (fase 3).
- [x] Desglose por VENTANA (t72/t24/close). Cubierto por `shadow_sharp.report`
      (`by_lead`, en publicables y en todas las ofertas), que es la muestra
      que decide la puerta; desde 2026-09-24 visible también en `/control`.
      Para `pick_results` no hace falta mientras la publicación siga pausada.

### 2.B — Anclar el residuo en el MERCADO, no en el modelo ✅ IMPLEMENTADO

Bug de diseño que se ve al leer `w_model ≈ 0` junto a `lineup_challenger.py`:
`apply()` multiplica `base_lam`, y `base_lam` viene de
`predictions.home_lambda`, es decir **las lambdas del modelo**. Si el modelo
vale cero frente al mercado, ajustar por el XI unas lambdas peores solo mueve
una estimación peor.

La única construcción en la que el XI es información ADITIVA a lo ya preciado:

    1. de-vigar el 1X2 (y los totales si están) del consenso sharp a T-60;
    2. invertir esas probabilidades a (lambda, mu) ajustando la matriz de
       marcadores de Dixon-Coles -> 2 parámetros por partido;
    3. aplicar encima  exp(beta · x_XI)  con los mismos betas ya estimados.

Así el modelo aporta la ESTRUCTURA (la matriz de marcadores, los ~150 mercados
coherentes) y el mercado aporta el NIVEL. Es la lectura correcta de w_model=0:
no "el modelo no sirve", sino "el modelo sirve para la forma, no para el nivel".

- [x] `model/market_anchor.py`: inversión de 1X2 de-vigado a (lambda, mu), con
      residuo obligatorio porque la familia no representa cualquier terna.
- [x] `model/shadow.py` gana dos brazos: `baseline_market` y
      `lineup_lambda_market`. Los cuatro sobre las mismas cuotas, de modo que
      cada comparación aísla una sola cosa.
- [ ] Acumular muestra y comparar los cuatro brazos. Es lo único que falta y no
      se acelera con código. Bloqueo real encontrado el 2026-09-24:
      `qf.model.shadow` responde "sin modelo activo" en cada pasada, así que
      los brazos no acumulan nada hasta que haya modelo. Lo destraba el
      entrenamiento `--bootstrap` (ver "Desplegar y esperar la muestra").

### 2.C — Meter información que el mercado aún no tiene

Es lo único que puede cerrar el hueco, por el propio diagnóstico:

- [ ] **XI a T-60** (ya construido, sin muestra). Ya no lo bloquea el plan
      (Pro desde 2026-09-22; `lineups` corre cada 5 min en el servidor). Lo
      bloquean la muestra y, como a 2.B, la falta de modelo activo. Es el de
      mejor relación valor/esfuerzo del proyecto.
- [x] **Bajas/lesiones.** Superado por algo mejor que un LLM leyendo prensa:
      `/injuries` de API-Football ya da el dato estructurado (jugador, tipo de
      baja, motivo) con el mismo proveedor ya contratado. Ingesta en
      `src/qf/ingest/injuries.py`, sellada con `captured_at`. Falta la
      feature de disponibilidad que entra en 2.B (ver Pendientes 🔴 arriba).
- [ ] **Movimiento de línea (fase 5).** Predecir la dirección del movimiento
      T-72 -> cierre es modelar un proceso MECÁNICO (flujo de dinero, cambios
      de límite), no uno caótico, y es donde un operador pequeño puede ganar de
      verdad. Necesita los 12 meses de snapshots: empezar a acumular hoy.

### 2.D — Modelos matemáticos: qué vale la pena y cuánto (poco)

Alternativas a Dixon-Coles publicadas como mejores, con expectativa HONESTA de
orden 0,001–0,002 de RPS cada una, frente a un hueco de 0,0065:

- [x] Conteo Weibull con cópula (Boshnakov, Kharrat & McHale, 2017). Es la
      mejora principal publicada sobre DC: trata dispersión y dependencia en
      vez del parche `tau` de 1997.
- [x] Conway-Maxwell-Poisson o Poisson bivariante (Karlis-Ntzoufras).
- [x] Probit ordenado sobre la diferencia de goles, como ruta alternativa al 1X2.

**Medido (2026-09-24), NEGATIVO:** `model/structure.py`, n=2.641 partidos
fuera de muestra del último año, walk-forward de DC real. Ningún brazo mejora
a DC `tau` con el IC entero por encima de cero en su métrica principal. Deltas
de RPS 1X2 contra `tau` (positivo = mejor que `tau`): Poisson bivariante
−0,00009 [−0,00017, +0,00001], CMP −0,00018 [−0,00029, −0,00006], Weibull con
cópula −0,00025 [−0,00045, −0,00002], probit ordenado −0,00044 [−0,00146,
+0,00055]. CMP y Weibull empeoran el 1X2 con el IC entero por debajo de cero.
Los parámetros ajustados quedan pegados al caso Poisson (ν=1,09, c=1,05,
κ=0,29, λ3=0,05): los goles del fútbol casi no tienen la sobredispersión ni
la dependencia que estos modelos saben corregir, y el `tau` (ρ≈−0,04) ya se
queda con lo poco que hay. Quitar el `tau` también empeora (−0,00006
[−0,0001, −0,00002]): se mantiene. Queda como informe en cada
entrenamiento (`val["structure"]`) por si cambia con más datos; no se activa
nada. Con esto 2.D queda cerrado: la forma de la matriz no es donde está el
hueco de 0,0065, como ya decía el diagnóstico.

Entran como challengers baratos, **nunca como el plan**: se medirían contra el
mismo conjunto de información que `w_model` ya declaró sin valor.

**Diseño acordado (2026-09-24, el usuario pidió implementarlos):**
`model/structure.py`. Los cuatro brazos de conteo conservan las MEDIAS de
Dixon-Coles (`lam`, `mu` fuera de muestra) y cambian solo la FORMA de la
matriz de marcadores: dispersión y dependencia, que es justo lo que los
papers dicen mejorar sobre el parche `tau`. Así no hace falta otro ajuste de
fuerzas por equipo (el walk-forward ya cuesta horas) y cada brazo aísla una
sola cosa. Brazos: Poisson independiente, DC `tau` (el titular, reajustado con
el mismo protocolo para que la comparación sea justa), Poisson bivariante
(λ3), CMP (ν, medias igualadas), Weibull con cópula de Frank (forma c y κ).
Aparte, probit ordenado heterocedástico sobre la diferencia de goles con
índice `log lam − log mu`. Parámetros globales reajustados por ventana
creciente mensual (sin mirar el futuro). Métricas: log-loss del marcador
exacto, over/under 2,5 y 1X2 (RPS y log-loss), con deltas contra DC `tau` e
IC por remuestreo de semanas. Solo informe en `val["structure"]`: NUNCA se
activa solo.

Lo que sí es matemática valiosa y NO está construido:

- [x] **Zona de abstención y Kelly bajo incertidumbre** (2026-09-22).
      `model/uncertainty.py`. El error estándar de cada parámetro sale del
      ajuste (estimador sándwich) y se propaga por Monte Carlo hasta el edge.
      De la misma medida salen las dos decisiones: abstenerse si
      `media - Z·sd <= 0`, y si no, encoger por `floor/media` en vez de por la
      constante 0,55. `UNCERTAINTY_ENABLED` apagado por defecto: cambia
      cuántos picks se publican al día.
- [x] **Guarda de muestra efectiva** (2026-09-22). Caso particular de la zona de
      abstención, cerrado ya porque la demostración con cuotas reales lo
      destapó: un club que vuelve a primera tras años fuera seguía en el índice
      con un parámetro extremo del ridge, `knows()` decía True, `_confidence()`
      le daba `high` (cuenta partidos de toda la vida) y se llevaba el stake
      máximo con un "edge" del 97%. Ahora `DCParams.effective_n` mide la suma
      de pesos de decaimiento y `MIN_EFFECTIVE_MATCHES` la exige.
- [~] **Validar la zona de abstención con datos reales.** Superado
      (2026-09-24): medida sin señal (ver `UNCERTAINTY_Z` abajo) y su
      integración se eliminó en el paso 4. `model/uncertainty.py` ya no lo
      importa ningún módulo; los picks no salen del edge del modelo.
- [x] **Calibrado `UNCERTAINTY_Z`: NO HAY SEÑAL QUE CALIBRAR** (2026-09-22).
      12.183 filas point-in-time sobre 4.061 partidos. La razón media/sd no
      discrimina (correlación con el acierto −0,047) y el motivo está debajo:
      el edge crudo del modelo correlaciona **−0,123** con el acierto. Es una
      anti-señal, y filtrar más fuerte sobre ella no puede ayudar. Queda
      `UNCERTAINTY_ENABLED=0` por medición, no por prudencia.
- [ ] **PLAN (2026-09-23) — sustituir el criterio de selección por "casa blanda
      contra precio sharp".** Piloto en `progreso.md`. Orden obligatorio:
      0. [x] Bloquear la publicación con el criterio viejo (2026-09-23).
         `PUBLISH_PICKS_ENABLED=0` por defecto: `daily.py` predice y sella,
         no selecciona, guarda ni difunde picks. `/model-card` lo declara.
         `tests/test_publicacion_bloqueada.py`.
      1. [x] Arreglar la vara (2026-09-23). `ev_close_pct = price ×
         closing_prob_devig − 1` en `pick_results` y `shadow_results`
         (`db/015_ev_cierre.sql`, aplicada en local). `summarize_clv`,
         `evaluate_clv_gate`, `shadow.summary` y
         `evaluate_shadow_promotion` deciden sobre él; `clv_pct` se sigue
         reportando. `closing_prob_devig` sale ahora de UN snapshot de
         cierre sharp con grupo completo. Tests: `test_ev_cierre.py`,
         `test_puerta_clv.py`. `v_clv_daily` y los paneles de CLV de Grafana
         ya muestran `ev_close_pct` (`db/019`, 2026-09-24).
      2. [x] `eval/soft_vs_sharp.py` (2026-09-23). Backtest reproducible
         sobre los CSV del formato principal, cacheados en `.local/fd_cache`
         con firma sha256; por casa, umbral y "mejor cuota entre casas
         reales"; IC por semanas; control sin criterio. Guarda
         `MAX_SHARP_DEVIATION`. 12 tests. Resultado: 1X2 +2,09% [1,21, 2,91]
         con la mejor casa real a umbral 2%; over/under sin oportunidades
         verificables.
         Decisiones que salen del backtest, para el paso 4:
         - Mercado principal 1X2. Totales solo con la guarda de referencia.
         - El encogimiento no puede ser el 0,55 constante: la persistencia
           medida va de 0,13 (Bet365) a 0,68 (1xBet); ~0,42 en conjunto.
         - La misma guarda de referencia en vivo: Pinnacle contra el
           consenso de las demás casas en el mismo snapshot.
         - Volumen: ~230 apuestas por temporada en 7 ligas con UN snapshot
           pre-cierre; la puerta pide 300. El vivo tiene más ventanas.
      3. [x] `ingest/odds_history.py` (2026-09-23). `plan` / `fetch` /
         `report` (con `--books`) con presupuesto por ejecución y reserva
         leyendo `x-requests-remaining`; respuestas crudas en
         `.local/odds_hist/`, NO en `odds_snapshots` (inmutable). 1X2,
         región `eu`. 11 tests. Descargado 2025 de Liga MX, Brasil,
         Argentina y MLS: 16.560 créditos, justo lo planificado.
         Resultado a umbral 2%: todas las casas +2,78% [1,79, 3,78] n=317;
         casas accesibles (1xBet+WH+888) +3,83% [2,36, 5,20] n=127, de las
         que 126 son 1xBet y 85 son MLS. Liga MX con casas accesibles: 7
         apuestas, negativo. Detalle en `progreso.md`.
         Decisión del usuario (2026-09-23): los suscriptores apuestan en
         casas internacionales presentes en LatAm (Bet365, 1xBet, Betway,
         William Hill, 888...). The Odds API no tiene Bet365 ni casas
         mexicanas; API-Football sí trae Bet365, Betano, 1xBet y William
         Hill junto a Pinnacle en 12 de 13 competiciones.
      3b. [x] Captura de cuotas de API-Football (2026-09-23, confirmada por
         el usuario). `src/qf/ingest/af_odds.py` + `db/016_af_odds.sql`
         (aplicada en local): tabla propia `af_odds_snapshots`, inmutable,
         con `provider_updated_at` y `fetched_at`; deduplica por la marca
         `update` del proveedor. 1X2, 9 casas, partidos en las próximas 72 h,
         cron cada hora. Verificada con dos pasadas reales (78 filas, luego
         0). 4 tests. Casa blanda y Pinnacle de la MISMA respuesta, nunca
         mezclando con el Pinnacle de The Odds API.
         Pendiente: desplegar el cron de verdad (Docker no disponible aquí)
         y, en unas semanas, medir con estas filas + el cierre de The Odds
         API el valor de Bet365 y Betano, que no tienen histórico en
         ninguna fuente.
      4. [x] `find_candidates` nuevo (2026-09-23). Precio justo = Pinnacle
         de-vigado en el MISMO snapshot que la casa blanda (API-Football o una
         captura de The Odds API, nunca cruzadas); guarda de referencia contra
         el consenso del snapshot (≥2 casas, sin exchanges); lista blanca
         `SOFT_BOOKS` con nombres unificados; edge bruto ≥ `SOFT_MIN_EDGE_PCT`
         (2%); antigüedad ≤ `SOFT_QUOTE_MAX_AGE_HOURS` (6 h); solo 1X2. Stake
         por Kelly sobre el edge esperado al cierre (× persistencia por casa,
         `picks.PERSISTENCE`). `picks` gana `fair_prob`, `min_price`,
         `odds_source`, `odds_as_of` (`db/017`, aplicada en local), que se
         sellan y salen por la API. Eliminado el criterio del modelo con sus
         integraciones (`eligible_markets`, `UNCERTAINTY_ENABLED`) y
         `tests/test_eligible_markets.py`. 13 tests nuevos. Prueba en seco con
         datos reales: 0 candidatos (ninguna casa de la lista por encima del
         justo; Liga MX con snapshot de 19 h).
         Sin validar todavía: el histórico cubrió precios 24-48 h antes del
         partido; el vivo decide a cualquier distancia. La sombra (paso 5)
         tiene que estratificar por antelación.
      5. [x] Sombra del criterio (2026-09-23). `publish/shadow_sharp.py` +
         `db/018_sombra_sharp.sql` (aplicada en local). `capture` cada hora
         a las :25 registra TODAS las ofertas (incluidas las de stake 0) de
         partidos a 72 h, sin duplicar un mismo snapshot; `settle_pending`
         se encadena desde `eval/clv.settle_pending` contra el cierre de
         Pinnacle sin margen; `report` separa "publicables" (primera pasada
         con stake por partido, la mejor de esa pasada: lo que ve la puerta)
         de todas las ofertas por antelación, casa, fuente y liga. Estado
         publicado en `/model-card` (`sombra_criterio_sharp`). 7 tests.
         Verificado contra el Postgres local: 0 ofertas hoy.
- [ ] **PLAN (2026-09-25) — Más mercados en el criterio sharp: goles y
      hándicap asiático.** Decisión del usuario: necesita picks todos los días
      y el 1X2 solo da pick en ~1 de cada 5 partidos (medido en vivo 24-25
      sep). Mismo criterio, más mercados; no se baja el umbral.
      Hechos que condicionan el diseño (sondeados el 2026-09-25):
      - API-Football trae Pinnacle, Bet365, Betano y 1xBet con goles (bet 5)
        y hándicap asiático (bet 4) en varias líneas, en la MISMA respuesta
        que el 1X2 y por la misma petición (quitando el filtro `bet`).
      - Trampa del hándicap de API-Football: las dos patas llevan la línea
        del LOCAL. 'Away -1' a 1,23 es visitante +1. Hay que invertirla.
      - Bet365 solo cotiza la línea 0 en hándicap; su valor estaría en goles.
      - The Odds API solo da UNA línea de Pinnacle por partido (la principal)
        en totals/spreads. Sin cierre de Pinnacle en esa línea, una oferta no
        se puede validar. Por eso el criterio solo mira la LÍNEA PRINCIPAL de
        Pinnacle del snapshot (la más equilibrada).
      Pasos:
      1. [x] `db/022`: columna `line` en `af_odds_snapshots` y
         `sharp_shadow_offers`; claves únicas con `line` (NULLS NOT DISTINCT,
         PG16). Nombres reales de las claves viejas comprobados en producción.
      2. [x] `af_odds`: capturar 1X2 + goles + hándicap en la misma llamada;
         pares completos por casa y línea; hándicap con la línea del lado.
      3. [x] `picks.offers`: mercados de dos vías por línea (totals/spreads):
         justo = Pinnacle sin margen de esa línea, guarda de consenso con ≥2
         casas en la misma línea, solo línea principal, umbral 2%.
         Persistencia por casa igual que 1X2 hasta tener muestra por mercado
         (suposición declarada; la sombra la mide).
      4. [x] Sombra: mercado y línea en ofertas y liquidación (`fair_close_prob`
         y `_settle_outcome` ya soportan totals/spreads); informe por mercado.
      5. [x] Tests (parseo con la trampa del hándicap, criterio por línea,
         liquidación) y harness: 413 tests.
      6. [ ] **NO desplegado: el ensayo con datos reales no encontró valor.**
         2026-09-25, 24 partidos de Liga MX y MLS, respuesta real de
         API-Football evaluada en memoria. Línea principal: las guardas pasan
         (47 de 48 mercados evaluados) pero la mejor casa de la lista queda
         en −0,1% (Betano) y el resto entre −1% y −5%. TODAS las líneas:
         0 de 1.448 precios de casas de la lista superan el justo en un 2%.
         1X2 en las mismas respuestas: 2 ofertas. Coincide con el histórico
         (over/under: 11 apuestas en 7 ligas y 6 temporadas). Las casas
         blandas copian a Pinnacle en goles y hándicap con su margen; el
         valor del 1X2 está en empates y no favoritos. Además, desplegarlo tal
         cual multiplicaría por ~50 las filas de `af_odds_snapshots` (todas
         las líneas de todas las casas). Si se despliega, guardar solo la
         línea principal de Pinnacle. Muestra corta (un día, dos ligas):
         repetir el ensayo con Europa activa antes de descartarlo del todo.
      Fuera de este paso, anotado: córners/tarjetas/mitades (Pinnacle los
      cotiza en API-Football pero no hay cierre fiable) y líneas alternativas
      de Pinnacle al cierre vía `alternate_totals` de The Odds API (coste por
      evento, a medir).
- [x] **HECHO (2026-09-25) — LaLiga 2 y Serie B en modo "solo sharp".**
      Desplegado: `db/023` y `db/024` aplicadas, worker y api reconstruidos,
      calendario cargado. Verificado en producción: 44 partidos (LaLiga 2 34,
      Serie B 10), equipos 390 → 390 tras el calendario (ningún alta
      automática), alias 941 → 1.018 (+77 revisados), pendientes 35 → 35,
      0 predicciones de estas ligas; `af_odds` las captura, lineups/bajas no,
      The Odds API solo `h2h`. Respaldo de los archivos sustituidos en
      `~/respaldo_20260925_ligas/` del servidor. Pendiente: que las primeras
      ofertas y cierres lleguen a la sombra (primer partido de LaLiga 2 hoy).
      Decisión del usuario, con la condición de no ensuciar la base. Dos
      riesgos encontrados antes de tocar nada:
      a) Duplicados: un club tiene UNA liga (`teams.league_id`). La liga nueva
         empieza sin equipos, `match_team` no encuentra a nadie y
         `resolve_or_register` crearía de nuevo a los descendidos de LaLiga y
         Serie A, con la historia partida.
      b) Cadena sellada: `daily._upcoming` predice y SELLA todo partido
         programado. El modelo no conoce a esos equipos: se publicarían
         predicciones sin base, inmutables.
      Diseño:
      1. [ ] `db/023`: `leagues.model_enabled` (TRUE por defecto; FALSE en las
         dos nuevas) y alta de `es.laliga2` / `it.serie_b`.
      2. [ ] `normalize.resolve_or_register`: antes de crear, coincidencia
         EXACTA (nombre canónico o cualquier alias) en las demás ligas
         domésticas del MISMO país; si hay un parecido dudoso allí, pendiente
         de revisión en vez de crear. Simétrico: sirve para ascensos y
         descensos entre ligas del catálogo.
      3. [ ] Fuera de todo lo que alimenta al modelo o a la cadena cuando
         `model_enabled` es FALSE: `daily._upcoming`, `train` (datos y
         `bootstrap_status`), `lineups`, `injuries`, `xg_worldfootball`.
         Dentro: calendario, resultados, `af_odds`, sombra sharp y
         `odds_worker` (solo `h2h`: 1 crédito por llamada).
      4. [ ] Ensayo en seco en el servidor (qué equipos se reutilizan, cuáles
         quedan pendientes, cuáles se crean) ANTES de aplicar.
      Sin histórico de football-data para ellas: el criterio no lo necesita y
      cargarlo mezclaría nombres de dos fuentes en ligas nuevas.
- [x] **HECHO (2026-09-27) — Fichas de partido reales en la web (estilo
      PropsBR): estadísticas, forma y H2H con datos de API-Football.**
      Desplegado: db/028 (`matches.stats`, `standings`), db/029
      (`teams.display_name`), `ingest/standings.py` (cron 06:40 y 22:40),
      `/web/partidos` y `/web/partidos/{id}` (`api/fichas.py`), vista
      «Partidos y estadísticas» y franja «Hoy en las ligas» en la portada.
      Sin probabilidades del mercado en la ficha (ver progreso).
- [x] **HECHO (2026-09-27, con el sí del usuario): cargados los partidos
      ya jugados de esta temporada de LaLiga 2 (66) y Serie B (50)** con
      `python -m qf.ingest.fixtures --temporada es.laliga2 it.serie_b`.
      0 equipos nuevos, 0 duplicados. Y escudos: db/030, 271 descargados.
      Texto original de la propuesta: Faltan
      ~90 y ~50 (anteriores al alta del 25-sep). Sin ellos, la forma de un
      descendido enseña sus partidos de mayo en Primera. Coste: 2 peticiones
      de calendario + estadísticas por partido; el modelo no los lee (ligas
      `model_enabled = false`). Vía: insertarlos como programados con su
      `external_id` y dejar que `results.close_recent(hours_back=…)` los
      cierre por el camino normal.
- [x] **HECHO (2026-09-28, lo pidió el usuario): `/fair-price` pasa a
      `/v1/fair-price/{id}` con `SERVICE_TOKEN`.** Nadie lo consumía (ni
      frontend ni tests); sin token responde 404. Aviso original:
      `/fair-price/{id}` era público y
      devuelve `best_price` y `gap_pct`,** es decir, qué casa paga por encima
      del justo en cada partido: el criterio de picks en abierto. No se ha
      tocado; decidir si pasa a `/v1` (SERVICE_TOKEN) o se recorta.
- [x] **HECHO (2026-09-28, pedido del usuario: "ejecuta todas las
      palancas") — Acelerar la muestra de la puerta sin rebajarla.**
      Desplegado: sombra con todas las casas y puerta con `SOFT_BOOKS`
      ampliada (.env del servidor actualizado), guarda de 15 min, persistencia
      recalibrada, db/033 (10 ligas, 127 equipos nuevos, 43 reutilizados) y
      guardas en daily/train para equipos de ligas sin modelo en copas.
      El usuario confirmó (2026-09-28) Betsson y Coolbet; LeoVegas y Unibet
      fuera de `SOFT_BOOKS` (la sombra las sigue midiendo igual).
      Diagnóstico previo (solo lectura): desde el 24-sep, 36 partidos; con la
      lista actual 8 con oferta, con todas las casas del feed 23. Cierre de
      Pinnacle: 10 de 10 partidos en sombra lo tienen (el "3 de 4" era un
      pick aún sin jugar). El Pinnacle de API-Football nunca baja de 2,5 h
      antes del partido: el cierre solo puede venir de The Odds API.
      1. [x] Casas: la sombra mide TODAS las casas no exchange del snapshot;
         la puerta (publicables) cuenta solo `SOFT_BOOKS`, filtrado al
         informar (sin columna nueva: se puede recalcular para cualquier
         lista). `SOFT_BOOKS` += betsson, coolbet, leovegas_se, unibet_se,
         unibet_nl, a confirmar por el usuario (el feed da precios de
         Suecia/Países Bajos para LeoVegas/Unibet).
      2. [x] Cierre: ninguna oferta de la sombra puede salir de un snapshot
         de la ventana de cierre (se liquidaría contra sí misma: EV = edge
         bruto). Se exige antelación ≥ 15 min.
      3. [x] Ligas "solo sharp" con Pinnacle en The Odds API y sin
         divisiones hermanas en la base (no duplican clubes): Chile, Turquía,
         Suiza, Dinamarca; Colombia/Perú/Ecuador si hay cobertura. Antes:
         el job diario deja de predecir partidos de copa con equipos de ligas
         sin modelo (hoy se sellarían con `both_teams_known=false`).
      4. [x] Persistencia por casa: regla fijada AHORA, antes de ver la
         muestra: media ponderada previa/medida con peso n/(n+100) partidos,
         medida = EV al cierre / edge bruto de la primera oferta por partido
         y casa, suelo 0. Solo afecta a capturas futuras (cada oferta guarda
         la persistencia con la que se decidió).
- [ ] **Idea aparcada (2026-09-27, el usuario prefirió no hacerlo): medir más
      casas en sombra.** Con TODAS las casas del feed, los partidos con oferta
      desde el 24-sep pasarían de 8 a 25; las que más aportan: LeoVegas (22),
      BetVictor (14), Unibet (13), Coolbet (7; +4,4% al cierre en el histórico
      de Liga MX). Más casas dan más picks y mejor precio, NO más acierto (sus
      cuotas medias eran 3,6-4,5). Suscriptores en Latinoamérica y España.
      Ojo si se retoma: el feed da LeoVegas/Unibet de Suecia y Países Bajos,
      no el precio de la web española o latinoamericana; Codere, Caliente,
      Sportium, Luckia, Kirolbet, Strendus y Playdoit no los da ningún
      proveedor. Propuesta que quedó sin hacer: registrar esas ofertas en la
      sombra marcadas "en medición", fuera de la puerta y sin publicar.
- [ ] **PLAN (2026-09-25) — Más ligas en 1X2 para tener picks a diario.**
      Sondeo real (API-Football `odds?date=`, 1X2, 26-28 sep, parón de
      selecciones en Europa, una foto por partido): 823 partidos con cuotas
      en 176 ligas; 491 con Pinnacle y casas de la lista en la misma
      respuesta; **14 con pick (2,9%)** en 12 ligas, frente a 2 de nuestro
      catálogo actual (Liga MX). Bet365 da 11 de los 14 (persistencia medida
      0,13: muchos quedarán con stake mínimo) y 1xBet 3. En vivo se mira cada
      hora durante 72 h, así que la tasa real será mayor (MX/MLS: 5 de 25
      partidos en 34 h frente a 2 de 24 en una foto).
      Restricción que manda: validar exige el cierre de Pinnacle y eso solo
      lo da The Odds API. De los 14, solo 5 son de competiciones que cubre
      (Nations League, Liga MX, League Two). Las demás (Segunda RFEF, WSL,
      3. liga checa, Segunda uruguaya, Primera B colombiana, Copa Chile…) NO
      se podrían validar nunca: no entran.
      Candidatas validables (en The Odds API y activas): Championship, League
      One, League Two, EFL Cup, La Liga 2, Serie B, Ligue 2, Bundesliga 2,
      3. Liga, DFB-Pokal, Bélgica, Austria, Suiza, Dinamarca, Noruega, Suecia
      (Allsvenskan y Superettan), Finlandia, Grecia, Turquía, Escocia,
      Irlanda, A-League, K League 1, Chile, Brasil Série B, Libertadores,
      Sudamericana, Conference League, Nations League.
      Backtest por liga (football-data 2021/22-2024/25, 1X2, mejor de
      Bet365/William Hill/1xBet a umbral 2%, una foto pre-cierre por partido,
      EV contra el cierre de Pinnacle sin margen). Picks por semana · EV al
      cierre [IC95]:
        National League 1,77 · +4,83% [3,0, 6,7]  (sin The Odds API: no validable)
        LaLiga 2        1,64 · +3,91% [2,5, 5,3]
        Serie B         1,43 · +5,06% [3,3, 7,1]
        Bélgica         0,85 · +3,20% [1,2, 4,9]
        Serie A         0,71 · +3,91% [1,6, 6,3]  (ya en catálogo)
        Escocia Champ.  0,23 · +4,34% [1,3, 7,2]  (sin The Odds API)
        Positivas sin demostrar: Turquía +1,95, Bundesliga 2 +1,86,
        Championship +1,43, Ligue 2 +1,15, League One/Two +1,1.
        Sin valor: Grecia −0,22 (88% Bet365), Ligue 1 −0,77, Portugal +0,17,
        Eredivisie +0,84 (IC con cero). Las tres últimas YA están en el
        catálogo: la sombra por liga debe decidir si se publican.
        Total 20 ligas: 2.158 picks, +2,48% [1,93, 3,10], persistencia 0,51.
      Cuotas (medido 2026-09-25): API-Football gasta ~350-430/día con 25
      partidos en el horizonte (1 petición por partido y hora); con Europa de
      vuelta serán ~3.000-3.500/día y con 6 ligas más ~5.000 de 7.500. Cabe,
      pero la captura por fecha lo dejaría en ~2.200 fijo. The Odds API: le
      quedan 3.205 créditos de 20.000 tras el histórico (16.560).
      **Corregido el 2026-09-27: NO es urgente.** El plan se renueva el día 1
      de cada mes (dato del usuario); el 27-sep quedaban 3.006 con un gasto
      medido de 70-100/día, así que llegan al reset con ~2.600 de sobra. Con
      Europa activa se estiman ~6.000-9.000 al mes: caben en 20.000. Pasar el
      vivo a solo `h2h` (goles y hándicap no dieron valor) queda como palanca
      para crecer en ligas sin subir de plan, no como arreglo urgente.
      Cobertura REAL de Pinnacle en The Odds API (una llamada h2h por liga,
      2026-09-25; eventos con Pinnacle / eventos): League One 4/4, League
      Two 10/10, Bundesliga 2 9/9, Ligue 2 9/9, LaLiga 2 11/12, Serie B
      10/10, Chile 9/10, Dinamarca 6/6, Finlandia 6/6, Suiza 6/6, Turquía
      9/9; PARCIAL Austria 6/12 y Brasil Série B 10/20; SIN Pinnacle: 3. Liga
      1/11, Superettan 0/7 y **Bélgica 0/9** (recomendada por el backtest:
      volver a comprobar antes de darla de alta; si sigue sin Pinnacle no es
      validable).
      Descubierto en la misma prueba: `bookmakers=` con hasta 10 casas cuesta
      1 crédito (medido: `x-requests-last=1` con 6 casas) y MEZCLA regiones:
      trajo Betway, que solo está en `uk` y es casa de los suscriptores. Usar
      `bookmakers=pinnacle,onexbet,williamhill,sport888,betway,...` en vez de
      `regions=eu` da más casas por el mismo precio. `regions=eu,uk,us`
      triplicaría el coste.
      Trabajo que implica, en orden:
      1. [ ] Catálogo: filas en `leagues` (api_football_id, clave de The Odds
         API, estilo de temporada) y calendario/resultados de esas ligas.
      2. [ ] Captura de API-Football por FECHA (`odds?date=`, ~30 páginas por
         día) en vez de una petición por partido: con ~250 partidos a 72 h la
         captura actual gastaría ~6.000 peticiones/día de 7.500.
      3. [ ] The Odds API: ligas nuevas solo `h2h` (1 crédito por llamada);
         goles y hándicap no dieron valor y cuestan 3.
      4. [ ] Sombra primero: las ligas nuevas acumulan ofertas y cierres antes
         de publicar nada; la puerta por liga ya existe (`by_league`).
      5. [x] Desacoplar el pick de la predicción (2026-09-25, desplegado).
         `db/025`: `picks.prediction_id` y `model_prob` admiten vacío (nunca
         0: se leería como "el modelo da 0%"). `daily._sharp_only_upcoming`
         añade los partidos de ligas `model_enabled = FALSE` a la selección
         sin predecirlos ni sellar predicción; el orden predecir →
         seleccionar → sellar → publicar no cambia. Con la publicación
         cerrada no se elige nada, igual que antes. Verificado: 43 partidos
         solo sharp elegibles a 30 días, 0 en la predicción sellada.
- [ ] **Desplegar y esperar la muestra.** Nada de lo anterior produce datos
      hasta que el contenedor corra el cron: `odds_worker` (cierres de
      Pinnacle), `af_odds` y `shadow_sharp capture`.
      Preparado en local (2026-09-23), falta ejecutarlo en el servidor:
      `quantfut.dump` (4 MB), `.env.server` (rellenar `DOMAIN` y
      `GRAFANA_ALLOWED_IP`), `scripts/restore_db.sh`; corregidos el entorno y
      el `PATH` del cron del worker, `.dockerignore` y `PG_PASSWORD` en
      `.env.example`. Pasos en README → "Llevar la base local al servidor".
      Tras arrancar: entrenar el primer modelo (no hay ninguno activo) y
      comprobar `/var/log/af_odds.log`. Luego, revisar
      `report` cada semana y, cuando `sombra_criterio_sharp.autorizada` sea
      true, decidir con el desglose por antelación si se restringe el tramo
      antes de poner `PUBLISH_PICKS_ENABLED=1`. Eso último es decisión del
      usuario, no del código.
      **Plan de despliegue (2026-09-24)** — VPS Contabo `31.220.72.30`,
      dominio `pronosticosdeportivos.pro` con DNS y proxy de Cloudflare
      (SSL Full strict, Origin Certificate en `/etc/ssl/quantfut/`):
      - [x] Caddy detrás de Cloudflare: `trusted_proxies` = rangos CF,
            IP real desde `CF-Connecting-IP`, `X-Forwarded-For: {client_ip}`
            hacia la API (el rate limit de `main.py` usa su primer elemento),
            `tls` con el Origin Certificate en vez de ACME.
      - [x] Sustituir la restricción por IP (`GRAFANA_ALLOWED_IP`) por
            Cloudflare Access en `panel.`, `/control` y `/admin` (decisión
            del usuario). Caddy exige además `Cf-Access-Jwt-Assertion`.
      - [x] Configurar las aplicaciones de Access en Zero Trust: Google como
            proveedor de identidad, app "QuantFut - panel de operación" con
            los 7 destinos y política "Solo el operador" (jairlopez.cc@gmail.com).
            Probado en vivo: login con Google → 503 propio de la API
            ("Panel no configurado"), no un bloqueo de Access.
      - [x] `ADMIN_CONSOLE_USER` (jairlopez.lcc@gmail.com) + hash en `.env`
            del servidor. Trampa real: el `$` del hash pbkdf2 choca con la
            interpolación de variables de `docker compose` en `.env` — sin
            escapar como `$$`, el hash se corta en el primer `$` sin avisar
            (compose solo advierte "variable is not set", nada apunta al
            valor roto). `/control` pasó de 503 a 302 tras corregirlo.
      - [x] **Bug encontrado y corregido (2026-09-24): el cron del worker no
            corría en el servidor.** `chmod 0644 /etc/cron.d/quantfut` fallaba
            contra el volumen `:ro` y el `&&` cortaba antes de `crontab`;
            `cron -f` seguía arriba pero con cero jobs, sin error visible.
            Quitado el `chmod` (no hacía falta) en `docker-compose.yml`.
            Verificado: 17 jobs cargados, `cron -f` corriendo.
      - [x] Servidor: usuario `qf`, swap 4 GB, fail2ban, ufw (solo 22) +
            cadena `DOCKER-USER` que deja 80/443 solo a rangos de Cloudflare
            (Docker se salta ufw en puertos publicados).
      - [x] `PermitRootLogin no` (2026-09-24): contraseña puesta a `qf`,
            login root por SSH desactivado y verificado (`Permission denied`
            probando con la clave). `qf` sigue entrando por clave y ahora
            tiene sudo sin contraseña (`/etc/sudoers.d/qf-nopasswd`) para no
            bloquear tareas de administración futuras. Alias `ssh quantfut`
            actualizado a `qf@` en `~/.ssh/config`.
      - [x] Subir repo + `quantfut.dump` + `.env`, `build`, `restore_db.sh`,
            `up -d`, backup diario `pg_dump -Fc`.
      - [x] Entrenar el primer modelo y cargar el calendario (2026-09-24).
            Calendario cargado (171 partidos programados). Primer
            entrenamiento corrido: NO activó modelo, correctamente —
            `market_age_days=250` en la base restaurada (cierre sharp más
            reciente de enero 2026), y la puerta exige <30 días. No es un
            fallo, es la puerta funcionando. **Resuelto el 2026-09-27:** el
            `--bootstrap` de las 01:05 entrenó con los cierres de Pinnacle
            del fin de semana y activó `2026.09.27-010508` (RPS 0,1991 frente a
            0,19345 del mercado: sigue detrás, como se esperaba); el job de
            las 08:00 selló las primeras 4 predicciones. Reentrenar cuando
            `odds_worker`/`af_odds`/`shadow_sharp` acumulen cierres frescos
            (ya corriendo desde el fix del cron).
      - [ ] Backup fuera del servidor (sin destino rclone todavía).
      - [ ] **Resultados de la temporada en curso sin cargar (revisado
            2026-09-24, 01:50 UTC del 25).** Último partido terminado en la
            base: Premier, LaLiga, Serie A, Eredivisie y Liga MX en mayo de
            2026; Brasil en diciembre de 2025. Bundesliga, Ligue 1, Portugal
            y Argentina sí tienen septiembre. Sin resultados no se liquida
            ningún cierre ni el entrenamiento ve la temporada actual.
            **Causa encontrada:** `history_fd.backfill()` tenía el rango fijo
            2014..2025 (nunca cargaba 2026/27), `fixtures` solo crea partidos
            futuros y `results` solo cierra las últimas 72 h: lo jugado antes
            del primer calendario no existía. Arreglado en local con tests:
            `default_seasons()` llega al año en curso y `_ingest_rows` salta
            la fila entera si el partido ya existe (misma liga y equipos,
            ±36 h), porque API-Football etiqueta distinto la temporada y las
            cuotas no admiten DELETE. Alias `db/021` (Racing Santander).
            **Desplegado y cargado (2026-09-25 UTC, confirmado por el
            usuario):** `db/021` aplicada y `backfill(['2627'])` con el código
            nuevo en un contenedor aparte. 991 partidos en 7 ligas, 2.973
            cuotas de cierre (3 por partido), 0 duplicados, 0 clubes nuevos;
            los 531 ya cargados y el cruce con API-Football, saltados.
            **No desbloquea el `--bootstrap`:** football-data dejó de traer
            Pinnacle a mediados de enero de 2026; los cierres nuevos son de
            Bet365 y la frescura exige el sharp. El primer Pinnacle fresco
            será la captura en vivo de los 25 partidos de Liga MX y MLS del
            26-28 de septiembre. Comprobar el 28-29: `close` de Pinnacle
            capturado, partidos cerrados por `results` y `bootstrap_status()`.
      - [x] **17.385 grupos de cuotas de cierre de football_data repetidos**
            (revisado 2026-09-25). Todos con exactamente UNA fila de más y el
            MISMO precio (0 grupos con precio distinto): recargas de Liga MX
            (3.987 partidos), Argentina (1.428) y Premier (380) anteriores a
            la guarda de `history_fd`. Ningún número medido está sesgado:
            entrenamiento, CLV, sombra, `/fair-price`, `daily`, `picks` y
            `v_closing_odds` eligen un precio por selección (`DISTINCT ON` o
            un único `captured_at`), y `soft_vs_sharp` lee los CSV, no la
            base. Único efecto: `v_odds_growth.snapshots` (count(*)) cuenta
            de más en días históricos; cosmético. No se borran (inmutable) ni
            se añade índice único: ya no se puede crear con esas filas y la
            guarda del código basta. Mismo día: 0 cierres de Pinnacle capturados en 3
            días (solo 1 partido terminado desde el arreglo del cron) y el
            `--bootstrap` de las 01:05 volvió a rechazar ("mercado de 252
            días"); los primeros cierres llegan con los 25 partidos de Liga
            MX y MLS del 26 al 28 de septiembre. Los avisos «Evento sin
            emparejar» de `odds_worker` NO son un fallo: `meta` solo contiene
            los partidos que tocan en esa ventana y el resto del feed se
            registra como sin emparejar (ruido que convendría bajar a debug).
      - [x] **Salir de "sin modelo activo" (2026-09-24, desplegado).** Sin modelo, el job
            de las 08:00 falla cada día (no sella nada) y la sombra del XI
            (2.B/2.C) no acumula. El reentrenamiento mensual es el 1-oct.
            Hecho en local, pendiente de desplegar: `train --bootstrap` diario
            a las 01:05 UTC que solo entrena (~3,5 h) si no hay modelo activo
            y el cierre sharp ya pasaría la misma puerta de frescura
            (`MARKET_MAX_AGE_DAYS`, compartido con `promotion.py`); si no,
            sale en segundos. Tarjetas nuevas en `/control`: puerta comercial
            (mismo `shadow_sharp.report` que decide) y último entrenamiento
            con sus motivos. `db/019` para `v_clv_daily`. Desplegado y
            verificado: prueba en seco "mercado de 252 días" (sale sin
            entrenar), `019` aplicada con el GRANT a `qf_readonly` intacto, y
            la tarjeta de la puerta leyendo 4 ofertas reales con stake.
- [x] **CONSECUENCIA GRAVE: `find_candidates` selecciona apuestas perdedoras.**
      Resuelto el 2026-09-23 con el paso 4: el criterio del modelo se sustituyó
      por el de precio sharp (punto 2.A), y la publicación sigue pausada hasta
      pasar la puerta.
- [ ] ~~Calibrar `UNCERTAINTY_Z` contra ROI~~
- [~] **Medir la incertidumbre RELATIVA al mercado, no la absoluta.**
      Superado (2026-09-24) por el mismo motivo: servía para decidir apuestas
      a partir del edge del modelo, y ese criterio ya no existe. Reabrir solo
      si el modelo vuelve a proponer apuestas.
- [~] **La ordenación por media/sd no arregla la selección adversa.**
      Superado: el criterio sharp no ordena por edge del modelo.

### 2.E — No volver a proponer (medido negativo, está en progreso.md)

Ajuste por estado del partido, PSxG como objetivo, más ligas, mercados
derivados como fuente de edge, Elo como sustituto, y barridos de
hiperparámetros. Todos medidos, todos negativos o en la cuarta decimal.

## Verificación pendiente CON DATOS REALES 🔬

Ya hay Postgres local con 50.079 partidos reales (11 ligas + 2 copas). Queda:

- [ ] Revisar si la calibración supera su puerta. Que la descarte NO es un
      fallo: significa que el modelo ya estaba calibrado.
- [ ] Revisar si el modelo de residuo supera la suya. Se entrena siempre pero
      solo se aplica con `RESIDUAL_ENABLED=1`.
- [x] Verificar `ingest/lineups.py` contra la API real (2026-09-22). `_parse_side`
      cuadra con la respuesta real: `formation`, 11 titulares, `pos` en G/D/M/F
      —que es lo que `availability()` cuenta por posición—, `number`, `coach` y
      `player_id`. El contrato de orden [local, visitante] también se confirma.
- [x] Verificar `ingest/fixtures.py` con una competición `cross_league` real
      (2026-09-22). `_resolve` no dio de alta ni un equipo bajo `eu.ucl` y la
      exigencia de coincidencia exacta evitó dos contaminaciones reales que el
      difuso proponía. Ver `progreso.md`.

- [x] **Nombres sin resolver en producción (2026-09-24).** 36 pendientes:
      uno real, `Coventry City` (The Odds API; el club lo dio de alta
      API-Football como `Coventry` al ascender) → alias en `db/020`; se
      estaban descartando sus cuotas de Premier. Los otros 35 son clubes de
      ligas fuera del catálogo en copas europeas (grupo 1 de abajo). La alarma
      `nombres sin emparejar` ya no los cuenta: solo alarma lo que se ve en
      una liga doméstica o sin competición anotada. `resolve_team(seen_in=)`
      anota la competición del feed de The Odds API sin acotar la búsqueda.
- [x] **Revisados (2026-09-25).** Producción: 35 pendientes, TODOS clubes de
      copas europeas fuera del catálogo (correcto rechazarlos: "Rangers"
      daba 92 contra Angers, "Celtic" 73 contra Celta). CSV: 228 nombres
      únicos, 109 ya resueltos; de los 119 restantes, 117 de copas y 2
      domésticos: "Den Bosch" (segunda neerlandesa, sin partidos esta
      temporada: nada que hacer) y "Real Racing Club de Santander", el
      nombre de The Odds API para Racing Santander, recién ascendido: SIN
      alias sus partidos de LaLiga no tenían cierre de Pinnacle → `db/027`.
      Comprobados además los 305 equipos de las 13 ligas domésticas contra
      la lista de partidos de The Odds API (gratuita): Racing era el único.
      Texto original:
- [ ] ~~**Cerrar los 163 alias que siguen sin emparejar.**~~ Tras el bootstrap con
      las dos claves quedan en `aliases_pendientes.csv`. Se reparten en tres
      grupos y solo uno es trabajo de verdad:
      1. Clubes de ligas que el catálogo NO cubre (Celtic, Rangers,
         Galatasaray, Slavia Praha, Bodø/Glimt…): aparecen en Champions y
         Europa League y son irresolubles por diseño. Se descartan, y el
         partido de copa con ellos también.
      2. Equipos que ya no están en la competición en la temporada 2024 que
         permite el plan Free.
      3. Nombres nuevos reales, que son los que hay que mapear a mano.
      Cuidado con el difuso al revisarlos: propuso `Remo`→Grêmio (80) y
      `Atlético Huracán`→Atlético Tucumán (81). Ambos falsos.

## En progreso 🟡

- [ ] **Fase 2–4 — evaluación y challengers point-in-time (orden solicitado
      2026-09-22).** Implementar sin saltarse dependencias:
      1. Elo secuencial point-in-time con 1X2 completo.
      2. Comparación Elo / Dixon-Coles / Pinnacle sobre las mismas filas.
      3. Puerta champion/challenger estricta y hash completo del dataset.
      4. Feature builder point-in-time con pruebas contra leakage.
      5. Ablaciones de descanso, Elo, forma y tiros.
      6. Logística multinomial deportiva y anclada al mercado, solo challenger.
      7. Mantener la captura de alineaciones y medir su preparación muestral.
      8. Challenger en sombra que ajuste `log(lambda_home/away)` por el XI.
      9. Registrar y liquidar CLV del periodo en sombra sin publicar apuestas.
      Ningún challenger se activa automáticamente; la promoción exige mejora
      temporal fuera de muestra y, cuando exista muestra, CLV.
      Código y migración local verificados; pendiente demostrar señal con
      cuotas recientes y acumular la muestra de sombra antes de promover.

## Completadas 🟢

- [x] **Fix: liquidación del hándicap asiático en líneas de cuarto**
      (2026-09-23). `clv._settle_outcome` devuelve ahora (outcome, fracción
      ganada, fracción devuelta) y `settle_profit` paga lo ganado a cuota y lo
      devuelto a 1. Antes medio-ganada y medio-perdida solo cuadraban a 2,00.
      `tests/test_liquidacion_ah.py`. `pick_results` estaba vacía: nada que
      rehacer.

- [x] **Plan Pro de API-Football: cadena operativa desbloqueada** (2026-09-22).
      Temporada en curso accesible, 300 req/min, 7.500/día. Primera ingesta
      real de calendario: 173 partidos programados en 12 competiciones.
      `results.py` cierra y encadena la liquidación. Quedan fuera solo los
      clubes de copa cuyas ligas no están en el catálogo, que es el diseño.
- [x] **`db/013_aliases_api_football.sql`** (2026-09-22). Cinco alias de la
      temporada en curso y cuatro altas de clubes que de verdad faltaban
      (Remo, Gimnasia Mendoza, Estudiantes Río Cuarto, Atlante). Los cuatro
      tenían un candidato difuso FALSO por encima del suelo de sugerencia.
- [x] **Dos alarmas que estaban permanentemente en rojo** (2026-09-22). El
      chequeo de calendario preguntaba por 10 días cuando la ingesta trae 21,
      así que saltaba en 10 competiciones a la vez cada parón de selecciones; y
      `history_fd._ensure_team` insertaba el alias con SQL directo en vez de
      `register_alias`, dejando 362 nombres marcados como pendientes para
      siempre. Una alarma que siempre suena no se lee el día que importa.

- [x] **Claves de API-Football y The Odds API configuradas y verificadas**
      (2026-09-22). Los 13 `odds_api_key` existen y están activos; los 13
      `api_football_id` apuntan a la competición correcta. Tres bugs del
      cliente salieron al usarlo de verdad: ritmo de llamadas 17× por encima
      del plan Free, reintento ciego del 429 y reintento de errores de plan
      (permanentes) que quemaba cuota. Ver `progreso.md`.
- [x] **Coste real de The Odds API con 13 competiciones** (2026-09-22). Medido
      sobre el calendario anunciado, no estimado: ~1.935 llamadas/mes, entre
      1.935 y 11.610 créditos/mes según mercados y regiones.
- [x] **Emparejamiento exacto obligatorio cuando no hay liga que acote**
      (2026-09-22). `resolve_team(..., exact=True)` por defecto. Cerraba un
      agujero real en `odds_worker` con los eventos de copa.

- [x] **Baseline Elo point-in-time** con empate, localía, ascendidos,
      actualización diferida del resultado y evaluación común histórica.
- [x] **Feature builder point-in-time** para Elo, descanso, forma y tiros;
      ablaciones y dos challenger multinomiales de solo diagnóstico.
- [x] **Infraestructura XI y CLV de sombra:** captura reintentable, ventana
      `post_xi` antes de cierre, ajuste de lambdas, baseline T-60, migración
      `db/012` aplicada en Postgres local y puerta de promoción estricta.
- [x] Fase 0 — captura de cuotas (`qf.ingest.odds_worker`).
- [x] Fase 1 — ingesta + modelo base (calendario, resultados, xG, aliases,
      salud, Dixon-Coles).
- [x] Arnés: `CLAUDE.md`, `scripts/harness_check.sh`, `harness/`.
- [x] Reorganización: se extrajo `pyton/quantfut.tar.gz` a la raíz del
      proyecto (era el repo completo, no solo los archivos sueltos que había
      en `pyton/`). Estructura ahora coincide con la documentada en README.md.
- [x] **Fix: bug de `tier` hardcoded en `persist()`.** `daily.py` guardaba
      TODOS los picks del día como `tier='paid'`, así que `/picks/free` y la
      vista gratuita de `/v1/picks` siempre devolvían vacío. Ahora
      `picks.assign_tiers()` decide el tier (los de mayor edge, `free`;
      configurable con `FREE_PICKS_PER_DAY`, default 2) antes de persistir, y
      `daily.py` usa ese mismo reparto para Telegram (que es opcional/no-op
      sin token) en vez de que Telegram decida el tier.
- [x] **API — endpoints de catálogo y ficha de partido.** Añadidos
      `GET /leagues`, `GET /teams`, `GET /matches/{match_id}` (público, con
      predicción recortada al tier gratuito). Antes no existía forma de que
      la web listara ligas/equipos sin tocar la BD directamente.
- [x] **API — paginación.** `limit`/`offset` en `/picks/free` y `/v1/picks`
      (antes devolvían todo sin límite).
- [x] **Modelo por liga con pooling parcial.** `model/dixon_coles.py`: ventaja
      de local e intercepto de goles POR LIGA, encogidos hacia la media global
      (equivalente MAP de un jerárquico bayesiano, sin PyMC ni GPU). De paso
      se corrigió que los equipos se indexaban solo por nombre: dos ligas con
      un "Santos" fusionaban sus historiales en silencio.
- [x] **Calibración** (`model/calibration.py`). Corrección afín en log-espacio
      sobre las lambdas, no sobre el 1X2: así los ~150 mercados siguen siendo
      coherentes entre sí. Con puerta de validación temporal que la descarta
      si no mejora fuera de muestra.
- [x] **Riesgo de portafolio correlacionado** (`publish/picks.py`). Sustituye
      el tope ingenuo de suma de stakes por una sigma conjunta con matriz de
      correlación (riesgo de modelo común + misma liga + misma dirección).
- [x] **GBM sobre el residuo del mercado** (`model/residual.py`). Se entrena
      siempre, se aplica solo con `RESIDUAL_ENABLED=1` y tras superar su
      validación. Desactivado por defecto: corrige solo el 1X2.
- [x] **Ingesta de alineaciones a T-60** (`ingest/lineups.py`). La tabla
      `lineups` existía desde el día uno y nada la escribía. En el crontab
      cada 5 min, ventana T-90..T-20.
- [x] **Suite de tests** (`tests/`, 48 casos) + `requirements-dev.txt`.
      `scripts/harness_check.sh` los ejecuta.
- [x] **Fix: desajuste de versión de artefacto.** `train.py` guardaba
      `dc_2026.09.21.pkl` pero `daily.py` cargaba `dc_{MODEL_VERSION}.pkl`.
      Habría roto el job diario en el primer reentrenamiento. Ahora se
      resuelve el modelo activo desde `model_artifacts`.
- [x] **Ponderación óptima modelo/mercado** (`model/meta.py`). Estima
      `w_model` por log-loss fuera de muestra, con pesos por liga encogidos
      hacia el global. Se estima y publica SIEMPRE en `/model-card`; aplicarla
      en producción requiere `META_BLEND_ENABLED=1`. Excluyente con el modelo
      de residuo (ambos fusionan con el mercado; juntos lo contarían dos
      veces) — `daily.py` avisa y prioriza la mezcla.
- [x] **Fix CRÍTICO: unidades del stake.** `kelly()` devolvía fracción de
      banca (0.0067) pero todo el sistema la leía como unidades. El descarte
      `stake <= 0.05` de `find_candidates` eliminaba TODOS los picks con edge
      realista (3-10%): el sistema habría publicado CERO picks para siempre
      sin dar ningún error. Contrato ahora fijado por
      `tests/test_kelly_units.py`: 1 unidad = 1% de banca.
- [x] **Ratings dinámicos con filtro de Kalman** (`model/kalman.py`). La fuerza
      como estado latente en vez de fija con decaimiento.
- [x] **Bundesliga, Ligue 1 y Primeira** (2026-09-22). `db/010` + `db/011`.
      No por sí mismas —aunque son apostables— sino porque eran las tres que
      más partidos de copa descartaban. Los cruces utilizables pasaron de 406
      a 1.111.
- [x] **MLS, Champions y Europa League** (2026-09-22). `db/007_competiciones.sql`
      separa competición (`matches.league_id`) de liga doméstica del equipo
      (`teams.league_id`); `ingest/uefa_cups.py` carga el histórico de copas
      desde los `.rds` de worldfootballR_data (única fuente gratuita: ese
      release no publica CSV); `model/dixon_coles.py` gana el término
      `strength` de fuerza relativa entre ligas, que los cruces europeos son
      lo único que identifica.
- [x] **xG de Argentina** (2026-09-22). Pasó de 0% a 62,5%. No hacía falta
      técnica nueva: la dependencia `pyreadr`, que antes no compensaba por una
      sola liga, ya era obligatoria para las copas europeas.
- [x] **Fix: `harness_check.sh` daba OK saltándose los tests.** Elegía
      `python3`, que en Windows resuelve al stub de la Microsoft Store: tiene
      `--version` y ninguna dependencia. Ahora prefiere `.venv` y FALLA si no
      encuentra pytest, en vez de avisar y seguir.

## Nota sobre `pyton/` — BORRADA (2026-09-25)

Borrada con confirmación del usuario. De sus 11 archivos, 9 tenían copia
en `src/`, `scripts/` o `db/`; `xg_fbref.py` era el módulo retirado a
propósito el 2026-09-24. Lo único sin copia, `quantfut.tar.gz` (la versión
inicial del proyecto, sin secretos), se conserva en
`harness/archivo/quantfut_version_inicial.tar.gz` porque no hay git.
