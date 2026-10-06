# Backlog — QuantFut

Orden de dependencia (ver "Huecos concretos que quedan" en README.md).
No reordenar sin razón: cada ítem depende del anterior.

## Decisión de alcance (2026-09-21)

El usuario **no usa Telegram**. La venta de picks es 100% en su web propia.
El bot de Telegram y el auth por Telegram quedan fuera de alcance (no se
borran, pero no se desarrollan más). Prioridad actual: la API que sirve
predicciones a la web. Auth de suscriptor no-Telegram y cobros son "después",
no ahora.

**Ampliación NBA (2026-10-03, indicación nueva del usuario):** las señales NBA
se prevén por notificación inmediata de Telegram. Esta excepción corresponde
al diseño de NBA; no activa publicación de fútbol ni reutiliza el canal
operativo como canal de clientes.

## Pendientes 🔴

## NBA 2026-27 — investigación y experimentos (2026-10-03)

- [x] Revisar arquitectura y contrastar literatura académica, doctorados,
      maestrías y el texto aportado. Plan integrado con fuentes, modelos,
      datos, presupuesto y 27 experimentos propuestos E0–E26:
      `docs/nba_2026_27_investigacion_y_plan.md`.
- [x] Contrastar el segundo texto y ampliar el plan con calibración,
      incertidumbre, SBC, conformal online/control de riesgo y Kelly robusto.
      Separar cobertura predictiva, acierto, retorno y ejecución. E21–E26
      son diseños pendientes de ejecución, no estrategias validadas.
- [x] Documentar aislamiento recomendado a petición del usuario:
      `docs/nba_arquitectura_aislada.md`. Aplicación/dependencias/despliegue,
      Postgres/Redis, credenciales, presupuestos y Telegram NBA propios;
      sin imports entre deportes ni refactor inicial de fútbol.
- [x] Revisar crítica operativa de props/Telegram/noticias y acotar MVP:
      `docs/nba_mvp_ejecucion_y_capacidad.md`. Rangos de límites/reacción no
      corroborados se tratan como hipótesis; 27 experimentos siguen como backlog.
- [x] Consolidar plan maestro por fases F0–F9 y registro estructurado:
      `docs/nba_plan_fases_auditable.md` y
      `docs/nba_plan_fases_auditoria.json`. Plan documentado; ninguna fase
      de implementación ni puerta G0–G9 se considera aprobada por escribirlo.
- [x] Revisar viabilidad antes del inicio (4-oct): quedan 16 días al 20-oct.
      Aplicación NBA inexistente y cero ejecuciones registradas. Objetivo
      condicionado: MVP estadístico acotado; priorizar histórico deportivo
      reciente y datos actuales. Sin prometer históricos completos, modelo
      avanzado ni validación comercial para la fecha de apertura.
- [x] Incorporar pretemporada al arranque y revisar preparación del plan:
      `docs/nba_pretemporada_arranque.md`. Captura actual, históricos recientes,
      separación de regímenes y métricas; pruebas no sustituyen F7 regular.
      Plan preparado para iniciar trabajo local; implementación pendiente.
- [x] Contrastar texto adicional sobre CLV, sharp/soft, lesiones y QNN:
      `docs/nba_revision_critica_clv_fuentes.md`. CLV complementario con cierre
      comparable; liderazgo por mercado/latencia observada; minutos separados
      de USG%. Sin garantizar ventaja de props o modelos cuánticos.
- [x] Integrar correcciones en plan maestro NBA 1.1 y registro: CLV complementario, cierre comparable, latencia/linaje, USG y pretemporada. Versiones previas preservadas; fases de implementacion pendientes.
- [ ] **F0 / G0:** alcance, decisiones y protocolo preregistrado. Presupuesto,
      operadores/proveedor y canal de pruebas pendientes de definición.
- [ ] **F1 / G1:** aplicación `apps/nba/`, dependencias/despliegue, Postgres/
      Redis, configuración y recuperación propios. Aplicación/entorno/config
      locales implementados; Postgres/Redis y recuperación aún pendientes.
      Arnés resuelto y verificado; no importar `qf`.
- [ ] **F2 / G2:** cobertura E0, identidad, contratos/reglas, gasto y familia
      prepartido inicial elegida por datos. Puede avanzar con F1 después de F0.
- [ ] **F3 / G3:** ingesta versionada, raw, cuarentena, reconciliación y PIT.
      E18 continúa en todas las fases; referencias/hash y anclaje de evidencia.
- [ ] **F4 / G4:** baselines y distribución de minutos E1, priors encogidos,
      roles/carga y coherencia deportiva; no usar minutos reales como feature.
- [ ] **F5 / G5:** tasa/distribución de estadística, E8 básico, E21 cuando
      proceda y E22/E23 básicos. Candidato y criterios congelados antes del test.
- [ ] **F6 / G6:** Telegram de pruebas, sellado/outbox, caducidad, revalidación,
      disponibilidad E5/E17 y resiliencia E19. Resolución y demoras explícitas.
- [ ] **F7 / G7:** confirmación prospectiva E26 y revisión de promoción propia.
      300 partidos/60 días/3 bloques son piso propuesto, no prueba suficiente
      de ROI. Separar métricas deportivas, simulación y datos informados.
- [ ] **F8 / G8:** challengers de lesiones/rol/oportunidades E2/E3/E7/E8/
      E9/E13. Núcleo F6 y datos suficientes; cada candidato nuevo vuelve a F7.
- [ ] **F9 / G9:** operación evaluada, capacidad/utilidad del producto y
      extensiones a periodos/live/modelos avanzados con validación específica.
      No heredar puertas de fútbol ni operar apuestas/cuentas de clientes.

- [x] **Primer incremento NBA autorizado (4-oct):** entorno independiente,
      fuentes gratuitas, box scores auditados, baseline de minutos/rebotes,
      replay temporal y ledger local. 22 pruebas NBA y 606 de fútbol correctas.
      `docs/nba_arranque_resultados.md`; no aprueba G0–G9 ni activa Telegram.
