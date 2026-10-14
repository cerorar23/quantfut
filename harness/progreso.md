# Registro de decisiones — QuantFut

## 2026-10-03 — Decorrelación con el mercado: tampoco

Idea 4. Hubáček y Šír (IJF 2023) entrenan con `Σ(t−y)² − γΣ(t−m)²` y ganan
en la NBA contra el cierre de Pinnacle con un modelo peor que el mercado.
Leído el artículo antes de diseñar: con apuesta uniforme ellos también
pierden para todo γ; solo ganan con cartera de Sharpe. Regla fijada antes
en tareas.md. `eval/decorrelacion.py`: segunda etapa softmax sobre la
información de Kalman, `m` = justo temprano de Pinnacle, walk-forward por
temporadas (prueba 2021/22-2024/25), γ elegido en la temporada anterior.

- Con el γ elegido: EV contra el cierre −3,51 % [−3,78, −3,25], 0/7 ligas,
  8.802 apuestas. γ fijo 0 → 0,8: −3,78 % → −3,46 %. Apartarse del mercado
  mejora 0,3 puntos y no se acerca a cubrir el margen de Pinnacle (~3,9 %).
- Por qué no se probó la cartera de Sharpe: solo repondera las mismas
  apuestas según la ventaja estimada, y esa ventaja correlaciona −0,10 con
  el EV real (el quintil de más ventaja estimada da −5,1 %). Pesaría más lo
  peor. Es la misma selección adversa que el README midió en 2026-09-22.
- La correlación con el mercado se queda en 0,95 para todo γ: las variables
  son las probabilidades del propio modelo, que ya se parecen al mercado.
  Decorrelar de verdad exigiría información que el mercado no tenga, que es
  justo lo que falta (diagnóstico del README).

Balance de las 5 ideas: 1, 2 y 4 descartadas con datos; 3 y 5 desplegadas,
las dos sobre el criterio de casas blandas, que es donde está la ventaja.

## 2026-10-03 — Stake encogido por la incertidumbre de la persistencia

Idea 5 (Baker y McHale 2013; Uhrín y otros 2021). El stake era Kelly 0,20
sobre `edge × persistencia`, con la persistencia tratada como conocida.
Medida con bootstrap por semanas en football-data (2 %, primera oferta por
partido): 1xBet 0,72 [0,37, 1,06], Bet365 0,13 [−0,15, 0,41], William Hill
−0,15; dispersión entre casas 0,31. La de Bet365 no se distingue de cero.

- Factor `ρ²/(ρ²+SE²)` por casa, multiplicado al Kelly fraccional, que se
  queda en 0,20: el 0,20 es preferencia de riesgo; el factor, estimación.
  Lo que cambia es el reparto entre casas, no el nivel general.
- SE en vivo por el método delta sobre la sombra (coincide con el bootstrap:
  Bet365 0,140 frente a 0,146), mezclado con la previa con los mismos pesos
  que `mezclar` (la previa vale 100 partidos).
- "Stake sí, muestra no" (decisión del usuario): `stake_units` de la sombra
  y `stake_kelly_units` del candidato siguen SIN factor y deciden qué es
  publicable; el factor va en columnas nuevas (db/039). La puerta mide lo
  mismo que antes del cambio.
- Desplegado 18:03 UTC (respaldo `~/respaldo_20261003_stake/`). Factores
  vigentes: 1xBet 0,94, Betano 0,71, Betsson 0,65, Bet365 0,54 (la sombra
  ya la sube desde 0,43), William Hill 0. En la misma comprobación: las 258
  filas de The Odds API desde el despliegue de 3A traen `book_updated_at`.

## 2026-10-03 — Latencia de las casas blandas: empezar a medirla

Idea 3. Hoy no se podía medir: API-Football refresca cada competición de
golpe cada varias horas con una sola hora para todas las casas, y
`odds_worker` descartaba el `last_update` por casa de The Odds API. Además
solo hay 6 capturas por partido y la sombra lleva 184 ofertas.

- 3A (gratis): db/038 `odds_snapshots.book_updated_at` + `odds_worker` la
  guarda. ADD COLUMN: el trigger de inmutabilidad sigue igual.
- 3B: `ingest/rafagas.py` cada 5 min, T-6 h a T-15 min, 1X2 con
  `bookmakers=` (10 casas → 1 crédito), Premier, LaLiga y Liga MX, a
  `odds_rafagas` (tabla aparte: ventanas, sombra y cierre no la ven), una
  fila por CAMBIO de precio. Tope 3.000 créditos/mes, contado en
  `rafagas_log` (decisión del usuario).
- Por qué 5 min bastan: `last_update` fecha cada cambio al segundo; la
  consulta solo tiene que verlo antes de que vuelva a cambiar.
- Vara fijada con el usuario: su cliente tarda UNA HORA O MÁS en apostar.
  `eval/latencia.py` mide la fracción de ofertas que duran ≥60 min por casa
  (regla en tareas.md). Si una casa no llega a la mitad, sus ofertas no son
  aprovechables con el formato actual y no deberían contar para la puerta.
- Para no duplicar el emparejamiento evento→partido, `odds_worker` expone
  `match_meta` y `match_events`; las ráfagas los reutilizan.
- Despliegue: respaldo en `~/respaldo_20261003_latencia/`, migración
  aplicada, worker reconstruido y reiniciado después del cierre de los dos
  partidos de LaLiga 2 de las 16:30 UTC. Primera lectura posible tras 2-3
  fines de semana desde el 9-oct.

## 2026-10-03 — Más-menos por jugador: tampoco aporta sobre el XI simple

Idea 2 de la literatura (Kharrat, McHale y Peña 2020; Hvattum): valorar al
jugador por cómo le va al equipo con él en el campo, no por sus estadísticas.
Versión aproximada por minutos (decisión del usuario; el diseño del 29-sep la
dejaba fuera por no tener el minuto de cada cambio). Diseño y regla fijados
antes de ver resultados en tareas.md. Mismas 3.646 filas y misma base
(`oos_2026.10.01-030007.pkl`) para los cuatro brazos:

| brazo | RPS | log-loss | ECE | ligas | valida |
|---|---|---|---|---|---|
| base | 0,21826 | 1,0516 | 0,03029 | - | - |
| XI simple | 0,21686 | 1,0471 | 0,03086 | 8 | sí |
| XI con valor | 0,21907 | 1,05448 | 0,03581 | 2 | no |
| XI con nota | 0,21808 | 1,05115 | 0,03034 | 8 | (comparación) |
| más-menos | 0,21838 | 1,05212 | 0,03324 | 4 | no |

- El más-menos queda en la base o un pelo peor. Con dos señales no
  sobreajusta como "XI con valor" (18), así que el problema no es la forma de
  medir al jugador sino que, con un año de datos, quién falta no añade nada a
  cuántos habituales faltan.
- Límite conocido de la aproximación (el test lo documenta): un jugador que
  juega siempre es inseparable de su equipo; el más-menos solo lo mide por
  los partidos que se pierde, que son justo los raros.
- La versión exacta (`/fixtures/events`, ~4.600 peticiones) NO se hace: era
  condicional a que esta apuntara algo.
- Ejecución: copia aparte del código en `/tmp` del worker, sin reconstruir,
  reiniciar ni guardar artefactos; borrada al terminar. En el servidor sigue
  el `player_value.py` anterior: el brazo entrará en el reentreno mensual
  cuando se despliegue, como "XI con valor", por si la muestra cambia.

## 2026-10-03 — El modelo tampoco llega antes que la cuota temprana

Pregunta: `w_model = 0,0001` se midió contra el cierre; ¿y contra la cuota de
Pinnacle de 1-3 días antes, que es la que se puede tomar? Regla fijada antes
de correr (tareas.md, "Ideas de la literatura" 1). `qf.eval.early_vs_close`,
Kalman secuencial con xG, 14.110 partidos de 7 ligas (2019/20-2024/25).

- Prueba principal: el movimiento temprana→cierre no va hacia el modelo.
  Pendiente 0,0028, IC95 por semanas [−0,0078, +0,0137], corr 0,006.
- Se eligió el MOVIMIENTO y no el RPS porque no depende del resultado: con
  42.000 filas detecta pendientes de ~0,01. Control positivo para comprobar
  que la prueba no es ciega: la media de casas como "modelo" da 0,38 [0,29,
  0,46] en 7/7 ligas; Bet365, 0,16 [0,13, 0,19]. Las casas sí anticipan a
  Pinnacle; el modelo no.
- Apostar a Pinnacle temprano con ≥2 % de ventaja del modelo: −4,87 %
  [−5,15, −4,59] contra el cierre justo, peor que sin criterio (−3,9 %): la
  misma selección adversa del README. `w_model` contra la temprana: 0,0001.
- Fuga cerrada al implementar: `predict_sequential` estima nivel de goles y
  localía por liga con TODO el histórico. Aquí se fijan con lo anterior al
  primer partido evaluado (`_KalmanSinFuturo`); sin eso, una pendiente
  positiva habría sido sospechosa.
- La base local no tenía db/023 (`model_enabled`) y `load_training_data`
  fallaba: se aplicó la migración del repo en LOCAL. El servidor ya la tenía.

Consecuencia: la información del modelo (goles + xG) no llega antes que el
mercado en ninguna ventana medible. Lo que queda de la lista son fuentes de
información nueva (punto 2, más-menos) o del criterio sharp (3 y 5).

## 2026-10-03 — FotMob para histórico puntual, futuros de otra API

Alcance explícito del usuario: 23 ligas y 2 copas, desde 2024 hasta hoy.
Se interpreta 1-ene-2024 a 3-oct-2026 inclusive en America/Mexico_City.
Se aprovechan las rutas JSON documentadas en Public-FotMob-API mediante un
descargador independiente de biblioteca estándar; no se despliega su proxy
Django ni se añade una fuente recurrente. Sin escritura en Postgres.

La consulta real de allLeagues confirmó los 25 IDs, y matchDetails respondió
200 con xG, eventos, alineaciones y tiros para Liverpool-Newcastle (1-ene-2024).
Inventario completo: 22.461 partidos terminados, 96 temporadas/torneos, 0
errores de calendario. La descarga de detalles queda EN CURSO, reanudable,
en `.local/fotmob-history/2024-01-01_2026-10-03/`; `coverage.json` expresa
la terminación real y no el éxito de arranque. Captura JSON comprimido con
SHA-256/hora real, y CSV con xG ausente separado de pendiente/error. Ante
401/403/429 se detiene sin evasión. No se presume cobertura de xG total.

Validación: 573 pruebas pasan (13 nuevas sobre fechas locales, identidad,
xG total frente al del descanso, ceros/datos ausentes, caché y denegaciones).
Se ejecutó el arnés Windows real: el shell Git mínimo omite Python y no
dispone de dirname, así que su salida OK no valida las pruebas.

Corrección durante la descarga: ediciones de Liga MX, Brasil y Argentina
usan IDs de torneo propios con `general.parentLeagueId` explícito. La guarda
original rechazaba esos detalles aun guardando el JSON. Se valida ahora la
liga principal declarada, manteniendo las guardas de ID, equipos y fecha.
Reanudada en segundo plano con logs y PID en `process.json`, recuperando los
detalles desde caché: Liga MX completa, 923/923 con xG. Dos respuestas de
Brasil tienen fecha distinta de su calendario y siguen como error; no se
relaja esa guarda ni se inventa la fecha. Validación actual: 584 tests pasan,
14 específicos de FotMob (hay otros cambios simultáneos en el workspace).

## 2026-09-24 — Fase 2.D medida: la forma de la matriz no es el problema

Implementados como challengers (a petición del usuario, sabiendo que el
esperado era 0,001–0,002 de RPS): Poisson bivariante, Conway-Maxwell-Poisson,
conteo Weibull con cópula de Frank y probit ordenado sobre la diferencia de
goles. Decisión de diseño: los brazos de conteo conservan las MEDIAS de
Dixon-Coles fuera de muestra y cambian solo la forma. Así cada brazo aísla lo
que dicen mejorar los papers (dispersión y dependencia) y no hace falta otro
ajuste de fuerzas por equipo, que costaría horas por brazo. `dc_tau` se
reajusta con el mismo protocolo para que la comparación sea justa.

Resultado sobre 2.641 partidos del último año: ninguno mejora a `tau`; CMP y
Weibull empeoran el 1X2 con el IC entero por debajo de cero. Los parámetros
se quedan pegados a Poisson (ν=1,09, c=1,05), es decir, los datos no tienen
la sobredispersión que esos modelos corrigen. Confirma el diagnóstico de
siempre: falta información, no técnica. No se activa nada; el informe se
recalcula en cada entrenamiento por si con más muestra cambia. Detalle y
cifras en `tareas.md` (2.D).

## 2026-09-24 — Rate limiting: existía, pero con dos agujeros

El pendiente "rate limiting en rutas públicas" ya estaba cubierto por el
middleware global. Revisándolo salieron dos fallos: el tope de 10/min de
`/control` se comparaba contra el contador compartido de todas las rutas
(abrir la web y luego el panel en el mismo minuto daba 429), y en IPv6 se
limitaba por dirección, cuando un cliente suele controlar un /64 entero.
Contador propio para `/control` e IPv6 agrupado por /64; las IPv6 que
envuelven una IPv4 se cuentan como la IPv4. Con Cloudflare delante el caso
IPv6 no es teórico: la primera petición de verificación ya llegó por IPv6.

## 2026-09-24 — Fuera `soccerdata`

Se borró `xg_fbref.py` en vez de aflojar el pin: FBref bloquea el scraping
con Cloudflare y el mismo dato llega por `xg_worldfootball`, así que arreglar
la instalación de `soccerdata` solo habría devuelto un módulo que no funciona.
Con él salen `lxml` y `html5lib`, que ningún código usaba. `requirements.txt`
vuelve a resolver (`pip install --dry-run`) y la imagen del servidor se
reconstruyó sin ellos.

## 2026-09-24 — Nombres sin resolver: una alarma que no se podía apagar

De 36 nombres pendientes en producción solo uno era trabajo: `Coventry City`,
el nombre de The Odds API para el Coventry que API-Football había dado de
alta como `Coventry` al ascender. Sin alias, cada pasada descartaba sus
eventos de Premier (8 descartes en dos días). Alias en `db/020`, nunca equipo
nuevo; el difuso daba 76 y no se toca el umbral (ver 013).

Los otros 35 son clubes de ligas fuera del catálogo jugando copas europeas:
irresolubles por diseño. Pero la alarma los contaba, así que "Salud del
sistema" iba a estar en rojo para siempre — el mismo fallo que ya se corrigió
el 2026-09-22 con el calendario. Ahora cuenta solo nombres vistos en liga
doméstica o sin competición anotada (en la duda, alarma). Para poder
distinguirlo, `odds_worker` anota la competición del feed con
`resolve_team(seen_in=)`, un parámetro aparte porque pasar `league_id`
habría ACOTADO la búsqueda a los equipos de la copa, que no tiene ninguno.
Si un nombre se ve primero en copa y luego en liga, gana la liga: es la que
debe alarmar.

## 2026-09-24 — Guía visual de QuantFut aplicada a la demo

La portada pasa de una presentación casi solo editorial a mostrar una ficha
1X2 ficticia junto a su explicación y acceso al historial: la identidad
propia de QuantFut debe ser la evidencia del partido, no los efectos típicos
de una casa de apuestas. `frontend/DESIGN_SYSTEM.md` fija tokens, jerarquía,
componentes, móvil y accesibilidad. UI UX Pro Max se usó como catálogo de
criterios, sin instalarlo, añadir dependencias ni copiar una plantilla.
El prototipo conserva sus seis vistas y sigue sin cuentas, pagos, apuestas o
datos reales. El contenido futuro autorizado permanece en el FastAPI modular,
nunca oculto solo con CSS ni protegido por un secreto en el navegador.

## 2026-09-24 — Fase 2: lo que faltaba era código de arranque, no más modelo

Revisada la Fase 2 entera con el sistema ya en producción. Casi todo lo
pendiente es muestra y no se acelera con código, pero había un bloqueo que sí
era código: **sin modelo activo nada de la parte "modelo" acumula**. El job
de las 08:00 falla ("No hay ningún modelo activo") y `qf.model.shadow`
responde "sin modelo activo" cada 5 minutos, así que los cuatro brazos de 2.B
y el XI de 2.C no guardan ni una fila. El único reentrenamiento programado era
el mensual (1-oct).

No se tocó la puerta: rechazar con mercado de 252 días es correcto. Se añadió
`train --bootstrap` diario que solo entrena si no hay modelo activo Y el
cierre sharp ya pasaría la misma comprobación de frescura. La constante se
movió a `promotion.MARKET_MAX_AGE_DAYS` para que el chequeo barato y la
puerta no puedan divergir. Motivo del chequeo previo: un entrenamiento cuesta
~3,5 h en el VPS; reentrenar a ciegas cada día quemaría CPU para una
respuesta que ya se conoce.

La muestra comercial (sombra sharp) NO depende del modelo y ya acumula:
`af_odds` 801 filas en 21 partidos el primer día. Pero no se veía en ningún
sitio del operador: Grafana leía `pick_results` (vacía a propósito con la
publicación pausada) y con `clv_pct`, la vara que 015 descartó. `/control`
gana la tarjeta de la puerta usando el mismo `shadow_sharp.report()` que
decide, no una copia en SQL que pudiera divergir.

Cerrados como superados, no borrados: validar la zona de abstención, la
incertidumbre relativa al mercado y la ordenación media/sd (servían para
apostar con el edge del modelo, criterio eliminado en el paso 4;
`uncertainty.py` ya no lo importa nadie), y extender la mezcla al AH (la
premisa de devolver el AH a los picks ya no aplica). 2.D (Weibull, CMP,
probit) no se implementó: esperado 0,001–0,002 de RPS y el producto ya no
depende de que el modelo bata al mercado.

## 2026-09-24 — El cron del worker nunca había corrido en el servidor

Tras el primer despliegue, `docker compose exec worker crontab -l` devolvía
"no crontab for root": el `command` del servicio `worker` en
`docker-compose.yml` intentaba `chmod 0644 /etc/cron.d/quantfut` antes de
`crontab /etc/cron.d/quantfut`, y ese archivo está montado `:ro` (es el
`./scripts/crontab` del repo). El `chmod` fallaba ("Read-only file system"),
el `&&` cortaba antes de `crontab`, y el contenedor seguía "Up" porque
`cron -f` sí llegaba a ejecutarse — pero sin ningún job cargado. Cuatro horas
sin captura de cuotas, resultados ni nada, sin ningún error visible salvo una
línea en `docker compose logs worker`.

El `chmod` no hacía falta: `scripts/crontab` está en formato de crontab de
usuario (5 columnas, sin campo de usuario), y `crontab <archivo>` solo
necesita *leer* el archivo — root puede leerlo aunque el volumen sea `:ro`.
Se quitó el `chmod` y se encadenó todo con `&&` explícito para que un fallo
futuro en cualquier paso no deje `cron -f` corriendo en silencio con cero
jobs. Redesplegado y verificado: `crontab -l` en el worker devuelve los 17
jobs y `cron -f` corre como proceso propio (no como parte de la cadena `&&`).

Consecuencia directa: el primer entrenamiento (`qf.model.train`, mismo día)
no activó ningún modelo — no por este bug, sino porque `market_age_days=250`
en la base restaurada del local (el cierre sharp más reciente es de enero
2026): la puerta de promoción exige mercado con menos de 30 días. Es el
comportamiento correcto de la puerta, no un fallo; hace falta que
`odds_worker`/`af_odds`/`shadow_sharp` acumulen cierres frescos (ahora sí
corriendo) antes de reentrenar y esperar activación.

## 2026-09-24 — Despliegue detrás de Cloudflare: lo que rompía sin avisar

Desplegado en el VPS de Contabo (`31.220.72.30`) con el dominio
`pronosticosdeportivos.pro` detrás del proxy de Cloudflare. El `Caddyfile`
anterior daba por hecho que Caddy recibía las conexiones directamente, y con
Cloudflare delante eso fallaba en tres puntos, sin que ninguno diera error:

1. `remote_ip {$GRAFANA_ALLOWED_IP}` veía siempre una IP de Cloudflare, así
   que `/control`, `/admin` y Grafana habrían respondido 404 también al
   operador.
2. Caddy reescribe `X-Forwarded-For` con la IP del salto anterior, y el rate
   limit de `main.py` usa su primer elemento. Todos los visitantes de un mismo
   nodo de Cloudflare habrían compartido el cupo de 60/min. Arreglado en
   Caddy (`trusted_proxies` con los rangos de Cloudflare + `CF-Connecting-IP`
   + `header_up X-Forwarded-For {client_ip}`), sin tocar `main.py`.
   Verificado: la clave de Redis del rate limit lleva la IP real del cliente.
3. Docker publica 80/443 por delante de ufw, así que un "solo Cloudflare"
   hecho con ufw habría sido falso. El filtro va en `DOCKER-USER`
   (`qf-cf-firewall`). Verificado: HTTPS directo a la IP no conecta y a través
   de Cloudflare responde 200.

El usuario eligió Cloudflare Access en lugar de filtrar por IP para el acceso
de operación. Caddy exige que llegue `Cf-Access-Jwt-Assertion` pero no valida
su firma: con el origen cerrado a Cloudflare, esa cabecera solo puede venir de
Access. Si algún día se abre el origen a otro tráfico, hay que validar el JWT.
Hasta que Access esté configurado, `/control`, `/admin` y `panel.` responden
404: si falta la configuración, el acceso queda cerrado, no abierto.

Backups: `pg_dump -Fc` (el formato que lee `restore_db.sh`, no el `.sql.gz`
del README anterior) y sin `rclone`, porque no hay destino externo. Esto
queda pendiente y es el mayor riesgo que sigue abierto: la base guarda picks
sellados que no se pueden reconstruir.

Las contraseñas de Grafana de `.env.server` se regeneraron antes del primer
arranque porque se mostraron en la salida de una herramienta durante la
sesión.

## 2026-09-23 — Preparación del despliegue: el cron del contenedor nunca habría funcionado

Al revisar `docker-compose.yml` y `scripts/crontab` antes del primer despliegue
salieron dos fallos que habrían dejado el sistema entero parado sin un solo
error visible (cada job escribe en su propio log dentro del contenedor):

1. El worker copiaba a `/etc/environment` (de donde cron toma el entorno vía
   pam_env) solo las variables con ciertos prefijos. `API_FOOTBALL_*` no
   estaba: calendario, resultados, alineaciones, lesiones y cuotas de
   API-Football habrían fallado en cada pasada. Tampoco `PUBLISH_*`,
   `SOFT_*`, `META_*`… Ahora se copia todo. Una lista blanca de prefijos es
   exactamente el tipo de cosa que se queda atrás cada vez que se añade una
   variable.
2. El crontab no fijaba `PATH`; el de cron es `/usr/bin:/bin` y en
   `python:3.12-slim` el intérprete está en `/usr/local/bin`. "python: not
   found" en cada job. `BASH_ENV` no servía de nada con `SHELL=/bin/sh`.

No verificado en un contenedor real: no hay Docker en este entorno. Por eso el
procedimiento termina comprobando `/var/log/af_odds.log` tras la primera pasada.

Decisión de migración: se restaura la base local (`pg_dump`, 4 MB) en vez de
rehacer el backfill en el servidor, porque los alias revisados a mano no se
reproducen solos. `scripts/restore_db.sh` se niega a pisar una base con datos
sin `--force` y re-crea permisos y contraseña del rol de Grafana (el `004` lo
crea con una contraseña por defecto que no coincide con la de Grafana). La
base local no tenía ningún modelo activo ni lotes sellados: no había cadena que
trasladar, pero hay que entrenar el primer modelo en el servidor antes de las
08:00. `014_injuries` tampoco estaba aplicada en local; se aplicó.

## 2026-09-23 — Sombra del criterio sharp: lo que decide si se reactiva la publicación

Paso 5, último del plan. `src/qf/publish/shadow_sharp.py`, `db/018`.

- **Qué cuenta para la puerta: lo que se habría publicado, no cada oferta.**
  Capturando cada hora, un mismo partido acumula decenas de ofertas; contarlas
  todas inflaría `n` con apuestas correlacionadas que nadie habría hecho. La
  vista "publicables" toma, por partido, la primera pasada en la que el
  criterio habría dado un pick con stake, y de ella la de mayor edge esperado:
  una fila por partido, como el sistema real. Todas las ofertas se desglosan
  aparte para investigar.
- **Se registran también las ofertas de stake 0.** Son las de casas con
  persistencia medida nula (William Hill); sin registrarlas no habría forma de
  comprobar si esa persistencia está bien estimada.
- **Se guarda la persistencia usada ese día** en cada oferta: la tabla de
  `picks.PERSISTENCE` va a cambiar con esta misma muestra, y el informe tiene
  que poder distinguir qué se decidió con qué.
- **Tablas propias, no `shadow_picks`**: aquellas cuelgan de una predicción
  del modelo en sombra, y este criterio no sale del modelo.
- **Desglose por antelación (0-6, 6-24, 24-48, 48-72 h).** El histórico solo
  validó 24-48 h. Si el valor solo aparece en un tramo, hay que restringir la
  publicación a él antes de reactivarla.
- **Reactivar la publicación no es automático.** `/model-card` publica
  `sombra_criterio_sharp.autorizada`, pero `PUBLISH_PICKS_ENABLED=1` lo pone
  el usuario, viendo el desglose.

Corregidos de paso dos textos que ya eran falsos tras el paso 4: el
`/model-card` y el comentario de `PUBLISH_PICKS_ENABLED` decían que el
criterio vigente ordenaba por el edge del modelo.

## 2026-09-23 — El modelo deja de elegir los picks

Paso 4. `publish/picks.py` selecciona casas blandas que pagan por encima del
precio justo de Pinnacle; el criterio del modelo (anti-señal medida) se borró
con sus integraciones. Decisiones que no se leen en el diff:

- **Un snapshot, nunca dos fuentes cruzadas.** La casa blanda y Pinnacle
  salen de la misma respuesta (API-Football) o de la misma captura (The Odds
  API). Un 1xBet de API-Football de hace 19 h contra un Pinnacle fresco de The
  Odds API "mostraría" el movimiento de las 19 h como edge.
- **Point-in-time.** Del lado de API-Football solo cuenta lo que ya teníamos
  (`fetched_at ≤ ahora`), y por antigüedad del precio (`odds_as_of`) se corta a
  6 h: un pick con un precio que ya no existe engaña al suscriptor y además
  infla el CLV medido, porque se compara una cuota que no se podía tomar.
- **El stake sale del edge esperado al cierre, no del bruto**, con la
  persistencia medida por casa (1xBet 0,72, Bet365 0,13, William Hill 0; las
  no medidas, 0,42 de población). Sustituye al 0,55 fijo para todas. Con
  persistencia 0 el candidato se genera igual —la sombra necesita medirlo— y
  `select_daily` lo descarta por stake.
- **La confianza del modelo ya no filtra.** `daily.run` pasaba solo las
  predicciones que no eran de confianza baja; eso era una regla sobre el
  modelo y ya no aplica. La predicción sigue siendo obligatoria: cada pick la
  referencia (FK) y se sella con ella.
- **`min_price`, `fair_prob`, `odds_source` y `odds_as_of` se sellan.** Son
  parte de lo que se publica; si no entraran en el payload de la cadena, se
  podrían cambiar sin que la verificación lo detectara. Los lotes anteriores
  no cambian: `verify` recalcula desde los ficheros en disco.
- **Se borró** `tests/test_eligible_markets.py` y los tests del interruptor
  de incertidumbre: probaban un comportamiento que ya no existe.
  `model/uncertainty.py` y sus tests del módulo se conservan.
- `/model-card` corregido: afirmaba que el edge publicado llevaba el factor
  0,55 y que la confianza baja impedía picks; ninguna de las dos es ya cierta.
  Añadidas como limitaciones la dependencia de 1xBet y que Bet365/Betano no
  tienen histórico.

Sin validar: el histórico midió precios de 24-48 h antes del partido; en vivo
se decide a cualquier distancia. La sombra (paso 5) debe estratificar por
antelación antes de fiarse del conjunto.

## 2026-09-23 — Captura de cuotas de API-Football en tabla propia

Pedida por el usuario. `src/qf/ingest/af_odds.py`, `db/016_af_odds.sql`.

- **Tabla separada (`af_odds_snapshots`), no `odds_snapshots`.** Esa tabla
  la leen sin filtrar por casa el consenso de mercado de `daily.py`, el mejor
  precio de `picks`, `/fair-price`, la sombra y `health` ("última captura").
  API-Football actualiza cada liga de golpe cada varias horas (2 h en MLS, 19
  h en Liga MX, 3,5 días en Premier durante un parón): sus precios viejos
  habrían entrado en todos esos cálculos, y la salud habría dado por vivo un
  worker de The Odds API caído.
- **Dos tiempos por fila.** `provider_updated_at` es el `update` del
  proveedor (cuándo existía el precio) y `fetched_at` cuándo lo supimos. Una
  decisión en T solo puede usar `fetched_at ≤ T`. Guardar solo la hora de
  captura habría hecho pasar por frescos precios de 19 horas.
- **Deduplicación por esa marca.** El proveedor devuelve la misma
  actualización durante horas; la restricción única con
  `provider_updated_at` hace que repetir la consulta no duplique filas en una
  tabla inmutable. Comprobado: 78 filas en la primera pasada, 0 en la segunda.
- **Cada hora, no cada 3 horas** como se propuso al usuario. El proveedor
  actualiza cuando le toca y el job diario decide a las 08:00: con el cron cada
  3 h, una actualización de las 06:10 no llegaría a tiempo. Coste ~50
  peticiones/hora de 7.500/día. Horizonte de 72 h, que cubre la ventana
  temprana del criterio (24-48 h).

## 2026-09-23 — Cuatro ligas con histórico de The Odds API: el valor accesible es 1xBet

Descargado 2025 de Brasil, Argentina y MLS (12.640 créditos, exactamente lo
que calculó `plan`; saldo 3.217). Con Liga MX: 1.681 partidos con Pinnacle
antes y al cierre.

| casas (umbral 2%) | n | valor esperado al cierre | IC95 |
|---|---|---|---|
| todas las casas blandas (26) | 317 | +2,78% | [1,79, 3,78] |
| accesibles: 1xBet + William Hill + 888sport | 127 | +3,83% | [2,36, 5,20] |
| solo 1xBet | 126 | +3,91% | [2,45, 5,31] |

Lo que hay debajo del +3,83%, y por qué no se puede leer como "funciona":

- **Es una sola casa.** 126 de las 127 apuestas accesibles son de 1xBet.
  William Hill y 888sport casi nunca superan el precio justo. Un producto que
  depende de una sola casa desaparece el día que esa casa limita las cuentas
  de los suscriptores, y es lo primero que hacen con quien gana.
- **Es sobre todo MLS** (85 de 127). Argentina 26 (+2,5%), Brasil 9, Liga MX 7
  y negativa. En Liga MX el valor que había (+2,43% con todas las casas) era de
  Coolbet y Unibet, que los suscriptores no usan.
- **No pasa la puerta en amplitud:** pide 3 ligas con 30 apuestas; con las
  casas accesibles solo MLS la supera en un año.
- Coincide con football-data, que es independiente: 1xBet +2,78% en las 7
  ligas europeas en 2024/25 (única temporada en que los CSV la incluyen).

**Las casas de los suscriptores no están donde se creía.** Decisión del
usuario: apuestan en casas internacionales presentes en LatAm (Bet365, 1xBet,
Betway, William Hill, 888…). La región `eu` de The Odds API solo cubre 1xBet,
William Hill y 888sport; Bet365 no está en The Odds API (solo `bet365_au`),
Betway solo en `uk`, y no hay ninguna casa mexicana. Preguntado a
API-Football (`/odds/bookmakers` y `/odds` por competición): de 33 casas en su
catálogo, solo 9 cotizan de verdad nuestras competiciones, y entre ellas están
**Bet365, Betano, 1xBet y William Hill, junto a Pinnacle en la misma
respuesta**, en 12 de 13 (Champions sin cuotas en la consulta). Betway,
888sport, Betcris y Sportingbet están en el catálogo pero con cero partidos.
Límites: refresco cada ~3 h y solo 7 días de histórico, y no se sabe si su
Bet365/Betano son los precios de las webs mexicanas o los internacionales.
Otros proveedores revisados: OddsPapi tiene Betano MX (la única versión
mexicana encontrada) y OpticOdds tiene Playdoit; ninguno tiene Caliente.

## 2026-09-23 — Histórico de The Odds API: Liga MX tiene valor, pero en casas europeas

Paso 3. `src/qf/ingest/odds_history.py`. Decisiones:

- **No se escribe en `odds_snapshots`.** El plan decía lo contrario; se
  cambió al escribir el código. Esa tabla es inmutable y alimenta el
  entrenamiento (`window_tag='close'`) y la liquidación: un error de parseo o
  de emparejamiento quedaría para siempre y contaminaría las dos. Las
  respuestas se guardan crudas en `.local/odds_hist/` y se reprocesan sin
  volver a pagarlas. Cargarlas en la base es una decisión aparte.
- **Cómo se gasta poco.** Un snapshot trae TODOS los partidos próximos de la
  competición, así que el precio temprano sale de un snapshot diario a las
  12:00 UTC (24-48 h antes de cada partido) y el cierre, de uno por hora de
  inicio distinta, 5 min antes. `plan` calcula el número exacto con el
  endpoint de eventos (1 crédito por semana) ANTES de gastar.
- **Solo 1X2.** El backtest de football-data no encontró oportunidades
  verificables en over/under; cada mercado duplica el coste.
- **Guardas propias del feed:** una cuota con `last_update` de más de 60 min no
  cuenta como apostable; un "cierre" de más de 30 min antes del kickoff no es
  un cierre; los exchanges no entran como casa blanda (cobran comisión). La
  guarda de referencia es la misma del backtest, con el consenso de las casas
  blandas del snapshot en lugar de la media de football-data.

Coste medido para 2025: Liga MX 3.920, Brasil 3.910, Argentina 5.090, MLS
3.640 créditos (16.560 en total). Solo se descargó Liga MX.

Resultado Liga MX 2025 (316 partidos con Pinnacle antes y al cierre, 22 casas):
mejor cuota a umbral 0% → n=148, valor esperado al cierre justo +2,43%, IC95
por semanas [0,47, 4,20]; a 2% → n=70, +2,87% [−0,18, 5,51], sin concluir.

Lo que importa para el producto: el valor se concentra en Coolbet (38 de 70
apuestas a 2%, +4,39%) y Unibet (`unibet_eu` +4,00%). Son casas europeas; es
probable que un suscriptor en México no pueda usarlas, y la región `eu` de The
Odds API no incluye casas mexicanas. `unibet_it/nl/se` son la misma casa con
otra marca y dan exactamente las mismas cifras: al contar apuestas por casa no
hay que sumarlas como independientes. Y el volumen es bajo: 148 apuestas al año
en una liga con la puerta pidiendo 300 en 3 ligas.

## 2026-09-23 — Liquidación de AH: fracción ganada y fracción devuelta, por separado

El bug anotado en la entrada de abajo. `_settle_outcome` devolvía un único
multiplicador (`0,5·a + 0,5·b`, con el empuje valiendo 0,5 por pata) y
`settle_pending` lo multiplicaba por la cuota. Eso paga a cuota la mitad
empujada, que en realidad solo se devuelve. A 1,90: medio-ganada +0,425 en vez
de +0,45, medio-perdida −0,525 en vez de −0,50. A 2,00 coinciden, y por eso no
lo delataba ningún ejemplo "redondo".

Se eligió devolver `(outcome, ganada, devuelta)` en vez de una función de la
cuota porque es exactamente la descomposición que ya usa
`pricing.market_asian_handicap` para fijar la cuota justa (`E[w]·cuota +
E[push]`). Precio y liquidación hablan ahora el mismo idioma, y el empuje de
línea entera deja de ser un caso especial en `settle_pending`: con
ganada=0 y devuelta=1 el beneficio sale 0 solo.

El error no era ruido: en medio-ganada y medio-perdida vale
`0,25·cuota − 0,5` por unidad, con signo fijo según el lado de 2,00. Por
debajo (casi todas las cuotas de AH) restaba siempre; por encima sumaba.
Habría sesgado el ROI publicado sin tocar el CLV, así que la puerta no lo
habría detectado. `pick_results` estaba vacía: no hubo filas que
rehacer. `shadow.py` liquida solo 1X2 con su propio código y no usa
`_settle_outcome`.

## 2026-09-23 — Backtest "casa blanda contra sharp" en el repo, y Pinnacle también se rompe

Paso 2 del plan: `src/qf/eval/soft_vs_sharp.py`. Reproduce el piloto al
decimal (mismos n y EV por casa), así que el piloto no tenía un error de
cálculo. Pero al mirar la tabla completa apareció algo que el piloto no vio.

**La referencia sharp también falla, y en over/under falla de forma que se
esconde sola.** Bet365 y la MEDIA del mercado daban "edges" tempranos del
10-13% en over/under que persistían ENTEROS hasta el cierre (persistencia
≈1,0). La media del mercado no puede batir al precio justo por 12 puntos. Las
filas lo explicaban: Pinnacle a 1,53/2,63 mientras todas las casas daban
1,36-1,44 en el over, y con el precio temprano idéntico al de cierre. Pinnacle
congelado o en otra línea. El cierre no lo delata porque es el mismo precio
roto: es exactamente el tipo de fallo que un backtest valida a sí mismo.

Comprobación independiente: en 2024/25, único año con Betfair Exchange en los
CSV, cuando Pinnacle y Betfair discrepan más de 3 puntos en over/under, la
media de las casas se pone del lado de Betfair en 21 de 24 casos. En 1X2 casi
no ocurre (5 casos, y la media apoya a Pinnacle en 4).

Guarda elegida: `MAX_SHARP_DEVIATION = 0,03` sobre la probabilidad justa de
Pinnacle TEMPRANA frente a la de la media de las casas TEMPRANA. Solo usa
información anterior al cierre, así que no es una fuga y se puede aplicar
igual en vivo. El 0,03 es unas dos veces el p99 de la desviación (1,5-1,6
puntos) y es el primer valor en el que desaparecen TODOS los casos de "la media
supera el precio justo". Descarta 1 mercado 1X2 y 42 de over/under de 14.294.
Sin media completa no se puede verificar y el mercado no entra.

Resultado con guarda (1X2, umbral 2%, mejor cuota entre las 6 casas reales):
n=1.378, EV al cierre justo +2,09% (IC95 por semanas [1,21, 2,91]), positivo
en las 7 ligas; persistencia 0,42; ROI +2,9% con IC [−10,2, +15,1], sin
concluir. Over/under en casas reales: 11 apuestas, IC que incluye cero. El
"máximo del mercado" sigue positivo en los dos mercados, pero no es una casa y
no se puede publicar como pick.

Lo que esto NO prueba: los CSV traen un único snapshot pre-cierre (viernes o
martes), no la operación real con varias ventanas; no incluye el límite de
cuentas de las casas blandas; y el ROI no está demostrado. Lo que SÍ prueba es
que el criterio tiene valor contra la misma vara que decide la puerta, que es
lo que el criterio del modelo no tenía.

Fuera de alcance, con motivo: hándicap asiático (la línea temprana y la de
cierre cambian a menudo). Al revisar su liquidación salió un bug aparte en
`clv._settle_outcome`: en líneas de cuarto trata la media apuesta devuelta
como si pagara a cuota, así que medio-ganada y medio-perdida solo se liquidan
bien a cuota 2,00. Anotado como tarea aparte.

## 2026-09-23 — La puerta comercial decide por valor esperado al cierre sin margen

Paso 1 del plan. `ev_close_pct = price × closing_prob_devig − 1` pasa a ser la
cifra de la puerta (`evaluate_clv_gate`) y de la puerta de sombra
(`evaluate_shadow_promotion`). `clv_pct` se conserva y se publica: quitarlo
rompería la comparabilidad con lo ya reportado, y enseñar las dos cifras
explica el sesgo al lector del track record.

Decisiones que no se ven en el diff:

- **`closing_prob_devig` cambió de definición, no solo de uso.** Antes
  `_closing_prices` tomaba por cada selección la cuota sharp si existía y si no
  otra casa, así que el de-vig podía mezclar precios de dos casas. Ahora sale
  de UN snapshot de cierre de Pinnacle (`window_tag='close'`, mismo
  `captured_at`) con el grupo completo. Si no lo hay, no se mide: una apuesta
  sin cierre justo no puede demostrar valor. Se eligió exigir `close` y no "el
  último precio antes del kickoff" porque, si falló la ventana de cierre, el
  último precio puede ser de días antes y ya no es un cierre.
- **El hándicap se empareja con la línea opuesta.** The Odds API guarda local
  −0,5 y visitante +0,5; el filtro por línea igual del código anterior nunca
  encontraba la pareja, así que en hándicap `closing_prob_devig` salía siempre
  vacío sin avisar.
- **BTTS, doble oportunidad y totales por equipo no cuentan para la puerta.**
  El worker no captura esos mercados, así que no hay cierre sharp. Aparecen en
  `n_without_fair_close` para que se vea cuántos quedan fuera.
- El mensaje de rechazo pasó de "incluye cero" a "no está entero por encima de
  cero": con la vara nueva el caso típico es un intervalo entero NEGATIVO, y
  "incluye cero" habría sido falso.

Verificado contra cierres reales del histórico: tomar el propio cierre de
Pinnacle en un Inter–Lecce da −2,0% de valor esperado, que es su margen. 289
tests. `pick_results` y `shadow_results` estaban vacías: no hubo nada que
rellenar.

## 2026-09-23 — Publicación de picks pausada y The Odds API solo en `eu`

Decisión del usuario tras el piloto de abajo. `PUBLISH_PICKS_ENABLED=0` por
defecto: el job diario sigue prediciendo y sellando las predicciones, pero no
selecciona, guarda ni difunde picks. Se eligió un interruptor en vez de borrar
la selección porque la reanudación es una decisión explícita, no un
redespliegue, y porque el criterio nuevo aún no existe. Se sigue sellando
porque las predicciones del día deben quedar probadas aunque no haya picks; el
orden predecir → sellar no cambia. `/model-card` publica que está pausada.

Región de The Odds API: solo `eu` (Pinnacle y Betfair Exchange). Esto corrige
la entrada de más abajo del mismo día que la había subido a `eu,us`: con `us`
el vivo gastaba ~11.610 de 20.000 créditos y no quedaba margen para el
histórico, que cuesta 10× por llamada. Ahora ~5.800 en vivo y ~14.000 libres.

## 2026-09-23 — Piloto "casa blanda contra precio sharp": el criterio de mercado sí tiene valor, y la vara de CLV estaba torcida

Tres hallazgos, medidos con un script de scratchpad (no en el repo todavía):

1. **El CLV histórico SÍ era medible.** Los CSV del formato principal de
   football-data traen cuotas pre-cierre de 8 fuentes además del cierre, para
   1X2, O/U 2,5 y AH. `history_fd._ingest_rows` guarda solo la primera familia
   disponible (`break`) y tiraba el resto. README corregido.
2. **Seleccionar por distancia al precio sharp funciona donde el modelo
   falla.** 14.294 partidos, 7 ligas, 2019-2025. Precio justo temprano = Shin
   sobre Pinnacle pre-cierre; se apuesta si `cuota_blanda × p_justa − 1 ≥ 2%`.
   Valor esperado contra el cierre justo: máximo del mercado +3,05% (IC95
   [2,68, 3,39], n=4.684), 1xBet +2,78%, Bwin +1,37%, Bet365 +0,56% (IC95
   [−0,64, 1,81]), William Hill −0,37%. ROI realizado no concluyente (máximo
   +0,95%, IC95 [−5,1, +7,0]). Qué fracción del edge temprano sobrevive al
   cierre depende MUCHO de la casa (Max ~0,71, 1xBet ~0,68, Bet365 ~0,12): un
   encogimiento constante único está mal planteado. El "máximo del mercado" es
   una cota optimista: mezcla casas a las que un suscriptor quizá no accede.
3. **`clv_pct` está sesgado al alza por el margen.** Se calcula contra el
   cierre de Pinnacle CON margen (`price / close − 1`). Apostar a Pinnacle
   temprano en todo, sin criterio, da `clv_pct` −0,32% pero valor esperado
   contra el cierre justo −3,90%. La puerta comercial (`evaluate_clv_gate`)
   lee `clv_pct`: podía autorizar una estrategia con EV ≈ −3%. La cantidad
   correcta es `price × closing_prob_devig − 1`, y `closing_prob_devig` ya se
   guarda en `pick_results`.

Además: la puerta de CLV solo se REPORTA en `/model-card`; `daily.py` no la
consulta y publica (y sella en la cadena, para siempre) con el criterio viejo
en cuanto el cron corra con cuotas reales.

## 2026-09-23 — The Odds API subida a plan de pago: el cron de `odds_worker` deja de ser manual

El usuario dio de alta una nueva `ODDS_API_KEY` de pago, 20.000 créditos/mes
(reinicia el día 1 a las 00:00 UTC), reemplazando la del plan de 500 créditos
que obligaba a correr `odds_worker` a mano. Con el coste ya medido el
2026-09-22 sobre el calendario real de las 13 competiciones
(`eu,us x h2h,totals,spreads` ≈ 1.935 llamadas/mes × 6 créditos = ~11.610
créditos/mes), el nuevo plan cabe con 1,7x de margen — antes ni la opción más
barata cabía en 500. `.env` ya no restringe a `eu x h2h`: pasa a
`ODDS_API_REGIONS=eu,us` / `ODDS_API_MARKETS=h2h,totals,spreads`, la
configuración completa que ya asumía el cálculo de coste. `scripts/crontab`
ya traía la línea de `odds_worker` cada 10 min sin comentar, así que no hizo
falta tocar el cron en sí — el bloqueo era solo de crédito/clave.

**Lo que sigue sin verificar:** no hay Docker en este entorno, así que no se
confirmó el despliegue real del contenedor con cron activo, ni que el
consumo de crédito en producción coincida con lo estimado sobre el
calendario anunciado (los reprogramados y los mercados que de verdad devuelve
cada casa pueden variar el coste real).

## 2026-09-23 — Un solo FastAPI para web demo, API y control interno

La decisión posterior del usuario sustituyó el BFF como segundo servicio:
el mismo FastAPI sirve el prototipo en `/` y un panel de lectura en
`/control`. Se conserva el aislamiento de permisos: `/v1` y `/admin`
mantienen sus tokens de servidor, `/control` exige credenciales humanas
separadas y Caddy limita `/admin` y `/control` a la IP operativa. El
JavaScript solo contiene datos ficticios. No se activaron cuentas de cliente,
pagos ni picks premium reales porque la puerta de CLV sigue pendiente.
Pruebas de regresión: 278 pasan; el frontend valida sintaxis. El arnés no
pudo ejecutar Python ni Docker desde Git Bash en este entorno, por lo que
se ejecutó pytest explícitamente con `.venv` y no se validó Caddy en un
contenedor.

## 2026-09-22 — Prototipo visual antes de la web comercial

El usuario pidió ver un prototipo completo en modo demo y eligió expresamente
la distribución y los menús de Pitchverse como referencia visual. Se creó
`frontend/` con seis vistas navegables y datos ficticios, sin integrar la API:
el objetivo es validar el diseño sin aparentar que ya hay picks rentables o
una suscripción activa. La aplicación comercial sigue pospuesta hasta reunir
CLV real y superar la puerta de la fase 2. El futuro navegador hablará con un
backend web propio; el `SERVICE_TOKEN` de FastAPI nunca se pondrá en JS.

## 2026-09-21 — Arnés inicial creado

- El proyecto tenía dos versiones del `README.md`: una suelta en la raíz
  (más antigua, sin mención de Grafana ni de los tres niveles de auth de la
  API) y otra empaquetada dentro de `pyton/quantfut.tar.gz` (menciona
  `db/004_grafana_readonly.sql`, `grafana/`, y coincide exactamente con los
  archivos reales que trae el propio tar.gz). Se conservó la versión del
  tar.gz porque es la que describe el código que realmente existe. Si esto
  fue un error, la versión anterior no quedó guardada aparte — revisar con
  el usuario si hace falta.
- `pyton/` contenía archivos `.py`/`.sql`/`.sh` sueltos que resultaron ser
  copias idénticas (diff sin diferencias) de los mismos archivos dentro del
  `quantfut.tar.gz`. El tar.gz es el repo completo (incluye `db/`, `src/qf/`
  completo, `docker-compose.yml`, `Dockerfile`, `requirements.txt`,
  `grafana/`); se extrajo a la raíz del proyecto para que la estructura
  coincida con la que documenta README.md.
- El tar.gz traía dos directorios basura con nombres literales
  `{db,src` y `{db,src/qf/{ingest,model,publish,eval,api},scripts}` —
  artefacto de un `mkdir -p {a,b}` corrido sin expansión de llaves al crear
  el archivo. Estaban vacíos, se eliminaron.
- No se inicializó git ni se borró `pyton/` — no había repo git en el
  directorio, así que borrar sin poder revertir era riesgo innecesario. Se
  dejó como nota en `harness/tareas.md` para que el usuario lo confirme.
- No existe todavía suite de tests (`pytest` u otro). `scripts/harness_check.sh`
  por ahora solo valida sintaxis Python (`py_compile`) y `docker compose
  config`; si se agrega una suite de tests, añadir esa verificación aquí.

## 2026-09-21 — Alcance: sin Telegram, foco en la API para la web

El usuario confirmó que no usa Telegram — la venta de picks es solo en su
propia web, consumiendo esta API. Decisiones tomadas en esta sesión:

- **El reparto free/paid ya no lo decide Telegram.** Encontré que
  `daily.py` llamaba `pk.persist(selected, tier="paid")` con un tier fijo
  para TODO el lote, y era `telegram.publish_batch()` quien in-place decidía
  qué picks eran "gratis" (los primeros `free_count=2` por edge) solo para
  el mensaje de Telegram — nunca se reflejaba en la BD. Consecuencia real:
  `/picks/free` y la vista gratuita de `/v1/picks` devolvían siempre una
  lista vacía, porque en la tabla `picks` todo quedaba con `tier='paid'`.
  Solución: `picks.assign_tiers()` (nuevo, en `src/qf/publish/picks.py`)
  decide el tier antes de persistir, usando `settings.free_picks_per_day`
  (nuevo en `config.py`, default 2, env `FREE_PICKS_PER_DAY`). `daily.py`
  pasa ese mismo reparto a Telegram en vez de dejar que Telegram lo calcule
  de nuevo. Telegram sigue siendo 100% opcional (no-op si no hay
  `TG_BOT_TOKEN`), pero ya no es la fuente de verdad de nada.
- **Gap de modelo encontrado leyendo `model/train.py`, no está en el
  README:** `train_and_register()` llama `load_training_data()` sin
  `league_id`, así que el Dixon-Coles se ajusta con las 7 ligas mezcladas en
  un solo fit — una sola ventaja de local y una sola escala de fuerza
  ataque/defensa para Premier League, Liga MX, Brasileirão, etc. La función
  ya soporta filtrar por `league_id`; no se usa. No lo toqué todavía (el
  usuario pidió enfocarse en la API primero) — queda en
  `harness/tareas.md` como pendiente de mayor impacto que la calibración,
  porque calibrar un modelo mal especificado por liga no corrige el sesgo
  de fondo.
- **Endpoints añadidos a `src/qf/api/main.py`:** `GET /leagues`,
  `GET /teams` (filtrable por `league`), `GET /matches/{match_id}` público
  (ficha de partido con predicción recortada a tier gratuito — pensado para
  páginas de partido indexables sin login). Antes no existía forma de que
  el frontend listara ligas/equipos sin pegarle directo a Postgres.
- **Paginación** (`limit`/`offset`) añadida a `/picks/free` y `/v1/picks`;
  antes devolvían todo el resultado sin límite.
- **Pendiente explícito, no urgente ahora:** auth de suscriptor sin
  Telegram (email/magic-link o vía checkout de pago) y el webhook de
  cobros. El usuario dijo textualmente que eso es "después".

## 2026-09-21 — Corrección de las brechas técnicas del modelo

Decisiones de diseño que no son obvias leyendo el código:

- **Por qué la calibración actúa sobre las lambdas y no sobre el 1X2.** Los
  ~150 mercados salen todos de la misma matriz de marcadores. Calibrar el
  1X2 directamente (isotónica, que es lo estándar) dejaría el over/under y
  el hándicap saliendo de una matriz sin corregir, y el producto publicaría
  un 1X2 que no cuadra con su propio total de goles. La corrección afín en
  log-espacio sobre (lambda, mu) recalcula toda la matriz y mantiene la
  coherencia. Se pierde algo de flexibilidad frente a la isotónica; se gana
  que el producto no se contradiga a sí mismo.
- **Por qué NO se usó PyMC/numpyro para el modelo jerárquico.** El pooling
  parcial está implementado como penalización en la verosimilitud, que es el
  estimador MAP del mismo modelo jerárquico. Da el encogimiento (que es lo
  que se quería) sin añadir una dependencia pesada ni muestreo NUTS, que el
  propio README dice que es lo único que justificaría GPU. Si algún día se
  quieren intervalos de credibilidad por equipo, ahí sí hace falta la
  versión bayesiana completa.
- **Por qué el riesgo de portafolio usa la probabilidad del MERCADO.** Medir
  la varianza con la probabilidad del propio modelo la subestima justo
  cuando el modelo está sobreconfiado, que es el caso por defecto y la razón
  de existir del shrinkage. Ver `picks._risk_prob`.
- **Por qué las correlaciones son constantes y no estimadas.** Con unos
  cientos de picks liquidados, estimar una matriz de correlación daría
  ruido. Son cotas superiores razonadas; equivocarse por prudencia solo
  cuesta tamaño de apuesta. El número que NO puede ser cero es `CORR_BASE`:
  todos los picks salen del mismo modelo, y ese riesgo común no se
  diversifica repartiendo entre ligas.
- **Por qué el modelo de residuo está desactivado por defecto.** Corrige
  solo el 1X2, así que mientras esté activo ese mercado deja de ser
  coherente con el resto del paquete. Es una decisión de producto, no
  técnica, y por eso la toma `RESIDUAL_ENABLED` y no el código. Se entrena
  siempre igualmente, para poder medir cuánto se está dejando sobre la mesa.
- **Bug encontrado de paso:** `train.py` versiona por fecha
  ("2026.09.21") pero `daily.py` cargaba `dc_{MODEL_VERSION}.pkl` desde una
  variable de entorno fija. El primer reentrenamiento habría dejado el job
  diario cargando un artefacto viejo o ninguno, sin avisar. Ahora el modelo
  activo se resuelve desde `model_artifacts`, que es la única fuente de
  verdad de qué está desplegado.

## 2026-09-21 — Ponderación modelo/mercado + bug crítico de unidades

- **`model/meta.py`**: estima `w_model` minimizando log-loss fuera de muestra
  sobre `blend_logit()` (que ya existía sin que nadie calculara su peso).
  Detalle: `blend_logit` es en realidad un *log-opinion pool* (media
  geométrica de probabilidades renormalizada), no una mezcla en logit pese al
  nombre. La matemática es la estándar y correcta para multiclase, así que se
  reutilizó tal cual en vez de duplicarla.
- **Pesos por liga** encogidos hacia el global con pseudo-conteo
  (`LEAGUE_SHRINK_K=600`), misma filosofía de pooling que el modelo. Una liga
  con menos de 250 partidos no recibe peso propio.
- **Por qué la mezcla viene DESACTIVADA.** Acerca las probabilidades al
  mercado y por tanto REDUCE el edge: con w bajo, muchos picks dejan de
  superar el umbral. Es correcto, pero cambia cuántos picks se publican al
  día, y esa es una decisión de negocio. El peso se estima y se publica en
  `/model-card` aunque esté apagada.
- **Riesgo sutil que obligó a restringir mercados.** Solo se mezclan 1X2 y
  totales (el AH tiene empuje en líneas enteras y necesita trato aparte). Si
  se mezclara solo eso y la selección siguiera mirando todos los mercados,
  los NO mezclados conservarían el edge inflado y el sistema se desplazaría
  solo hacia ellos: apostaría justo donde menos ha validado. Por eso
  `find_candidates` respeta `eligible_markets` cuando la mezcla está activa.
  Cubierto por `tests/test_eligible_markets.py`.
- **Exclusión mutua con el modelo de residuo**: ambos fusionan con el
  mercado (el residuo usa `logit_gap` modelo-mercado como feature).
  Aplicarlos juntos contaría la información del mercado dos veces. `daily.py`
  avisa y desactiva el residuo.
- **BUG CRÍTICO PREEXISTENTE ENCONTRADO: unidades del stake.** `kelly()`
  devolvía una fracción de banca (0.0067 = 0.67%) pero el resto del sistema
  interpretaba ese número como unidades, donde 1 unidad = 1% de banca (es la
  única lectura coherente: `MAX_STAKE_UNITS=2.0` sería si no un tope del 200%
  de la banca por apuesta, y la exposición diaria de 10.0 sería del 1000%).
  Consecuencia real: el descarte `stake <= 0.05` de `find_candidates`
  eliminaba TODOS los picks con edge realista (3-10%) — comprobado a cuotas
  1.8/2.5/3.5 — así que el sistema habría publicado CERO picks
  indefinidamente sin dar ningún error, y lo natural habría sido culpar al
  modelo. Corregido con la conversión ×100 y el contrato fijado en
  `tests/test_kelly_units.py` para que no pueda volver a romperse en
  silencio.

## 2026-09-22 — Postgres local y verificación end-to-end

PostgreSQL 16.15 instalado nativamente (winget, servicio `postgresql-x64-16`,
puerto 5432). Base `quantfut`, rol `qf`. El `.env` local apunta ahí. El
esquema completo (`db/001..004`) se aplicó por primera vez: 17 tablas, 6
vistas, 5 triggers, 7 ligas. `db/004_grafana_readonly.sql` necesita
superusuario (crea un rol), en producción eso lo cubre
`docker-entrypoint-initdb.d`.

**Garantías de BD verificadas ejecutándolas de verdad:** UPDATE y DELETE
rechazados en `predictions`, `picks` y `odds_snapshots`; `features_pit`
rechaza `as_of > kickoff`. Funcionan tal como documenta el README.

**El modelo por liga funciona con datos que pasaron por la base.** Se
sembraron dos ligas con ventaja de local deliberadamente distinta y el
entrenamiento real las recuperó por separado:

| liga | ha sembrada | ha recuperada | base sembrada | base recuperada |
|---|---|---|---|---|
| mx.liga_mx | 0.42 | 0.4021 | 0.22 | 0.2211 |
| gb.premier_league | 0.18 | 0.2147 | 0.12 | 0.1019 |

`beats_market: false` — la evaluación no se autoengaña. La calibración y el
modelo de residuo fueron correctamente DESCARTADOS por sus puertas
(calibración no mejoraba; residuo sin datos suficientes).

### Cuatro bugs preexistentes que solo aparecen con Postgres real

1. **`IndeterminateDatatype` en el filtro opcional por liga.** El patrón
   `(%s IS NULL OR col = %s)` no compila: Postgres no infiere el tipo de un
   parámetro suelto en una comparación IS NULL. Afectaba a
   `train.py::load_training_data` (fallo del 100% de los entrenamientos, en
   la primera llamada), a `/v1/fixtures` y a `clv.py::_closing_prices` (la
   ruta de liquidación). Corregido con casts `::text` / `::real`.
   OJO al corregirlo: psycopg cuenta los `%s` que aparezcan DENTRO de los
   comentarios SQL como marcadores; un comentario explicativo con `%s` rompe
   la consulta.
2. **`pd.Timestamp(start_date, tz="UTC")` con fecha ya consciente de zona.**
   `train.py` pasa `df["kickoff_utc"].max() - timedelta(...)`, que siempre
   trae zona. Reventaba todo walk-forward. Ahora se normaliza.
3. **Fecha del lote en UTC vs cast en zona del servidor.** `hashchain._collect`
   comparaba `generated_at::date` (que castea en la zona del SERVIDOR) contra
   un `batch_date` calculado en Python con UTC. Con el servidor en
   America/Mexico_City las fechas discrepaban, el lote salía vacío, no se
   sellaba y —por diseño— NO SE PUBLICABA NADA. Fallo mudo. Corregido con
   `(generated_at AT TIME ZONE 'UTC')::date`. En Docker suele pasar
   desapercibido porque los contenedores van en UTC.
4. (Ya registrado arriba) unidades del stake en `kelly()`.

**Verificado end-to-end:** `qf.model.train` completo, `qf.publish.daily`
(predice, sella, publica), `hashchain verify` OK, y todas las rutas de la API
contra datos reales, incluidas `/leagues`, `/teams`, `/matches/{id}` y el
`/model-card` con parámetros por liga y peso modelo/mercado.

**Lo que sigue sin verificarse:** los datos son SINTÉTICOS (goles Poisson
desde fuerzas conocidas, cuotas derivadas de la probabilidad verdadera más
margen). Sirven para verificar el CÓDIGO, no para evaluar el modelo. El
`w_model=0.43` que sale es alto justo porque el modelo coincide con el
proceso que generó los datos; con datos reales se espera bastante más bajo.
Tampoco se ha probado `ingest/lineups.py` contra la API real de API-Football.

## 2026-09-22 — Histórico real cargado + backfill de ligas LatAm roto

Cargados **31.041 partidos reales** de football-data.co.uk (gratis, sin
claves), 7 ligas, 2014-2026, con **96.7% de cobertura de cuotas de cierre de
Pinnacle**. Es material suficiente para cerrar la Fase 2 (validar si el modelo
tiene edge) sin pagar ninguna API.

### Quinto bug preexistente: las 3 ligas LatAm nunca cargaban nada

`history_fd.py` trataba el formato "extra" (Liga MX, Argentina, Brasil) como
si fuera el principal. Dos fallos superpuestos, ambos mudos:

1. **Nombres de columna distintos.** El extra usa `Home`/`Away`/`HG`/`AG`; el
   código leía `HomeTeam`/`AwayTeam`/`FTHG`/`FTAG`. Cada fila salía None y se
   descartaba en el primer `isinstance`.
2. **Filtro de temporada que no casa nunca.** Buscaba `'2526'` como subcadena
   de la columna Season, que vale `'2025/2026'`.

Efecto comprobado ejecutando el código viejo: `{"mx.liga_mx": 0,
"br.serie_a": 0, "ar.primera": 0}` frente a 4.560 por liga europea. Tres de
siete ligas —toda la parte latinoamericana, que es donde el README sitúa la
ventaja competitiva por haber menos apostante sharp— se quedaban vacías sin
un solo error.

Además, **no hay un único formato de temporada dentro del formato extra**:
las ligas de año natural (Brasil siempre; Argentina desde que cambió) la
escriben `'2025'` a secas, y ARG.csv contiene LAS DOS formas en el mismo
fichero. Aceptar solo la forma con barra dejaba Brasil a cero y Argentina a
un tercio (1.428 de 5.217). `season_labels_extra()` devuelve ahora ambas.

`ingest_extra()` descarga el fichero UNA vez y recorre todas las temporadas,
en vez de una sola (el extra trae todo el histórico en un CSV).

## 2026-09-22 — Kalman, cara a cara real, y xG por fin disponible

### El número que importa: ninguno de los dos modelos bate al mercado

Sobre 31.041 partidos reales, ventana de validación de 365 días:

| | RPS | log-loss | tiempo |
|---|---|---|---|
| Mercado (Pinnacle des-margenado) | **0.19994** | — | — |
| Dixon-Coles con decaimiento | 0.20359 | 1.01135 | 4.888 s |
| Ratings dinámicos (Kalman) | 0.20388 | 1.00795 | **51 s** |

Los dos modelos están empatados entre sí (0.0003 de diferencia con n=1.324 es
ruido). El hueco contra el mercado, 0.0037, es diez veces mayor y sí es real.
Es el resultado esperado y honesto: el mercado sabe más.

Kalman es **96 veces más rápido**, y eso cambia qué se puede hacer: ajustar
hiperparámetros pasa de ser una expedición mensual a algo rutinario. El
barrido ya encontró `process_var=1e-4` mejor que el 2.5e-4 por defecto.

Sanidad del ranking que produce: Inter, Barcelona, Flamengo, PSV, Arsenal,
Man City, Roma, Palmeiras, Real Madrid. Aprende fútbol real.

### `model/kalman.py`

Ratings de ataque/defensa como estado latente con paseo aleatorio. Tres cosas
que el decaimiento exponencial no puede expresar: la incertidumbre crece con
el tiempo parado (un parón de 3 meses no es igual que uno de 3 días), los
ascendidos convergen rápido, y un cambio brusco de fuerza se captura en vez de
promediarse con la época anterior.

Aproximación declarada: covarianza DIAGONAL. La completa capturaría la
correlación entre rivales pero cuesta O(n²) y aporta poco con equipos que
juegan decenas de partidos.

`predict_sequential()` predice antes de aprender cada partido: es fuera de
muestra por construcción, en una sola pasada. No hay forma de colar futuro ni
olvidándose de un filtro.

### FBref está bloqueado; worldfootballR_data no

FBref devuelve 403 con desafío de Cloudflare. `soccerdata` llega a descargar
un driver de Chrome para evadirlo y falla igual tras 400 s. Como fuente
operativa no sirve. (De paso: `xg_fbref.py` pasaba la caché como `str` y
soccerdata exige `Path`; corregido, aunque el módulo siga sin poder scrapear.)

`ingest/xg_worldfootball.py` (nuevo) descarga los mismos datos de FBref ya
raspados desde los releases de `JaseZiv/worldfootballR_data`, por HTTPS
normal, en segundos.

**La cobertura de xG pasó de 0 a 9.458 partidos**, y eso incluye 967 de Liga
MX y 1.322 de Brasileirão. **Esto contradice el README**, que da por perdido
el xG de esas ligas ("no tienen xG en las fuentes gratuitas... está en el
model-card a propósito, no es un error a arreglar"). Sí lo tienen por esta
vía. Hay que actualizar el README y el model-card.

Aclaraciones sobre el formato, porque la petición original hablaba de Parquet:
no hay Parquet en ese repositorio, solo `.rds` y `.csv`. Argentina solo está
en `.rds`, que exigiría `pyreadr`; no se añadió esa dependencia por una liga.
Los datasets se publican por lotes, así que van por detrás del presente:
sirven para entrenar, no para cerrar el xG de anoche.

### El emparejamiento de nombres es el cuello de botella, y no se automatiza

Parte de la cobertura que falta no es por ausencia de datos sino porque los
nombres de FBref no casan con los de football-data. Y el umbral NO se puede
bajar: con score ~72, `Newcastle Utd` empareja con `manchester united` y
`Leeds United` con `sheffield united`. Fusionarlos arruinaría dos equipos a la
vez en silencio. A la vez, aciertos como `Leicester City`→`leicester` (78.3) o
`Flamengo`→`flamengo rj` (84.2) quedan por debajo. No hay número que separe
los dos grupos: hace falta criterio humano. El paso 4 del README existe por
esto y está funcionando como debe al negarse.

## 2026-09-22 — Ajuste por estado del partido: NEGATIVO, y el motivo importa

`ingest/game_state.py` + 22 tests. Reconstruye el marcador minuto a minuto
desde los remates que acabaron en gol y reparte el xG de cada equipo entre
ganando / empatando / perdiendo.

**Los ratios empíricos contradicen la premisa del método** (12.928 partidos):

    perdiendo 1.135 · empatado 1.000 · ganando 1.177

Se esperaba que el equipo que gana se repliegue y produzca MENOS. Produce un
17.7% MÁS. La causa es un confundidor: ir ganando está correlacionado con ser
mejor equipo, así que el estado "ganando" no mide repliegue, mide calidad.
Normalizar por ese ratio **elimina la señal de fuerza** que el modelo busca.

Resultado medido: RPS 0.20330 → 0.20344 (todos), y 0.20075 → 0.20108
restringiendo a los partidos con ajuste. Empeora en ambas comparaciones. NO
volver a proponerlo sin estratificar por calidad de equipo.

**Validación que salvó el módulo de ser basura silenciosa:** el marcador se
deriva de los goles que fueron remate, y un AUTOGOL no lo es. Contrastado
partido a partido contra la BD en Liga MX: 1.651 cuadran, 139 no (7.8%), y en
todos los casos la BD tenía exactamente un gol más. `match_state_data()`
devuelve `None` cuando no cuadra. Sin esa comprobación, 1 de cada 13 partidos
habría tenido un estado inventado sin dar ningún error.

El módulo se conserva: la reconstrucción sirve como FEATURE del modelo de
residuo (uso distinto de corregir el objetivo) y la validación contra
autogoles es infraestructura reutilizable.

## 2026-09-22 — Exprimido el fichero de tiros: resultado en parte negativo

`db/006_shot_stats.sql` + `match_stats()` en `ingest/xg_worldfootball.py`.
Del mismo CSV tiro a tiro que ya se descargaba para el xG se extraen ahora
remates, remates a puerta, PSxG y distancia media.

**Lo que aportó:** Liga MX y Brasileirão pasaron de CERO datos de remates a
tenerlos (1.790 y 1.905 partidos). El formato "extra" de football-data.co.uk
no trae tiros ni córners, así que esas columnas llevaban vacías desde el
principio en las tres ligas latinoamericanas.

**Lo que NO aportó, medido sobre n=28.718:** el PSxG como objetivo del modelo
de fuerza EMPEORA el RPS (0.20368 frente a 0.20330 del xG actual); la media de
ambos también (0.20340). El xG que ya se usaba es el mejor de los tres. No
volver a proponer PSxG como objetivo sin una razón nueva: solo cubre remates a
puerta, así que como medida de creación de ocasiones está sesgado, y mezcla la
colocación del disparo, que es más ruidosa que la calidad de la ocasión.

**Error propio corregido en el camino:** el comentario original de la
migración afirmaba que `PSxG - xG` mide la calidad de definición. Es falso:
`psxg` suma solo remates a puerta y `xg` suma todos, así que son poblaciones
distintas y la resta sale negativa en las seis ligas (-0.006 a -0.084) sin
decir nada de los delanteros. `goles - PSxG` sí es válido (rendimiento del
portero rival) porque ambas magnitudes hablan de la misma población. El
comentario del SQL ya lo explica.

## 2026-09-22 — MEDICIÓN DEFINITIVA: el modelo no tiene edge

Con xG ya cargado y sobre **n=28.128** predicciones fuera de muestra
(veintiuna veces la medición anterior, que además corrió con cobertura de xG
a 0% y por tanto con el modelo a media potencia):

- **Pierde contra el mercado en las 7 ligas.** Delta de −0.00485 (Liga MX, el
  hueco menor) a −0.00790 (Serie A). Total −0.00653.
- **w_model = 0.0001.** El peso óptimo del modelo en la mezcla con el mercado
  es cero. El mercado ya contiene todo lo que el modelo sabe.

Hipótesis descartadas POR MEDICIÓN, no por intuición. No volver a proponerlas
sin datos nuevos:

1. "Gana en ligas latinoamericanas porque son mercados blandos" → falso, Liga
   MX tiene el hueco más pequeño pero negativo.
2. "Faltan hiperparámetros ajustados" → el barrido de `process_var` mueve la
   cuarta decimal (mejor: 2.0e-4).
3. "Falta el xG" → ayuda (0.20424 → 0.20336) pero cierra el 12% del hueco.
4. "Es cuestión de técnica" → dos motores independientes (Dixon-Coles con
   decaimiento y filtrado bayesiano) aterrizan en el mismo sitio.

**Diagnóstico: falta INFORMACIÓN, no técnica.** El modelo sabe goles y xG; el
mercado sabe además lesiones, alineaciones, rotación, motivación y clima. Más
matemática sobre los mismos datos no fabrica información.

**Límite estructural de lo medible:** todo esto compara contra el CIERRE. Un
modelo peor que el cierre aún podría ser rentable contra casas blandas antes
de que converjan —eso es el CLV—, pero el histórico de football-data solo trae
cuotas de cierre. Con un precio por partido el CLV es inmedible. Responderlo
exige `odds_worker` capturando a lo largo del tiempo. Es la justificación
empírica de por qué ese worker es el paso 0.

**Implicación de negocio:** la puerta de la fase 2 NO se cumple. Según la
propia filosofía del README, la fase 3 (vender) no arranca hasta que se
cumpla.

## 2026-09-22 — Alias curados y documentación al día

`db/005_fbref_aliases.sql`: 35 alias de FBref revisados uno a uno. La
cobertura de xG subió de 9.458 a **14.141 partidos** y quedaron **cero**
nombres sin emparejar. Lo que falta ya no es resoluble: FBref no publica xG
antes de ~2017-18 y el histórico arranca en 2014.

**No intentes automatizar esto bajando el umbral.** Está demostrado en el
propio archivo SQL: con score ~72 el matcher propone `Newcastle Utd` →
`manchester united`, `Leeds United` → `sheffield united` y `Ath Paranaense` →
`parana`, que son tres clubes distintos en cada caso. Y por encima de ese
score hay aciertos legítimos que se perderían. No existe umbral que separe
ambos grupos.

Los alias se aplican DESPUÉS del backfill (necesitan que los equipos existan);
`setup_fase1.sh` tiene ahora un paso 4b para eso, y el SQL avisa por
`RAISE WARNING` si algún equipo canónico no existe todavía.

### Documentación actualizada (instrucción permanente del usuario)

El usuario pidió que README y model-card se actualicen con cada hallazgo, sin
esperar a que lo pida. Guardado en memoria. En esta tanda:

- README: corregida la afirmación falsa sobre el xG de Liga MX y Brasileirão,
  con la tabla de cobertura real medida; añadida la medición RPS contra el
  mercado; actualizados mapa de fases, estructura, calendario de procesos y
  tabla de fuentes; documentado el bloqueo de Cloudflare en FBref.
- `model_card`: quitada la limitación falsa sobre el xG latinoamericano y
  **añadida la de que el modelo no bate al cierre de Pinnacle**. Publicar eso
  es coherente con la tesis del producto: ocultarlo es lo que hace increíble
  al sector.
- `crontab` y `/admin/run/xg`: apuntan a `xg_worldfootball`, no al scraper
  bloqueado.

**Nota histórica (previo a Postgres):** no había Postgres ni datos reales en este
entorno. Los 48 tests corren sobre datos simulados y verifican la matemática
(recuperación de parámetros, ausencia de fugas point-in-time, coherencia
entre el 1X2 vectorizado del calibrador y el de `pricing.py`). Nada se ha
ejecutado contra el histórico real ni contra la API de alineaciones. La
lista de comprobaciones con datos reales está en `harness/tareas.md`.

---

## 2026-09-22 — MLS, Champions y Europa League: competición deja de ser liga

De 7 ligas a **8 ligas + 2 copas**, 31.041 → 37.650 partidos.

### La decisión de diseño que condicionaba todo lo demás

Hasta aquí "liga" y "competición" eran lo mismo, y todo el sistema se apoyaba
en ese supuesto sin decirlo. Meter la Champions lo rompe.

La salida fácil habría sido dar de alta equipos bajo `league_id='eu.ucl'`.
Habría funcionado, no habría dado ningún error, y habría sido destructiva: el
Real Madrid de Champions sería un club DISTINTO del de LaLiga, con 6-13
partidos por temporada, ningún rival en común y ataque/defensa prácticamente
en el prior. Más de cien clubes duplicados en el catálogo.

La separación es:

- `matches.league_id` → la **competición** del partido.
- `teams.league_id` → la liga **doméstica** del equipo.

El esquema ya lo permitía: no había ninguna restricción que obligara a que
coincidieran. `db/007_competiciones.sql` añade `cross_league` para marcar las
competiciones donde no coinciden, y todo lo demás se deriva de ahí.

Consecuencias que hubo que propagar a mano (y que son la parte que se olvida):

- Toda consulta que alimenta al modelo (`train.py`, `daily.py`) trae ahora
  `th.league_id AS home_league` y `ta.league_id AS away_league`.
- `lambdas()`, `knows()` y `predict()` aceptan las dos ligas, en Dixon-Coles y
  en Kalman. Sin los parámetros se comportan como antes (la liga doméstica ES
  la competición), así que el histórico y los artefactos viejos siguen valiendo.
- `ingest/uefa_cups.py` NUNCA crea equipos: descarta el partido.
- `ingest/fixtures.py` en competiciones `cross_league` solo acepta coincidencia
  EXACTA. Buscando a la vez en todas las ligas, un difuso de 95 puntos puede poner
  un club europeo encima de uno latinoamericano de nombre parecido y contaminar
  dos historiales de golpe. Fijado por `tests/test_fixtures_cross_league.py`.

### El término `strength`: lo que las copas aportan de verdad

No es poder apostarlas. Es que son los ÚNICOS partidos entre equipos de ligas
distintas, y por tanto lo único que permite comparar ligas entre sí.

El modelo impone suma cero de ataque y defensa DENTRO de cada liga. Eso
significa que un ataque de 0,3 en Eredivisie y uno de 0,3 en LaLiga no están
en la misma escala, y dentro de los datos domésticos **no hay absolutamente
nada** que las conecte: el nivel de liga y `base[liga]` son intercambiables.

La formulación elegida añade un desplazamiento por liga con signo opuesto en
las dos intensidades:

```
log lam = base[comp] + ha[comp] + (atk[h] + str[lg_h]) - (dfn[a] + str[lg_a])
log mu  = base[comp]            + (atk[a] + str[lg_a]) - (dfn[h] + str[lg_h])
```

La propiedad que hace que esto sea seguro: **en un partido doméstico lg_h ==
lg_a y el término se cancela exactamente**. Por eso se pudo añadir sin volver
a validar las ocho ligas. `tests/test_cross_league.py` lo comprueba
recalculando la lambda a mano sin el término y exigiendo igualdad a 1e-9.

Verificado sobre simulación con dos ligas de nivel deliberadamente distinto:
con 400 cruces recupera 0,32 de una diferencia sembrada de 0,40. El
encogimiento (`POOL_STRENGTH = 300`) es deliberado y la muestra real es aún
más pequeña.

### El límite honesto: 406 cruces de 3.308

Solo sirven los partidos con los DOS equipos en el catálogo. El resto
involucra ligas que no tenemos:

| país | partidos perdidos |
|---|---|
| Alemania | 633 |
| Francia | 464 |
| Portugal | 380 |
| Bélgica | 264 |
| Rusia | 252 |

Dar de alta Bundesliga, Ligue 1 y Primeira multiplicaría por ~4 la muestra que
identifica `strength`, y las tres están gratis en football-data (`D1`, `F1`,
`P1`) y en FBref (`GER_M`, `FRA_M`, `POR_M`). Es la ampliación con mejor
relación coste/beneficio que queda pendiente. Anotada en `tareas.md`.

### Y las copas NO son apostables todavía

No existe histórico gratuito de cuotas de Champions ni de Europa League:
football-data.co.uk solo cubre ligas domésticas y el release de copas de
worldfootballR_data da resultado y xG pero ni un precio. Sin cierre no hay
baseline de mercado → no se pueden evaluar, ni calibrar, ni medir CLV. Entran
como datos de ENTRENAMIENTO. Que sean apostables depende de que `odds_worker`
acumule cierres propios.

### Hallazgo lateral: Argentina SÍ tiene xG (0% → 62,5%)

`xg_worldfootball.py` decía, con razón, que Argentina solo existe en `.rds` y
que no compensaba añadir `pyreadr` por una sola liga. **Esa decisión estaba
bien tomada y aun así había caducado**: las copas europeas tampoco tienen CSV,
así que `pyreadr` era obligatoria de todos modos. Con la dependencia ya dentro,
Argentina entró gratis: 2.304 partidos con xG en una pasada.

La lección es general y vale la pena tenerla presente: **una decisión de "no
compensa" depende del coste de la alternativa, y caduca cuando ese coste
cambia.** Cuando se amplía el alcance, toca re-revisar las decisiones negativas
escritas en los módulos, no solo añadir código nuevo.

Lo que Argentina sigue sin tener es el fichero tiro a tiro: solo el xG
agregado. Sin PSxG, sin distancia, sin estado del partido.

### Tres bugs encontrados de paso

1. **`harness_check.sh` daba "OK" sin correr un solo test.** Elegía `python3`,
   que en Windows resuelve al stub de la Microsoft Store: arranca, responde a
   `--version`, y no tiene ninguna dependencia. El script imprimía
   "(pytest no instalado)" y seguía adelante con código de salida 0. Ahora
   prefiere `.venv` y **falla** si no encuentra pytest. Un chequeo que avisa y
   sigue es peor que no tenerlo: da confianza falsa.

2. **`requirements.txt` no se podía instalar.** `soccerdata==1.8.7` entra en
   conflicto con `lxml==5.3.0` y `pip install -r` aborta con
   ResolutionImpossible. Solo lo usa `xg_fbref.py`, que el README ya da por
   inservible (Cloudflare). Comentado, con la decisión pendiente en `tareas.md`.

3. **El chequeo de salud del calendario iba a alertar todos los días.**
   `check_fixtures_horizon` exigía partidos en 10 días a TODAS las ligas
   activas. La MLS para el invierno y las copas tienen huecos de meses entre
   eliminatorias. Ahora solo avisa de competiciones en juego (con algún
   partido terminado en las últimas 3 semanas). Una alerta que salta a diario
   por algo normal se deja de leer, y con ella la del día que sí importa.

### Y uno mío, del mismo tipo que ya había cometido

`INSERT ... CASE WHEN %s IS NULL` en `uefa_cups.py` → `IndeterminateDatatype`.
Es el tercer encuentro con la misma trampa de psycopg (parámetro suelto sin
tipo inferible). Resuelto decidiendo el valor en Python en vez de en SQL.
También volvió a aparecer el `%` dentro de un comentario SQL: `db.execute()`
interpola aunque no pases parámetros, así que un "0%." en un comentario rompe
el fichero entero.

---

## 2026-09-22 — Bundesliga, Ligue 1 y Primeira: añadidas por los cruces, no por sí mismas

De 8 ligas + 2 copas a **11 ligas + 2 copas**, 37.650 → **50.079 partidos**.

La razón no es que sean ligas atractivas, que lo son. Es que eran las tres que
más partidos de copa estaban tirando a la basura. `uefa_cups.py` descarta todo
cruce en el que alguno de los dos equipos no esté en el catálogo, y el desglose
de descartes lo decía sin ambigüedad: Alemania 633, Francia 464, Portugal 380.

**Resultado: los cruces utilizables pasaron de 406 a 1.111 (×2,7).** Que es lo
único que identifica el término `strength`, es decir, lo único que permite
comparar la fuerza de una liga con la de otra.

Coste real: casi nulo. Las tres están en el formato PRINCIPAL de
football-data.co.uk, así que `ingest_season` las carga sin tocar una línea de
código; y las tres tienen fichero tiro a tiro en FBref (`GER_M`, `FRA_M`,
`POR_M`). Lo único a mano fueron 19 alias (`db/011_aliases_europa.sql`).

### Los tres alias que no se podían dejar al emparejador difuso

- **`Paris S-G`** se queda en 82 puntos contra `Paris SG` y no resuelve. Bajar
  el umbral para capturarlo lo pone a tiro de **`Paris FC`**, que es otro club
  de la misma ciudad y también está en el catálogo.
- **`Vitória`** a secas es Guimarães, no Setúbal. Comprobado por fechas:
  aparece de forma continua de 2018 a 2025, mientras FBref llama
  `Vitória Setúbal` al otro, que además dejó la Primeira en 2020.
- **`B-SAD`** es Belenenses SAD. Se mapea a `Belenenses` porque es lo que hace
  football-data: su histórico usa ese único nombre de 2014 a 2022 sin separar
  el club original de la escisión. Aquí se HEREDA esa decisión en vez de tomar
  una distinta, para que las dos fuentes sigan cuadrando. No es la decisión
  "correcta" en abstracto; es la que mantiene el join sano.

### Dónde parar

El siguiente escalón es mucho peor: Bélgica, Rusia, Ucrania, Turquía y Grecia
sumarían ~1.160 cruces, pero son **cinco** ligas para menos muestra de la que
dieron **tres**, varias fuera del formato principal de football-data, y con
clubes que rotan más en Europa. Rendimientos decrecientes claros. Anotado en
`tareas.md` como "solo si se quieren esas ligas por sí mismas".

### Lo que NO cambió, y conviene no olvidarlo

El modelo sigue sin batir al mercado. Remedido con el mismo protocolo Kalman:
el delta por liga se mueve como mucho en la cuarta cifra decimal y la MLS
aterriza en −0.00590, exactamente donde las demás.

**Ampliar el catálogo no crea ventaja.** Es la misma conclusión que para los
mercados derivados: más ligas son más partidos de la misma calidad de
predicción, no una fuente de edge nueva. Lo que estas tres ligas mejoran es un
parámetro concreto (`strength`), no el acierto.

---

## 2026-09-22 — Ideas futuras del FPL Decision Engine, sin integración directa

Se revisó `percivalmahwaya/fpl-decision-engine` como referencia externa. No se
integra: resuelve Fantasy Premier League a nivel de jugador, con SQLite,
Streamlit y un optimizador de plantillas, mientras QuantFut predice partidos y
precios contra mercado. Además, el repositorio externo no muestra una licencia
que autorice copiar código.

Se conservan tres ideas metodológicas para cuando exista suficiente histórico
de alineaciones y cuotas:

- **Alineaciones como información nueva, no como otro modelo sobre los mismos
  goles.** Estimar su efecto sobre `log(lambda_home)` y
  `log(lambda_away)` usando continuidad del XI, ausencias y eventualmente
  ratings por jugador.
- **Champion/challenger real.** El ajuste de alineaciones correrá en sombra y
  solo podrá promoverse si mejora RPS/log-loss secuencial y CLV previo al
  cierre en varias ligas. La infraestructura de artefactos y puertas ya
  existente se reutiliza; no se importa la implementación FPL.
- **Zona de abstención.** Medir mediante bootstrap o reentrenamientos cuánto
  varían probabilidades y edges. Un edge dentro de ese ruido no debe producir
  un pick. El umbral se estimará en unidades de QuantFut; no se copia el valor
  del sistema FPL y no sustituye al `edge_shrinkage`.

No se adoptan su modelo de puntos por jugador, MILP de plantilla, recolector
FPL, SQLite, GitHub Actions ni Streamlit como frontend comercial. Streamlit
solo seguiría siendo opcional como vista personal de solo lectura; Grafana ya
es el panel operativo oficial de QuantFut.

---

## 2026-09-22 — SciKick queda como referencia para el frontend posterior

Se revisó `Pa004/scikick` y se conserva como referencia para el frontend de la
Fase 3, no como trabajo inmediato. La razón es de orden de dependencias: primero
deben estabilizarse la API y los pendientes de las fases anteriores para no
construir la interfaz sobre contratos que todavía puedan cambiar.

Cuando llegue esa fase, se podrán adaptar su estructura React/TypeScript, las
páginas de partido, la navegación de mercados, los gráficos de calibración, el
tema claro/oscuro y la internacionalización. Se conservará el aviso de su
licencia MIT. No se adoptarán su backend, SQLite, sus modelos predictivos ni su
lógica de `value`; QuantFut seguirá siendo la fuente de datos, probabilidades,
selección de picks y control de acceso.

---

## 2026-09-22 — Orden Elo → mercado → XI en sombra

Se implementó el baseline Elo secuencial y un constructor único de features
point-in-time. Ambos retrasan dos horas el uso de resultados y tiros cuando no
hay timestamp de finalización: un partido iniciado 30 minutos antes no puede
filtrar su marcador a otro. Las regresiones y ablaciones siguen siendo
challengers de diagnóstico; las cuotas históricas de cierre no se tratan como
features desplegables a T-60.

La comparación de tres vías sobre 1.907 partidos comunes de julio de 2025 a
enero de 2026 dio RPS Dixon-Coles 0,20245, Elo 0,20533 y Pinnacle 0,19561.
La lección es mantener Elo como control útil, no promover complejidad por
ganarle a Elo. Las cuotas sharp locales terminan el 14 de enero de 2026;
para la evaluación actual están obsoletas. La puerta de promoción bloquea
mercado con más de 30 días de antigüedad.
El bootstrap semanal favoreció a Dixon-Coles frente a Elo por 0,00288 RPS
(IC 95 %: 0,00053–0,00506) y a Pinnacle frente a Dixon-Coles por 0,00684
(IC 95 %: 0,00350–0,01061). Las pequeñas mejoras de Elo o tiros sobre el
cierre en un único holdout no sustituyen una prueba con cuotas disponibles
en el momento operativo.

El XI solo se convierte en ajuste de lambdas si acumula histórico temporal
suficiente y supera su holdout. Para medir CLV real se añadió una captura
`post_xi` condicionada a ambos XI, anterior a `close`: sin esa separación, el
CLV sería cero por construcción. La migración de sombra se aplicó al Postgres
local sin tocar predicciones ni picks publicados. Faltan claves de API-Football
y The Odds API para obtener nuevas alineaciones y cuotas, así que no se ha
observado CLV real ni se ha promovido challenger alguno.
La carga de entrenamiento exige ahora `window_tag='close'` de forma explícita;
la vista heredada elegía simplemente el último snapshot y podría confundir la
nueva ventana `post_xi` con un cierre cuando faltase este último.

---

## 2026-09-22 — Claves reales conectadas: lo que la API enseña y los tests no

Se configuraron y verificaron las dos claves. Lo importante no es que
funcionen, sino los cuatro problemas que solo aparecen al llamar de verdad.

### El plan Free de API-Football no puede operar el sistema, y no por la cuota

Lo que descarta ese plan no son las 100 peticiones diarias: es que **solo da
acceso a las temporadas 2022–2024**. La temporada en curso responde
`Free plans do not have access to this season`. Sin temporada en curso,
`ingest/fixtures.py` no puede poblar `matches` con partidos `scheduled`; sin
esas filas, `_pending_windows` del odds_worker no encuentra nada que capturar,
`ingest/lineups.py` no tiene partidos en ventana y `post_xi` nunca se dispara.
La cadena entera de datos operativos cuelga de ahí. La clave Free sirve para
verificar IDs y formas de respuesta, que es justo lo que estaba pendiente.

### Tres bugs del cliente que solo se ven con una clave en la mano

1. **El ritmo de llamadas estaba fijado para otro plan.** `MIN_INTERVAL = 0.35`
   (~170 req/min) estaba pensado como "por debajo de todos los planes"; el Free
   son **10 req/min**. La cuarta llamada seguida ya devolvía 429. Ahora el
   intervalo se deriva de `API_FOOTBALL_RPM`, que es un dato del plan y no una
   constante del código.
2. **El 429 entraba en el reintento exponencial genérico**, que espera 2 s y
   vuelve a chocar contra el mismo límite por minuto. Ahora es `RateLimited` y
   espera al minuto siguiente.
3. **Los errores de PLAN se reintentaban cuatro veces.** Son permanentes por
   definición: la suscripción no va a cambiar entre reintentos. Cada uno
   consumía una petición de las 100 del día, así que el modo de fallo era
   quedarse sin cuota justo cuando algo estaba mal configurado. Ahora
   `PlanError` no es reintentable.

Los tres comparten la misma forma: el proveedor devuelve **HTTP 200** y mete el
problema en el cuerpo, así que sin distinguir clases de error todo acaba en el
mismo reintento ciego.

### Los IDs de competición estaban bien; el verificador no

Los 13 `api_football_id` y los 13 `odds_api_key` son correctos y están activos.
Pero `verify_league_ids()` daba FALLO en Champions y Europa League: comparaba
el país, y API-Football archiva las competiciones continentales bajo `World`
mientras el catálogo local dice `Europe`. Un verificador que da falsos
positivos es peor que no tenerlo, porque entrena a ignorarlo. Ahora, para las
`cross_league`, comprueba `type == "Cup"` y el nombre.

### La coincidencia exacta no era paranoia: era necesaria, y faltaba en un sitio

Ejecutado `_resolve` contra fixtures reales de Champions, se confirmó lo que
`CLAUDE.md` advertía, con números:

    'Paris Saint Germain'  -> mejor candidato difuso 'San Martin S.J.'  (61)
    'Atletico Madrid'      -> mejor candidato difuso 'Atletico MG'      (77)
    'Rangers'              -> mejor candidato difuso 'Angers'           (92)

El tercero **supera el umbral de auto-aceptación de 90**. Y `resolve_team`
graba como alias permanente todo difuso aceptado, así que no habría sido un
partido mal emparejado sino la fuente contaminada para siempre. `fixtures.py`
ya estaba protegido; **`odds_worker.py` no**: resolvía los eventos de copa con
`league_id=None`, es decir, difuso contra las 13 competiciones a la vez. Por
eso `resolve_team` pasa a exigir coincidencia exacta POR DEFECTO, y el difuso
queda detrás de `exact=False`. `tests/test_resolve_exacto.py` fija los tres
casos, incluido el que pasa el umbral.

### El coste de The Odds API era cinco veces el estimado, y por un motivo útil

Recalculado con datos reales (el endpoint `/events` cuesta 0 créditos, así que
se leyó el calendario anunciado de las 13 competiciones y se simuló
`_pending_windows` sobre él): **~1.935 llamadas/mes**, o sea ~11.610
créditos/mes con `eu,us × h2h,totals,spreads`. El README daba ~2.160 para 7
ligas.

El factor cinco no viene de tener casi el doble de competiciones. Viene de que
**el coste lo manda el número de huecos de 10 minutos distintos, no el de
partidos**: una llamada trae todos los partidos de esa competición que entren a
la vez en la misma ventana. LaLiga y la Serie A, con 20 partidos en 14 días,
cuestan más que la MLS con 33, porque la MLS concentra kickoffs. Las copas son
lo más barato que hay: juegan todas la misma tarde. La consecuencia práctica es
que **repartir los mismos partidos entre más competiciones encarece**, y que la
palanca barata para bajar el coste no es quitar ligas sino quitar ventanas.

El plan de $30 (20.000 créditos) sigue alcanzando, con 1,7× de margen en vez de
"de sobra". El de 500 no alcanza ni en la configuración más barata (1.935), así
que con esta clave el worker se ejecuta a mano, nunca desde el cron.

### Emparejamiento de nombres: 108 alias nuevos y dos trampas

El bootstrap con las dos fuentes auto-registró 362 alias y dejó 283 a mano; se
curaron 108. De los que quedan, la mayoría son irresolubles por diseño (Celtic,
Rangers, Galatasaray, Slavia Praha… juegan las copas pero sus ligas no están en
el catálogo). Dos propuestas del difuso eran falsas y habrían pasado una
revisión rápida: `Remo` → Grêmio (80) y `Atlético Huracán` → Atlético Tucumán
(81). Revisar esta lista por puntuación descendente es exactamente la forma de
tragárselas.

---

## 2026-09-22 — La demostración del motor encontró el fallo más caro del sistema

Se ajustó Dixon-Coles sobre los 48.372 partidos con objetivo (945 s) y se
recorrió la cadena completa contra cuotas REALES de la Premier: de-vig →
lambdas → ~150 mercados → edge → encogimiento → Kelly. El motor funciona: 20
partidos, 70 selecciones preciadas por partido desde dos lambdas, line shopping
entre 22 casas, 19 candidatos por encima de los umbrales.

Y los tres candidatos de mayor stake eran basura.

    Hull v Everton     away @ 2.18   modelo 0,9061  mercado 0,4659   2,00 u
    Fulham v Hull      home @ 1.74   modelo 0,9506  mercado 0,5785   2,00 u
    Ipswich v Fulham   away @ 2.70   modelo 0,5574  mercado 0,3781   2,00 u

### El mecanismo, que no es "datos viejos"

Hull vuelve a primera; no la jugaba desde 2017. Con media vida de 180 días, la
suma de pesos de sus partidos es **0,0000**: sus `attack` y `defence` no los
deciden sus datos, los deciden el ridge y la restricción de suma cero por liga.

Y no quedan en cero. Quedan en (−0,81, −0,79) mientras los 20 equipos activos
se sitúan entre +0,2 y +0,9, porque el centrado se calcula sobre los 35 equipos
del catálogo incluyendo 15 que ya no juegan: los ausentes son el contrapeso
negativo de los presentes. La distancia entre un equipo activo y uno de estos
es ~1,3 en ataque, o sea un factor e^1,3 ≈ 3,7 en lambda. De ahí λ = 4,046 /
0,371 en Fulham v Hull.

**Por qué esto no contamina el resto:** en `lambdas()` el término es
`(atk_h + s) − (dfn_a + s)`, así que un desplazamiento común se cancela entre
dos equipos activos. Solo NO se cancela en activo-contra-ausente. Es coherente
con que el RPS medido sobre partidos normales sea razonable.

### Las tres guardas existentes miraban el número equivocado

- `knows()` daba **True**: comprobaba pertenencia al índice, y Hull está.
- `_confidence()` daba **`high`**: cuenta partidos de TODA LA VIDA, y Hull tiene
  cientos. El modelo pesa con media vida de 180 días. Son dos magnitudes
  distintas y se estaba usando una para hablar de la otra.
- `EDGE_SHRINKAGE=0.55` dejaba el 97,53% en 53,64%, y `MAX_STAKE_UNITS=2.0`
  recortaba justo a lo que ya se apostaba.
- Y `both_teams_known` se guardaba en los metadatos sin que **nadie** lo usara
  para descartar.

Cada guarda parecía razonable por separado. Ninguna medía la cantidad correcta.

### Lo que distingue el caso peligroso del inofensivo

Un ascendido de verdad (sin historia) es **seguro**: no está en el índice y
`lambdas()` lo lleva a la media de su liga. El peligroso es el contrario, el
que SÍ está en el índice con muestra efectiva ~0, porque entonces no cae a la
media: carga un parámetro extremo del que el modelo está seguro.

La magnitud que los separa es la **muestra efectiva** —suma de pesos de
decaimiento— y no existía. Ahora se calcula en `fit()`, se guarda en `DCParams`
(con default, para que los artefactos anteriores sigan cargando y devuelvan
`inf`: sin el dato no se puede AFIRMAR que falte muestra), la expone
`effective_n()`, la exige `knows()` y la mira `_confidence()`.

Se eligió `low` en vez de descartar la predicción: se sigue guardando, sirviendo
y auditando, pero `run()` ya la excluye del universo de picks con el filtro que
tenía. No se tocó el orden predecir → sellar → publicar.

Reparto en el modelo entrenado: **95 de 362 equipos tienen muestra efectiva
menor que 1**; 130 por debajo de 5, que es el umbral por defecto
(`MIN_EFFECTIVE_MATCHES`). No es un caso raro: son los tres ascendidos de cada
liga, cada agosto.

### Por qué importa para la fase 2

Esto no da edge; evita pérdidas. Pero es la demostración empírica del punto 2.D
del plan: el sistema no tenía forma de distinguir "mi ventaja es real" de "mi
parámetro es ruido", y por construcción apostaba el máximo justo donde más
ruido había. La zona de abstención por bootstrap es la versión general de esta
misma guarda; esta es el caso particular que se podía cerrar hoy y con un
número exacto.

---

## 2026-09-22 — Plan Pro: la cadena operativa arranca, y dos alarmas eran mentira

Contratado el plan Pro de API-Football. Verificado contra `/status`: 300
req/min, 7.500/día, temporada en curso incluida. `API_FOOTBALL_RPM` pasa de 10
a 300 y el intervalo entre llamadas del cliente baja de 6 s a 0,2 s solo.

Lo que cambia no es la cuota, es el acceso a la temporada EN CURSO. Primera
ingesta real de calendario: **173 partidos programados en 12 competiciones**.
De ahí cuelgan las ventanas de cuotas, las alineaciones a T-60 y el CLV, que
era todo lo que estaba esperando. `results.py` cerró su primer partido y
encadenó la liquidación sin incidencias.

### Los nombres de la temporada en curso no se habían visto nunca

El catálogo venía de football-data.co.uk y FBref; API-Football escribe distinto.
17 equipos sin emparejar en la primera pasada, resueltos en
`db/013_aliases_api_football.sql` con dos tratamientos OPUESTOS y la distinción
importa:

- **Alias** (mismo club, otra grafía): API-Football conserva la forma societaria
  completa y football-data la recorta — `Hamburger SV`, `SC Paderborn 07`,
  `1. FC Köln`, `Estac Troyes`, `Hull City`. Todos caen entre 62 y 88, por
  debajo del umbral de 90.
- **Alta de equipo** (club que de verdad faltaba): `Remo`, `Gimnasia M.`,
  `Estudiantes de Rio Cuarto`, `Atlante FC`. `resolve_or_register` se negó a
  crearlos porque los cuatro tienen candidato difuso por encima del suelo de
  60, y **los cuatro candidatos eran falsos**: Remo (Belém) contra Grêmio
  (Porto Alegre) a 80, Gimnasia de Mendoza contra la de La Plata a 82.

Bajar el umbral habría "resuelto" los cinco del primer grupo y fusionado los
cuatro del segundo con clubes ajenos. Es el mismo argumento de `db/011` y sigue
siendo el correcto: el umbral no se toca, los casos se miran uno a uno.

Los cinco de Champions que quedan (Club Brugge, Galatasaray, Sabah, Slavia
Praha, Viking) no se tocan: sus ligas no están en el catálogo y darlos de alta
bajo `eu.ucl` partiría historiales. Sus partidos se descartan a propósito.

### Dos alarmas permanentemente en rojo, que es lo mismo que apagadas

Con el sistema por fin produciendo datos reales, el chequeo de salud daba
fallos que no lo eran. Las dos causas son del mismo tipo: **la métrica no medía
lo que decía medir**.

1. **Calendario.** Preguntaba por partidos en los próximos 10 días cuando
   `fixtures.run()` ingiere 21. Con el calendario recién traído y correcto,
   saltó en 10 competiciones a la vez: todas las europeas más Brasil y
   Argentina tenían su próximo partido pasado ese plazo, porque estamos en
   parón de selecciones. Preguntar por una ventana más CORTA que la que se
   ingiere no puede distinguir "no hay partidos" de "no se han traído": solo
   sabe dar falsos positivos. El horizonte pasa a ser el mismo que el de la
   ingesta.

2. **Nombres sin emparejar: 362 fantasmas.** `history_fd._ensure_team` daba de
   alta el equipo e insertaba su alias con un INSERT a mano en vez de
   `register_alias`. Para la tabla de alias da igual; para `unresolved_names`
   no, porque solo `register_alias` marca la fila resuelta. Cada nombre nuevo
   pasaba antes por `resolve_team`, quedaba registrado como pendiente, y ahí
   se quedaba **para siempre aunque todo hubiera funcionado**. El chequeo
   reportaba 362 nombres (84.887 apariciones, casi todos MLS) y recomendaba
   `bootstrap_aliases.py`, que ni siquiera toca la fuente `football_data`.

   Tras el arreglo y el cierre de las filas viejas: **371 → 9**, y los 9 son
   los clubes de copa irresolubles por diseño. Ahora cuando esa alarma suene
   querrá decir algo.

La lección es la misma de la guarda de muestra efectiva de esta misma sesión:
tres guardas y dos alarmas, todas razonables por separado, todas midiendo la
cantidad equivocada. Lo que las destapó en los tres casos fue hacer correr el
sistema con datos de verdad.

---

## 2026-09-22 — Fase 2: implementado el plan. El cierre deja de ser el rival

Implementados los cuatro puntos del plan de fase 2. Lo que los une es una sola
lectura, y conviene tenerla clara antes que el código: **`w_model = 0.0001` no
dice "el modelo no sirve", dice "el modelo sirve para la FORMA, no para el
NIVEL"**. La forma es la matriz de marcadores, de la que salen ~150 mercados
coherentes entre sí; eso el mercado no lo da. El nivel lo da el mercado, y
mejor.

### 1. La puerta comercial pasa a decidirse por CLV

Son dos afirmaciones distintas y solo una es alcanzable:

    "mi probabilidad es mejor que el consenso de cierre"   -> casi nadie
    "el precio que tomé era mejor que el cierre que vino"  -> medible, y es
                                                              lo que se cobra

La puerta anterior exigía la primera (`beats_market_same_rows` en RPS) y se
conformaba, para el CLV, con una media no negativa. Es la peor combinación:
rechazaba todo por lo imposible y no filtraba nada por lo que importa, porque
una media positiva la produce cualquier racha.

`evaluate_clv_gate` exige ahora tres cosas a la vez: 300 apuestas liquidadas,
el intervalo de confianza del 95% del CLV **entero** por encima de cero, y al
menos 3 ligas con muestra propia. La tercera no es adorno: un CLV que solo vive
en una liga es un hallazgo sobre esa liga —o sobre una casa, o sobre un horario
de publicación— y es lo primero que desaparece cuando esa casa limita la
cuenta. Batir al cierre se sigue reportando; ya no veta.

**No es un ablandamiento.** Se quita una condición inalcanzable y se endurece
la que sí discrimina. Está fijado en `tests/test_puerta_clv.py`, con un test
por cada una de las tres condiciones.

De paso: el parámetro `clv` de `evaluate_base_promotion` existía y **no se
pasaba nunca** desde `train.py`, así que `ready_for_commercial_picks` era falso
por construcción, no por medición. Parecía una puerta y era un tapón.

### 2. El ancla de mercado, y el brazo que faltaba

`model/market_anchor.py` invierte el 1X2 ya sin margen a las intensidades que
lo reproducen bajo Dixon-Coles. Ida y vuelta exacta a 1e-10.

Devuelve SIEMPRE el residuo, y no es cautela retórica: fijados los dos goles
esperados, la probabilidad de empate queda determinada, así que la familia no
puede representar cualquier terna. Un mercado con empate al 10% y local y
visitante iguales no tiene solución —el ajuste se va a lambda = mu = 7,5 con
residuo 0,0127— y el módulo lo dice en vez de devolver el ajuste menos malo con
cara de número bueno.

El bug de diseño que esto cierra: `lineup_challenger.apply()` multiplica
`base_lam`, y `base_lam` venía de `predictions.home_lambda`, o sea **las
lambdas del modelo**. Con w_model ≈ 0, ajustar por el XI unas lambdas peores
solo mueve una estimación peor. `shadow.py` gana dos brazos más
(`baseline_market` y `lineup_lambda_market`), y con los cuatro sobre las mismas
cuotas cada comparación aísla una sola cosa:

    modelo  -> modelo+XI    : ¿el XI aporta?
    mercado -> mercado+XI   : ¿aporta SOBRE lo que ya estaba preciado?
    modelo  -> mercado      : cuánto de la diferencia era solo nivel

### 3. Información nueva

El XI ya estaba construido y ahora tiene dónde apoyarse (punto 2). La señal de
noticias y lesiones vía LLM sigue **esperando una decisión que no es técnica**:
qué medios por liga. No se inventa aquí.

### 4. Los dos puntos matemáticos, que resultaron ser uno

Iban en la lista como dos ítems y se resuelven con la misma cantidad: cuánto
varía el edge cuando los parámetros varían dentro de su propia incertidumbre.

`DixonColes.fit()` deja ahora el error estándar de `attack` y `defence` de cada
equipo. Se llegó a la fórmula por descarte, y los dos intentos fallidos la
explican mejor que ella misma:

1. **La curvatura del objetivo a secas** no vale: los pesos se normalizan por
   su media antes de entrar en la verosimilitud, así que un dataset de 12 años
   con media vida de 180 días se comporta como si sus 48.000 partidos contaran
   enteros. Errores estándar unas cuatro veces demasiado pequeños.

2. **El estimador sándwich** `H^-1·V·H^-1` arregla la escala y falla justo
   donde importa. Entrenado sobre los 48.372 partidos reales, los seis equipos
   con el error estándar MÁS PEQUEÑO del modelo —o sea, los que decía conocer
   mejor— eran los seis con muestra efectiva 0,0000: Chivas USA, QPR, Córdoba,
   Leones Negros, Cesena, Evian. Y es correcto en su propio marco: sin muestra
   no hay variabilidad muestral. Pero ese parámetro no lo fijan los datos, lo
   fija el ridge, y **un prior no es conocimiento**. Un número que dice "de
   este equipo estoy segurísimo" sobre un equipo del que no se sabe nada es
   peor que no tener número.

3. **Corregir el sándwich con la muestra efectiva** `(Σwλ)²/(Σw²λ)` tampoco:
   esa expresión es invariante a la ESCALA de los pesos, que es exactamente lo
   que aquí no se puede ignorar. 24 partidos de hace ocho años, todos con el
   mismo peso minúsculo, "cuentan" como 24 observaciones. Mide cuántas
   observaciones contribuyen, no cuánto pesan.

Lo que queda es la precisión posterior con pesos crudos:

    se = 1 / sqrt( Σ w·λ  +  2·ridge·media(w) )
                   \_____/    \______________/
                   los datos      el prior

Con muchos datos domina el primer término. Sin datos el segundo, que es
diminuto, así que el error estándar se dispara y el modelo declara que no sabe.
Las dos situaciones son el mismo número, no dos reglas pegadas, y por eso la
abstención del equipo sin muestra sale sola sin una regla aparte.

Se ignoran los términos fuera de la diagonal: suficiente para decidir una
abstención, no para publicar un intervalo de confianza. Está dicho en el código.

`model/uncertainty.py` los propaga por Monte Carlo hasta el edge, y de la
distribución salen las dos decisiones de golpe:

    edge_floor = media - Z·sd
    edge_floor <= 0  ->  ABSTENERSE: la ventaja no se distingue de cero
    edge_floor >  0  ->  encogimiento = edge_floor / media

Ese cociente es `EDGE_SHRINKAGE` pero **medido y por apuesta**. La constante
0,55 encogía igual una discrepancia sobre el Liverpool, del que hay veinte
partidos recientes, que una sobre un recién ascendido del que hay tres. El
test que de verdad importa no es que el número salga, es
`test_el_encogimiento_medido_premia_a_quien_esta_mejor_medido`: que
DISTINGA. Si no distingue, no vale más que la constante.

`UNCERTAINTY_ENABLED` apagado por defecto, como `META_BLEND_ENABLED` y
`RESIDUAL_ENABLED`: cambia cuántos picks se publican al día y eso es decisión
de negocio, no del código.

**Al medir si funciona, no confundir la métrica.** Esto no crea ventaja:
elimina apuestas de EV negativo. Sube el ROI realizado y NO debe mejorar el
RPS. Si alguna vez mejora el RPS, está mal planteado.

## 2026-09-22 — Bajas/lesiones: fuente decidida, no era el LLM

El backlog llevaba la tarea bloqueada como "vía LLM" (lectura de prensa local
por liga + extracción NLP). El usuario encontró que API-Football —el mismo
proveedor ya contratado en plan Pro para calendario y alineaciones— tiene un
endpoint `/injuries` que da el dato ya estructurado (jugador, tipo de baja,
motivo) por prácticamente cualquier liga. Eso descarta el diseño LLM por
completo para esta señal: no hay texto que extraer, así que no hay coste de
inferencia recurrente ni riesgo de alucinación en el parseo, y el coste de
API es $0 incremental sobre lo ya pagado.

La restricción de diseño que sí se hereda del plan original sigue vigente:
cada fila lleva su propio `captured_at`, y cualquier feature construida sobre
`injuries` tiene que respetar `as_of <= kickoff` en `features_pit`, igual que
todo lo demás. Sin eso es fuga, no señal — el proveedor cambiado no cambia
esa regla.

Decisión de diseño tomada al implementar: a diferencia de `lineups` (una
sola captura por partido dentro de T-90..T-20, porque el XI no cambia una
vez publicado), una baja se conoce con días de antelación y su estado
evoluciona (duda → confirmado), así que `injuries.py` relee cada partido
cada `MIN_HOURS_BETWEEN_CHECKS` (4h) dentro de una ventana de 7 días. Para
no reconsultar para siempre un partido sin bajas reportadas, se añadió
`injuries_capture_log`, que registra el intento aunque la respuesta esté
vacía — sin eso, "no hay bajas" y "no se ha comprobado" son indistinguibles
y el ingest reintentaría cada partido en cada pasada sin parar.

Todavía no existe la feature de disponibilidad (equivalente a
`lineups.availability()`): `injuries.py` solo ingiere y almacena. Es el
siguiente paso, y necesita acumular datos primero — igual que pasó con
alineaciones.

## 2026-09-22 — Verificada cobertura de `/injuries`: hueco real en 3 ligas

Se comprobó `/injuries` contra las 13 competiciones (clave real, `league` +
`season` actual y también por `fixture` suelto). 10 van bien. Tres no:
`mx.liga_mx`, `ar.primera`, `pt.primeira` devuelven 0 resultados para la
temporada 2026 en curso, tanto agregado como por partido, pese a tener 79,
400 y 62 partidos terminados esa misma temporada — no es que no haya
lesionados, es que el proveedor no tiene el dato ahí. Con `season=2025` sí
hay datos (166, 51, 77), lo que descarta un parámetro de temporada mal
calculado: es cobertura real ausente, exactamente el mismo patrón de "array
vacío con status 200" que ya se documentó para el xG de este mismo
proveedor. Anotado en README.md junto a esa advertencia porque es el mismo
fallo silencioso, no uno nuevo que inventar.

Decisión: no se excluye a esas 3 ligas de `injuries.py` (el módulo sigue
llamando al endpoint para las 13, tal como está). No hay forma de
distinguir por una sola pasada "liga sin cobertura" de "liga sana sin
bajas hoy" — hace falta acumular varios ciclos de 4h y ver si CUALQUIER
partido de esas 3 ligas reporta alguna vez una baja; si nunca lo hace, ahí
sí se confirma el hueco y se puede marcar la liga como "sin señal de
lesiones" en vez de asumir plantillas sanas.

Añadida la vigilancia: `check_injuries_coverage()` en
`src/qf/ingest/health.py`, en la lista `CHECKS` que corre `health.run()`
diario. Cuenta, por liga, partidos distintos comprobados en
`injuries_capture_log` los últimos 30 días y la suma de `n_reported`. Si una
liga acumula 15+ partidos comprobados con 0 bajas en total, es la misma
firma que ya se vio a mano con mx/ar/pt — salvo que esa liga ya esté en
`KNOWN_INJURY_COVERAGE_GAPS`, para no alertar cada día por algo ya
investigado y no accionable desde este lado (mismo principio que
`check_fixtures_horizon` con las ligas fuera de temporada: una alerta que
salta a diario por algo normal se deja de leer). El umbral de 15 partidos es
el mismo tipo de decisión que `HORIZON_DAYS`: bajo con muestra chica da
falsos positivos, y aquí 15 partidos de una liga completa sin una sola baja
es prácticamente imposible por azar si el proveedor sí tiene el dato.

---

## 2026-09-22 — La zona de abstención rechaza el 100% de los picks, y el número cuadra

Reajustado el modelo con los errores estándar correctos (86 min) y pasada la
cadena completa del punto 4 sobre cuotas reales de la Premier.

Primero, la corrección funciona. Los errores estándar son ahora **monótonos en
la muestra** a lo largo de cinco órdenes de magnitud:

    N_efectivo   equipos   se_attack (mediana)
    [0, 0.1)         75        21.56
    [0.1, 1)         20         1.26
    [1, 5)           35         0.55
    [5, 15)          61         0.31
    [15, 99)        171         0.19

Mejor conocidos: Bayern Munich (0,117), Inter Miami (0,121), Sp Lisbon (0,129).
Peor: Córdoba, QPR, Chivas USA, los tres a 23,7 con muestra 0,0000. Son
exactamente los mismos que la versión con sándwich colocaba como los MEJOR
conocidos, con el orden invertido.

### Y entonces la abstención rechaza los 19 picks del día

    con la constante 0,55:      19 picks
    con encogimiento medido:     0 picks

Ninguno sobrevive. Ni siquiera partidos entre equipos con 19-20 partidos
efectivos. La desviación típica del edge va de 14 a 94 puntos porcentuales.

**No es un error del código, y la aritmética lo dice sin ambigüedad.** Un
equipo bien medido tiene ~20 partidos efectivos a ~1,4 goles, o sea ~28 goles
observados. El error estándar de una tasa logarítmica con 28 eventos es
1/sqrt(28) = 0,19, que es exactamente el `se_attack` que sale del ajuste. De
ahí, sd(log lambda) ~ 0,26: **la intensidad varía ±26% a una sigma**. Con esa
variación, una cuota de 5,50 mueve el edge decenas de puntos. Es la varianza de
Poisson de los goles del fútbol, no un defecto de la implementación.

Dicho de otro modo: la ventaja nominal del modelo (3-10%) es **un orden de
magnitud menor que el ruido de sus propios parámetros**.

Esto CONCUERDA con lo ya medido por caminos independientes —`w_model = 0.0001`,
derrota contra el cierre en las 7 ligas— y es una comprobación cruzada
valiosa: dos métodos que no comparten nada llegan a la misma conclusión.

### Pero Z = 1,0 no sirve como valor por defecto, y hay que decirlo

La regla `media - Z·sd > 0` con Z=1 exige ~84% de confianza en que el edge es
positivo. Con sd de ese tamaño eso es inalcanzable por construcción, así que el
interruptor encendido significa hoy "no apostar nunca". Un mecanismo que
siempre dice no no está midiendo, está apagado con otro nombre.

Tres cosas que corregir antes de darlo por bueno:

1. **La regla es MÁS ESTRICTA que la óptima en valor esperado.** Para EV basta
   `E[p]·cuota > 1`; exigir que el suelo sea positivo es una decisión de
   prudencia, no un resultado estadístico. Conviene no confundirlas.
2. **Mide incertidumbre ABSOLUTA, no relativa al mercado.** Lo que decide una
   apuesta es si nuestro error es menor que el suyo, y el mercado también
   desconoce la lambda verdadera. Un modelo puede tener ventaja real con
   incertidumbre absoluta grande. La versión correcta mediría la varianza de
   (p_modelo − p_mercado), y con el ancla de mercado ya existe la pieza para
   hacerlo.
3. **Ordenar por media/sd no arregla la selección adversa.** Los dos
   candidatos que más se acercan a pasar son justo los de mayor edge bruto
   (47,9% y 50,4%), que son los más sospechosos de ser error del modelo. El
   cociente se queda cerca de 1 para todos, así que no discrimina donde hace
   falta.

Los cocientes media/sd del día: 0,995 · 0,957 · 0,829 · 0,792 · 0,682 · 0,671 ·
0,613... Con Z=0,95 pasarían dos; con Z=0,80, cuatro. Ese es el rango en el que
hay que calibrar contra histórico liquidado, no en 1,0 por convención.

---

## 2026-09-22 — Caddy como servicio de `docker-compose.yml`

El README ya documentaba un Caddyfile de ejemplo (sección "Proxy con TLS"),
pero era un paso manual fuera del repo: no había ni `Caddyfile` ni servicio
`caddy` en `docker-compose.yml`. `docker compose up -d` no dejaba la API
alcanzable por HTTPS desde ningún dominio; solo `127.0.0.1:8000`.

Se añadió el servicio `caddy` (imagen `caddy:2-alpine`, puertos 80/443,
volúmenes `caddydata`/`caddyconfig` para el certificado y el estado interno) y
un `Caddyfile` en la raíz. Decisión de diseño: `reverse_proxy` apunta a los
nombres de servicio de Compose (`api:8000`, `grafana:3000`), no a `localhost`
como en el ejemplo original del README — ese ejemplo asumía Caddy instalado en
el host, no dentro de la misma red de Docker Compose.

Grafana se mantiene cerrado por IP (`@yo remote_ip {$GRAFANA_ALLOWED_IP}`)
además del login, tal como ya decidía el README: es el panel de operación
privado, no tiene por qué ser alcanzable desde internet en general. Se añadió
`GRAFANA_ALLOWED_IP` a `.env.example` porque antes esa IP estaba hardcodeada
como placeholder en el bloque de código del README y no era una variable real
del sistema.

Pendiente explícito, no resuelto aquí: esto solo pone el proxy TLS en pie.
Sigue sin existir auth de suscriptor no-Telegram ni rate limiting en las rutas
públicas (`harness/tareas.md`); exponer la API con HTTPS no sustituye a esas
dos garantías antes de anunciarla desde la web.

---

## 2026-09-22 — Auth de suscriptor (email+contraseña) y hardening de la API

Decisión del usuario, explícita: la API es de uso exclusivo para su propia web
y una futura app Flutter, pero SIGUE vendiendo picks a suscriptores reales
(no es acceso solo para él) — así que "exclusivo" describe quién puede
integrarse (nada de terceros, sin API pública documentada), no quién se
autentica. Y sobre el criterio de cliente: eligió "solo JWT de sesión" en vez
de añadir un secreto de cliente por plataforma, porque un secreto embebido en
una app Flutter siempre se puede extraer con ingeniería inversa — daría una
sensación de seguridad que no es real, a cambio de mantenimiento real
(rotarlo si se filtra el binario).

### Por qué el diseño previo no alcanzaba, más allá de "falta implementar"

`/v1/auth/telegram` era el único login y depende de `TG_BOT_TOKEN`, que el
usuario no tiene configurado — es decir, el login de suscriptor llevaba
tiempo roto de facto, no solo pendiente. Además el JWT de sesión duraba 30
días sin ningún mecanismo de revocación, y `JWT_SECRET` cuando faltaba se
generaba aleatoriamente EN SILENCIO (`os.getenv("JWT_SECRET") or
secrets.token_hex(32)`): cada reinicio del proceso invalidaba todas las
sesiones sin avisar, y con más de una réplica cada una firmaría con un
secreto distinto. Ninguno de los dos era un bug visible — son exactamente el
tipo de fallo silencioso que este proyecto ya se ha encontrado varias veces
(unidades del stake, `harness_check.sh` sin pytest, fechas UTC vs zona del
servidor).

### Lo que se construyó

- **`db/015_subscriber_auth.sql`**: `password_hash` (nullable — los
  suscriptores viejos de Telegram no tienen y NULL nunca autentica, no abre
  una puerta), `email_verified`, `failed_login_count`, `locked_until` en
  `subscribers`; tabla `refresh_tokens` (hash del token, nunca el valor en
  claro, con cadena de rotación `replaced_by`); tabla `auth_audit_log`.
- **`src/qf/api/auth.py`** (nuevo módulo, separado de `main.py` para poder
  probarlo sin FastAPI ni Postgres real): Argon2id para contraseñas (ganador
  del Password Hashing Competition, recomendación OWASP actual sobre bcrypt
  por su costo de memoria configurable), política de contraseña mínima (12
  caracteres, sin exigir símbolos — la guía NIST 800-63B es explícita en que
  eso empuja a "Passw0rd!" en vez de a contraseñas largas de verdad), emisión
  de access JWT de 15 minutos, refresh token opaco de 30 días con rotación en
  cada uso y **detección de reuso**: si se presenta un refresh ya revocado
  (señal de que un atacante está usando en paralelo un token robado), se
  revoca toda la cadena de sesiones del suscriptor, no solo esa.
- **Endpoints nuevos** en `main.py`: `POST /v1/auth/register`,
  `/login`, `/refresh`, `/logout`. `/v1/auth/telegram` se conserva pero ahora
  devuelve 404 explícito sin `TG_BOT_TOKEN` en vez de fallar más abajo con un
  HMAC que nunca va a poder verificar nada.
- **Enumeración de cuentas cerrada**: registrar con un email ya existente y
  hacer login con contraseña incorrecta devuelven el mismo mensaje genérico
  que "credenciales inválidas" — no confirman si el email está registrado.
- **Bloqueo de cuenta**: `LOGIN_MAX_ATTEMPTS` (5) fallos consecutivos
  bloquean la cuenta `LOGIN_LOCKOUT_MINUTES` (15). Protege contra fuerza
  bruta dirigida a un email; el rate limit por IP (más abajo) protege contra
  fuerza bruta distribuida entre muchas cuentas.
- **Rate limiting real**: no existía NINGUNO antes de hoy — ni global ni en
  auth. `security_middleware` en `main.py` limita por IP TODAS las rutas
  (`RATE_LIMIT_DEFAULT_PER_MINUTE=60`) y más estricto en `/v1/auth/*`
  (`RATE_LIMIT_AUTH_PER_MINUTE=10`), usando `INCR` de Redis sobre una ventana
  fija — atómico, dos peticiones concurrentes no pisan el contador. La IP se
  toma de `X-Forwarded-For`, correcto solo porque Caddy (ver sección anterior)
  es quien lo escribe y el cliente no puede llegar a la API sin pasar por él.
- **`JWT_SECRET` obligatorio en el arranque**: `main.py` ahora lanza
  `RuntimeError` si falta, en vez de generar uno efímero. Falla fuerte y
  temprano en vez de fallar silenciosamente en producción.
- **Manejador de excepciones global**: cualquier excepción no capturada
  devuelve `{"detail": "Error interno"}` con 500 en vez de dejar que algo se
  filtre (traceback, ruta de archivo, fragmento de SQL); el detalle real va
  al log del proceso, no a la respuesta.
- **Cabeceras de seguridad** en todas las respuestas
  (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`) y `Cache-Control: no-store` en `/v1` y `/admin` — no
  tiene sentido que un proxy o el navegador cacheen picks de pago o rutas de
  operación.
- **CORS**: el origen de desarrollo (`localhost:5173`) ya solo se añade con
  `APP_ENV=development`; antes estaba siempre en la lista, incluida en
  producción, sin ganar nada por tenerlo ahí (`allow_headers` también se
  acotó de `["*"]` a los dos que la API realmente usa).

### Lo que se decidió NO construir ahora, y por qué

Verificación de email y reseteo de contraseña por correo requieren decidir un
proveedor SMTP (Resend/Postmark/SES) antes de escribir una sola línea — no
tiene sentido dejar `email_verified` a medias sin forma real de enviar el
correo de verificación. Por eso `email_verified` existe en el esquema (para
no tener que migrar otra vez) pero no bloquea el login todavía. Cobros siguen
fuera de alcance, como ya decidía `harness/tareas.md`.

Un secreto de cliente por plataforma (HMAC firmado por build) se descartó por
decisión explícita del usuario: añade fricción y mantenimiento (rotarlo si se
filtra el binario de la app) a cambio de una protección que no es real contra
un atacante dedicado — solo filtraría bots automatizados poco sofisticados,
y eso ya lo cubre el rate limiting por IP.

### Tests

`tests/test_auth.py`, 12 casos, todos sobre lógica pura (hash/verify de
contraseña, política mínima, emisión/expiración/tipo de access JWT, y el
contador de rate limit contra un Redis falso en memoria). Lo que necesita
Postgres real (rotación de refresh tokens, bloqueo de cuenta, auditoría) no
tiene test automatizado — mismo patrón que el resto de `main.py`, que no se
prueba con TestClient en este repo. Queda como verificación manual pendiente,
igual que el resto de rutas de la API en `harness/tareas.md`.

---

## 2026-09-22 — Corrección de alcance: sin cuentas de usuario en la API

En la misma sesión que construyó el auth de suscriptor de arriba, el usuario
corrigió el modelo de negocio: la API no va a tener suscripciones ni registro
de usuarios. Los pronósticos se sirven a su frontend, que es quien arma los
prompts del LLM para el usuario final y quien cobra las suscripciones — con
su propia base de datos de usuarios, que no vive en este repo.

Eso obligó a revisar una premisa que había quedado sin cuestionar: ¿la app
Flutter futura llama directo a esta API, o llama al backend del frontend? La
respuesta importa porque un secreto que vive en un cliente que corre en el
dispositivo del usuario —JavaScript de navegador, o el binario de una app
Flutter— **siempre se puede extraer** con herramientas estándar (devtools,
apktool, frida). No es una debilidad de implementación que se arregle
ofuscando mejor: es una propiedad física de ese tipo de cliente. El usuario
confirmó el patrón BFF (Backend For Frontend): tanto la web como la futura
app Flutter le hablan a un backend propio suyo, y SOLO ese backend —que corre
en un servidor, no en el dispositivo del usuario— conoce el secreto que abre
esta API.

### Se revirtió el trabajo de la entrada anterior, completo

- `db/015_subscriber_auth.sql` se eliminó sin haberse aplicado a ningún
  Postgres real (se creó y se borró en la misma sesión).
- `src/qf/api/auth.py` (hash Argon2id, política de contraseña, access/refresh
  JWT, bloqueo de cuenta, auditoría) se eliminó completo.
- `POST /v1/auth/register|login|refresh|logout|telegram` se eliminaron de
  `main.py`: no hay usuario final que la API deba conocer.
- `PyJWT`, `argon2-cffi`, `email-validator` salieron de `requirements.txt`:
  ya no tienen consumidor.

Lo único que sobrevivió del trabajo anterior fue el rate limiting por IP
(movido a `src/qf/api/ratelimit.py`, sigue haciendo falta con o sin cuentas:
un `SERVICE_TOKEN` filtrado sin límite de tasa permite scraping sin freno) y
las cabeceras de seguridad / manejador de excepciones global de
`main.py`, que no dependían de la existencia de suscriptores.

### El diseño que quedó: `require_service`, un único secreto

`/v1/*` pasó de `current_subscriber` (JWT por usuario, con tier) a
`require_service` (`X-Service-Token` contra `SERVICE_TOKEN`, comparación en
tiempo constante, 404 si no coincide — el mismo patrón ya usado por
`require_admin`, deliberadamente: no confirmar que la ruta existe si el
secreto no coincide). Sin distinción de tier: quien presenta el token de
servicio recibe TODOS los picks y todas las probabilidades, porque decidir
qué le muestra a CADA usuario final ya no es trabajo de esta API — es trabajo
del backend del frontend, con su propia base de suscriptores.

Consecuencia directa: la tabla `subscribers` de `db/001_schema.sql` (con
`email`, `tier`, `telegram_id`) se queda sin ningún consumidor en esta API.
No se borró de la migración base porque editar `001_schema.sql` no cambia una
base de datos ya aplicada, y no hay evidencia de que el usuario quiera
mantener esa tabla para otra cosa; queda anotado en `harness/tareas.md` para
cuando construya el backend del frontend, por si prefiere esa base de datos
en otro sitio.

### Por qué NO se ofreció "secreto de cliente por plataforma" como alternativa

Con el patrón BFF confirmado, la pregunta de si el `SERVICE_TOKEN` necesitaba
algo más fuerte que una comparación simple (HMAC por request, mTLS) queda sin
urgencia: el secreto vive en un servidor que el propio usuario opera, no en
un cliente hostil. mTLS sería la siguiente capa razonable SI el backend del
frontend corriera en infraestructura que el usuario no controla del todo;
mientras sea su propio servidor, la comparación en tiempo constante sobre
HTTPS (ya servido por Caddy) es proporcional al riesgo real.

---

## 2026-09-22 — Calibración de Z: no hay nada que calibrar, y el control lo explica

Se calibró contra histórico real y point-in-time: tres cortes (2025-01-01,
2025-06-01, 2025-11-01), ajuste con SOLO lo anterior a cada corte, predicción
del tramo siguiente, errores estándar del mismo ajuste. **12.183 filas sobre
4.061 partidos y 11 competiciones**, con el cierre real como precio apostable.

### La pregunta previa: ¿discrimina la razón media/sd?

Antes de optimizar Z hay que comprobar que el mando está conectado a algo. No
lo está. Quintiles de media/sd, ROI con stake plano:

    quintil   ratio medio    ROI        IC95
      1          0.086      +3.44%   [-7.1, 14.0]
      2          0.266      -8.67%   [-18.8,  2.0]
      3          0.461     -11.34%   [-21.4, -0.2]
      4          0.721     -13.15%   [-23.8, -1.4]
      5          1.246      -6.77%   [-18.1,  5.0]

No monótono, intervalos solapados, correlación con el acierto **−0,047**.

La rejilla de Z parecía decir lo contrario —el ROI sube de −8,48% (Z=0) a
+2,48% (Z=1,0)— pero desde Z=0,4 **todos los intervalos incluyen cero**, y en
Z=1,0 el intervalo es [−13,0, +19,0] con 563 picks. Es ruido con forma de
tendencia. Si se hubiera mirado solo esa tabla, se habría "calibrado" Z=1,0 con
un número de aspecto convincente.

### El control, que es el hallazgo de verdad: el edge del modelo es ANTI-señal

Quintiles del edge CRUDO, sin incertidumbre de por medio:

    quintil   edge medio     ROI        IC95
      1          2.10%      +1.65%   [-7.3,  11.3]
      2          7.11%      -2.78%   [-12.8,  7.2]
      3         14.08%      -5.04%   [-16.0,  5.4]
      4         25.20%     -15.90%   [-25.8, -4.6]
      5         57.26%     -14.43%   [-26.9, -1.8]

**Cuanto mayor dice el modelo que es su ventaja, peor va.** Monótono, y la
correlación del edge con el acierto es **−0,1228** sobre 4.880 filas, que son
unas 8,6 desviaciones típicas de cero.

Es selección adversa en estado puro: donde el modelo más discrepa del cierre,
más se equivoca. Y explica por qué la zona de abstención no podía funcionar:
**filtrar más fuerte sobre una señal negativa no mejora nada**. Cualquier regla
construida sobre esa cantidad hereda el signo.

Correlaciones con el acierto, para situarlo:

    p_model    +0.3123   <- el modelo SÍ sabe de fútbol
    n_ef       -0.0255
    ratio      -0.0474
    edge_mean  -0.1228   <- pero su discrepancia con el cierre es dañina
    edge_sd    -0.2106

El modelo no tiene edge cero. Lo tiene **negativo**, y eso es distinto y peor.

### De paso: el modelo está bien calibrado

Independiente de todo lo anterior, y es una buena noticia:

    p_model        n     predicha   observada    error
    (0.1, 0.2]   1440     0.1620     0.1535     -0.009
    (0.2, 0.3]   4870     0.2517     0.2624     +0.011
    (0.3, 0.4]   2292     0.3443     0.3264     -0.018
    (0.4, 0.5]   1573     0.4478     0.4520     +0.004
    (0.5, 0.6]    980     0.5467     0.5398     -0.007
    (0.6, 0.7]    542     0.6445     0.6365     -0.008

Dentro de ±0,02 en todos los tramos con muestra. Confirma por otra vía por qué
el calibrador se descartaba: no había nada que corregir. Los extremos
(p > 0,7, n = 270) muestran infraconfianza de +0,05, pero con esa muestra no
se puede afirmar.

### Decisión

- `UNCERTAINTY_ENABLED` se queda en 0, y **no por prudencia sino por medición**.
- `UNCERTAINTY_Z` queda documentado como SIN CALIBRAR. Ningún valor es
  defendible porque no hay señal que calibrar. Poner 0,9 porque la tabla sube
  sería exactamente el error que este experimento existía para evitar.
- Y lo más importante: **`find_candidates` selecciona hoy, en promedio,
  apuestas perdedoras**, porque ordena por una cantidad con correlación −0,12.
  No se cambia a escondidas, pero queda escrito arriba del todo.

### La estrategia que sí podría funcionar NO se puede probar con este histórico

El punto 1 del plan —precio justo sharp y apostar donde una casa blanda aún no
ha convergido— no depende del edge del modelo, así que no hereda este signo.
Pero es **imposible de medir con los datos que hay**: el solapamiento entre
Pinnacle y bet365 es CERO. 46.928 partidos tienen solo Pinnacle y 2.014 solo
bet365, porque `history_fd` guarda una única casa de cierre por partido. Sin
dos casas sobre el mismo partido no hay line shopping que medir.

Eso convierte el plan de The Odds API en el cuello de botella real: es la única
fuente que da varias casas sobre el mismo partido, y con 500 créditos el worker
no puede correr. Ya no es una mejora deseable, es la única vía abierta.

## 2026-09-24 — Mesa de mercados en el prototipo web (referencia: propsbr.app)

El usuario preguntó si propsbr.app podía servir de modelo para vender sus
picks. PropsBR es un buscador de props por acierto reciente (L5/L10/L20, H2H)
con nota 0-100 y etiquetas del tipo «certera/segura»; no mide nada contra el
cierre. Se copió su **composición** (lista de partidos, tabla densa ordenable,
detalle lateral con pestañas, columna de destacados, formato de cuota) y se
descartó su **contenido**.

Decisiones:

- La mesa enseña lo que el sistema sí mide: precio justo de Pinnacle sin
  margen, mejor casa de la lista, % sobre el justo en el mismo snapshot,
  `min_price` y exclusión por Pinnacle fuera de consenso. El modelo va como
  columna de diagnóstico y nunca ordena: su edge es anti-señal medida.
- Al ordenar por diferencia, lo excluido o cerrado va siempre al final. Un
  +10% de un partido con Pinnacle roto encabezaba la tabla y era justo el
  número que el criterio descarta.
- Los precios demo se derivan de dos lambdas (Poisson) y pasan por el mismo
  criterio que `publish/picks.py` (1X2, +2%, 3% de desviación máxima, un pick
  por partido), para que mesa, picks y ficha no se contradigan. Con precios
  realistas salen pocas candidatas; no se forzaron más.
- `.table-wrap` necesita `position:relative`: el texto `sr-only` absoluto
  dentro de tablas desplazables se escapaba del recorte y ensanchaba la
  página a 825 px en móvil.
- El menú lateral pasó a una cabecera fija arriba (petición del usuario): la
  mesa necesita todo el ancho para la tabla, y el lateral le quitaba 224 px.
- Accesos rápidos al estilo PropsBR (petición del usuario), con nombres que
  dicen lo que miden: «Top probabilidad» en vez de «top confianza», porque
  ordena por probabilidad justa y eso no dice si la cuota compensa.
- Combinadas calculadas por casa y no con la mejor cuota de cada selección:
  la combinada se juega entera en una casa. En la demo, dos selecciones a
  +3,5% y +7,5% en su mejor casa dan +0,0% en la única que cotiza las dos a
  buen precio; enseñar la otra cifra habría sido vender una ventaja que no
  se puede cobrar. Una selección por partido: dentro del mismo partido están
  correlacionadas y el producto de probabilidades sería falso.
- Revisados los nueve botones reales de PropsBR: seis son la misma lista por
  Score con distinto corte, dos son combinadas armadas (Parlays ~2X/~3X y
  Seguras 1,50–2,30) y uno, «Certera del día», es un pick de pago con venta
  que cierra al inicio e historial público. Ese último es exactamente el
  negocio de QuantFut, así que entró como **Pick del día**; los cortes
  duplicados no se copiaron. Sus parlays anuncian «62% prob» en una cuota
  2.30 (implícita 43%): nuestras combinadas enseñan la probabilidad justa.

## 2026-09-25 — El proyecto pasa a git

Petición del usuario tras el incidente de abajo. Rama `main`, primer commit
`4bd73ee`. Decisiones:

- Fuera del repo: `.env` y `.env.*` (menos `.env.example`), el volcado
  `quantfut.dump` (dato de producción, no código), `.venv`, `.local` (cachés
  de >100 MB) y `__pycache__`. Antes del primer commit se comprobó que ningún
  valor secreto de los `.env` aparece en otro archivo (solo `REDIS_URL`, que
  no lleva contraseña).
- `.gitattributes` fija LF: el despliegue copia al servidor Linux tal cual, y
  el `crontab` y los `.sh` se rompen con CRLF. 21 archivos Python tenían CRLF
  en disco; normalizados.
- Aún SIN remoto: el código solo está en este PC y en el VPS. Falta decidir
  dónde vive la copia remota (GitHub privado o un repo en el propio VPS) y
  convertir `~/quantfut` del servidor en copia de git, para que `git status`
  allí delate cualquier archivo subido a mano.

## 2026-09-25 — Incidente: la sombra caída 2 h por un archivo subido a medias

A las 17:56 UTC alguien (no esta sesión) subió al servidor el
`shadow_sharp.py` de goles y hándicap —que se había decidido NO desplegar— y
reconstruyó la imagen, sin la migración 022 ni el `picks.py` a juego. La
captura horaria de la sombra falló desde las 18:25 (`'Offer' object has no
attribute 'market'`); falla antes de escribir, así que no ensució nada, pero
se perdieron ~2 h de ofertas. Restaurado el original (reconstruido deshaciendo
los cambios exactos: no quedaba imagen anterior) y verificado con una captura
manual.

Decisiones:

- El código de goles y hándicap sale del repo y va a
  `harness/archivo/goles_handicap_20260925/` (con su migración 022). Tenerlo
  en `src/` sin desplegar era la trampa: el proyecto no usa git y cualquier
  subida de la carpeta lo arrastra.
- Antes de cada despliegue se compara TODO `src/` y `db/` con el servidor
  (`tar` + `diff -rq`), no solo los archivos que se van a subir. Así se vio
  que el único archivo distinto era el roto.

## 2026-09-25 — Picks sin predicción, etiquetas de temporada y limpieza

- Pick sin predicción (`db/025`): ver tareas. Vacío, nunca 0, en
  `model_prob`: un 0 se leería como "el modelo da 0%".
- Etiqueta de temporada (`db/026`): el calendario etiqueta como el
  histórico ('2627'). Se cambió la columna, no el match_id, que lo referencian
  predicciones, picks y cuotas inmutables; el calendario encuentra los
  existentes por su id de API-Football, así que no duplicó nada (verificado).
- "Evento sin emparejar" de `odds_worker` baja a debug: no era un fallo.
- `pyton/` borrada; su único contenido sin copia (la versión inicial) queda en
  `harness/archivo/`.

## 2026-09-25 — LaLiga 2 y Serie B, sin ensuciar la base

Petición del usuario, con esa condición expresa. Entran por el criterio sharp
(backtest: +3,9% y +5,1% al cierre, validables en The Odds API).

Decisiones:

- `leagues.model_enabled`: las ligas nuevas alimentan calendario, resultados,
  cuotas y sombra, pero NO el modelo ni la predicción diaria. Sin esto el job
  de las 08:00 habría sellado predicciones de equipos que el modelo no
  conoce, y lo sellado es público e inmutable.
- Un club tiene una sola liga en `teams`: al abrir una división nueva el
  calendario habría duplicado a los 20 descendidos de LaLiga y Serie A. Ahora
  `resolve_or_register` busca coincidencia EXACTA en las otras ligas del mismo
  país antes de crear, y el parecido dudoso queda pendiente. Sirve también
  para ascensos futuros.
- Aun así, ningún equipo quedó a la automática: `db/024` da de alta los 22
  nuevos y los alias de las dos fuentes de los 42, revisados uno a uno tras un
  ensayo en seco. El ensayo justificó la regla: "Real Sociedad II" daba 90
  contra "Real Sociedad" (el umbral de aceptación) y era el filial;
  "Sporting Gijon" daba 73 contra "Sp Gijon" y sí era el mismo club.
- Alias de The Odds API desde el primer día: sin ellos el cierre de Pinnacle
  no casa y la oferta se queda sin vara en silencio.
- The Odds API solo paga `h2h` en estas ligas (1 crédito por llamada): es el
  único mercado del criterio y a la API le quedan ~3.200 créditos.
- Sin histórico de football-data (`fd_code` NULL): el criterio no lo
  necesita y cargarlo mezclaría dos fuentes de nombres en equipos nuevos.

## 2026-09-25 — Goles y hándicap: implementado, probado, y sin valor

Petición del usuario: más picks cada día, eligiendo "más mercados". Se
implementó el mismo criterio por línea (captura, criterio, sombra, 19 tests,
`db/022`) y, ANTES de desplegar, se ensayó en memoria con la respuesta real
de API-Football para los 24 partidos próximos. Resultado: 0 de 1.448 precios
de casas de la lista por encima del justo en un 2%, en cualquier línea.

Decisiones:

- No se despliega. Publicar el código añadiría captura y almacenamiento
  (~50× filas) sin añadir picks. Queda en el repo, probado, para repetir el
  ensayo con Europa en juego.
- La lección es de producto, no de código: las casas de los suscriptores
  ponen goles y hándicap copiando a Pinnacle con margen; donde se equivocan es
  el 1X2 (empates y no favoritos). Más picks tienen que venir de más PARTIDOS
  en 1X2 (más ligas), no de más mercados del mismo partido.
- Solo línea principal en el criterio: The Odds API da el cierre de Pinnacle
  en una sola línea, y una oferta sin cierre no se puede validar. Trampa
  encontrada y cubierta por test: API-Football etiqueta las dos patas del
  hándicap con la línea del local.

## 2026-09-27 — Fichas de partido reales en la web: contenido, no criterio

Pedido del usuario: que el sitio resulte atractivo con fichas al estilo
PropsBR usando API-Football. Desplegado (db/028, db/029, `ingest/standings`,
`/web/partidos`, vista «Partidos y estadísticas»).

- La ficha NO lleva probabilidades de mercado ni precio justo, aunque el
  plan las incluía. El producto es "una casa paga ≥2% sobre el justo de
  Pinnacle"; publicar ese justo en cada partido deja a cualquiera hacer la
  cuenta con la cuota de su casa. Tampoco el modelo (su edge es negativo).
- Coste de API casi nulo: `results.py` ya pedía `/fixtures/statistics`;
  ahora guarda la respuesta entera en `matches.stats`. Lo único nuevo es
  `/standings`, 13 peticiones dos veces al día.
- La forma y los promedios solo miran 270 días atrás. Sin tope, Valladolid
  (en Segunda, sin histórico de football-data) enseñaba como "últimos 5"
  partidos de Primera de mayo de 2025. Con tope, un descendido enseña sus
  partidos de mayo de 2026 con fecha y competición: verdad, aunque no sea
  su forma en Segunda. Lo correcto es cargar la temporada en curso de
  LaLiga 2 y Serie B (propuesto al usuario; ver tareas).
- `teams.display_name` (nombre de API-Football, solo si la coincidencia en
  standings es EXACTA) en vez de tocar `canonical_name`, que es la identidad
  de emparejamiento: "Manchester City" en la web, "Man City" en el sistema.
- Argentina devuelve Apertura (cerrada) y Clausura con la MISMA fecha de
  actualización en todas las filas: la fecha no distingue fases. Se usa el
  orden del proveedor (calendario) y se conserva la última fase; los grupos
  sin prefijo de fase (conferencias de la MLS) no se tocan.
- Aviso sin tocar: `/fair-price/{id}` es público y devuelve `best_price` y
  `gap_pct`: el criterio en abierto. Decisión del usuario pendiente.
- Los logs de cron viven dentro del contenedor `worker`: al reconstruirlo se
  pierden (se vio al buscar `/var/log/fixtures.log`). No se cambió.

## 2026-09-27 — Escudos, temporada de LaLiga 2 / Serie B y un ir y venir del calendario

- Escudos descargados UNA vez al volumen `escudos` y servidos desde el
  propio dominio, en vez de enlazar `media.api-sports.io`: la web no depende
  del CDN del proveedor ni le pasa la IP de cada visitante. 271 archivos,
  12 MB, caché de navegador de 7 días.
- `/standings` devolvió `team.id` nulo para Club León y `/teams` lo llama
  'Leon'. Se completa con `/teams` (1 petición, solo si falta alguno) por
  nombre y, si difiere, por el MISMO equipo resuelto exacto. Un id nulo no
  borra uno guardado (`COALESCE`).
- Temporada de LaLiga 2 y Serie B cargada por el camino normal (insertar
  como programados + `results.close_recent`) en vez de un INSERT a mano:
  mismas reglas de resolución, marcador y estadísticas que cualquier
  partido. El modelo no los lee (`model_enabled = false`).
- Fallo previo encontrado al preparar la carga: `fixtures` pide el día
  entero y los partidos de hoy ya terminados llegan como FT; se mapeaban a
  'scheduled', se reabrían y se borraba su `odds_capture_log` hasta que
  `results` los cerraba otra vez. Ahora un partido `finished` no se toca
  desde el calendario (test en `test_calendario_terminados.py`).

## 2026-09-28 — Un alias no cruza países (Guimarães era el Vitória brasileño)

Buscando escudos que faltaban apareció el Vitória BRASILEÑO 14.º en la
Primeira. API-Football renombró al Guimarães 'Vitória SC', que se normaliza
igual que su alias 'Vitoria' de Brasil; el mapa de alias guardaba UN equipo
por nombre y sin mirar la liga. Ya había metido al brasileño en el
Benfica–Guimarães del 11-oct: se habría sellado una predicción inmutable con
los ratings de otro club.

- `normalize.match_team`: un alias puede ser de varios equipos y solo vale
  el que juega en la liga o en otra división del MISMO país. En copas (sin
  liga) un alias ambiguo no se adivina: se descarta como cualquier nombre
  sin resolver. Colisiones hoy en `team_aliases`: ninguna dentro de una
  fuente; la de Vitória entraba por el nombre nuevo del proveedor.
- db/031 corrige el partido (sin predicciones, cuotas ni sombra), añade el
  alias propio de Guimarães y limpia nombre, id y fila de clasificación que
  se escribieron sobre el brasileño. Comprobación tras el cambio: 0 partidos
  domésticos con un equipo de otro país; las copas siguen con los mismos
  9 + 16 nombres sin emparejar de siempre.
- db/032: escudos de 47 equipos que ya no están en ninguna tabla actual,
  con ids de `/teams` 2023-2025 revisados a mano ('Atletico GO' puntuaba más
  con Atlético-MG). 0 equipos sin escudo entre los que jugaron en 3 años.

## 2026-09-28 — `/fair-price` pasa a privado

Decisión del usuario. `best_price` + `gap_pct` por partido es el criterio de
picks entero: con él cualquiera ve qué casa paga ≥2% sobre el justo sin
suscribirse. Ahora es `/v1/fair-price/{id}` con `SERVICE_TOKEN`; la ruta
pública desaparece (404, igual que una ruta privada sin token, para no
confirmar que existe). No lo consumía nada: ni el frontend ni otro módulo.

## 2026-09-28 — Palancas para acelerar la puerta, sin rebajarla

Pedido del usuario ("ejecuta todas las palancas"). La puerta NO cambia (300
publicables con cierre justo, IC95 > 0, 3 ligas); cambia cuántas
oportunidades se miden por día.

- **Casas.** Simulado antes sobre 36 partidos desde el 24-sep: con la lista
  de entonces, 8 partidos con oferta; con todas las casas del feed, 23. La
  sombra mide ahora TODAS las casas no exchange, pero la puerta filtra por
  `SOFT_BOOKS` AL INFORMAR (no se guarda columna): así la muestra se puede
  recalcular para otra lista sin volver a capturar. Lista ampliada con
  Betsson, Coolbet, LeoVegas y Unibet por operar en España o Latinoamérica,
  pendiente de que el usuario lo confirme; LeoVegas/Unibet llegan con precio
  de Suecia/Países Bajos. Casas offshore de EE. UU. y francesas/alemanas se
  miden pero no cuentan.
- **Cierre.** El "3 de 4 con cierre" era un pick aún sin jugar: 10 de 10
  partidos en sombra lo tienen. El Pinnacle de API-Football nunca baja de
  2,5 h antes del inicio, así que el cierre solo sirve de The Odds API.
  Riesgo encontrado y cerrado: la captura de :25 podía tomar como oferta el
  snapshot de la ventana de cierre, que es contra el que se liquida (EV =
  edge bruto por construcción). No había pasado; ahora se exige ≥ 15 min.
- **Persistencia.** Regla fijada ANTES de tener muestra: la previa pesa como
  100 partidos frente a lo medido (primera oferta por casa y partido,
  acotado a [0, 1]). Cada oferta guarda la persistencia con la que se
  decidió, así que recalibrar no reescribe el pasado.
- **Ligas (db/033).** Chile, Turquía, Suiza, Dinamarca, Noruega, Suecia,
  Championship, Ligue 2, 2. Bundesliga y Brasil B, todas con Pinnacle en The
  Odds API (sondeo de 21 créditos). Colombia, Perú y Ecuador no existen en
  The Odds API; Bélgica, Australia y Superettan no tienen Pinnacle. Equipos
  preparados de antemano como en 024: el calendario, creando de uno en uno,
  descartaba el segundo club que se pareciera al primero. 43 reutilizados
  (25 confirmados por id de API-Football) y 127 nuevos; el calendario no
  creó ninguno más. Coste estimado: ~100 créditos/mes por liga (solo 1X2) y
  ~800 peticiones/día de API-Football.
- **Copas.** Con clubes turcos, suizos o daneses en el catálogo, sus partidos
  de Champions/Europa League empiezan a resolverse. `daily._upcoming` y el
  entrenamiento exigen ahora que la liga DOMÉSTICA de ambos equipos tenga
  modelo: si no, se sellaría una predicción con ataque y defensa 0. Al
  introducir la guarda no excluía ningún partido del entrenamiento.

- **Lista confirmada por el usuario:** sus clientes usan Betsson y Coolbet;
  LeoVegas y Unibet salen de `SOFT_BOOKS` y se siguen midiendo sin contar.

## 2026-09-29 — Fase 4: el ajuste por XI deja de esperar a diciembre

Diagnóstico: todo estaba construido (captura de XI cada 5 min, challenger,
cuatro brazos en sombra) pero el challenger nunca se había entrenado. Exige
700 partidos con predicción sellada + XI capturado antes del inicio, y había
4 y 21 (modelo activo desde el 27-sep, XI desde el 26-sep). En vivo llegaría
hacia diciembre.

Decisión del USUARIO (única excepción al punto en el tiempo, y acotada):
alineaciones descargadas después del partido, en `lineups_historicas`
(db/034), que SOLO lee el entrenamiento/validación del challenger. La
predicción diaria, la sombra y `availability()` siguen con XI capturados
antes del partido; hay un test que falla si alguno de esos módulos nombra la
tabla. La promoción sigue exigiendo CLV en sombra.

- Base: las predicciones fuera de muestra que `train.py` YA calcula (walk-
  forward del último año, sin coste extra), ahora con la rho de su paso.
- Una fila sellada con UN lado histórico no cuenta como sellada: su hora de
  XI queda vacía y la regla estricta la descarta.
- Encontrado de paso: si nadie tenía 3 XI previos, las features salían sin
  columnas y el cruce reventaba; `train.py` lo tapaba como "no se pudo
  preparar". Ahora devuelve "collecting" con su motivo real.
- Un reentreno no promovido guardaba el challenger con otra versión y el
  brazo de la sombra se quedaba sin artefacto: ahora usa el último validado.
- La cuota restante de API-Football llega como TEXTO en la cabecera; la
  primera pasada murió comparándola con un número (46 peticiones perdidas).

- Resultado de la descarga: 4.555 partidos con XI (0 vacíos), 3.988 con 3
  XI previos por equipo dentro del último año, entre 288 y 508 por liga. Las
  copas no emparejaron (sus rivales no están en el catálogo); no hacen falta.
  No se fuerza el entrenamiento: el mensual del 1-oct lo incluye y no hay
  partidos de estas ligas hasta el 9-oct (parón de selecciones).

## 2026-10-01 — Cadena del XI en vivo: funciona, pero el XI llega a T-25

Auditoría de los partidos de los últimos 30 días en ligas con modelo:

- Solo 21 de 397 tenían XI. No es un fallo: las europeas jugaron por última
  vez el 20-sep y la captura en vivo de The Odds API empezó el 24-sep; los 21
  son de MLS y Liga MX. Las europeas vuelven el 9-oct.
- 17 de esos 21 no tenían predicción porque no hubo modelo activo hasta el
  27-sep 06:21 (el de 24-sep no se activó). Desde entonces, 4 de 4 partidos
  con XI recorrieron toda la cadena: predicción 08:00 → XI → cuotas
  `post_xi` → sombra (`baseline_t60`, `baseline_market`). Faltaba el brazo de
  XI solo porque no había ajuste validado (resuelto hoy).
- Hallazgo importante: el XI se guarda a T-25 en 22 de 22 partidos, aunque se
  consulta cada 5 min desde T-90. El cliente no tiene caché; es el
  proveedor (su guía: 20-40 min antes). Con el XI a T-25, Pinnacle ya ajustó
  y la ventaja temporal de la recomendación 1 casi desaparece. Siguiente paso:
  medir la antelación en europeas desde el 9-oct antes de pensar en otra
  fuente.

- Prueba en vivo (Seattle–Sporting KC, 2-oct 01:30 UTC): XI a T-24, cuotas
  `post_xi` a T-20 con 21 casas, sombra a T-19 con `baseline_t60` y
  `baseline_market`. Los brazos de XI NO se registraron aunque el ajuste está
  validado: `availability()` exige 3 XI previos del equipo en la tabla en
  vivo `lineups` (existe desde el 26-sep) y devuelve "historia
  insuficiente". Las europeas empiezan de cero el 9-oct: el brazo de XI no
  medirá nada hasta ~finales de octubre. Completar esa historia con
  `lineups_historicas` ampliaría la excepción del usuario (hoy solo
  entrenamiento): queda a su decisión.

## 2026-10-01 — Criterio de ECE del XI: ruido, no orden (decisión del usuario)

Opción B elegida por el usuario. Antes: el XI se validaba solo si
`ECE_después <= ECE_antes`. Ahora: remuestreo pareado por partido (1.000,
semilla 0) de ECE_después − ECE_antes; solo "empeora" si el percentil 2,5 %
es > 0. Se informa `ece_delta_ic95` y `ece_empeora`. RPS, log-loss y ≥2 ligas
no cambian.

- Por qué: simulado con base variable y 3.600 filas, una señal real pasaba la
  puerta antigua 2-6 de 8 veces; con la nueva, 8-10 de 10 (efecto 0,1-0,4).
  Ruido puro: 0 de 10 con 1 señal, 1 de 10 con 14 (frenan RPS, log-loss y
  ligas; y la sombra todavía exige CLV antes de publicar nada).
- Transparencia: el criterio se cambió después de ver que el XI simple
  fallaba solo por el ECE (+0,00055). La regla es la estándar (no
  significativo al 95 %), no un umbral ajustado a ese número, y aplica igual
  a los brazos de la fuerza por jugador (XI con valor sigue sin validar:
  falla por RPS y log-loss).
- Reevaluado con `python -m qf.model.lineup_challenger` sobre
  `oos_2026.10.01-030007.pkl` (mismos números que el reentreno: el ajuste es
  determinista): IC95 del cambio de ECE [−0,00741, +0,00582], `ok: true`.
  `lineup_2026.10.01-030007.pkl` reescrito; el anterior, en
  `~/respaldo_20261002_b1/`. `model_artifacts.val_metrics` no se reescribe:
  conserva lo que dijo el reentreno con el criterio de entonces.

## 2026-10-01 — Reentreno mensual y fuerza por jugador (Fase B1)

Reentreno 2026.10.01-030007: NO se activa ("No mejora el baseline Elo sobre
las mismas filas"; RPS 0,20074 en 1.107 filas). Sigue activo 2026.09.27.
El walk-forward se guardó (`oos_2026.10.01-030007.pkl`) y sirvió para la B1
sin repetir 3,5 h de entrenamiento.

XI simple (3.650 filas, 2.555 ajuste / 1.095 validación): RPS 0,21817 →
0,21678, log-loss 1,05235 → 1,0479, 8 de 11 ligas mejoran, pero ECE 0,03041 →
0,03096: queda `shadow_only`. La sombra no tiene ningún XI validado.

Fuerza por jugador B1, mismas 3.645 filas para los tres brazos:

| brazo | RPS | log-loss | ECE | ligas |
|---|---|---|---|---|
| base | 0,21818 | 1,05317 | 0,03125 | - |
| XI simple | 0,21677 | 1,04868 | 0,03182 | 8 |
| XI con valor | 0,21912 | 1,05654 | 0,03705 | 1 |
| XI con nota | 0,21801 | 1,05274 | 0,03175 | 8 |

- "XI con valor" empeora a la base: 18 señales (9 estadísticas por lado)
  sobreajustan con 2.551 partidos. Saber QUIÉN falta, medido por sus
  estadísticas, no añade nada a saber CUÁNTOS habituales faltan. Según el
  plan, no se escribe la B2. No se probaron variantes sobre la misma
  validación: elegir la que salga mejor sería ajustar al 30 % de prueba.
- La nota del proveedor (solo comparación) tampoco supera al XI simple.
- El test de "valor gana" de la B1 se reescribió con informes controlados:
  con validación de 300 filas el ECE de dos brazos se ordena casi al azar
  (simulado: señal real fuerte pasa 2-6 de 8 veces; sin señal llegó a pasar
  1 de 6 con 1.000 filas). Eso mismo afecta al XI simple real: decisión
  del criterio pendiente del usuario (ver tareas).
- `shadow._challenger_validado` ahora exige `features == LINEUP_FEATURES`:
  los artefactos `lineup_valor_` / `lineup_nota_` comparten el patrón
  `lineup_*.pkl` y uno validado en el futuro se habría cargado como XI simple.
- La revisión programada del 1-oct quedó colgada en "running" sin actividad;
  esta revisión se hizo a mano.

## 2026-10-03 — FotMob: mismo xG que Opta, disponible en horas y con LatAm

Pregunta del usuario: ¿llega antes por FotMob? Comprobado en su JSON
público (solo lectura, desde el navegador): los 6 partidos recientes sin xG
en API-Football lo tienen en FotMob, incluido Boca–Unión jugado horas
antes; y cubre Liga MX y Argentina, que en API-Football casi nunca lo
traen. Contra el xG de FBref guardado (17 partidos de 2024, 6 ligas):
diferencias de 0,00-0,05 en 32 de 34 valores; dos de 0,2 y 0,6 (Premier y
LaLiga), probablemente el valor de un penalti. Sin retraso, además, no hay
la fuga de backtest que traería el xG tardío de API-Football.

## 2026-10-03 — El xG de API-Football: fiable cuando está, irregular en cuándo

Pregunta del usuario: ¿no sirve el proveedor ya contratado? El README lo
prohibía (22-sep) por cobertura irregular y vacíos mudos. Medido, solo
lectura, ~350 peticiones:

- **Valores: los mismos que FBref/Opta.** 2024, 15 partidos por liga
  emparejados con el xG guardado: correlación 0,963 (Argentina) a 1,000
  (Serie A), medias casi idénticas, diferencia media 0,01-0,09 por equipo.
  Muy probablemente el mismo proveedor (Opta): se puede empalmar sin
  romper la serie.
- **Cobertura: irregular por liga, temporada y fecha.** 2024: completa en 8
  ligas europeas, Brasil y MLS; Argentina 5/15; Liga MX 0/15. Temporada en
  curso, muestra al azar: casi todo con xG salvo Argentina (1/6). Pero los
  partidos RECIENTES no lo tienen: MLS 0 en los últimos 6,6 días, Liga MX 1
  de 14 en dos semanas, Argentina 0 de 14; LaLiga y Premier sí a 13 días.
  Llega con retraso de días o semanas, y en las americanas puede no llegar.
- Consecuencia de diseño si se adopta: no basta con leerlo al cerrar el
  partido (`results.py` lo pide a +105 min y por eso no lo tenía); hay que
  volver a pedirlo durante semanas. Y en backtests el xG de las últimas
  ~2 semanas no existía en el momento de predecir (`check_leakage` avisa de
  xG registrado >6 h tarde): fuga pequeña, pero real.

## 2026-10-03 — El xG aporta: merece una fuente nueva

`eval/xg_value.py`, regla fijada antes de ver nada. Mismo walk-forward
(reajuste cada 30 días, solo pasado) con `xg_blend` 0,65 frente a 0; cada
reajuste tardó ~18 min, así que se lanzaron los cuatro brazos en procesos
aparte (6 h). `check_leakage`: solo el aviso genérico de que las cuotas son
cierre, y aquí no se usan como variable.

- Ventana A (xG existía, 6.785 partidos, 84 semanas): RPS 0,20154 frente a
  0,20440; delta −0,00287, IC95 [−0,00376, −0,00200]; mejora en 12 de 13
  ligas (solo la Europa League, n=66, empeora). Veredicto: `xg_aporta`.
- Ventana B (hoy, 3% de partidos de test con xG): −0,00055 [−0,00100,
  −0,00018], 8 de 13 ligas. Lo que queda es la historia vieja con xG en el
  entrenamiento, que se diluye con la media vida.
- Lectura: 0,0029 de RPS es lo mismo que Dixon-Coles saca a Elo y ~40% del
  hueco con Pinnacle (0,0068). Perderlo para siempre no es neutral. Pero el
  modelo no elige los picks: esto mejora el modelo, no la puerta comercial.

## 2026-10-03 — Cerradas las fugas del criterio de la fase 3

Con el sí del usuario: `/matches/{id}` sin `market_consensus`, sin
`/openapi.json`, y opción (b) para la cadena: el lote deja de llevar el
precio justo desde el 3-oct. Se descartó reescribir el formato hacia atrás:
un lote pasado regenerado desde la base tiene que dar el hash sellado, y es
lo que hace verificable la cadena; por eso la fecha de corte vive en el
código (`LOTE_SIN_CONSENSO_DESDE`). Comprobado en producción con el lote del
2-oct.

Al tocar `hashchain.py` apareció el problema mayor: el lote lleva también
los picks, de pago incluidos, y el flujo documentado lo sube a un repo
público ANTES de los partidos. (b) no lo resuelve; lo resolvería publicar
solo el hash antes y el JSON después (comprometer-revelar). Queda como
decisión del usuario en tareas; hoy no ocurre porque no hay remoto.

## 2026-10-03 — Auditoría de la fase 3 (solo lectura, contra producción)

- **Bien:** Cloudflare Access cierra `/control`, `/admin` y Grafana en los
  tres dominios, y una cabecera `Cf-Access-Jwt-Assertion` falsa no lo salta
  (Access valida en el borde; Caddy solo comprueba que exista). `/v1/*` sin
  token da 404; el panel exige PBKDF2 600k y token de 64. Puertos: solo 22,
  80 y 443 públicos; 8000 y 3000 en 127.0.0.1. CORS rechaza orígenes
  ajenos. El limitador corta en 60/min por IP (ventana fija: hasta 2x en el
  cambio de minuto). El JavaScript solo llama a rutas públicas. La ficha
  `/web/partidos/{id}` no lleva cuotas ni probabilidades.
- **Fuga del criterio:** `/matches/{id}` devuelve `market_consensus` (justo
  sin margen) y los lotes sellados también lo llevan. No hace daño hoy (no
  se vende ni se publica la cadena), pero es exactamente lo que se quiso
  cerrar el 28-sep. Pendiente de decisión del usuario (tareas.md).
- Menores: `/openapi.json` público con las rutas privadas, rutas internas en
  `/model-card`, sin CSP, y ningún aviso legal (+18, juego responsable,
  privacidad, términos) en la web.

## 2026-10-03 — Antelación de la decisión y rescate del cierre

Las dos primeras mejoras de la auditoría, con el sí del usuario.

- **Una sola `MIN_LEAD` para sombra y publicación, aplicada al precio Y a
  la decisión.** Al leer el código apareció algo peor que lo auditado: la
  publicación real no tenía ninguna guarda de antelación. La puerta
  certifica "lo que se habría publicado", así que la regla tiene que ser la
  misma en los dos lados; la constante vive en `picks.py` y la sombra la
  importa, para que no puedan divergir.
- **Rescate del cierre desfasado 5 min, solo `close`.** Se descartó mover la
  ventana o tomar un "precierre" de respaldo: cualquiera de las dos cambia
  la vara de la puerta. Con el rescate la vara es la misma (último precio a
  3-12 min) y hay dos intentos; el registro de captura evita pagar dos veces.
- Desplegado sin reiniciar el worker (`docker compose cp` + recargar el
  crontab montado) para no cortar la medición del xG; API reconstruida.

## 2026-10-03 — Auditoría de las fases 0, 1 y 2 (solo lectura)

Recalculado de forma independiente contra la base de producción, no leído de
los informes del propio sistema.

- **Fase 0, limpia.** 0 precios fuera de rango, 0 ternas 1X2 incompletas (de
  5.129), 0 duplicados, 0 snapshots posteriores al inicio; Pinnacle dentro
  del consenso en los 49 cierres; cierre a 4-9 min. Toda ventana que falta es
  de partidos dados de alta con <72 h (LaLiga 2 el 25-sep, Brasil B el
  28-sep) o reprogramados. Riesgo anotado, no fallo: la ventana `close`
  (3-12 min) cae en UNA pasada del cron */10; si esa pasada falla, el
  cierre se pierde y la oferta no cuenta para la puerta.
- **Fase 1, limpia salvo lo ya sabido** (xG parado). 0 clubes duplicados
  por `af_team_id`, 0 equipos bajo `eu.*`, 0 partidos duplicados, 0 equipos
  en dos partidos a <40 h; 10 de 10 partidos con predicción sellada antes del
  inicio; cadena de hashes verificada (4 lotes). Arreglado: `fixtures.run()`
  contaba los clubes de copa fuera del catálogo como incidencia; con
  Telegram activo habría avisado dos veces al día por algo esperado (mismo
  criterio que `check_unresolved_names`). Desplegado con `docker compose cp`
  para no matar la medición del xG en curso; el próximo build lo incluye.
- **Fase 2, los números de la sombra son correctos.** 165 de 165 precios
  justos de entrada reproducidos (Shin sobre el snapshot de Pinnacle del
  mismo instante; en API-Football el snapshot es `provider_updated_at`, no
  `fetched_at`); 89 de 89 EV al cierre idénticos; 0 resultados o
  beneficios mal liquidados; publicables una por partido, solo SOFT_BOOKS,
  decididas 8-71 h antes con precios de ≤5,2 h. Matiz: la guarda de 15 min
  mira la hora del PRECIO, no la de la decisión; 3 ofertas se decidieron a
  <15 min (ninguna de SOFT_BOOKS, no cuentan). Publicación pausada
  (`PUBLISH_PICKS_ENABLED=0`, `picks` vacía).

## 2026-10-02 — Copas recuperadas y chequeo de xG que mira el dato

`worldfootballR_data` lleva parado desde sep-2025 (dic-2024 en copas): el
modelo entrenaba solo con goles en los últimos meses y sin ningún partido de
copa de 2025/26. Decisión del usuario: recuperar copas y vigilar el xG; la
fuente de xG nueva queda pendiente.

- Copas desde API-Football, por el camino ya probado (insertar como
  programado, cerrar con `close_recent`). Ensayo en seco primero; la carga
  real coincidió partido a partido (351, 0 duplicados, 0 errores). Guarda de
  duplicados nueva en las cargas hacia atrás (misma competición y equipos,
  ±36 h): `matches` no tiene clave natural y lo que cuelga de un partido no
  se borra. Rangers→Angers (92) o Wolfsberger→Wolfsburg (80) confirman por
  qué en copa solo vale la coincidencia exacta.
- `check_xg_freshness` con reconocimiento CON CADUCIDAD (1-nov): sin ella
  el chequeo alertaría a diario por algo ya sabido —y se aprende a ignorar
  las alertas, que es como se perdió la de bajas—; sin caducar, escondería
  el problema para siempre como hizo el `ok` con 0 filas del job.

## 2026-10-02 — La alerta de bajas saltó cuatro días y no la vio nadie

Reconstruido con los datos de cada mañana: `check_injuries_coverage()` falló
el 28, 29 y 30-sep y el 1-oct (`us.mls` 16-17 partidos, 0 bajas). Tres
agujeros en cadena:

- **Ningún canal.** `health.run()` llama a `telegram.alert()`; sin
  `TG_BOT_TOKEN` eso era un WARNING genérico "mensaje omitido". Afecta a los
  7 chequeos diarios y a las 8 llamadas a `alert()` del código, no solo a
  las bajas. Decisión del usuario: configurar Telegram SOLO para alertas a su
  chat privado (`TG_ALERT_CHAT`); los canales de picks siguen vacíos, así que
  no se publica nada por ahí. Sin canal, `alert()` deja ahora el texto
  completo como ERROR.
- **Log efímero.** El cron escribía en `/var/log` del contenedor, que se
  borra en cada despliegue (dos ese mismo día). `/var/log` del worker es ahora
  el volumen `workerlogs`, y cada pasada del cron queda en `health_runs`
  (db/037). El panel y `/admin/health` no escriben historial.
- **Mensaje que invitaba a archivarlo.** Decía "mismo patrón de cobertura
  silenciosa que mx.liga_mx…", es decir, culpaba al proveedor. Ahora pide
  descartar antes un error nuestro.

Al activar Telegram aparecían dos riesgos nuevos, cerrados antes: el envío
es HTML y un "5 < 300" sin escapar hacía rechazar el mensaje; y un fallo de
Telegram propagaba la excepción al job que avisaba. Comprobado de paso: los
tres huecos conocidos de `/injuries` (Liga MX, Argentina, Primeira) son
reales (la API devuelve 0 por partido); Brasil sí trae datos.

## 2026-10-02 — La historia del XI en vivo sale también de lineups_historicas

Decisión del usuario, ampliando la excepción de db/034. `availability()`
exige 3 XI previos por equipo y solo miraba `lineups` (en vivo desde el
26-sep): el brazo de XI no habría medido nada en las europeas hasta finales
de octubre.

- Por qué no rompe el punto en el tiempo: lo que se toma de la tabla es el
  XI de partidos YA JUGADOS antes del de hoy, que era público antes del
  partido que se predice. Lo que sigue exigiendo captura previa al inicio es
  el XI de HOY, que solo sale de `lineups`. La predicción diaria y lo
  sellado no leen la tabla (test por AST en `test_lineups_historicas.py`).
- Coherencia: el entrenamiento del challenger ya construía la historia con
  las dos tablas; la sombra ahora calcula la variable igual.
- Si un partido está en las dos tablas manda el capturado en vivo; solo XI
  completos (≥11), como en el entrenamiento. `n_history_historico` dice
  cuántos XI de la historia salieron de la tabla histórica.
- Desplegado (worker + db/036, que solo cambia el COMMENT de la tabla;
  respaldo en `~/respaldo_20261002_historia/`). Verificado: el
  Seattle–Sporting KC pasa de "historia insuficiente" a 5 XI previos por
  lado (4 históricos); 257 de 262 equipos con partido en 14 días tienen ≥3.

## 2026-10-02 — Las bajas nunca se guardaron: id de API-Football contra id interno

`injuries` estaba vacía tras 521 comprobaciones en 51 partidos (22-sep a
2-oct), sin un solo error. `_side_of()` comparaba `team.id` de la respuesta
(API-Football, p. ej. Seattle = 1595) con `matches.home_team_id` (interno,
49060): nunca coincidía y cada baja se descartaba con `continue`. Comprobado
con una llamada real: 26 bajas en el Seattle–Sporting KC, las 26 perdidas.

- Arreglo: `pending_matches()` trae `teams.af_team_id` de ambos lados y se
  compara contra eso (`tests/test_injuries.py`). Ningún equipo de las ligas
  con modelo con partido en 14 días tiene `af_team_id` nulo.
- Lo que se descarte a partir de ahora deja un WARNING y cuenta en
  `discarded`, también en el `record_health` de la pasada: un descarte
  masivo ya no puede volver a pasar mudo.
- Lo perdido no se recupera como dato point-in-time: pedir hoy las bajas de
  un partido pasado da la foto de hoy, no la que se conocía antes del
  partido. No se rellena; la muestra válida empieza el 2-oct.
- Desplegado (solo `worker`; respaldo del archivo anterior en
  `~/respaldo_20261002_injuries/`). Verificado en producción: el
  Seattle–Sporting KC guarda 26 bajas, 0 descartadas.

## 2026-09-30 — Fuerza por jugador, Fase A: los datos

Diseño aprobado por el usuario sección a sección (valor por contribución por
90 min con decaimiento, encogimiento por posición y pesos estimados solo con
el tramo de entrenamiento; la nota del proveedor solo como comparación;
plus-minus descartado por coste y ruido con esta muestra). Calendario del
usuario: datos ahora, modelo después del reentreno del 1-oct, para poder
compararlo con el XI simple.

- No necesita excepción al punto en el tiempo: son estadísticas de partidos
  ya jugados; la Fase B solo usará, para el día D, partidos anteriores a D.
- `estadisticas_jugador_log` registra también los intentos vacíos: sin él,
  cada pasada reintentaría para siempre los partidos que el proveedor no
  cubre (hubo 11).
- El lado de cada bloque se decide por el id de equipo de API-Football, no
  por el orden (en `/fixtures/players` no está garantizado).
- Descubierto en los datos: el campo `substitute` del proveedor no es fiable,
  hay lados con 16 "titulares". La Fase B tomará el once de las alineaciones.
- Coste diario nuevo: 1 petición por partido cerrado en ligas con modelo.

## 2026-09-25 — Más volumen: medir antes de cambiar el criterio

Decisión: el umbral del 2%, un pick por partido, la referencia Pinnacle/Shin
y la publicación pausada NO cambian. El histórico puede descubrir variantes,
pero ya se utilizó para diseñar la estrategia: no sirve para certificarla.

- `eval/quote_coverage.py` informa la primera terna 1X2 completa observada
  por casa/fuente/liga, antelación y edad del precio cuando se conoce.
  The Odds API no conserva aún `last_update` del bookmaker: edad desconocida
  se deja nula, no se inventa cero. Hace falta ejecutarlo contra Postgres
  operativo antes de gastar más cuota en capturar antes de T−72.
- `eval/sharp_challengers.py` usa los 42 CSV ya cacheados, 7 ligas y seis
  temporadas, hash `59586239a2169a51b9a864f3655c6e5cdc4c8d68f18a1ccdcc2b69b2408f6118`.
  Compara Shin y Power sobre los mismos 14.294 partidos 1X2 y mide TODOS
  los brazos contra el MISMO cierre Pinnacle/Shin. Power apenas mejora el
  log-loss temprano (0,960347 frente a 0,960392) y el RPS (0,193120 frente
  a 0,193131): magnitud insuficiente para cambiar la referencia.
- Con la lista blanca actual y un pick potencial por partido, Shin al 2%
  deja 286 partidos, EV al cierre justo +3,788%; al 1% deja 530, con 244
  partidos nuevos cuyo EV histórico es +2,499% (IC95 por semanas
  [1,915, 3,071]). 502 de los 530 candidatos al 1% dependen de 1xBet.
  El umbral dinámico predefinido (1,5% <1,80; 2% 1,80–3,49; 3% ≥3,50)
  deja solo 233 partidos: no cumple ni el objetivo de más volumen.
- Esto es un proxy offline: no hay timestamp exacto de decisión, acceso
  regional, límite de stake, cuota todavía disponible ni tope diario en los
  CSV. La persistencia por casa se estimó al 2% y no se recalibró para el
  1%. La puerta en sombra, con precio verificable al cierre, sigue mandando.

## 2026-09-24 — La temporada 2026/27 no existía en siete ligas

Síntoma: el `--bootstrap` rechazaba cada noche ("mercado de 252 días") y la
puerta no tenía nada que liquidar. Causa: tres piezas correctas por separado
que dejaban un hueco entre ellas. `backfill()` acababa en 2025/26 por un rango
fijo; `fixtures` solo crea partidos futuros; `results` solo cierra 72 h. Lo
jugado entre el último histórico y el primer calendario no lo creaba nadie.

Decisiones:

- El histórico llega al año en curso, no a la temporada europea en curso:
  Brasil y Argentina etiquetan '2026' lo que juegan en mayo.
- Antes de insertar, `_ingest_rows` busca el mismo partido por liga, equipos
  y ±36 h, y si existe salta la fila ENTERA. El match_id no sirve de guarda:
  API-Football etiqueta la temporada '2026A'/'2026' y escribe otros nombres.
  Y las cuotas de cierre no tienen clave única y `odds_snapshots` no admite
  DELETE: una recarga sin esta guarda las habría duplicado para siempre (el
  ensayo lo confirma: 531 partidos ya cargados habrían vuelto a entrar).
- Racing Santander como alias (`db/021`), no como club nuevo: la guarda
  compara por team_id y un club duplicado la esquiva.
- Cargado en producción (991 partidos, 0 duplicados). No destraba el modelo:
  los CSV no traen Pinnacle desde enero de 2026, así que la frescura del
  mercado sharp depende SOLO de la captura en vivo. Suposición corregida: se
  esperaba que el cierre del CSV bastara.
- Las 17.385 cuotas de cierre repetidas de recargas antiguas no sesgan nada:
  son copias exactas (mismo precio) y todo lector del cierre toma un precio
  por selección. Se documentan y se dejan: la tabla es inmutable a propósito.
- Pendiente aparte, cosmético hoy: la columna `season` no es coherente entre
  fuentes en ligas de año natural ('2627' histórico, '2026'/'2026A'
  API-Football). Ningún cálculo del modelo la usa.

## 2026-10-03 — Investigación NBA 2026-27 y Telegram inmediato

El usuario pide incorporar NBA mediante investigación profunda, literatura
académica y experimentos, y aclara que las señales llegarían al instante por
Telegram. Se incorpora también su archivo `Texto pegado.txt`. Documento:
`docs/nba_2026_27_investigacion_y_plan.md` (21 experimentos E0–E20).

Decisiones de diseño, todavía sin implementación ni resultados propios NBA:

- La entrega por Telegram cambia la antigua restricción de web para esta
  ampliación. La rapidez real depende además del feed y de cuándo apuesta
  el cliente; medir supervivencia de ventaja y no asumir ejecución instantánea.
- Props de rebotes/asistencias/puntos y totales entre periodos son hipótesis
  experimentales. La literatura respalda posesiones, minutos, rotaciones y
  actualización, pero no un ranking contemporáneo garantizado de rentabilidad.
- Corregidas afirmaciones del texto sobre regresión inevitable, eliminación
  universal de garbage time, transferencia fija de USG y ventaja cuántica NBA.
  Box score, regímenes competitivos/paliza y resultados liquidables se separan.
- La infraestructura de fútbol conserva sus puertas/triggers/publicación.
  NBA requiere contratos/jugadores/periodos, guard point-in-time para live,
  liquidación y política de promoción propias; no convertir puntos en goles
  ni importar persistencias o requisitos de tres ligas sin validación.
- Propuesto worker dedicado con sellado y outbox, revalidación, caducidad e
  historial de envío. No se activó ni envió Telegram, no se consultaron APIs
  de pago, no se desplegó ni se modificó código de producción.
- Fuentes y límites de lectura explicitados: algunos trabajos se verificaron
  por abstract/metadata, otros con texto completo. No presentar beneficios
  antiguos como expectativa 2026 ni precisión deportiva como ventaja de cuota.
- Revisión AST correcta de 74 archivos Python. El arnés Bash no ejecutó
  pruebas en este entorno; su mensaje OK no se toma como validación completa.
  La venv local apunta a un intérprete no disponible. Cambio documental.

## 2026-10-03 — Revisión de certeza y segundo texto NBA

- El nuevo texto mezcla autores (Shannon/Thorp con Dixon–Coles), confunde
  recencia con deterioro de habilidad y atribuye al EPV original tecnología
  distinta de la documentada. Ver secciones 22–26 del plan NBA para fuentes
  y correcciones; las cifras privadas de rentabilidad no validan una estrategia.
- Se prioriza fiabilidad antes de complejidad: cálculo bayesiano, calibración
  temporal con mercado, selección con abstención y réplica prospectiva.
  El plan pasa de 21 a 27 experimentos propuestos, E0–E26, sin resultados
  nuevos ejecutados. Fijar política antes del test y medir el subconjunto elegido.
- Conformal aporta cobertura bajo condiciones, no probabilidad de cobrar
  ni ROI. La extensión a pérdidas no monótonas de febrero de 2026 se incluye
  como preprint exploratorio, con resumen consultado y supuestos por auditar.
  Kelly robusto/restringido trata asignación y riesgo; no crea ventaja.
- Para Telegram, contrato, cuota mínima y caducidad medidos mandan sobre
  etiquetas de confianza. Acuse de envío no confirma ejecución y la captura
  por minutos no se vuelve instantánea por un modelo más moderno.
- Solo documentación y backlog: no envío de Telegram, llamadas de pago,
  cambios de producción ni modificación de trabajos FotMob concurrentes.
  Revisados IDs de experimentos, secciones, referencias y cálculos ilustrativos;
  no se ejecutaron nuevos modelos ni pruebas de código por este cambio.

## 2026-10-03 — Arquitectura NBA aislada del fútbol

- A partir de la preocupación del usuario por mezclar componentes, se
  documenta aplicación NBA independiente en `apps/nba/`, aún inexistente,
  con entorno, imagen, despliegue, persistencia y Telegram propios.
  Documento: `docs/nba_arquitectura_aislada.md`.
- La frontera incluye ejecución y permisos, no solo carpetas: no importar
  `qf.config`/`qf.db`, no compartir cron, DSN, artefactos o migraciones.
  Esos módulos cargan configuración o conexiones de fútbol; acoplarlos
  introduciría rutas implícitas hacia el sistema existente.
- Se recomiendan instancias Postgres y Redis NBA propias. La outbox durable
  va en Postgres; la caché futbolística usa allkeys-lru. Dependencias propias
  evitan que una actualización NBA cambie el runtime de fútbol.
- Un mismo VPS y una cuenta de proveedor conservan riesgos compartidos.
  Fijar límites de recursos/retención y verificar el ámbito de créditos;
  prefijos de claves o dos contadores independientes no aíslan esos límites.
- Plan y backlog actualizados; solo documentación. No se crearon servicios,
  se movió código, se instalaron dependencias ni se modificó producción.
  Criterios de aceptación de permisos, imports, fallos y carga documentados;
  su ejecución queda pendiente de la implementación.

## 2026-10-03 — MVP NBA y capacidad comercial de las señales

- La crítica del usuario aporta un criterio operativo útil: precio correcto
  y disponible para el cliente, además de precisión deportiva. Documento:
  `docs/nba_mvp_ejecucion_y_capacidad.md`; resumen en sección 27 del plan.
- Cadencia de props de 60 s verificada en documentación de The Odds API.
  Rangos USD 20–250, colapso en 45 s, reacción 5–30 s y secundarios 2–5 min
  no corroborados por fuentes primarias suficientes: medirlos, no prometerlos.
  Polling y noticias tienen tiempos distintos; snapshots de 60 s no permiten
  asignar una duración exacta de 45 s a una oferta.
- MVP reduce familias/operadores y mantiene PIT transversal, minutos/tasas,
  calibración E22/E23 mínima, precio E5/E17 y entrega E19. Noticias E7/E8
  después del núcleo; los 27 experimentos siguen como backlog científico.
- No hay minutos implícitos únicos deducibles de una prop, ni una cuota
  mínima universal de 1,83. Cambio de línea requiere nueva evaluación.
  Beneficiarios secundarios son hipótesis, no ventana garantizada.
- Medir ejecución/capacidad/utilidad neta de tarifa con datos reportados
  voluntariamente, registrando faltantes y sesgo. Replay sin volumen real
  no identifica impacto de suscriptores sobre el mercado. Reglas de oferta
  por jurisdicción; Bonus Bets no equivalen a devolución de efectivo.
- Objetivo de inicio propuesto: captura y sombra, condicionado a preparación.
  Mantener puertas NBA y separación respecto a fútbol. Solo documentación;
  sin implementación, Telegram, gasto de API ni apuestas. Comprobados enlaces
  locales y consistencia de ejemplos, sin ejecutar modelos o tests de código.

## 2026-10-03 — Plan maestro NBA por fases y auditoría

- Consolidado lo solicitado en `docs/nba_plan_fases_auditable.md`: F0–F9,
  37 tareas, 10 puertas, entregables, dependencias, criterios de evidencia,
  roles de revisión y E0–E26 asignados. Referencias anteriores conservadas;
  el plan maestro dirige el MVP y el orden de implementación.
- Registro inicial en `docs/nba_plan_fases_auditoria.json` con hashes SHA256
  de cuatro documentos y commit de referencia. Se declara que el workspace
  tiene cambios locales; ese commit no se presenta como implementación NBA.
  Cero ejecuciones y cero puertas aprobadas. Integridad de un hash no equivale
  a prueba de fecha/origen; anclaje prospectivo se define en F3.
- Aislamiento, datos/PIT, minutos, distribución/calibración, Telegram de
  pruebas y confirmación prospectiva forman el núcleo. F8 estudia noticias
  como challengers separados; F9 amplía con validación propia por mercado.
  Una variante no cambia el candidato bajo confirmación ni hereda su puerta.
- Piso 300 partidos/60 días/3 bloques conservado como propuesta de muestra,
  no demostración de ROI ni calendario de ventas. La apertura de temporada
  referencia captura; no sustituye evidencia. Presupuesto/canal/familia y
  métricas definitivas se registran como entradas pendientes.
- Verificación documental: JSON válido, 37 IDs de tareas coinciden con el
  plan, E0–E26 completos, dependencias sin ciclos, cuatro hashes correctos
  y enlaces locales existentes. No se ejecutaron modelos ni tests de código.
- Solo documentación/backlog. `apps/nba/` sigue sin existir; no despliegue,
  captura pagada, Telegram ni colocación de apuestas. El arnés local debe
  resolverse antes de futuras tareas de código, según instrucciones del repo.

## 2026-10-04 — Viabilidad NBA antes del inicio de temporada

- Usuario consulta si el modelo puede funcionar antes del inicio mediante
  descarga de históricos. Revalidado calendario oficial: 20-oct-2026,
  16 días desde fecha del cliente. `apps/nba/` sigue inexistente; registro
  declara not_started, cero ejecuciones y cero fases aprobadas.
- Un MVP deportivo reducido es un objetivo condicionado, no un compromiso
  de completar F0–F6 ni de ventaja comercial en 16 días. Priorizar box scores
  y minutos de 2023-24 a 2025-26, luego ampliar a 2021-22 según cobertura;
  rosters/calendario/disponibilidad actuales son necesarios para 2026-27.
- Históricos de cuotas/noticias y tracking tienen cobertura/acceso distintos.
  The Odds API documenta props desde 3-may-2023 a cinco minutos en planes
  pagados, sujeto a incorporación de deporte/casa/mercado. No gastar créditos
  ni afirmar cobertura total; las estadísticas deportivas pueden investigarse
  sin haber adquirido ese histórico de cuotas.
- Verificadas documentación de nba_api y pbpstats, no probado todavía acceso
  de descarga desde este host ni tiempo total. No presentar repositorios o
  documentación accesibles como ingesta completada. No se escribió código,
  inició descarga, activó Telegram ni cambió el registro de auditoría inicial.

## 2026-10-04 — Preparación del plan y complemento de pretemporada

- Revisados maestro y registro: fases, puertas y evidencia definidos;
  implementación pendiente. Añadido `docs/nba_pretemporada_arranque.md` tras
  indicación del usuario sobre la pretemporada. Recoger observaciones actuales
  y evaluar pronósticos experimentales sin mezclar métricas con regular/playoffs.
- Orden local: arnés/aislamiento, acceso y cobertura, captura actual/históricos
  recientes, baselines y distribución, ensayo de entrega, confirmación F7.
  Peso de señales de pretemporada requiere evaluación histórica temporal;
  no traslado directo de minutos ni garantía de mejora o fecha de entrega.
- Registro amplía documentación mediante complemento y cambio registrado;
  conserva hashes de la base original. Ninguna puerta se aprueba por este
  ajuste. Presupuesto, fuentes/cobertura, operadores y destino de Telegram
  se resuelven antes de sus tareas dependientes; trabajo local puede empezar.
- Cambios documentales solamente: no aplicación, descarga ni activación.

## 2026-10-04 — Revisión crítica de CLV, liderazgo de fuentes y QNN

- Analizado texto aportado en attachment c6f7385e. Fuentes primarias de
  scoring propio, QNN/benchmarking, NGBoost, glosario NBA y contratos/feed
  contrastadas. Referencias vagas a Stanford/Leiden y redirecciones del texto
  no constituyen tesis identificadas; no asumir que sus afirmaciones se probaron.
- Añadido complemento `docs/nba_revision_critica_clv_fuentes.md` con CLV como
  diagnóstico de mercado en F6/F7, sin desplazar pérdidas/calibración de F5.
  Definir referencia, cierre fresco, mismo contrato, margen, push/void y
  cobertura; cierre permanece fuera de features previas. Movimiento 2.00 a
  1.80 no acredita por sí solo probabilidad correcta o retorno favorable.
- Sharp/soft se reemplaza como regla universal por atributos/liderazgo medidos
  por mercado. E17/E7 investigan noticias, duplicación y tiempos censurados;
  feed de 60 s no permite inferir ajustes externos al segundo. USG% no es
  minutos; conservar disponibilidad/minutos/tasa/oportunidades separados.
- E20 sigue diferido; evidencia sobre barren plateaus y benchmarking no
  respalda aceleración general NBA. Corregida mención externa a F18 (solo E18
  existe). Base original y fases conservadas; complemento registrado sin
  aprobar puertas. Solo documentación, sin runtime NBA ni descargas/envíos.

## 2026-10-04 - Plan maestro NBA actualizado a 1.1

- Integradas correcciones en el propio maestro a peticion del usuario, con CLV complementario y protocolo de cierre/comparabilidad/margen, liderazgo por mercado y precision de tiempos.
- Incorporados pretemporada/historico reciente y separacion de regimenes; minutos, USG y oportunidades distintos; E20 sigue diferido con benchmarking completo.
- Version 1.0 y registro previo guardados byte por byte. Registro vigente sincroniza 37 tareas y amplía criterios pendientes, sin aprobar puertas ni declarar ejecuciones.
- Cambios solo documentales; no aplicacion NBA, descarga, despliegue ni envio Telegram. Verificacion documental independiente de los tests de runtime.

## 2026-10-04 — Ejecución NBA con fuentes gratuitas

- Usuario autoriza ejecutar el plan y confirma fuentes gratuitas. Creado
  `apps/nba` con entorno/dependencias/configuración/datos propios; no se
  importa `qf`, carga `.env` global ni toca DB/implementación de fútbol.
  Entorno raíz previo roto: se conserva y usa `.local/harness-venv` auxiliar.
  Arnés antes: 606 pruebas; después: 606 pruebas (73,82 s), Docker omitido
  por no estar instalado. Suite NBA: 22 pruebas correctas (1,38 s).
- Fuentes NBA oficiales: CDN 403, stats timeout. Sin evasión ni reintento
  ciego. A petición del usuario se investigan archivos GitHub reales:
  llimllib box scores recientes; shufinskiy jugadas/tiros desde 1996-97;
  hoopR box scores/calendarios ESPN hasta 2023. Descargas con commit/hashes.
  Índices/README que anuncian datasets ausentes no acreditan descarga.
- Auditoría revela llimllib individual 2022–2024 solo 15 partidos/año,
  duplicados y minutos `MM:60`. Se preserva raw y rechaza bajo el contrato
  inicial; no reparar en silencio. Duraciones inválidas permanecen en el
  denominador raw. Dataset normalizado: 67.066 filas, con cuarentena explícita.
- Protocolo local congelado para rebotes; benchmark retrospectivo condicional
  a participación, con todos los resultados del día excluidos del historial.
  39.334 observaciones/2.048 partidos. CRPS 1,3510 vs 1,3947, error de minutos
  4,9723 vs 5,0773. Detalle y límites en `docs/nba_arranque_resultados.md`.
  Esto no reconstruye disponibilidad previa ni demuestra EV/ROI ante casas.
- SQLite es almacenamiento de investigación explícito, no sustitución ni
  aprobación de Postgres/Redis/recuperación G1. Cadena local sin anclaje externo.
  Ninguna puerta completa aprobada; resultados/reportes con evidencia real
  sustituyen el estado inicial inexistente. Telegram/cuotas pagadas inactivos;
  no apuestas ni cuentas/fondos operados. Falta capturar contexto actual,
  resolver cobertura/IDs, calibrar y ejecutar confirmación prospectiva.

## 2026-10-05 — NBA: cubrir huecos con archivos GitHub auditados

- Priorizado archivo real frente a README/clientes. SportsDataverse release
  aporta 30 Parquet individuales 1996-97 a 2025-26 (1.041.847 filas, incluidas
  no participaciones). IDs/assets/digests y recepción local preservados. Cinco
  temporadas recientes cubren 1.230 partidos regulares; conciliación PTS/REB/AST
  mejora claramente, pero hay discrepancias y minutos MM:60 en cuarentena.
- Maezellemillan contiene todos los partidos pero no concilia muchos totales
  individuales: cobertura de partidos no demuestra censo completo de jugadores.
  Professor-Pete aporta 107.337 designaciones/1.165 snapshots de lesiones;
  falta validar PDFs, reloj/AMPM, IDs y corte temporal. No inventar recepción
  histórica; mantener NOT YET SUBMITTED como desconocido.
- Props: sample 2.505 filas NBA, 1.415 al inicio/después y 730 sin tiempos
  interpretables; 53 pasan filtro básico, ninguna contrato completo aprobado.
  Otras muestras son un día o carecen de identificación de partido. Sin ROI/CLV.
- Plantillas de tercero: 527 nombres, declara sync 1-sep; no valida todos los
  equipos actuales. Release de rosters sin 2027. nba_api es cliente no oficial
  y CommonTeamRoster no equivale a archivo histórico de lesiones.
- Documentado en docs/nba_fuentes_github_huecos_20261005.md, reporte JSON y
  NBA-RUN-004. Hashes verificados, registros anteriores preservados, puertas
  pendientes. Datos candidatos no integrados; sin cambios a aplicación/modelo,
  fútbol, Telegram ni apuestas. No se repitieron tests por ser datos/documentos.

## 2026-10-05 — Incremento NBA F1–F5 y arranque de temporada

- Integrados cinco años recientes SportsDataverse con fechas/IDs/tipos propios:
  154.058 registros, dataset por hashes separado. 2023-24 pasa de 15 a 1.159
  partidos regulares conciliados. 2025-26 pasa de 1.151 a 1.146: no reemplazar
  referencia por asumir superioridad. Minutos MM:60 y discrepancias siguen en
  cuarentena. Adaptador v2 cubre también participantes sin referencia de equipo;
  v1/v2 generan bytes idénticos, replay reutilizado por SHA256 comprobado.
- Capturadas 30 plantillas ESPN 2026-27, 606 jugadores y recepción UTC. IDs
  separados, sin unión aproximada. 78 lesiones raw, 36 con fecha >48 h; fecha
  no verificada como actualización. No inferir disponibilidad o salud de roster.
- Nueva evaluación referencia: 39.225 casos/2.044 partidos, CRPS 1,3519
  vs 1,3953. Sensibilidad entre fuentes: 36 resultados comunes difieren; comparación
  emparejada solo donde coinciden rebotes/minutos. Sin selección por scores.
- Experimento independiente startup-research-v0.1: priors del año anterior,
  primeras 10 apariciones observadas, excluye día objetivo y abstiene sin prior.
  8.264 casos/1.396 partidos, CRPS 1,3026 vs 1,3763; minutos MAE 5,3779 vs
  5,6229. Exploratorio (datos ya inspeccionados), sin sweep, rol/disponibilidad
  actuales ni EV/ROI. Escenario 2026-27 posible, siempre actionable=false.
- Recuperación local ensayada sobre checkpoint de 15 eventos y dataset; triggers
  y hashes preservados. No recuperación Postgres/Redis, raw completa ni anclaje.
  Código fuente final preservado en snapshot propio, evidencia anterior intacta.
- Arnés inicial: problemas de temporales, resueltos sin cambiar código de fútbol
  usando padre dentro del workspace y cacheprovider deshabilitado. Comprobación
  previa/final: 606 pruebas correctas; NBA: 47. Docker omitido por no disponible.
- Detalle en docs/nba_avance_fases_20261005.md y NBA-RUN-005..010. G0–G9
  pendientes. Faltan identidad/roles/disponibilidad, calibración y coherencia de
  equipo; después contratos/cuotas/outbox y Telegram de pruebas. Sin publicación.

## 2026-10-05 — continuación NBA, identidades/calibración/outbox

Se mantiene la abstención como resultado válido: el usuario autorizó continuar
las fases, pero la captura pública no acredita disponibilidad médica ni una cuota
accionable. NBA.com respondió con 619 identidades; 606 rosters ESPN se cruzaron
por nombre exacto normalizado y DOB independiente, obteniendo 596 equipos e IDs
concordantes. Diez quedan separados. Se capturaron 165 fichas (51,340,337 bytes)
y se ejecutó el capturador prospectivo de tres fuentes. De 596 cruces, 436 permiten
escenarios condicionales de arranque. Comparar el último equipo observado no
prueba rol actual; equipo previo desconocido se distingue de traspaso.

La calibración se comprueba contra masa discreta esperada, no solo 80% nominal:
8,264 observaciones/1,396 partidos reproducidos; cobertura 87.9356% frente a
masa 88.5199%, diferencia −0.5843 pp (IC por partido −1.2808 a +0.1703).
Sin fitting/promoción. El listado ESPN contiene 81 entradas no verificadas
para un partido; los enlaces oficiales 2026–27 consultados dieron 404. La
página de cuotas del partido muestreado solo ofreció totales de equipo: cero
props individuales validadas, sin generalizar a toda la fuente.

Decisión humana: compartir el bot de fútbol y TG_ALERT_CHAT. El enlace NBA
solo lee esos dos campos mediante configuración explícita, sin importar qf,
modificar su env ni copiar tokens. No hay credenciales activas locales. Outbox
NBA independiente: sellar antes de encolar, claim persistente antes de HTTP,
expiración con reloj real, no reintentar timeout ambiguo; prueba local sin envío.
La confirmación Telegram tampoco acredita recepción por suscriptor. Cuotas,
rol/disponibilidad, límites globales del bot y promoción prospectiva siguen
pendientes; el selector rechaza todos los picks comerciales actuales.

79 pruebas NBA y 606 de fútbol aprobadas después del código final; Docker no
está disponible. Copia de 31 archivos en code_snapshots/continuation_20261005,
ledger de investigación verificado y registro ampliado a 50 evidencias/15 runs.
Las puertas G0–G9 permanecen pendientes. Detalles y condiciones de avance:
docs/nba_continuacion_20261005.md. Se conservaron reportes intermedios y se
registraron correcciones de abreviatura, conteo de equipo previo desconocido,
entrada CLI y nombre del lockfile; no se sustituyó evidencia anterior.
## 2026-10-05 — Scrapers NBA y contexto adicional

Diez repos fijados por commit y 52 archivos verificados; ningún código de
terceros ejecutado. Se integran adaptadores NBA propios para observar
alineaciones públicas RotoWire y contrastar agregados PBP Stats por cuarto.
La captura actual aporta cinco partidos y 50 titulares previstos, sin
confirmación médica. El piloto histórico conserva 15 partidos/745 registros
de quintetos, incluidos dos tiempos extra en un partido; seis descargas 503
quedan registradas. No son secuencias cronológicas de cambios ni rebotes
individuales. Los dos calendarios nuevos tienen IDs/fechas, pero ninguna hora
de inicio; el PDF oficial actual devolvió 403 y no se intentó eludirlo.

Decisión: ampliar datos de minutos/roles sin convertir observaciones previstas
en elegibilidad o cambiar los parámetros del modelo. Las puertas siguen
pendientes. IDs de proveedores y ledger siguen separados de fútbol; el único
puente autorizado continúa siendo bot/chat de alertas, sin credenciales
activas locales ni envío real. Pasan 100 pruebas NBA y 606 fútbol. Se corrigió
UTF-8 en lectura de JSON y se conservó el primer informe con errores; el
harness final usa PATH completo y temporales dentro del workspace.
Evidencia: docs/nba_scrapers_avance_20261005.md y registro auditable NBA.

## 2026-10-05 — The Odds API de fútbol también cubre NBA

A petición del usuario se revisó la documentación oficial y se probó la clave
existente sin copiarla a NBA o reportes. Autenticación y eventos: 46 NBA
regular, ocho pretemporada. Prueba acotada de un partido: descubrimiento de
mercados y 22 líneas alternativas P/R/A de un jugador en DraftKings, solo
Over. Cuatro créditos gastados; 19,652 restantes al capturar. Última
actualización de props unos 193.6 segundos anterior a recepción: no supera
frescura local de 60 segundos; faltan lado opuesto, reglas e IDs verificados.
No se descargaron históricos ni se habilitó polling continuo. El presupuesto
del proveedor se comparte con fútbol aunque el procesamiento NBA permanezca
separado; requiere reserva coordinada antes de operar. La revisión no cambia
código de aplicación ni parámetros. Evidencia y próxima integración:
docs/nba_the_odds_api_revision_20261005.md, NBA-RUN-019. Puertas pendientes.

## 2026-10-05 — Acceso histórico NBA confirmado

El usuario confirma plan de pago. Prueba real: eventos históricos y
player_rebounds responden 200; Houston–OKC 2025-10-21, 242 cuotas de 17
jugadores/ocho casas y 121 pares Over/Under. Once créditos consumidos, saldo
observado 19,638. Tres relojes de mercado posteriores al snapshot por 7–26
segundos, todos anteriores al as-of solicitado: se excluyen para el corte
estricto del snapshot, sin alterar timestamps. Cinco casas/154 cuotas quedan
compatibles con ese corte; no se acredita recepción propia histórica,
identidad NBA, reglas o rentabilidad. Fuente histórica disponible para el
dataset de precios; código/modelo sin cambios y puertas pendientes.
Evidencia: docs/nba_the_odds_api_historicos_20261005.md.

## 2026-10-05 — austin-pesina/nba_scrapes descargado

Descarga completa del commit d6d06b273d7a8818be3936f43425979db1ab92a3:
seis archivos/15,023 bytes, verificados con Git SHA-1 y SHA-256. Solo main;
cero datasets en árbol, cero releases y cero artefactos Actions disponibles.
Los scripts consultan Basketball Reference y escriben Snowflake/exportes;
sus resultados no están publicados aquí. Año final fijo 2026 = 2025–26;
IDs Basketball Reference, sin lesiones o precios históricos de props.
No ejecutar proyectos de terceros para confundir herramientas con datos:
se conserva código como referencia, sin dotenv global, instalación o acceso
Snowflake. Cero filas nuevas y cero créditos The Odds API. Código/modelo
propio sin cambios. Evidencia: docs/nba_repo_austin_pesina_20261005.md.

## 2026-10-05 — Descargador histórico Edgar Parra revisado

Se inventarió el commit 7a0c22f6e26e8ec6854742dd88abf755d10733f4 y se
descargaron 14 referencias/167,099 bytes con hashes verificados. Su módulo
masivo usa LeagueGameFinder y PlayerGameLogs por temporada: patrón útil para
completar huecos estadísticos. El único CSV publicado está vacío y la base
SQLite descrita por el inventario del autor no está en main. Los 90
artefactos Actions son pequeños y el workflow publica reportes/logs; no se
descargaron ni se acreditó que contengan registros históricos.

Decisión: usar el patrón de consulta como referencia, manteniendo el pipeline
NBA propio. Exigir separación de competición/temporada y validación de
censo, caché, minutos y disponibilidad original. Su historical_odds_backfill
asigna -110 a ambos lados y usa fecha de observación como fecha de partido;
no constituye histórico real de cuotas. No ejecutar ni adoptar ese modelo.
La revisión añade cero partidos y consume cero créditos de The Odds API.
Se sellaron Austin/Edgar en NBA-RUN-021/022: 80 evidencias verificadas y 33
archivos propios sin cambios; todas las puertas pendientes. Documento:
docs/nba_repo_edgar_parra_20261005.md.

## 2026-10-05 — Históricos gratuitos y ahorro de créditos

El usuario autoriza aprovechar scrapers para históricos sin gastar créditos.
Se contrastó cobertura regular: 5,830/6,150 partidos aceptados en cinco
temporadas, 320 pendientes por ausencia o cuarentena. Una consulta acotada
oficial LeagueGameLog, jugadores 2025–26 regular, agotó lectura tras 20 s;
manifiesto conservado, sin reintentos ni nuevas filas. Los archivos gratuitos
ya recibidos siguen disponibles. No se puede declarar descarga oficial
completa o funcionamiento del scraper desde esta conexión.

Decisión: completar estadísticas con fuentes gratuitas y reservar presupuesto
para precios auténticos. Son datasets distintos; el backfill de -110 no
sustituye cuotas históricas. Se documenta muestra de 100 partidos/rebotes/una
región/un snapshot ≈1,000 créditos más descubrimiento, sin ejecutarla. Cero
créditos gastados en esta tarea; código/modelo sin cambios. Documento:
docs/nba_historicos_gratis_presupuesto_20261005.md.


## 2026-10-05 — Los picks de la sombra, visibles en `/control`

Pedido del usuario: ver cuáles se habrían publicado, no solo los totales.
La tabla sale de `publishable()`, no de una consulta propia: si el panel
enseñara otra selección, el usuario juzgaría una muestra distinta de la que
decide la puerta (comprobado en producción: 28 filas = `publishable.n` 28).
Va tras el login del panel y nunca a la web pública porque revela casa,
cuota y antelación del criterio. Stake mostrado = el que se publicaría
(× factor de incertidumbre, db/039).

Despliegue mínimo, sin reconstruir: el repo del servidor va por detrás de
HEAD (`promotion.py`, `clv.py`, `dixon_coles.py`, `api_football.py`…) y el
contenedor de la API aún más (sin `latencia.py`, `shadow_sharp` previo a
db/039). Reconstruir habría desplegado de rebote la lógica de la puerta. Se
copió al contenedor su propio `shadow_sharp.py` + las dos funciones nuevas
(solo añade líneas), `console.py` y `console.css`; el repo del servidor
recibe la versión HEAD + cambio. Respaldo en
`~/respaldo_20261005_panel_sombra`. Pendiente aparte: decidir cuándo se
sincroniza y reconstruye el servidor con HEAD.

## 2026-10-05 — Recuperación NBA gratuita implementada y piloto auditado

El usuario autoriza avanzar con boxscores, GameRotation y PDF oficiales de
lesiones. Se implementaron inventario reproducible, capturadores finitos que
conservan originales/errores y validadores estrictos de estadísticas,
minutos, stints y cronología. El inventario identifica 395 partidos conocidos
pendientes: 320 regulares, 71 de pretemporada, tres de playoffs y uno de
play-in. En 299 pendientes regulares la fuente contiene minutos inválidos;
no se corrigen valores como 30:60 sin evidencia independiente. Los siete
conflictos de referencias de equipo ya tienen GameID; no eran IDs ausentes.

Las consultas reales de boxscore y rotación oficiales terminaron en
ReadTimeout; la alternativa CDN devolvió 403. Se detuvo cada lote y se
conservó la evidencia, sin importar partidos o stints. Se recibieron tres
PDF oficiales de lesiones, ocho páginas verificadas visualmente y 84
observaciones de 30 jugadores distintos; cuatro cambios reales de estado
entre los primeros reportes. El nombre 05PM corresponde a una cabecera
17:30 ET: se decide usar la cabecera y convertir con zona/DST validada.
Recepción en 2026 de informes de 2025 no acredita disponibilidad original;
el modo retrospectivo queda separado del filtro prospectivo. IDs médicos,
hora de partido y cobertura de archivo siguen pendientes.

Validación: 136 pruebas NBA y 609 de harness pasan; baseline de harness
606 antes de cambios concurrentes de fútbol, que se preservan y no se
atribuyen a NBA. Docker no disponible. Código propio congelado en 37
archivos; dataset/modelo aceptados conservan hash. NBA-RUN-024–026,
100 evidencias verificadas y ledger de 60 eventos, sin ancla externa.
Cero créditos The Odds API, cero nuevos partidos, cero publicación de picks
y todas las puertas pendientes. Documento:
docs/nba_recuperacion_piloto_20261005.md.

## 2026-10-05 — Basketball Reference responde; alternativas con cobertura real

La lista del usuario se contrastó con siete commits e interfaces reales.
Decisión: priorizar una muestra independiente que responda, conservando los
IDs y la precisión de cada fuente. Basketball Reference devolvió HTTP 200;
se conciliaron veinte participantes de 0022100012, 240 minutos por equipo
y P/R/A completos, sin errores del validador existente. El valor NBA 33:60
de Michael Porter Jr. corresponde a 33:59 en esa fuente, no a 34:00. No
corregir todas las anomalías de reloj mediante una regla supuesta. El
resultado queda en staging y el dataset principal/modelo no cambian.

ESPN Parquet 2025–26 descargado y digest GitHub verificado: 34,883 filas,
1,326 eventos. Candidatos únicos por fecha/equipos para 84 regulares, tres
playoffs y un play-in pendientes recientes; ninguno de 71 pretemporada.
Minutos enteros e IDs ESPN impiden importar directamente como NBA exacto.
JaseZiv aporta 73,306 transacciones hasta 2025-05-13, no publicación
horaria; una fecha 1899-12-30 y 16 filas sin equipo requieren cuarentena.
Workflow diario escrito no prueba actualización: commit último mayo 2025.

nba_api incluye PlayIn/Pre Season pero no evita bloqueo del endpoint;
pbpstats documenta Client y overrides; nbainjuries usa get_reportdata con
Java y no garantiza timestamp de cabecera en sus siete columnas. No se
ejecutaron bibliotecas externas ni se gastaron créditos The Odds API.
609 pruebas del harness pasan; 37 archivos NBA y 100 evidencias previas
sin cambios verificados. Puertas pendientes. Documento:
docs/nba_repos_alternativas_verificadas_20261005.md.

## 2026-10-05 — Ampliación Basketball Reference: 159 partidos recuperados

El usuario pide ampliar esta recuperación. Decisión: cachear por fecha,
preservar recepción/raw y generar versiones nuevas que heredan intacto el
dataset anterior. Parser, cruce por mismo partido/equipo/localía y P/R/A,
conciliación existente sin bajar umbrales. Variantes de sufijos omitidos y
puntos en iniciales solo con candidato único; rechazar generaciones
contradictorias y apodos. No atribuir DNP o lesión por ausencia de una fila.

Se programaron 263 fechas con lotes de veinte y seis segundos mínimos.
140 páginas válidas recibidas/reutilizadas; 2024-03-11 devolvió HTTP403,
se detuvo el lote ocho y no se intentaron fechas posteriores. Cuerpo y
parada del proveedor conservados. Cero créditos The Odds API, sin proxies
o reintentos. La causa precisa del rechazo no está acreditada.

Versiones parciales de 34 y 111 partidos y final de 159 partidos regulares
recuperadas. La versión ampliada contiene 157,375 filas: 154,058 originales
idénticas y 3,317 nuevas (3,316 con participación). Se reparsaron las 136
páginas utilizadas y reconciliaron de nuevo los 159 partidos; 597 jugadores
NBA con cruce consistente entre partidos. Hash antiguo preservado, sin
reentrenamiento/publicación. Cobertura regular: 5,989/6,150; 2021–22
completa, 2022–23 queda a un partido. Restan 161 regulares y 75 no regulares
conocidos; calendario antiguo de playoffs no se declara completo.

Nueve recibidos se mantienen separados: siete diferencias de un REB/AST,
referencia parcial 0022300835 (42.75 minutos y marcador parcial), y
0022300810 con fila Thomas Bryant sin minutos/comentario. No asignar DNP
a esa ausencia ni modificar agregados para forzar concordancia. Los otros
152 regulares no tienen página válida en este intento. Diagnóstico local
por equipo/valor conservado.

172 NBA/609 harness pasan; 39 archivos propios congelados, ambas versiones
del código conservadas. Fixture nuevo de colisión se corrigió tras un fallo
de prueba; logs fallido y posteriores preservados. Docker no disponible;
revisión propia sin revisor independiente. Cambios concurrentes de fútbol
preservados y no atribuidos a NBA. Todas las puertas pendientes. Documento:
docs/nba_basketball_reference_recuperacion_20261005.md.

### 2026-10-05 — Black Falcon ESPN NBA: utilidad comprobada antes de escalar

La cuenta Apify ya tenía sesión en el navegador; se usó sin copiar tokens.
Diez candidatos explícitos (6 regular, 2 playoffs, 1 play-in, 1 pretemporada),
máximo US$0.25/400filas/120s. Run T6I23rByjmvXbCpL2 correcto: 282 filas,
226 participantes/56DNP, US$0.142 mostrado. JSON íntegro de 927,312 bytes,
entrada, log, recibo, screenshot y scripts congelados; sin créditos Odds API.

No se amplió porque 247 filas de nueve partidos duplican ESPN previo y los
minutos vuelven a ser enteros: no resuelven valores NBA malformados ni prueban
240 minutos exactos por equipo. P/R/A de participantes coinciden; 53 DNP
comparan null contra cero, conservados sin rellenar. Cuatro fechas UTC
requieren conversión explícita a America/New_York; primer assert detectó
esa diferencia y se corrigió la semántica del reloj, no el emparejamiento.
Los 20 totales P/R/A y puntos por cuartos/prórroga cuadran. playerActive=false
en 126 participantes impide interpretarlo como disponibilidad prepartido.

Las 35 filas nuevas de pretemporada NYK/PHI 2025-10-02 siguen separadas:
referencia NBA con ambos visitantes y sin candidatos individuales NBA.
No hay importaciones, reentrenamiento ni promoción de puertas. Cobertura
aceptada 5,989/6,150 regulares; 161 regulares/236 pendientes conocidos totales.
39 archivos NBA de código siguen con sus hashes anteriores; fútbol preservado.
609 pruebas pasan antes/después; intentos iniciales del harness con PATH
incompleto no cuentan como pruebas. Docker no disponible. Revisión propia.
NBA-RUN-031, 139 evidencias verificadas, cadena 77 eventos sin ancla externa.
Documento: docs/nba_blackfalcon_descarga_20261005.md. Siguiente paso útil:
fuente con segundos y corroboración de referencias, no compras masivas de
estadísticas que ya tenemos.

## 2026-10-05 — ¿Limitar a cuota ≤ 1,80 para acertar más? No con las casas de los suscriptores

Pregunta del usuario tras ver 12 de 19 perdidas en la sombra (que eran lo
esperado: 6,25 ganadas esperadas al cierre, 7 reales). Medido sobre
football-data (7 ligas, 2019/20-2024/25, 14.294 partidos, firma
d5cbc3151164), criterio actual aproximado: mejor de bet365/1xBet con edge
temprano ≥ 2%. De 683 apuestas solo 14 tienen cuota ≤ 1,80 (2%), aciertan
el 71% y su EV al cierre es −0,07% [−1,78, 2,33]: ahí no hay valor. El valor
está en 2,51-5,00 (+2,8% y +1,9%, IC entero > 0). Con todas las casas el
tramo ≤ 1,80 sí da +3,4% [2,1, 4,8], pero esas casas no cuentan para la
puerta. En vivo, 2 de 28 publicables tienen cuota ≤ 1,80.

Decisión: no se restringe la cuota. Subiría el acierto, pero bajaría o
anularía el valor esperado y dividiría por ~15-50 el ritmo de una muestra
que ya necesita ~6 meses. Acierto alto ≠ rentable: es un problema de
comunicación al suscriptor, no del criterio.

## 2026-10-05 — Probabilidad real de cada pick en la web

Pedido del usuario tras ver que la sombra pierde 12 de 19 (lo esperado con
cuotas medias de 3,9). La probabilidad que se enseña es `fair_prob`, la de
Pinnacle sin margen en el snapshot del pick, NUNCA `model_prob`: el modelo no
elige los picks y su edge resultó anti-señal. Se muestra en porcentaje y en
frecuencia ("29% · sale 1 de cada 3.4") porque la frecuencia es lo que
prepara al suscriptor para las rachas. El bloque real añade el acierto
esperado de la lista (media de `fair_prob`) y no lo estima si a algún pick le
falta el dato: los picks anteriores a db/017 lo tienen NULL.

Solo frontend: `/picks/free` ya devolvía `fair_prob`. Desplegado copiando los
4 estáticos al contenedor y al repo del servidor (coincidían con HEAD; se
leen del disco en cada petición, sin reinicio). Respaldo en
`~/respaldo_20261005_prob_real`. Con la publicación pausada el bloque real
sigue vacío; hoy solo se ve en las tarjetas de demostración.

## 2026-10-05 — Propuesta del usuario: picks con 80% de acierto (medido, sin decidir)

Motivo del usuario: los clientes valoran acertar más que batir a la casa, y
no toman todos los picks. Medido en football-data (7 ligas, 6 temporadas,
mejor cuota de bet365/1xBet, firma d5cbc3151164): selecciones con
probabilidad justa ≥ 80% = 5,2% de los partidos (~123/temporada), aciertan
el 84,8% a cuota media 1,15, ROI −2,4% y EV al cierre −2,6%. Con casa
pagando ≥ 2% sobre el justo: 0 casos. Ningún umbral entre 50% y 85% da EV
positivo. Simulación de un cliente que toma picks al azar: el favorito ≥ 80%
deja en ganancia al 53% tras 10 picks, al 27% tras 100 y al 14% tras 300; el
criterio de valor, al 45%, 51% y 54%. La objeción del usuario es real (el
valor es casi una moneda al aire para el cliente hasta cientos de picks),
pero el 80% no la resuelve: pierde más cuanto más se sigue. Pendiente de
decisión del usuario; nada cambiado.

## 2026-10-05 — NBA: servicios auxiliares y conciliación de históricos

Se amplió solo Flashscore, que aporta minutos fraccionarios a dos decimales,
y el calendario NBA para referencias canónicas. Cinco runs Apify acotados,
US$2.064 mostrado, cero créditos The Odds API. Ningún plan/recarga/schedule.
Tres lotes Flashscore: 227 partidos/6,631 registros; calendario ampliado99
partidos, incluidos los71 IDs de pretemporada pendientes. Cinco partidos
presentan discrepancias con referencias previas; no se sobrescribieron.

Decisión: aceptar únicamente el partido completo con IDs únicos, P/R/A por
jugador, segundos previos válidos concordantes y conciliación estricta. Un
contraejemplo real de +41/-41 segundos conserva el total del equipo, por lo
que ese total nunca sustituye la comprobación individual. Se añadieron67
partidos (63regular,3playoffs,1play-in),1,713 filas/1,470 participantes a una
versión nueva:159,088 filas, todas las157,375 previas intactas. Cobertura
regular6,052/6,150=98.41%; quedan98regular y71pretemporada. Los62 boxscores
candidatos de pretemporada descargados siguen separados por identidades o
referencias. Cero pendientes de playoffs/play-in solo en el inventario
actual; no certifica todo el histórico.

Verificación completa de los67 partidos,1,400 relojes previos válidos,34
páginas de originales,17 controles adversariales y139 evidencias previas.
Los39 archivos NBA congelados y modelo preservados; cambios concurrentes
de fútbol no tocados. Esta es auto-revisión de investigación y hashes
locales, sin anclaje externo ni promoción G0–G9. Los timestamps de captura
son actuales; lesiones disponibles antes del partido no se inventan desde
DNP. No ampliar el mismo scraper mientras falte conciliación. Informe:
docs/nba_servicios_recuperacion_20261005.md.

Cierre verificado: harness antes/después609 pruebas aprobadas (una advertencia;
Docker no disponible);17 controles de datos aprobados. NBA-RUN-032 registra
152 evidencias verificadas; cadena78 eventos, cabeza
c89ee0f4ab3ef619536a259a2fee9b91c03d4be074123ff3933edfe0bebd8389.
Dataset final_v2 SHA256f10b5e8e5dc8ba7dc85dac184fdf90ac25c17b64fe48a7e14b00f5d8885a13fd.
Los pilotos/expanded previos son exploratorios; final_v2 es la versión
auditable de esta recuperación. Recibos y74 originales referenciados en
manifest; snapshots de4 scripts. No se modificó el modelo ni su config.

## 2026-10-05 — NBA: pendientes, lesiones, rotaciones y props

Decisión: descargar candidatos no significa recuperar un partido, y una
cabecera histórica no prueba recepción en su momento. ESPN completo sobre
166candidatos permite añadir16partidos (3regular/13pretemporada),515filas,
159603totales;159088anteriores intactas.6055/6150regulares;95regular y58pre
siguen pendientes por conflictos de reloj/PRA/referencias/IDs. No convertir
minutos enteros ESPN en segundos; Flashscore conserva su supuesto de
redondeo decimal. Perfiles NBA respondieron403; lote detenido sin forzarIDs.

PBP local reconstruye5161partidos/217334tramos;891cuarentenas. El presupuesto
de cuantización cuenta intervalos continuos del propio jugador por período,
no cada cambio del quinteto por sustituciones de compañeros. Sin carryover
automático de titulares, sin rescalar clocks, y sin tratar rebotes de equipo
como jugadores. La versión final es chronological_stints_v4_20261005.

486PDFs/43924filas/36300registros nominales médicos: un corte diario,
330fechas pendientes tras403.272motivos partidos entre páginas unidos solo
con precedente nominal/estado válido y fragmento inicial de motivo. Segundo
motor verifica los486PDFs.43675filas conpartido,36063conjugador;237nominales
sinID(13nombres).1213regulares2025-26conreporte anterioraT60;974conambos
equipos enviados. El recibo es actual: reconstrucción retrospectiva, no PIT
ejecutable. Absent/unsubmitted siempre desconocido. IDs no prueban roster
histórico. Versión final injury_daily_joined_remaining_v2_20261005.

20juegos/40snapshotsrebotes,2961pares/5922precios;420créditos de límite500
predefinido conservador mientras la pregunta opcional seguía sin respuesta.
No nueva ejecución Apify.88casa/mercado rechazados por actualización futura
al snapshot y73entidades por IDnominal ambiguo; no ROI ni reglas de void
inventadas. Dos horarios del proveedor revisados entre snapshots: se
registran las versiones y los cortes deben preceder todos los horarios.
Versión final historical_rebounds_remaining_v2_20261005.

19controlesde corrupción/temporalidad, todos16boxscores/515filas,
todos5161juegos de stints,6replaysrawPBP,40replayscuotas y486PDFssegundomotor.
Harness609antes/después(unaadvertencia,Dockernodisponible). Auto-revisión;
hasheslocales, no anclaje externo.39archivosNBA/modeloconfig y152evidencias
anteriores preservados. NBA-RUN-033; G0–G9 pendientes. Fútbol no modificado,
sin entrenamiento/publicación/avisos. Informe detallado y manifests:
docs/nba_pendientes_recuperacion_20261005.md.

Cierre del lote de pendientes: NBA-RUN-033,168evidencias verificadas,
974originales/manifests fijados y22scripts con snapshot; cadena79eventos,
cabeza dca828a0271f04a12d518b74a7f43ea9e75a3dc628b459a3c58228aca958c3fe.
Datasetboxscore SHA25641c5a4f82d3638138a6a4d9b5bb7fb21033eecbae5e3fa07de99dc074d67ef68.
El cierre certifica este lote verificado, no la finalización del histórico.

## 2026-10-06 — Servidor sincronizado con HEAD (paso previo de la línea de alta probabilidad)

Lo que parecía un servidor muy atrasado era casi todo finales de línea: el
repo del servidor tenía archivos con CRLF (copiados desde Windows) y contenido
idéntico. Comparando sin CR, el worker ya corría HEAD salvo el brazo
"más-menos" de `player_value.py` y módulos de investigación; la API iba más
atrás (picks, config, odds_worker, shadow_sharp). Con visto bueno del usuario:
commit af9c8b4 del trabajo del día ya desplegado a mano (si no, la
sincronización lo habría revertido), `git archive HEAD` sin `harness/`,
build y reinicio de api/worker en un minuto sin crons (04:14 UTC). Verificado:
cadena (7 lotes), salud, model-card, web, /control 401 y crons sin errores.
Respaldo en `~/respaldo_20261006_presync.tgz`. Regla para el futuro: comparar
servidor y repo con `tr -d '
'`, o la lista de "cambios" engaña.

## 2026-10-06 — NBA: recuperación con actores adicionales de Apify

Se usó la cuenta existente para seis capturas acotadas de Basketball API y
Action Network, US$2.341 del crédito gratuito; saldo mostrado aproximado
US$0.45. Sin recargas, suscripciones ni créditos The Odds API. El actor de
boxscores publica secondsPlayed: Clippers–Nuggets 0012500052 agrega 40 filas
(30 participantes y diez DNP expresamente señalados por ESPN). Ambos equipos
suman 14400 segundos y PRA coincide con ESPN/referencia NBA. Sus 13 teamId
contradictorios no se usan: equipo histórico unido por lado, calendario y
pertenencia ESPN; identidad NBA por nombre completo único. Pelicans–Melbourne
solo tiene un equipo y queda como candidato. Dataset159643; anteriores159603
intactos. El calendario nuevo tiene71juegos y68cruces exactos NBA; tres códigos
extranjeros separados.

Action Network devuelve385precios P/R/A de casas reales sin hora original,
y movimiento solicitado vacío;18de19lesiones anexas se actualizaron después
del partido. Ninguno entra al backtest. Una fecha solicitada no acredita que
sus bloques anexos fueran conocidos entonces; no ampliar ese flujo para PIT.

Ocho controles de corrupción,609pruebas antes/después,39archivos NBA/modelo
congelados intactos,168evidencias anteriores/974originales/22scripts verificados;
181evidencias totales. NBA-RUN-034,80eventos de auditoría;G0–G9 pendientes.
95regular y57pretemporada aún faltan; lesiones/rotaciones y props conservan
los huecos anteriores. Sin entrenamiento/publicación ni avisos; fútbol no
modificado. Informe:docs/nba_apify_fuentes_adicionales_20261006.md.

## 2026-10-06 — NBA: API-NBA con clave autorizada por el usuario

La autenticación funciona, pero el permiso NBA efectivo es Free: los endpoints
de temporada2025 devuelven error de plan, aunque la guía pública no dejaba
clara esa restricción.80pendientes2025-26(23regulares/57pretemporadas) bloqueados.
No contratar ni recomendar una compra como garantía de recuperación: el acceso
y la precisión son requisitos distintos. Clave solo en archivo local ignorado;
estados sanitizados sin datos personales, evidencias sin encabezados secretos.

Tres calendarios y72cruces exactos por fechaEastern/localía/nombre.72boxscores
descargados,1543registros; todos los minutos individuales son enteros, sin
segundos. Consulta por temporada sola rechazada;83peticiones de datos,3errores
de aplicación y2/status. Límite local95, cuotaFree100/día. Estado final70/100;
cabeceras no monótonas conservadas, sin fingir que equivalen al contador local.
Cero suscripciones nuevas, Apify o créditos TheOddsAPI.

No hubo partido aceptado: conflictos de PRA, identidad y segundos previos
válidos frente al reloj decimal alternativo. API-NBA no repara33:60 ni38:60
desde un entero. Referencias de rebotes contrapuestas no sobrescritas con
sumas individuales; no expandir iniciales o inferir DNP. Conservar72candidatos
fuera del dataset aceptado;159643filas previas y152pendientes permanecen.

693pruebas antes/después,10controles de corrupción;181evidencias previas y39
archivos NBA congelados intactos. NBA-RUN-035,194evidencias totales,81eventos
ledger,cabeza a40baa89c829109da4f82d2a21f23f5629943f01eac3a62c1fb818cf3dfd077e.
Auto-revisión, sin anclaje externo, sin entrenamiento/puertas/picks/Telegram.
Fútbol y cambios concurrentes no tocados. Informe y manifiestos:
docs/nba_api_nba_recuperacion_20261006.md.

## 2026-10-06 — Línea de alta probabilidad: implementada, integrada y desplegada apagada

Pedido del usuario: pronósticos "seguros" de al menos 80 %, aparte de los picks
de valor. Diseño, plan y ejecución con subagentes (docs/superpowers/). Decisiones
clave (el porqué):

- Probabilidad de Pinnacle sin margen, no del modelo: la promesa es un
  porcentaje y tiene que salir de la referencia calibrada. Se publica el
  candidato de MENOR probabilidad en [80, 95]: cumple el 80 % y es el más útil.
- Goles por ajuste al mercado con push correcto (`pricing.totals_fair_over`):
  Pinnacle cotiza 2 de cada 3 líneas en cuarto o gol entero. Prueba histórica
  (firma d5cbc3151164): regla completa prometido 84,45 / real 84,60; pasan
  h2h, doble oportunidad y las tres líneas de goles.
- Sellado con UNA fuente de verdad (`hashchain.lote_lleva_alta`): la revisión
  de la tarea 7 encontró que, con la línea encendida y sin fecha de corte, la
  API habría mostrado como sellado algo que el lote no cubría.
- Probabilidad pública a punto entero (decisión del usuario): con 6 decimales,
  1 − prob de una doble oportunidad era el precio justo del no favorito, el
  criterio de los picks de valor. El lote conserva el exacto.
- Pausa más exigente (decisión del usuario): IC99, mínimo 10 semanas y z ≤ −4
  para fallos groseros. Con IC95 y 8 semanas, ~32 % de líneas calibradas se
  habrían pausado en falso en 6 meses (pausa pública y manual de levantar).
- Esquema verificado en producción, no en tests (decisión del usuario).
- Despliegue 2026-10-06 18:12 UTC con `ALTA_PROB_ENABLED=0` y corte
  `LOTE_ALTA_PROB_DESDE = 2026-10-07` (el 6-oct ya había sellado). Vista
  previa: 2 de 15 partidos (parón de selecciones; sin goles porque el precio
  reciente a las 08:00 es de API-Football). Activación pendiente del usuario
  tras verificar el lote del 7-oct.


## 2026-10-06 — NBA: lineups Ramiro y contraste offline pbpstats

Cinco CSV públicos fijados al commit e702d9b7b585bb79e751eb52d5d767e29f16cab0, 110,072,340 bytes y 6,150 partidos regulares. 6033 pasan estructura/minutos; la aceptación final exige replay de PBP, titulares demostrados por período, sustituciones, marcador y minutos individuales sin rescaling. Se añaden 7 partidos (4 de las 891 cuarentenas); la versión combinada conserva los 5,161 previos y contiene 5168 juegos / 217619 tramos. Permanecen 887 cuarentenas previas y 887 regulares aceptados sin rotaciones.

pbpstats 1.3.11 contrasta 248283 sustituciones con IDs corroborados y red bloqueada, no ingestión nativa V3/posesiones. Fuente y PBP pueden compartir origen NBA; no se presume revisión independiente o disponibilidad prepartido. 15 controles adversariales, invariantes completos, 39 archivos NBA congelados intactos; harness 693/693, NBA 172. Cero créditos de pago, sin entrenamiento/promoción/picks. NBA-RUN-036; informe docs/nba_ramiro_pbpstats_auditoria_20261006.md.

## 2026-10-06 — Más pronósticos de goles: API-Football ya trae las líneas de Pinnacle

La línea de alta probabilidad casi no daba goles: a las 08:00 UTC el precio
de ≤ 6 h suele ser de API-Football, y `af_odds` pedía solo `bet=1` (1X2). La
misma petición por partido, sin filtro, trae de Pinnacle "Goals Over/Under"
(bet 5) con 1,5 / 2,5 / 3,5 / 4,5 y cuartos, más las casas blandas. Prueba de
solo lectura (22 partidos de las próximas 72 h, 21 peticiones): 22/22 con
1X2 + O/U de Pinnacle; pronóstico de goles en 15/22 (hoy 0) y pronóstico en
18/22 en total. Línea directa de Pinnacle frente al ajuste Dixon-Coles con su
2,5: media −0,03 pts, máx. 1,55 pts (n = 46): el ajuste validado en el
histórico también cuadra en vivo. Coste en peticiones: cero. Pendiente de
decisión del usuario: guardar bet 5 en `af_odds_snapshots` (necesita columna
`line` y nuevo índice único NULLS NOT DISTINCT) y que `alta_prob_datos` lea
esos totales.


## 2026-10-06 — NBA: ejecución real de scrapers, Java y ZenRows

Los152boxscores pendientes llegaron desde NBA Stats sin proxy;53pretemporadas pasan,1903filas nuevas/161546combinadas,67de71juegos. Los95regulares conservan minutos inválidos/discrepancias; capturar no equivale a aceptar. El archivo público de pbpstats, actualizado abril2023, aporta405PBP de candidatos: el replay con IDs explícitos V2 y las corroboraciones Ramiro/native EnhancedPbp añaden325rotaciones. Combinado5493juegos/231075tramos,562regulares aceptados sin rotación; previos159643filas/5168rotaciones intactos.

Java portátil permite18acuerdos de tres parsers sobre seis PDFs/398registros nominales; no recupera fechas nuevas. BRef/CDN/PDF403 yCDX503 se conservan; no se reintentan mediante rotación IP. oddsapiR revisado, sin Rscript ni llamadas pagadas nuevas; otros repos de la tabla quedan con estado explícito, no se afirma ejecución total. Toolkit ZenRows1.3.1/MCP2.4.0 instalados con alcance de proyecto para Claude Code;44herramientas stdio y cero llamadas proveedor; credenciales ignoradas, validez/cuota no comprobada.

Once controles adversariales e invariantes completos,39archivos propios intactos,225evidencias previas verificadas; harness693antes/después, NBA172. Fallos de configuración de temporales, acceso a ejecutables y serialización NaN conservados y corregidos. Sin entrenamiento, promoción de puertas o picks. NBA-RUN-037; docs/nba_github_scrapers_recuperacion_20261006.md.


Cierre de NBA-RUN-037: la salida de consola se escribió después del hash de su archivo abierto. Se conserva el snapshot vacío exacto del checkpoint y toda la salida final en otro archivo cerrado, con recibo explícito console_finalization.json y evento artifact_finalization. Se verifican304evidencias/84eventos; no se modifica ninguna fila, rotación, registro de corrida o evidencia existente.

## 2026-10-06 — Goles desde API-Football: desplegado

Implementado con plan corto y subagentes (docs/superpowers/plans/
2026-10-06-goles-desde-api-football.md): `af_odds` quita el filtro `bet`
(misma petición) y guarda bet 5 — todas las líneas de Pinnacle y 1,5/2,5/
3,5/4,5 de las casas de la lista — con columna `line` e índice único NULLS
NOT DISTINCT (db/041, con guardia que aborta si queda el UNIQUE viejo, por
la revisión final: con IF EXISTS un nombre mal escrito habría tumbado toda la
captura en silencio). La línea de alta probabilidad lee esos totales de la
MISMA respuesta que el 1X2 (`_totales_af`, con `fetched_at <= now`).

Despliegue 19:58 UTC en un minuto sin jobs ni partidos en 15 min: migración
y reinicio juntos (el código viejo no funciona con el esquema nuevo y no hay
vuelta atrás salvo hacia delante: volver a pedir `bet=1` con el INSERT de 9
columnas). Dos pasadas manuales de `af_odds`: 1.622 filas nuevas en 41
partidos (15 s) y luego 0 (el 1X2 se sigue deduplicando). Vista previa con
la línea encendida solo para ese proceso: 9 pronósticos de 15 partidos, 7 de
goles (casi todos "menos de 4,5", con referencia de Betano), antes 2.


## 2026-10-06 — NBA: ZenRows usado en tráfico real de fuentes

La instalación del MCP no redirigía los scrapers. Se autenticó account_usage y se probaron cuatro targets con máximo100créditos: BasketballReference.cgi devuelveHTML válido/152filas y pasa parser upstream; CDN yPDF dan ZenRows422/RESP001,CDX agota110segundos. Consumo observado1de5000créditos, sin compras. El adaptador nuevo enruta GET del scraper BRef a scrape del MCP y conserva HTML/recibo/hash; no se declara desbloqueo universal.

Memphis–OKC0022200443 añade23filas/22participantes/1DNP explícito,161569combinadas;6056regulares aceptados y94pendientes. Overlay declarado OKCreb54→53 corroborado por NBAStats actual y BRef, conservando el Parquet antiguo y umbrales.152acuerdos entre parsers,6controles adversariales,161546filas previas intactas,39archivos propios intactos,304evidencias previas verificadas; harness706antes/después. No se atribuye nueva ejecución a la suiteNBA172 anterior. NBA-RUN-038; docs/nba_zenrows_recuperacion_20261006.md.

## 2026-10-06 — Línea de alta probabilidad: fuera "menos de 4,5 goles"

Decisión del usuario tras la vista previa con goles de API-Football: casi
todos los pronósticos de goles eran "menos de 4,5" (se paga a 1,09-1,17),
poco útil para el cliente. `MERCADOS_GOLES_HABILITADOS` queda en más de 1,5
y menos de 3,5 (commit 396af2c). Pasó la prueba histórica: quitarla no exige
repetirla; volver a añadirla, sí. API-Football sigue guardando la 4,5 de las
casas blandas (no cuesta peticiones) por si se reabre.


## 2026-10-06 — NBA: completar y validar históricos (NBA-RUN-039)

BRef: 83 fechas por ZenRows recuperan 93 regulares; actas/calendario/ESPN completan cuatro pretemporadas. Resultado: 6149/6150 regulares, 71/71 pretemporadas, 164190 filas. Las fuentes de los 6150 regulares están capturadas. Tony Bradley (0:00 / 1 REB) está corroborado por PBP de 0,2 segundos y se conserva fuera del normalizador congelado, sin inventar segundos. Rotaciones: 6113/6150, 258137 tramos y 37 pendientes. Los 330 PDFs de 17:30 completan 816 fechas, 80932 filas y 70941 filas nominales con ID; 13 nombres originales y 19 nuevos resueltos con fuentes oficiales. No se acredita intradía total o recepción pregame original. Props: +795 pares P/A (603/192), 3756 con rebotes; 500 créditos locales agotados, cobertura de dos juegos P/A y veinte de rebotes. Se preservan 161569 filas y 5493 rotaciones previas, 39 archivos NBA y 340 evidencias. Harness: 706 antes/después; 21 controles adversariales. Los timeouts mantienen reserva por coste incierto; sin compras. Modelo y gates intactos. Informe: docs/nba_completar_validar_20261006.md.


## 2026-10-06 — NBA: segundos oficiales y rotaciones (NBA-RUN-040)

Se amplió el contrato de minutos solo con fuentes GameRotation completas y hash externo, para permitir <=1s con reloj cero/estado vacío; PRA no infiere participación. Tony Bradley conserva 0:00 y 1REB, acredita0,2s y añade su roster completo28filas:6150regulares/71pretemporadas/164218filas. La ruta por defecto coincide con el normalizador archivado en164190filas. Rotaciones:+28,6141/6150 y259416tramos; nueve casos mantienen contradicciones administrativas o titulares de OT sin prueba. V3actual17capturas requirió adaptar el esquema nestedgame y reconocer actionId único; actionNumber duplicado permanece. Alias de sustitución solo mediante IDs explícitos V2/V3 corroborados; sin override de titulares.245créditos nuevos confirmados;riesgo1612/3200 con reservasinciertas, cero props/sincompras.189NBA/707harness; primerWinError5temporal preservado y repetición completa exitosa.2105evidencias previas verificadas,38archivos antiguos intactos e ingest original archivado; modelo/gates intactos. Intradía médico/PIT y props multitemporada pendientes. Informe:docs/nba_segundos_y_rotaciones_20261006.md.


## 2026-10-06 — NBA: pendientes e intradía (NBA-RUN-041)

Se aceptaron seis rotaciones adicionales mediante intervalos administrativos de tiempo cero y exposición oficial de OT:6147/6150,259687tramos; tres contradicciones persisten. Descarga médica:815/816cortes nuevos;1631versiones/165729filas,75451jugadores nuevos con ID. Se preservan continuaciones NOTYETSUBMITTED/filas nombradas, razones literales y diferencias upstream; once identidades exactas CuiYongxi se resuelven en una versión separada.3859cambios de estado/motivo y1215selecciones retrospectivasT60;1216horarios únicos corroborados,40búsquedas vacías separadas. Recepción original/PIT no acreditados. Props3756previos/44snapshots revalidados,cero llamadas; repos fijados sin nuevas cuotas; plan36solicitudes/720créditos sigue pendiente de autorización por límite500agotado.140ZenRowsconfirmados nuevos;riesgo1752/3200,sincompras.189NBA/707harness y controles auxiliares;2280evidencias/40corridas/gates/producción previos preservados. Informe:docs/nba_pendientes_intradia_20261006.md.

Corrección de checklist NBA-RUN-041: el reintento del auxiliar de sellado marcó por error la línea de pendientes como completada. Se restituyó la casilla abierta para las tres rotaciones, intradía/PIT y props; el informe, datasets y evidencias del checkpoint permanecen intactos. La instantánea incorrecta se conserva y esta corrección se registra aparte.

## 2026-10-07 — Línea de alta probabilidad activada y "marca el local / el visitante" desplegado

- Sellado del 7-oct (08:00 UTC) correcto con el bloque vacío (`n_alta_prob: 0`).
  La tarea programada de activación (08:30 UTC) se quedó esperando el
  permiso de su primer `Bash` (nadie lo aprobó): se detuvo y la activación se
  hizo a mano tras repetir sus comprobaciones (verify 9 lotes, salud, tablas
  vacías, log del job). Lección: una tarea programada que usa `ssh` necesita
  sus permisos aprobados de antemano ("Run now" en una prueba inocua).
- "Marca el local / el visitante" (más de 0,5 goles de un equipo), decisión
  del usuario: probabilidad del mismo ajuste de goles (prueba histórica:
  local 86,97→88,52, visitante 86,10→87,45); cuota de referencia de las casas
  blandas desde API-Football bets 16/17 (con guarda por nombre); `db/042`
  amplía el CHECK con guardia. El control vigila los dos lados como UN grupo
  (`team_totals`), decisión del usuario: en el Monte Carlo del revisor da
  menos pausas en falso y más detección que por separado.
- Tasas del control con mezcla realista y grupo fusionado: ~16 % de líneas
  con alguna pausa de grupo en falso, ~5 % de la línea entera; detección de
  un déficit de 3 pts ~82 % / ~73 %. Las cifras del 6-oct (9,7 % / 3 % /
  88 %) suponían probabilidades uniformes y 4 grupos.
- Despliegue 17:02 UTC: `db/042` + `ALTA_PROB_ENABLED=1` + reinicio en un
  minuto seguro. Vista previa: 10 pronósticos de 17 partidos (5 de equipo).
  Primeros pronósticos reales: sellado del 8-oct, 08:00 UTC.


## 2026-10-07 — NBA: archivo público y rotaciones (NBA-RUN-042)

Las tres actas completas acreditan entrada/salida al mismo reloj detenido;6150/6150rotaciones y259826tramos, sin segundos positivos para actores administrativos. ArchivoKamran fijado/verificado:3662JSON,228324pares nuevos de puntos/3429partidos,232080pares combinados; horizontes6,07–16,79horas, noT60/T15. Calendarios ESPN2024/25verificados porasset/hash más2026sellado, roster/nombres/cronología estrictos; rechazosconservados. Médico:223PDFs disponibles en240rutas/7fechas,13previos y210nuevos;1841versiones/186634filas,18750nominales nuevas conID,22CuiYongxi exactos. Control de motivo final limitado a página deuna fila; diferencias literales de páginas normales conservadas. Primerdía2023–24disponible desde17:30, compatible conconstanteupstream;16:30noacreditado, no se concluye bloqueoIP. Recepciónoriginal/reglas de liquidación siguenpendientes.4939evidencias/41corridas/89eventosprevios preservados;189NBA,707harnessantes/732después portrabajo concurrente preservado.30ZenRowsnuevos,riesgo1782/3200,OddsAPI0nuevo/500agotado,sincompras;producción/modelo/gatesintactos. Informe:docs/nba_props_y_rotaciones_20261007.md.

Presentación legible de NBA-RUN-042: docs/nba_resultados_validados_20261007.md. El informe técnico/datasets sellados no se modifican; la casilla RUN-041 queda identificada como estado histórico, con pendientes actuales en RUN-042. Revisión documental registrada aparte.

## 2026-10-07 — web: portada inspirada en TennisPredictions y paleta del usuario

Se conserva la jerarquía editorial/calendario/filtros/filas por competición de
la referencia pública, adaptada al criterio de QuantFut. SingleFile CLI 2.18.0
capturó el HTML con manifiesto en `.local/design-reference/`; no es dependencia
de la web ni reproduce el backend ajeno. El usuario aportó azul noche #0b132b,
pizarra #1c2541 y esmeralda #10b981: superficies y cabecera se armonizan con
esa paleta. El tablero continúa siendo demo identificada; agenda real y puerta
comercial permanecen separadas, con error de API visible. No se activó ninguna
publicación, cuenta ni pago ni se desplegó. Nueve pruebas del frontend pasan;
732 pruebas Python pasaron antes de las ediciones de presentación. El script
shell no encontró utilidades dentro del entorno restringido y su OK no se
consideró válido; se ejecutó la suite con el Python del proyecto. Revisión en
navegador de filtros, fechas, fichas, Pick del día y combinadas. Propuesta y
siguiente fase: `docs/web_diseno_tennispredictions_20261007.md`.
- Prueba histórica con la regla desplegada (firma d5cbc3151164): 9.021 de
  14.216 partidos (63 %), prometido 82,62 %, real 83,23 %; todos los mercados
  pasan (equipo local 86,97→88,52, visitante 86,10→87,45).

## 2026-10-07 — web: cuenta y modelo de paquetes/suscripciones

El usuario aclaró que «su modelo» significa paquetes y suscripciones. Se
adaptaron las vistas de acceso, recuperación, registro, cuenta, catálogo de
picks y planes de 1/3/6 meses más Club de TennisPredictions. SingleFile guardó
las páginas públicas; el acceso se capturó sin sesión. El panel de referencia
se inspeccionó sin guardar ni incorporar su información personal.

La selección de modalidad y el perfil son estado visual de la pestaña, no
autorización de servidor. Identidad y contraseña son sintéticas, de solo
lectura; no se envían correos ni se crea una orden. Mi cuenta mantiene «Sin
suscripción activa» incluso después de revisar el pedido. Preferencias de
cuotas/ligas conservan la persistencia local existente; favoritos demo se
añaden y quitan durante la sesión. El resumen conserva el cobro deshabilitado.
Los importes de referencia usan centavos enteros: equivalentes mensuales y
ahorros derivados del total, corrigiendo discrepancias visibles en la referencia.

13 pruebas frontend y 11 del servidor web aprobadas. Validación en navegador
del recorrido de acceso → pedido, recuperación sin correo, preferencias,
favoritos, ausencia de activación y vistas 320/390/768/1024/1440 px. Se corrigió
un desbordamiento de 4 px del catálogo a 320 px. El chequeo shell final volvió
a omitir utilidades/Python en este entorno: su «OK» no cuenta como validación;
las pruebas directas son la evidencia. Sin despliegue ni cambio de gates.
Propuesta: docs/modelo_paquetes_suscripciones_20261007.md; capturas propias en
la carpeta local ignorada `.local/design-reference/quantfut-{acceso,cuenta,suscripciones}.jpg`.

## 2026-10-07 — web: despliegue autorizado

Por petición explícita del usuario, commit de producto 2266311 creado localmente
y desplegado en pronosticosdeportivos.pro. Sin remoto Git configurado: transferencia
SSH de paquete generado desde el commit. Base de archivos cotejada antes de sustituir;
imagen derivada de la API ejecutándose, solo seis archivos de presentación/rutas.
Respaldo en /home/qf/web-release-2266311/backup e imagen previa conservada.
Solo API recreada; worker, DB, caché, proxy y Grafana conservan sus identificadores.
Gate, variables, modelo y base intactos; cuentas y cobros siguen en demo.

El arnés completo se ejecutó correctamente al fijar PATH de Git Bash: 732 pruebas
aprobadas, una advertencia; frontend 13 aprobadas. Salud origen/HTTPS status ok,
archivos cotejados por SHA-256; el HTML público solo incorpora el beacon existente
de Cloudflare. Navegador público comprobó acceso demo → pedido bloqueado y cuenta
sin suscripción activa. Registro: docs/web_despliegue_20261007.md.

## 2026-10-07 — Fase comercial desbloqueada: cuentas, API de clientes y panel

Decisión del usuario: avanzar ya con cuentas y panel de administración sin
esperar a la puerta de CLV. La puerta sigue decidiendo si hay picks que
vender (`PUBLISH_PICKS_ENABLED`); las cuentas existen aunque esté cerrada.

- Un solo FastAPI para web, app Flutter y panel (se mantiene la decisión
  2026-09-23). `/app/v1` sin secretos en el cliente: bearer opaco de 15 min
  en Redis + refresh de 30 días hasheado en Postgres y rotado en cada uso;
  el reuso de un refresh revoca la sesión (robo de token). Opaco y no JWT:
  suspender o cerrar sesiones corta en el acto y no hace falta PyJWT.
- `ACCOUNTS_ENABLED` apagado por defecto: desplegar no abre altas solo.
- `subscriptions` solo admite revocar una vez (trigger); `admin_audit`
  inmutable con `deny_mutation()`. Una concesión manual no es ingreso: los
  ingresos del dashboard solo cuentan `source='payment'`.
- Panel: Tabler + Tabler Icons + Chart.js vendorizados (MIT, versiones y
  SHA en `static/vendor/README.md`) para mantener CSP `'self'` sin
  `unsafe-inline`. Se descartaron SQLAdmin/starlette-admin (exigen ORM y
  chocan con los triggers) y react-admin/refine (build de Node y tokens en
  JS). El pipeline sigue siendo de solo lectura desde el panel.
- Trampa encontrada: `main.py` manda `Referrer-Policy: no-referrer`, y con
  eso Chrome envía `Origin: null` en los POST propios; la defensa CSRF se
  apoya en `Sec-Fetch-Site` + token HMAC, no en `Origin`.
- El tope de 10/min de `/control` se subió a 2× el general y cubre también
  `/static`: con varias páginas daba 429 navegando normalmente.
- Verificado: 753 tests + 6 de integración contra un Postgres 16 desechable
  con todo `db/*.sql` (rotación/reuso, suspensión, renovación sin perder
  días, de por vida, revocación única); flujo HTTP completo y panel en
  navegador. Sin despliegue: falta aplicar `db/043`, `pip install` y
  `ACCOUNTS_ENABLED=1` en el VPS.
- Pendiente de decisión del usuario: procesador de pago y proveedor de
  correo. Guía de la app: `docs/app_api_flutter.md`.


## 2026-10-07 — NBA: calendario completo y recuperación médica (NBA-RUN-043)

Horarios corroborados para 6150 regulares, incluidos diez neutrales con ambas referencias NBA @ y designación ESPN conservada. +2784 reportes/368902 filas; 6129/6150 selecciones médicas retrospectivas con reloj/contexto literal concordante, 6037 ambos equipos enviados. +1350 puntos mediante seis alias oficiales exactos/308 partidos, total233430; 27151 candidatos multimerkado/34 partidos separados por relojes libro/mercado y vecinos ausentes. Cinco repos públicos fijados/blobs verificados,97 PDFs archivados, cero llamadas pagadas nuevas; presupuesto previo sin aumento. 9641 evidencias/42 corridas/91 eventos conservados; arnés732/732; producciónNBA/modelo/gates sin cambios, trabajo concurrente preservado. Recepción original/settlement y demás huecos siguen pendientes. Informe:docs/nba_recuperacion_medica_y_props_20261007.md.

## 2026-10-07 — Correo transaccional con Proton Mail

Decisión del usuario: Proton Mail. Hay dos formas y el código es el mismo
(SMTP genérico en `comercial/correo.py`); solo cambia `.env`:
- Recomendada: envío SMTP oficial de Proton (`smtp.protonmail.ch:587`,
  STARTTLS, token SMTP). Exige plan de pago y dominio propio en Proton; no
  añade servicios que mantener.
- Alternativa: Proton Mail Bridge en Compose (perfil `proton-bridge`) con
  shenxn/protonmail-bridge-docker. Su imagen de Docker Hub está parada en la
  3.19 (abr-2025) aunque el repo sigue (v3.27): se compila desde un commit
  fijo con el bridge v3.27.1. El login es interactivo (2FA): lo hace el
  usuario en el VPS.
- Proton no es para envíos masivos y limita por reputación: aquí solo
  salen correos uno a uno disparados por el cliente.
- Los enlaces solo guardan sha256; GET nunca consume el token (los filtros
  de correo visitan enlaces), solo el POST del botón. `forgot` responde 202
  siempre y envía en segundo plano. Restablecer cierra todas las sesiones.
- Verificado con un servidor SMTP real en local (aiosmtpd con STARTTLS y
  certificado autofirmado): llega autenticado y cifrado, con verificación
  estricta se rechaza el autofirmado y una contraseña mala no envía.
  Flujo completo en navegador: enlace → nueva contraseña → login.


## 2026-10-07 — NBA: veinte relojes corroborados (NBA-RUN-044)

+20 selecciones retrospectivas con PDF ET y metadata BRef de fecha/equipos/reloj exactos; corte60min antes del reloj más temprano; ESPN12–50min más tarde se conserva sin atribuir causa. Total6149/6150, ambos enviados6056, algún equipo ausente93. BOS@NYK25oct2023 ausente en diez PDFs inspeccionados; no se infiere sano/enviado. +3 reportes/167 filas, total4628/555703; dos parsers y todos los nombres conID. 22tareasZenRows/200créditos, riesgo1982/3200;3GETPDFsinpago;OddsAPI0. 18952evidencias/43corridas/92eventos previos preservados; arnés753/764; producción/modelos/gates intactos. Corrección v2 de atribución de zona: ET lo declara PDF, no metadataBRef. docs/nba_horarios_medicos_corroborados_20261007.md.

## 2026-10-07 — Despliegue de la fase comercial (commit 3d40e05)

Autorizado por el usuario. Paquete `git archive` verificado por SHA-256;
base del servidor cotejada con HEAD antes de sustituir. Respaldo en
`~/release-3d40e05/backup.tgz`, imagen previa `quantfut-api:before-3d40e05`.
Imagen nueva derivada de la que corría (+argon2-cffi, jinja2, src/), solo
`api` recreado con `--no-deps --no-build`; worker, db, caché y proxy
intactos. `ACCOUNTS_ENABLED=0`: `/app/v1` responde 503 hasta abrir altas.
El token SMTP lo escribió el usuario con un script de entrada oculta
(`~/release-3d40e05/poner_token.sh`): nunca pasó por el agente. Login SMTP
con Proton verificado sin enviar correo.
Hallazgo: `ADMIN_CONSOLE_PASSWORD_HASH` ya estaba vacío en `.env` antes del
despliegue (en `.env.bak-2026-10-07` de las 19:45 sí estaba): `/control`
devuelve 503. No se restauró sin permiso del usuario.
Reversión: retag `quantfut-api:before-3d40e05` → `latest`, restaurar
`backup.tgz` y recrear `api`; las tablas nuevas no afectan al código previo.
Con permiso del usuario se restauró la línea del hash desde
`.env.bak-2026-10-07` (idéntica byte a byte; resto del `.env` sin cambios,
copia previa en `~/release-3d40e05/env.antes-restaurar-hash`). `/control`:
401 en origen sin credenciales y 302 a Cloudflare Access desde fuera.
Lección: al reescribir `.env` en un despliegue, comparar después las claves
contra la copia previa; un valor vacío no da error, solo un 503 del panel.
Altas abiertas (`ACCOUNTS_ENABLED=1`) por decisión del usuario. Verificado
en producción sin crear cuentas ni enviar correos: planes 200 (también
desde el dominio público), login inexistente 401, olvido 202, picks sin
sesión 401, `/cuenta` con token falso 400, panel 401. Trampa del script de
despliegue: `diff` sale con 1 si hay cambios y `set -e` cortó antes de
recrear la API; comprobar siempre que el servicio se recreó.

## 2026-10-07 — NBA: props y reglas México/LATAM (NBA-RUN-045)

+9702pares de puntos/145partidos por unión única fecha/equipos con calendario NBA/ESPN y box canónico; mapas originales erróneos conservados,21eventos sin resolver. Total243132 (239979PTS/2961REB/192AST);233430previos exactos,27151candidatos aparte. 14blobs de dos repos extra;78tarjetas sin relojes completos,0pares adoptados de esos dos. Cinco documentos oficiales/cuatrocasas/MX-CO-PE; vigencia histórica desconocida y sin coincidencia con11books de cuotas. Recepción243132cuotas/4628PDFs todaOct2026,0pruebas originales; estructuraycontratocandidate confixtures explícitos sintéticos,ninguna liquidación automática.31GETintentados,0OddsAPI/0ZenRows/cero compras;riesgo1982/3200.19062evidencias/44corridas/93eventos previos preservados,21controles y arnés764/764;producción/modelos/gates sin cambios. docs/nba_props_y_reglas_latam_20261007.md.

## 2026-10-07 — NBA: versiones archivadas y mecánica de liquidación (NBA-RUN-046)

Seis capturas realesCaliente2025/Betway2021–2024 con SHA1CDXbase32exacto y Memento concordante; cinco secciones históricas Betway y secciónCaliente iguales a actuales, sin inferir vigencia continua. +perfilBetwayMX,total5perfiles;8documentosreglas nuevos/1ayuda. CodereARredirigeMéxico, cuarentena. Usuario confirma sinlogs originales;4978artefactos pornombre no prueban recepción antigua. Evaluador localv3 con38controles sintéticos yrecibosactuales exclusivos;243132pares todos pendientes,0liquidacionesreales/0ROI.19165evidencias/45corridas/94eventos previos verificados; arnés764/764.28intentosGET,0Odds/0ZenRows,riesgo1982/3200;sin compras. Producción/gates/modelos intactos;intermediosfallidos conservados. docs/nba_reglas_archivadas_y_liquidacion_20261007.md.


## 2026-10-07 — NBA: corrección documental del arnés (NBA-RUN-047)

El informe RUN-046 y su nota de progreso conservaban el recuento anterior764/764. Log final y verificación sellados acreditan764antes/767después,9omisionesantes/10después. Versiónv2 del informe corrige el texto; documentos/evidencias/corridas previos íntegros.0capturas/0créditos/0cambiosdataset oproducción/gates. docs/nba_reglas_archivadas_y_liquidacion_v2_20261007.md.

## 2026-10-07 — Web conectada a las cuentas reales

La web deja la sesión demo y usa `/app/v1` con `frontend/cuenta-api.js`.
Decisiones: en el navegador el refresh vive en una cookie HttpOnly
(SameSite=Strict, `Path=/app/v1/auth`) y el acceso solo en memoria; nada en
localStorage, para que un XSS no se lleve una sesión de 30 días. La cabecera
`X-QF-Client: web` activa ese modo y fuerza preflight CORS desde otro origen,
así que la cookie no sirve fuera del dominio. Dos pestañas que arrancan a la
vez mandan la misma cookie: la segunda tenía el refresh recién rotado y la
detección de reuso habría revocado la sesión; se da una gracia de 20 s solo
en modo web (la app serializa sus refresh y no la necesita). Un indicador
`qf_hay_sesion=1` sin secreto evita un refresh 401 por cada visitante.
Verificado en navegador contra el FastAPI completo en local: registro, error
de login, login, recarga con sesión recuperada, plan concedido visible como
Plus y cierre de sesión que borra ambas cookies.

## 2026-10-07 — Despliegue de la web con cuentas reales (commit 9b9d180)

Autorizado por el usuario. Solo los 8 archivos de ejecución (5 del frontend,
3 de la API); `ACCESS_FLOW.md`, `package.json` y `server.mjs` del servidor
difieren del repo pero no se sirven y no se tocaron. Base cotejada contra
3d40e05, paquete verificado por SHA-256, respaldo en
`~/release-9b9d180/backup.tgz`, imagen previa `quantfut-api:before-9b9d180`;
solo `api` recreado. Los archivos públicos (también a través de Cloudflare)
coinciden byte a byte con el commit. En producción el acceso muestra el
formulario real, sin aviso demo, sin errores de consola y sin refresh para
visitantes anónimos. No se creó ninguna cuenta en producción.

## 2026-10-07 — La web lee los precios del panel

`MEMBERSHIP_PLANS` (precios fijos en JS) desaparece: importes, duración,
moneda y qué planes se venden salen de `/app/v1/plans`, que es lo que edita
el panel. En el código solo quedan los textos por `plan_code`; un plan nuevo
sin texto usa el nombre del panel. El ahorro se calcula contra el plan
mensual de la misma lista y, si no se vende, no se inventa. `/plans` pasa a
un router público sin `ACCOUNTS_ENABLED`: los precios son información
pública y la web no debe romperse si se cierran las altas. Sin precios
cargados la web dice «Cargando»/«Reintentar» en vez de enseñar importes
viejos. Verificado en local: cambiar 3 meses a 29,99 en el panel se ve en
la web al recargar ($10.00/mes, ahorro $14.98) y Club, desactivado, no sale.

## 2026-10-07 — Despliegue de precios desde el panel (commit f94a5bc)

Autorizado por el usuario. 6 archivos de ejecución, base cotejada contra
9b9d180, paquete verificado por SHA-256, respaldo en
`~/release-f94a5bc/backup.tgz`, imagen previa `quantfut-api:before-f94a5bc`;
solo `api` recreado. En producción `#planes` muestra los 3 planes activos
del panel (14,99 / 33,99 / 53,99 USD) sin errores de consola. Ojo: Cloudflare
sigue sirviendo `/app.js` sin versión desde caché; la portada pide
`app.js?v=…` y esa URL sí es la nueva: por eso las versiones `?v=` deben
recalcularse siempre que cambie un archivo.


## 2026-10-07 — NBA: todas las casas solicitadas (NBA-RUN-048)

Revisión de 22 combinaciones casa/país más Rushbet México: 25 perfiles, cinco anteriores preservados y veinte nuevos, 72 cláusulas (49 nuevas). La matriz distingue cláusulas recuperadas/observadas de páginas vacías, redirecciones, contenido educativo, PDF físico de Te Apuesto y proveedor Kambi sin vínculo contractual probado por Luckia. Sportium España exige un segundo; bwin separa simples/Build a Bet; Winamax tiene excepción limitada de logros para titular con menos de doce minutos. Son perfiles de investigación, no liquidaciones reales.

21 índices consultados, cinco JSON válidos y nueve entradas históricas; nueve replays fallaron por conexión, cero contenido archivado nuevo validado. Se preservan los seis replays RUN-046. 87 GET del colector, 98 transacciones registradas y un diagnóstico adicional; cero créditos pagados/purchases. 19.260 evidencias y 47 corridas previas verificadas; seis controles negativos de procedencia. Arnés 767 antes/768 después, diez omisiones ambas; incremento concurrente sin atribuirlo al catálogo. Producción NBA/datasets/gates intactos. Recibos originales y contratos por ticket ausentes; las 243.132 parejas siguen sin liquidación real. docs/nba_casas_hispanohablantes_reglas_20261007.md.


## 2026-10-07 — NBA: reglas Colombia y props públicos (NBA-RUN-049)

BetPlay recuperado mediante desplegables DOM; Sportium Colombia mediante ZenRows MCP.18 cláusulas en dos revisiones;25 perfiles/72 cláusulas anteriores íntegros. Participación BetPlay con frase imprecisa y suspensión con ancla ambigua, Sportium43 minutos/abandono sin precedencia resuelta. No transferir mínimo español de un segundo ni push de totales a jugador. Inkabet/Betsson Perú tienen enlaces oficiales/footer peruano, pero rutas devolvieron landings; Apuesta Total sin cuerpo de reglamento y Dorado general.

Dos repos fijados,19 blobs verificados y26 GET GitHub:77 filas PTS30/REB29/AST18 en cuarentena separada,17 cruzan casas y faltan relojes del proveedor; commits del archivo constan en febrero12. Otro repo publica agregados/sintéticos, no cuotas.0 parejas nuevas,0 liquidaciones,0 contratos/recibos históricos acreditados. Diez scrapes MCP; reserva250, cota2232/3200; cuenta1674→1804, delta130 sin atribución exclusiva por petición. Salto35 activa parada; sin compras ni OddsAPI nuevo.48 corridas/19636 evidencias/97 eventos previos íntegros; ocho controles negativos; arnés768/10 antes y después. Producción NBA y gates intactos. docs/nba_reglas_colombia_y_props_candidatos_20261007.md.


## 2026-10-07 — NBA: minutos de regulación y F4 (NBA-RUN-050)

Continuar F4 como investigación: el candidato reciente mejora CRPS3,6638→3,5479 y MAE4,9654→4,8694 minutos en63155 casos/3256 juegos/433 fechas, tres temporadas y nueve bloques. La cobertura nominal80 solo llega70,663%, no hay disponibilidad previa ni coherencia conjunta de equipo; no promover ni aprobar G4. Historial mínimo10 positivo de la misma temporada, exclusión estricta de toda fecha objetivo. Intervalos exploratorios por fecha, sin test confirmatorio intacto.

159075 etiquetas desde6150 partidos/259826 tramos,12300 totales equipo de240 minutos. Periodos1–4 separados de OT, ceros/DNP y archivos originales intactos. Primer intento rechazado por28 namespaces vacíos de0022400942 antes de métricas; capa derivada acredita roster/persona/equipo/estadísticas/estado completos contra NBA V3 archivado. Protocolos99/100 y fuentes previas preservados.

213 pruebas NBA,24 nuevas; arnés768/10 antes/después. Revisión independiente de fórmula de126310 CRPS e historiales63155, resúmenes/bootstrap reproducidos; revisión humana propia.49 corridas/19744 evidencias anteriores íntegras, prefijo98 eventos conservado, checkpoint101. Cero llamadas/purchases nuevas; ZenRows2232/3200 y243132 parejas de cuotas preservados. Sin recibos originales, liquidaciones, despliegue ni promoción de gates. Seguir disponibilidad/rol jerárquico y rotaciones conjuntas antes de F5; pendientes LATAM/REB/AST/reglas por ticket continúan. docs/nba_f4_minutos_regulacion_20261007.md.


## 2026-10-07 — NBA: cobertura y escenarios, continuidad F5 (NBA-RUN-051)

Se corrige cobertura nominal80:70,663%→80,537% posterior y80,534% validación. Ajuste1,25 global/1,30 historial<12, entrenado exclusivamente en20630 casos2021-22 y congelado antes de validar2022-23/evaluar2023-26. CRPS empeora3,5479→3,5782 y MAE4,8694→4,8873; conservar RUN050 como referencia principal, no promover el ajuste por cobertura secundaria. Histórico ya inspeccionado, sin confirmación intacta.

3246 escenarios completos de equipo/415488 realizaciones conservan240 minutos, soporte0–48 y DNP0.4134 equipos excluidos por historial incompleto. Disponibilidad observada después del evento solo como diagnóstico oracle, no como predicción. Restricciones inviables/IDs/equipos cruzados se rechazan.234 pruebas NBA,21 nuevas; arnés768/10 antes y después.84002 pronósticos revisados,168004 CRPS independientes, nueve matrices regeneradas con hash exacto.

50 corridas/19786 evidencias y prefijo101 eventos intactos; protocolos102/103, checkpoint104.0 APIs/compras; ZenRows2232/3200, cuotas/contratos/recepción original y gates preservados. Traspaso F5 de investigación con rutas/hashes y referencia anterior; noOT mientras las estadísticas por periodo no estén verificadas. F4 de disponibilidad/rol y dependencia conjunta sigue pendiente; no producción. docs/nba_f4_calibracion_y_coherencia_20261007.md.


## 2026-10-07 — NBA: distribución de rebotes F5 (NBA-RUN-052)

negative_binomial elegida solo en19315 casos de validación2022-23 tras ajustar dispersión con19513 de2021-22. Parámetros/elección congelados antes de59816 casos2023-26. CRPS1.376733→1.332904, MAE1.944846→1.911748. Candidato de investigación favorable al baseline en este replay; sin promoción ni confirmación intacta.

6150 juegos/159075 etiquetas preservadas,5840 sinOT,310 OT excluidos por falta de estadísticas de regulación;98644 features causales, sin resultados del día objetivo. Prior30 minutos a0,18 heredado; historia20/min10 positiva sinOT para tasa, minutos RUN050 para distribución. Diagnóstico ampliado RUN051 separado; no escenarios oracle en métricas predictivas. Probabilidades under/push/over son categorías matemáticas sin contrato ni void conocido. PIT aleatorizado y masa discreta evitan confundir cobertura central con80 exacto.

Primer intento105 falló al serializar bool NumPy antes de validación; fuentes conservadas, entradas reutilizadas con hashes y AST iguales. Canon106/ajuste107/selección108/checkpoint109.265 pruebas NBA,31 nuevas; arnés768/10 antes/después.98644 historias,179448 PMFs/CRPS independientes y27 distribuciones regeneradas.51 corridas/19819 evidencias previas intactas.0 APIs/compras, ZenRows2232/3200; recepción/contratos/cuotas/gates sin cambios. F6 de investigación preparado con hashes, no producción. docs/nba_f5_distribucion_rebotes_20261007.md.


## 2026-10-07 — NBA: ensayos de entrega F6 (NBA-RUN-053)

El plan define F6 como entrega/observación, no solo auditoría temporal. Recuperar reclamaciones interrumpidas únicamente tras caducar a unknown, sin volver a cola; conservar sending fresco y reclamar antes del transporte. Hora real de intento separada del as_of solicitado y nueva comprobación de caducidad antes del remitente. Reinicios, concurrencia, auditoría fallida, 429 y timeout verificados sin duplicados.

Diez fixtures/60 cortes a0/15/30/60/120/300s, cinco outboxes y26 pruebas nuevas;291NBA y768general/10omisiones. Revisiones se seleccionan por recepción propia, otro operador no sustituye contrato y error/suspensión no reutiliza cuota anterior; diferencias son brackets de observaciones, no duración exacta ni ejecución real. Solo remitentes inyectados;0mensajes/APIs/compras. Latencia local simulada no demuestra p95 del canal.

52corridas/19873evidencias/109eventos previos íntegros; protocolo110/checkpoint111. Sin credenciales NBA ni campos del puente operativo, herramientas Postgres/Docker ausentes en PATH y ninguna integración DB probada. SQLite local no apruebaF6.1. PropuestaF7 draft_not_started: selección histórica participante positivo/noOT no es universo previo. Postgres/canal/recepción anclada/contratos/OT y disponibilidad reales pendientes. Gates/cuotas/reglas/budget2232/3200 y producción sin cambios. docs/nba_f6_entrega_y_observaciones_20261007.md.


## 2026-10-08 — NBA: Postgres durable local (NBA-RUN-054)

PostgreSQL16.15 existía fuera del PATH. Clúster NBA propio127.0.0.1:55434/base nba_delivery_run54, SCRAM/secretos privados y trabajador limitado; fútbol intacto. Sellado+cola, reclamación+intento y resultado+evento atómicos. Concurrencia/rollback/inmutabilidad/expiración/resultado incierto verificados.39eventos/19mensajes exportados; parada inmediata real y recuperación WAL preservaron queued/sent/sending y cadena; ninguna repetición ciega. Clúster detenido.

309NBA/18nuevas,768general/10omisiones;11controles adicionales propietario. Pipe Windows inicial corregido antes del protocolo112; expectativa de QA sobre TRUNCATE corregida y primer intento conservado, sin cambiar código/protocolo congelados.53corridas/19920evidencias/111eventos íntegros, checkpoint113.0APIs de datos/compras/mensajes; transporte en memoria. Implementación Postgres local probada, no canal/latencia/cuotas/backup/rendimiento productivo. G6/F7 y gates pendientes, ZenRows2232/3200 intacto. docs/nba_f6_postgres_durable_20261008.md.


## 2026-10-08 — NBA: backup y canal VPS (NBA-RUN-055)

Usuario indicó credenciales en VPS y usar las de fútbol. Solo TG_BOT_TOKEN/TG_ALERT_CHAT se leen allí, sin copia local ni cambios del entorno/servicios de fútbol. Un mensaje PRUEBA TÉCNICA NBA aceptado por Telegram: message_id6 y chat configurado coincide; repetición del mismo ID bloqueada.14.625006s sellado→acuse local incluyendo SSH, n1; no cumple ni demuestra p95<2s y recepción en dispositivo desconocida.

pg_dump/pg_restore reales en base nueva:39eventos/19mensajes idénticos a fuente; fuente intacta después, restaurada75eventos/36mensajes tras tests/envío.330NBA/21nuevas,768general/10omisiones. Métricas conservan faltantes/anomalías y ledger válido. Roles preexistentes; no recuperación integral en otro servidor ni retención automática. Servidor de ensayo detenido.

Protocolo114/primer intento conservado: Python3.10 del VPS no importa datetime.UTC; falla antes de credenciales/HTTP, estado unknown sin reintento automático. Diagnóstico de solo lectura acreditó causa; timezone.utc compatible y nuevo protocolo115 antes del único POST.54corridas/19962evidencias/113eventos íntegros, checkpoint116.1mensaje real autorizado,0APIs de datos pagadas/compras; cota2232/3200 intacta. G6/cuotas/recepción externa/OT/disponibilidad/F7 y producción pendientes. docs/nba_f6_backup_y_canal_vps_20261008.md.


## 2026-10-08 — NBA: transporte y recuperación VPS (NBA-RUN-056)

Reutilizar SSH solo no bastó: tres acuses7,75–10,75s. Diagnóstico públicoHTTPS0,262/0,016s precedió transporte HTTPSConnection reutilizable; dos acuses locales desde sellado0,421309/0,484205s, arranque separado4,312s. Cinco mensajes técnicos totalesIDs7–11, destino autorizado coincide y cada repetición bloqueada. Muestras diagnósticasn3/n2, no p95 operativo ni recepción en dispositivo. Credenciales solo enVPS, fútbol intacto.

Respaldo congeladoRUN055 del ledger/outbox39eventos19mensajes restaurado en contenedor propioVPSPostgres16.15/rednone/sinpuertos; roles recreados sin contraseñas previas, seis mutaciones rechazadas y reinicio idéntico. TrabajadorNOLOGIN para SET ROLE, no pruebaSCRAMremota. Contenedor eliminado tras verificar etiqueta/imagen; copia600/carpeta700 retenida fuera del equipo. No backup integral histórico ni últimasalertas ni automatización/retención periódica.

Colector de cuerpo/hash/recibo propio y controles de contrato preparado. MarcadorNBA403local, marcador/calendario403VPS; tres cuerpos conservados, cero datos/contratos nuevos. Ecosacotan relojVPS−local−0,902…−0,725s pese aNTPVPSyes, sin cambios de reloj; métricaslocales no restan UTCentrehosts. F7propuesta actualizada, no iniciada: universo/lesiones/rol/OT/contratos/anclaje/relojes/operación pendientes.

Primerintento117:352pasan/1PermissionErrorenmanifiestotemporal antes de accionesexternas; pruebaaislada pasa sincambiocódigo. Versión118base/carpeta nuevas353pasan; diagnóstico119,HTTPS120 con356pasan, capturas121/relojes122,checkpoint123. Arnés768/10antes/final.55corridas/20038evidencias/116eventos anteriores conservados; revisiónmismaautor con scriptseparado.0APIsdatos pagadas/compras,5POSTTelegram técnicos, cota2232/3200 y todosgates/producción intactos. docs/nba_f6_transporte_y_recuperacion_vps_20261008.md.


## 2026-10-08 — NBA: captura anclada y operación de investigación (NBA-RUN-057)

Se recuperaron seis eventos de pretemporada, doce rosters con 247 jugadores/240 IDs NBA estables, 101 observaciones de lesiones y 14 precios públicos de Caliente México. Cruce previo de nombre/DOB acredita identidad estable, no equipo actual. Lesiones genéricas/Active no acreditan disponibilidad por partido; precios de equipo sin props individuales, reloj de proveedor o reglas completas. NBA jugadores403; páginas NBA200 sin calendario/quintetos en datos incrustados; Codere redirección detenida; ruta candidata BetPlay URLError, cero contratos aceptados.

DigiCert RFC3161 verificó nonce, contenido y cadena para manifiesto de 25 recibos nuevos/prefijo130 a17:39:29UTC y primer manifiesto VPS15recibos a17:52:14UTC. Contenido alterado/nonce distinto rechazados; prueba VPS revalidada localmente. Existencia nueva, no recibos históricos ni exactitud del proveedor ni revocación OCSP/CRL. Consulta BetPlay posterior no anclada; checkpoint final tampoco.

Colector público nuevo en VPS, usuario1001/red propia/raíz read-only/sinpuertos/cap-dropALL/no-new-privileges, CPU0,25/128MiB/64pids; imagen base fijada por digest. Ciclo15min; lesiones/rosters por hora; sello máximo diario sin reintento inmediato. Primer intento de activación se detuvo ante Caliente403: catorce ESPN200 válidos. Segundo protocolo activó mismo código con salud source_degraded explícita; reinicio preservó capturas y seis servicios existentes conservan identidad. Sin secretos de fútbol, mensajes o picks.

Respaldo consistente de ledger/cuerpos diario y máximo siete archivos generados verificados; no borra cuerpos originales. Pausa a16GiBpropios o menos de10GiB libres. Primer archivo restaurado localmente con15eventos y cuerpos idénticos; 12archivos copiados incluyendo pruebas temporales. Copia fuera del VPS puntual, no periódica; archivos diarios aún no incluyen sellos/modelos/cola completa.

Dos fallos de normalización preservados, luego corregidos por IDs desde enlaces y alias de etiquetas sin aceptar precios contradictorios. Tres pruebas de respaldo fallaron por handles SQLite abiertos enWindows, corregidos con cierre explícito:31casos pasan y tres controles operativos adicionales pasan. Dos reconstrucciones iniciales fallaron por suponer orden de respuestas paralelas; revisión correcta usa hashes de evento y pasa sin modificar los datos. Suite completa390sinomisiones conPostgresNBA nuevo; source39eventos/19mensajes intacto y clúster detenido. Arnés768/10antes/final.56corridas/20143evidencias/123eventos anteriores preservados; revisión misma autoría/scriptseparado.

Protocolos124–133, checkpoint134; 26intentos públicos locales y15primerVPS, dos solicitudes TSA gratuitas, cero APIdeportiva pagada/mensajes/compras, cota2232/3200sin cambios. Captura de investigación continua activa; G0–G9/alcance/decisiones y producción comercial intactos. F7 sin iniciar por contratos/universo/rol/OT y criterios finales. docs/nba_f6_captura_anclada_y_operacion_20261008.md.


## 2026-10-08 — NBA: partido completo y contexto oficial (NBA-RUN-058)

Nuevas copias periódicas excluidas por instrucción expresa; servicio anterior sin cambios.35capturas gratuitas:12perfiles oficiales NBA2026-27 con249listados y245/247identidades ESPN corroboradas por nombre/team/DOB, cincoIDsNBA nuevos. Tres alias generacionales únicos aceptados; MaliqBrown/SteveSettleIII desconocidos. Listado no acredita contrato/convocatoria.34lesiones en contexto de seis eventos, cero disponibilidad final/rol; cruce oficial BOS-CLE0012600011/401898392 a23UTC. Ruta candidata reporte404 y redirección de roster detenida no prueban ausencia global.

Protocolo fullgame previo a métricas:159075etiquetas/6150partidos/310OT;104645antecedentes causales;84015casos evaluados/4343partidos/3842observaciones OT. Gamma-Poisson con minutos históricos completos, prior heredado fijo y familia sin selección actual. CRPS1,361001 contra1,390279;delta-0,029277/IC95porfecha[-0,032610;-0,026288]. IncluyeOTsinfiltrarobjetivo; cohorteparticipaciónpositiva posterior, temporadas previamente inspeccionadas, sin disponibilidad/DNP ni OTduración/rotación/jointminutes. Resultado exploratorio; RUN052preservado, F7noiniciado.

Caliente10preciosdeequipos/0props/0contratos, dos páginas reglas actuales sin vigencia/ticket histórico acreditado. Revalidación fija fuente de liquidación/horario ademásDNP/push/payout. TresSSHclockechoes:offsetremoto-local[-0,010387;2,711583]s, no sincronización ni prueba en vivo. Transportes requieren límites frescos y usan vencimiento conservador remoto; falta/antigüedad rechaza antesSSH/stdin. Fallo inicial425pass/1WindowsPermissionErrorpreservado; guardado único/fsync/reemplazocon6reintentoslocalesWindows5/32, nunca llamadas externas. ImportError previo y dos lanzadores sinpsycopg previos a acciones preservados.

Suite final435sinomisiones conPostgresNBA nuevo, fuente39eventos/19mensajesintacta,clústerdetenido; arnés768/10antes/después. Revisión separada mismaautoría reconstruyó allCRPS/ICporfechas,104645historias,332distribucionesmuestreadas,245IDs/34lesiones/35recibos.57corridas/20328evidencias/134eventos preservados.

Protocolo cierre144read-only:colector activo19:15UTC/38recibos/mismaimagen/cero reinicios/source_degradedCalienteVPS403;serviciosanteriorespreservados, módulos nuevos no desplegados. Revisión automática rechazó envío SHA256manifiesto aDigiCert sin autorización explícita del payload/destino:ningúnPOST/GETTSA nuevo ejecutado, alternativa local completa. Manifiesto d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e preparado, sello nuevo pendiente; pruebas anteriores RUN057 conservan propioalcance.

Protocolos135–144; checkpoint145.0APIdatosdeportivospagadas/0mensajes/0apuestas/0nuevascopiasperiódicas. Cota2232/3200sin cambios. G0–G9/alcance/decisiones/produccióncomercial preservados, F6abierta/F7draft_not_started. docs/nba_f6_partido_completo_y_contexto_oficial_20261008.md.


## 2026-10-08 — NBA: sello autorizado del manifiesto RUN058 (NBA-RUN-059)

El usuario respondió «si autorizo» al envío exclusivo SHA256/nonce aDigiCert. Protocolo146 fijó exactamente d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e. Una descarga de cadena y un POSTTSA gratuitos, sin documentos/credenciales ni reintentos. Granted firmado2026-10-08T19:24:17Z; firma/cadena/hash/nonce verificados dos veces, contenido alterado/nonce distinto rechazados. Sin nuevaOCSP/CRL. Prueba existencia nueva del manifiesto y sus hashes; no recepción original histórica, predicción previa a partidos retrospectivos, exactitud ni checkpoint posterior.

58corridas/20535evidencias/145eventos preservados; artefactos RUN058 se mantienen intactos, incluido rechazo histórico. Asociación externa posterior registrada separadamente. Revisión separada mismaautoría, arnés768/10antes/después; módulos NBA intactos y suite435anterior no repetida.0APIsdeportivaspagadas/0mensajes/0apuestas/0nuevascopiasperiódicas/0cambiosVPS. Protocolo146/checkpoint147, F6abierta/F7noiniciado. docs/nba_sello_externo_autorizado_20261008.md.

## 2026-10-08 — Reto escalera

Pedido del usuario con una regla de partida (cuota 1,25-1,40, 5-7 pasos,
freeroll a ×2,5). Antes de construir se midió (`eval/escalera_prueba.py`,
firma d5cbc3151164): la probabilidad en ese rango está calibrada (72,1 %
prometido, 72,6 % real) pero cada escalón pierde −3,6 % de EV a la mejor de
bet365/1xBet, y la escalera lo multiplica: 6 pasos se completan el 15,6 % y
dejan −24,1 % por reto (−19,7 % con freeroll). Decisión: solo escalones con
cuota ≥ precio justo de Pinnacle sin margen, en las casas de la lista; sin
candidato no se apuesta. En vivo (24-sep → 8-oct) eso deja 4 de 20
candidatos: un reto puede tardar semanas. La muestra con filtro (73
escalones, 16 retos históricos) no demuestra beneficio y la web lo dice.
Diseño: tablas inmutables y estado DERIVADO (`escalera.estado`) en vez de
columnas que se actualizan; aplazado → nulo a las 48 h; bloque `escalera`
en el lote sellado con `LOTE_ESCALERA_DESDE` (None hasta desplegar), mismo
patrón que alta probabilidad. Doble oportunidad fuera: no hay cuota que
tomar en las fuentes. Primer escalón según la vista previa en producción
(8-oct, sin escribir): Dortmund gana a Werder Bremen @1,36 (1xBet), prob.
74,1 %, EV +0,8 %.

## 2026-10-08 — Escalera: retos de 3 a 6 a la vez y hándicap asiático

Decisión del usuario: varios retos a la vez, 3 escalones por defecto, de 6 como
mucho 3 al mes, 4 y 5 cuando ya hay otro abierto. Medido antes
(`escalera_prueba`, 3-6 pasos): acortar sube los completados (39,9 % a 3
pasos frente a 15,3 % a 6) y reduce la pérdida de la regla sin filtro (−11,5 %
frente a −26,2 % por reto), pero ninguna longitud gana sin el filtro de valor:
el valor esperado de un reto es el producto del de sus escalones. Reparto:
primero los retos abiertos (el más avanzado antes), después retos nuevos; un
partido nunca se repite entre retos ni coincide con un escalón sin liquidar.
Hándicap: Pinnacle solo da su línea principal en nuestras fuentes, así que la
probabilidad sale del ajuste de goles; se validó la calibración sin cuotas
históricas de esas líneas (firma d5cbc3151164): pasan −1 a +2 salvo −1,5. Solo
enteras y medias (las de cuarto liquidan medias y la escalera no las trata);
'push' no cuenta ni mueve el saldo. En vivo las protectoras llevan mucho margen
(Santos +1,5 a 1,36: −8 %). La prueba tarda ~40 min: el ajuste por partido.

## 2026-10-08 — Despliegue del reto escalera (commit 37aa902)

Autorizado por el usuario a las 21:06 UTC. `LOTE_ESCALERA_DESDE = 2026-10-09`
(el lote del 08 ya estaba sellado). Base del servidor cotejada contra f94a5bc
y el árbol `src` del worker contra el servidor (solo difería lo de cuentas y
panel, desplegado antes solo en la API). Paquete por SHA-256, respaldo en
`~/release-37aa902/backup.tgz`, imágenes previas `quantfut-api:before-37aa902`
y `quantfut-worker:before-37aa902`; `db/045` aplicado; `ESCALERA_ENABLED=1`.
Primera vez que se recrea el WORKER en esta fase: es quien corre el job
diario. Trampa: el contenedor no tiene `ps` ni `pgrep`, así que la comprobación
de "ningún job en marcha" no midió nada; se recreó a las 21:08:27 (minuto
tranquilo, sin jobs de :08) y a las 21:10 cron ya ejecutaba odds y ráfagas. Para
la próxima, listar `/proc/*/cmdline`. Verificado: cadena (10 lotes OK),
vista previa en el worker (reto nuevo de 3, escalón Dortmund @1,36 1xBet,
EV +0,8 %), `/escalera` 200 también desde el dominio y `app.js` público igual
al del commit.

## 2026-10-08 — Escalera por probabilidad: córners, tarjetas, goles, ambos anotan (sin desplegar)

Decisión del usuario: la escalera elige el MÁS PROBABLE en 1,25-1,40, sin filtro
de valor (`EV_MIN = None`, `db/046` permite NULL). Córners y tarjetas
(amarillas + rojas) con `model/estadisticas_mercado.py` (equipos, liga,
árbitro; sin cuotas). Prueba `eval/escalera_estadistica.py`: con encogimiento
6 prometía de más en los extremos; φ en 2019-21, encogimiento elegido en
2021/22, criterio en 2022-25. Córners pasan (más de 7,5/8,5/9,5; menos de
9,5/10,5/11,5); tarjetas no (−1 a −3 pts; solo menos de 6,5). Ambos anotan:
prueba en curso al cortar la sesión; `BTTS_HABILITADO = False` hasta verla.
Cuotas de bets 8/45/80 de la respuesta de API-Football ya pedida; árbitro y
tarjetas de football-data (`history_fd tarjetas`) y de results/fixtures.
Pendiente: resultado de ambos anotan, harness completo, desplegar (db/046,
`history_fd tarjetas` en el VPS, api + worker).


## 2026-10-08 — NBA: piloto de precios y contexto (NBA-RUN-060)

El usuario autorizó ejecutar el piloto de diez partidos tras conocer costos y falta de presupuesto adicional. Techo conservador incremental250 comunicado antes de consultas; cuenta existente, ninguna contratación. Once consultas históricas cobradas210 y tres actuales9, total219;28rutas totales incluidas gratuitas y un422sin cargo. Saldo18.419al último recibo21:43UTC, sin saldo futuro garantizado. Los500anteriores se conservan como histórico, sin retroeditar. Cliente NBA aislado con reserva persistida, cuota/corte/URLs/credenciales y cero reintentos automáticos.

Diez históricos con puntos/rebotes/asistencias al corte60min previo al horario más temprano,2617pares identificados:1957nuevos+660previos.43rebotes excluidos por snapshot tardío, Dallas recuperado al corte correcto por10créditos.13pares anteriores con Jimmy Butler/III quedan separados por política de nombre completo exacto; fuentes/IDs anteriores intactos.41mercados nuevos con relojes incompatibles y91pares históricos sin identidad quedan sin promover.62observaciones oficiales previas al corte,10PDFs enlazados, recepción2026nooriginal2025.

Diez actuales (6pretemporada/4regular):21pares en3regular,15frescos al recibo, sin identidades/contratos/estadofinal acreditados.6eventos/96lesionesESPN,5RotoWire/6tarjetasquintetos. CalienteHTTP403pero navegador público legible; dos eventos solo cuotas de equipos. Observaciones DOM son transcripción, no bytes HTTP ni recibo exacto; sin sesión/boletos.

Fallos locales y422preservados; correcciones de fechaZ/reloj opcional de casa actual se prueban, reproceso offline sin pagar nuevamente. Verificación separada mismaautoría reconstruye2069pares nuevos y archivo2617, hash/cadena/identidades/consumo/ausencia de claves.69pruebas pertinentes,786/15arnés inicial y798/16final en árbol compartido con fútbol concurrente. Modelos/gates/F7/VPS/mensajes/apuestas/copiasperiódicas sin cambio por este piloto. docs/nba_piloto_props_y_contexto_20261008.md.


## 2026-10-08 — NBA: casas mexicanas y admisión por evento (NBA-RUN-061)

Ante la petición de solucionar fuentes y revisar1xBet/Novibet, se verificó navegación pública sin cuentas/apuestas. Novibet muestra mercados de equipo enBOS-CLE; reglas de jugador explícitas (entrada en cancha mantiene apuesta, DNPanula, OTsalvo excepción, push), pero captura directa403y sin pares PTS/REB/AST verificados.1xBet tiene PDFmexicano recibido200y regla estadísticaOT; sus conteos de mercados no prueban cuotas individuales, selecciones ilegibles en dos eventos. No se adopta como fuente operativa por anuncio comercial. Betsson también solo mercados de equipos en la vista revisada.

NBApágina oficial recibida22:04:25UTC contiene42listados para0012600011; pertenencia al listado no prueba convocatoria efectiva ni salud. Un nombre corrupto marcado; inactivos vacíos no prueban disponibilidad. Comando offline rechaza hash/partido/equipos/IDs/cortes incompatibles y conserva salidas. Al documentar la revisión el partido ya comenzó: ninguna observación nueva se retrofecha.61pruebas, arnés798/16,19GETgratis/0créditos nuevos.60corridas/20675evidencias anteriores intactas y prefijo155eventos conservado; reparación transparente del logpostsealRUN060preservada. Sin cambioVPS/mensajes/modelos/gates/F7 ni copias periódicas. docs/nba_fuentes_1xbet_novibet_y_disponibilidad_20261008.md.

## 2026-10-08 — Despliegue de la escalera por probabilidad (commit abe3da4)

Pedido del usuario ("termina lo pendiente"). Desplegado a las 23:10-23:22 UTC,
ANTES del primer job con escalera (09-oct 08:00), así que el primer reto nace
con la regla nueva. Base cotejada contra 37aa902, paquete por SHA-256, respaldo
en `~/release-abe3da4/backup.tgz`, imágenes previas `*:before-abe3da4`;
`db/046` aplicado; api y worker recreados. `history_fd tarjetas` cargó
amarillas/rojas de 27.398 partidos de las 7 ligas principales y árbitro de
4.610 de la Premier. Cadena: 10 lotes OK. Vista previa: abriría 4 retos (3, 6,
4 y 5) con PSV @1,26, Unión-Defensa menos de 3,5 @1,27, Galatasaray @1,30 y
Dortmund @1,36. Córners/tarjetas/ambos marcan entran cuando af_odds capture
sus cuotas (desde las 00:20 UTC). Trampa repetida: la comprobación de jobs en
marcha vía /proc se contaba a sí misma (su línea contiene "python -m qf");
el worker se recreó a las 23:21:40 tras agotar la espera. Para la próxima,
excluir el propio proceso (`grep -v` del PID o patrón con corchetes).


## 2026-10-08 — NBA: selección europea explícita (NBA-RUN-062)

El usuario solicitó incluir1xBetEuropa,BetssonEuropa,CodereItalia yBetanoReinoUnido. Se usan claves oficiales onexbet,betsson,codere_it,betano_uk y filtro de casas explícitas, en lugar de ampliar a todos los proveedores de cada región. Europa no identifica el país contractual de1xBet/Betsson; no se acredita equivalencia mexicana ni cobertura de props por presencia en catálogo.

Selección distribuida con paquete, planCLIoffline y método del cliente acotado mantienen presupuestos/recibos y no activan consultas periódicas. Descubrimiento actual reserva1crédito; tres mercados reservan3actuales o30históricos. Solo transporte simulado y consolaoffline:33pruebas, arnés798/16,0consultasTheOddsAPI/0créditos.61corridas/20756evidencias y prefijo160eventos preservados. F6abierta,F7sin iniciar; captura real y contratos aún pendientes. Sin cambioVPS/mensajes/apuestas ni nuevas copias periódicas. docs/nba_casas_europeas_seleccionadas_20261008.md.


## 2026-10-08 — NBA: cuotas europeas comprobadas (NBA-RUN-063)

El usuario autorizó la consulta real con «hazlo». Se fijó protocolo antes de solicitudes pagadas: cuatro versiones explícitas, ocho eventos, máximo56créditos, cuenta existente/reserva compartida y sin reintentos. Se recibieron27respuestas200,16con cargo,29créditos; cero fallos/reservas pendientes.

1xBet EU aportó 24 precios en 4 eventos; Betsson EU, 36 en 8; Betano UK, 12 en 3; Codere IT, ninguno. Total 72 selecciones de equipos, no pares de props. Ocho consultas directas PTS/REB/AST y descubrimiento sin esos mercados. Ausencia específica del recibo: cuatro eventos de pretemporada tenían horario ya pasado y cuatro regulares estaban lejos del inicio; no se prueba ausencia universal. Se verificaron recibos y 33 pruebas pertinentes. Arnés 798/16. 62 corridas/20.777 evidencias y prefijo de 161 eventos preservados. F6 abierta/F7 sin iniciar; contratos, recepción histórica y disponibilidad aún pendientes. Sin VPS, mensajes, apuestas ni copias periódicas. docs/nba_cuotas_europeas_comprobadas_20261008.md.


## 2026-10-08 — NBA: suministro reutilizable de props resuelto (NBA-RUN-064)

El usuario pidió solucionar el atasco de props. La causa era tratar la captura de datos y la admisión comercial como el mismo requisito, además de conservar precios US en muestras aisladas. Se implementó capture-props con perfil US/AU propio, presupuesto explícito, diez casas y selección exclusivamente futura, conservando la selección europea. La fuente de precios tiene estado funcional separado de production_ready/actionable, sin relajar validadores.

Captura real: 19 respuestas API, 17/32 créditos, 36 pares (12 PTS/12 REB/12 AST) de FanDuel15, Sportsbet15 y Fanatics6 para cinco jugadores/tres eventos. 33 frescos al recibo, sin garantía de frescura futura. Identidades oficiales completas: 23 pruebas previas y 13 enriquecidas posteriormente, sin retrofechar el corte. 2617 pares históricos reutilizados con recepción original desconocida. Ocho GET públicos: dos perfiles y seis páginas de reglas; FanDuel directo403 conservado, las otras200. Sportsbet tiene guía explícita de participación/prórroga/resultados; Fanatics conserva excepción por lesión, contratos de cuentas no acreditados.

40 pruebas pertinentes; arnés 798/16. Reproducción offline de precios, recibos, créditos e identidades. 63 corridas/20.831 evidencias y prefijo164 eventos preservados. El pendiente de suministro queda resuelto; F6 global abierta por contrato, disponibilidad cerca del inicio y validación prospectiva; F7 sin iniciar. Sin apuestas, publicación, cambios VPS ni nuevas copias periódicas. docs/nba_props_fuente_funcional_20261008.md.

## 2026-10-09 — Escalera: probabilidad prudente en córners y tarjetas (commit ed7ac99)

Con las primeras cuotas reales de córners/tarjetas (00:20 UTC), la vista
previa abría los 4 retos con «menos de 6,5 tarjetas» y «más de 7,5 córners»:
modelo 81-82 % frente a 69-72 % de la propia Betano sin margen. No es que la
casa regale 11 puntos: al elegir el MÁXIMO entre ~580 candidatos gana quien
más se equivoca hacia arriba, y la prueba histórica no lo podía ver porque
football-data no trae cuotas de esos mercados. El usuario eligió la
probabilidad prudente: `min(modelo, mercado sin margen)` (Pinnacle si cotiza
los dos lados; si no, media de las casas de la lista); sin los dos lados el
candidato no entra. Desplegado a las 02:07 UTC del 9-oct, antes del primer
job con escalera (08:00): respaldo `~/release-ed7ac99/backup.tgz`, imágenes
`*:before-ed7ac99`. Vista previa nueva: 4 retos sin córners ni tarjetas
(Moreirense menos de 3,5 @1,25, Red Star marca @1,25, PSV @1,27, Dunkerque-
Annecy más de 1,5 @1,27). El chequeo de jobs en marcha usa ya `[p]ython -m qf`.


## 2026-10-08 — NBA: seguimiento prospectivo en simulación (NBA-RUN-065)

El usuario autorizó conectar props al modelo y el seguimiento prospectivo, aceptando referencias US/AU. Protocolo exploratorio congelado antes de capturar: PTS/REB/AST, regular/fullgame/OT incluido,20apariciones/min10, prior temporada anterior, baselinePoisson, precios<=60s al sello, una unidad hipotética. No se promueven candidatos de puntos/asistencias ni la extensión de apertura de rebotes; probabilidades condicionadas a participación y disponibilidad final desconocida.

Lote inicial12créditos/3eventos/36pares; adaptación detectó namespace omitido en parte del archivo corregido. Reparación por cruce exacto con etiquetas NBA verificadas, registrada antes de pronósticos; fallo original conservado. Quince predicciones selladas después, con cuotas vencidas y cero entradas. Tras66pruebas se anunció/fijó máximo adicional4créditos para un partido: paper-run prevalidó antes de cobrar y selló seis versiones/15pares recientes; precios53,75–53,98s. Dos entradas hipotéticas AST/PTS Cade; tres Tatum excluidas por candidato nominal de feedESPN (no estado de evento verificado), un mercado bajoEV. Cohorte congelada15casosúnicos,21versiones conservadas; total51pares/12consultas/16créditos.

Se implementaron recepción de final NBA, evaluación y resumen con sellos, identidad/equipos/hora/finalización, DNP separados y rechazo de duplicados. CDN403; webNBA200 comprobada HOU–OKC0022500001/final2OT con20participantes y sumasPTS/REB/AST reconciliadas. SeisGETpúblicos: ESPN200, CDNcalendario403, NBAcalendario200sin eventos y dos páginas futuras403. Los IDsNBA de eventos aún necesitan enlace oficial; futuros resultados y disponibilidad no acreditados. Ningún resultado pasado sustituyó un futuro.

Reproducción causal exacta21pronósticos y51pares;159075filas históricas cruzadas. SuiteNBA499/17 y arnésgeneral800/16. Se preservan64corridas,20900evidencias y prefijo167eventos. F6 sigue abierta; preparaciónF7/piloto exploratorio activo, confirmacióncientífica/G7sin iniciar, D07/D08pendientes. Sin mensajes/apuestas/publicación/VPS/suscripciones/recolector nuevo ni nuevas copias periódicas. docs/nba_seguimiento_prospectivo_20261008.md.


## 2026-10-08 — NBA: enlace oficial y seguimiento acotado (NBA-RUN-066)

El usuario pidió resolver todos los pendientes. Se conservaron RUN065,21versiones/15unidades y2entradas hipotéticas. Tres páginas NBA HTTP200 cruzadas con proveedor por equipos y hora exactos:0022600001,0022600002,0022600003; inicio20oct13:00/17:00/19:30CiudadMéxico. Conocimiento de IDs posterior al sello explícito. Plantillas actuales vacías, no disponibilidad. Cero créditos nuevos y3GETpúblicos.

Nuevo trabajador acotado paper-followup-plan/paper-advance: sello de inputs, reclamación previa inmutable, máximo3tareasred por ejecución, sin reintentos, estado vivo fuera de evidencia de hashfijo. Observación previaT-2min; cierre Sportsbet mismoevento/jugador/mercado/línea, últimos5min/frescura60s/max2créditos futuros; finalesoficialesT+4/+6/+12/+24h con ventanas2h. Score/summary sólo registrosoriginales/finalesverificados, DNP separados. Prueba actual sobrecohortereal cero tareasdebidas/cero consultas. Automatización local cierre-del-piloto-nba-octubre-20-y-21 ACTIVE para20–21oct en estechat; necesitaequipoencendido/Codexabierto, avisos sólocambios/fallos/acción. Fin22oct12UTC; ninguna ventana nirespuesta garantizada.

Lectura/CLV investigación prefijados y borradorpotencia usando sólo20853unidades/145días/1087partidos de entrenamiento2022-23: CRPSprimarioREB/efectomínimo.05/alfa.025/potencia.8/mínimo112días y300partidos. Proxydeplanificación, no confirmación. Candidato/exposiciónexactos, revisiónexterna, calendariofinal y cobertura aún pendientes antesdeabrir otrobloque. D08investigación definido; reglasporcuenta/jurisdicción pendientes. Recepciónhistóricaoriginal imposibledeacreditarcon descarganueva.

24pruebas de ciclo cubren cruce/hash/hora, roster≠salud, CLVcontrato/frescura, fallo403, duplicados, límites/claims y cierre2mercadosrealmock. Prueba integral detectó dictmarketduplicado; corregido antesdevalidaciónfinal. Planificaciónhistoricalectura necesitó adaptar metrics anidados; fallo preservado. Primer arnéspost falló porWinError5caché pese800pruebas; repetición con cachénueva conserva las mismas comprobaciones y pasa. SuiteNBA523/17; arnés800/16. Se preservan65corridas/21016evidencias/prefijo173eventos. F6/F7/G7sinpromoción, futuroseventos/resultadosnoinventados;0apuestas/copiasperiódicas/publicación/VPS/mensajesexternos. docs/nba_pendientes_resueltos_y_cierre_programado_20261008.md.


## 2026-10-08 — NBA: seguimiento autónomo en VPS (NBA-RUN-067)

El usuario pidió resolver pendientes. Se cerró dependenciaPC/Codex de captura mediante servicioNBA aislado enVPS, mismo plan/15casos/sellos RUN065/066. Primer despliegue rechazó FROMconID; segundo detectó rutasWindows enJSON. Ambos0cuotas/0probes deportivos; informesconservados. Readerinterpreta separadores sin cambiarbytes sellados; tercera versiónverificó fuente/modelo y arrancó. TrespáginasNBA200 desdeVPS, exactosIDs/equipos/hora;3recibospúblicos nuevos,0créditosactuales,2máximocierre futuro.

Servicio nba-paper-pilot-run67, root /home/qf/nba-isolated/paper-pilot/run67-v3-20261008. Fuente/carpetasRO, redpropia/sinpuertos/0.5CPU/512MiB/64pids, sincapacidades/no-new-privileges, restartunless-stopped. ODDS_API_KEY existenteVPS comparada con cuentalocal, leída sinexportación; dos clavesdeintentosfallidos retiradas tras comprobarningúnmontaje; activa600conservada. NTPsincronizado. Primer cicloespera/cerojobs, segundoejecutorbloqueado antesdered, reinicio conservaexactostate;7serviciospreviosIDsiguales.

Estado/claims persisten; ventanas/fin/lectura max3tareas porinvocación y cap2originales. Automatización delchat ahoraobservaVPS, noejecuta capturas; tombstone state.owner.json y guardCLI rechazanexecutorlocalretirado. Avisos delobservador siguen locales, captura no. Terminal bloqueanuevasconsultas; observador detiene exclusivamentecontenedorNBA validandoetiqueta, sinborrar. No se garantizan fuentes futuras/p95.

Criterios/diseñocientífico exactos congelados para revisión:REB fullgmOT,GammaPoisson/Poisson10,hist20/min10; ventana propuestaNov1-Mar31/lecturaApr2/3bloques,112días/300partidos,deltaCRPS.05/alfa.025/potencia.8,bootstrapdías5000/seed20261009/calibmasa realdiscreta5pp. No activado porfaltarrevisión,F6scopedy presupuesto; nosepromueveG7. Ficha vacía decontratocuenta separada delpaper. Recepciónhistóricaoriginalnoaportada, no reconstruiblehoy.

SuiteNBA531/17 y arnés800/16; paquete/worker7controles nuevos másguardCLI, flujosciclo24 conservados.66corridas/21056evidencias/prefijo176eventos preservados. Esperadatos20oct y confirmación nueva no se etiqueta como fallo técnico. Sinapuestas/publicación/mensajesexternos/nuevascopiasperiódicas ni cambiosfútbol. docs/nba_seguimiento_vps_y_pendientes_por_alcance_20261008.md.


## 2026-10-09 — NBA: activación operativa y alertas autónomas (NBA-RUN-068)

El usuario pidió solucionar y activar todo. La salud degradada tenía origen enCaliente403 opcional; ESPNrespondía200. Se separó salud de fuentes necesarias de cobertura de casa, manteniendo403/cuerpo/hash y deteniendo consultas repetitivas. La misma carpeta RUN057 y todo su prefijo344eventos se conservaron; nuevo recolector conflock, imagenverificada yreinicio retieneestado. Nuevas copias periódicas desactivadas y archivosanteriores sin cambios.

Nuevo supervisor host aislado usaúnicamente token/destino operativo yaautorizados, extraídos enVPS yprivados600. ReclamaantesPOST, diariocontriggers/hash, cap20intentos porUTCdía, sinretryincierto niavisosrepetidos porreinicio. UnTelegramconfirmado condestinoverificado; no acredita lecturadesuscriptores. Detención terminal exclusiva decontenedorpiloto con etiquetaexacta; noDocker general niapuestas.

Primer despliegue detectócarrera Type=simple alcomprobar bloqueoantesinicialización; rollback automático conservado. RecuperaciónType=notify anunciaREADYdespuéslock/ciclodurable; segundoejecutor rechazado, reinicio conservaúnica reclamación/mensaje. ArranqueVPS habilitado, independientedelPC/Codex. Piloto/sellos15casos/cap2intactos ycontenedoresfútbolsin cambios.

DosGETpúblicos actuales, ceroAPIcuotas; futurocierremax2. Diseñocientífico yficha decuenta copiados una vez; F7confirmatoria/G7no promovidos. Falta revisar/validaruniversoprospectivo yrecibirpartidos futuros; cero tickets reales, disponibilidad yrecepciónhistóricaoriginal no inventadas. Fallossintaxislocal/directoriotemporal/fixture preservados ycorregidos; suiteNBA542/1 yarnés800/16. docs/nba_activacion_y_alertas_vps_20261009.md.


## 2026-10-09 — NBA: página pública de pronósticos y resultados (NBA-RUN-069)

Se publicó https://pronosticosdeportivos.pro/nba con la cohorte sellada de 15 registros, cinco jugadores y tres partidos. La página filtra jugador/equipo, mercado, partido y estado. Presenta estimación, rango, probabilidades condicionales a participación y cuotas históricas con recepción/sello; cero resultados evaluados hoy, partidos registrados el 20 de octubre. No son apuestas ni cotizaciones actuales.

Servicio aislado con recursos limitados y fuentes originales montadas solo para lectura. Verifica diario, plan, sellos y recepción; reconstruye conteos desde el boxscore oficial antes de publicar un resultado. DNP explícito separado de cero, ausencia exige revisión. No ejecuta modelos ni captura desde solicitudes web, no monta credenciales ni datos de fútbol. La configuración del proxy y su segunda red quedan persistentes. Fútbol y protección de administración comprobados por HTTPS.

Se conservaron tres intentos fallidos con reversión automática: archivo anterior retenido por el montaje del proxy y comprobaciones de disponibilidad demasiado tempranas. Cuarto intento espera HTTP real antes y después de reiniciar; pasó conservando diario del piloto y contenedores originales. La comparación pública contempla solo la etiqueta de analítica inyectada por el CDN existente y exige igualdad de los bytes propios.

La página pública se abrió en navegador y los filtros/detalles de cuotas se comprobaron sin errores de consola. Captura guardada. El navegador ignoró los tamaños solicitados y mantuvo 700×572; revisión visual móvil pendiente explícita, no declarada como probada. Pruebas NBA 558/2, arnés antes y después 800/16. Se preservaron las 68 ejecuciones y todas sus evidencias, sin promover puertas científicas, apuestas ni copias periódicas. docs/nba_pagina_pronosticos_resultados_20261009.md.


## 2026-10-09 — Menú Fútbol/NBA e histórico (NBA-RUN-070)

El usuario preguntó por el histórico y pidió acceso NBA desde la cabecera de fútbol. El archivo aceptado conserva su huella NBA-EV-2204:164.218 filas y6.313 IDs, fechas2021-10-19..2026-06-13. Son datos retrospectivos; no un historial de aciertos emitidos antes del partido. El piloto conserva15pronósticos y0resultados recibidos.

Selector superior Fútbol/NBA con enlaces accesibles, activo marcado y reglas móviles fuera del menú que se oculta. Nuevas huellas JS/CSS enHTML. Publicación deriva de la imagen exacta de fútbol ya ejecutada y añade solamente tres recursos públicos. Se recreó únicamente laAPI; las otras identidades, trabajador/base/proxy/NBA y códigos de backend se conservaron. Configuración de imagen y fuentes persistida enVPS.

Primera comprobación recibió conexión cortada al arrancar y revirtió automáticamente. Recuperación conservada tolera esa lectura transitoria de salud propia y exige200antes de comprobarHTTPS; pasó. Navegación real Fútbol→NBA→Fútbol,15filasNBA y captura de pantalla; consola sinerrores a1280×720. La solicitud390×844 volvió a ignorarse, también en pestaña nueva: revisión visual móvil pendiente explícita.24pruebasfrontend y800/16arnés; registrosprevios/gates intactos, sinapuestas/copiasperiódicas nuevas. docs/nba_menu_e_historico_20261009.md.


## 2026-10-09 — Nueve mercados NBA desde estadísticas (NBA-RUN-071)

El usuario pidió desarrollar todos los mercados discutidos, priorizando probabilidad/estadística sobre cuotas. Se recuperaron triples/robos/tapones de los originales ya recibidos, con uniones exactas y reconciliación de equipos:157.962filas/6.108partidos regulares;42discrepantes excluidos sin alterar el histórico anterior. Se desarrollaron seis modelos de conteo y Elo/medias ataque-defensa/covarianza para ganador/equipos/total, con características anteriores a cada fecha.

Entrenamiento2021–22, calibración2022–23, evaluación exploratoria2023–26. Candidato y referencia calibrados igual; cálculo preliminar sin esa equidad conservado y protocolo corregido antes de inspeccionar métricas. Ganador≥70% acierta80.4%/1.071casos frente69.5%referencia; equipos74.3%/1.721 frente53.3%. Los conteos raros pueden dar mucho acierto por baja frecuencia; tapones80.3% coincide con referencia. Puntos/rebotes≥70% logran65.1%/65.6%, por debajo de sus probabilidades medias: no se anuncian selecciones fiables70%. Todos los modelos continúan experimentales y no accionables; no se alteró el candidato confirmatorio de rebotes RUN067.

42unidades nuevas selladas para los mismos tres eventos y cinco jugadores;15originales intactas. Web con nueve filtros y tabla conprobabilidadmedia/acierto/cobertura/referencia/intervalos. La extensión reutiliza recibos oficiales verificados del piloto sólo para lectura: conteos reconciliados, ausencia en revisión y DNP separado. Prueba integral verifica conteo adicional real y rechaza cuerpo modificado, sin escribir diario. No agrega consultas deportivas ni créditos.

Imagennba-dashboard-run71 reemplaza sólo el servicio NBA manteniendo su nombre interno; anterior detenido recuperable. Fútbol/proxy/captura/piloto/alertas conservan identidad, configuración y estado; reinicio/HTTPS y diezaccionesfiltroverificadas. 1280×720, consola sinerrores; revisiónmóvil390px sigue pendiente porlimitación previa.577/18NBA más3pruebasintegrales y800/16arnés. Nuevascopiasperiódicas/apuestas desactivadas, puertas científicas y cuatrobloquesde decisiones conservados; resultados y disponibilidad de20oct siguen futuros. docs/nba_nueve_mercados_estadistica_20261009.md.

## 2026-10-09 — Alta probabilidad: más de 2,5, hándicap asiático y córners (commit 27e8a7f)

Pedido del usuario (ambos marcan, córners, más/menos 2,5 y hándicap). Regla de
la línea: solo entra lo que pasa la prueba histórica, así que se midió todo
(firma d5cbc3151164) y se habilitó lo que pasa. Ambos marcan NO se publica no
por fallar sino porque nunca llega al 80 % en las 7 ligas: no hay nada que
validar. Córners rompe el "siempre Pinnacle": se acepta solo recortado a la
probabilidad sin margen de la casa (misma regla que la escalera desde hoy) y
sin los dos lados cotizados no entra. Con todo habilitado la regla da
pronóstico en el 85 % de los partidos (antes 63 %) y sigue cumpliendo
(82,35 → 82,89); dentro de lo elegido, 1X2 y menos de 3,5 quedan ~2 puntos
por debajo: no es criterio, lo vigila el control por grupo. Ojo: el hándicap
casi nunca trae cuota de referencia (solo The Odds API lo cotiza) y los
córners elegidos se pagan a 1,10-1,16. Desplegado 23:32 UTC; la API usa la
imagen fijada en compose (`quantfut-api-menu70:20261009`), así que se
retagueó ese nombre; respaldo `~/release-27e8a7f/`, imágenes `*:before-27e8a7f`.
Vista previa: 61 decisiones, 29 de hándicap y 8 de córners.

## 2026-10-09 — API-NBA: comprobar permisos antes de activar la fuente

La clave facilitada coincide con la privada ya configurada; autenticación y Free activo comprobados. Se corrigió la afirmación basada en la guía pública: 100 consultas pueden alcanzar por volumen, pero la cuenta rechaza temporadas 2025 y 2026. También rechaza fechas históricas explícitas; el calendario de temporada 2024 sin fecha devuelve 1.406 partidos y es acceso expresamente permitido. Cinco solicitudes de datos y dos estados, sin reintentos; cabecera final 99 restantes, estados declararon cero consumo y no se fuerza conciliación de contadores. Cuenta personal retirada de recibos, clave excluida de evidencia/Git. No se activa un bucle improductivo ni una suscripción, no se modifica VPS/fútbol/modelos/sellos. Recibos nuevos separados de originales previos, docs/nba_api_nba_acceso_actual_20261009.md. Arnés previo:808/16.
Cierre del diagnóstico API-NBA: arnés posterior808/16, igual al previo; siete recibos con SHA-256 verificados y evidencia sin credencial/identidad de cuenta. Docker no disponible. Los cambios ajenos en escalera_estadistica.py se conservaron sin intervención.

## 2026-10-10 — Córners de cada equipo y más de 6,5 (commits 3ce62c4 y 583d432)

Pedido del usuario a partir de un texto de "mercados de más del 70 %". De ese
texto casi todo ya estaba publicado; lo nuevo eran más de 6,5 córners y los
córners del favorito. Se miden con el mismo acumulador y un φ propio por
equipo (1,5455): el modelo por equipo calibra peor que el de totales (varias
líneas fallan en 60-80 %), así que solo entran las líneas que pasan, por
separado en la escalera y en alta probabilidad. "El favorito saca más de 3,5"
pasa en alta probabilidad para el local, no en la escalera. Cuotas: bets 57/58
de la misma respuesta de API-Football (ids comprobados con 1 consulta a
/odds/bets). Desplegado 00:52 UTC (db/048); la primera captura (01:20) trajo
~8.700 filas de 194 partidos. Fallo encontrado en la vista previa: los
córners por equipo salían sin cuota de referencia (`_ref_nuevos` solo miraba
'corners'); corregido y redesplegado 01:27 (583d432). Vista previa: 81
pronósticos de alta probabilidad, 22 de córners; la escalera sigue eligiendo
sobre todo goles.

## 2026-10-11 — Historial de las ligas "solo sharp" para el modelo propio (pasos 1-5)

Pedido del usuario ("activa todas esas ligas en el modelo propio"). El
cargador de football-data buscaba cada nombre SOLO en la liga que cargaba:
el historial de Segunda habría creado un segundo Racing, Leeds, Troyes… y
partido su historia sin error. Ahora clasifica en todo el país (alias del
país o exacto de cualquier fuente; un parecido NUNCA se crea ni se acepta
solo) y hay un ensayo en seco previo. El ensayo cazó dos cosas que la carga
habría grabado: `new/CHL.csv` redirige con 200 a la Superliga CHINA (Chile
se queda sin football-data; el cargador comprueba ahora Country/Div), y un
duplicado que ya existía (el calendario creó "Arminia Bielefeld" sin ver al
"Bielefeld" de la Bundesliga; fusionado en db/050). Los 86 dudosos se
revisaron a mano (db/050) y los clubes nuevos se crearon ANTES de cargar
(db/051): cada club que crea el cargador se vuelve candidato para los
siguientes nombres, y la carga dejaba de ser lo que el ensayo había medido.
Resultado: 39.842 partidos, 0 equipos creados por la carga, 0 duplicados.

`model_enabled` decidía también qué se paga a los proveedores; encenderlo
habría triplicado el gasto de The Odds API en 10 ligas y activado
alineaciones/bajas/jugadores con API-Football ya en ~5.400 de 7.500/día.
`captura_completa` (db/052) lo separa. Y el modelo no se puede entrenar con
el interruptor encendido: con el modelo viejo activo, el job de las 08:00
sellaría predicciones de equipos que no conoce. De ahí `train --incluir`.
Desplegado sin cambio de comportamiento (imágenes `*:before-ligas`).
Pendiente: evaluación en sombra y decisión del usuario antes de activar.

## 2026-10-10 — Tarjetas con árbitro: no; y las pruebas de córners/tarjetas iban sin 2024/25

Pedido del usuario (mercado de tarjetas "con historial y árbitros"). Prueba
`eval/tarjetas_arbitro.py` en E0+E1 (árbitro en el 100 %), criterio fijado
antes de mirar. El árbitro mejora la pérdida logarítmica 0,0011 por partido
(z=1,07; Premier −1,48, Championship +2,47) y empuja la media 0,18 tarjetas
por encima de la real: cumple la letra del criterio (A) pero no es una
mejora real, así que no hay regla propia para Inglaterra. Y en Inglaterra el
modelo calibra igual de bien SIN árbitro.

Lo importante salió de rebote: 9 CSV de football-data (toda 2024/25 y la
Premier 2021/22) traen BOM; leídos en latin-1 la columna `Div` era
`ï»¿Div` y `groupby("Div")` de `escalera_estadistica` los tiraba sin error.
Las pruebas del 8 y 9-oct midieron 10.842 partidos, no 13.555, y la Premier
eligió parámetros sin su temporada de ajuste. Las demás pruebas agrupan por
`league_id` y no se vieron afectadas; el cargador de producción
(`history_fd`) ya decodificaba con utf-8-sig. Con los datos completos y los
mismos parámetros (`--fijos`) caen tres líneas de córners de la escalera, las
tres en el tramo 70-80 %, que es justo donde elige la escalera, y una de alta
probabilidad; entran tarjetas menos de 4,5 y 5,5. La regla es la de siempre
(solo lo que pasa), no se reajustaron parámetros. Tarjetas en alta
probabilidad, todavía no: alta va 11 puntos por debajo de lo prometido.
Resultados en `.local/escalera_estadistica_20261010_fijos.json` y
`.local/tarjetas_arbitro_20261010.json`. Sin desplegar.

## 2026-10-11 — Flutter/Firebase: análisis y pantallas antes de implementar

App ubicada en `apps/mobile`: revisados 62 archivos Dart, configuración
nativa, cuentas/suscripciones/API/panel existentes y documentación oficial de
Firebase. Análisis Flutter sin incidencias y nueve pruebas existentes
aprobadas desde la nueva ubicación; no validan aún Auth/FCM/compras. Plan
documentado en
`apps/mobile/docs/FIREBASE_INTEGRACION_CON_BACKEND_20261011.md` con identidad
Firebase vinculada a cuentas existentes, API como autoridad de permisos,
notificaciones, medición, control y transición de usuarios.

El usuario confirmó implementación por fases y pidió primero presentar sus
ideas de pantallas. Se registra fase 0 de diseño y recomendaciones antes de
concretar fases/entregables. Pendiente de recibir esas ideas; no se inició
integración funcional, configuración Firebase ni cambios de producción.

## 2026-10-11 — Flutter: primeras pantallas QuantFut y navegación VIP

Incorporadas las referencias del usuario en `apps/mobile`: cinco bienvenidas
con ilustraciones animadas originales, arranque QuantFut y barra inferior
Inicio / Predicciones / En vivo / La Grada / Perfil. Tarjetas de ejemplo,
filtros de equipo/liga/día/deporte, fichas VIP difuminadas y botón Hazte VIP
que abre la selección de planes. Los metadatos VIP no contienen el análisis
privado. Precios pendientes; comprar muestra un aviso y no realiza cargos.

Estados de directo, comunidad y perfil preparados como propuestas. Sin
conexión Firebase/API, sin sesión ni pagos activos. No se alteró producción.
Diseño, límites y fases documentados en
`apps/mobile/docs/PANTALLAS_BIENVENIDA_INICIO_VIP_20261011.md`.
Validación: trece pruebas Flutter, texto ampliado en 320 × 568, análisis sin
incidencias y Android debug. Capturas en `apps/mobile/docs/validation/`.

## 2026-10-11 — Flutter: mercados con evidencia e idioma registrado

Sustituidas las propuestas de radar/primer tiempo por Mercados: ocho familias
fútbol, selección de líneas habilitadas con prueba aprobada y al menos 500
casos como regla de presentación, sin modificar las reglas del modelo.
Historial público del VPS guardado aparte: 75/96 (78,1 %), muestra inicial;
las tasas retrospectivas no se presentan como resultados publicados.
Pantallas Hoy/Histórico, avisos pendientes, ruta VIP y NBA exploratoria.
Revisión local del 10-oct distinta de la desplegada: tarjetas 4,5/5,5
pendientes y córners local +2,5 no se destacan; servidor sin cambios.
18 pruebas Flutter aprobadas, análisis sin incidencias, Android debug
compilado e instalado en el emulador. Detalle y fuentes:
`apps/mobile/docs/MERCADOS_MODELO_APP_20261011.md`.

Nueva referencia del usuario: selector de idioma desde el primer arranque,
antes de bienvenida, con es/en/pt/fr/it/de, persistencia y cambio en Perfil.
Registrado junto a Firebase: traducción Flutter, cuenta/backend/web,
Auth/correos, FCM/bandeja y medición; identificadores y datos del modelo no
se traducen. Pendiente de implementar, sin simular traducciones ya listas.
`apps/mobile/docs/IDIOMAS_APP_BACKEND_FIREBASE_20261011.md` y tareas del arnés.

## 2026-10-11 — App con datos reales, Monedas y Referidos

Autorización posterior del usuario: eliminar el modo demo y conectar el modelo
real, con interruptores por sección y leyenda configurable de entrenamiento.
La raíz Flutter consume la API de producción; calendario, enfrentamientos,
pronósticos, detalle, historial, planes y cuenta dejan de usar datos ilustrativos.
Los datos que la fuente todavía no entrega se identifican como ausentes.

Alta Probabilidad: rango de presentación 75–90 %, 10 % gratuito (redondeado
hacia arriba), mayor cuota real entre elegibles y asignación inmutable por lote.
Escalera: un único pendiente gratuito de mayor probabilidad exacta entre todos
los retos activos. VIP oculta selección/mercado/cuota/probabilidad desde el
servidor, incluidas las rutas web públicas; no solo desde la pantalla.

Menú reemplaza La Grada y ofrece Monedas y Referidos. Saldo y movimientos en
PostgreSQL, asistencia de siete días, códigos de invitación y canje de un pick.
Correo verificado, movimientos idempotentes, canjes atómicos y anulaciones
reversibles de premios. Configuración administrativa en
`/control/configuracion-app` y `/control/recompensas`, con CSRF y auditoría.

Investigación de Tapjoy/Unity, RevU, Torox, ayeT, adjoe y BitLabs documentada con
fuentes. Adaptadores iniciales RevU/BitLabs preparados; el usuario confirmó que
todavía no tiene cuentas de editor. Los seis proveedores están desactivados:
no se anuncian ofertas, ingresos ni acreditaciones comerciales inventadas.

Migraciones 054/055 instaladas. Despliegue limitado de API sobre su imagen previa,
sin recrear los workers. Imagen activa y persistida en compose:
`quantfut-api-mobile-rewards:20261011`; copia de configuración anterior guardada.
Web, health y seis rutas de contenido/monedas respondieron 200. Comprobación
UTC−6 del 11/10: 99 enfrentamientos, dos picks públicos, quince VIP pendientes,
un escalón público y seis proveedores pendientes. Estos conteos son variables.

Validación: 124 pruebas backend aprobadas y cinco PostgreSQL condicionadas
omitidas localmente; ocho comprobaciones adicionales contra PostgreSQL real,
siempre con rollback (saldo, repetición, reversión, referidos, cuotas gratuitas,
canje, vistas y formularios administrativos). Flutter: 18 pruebas aprobadas;
siete pruebas de navegación repetidas tras los últimos ajustes, análisis limpio,
APK debug compilado e instalado. Calendario, tarjetas y Monedas inspeccionados
en el emulador, sin errores Flutter/AndroidRuntime observados.

Estado, fuentes y activación:
`apps/mobile/docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md`.
Evidencia pública y de servidor:
`docs/validation/mobile_rewards_release_20261011/`.
Capturas Android reales:
`apps/mobile/docs/validation/real_mobile_20261011/emulator-*.png`.
Firebase, idiomas, persistencia segura de sesión, pagos/restauración, cuentas
de editor y métricas de detalle aún no expuestas permanecen en tareas pendientes.

## 2026-10-11 — Registro primero: requisito Firebase, sin ejecución

El usuario entregó la captura de acceso oscuro con Google, idioma en la esquina
superior y aceptación de términos/privacidad. Pidió que registro/acceso sea la
primera pantalla de la app y que se anote en el plan Firebase sin implementarlo
todavía. Registrado en el plan principal, el plan de suscripciones, la
especificación de idiomas y el backlog. La elección de idioma pasa a estar
disponible en la pantalla de registro; bienvenida y contenido vienen después
del acceso para personas sin sesión. La sesión existente y los derechos/saldo
del backend deben conservarse. Las cifras de la referencia no se trasladarán
sin respaldo real. Este ajuste modifica documentación únicamente: sin cambios
de código, configuración Firebase, compilación, emulador ni despliegue.

## 2026-10-11 — Coins: recompensas como cuarta pestaña

Corrección del usuario: eliminar el menú intermedio de Monedas/Referidos y
abrir directamente la pantalla de saldo, asistencia, ofertas y referidos.
La cuarta pestaña y su encabezado ahora se llaman Coins, con icono de monedas.
La navegación inferior permanece disponible dentro de esta pantalla y su
actualización consulta el saldo real. No se alteraron las reglas del backend.
Siete pruebas de navegación aprobadas, análisis sin incidencias y APK debug
compilado para actualizar el emulador. Registro inicial Firebase sigue pendiente
sin implementación, conforme a la instrucción anterior del usuario.

## 2026-10-11 — Activación de las 10 ligas: el modelo nuevo no pasa la puerta

Con el visto bueno del usuario se entrenó con `--incluir` (9 h 40 min,
artefacto 2026.10.11-135412). La puerta lo rechazó: no vence a Elo en las
mismas filas (0,20517 frente a 0,20468, n=1.541). El script no encendió
`model_enabled` y nada cambió en producción. La causa no son las ligas
nuevas: el entrenamiento del 1-oct, sin ellas, ya perdía contra Elo
(0,20074 frente a 0,19995); con ellas la distancia se acorta, y la sombra
mostró que las ligas ya medidas mejoran (0,20800 → 0,20752). El activo
(09-27) pasó la puerta por 0,0002: Dixon-Coles y Elo están empatados en la
ventana reciente. No se fuerza una puerta de seguridad sin decisión expresa.

## 2026-10-11 — Parley del día (sin desplegar)

Pedido del usuario: 1-5 parlays diarios de cuota 1,90-5,00, "los más
probables". Con "máxima probabilidad dentro de un rango" todo saldría pegado
a 1,90, así que el usuario eligió escalones (≈2 · 2,5 · 3 · 4 · 5), un partido
por parlay y ninguno repetido en el día, y solo probabilidad (pierde el margen
en cada pata; el historial lo enseña). La revisión final cazó cuatro cosas que
los tests del plan no veían: la poda de patas "dominadas" que prescribía la
propia spec pierde parlays válidos cuando hay techo de cuota (se quitó; 4,5 s
sin ella); las cuotas llegan como float4 y 1,25 × 1,76 salía "2,20 en el
escalón 1"; un ticket se guardaba fila a fila y uno a medias habría quedado
inmutable y sellado (ahora una transacción con candado por día); y
`fixtures` sobrescribe la hora de un partido reprogramado, así que la pata
guarda su hora original y se anula a las 48 h de ella. Acierto frente a la
probabilidad EFECTIVA (solo patas que contaron). Sin doble oportunidad:
ningún proveedor la cotiza. Desplegado apagado el 12-oct 00:10 UTC SOBRE las imágenes de producción (que
ya llevan la app móvil sin commitear) copiando SOLO los archivos del parley:
desplegar la carpeta entera habría metido también los cambios de tarjetas y
córners del 10-oct, que no estaban desplegados. El árbol `~/quantfut` del
VPS no tiene ni la app móvil ni el parley: un `docker compose build` los
quitaría. Primer ensayo: los cinco parlays salen de 2 patas; la búsqueda
prefiere pocas patas porque cada una paga margen.

## 2026-10-11 — Pestaña Pronósticos con el formato «Pronósticos IA»

El usuario pidió la ficha de la referencia (pronóstico destacado, Confianza IA,
xG proyectado, diferencial Elo, tendencia de goles, dictamen). Se adoptó el
diseño, no las cifras: «Confianza IA» y Elo no existen en el contrato y el
documento de detalle prohíbe fabricarlos a partir de un porcentaje histórico.
Se sustituyeron por magnitudes que el servidor sí tiene: probabilidad con cuota
justa, favorito 1X2 (`ficha.probabilities`) y tendencia de más de 2,5 goles
(`promedios.pct_mas_2_5`). El xG proyectado sale de las lambdas del ajuste de
mercado (`alta_prob_picks.fit`), que `high_probability` ahora expone como `xg`
sin filtrar el ajuste crudo; en mercados sin ajuste queda «—». El dictamen se
compone en el cliente solo con esos datos. Con el visto bueno del usuario se desplegó SOLO `mobile.py` (el remoto era
idéntico a HEAD) con `docker compose cp` + reinicio de `api`, sin tocar el
worker; producción ya devuelve `xg` real. Ojo: al ser `cp`, una recreación del
contenedor desde la imagen lo perdería hasta reconstruirla. APK debug
compilado e instalado en el emulador.

## 2026-10-11 — Pantalla VIP con el formato «VIP ELITE» (solo app, sin backend)

Se movió `LiveVipScreen` a `live_vip.dart` y se rediseñó. De la referencia se
tomó la estructura; se descartaron las cifras y promesas que el servidor no
respalda (miembros, testimonio, pruebas gratuitas, «pago con Google Play»,
«cancela cuando quieras»): el cobro sigue sin proveedor y el botón dorado solo
muestra el mensaje de la sección `compras`. «Mejor precio» se marca por el menor
equivalente mensual entre los planes que llegan del servidor. Sin despliegue de
backend; APK debug instalado en el emulador. 21 pruebas Flutter aprobadas.

## 2026-10-12 — Ficha de partido: el pick sellado sigue visible al empezar el partido

Pumas–Cruz Azul mostraba «No hay pronósticos publicados» a los 20 min de empezar
aunque el pick existía en `alta_prob_picks`: `high_probability` descartaba todo
pick con `kickoff_utc <= now`, decisión pensada para los listados de «próximos»
y no para la ficha. Ahora `detail()` pide `started=True` y recibe también los
picks de partidos en curso o liquidados, con `started` y `outcome`/marcador
(LEFT JOIN `alta_prob_results`); el reparto gratis/VIP no cambia, y home y
listados siguen sin verlos. La app muestra una franja «EN JUEGO / ACERTADO /
FALLADO». Desplegado SOLO `mobile.py` (el remoto era idéntico salvo este cambio)
con `docker compose cp` + reinicio de `api`; copia previa en
`~/backups/mobile.py.*.bak` del VPS. Mismo aviso de siempre: al ser `cp`, una
recreación del contenedor desde la imagen lo perdería hasta reconstruirla.

### Marcador en vivo para la app (2026-10-11)

Decisión: columnas `live_*` propias (db/056) en vez de reutilizar `status` y
`home_goals`. Esos los usa el pipeline de picks y `results.py` los escribe con
`result_recorded_at`; un marcador provisional ahí contaminaría la auditoría
temporal. `ingest/live.py` hace UNA petición `fixtures?live=all` por pasada y
ninguna si no hay partido en ventana, así el coste no depende de los usuarios.
Cron cada 45 min por decisión del usuario (cuota); `*/45` da huecos de 45 y 15
min. El marcador sale en `/mobile/v1/matches/{id}` como `partido.vivo`, fuera
de la ficha cacheada. Se descartó `tunjayoff/sofascore_scraper`: licencia
PolyForm Noncommercial y raspado contra los términos de Sofascore.
Desplegado el 2026-10-12 sin tocar compose: imágenes delgadas sobre las vivas, con
respaldo `before-live` (api `quantfut-api-mobile-rewards`, worker `quantfut-worker`).
Primera pasada real: 6 candidatos, 2 en juego, 1 petición. Franja `LiveScoreStrip`
en Flutter (falta recompilar la app). Pendiente: marcador en el calendario.

### Pestaña Mercados rediseñada (2026-10-12)

Decisión: se adapta el lenguaje visual de la referencia (radar, anillos, puntos)
pero NO sus alertas en vivo («Más/Menos en vivo», «Quién marca en el primer
tiempo»): los modelos pronostican antes del partido y el catálogo de evidencia
lo dice expresamente. Cada tarjeta sale de `MarketCatalog` (mejor línea
confirmada + publicados resueltos), así que no hay cifras inventadas y una
familia sin línea confirmada muestra «—». Animaciones con CustomPainter, sin
paquetes ni assets de terceros; se detienen con «reducir movimiento».

### Mercados: pantalla por mercado e historial por pronóstico (2026-10-12)

Decisión: se quita la tarjeta «Rendimiento registrado» de Mercados; cada
familia abre su pantalla con «Hoy» (pronósticos abiertos que el servidor ya
entrega) y «Anteriores» (resueltos, acertó/falló). Las cifras salen del
historial del servidor, no del JSON empaquetado: el radar decía 75/96 y el
servidor 89/114. Nuevo `GET /mobile/v1/markets/history` (alta probabilidad,
selladas, rango público 75-90 %, anuladas fuera, probabilidad con precisión
pública). Los pronósticos VIP bloqueados no se atribuyen a un mercado (su
metadato no lo lleva) y no se muestran en «Hoy»; el reparto gratis/VIP sigue
decidido por el servidor.

El historial por mercado manda `home_corners/away_corners` y la app los muestra en los
mercados de córners en vez del marcador de goles (despliegue 2026-10-12, respaldo
`before-corners`). Posible hueco de datos: Operario-PR - Goias figura 14-0 en córners;
un 0 puede ser un córner no capturado, no un cero real.

### Candados dentro de cada mercado (2026-10-12)

Decisión del usuario: los pronósticos VIP bloqueados se ven dentro de su mercado
(partido, hora, candado), sin el pick. Cambio de política: antes el metadato
bloqueado no llevaba `market`. Ahora sale SOLO la categoría; selección, línea,
probabilidad, cuota y `fit` siguen fuera (test actualizado). Sin tarjeta de venta:
tocar el candado abre VIP. Escalera no se incluye (su metadato no se reparte por familia).

### Gratis: uno por mercado, el de mayor probabilidad (2026-10-12)

Decisión del usuario: el escaparate gratuito debe mostrar lo más sólido para que se vea que la
mayoría acierta. Antes: 10 % del lote por mejor cuota. Ahora: un pronóstico por mercado con
candidatos, el de mayor probabilidad (empate: cuota). El reparto de cada lote queda fijo en
`mobile_free_allocations` al crearse, así que la regla solo afecta a lotes NUEVOS salvo que se
amplíe el lote vigente a mano (solo añadir, nunca quitar).

Desplegado el 2026-10-12 (respaldo `quantfut-api-mobile-rewards:before-gratis`). Lote 2026-10-11
ampliado a mano con 3 gratis (córners, goles, goles del visitante; free_count 3 -> 6). Hándicap (7)
y doble oportunidad (1) siguen bloqueados: sus candidatos no tienen cuota publicada y un gratis
sin cuota real no se entrega.

### Gratis: cuota entre 1,20 y 1,60 (2026-10-12)

Decisión del usuario: el gratis debe tener cuota publicada entre 1,20 y 1,60, el de mayor probabilidad
por mercado. El usuario pidió 1,40-1,60 pero con 75-90 % de probabilidad las cuotas reales van de 1,01
a 1,25 (132 candidatos en 7 días, 0 en 1,40-1,60), así que eligió piso 1,20. Desplegado (respaldo
`before-cuota`). Los 3 gratis añadidos a mano al lote 2026-10-11 se quitaron (cuotas 1,08-1,19; fuera de
rango; free_count 6 -> 3, auditado). Hoy no queda ningún gratis abierto: ningún candidato sin empezar
tiene cuota en rango.

### Gratis: la cuota manda (2026-10-12)

Decisión del usuario: el gratis de cada mercado es el de MAYOR cuota publicada (tope 1,60, sin piso),
aunque tenga menos probabilidad que otros; empate por probabilidad. Sustituye al rango 1,20-1,60 por
probabilidad. Desplegado (respaldo `before-mayor-cuota`) y los 3 gratis quitados antes se volvieron a
añadir al lote 2026-10-11 (Elfsborg 1,19, Valerenga 1,18, Malmo 1,08; free_count 3 -> 6). Hándicap y
doble oportunidad siguen sin gratis: sus candidatos no tienen cuota publicada.

### Gratis automático (2026-10-12)

Decisión del usuario: la regla es permanente, no un parche por lote. `top_up()` corre en cada lectura
(`allocations()`, dentro del mismo bloqueo del lote) y hace gratis el pronóstico sin empezar de mayor
cuota de cada mercado que no tenga ya uno abierto. Solo añade (no quita lo que el usuario ya vio),
es idempotente y queda auditado (`mobile:allocation_topup`). Desplegado (respaldo `before-automatico`):
tres lecturas seguidas dejaron free_count en 6, sin cambios. Ya no hacen falta ampliaciones manuales.
La Escalera conserva su regla de un solo pendiente gratuito.

### Tarjeta del pronóstico nueva (2026-10-12)

Sustituye al destacado + 4 recuadros por: 4 anillos (Más 2,5, Ambos marcan, Más 1,5, Gana local),
caja del pronóstico y tabla «¿Cuántos goles?» (al menos 1/2/3 por equipo = team_totals 0,5/1,5/2,5).
El «1T >0,5» de la referencia NO existe: no hay modelo de primer tiempo, se usa «Más 1,5».
Backend: `ficha.modelo` (model_card, 2 decimales) sale en /mobile/v1/matches/{id} SOLO si el usuario
tiene un pronóstico visible de ese partido; las probabilidades de las que se deriva el pronóstico no
se regalan para todos los partidos. Sin datos del modelo, la tarjeta no dibuja anillos ni tabla.

Ligas solo sharp (sin predicción propia): `market_card()` calcula la misma tarjeta desde el ajuste a
Pinnacle del pick (lambda, mu, rho) con `pricing.price_all_markets`, y la marca `fuente: mercado`; la app
lo dice debajo de los anillos. Solo para picks con `fit` (goles, hándicap y córners); doble oportunidad y
1X2 no guardan `fit` y siguen sin anillos. Sin desplegar al escribir esto.

## 2026-10-11 — Alta probabilidad: medición 62–95 % (paso previo a ampliar el rango)

- Pedido del usuario: abrir el rango de alta probabilidad a 62–95 % en todos los
  mercados, ordenando por mayor cuota. Decisión: medir ANTES de publicar (el 80 %
  se validó; los tramos 62–80 % nunca se midieron).
- `eval/alta_prob_calibracion.py --amplio` (`run_amplio`): todos los candidatos de
  62–95 %, tramos 62-67/67-72/72-76/76-80 + los de siempre, mismo criterio
  (tramo con n≥100: real ≥ prometido−2·SE; global ≥ −1 punto). 14.305 partidos.
  Resultado en `.local/alta_prob_amplio_20261011.json`: pasan 27 de 40 líneas
  (1X2, doble oportunidad, hándicap −1/0/+1/+1,5/+2, marca local/visitante, más
  de 1,5/2,5, menos de 3,5/4,5, ambos marcan «sí», córners más 6,5/8,5 y menos
  11,5/12,5 totales). No pasan: ambos marcan «no», menos de 2,5, y la mayoría de
  córners por equipo (déficits de 0,1–1,2 puntos o un tramo bajo).
- Aún NO se publica nada: falta decidir la tabla sellada nueva (`alta_prob_picks`
  tiene `match_id UNIQUE`, un pick por partido) y la cadena de hashes.

### Pestaña Pronósticos con todos los mercados (2026-10-12)

Pedido del usuario: la pestaña queda como su referencia (tarjeta «Análisis estadístico» + lista de mercados
con nivel + marcadores). `api/partido_mercados.py` deriva la lista de (lambda, mu, rho): la predicción propia
o, en ligas solo sharp, el ajuste a Pinnacle del pick; los cálculos son los de `pricing` (comprobado: diferencia
0,0 frente a `predictions.markets` en 40 predicciones). Córners y tarjetas salen de `estadisticas_mercado` y
SOLO con sus `LINEAS_HABILITADAS`. Nivel por probabilidad (alta >= 75, sólida >= 60, moderada); «oportunidad»
solo con cuota publicada y prob x cuota > 1,02; sin cuota publicada se muestra la cuota justa etiquetada.
Acceso: abiertas = las del usuario (gratis/desbloqueadas) o todas con VIP; el resto va con candado que solo
dice la categoría y SIN orden por probabilidad (el orden la filtraría). La app agrupa los candados por categoría.
Desplegado (respaldo `before-mercados`): 24 mercados en un partido real, 0,58 s la primera vez y 15 ms con caché.

AVISO de despliegue: el VPS corre el módulo VIEJO de córners/tarjetas (líneas anteriores a la revisión del
10-oct, que se dejó «sin desplegar» a propósito: más de 6,5 y 9,5 córners siguen apareciendo). La lista sigue lo
que está desplegado y se alineará sola cuando esa revisión se despliegue (decisión sobre los picks del worker).
La tarjeta anterior de anillos/«¿Cuántos goles?» se retiró de la pestaña (la sustituye la lista).

## 2026-10-11 — Alta probabilidad ampliada 62–95 % (`alta_prob_ext`), implementada sin desplegar

- Decisión del usuario: tabla aparte (`db/057`, un candidato por partido+mercado+
  selección+línea, inmutable) con todo lo aprobado por la prueba amplia; la línea
  de 80–95 % (`alta_prob_picks`) no cambia. Por qué aparte: `match_id UNIQUE` de
  `alta_prob_picks` y su lote ya sellado no admiten varios picks por partido.
- `publish/alta_prob_ext.py`: selección (`alta_prob.elegir_ext`, listas `*_EXT`),
  control por mercado (reusa `ap.control`), liquidación (encadenada en
  `eval/clv.settle_pending`). Sellado: bloque `alta_ext` en el lote desde
  `LOTE_ALTA_EXT_DESDE = 2026-10-12`; los lotes anteriores no cambian de hash.
- App: `mobile.py` lee ambas tablas (62–95 %), sin duplicar partido+mercado+
  selección+línea (manda la fila original); gratis = mayor cuota por mercado, tope
  1,60; `pick_key` de las filas ampliadas es `ext_id`. Escalera sigue en 75–90 %.
- Apagada: `ALTA_PROB_EXT_ENABLED=0`. Falta aplicar db/057 en el servidor, activar
  el flag ANTES del sellado de las 08:00 UTC del 12-oct, y verificar con
  `python -m qf.publish.alta_prob_ext preview`. Si no se despliega a tiempo,
  mover `LOTE_ALTA_EXT_DESDE` al primer lote sin sellar.
- Desplegado el 12-oct ~02:40 UTC con visto bueno del usuario. db/057 aplicada;
  archivos copiados a `api` y `worker` partiendo de lo que había en producción
  (el servidor NO tenía la revisión de córners del 10-oct en `alta_prob.py`: se
  conservó, solo se añadió lo de la ampliación). Imágenes confirmadas con
  `docker commit` (`quantfut-api-mobile-rewards:20261011`, `quantfut-worker:latest`)
  y recreados `api` y `worker` con `ALTA_PROB_EXT_ENABLED=1` en `.env`; respaldo en
  `~/quantfut/deployments/before-ext` y etiquetas `:before-ext`. Preview real:
  287 candidatos en 25 partidos (143 con cuota publicada), 0,62–0,95. El árbol
  `~/quantfut/src` del VPS sigue sin actualizar. Falta: ver el primer sellado (08:00
  UTC) con `n_alta_ext` > 0 y recompilar la app.

### 1ª mitad: prueba histórica y mercados publicados (2026-10-12)

`eval/primer_tiempo.py` (football-data, cuotas de Pinnacle, entreno 2019-2022 con 5.743 partidos y medida en
2022-2025 con 6.236, criterio de `alta_prob_calibracion` fijado antes): PASAN «ambos anotan 1T: no» (n=6.236,
79,9 frente a 80,5 prometido) y «gol en 1T: sí» (n=6.015, 72,6 frente a 71,7). No pasan: ganador 1T visitante
(n=27), más de 1,5 goles 1T (tramo 62-67 %: 61,7 frente a 64,4) y ganador 1T local pasa pero con n=159, por
debajo de las 500 muestras que exige el catálogo de evidencia: no se publica. Modelo: goles del 1T Poisson con
proporción (0,4366 local, 0,4588 visitante) del mismo ajuste de mercado; vive en `model/primer_tiempo.py`.
Se publican solo esos dos, por ese lado y en el tramo medido (62-95 %). Desplegado (respaldo
`before-primer-tiempo`). Ojo: hay OTRA edición sin commit de `mobile.py` (alta probabilidad 62-95 %, db/057)
que no es de esta tarea y NO está desplegada.

### Parley activado (2026-10-12, 05:5x UTC)

Visto bueno del usuario. Fecha de arranque = 12-oct (`LOTE_PARLEY_DESDE`, ya fijada): el sellado de las
08:00 UTC es el primero que lo lleva. ANTES de activarlo, el ensayo (`parley_datos preview`) mostró una pata
«más de 9,5 córners», línea que la revisión del 10-oct había quitado y que el VPS aún permitía. Con la
aprobación del usuario se desplegó esa revisión al worker y a la API (`estadisticas_mercado.py` y, en el
worker, solo el hunk de `CORNERS_HABILITADOS` de `alta_prob.py` sobre el archivo ya desplegado por la otra
sesión; respaldo `quantfut-worker:before-lineas`, `...:before-lineas-api`). Efecto: córners más de 7,5/8,5 y
menos de 9,5/10,5/11,5; tarjetas menos de 4,5/5,5/6,5; fuera córners más de 6,5/9,5 y local más de 2,5 en alta
probabilidad. Segundo ensayo: 5 parlays de 2 patas, 0 con líneas no validadas. `PARLEY_ENABLED=1` en el
`.env` del VPS (copia en `releases/lineas-10oct-20261012/env.before-parley`), worker y API recreados.
PENDIENTE: quién ve cada parley. `/parley` es público y la app los muestra todos; falta el reparto
gratis/VIP (hoy son gratis para cualquiera).

### Corrección: hora real de la activación del Parley y nuevo horario de sellado (2026-10-12)

La sección «Parley activado (05:5x UTC)» y el mensaje del commit fe441c1 están MAL en la hora: la pregunta al
usuario esperó ~9 h y la activación se ejecutó a las 14:48 UTC, no a las 05:5x. El sellado de las 08:00 UTC
de hoy ya había corrido con el Parley apagado (`parley: desactivado`, 0 parlays), así que NO hay parlays
sin sellar (`hashchain verify`: 14 lotes OK). El primer lote con Parley es el del 13-oct.
Decisión del usuario: el sellado diario pasa a las 07:00 de Ciudad de México = 13:00 UTC, siempre (México no
tiene horario de verano desde 2022; cron corre en UTC). `scripts/crontab`: `0 13 * * *` (antes `0 8`),
aplicado en el VPS (copia `scripts/crontab.before-13utc`) y recargado con `crontab /etc/cron.d/quantfut`, sin
reiniciar el worker. Efecto: solo entran partidos que empiezan DESPUÉS del sellado; los de 08:00-13:00 UTC
dependen del lote anterior (el job ya mira partidos de hoy y mañana). El comentario de `daily.py` («08:00,
antes del primer kickoff europeo») queda desfasado; no se tocó porque ese archivo tiene cambios de otra sesión.

## 2026-10-12 — App actualizada en el emulador Android

Pedido: «despliega el trabajo». Compilada la app del espacio de trabajo actual,
con Estadísticas, Coins, mercados y la nueva pestaña Parley. `flutter analyze`
sin incidencias; suite completa `flutter test`: 32 pruebas aprobadas.
`flutter build apk --release`: correcto, 59,8 MB. Instalación con `adb install -r`
confirmada (Success) en Medium_Phone_API_37.0, emulator-5556, sin borrar los datos.
Aplicación abierta y navegación Inicio / Predicciones / Parley comprobada con
respuesta real; Parley activo pero sin tickets publicados hoy, estado mostrado
sin inventar selecciones. Registro de errores Android/Flutter vacío.

API HTTPS comprobada: /mobile/v1/config, /mobile/v1/home y /parley devuelven 200.
La configuración real entrega 62–95 %. Los servicios del VPS ya estaban activos;
no se volvieron a desplegar archivos ni trabajadores desde este árbol local.
Firebase/registro inicial continúa únicamente en el plan.

APK: apps/mobile/build/app/outputs/flutter-apk/app-release.apk (1.0.0+1).
SHA256: 3D963890AB6FFF66CA0A46AC76B2377DBAFE92878DC80E635AD0F0213037E62F.
Captura: apps/mobile/docs/validation/real_mobile_20261011/release-parley-20261012.png.
Este APK conserva la firma de desarrollo configurada en el proyecto; no se ha
publicado en Google Play ni cambiado la firma o el identificador de la aplicación.

## 2026-10-12 — Firebase Core e identidad definitiva de QuantFut

Decisión del usuario: comenzar Firebase por fases en el proyecto existente
`pronosticos-deportivos-85ffa`; después de la pausa, fijar nombre QuantFut e
identificadores Android/iOS `com.saptain.quantfut`. Por eso se generaron apps y
configuración nuevas, en vez de conservar los registros `com.example.gobet`.
El usuario completó el acceso de Google y pidió eliminar los dos ejemplos.
Ambos registros `gobet` se eliminaron; la lista remota confirma únicamente
QuantFut Android e iOS activos. Configuración Android descargada de nuevo,
verificando que contiene solo el paquete definitivo.

La fase actual instala `firebase_core` y espera su inicialización antes de
abrir la app, con reintento visible si falla. Firebase está activo por defecto.
Se conserva FastAPI/Postgres como autoridad de cuentas, suscripción, saldo y
pronósticos: Auth/Google, FCM, Analytics, Crashlytics, Performance y Remote
Config siguen pendientes. Las herramientas CLI quedan locales e ignoradas;
la configuración pública puede versionarse, las credenciales privadas no.

Validación: análisis Flutter limpio, 35 pruebas aprobadas y APK debug con la
nueva identidad compilado/instalado en emulator-5556. Registro nativo confirma
`FirebaseApp initialization successful`; el arranque abrió el calendario con
datos reales. Arnés inicial y posterior: 911 aprobadas, 21 omitidas y una
advertencia; Docker no disponible. iOS tiene bundle ID, opciones y plist
incluido en Runner, pero necesita compilación/ejecución en Mac. Firma Android
de distribución pendiente. Detalle: apps/mobile/docs/FIREBASE_INSTALACION_20261012.md;
evidencia: apps/mobile/docs/validation/firebase_base_20261012/.


### Doble oportunidad con cuota real en el Parley (2026-10-12)

CORRECCIÓN de la nota «ningún proveedor la cotiza»: API-Football SÍ cotiza Doble Oportunidad (bet 12, 8 casas
en un partido de La Liga, entre ellas Bet365, Betano, 1xBet y William Hill; valores `Home/Draw`, `Home/Away`,
`Draw/Away`). Se descartó sintetizarla desde el 1X2: una cuota justa calculada no la ofrece nadie y no sirve de
precio de referencia; se capturan las cuotas reales. Hecho: (1) `ingest/af_odds.py` guarda bet 12 como
`double_chance` 1X/12/X2 (grupo completo, nombre exacto, soft books y Pinnacle); sin peticiones extra; primera
pasada: 65 partidos x 4 casas. (2) Solo el PARLEY la usa: `escalera_datos.opciones(incluir_doble=True)` añade
`candidatos_doble` (probabilidad = P1+PX de Pinnacle sin margen) con cuota de `_cuotas_af`; `parley.MERCADOS_PARLEY`.
La Escalera NO cambió (verificado en producción: 323 opciones evaluadas, 48 en rango, antes y después). (3) db/059:
el CHECK `parley_patas_market_check` rechazaba `double_chance` y habría roto el guardado del primer parley; la migración
solo amplía la regla (0 filas afectadas). Desplegado en worker (respaldos `before-doble`, `before-doble-parley`).
Ensayo: 4 patas de doble oportunidad con cuotas reales (Betano 1,16/1,29/1,67, Bet365 1,33).
PENDIENTE (toca archivos de la otra sesión, alta probabilidad ampliada): que `alta_prob_datos._ref` use esas cuotas
para que la doble oportunidad pueda ser pronóstico gratis; hoy `_ref` devuelve sin precio. Ideas aún sin hacer:
informe de calibración por origen (Pinnacle frente a córners/tarjetas), test binomial exacto en el control del parley
(con n=50 y p=0,24 el `z<=-4` actual no puede dispararse) y orden del armado (medido: +0,6 % en un día).


## 2026-10-12 — Servicios Firebase, identidad y despliegue de API

El usuario amplió el alcance a Auth/Google, FCM, Analytics, Crashlytics,
Performance, Remote Config y App Check. Se conservan FastAPI/Postgres como
autoridad comercial; Firestore/Storage/Functions P2 no se activaron. Google
está habilitado en Firebase y los recursos Android/iOS preparados. App Check
usa Play Integrity en distribución y proveedor de desarrollo registrado en
emulator-5556; enforcement continúa apagado. Los registros de ejemplo ya no
están activos.

Decisión de identidad: cabecera explícita Firebase y verificación de proyecto/
revocación; no convertir un token inválido en sesión anterior. El mismo correo
no toma control de una cuenta: vínculo solo demostrando la sesión previa.
Se preservan ID, saldo, VIP y referidos. Consentimientos versionados;
medición/diagnóstico/avisos opcionales apagados por defecto. Avisos genéricos,
ruta interna validada y permisos consultados de nuevo al abrir; bandeja y
cola con propietario/caducidad/reintentos. El envío automático no está activo.

Tras rechazo de revisión automática, el usuario autorizó explícitamente crear
quantfut-backend con lectura Auth y envío FCM, generar clave privada, y después
desplegar en producción. Clave fuera de Git y Flutter, privada y montada como
solo lectura. SDK 7.7.0 instalado, migración 058 aplicada, solo API recreada.
Compose e imagen anteriores respaldados, reversión de arranque preparada.
Paquete sobre la imagen real del servidor, sin cambios deportivos de otras
sesiones. La primera compilación falló al interpretar SHA como repositorio;
se corrigió usando una etiqueta local de la misma imagen y el despliegue pasó.

La imagen en ejecución incluye módulos móviles que todavía no están en el
checkout del VPS. Una comprobación previa detuvo la sincronización antes de
escribir archivos; no se intentó reconstruir desde ese checkout antiguo.
El paquete y fuentes exactas quedan en releases/firebase-backend-20261012.
Una futura reconstrucción debe partir de la imagen vigente o reconciliar
primero todo el código desplegado, para no perder funciones anteriores.

Servidor verificado: credencial Auth válida sin descargar usuarios reales,
seis tablas presentes, pip check correcto, API HTTPS config/home 200;
preferencias/avisos anónimos 401 y acceso Google cerrado 503. Google continúa
FIREBASE_AUTH_ENABLED=0 y qf_google_auth_enabled=false hasta documentos vigentes.

Validación: análisis Flutter limpio, 38 pruebas aprobadas,APKdebug instalado y
calendario real con 43 partidos. Preferencias opcionales comprobadas apagadas;
arranque posterior al registro App Check sin error fatal/Flutter/intercambio
en la observación. 11 pruebas Firebase y 8 escenarios PostgreSQL real en esquema
aislado con rollback, sin cambiar filas comerciales. Arnés completo: 924 aprobadas,
21 omitidas, 2 advertencias; Docker local no disponible. No se ha probado Google
con usuario real, entrega FCM ni iOS. Firma de distribución y Apple/APNs
pendientes; selector de 6 idiomas disponible, traducción completa pendiente.

Datos legales confirmados por el usuario: Saptain LTD; E Coast Rd, Victoria,
Seychelles; admin@pronosticosdeportivos.com; edad 18; Estados Unidos, toda Europa
y Latinoamérica. Se actualizaron borradores y fuentes primarias. Proveedores
Contabo/Proton identificados en notas; faltan ubicación contractual, ciclos de
retención/respaldo/procedimiento de derechos y revisión territorial. No se
publicaron borradores ni se registraron como aceptados. Las leyes obligatorias
de mercados de destino no se excluyen por la constitución en Seychelles.

Detalle: apps/mobile/docs/FIREBASE_SERVICIOS_20261012.md. Evidencia sin secretos
en apps/mobile/docs/validation/firebase_services_20261012/; borradores y control
de publicación en docs/legal/.

## 2026-10-12 — Tapjoy Offerwall (Unity) como proveedor de monedas

- Decision: callback S2S estandar de Tapjoy (GET, `verifier=md5(id:snuid:currency:secret)`), moneda *self-managed*. Solo creditos: la doc de Tapjoy no define reversiones; un `currency` negativo se rechaza con 403. Errores definitivos siempre 403 (Tapjoy reintenta 4 dias ante cualquier otro codigo distinto de 200/403).
- El offerwall se abre por SDK nativo (no URL): `launch` devuelve `{sdk,sdk_key,user_id}` y `MainActivity.kt` hace `Tapjoy.connect` con `USER_ID`=uid del monedero, que llega como `snuid`.
- Dashboard (cloud.unity.com > Tapjoy Offerwall): app Quantumfut (Android, no activa), moneda `Monedas` ($1 = 1000), placement `coins_offerwall` + tarjeta `Coins`. Secreto en `QF_TAPJOY_SECRET` (VPS); la cuenta Tapjoy esta en revision.

- Secret keys de proveedores (Tapjoy, BitLabs) editables desde /control/recompensas (db/060, columna `secret_enc`): AES-256-GCM con `cryptography` (pyca; AEAD estandar, auditado, sobre OpenSSL), nonce aleatorio y contexto `reward_provider:<id>` como AAD para que un secreto no se pueda mover a otra fila. La clave maestra `QF_SECRETS_KEY` vive solo en el entorno del servidor (rotacion con `QF_SECRETS_KEY_OLD`): copiar la BD no basta. Campo de solo escritura, auditoria sin el valor, variable de entorno como respaldo. Fallo cerrado: sin clave maestra el panel rechaza guardar.

- Despliegue VPS 2026-10-12 (sin git): codigo copiado al contenedor, `docker commit` a `quantfut-api-tapjoy:20261012`, compose apuntado a esa imagen y `compose up -d --no-deps api`. Respaldos en ~/backups/tapjoy-20261012 (env, compose, rewards.py/html previos); vuelta atras = imagen `quantfut-api-mobile-rewards:pre-tapjoy-backup` + env respaldado. db/060 aplicada; `QF_SECRETS_KEY` generada en el servidor (no esta en ningun otro sitio: respaldarla).

- 2026-10-12 — Firebase no arrancaba en el emulador (`channel-error` en `FirebaseCoreHostApi.initializeCore`): `GeneratedPluginRegistrant.java` estaba vacio (19 lineas) porque las dependencias de Flutter no estaban resueltas (avisos de `google_sign_in_android` inexistente). `flutter pub get` lo regenero (71 lineas) y `FirebaseApp initialization successful`. Si reaparece el mensaje «No pudimos iniciar QuantFut», comprobar primero `flutter pub get` y que el registrant liste los plugins.

## 2026-10-12 — Conservacion y limpieza Firebase puestas en marcha en el VPS

El codigo (`firebase_mantenimiento.py`, `scripts/firebase_operations.py`) existia pero NO estaba operando: el modulo no estaba en la imagen, el usuario `qf` no tenia crontab y la carpeta de copias no existia, mientras los textos legales ya prometen 30/90 dias. Ahora: modulo en la imagen (`quantfut-api-tapjoy:20261012-mant`), crontab diario a las 03:40 UTC solo con `daily` (`deliver` sigue sin programarse: el envio automatico esta apagado), alerta por Telegram si falla y rotacion extraida a `rotate()` con pruebas. Se probo la logica de limpieza con datos ficticios en transaccion revertida y la restauracion real de una copia en una base temporal. Limite conocido: la copia es parcial (sin citext ni deny_mutation) y no sustituye un respaldo completo ni uno fuera del VPS; el camino de alerta ante fallo no se ejercito con un envio real. Un limite de la conservacion: las tablas `sessions`/`email_tokens` no se limpian aqui (estan vacias hoy).

- 2026-10-12 — Limpieza de sesiones y tokens de correo (`cuentas_mantenimiento`), dentro de la tarea diaria 03:40 UTC. Plazos elegidos: sesiones 30 dias tras caducar/revocar (margen para investigar `reuso_refresh`; borra IP y user-agent), tokens retirados de refresh al borrar la sesion o al pasar `REFRESH_TTL_DAYS` (la sesion tiene caducidad absoluta de 30 dias, asi que la deteccion de reuso no pierde nada; borrados antes que su sesion por la FK), tokens de correo 7 dias. No toca cuentas, suscripciones, monedas ni `admin_audit`. Probado con tablas reales + FK en transaccion revertida. Pendiente: reflejar los plazos en la politica de privacidad publicada y revisar si procede una limpieza de cuentas inactivas.

- 2026-10-12 — APK release firmado verificado (`apksigner`, certificado CN=QuantFut, SHA-1 ya registrado en Firebase). El release fallaba por R8: el SDK de Tapjoy referencia clases `appset` opcionales; se anadieron sus reglas oficiales en `android/app/proguard-rules.pro` + `-dontwarn` para appset. Documento: apps/mobile/docs/FIRMA_ANDROID.md. Riesgo abierto: copia unica del `.jks` en `.local/`; falta respaldo fuera del equipo y activar Play App Signing al publicar.

- 2026-10-12 — Firma de release cambiada por decision del titular a `C:/1. llave/llave.jks` (alias `llave`, CN=ely marine / O=NavalQuiz: identidad de otro proyecto, riesgo aceptado: comparte firma). Huellas SHA-1/SHA-256 registradas en Firebase con la CLI y `google-services.json` actualizado (cliente OAuth nuevo). APK release verificado con `apksigner`. La clave anterior `quantfut-release.jks` sigue registrada pero sus contrasenas se perdieron al sobrescribir `key.properties`. No se guardan contrasenas en el repo.

## 2026-10-12 — Traducciones completas de la app (es, en, pt, fr, it, de)

Decision del usuario: traducir toda la app y mantenerlo siempre al dia (regla tambien en CLAUDE.md y en la memoria). Base: `gen-l10n` (ARB), `AppLocale` persistente que funciona sin Firebase, selector de idioma (bienvenida, acceso, Perfil, Privacidad), idioma del dispositivo como sugerencia. ~450 textos de los 29 archivos alcanzables desde `main.dart`; los 60 archivos de la plantilla original y 5 de `lib/product` son codigo muerto y no se tradujeron. Decisiones clave: (1) los textos de pronostico/mercado (`texto`, `titulo`, `seleccion`, `grupo`, `nota`) se reconstruyen en la app desde `market/selection/line` + equipos (`pick_labels.dart`), sin tocar los datos sellados ni el servidor; (2) formateadores sin contexto leen el idioma de `AppLocale` y cada pantalla depende de `context.l10n` para reconstruirse al cambiar; (3) mensajes del backend por `Accept-Language` con un catalogo unico (`src/qf/api/mensajes.py`) y un manejador global de `HTTPException`: sin cabecera todo sigue en espanol; (4) pruebas que lo exigen: paridad de ARB, cero cadenas fijas (con o sin acentos), render de las 5 pestanas en los 6 idiomas con fuentes reales sin desbordes, cambio en caliente, y catalogo backend completo via `ast`. Limites: traducciones hechas por un modelo, sin revision nativa; textos legales publicos y correos de cuenta sin traducir; el backend con `mensajes.py` NO esta desplegado todavia. Detalle: apps/mobile/docs/TRADUCCIONES.md.

- Despliegue VPS 2026-10-12 (mensajes por idioma): `mensajes.py` + manejador de HTTPException + terminos/mensaje de monedas traducidos. `main.py` desplegado se PARCHEO (solo import + manejador): el local trae cambios de Parley/Alta prob. sin desplegar. Respaldos en ~/backups/mensajes-20261012; vuelta atras = imagen `quantfut-api-tapjoy:pre-mensajes-backup` (compose `image:`) + `compose up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-msg`.

- 2026-10-12 — Icono y arranque nativo: se reemplazo el icono «GoBet» de la plantilla por el «Q.» verde sobre fondo oscuro de la bienvenida (no habia logotipo de QuantFut en el repo). Generado con `apps/mobile/tool/make_icon.py` (Pillow) + `dart run flutter_launcher_icons` (Android clasico y adaptable, iOS) y el fondo de `launch_background` pasa de blanco a #090f1a. Es un icono provisional con la identidad actual de la app: si el titular tiene un logotipo propio, sustituir `image/quantfut_icon*.png` y repetir el comando.

## 2026-10-12 — Textos legales finales

Los tres textos (términos, privacidad, eliminar cuenta) ya no tienen marcadores y
describen solo lo que el servidor hace: retención 30/90/30/7 días, copias de 30 días,
eliminación manual atendida por correo. Decisión clave: el titular ordenó publicarlas (2026-10-12). Se desplegó solo
`legal.py` + `legal_pages/` y se parcheó el `main.py` del contenedor (import + include_router;
el local trae cambios de otras tareas sin desplegar). Respaldos en `~/backups/legal-20261012`;
vuelta atrás = imagen `quantfut-api-tapjoy:pre-legal-backup` en el compose y
`up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-legal`. `/legal/*` da 200
desde el dominio. NO se activó Google ni se registran aceptaciones: eso sigue siendo del titular.
`REVISION_Y_PUBLICACION.md` estaba obsoleto (decía `.com` y «borrador») y se reescribió; los
`*_BORRADOR.md` quedan como historial. Los textos legales siguen solo en español.

## 2026-10-12 — xG de API-Football conectado al entrenamiento

Decisión explícita del usuario: usar el xG actual de API-Football en el modelo.
La exclusión histórica del proveedor queda revocada y documentada. La respuesta
ya llegaba a matches.stats, pero el entrenamiento leía home_xg/away_xg vacíos.
Se conserva la primera pareja válida con origen y recepción real, sin sobrescribir
histórico ni revisiones posteriores. Reconsulta diaria 12:10 UTC (06:10 CDMX),
35 días, tope 100, espera 20 h y reserva del 15% de cuota. db/061 aditiva.

Punto clave: cargar xG hoy no lo vuelve disponible en una predicción antigua.
Dixon-Coles y más-menos lo usan solo desde su captura; el replay secuencial de
Kalman conserva goles para esta fuente hasta soportar llegadas tardías. La
recepción original del xG previo sigue sin acreditarse. Hash de dataset/código
incluye las nuevas entradas y protección. No se relajan puertas.

Desplegado solo en worker, sobre archivos cotejados con la versión real, sin
reiniciar servicios. Imagen quantfut-worker:latest verificada; respaldo
quantfut-worker:xg-before-20261012 y paquete completo en
/home/qf/quantfut/deployments/xg-api-20261012. El checkout viejo del VPS no se
usa como base de reconstrucción. API y NBA conservados.

Primera captura: 182 consultas, 149 parejas, 33 ausentes, cero errores; 13
competiciones. Entrenamiento: 49.505 filas, 148 parejas de la nueva fuente;
Sporting-Galatasaray se excluye por Turquía fuera del modelo, regla previa.
Comprobado que todas se ocultan antes de su recepción y entran después.
Modelo activo 2026.09.27-010508 intacto; no se lanzó otro entrenamiento.
Cadena: 14 lotes OK; HTTPS config/home/model-card 200.

Validación: 970 aprobadas, 22 omitidas y 2 advertencias; 79 pruebas dirigidas,
8 escenarios PostgreSQL temporal con rollback, 117 módulos compilables.
Las pruebas de API necesitaron sockets locales fuera del aislamiento Windows;
la primera ejecución aislada se atascaba en socketpair, no en código del proyecto.
Detalle y cobertura: docs/xg_api_football_20261012.md; evidencia ignorada en
.local/xg_api_20261012/. Pendiente cobertura sostenida y próximo entrenamiento.

## 2026-10-12 — Acceso con Google activado

Orden del titular. Tres piezas, en este orden: (1) servidor `FIREBASE_AUTH_ENABLED=1` en
`~/quantfut/docker-compose.yml` (copia previa en `~/backups/legal-20261012/docker-compose.pre-google.yml`);
(2) Remote Config `qf_google_auth_enabled=true`, `qf_terms_url` y `qf_privacy_url` apuntando a
`/legal/terminos` y `/legal/privacidad` (la app solo acepta esas dos rutas en pronosticosdeportivos.pro);
(3) el proveedor Google ya estaba habilitado en Firebase Auth.
Pruebas: `/app/v1/firebase/connect` con token falso pasó de 503 `firebase_deshabilitado` a 401
`firebase_token_invalido` (el servidor verifica contra Firebase); en el emulador la app muestra la
pantalla de acceso, el botón queda desactivado hasta aceptar y, al pulsarlo, abre el flujo de Google.
NO probado: sesión completa con una cuenta real (el emulador no tiene cuenta y no se introducen credenciales
de Google) ni FCM. Vuelta atrás: Remote Config `qf_google_auth_enabled=false` (apaga la pantalla al instante,
plantilla anterior en el historial de Firebase) y/o compose con `FIREBASE_AUTH_ENABLED: '0'` + `up -d --no-deps api`.

## 2026-10-12 — Correos de cuenta en 6 idiomas

Los dos correos propios (verificar y restablecer) estaban solo en español pese a la regla de
traducciones. Las plantillas viven en `comercial/correo.py` y el idioma sale del `Accept-Language`
(la app ya lo envía) en vez de guardarse en la cuenta: no hay migración y funciona también para
cuentas sin preferencia Firebase. El panel `/control` reenvía en español (el admin no conoce el
idioma de la persona). Un idioma desconocido cae a español. Desplegado con respaldo en
`~/backups/correos-20261012`; vuelta atrás = imagen `quantfut-api-tapjoy:pre-correos-backup` en el
compose. Imagen vigente: `quantfut-api-tapjoy:20261012-correos`. Las páginas web a las que llevan los
enlaces siguen en español (límite documentado en `TRADUCCIONES.md`).
Se marcaron como hechos cuatro pendientes de idioma/FCM que ya estaban implementados y sin tildar.

## 2026-10-12 — Entrenamiento con el nuevo xG iniciado

El usuario pidió ejecutar el entrenamiento y recibir aviso al terminar.
Versión 2026.10.12-221104 lanzada en el worker a las 22:11:04 UTC / 16:11 CDMX:
49.504 partidos, 148 parejas xG de API-Football, 11 ligas + 2 copas, validación
completa de 365 días y puertas habituales. No se amplían ligas ni se fuerza
activación: el modelo 2026.09.27-010508 permanece activo durante el cálculo.
La nueva fuente entra en el ajuste final y se oculta en cortes anteriores a
su captura; no atribuirle mejora retrospectiva en el backtest.

Proceso desacoplado de SSH, prioridad reducida y un hilo por biblioteca.
Snapshot del input y fuentes, log, estado con señal de vida cada 30 s y resultado
final en /srv/quantfut/artifacts/training-runs/xg-2026.10.12-221104/.
A las 22:15 UTC: proceso vivo, primer ajuste histórico, sin errores registrados;
/model-card interno y público 200. Una consulta urllib desde VPS al dominio
recibió 403; desde este equipo con User-Agent de navegador dio 200.

Automatización heartbeat resultado-del-entrenamiento-con-xg creada y verificada
en este chat, cada 15 min: avisar resultado/fallo, verificar registro/artefactos,
actualizar documentación y detener seguimiento; silencio mientras sigue.
El equipo y Codex deben estar encendidos para el seguimiento, no para el cálculo
remoto. Comprobaciones obligatorias inicial y final: 972 aprobadas, 22 omitidas,
2 advertencias. Documentación: docs/entrenamiento_xg_20261012.md.
El entrenamiento sigue en curso; todavía no hay métricas nuevas ni promoción.

## 2026-10-12 — Sentry instalado (errores)

Orden del titular. Dos proyectos en la organización `saptain`: `quantfut-api` (FastAPI, también
recibe los trabajos del worker) y `quantfut-app` (Flutter). Decisiones, todas por privacidad:
solo errores (sin tracing/replay/logs); el backend maneja tokens y claves en URLs, así que
`src/qf/observabilidad.py` apaga PII, cuerpos, variables locales, SQL y migas de pan, y limpia
cabeceras/cookies/query/usuario/`sys.argv` antes de enviar (pruebas en `tests/test_observabilidad.py`).
Se inicia desde `qf/__init__.py` para cubrir API y todos los `python -m qf...` del cron; sin
`SENTRY_DSN` no hace nada. El DSN vive solo en el `.env` del servidor.
App: Sentry se inicia únicamente si el diagnóstico está activado (mismo consentimiento que
Crashlytics) y se cierra al retirarlo; no basta un `beforeSend` porque los fallos nativos se
capturan antes que Dart. Texto del interruptor actualizado en los 6 idiomas y política de
privacidad (Sentry como encargado; publicada en `/legal/privacidad`).
Coste: `sentry_flutter` 10 exige Android 8.0, así que `minSdk` sube de 24 a 26 (la 9.x no compila
con AGP 9). Desplegado en la API (imagen `quantfut-api-tapjoy:20261012-sentry`, respaldos en
`~/backups/sentry-20261012`, vuelta atrás = `pre-sentry-backup`) y en el worker (pip + archivos +
`/etc/environment`, sin recrearlo; `~/quantfut/{requirements.txt,src}` actualizados para el próximo
build). Verificado: evento `QUANTFUT-API-1` desde la API y `-2` (excepción no capturada) desde el worker.
No verificado: la app en un dispositivo (exige consentimiento y sesión de Google).

## 2026-10-12 — «Sesión no válida» tras entrar con Google

Causa: `api/mobile.py` usaba `request: Request` en `member()` sin importar `Request`. Con
`from __future__ import annotations`, FastAPI no resolvía el tipo y trataba `request` como un
parámetro de consulta siempre vacío, así que la rama `X-QF-Identity: firebase` nunca se activaba
y el ID token de Google se validaba como sesión clásica: 401 en todo `/mobile/v1/*` con sesión.
Pasó desapercibido porque `connect`/`preferences` (otro módulo, sí importa `Request`) funcionaban.
Regresión cubierta en `tests/test_mobile_identidad_firebase.py`. Desplegado en la API (respaldo
`~/backups/mobile-identidad-20261012`, vuelta atrás = imagen `pre-mobile-identidad-backup`).
Lección: un `Request` sin importar no da error al arrancar; revisar esto en endpoints nuevos.
El registro de rechazos de identidad añadido en `api/firebase.py` se queda (aviso WARNING).

## 2026-10-12 — Elección de idioma como primera pantalla

Pedido del titular (captura de referencia con globo animado y cuadrícula de 6 idiomas).
`LanguageSelectionScreen` (`lib/l10n/language_selection_screen.dart`) sale solo la primera vez:
`QuantFutApp.home` la muestra mientras `AppLocale.chosen` sea falso y la app pasa sola al flujo
normal al elegir (ya escucha `AppLocale`), así que no se tocó el acceso con Google ni Firebase.
Quien actualiza la app la verá una vez, porque su idioma nunca se guardó como «elegido».
Animación dibujada en código (CustomPainter + controladores), sin dependencias: respeta «reducir
animaciones». Referencias consultadas, sin copiar código: `gskinner/flutter_animate` (BSD-3) y
`flutterfx/flutterfx_widgets` (sin licencia). La etiqueta de la captura («Neural interface
configuration») se cambió por «Configuración de idioma» y los textos van en los 6 idiomas.
No verificado visualmente en emulador (se interrumpió el reinicio): compararlo con la captura.

## 2026-10-12 — Una sola tarjeta destacada por partido

Antes el detalle pintaba una tarjeta verde por cada pronóstico (una por mercado) con chips para
filtrar. Ahora `featuredPick` (`live_forecast.dart`) elige UNA: la de mayor probabilidad y, si
empatan, la de cuota más alta (decisión del titular entre tres reglas; la cuota más alta y
probabilidad × cuota quedaron descartadas). Se quitaron los chips, que ya no filtran nada; el resto de
mercados sigue en la tabla «Mercados del partido». Es lógica del cliente: el servidor no cambia.

## 2026-10-12 — Alta probabilidad muestra solo 73-95 %

Pedido del titular: el apartado solo muestra pronosticos de mas de 73 %. Revierte la ampliacion
del 11-oct (62-95 %). Es un FILTRO DE LECTURA (`HIGH_MIN` en `api/mobile.py`): `alta_prob_ext`
sigue sellando candidatos desde 62 % y sus filas inmutables no se tocan, solo dejan de mostrarse
(cambiar `PROB_MIN_EXT` alteraria el sellado y se haria solo si el titular lo pide). Efectos: el
historial y el acierto mostrados pasan a calcularse solo sobre >=73 % (mismo filtro) y la pantalla
VIP ya leia el rango del servidor. El texto del apartado (`picksRangeHint`) ahora recibe el rango
del servidor en vez de tenerlo escrito en 6 idiomas. Desplegado con respaldo
`~/backups/alta-73-20261012` (vuelta atras = imagen `pre-alta73-backup`); la app instalada filtra
bien sin APK nuevo, pero su texto dira «62-95 %» hasta actualizarla.

## 2026-10-12 — Reto Escalera rediseñado (tarjetas de avance)

Pedido del titular: diseño ergonómico, % de avance, cuánto falta, si el reto sigue vivo, probabilidad
de cumplirse e historial. Una tarjeta por reto (`lib/product/live_ladder.dart`): anillo de avance,
barra con un tramo por escalón (verde ganado, ámbar en juego), estado «En juego» / «Por elegir»,
probabilidad estimada, saldo como MULTIPLICADOR (×1,56, decisión del titular: sin cantidades) y
escalones liquidados plegados. Orden: primero el que tiene un escalón en juego, luego el más avanzado.
Historial: tarjeta pequeña con cumplidos Y fallidos (decisión del titular, por honestidad de la tasa);
hoy está vacío (0 retos cerrados) y muestra un estado vacío.
La probabilidad es una ESTIMACIÓN (`ladder_progress.dart`): escalón en juego (si es visible) × la media
de probabilidad de los escalones liquidados elevada a los que faltan; la media viene del servidor
(`escalones.prob_media`, 79,1 % con 9 escalones) y solo se usa con ≥5 escalones, si no se asume el 73 %
medido en `publish/escalera.py`. La tarjeta lo dice («Estimación … No es una garantía»). Todo sale de
datos que el servidor ya entrega: sin cambios de backend ni despliegue. Referencias sin copiar código:
SandroMaglione/step-progress-indicator (MIT), JHBitencourt/timeline_tile (MIT), flutter_percent_indicator
(BSD-2); `InlitX/streak` es GPL-3.0 y se descartó.

## 2026-10-12 — Predicciones: menú, Alta probabilidad y Parley rediseñados

Pedido del titular (misma línea que el Reto Escalera). Menú superior (`predictions_switcher.dart`):
píldora con indicador que se desliza, icono + texto + contador (pronósticos abiertos y retos en marcha),
fijo arriba al hacer scroll; se cambia de sección tocando o DESLIZANDO el dedo (decisión del titular).
Alta probabilidad (`live_picks.dart`): tarjeta de acierto histórico real frente al prometido (hoy 80,9 %
sobre 141), pronósticos abiertos agrupados por día con la etiqueta «Mayor probabilidad» en el primero
(misma regla que la tarjeta única del detalle) y los de candado AGRUPADOS en una sola tarjeta plegable
(decisión del titular: había 54 candados casi idénticos ahogando a 5 gratuitos). Los nombres de liga
salen de `league_names.dart` (el payload solo trae el id; es un dato, no se traduce).
Parley (`live_parley.dart`): boleto con muescas, patas en línea de tiempo, reglas en una línea con ⓘ
que abre una hoja, y estados vacíos (sin parlays / sin historial). Todo con datos que el servidor ya
entrega: sin cambios de backend. Referencias sin copiar código: splashbyte/animated_toggle_switch (BSD-3),
hadukin/custom_sliding_segmented_control (MIT), fathialamre/ticketcher y FazalHussain/Ticket-UI-Widget (MIT).
`product_navigation_test` y `live_parley_test` se actualizaron: ya no hay un botón por candado y las
reglas largas viven en la hoja.

## 2026-10-12 — Tapjoy: no mostrar HTML de errores en Coins

El puente reenviaba TJError.message y Flutter lo mostraba completo dentro del SnackBar: un fallo del SDK podía cubrir la pantalla con HTML. Ahora el canal solo transmite códigos estables y el código numérico del SDK; la app presenta avisos en es/en/pt/fr/it/de, permite reintentar y bloquea solicitudes duplicadas. Activity en connect, apertura en el hilo principal, éxito al mostrarse contenido y límite de 45 s. SDK 14.8.0 por mejoras oficiales de contenido web/interfaz, sin atribuirle una solución específica no documentada. 16 pruebas Flutter y análisis correctos, arnés final 977/24. Caché Pub incompleta restaurada. La apertura real sigue pendiente: BlueStacks no ofreció logs dentro del límite y hubo interacción concurrente del usuario. Detalle: apps/mobile/docs/TAPJOY_ERROR_HTML_20261012.md.

APK corregido release compilado, SDK/códigos verificados dentro del archivo y firma v2 coincidente con distribución vigente; entregable `.local/artifacts/QuantFut-ofertas-corregidas-20261012.apk` (74,1 MB). No instalado ni acreditada apertura real en la cuenta del usuario.

## 2026-10-12 — Entrenamiento xG terminado; candidato no activado

2026.10.12-221104 terminó a las 20:55:22 CDMX (13-oct, 02:55 UTC), tras
4 h 44 min 18 s: 49.504 partidos, 148 parejas nuevas xG y 13 competiciones.
Se ejecutaron todas las etapas, 12 ajustes históricos (una ventana mensual
sin test), ajuste final y puertas existentes. El candidato quedó registrado
inactivo: en los mismos 1.051 partidos, RPS DC 0,19873 frente a Elo 0,19657
y mercado 0,19147; log-loss 0,98694 / 0,98686 / 0,96547. Menor es mejor.
El veto es no superar Elo; champion de ventana distinta no comparable y la
puerta comercial sigue cerrada (clv_report de este pipeline n=0, mínimo 300;
no confundir con las capturas de otros informes sharp). Calibración aprobada
no anula el veto del modelo base. Modelo activo conservado 2026.09.27-010508.

La nueva fuente está incorporada en el artefacto candidato, no en el modelo
activo: carga con mezcla xG 0,65 y las 148 parejas disponibles en el corte
final 13-oct 02:32:16 UTC. Su backtest no acredita mejora retrospectiva por
xG capturado hoy. No se fuerza promoción ni se reinicia entrenamiento.

Resultado, fila model_artifacts y métricas cotejados. Recalculado el hash del
dataset desde training_input.pkl con la configuración registrada; fuentes
copiadas coinciden con el hash inicial. Diez artefactos comprobados y hashes
registrados; /model-card interno/público 200. Evidencia local completa en
.local/xg_api_20261012/training-2026.10.12-221104/: completion-audit.json,
artifact-verification.json y result.json/status.json/training.log exactos,
con hashes iguales al VPS. Actualizadas documentación y tareas.
Automatización resultado-del-entrenamiento-con-xg detenida (PAUSED) conforme
a la orden de avisar al finalizar; sin cambios de código ni puertas.

## 2026-10-12 — Tapjoy abierto en BlueStacks tras registro de prueba

La segunda captura conservaba el fallo de carga pese a ocultar el HTML. Registro Android: `no_currency`; Unity: moneda Monedas activa, Coins vinculada a esa moneda y coins_offerwall, SDK coincidente. Cuenta aún en revisión/app no activa sin tienda; cero dispositivos de prueba. Se registró BlueStacks QuantFut con permiso explícito para enviar su ID publicitario a Unity. Registro confirmado y apertura en la sesión actual verificada visualmente: Earn Rewards, Tapjoy Test CPA, 7 monedas. No se completó oferta ni se acreditaron monedas. La apertura de pruebas queda resuelta; aprobación/comercial y callback real siguen pendientes. Sin nuevos cambios de código o APK.

## 2026-10-12 — Coins rediseñado y aviso de monedas insuficientes

Pedido del titular (referencia: capturas de otra app de recompensas). Se adaptó la FORMA, no su
contenido: no hay cobro en dinero (las monedas no tienen valor monetario, dicen los términos), ni
marcadores «en vivo» de otros usuarios, ni «2×»/temporizadores inventados, ni juegos de terceros. La
cuenta atrás es real (reinicio de la asistencia a las 00:00 UTC).
`live_rewards.dart`: saldo con anillo de avance hacia el desbloqueo, asistencia de 7 días con el de hoy
resaltado y botón con las monedas de hoy, ofertas como UNA tarjeta del proveedor listo (Tapjoy) y los 5
sin activar en una línea «Próximamente» (antes 5 tarjetas muertas), invitación con código copiable,
historial con 5 movimientos y «Ver más», términos plegados y lluvia de monedas al reclamar
(`coin_burst.dart`, respeta «reducir animaciones»). Base oscura con acentos vivos (morado, dorado,
rosa), decisión recomendada y aprobada con «hazlo».
Bug corregido: la racha mostrada era el número guardado aunque se hubiera roto; ahora se calcula con la
fecha real UTC (`rewards_progress.dart`, misma regla que el servidor).
Cuando faltan monedas al desbloquear, el servidor responde 409 con `code: monedas_insuficientes` (antes
solo texto traducido) y la app ofrece «Ganar monedas» en vez de un error. Desplegado en la API con
respaldo `~/backups/coins-409-20261012` (vuelta atrás = imagen `pre-coins409-backup`); la app antigua
sigue funcionando (muestra el texto de siempre).
Tapjoy: según la documentación de Unity Grow, el SDK de Flutter solo muestra el placement entero
(`TJPlacement.requestContent/showContent`); no hay forma documentada de pintar las ofertas una a una en
la propia pantalla. Lo personalizable es la tarjeta de contenido del panel (moneda, icono, colores,
tasa), Message to Earn y los placements contextuales.

## 2026-10-12 — Inicio ya no enseña partidos terminados

Pedido del titular: un partido que acaba sale de la app y queda en los registros históricos. Se filtra en
el SERVIDOR (`visible_agenda` en `api/mobile.py`, solo la agenda de `/mobile/v1/home`) para que la app ya
instalada lo tenga sin actualizarse, y otra vez en la app (`calendar()`), por si llega una agenda sin
filtrar. Se quita todo `estado == 'finished'`; los de en juego y los por jugar siguen. La web y las demás
rutas de fichas no cambian. Medido en producción antes/después con `fecha=2026-10-12`: 41 partidos (25
terminados) → 16, todos por jugar. Consecuencia a vigilar: en un día pasado Inicio queda vacío, porque
todos sus partidos ya terminaron; los resultados siguen en los pronósticos liquidados y en las
estadísticas del partido. Desplegado con respaldo `~/backups/agenda-sin-terminados-20261012`
(vuelta atrás = imagen `pre-agenda-backup`).

## 2026-10-12 — Pestaña «Alertas» en el análisis del partido (fase 1, sin IA)

Pedido del titular (referencia: pestaña de alertas de otra app). Fase 1 decidida con él: datos REALES y
verificables, sin modelo de lenguaje. Se apoya en lo que ya existía: `ficha.bajas` (API-Football
`/injuries`, última comprobación, ver `fichas._bajas` e `ingest/injuries.py`). No se tocó el servidor.
`live_alerts.dart` + `alerts_model.dart`: por equipo, «Desventaja» = sus bajas y «Ventaja» = las del rival
(como en la referencia); tarjeta con iniciales, motivo traducido (se agrupa el texto en inglés del
proveedor y lo que no encaja se muestra TAL CUAL, nunca se inventa un motivo), estado No disponible /
Duda / Sancionado, fuente y hora de la comprobación. Selector de equipo con escudo, indicador que se
desliza, cambio por deslizamiento, entrada escalonada (respeta «reducir animaciones») y contador de
bajas en la pestaña. El estado va siempre en rojo/ámbar (hecho del jugador); solo el borde marca la
sección, para que «No disponible» no se lea como algo bueno en la sección de Ventaja.
Sin comprobación (`bajas` nulo) se dice que NO equivale a «sin lesionados»: hay ligas sin cobertura del
proveedor (Championship, Liga Profesional, Série B hoy; ver README) y para esas es dato ausente.
No hay foto del jugador (no se guarda ni se sirve). Pendiente, solo si el titular lo pide: fase 2 con IA
(resumen de prensa con citas, aparte de los datos oficiales) y retirar la lista de bajas duplicada de la
pestaña H2H.

## 2026-10-12 — «Datos del partido» en Análisis (la pestaña Estadísticas pasa a llamarse Análisis)

Pedido del titular: una tarjeta como la de la referencia, justo debajo de «Probabilidad de victoria 1X2»,
y la pestaña Estadísticas renombrada a Análisis. Solo datos comprobables: último resultado de cada equipo
(y el de la competición si es otro partido), ÚLTIMO once conocido con su fecha y rival (nunca un «once
probable»: lo dice la propia tarjeta), y el resumen de bajas con acceso a la pestaña Alertas. Lo que falta
se dice («Aún no hay una alineación guardada», «Sin partidos previos registrados»). Lo narrativo de la
referencia («perfil de la previa apunta a un juego abierto…») queda para la fase 2 con IA, si se aprueba.
Servidor: `fichas._ultimo_once` añade `ultimo_once` por equipo (último partido terminado con alineación,
de `lineups` o `lineups_historicas`); es un campo NUEVO, compatible con la web y la app anterior.
Verificado en producción: Lens 3-4-2-1 vs Lyon (9-oct) y Sporting CP 4-2-3-1 vs SC Braga, 11 titulares cada
uno. Desplegado con respaldo `~/backups/ultimo-once-20261012` (vuelta atrás = imagen `pre-once-backup`).
Decidido NO incluir el estadio: la base no guarda sede por partido (haría falta una columna nueva y
cambiar la captura del calendario). La cobertura del once depende de las alineaciones guardadas (desde
finales de septiembre más el histórico): un equipo sin ninguna lo muestra como ausente.

## 2026-10-12 — Pantalla de acceso rediseñada (carrusel + tarjeta con Google) y fuera la presentación posterior

Decisión: la pantalla de acceso pasa a ser un carrusel de 5 diapositivas con ilustraciones dibujadas en
código (no capturas reales: no envejecen ni prometen cifras) y una tarjeta fija abajo, a la altura del
pulgar, con el botón oficial de Google y el consentimiento (mayor de 18 + términos + privacidad) con los
enlaces dentro de la frase. El botón de Google ya no se apaga sin casilla: se deja pulsar, la casilla
vibra y se explica qué falta (un botón gris sin motivo es peor ergonomía). Los textos del carrusel no llevan
cifras ni promesas de resultado (solo lo que la app hace). Se retira la presentación `SecondScreen` que salía
tras el acceso: quien entra con Google va directo al producto (`onboarding_done` ya no se lee).
Código en `lib/core/access_screen.dart` (no conoce Firebase; la puerta de acceso le pasa estado y acciones) y
`lib/core/access_illustrations.dart`; dependencia nueva `flutter_svg` solo para la «G» de 4 colores. 20 textos
nuevos en los 6 idiomas. Por debajo de 700 px de alto la pantalla se desplaza en vez de apretar el texto.
Pruebas: `test/access_screen_test.dart` (14, incluye 6 idiomas a 390 y 320 px). Suite: 177 verdes. Sin cambios
de servidor ni despliegue.

## 2026-10-13 — Inicio rediseñado: agenda por día, boletos del día y menú «Más» con guía

Pedido del titular (capturas de QuantFut y de WIN Betting): quitar los atajos «Alta probabilidad / Reto
Escalera» y los filtros «+48 h, +1 h…» del Inicio, un calendario más visual y los partidos agrupados por día en
orden cronológico; del diseño de referencia, resumen, boletos y un menú con ventanas nuevas. Repos usados como
referencia de patrón (no como dependencia): `easy_date_timeline` (tira de días) y `sticky_grouped_list`
(encabezados por día con salto). Lo que NO se copia de la referencia: oferta con cuenta atrás, «1.000.000+
apostantes», «Seguro/Medio/Arriesgado» y el «84 % de acierto» fijo: serían cifras inventadas. El aviso superior es
el de Remote Config que ya existía (cerrable), no una oferta nueva.
Decisiones: (1) el servidor manda 7 días (`mobile.DIAS_AGENDA`, antes 2) y la app agrupa por día local; la app
anterior sigue funcionando (filtra por su cuenta). Desplegado con respaldo `~/backups/agenda7-20261013` (vuelta
atrás = imagen `quantfut-api-tapjoy:pre-agenda-backup`). (2) La tira de 7 días queda FIJA arriba y el día activo
sigue al desplazamiento; tocar un día salta a sus partidos y un día sin partidos avisa. Los encabezados de día no
son fijos: con una lista de hasta ~85 partidos por día, una tira fija es más útil que dos barras fijas. (3) Se
quitan Alta probabilidad y Reto Escalera del Inicio (viven en Predicciones; quedan como tarjetas de «Boletos del
día» con el pronóstico de mayor probabilidad y el parley). (4) Resumen con datos reales: saldo de monedas
(`/mobile/v1/rewards`) y acierto histórico real de Alta probabilidad; sin historial liquidado no se enseña la
tarjeta. (5) Menú «Más» (hoja inferior): guía de pronósticos (6 temas, sin promesas de ganancia), evaluar la app
(ficha de la tienda; no abrirá nada hasta que la app esté publicada), compartir (hoja del sistema; dependencia
`share_plus`) y términos/privacidad. El buscador pasa a un icono de la tira para ganar sitio.
Código: `home_agenda.dart` (agrupar, tira, fila de partido), `live_home.dart`, `live_more.dart`, `live_guide.dart`;
42 textos nuevos en 6 idiomas. Pruebas: `home_screen_test.dart` (19) y las de navegación/idiomas actualizadas;
suite 196 verdes. Lección: `dart format lib/product` reformateó archivos ajenos; se restauraron con `git checkout`
(formatear solo archivos propios).

## 2026-10-13 — El pronóstico se calcula cada día a las 03:00 de México (09:00 UTC)

Pedido del titular: el calendario se ve 7 días, pero un partido solo tiene probabilidad el mismo día en que se
calcula; antes la app enseña el partido con candado y la hora. Hora elegida por el titular tras comparar
(03:00 / 04:00 / 05:00 / 07:00 MX): las 03:00 cubren casi todos los kickoffs europeos de mediodía el mismo día
(Serie A 12:30 CEST = 04:30 MX, Premier 12:30 BST = 05:30 MX), con los datos del día ya capturados (calendario
05:15 UTC, clasificación 06:40, resultados 06:45, lesiones 08:00) y ~3 h de margen para arreglar un fallo antes
de que se despierten los usuarios de México. Coste: el precio de mercado usado tiene 2 h más que a las 05:00.
Regla (`src/qf/publish/ventana.py`): un partido pertenece a la corrida de las 03:00 de su día de México; si
empieza antes de las 03:00 + 60 min (sin tiempo para sellar) pertenece a la del día anterior. México es UTC-6 fijo
(sin horario de verano desde 2022). Mismo corte en TODOS los generadores —`daily` (predicciones y «solo sharp»),
alta probabilidad, alta ext., escalera y parley—, siempre con tope en su horizonte propio: la ventana solo se
recorta, nunca se amplía. El servidor añade `pronostico_desde` (UTC) a cada partido de la agenda; la app pinta el
candado solo si no hay probabilidad y esa hora aún no llegó (si ya pasó y sigue sin dato, no finge un candado: son
ligas sin modelo). La hora de México que enseña la app sale de ese dato (UTC-6), no de una constante propia.
NO se cambió el orden predecir → seleccionar → sellar → publicar ni ningún trigger. Aviso de transición: la corrida
de las 13:00 UTC de hoy ya usó la ventana antigua de 36 h; desde mañana 09:00 UTC rige la nueva. `prediction_batches`
sigue indexado por fecha UTC (09:00 UTC es el mismo día UTC que antes).
Corrección de lo dicho antes al titular: el xG de API-Football solo alimenta el entrenamiento y el modelo no usa
lesiones, así que NO hacía falta mover esas capturas (se dejaron como estaban, incluida la del xG de otra sesión).
Desplegado en api y worker con respaldo `~/backups/ventana-20261013` (vuelta atrás = imágenes `pre-ventana-backup`
de `quantfut-worker` y `quantfut-api-tapjoy`, y el crontab respaldado). Pruebas: `tests/test_ventana_pronostico.py`
(13) + suite Python completa (972) y Flutter (197).

## 2026-10-13 — Integración xG y resultado preparados para commit

Comprobación actual antes de guardar esta integración: 994 pruebas aprobadas,
24 omitidas y 2 advertencias. El commit incluye la captura de la primera pareja,
protección temporal, migración, pruebas y resultado del candidato rechazado.
Se conservan sin incluir los cambios concurrentes de Tapjoy y de la app.

## 2026-10-13 — Cambios pendientes de Tapjoy preparados para commit

Orden del titular: guardar los cambios restantes. Puente Android con códigos
seguros (sin HTML del SDK), exclusión de aperturas simultáneas, espera de 45 s
y SDK 14.8.0; documentación del diagnóstico y apertura de prueba conservada.
La apertura de pruebas ya está confirmada, pero aprobación y acreditación
comercial siguen pendientes. Comprobación actual: 16 pruebas Flutter aprobadas
y :app:compileReleaseKotlin correcto. Se restauraron las cachés Pub/Maven que
faltaban, con pub get --enforce-lockfile; pubspec y lock permanecen iguales.
Se excluyen .venv-api, caché Kotlin y build Android; el informe HTML generado
sale del índice, conservado en disco. No se instala APK ni se modifican claves.

## 2026-10-13 — Un pronóstico gratis abre también los marcadores más probables del partido

Pedido del titular (captura del detalle de Lens–Sporting): un pronóstico gratis debe ir completo. Hoy la fila del
pronóstico, su dictamen y su cuota ya iban abiertos; lo único suyo que seguía con candado eran los «marcadores más
probables». Alcance elegido por el titular: SOLO el pronóstico gratis completo; los demás mercados del partido
(Resultado, Doble oportunidad…) siguen siendo VIP, que es el contenido de pago. Cambio solo de servidor
(`partido_mercados.aplicar_acceso`): hay marcadores si el usuario es VIP o si tiene algún pronóstico abierto del
partido (gratis o desbloqueado con monedas). Revierte la regla anterior «marcadores solo con VIP» (la prueba
`test_locked_rows_reveal...` la fijaba y se actualizó; nueva prueba: sin pronóstico abierto ni VIP no hay marcadores).
Verificado en producción: partidos con pronóstico abierto devuelven 5 marcadores sin ser VIP. Desplegado con respaldo
`~/backups/marcadores-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-marcadores-backup`). No hace falta
APK nuevo: la app ya dibuja los marcadores cuando llegan.

## 2026-10-13 — Parley: un único parley del día no es gratis

La app mostraba todos los parlays porque el reparto gratis/VIP (`api/parley_acceso.py`) solo existía en local: el VPS sigue con `/parley` público sin filtro (comprobado: el contenedor de la API no trae `parley_acceso.py`). Decisión del usuario: un parley gratis por día y, si el día trae uno solo, ninguno gratis (con uno solo no hay "resto" que vender; el liquidado se sigue viendo siempre). Regla en `aplicar_acceso`: `gratis = None` si `len(tickets) <= 1`. Desplegado en el VPS (api) con respaldo `~/backups/parley-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-parley-backup` en el compose + `up -d --no-deps api`). Imagen nueva = la anterior + `main.py` y `parley_acceso.py`; el `main.py` del contenedor difería del local solo en `/parley`. Verificado en producción sin cuenta: hoy 1 parley abierto (escalón 1, gratis) y 4 bloqueados. Sin APK nuevo.

## 2026-10-13 — Cobertura fútbol: archivo disponible y ZenRows comprobado

El usuario pidió viabilidad de xG, XI, bajas y estadísticas para 12 ligas sin
modelo y huecos de las 13 habilitadas. Se comprobó la base actual (interruptores
false y conteos citados), pero el dato pendiente está en buena parte archivado:
FotMob 2024-01-01 a 2026-10-03, 22.461 filas, 22.456 originales verificados.
Hashes y normalizador cotejados: 3 originales faltantes Championship y 2 fechas
inconsistentes Brasil A excluidos. Las 12 ligas tienen 7.701 parejas xG,
10.524 partidos con ambos XI válidos y 10.466 con estadísticas de ambos equipos.
Campos de bajas presentes en 6.013 partidos; no se acredita exhaustividad ni
publicación previa al kickoff. Chile 662 resultados/XI, sin xG; Brasil B 1.066
resultados/XI y 686 xG. Copas: 425 UCL/441 UEL con xG, XI y estadísticas.
Argentina/MX/Primeira también tienen bajas declaradas en el archivo, pese al
vacío de API-Football. No se mezclan universos ni se atribuyen eventos nuevos
antes de emparejar con las identidades existentes.

Prueba SofaScore por cuenta ZenRows existente: cuatro GET correctos, reserva
100, incremento observado 20 créditos (1804→1824). Southampton-Portsmouth,
16391229, Championship/18: xG 1,28/1,18; 22 titulares, 40 fichas/29 jugadores
con minutos positivos, 6 bajas visitantes. Recibos y hashes verificados. Un
primer arranque MCP falló antes de consultar; segundo correcto. Repo fijado
dd9f061be2c64f01a6d3a50fb34d55a102d7107b: PolyForm Noncommercial real comprobada
por API ref fijo, pese a raw main en caché que daba MIT; piloto con adaptador
propio, sin integrar ese código restringido. No se declara qué IP usó el servicio.

Decisión: reutilizar primero el archivo existente; completar con consultas
acotadas tras medir cobertura por liga. Próxima integración necesita matching
estricto y extender la protección xG (hoy explícita para api_football) a las
nuevas fuentes; disponibilidad real del 3-oct no acredita datos en backtests
anteriores. Más datos no equivalen a superar Elo. Cero importaciones, compras,
API-Football/Odds API nuevas, cambios de flags, cron o modelo. Arnés antes:
995/24; después: 996/24, dos advertencias. Informe:
docs/futbol_scraping_viabilidad_20261013.md. Evidencia:
.local/football_scraper_20261013/; originales antiguos intactos.

## 2026-10-13 — Detalle del partido sin modelo de goles: los VIP se avisan aparte del gratuito

En partidos de ligas sin modelo propio (p. ej. Championship) `ficha.mercados` salía `None` (`partido_mercados.construir` exige lambdas de goles; el `fit` de un pronóstico de córners solo trae lambdas de córners) y la pestaña Pronósticos mostraba el banner «tiene un pronóstico VIP» sin nada que lo respaldara debajo. Solución provisional hasta que exista modelo: `partido_mercados.solo_candados` devuelve candados SOLO con la categoría de cada pronóstico VIP real del partido (sin línea, selección, probabilidad ni cuota), con `sin_modelo: true` y sin marcadores; la app oculta el bloque «Marcadores más probables» en ese caso para no prometer lo que ni un VIP vería. Con VIP no cambia nada. Pruebas: `test_partido_mercados`, `test_mobile_delivery` y `match_markets_sin_modelo_test.dart`. Servidor desplegado (api) con respaldo `~/backups/sin-modelo-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-sinmodelo-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py` y `partido_mercados.py`, que coincidían con el commit). Verificado en producción: Bristol City–Blackburn devuelve 2 candados (Doble oportunidad, Córners) con `sin_modelo`; partidos con modelo de goles no cambian. APK compilado (`flutter build apk --release`, 76,0 MB, 13-oct 13:50, SHA256 75635A883E24385FAE2D24E163780BC4D2EAE56538CFCA77FB6CF44B521DB64E): `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`. No se verificó la firma con apksigner (no está en el equipo); el release exige `key.properties`. No se instaló en ningún dispositivo ni se publicó.

## 2026-10-13 — Detalle y cabecera de la app: sin banner VIP con pronóstico abierto, sin botón de estadísticas, monedas en la cabecera

Pedido del titular (capturas de Bristol City–Blackburn): (1) el banner «Este partido tiene un pronóstico VIP» solo sale si el partido NO tiene ningún pronóstico abierto (gratis o desbloqueado): los demás VIP ya van con candado en «Mercados del partido»; (2) se quita de la tarjeta del pronóstico el botón azul «Ver estadísticas del partido» (la clave `forecastSeeStats` queda sin uso en los 6 idiomas; se dejó para no tocar traducciones, Análisis sigue en su pestaña); (3) la cabecera fija lleva una moneda en miniatura (`Icons.toll`, la misma de la pestaña Coins) con el saldo DISPONIBLE (`wallet.spendable`, nunca negativo), «—» sin cuenta; al tocarla abre Coins. Se refresca al recargar y al salir de la pestaña Coins. No hay imagen propia: el repo no tiene activos de imagen; si se quiere un logo/ilustración hace falta el archivo. Solo cambia la app, sin textos nuevos. Pruebas: `product_navigation_test` (nuevas: saldo en cabecera, sin cuenta, banner/botón ausentes); suite Flutter 201 OK y analyze limpio. APK nuevo (76,0 MB, 13-oct 14:10, SHA256 4CDBF3D998392604C60E534BB8009138B09092F07B97997E8713AEA4A5367E45) en `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`, sin instalar ni publicar.


## 2026-10-13 — Histórico FotMob importado en PostgreSQL

El usuario autorizó transferir e importar los originales en quantfut y confirmó
el importador/migración/protección temporal. Carga atómica completada 20:06 UTC:
22.456 originales, 44.912 XI de equipo, 940.386 registros de estadísticas y
48.571 declaraciones de bajas históricas. 20.502 asociaciones existentes,
1.554 partidos nuevos y once clubes domésticos nuevos; 400 originales conservan
asociación pendiente/conflicto (379 identidades de copas, 21 discrepancias).

Se rellenan 14.629 parejas xG vacías con recepción real del 3-oct y 8.537
partidos en conteos ausentes; no se toca xG previo. Control temporal de todas
las fuentes observadas y replay Kalman sin anticipar xG. IDs por proveedor,
originales/recibos congelados, datos históricos separados de capturas PIT;
los consumidores de jugadores/XI/bajas requieren adaptación posterior.

Prueba PostgreSQL con 53 encuentros, segunda carga cero escrituras y reversión
confirmada; arnés 1.007 aprobadas/24 omitidas. Se cotejan 20.816 partidos previos,
25 originales releídos por hash y las 14.629 parejas contra cortes temporales.
Ligas, puertas, lotes sellados, XI/jugadores previos y modelo 2026.09.27-010508
conservados; API interna/pública 200 y versión coincidente. La captura habitual
injuries de las 20:00 añadió 324 filas durante la carga; se corroboró su cron y
recepción, sin modificar esa tabla/tarea desde el importador. Sin entrenamiento
nuevo, publicación o mensajes manuales externos.

Evidencia .local/fotmob_import_20261013/verified/ y volumen
/srv/quantfut/artifacts/imports/fotmob-20261013/; backup de partidos y worker.
Detalle/cobertura: docs/importacion_fotmob_20261013.md. El xG nuevo no demuestra
una mejora retroactiva; Chile continúa sin xG en el archivo.

## 2026-10-13 — soccerdata con ZenRows e importación adicional verificada

El usuario detuvo el scraper anterior y lo sustituyó por soccerdata y su
documentación. Se confirmó cero procesos anteriores activos. soccerdata 1.9.1
fijado en e120471e424a173e83e8aeeaaf4d954ab9d38ee4, Apache-2.0; instalación
aislada optativa. Transporte MCP ZenRows 2.4.0 con proxies automáticos, recibos,
hashes, reserva 100 y caché que conserva fallos sin bucles. Los calendarios que
habían fallado con otra configuración se probaron una vez con GB, recuperando
Chile/LaLiga 2/Ligue 2/Serie B. Se reutilizan respuestas antiguas verificadas.

El lector SofaScore se amplía para detalles; FBref ya retiró datos avanzados y
el listado obtenido no sirvió para ligas domésticas. ESPN Chile/Brasil B falló.
Muestra 2023/24: eventos sin xG anunciado en LaLiga 2, Serie B y Ligue 2; las
estadísticas consultadas en España/Francia no traían esa métrica y las demás
consultas no acreditaron cobertura. No prometer historia completa por aceptar
un calendario ni atribuir una mejora de backtest al xG recibido ahora.

Carga adicional completada 23:15 UTC: 586 originales, 574 asociaciones,
54 parejas xG añadidas a huecos, 138 XI, 2.789 registros de jugadores y 269
bajas históricas. Cero partidos/clubes nuevos: la propuesta Troyes–Valenciennes
1–1 fue puesta en cuarentena tras cotejar la derrota administrativa en LFP.
Otro marcador discrepante y diez identidades de copas quedan separados. Doce
equivalencias domésticas revisadas con nombres, país y partidos; sin difuso.

Prueba PostgreSQL de carga repetida dentro de transacción revertida: cero
escrituras adicionales y reversión corroborada. Carga real coteja 22.615 registros
previos, 586 hashes y 54 disponibilidades temporales. Se conservan modelo
2026.09.27-010508, flags, lotes sellados y tablas de jugadores/XI API-Football;
model-card interna/pública 200 y misma versión. Worker respaldado y ampliación
persistida sin reiniciar ni reconstruir desde el checkout viejo. Arnés final:
1.033 aprobadas/24 omitidas, 35 relevantes. Sin entrenamiento, compras o mensajes
externos. ZenRows 2.515→3.751 utilizados; quedan 1.249 en última lectura.

Persisten 3.154 partidos sin xG y bloqueos de calendario en cinco competiciones;
los consumidores de XI/jugadores/bajas históricos siguen pendientes. Evidencia
.local/soccerdata_completion_20261013/verified/ y artifacts/imports/soccerdata-20261013
del worker. Detalle y desglose: docs/soccerdata_zenrows_20261013.md.

## 2026-10-13 — Los pronósticos bloqueados enseñan su cuota

Pedido del titular (lista «143 pronósticos más con VIP»): que cada bloqueado muestre la cuota para que sea atractivo. `mobile.metadata()` añade `cuota` (cuota publicada: `ref_price` en alta probabilidad, `price` en la escalera; `None` si no es válida, nunca inventada). Sigue SIN salir selección, línea ni probabilidad (el test lo comprueba). Efecto a tener en cuenta: cuota + categoría permite estimar la probabilidad (~1/cuota), así que la leyenda «Con VIP ves la probabilidad, la cuota y el análisis» pasó a «…la selección, la probabilidad y el análisis» (6 idiomas, `picksLockedHint`). App: la fila bloqueada de `LockedPicksGroup` dibuja `@cuota` en dorado. Los candados por categoría del detalle del partido (`solo_candados`) no llevan cuota. Servidor desplegado (api) con respaldo `~/backups/cuota-bloqueados-20261013` (vuelta atrás = imagen `quantfut-api-tapjoy:pre-cuota-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py`, que coincidía con el commit anterior). Medido en producción: de los 143 bloqueados de partidos no empezados, 61 llevan cuota y 82 NO (hándicap 60 y doble oportunidad 22: `alta_prob_picks.ref_price` es NULL, no hay precio publicado de casa para esos mercados; no se inventa con 1/prob). PENDIENTE: APK; sin APK nuevo la cuota viaja pero no se ve, y la leyenda vieja sigue diciendo que la cuota es de VIP. Pruebas: Python 1032 OK, Flutter 201 OK, analyze limpio.

## 2026-10-13 — Parley: cada pata de cuota 1,20 a 1,80 (sin desplegar)

Pedido del titular, tras una primera lectura equivocada mía (que cambió la cuota TOTAL; se revirtió entera): la cuota total de cada parlay sigue en los 5 escalones de 1,90 a 5,00; lo que cambia es que CADA PATA tenga cuota de 1,20 a 1,80 (antes: >= 1,15 sin techo), con la combinación más probable de cada escalón y las patas que hagan falta (2 a 6). `parley.CUOTA_MIN_PATA, CUOTA_MAX_PATA = 1.20, 1.80` en `filtrar`; el informe público añade `reglas.cuota_max_pata`. Sin cambio de esquema, escalones ni historial (el control sigue comparando probabilidad prometida y acierto, mismo significado). Simulación con datos reales (17 partidos con precio, dry-run en el worker, sin escribir): la probabilidad de cada parlay casi NO cambia (52/46/37/28/22 % frente a 52/45/37/30/23 %), porque la fija la cuota total y mas patas la bajan; el efecto es que desaparecen las patas largas (1X2 a 2,16 con 48 %, córners a 2,00 con 51 %) y toda pata queda entre 56 % y 82 %. Rige desde el primer sellado tras desplegar el worker (el del 14-oct 09:00 UTC si se despliega antes). Pruebas: `test_parley` (rango de pata incluidos bordes y float4, ningún parlay con pata fuera de rango), suite Python OK. PENDIENTE: desplegar worker (parley.py, parley_datos.py) y api (parley_datos.py: informe) antes de ese sellado.

Decisión del titular sobre mercados (2026-10-13): el parley NO busca en todos los mercados, solo en los de líneas validadas (1X2, doble oportunidad, goles 1,5/2,5/3,5, goles por equipo, ambos marcan sí, hándicap, córners y tarjetas habilitados) y elige por probabilidad calculada, no por acierto real. Ponderar por acierto real por mercado se pospone hasta tener ~50 liquidados por mercado (hoy 5-41): anotado en `harness/tareas.md` (Parley, punto 11) y en el README.

## 2026-10-13 — Recuperación adicional con clave nueva de ZenRows

Se priorizó el modo automático de la CLI oficial 1.5.0, sin imponer país ni
funciones caras a todas las llamadas; tres conexiones frente al límite verificado
de cinco. Presupuesto compartido con reserva previa de 25 por solicitud, devolución
solo del coste comunicado y parada ante autenticación/cuota agotada. MCP 2.4.0
lee cuota y acepta la clave de la tarea solo en el entorno; configuración y cuenta
compartidas anteriores conservadas. Clave nueva cifrada DPAPI fuera de Git y VPS.

La ruta pública www de SofaScore recuperó calendarios antes bloqueados en Brasil B,
Bundesliga 2, Dinamarca, Suecia y Europa League. Parser real de soccerdata 1.9.1;
fallos conservados, jornadas danesas procesadas independientemente. No repetir
fallos ni confundir tiros sin xG con xG publicado: las muestras históricas de
España/Francia carecían de ese campo. Recuperar jornadas actuales no demuestra
acceso a toda la historia. Se excluyen los 586 IDs SofaScore ya congelados.

Carga confirmada 14-oct 00:55 UTC (13-oct 18:55 México): 125 originales, 101
asociaciones, 36 parejas xG canónicas añadidas, 228 XI, 4.137 registros de jugadores
y 294 bajas históricas. De 97 xG originales, once no tienen asociación y cincuenta
conservan valores canónicos anteriores. Cero partidos/clubes nuevos; 24 originales
europeos sin identidad canónica conservados. Seis equivalencias danesas revisadas
con país/nombres y dos fixtures independientes cada una; AGF doméstico resuelve
también su encuentro europeo. Sin difuso ni altas bajo copas.

Dos cargas en transacción revertida: segunda cero escrituras y conteos restaurados.
Carga real verifica 125 normalizaciones y cuerpos HTTP/hash/recepción; conserva
22.632 partidos previos y 23.042 originales anteriores con identidad/hash/reloj.
Las 36 parejas xG respetan cortes temporales. Modelo 2026.09.27-010508, flags,
lotes sellados y tablas antiguas XI/jugadores conservados; API interna/pública
200 y misma versión. Sin código nuevo en worker ni reinicio, entrenamiento,
compras, activación de ligas o mensajes externos manuales.

Saldo nuevo verificado: 988 utilizados de 5.000, 4.012 restantes y cero concurrencia
activa. Descarga principal 233 llamadas CLI y complemento danés 26; pruebas previas
incluidas en consumo total. Arnés final 1.045 aprobadas/24 omitidas. Huecos xG
3.154→3.118; Bundesliga 2 queda sin huecos en el corte desde 2024, Brasil B aún384,
Dinamarca3 y Suecia2. Consumo medido por cuenta, sin inferir fallos gratuitos;
RESP008 puede cobrarse. Evidencia .local/zenrows_key_20261013/prepared/ y verified/,
worker artifacts/imports/zenrows-new-key-20261013/. Detalle y pendientes en
docs/zenrows_clave_nueva_futbol_20261013.md; adaptación de consumidores históricos
y mejoras del modelo siguen sujetas a validación, sin mejora retroactiva atribuible.

## 2026-10-13 — Eliminación física de Chile y Brasil B

El titular pidió retirarlas por completo y autorizó expresamente borrar su
historial protegido tras revisar cuotas, alta probabilidad, escalera y parley.
Se comprobó que sus clubes domésticos no intervenían en otras competiciones.
Se eliminan 1.806 partidos, 1.784 originales históricos, 36 clubes, 49 alias,
36 clasificaciones, 81.082 cuotas, 3.518 XI, 73.414 registros de jugadores y
465 bajas, junto con selecciones y resultados relacionados. Para evitar
productos incompletos se retiran dos retos enteros (seis pasos) y un parley
entero (tres patas), incluidas las partes de otras ligas dentro de esos grupos.

Respaldo selectivo: 25 COPY binarios, 45.427.123 bytes, con hashes cotejados
localmente. Bloqueos exclusivos y excepción temporal de triggers solo en
tablas seleccionadas, restaurados antes del commit. Prueba PostgreSQL real:
primera eliminación, repetición cero escrituras y reversión; eliminación real
con los mismos conteos. Conteos y huellas de filas ajenas a la selección en
40 tablas conservados, modelo 2026.09.27-010508 y Série A intactos. Los 15
lotes originales en disco conservan su cadena; no se reescriben. Su contenido
retirado ya no se regenera desde la base operativa. Comparaciones de acierto
posteriores deben explicar el cambio de población, sin atribuirlo a una mejora.

db/063 registra únicamente metadatos de retiro y bloquea reinserción en
catálogo/partidos. FotMob y SofaScore quedan en 23 competiciones; normalización,
emparejamiento/importación y manifests viejos no reintroducen las dos retiradas.
Fuentes exactas cotejadas y desplegadas sin reconstruir checkout viejo ni
reiniciar. Worker respaldado y cambios persistidos en imagen. API interna y
pública 200, catálogo23 y home móvil sin IDs retirados; cero ligas/partidos/
originales/clubes de ambas. Arnés 1.049/24. Sin entrenamiento ni llamadas nuevas
a proveedores deportivos; comprobado cero procesos entrenadores al terminar.

Quedan 13 competiciones con modelo habilitado y diez pendientes; huecos xG
desde2024: 3.118→2.073 por retirar ligas, no por recuperar valores. Los datos
recién importados aún no participaron en un nuevo modelo activado. Evidencia
.local/remove_chile_brasil_b_20261013/verified/ y artifacts/maintenance/
remove-chile-brasil-b-20261013 del worker; 45MB de respaldo también en host.
Detalle: docs/eliminacion_chile_brasil_b_20261013.md. Informes de cobertura
actuales actualizados; archivos previos y sellados conservados como evidencia.
