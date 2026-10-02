# Registro de decisiones — QuantFut

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