- [x] **Buscar y descargar repositorios GitHub NBA:** shufinskiy PBP/tiros
      (30 temporadas disponibles, 124 archivos) y hoopR box scores/calendario
      (66 archivos) como complemento a llimllib. Inventario/cobertura en
      `docs/nba_fuentes_github.md`; ausencia de huecos requiere auditoría propia.
- [x] **Auditar fuentes para huecos NBA (5-oct):** 30 Parquet individuales
      SportsDataverse (1996-97 a 2025-26), lesiones con snapshots y muestras
      de props descargados con hashes. Resultados y límites en
      `docs/nba_fuentes_github_huecos_20261005.md`; candidatos no integrados.
- [x] **Integrar históricos NBA (5-oct):** importador SportsDataverse
      2021-22 a 2025-26, fechas/IDs/tipos conciliados, 154.058 registros en
      snapshot propio; minutos dudosos en cuarentena. Replay congelado y
      referencia anterior preservados. `docs/nba_avance_fases_20261005.md`.
- [x] **Captura experimental actual (5-oct):** 30 plantillas ESPN 2026-27,
      606 jugadores, recepción UTC/namespace propios. Lesiones incluidas
      conservadas raw, con auditoría de fechas; no disponibilidad verificada.
- [x] **Experimento de arranque (5-oct):** priors del año anterior para
      primeras diez apariciones observadas, protocolo separado, 8.264 casos
      históricos y escenario 2026-27; abstiene sin prior suficiente. Resultado
      exploratorio, condicional a participación, sin promoción ni publicación.
- [ ] Verificar correspondencias ESPN/NBA y disponibilidad actual; incorporar
      rol/rotación, calibración/abstención y coherencia conjunta de minutos al
      arranque. Rookies y ausencia de datos no se convierten en ceros.
- [ ] Validar lesiones históricas contra PDFs, IDs y corte temporal; muestras
      de props siguen sin contratos/PIT suficientes para ROI o CLV.
- [ ] Recuperar registros en cuarentena contrastando otra fuente; unir IDs
      ESPN→NBA con evidencia y cubrir 2023-24 individual incompleto.
- [ ] Captura gratuita actual con rosters, calendario y disponibilidad PIT;
      contratos/cuotas y destino NBA privado de pruebas siguen pendientes.

## Histórico FotMob (2026-10-03, alcance del usuario)

- [ ] Descargar a archivos locales el histórico del 1-ene-2024 al 3-oct-2026
      de las 23 ligas y Champions/Europa League. Inventariar temporadas reales,
      filtrar partidos terminados y deduplicar por ID de FotMob. Conservar JSON
      comprimido y hora de captura, exportar xG/estadísticas y cobertura por
      competición. Descarga reanudable; detenerse ante denegación de acceso o
      límite del proveedor. Sin escrituras en Postgres ni jobs recurrentes:
      los partidos futuros vendrán de otra API por decisión del usuario.
      **En curso:** inventario completo de 22.461 partidos en 96 temporadas;
      detalles descargándose a `.local/fotmob-history/2024-01-01_2026-10-03/`.
      `coverage.json` indica cuándo termina; no marcar HECHO hasta entonces.

## Ideas de la literatura (2026-10-03, aprobadas por el usuario) — en orden

Cruzadas con lo ya medido (2.D, 2.E): solo entra lo que no se ha probado.

- [x] **HECHO (3-oct) — SIN SEÑAL. 1. ¿Aporta el modelo frente a la cuota
      TEMPRANA de Pinnacle?** Pendiente 0,003 [−0,008, +0,014], 4/7 ligas,
      EV −4,9 % [−5,2, −4,6], `w_model` 0,0001 también contra la temprana.
      Control positivo (media de casas): 0,38 [0,29, 0,46]. Ver progreso.md.
      Planteamiento original:
      `w_model = 0,0001` se midió contra el CIERRE. `history_fd.py` ya lee
      `PSH` (cuota de viernes/martes) pero solo como respaldo del cierre. Se
      mide con los 42 CSV de `.local/fd_cache` (7 ligas, 2019/20-2024/25) y
      las predicciones secuenciales de Kalman (xG incluido), sin tocar
      producción: `python -m qf.eval.early_vs_close`.
      **Regla fijada ANTES de ver resultados.** Prueba principal: pendiente
      de la regresión del movimiento `logit p_cierre − logit p_temprana`
      sobre el desacuerdo `logit p_modelo − logit p_temprana` (no necesita
      resultados, mucho menos ruido que el RPS). "Hay señal" si el IC95 por
      semanas de la pendiente está ENTERO por encima de cero, es positiva en
      ≥4 de 7 ligas y el EV contra el cierre justo de apostar al precio
      temprano de Pinnacle cuando el modelo ve ≥2 % de ventaja tiene el IC95
      entero por encima de cero. Informativas: `w_model` contra la temprana
      (estimado en el 70 % antiguo, RPS en el 30 % reciente) y lo mismo
      contra el cierre como control (debe salir ≈0, como en el README).
- [x] **HECHO (3-oct) — NO SE VALIDA. 2.** RPS 0,21826 → 0,21838 (peor),
      log-loss 1,0516 → 1,0521, 4/11 ligas; el XI simple sobre las mismas
      3.646 filas: 0,21686. Ver progreso.md. Código en el repo
      (`model/masmenos.py`, brazo en `player_value.comparar`); en el servidor
      solo se ejecutó una copia aparte, sin desplegar. La versión exacta con
      `/fixtures/events` NO se hace: dependía de que esta apuntara algo.
      Planteamiento original:
- [ ] **2. Valor del XI por "más-menos" regularizado** (Kharrat, McHale y
      Peña 2020; Hvattum): una sola señal por equipo en vez de las 18 de
      "XI con valor". Con `minutos` de db/035. Brazo más del reentreno
      mensual, nada en producción.
      **Decisiones del usuario (3-oct):** versión APROXIMADA por minutos (el
      diseño del 29-sep la dejaba fuera por no tener el minuto de cada
      cambio; la exacta con `/fixtures/events` queda para después si esta
      apunta algo) y ejecución en el VPS en solo lectura.
      **Diseño fijado ANTES de ver resultados** (`model/masmenos.py`):
      - Por partido, `y` = diferencia de goles local−visitante mezclada con
        la de xG (`xg_blend`, como el modelo) y centrada; fila de diseño
        `+minutos/90` por jugador local y `−minutos/90` por visitante.
        Ridge ponderado por decaimiento (vida media 180 días) con λ = 10
        (un jugador pesa como 10 partidos completos a rating 0). Un solo
        λ: no se prueban variantes sobre la validación.
      - Punto en el tiempo: reajuste cada 7 días solo con partidos
        anteriores; la semana siguiente usa esos ratings.
      - Señal: `{lado}_d_pm` = suma de ratings del XI de hoy − la del XI
        habitual (mismos 5 XI previos y mismo descarte por >3 titulares
        sin minutos que "XI con valor"). Dos señales en total.
      - Brazo `masmenos` en `player_value.comparar`, mismas filas que los
        demás. Se valida solo si pasa las exigencias de siempre Y mejora
        RPS y log-loss del XI simple, como "XI con valor".
- [~] **EN MARCHA (3-oct) — 3A y 3B desplegados; falta la LECTURA.**
      Tras 2-3 fines de semana desde el 9-oct: `python -m qf.eval.latencia`
      en el worker y aplicar la regla de abajo. Vigilar el gasto en
      `rafagas_log`.
- [ ] **3. Latencia de las casas blandas tras moverse Pinnacle** (fase 5):
      qué casa tarda más y si el cliente llega a tiempo. Choca con los
      créditos de The Odds API: elegir partidos.
      **Diagnóstico (3-oct):** hoy no se puede medir. API-Football (Bet365,
      Betano) refresca cada competición de golpe cada varias horas con UNA
      hora para todas las casas: no distingue quién reacciona. The Odds API
      sí da `last_update` por casa y mercado, pero `odds_worker` lo descarta
      y solo captura 6 ventanas por partido. Muestra de la sombra: 184
      ofertas en 28 partidos (Europa vuelve el 9-oct). Casas de los
      clientes medibles por The Odds API: Betsson, Coolbet, William Hill,
      1xBet (no Bet365 ni Betano).
      **Plan propuesto (pendiente de decisión del usuario):**
      - 3A, gratis: db/038 añade `book_updated_at` (nullable) a
        `odds_snapshots` y `odds_worker` guarda el `last_update` del mercado
        (si falta, el de la casa). Con eso, en cada captura se sabe si una
        oferta existe porque la casa blanda no ha reaccionado a un cambio de
        Pinnacle (precio blando más viejo que el último cambio de Pinnacle).
        No toca triggers: es ADD COLUMN, no UPDATE.
      - 3B, con créditos: `ingest/rafagas.py`, solo 1X2 y `bookmakers=`
        (Pinnacle + casas blandas, ≤10 → 1 crédito por llamada y liga),
        cada 5 min entre T-6h y T-15min en las ligas elegidas, a una tabla
        APARTE (`odds_rafagas`) para no tocar ventanas ni sombra, con tope de
        créditos al mes que la detiene. `last_update` da el segundo exacto de
        cada cambio, así que 5 min bastan. ~72 créditos por liga y día de
        partidos.
      - Medida fijada antes: duración de cada oferta (cuota blanda ≥2 % sobre
        el justo de Pinnacle en muestras seguidas) y minutos que tarda cada
        casa en cambiar tras un movimiento de Pinnacle ≥2 puntos de
        probabilidad justa. Se compara con el tiempo que necesita un cliente
        para apostar (dato del usuario).
      **Decisiones del usuario (3-oct):** desplegar 3A; 3B con tope de 3.000
      créditos/mes (`RAFAGAS_MAX_CREDITOS_MES`), ligas Premier, LaLiga y Liga
      MX (`RAFAGAS_LIGAS`); el cliente tarda UNA HORA O MÁS en apostar.
      **Regla de lectura fijada antes** (`python -m qf.eval.latencia`): no se
      lee antes de 200 ofertas clasificables en ≥3 casas. Si menos de la
      mitad de las ofertas de una casa dura ≥60 min, el formato actual
      (pick publicado que el cliente apuesta al rato) no captura la ventaja
      de esa casa y esa casa no debería contar para la puerta; si la mitad o
      más, sí. Las censuradas ≥60 cuentan como largas; las censuradas <60 se
      excluyen.
- [x] **HECHO (3-oct) — SIN SEÑAL. 4.** Con γ elegido en validación: EV
      contra el cierre −3,51 % [−3,78, −3,25], 0/7 ligas; γ fijo de 0 a
      0,8: −3,78 % → −3,46 %, todos con el IC entero bajo cero. La ventaja
      estimada correlaciona −0,10 con el EV real (peor quintil, el de más
      ventaja): la cartera de Sharpe pesaría más lo peor, no se prueba.
      Ver progreso.md. Planteamiento:
- [ ] **4. Decorrelación con el mercado** (Hubáček y Šír, IJF 2023):
      entrenar para discrepar donde el mercado se equivoca. Investigación.
      **Método del artículo (leído el 3-oct, arXiv 2010.12508 §4.5 y §5):**
      pérdida `Σ (t−y)² − γ·Σ (t−m)²`, `y` el resultado, `m` la probabilidad
      del bookmaker; γ ∈ {0, 0,2, …, 1}; NBA 2006-2014 contra el cierre de
      Pinnacle, walk-forward por temporadas; con apuesta uniforme siguen en
      pérdidas para todo γ, con cartera de Sharpe ganan con γ 0,2-0,8.
      **Diseño fijado ANTES de ver resultados** (`eval/decorrelacion.py`,
      solo lectura, local):
      - Mismos 14.110 partidos y Kalman sin futuro del punto 1. `m` = justo
        de Pinnacle TEMPRANO (es contra quien se apuesta).
      - Segunda etapa: softmax lineal sobre la información del modelo (log
        de sus tres probabilidades y log de las dos lambdas), pérdida del
        artículo + L2 1e-3. Sin cuotas como variable (su caso principal).
      - Walk-forward por temporadas: prueba 2021/22-2024/25, entrenando con
        todas las anteriores. γ ∈ {0, 0,2, 0,4, 0,6, 0,8}, elegido para cada
        temporada con la anterior como validación (entrenando con las de
        antes): nunca se elige mirando la prueba.
      - Apuesta uniforme: por partido, la selección de mayor `t·cuota − 1`
        si es > 0, al precio temprano de Pinnacle.
      - "Hay señal" si con el γ elegido el EV contra el cierre justo tiene
        el IC95 por semanas ENTERO por encima de cero y es positivo en ≥4 de
        7 ligas. Con el cierre insesgado, el EV contra el cierre es la misma
        esperanza que el ROI con mucho menos ruido; el ROI se informa.
        Informativo: la tabla de todos los γ y la correlación con el
        mercado. La cartera de Sharpe solo se prueba si lo uniforme apunta
        algo.
- [x] **HECHO y DESPLEGADO (3-oct) — 5.** db/039, `picks.factores()`,
      sombra con `stake_publicado_units` y `factor_incertidumbre`. Factores
      vigentes al desplegar: 1xBet 0,94, Betano 0,71, Betsson 0,65,
      Bet365 0,54, William Hill 0. Planteamiento:
- [ ] **5. Encoger el stake del criterio sharp por la incertidumbre de la
      persistencia** (Baker y McHale 2013; Uhrín y otros 2021). No es lo
      superado en 2.D: aquí la incertidumbre es la del criterio, no la del
      modelo.
      **Medido (3-oct, fd_cache, 2 %, primera oferta por partido):**
      persistencia e IC95 por semanas: 1xBet 0,72 [0,37, 1,06], Interwetten
      0,55, bwin 0,31, BetVictor 0,20, Bet365 0,13 [−0,15, 0,41] (no se
      distingue de cero), William Hill −0,15. Dispersión entre casas 0,31.
      **Decisión del usuario:** "stake sí, muestra no".
      **Diseño fijado antes de implementar:**
      - Factor por casa `k = ρ² / (ρ² + SE²)` (0 si ρ ≤ 0): la aproximación
        de Baker y McHale con la persistencia como única fuente de
        incertidumbre. Se multiplica al Kelly fraccional, que se queda en
        0,20 (es preferencia de riesgo, no estimación).
      - SE previa: 1xBet 0,17, Bet365 0,15, William Hill 0,25 (bootstrap
        por semanas de football-data); casas sin medir 0,31 (dispersión
        entre casas). En vivo, SE de la sombra por el método delta
        (`sd(ev)/(√n·media(edge))`, coincide con el bootstrap) y se mezcla
        con la previa con los MISMOS pesos que `picks.mezclar`.
      - El stake con factor es el que se publica y el que guarda la sombra
        en una columna nueva; qué oferta es publicable se sigue decidiendo
        con el stake SIN factor (`stake_units` de la sombra y
        `stake_kelly_units` del candidato): la muestra de la puerta no
        cambia.

## Auditoría fase 3 (2026-10-03) — pendientes de decisión

- [x] **HECHO (3-oct) — `/matches/{id}` ya no publica `market_consensus`**
      (sigue en `/v1/matches/{id}/predictions`).
- [x] **HECHO (3-oct, opción b del usuario) — los lotes sellados dejan de
      llevar `market_consensus` desde el 3-oct** (`LOTE_SIN_CONSENSO_DESDE`).
      Los anteriores conservan su formato: el del 2-oct regenerado desde la
      base da el mismo JSON que el sellado.
- [x] **HECHO (3-oct) — `/openapi.json` ya no se sirve** (`openapi_url=None`).
- [ ] **ALTA antes de publicar la cadena — el lote lleva también los PICKS,
      de pago incluidos** (`advised_price`, `bookmaker`, `min_price`,
      `fair_prob`). El flujo documentado en `hashchain.py` hace commit del
      JSON a un repo público "antes del primer kickoff": eso regalaría cada
      mañana los picks de pago. Lo habitual es comprometer-revelar: publicar
      solo el `chain_sha256` antes de los partidos y el JSON después del
      último inicio del día. Hoy no pasa (`CHAIN_GIT_REMOTE` vacío).
- [ ] **BAJA — `/model-card` publica rutas internas** (`*_uri` con rutas de
      archivos del servidor). Quitarlas de la respuesta pública.
- [ ] **BAJA — sin `Content-Security-Policy`.** El resto de cabeceras está.
- [ ] **ANTES DE VENDER — avisos legales en la web:** +18, juego
      responsable, privacidad/cookies y términos; no hay ninguno. Y el README
      remite a una sección "Procesadores de pago" que no existe.

## Auditoría 2026-10-03 — mejoras propuestas (pendientes de decisión)

- [x] **HECHO (3-oct, decisión del usuario) — Antelación de la DECISIÓN.**
      `picks.MIN_LEAD` (15 min) la usan la sombra y la publicación real, para
      el precio y para la decisión. La publicación (`find_candidates`) no
      tenía ninguna guarda: el job de las 08:00 habría publicado a T-5 un
      partido de las 08:05.
- [x] **HECHO (3-oct) — Segunda oportunidad del cierre.** Pasada de rescate
      `odds_worker --solo-cierre` a los minutos 5,15,…: dos intentos dentro
      de la ventana 3-12 min, misma vara, 0 créditos si el primero funcionó.
- [ ] **Vigilar 1xBet en la sombra.** Era la casa del valor histórico
      (+2,78% en el backtest, persistencia 0,72); en vivo va −0,2% en 28
      ofertas con cierre. Muestra pequeña: revisar con las europeas.

## Fase 1 — fuentes paradas (encontrado 2026-10-02)

`worldfootballR_data` no actualiza ningún fichero que usamos desde el
18-sep-2025 (ver README, "Corrección (2026-10-02)").

- [x] **HECHO (2-oct, decisión del usuario) — Resultados de copas que
      faltaban (dic-2024 → hoy).** `fixtures --copas-ensayo` y luego
      `--copas 2024-12-13 2024 2025 2026`: 351 partidos (215 UCL, 136 UEL)
      cerrados con marcador y estadísticas, 0 duplicados, 726 peticiones.
      Todo lo no resuelto son clubes de ligas fuera del catálogo; ningún
      equipo dado de alta en copa. Entran en el reentreno del 1-nov.
- [x] **HECHO (2-oct) — Chequeo de frescura del xG** (`check_xg_freshness`).
      Mira el dato, no el job. Las 13 competiciones paradas quedan
      reconocidas hasta el 1-nov-2026; desde entonces alertan cada día.
- [ ] **Fuente de xG reciente — decidir ANTES del 1-nov-2026** (el chequeo
      vuelve a fallar ese día). **Medido el 3-oct: el xG APORTA** (regla
      fijada antes: IC95 entero bajo cero y ≥ mitad de ligas). Ventana
      jul-2023→ene-2025: RPS 0,20154 con xG frente a 0,20440 solo goles,
      delta −0,00287 [−0,00376, −0,00200], 12 de 13 ligas. Es del orden de
      lo que Dixon-Coles saca a Elo y ~40% del hueco con Pinnacle. Hoy
      (xG viejo) aún aporta −0,00055 [−0,00100, −0,00018] y se irá
      apagando con la media vida de 180 días. Siguiente paso: elegir fuente.
      FotMob usa xG de Opta, como FBref: medir antes la coherencia con el xG
      guardado en el solape 2024-25 (correlación y sesgo por liga).
      **3-oct: medido el xG de API-Football** (progreso): mismos valores que
      FBref (corr. 0,96-1,00) pero llega con días/semanas de retraso e
      irregular en Argentina/Liga MX. Usarlo exige revertir la regla del
      README y CLAUDE.md: DECISIÓN DEL USUARIO pendiente.

## Línea de alta probabilidad (2026-10-05, decisión del usuario)

Diseño aprobado: `docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md`.
Pronósticos ≥ 80 % de probabilidad real (Pinnacle sin margen), aparte de los
picks de valor y sin tocar su puerta. Es una línea de acierto, no de valor.

- [x] Paso previo: sincronizar servidor con HEAD (lista de cambios al usuario
      antes de reconstruir).
- [x] Prueba histórica de goles (`eval/alta_prob_calibracion.py`) y fijar
      `MERCADOS_GOLES_HABILITADOS`.
- [x] `db/040`, `publish/alta_prob.py`, sellado en `hashchain`, liquidación.
- [x] `GET /alta-probabilidad`, sección web y estado en `/control`.
- [x] Despliegue con `ALTA_PROB_ENABLED=0` (2026-10-06 18:12 UTC): db/040 aplicada y
      verificada (bordes, UNIQUE, inmutabilidad), ensayo de SQL, verify 8 lotes.
- [ ] Tras el sellado del 7-oct (08:00 UTC): verify y recibo con `n_alta_prob: 0`;
      luego activar `ALTA_PROB_ENABLED=1` con visto bueno del usuario.
- [x] Más goles (2026-10-06): `af_odds` guarda las líneas de goles de la misma
      petición (db/041) y la línea las lee de la misma respuesta. Desplegado
      19:58 UTC; vista previa 9 de 15 partidos (7 de goles, antes 0).
- [ ] Vigilar a las 24 h: filas/día de `af_odds_snapshots` y duración de la
      pasada (hoy 15 s, ~40 filas por partido). Chequeo de frescura de
      `af_odds` en `health.py` (hoy un fallo de escritura solo queda en el log).
- [ ] Antes de configurar `CHAIN_GIT_REMOTE`: el lote lleva `prob` exacta y el
      ajuste de goles (anula el redondeo público). Decidir.

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
- [x] (2026-10-05, pedido del usuario) Tabla en `/control` con los picks que
      se habrían publicado en la sombra sharp (`shadow_sharp.publishable_list`).
- [x] (2026-10-05, pedido del usuario) Probabilidad real de cada pick en la
      web (`fair_prob`, Pinnacle sin margen) y acierto esperado de la lista.
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
      **Corregido y desplegado el 2-oct-2026:** hasta entonces no guardó
      NINGUNA baja (comparaba el id de API-Football con el `team_id`
      interno). La muestra point-in-time empieza el 2-oct.
- [ ] **Feature de disponibilidad a partir de bajas.** `injuries.py` solo
      ingiere y almacena, igual que hizo `lineups.py` en su fase inicial.
      Falta un equivalente a `lineups.availability()` que combine bajas +
      XI confirmado en una feature de `residual.py`. Requiere haber
      acumulado datos primero (desde el 2-oct; antes la tabla está vacía).
- [x] **HECHO (2-oct) — Por qué `check_injuries_coverage()` no frenó el
      fallo de bajas.** Saltó cada mañana del 28-sep al 1-oct; el aviso iba a
      Telegram sin token y el log del cron se borraba en cada despliegue.
      Ahora: `health_runs` (db/037), `/var/log` del worker en volumen, alerta
      sin canal como ERROR, HTML escapado y fallo de envío que no tumba el job.
- [x] **HECHO (2-oct) — Bot de alertas de Telegram configurado.** El
      usuario puso `TG_BOT_TOKEN` (@NavyAnalista_bot) en el `.env` del
      servidor; `TG_ALERT_CHAT` es su chat privado. Alerta de prueba enviada
      desde el worker. `TG_CHANNEL_FREE/PAID` siguen vacíos: por Telegram
      solo salen alertas, nunca picks. Si se rota el token, revisar que el
      bot siga teniendo el chat (`getUpdates` tras un `/start`).
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
- [x] **HECHO (2-oct, decisión del usuario) — historia del XI desde
      `lineups_historicas` (db/036).** `availability()` toma los XI previos
      de cada equipo también de esa tabla; el XI de hoy, solo de `lineups`.
      257 de 262 equipos con partido en 14 días ya tienen ≥3 XI previos
      (faltan 5 de copas), así que los brazos de XI miden desde el 9-oct y
      no desde finales de octubre.
- [ ] **El XI llega tarde: medir antes de comprar otra fuente (2026-10-01).**
      API-Football publica el once a T-25 (22 de 22 partidos de MLS/Liga MX;
      su propia guía dice 20-40 min). Los clubes lo anuncian ~T-60 y
      Pinnacle se mueve en minutos: la ventaja de "reaccionar antes que las
      casas blandas" casi no existe con esta fuente. Desde el 9-oct, medir la
      antelación del XI en las ligas europeas (`lineups.mins_to_kickoff`). Si
      sigue en ~T-25, evaluar una fuente más temprana, con prueba gratuita y
      midiendo su antelación real antes de pagar. Ojo con el brazo
      `lineup_lambda_market`: aplica el ajuste de XI sobre cuotas de T-20 que
      ya incorporan el XI, así que mide doble efecto por diseño; leerlo
      como cota inferior, no como el valor del XI.
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
- [ ] **Fase 5 — movimiento de línea.** Requiere 12 meses de snapshots
      PROPIOS para validar (captura en vivo desde el 24-sep-2026).
  - [ ] **Estudio exploratorio con histórico ya disponible (añadido
        2026-10-02, pedido del usuario).** Pregunta: ¿se puede predecir la
        dirección del movimiento de Pinnacle 1X2 entre el precio temprano y
        el cierre? No espera a los 12 meses porque ya hay datos:
        1. football-data.co.uk: 14.294 partidos, 7 ligas, 2019/20-2024/25,
           Pinnacle pre-cierre (`PSH/PSD/PSA`) y cierre (`PSCH/PSCD/PSCA`),
           ya cacheados para `soft_vs_sharp.py`. Límite: el precio temprano
           no tiene hora exacta.
        2. Histórico de The Odds API (desde jun-2020; cada 5 min desde
           sep-2022) con hora exacta: solo con créditos sobrantes del mes y
           fijando antes cuántos se gastan.
        Reglas: solo lectura, sin tocar producción ni picks; partición
        temporal fijada antes de mirar resultados; la base a batir es "no
        se mueve" y la media del mercado. Es descubrimiento, NO
        certificación: lo que salga se valida después en sombra con la
        captura propia, igual que la puerta de la fase 2.
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
También (2026-10-03): el modelo contra la cuota TEMPRANA de Pinnacle; no
anticipa el movimiento (`eval/early_vs_close.py`). El más-menos por jugador
(`model/masmenos.py`). Y entrenar para apartarse del mercado (Hubáček y Šír,
`eval/decorrelacion.py`): con la información de goles y xG no hay nada de lo
que apartarse con provecho.

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

### Continuación NBA autorizada 2026-10-05
- [x] F2: cruce conservador ESPN→NBA: 596/606 identidades y equipos comprobados, diez conflictos separados; capturas públicas con hash.
- [x] F3/F4: calendario y validador de disponibilidad por partido/PIT; 436 escenarios condicionales y proyección acotada de minutos implementados. Disponibilidad y rol reales siguen pendientes.
- [x] F5: diagnóstico discreto del replay comprobado, sin ajustar ni promover parámetros.
- [x] F6: contrato/revalidación de cuotas y outbox NBA; prueba local y rechazo de picks insuficientes. Enlace explícito al bot y chat de alertas de fútbol elegido por el usuario.
- [x] Evidencia NBA-EV-035–050, ejecuciones NBA-RUN-011–015, código congelado; 79 NBA/606 fútbol aprobadas, puertas pendientes.
- [ ] Configuración activa del bot/chat de fútbol disponible en el entorno/ruta autorizados; ejecutar prueba técnica real y medir entrega.
- [ ] Disponibilidad por partido y rol/minutos validados; diez identidades no resueltas y rookies sin historial conservan abstención.
- [ ] Fuente de props, contratos y frescura utilizables; supervivencia de precio, límites compartidos del bot y confirmación prospectiva antes de promover/publicar.

### Scrapers y datos adicionales NBA — 2026-10-05
- [x] Inventariar repos públicos, fijar commits y revisar código/datos reales sin ejecutar proyectos de terceros: diez repos y 52 archivos verificados.
- [x] Auditar horarios históricos y muestras de reportes de lesiones: calendarios sin horas; PDF actual 403. No se acredita PIT histórico.
- [x] Integrar observaciones con namespace/captura explícitos y auditoría: alineaciones previstas RotoWire y piloto de quintetos PBP Stats; ninguna promoción médica o comercial.
- [x] Ejecutar pruebas relevantes, conservar evidencia y actualizar registro de fases: 100 NBA y 606 fútbol pasan.
- [ ] Ampliar quintetos en lotes auditados y obtener sustituciones cronológicas del PBP; validar reloj/IDs de alineaciones y publicación médica por partido antes de usar contexto en pronósticos.

### NBA — The Odds API existente, revisión 2026-10-05

- [x] Comprobar con la clave existente deportes NBA/pretemporada, eventos y muestra real de cuotas; cuatro créditos usados, sin guardar clave o activar polling.
- [x] Documentar mercados, latencia efectiva, acceso histórico todavía no probado y presupuesto compartido con fútbol.
- [ ] Implementar cliente NBA persistente con reserva coordinada de créditos y evaluación específica de props alternativos; verificar reglas, reloj e identidades antes de promover contratos.
- [x] Verificar acceso histórico tras confirmar el usuario su plan de pago: muestra NBA `player_rebounds`, 242 cuotas, ocho casas; once créditos. Conservar discrepancias del reloj de snapshot.

### NBA — austin-pesina/nba_scrapes, 2026-10-05

- [x] Descargar rama principal completa con commit y hashes: seis archivos, 15,023 bytes.
- [x] Comprobar datasets/releases/Actions: cero archivos de datos, cero releases y cero artefactos disponibles; no ejecutar los scripts o conectar Snowflake.
- [x] Documentar cobertura real: herramientas Basketball Reference 2025–26, sin cuotas o lesiones; cero filas importadas y cero créditos The Odds API.
- [x] Sellar descarga y revisión en NBA-RUN-021 y registro de evidencias; integridad de archivos comprobada.

### NBA — EdgarParra565/player-performance-forecaster, 2026-10-05

- [x] Inventariar 365 archivos del commit y descargar 14 referencias verificadas; CSV vacío, base no publicada en main.
- [x] Revisar descarga masiva nba_api y límites de temporada/caché/PIT; separar cuotas reales de backfill con precios supuestos.
- [x] Registrar NBA-RUN-022, informe y documento; 80 evidencias verificadas, 33 archivos propios sin cambios, puertas pendientes.
- [ ] Completar huecos estadísticos con consultas por temporada y competición, sin importar el proyecto externo o sus precios supuestos.
- [x] Auditar ahorro/cobertura: 320 partidos regulares pendientes en cinco temporadas; prueba oficial gratuita terminó en ReadTimeout, cero filas o créditos nuevos.
- [x] Documentar uso de fuentes gratuitas y presupuesto separado para precios reales; sin activar descarga masiva de cuotas.

### NBA — recuperación gratuita de históricos, autorizada 2026-10-05

- [x] Crear lista exacta de pendientes por ID/temporada y diagnóstico reproducible: 395 partidos conocidos pendientes, incluidos 320 regulares; 299 regulares contienen minutos inválidos en la fuente.
- [x] Implementar captura NBA acotada y reanudable de boxscores/rotaciones; guardar originales, hashes y errores, detener lote ante acceso fallido.
- [x] Probar boxscores y GameRotation en muestra real: API oficial ReadTimeout y CDN 403; cero partidos o stints importados. Validadores conservan las restricciones existentes.
- [x] Probar lesiones históricas: tres PDF oficiales, ocho páginas verificadas, 84 observaciones de 30 jugadores; usar hora de cabecera, no nombre del archivo. Identidades y disponibilidad original siguen sin acreditar.
- [x] Validar con 136 pruebas NBA y 609 de harness; congelar 37 archivos propios y registrar NBA-RUN-024–026, 100 evidencias verificadas y 60 eventos de ledger; puertas pendientes.
- [ ] Recuperar físicamente los 395 pendientes con una fuente accesible y validar cada partido antes de importar; certificar calendarios de playoffs anteriores.
- [ ] Obtener rotaciones reales y conciliar tiempos, quintetos y minutos; los validadores probados con fixtures no acreditan cobertura real.
- [ ] Resolver IDs y horarios oficiales de las lesiones; ampliar archivo histórico y capturar disponibilidad prospectiva antes de habilitar señales médicas en picks.

### NBA — contraste de alternativas propuesto por el usuario, 2026-10-05

- [x] Fijar siete repositorios y comprobar interfaz, fuentes, actualización real y límites; no ejecutar proyectos externos.
- [x] Descargar archivo de transacciones JaseZiv y release ESPN 2025–26, comprobar hashes y cobertura. Mantener separados del dataset principal.
- [x] Probar fuente independiente Basketball Reference y conciliar un partido pendiente: 20 participantes, 240 minutos por equipo y estadísticas concordantes, sin errores del validador.
- [x] Documentar candidatos ESPN para 88 pendientes recientes, ausencia de pretemporada y límites de precisión/IDs/PIT; sin cuotas de apuestas o créditos The Odds API.
- [x] Formalizar adaptador Basketball Reference y cruce de IDs con caché/validación: ampliación de 159 partidos y 3,317 filas a versión nueva, linaje conservado; recuperación completa sigue pendiente.
- [ ] Recuperar pretemporada por separado; no equiparar tipo de temporada ESPN a prefijos NBA sin contraste del calendario.

### NBA — ampliación Basketball Reference autorizada 2026-10-05

- [x] Formalizar parser diario y cruce por fecha/localía/equipos/identidad: nombres exactos con acentos y variantes únicas de sufijos/puntos; sin apodos, generaciones contradictorias o candidatos múltiples. No reparar minutos o inferir DNP.
- [x] Capturar con caché, lotes de hasta 20 y seis segundos entre solicitudes: 140 páginas válidas, parada y respuesta conservada ante 403 del 2024-03-11; fechas posteriores no solicitadas.
- [x] Probar identidad/estadística/reloj/caché/integridad: 172 NBA y 609 harness aprobadas. Nueva versión con 159 partidos/3,317 filas; código propio congelado en 39 archivos.
- [x] Verificar todos los nuevos valores contra páginas raw y volver a conciliar los 159 partidos; 597 identidades consistentes, 154,058 filas previas conservadas; dataset ampliado 157,375 filas, modelo/fútbol/puertas preservados.
- [ ] Corroborar los nueve casos recibidos separados (siete diferencias de REB/AST, una referencia parcial y un estado desconocido) sin forzar aceptación.
- [ ] Recuperar los 152 regulares sin página válida tras el 403 y pendientes de otras competiciones: total restante 161 regulares, 71 pretemporada, tres playoffs y un play-in.

### NBA — Black Falcon / Apify, autorizado 2026-10-05

- [x] Preparar piloto de diez pendientes con IDs ESPN candidatos y referencias NBA; seis regulares, dos playoffs, un play-in y uno de pretemporada.
- [x] Ejecutar desde la sesión Apify existente: 282 filas descargadas, US$0.142 mostrado, máximo US$0.25; entrada/log/recibo/screenshot/JSON íntegro y hashes conservados, cero créditos The Odds API.
- [x] Validar identidad, estadística, DNP y precisión temporal: 247 candidatos NBA, cero diferencias P/R/A entre participantes; 53 diferencias null/cero DNP preservadas. Enteros de minutos no importados, pretemporada sin localía/IDs corroborados; dataset aceptado preservado.
- [ ] Recuperar segundos de minutos y referencias faltantes mediante fuente adecuada: Black Falcon repite los nueve partidos del ESPN previo; no ampliar ese flujo para solucionar precisión que no ofrece.

### NBA — servicios auxiliares para completar datos, autorizado 2026-10-05

- [x] Verificar cobertura real y precisión de servicios Apify; promedios de temporada/minutos enteros descartados; Flashscore decimal condicionado a concordancia individual y calendario NBA contrastado.
- [x] Ejecutar tres capturas Flashscore y dos de calendario NBA con límites: 6,631 registros Flashscore y 100 de calendario; US$2.064 mostrado, cero créditos Odds API; originales/entradas/logs/recibos conservados.
- [x] Ampliar fuentes útiles y conciliar íntegramente: 67 partidos/1,713 filas agregados, 157,375 filas previas conservadas; 6,052/6,150 regulares, 98 regulares y 71 pretemporada aún pendientes.
- [ ] Resolver identidades y discrepancias de los 169 boxscores restantes; 62 candidatos de pretemporada y calendario de sus 71 IDs ya capturados. No repetir descarga masiva para corregir problemas de conciliación.

### NBA — continuación de pendientes autorizada 2026-10-05

- [x] Auditar los169 candidatos:166 resúmenes ESPN;16 partidos/515 filas adicionales (3regular,13pretemporada),159603 filas finales. Mantener separados95regular y58pretemporada pendientes; no forzar IDs ni discrepancias.
- [x] Ampliar reportes médicos:486PDFs/36300 registros nominales; timestamp de cabecera y recibo actual;43675 filas enlazadas a partido,36063 a jugador. Segundo motor verifica todos; HTTP403 conservado y descarga detenida.
- [x] Recuperar rotaciones cronológicas:5161partidos/217334tramos; cinco jugadores, períodos/prórrogas, continuidad y minutos con cuantización por intervalo continuo del jugador;891partidos separados.
- [x] Ampliar props históricos acotados:20partidos/40snapshots de rebotes/2961pares válidos,420créditos de límite500; originales/temporalidad/cortes preservados, sin picks ni ROI.
- [x] Verificar datasets y preservación:19controles,6replaysPBP,40replayscuotas,486PDFs con segundo motor;609pruebas antes/después,39archivos NBA congelados y152evidencias previas verificados; NBA-RUN-033.
- [ ] Completar95regular/58pretemporada,330fechas médicas/cortes intradía y13nombres sin ID,891rotaciones separadas; ampliar puntos/asistencias/temporadas de props tras definir próximo presupuesto y reglas de liquidación. Informe:docs/nba_pendientes_recuperacion_20261005.md.

### NBA — fuentes Apify adicionales, autorizado 2026-10-06

- [x] Verificar cobertura y saldo; seis capturas de dos actores, US$2.341 del crédito gratuito. PBP sin acreditación de quintetos; cuotas sin timestamp original. Sin suscripciones/recargas ni créditos Odds API.
- [x] Conservar JSON completos, entradas, recibos, IDs y hashes; agregar Clippers–Nuggets 0012500052, 40 filas/30 participantes y diez DNP explícitos. Segundos exactos por equipo y PRA corroborados; 13 etiquetas de equipo contradictorias conservadas sin uso.
- [x] Sellar NBA-RUN-034: 159643 filas, 95 regulares/57 pretemporada pendientes; 71 calendarios/68 cruces exactos, 385 precios sin tiempo y 19 lesiones no históricas excluidos. 181 evidencias verificadas, 39 archivos NBA intactos, 609 pruebas antes/después. Informe: docs/nba_apify_fuentes_adicionales_20261006.md.
- [ ] Ampliar boxscores después de definir saldo/límite: diez partidos de 30 filas cuestan aproximadamente US$5 al precio observado, tope propuesto US$6; saldo disponible aproximado US$0.45. Resolver identidades y conflictos antes de importar. Props con timestamps, lesiones archivadas y rotaciones siguen requiriendo fuentes adecuadas.

### NBA — recuperación API-NBA autorizada 2026-10-06

- [x] Configurar la clave local excluida de Git; comprobar autenticación, plan y cuota sin conservar datos personales o secretos en evidencias. Plan NBA real Free; estado final declara70/100usadas.
- [x] Descubrir temporadas y calendario del proveedor; cruzar sus IDs con los 95 regulares y 57 de pretemporada pendientes. 72cruces únicos;80pendientes2025-26rechazados por plan. Sin contratación o exceso del límite local95.
- [x] Recuperar candidatos mediante consultas acotadas/reanudables; conservar originales, fechas y hashes.72boxscores/1543filas con minutos enteros;0partidos nuevos aceptados.159643filas previas preservadas. No inventar segundos ni resolver discrepancias por votación de fuentes.
- [x] Verificar el lote, documentar recuperación y bloqueos reales, ejecutar harness posterior y registrar evidencia NBA aislada sin modificar el modelo, fútbol, puertas o publicación.693pruebas antes/después;10controles;194evidencias,81eventos deledger; NBA-RUN-035.
- [ ] Obtener segundos individuales verificables y resolver discrepancias estadísticas/IDs para los72candidatos; acceso2025bloqueado para23regulares/57pretemporadas. Ampliar un plan no garantiza precisión ni recuperación; informe docs/nba_api_nba_recuperacion_20261006.md.

### NBA — auditoría de lineups Ramiro / pbpstats autorizada 2026-10-06

- [x] Fijar commit y descargar los CSV de lineups 2022–2026 con hashes y recibos; preservar boxscores y rotaciones aceptadas.
- [x] Contrastar cobertura, identidades, localía, períodos, continuidad, quintetos y minutos contra boxscores y PBP locales; separar discrepancias por partido.
- [x] Probar pbpstats sin consultas NBA automáticas; registrar formatos soportados y resultado real del contraste.
- [x] Conservar resultados reproducibles, pruebas e informe; registrar el incremento únicamente si satisface los controles existentes.

### NBA — ejecución de repositorios y scrapers históricos, autorizada 2026-10-06

- [x] Revisar y fijar código de las fuentes propuestas; ejecutar componentes de adquisición o parseo aislados y conservar resultados por repositorio.
- [x] Examinar el archivo corregido de pbpstats y contrastar PBP/quintetos de los partidos pendientes con las referencias existentes.
- [x] Procesar boxscores y PDFs disponibles, descubrir archivos médicos históricos y probar acceso público acotado; conservar bloqueos y no forzar aceptación.
- [x] Verificar preservación, cobertura incremental, pruebas e informe final; registrar lo ejecutado y las dependencias/accesos que impidan completar una fuente.

- [x] Instalar Java portátil y toolkit/MCP ZenRows solicitado para Claude Code; handshake stdio/44 herramientas, cero llamadas de proveedor.
- [ ] Completar95regulares/4pretemporadas,562rotaciones entre boxscores aceptados y330fechas médicas/13nombres; props y otros repos no ejecutados se detallan en docs/nba_github_scrapers_recuperacion_20261006.md.
