# Registro de decisiones â€” QuantFut

## 2026-11-06 Â· Parley v2.1: tope por mercado, cuatro targets a la vez y Â«solo referenciaÂ» sin calibraciÃ³n

El usuario pidiÃ³ un selector de parleys por targets (2.10, 3.10, 8.20, 12.10), mÃ­nimo de patas y sin +EV. Lo que
decide el diseÃ±o no es el prompt sino lo medido (`docs/parley_topes_medicion_20261106.md`): a cuota total fija
la probabilidad conjunta es casi la misma con 3 o 4 patas (P â‰ˆ (1 âˆ’ margen) / cuota), asÃ­ que menos patas compra
cobertura y menos margen acumulado, no acierto; el salto Ãºtil es de tope 2.0 a 2.5 y 3.0 aÃ±ade poco, mientras
que por encima de 2.1 los goles y los props de jugador se calibran peor y cuestan 3-4 puntos mÃ¡s por pata. Por eso
2.50 solo para ganador, 2.10 para lÃ­neas, 1.80 para lo no medido y el 1T 1X2 fuera (margen 9-11 %). Los cuatro
tickets se resuelven a la vez: con el orden secuencial, el 12.10 se quedaba con lo que dejaban los demÃ¡s.

`publicado` exige probabilidad calibrada con incertidumbre en cada pata; sin artefacto de calibraciÃ³n (fase 2) todo
sale `solo_referencia`, y un same-game solo es ejecutable con cuota real del paquete y modelo conjunto (la
correlaciÃ³n medida llega a 1,45-1,59 sobre el producto de marginales). El mÃ³dulo no estÃ¡ enganchado al sellado:
el lote propio de las 03:35 invierte predecir â†’ seleccionar â†’ sellar y exige confirmaciÃ³n expresa. Lecciones: la
prueba contra bÃºsqueda exhaustiva cazÃ³ un fallo real (dos opciones de un mismo conjunto de eventos se pisaban
al deduplicar), y el BOM de football-data dejaba sin id al 19 % de los partidos, lo que subestimÃ³ la cobertura del
fÃºtbol en la primera mediciÃ³n (corregido y documentado).

Mismo dÃ­a, a pedido del usuario: Pinnacle deja de ser obligatorio para la probabilidad de referencia en todos los
deportes y mercados del parley. `publish/referencia.py` usa el consenso de las casas que cotizan el contrato
completo (Pinnacle conserva su peso si cotiza; mÃ­nimo 2 casas). Se aplicÃ³ a tenis/NBA (`parley_ext.py`) y al
fÃºtbol mediante un parÃ¡metro `consenso` que solo activa `PARLEY_STRATEGY_VERSION=v2`, para no mover alta
probabilidad, escalera ni el parley legado, cuyos controles se midieron con Pinnacle. El efecto sobre las
probabilidades sin Pinnacle no estÃ¡ medido todavÃ­a: va antes de activar v2.

DespuÃ©s, a pedido de Â«termina los pendientesÂ»: fase 2 (calibraciÃ³n y backtest), fase 3 (lote propio con cadena de hashes, barrera
y reintentos, apagado) y fase 4 (parley NBA por partido, lÃ³gica pura). La decisiÃ³n clave de la fase 2 es negativa: en fÃºtbol y tenis
el mercado sin margen ya estÃ¡ calibrado, Platt e isotÃ³nica no lo mejoran con claridad y por eso B1/B2 no se promueven; lo que
sÃ­ aporta el artefacto es la abstenciÃ³n (NBA se abstuvo en las categorÃ­as de cuota alta de props) y la incertidumbre por pata. La
fase 3 se diseÃ±Ã³ para NO tocar `seal()` ni el cron diario: cadena propia que guarda el hash del lote diario como prueba de
orden, y todo apagado hasta confirmar. Un fallo real saliÃ³ del cierre: dos jugadores con el mismo prop y lÃ­nea se fundÃ­an en un
contrato al consolidar; el jugador ahora forma parte de la clave de la pata.

Cierre de pendientes: liquidaciÃ³n de patas v2 (fÃºtbol, tenis, NBA) y orquestaciÃ³n del parley NBA por partido. La prueba de la
liquidaciÃ³n destapÃ³ otro fallo: el id de evento de fÃºtbol (`liga:temporada:equipos:fecha`) se cortaba en el primer `:` al sellar,
lo que habrÃ­a impedido unir la pata con `matches`; ahora fÃºtbol conserva el `match_id` completo y tenis/NBA quitan su prefijo.
Lo que queda no es cÃ³digo: aprobaciÃ³n del artefacto, aplicar la migraciÃ³n 098, desplegar, el sellado diario NBA v1.3 con su
revisor y la disponibilidad en vivo.

## 2026-10-25 â€” Destacado del detalle: cuota mÃ­nima 1,40

## 5-nov-2026 (noche) Â· CalibraciÃ³n del destacado de fÃºtbol por mercado y banda; quÃ© regla cumple el 80 %

MediciÃ³n con 390 partidos terminados que tenÃ­an predicciÃ³n previa al saque (base local `entreno`, copia de producciÃ³n al 25-oct; del 27-sep al 25-oct), reconstruyendo las filas de la lista web (goles, equipo, hÃ¡ndicap, doble oportunidad, empate no acciÃ³n, 1Âª mitad, cÃ³rners y tarjetas) y liquidÃ¡ndolas con el resultado real (los empates devueltos no cuentan). 97 de esos partidos tienen cuota de casa (PropLine, desde el 23-oct). NBA y tenis NO se calibraron aquÃ­ (pendiente).

- **Valor esperado con cuota de casa** (cuota â‰¥ 1,20, prob â‰¥ 55 %, mayor prob Ã— cuota): **56,5 % de acierto** (n = 85, IC95 46â€“66 %), cuota media 1,80; con cuota del modelo es idÃ©ntico a la regla nueva. La cifra Â«31 %Â» del encargo no se pudo reproducir con este historial (su muestra viva fueron pocas horas).
- **Regla desplegada (â‰¥ 75 %, mayor prob., cuota â‰¥ 1,20):** 80,1 % (IC95 75,8â€“83,7 %, n = 386) con cuota del modelo y 78,0 % (IC95 68,5â€“85,3 %, n = 91) con cuota de casa; cuota media 1,23 / 1,29. EstÃ¡ calibrada (probabilidad predicha media 81,6 %), pero el techo de 83,3 % que impone la cuota â‰¥ 1,20 deja el 80 % justo en el borde: no lo garantiza.
- **La cuota mÃ­nima manda mÃ¡s que cualquier lista de mercados:** con â‰¥ 1,15 el acierto medido es 84,8 % (IC95 80,9â€“88,1 %, cuota media 1,18) y 83,2 % con casas; con â‰¥ 1,10, 84,9 % (cuota 1,14) y 85,6 % con casas. El 80 % se cumple con holgura bajando el mÃ­nimo de 1,20 a 1,15 (a costa de ~4 % de pago). Las casas pagan MENOS que la cuota justa en estas selecciones (media 1,205 frente a 1,233 justa; la mitad de los candidatos de â‰¥ 75 % paga < 1,20): Â«80 % de aciertoÂ» y Â«cuota competitivaÂ» chocan por construcciÃ³n (80 % â‰ˆ cuota justa 1,25).
- **Por mercado (franja 75â€“83,3 %, toda la muestra):** calibrados dentro del error: goles de equipo 79,1 %, hÃ¡ndicap 78,8 %, tarjetas 78,7 %, cÃ³rners 78,2 %, goles 77,4 %, 1Âª mitad 76,3 %, doble oportunidad 75,8 %, empate no acciÃ³n 82,2 % (n = 45). Por selecciÃ³n, los Â«menos deÂ»/Â«noÂ» estÃ¡n sobreestimados (totals:under âˆ’6,1 pts, ht_btts:no âˆ’6,1, team_totals_away:under âˆ’8,7; la lÃ­nea 3,5: 70,9 % real contra 78,9 % predicho) y los Â«mÃ¡s deÂ» subestimados (+2 a +7): el modelo subestima los goles de este periodo.
- **Lo que NO funcionÃ³ fuera de muestra:** listas blancas, probabilidad corregida por la brecha de su clave y excluir under/no. Las claves Â«segurasÂ» cambian de un tramo a otro (ruido con n de 25â€“100), y excluir under/no mejora con cuota del modelo (+3 pts) pero empeora con casas (âˆ’3 pts). No se aÃ±adiÃ³ ninguna lista de mercados.
- **RecomendaciÃ³n:** bajar `CUOTA_MIN` a 1,15 (constante en `destacado_valor.py`, su copia de NBA y `featured_rule.dart` / `bestBySafety` de web y app) si el 80 % es el objetivo duro; el siguiente paso de fondo es recalibrar el modelo de goles (under/no sobreestimados), no filtrar mercados.

## 5-nov-2026 (tarde) Â· Destacado: de valor esperado a Â«probabilidad mÃ¡xima seguraÂ»

DecisiÃ³n del titular, horas despuÃ©s de desplegar el valor esperado (PR #262): el destacado es un producto de retenciÃ³n, no de ROI; el objetivo es que el usuario vea >= 80 % de aciertos. Regla vigente en fÃºtbol, NBA, tenis, web y app: candidato = cuota de referencia >= 1,20 y probabilidad >= 75 %; gana la MAYOR probabilidad (la cuota ya no multiplica nada y `score_destacado` desaparece); empate -> mayor cuota; sin candidatos -> `null`. Sin cuota de casa la de referencia es 1 Ã· prob., asÃ­ que el destacado sale de la franja 75 %-83,3 %. Se conserva la regla de que, con cuotas de casa en el partido, solo compiten los mercados que una casa cotiza, y que el destacado es siempre uno de los 3 mercados gratis de la web.

AmbigÃ¼edad del encargo resuelta: el punto 1 pedÃ­a cuota >= 1,20 y el punto 4 decÃ­a Â«pagando 1.10Â»; se aplicÃ³ 1,20 (aparece dos veces y el propio encargo habla del tope de 83,3 %). Si se querÃ­a 1,10, el tope de la franja sube a 90,9 % sin cuota de casa: es un cambio de una constante (`CUOTA_MIN`).

QuÃ© NO estÃ¡ demostrado: la cifra Â«31 % de acierto empÃ­ricoÂ» del valor esperado y que la nueva regla llegue a 80 % se citaron sin mediciÃ³n propia. Un destacado sale de una franja estrecha (75 %-83,3 %), asÃ­ que 80 % real exige un modelo calibrado justo ahÃ­; la calibraciÃ³n por mercado e historial se mide aparte (ver la entrada de calibraciÃ³n).

## 5-nov-2026 Â· PronÃ³stico destacado por valor esperado en fÃºtbol, NBA y tenis (servidor)

DecisiÃ³n del titular: el destacado deja de ser Â«la mayor probabilidad con cuota â‰¥ 1,40Â» y pasa a ser el mercado de mayor `probabilidad Ã— cuota de referencia` entre los que tienen cuota â‰¥ 1,20 y probabilidad â‰¥ 55 %; empate por mayor probabilidad; sin candidatos, `null`. Lo implementa `src/qf/api/destacado_valor.py` (puro, sin dependencias), usado por `partido_mercados.aplicar_acceso_web` (fÃºtbol), `tenis_publico.read_public_feed` (campo `destacado` por evento) y la copia `apps/nba/src/nba/api/destacado_valor.py` en `/nba/v1/partido/{id}/mercados` (campo `destacado`). Pruebas: `tests/test_destacado_valor.py` y `apps/nba/tests/v2/test_destacado_valor_nba.py`, con el dilema 1,20/75 % contra 1,80/70 % (gana 1,80: 1,26 > 0,90).

Por quÃ© importa saberlo: con cuota del modelo (1 Ã· prob) el score vale 1 en todos los mercados, asÃ­ que sin cuota de casa la regla equivale a Â«la mayor probabilidad que aÃºn paga 1,20Â» (â‰¤ 83,3 %); el valor esperado solo discrimina con cuota real. Se compara con redondeo a 9 decimales para que el ruido de coma flotante no decida empates. Se conservÃ³ la regla del 2-nov de que, con cuotas de casa en el partido, solo cuentan los mercados cotizados por una casa. El destacado es siempre uno de los 3 mercados gratis de la web. `RANGO_DESTACADO` pasa a (1,20, null).

Web adaptada en la misma rama: `featuredSportMarket` (NBA y tenis) ya no calcula, solo localiza el mercado que manda el servidor en `destacado` (si es una revisiÃ³n posterior al inicio, queda sin destacado en vez de sustituirse); `loadNbaMarkets`/`withNbaMarkets` conservan su id; el cliente aplica la misma regla (`bestByValue`) solo si el servidor no manda el campo (fuente antigua o mercados aÃºn sin cargar). El Â«destacado del dÃ­aÂ» (`ergonomic-views`) usa tambiÃ©n `bestByValue`. Textos Â«cuota de 1,40â€¦Â» sustituidos por la regla nueva y versiones `?v=destacado-valor-20261105` para saltar la cachÃ© de Cloudflare. El historial de NBA/tenis se calcula en vivo con el destacado vigente, asÃ­ que la regla nueva tambiÃ©n cambia lo que enseÃ±a de partidos pasados (ya ocurrÃ­a con el cambio del 2-nov). App Flutter adaptada (misma rama, base `origin/main`, app 1.1.0+7): `featured_rule.dart` (`bestByValue`) sustituye la banda 74â€“85 % / cuota 1,20â€“1,60 de `featuredPick` (detalle del partido), el Â«Destacado del dÃ­aÂ» de fÃºtbol (`live_home`, ahora solo entre pronÃ³sticos abiertos y sin tarjeta si nadie cumple la regla) y `featuredMarket` de NBA/tenis, que respeta el campo `destacado` del servidor (`SportEvent.serverFeatured/featuredId`) y, sin Ã©l, aplica la regla con la cuota del modelo. Texto `detailNoFeatured` actualizado en los 6 idiomas. Ojo con las ramas: la regla Â«cuota â‰¥ 1,40, sin tope de probabilidadÂ» (commit f8c9ffd1, app 1.0.0+3, 25-oct) vive solo en `nba/v13-disponibilidad` y NUNCA llegÃ³ a `main`, que conserva la banda 74â€“85 %; esta rama parte de `main`, asÃ­ que sustituye la banda y deja sin efecto esa rama en este punto. No se subiÃ³ el cÃ³digo de versiÃ³n ni se compilÃ³ un AAB (hacerlo al publicar). Pendiente: los destacados ya congelados en `web_destacado` (hashchain) no cambian; sin desplegar (ver DEPLOYS.md) ni probado en navegador contra la API real. Base: `origin/main` 0097b767, rama `futbol/destacado-valor-esperado`.

## 5-nov-2026 Â· PronÃ³sticos de jugador NBA en Â«PendienteÂ»: faltaba el id de la NBA, no los crÃ©ditos

Los 14 partidos del 4-nov liquidaban los mercados de equipo y ninguno de jugador. La razÃ³n no era de crÃ©ditos ni de la
web: el marcador de cdn de las 10:00 ET trajo `games: []` con la fecha anterior, el colector lo dio por hecho durante
20 h y solo buscaba ids de hoy, asÃ­ que sin id de la NBA no sabÃ­a quÃ© box score pedir. DecisiÃ³n: reintentar el marcador
cada 55 min (tope 4 por ventana) mientras falten ids de ayer u hoy, en vez de fiarse de una sola lectura. El mismo dÃ­a
se aÃ±adiÃ³ SofaScore como respaldo automÃ¡tico de los box scores de jugador (fuente `sofascore` del colector, solo
partidos recientes, solo aÃ±ade filas, la caja oficial manda), pero depende de que el scraper del VPS pase el bloqueo
de SofaScore, que hoy no lo hace con la NBA (403 en la lista de temporadas): el cdn sigue siendo la vÃ­a principal.
Pendiente de decisiÃ³n: 66 mercados de 5 jugadores ausentes del box score (Jalen Johnson, Josh Hart, Jayson Tatum,
Trey Murphy, Jaylin Williams) siguen sin resultado; `resolver()` deja pendiente lo que no ve y no lo marca nulo.

## 4-nov-2026 Â· Publicadas las correcciones NBA; acreditaciÃ³n prospectiva condicionada a datos reales

Orden expresa de publicar. PR #255 integrado con arnÃ©s remoto verde (NBA con PostgreSQL, fÃºtbol/API, frontend y tenis), main `a491f225`. API concurrente de mercados preservada desde `61ff260`; sus probabilidades/Ãºltimas cuotas por lado se integraron con los contratos corregidos. CI detectÃ³ fixtures con fechas UTC en lugar de ET al cruzar medianoche y una ruta temporal sin permisos; se corrigieron las pruebas sin debilitar la lÃ³gica de producciÃ³n.

Publicados Ãºnicamente `nba-motor:auditoria-a491f225` y `nba-api:auditoria-a491f225`, con respaldo, migraciÃ³n 0009, ensayo lector y rollback. Un ensayo previo detectÃ³ directorios Docker sin lectura; se reconstruyÃ³ sin cachÃ© antes de sustituir. Cuatro rutas pÃºblicas 200, 153 archivos de API iguales a main, cadena de 1.541 sellos Ã­ntegra. Cron 00:30 UTC: 2.2, cero errores y primer pronÃ³stico de equipo sellado.

La cohorte y tolerancias se registraron antes de activar. No se acredita calibraciÃ³n con cero resultados ni se mezclan los de 2.0/2.1. Seguimiento por versiÃ³n activo; la candidata hÃ­brida permanece bloqueada. El artefacto actual vence el 7-nov-2026 13:18 CDMX y debe renovarse en local. Registro/rollback: DEPLOYS.md; evidencia y lÃ­mites: docs/nba_auditoria_correcciones.md.

## 4-nov-2026 Â· AuditorÃ­a NBA: correcciones y evidencia, promociÃ³n pendiente

La autorizaciÃ³n posterior del titular permite corregir el cÃ³digo auditado. Rama `codex/nba-auditoria-20261104`, sobre main vigente, preservando el checkout antiguo y la evidencia original. Las guardias temporales incluyen la recepciÃ³n del original: publicar un PDF antes del corte no prueba que el sistema lo hubiera recibido entonces. No se alteran filas inmutables para fingir esa disponibilidad.

El candidato 2.2 proyecta posesiones e infiere desde ratings congelados; no aprende resultados en el VPS. La ley separa regulaciÃ³n y OT y usa una CDF comÃºn para masas y cuantiles. Artefactos futuros/del dÃ­a objetivo/caducados se rechazan: publicar exige renovaciÃ³n local versionada, no entrenamiento en producciÃ³n. La web ya no afirma calibraciÃ³n sin evidencia y presenta versiÃ³n y log-loss en seis idiomas.

ValidaciÃ³n: 1.224 pruebas NBA aprobadas, 18 omitidas (17 de entrega legacy sin DSN especÃ­fico y un privilegio Windows); 94 regresiones finales y 4 pruebas nuevas de entrenamiento aprobadas. EvaluaciÃ³n retrospectiva de equipo: 1.235 partidos, Brier 0,20550, log-loss 0,59795, sin acreditar al hÃ­brido ni disponibilidad histÃ³rica original. SerializaciÃ³n 14,418 â†’ 0,0751 s. CI NBA incorpora PostgreSQL.

Se autorizÃ³ expresamente exportar cajas de jugadores mediante SELECT. La candidata de impacto de regulaciÃ³n sin RAPM empeorÃ³ Brier (0,21061 vs 0,20568; IC95 Î” positivo) y no se activa. Tampoco se traslada el impacto antiguo de finales a regulaciÃ³n sin validaciÃ³n. El motor conserva el nÃºcleo y exige evidencia para habilitar una mezcla. La confirmaciÃ³n posterior en 43 partidos de playoffs (Brier 0,20506) es descriptiva y no sirviÃ³ para elegir variante. 359 pruebas v2 con PostgreSQL aprobadas tras la puerta.

Ãšltima revalidaciÃ³n: 55/55 aprobadas, cero omitidas, incluyendo estrÃ©s completo, SQL PIT con equipos/fechas filtrados antes de resolver versiones, artefactos y API que identifica automÃ¡ticamente la versiÃ³n. El PostgreSQL desechable se detiene al terminar.

Sin despliegue, migraciones ni entrenamiento en VPS. PublicaciÃ³n del nÃºcleo, renovaciÃ³n local y certificaciÃ³n prospectiva pendientes. Detalle y vuelta atrÃ¡s: `docs/nba_auditoria_correcciones.md`; auditorÃ­a original conservada en `docs/nba_auditoria_reporte.md`.

## 3-nov-2026 Â· Las estadÃ­sticas de equipos de NBA las publica el servidor (API v2), no el navegador
La web resumÃ­a rÃ©cord, forma, cara a cara y clasificaciÃ³n en el navegador con ~26 peticiones de cartelera; solo veÃ­a desde el 20-oct (sin temporada pasada, cara a cara de dos semanas). **DecisiÃ³n:** `GET /nba/v1/partido/{id}/estadisticas` (`apps/nba/src/nba/api/estadisticas.py`, funciÃ³n pura + una consulta de solo lectura) devuelve el mismo contrato que ya consumÃ­a la web, calculado desde `nba.dato` (`puntos`, periodo 0, fase `final`, fuente por prioridad). **Reglas:** solo temporada regular (tabla `REGULAR` por temporada; sin pretemporada, play-in ni playoffs; una temporada sin fila usa 15-oct â†’ 13-abr y hay que aÃ±adirla antes de que empiece) y solo marcadores de fechas ANTERIORES a la del partido (un equipo no juega dos veces el mismo dÃ­a, asÃ­ que la fecha ET basta y no depende de la hora de inicio, que las temporadas viejas no tienen). Incluye `last_season` (temporada anterior completa) y un cara a cara de hasta 10 partidos de varias temporadas. Un partido de pretemporada responde 404 `sin_estadisticas` (traducido a los 6 idiomas en `static/i18n.json`). **Web:** `loadNba` pide solo 9 dÃ­as de cartelera (âˆ’4â€¦+4) y `loadNbaStats` pide el endpoint al abrir una pestaÃ±a de estadÃ­sticas; se borrÃ³ el cÃ¡lculo local. **Verificado contra la base real** (contenedor temporal de solo lectura con el rol `nba_api`): 52 partidos de 4 dÃ­as, todos 200, 0,11 s de media; cada equipo con 82 partidos de la temporada pasada (dedupe y filtro de regular correctos); estreno del 20-oct sin marcadores previos. **No desplegado:** exige reconstruir `nba-api` y la imagen del frontend (ver DEPLOYS.md); la ficha mostrarÃ¡ Â«TodavÃ­a no hay estadÃ­sticasÂ» hasta que el contenedor `nba-api` lleve el endpoint.

## 3-nov-2026 Â· La cartelera de NBA de la web lee la API v2 y explica cuÃ¡ndo llega el pronÃ³stico
Al retirarse la v1 de NBA (3-nov, 18:05 UTC) `/nba/api/data` pasÃ³ a redirigir (302) a `/nba/v2/` y la web (`sports-data.js`) y la app (`sports_feed.dart`) se quedaron sin fuente: Â«No se pudo cargar la fuenteÂ» y Â«Sin eventos este dÃ­aÂ». **DecisiÃ³n del titular:** solo v2; los pronÃ³sticos que la v1 ya habÃ­a publicado (hasta el 2-nov) no se recuperan en la web. `loadSport('nba')` pide `/nba/v1/cartelera?fecha=` desde el estreno de la temporada (20-oct, tope de 21 dÃ­as atrÃ¡s) hasta 4 dÃ­as adelante, y conserva los partidos sin pronÃ³stico: el pronÃ³stico ganador solo se muestra si viene sellado antes del inicio. Las estadÃ­sticas (rÃ©cord, forma, cara a cara, clasificaciÃ³n, descanso) se resumen en el navegador con los marcadores finales de la propia API, sin pretemporada y sin temporada pasada; el feed `nba_stats.json` no sirve porque se genera de las cohortes v1 congeladas. Tarjeta Â«CuÃ¡ndo se agrega el pronÃ³sticoÂ» en la ficha (hora de `sello_previsto`, 60 min antes del saque; distingue pendiente, sellado y sin pronÃ³stico previo, y nunca presenta uno a posteriori). **Pendiente:** la app mÃ³vil sigue leyendo `/nba/api/data`; el feed de estadÃ­sticas v2 en servidor; todavÃ­a no se despliega (rama `web/nba-cartelera-v2`, sin commit).


## 3-nov-2026 Â· Correcciones de auditorÃ­a: la evidencia previa decide el historial

Se guarda el destacado en la predicciÃ³n inmutable y se incluye en su sello; una fila reconstruida despuÃ©s del resultado deja de contar como pronÃ³stico publicado. Los lotes anteriores omiten el campo nuevo para conservar su forma. La migraciÃ³n 102 propaga capturas previas dentro de su transacciÃ³n, conserva su recepciÃ³n y aparta tiros incoherentes con copia Ã­ntegra en cuarentena; ensayo en Postgres aislado aprobado.

La nueva comparaciÃ³n A0/DC con la misma admisiÃ³n de xG reduce la diferencia a âˆ’0,001246 de log-loss en 5.541 partidos (IC95 cruza cero); en 475 de seguimiento A0 empeora +0,000304. No se promueve. Conteos sin simultÃ¡neos mantienen su orden frente a la media de liga. El nuevo A4 construyÃ³ 49.933 tramos de 7.138 partidos; sigue condicionado al once reconstruido y no demuestra mejora de acierto. La ausencia de evidencia no se convierte en parÃ¡metros de producciÃ³n. Suite corregida: 1.756 aprobadas, 122 omitidas. Detalle: `docs/correcciones_futbol_20261103.md`.

## 2-nov-2026 Â· Los escudos de una tarjeta terminada los manda el servidor, no la agenda
Al ver las tarjetas de fÃºtbol terminadas (PR #237) salÃ­an las iniciales en vez del escudo. **Causa:** los partidos terminados no estÃ¡n en la agenda del dÃ­a, que es de donde las tarjetas prÃ³ximas toman el escudo. **DecisiÃ³n:** que `destacados_resueltos` devuelva el escudo de cada equipo con la misma funciÃ³n que usa la agenda (`fichas.escudo`) en vez de buscar la ficha de cada partido desde el navegador (una peticiÃ³n por tarjeta) o de derivar la URL en el frontend (duplicarÃ­a la regla de dÃ³nde estÃ¡ cada imagen). Sin escudo descargado queda `None` y se mantienen las iniciales: no se inventa ninguna imagen.

## 2-nov-2026 Â· El destacado de la web se elige con la cuota de una casa, no con 1 Ã· probabilidad
El titular preguntÃ³ por quÃ© la tabla decÃ­a Â«Del modeloÂ» y pidiÃ³ dos cosas: que cada cuota diga de quÃ© casa es y que el destacado se elija con la cuota real. **DecisiÃ³n:** `partido_mercados.cuotas_casas` toma, de `odds_snapshots` (PropLine), la mejor cuota entre las casas de los suscriptores (`settings.soft_books`; Pinnacle y exchanges no son casas donde apostar) hasta el saque y con menos de 6 h, la misma regla de la escalera. **Por quÃ© Â«solo lo que cotiza una casaÂ» cuando el partido tiene cuotas:** el precio del modelo es una cuota justa sin margen; dejarlo competir con precios de casa (siempre algo menores) favorecÃ­a justo los mercados que ninguna casa cotiza (gana a cero, 1.Âª mitad). Sin ninguna cuota de casa en el partido (antes del 23-oct, liga sin PropLine) se conserva la del modelo y se etiqueta Â«Del modeloÂ». **Historial reproducible:** la cuota del partido terminado es la Ãºltima anterior al saque, asÃ­ que no cambia con el tiempo; `ref_price`/`ref_book` solo se rellenan si la cuota es de una casa. Medido en producciÃ³n (solo lectura): 213 destacados desde el 26-oct, 209 con casa (Bovada 115, Heritage 39, Jazz Sports 14â€¦), 70,4 % de acierto con la probabilidad media del modelo en 71,6 %; 2,8 s en recalcular todo (cachÃ© de 10 min). **A vigilar:** Bovada gana casi siempre por precio y es una casa que muchos suscriptores no pueden usar; si el titular quiere restringir las casas del destacado, es `settings.soft_books`.

## 2-nov-2026 Â· Los partidos de fÃºtbol terminados salen como tarjeta: el motivo era la fuente de la lista, no los datos
El titular preguntÃ³ por quÃ© no aparecÃ­an ni los terminados de hoy. **Causa:** la lista de tarjetas de fÃºtbol solo salÃ­a de los picks Â«prÃ³ximosÂ» (y de pago) de la portada; el servidor manda como prÃ³ximos Ãºnicamente los que no han empezado, asÃ­ que al empezar el partido su tarjeta desaparecÃ­a y quedaba solo en el panel de resultados (NBA y tenis salen de otra fuente que sÃ­ incluye terminados). **DecisiÃ³n:** construir las tarjetas terminadas desde el destacado resuelto de cada partido (`/markets/destacados`, ya cargado para el historial) en vez de pedir la ficha de cada uno o ampliar el payload de la portada; el destacado trae marcador y resultado, y no suma a Â«PublicadosÂ» porque no es un pick sellado. Probado con la respuesta real de producciÃ³n antes de desplegar.

## 2-nov-2026 Â· El destacado de la web sale de todas las opciones y `main` vuelve a ser el frontend de producciÃ³n
Orden del titular: resolver el aviso de que `main` no coincidÃ­a con producciÃ³n y que la tarjeta de fÃºtbol use todos los mercados y diga en la fecha si acertÃ³ o fallÃ³. **Por quÃ© la causa era una rama sin fusionar:** `web/destacado-en-tarjeta` se desplegÃ³ el 30-oct pero nunca se subiÃ³ a GitHub; fusionarla recuperÃ³ el frontend real y, de paso, el pie de pÃ¡gina y el estado AcertÃ³/FallÃ³ bajo el destacado que `main` tenÃ­a y producciÃ³n no. **Por quÃ© opciones complementarias solo en la web:** `filas_goles` listaba el lado mÃ¡s probable de cada mercado (la lista de la app), de modo que Â«Menos de 1,5Â» o los otros resultados del 1X2 no podÃ­an ser nunca el destacado; aÃ±adirlas en `construir(web=True)` cumple Â«todos los mercadosÂ» sin cambiar la lista ni los conteos de la app. CÃ³rners, tarjetas y 1.Âª mitad siguen con sus lÃ­neas validadas histÃ³ricamente. Efecto colateral: los destacados del historial pÃºblico se recalculan.

## 2-nov-2026 Â· Destacado de la web sin tope: se aplicÃ³ sobre el frontend real de producciÃ³n, no sobre el de main
Orden del titular: cuota mÃ­nima 1,40 y sin tope (antes 1,40-1,80). **Por quÃ© un parche archivo a archivo:** la comparaciÃ³n con el contenedor mostrÃ³ que el frontend en producciÃ³n lleva cambios del 30-oct (`app.js`, `ergonomic-views.js`) que `main` no tiene; copiar los archivos de `main` los habrÃ­a revertido. Se aplicÃ³ el diff del PR sobre las copias del contenedor (sin ambigÃ¼edad: una coincidencia por reemplazo) y se verificÃ³ por hash en el dominio real. El tope pasa a `None` (viaja como `null` en `rango`) en vez de infinito porque JSON no admite infinito.

## 2-nov-2026 Â· SharpAPI se captura como archivos y hacia adelante, no se carga en la base
El titular autorizÃ³ capturar SharpAPI para los mercados que PropLine no trae. **Por quÃ© asÃ­:** el plan gratuito no da histÃ³rico ni cierres y solo DraftKings y FanDuel con 60 s de retraso, de modo que solo sirve capturar a momentos fijos antes del saque (24 h, 6 h, 2 h, 60 min, 15 min); se guarda todo el catÃ¡logo prepartido del partido (â‰ˆ 1.500 filas, 58 mercados, 16 KB) porque cuesta lo mismo que filtrar y no se sabe aÃºn quÃ© mercados valdrÃ¡n. Siguen las convenciones del proyecto: originales como archivos, script con biblioteca estÃ¡ndar y cron del host (como `propline_captura.py`), sin tocar imÃ¡genes, base ni picks. Cargarlos en la base espera a tener semanas de datos y a ampliar el CHECK de `futbol.cuota_historica`.

## 2-nov-2026 Â· Cierre del rediseÃ±o de fÃºtbol: cuota 1,40, el once no mueve el 1X2 y producciÃ³n ya estaba alineada
Decisiones del titular: cuota mÃ­nima 1,40 hacia arriba y se acepta lo medido sobre A0 frente a Dixon-Coles (se queda Dixon-Coles). **Por quÃ© no hay cambios de cÃ³digo en los picks:** el mÃ³dulo de alta probabilidad ya toma el porcentaje de Pinnacle sin margen (desde el 5-oct) y es justo lo que 10.000 partidos con cuotas reales confirman como la fuente honesta; el motor propio promete 5-9 puntos de mÃ¡s y sustituirlo exigirÃ­a repetir la prueba histÃ³rica de `alta_prob_calibracion` sin ganancia esperable. F5 (A3-A7) se midiÃ³ con el once real: rotaciÃ³n y habituales ausentes tienen el signo esperado (âˆ’1,4 % de goles por titular cambiado; +1,9 % por cada habitual ausente del rival) pero el log-loss mejora â‰¤ 0,0012, y la fuerza del once no aporta. Con cuota â‰¥ 1,40 el techo honesto es â‰ˆ 65 % con una lÃ­nea y â‰ˆ 72-75 % eligiendo entre la escalera de lÃ­neas. Queda la mediciÃ³n semanal (`remedir_semana.py`) y dos decisiones del titular (tope de 1,80 del destacado web; capturar SharpAPI). Informe Â§14.

## 2-nov-2026 Â· Las cuotas histÃ³ricas se cargan en `futbol.cuota_historica`, no en `odds_snapshots`
El titular autorizÃ³ cargar el archivo de BetsAPI y el respaldo de API-Football. **Por quÃ© una tabla aparte:** `odds_snapshots` es inmutable y varias lecturas no filtran por fuente (`api/main.py`, `daily.py`, `clv._closing_prices`, `quote_coverage`); cuotas retroactivas con `captured_at` ficticio habrÃ­an alterado CLV y pantallas ya medidos, y un error de carga no se puede deshacer allÃ­. La tabla nueva es igual de inmutable, guarda solo apertura/T-60/cierre (1,03 M filas, 351 MB; los 17 M de cambios de precio siguen en el VPS) y marca `retroactiva`. Ensayada en un esquema aislado, cargada en una transacciÃ³n, `odds_snapshots` intacta. De paso, la mezcla casa + motor se validÃ³ fuera de muestra y se redujo a hÃ¡ndicap y goles de la 1.Âª parte: en cÃ³rners y hÃ¡ndicap total no aporta.

## 1-nov-2026 Â· Con 10.000 partidos de cuotas de bet365 la casa sigue siendo la fuente honesta y el motor solo ayuda en hÃ¡ndicap, cÃ³rners y 1.Âª parte
Se analizÃ³ en local (sin tocar la base) el archivo de BetsAPI del VPS: 9 ligas, 6.944 partidos con modelo, cuotas a T-60 y al cierre. **Por quÃ©:** con una muestra 50 veces mayor que la de PropLine (150 partidos) el resultado se confirma: bet365 sin margen cumple o es conservador (mejor 10 % del dÃ­a 70â€“72 %) y el motor propio promete 8 puntos de mÃ¡s; su aporte Ãºtil es una mezcla de â‰ˆ 30 % solo en mercados con menos liquidez (hÃ¡ndicap, cÃ³rners, 1.Âª parte), con ganancias de Brier de 0,0003â€“0,003. Un error mÃ­o (el Â«pierdeÂ» del hÃ¡ndicap del motor estaba mal calculado) se encontrÃ³ porque el motor salÃ­a 20 puntos por encima de la realidad en hÃ¡ndicap; se corrigiÃ³ y se aÃ±adiÃ³ prueba. Las lecturas en vivo hicieron medibles los cÃ³rners en el minuto 65-70 (â‰ˆ 53 %, la casa ya precia que el favorito pierda) y la carrera a X cÃ³rners. Las fichas de bet365 NO traen todos los mercados de las listas (faltan descanso/final, goleadores, primer equipo en marcar, pases, faltas). Informe Â§13.

## 1-nov-2026 Â· Donde Pinnacle no cotiza, la mediana de las demÃ¡s casas
DecisiÃ³n del titular: usar las demÃ¡s casas de PropLine en los mercados que Pinnacle no cotiza. **Por quÃ© la mediana y no una casa:** en estas ligas, a una o dos horas del saque, cada casa comÃºn tiene el mismo Brier que Pinnacle en las opciones compartidas (diferencia < 0,0007) y cumple lo anunciado en el tramo 60â€“80 %; la mediana no depende de que una casa concreta cotice o se equivoque. Sube la cobertura del mercado del 78â€“80 % al 99â€“99,5 % de las opciones con cuota â‰¥ 1,28 sin perder honestidad (cierre: anuncia 74,8 %, acierta 74,7 %). El motor queda para el â‰ˆ 1 % que no cotiza nadie. De paso se corrigiÃ³ el emparejamiento del hÃ¡ndicap de Pinnacle (local L con visitante âˆ’L). Informe Â§12.

## 1-nov-2026 Â· Con cuota real â‰¥ 1,28 la probabilidad publicada debe ser la de Pinnacle, no la del motor
Medido con las cuotas reales de PropLine (23-oct â†’ 1-nov, 128 partidos a T-60, 150 al cierre). **Por quÃ©:** exigir cuota â‰¥ 1,28 a una opciÃ³n que el motor ve por encima de 74 % selecciona justo los casos en que el motor discrepa del mercado, y en ellos acierta lo que dice Pinnacle (motor 54 %, Pinnacle 46 %, real 46â€“47 %). Elegir entre muchas lÃ­neas con el motor infla lo anunciado 5â€“8 puntos; Pinnacle sin margen cumple lo anunciado (cierre 74,7 % frente a 74,4 %). El motor queda para mercados que Pinnacle no cotiza, con el tope de 74,4 %. Muestra corta (Â±8 puntos): remedir cada semana. Informe Â§12.

## 1-nov-2026 Â· Mercados del titular: la probabilidad alta honesta estÃ¡ en mercados Â«aburridosÂ», no en los populares
Se modelaron y midieron los 37 mercados de las dos listas del titular con las mismas distribuciones del rediseÃ±o (matriz de A0 o del mercado invertido, mitades por f1 de liga, Yip, Dawson, props por jugador) y la cuota mÃ­nima 1,28. **Por quÃ© importa:** por encima de â‰ˆ 74 % de probabilidad la cuota cae bajo 1,28, asÃ­ que el techo honesto con cuota publicable es â‰ˆ 75â€“80 %, y lo alcanzan favorito marca, 2.Âª parte mÃ¡s de 0,5, mÃ¡s de 1,5, doble del favorito, primer equipo en marcar y cÃ³rners mÃ¡s de 7,5; los mercados populares (Lista 2) casi todos quedan bajo 60 %. Tres afirmaciones de la Lista 1 no se sostienen (2.Âª mitad con mÃ¡s goles 45 %, ambos marcan NO 46 %, AH de cÃ³rners 63 %). Los props de jugador crudos prometen de mÃ¡s y se recalibran con temporadas anteriores; los pases son la excepciÃ³n (deriva). Informe Â§10â€“11.

## 1-nov-2026 Â· Retirada completa de las fuentes antiguas en un solo PR (`retirar/fuentes-todo`)

DecisiÃ³n del titular: hacerlo todo de una vez en un PR nuevo, y fusionar y desplegar al final. Lo que se aÃ±ade a las fases 1-2c: las tres piezas que quedaban enganchadas, separando siempre lo vivo de lo retirable. `sofascore_alineaciones` y `sofascore_partidos` mezclaban la lectura del archivo de Apify con las funciones que escriben bajas y once (`emparejar`, `aplicar`, `titulares`, `bajas`) y que sigue usando SportsAPIPro: esas pasan a `sofascore_carga.py` y el resto se borra. `history_fd.py` mezclaba el cargador de CSV de football-data con `insertar_cierre` (lo usa `cierres_odds_api`) y `_parse_date` (lo usa `early_vs_close`): se extraen y el cargador se borra. El chequeo de frescura del xG ya no lee los assets de worldfootballR.

Descanso: `db/093` hace que `v_descanso_equipo` use `calendario_equipo` hasta su Ãºltima carga y los partidos terminados de `matches` despuÃ©s; antes la vista sobrestimaba el descanso 8,2 dÃ­as de media. Verificado en un esquema aislado con partidos antes y despuÃ©s del corte. LÃ­mite declarado: copas domÃ©sticas y selecciones posteriores al 22-oct no estÃ¡n.

AdemÃ¡s, la prueba de tenis `test_shadow_paid_path_uses_post_receipt_time_and_preseals` dependÃ­a del mes real (parcheaba `shadow.now`, pero `Capture` usa su propio reloj): desde el 1-nov fallaba en `main` limpio. Se fija el reloj de `Capture` (mismo criterio que #64).

## 1-nov-2026 Â· Las fuentes retiradas se quitan del cÃ³digo por fases, no de golpe

DecisiÃ³n del titular: retirar API-Football, Apify, PitchAPI, BetsAPI, worldfootballR/FBref, football-data y soccerway/365scores conservando los datos ya cargados. Por quÃ© por fases: el grafo de imports mostrÃ³ que `api_football.py` no es solo un cliente, tambiÃ©n aloja `record_health`, que usan 20 mÃ³dulos (PropLine, FotMob y SportsAPIPro incluidos), y que football-data sostiene la base estadÃ­stica, los cierres de 1X2 y 24 archivos de `src`. Borrarlos de golpe habrÃ­a roto jobs activos sin avisar.

Fase 1 (esta rama): solo lo que no tiene importadores ni cron activo: PitchAPI completo con su panel, `calendario_equipos`, `injuries`, los dos puentes AFâ†”FotMob, el descargador de BetsAPI y 6 pruebas. Las bajas siguen entrando por FotMob y SportsAPIPro. Los datos y migraciones no se tocan; el panel `/control/respaldo` desaparece y la clave de PitchAPI ya estaba vacÃ­a en `pitchapi_settings`. Vuelta atrÃ¡s: `git revert` del commit de la rama (el cÃ³digo vive tambiÃ©n en `e097691`). Lo que queda y por quÃ© estÃ¡ en `harness/tareas.md`.

## 31-oct-2026 Â· El respaldo de cuotas es un comando por lotes, no una llamada del endpoint
DecisiÃ³n: The Odds API solo se consulta desde `python -m qf.ingest.cuotas_respaldo` y el overlay lee una cachÃ© en disco. Un endpoint pÃºblico que gastara crÃ©ditos serÃ­a un vector de abuso, y el presupuesto (2.855 crÃ©ditos hasta el 23-nov) es la restricciÃ³n principal. Se usa el histÃ³rico a la hora del sello para que `as_of <= sealed_at`; PropLine gana siempre y el respaldo solo rellena lados en None, con emparejamiento por nombre exacto y comienzo a Â±30 min (ante duda, Â«â€”Â»).

## 30-oct-2026 Â· App: NBA y tenis con selector global (1.1.0+5)

Por quÃ© un selector global de deporte y no pestaÃ±as por deporte: la barra inferior ya estÃ¡ llena y el deporte condiciona Inicio, Predicciones y Mercados a la vez; un solo estado evita duplicar pantallas. Los feeds pÃºblicos de NBA y tenis se muestran sin candado VIP porque en la web son pÃºblicos (`actionable:false`): un candado en la app no protegerÃ­a nada; venderlos exige que el servidor aplique acceso, como hace con fÃºtbol. No se muestran cuotas porque los feeds no las publican (`price: null`). Escudos, logos y fotos vienen del servidor, con respaldo a iniciales si falta la imagen. Decidido por el titular: el deporte inicial es el primero visible de Mis deportes (Â«por defectoÂ»), siempre; dentro de la sesiÃ³n manda lo que toque el usuario, pero no se guarda como deporte de arranque (se eliminÃ³ `sports_last`/`SportPrefs.remember`). VersiÃ³n 1.1.0+5. Verificado: `flutter analyze` limpio, 376 pruebas de Flutter y `tests/test_mensajes.py` en verde; APK de depuraciÃ³n compilado, la firma de release no estÃ¡ disponible en el worktree y la prueba en emulador no se hizo (emulador apagado).

## 29-oct-2026 Â· #historial desde el 26 de octubre, solo Destacados y Alta probabilidad

DecisiÃ³n del titular: el historial de la web empieza el 26 de octubre (dÃ­a local) y de ahÃ­ hacia atrÃ¡s no se muestra nada. Cuenta solo los Destacados de fÃºtbol, NBA y tenis y Alta probabilidad (fÃºtbol); la regla de quÃ© es destacado no cambia y no se aÃ±ade ninguna leyenda (orden del titular). Medido antes de aplicar, con la web en producciÃ³n: destacados 54 de 69 (78,3 %) y Alta probabilidad 51 de 60 (85 %), 105 de 129 (81,4 %) juntos; antes del 26, 65,4 % y 80 %.

Por quÃ© en servidor: el destacado de fÃºtbol no se guarda, se recalcula del anÃ¡lisis del modelo y pedir una ficha por partido desde el navegador da 429. `GET /mobile/v1/markets/destacados?desde=` (`partido_mercados.destacados_resueltos`) lo devuelve ya resuelto, con definiciÃ³n fija: `aplicar_acceso_web` sin picks abiertos ni VIP, cuota siempre la del modelo. La ficha de un partido puede enseÃ±ar otro destacado a quien tenga un pick abierto (su cuota publicada saca la fila del rango 1,40â€“1,80), asÃ­ que las cifras pueden diferir levemente de las medidas en la web. Tenis y NBA usan `featuredModelMarket` sin revisiones; antes el historial contaba el mercado Â«ganadorÂ» de cada evento. Sin desplegar: la API va antes que el frontend.

## 28-oct-2026 Â· #historial rediseÃ±ado para convertir: la prueba es verlo todo, con cuota y resultado

El titular pidiÃ³ rediseÃ±ar `#historial` porque es donde el visitante decide si el sistema da resultado y si compra la membresÃ­a. La versiÃ³n anterior era una tabla plana de 50 filas sin cifras resumen. DecisiÃ³n: el nuevo `historial-views.js` aplica el mismo patrÃ³n de prueba que ya usaban #alta/#parley/#escalera (cifra grande, racha, sello, planes, preguntas) y aÃ±ade lo que faltaba: resumen con intervalo de Wilson, prometido frente a real, curva de beneficio, acierto por dÃ­a y por deporte, y la lista dÃ­a por dÃ­a con cuota y marcador de cada pronÃ³stico.

Reglas de honestidad que mandan sobre el marketing (y tienen prueba en `historial-views.test.mjs`): (1) la muestra y el rango probable van siempre junto al porcentaje, con aviso bajo 50 liquidados; (2) el beneficio usa solo cuotas realmente registradas (fÃºtbol, 1 u por pronÃ³stico) y no se esconde aunque sea modesto (+0,96 u en 64 con cuota medio 1,19: se acierta mucho y se gana poco); (3) en NBA y tenis ninguna casa publica cuota, asÃ­ que se enseÃ±a la Â«justa del modeloÂ» (1 Ã· prob.) marcada con â‰ˆ y NUNCA entra en el beneficio; (4) los fallos tienen el mismo peso visual que los aciertos y hay filtro de Â«falladosÂ»; (5) sin Â«seguraÂ», Â«garantizadaÂ» ni Â«certeraÂ».

Datos: sin cambios en la API (`/mobile/v1/markets/history`, `/web/deportes/*`); `resultRows` pasÃ³ a `allResults` y ahora lleva `prob`. Solo SVG propio y clases de CYBERCORE 0.3.0 ya vendorizadas (sin CDN nuevo: la CSP no lo admite y `cybercore-charts` aÃ±adirÃ­a una dependencia sin necesidad); el CSS nuevo es aditivo en `conversion.css` con prefijo `.cv-hist-` (la prueba de CSS existente lo exige y sigue verde). El orden `predecir â†’ sellar â†’ publicar` no se toca.

Base: la producciÃ³n de la web NO coincide con `main` (el hub `ergonomic-views.js` y la ventana Ãºnica viven en `docs/deploy-estado-mercados`, `027e536`); esta rama sale de ahÃ­. Antes de desplegar hay que fusionar esa base a `main` o desplegar desde esta rama siguiendo `DEPLOYS.md`. Verificado con datos reales (246 resultados) en escritorio y 375 px, CSP estricta sin estilos en lÃ­nea.

## 28-oct-2026 Â· Estado real en cada mercado de fÃºtbol; #alta, #parley y #escalera centradas y sin avisos

El titular pidiÃ³ que la columna Â«AccesoÂ» de los mercados de fÃºtbol diga el estado de la apuesta, como en NBA. DecisiÃ³n: el servidor decide el resultado, no el navegador. `partido_mercados.resultado_fila` liquida cada fila abierta de un partido terminado con la misma regla de los picks (`eval.clv._settle_outcome`) y, para gana a cero, 1Âª mitad, cÃ³rners y tarjetas, con la de la escalera (tarjetas = amarillas + rojas). Si falta el dato (p. ej. cÃ³rners sin estadÃ­stica) la fila queda Â«PendienteÂ»: no se inventa un resultado. Las filas con candado VIP no llevan resultado, para no filtrar su contenido. La web muestra AcertÃ³ / FallÃ³ / DevoluciÃ³n / Pendiente; el tipo de cuota (registrada o del modelo) pasa a una nota bajo la cuota y el destacado a una nota bajo la selecciÃ³n.

Las tres vistas de `conversion-views.js` tenÃ­an ancho mÃ¡ximo de 1120 px pero sin `margin-inline: auto`, asÃ­ que en pantallas anchas quedaban pegadas a la izquierda (medido en producciÃ³n a 1800 px: 157â€“1277 de 1800). Se centran en `conversion.css`. Por decisiÃ³n del titular se quitan: en #alta el aviso Â«Acertar no es lo mismo que ganar dineroÂ»; en #escalera el aviso del margen de la casa, Â«CÃ³mo se elige cada escalÃ³nÂ», el bloque Â«Cadena Â· Ãºltimo loteÂ» y la lista Â«Todos los retos cerradosÂ». El historial por longitud y las preguntas frecuentes se conservan.

## 28-oct-2026 Â· La web tiene su propia regla de destacado y de mercados gratis

El titular aclarÃ³ que la web es independiente de la regla de la app: necesita siempre un pronÃ³stico destacado visible y gratis, y al menos 3 mercados abiertos sin VIP. DecisiÃ³n: el destacado es, de TODOS los mercados del partido (tambiÃ©n los que sin VIP salen con candado), el de mayor probabilidad con cuota entre 1,40 y 1,80, y se enseÃ±a abierto. La cuota es la del modelo (1 Ã· probabilidad; la publicada si el mercado coincide con un pick sellado abierto), rotulada Â«Cuota del modeloÂ» para no confundirla con una cuota de casa. Gratis = el destacado + los siguientes mÃ¡s probables del rango hasta 3; si el rango no da para 3, se completa con los mÃ¡s probables. El resto sigue con candado (solo categorÃ­a) y los marcadores no se regalan.

ImplementaciÃ³n: `partido_mercados.aplicar_acceso_web`, activada solo con `GET /mobile/v1/matches/{id}?web=1`; sin ese parÃ¡metro (la app) todo queda igual, con prueba. La elecciÃ³n vive en el servidor porque los mercados bloqueados nunca llegan al navegador. Quien tiene VIP ve todo abierto y el mismo destacado. Un destacado derivado del anÃ¡lisis no es un pronÃ³stico sellado: la tarjeta lo dice y solo enseÃ±a el registro de cadena si coincide con un pick sellado. Sustituye el criterio anterior de la web (1,30â€“1,80 sobre picks sellados).

NBA y tenis adoptan la misma ventana Ãºnica (`sports-window.js`, mismo `window.css`), dentro de `#partidos` con el selector de deporte de la cabecera. Es solo presentaciÃ³n de lo que ya publican los motores: la NBA y el tenis no tienen cuotas de casa, asÃ­ que el destacado usa la Â«cuota del modeloÂ» (1 Ã· probabilidad) en 1,40â€“1,80 con la mayor probabilidad (`featuredModelMarket`), y los mercados revisados despuÃ©s del inicio no se consideran pronÃ³stico previo. EstadÃ­sticas: NBA = probabilidad de ganar, proyecciones de equipo, reporte oficial de lesiones y resultado; tenis = probabilidad de ganar, sets, juegos y resultado. Todo abierto (NBA y tenis son pÃºblicos). La cabecera es la misma de todas las pÃ¡ginas (se descartÃ³ compactarla). **Tenis, estadÃ­sticas de jugadores (decisiÃ³n del titular, 28-oct):** la pestaÃ±a de estadÃ­sticas pasa de Â«lo que dice el modeloÂ» a datos de los jugadores, sacados de API-Tennis (`get_players`, `get_standings`, `get_H2H`, con `scores` por set de los Ãºltimos 10 partidos de cada uno). Un exportador en el host (`scripts/publicar_tenis_estadisticas.py`, cachÃ© en disco, tope de 600 llamadas/dÃ­a y 140 por corrida) resume las respuestas con `src/qf/api/tenis_estadisticas.py` y escribe `tennis_stats.json`; la API lo sirve en `/web/deportes/tenis/estadisticas/{id}` sin tocar la red ni conocer la clave. PestaÃ±as: Resumen (comparativa, etiquetas, ranking por temporada), Forma (Ã­ndice 0â€“100, ventanas de 30/90/360 dÃ­as, racha, mÃ¡s de 2,5 sets, tie-breaks, primeras rondas vs. avanzadas, clasificaciÃ³n), Superficie, Cara a cara, Modelo y Resultado. **No hay, porque la fuente no lo trae:** rendimiento como favorito/no favorito (no hay cuotas histÃ³ricas), mano hÃ¡bil, estatura/peso ni pista cubierta; las etiquetas Â«especialista en sorpresasÂ» y Â«favorito sÃ³lidoÂ» quedan fuera por lo mismo. Las ventanas de tiempo cuentan solo dentro de los 10 partidos que entrega la fuente. Los partidos suspendidos (sets 0-0 o menos de 2 sets) no cuentan para sets ni tie-breaks. En NBA siguen sin existir forma/cara a cara: requieren su propio exportador.

## 28-oct-2026 Â· Partidos y Mercados pasan a una sola ventana: pronÃ³stico y estadÃ­sticas del mismo partido

El titular pidiÃ³ ver el pronÃ³stico y las estadÃ­sticas de un partido en una sola ventana, con lectura fÃ¡cil y CYBERCORE CSS 0.3.0 como base. `Partidos` y `Mercados` (que repetÃ­an la lista de partidos) se fusionan en la ruta `partidos`; `mercados` y `partido` quedan como alias, asÃ­ que los enlaces viejos siguen funcionando. Cabecera de una fila, franja de fecha/liga, lista de partidos con escudos, y dos zonas con desplazamiento propio: pronÃ³stico (destacado, mercados) y estadÃ­sticas en pestaÃ±as (resumen, forma, cara a cara, estadÃ­sticas, tabla, alineaciones). En mÃ³vil una zona a la vez con selector PronÃ³stico | EstadÃ­sticas.

Decisiones: (1) El destacado se elige en el navegador entre los pronÃ³sticos sellados y abiertos que envÃ­a el servidor: cuota de 1,30 a 1,80 (el titular bajÃ³ el mÃ­nimo de 1,40 a 1,30 el 28-oct) y, entre ellos, la mayor probabilidad (`featuredPick`, con pruebas); si ninguno cumple, la tarjeta lo dice y no se rellena con otro. (2) El bloqueo sigue siendo del servidor: el navegador solo ordena abiertos primero, muestra los reservados como Â«Contenido reservado / VIPÂ» y ofrece un Ãºnico Â«Acceso VIPÂ» hacia planes. Que gratis vea 3 mercados en lugar de los que hoy abre `partido_mercados.aplicar_acceso` es polÃ­tica de acceso compartida con la app y NO se cambiÃ³. (3) Las cuatro hojas originales siguen idÃ©nticas por hash; se aÃ±ade `window.css`, solo disposiciÃ³n, sin colores ni fuentes propios y con todos los selectores colgando de `.win`/`.is-win` (lo exige `original-css.test.mjs`). Es una excepciÃ³n a Â«solo hojas originalesÂ», anotada aquÃ­ para que se pueda revertir quitando esa hoja.

## 27-oct-2026 Â· Tenis: juegos por jugador sÃ­, aces y dobles faltas no

El titular pidiÃ³ los pronÃ³sticos de jugadores de tenis. PropLine cotiza aces, dobles faltas, puntos de quiebre y juegos ganados por jugador (125-225 partidos por hora). Solo los juegos ganados salen de lo que el motor ya calcula (la misma distribuciÃ³n conjunta de juegos que da el total y el hÃ¡ndicap); los otros tres exigirÃ­an otro modelo y quedan fuera. El contrato vive en un paquete nuevo porque aÃ±adirlo al catÃ¡logo cambiarÃ­a los hashes del estudio multi-mercado congelado. En el mismo cambio, un partido sellado sin precio por un nombre intermedio en PropLine: se acepta solo el mismo nombre y apellido con nombres intermedios de mÃ¡s, nunca un parecido, porque un falso emparejamiento sellarÃ­a el precio de otro partido.

Desplegado a las 15:45:35 UTC: imagen `quantfut-tenis:45f5876` (`main` `45f5876`, PR #177). Ensayo y vuelta atrÃ¡s en `DEPLOYS.md`. Los Â«mÃ¡s deÂ» de juegos por jugador heredan la diferencia que el motor ya tiene en el total de juegos (âˆ’0,04 frente al mercado); se mide fuera de muestra, no se corrige a mano.

## 27-oct-2026 Â· ErgonomÃ­a significa acomodo, sin cambiar el CSS

El titular corrigiÃ³ el alcance: mantener obligatoriamente el diseÃ±o anterior, sin cambiar colores, tarjetas ni botones. Se retira la hoja `ergonomia.css`; fÃºtbol, NBA y tenis reutilizan `live-pick`, paneles, cabecera, controles y planes anteriores. El menÃº de escritorio deja de abrir un cajÃ³n diseÃ±ado solo para mÃ³vil; las herramientas adicionales quedan agrupadas con componentes ya existentes. Se aÃ±aden huellas fijas de los cuatro CSS anteriores para impedir que otro cambio visual vuelva a sustituirlos. La integraciÃ³n de datos reales se conserva.

CorrecciÃ³n publicada a las 15:33:52 UTC en `quantfut-api-original:5ba3375`, igual a `main` `1866c9b` (PR #175). CI verde, ensayo aislado y 179 archivos finales verificados. El dominio carga Ãºnicamente las cuatro hojas originales, con hashes idÃ©nticos a `18f5604`, y sirve el HTML con revalidaciÃ³n para evitar una versiÃ³n visual anterior en cachÃ©. Sin cambios en motores ni cron.

## 27-oct-2026 Â· La navegaciÃ³n reÃºne fÃºtbol, NBA y tenis

El titular pidiÃ³ ordenar ergonÃ³micamente la web e incluir los tres deportes. La nueva portada prioriza encontrar un anÃ¡lisis real y mantiene resultados y planes prÃ³ximos, con cuatro accesos principales y herramientas agrupadas. Los nÃºmeros del texto adjunto se sustituyen por las cifras del servidor: no se inventan rentabilidad, popularidad ni escasez. NBA conserva su distinciÃ³n estadÃ­stica y las revisiones posteriores al inicio no cuentan como pronÃ³sticos previos. Para tenis, la API recibe solo una proyecciÃ³n pÃºblica de campos permitidos; no se montan los originales privados. Ver `docs/web_ergonomia_multideporte_20261027.md`.

Publicado a las 15:16:36 UTC sobre `main` `de06ab6` (PR #172), con CI verde, ensayo aislado y 180 hashes finales coincidentes. Se conservaron todos los montajes de la API, el worker y el panel NBA. Solo se aÃ±ade al host un exportador de JSON pÃºblico de tenis, cada cinco minutos, sin llamadas a proveedores ni cambios en sus pronÃ³sticos originales. Verificados en el dominio cuatro pronÃ³sticos abiertos y cinco reservados de fÃºtbol, 155 eventos de tenis sin problemas de integridad y las 18 cohortes NBA.

## 27-oct-2026 Â· La web consume el motor real

El titular pidiÃ³ conservar el diseÃ±o anterior y retirar los pronÃ³sticos ficticios. El motor ya corre: la jornada del 27-oct estÃ¡ calculada y sellada. La correcciÃ³n conecta la web al contrato real de la app, con el mismo recorte gratis/VIP, en lugar de modificar modelos o evitar la puerta de CLV. Los archivos CSS y CYBERCORE 0.3.0 permanecen intactos. Ver `docs/web_pronosticos_reales_20261027.md`.

Publicado a las 14:14:55 UTC sobre `main` `b05e085` (PR #170): cuatro selecciones reales comprobadas visualmente en el dominio. Se contrastaron 166 archivos de base y se ensayÃ³ la imagen con consultas de solo lectura antes de sustituir exclusivamente la API. El motor ya estaba activo: el fallo era la presentaciÃ³n ficticia de la web, por eso no se entrenÃ³ ni se modificÃ³ la puerta de los picks de valor. Respaldo y reversiÃ³n en `DEPLOYS.md`.

## 2026-10-26 â€” NBA 1.7.0: la fuerza individual entra al vivo y lo publicado se revisa sin reescribirse
Por instrucciÃ³n del titular la fuerza individual se activa aunque su mejora histÃ³rica no sea concluyente, y lo ya publicado se recalcula. DecisiÃ³n clave: el recÃ¡lculo es una revisiÃ³n sellada aparte, nunca una ediciÃ³n del original; un partido ya iniciado se recalcula solo con informaciÃ³n anterior a su fecha (la primera versiÃ³n usaba todo hasta hoy, incluido el resultado del propio partido, y la fuerza ajustada con partidos futuros: lo detectaron las verificaciones) y no cuenta en el marcador, que usa la Ãºltima versiÃ³n previa al salto. Al consolidar playoffs, el historial individual de inicio de temporada quedÃ³ lleno de playoffs (Brunson 19 de 20) y empeoraba las combinaciones; un partido regular usa solo partidos regulares. Ensayo con 1.061 resultados: Brier 0,2490 frente a 0,2482 del original (0,2518 antes de esa correcciÃ³n); total del partido mejora, ganador empeora; una semana no lo distingue del azar. Detalle: `docs/nba_recalibracion_17_20261026.md`.

## 2026-10-26 â€” NBA: pertenencia actual comprobada y fuerza individual separada de los resultados publicados
El usuario pidiÃ³ corregir el efecto de los traspasos y recalibrar el vivo. La copia inicial estaba antigua; se creÃ³ una copia aislada desde `03f4ada` (productor 1.5.0). Se capturaron las 30 plantillas oficiales: 521 IDs Ãºnicos y 121 con equipo distinto al Ãºltimo registro histÃ³rico. La pertenencia pasa a una evidencia actual con recibo real, temporada y hash, tambiÃ©n antes del debut; el historial personal sigue al ID y no se confunde una cotizaciÃ³n con pertenencia. La fuerza individual se mide con regresiones regularizadas de margen/total por minutos, comparando la rotaciÃ³n actual con la que ya representa la forma histÃ³rica. A diferencia de transportar el Elo del antiguo equipo, sÃ­ distingue valor individual; tampoco es una medida causal de on/off. Elegida en 2024-25 (ridge 25, peso 0,25), mejora poco en 2025-26: ganador âˆ’0,000129 de Brier, IC95 [âˆ’0,000681; +0,000319]; equipo âˆ’0,000131 y total âˆ’0,000166. No supera la regla y no cambia las probabilidades publicadas: se registra aparte en sombra con las plantillas reales para evaluaciÃ³n prospectiva. No se dice que el motor completo estÃ© recalibrado. La revisiÃ³n automÃ¡tica rechazÃ³ exportar el modelo activo y sus datos a esta carpeta; la alternativa es comparar y ensayar dentro del servidor, sin esa copia. Ver `docs/nba_current_rosters_20261026.md`.

## 2026-10-26 â€” NBA: el Elo ponderado por la plantilla actual no mejora el ganador
Encargo tras IND @ MIL (modelo 69 % Milwaukee, mercado 41 %; Giannis ya en Miami): cada jugador de la rotaciÃ³n arrastra el Elo de los equipos con los que jugÃ³ sus Ãºltimos minutos. Protocolo congelado antes de calcular (`nba_roster_elo_protocol.json`). DecisiÃ³n clave: no entra; las cuatro configuraciones empeoran en el ajuste (2024-25) y en la prueba (2025-26: la elegida +0,00038 [âˆ’0,00005; +0,00082]; con Î± 1 empeora con significaciÃ³n) y donde mÃ¡s mueve el Elo mÃ¡s empeora. El rating que arrastra un jugador es el de su equipo anterior, no lo que vale Ã©l; valorar traspasos exige un rating por jugador, que es otro modelo. El productor no cambia. `docs/nba_elo_plantilla_20261026.md`.

## 2026-10-26 â€” Notas recuperadas de una copia local desactualizada
La carpeta principal seguÃ­a en `nba/v13-disponibilidad` (197 commits por detrÃ¡s de `main`) con notas sin commitear y otras que se perdieron al fusionar sus commits: el cÃ³digo sÃ­ llegÃ³ a `main`, las notas no. Se copiaron tal cual 3 entradas de DEPLOYS.md, 7 de este registro y 3 secciones de tareas; no se copiÃ³ lo que `main` ya cuenta con otra redacciÃ³n (segunda auditorÃ­a NBA, props 100K, bet365 normalizadas). Las tareas que quedaban abiertas se cierran con su motivo verificado contra `main`, segÃºn la regla de la limpieza del 25-oct.

## 2026-10-26 â€” `nba_api` por proxy: 86 de 95 partidos recuperados; el acceso funciona con el proxy bÃ¡sico (1 crÃ©dito), no con el premium
DecisiÃ³n clave: de `swar/nba_api` se usan sus endpoints (BoxScoreTraditionalV3, GameRotation) llamados por ZenRows desde `nba.stats_proxy`, no la librerÃ­a ni el acceso directo (stats.nba.com agota el tiempo y el CDN da 403 desde el PC y el VPS). Tope de gasto 450 crÃ©ditos aplicado antes de cada peticiÃ³n; gasto real 106 (el premium del primer ensayo sobraba: el bÃ¡sico basta). Las cifras del 6-oct estaban cerradas: los Â«95Â» de hoy son 42 partidos en cuarentena de la base v1.x + 53 sin conteos extendidos, y las rotaciones pendientes son 9, no 562. Con el contrato vigente se aceptan 86 (41 de 2025-26) y los 1.869 participantes coinciden con una fuente independiente; 9 se quedan en cuarentena (siete con minutos `:60` que no se convierten, uno con el oficial sin minutos para un jugador que la base da 22,6 y uno con un 0:00 con tiros libres). GameRotation oficial devuelve 422 para 8 de 9 con ambos niveles: 1 de 9 recuperada. No se fusiona en la base de entrenamiento (+1,4 % de partidos exige reajuste con protocolo congelado). De paso se arreglÃ³ el plazo fijo de `paper_bundle` que caducaba tres pruebas por reloj. docs/nba_api_proxy_recuperacion_20261026.md.

## 2026-10-26 â€” InvestigaciÃ³n de otros modelos y factores: ninguno aÃ±ade informaciÃ³n sobre el cierre de Pinnacle
DecisiÃ³n clave: con 3 aÃ±os de origen rodante, ni pi-ratings, forma de xG, tiros, viaje, descanso, forma, motivaciÃ³n (carreras vivas) ni Ã¡rboles de gradiente mejoran al Dixon-Coles de forma fiable (solo los tiros, âˆ’0,0005 con intervalo al borde de cero) y ninguno aÃ±ade nada sobre el cierre de Pinnacle; el propio DC tampoco (+0,0004). El hueco de 0,0096 es informaciÃ³n (alineaciones, bajas, noticias), no forma del modelo. La ventaja documentada en la literatura estÃ¡ en totales, cÃ³rners y tarjetas con estadÃ­sticas de partido, pero hay 459 partidos con cierre de totales: se conserva el cierre de todos los mercados y se repite con ~2.000. Informe: `docs/investigacion_modelos_y_factores_20261026.md`.

## 2026-10-26 â€” Modelo dinÃ¡mico y prior de ascendidos medidos: el prior no tiene seÃ±al; la mezcla dinÃ¡mica gana poco y no se despliega
DecisiÃ³n clave: con 3 aÃ±os de walk-forward (12.878 partidos), el prior de ascendidos no mejora (Î”RPS âˆ’0,00002; el sesgo del Ãºltimo aÃ±o era ruido) y el Kalman del repo solo empata con el DC una vez quitada su reversiÃ³n a la media, que lo empeoraba. La mezcla log-lineal DC 270/90/730 + Kalman, con pesos ajustados en dos aÃ±os, da âˆ’0,0008 en el tercero (p95 âˆ’0,0003) y âˆ’0,0006 en los tres, mejora la calibraciÃ³n y se suma al contexto (altitud + once), pero el aÃ±o 2 queda en cero, las copas empeoran y exige un estado de Kalman diario y tres DC en producciÃ³n: no se despliega sin decisiÃ³n del titular. Informe: `docs/modelo_dinamico_y_ascendidos_20261026.md`.

## 2026-10-26 â€” NBA 1.5.0: no se recalibra el equipo; los jugadores ya no dependen de una sola captura de PropLine

La recalibraciÃ³n de total y puntos de equipo se probÃ³ con protocolo congelado (`nba_live15`) y no entra: en sus propias
lÃ­neas el modelo ya estÃ¡ calibrado en 2025-26 y el sesgo de una temporada no sirve para la siguiente (cambia de signo).
El intercepto dentro de la temporada saliÃ³ peor porque aprende de partidos predichos sin disponibilidad; aprender de las
cohortes selladas solo se puede medir hacia delante. En vivo, una captura de PropLine perdida (cuota diaria en reserva)
dejÃ³ una cohorte entera sin jugadores y las pÃ©rdidas no se sellaban nunca (menos de 2 casas). DecisiÃ³n: la lÃ­nea de una
casa sigue mandando cuando existe, y si no, el jugador de rotaciÃ³n se pronostica en el umbral estadÃ­stico sobre el que
ya estÃ¡ calibrado el modelo; asÃ­ la cobertura no depende del proveedor y no se reajusta ningÃºn parÃ¡metro.

## 2026-10-26 â€” Tenis: sellado cerca del inicio y todas las lÃ­neas de las casas

AuditorÃ­a del motor de tenis (`docs/tenis_auditoria_20261026.md`). El sellado pasa de dos veces al dÃ­a a cada hora, 1,5-2,5 h
antes del partido: el precio sin margen es la mejor entrada del ganador y es mÃ¡s preciso cuanto mÃ¡s cerca del inicio, y ademÃ¡s
un cron en hora de BerlÃ­n dejÃ³ la pasada nocturna en la hora en que PropLine no captura. Cada sellado guarda todas las lÃ­neas
ofrecidas con la probabilidad del motor en la misma lÃ­nea, porque comparar en lÃ­neas fijas no mide nada frente al mercado. Con
27 partidos con cierre, el motor bate al cierre en totales de juegos (el mercado sobrevalora el Â«mÃ¡s deÂ»): por eso solo se
ancla al mercado el ganador, no los totales. La superficie del torneo sale de la ediciÃ³n de la misma Ã©poca del aÃ±o.

## 2026-10-26 â€” Fases del Motor A medidas con el modelo nuevo: lo robusto es pequeÃ±o y no se activa nada

Con el modelo entrenado en local se repitiÃ³ la mediciÃ³n de cada fase (`docs/fases_motor_a_20261026.md`). DecisiÃ³n clave: no
activar nada. Lo Ãºnico estable en cuatro particiones de validaciÃ³n es la combinaciÃ³n altitud + impacto del once (Î”RPS âˆ’0,0007
a âˆ’0,0010, una dÃ©cima parte de los 0,0096 que separan al modelo del mercado), y hacia adelante la altitud en sombra no lo
confirma todavÃ­a (32 partidos, +0,0010, p95 +0,0057). Descanso, clima, bajas, valor del once, tres ligas mÃ¡s (la SÃ¼per Lig
queda a +0,0187 del mercado) y las correcciones de empate y de nivel de goles (âˆ’0,00007, no significativa) no pasan. Los
artefactos de sombra regenerados no se subieron: el del once vigente se ajustÃ³ con 11.920 filas y el nuevo con 4.264. Las
mediciones quedan como scripts en `scripts/entrenamiento_local/` para repetirlas tras cada reentrenamiento.

## 2026-10-26 â€” El Motor A se entrena en local y se sube

DecisiÃ³n del titular: el entrenamiento se hace en local y luego se sube (`scripts/entrenamiento_local/`). La copia
trae solo las 19 tablas que lee `train.py` a un esquema `entreno` aparte, para no tocar la base local de pruebas. La
configuraciÃ³n del modelo se fija a la del worker, no a la del `.env` local, que tenÃ­a otra vida media (180 frente a
270 dÃ­as): sin eso se habrÃ­a entrenado y subido un modelo distinto del que se cree. Se sube solo lo que la misma puerta
de `train.py` deja activo. Como esa puerta casi nunca puede comparar con el modelo anterior (la ventana cambia con
cada dato nuevo), antes de subir se compara tambiÃ©n sobre los partidos fuera de muestra comunes. El entrenamiento
tarda ~2 min desde el gradiente exacto del 22-oct (antes 4 h 44 min).

## 2026-10-25 (noche) â€” Aviso Â«sin pronÃ³stico selladoÂ» en el detalle del partido

El titular leyÃ³ Â«No hay pronÃ³sticos publicadosÂ» encima de 25 mercados y lo tomÃ³ por un fallo. No lo era (pronÃ³stico =
pick sellado; los mercados son estimaciones del modelo al momento), pero el texto inducÃ­a a error. DecisiÃ³n: con
mercados debajo, el aviso dice que no hay pronÃ³stico **sellado** y que abajo estÃ¡n las estimaciones del modelo (o que
estÃ¡n con VIP si todos llevan candado); sin mercados se mantiene el aviso de siempre. No se mezclan los dos conceptos:
un mercado del modelo nunca pasa a contar como pronÃ³stico publicado.

## 2026-10-25 (noche) â€” Alta probabilidad: solo pronÃ³sticos con cuota

DecisiÃ³n del titular tras ver Â«LAFC +1,5 asiÃ¡tico @â€”Â» en la app: no se publica ningÃºn pronÃ³stico sin cuota de una casa
de los suscriptores. HabÃ­a dos causas. La primera: la selecciÃ³n tomaba la Ãºltima captura de PropLine, y casi todas las
horas trae solo a Pinnacle (las casas llegan cada ~3 h). La segunda: el modelo proponÃ­a lÃ­neas que nadie ofrece; el
+1,5 de LAFC no lo cotizÃ³ ninguna casa, ni Pinnacle, en 49 capturas. Ahora `_snapshot` elige la captura mÃ¡s reciente
(â‰¤ 6 h) que trae a Pinnacle y a alguna casa de los suscriptores, y los candidatos sin cuota se descartan antes de
elegir. AsÃ­ el partido se queda con el siguiente que sÃ­ cotiza, en vez de perder el pronÃ³stico o publicarlo vacÃ­o.
Repetido en seco sobre el 25-oct: alta 5/28 â†’ 27/27 con cuota; ampliada 62/385 â†’ 303/303. Lo ya sellado no cambia
(es inmutable). La escalera y el parley comparten `_snapshot` y `_referencias`, y ganan las mismas cuotas.

## 2026-10-25 (noche) â€” Tarjetas a cero de FotMob: manda la cronologÃ­a

El titular vio Â«menos de 6,5 tarjetasÂ» al 100 % (media 1,7) en Independienteâ€“Boca. Causa: en Argentina, Brasil y parte
de MÃ©xico FotMob deja el bloque de tarjetas en `[0, 0]` en 2026, y el relleno lo tomÃ³ por dato vÃ¡lido (~790 partidos).
DecisiÃ³n: no descartar FotMob para tarjetas, sino leer su cronologÃ­a cuando el bloque viene con las cuatro a cero; la
cronologÃ­a, sin las tarjetas al cuerpo tÃ©cnico, coincide con API-Football en ~92-97 % de amarillas. Solo se toca el caso
medido (amarillas del bloque a cero; a veces trae la roja y deja las amarillas en cero, por eso la condiciÃ³n mira solo
las amarillas): con el bloque con datos se respeta, para no cambiar la convenciÃ³n del historial. Si la
cronologÃ­a no es fiable, NULL antes que un cero que no consta.

## 2026-10-25 (noche) â€” Resultado al pitido con la primera fuente disponible

DecisiÃ³n del titular: la app muestra el marcador final al pitido y el resultado se cierra con la fuente que lo tenga
primero. FotMob lo tiene a los ~5 min (el vivo ya lee su listado); PropLine, a las 3-6 h. Por eso el vivo cierra al
pitido con las validaciones del respaldo (mismo partido, mismos equipos, `FT`) y no se adelanta nada mÃ¡s: cÃ³rners,
tarjetas y estadÃ­sticas siguen con SofaScore como fuente principal, porque sus recuentos no coinciden con los de otras
fuentes (las amarillas de BetsAPI difieren hasta un 45 %) y mezclar fuentes por llegar antes falsearÃ­a el Motor C.
PrÃ³rroga y penaltis quedan fuera: el marcador de los 90 minutos sale de otra fuente.

## 2026-10-25 (noche) â€” AuditorÃ­a de motores y datos: lo que quedÃ³ parado con el cambio de fuente

Orden del titular: auditar los tres motores y las fases del A, comprobar vivo, cierres y completitud, y arreglar en el
momento (`docs/auditoria_motores_datos_20261025_noche.md`). Lo que se encontrÃ³ no eran datos que faltaran, sino
consumidores que seguÃ­an esperando la forma de The Odds API: la sombra del XI solo aceptaba `post_xi` (PropLine nunca lo
fabrica, y no debe) y el lector de cuotas solo miraba alias `odds_api`. DecisiÃ³n: adaptar el consumidor (foto horaria
posterior al XI, â‰¤ 75 min, â‰¥ T-15) en vez de inventar etiquetas en la ingesta. ERA5 no estaba roto por datos: Copernicus
rechaza las peticiones simultÃ¡neas de una cuenta; de una en una salen todas. La API llevaba cÃ³digo de antes del 22-oct
porque la imagen `3babeb4` se construyÃ³ sobre la API anterior en vez de sobre `main`: se despliega entera desde `main`.
El chequeo de salud mira ahora el dato (cierres, cobertura de xG, once) y no solo la Ãºltima fecha, que es lo que lo dejÃ³
en verde con 3 dÃ­as sin cierres.
Cuota de PropLine (5.000/dÃ­a, reserva 500): ~40 % se iba en competiciones sin motor y la liquidaciÃ³n de fÃºtbol en el orden
del catÃ¡logo; por eso faltaban cierres de la Premier y se cortaban las pasadas de la noche UTC. DecisiÃ³n: no dejar de
archivar esas competiciones (observaciones originales para el futuro), solo bajarlas a cada 6 h y liquidar solo las
nuestras; NBA y tenis no cambian.

## 2026-10-25 â€” ClasificaciÃ³n y vivo sin API-Football; regla de arreglar al momento

Pregunta del titular: Â¿por quÃ© cada auditorÃ­a deja mÃ¡s pendientes? Porque eran de solo lectura (apuntaban sin cerrar), los
cambios de fuente abrÃ­an huecos nuevos y el punto de entrada estaba desactualizado (F7 figuraba Â«sin empezarÂ» y corre cada
5 min). Regla nueva del titular: el error que aparece al desplegar o probar se arregla en la misma sesiÃ³n; `PENDIENTES.md`
solo guarda lo que depende de Ã©l o de una fecha o muestra. Ya no hay ninguna pausa del motor.
ClasificaciÃ³n: se calcula con nuestros resultados en vez de pedirla a SofaScore (dinero) o PropLine (no la tiene). Contra
la Ãºltima foto de API-Football (22-oct 06:40) coincide equipo a equipo en las 19 ligas salvo una sanciÃ³n de puntos
(Southampton âˆ’4), que va a mano en `SANCIONES`; la forma de API-Football iba del mÃ¡s reciente al mÃ¡s viejo. Las
eliminatorias se excluyen con el tope de partidos de fase regular por equipo, no adivinando la jornada. Vivo: FotMob y no
PropLine `/scores`, porque PropLine cobra cada consulta del presupuesto diario compartido y ese dÃ­a quedaban 1.237 a las
17:12 UTC frente a ~1.330 que necesita la captura horaria hasta medianoche; FotMob da todos los partidos del dÃ­a en una
peticiÃ³n. Trampa vista: `docker compose cp worker` tambiÃ©n apunta al contenedor de la captura de PropLine; usar
`docker cp quantfut-worker-1`.

## 2026-10-25 â€” Cierres de PropLine, Liga MX/MLS en SofaScore y `stats` desde SofaScore y FotMob

Orden del titular tras la auditorÃ­a de datos: arreglar lo que falla y usar FotMob para completar. DecisiÃ³n clave: el
cierre de PropLine llega horas DESPUÃ‰S del partido, y la liquidaciÃ³n con CLV es inmutable; cargar los cierres sin mÃ¡s
habrÃ­a dejado igual la sombra y la puerta comercial, porque los resultados se liquidan antes. Por eso la liquidaciÃ³n
(picks, sombra sharp y sombra XI) espera al cierre sharp hasta 48 h (`cierre.cierre_o_vencido`). Cada lÃ­nea del cierre
trae su propia hora y el de-vig exige un Ãºnico momento por grupo: todas se fechan en el Ãºltimo instante en que todas
seguÃ­an a la vista (â‰¤ 10 min del inicio); ensayo en producciÃ³n: 79 partidos, 25.437 filas, diferencia mediana con la
Ãºltima foto horaria 0,7 puntos y ningÃºn lado invertido. Liga MX pedÃ­a el torneo del Clausura (vacÃ­o) y la MLS en
eliminatorias trae `round: null`: el recolector abandonaba sin avisar; ahora lista sin jornada. `matches.stats` vuelve a
llenarse (fichas de la web y faltas/centros para el Motor C) desde SofaScore y, si falta, FotMob; solo donde estÃ¡ NULL.
Los 10 fallos del arnÃ©s local son de entorno (Postgres sin contraseÃ±a en el worktree); en CI pasan.

## 2026-10-25 â€” AuditorÃ­a de datos de los tres motores (PropLine, SofaScore, BetsAPI)

Pedido del titular: comprobar si los motores reciben bien los datos nuevos, si hay cierres y alineaciones, si se sigue lo
recomendado en los documentos del 15-oct, quÃ© ligas estÃ¡n completas para entrenar y quÃ© data disponible conviene acoplar.
Solo lectura. DecisiÃ³n clave: el cuello de botella de los cierres no es la fuente sino la carga. El archivo de PropLine ya
guarda `/odds/closing` de 185 partidos del 21 al 25-oct (Pinnacle 1X2 a una mediana de 11 min del inicio, con cÃ³rners y
tarjetas), pero nada lo pasa a `odds_snapshots`: sin cierres desde el 22-oct 18:50, la puerta de frescura del
reentrenamiento pasa el 1-nov y falla hacia el 21-nov. Otros hallazgos: SofaScore no tiene ningÃºn evento de MLS ni Liga MX;
bajas y once llegan pero ningÃºn motor los lee; las estadÃ­sticas de SofaScore no llegan a `matches.stats`; casi no hay
cierres histÃ³ricos de totales, cÃ³rners ni tarjetas (0â€“6 %). BetsAPI (~25.600 partidos desde jul-2023) tiene xG con r â‰ˆ
0,95â€“0,97 frente al nuestro y cuotas bet365 de 8 mercados, pero sus amarillas no coinciden con las nuestras (55 % en
Brasil/Argentina), su recepciÃ³n original es desconocida y la licencia no estÃ¡ leÃ­da: acoplar en tabla propia, no encima de
lo sellado. docs/auditoria_datos_motores_20261025.md.

## 2026-10-25 â€” Limpieza de pendientes y fin de la pausa del motor

En 12 dÃ­as se cerraron 297 tareas, pero las abiertas pasaron de 128 a 250: cada auditorÃ­a apuntaba ideas al mismo nivel
que los fallos, y los cambios de fuente dejaban tareas muertas. Se cerraron 134 en su sitio con el motivo (hechas,
duplicadas, de fuentes o ligas retiradas, estados viejos de NBA) y quedan 116 con un Ã­ndice al principio de
`harness/tareas.md`: 3 fallos (los cierres de PropLine se resolvieron el mismo dÃ­a en el PR #127), 27 del titular,
31 en espera, 55 mejoras. Regla nueva: solo bloquea lo que hace
perder dinero o datos. El mismo dÃ­a el titular levantÃ³ la pausa del motor hasta el 1-nov: se toca cuando convenga,
sin desplegar el worker durante el reentrenamiento del 1-nov.

## 2026-10-25 â€” Respaldo de resultados con FotMob

PropLine deja partidos sin resultado (`expired`: toda la liga suiza, y partidos sueltos de Noruega, TurquÃ­a, MLS, y
Hoffenheimâ€“Lyon con alta probabilidad, escalera y parley), y sin resultado no se liquida ningÃºn producto: habÃ­a 19
atascados en ligas activas. FotMob ya estÃ¡ reactivado, asÃ­ que cierra esos partidos tras 6 h (dos pasadas de PropLine).
Solo con `reason.short == 'FT'` (prÃ³rroga y penaltis cambian el marcador de los mercados a 90 min) y con los dos
equipos en el mismo orden por `fotmob_equipo`; lo demÃ¡s se queda abierto para revisiÃ³n manual en vez de adivinar.

## 2026-10-25 â€” Quedan 15 ligas + 2 copas; FotMob vuelve como complemento diario

Orden del titular tras medir la cobertura combinada de PropLine y SofaScore
(`docs/cobertura_ligas_propline_sofascore_20261025.md`): fuera Serie B, LaLiga 2, Allsvenskan y Super League suiza
(db/088, mismo trato que db/086: `active=false`, historial intacto, sin `retired_leagues`). FotMob se reactiva el mismo
dÃ­a que se habÃ­a retirado, pero como complemento: el nuevo paso `completar` solo rellena NULL y espera 36 h desde el
saque, porque el detalle de SofaScore llega con p90 de 19 h y mÃ¡ximo de 33 h; sin esa espera FotMob (captura a las
~2,5 h) se adelantarÃ­a siempre y dejarÃ­a de ser complemento. Su xG entra como primera pareja vÃ¡lida con la hora real
de captura de la pÃ¡gina. Championship, 2. Bundesliga, TurquÃ­a y Noruega se aÃ±aden al recolector SofaScore: sin
API-Football se habrÃ­an quedado sin xG. Desplegado el 25-oct (worker `e5a29a7`). La 088 se aplica de forma
programada a las 22:30 UTC y no al desplegar: `results.py` solo cierra partidos de ligas activas, y desactivarlas
antes habrÃ­a dejado sin liquidar los productos del dÃ­a en esas ligas.

## 2026-10-25 â€” Bajas y once desde SofaScore

Al retirar API-Football y FotMob los pronÃ³sticos quedaron sin bajas ni once. SofaScore (rl1987 `event_detail` con `includeLineups`) trae en partidos futuros el once previsto (`confirmed=false`) y las bajas con tipo, motivo y fecha de regreso, asÃ­ que no hace falta otra fuente. DecisiÃ³n clave: el once previsto va a una tabla propia (`lineups_previstas`) y SOLO el oficial y completo se copia a `lineups`, porque `sello_tardio` lee esa tabla como Â«alineaciÃ³n confirmadaÂ» y un previsto la falsearÃ­a y adelantarÃ­a el sellado. Los ids de SofaScore no son los de API-Football: cada titular lleva `src` y `availability()` solo compara contra historia de su fuente, asÃ­ que de momento da Â«insuficienteÂ» en vez de decir que faltan todos los habituales. Las bajas se guardan pero aÃºn no alimentan al modelo (antes tampoco: solo las fichas). Desplegado el 25-oct (PR #118, worker `117feb7`, migraciÃ³n 087).

## 2026-10-25 â€” Fuera del cron las tareas de API-Football, FotMob, PitchAPI y worldfootball

Orden del titular: en el servidor solo deben correr las fuentes nuevas. Se comentan (prefijo Â«RETIRADOÂ», reversible) 14
tareas: bajas, alineaciones, clasificaciÃ³n, en vivo, xG, cuotas y calendario de equipos de API-Football; las tres
capturas de FotMob y sus sedes; el respaldo de PitchAPI; xG y copas de worldfootball/FBref. Quedan sin fuente hasta
conectar SofaScore/PropLine: bajas, once previo, clasificaciÃ³n y marcador en vivo; el sello por partido sigue a T-38 sin
once. El chequeo de bajas deja de alarmar con `RESULTS_PROVIDER=propline` porque no informarÃ­a de nada nuevo.

## 2026-10-25 â€” Ligue 2 y Superliga danesa fuera de los motores; fuentes: solo SofaScore y PropLine

El titular fijÃ³ las fuentes: SofaScore vÃ­a Apify (actor por deporte del 24-oct: rl1987 fÃºtbol, scrapesage NBA y
tenis) y PropLine; ya no API-Football ni FotMob. PropLine no cotiza Ligue 2 ni la Superliga danesa, asÃ­ que el titular
las retirÃ³ (db/086). Se desactivan en vez de borrarlas como Chile y Brasil B: tienen 205 pronÃ³sticos de alta
probabilidad, 7 patas de escalera/parley y 55 ofertas en sombra sellados, y borrar historial sellado necesita una
autorizaciÃ³n aparte. Tampoco entran en `retired_leagues`: su trigger rechazarÃ­a cualquier UPDATE de los partidos que se
conservan. `RETIRED_LEAGUES` impide reimportarlas desde archivos. El recolector SofaScore de este PR se rehÃ­zo sobre la
versiÃ³n por deporte que corrÃ­a en el servidor y no estaba en `main`; desplegar la de `main` habrÃ­a devuelto NBA y tenis
a rl1987.

## 2026-10-25 â€” Resultados y calendario desde PropLine; xG desde SofaScore

API-Football volviÃ³ al plan gratuito el 22-oct y el titular eligiÃ³ sustituirlo en vez de renovarlo. Se lee lo que ya
capturan los recolectores (cero peticiones nuevas). El emparejamiento es lo delicado: PropLine escribe los clubes de otra
forma y a veces publica el mismo cruce al revÃ©s o dos veces. Por eso un evento se enlaza solo si los DOS equipos se
parecen, a Â±36 h y como Ãºnico candidato (entonces se aprenden los alias, fuente `propline`, no `odds_api`), y un
partido nuevo solo se crea con nombres exactos y sin el cruce ya presente en ningÃºn sentido. SofaScore exige ademÃ¡s el
mismo marcador: es la comprobaciÃ³n independiente de PropLine. Casas nuevas de PropLine solo a â‰¤ 48 h y cada 3 h por
volumen (~100 MB/dÃ­a si no). Ensayo en seco en producciÃ³n: 83 cierres de 111 pendientes, 61 alias aprendidos todos
correctos, 3 altas, 10 cruces invertidos rechazados; 15/15 detalles SofaScore con marcador igual.

## 2026-10-24 â€” AuditorÃ­a de fuentes y backtest: no recalibrar el Motor A

El titular pidiÃ³ calibrar y validar los tres motores con la data nueva. No se calibrÃ³ ni reentrenÃ³ nada: la data nueva aÃºn
no estÃ¡ en las tablas (PropLine solo entra como cuota horaria desde el 24-oct; cierres, box score y SofaScore solo en el
archivo) y los resultados estÃ¡n parados desde el 22-oct por el plan gratuito de API-Football. El backtest con ventana
creciente muestra que el A estÃ¡ calibrado (la mejor recalibraciÃ³n coherente da Î”RPS âˆ’0,00016, en el lÃ­mite del ruido) y
que su brecha con el cierre es de informaciÃ³n: peso Ã³ptimo en la mezcla 0 y Kelly con P_modelo > P_mercado âˆ’11 % (IC95
âˆ’15/âˆ’7). Recalibrar serÃ­a ajustar ruido. Lo urgente son las fuentes: plan de API-Football, worker con dos archivos viejos
y cierres de PropLine sin cargar. Detalle: `docs/auditoria_motores_20261024.md`.

## 2026-10-24 â€” Tenis: cuotas del archivo de PropLine, sin The Odds API

El titular pidiÃ³ conectar el motor de tenis al archivo compartido. Se hizo con un paquete nuevo (`tennis_odds_propline_v1`) en vez de
modificar `tennis_odds_live_v1`: el protocolo v8 congela el hash de ese cÃ³digo y tocarlo invalidarÃ­a su carga. Solo cuenta la observaciÃ³n
horaria mÃ¡s reciente (mÃ¡ximo 65 min), no la ventana de 36 h de antes: con una foto por hora no hace falta tirar de precios viejos. Se
retirÃ³ la foto de The Odds API del cron en lugar de dejarla como respaldo, por la decisiÃ³n del 23-oct (sin fallback ni peticiones
duplicadas). Si la pareja sale dos veces en la misma observaciÃ³n no hay mercado: es preferible caer al apilador v7 que adivinar.

## 2026-10-18 (noche) â€” Candados difuminados: el botÃ³n VIP va a la tienda en la app, a Whop en la web

El titular pidiÃ³ los pronÃ³sticos bloqueados difuminados con un botÃ³n Â«Acceso VIPÂ» hacia la pasarela. Lo gratis (4 / 1 / 1) ya era lo que aplica el
cÃ³digo. El difuminado es seguro porque el servidor nunca manda la selecciÃ³n ni la probabilidad de lo bloqueado; la franja son bloques, no un
pronÃ³stico falso. En la app el botÃ³n abre la pantalla VIP que compra con Play / App Store y no enlaza a Whop: las tiendas exigen su sistema de
compras para suscripciones digitales dentro de la app y un enlace de pago externo puede costar el rechazo de la ficha. Whop cubre la web, que no
pinta pronÃ³sticos reales bloqueados. Ventana de sello y fecha de corte de F7 siguen sin responder: quedan como propuesta.

## 2026-10-18 (tarde) â€” FotMob en vivo como fuente previa; Open-Meteo descartada por licencia

El titular autorizÃ³ la captura recurrente de FotMob (antes registrada como puntual) y entregÃ³ el token de Copernicus. La pÃ¡gina
previa de FotMob trae alineaciÃ³n probable, no disponibles con tipo y pronÃ³stico de clima con hora de actualizaciÃ³n: cubre las
bajas previas y el pronÃ³stico de F6 con una sola fuente, point-in-time, sin la clave de Open-Meteo. No se usÃ³ el plan gratuito de
Open-Meteo porque el producto vende suscripciones (uso comercial) y el titular habÃ­a contratado el plan de pago; si se quiere esa
fuente, se carga la clave de pago. Las ventanas de captura previa se estrecharon (70 y 40 min) porque una ventana de 30 a 120 min
habrÃ­a tomado la alineaciÃ³n antes de que se publique la oficial. ERA5 se valida contra el clima que midiÃ³ FotMob (temperatura 0,98).
La captura se detiene 12 h ante cualquier HTTP 401/403/429 y no evita controles de acceso.

## 2026-10-18 â€” Datos al motor: tablas propias por fuente, nunca mezclar identificadores

El archivo de FotMob (20.331 partidos) pasÃ³ a tablas con `match_id` en lugar de volcarse en `lineups_historicas` y
`estadisticas_jugador`: esas llevan ids de API-Football y mezclar los dos espacios habrÃ­a roto `player_ratings` y
`lineup_challenger` sin dar ningÃºn error. El puente (7.834 jugadores) y la equivalencia de Ã¡rbitros (54) son tablas aparte, con
umbral de coincidencia y 1 a 1 en las dos direcciones. Hallazgos que cambian el plan: el original de FotMob ya trae entrenador,
valor de mercado, asistencia y clima (40 %, medido en el partido); el calendario completo de API-Football muestra un partido
intermedio que `matches` no ve en el 17,6 % de los equipo-partidos; el cruce de Ã¡rbitros apenas suma porque las fuentes casi
no se solapan. No se montÃ³ captura diaria de FotMob porque la descarga se registrÃ³ como puntual: lo decide el titular.
Una mediciÃ³n propia, cancelada desde el cliente, siguiÃ³ ejecutÃ¡ndose 38 minutos en el servidor: cancelar en la base, no solo
en el cliente. La suite completa tiene fallos previos que no son de estos cambios.

## 2026-10-18 â€” Orden de identidades: el error real es Arsenal, no las 379 "identidades"

Medido en producciÃ³n sin escribir nada. Las 379 "identidades" de copas eran partidos (110 equipos); en ninguno estÃ¡n los
dos equipos identificados, porque el rival es siempre un club de una liga que no cubrimos, y la regla de `eu.ucl`/`eu.uel`
(no dar de alta equipos, solo coincidencia exacta) es la que lo impide: se cierra como no resoluble por diseÃ±o. La coincidencia
aproximada habrÃ­a dado Pafosâ†’Paris FC y Rangersâ†’Angers. Lo que sÃ­ estaba mal es una fila de alias (`Arsenal`, `fbref`) que apunta a
Arsenal de SarandÃ­: 33 partidos de copa hasta 2024-12-11 en el club equivocado. Antes de afirmar su efecto en el modelo habrÃ­a que
medirlo (se espera pequeÃ±o por el decaimiento de 180 dÃ­as). Cuatro alias de The Odds API recuperan 39 de los 103 cierres de copa con
los snapshots ya pagados. Nada de esto se aplica sin visto bueno; ver docs/ordenar_identidades_20261018.md.

## 2026-10-16 â€” Tenis: extracciÃ³n completa, motor local y resultados negativos conservados

Por autorizaciÃ³n nueva se completaron 171 archivos TML y 43 archivos MCP:
214/214, 593.347.344 bytes, cero fallos y hashes/tamaÃ±os verificados. TML se
consolidÃ³ en 492.251 partidos (249.938 aptos para el candidato), con 15 conflictos
de identidad apartados y 3.923 filas invÃ¡lidas conservadas en cuarentena.
MCP permanece como archivo de investigaciÃ³n y no alimenta los modelos ajustados.

CÃ³digo aislado en el checkout gestionado tennis-engine, apps/tennis. Binomial
de saque/resto por rival/superficie, priors gaussianos, MAP/Laplace y ponderaciÃ³n
de antigÃ¼edad; no es todavÃ­a un modelo dinÃ¡mico de estados. Markov conserva
saque/distribuciÃ³n conjunta y resuelve deuce/tie-break sin truncaciÃ³n. Dos
candidatos actuales: ATP 74.029 partidos y WTA 20.614, historia desde 2018 y
embargo de 35 dÃ­as por fechas semanales. Consultas hipotÃ©ticas con incertidumbre.

EvaluaciÃ³n anual congelada 2025/2026: candidato inferior a Elo en log-loss.
2026 ATP 0,64466 vs 0,62855; WTA 0,65296 vs 0,62177. HÃ¡ndicap Aâˆ’3,5 mejora
frecuencia de entrenamiento; totales 22,5 no. Sin cuotas/ROI/CLV ni promociÃ³n.
El test 2026 ya observado no se usarÃ¡ como nueva prueba intacta tras ajustes.

17 pruebas especÃ­ficas aprobadas. ArnÃ©s inicial/final 1.300 pasadas, 88 omitidas;
Docker no disponible. El primer arnÃ©s del checkout sin .env fallÃ³ nueve pruebas
heredadas de BD; se diagnosticÃ³ y repitiÃ³ completo con configuraciÃ³n existente
cargada solo en memoria, sin cambiar esos motores. Datos/recibos/modelos en
data/tennis/full_20261016; informe docs/tenis_primera_version_y_resultados_20261016.md.
Sin despliegue, apuestas ni consumo de The Odds API/ZenRows. Pendientes: tiempos
reales y agenda/IDs, calibraciÃ³n y prueba prospectiva, casas/presupuesto de cuotas.

## 2026-10-16 â€” Tenis: fuentes propuestas verificadas y muestra TennisMyLife

gmalbert actualizado 16-oct, commit 3d132eec; su pipeline central es clasificador de
ganador, selecciÃ³n por accuracy de test y Elo de referencia 0/1. El scraper
Flashscore revisado deja saque/resto nulos. No se ejecutÃ³ ni incorporÃ³ ese cÃ³digo.
panaC es Node/Puppeteer con Ãºltimo commit de 2018. Live Tennis API enlaza SDK GitLab;
FREE para agenda/estado, estadÃ­sticas detalladas ULTRA segÃºn documentaciÃ³n.
TennisMyLife directo aporta seis muestras 2026/en curso, 11.364 filas; conteos y
hashes conservados en .local/tennis_sources_20261016/. MIT declarada por la fuente;
WTA con aviso de fiabilidad en revisiÃ³n. Fecha de torneo no es hora de partido,
claves repetidas y enlace entre fuentes pendientes. Dos CSV iguales a gmalbert y
blobs Git verificados. Sin cuentas/compras, cuotas API o proxy, entrenamiento ni
despliegue. Informe: docs/tenis_fuentes_y_repositorios_20261016.md.

## 2026-10-16 â€” Tenis: Match Charting Project auditado para investigaciÃ³n

El usuario eligiÃ³ The Odds API para cuotas y JeffSackmann/tennis_MatchChartingProject
para datos. Descarga directa, sin proxy ni crÃ©ditos API, fijada al commit
1813a1309b7ed7ebf1c7e884b32bf675d00e4edf. Los 1.877.757 registros de puntos se
contrastaron con Overview; S/R son puntos con ganador conocido sin detalle y
P/Q son penalizaciones, segÃºn las instrucciones originales leÃ­das sin macros.
No confundir exclusiÃ³n de esos cÃ³digos en Overview con inconsistencia de resultados.
Superan los controles iniciales 7.501 partidos masculinos y 4.237 femeninos:
23.476 observaciones de investigaciÃ³n. Conservados originales y cuarentena.
Las fechas mÃ¡ximas son 21-may y 9-sep-2026; la muestra seleccionada por colaboradores
no basta para actualizaciÃ³n diaria. CC BY-NC-SA 4.0: permiso comercial sin acreditar.
DiseÃ±o y lÃ­mites en docs/tenis_modelo_y_datos_20261016.md y
data/tennis/mcp_20261016/AUDIT_README.md. Sin entrenamiento ni despliegue.
VerificaciÃ³n independiente con pandas reproduce las 23.476 observaciones;
arnÃ©s inicial y final: 1.300 pruebas pasadas, 88 omitidas y cero fallos.
Docker no disponible: se omitiÃ³ la validaciÃ³n de Compose.

## 2026-10-15 â€” Plan de mejora de los tres motores: el contexto tiene que llegar a los picks

El documento de recomendaciones del usuario se contrastÃ³ con el cÃ³digo: F1â€“F7 ya
cubren XI, bajas, Ã¡rbitro, clima/sede y la revisiÃ³n con el once; el anclaje de B
usa 1X2 mÃ¡s la lÃ­nea de goles con Ï fijo (identificable) y parley/escalera no
repiten partido. Lo que faltaba es el porquÃ© de fondo: los picks vendidos salen
de B, asÃ­ que mejorar A sin una mezcla aprendida (F8) no cambia nada vendido, y
una probabilidad mejor no prueba un pick mejor sin evaluarlo a volumen constante
(F9). Por eso F9 va antes que F8 y ambas antes de F3â€“F6. Medido en producciÃ³n:
alta probabilidad acierta lo prometido pero pierde a cuota de referencia
(âˆ’3,0 % base, âˆ’7,5 % ampliada); es la lÃ­nea de acierto decidida el 2026-10-05, y
solo informaciÃ³n ajena al mercado puede cambiar ese signo. Por decisiÃ³n del
usuario no se toca el motor antes del 1-nov. Spec:
docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md.

## 2026-10-15 â€” RevisiÃ³n del plan: A se juzga contra B del mismo momento

La revisiÃ³n del usuario corrige el orden: F8 se evalÃºa en paralelo con F9 y se
activa al final, porque una mezcla no evita el doble conteo por sÃ­ sola y ganar a
un B de las 03:00 puede ser solo ventaja de hora (F7). Por eso F9 separa el efecto
del horario, del modelo y de la selecciÃ³n. La regla Â«â‰¥2 ligasÂ» queda como filtro
inicial: con muchas variantes probadas hace falta magnitud, estabilidad y
registro de lo probado. Descanso/calendario sube por coste bajo. Hallazgo de
datos: el archivo FotMob ya trae XI, minutos, bajas, entrenador, ronda y estilos
de 2024 en adelante (sin pasar a las tablas del motor, donde el XI estÃ¡ al 0 %
antes de 25-26); lo que de verdad falta descargar es el calendario de copas y
otras competiciones, altitud y ERA5. El 91/223 con cuota de referencia estÃ¡
sesgado porque doble oportunidad y hÃ¡ndicap se capturan desde el 12 y 14-oct. No
se compran cuotas histÃ³ricas a T-60 (â‰ˆ14.000â€“31.000 crÃ©ditos por temporada): se
evalÃºa hacia delante con la captura propia.
## 2026-10-15 â€” Tres parejas xG de 365Scores cargadas por peticiÃ³n del titular

La discrepancia horaria de Granadaâ€“Albacete no impide identificarlo: el archivo
FotMob 4521823 tambiÃ©n sitÃºa el partido a las 18:30 UTC y coincide en equipos y
marcador 1â€“2. Se conservÃ³ el kickoff canÃ³nico 19:30 UTC; no se corrigieron fechas
como efecto lateral de cargar xG. Los endpoints de 365Scores tampoco siempre
serializan igual sus relojes: ambos originales y la discrepancia quedan guardados.

Tres parejas en `matches`, tres detalles en `historical_football_matches` y tres
estadÃ­sticas en `historical_football_observations`, fuente `365scores`. Se usa la
recepciÃ³n real del 15-oct-2026, para que el dato no entre en cortes anteriores.
Respaldo solo de los tres registros en el servidor, ensayo revertido, repeticiÃ³n
con cero escrituras y lectura independiente tras commit. Hashes de seis originales
verificados; resto de partidos, archivo previo, modelo, flags, sellos y triggers
conservados; API 200. Huecos 1.222â†’1.219 (LaLiga 2: 236â†’233).
No se desplegÃ³ cÃ³digo de aplicaciÃ³n ni se reentrenÃ³. Evidencia e instrucciones
de reversiÃ³n: `docs/lanusstats_carga_20261015.md` y `data/xg_recovery/20261015_lanusstats/carga/`.
ArnÃ©s previo y final: 1.251 pruebas pasadas y 66 omitidas, sin fallos.

## 2026-10-15 â€” LanusStats/365Scores aporta xG en la muestra de LaLiga 2

Prueba autorizada con LanusStats 2.1.13 aislado: tres de nueve huecos aportan
parejas de xG, todos de LaLiga 2; los tres de Serie B y tres de Ligue 2 tienen
estadÃ­sticas sin xG publicado en las respuestas consultadas. Control positivo
LanÃºsâ€“UniÃ³n 2,22â€“0,64. Acceso directo HTTP 200: no hizo falta proxy y no hubo
consumo de ZenRows. No confundir ausencia de un campo con bloqueo de acceso.

Se separÃ³ explÃ­citamente xG (`statistics.id=76`) del xG recibido (77) y xGOT
(79), con pares completos por ID de equipo; sin estimaciones ni ceros de relleno.
Originales/hash/recepciÃ³n real e identidad comprobados. Granadaâ€“Albacete tiene
una hora de discrepancia, seÃ±alada sin corregir la base. Los nueve casos son
una muestra de los 1.222 pendientes; se localizaron 32 candidatos por calendario/
enfrentamientos, no se descargaron 1.222 detalles. Sin importaciÃ³n ni cambios
del motor. Entrega verificable en data/xg_recovery/20261015_lanusstats/.
ArnÃ©s previo y final correctos: 1.251 pruebas pasadas, 66 omitidas. Paquete de
46 archivos verificado por hash y revisado para excluir credenciales.

## 2026-10-15 â€” Carga autorizada de OddsPapi: cierre utilizable y referencia separados

Confirmados 2.918 cierres reconstruidos (8.754 cuotas), mÃ¡s 25 referencias solo
en procedencia. Se cotejaron los 2.943 originales completos y las identidades
actuales, sin cambios ni cierres previos. Se mantienen sin certificar: fuente
`oddspapi_reconstructed`, recepciÃ³n real separada y marcas de cambio originales.
Las 23 ternas antiguas y dos conflictos temporales adicionales no entran en
`odds_snapshots`: consumidores existentes podrÃ­an usarlas incluso con otra etiqueta.

Nueva procedencia inmutable `historical_odds_backfills` conserva las 2.943 y sus
extractos 1X2 verificables. Ensayo con rollback y repeticiÃ³n cero; commit con
respaldo completo de 444.756 cuotas previas. Partido/equipos/predicciones/picks/
modelo/cuotas anteriores intactos; cero violaciones temporales. Huecos desde
2024: 6.185 â†’ 3.267. Sin entrenamiento. Pruebas: 1.237/60 omitidas.

La copia local del respaldo completo fue rechazada por revisiÃ³n automÃ¡tica como
exportaciÃ³n no autorizada especÃ­ficamente; se verificÃ³ hash/CRC/cabecera COPY en
el servidor y permanece en su volumen persistente. La carga sÃ­ quedÃ³ completada.
Detalle: docs/oddspapi_carga_20261015.md; informe y estados en el paquete de OddsPapi.

ComprobaciÃ³n antes de guardar en Git: arnÃ©s correcto, 1.246 pruebas pasadas y
64 omitidas; revisiÃ³n de credenciales y recuentos del paquete sin incidencias.

## 2026-10-15 â€” OddsPapi: cola terminada, cobertura parcial

A las 03:46 de Ciudad de MÃ©xico finalizÃ³ la cola de 6.094 asociados. Resultado:
2.943 ternas Pinnacle prepartido reconstruidas (2.920 recientes, 23 para revisar),
3.151 sin histÃ³rico; ademÃ¡s, 87 sin fixture y cuatro cancelados. Quedan 3.242
de las 6.185 filas originales sin recuperar con esta API; cero consultas pendientes.
CSV final y estados en `data/pinnacle_recovery/20261014_oddspapi/`; originales
y recibos conservados en `.local/oddspapi_20261014/`. Unicidad, corte temporal,
referencias a recibos y preservaciÃ³n del original comprobados. No se cargaron
automÃ¡ticamente ni se acreditÃ³ cierre oficial. Seguimiento periÃ³dico desactivado.

## 2026-10-14 â€” OddsPapi: recuperar el historial sin introducir cuotas en vivo

Clave autorizada, cuenta gratuita con Pinnacle y cupo de 250 consultas. El
histÃ³rico no factura consultas segÃºn la documentaciÃ³n; catÃ¡logo/calendario sÃ­.
Se asociaron 6.094 de los 6.185 pendientes con 48 equivalencias revisadas y
equipos existentes. Quedan 87 de 2024 fuera de los calendarios consultados y
cuatro de 2026 cancelados en la fuente, registrados para conciliaciÃ³n.

Primer lote: 51 ternas prepartido con historial, originales y marcas de tiempo.
La descarga continua estÃ¡ en marcha sobre la cola completa, con espera mÃ­nima
de 5,15 s tras cada respuesta, cachÃ© verificable y reanudaciÃ³n. CSV y recuentos
en `data/pinnacle_recovery/20261014_oddspapi/`; estado del proceso y originales
en `.local/oddspapi_20261014/`. No afirmar que el lote ya terminÃ³: consultar
`worker_state.json` e `informe.json` antes de informar cifras actuales.

El histÃ³rico mezcla prepartido y en vivo: solo se toma Pinnacle/101/101-103,
Ãºltima cuota no suspendida anterior al menor del inicio programado y real.
Se documenta como cierre reconstruido, `close_verified=False`, sin carga
automÃ¡tica ni entrenamiento. Los 404 comprobados de enero/febrero no acreditan
una ausencia universal de esos meses. Detalle: docs/oddspapi_recuperacion_20261014.md.

## 2026-10-14 â€” Reintento OddsHarvester: comprobar el payload completo

A peticiÃ³n repetida del usuario, cuatro sesiones nuevas de ZenRows sobre dos
filas exactas (Unitedâ€“City ene-2026 y PSGâ€“Inter may-2025): cero Pinnacle. Tres
capturas acreditan en el JSON que consume la interfaz el evento, mercado 1,
scope 2 y `bookieFilter=all`; sus 8/11/8 proveedores coinciden con las filas
extraÃ­das. No era solamente el filtro del parser. PerÃº quedÃ³ limitado por
idioma y filtro, y la geolocalizaciÃ³n fÃ­sica no se verificÃ³ independientemente:
se registran los paÃ­ses solicitados, sin afirmar que sean los de salida.

Se conserva la lista con 272 candidatas previas sin verificar y 5.913 sin
candidata. No se hicieron 6.185 consultas individuales ni cargas. Nuevos
datos/recibos/manifiesto en `data/pinnacle_recovery/20261014_oddsharvester_retry/`;
detalle: docs/oddsharvester_reintento_20261014.md. El paquete del commit
43c462f permanece intacto.

## 2026-10-14 â€” PySBR/Flashscore: separar precio histÃ³rico candidato de cierre acreditado

Sobre la lista exacta `.local/cierres_faltantes_20261014.csv` (6.185 filas de
23 competiciones), OddsTrader permitiÃ³ descargar 3.624 eventos: 586 ternas
Pinnacle candidatas anteriores al inicio, 272 asociadas a pendientes con
nombres/alias o equivalencias explÃ­citas, fecha y marcador reglamentario
corroborados. Se conserva la distinciÃ³n: `currentLines` no demuestra la
integridad del historial ni el cierre final. Nueve discrepancias de marcador
(prÃ³rrogas) se excluyeron; no se arreglaron silenciosamente ni se cargaron cuotas.

PySBR original apunta a un endpoint retirado; su consulta funcionÃ³ adaptada a
OddsTrader y ZenRows residencial GB. Flashscore omkarcloud y M3MONs tambiÃ©n
funcionaron con ZenRows CL; el segundo necesitÃ³ conservar `mid` y la ruta del
mercado histÃ³rico. Las cinco ternas comunes coinciden por casa, pero ninguna
es Pinnacle. CatÃ¡logos de siete regiones y controles de 2025/2026 tampoco
aportaron la casa en las muestras. No se confunde bloqueo resuelto con cobertura.

Se entrega CSV de estado para las 6.185 filas, candidatas separadas, 5.913 sin
candidato, y cobertura/limitaciones por fuente. Las dos muestras individuales
Flashscore estÃ¡n seÃ±aladas; no se afirma haber consultado las 6.185 allÃ­.
La base y el archivo original permanecen intactos. Detalles y reproducciÃ³n:
docs/pysbr_zenrows_20261014.md y docs/flashscore_pinnacle_20261014.md.

Por peticiÃ³n posterior del usuario se guarda una copia versionada en
`data/pinnacle_recovery/20261014/`: 272 candidatas, 586 ternas totales,
lista/estados, 25 originales con sus recibos y evidencia del subconjunto
asociado. El manifiesto y atributos de Git conservan los hashes exactos.
Guardar los datos no acredita cierre final ni autoriza usarlos como tal.

## 2026-10-14 â€” RecuperaciÃ³n Pinnacle: no confundir cobertura histÃ³rica con reciente

Ensayo de lectura sobre los 6.185 cierres faltantes: 60 CSV pÃºblicos, 14.381
ternas explÃ­citas vÃ¡lidas desde 2024, TODAS ya almacenadas. MEX contiene 4.437
ternas de 4.752 filas, pero la Ãºltima es del 27-oct-2025; ARG/BRA/USA tambiÃ©n
terminan en 2025. Los 1.457 huecos de esas ligas no se recuperan reimportando
los CSV actuales. No se escribiÃ³ en producciÃ³n ni se entrenaron modelos.

OddsHarvester 0.20.0 aislado + ZenRows Browser Sessions lee pÃ¡ginas y fichas,
pero las pruebas GB/CA/CL y PSGâ€“Inter de mayo de 2025 devolvieron cero Pinnacle.
Se archivan originales y recibos; el adaptador devuelve error cuando una ficha
leÃ­da no trae ternas de la casa pedida. Pendiente fuente/acceso con cobertura
acreditada antes del lote. Incidencia de autoalta gratuita de la CLI documentada,
sin compras; las pruebas usan la clave existente. Detalle y archivos:
docs/pinnacle_recuperacion_20261014.md.

## 2026-10-03 â€” DecorrelaciÃ³n con el mercado: tampoco

Idea 4. HubÃ¡Äek y Å Ã­r (IJF 2023) entrenan con `Î£(tâˆ’y)Â² âˆ’ Î³Î£(tâˆ’m)Â²` y ganan
en la NBA contra el cierre de Pinnacle con un modelo peor que el mercado.
LeÃ­do el artÃ­culo antes de diseÃ±ar: con apuesta uniforme ellos tambiÃ©n
pierden para todo Î³; solo ganan con cartera de Sharpe. Regla fijada antes
en tareas.md. `eval/decorrelacion.py`: segunda etapa softmax sobre la
informaciÃ³n de Kalman, `m` = justo temprano de Pinnacle, walk-forward por
temporadas (prueba 2021/22-2024/25), Î³ elegido en la temporada anterior.

- Con el Î³ elegido: EV contra el cierre âˆ’3,51 % [âˆ’3,78, âˆ’3,25], 0/7 ligas,
  8.802 apuestas. Î³ fijo 0 â†’ 0,8: âˆ’3,78 % â†’ âˆ’3,46 %. Apartarse del mercado
  mejora 0,3 puntos y no se acerca a cubrir el margen de Pinnacle (~3,9 %).
- Por quÃ© no se probÃ³ la cartera de Sharpe: solo repondera las mismas
  apuestas segÃºn la ventaja estimada, y esa ventaja correlaciona âˆ’0,10 con
  el EV real (el quintil de mÃ¡s ventaja estimada da âˆ’5,1 %). PesarÃ­a mÃ¡s lo
  peor. Es la misma selecciÃ³n adversa que el README midiÃ³ en 2026-09-22.
- La correlaciÃ³n con el mercado se queda en 0,95 para todo Î³: las variables
  son las probabilidades del propio modelo, que ya se parecen al mercado.
  Decorrelar de verdad exigirÃ­a informaciÃ³n que el mercado no tenga, que es
  justo lo que falta (diagnÃ³stico del README).

Balance de las 5 ideas: 1, 2 y 4 descartadas con datos; 3 y 5 desplegadas,
las dos sobre el criterio de casas blandas, que es donde estÃ¡ la ventaja.

## 2026-10-03 â€” Stake encogido por la incertidumbre de la persistencia

Idea 5 (Baker y McHale 2013; UhrÃ­n y otros 2021). El stake era Kelly 0,20
sobre `edge Ã— persistencia`, con la persistencia tratada como conocida.
Medida con bootstrap por semanas en football-data (2 %, primera oferta por
partido): 1xBet 0,72 [0,37, 1,06], Bet365 0,13 [âˆ’0,15, 0,41], William Hill
âˆ’0,15; dispersiÃ³n entre casas 0,31. La de Bet365 no se distingue de cero.

- Factor `ÏÂ²/(ÏÂ²+SEÂ²)` por casa, multiplicado al Kelly fraccional, que se
  queda en 0,20: el 0,20 es preferencia de riesgo; el factor, estimaciÃ³n.
  Lo que cambia es el reparto entre casas, no el nivel general.
- SE en vivo por el mÃ©todo delta sobre la sombra (coincide con el bootstrap:
  Bet365 0,140 frente a 0,146), mezclado con la previa con los mismos pesos
  que `mezclar` (la previa vale 100 partidos).
- "Stake sÃ­, muestra no" (decisiÃ³n del usuario): `stake_units` de la sombra
  y `stake_kelly_units` del candidato siguen SIN factor y deciden quÃ© es
  publicable; el factor va en columnas nuevas (db/039). La puerta mide lo
  mismo que antes del cambio.
- Desplegado 18:03 UTC (respaldo `~/respaldo_20261003_stake/`). Factores
  vigentes: 1xBet 0,94, Betano 0,71, Betsson 0,65, Bet365 0,54 (la sombra
  ya la sube desde 0,43), William Hill 0. En la misma comprobaciÃ³n: las 258
  filas de The Odds API desde el despliegue de 3A traen `book_updated_at`.

## 2026-10-03 â€” Latencia de las casas blandas: empezar a medirla

Idea 3. Hoy no se podÃ­a medir: API-Football refresca cada competiciÃ³n de
golpe cada varias horas con una sola hora para todas las casas, y
`odds_worker` descartaba el `last_update` por casa de The Odds API. AdemÃ¡s
solo hay 6 capturas por partido y la sombra lleva 184 ofertas.

- 3A (gratis): db/038 `odds_snapshots.book_updated_at` + `odds_worker` la
  guarda. ADD COLUMN: el trigger de inmutabilidad sigue igual.
- 3B: `ingest/rafagas.py` cada 5 min, T-6 h a T-15 min, 1X2 con
  `bookmakers=` (10 casas â†’ 1 crÃ©dito), Premier, LaLiga y Liga MX, a
  `odds_rafagas` (tabla aparte: ventanas, sombra y cierre no la ven), una
  fila por CAMBIO de precio. Tope 3.000 crÃ©ditos/mes, contado en
  `rafagas_log` (decisiÃ³n del usuario).
- Por quÃ© 5 min bastan: `last_update` fecha cada cambio al segundo; la
  consulta solo tiene que verlo antes de que vuelva a cambiar.
- Vara fijada con el usuario: su cliente tarda UNA HORA O MÃS en apostar.
  `eval/latencia.py` mide la fracciÃ³n de ofertas que duran â‰¥60 min por casa
  (regla en tareas.md). Si una casa no llega a la mitad, sus ofertas no son
  aprovechables con el formato actual y no deberÃ­an contar para la puerta.
- Para no duplicar el emparejamiento eventoâ†’partido, `odds_worker` expone
  `match_meta` y `match_events`; las rÃ¡fagas los reutilizan.
- Despliegue: respaldo en `~/respaldo_20261003_latencia/`, migraciÃ³n
  aplicada, worker reconstruido y reiniciado despuÃ©s del cierre de los dos
  partidos de LaLiga 2 de las 16:30 UTC. Primera lectura posible tras 2-3
  fines de semana desde el 9-oct.

## 2026-10-03 â€” MÃ¡s-menos por jugador: tampoco aporta sobre el XI simple

Idea 2 de la literatura (Kharrat, McHale y PeÃ±a 2020; Hvattum): valorar al
jugador por cÃ³mo le va al equipo con Ã©l en el campo, no por sus estadÃ­sticas.
VersiÃ³n aproximada por minutos (decisiÃ³n del usuario; el diseÃ±o del 29-sep la
dejaba fuera por no tener el minuto de cada cambio). DiseÃ±o y regla fijados
antes de ver resultados en tareas.md. Mismas 3.646 filas y misma base
(`oos_2026.10.01-030007.pkl`) para los cuatro brazos:

| brazo | RPS | log-loss | ECE | ligas | valida |
|---|---|---|---|---|---|
| base | 0,21826 | 1,0516 | 0,03029 | - | - |
| XI simple | 0,21686 | 1,0471 | 0,03086 | 8 | sÃ­ |
| XI con valor | 0,21907 | 1,05448 | 0,03581 | 2 | no |
| XI con nota | 0,21808 | 1,05115 | 0,03034 | 8 | (comparaciÃ³n) |
| mÃ¡s-menos | 0,21838 | 1,05212 | 0,03324 | 4 | no |

- El mÃ¡s-menos queda en la base o un pelo peor. Con dos seÃ±ales no
  sobreajusta como "XI con valor" (18), asÃ­ que el problema no es la forma de
  medir al jugador sino que, con un aÃ±o de datos, quiÃ©n falta no aÃ±ade nada a
  cuÃ¡ntos habituales faltan.
- LÃ­mite conocido de la aproximaciÃ³n (el test lo documenta): un jugador que
  juega siempre es inseparable de su equipo; el mÃ¡s-menos solo lo mide por
  los partidos que se pierde, que son justo los raros.
- La versiÃ³n exacta (`/fixtures/events`, ~4.600 peticiones) NO se hace: era
  condicional a que esta apuntara algo.
- EjecuciÃ³n: copia aparte del cÃ³digo en `/tmp` del worker, sin reconstruir,
  reiniciar ni guardar artefactos; borrada al terminar. En el servidor sigue
  el `player_value.py` anterior: el brazo entrarÃ¡ en el reentreno mensual
  cuando se despliegue, como "XI con valor", por si la muestra cambia.

## 2026-10-03 â€” El modelo tampoco llega antes que la cuota temprana

Pregunta: `w_model = 0,0001` se midiÃ³ contra el cierre; Â¿y contra la cuota de
Pinnacle de 1-3 dÃ­as antes, que es la que se puede tomar? Regla fijada antes
de correr (tareas.md, "Ideas de la literatura" 1). `qf.eval.early_vs_close`,
Kalman secuencial con xG, 14.110 partidos de 7 ligas (2019/20-2024/25).

- Prueba principal: el movimiento tempranaâ†’cierre no va hacia el modelo.
  Pendiente 0,0028, IC95 por semanas [âˆ’0,0078, +0,0137], corr 0,006.
- Se eligiÃ³ el MOVIMIENTO y no el RPS porque no depende del resultado: con
  42.000 filas detecta pendientes de ~0,01. Control positivo para comprobar
  que la prueba no es ciega: la media de casas como "modelo" da 0,38 [0,29,
  0,46] en 7/7 ligas; Bet365, 0,16 [0,13, 0,19]. Las casas sÃ­ anticipan a
  Pinnacle; el modelo no.
- Apostar a Pinnacle temprano con â‰¥2 % de ventaja del modelo: âˆ’4,87 %
  [âˆ’5,15, âˆ’4,59] contra el cierre justo, peor que sin criterio (âˆ’3,9 %): la
  misma selecciÃ³n adversa del README. `w_model` contra la temprana: 0,0001.
- Fuga cerrada al implementar: `predict_sequential` estima nivel de goles y
  localÃ­a por liga con TODO el histÃ³rico. AquÃ­ se fijan con lo anterior al
  primer partido evaluado (`_KalmanSinFuturo`); sin eso, una pendiente
  positiva habrÃ­a sido sospechosa.
- La base local no tenÃ­a db/023 (`model_enabled`) y `load_training_data`
  fallaba: se aplicÃ³ la migraciÃ³n del repo en LOCAL. El servidor ya la tenÃ­a.

Consecuencia: la informaciÃ³n del modelo (goles + xG) no llega antes que el
mercado en ninguna ventana medible. Lo que queda de la lista son fuentes de
informaciÃ³n nueva (punto 2, mÃ¡s-menos) o del criterio sharp (3 y 5).

## 2026-10-03 â€” FotMob para histÃ³rico puntual, futuros de otra API

Alcance explÃ­cito del usuario: 23 ligas y 2 copas, desde 2024 hasta hoy.
Se interpreta 1-ene-2024 a 3-oct-2026 inclusive en America/Mexico_City.
Se aprovechan las rutas JSON documentadas en Public-FotMob-API mediante un
descargador independiente de biblioteca estÃ¡ndar; no se despliega su proxy
Django ni se aÃ±ade una fuente recurrente. Sin escritura en Postgres.

La consulta real de allLeagues confirmÃ³ los 25 IDs, y matchDetails respondiÃ³
200 con xG, eventos, alineaciones y tiros para Liverpool-Newcastle (1-ene-2024).
Inventario completo: 22.461 partidos terminados, 96 temporadas/torneos, 0
errores de calendario. La descarga de detalles queda EN CURSO, reanudable,
en `.local/fotmob-history/2024-01-01_2026-10-03/`; `coverage.json` expresa
la terminaciÃ³n real y no el Ã©xito de arranque. Captura JSON comprimido con
SHA-256/hora real, y CSV con xG ausente separado de pendiente/error. Ante
401/403/429 se detiene sin evasiÃ³n. No se presume cobertura de xG total.

ValidaciÃ³n: 573 pruebas pasan (13 nuevas sobre fechas locales, identidad,
xG total frente al del descanso, ceros/datos ausentes, cachÃ© y denegaciones).
Se ejecutÃ³ el arnÃ©s Windows real: el shell Git mÃ­nimo omite Python y no
dispone de dirname, asÃ­ que su salida OK no valida las pruebas.

CorrecciÃ³n durante la descarga: ediciones de Liga MX, Brasil y Argentina
usan IDs de torneo propios con `general.parentLeagueId` explÃ­cito. La guarda
original rechazaba esos detalles aun guardando el JSON. Se valida ahora la
liga principal declarada, manteniendo las guardas de ID, equipos y fecha.
Reanudada en segundo plano con logs y PID en `process.json`, recuperando los
detalles desde cachÃ©: Liga MX completa, 923/923 con xG. Dos respuestas de
Brasil tienen fecha distinta de su calendario y siguen como error; no se
relaja esa guarda ni se inventa la fecha. ValidaciÃ³n actual: 584 tests pasan,
14 especÃ­ficos de FotMob (hay otros cambios simultÃ¡neos en el workspace).

## 2026-09-24 â€” Fase 2.D medida: la forma de la matriz no es el problema

Implementados como challengers (a peticiÃ³n del usuario, sabiendo que el
esperado era 0,001â€“0,002 de RPS): Poisson bivariante, Conway-Maxwell-Poisson,
conteo Weibull con cÃ³pula de Frank y probit ordenado sobre la diferencia de
goles. DecisiÃ³n de diseÃ±o: los brazos de conteo conservan las MEDIAS de
Dixon-Coles fuera de muestra y cambian solo la forma. AsÃ­ cada brazo aÃ­sla lo
que dicen mejorar los papers (dispersiÃ³n y dependencia) y no hace falta otro
ajuste de fuerzas por equipo, que costarÃ­a horas por brazo. `dc_tau` se
reajusta con el mismo protocolo para que la comparaciÃ³n sea justa.

Resultado sobre 2.641 partidos del Ãºltimo aÃ±o: ninguno mejora a `tau`; CMP y
Weibull empeoran el 1X2 con el IC entero por debajo de cero. Los parÃ¡metros
se quedan pegados a Poisson (Î½=1,09, c=1,05), es decir, los datos no tienen
la sobredispersiÃ³n que esos modelos corrigen. Confirma el diagnÃ³stico de
siempre: falta informaciÃ³n, no tÃ©cnica. No se activa nada; el informe se
recalcula en cada entrenamiento por si con mÃ¡s muestra cambia. Detalle y
cifras en `tareas.md` (2.D).

## 2026-09-24 â€” Rate limiting: existÃ­a, pero con dos agujeros

El pendiente "rate limiting en rutas pÃºblicas" ya estaba cubierto por el
middleware global. RevisÃ¡ndolo salieron dos fallos: el tope de 10/min de
`/control` se comparaba contra el contador compartido de todas las rutas
(abrir la web y luego el panel en el mismo minuto daba 429), y en IPv6 se
limitaba por direcciÃ³n, cuando un cliente suele controlar un /64 entero.
Contador propio para `/control` e IPv6 agrupado por /64; las IPv6 que
envuelven una IPv4 se cuentan como la IPv4. Con Cloudflare delante el caso
IPv6 no es teÃ³rico: la primera peticiÃ³n de verificaciÃ³n ya llegÃ³ por IPv6.

## 2026-09-24 â€” Fuera `soccerdata`

Se borrÃ³ `xg_fbref.py` en vez de aflojar el pin: FBref bloquea el scraping
con Cloudflare y el mismo dato llega por `xg_worldfootball`, asÃ­ que arreglar
la instalaciÃ³n de `soccerdata` solo habrÃ­a devuelto un mÃ³dulo que no funciona.
Con Ã©l salen `lxml` y `html5lib`, que ningÃºn cÃ³digo usaba. `requirements.txt`
vuelve a resolver (`pip install --dry-run`) y la imagen del servidor se
reconstruyÃ³ sin ellos.

## 2026-09-24 â€” Nombres sin resolver: una alarma que no se podÃ­a apagar

De 36 nombres pendientes en producciÃ³n solo uno era trabajo: `Coventry City`,
el nombre de The Odds API para el Coventry que API-Football habÃ­a dado de
alta como `Coventry` al ascender. Sin alias, cada pasada descartaba sus
eventos de Premier (8 descartes en dos dÃ­as). Alias en `db/020`, nunca equipo
nuevo; el difuso daba 76 y no se toca el umbral (ver 013).

Los otros 35 son clubes de ligas fuera del catÃ¡logo jugando copas europeas:
irresolubles por diseÃ±o. Pero la alarma los contaba, asÃ­ que "Salud del
sistema" iba a estar en rojo para siempre â€” el mismo fallo que ya se corrigiÃ³
el 2026-09-22 con el calendario. Ahora cuenta solo nombres vistos en liga
domÃ©stica o sin competiciÃ³n anotada (en la duda, alarma). Para poder
distinguirlo, `odds_worker` anota la competiciÃ³n del feed con
`resolve_team(seen_in=)`, un parÃ¡metro aparte porque pasar `league_id`
habrÃ­a ACOTADO la bÃºsqueda a los equipos de la copa, que no tiene ninguno.
Si un nombre se ve primero en copa y luego en liga, gana la liga: es la que
debe alarmar.

## 2026-09-24 â€” GuÃ­a visual de QuantFut aplicada a la demo

La portada pasa de una presentaciÃ³n casi solo editorial a mostrar una ficha
1X2 ficticia junto a su explicaciÃ³n y acceso al historial: la identidad
propia de QuantFut debe ser la evidencia del partido, no los efectos tÃ­picos
de una casa de apuestas. `frontend/DESIGN_SYSTEM.md` fija tokens, jerarquÃ­a,
componentes, mÃ³vil y accesibilidad. UI UX Pro Max se usÃ³ como catÃ¡logo de
criterios, sin instalarlo, aÃ±adir dependencias ni copiar una plantilla.
El prototipo conserva sus seis vistas y sigue sin cuentas, pagos, apuestas o
datos reales. El contenido futuro autorizado permanece en el FastAPI modular,
nunca oculto solo con CSS ni protegido por un secreto en el navegador.

## 2026-09-24 â€” Fase 2: lo que faltaba era cÃ³digo de arranque, no mÃ¡s modelo

Revisada la Fase 2 entera con el sistema ya en producciÃ³n. Casi todo lo
pendiente es muestra y no se acelera con cÃ³digo, pero habÃ­a un bloqueo que sÃ­
era cÃ³digo: **sin modelo activo nada de la parte "modelo" acumula**. El job
de las 08:00 falla ("No hay ningÃºn modelo activo") y `qf.model.shadow`
responde "sin modelo activo" cada 5 minutos, asÃ­ que los cuatro brazos de 2.B
y el XI de 2.C no guardan ni una fila. El Ãºnico reentrenamiento programado era
el mensual (1-oct).

No se tocÃ³ la puerta: rechazar con mercado de 252 dÃ­as es correcto. Se aÃ±adiÃ³
`train --bootstrap` diario que solo entrena si no hay modelo activo Y el
cierre sharp ya pasarÃ­a la misma comprobaciÃ³n de frescura. La constante se
moviÃ³ a `promotion.MARKET_MAX_AGE_DAYS` para que el chequeo barato y la
puerta no puedan divergir. Motivo del chequeo previo: un entrenamiento cuesta
~3,5 h en el VPS; reentrenar a ciegas cada dÃ­a quemarÃ­a CPU para una
respuesta que ya se conoce.

La muestra comercial (sombra sharp) NO depende del modelo y ya acumula:
`af_odds` 801 filas en 21 partidos el primer dÃ­a. Pero no se veÃ­a en ningÃºn
sitio del operador: Grafana leÃ­a `pick_results` (vacÃ­a a propÃ³sito con la
publicaciÃ³n pausada) y con `clv_pct`, la vara que 015 descartÃ³. `/control`
gana la tarjeta de la puerta usando el mismo `shadow_sharp.report()` que
decide, no una copia en SQL que pudiera divergir.

Cerrados como superados, no borrados: validar la zona de abstenciÃ³n, la
incertidumbre relativa al mercado y la ordenaciÃ³n media/sd (servÃ­an para
apostar con el edge del modelo, criterio eliminado en el paso 4;
`uncertainty.py` ya no lo importa nadie), y extender la mezcla al AH (la
premisa de devolver el AH a los picks ya no aplica). 2.D (Weibull, CMP,
probit) no se implementÃ³: esperado 0,001â€“0,002 de RPS y el producto ya no
depende de que el modelo bata al mercado.

## 2026-09-24 â€” El cron del worker nunca habÃ­a corrido en el servidor

Tras el primer despliegue, `docker compose exec worker crontab -l` devolvÃ­a
"no crontab for root": el `command` del servicio `worker` en
`docker-compose.yml` intentaba `chmod 0644 /etc/cron.d/quantfut` antes de
`crontab /etc/cron.d/quantfut`, y ese archivo estÃ¡ montado `:ro` (es el
`./scripts/crontab` del repo). El `chmod` fallaba ("Read-only file system"),
el `&&` cortaba antes de `crontab`, y el contenedor seguÃ­a "Up" porque
`cron -f` sÃ­ llegaba a ejecutarse â€” pero sin ningÃºn job cargado. Cuatro horas
sin captura de cuotas, resultados ni nada, sin ningÃºn error visible salvo una
lÃ­nea en `docker compose logs worker`.

El `chmod` no hacÃ­a falta: `scripts/crontab` estÃ¡ en formato de crontab de
usuario (5 columnas, sin campo de usuario), y `crontab <archivo>` solo
necesita *leer* el archivo â€” root puede leerlo aunque el volumen sea `:ro`.
Se quitÃ³ el `chmod` y se encadenÃ³ todo con `&&` explÃ­cito para que un fallo
futuro en cualquier paso no deje `cron -f` corriendo en silencio con cero
jobs. Redesplegado y verificado: `crontab -l` en el worker devuelve los 17
jobs y `cron -f` corre como proceso propio (no como parte de la cadena `&&`).

Consecuencia directa: el primer entrenamiento (`qf.model.train`, mismo dÃ­a)
no activÃ³ ningÃºn modelo â€” no por este bug, sino porque `market_age_days=250`
en la base restaurada del local (el cierre sharp mÃ¡s reciente es de enero
2026): la puerta de promociÃ³n exige mercado con menos de 30 dÃ­as. Es el
comportamiento correcto de la puerta, no un fallo; hace falta que
`odds_worker`/`af_odds`/`shadow_sharp` acumulen cierres frescos (ahora sÃ­
corriendo) antes de reentrenar y esperar activaciÃ³n.

## 2026-09-24 â€” Despliegue detrÃ¡s de Cloudflare: lo que rompÃ­a sin avisar

Desplegado en el VPS de Contabo (`31.220.72.30`) con el dominio
`pronosticosdeportivos.pro` detrÃ¡s del proxy de Cloudflare. El `Caddyfile`
anterior daba por hecho que Caddy recibÃ­a las conexiones directamente, y con
Cloudflare delante eso fallaba en tres puntos, sin que ninguno diera error:

1. `remote_ip {$GRAFANA_ALLOWED_IP}` veÃ­a siempre una IP de Cloudflare, asÃ­
   que `/control`, `/admin` y Grafana habrÃ­an respondido 404 tambiÃ©n al
   operador.
2. Caddy reescribe `X-Forwarded-For` con la IP del salto anterior, y el rate
   limit de `main.py` usa su primer elemento. Todos los visitantes de un mismo
   nodo de Cloudflare habrÃ­an compartido el cupo de 60/min. Arreglado en
   Caddy (`trusted_proxies` con los rangos de Cloudflare + `CF-Connecting-IP`
   + `header_up X-Forwarded-For {client_ip}`), sin tocar `main.py`.
   Verificado: la clave de Redis del rate limit lleva la IP real del cliente.
3. Docker publica 80/443 por delante de ufw, asÃ­ que un "solo Cloudflare"
   hecho con ufw habrÃ­a sido falso. El filtro va en `DOCKER-USER`
   (`qf-cf-firewall`). Verificado: HTTPS directo a la IP no conecta y a travÃ©s
   de Cloudflare responde 200.

El usuario eligiÃ³ Cloudflare Access en lugar de filtrar por IP para el acceso
de operaciÃ³n. Caddy exige que llegue `Cf-Access-Jwt-Assertion` pero no valida
su firma: con el origen cerrado a Cloudflare, esa cabecera solo puede venir de
Access. Si algÃºn dÃ­a se abre el origen a otro trÃ¡fico, hay que validar el JWT.
Hasta que Access estÃ© configurado, `/control`, `/admin` y `panel.` responden
404: si falta la configuraciÃ³n, el acceso queda cerrado, no abierto.

Backups: `pg_dump -Fc` (el formato que lee `restore_db.sh`, no el `.sql.gz`
del README anterior) y sin `rclone`, porque no hay destino externo. Esto
queda pendiente y es el mayor riesgo que sigue abierto: la base guarda picks
sellados que no se pueden reconstruir.

Las contraseÃ±as de Grafana de `.env.server` se regeneraron antes del primer
arranque porque se mostraron en la salida de una herramienta durante la
sesiÃ³n.

## 2026-09-23 â€” PreparaciÃ³n del despliegue: el cron del contenedor nunca habrÃ­a funcionado

Al revisar `docker-compose.yml` y `scripts/crontab` antes del primer despliegue
salieron dos fallos que habrÃ­an dejado el sistema entero parado sin un solo
error visible (cada job escribe en su propio log dentro del contenedor):

1. El worker copiaba a `/etc/environment` (de donde cron toma el entorno vÃ­a
   pam_env) solo las variables con ciertos prefijos. `API_FOOTBALL_*` no
   estaba: calendario, resultados, alineaciones, lesiones y cuotas de
   API-Football habrÃ­an fallado en cada pasada. Tampoco `PUBLISH_*`,
   `SOFT_*`, `META_*`â€¦ Ahora se copia todo. Una lista blanca de prefijos es
   exactamente el tipo de cosa que se queda atrÃ¡s cada vez que se aÃ±ade una
   variable.
2. El crontab no fijaba `PATH`; el de cron es `/usr/bin:/bin` y en
   `python:3.12-slim` el intÃ©rprete estÃ¡ en `/usr/local/bin`. "python: not
   found" en cada job. `BASH_ENV` no servÃ­a de nada con `SHELL=/bin/sh`.

No verificado en un contenedor real: no hay Docker en este entorno. Por eso el
procedimiento termina comprobando `/var/log/af_odds.log` tras la primera pasada.

DecisiÃ³n de migraciÃ³n: se restaura la base local (`pg_dump`, 4 MB) en vez de
rehacer el backfill en el servidor, porque los alias revisados a mano no se
reproducen solos. `scripts/restore_db.sh` se niega a pisar una base con datos
sin `--force` y re-crea permisos y contraseÃ±a del rol de Grafana (el `004` lo
crea con una contraseÃ±a por defecto que no coincide con la de Grafana). La
base local no tenÃ­a ningÃºn modelo activo ni lotes sellados: no habÃ­a cadena que
trasladar, pero hay que entrenar el primer modelo en el servidor antes de las
08:00. `014_injuries` tampoco estaba aplicada en local; se aplicÃ³.

## 2026-09-23 â€” Sombra del criterio sharp: lo que decide si se reactiva la publicaciÃ³n

Paso 5, Ãºltimo del plan. `src/qf/publish/shadow_sharp.py`, `db/018`.

- **QuÃ© cuenta para la puerta: lo que se habrÃ­a publicado, no cada oferta.**
  Capturando cada hora, un mismo partido acumula decenas de ofertas; contarlas
  todas inflarÃ­a `n` con apuestas correlacionadas que nadie habrÃ­a hecho. La
  vista "publicables" toma, por partido, la primera pasada en la que el
  criterio habrÃ­a dado un pick con stake, y de ella la de mayor edge esperado:
  una fila por partido, como el sistema real. Todas las ofertas se desglosan
  aparte para investigar.
- **Se registran tambiÃ©n las ofertas de stake 0.** Son las de casas con
  persistencia medida nula (William Hill); sin registrarlas no habrÃ­a forma de
  comprobar si esa persistencia estÃ¡ bien estimada.
- **Se guarda la persistencia usada ese dÃ­a** en cada oferta: la tabla de
  `picks.PERSISTENCE` va a cambiar con esta misma muestra, y el informe tiene
  que poder distinguir quÃ© se decidiÃ³ con quÃ©.
- **Tablas propias, no `shadow_picks`**: aquellas cuelgan de una predicciÃ³n
  del modelo en sombra, y este criterio no sale del modelo.
- **Desglose por antelaciÃ³n (0-6, 6-24, 24-48, 48-72 h).** El histÃ³rico solo
  validÃ³ 24-48 h. Si el valor solo aparece en un tramo, hay que restringir la
  publicaciÃ³n a Ã©l antes de reactivarla.
- **Reactivar la publicaciÃ³n no es automÃ¡tico.** `/model-card` publica
  `sombra_criterio_sharp.autorizada`, pero `PUBLISH_PICKS_ENABLED=1` lo pone
  el usuario, viendo el desglose.

Corregidos de paso dos textos que ya eran falsos tras el paso 4: el
`/model-card` y el comentario de `PUBLISH_PICKS_ENABLED` decÃ­an que el
criterio vigente ordenaba por el edge del modelo.

## 2026-09-23 â€” El modelo deja de elegir los picks

Paso 4. `publish/picks.py` selecciona casas blandas que pagan por encima del
precio justo de Pinnacle; el criterio del modelo (anti-seÃ±al medida) se borrÃ³
con sus integraciones. Decisiones que no se leen en el diff:

- **Un snapshot, nunca dos fuentes cruzadas.** La casa blanda y Pinnacle
  salen de la misma respuesta (API-Football) o de la misma captura (The Odds
  API). Un 1xBet de API-Football de hace 19 h contra un Pinnacle fresco de The
  Odds API "mostrarÃ­a" el movimiento de las 19 h como edge.
- **Point-in-time.** Del lado de API-Football solo cuenta lo que ya tenÃ­amos
  (`fetched_at â‰¤ ahora`), y por antigÃ¼edad del precio (`odds_as_of`) se corta a
  6 h: un pick con un precio que ya no existe engaÃ±a al suscriptor y ademÃ¡s
  infla el CLV medido, porque se compara una cuota que no se podÃ­a tomar.
- **El stake sale del edge esperado al cierre, no del bruto**, con la
  persistencia medida por casa (1xBet 0,72, Bet365 0,13, William Hill 0; las
  no medidas, 0,42 de poblaciÃ³n). Sustituye al 0,55 fijo para todas. Con
  persistencia 0 el candidato se genera igual â€”la sombra necesita medirloâ€” y
  `select_daily` lo descarta por stake.
- **La confianza del modelo ya no filtra.** `daily.run` pasaba solo las
  predicciones que no eran de confianza baja; eso era una regla sobre el
  modelo y ya no aplica. La predicciÃ³n sigue siendo obligatoria: cada pick la
  referencia (FK) y se sella con ella.
- **`min_price`, `fair_prob`, `odds_source` y `odds_as_of` se sellan.** Son
  parte de lo que se publica; si no entraran en el payload de la cadena, se
  podrÃ­an cambiar sin que la verificaciÃ³n lo detectara. Los lotes anteriores
  no cambian: `verify` recalcula desde los ficheros en disco.
- **Se borrÃ³** `tests/test_eligible_markets.py` y los tests del interruptor
  de incertidumbre: probaban un comportamiento que ya no existe.
  `model/uncertainty.py` y sus tests del mÃ³dulo se conservan.
- `/model-card` corregido: afirmaba que el edge publicado llevaba el factor
  0,55 y que la confianza baja impedÃ­a picks; ninguna de las dos es ya cierta.
  AÃ±adidas como limitaciones la dependencia de 1xBet y que Bet365/Betano no
  tienen histÃ³rico.

Sin validar: el histÃ³rico midiÃ³ precios de 24-48 h antes del partido; en vivo
se decide a cualquier distancia. La sombra (paso 5) debe estratificar por
antelaciÃ³n antes de fiarse del conjunto.

## 2026-09-23 â€” Captura de cuotas de API-Football en tabla propia

Pedida por el usuario. `src/qf/ingest/af_odds.py`, `db/016_af_odds.sql`.

- **Tabla separada (`af_odds_snapshots`), no `odds_snapshots`.** Esa tabla
  la leen sin filtrar por casa el consenso de mercado de `daily.py`, el mejor
  precio de `picks`, `/fair-price`, la sombra y `health` ("Ãºltima captura").
  API-Football actualiza cada liga de golpe cada varias horas (2 h en MLS, 19
  h en Liga MX, 3,5 dÃ­as en Premier durante un parÃ³n): sus precios viejos
  habrÃ­an entrado en todos esos cÃ¡lculos, y la salud habrÃ­a dado por vivo un
  worker de The Odds API caÃ­do.
- **Dos tiempos por fila.** `provider_updated_at` es el `update` del
  proveedor (cuÃ¡ndo existÃ­a el precio) y `fetched_at` cuÃ¡ndo lo supimos. Una
  decisiÃ³n en T solo puede usar `fetched_at â‰¤ T`. Guardar solo la hora de
  captura habrÃ­a hecho pasar por frescos precios de 19 horas.
- **DeduplicaciÃ³n por esa marca.** El proveedor devuelve la misma
  actualizaciÃ³n durante horas; la restricciÃ³n Ãºnica con
  `provider_updated_at` hace que repetir la consulta no duplique filas en una
  tabla inmutable. Comprobado: 78 filas en la primera pasada, 0 en la segunda.
- **Cada hora, no cada 3 horas** como se propuso al usuario. El proveedor
  actualiza cuando le toca y el job diario decide a las 08:00: con el cron cada
  3 h, una actualizaciÃ³n de las 06:10 no llegarÃ­a a tiempo. Coste ~50
  peticiones/hora de 7.500/dÃ­a. Horizonte de 72 h, que cubre la ventana
  temprana del criterio (24-48 h).

## 2026-09-23 â€” Cuatro ligas con histÃ³rico de The Odds API: el valor accesible es 1xBet

Descargado 2025 de Brasil, Argentina y MLS (12.640 crÃ©ditos, exactamente lo
que calculÃ³ `plan`; saldo 3.217). Con Liga MX: 1.681 partidos con Pinnacle
antes y al cierre.

| casas (umbral 2%) | n | valor esperado al cierre | IC95 |
|---|---|---|---|
| todas las casas blandas (26) | 317 | +2,78% | [1,79, 3,78] |
| accesibles: 1xBet + William Hill + 888sport | 127 | +3,83% | [2,36, 5,20] |
| solo 1xBet | 126 | +3,91% | [2,45, 5,31] |

Lo que hay debajo del +3,83%, y por quÃ© no se puede leer como "funciona":

- **Es una sola casa.** 126 de las 127 apuestas accesibles son de 1xBet.
  William Hill y 888sport casi nunca superan el precio justo. Un producto que
  depende de una sola casa desaparece el dÃ­a que esa casa limita las cuentas
  de los suscriptores, y es lo primero que hacen con quien gana.
- **Es sobre todo MLS** (85 de 127). Argentina 26 (+2,5%), Brasil 9, Liga MX 7
  y negativa. En Liga MX el valor que habÃ­a (+2,43% con todas las casas) era de
  Coolbet y Unibet, que los suscriptores no usan.
- **No pasa la puerta en amplitud:** pide 3 ligas con 30 apuestas; con las
  casas accesibles solo MLS la supera en un aÃ±o.
- Coincide con football-data, que es independiente: 1xBet +2,78% en las 7
  ligas europeas en 2024/25 (Ãºnica temporada en que los CSV la incluyen).

**Las casas de los suscriptores no estÃ¡n donde se creÃ­a.** DecisiÃ³n del
usuario: apuestan en casas internacionales presentes en LatAm (Bet365, 1xBet,
Betway, William Hill, 888â€¦). La regiÃ³n `eu` de The Odds API solo cubre 1xBet,
William Hill y 888sport; Bet365 no estÃ¡ en The Odds API (solo `bet365_au`),
Betway solo en `uk`, y no hay ninguna casa mexicana. Preguntado a
API-Football (`/odds/bookmakers` y `/odds` por competiciÃ³n): de 33 casas en su
catÃ¡logo, solo 9 cotizan de verdad nuestras competiciones, y entre ellas estÃ¡n
**Bet365, Betano, 1xBet y William Hill, junto a Pinnacle en la misma
respuesta**, en 12 de 13 (Champions sin cuotas en la consulta). Betway,
888sport, Betcris y Sportingbet estÃ¡n en el catÃ¡logo pero con cero partidos.
LÃ­mites: refresco cada ~3 h y solo 7 dÃ­as de histÃ³rico, y no se sabe si su
Bet365/Betano son los precios de las webs mexicanas o los internacionales.
Otros proveedores revisados: OddsPapi tiene Betano MX (la Ãºnica versiÃ³n
mexicana encontrada) y OpticOdds tiene Playdoit; ninguno tiene Caliente.

## 2026-09-23 â€” HistÃ³rico de The Odds API: Liga MX tiene valor, pero en casas europeas

Paso 3. `src/qf/ingest/odds_history.py`. Decisiones:

- **No se escribe en `odds_snapshots`.** El plan decÃ­a lo contrario; se
  cambiÃ³ al escribir el cÃ³digo. Esa tabla es inmutable y alimenta el
  entrenamiento (`window_tag='close'`) y la liquidaciÃ³n: un error de parseo o
  de emparejamiento quedarÃ­a para siempre y contaminarÃ­a las dos. Las
  respuestas se guardan crudas en `.local/odds_hist/` y se reprocesan sin
  volver a pagarlas. Cargarlas en la base es una decisiÃ³n aparte.
- **CÃ³mo se gasta poco.** Un snapshot trae TODOS los partidos prÃ³ximos de la
  competiciÃ³n, asÃ­ que el precio temprano sale de un snapshot diario a las
  12:00 UTC (24-48 h antes de cada partido) y el cierre, de uno por hora de
  inicio distinta, 5 min antes. `plan` calcula el nÃºmero exacto con el
  endpoint de eventos (1 crÃ©dito por semana) ANTES de gastar.
- **Solo 1X2.** El backtest de football-data no encontrÃ³ oportunidades
  verificables en over/under; cada mercado duplica el coste.
- **Guardas propias del feed:** una cuota con `last_update` de mÃ¡s de 60 min no
  cuenta como apostable; un "cierre" de mÃ¡s de 30 min antes del kickoff no es
  un cierre; los exchanges no entran como casa blanda (cobran comisiÃ³n). La
  guarda de referencia es la misma del backtest, con el consenso de las casas
  blandas del snapshot en lugar de la media de football-data.

Coste medido para 2025: Liga MX 3.920, Brasil 3.910, Argentina 5.090, MLS
3.640 crÃ©ditos (16.560 en total). Solo se descargÃ³ Liga MX.

Resultado Liga MX 2025 (316 partidos con Pinnacle antes y al cierre, 22 casas):
mejor cuota a umbral 0% â†’ n=148, valor esperado al cierre justo +2,43%, IC95
por semanas [0,47, 4,20]; a 2% â†’ n=70, +2,87% [âˆ’0,18, 5,51], sin concluir.

Lo que importa para el producto: el valor se concentra en Coolbet (38 de 70
apuestas a 2%, +4,39%) y Unibet (`unibet_eu` +4,00%). Son casas europeas; es
probable que un suscriptor en MÃ©xico no pueda usarlas, y la regiÃ³n `eu` de The
Odds API no incluye casas mexicanas. `unibet_it/nl/se` son la misma casa con
otra marca y dan exactamente las mismas cifras: al contar apuestas por casa no
hay que sumarlas como independientes. Y el volumen es bajo: 148 apuestas al aÃ±o
en una liga con la puerta pidiendo 300 en 3 ligas.

## 2026-09-23 â€” LiquidaciÃ³n de AH: fracciÃ³n ganada y fracciÃ³n devuelta, por separado

El bug anotado en la entrada de abajo. `_settle_outcome` devolvÃ­a un Ãºnico
multiplicador (`0,5Â·a + 0,5Â·b`, con el empuje valiendo 0,5 por pata) y
`settle_pending` lo multiplicaba por la cuota. Eso paga a cuota la mitad
empujada, que en realidad solo se devuelve. A 1,90: medio-ganada +0,425 en vez
de +0,45, medio-perdida âˆ’0,525 en vez de âˆ’0,50. A 2,00 coinciden, y por eso no
lo delataba ningÃºn ejemplo "redondo".

Se eligiÃ³ devolver `(outcome, ganada, devuelta)` en vez de una funciÃ³n de la
cuota porque es exactamente la descomposiciÃ³n que ya usa
`pricing.market_asian_handicap` para fijar la cuota justa (`E[w]Â·cuota +
E[push]`). Precio y liquidaciÃ³n hablan ahora el mismo idioma, y el empuje de
lÃ­nea entera deja de ser un caso especial en `settle_pending`: con
ganada=0 y devuelta=1 el beneficio sale 0 solo.

El error no era ruido: en medio-ganada y medio-perdida vale
`0,25Â·cuota âˆ’ 0,5` por unidad, con signo fijo segÃºn el lado de 2,00. Por
debajo (casi todas las cuotas de AH) restaba siempre; por encima sumaba.
HabrÃ­a sesgado el ROI publicado sin tocar el CLV, asÃ­ que la puerta no lo
habrÃ­a detectado. `pick_results` estaba vacÃ­a: no hubo filas que
rehacer. `shadow.py` liquida solo 1X2 con su propio cÃ³digo y no usa
`_settle_outcome`.

## 2026-09-23 â€” Backtest "casa blanda contra sharp" en el repo, y Pinnacle tambiÃ©n se rompe

Paso 2 del plan: `src/qf/eval/soft_vs_sharp.py`. Reproduce el piloto al
decimal (mismos n y EV por casa), asÃ­ que el piloto no tenÃ­a un error de
cÃ¡lculo. Pero al mirar la tabla completa apareciÃ³ algo que el piloto no vio.

**La referencia sharp tambiÃ©n falla, y en over/under falla de forma que se
esconde sola.** Bet365 y la MEDIA del mercado daban "edges" tempranos del
10-13% en over/under que persistÃ­an ENTEROS hasta el cierre (persistencia
â‰ˆ1,0). La media del mercado no puede batir al precio justo por 12 puntos. Las
filas lo explicaban: Pinnacle a 1,53/2,63 mientras todas las casas daban
1,36-1,44 en el over, y con el precio temprano idÃ©ntico al de cierre. Pinnacle
congelado o en otra lÃ­nea. El cierre no lo delata porque es el mismo precio
roto: es exactamente el tipo de fallo que un backtest valida a sÃ­ mismo.

ComprobaciÃ³n independiente: en 2024/25, Ãºnico aÃ±o con Betfair Exchange en los
CSV, cuando Pinnacle y Betfair discrepan mÃ¡s de 3 puntos en over/under, la
media de las casas se pone del lado de Betfair en 21 de 24 casos. En 1X2 casi
no ocurre (5 casos, y la media apoya a Pinnacle en 4).

Guarda elegida: `MAX_SHARP_DEVIATION = 0,03` sobre la probabilidad justa de
Pinnacle TEMPRANA frente a la de la media de las casas TEMPRANA. Solo usa
informaciÃ³n anterior al cierre, asÃ­ que no es una fuga y se puede aplicar
igual en vivo. El 0,03 es unas dos veces el p99 de la desviaciÃ³n (1,5-1,6
puntos) y es el primer valor en el que desaparecen TODOS los casos de "la media
supera el precio justo". Descarta 1 mercado 1X2 y 42 de over/under de 14.294.
Sin media completa no se puede verificar y el mercado no entra.

Resultado con guarda (1X2, umbral 2%, mejor cuota entre las 6 casas reales):
n=1.378, EV al cierre justo +2,09% (IC95 por semanas [1,21, 2,91]), positivo
en las 7 ligas; persistencia 0,42; ROI +2,9% con IC [âˆ’10,2, +15,1], sin
concluir. Over/under en casas reales: 11 apuestas, IC que incluye cero. El
"mÃ¡ximo del mercado" sigue positivo en los dos mercados, pero no es una casa y
no se puede publicar como pick.

Lo que esto NO prueba: los CSV traen un Ãºnico snapshot pre-cierre (viernes o
martes), no la operaciÃ³n real con varias ventanas; no incluye el lÃ­mite de
cuentas de las casas blandas; y el ROI no estÃ¡ demostrado. Lo que SÃ prueba es
que el criterio tiene valor contra la misma vara que decide la puerta, que es
lo que el criterio del modelo no tenÃ­a.

Fuera de alcance, con motivo: hÃ¡ndicap asiÃ¡tico (la lÃ­nea temprana y la de
cierre cambian a menudo). Al revisar su liquidaciÃ³n saliÃ³ un bug aparte en
`clv._settle_outcome`: en lÃ­neas de cuarto trata la media apuesta devuelta
como si pagara a cuota, asÃ­ que medio-ganada y medio-perdida solo se liquidan
bien a cuota 2,00. Anotado como tarea aparte.

## 2026-09-23 â€” La puerta comercial decide por valor esperado al cierre sin margen

Paso 1 del plan. `ev_close_pct = price Ã— closing_prob_devig âˆ’ 1` pasa a ser la
cifra de la puerta (`evaluate_clv_gate`) y de la puerta de sombra
(`evaluate_shadow_promotion`). `clv_pct` se conserva y se publica: quitarlo
romperÃ­a la comparabilidad con lo ya reportado, y enseÃ±ar las dos cifras
explica el sesgo al lector del track record.

Decisiones que no se ven en el diff:

- **`closing_prob_devig` cambiÃ³ de definiciÃ³n, no solo de uso.** Antes
  `_closing_prices` tomaba por cada selecciÃ³n la cuota sharp si existÃ­a y si no
  otra casa, asÃ­ que el de-vig podÃ­a mezclar precios de dos casas. Ahora sale
  de UN snapshot de cierre de Pinnacle (`window_tag='close'`, mismo
  `captured_at`) con el grupo completo. Si no lo hay, no se mide: una apuesta
  sin cierre justo no puede demostrar valor. Se eligiÃ³ exigir `close` y no "el
  Ãºltimo precio antes del kickoff" porque, si fallÃ³ la ventana de cierre, el
  Ãºltimo precio puede ser de dÃ­as antes y ya no es un cierre.
- **El hÃ¡ndicap se empareja con la lÃ­nea opuesta.** The Odds API guarda local
  âˆ’0,5 y visitante +0,5; el filtro por lÃ­nea igual del cÃ³digo anterior nunca
  encontraba la pareja, asÃ­ que en hÃ¡ndicap `closing_prob_devig` salÃ­a siempre
  vacÃ­o sin avisar.
- **BTTS, doble oportunidad y totales por equipo no cuentan para la puerta.**
  El worker no captura esos mercados, asÃ­ que no hay cierre sharp. Aparecen en
  `n_without_fair_close` para que se vea cuÃ¡ntos quedan fuera.
- El mensaje de rechazo pasÃ³ de "incluye cero" a "no estÃ¡ entero por encima de
  cero": con la vara nueva el caso tÃ­pico es un intervalo entero NEGATIVO, y
  "incluye cero" habrÃ­a sido falso.

Verificado contra cierres reales del histÃ³rico: tomar el propio cierre de
Pinnacle en un Interâ€“Lecce da âˆ’2,0% de valor esperado, que es su margen. 289
tests. `pick_results` y `shadow_results` estaban vacÃ­as: no hubo nada que
rellenar.

## 2026-09-23 â€” PublicaciÃ³n de picks pausada y The Odds API solo en `eu`

DecisiÃ³n del usuario tras el piloto de abajo. `PUBLISH_PICKS_ENABLED=0` por
defecto: el job diario sigue prediciendo y sellando las predicciones, pero no
selecciona, guarda ni difunde picks. Se eligiÃ³ un interruptor en vez de borrar
la selecciÃ³n porque la reanudaciÃ³n es una decisiÃ³n explÃ­cita, no un
redespliegue, y porque el criterio nuevo aÃºn no existe. Se sigue sellando
porque las predicciones del dÃ­a deben quedar probadas aunque no haya picks; el
orden predecir â†’ sellar no cambia. `/model-card` publica que estÃ¡ pausada.

RegiÃ³n de The Odds API: solo `eu` (Pinnacle y Betfair Exchange). Esto corrige
la entrada de mÃ¡s abajo del mismo dÃ­a que la habÃ­a subido a `eu,us`: con `us`
el vivo gastaba ~11.610 de 20.000 crÃ©ditos y no quedaba margen para el
histÃ³rico, que cuesta 10Ã— por llamada. Ahora ~5.800 en vivo y ~14.000 libres.

## 2026-09-23 â€” Piloto "casa blanda contra precio sharp": el criterio de mercado sÃ­ tiene valor, y la vara de CLV estaba torcida

Tres hallazgos, medidos con un script de scratchpad (no en el repo todavÃ­a):

1. **El CLV histÃ³rico SÃ era medible.** Los CSV del formato principal de
   football-data traen cuotas pre-cierre de 8 fuentes ademÃ¡s del cierre, para
   1X2, O/U 2,5 y AH. `history_fd._ingest_rows` guarda solo la primera familia
   disponible (`break`) y tiraba el resto. README corregido.
2. **Seleccionar por distancia al precio sharp funciona donde el modelo
   falla.** 14.294 partidos, 7 ligas, 2019-2025. Precio justo temprano = Shin
   sobre Pinnacle pre-cierre; se apuesta si `cuota_blanda Ã— p_justa âˆ’ 1 â‰¥ 2%`.
   Valor esperado contra el cierre justo: mÃ¡ximo del mercado +3,05% (IC95
   [2,68, 3,39], n=4.684), 1xBet +2,78%, Bwin +1,37%, Bet365 +0,56% (IC95
   [âˆ’0,64, 1,81]), William Hill âˆ’0,37%. ROI realizado no concluyente (mÃ¡ximo
   +0,95%, IC95 [âˆ’5,1, +7,0]). QuÃ© fracciÃ³n del edge temprano sobrevive al
   cierre depende MUCHO de la casa (Max ~0,71, 1xBet ~0,68, Bet365 ~0,12): un
   encogimiento constante Ãºnico estÃ¡ mal planteado. El "mÃ¡ximo del mercado" es
   una cota optimista: mezcla casas a las que un suscriptor quizÃ¡ no accede.
3. **`clv_pct` estÃ¡ sesgado al alza por el margen.** Se calcula contra el
   cierre de Pinnacle CON margen (`price / close âˆ’ 1`). Apostar a Pinnacle
   temprano en todo, sin criterio, da `clv_pct` âˆ’0,32% pero valor esperado
   contra el cierre justo âˆ’3,90%. La puerta comercial (`evaluate_clv_gate`)
   lee `clv_pct`: podÃ­a autorizar una estrategia con EV â‰ˆ âˆ’3%. La cantidad
   correcta es `price Ã— closing_prob_devig âˆ’ 1`, y `closing_prob_devig` ya se
   guarda en `pick_results`.

AdemÃ¡s: la puerta de CLV solo se REPORTA en `/model-card`; `daily.py` no la
consulta y publica (y sella en la cadena, para siempre) con el criterio viejo
en cuanto el cron corra con cuotas reales.

## 2026-09-23 â€” The Odds API subida a plan de pago: el cron de `odds_worker` deja de ser manual

El usuario dio de alta una nueva `ODDS_API_KEY` de pago, 20.000 crÃ©ditos/mes
(reinicia el dÃ­a 1 a las 00:00 UTC), reemplazando la del plan de 500 crÃ©ditos
que obligaba a correr `odds_worker` a mano. Con el coste ya medido el
2026-09-22 sobre el calendario real de las 13 competiciones
(`eu,us x h2h,totals,spreads` â‰ˆ 1.935 llamadas/mes Ã— 6 crÃ©ditos = ~11.610
crÃ©ditos/mes), el nuevo plan cabe con 1,7x de margen â€” antes ni la opciÃ³n mÃ¡s
barata cabÃ­a en 500. `.env` ya no restringe a `eu x h2h`: pasa a
`ODDS_API_REGIONS=eu,us` / `ODDS_API_MARKETS=h2h,totals,spreads`, la
configuraciÃ³n completa que ya asumÃ­a el cÃ¡lculo de coste. `scripts/crontab`
ya traÃ­a la lÃ­nea de `odds_worker` cada 10 min sin comentar, asÃ­ que no hizo
falta tocar el cron en sÃ­ â€” el bloqueo era solo de crÃ©dito/clave.

**Lo que sigue sin verificar:** no hay Docker en este entorno, asÃ­ que no se
confirmÃ³ el despliegue real del contenedor con cron activo, ni que el
consumo de crÃ©dito en producciÃ³n coincida con lo estimado sobre el
calendario anunciado (los reprogramados y los mercados que de verdad devuelve
cada casa pueden variar el coste real).

## 2026-09-23 â€” Un solo FastAPI para web demo, API y control interno

La decisiÃ³n posterior del usuario sustituyÃ³ el BFF como segundo servicio:
el mismo FastAPI sirve el prototipo en `/` y un panel de lectura en
`/control`. Se conserva el aislamiento de permisos: `/v1` y `/admin`
mantienen sus tokens de servidor, `/control` exige credenciales humanas
separadas y Caddy limita `/admin` y `/control` a la IP operativa. El
JavaScript solo contiene datos ficticios. No se activaron cuentas de cliente,
pagos ni picks premium reales porque la puerta de CLV sigue pendiente.
Pruebas de regresiÃ³n: 278 pasan; el frontend valida sintaxis. El arnÃ©s no
pudo ejecutar Python ni Docker desde Git Bash en este entorno, por lo que
se ejecutÃ³ pytest explÃ­citamente con `.venv` y no se validÃ³ Caddy en un
contenedor.

## 2026-09-22 â€” Prototipo visual antes de la web comercial

El usuario pidiÃ³ ver un prototipo completo en modo demo y eligiÃ³ expresamente
la distribuciÃ³n y los menÃºs de Pitchverse como referencia visual. Se creÃ³
`frontend/` con seis vistas navegables y datos ficticios, sin integrar la API:
el objetivo es validar el diseÃ±o sin aparentar que ya hay picks rentables o
una suscripciÃ³n activa. La aplicaciÃ³n comercial sigue pospuesta hasta reunir
CLV real y superar la puerta de la fase 2. El futuro navegador hablarÃ¡ con un
backend web propio; el `SERVICE_TOKEN` de FastAPI nunca se pondrÃ¡ en JS.

## 2026-09-21 â€” ArnÃ©s inicial creado

- El proyecto tenÃ­a dos versiones del `README.md`: una suelta en la raÃ­z
  (mÃ¡s antigua, sin menciÃ³n de Grafana ni de los tres niveles de auth de la
  API) y otra empaquetada dentro de `pyton/quantfut.tar.gz` (menciona
  `db/004_grafana_readonly.sql`, `grafana/`, y coincide exactamente con los
  archivos reales que trae el propio tar.gz). Se conservÃ³ la versiÃ³n del
  tar.gz porque es la que describe el cÃ³digo que realmente existe. Si esto
  fue un error, la versiÃ³n anterior no quedÃ³ guardada aparte â€” revisar con
  el usuario si hace falta.
- `pyton/` contenÃ­a archivos `.py`/`.sql`/`.sh` sueltos que resultaron ser
  copias idÃ©nticas (diff sin diferencias) de los mismos archivos dentro del
  `quantfut.tar.gz`. El tar.gz es el repo completo (incluye `db/`, `src/qf/`
  completo, `docker-compose.yml`, `Dockerfile`, `requirements.txt`,
  `grafana/`); se extrajo a la raÃ­z del proyecto para que la estructura
  coincida con la que documenta README.md.
- El tar.gz traÃ­a dos directorios basura con nombres literales
  `{db,src` y `{db,src/qf/{ingest,model,publish,eval,api},scripts}` â€”
  artefacto de un `mkdir -p {a,b}` corrido sin expansiÃ³n de llaves al crear
  el archivo. Estaban vacÃ­os, se eliminaron.
- No se inicializÃ³ git ni se borrÃ³ `pyton/` â€” no habÃ­a repo git en el
  directorio, asÃ­ que borrar sin poder revertir era riesgo innecesario. Se
  dejÃ³ como nota en `harness/tareas.md` para que el usuario lo confirme.
- No existe todavÃ­a suite de tests (`pytest` u otro). `scripts/harness_check.sh`
  por ahora solo valida sintaxis Python (`py_compile`) y `docker compose
  config`; si se agrega una suite de tests, aÃ±adir esa verificaciÃ³n aquÃ­.

## 2026-09-21 â€” Alcance: sin Telegram, foco en la API para la web

El usuario confirmÃ³ que no usa Telegram â€” la venta de picks es solo en su
propia web, consumiendo esta API. Decisiones tomadas en esta sesiÃ³n:

- **El reparto free/paid ya no lo decide Telegram.** EncontrÃ© que
  `daily.py` llamaba `pk.persist(selected, tier="paid")` con un tier fijo
  para TODO el lote, y era `telegram.publish_batch()` quien in-place decidÃ­a
  quÃ© picks eran "gratis" (los primeros `free_count=2` por edge) solo para
  el mensaje de Telegram â€” nunca se reflejaba en la BD. Consecuencia real:
  `/picks/free` y la vista gratuita de `/v1/picks` devolvÃ­an siempre una
  lista vacÃ­a, porque en la tabla `picks` todo quedaba con `tier='paid'`.
  SoluciÃ³n: `picks.assign_tiers()` (nuevo, en `src/qf/publish/picks.py`)
  decide el tier antes de persistir, usando `settings.free_picks_per_day`
  (nuevo en `config.py`, default 2, env `FREE_PICKS_PER_DAY`). `daily.py`
  pasa ese mismo reparto a Telegram en vez de dejar que Telegram lo calcule
  de nuevo. Telegram sigue siendo 100% opcional (no-op si no hay
  `TG_BOT_TOKEN`), pero ya no es la fuente de verdad de nada.
- **Gap de modelo encontrado leyendo `model/train.py`, no estÃ¡ en el
  README:** `train_and_register()` llama `load_training_data()` sin
  `league_id`, asÃ­ que el Dixon-Coles se ajusta con las 7 ligas mezcladas en
  un solo fit â€” una sola ventaja de local y una sola escala de fuerza
  ataque/defensa para Premier League, Liga MX, BrasileirÃ£o, etc. La funciÃ³n
  ya soporta filtrar por `league_id`; no se usa. No lo toquÃ© todavÃ­a (el
  usuario pidiÃ³ enfocarse en la API primero) â€” queda en
  `harness/tareas.md` como pendiente de mayor impacto que la calibraciÃ³n,
  porque calibrar un modelo mal especificado por liga no corrige el sesgo
  de fondo.
- **Endpoints aÃ±adidos a `src/qf/api/main.py`:** `GET /leagues`,
  `GET /teams` (filtrable por `league`), `GET /matches/{match_id}` pÃºblico
  (ficha de partido con predicciÃ³n recortada a tier gratuito â€” pensado para
  pÃ¡ginas de partido indexables sin login). Antes no existÃ­a forma de que
  el frontend listara ligas/equipos sin pegarle directo a Postgres.
- **PaginaciÃ³n** (`limit`/`offset`) aÃ±adida a `/picks/free` y `/v1/picks`;
  antes devolvÃ­an todo el resultado sin lÃ­mite.
- **Pendiente explÃ­cito, no urgente ahora:** auth de suscriptor sin
  Telegram (email/magic-link o vÃ­a checkout de pago) y el webhook de
  cobros. El usuario dijo textualmente que eso es "despuÃ©s".

## 2026-09-21 â€” CorrecciÃ³n de las brechas tÃ©cnicas del modelo

Decisiones de diseÃ±o que no son obvias leyendo el cÃ³digo:

- **Por quÃ© la calibraciÃ³n actÃºa sobre las lambdas y no sobre el 1X2.** Los
  ~150 mercados salen todos de la misma matriz de marcadores. Calibrar el
  1X2 directamente (isotÃ³nica, que es lo estÃ¡ndar) dejarÃ­a el over/under y
  el hÃ¡ndicap saliendo de una matriz sin corregir, y el producto publicarÃ­a
  un 1X2 que no cuadra con su propio total de goles. La correcciÃ³n afÃ­n en
  log-espacio sobre (lambda, mu) recalcula toda la matriz y mantiene la
  coherencia. Se pierde algo de flexibilidad frente a la isotÃ³nica; se gana
  que el producto no se contradiga a sÃ­ mismo.
- **Por quÃ© NO se usÃ³ PyMC/numpyro para el modelo jerÃ¡rquico.** El pooling
  parcial estÃ¡ implementado como penalizaciÃ³n en la verosimilitud, que es el
  estimador MAP del mismo modelo jerÃ¡rquico. Da el encogimiento (que es lo
  que se querÃ­a) sin aÃ±adir una dependencia pesada ni muestreo NUTS, que el
  propio README dice que es lo Ãºnico que justificarÃ­a GPU. Si algÃºn dÃ­a se
  quieren intervalos de credibilidad por equipo, ahÃ­ sÃ­ hace falta la
  versiÃ³n bayesiana completa.
- **Por quÃ© el riesgo de portafolio usa la probabilidad del MERCADO.** Medir
  la varianza con la probabilidad del propio modelo la subestima justo
  cuando el modelo estÃ¡ sobreconfiado, que es el caso por defecto y la razÃ³n
  de existir del shrinkage. Ver `picks._risk_prob`.
- **Por quÃ© las correlaciones son constantes y no estimadas.** Con unos
  cientos de picks liquidados, estimar una matriz de correlaciÃ³n darÃ­a
  ruido. Son cotas superiores razonadas; equivocarse por prudencia solo
  cuesta tamaÃ±o de apuesta. El nÃºmero que NO puede ser cero es `CORR_BASE`:
  todos los picks salen del mismo modelo, y ese riesgo comÃºn no se
  diversifica repartiendo entre ligas.
- **Por quÃ© el modelo de residuo estÃ¡ desactivado por defecto.** Corrige
  solo el 1X2, asÃ­ que mientras estÃ© activo ese mercado deja de ser
  coherente con el resto del paquete. Es una decisiÃ³n de producto, no
  tÃ©cnica, y por eso la toma `RESIDUAL_ENABLED` y no el cÃ³digo. Se entrena
  siempre igualmente, para poder medir cuÃ¡nto se estÃ¡ dejando sobre la mesa.
- **Bug encontrado de paso:** `train.py` versiona por fecha
  ("2026.09.21") pero `daily.py` cargaba `dc_{MODEL_VERSION}.pkl` desde una
  variable de entorno fija. El primer reentrenamiento habrÃ­a dejado el job
  diario cargando un artefacto viejo o ninguno, sin avisar. Ahora el modelo
  activo se resuelve desde `model_artifacts`, que es la Ãºnica fuente de
  verdad de quÃ© estÃ¡ desplegado.

## 2026-09-21 â€” PonderaciÃ³n modelo/mercado + bug crÃ­tico de unidades

- **`model/meta.py`**: estima `w_model` minimizando log-loss fuera de muestra
  sobre `blend_logit()` (que ya existÃ­a sin que nadie calculara su peso).
  Detalle: `blend_logit` es en realidad un *log-opinion pool* (media
  geomÃ©trica de probabilidades renormalizada), no una mezcla en logit pese al
  nombre. La matemÃ¡tica es la estÃ¡ndar y correcta para multiclase, asÃ­ que se
  reutilizÃ³ tal cual en vez de duplicarla.
- **Pesos por liga** encogidos hacia el global con pseudo-conteo
  (`LEAGUE_SHRINK_K=600`), misma filosofÃ­a de pooling que el modelo. Una liga
  con menos de 250 partidos no recibe peso propio.
- **Por quÃ© la mezcla viene DESACTIVADA.** Acerca las probabilidades al
  mercado y por tanto REDUCE el edge: con w bajo, muchos picks dejan de
  superar el umbral. Es correcto, pero cambia cuÃ¡ntos picks se publican al
  dÃ­a, y esa es una decisiÃ³n de negocio. El peso se estima y se publica en
  `/model-card` aunque estÃ© apagada.
- **Riesgo sutil que obligÃ³ a restringir mercados.** Solo se mezclan 1X2 y
  totales (el AH tiene empuje en lÃ­neas enteras y necesita trato aparte). Si
  se mezclara solo eso y la selecciÃ³n siguiera mirando todos los mercados,
  los NO mezclados conservarÃ­an el edge inflado y el sistema se desplazarÃ­a
  solo hacia ellos: apostarÃ­a justo donde menos ha validado. Por eso
  `find_candidates` respeta `eligible_markets` cuando la mezcla estÃ¡ activa.
  Cubierto por `tests/test_eligible_markets.py`.
- **ExclusiÃ³n mutua con el modelo de residuo**: ambos fusionan con el
  mercado (el residuo usa `logit_gap` modelo-mercado como feature).
  Aplicarlos juntos contarÃ­a la informaciÃ³n del mercado dos veces. `daily.py`
  avisa y desactiva el residuo.
- **BUG CRÃTICO PREEXISTENTE ENCONTRADO: unidades del stake.** `kelly()`
  devolvÃ­a una fracciÃ³n de banca (0.0067 = 0.67%) pero el resto del sistema
  interpretaba ese nÃºmero como unidades, donde 1 unidad = 1% de banca (es la
  Ãºnica lectura coherente: `MAX_STAKE_UNITS=2.0` serÃ­a si no un tope del 200%
  de la banca por apuesta, y la exposiciÃ³n diaria de 10.0 serÃ­a del 1000%).
  Consecuencia real: el descarte `stake <= 0.05` de `find_candidates`
  eliminaba TODOS los picks con edge realista (3-10%) â€” comprobado a cuotas
  1.8/2.5/3.5 â€” asÃ­ que el sistema habrÃ­a publicado CERO picks
  indefinidamente sin dar ningÃºn error, y lo natural habrÃ­a sido culpar al
  modelo. Corregido con la conversiÃ³n Ã—100 y el contrato fijado en
  `tests/test_kelly_units.py` para que no pueda volver a romperse en
  silencio.

## 2026-09-22 â€” Postgres local y verificaciÃ³n end-to-end

PostgreSQL 16.15 instalado nativamente (winget, servicio `postgresql-x64-16`,
puerto 5432). Base `quantfut`, rol `qf`. El `.env` local apunta ahÃ­. El
esquema completo (`db/001..004`) se aplicÃ³ por primera vez: 17 tablas, 6
vistas, 5 triggers, 7 ligas. `db/004_grafana_readonly.sql` necesita
superusuario (crea un rol), en producciÃ³n eso lo cubre
`docker-entrypoint-initdb.d`.

**GarantÃ­as de BD verificadas ejecutÃ¡ndolas de verdad:** UPDATE y DELETE
rechazados en `predictions`, `picks` y `odds_snapshots`; `features_pit`
rechaza `as_of > kickoff`. Funcionan tal como documenta el README.

**El modelo por liga funciona con datos que pasaron por la base.** Se
sembraron dos ligas con ventaja de local deliberadamente distinta y el
entrenamiento real las recuperÃ³ por separado:

| liga | ha sembrada | ha recuperada | base sembrada | base recuperada |
|---|---|---|---|---|
| mx.liga_mx | 0.42 | 0.4021 | 0.22 | 0.2211 |
| gb.premier_league | 0.18 | 0.2147 | 0.12 | 0.1019 |

`beats_market: false` â€” la evaluaciÃ³n no se autoengaÃ±a. La calibraciÃ³n y el
modelo de residuo fueron correctamente DESCARTADOS por sus puertas
(calibraciÃ³n no mejoraba; residuo sin datos suficientes).

### Cuatro bugs preexistentes que solo aparecen con Postgres real

1. **`IndeterminateDatatype` en el filtro opcional por liga.** El patrÃ³n
   `(%s IS NULL OR col = %s)` no compila: Postgres no infiere el tipo de un
   parÃ¡metro suelto en una comparaciÃ³n IS NULL. Afectaba a
   `train.py::load_training_data` (fallo del 100% de los entrenamientos, en
   la primera llamada), a `/v1/fixtures` y a `clv.py::_closing_prices` (la
   ruta de liquidaciÃ³n). Corregido con casts `::text` / `::real`.
   OJO al corregirlo: psycopg cuenta los `%s` que aparezcan DENTRO de los
   comentarios SQL como marcadores; un comentario explicativo con `%s` rompe
   la consulta.
2. **`pd.Timestamp(start_date, tz="UTC")` con fecha ya consciente de zona.**
   `train.py` pasa `df["kickoff_utc"].max() - timedelta(...)`, que siempre
   trae zona. Reventaba todo walk-forward. Ahora se normaliza.
3. **Fecha del lote en UTC vs cast en zona del servidor.** `hashchain._collect`
   comparaba `generated_at::date` (que castea en la zona del SERVIDOR) contra
   un `batch_date` calculado en Python con UTC. Con el servidor en
   America/Mexico_City las fechas discrepaban, el lote salÃ­a vacÃ­o, no se
   sellaba y â€”por diseÃ±oâ€” NO SE PUBLICABA NADA. Fallo mudo. Corregido con
   `(generated_at AT TIME ZONE 'UTC')::date`. En Docker suele pasar
   desapercibido porque los contenedores van en UTC.
4. (Ya registrado arriba) unidades del stake en `kelly()`.

**Verificado end-to-end:** `qf.model.train` completo, `qf.publish.daily`
(predice, sella, publica), `hashchain verify` OK, y todas las rutas de la API
contra datos reales, incluidas `/leagues`, `/teams`, `/matches/{id}` y el
`/model-card` con parÃ¡metros por liga y peso modelo/mercado.

**Lo que sigue sin verificarse:** los datos son SINTÃ‰TICOS (goles Poisson
desde fuerzas conocidas, cuotas derivadas de la probabilidad verdadera mÃ¡s
margen). Sirven para verificar el CÃ“DIGO, no para evaluar el modelo. El
`w_model=0.43` que sale es alto justo porque el modelo coincide con el
proceso que generÃ³ los datos; con datos reales se espera bastante mÃ¡s bajo.
Tampoco se ha probado `ingest/lineups.py` contra la API real de API-Football.

## 2026-09-22 â€” HistÃ³rico real cargado + backfill de ligas LatAm roto

Cargados **31.041 partidos reales** de football-data.co.uk (gratis, sin
claves), 7 ligas, 2014-2026, con **96.7% de cobertura de cuotas de cierre de
Pinnacle**. Es material suficiente para cerrar la Fase 2 (validar si el modelo
tiene edge) sin pagar ninguna API.

### Quinto bug preexistente: las 3 ligas LatAm nunca cargaban nada

`history_fd.py` trataba el formato "extra" (Liga MX, Argentina, Brasil) como
si fuera el principal. Dos fallos superpuestos, ambos mudos:

1. **Nombres de columna distintos.** El extra usa `Home`/`Away`/`HG`/`AG`; el
   cÃ³digo leÃ­a `HomeTeam`/`AwayTeam`/`FTHG`/`FTAG`. Cada fila salÃ­a None y se
   descartaba en el primer `isinstance`.
2. **Filtro de temporada que no casa nunca.** Buscaba `'2526'` como subcadena
   de la columna Season, que vale `'2025/2026'`.

Efecto comprobado ejecutando el cÃ³digo viejo: `{"mx.liga_mx": 0,
"br.serie_a": 0, "ar.primera": 0}` frente a 4.560 por liga europea. Tres de
siete ligas â€”toda la parte latinoamericana, que es donde el README sitÃºa la
ventaja competitiva por haber menos apostante sharpâ€” se quedaban vacÃ­as sin
un solo error.

AdemÃ¡s, **no hay un Ãºnico formato de temporada dentro del formato extra**:
las ligas de aÃ±o natural (Brasil siempre; Argentina desde que cambiÃ³) la
escriben `'2025'` a secas, y ARG.csv contiene LAS DOS formas en el mismo
fichero. Aceptar solo la forma con barra dejaba Brasil a cero y Argentina a
un tercio (1.428 de 5.217). `season_labels_extra()` devuelve ahora ambas.

`ingest_extra()` descarga el fichero UNA vez y recorre todas las temporadas,
en vez de una sola (el extra trae todo el histÃ³rico en un CSV).

## 2026-09-22 â€” Kalman, cara a cara real, y xG por fin disponible

### El nÃºmero que importa: ninguno de los dos modelos bate al mercado

Sobre 31.041 partidos reales, ventana de validaciÃ³n de 365 dÃ­as:

| | RPS | log-loss | tiempo |
|---|---|---|---|
| Mercado (Pinnacle des-margenado) | **0.19994** | â€” | â€” |
| Dixon-Coles con decaimiento | 0.20359 | 1.01135 | 4.888 s |
| Ratings dinÃ¡micos (Kalman) | 0.20388 | 1.00795 | **51 s** |

Los dos modelos estÃ¡n empatados entre sÃ­ (0.0003 de diferencia con n=1.324 es
ruido). El hueco contra el mercado, 0.0037, es diez veces mayor y sÃ­ es real.
Es el resultado esperado y honesto: el mercado sabe mÃ¡s.

Kalman es **96 veces mÃ¡s rÃ¡pido**, y eso cambia quÃ© se puede hacer: ajustar
hiperparÃ¡metros pasa de ser una expediciÃ³n mensual a algo rutinario. El
barrido ya encontrÃ³ `process_var=1e-4` mejor que el 2.5e-4 por defecto.

Sanidad del ranking que produce: Inter, Barcelona, Flamengo, PSV, Arsenal,
Man City, Roma, Palmeiras, Real Madrid. Aprende fÃºtbol real.

### `model/kalman.py`

Ratings de ataque/defensa como estado latente con paseo aleatorio. Tres cosas
que el decaimiento exponencial no puede expresar: la incertidumbre crece con
el tiempo parado (un parÃ³n de 3 meses no es igual que uno de 3 dÃ­as), los
ascendidos convergen rÃ¡pido, y un cambio brusco de fuerza se captura en vez de
promediarse con la Ã©poca anterior.

AproximaciÃ³n declarada: covarianza DIAGONAL. La completa capturarÃ­a la
correlaciÃ³n entre rivales pero cuesta O(nÂ²) y aporta poco con equipos que
juegan decenas de partidos.

`predict_sequential()` predice antes de aprender cada partido: es fuera de
muestra por construcciÃ³n, en una sola pasada. No hay forma de colar futuro ni
olvidÃ¡ndose de un filtro.

### FBref estÃ¡ bloqueado; worldfootballR_data no

FBref devuelve 403 con desafÃ­o de Cloudflare. `soccerdata` llega a descargar
un driver de Chrome para evadirlo y falla igual tras 400 s. Como fuente
operativa no sirve. (De paso: `xg_fbref.py` pasaba la cachÃ© como `str` y
soccerdata exige `Path`; corregido, aunque el mÃ³dulo siga sin poder scrapear.)

`ingest/xg_worldfootball.py` (nuevo) descarga los mismos datos de FBref ya
raspados desde los releases de `JaseZiv/worldfootballR_data`, por HTTPS
normal, en segundos.

**La cobertura de xG pasÃ³ de 0 a 9.458 partidos**, y eso incluye 967 de Liga
MX y 1.322 de BrasileirÃ£o. **Esto contradice el README**, que da por perdido
el xG de esas ligas ("no tienen xG en las fuentes gratuitas... estÃ¡ en el
model-card a propÃ³sito, no es un error a arreglar"). SÃ­ lo tienen por esta
vÃ­a. Hay que actualizar el README y el model-card.

Aclaraciones sobre el formato, porque la peticiÃ³n original hablaba de Parquet:
no hay Parquet en ese repositorio, solo `.rds` y `.csv`. Argentina solo estÃ¡
en `.rds`, que exigirÃ­a `pyreadr`; no se aÃ±adiÃ³ esa dependencia por una liga.
Los datasets se publican por lotes, asÃ­ que van por detrÃ¡s del presente:
sirven para entrenar, no para cerrar el xG de anoche.

### El emparejamiento de nombres es el cuello de botella, y no se automatiza

Parte de la cobertura que falta no es por ausencia de datos sino porque los
nombres de FBref no casan con los de football-data. Y el umbral NO se puede
bajar: con score ~72, `Newcastle Utd` empareja con `manchester united` y
`Leeds United` con `sheffield united`. Fusionarlos arruinarÃ­a dos equipos a la
vez en silencio. A la vez, aciertos como `Leicester City`â†’`leicester` (78.3) o
`Flamengo`â†’`flamengo rj` (84.2) quedan por debajo. No hay nÃºmero que separe
los dos grupos: hace falta criterio humano. El paso 4 del README existe por
esto y estÃ¡ funcionando como debe al negarse.

## 2026-09-22 â€” Ajuste por estado del partido: NEGATIVO, y el motivo importa

`ingest/game_state.py` + 22 tests. Reconstruye el marcador minuto a minuto
desde los remates que acabaron en gol y reparte el xG de cada equipo entre
ganando / empatando / perdiendo.

**Los ratios empÃ­ricos contradicen la premisa del mÃ©todo** (12.928 partidos):

    perdiendo 1.135 Â· empatado 1.000 Â· ganando 1.177

Se esperaba que el equipo que gana se repliegue y produzca MENOS. Produce un
17.7% MÃS. La causa es un confundidor: ir ganando estÃ¡ correlacionado con ser
mejor equipo, asÃ­ que el estado "ganando" no mide repliegue, mide calidad.
Normalizar por ese ratio **elimina la seÃ±al de fuerza** que el modelo busca.

Resultado medido: RPS 0.20330 â†’ 0.20344 (todos), y 0.20075 â†’ 0.20108
restringiendo a los partidos con ajuste. Empeora en ambas comparaciones. NO
volver a proponerlo sin estratificar por calidad de equipo.

**ValidaciÃ³n que salvÃ³ el mÃ³dulo de ser basura silenciosa:** el marcador se
deriva de los goles que fueron remate, y un AUTOGOL no lo es. Contrastado
partido a partido contra la BD en Liga MX: 1.651 cuadran, 139 no (7.8%), y en
todos los casos la BD tenÃ­a exactamente un gol mÃ¡s. `match_state_data()`
devuelve `None` cuando no cuadra. Sin esa comprobaciÃ³n, 1 de cada 13 partidos
habrÃ­a tenido un estado inventado sin dar ningÃºn error.

El mÃ³dulo se conserva: la reconstrucciÃ³n sirve como FEATURE del modelo de
residuo (uso distinto de corregir el objetivo) y la validaciÃ³n contra
autogoles es infraestructura reutilizable.

## 2026-09-22 â€” Exprimido el fichero de tiros: resultado en parte negativo

`db/006_shot_stats.sql` + `match_stats()` en `ingest/xg_worldfootball.py`.
Del mismo CSV tiro a tiro que ya se descargaba para el xG se extraen ahora
remates, remates a puerta, PSxG y distancia media.

**Lo que aportÃ³:** Liga MX y BrasileirÃ£o pasaron de CERO datos de remates a
tenerlos (1.790 y 1.905 partidos). El formato "extra" de football-data.co.uk
no trae tiros ni cÃ³rners, asÃ­ que esas columnas llevaban vacÃ­as desde el
principio en las tres ligas latinoamericanas.

**Lo que NO aportÃ³, medido sobre n=28.718:** el PSxG como objetivo del modelo
de fuerza EMPEORA el RPS (0.20368 frente a 0.20330 del xG actual); la media de
ambos tambiÃ©n (0.20340). El xG que ya se usaba es el mejor de los tres. No
volver a proponer PSxG como objetivo sin una razÃ³n nueva: solo cubre remates a
puerta, asÃ­ que como medida de creaciÃ³n de ocasiones estÃ¡ sesgado, y mezcla la
colocaciÃ³n del disparo, que es mÃ¡s ruidosa que la calidad de la ocasiÃ³n.

**Error propio corregido en el camino:** el comentario original de la
migraciÃ³n afirmaba que `PSxG - xG` mide la calidad de definiciÃ³n. Es falso:
`psxg` suma solo remates a puerta y `xg` suma todos, asÃ­ que son poblaciones
distintas y la resta sale negativa en las seis ligas (-0.006 a -0.084) sin
decir nada de los delanteros. `goles - PSxG` sÃ­ es vÃ¡lido (rendimiento del
portero rival) porque ambas magnitudes hablan de la misma poblaciÃ³n. El
comentario del SQL ya lo explica.

## 2026-09-22 â€” MEDICIÃ“N DEFINITIVA: el modelo no tiene edge

Con xG ya cargado y sobre **n=28.128** predicciones fuera de muestra
(veintiuna veces la mediciÃ³n anterior, que ademÃ¡s corriÃ³ con cobertura de xG
a 0% y por tanto con el modelo a media potencia):

- **Pierde contra el mercado en las 7 ligas.** Delta de âˆ’0.00485 (Liga MX, el
  hueco menor) a âˆ’0.00790 (Serie A). Total âˆ’0.00653.
- **w_model = 0.0001.** El peso Ã³ptimo del modelo en la mezcla con el mercado
  es cero. El mercado ya contiene todo lo que el modelo sabe.

HipÃ³tesis descartadas POR MEDICIÃ“N, no por intuiciÃ³n. No volver a proponerlas
sin datos nuevos:

1. "Gana en ligas latinoamericanas porque son mercados blandos" â†’ falso, Liga
   MX tiene el hueco mÃ¡s pequeÃ±o pero negativo.
2. "Faltan hiperparÃ¡metros ajustados" â†’ el barrido de `process_var` mueve la
   cuarta decimal (mejor: 2.0e-4).
3. "Falta el xG" â†’ ayuda (0.20424 â†’ 0.20336) pero cierra el 12% del hueco.
4. "Es cuestiÃ³n de tÃ©cnica" â†’ dos motores independientes (Dixon-Coles con
   decaimiento y filtrado bayesiano) aterrizan en el mismo sitio.

**DiagnÃ³stico: falta INFORMACIÃ“N, no tÃ©cnica.** El modelo sabe goles y xG; el
mercado sabe ademÃ¡s lesiones, alineaciones, rotaciÃ³n, motivaciÃ³n y clima. MÃ¡s
matemÃ¡tica sobre los mismos datos no fabrica informaciÃ³n.

**LÃ­mite estructural de lo medible:** todo esto compara contra el CIERRE. Un
modelo peor que el cierre aÃºn podrÃ­a ser rentable contra casas blandas antes
de que converjan â€”eso es el CLVâ€”, pero el histÃ³rico de football-data solo trae
cuotas de cierre. Con un precio por partido el CLV es inmedible. Responderlo
exige `odds_worker` capturando a lo largo del tiempo. Es la justificaciÃ³n
empÃ­rica de por quÃ© ese worker es el paso 0.

**ImplicaciÃ³n de negocio:** la puerta de la fase 2 NO se cumple. SegÃºn la
propia filosofÃ­a del README, la fase 3 (vender) no arranca hasta que se
cumpla.

## 2026-09-22 â€” Alias curados y documentaciÃ³n al dÃ­a

`db/005_fbref_aliases.sql`: 35 alias de FBref revisados uno a uno. La
cobertura de xG subiÃ³ de 9.458 a **14.141 partidos** y quedaron **cero**
nombres sin emparejar. Lo que falta ya no es resoluble: FBref no publica xG
antes de ~2017-18 y el histÃ³rico arranca en 2014.

**No intentes automatizar esto bajando el umbral.** EstÃ¡ demostrado en el
propio archivo SQL: con score ~72 el matcher propone `Newcastle Utd` â†’
`manchester united`, `Leeds United` â†’ `sheffield united` y `Ath Paranaense` â†’
`parana`, que son tres clubes distintos en cada caso. Y por encima de ese
score hay aciertos legÃ­timos que se perderÃ­an. No existe umbral que separe
ambos grupos.

Los alias se aplican DESPUÃ‰S del backfill (necesitan que los equipos existan);
`setup_fase1.sh` tiene ahora un paso 4b para eso, y el SQL avisa por
`RAISE WARNING` si algÃºn equipo canÃ³nico no existe todavÃ­a.

### DocumentaciÃ³n actualizada (instrucciÃ³n permanente del usuario)

El usuario pidiÃ³ que README y model-card se actualicen con cada hallazgo, sin
esperar a que lo pida. Guardado en memoria. En esta tanda:

- README: corregida la afirmaciÃ³n falsa sobre el xG de Liga MX y BrasileirÃ£o,
  con la tabla de cobertura real medida; aÃ±adida la mediciÃ³n RPS contra el
  mercado; actualizados mapa de fases, estructura, calendario de procesos y
  tabla de fuentes; documentado el bloqueo de Cloudflare en FBref.
- `model_card`: quitada la limitaciÃ³n falsa sobre el xG latinoamericano y
  **aÃ±adida la de que el modelo no bate al cierre de Pinnacle**. Publicar eso
  es coherente con la tesis del producto: ocultarlo es lo que hace increÃ­ble
  al sector.
- `crontab` y `/admin/run/xg`: apuntan a `xg_worldfootball`, no al scraper
  bloqueado.

**Nota histÃ³rica (previo a Postgres):** no habÃ­a Postgres ni datos reales en este
entorno. Los 48 tests corren sobre datos simulados y verifican la matemÃ¡tica
(recuperaciÃ³n de parÃ¡metros, ausencia de fugas point-in-time, coherencia
entre el 1X2 vectorizado del calibrador y el de `pricing.py`). Nada se ha
ejecutado contra el histÃ³rico real ni contra la API de alineaciones. La
lista de comprobaciones con datos reales estÃ¡ en `harness/tareas.md`.

---

## 2026-09-22 â€” MLS, Champions y Europa League: competiciÃ³n deja de ser liga

De 7 ligas a **8 ligas + 2 copas**, 31.041 â†’ 37.650 partidos.

### La decisiÃ³n de diseÃ±o que condicionaba todo lo demÃ¡s

Hasta aquÃ­ "liga" y "competiciÃ³n" eran lo mismo, y todo el sistema se apoyaba
en ese supuesto sin decirlo. Meter la Champions lo rompe.

La salida fÃ¡cil habrÃ­a sido dar de alta equipos bajo `league_id='eu.ucl'`.
HabrÃ­a funcionado, no habrÃ­a dado ningÃºn error, y habrÃ­a sido destructiva: el
Real Madrid de Champions serÃ­a un club DISTINTO del de LaLiga, con 6-13
partidos por temporada, ningÃºn rival en comÃºn y ataque/defensa prÃ¡cticamente
en el prior. MÃ¡s de cien clubes duplicados en el catÃ¡logo.

La separaciÃ³n es:

- `matches.league_id` â†’ la **competiciÃ³n** del partido.
- `teams.league_id` â†’ la liga **domÃ©stica** del equipo.

El esquema ya lo permitÃ­a: no habÃ­a ninguna restricciÃ³n que obligara a que
coincidieran. `db/007_competiciones.sql` aÃ±ade `cross_league` para marcar las
competiciones donde no coinciden, y todo lo demÃ¡s se deriva de ahÃ­.

Consecuencias que hubo que propagar a mano (y que son la parte que se olvida):

- Toda consulta que alimenta al modelo (`train.py`, `daily.py`) trae ahora
  `th.league_id AS home_league` y `ta.league_id AS away_league`.
- `lambdas()`, `knows()` y `predict()` aceptan las dos ligas, en Dixon-Coles y
  en Kalman. Sin los parÃ¡metros se comportan como antes (la liga domÃ©stica ES
  la competiciÃ³n), asÃ­ que el histÃ³rico y los artefactos viejos siguen valiendo.
- `ingest/uefa_cups.py` NUNCA crea equipos: descarta el partido.
- `ingest/fixtures.py` en competiciones `cross_league` solo acepta coincidencia
  EXACTA. Buscando a la vez en todas las ligas, un difuso de 95 puntos puede poner
  un club europeo encima de uno latinoamericano de nombre parecido y contaminar
  dos historiales de golpe. Fijado por `tests/test_fixtures_cross_league.py`.

### El tÃ©rmino `strength`: lo que las copas aportan de verdad

No es poder apostarlas. Es que son los ÃšNICOS partidos entre equipos de ligas
distintas, y por tanto lo Ãºnico que permite comparar ligas entre sÃ­.

El modelo impone suma cero de ataque y defensa DENTRO de cada liga. Eso
significa que un ataque de 0,3 en Eredivisie y uno de 0,3 en LaLiga no estÃ¡n
en la misma escala, y dentro de los datos domÃ©sticos **no hay absolutamente
nada** que las conecte: el nivel de liga y `base[liga]` son intercambiables.

La formulaciÃ³n elegida aÃ±ade un desplazamiento por liga con signo opuesto en
las dos intensidades:

```
log lam = base[comp] + ha[comp] + (atk[h] + str[lg_h]) - (dfn[a] + str[lg_a])
log mu  = base[comp]            + (atk[a] + str[lg_a]) - (dfn[h] + str[lg_h])
```

La propiedad que hace que esto sea seguro: **en un partido domÃ©stico lg_h ==
lg_a y el tÃ©rmino se cancela exactamente**. Por eso se pudo aÃ±adir sin volver
a validar las ocho ligas. `tests/test_cross_league.py` lo comprueba
recalculando la lambda a mano sin el tÃ©rmino y exigiendo igualdad a 1e-9.

Verificado sobre simulaciÃ³n con dos ligas de nivel deliberadamente distinto:
con 400 cruces recupera 0,32 de una diferencia sembrada de 0,40. El
encogimiento (`POOL_STRENGTH = 300`) es deliberado y la muestra real es aÃºn
mÃ¡s pequeÃ±a.

### El lÃ­mite honesto: 406 cruces de 3.308

Solo sirven los partidos con los DOS equipos en el catÃ¡logo. El resto
involucra ligas que no tenemos:

| paÃ­s | partidos perdidos |
|---|---|
| Alemania | 633 |
| Francia | 464 |
| Portugal | 380 |
| BÃ©lgica | 264 |
| Rusia | 252 |

Dar de alta Bundesliga, Ligue 1 y Primeira multiplicarÃ­a por ~4 la muestra que
identifica `strength`, y las tres estÃ¡n gratis en football-data (`D1`, `F1`,
`P1`) y en FBref (`GER_M`, `FRA_M`, `POR_M`). Es la ampliaciÃ³n con mejor
relaciÃ³n coste/beneficio que queda pendiente. Anotada en `tareas.md`.

### Y las copas NO son apostables todavÃ­a

No existe histÃ³rico gratuito de cuotas de Champions ni de Europa League:
football-data.co.uk solo cubre ligas domÃ©sticas y el release de copas de
worldfootballR_data da resultado y xG pero ni un precio. Sin cierre no hay
baseline de mercado â†’ no se pueden evaluar, ni calibrar, ni medir CLV. Entran
como datos de ENTRENAMIENTO. Que sean apostables depende de que `odds_worker`
acumule cierres propios.

### Hallazgo lateral: Argentina SÃ tiene xG (0% â†’ 62,5%)

`xg_worldfootball.py` decÃ­a, con razÃ³n, que Argentina solo existe en `.rds` y
que no compensaba aÃ±adir `pyreadr` por una sola liga. **Esa decisiÃ³n estaba
bien tomada y aun asÃ­ habÃ­a caducado**: las copas europeas tampoco tienen CSV,
asÃ­ que `pyreadr` era obligatoria de todos modos. Con la dependencia ya dentro,
Argentina entrÃ³ gratis: 2.304 partidos con xG en una pasada.

La lecciÃ³n es general y vale la pena tenerla presente: **una decisiÃ³n de "no
compensa" depende del coste de la alternativa, y caduca cuando ese coste
cambia.** Cuando se amplÃ­a el alcance, toca re-revisar las decisiones negativas
escritas en los mÃ³dulos, no solo aÃ±adir cÃ³digo nuevo.

Lo que Argentina sigue sin tener es el fichero tiro a tiro: solo el xG
agregado. Sin PSxG, sin distancia, sin estado del partido.

### Tres bugs encontrados de paso

1. **`harness_check.sh` daba "OK" sin correr un solo test.** ElegÃ­a `python3`,
   que en Windows resuelve al stub de la Microsoft Store: arranca, responde a
   `--version`, y no tiene ninguna dependencia. El script imprimÃ­a
   "(pytest no instalado)" y seguÃ­a adelante con cÃ³digo de salida 0. Ahora
   prefiere `.venv` y **falla** si no encuentra pytest. Un chequeo que avisa y
   sigue es peor que no tenerlo: da confianza falsa.

2. **`requirements.txt` no se podÃ­a instalar.** `soccerdata==1.8.7` entra en
   conflicto con `lxml==5.3.0` y `pip install -r` aborta con
   ResolutionImpossible. Solo lo usa `xg_fbref.py`, que el README ya da por
   inservible (Cloudflare). Comentado, con la decisiÃ³n pendiente en `tareas.md`.

3. **El chequeo de salud del calendario iba a alertar todos los dÃ­as.**
   `check_fixtures_horizon` exigÃ­a partidos en 10 dÃ­as a TODAS las ligas
   activas. La MLS para el invierno y las copas tienen huecos de meses entre
   eliminatorias. Ahora solo avisa de competiciones en juego (con algÃºn
   partido terminado en las Ãºltimas 3 semanas). Una alerta que salta a diario
   por algo normal se deja de leer, y con ella la del dÃ­a que sÃ­ importa.

### Y uno mÃ­o, del mismo tipo que ya habÃ­a cometido

`INSERT ... CASE WHEN %s IS NULL` en `uefa_cups.py` â†’ `IndeterminateDatatype`.
Es el tercer encuentro con la misma trampa de psycopg (parÃ¡metro suelto sin
tipo inferible). Resuelto decidiendo el valor en Python en vez de en SQL.
TambiÃ©n volviÃ³ a aparecer el `%` dentro de un comentario SQL: `db.execute()`
interpola aunque no pases parÃ¡metros, asÃ­ que un "0%." en un comentario rompe
el fichero entero.

---

## 2026-09-22 â€” Bundesliga, Ligue 1 y Primeira: aÃ±adidas por los cruces, no por sÃ­ mismas

De 8 ligas + 2 copas a **11 ligas + 2 copas**, 37.650 â†’ **50.079 partidos**.

La razÃ³n no es que sean ligas atractivas, que lo son. Es que eran las tres que
mÃ¡s partidos de copa estaban tirando a la basura. `uefa_cups.py` descarta todo
cruce en el que alguno de los dos equipos no estÃ© en el catÃ¡logo, y el desglose
de descartes lo decÃ­a sin ambigÃ¼edad: Alemania 633, Francia 464, Portugal 380.

**Resultado: los cruces utilizables pasaron de 406 a 1.111 (Ã—2,7).** Que es lo
Ãºnico que identifica el tÃ©rmino `strength`, es decir, lo Ãºnico que permite
comparar la fuerza de una liga con la de otra.

Coste real: casi nulo. Las tres estÃ¡n en el formato PRINCIPAL de
football-data.co.uk, asÃ­ que `ingest_season` las carga sin tocar una lÃ­nea de
cÃ³digo; y las tres tienen fichero tiro a tiro en FBref (`GER_M`, `FRA_M`,
`POR_M`). Lo Ãºnico a mano fueron 19 alias (`db/011_aliases_europa.sql`).

### Los tres alias que no se podÃ­an dejar al emparejador difuso

- **`Paris S-G`** se queda en 82 puntos contra `Paris SG` y no resuelve. Bajar
  el umbral para capturarlo lo pone a tiro de **`Paris FC`**, que es otro club
  de la misma ciudad y tambiÃ©n estÃ¡ en el catÃ¡logo.
- **`VitÃ³ria`** a secas es GuimarÃ£es, no SetÃºbal. Comprobado por fechas:
  aparece de forma continua de 2018 a 2025, mientras FBref llama
  `VitÃ³ria SetÃºbal` al otro, que ademÃ¡s dejÃ³ la Primeira en 2020.
- **`B-SAD`** es Belenenses SAD. Se mapea a `Belenenses` porque es lo que hace
  football-data: su histÃ³rico usa ese Ãºnico nombre de 2014 a 2022 sin separar
  el club original de la escisiÃ³n. AquÃ­ se HEREDA esa decisiÃ³n en vez de tomar
  una distinta, para que las dos fuentes sigan cuadrando. No es la decisiÃ³n
  "correcta" en abstracto; es la que mantiene el join sano.

### DÃ³nde parar

El siguiente escalÃ³n es mucho peor: BÃ©lgica, Rusia, Ucrania, TurquÃ­a y Grecia
sumarÃ­an ~1.160 cruces, pero son **cinco** ligas para menos muestra de la que
dieron **tres**, varias fuera del formato principal de football-data, y con
clubes que rotan mÃ¡s en Europa. Rendimientos decrecientes claros. Anotado en
`tareas.md` como "solo si se quieren esas ligas por sÃ­ mismas".

### Lo que NO cambiÃ³, y conviene no olvidarlo

El modelo sigue sin batir al mercado. Remedido con el mismo protocolo Kalman:
el delta por liga se mueve como mucho en la cuarta cifra decimal y la MLS
aterriza en âˆ’0.00590, exactamente donde las demÃ¡s.

**Ampliar el catÃ¡logo no crea ventaja.** Es la misma conclusiÃ³n que para los
mercados derivados: mÃ¡s ligas son mÃ¡s partidos de la misma calidad de
predicciÃ³n, no una fuente de edge nueva. Lo que estas tres ligas mejoran es un
parÃ¡metro concreto (`strength`), no el acierto.

---

## 2026-09-22 â€” Ideas futuras del FPL Decision Engine, sin integraciÃ³n directa

Se revisÃ³ `percivalmahwaya/fpl-decision-engine` como referencia externa. No se
integra: resuelve Fantasy Premier League a nivel de jugador, con SQLite,
Streamlit y un optimizador de plantillas, mientras QuantFut predice partidos y
precios contra mercado. AdemÃ¡s, el repositorio externo no muestra una licencia
que autorice copiar cÃ³digo.

Se conservan tres ideas metodolÃ³gicas para cuando exista suficiente histÃ³rico
de alineaciones y cuotas:

- **Alineaciones como informaciÃ³n nueva, no como otro modelo sobre los mismos
  goles.** Estimar su efecto sobre `log(lambda_home)` y
  `log(lambda_away)` usando continuidad del XI, ausencias y eventualmente
  ratings por jugador.
- **Champion/challenger real.** El ajuste de alineaciones correrÃ¡ en sombra y
  solo podrÃ¡ promoverse si mejora RPS/log-loss secuencial y CLV previo al
  cierre en varias ligas. La infraestructura de artefactos y puertas ya
  existente se reutiliza; no se importa la implementaciÃ³n FPL.
- **Zona de abstenciÃ³n.** Medir mediante bootstrap o reentrenamientos cuÃ¡nto
  varÃ­an probabilidades y edges. Un edge dentro de ese ruido no debe producir
  un pick. El umbral se estimarÃ¡ en unidades de QuantFut; no se copia el valor
  del sistema FPL y no sustituye al `edge_shrinkage`.

No se adoptan su modelo de puntos por jugador, MILP de plantilla, recolector
FPL, SQLite, GitHub Actions ni Streamlit como frontend comercial. Streamlit
solo seguirÃ­a siendo opcional como vista personal de solo lectura; Grafana ya
es el panel operativo oficial de QuantFut.

---

## 2026-09-22 â€” SciKick queda como referencia para el frontend posterior

Se revisÃ³ `Pa004/scikick` y se conserva como referencia para el frontend de la
Fase 3, no como trabajo inmediato. La razÃ³n es de orden de dependencias: primero
deben estabilizarse la API y los pendientes de las fases anteriores para no
construir la interfaz sobre contratos que todavÃ­a puedan cambiar.

Cuando llegue esa fase, se podrÃ¡n adaptar su estructura React/TypeScript, las
pÃ¡ginas de partido, la navegaciÃ³n de mercados, los grÃ¡ficos de calibraciÃ³n, el
tema claro/oscuro y la internacionalizaciÃ³n. Se conservarÃ¡ el aviso de su
licencia MIT. No se adoptarÃ¡n su backend, SQLite, sus modelos predictivos ni su
lÃ³gica de `value`; QuantFut seguirÃ¡ siendo la fuente de datos, probabilidades,
selecciÃ³n de picks y control de acceso.

---

## 2026-09-22 â€” Orden Elo â†’ mercado â†’ XI en sombra

Se implementÃ³ el baseline Elo secuencial y un constructor Ãºnico de features
point-in-time. Ambos retrasan dos horas el uso de resultados y tiros cuando no
hay timestamp de finalizaciÃ³n: un partido iniciado 30 minutos antes no puede
filtrar su marcador a otro. Las regresiones y ablaciones siguen siendo
challengers de diagnÃ³stico; las cuotas histÃ³ricas de cierre no se tratan como
features desplegables a T-60.

La comparaciÃ³n de tres vÃ­as sobre 1.907 partidos comunes de julio de 2025 a
enero de 2026 dio RPS Dixon-Coles 0,20245, Elo 0,20533 y Pinnacle 0,19561.
La lecciÃ³n es mantener Elo como control Ãºtil, no promover complejidad por
ganarle a Elo. Las cuotas sharp locales terminan el 14 de enero de 2026;
para la evaluaciÃ³n actual estÃ¡n obsoletas. La puerta de promociÃ³n bloquea
mercado con mÃ¡s de 30 dÃ­as de antigÃ¼edad.
El bootstrap semanal favoreciÃ³ a Dixon-Coles frente a Elo por 0,00288 RPS
(IC 95 %: 0,00053â€“0,00506) y a Pinnacle frente a Dixon-Coles por 0,00684
(IC 95 %: 0,00350â€“0,01061). Las pequeÃ±as mejoras de Elo o tiros sobre el
cierre en un Ãºnico holdout no sustituyen una prueba con cuotas disponibles
en el momento operativo.

El XI solo se convierte en ajuste de lambdas si acumula histÃ³rico temporal
suficiente y supera su holdout. Para medir CLV real se aÃ±adiÃ³ una captura
`post_xi` condicionada a ambos XI, anterior a `close`: sin esa separaciÃ³n, el
CLV serÃ­a cero por construcciÃ³n. La migraciÃ³n de sombra se aplicÃ³ al Postgres
local sin tocar predicciones ni picks publicados. Faltan claves de API-Football
y The Odds API para obtener nuevas alineaciones y cuotas, asÃ­ que no se ha
observado CLV real ni se ha promovido challenger alguno.
La carga de entrenamiento exige ahora `window_tag='close'` de forma explÃ­cita;
la vista heredada elegÃ­a simplemente el Ãºltimo snapshot y podrÃ­a confundir la
nueva ventana `post_xi` con un cierre cuando faltase este Ãºltimo.

---

## 2026-09-22 â€” Claves reales conectadas: lo que la API enseÃ±a y los tests no

Se configuraron y verificaron las dos claves. Lo importante no es que
funcionen, sino los cuatro problemas que solo aparecen al llamar de verdad.

### El plan Free de API-Football no puede operar el sistema, y no por la cuota

Lo que descarta ese plan no son las 100 peticiones diarias: es que **solo da
acceso a las temporadas 2022â€“2024**. La temporada en curso responde
`Free plans do not have access to this season`. Sin temporada en curso,
`ingest/fixtures.py` no puede poblar `matches` con partidos `scheduled`; sin
esas filas, `_pending_windows` del odds_worker no encuentra nada que capturar,
`ingest/lineups.py` no tiene partidos en ventana y `post_xi` nunca se dispara.
La cadena entera de datos operativos cuelga de ahÃ­. La clave Free sirve para
verificar IDs y formas de respuesta, que es justo lo que estaba pendiente.

### Tres bugs del cliente que solo se ven con una clave en la mano

1. **El ritmo de llamadas estaba fijado para otro plan.** `MIN_INTERVAL = 0.35`
   (~170 req/min) estaba pensado como "por debajo de todos los planes"; el Free
   son **10 req/min**. La cuarta llamada seguida ya devolvÃ­a 429. Ahora el
   intervalo se deriva de `API_FOOTBALL_RPM`, que es un dato del plan y no una
   constante del cÃ³digo.
2. **El 429 entraba en el reintento exponencial genÃ©rico**, que espera 2 s y
   vuelve a chocar contra el mismo lÃ­mite por minuto. Ahora es `RateLimited` y
   espera al minuto siguiente.
3. **Los errores de PLAN se reintentaban cuatro veces.** Son permanentes por
   definiciÃ³n: la suscripciÃ³n no va a cambiar entre reintentos. Cada uno
   consumÃ­a una peticiÃ³n de las 100 del dÃ­a, asÃ­ que el modo de fallo era
   quedarse sin cuota justo cuando algo estaba mal configurado. Ahora
   `PlanError` no es reintentable.

Los tres comparten la misma forma: el proveedor devuelve **HTTP 200** y mete el
problema en el cuerpo, asÃ­ que sin distinguir clases de error todo acaba en el
mismo reintento ciego.

### Los IDs de competiciÃ³n estaban bien; el verificador no

Los 13 `api_football_id` y los 13 `odds_api_key` son correctos y estÃ¡n activos.
Pero `verify_league_ids()` daba FALLO en Champions y Europa League: comparaba
el paÃ­s, y API-Football archiva las competiciones continentales bajo `World`
mientras el catÃ¡logo local dice `Europe`. Un verificador que da falsos
positivos es peor que no tenerlo, porque entrena a ignorarlo. Ahora, para las
`cross_league`, comprueba `type == "Cup"` y el nombre.

### La coincidencia exacta no era paranoia: era necesaria, y faltaba en un sitio

Ejecutado `_resolve` contra fixtures reales de Champions, se confirmÃ³ lo que
`CLAUDE.md` advertÃ­a, con nÃºmeros:

    'Paris Saint Germain'  -> mejor candidato difuso 'San Martin S.J.'  (61)
    'Atletico Madrid'      -> mejor candidato difuso 'Atletico MG'      (77)
    'Rangers'              -> mejor candidato difuso 'Angers'           (92)

El tercero **supera el umbral de auto-aceptaciÃ³n de 90**. Y `resolve_team`
graba como alias permanente todo difuso aceptado, asÃ­ que no habrÃ­a sido un
partido mal emparejado sino la fuente contaminada para siempre. `fixtures.py`
ya estaba protegido; **`odds_worker.py` no**: resolvÃ­a los eventos de copa con
`league_id=None`, es decir, difuso contra las 13 competiciones a la vez. Por
eso `resolve_team` pasa a exigir coincidencia exacta POR DEFECTO, y el difuso
queda detrÃ¡s de `exact=False`. `tests/test_resolve_exacto.py` fija los tres
casos, incluido el que pasa el umbral.

### El coste de The Odds API era cinco veces el estimado, y por un motivo Ãºtil

Recalculado con datos reales (el endpoint `/events` cuesta 0 crÃ©ditos, asÃ­ que
se leyÃ³ el calendario anunciado de las 13 competiciones y se simulÃ³
`_pending_windows` sobre Ã©l): **~1.935 llamadas/mes**, o sea ~11.610
crÃ©ditos/mes con `eu,us Ã— h2h,totals,spreads`. El README daba ~2.160 para 7
ligas.

El factor cinco no viene de tener casi el doble de competiciones. Viene de que
**el coste lo manda el nÃºmero de huecos de 10 minutos distintos, no el de
partidos**: una llamada trae todos los partidos de esa competiciÃ³n que entren a
la vez en la misma ventana. LaLiga y la Serie A, con 20 partidos en 14 dÃ­as,
cuestan mÃ¡s que la MLS con 33, porque la MLS concentra kickoffs. Las copas son
lo mÃ¡s barato que hay: juegan todas la misma tarde. La consecuencia prÃ¡ctica es
que **repartir los mismos partidos entre mÃ¡s competiciones encarece**, y que la
palanca barata para bajar el coste no es quitar ligas sino quitar ventanas.

El plan de $30 (20.000 crÃ©ditos) sigue alcanzando, con 1,7Ã— de margen en vez de
"de sobra". El de 500 no alcanza ni en la configuraciÃ³n mÃ¡s barata (1.935), asÃ­
que con esta clave el worker se ejecuta a mano, nunca desde el cron.

### Emparejamiento de nombres: 108 alias nuevos y dos trampas

El bootstrap con las dos fuentes auto-registrÃ³ 362 alias y dejÃ³ 283 a mano; se
curaron 108. De los que quedan, la mayorÃ­a son irresolubles por diseÃ±o (Celtic,
Rangers, Galatasaray, Slavia Prahaâ€¦ juegan las copas pero sus ligas no estÃ¡n en
el catÃ¡logo). Dos propuestas del difuso eran falsas y habrÃ­an pasado una
revisiÃ³n rÃ¡pida: `Remo` â†’ GrÃªmio (80) y `AtlÃ©tico HuracÃ¡n` â†’ AtlÃ©tico TucumÃ¡n
(81). Revisar esta lista por puntuaciÃ³n descendente es exactamente la forma de
tragÃ¡rselas.

---

## 2026-09-22 â€” La demostraciÃ³n del motor encontrÃ³ el fallo mÃ¡s caro del sistema

Se ajustÃ³ Dixon-Coles sobre los 48.372 partidos con objetivo (945 s) y se
recorriÃ³ la cadena completa contra cuotas REALES de la Premier: de-vig â†’
lambdas â†’ ~150 mercados â†’ edge â†’ encogimiento â†’ Kelly. El motor funciona: 20
partidos, 70 selecciones preciadas por partido desde dos lambdas, line shopping
entre 22 casas, 19 candidatos por encima de los umbrales.

Y los tres candidatos de mayor stake eran basura.

    Hull v Everton     away @ 2.18   modelo 0,9061  mercado 0,4659   2,00 u
    Fulham v Hull      home @ 1.74   modelo 0,9506  mercado 0,5785   2,00 u
    Ipswich v Fulham   away @ 2.70   modelo 0,5574  mercado 0,3781   2,00 u

### El mecanismo, que no es "datos viejos"

Hull vuelve a primera; no la jugaba desde 2017. Con media vida de 180 dÃ­as, la
suma de pesos de sus partidos es **0,0000**: sus `attack` y `defence` no los
deciden sus datos, los deciden el ridge y la restricciÃ³n de suma cero por liga.

Y no quedan en cero. Quedan en (âˆ’0,81, âˆ’0,79) mientras los 20 equipos activos
se sitÃºan entre +0,2 y +0,9, porque el centrado se calcula sobre los 35 equipos
del catÃ¡logo incluyendo 15 que ya no juegan: los ausentes son el contrapeso
negativo de los presentes. La distancia entre un equipo activo y uno de estos
es ~1,3 en ataque, o sea un factor e^1,3 â‰ˆ 3,7 en lambda. De ahÃ­ Î» = 4,046 /
0,371 en Fulham v Hull.

**Por quÃ© esto no contamina el resto:** en `lambdas()` el tÃ©rmino es
`(atk_h + s) âˆ’ (dfn_a + s)`, asÃ­ que un desplazamiento comÃºn se cancela entre
dos equipos activos. Solo NO se cancela en activo-contra-ausente. Es coherente
con que el RPS medido sobre partidos normales sea razonable.

### Las tres guardas existentes miraban el nÃºmero equivocado

- `knows()` daba **True**: comprobaba pertenencia al Ã­ndice, y Hull estÃ¡.
- `_confidence()` daba **`high`**: cuenta partidos de TODA LA VIDA, y Hull tiene
  cientos. El modelo pesa con media vida de 180 dÃ­as. Son dos magnitudes
  distintas y se estaba usando una para hablar de la otra.
- `EDGE_SHRINKAGE=0.55` dejaba el 97,53% en 53,64%, y `MAX_STAKE_UNITS=2.0`
  recortaba justo a lo que ya se apostaba.
- Y `both_teams_known` se guardaba en los metadatos sin que **nadie** lo usara
  para descartar.

Cada guarda parecÃ­a razonable por separado. Ninguna medÃ­a la cantidad correcta.

### Lo que distingue el caso peligroso del inofensivo

Un ascendido de verdad (sin historia) es **seguro**: no estÃ¡ en el Ã­ndice y
`lambdas()` lo lleva a la media de su liga. El peligroso es el contrario, el
que SÃ estÃ¡ en el Ã­ndice con muestra efectiva ~0, porque entonces no cae a la
media: carga un parÃ¡metro extremo del que el modelo estÃ¡ seguro.

La magnitud que los separa es la **muestra efectiva** â€”suma de pesos de
decaimientoâ€” y no existÃ­a. Ahora se calcula en `fit()`, se guarda en `DCParams`
(con default, para que los artefactos anteriores sigan cargando y devuelvan
`inf`: sin el dato no se puede AFIRMAR que falte muestra), la expone
`effective_n()`, la exige `knows()` y la mira `_confidence()`.

Se eligiÃ³ `low` en vez de descartar la predicciÃ³n: se sigue guardando, sirviendo
y auditando, pero `run()` ya la excluye del universo de picks con el filtro que
tenÃ­a. No se tocÃ³ el orden predecir â†’ sellar â†’ publicar.

Reparto en el modelo entrenado: **95 de 362 equipos tienen muestra efectiva
menor que 1**; 130 por debajo de 5, que es el umbral por defecto
(`MIN_EFFECTIVE_MATCHES`). No es un caso raro: son los tres ascendidos de cada
liga, cada agosto.

### Por quÃ© importa para la fase 2

Esto no da edge; evita pÃ©rdidas. Pero es la demostraciÃ³n empÃ­rica del punto 2.D
del plan: el sistema no tenÃ­a forma de distinguir "mi ventaja es real" de "mi
parÃ¡metro es ruido", y por construcciÃ³n apostaba el mÃ¡ximo justo donde mÃ¡s
ruido habÃ­a. La zona de abstenciÃ³n por bootstrap es la versiÃ³n general de esta
misma guarda; esta es el caso particular que se podÃ­a cerrar hoy y con un
nÃºmero exacto.

---

## 2026-09-22 â€” Plan Pro: la cadena operativa arranca, y dos alarmas eran mentira

Contratado el plan Pro de API-Football. Verificado contra `/status`: 300
req/min, 7.500/dÃ­a, temporada en curso incluida. `API_FOOTBALL_RPM` pasa de 10
a 300 y el intervalo entre llamadas del cliente baja de 6 s a 0,2 s solo.

Lo que cambia no es la cuota, es el acceso a la temporada EN CURSO. Primera
ingesta real de calendario: **173 partidos programados en 12 competiciones**.
De ahÃ­ cuelgan las ventanas de cuotas, las alineaciones a T-60 y el CLV, que
era todo lo que estaba esperando. `results.py` cerrÃ³ su primer partido y
encadenÃ³ la liquidaciÃ³n sin incidencias.

### Los nombres de la temporada en curso no se habÃ­an visto nunca

El catÃ¡logo venÃ­a de football-data.co.uk y FBref; API-Football escribe distinto.
17 equipos sin emparejar en la primera pasada, resueltos en
`db/013_aliases_api_football.sql` con dos tratamientos OPUESTOS y la distinciÃ³n
importa:

- **Alias** (mismo club, otra grafÃ­a): API-Football conserva la forma societaria
  completa y football-data la recorta â€” `Hamburger SV`, `SC Paderborn 07`,
  `1. FC KÃ¶ln`, `Estac Troyes`, `Hull City`. Todos caen entre 62 y 88, por
  debajo del umbral de 90.
- **Alta de equipo** (club que de verdad faltaba): `Remo`, `Gimnasia M.`,
  `Estudiantes de Rio Cuarto`, `Atlante FC`. `resolve_or_register` se negÃ³ a
  crearlos porque los cuatro tienen candidato difuso por encima del suelo de
  60, y **los cuatro candidatos eran falsos**: Remo (BelÃ©m) contra GrÃªmio
  (Porto Alegre) a 80, Gimnasia de Mendoza contra la de La Plata a 82.

Bajar el umbral habrÃ­a "resuelto" los cinco del primer grupo y fusionado los
cuatro del segundo con clubes ajenos. Es el mismo argumento de `db/011` y sigue
siendo el correcto: el umbral no se toca, los casos se miran uno a uno.

Los cinco de Champions que quedan (Club Brugge, Galatasaray, Sabah, Slavia
Praha, Viking) no se tocan: sus ligas no estÃ¡n en el catÃ¡logo y darlos de alta
bajo `eu.ucl` partirÃ­a historiales. Sus partidos se descartan a propÃ³sito.

### Dos alarmas permanentemente en rojo, que es lo mismo que apagadas

Con el sistema por fin produciendo datos reales, el chequeo de salud daba
fallos que no lo eran. Las dos causas son del mismo tipo: **la mÃ©trica no medÃ­a
lo que decÃ­a medir**.

1. **Calendario.** Preguntaba por partidos en los prÃ³ximos 10 dÃ­as cuando
   `fixtures.run()` ingiere 21. Con el calendario reciÃ©n traÃ­do y correcto,
   saltÃ³ en 10 competiciones a la vez: todas las europeas mÃ¡s Brasil y
   Argentina tenÃ­an su prÃ³ximo partido pasado ese plazo, porque estamos en
   parÃ³n de selecciones. Preguntar por una ventana mÃ¡s CORTA que la que se
   ingiere no puede distinguir "no hay partidos" de "no se han traÃ­do": solo
   sabe dar falsos positivos. El horizonte pasa a ser el mismo que el de la
   ingesta.

2. **Nombres sin emparejar: 362 fantasmas.** `history_fd._ensure_team` daba de
   alta el equipo e insertaba su alias con un INSERT a mano en vez de
   `register_alias`. Para la tabla de alias da igual; para `unresolved_names`
   no, porque solo `register_alias` marca la fila resuelta. Cada nombre nuevo
   pasaba antes por `resolve_team`, quedaba registrado como pendiente, y ahÃ­
   se quedaba **para siempre aunque todo hubiera funcionado**. El chequeo
   reportaba 362 nombres (84.887 apariciones, casi todos MLS) y recomendaba
   `bootstrap_aliases.py`, que ni siquiera toca la fuente `football_data`.

   Tras el arreglo y el cierre de las filas viejas: **371 â†’ 9**, y los 9 son
   los clubes de copa irresolubles por diseÃ±o. Ahora cuando esa alarma suene
   querrÃ¡ decir algo.

La lecciÃ³n es la misma de la guarda de muestra efectiva de esta misma sesiÃ³n:
tres guardas y dos alarmas, todas razonables por separado, todas midiendo la
cantidad equivocada. Lo que las destapÃ³ en los tres casos fue hacer correr el
sistema con datos de verdad.

---

## 2026-09-22 â€” Fase 2: implementado el plan. El cierre deja de ser el rival

Implementados los cuatro puntos del plan de fase 2. Lo que los une es una sola
lectura, y conviene tenerla clara antes que el cÃ³digo: **`w_model = 0.0001` no
dice "el modelo no sirve", dice "el modelo sirve para la FORMA, no para el
NIVEL"**. La forma es la matriz de marcadores, de la que salen ~150 mercados
coherentes entre sÃ­; eso el mercado no lo da. El nivel lo da el mercado, y
mejor.

### 1. La puerta comercial pasa a decidirse por CLV

Son dos afirmaciones distintas y solo una es alcanzable:

    "mi probabilidad es mejor que el consenso de cierre"   -> casi nadie
    "el precio que tomÃ© era mejor que el cierre que vino"  -> medible, y es
                                                              lo que se cobra

La puerta anterior exigÃ­a la primera (`beats_market_same_rows` en RPS) y se
conformaba, para el CLV, con una media no negativa. Es la peor combinaciÃ³n:
rechazaba todo por lo imposible y no filtraba nada por lo que importa, porque
una media positiva la produce cualquier racha.

`evaluate_clv_gate` exige ahora tres cosas a la vez: 300 apuestas liquidadas,
el intervalo de confianza del 95% del CLV **entero** por encima de cero, y al
menos 3 ligas con muestra propia. La tercera no es adorno: un CLV que solo vive
en una liga es un hallazgo sobre esa liga â€”o sobre una casa, o sobre un horario
de publicaciÃ³nâ€” y es lo primero que desaparece cuando esa casa limita la
cuenta. Batir al cierre se sigue reportando; ya no veta.

**No es un ablandamiento.** Se quita una condiciÃ³n inalcanzable y se endurece
la que sÃ­ discrimina. EstÃ¡ fijado en `tests/test_puerta_clv.py`, con un test
por cada una de las tres condiciones.

De paso: el parÃ¡metro `clv` de `evaluate_base_promotion` existÃ­a y **no se
pasaba nunca** desde `train.py`, asÃ­ que `ready_for_commercial_picks` era falso
por construcciÃ³n, no por mediciÃ³n. ParecÃ­a una puerta y era un tapÃ³n.

### 2. El ancla de mercado, y el brazo que faltaba

`model/market_anchor.py` invierte el 1X2 ya sin margen a las intensidades que
lo reproducen bajo Dixon-Coles. Ida y vuelta exacta a 1e-10.

Devuelve SIEMPRE el residuo, y no es cautela retÃ³rica: fijados los dos goles
esperados, la probabilidad de empate queda determinada, asÃ­ que la familia no
puede representar cualquier terna. Un mercado con empate al 10% y local y
visitante iguales no tiene soluciÃ³n â€”el ajuste se va a lambda = mu = 7,5 con
residuo 0,0127â€” y el mÃ³dulo lo dice en vez de devolver el ajuste menos malo con
cara de nÃºmero bueno.

El bug de diseÃ±o que esto cierra: `lineup_challenger.apply()` multiplica
`base_lam`, y `base_lam` venÃ­a de `predictions.home_lambda`, o sea **las
lambdas del modelo**. Con w_model â‰ˆ 0, ajustar por el XI unas lambdas peores
solo mueve una estimaciÃ³n peor. `shadow.py` gana dos brazos mÃ¡s
(`baseline_market` y `lineup_lambda_market`), y con los cuatro sobre las mismas
cuotas cada comparaciÃ³n aÃ­sla una sola cosa:

    modelo  -> modelo+XI    : Â¿el XI aporta?
    mercado -> mercado+XI   : Â¿aporta SOBRE lo que ya estaba preciado?
    modelo  -> mercado      : cuÃ¡nto de la diferencia era solo nivel

### 3. InformaciÃ³n nueva

El XI ya estaba construido y ahora tiene dÃ³nde apoyarse (punto 2). La seÃ±al de
noticias y lesiones vÃ­a LLM sigue **esperando una decisiÃ³n que no es tÃ©cnica**:
quÃ© medios por liga. No se inventa aquÃ­.

### 4. Los dos puntos matemÃ¡ticos, que resultaron ser uno

Iban en la lista como dos Ã­tems y se resuelven con la misma cantidad: cuÃ¡nto
varÃ­a el edge cuando los parÃ¡metros varÃ­an dentro de su propia incertidumbre.

`DixonColes.fit()` deja ahora el error estÃ¡ndar de `attack` y `defence` de cada
equipo. Se llegÃ³ a la fÃ³rmula por descarte, y los dos intentos fallidos la
explican mejor que ella misma:

1. **La curvatura del objetivo a secas** no vale: los pesos se normalizan por
   su media antes de entrar en la verosimilitud, asÃ­ que un dataset de 12 aÃ±os
   con media vida de 180 dÃ­as se comporta como si sus 48.000 partidos contaran
   enteros. Errores estÃ¡ndar unas cuatro veces demasiado pequeÃ±os.

2. **El estimador sÃ¡ndwich** `H^-1Â·VÂ·H^-1` arregla la escala y falla justo
   donde importa. Entrenado sobre los 48.372 partidos reales, los seis equipos
   con el error estÃ¡ndar MÃS PEQUEÃ‘O del modelo â€”o sea, los que decÃ­a conocer
   mejorâ€” eran los seis con muestra efectiva 0,0000: Chivas USA, QPR, CÃ³rdoba,
   Leones Negros, Cesena, Evian. Y es correcto en su propio marco: sin muestra
   no hay variabilidad muestral. Pero ese parÃ¡metro no lo fijan los datos, lo
   fija el ridge, y **un prior no es conocimiento**. Un nÃºmero que dice "de
   este equipo estoy segurÃ­simo" sobre un equipo del que no se sabe nada es
   peor que no tener nÃºmero.

3. **Corregir el sÃ¡ndwich con la muestra efectiva** `(Î£wÎ»)Â²/(Î£wÂ²Î»)` tampoco:
   esa expresiÃ³n es invariante a la ESCALA de los pesos, que es exactamente lo
   que aquÃ­ no se puede ignorar. 24 partidos de hace ocho aÃ±os, todos con el
   mismo peso minÃºsculo, "cuentan" como 24 observaciones. Mide cuÃ¡ntas
   observaciones contribuyen, no cuÃ¡nto pesan.

Lo que queda es la precisiÃ³n posterior con pesos crudos:

    se = 1 / sqrt( Î£ wÂ·Î»  +  2Â·ridgeÂ·media(w) )
                   \_____/    \______________/
                   los datos      el prior

Con muchos datos domina el primer tÃ©rmino. Sin datos el segundo, que es
diminuto, asÃ­ que el error estÃ¡ndar se dispara y el modelo declara que no sabe.
Las dos situaciones son el mismo nÃºmero, no dos reglas pegadas, y por eso la
abstenciÃ³n del equipo sin muestra sale sola sin una regla aparte.

Se ignoran los tÃ©rminos fuera de la diagonal: suficiente para decidir una
abstenciÃ³n, no para publicar un intervalo de confianza. EstÃ¡ dicho en el cÃ³digo.

`model/uncertainty.py` los propaga por Monte Carlo hasta el edge, y de la
distribuciÃ³n salen las dos decisiones de golpe:

    edge_floor = media - ZÂ·sd
    edge_floor <= 0  ->  ABSTENERSE: la ventaja no se distingue de cero
    edge_floor >  0  ->  encogimiento = edge_floor / media

Ese cociente es `EDGE_SHRINKAGE` pero **medido y por apuesta**. La constante
0,55 encogÃ­a igual una discrepancia sobre el Liverpool, del que hay veinte
partidos recientes, que una sobre un reciÃ©n ascendido del que hay tres. El
test que de verdad importa no es que el nÃºmero salga, es
`test_el_encogimiento_medido_premia_a_quien_esta_mejor_medido`: que
DISTINGA. Si no distingue, no vale mÃ¡s que la constante.

`UNCERTAINTY_ENABLED` apagado por defecto, como `META_BLEND_ENABLED` y
`RESIDUAL_ENABLED`: cambia cuÃ¡ntos picks se publican al dÃ­a y eso es decisiÃ³n
de negocio, no del cÃ³digo.

**Al medir si funciona, no confundir la mÃ©trica.** Esto no crea ventaja:
elimina apuestas de EV negativo. Sube el ROI realizado y NO debe mejorar el
RPS. Si alguna vez mejora el RPS, estÃ¡ mal planteado.

## 2026-09-22 â€” Bajas/lesiones: fuente decidida, no era el LLM

El backlog llevaba la tarea bloqueada como "vÃ­a LLM" (lectura de prensa local
por liga + extracciÃ³n NLP). El usuario encontrÃ³ que API-Football â€”el mismo
proveedor ya contratado en plan Pro para calendario y alineacionesâ€” tiene un
endpoint `/injuries` que da el dato ya estructurado (jugador, tipo de baja,
motivo) por prÃ¡cticamente cualquier liga. Eso descarta el diseÃ±o LLM por
completo para esta seÃ±al: no hay texto que extraer, asÃ­ que no hay coste de
inferencia recurrente ni riesgo de alucinaciÃ³n en el parseo, y el coste de
API es $0 incremental sobre lo ya pagado.

La restricciÃ³n de diseÃ±o que sÃ­ se hereda del plan original sigue vigente:
cada fila lleva su propio `captured_at`, y cualquier feature construida sobre
`injuries` tiene que respetar `as_of <= kickoff` en `features_pit`, igual que
todo lo demÃ¡s. Sin eso es fuga, no seÃ±al â€” el proveedor cambiado no cambia
esa regla.

DecisiÃ³n de diseÃ±o tomada al implementar: a diferencia de `lineups` (una
sola captura por partido dentro de T-90..T-20, porque el XI no cambia una
vez publicado), una baja se conoce con dÃ­as de antelaciÃ³n y su estado
evoluciona (duda â†’ confirmado), asÃ­ que `injuries.py` relee cada partido
cada `MIN_HOURS_BETWEEN_CHECKS` (4h) dentro de una ventana de 7 dÃ­as. Para
no reconsultar para siempre un partido sin bajas reportadas, se aÃ±adiÃ³
`injuries_capture_log`, que registra el intento aunque la respuesta estÃ©
vacÃ­a â€” sin eso, "no hay bajas" y "no se ha comprobado" son indistinguibles
y el ingest reintentarÃ­a cada partido en cada pasada sin parar.

TodavÃ­a no existe la feature de disponibilidad (equivalente a
`lineups.availability()`): `injuries.py` solo ingiere y almacena. Es el
siguiente paso, y necesita acumular datos primero â€” igual que pasÃ³ con
alineaciones.

## 2026-09-22 â€” Verificada cobertura de `/injuries`: hueco real en 3 ligas

Se comprobÃ³ `/injuries` contra las 13 competiciones (clave real, `league` +
`season` actual y tambiÃ©n por `fixture` suelto). 10 van bien. Tres no:
`mx.liga_mx`, `ar.primera`, `pt.primeira` devuelven 0 resultados para la
temporada 2026 en curso, tanto agregado como por partido, pese a tener 79,
400 y 62 partidos terminados esa misma temporada â€” no es que no haya
lesionados, es que el proveedor no tiene el dato ahÃ­. Con `season=2025` sÃ­
hay datos (166, 51, 77), lo que descarta un parÃ¡metro de temporada mal
calculado: es cobertura real ausente, exactamente el mismo patrÃ³n de "array
vacÃ­o con status 200" que ya se documentÃ³ para el xG de este mismo
proveedor. Anotado en README.md junto a esa advertencia porque es el mismo
fallo silencioso, no uno nuevo que inventar.

DecisiÃ³n: no se excluye a esas 3 ligas de `injuries.py` (el mÃ³dulo sigue
llamando al endpoint para las 13, tal como estÃ¡). No hay forma de
distinguir por una sola pasada "liga sin cobertura" de "liga sana sin
bajas hoy" â€” hace falta acumular varios ciclos de 4h y ver si CUALQUIER
partido de esas 3 ligas reporta alguna vez una baja; si nunca lo hace, ahÃ­
sÃ­ se confirma el hueco y se puede marcar la liga como "sin seÃ±al de
lesiones" en vez de asumir plantillas sanas.

AÃ±adida la vigilancia: `check_injuries_coverage()` en
`src/qf/ingest/health.py`, en la lista `CHECKS` que corre `health.run()`
diario. Cuenta, por liga, partidos distintos comprobados en
`injuries_capture_log` los Ãºltimos 30 dÃ­as y la suma de `n_reported`. Si una
liga acumula 15+ partidos comprobados con 0 bajas en total, es la misma
firma que ya se vio a mano con mx/ar/pt â€” salvo que esa liga ya estÃ© en
`KNOWN_INJURY_COVERAGE_GAPS`, para no alertar cada dÃ­a por algo ya
investigado y no accionable desde este lado (mismo principio que
`check_fixtures_horizon` con las ligas fuera de temporada: una alerta que
salta a diario por algo normal se deja de leer). El umbral de 15 partidos es
el mismo tipo de decisiÃ³n que `HORIZON_DAYS`: bajo con muestra chica da
falsos positivos, y aquÃ­ 15 partidos de una liga completa sin una sola baja
es prÃ¡cticamente imposible por azar si el proveedor sÃ­ tiene el dato.

---

## 2026-09-22 â€” La zona de abstenciÃ³n rechaza el 100% de los picks, y el nÃºmero cuadra

Reajustado el modelo con los errores estÃ¡ndar correctos (86 min) y pasada la
cadena completa del punto 4 sobre cuotas reales de la Premier.

Primero, la correcciÃ³n funciona. Los errores estÃ¡ndar son ahora **monÃ³tonos en
la muestra** a lo largo de cinco Ã³rdenes de magnitud:

    N_efectivo   equipos   se_attack (mediana)
    [0, 0.1)         75        21.56
    [0.1, 1)         20         1.26
    [1, 5)           35         0.55
    [5, 15)          61         0.31
    [15, 99)        171         0.19

Mejor conocidos: Bayern Munich (0,117), Inter Miami (0,121), Sp Lisbon (0,129).
Peor: CÃ³rdoba, QPR, Chivas USA, los tres a 23,7 con muestra 0,0000. Son
exactamente los mismos que la versiÃ³n con sÃ¡ndwich colocaba como los MEJOR
conocidos, con el orden invertido.

### Y entonces la abstenciÃ³n rechaza los 19 picks del dÃ­a

    con la constante 0,55:      19 picks
    con encogimiento medido:     0 picks

Ninguno sobrevive. Ni siquiera partidos entre equipos con 19-20 partidos
efectivos. La desviaciÃ³n tÃ­pica del edge va de 14 a 94 puntos porcentuales.

**No es un error del cÃ³digo, y la aritmÃ©tica lo dice sin ambigÃ¼edad.** Un
equipo bien medido tiene ~20 partidos efectivos a ~1,4 goles, o sea ~28 goles
observados. El error estÃ¡ndar de una tasa logarÃ­tmica con 28 eventos es
1/sqrt(28) = 0,19, que es exactamente el `se_attack` que sale del ajuste. De
ahÃ­, sd(log lambda) ~ 0,26: **la intensidad varÃ­a Â±26% a una sigma**. Con esa
variaciÃ³n, una cuota de 5,50 mueve el edge decenas de puntos. Es la varianza de
Poisson de los goles del fÃºtbol, no un defecto de la implementaciÃ³n.

Dicho de otro modo: la ventaja nominal del modelo (3-10%) es **un orden de
magnitud menor que el ruido de sus propios parÃ¡metros**.

Esto CONCUERDA con lo ya medido por caminos independientes â€”`w_model = 0.0001`,
derrota contra el cierre en las 7 ligasâ€” y es una comprobaciÃ³n cruzada
valiosa: dos mÃ©todos que no comparten nada llegan a la misma conclusiÃ³n.

### Pero Z = 1,0 no sirve como valor por defecto, y hay que decirlo

La regla `media - ZÂ·sd > 0` con Z=1 exige ~84% de confianza en que el edge es
positivo. Con sd de ese tamaÃ±o eso es inalcanzable por construcciÃ³n, asÃ­ que el
interruptor encendido significa hoy "no apostar nunca". Un mecanismo que
siempre dice no no estÃ¡ midiendo, estÃ¡ apagado con otro nombre.

Tres cosas que corregir antes de darlo por bueno:

1. **La regla es MÃS ESTRICTA que la Ã³ptima en valor esperado.** Para EV basta
   `E[p]Â·cuota > 1`; exigir que el suelo sea positivo es una decisiÃ³n de
   prudencia, no un resultado estadÃ­stico. Conviene no confundirlas.
2. **Mide incertidumbre ABSOLUTA, no relativa al mercado.** Lo que decide una
   apuesta es si nuestro error es menor que el suyo, y el mercado tambiÃ©n
   desconoce la lambda verdadera. Un modelo puede tener ventaja real con
   incertidumbre absoluta grande. La versiÃ³n correcta medirÃ­a la varianza de
   (p_modelo âˆ’ p_mercado), y con el ancla de mercado ya existe la pieza para
   hacerlo.
3. **Ordenar por media/sd no arregla la selecciÃ³n adversa.** Los dos
   candidatos que mÃ¡s se acercan a pasar son justo los de mayor edge bruto
   (47,9% y 50,4%), que son los mÃ¡s sospechosos de ser error del modelo. El
   cociente se queda cerca de 1 para todos, asÃ­ que no discrimina donde hace
   falta.

Los cocientes media/sd del dÃ­a: 0,995 Â· 0,957 Â· 0,829 Â· 0,792 Â· 0,682 Â· 0,671 Â·
0,613... Con Z=0,95 pasarÃ­an dos; con Z=0,80, cuatro. Ese es el rango en el que
hay que calibrar contra histÃ³rico liquidado, no en 1,0 por convenciÃ³n.

---

## 2026-09-22 â€” Caddy como servicio de `docker-compose.yml`

El README ya documentaba un Caddyfile de ejemplo (secciÃ³n "Proxy con TLS"),
pero era un paso manual fuera del repo: no habÃ­a ni `Caddyfile` ni servicio
`caddy` en `docker-compose.yml`. `docker compose up -d` no dejaba la API
alcanzable por HTTPS desde ningÃºn dominio; solo `127.0.0.1:8000`.

Se aÃ±adiÃ³ el servicio `caddy` (imagen `caddy:2-alpine`, puertos 80/443,
volÃºmenes `caddydata`/`caddyconfig` para el certificado y el estado interno) y
un `Caddyfile` en la raÃ­z. DecisiÃ³n de diseÃ±o: `reverse_proxy` apunta a los
nombres de servicio de Compose (`api:8000`, `grafana:3000`), no a `localhost`
como en el ejemplo original del README â€” ese ejemplo asumÃ­a Caddy instalado en
el host, no dentro de la misma red de Docker Compose.

Grafana se mantiene cerrado por IP (`@yo remote_ip {$GRAFANA_ALLOWED_IP}`)
ademÃ¡s del login, tal como ya decidÃ­a el README: es el panel de operaciÃ³n
privado, no tiene por quÃ© ser alcanzable desde internet en general. Se aÃ±adiÃ³
`GRAFANA_ALLOWED_IP` a `.env.example` porque antes esa IP estaba hardcodeada
como placeholder en el bloque de cÃ³digo del README y no era una variable real
del sistema.

Pendiente explÃ­cito, no resuelto aquÃ­: esto solo pone el proxy TLS en pie.
Sigue sin existir auth de suscriptor no-Telegram ni rate limiting en las rutas
pÃºblicas (`harness/tareas.md`); exponer la API con HTTPS no sustituye a esas
dos garantÃ­as antes de anunciarla desde la web.

---

## 2026-09-22 â€” Auth de suscriptor (email+contraseÃ±a) y hardening de la API

DecisiÃ³n del usuario, explÃ­cita: la API es de uso exclusivo para su propia web
y una futura app Flutter, pero SIGUE vendiendo picks a suscriptores reales
(no es acceso solo para Ã©l) â€” asÃ­ que "exclusivo" describe quiÃ©n puede
integrarse (nada de terceros, sin API pÃºblica documentada), no quiÃ©n se
autentica. Y sobre el criterio de cliente: eligiÃ³ "solo JWT de sesiÃ³n" en vez
de aÃ±adir un secreto de cliente por plataforma, porque un secreto embebido en
una app Flutter siempre se puede extraer con ingenierÃ­a inversa â€” darÃ­a una
sensaciÃ³n de seguridad que no es real, a cambio de mantenimiento real
(rotarlo si se filtra el binario).

### Por quÃ© el diseÃ±o previo no alcanzaba, mÃ¡s allÃ¡ de "falta implementar"

`/v1/auth/telegram` era el Ãºnico login y depende de `TG_BOT_TOKEN`, que el
usuario no tiene configurado â€” es decir, el login de suscriptor llevaba
tiempo roto de facto, no solo pendiente. AdemÃ¡s el JWT de sesiÃ³n duraba 30
dÃ­as sin ningÃºn mecanismo de revocaciÃ³n, y `JWT_SECRET` cuando faltaba se
generaba aleatoriamente EN SILENCIO (`os.getenv("JWT_SECRET") or
secrets.token_hex(32)`): cada reinicio del proceso invalidaba todas las
sesiones sin avisar, y con mÃ¡s de una rÃ©plica cada una firmarÃ­a con un
secreto distinto. Ninguno de los dos era un bug visible â€” son exactamente el
tipo de fallo silencioso que este proyecto ya se ha encontrado varias veces
(unidades del stake, `harness_check.sh` sin pytest, fechas UTC vs zona del
servidor).

### Lo que se construyÃ³

- **`db/015_subscriber_auth.sql`**: `password_hash` (nullable â€” los
  suscriptores viejos de Telegram no tienen y NULL nunca autentica, no abre
  una puerta), `email_verified`, `failed_login_count`, `locked_until` en
  `subscribers`; tabla `refresh_tokens` (hash del token, nunca el valor en
  claro, con cadena de rotaciÃ³n `replaced_by`); tabla `auth_audit_log`.
- **`src/qf/api/auth.py`** (nuevo mÃ³dulo, separado de `main.py` para poder
  probarlo sin FastAPI ni Postgres real): Argon2id para contraseÃ±as (ganador
  del Password Hashing Competition, recomendaciÃ³n OWASP actual sobre bcrypt
  por su costo de memoria configurable), polÃ­tica de contraseÃ±a mÃ­nima (12
  caracteres, sin exigir sÃ­mbolos â€” la guÃ­a NIST 800-63B es explÃ­cita en que
  eso empuja a "Passw0rd!" en vez de a contraseÃ±as largas de verdad), emisiÃ³n
  de access JWT de 15 minutos, refresh token opaco de 30 dÃ­as con rotaciÃ³n en
  cada uso y **detecciÃ³n de reuso**: si se presenta un refresh ya revocado
  (seÃ±al de que un atacante estÃ¡ usando en paralelo un token robado), se
  revoca toda la cadena de sesiones del suscriptor, no solo esa.
- **Endpoints nuevos** en `main.py`: `POST /v1/auth/register`,
  `/login`, `/refresh`, `/logout`. `/v1/auth/telegram` se conserva pero ahora
  devuelve 404 explÃ­cito sin `TG_BOT_TOKEN` en vez de fallar mÃ¡s abajo con un
  HMAC que nunca va a poder verificar nada.
- **EnumeraciÃ³n de cuentas cerrada**: registrar con un email ya existente y
  hacer login con contraseÃ±a incorrecta devuelven el mismo mensaje genÃ©rico
  que "credenciales invÃ¡lidas" â€” no confirman si el email estÃ¡ registrado.
- **Bloqueo de cuenta**: `LOGIN_MAX_ATTEMPTS` (5) fallos consecutivos
  bloquean la cuenta `LOGIN_LOCKOUT_MINUTES` (15). Protege contra fuerza
  bruta dirigida a un email; el rate limit por IP (mÃ¡s abajo) protege contra
  fuerza bruta distribuida entre muchas cuentas.
- **Rate limiting real**: no existÃ­a NINGUNO antes de hoy â€” ni global ni en
  auth. `security_middleware` en `main.py` limita por IP TODAS las rutas
  (`RATE_LIMIT_DEFAULT_PER_MINUTE=60`) y mÃ¡s estricto en `/v1/auth/*`
  (`RATE_LIMIT_AUTH_PER_MINUTE=10`), usando `INCR` de Redis sobre una ventana
  fija â€” atÃ³mico, dos peticiones concurrentes no pisan el contador. La IP se
  toma de `X-Forwarded-For`, correcto solo porque Caddy (ver secciÃ³n anterior)
  es quien lo escribe y el cliente no puede llegar a la API sin pasar por Ã©l.
- **`JWT_SECRET` obligatorio en el arranque**: `main.py` ahora lanza
  `RuntimeError` si falta, en vez de generar uno efÃ­mero. Falla fuerte y
  temprano en vez de fallar silenciosamente en producciÃ³n.
- **Manejador de excepciones global**: cualquier excepciÃ³n no capturada
  devuelve `{"detail": "Error interno"}` con 500 en vez de dejar que algo se
  filtre (traceback, ruta de archivo, fragmento de SQL); el detalle real va
  al log del proceso, no a la respuesta.
- **Cabeceras de seguridad** en todas las respuestas
  (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`) y `Cache-Control: no-store` en `/v1` y `/admin` â€” no
  tiene sentido que un proxy o el navegador cacheen picks de pago o rutas de
  operaciÃ³n.
- **CORS**: el origen de desarrollo (`localhost:5173`) ya solo se aÃ±ade con
  `APP_ENV=development`; antes estaba siempre en la lista, incluida en
  producciÃ³n, sin ganar nada por tenerlo ahÃ­ (`allow_headers` tambiÃ©n se
  acotÃ³ de `["*"]` a los dos que la API realmente usa).

### Lo que se decidiÃ³ NO construir ahora, y por quÃ©

VerificaciÃ³n de email y reseteo de contraseÃ±a por correo requieren decidir un
proveedor SMTP (Resend/Postmark/SES) antes de escribir una sola lÃ­nea â€” no
tiene sentido dejar `email_verified` a medias sin forma real de enviar el
correo de verificaciÃ³n. Por eso `email_verified` existe en el esquema (para
no tener que migrar otra vez) pero no bloquea el login todavÃ­a. Cobros siguen
fuera de alcance, como ya decidÃ­a `harness/tareas.md`.

Un secreto de cliente por plataforma (HMAC firmado por build) se descartÃ³ por
decisiÃ³n explÃ­cita del usuario: aÃ±ade fricciÃ³n y mantenimiento (rotarlo si se
filtra el binario de la app) a cambio de una protecciÃ³n que no es real contra
un atacante dedicado â€” solo filtrarÃ­a bots automatizados poco sofisticados,
y eso ya lo cubre el rate limiting por IP.

### Tests

`tests/test_auth.py`, 12 casos, todos sobre lÃ³gica pura (hash/verify de
contraseÃ±a, polÃ­tica mÃ­nima, emisiÃ³n/expiraciÃ³n/tipo de access JWT, y el
contador de rate limit contra un Redis falso en memoria). Lo que necesita
Postgres real (rotaciÃ³n de refresh tokens, bloqueo de cuenta, auditorÃ­a) no
tiene test automatizado â€” mismo patrÃ³n que el resto de `main.py`, que no se
prueba con TestClient en este repo. Queda como verificaciÃ³n manual pendiente,
igual que el resto de rutas de la API en `harness/tareas.md`.

---

## 2026-09-22 â€” CorrecciÃ³n de alcance: sin cuentas de usuario en la API

En la misma sesiÃ³n que construyÃ³ el auth de suscriptor de arriba, el usuario
corrigiÃ³ el modelo de negocio: la API no va a tener suscripciones ni registro
de usuarios. Los pronÃ³sticos se sirven a su frontend, que es quien arma los
prompts del LLM para el usuario final y quien cobra las suscripciones â€” con
su propia base de datos de usuarios, que no vive en este repo.

Eso obligÃ³ a revisar una premisa que habÃ­a quedado sin cuestionar: Â¿la app
Flutter futura llama directo a esta API, o llama al backend del frontend? La
respuesta importa porque un secreto que vive en un cliente que corre en el
dispositivo del usuario â€”JavaScript de navegador, o el binario de una app
Flutterâ€” **siempre se puede extraer** con herramientas estÃ¡ndar (devtools,
apktool, frida). No es una debilidad de implementaciÃ³n que se arregle
ofuscando mejor: es una propiedad fÃ­sica de ese tipo de cliente. El usuario
confirmÃ³ el patrÃ³n BFF (Backend For Frontend): tanto la web como la futura
app Flutter le hablan a un backend propio suyo, y SOLO ese backend â€”que corre
en un servidor, no en el dispositivo del usuarioâ€” conoce el secreto que abre
esta API.

### Se revirtiÃ³ el trabajo de la entrada anterior, completo

- `db/015_subscriber_auth.sql` se eliminÃ³ sin haberse aplicado a ningÃºn
  Postgres real (se creÃ³ y se borrÃ³ en la misma sesiÃ³n).
- `src/qf/api/auth.py` (hash Argon2id, polÃ­tica de contraseÃ±a, access/refresh
  JWT, bloqueo de cuenta, auditorÃ­a) se eliminÃ³ completo.
- `POST /v1/auth/register|login|refresh|logout|telegram` se eliminaron de
  `main.py`: no hay usuario final que la API deba conocer.
- `PyJWT`, `argon2-cffi`, `email-validator` salieron de `requirements.txt`:
  ya no tienen consumidor.

Lo Ãºnico que sobreviviÃ³ del trabajo anterior fue el rate limiting por IP
(movido a `src/qf/api/ratelimit.py`, sigue haciendo falta con o sin cuentas:
un `SERVICE_TOKEN` filtrado sin lÃ­mite de tasa permite scraping sin freno) y
las cabeceras de seguridad / manejador de excepciones global de
`main.py`, que no dependÃ­an de la existencia de suscriptores.

### El diseÃ±o que quedÃ³: `require_service`, un Ãºnico secreto

`/v1/*` pasÃ³ de `current_subscriber` (JWT por usuario, con tier) a
`require_service` (`X-Service-Token` contra `SERVICE_TOKEN`, comparaciÃ³n en
tiempo constante, 404 si no coincide â€” el mismo patrÃ³n ya usado por
`require_admin`, deliberadamente: no confirmar que la ruta existe si el
secreto no coincide). Sin distinciÃ³n de tier: quien presenta el token de
servicio recibe TODOS los picks y todas las probabilidades, porque decidir
quÃ© le muestra a CADA usuario final ya no es trabajo de esta API â€” es trabajo
del backend del frontend, con su propia base de suscriptores.

Consecuencia directa: la tabla `subscribers` de `db/001_schema.sql` (con
`email`, `tier`, `telegram_id`) se queda sin ningÃºn consumidor en esta API.
No se borrÃ³ de la migraciÃ³n base porque editar `001_schema.sql` no cambia una
base de datos ya aplicada, y no hay evidencia de que el usuario quiera
mantener esa tabla para otra cosa; queda anotado en `harness/tareas.md` para
cuando construya el backend del frontend, por si prefiere esa base de datos
en otro sitio.

### Por quÃ© NO se ofreciÃ³ "secreto de cliente por plataforma" como alternativa

Con el patrÃ³n BFF confirmado, la pregunta de si el `SERVICE_TOKEN` necesitaba
algo mÃ¡s fuerte que una comparaciÃ³n simple (HMAC por request, mTLS) queda sin
urgencia: el secreto vive en un servidor que el propio usuario opera, no en
un cliente hostil. mTLS serÃ­a la siguiente capa razonable SI el backend del
frontend corriera en infraestructura que el usuario no controla del todo;
mientras sea su propio servidor, la comparaciÃ³n en tiempo constante sobre
HTTPS (ya servido por Caddy) es proporcional al riesgo real.

---

## 2026-09-22 â€” CalibraciÃ³n de Z: no hay nada que calibrar, y el control lo explica

Se calibrÃ³ contra histÃ³rico real y point-in-time: tres cortes (2025-01-01,
2025-06-01, 2025-11-01), ajuste con SOLO lo anterior a cada corte, predicciÃ³n
del tramo siguiente, errores estÃ¡ndar del mismo ajuste. **12.183 filas sobre
4.061 partidos y 11 competiciones**, con el cierre real como precio apostable.

### La pregunta previa: Â¿discrimina la razÃ³n media/sd?

Antes de optimizar Z hay que comprobar que el mando estÃ¡ conectado a algo. No
lo estÃ¡. Quintiles de media/sd, ROI con stake plano:

    quintil   ratio medio    ROI        IC95
      1          0.086      +3.44%   [-7.1, 14.0]
      2          0.266      -8.67%   [-18.8,  2.0]
      3          0.461     -11.34%   [-21.4, -0.2]
      4          0.721     -13.15%   [-23.8, -1.4]
      5          1.246      -6.77%   [-18.1,  5.0]

No monÃ³tono, intervalos solapados, correlaciÃ³n con el acierto **âˆ’0,047**.

La rejilla de Z parecÃ­a decir lo contrario â€”el ROI sube de âˆ’8,48% (Z=0) a
+2,48% (Z=1,0)â€” pero desde Z=0,4 **todos los intervalos incluyen cero**, y en
Z=1,0 el intervalo es [âˆ’13,0, +19,0] con 563 picks. Es ruido con forma de
tendencia. Si se hubiera mirado solo esa tabla, se habrÃ­a "calibrado" Z=1,0 con
un nÃºmero de aspecto convincente.

### El control, que es el hallazgo de verdad: el edge del modelo es ANTI-seÃ±al

Quintiles del edge CRUDO, sin incertidumbre de por medio:

    quintil   edge medio     ROI        IC95
      1          2.10%      +1.65%   [-7.3,  11.3]
      2          7.11%      -2.78%   [-12.8,  7.2]
      3         14.08%      -5.04%   [-16.0,  5.4]
      4         25.20%     -15.90%   [-25.8, -4.6]
      5         57.26%     -14.43%   [-26.9, -1.8]

**Cuanto mayor dice el modelo que es su ventaja, peor va.** MonÃ³tono, y la
correlaciÃ³n del edge con el acierto es **âˆ’0,1228** sobre 4.880 filas, que son
unas 8,6 desviaciones tÃ­picas de cero.

Es selecciÃ³n adversa en estado puro: donde el modelo mÃ¡s discrepa del cierre,
mÃ¡s se equivoca. Y explica por quÃ© la zona de abstenciÃ³n no podÃ­a funcionar:
**filtrar mÃ¡s fuerte sobre una seÃ±al negativa no mejora nada**. Cualquier regla
construida sobre esa cantidad hereda el signo.

Correlaciones con el acierto, para situarlo:

    p_model    +0.3123   <- el modelo SÃ sabe de fÃºtbol
    n_ef       -0.0255
    ratio      -0.0474
    edge_mean  -0.1228   <- pero su discrepancia con el cierre es daÃ±ina
    edge_sd    -0.2106

El modelo no tiene edge cero. Lo tiene **negativo**, y eso es distinto y peor.

### De paso: el modelo estÃ¡ bien calibrado

Independiente de todo lo anterior, y es una buena noticia:

    p_model        n     predicha   observada    error
    (0.1, 0.2]   1440     0.1620     0.1535     -0.009
    (0.2, 0.3]   4870     0.2517     0.2624     +0.011
    (0.3, 0.4]   2292     0.3443     0.3264     -0.018
    (0.4, 0.5]   1573     0.4478     0.4520     +0.004
    (0.5, 0.6]    980     0.5467     0.5398     -0.007
    (0.6, 0.7]    542     0.6445     0.6365     -0.008

Dentro de Â±0,02 en todos los tramos con muestra. Confirma por otra vÃ­a por quÃ©
el calibrador se descartaba: no habÃ­a nada que corregir. Los extremos
(p > 0,7, n = 270) muestran infraconfianza de +0,05, pero con esa muestra no
se puede afirmar.

### DecisiÃ³n

- `UNCERTAINTY_ENABLED` se queda en 0, y **no por prudencia sino por mediciÃ³n**.
- `UNCERTAINTY_Z` queda documentado como SIN CALIBRAR. NingÃºn valor es
  defendible porque no hay seÃ±al que calibrar. Poner 0,9 porque la tabla sube
  serÃ­a exactamente el error que este experimento existÃ­a para evitar.
- Y lo mÃ¡s importante: **`find_candidates` selecciona hoy, en promedio,
  apuestas perdedoras**, porque ordena por una cantidad con correlaciÃ³n âˆ’0,12.
  No se cambia a escondidas, pero queda escrito arriba del todo.

### La estrategia que sÃ­ podrÃ­a funcionar NO se puede probar con este histÃ³rico

El punto 1 del plan â€”precio justo sharp y apostar donde una casa blanda aÃºn no
ha convergidoâ€” no depende del edge del modelo, asÃ­ que no hereda este signo.
Pero es **imposible de medir con los datos que hay**: el solapamiento entre
Pinnacle y bet365 es CERO. 46.928 partidos tienen solo Pinnacle y 2.014 solo
bet365, porque `history_fd` guarda una Ãºnica casa de cierre por partido. Sin
dos casas sobre el mismo partido no hay line shopping que medir.

Eso convierte el plan de The Odds API en el cuello de botella real: es la Ãºnica
fuente que da varias casas sobre el mismo partido, y con 500 crÃ©ditos el worker
no puede correr. Ya no es una mejora deseable, es la Ãºnica vÃ­a abierta.

## 2026-09-24 â€” Mesa de mercados en el prototipo web (referencia: propsbr.app)

El usuario preguntÃ³ si propsbr.app podÃ­a servir de modelo para vender sus
picks. PropsBR es un buscador de props por acierto reciente (L5/L10/L20, H2H)
con nota 0-100 y etiquetas del tipo Â«certera/seguraÂ»; no mide nada contra el
cierre. Se copiÃ³ su **composiciÃ³n** (lista de partidos, tabla densa ordenable,
detalle lateral con pestaÃ±as, columna de destacados, formato de cuota) y se
descartÃ³ su **contenido**.

Decisiones:

- La mesa enseÃ±a lo que el sistema sÃ­ mide: precio justo de Pinnacle sin
  margen, mejor casa de la lista, % sobre el justo en el mismo snapshot,
  `min_price` y exclusiÃ³n por Pinnacle fuera de consenso. El modelo va como
  columna de diagnÃ³stico y nunca ordena: su edge es anti-seÃ±al medida.
- Al ordenar por diferencia, lo excluido o cerrado va siempre al final. Un
  +10% de un partido con Pinnacle roto encabezaba la tabla y era justo el
  nÃºmero que el criterio descarta.
- Los precios demo se derivan de dos lambdas (Poisson) y pasan por el mismo
  criterio que `publish/picks.py` (1X2, +2%, 3% de desviaciÃ³n mÃ¡xima, un pick
  por partido), para que mesa, picks y ficha no se contradigan. Con precios
  realistas salen pocas candidatas; no se forzaron mÃ¡s.
- `.table-wrap` necesita `position:relative`: el texto `sr-only` absoluto
  dentro de tablas desplazables se escapaba del recorte y ensanchaba la
  pÃ¡gina a 825 px en mÃ³vil.
- El menÃº lateral pasÃ³ a una cabecera fija arriba (peticiÃ³n del usuario): la
  mesa necesita todo el ancho para la tabla, y el lateral le quitaba 224 px.
- Accesos rÃ¡pidos al estilo PropsBR (peticiÃ³n del usuario), con nombres que
  dicen lo que miden: Â«Top probabilidadÂ» en vez de Â«top confianzaÂ», porque
  ordena por probabilidad justa y eso no dice si la cuota compensa.
- Combinadas calculadas por casa y no con la mejor cuota de cada selecciÃ³n:
  la combinada se juega entera en una casa. En la demo, dos selecciones a
  +3,5% y +7,5% en su mejor casa dan +0,0% en la Ãºnica que cotiza las dos a
  buen precio; enseÃ±ar la otra cifra habrÃ­a sido vender una ventaja que no
  se puede cobrar. Una selecciÃ³n por partido: dentro del mismo partido estÃ¡n
  correlacionadas y el producto de probabilidades serÃ­a falso.
- Revisados los nueve botones reales de PropsBR: seis son la misma lista por
  Score con distinto corte, dos son combinadas armadas (Parlays ~2X/~3X y
  Seguras 1,50â€“2,30) y uno, Â«Certera del dÃ­aÂ», es un pick de pago con venta
  que cierra al inicio e historial pÃºblico. Ese Ãºltimo es exactamente el
  negocio de QuantFut, asÃ­ que entrÃ³ como **Pick del dÃ­a**; los cortes
  duplicados no se copiaron. Sus parlays anuncian Â«62% probÂ» en una cuota
  2.30 (implÃ­cita 43%): nuestras combinadas enseÃ±an la probabilidad justa.

## 2026-09-25 â€” El proyecto pasa a git

PeticiÃ³n del usuario tras el incidente de abajo. Rama `main`, primer commit
`4bd73ee`. Decisiones:

- Fuera del repo: `.env` y `.env.*` (menos `.env.example`), el volcado
  `quantfut.dump` (dato de producciÃ³n, no cÃ³digo), `.venv`, `.local` (cachÃ©s
  de >100 MB) y `__pycache__`. Antes del primer commit se comprobÃ³ que ningÃºn
  valor secreto de los `.env` aparece en otro archivo (solo `REDIS_URL`, que
  no lleva contraseÃ±a).
- `.gitattributes` fija LF: el despliegue copia al servidor Linux tal cual, y
  el `crontab` y los `.sh` se rompen con CRLF. 21 archivos Python tenÃ­an CRLF
  en disco; normalizados.
- AÃºn SIN remoto: el cÃ³digo solo estÃ¡ en este PC y en el VPS. Falta decidir
  dÃ³nde vive la copia remota (GitHub privado o un repo en el propio VPS) y
  convertir `~/quantfut` del servidor en copia de git, para que `git status`
  allÃ­ delate cualquier archivo subido a mano.

## 2026-09-25 â€” Incidente: la sombra caÃ­da 2 h por un archivo subido a medias

A las 17:56 UTC alguien (no esta sesiÃ³n) subiÃ³ al servidor el
`shadow_sharp.py` de goles y hÃ¡ndicap â€”que se habÃ­a decidido NO desplegarâ€” y
reconstruyÃ³ la imagen, sin la migraciÃ³n 022 ni el `picks.py` a juego. La
captura horaria de la sombra fallÃ³ desde las 18:25 (`'Offer' object has no
attribute 'market'`); falla antes de escribir, asÃ­ que no ensuciÃ³ nada, pero
se perdieron ~2 h de ofertas. Restaurado el original (reconstruido deshaciendo
los cambios exactos: no quedaba imagen anterior) y verificado con una captura
manual.

Decisiones:

- El cÃ³digo de goles y hÃ¡ndicap sale del repo y va a
  `harness/archivo/goles_handicap_20260925/` (con su migraciÃ³n 022). Tenerlo
  en `src/` sin desplegar era la trampa: el proyecto no usa git y cualquier
  subida de la carpeta lo arrastra.
- Antes de cada despliegue se compara TODO `src/` y `db/` con el servidor
  (`tar` + `diff -rq`), no solo los archivos que se van a subir. AsÃ­ se vio
  que el Ãºnico archivo distinto era el roto.

## 2026-09-25 â€” Picks sin predicciÃ³n, etiquetas de temporada y limpieza

- Pick sin predicciÃ³n (`db/025`): ver tareas. VacÃ­o, nunca 0, en
  `model_prob`: un 0 se leerÃ­a como "el modelo da 0%".
- Etiqueta de temporada (`db/026`): el calendario etiqueta como el
  histÃ³rico ('2627'). Se cambiÃ³ la columna, no el match_id, que lo referencian
  predicciones, picks y cuotas inmutables; el calendario encuentra los
  existentes por su id de API-Football, asÃ­ que no duplicÃ³ nada (verificado).
- "Evento sin emparejar" de `odds_worker` baja a debug: no era un fallo.
- `pyton/` borrada; su Ãºnico contenido sin copia (la versiÃ³n inicial) queda en
  `harness/archivo/`.

## 2026-09-25 â€” LaLiga 2 y Serie B, sin ensuciar la base

PeticiÃ³n del usuario, con esa condiciÃ³n expresa. Entran por el criterio sharp
(backtest: +3,9% y +5,1% al cierre, validables en The Odds API).

Decisiones:

- `leagues.model_enabled`: las ligas nuevas alimentan calendario, resultados,
  cuotas y sombra, pero NO el modelo ni la predicciÃ³n diaria. Sin esto el job
  de las 08:00 habrÃ­a sellado predicciones de equipos que el modelo no
  conoce, y lo sellado es pÃºblico e inmutable.
- Un club tiene una sola liga en `teams`: al abrir una divisiÃ³n nueva el
  calendario habrÃ­a duplicado a los 20 descendidos de LaLiga y Serie A. Ahora
  `resolve_or_register` busca coincidencia EXACTA en las otras ligas del mismo
  paÃ­s antes de crear, y el parecido dudoso queda pendiente. Sirve tambiÃ©n
  para ascensos futuros.
- Aun asÃ­, ningÃºn equipo quedÃ³ a la automÃ¡tica: `db/024` da de alta los 22
  nuevos y los alias de las dos fuentes de los 42, revisados uno a uno tras un
  ensayo en seco. El ensayo justificÃ³ la regla: "Real Sociedad II" daba 90
  contra "Real Sociedad" (el umbral de aceptaciÃ³n) y era el filial;
  "Sporting Gijon" daba 73 contra "Sp Gijon" y sÃ­ era el mismo club.
- Alias de The Odds API desde el primer dÃ­a: sin ellos el cierre de Pinnacle
  no casa y la oferta se queda sin vara en silencio.
- The Odds API solo paga `h2h` en estas ligas (1 crÃ©dito por llamada): es el
  Ãºnico mercado del criterio y a la API le quedan ~3.200 crÃ©ditos.
- Sin histÃ³rico de football-data (`fd_code` NULL): el criterio no lo
  necesita y cargarlo mezclarÃ­a dos fuentes de nombres en equipos nuevos.

## 2026-09-25 â€” Goles y hÃ¡ndicap: implementado, probado, y sin valor

PeticiÃ³n del usuario: mÃ¡s picks cada dÃ­a, eligiendo "mÃ¡s mercados". Se
implementÃ³ el mismo criterio por lÃ­nea (captura, criterio, sombra, 19 tests,
`db/022`) y, ANTES de desplegar, se ensayÃ³ en memoria con la respuesta real
de API-Football para los 24 partidos prÃ³ximos. Resultado: 0 de 1.448 precios
de casas de la lista por encima del justo en un 2%, en cualquier lÃ­nea.

Decisiones:

- No se despliega. Publicar el cÃ³digo aÃ±adirÃ­a captura y almacenamiento
  (~50Ã— filas) sin aÃ±adir picks. Queda en el repo, probado, para repetir el
  ensayo con Europa en juego.
- La lecciÃ³n es de producto, no de cÃ³digo: las casas de los suscriptores
  ponen goles y hÃ¡ndicap copiando a Pinnacle con margen; donde se equivocan es
  el 1X2 (empates y no favoritos). MÃ¡s picks tienen que venir de mÃ¡s PARTIDOS
  en 1X2 (mÃ¡s ligas), no de mÃ¡s mercados del mismo partido.
- Solo lÃ­nea principal en el criterio: The Odds API da el cierre de Pinnacle
  en una sola lÃ­nea, y una oferta sin cierre no se puede validar. Trampa
  encontrada y cubierta por test: API-Football etiqueta las dos patas del
  hÃ¡ndicap con la lÃ­nea del local.

## 2026-09-27 â€” Fichas de partido reales en la web: contenido, no criterio

Pedido del usuario: que el sitio resulte atractivo con fichas al estilo
PropsBR usando API-Football. Desplegado (db/028, db/029, `ingest/standings`,
`/web/partidos`, vista Â«Partidos y estadÃ­sticasÂ»).

- La ficha NO lleva probabilidades de mercado ni precio justo, aunque el
  plan las incluÃ­a. El producto es "una casa paga â‰¥2% sobre el justo de
  Pinnacle"; publicar ese justo en cada partido deja a cualquiera hacer la
  cuenta con la cuota de su casa. Tampoco el modelo (su edge es negativo).
- Coste de API casi nulo: `results.py` ya pedÃ­a `/fixtures/statistics`;
  ahora guarda la respuesta entera en `matches.stats`. Lo Ãºnico nuevo es
  `/standings`, 13 peticiones dos veces al dÃ­a.
- La forma y los promedios solo miran 270 dÃ­as atrÃ¡s. Sin tope, Valladolid
  (en Segunda, sin histÃ³rico de football-data) enseÃ±aba como "Ãºltimos 5"
  partidos de Primera de mayo de 2025. Con tope, un descendido enseÃ±a sus
  partidos de mayo de 2026 con fecha y competiciÃ³n: verdad, aunque no sea
  su forma en Segunda. Lo correcto es cargar la temporada en curso de
  LaLiga 2 y Serie B (propuesto al usuario; ver tareas).
- `teams.display_name` (nombre de API-Football, solo si la coincidencia en
  standings es EXACTA) en vez de tocar `canonical_name`, que es la identidad
  de emparejamiento: "Manchester City" en la web, "Man City" en el sistema.
- Argentina devuelve Apertura (cerrada) y Clausura con la MISMA fecha de
  actualizaciÃ³n en todas las filas: la fecha no distingue fases. Se usa el
  orden del proveedor (calendario) y se conserva la Ãºltima fase; los grupos
  sin prefijo de fase (conferencias de la MLS) no se tocan.
- Aviso sin tocar: `/fair-price/{id}` es pÃºblico y devuelve `best_price` y
  `gap_pct`: el criterio en abierto. DecisiÃ³n del usuario pendiente.
- Los logs de cron viven dentro del contenedor `worker`: al reconstruirlo se
  pierden (se vio al buscar `/var/log/fixtures.log`). No se cambiÃ³.

## 2026-09-27 â€” Escudos, temporada de LaLiga 2 / Serie B y un ir y venir del calendario

- Escudos descargados UNA vez al volumen `escudos` y servidos desde el
  propio dominio, en vez de enlazar `media.api-sports.io`: la web no depende
  del CDN del proveedor ni le pasa la IP de cada visitante. 271 archivos,
  12 MB, cachÃ© de navegador de 7 dÃ­as.
- `/standings` devolviÃ³ `team.id` nulo para Club LeÃ³n y `/teams` lo llama
  'Leon'. Se completa con `/teams` (1 peticiÃ³n, solo si falta alguno) por
  nombre y, si difiere, por el MISMO equipo resuelto exacto. Un id nulo no
  borra uno guardado (`COALESCE`).
- Temporada de LaLiga 2 y Serie B cargada por el camino normal (insertar
  como programados + `results.close_recent`) en vez de un INSERT a mano:
  mismas reglas de resoluciÃ³n, marcador y estadÃ­sticas que cualquier
  partido. El modelo no los lee (`model_enabled = false`).
- Fallo previo encontrado al preparar la carga: `fixtures` pide el dÃ­a
  entero y los partidos de hoy ya terminados llegan como FT; se mapeaban a
  'scheduled', se reabrÃ­an y se borraba su `odds_capture_log` hasta que
  `results` los cerraba otra vez. Ahora un partido `finished` no se toca
  desde el calendario (test en `test_calendario_terminados.py`).

## 2026-09-28 â€” Un alias no cruza paÃ­ses (GuimarÃ£es era el VitÃ³ria brasileÃ±o)

Buscando escudos que faltaban apareciÃ³ el VitÃ³ria BRASILEÃ‘O 14.Âº en la
Primeira. API-Football renombrÃ³ al GuimarÃ£es 'VitÃ³ria SC', que se normaliza
igual que su alias 'Vitoria' de Brasil; el mapa de alias guardaba UN equipo
por nombre y sin mirar la liga. Ya habÃ­a metido al brasileÃ±o en el
Benficaâ€“GuimarÃ£es del 11-oct: se habrÃ­a sellado una predicciÃ³n inmutable con
los ratings de otro club.

- `normalize.match_team`: un alias puede ser de varios equipos y solo vale
  el que juega en la liga o en otra divisiÃ³n del MISMO paÃ­s. En copas (sin
  liga) un alias ambiguo no se adivina: se descarta como cualquier nombre
  sin resolver. Colisiones hoy en `team_aliases`: ninguna dentro de una
  fuente; la de VitÃ³ria entraba por el nombre nuevo del proveedor.
- db/031 corrige el partido (sin predicciones, cuotas ni sombra), aÃ±ade el
  alias propio de GuimarÃ£es y limpia nombre, id y fila de clasificaciÃ³n que
  se escribieron sobre el brasileÃ±o. ComprobaciÃ³n tras el cambio: 0 partidos
  domÃ©sticos con un equipo de otro paÃ­s; las copas siguen con los mismos
  9 + 16 nombres sin emparejar de siempre.
- db/032: escudos de 47 equipos que ya no estÃ¡n en ninguna tabla actual,
  con ids de `/teams` 2023-2025 revisados a mano ('Atletico GO' puntuaba mÃ¡s
  con AtlÃ©tico-MG). 0 equipos sin escudo entre los que jugaron en 3 aÃ±os.

## 2026-09-28 â€” `/fair-price` pasa a privado

DecisiÃ³n del usuario. `best_price` + `gap_pct` por partido es el criterio de
picks entero: con Ã©l cualquiera ve quÃ© casa paga â‰¥2% sobre el justo sin
suscribirse. Ahora es `/v1/fair-price/{id}` con `SERVICE_TOKEN`; la ruta
pÃºblica desaparece (404, igual que una ruta privada sin token, para no
confirmar que existe). No lo consumÃ­a nada: ni el frontend ni otro mÃ³dulo.

## 2026-09-28 â€” Palancas para acelerar la puerta, sin rebajarla

Pedido del usuario ("ejecuta todas las palancas"). La puerta NO cambia (300
publicables con cierre justo, IC95 > 0, 3 ligas); cambia cuÃ¡ntas
oportunidades se miden por dÃ­a.

- **Casas.** Simulado antes sobre 36 partidos desde el 24-sep: con la lista
  de entonces, 8 partidos con oferta; con todas las casas del feed, 23. La
  sombra mide ahora TODAS las casas no exchange, pero la puerta filtra por
  `SOFT_BOOKS` AL INFORMAR (no se guarda columna): asÃ­ la muestra se puede
  recalcular para otra lista sin volver a capturar. Lista ampliada con
  Betsson, Coolbet, LeoVegas y Unibet por operar en EspaÃ±a o LatinoamÃ©rica,
  pendiente de que el usuario lo confirme; LeoVegas/Unibet llegan con precio
  de Suecia/PaÃ­ses Bajos. Casas offshore de EE. UU. y francesas/alemanas se
  miden pero no cuentan.
- **Cierre.** El "3 de 4 con cierre" era un pick aÃºn sin jugar: 10 de 10
  partidos en sombra lo tienen. El Pinnacle de API-Football nunca baja de
  2,5 h antes del inicio, asÃ­ que el cierre solo sirve de The Odds API.
  Riesgo encontrado y cerrado: la captura de :25 podÃ­a tomar como oferta el
  snapshot de la ventana de cierre, que es contra el que se liquida (EV =
  edge bruto por construcciÃ³n). No habÃ­a pasado; ahora se exige â‰¥ 15 min.
- **Persistencia.** Regla fijada ANTES de tener muestra: la previa pesa como
  100 partidos frente a lo medido (primera oferta por casa y partido,
  acotado a [0, 1]). Cada oferta guarda la persistencia con la que se
  decidiÃ³, asÃ­ que recalibrar no reescribe el pasado.
- **Ligas (db/033).** Chile, TurquÃ­a, Suiza, Dinamarca, Noruega, Suecia,
  Championship, Ligue 2, 2. Bundesliga y Brasil B, todas con Pinnacle en The
  Odds API (sondeo de 21 crÃ©ditos). Colombia, PerÃº y Ecuador no existen en
  The Odds API; BÃ©lgica, Australia y Superettan no tienen Pinnacle. Equipos
  preparados de antemano como en 024: el calendario, creando de uno en uno,
  descartaba el segundo club que se pareciera al primero. 43 reutilizados
  (25 confirmados por id de API-Football) y 127 nuevos; el calendario no
  creÃ³ ninguno mÃ¡s. Coste estimado: ~100 crÃ©ditos/mes por liga (solo 1X2) y
  ~800 peticiones/dÃ­a de API-Football.
- **Copas.** Con clubes turcos, suizos o daneses en el catÃ¡logo, sus partidos
  de Champions/Europa League empiezan a resolverse. `daily._upcoming` y el
  entrenamiento exigen ahora que la liga DOMÃ‰STICA de ambos equipos tenga
  modelo: si no, se sellarÃ­a una predicciÃ³n con ataque y defensa 0. Al
  introducir la guarda no excluÃ­a ningÃºn partido del entrenamiento.

- **Lista confirmada por el usuario:** sus clientes usan Betsson y Coolbet;
  LeoVegas y Unibet salen de `SOFT_BOOKS` y se siguen midiendo sin contar.

## 2026-09-29 â€” Fase 4: el ajuste por XI deja de esperar a diciembre

DiagnÃ³stico: todo estaba construido (captura de XI cada 5 min, challenger,
cuatro brazos en sombra) pero el challenger nunca se habÃ­a entrenado. Exige
700 partidos con predicciÃ³n sellada + XI capturado antes del inicio, y habÃ­a
4 y 21 (modelo activo desde el 27-sep, XI desde el 26-sep). En vivo llegarÃ­a
hacia diciembre.

DecisiÃ³n del USUARIO (Ãºnica excepciÃ³n al punto en el tiempo, y acotada):
alineaciones descargadas despuÃ©s del partido, en `lineups_historicas`
(db/034), que SOLO lee el entrenamiento/validaciÃ³n del challenger. La
predicciÃ³n diaria, la sombra y `availability()` siguen con XI capturados
antes del partido; hay un test que falla si alguno de esos mÃ³dulos nombra la
tabla. La promociÃ³n sigue exigiendo CLV en sombra.

- Base: las predicciones fuera de muestra que `train.py` YA calcula (walk-
  forward del Ãºltimo aÃ±o, sin coste extra), ahora con la rho de su paso.
- Una fila sellada con UN lado histÃ³rico no cuenta como sellada: su hora de
  XI queda vacÃ­a y la regla estricta la descarta.
- Encontrado de paso: si nadie tenÃ­a 3 XI previos, las features salÃ­an sin
  columnas y el cruce reventaba; `train.py` lo tapaba como "no se pudo
  preparar". Ahora devuelve "collecting" con su motivo real.
- Un reentreno no promovido guardaba el challenger con otra versiÃ³n y el
  brazo de la sombra se quedaba sin artefacto: ahora usa el Ãºltimo validado.
- La cuota restante de API-Football llega como TEXTO en la cabecera; la
  primera pasada muriÃ³ comparÃ¡ndola con un nÃºmero (46 peticiones perdidas).

- Resultado de la descarga: 4.555 partidos con XI (0 vacÃ­os), 3.988 con 3
  XI previos por equipo dentro del Ãºltimo aÃ±o, entre 288 y 508 por liga. Las
  copas no emparejaron (sus rivales no estÃ¡n en el catÃ¡logo); no hacen falta.
  No se fuerza el entrenamiento: el mensual del 1-oct lo incluye y no hay
  partidos de estas ligas hasta el 9-oct (parÃ³n de selecciones).

## 2026-10-01 â€” Cadena del XI en vivo: funciona, pero el XI llega a T-25

AuditorÃ­a de los partidos de los Ãºltimos 30 dÃ­as en ligas con modelo:

- Solo 21 de 397 tenÃ­an XI. No es un fallo: las europeas jugaron por Ãºltima
  vez el 20-sep y la captura en vivo de The Odds API empezÃ³ el 24-sep; los 21
  son de MLS y Liga MX. Las europeas vuelven el 9-oct.
- 17 de esos 21 no tenÃ­an predicciÃ³n porque no hubo modelo activo hasta el
  27-sep 06:21 (el de 24-sep no se activÃ³). Desde entonces, 4 de 4 partidos
  con XI recorrieron toda la cadena: predicciÃ³n 08:00 â†’ XI â†’ cuotas
  `post_xi` â†’ sombra (`baseline_t60`, `baseline_market`). Faltaba el brazo de
  XI solo porque no habÃ­a ajuste validado (resuelto hoy).
- Hallazgo importante: el XI se guarda a T-25 en 22 de 22 partidos, aunque se
  consulta cada 5 min desde T-90. El cliente no tiene cachÃ©; es el
  proveedor (su guÃ­a: 20-40 min antes). Con el XI a T-25, Pinnacle ya ajustÃ³
  y la ventaja temporal de la recomendaciÃ³n 1 casi desaparece. Siguiente paso:
  medir la antelaciÃ³n en europeas desde el 9-oct antes de pensar en otra
  fuente.

- Prueba en vivo (Seattleâ€“Sporting KC, 2-oct 01:30 UTC): XI a T-24, cuotas
  `post_xi` a T-20 con 21 casas, sombra a T-19 con `baseline_t60` y
  `baseline_market`. Los brazos de XI NO se registraron aunque el ajuste estÃ¡
  validado: `availability()` exige 3 XI previos del equipo en la tabla en
  vivo `lineups` (existe desde el 26-sep) y devuelve "historia
  insuficiente". Las europeas empiezan de cero el 9-oct: el brazo de XI no
  medirÃ¡ nada hasta ~finales de octubre. Completar esa historia con
  `lineups_historicas` ampliarÃ­a la excepciÃ³n del usuario (hoy solo
  entrenamiento): queda a su decisiÃ³n.

## 2026-10-01 â€” Criterio de ECE del XI: ruido, no orden (decisiÃ³n del usuario)

OpciÃ³n B elegida por el usuario. Antes: el XI se validaba solo si
`ECE_despuÃ©s <= ECE_antes`. Ahora: remuestreo pareado por partido (1.000,
semilla 0) de ECE_despuÃ©s âˆ’ ECE_antes; solo "empeora" si el percentil 2,5 %
es > 0. Se informa `ece_delta_ic95` y `ece_empeora`. RPS, log-loss y â‰¥2 ligas
no cambian.

- Por quÃ©: simulado con base variable y 3.600 filas, una seÃ±al real pasaba la
  puerta antigua 2-6 de 8 veces; con la nueva, 8-10 de 10 (efecto 0,1-0,4).
  Ruido puro: 0 de 10 con 1 seÃ±al, 1 de 10 con 14 (frenan RPS, log-loss y
  ligas; y la sombra todavÃ­a exige CLV antes de publicar nada).
- Transparencia: el criterio se cambiÃ³ despuÃ©s de ver que el XI simple
  fallaba solo por el ECE (+0,00055). La regla es la estÃ¡ndar (no
  significativo al 95 %), no un umbral ajustado a ese nÃºmero, y aplica igual
  a los brazos de la fuerza por jugador (XI con valor sigue sin validar:
  falla por RPS y log-loss).
- Reevaluado con `python -m qf.model.lineup_challenger` sobre
  `oos_2026.10.01-030007.pkl` (mismos nÃºmeros que el reentreno: el ajuste es
  determinista): IC95 del cambio de ECE [âˆ’0,00741, +0,00582], `ok: true`.
  `lineup_2026.10.01-030007.pkl` reescrito; el anterior, en
  `~/respaldo_20261002_b1/`. `model_artifacts.val_metrics` no se reescribe:
  conserva lo que dijo el reentreno con el criterio de entonces.

## 2026-10-01 â€” Reentreno mensual y fuerza por jugador (Fase B1)

Reentreno 2026.10.01-030007: NO se activa ("No mejora el baseline Elo sobre
las mismas filas"; RPS 0,20074 en 1.107 filas). Sigue activo 2026.09.27.
El walk-forward se guardÃ³ (`oos_2026.10.01-030007.pkl`) y sirviÃ³ para la B1
sin repetir 3,5 h de entrenamiento.

XI simple (3.650 filas, 2.555 ajuste / 1.095 validaciÃ³n): RPS 0,21817 â†’
0,21678, log-loss 1,05235 â†’ 1,0479, 8 de 11 ligas mejoran, pero ECE 0,03041 â†’
0,03096: queda `shadow_only`. La sombra no tiene ningÃºn XI validado.

Fuerza por jugador B1, mismas 3.645 filas para los tres brazos:

| brazo | RPS | log-loss | ECE | ligas |
|---|---|---|---|---|
| base | 0,21818 | 1,05317 | 0,03125 | - |
| XI simple | 0,21677 | 1,04868 | 0,03182 | 8 |
| XI con valor | 0,21912 | 1,05654 | 0,03705 | 1 |
| XI con nota | 0,21801 | 1,05274 | 0,03175 | 8 |

- "XI con valor" empeora a la base: 18 seÃ±ales (9 estadÃ­sticas por lado)
  sobreajustan con 2.551 partidos. Saber QUIÃ‰N falta, medido por sus
  estadÃ­sticas, no aÃ±ade nada a saber CUÃNTOS habituales faltan. SegÃºn el
  plan, no se escribe la B2. No se probaron variantes sobre la misma
  validaciÃ³n: elegir la que salga mejor serÃ­a ajustar al 30 % de prueba.
- La nota del proveedor (solo comparaciÃ³n) tampoco supera al XI simple.
- El test de "valor gana" de la B1 se reescribiÃ³ con informes controlados:
  con validaciÃ³n de 300 filas el ECE de dos brazos se ordena casi al azar
  (simulado: seÃ±al real fuerte pasa 2-6 de 8 veces; sin seÃ±al llegÃ³ a pasar
  1 de 6 con 1.000 filas). Eso mismo afecta al XI simple real: decisiÃ³n
  del criterio pendiente del usuario (ver tareas).
- `shadow._challenger_validado` ahora exige `features == LINEUP_FEATURES`:
  los artefactos `lineup_valor_` / `lineup_nota_` comparten el patrÃ³n
  `lineup_*.pkl` y uno validado en el futuro se habrÃ­a cargado como XI simple.
- La revisiÃ³n programada del 1-oct quedÃ³ colgada en "running" sin actividad;
  esta revisiÃ³n se hizo a mano.

## 2026-10-03 â€” FotMob: mismo xG que Opta, disponible en horas y con LatAm

Pregunta del usuario: Â¿llega antes por FotMob? Comprobado en su JSON
pÃºblico (solo lectura, desde el navegador): los 6 partidos recientes sin xG
en API-Football lo tienen en FotMob, incluido Bocaâ€“UniÃ³n jugado horas
antes; y cubre Liga MX y Argentina, que en API-Football casi nunca lo
traen. Contra el xG de FBref guardado (17 partidos de 2024, 6 ligas):
diferencias de 0,00-0,05 en 32 de 34 valores; dos de 0,2 y 0,6 (Premier y
LaLiga), probablemente el valor de un penalti. Sin retraso, ademÃ¡s, no hay
la fuga de backtest que traerÃ­a el xG tardÃ­o de API-Football.

## 2026-10-03 â€” El xG de API-Football: fiable cuando estÃ¡, irregular en cuÃ¡ndo

Pregunta del usuario: Â¿no sirve el proveedor ya contratado? El README lo
prohibÃ­a (22-sep) por cobertura irregular y vacÃ­os mudos. Medido, solo
lectura, ~350 peticiones:

- **Valores: los mismos que FBref/Opta.** 2024, 15 partidos por liga
  emparejados con el xG guardado: correlaciÃ³n 0,963 (Argentina) a 1,000
  (Serie A), medias casi idÃ©nticas, diferencia media 0,01-0,09 por equipo.
  Muy probablemente el mismo proveedor (Opta): se puede empalmar sin
  romper la serie.
- **Cobertura: irregular por liga, temporada y fecha.** 2024: completa en 8
  ligas europeas, Brasil y MLS; Argentina 5/15; Liga MX 0/15. Temporada en
  curso, muestra al azar: casi todo con xG salvo Argentina (1/6). Pero los
  partidos RECIENTES no lo tienen: MLS 0 en los Ãºltimos 6,6 dÃ­as, Liga MX 1
  de 14 en dos semanas, Argentina 0 de 14; LaLiga y Premier sÃ­ a 13 dÃ­as.
  Llega con retraso de dÃ­as o semanas, y en las americanas puede no llegar.
- Consecuencia de diseÃ±o si se adopta: no basta con leerlo al cerrar el
  partido (`results.py` lo pide a +105 min y por eso no lo tenÃ­a); hay que
  volver a pedirlo durante semanas. Y en backtests el xG de las Ãºltimas
  ~2 semanas no existÃ­a en el momento de predecir (`check_leakage` avisa de
  xG registrado >6 h tarde): fuga pequeÃ±a, pero real.

## 2026-10-03 â€” El xG aporta: merece una fuente nueva

`eval/xg_value.py`, regla fijada antes de ver nada. Mismo walk-forward
(reajuste cada 30 dÃ­as, solo pasado) con `xg_blend` 0,65 frente a 0; cada
reajuste tardÃ³ ~18 min, asÃ­ que se lanzaron los cuatro brazos en procesos
aparte (6 h). `check_leakage`: solo el aviso genÃ©rico de que las cuotas son
cierre, y aquÃ­ no se usan como variable.

- Ventana A (xG existÃ­a, 6.785 partidos, 84 semanas): RPS 0,20154 frente a
  0,20440; delta âˆ’0,00287, IC95 [âˆ’0,00376, âˆ’0,00200]; mejora en 12 de 13
  ligas (solo la Europa League, n=66, empeora). Veredicto: `xg_aporta`.
- Ventana B (hoy, 3% de partidos de test con xG): âˆ’0,00055 [âˆ’0,00100,
  âˆ’0,00018], 8 de 13 ligas. Lo que queda es la historia vieja con xG en el
  entrenamiento, que se diluye con la media vida.
- Lectura: 0,0029 de RPS es lo mismo que Dixon-Coles saca a Elo y ~40% del
  hueco con Pinnacle (0,0068). Perderlo para siempre no es neutral. Pero el
  modelo no elige los picks: esto mejora el modelo, no la puerta comercial.

## 2026-10-03 â€” Cerradas las fugas del criterio de la fase 3

Con el sÃ­ del usuario: `/matches/{id}` sin `market_consensus`, sin
`/openapi.json`, y opciÃ³n (b) para la cadena: el lote deja de llevar el
precio justo desde el 3-oct. Se descartÃ³ reescribir el formato hacia atrÃ¡s:
un lote pasado regenerado desde la base tiene que dar el hash sellado, y es
lo que hace verificable la cadena; por eso la fecha de corte vive en el
cÃ³digo (`LOTE_SIN_CONSENSO_DESDE`). Comprobado en producciÃ³n con el lote del
2-oct.

Al tocar `hashchain.py` apareciÃ³ el problema mayor: el lote lleva tambiÃ©n
los picks, de pago incluidos, y el flujo documentado lo sube a un repo
pÃºblico ANTES de los partidos. (b) no lo resuelve; lo resolverÃ­a publicar
solo el hash antes y el JSON despuÃ©s (comprometer-revelar). Queda como
decisiÃ³n del usuario en tareas; hoy no ocurre porque no hay remoto.

## 2026-10-03 â€” AuditorÃ­a de la fase 3 (solo lectura, contra producciÃ³n)

- **Bien:** Cloudflare Access cierra `/control`, `/admin` y Grafana en los
  tres dominios, y una cabecera `Cf-Access-Jwt-Assertion` falsa no lo salta
  (Access valida en el borde; Caddy solo comprueba que exista). `/v1/*` sin
  token da 404; el panel exige PBKDF2 600k y token de 64. Puertos: solo 22,
  80 y 443 pÃºblicos; 8000 y 3000 en 127.0.0.1. CORS rechaza orÃ­genes
  ajenos. El limitador corta en 60/min por IP (ventana fija: hasta 2x en el
  cambio de minuto). El JavaScript solo llama a rutas pÃºblicas. La ficha
  `/web/partidos/{id}` no lleva cuotas ni probabilidades.
- **Fuga del criterio:** `/matches/{id}` devuelve `market_consensus` (justo
  sin margen) y los lotes sellados tambiÃ©n lo llevan. No hace daÃ±o hoy (no
  se vende ni se publica la cadena), pero es exactamente lo que se quiso
  cerrar el 28-sep. Pendiente de decisiÃ³n del usuario (tareas.md).
- Menores: `/openapi.json` pÃºblico con las rutas privadas, rutas internas en
  `/model-card`, sin CSP, y ningÃºn aviso legal (+18, juego responsable,
  privacidad, tÃ©rminos) en la web.

## 2026-10-03 â€” AntelaciÃ³n de la decisiÃ³n y rescate del cierre

Las dos primeras mejoras de la auditorÃ­a, con el sÃ­ del usuario.

- **Una sola `MIN_LEAD` para sombra y publicaciÃ³n, aplicada al precio Y a
  la decisiÃ³n.** Al leer el cÃ³digo apareciÃ³ algo peor que lo auditado: la
  publicaciÃ³n real no tenÃ­a ninguna guarda de antelaciÃ³n. La puerta
  certifica "lo que se habrÃ­a publicado", asÃ­ que la regla tiene que ser la
  misma en los dos lados; la constante vive en `picks.py` y la sombra la
  importa, para que no puedan divergir.
- **Rescate del cierre desfasado 5 min, solo `close`.** Se descartÃ³ mover la
  ventana o tomar un "precierre" de respaldo: cualquiera de las dos cambia
  la vara de la puerta. Con el rescate la vara es la misma (Ãºltimo precio a
  3-12 min) y hay dos intentos; el registro de captura evita pagar dos veces.
- Desplegado sin reiniciar el worker (`docker compose cp` + recargar el
  crontab montado) para no cortar la mediciÃ³n del xG; API reconstruida.

## 2026-10-03 â€” AuditorÃ­a de las fases 0, 1 y 2 (solo lectura)

Recalculado de forma independiente contra la base de producciÃ³n, no leÃ­do de
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
  en dos partidos a <40 h; 10 de 10 partidos con predicciÃ³n sellada antes del
  inicio; cadena de hashes verificada (4 lotes). Arreglado: `fixtures.run()`
  contaba los clubes de copa fuera del catÃ¡logo como incidencia; con
  Telegram activo habrÃ­a avisado dos veces al dÃ­a por algo esperado (mismo
  criterio que `check_unresolved_names`). Desplegado con `docker compose cp`
  para no matar la mediciÃ³n del xG en curso; el prÃ³ximo build lo incluye.
- **Fase 2, los nÃºmeros de la sombra son correctos.** 165 de 165 precios
  justos de entrada reproducidos (Shin sobre el snapshot de Pinnacle del
  mismo instante; en API-Football el snapshot es `provider_updated_at`, no
  `fetched_at`); 89 de 89 EV al cierre idÃ©nticos; 0 resultados o
  beneficios mal liquidados; publicables una por partido, solo SOFT_BOOKS,
  decididas 8-71 h antes con precios de â‰¤5,2 h. Matiz: la guarda de 15 min
  mira la hora del PRECIO, no la de la decisiÃ³n; 3 ofertas se decidieron a
  <15 min (ninguna de SOFT_BOOKS, no cuentan). PublicaciÃ³n pausada
  (`PUBLISH_PICKS_ENABLED=0`, `picks` vacÃ­a).

## 2026-10-02 â€” Copas recuperadas y chequeo de xG que mira el dato

`worldfootballR_data` lleva parado desde sep-2025 (dic-2024 en copas): el
modelo entrenaba solo con goles en los Ãºltimos meses y sin ningÃºn partido de
copa de 2025/26. DecisiÃ³n del usuario: recuperar copas y vigilar el xG; la
fuente de xG nueva queda pendiente.

- Copas desde API-Football, por el camino ya probado (insertar como
  programado, cerrar con `close_recent`). Ensayo en seco primero; la carga
  real coincidiÃ³ partido a partido (351, 0 duplicados, 0 errores). Guarda de
  duplicados nueva en las cargas hacia atrÃ¡s (misma competiciÃ³n y equipos,
  Â±36 h): `matches` no tiene clave natural y lo que cuelga de un partido no
  se borra. Rangersâ†’Angers (92) o Wolfsbergerâ†’Wolfsburg (80) confirman por
  quÃ© en copa solo vale la coincidencia exacta.
- `check_xg_freshness` con reconocimiento CON CADUCIDAD (1-nov): sin ella
  el chequeo alertarÃ­a a diario por algo ya sabido â€”y se aprende a ignorar
  las alertas, que es como se perdiÃ³ la de bajasâ€”; sin caducar, esconderÃ­a
  el problema para siempre como hizo el `ok` con 0 filas del job.

## 2026-10-02 â€” La alerta de bajas saltÃ³ cuatro dÃ­as y no la vio nadie

Reconstruido con los datos de cada maÃ±ana: `check_injuries_coverage()` fallÃ³
el 28, 29 y 30-sep y el 1-oct (`us.mls` 16-17 partidos, 0 bajas). Tres
agujeros en cadena:

- **NingÃºn canal.** `health.run()` llama a `telegram.alert()`; sin
  `TG_BOT_TOKEN` eso era un WARNING genÃ©rico "mensaje omitido". Afecta a los
  7 chequeos diarios y a las 8 llamadas a `alert()` del cÃ³digo, no solo a
  las bajas. DecisiÃ³n del usuario: configurar Telegram SOLO para alertas a su
  chat privado (`TG_ALERT_CHAT`); los canales de picks siguen vacÃ­os, asÃ­ que
  no se publica nada por ahÃ­. Sin canal, `alert()` deja ahora el texto
  completo como ERROR.
- **Log efÃ­mero.** El cron escribÃ­a en `/var/log` del contenedor, que se
  borra en cada despliegue (dos ese mismo dÃ­a). `/var/log` del worker es ahora
  el volumen `workerlogs`, y cada pasada del cron queda en `health_runs`
  (db/037). El panel y `/admin/health` no escriben historial.
- **Mensaje que invitaba a archivarlo.** DecÃ­a "mismo patrÃ³n de cobertura
  silenciosa que mx.liga_mxâ€¦", es decir, culpaba al proveedor. Ahora pide
  descartar antes un error nuestro.

Al activar Telegram aparecÃ­an dos riesgos nuevos, cerrados antes: el envÃ­o
es HTML y un "5 < 300" sin escapar hacÃ­a rechazar el mensaje; y un fallo de
Telegram propagaba la excepciÃ³n al job que avisaba. Comprobado de paso: los
tres huecos conocidos de `/injuries` (Liga MX, Argentina, Primeira) son
reales (la API devuelve 0 por partido); Brasil sÃ­ trae datos.

## 2026-10-02 â€” La historia del XI en vivo sale tambiÃ©n de lineups_historicas

DecisiÃ³n del usuario, ampliando la excepciÃ³n de db/034. `availability()`
exige 3 XI previos por equipo y solo miraba `lineups` (en vivo desde el
26-sep): el brazo de XI no habrÃ­a medido nada en las europeas hasta finales
de octubre.

- Por quÃ© no rompe el punto en el tiempo: lo que se toma de la tabla es el
  XI de partidos YA JUGADOS antes del de hoy, que era pÃºblico antes del
  partido que se predice. Lo que sigue exigiendo captura previa al inicio es
  el XI de HOY, que solo sale de `lineups`. La predicciÃ³n diaria y lo
  sellado no leen la tabla (test por AST en `test_lineups_historicas.py`).
- Coherencia: el entrenamiento del challenger ya construÃ­a la historia con
  las dos tablas; la sombra ahora calcula la variable igual.
- Si un partido estÃ¡ en las dos tablas manda el capturado en vivo; solo XI
  completos (â‰¥11), como en el entrenamiento. `n_history_historico` dice
  cuÃ¡ntos XI de la historia salieron de la tabla histÃ³rica.
- Desplegado (worker + db/036, que solo cambia el COMMENT de la tabla;
  respaldo en `~/respaldo_20261002_historia/`). Verificado: el
  Seattleâ€“Sporting KC pasa de "historia insuficiente" a 5 XI previos por
  lado (4 histÃ³ricos); 257 de 262 equipos con partido en 14 dÃ­as tienen â‰¥3.

## 2026-10-02 â€” Las bajas nunca se guardaron: id de API-Football contra id interno

`injuries` estaba vacÃ­a tras 521 comprobaciones en 51 partidos (22-sep a
2-oct), sin un solo error. `_side_of()` comparaba `team.id` de la respuesta
(API-Football, p. ej. Seattle = 1595) con `matches.home_team_id` (interno,
49060): nunca coincidÃ­a y cada baja se descartaba con `continue`. Comprobado
con una llamada real: 26 bajas en el Seattleâ€“Sporting KC, las 26 perdidas.

- Arreglo: `pending_matches()` trae `teams.af_team_id` de ambos lados y se
  compara contra eso (`tests/test_injuries.py`). NingÃºn equipo de las ligas
  con modelo con partido en 14 dÃ­as tiene `af_team_id` nulo.
- Lo que se descarte a partir de ahora deja un WARNING y cuenta en
  `discarded`, tambiÃ©n en el `record_health` de la pasada: un descarte
  masivo ya no puede volver a pasar mudo.
- Lo perdido no se recupera como dato point-in-time: pedir hoy las bajas de
  un partido pasado da la foto de hoy, no la que se conocÃ­a antes del
  partido. No se rellena; la muestra vÃ¡lida empieza el 2-oct.
- Desplegado (solo `worker`; respaldo del archivo anterior en
  `~/respaldo_20261002_injuries/`). Verificado en producciÃ³n: el
  Seattleâ€“Sporting KC guarda 26 bajas, 0 descartadas.

## 2026-09-30 â€” Fuerza por jugador, Fase A: los datos

DiseÃ±o aprobado por el usuario secciÃ³n a secciÃ³n (valor por contribuciÃ³n por
90 min con decaimiento, encogimiento por posiciÃ³n y pesos estimados solo con
el tramo de entrenamiento; la nota del proveedor solo como comparaciÃ³n;
plus-minus descartado por coste y ruido con esta muestra). Calendario del
usuario: datos ahora, modelo despuÃ©s del reentreno del 1-oct, para poder
compararlo con el XI simple.

- No necesita excepciÃ³n al punto en el tiempo: son estadÃ­sticas de partidos
  ya jugados; la Fase B solo usarÃ¡, para el dÃ­a D, partidos anteriores a D.
- `estadisticas_jugador_log` registra tambiÃ©n los intentos vacÃ­os: sin Ã©l,
  cada pasada reintentarÃ­a para siempre los partidos que el proveedor no
  cubre (hubo 11).
- El lado de cada bloque se decide por el id de equipo de API-Football, no
  por el orden (en `/fixtures/players` no estÃ¡ garantizado).
- Descubierto en los datos: el campo `substitute` del proveedor no es fiable,
  hay lados con 16 "titulares". La Fase B tomarÃ¡ el once de las alineaciones.
- Coste diario nuevo: 1 peticiÃ³n por partido cerrado en ligas con modelo.

## 2026-09-25 â€” MÃ¡s volumen: medir antes de cambiar el criterio

DecisiÃ³n: el umbral del 2%, un pick por partido, la referencia Pinnacle/Shin
y la publicaciÃ³n pausada NO cambian. El histÃ³rico puede descubrir variantes,
pero ya se utilizÃ³ para diseÃ±ar la estrategia: no sirve para certificarla.

- `eval/quote_coverage.py` informa la primera terna 1X2 completa observada
  por casa/fuente/liga, antelaciÃ³n y edad del precio cuando se conoce.
  The Odds API no conserva aÃºn `last_update` del bookmaker: edad desconocida
  se deja nula, no se inventa cero. Hace falta ejecutarlo contra Postgres
  operativo antes de gastar mÃ¡s cuota en capturar antes de Tâˆ’72.
- `eval/sharp_challengers.py` usa los 42 CSV ya cacheados, 7 ligas y seis
  temporadas, hash `59586239a2169a51b9a864f3655c6e5cdc4c8d68f18a1ccdcc2b69b2408f6118`.
  Compara Shin y Power sobre los mismos 14.294 partidos 1X2 y mide TODOS
  los brazos contra el MISMO cierre Pinnacle/Shin. Power apenas mejora el
  log-loss temprano (0,960347 frente a 0,960392) y el RPS (0,193120 frente
  a 0,193131): magnitud insuficiente para cambiar la referencia.
- Con la lista blanca actual y un pick potencial por partido, Shin al 2%
  deja 286 partidos, EV al cierre justo +3,788%; al 1% deja 530, con 244
  partidos nuevos cuyo EV histÃ³rico es +2,499% (IC95 por semanas
  [1,915, 3,071]). 502 de los 530 candidatos al 1% dependen de 1xBet.
  El umbral dinÃ¡mico predefinido (1,5% <1,80; 2% 1,80â€“3,49; 3% â‰¥3,50)
  deja solo 233 partidos: no cumple ni el objetivo de mÃ¡s volumen.
- Esto es un proxy offline: no hay timestamp exacto de decisiÃ³n, acceso
  regional, lÃ­mite de stake, cuota todavÃ­a disponible ni tope diario en los
  CSV. La persistencia por casa se estimÃ³ al 2% y no se recalibrÃ³ para el
  1%. La puerta en sombra, con precio verificable al cierre, sigue mandando.

## 2026-09-24 â€” La temporada 2026/27 no existÃ­a en siete ligas

SÃ­ntoma: el `--bootstrap` rechazaba cada noche ("mercado de 252 dÃ­as") y la
puerta no tenÃ­a nada que liquidar. Causa: tres piezas correctas por separado
que dejaban un hueco entre ellas. `backfill()` acababa en 2025/26 por un rango
fijo; `fixtures` solo crea partidos futuros; `results` solo cierra 72 h. Lo
jugado entre el Ãºltimo histÃ³rico y el primer calendario no lo creaba nadie.

Decisiones:

- El histÃ³rico llega al aÃ±o en curso, no a la temporada europea en curso:
  Brasil y Argentina etiquetan '2026' lo que juegan en mayo.
- Antes de insertar, `_ingest_rows` busca el mismo partido por liga, equipos
  y Â±36 h, y si existe salta la fila ENTERA. El match_id no sirve de guarda:
  API-Football etiqueta la temporada '2026A'/'2026' y escribe otros nombres.
  Y las cuotas de cierre no tienen clave Ãºnica y `odds_snapshots` no admite
  DELETE: una recarga sin esta guarda las habrÃ­a duplicado para siempre (el
  ensayo lo confirma: 531 partidos ya cargados habrÃ­an vuelto a entrar).
- Racing Santander como alias (`db/021`), no como club nuevo: la guarda
  compara por team_id y un club duplicado la esquiva.
- Cargado en producciÃ³n (991 partidos, 0 duplicados). No destraba el modelo:
  los CSV no traen Pinnacle desde enero de 2026, asÃ­ que la frescura del
  mercado sharp depende SOLO de la captura en vivo. SuposiciÃ³n corregida: se
  esperaba que el cierre del CSV bastara.
- Las 17.385 cuotas de cierre repetidas de recargas antiguas no sesgan nada:
  son copias exactas (mismo precio) y todo lector del cierre toma un precio
  por selecciÃ³n. Se documentan y se dejan: la tabla es inmutable a propÃ³sito.
- Pendiente aparte, cosmÃ©tico hoy: la columna `season` no es coherente entre
  fuentes en ligas de aÃ±o natural ('2627' histÃ³rico, '2026'/'2026A'
  API-Football). NingÃºn cÃ¡lculo del modelo la usa.

## 2026-10-03 â€” InvestigaciÃ³n NBA 2026-27 y Telegram inmediato

El usuario pide incorporar NBA mediante investigaciÃ³n profunda, literatura
acadÃ©mica y experimentos, y aclara que las seÃ±ales llegarÃ­an al instante por
Telegram. Se incorpora tambiÃ©n su archivo `Texto pegado.txt`. Documento:
`docs/nba_2026_27_investigacion_y_plan.md` (21 experimentos E0â€“E20).

Decisiones de diseÃ±o, todavÃ­a sin implementaciÃ³n ni resultados propios NBA:

- La entrega por Telegram cambia la antigua restricciÃ³n de web para esta
  ampliaciÃ³n. La rapidez real depende ademÃ¡s del feed y de cuÃ¡ndo apuesta
  el cliente; medir supervivencia de ventaja y no asumir ejecuciÃ³n instantÃ¡nea.
- Props de rebotes/asistencias/puntos y totales entre periodos son hipÃ³tesis
  experimentales. La literatura respalda posesiones, minutos, rotaciones y
  actualizaciÃ³n, pero no un ranking contemporÃ¡neo garantizado de rentabilidad.
- Corregidas afirmaciones del texto sobre regresiÃ³n inevitable, eliminaciÃ³n
  universal de garbage time, transferencia fija de USG y ventaja cuÃ¡ntica NBA.
  Box score, regÃ­menes competitivos/paliza y resultados liquidables se separan.
- La infraestructura de fÃºtbol conserva sus puertas/triggers/publicaciÃ³n.
  NBA requiere contratos/jugadores/periodos, guard point-in-time para live,
  liquidaciÃ³n y polÃ­tica de promociÃ³n propias; no convertir puntos en goles
  ni importar persistencias o requisitos de tres ligas sin validaciÃ³n.
- Propuesto worker dedicado con sellado y outbox, revalidaciÃ³n, caducidad e
  historial de envÃ­o. No se activÃ³ ni enviÃ³ Telegram, no se consultaron APIs
  de pago, no se desplegÃ³ ni se modificÃ³ cÃ³digo de producciÃ³n.
- Fuentes y lÃ­mites de lectura explicitados: algunos trabajos se verificaron
  por abstract/metadata, otros con texto completo. No presentar beneficios
  antiguos como expectativa 2026 ni precisiÃ³n deportiva como ventaja de cuota.
- RevisiÃ³n AST correcta de 74 archivos Python. El arnÃ©s Bash no ejecutÃ³
  pruebas en este entorno; su mensaje OK no se toma como validaciÃ³n completa.
  La venv local apunta a un intÃ©rprete no disponible. Cambio documental.

## 2026-10-03 â€” RevisiÃ³n de certeza y segundo texto NBA

- El nuevo texto mezcla autores (Shannon/Thorp con Dixonâ€“Coles), confunde
  recencia con deterioro de habilidad y atribuye al EPV original tecnologÃ­a
  distinta de la documentada. Ver secciones 22â€“26 del plan NBA para fuentes
  y correcciones; las cifras privadas de rentabilidad no validan una estrategia.
- Se prioriza fiabilidad antes de complejidad: cÃ¡lculo bayesiano, calibraciÃ³n
  temporal con mercado, selecciÃ³n con abstenciÃ³n y rÃ©plica prospectiva.
  El plan pasa de 21 a 27 experimentos propuestos, E0â€“E26, sin resultados
  nuevos ejecutados. Fijar polÃ­tica antes del test y medir el subconjunto elegido.
- Conformal aporta cobertura bajo condiciones, no probabilidad de cobrar
  ni ROI. La extensiÃ³n a pÃ©rdidas no monÃ³tonas de febrero de 2026 se incluye
  como preprint exploratorio, con resumen consultado y supuestos por auditar.
  Kelly robusto/restringido trata asignaciÃ³n y riesgo; no crea ventaja.
- Para Telegram, contrato, cuota mÃ­nima y caducidad medidos mandan sobre
  etiquetas de confianza. Acuse de envÃ­o no confirma ejecuciÃ³n y la captura
  por minutos no se vuelve instantÃ¡nea por un modelo mÃ¡s moderno.
- Solo documentaciÃ³n y backlog: no envÃ­o de Telegram, llamadas de pago,
  cambios de producciÃ³n ni modificaciÃ³n de trabajos FotMob concurrentes.
  Revisados IDs de experimentos, secciones, referencias y cÃ¡lculos ilustrativos;
  no se ejecutaron nuevos modelos ni pruebas de cÃ³digo por este cambio.

## 2026-10-03 â€” Arquitectura NBA aislada del fÃºtbol

- A partir de la preocupaciÃ³n del usuario por mezclar componentes, se
  documenta aplicaciÃ³n NBA independiente en `apps/nba/`, aÃºn inexistente,
  con entorno, imagen, despliegue, persistencia y Telegram propios.
  Documento: `docs/nba_arquitectura_aislada.md`.
- La frontera incluye ejecuciÃ³n y permisos, no solo carpetas: no importar
  `qf.config`/`qf.db`, no compartir cron, DSN, artefactos o migraciones.
  Esos mÃ³dulos cargan configuraciÃ³n o conexiones de fÃºtbol; acoplarlos
  introducirÃ­a rutas implÃ­citas hacia el sistema existente.
- Se recomiendan instancias Postgres y Redis NBA propias. La outbox durable
  va en Postgres; la cachÃ© futbolÃ­stica usa allkeys-lru. Dependencias propias
  evitan que una actualizaciÃ³n NBA cambie el runtime de fÃºtbol.
- Un mismo VPS y una cuenta de proveedor conservan riesgos compartidos.
  Fijar lÃ­mites de recursos/retenciÃ³n y verificar el Ã¡mbito de crÃ©ditos;
  prefijos de claves o dos contadores independientes no aÃ­slan esos lÃ­mites.
- Plan y backlog actualizados; solo documentaciÃ³n. No se crearon servicios,
  se moviÃ³ cÃ³digo, se instalaron dependencias ni se modificÃ³ producciÃ³n.
  Criterios de aceptaciÃ³n de permisos, imports, fallos y carga documentados;
  su ejecuciÃ³n queda pendiente de la implementaciÃ³n.

## 2026-10-03 â€” MVP NBA y capacidad comercial de las seÃ±ales

- La crÃ­tica del usuario aporta un criterio operativo Ãºtil: precio correcto
  y disponible para el cliente, ademÃ¡s de precisiÃ³n deportiva. Documento:
  `docs/nba_mvp_ejecucion_y_capacidad.md`; resumen en secciÃ³n 27 del plan.
- Cadencia de props de 60 s verificada en documentaciÃ³n de The Odds API.
  Rangos USD 20â€“250, colapso en 45 s, reacciÃ³n 5â€“30 s y secundarios 2â€“5 min
  no corroborados por fuentes primarias suficientes: medirlos, no prometerlos.
  Polling y noticias tienen tiempos distintos; snapshots de 60 s no permiten
  asignar una duraciÃ³n exacta de 45 s a una oferta.
- MVP reduce familias/operadores y mantiene PIT transversal, minutos/tasas,
  calibraciÃ³n E22/E23 mÃ­nima, precio E5/E17 y entrega E19. Noticias E7/E8
  despuÃ©s del nÃºcleo; los 27 experimentos siguen como backlog cientÃ­fico.
- No hay minutos implÃ­citos Ãºnicos deducibles de una prop, ni una cuota
  mÃ­nima universal de 1,83. Cambio de lÃ­nea requiere nueva evaluaciÃ³n.
  Beneficiarios secundarios son hipÃ³tesis, no ventana garantizada.
- Medir ejecuciÃ³n/capacidad/utilidad neta de tarifa con datos reportados
  voluntariamente, registrando faltantes y sesgo. Replay sin volumen real
  no identifica impacto de suscriptores sobre el mercado. Reglas de oferta
  por jurisdicciÃ³n; Bonus Bets no equivalen a devoluciÃ³n de efectivo.
- Objetivo de inicio propuesto: captura y sombra, condicionado a preparaciÃ³n.
  Mantener puertas NBA y separaciÃ³n respecto a fÃºtbol. Solo documentaciÃ³n;
  sin implementaciÃ³n, Telegram, gasto de API ni apuestas. Comprobados enlaces
  locales y consistencia de ejemplos, sin ejecutar modelos o tests de cÃ³digo.

## 2026-10-03 â€” Plan maestro NBA por fases y auditorÃ­a

- Consolidado lo solicitado en `docs/nba_plan_fases_auditable.md`: F0â€“F9,
  37 tareas, 10 puertas, entregables, dependencias, criterios de evidencia,
  roles de revisiÃ³n y E0â€“E26 asignados. Referencias anteriores conservadas;
  el plan maestro dirige el MVP y el orden de implementaciÃ³n.
- Registro inicial en `docs/nba_plan_fases_auditoria.json` con hashes SHA256
  de cuatro documentos y commit de referencia. Se declara que el workspace
  tiene cambios locales; ese commit no se presenta como implementaciÃ³n NBA.
  Cero ejecuciones y cero puertas aprobadas. Integridad de un hash no equivale
  a prueba de fecha/origen; anclaje prospectivo se define en F3.
- Aislamiento, datos/PIT, minutos, distribuciÃ³n/calibraciÃ³n, Telegram de
  pruebas y confirmaciÃ³n prospectiva forman el nÃºcleo. F8 estudia noticias
  como challengers separados; F9 amplÃ­a con validaciÃ³n propia por mercado.
  Una variante no cambia el candidato bajo confirmaciÃ³n ni hereda su puerta.
- Piso 300 partidos/60 dÃ­as/3 bloques conservado como propuesta de muestra,
  no demostraciÃ³n de ROI ni calendario de ventas. La apertura de temporada
  referencia captura; no sustituye evidencia. Presupuesto/canal/familia y
  mÃ©tricas definitivas se registran como entradas pendientes.
- VerificaciÃ³n documental: JSON vÃ¡lido, 37 IDs de tareas coinciden con el
  plan, E0â€“E26 completos, dependencias sin ciclos, cuatro hashes correctos
  y enlaces locales existentes. No se ejecutaron modelos ni tests de cÃ³digo.
- Solo documentaciÃ³n/backlog. `apps/nba/` sigue sin existir; no despliegue,
  captura pagada, Telegram ni colocaciÃ³n de apuestas. El arnÃ©s local debe
  resolverse antes de futuras tareas de cÃ³digo, segÃºn instrucciones del repo.

## 2026-10-04 â€” Viabilidad NBA antes del inicio de temporada

- Usuario consulta si el modelo puede funcionar antes del inicio mediante
  descarga de histÃ³ricos. Revalidado calendario oficial: 20-oct-2026,
  16 dÃ­as desde fecha del cliente. `apps/nba/` sigue inexistente; registro
  declara not_started, cero ejecuciones y cero fases aprobadas.
- Un MVP deportivo reducido es un objetivo condicionado, no un compromiso
  de completar F0â€“F6 ni de ventaja comercial en 16 dÃ­as. Priorizar box scores
  y minutos de 2023-24 a 2025-26, luego ampliar a 2021-22 segÃºn cobertura;
  rosters/calendario/disponibilidad actuales son necesarios para 2026-27.
- HistÃ³ricos de cuotas/noticias y tracking tienen cobertura/acceso distintos.
  The Odds API documenta props desde 3-may-2023 a cinco minutos en planes
  pagados, sujeto a incorporaciÃ³n de deporte/casa/mercado. No gastar crÃ©ditos
  ni afirmar cobertura total; las estadÃ­sticas deportivas pueden investigarse
  sin haber adquirido ese histÃ³rico de cuotas.
- Verificadas documentaciÃ³n de nba_api y pbpstats, no probado todavÃ­a acceso
  de descarga desde este host ni tiempo total. No presentar repositorios o
  documentaciÃ³n accesibles como ingesta completada. No se escribiÃ³ cÃ³digo,
  iniciÃ³ descarga, activÃ³ Telegram ni cambiÃ³ el registro de auditorÃ­a inicial.

## 2026-10-04 â€” PreparaciÃ³n del plan y complemento de pretemporada

- Revisados maestro y registro: fases, puertas y evidencia definidos;
  implementaciÃ³n pendiente. AÃ±adido `docs/nba_pretemporada_arranque.md` tras
  indicaciÃ³n del usuario sobre la pretemporada. Recoger observaciones actuales
  y evaluar pronÃ³sticos experimentales sin mezclar mÃ©tricas con regular/playoffs.
- Orden local: arnÃ©s/aislamiento, acceso y cobertura, captura actual/histÃ³ricos
  recientes, baselines y distribuciÃ³n, ensayo de entrega, confirmaciÃ³n F7.
  Peso de seÃ±ales de pretemporada requiere evaluaciÃ³n histÃ³rica temporal;
  no traslado directo de minutos ni garantÃ­a de mejora o fecha de entrega.
- Registro amplÃ­a documentaciÃ³n mediante complemento y cambio registrado;
  conserva hashes de la base original. Ninguna puerta se aprueba por este
  ajuste. Presupuesto, fuentes/cobertura, operadores y destino de Telegram
  se resuelven antes de sus tareas dependientes; trabajo local puede empezar.
- Cambios documentales solamente: no aplicaciÃ³n, descarga ni activaciÃ³n.

## 2026-10-04 â€” RevisiÃ³n crÃ­tica de CLV, liderazgo de fuentes y QNN

- Analizado texto aportado en attachment c6f7385e. Fuentes primarias de
  scoring propio, QNN/benchmarking, NGBoost, glosario NBA y contratos/feed
  contrastadas. Referencias vagas a Stanford/Leiden y redirecciones del texto
  no constituyen tesis identificadas; no asumir que sus afirmaciones se probaron.
- AÃ±adido complemento `docs/nba_revision_critica_clv_fuentes.md` con CLV como
  diagnÃ³stico de mercado en F6/F7, sin desplazar pÃ©rdidas/calibraciÃ³n de F5.
  Definir referencia, cierre fresco, mismo contrato, margen, push/void y
  cobertura; cierre permanece fuera de features previas. Movimiento 2.00 a
  1.80 no acredita por sÃ­ solo probabilidad correcta o retorno favorable.
- Sharp/soft se reemplaza como regla universal por atributos/liderazgo medidos
  por mercado. E17/E7 investigan noticias, duplicaciÃ³n y tiempos censurados;
  feed de 60 s no permite inferir ajustes externos al segundo. USG% no es
  minutos; conservar disponibilidad/minutos/tasa/oportunidades separados.
- E20 sigue diferido; evidencia sobre barren plateaus y benchmarking no
  respalda aceleraciÃ³n general NBA. Corregida menciÃ³n externa a F18 (solo E18
  existe). Base original y fases conservadas; complemento registrado sin
  aprobar puertas. Solo documentaciÃ³n, sin runtime NBA ni descargas/envÃ­os.

## 2026-10-04 - Plan maestro NBA actualizado a 1.1

- Integradas correcciones en el propio maestro a peticion del usuario, con CLV complementario y protocolo de cierre/comparabilidad/margen, liderazgo por mercado y precision de tiempos.
- Incorporados pretemporada/historico reciente y separacion de regimenes; minutos, USG y oportunidades distintos; E20 sigue diferido con benchmarking completo.
- Version 1.0 y registro previo guardados byte por byte. Registro vigente sincroniza 37 tareas y amplÃ­a criterios pendientes, sin aprobar puertas ni declarar ejecuciones.
- Cambios solo documentales; no aplicacion NBA, descarga, despliegue ni envio Telegram. Verificacion documental independiente de los tests de runtime.

## 2026-10-04 â€” EjecuciÃ³n NBA con fuentes gratuitas

- Usuario autoriza ejecutar el plan y confirma fuentes gratuitas. Creado
  `apps/nba` con entorno/dependencias/configuraciÃ³n/datos propios; no se
  importa `qf`, carga `.env` global ni toca DB/implementaciÃ³n de fÃºtbol.
  Entorno raÃ­z previo roto: se conserva y usa `.local/harness-venv` auxiliar.
  ArnÃ©s antes: 606 pruebas; despuÃ©s: 606 pruebas (73,82 s), Docker omitido
  por no estar instalado. Suite NBA: 22 pruebas correctas (1,38 s).
- Fuentes NBA oficiales: CDN 403, stats timeout. Sin evasiÃ³n ni reintento
  ciego. A peticiÃ³n del usuario se investigan archivos GitHub reales:
  llimllib box scores recientes; shufinskiy jugadas/tiros desde 1996-97;
  hoopR box scores/calendarios ESPN hasta 2023. Descargas con commit/hashes.
  Ãndices/README que anuncian datasets ausentes no acreditan descarga.
- AuditorÃ­a revela llimllib individual 2022â€“2024 solo 15 partidos/aÃ±o,
  duplicados y minutos `MM:60`. Se preserva raw y rechaza bajo el contrato
  inicial; no reparar en silencio. Duraciones invÃ¡lidas permanecen en el
  denominador raw. Dataset normalizado: 67.066 filas, con cuarentena explÃ­cita.
- Protocolo local congelado para rebotes; benchmark retrospectivo condicional
  a participaciÃ³n, con todos los resultados del dÃ­a excluidos del historial.
  39.334 observaciones/2.048 partidos. CRPS 1,3510 vs 1,3947, error de minutos
  4,9723 vs 5,0773. Detalle y lÃ­mites en `docs/nba_arranque_resultados.md`.
  Esto no reconstruye disponibilidad previa ni demuestra EV/ROI ante casas.
- SQLite es almacenamiento de investigaciÃ³n explÃ­cito, no sustituciÃ³n ni
  aprobaciÃ³n de Postgres/Redis/recuperaciÃ³n G1. Cadena local sin anclaje externo.
  Ninguna puerta completa aprobada; resultados/reportes con evidencia real
  sustituyen el estado inicial inexistente. Telegram/cuotas pagadas inactivos;
  no apuestas ni cuentas/fondos operados. Falta capturar contexto actual,
  resolver cobertura/IDs, calibrar y ejecutar confirmaciÃ³n prospectiva.

## 2026-10-05 â€” NBA: cubrir huecos con archivos GitHub auditados

- Priorizado archivo real frente a README/clientes. SportsDataverse release
  aporta 30 Parquet individuales 1996-97 a 2025-26 (1.041.847 filas, incluidas
  no participaciones). IDs/assets/digests y recepciÃ³n local preservados. Cinco
  temporadas recientes cubren 1.230 partidos regulares; conciliaciÃ³n PTS/REB/AST
  mejora claramente, pero hay discrepancias y minutos MM:60 en cuarentena.
- Maezellemillan contiene todos los partidos pero no concilia muchos totales
  individuales: cobertura de partidos no demuestra censo completo de jugadores.
  Professor-Pete aporta 107.337 designaciones/1.165 snapshots de lesiones;
  falta validar PDFs, reloj/AMPM, IDs y corte temporal. No inventar recepciÃ³n
  histÃ³rica; mantener NOT YET SUBMITTED como desconocido.
- Props: sample 2.505 filas NBA, 1.415 al inicio/despuÃ©s y 730 sin tiempos
  interpretables; 53 pasan filtro bÃ¡sico, ninguna contrato completo aprobado.
  Otras muestras son un dÃ­a o carecen de identificaciÃ³n de partido. Sin ROI/CLV.
- Plantillas de tercero: 527 nombres, declara sync 1-sep; no valida todos los
  equipos actuales. Release de rosters sin 2027. nba_api es cliente no oficial
  y CommonTeamRoster no equivale a archivo histÃ³rico de lesiones.
- Documentado en docs/nba_fuentes_github_huecos_20261005.md, reporte JSON y
  NBA-RUN-004. Hashes verificados, registros anteriores preservados, puertas
  pendientes. Datos candidatos no integrados; sin cambios a aplicaciÃ³n/modelo,
  fÃºtbol, Telegram ni apuestas. No se repitieron tests por ser datos/documentos.

## 2026-10-05 â€” Incremento NBA F1â€“F5 y arranque de temporada

- Integrados cinco aÃ±os recientes SportsDataverse con fechas/IDs/tipos propios:
  154.058 registros, dataset por hashes separado. 2023-24 pasa de 15 a 1.159
  partidos regulares conciliados. 2025-26 pasa de 1.151 a 1.146: no reemplazar
  referencia por asumir superioridad. Minutos MM:60 y discrepancias siguen en
  cuarentena. Adaptador v2 cubre tambiÃ©n participantes sin referencia de equipo;
  v1/v2 generan bytes idÃ©nticos, replay reutilizado por SHA256 comprobado.
- Capturadas 30 plantillas ESPN 2026-27, 606 jugadores y recepciÃ³n UTC. IDs
  separados, sin uniÃ³n aproximada. 78 lesiones raw, 36 con fecha >48 h; fecha
  no verificada como actualizaciÃ³n. No inferir disponibilidad o salud de roster.
- Nueva evaluaciÃ³n referencia: 39.225 casos/2.044 partidos, CRPS 1,3519
  vs 1,3953. Sensibilidad entre fuentes: 36 resultados comunes difieren; comparaciÃ³n
  emparejada solo donde coinciden rebotes/minutos. Sin selecciÃ³n por scores.
- Experimento independiente startup-research-v0.1: priors del aÃ±o anterior,
  primeras 10 apariciones observadas, excluye dÃ­a objetivo y abstiene sin prior.
  8.264 casos/1.396 partidos, CRPS 1,3026 vs 1,3763; minutos MAE 5,3779 vs
  5,6229. Exploratorio (datos ya inspeccionados), sin sweep, rol/disponibilidad
  actuales ni EV/ROI. Escenario 2026-27 posible, siempre actionable=false.
- RecuperaciÃ³n local ensayada sobre checkpoint de 15 eventos y dataset; triggers
  y hashes preservados. No recuperaciÃ³n Postgres/Redis, raw completa ni anclaje.
  CÃ³digo fuente final preservado en snapshot propio, evidencia anterior intacta.
- ArnÃ©s inicial: problemas de temporales, resueltos sin cambiar cÃ³digo de fÃºtbol
  usando padre dentro del workspace y cacheprovider deshabilitado. ComprobaciÃ³n
  previa/final: 606 pruebas correctas; NBA: 47. Docker omitido por no disponible.
- Detalle en docs/nba_avance_fases_20261005.md y NBA-RUN-005..010. G0â€“G9
  pendientes. Faltan identidad/roles/disponibilidad, calibraciÃ³n y coherencia de
  equipo; despuÃ©s contratos/cuotas/outbox y Telegram de pruebas. Sin publicaciÃ³n.

## 2026-10-05 â€” continuaciÃ³n NBA, identidades/calibraciÃ³n/outbox

Se mantiene la abstenciÃ³n como resultado vÃ¡lido: el usuario autorizÃ³ continuar
las fases, pero la captura pÃºblica no acredita disponibilidad mÃ©dica ni una cuota
accionable. NBA.com respondiÃ³ con 619 identidades; 606 rosters ESPN se cruzaron
por nombre exacto normalizado y DOB independiente, obteniendo 596 equipos e IDs
concordantes. Diez quedan separados. Se capturaron 165 fichas (51,340,337 bytes)
y se ejecutÃ³ el capturador prospectivo de tres fuentes. De 596 cruces, 436 permiten
escenarios condicionales de arranque. Comparar el Ãºltimo equipo observado no
prueba rol actual; equipo previo desconocido se distingue de traspaso.

La calibraciÃ³n se comprueba contra masa discreta esperada, no solo 80% nominal:
8,264 observaciones/1,396 partidos reproducidos; cobertura 87.9356% frente a
masa 88.5199%, diferencia âˆ’0.5843 pp (IC por partido âˆ’1.2808 a +0.1703).
Sin fitting/promociÃ³n. El listado ESPN contiene 81 entradas no verificadas
para un partido; los enlaces oficiales 2026â€“27 consultados dieron 404. La
pÃ¡gina de cuotas del partido muestreado solo ofreciÃ³ totales de equipo: cero
props individuales validadas, sin generalizar a toda la fuente.

DecisiÃ³n humana: compartir el bot de fÃºtbol y TG_ALERT_CHAT. El enlace NBA
solo lee esos dos campos mediante configuraciÃ³n explÃ­cita, sin importar qf,
modificar su env ni copiar tokens. No hay credenciales activas locales. Outbox
NBA independiente: sellar antes de encolar, claim persistente antes de HTTP,
expiraciÃ³n con reloj real, no reintentar timeout ambiguo; prueba local sin envÃ­o.
La confirmaciÃ³n Telegram tampoco acredita recepciÃ³n por suscriptor. Cuotas,
rol/disponibilidad, lÃ­mites globales del bot y promociÃ³n prospectiva siguen
pendientes; el selector rechaza todos los picks comerciales actuales.

79 pruebas NBA y 606 de fÃºtbol aprobadas despuÃ©s del cÃ³digo final; Docker no
estÃ¡ disponible. Copia de 31 archivos en code_snapshots/continuation_20261005,
ledger de investigaciÃ³n verificado y registro ampliado a 50 evidencias/15 runs.
Las puertas G0â€“G9 permanecen pendientes. Detalles y condiciones de avance:
docs/nba_continuacion_20261005.md. Se conservaron reportes intermedios y se
registraron correcciones de abreviatura, conteo de equipo previo desconocido,
entrada CLI y nombre del lockfile; no se sustituyÃ³ evidencia anterior.
## 2026-10-05 â€” Scrapers NBA y contexto adicional

Diez repos fijados por commit y 52 archivos verificados; ningÃºn cÃ³digo de
terceros ejecutado. Se integran adaptadores NBA propios para observar
alineaciones pÃºblicas RotoWire y contrastar agregados PBP Stats por cuarto.
La captura actual aporta cinco partidos y 50 titulares previstos, sin
confirmaciÃ³n mÃ©dica. El piloto histÃ³rico conserva 15 partidos/745 registros
de quintetos, incluidos dos tiempos extra en un partido; seis descargas 503
quedan registradas. No son secuencias cronolÃ³gicas de cambios ni rebotes
individuales. Los dos calendarios nuevos tienen IDs/fechas, pero ninguna hora
de inicio; el PDF oficial actual devolviÃ³ 403 y no se intentÃ³ eludirlo.

DecisiÃ³n: ampliar datos de minutos/roles sin convertir observaciones previstas
en elegibilidad o cambiar los parÃ¡metros del modelo. Las puertas siguen
pendientes. IDs de proveedores y ledger siguen separados de fÃºtbol; el Ãºnico
puente autorizado continÃºa siendo bot/chat de alertas, sin credenciales
activas locales ni envÃ­o real. Pasan 100 pruebas NBA y 606 fÃºtbol. Se corrigiÃ³
UTF-8 en lectura de JSON y se conservÃ³ el primer informe con errores; el
harness final usa PATH completo y temporales dentro del workspace.
Evidencia: docs/nba_scrapers_avance_20261005.md y registro auditable NBA.

## 2026-10-05 â€” The Odds API de fÃºtbol tambiÃ©n cubre NBA

A peticiÃ³n del usuario se revisÃ³ la documentaciÃ³n oficial y se probÃ³ la clave
existente sin copiarla a NBA o reportes. AutenticaciÃ³n y eventos: 46 NBA
regular, ocho pretemporada. Prueba acotada de un partido: descubrimiento de
mercados y 22 lÃ­neas alternativas P/R/A de un jugador en DraftKings, solo
Over. Cuatro crÃ©ditos gastados; 19,652 restantes al capturar. Ãšltima
actualizaciÃ³n de props unos 193.6 segundos anterior a recepciÃ³n: no supera
frescura local de 60 segundos; faltan lado opuesto, reglas e IDs verificados.
No se descargaron histÃ³ricos ni se habilitÃ³ polling continuo. El presupuesto
del proveedor se comparte con fÃºtbol aunque el procesamiento NBA permanezca
separado; requiere reserva coordinada antes de operar. La revisiÃ³n no cambia
cÃ³digo de aplicaciÃ³n ni parÃ¡metros. Evidencia y prÃ³xima integraciÃ³n:
docs/nba_the_odds_api_revision_20261005.md, NBA-RUN-019. Puertas pendientes.

## 2026-10-05 â€” Acceso histÃ³rico NBA confirmado

El usuario confirma plan de pago. Prueba real: eventos histÃ³ricos y
player_rebounds responden 200; Houstonâ€“OKC 2025-10-21, 242 cuotas de 17
jugadores/ocho casas y 121 pares Over/Under. Once crÃ©ditos consumidos, saldo
observado 19,638. Tres relojes de mercado posteriores al snapshot por 7â€“26
segundos, todos anteriores al as-of solicitado: se excluyen para el corte
estricto del snapshot, sin alterar timestamps. Cinco casas/154 cuotas quedan
compatibles con ese corte; no se acredita recepciÃ³n propia histÃ³rica,
identidad NBA, reglas o rentabilidad. Fuente histÃ³rica disponible para el
dataset de precios; cÃ³digo/modelo sin cambios y puertas pendientes.
Evidencia: docs/nba_the_odds_api_historicos_20261005.md.

## 2026-10-05 â€” austin-pesina/nba_scrapes descargado

Descarga completa del commit d6d06b273d7a8818be3936f43425979db1ab92a3:
seis archivos/15,023 bytes, verificados con Git SHA-1 y SHA-256. Solo main;
cero datasets en Ã¡rbol, cero releases y cero artefactos Actions disponibles.
Los scripts consultan Basketball Reference y escriben Snowflake/exportes;
sus resultados no estÃ¡n publicados aquÃ­. AÃ±o final fijo 2026 = 2025â€“26;
IDs Basketball Reference, sin lesiones o precios histÃ³ricos de props.
No ejecutar proyectos de terceros para confundir herramientas con datos:
se conserva cÃ³digo como referencia, sin dotenv global, instalaciÃ³n o acceso
Snowflake. Cero filas nuevas y cero crÃ©ditos The Odds API. CÃ³digo/modelo
propio sin cambios. Evidencia: docs/nba_repo_austin_pesina_20261005.md.

## 2026-10-05 â€” Descargador histÃ³rico Edgar Parra revisado

Se inventariÃ³ el commit 7a0c22f6e26e8ec6854742dd88abf755d10733f4 y se
descargaron 14 referencias/167,099 bytes con hashes verificados. Su mÃ³dulo
masivo usa LeagueGameFinder y PlayerGameLogs por temporada: patrÃ³n Ãºtil para
completar huecos estadÃ­sticos. El Ãºnico CSV publicado estÃ¡ vacÃ­o y la base
SQLite descrita por el inventario del autor no estÃ¡ en main. Los 90
artefactos Actions son pequeÃ±os y el workflow publica reportes/logs; no se
descargaron ni se acreditÃ³ que contengan registros histÃ³ricos.

DecisiÃ³n: usar el patrÃ³n de consulta como referencia, manteniendo el pipeline
NBA propio. Exigir separaciÃ³n de competiciÃ³n/temporada y validaciÃ³n de
censo, cachÃ©, minutos y disponibilidad original. Su historical_odds_backfill
asigna -110 a ambos lados y usa fecha de observaciÃ³n como fecha de partido;
no constituye histÃ³rico real de cuotas. No ejecutar ni adoptar ese modelo.
La revisiÃ³n aÃ±ade cero partidos y consume cero crÃ©ditos de The Odds API.
Se sellaron Austin/Edgar en NBA-RUN-021/022: 80 evidencias verificadas y 33
archivos propios sin cambios; todas las puertas pendientes. Documento:
docs/nba_repo_edgar_parra_20261005.md.

## 2026-10-05 â€” HistÃ³ricos gratuitos y ahorro de crÃ©ditos

El usuario autoriza aprovechar scrapers para histÃ³ricos sin gastar crÃ©ditos.
Se contrastÃ³ cobertura regular: 5,830/6,150 partidos aceptados en cinco
temporadas, 320 pendientes por ausencia o cuarentena. Una consulta acotada
oficial LeagueGameLog, jugadores 2025â€“26 regular, agotÃ³ lectura tras 20 s;
manifiesto conservado, sin reintentos ni nuevas filas. Los archivos gratuitos
ya recibidos siguen disponibles. No se puede declarar descarga oficial
completa o funcionamiento del scraper desde esta conexiÃ³n.

DecisiÃ³n: completar estadÃ­sticas con fuentes gratuitas y reservar presupuesto
para precios autÃ©nticos. Son datasets distintos; el backfill de -110 no
sustituye cuotas histÃ³ricas. Se documenta muestra de 100 partidos/rebotes/una
regiÃ³n/un snapshot â‰ˆ1,000 crÃ©ditos mÃ¡s descubrimiento, sin ejecutarla. Cero
crÃ©ditos gastados en esta tarea; cÃ³digo/modelo sin cambios. Documento:
docs/nba_historicos_gratis_presupuesto_20261005.md.


## 2026-10-05 â€” Los picks de la sombra, visibles en `/control`

Pedido del usuario: ver cuÃ¡les se habrÃ­an publicado, no solo los totales.
La tabla sale de `publishable()`, no de una consulta propia: si el panel
enseÃ±ara otra selecciÃ³n, el usuario juzgarÃ­a una muestra distinta de la que
decide la puerta (comprobado en producciÃ³n: 28 filas = `publishable.n` 28).
Va tras el login del panel y nunca a la web pÃºblica porque revela casa,
cuota y antelaciÃ³n del criterio. Stake mostrado = el que se publicarÃ­a
(Ã— factor de incertidumbre, db/039).

Despliegue mÃ­nimo, sin reconstruir: el repo del servidor va por detrÃ¡s de
HEAD (`promotion.py`, `clv.py`, `dixon_coles.py`, `api_football.py`â€¦) y el
contenedor de la API aÃºn mÃ¡s (sin `latencia.py`, `shadow_sharp` previo a
db/039). Reconstruir habrÃ­a desplegado de rebote la lÃ³gica de la puerta. Se
copiÃ³ al contenedor su propio `shadow_sharp.py` + las dos funciones nuevas
(solo aÃ±ade lÃ­neas), `console.py` y `console.css`; el repo del servidor
recibe la versiÃ³n HEAD + cambio. Respaldo en
`~/respaldo_20261005_panel_sombra`. Pendiente aparte: decidir cuÃ¡ndo se
sincroniza y reconstruye el servidor con HEAD.

## 2026-10-05 â€” RecuperaciÃ³n NBA gratuita implementada y piloto auditado

El usuario autoriza avanzar con boxscores, GameRotation y PDF oficiales de
lesiones. Se implementaron inventario reproducible, capturadores finitos que
conservan originales/errores y validadores estrictos de estadÃ­sticas,
minutos, stints y cronologÃ­a. El inventario identifica 395 partidos conocidos
pendientes: 320 regulares, 71 de pretemporada, tres de playoffs y uno de
play-in. En 299 pendientes regulares la fuente contiene minutos invÃ¡lidos;
no se corrigen valores como 30:60 sin evidencia independiente. Los siete
conflictos de referencias de equipo ya tienen GameID; no eran IDs ausentes.

Las consultas reales de boxscore y rotaciÃ³n oficiales terminaron en
ReadTimeout; la alternativa CDN devolviÃ³ 403. Se detuvo cada lote y se
conservÃ³ la evidencia, sin importar partidos o stints. Se recibieron tres
PDF oficiales de lesiones, ocho pÃ¡ginas verificadas visualmente y 84
observaciones de 30 jugadores distintos; cuatro cambios reales de estado
entre los primeros reportes. El nombre 05PM corresponde a una cabecera
17:30 ET: se decide usar la cabecera y convertir con zona/DST validada.
RecepciÃ³n en 2026 de informes de 2025 no acredita disponibilidad original;
el modo retrospectivo queda separado del filtro prospectivo. IDs mÃ©dicos,
hora de partido y cobertura de archivo siguen pendientes.

ValidaciÃ³n: 136 pruebas NBA y 609 de harness pasan; baseline de harness
606 antes de cambios concurrentes de fÃºtbol, que se preservan y no se
atribuyen a NBA. Docker no disponible. CÃ³digo propio congelado en 37
archivos; dataset/modelo aceptados conservan hash. NBA-RUN-024â€“026,
100 evidencias verificadas y ledger de 60 eventos, sin ancla externa.
Cero crÃ©ditos The Odds API, cero nuevos partidos, cero publicaciÃ³n de picks
y todas las puertas pendientes. Documento:
docs/nba_recuperacion_piloto_20261005.md.

## 2026-10-05 â€” Basketball Reference responde; alternativas con cobertura real

La lista del usuario se contrastÃ³ con siete commits e interfaces reales.
DecisiÃ³n: priorizar una muestra independiente que responda, conservando los
IDs y la precisiÃ³n de cada fuente. Basketball Reference devolviÃ³ HTTP 200;
se conciliaron veinte participantes de 0022100012, 240 minutos por equipo
y P/R/A completos, sin errores del validador existente. El valor NBA 33:60
de Michael Porter Jr. corresponde a 33:59 en esa fuente, no a 34:00. No
corregir todas las anomalÃ­as de reloj mediante una regla supuesta. El
resultado queda en staging y el dataset principal/modelo no cambian.

ESPN Parquet 2025â€“26 descargado y digest GitHub verificado: 34,883 filas,
1,326 eventos. Candidatos Ãºnicos por fecha/equipos para 84 regulares, tres
playoffs y un play-in pendientes recientes; ninguno de 71 pretemporada.
Minutos enteros e IDs ESPN impiden importar directamente como NBA exacto.
JaseZiv aporta 73,306 transacciones hasta 2025-05-13, no publicaciÃ³n
horaria; una fecha 1899-12-30 y 16 filas sin equipo requieren cuarentena.
Workflow diario escrito no prueba actualizaciÃ³n: commit Ãºltimo mayo 2025.

nba_api incluye PlayIn/Pre Season pero no evita bloqueo del endpoint;
pbpstats documenta Client y overrides; nbainjuries usa get_reportdata con
Java y no garantiza timestamp de cabecera en sus siete columnas. No se
ejecutaron bibliotecas externas ni se gastaron crÃ©ditos The Odds API.
609 pruebas del harness pasan; 37 archivos NBA y 100 evidencias previas
sin cambios verificados. Puertas pendientes. Documento:
docs/nba_repos_alternativas_verificadas_20261005.md.

## 2026-10-05 â€” AmpliaciÃ³n Basketball Reference: 159 partidos recuperados

El usuario pide ampliar esta recuperaciÃ³n. DecisiÃ³n: cachear por fecha,
preservar recepciÃ³n/raw y generar versiones nuevas que heredan intacto el
dataset anterior. Parser, cruce por mismo partido/equipo/localÃ­a y P/R/A,
conciliaciÃ³n existente sin bajar umbrales. Variantes de sufijos omitidos y
puntos en iniciales solo con candidato Ãºnico; rechazar generaciones
contradictorias y apodos. No atribuir DNP o lesiÃ³n por ausencia de una fila.

Se programaron 263 fechas con lotes de veinte y seis segundos mÃ­nimos.
140 pÃ¡ginas vÃ¡lidas recibidas/reutilizadas; 2024-03-11 devolviÃ³ HTTP403,
se detuvo el lote ocho y no se intentaron fechas posteriores. Cuerpo y
parada del proveedor conservados. Cero crÃ©ditos The Odds API, sin proxies
o reintentos. La causa precisa del rechazo no estÃ¡ acreditada.

Versiones parciales de 34 y 111 partidos y final de 159 partidos regulares
recuperadas. La versiÃ³n ampliada contiene 157,375 filas: 154,058 originales
idÃ©nticas y 3,317 nuevas (3,316 con participaciÃ³n). Se reparsaron las 136
pÃ¡ginas utilizadas y reconciliaron de nuevo los 159 partidos; 597 jugadores
NBA con cruce consistente entre partidos. Hash antiguo preservado, sin
reentrenamiento/publicaciÃ³n. Cobertura regular: 5,989/6,150; 2021â€“22
completa, 2022â€“23 queda a un partido. Restan 161 regulares y 75 no regulares
conocidos; calendario antiguo de playoffs no se declara completo.

Nueve recibidos se mantienen separados: siete diferencias de un REB/AST,
referencia parcial 0022300835 (42.75 minutos y marcador parcial), y
0022300810 con fila Thomas Bryant sin minutos/comentario. No asignar DNP
a esa ausencia ni modificar agregados para forzar concordancia. Los otros
152 regulares no tienen pÃ¡gina vÃ¡lida en este intento. DiagnÃ³stico local
por equipo/valor conservado.

172 NBA/609 harness pasan; 39 archivos propios congelados, ambas versiones
del cÃ³digo conservadas. Fixture nuevo de colisiÃ³n se corrigiÃ³ tras un fallo
de prueba; logs fallido y posteriores preservados. Docker no disponible;
revisiÃ³n propia sin revisor independiente. Cambios concurrentes de fÃºtbol
preservados y no atribuidos a NBA. Todas las puertas pendientes. Documento:
docs/nba_basketball_reference_recuperacion_20261005.md.

### 2026-10-05 â€” Black Falcon ESPN NBA: utilidad comprobada antes de escalar

La cuenta Apify ya tenÃ­a sesiÃ³n en el navegador; se usÃ³ sin copiar tokens.
Diez candidatos explÃ­citos (6 regular, 2 playoffs, 1 play-in, 1 pretemporada),
mÃ¡ximo US$0.25/400filas/120s. Run T6I23rByjmvXbCpL2 correcto: 282 filas,
226 participantes/56DNP, US$0.142 mostrado. JSON Ã­ntegro de 927,312 bytes,
entrada, log, recibo, screenshot y scripts congelados; sin crÃ©ditos Odds API.

No se ampliÃ³ porque 247 filas de nueve partidos duplican ESPN previo y los
minutos vuelven a ser enteros: no resuelven valores NBA malformados ni prueban
240 minutos exactos por equipo. P/R/A de participantes coinciden; 53 DNP
comparan null contra cero, conservados sin rellenar. Cuatro fechas UTC
requieren conversiÃ³n explÃ­cita a America/New_York; primer assert detectÃ³
esa diferencia y se corrigiÃ³ la semÃ¡ntica del reloj, no el emparejamiento.
Los 20 totales P/R/A y puntos por cuartos/prÃ³rroga cuadran. playerActive=false
en 126 participantes impide interpretarlo como disponibilidad prepartido.

Las 35 filas nuevas de pretemporada NYK/PHI 2025-10-02 siguen separadas:
referencia NBA con ambos visitantes y sin candidatos individuales NBA.
No hay importaciones, reentrenamiento ni promociÃ³n de puertas. Cobertura
aceptada 5,989/6,150 regulares; 161 regulares/236 pendientes conocidos totales.
39 archivos NBA de cÃ³digo siguen con sus hashes anteriores; fÃºtbol preservado.
609 pruebas pasan antes/despuÃ©s; intentos iniciales del harness con PATH
incompleto no cuentan como pruebas. Docker no disponible. RevisiÃ³n propia.
NBA-RUN-031, 139 evidencias verificadas, cadena 77 eventos sin ancla externa.
Documento: docs/nba_blackfalcon_descarga_20261005.md. Siguiente paso Ãºtil:
fuente con segundos y corroboraciÃ³n de referencias, no compras masivas de
estadÃ­sticas que ya tenemos.

## 2026-10-05 â€” Â¿Limitar a cuota â‰¤ 1,80 para acertar mÃ¡s? No con las casas de los suscriptores

Pregunta del usuario tras ver 12 de 19 perdidas en la sombra (que eran lo
esperado: 6,25 ganadas esperadas al cierre, 7 reales). Medido sobre
football-data (7 ligas, 2019/20-2024/25, 14.294 partidos, firma
d5cbc3151164), criterio actual aproximado: mejor de bet365/1xBet con edge
temprano â‰¥ 2%. De 683 apuestas solo 14 tienen cuota â‰¤ 1,80 (2%), aciertan
el 71% y su EV al cierre es âˆ’0,07% [âˆ’1,78, 2,33]: ahÃ­ no hay valor. El valor
estÃ¡ en 2,51-5,00 (+2,8% y +1,9%, IC entero > 0). Con todas las casas el
tramo â‰¤ 1,80 sÃ­ da +3,4% [2,1, 4,8], pero esas casas no cuentan para la
puerta. En vivo, 2 de 28 publicables tienen cuota â‰¤ 1,80.

DecisiÃ³n: no se restringe la cuota. SubirÃ­a el acierto, pero bajarÃ­a o
anularÃ­a el valor esperado y dividirÃ­a por ~15-50 el ritmo de una muestra
que ya necesita ~6 meses. Acierto alto â‰  rentable: es un problema de
comunicaciÃ³n al suscriptor, no del criterio.

## 2026-10-05 â€” Probabilidad real de cada pick en la web

Pedido del usuario tras ver que la sombra pierde 12 de 19 (lo esperado con
cuotas medias de 3,9). La probabilidad que se enseÃ±a es `fair_prob`, la de
Pinnacle sin margen en el snapshot del pick, NUNCA `model_prob`: el modelo no
elige los picks y su edge resultÃ³ anti-seÃ±al. Se muestra en porcentaje y en
frecuencia ("29% Â· sale 1 de cada 3.4") porque la frecuencia es lo que
prepara al suscriptor para las rachas. El bloque real aÃ±ade el acierto
esperado de la lista (media de `fair_prob`) y no lo estima si a algÃºn pick le
falta el dato: los picks anteriores a db/017 lo tienen NULL.

Solo frontend: `/picks/free` ya devolvÃ­a `fair_prob`. Desplegado copiando los
4 estÃ¡ticos al contenedor y al repo del servidor (coincidÃ­an con HEAD; se
leen del disco en cada peticiÃ³n, sin reinicio). Respaldo en
`~/respaldo_20261005_prob_real`. Con la publicaciÃ³n pausada el bloque real
sigue vacÃ­o; hoy solo se ve en las tarjetas de demostraciÃ³n.

## 2026-10-05 â€” Propuesta del usuario: picks con 80% de acierto (medido, sin decidir)

Motivo del usuario: los clientes valoran acertar mÃ¡s que batir a la casa, y
no toman todos los picks. Medido en football-data (7 ligas, 6 temporadas,
mejor cuota de bet365/1xBet, firma d5cbc3151164): selecciones con
probabilidad justa â‰¥ 80% = 5,2% de los partidos (~123/temporada), aciertan
el 84,8% a cuota media 1,15, ROI âˆ’2,4% y EV al cierre âˆ’2,6%. Con casa
pagando â‰¥ 2% sobre el justo: 0 casos. NingÃºn umbral entre 50% y 85% da EV
positivo. SimulaciÃ³n de un cliente que toma picks al azar: el favorito â‰¥ 80%
deja en ganancia al 53% tras 10 picks, al 27% tras 100 y al 14% tras 300; el
criterio de valor, al 45%, 51% y 54%. La objeciÃ³n del usuario es real (el
valor es casi una moneda al aire para el cliente hasta cientos de picks),
pero el 80% no la resuelve: pierde mÃ¡s cuanto mÃ¡s se sigue. Pendiente de
decisiÃ³n del usuario; nada cambiado.

## 2026-10-05 â€” NBA: servicios auxiliares y conciliaciÃ³n de histÃ³ricos

Se ampliÃ³ solo Flashscore, que aporta minutos fraccionarios a dos decimales,
y el calendario NBA para referencias canÃ³nicas. Cinco runs Apify acotados,
US$2.064 mostrado, cero crÃ©ditos The Odds API. NingÃºn plan/recarga/schedule.
Tres lotes Flashscore: 227 partidos/6,631 registros; calendario ampliado99
partidos, incluidos los71 IDs de pretemporada pendientes. Cinco partidos
presentan discrepancias con referencias previas; no se sobrescribieron.

DecisiÃ³n: aceptar Ãºnicamente el partido completo con IDs Ãºnicos, P/R/A por
jugador, segundos previos vÃ¡lidos concordantes y conciliaciÃ³n estricta. Un
contraejemplo real de +41/-41 segundos conserva el total del equipo, por lo
que ese total nunca sustituye la comprobaciÃ³n individual. Se aÃ±adieron67
partidos (63regular,3playoffs,1play-in),1,713 filas/1,470 participantes a una
versiÃ³n nueva:159,088 filas, todas las157,375 previas intactas. Cobertura
regular6,052/6,150=98.41%; quedan98regular y71pretemporada. Los62 boxscores
candidatos de pretemporada descargados siguen separados por identidades o
referencias. Cero pendientes de playoffs/play-in solo en el inventario
actual; no certifica todo el histÃ³rico.

VerificaciÃ³n completa de los67 partidos,1,400 relojes previos vÃ¡lidos,34
pÃ¡ginas de originales,17 controles adversariales y139 evidencias previas.
Los39 archivos NBA congelados y modelo preservados; cambios concurrentes
de fÃºtbol no tocados. Esta es auto-revisiÃ³n de investigaciÃ³n y hashes
locales, sin anclaje externo ni promociÃ³n G0â€“G9. Los timestamps de captura
son actuales; lesiones disponibles antes del partido no se inventan desde
DNP. No ampliar el mismo scraper mientras falte conciliaciÃ³n. Informe:
docs/nba_servicios_recuperacion_20261005.md.

Cierre verificado: harness antes/despuÃ©s609 pruebas aprobadas (una advertencia;
Docker no disponible);17 controles de datos aprobados. NBA-RUN-032 registra
152 evidencias verificadas; cadena78 eventos, cabeza
c89ee0f4ab3ef619536a259a2fee9b91c03d4be074123ff3933edfe0bebd8389.
Dataset final_v2 SHA256f10b5e8e5dc8ba7dc85dac184fdf90ac25c17b64fe48a7e14b00f5d8885a13fd.
Los pilotos/expanded previos son exploratorios; final_v2 es la versiÃ³n
auditable de esta recuperaciÃ³n. Recibos y74 originales referenciados en
manifest; snapshots de4 scripts. No se modificÃ³ el modelo ni su config.

## 2026-10-05 â€” NBA: pendientes, lesiones, rotaciones y props

DecisiÃ³n: descargar candidatos no significa recuperar un partido, y una
cabecera histÃ³rica no prueba recepciÃ³n en su momento. ESPN completo sobre
166candidatos permite aÃ±adir16partidos (3regular/13pretemporada),515filas,
159603totales;159088anteriores intactas.6055/6150regulares;95regular y58pre
siguen pendientes por conflictos de reloj/PRA/referencias/IDs. No convertir
minutos enteros ESPN en segundos; Flashscore conserva su supuesto de
redondeo decimal. Perfiles NBA respondieron403; lote detenido sin forzarIDs.

PBP local reconstruye5161partidos/217334tramos;891cuarentenas. El presupuesto
de cuantizaciÃ³n cuenta intervalos continuos del propio jugador por perÃ­odo,
no cada cambio del quinteto por sustituciones de compaÃ±eros. Sin carryover
automÃ¡tico de titulares, sin rescalar clocks, y sin tratar rebotes de equipo
como jugadores. La versiÃ³n final es chronological_stints_v4_20261005.

486PDFs/43924filas/36300registros nominales mÃ©dicos: un corte diario,
330fechas pendientes tras403.272motivos partidos entre pÃ¡ginas unidos solo
con precedente nominal/estado vÃ¡lido y fragmento inicial de motivo. Segundo
motor verifica los486PDFs.43675filas conpartido,36063conjugador;237nominales
sinID(13nombres).1213regulares2025-26conreporte anterioraT60;974conambos
equipos enviados. El recibo es actual: reconstrucciÃ³n retrospectiva, no PIT
ejecutable. Absent/unsubmitted siempre desconocido. IDs no prueban roster
histÃ³rico. VersiÃ³n final injury_daily_joined_remaining_v2_20261005.

20juegos/40snapshotsrebotes,2961pares/5922precios;420crÃ©ditos de lÃ­mite500
predefinido conservador mientras la pregunta opcional seguÃ­a sin respuesta.
No nueva ejecuciÃ³n Apify.88casa/mercado rechazados por actualizaciÃ³n futura
al snapshot y73entidades por IDnominal ambiguo; no ROI ni reglas de void
inventadas. Dos horarios del proveedor revisados entre snapshots: se
registran las versiones y los cortes deben preceder todos los horarios.
VersiÃ³n final historical_rebounds_remaining_v2_20261005.

19controlesde corrupciÃ³n/temporalidad, todos16boxscores/515filas,
todos5161juegos de stints,6replaysrawPBP,40replayscuotas y486PDFssegundomotor.
Harness609antes/despuÃ©s(unaadvertencia,Dockernodisponible). Auto-revisiÃ³n;
hasheslocales, no anclaje externo.39archivosNBA/modeloconfig y152evidencias
anteriores preservados. NBA-RUN-033; G0â€“G9 pendientes. FÃºtbol no modificado,
sin entrenamiento/publicaciÃ³n/avisos. Informe detallado y manifests:
docs/nba_pendientes_recuperacion_20261005.md.

Cierre del lote de pendientes: NBA-RUN-033,168evidencias verificadas,
974originales/manifests fijados y22scripts con snapshot; cadena79eventos,
cabeza dca828a0271f04a12d518b74a7f43ea9e75a3dc628b459a3c58228aca958c3fe.
Datasetboxscore SHA25641c5a4f82d3638138a6a4d9b5bb7fb21033eecbae5e3fa07de99dc074d67ef68.
El cierre certifica este lote verificado, no la finalizaciÃ³n del histÃ³rico.

## 2026-10-06 â€” Servidor sincronizado con HEAD (paso previo de la lÃ­nea de alta probabilidad)

Lo que parecÃ­a un servidor muy atrasado era casi todo finales de lÃ­nea: el
repo del servidor tenÃ­a archivos con CRLF (copiados desde Windows) y contenido
idÃ©ntico. Comparando sin CR, el worker ya corrÃ­a HEAD salvo el brazo
"mÃ¡s-menos" de `player_value.py` y mÃ³dulos de investigaciÃ³n; la API iba mÃ¡s
atrÃ¡s (picks, config, odds_worker, shadow_sharp). Con visto bueno del usuario:
commit af9c8b4 del trabajo del dÃ­a ya desplegado a mano (si no, la
sincronizaciÃ³n lo habrÃ­a revertido), `git archive HEAD` sin `harness/`,
build y reinicio de api/worker en un minuto sin crons (04:14 UTC). Verificado:
cadena (7 lotes), salud, model-card, web, /control 401 y crons sin errores.
Respaldo en `~/respaldo_20261006_presync.tgz`. Regla para el futuro: comparar
servidor y repo con `tr -d '
'`, o la lista de "cambios" engaÃ±a.

## 2026-10-06 â€” NBA: recuperaciÃ³n con actores adicionales de Apify

Se usÃ³ la cuenta existente para seis capturas acotadas de Basketball API y
Action Network, US$2.341 del crÃ©dito gratuito; saldo mostrado aproximado
US$0.45. Sin recargas, suscripciones ni crÃ©ditos The Odds API. El actor de
boxscores publica secondsPlayed: Clippersâ€“Nuggets 0012500052 agrega 40 filas
(30 participantes y diez DNP expresamente seÃ±alados por ESPN). Ambos equipos
suman 14400 segundos y PRA coincide con ESPN/referencia NBA. Sus 13 teamId
contradictorios no se usan: equipo histÃ³rico unido por lado, calendario y
pertenencia ESPN; identidad NBA por nombre completo Ãºnico. Pelicansâ€“Melbourne
solo tiene un equipo y queda como candidato. Dataset159643; anteriores159603
intactos. El calendario nuevo tiene71juegos y68cruces exactos NBA; tres cÃ³digos
extranjeros separados.

Action Network devuelve385precios P/R/A de casas reales sin hora original,
y movimiento solicitado vacÃ­o;18de19lesiones anexas se actualizaron despuÃ©s
del partido. Ninguno entra al backtest. Una fecha solicitada no acredita que
sus bloques anexos fueran conocidos entonces; no ampliar ese flujo para PIT.

Ocho controles de corrupciÃ³n,609pruebas antes/despuÃ©s,39archivos NBA/modelo
congelados intactos,168evidencias anteriores/974originales/22scripts verificados;
181evidencias totales. NBA-RUN-034,80eventos de auditorÃ­a;G0â€“G9 pendientes.
95regular y57pretemporada aÃºn faltan; lesiones/rotaciones y props conservan
los huecos anteriores. Sin entrenamiento/publicaciÃ³n ni avisos; fÃºtbol no
modificado. Informe:docs/nba_apify_fuentes_adicionales_20261006.md.

## 2026-10-06 â€” NBA: API-NBA con clave autorizada por el usuario

La autenticaciÃ³n funciona, pero el permiso NBA efectivo es Free: los endpoints
de temporada2025 devuelven error de plan, aunque la guÃ­a pÃºblica no dejaba
clara esa restricciÃ³n.80pendientes2025-26(23regulares/57pretemporadas) bloqueados.
No contratar ni recomendar una compra como garantÃ­a de recuperaciÃ³n: el acceso
y la precisiÃ³n son requisitos distintos. Clave solo en archivo local ignorado;
estados sanitizados sin datos personales, evidencias sin encabezados secretos.

Tres calendarios y72cruces exactos por fechaEastern/localÃ­a/nombre.72boxscores
descargados,1543registros; todos los minutos individuales son enteros, sin
segundos. Consulta por temporada sola rechazada;83peticiones de datos,3errores
de aplicaciÃ³n y2/status. LÃ­mite local95, cuotaFree100/dÃ­a. Estado final70/100;
cabeceras no monÃ³tonas conservadas, sin fingir que equivalen al contador local.
Cero suscripciones nuevas, Apify o crÃ©ditos TheOddsAPI.

No hubo partido aceptado: conflictos de PRA, identidad y segundos previos
vÃ¡lidos frente al reloj decimal alternativo. API-NBA no repara33:60 ni38:60
desde un entero. Referencias de rebotes contrapuestas no sobrescritas con
sumas individuales; no expandir iniciales o inferir DNP. Conservar72candidatos
fuera del dataset aceptado;159643filas previas y152pendientes permanecen.

693pruebas antes/despuÃ©s,10controles de corrupciÃ³n;181evidencias previas y39
archivos NBA congelados intactos. NBA-RUN-035,194evidencias totales,81eventos
ledger,cabeza a40baa89c829109da4f82d2a21f23f5629943f01eac3a62c1fb818cf3dfd077e.
Auto-revisiÃ³n, sin anclaje externo, sin entrenamiento/puertas/picks/Telegram.
FÃºtbol y cambios concurrentes no tocados. Informe y manifiestos:
docs/nba_api_nba_recuperacion_20261006.md.

## 2026-10-06 â€” LÃ­nea de alta probabilidad: implementada, integrada y desplegada apagada

Pedido del usuario: pronÃ³sticos "seguros" de al menos 80 %, aparte de los picks
de valor. DiseÃ±o, plan y ejecuciÃ³n con subagentes (docs/superpowers/). Decisiones
clave (el porquÃ©):

- Probabilidad de Pinnacle sin margen, no del modelo: la promesa es un
  porcentaje y tiene que salir de la referencia calibrada. Se publica el
  candidato de MENOR probabilidad en [80, 95]: cumple el 80 % y es el mÃ¡s Ãºtil.
- Goles por ajuste al mercado con push correcto (`pricing.totals_fair_over`):
  Pinnacle cotiza 2 de cada 3 lÃ­neas en cuarto o gol entero. Prueba histÃ³rica
  (firma d5cbc3151164): regla completa prometido 84,45 / real 84,60; pasan
  h2h, doble oportunidad y las tres lÃ­neas de goles.
- Sellado con UNA fuente de verdad (`hashchain.lote_lleva_alta`): la revisiÃ³n
  de la tarea 7 encontrÃ³ que, con la lÃ­nea encendida y sin fecha de corte, la
  API habrÃ­a mostrado como sellado algo que el lote no cubrÃ­a.
- Probabilidad pÃºblica a punto entero (decisiÃ³n del usuario): con 6 decimales,
  1 âˆ’ prob de una doble oportunidad era el precio justo del no favorito, el
  criterio de los picks de valor. El lote conserva el exacto.
- Pausa mÃ¡s exigente (decisiÃ³n del usuario): IC99, mÃ­nimo 10 semanas y z â‰¤ âˆ’4
  para fallos groseros. Con IC95 y 8 semanas, ~32 % de lÃ­neas calibradas se
  habrÃ­an pausado en falso en 6 meses (pausa pÃºblica y manual de levantar).
- Esquema verificado en producciÃ³n, no en tests (decisiÃ³n del usuario).
- Despliegue 2026-10-06 18:12 UTC con `ALTA_PROB_ENABLED=0` y corte
  `LOTE_ALTA_PROB_DESDE = 2026-10-07` (el 6-oct ya habÃ­a sellado). Vista
  previa: 2 de 15 partidos (parÃ³n de selecciones; sin goles porque el precio
  reciente a las 08:00 es de API-Football). ActivaciÃ³n pendiente del usuario
  tras verificar el lote del 7-oct.


## 2026-10-06 â€” NBA: lineups Ramiro y contraste offline pbpstats

Cinco CSV pÃºblicos fijados al commit e702d9b7b585bb79e751eb52d5d767e29f16cab0, 110,072,340 bytes y 6,150 partidos regulares. 6033 pasan estructura/minutos; la aceptaciÃ³n final exige replay de PBP, titulares demostrados por perÃ­odo, sustituciones, marcador y minutos individuales sin rescaling. Se aÃ±aden 7 partidos (4 de las 891 cuarentenas); la versiÃ³n combinada conserva los 5,161 previos y contiene 5168 juegos / 217619 tramos. Permanecen 887 cuarentenas previas y 887 regulares aceptados sin rotaciones.

pbpstats 1.3.11 contrasta 248283 sustituciones con IDs corroborados y red bloqueada, no ingestiÃ³n nativa V3/posesiones. Fuente y PBP pueden compartir origen NBA; no se presume revisiÃ³n independiente o disponibilidad prepartido. 15 controles adversariales, invariantes completos, 39 archivos NBA congelados intactos; harness 693/693, NBA 172. Cero crÃ©ditos de pago, sin entrenamiento/promociÃ³n/picks. NBA-RUN-036; informe docs/nba_ramiro_pbpstats_auditoria_20261006.md.

## 2026-10-06 â€” MÃ¡s pronÃ³sticos de goles: API-Football ya trae las lÃ­neas de Pinnacle

La lÃ­nea de alta probabilidad casi no daba goles: a las 08:00 UTC el precio
de â‰¤ 6 h suele ser de API-Football, y `af_odds` pedÃ­a solo `bet=1` (1X2). La
misma peticiÃ³n por partido, sin filtro, trae de Pinnacle "Goals Over/Under"
(bet 5) con 1,5 / 2,5 / 3,5 / 4,5 y cuartos, mÃ¡s las casas blandas. Prueba de
solo lectura (22 partidos de las prÃ³ximas 72 h, 21 peticiones): 22/22 con
1X2 + O/U de Pinnacle; pronÃ³stico de goles en 15/22 (hoy 0) y pronÃ³stico en
18/22 en total. LÃ­nea directa de Pinnacle frente al ajuste Dixon-Coles con su
2,5: media âˆ’0,03 pts, mÃ¡x. 1,55 pts (n = 46): el ajuste validado en el
histÃ³rico tambiÃ©n cuadra en vivo. Coste en peticiones: cero. Pendiente de
decisiÃ³n del usuario: guardar bet 5 en `af_odds_snapshots` (necesita columna
`line` y nuevo Ã­ndice Ãºnico NULLS NOT DISTINCT) y que `alta_prob_datos` lea
esos totales.


## 2026-10-06 â€” NBA: ejecuciÃ³n real de scrapers, Java y ZenRows

Los152boxscores pendientes llegaron desde NBA Stats sin proxy;53pretemporadas pasan,1903filas nuevas/161546combinadas,67de71juegos. Los95regulares conservan minutos invÃ¡lidos/discrepancias; capturar no equivale a aceptar. El archivo pÃºblico de pbpstats, actualizado abril2023, aporta405PBP de candidatos: el replay con IDs explÃ­citos V2 y las corroboraciones Ramiro/native EnhancedPbp aÃ±aden325rotaciones. Combinado5493juegos/231075tramos,562regulares aceptados sin rotaciÃ³n; previos159643filas/5168rotaciones intactos.

Java portÃ¡til permite18acuerdos de tres parsers sobre seis PDFs/398registros nominales; no recupera fechas nuevas. BRef/CDN/PDF403 yCDX503 se conservan; no se reintentan mediante rotaciÃ³n IP. oddsapiR revisado, sin Rscript ni llamadas pagadas nuevas; otros repos de la tabla quedan con estado explÃ­cito, no se afirma ejecuciÃ³n total. Toolkit ZenRows1.3.1/MCP2.4.0 instalados con alcance de proyecto para Claude Code;44herramientas stdio y cero llamadas proveedor; credenciales ignoradas, validez/cuota no comprobada.

Once controles adversariales e invariantes completos,39archivos propios intactos,225evidencias previas verificadas; harness693antes/despuÃ©s, NBA172. Fallos de configuraciÃ³n de temporales, acceso a ejecutables y serializaciÃ³n NaN conservados y corregidos. Sin entrenamiento, promociÃ³n de puertas o picks. NBA-RUN-037; docs/nba_github_scrapers_recuperacion_20261006.md.


Cierre de NBA-RUN-037: la salida de consola se escribiÃ³ despuÃ©s del hash de su archivo abierto. Se conserva el snapshot vacÃ­o exacto del checkpoint y toda la salida final en otro archivo cerrado, con recibo explÃ­cito console_finalization.json y evento artifact_finalization. Se verifican304evidencias/84eventos; no se modifica ninguna fila, rotaciÃ³n, registro de corrida o evidencia existente.

## 2026-10-06 â€” Goles desde API-Football: desplegado

Implementado con plan corto y subagentes (docs/superpowers/plans/
2026-10-06-goles-desde-api-football.md): `af_odds` quita el filtro `bet`
(misma peticiÃ³n) y guarda bet 5 â€” todas las lÃ­neas de Pinnacle y 1,5/2,5/
3,5/4,5 de las casas de la lista â€” con columna `line` e Ã­ndice Ãºnico NULLS
NOT DISTINCT (db/041, con guardia que aborta si queda el UNIQUE viejo, por
la revisiÃ³n final: con IF EXISTS un nombre mal escrito habrÃ­a tumbado toda la
captura en silencio). La lÃ­nea de alta probabilidad lee esos totales de la
MISMA respuesta que el 1X2 (`_totales_af`, con `fetched_at <= now`).

Despliegue 19:58 UTC en un minuto sin jobs ni partidos en 15 min: migraciÃ³n
y reinicio juntos (el cÃ³digo viejo no funciona con el esquema nuevo y no hay
vuelta atrÃ¡s salvo hacia delante: volver a pedir `bet=1` con el INSERT de 9
columnas). Dos pasadas manuales de `af_odds`: 1.622 filas nuevas en 41
partidos (15 s) y luego 0 (el 1X2 se sigue deduplicando). Vista previa con
la lÃ­nea encendida solo para ese proceso: 9 pronÃ³sticos de 15 partidos, 7 de
goles (casi todos "menos de 4,5", con referencia de Betano), antes 2.


## 2026-10-06 â€” NBA: ZenRows usado en trÃ¡fico real de fuentes

La instalaciÃ³n del MCP no redirigÃ­a los scrapers. Se autenticÃ³ account_usage y se probaron cuatro targets con mÃ¡ximo100crÃ©ditos: BasketballReference.cgi devuelveHTML vÃ¡lido/152filas y pasa parser upstream; CDN yPDF dan ZenRows422/RESP001,CDX agota110segundos. Consumo observado1de5000crÃ©ditos, sin compras. El adaptador nuevo enruta GET del scraper BRef a scrape del MCP y conserva HTML/recibo/hash; no se declara desbloqueo universal.

Memphisâ€“OKC0022200443 aÃ±ade23filas/22participantes/1DNP explÃ­cito,161569combinadas;6056regulares aceptados y94pendientes. Overlay declarado OKCreb54â†’53 corroborado por NBAStats actual y BRef, conservando el Parquet antiguo y umbrales.152acuerdos entre parsers,6controles adversariales,161546filas previas intactas,39archivos propios intactos,304evidencias previas verificadas; harness706antes/despuÃ©s. No se atribuye nueva ejecuciÃ³n a la suiteNBA172 anterior. NBA-RUN-038; docs/nba_zenrows_recuperacion_20261006.md.

## 2026-10-06 â€” LÃ­nea de alta probabilidad: fuera "menos de 4,5 goles"

DecisiÃ³n del usuario tras la vista previa con goles de API-Football: casi
todos los pronÃ³sticos de goles eran "menos de 4,5" (se paga a 1,09-1,17),
poco Ãºtil para el cliente. `MERCADOS_GOLES_HABILITADOS` queda en mÃ¡s de 1,5
y menos de 3,5 (commit 396af2c). PasÃ³ la prueba histÃ³rica: quitarla no exige
repetirla; volver a aÃ±adirla, sÃ­. API-Football sigue guardando la 4,5 de las
casas blandas (no cuesta peticiones) por si se reabre.


## 2026-10-06 â€” NBA: completar y validar histÃ³ricos (NBA-RUN-039)

BRef: 83 fechas por ZenRows recuperan 93 regulares; actas/calendario/ESPN completan cuatro pretemporadas. Resultado: 6149/6150 regulares, 71/71 pretemporadas, 164190 filas. Las fuentes de los 6150 regulares estÃ¡n capturadas. Tony Bradley (0:00 / 1 REB) estÃ¡ corroborado por PBP de 0,2 segundos y se conserva fuera del normalizador congelado, sin inventar segundos. Rotaciones: 6113/6150, 258137 tramos y 37 pendientes. Los 330 PDFs de 17:30 completan 816 fechas, 80932 filas y 70941 filas nominales con ID; 13 nombres originales y 19 nuevos resueltos con fuentes oficiales. No se acredita intradÃ­a total o recepciÃ³n pregame original. Props: +795 pares P/A (603/192), 3756 con rebotes; 500 crÃ©ditos locales agotados, cobertura de dos juegos P/A y veinte de rebotes. Se preservan 161569 filas y 5493 rotaciones previas, 39 archivos NBA y 340 evidencias. Harness: 706 antes/despuÃ©s; 21 controles adversariales. Los timeouts mantienen reserva por coste incierto; sin compras. Modelo y gates intactos. Informe: docs/nba_completar_validar_20261006.md.


## 2026-10-06 â€” NBA: segundos oficiales y rotaciones (NBA-RUN-040)

Se ampliÃ³ el contrato de minutos solo con fuentes GameRotation completas y hash externo, para permitir <=1s con reloj cero/estado vacÃ­o; PRA no infiere participaciÃ³n. Tony Bradley conserva 0:00 y 1REB, acredita0,2s y aÃ±ade su roster completo28filas:6150regulares/71pretemporadas/164218filas. La ruta por defecto coincide con el normalizador archivado en164190filas. Rotaciones:+28,6141/6150 y259416tramos; nueve casos mantienen contradicciones administrativas o titulares de OT sin prueba. V3actual17capturas requiriÃ³ adaptar el esquema nestedgame y reconocer actionId Ãºnico; actionNumber duplicado permanece. Alias de sustituciÃ³n solo mediante IDs explÃ­citos V2/V3 corroborados; sin override de titulares.245crÃ©ditos nuevos confirmados;riesgo1612/3200 con reservasinciertas, cero props/sincompras.189NBA/707harness; primerWinError5temporal preservado y repeticiÃ³n completa exitosa.2105evidencias previas verificadas,38archivos antiguos intactos e ingest original archivado; modelo/gates intactos. IntradÃ­a mÃ©dico/PIT y props multitemporada pendientes. Informe:docs/nba_segundos_y_rotaciones_20261006.md.


## 2026-10-06 â€” NBA: pendientes e intradÃ­a (NBA-RUN-041)

Se aceptaron seis rotaciones adicionales mediante intervalos administrativos de tiempo cero y exposiciÃ³n oficial de OT:6147/6150,259687tramos; tres contradicciones persisten. Descarga mÃ©dica:815/816cortes nuevos;1631versiones/165729filas,75451jugadores nuevos con ID. Se preservan continuaciones NOTYETSUBMITTED/filas nombradas, razones literales y diferencias upstream; once identidades exactas CuiYongxi se resuelven en una versiÃ³n separada.3859cambios de estado/motivo y1215selecciones retrospectivasT60;1216horarios Ãºnicos corroborados,40bÃºsquedas vacÃ­as separadas. RecepciÃ³n original/PIT no acreditados. Props3756previos/44snapshots revalidados,cero llamadas; repos fijados sin nuevas cuotas; plan36solicitudes/720crÃ©ditos sigue pendiente de autorizaciÃ³n por lÃ­mite500agotado.140ZenRowsconfirmados nuevos;riesgo1752/3200,sincompras.189NBA/707harness y controles auxiliares;2280evidencias/40corridas/gates/producciÃ³n previos preservados. Informe:docs/nba_pendientes_intradia_20261006.md.

CorrecciÃ³n de checklist NBA-RUN-041: el reintento del auxiliar de sellado marcÃ³ por error la lÃ­nea de pendientes como completada. Se restituyÃ³ la casilla abierta para las tres rotaciones, intradÃ­a/PIT y props; el informe, datasets y evidencias del checkpoint permanecen intactos. La instantÃ¡nea incorrecta se conserva y esta correcciÃ³n se registra aparte.

## 2026-10-07 â€” LÃ­nea de alta probabilidad activada y "marca el local / el visitante" desplegado

- Sellado del 7-oct (08:00 UTC) correcto con el bloque vacÃ­o (`n_alta_prob: 0`).
  La tarea programada de activaciÃ³n (08:30 UTC) se quedÃ³ esperando el
  permiso de su primer `Bash` (nadie lo aprobÃ³): se detuvo y la activaciÃ³n se
  hizo a mano tras repetir sus comprobaciones (verify 9 lotes, salud, tablas
  vacÃ­as, log del job). LecciÃ³n: una tarea programada que usa `ssh` necesita
  sus permisos aprobados de antemano ("Run now" en una prueba inocua).
- "Marca el local / el visitante" (mÃ¡s de 0,5 goles de un equipo), decisiÃ³n
  del usuario: probabilidad del mismo ajuste de goles (prueba histÃ³rica:
  local 86,97â†’88,52, visitante 86,10â†’87,45); cuota de referencia de las casas
  blandas desde API-Football bets 16/17 (con guarda por nombre); `db/042`
  amplÃ­a el CHECK con guardia. El control vigila los dos lados como UN grupo
  (`team_totals`), decisiÃ³n del usuario: en el Monte Carlo del revisor da
  menos pausas en falso y mÃ¡s detecciÃ³n que por separado.
- Tasas del control con mezcla realista y grupo fusionado: ~16 % de lÃ­neas
  con alguna pausa de grupo en falso, ~5 % de la lÃ­nea entera; detecciÃ³n de
  un dÃ©ficit de 3 pts ~82 % / ~73 %. Las cifras del 6-oct (9,7 % / 3 % /
  88 %) suponÃ­an probabilidades uniformes y 4 grupos.
- Despliegue 17:02 UTC: `db/042` + `ALTA_PROB_ENABLED=1` + reinicio en un
  minuto seguro. Vista previa: 10 pronÃ³sticos de 17 partidos (5 de equipo).
  Primeros pronÃ³sticos reales: sellado del 8-oct, 08:00 UTC.


## 2026-10-07 â€” NBA: archivo pÃºblico y rotaciones (NBA-RUN-042)

Las tres actas completas acreditan entrada/salida al mismo reloj detenido;6150/6150rotaciones y259826tramos, sin segundos positivos para actores administrativos. ArchivoKamran fijado/verificado:3662JSON,228324pares nuevos de puntos/3429partidos,232080pares combinados; horizontes6,07â€“16,79horas, noT60/T15. Calendarios ESPN2024/25verificados porasset/hash mÃ¡s2026sellado, roster/nombres/cronologÃ­a estrictos; rechazosconservados. MÃ©dico:223PDFs disponibles en240rutas/7fechas,13previos y210nuevos;1841versiones/186634filas,18750nominales nuevas conID,22CuiYongxi exactos. Control de motivo final limitado a pÃ¡gina deuna fila; diferencias literales de pÃ¡ginas normales conservadas. PrimerdÃ­a2023â€“24disponible desde17:30, compatible conconstanteupstream;16:30noacreditado, no se concluye bloqueoIP. RecepciÃ³noriginal/reglas de liquidaciÃ³n siguenpendientes.4939evidencias/41corridas/89eventosprevios preservados;189NBA,707harnessantes/732despuÃ©s portrabajo concurrente preservado.30ZenRowsnuevos,riesgo1782/3200,OddsAPI0nuevo/500agotado,sincompras;producciÃ³n/modelo/gatesintactos. Informe:docs/nba_props_y_rotaciones_20261007.md.

PresentaciÃ³n legible de NBA-RUN-042: docs/nba_resultados_validados_20261007.md. El informe tÃ©cnico/datasets sellados no se modifican; la casilla RUN-041 queda identificada como estado histÃ³rico, con pendientes actuales en RUN-042. RevisiÃ³n documental registrada aparte.

## 2026-10-07 â€” web: portada inspirada en TennisPredictions y paleta del usuario

Se conserva la jerarquÃ­a editorial/calendario/filtros/filas por competiciÃ³n de
la referencia pÃºblica, adaptada al criterio de QuantFut. SingleFile CLI 2.18.0
capturÃ³ el HTML con manifiesto en `.local/design-reference/`; no es dependencia
de la web ni reproduce el backend ajeno. El usuario aportÃ³ azul noche #0b132b,
pizarra #1c2541 y esmeralda #10b981: superficies y cabecera se armonizan con
esa paleta. El tablero continÃºa siendo demo identificada; agenda real y puerta
comercial permanecen separadas, con error de API visible. No se activÃ³ ninguna
publicaciÃ³n, cuenta ni pago ni se desplegÃ³. Nueve pruebas del frontend pasan;
732 pruebas Python pasaron antes de las ediciones de presentaciÃ³n. El script
shell no encontrÃ³ utilidades dentro del entorno restringido y su OK no se
considerÃ³ vÃ¡lido; se ejecutÃ³ la suite con el Python del proyecto. RevisiÃ³n en
navegador de filtros, fechas, fichas, Pick del dÃ­a y combinadas. Propuesta y
siguiente fase: `docs/web_diseno_tennispredictions_20261007.md`.
- Prueba histÃ³rica con la regla desplegada (firma d5cbc3151164): 9.021 de
  14.216 partidos (63 %), prometido 82,62 %, real 83,23 %; todos los mercados
  pasan (equipo local 86,97â†’88,52, visitante 86,10â†’87,45).

## 2026-10-07 â€” web: cuenta y modelo de paquetes/suscripciones

El usuario aclarÃ³ que Â«su modeloÂ» significa paquetes y suscripciones. Se
adaptaron las vistas de acceso, recuperaciÃ³n, registro, cuenta, catÃ¡logo de
picks y planes de 1/3/6 meses mÃ¡s Club de TennisPredictions. SingleFile guardÃ³
las pÃ¡ginas pÃºblicas; el acceso se capturÃ³ sin sesiÃ³n. El panel de referencia
se inspeccionÃ³ sin guardar ni incorporar su informaciÃ³n personal.

La selecciÃ³n de modalidad y el perfil son estado visual de la pestaÃ±a, no
autorizaciÃ³n de servidor. Identidad y contraseÃ±a son sintÃ©ticas, de solo
lectura; no se envÃ­an correos ni se crea una orden. Mi cuenta mantiene Â«Sin
suscripciÃ³n activaÂ» incluso despuÃ©s de revisar el pedido. Preferencias de
cuotas/ligas conservan la persistencia local existente; favoritos demo se
aÃ±aden y quitan durante la sesiÃ³n. El resumen conserva el cobro deshabilitado.
Los importes de referencia usan centavos enteros: equivalentes mensuales y
ahorros derivados del total, corrigiendo discrepancias visibles en la referencia.

13 pruebas frontend y 11 del servidor web aprobadas. ValidaciÃ³n en navegador
del recorrido de acceso â†’ pedido, recuperaciÃ³n sin correo, preferencias,
favoritos, ausencia de activaciÃ³n y vistas 320/390/768/1024/1440 px. Se corrigiÃ³
un desbordamiento de 4 px del catÃ¡logo a 320 px. El chequeo shell final volviÃ³
a omitir utilidades/Python en este entorno: su Â«OKÂ» no cuenta como validaciÃ³n;
las pruebas directas son la evidencia. Sin despliegue ni cambio de gates.
Propuesta: docs/modelo_paquetes_suscripciones_20261007.md; capturas propias en
la carpeta local ignorada `.local/design-reference/quantfut-{acceso,cuenta,suscripciones}.jpg`.

## 2026-10-07 â€” web: despliegue autorizado

Por peticiÃ³n explÃ­cita del usuario, commit de producto 2266311 creado localmente
y desplegado en pronosticosdeportivos.pro. Sin remoto Git configurado: transferencia
SSH de paquete generado desde el commit. Base de archivos cotejada antes de sustituir;
imagen derivada de la API ejecutÃ¡ndose, solo seis archivos de presentaciÃ³n/rutas.
Respaldo en /home/qf/web-release-2266311/backup e imagen previa conservada.
Solo API recreada; worker, DB, cachÃ©, proxy y Grafana conservan sus identificadores.
Gate, variables, modelo y base intactos; cuentas y cobros siguen en demo.

El arnÃ©s completo se ejecutÃ³ correctamente al fijar PATH de Git Bash: 732 pruebas
aprobadas, una advertencia; frontend 13 aprobadas. Salud origen/HTTPS status ok,
archivos cotejados por SHA-256; el HTML pÃºblico solo incorpora el beacon existente
de Cloudflare. Navegador pÃºblico comprobÃ³ acceso demo â†’ pedido bloqueado y cuenta
sin suscripciÃ³n activa. Registro: docs/web_despliegue_20261007.md.

## 2026-10-07 â€” Fase comercial desbloqueada: cuentas, API de clientes y panel

DecisiÃ³n del usuario: avanzar ya con cuentas y panel de administraciÃ³n sin
esperar a la puerta de CLV. La puerta sigue decidiendo si hay picks que
vender (`PUBLISH_PICKS_ENABLED`); las cuentas existen aunque estÃ© cerrada.

- Un solo FastAPI para web, app Flutter y panel (se mantiene la decisiÃ³n
  2026-09-23). `/app/v1` sin secretos en el cliente: bearer opaco de 15 min
  en Redis + refresh de 30 dÃ­as hasheado en Postgres y rotado en cada uso;
  el reuso de un refresh revoca la sesiÃ³n (robo de token). Opaco y no JWT:
  suspender o cerrar sesiones corta en el acto y no hace falta PyJWT.
- `ACCOUNTS_ENABLED` apagado por defecto: desplegar no abre altas solo.
- `subscriptions` solo admite revocar una vez (trigger); `admin_audit`
  inmutable con `deny_mutation()`. Una concesiÃ³n manual no es ingreso: los
  ingresos del dashboard solo cuentan `source='payment'`.
- Panel: Tabler + Tabler Icons + Chart.js vendorizados (MIT, versiones y
  SHA en `static/vendor/README.md`) para mantener CSP `'self'` sin
  `unsafe-inline`. Se descartaron SQLAdmin/starlette-admin (exigen ORM y
  chocan con los triggers) y react-admin/refine (build de Node y tokens en
  JS). El pipeline sigue siendo de solo lectura desde el panel.
- Trampa encontrada: `main.py` manda `Referrer-Policy: no-referrer`, y con
  eso Chrome envÃ­a `Origin: null` en los POST propios; la defensa CSRF se
  apoya en `Sec-Fetch-Site` + token HMAC, no en `Origin`.
- El tope de 10/min de `/control` se subiÃ³ a 2Ã— el general y cubre tambiÃ©n
  `/static`: con varias pÃ¡ginas daba 429 navegando normalmente.
- Verificado: 753 tests + 6 de integraciÃ³n contra un Postgres 16 desechable
  con todo `db/*.sql` (rotaciÃ³n/reuso, suspensiÃ³n, renovaciÃ³n sin perder
  dÃ­as, de por vida, revocaciÃ³n Ãºnica); flujo HTTP completo y panel en
  navegador. Sin despliegue: falta aplicar `db/043`, `pip install` y
  `ACCOUNTS_ENABLED=1` en el VPS.
- Pendiente de decisiÃ³n del usuario: procesador de pago y proveedor de
  correo. GuÃ­a de la app: `docs/app_api_flutter.md`.


## 2026-10-07 â€” NBA: calendario completo y recuperaciÃ³n mÃ©dica (NBA-RUN-043)

Horarios corroborados para 6150 regulares, incluidos diez neutrales con ambas referencias NBA @ y designaciÃ³n ESPN conservada. +2784 reportes/368902 filas; 6129/6150 selecciones mÃ©dicas retrospectivas con reloj/contexto literal concordante, 6037 ambos equipos enviados. +1350 puntos mediante seis alias oficiales exactos/308 partidos, total233430; 27151 candidatos multimerkado/34 partidos separados por relojes libro/mercado y vecinos ausentes. Cinco repos pÃºblicos fijados/blobs verificados,97 PDFs archivados, cero llamadas pagadas nuevas; presupuesto previo sin aumento. 9641 evidencias/42 corridas/91 eventos conservados; arnÃ©s732/732; producciÃ³nNBA/modelo/gates sin cambios, trabajo concurrente preservado. RecepciÃ³n original/settlement y demÃ¡s huecos siguen pendientes. Informe:docs/nba_recuperacion_medica_y_props_20261007.md.

## 2026-10-07 â€” Correo transaccional con Proton Mail

DecisiÃ³n del usuario: Proton Mail. Hay dos formas y el cÃ³digo es el mismo
(SMTP genÃ©rico en `comercial/correo.py`); solo cambia `.env`:
- Recomendada: envÃ­o SMTP oficial de Proton (`smtp.protonmail.ch:587`,
  STARTTLS, token SMTP). Exige plan de pago y dominio propio en Proton; no
  aÃ±ade servicios que mantener.
- Alternativa: Proton Mail Bridge en Compose (perfil `proton-bridge`) con
  shenxn/protonmail-bridge-docker. Su imagen de Docker Hub estÃ¡ parada en la
  3.19 (abr-2025) aunque el repo sigue (v3.27): se compila desde un commit
  fijo con el bridge v3.27.1. El login es interactivo (2FA): lo hace el
  usuario en el VPS.
- Proton no es para envÃ­os masivos y limita por reputaciÃ³n: aquÃ­ solo
  salen correos uno a uno disparados por el cliente.
- Los enlaces solo guardan sha256; GET nunca consume el token (los filtros
  de correo visitan enlaces), solo el POST del botÃ³n. `forgot` responde 202
  siempre y envÃ­a en segundo plano. Restablecer cierra todas las sesiones.
- Verificado con un servidor SMTP real en local (aiosmtpd con STARTTLS y
  certificado autofirmado): llega autenticado y cifrado, con verificaciÃ³n
  estricta se rechaza el autofirmado y una contraseÃ±a mala no envÃ­a.
  Flujo completo en navegador: enlace â†’ nueva contraseÃ±a â†’ login.


## 2026-10-07 â€” NBA: veinte relojes corroborados (NBA-RUN-044)

+20 selecciones retrospectivas con PDF ET y metadata BRef de fecha/equipos/reloj exactos; corte60min antes del reloj mÃ¡s temprano; ESPN12â€“50min mÃ¡s tarde se conserva sin atribuir causa. Total6149/6150, ambos enviados6056, algÃºn equipo ausente93. BOS@NYK25oct2023 ausente en diez PDFs inspeccionados; no se infiere sano/enviado. +3 reportes/167 filas, total4628/555703; dos parsers y todos los nombres conID. 22tareasZenRows/200crÃ©ditos, riesgo1982/3200;3GETPDFsinpago;OddsAPI0. 18952evidencias/43corridas/92eventos previos preservados; arnÃ©s753/764; producciÃ³n/modelos/gates intactos. CorrecciÃ³n v2 de atribuciÃ³n de zona: ET lo declara PDF, no metadataBRef. docs/nba_horarios_medicos_corroborados_20261007.md.

## 2026-10-07 â€” Despliegue de la fase comercial (commit 3d40e05)

Autorizado por el usuario. Paquete `git archive` verificado por SHA-256;
base del servidor cotejada con HEAD antes de sustituir. Respaldo en
`~/release-3d40e05/backup.tgz`, imagen previa `quantfut-api:before-3d40e05`.
Imagen nueva derivada de la que corrÃ­a (+argon2-cffi, jinja2, src/), solo
`api` recreado con `--no-deps --no-build`; worker, db, cachÃ© y proxy
intactos. `ACCOUNTS_ENABLED=0`: `/app/v1` responde 503 hasta abrir altas.
El token SMTP lo escribiÃ³ el usuario con un script de entrada oculta
(`~/release-3d40e05/poner_token.sh`): nunca pasÃ³ por el agente. Login SMTP
con Proton verificado sin enviar correo.
Hallazgo: `ADMIN_CONSOLE_PASSWORD_HASH` ya estaba vacÃ­o en `.env` antes del
despliegue (en `.env.bak-2026-10-07` de las 19:45 sÃ­ estaba): `/control`
devuelve 503. No se restaurÃ³ sin permiso del usuario.
ReversiÃ³n: retag `quantfut-api:before-3d40e05` â†’ `latest`, restaurar
`backup.tgz` y recrear `api`; las tablas nuevas no afectan al cÃ³digo previo.
Con permiso del usuario se restaurÃ³ la lÃ­nea del hash desde
`.env.bak-2026-10-07` (idÃ©ntica byte a byte; resto del `.env` sin cambios,
copia previa en `~/release-3d40e05/env.antes-restaurar-hash`). `/control`:
401 en origen sin credenciales y 302 a Cloudflare Access desde fuera.
LecciÃ³n: al reescribir `.env` en un despliegue, comparar despuÃ©s las claves
contra la copia previa; un valor vacÃ­o no da error, solo un 503 del panel.
Altas abiertas (`ACCOUNTS_ENABLED=1`) por decisiÃ³n del usuario. Verificado
en producciÃ³n sin crear cuentas ni enviar correos: planes 200 (tambiÃ©n
desde el dominio pÃºblico), login inexistente 401, olvido 202, picks sin
sesiÃ³n 401, `/cuenta` con token falso 400, panel 401. Trampa del script de
despliegue: `diff` sale con 1 si hay cambios y `set -e` cortÃ³ antes de
recrear la API; comprobar siempre que el servicio se recreÃ³.

## 2026-10-07 â€” NBA: props y reglas MÃ©xico/LATAM (NBA-RUN-045)

+9702pares de puntos/145partidos por uniÃ³n Ãºnica fecha/equipos con calendario NBA/ESPN y box canÃ³nico; mapas originales errÃ³neos conservados,21eventos sin resolver. Total243132 (239979PTS/2961REB/192AST);233430previos exactos,27151candidatos aparte. 14blobs de dos repos extra;78tarjetas sin relojes completos,0pares adoptados de esos dos. Cinco documentos oficiales/cuatrocasas/MX-CO-PE; vigencia histÃ³rica desconocida y sin coincidencia con11books de cuotas. RecepciÃ³n243132cuotas/4628PDFs todaOct2026,0pruebas originales; estructuraycontratocandidate confixtures explÃ­citos sintÃ©ticos,ninguna liquidaciÃ³n automÃ¡tica.31GETintentados,0OddsAPI/0ZenRows/cero compras;riesgo1982/3200.19062evidencias/44corridas/93eventos previos preservados,21controles y arnÃ©s764/764;producciÃ³n/modelos/gates sin cambios. docs/nba_props_y_reglas_latam_20261007.md.

## 2026-10-07 â€” NBA: versiones archivadas y mecÃ¡nica de liquidaciÃ³n (NBA-RUN-046)

Seis capturas realesCaliente2025/Betway2021â€“2024 con SHA1CDXbase32exacto y Memento concordante; cinco secciones histÃ³ricas Betway y secciÃ³nCaliente iguales a actuales, sin inferir vigencia continua. +perfilBetwayMX,total5perfiles;8documentosreglas nuevos/1ayuda. CodereARredirigeMÃ©xico, cuarentena. Usuario confirma sinlogs originales;4978artefactos pornombre no prueban recepciÃ³n antigua. Evaluador localv3 con38controles sintÃ©ticos yrecibosactuales exclusivos;243132pares todos pendientes,0liquidacionesreales/0ROI.19165evidencias/45corridas/94eventos previos verificados; arnÃ©s764/764.28intentosGET,0Odds/0ZenRows,riesgo1982/3200;sin compras. ProducciÃ³n/gates/modelos intactos;intermediosfallidos conservados. docs/nba_reglas_archivadas_y_liquidacion_20261007.md.


## 2026-10-07 â€” NBA: correcciÃ³n documental del arnÃ©s (NBA-RUN-047)

El informe RUN-046 y su nota de progreso conservaban el recuento anterior764/764. Log final y verificaciÃ³n sellados acreditan764antes/767despuÃ©s,9omisionesantes/10despuÃ©s. VersiÃ³nv2 del informe corrige el texto; documentos/evidencias/corridas previos Ã­ntegros.0capturas/0crÃ©ditos/0cambiosdataset oproducciÃ³n/gates. docs/nba_reglas_archivadas_y_liquidacion_v2_20261007.md.

## 2026-10-07 â€” Web conectada a las cuentas reales

La web deja la sesiÃ³n demo y usa `/app/v1` con `frontend/cuenta-api.js`.
Decisiones: en el navegador el refresh vive en una cookie HttpOnly
(SameSite=Strict, `Path=/app/v1/auth`) y el acceso solo en memoria; nada en
localStorage, para que un XSS no se lleve una sesiÃ³n de 30 dÃ­as. La cabecera
`X-QF-Client: web` activa ese modo y fuerza preflight CORS desde otro origen,
asÃ­ que la cookie no sirve fuera del dominio. Dos pestaÃ±as que arrancan a la
vez mandan la misma cookie: la segunda tenÃ­a el refresh reciÃ©n rotado y la
detecciÃ³n de reuso habrÃ­a revocado la sesiÃ³n; se da una gracia de 20 s solo
en modo web (la app serializa sus refresh y no la necesita). Un indicador
`qf_hay_sesion=1` sin secreto evita un refresh 401 por cada visitante.
Verificado en navegador contra el FastAPI completo en local: registro, error
de login, login, recarga con sesiÃ³n recuperada, plan concedido visible como
Plus y cierre de sesiÃ³n que borra ambas cookies.

## 2026-10-07 â€” Despliegue de la web con cuentas reales (commit 9b9d180)

Autorizado por el usuario. Solo los 8 archivos de ejecuciÃ³n (5 del frontend,
3 de la API); `ACCESS_FLOW.md`, `package.json` y `server.mjs` del servidor
difieren del repo pero no se sirven y no se tocaron. Base cotejada contra
3d40e05, paquete verificado por SHA-256, respaldo en
`~/release-9b9d180/backup.tgz`, imagen previa `quantfut-api:before-9b9d180`;
solo `api` recreado. Los archivos pÃºblicos (tambiÃ©n a travÃ©s de Cloudflare)
coinciden byte a byte con el commit. En producciÃ³n el acceso muestra el
formulario real, sin aviso demo, sin errores de consola y sin refresh para
visitantes anÃ³nimos. No se creÃ³ ninguna cuenta en producciÃ³n.

## 2026-10-07 â€” La web lee los precios del panel

`MEMBERSHIP_PLANS` (precios fijos en JS) desaparece: importes, duraciÃ³n,
moneda y quÃ© planes se venden salen de `/app/v1/plans`, que es lo que edita
el panel. En el cÃ³digo solo quedan los textos por `plan_code`; un plan nuevo
sin texto usa el nombre del panel. El ahorro se calcula contra el plan
mensual de la misma lista y, si no se vende, no se inventa. `/plans` pasa a
un router pÃºblico sin `ACCOUNTS_ENABLED`: los precios son informaciÃ³n
pÃºblica y la web no debe romperse si se cierran las altas. Sin precios
cargados la web dice Â«CargandoÂ»/Â«ReintentarÂ» en vez de enseÃ±ar importes
viejos. Verificado en local: cambiar 3 meses a 29,99 en el panel se ve en
la web al recargar ($10.00/mes, ahorro $14.98) y Club, desactivado, no sale.

## 2026-10-07 â€” Despliegue de precios desde el panel (commit f94a5bc)

Autorizado por el usuario. 6 archivos de ejecuciÃ³n, base cotejada contra
9b9d180, paquete verificado por SHA-256, respaldo en
`~/release-f94a5bc/backup.tgz`, imagen previa `quantfut-api:before-f94a5bc`;
solo `api` recreado. En producciÃ³n `#planes` muestra los 3 planes activos
del panel (14,99 / 33,99 / 53,99 USD) sin errores de consola. Ojo: Cloudflare
sigue sirviendo `/app.js` sin versiÃ³n desde cachÃ©; la portada pide
`app.js?v=â€¦` y esa URL sÃ­ es la nueva: por eso las versiones `?v=` deben
recalcularse siempre que cambie un archivo.


## 2026-10-07 â€” NBA: todas las casas solicitadas (NBA-RUN-048)

RevisiÃ³n de 22 combinaciones casa/paÃ­s mÃ¡s Rushbet MÃ©xico: 25 perfiles, cinco anteriores preservados y veinte nuevos, 72 clÃ¡usulas (49 nuevas). La matriz distingue clÃ¡usulas recuperadas/observadas de pÃ¡ginas vacÃ­as, redirecciones, contenido educativo, PDF fÃ­sico de Te Apuesto y proveedor Kambi sin vÃ­nculo contractual probado por Luckia. Sportium EspaÃ±a exige un segundo; bwin separa simples/Build a Bet; Winamax tiene excepciÃ³n limitada de logros para titular con menos de doce minutos. Son perfiles de investigaciÃ³n, no liquidaciones reales.

21 Ã­ndices consultados, cinco JSON vÃ¡lidos y nueve entradas histÃ³ricas; nueve replays fallaron por conexiÃ³n, cero contenido archivado nuevo validado. Se preservan los seis replays RUN-046. 87 GET del colector, 98 transacciones registradas y un diagnÃ³stico adicional; cero crÃ©ditos pagados/purchases. 19.260 evidencias y 47 corridas previas verificadas; seis controles negativos de procedencia. ArnÃ©s 767 antes/768 despuÃ©s, diez omisiones ambas; incremento concurrente sin atribuirlo al catÃ¡logo. ProducciÃ³n NBA/datasets/gates intactos. Recibos originales y contratos por ticket ausentes; las 243.132 parejas siguen sin liquidaciÃ³n real. docs/nba_casas_hispanohablantes_reglas_20261007.md.


## 2026-10-07 â€” NBA: reglas Colombia y props pÃºblicos (NBA-RUN-049)

BetPlay recuperado mediante desplegables DOM; Sportium Colombia mediante ZenRows MCP.18 clÃ¡usulas en dos revisiones;25 perfiles/72 clÃ¡usulas anteriores Ã­ntegros. ParticipaciÃ³n BetPlay con frase imprecisa y suspensiÃ³n con ancla ambigua, Sportium43 minutos/abandono sin precedencia resuelta. No transferir mÃ­nimo espaÃ±ol de un segundo ni push de totales a jugador. Inkabet/Betsson PerÃº tienen enlaces oficiales/footer peruano, pero rutas devolvieron landings; Apuesta Total sin cuerpo de reglamento y Dorado general.

Dos repos fijados,19 blobs verificados y26 GET GitHub:77 filas PTS30/REB29/AST18 en cuarentena separada,17 cruzan casas y faltan relojes del proveedor; commits del archivo constan en febrero12. Otro repo publica agregados/sintÃ©ticos, no cuotas.0 parejas nuevas,0 liquidaciones,0 contratos/recibos histÃ³ricos acreditados. Diez scrapes MCP; reserva250, cota2232/3200; cuenta1674â†’1804, delta130 sin atribuciÃ³n exclusiva por peticiÃ³n. Salto35 activa parada; sin compras ni OddsAPI nuevo.48 corridas/19636 evidencias/97 eventos previos Ã­ntegros; ocho controles negativos; arnÃ©s768/10 antes y despuÃ©s. ProducciÃ³n NBA y gates intactos. docs/nba_reglas_colombia_y_props_candidatos_20261007.md.


## 2026-10-07 â€” NBA: minutos de regulaciÃ³n y F4 (NBA-RUN-050)

Continuar F4 como investigaciÃ³n: el candidato reciente mejora CRPS3,6638â†’3,5479 y MAE4,9654â†’4,8694 minutos en63155 casos/3256 juegos/433 fechas, tres temporadas y nueve bloques. La cobertura nominal80 solo llega70,663%, no hay disponibilidad previa ni coherencia conjunta de equipo; no promover ni aprobar G4. Historial mÃ­nimo10 positivo de la misma temporada, exclusiÃ³n estricta de toda fecha objetivo. Intervalos exploratorios por fecha, sin test confirmatorio intacto.

159075 etiquetas desde6150 partidos/259826 tramos,12300 totales equipo de240 minutos. Periodos1â€“4 separados de OT, ceros/DNP y archivos originales intactos. Primer intento rechazado por28 namespaces vacÃ­os de0022400942 antes de mÃ©tricas; capa derivada acredita roster/persona/equipo/estadÃ­sticas/estado completos contra NBA V3 archivado. Protocolos99/100 y fuentes previas preservados.

213 pruebas NBA,24 nuevas; arnÃ©s768/10 antes/despuÃ©s. RevisiÃ³n independiente de fÃ³rmula de126310 CRPS e historiales63155, resÃºmenes/bootstrap reproducidos; revisiÃ³n humana propia.49 corridas/19744 evidencias anteriores Ã­ntegras, prefijo98 eventos conservado, checkpoint101. Cero llamadas/purchases nuevas; ZenRows2232/3200 y243132 parejas de cuotas preservados. Sin recibos originales, liquidaciones, despliegue ni promociÃ³n de gates. Seguir disponibilidad/rol jerÃ¡rquico y rotaciones conjuntas antes de F5; pendientes LATAM/REB/AST/reglas por ticket continÃºan. docs/nba_f4_minutos_regulacion_20261007.md.


## 2026-10-07 â€” NBA: cobertura y escenarios, continuidad F5 (NBA-RUN-051)

Se corrige cobertura nominal80:70,663%â†’80,537% posterior y80,534% validaciÃ³n. Ajuste1,25 global/1,30 historial<12, entrenado exclusivamente en20630 casos2021-22 y congelado antes de validar2022-23/evaluar2023-26. CRPS empeora3,5479â†’3,5782 y MAE4,8694â†’4,8873; conservar RUN050 como referencia principal, no promover el ajuste por cobertura secundaria. HistÃ³rico ya inspeccionado, sin confirmaciÃ³n intacta.

3246 escenarios completos de equipo/415488 realizaciones conservan240 minutos, soporte0â€“48 y DNP0.4134 equipos excluidos por historial incompleto. Disponibilidad observada despuÃ©s del evento solo como diagnÃ³stico oracle, no como predicciÃ³n. Restricciones inviables/IDs/equipos cruzados se rechazan.234 pruebas NBA,21 nuevas; arnÃ©s768/10 antes y despuÃ©s.84002 pronÃ³sticos revisados,168004 CRPS independientes, nueve matrices regeneradas con hash exacto.

50 corridas/19786 evidencias y prefijo101 eventos intactos; protocolos102/103, checkpoint104.0 APIs/compras; ZenRows2232/3200, cuotas/contratos/recepciÃ³n original y gates preservados. Traspaso F5 de investigaciÃ³n con rutas/hashes y referencia anterior; noOT mientras las estadÃ­sticas por periodo no estÃ©n verificadas. F4 de disponibilidad/rol y dependencia conjunta sigue pendiente; no producciÃ³n. docs/nba_f4_calibracion_y_coherencia_20261007.md.


## 2026-10-07 â€” NBA: distribuciÃ³n de rebotes F5 (NBA-RUN-052)

negative_binomial elegida solo en19315 casos de validaciÃ³n2022-23 tras ajustar dispersiÃ³n con19513 de2021-22. ParÃ¡metros/elecciÃ³n congelados antes de59816 casos2023-26. CRPS1.376733â†’1.332904, MAE1.944846â†’1.911748. Candidato de investigaciÃ³n favorable al baseline en este replay; sin promociÃ³n ni confirmaciÃ³n intacta.

6150 juegos/159075 etiquetas preservadas,5840 sinOT,310 OT excluidos por falta de estadÃ­sticas de regulaciÃ³n;98644 features causales, sin resultados del dÃ­a objetivo. Prior30 minutos a0,18 heredado; historia20/min10 positiva sinOT para tasa, minutos RUN050 para distribuciÃ³n. DiagnÃ³stico ampliado RUN051 separado; no escenarios oracle en mÃ©tricas predictivas. Probabilidades under/push/over son categorÃ­as matemÃ¡ticas sin contrato ni void conocido. PIT aleatorizado y masa discreta evitan confundir cobertura central con80 exacto.

Primer intento105 fallÃ³ al serializar bool NumPy antes de validaciÃ³n; fuentes conservadas, entradas reutilizadas con hashes y AST iguales. Canon106/ajuste107/selecciÃ³n108/checkpoint109.265 pruebas NBA,31 nuevas; arnÃ©s768/10 antes/despuÃ©s.98644 historias,179448 PMFs/CRPS independientes y27 distribuciones regeneradas.51 corridas/19819 evidencias previas intactas.0 APIs/compras, ZenRows2232/3200; recepciÃ³n/contratos/cuotas/gates sin cambios. F6 de investigaciÃ³n preparado con hashes, no producciÃ³n. docs/nba_f5_distribucion_rebotes_20261007.md.


## 2026-10-07 â€” NBA: ensayos de entrega F6 (NBA-RUN-053)

El plan define F6 como entrega/observaciÃ³n, no solo auditorÃ­a temporal. Recuperar reclamaciones interrumpidas Ãºnicamente tras caducar a unknown, sin volver a cola; conservar sending fresco y reclamar antes del transporte. Hora real de intento separada del as_of solicitado y nueva comprobaciÃ³n de caducidad antes del remitente. Reinicios, concurrencia, auditorÃ­a fallida, 429 y timeout verificados sin duplicados.

Diez fixtures/60 cortes a0/15/30/60/120/300s, cinco outboxes y26 pruebas nuevas;291NBA y768general/10omisiones. Revisiones se seleccionan por recepciÃ³n propia, otro operador no sustituye contrato y error/suspensiÃ³n no reutiliza cuota anterior; diferencias son brackets de observaciones, no duraciÃ³n exacta ni ejecuciÃ³n real. Solo remitentes inyectados;0mensajes/APIs/compras. Latencia local simulada no demuestra p95 del canal.

52corridas/19873evidencias/109eventos previos Ã­ntegros; protocolo110/checkpoint111. Sin credenciales NBA ni campos del puente operativo, herramientas Postgres/Docker ausentes en PATH y ninguna integraciÃ³n DB probada. SQLite local no apruebaF6.1. PropuestaF7 draft_not_started: selecciÃ³n histÃ³rica participante positivo/noOT no es universo previo. Postgres/canal/recepciÃ³n anclada/contratos/OT y disponibilidad reales pendientes. Gates/cuotas/reglas/budget2232/3200 y producciÃ³n sin cambios. docs/nba_f6_entrega_y_observaciones_20261007.md.


## 2026-10-08 â€” NBA: Postgres durable local (NBA-RUN-054)

PostgreSQL16.15 existÃ­a fuera del PATH. ClÃºster NBA propio127.0.0.1:55434/base nba_delivery_run54, SCRAM/secretos privados y trabajador limitado; fÃºtbol intacto. Sellado+cola, reclamaciÃ³n+intento y resultado+evento atÃ³micos. Concurrencia/rollback/inmutabilidad/expiraciÃ³n/resultado incierto verificados.39eventos/19mensajes exportados; parada inmediata real y recuperaciÃ³n WAL preservaron queued/sent/sending y cadena; ninguna repeticiÃ³n ciega. ClÃºster detenido.

309NBA/18nuevas,768general/10omisiones;11controles adicionales propietario. Pipe Windows inicial corregido antes del protocolo112; expectativa de QA sobre TRUNCATE corregida y primer intento conservado, sin cambiar cÃ³digo/protocolo congelados.53corridas/19920evidencias/111eventos Ã­ntegros, checkpoint113.0APIs de datos/compras/mensajes; transporte en memoria. ImplementaciÃ³n Postgres local probada, no canal/latencia/cuotas/backup/rendimiento productivo. G6/F7 y gates pendientes, ZenRows2232/3200 intacto. docs/nba_f6_postgres_durable_20261008.md.


## 2026-10-08 â€” NBA: backup y canal VPS (NBA-RUN-055)

Usuario indicÃ³ credenciales en VPS y usar las de fÃºtbol. Solo TG_BOT_TOKEN/TG_ALERT_CHAT se leen allÃ­, sin copia local ni cambios del entorno/servicios de fÃºtbol. Un mensaje PRUEBA TÃ‰CNICA NBA aceptado por Telegram: message_id6 y chat configurado coincide; repeticiÃ³n del mismo ID bloqueada.14.625006s selladoâ†’acuse local incluyendo SSH, n1; no cumple ni demuestra p95<2s y recepciÃ³n en dispositivo desconocida.

pg_dump/pg_restore reales en base nueva:39eventos/19mensajes idÃ©nticos a fuente; fuente intacta despuÃ©s, restaurada75eventos/36mensajes tras tests/envÃ­o.330NBA/21nuevas,768general/10omisiones. MÃ©tricas conservan faltantes/anomalÃ­as y ledger vÃ¡lido. Roles preexistentes; no recuperaciÃ³n integral en otro servidor ni retenciÃ³n automÃ¡tica. Servidor de ensayo detenido.

Protocolo114/primer intento conservado: Python3.10 del VPS no importa datetime.UTC; falla antes de credenciales/HTTP, estado unknown sin reintento automÃ¡tico. DiagnÃ³stico de solo lectura acreditÃ³ causa; timezone.utc compatible y nuevo protocolo115 antes del Ãºnico POST.54corridas/19962evidencias/113eventos Ã­ntegros, checkpoint116.1mensaje real autorizado,0APIs de datos pagadas/compras; cota2232/3200 intacta. G6/cuotas/recepciÃ³n externa/OT/disponibilidad/F7 y producciÃ³n pendientes. docs/nba_f6_backup_y_canal_vps_20261008.md.


## 2026-10-08 â€” NBA: transporte y recuperaciÃ³n VPS (NBA-RUN-056)

Reutilizar SSH solo no bastÃ³: tres acuses7,75â€“10,75s. DiagnÃ³stico pÃºblicoHTTPS0,262/0,016s precediÃ³ transporte HTTPSConnection reutilizable; dos acuses locales desde sellado0,421309/0,484205s, arranque separado4,312s. Cinco mensajes tÃ©cnicos totalesIDs7â€“11, destino autorizado coincide y cada repeticiÃ³n bloqueada. Muestras diagnÃ³sticasn3/n2, no p95 operativo ni recepciÃ³n en dispositivo. Credenciales solo enVPS, fÃºtbol intacto.

Respaldo congeladoRUN055 del ledger/outbox39eventos19mensajes restaurado en contenedor propioVPSPostgres16.15/rednone/sinpuertos; roles recreados sin contraseÃ±as previas, seis mutaciones rechazadas y reinicio idÃ©ntico. TrabajadorNOLOGIN para SET ROLE, no pruebaSCRAMremota. Contenedor eliminado tras verificar etiqueta/imagen; copia600/carpeta700 retenida fuera del equipo. No backup integral histÃ³rico ni Ãºltimasalertas ni automatizaciÃ³n/retenciÃ³n periÃ³dica.

Colector de cuerpo/hash/recibo propio y controles de contrato preparado. MarcadorNBA403local, marcador/calendario403VPS; tres cuerpos conservados, cero datos/contratos nuevos. Ecosacotan relojVPSâˆ’localâˆ’0,902â€¦âˆ’0,725s pese aNTPVPSyes, sin cambios de reloj; mÃ©tricaslocales no restan UTCentrehosts. F7propuesta actualizada, no iniciada: universo/lesiones/rol/OT/contratos/anclaje/relojes/operaciÃ³n pendientes.

Primerintento117:352pasan/1PermissionErrorenmanifiestotemporal antes de accionesexternas; pruebaaislada pasa sincambiocÃ³digo. VersiÃ³n118base/carpeta nuevas353pasan; diagnÃ³stico119,HTTPS120 con356pasan, capturas121/relojes122,checkpoint123. ArnÃ©s768/10antes/final.55corridas/20038evidencias/116eventos anteriores conservados; revisiÃ³nmismaautor con scriptseparado.0APIsdatos pagadas/compras,5POSTTelegram tÃ©cnicos, cota2232/3200 y todosgates/producciÃ³n intactos. docs/nba_f6_transporte_y_recuperacion_vps_20261008.md.


## 2026-10-08 â€” NBA: captura anclada y operaciÃ³n de investigaciÃ³n (NBA-RUN-057)

Se recuperaron seis eventos de pretemporada, doce rosters con 247 jugadores/240 IDs NBA estables, 101 observaciones de lesiones y 14 precios pÃºblicos de Caliente MÃ©xico. Cruce previo de nombre/DOB acredita identidad estable, no equipo actual. Lesiones genÃ©ricas/Active no acreditan disponibilidad por partido; precios de equipo sin props individuales, reloj de proveedor o reglas completas. NBA jugadores403; pÃ¡ginas NBA200 sin calendario/quintetos en datos incrustados; Codere redirecciÃ³n detenida; ruta candidata BetPlay URLError, cero contratos aceptados.

DigiCert RFC3161 verificÃ³ nonce, contenido y cadena para manifiesto de 25 recibos nuevos/prefijo130 a17:39:29UTC y primer manifiesto VPS15recibos a17:52:14UTC. Contenido alterado/nonce distinto rechazados; prueba VPS revalidada localmente. Existencia nueva, no recibos histÃ³ricos ni exactitud del proveedor ni revocaciÃ³n OCSP/CRL. Consulta BetPlay posterior no anclada; checkpoint final tampoco.

Colector pÃºblico nuevo en VPS, usuario1001/red propia/raÃ­z read-only/sinpuertos/cap-dropALL/no-new-privileges, CPU0,25/128MiB/64pids; imagen base fijada por digest. Ciclo15min; lesiones/rosters por hora; sello mÃ¡ximo diario sin reintento inmediato. Primer intento de activaciÃ³n se detuvo ante Caliente403: catorce ESPN200 vÃ¡lidos. Segundo protocolo activÃ³ mismo cÃ³digo con salud source_degraded explÃ­cita; reinicio preservÃ³ capturas y seis servicios existentes conservan identidad. Sin secretos de fÃºtbol, mensajes o picks.

Respaldo consistente de ledger/cuerpos diario y mÃ¡ximo siete archivos generados verificados; no borra cuerpos originales. Pausa a16GiBpropios o menos de10GiB libres. Primer archivo restaurado localmente con15eventos y cuerpos idÃ©nticos; 12archivos copiados incluyendo pruebas temporales. Copia fuera del VPS puntual, no periÃ³dica; archivos diarios aÃºn no incluyen sellos/modelos/cola completa.

Dos fallos de normalizaciÃ³n preservados, luego corregidos por IDs desde enlaces y alias de etiquetas sin aceptar precios contradictorios. Tres pruebas de respaldo fallaron por handles SQLite abiertos enWindows, corregidos con cierre explÃ­cito:31casos pasan y tres controles operativos adicionales pasan. Dos reconstrucciones iniciales fallaron por suponer orden de respuestas paralelas; revisiÃ³n correcta usa hashes de evento y pasa sin modificar los datos. Suite completa390sinomisiones conPostgresNBA nuevo; source39eventos/19mensajes intacto y clÃºster detenido. ArnÃ©s768/10antes/final.56corridas/20143evidencias/123eventos anteriores preservados; revisiÃ³n misma autorÃ­a/scriptseparado.

Protocolos124â€“133, checkpoint134; 26intentos pÃºblicos locales y15primerVPS, dos solicitudes TSA gratuitas, cero APIdeportiva pagada/mensajes/compras, cota2232/3200sin cambios. Captura de investigaciÃ³n continua activa; G0â€“G9/alcance/decisiones y producciÃ³n comercial intactos. F7 sin iniciar por contratos/universo/rol/OT y criterios finales. docs/nba_f6_captura_anclada_y_operacion_20261008.md.


## 2026-10-08 â€” NBA: partido completo y contexto oficial (NBA-RUN-058)

Nuevas copias periÃ³dicas excluidas por instrucciÃ³n expresa; servicio anterior sin cambios.35capturas gratuitas:12perfiles oficiales NBA2026-27 con249listados y245/247identidades ESPN corroboradas por nombre/team/DOB, cincoIDsNBA nuevos. Tres alias generacionales Ãºnicos aceptados; MaliqBrown/SteveSettleIII desconocidos. Listado no acredita contrato/convocatoria.34lesiones en contexto de seis eventos, cero disponibilidad final/rol; cruce oficial BOS-CLE0012600011/401898392 a23UTC. Ruta candidata reporte404 y redirecciÃ³n de roster detenida no prueban ausencia global.

Protocolo fullgame previo a mÃ©tricas:159075etiquetas/6150partidos/310OT;104645antecedentes causales;84015casos evaluados/4343partidos/3842observaciones OT. Gamma-Poisson con minutos histÃ³ricos completos, prior heredado fijo y familia sin selecciÃ³n actual. CRPS1,361001 contra1,390279;delta-0,029277/IC95porfecha[-0,032610;-0,026288]. IncluyeOTsinfiltrarobjetivo; cohorteparticipaciÃ³npositiva posterior, temporadas previamente inspeccionadas, sin disponibilidad/DNP ni OTduraciÃ³n/rotaciÃ³n/jointminutes. Resultado exploratorio; RUN052preservado, F7noiniciado.

Caliente10preciosdeequipos/0props/0contratos, dos pÃ¡ginas reglas actuales sin vigencia/ticket histÃ³rico acreditado. RevalidaciÃ³n fija fuente de liquidaciÃ³n/horario ademÃ¡sDNP/push/payout. TresSSHclockechoes:offsetremoto-local[-0,010387;2,711583]s, no sincronizaciÃ³n ni prueba en vivo. Transportes requieren lÃ­mites frescos y usan vencimiento conservador remoto; falta/antigÃ¼edad rechaza antesSSH/stdin. Fallo inicial425pass/1WindowsPermissionErrorpreservado; guardado Ãºnico/fsync/reemplazocon6reintentoslocalesWindows5/32, nunca llamadas externas. ImportError previo y dos lanzadores sinpsycopg previos a acciones preservados.

Suite final435sinomisiones conPostgresNBA nuevo, fuente39eventos/19mensajesintacta,clÃºsterdetenido; arnÃ©s768/10antes/despuÃ©s. RevisiÃ³n separada mismaautorÃ­a reconstruyÃ³ allCRPS/ICporfechas,104645historias,332distribucionesmuestreadas,245IDs/34lesiones/35recibos.57corridas/20328evidencias/134eventos preservados.

Protocolo cierre144read-only:colector activo19:15UTC/38recibos/mismaimagen/cero reinicios/source_degradedCalienteVPS403;serviciosanteriorespreservados, mÃ³dulos nuevos no desplegados. RevisiÃ³n automÃ¡tica rechazÃ³ envÃ­o SHA256manifiesto aDigiCert sin autorizaciÃ³n explÃ­cita del payload/destino:ningÃºnPOST/GETTSA nuevo ejecutado, alternativa local completa. Manifiesto d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e preparado, sello nuevo pendiente; pruebas anteriores RUN057 conservan propioalcance.

Protocolos135â€“144; checkpoint145.0APIdatosdeportivospagadas/0mensajes/0apuestas/0nuevascopiasperiÃ³dicas. Cota2232/3200sin cambios. G0â€“G9/alcance/decisiones/producciÃ³ncomercial preservados, F6abierta/F7draft_not_started. docs/nba_f6_partido_completo_y_contexto_oficial_20261008.md.


## 2026-10-08 â€” NBA: sello autorizado del manifiesto RUN058 (NBA-RUN-059)

El usuario respondiÃ³ Â«si autorizoÂ» al envÃ­o exclusivo SHA256/nonce aDigiCert. Protocolo146 fijÃ³ exactamente d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e. Una descarga de cadena y un POSTTSA gratuitos, sin documentos/credenciales ni reintentos. Granted firmado2026-10-08T19:24:17Z; firma/cadena/hash/nonce verificados dos veces, contenido alterado/nonce distinto rechazados. Sin nuevaOCSP/CRL. Prueba existencia nueva del manifiesto y sus hashes; no recepciÃ³n original histÃ³rica, predicciÃ³n previa a partidos retrospectivos, exactitud ni checkpoint posterior.

58corridas/20535evidencias/145eventos preservados; artefactos RUN058 se mantienen intactos, incluido rechazo histÃ³rico. AsociaciÃ³n externa posterior registrada separadamente. RevisiÃ³n separada mismaautorÃ­a, arnÃ©s768/10antes/despuÃ©s; mÃ³dulos NBA intactos y suite435anterior no repetida.0APIsdeportivaspagadas/0mensajes/0apuestas/0nuevascopiasperiÃ³dicas/0cambiosVPS. Protocolo146/checkpoint147, F6abierta/F7noiniciado. docs/nba_sello_externo_autorizado_20261008.md.

## 2026-10-08 â€” Reto escalera

Pedido del usuario con una regla de partida (cuota 1,25-1,40, 5-7 pasos,
freeroll a Ã—2,5). Antes de construir se midiÃ³ (`eval/escalera_prueba.py`,
firma d5cbc3151164): la probabilidad en ese rango estÃ¡ calibrada (72,1 %
prometido, 72,6 % real) pero cada escalÃ³n pierde âˆ’3,6 % de EV a la mejor de
bet365/1xBet, y la escalera lo multiplica: 6 pasos se completan el 15,6 % y
dejan âˆ’24,1 % por reto (âˆ’19,7 % con freeroll). DecisiÃ³n: solo escalones con
cuota â‰¥ precio justo de Pinnacle sin margen, en las casas de la lista; sin
candidato no se apuesta. En vivo (24-sep â†’ 8-oct) eso deja 4 de 20
candidatos: un reto puede tardar semanas. La muestra con filtro (73
escalones, 16 retos histÃ³ricos) no demuestra beneficio y la web lo dice.
DiseÃ±o: tablas inmutables y estado DERIVADO (`escalera.estado`) en vez de
columnas que se actualizan; aplazado â†’ nulo a las 48 h; bloque `escalera`
en el lote sellado con `LOTE_ESCALERA_DESDE` (None hasta desplegar), mismo
patrÃ³n que alta probabilidad. Doble oportunidad fuera: no hay cuota que
tomar en las fuentes. Primer escalÃ³n segÃºn la vista previa en producciÃ³n
(8-oct, sin escribir): Dortmund gana a Werder Bremen @1,36 (1xBet), prob.
74,1 %, EV +0,8 %.

## 2026-10-08 â€” Escalera: retos de 3 a 6 a la vez y hÃ¡ndicap asiÃ¡tico

DecisiÃ³n del usuario: varios retos a la vez, 3 escalones por defecto, de 6 como
mucho 3 al mes, 4 y 5 cuando ya hay otro abierto. Medido antes
(`escalera_prueba`, 3-6 pasos): acortar sube los completados (39,9 % a 3
pasos frente a 15,3 % a 6) y reduce la pÃ©rdida de la regla sin filtro (âˆ’11,5 %
frente a âˆ’26,2 % por reto), pero ninguna longitud gana sin el filtro de valor:
el valor esperado de un reto es el producto del de sus escalones. Reparto:
primero los retos abiertos (el mÃ¡s avanzado antes), despuÃ©s retos nuevos; un
partido nunca se repite entre retos ni coincide con un escalÃ³n sin liquidar.
HÃ¡ndicap: Pinnacle solo da su lÃ­nea principal en nuestras fuentes, asÃ­ que la
probabilidad sale del ajuste de goles; se validÃ³ la calibraciÃ³n sin cuotas
histÃ³ricas de esas lÃ­neas (firma d5cbc3151164): pasan âˆ’1 a +2 salvo âˆ’1,5. Solo
enteras y medias (las de cuarto liquidan medias y la escalera no las trata);
'push' no cuenta ni mueve el saldo. En vivo las protectoras llevan mucho margen
(Santos +1,5 a 1,36: âˆ’8 %). La prueba tarda ~40 min: el ajuste por partido.

## 2026-10-08 â€” Despliegue del reto escalera (commit 37aa902)

Autorizado por el usuario a las 21:06 UTC. `LOTE_ESCALERA_DESDE = 2026-10-09`
(el lote del 08 ya estaba sellado). Base del servidor cotejada contra f94a5bc
y el Ã¡rbol `src` del worker contra el servidor (solo diferÃ­a lo de cuentas y
panel, desplegado antes solo en la API). Paquete por SHA-256, respaldo en
`~/release-37aa902/backup.tgz`, imÃ¡genes previas `quantfut-api:before-37aa902`
y `quantfut-worker:before-37aa902`; `db/045` aplicado; `ESCALERA_ENABLED=1`.
Primera vez que se recrea el WORKER en esta fase: es quien corre el job
diario. Trampa: el contenedor no tiene `ps` ni `pgrep`, asÃ­ que la comprobaciÃ³n
de "ningÃºn job en marcha" no midiÃ³ nada; se recreÃ³ a las 21:08:27 (minuto
tranquilo, sin jobs de :08) y a las 21:10 cron ya ejecutaba odds y rÃ¡fagas. Para
la prÃ³xima, listar `/proc/*/cmdline`. Verificado: cadena (10 lotes OK),
vista previa en el worker (reto nuevo de 3, escalÃ³n Dortmund @1,36 1xBet,
EV +0,8 %), `/escalera` 200 tambiÃ©n desde el dominio y `app.js` pÃºblico igual
al del commit.

## 2026-10-08 â€” Escalera por probabilidad: cÃ³rners, tarjetas, goles, ambos anotan (sin desplegar)

DecisiÃ³n del usuario: la escalera elige el MÃS PROBABLE en 1,25-1,40, sin filtro
de valor (`EV_MIN = None`, `db/046` permite NULL). CÃ³rners y tarjetas
(amarillas + rojas) con `model/estadisticas_mercado.py` (equipos, liga,
Ã¡rbitro; sin cuotas). Prueba `eval/escalera_estadistica.py`: con encogimiento
6 prometÃ­a de mÃ¡s en los extremos; Ï† en 2019-21, encogimiento elegido en
2021/22, criterio en 2022-25. CÃ³rners pasan (mÃ¡s de 7,5/8,5/9,5; menos de
9,5/10,5/11,5); tarjetas no (âˆ’1 a âˆ’3 pts; solo menos de 6,5). Ambos anotan:
prueba en curso al cortar la sesiÃ³n; `BTTS_HABILITADO = False` hasta verla.
Cuotas de bets 8/45/80 de la respuesta de API-Football ya pedida; Ã¡rbitro y
tarjetas de football-data (`history_fd tarjetas`) y de results/fixtures.
Pendiente: resultado de ambos anotan, harness completo, desplegar (db/046,
`history_fd tarjetas` en el VPS, api + worker).


## 2026-10-08 â€” NBA: piloto de precios y contexto (NBA-RUN-060)

El usuario autorizÃ³ ejecutar el piloto de diez partidos tras conocer costos y falta de presupuesto adicional. Techo conservador incremental250 comunicado antes de consultas; cuenta existente, ninguna contrataciÃ³n. Once consultas histÃ³ricas cobradas210 y tres actuales9, total219;28rutas totales incluidas gratuitas y un422sin cargo. Saldo18.419al Ãºltimo recibo21:43UTC, sin saldo futuro garantizado. Los500anteriores se conservan como histÃ³rico, sin retroeditar. Cliente NBA aislado con reserva persistida, cuota/corte/URLs/credenciales y cero reintentos automÃ¡ticos.

Diez histÃ³ricos con puntos/rebotes/asistencias al corte60min previo al horario mÃ¡s temprano,2617pares identificados:1957nuevos+660previos.43rebotes excluidos por snapshot tardÃ­o, Dallas recuperado al corte correcto por10crÃ©ditos.13pares anteriores con Jimmy Butler/III quedan separados por polÃ­tica de nombre completo exacto; fuentes/IDs anteriores intactos.41mercados nuevos con relojes incompatibles y91pares histÃ³ricos sin identidad quedan sin promover.62observaciones oficiales previas al corte,10PDFs enlazados, recepciÃ³n2026nooriginal2025.

Diez actuales (6pretemporada/4regular):21pares en3regular,15frescos al recibo, sin identidades/contratos/estadofinal acreditados.6eventos/96lesionesESPN,5RotoWire/6tarjetasquintetos. CalienteHTTP403pero navegador pÃºblico legible; dos eventos solo cuotas de equipos. Observaciones DOM son transcripciÃ³n, no bytes HTTP ni recibo exacto; sin sesiÃ³n/boletos.

Fallos locales y422preservados; correcciones de fechaZ/reloj opcional de casa actual se prueban, reproceso offline sin pagar nuevamente. VerificaciÃ³n separada mismaautorÃ­a reconstruye2069pares nuevos y archivo2617, hash/cadena/identidades/consumo/ausencia de claves.69pruebas pertinentes,786/15arnÃ©s inicial y798/16final en Ã¡rbol compartido con fÃºtbol concurrente. Modelos/gates/F7/VPS/mensajes/apuestas/copiasperiÃ³dicas sin cambio por este piloto. docs/nba_piloto_props_y_contexto_20261008.md.


## 2026-10-08 â€” NBA: casas mexicanas y admisiÃ³n por evento (NBA-RUN-061)

Ante la peticiÃ³n de solucionar fuentes y revisar1xBet/Novibet, se verificÃ³ navegaciÃ³n pÃºblica sin cuentas/apuestas. Novibet muestra mercados de equipo enBOS-CLE; reglas de jugador explÃ­citas (entrada en cancha mantiene apuesta, DNPanula, OTsalvo excepciÃ³n, push), pero captura directa403y sin pares PTS/REB/AST verificados.1xBet tiene PDFmexicano recibido200y regla estadÃ­sticaOT; sus conteos de mercados no prueban cuotas individuales, selecciones ilegibles en dos eventos. No se adopta como fuente operativa por anuncio comercial. Betsson tambiÃ©n solo mercados de equipos en la vista revisada.

NBApÃ¡gina oficial recibida22:04:25UTC contiene42listados para0012600011; pertenencia al listado no prueba convocatoria efectiva ni salud. Un nombre corrupto marcado; inactivos vacÃ­os no prueban disponibilidad. Comando offline rechaza hash/partido/equipos/IDs/cortes incompatibles y conserva salidas. Al documentar la revisiÃ³n el partido ya comenzÃ³: ninguna observaciÃ³n nueva se retrofecha.61pruebas, arnÃ©s798/16,19GETgratis/0crÃ©ditos nuevos.60corridas/20675evidencias anteriores intactas y prefijo155eventos conservado; reparaciÃ³n transparente del logpostsealRUN060preservada. Sin cambioVPS/mensajes/modelos/gates/F7 ni copias periÃ³dicas. docs/nba_fuentes_1xbet_novibet_y_disponibilidad_20261008.md.

## 2026-10-08 â€” Despliegue de la escalera por probabilidad (commit abe3da4)

Pedido del usuario ("termina lo pendiente"). Desplegado a las 23:10-23:22 UTC,
ANTES del primer job con escalera (09-oct 08:00), asÃ­ que el primer reto nace
con la regla nueva. Base cotejada contra 37aa902, paquete por SHA-256, respaldo
en `~/release-abe3da4/backup.tgz`, imÃ¡genes previas `*:before-abe3da4`;
`db/046` aplicado; api y worker recreados. `history_fd tarjetas` cargÃ³
amarillas/rojas de 27.398 partidos de las 7 ligas principales y Ã¡rbitro de
4.610 de la Premier. Cadena: 10 lotes OK. Vista previa: abrirÃ­a 4 retos (3, 6,
4 y 5) con PSV @1,26, UniÃ³n-Defensa menos de 3,5 @1,27, Galatasaray @1,30 y
Dortmund @1,36. CÃ³rners/tarjetas/ambos marcan entran cuando af_odds capture
sus cuotas (desde las 00:20 UTC). Trampa repetida: la comprobaciÃ³n de jobs en
marcha vÃ­a /proc se contaba a sÃ­ misma (su lÃ­nea contiene "python -m qf");
el worker se recreÃ³ a las 23:21:40 tras agotar la espera. Para la prÃ³xima,
excluir el propio proceso (`grep -v` del PID o patrÃ³n con corchetes).


## 2026-10-08 â€” NBA: selecciÃ³n europea explÃ­cita (NBA-RUN-062)

El usuario solicitÃ³ incluir1xBetEuropa,BetssonEuropa,CodereItalia yBetanoReinoUnido. Se usan claves oficiales onexbet,betsson,codere_it,betano_uk y filtro de casas explÃ­citas, en lugar de ampliar a todos los proveedores de cada regiÃ³n. Europa no identifica el paÃ­s contractual de1xBet/Betsson; no se acredita equivalencia mexicana ni cobertura de props por presencia en catÃ¡logo.

SelecciÃ³n distribuida con paquete, planCLIoffline y mÃ©todo del cliente acotado mantienen presupuestos/recibos y no activan consultas periÃ³dicas. Descubrimiento actual reserva1crÃ©dito; tres mercados reservan3actuales o30histÃ³ricos. Solo transporte simulado y consolaoffline:33pruebas, arnÃ©s798/16,0consultasTheOddsAPI/0crÃ©ditos.61corridas/20756evidencias y prefijo160eventos preservados. F6abierta,F7sin iniciar; captura real y contratos aÃºn pendientes. Sin cambioVPS/mensajes/apuestas ni nuevas copias periÃ³dicas. docs/nba_casas_europeas_seleccionadas_20261008.md.


## 2026-10-08 â€” NBA: cuotas europeas comprobadas (NBA-RUN-063)

El usuario autorizÃ³ la consulta real con Â«hazloÂ». Se fijÃ³ protocolo antes de solicitudes pagadas: cuatro versiones explÃ­citas, ocho eventos, mÃ¡ximo56crÃ©ditos, cuenta existente/reserva compartida y sin reintentos. Se recibieron27respuestas200,16con cargo,29crÃ©ditos; cero fallos/reservas pendientes.

1xBet EU aportÃ³ 24 precios en 4 eventos; Betsson EU, 36 en 8; Betano UK, 12 en 3; Codere IT, ninguno. Total 72 selecciones de equipos, no pares de props. Ocho consultas directas PTS/REB/AST y descubrimiento sin esos mercados. Ausencia especÃ­fica del recibo: cuatro eventos de pretemporada tenÃ­an horario ya pasado y cuatro regulares estaban lejos del inicio; no se prueba ausencia universal. Se verificaron recibos y 33 pruebas pertinentes. ArnÃ©s 798/16. 62 corridas/20.777 evidencias y prefijo de 161 eventos preservados. F6 abierta/F7 sin iniciar; contratos, recepciÃ³n histÃ³rica y disponibilidad aÃºn pendientes. Sin VPS, mensajes, apuestas ni copias periÃ³dicas. docs/nba_cuotas_europeas_comprobadas_20261008.md.


## 2026-10-08 â€” NBA: suministro reutilizable de props resuelto (NBA-RUN-064)

El usuario pidiÃ³ solucionar el atasco de props. La causa era tratar la captura de datos y la admisiÃ³n comercial como el mismo requisito, ademÃ¡s de conservar precios US en muestras aisladas. Se implementÃ³ capture-props con perfil US/AU propio, presupuesto explÃ­cito, diez casas y selecciÃ³n exclusivamente futura, conservando la selecciÃ³n europea. La fuente de precios tiene estado funcional separado de production_ready/actionable, sin relajar validadores.

Captura real: 19 respuestas API, 17/32 crÃ©ditos, 36 pares (12 PTS/12 REB/12 AST) de FanDuel15, Sportsbet15 y Fanatics6 para cinco jugadores/tres eventos. 33 frescos al recibo, sin garantÃ­a de frescura futura. Identidades oficiales completas: 23 pruebas previas y 13 enriquecidas posteriormente, sin retrofechar el corte. 2617 pares histÃ³ricos reutilizados con recepciÃ³n original desconocida. Ocho GET pÃºblicos: dos perfiles y seis pÃ¡ginas de reglas; FanDuel directo403 conservado, las otras200. Sportsbet tiene guÃ­a explÃ­cita de participaciÃ³n/prÃ³rroga/resultados; Fanatics conserva excepciÃ³n por lesiÃ³n, contratos de cuentas no acreditados.

40 pruebas pertinentes; arnÃ©s 798/16. ReproducciÃ³n offline de precios, recibos, crÃ©ditos e identidades. 63 corridas/20.831 evidencias y prefijo164 eventos preservados. El pendiente de suministro queda resuelto; F6 global abierta por contrato, disponibilidad cerca del inicio y validaciÃ³n prospectiva; F7 sin iniciar. Sin apuestas, publicaciÃ³n, cambios VPS ni nuevas copias periÃ³dicas. docs/nba_props_fuente_funcional_20261008.md.

## 2026-10-09 â€” Escalera: probabilidad prudente en cÃ³rners y tarjetas (commit ed7ac99)

Con las primeras cuotas reales de cÃ³rners/tarjetas (00:20 UTC), la vista
previa abrÃ­a los 4 retos con Â«menos de 6,5 tarjetasÂ» y Â«mÃ¡s de 7,5 cÃ³rnersÂ»:
modelo 81-82 % frente a 69-72 % de la propia Betano sin margen. No es que la
casa regale 11 puntos: al elegir el MÃXIMO entre ~580 candidatos gana quien
mÃ¡s se equivoca hacia arriba, y la prueba histÃ³rica no lo podÃ­a ver porque
football-data no trae cuotas de esos mercados. El usuario eligiÃ³ la
probabilidad prudente: `min(modelo, mercado sin margen)` (Pinnacle si cotiza
los dos lados; si no, media de las casas de la lista); sin los dos lados el
candidato no entra. Desplegado a las 02:07 UTC del 9-oct, antes del primer
job con escalera (08:00): respaldo `~/release-ed7ac99/backup.tgz`, imÃ¡genes
`*:before-ed7ac99`. Vista previa nueva: 4 retos sin cÃ³rners ni tarjetas
(Moreirense menos de 3,5 @1,25, Red Star marca @1,25, PSV @1,27, Dunkerque-
Annecy mÃ¡s de 1,5 @1,27). El chequeo de jobs en marcha usa ya `[p]ython -m qf`.


## 2026-10-08 â€” NBA: seguimiento prospectivo en simulaciÃ³n (NBA-RUN-065)

El usuario autorizÃ³ conectar props al modelo y el seguimiento prospectivo, aceptando referencias US/AU. Protocolo exploratorio congelado antes de capturar: PTS/REB/AST, regular/fullgame/OT incluido,20apariciones/min10, prior temporada anterior, baselinePoisson, precios<=60s al sello, una unidad hipotÃ©tica. No se promueven candidatos de puntos/asistencias ni la extensiÃ³n de apertura de rebotes; probabilidades condicionadas a participaciÃ³n y disponibilidad final desconocida.

Lote inicial12crÃ©ditos/3eventos/36pares; adaptaciÃ³n detectÃ³ namespace omitido en parte del archivo corregido. ReparaciÃ³n por cruce exacto con etiquetas NBA verificadas, registrada antes de pronÃ³sticos; fallo original conservado. Quince predicciones selladas despuÃ©s, con cuotas vencidas y cero entradas. Tras66pruebas se anunciÃ³/fijÃ³ mÃ¡ximo adicional4crÃ©ditos para un partido: paper-run prevalidÃ³ antes de cobrar y sellÃ³ seis versiones/15pares recientes; precios53,75â€“53,98s. Dos entradas hipotÃ©ticas AST/PTS Cade; tres Tatum excluidas por candidato nominal de feedESPN (no estado de evento verificado), un mercado bajoEV. Cohorte congelada15casosÃºnicos,21versiones conservadas; total51pares/12consultas/16crÃ©ditos.

Se implementaron recepciÃ³n de final NBA, evaluaciÃ³n y resumen con sellos, identidad/equipos/hora/finalizaciÃ³n, DNP separados y rechazo de duplicados. CDN403; webNBA200 comprobada HOUâ€“OKC0022500001/final2OT con20participantes y sumasPTS/REB/AST reconciliadas. SeisGETpÃºblicos: ESPN200, CDNcalendario403, NBAcalendario200sin eventos y dos pÃ¡ginas futuras403. Los IDsNBA de eventos aÃºn necesitan enlace oficial; futuros resultados y disponibilidad no acreditados. NingÃºn resultado pasado sustituyÃ³ un futuro.

ReproducciÃ³n causal exacta21pronÃ³sticos y51pares;159075filas histÃ³ricas cruzadas. SuiteNBA499/17 y arnÃ©sgeneral800/16. Se preservan64corridas,20900evidencias y prefijo167eventos. F6 sigue abierta; preparaciÃ³nF7/piloto exploratorio activo, confirmaciÃ³ncientÃ­fica/G7sin iniciar, D07/D08pendientes. Sin mensajes/apuestas/publicaciÃ³n/VPS/suscripciones/recolector nuevo ni nuevas copias periÃ³dicas. docs/nba_seguimiento_prospectivo_20261008.md.


## 2026-10-08 â€” NBA: enlace oficial y seguimiento acotado (NBA-RUN-066)

El usuario pidiÃ³ resolver todos los pendientes. Se conservaron RUN065,21versiones/15unidades y2entradas hipotÃ©ticas. Tres pÃ¡ginas NBA HTTP200 cruzadas con proveedor por equipos y hora exactos:0022600001,0022600002,0022600003; inicio20oct13:00/17:00/19:30CiudadMÃ©xico. Conocimiento de IDs posterior al sello explÃ­cito. Plantillas actuales vacÃ­as, no disponibilidad. Cero crÃ©ditos nuevos y3GETpÃºblicos.

Nuevo trabajador acotado paper-followup-plan/paper-advance: sello de inputs, reclamaciÃ³n previa inmutable, mÃ¡ximo3tareasred por ejecuciÃ³n, sin reintentos, estado vivo fuera de evidencia de hashfijo. ObservaciÃ³n previaT-2min; cierre Sportsbet mismoevento/jugador/mercado/lÃ­nea, Ãºltimos5min/frescura60s/max2crÃ©ditos futuros; finalesoficialesT+4/+6/+12/+24h con ventanas2h. Score/summary sÃ³lo registrosoriginales/finalesverificados, DNP separados. Prueba actual sobrecohortereal cero tareasdebidas/cero consultas. AutomatizaciÃ³n local cierre-del-piloto-nba-octubre-20-y-21 ACTIVE para20â€“21oct en estechat; necesitaequipoencendido/Codexabierto, avisos sÃ³locambios/fallos/acciÃ³n. Fin22oct12UTC; ninguna ventana nirespuesta garantizada.

Lectura/CLV investigaciÃ³n prefijados y borradorpotencia usando sÃ³lo20853unidades/145dÃ­as/1087partidos de entrenamiento2022-23: CRPSprimarioREB/efectomÃ­nimo.05/alfa.025/potencia.8/mÃ­nimo112dÃ­as y300partidos. ProxydeplanificaciÃ³n, no confirmaciÃ³n. Candidato/exposiciÃ³nexactos, revisiÃ³nexterna, calendariofinal y cobertura aÃºn pendientes antesdeabrir otrobloque. D08investigaciÃ³n definido; reglasporcuenta/jurisdicciÃ³n pendientes. RecepciÃ³nhistÃ³ricaoriginal imposibledeacreditarcon descarganueva.

24pruebas de ciclo cubren cruce/hash/hora, rosterâ‰ salud, CLVcontrato/frescura, fallo403, duplicados, lÃ­mites/claims y cierre2mercadosrealmock. Prueba integral detectÃ³ dictmarketduplicado; corregido antesdevalidaciÃ³nfinal. PlanificaciÃ³nhistoricalectura necesitÃ³ adaptar metrics anidados; fallo preservado. Primer arnÃ©spost fallÃ³ porWinError5cachÃ© pese800pruebas; repeticiÃ³n con cachÃ©nueva conserva las mismas comprobaciones y pasa. SuiteNBA523/17; arnÃ©s800/16. Se preservan65corridas/21016evidencias/prefijo173eventos. F6/F7/G7sinpromociÃ³n, futuroseventos/resultadosnoinventados;0apuestas/copiasperiÃ³dicas/publicaciÃ³n/VPS/mensajesexternos. docs/nba_pendientes_resueltos_y_cierre_programado_20261008.md.


## 2026-10-08 â€” NBA: seguimiento autÃ³nomo en VPS (NBA-RUN-067)

El usuario pidiÃ³ resolver pendientes. Se cerrÃ³ dependenciaPC/Codex de captura mediante servicioNBA aislado enVPS, mismo plan/15casos/sellos RUN065/066. Primer despliegue rechazÃ³ FROMconID; segundo detectÃ³ rutasWindows enJSON. Ambos0cuotas/0probes deportivos; informesconservados. Readerinterpreta separadores sin cambiarbytes sellados; tercera versiÃ³nverificÃ³ fuente/modelo y arrancÃ³. TrespÃ¡ginasNBA200 desdeVPS, exactosIDs/equipos/hora;3recibospÃºblicos nuevos,0crÃ©ditosactuales,2mÃ¡ximocierre futuro.

Servicio nba-paper-pilot-run67, root /home/qf/nba-isolated/paper-pilot/run67-v3-20261008. Fuente/carpetasRO, redpropia/sinpuertos/0.5CPU/512MiB/64pids, sincapacidades/no-new-privileges, restartunless-stopped. ODDS_API_KEY existenteVPS comparada con cuentalocal, leÃ­da sinexportaciÃ³n; dos clavesdeintentosfallidos retiradas tras comprobarningÃºnmontaje; activa600conservada. NTPsincronizado. Primer cicloespera/cerojobs, segundoejecutorbloqueado antesdered, reinicio conservaexactostate;7serviciospreviosIDsiguales.

Estado/claims persisten; ventanas/fin/lectura max3tareas porinvocaciÃ³n y cap2originales. AutomatizaciÃ³n delchat ahoraobservaVPS, noejecuta capturas; tombstone state.owner.json y guardCLI rechazanexecutorlocalretirado. Avisos delobservador siguen locales, captura no. Terminal bloqueanuevasconsultas; observador detiene exclusivamentecontenedorNBA validandoetiqueta, sinborrar. No se garantizan fuentes futuras/p95.

Criterios/diseÃ±ocientÃ­fico exactos congelados para revisiÃ³n:REB fullgmOT,GammaPoisson/Poisson10,hist20/min10; ventana propuestaNov1-Mar31/lecturaApr2/3bloques,112dÃ­as/300partidos,deltaCRPS.05/alfa.025/potencia.8,bootstrapdÃ­as5000/seed20261009/calibmasa realdiscreta5pp. No activado porfaltarrevisiÃ³n,F6scopedy presupuesto; nosepromueveG7. Ficha vacÃ­a decontratocuenta separada delpaper. RecepciÃ³nhistÃ³ricaoriginalnoaportada, no reconstruiblehoy.

SuiteNBA531/17 y arnÃ©s800/16; paquete/worker7controles nuevos mÃ¡sguardCLI, flujosciclo24 conservados.66corridas/21056evidencias/prefijo176eventos preservados. Esperadatos20oct y confirmaciÃ³n nueva no se etiqueta como fallo tÃ©cnico. Sinapuestas/publicaciÃ³n/mensajesexternos/nuevascopiasperiÃ³dicas ni cambiosfÃºtbol. docs/nba_seguimiento_vps_y_pendientes_por_alcance_20261008.md.


## 2026-10-09 â€” NBA: activaciÃ³n operativa y alertas autÃ³nomas (NBA-RUN-068)

El usuario pidiÃ³ solucionar y activar todo. La salud degradada tenÃ­a origen enCaliente403 opcional; ESPNrespondÃ­a200. Se separÃ³ salud de fuentes necesarias de cobertura de casa, manteniendo403/cuerpo/hash y deteniendo consultas repetitivas. La misma carpeta RUN057 y todo su prefijo344eventos se conservaron; nuevo recolector conflock, imagenverificada yreinicio retieneestado. Nuevas copias periÃ³dicas desactivadas y archivosanteriores sin cambios.

Nuevo supervisor host aislado usaÃºnicamente token/destino operativo yaautorizados, extraÃ­dos enVPS yprivados600. ReclamaantesPOST, diariocontriggers/hash, cap20intentos porUTCdÃ­a, sinretryincierto niavisosrepetidos porreinicio. UnTelegramconfirmado condestinoverificado; no acredita lecturadesuscriptores. DetenciÃ³n terminal exclusiva decontenedorpiloto con etiquetaexacta; noDocker general niapuestas.

Primer despliegue detectÃ³carrera Type=simple alcomprobar bloqueoantesinicializaciÃ³n; rollback automÃ¡tico conservado. RecuperaciÃ³nType=notify anunciaREADYdespuÃ©slock/ciclodurable; segundoejecutor rechazado, reinicio conservaÃºnica reclamaciÃ³n/mensaje. ArranqueVPS habilitado, independientedelPC/Codex. Piloto/sellos15casos/cap2intactos ycontenedoresfÃºtbolsin cambios.

DosGETpÃºblicos actuales, ceroAPIcuotas; futurocierremax2. DiseÃ±ocientÃ­fico yficha decuenta copiados una vez; F7confirmatoria/G7no promovidos. Falta revisar/validaruniversoprospectivo yrecibirpartidos futuros; cero tickets reales, disponibilidad yrecepciÃ³nhistÃ³ricaoriginal no inventadas. Fallossintaxislocal/directoriotemporal/fixture preservados ycorregidos; suiteNBA542/1 yarnÃ©s800/16. docs/nba_activacion_y_alertas_vps_20261009.md.


## 2026-10-09 â€” NBA: pÃ¡gina pÃºblica de pronÃ³sticos y resultados (NBA-RUN-069)

Se publicÃ³ https://pronosticosdeportivos.pro/nba con la cohorte sellada de 15 registros, cinco jugadores y tres partidos. La pÃ¡gina filtra jugador/equipo, mercado, partido y estado. Presenta estimaciÃ³n, rango, probabilidades condicionales a participaciÃ³n y cuotas histÃ³ricas con recepciÃ³n/sello; cero resultados evaluados hoy, partidos registrados el 20 de octubre. No son apuestas ni cotizaciones actuales.

Servicio aislado con recursos limitados y fuentes originales montadas solo para lectura. Verifica diario, plan, sellos y recepciÃ³n; reconstruye conteos desde el boxscore oficial antes de publicar un resultado. DNP explÃ­cito separado de cero, ausencia exige revisiÃ³n. No ejecuta modelos ni captura desde solicitudes web, no monta credenciales ni datos de fÃºtbol. La configuraciÃ³n del proxy y su segunda red quedan persistentes. FÃºtbol y protecciÃ³n de administraciÃ³n comprobados por HTTPS.

Se conservaron tres intentos fallidos con reversiÃ³n automÃ¡tica: archivo anterior retenido por el montaje del proxy y comprobaciones de disponibilidad demasiado tempranas. Cuarto intento espera HTTP real antes y despuÃ©s de reiniciar; pasÃ³ conservando diario del piloto y contenedores originales. La comparaciÃ³n pÃºblica contempla solo la etiqueta de analÃ­tica inyectada por el CDN existente y exige igualdad de los bytes propios.

La pÃ¡gina pÃºblica se abriÃ³ en navegador y los filtros/detalles de cuotas se comprobaron sin errores de consola. Captura guardada. El navegador ignorÃ³ los tamaÃ±os solicitados y mantuvo 700Ã—572; revisiÃ³n visual mÃ³vil pendiente explÃ­cita, no declarada como probada. Pruebas NBA 558/2, arnÃ©s antes y despuÃ©s 800/16. Se preservaron las 68 ejecuciones y todas sus evidencias, sin promover puertas cientÃ­ficas, apuestas ni copias periÃ³dicas. docs/nba_pagina_pronosticos_resultados_20261009.md.


## 2026-10-09 â€” MenÃº FÃºtbol/NBA e histÃ³rico (NBA-RUN-070)

El usuario preguntÃ³ por el histÃ³rico y pidiÃ³ acceso NBA desde la cabecera de fÃºtbol. El archivo aceptado conserva su huella NBA-EV-2204:164.218 filas y6.313 IDs, fechas2021-10-19..2026-06-13. Son datos retrospectivos; no un historial de aciertos emitidos antes del partido. El piloto conserva15pronÃ³sticos y0resultados recibidos.

Selector superior FÃºtbol/NBA con enlaces accesibles, activo marcado y reglas mÃ³viles fuera del menÃº que se oculta. Nuevas huellas JS/CSS enHTML. PublicaciÃ³n deriva de la imagen exacta de fÃºtbol ya ejecutada y aÃ±ade solamente tres recursos pÃºblicos. Se recreÃ³ Ãºnicamente laAPI; las otras identidades, trabajador/base/proxy/NBA y cÃ³digos de backend se conservaron. ConfiguraciÃ³n de imagen y fuentes persistida enVPS.

Primera comprobaciÃ³n recibiÃ³ conexiÃ³n cortada al arrancar y revirtiÃ³ automÃ¡ticamente. RecuperaciÃ³n conservada tolera esa lectura transitoria de salud propia y exige200antes de comprobarHTTPS; pasÃ³. NavegaciÃ³n real FÃºtbolâ†’NBAâ†’FÃºtbol,15filasNBA y captura de pantalla; consola sinerrores a1280Ã—720. La solicitud390Ã—844 volviÃ³ a ignorarse, tambiÃ©n en pestaÃ±a nueva: revisiÃ³n visual mÃ³vil pendiente explÃ­cita.24pruebasfrontend y800/16arnÃ©s; registrosprevios/gates intactos, sinapuestas/copiasperiÃ³dicas nuevas. docs/nba_menu_e_historico_20261009.md.


## 2026-10-09 â€” Nueve mercados NBA desde estadÃ­sticas (NBA-RUN-071)

El usuario pidiÃ³ desarrollar todos los mercados discutidos, priorizando probabilidad/estadÃ­stica sobre cuotas. Se recuperaron triples/robos/tapones de los originales ya recibidos, con uniones exactas y reconciliaciÃ³n de equipos:157.962filas/6.108partidos regulares;42discrepantes excluidos sin alterar el histÃ³rico anterior. Se desarrollaron seis modelos de conteo y Elo/medias ataque-defensa/covarianza para ganador/equipos/total, con caracterÃ­sticas anteriores a cada fecha.

Entrenamiento2021â€“22, calibraciÃ³n2022â€“23, evaluaciÃ³n exploratoria2023â€“26. Candidato y referencia calibrados igual; cÃ¡lculo preliminar sin esa equidad conservado y protocolo corregido antes de inspeccionar mÃ©tricas. Ganadorâ‰¥70% acierta80.4%/1.071casos frente69.5%referencia; equipos74.3%/1.721 frente53.3%. Los conteos raros pueden dar mucho acierto por baja frecuencia; tapones80.3% coincide con referencia. Puntos/rebotesâ‰¥70% logran65.1%/65.6%, por debajo de sus probabilidades medias: no se anuncian selecciones fiables70%. Todos los modelos continÃºan experimentales y no accionables; no se alterÃ³ el candidato confirmatorio de rebotes RUN067.

42unidades nuevas selladas para los mismos tres eventos y cinco jugadores;15originales intactas. Web con nueve filtros y tabla conprobabilidadmedia/acierto/cobertura/referencia/intervalos. La extensiÃ³n reutiliza recibos oficiales verificados del piloto sÃ³lo para lectura: conteos reconciliados, ausencia en revisiÃ³n y DNP separado. Prueba integral verifica conteo adicional real y rechaza cuerpo modificado, sin escribir diario. No agrega consultas deportivas ni crÃ©ditos.

Imagennba-dashboard-run71 reemplaza sÃ³lo el servicio NBA manteniendo su nombre interno; anterior detenido recuperable. FÃºtbol/proxy/captura/piloto/alertas conservan identidad, configuraciÃ³n y estado; reinicio/HTTPS y diezaccionesfiltroverificadas. 1280Ã—720, consola sinerrores; revisiÃ³nmÃ³vil390px sigue pendiente porlimitaciÃ³n previa.577/18NBA mÃ¡s3pruebasintegrales y800/16arnÃ©s. NuevascopiasperiÃ³dicas/apuestas desactivadas, puertas cientÃ­ficas y cuatrobloquesde decisiones conservados; resultados y disponibilidad de20oct siguen futuros. docs/nba_nueve_mercados_estadistica_20261009.md.

## 2026-10-09 â€” Alta probabilidad: mÃ¡s de 2,5, hÃ¡ndicap asiÃ¡tico y cÃ³rners (commit 27e8a7f)

Pedido del usuario (ambos marcan, cÃ³rners, mÃ¡s/menos 2,5 y hÃ¡ndicap). Regla de
la lÃ­nea: solo entra lo que pasa la prueba histÃ³rica, asÃ­ que se midiÃ³ todo
(firma d5cbc3151164) y se habilitÃ³ lo que pasa. Ambos marcan NO se publica no
por fallar sino porque nunca llega al 80 % en las 7 ligas: no hay nada que
validar. CÃ³rners rompe el "siempre Pinnacle": se acepta solo recortado a la
probabilidad sin margen de la casa (misma regla que la escalera desde hoy) y
sin los dos lados cotizados no entra. Con todo habilitado la regla da
pronÃ³stico en el 85 % de los partidos (antes 63 %) y sigue cumpliendo
(82,35 â†’ 82,89); dentro de lo elegido, 1X2 y menos de 3,5 quedan ~2 puntos
por debajo: no es criterio, lo vigila el control por grupo. Ojo: el hÃ¡ndicap
casi nunca trae cuota de referencia (solo The Odds API lo cotiza) y los
cÃ³rners elegidos se pagan a 1,10-1,16. Desplegado 23:32 UTC; la API usa la
imagen fijada en compose (`quantfut-api-menu70:20261009`), asÃ­ que se
retagueÃ³ ese nombre; respaldo `~/release-27e8a7f/`, imÃ¡genes `*:before-27e8a7f`.
Vista previa: 61 decisiones, 29 de hÃ¡ndicap y 8 de cÃ³rners.

## 2026-10-09 â€” API-NBA: comprobar permisos antes de activar la fuente

La clave facilitada coincide con la privada ya configurada; autenticaciÃ³n y Free activo comprobados. Se corrigiÃ³ la afirmaciÃ³n basada en la guÃ­a pÃºblica: 100 consultas pueden alcanzar por volumen, pero la cuenta rechaza temporadas 2025 y 2026. TambiÃ©n rechaza fechas histÃ³ricas explÃ­citas; el calendario de temporada 2024 sin fecha devuelve 1.406 partidos y es acceso expresamente permitido. Cinco solicitudes de datos y dos estados, sin reintentos; cabecera final 99 restantes, estados declararon cero consumo y no se fuerza conciliaciÃ³n de contadores. Cuenta personal retirada de recibos, clave excluida de evidencia/Git. No se activa un bucle improductivo ni una suscripciÃ³n, no se modifica VPS/fÃºtbol/modelos/sellos. Recibos nuevos separados de originales previos, docs/nba_api_nba_acceso_actual_20261009.md. ArnÃ©s previo:808/16.
Cierre del diagnÃ³stico API-NBA: arnÃ©s posterior808/16, igual al previo; siete recibos con SHA-256 verificados y evidencia sin credencial/identidad de cuenta. Docker no disponible. Los cambios ajenos en escalera_estadistica.py se conservaron sin intervenciÃ³n.

## 2026-10-10 â€” CÃ³rners de cada equipo y mÃ¡s de 6,5 (commits 3ce62c4 y 583d432)

Pedido del usuario a partir de un texto de "mercados de mÃ¡s del 70 %". De ese
texto casi todo ya estaba publicado; lo nuevo eran mÃ¡s de 6,5 cÃ³rners y los
cÃ³rners del favorito. Se miden con el mismo acumulador y un Ï† propio por
equipo (1,5455): el modelo por equipo calibra peor que el de totales (varias
lÃ­neas fallan en 60-80 %), asÃ­ que solo entran las lÃ­neas que pasan, por
separado en la escalera y en alta probabilidad. "El favorito saca mÃ¡s de 3,5"
pasa en alta probabilidad para el local, no en la escalera. Cuotas: bets 57/58
de la misma respuesta de API-Football (ids comprobados con 1 consulta a
/odds/bets). Desplegado 00:52 UTC (db/048); la primera captura (01:20) trajo
~8.700 filas de 194 partidos. Fallo encontrado en la vista previa: los
cÃ³rners por equipo salÃ­an sin cuota de referencia (`_ref_nuevos` solo miraba
'corners'); corregido y redesplegado 01:27 (583d432). Vista previa: 81
pronÃ³sticos de alta probabilidad, 22 de cÃ³rners; la escalera sigue eligiendo
sobre todo goles.

## 2026-10-11 â€” Historial de las ligas "solo sharp" para el modelo propio (pasos 1-5)

Pedido del usuario ("activa todas esas ligas en el modelo propio"). El
cargador de football-data buscaba cada nombre SOLO en la liga que cargaba:
el historial de Segunda habrÃ­a creado un segundo Racing, Leeds, Troyesâ€¦ y
partido su historia sin error. Ahora clasifica en todo el paÃ­s (alias del
paÃ­s o exacto de cualquier fuente; un parecido NUNCA se crea ni se acepta
solo) y hay un ensayo en seco previo. El ensayo cazÃ³ dos cosas que la carga
habrÃ­a grabado: `new/CHL.csv` redirige con 200 a la Superliga CHINA (Chile
se queda sin football-data; el cargador comprueba ahora Country/Div), y un
duplicado que ya existÃ­a (el calendario creÃ³ "Arminia Bielefeld" sin ver al
"Bielefeld" de la Bundesliga; fusionado en db/050). Los 86 dudosos se
revisaron a mano (db/050) y los clubes nuevos se crearon ANTES de cargar
(db/051): cada club que crea el cargador se vuelve candidato para los
siguientes nombres, y la carga dejaba de ser lo que el ensayo habÃ­a medido.
Resultado: 39.842 partidos, 0 equipos creados por la carga, 0 duplicados.

`model_enabled` decidÃ­a tambiÃ©n quÃ© se paga a los proveedores; encenderlo
habrÃ­a triplicado el gasto de The Odds API en 10 ligas y activado
alineaciones/bajas/jugadores con API-Football ya en ~5.400 de 7.500/dÃ­a.
`captura_completa` (db/052) lo separa. Y el modelo no se puede entrenar con
el interruptor encendido: con el modelo viejo activo, el job de las 08:00
sellarÃ­a predicciones de equipos que no conoce. De ahÃ­ `train --incluir`.
Desplegado sin cambio de comportamiento (imÃ¡genes `*:before-ligas`).
Pendiente: evaluaciÃ³n en sombra y decisiÃ³n del usuario antes de activar.

## 2026-10-10 â€” Tarjetas con Ã¡rbitro: no; y las pruebas de cÃ³rners/tarjetas iban sin 2024/25

Pedido del usuario (mercado de tarjetas "con historial y Ã¡rbitros"). Prueba
`eval/tarjetas_arbitro.py` en E0+E1 (Ã¡rbitro en el 100 %), criterio fijado
antes de mirar. El Ã¡rbitro mejora la pÃ©rdida logarÃ­tmica 0,0011 por partido
(z=1,07; Premier âˆ’1,48, Championship +2,47) y empuja la media 0,18 tarjetas
por encima de la real: cumple la letra del criterio (A) pero no es una
mejora real, asÃ­ que no hay regla propia para Inglaterra. Y en Inglaterra el
modelo calibra igual de bien SIN Ã¡rbitro.

Lo importante saliÃ³ de rebote: 9 CSV de football-data (toda 2024/25 y la
Premier 2021/22) traen BOM; leÃ­dos en latin-1 la columna `Div` era
`Ã¯Â»Â¿Div` y `groupby("Div")` de `escalera_estadistica` los tiraba sin error.
Las pruebas del 8 y 9-oct midieron 10.842 partidos, no 13.555, y la Premier
eligiÃ³ parÃ¡metros sin su temporada de ajuste. Las demÃ¡s pruebas agrupan por
`league_id` y no se vieron afectadas; el cargador de producciÃ³n
(`history_fd`) ya decodificaba con utf-8-sig. Con los datos completos y los
mismos parÃ¡metros (`--fijos`) caen tres lÃ­neas de cÃ³rners de la escalera, las
tres en el tramo 70-80 %, que es justo donde elige la escalera, y una de alta
probabilidad; entran tarjetas menos de 4,5 y 5,5. La regla es la de siempre
(solo lo que pasa), no se reajustaron parÃ¡metros. Tarjetas en alta
probabilidad, todavÃ­a no: alta va 11 puntos por debajo de lo prometido.
Resultados en `.local/escalera_estadistica_20261010_fijos.json` y
`.local/tarjetas_arbitro_20261010.json`. Sin desplegar.

## 2026-10-11 â€” Flutter/Firebase: anÃ¡lisis y pantallas antes de implementar

App ubicada en `apps/mobile`: revisados 62 archivos Dart, configuraciÃ³n
nativa, cuentas/suscripciones/API/panel existentes y documentaciÃ³n oficial de
Firebase. AnÃ¡lisis Flutter sin incidencias y nueve pruebas existentes
aprobadas desde la nueva ubicaciÃ³n; no validan aÃºn Auth/FCM/compras. Plan
documentado en
`apps/mobile/docs/FIREBASE_INTEGRACION_CON_BACKEND_20261011.md` con identidad
Firebase vinculada a cuentas existentes, API como autoridad de permisos,
notificaciones, mediciÃ³n, control y transiciÃ³n de usuarios.

El usuario confirmÃ³ implementaciÃ³n por fases y pidiÃ³ primero presentar sus
ideas de pantallas. Se registra fase 0 de diseÃ±o y recomendaciones antes de
concretar fases/entregables. Pendiente de recibir esas ideas; no se iniciÃ³
integraciÃ³n funcional, configuraciÃ³n Firebase ni cambios de producciÃ³n.

## 2026-10-11 â€” Flutter: primeras pantallas QuantFut y navegaciÃ³n VIP

Incorporadas las referencias del usuario en `apps/mobile`: cinco bienvenidas
con ilustraciones animadas originales, arranque QuantFut y barra inferior
Inicio / Predicciones / En vivo / La Grada / Perfil. Tarjetas de ejemplo,
filtros de equipo/liga/dÃ­a/deporte, fichas VIP difuminadas y botÃ³n Hazte VIP
que abre la selecciÃ³n de planes. Los metadatos VIP no contienen el anÃ¡lisis
privado. Precios pendientes; comprar muestra un aviso y no realiza cargos.

Estados de directo, comunidad y perfil preparados como propuestas. Sin
conexiÃ³n Firebase/API, sin sesiÃ³n ni pagos activos. No se alterÃ³ producciÃ³n.
DiseÃ±o, lÃ­mites y fases documentados en
`apps/mobile/docs/PANTALLAS_BIENVENIDA_INICIO_VIP_20261011.md`.
ValidaciÃ³n: trece pruebas Flutter, texto ampliado en 320 Ã— 568, anÃ¡lisis sin
incidencias y Android debug. Capturas en `apps/mobile/docs/validation/`.

## 2026-10-11 â€” Flutter: mercados con evidencia e idioma registrado

Sustituidas las propuestas de radar/primer tiempo por Mercados: ocho familias
fÃºtbol, selecciÃ³n de lÃ­neas habilitadas con prueba aprobada y al menos 500
casos como regla de presentaciÃ³n, sin modificar las reglas del modelo.
Historial pÃºblico del VPS guardado aparte: 75/96 (78,1 %), muestra inicial;
las tasas retrospectivas no se presentan como resultados publicados.
Pantallas Hoy/HistÃ³rico, avisos pendientes, ruta VIP y NBA exploratoria.
RevisiÃ³n local del 10-oct distinta de la desplegada: tarjetas 4,5/5,5
pendientes y cÃ³rners local +2,5 no se destacan; servidor sin cambios.
18 pruebas Flutter aprobadas, anÃ¡lisis sin incidencias, Android debug
compilado e instalado en el emulador. Detalle y fuentes:
`apps/mobile/docs/MERCADOS_MODELO_APP_20261011.md`.

Nueva referencia del usuario: selector de idioma desde el primer arranque,
antes de bienvenida, con es/en/pt/fr/it/de, persistencia y cambio en Perfil.
Registrado junto a Firebase: traducciÃ³n Flutter, cuenta/backend/web,
Auth/correos, FCM/bandeja y mediciÃ³n; identificadores y datos del modelo no
se traducen. Pendiente de implementar, sin simular traducciones ya listas.
`apps/mobile/docs/IDIOMAS_APP_BACKEND_FIREBASE_20261011.md` y tareas del arnÃ©s.

## 2026-10-11 â€” App con datos reales, Monedas y Referidos

AutorizaciÃ³n posterior del usuario: eliminar el modo demo y conectar el modelo
real, con interruptores por secciÃ³n y leyenda configurable de entrenamiento.
La raÃ­z Flutter consume la API de producciÃ³n; calendario, enfrentamientos,
pronÃ³sticos, detalle, historial, planes y cuenta dejan de usar datos ilustrativos.
Los datos que la fuente todavÃ­a no entrega se identifican como ausentes.

Alta Probabilidad: rango de presentaciÃ³n 75â€“90 %, 10 % gratuito (redondeado
hacia arriba), mayor cuota real entre elegibles y asignaciÃ³n inmutable por lote.
Escalera: un Ãºnico pendiente gratuito de mayor probabilidad exacta entre todos
los retos activos. VIP oculta selecciÃ³n/mercado/cuota/probabilidad desde el
servidor, incluidas las rutas web pÃºblicas; no solo desde la pantalla.

MenÃº reemplaza La Grada y ofrece Monedas y Referidos. Saldo y movimientos en
PostgreSQL, asistencia de siete dÃ­as, cÃ³digos de invitaciÃ³n y canje de un pick.
Correo verificado, movimientos idempotentes, canjes atÃ³micos y anulaciones
reversibles de premios. ConfiguraciÃ³n administrativa en
`/control/configuracion-app` y `/control/recompensas`, con CSRF y auditorÃ­a.

InvestigaciÃ³n de Tapjoy/Unity, RevU, Torox, ayeT, adjoe y BitLabs documentada con
fuentes. Adaptadores iniciales RevU/BitLabs preparados; el usuario confirmÃ³ que
todavÃ­a no tiene cuentas de editor. Los seis proveedores estÃ¡n desactivados:
no se anuncian ofertas, ingresos ni acreditaciones comerciales inventadas.

Migraciones 054/055 instaladas. Despliegue limitado de API sobre su imagen previa,
sin recrear los workers. Imagen activa y persistida en compose:
`quantfut-api-mobile-rewards:20261011`; copia de configuraciÃ³n anterior guardada.
Web, health y seis rutas de contenido/monedas respondieron 200. ComprobaciÃ³n
UTCâˆ’6 del 11/10: 99 enfrentamientos, dos picks pÃºblicos, quince VIP pendientes,
un escalÃ³n pÃºblico y seis proveedores pendientes. Estos conteos son variables.

ValidaciÃ³n: 124 pruebas backend aprobadas y cinco PostgreSQL condicionadas
omitidas localmente; ocho comprobaciones adicionales contra PostgreSQL real,
siempre con rollback (saldo, repeticiÃ³n, reversiÃ³n, referidos, cuotas gratuitas,
canje, vistas y formularios administrativos). Flutter: 18 pruebas aprobadas;
siete pruebas de navegaciÃ³n repetidas tras los Ãºltimos ajustes, anÃ¡lisis limpio,
APK debug compilado e instalado. Calendario, tarjetas y Monedas inspeccionados
en el emulador, sin errores Flutter/AndroidRuntime observados.

Estado, fuentes y activaciÃ³n:
`apps/mobile/docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md`.
Evidencia pÃºblica y de servidor:
`docs/validation/mobile_rewards_release_20261011/`.
Capturas Android reales:
`apps/mobile/docs/validation/real_mobile_20261011/emulator-*.png`.
Firebase, idiomas, persistencia segura de sesiÃ³n, pagos/restauraciÃ³n, cuentas
de editor y mÃ©tricas de detalle aÃºn no expuestas permanecen en tareas pendientes.

## 2026-10-11 â€” Registro primero: requisito Firebase, sin ejecuciÃ³n

El usuario entregÃ³ la captura de acceso oscuro con Google, idioma en la esquina
superior y aceptaciÃ³n de tÃ©rminos/privacidad. PidiÃ³ que registro/acceso sea la
primera pantalla de la app y que se anote en el plan Firebase sin implementarlo
todavÃ­a. Registrado en el plan principal, el plan de suscripciones, la
especificaciÃ³n de idiomas y el backlog. La elecciÃ³n de idioma pasa a estar
disponible en la pantalla de registro; bienvenida y contenido vienen despuÃ©s
del acceso para personas sin sesiÃ³n. La sesiÃ³n existente y los derechos/saldo
del backend deben conservarse. Las cifras de la referencia no se trasladarÃ¡n
sin respaldo real. Este ajuste modifica documentaciÃ³n Ãºnicamente: sin cambios
de cÃ³digo, configuraciÃ³n Firebase, compilaciÃ³n, emulador ni despliegue.

## 2026-10-11 â€” Coins: recompensas como cuarta pestaÃ±a

CorrecciÃ³n del usuario: eliminar el menÃº intermedio de Monedas/Referidos y
abrir directamente la pantalla de saldo, asistencia, ofertas y referidos.
La cuarta pestaÃ±a y su encabezado ahora se llaman Coins, con icono de monedas.
La navegaciÃ³n inferior permanece disponible dentro de esta pantalla y su
actualizaciÃ³n consulta el saldo real. No se alteraron las reglas del backend.
Siete pruebas de navegaciÃ³n aprobadas, anÃ¡lisis sin incidencias y APK debug
compilado para actualizar el emulador. Registro inicial Firebase sigue pendiente
sin implementaciÃ³n, conforme a la instrucciÃ³n anterior del usuario.

## 2026-10-11 â€” ActivaciÃ³n de las 10 ligas: el modelo nuevo no pasa la puerta

Con el visto bueno del usuario se entrenÃ³ con `--incluir` (9 h 40 min,
artefacto 2026.10.11-135412). La puerta lo rechazÃ³: no vence a Elo en las
mismas filas (0,20517 frente a 0,20468, n=1.541). El script no encendiÃ³
`model_enabled` y nada cambiÃ³ en producciÃ³n. La causa no son las ligas
nuevas: el entrenamiento del 1-oct, sin ellas, ya perdÃ­a contra Elo
(0,20074 frente a 0,19995); con ellas la distancia se acorta, y la sombra
mostrÃ³ que las ligas ya medidas mejoran (0,20800 â†’ 0,20752). El activo
(09-27) pasÃ³ la puerta por 0,0002: Dixon-Coles y Elo estÃ¡n empatados en la
ventana reciente. No se fuerza una puerta de seguridad sin decisiÃ³n expresa.

## 2026-10-11 â€” Parley del dÃ­a (sin desplegar)

Pedido del usuario: 1-5 parlays diarios de cuota 1,90-5,00, "los mÃ¡s
probables". Con "mÃ¡xima probabilidad dentro de un rango" todo saldrÃ­a pegado
a 1,90, asÃ­ que el usuario eligiÃ³ escalones (â‰ˆ2 Â· 2,5 Â· 3 Â· 4 Â· 5), un partido
por parlay y ninguno repetido en el dÃ­a, y solo probabilidad (pierde el margen
en cada pata; el historial lo enseÃ±a). La revisiÃ³n final cazÃ³ cuatro cosas que
los tests del plan no veÃ­an: la poda de patas "dominadas" que prescribÃ­a la
propia spec pierde parlays vÃ¡lidos cuando hay techo de cuota (se quitÃ³; 4,5 s
sin ella); las cuotas llegan como float4 y 1,25 Ã— 1,76 salÃ­a "2,20 en el
escalÃ³n 1"; un ticket se guardaba fila a fila y uno a medias habrÃ­a quedado
inmutable y sellado (ahora una transacciÃ³n con candado por dÃ­a); y
`fixtures` sobrescribe la hora de un partido reprogramado, asÃ­ que la pata
guarda su hora original y se anula a las 48 h de ella. Acierto frente a la
probabilidad EFECTIVA (solo patas que contaron). Sin doble oportunidad:
ningÃºn proveedor la cotiza. Desplegado apagado el 12-oct 00:10 UTC SOBRE las imÃ¡genes de producciÃ³n (que
ya llevan la app mÃ³vil sin commitear) copiando SOLO los archivos del parley:
desplegar la carpeta entera habrÃ­a metido tambiÃ©n los cambios de tarjetas y
cÃ³rners del 10-oct, que no estaban desplegados. El Ã¡rbol `~/quantfut` del
VPS no tiene ni la app mÃ³vil ni el parley: un `docker compose build` los
quitarÃ­a. Primer ensayo: los cinco parlays salen de 2 patas; la bÃºsqueda
prefiere pocas patas porque cada una paga margen.

## 2026-10-11 â€” PestaÃ±a PronÃ³sticos con el formato Â«PronÃ³sticos IAÂ»

El usuario pidiÃ³ la ficha de la referencia (pronÃ³stico destacado, Confianza IA,
xG proyectado, diferencial Elo, tendencia de goles, dictamen). Se adoptÃ³ el
diseÃ±o, no las cifras: Â«Confianza IAÂ» y Elo no existen en el contrato y el
documento de detalle prohÃ­be fabricarlos a partir de un porcentaje histÃ³rico.
Se sustituyeron por magnitudes que el servidor sÃ­ tiene: probabilidad con cuota
justa, favorito 1X2 (`ficha.probabilities`) y tendencia de mÃ¡s de 2,5 goles
(`promedios.pct_mas_2_5`). El xG proyectado sale de las lambdas del ajuste de
mercado (`alta_prob_picks.fit`), que `high_probability` ahora expone como `xg`
sin filtrar el ajuste crudo; en mercados sin ajuste queda Â«â€”Â». El dictamen se
compone en el cliente solo con esos datos. Con el visto bueno del usuario se desplegÃ³ SOLO `mobile.py` (el remoto era
idÃ©ntico a HEAD) con `docker compose cp` + reinicio de `api`, sin tocar el
worker; producciÃ³n ya devuelve `xg` real. Ojo: al ser `cp`, una recreaciÃ³n del
contenedor desde la imagen lo perderÃ­a hasta reconstruirla. APK debug
compilado e instalado en el emulador.

## 2026-10-11 â€” Pantalla VIP con el formato Â«VIP ELITEÂ» (solo app, sin backend)

Se moviÃ³ `LiveVipScreen` a `live_vip.dart` y se rediseÃ±Ã³. De la referencia se
tomÃ³ la estructura; se descartaron las cifras y promesas que el servidor no
respalda (miembros, testimonio, pruebas gratuitas, Â«pago con Google PlayÂ»,
Â«cancela cuando quierasÂ»): el cobro sigue sin proveedor y el botÃ³n dorado solo
muestra el mensaje de la secciÃ³n `compras`. Â«Mejor precioÂ» se marca por el menor
equivalente mensual entre los planes que llegan del servidor. Sin despliegue de
backend; APK debug instalado en el emulador. 21 pruebas Flutter aprobadas.

## 2026-10-12 â€” Ficha de partido: el pick sellado sigue visible al empezar el partido

Pumasâ€“Cruz Azul mostraba Â«No hay pronÃ³sticos publicadosÂ» a los 20 min de empezar
aunque el pick existÃ­a en `alta_prob_picks`: `high_probability` descartaba todo
pick con `kickoff_utc <= now`, decisiÃ³n pensada para los listados de Â«prÃ³ximosÂ»
y no para la ficha. Ahora `detail()` pide `started=True` y recibe tambiÃ©n los
picks de partidos en curso o liquidados, con `started` y `outcome`/marcador
(LEFT JOIN `alta_prob_results`); el reparto gratis/VIP no cambia, y home y
listados siguen sin verlos. La app muestra una franja Â«EN JUEGO / ACERTADO /
FALLADOÂ». Desplegado SOLO `mobile.py` (el remoto era idÃ©ntico salvo este cambio)
con `docker compose cp` + reinicio de `api`; copia previa en
`~/backups/mobile.py.*.bak` del VPS. Mismo aviso de siempre: al ser `cp`, una
recreaciÃ³n del contenedor desde la imagen lo perderÃ­a hasta reconstruirla.

### Marcador en vivo para la app (2026-10-11)

DecisiÃ³n: columnas `live_*` propias (db/056) en vez de reutilizar `status` y
`home_goals`. Esos los usa el pipeline de picks y `results.py` los escribe con
`result_recorded_at`; un marcador provisional ahÃ­ contaminarÃ­a la auditorÃ­a
temporal. `ingest/live.py` hace UNA peticiÃ³n `fixtures?live=all` por pasada y
ninguna si no hay partido en ventana, asÃ­ el coste no depende de los usuarios.
Cron cada 45 min por decisiÃ³n del usuario (cuota); `*/45` da huecos de 45 y 15
min. El marcador sale en `/mobile/v1/matches/{id}` como `partido.vivo`, fuera
de la ficha cacheada. Se descartÃ³ `tunjayoff/sofascore_scraper`: licencia
PolyForm Noncommercial y raspado contra los tÃ©rminos de Sofascore.
Desplegado el 2026-10-12 sin tocar compose: imÃ¡genes delgadas sobre las vivas, con
respaldo `before-live` (api `quantfut-api-mobile-rewards`, worker `quantfut-worker`).
Primera pasada real: 6 candidatos, 2 en juego, 1 peticiÃ³n. Franja `LiveScoreStrip`
en Flutter (falta recompilar la app). Pendiente: marcador en el calendario.

### PestaÃ±a Mercados rediseÃ±ada (2026-10-12)

DecisiÃ³n: se adapta el lenguaje visual de la referencia (radar, anillos, puntos)
pero NO sus alertas en vivo (Â«MÃ¡s/Menos en vivoÂ», Â«QuiÃ©n marca en el primer
tiempoÂ»): los modelos pronostican antes del partido y el catÃ¡logo de evidencia
lo dice expresamente. Cada tarjeta sale de `MarketCatalog` (mejor lÃ­nea
confirmada + publicados resueltos), asÃ­ que no hay cifras inventadas y una
familia sin lÃ­nea confirmada muestra Â«â€”Â». Animaciones con CustomPainter, sin
paquetes ni assets de terceros; se detienen con Â«reducir movimientoÂ».

### Mercados: pantalla por mercado e historial por pronÃ³stico (2026-10-12)

DecisiÃ³n: se quita la tarjeta Â«Rendimiento registradoÂ» de Mercados; cada
familia abre su pantalla con Â«HoyÂ» (pronÃ³sticos abiertos que el servidor ya
entrega) y Â«AnterioresÂ» (resueltos, acertÃ³/fallÃ³). Las cifras salen del
historial del servidor, no del JSON empaquetado: el radar decÃ­a 75/96 y el
servidor 89/114. Nuevo `GET /mobile/v1/markets/history` (alta probabilidad,
selladas, rango pÃºblico 75-90 %, anuladas fuera, probabilidad con precisiÃ³n
pÃºblica). Los pronÃ³sticos VIP bloqueados no se atribuyen a un mercado (su
metadato no lo lleva) y no se muestran en Â«HoyÂ»; el reparto gratis/VIP sigue
decidido por el servidor.

El historial por mercado manda `home_corners/away_corners` y la app los muestra en los
mercados de cÃ³rners en vez del marcador de goles (despliegue 2026-10-12, respaldo
`before-corners`). Posible hueco de datos: Operario-PR - Goias figura 14-0 en cÃ³rners;
un 0 puede ser un cÃ³rner no capturado, no un cero real.

### Candados dentro de cada mercado (2026-10-12)

DecisiÃ³n del usuario: los pronÃ³sticos VIP bloqueados se ven dentro de su mercado
(partido, hora, candado), sin el pick. Cambio de polÃ­tica: antes el metadato
bloqueado no llevaba `market`. Ahora sale SOLO la categorÃ­a; selecciÃ³n, lÃ­nea,
probabilidad, cuota y `fit` siguen fuera (test actualizado). Sin tarjeta de venta:
tocar el candado abre VIP. Escalera no se incluye (su metadato no se reparte por familia).

### Gratis: uno por mercado, el de mayor probabilidad (2026-10-12)

DecisiÃ³n del usuario: el escaparate gratuito debe mostrar lo mÃ¡s sÃ³lido para que se vea que la
mayorÃ­a acierta. Antes: 10 % del lote por mejor cuota. Ahora: un pronÃ³stico por mercado con
candidatos, el de mayor probabilidad (empate: cuota). El reparto de cada lote queda fijo en
`mobile_free_allocations` al crearse, asÃ­ que la regla solo afecta a lotes NUEVOS salvo que se
amplÃ­e el lote vigente a mano (solo aÃ±adir, nunca quitar).

Desplegado el 2026-10-12 (respaldo `quantfut-api-mobile-rewards:before-gratis`). Lote 2026-10-11
ampliado a mano con 3 gratis (cÃ³rners, goles, goles del visitante; free_count 3 -> 6). HÃ¡ndicap (7)
y doble oportunidad (1) siguen bloqueados: sus candidatos no tienen cuota publicada y un gratis
sin cuota real no se entrega.

### Gratis: cuota entre 1,20 y 1,60 (2026-10-12)

DecisiÃ³n del usuario: el gratis debe tener cuota publicada entre 1,20 y 1,60, el de mayor probabilidad
por mercado. El usuario pidiÃ³ 1,40-1,60 pero con 75-90 % de probabilidad las cuotas reales van de 1,01
a 1,25 (132 candidatos en 7 dÃ­as, 0 en 1,40-1,60), asÃ­ que eligiÃ³ piso 1,20. Desplegado (respaldo
`before-cuota`). Los 3 gratis aÃ±adidos a mano al lote 2026-10-11 se quitaron (cuotas 1,08-1,19; fuera de
rango; free_count 6 -> 3, auditado). Hoy no queda ningÃºn gratis abierto: ningÃºn candidato sin empezar
tiene cuota en rango.

### Gratis: la cuota manda (2026-10-12)

DecisiÃ³n del usuario: el gratis de cada mercado es el de MAYOR cuota publicada (tope 1,60, sin piso),
aunque tenga menos probabilidad que otros; empate por probabilidad. Sustituye al rango 1,20-1,60 por
probabilidad. Desplegado (respaldo `before-mayor-cuota`) y los 3 gratis quitados antes se volvieron a
aÃ±adir al lote 2026-10-11 (Elfsborg 1,19, Valerenga 1,18, Malmo 1,08; free_count 3 -> 6). HÃ¡ndicap y
doble oportunidad siguen sin gratis: sus candidatos no tienen cuota publicada.

### Gratis automÃ¡tico (2026-10-12)

DecisiÃ³n del usuario: la regla es permanente, no un parche por lote. `top_up()` corre en cada lectura
(`allocations()`, dentro del mismo bloqueo del lote) y hace gratis el pronÃ³stico sin empezar de mayor
cuota de cada mercado que no tenga ya uno abierto. Solo aÃ±ade (no quita lo que el usuario ya vio),
es idempotente y queda auditado (`mobile:allocation_topup`). Desplegado (respaldo `before-automatico`):
tres lecturas seguidas dejaron free_count en 6, sin cambios. Ya no hacen falta ampliaciones manuales.
La Escalera conserva su regla de un solo pendiente gratuito.

### Tarjeta del pronÃ³stico nueva (2026-10-12)

Sustituye al destacado + 4 recuadros por: 4 anillos (MÃ¡s 2,5, Ambos marcan, MÃ¡s 1,5, Gana local),
caja del pronÃ³stico y tabla Â«Â¿CuÃ¡ntos goles?Â» (al menos 1/2/3 por equipo = team_totals 0,5/1,5/2,5).
El Â«1T >0,5Â» de la referencia NO existe: no hay modelo de primer tiempo, se usa Â«MÃ¡s 1,5Â».
Backend: `ficha.modelo` (model_card, 2 decimales) sale en /mobile/v1/matches/{id} SOLO si el usuario
tiene un pronÃ³stico visible de ese partido; las probabilidades de las que se deriva el pronÃ³stico no
se regalan para todos los partidos. Sin datos del modelo, la tarjeta no dibuja anillos ni tabla.

Ligas solo sharp (sin predicciÃ³n propia): `market_card()` calcula la misma tarjeta desde el ajuste a
Pinnacle del pick (lambda, mu, rho) con `pricing.price_all_markets`, y la marca `fuente: mercado`; la app
lo dice debajo de los anillos. Solo para picks con `fit` (goles, hÃ¡ndicap y cÃ³rners); doble oportunidad y
1X2 no guardan `fit` y siguen sin anillos. Sin desplegar al escribir esto.

## 2026-10-11 â€” Alta probabilidad: mediciÃ³n 62â€“95 % (paso previo a ampliar el rango)

- Pedido del usuario: abrir el rango de alta probabilidad a 62â€“95 % en todos los
  mercados, ordenando por mayor cuota. DecisiÃ³n: medir ANTES de publicar (el 80 %
  se validÃ³; los tramos 62â€“80 % nunca se midieron).
- `eval/alta_prob_calibracion.py --amplio` (`run_amplio`): todos los candidatos de
  62â€“95 %, tramos 62-67/67-72/72-76/76-80 + los de siempre, mismo criterio
  (tramo con nâ‰¥100: real â‰¥ prometidoâˆ’2Â·SE; global â‰¥ âˆ’1 punto). 14.305 partidos.
  Resultado en `.local/alta_prob_amplio_20261011.json`: pasan 27 de 40 lÃ­neas
  (1X2, doble oportunidad, hÃ¡ndicap âˆ’1/0/+1/+1,5/+2, marca local/visitante, mÃ¡s
  de 1,5/2,5, menos de 3,5/4,5, ambos marcan Â«sÃ­Â», cÃ³rners mÃ¡s 6,5/8,5 y menos
  11,5/12,5 totales). No pasan: ambos marcan Â«noÂ», menos de 2,5, y la mayorÃ­a de
  cÃ³rners por equipo (dÃ©ficits de 0,1â€“1,2 puntos o un tramo bajo).
- AÃºn NO se publica nada: falta decidir la tabla sellada nueva (`alta_prob_picks`
  tiene `match_id UNIQUE`, un pick por partido) y la cadena de hashes.

### PestaÃ±a PronÃ³sticos con todos los mercados (2026-10-12)

Pedido del usuario: la pestaÃ±a queda como su referencia (tarjeta Â«AnÃ¡lisis estadÃ­sticoÂ» + lista de mercados
con nivel + marcadores). `api/partido_mercados.py` deriva la lista de (lambda, mu, rho): la predicciÃ³n propia
o, en ligas solo sharp, el ajuste a Pinnacle del pick; los cÃ¡lculos son los de `pricing` (comprobado: diferencia
0,0 frente a `predictions.markets` en 40 predicciones). CÃ³rners y tarjetas salen de `estadisticas_mercado` y
SOLO con sus `LINEAS_HABILITADAS`. Nivel por probabilidad (alta >= 75, sÃ³lida >= 60, moderada); Â«oportunidadÂ»
solo con cuota publicada y prob x cuota > 1,02; sin cuota publicada se muestra la cuota justa etiquetada.
Acceso: abiertas = las del usuario (gratis/desbloqueadas) o todas con VIP; el resto va con candado que solo
dice la categorÃ­a y SIN orden por probabilidad (el orden la filtrarÃ­a). La app agrupa los candados por categorÃ­a.
Desplegado (respaldo `before-mercados`): 24 mercados en un partido real, 0,58 s la primera vez y 15 ms con cachÃ©.

AVISO de despliegue: el VPS corre el mÃ³dulo VIEJO de cÃ³rners/tarjetas (lÃ­neas anteriores a la revisiÃ³n del
10-oct, que se dejÃ³ Â«sin desplegarÂ» a propÃ³sito: mÃ¡s de 6,5 y 9,5 cÃ³rners siguen apareciendo). La lista sigue lo
que estÃ¡ desplegado y se alinearÃ¡ sola cuando esa revisiÃ³n se despliegue (decisiÃ³n sobre los picks del worker).
La tarjeta anterior de anillos/Â«Â¿CuÃ¡ntos goles?Â» se retirÃ³ de la pestaÃ±a (la sustituye la lista).

## 2026-10-11 â€” Alta probabilidad ampliada 62â€“95 % (`alta_prob_ext`), implementada sin desplegar

- DecisiÃ³n del usuario: tabla aparte (`db/057`, un candidato por partido+mercado+
  selecciÃ³n+lÃ­nea, inmutable) con todo lo aprobado por la prueba amplia; la lÃ­nea
  de 80â€“95 % (`alta_prob_picks`) no cambia. Por quÃ© aparte: `match_id UNIQUE` de
  `alta_prob_picks` y su lote ya sellado no admiten varios picks por partido.
- `publish/alta_prob_ext.py`: selecciÃ³n (`alta_prob.elegir_ext`, listas `*_EXT`),
  control por mercado (reusa `ap.control`), liquidaciÃ³n (encadenada en
  `eval/clv.settle_pending`). Sellado: bloque `alta_ext` en el lote desde
  `LOTE_ALTA_EXT_DESDE = 2026-10-12`; los lotes anteriores no cambian de hash.
- App: `mobile.py` lee ambas tablas (62â€“95 %), sin duplicar partido+mercado+
  selecciÃ³n+lÃ­nea (manda la fila original); gratis = mayor cuota por mercado, tope
  1,60; `pick_key` de las filas ampliadas es `ext_id`. Escalera sigue en 75â€“90 %.
- Apagada: `ALTA_PROB_EXT_ENABLED=0`. Falta aplicar db/057 en el servidor, activar
  el flag ANTES del sellado de las 08:00 UTC del 12-oct, y verificar con
  `python -m qf.publish.alta_prob_ext preview`. Si no se despliega a tiempo,
  mover `LOTE_ALTA_EXT_DESDE` al primer lote sin sellar.
- Desplegado el 12-oct ~02:40 UTC con visto bueno del usuario. db/057 aplicada;
  archivos copiados a `api` y `worker` partiendo de lo que habÃ­a en producciÃ³n
  (el servidor NO tenÃ­a la revisiÃ³n de cÃ³rners del 10-oct en `alta_prob.py`: se
  conservÃ³, solo se aÃ±adiÃ³ lo de la ampliaciÃ³n). ImÃ¡genes confirmadas con
  `docker commit` (`quantfut-api-mobile-rewards:20261011`, `quantfut-worker:latest`)
  y recreados `api` y `worker` con `ALTA_PROB_EXT_ENABLED=1` en `.env`; respaldo en
  `~/quantfut/deployments/before-ext` y etiquetas `:before-ext`. Preview real:
  287 candidatos en 25 partidos (143 con cuota publicada), 0,62â€“0,95. El Ã¡rbol
  `~/quantfut/src` del VPS sigue sin actualizar. Falta: ver el primer sellado (08:00
  UTC) con `n_alta_ext` > 0 y recompilar la app.

### 1Âª mitad: prueba histÃ³rica y mercados publicados (2026-10-12)

`eval/primer_tiempo.py` (football-data, cuotas de Pinnacle, entreno 2019-2022 con 5.743 partidos y medida en
2022-2025 con 6.236, criterio de `alta_prob_calibracion` fijado antes): PASAN Â«ambos anotan 1T: noÂ» (n=6.236,
79,9 frente a 80,5 prometido) y Â«gol en 1T: sÃ­Â» (n=6.015, 72,6 frente a 71,7). No pasan: ganador 1T visitante
(n=27), mÃ¡s de 1,5 goles 1T (tramo 62-67 %: 61,7 frente a 64,4) y ganador 1T local pasa pero con n=159, por
debajo de las 500 muestras que exige el catÃ¡logo de evidencia: no se publica. Modelo: goles del 1T Poisson con
proporciÃ³n (0,4366 local, 0,4588 visitante) del mismo ajuste de mercado; vive en `model/primer_tiempo.py`.
Se publican solo esos dos, por ese lado y en el tramo medido (62-95 %). Desplegado (respaldo
`before-primer-tiempo`). Ojo: hay OTRA ediciÃ³n sin commit de `mobile.py` (alta probabilidad 62-95 %, db/057)
que no es de esta tarea y NO estÃ¡ desplegada.

### Parley activado (2026-10-12, 05:5x UTC)

Visto bueno del usuario. Fecha de arranque = 12-oct (`LOTE_PARLEY_DESDE`, ya fijada): el sellado de las
08:00 UTC es el primero que lo lleva. ANTES de activarlo, el ensayo (`parley_datos preview`) mostrÃ³ una pata
Â«mÃ¡s de 9,5 cÃ³rnersÂ», lÃ­nea que la revisiÃ³n del 10-oct habÃ­a quitado y que el VPS aÃºn permitÃ­a. Con la
aprobaciÃ³n del usuario se desplegÃ³ esa revisiÃ³n al worker y a la API (`estadisticas_mercado.py` y, en el
worker, solo el hunk de `CORNERS_HABILITADOS` de `alta_prob.py` sobre el archivo ya desplegado por la otra
sesiÃ³n; respaldo `quantfut-worker:before-lineas`, `...:before-lineas-api`). Efecto: cÃ³rners mÃ¡s de 7,5/8,5 y
menos de 9,5/10,5/11,5; tarjetas menos de 4,5/5,5/6,5; fuera cÃ³rners mÃ¡s de 6,5/9,5 y local mÃ¡s de 2,5 en alta
probabilidad. Segundo ensayo: 5 parlays de 2 patas, 0 con lÃ­neas no validadas. `PARLEY_ENABLED=1` en el
`.env` del VPS (copia en `releases/lineas-10oct-20261012/env.before-parley`), worker y API recreados.
PENDIENTE: quiÃ©n ve cada parley. `/parley` es pÃºblico y la app los muestra todos; falta el reparto
gratis/VIP (hoy son gratis para cualquiera).

### CorrecciÃ³n: hora real de la activaciÃ³n del Parley y nuevo horario de sellado (2026-10-12)

La secciÃ³n Â«Parley activado (05:5x UTC)Â» y el mensaje del commit fe441c1 estÃ¡n MAL en la hora: la pregunta al
usuario esperÃ³ ~9 h y la activaciÃ³n se ejecutÃ³ a las 14:48 UTC, no a las 05:5x. El sellado de las 08:00 UTC
de hoy ya habÃ­a corrido con el Parley apagado (`parley: desactivado`, 0 parlays), asÃ­ que NO hay parlays
sin sellar (`hashchain verify`: 14 lotes OK). El primer lote con Parley es el del 13-oct.
DecisiÃ³n del usuario: el sellado diario pasa a las 07:00 de Ciudad de MÃ©xico = 13:00 UTC, siempre (MÃ©xico no
tiene horario de verano desde 2022; cron corre en UTC). `scripts/crontab`: `0 13 * * *` (antes `0 8`),
aplicado en el VPS (copia `scripts/crontab.before-13utc`) y recargado con `crontab /etc/cron.d/quantfut`, sin
reiniciar el worker. Efecto: solo entran partidos que empiezan DESPUÃ‰S del sellado; los de 08:00-13:00 UTC
dependen del lote anterior (el job ya mira partidos de hoy y maÃ±ana). El comentario de `daily.py` (Â«08:00,
antes del primer kickoff europeoÂ») queda desfasado; no se tocÃ³ porque ese archivo tiene cambios de otra sesiÃ³n.

## 2026-10-12 â€” App actualizada en el emulador Android

Pedido: Â«despliega el trabajoÂ». Compilada la app del espacio de trabajo actual,
con EstadÃ­sticas, Coins, mercados y la nueva pestaÃ±a Parley. `flutter analyze`
sin incidencias; suite completa `flutter test`: 32 pruebas aprobadas.
`flutter build apk --release`: correcto, 59,8 MB. InstalaciÃ³n con `adb install -r`
confirmada (Success) en Medium_Phone_API_37.0, emulator-5556, sin borrar los datos.
AplicaciÃ³n abierta y navegaciÃ³n Inicio / Predicciones / Parley comprobada con
respuesta real; Parley activo pero sin tickets publicados hoy, estado mostrado
sin inventar selecciones. Registro de errores Android/Flutter vacÃ­o.

API HTTPS comprobada: /mobile/v1/config, /mobile/v1/home y /parley devuelven 200.
La configuraciÃ³n real entrega 62â€“95 %. Los servicios del VPS ya estaban activos;
no se volvieron a desplegar archivos ni trabajadores desde este Ã¡rbol local.
Firebase/registro inicial continÃºa Ãºnicamente en el plan.

APK: apps/mobile/build/app/outputs/flutter-apk/app-release.apk (1.0.0+1).
SHA256: 3D963890AB6FFF66CA0A46AC76B2377DBAFE92878DC80E635AD0F0213037E62F.
Captura: apps/mobile/docs/validation/real_mobile_20261011/release-parley-20261012.png.
Este APK conserva la firma de desarrollo configurada en el proyecto; no se ha
publicado en Google Play ni cambiado la firma o el identificador de la aplicaciÃ³n.

## 2026-10-12 â€” Firebase Core e identidad definitiva de QuantFut

DecisiÃ³n del usuario: comenzar Firebase por fases en el proyecto existente
`pronosticos-deportivos-85ffa`; despuÃ©s de la pausa, fijar nombre QuantFut e
identificadores Android/iOS `com.saptain.quantfut`. Por eso se generaron apps y
configuraciÃ³n nuevas, en vez de conservar los registros `com.example.gobet`.
El usuario completÃ³ el acceso de Google y pidiÃ³ eliminar los dos ejemplos.
Ambos registros `gobet` se eliminaron; la lista remota confirma Ãºnicamente
QuantFut Android e iOS activos. ConfiguraciÃ³n Android descargada de nuevo,
verificando que contiene solo el paquete definitivo.

La fase actual instala `firebase_core` y espera su inicializaciÃ³n antes de
abrir la app, con reintento visible si falla. Firebase estÃ¡ activo por defecto.
Se conserva FastAPI/Postgres como autoridad de cuentas, suscripciÃ³n, saldo y
pronÃ³sticos: Auth/Google, FCM, Analytics, Crashlytics, Performance y Remote
Config siguen pendientes. Las herramientas CLI quedan locales e ignoradas;
la configuraciÃ³n pÃºblica puede versionarse, las credenciales privadas no.

ValidaciÃ³n: anÃ¡lisis Flutter limpio, 35 pruebas aprobadas y APK debug con la
nueva identidad compilado/instalado en emulator-5556. Registro nativo confirma
`FirebaseApp initialization successful`; el arranque abriÃ³ el calendario con
datos reales. ArnÃ©s inicial y posterior: 911 aprobadas, 21 omitidas y una
advertencia; Docker no disponible. iOS tiene bundle ID, opciones y plist
incluido en Runner, pero necesita compilaciÃ³n/ejecuciÃ³n en Mac. Firma Android
de distribuciÃ³n pendiente. Detalle: apps/mobile/docs/FIREBASE_INSTALACION_20261012.md;
evidencia: apps/mobile/docs/validation/firebase_base_20261012/.


### Doble oportunidad con cuota real en el Parley (2026-10-12)

CORRECCIÃ“N de la nota Â«ningÃºn proveedor la cotizaÂ»: API-Football SÃ cotiza Doble Oportunidad (bet 12, 8 casas
en un partido de La Liga, entre ellas Bet365, Betano, 1xBet y William Hill; valores `Home/Draw`, `Home/Away`,
`Draw/Away`). Se descartÃ³ sintetizarla desde el 1X2: una cuota justa calculada no la ofrece nadie y no sirve de
precio de referencia; se capturan las cuotas reales. Hecho: (1) `ingest/af_odds.py` guarda bet 12 como
`double_chance` 1X/12/X2 (grupo completo, nombre exacto, soft books y Pinnacle); sin peticiones extra; primera
pasada: 65 partidos x 4 casas. (2) Solo el PARLEY la usa: `escalera_datos.opciones(incluir_doble=True)` aÃ±ade
`candidatos_doble` (probabilidad = P1+PX de Pinnacle sin margen) con cuota de `_cuotas_af`; `parley.MERCADOS_PARLEY`.
La Escalera NO cambiÃ³ (verificado en producciÃ³n: 323 opciones evaluadas, 48 en rango, antes y despuÃ©s). (3) db/059:
el CHECK `parley_patas_market_check` rechazaba `double_chance` y habrÃ­a roto el guardado del primer parley; la migraciÃ³n
solo amplÃ­a la regla (0 filas afectadas). Desplegado en worker (respaldos `before-doble`, `before-doble-parley`).
Ensayo: 4 patas de doble oportunidad con cuotas reales (Betano 1,16/1,29/1,67, Bet365 1,33).
PENDIENTE (toca archivos de la otra sesiÃ³n, alta probabilidad ampliada): que `alta_prob_datos._ref` use esas cuotas
para que la doble oportunidad pueda ser pronÃ³stico gratis; hoy `_ref` devuelve sin precio. Ideas aÃºn sin hacer:
informe de calibraciÃ³n por origen (Pinnacle frente a cÃ³rners/tarjetas), test binomial exacto en el control del parley
(con n=50 y p=0,24 el `z<=-4` actual no puede dispararse) y orden del armado (medido: +0,6 % en un dÃ­a).


## 2026-10-12 â€” Servicios Firebase, identidad y despliegue de API

El usuario ampliÃ³ el alcance a Auth/Google, FCM, Analytics, Crashlytics,
Performance, Remote Config y App Check. Se conservan FastAPI/Postgres como
autoridad comercial; Firestore/Storage/Functions P2 no se activaron. Google
estÃ¡ habilitado en Firebase y los recursos Android/iOS preparados. App Check
usa Play Integrity en distribuciÃ³n y proveedor de desarrollo registrado en
emulator-5556; enforcement continÃºa apagado. Los registros de ejemplo ya no
estÃ¡n activos.

DecisiÃ³n de identidad: cabecera explÃ­cita Firebase y verificaciÃ³n de proyecto/
revocaciÃ³n; no convertir un token invÃ¡lido en sesiÃ³n anterior. El mismo correo
no toma control de una cuenta: vÃ­nculo solo demostrando la sesiÃ³n previa.
Se preservan ID, saldo, VIP y referidos. Consentimientos versionados;
mediciÃ³n/diagnÃ³stico/avisos opcionales apagados por defecto. Avisos genÃ©ricos,
ruta interna validada y permisos consultados de nuevo al abrir; bandeja y
cola con propietario/caducidad/reintentos. El envÃ­o automÃ¡tico no estÃ¡ activo.

Tras rechazo de revisiÃ³n automÃ¡tica, el usuario autorizÃ³ explÃ­citamente crear
quantfut-backend con lectura Auth y envÃ­o FCM, generar clave privada, y despuÃ©s
desplegar en producciÃ³n. Clave fuera de Git y Flutter, privada y montada como
solo lectura. SDK 7.7.0 instalado, migraciÃ³n 058 aplicada, solo API recreada.
Compose e imagen anteriores respaldados, reversiÃ³n de arranque preparada.
Paquete sobre la imagen real del servidor, sin cambios deportivos de otras
sesiones. La primera compilaciÃ³n fallÃ³ al interpretar SHA como repositorio;
se corrigiÃ³ usando una etiqueta local de la misma imagen y el despliegue pasÃ³.

La imagen en ejecuciÃ³n incluye mÃ³dulos mÃ³viles que todavÃ­a no estÃ¡n en el
checkout del VPS. Una comprobaciÃ³n previa detuvo la sincronizaciÃ³n antes de
escribir archivos; no se intentÃ³ reconstruir desde ese checkout antiguo.
El paquete y fuentes exactas quedan en releases/firebase-backend-20261012.
Una futura reconstrucciÃ³n debe partir de la imagen vigente o reconciliar
primero todo el cÃ³digo desplegado, para no perder funciones anteriores.

Servidor verificado: credencial Auth vÃ¡lida sin descargar usuarios reales,
seis tablas presentes, pip check correcto, API HTTPS config/home 200;
preferencias/avisos anÃ³nimos 401 y acceso Google cerrado 503. Google continÃºa
FIREBASE_AUTH_ENABLED=0 y qf_google_auth_enabled=false hasta documentos vigentes.

ValidaciÃ³n: anÃ¡lisis Flutter limpio, 38 pruebas aprobadas,APKdebug instalado y
calendario real con 43 partidos. Preferencias opcionales comprobadas apagadas;
arranque posterior al registro App Check sin error fatal/Flutter/intercambio
en la observaciÃ³n. 11 pruebas Firebase y 8 escenarios PostgreSQL real en esquema
aislado con rollback, sin cambiar filas comerciales. ArnÃ©s completo: 924 aprobadas,
21 omitidas, 2 advertencias; Docker local no disponible. No se ha probado Google
con usuario real, entrega FCM ni iOS. Firma de distribuciÃ³n y Apple/APNs
pendientes; selector de 6 idiomas disponible, traducciÃ³n completa pendiente.

Datos legales confirmados por el usuario: Saptain LTD; E Coast Rd, Victoria,
Seychelles; admin@pronosticosdeportivos.com; edad 18; Estados Unidos, toda Europa
y LatinoamÃ©rica. Se actualizaron borradores y fuentes primarias. Proveedores
Contabo/Proton identificados en notas; faltan ubicaciÃ³n contractual, ciclos de
retenciÃ³n/respaldo/procedimiento de derechos y revisiÃ³n territorial. No se
publicaron borradores ni se registraron como aceptados. Las leyes obligatorias
de mercados de destino no se excluyen por la constituciÃ³n en Seychelles.

Detalle: apps/mobile/docs/FIREBASE_SERVICIOS_20261012.md. Evidencia sin secretos
en apps/mobile/docs/validation/firebase_services_20261012/; borradores y control
de publicaciÃ³n en docs/legal/.

## 2026-10-12 â€” Tapjoy Offerwall (Unity) como proveedor de monedas

- Decision: callback S2S estandar de Tapjoy (GET, `verifier=md5(id:snuid:currency:secret)`), moneda *self-managed*. Solo creditos: la doc de Tapjoy no define reversiones; un `currency` negativo se rechaza con 403. Errores definitivos siempre 403 (Tapjoy reintenta 4 dias ante cualquier otro codigo distinto de 200/403).
- El offerwall se abre por SDK nativo (no URL): `launch` devuelve `{sdk,sdk_key,user_id}` y `MainActivity.kt` hace `Tapjoy.connect` con `USER_ID`=uid del monedero, que llega como `snuid`.
- Dashboard (cloud.unity.com > Tapjoy Offerwall): app Quantumfut (Android, no activa), moneda `Monedas` ($1 = 1000), placement `coins_offerwall` + tarjeta `Coins`. Secreto en `QF_TAPJOY_SECRET` (VPS); la cuenta Tapjoy esta en revision.

- Secret keys de proveedores (Tapjoy, BitLabs) editables desde /control/recompensas (db/060, columna `secret_enc`): AES-256-GCM con `cryptography` (pyca; AEAD estandar, auditado, sobre OpenSSL), nonce aleatorio y contexto `reward_provider:<id>` como AAD para que un secreto no se pueda mover a otra fila. La clave maestra `QF_SECRETS_KEY` vive solo en el entorno del servidor (rotacion con `QF_SECRETS_KEY_OLD`): copiar la BD no basta. Campo de solo escritura, auditoria sin el valor, variable de entorno como respaldo. Fallo cerrado: sin clave maestra el panel rechaza guardar.

- Despliegue VPS 2026-10-12 (sin git): codigo copiado al contenedor, `docker commit` a `quantfut-api-tapjoy:20261012`, compose apuntado a esa imagen y `compose up -d --no-deps api`. Respaldos en ~/backups/tapjoy-20261012 (env, compose, rewards.py/html previos); vuelta atras = imagen `quantfut-api-mobile-rewards:pre-tapjoy-backup` + env respaldado. db/060 aplicada; `QF_SECRETS_KEY` generada en el servidor (no esta en ningun otro sitio: respaldarla).

- 2026-10-12 â€” Firebase no arrancaba en el emulador (`channel-error` en `FirebaseCoreHostApi.initializeCore`): `GeneratedPluginRegistrant.java` estaba vacio (19 lineas) porque las dependencias de Flutter no estaban resueltas (avisos de `google_sign_in_android` inexistente). `flutter pub get` lo regenero (71 lineas) y `FirebaseApp initialization successful`. Si reaparece el mensaje Â«No pudimos iniciar QuantFutÂ», comprobar primero `flutter pub get` y que el registrant liste los plugins.

## 2026-10-12 â€” Conservacion y limpieza Firebase puestas en marcha en el VPS

El codigo (`firebase_mantenimiento.py`, `scripts/firebase_operations.py`) existia pero NO estaba operando: el modulo no estaba en la imagen, el usuario `qf` no tenia crontab y la carpeta de copias no existia, mientras los textos legales ya prometen 30/90 dias. Ahora: modulo en la imagen (`quantfut-api-tapjoy:20261012-mant`), crontab diario a las 03:40 UTC solo con `daily` (`deliver` sigue sin programarse: el envio automatico esta apagado), alerta por Telegram si falla y rotacion extraida a `rotate()` con pruebas. Se probo la logica de limpieza con datos ficticios en transaccion revertida y la restauracion real de una copia en una base temporal. Limite conocido: la copia es parcial (sin citext ni deny_mutation) y no sustituye un respaldo completo ni uno fuera del VPS; el camino de alerta ante fallo no se ejercito con un envio real. Un limite de la conservacion: las tablas `sessions`/`email_tokens` no se limpian aqui (estan vacias hoy).

- 2026-10-12 â€” Limpieza de sesiones y tokens de correo (`cuentas_mantenimiento`), dentro de la tarea diaria 03:40 UTC. Plazos elegidos: sesiones 30 dias tras caducar/revocar (margen para investigar `reuso_refresh`; borra IP y user-agent), tokens retirados de refresh al borrar la sesion o al pasar `REFRESH_TTL_DAYS` (la sesion tiene caducidad absoluta de 30 dias, asi que la deteccion de reuso no pierde nada; borrados antes que su sesion por la FK), tokens de correo 7 dias. No toca cuentas, suscripciones, monedas ni `admin_audit`. Probado con tablas reales + FK en transaccion revertida. Pendiente: reflejar los plazos en la politica de privacidad publicada y revisar si procede una limpieza de cuentas inactivas.

- 2026-10-12 â€” APK release firmado verificado (`apksigner`, certificado CN=QuantFut, SHA-1 ya registrado en Firebase). El release fallaba por R8: el SDK de Tapjoy referencia clases `appset` opcionales; se anadieron sus reglas oficiales en `android/app/proguard-rules.pro` + `-dontwarn` para appset. Documento: apps/mobile/docs/FIRMA_ANDROID.md. Riesgo abierto: copia unica del `.jks` en `.local/`; falta respaldo fuera del equipo y activar Play App Signing al publicar.

- 2026-10-12 â€” Firma de release cambiada por decision del titular a `C:/1. llave/llave.jks` (alias `llave`, CN=ely marine / O=NavalQuiz: identidad de otro proyecto, riesgo aceptado: comparte firma). Huellas SHA-1/SHA-256 registradas en Firebase con la CLI y `google-services.json` actualizado (cliente OAuth nuevo). APK release verificado con `apksigner`. La clave anterior `quantfut-release.jks` sigue registrada pero sus contrasenas se perdieron al sobrescribir `key.properties`. No se guardan contrasenas en el repo.

## 2026-10-12 â€” Traducciones completas de la app (es, en, pt, fr, it, de)

Decision del usuario: traducir toda la app y mantenerlo siempre al dia (regla tambien en CLAUDE.md y en la memoria). Base: `gen-l10n` (ARB), `AppLocale` persistente que funciona sin Firebase, selector de idioma (bienvenida, acceso, Perfil, Privacidad), idioma del dispositivo como sugerencia. ~450 textos de los 29 archivos alcanzables desde `main.dart`; los 60 archivos de la plantilla original y 5 de `lib/product` son codigo muerto y no se tradujeron. Decisiones clave: (1) los textos de pronostico/mercado (`texto`, `titulo`, `seleccion`, `grupo`, `nota`) se reconstruyen en la app desde `market/selection/line` + equipos (`pick_labels.dart`), sin tocar los datos sellados ni el servidor; (2) formateadores sin contexto leen el idioma de `AppLocale` y cada pantalla depende de `context.l10n` para reconstruirse al cambiar; (3) mensajes del backend por `Accept-Language` con un catalogo unico (`src/qf/api/mensajes.py`) y un manejador global de `HTTPException`: sin cabecera todo sigue en espanol; (4) pruebas que lo exigen: paridad de ARB, cero cadenas fijas (con o sin acentos), render de las 5 pestanas en los 6 idiomas con fuentes reales sin desbordes, cambio en caliente, y catalogo backend completo via `ast`. Limites: traducciones hechas por un modelo, sin revision nativa; textos legales publicos y correos de cuenta sin traducir; el backend con `mensajes.py` NO esta desplegado todavia. Detalle: apps/mobile/docs/TRADUCCIONES.md.

- Despliegue VPS 2026-10-12 (mensajes por idioma): `mensajes.py` + manejador de HTTPException + terminos/mensaje de monedas traducidos. `main.py` desplegado se PARCHEO (solo import + manejador): el local trae cambios de Parley/Alta prob. sin desplegar. Respaldos en ~/backups/mensajes-20261012; vuelta atras = imagen `quantfut-api-tapjoy:pre-mensajes-backup` (compose `image:`) + `compose up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-msg`.

- 2026-10-12 â€” Icono y arranque nativo: se reemplazo el icono Â«GoBetÂ» de la plantilla por el Â«Q.Â» verde sobre fondo oscuro de la bienvenida (no habia logotipo de QuantFut en el repo). Generado con `apps/mobile/tool/make_icon.py` (Pillow) + `dart run flutter_launcher_icons` (Android clasico y adaptable, iOS) y el fondo de `launch_background` pasa de blanco a #090f1a. Es un icono provisional con la identidad actual de la app: si el titular tiene un logotipo propio, sustituir `image/quantfut_icon*.png` y repetir el comando.

## 2026-10-12 â€” Textos legales finales

Los tres textos (tÃ©rminos, privacidad, eliminar cuenta) ya no tienen marcadores y
describen solo lo que el servidor hace: retenciÃ³n 30/90/30/7 dÃ­as, copias de 30 dÃ­as,
eliminaciÃ³n manual atendida por correo. DecisiÃ³n clave: el titular ordenÃ³ publicarlas (2026-10-12). Se desplegÃ³ solo
`legal.py` + `legal_pages/` y se parcheÃ³ el `main.py` del contenedor (import + include_router;
el local trae cambios de otras tareas sin desplegar). Respaldos en `~/backups/legal-20261012`;
vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-legal-backup` en el compose y
`up -d --no-deps api`. Imagen vigente: `quantfut-api-tapjoy:20261012-legal`. `/legal/*` da 200
desde el dominio. NO se activÃ³ Google ni se registran aceptaciones: eso sigue siendo del titular.
`REVISION_Y_PUBLICACION.md` estaba obsoleto (decÃ­a `.com` y Â«borradorÂ») y se reescribiÃ³; los
`*_BORRADOR.md` quedan como historial. Los textos legales siguen solo en espaÃ±ol.

## 2026-10-12 â€” xG de API-Football conectado al entrenamiento

DecisiÃ³n explÃ­cita del usuario: usar el xG actual de API-Football en el modelo.
La exclusiÃ³n histÃ³rica del proveedor queda revocada y documentada. La respuesta
ya llegaba a matches.stats, pero el entrenamiento leÃ­a home_xg/away_xg vacÃ­os.
Se conserva la primera pareja vÃ¡lida con origen y recepciÃ³n real, sin sobrescribir
histÃ³rico ni revisiones posteriores. Reconsulta diaria 12:10 UTC (06:10 CDMX),
35 dÃ­as, tope 100, espera 20 h y reserva del 15% de cuota. db/061 aditiva.

Punto clave: cargar xG hoy no lo vuelve disponible en una predicciÃ³n antigua.
Dixon-Coles y mÃ¡s-menos lo usan solo desde su captura; el replay secuencial de
Kalman conserva goles para esta fuente hasta soportar llegadas tardÃ­as. La
recepciÃ³n original del xG previo sigue sin acreditarse. Hash de dataset/cÃ³digo
incluye las nuevas entradas y protecciÃ³n. No se relajan puertas.

Desplegado solo en worker, sobre archivos cotejados con la versiÃ³n real, sin
reiniciar servicios. Imagen quantfut-worker:latest verificada; respaldo
quantfut-worker:xg-before-20261012 y paquete completo en
/home/qf/quantfut/deployments/xg-api-20261012. El checkout viejo del VPS no se
usa como base de reconstrucciÃ³n. API y NBA conservados.

Primera captura: 182 consultas, 149 parejas, 33 ausentes, cero errores; 13
competiciones. Entrenamiento: 49.505 filas, 148 parejas de la nueva fuente;
Sporting-Galatasaray se excluye por TurquÃ­a fuera del modelo, regla previa.
Comprobado que todas se ocultan antes de su recepciÃ³n y entran despuÃ©s.
Modelo activo 2026.09.27-010508 intacto; no se lanzÃ³ otro entrenamiento.
Cadena: 14 lotes OK; HTTPS config/home/model-card 200.

ValidaciÃ³n: 970 aprobadas, 22 omitidas y 2 advertencias; 79 pruebas dirigidas,
8 escenarios PostgreSQL temporal con rollback, 117 mÃ³dulos compilables.
Las pruebas de API necesitaron sockets locales fuera del aislamiento Windows;
la primera ejecuciÃ³n aislada se atascaba en socketpair, no en cÃ³digo del proyecto.
Detalle y cobertura: docs/xg_api_football_20261012.md; evidencia ignorada en
.local/xg_api_20261012/. Pendiente cobertura sostenida y prÃ³ximo entrenamiento.

## 2026-10-12 â€” Acceso con Google activado

Orden del titular. Tres piezas, en este orden: (1) servidor `FIREBASE_AUTH_ENABLED=1` en
`~/quantfut/docker-compose.yml` (copia previa en `~/backups/legal-20261012/docker-compose.pre-google.yml`);
(2) Remote Config `qf_google_auth_enabled=true`, `qf_terms_url` y `qf_privacy_url` apuntando a
`/legal/terminos` y `/legal/privacidad` (la app solo acepta esas dos rutas en pronosticosdeportivos.pro);
(3) el proveedor Google ya estaba habilitado en Firebase Auth.
Pruebas: `/app/v1/firebase/connect` con token falso pasÃ³ de 503 `firebase_deshabilitado` a 401
`firebase_token_invalido` (el servidor verifica contra Firebase); en el emulador la app muestra la
pantalla de acceso, el botÃ³n queda desactivado hasta aceptar y, al pulsarlo, abre el flujo de Google.
NO probado: sesiÃ³n completa con una cuenta real (el emulador no tiene cuenta y no se introducen credenciales
de Google) ni FCM. Vuelta atrÃ¡s: Remote Config `qf_google_auth_enabled=false` (apaga la pantalla al instante,
plantilla anterior en el historial de Firebase) y/o compose con `FIREBASE_AUTH_ENABLED: '0'` + `up -d --no-deps api`.

## 2026-10-12 â€” Correos de cuenta en 6 idiomas

Los dos correos propios (verificar y restablecer) estaban solo en espaÃ±ol pese a la regla de
traducciones. Las plantillas viven en `comercial/correo.py` y el idioma sale del `Accept-Language`
(la app ya lo envÃ­a) en vez de guardarse en la cuenta: no hay migraciÃ³n y funciona tambiÃ©n para
cuentas sin preferencia Firebase. El panel `/control` reenvÃ­a en espaÃ±ol (el admin no conoce el
idioma de la persona). Un idioma desconocido cae a espaÃ±ol. Desplegado con respaldo en
`~/backups/correos-20261012`; vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-correos-backup` en el
compose. Imagen vigente: `quantfut-api-tapjoy:20261012-correos`. Las pÃ¡ginas web a las que llevan los
enlaces siguen en espaÃ±ol (lÃ­mite documentado en `TRADUCCIONES.md`).
Se marcaron como hechos cuatro pendientes de idioma/FCM que ya estaban implementados y sin tildar.

## 2026-10-12 â€” Entrenamiento con el nuevo xG iniciado

El usuario pidiÃ³ ejecutar el entrenamiento y recibir aviso al terminar.
VersiÃ³n 2026.10.12-221104 lanzada en el worker a las 22:11:04 UTC / 16:11 CDMX:
49.504 partidos, 148 parejas xG de API-Football, 11 ligas + 2 copas, validaciÃ³n
completa de 365 dÃ­as y puertas habituales. No se amplÃ­an ligas ni se fuerza
activaciÃ³n: el modelo 2026.09.27-010508 permanece activo durante el cÃ¡lculo.
La nueva fuente entra en el ajuste final y se oculta en cortes anteriores a
su captura; no atribuirle mejora retrospectiva en el backtest.

Proceso desacoplado de SSH, prioridad reducida y un hilo por biblioteca.
Snapshot del input y fuentes, log, estado con seÃ±al de vida cada 30 s y resultado
final en /srv/quantfut/artifacts/training-runs/xg-2026.10.12-221104/.
A las 22:15 UTC: proceso vivo, primer ajuste histÃ³rico, sin errores registrados;
/model-card interno y pÃºblico 200. Una consulta urllib desde VPS al dominio
recibiÃ³ 403; desde este equipo con User-Agent de navegador dio 200.

AutomatizaciÃ³n heartbeat resultado-del-entrenamiento-con-xg creada y verificada
en este chat, cada 15 min: avisar resultado/fallo, verificar registro/artefactos,
actualizar documentaciÃ³n y detener seguimiento; silencio mientras sigue.
El equipo y Codex deben estar encendidos para el seguimiento, no para el cÃ¡lculo
remoto. Comprobaciones obligatorias inicial y final: 972 aprobadas, 22 omitidas,
2 advertencias. DocumentaciÃ³n: docs/entrenamiento_xg_20261012.md.
El entrenamiento sigue en curso; todavÃ­a no hay mÃ©tricas nuevas ni promociÃ³n.

## 2026-10-12 â€” Sentry instalado (errores)

Orden del titular. Dos proyectos en la organizaciÃ³n `saptain`: `quantfut-api` (FastAPI, tambiÃ©n
recibe los trabajos del worker) y `quantfut-app` (Flutter). Decisiones, todas por privacidad:
solo errores (sin tracing/replay/logs); el backend maneja tokens y claves en URLs, asÃ­ que
`src/qf/observabilidad.py` apaga PII, cuerpos, variables locales, SQL y migas de pan, y limpia
cabeceras/cookies/query/usuario/`sys.argv` antes de enviar (pruebas en `tests/test_observabilidad.py`).
Se inicia desde `qf/__init__.py` para cubrir API y todos los `python -m qf...` del cron; sin
`SENTRY_DSN` no hace nada. El DSN vive solo en el `.env` del servidor.
App: Sentry se inicia Ãºnicamente si el diagnÃ³stico estÃ¡ activado (mismo consentimiento que
Crashlytics) y se cierra al retirarlo; no basta un `beforeSend` porque los fallos nativos se
capturan antes que Dart. Texto del interruptor actualizado en los 6 idiomas y polÃ­tica de
privacidad (Sentry como encargado; publicada en `/legal/privacidad`).
Coste: `sentry_flutter` 10 exige Android 8.0, asÃ­ que `minSdk` sube de 24 a 26 (la 9.x no compila
con AGP 9). Desplegado en la API (imagen `quantfut-api-tapjoy:20261012-sentry`, respaldos en
`~/backups/sentry-20261012`, vuelta atrÃ¡s = `pre-sentry-backup`) y en el worker (pip + archivos +
`/etc/environment`, sin recrearlo; `~/quantfut/{requirements.txt,src}` actualizados para el prÃ³ximo
build). Verificado: evento `QUANTFUT-API-1` desde la API y `-2` (excepciÃ³n no capturada) desde el worker.
No verificado: la app en un dispositivo (exige consentimiento y sesiÃ³n de Google).

## 2026-10-12 â€” Â«SesiÃ³n no vÃ¡lidaÂ» tras entrar con Google

Causa: `api/mobile.py` usaba `request: Request` en `member()` sin importar `Request`. Con
`from __future__ import annotations`, FastAPI no resolvÃ­a el tipo y trataba `request` como un
parÃ¡metro de consulta siempre vacÃ­o, asÃ­ que la rama `X-QF-Identity: firebase` nunca se activaba
y el ID token de Google se validaba como sesiÃ³n clÃ¡sica: 401 en todo `/mobile/v1/*` con sesiÃ³n.
PasÃ³ desapercibido porque `connect`/`preferences` (otro mÃ³dulo, sÃ­ importa `Request`) funcionaban.
RegresiÃ³n cubierta en `tests/test_mobile_identidad_firebase.py`. Desplegado en la API (respaldo
`~/backups/mobile-identidad-20261012`, vuelta atrÃ¡s = imagen `pre-mobile-identidad-backup`).
LecciÃ³n: un `Request` sin importar no da error al arrancar; revisar esto en endpoints nuevos.
El registro de rechazos de identidad aÃ±adido en `api/firebase.py` se queda (aviso WARNING).

## 2026-10-12 â€” ElecciÃ³n de idioma como primera pantalla

Pedido del titular (captura de referencia con globo animado y cuadrÃ­cula de 6 idiomas).
`LanguageSelectionScreen` (`lib/l10n/language_selection_screen.dart`) sale solo la primera vez:
`QuantFutApp.home` la muestra mientras `AppLocale.chosen` sea falso y la app pasa sola al flujo
normal al elegir (ya escucha `AppLocale`), asÃ­ que no se tocÃ³ el acceso con Google ni Firebase.
Quien actualiza la app la verÃ¡ una vez, porque su idioma nunca se guardÃ³ como Â«elegidoÂ».
AnimaciÃ³n dibujada en cÃ³digo (CustomPainter + controladores), sin dependencias: respeta Â«reducir
animacionesÂ». Referencias consultadas, sin copiar cÃ³digo: `gskinner/flutter_animate` (BSD-3) y
`flutterfx/flutterfx_widgets` (sin licencia). La etiqueta de la captura (Â«Neural interface
configurationÂ») se cambiÃ³ por Â«ConfiguraciÃ³n de idiomaÂ» y los textos van en los 6 idiomas.
No verificado visualmente en emulador (se interrumpiÃ³ el reinicio): compararlo con la captura.

## 2026-10-12 â€” Una sola tarjeta destacada por partido

Antes el detalle pintaba una tarjeta verde por cada pronÃ³stico (una por mercado) con chips para
filtrar. Ahora `featuredPick` (`live_forecast.dart`) elige UNA: la de mayor probabilidad y, si
empatan, la de cuota mÃ¡s alta (decisiÃ³n del titular entre tres reglas; la cuota mÃ¡s alta y
probabilidad Ã— cuota quedaron descartadas). Se quitaron los chips, que ya no filtran nada; el resto de
mercados sigue en la tabla Â«Mercados del partidoÂ». Es lÃ³gica del cliente: el servidor no cambia.

## 2026-10-12 â€” Alta probabilidad muestra solo 73-95 %

Pedido del titular: el apartado solo muestra pronosticos de mas de 73 %. Revierte la ampliacion
del 11-oct (62-95 %). Es un FILTRO DE LECTURA (`HIGH_MIN` en `api/mobile.py`): `alta_prob_ext`
sigue sellando candidatos desde 62 % y sus filas inmutables no se tocan, solo dejan de mostrarse
(cambiar `PROB_MIN_EXT` alteraria el sellado y se haria solo si el titular lo pide). Efectos: el
historial y el acierto mostrados pasan a calcularse solo sobre >=73 % (mismo filtro) y la pantalla
VIP ya leia el rango del servidor. El texto del apartado (`picksRangeHint`) ahora recibe el rango
del servidor en vez de tenerlo escrito en 6 idiomas. Desplegado con respaldo
`~/backups/alta-73-20261012` (vuelta atras = imagen `pre-alta73-backup`); la app instalada filtra
bien sin APK nuevo, pero su texto dira Â«62-95 %Â» hasta actualizarla.

## 2026-10-12 â€” Reto Escalera rediseÃ±ado (tarjetas de avance)

Pedido del titular: diseÃ±o ergonÃ³mico, % de avance, cuÃ¡nto falta, si el reto sigue vivo, probabilidad
de cumplirse e historial. Una tarjeta por reto (`lib/product/live_ladder.dart`): anillo de avance,
barra con un tramo por escalÃ³n (verde ganado, Ã¡mbar en juego), estado Â«En juegoÂ» / Â«Por elegirÂ»,
probabilidad estimada, saldo como MULTIPLICADOR (Ã—1,56, decisiÃ³n del titular: sin cantidades) y
escalones liquidados plegados. Orden: primero el que tiene un escalÃ³n en juego, luego el mÃ¡s avanzado.
Historial: tarjeta pequeÃ±a con cumplidos Y fallidos (decisiÃ³n del titular, por honestidad de la tasa);
hoy estÃ¡ vacÃ­o (0 retos cerrados) y muestra un estado vacÃ­o.
La probabilidad es una ESTIMACIÃ“N (`ladder_progress.dart`): escalÃ³n en juego (si es visible) Ã— la media
de probabilidad de los escalones liquidados elevada a los que faltan; la media viene del servidor
(`escalones.prob_media`, 79,1 % con 9 escalones) y solo se usa con â‰¥5 escalones, si no se asume el 73 %
medido en `publish/escalera.py`. La tarjeta lo dice (Â«EstimaciÃ³n â€¦ No es una garantÃ­aÂ»). Todo sale de
datos que el servidor ya entrega: sin cambios de backend ni despliegue. Referencias sin copiar cÃ³digo:
SandroMaglione/step-progress-indicator (MIT), JHBitencourt/timeline_tile (MIT), flutter_percent_indicator
(BSD-2); `InlitX/streak` es GPL-3.0 y se descartÃ³.

## 2026-10-12 â€” Predicciones: menÃº, Alta probabilidad y Parley rediseÃ±ados

Pedido del titular (misma lÃ­nea que el Reto Escalera). MenÃº superior (`predictions_switcher.dart`):
pÃ­ldora con indicador que se desliza, icono + texto + contador (pronÃ³sticos abiertos y retos en marcha),
fijo arriba al hacer scroll; se cambia de secciÃ³n tocando o DESLIZANDO el dedo (decisiÃ³n del titular).
Alta probabilidad (`live_picks.dart`): tarjeta de acierto histÃ³rico real frente al prometido (hoy 80,9 %
sobre 141), pronÃ³sticos abiertos agrupados por dÃ­a con la etiqueta Â«Mayor probabilidadÂ» en el primero
(misma regla que la tarjeta Ãºnica del detalle) y los de candado AGRUPADOS en una sola tarjeta plegable
(decisiÃ³n del titular: habÃ­a 54 candados casi idÃ©nticos ahogando a 5 gratuitos). Los nombres de liga
salen de `league_names.dart` (el payload solo trae el id; es un dato, no se traduce).
Parley (`live_parley.dart`): boleto con muescas, patas en lÃ­nea de tiempo, reglas en una lÃ­nea con â“˜
que abre una hoja, y estados vacÃ­os (sin parlays / sin historial). Todo con datos que el servidor ya
entrega: sin cambios de backend. Referencias sin copiar cÃ³digo: splashbyte/animated_toggle_switch (BSD-3),
hadukin/custom_sliding_segmented_control (MIT), fathialamre/ticketcher y FazalHussain/Ticket-UI-Widget (MIT).
`product_navigation_test` y `live_parley_test` se actualizaron: ya no hay un botÃ³n por candado y las
reglas largas viven en la hoja.

## 2026-10-12 â€” Tapjoy: no mostrar HTML de errores en Coins

El puente reenviaba TJError.message y Flutter lo mostraba completo dentro del SnackBar: un fallo del SDK podÃ­a cubrir la pantalla con HTML. Ahora el canal solo transmite cÃ³digos estables y el cÃ³digo numÃ©rico del SDK; la app presenta avisos en es/en/pt/fr/it/de, permite reintentar y bloquea solicitudes duplicadas. Activity en connect, apertura en el hilo principal, Ã©xito al mostrarse contenido y lÃ­mite de 45 s. SDK 14.8.0 por mejoras oficiales de contenido web/interfaz, sin atribuirle una soluciÃ³n especÃ­fica no documentada. 16 pruebas Flutter y anÃ¡lisis correctos, arnÃ©s final 977/24. CachÃ© Pub incompleta restaurada. La apertura real sigue pendiente: BlueStacks no ofreciÃ³ logs dentro del lÃ­mite y hubo interacciÃ³n concurrente del usuario. Detalle: apps/mobile/docs/TAPJOY_ERROR_HTML_20261012.md.

APK corregido release compilado, SDK/cÃ³digos verificados dentro del archivo y firma v2 coincidente con distribuciÃ³n vigente; entregable `.local/artifacts/QuantFut-ofertas-corregidas-20261012.apk` (74,1 MB). No instalado ni acreditada apertura real en la cuenta del usuario.

## 2026-10-12 â€” Entrenamiento xG terminado; candidato no activado

2026.10.12-221104 terminÃ³ a las 20:55:22 CDMX (13-oct, 02:55 UTC), tras
4 h 44 min 18 s: 49.504 partidos, 148 parejas nuevas xG y 13 competiciones.
Se ejecutaron todas las etapas, 12 ajustes histÃ³ricos (una ventana mensual
sin test), ajuste final y puertas existentes. El candidato quedÃ³ registrado
inactivo: en los mismos 1.051 partidos, RPS DC 0,19873 frente a Elo 0,19657
y mercado 0,19147; log-loss 0,98694 / 0,98686 / 0,96547. Menor es mejor.
El veto es no superar Elo; champion de ventana distinta no comparable y la
puerta comercial sigue cerrada (clv_report de este pipeline n=0, mÃ­nimo 300;
no confundir con las capturas de otros informes sharp). CalibraciÃ³n aprobada
no anula el veto del modelo base. Modelo activo conservado 2026.09.27-010508.

La nueva fuente estÃ¡ incorporada en el artefacto candidato, no en el modelo
activo: carga con mezcla xG 0,65 y las 148 parejas disponibles en el corte
final 13-oct 02:32:16 UTC. Su backtest no acredita mejora retrospectiva por
xG capturado hoy. No se fuerza promociÃ³n ni se reinicia entrenamiento.

Resultado, fila model_artifacts y mÃ©tricas cotejados. Recalculado el hash del
dataset desde training_input.pkl con la configuraciÃ³n registrada; fuentes
copiadas coinciden con el hash inicial. Diez artefactos comprobados y hashes
registrados; /model-card interno/pÃºblico 200. Evidencia local completa en
.local/xg_api_20261012/training-2026.10.12-221104/: completion-audit.json,
artifact-verification.json y result.json/status.json/training.log exactos,
con hashes iguales al VPS. Actualizadas documentaciÃ³n y tareas.
AutomatizaciÃ³n resultado-del-entrenamiento-con-xg detenida (PAUSED) conforme
a la orden de avisar al finalizar; sin cambios de cÃ³digo ni puertas.

## 2026-10-12 â€” Tapjoy abierto en BlueStacks tras registro de prueba

La segunda captura conservaba el fallo de carga pese a ocultar el HTML. Registro Android: `no_currency`; Unity: moneda Monedas activa, Coins vinculada a esa moneda y coins_offerwall, SDK coincidente. Cuenta aÃºn en revisiÃ³n/app no activa sin tienda; cero dispositivos de prueba. Se registrÃ³ BlueStacks QuantFut con permiso explÃ­cito para enviar su ID publicitario a Unity. Registro confirmado y apertura en la sesiÃ³n actual verificada visualmente: Earn Rewards, Tapjoy Test CPA, 7 monedas. No se completÃ³ oferta ni se acreditaron monedas. La apertura de pruebas queda resuelta; aprobaciÃ³n/comercial y callback real siguen pendientes. Sin nuevos cambios de cÃ³digo o APK.

## 2026-10-12 â€” Coins rediseÃ±ado y aviso de monedas insuficientes

Pedido del titular (referencia: capturas de otra app de recompensas). Se adaptÃ³ la FORMA, no su
contenido: no hay cobro en dinero (las monedas no tienen valor monetario, dicen los tÃ©rminos), ni
marcadores Â«en vivoÂ» de otros usuarios, ni Â«2Ã—Â»/temporizadores inventados, ni juegos de terceros. La
cuenta atrÃ¡s es real (reinicio de la asistencia a las 00:00 UTC).
`live_rewards.dart`: saldo con anillo de avance hacia el desbloqueo, asistencia de 7 dÃ­as con el de hoy
resaltado y botÃ³n con las monedas de hoy, ofertas como UNA tarjeta del proveedor listo (Tapjoy) y los 5
sin activar en una lÃ­nea Â«PrÃ³ximamenteÂ» (antes 5 tarjetas muertas), invitaciÃ³n con cÃ³digo copiable,
historial con 5 movimientos y Â«Ver mÃ¡sÂ», tÃ©rminos plegados y lluvia de monedas al reclamar
(`coin_burst.dart`, respeta Â«reducir animacionesÂ»). Base oscura con acentos vivos (morado, dorado,
rosa), decisiÃ³n recomendada y aprobada con Â«hazloÂ».
Bug corregido: la racha mostrada era el nÃºmero guardado aunque se hubiera roto; ahora se calcula con la
fecha real UTC (`rewards_progress.dart`, misma regla que el servidor).
Cuando faltan monedas al desbloquear, el servidor responde 409 con `code: monedas_insuficientes` (antes
solo texto traducido) y la app ofrece Â«Ganar monedasÂ» en vez de un error. Desplegado en la API con
respaldo `~/backups/coins-409-20261012` (vuelta atrÃ¡s = imagen `pre-coins409-backup`); la app antigua
sigue funcionando (muestra el texto de siempre).
Tapjoy: segÃºn la documentaciÃ³n de Unity Grow, el SDK de Flutter solo muestra el placement entero
(`TJPlacement.requestContent/showContent`); no hay forma documentada de pintar las ofertas una a una en
la propia pantalla. Lo personalizable es la tarjeta de contenido del panel (moneda, icono, colores,
tasa), Message to Earn y los placements contextuales.

## 2026-10-12 â€” Inicio ya no enseÃ±a partidos terminados

Pedido del titular: un partido que acaba sale de la app y queda en los registros histÃ³ricos. Se filtra en
el SERVIDOR (`visible_agenda` en `api/mobile.py`, solo la agenda de `/mobile/v1/home`) para que la app ya
instalada lo tenga sin actualizarse, y otra vez en la app (`calendar()`), por si llega una agenda sin
filtrar. Se quita todo `estado == 'finished'`; los de en juego y los por jugar siguen. La web y las demÃ¡s
rutas de fichas no cambian. Medido en producciÃ³n antes/despuÃ©s con `fecha=2026-10-12`: 41 partidos (25
terminados) â†’ 16, todos por jugar. Consecuencia a vigilar: en un dÃ­a pasado Inicio queda vacÃ­o, porque
todos sus partidos ya terminaron; los resultados siguen en los pronÃ³sticos liquidados y en las
estadÃ­sticas del partido. Desplegado con respaldo `~/backups/agenda-sin-terminados-20261012`
(vuelta atrÃ¡s = imagen `pre-agenda-backup`).

## 2026-10-12 â€” PestaÃ±a Â«AlertasÂ» en el anÃ¡lisis del partido (fase 1, sin IA)

Pedido del titular (referencia: pestaÃ±a de alertas de otra app). Fase 1 decidida con Ã©l: datos REALES y
verificables, sin modelo de lenguaje. Se apoya en lo que ya existÃ­a: `ficha.bajas` (API-Football
`/injuries`, Ãºltima comprobaciÃ³n, ver `fichas._bajas` e `ingest/injuries.py`). No se tocÃ³ el servidor.
`live_alerts.dart` + `alerts_model.dart`: por equipo, Â«DesventajaÂ» = sus bajas y Â«VentajaÂ» = las del rival
(como en la referencia); tarjeta con iniciales, motivo traducido (se agrupa el texto en inglÃ©s del
proveedor y lo que no encaja se muestra TAL CUAL, nunca se inventa un motivo), estado No disponible /
Duda / Sancionado, fuente y hora de la comprobaciÃ³n. Selector de equipo con escudo, indicador que se
desliza, cambio por deslizamiento, entrada escalonada (respeta Â«reducir animacionesÂ») y contador de
bajas en la pestaÃ±a. El estado va siempre en rojo/Ã¡mbar (hecho del jugador); solo el borde marca la
secciÃ³n, para que Â«No disponibleÂ» no se lea como algo bueno en la secciÃ³n de Ventaja.
Sin comprobaciÃ³n (`bajas` nulo) se dice que NO equivale a Â«sin lesionadosÂ»: hay ligas sin cobertura del
proveedor (Championship, Liga Profesional, SÃ©rie B hoy; ver README) y para esas es dato ausente.
No hay foto del jugador (no se guarda ni se sirve). Pendiente, solo si el titular lo pide: fase 2 con IA
(resumen de prensa con citas, aparte de los datos oficiales) y retirar la lista de bajas duplicada de la
pestaÃ±a H2H.

## 2026-10-12 â€” Â«Datos del partidoÂ» en AnÃ¡lisis (la pestaÃ±a EstadÃ­sticas pasa a llamarse AnÃ¡lisis)

Pedido del titular: una tarjeta como la de la referencia, justo debajo de Â«Probabilidad de victoria 1X2Â»,
y la pestaÃ±a EstadÃ­sticas renombrada a AnÃ¡lisis. Solo datos comprobables: Ãºltimo resultado de cada equipo
(y el de la competiciÃ³n si es otro partido), ÃšLTIMO once conocido con su fecha y rival (nunca un Â«once
probableÂ»: lo dice la propia tarjeta), y el resumen de bajas con acceso a la pestaÃ±a Alertas. Lo que falta
se dice (Â«AÃºn no hay una alineaciÃ³n guardadaÂ», Â«Sin partidos previos registradosÂ»). Lo narrativo de la
referencia (Â«perfil de la previa apunta a un juego abiertoâ€¦Â») queda para la fase 2 con IA, si se aprueba.
Servidor: `fichas._ultimo_once` aÃ±ade `ultimo_once` por equipo (Ãºltimo partido terminado con alineaciÃ³n,
de `lineups` o `lineups_historicas`); es un campo NUEVO, compatible con la web y la app anterior.
Verificado en producciÃ³n: Lens 3-4-2-1 vs Lyon (9-oct) y Sporting CP 4-2-3-1 vs SC Braga, 11 titulares cada
uno. Desplegado con respaldo `~/backups/ultimo-once-20261012` (vuelta atrÃ¡s = imagen `pre-once-backup`).
Decidido NO incluir el estadio: la base no guarda sede por partido (harÃ­a falta una columna nueva y
cambiar la captura del calendario). La cobertura del once depende de las alineaciones guardadas (desde
finales de septiembre mÃ¡s el histÃ³rico): un equipo sin ninguna lo muestra como ausente.

## 2026-10-12 â€” Pantalla de acceso rediseÃ±ada (carrusel + tarjeta con Google) y fuera la presentaciÃ³n posterior

DecisiÃ³n: la pantalla de acceso pasa a ser un carrusel de 5 diapositivas con ilustraciones dibujadas en
cÃ³digo (no capturas reales: no envejecen ni prometen cifras) y una tarjeta fija abajo, a la altura del
pulgar, con el botÃ³n oficial de Google y el consentimiento (mayor de 18 + tÃ©rminos + privacidad) con los
enlaces dentro de la frase. El botÃ³n de Google ya no se apaga sin casilla: se deja pulsar, la casilla
vibra y se explica quÃ© falta (un botÃ³n gris sin motivo es peor ergonomÃ­a). Los textos del carrusel no llevan
cifras ni promesas de resultado (solo lo que la app hace). Se retira la presentaciÃ³n `SecondScreen` que salÃ­a
tras el acceso: quien entra con Google va directo al producto (`onboarding_done` ya no se lee).
CÃ³digo en `lib/core/access_screen.dart` (no conoce Firebase; la puerta de acceso le pasa estado y acciones) y
`lib/core/access_illustrations.dart`; dependencia nueva `flutter_svg` solo para la Â«GÂ» de 4 colores. 20 textos
nuevos en los 6 idiomas. Por debajo de 700 px de alto la pantalla se desplaza en vez de apretar el texto.
Pruebas: `test/access_screen_test.dart` (14, incluye 6 idiomas a 390 y 320 px). Suite: 177 verdes. Sin cambios
de servidor ni despliegue.

## 2026-10-13 â€” Inicio rediseÃ±ado: agenda por dÃ­a, boletos del dÃ­a y menÃº Â«MÃ¡sÂ» con guÃ­a

Pedido del titular (capturas de QuantFut y de WIN Betting): quitar los atajos Â«Alta probabilidad / Reto
EscaleraÂ» y los filtros Â«+48 h, +1 hâ€¦Â» del Inicio, un calendario mÃ¡s visual y los partidos agrupados por dÃ­a en
orden cronolÃ³gico; del diseÃ±o de referencia, resumen, boletos y un menÃº con ventanas nuevas. Repos usados como
referencia de patrÃ³n (no como dependencia): `easy_date_timeline` (tira de dÃ­as) y `sticky_grouped_list`
(encabezados por dÃ­a con salto). Lo que NO se copia de la referencia: oferta con cuenta atrÃ¡s, Â«1.000.000+
apostantesÂ», Â«Seguro/Medio/ArriesgadoÂ» y el Â«84 % de aciertoÂ» fijo: serÃ­an cifras inventadas. El aviso superior es
el de Remote Config que ya existÃ­a (cerrable), no una oferta nueva.
Decisiones: (1) el servidor manda 7 dÃ­as (`mobile.DIAS_AGENDA`, antes 2) y la app agrupa por dÃ­a local; la app
anterior sigue funcionando (filtra por su cuenta). Desplegado con respaldo `~/backups/agenda7-20261013` (vuelta
atrÃ¡s = imagen `quantfut-api-tapjoy:pre-agenda-backup`). (2) La tira de 7 dÃ­as queda FIJA arriba y el dÃ­a activo
sigue al desplazamiento; tocar un dÃ­a salta a sus partidos y un dÃ­a sin partidos avisa. Los encabezados de dÃ­a no
son fijos: con una lista de hasta ~85 partidos por dÃ­a, una tira fija es mÃ¡s Ãºtil que dos barras fijas. (3) Se
quitan Alta probabilidad y Reto Escalera del Inicio (viven en Predicciones; quedan como tarjetas de Â«Boletos del
dÃ­aÂ» con el pronÃ³stico de mayor probabilidad y el parley). (4) Resumen con datos reales: saldo de monedas
(`/mobile/v1/rewards`) y acierto histÃ³rico real de Alta probabilidad; sin historial liquidado no se enseÃ±a la
tarjeta. (5) MenÃº Â«MÃ¡sÂ» (hoja inferior): guÃ­a de pronÃ³sticos (6 temas, sin promesas de ganancia), evaluar la app
(ficha de la tienda; no abrirÃ¡ nada hasta que la app estÃ© publicada), compartir (hoja del sistema; dependencia
`share_plus`) y tÃ©rminos/privacidad. El buscador pasa a un icono de la tira para ganar sitio.
CÃ³digo: `home_agenda.dart` (agrupar, tira, fila de partido), `live_home.dart`, `live_more.dart`, `live_guide.dart`;
42 textos nuevos en 6 idiomas. Pruebas: `home_screen_test.dart` (19) y las de navegaciÃ³n/idiomas actualizadas;
suite 196 verdes. LecciÃ³n: `dart format lib/product` reformateÃ³ archivos ajenos; se restauraron con `git checkout`
(formatear solo archivos propios).

## 2026-10-13 â€” El pronÃ³stico se calcula cada dÃ­a a las 03:00 de MÃ©xico (09:00 UTC)

Pedido del titular: el calendario se ve 7 dÃ­as, pero un partido solo tiene probabilidad el mismo dÃ­a en que se
calcula; antes la app enseÃ±a el partido con candado y la hora. Hora elegida por el titular tras comparar
(03:00 / 04:00 / 05:00 / 07:00 MX): las 03:00 cubren casi todos los kickoffs europeos de mediodÃ­a el mismo dÃ­a
(Serie A 12:30 CEST = 04:30 MX, Premier 12:30 BST = 05:30 MX), con los datos del dÃ­a ya capturados (calendario
05:15 UTC, clasificaciÃ³n 06:40, resultados 06:45, lesiones 08:00) y ~3 h de margen para arreglar un fallo antes
de que se despierten los usuarios de MÃ©xico. Coste: el precio de mercado usado tiene 2 h mÃ¡s que a las 05:00.
Regla (`src/qf/publish/ventana.py`): un partido pertenece a la corrida de las 03:00 de su dÃ­a de MÃ©xico; si
empieza antes de las 03:00 + 60 min (sin tiempo para sellar) pertenece a la del dÃ­a anterior. MÃ©xico es UTC-6 fijo
(sin horario de verano desde 2022). Mismo corte en TODOS los generadores â€”`daily` (predicciones y Â«solo sharpÂ»),
alta probabilidad, alta ext., escalera y parleyâ€”, siempre con tope en su horizonte propio: la ventana solo se
recorta, nunca se amplÃ­a. El servidor aÃ±ade `pronostico_desde` (UTC) a cada partido de la agenda; la app pinta el
candado solo si no hay probabilidad y esa hora aÃºn no llegÃ³ (si ya pasÃ³ y sigue sin dato, no finge un candado: son
ligas sin modelo). La hora de MÃ©xico que enseÃ±a la app sale de ese dato (UTC-6), no de una constante propia.
NO se cambiÃ³ el orden predecir â†’ seleccionar â†’ sellar â†’ publicar ni ningÃºn trigger. Aviso de transiciÃ³n: la corrida
de las 13:00 UTC de hoy ya usÃ³ la ventana antigua de 36 h; desde maÃ±ana 09:00 UTC rige la nueva. `prediction_batches`
sigue indexado por fecha UTC (09:00 UTC es el mismo dÃ­a UTC que antes).
CorrecciÃ³n de lo dicho antes al titular: el xG de API-Football solo alimenta el entrenamiento y el modelo no usa
lesiones, asÃ­ que NO hacÃ­a falta mover esas capturas (se dejaron como estaban, incluida la del xG de otra sesiÃ³n).
Desplegado en api y worker con respaldo `~/backups/ventana-20261013` (vuelta atrÃ¡s = imÃ¡genes `pre-ventana-backup`
de `quantfut-worker` y `quantfut-api-tapjoy`, y el crontab respaldado). Pruebas: `tests/test_ventana_pronostico.py`
(13) + suite Python completa (972) y Flutter (197).

## 2026-10-13 â€” IntegraciÃ³n xG y resultado preparados para commit

ComprobaciÃ³n actual antes de guardar esta integraciÃ³n: 994 pruebas aprobadas,
24 omitidas y 2 advertencias. El commit incluye la captura de la primera pareja,
protecciÃ³n temporal, migraciÃ³n, pruebas y resultado del candidato rechazado.
Se conservan sin incluir los cambios concurrentes de Tapjoy y de la app.

## 2026-10-13 â€” Cambios pendientes de Tapjoy preparados para commit

Orden del titular: guardar los cambios restantes. Puente Android con cÃ³digos
seguros (sin HTML del SDK), exclusiÃ³n de aperturas simultÃ¡neas, espera de 45 s
y SDK 14.8.0; documentaciÃ³n del diagnÃ³stico y apertura de prueba conservada.
La apertura de pruebas ya estÃ¡ confirmada, pero aprobaciÃ³n y acreditaciÃ³n
comercial siguen pendientes. ComprobaciÃ³n actual: 16 pruebas Flutter aprobadas
y :app:compileReleaseKotlin correcto. Se restauraron las cachÃ©s Pub/Maven que
faltaban, con pub get --enforce-lockfile; pubspec y lock permanecen iguales.
Se excluyen .venv-api, cachÃ© Kotlin y build Android; el informe HTML generado
sale del Ã­ndice, conservado en disco. No se instala APK ni se modifican claves.

## 2026-10-13 â€” Un pronÃ³stico gratis abre tambiÃ©n los marcadores mÃ¡s probables del partido

Pedido del titular (captura del detalle de Lensâ€“Sporting): un pronÃ³stico gratis debe ir completo. Hoy la fila del
pronÃ³stico, su dictamen y su cuota ya iban abiertos; lo Ãºnico suyo que seguÃ­a con candado eran los Â«marcadores mÃ¡s
probablesÂ». Alcance elegido por el titular: SOLO el pronÃ³stico gratis completo; los demÃ¡s mercados del partido
(Resultado, Doble oportunidadâ€¦) siguen siendo VIP, que es el contenido de pago. Cambio solo de servidor
(`partido_mercados.aplicar_acceso`): hay marcadores si el usuario es VIP o si tiene algÃºn pronÃ³stico abierto del
partido (gratis o desbloqueado con monedas). Revierte la regla anterior Â«marcadores solo con VIPÂ» (la prueba
`test_locked_rows_reveal...` la fijaba y se actualizÃ³; nueva prueba: sin pronÃ³stico abierto ni VIP no hay marcadores).
Verificado en producciÃ³n: partidos con pronÃ³stico abierto devuelven 5 marcadores sin ser VIP. Desplegado con respaldo
`~/backups/marcadores-20261013` (vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-marcadores-backup`). No hace falta
APK nuevo: la app ya dibuja los marcadores cuando llegan.

## 2026-10-13 â€” Parley: un Ãºnico parley del dÃ­a no es gratis

La app mostraba todos los parlays porque el reparto gratis/VIP (`api/parley_acceso.py`) solo existÃ­a en local: el VPS sigue con `/parley` pÃºblico sin filtro (comprobado: el contenedor de la API no trae `parley_acceso.py`). DecisiÃ³n del usuario: un parley gratis por dÃ­a y, si el dÃ­a trae uno solo, ninguno gratis (con uno solo no hay "resto" que vender; el liquidado se sigue viendo siempre). Regla en `aplicar_acceso`: `gratis = None` si `len(tickets) <= 1`. Desplegado en el VPS (api) con respaldo `~/backups/parley-20261013` (vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-parley-backup` en el compose + `up -d --no-deps api`). Imagen nueva = la anterior + `main.py` y `parley_acceso.py`; el `main.py` del contenedor diferÃ­a del local solo en `/parley`. Verificado en producciÃ³n sin cuenta: hoy 1 parley abierto (escalÃ³n 1, gratis) y 4 bloqueados. Sin APK nuevo.

## 2026-10-13 â€” Cobertura fÃºtbol: archivo disponible y ZenRows comprobado

El usuario pidiÃ³ viabilidad de xG, XI, bajas y estadÃ­sticas para 12 ligas sin
modelo y huecos de las 13 habilitadas. Se comprobÃ³ la base actual (interruptores
false y conteos citados), pero el dato pendiente estÃ¡ en buena parte archivado:
FotMob 2024-01-01 a 2026-10-03, 22.461 filas, 22.456 originales verificados.
Hashes y normalizador cotejados: 3 originales faltantes Championship y 2 fechas
inconsistentes Brasil A excluidos. Las 12 ligas tienen 7.701 parejas xG,
10.524 partidos con ambos XI vÃ¡lidos y 10.466 con estadÃ­sticas de ambos equipos.
Campos de bajas presentes en 6.013 partidos; no se acredita exhaustividad ni
publicaciÃ³n previa al kickoff. Chile 662 resultados/XI, sin xG; Brasil B 1.066
resultados/XI y 686 xG. Copas: 425 UCL/441 UEL con xG, XI y estadÃ­sticas.
Argentina/MX/Primeira tambiÃ©n tienen bajas declaradas en el archivo, pese al
vacÃ­o de API-Football. No se mezclan universos ni se atribuyen eventos nuevos
antes de emparejar con las identidades existentes.

Prueba SofaScore por cuenta ZenRows existente: cuatro GET correctos, reserva
100, incremento observado 20 crÃ©ditos (1804â†’1824). Southampton-Portsmouth,
16391229, Championship/18: xG 1,28/1,18; 22 titulares, 40 fichas/29 jugadores
con minutos positivos, 6 bajas visitantes. Recibos y hashes verificados. Un
primer arranque MCP fallÃ³ antes de consultar; segundo correcto. Repo fijado
dd9f061be2c64f01a6d3a50fb34d55a102d7107b: PolyForm Noncommercial real comprobada
por API ref fijo, pese a raw main en cachÃ© que daba MIT; piloto con adaptador
propio, sin integrar ese cÃ³digo restringido. No se declara quÃ© IP usÃ³ el servicio.

DecisiÃ³n: reutilizar primero el archivo existente; completar con consultas
acotadas tras medir cobertura por liga. PrÃ³xima integraciÃ³n necesita matching
estricto y extender la protecciÃ³n xG (hoy explÃ­cita para api_football) a las
nuevas fuentes; disponibilidad real del 3-oct no acredita datos en backtests
anteriores. MÃ¡s datos no equivalen a superar Elo. Cero importaciones, compras,
API-Football/Odds API nuevas, cambios de flags, cron o modelo. ArnÃ©s antes:
995/24; despuÃ©s: 996/24, dos advertencias. Informe:
docs/futbol_scraping_viabilidad_20261013.md. Evidencia:
.local/football_scraper_20261013/; originales antiguos intactos.

## 2026-10-13 â€” Detalle del partido sin modelo de goles: los VIP se avisan aparte del gratuito

En partidos de ligas sin modelo propio (p. ej. Championship) `ficha.mercados` salÃ­a `None` (`partido_mercados.construir` exige lambdas de goles; el `fit` de un pronÃ³stico de cÃ³rners solo trae lambdas de cÃ³rners) y la pestaÃ±a PronÃ³sticos mostraba el banner Â«tiene un pronÃ³stico VIPÂ» sin nada que lo respaldara debajo. SoluciÃ³n provisional hasta que exista modelo: `partido_mercados.solo_candados` devuelve candados SOLO con la categorÃ­a de cada pronÃ³stico VIP real del partido (sin lÃ­nea, selecciÃ³n, probabilidad ni cuota), con `sin_modelo: true` y sin marcadores; la app oculta el bloque Â«Marcadores mÃ¡s probablesÂ» en ese caso para no prometer lo que ni un VIP verÃ­a. Con VIP no cambia nada. Pruebas: `test_partido_mercados`, `test_mobile_delivery` y `match_markets_sin_modelo_test.dart`. Servidor desplegado (api) con respaldo `~/backups/sin-modelo-20261013` (vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-sinmodelo-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py` y `partido_mercados.py`, que coincidÃ­an con el commit). Verificado en producciÃ³n: Bristol Cityâ€“Blackburn devuelve 2 candados (Doble oportunidad, CÃ³rners) con `sin_modelo`; partidos con modelo de goles no cambian. APK compilado (`flutter build apk --release`, 76,0 MB, 13-oct 13:50, SHA256 75635A883E24385FAE2D24E163780BC4D2EAE56538CFCA77FB6CF44B521DB64E): `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`. No se verificÃ³ la firma con apksigner (no estÃ¡ en el equipo); el release exige `key.properties`. No se instalÃ³ en ningÃºn dispositivo ni se publicÃ³.

## 2026-10-13 â€” Detalle y cabecera de la app: sin banner VIP con pronÃ³stico abierto, sin botÃ³n de estadÃ­sticas, monedas en la cabecera

Pedido del titular (capturas de Bristol Cityâ€“Blackburn): (1) el banner Â«Este partido tiene un pronÃ³stico VIPÂ» solo sale si el partido NO tiene ningÃºn pronÃ³stico abierto (gratis o desbloqueado): los demÃ¡s VIP ya van con candado en Â«Mercados del partidoÂ»; (2) se quita de la tarjeta del pronÃ³stico el botÃ³n azul Â«Ver estadÃ­sticas del partidoÂ» (la clave `forecastSeeStats` queda sin uso en los 6 idiomas; se dejÃ³ para no tocar traducciones, AnÃ¡lisis sigue en su pestaÃ±a); (3) la cabecera fija lleva una moneda en miniatura (`Icons.toll`, la misma de la pestaÃ±a Coins) con el saldo DISPONIBLE (`wallet.spendable`, nunca negativo), Â«â€”Â» sin cuenta; al tocarla abre Coins. Se refresca al recargar y al salir de la pestaÃ±a Coins. No hay imagen propia: el repo no tiene activos de imagen; si se quiere un logo/ilustraciÃ³n hace falta el archivo. Solo cambia la app, sin textos nuevos. Pruebas: `product_navigation_test` (nuevas: saldo en cabecera, sin cuenta, banner/botÃ³n ausentes); suite Flutter 201 OK y analyze limpio. APK nuevo (76,0 MB, 13-oct 14:10, SHA256 4CDBF3D998392604C60E534BB8009138B09092F07B97997E8713AEA4A5367E45) en `apps/mobile/build/app/outputs/flutter-apk/app-release.apk`, sin instalar ni publicar.


## 2026-10-13 â€” HistÃ³rico FotMob importado en PostgreSQL

El usuario autorizÃ³ transferir e importar los originales en quantfut y confirmÃ³
el importador/migraciÃ³n/protecciÃ³n temporal. Carga atÃ³mica completada 20:06 UTC:
22.456 originales, 44.912 XI de equipo, 940.386 registros de estadÃ­sticas y
48.571 declaraciones de bajas histÃ³ricas. 20.502 asociaciones existentes,
1.554 partidos nuevos y once clubes domÃ©sticos nuevos; 400 originales conservan
asociaciÃ³n pendiente/conflicto (379 identidades de copas, 21 discrepancias).

Se rellenan 14.629 parejas xG vacÃ­as con recepciÃ³n real del 3-oct y 8.537
partidos en conteos ausentes; no se toca xG previo. Control temporal de todas
las fuentes observadas y replay Kalman sin anticipar xG. IDs por proveedor,
originales/recibos congelados, datos histÃ³ricos separados de capturas PIT;
los consumidores de jugadores/XI/bajas requieren adaptaciÃ³n posterior.

Prueba PostgreSQL con 53 encuentros, segunda carga cero escrituras y reversiÃ³n
confirmada; arnÃ©s 1.007 aprobadas/24 omitidas. Se cotejan 20.816 partidos previos,
25 originales releÃ­dos por hash y las 14.629 parejas contra cortes temporales.
Ligas, puertas, lotes sellados, XI/jugadores previos y modelo 2026.09.27-010508
conservados; API interna/pÃºblica 200 y versiÃ³n coincidente. La captura habitual
injuries de las 20:00 aÃ±adiÃ³ 324 filas durante la carga; se corroborÃ³ su cron y
recepciÃ³n, sin modificar esa tabla/tarea desde el importador. Sin entrenamiento
nuevo, publicaciÃ³n o mensajes manuales externos.

Evidencia .local/fotmob_import_20261013/verified/ y volumen
/srv/quantfut/artifacts/imports/fotmob-20261013/; backup de partidos y worker.
Detalle/cobertura: docs/importacion_fotmob_20261013.md. El xG nuevo no demuestra
una mejora retroactiva; Chile continÃºa sin xG en el archivo.

## 2026-10-13 â€” soccerdata con ZenRows e importaciÃ³n adicional verificada

El usuario detuvo el scraper anterior y lo sustituyÃ³ por soccerdata y su
documentaciÃ³n. Se confirmÃ³ cero procesos anteriores activos. soccerdata 1.9.1
fijado en e120471e424a173e83e8aeeaaf4d954ab9d38ee4, Apache-2.0; instalaciÃ³n
aislada optativa. Transporte MCP ZenRows 2.4.0 con proxies automÃ¡ticos, recibos,
hashes, reserva 100 y cachÃ© que conserva fallos sin bucles. Los calendarios que
habÃ­an fallado con otra configuraciÃ³n se probaron una vez con GB, recuperando
Chile/LaLiga 2/Ligue 2/Serie B. Se reutilizan respuestas antiguas verificadas.

El lector SofaScore se amplÃ­a para detalles; FBref ya retirÃ³ datos avanzados y
el listado obtenido no sirviÃ³ para ligas domÃ©sticas. ESPN Chile/Brasil B fallÃ³.
Muestra 2023/24: eventos sin xG anunciado en LaLiga 2, Serie B y Ligue 2; las
estadÃ­sticas consultadas en EspaÃ±a/Francia no traÃ­an esa mÃ©trica y las demÃ¡s
consultas no acreditaron cobertura. No prometer historia completa por aceptar
un calendario ni atribuir una mejora de backtest al xG recibido ahora.

Carga adicional completada 23:15 UTC: 586 originales, 574 asociaciones,
54 parejas xG aÃ±adidas a huecos, 138 XI, 2.789 registros de jugadores y 269
bajas histÃ³ricas. Cero partidos/clubes nuevos: la propuesta Troyesâ€“Valenciennes
1â€“1 fue puesta en cuarentena tras cotejar la derrota administrativa en LFP.
Otro marcador discrepante y diez identidades de copas quedan separados. Doce
equivalencias domÃ©sticas revisadas con nombres, paÃ­s y partidos; sin difuso.

Prueba PostgreSQL de carga repetida dentro de transacciÃ³n revertida: cero
escrituras adicionales y reversiÃ³n corroborada. Carga real coteja 22.615 registros
previos, 586 hashes y 54 disponibilidades temporales. Se conservan modelo
2026.09.27-010508, flags, lotes sellados y tablas de jugadores/XI API-Football;
model-card interna/pÃºblica 200 y misma versiÃ³n. Worker respaldado y ampliaciÃ³n
persistida sin reiniciar ni reconstruir desde el checkout viejo. ArnÃ©s final:
1.033 aprobadas/24 omitidas, 35 relevantes. Sin entrenamiento, compras o mensajes
externos. ZenRows 2.515â†’3.751 utilizados; quedan 1.249 en Ãºltima lectura.

Persisten 3.154 partidos sin xG y bloqueos de calendario en cinco competiciones;
los consumidores de XI/jugadores/bajas histÃ³ricos siguen pendientes. Evidencia
.local/soccerdata_completion_20261013/verified/ y artifacts/imports/soccerdata-20261013
del worker. Detalle y desglose: docs/soccerdata_zenrows_20261013.md.

## 2026-10-13 â€” Los pronÃ³sticos bloqueados enseÃ±an su cuota

Pedido del titular (lista Â«143 pronÃ³sticos mÃ¡s con VIPÂ»): que cada bloqueado muestre la cuota para que sea atractivo. `mobile.metadata()` aÃ±ade `cuota` (cuota publicada: `ref_price` en alta probabilidad, `price` en la escalera; `None` si no es vÃ¡lida, nunca inventada). Sigue SIN salir selecciÃ³n, lÃ­nea ni probabilidad (el test lo comprueba). Efecto a tener en cuenta: cuota + categorÃ­a permite estimar la probabilidad (~1/cuota), asÃ­ que la leyenda Â«Con VIP ves la probabilidad, la cuota y el anÃ¡lisisÂ» pasÃ³ a Â«â€¦la selecciÃ³n, la probabilidad y el anÃ¡lisisÂ» (6 idiomas, `picksLockedHint`). App: la fila bloqueada de `LockedPicksGroup` dibuja `@cuota` en dorado. Los candados por categorÃ­a del detalle del partido (`solo_candados`) no llevan cuota. Servidor desplegado (api) con respaldo `~/backups/cuota-bloqueados-20261013` (vuelta atrÃ¡s = imagen `quantfut-api-tapjoy:pre-cuota-backup` en el compose + `up -d --no-deps api`; imagen nueva = la anterior + `mobile.py`, que coincidÃ­a con el commit anterior). Medido en producciÃ³n: de los 143 bloqueados de partidos no empezados, 61 llevan cuota y 82 NO (hÃ¡ndicap 60 y doble oportunidad 22: `alta_prob_picks.ref_price` es NULL, no hay precio publicado de casa para esos mercados; no se inventa con 1/prob). PENDIENTE: APK; sin APK nuevo la cuota viaja pero no se ve, y la leyenda vieja sigue diciendo que la cuota es de VIP. Pruebas: Python 1032 OK, Flutter 201 OK, analyze limpio.

## 2026-10-13 â€” Parley: cada pata de cuota 1,20 a 1,80 (sin desplegar)

Pedido del titular, tras una primera lectura equivocada mÃ­a (que cambiÃ³ la cuota TOTAL; se revirtiÃ³ entera): la cuota total de cada parlay sigue en los 5 escalones de 1,90 a 5,00; lo que cambia es que CADA PATA tenga cuota de 1,20 a 1,80 (antes: >= 1,15 sin techo), con la combinaciÃ³n mÃ¡s probable de cada escalÃ³n y las patas que hagan falta (2 a 6). `parley.CUOTA_MIN_PATA, CUOTA_MAX_PATA = 1.20, 1.80` en `filtrar`; el informe pÃºblico aÃ±ade `reglas.cuota_max_pata`. Sin cambio de esquema, escalones ni historial (el control sigue comparando probabilidad prometida y acierto, mismo significado). SimulaciÃ³n con datos reales (17 partidos con precio, dry-run en el worker, sin escribir): la probabilidad de cada parlay casi NO cambia (52/46/37/28/22 % frente a 52/45/37/30/23 %), porque la fija la cuota total y mas patas la bajan; el efecto es que desaparecen las patas largas (1X2 a 2,16 con 48 %, cÃ³rners a 2,00 con 51 %) y toda pata queda entre 56 % y 82 %. Rige desde el primer sellado tras desplegar el worker (el del 14-oct 09:00 UTC si se despliega antes). Pruebas: `test_parley` (rango de pata incluidos bordes y float4, ningÃºn parlay con pata fuera de rango), suite Python OK. PENDIENTE: desplegar worker (parley.py, parley_datos.py) y api (parley_datos.py: informe) antes de ese sellado.

DecisiÃ³n del titular sobre mercados (2026-10-13): el parley NO busca en todos los mercados, solo en los de lÃ­neas validadas (1X2, doble oportunidad, goles 1,5/2,5/3,5, goles por equipo, ambos marcan sÃ­, hÃ¡ndicap, cÃ³rners y tarjetas habilitados) y elige por probabilidad calculada, no por acierto real. Ponderar por acierto real por mercado se pospone hasta tener ~50 liquidados por mercado (hoy 5-41): anotado en `harness/tareas.md` (Parley, punto 11) y en el README.

Parley con patas de 1,20-1,80 DESPLEGADO (2026-10-13 ~20:00 UTC, commit a90bdd2) en worker y api con respaldo `~/backups/patas-20261013` (vuelta atrÃ¡s = imÃ¡genes `quantfut-worker:pre-patas-backup` y `quantfut-api-tapjoy:pre-patas-backup`; en el compose la api vuelve a `image: quantfut-api-tapjoy:pre-patas-backup` y el worker se retaga a `latest`, luego `up -d --no-deps --no-build api worker`). El `parley.py` de la api estaba en la versiÃ³n 059372a (sin doble oportunidad); ahora los dos llevan la misma. Comprobado: md5 de parley.py/parley_datos.py = HEAD en ambos contenedores, cron del worker vivo (daily 09:00 UTC), `/parley` publica `cuota_min_pata 1.2` y `cuota_max_pata 1.8`. El ensayo en seco a las ~20:00 UTC sale vacÃ­o (ventana por dÃ­a, sin partidos dentro): el primer sellado real con la regla es el del 14-oct 09:00 UTC; VERIFICAR ese lote (`parley_datos informe`: toda pata entre 1,20 y 1,80). APK nuevo compilado con la cuota de los bloqueados y la leyenda nueva: 76,0 MB, 13-oct 18:50, SHA256 1113356E19103446A3C7C28EDA5551340E27C48EDFFF363E3C371BCA10104EC7; sin instalar ni publicar.


## 2026-10-13 â€” RecuperaciÃ³n adicional con clave nueva de ZenRows

Se priorizÃ³ el modo automÃ¡tico de la CLI oficial 1.5.0, sin imponer paÃ­s ni
funciones caras a todas las llamadas; tres conexiones frente al lÃ­mite verificado
de cinco. Presupuesto compartido con reserva previa de 25 por solicitud, devoluciÃ³n
solo del coste comunicado y parada ante autenticaciÃ³n/cuota agotada. MCP 2.4.0
lee cuota y acepta la clave de la tarea solo en el entorno; configuraciÃ³n y cuenta
compartidas anteriores conservadas. Clave nueva cifrada DPAPI fuera de Git y VPS.

La ruta pÃºblica www de SofaScore recuperÃ³ calendarios antes bloqueados en Brasil B,
Bundesliga 2, Dinamarca, Suecia y Europa League. Parser real de soccerdata 1.9.1;
fallos conservados, jornadas danesas procesadas independientemente. No repetir
fallos ni confundir tiros sin xG con xG publicado: las muestras histÃ³ricas de
EspaÃ±a/Francia carecÃ­an de ese campo. Recuperar jornadas actuales no demuestra
acceso a toda la historia. Se excluyen los 586 IDs SofaScore ya congelados.

Carga confirmada 14-oct 00:55 UTC (13-oct 18:55 MÃ©xico): 125 originales, 101
asociaciones, 36 parejas xG canÃ³nicas aÃ±adidas, 228 XI, 4.137 registros de jugadores
y 294 bajas histÃ³ricas. De 97 xG originales, once no tienen asociaciÃ³n y cincuenta
conservan valores canÃ³nicos anteriores. Cero partidos/clubes nuevos; 24 originales
europeos sin identidad canÃ³nica conservados. Seis equivalencias danesas revisadas
con paÃ­s/nombres y dos fixtures independientes cada una; AGF domÃ©stico resuelve
tambiÃ©n su encuentro europeo. Sin difuso ni altas bajo copas.

Dos cargas en transacciÃ³n revertida: segunda cero escrituras y conteos restaurados.
Carga real verifica 125 normalizaciones y cuerpos HTTP/hash/recepciÃ³n; conserva
22.632 partidos previos y 23.042 originales anteriores con identidad/hash/reloj.
Las 36 parejas xG respetan cortes temporales. Modelo 2026.09.27-010508, flags,
lotes sellados y tablas antiguas XI/jugadores conservados; API interna/pÃºblica
200 y misma versiÃ³n. Sin cÃ³digo nuevo en worker ni reinicio, entrenamiento,
compras, activaciÃ³n de ligas o mensajes externos manuales.

Saldo nuevo verificado: 988 utilizados de 5.000, 4.012 restantes y cero concurrencia
activa. Descarga principal 233 llamadas CLI y complemento danÃ©s 26; pruebas previas
incluidas en consumo total. ArnÃ©s final 1.045 aprobadas/24 omitidas. Huecos xG
3.154â†’3.118; Bundesliga 2 queda sin huecos en el corte desde 2024, Brasil B aÃºn384,
Dinamarca3 y Suecia2. Consumo medido por cuenta, sin inferir fallos gratuitos;
RESP008 puede cobrarse. Evidencia .local/zenrows_key_20261013/prepared/ y verified/,
worker artifacts/imports/zenrows-new-key-20261013/. Detalle y pendientes en
docs/zenrows_clave_nueva_futbol_20261013.md; adaptaciÃ³n de consumidores histÃ³ricos
y mejoras del modelo siguen sujetas a validaciÃ³n, sin mejora retroactiva atribuible.

## 2026-10-13 â€” EliminaciÃ³n fÃ­sica de Chile y Brasil B

El titular pidiÃ³ retirarlas por completo y autorizÃ³ expresamente borrar su
historial protegido tras revisar cuotas, alta probabilidad, escalera y parley.
Se comprobÃ³ que sus clubes domÃ©sticos no intervenÃ­an en otras competiciones.
Se eliminan 1.806 partidos, 1.784 originales histÃ³ricos, 36 clubes, 49 alias,
36 clasificaciones, 81.082 cuotas, 3.518 XI, 73.414 registros de jugadores y
465 bajas, junto con selecciones y resultados relacionados. Para evitar
productos incompletos se retiran dos retos enteros (seis pasos) y un parley
entero (tres patas), incluidas las partes de otras ligas dentro de esos grupos.

Respaldo selectivo: 25 COPY binarios, 45.427.123 bytes, con hashes cotejados
localmente. Bloqueos exclusivos y excepciÃ³n temporal de triggers solo en
tablas seleccionadas, restaurados antes del commit. Prueba PostgreSQL real:
primera eliminaciÃ³n, repeticiÃ³n cero escrituras y reversiÃ³n; eliminaciÃ³n real
con los mismos conteos. Conteos y huellas de filas ajenas a la selecciÃ³n en
40 tablas conservados, modelo 2026.09.27-010508 y SÃ©rie A intactos. Los 15
lotes originales en disco conservan su cadena; no se reescriben. Su contenido
retirado ya no se regenera desde la base operativa. Comparaciones de acierto
posteriores deben explicar el cambio de poblaciÃ³n, sin atribuirlo a una mejora.

db/063 registra Ãºnicamente metadatos de retiro y bloquea reinserciÃ³n en
catÃ¡logo/partidos. FotMob y SofaScore quedan en 23 competiciones; normalizaciÃ³n,
emparejamiento/importaciÃ³n y manifests viejos no reintroducen las dos retiradas.
Fuentes exactas cotejadas y desplegadas sin reconstruir checkout viejo ni
reiniciar. Worker respaldado y cambios persistidos en imagen. API interna y
pÃºblica 200, catÃ¡logo23 y home mÃ³vil sin IDs retirados; cero ligas/partidos/
originales/clubes de ambas. ArnÃ©s 1.049/24. Sin entrenamiento ni llamadas nuevas
a proveedores deportivos; comprobado cero procesos entrenadores al terminar.

Quedan 13 competiciones con modelo habilitado y diez pendientes; huecos xG
desde2024: 3.118â†’2.073 por retirar ligas, no por recuperar valores. Los datos
reciÃ©n importados aÃºn no participaron en un nuevo modelo activado. Evidencia
.local/remove_chile_brasil_b_20261013/verified/ y artifacts/maintenance/
remove-chile-brasil-b-20261013 del worker; 45MB de respaldo tambiÃ©n en host.
Detalle: docs/eliminacion_chile_brasil_b_20261013.md. Informes de cobertura
actuales actualizados; archivos previos y sellados conservados como evidencia.

## 2026-10-14 â€” PitchAPI: histÃ³rico y xG a la base

Por orden del titular se descargÃ³ el histÃ³rico de PitchAPI y se importaron
sus xG. DecisiÃ³n clave: identidad de club solo por corroboraciÃ³n de partidos
(3 votos, 90 % de dominancia, fecha UTC exacta), nunca por nombre. Una primera
versiÃ³n con ventana de Â±1 dÃ­a votaba mal entre partidos vecinos con igual
marcador; se corrigiÃ³ antes de escribir nada. La recepciÃ³n real queda en
`xg_recorded_at` para que el modelo no use el xG antes de existir.

5.355 xG importados (ensayo revertido, carga e idempotencia verificadas); los
huecos desde 2024 pasan de 1.262 a 1.220 porque PitchAPI no cubre 2024 en
Serie B, LaLiga 2 ni Ligue 2. Detalle: docs/pitchapi_historico_20261014.md.

## 2026-10-14 â€” AuditorÃ­a de completitud desde 2025-01-01 y cierre de Allsvenskan

AuditorÃ­a de solo lectura de las 23 competiciones contra API-Football (segunda
fuente independiente) y la base. Resultado: 13.200 partidos terminados, todos
con marcador, y la base no tiene ningÃºn partido que API-Football no tenga. Las
diferencias son playoffs de promociÃ³n/relegaciÃ³n y finales (~55, fuera de
jornada regular) y, en Champions/Europa League, clubes fuera del catÃ¡logo, que
se descartan por diseÃ±o. LecciÃ³n del mÃ©todo: emparejar por fecha y marcador
produce falsos positivos entre partidos con igual resultado en dÃ­as cercanos;
solo son fiables los conteos y el emparejamiento con fecha exacta primero.

Tres partidos de Allsvenskan del 31-may-2026 seguÃ­an `scheduled` porque
`close_recent` solo mira 72 horas. Se cerraron con esa misma funciÃ³n
(`hours_back` amplio, solo `se.allsvenskan`), sin picks ni predicciones
asociados: 2-2, 3-2 y 4-5, con `result_recorded_at` real de hoy. Vencidos sin
cerrar: 0; queda 1 aplazado (Vallecanoâ€“Athletic, 10-oct). xG desde 2025 sin
cubrir: 237 (Serie B 188 de eneâ€“jun 2025, copas 26, resto ~23).

## 2026-10-14 â€” Respaldo y cotejo con PitchAPI (implementado, sin desplegar)

DecisiÃ³n del usuario: resultados solo con AVISOS; relleno automÃ¡tico solo de xG.
Se eligiÃ³ asÃ­ porque los IDs de partido de PitchAPI no son estables (26 ligas se
restauraron con IDs nuevos), no hay SLA ni tÃ©rminos publicados y un resultado
errÃ³neo liquidarÃ­a picks. El xG espera 48 h para que API-Football capture
primero; PitchAPI nunca sobrescribe y guarda el original con hash y recepciÃ³n.
Los clubes se emparejan solo por partidos corroborados (semilla de 496 mÃ¡s
aprendizaje diario por votos). La clave `pk_test_` anterior se revocÃ³ sola el
14-oct: el panel permite rotarla sin tocar el servidor. Comprobado contra datos
reales (10 dÃ­as, 235 partidos, 0 discrepancias) y las migraciones en transacciÃ³n
revertida. Pendiente: pasar a una clave `pk_live_`, preguntar al proveedor por
uso comercial y almacenamiento, y desplegar.

Desplegado el mismo dÃ­a por orden del titular: la clave se guardÃ³ cifrada en la
base (no en `.env`) y el respaldo quedÃ³ activo con cron 12:40 UTC. Decisiones del
despliegue: se parchÃ³ `base.html` sobre la versiÃ³n de producciÃ³n (el menÃº
diferÃ­a del repo) en vez de pisarlo; el worker, de imagen anterior a las claves
cifradas, recibiÃ³ `cryptography==50.0.2` (la versiÃ³n ya fijada) y `cifrado.py`,
en capas nuevas sin reiniciar. Primera pasada real: 0 discrepancias. Detalle y
reversiÃ³n en docs/pitchapi_respaldo_20261014.md.

## 2026-10-14 â€” AuditorÃ­a de las 23 competiciones y entradas del pronÃ³stico

La disponibilidad de datos no equivale a que el motor los utilice. Se auditÃ³
producciÃ³n en transacciones de solo lectura: 20.854 terminados desde 2024,
1.222 sin xG, 336 sin XI completo archivado y 349 sin al menos 11 jugadores
con minutos por lado. Los mÃ³dulos actuales solo leen las tablas nativas:
16.176 no tienen XI compatible y 15.822 no tienen jugadores compatibles.
Se encontraron 8.118 parejas de amarillas pendientes de pasar del archivo a
la tabla principal. De 20.331 originales FotMob vinculados y leÃ­dos, 8.623
contienen campos de clima, 20.331 sede y 20.140 Ã¡rbitro; no son entradas
directas del motor principal. Deben validarse contenido, unidades y momento
de disponibilidad, sin usar el clima posterior como pronÃ³stico anterior.

El modelo activo sigue `2026.09.27-010508` en 13 competiciones, sin mezcla ni
residuo. XI tiene 106 predicciones experimentales pero no promociÃ³n; las bajas
se capturan. El selector de valor decide por cuotas frente a Pinnacle, no por
el edge del modelo. En 7.689 parejas xG de las competiciones modeladas la
recepciÃ³n es posterior al ajuste del artefacto, por lo que importar no actualiza
sus parÃ¡metros. Otra limitaciÃ³n comprobada: el importador de estadÃ­sticas
individuales convierte ausentes en cero; no nulo no certifica cobertura real.

PrÃ³ximos siete dÃ­as: 227 programados, 140 en ligas modeladas con consulta de
bajas en Ãºltimas 24 h y 87 excluidos de esa captura por configuraciÃ³n; ninguno
estaba en la ventana de XI. Informe y prioridades propuestas en
`docs/auditoria_datos_modelo_20261014.md`; sin cambios de producciÃ³n ni nuevo
entrenamiento. ArnÃ©s inicial aprobado (1.084 pruebas, 24 omitidas) y huellas
del cÃ³digo principal/selector/captura contrastadas con el despliegue.

## 2026-10-14 â€” SeÃ±ales del motor: spec, plan y F0 aplicada

El usuario pidiÃ³ llevar al motor principal los datos que solo estaban archivados.
Decisiones: una seÃ±al entra Ãºnicamente si gana fuera de muestra (RPS, log-loss y
ECE en >=2 ligas); mecanismo de ajuste de lambdas sobre Dixon-Coles, no dentro del
ajuste ni un GBM; y, como el XI llega a T-60 y la predicciÃ³n se sellaba a las 08:00,
el usuario relajÃ³ la garantÃ­a a un sello por partido justo antes del inicio (los
lotes antiguos se regeneran con su formato por fecha de corte). Spec y plan en
docs/superpowers/. Clima con Open-Meteo plan Standard: sin Historical Forecast, asÃ­
que el bloque se valida con los pronÃ³sticos que guardemos o con el clima observado
de FotMob como sustituto declarado.

F0 aplicada: el archivo FotMob rellenÃ³ solo NULL en `matches` (amarillas/rojas
8.412->294, descanso 7.325->240, xGOT, Ã¡rbitro en columna aparte, sede en la tabla
`estadios`) con procedencia en `matches_enriquecimiento`. Decisiones que costaron
algo: el xGOT no se mezcla con PSxG; el Ã¡rbitro de FotMob no pisa `matches.referee`
(lo lee el motor de tarjetas); el simulacro fue de solo lectura porque la migraciÃ³n
bloquea `matches`. Contraste: FotMob cuenta tarjetas distinto en ~6 % de los
partidos (+1), asÃ­ que las probabilidades de tarjetas se mueven en las ligas que casi
no tenÃ­an historial. Detalle y reversiÃ³n: docs/f0_archivo_a_matches_20261014.md.

## 2026-10-14 â€” F1: capa de ajuste por bloques y puerta corregida

`qf.model.ajuste` generaliza el challenger de XI (bloques registrados, comparaciÃ³n
incremental A frente a A+B, artefacto `ajuste_<versiÃ³n>.pkl`). DecisiÃ³n clave: la
puerta heredada tenÃ­a dos defectos que se midieron antes de corregirlos. Una
columna constante pasaba la puerta con la misma mejora que el ruido, porque el
intercepto re-nivela lambdas sesgadas y el mÃ©rito se le daba al primer bloque; y el
ruido puro la pasaba en 8 de 40 semillas. En `ajuste.comparar` la referencia es
ahora un modelo solo de nivel y se exige significancia (remuestreo pareado de la
diferencia de RPS, percentil 95 < 0). La puerta de `lineup_challenger` no cambia.
Con datos reales, el XI simple pasa la puerta estricta (dRPS -0,0013, p95 -0,00056,
9 de 12 ligas) y el modelo de nivel casi coincide con las lambdas crudas: no era
re-nivelaciÃ³n. No se reentrenÃ³: el entrenamiento del 12-oct ya usÃ³ el xG nuevo y no
pasÃ³ la puerta frente a Elo; el cron del 1-nov incorpora el resto. Detalle:
docs/f1_capa_de_ajuste_20261014.md.

## 2026-10-14 â€” Historial del Reto Escalera con detalle en la app

El historial ya se guardaba (tablas inmutables `escalera_*`) y la app listaba los Ãºltimos 10
cerrados, pero sin ver sus escalones. DecisiÃ³n: el detalle se despliega en la propia fila
(acordeÃ³n de uno), no en otra pantalla, para no recargar. QuÃ© se enseÃ±a lo fijÃ³ el titular:
los 9 Ãºltimos retos cumplidos y el Ãºltimo fallido, sin filtros (mi primer intento fue un
filtro Todos/Cumplidos/Fallidos con 10 por filtro y no era lo pedido). El resumen de arriba
sigue contando todos los cerrados y un texto bajo la lista dice quÃ© se muestra, para que la
selecciÃ³n no pase por el historial completo. `_paso_publico` ahora publica `selection` y
`line` porque la app traduce el pronÃ³stico desde esos campos; no revela nada nuevo (el
`texto` en espaÃ±ol ya salÃ­a). Los escalones sin liquidar siguen saliendo por `metadata`
(lista blanca), asÃ­ que el candado VIP no cambia.

## 2026-10-14 â€” Doble oportunidad: su cuota se toma de API-Football

En la lista de alta probabilidad, los pronÃ³sticos de doble oportunidad (119 + 28 en
producciÃ³n) salÃ­an sin cuota: `_ref` decÃ­a que ningÃºn proveedor la cotizaba, pero
`af_odds` guarda el bet 12 desde el 12-oct (154 partidos). Ahora `_ref_nuevos` la lee de
las filas de API-Football con la misma regla de casas y edad que la escalera y el parley,
y `select_and_persist` carga esas filas siempre (antes solo con ambos marcan/cÃ³rners
activos). Solo afecta a pronÃ³sticos NUEVOS: los sellados tienen `ref_price` vacÃ­o en la
cadena y no se tocan. El hÃ¡ndicap sigue sin cuota (API-Football no lo trae; las cuotas de
hÃ¡ndicap estÃ¡n en The Odds API y el pronÃ³stico se elige sobre otro snapshot): pendiente
de decidir si se cruzan fuentes o se oculta el pronÃ³stico sin cuota.

Desplegado el 14-oct (solo `worker`, sin reiniciarlo): `docker cp` de `alta_prob_datos.py` y
`alta_prob_ext.py` al contenedor; los jobs de cron arrancan un proceso nuevo y cogen el
archivo en la siguiente pasada. Respaldo de los anteriores en
`~/quantfut/releases/doble-oportunidad-cuota-20261014/*.before`. Comprobado con la base de
producciÃ³n: tres partidos con doble oportunidad vigente dan cuota por casa (p. ej. 1X 1,75
betano). Aviso: la copia es solo del contenedor; el Ã¡rbol `~/quantfut/src` del VPS estÃ¡
desfasado (ni siquiera tiene `alta_prob_ext.py`), asÃ­ que reconstruir el worker desde Ã©l
perderÃ­a este y otros parches.

## 2026-10-14 â€” HÃ¡ndicap: su cuota sale de API-Football (bet 4)

Los 279 pronÃ³sticos de hÃ¡ndicap de producciÃ³n tenÃ­an `ref_price` vacÃ­o: la cuota solo se
buscaba en The Odds API y los pronÃ³sticos se eligen sobre un snapshot de API-Football.
Cruzar fuentes cubrÃ­a solo el 19 % (53 de 279; solo 1xBet y Coolbet cotizan ahÃ­) y mezclarÃ­a
edades distintas, que el proyecto prohÃ­be. DecisiÃ³n: volver a capturar el bet 4 ("Asian
Handicap") en `af_odds` (misma peticiÃ³n, sin coste de cuota ni migraciÃ³n), solo de SOFT_BOOKS
y solo lÃ­neas enteras y medias; comprobado con una respuesta real (Bet365 y Betano lo
cotizan). La lÃ­nea del visitante se guarda invertida (propia, no la del local): es la
trampa que ya estaba documentada en el cÃ³digo archivado del 25-sep. `_cuotas_af` lee
`spreads` y `_ref_nuevos` los usa cuando el snapshot es de API-Football; con uno de The Odds
API sigue leyendo los suyos (nunca mezcladas). Solo afecta a pronÃ³sticos nuevos y solo cuando
la casa ya tenga guardada la cuota; los sellados no se tocan. Pendiente de medir: cuÃ¡ntos
hÃ¡ndicap salen con cuota tras uno o dos dÃ­as de captura.

## 2026-10-14 â€” Tope de 4 gratis en Inicio y en Alta probabilidad

DecisiÃ³n del titular: como mucho 4 pronÃ³sticos gratis a la vez en Inicio y en Alta probabilidad
(antes uno por mercado y por lote: hoy habÃ­a mÃ¡s de 4 abiertos al sumar lotes de varios dÃ­as).
Se aplica como filtro de lectura en `high_probability` (`cap_free`, FREE_MAX = 4): entre los
gratis sin empezar quedan los de mayor cuota publicada y a igualdad mayor probabilidad, la
misma prioridad de siempre; los demÃ¡s pasan a candado con su cuota a la vista. Los que ya
empezaron no cuentan y siguen visibles con su resultado. El reparto por lote
(`mobile_free_allocations`) no se toca: es auditorÃ­a. Inicio y Alta probabilidad leen el mismo
bloque `alta_probabilidad`, por eso un solo punto cubre las dos pantallas. El Reto Escalera
conserva su Ãºnico escalÃ³n gratis aparte. Tope de 4 gratis publicado tambiÃ©n en `/config`
(`high_probability_free_max`) y el texto de la app lo muestra (Â«hasta 4 gratisÂ»).

Desplegado el 14-oct: API reconstruida sobre la imagen anterior con solo `api/mobile.py`
(`quantfut-api-tope-gratis:20261014`, persistida en el compose; worker intacto). Respaldo y ID de
la imagen previa en `~/quantfut/releases/tope-gratis-20261014/`. Comprobado en producciÃ³n:
`/mobile/v1/home` devuelve 4 gratis abiertos (cuotas 1,32 / 1,28 / 1,27 / 1,25) y 81 con candado, y
`/mobile/v1/config` publica `high_probability_free_max: 4`.

## 2026-10-14 â€” El parley respeta los mercados bloqueados de alta probabilidad

Se midiÃ³ el planteamiento de Â«mejorar el parleyÂ» (arriba-abajo, penalizar margen, anclas
1,12-1,19, tendencia de cuotas) sobre el conjunto real de patas del dÃ­a (116 patas, 9 partidos).
La probabilidad de un ticket sale â‰ˆ 1/cuota (1,97â†’52 %, 2,21â†’46 %, 2,79â†’37 %, 3,49â†’28 %), asÃ­
que sin cambiar los escalones no hay forma de subir el acierto con la selecciÃ³n. Armar de arriba
abajo da 3 tickets (Î£P 0,87) frente a 4 (Î£P 1,62) del orden actual, y el mejor de los 120
Ã³rdenes posibles coincide con el actual: el cuello de botella son los partidos, no el orden. Las
anclas dan Î£P 1,628 frente a 1,623 y peor valor esperado. Margen y calibraciÃ³n por mercado:
el margen ya estÃ¡ en cuota frente a probabilidad justa; la calibraciÃ³n sÃ­ tiene respaldo.
`alta_prob_ext` bloquea `totals` (prometÃ­a 82 %, real 67,3 % en 55 casos; z âˆ’4,3 con 80) y los
parlays reales llevaban 7 patas de goles con 61,8 % prometido y 3 ganadas. El parley no
consultaba ese control. DecisiÃ³n del usuario: `pl.sin_bloqueados` quita las patas de los
mercados (por grupo de control) bloqueados en la alta probabilidad principal o ampliada;
`todo` no pausa el parlay. Con 9 partidos de muestra y 6 parlays liquidados NO se puede medir el
efecto sobre el acierto: el control por escalÃ³n del propio parlay sigue siendo el juez. Pendiente
de medir: tarjetas y cÃ³rners, que dominan los tickets y no tienen historial de calibraciÃ³n propio.

Desplegado el 14-oct (solo `worker`, sin reiniciarlo): `docker cp` de `parley.py` y `parley_datos.py`;
respaldo de los anteriores en `~/quantfut/releases/parley-bloqueados-20261014/*.before`. Ensayo en
seco con datos reales: mercados bloqueados `['totals']`, 104 candidatas (se quitaron las 12 de
goles de las 116), 4 tickets (1,97 Â· 2,21 Â· 2,79 Â· 3,49) sin cambios de probabilidad. Misma
salvedad que antes: la copia es solo del contenedor y el Ã¡rbol `~/quantfut/src` estÃ¡ desfasado.

## 2026-10-14 â€” Seguimiento sin publicar de tarjetas e informe de prometido frente a real

Las tarjetas estÃ¡n en 3 de los 4 tickets del parley y no tienen historial propio (ninguna liquidada
en alta probabilidad ni en la escalera; 2 patas en el parley). DecisiÃ³n del usuario: tabla aparte
`tarjetas_seg` (db/068, inmutable, con `tarjetas_seg_results`) que guarda cada dÃ­a TODOS los
candidatos de tarjetas de los partidos con precio (lÃ­neas de `LINEAS_HABILITADAS["cards"]`, la
probabilidad prudente = menor entre modelo y mercado, y la mejor cuota de la lista; sin cuota de la
lista no entra, como en el parley). NO se publica: ninguna ruta de API, panel, web ni app la lee (lo
comprueba una prueba). Se sella en el lote (`tarjetas_seg`, `LOTE_TARJETAS_DESDE` = 2026-10-15, primer
lote sin sellar) y se liquida en `clv.settle_pending` con la misma regla que la escalera (amarillas +
rojas). Va ENCENDIDO por defecto en cÃ³digo, no por entorno: activarlo por `.env` obliga a recrear el
worker y eso borrarÃ­a los parches copiados con `docker cp`; `tests/conftest.py` lo apaga en las
pruebas. `eval/calibracion_mercados.py` (`python -m qf.eval.calibracion_mercados [--json]`) compara por
mercado prometido y real con IC de Wilson al 95 % sobre lo liquidado y SELLADO de alta probabilidad,
ampliada, escalera, parley y tarjetas; un pronÃ³stico repetido en varias fuentes cuenta una vez en el
total (el desglose no deduplica) y con menos de 30 casos no opina. Solo lectura: no bloquea nada.

Desplegado el 15-oct 00:18 UTC, ANTES del job de las 08:00 (el lote del 15 es el primero que lleva el
bloque): migraciÃ³n db/068 aplicada (ensayada antes en una transacciÃ³n revertida, con los triggers
rechazando UPDATE y DELETE) y worker actualizado con `docker cp` (`tarjetas_seg.py`,
`calibracion_mercados.py`, `config.py`, `hashchain.py`, `clv.py`, `daily.py`; respaldo de los cuatro
anteriores en `~/quantfut/releases/tarjetas-seg-20261014/*.before`; sin deriva respecto al repo).
Ensayo en seco con datos reales: 5 partidos, lÃ­neas bajo 4,5 y bajo 5,5 con cuota de bet365/betano
(probabilidades 54-71 %). Primer informe de calibraciÃ³n sobre lo ya liquidado: goles `totals` 77,5 %
prometido frente a 60,9 % real (n 110, IC95 51,6-69,5 %, Â«por debajoÂ»); `spreads` âˆ’3,8, `corners`
âˆ’1,7, `double_chance` +2,4 y goles de equipo +3 a +8 dentro del IC; `btts` (9), `h2h` (12),
`corners_home/away` y `cards` (2) sin muestra. Misma salvedad de siempre: la copia es solo del
contenedor y el Ã¡rbol `~/quantfut/src` del VPS estÃ¡ desfasado. Por quÃ© no hay API: la API no lee la
tabla ni necesita este cÃ³digo, asÃ­ que su imagen no se tocÃ³.

Medido el 15-oct tras la primera captura con el bet 4 (00:20 UTC): 2.580 filas de hÃ¡ndicap de 101
partidos de las tres casas de la lista que lo cotizan (Bet365 96 partidos, 1xBet 84, Betano 108
partidos con alguna lÃ­nea). De las combinaciones lado/lÃ­nea que elige la alta probabilidad en los 9
partidos prÃ³ximos con hÃ¡ndicap, el 86 % (77 de 90) ya tiene cuota; la lÃ­nea +2 del local casi nunca
se cotiza (1 de 9) y el resto cubre 8-9 de 9. El primer lote que ya sale con cuota de hÃ¡ndicap es el
de las 08:00 UTC del 15-oct. Pendiente de confirmarlo con los pronÃ³sticos reales de ese lote.

## 2026-10-14 â€” Fuera el aviso Â«Modelo NBA en entrenamientoÂ» de Mercados

Pedido del titular: en la pestaÃ±a Mercados de la app se quita el bloque Â«Modelo NBA en entrenamientoÂ»
(el Ãºltimo de la pantalla, bajo Â«Ver acceso VIPÂ»). La secciÃ³n `nba` sigue existiendo en
`mobile_features` y en el servidor; solo deja de pintarse el aviso. Si NBA se activa algÃºn dÃ­a, habrÃ¡
que decidir dÃ³nde se muestra.

## 2026-10-14 â€” Compartir el cÃ³digo de referido con enlace y pÃ¡gina de invitaciÃ³n

Pregunta del titular: cÃ³mo llega el cÃ³digo de referido al invitado en una app de telÃ©fono. Estado
real: el cÃ³digo se copiaba y se escribÃ­a a mano en Coins; el botÃ³n de compartir enviaba un texto sin
cÃ³digo ni enlace; la app no lee nada al instalarse. DecisiÃ³n: paso 1 (sin depender de la tienda).
Â«Compartir mi cÃ³digoÂ» de Coins envÃ­a el cÃ³digo y `https://pronosticosdeportivos.pro/i/CODIGO`; la
ruta `/i/{codigo}` (`api/invitacion.py`) es pÃºblica, sin base de datos (no confirma que el cÃ³digo
exista, asÃ­ que no sirve para enumerar) y muestra el cÃ³digo, copiar y los pasos en los 6 idiomas segÃºn
`Accept-Language`; un cÃ³digo mal formado da 404 y no se repite en la pÃ¡gina. Cumple la CSP del panel
(`script-src 'self'`): el copiar vive en `static/invitacion.js`, sin scripts ni estilos en lÃ­nea. En el
campo de Coins, Â«Pegar cÃ³digoÂ» extrae el cÃ³digo del portapapeles aunque sea el enlace o el mensaje
entero (`inviteCodeFrom`: solo el cÃ³digo suelto o el de `/i/CODIGO`; una palabra cualquiera no cuenta) y
Registrar tambiÃ©n lo normaliza. `APP_DOWNLOAD_URL` (vacÃ­o por defecto) aÃ±ade el botÃ³n de descarga
cuando la app tenga tienda. Pendiente, a propÃ³sito: leer el referrer de Google Play al instalar
(Android y solo desde la tienda), App Links para abrir la app desde el enlace y una soluciÃ³n para iOS
(terceros: Branch, AppsFlyer o Adjust).

Desplegado el 15-oct (solo API; worker intacto): imagen `quantfut-api-invitacion:20261014` sobre la anterior con
`invitacion.py`, `main.py`, `config.py`, la plantilla `cuenta/base.html` (ahora con `lang` variable),
`cuenta/invitacion.html` y `static/invitacion.js`; persistida en el compose. Respaldo del compose y de
la imagen previa en `~/quantfut/releases/invitacion-20261014/`. Comprobado en el dominio real (vÃ­a
Cloudflare): `/i/f9b9cbe3633f` â†’ 200 con el cÃ³digo en mayÃºsculas; `Accept-Language` en/de cambian el
idioma; `/i/abc` y un cÃ³digo con `<script>` â†’ 404 sin repetirlo; `/static/invitacion.js` 200;
cabeceras `no-store`, CSP `script-src 'self'`, `noindex` y `no-referrer`.

## 2026-10-14 â€” Plan anotado: referidos cuando la app suba a la Play Store

A peticiÃ³n del titular, el plan completo quedÃ³ en `tareas.md` (secciÃ³n Â«Referidos al subir la app a la
Play StoreÂ»): `APP_DOWNLOAD_URL` + parÃ¡metro `referrer` en el enlace de Play, lectura del referrer en
la app (solo Android y solo desde la tienda, registrando el cÃ³digo al verificar el correo), App Links con
`assetlinks.json` usando la huella de la clave de firma final de Play, prueba con dos cuentas reales y
las decisiones pendientes (iOS, instalaciones por APK). No se implementa antes de tener una pista de
pruebas de Play: el referrer no se puede probar sin instalar desde la tienda.

## 2026-10-14 â€” Videos con recompensa de AdMob (apagado y en modo prueba)

DecisiÃ³n clave: **solo el servidor acredita**, y solo con el callback firmado de Google (SSV). La app pide un
ticket, muestra el video y espera a que suba el saldo; nunca acredita ni elige el importe (se ignora el
`reward_amount` de Google). Tope diario (5), pausa (180 s) y dÃ­a UTC se deciden en el servidor y se editan en
`/control/anuncios`. Por quÃ© asÃ­: un cliente que acredita se falsifica, y los clics o visualizaciones
inventados son exactamente el trÃ¡fico no vÃ¡lido que cuesta la cuenta de AdMob.

Detalles que no son obvios: el dÃ­a de un crÃ©dito es el de emisiÃ³n del ticket; un rechazo tras firma vÃ¡lida
responde 200 con `coins=0` para que Google no reintente; las monedas de anuncios no validan referidos; los
callbacks ya emitidos se aceptan aunque se apaguen los anuncios. Dejado apagado y en modo prueba: la polÃ­tica
de apuestas de AdMob/Play para una app de cuotas no se pudo confirmar y la polÃ­tica de privacidad publicada
dice que no hay publicidad personalizada; ambos son bloqueantes (ver `tareas.md`). Nada desplegado.
Probado con Postgres local en un esquema aislado: la prueba `test_pg_fixed_allocations_and_ladder_global_one`
(ajena a esto) falla con `KeyError: 'kickoff_utc'` en `mobile.py` cuando hay base; antes se omitÃ­a.

Desplegado el 15-oct (solo API; worker intacto): imagen `quantfut-api-admob:20261014b` sobre `quantfut-api-invitacion:20261014`
con `anuncios.py`, `anuncios_ssv.py`, `rewards.py`, `main.py`, `panel.py`, `mensajes.py` y las plantillas `anuncios.html` y
`base.html` (los cinco archivos ya existentes en producciÃ³n eran idÃ©nticos a la base de la rama antes de copiar los
mÃ­os). `db/069` aplicada tras un ensayo con ROLLBACK; respaldo del compose y de las tablas `reward_*` en
`~/quantfut/releases/admob-recompensas-20261014/`; imagen previa conservada para volver atrÃ¡s (la migraciÃ³n es
aditiva: el cÃ³digo anterior la ignora). Comprobado en el dominio real: `/health` 200, `/app-ads.txt` 404 (sin ID de
editor), callback con firma invÃ¡lida 403, ticket sin sesiÃ³n 401, `/control/anuncios` tras Cloudflare Access,
resumen de monedas sin cambios para la app actual; el contenedor alcanza las claves pÃºblicas de Google.

Fallo encontrado SOLO al verificar en producciÃ³n: `/rewards/callback/{provider}` (ofertas) capturaba
`/rewards/callback/admob` y respondÃ­a 503 Â«Proveedor no configuradoÂ». Mis pruebas usaban una app mÃ­nima con solo el
router de anuncios y no lo veÃ­an. Corregido registrando el router de anuncios antes que el de ofertas y con una
prueba sobre la app completa (`test_el_callback_de_admob_no_lo_capturaâ€¦`). LecciÃ³n: en rutas con parÃ¡metro de
ruta genÃ©rico, probar el orden de registro con `main.app`.

Privacidad con AdMob desplegada (solo API; worker intacto): imagen `quantfut-api-admob:20261014c` sobre la anterior con solo
`legal_pages/privacidad.html` (la desplegada era idÃ©ntica a la base de la rama antes de copiar; tÃ©rminos y eliminar
cuenta, sin cambios). Fijada en el compose; respaldo en `~/quantfut/releases/privacidad-admob-20261014/`. Comprobado en el
dominio: 200, 5 menciones de AdMob, la frase Â«no estÃ¡ habilitadaÂ» ya no estÃ¡, versiÃ³n `2026-10-12` intacta. DecisiÃ³n: NO se
subiÃ³ `CONSENT_VERSION`: el servidor la compara con la que envÃ­a la app (`live_api.dart`) y rechazarÃ­a registros de las apps ya
instaladas. El `<script>` que se ve en las pÃ¡ginas pÃºblicas es la ofuscaciÃ³n de correo de Cloudflare (tambiÃ©n en tÃ©rminos);
el origen no sirve ninguno. Error propio al preparar: una primera comparaciÃ³n usÃ³ una ruta mal formada y dio Â«vacÃ­oÂ»; se
detectÃ³ antes de actuar y se repitiÃ³ bien.

TÃ©rminos con los videos con recompensa desplegados (solo API; worker intacto): imagen `quantfut-api-admob:20261014d` sobre la
anterior con solo `legal_pages/terminos.html` (la desplegada era idÃ©ntica a la base de la rama; privacidad ya coincidÃ­a con el
repo). Fijada en el compose; respaldo en `~/quantfut/releases/terminos-admob-20261014/`. Comprobado en el dominio: 200 en las
tres pÃ¡ginas legales, pÃ¡rrafo nuevo presente, versiÃ³n `2026-10-12` intacta, privacidad con AdMob, API sana y sin errores en logs.
Esta vez la comparaciÃ³n previa se protegiÃ³ contra una lectura vacÃ­a (hash de archivo vacÃ­o) antes de dar el paso por vÃ¡lido.

Anuncios activados en modo prueba en producciÃ³n (15-oct, a peticiÃ³n del titular Â«usa por mientras ID de modo pruebaÂ»): UPDATE de
`reward_settings` (`ads_enabled=TRUE`, `ad_test_mode=TRUE`) mÃ¡s fila en `admin_audit` con actor `claude:despliegue`, hecho por SQL
porque el panel estÃ¡ detrÃ¡s de Cloudflare Access sin sesiÃ³n disponible. Comprobado con el cÃ³digo real del servidor: ticket permitido
en Android e iOS con los bloques de prueba oficiales; sin sesiÃ³n nada se expone (`ads: {enabled: false}`, ticket 401). Riesgo
acotado: solo bloques de prueba y la app publicada no trae aÃºn el cÃ³digo. Sin comprobar: si los bloques de prueba envÃ­an el callback
SSV a `/rewards/callback/admob`; si no lo hacen, el saldo no sube y la app muestra Â«tus monedas llegarÃ¡n en unos instantesÂ».
Intento de leer los IDs desde el Chrome del titular: no tiene cuenta de AdMob (redirige al registro); no se creÃ³ ninguna.

## 2026-10-14 â€” APK de release no abrÃ­a (WorkManager / R8)

Causa: al aÃ±adir `google_mobile_ads` entrÃ³ una versiÃ³n de WorkManager cuyo `WorkDatabase_Impl`
se instancia por reflexiÃ³n; R8 conservaba la clase (`-keep class * extends RoomDatabase`) pero
eliminaba su constructor vacÃ­o, y `androidx.startup.InitializationProvider` mataba el proceso al
arrancar (antes de Dart, asÃ­ que Sentry/Crashlytics no lo habrÃ­an recibido). Se vio en `adb logcat`,
no en Sentry. Arreglo: `-keep class * extends androidx.room.RoomDatabase { <init>(); }` en
`android/app/proguard-rules.pro`. Verificado: release recompilado, instalado en el emulador, abre
sin `FATAL EXCEPTION`. LecciÃ³n: tras aÃ±adir un SDK con dependencias nativas, abrir el release en
emulador antes de darlo por bueno (el debug no pasa por R8).

## 2026-10-14 â€” Videos de prueba no acreditaban: crÃ©dito simulado solo en modo prueba

Causa: el video demo se vio y el ticket se pidiÃ³ bien, pero Google nunca llamÃ³ a `/rewards/callback/admob`
(Caddy sin llamadas, `reward_ad_events` vacÃ­a). Los bloques de prueba son de Google y no admiten nuestra
URL SSV, asÃ­ que no hay callback que acredite. DecisiÃ³n del titular: en lugar de montar un bloque real
con dispositivo de prueba, el servidor acredita por una vÃ­a de solo prueba (`/ads/test-credit`), limitada
al modo prueba Y a `QF_ADS_TEST_CREDIT_EMAILS`. La lista existe porque producciÃ³n estÃ¡ en modo prueba con
anuncios activos: sin ella cualquier cuenta cobrarÃ­a 5Ã—10 monedas al dÃ­a sin ver nada. Reusa `credit()`.
Verificado: 42 pruebas de anuncios con Postgres real (esquema aislado), Flutter 235 y analyze limpios.
Desplegado el 2026-10-14 (imagen `quantfut-api-admob:20261014e`, variable `QF_ADS_TEST_CREDIT_EMAILS` en el `.env`, respaldos en `~/backups/ads-test-credit-20261014`, vuelta atrÃ¡s = `pre-test-credit`). Probado por el titular en su telÃ©fono: las monedas se acreditan.

## 2026-10-15 â€” Â«Demasiadas solicitudesÂ» en Coins: escudos con contador propio

Causa: el lÃ­mite global es 60/min por IP y cuenta todas las rutas. Una pantalla de la app pide ~80
escudos (`/web/escudos/*.png`, uno por equipo) en un minuto; al pasar de 60 el servidor devolvÃ­a 429
tambiÃ©n a `/mobile/v1/rewards` y Coins quedaba con Â«ReintentarÂ». Medido en los logs de producciÃ³n
(05:55 UTC: ~95 solicitudes, 23 rechazadas). Arreglo: los escudos van a su propio contador
(`escudos:<ip>`, 10Ã— el lÃ­mite general), igual que `/control` y `/static`; el resto sigue en 60/min.
Pendiente posible: que la app cachee los escudos en disco para no repetir las descargas.

## 2026-10-15 â€” F2: cierres de Pinnacle, comprobando antes de pagar

Football-data parecÃ­a poder rellenar ~1.457 cierres de MÃ©xico, Argentina, Brasil y MLS; el
ensayo en producciÃ³n demostrÃ³ lo contrario (11.923 filas de Pinnacle desde 2024, todas ya
cargadas) y se descartÃ³ sin escribir nada. Para Europa se comprÃ³ histÃ³rico de The Odds API en
fases: prueba de 10 crÃ©ditos, 8.000 crÃ©ditos (801 snapshots) con reserva de 6.000 para la captura
en vivo, y carga solo tras ensayo, comprobaciÃ³n de integridad (RPS 0,1987 con las cuotas
emparejadas frente a 0,2357 uniforme: un emparejamiento errÃ³neo se verÃ­a) y respaldo. DecisiÃ³n
clave: un cierre solo se acepta si el snapshot estÃ¡ a <=30 min del inicio y el precio de Pinnacle
se moviÃ³ <=30 min antes; el emparejador usa ids de equipo, no nombres de liga, porque los clubes
ascendidos tienen su fila en otra divisiÃ³n. Huecos de modeladas: 1.861 a 697. Quedan para tras el
1-nov los snapshots de MÃ©xico, LaLiga, Serie A, Eredivisie y Primeira (~5.270 crÃ©ditos) y los alias
de Champions. Detalle: docs/f2_cierres_pinnacle_20261015.md.

## 2026-10-15 â€” F2c: el cierre ya no incluye precios de 60 minutos

Las cuotas `oddspapi_reconstructed` estÃ¡n, en el 74 % de los partidos, cortadas a 60 minutos del inicio
(precio a la hora del XI). Contra ellas el modelo parece mejor que el mercado y el CLV sale inflado, y el
reentrenamiento del 1-nov las habrÃ­a usado como cierre en su ventana de validaciÃ³n. DecisiÃ³n del usuario:
filtrarlas antes del reentrenamiento. Una sola funciÃ³n (`eval.cierre.es_cierre_real`) gobierna las seis
lecturas del cierre; se descartan 1.613 cierres de las ligas modeladas y se conservan los 739 cortados al
inicio. Desplegado solo en el worker: la API y el Ã¡rbol `~/quantfut/src` del servidor llevan versiones
antiguas de `train.py` y `clv.py` y sobrescribirlas habrÃ­a revertido cÃ³digo ajeno. El parche vive en el
contenedor, no en la imagen: hay que comprobarlo antes del 1-nov si se recrea. Detalle:
docs/f2_cierres_pinnacle_20261015.md.

## 2026-10-15 â€” Meta y compras en la app: diseÃ±o aprobado (sin cÃ³digo aÃºn)

El titular eligiÃ³ Google Play / App Store como procesador **de la app** (suscripciÃ³n renovable, sin
prueba gratis) y el enfoque Â«servidor fuente ÃºnicaÂ»: compras, registro y desbloqueos van a Meta solo
por Conversions API tras verificarlos, y el SDK solo manda lo que Ãºnicamente sabe la app. AsÃ­ no hace
falta deduplicar (Meta solo documenta el `event_id` del SDK en iOS) y una compra falsificada en la app
no llega a Meta ni da acceso. La App Events API `/{app-id}/activities` se descartÃ³: Meta ya no la
recomienda para integraciones nuevas. Seguimiento encendido por defecto en todo el mundo por decisiÃ³n
del titular, que asume el riesgo RGPD (Meta pide consentimiento previo en la UE); se conservan las
negativas explÃ­citas previas y los lÃ­mites de ATT y del ID de publicidad. Â«EMQ 10/10Â» no es
garantizable: se envÃ­an todos los datos legÃ­timos disponibles. Spec:
docs/superpowers/specs/2026-10-15-meta-compras-design.md.

## 2026-10-15 â€” Compras de tienda y Meta: implementadas y API desplegada (apagadas)

El titular pidiÃ³ ejecutar el plan y desplegarlo el mismo dÃ­a, asÃ­ que la API saliÃ³ antes del 1-nov; el worker no se tocÃ³.
DecisiÃ³n clave: la API se desplegÃ³ como capa sobre la imagen en ejecuciÃ³n con solo los 20 archivos de la rama, tras comprobar
que los 12 modificados eran idÃ©nticos a `main` en el contenedor; asÃ­ no se revirtieron las otras diferencias de la API.
El periodo de cada cobro sale de la tienda y no de `duration_days`, y una compra de prueba concede acceso pero no va a Meta.
Quedan apagadas las compras y el envÃ­o a Meta hasta tener credenciales. Pendiente: alinear el worker antes de activar CAPI.

## 2026-10-16 â€” Play Console: ficha, declaraciones y RTDN preparados

La prueba interna de QuantFut continÃºa activa. Por navegador se guardaron la ficha en espaÃ±ol con icono y grÃ¡fico destacado, las declaraciones de funciones financieras e ID de publicidad y el borrador completo de Seguridad de datos. Faltan capturas actuales, una cuenta dedicada de revisiÃ³n con Plus, PÃºblico objetivo y el cuestionario IARC; este Ãºltimo quedÃ³ preparado antes de aceptar sus condiciones.

En Google Cloud ya existen la cuenta de servicio y el tema `quantfut-play-rtdn`. Quedaron preparados, sin confirmar, el permiso de publicaciÃ³n para el servicio de notificaciones de Google Play y la activaciÃ³n de Android Publisher API. La primera clave JSON existe en Cloud pero no apareciÃ³ en Descargas, por lo que debe revocarse y sustituirse antes de habilitar compras. Estado y evidencias: `apps/mobile/docs/PLAY_CONSOLE_20261015.md`.

## 2026-10-17 â€” API-Tennis: muestra autenticada autorizada
Seis consultas correctas: 27 tipos, 10.360 entradas de catalogo, 445 partidos recientes, 228 futuros, 205 de una fecha 2025 y cinco en vivo. En recientes, 45 terminados ATP/WTA individuales tienen estadisticas; se comprobaron 1.138 pares numericos y consistencia saque/resto sin incidencias. No generalizar a ITF: solo 132/393 terminados globales tienen estadisticas. No hay inicio/final reales ni duracion en campos observados; por ello no habilitamos descanso horario con event_time. Originales con SHA-256 en .local/api_tennis_probe/20261017T211250Z, clave solo en configuracion ignorada, cero apariciones en artefactos. No se consulto The Odds API ni se alteraron modelos o protocolos. La integracion automatica y medicion de latencia quedan pendientes. Informe docs/tenis_api_tennis_prueba_20261017.md. Arnes inicial: 1.300 aprobadas/88 omitidas/dos avisos; Docker ausente.

## 2026-10-17 â€” Tenis: evaluador comun y carga observable, fase 1
Implementados BenchmarkEvaluator, RecentLoadExtractor, ModelRunner y correccion logistica ridge sobre log-odds del candidato actual. Corte estricto por disponibilidad anterior a decision; ventanas con incertidumbre y datos faltantes explicitos. Recalculo temporal de features en ajuste, control de orientacion, resultados completados y muestra comun. API-Tennis no acredita inicio/final reales: normalizador no usa fecha programada como final exacto. Muestra real sin red: 104 observaciones normalizadas, dos pronosticos base actuales, cero entrenamiento/candidato carga y cero evaluables por futuros pendientes; metricas nulas, sin simular mejora. 24 nuevas pruebas y 75 totales tenis aprobadas. Los 12 hashes del protocolo previo intactos. Informe docs/tenis_carga_evaluacion_fase1_20261017.md. Motor de futbol y apuestas intactos.
Validacion final fase 1: 75 pruebas tenis aprobadas; arnes general 1.300 aprobadas/88 omitidas/dos avisos en 226,35 s. Los cuatro hashes de implementacion coinciden con report.json; cero apariciones de clave en los nuevos entregables.

## 2026-10-17 â€” Tenis: captura de estados y Weighted Elo
Captura con limite diario local, originales/recibos SHA-256, tabla append-only y consultas as-of. No inferir terminado por ausencia en vivo, ni convertir observacion en inicio/final reales sin conocer latencia. Correccion terminal->en vivo invalida carga posterior sin borrar pasado. Importadas 883 observaciones previas (incluido historial 2025), dos consultas ATP/WTA nuevas aportaron 113; total 996 observaciones/879 eventos, cero conflictos. Seis hashes de recibo validos, cero claves en resultados. No hay tarea periodica activa ni consumo nuevo de The Odds API.
WElo original segun ecuaciones del articulo, K con conteo previo explicito y adaptacion simultanea por periodos semanales. Mismas filas de entrenamiento/embargo35 y prueba congelada2026: ATP n2451 logloss WElo0,629374 vs hibrido0,622427; WTA n2146 0,629068 vs0,618318. Mejor que Elo adaptativo no ponderado, inferior al hibrido; no se promueve. Bootstrap por periodo exploratorio, no prueba financiera ni reproduccion diaria exacta. 96 pruebas tenis aprobadas (21 nuevas), 12 hashes del protocolo anterior intactos. Informe docs/tenis_estados_weighted_elo_20261017.md.
Verificacion final estados/WElo: 96 pruebas tenis aprobadas y arnes general 1.300 aprobadas/88 omitidas/dos avisos en 145,62 s. Fuentes/codigo de ambos reportes v2 verificados. La pagina publica de API-Tennis anuncia Starter 8.000 solicitudes/dia y prueba14dias; plan/vigencia de esta cuenta aun por confirmar para fijar frecuencia recurrente. No confundir con The Odds API de pago ya confirmado.

## 2026-10-17 â€” Plan de API-Tennis sin confirmar
El titular responde Â«Periodo de prueba / no sÃ©Â». Registrado como posible prueba, sin cuota ni vencimiento acreditados, en data/tennis/state_capture_20261017/account_policy.json. Mantener tope local de 24 consultas/dia del capturador; no implica cuota de la cuenta. Programacion automatica pendiente. No cambia The Odds API de pago ni sus 2.000 creditos mensuales de tenis y reserva de 6.000. Sin nuevas consultas ni cambios de codigo.

## 2026-10-17 â€” Web: interfaz sports intelligence HUD

DecisiÃ³n clave: conservar el frontend nativo y su lÃ³gica completa, y aplicar el rediseÃ±o en una capa
`future.css` cargada al final. La separaciÃ³n evita mezclar presentaciÃ³n con contratos de datos y hace
reversible el cambio sin reescribir las ocho vistas. Tras la revisiÃ³n del usuario se integrÃ³
CYBERCORE CSS 0.3.0 como dependencia exacta: `postinstall` copia su distribuciÃ³n y licencia MIT a
`frontend/vendor/cybercore/`, por lo que producciÃ³n no depende de CDN. Las vistas reciben sus clases
reales de tarjetas, botones, insignias, entradas, tablas, alertas, bordes neÃ³n, scanlines y datastream.
Cyberpunk CSS se mantiene como referencia porque sus reglas globales colisionan con la aplicaciÃ³n; se
adaptaron sus cortes geomÃ©tricos y alto contraste. La paleta ahora usa los tokens oficiales cian
#00f0ff, magenta #ff2a6d, amarillo #fcee0a, verde #05ffa1 y void #0a0a0f, con iconografÃ­a SVG propia.
El frontend conserva foco, texto de estados, objetivos tÃ¡ctiles y `prefers-reduced-motion`; no se
desplegÃ³ ni se modificÃ³ el motor.

ValidaciÃ³n final del rediseÃ±o: 25/25 pruebas del frontend y arnÃ©s general con 1.300 aprobadas,
88 omitidas y dos avisos en 126,80 s. `docker-compose.yml` vÃ¡lido; Docker no estaba disponible en
este entorno. El servidor local inicia en `127.0.0.1:5173`; la comprobaciÃ³n HTTP automatizada quedÃ³
limitada por los permisos de sockets del entorno, no por un error de la aplicaciÃ³n.

## 2026-10-17 â€” Tenis: sedes por edicion y vigencia
Implementado VenueRegistry relacional de solo adicion, fuentes SHA-256 por campo, versiones y enlaces exactos proveedor/modalidad/temporada con vigencia local. Enriquecimiento exige UTC y recepcion previa a decision. Bruselas cambia P12->P5 el 23-oct; se resuelve por fecha local, sin heredar Marsella para Lyon ni imputar techos. Ocho recintos, siete ediciones, quince enlaces, 24 fuentes verificadas. Archivo228:102/102 ATP/WTA enlazados con coordenadas;126 sin sede y48 fechas2026 con temporada2025 marcadas. Altitudes desconocidas: servicio de elevacion no disponible, no imputar ciudad/EXIF. Sin API deportivas nuevas ni cambios al modelo; doce hashes prospectivos intactos. 116 pruebas tenis aprobadas (20 nuevas). Informe docs/tenis_sedes_verificadas_20261017.md.
Verificacion final sedes: 116 pruebas tenis aprobadas y arnes general 1.300 aprobadas/88 omitidas/dos avisos en 116,35 s. Docker ausente. Hash del modulo y semilla coinciden con informe v2; PENDIENTES actualizado con alcance y campos externos pendientes.

## 2026-10-17 â€” Tenis: aclaracion no comercial y Open-Meteo
El usuario aclara que este proyecto de tenis no esta monetizado. Utilizar Open-Meteo publico sin clave; la referencia previa a Standard procede del contexto de futbol y no es requisito para tenis. No altera The Odds API de pago ni sus 2.000 creditos mensuales. Documentacion oficial de elevacion/terminos revisada. Una consulta exitosa recibida 18-oct02:59:53UTC devuelve Almaty756,LDLC194,P12:73,P5:83,Shanghai20,Wuhan48,Ningbo9,Osaka5 metros. Son estimaciones del modelo Copernicus DEM2021 GLO-90, resolucion horizontal90m, no cota medida de pista. Fuente y atribucion guardadas; no imputar altitud de ciudad.
Semilla registry_seed_open_meteo_v2.json conserva original y enlaces, agrega fuente25 y ocho revisiones posteriores a recepcion. calendar_report_v3_open_meteo.json:102/228 con altitud, mismos102/102 ATP/WTA. Verificados hash, orden y coordenadas, valores finitos, semilla original intacta y consultas previas siguen con altitud desconocida. 126 encuentros sin sede y48 discrepancias no resueltos por elevacion. Sin consultas deportivas, cambios a probabilidades ni captura meteorologica. Informe docs/tenis_open_meteo_20261017.md. Validacion:116 pruebas tenis aprobadas; arnes general1300 aprobadas/88 omitidas/2avisos en127,80s, Docker ausente. Solo metadatos/documentacion, sin modificaciones de codigo.

## 2026-10-18 â€” Tenis: sedes pendientes y temporada revisada
Las 48 discrepancias eran cuatro IDs en tres ediciones: Guangzhou22, Lisboa18 y Cali8. Contrastadas fuentes ATP/WTA, ITF y organizadores; se corrige metadata de edicion2025->2026 por evento/digest, no por una regla generica de fecha. FixtureReviews exige fila exacta en original archivado, fuentes integras y registradas antes de decision, conserva original/correccion y bloquea cambios de fila, conflictos y cuarentenas. Se agregaron 27recintos/37alias para126encuentros; total35recintos52enlaces228/228con sede principal. Heraklion hombresLyttos/mujeresNANA; RoanneprincipalVacheresse, no reutilizar tabla historicaScarabee. No acreditar pista individual ni horario por esta revision.
La cobertura espacial sigue102/228: coordenadas/altitudes desconocidas en27recintos nuevos. Extraccion OSM acotada fallo406/502/timeout; no imputar centros de ciudad. Dos consultas ZenRows existentes recuperaron paginas oficiales Cali/Jinan; cero consultas deportivas/TheOddsAPI. Originales HTTP y extracciones web diferenciadas, recibos/hash;65 fuentes verificadas. Artefactos data/tennis/venues_completion_20261017/calendar_completed_v2.json,registry_seed_completed.json,season_reviews.json,integration_audit.json. Modelos intactos,12hashes prospectivos verificados. Auditoriareal a decision anterior conserva102sedes,0correcciones y48flags: no fuga retrospectiva.
Validacion del checkout entregado:126tests tenis aprobados, diez nuevos. Arnes general1300aprobados/88omitidos/2avisos79,88s, Docker ausente; diffcheck correcto. Pendientes de identidad de sede y revision de temporada cerrados para esta muestra; georreferenciacion nueva y variables viaje/clima siguen aparte. Informe docs/tenis_sedes_temporadas_completadas_20261018.md.

## 2026-10-18 â€” Tenis: revision cientifica de viajes
Revision documental de fuentes oficiales ORS/OSRM/Amadeus/Arcascope y consensos deportivos. No adoptar score 0,4/1,8/1,2 ni umbral10 como validados. Distancia/800+2,5 queda como escenario hipotetico sin respaldo ATP/NBA verificado. Entre torneos solamente; no inferir viaje directo, llegada, descanso efectivo o vuelo tomado. Intervalo ultima participacion-debut e indicadores de incertidumbre separados. Plan en docs/tenis_viajes_criterios_20261018.md; georreferenciacion27 sigue pendiente, cobertura espacial confirmada102/228. Solo documentacion, sin codigo ni nuevas consultas deportivas/rutas/vuelos.


## 2026-10-18 â€” Tenis: 27 coordenadas y modulo intertorneos
Cerrada georreferenciacion de27recintos con selecciones explicitas OSM/Nominatim/Photon, GPS oficiales y cuatro extracciones publicas de navegador etiquetadas. Rechazados bus/calle homonimos, estadio futbol y encuadres. China usaWGS84, noGCJ02. Una peticion Open-Meteo gratuita entrega27cotas DEM90m; geometria representa recinto/complejo y precision150-1100m es margen conservador, no medicion. Semilla89revisiones35recintos52enlaces112fuentes. Calendario archivado228/228 con coordenadas/altitud,48correcciones; asof previo sigue102/228. No afirmar pista, techo o horario real. Docehashes congelados intactos.
TravelExtractor requiere evidencia previa integra y cierre de participacion incluyendo dobles; no viajes por cambio de pista. DiferenciaUTC al mismo instante conDST, direccion y linea de fecha, distancia/altitud, transporte candidato configurable; intervalo salida a debutprogramado separado de descanso/arrival. Context legacy deja de inferirviajes entre partidos. Historial879eventos,614terminados/retirados,183/456participaciones con candidato porfecha programada; cero transiciones totalmente verificadas, sin horasreales acreditadas. Datos listos no equivalen a eficacia predictiva.143tests tenis entregados aprobados,17nuevos; primer intento con temporalesdel sistema fallo porpermisos, repeticion en workspace limpia. Sinconsultas API deportivas/creditosOdds ni entrenamiento. Informe docs/tenis_coordenadas_viajes_20261018.md.

Verificacion final coordenadas/viajes: arnes general1300aprobados/88omitidos/2avisos138,58s, Docker ausente;143tests tenis entregados aprobados8,60s. Diffcheck tenis correcto y hashes stage/entrega coinciden; entrega auditada en data/tennis/coordinates_20261018/delivery_audit.json.


## 2026-10-18 â€” Tenis: comparador espacial y sensibilidad
SpatialExperiment implementado: base, residualridgeespacial y nueve escenarios experimentales de intervalo. EscaladoRMS/coeficientes soloentrenamiento, interseccioncomun de tresfamilias/todosescenarios, sin seleccionarporprueba; logloss/Brier/ECE10. Horasmainintactas; experimentalrequiere diasreales verificados, conserva horasconocidas, rechaza semanas/DSTambiguo. Cierres12/18/23 perturbadosporjugador con ordenIDinvariante; aplicar igualcambioados cancela ladiferencia y no sirvecomosensibilidad. Hashesfuentes/matriz e IDs entrenamiento registrados.
Auditoriareal ejecutada v3: archivo492251 corte16oct anterioraprimerascoordenadas; snapshot228sinresultadoscompletadosobjetivo en estados;0transicionesverificadas. Entrenamiento/pruebacomunes0,0modelosajustados,metricasnull y sensibilidadrealnoejecutada. No backfill asof ni datos sinteticos paraafirmarrendimiento. Once testsnuevos,154tenisaprobados. Doc docs/tenis_comparacion_espacial_20261018.md; protocolo/report data/tennis/spatial_trial_20261018_v3. CeroAPIsdeportivas/creditosOdds, docehashescongeladosintactos. Holdoutexistentenoreutilizadoparanuevaseleccion.

Verificacion final comparador espacial:154pruebas tenis aprobadas en entrega, arnesgeneral1300/88omitidas/2avisos139,58s, Docker ausente. Diffcheck correcto; hashesdelcodigo/protocolo/reportecoinciden. Deliveryaudit registra0modelosrealesajustados, no confundir pruebas sinteticas con mejora predictiva.


## 2026-10-18 â€” Tenis: reconstruccion retrospectiva 2024/2025
Autorizada por usuario una rama retrospectiva separada, no backfill asof. Directorios ATP2024/25, notas WTA por edicion e ITF Paris2024 archivados; correcciones Dallas/Bruselas/Hangzhou/Belgrado/Atenas, Paris por temporada.187ediciones enlazadas,160georreferenciadas,27sede conocida sincoordenadas;95recintos,78concoordenadas yDEM,122fuentesSHA verificadas. Sinherencia de enlaces2026. OpenMeteo1consulta72puntos, Nominatim serialcache1,25s, candidatos ambiguos rechazados.
HistoricalDataset: historial38936filas2023â€“25, objetivo11240/472bloques. Antecedente inmediato observado sin saltarunknowns, incluye Challenger/qualy, noherencia sedequaly. Variables distancia/deltaaltitud/deltaUTC; DSTambiguo queda rango, guardaconservadora7dias porperiodo. No descanso/imputaciones dehora niitinerarioreal.3155convariablescompletas antesfiltros,2982aptos(1426desarrollo2024/1556exploratorio2025);26,53%coberturaobjetivo. Particiones5661/5378/201cuarentena porfrontera, edicionescompletas.165tests tenis entregados aprobados,11nuevos,12hashescongelados intactos. Datos+proveniencia+splits+pendientes en data/tennis/historical_venues_20261018; doc docs/tenis_dataset_historico_20261018.md. CeroOdds/API-Tennis,0modelosajustados,metricaspendientes. Falta cobertura52edicionesindividuales,17recintos(27ediciones),233bloquesporequipos/multisede; no interpretarpreparacioncomo eficacia. Comparacion exigira interseccionpredicciones no simplementecohortedatos.
Verificacion final retrospectiva: arnes general1300aprobados/88omitidos/2avisos115s; Docker no disponible. Entrega165tests tenis aprobados16,66s. Diffcheck entrega correcto, auditoria hashes/dataset/particiones aprobada.

## 2026-10-18 â€” Comprometer-revelar de la cadena y plan de F7
DecisiÃ³n: al repo pÃºblico va solo el compromiso (recibo y `LEDGER.md`); el JSON del lote sube cuando todos los partidos que cita constan terminados y pasaron 4 h (tope de 7 dÃ­as para aplazados). Por quÃ©: el lote lleva los picks de pago y publicarlo antes de los partidos los regala. El hash no cambia, asÃ­ que ningÃºn lote ya sellado se altera; `verify` ahora recorre por recibos y cuenta aparte los lotes sin revelar, y sigue detectando JSON alterado y cadena rota. `seal()` revela los pendientes al inicio de cada pasada, sin tocar `daily.py` ni el orden predecir â†’ seleccionar â†’ sellar â†’ publicar. `CHAIN_GIT_REMOTE` sigue vacÃ­o: falta desplegar con ensayo. Pruebas: `tests/test_hashchain_revelado.py` (8) y suite completa 1308 aprobadas / 88 omitidas.
Hallazgo para F7 (`docs/superpowers/plans/2026-10-18-f7-sello-tardio.md`): con varios lotes por dÃ­a, los cuatro lectores que unen `prediction_batches` por fecha contarÃ­an cada fila varias veces; hay que filtrarlos por `batch_kind = 'diario'` en el mismo cambio.
MediciÃ³n contra producciÃ³n (solo lectura): cierres de Pinnacle faltantes en ligas modeladas = 697 (coincide con PENDIENTES); el CLV en sombra de +3,46 % (n=142) no se reproduce con ninguna fuente (ver PENDIENTES); el servidor dejÃ³ de responder por SSH durante la sesiÃ³n.

## 2026-10-18 â€” RediseÃ±o CYBERCORE desplegado

Los PR #12 y #13 quedaron fusionados con CI verde. El segundo fue necesario porque producciÃ³n sirve la
web desde FastAPI y debÃ­a exponer explÃ­citamente `future.css` y el CSS vendorizado de CYBERCORE. Para no
revertir las diferencias histÃ³ricas de la API se construyÃ³ `quantfut-api-cybercore:2d8cfef` sobre la
imagen que ya estaba en ejecuciÃ³n y se sustituyeron Ãºnicamente `frontend/` y `src/qf/api/web.py`.
Dominio y assets responden 200, los hashes coinciden con `main`, la comprobaciÃ³n visual no mostrÃ³ errores
de consola, el modelo sigue en `2026.09.27-010508` y los 19 lotes verifican. Worker, base y flags intactos;
respaldo y reversiÃ³n en `DEPLOYS.md`.

## 2026-10-18 â€” Tenis: cierre de las tres colas histÃ³ricas originales

Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de ediciÃ³n, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliaciÃ³n siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.

Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geogrÃ¡ficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigÃ¼edad de mÃºltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni mÃ©tricas nuevas;2025exploratorio, comparaciÃ³n de predicciones pendiente.

173pruebas tenis aprobadas en preparaciÃ³n y entrega; regresiÃ³n con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canÃ³nico/CSV verificados por auditorÃ­a. ArnÃ©s general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesiÃ³n aÃ±adiÃ³8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni crÃ©ditos; una consulta Open-Meteo69puntos para elevaciÃ³n. Informe docs/tenis_cobertura_historica_completada_20261018.md; mÃ³dulo, pruebas, constructores y auditorÃ­a entregados al motor aislado. PrÃ³ximo paso: comparaciÃ³n Base/Base+Espaciales en intersecciÃ³n comÃºn y completar las coordenadas adicionales pendientes.

## 2026-10-18 â€” Acceso con Google en la web

Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de ediciÃ³n, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliaciÃ³n siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.
Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geogrÃ¡ficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigÃ¼edad de mÃºltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni mÃ©tricas nuevas;2025exploratorio, comparaciÃ³n de predicciones pendiente.
173pruebas tenis aprobadas en preparaciÃ³n y entrega; regresiÃ³n con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canÃ³nico/CSV verificados por auditorÃ­a. ArnÃ©s general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesiÃ³n aÃ±adiÃ³8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni crÃ©ditos; una consulta Open-Meteo69puntos para elevaciÃ³n. Informe docs/tenis_cobertura_historica_completada_20261018.md; mÃ³dulo, pruebas, constructores y auditorÃ­a entregados al motor aislado. PrÃ³ximo paso: comparaciÃ³n Base/Base+Espaciales en intersecciÃ³n comÃºn y completar las coordenadas adicionales pendientes.
## 2026-10-18 â€” Acceso con Google en la web


Resueltas 52 ediciones individuales con evidencia de su temporada, los 17 recintos originales con WGS84/terreno/zona horaria y 233 bloques por equipos (225 Davis, dos finales BJK y seis multicidad con 178 enlaces por partido). Seis revisiones de identidad/fase preservan los originales. Registro ampliado: 466 enlaces de ediciÃ³n, 178 por partido, 240 entradas de sede incluidas equivalencias y 280 fuentes con SHA. De las 240 entradas, 152 tienen coordenadas; otras 88 identificadas en la ampliaciÃ³n siguen pendientes, distintas de los 17 recintos originales. Kempes/Jiujiang son referencias de complejo con tolerancia amplia, no coordenadas exactas de pista.

Dataset separado en data/tennis/historical_coverage_20261018: identidad de sede 11240/11240, coordenadas de destino 10510/11240, variables completas ambos jugadores 6126 y cohorte apta 5798 (51,58%; 2965 desarrollo2024/2833 exploratorio2025). Sensibilidad sin referencias geogrÃ¡ficas amplias:5569. 472 bloques originales agrupados en384competiciones indivisibles;201filasfrontera en cuarentena. Se preservan antecedentes desconocidos, ambigÃ¼edad de mÃºltiples sedes y horas ausentes. Fuentes recibidas2026sin backdating. No ajuste ni mÃ©tricas nuevas;2025exploratorio, comparaciÃ³n de predicciones pendiente.

173pruebas tenis aprobadas en preparaciÃ³n y entrega; regresiÃ³n con registro anterior reproduce2982aptos;12hashes congelados intactos, fuentes/canÃ³nico/CSV verificados por auditorÃ­a. ArnÃ©s general inicial1300/88/2; final1308aprobados/88omitidos/2avisos150,98s (otra sesiÃ³n aÃ±adiÃ³8pruebas). Docker no disponible. Sin consultas Odds/API-Tennis ni crÃ©ditos; una consulta Open-Meteo69puntos para elevaciÃ³n. Informe docs/tenis_cobertura_historica_completada_20261018.md; mÃ³dulo, pruebas, constructores y auditorÃ­a entregados al motor aislado. PrÃ³ximo paso: comparaciÃ³n Base/Base+Espaciales en intersecciÃ³n comÃºn y completar las coordenadas adicionales pendientes.

## 2026-10-18 â€” Acceso con Google en la web

- DecisiÃ³n: el navegador solo obtiene el ID token (SDK web de Firebase, `frontend/google-auth.js`) y el servidor
  lo cambia por la MISMA sesiÃ³n de cookie HttpOnly del correo (`POST /app/v1/firebase/web-session`). AsÃ­ Firebase no
  guarda estado en la pÃ¡gina y el resto de la web/checkout sigue usando `cuenta-api.js`.
- La config web sale de `GET /app/v1/firebase/web-config` (env `FIREBASE_WEB_*`), no del repo. Cerrada con 503 hasta
  que existan las variables y `FIREBASE_AUTH_ENABLED=1`.
- Cuenta nueva exige casilla de tÃ©rminos/privacidad (`CONSENT_VERSION`). Un correo ya registrado con contraseÃ±a da
  `vinculacion_requerida`: no se vincula por correo automÃ¡ticamente (regla existente).
- Pendiente del titular: registrar app Web en Firebase, aÃ±adir el dominio a Â«Dominios autorizadosÂ» y poner las 3 variables.
- Verificado en local con popup real de Google: sesiÃ³n creada y Â«Mi cuentaÂ» abierta. Despliegue preparado, no ejecutado: `docs/despliegue_google_web_20261018.md` (producciÃ³n lleva un frontend Cybercore sin comitear; comitearlo antes).
- Siguiente: Whop (checkout embebido + webhooks `payment.succeeded`) y Pixel + CAPI web con `event_id` compartido.


## 2026-10-18 â€” Tenis: comparaciÃ³n espacial retrospectiva ejecutada
DecisiÃ³n: no activar la correcciÃ³n espacial. Base hÃ­brida Markov/Elo reconstruida por orÃ­genes2023/24/25, mezclas calibradas con predicciones del aÃ±o anterior y embargo35dÃ­as, sin usar coeficientes actuales hacia atrÃ¡s. Ajuste espacial ridge1 con2965partidos desarrollo2024, evaluaciÃ³n comÃºn2833en2025exploratorio(52,68% de5378). LogLoss0,6387331418â†’0,6386822788; deltaâˆ’0,000050863, intervalo95%por116competiciones[âˆ’0,000159672;+0,000054898]. Brier0,2243935574â†’0,2243696603;ECE0,026213â†’0,026260. Intervalos incluyen cero, calibraciÃ³n no mejora.
Sensibilidad sin tolerancias geogrÃ¡ficas>1000m:2851train/2718test,deltaLLâˆ’0,0000764803,intervalo[âˆ’0,000194240;+0,000025873]. Mismos IDs entre variantes dentro de cada escenario; distintas muestras entre escenarios.2025no usado para ajustar ni elegir ridge; evidencia retrospectiva recibida2026, no validaciÃ³n asof real ni itinerarios/descanso exactos. Se preserva agrupaciÃ³n por competiciÃ³n completa. Intervalos descriptivos sin toda dependencia entre jugadores.
Entrega en motor aislado: historical_comparison.py, runner y auditorÃ­a,9tests nuevos;182pruebas tenis aprobadas en preparaciÃ³n y entrega. AuditorÃ­a reproduce ajustes y mÃ©tricas, verifica fuentes y12hashes congelados intactos. Resultados/protocolo/predicciones/calibraciÃ³n en data/tennis/historical_comparison_20261018; informe docs/tenis_resultados_espaciales_historicos_20261018.md.0llamadas deportivas/0crÃ©ditos Odds. PrÃ³ximas mejoras deben elegir especificaciÃ³n en entrenamiento y reservar periodo futuro nuevo; la ampliaciÃ³n de88sedes sigue pendiente. ArnÃ©s inicial1310/88/2aprobado; verificaciÃ³n final en curso.
VerificaciÃ³n final comparaciÃ³n: arnÃ©s general1310aprobados/88omitidos/2avisos145,51s; Docker no disponible. CoincidenciaSHA de4archivos entregados y diffcheck correctos; auditorÃ­a entregada ejecutada sin errores. No trabajo de esta fase pendiente de verificaciÃ³n.


## 2026-10-18 â€” Tenis: carga observable por rondas
DecisiÃ³n: conservar correcciÃ³n experimental, sin activarla. Ventanas3/7d siguen bloqueadas:152terminales API-Tennis de Ãºltimas revisiones archivadas tienen lÃ­mite inferior desconocido; no se transformaron fechas programadas/recibos en horas reales. Nueva carga distinta: puntos de totales al saque, juegos/sets de marcadores completos y partidos decisivos de rondas anteriores del mismo cuadro individual; sin dobles, qualies, torneos previos ni tiempo transcurrido supuesto.
Base histÃ³rica previa reutilizada porSHA. Tres variantes en intersecciÃ³n comÃºn: Base, Base+Cobertura, Base+Cobertura+Carga. Ajuste solo2024,ridge1,RMSentrenamiento;2130train/1957test2025exploratorio(36,39%),993ATP/964WTA. LL0,615696â†’0,615221;deltaâˆ’0,000475307,IC95%[âˆ’0,00110306;+0,00015902];contra cobertura deltaâˆ’0,000408593,ICincluyecero. Brier0,213501â†’0,213225;ECE0,028584â†’0,026355. Sensibilidad contadores observados completos1882/1700,LL0,611986â†’0,611413,ICincluyecero. No declarar superioridad ni rentabilidad.
RevisiÃ³n detectÃ³ pÃ©rdidas seguidas de avance en finalesBJK2024: eran partidos por equipos, una derrota individual no elimina necesariamente a la selecciÃ³n. Se corrigiÃ³ el alcance para excluir todos los equipos y grupos; versiÃ³n preliminar draw_load_20261018 retirada porSUPERSEDED.json, vÃ¡lida draw_load_20261018_v2. No correcciÃ³n de datos originales ni selecciÃ³n por mÃ©tricas. AuditorÃ­a reproduce10407formatoscompatibles/4378conpreviojuegoambos antesfiltros, contadores yprecedencia,coeficientes/mÃ©tricas.194pruebas tenis aprobadas en entrega,12nuevas;12hashescongelados intactos. Cola88sedes/730destinos priorizada,5primeras264destinos.0APIdeportivas/0crÃ©ditosOdds. Informe docs/tenis_carga_rondas_resultados_20261018.md. ArnÃ©s general inicial1310/88/2en224,53s; final1310/88/2en324,67s, Docker ausente.

## 2026-10-18 â€” Cobro web con Whop (checkout embebido + webhooks) y Meta web


## 2026-10-18 â€” Cobro web con Whop (checkout embebido + webhooks) y Meta web

- DecisiÃ³n: el servidor crea la `checkout_configuration` (con `qf_account_id` en `metadata`) y el navegador solo monta `ch_â€¦`
  en el elemento Checkout; el acceso lo concede Ãºnicamente `payment.succeeded` (firma Standard Webhooks, idempotente por
  `webhook-id` y por `payment_id`). AsÃ­ ni la web ni la metadata del cliente pueden conceder acceso.
- Dedupe Pixelâ†”CAPI: `purchase:<ch_id>` (existe antes del pago, por eso el navegador ya lo conoce) e `ic:<ch_id>`; el contexto del
  navegador (fbp, fbc, IP, UA, URL) se guarda al crear el checkout para que el Purchase de servidor lo lleve (EMQ).
- `meta_events` ganÃ³ `action_source`/`web_context`; el cron de CAPI del worker debe actualizarse con la prÃ³xima alineaciÃ³n del worker
  ANTES de activar `META_CAPI_ENABLED` con trÃ¡fico web (el cÃ³digo viejo ignorarÃ­a `web_context`).
- Hallado: el payload de `payment.succeeded` y la membresÃ­a solo estÃ¡n en el OpenAPI (requiere login); los campos usados salen de las
  pÃ¡ginas de objetos Payment/Membership. Reembolsos: no hay evento documentado; se revoca por `membership.updated` en `canceled`/`expired`.
  Verificar con una entrega real y aÃ±adir `refund` si Whop lo emite.
- El sandbox de Whop no cubre Elements todavÃ­a: la primera prueba real del formulario serÃ¡ en producciÃ³n con un plan barato.


## 2026-10-18 â€” Tenis: cinco sedes prioritarias verificadas
HuaHin por mapa enlazado porpropietario yOSMtenis71mdediferencia;SeÃºl porgeometrÃ­a estadioOSMrel8679966 yoperador/Wikidata61m;AbuDabi objeto93051899tenis corroborado enidentidad poroperador,sin fingirsegunda mediciÃ³n;Carpena coordenadasJuntaAndalucÃ­a yestadioOSM18m,no parada detaxis. YucatÃ¡n punto delcomplejo enlazado porpropietario a1102mdelÃ¡reatenisOSM;1800mtolerancia ycoarseflag,no pistas2024/25precisasproyectadas. RechazadaslocalidadhomÃ³nima,centrosgenÃ©ricosparque/estadiofÃºtbol. Fuentes archivadasconrecibosreales,erroresdevueltosnocuentancomoevidencia.1OpenMeteopÃºblico5puntos,terreno5/6/23/6/20m,noalturamedidapista.
Registroseparado data/tennis/historical_geography_top5_20261018:294fuentes,240entradas(157concoordenadas,83pendientes); enlacesdeediciÃ³nypartidointactos.11240objetivos,10774destinosconcoordenadas(+264),6651variablescompletasambos,6244aptos(+446),5943sinreferencias>1km.3226desarrollo2024/3018exploratorio2025;201frontera.264destinosy446transicionesaptas no sonlamismamÃ©trica. Nuevosaptos261desarrollo/185exploraciÃ³n. Pendientes466destinos;colaactualChennai31/Palermo31/Riad30/Hengqin15/Shenzhen14.
AuditorÃ­avalida5cambiosdeentrada,recibos/CSV/canÃ³nico,particionesyobjetivosidÃ©nticos,los5798aptosanterioressiguenconvariablesnumÃ©ricasidÃ©nticas,experimentos/datasetsanterioresnohansidosobrescritos,12hashescongeladosintactos.194teststenisaprobados;constructoryauditorentregadosyejecutadosdesdecheckoutaislado,diffcheckcorrecto.0Odds/API-Tennis,0crÃ©ditos;0ajustesymÃ©tricasnuevas,nomodificaprobabilidades. Informe docs/tenis_cinco_sedes_verificadas_20261018.md. ArnÃ©sinicial1315/94/2en119,16s;finalpendientedecierre.
VerificaciÃ³n final cinco sedes: arnÃ©s general1315aprobados/94omitidos/2avisos123,15s,Docker ausente;194tenis aprobadas,2scripts entregados conSHA coincidente, auditorÃ­a desde motoraislado aprobada. Fase completada;83entradas geogrÃ¡ficas yclocks siguenpendientes explÃ­citos.

## 2026-10-18 â€” Meta web con EMQ alto y envÃ­o real de CAPI

- El contexto del navegador (fbp, fbc, IP, user agent, URL) se lee de las cookies y cabeceras de la propia peticiÃ³n web: no hace falta que el cliente lo mande y no se puede
  confundir con el de otra sesiÃ³n. Aplica a registro por correo, Google y checkout.
- EMQ: a lo que ya habÃ­a se aÃ±aden ciudad, estado, cÃ³digo postal y telÃ©fono de la facturaciÃ³n de Whop (normalizados y cifrados). Probado en Â«Probar eventosÂ»: 13 claves de cliente.
- El token de Conversions API se generÃ³ con la opciÃ³n Â«sin Dataset Quality APIÂ»: la otra es irreversible y no hacÃ­a falta.
- Mientras `META_TEST_EVENT_CODE` estÃ© puesto, nada llega a los eventos reales; el paso a producciÃ³n es quitar esa lÃ­nea (decisiÃ³n del titular tras ver el EMQ).
- El worker no lleva `meta_capi` (alineaciÃ³n pendiente): el cron del host envÃ­a cada 5 min. Es transitorio.
## 2026-10-18 â€” AclaraciÃ³n de las dos cifras que no cuadraban
CLV: la puerta comercial lee `publish.shadow_sharp.report()` (ofertas publicables de la sombra sharp). Esa medida da hoy n=213 con cierre justo, `ev_close` +3,07 % (IC95 +1,54 a +4,67); el +3,46 % (n=142) del 15-oct era la misma medida con menos muestra. `shadow.summary` y `shadow_results` miden los retadores de XI (nâ‰ˆ135, evâ‰ˆ+0,06 %): otra cosa, y coherente con que el XI aÃºn no aporta frente al cierre. La puerta sigue cerrada por n<300 y porque ninguna liga llega a 30 (la mayor, MLS, 18). xG: los 1.219 huecos son exactos para Â«terminados desde 2024-01-01, sin xG de alguno de los dosÂ»; mi cuenta anterior usaba otra ventana.

## 2026-10-18 â€” Meta web con EMQ alto y envÃ­o real de CAPI

- El contexto del navegador (fbp, fbc, IP, user agent, URL) se lee de las cookies y cabeceras de la propia peticiÃ³n web: no hace falta que el cliente lo mande y no se puede
  confundir con el de otra sesiÃ³n. Aplica a registro por correo, Google y checkout.
- EMQ: a lo que ya habÃ­a se aÃ±aden ciudad, estado, cÃ³digo postal y telÃ©fono de la facturaciÃ³n de Whop (normalizados y cifrados). Probado en Â«Probar eventosÂ»: 13 claves de cliente.
- El token de Conversions API se generÃ³ con la opciÃ³n Â«sin Dataset Quality APIÂ»: la otra es irreversible y no hacÃ­a falta.
- Mientras `META_TEST_EVENT_CODE` estÃ© puesto, nada llega a los eventos reales; el paso a producciÃ³n es quitar esa lÃ­nea (decisiÃ³n del titular tras ver el EMQ).
- El worker no lleva `meta_capi` (alineaciÃ³n pendiente): el cron del host envÃ­a cada 5 min. Es transitorio.

## 2026-10-19 Â· F7 sello tardÃ­o implementado, sin desplegar

DecisiÃ³n del titular: ventana = alineaciones de los dos lados o T-45; corte = primer dÃ­a sin lote diario al desplegar. DecisiÃ³n tÃ©cnica clave: el lote de partido va en la MISMA cadena (orden por `seq`), asÃ­ que `verify` ya no puede ordenar por nombre de archivo y sigue `prev_sha256` desde el gÃ©nesis (con vuelta al orden por nombre si hay ruptura, para que los errores sigan siendo los de siempre). Los tres lectores que deciden quÃ© estÃ¡ sellado miran solo `batch_kind='diario'`: un lote de partido ni cuenta ni duplica. La predicciÃ³n final no cambia la calidad por sÃ­ sola (mismos lambdas mientras ningÃºn bloque de alineaciÃ³n pase la puerta); lo que cambia es el momento del sello y el precio de los picks de valor. No se fusiona hasta desplegar para no romper Â«producciÃ³n = mainÂ».

## 2026-10-19 Â· F7 desplegado apagado y reentrenamiento manual sin promociÃ³n

F7 (migraciÃ³n 084, worker, API, crontab) estÃ¡ en producciÃ³n con `LOTE_POR_PARTIDO_DESDE=None`: el job responde `apagado` y el sellado diario no cambia. Reentrenamiento manual pedido por el titular (13:18-17:59 UTC): candidato `2026.10.19-131830` guardado SIN activar. La puerta lo rechazÃ³ (no mejora a Elo sobre las mismas filas, el campeÃ³n no es comparable por la ventana distinta, CLV 0 de 300). RPS 0,2042 frente a 0,1945 del mercado (n=2.056), ECE 0,0104, peso modelo/mercado â‰ˆ 0,0001. Sigue activo `2026.09.27-010508`. DecisiÃ³n: no fijar el corte del sello por partido todavÃ­a; no aporta nada mientras ningÃºn bloque de alineaciÃ³n pase la puerta de mediciÃ³n.

## 2026-10-19 Â· Impacto por jugador: primer bloque con evidencia

Se midiÃ³ el apartamiento del once real respecto al habitual ponderado por rendimiento histÃ³rico (calificaciones de FotMob relativas al equipo, point-in-time). Pasa la puerta y resiste cuatro particiones y un placebo, pero el efecto (â‰ˆ âˆ’0,0005 de RPS) es ~5 % de la brecha con el mercado y solo es aplicable con el once confirmado (sello tardÃ­o, apagado). DecisiÃ³n tÃ©cnica: no recalibrar nada; pasarlo a producciÃ³n en modo sombra como la altitud, y no activarlo hasta medir hacia adelante. No se cambia el modelo activo.

## 2026-10-19 Â· Brecha con el mercado por momento y por liga; ajuste del once en sombra

Comparado el A con Pinnacle en T-72 h, T-24 h, T-6 h, T-1 h, once confirmado y cierre (docs/brecha_mercado_20261019.md): la brecha NO se cierra
en los momentos tempranos (+0,0140 en T-72 h, +0,0164 en el cierre sobre los mismos 181 partidos); la informaciÃ³n posterior a T-72 h explica ~15 %.
Descarta que el problema sea solo comparar contra el cierre. Por liga el A estÃ¡ mÃ¡s cerca en las europeas medianas y mÃ¡s lejos en MLS, MX y Brasil.
Activado el sello por partido desde el 20-oct (decisiÃ³n del titular) con el ajuste del once en MODO SOMBRA; gracia de 7 min porque la captura de
FotMob y el job de sello coinciden en el minuto. Walk-forward ampliado (2024-01 a 2025-10) corriendo en el worker: unirlo con el OOS actual
y reajustar `ajuste_xi` cuando termine.

## 2026-10-20 Â· Walk-forward ampliado: el bloque del once vale la mitad de lo medido

Con 11.920 partidos (2024-01 a 2026-10) el bloque de impacto por jugador baja de Î”RPS âˆ’0,0005 a â‰ˆ âˆ’0,0002: favorable en los 5 tramos secuenciales y
con placebo limpio, pero solo pasa la puerta estricta en 1 de 4 particiones. DecisiÃ³n: seguir en modo sombra, no activar; artefacto reajustado con la muestra
completa. La primera estimaciÃ³n sobre ~1.300 partidos sobreestimÃ³ el efecto: medir con la muestra grande antes de pasar nada a producciÃ³n.

## 2026-10-18 â€” Tenis: segundo bloque geogrÃ¡fico y comparaciÃ³n fija terminados
Chennai, Palermo, Riad, Hengqin y Shenzhen incorporados en data/tennis/historical_geography_batch2_20261018. Chennai: punto del estadio enlazado por TNTA, OSM tenis a 89 m; Riad: enlace de mapa observado en webook enlazado por WTA, geometrÃ­a arena cubierta a 208 m, no estadio de fÃºtbol. Shenzhen: gimnasio cubierto OSM 665408865 diferenciado de piscina y estadio. Hengqin: operador Huafa y OSM WGS84, timezone Asia/Shanghai. Palermo: inferencia de complejo por direcciÃ³n del operador y conjunto cartogrÃ¡fico de canchas, polÃ­gono sin nombre; tolerancia 750 m, no pista exacta afirmada. Elevaciones DEM 12/19/665/1/24 m, una consulta Open-Meteo no comercial; no mediciÃ³n de la cancha. Extractos del lector identificados como tales, no HTTP200 ficticio; desafÃ­os/TLS fallidos excluidos como evidencia.
309 fuentes SHA verificadas, 162 entradas georreferenciadas de 240. Destinos 10895/11240 (+121), variables completas ambos 6845, aptos 6414 (+170), sin referencias >1 km 6107. Desarrollo 3306, exploraciÃ³n 3108; cuarentena 201 sin cambios. Identidades, enlaces histÃ³ricos, particiones y variables de los 6244 aptos anteriores intactos. Restan 78 entradas/345 destinos; siguiente prioridad Taipei14/Bolonia14/Manchester12/Vilna10/Biel9.
Protocolo escrito antes del ajuste; 11240 probabilidades base cacheadas sin reentrenar, ridge1, RMS desarrollo, remuestreo1000 semilla20261018, sin bÃºsqueda en2025. Principal entrenamiento3306/evaluaciÃ³n3108: Log-Loss base0.635570632, espacial0.635580691; diferencia+0.000010060, IC95[-0.000124964,+0.000144395]. Sin >1km:3163/2944,0.631982160â†’0.631955198, IC incluye0. Mismos2833 IDs originales: base0.638733142, ajuste anterior0.638682279, ajuste ampliado0.638763510. No mejora clara ni selecciÃ³n/activaciÃ³n;2025exploratorio. CalibraciÃ³n, coeficientes y comparaciÃ³n comÃºn archivados.
AuditorÃ­a desde motor aislado aprobada: fuentes/canÃ³nico/CSV, datasets y experimentos anteriores, seis modelos base y12artefactos congelados verificados; no horas imputadas ni ROI.194 pruebas tenis; cÃ³digo y tests coinciden en50archivos; cuatro scripts entregados conSHA coincidente e informe docs/tenis_segundo_bloque_sedes_20261018.md. ArnÃ©s inicial1315/95/2 y final1315/95/2 en126.80s, Docker ausente. La sincronizaciÃ³n final fue rechazada temporalmente por lÃ­mite de uso del revisor automÃ¡tico, sin ejecutarse; tras continuaciÃ³n del usuario se reintentÃ³ por la misma vÃ­a y se completÃ³. Cero solicitudes Odds/API-Tennis y cero crÃ©ditos deportivos. Pendientes de clocks y futuro intacto preservados.

## 2026-10-18 â€” Tenis: tercer bloque geogrÃ¡fico terminado
Taipei/BolognaFiere/AO Manchester/SEB Vilna/Swiss Tennis Biel incorporados en data/tennis/historical_geography_batch3_20261018. Taipei OSM189781451 coincide con direcciÃ³n del operador208: estaciÃ³n YouBike rechazada; fuente del operador conservada como extracto de buscador, accesos TLS/conexiÃ³n fallidos no se aceptan. Bolonia pabellÃ³n37 OSM41260142/VirtusArena, contexto federativo y regional2025: no UnipolCasalecchio ni pabellÃ³n futuro2026. AOstadium354135390 coincide operadorweb/postcode. SEB punto municipal54.7069912,25.2347764 corroborado por OSM199382037 y operador. Biel referencia del complejo NLZ213588055 segÃºn operador y pÃ¡ginaarena,600m de tolerancia, huella precisa de arena no verificada; plano de acceso examinado no aÃ±ade esa precisiÃ³n. Se rechazan paradas y TissotArena. Tres IANA completados. DEM Ãºnico5puntos17/40/35/176/445m, terreno no altura medida cancha.
324 fuentes SHA,167 entradas georreferenciadas/240.10954destinos/11240 (+59),6874variablescompletas ambos,6442aptos(+28:16desarrollo/12exploraciÃ³n ATP),6135sinreferencias>1km;3322desarrollo/3120exploraciÃ³n/201cuarentena. Enlaces e IDs intactos,6442 no equivale a destinos,los6414aptos previos conservan variables. Cola73entradas/286destinos; prÃ³ximas EricBellKingston8/ElGeziraCairo7/GroenkloofPretoria7/DomainHobart6/Radom6 (34destinos potenciales).
Protocolo fijo guardado antes ajuste,11240probabilidadesbase reutilizadas,6modelos verificadasSHA,sinreentrenarbase, ridge1,RMS2024,bootstrap1000seed20261018,2025exploratorio. Principal3322/3120: LLbase0.635817235â†’espacial0.635834986, diferencia+0.000017751 IC95[-0.000132859,+0.000153060]. Sensibilidad3179/2956:0.632257012â†’0.632243081;ICincluye0. Muestra comÃºn3108delbloque2:base0.635570632,ajuste2 0.635580691,ajuste3 0.635585106; muestraoriginal2833actual0.638773950frentebase0.638733142. Sin mejora clara, no selecciÃ³n/activaciÃ³n. Horas e itinerarios no imputados; holdout congelado intacto.
194pruebastenis37.71s;50archivoscÃ³digo/testscoincidenentrepreparaciÃ³n yaislado;4scriptsnuevosentregadosSHAcoincidente,auditorÃ­adesdeaisladoaprobada,12artefactoscongeladosintactos,estudiospreviospreservados. ArnÃ©sinicial1315/95/2en137.18s;final1315/95/2en130.60s,Dockerausente. Sintaxis ydiffcheckcorrectos. Informe docs/tenis_tercer_bloque_sedes_20261018.md.0Odds/API-Tennis,0crÃ©ditosdeportivos;1consultaDEM. Ventanasdiarias/relojes siguenpendientes explÃ­citos.

## 2026-10-18 â€” Tenis: revisiÃ³n integral, evaluaciÃ³n y cierre consolidado
DecisiÃ³n: revisar la cola completa en una ejecuciÃ³n. Se examinaron las 73 entradas; 72 referencias acreditadas (59 puntos nuevos y 13 alias), 239/240 entradas georreferenciadas y 413 fuentes verificadas. Palm Hills de septiembre de 2025 conserva ambigÃ¼edad entre dos campus, uno inaugurado en mayo de ese aÃ±o: tres partidos excluidos. Todas las decisiones, los homÃ³nimos rechazados y los mÃ¡rgenes de complejo quedan documentados. Una consulta DEM agrupada de 59 puntos; cero consultas Odds/API-Tennis y cero crÃ©ditos.

La versiÃ³n historical_geography_complete_20261018 contiene 11.237/11.240 destinos, 7.002 casos con variables completas de ambos jugadores y 6.568 aptos (+126); 6.250 sin referencias de mÃ¡s de 1 km. Desarrollo 2024: 3.353; evaluaciÃ³n exploratoria 2025: 3.215; cuarentena de frontera: 201. Se recuperaron 283 destinos. Protocolo fijo y 11.240 predicciones base reutilizadas: Log-Loss 0,635501745495 frente a 0,635489645388; diferencia âˆ’0,000012100107, IC95 % [âˆ’0,000132496253; +0,000112690377]. Brier 0,223022884664 frente a 0,223021836192; ECE 0,0230183773 frente a 0,0230861881. Sensibilidad 3.207/3.043 e intersecciones anteriores de 3.120 y 2.833 IDs conservadas. Sin mejora acreditada ni activaciÃ³n.

AuditorÃ­a: 214 originales, 492.251 resultados canÃ³nicos y dos modelos actuales verificados sin fallos. Se conservan las advertencias histÃ³ricas: dos observaciones temporales posteriores a un registro antiguo y el linaje incompleto del canÃ³nico anterior. Coinciden los 35 mÃ³dulos y 15 archivos de pruebas con la entrega; seis scripts nuevos entregados. Pasaron 194 pruebas de tenis y una prueba de inferencia ATP/WTA con modelos reales, simetrÃ­a y masa conjunta. Seis modelos base, doce artefactos congelados y las variables de los 6.442 casos anteriormente aptos permanecen intactos. ArnÃ©s inicial: 1.315 aprobadas, 95 omitidas, dos avisos, 112,86 s; final: 1.315/95/2, 127,50 s. Docker ausente.

Informe Ãºnico: docs/tenis_cierre_integral_20261018.md. engine_readiness.json y completion_manifest.json separan implementaciÃ³n, cobertura, integridad y aprobaciÃ³n de producciÃ³n. Clima completo, carga diaria, itinerarios, reglas por casa, cuotas ejecutables y prueba futura siguen sujetos a evidencia. API-Tennis conserva prueba/cuota desconocida; The Odds API conserva plan de pago, 2.000 crÃ©ditos mensuales de tenis y reserva compartida de 6.000. No se activÃ³ un servicio ni se atribuyÃ³ rentabilidad.

## 2026-10-18 â€” Tenis: preparaciÃ³n operativa y evaluaciÃ³n financiera prospectiva

DecisiÃ³n: completar el archivo meteorolÃ³gico y el evaluador financiero sin convertir cobertura informÃ¡tica en una afirmaciÃ³n de rentabilidad. Entregados al motor aislado weather.py, paper_validation.py, sus dos archivos de pruebas, operational_validation.py, dependencia requests explÃ­cita, README e informe PREPARACION_APUESTAS_20261018.md. Los 50 archivos previos de cÃ³digo/pruebas y los 12 artefactos congelados siguen intactos; 37 mÃ³dulos coinciden con la polÃ­tica que se ejecuta.

Dos consultas API-Tennis: 66 eventos, 64 programados sin confirmaciÃ³n oficial y dos cancelados; cero instantes fÃ­sicos acreditados. Todas las sedes y coordenadas de esos 66 enlazan con el registro revisado. Una consulta pÃºblica Open-Meteo para cinco puntos, respuesta original y recibo con SHA; no se infiere hora de emisiÃ³n a partir de generationtime_ms. v3 tuvo 64 candidatos futuros; v4, reprocesado sin red a las 04:11:58 UTC del 19-oct, conserva 58 todavÃ­a futuros. Techo desconocido sigue desconocido; sensibilidad exterior separada y sin entrada al modelo. La carga inicial del registro por delta fallÃ³ antes de llamar a la API; se corrigiÃ³ cargando primero las revisiones originales, sin retrofechar vÃ­nculos. Se conservan los intentos y versiones.

El evaluador financiero vincula cuotas originales, predicciÃ³n anterior a la consulta, versiÃ³n activa del cÃ³digo, modelos, identidades y constancias oficiales. Conserva retiros y anulaciones conforme al contrato Pinnacle, compara probabilidades contra cuotas sin margen al mismo momento y calcula ROI/CLV con bloques de competiciÃ³n. La polÃ­tica v1 de preparaciÃ³n, sin selecciones ni resultados, estÃ¡ marcada como sustituida; v2 fija por adelantado 20-oct-2026 a 1-jul-2027, 500 selecciones y 30 competiciones por circuito, cierres completos y lÃ­mites inferiores positivos. No permite aprobar por mirar resultados antes de terminar el periodo. La ventana mÃ¡s amplia permite reunir torneos, sin prometer tamaÃ±o o ventaja. El protocolo futuro original sigue intacto.

Cero selecciones prospectivas y cero resultados financieros: ROI desconocido, nunca cero inventado. Costes cero son supuestos de simulaciÃ³n explÃ­citos; precios observados no son ejecuciÃ³n acreditada. Los adaptadores oficiales no cubren universalmente todos los torneos; eso permanece como puerta de evidencia, sin relajar comprobaciones. Palm Hills septiembre de 2025 conserva sus tres exclusiones; no bloquea eventos independientes del modelo base. No hay servicio nuevo activo ni apuestas colocadas. The Odds API: cero consultas/crÃ©ditos en esta ampliaciÃ³n, plan de pago y presupuesto de 2.000/mes conservados.

Pruebas: 225 especÃ­ficas en preparaciÃ³n (33,92 s) y desde el checkout entregado (30,04 s). ArnÃ©s general inicial 1.315/95/2 en 173,86 s; final 1.315/95/2 en 93,32 s; Docker ausente. El primer intento final no se ejecutÃ³ por el lÃ­mite temporal de la revisiÃ³n automÃ¡tica de permisos; despuÃ©s de su horario de restablecimiento, el mismo control se autorizÃ³ y completÃ³. Informe actual docs/tenis_preparacion_apuestas_20261018.md; evidencia data/tennis/operational_readiness_20261018, delivery_manifest.json y completion_manifest_v2.json. Sin modificaciÃ³n de producciÃ³n, modelos, probabilidades ni trabajos ajenos de fÃºtbol/NBA/web/mÃ³vil.

## 2026-10-19 UTC â€” Tenis: auditorÃ­a nueva y ocho probabilidades prospectivas contrastadas

DecisiÃ³n: producir un archivo real de probabilidades para los encuentros acreditables, conservando separados el contrato de investigaciÃ³n y la validaciÃ³n financiera. API-Tennis actualizado con dos consultas: 66 eventos, 58 programados sin confirmaciÃ³n oficial, tres completados, tres en juego y dos cancelados. Cero horas fÃ­sicas acreditadas. Cuatro programas actuales ATP/WTA descargados de fuentes oficiales, renderizados y revisados visualmente; recibos y bytes archivados. Se comprobÃ³ cada pareja en su celda de la cancha, fecha, superficie, circuito y torneo; nombres completos y abreviaturas exactas, sin aceptaciÃ³n por similitud. Horas previstas y lÃ­mites de turno se mantienen como tales.

20 parejas individuales revisadas: ocho ATP selladas entre 04:24:52 y 04:25:23 UTC del 19-oct antes del lÃ­mite horario oficial revisado. Ocho excluidas por lÃ­mite ya transcurrido, cuatro por ambigÃ¼edad de nombre canÃ³nico. Cobertura 8/20 revisadas y 8/66 del calendario, no universal. La herramienta exige recibos anteriores a la decisiÃ³n y de hasta 15 minutos; vuelve a comprobar despuÃ©s de calcular y no retrofecha los sellos. Probabilidades condicionales a partido completo, sin cuotas ejecutables ni apuestas. Artefactos data/tennis/forecast_audit_20261019/pronosticos.md y research_emission_v1/predictions.json.

Hallazgo nuevo: 50 nombres WTA y uno ATP asociados a mÃºltiples IDs en los modelos existentes. El listado completo queda en identity_ambiguities.json; no se elige ID por tamaÃ±o/mayorÃ­a ni se fusiona por nombre. Las cuatro WTA aÃºn horariamente candidatas quedan excluidas. Es necesario acreditar puentes y consolidar una versiÃ³n nueva de datos/modelos para ampliar cobertura. No se alteran los 37 mÃ³dulos congelados, 12 artefactos ni el protocolo financiero previo. Las ocho ATP emitidas tienen nombre canÃ³nico Ãºnico y parÃ¡metros completos; eso no equivale a ausencia de incertidumbre.

Palm Hills: nuevas bÃºsquedas por ficha Davis Cup, prensa contemporÃ¡nea y publicaciÃ³n de empleado no acreditan campus. Ficha histÃ³rica ITF devuelve HTTP502, archivado como fallo. Los tres IDs de partido conservan exclusiÃ³n espacial explÃ­cita en palm_hills_disposition.json; el modelo base no usa esa sede y no queda bloqueado globalmente. Horarios fÃ­sicos/techo solo se exigen a las variables y evaluaciones que los usan. No se inventan ni se declaran resueltos.

Integridad: 214 originales, 492.251 filas, cero fallos; persisten dos advertencias temporales de registros antiguos y linaje incompleto del canÃ³nico previo. Los siete registros antiguos no habilitan confirmaciÃ³n financiera: finales fuera de las ventanas predeclaradas. Nueva muestra financiera continÃºa en cero, ROI desconocido. Los ocho pronÃ³sticos nuevos son investigaciÃ³n independiente, no selecciones bajo la polÃ­tica que empieza el 20-oct. Cero crÃ©ditos Odds, cero apuestas, sin servicio automÃ¡tico ni adaptador universal; los scripts cubren las fuentes/ediciones efectivamente revisadas.

Entrega: capture_forecast_evidence.py, reviewed_forecasts.py, test_reviewed_forecasts.py e informe AUDITORIA_PRONOSTICOS_20261019.md en el motor aislado. Pruebas especÃ­ficas 246 en preparaciÃ³n (20,75s) y entrega (17,62s); general inicial 1315/95/2 en94,79s, final1315/95/2 en79,34s; Docker ausente. Informe actual docs/tenis_auditoria_pronosticos_20261019.md. No se atribuye rentabilidad ni perfecciÃ³n; no se tocaron producciÃ³n ni tareas ajenas.

## 2026-10-19 â€” Tenis: mercados v2, capturas ampliadas y conciliaciÃ³n de cuentas

DecisiÃ³n: integrar todas las familias acordadas sin alterar el candidato ni el estudio financiero congelados. Ocho mÃ³dulos en tennis_markets_v2: contratos y precios coherentes, periodos, adaptador de trece claves oficiales, comparaciÃ³n, liquidaciÃ³n, evaluaciÃ³n y controles de cuenta. Diez familias: ganador, ganador del set, totales/hÃ¡ndicaps de juegos y sets, tiebreak, marcador por sets y totales/hÃ¡ndicaps de juegos del set. BO3/BO5, lÃ­neas enteras/medias y pushes; cuartos rechazados. Cuotas de bolsa y props fuera del modelo permanecen visibles. Ganador hÃ­brido anterior separado: no se mezclan marginales incoherentes. Las marginales nuevas aÃºn no estÃ¡n completamente calibradas ni aprobadas financieramente.

624 contratos ilustrativos para ocho encuentros, derivados despuÃ©s del sello anterior y marcados como tales. ReproducciÃ³n offline de146 ofertas reales antiguas:144 calculables y dos lay sin soporte, sin atribuir vigencia. EvaluaciÃ³n exploratoria fija sobre2026 con modelos de origen1-ene-2026:2.207/2.451 ATP y1.291/2.146 WTA,56.804 probabilidades; exclusiones de identidad/parÃ¡metro explÃ­citas, ECE/Brier/Log-Loss por contrato y formato. No se utilizaron modelos de octubre para predecir retrospectivamente todo2026 ni se infiriÃ³ ROI sin precios. AÃ±o inspeccionado: no prueba confirmatoria.

La cuenta compartida tenÃ­a5.118 disponibles frente a reserva6.000; los primeros intentos de pago se detuvieron. El usuario autorizÃ³ una excepciÃ³n Ãºnica <=14 crÃ©ditos, mÃ­nimo5.104: consumiÃ³6 y saldo observado5.108. Se marcÃ³ consumida, sin modificar la reserva general. Luego autorizÃ³500 por cada una de dos claves: consumos confirmados500/500, cero cargos desconocidos. Primera clave distinta: saldo0. Segunda clave coincide con la principal: saldo observado4.606, no era otra demo independiente. Se detectÃ³ despuÃ©s de la prueba; debiÃ³ compararse antes. Se informÃ³ al usuario, se preservaron los informes originales y account_identity_correction.json corrigiÃ³ la etiqueta, enlazando500 cargos al registro central sin doble conteo. Nuevos scripts comprueban la coincidencia y requieren autorizaciÃ³n explÃ­cita para pruebas de la compartida. Ninguna llamada adicional despuÃ©s de consumir esos permisos.

Las pruebas ampliadas obtuvieron12.052 ofertas en snapshots repetidos de56 casas y9 IDs de evento;6.796 con precio de modelo, restantes sin parÃ¡metro/identidad acreditados o mercado fuera de soporte. Siete claves observadas de trece conectadas; seis no observadas, marcador/tiebreak sin clave de tenis inventada. ExpansiÃ³n priorizÃ³ casas no consultadas y conservÃ³ cambios;500 de cada clave realmente consumidos, sin sobrepasar500. DemoCapture libera Ãºnicamente exceso de reserva confirmado por cabeceras vÃ¡lidas, nunca fallos de cargo incierto. Snapshot repetido no es apuesta independiente. Sara Bejlek aparece frente a dos rivales el20-oct: ambos requieren revisiÃ³n oficial. No se borrÃ³ ni resolviÃ³ el conflicto por suposiciÃ³n.

Contabilidad central de tenis octubre:583 confirmados/595 reservados, dentro de2.000;incluye17 de recibos antiguos que SQL sum(actual_cost) omitÃ­a por NULL. Consumo de esta ejecuciÃ³n1.006:500 cuenta distinta,506 compartida (500+6 previos), no1.000 adicionales mÃ¡s500 duplicados. Los saldos son observaciones; hay otros consumidores. Credenciales en archivos locales ignorados, sin valores en informes ni comandos. No se publicaron ni ejecutaron apuestas.

Entrega:17 archivos al motor aislado, incluidos cinco scripts, dos nuevos archivos de pruebas, ocho mÃ³dulos y documentaciÃ³n/README.37 mÃ³dulos congelados y12 artefactos verificados intactos.294 pruebas en preparaciÃ³n31,18s y entrega22,01s; arnÃ©s general inicial1315/95/2 en139,34s y final1315/95/2 en112,12s, Docker ausente. Informe docs/tenis_mercados_integrados_20261019.md; datos data/tennis/markets_integration_20261019, markets_demo_20261019, markets_demo_2_20261019 y markets_backtest_v2_20261019. Modelos, estudio financiero, producciÃ³n y trabajos ajenos conservados. AprobaciÃ³n financiera y rentabilidad siguen sin acreditarse.

### 19-oct-2026: auditorÃ­a financiera y acreditaciÃ³n temporal externa

El usuario solicitÃ³ acreditar rentabilidad. No se confundieron las pruebas de API con selecciones financieras: revisiÃ³n offline de tres raÃ­ces,227 respuestas originales vÃ¡lidas/12.420 observaciones/11 eventos/56casas/cero cuotas vigentes;6registros antiguos sellados y1sin sello,8pronÃ³sticos de investigaciÃ³n y10archivos de integraciÃ³n conservados aparte. BÃºsqueda global no encontrÃ³ Ã³rdenes financieras. El estudio v2 permanece20-oct-2026 a1-jul-2027, ganadorPinnacle,500liquidadas/30bloques por circuito, coberturas completas y ROI/CLVcon intervalospositivos; ceroÃ³rdenes/ROI desconocido. NingÃºn beneficio ni evidencia futura inventados.

Nuevo paquete tennis_finance_v2 separado del candidato: evaluaciÃ³n reproducible, raÃ­ces deduplicadas, originales/cronologÃ­a, versiones, errores por directorios ausentes, creaciÃ³n exclusiva de informes y sellado de Ã³rdenes simuladas mediante las compuertas existentes. Sensibilidad a costes0/0,5/1/2%del importe original, pendientes y anulaciones visibles. IlustraciÃ³n de potencia bajo supuestos explÃ­citos, sin cambiar mÃ­nimos ni periodo. Registros vacÃ­os creados explÃ­citamente, sin convertir pronÃ³sticos viejos en Ã³rdenes. Otras familias de mercados no heredan aprobaciÃ³n. No se presupone que fuentes con hash acrediten automÃ¡ticamente los campos interpretados.

La revisiÃ³n automÃ¡tica rechazÃ³ inicialmente enviar una huella a DigiCert por falta de autorizaciÃ³n del destino. Se preguntÃ³ mediante herramienta y el usuario autorizÃ³ explÃ­citamente el sello. Una solicitud RFC3161, sin contenidos ni claves: DigiCert19-oct-2026 16:22:52UTC. Firma/cadena con CA independiente, nonce y digest verificados; todas las entradas intactas y sello anterior al estudio. Prueba negativa real: copia alterada y recibo local recalculado rechazados criptogrÃ¡ficamente; original conserva validez. El sello prueba existencia del protocolo y conjunto a esa hora, no retrodata registros ni prueba beneficio ni futuras selecciones.

Entrega:4mÃ³dulos nuevos,18pruebas y documentaciÃ³n. Suite preparada310antes de aÃ±adir2pruebas de sello,18especÃ­ficas alfinal y312enmotorentregado. ArnÃ©sgeneral inicial1.315/95omitidas/2advertencias114,99s;finaligual115,80s;Docker ausente.37mÃ³dulos congelados/12artefactos conservados. Cero consultas nuevas de cuotas/crÃ©ditos/apuestas/publicaciones/servicios automÃ¡ticos. La autorizaciÃ³n de500porclave ya estaba consumida y la reserva compartida no se tocÃ³. Informe docs/tenis_acreditacion_financiera_20261019.md; evidencias data/tennis/financial_accreditation_20261019. Rentabilidad sigue sin acreditarse por ausencia de muestra financiera y ejecuciÃ³n verificable, no por un defecto que se pueda eliminar rellenando datos.

### 19-oct-2026: calidad predictiva sin cuotas, comparaciÃ³n y protocolo futuro

El usuario pidiÃ³ resolver los requisitos de calidad. Se entregÃ³ tennis_quality_v3 en versiÃ³n separada: cuarentena normalizando acentos, comparaciÃ³n comÃºn de seis variantes, cobertura, Log-Loss/Brier/ECE/aciertos, bandas y umbrales fijos, Wilson explÃ­citamente iid y bootstrap por torneos/periodos. Cuatro contrastes principales hÃ­brido frente a WElo/Elo superficie calibrado, dos circuitos, Bonferroni98,75%. No se fusionaron IDs sin evidencia ni se promoviÃ³ retrospectivamente un ganador. Se verificaron fuentes y probabilidades archivadas frente a fÃ³rmulas y ratings; modelos de origenenero2026 para la evaluaciÃ³n2026, aÃ±o ya inspeccionado/exploratorio.

La revisiÃ³n encontrÃ³ dos grupos ATP(AndreIlagan yJulioCesarPorras) y50WTA ambiguos. Muestra comÃºnATP2.207/2.451,WTA581/2.146: ATP224sin efectos entrenados/20identidad desconocida; WTA1.156identidad ambigua/350efectos no entrenados/59desconocidos. Actualizar cuarentena protege la emisiÃ³n, no repara el entrenamiento previo ni acredita la disponibilidad histÃ³rica de esa metadata. HÃ­bridoLL0,62956ATP y0,60441WTA; referencias calibrada0,63217/0,60775,WElo0,63814/0,60365. Intervalos corregidos incluyen cero; superioridad no acreditada. ATP80â€“90%:145casos,84,5%pronÃ³stico medio/82,8%acierto,CIporbloquesaprox75,9â€“89,1%. WTA90%solo5casos: bootstrap degenerado se suprime, sin declarar certeza. Revisadas10familias/50grupos,45.444probabilidades con filtro comÃºn; no calibraciÃ³n nueva ni aprobaciÃ³n para todas las lÃ­neas.

Cuatro mÃ³dulos,script de auditorÃ­a y20pruebas nuevos. Registro probability-only sin resultados/cuotas, evidencia oficial reciente, reglas/identidades y segunda comprobaciÃ³n de vigencia al sellar. Versiones de modelo y del cÃ³digo activo verificadas, duplicados rechazados. Nuevo protocolo20-oct-2026 a1-jul-2027, seis variantes, umbrales de diseÃ±o500completados/30bloques por circuito, bandas>=70%con200casos y tolerancia5puntos, cobertura condicionalmÃ­nima20%; mÃ­nimos no garantizan potencia. Referencias actuales WElo/adaptativo nuevas con74.029ATP/20.614WTA, mismos datos/embargo que el candidato actual. Datos/modelos financieros congelados intactos. Cero resultados futuros: pendiente confirmaciÃ³n y revisiÃ³n independiente de fuentes; tiempos fÃ­sicos siguen requeridos por el contrato de resultados. No servicio automÃ¡tico ni nuevas consultas de cuotas, crÃ©ditos o apuestas.

Entrega vigente data/tennis/predictive_quality_v3_20261019_v3; dos preparaciones anteriores conservadas y sustituidas antes de cualquier pronÃ³stico confirmatorio. El intento de sello DigiCert para el NUEVO protocolo fue rechazado por revisiÃ³n automÃ¡tica: autorizaciÃ³n anterior era solo del financiero. Se pidiÃ³ autorizaciÃ³n especÃ­fica; no se enviÃ³ la nueva huella mientras no exista respuesta. No se usÃ³ ruta alternativa. DocumentaciÃ³n docs/tenis_calidad_predictiva_20261019.md.332pruebas del motor entregado26,71s,20nuevas; arnÃ©s inicial1315/95omitidas/2advertencias110,17s yfinaligual112,41s,Docker ausente. No se acredita hoy toda la calidad ni se inventan resultados futuros: se cierra infraestructura, diagnÃ³stico y protecciÃ³n; siguen abiertos recuperaciÃ³n de identidades, muestra futura y protocolos de los mercados restantes.

### 19-oct-2026: autorizaciÃ³n y sello del protocolo predictivo completados

El usuario autorizÃ³ explÃ­citamente el sello del nuevo protocolo predictivo. Una solicitud DigiCertRFC3161, enviando solo huella y nonce. Sello19-oct-2026 16:54:10UTC(10:54:10CiudaddeMÃ©xico), anterior a20-oct00UTC. Firma, cadena con CA independiente, nonce y digest del conjunto verificados. ProtocoloSHA25935f09a23ff91a95e71fbe3176ac18df332d198aa3e67eec25c5d5ac6a2b20; artefactos/cÃ³digo y todos los archivos del manifiesto anterior intactos. Prueba negativa real: copia alterada y recibo local recalculado rechazados criptogrÃ¡ficamente; original vÃ¡lido. Cero crÃ©ditos de cuotas, documentos o claves enviados, cero pronÃ³sticos/resultados confirmatorios. Nuevo completion_manifest_timestamp.json conserva el anterior y actualiza Ãºnicamente el estado de sellado. No cambios de cÃ³digo/modelos/criterios ni repeticiÃ³n innecesaria de la suite332ya aprobada. Informe adicional docs/tenis_sello_predictivo_20261019.md. Calidad y rentabilidad siguen sin acreditarse; el sello certifica existencia a esa hora, no aciertos.

### 19-oct-2026: continuidad autÃ³noma activada y primera emisiÃ³n prospectiva

El usuario autorizÃ³ continuidad sin intervenciÃ³n rutinaria. AutomatizaciÃ³nheartbeat creada y verificadaACTIVA: continuidad-de-validaci-n-predictiva-de-tenis, mismochat01a14720-ef8a-7c10-aa90-e4bc7df03407, cada2h. Capturador tennis_continuous_v1 nuevo, independiente de los protocolos sellados: ciclo compartido con reserva atÃ³mica4h, mÃ¡ximo12intentosAPI-Tennis/dÃ­aUTC, parada de segundo tour y espera24hpor401/403/429. Respeta autorizaciÃ³n de cuotas agotada/reserva compartida; ceroOddsAPI/apuestas. Clave dedicada solo en memoria, respuestas redactadas si la contienen, sin imprimirURLsconcredenciales. El servicio requiere equipo y aplicaciÃ³n disponibles; no se promete ejecuciÃ³n con el equipo apagado ni notificaciones rutinarias sin cambios. GuÃ­a docs/tenis_continuidad_autonoma_20261019.md.

Primera pasada real17:04UTC:2consultasAPI-Tennis,112eventos(50programados sin verificaciÃ³n fÃ­sica,49finalizados,5cancelados,5retiros,3jugando), cuatro PDFs oficiales20-oct descargados/renderizados/revisados visualmente.29parejas individuales;18pronÃ³sticos del protocolo congelado,11ATP/7WTA, sellados antes de los encuentros, sin cuotas. Ciclo9f9f8c1bea124f0696b12fa5e1e06be9. Once exclusiones finales; dos rectÃ¡ngulos deNingbo y una abreviaturaJ-L se corrigieron con adendas nuevas, no se alteraron revisiones vinculadas a registros previos. Se rechazÃ³Boulterâ€“Sakatsume porTBF/marcador parcial: reanudaciÃ³n, no pre-match. ProgramaactualBejlekâ€“Parks ycalendario coinciden; la ofertaantiguaBejlekâ€“Wang queda incompatible paraesa jornada y se conserva. Ninguna fusiÃ³n de IDs o relax de cuarentenas. Segunda invocaciÃ³n comprobÃ³capture_not_due/0consultas.

Se entregaron cuatro mÃ³dulos nuevos,10pruebas y guÃ­a.342pruebas del motor entregado26,49s; arnÃ©s inicial1315/95omitidas/2advertencias112,33s;finaligual104,50s,Docker ausente.37mÃ³dulos originales,12artefactos y4mÃ³dulosdecalidadsellados conservados. Protocolo de calidad verificado desde el motor entregado:18pendientes/cero resultados/cero calidad acreditada. El programador buscarÃ¡ y archivarÃ¡ resultados; tiempos fÃ­sicos insuficientes se conservarÃ¡n como candidatos pendientes, sin imputar ni reescribir los criterios. Resultados nuevos en versiones de listas, sin sobrescribirfuture_results.jsoninicialniinformes anteriores. No se afirma rentabilidad ni certeza. Datosdata/tennis/continuous_quality_20261019 ylistaPRIMEROS_PRONOSTICOS.md conhorariosCiudaddeMÃ©xico.

### 19-oct-2026: diez mercados en seguimiento prospectivo

El usuario pidiÃ³ validar tambiÃ©n los otros mercados y continuar sin confirmaciones rutinarias. Se aÃ±adiÃ³ tennis_allmarkets_v1 separado de calidad_v3/financiero: cuatro mÃ³dulos congelados, tablas fijas de55tareasBO3/77BO5, diez familias, todos los sets previstos, vectores conjuntos coherentes sin recalibraciÃ³n posterior. Marcador por sets es una sola tarea multiclase; complementos/otras lÃ­neas no son muestras independientes. Registro nuevo con hora real propia, sin atribuir el sello DigiCert anterior. Conservados37mÃ³dulos originales/12artefactos/4mÃ³duloscalidad sellados. Protocolo nuevo20-oct2026 a1-jul2027, sin sello externo; huellas locales no prueban existencia frente a terceros.

Primera emisiÃ³n real18partidos(11ATP/7WTA),990tareasrelacionadas,110gruposobservados,ceroresultados,cero registros/resultados rechazados. Fuentes anteriores verificadas al emitir padre y ahora dentro de polÃ­tica nueva4h estrictamente antes de cota oficial; se revalidaron horas despuÃ©s del cÃ¡lculo. No se retrodatÃ³ ni se cambiÃ³ el contrato anterior de15min. RepeticiÃ³n:18already_sealed/cero duplicados. Preserva cuarentenas, programa/calendario/revisiÃ³n exacta y reconstruye probabilidades desde parÃ¡metros congelados. API-Tennis0consultas nuevas,Odds0crÃ©ditos,apuestas0.

EvaluaciÃ³n por circuito/formato/tiebreak/contrato/lÃ­nea/set con Log-Loss/Brier de vector completo, ECE binario condicional y bandas. Pushes/set no disputado no se convierten en derrota; retiro/descalificaciÃ³n/walkover fuera de partido completado siguen en cobertura. Resultado invÃ¡lido permanece pendiente en denominador y se reporta separado. Criterios predeclarados500partidos/30bloques por grupo,cobertura80%,bandasaltas200casos/calibraciÃ³nÂ±5pp,correcciÃ³n por528grupos/cincobandas/dos agrupaciones y fin de periodo. Son criterios de diseÃ±o, no garantÃ­a de potencia ni certeza; solo habilitan revisiÃ³n independiente. HistÃ³rico45.444probabilidades/50grupos inspeccionados conservado aparte, sin heredar validaciÃ³n para las lÃ­neas nuevas. Financiero permanece limitado a ganador sin nuevas autorizaciones.

AutomatizaciÃ³n existente continuidad-de-validaci-n-predictiva-de-tenis actualizada mediante herramienta y verificadaACTIVA,mismochat,cada2h,captura4h,mÃ¡ximo12API-Tennis/dÃ­aUTC,silencio si sin cambio. Incluye emisiÃ³n/evaluaciÃ³n de todos los mercados y archivos nuevos, sin duplicar trabajos ni modificar candidatos. Reportes data/tennis/all_markets_prospective_20261019,guÃ­a docs/tenis_validacion_todos_mercados_20261019.md. Vistas RESUMEN.md y PRONOSTICOS_POR_MERCADO.md entregadas; documentos/script de vistas copiados al motor aislado.

367pruebas del motor entregado aprobadas28,64s,incluidas25nuevas. ArnÃ©s inicial1315/95omitidas/2advertencias104,20s. Primerfinal tuvo1fallo en test_ratelimit del panel: dependÃ­a del reloj real y podÃ­a cruzar minuto; repeticiÃ³n aislada aprobÃ³. Se aislÃ³ Ãºnicamente el reloj del mÃ³dulo en el helper de prueba, sin modificar producciÃ³n,con7pruebas de lÃ­mites aprobadas3,12s. ArnÃ©sfinal repetido1315/95/2aprobado;Dockerausente. Se conservaron fallo y reintento en logs/manifiesto. No se relajaron aserciones. Calidad deportiva futura y rentabilidad continÃºan sin acreditar; no se cerraron por pruebas de software.

### 19-oct-2026: causa del cero futuro e incorporaciÃ³n automÃ¡tica de resultados

El usuario pidiÃ³ solucionar el registro futuro vacÃ­o y la falta de acreditaciÃ³n. Se comprobÃ³ reloj real:19-oct18:27UTC; primera reconciliaciÃ³n18:35UTC. Los18eventos siguen futuros, primerinicioestimado20-oct04:15UTC/19-oct22:15MÃ©xico,unas9,7hdespuÃ©s. Cero terminales de esos18;59eventos terminales del proveedor ajenos no se convirtieron en aciertos. Capturador devolviÃ³capture_not_due;0API-Tennis nuevas/0OddscrÃ©ditos/0apuestas. No se esperÃ³ artificialmente ni se retrodatÃ³ evidencia.

Se entregÃ³ tennis_evidence_v1,cuatromÃ³dulosindependientes: cruce por ID de evento/jugadores, orientaciÃ³n, circuito/ediciÃ³n contra fuente de calendario original, SHA/fechas, marcadores por set y terminales. DecimalesAPI6.4/7.7 son juegos6â€“7 y puntosTB4â€“7; se validan sin usar floats/truncar silenciosamente. Conflictos requieren revisiÃ³n; IDsduplicados invalidan lote completo. Horas fÃ­sicas solo con fuente primaria JSONarchivada, pareja vinculada a campos nativos, caminos de valores, zonas explÃ­citas/cronologÃ­a/revisiÃ³n semÃ¡ntica. No se convierten tiempos programados/recepciÃ³n/transiciones en tiempos fÃ­sicos. DocsAPI-Tennis consultadas:los ejemplos no acreditanambasmarcasfÃ­sicas. Los candidatos sin ellas quedan separados.

Comando reconcile produce nueva accepted_results.json/terminal_candidates.json y ejecuta ambos evaluadores congelados. Primera pasada18pendientes scheduled_in_future,0aceptados/errores; fuentes/candidatos y cobertura conservados. Se corrigiÃ³ contador de defaultdict durante pruebas para que leer una lista vacÃ­a no contase un evento terminal. Los resultados sintÃ©ticos solo viven en tests, nunca en time_reviews real, actualmentevacÃ­o.

RevisiÃ³n histÃ³rica reproducible sin reentrenar:2788partidosterminados(2207ATP/581WTA),45444probabilidades marginales archivadas,39grupos al combinar50grupos anteriores de score en tareas multiclase; diezfamilias. Modelospre2026 y2026ya inspeccionado,etiquetaexploratoria. Se publican todos los contratos, LL/Brierbinario yvectorial separados, ECE/curvas de10intervalos incluso confianza<0,5para multiclase e incertidumbre por competiciÃ³n. DiagnÃ³stico de clases explÃ­citamenteexpost,no benchmark entrenado:98,8%en>22,5juegosBO5coincidecon98,8%clasemayoritaria. GanadorMarkovATPBO3n1789acierto62,3%LL0,6610;WTAn581acierto69,5%LL0,6043;scoreexacto41,3%/46,8%. No se confundiÃ³ con el hÃ­brido actual ni con validaciÃ³n global de lÃ­neas nuevas. Primera revisiÃ³n conservada;historical_v2aÃ±adebalance de clases sin reescribir.

AuditorÃ­a financiera nueva:0Ã³rdenesvÃ¡lidas,periodo aÃºn no iniciado/terminado,muestra/cierres/ROI/CLVinsuficientes,ejecuciones/costes no acreditados. Se explica que la continuidad predictiva no genera por sÃ­ sola una muestra de ROI; no afirmarfinancieroactivo. Las excepcionesOddsAPIseconsumieron yreserva6000permanece frenteÃºltimosaldoobservado4606,no saldo consultadohoy. No se inventaron cuotas/precios/Ã³rdenes o autorizaciones nuevas. El primer acierto no basta: se preservan finperiodo/mÃ­nimos/revisiÃ³n independiente.

AutomatizaciÃ³n existente actualizada mediante herramienta y verificadaACTIVA mismochat/con lÃ­mites/notificaciones originales; ahoraejecutareconcile offline ydocumenta esquema de revisiÃ³n real,investigaciÃ³n yconflictos. GuÃ­a docs/tenis_resultados_y_evidencia_20261019.md;raÃ­z data/tennis/evidence_resolution_20261019 con ESTADO.md,HISTORICO.md,estado/manifiesto. No se modificaron37core/12artefactos/4calidad ni4allmarkets/8marketscongelados.29pruebas especÃ­ficas aprobadas2,01s;motorentregado396aprobadas28,21s. ArnÃ©s inicial1315/95omitidas/2advertencias103,13s,finaligual106,83s,Dockerausente. Manifiesto22archivos entrega verificable. Infraestructura completada, resultados futuros y rentabilidad siguen sin acreditarse por condiciones reales de tiempo/datos/precios, no se declaran resueltos por software.

## 2026-10-19 â€” Tenis: puente de alias WTA y reevaluaciÃ³n (auditorÃ­a)

- Hallazgo: `2026_wta.csv` trae Queen's Club y 's-Hertogenbosch (45 filas, semana 2026-06-08) con IDs WTA alternos (3xxxxx). La cuarentena por nombre excluÃ­a TODOS los partidos de esas jugadoras: 1.161 de 2.146 WTA 2026 (54,1 %), sesgando la muestra WTA hacia jugadoras menores.
- DecisiÃ³n: mÃ³dulo nuevo `tennis_identity_v2` (en `apps/tennis`, 3 pruebas; suite 399 verde) fusiona un alias solo si mismo nombre normalizado, base >=30 filas, alias <=10 filas y 5x menor, dentro de la vida activa de la base (+120 dÃ­as), sin compartir torneo-semana y sin atributos ioc/hand disjuntos. Sin coincidencia difusa. 47 alias fusionados (46 WTA, 1 ATP), 403 filas reescritas, 62 ambiguos siguen en cuarentena con motivo. Datos nuevos en `data/tennis/identity_bridge_20261019/` (IDs originales conservados en `*_id_original`); `canonical_v2` y todo lo congelado intactos (hash verificado).
- Efecto: exclusiÃ³n por nombre WTA 2026 baja a 1,9 % (ATP 1,6 % -> 1,1 %). Es conocimiento actual, no prueba de que el alias fuera resoluble antes de cada partido.
- ReevaluaciÃ³n 2026 (origen 1-ene, modelos reentrenados en carpetas nuevas, muestra completa 2.451 ATP / 2.146 WTA), log-loss: ATP Markov 0,6447, Elo de superficie 0,6285, Weighted Elo 0,6294; WTA Markov 0,6546, Elo de superficie 0,6221, Weighted Elo 0,6309. Markov puro sigue peor que Elo (IC de diferencia por periodo excluye 0: ATP +0,016, WTA +0,033). Los alias casi no mueven el modelo; el beneficio real es cobertura y ausencia de sesgo de selecciÃ³n.
- ConclusiÃ³n: el nÃºcleo punto-a-juego solo aporta como componente de un hÃ­brido y para mercados derivados; para ganador manda Elo de superficie. Antes de ampliar mercados o protocolos, rediseÃ±ar el nÃºcleo (estado dinÃ¡mico + variables + calibraciÃ³n) y compararlo solo contra Elo y mercado sin margen. Pendiente: reentrenar modelo futuro y re-sellar protocolo con datos v3 (no se hizo; los sellos previos no se tocan).

## 2026-10-19 â€” Tenis: sobredispersiÃ³n por partido corrige todos los mercados (exploratorio)

- Hallazgo de la re-auditorÃ­a: el Markov saque/resto ordena mejor que Elo (acierto ganador 2026 ATP 64,6 % vs 64,2 %; WTA 66,7 % vs 64,8 %), pero es sobreconfiado (pendiente de calibraciÃ³n logit 0,55-0,59 ATP, 0,44-0,55 WTA). Por eso perdÃ­a en log-loss. A la vez subestima sets corridos (ATP 52,5 % previsto / 59,9 % real), sobreestima tie-breaks y da +1,1 a +1,2 juegos de mÃ¡s por partido. Una sola causa: suponer p y q fijos en todo el partido.
- Prueba: mezcla gaussiana sobre la diferencia de saque por partido (contracciÃ³n k de la diferencia estimada + ruido sigma del dÃ­a), 2 parÃ¡metros ajustados en 2025 y aplicados a 2026 (ATP k=0,9, sigma=0,2; WTA k=0,8, sigma=0,2). Mejora ganador, sets corridos, tie-break, primer set, mÃ¡s de 22,5 y hÃ¡ndicap -3,5 a la vez. Corrige el sesgo de juegos totales (ATP 27,43 -> 25,87, real 26,29; WTA 23,13 -> 21,86, real 22,09). Iguala a un Platt por mercado, pero sigue siendo una sola distribuciÃ³n coherente.
- Mezcla + Elo en logit (pesos ajustados en 2025) frente a Elo de superficie, 2026: ATP -0,0057 log-loss, IC95 por periodo [-0,0087; -0,0026]; WTA -0,0038 [-0,0071; -0,0006]. Exploratorio: 2026 ya estaba inspeccionado y el bootstrap por periodo no capta toda la dependencia.
- Consecuencia: el estudio prospectivo de diez mercados (990 tareas) se sellÃ³ con el Markov sin sobredispersiÃ³n, una variante con sesgo conocido. No se toca; se recomienda un protocolo nuevo con la mezcla. Resultados en `data/tennis/identity_bridge_20261019/overdispersion_test.json`; la implementaciÃ³n sigue pendiente como mÃ³dulo con pruebas.

## 2026-10-19 â€” Tenis: nÃºcleo v4/v5, retiro de los 990 pronÃ³sticos y ranking

- Por decisiÃ³n del titular se retiraron los 18 registros (990 filas) del estudio de diez mercados con Markov plano: movidos, sin borrar, a `data/tennis/retired_20261019/all_markets_v1_predictions/` con manifiesto SHA-256; aviso en `all_markets_prospective_20261019/RETIRED.md`. Los 18 padres de ganador (v3) y todo lo congelado siguen intactos.
- `tennis_core_v4` (mÃ³dulo nuevo, 4 pruebas): sobredispersiÃ³n por partido (mezcla gaussiana sobre la diferencia de saque, k/sigma de 2025) + mezcla logit con Elo, centro re-resuelto para que el ganador de la mezcla iguale el objetivo; todos los mercados salen de una sola distribuciÃ³n conjunta. Protocolo y 18 pronÃ³sticos en `data/tennis/core_v4_prospective_20261019/` (superado por v5, se conserva). Puerta del padre: sellado original + decisiÃ³n estrictamente antes de la cota oficial; NO exige recibo de calendario de menos de 4 h (el de las 17:04 UTC habÃ­a caducado y el cupo API-Tennis no se tocÃ³).
- Hallazgo con efecto grande: aÃ±adir ranking, puntos de ranking y edad al objetivo de ganador. 2026 (muestra completa): ATP log-loss 0,6229 -> 0,6032, acierto 64,9 % -> 66,9 %; WTA 0,6183 -> 0,6018, acierto 65,9 % -> 66,4 % (solo rank: 67,7 %). Variables elegidas por CV 2025 por periodos; altura y mano no aportan; 2026 ya estaba inspeccionado, solo lo prospectivo confirma.
- Otro error de datos: `2026_wta.csv` (17 filas) y 659 ATP tienen columnas biogrÃ¡ficas corruptas (edad hasta 3387, altura hasta 20.011.008). No afecta al motor actual (no usa esas columnas) pero rompÃ­a cualquier variable de edad/altura; se sanea (edad 14-50, altura 140-215) antes de usar.
- `tennis_core_v5` (+features, 2 pruebas; suite 405 verde): rank/puntos/edad de la Ãºltima fila previa del jugador (mÃ¡x. 60 dÃ­as de antigÃ¼edad; mÃ¡s antiguo = excluido). Protocolo y pronÃ³sticos en `data/tennis/core_v5_prospective_20261019/`: 17 sellados, 1 excluido (Uchijima/Shibahara, ranking caducado). ParÃ¡metros refit con 2025+2026.
- Pendiente: cuotas como dato de entrada (requiere crÃ©ditos/dataset histÃ³rico; no se gastÃ³ nada), nÃºcleo dinÃ¡mico por ronda, 62 alias dudosos, consolidar mÃ³dulos. La automatizaciÃ³n de Codex sigue sellando con el protocolo antiguo si estÃ¡ activa.

## 2026-10-19 â€” Tenis: motor v7 (Elo dinÃ¡mico por ronda) y cierre de recomendaciones

- Identidades v3: la edad al dÃ­a de la fuente da fecha de nacimiento. 5 fusiones con fecha igual (+-3 dÃ­as), 14 parejas homÃ³nimas confirmadas como personas distintas, 27 sin evidencia (casi todas ATP de los 70-90, mÃ¡s Ruse y Vandewinkel). Ya no hace falta excluir por nombre lo que se resuelve por ID.
- Elo dinÃ¡mico (`tennis_dynamic_v2`): Weighted Elo general + superficie (K=250/(n+5)^0.4), actualizado partido a partido con dÃ­a estimado por ronda y margen de 2 dÃ­as; los retiros cuentan como carga, no como resultado. Algunos archivos (85 torneos ATP 2026, quali) traen fecha por partido: v1 la desplazaba (posible fuga); v2 la usa tal cual. Resultado sin cambio material, pero v6 queda superado por v7.
- Apilador v7 (elegido por CV 2025, refit 2025+2026): Markov con sobredispersiÃ³n, Elo dinÃ¡mico, ranking, puntos, edad, inactividad, carga 14 dÃ­as, experiencia. El Elo congelado deja de aportar. 2026: ATP log-loss 0,5956 / acierto 67,6 %; WTA 0,5946 / 67,9 % (Elo de superficie 0,6285 / 64,2 % y 0,6221 / 64,8 %). En WTA el Markov casi no pesa para el ganador; sigue dando la forma de sets/juegos.
- DecisiÃ³n: v7 es el motor vigente (`tennis_motor`); v4-v6 se conservan como superados. 17 pronÃ³sticos sellados para 19-20 oct; Uchijima/Shibahara excluido por ranking de mÃ¡s de 60 dÃ­as.
- Pendiente con decisiÃ³n del titular: cuotas histÃ³ricas de cierre como entrada (descarga o crÃ©ditos) y la automatizaciÃ³n de Codex con el protocolo retirado.

## 2026-10-19 â€” Tenis: cuotas de Tennis-Data (descarga manual del titular)

- El titular descargÃ³ a mano 47 archivos (ATP 2000-2026, WTA 2007-2026) para un estudio privado sin lucro; quedan fuera de git (`.gitignore`) con manifiesto SHA-256 en `data/tennis/tennis_data_manual_processed/`. AtribuciÃ³n: tennis-data.co.uk. No se redistribuyen.
- Cruce con la base canÃ³nica (apellido + inicial, ventana de fechas, pareja exacta): 53.853 partidos 2015-2026, cobertura 93-95 % ATP y 90-95 % WTA reciente. Pinnacle casi desaparece en 2026 (3-4 %): se usa el promedio de casas sin margen.
- Resultado 2026 (CV 2025): el mercado solo gana a v7 con claridad. ATP log-loss 0,5935 vs 0,6031, acierto 68,5 % vs 67,1 %; WTA 0,5661 vs 0,5956, acierto 69,5 % vs 68,0 %. AÃ±adir v7 al mercado no aporta nada medible. Recentrar la mezcla al ganador de mercado mejora primer set y hÃ¡ndicap, y no empeora sets corridos, tie-break ni totales.
- DecisiÃ³n: si hay cuota previa disponible, el objetivo de ganador es la cuota sin margen y los demÃ¡s mercados salen coherentes del Markov recentrado; sin cuota, v7. `tennis_motor forecast --odds-a --odds-b` acepta cuotas tecleadas a mano (415 pruebas). Las cuotas de Tennis-Data son casi de cierre y se publican despuÃ©s: sirven para validar, no para pronosticar en vivo; para uso automÃ¡tico en vivo harÃ­a falta una fuente previa (p. ej. The Odds API, 1 crÃ©dito por torneo y foto), decisiÃ³n del titular.

## 2026-10-20 â€” Tenis: cuotas previas en vivo (The Odds API) y motor v8

- AutorizaciÃ³n del titular (19-oct): solo ganador (h2h), una regiÃ³n (`eu`), dos fotos al dÃ­a por torneo activo, tope 400 crÃ©ditos/mes. `tennis_odds_live_v1` reutiliza el registro de crÃ©ditos existente; ademÃ¡s, como la cuenta es compartida con el fÃºtbol, niega cualquier llamada que deje menos de 350 crÃ©ditos x dÃ­as hasta el reinicio del dÃ­a 1 (estimaciÃ³n de consumo del fÃºtbol). El 20-oct 00:39 UTC quedaban 4.389 crÃ©ditos frente a una reserva de 4.200: hay unos 189 crÃ©ditos de holgura este mes; el 1-nov se libera.
- Primera foto: un solo torneo de tenis activo en la API (WTA Ningbo, 9 partidos, 1 crÃ©dito). Los torneos ATP de esta semana no aparecen en The Odds API: para ellos el motor sigue con v7.
- v8 (`core_v8_prospective_20261019`, inicio 20-oct 01:00 UTC): mismo motor que v7; el objetivo de ganador es la cuota sin margen de la Ãºltima foto previa a la decisiÃ³n (mÃ¡x. 36 h), si existe. 17 sellados; 4 con cuota (Paolini 65,5 % por mercado frente a 75,8 % de v7; Bejlek 79,5 %; Putintseva 27,4 %; Ostapenko 43,6 %). v7 queda superado.
- ProgramaciÃ³n: tarea de Windows Â«QuantFut tenis cuotas h2hÂ» a las 05:00 y 17:00 (hora de MÃ©xico) = franjas AM/PM UTC; log en `data/tennis/live_odds_v1/scheduler.log`. Requiere el equipo encendido. `tennis_motor forecast` toma la Ãºltima foto automÃ¡ticamente (418 pruebas).

## 2026-10-20 â€” Tenis: motor en git (PR #46) y entrada automÃ¡tica

- El motor vivÃ­a sin seguimiento en el worktree de Codex: ahora estÃ¡ en la rama `tennis/motor-v8` (PR cerorar23/quantfut#46). `apps/tennis/.gitattributes` desactiva la normalizaciÃ³n de finales de lÃ­nea porque los protocolos sellados fijan el SHA-256 de esos bytes. Las notas de harness que dejÃ³ Codex en ese worktree quedan en un `git stash` de ese worktree; su contenido ya estÃ¡ resumido aquÃ­.
- La automatizaciÃ³n de Codex solo llegÃ³ a hacer una captura (19-oct 17:04 UTC). Se sustituye por `tennis_intake_v1`: calendario de API-Tennis (2 consultas por ejecuciÃ³n, mÃ¡ximo 4 al dÃ­a), identidad estricta, torneo por nombre exacto, sello Ãºnico 10 minutos antes de la hora del proveedor, resultados de capturas posteriores. Primera ejecuciÃ³n: 29 partidos sellados automÃ¡ticamente (frente a 17 con la revisiÃ³n manual de PDF); exclusiones con motivo (efectos sin entrenar, ranking caducado, Nakashima ambiguo).
- DecisiÃ³n: se acepta la hora del proveedor como lÃ­mite del sello (sin PDF oficial). Es menos estricto que el protocolo anterior, pero da cobertura real; queda declarado en cada registro.

## 2026-10-19 â€” Tenis: actualizaciÃ³n semanal de datos

- AutorizaciÃ³n del titular: descargar ahora los 9 archivos de TennisMyLife que cambiaron (4,1 MB, MIT) y cada lunes solo los que cambien. `tennis_refresh_v1` reutiliza el resto enlazÃ¡ndolo desde la instantÃ¡nea anterior tras verificar su SHA-256; la prueba en seco con la instantÃ¡nea del 16-oct reproduce la base idÃ©ntica (492.251 partidos, mismos IDs).
- Primera ejecuciÃ³n: 492.350 partidos hasta el 19-oct; 47 alias y 6 fusiones por nacimiento; promovida en `config/motor.json` (la anterior queda en `canonical_history`). La entrada automÃ¡tica y `tennis_motor` ya usan la base nueva; los protocolos sellados mantienen la suya.
- Tarea de Windows Â«QuantFut tenis datos semanalesÂ», lunes 04:00 (antes de la foto de cuotas de las 05:00). PR cerorar23/quantfut#49.

## 2026-10-20 â€” Tenis: Codex pausado, reentrenamiento semanal y validaciÃ³n punto a punto

- AutomatizaciÃ³n de Codex Â«continuidad-de-validaci-n-predictiva-de-tenisÂ» pausada editando su `automation.toml` (`status = "PAUSED"`; copia en `automation.toml.bak-20261020`). Si Codex estÃ¡ abierto puede necesitar reiniciarse para leerlo.
- Modelo de saque/resto reentrenado con la base al 19-oct (ATP 74.037 partidos, WTA 20.640; ambos convergen). Con la base corregida el modelo reconoce a Rybakina o Eala, que antes quedaban fuera por alias. La actualizaciÃ³n semanal ya reentrena y promueve `models_root` si converge.
- `tennis_motor` deja de rechazar partidos con alguna celda de saque sin entrenar: usa el valor de poblaciÃ³n, igual que en las filas con que se ajustÃ³ el apilador. La entrada pasÃ³ de 29 a 33 partidos sellados.
- Match Charting Project (9.400 partidos, 1,4 M de puntos): sd entre partidos â‰ˆ 0,23 logit por servidor (â‰ˆ 0,16 en la semidiferencia, coherente con el sigma 0,2); sin variaciÃ³n extra entre sets ni racha punto a punto. Break point +1,3 pp y tie-break âˆ’2 pp para el que saca, con efecto despreciable (hold â‰ˆ 0,4 pp, tie-break â‰ˆ 0,1 pp): no se modifica el Markov. Resultado en `data/tennis/weekly/20261019/mcp_point_analysis.json`.
- AÃºn no hay resultados: los primeros partidos sellados empiezan el 20-oct 04:15 UTC. PR cerorar23/quantfut#50.

## 2026-10-20 â€” Tenis: mezcla 2D (diferencia + nivel de saque) probada y descartada

- HipÃ³tesis sacada del Match Charting Project: ademÃ¡s de la diferencia, el nivel conjunto de saque de los dos jugadores varÃ­a de un partido a otro, lo que afectarÃ­a a totales y tie-breaks. Se calculÃ³ una rejilla 17x7 (diferencia x nivel) para 2025-2026, se ajustaron k, sigma de la diferencia, sigma del nivel y desplazamiento en 2025 y se probÃ³ en 2026.
- Resultado: en WTA no aporta nada (sigma del nivel 0,1, log-loss idÃ©ntico). En ATP corrige exactamente la media de juegos (26,29 previsto frente a 26,29 real, frente a 26,70 de la 1D), pero empeora tie-break (0,6604 frente a 0,6573) y mÃ¡s de 24,5 juegos (0,5607 frente a 0,5591); el resto se mueve menos de 0,0005.
- DecisiÃ³n: se mantiene la mezcla 1D. Acertar la media no compensa empeorar la probabilidad de los contratos. Detalle en `data/tennis/identity_bridge_20261019/mixture2d_test.json`.

## 2026-10-20 â€” Tenis: operaciÃ³n estable, sin ranking caducado y pruebas en CI

- Las tareas ya no dependen del worktree de Codex (que Codex puede limpiar): corren desde `C:\Users\huye\Documents\quantfut-tenis`, worktree propio del repo. La configuraciÃ³n que la actualizaciÃ³n semanal reescribe vive fuera de git en `data/tennis/motor_config.json` (variable `TENNIS_MOTOR_CONFIG`); `apps/tennis/config/motor.json` queda como plantilla. Los estudios congelados v4-v8 fijaron rutas del worktree de Codex en sus hashes de cÃ³digo: se conservan como evidencia, pero solo se pueden reverificar desde esa carpeta.
- Jugadores con ranking de mÃ¡s de 60 dÃ­as ya no se excluyen: el motor usa un apilador sin ranking/puntos/edad (Markov + Elo dinÃ¡mico + inactividad/carga/experiencia), ajustado igual. En 2026 (fuera de muestra respecto a 2025): ATP log-loss 0,6052 / acierto 67,1 %, WTA 0,6026 / 66,6 %, frente a 0,5956 / 67,6 % y 0,5946 / 67,9 % con ranking. Primer caso: Uchijima-Shibahara.
- CI: job `tenis` en `pruebas.yml` (425 pruebas de `apps/tennis`, sin base de datos).
- Las notas de tenis de `progreso.md`, `tareas.md`, `PENDIENTES.md` y los 32 `docs/tenis_*.md` entran por fin al repo. El stash de notas de Codex se exportÃ³ a `data/tennis/codex_harness_notes_stash_20261019.patch`.

## 2026-10-20 â€” Tenis: el motor pasa al VPS

- Para no depender del PC, el tenis corre en el VPS en una imagen propia (`quantfut-tenis`) con el cron de `qf`; ver la entrada de `DEPLOYS.md`. Aislado del fÃºtbol: no comparte contenedores, base ni crontab del worker.
- El servidor estÃ¡ en Europe/Berlin: el cron usa 00:30 y 12:30 locales para que siempre caiga una ejecuciÃ³n en cada media jornada UTC (franjas de cuotas y cupo diario de API-Tennis), con o sin horario de verano.
- No se lanzÃ³ una captura de prueba de API-Tennis para no gastar el cupo local del dÃ­a (4 consultas UTC); la cadena se verificÃ³ con la entrada en seco y la tarea semanal real.
- Tareas de Windows desactivadas, no borradas (vuelta atrÃ¡s).

## 2026-10-21 â€” CI de tenis: prueba de cuotas en vivo dependÃ­a del reloj real

- `test_latest_market_devigs_and_respects_time` fallaba en `main` desde el 20-oct ~12:59 UTC. Causa: `run(..., clock=...)` solo controla el nombre de la franja; `Capture.request` sella `received_at` con `operations.now()` (reloj real). La prueba consulta `before=2026-10-20T11:00Z`, asÃ­ que pasÃ³ mientras el reloj real iba antes de esa hora y fallÃ³ al pasarla.
- DecisiÃ³n: el cÃ³digo es correcto (en producciÃ³n ambos relojes coinciden); se arregla la prueba fijando `tennis_engine.operations.now` con `monkeypatch`, sin tocar lo que comprueba (de-vig, orden temporal, orientaciÃ³n).
## 2026-10-21 â€” NBA: etiqueta de temporada en pronÃ³sticos prospectivos
`multimarket.prospective` calculaba la temporada del tipoff con el aÃ±o calendario ("2027-28" para un partido de enero de 2027), asÃ­ que de enero a junio regresaba el Elo un 25 % hacia 1500 a mitad de temporada. Ahora `season_label()` usa la temporada NBA (agosto en adelante abre la nueva), con prueba parametrizada. El paquete sellado RUN071 no se tocÃ³ (sus 42 pronÃ³sticos de octubre no estaban afectados); como `model.json` sella el hash del cÃ³digo, una cohorte nueva exige `evaluate` en un directorio nuevo, no reutilizar el de RUN071.

## 2026-10-21 â€” NBA v1.2: correcciones de la auditorÃ­a
Se creÃ³ `multimarket_v12` (protocolo congelado antes de correr) sin tocar RUN071: recalibraciÃ³n mÃ³vil, Elo con margen + descanso, ventaja local de las dos temporadas previas y bootstrap por fechas. Solo el ganador mejora de forma significativa (Brier âˆ’0,006 en ambas temporadas de test, sesgo local casi eliminado); equipos, total y jugadores quedan neutros, y el peso empÃ­rico de jugadores sigue en 0,25. PorquÃ© importa: la ventaja que faltaba en el ganador era deriva de calibraciÃ³n y descanso, no mÃ¡s complejidad. Informe docs/nba_multimarket_v12_20261021.md. Pendiente sin datos: lesiones, cuotas/CLV.

## 2026-10-21 â€” NBA v1.3: disponibilidad desde reportes oficiales
Se aÃ±adiÃ³ `availability`/`multimarket_v13` (protocolo congelado antes de correr) con los 816 reportes de lesiones ya descargados, regla estricta de 60 min antes del salto y partidos sin hora de salto tratados como sin informaciÃ³n. Mejora de forma significativa el ganador (Brier âˆ’0,005), los puntos de equipo y cinco de los seis mercados de jugador; el total y tapones no cambian. No se gastÃ³ ningÃºn crÃ©dito: The Odds API tiene 4.092 y fÃºtbol necesita ~300/dÃ­a hasta el 1-nov, asÃ­ que las cuotas histÃ³ricas NBA (~3.300 crÃ©ditos) quedan para despuÃ©s del reset. Informe docs/nba_multimarket_v13_disponibilidad_20261021.md.

## 2026-10-21 â€” NBA: plan de cuotas histÃ³ricas, sin gastar
`nba.odds_history` (plan/fetch/load) con 325 snapshots h2h (3.250 crÃ©ditos) y bloqueo en cÃ³digo antes del 1-nov, tope y reserva. Se decidiÃ³ por fases porque la bolsa de noviembre (~5.700 libres tras vivo y los 527 snapshots de fÃºtbol) no cubre h2h+totales. Los totales van en diciembre.

## 2026-10-21 â€” NBA v1.3 prospectivo: cohorte sellada y pÃ¡gina
`nba.multimarket_v13_live` + `multimarket_live_dashboard` (protocolo `multimarket_v13_live_protocol.json`). DecisiÃ³n clave: solo mercados de equipo (ganador, puntos de equipo, total) porque antes del salto no existe lista verificada de jugadores, y un reporte cuenta Ãºnicamente si su sello y nuestra recepciÃ³n son â‰¥60 min previos al salto; si no, el partido se sella como Â«sin reporte vÃ¡lidoÂ» en vez de Â«sanoÂ». Modelo ajustado una vez y anclado por hash (el hash del cÃ³digo cambiÃ³, no se reutiliza el de RUN071); la pÃ¡gina recalcula resultados desde el recibo oficial y una cohorte rota no oculta RUN071. Ensayo: 11 partidos reales sellados 8 h antes del primer salto. De paso se corrigiÃ³ el analizador del PDF (motivo partido en dos filas). No desplegado; plan en docs/nba_v13_prospectivo_20261021.md.

## 2026-10-21 â€” CI de tenis: prueba de cuotas en vivo dependÃ­a del reloj real

- `test_latest_market_devigs_and_respects_time` fallaba en `main` desde el 20-oct ~12:59 UTC. Causa: `run(..., clock=...)` solo controla el nombre de la franja; `Capture.request` sella `received_at` con `operations.now()` (reloj real). La prueba consulta `before=2026-10-20T11:00Z`, asÃ­ que pasÃ³ mientras el reloj real iba antes de esa hora y fallÃ³ al pasarla.
- DecisiÃ³n: el cÃ³digo es correcto (en producciÃ³n ambos relojes coinciden); se arregla la prueba fijando `tennis_engine.operations.now` con `monkeypatch`, sin tocar lo que comprueba (de-vig, orden temporal, orientaciÃ³n).

## 2026-10-21 â€” NBA: paso de comparaciÃ³n contra el mercado
- DecisiÃ³n: `nba.market_compare` une las probabilidades de ganador v1.3 con Pinnacle sin margen (cuotas en cachÃ©) y reporta Brier/logloss, mezcla logit 50/50 e IC por bloques de fecha. Se construye antes de la compra del 1-nov para que ese dÃ­a solo haya que comprar y ejecutar; probado con datos sintÃ©ticos, sin ejecutar con cuotas reales. Es solo investigaciÃ³n y no se despliega en el servidor.

## 2026-10-21 â€” AdMob y Meta app: dÃ³nde estÃ¡ cada pieza

- DecisiÃ³n: un solo bloque Â«RecompensadoÂ» (es lo Ãºnico que implementa la app: `RewardedAd` con SSV); sin banner, intersticial ni nativo. El ID de editor se guarda en `reward_settings` para que `/app-ads.txt` lo sirva desde el propio dominio de la ficha de Play (`https://pronosticosdeportivos.pro`, sin `www`).
- DecisiÃ³n: en Meta se apaga el registro automÃ¡tico de compras de la app porque las compras las manda el servidor por CAPI; con Ã©l activo saldrÃ­an duplicadas. En Meta los hashes de clave van en base64 (el SHA-1 de Play App Signing, de `llave.jks` y de la clave antigua).
- DecisiÃ³n: tras subir un AAB a Play se registra la versiÃ³n en `mobile_update_settings` por SSH; `min_build_android` y la obligaciÃ³n solo se tocan cuando esa versiÃ³n ya estÃ¡ disponible para los usuarios.
- Pendiente: ID de app y bloque de iOS (cuando exista la app en App Store), autorizaciÃ³n de anuncios de apuestas en Meta/AdMob, compra de prueba web con `META_TEST_EVENT_CODE`.

## 2026-11-02 â€” RediseÃ±o NBA, Sprint 0 (base `nba_datos`)

- DecisiÃ³n: `nba.dato_a_las(corte)` es el Ãºnico camino de lectura del motor y cada mÃ©trica declara su `resolucion`: `prioridad` (hechos Ãºnicos; gana la mejor fuente) o `por_fuente` (disponibilidad y proyecciones, que cambian cada hora; una fila por fuente, la mÃ¡s reciente visible). Sin esto, un parte oficial viejo taparÃ­a a un dato mÃ¡s nuevo de otra fuente.
- DecisiÃ³n: las tablas de evidencia rechazan UPDATE/DELETE/TRUNCATE con disparadores por sentencia (fallan incluso con `WHERE false` y con `TRUNCATE ... CASCADE`), para que ningÃºn "arreglo rÃ¡pido" pase por filas vacÃ­as.
- DecisiÃ³n: la huella de cada migraciÃ³n ignora CRLF/LF; en Windows y en el VPS el mismo archivo debe dar la misma huella.
- DecisiÃ³n: el margen de las cuotas no se guarda (vista `nba.cuota_margen`) y el mÃ©todo de quitado de margen queda en `nba.pronostico.version_modelo`.
- Pendiente: desplegar `nba-db` en el VPS con confirmaciÃ³n; el compose no se probÃ³ con Docker (no hay Docker en este PC).

## 2026-11-02 â€” RediseÃ±o NBA, Sprint 1a (carga y adaptadores)

- DecisiÃ³n: `guardar_datos(..., solo_cambios=True)` no repite una fila si el Ãºltimo valor visible de esa fuente y clave es idÃ©ntico; `nba.dato_a_las` ya devuelve ese valor hasta que cambie, asÃ­ que guardar cada hora lo mismo solo gastarÃ­a espacio.
- DecisiÃ³n: la identidad nunca fusiona por duda. Un nombre normalizado igual solo crea alias si hay UN candidato canÃ³nico que aÃºn no tiene fila de esa fuente; un segundo id de la misma fuente con el mismo nombre es otra persona.
- DecisiÃ³n: de ESPN lesiones solo existe la lista de quienes figuran; quien deja de figurar recibe `sin_reporte` (no Â«disponibleÂ»), porque la ausencia de reporte no prueba que juegue.
- DecisiÃ³n: los adaptadores no hacen red; reciben `obtener(url)`. Un error o un 403 deja una captura `ok = false` y ningÃºn dato imputado; los minutos nulos de Rotowire no se rellenan.
- Hallazgo: ESPN omite `athlete.id` en las lesiones; el id se saca del enlace pÃºblico del jugador. Rotowire usa los tricodes oficiales; ESPN usa GS/NO/NY/SA/UTAH/WSH.
- Pendiente: S1b y S1c; nada de S1 estÃ¡ desplegado todavÃ­a.

## 2026-11-02 â€” Rotowire/ESPN a `nba_datos` (Sprint 1c)

- DecisiÃ³n: Rotowire entrega gratis los minutos proyectados solo del visitante; el endpoint del local responde Â«debes ser suscriptorÂ». No se paga ni se rodea: se piden solo los visitantes y el aviso de pago queda como captura fallida con su texto.
- DecisiÃ³n: el colector prueba siempre la peticiÃ³n directa (gratis) y usa ZenRows solo ante 403/429/503 y con tope diario (30 crÃ©ditos); hoy ni Rotowire desde el VPS ni la prueba local necesitaron pago.
- DecisiÃ³n: ESPN se procesa en lotes de 200 recibos y el estado (`estado_espn.json`) avanza tras confirmar cada lote; un fallo a mitad no pierde el avance ni repite lo ya cargado.
- Hallazgo: en pretemporada ESPN trae rivales que no son de la NBA (p. ej. Â«LONÂ»); esos partidos se omiten en lugar de abortar la carga.
- Hallazgo: `docker exec` sin `-i` no pasa la entrada estÃ¡ndar, y un `pg_restore -l` asÃ­ falla con Â«input file is too shortÂ»; la prueba de restauraciÃ³n usa `-i`.
- Pendiente: ninguna captura es de pago salvo el respaldo; falta programar la copia fuera del VPS en el PC del titular y S1b.

## 2026-11-02 â€” Parte oficial y final del partido (Sprint 1b-A)

- DecisiÃ³n: un juego es Ãºnico por (fecha ET, local, visitante). Una misma fuente puede traer ids distintos del mismo juego (el PDF no trae id y se usa uno sintÃ©tico; cdn trae el real), asÃ­ que el alias se decide por esa tupla y los datos siempre se escriben bajo el canÃ³nico mÃ¡s antiguo.
- DecisiÃ³n: el id real de la NBA se reconoce por su forma (10 dÃ­gitos); los ids sintÃ©ticos del PDF no cuentan.
- DecisiÃ³n: el presupuesto de Scrapfly se mide por dÃ­a UTC con tope 25, y un archivo se reintenta como mucho dos veces (en la prueba real 14 de 30 peticiones a cdn fallaron y se cobraron).
- Hallazgo: el CDN de los PDF responde 403 (no 404) cuando el PDF de esa hora aÃºn no existe; desde el VPS responde igual que desde el PC, asÃ­ que no hace falta proxy.
- Error mÃ­o: probÃ© la identidad con fixtures donde el PDF no existÃ­a y no vi el choque entre ids sintÃ©tico y real hasta el despliegue; quedaron 15 canÃ³nicos duplicados inertes (la evidencia no se borra).

## 2026-11-02 â€” Cuotas de PropLine (Sprint 1b-B)

- DecisiÃ³n: el contrato de una lÃ­nea principal NO lleva el punto (la lÃ­nea se mueve y es un valor); el de una alternativa SÃ (cada punto es otro contrato). AsÃ­ `cuota_cierre` da la lÃ­nea principal al cierre.
- DecisiÃ³n: solo se guarda una cuota cuando cambia el precio o la lÃ­nea (compara contra el Ãºltimo valor de la misma fase), pero la primera de cada fase se guarda siempre; asÃ­ el primer precio dentro de la Ãºltima hora (el cierre) existe aunque no se haya movido.
- DecisiÃ³n: casas = Pinnacle (referencia afilada), DraftKings, FanDuel y BetMGM; los Â«milestoneÂ» se omiten porque derivan de las alternativas y multiplican las filas.
- Hallazgo: en PropLine los totales de equipo vienen como mercado `totals` con el campo `team`; se guardan como `team_totals` con el equipo como entidad.
- Hallazgo: el id de jugador de PropLine (`nba:NNNN`) coincide con el `personId` de cdn.nba.com, asÃ­ que las cuotas se unen a box scores sin cruzar nombres.
- VerificaciÃ³n: mÃ¡rgenes de Pinnacle 2,6-3,8 % en mercados de equipo y â‰ˆ 7 % en props, coherentes con la literatura (fichas 21-23).

## 2026-11-02 â€” Cuotas histÃ³ricas (Sprint 1b-C)

- DecisiÃ³n: se reutilizan los archivos de cuotas que ya existÃ­an (bet365 de BetsAPI, props y moneyline de The Odds API) en lugar de comprar un backfill; el instante de cada fila es el de la casa y la adquisiciÃ³n va en la captura `historico`.
- DecisiÃ³n: el margen se calcula por contrato, no por lÃ­nea (en un hÃ¡ndicap los dos lados tienen lÃ­neas opuestas).
- DecisiÃ³n: en el histÃ³rico de props la lÃ­nea forma parte del contrato porque un mismo jugador, casa y foto trae varias lÃ­neas.
- Error mÃ­o: la vista `cuota_margen` de la migraciÃ³n 0004 estaba mal para hÃ¡ndicaps y solo se vio con datos reales; la corrige la 0007. LecciÃ³n: probar las vistas con datos reales de cada mercado antes de dar un sprint por cerrado.
- Medida: 3,25 M de filas histÃ³ricas cargadas en â‰ˆ 7 min; la base ocupa â‰ˆ 290 bytes por cuota con Ã­ndices.

## 2026-11-02 â€” Cajas y partes histÃ³ricos (Sprint 1b-D)

- DecisiÃ³n: las cajas histÃ³ricas se cargan en bloque (`guardar_datos_lote`, sin comparar con otras fuentes ni con el valor anterior) porque no hay solape en el tiempo con las capturas hacia adelante; los partes sÃ­ van con Â«solo cambiosÂ» y en orden cronolÃ³gico.
- DecisiÃ³n: `recibido_en` de la caja final es la adquisiciÃ³n del archivo y `pit = reconstruido`; las consultas histÃ³ricas filtran por fecha de juego. Los partes usan la hora del parte.
- Medida: 2,7 M de filas de caja en â‰ˆ 6 min y 657 mil filas de partes en â‰ˆ 8 min (con Â«solo cambiosÂ» quedan 150 mil); â‰ˆ 300 bytes por fila con Ã­ndices.
- Pendiente: 113 jugadores ambiguos (nombre repetido sin equipo como pista) y la uniÃ³n entre ids de ESPN/Rotowire y los de la NBA depende de ello.

## 2026-11-02 â€” Sprint 2: disponibilidad y minutos

- DecisiÃ³n: la probabilidad de jugar sale de medir los partes contra quiÃ©n jugÃ³ (no de una convenciÃ³n). Mi convenciÃ³n inicial era peor (Brier 0,0289 frente a 0,0266 de la tabla medida) y los partes cambian de significado con los aÃ±os (Probable pasÃ³ de 93 % a 71 %), asÃ­ que la tabla se vuelve a medir cada temporada.
- DecisiÃ³n: el decaimiento de los minutos se eligiÃ³ con 2023-24 y 2024-25 (0,70); con el 0,90 que puse al principio el modelo solo igualaba a la media de 5 partidos. La incertidumbre sale de residuos por tramo de minutos esperados, no de las muestras del historial (daban 74,7 % de cobertura en el intervalo del 80 %).
- Hallazgo: quien no figura en la caja cuenta como que no jugÃ³; si se excluyen esos casos Â«QuestionableÂ» parece jugar el 80 %, cuando en realidad es â‰ˆ 43 %. Sesgo de selecciÃ³n que hay que evitar en cualquier evaluaciÃ³n de disponibilidad.
- LÃ­mite: Available (84 %) y Â«sin parteÂ» (84 %) mezclan titulares y fondo de plantilla; falta condicionar al rol.

## 2026-11-02 â€” Sprint 3: nÃºcleo del marcador y mercados de equipo

- Resultado honesto: un nÃºcleo solo de ratings de equipo queda calibrado pero NO aporta informaciÃ³n al cierre de bet365 (peso de mezcla 0,03 contra 1,03 de la lÃ­nea; RMSE 14,49 frente a 14,04). Coincide con lo que ya decÃ­a la calibraciÃ³n de la v1.5; no se intentÃ³ forzar la mÃ©trica con ajustes sobre la prueba.
- DecisiÃ³n: el nivel de liga se actualiza mÃ¡s rÃ¡pido (0,01) porque la anotaciÃ³n sube cada temporada; con 0,002 el total iba retrasado.
- Hallazgo: jugar en la noche siguiente cuesta â‰ˆ 2,8 puntos de margen por equipo (3,5 errores estÃ¡ndar) y no mueve el total. Se mide en el ajuste y se fija antes de mirar la prueba.
- DecisiÃ³n: coherencia entre mercados por construcciÃ³n (una sola muestra simulada por partido), no por reconciliaciÃ³n posterior.
- Siguiente palanca: jugadores esperados dentro del rating de equipo (lo que mueve una lÃ­nea es quiÃ©n juega).

## 2026-11-02 â€” Sprint 3b: jugadores dentro del nÃºcleo

- DecisiÃ³n: el nÃºcleo v2 promedia el rating de equipo con el de jugadores (margen y total); solo jugadores empeora el total (19,46 frente a 19,12).
- Hallazgo: el tope no son los minutos esperados. Con los minutos reales del partido el error del margen solo baja a 14,30 (mercado 14,04); lo que falta es saber mÃ¡s de cada jugador, no adivinar quiÃ©n juega.
- DecisiÃ³n: la probabilidad de jugar sin parte se condiciona al rol (53 % bajo 15 minutos esperados, 88 % entre 15 y 25, 98 % con 25 o mÃ¡s); el 84 % global mezclaba titulares seguros con fondo de plantilla.
- DecisiÃ³n: el equipo de cada jugador en cada partido es un dato propio (`equipo_del_jugador`, migraciÃ³n 0008); no se deduce de forma fiable despuÃ©s.

## 2026-11-02 â€” Sprint 4: props de jugador

- DecisiÃ³n: los props se valoran condicionados a jugar (las casas anulan la apuesta si no juega); la incertidumbre de minutos entra como mezcla sobre muestras de minutos, no como una cola aparte.
- Hallazgo: la cobertura de conteos bajos no se mide con el PIT de punto medio (88 % falso en triples); se usa el PIT aleatorizado, que es uniforme si la distribuciÃ³n estÃ¡ calibrada.
- Hallazgo: la cobertura del 80 % pasÃ³ de 73 % (v1.5) a â‰ˆ 81 % en las cuatro estadÃ­sticas sin reajustar nada contra el mercado.
- LÃ­mite: sin contexto del partido, la probabilidad de superar la lÃ­nea apenas discrimina (pendientes 0,09-0,61).

## 2026-11-02 â€” Sprint 5: referencia, evaluaciÃ³n Ãºnica, sellado y G-fuga

- DecisiÃ³n: el mÃ©todo de quitado de margen es proporcional; Shin y potencia ganan unas diezmilÃ©simas en favoritos fuertes pero no significativas, y el mÃ©todo queda escrito en `version_modelo` (no en la cuota).
- Hallazgo: la implementaciÃ³n independiente de G-fuga hallÃ³ un error real del motor (no aplicaba el arrastre de temporada al primer partido de una temporada nueva, â‰ˆ 2,3 puntos de diferencia). Una compuerta de reproducibilidad sola no lo habrÃ­a visto; hace falta compararla con un cÃ¡lculo hecho por otro camino.
- DecisiÃ³n: las cajas histÃ³ricas se aceptan por fecha del partido (su `recibido_en` es la fecha de adquisiciÃ³n del archivo), supuesto escrito en `pit.py`; el motor y el sellado exigen que el corte ya haya pasado.
- LÃ­mite: G-fuga cubre solo el motor de equipo; jugadores y props se enlazan en el Sprint 6.

## 2026-11-03 â€” Sprint 6: API de lectura y web NBA

- DecisiÃ³n: la distribuciÃ³n sellada guarda 199 cuantiles (pasos de 0,5 %) para que la API calcule la probabilidad de cualquier lÃ­nea sin resimular; es la misma informaciÃ³n que ya se sellaba, solo mÃ¡s fina (aÃºn no habÃ­a nada sellado en producciÃ³n).
- DecisiÃ³n: la API no manda texto visible, solo cÃ³digos de error; la web los traduce a los 6 idiomas y una prueba exige paridad de claves y cobertura de cÃ³digos.
- DecisiÃ³n: v2 sigue sin exponerse; el piloto v1 de `/nba` se mantiene hasta que apruebes v2 (despuÃ©s se retira del VPS).
- Pendiente real: sin el proceso `nba-motor` (sellado por partido) la web no tiene pronÃ³sticos que mostrar.

## 2026-11-03 â€” nba-motor

- DecisiÃ³n: el corte del pronÃ³stico es `salto âˆ’ 60 min`, no la hora en que corre el cron; un cron atrasado usa los mismos datos y G-fuga sigue valiendo. Nunca se sella despuÃ©s del salto.
- DecisiÃ³n: el cron NO se activa solo: un sello es solo-anexar, y un error del motor quedarÃ­a para siempre en la cadena. Se activa con tu visto bueno tras ver el simulacro.
- Incidente propio: al construir la imagen puse solo la etiqueta (`3ca6392`) en `imagen_actual`, que guarda el nombre completo (`nba-captura:3ca6392`); los crons de captura fallaron de â‰ˆ 00:10 a 01:33 UTC del 3-nov (â‰ˆ 1 h 20 min sin Rotowire/ESPN/partes/cdn/PropLine). Corregido; ESPN y partes recuperaron lo pendiente, las fotos de Rotowire de ese tramo no se pueden recuperar.

## 2026-11-03 â€” Props de jugador en el motor

- DecisiÃ³n: el servidor no entrena; los parÃ¡metros de props son un artefacto JSON versionado (huella en `version_modelo`, normalizada por finales de lÃ­nea) producido en local.
- Hallazgo (G-fuga): la plantilla limitaba la historia a 500 dÃ­as y el modelo validado usa los Ãºltimos 30 partidos sin lÃ­mite de edad; era una diferencia real entre producciÃ³n y lo evaluado. Corregida y comprobada contra una reconstrucciÃ³n independiente.
- DecisiÃ³n: los props de un partido se sellan todo o nada (una transacciÃ³n); si fallan, el equipo ya sellado se conserva y el siguiente cron completa.
- DecisiÃ³n: la alerta sale una vez por tipo, partido y dÃ­a; el estado se sembrÃ³ con lo anterior a la activaciÃ³n para no mandar una avalancha al primer mensaje.
- LÃ­mite: los jugadores no entran aÃºn en el pronÃ³stico del equipo.

## 2026-11-03 â€” Equipo 2.1 (jugadores en el equipo)

- DecisiÃ³n: se mezcla solo el margen, porque es lo Ãºnico que mejora en los dos periodos de evaluaciÃ³n; el total de la mezcla cambia de signo entre validaciÃ³n y prueba y se deja en el nÃºcleo de equipo.
- DecisiÃ³n: un solo pronÃ³stico de equipo por partido y corte; la versiÃ³n (2.0 o 2.1) dice si hubo plantilla suficiente. Sin ella se sella 2.0, nunca con jugadores inventados.
- Hallazgo: al reordenar el motor se perdiÃ³ la atomicidad de los props (cada sello se confirmaba solo); la prueba de fallo a mitad lo detectÃ³ y ahora van en una transacciÃ³n explÃ­cita.
- LÃ­mite: el artefacto de impacto es estÃ¡tico; sin reentrenos periÃ³dicos se degrada (el 3b lo reajustaba cada 21 dÃ­as).

## 2026-11-03 â€” Carga de SofaScore

- DecisiÃ³n: `nba_datos` sigue siendo la base principal; SofaScore es una fuente con menos prioridad que `nba_oficial` y se carga completa (todas las temporadas), no solo los huecos, porque da una verificaciÃ³n cruzada de la caja y los titulares.
- DecisiÃ³n: los jugadores se emparejan por la huella de la caja en el mismo partido, no por nombre; el nombre solo para quienes no comparten ningÃºn partido.
- Hallazgo: las dos cajas coinciden en mÃ¡s del 99 % de los datos; las diferencias son correcciones de estadÃ­stica (minutos 0,25 %, mÃ¡s/menos 0,77 %).
- Pendiente real: los entrenamientos, las evaluaciones y G-fuga se hicieron solo con nba_oficial; hay que repetirlos con la base nueva antes de la Fase 4.

## 2026-11-03 â€” Reentrenamiento con la base nueva

- Resultado: con SofaScore (mÃ¡s partidos, titulares y 2026-27) las evaluaciones de equipo, jugadores y props dan prÃ¡cticamente lo mismo que antes; los modelos no dependÃ­an de un detalle de la caja oficial.
- DecisiÃ³n: el efecto del descanso (2,90) y las sigmas se actualizan con la base nueva; eta, arrastre, tasa de liga y la regla Â«solo el margen se mezclaÂ» no cambian.
- Aprendizaje: la muestra de 100 partidos de G-fuga cambia cuando cambia el nÃºmero de partidos; su Brier no es una mÃ©trica del modelo (error tÃ­pico â‰ˆ 0,02), solo la alarma de fuga por debajo de 0,18.

## 2026-11-03 â€” Fase 4, F4.0: contratos

- DecisiÃ³n: la Fase 4 empieza por las fronteras entre pasos (Pydantic estricto), con el Paso A definido por sus salidas y no por el tipo de modelo; una red neuronal serÃ­a un retador mÃ¡s, sujeto a las mismas compuertas hacia adelante.
- DecisiÃ³n: las distribuciones de salida del contrato tienen la forma exacta de lo que ya se sella, para validar lo sellado, lo servido y lo simulado con un solo esquema.
- Hallazgo: las pruebas con datos absurdos encontraron un hueco real en el contrato (`descanso_dias` aceptaba un equipo faltante); y los 192 sellos reales cumplen los contratos.
- LÃ­mite: los contratos aÃºn no estÃ¡n conectados al motor ni a la API.

- DecisiÃ³n (F4.0): un contrato incumplido nunca se arregla en silencio: el motor no sella ese partido (o descarta ese jugador) y alerta; la API no sirve ese dato. Los sellos son inmutables, asÃ­ que la validaciÃ³n va ANTES de sellar.
- Hecho: los 5.852 distribuciones reales de la comprobaciÃ³n cumplen los contratos; la frontera no rechaza nada legÃ­timo.

## 2026-11-03 â€” F4.1: origen mÃ³vil

- Resultado: con tres temporadas de prueba distintas las conclusiones se sostienen; el modelo no supera al cierre en ningÃºn origen (ganador +0,0099 [+0,0071, +0,0127]); los jugadores acercan el modelo al mercado en los tres (âˆ’0,0024 a âˆ’0,0036 de Brier).
- Hallazgo: la distancia al mercado se achica con mÃ¡s temporadas de entrenamiento (+0,0119, +0,0099, +0,0078), y la pendiente de calibraciÃ³n del ganador queda algo por encima de 1 (probabilidades tÃ­midas), candidata a recalibraciÃ³n.
- LÃ­mite: la v1.5 solo puede compararse en 2025-26; las cuotas de cierre no existen antes de 2023-24.

- Resultado (F4.1, recalibraciÃ³n): ajustar la escala de la media o la probabilidad con temporadas anteriores no mejora ni acerca al mercado; la pendiente >1 de la prueba es ruido de muestra, no un sesgo estable. No se cambia el motor.

## 2026-11-03 â€” F4.2 Monte Carlo

- DecisiÃ³n: subir el equipo a 100.000 simulaciones porque con 20.000 el error del 1 % peor (0,86 pp) incumplÃ­a la compuerta de 0,5 pp y el coste de 100.000 es de 6 ms; los props no tienen Monte Carlo (son analÃ­ticos).
- Hallazgo: la reproducibilidad entre Windows y Linux es exacta bit a bit con la misma versiÃ³n de numpy; se fija la versiÃ³n y se conserva el script de huella como prueba al actualizar.
- Hallazgo: el error de un prop correlaciona +0,10 a +0,13 con el del total del partido y âˆ’0,13 con lo desigual en titulares; sin combinaciones en el producto no se simulan conjuntamente, pero no se debe multiplicar un prop por una probabilidad del partido.

## 2026-11-03 â€” F4.3 estrÃ©s

- Hallazgo: tres huecos reales encontrados por las pruebas de estrÃ©s (estadÃ­stica ausente = 0, minutos corruptos aceptados, equipo con ratings viejos sellado cuando solo a Ã©l le faltaban resultados); ninguno afectaba a los datos de hoy (la base estÃ¡ limpia) pero sÃ­ a cualquier fuente futura.
- DecisiÃ³n: la imagen con los arreglos no se despliega mientras estÃ© pendiente la decisiÃ³n del titular sobre el impacto S3c, para no mezclar cambios de comportamiento con una activaciÃ³n sin aprobar.
- CorrecciÃ³n: el 3-nov no hubo partidos NBA (elecciones); mi aviso anterior de que los primeros sellos de la imagen 6b85093 saldrÃ­an hacia las 22:00 UTC de hoy era falso: salen con los partidos del 4-nov.

- DecisiÃ³n del titular (3-nov): mantener el impacto S3c (RAPM de quintetos) en producciÃ³n; se despliegan los arreglos de F4.3 sobre esa base (`nba-motor:d73c7c5`).

## 2026-11-03 â€” F4.4 ensayo operativo

- Resultado: se restaura y se verifica en menos de un minuto, la manipulaciÃ³n se detecta y la vuelta atrÃ¡s son 1 s; el punto dÃ©bil es la distancia entre respaldos (24 h de sellos) y la copia fuera del servidor, que dependÃ­a de traerla a mano y estaba desactualizada.

- DecisiÃ³n del titular (3-nov): respaldo del VPS cada 6 horas y copia diaria al PC programada; asÃ­ la pÃ©rdida mÃ¡xima de sellos pasa de 24 h a 6 h y la copia fuera del servidor deja de depender de que alguien la traiga.

## 2026-11-03 â€” F4.5 informe final

- Resultado: v2 es calibrado, coherente, sellado y reproducible, y mejora la cobertura de props (73 % â†’ 80â€“81 %), pero es peor que el cierre del mercado en las tres temporadas de prueba y no mejora el margen de la v1.5; el informe lo dice sin adornos y propone un periodo prospectivo antes de publicar.
- Hallazgo: v2 depende de v1 sin que constara (el colector de ESPN lee el libro `run57` escrito por `nba-research-capture-run68-v2`); por eso el retiro de v1 queda condicionado a independizar ese colector y a la aprobaciÃ³n explÃ­cita del titular.
- DecisiÃ³n pendiente: etapas Aâ€“D del informe; ninguna se ejecuta sin el visto bueno del titular.

## 2026-11-03 â€” PromociÃ³n de v2 (orden del titular: Â«de una vez todoÂ»)

- Resultado: v2 queda pÃºblico como beta en `/nba/v2/` y v1 detenido; el colector `espn_directo` sustituye al ledger de `run57`, que era la Ãºnica dependencia de v2 hacia v1.
- DecisiÃ³n: v1 se detiene pero no se borra (reversible en minutos); `/nba` redirige a v2. Se acorta el periodo prospectivo: la evidencia de los sellos reales se mide en paralelo, ya con v2 publicado y con el aviso beta, en lugar de esperar 5â€“6 semanas antes de publicar.
- DecisiÃ³n: sin cuentas ni paywall por ahora (el piloto v1 tambiÃ©n era abierto); si el titular quiere integrarlo con cuentas, es una tarea aparte.

## 2026-10-21 â€” AuditorÃ­a de los tres motores (literatura + datos)
- Hallazgo principal: el ajuste de Dixon-Coles de producciÃ³n no converge (`success=False` por tope de evaluaciones; gradiente por diferencias finitas sobre 776 parÃ¡metros, 23 min) y la suma cero uniforme usa a los equipos sin datos como holgura, por lo que los que vuelven a la liga heredan fuerzas extremas. Con gradiente analÃ­tico (3-14 s), suma cero ponderada, ridge en partidos equivalentes y media vida 270, el RPS mejora âˆ’0,00084 [âˆ’0,00137, âˆ’0,00031] sobre 11.920 partidos, concentrado en inicios de temporada.
- DecisiÃ³n: el calibrador afÃ­n ajustado con el log-loss del 1X2 no identifica el nivel de goles y fuera de muestra empeora; no debe guardarse otro igual. La puerta tiene que medir tambiÃ©n mercados de goles.
- DecisiÃ³n: el mercado sin margen sigue siendo el pronÃ³stico mÃ¡s exacto donde hay cuota (peso Ã³ptimo del A en la mezcla = 0); el A se mejora por coherencia y cobertura, no para Â«batirÂ» a Pinnacle.
- Motor C: cÃ³rners totales bien; cÃ³rners por equipo y tarjetas ganan claramente con el contexto del partido. Â«CuÃ¡nticoÂ»: sin evidencia, no se persigue.
- Nada se cambiÃ³ en producciÃ³n; todo queda en `docs/auditoria_motores_20261021.md` a la espera de confirmaciÃ³n.

## 2026-10-22 â€” Pasos 1-3 de la auditorÃ­a implementados (sin desplegar)
- DecisiÃ³n: el ridge se expresa en partidos recientes equivalentes (`RIDGE_PARTIDOS`), porque la verosimilitud normaliza los pesos por su media y cualquier ridge fijo cambia de significado al crecer el histÃ³rico. Los artefactos anteriores cargan con `ridge_partidos=0` para conservar su objetivo.
- DecisiÃ³n: el calibrador de intensidades se ajusta con la verosimilitud del marcador, que identifica el nivel de goles; la puerta exige que el 1X2 no empeore. Con el modelo corregido se rechaza: no se publica calibrado.
- DecisiÃ³n: un ajuste sin converger no se activa nunca.
- DecisiÃ³n: con un equipo desconocido la app muestra el mercado, no el modelo.
- Despliegue pendiente de confirmaciÃ³n; el `.env` del servidor fija `DECAY_HALFLIFE_DAYS=180` y hay que cambiarlo.

## 2026-10-22 â€” CÃ³rners de cada equipo con la supremacÃ­a del Motor A
- DecisiÃ³n: un Î³ y un nivel por lado, sin conservar el total. La versiÃ³n que conserva el total sale peor porque, con un favorito claro, el partido tiene mÃ¡s cÃ³rners de los que dice el C y el reparto se los quitaba al visitante. El mercado de cÃ³rners totales no cambia.
- DecisiÃ³n: el contexto sale del Motor A (`predictions`) y solo si conoce a los dos equipos, por la regla del 2026-10-08 de no usar cuotas en el C.
- DecisiÃ³n: se quitan las dos lÃ­neas del visitante que fallan con el modelo nuevo. Las que ahora pasan no se aÃ±aden sin decisiÃ³n de producto.
- DecisiÃ³n (pedido del usuario): se aÃ±aden las lÃ­neas de cÃ³rners por equipo que pasan y pagan mÃ¡s (cuota mediana 1,43-1,78); las de 1,04-1,13 quedan fuera, como Â«menos de 4,5 golesÂ» el 6-oct. Solo con supremacÃ­a del A, porque sin ella no se validaron.
## 2026-10-21 â€” Tarjetas: se miden tambiÃ©n las lÃ­neas de Â«mÃ¡s deÂ» (sin publicar; worker desplegado el 22-oct)

MediciÃ³n en producciÃ³n (SQL sobre `tarjetas_seg`, 162 resueltas): Â«menos deÂ» 4,5/5,5/6,5 prometen 54/61/76 % y aciertan 67/85/93 %; el modelo se queda corto, al revÃ©s de lo que se temÃ­a el 10-oct. Las lÃ­neas de Â«mÃ¡s deÂ» nunca se midieron porque `LINEAS_HABILITADAS` solo trae Â«menos deÂ». DecisiÃ³n del usuario: `tarjetas_seg.LINEAS_SEGUIMIENTO` aÃ±ade Â«mÃ¡s deÂ» 2,5-7,5 y Â«menos deÂ» 3,5/7,5 solo al seguimiento; escalera y parley no cambian. Publicar tarjetas espera esa muestra (las filas del mismo partido estÃ¡n correlacionadas).

## 2026-10-21 â€” NBA: auditorÃ­a del motor de predicciÃ³n
RevisiÃ³n de v1.1-v1.3 y del vivo, con medidas sobre los datos locales (0 crÃ©ditos, nada desplegado). DecisiÃ³n clave: lo primero a corregir no es mÃ¡s complejidad sino que la disponibilidad descuenta dos veces las bajas largas (52 % de los Â«puntos perdidosÂ» ya estaban en la forma de 20 partidos; en vivo, Butler resta 19,9 a Golden State) y que Â«AvailableÂ» mezcla asignaciones G League. Siguen: desfase de hora del reporte entrenamiento/vivo, puntos de jugador sobreconfiados (pendiente 0,42; rango 80 % cubre 73 %), ganador y puntos incoherentes en ~19 % de partidos, peor Brier en oct-nov y `completed()` que redescarga toda la temporada. Sin cuotas sigue sin haber prueba frente al mercado. docs/nba_auditoria_motor_20261021.md; tareas en harness/tareas.md.

## 2026-10-21 â€” NBA v1.4: los arreglos de la auditorÃ­a no mejoran los mercados de equipo
`multimarket_v14` (protocolo `multimarket_v14_protocol.json` congelado con hash antes de correr; reproduce v1.3 a 1e-12). El doble conteo de bajas existÃ­a (la masa de puntos perdidos baja de ~33 a 13 y los coeficientes crecen 50-70 %), pero corregirlo no mejora ganador ni puntos de equipo (+0,0005 a +0,0008 de Brier, IC incluye 0) y falla la regla de decisiÃ³n, asÃ­ que el vivo se queda en v1.3. SÃ­ mejora los mercados de jugador de forma consistente (âˆ’0,0003 a âˆ’0,0014). Separar G League es neutro. HipÃ³tesis sin probar: el tÃ©rmino absoluto tambiÃ©n medÃ­a profundidad de plantilla lesionada. La tabla de participaciÃ³n necesita suelo. docs/nba_multimarket_v14_20261021.md.

## 2026-10-21 â€” NBA v1.4b: absoluto + relativo y suelo de participaciÃ³n, sin mejora
`multimarket_v14b` (protocolo congelado con hash, reproduce v1.3 a 1e-12). Los mercados de equipo no cambian (Brier Â±0,0004, IC incluye 0; falla la regla de decisiÃ³n) y el tÃ©rmino relativo no aÃ±ade nada sobre el absoluto, asÃ­ que la hipÃ³tesis de Â«profundidad de plantillaÂ» no se sostiene; v1.3 sigue en vivo. CorrecciÃ³n de mi diagnÃ³stico de v1.4: el suelo de 0,02 EMPEORA la participaciÃ³n (los Â«OutÂ» juegan 0,7 %) y separar G League tampoco la mejora; el empeoramiento no venÃ­a de los Â«OutÂ». LÃ­nea de lesiones agotada para equipo: lo que queda con margen es el ajuste por rival/ritmo, el prior de pretemporada, T-60 y las cuotas. docs/nba_multimarket_v14b_20261021.md.

## 2026-10-21 â€” NBA: cachÃ© de completed() y backfill T-60 (en curso)
CachÃ© por partido: sin ella cada cohorte redescargaba toda la temporada (~1.200 pÃ¡ginas en abril); ahora un partido final se baja una vez y un dÃ­a cerrado no se vuelve a listar. Un partido pasado en curso aborta el sellado en vez de saltarse en silencio (descanso y forma saldrÃ­an mal); un aplazado queda registrado. Editar el mÃ³dulo cambia su hash, asÃ­ que se reajustÃ³ el modelo vivo: parÃ¡metros idÃ©nticos al anterior. Backfill T-60: la NBA publica reportes cada hora (archivo HHPM sellado HH:30 ET) y el histÃ³rico solo tenÃ­a 13:30 y 17:30; hoy solo el 2-4 % de los partidos ve un reporte a menos de 1 h del corte (mediana 5,5 h). Dato clave: en ese bucket un 403 significa Â«archivo inexistenteÂ», no bloqueo (los existentes dan 200), asÃ­ que se usa un archivo de control para detectar un bloqueo real. El parser estricto del repo solo lee 2023-24 en adelante; 2022-23 queda con lo que ya hay. La uniÃ³n de IDs reproduce el 100 % de los IDs ya unidos (3.048/3.048).

## 2026-10-21 â€” NBA: backfill T-60 terminado
1.910 PDF horarios (y desde el 22-dic-2025 de cada 15 min, con nombre `HH_MMPM`) para 2023-24..2025-26; cobertura de reporte a â‰¤1 h del corte de 2-4 % a 99,8-99,9 %. Decisiones: un 403 de ese bucket es Â«no existeÂ» y se vigila con archivo de control; un timeout reintenta una vez y deja la descarga reanudable (la primera pasada muriÃ³ por un ReadTimeout a mitad, sin bloqueo); el cambio de nombre de archivo se descubriÃ³ porque 236 peticiones seguidas daban Â«no existeÂ». Descriptivo: con T-60 Â«OutÂ» juega 0,8 % (antes 4,3 %) y Â«DoubtfulÂ» 3,1 % (9,6 %), asÃ­ que la tabla de participaciÃ³n de v1.3 se entrenÃ³ con estados mucho menos informativos que los que recibe en vivo. Falta medir si eso cuesta predicciÃ³n (v1.5). docs/nba_cache_completed_y_backfill_t60_20261021.md.

## 2026-10-21 â€” NBA v1.5: reportes T-60 en la v1.3
`multimarket_v15` (protocolo `multimarket_v15_protocol.json` congelado con hash; la referencia reproduce v1.3 a 1e-9). Mismo cÃ³digo, solo cambian los reportes. ParticipaciÃ³n 0,491â†’0,383 y 0,447â†’0,314 de log loss; seis mercados de jugador mejoran de forma significativa (puntos âˆ’0,002). Equipo: puntos de equipo âˆ’0,0013/âˆ’0,0006, ganador Â±0,0004, total ~0, con IC del ganador de Â±0,002 (â‰ˆ1.200 partidos): ausencia de evidencia, no de efecto. Falla la regla de decisiÃ³n, asÃ­ que el entrenamiento vivo conserva sus reportes; entrenar con estados del mismo tipo que se sirven queda como decisiÃ³n del titular. LecciÃ³n: la calidad del reporte importa para la disponibilidad individual, no para el equipo, que ya la captura por otras vÃ­as; el siguiente paso Ãºtil son las cuotas y no mÃ¡s lesiones. docs/nba_multimarket_v15_20261021.md.

## 2026-10-21 â€” NBA: comparaciÃ³n con Pinnacle preparada
Se revisÃ³ `odds_history`/`market_compare` antes de usarlos y se encontraron tres fallos que habrÃ­an contaminado el resultado: Â«Los Angeles ClippersÂ» (proveedor) â‰  Â«LA ClippersÂ» (histÃ³rico) descartaba en silencio ~5,5 % de los partidos; un partido sin snapshot propio podÃ­a emparejarse con el precio de la vÃ­spera (el filtro de antigÃ¼edad mira al libro, no al salto); y, sobre todo, en los partidos de noche el mercado tiene un precio de hace horas mientras el modelo usa reportes hasta T-60, lo que favorece al modelo. DecisiÃ³n clave: la comparaciÃ³n principal limita la informaciÃ³n del modelo a la hora del snapshot (brazo alineado) y la regla de decisiÃ³n se congelÃ³ antes de comprar ningÃºn precio (esperable: sin evidencia de informaciÃ³n aÃ±adida; es vÃ¡lido). Ensayo con precios sintÃ©ticos de punta a punta. El modelo vivo no se tocÃ³. docs/nba_comparacion_pinnacle_20261101.md.

## 2026-10-21 â€” NBA: prueba prospectiva contra Pinnacle (offline)
`nba.live_market`: captura el precio actual de Pinnacle justo despuÃ©s de sellar cada cohorte y lo compara con los pronÃ³sticos sellados cuando hay resultado oficial. Decisiones clave: el paso de captura solo lee el bundle sellado y el cÃ³digo de pronÃ³stico no lo importa, asÃ­ que un precio nunca puede influir en un pronÃ³stico; la captura de la fase Â«selloÂ» se rechaza antes de gastar el crÃ©dito si pasan mÃ¡s de 15 min del sellado (si no, precio y pronÃ³stico no describirÃ­an el mismo momento); cada fase se guarda una sola vez con la respuesta cruda y su hash, sin reintentos; la regla de decisiÃ³n (400 partidos y fin de temporada, cobertura â‰¥85 %) se congelÃ³ antes de que existiera ningÃºn precio. Es la Ãºnica prueba sin sesgo de selecciÃ³n. Ensayada sobre la cohorte real con una respuesta sintÃ©tica: 11/11 partidos emparejados. La API no se ha llamado. Abierto: dÃ³nde corre la captura, porque el contenedor NBA no tiene credenciales. docs/nba_mercado_prospectivo_20261101.md.

## 2026-10-22 â€” NBA: lectura del servidor y propuesta para la clave de cuotas
Lectura (sin cambios) del servidor para proponer cÃ³mo dar al productor acceso a la clave de The Odds API. Hallazgos: ya corre un productor `nba-live13-producer:20261021` (cron cada 10 min, contenedor de corta vida, raÃ­z de solo lectura, sin capacidades, sin secretos) y el panel `nba-dashboard-live13:20261021`, ambos desplegados ayer y registrados en el DEPLOYS.md de `main` (mi rama iba por detrÃ¡s y no los veÃ­a; mis documentos decÃ­an Â«no desplegadoÂ» y quedaron desactualizados). La clave del piloto se monta como archivo 600 de solo lectura en /run/secrets, nunca como variable. DecisiÃ³n propuesta (no ejecutada): contenedor de captura propio con su archivo de clave, cohortes en solo lectura, carpeta de precios aparte y libro de presupuesto fuera de las cohortes (2 peticiones/dÃ­a, 70 crÃ©ditos/mes), porque el productor actual interpreta HTML de terceros y no debe ver la clave. El servidor sigue con el mÃ³dulo anterior a la cachÃ© de completed(); la captura va en un contenedor aparte, asÃ­ que el modelo del productor no cambia. docs/nba_captura_precio_servidor_propuesta_20261022.md.

## 2026-10-22 â€” NBA: captura del precio en el servidor, preparada (sin desplegar)
Aprobada la opciÃ³n A (contenedor de captura propio) con tope de 2 peticiones/dÃ­a y 70 crÃ©ditos/mes y fase de cierre. Hecho: clave del piloto copiada a un archivo 600 propio sin leerla (idÃ©ntica por cmp, 32 bytes = la clave sola, asÃ­ que el lector acepta ese formato ademÃ¡s de ODDS_API_KEY=); `live_market` guarda los precios fuera de la cohorte (que puede montarse en solo lectura, con prueba de que no se toca), aplica el presupuesto desde un libro fuera de las cohortes y se detiene con un archivo `halt` ante cualquier fallo; `capture-pending` es idempotente y antes del 1-nov no lee la clave ni toca el disco. DecisiÃ³n clave al leer `main`: el envoltorio del productor usa `exec`, asÃ­ que el paso de precios va en una lÃ­nea de cron propia cada 5 min con su `flock`, en vez de editar algo que estÃ¡ en producciÃ³n. Rectifico dos afirmaciones mÃ­as: el productor y el panel SÃ estÃ¡n en DEPLOYS.md de `main` (mi rama iba por detrÃ¡s), y desplegar la captura NO exige reajustar el modelo del productor. Pendiente: confirmaciÃ³n para desplegar y fusionar con `main`.

## 2026-10-22 â€” NBA: paso de precios desplegado (bloqueado hasta el 1-nov)
Fusionada la PR #77 (CI 4/4, arnÃ©s 1441) y desplegado el contenedor de captura de precios con su cron propio. Decisiones clave: se trabajÃ³ en un worktree limpio sobre `main` porque el Ã¡rbol compartido tenÃ­a cambios sin confirmar de otras sesiones y entradas ajenas en progreso.md/tareas.md que no debÃ­an arrastrarse; el contexto de construcciÃ³n se exportÃ³ con `core.autocrlf=false` porque `git archive` con el `autocrlf` de Windows entregaba CRLF y habrÃ­a roto el `.sh` en Linux (se verificaron los 69 archivos contra los blobs); el arnÃ©s del worktree fallÃ³ al principio por falta de `.env` (credenciales de la base de pruebas), no por cÃ³digo. La clave se copiÃ³ sin leerla y solo el contenedor de precios la monta, en solo lectura. Hasta el 1-nov cada pasada solo escribe Â«bloqueadoÂ» y no lee la clave. Pendiente: primera captura real el 1-nov. DEPLOYS.md tiene la vuelta atrÃ¡s.

## 2026-10-22 â€” App: iconos de mercado sin emojis
Los emojis de los mercados (ðŸŸ¨, âš–, âœŒ, ðŸ¥…...) dependen de la fuente del telÃ©fono y en Android antiguos salen como cuadro o en monocromo. `live_markets.dart`, `live_match_markets.dart` y `live_forecast.dart` usan ahora iconos de Material (los mismos criterios que `marketIcon`). Quedan emojis solo en textos traducidos del VIP (ðŸ’¡ ðŸ”’ âœ¦ â˜…), comunes y sin quejas. `flutter analyze` y los 261 tests pasan; sin compilar ni probar en dispositivo (emulador apagado). Hace falta nuevo build para que llegue a los usuarios.

## 2026-10-23 â€” NBA: cuotas histÃ³ricas compradas y comparaciÃ³n con Pinnacle
Por instrucciÃ³n del titular (opciÃ³n 3) se compraron antes del 1-nov los 325 snapshots h2h (3.250 crÃ©ditos + 10 de un diagnÃ³stico cuya respuesta no guardÃ©): saldo 3.560 â†’ 294, con fÃºtbol quedÃ¡ndose sin crÃ©ditos hasta el reset; lo advertÃ­ con cifras (fÃºtbol gasta ~500/dÃ­a de media) y el titular lo aceptÃ³. Se compraron primero 20 y se revisÃ³ la carga (99,4 % de cobertura, margen medio 2,8 %, coste exacto de 10) antes de seguir. Hallazgo: la API devolvÃ­a 422 porque el cÃ³digo enviaba la fecha con +00:00 y exige Z; las pruebas con cliente falso no podÃ­an verlo, asÃ­ que el primer contacto real con un proveedor nuevo debe ser una peticiÃ³n de prueba. Resultado con el protocolo congelado: el modelo de ganador no supera a Pinnacle (Brier +0,0040 y +0,0057 peor, c = 0,25 y 0,09 con IC que incluye 0) y, cuando discrepa â‰¥10 puntos, acierta el mercado. La conclusiÃ³n Ãºtil: el ganador NBA no se vende como pick; sirve como lÃ­nea base (Brier del mercado 0,195-0,200) para medir mejoras. Total del partido, puntos de equipo y jugadores no quedan cubiertos. docs/nba_comparacion_pinnacle_resultado_20261023.md.

## 2026-10-23 â€” NBA: props de jugador, correcciÃ³n de Â«no viableÂ»
Al investigarlo (documentaciÃ³n oficial, pÃ¡ginas de mercados/casas/precios y la sonda real de rebotes) la cifra de ~145.000 crÃ©ditos resultÃ³ correcta pero la conclusiÃ³n equivocada: el plan 5M de The Odds API cuesta $119 al mes y cubre props, `team_totals`, `totals` y `spreads` de dos temporadas con dos snapshots (â‰ˆ345.000 crÃ©ditos); y no hace falta lista verificada de jugadores, porque el mercado define el universo y las casas anulan el prop si no juega (17 de 17 nombres emparejaron). Pinnacle no cotiza props de jugador (solo casas de EE. UU.), asÃ­ que la referencia serÃ­a un consenso sin margen. La sonda sugiere que el mercado se concentra en 0,50 Â± 0,055 y que el modelo correlaciona 0,47: esperable que gane el mercado. LecciÃ³n: no declarar Â«inviableÂ» una cifra sin comprobar los precios reales del proveedor. docs/nba_props_jugadores_viabilidad_20261023.md.

## 2026-10-23 â€” NBA: sonda de props de jugador y elecciÃ³n de paquete
Sonda real de 110 crÃ©ditos (un partido por temporada, seis mercados): el histÃ³rico de props existe en 2024-25 y 2025-26, con 7-8 casas de EE. UU. y nombres que emparejan al 100 %. Puntos y rebotes cubren el 100 % / 86 % de los jugadores de â‰¥20 min (80-93 % de los minutos); asistencias y triples algo menos; robos y tapones son demasiado escasos (en 2025-26 no hay robos y solo BetMGM cotiza tapones) y se excluyen del anÃ¡lisis principal. Con cuatro mercados el coste es 40 crÃ©ditos por partido y snapshot; el escenario completo (2 temporadas, 2 snapshots, team_totals, totals/spreads de Pinnacle) son ~249.000 crÃ©ditos, y solo el plan 5M ($119) lo cubre; dos meses de 100K cuestan lo mismo y dan menos. RecomendaciÃ³n: un mes de 5M desde el 1-nov, con piloto previo y protocolo congelado antes de gastar. LecciÃ³n: calcular el paquete con costes observados en una sonda y no con la estimaciÃ³n teÃ³rica de seis mercados (que sobreestimaba un 35 %). docs/nba_props_sonda_y_paquete_20261023.md.

## 2026-10-23 â€” NBA: segunda auditorÃ­a y correcciones del productor
AclaraciÃ³n del titular: el motor busca probabilidad estadÃ­stica bien calibrada y muchos pronÃ³sticos, no ganar a las cuotas; la certeza se mide contra el resultado real y Pinnacle queda como referencia. Errores del productor corregidos en `nba/productor-correcciones` (sin desplegar). DecisiÃ³n clave: sellar cada partido en la pasada que lo encuentra 65-90 min antes de su salto en vez de una cohorte a las 17:35 ET; asÃ­ entran los partidos de tarde (7-8 %) y los de 18:00-18:45 reciben un reporte que cuenta, sin tocar modelo ni regla de lesiones (enmienda operativa 1.3.1). El sello y las recepciones se fechan cuando ocurren; una franja 403 se contrasta con un archivo de control para no confundir un bloqueo con Â«sin reporteÂ». LecciÃ³n del ensayo real: la pÃ¡gina actual de nba.com da minutos como `PT23M56.00S` y las archivadas `33:15`; las pruebas con datos sintÃ©ticos no lo veÃ­an. RectificaciÃ³n: la captura de precios con The Odds API sÃ­ estÃ¡ desplegada (22-oct); leÃ­ el DEPLOYS.md de una rama atrasada. docs/nba_productor_correcciones_20261023.md.

## 2026-10-23 â€” PropLine compartido: implementaciÃ³n preparada
ImplementaciÃ³n preparada en `codex/propline-hourly`, commit `5ff66cf`: archivo horario comÃºn, originales comprimidos, lecturas sin HTTP, conversiÃ³n de cuotas y adaptadores de fÃºtbol. ArnÃ©s de main: 1.468 aprobadas, 104 omitidas; 27 pruebas especÃ­ficas. Piloto NBA: cinco respuestas 200, 112.154 observaciones, cero fallos en esa pasada. LÃ­mite 4.500 solicitudes/dÃ­a y reserva global 500; detener captura con menos de 5 GiB libres.

**Sin activar aÃºn en producciÃ³n.** La revisiÃ³n automÃ¡tica rechazÃ³ subir esta rama al repositorio remoto por falta de autorizaciÃ³n explÃ­cita del destino. No se cambiÃ³ cron, imÃ¡genes, proveedor activo ni base del servidor. Pendientes: autorizaciÃ³n de subida a `cerorar23/quantfut`, PR/main, despliegue y primera pasada completa; terminar de conectar los lectores NBA/tenis al archivo comÃºn conservando los protocolos sellados. AuditorÃ­a del servidor por hashes, sin exportar su cÃ³digo; parche de API preparado desde las versiones verificadas del repositorio.

## 2026-10-23 â€” PropLine: alias de ligas y claves de mercado
La Championship nunca recibÃ­a cuotas de PropLine: el alias usaba `soccer_england_efl_champ` y la base guarda `soccer_efl_champ`. Corregido y aÃ±adidas Noruega, Suecia y Suiza, con una prueba que exige que cada alias exista en `db/*.sql`, para que el nombre no vuelva a divergir en silencio. Se aÃ±adieron a las familias las claves vistas en partidos reales (tiros, tiros a puerta, paradas, 2+/3+ goles, margen; aces, dobles faltas, juegos ganados, quiebres; escalones 10+/15+ puntos NBA). Hallazgo: `2plus_goals`/`3plus_goals` no se capturaban aunque el descubrimiento los viera, porque el filtro de claves de deporte exige empezar por letra; las claves de mercado usan ahora `MARKET_KEY`. Capturar mÃ¡s claves no cambia predicciones: siguen sin adaptador hacia los motores.

## 2026-10-24 â€” NBA: mercados de jugador en vivo con lÃ­neas de PropLine
Por decisiÃ³n del titular, el productor 1.3.1 pronostica puntos, rebotes y asistencias de jugador sobre la lÃ­nea de PropLine (el archivo horario comÃºn, leÃ­do sin red y con montaje de solo lectura). Decisiones clave: el universo y el umbral los define el mercado (lÃ­nea principal mÃ¡s repetida en â‰¥2 casas, sin DFS ni intercambios), pero las cuotas no entran en el modelo; el pronÃ³stico es condicionado a jugar porque las casas anulan al que no juega. Hallazgo medido antes de adoptarlo: la recalibraciÃ³n v1.3 aprendida solo en el umbral sintÃ©tico se desvÃ­a 5-8 puntos de tasa cuando la lÃ­nea estÃ¡ 2-4 por encima o por debajo, que es lo normal con lÃ­neas reales; ajustada sobre una rejilla de umbrales mejora el Brier fuera de muestra en los tres mercados. TambiÃ©n entran play-in y playoffs y se arreglaron las 3 pruebas caducadas del piloto. Sin desplegar. docs/nba_productor_correcciones_20261023.md.

## 2026-10-24 â€” PropLine: cierres y liquidaciones en el recolector
La clave es Hobby y nadie pedÃ­a cierres ni liquidaciones. Se piden una vez por partido terminado (liquidaciones: hasta 3 dÃ­as mientras falten resultados), a partir de nuestros propios marcadores. DecisiÃ³n de presupuesto con el Ã­ndice real del servidor (129/h de cuotas): 600 peticiones diarias reservadas por deporte y la captura horaria limitada a 3.900, para que el cierre no dependa de lo que sobre. Las claves nuevas de fÃºtbol se quedan en el descubrimiento diario porque en la familia horaria costarÃ­an +744/dÃ­a; el descubrimiento ya no descarta claves que empiezan por dÃ­gito.

## 2026-10-24 â€” PropLine: box score, lesiones NBA y lectores sobre la liquidaciÃ³n del #96
Otra sesiÃ³n fusionÃ³ antes el #96 (cierre y liquidaciÃ³n con reserva diaria). En vez de duplicarlo, el #97 se rehÃ­zo encima: el box score entra como tercer tipo de su cola, despuÃ©s del cierre y la liquidaciÃ³n, para que solo use lo que sobre de la reserva; en tenis queda apagado porque cierre y liquidaciÃ³n ya la agotan. Reserva subida a 730 (NBA 130, fÃºtbol 300, tenis 300) y lesiones NBA cada hora (+24): siguen dentro del tope de 4.500 con lo medido en el servidor. LecciÃ³n: antes de abrir un PR sobre un mÃ³dulo compartido, mirar los PR reciÃ©n fusionados por otras sesiones. docs/propline_compartido_20261023.md.

## 2026-10-24 â€” PropLine: cobertura real de mercados medida en el archivo
MediciÃ³n de solo lectura del archivo horario (5 h, 667 respuestas). DecisiÃ³n clave: medir la cobertura solo en los partidos de las prÃ³ximas 36 h, porque las casas publican cÃ³rners, tarjetas y props cerca del inicio y el conteo total la subestima. Resultado: en las diez ligas del modelo hay Pinnacle en 1X2, totales, hÃ¡ndicap, BTTS y cÃ³rners; tarjetas con Pinnacle en siete; goles por equipo tambiÃ©n, porque viaja en `totals` con el campo `team` (una primera lectura buscÃ³ la clave `team_totals`, que no existe, y lo dio por ausente: hay que agrupar por `(key, period, team)`). Pendiente de remedir: props NBA el dÃ­a del partido y copas europeas en semana de copa. docs/propline_cobertura_20261024.md.

## 2026-10-24 â€” Recolector SofaScore (Apify, rl1987) en el VPS
DecisiÃ³n: `azzouzana/sofascore-scraper-pro` estÃ¡ roto (3 de 3 URLs fallan); se usa `rl1987`. El coste real es ~0,01 USD por partido con detalle, no los 3 USD/mes estimados; el titular autorizÃ³ hasta 15 USD/mes. `listRounds` cuesta ~0,12 USD por liga, asÃ­ que la jornada actual se toma del prÃ³ximo partido. El tenis se localiza cada 6 dÃ­as barriendo un dÃ­a de calendario y filtrando categorÃ­a ATP/WTA. Cada respuesta se archiva con la hora real de recepciÃ³n (SofaScore no la entrega). Cron 07:40 UTC en `~/sofascore-apify/`; ver DEPLOYS.md.

## 2026-10-24 â€” BetsAPI: clave nueva y mercados completos de bet365
El plan de un dÃ­a caducÃ³ (403 a las 04:15 UTC); el titular dio otra clave (solo en el VPS, `~/betsapi/.env` y `~/quantfut-tenis/secrets/.env.betsapi`). Hallazgo medido: `/v2/event/odds` solo trae los mercados principales, pero `/v4/bet365/prematch` devuelve todos (â‰ˆ125 en NBA con props de jugador, â‰ˆ190 en fÃºtbol con goleadores, tarjetas, cÃ³rners y estadÃ­sticas de jugador, sets/jugador en tenis), tambiÃ©n para partidos ya jugados, aunque bet365 los borra a las ~3-4 semanas (NBA abr-2026 y LaLiga 14-sep vacÃ­os). Por eso la cadena (`~/betsapi/cadena3.sh`) baja primero ese modo `prematch` desde el 20-sep y despuÃ©s reanuda el histÃ³rico de cuotas principales (fÃºtbol 2022+, NBA 2020+, tenis 2023+). Un cron horario (`fotos.sh`, :17) guarda fotos de los prÃ³ximos con hora real de recepciÃ³n (`fetched_at`), porque los props histÃ³ricos anteriores a ~1 mes no existen en ninguna parte de BetsAPI. Lotes de 10 en `event/view` y `prematch`: 2 peticiones por 10 partidos.

## 2026-10-24 â€” SofaScore vÃ­a Apify: proveedor por deporte
DecisiÃ³n del titular: `scrapesage/sofascore-scraper` para NBA y tenis, `rl1987/sofascore-api-scraper` para fÃºtbol; `azzouzana` descartado (publicado y Â«SucceededÂ», pero solo devuelve `NO ND script found`, comprobado en la consola). Motivo: con 2-3 partidos por deporte, `rl1987` tiene la alineaciÃ³n de fÃºtbol mÃ¡s profunda (~127 mÃ©tricas por jugador) pero en NBA devolviÃ³ un solo partido sin estadÃ­sticas, mientras `scrapesage` cubre NBA y tenis y llegÃ³ a un histÃ³rico con `seasonIds`. Trampa: el id de ATP ParÃ­s es 2404, no el 1415 de la URL. Es una prueba, no una auditorÃ­a; el gasto real no se midiÃ³ y no hay cÃ³digo ni despliegue. docs/sofascore_apify_proveedores_20261024.md.

## 2026-10-24 â€” Recolector SofaScore del VPS: actor por objetivo
Se adaptÃ³ `sofascore_apify.py` para que cada objetivo lleve su `provider` (NBA y tenis con scrapesage, fÃºtbol con rl1987). DecisiÃ³n clave: las filas de scrapesage se normalizan al Ã­ndice comÃºn (matchId â†’ id) pero el cuerpo original se archiva intacto y cada recibo anota el actor en `params._actor`; el detalle se agrupa por actor y scrapesage recibe ids enteros (rl1987 cadenas). El descubrimiento semanal de torneos de tenis sigue con rl1987 porque scrapesage no tiene modo por fecha. AclaraciÃ³n del titular: la cuenta Apify es de pago, asÃ­ que el presupuesto no es el riesgo que creÃ­ (corrijo mi nota de Â«plan gratisÂ»); se mantienen los topes por corrida. Respaldo previo en el VPS; desplegado sin tocar el cron. Ver DEPLOYS.md.

## 2026-10-24 â€” Props de jugador NBA: cuotas histÃ³ricas y comparaciÃ³n con el mercado
DecisiÃ³n del titular: clave nueva de The Odds API (plan 100K, solo NBA); 4 mercados Ã— 1 captura por partido (2.424 partidos, ~97.100 crÃ©ditos). Los props solo existen en el endpoint por evento, asÃ­ que `props_history.py` lista eventos por dÃ­a (1 crÃ©dito) y paga cada partido a `tipoff âˆ’ 30 min`; una captura sin cierre sirve para entrenar, no para CLV. `props_link.py` une cada cuota con el box score del MISMO partido (sin distancia de ediciÃ³n; 9 alias verificados); los jugadores que no jugaron se conservan sin resultado para que el entrenamiento decida.
Resultado de `props_market.py` (protocolo congelado antes de correr): el modelo v1 pierde contra el mercado en los 4 mercados (Brier +0,006 a +0,022); `c` â‰¤ 0,17. Por eso el archivo no se usa para sustituir al mercado sino como ancla de un futuro modelo de residuo. Detalle: `docs/nba_props_historicos_descarga_20261024.md`, `docs/nba_props_vs_mercado_20261024.md`.

## 2026-10-24 â€” PropLine: team_stats empareja clubes escritos distinto
La verificaciÃ³n de la primera pasada real (release 5a9cde0) mostrÃ³ que `team_stats` solo casaba los dos equipos en 46 de 98 box scores de fÃºtbol: las casas y la fuente del acta escriben distinto (Â«IpswichÂ» / Â«Ipswich TownÂ»). DecisiÃ³n: aceptar que un nombre plegado contenga al otro y, con exactamente dos clubes, deducir el segundo del primero; cualquier ambigÃ¼edad devuelve vacÃ­o. Medido sobre el archivo real: 95 de 98. LecciÃ³n: probar los lectores contra datos reales antes de darlos por buenos, no solo contra un caso inventado.

## 2026-10-24 â€” NBA: auditorÃ­a de datos para entrenar todos los mercados
No toda la data estÃ¡ conectada. Entrenables ya: ganador (con h2h), puntos de equipo/total contra resultado y los 4 props principales con cuotas. DecisiÃ³n clave: el primer cuello de botella no es comprar mÃ¡s, sino que el normalizado que leen los modelos descarta columnas ya descargadas (tiros intentados, pÃ©rdidas, posesiones) y los playoffs; las cuotas de hÃ¡ndicap/total existen en BetsAPI del VPS pero sin normalizar. El pendiente h2h "desde el 1-nov" estaba desactualizado: se comprÃ³ el 23-oct. docs/nba_auditoria_datos_entrenamiento_20261024.md.

## 2026-10-24 â€” NBA: modelo de props anclado en el mercado
Con protocolo congelado (entrena 2024-25, evalÃºa 2025-26, IC 98,75 %) las variables propias (v1, disponibilidad T-60, total y hÃ¡ndicap de bet365 Â«as-ofÂ» el precio, ritmo, defensa rival, descanso, minutos) no aÃ±aden informaciÃ³n al consenso de las casas de EE. UU. en ningÃºn mercado: la mejora mÃ¡xima es 0,0004 de Brier. En rebotes y triples toda la mejora es recalibrar el consenso, que sobrevalora el Over 1-2 puntos. DecisiÃ³n clave: se descartan los precios a mÃ¡s de 60 min del salto (1.566 unidades) para que un reporte T-60 no aporte informaciÃ³n que el precio no tenÃ­a. Defecto del protocolo, declarado: el placebo se compara contra el mercado crudo y por eso confunde recalibraciÃ³n con fuga, asÃ­ que rebotes y triples quedan como corrida nula por la letra; el control correcto es contra la recalibraciÃ³n y exige un v1.1 marcado como posterior a ver los nÃºmeros. Con precio, lo mejor es el consenso recalibrado; sin precio (robos, tapones, combinados) el motor depende de su modelo y se mide contra el resultado. docs/nba_props_residual_20261024.md.

## 2026-10-24 â€” NBA: normalizado ampliado con tiros, pÃ©rdidas, posesiones y postemporada
`nba.extended_box` con protocolo congelado antes de construir. DecisiÃ³n clave: el conjunto nuevo no toca ninguna fila de RUN071 (una prueba de no regresiÃ³n aborta si una sola fila regular cambia) y la postemporada sin filas aceptadas se marca `sportsdataverse_only`, cuadrada con las identidades del box y el marcador de API-Sports, en vez de mezclarla sin distinguir con la base de dos fuentes. Las pÃ©rdidas del box de equipo incluyen las de equipo, asÃ­ que se exige â‰¥ la suma de jugadores y la estimaciÃ³n de posesiones usa la suma de jugadores en todos los partidos para que sea comparable. Hallazgo: las filas aceptadas ya traÃ­an un campo `provenance` y la primera pasada lo pisaba; lo detectÃ³ la no regresiÃ³n. 6.414 partidos, 53 regulares perdidos (0,87 %). docs/nba_normalizado_ampliado_20261024.md.

## 2026-10-24 â€” NBA: cuotas de bet365 normalizadas (BetsAPI) y matriz por mercado
DecisiÃ³n clave: BetsAPI lista primero al visitante como Â«homeÂ» en el 100 % de los partidos, asÃ­ que emparejar por (fecha, local, visitante) no dio ninguna coincidencia y, peor, habrÃ­a invertido el lado de todas las cuotas de ganador y hÃ¡ndicap. Se resolviÃ³ con una sonda de orientaciÃ³n (solo equipos, fecha y marcador, sin cuotas), enmienda v1.1 del protocolo con el hash anterior conservado, y reorientaciÃ³n por partido contra la referencia. La regla de aceptaciÃ³n del 99 % sobre todos los eventos se cambiÃ³ por el acuerdo de marcador entre los emparejados (99,95 %), porque la referencia excluye partidos propios. Integridad tras construir: victoria local 55,1 % frente a 55,5 % implÃ­cito; margen + lÃ­nea â‰ˆ 0,05. 34.713 filas, 3.867 partidos, cierre mediano a 2,3 min del salto. Una sola casa y descarga histÃ³rica: la recepciÃ³n original es desconocida. Para entrenar no hace falta una casa con todo: hace falta, por mercado, una fuente igual antes y despuÃ©s (ganador: Pinnacle; hÃ¡ndicap/total/mitad/Q1: bet365; props: consenso de 6 casas de EE. UU.), con la casa marcada en cada fila. docs/nba_cuotas_betsapi_normalizadas_20261024.md, docs/nba_matriz_mercados_y_estudios_20261024.md.

## 2026-10-24 â€” NBA: entrenamiento y calibraciÃ³n de todos los mercados
Dos corridas con protocolo congelado (ajuste 2024-25, prueba 2025-26). Contra el cierre de bet365 el motor no mejora ninguno de los nueve mercados de equipo y recalibrar el precio no aporta: el cierre ya estÃ¡ calibrado. Hallazgo de medida que cambiÃ³ el plan: en hÃ¡ndicap y total la lÃ­nea deja la probabilidad en ~50 %, asÃ­ que medir contra el mercado no discrimina; se midiÃ³ la distribuciÃ³n del motor en varias lÃ­neas contra los resultados. En equipo el motor tiene habilidad en 11 de 12 mercados con pendiente â‰ˆ 1, pero la lÃ­nea de bet365 es mejor centro (RMSE 18,4 contra 19,3 en el total) y las desviaciones del motor respecto a la lÃ­nea no informan (peso âˆ’0,39 en el total). En jugador sin cuota, la ley v1 aplicada a las combinaciones estÃ¡ sobreconfiada (pendiente 0,78): recalibrar ayuda y aÃ±adir disponibilidad y entorno la corrige (Brier âˆ’0,005), sobre todo por el minutaje perdido de los compaÃ±eros; en robos, tapones y pÃ©rdidas la ganancia es pequeÃ±a. Dos defectos de diseÃ±o detectados antes de ver resultados reales y enmendados: el placebo de equipo comparaba contra la recalibraciÃ³n (siempre Â«mejorÂ» si el modelo informa) y pasÃ³ a compararse con el modelo solo (v1.1). Los parÃ¡metros estÃ¡n guardados con `promoted: false`; aplicarlos al vivo es una decisiÃ³n aparte. docs/nba_calibracion_motor_20261024.md.

## 2026-10-24 â€” NBA: productor vivo 1.3.2 con las sumas de puntos, rebotes y asistencias (preparado, sin desplegar)
Llevar al vivo la calibraciÃ³n de las combinaciones, que son donde la ley v1 sale mÃ¡s sobreconfiada, no necesitÃ³ un modelo nuevo: reutiliza el mecanismo del productor (logit p, sesgo, estado propio y minutos perdidos de los compaÃ±eros, ajustado sobre la rejilla de umbrales). Las cuatro sumas pasan el chequeo congelado (Brier âˆ’0,0023 a âˆ’0,0086 contra la ley cruda, pendiente 0,58-0,85 â†’ 0,98-1,01). DecisiÃ³n clave: el modelo candidato se verificÃ³ contra el desplegado y es idÃ©ntico en equipo y en puntos, rebotes y asistencias (solo cambian el hash del mÃ³dulo y las cuatro sumas nuevas), y el productor omite en vez de adivinar un mercado que su modelo no conoce. Riesgo de despliegue anotado: el panel actual rechaza una cohorte con un mercado desconocido, por lo que el orden es panel primero y productor despuÃ©s, y la vuelta atrÃ¡s conserva el panel nuevo. Robos, tapones, pÃ©rdidas y doble-doble siguen fuera porque las filas de box score vivas no los traen. docs/nba_productor_combinaciones_20261024.md.

## 2026-10-24 â€” NBA: el despliegue del productor 1.3.2 deja de depender de cÃ³mo se copiÃ³ el mÃ³dulo
El productor se niega a sellar con un modelo ajustado por otro mÃ³dulo, y ese hash era el de los bytes del archivo: cambiaba con los saltos de lÃ­nea de cada copia (Windows contra el servidor), asÃ­ que un modelo bueno habrÃ­a sido rechazado y habrÃ­a que reajustarlo en el servidor. Ahora es el hash del contenido con los saltos normalizados. AdemÃ¡s las comprobaciones que antes eran una lista manual (equipo y puntos, rebotes y asistencias idÃ©nticos al modelo desplegado, sumas presentes, insumos iguales salvo mÃ³dulo y protocolo) son el comando `compare`, que sale con cÃ³digo 1 si algo no coincide. Ensayado de punta a punta con el modelo real: 10 de 10 comprobaciones. docs/nba_productor_combinaciones_20261024.md.

## 2026-10-25 â€” NBA: productor vivo 1.4.0, reentrenado con la data nueva pieza por pieza
El titular pidiÃ³ el motor vivo entrenado y calibrado con toda la data nueva y desplegado. DecisiÃ³n clave: ninguna pieza entra por existir; cada una se comparÃ³ contra la anterior con el mismo fit_model del productor y sobre las mismas unidades de 2025-26 (protocolo congelado). Entran los reportes T-60 en el ajuste (Brier âˆ’0,0018, la mayor ganancia: el vivo servÃ­a reportes de una hora antes del salto pero se habÃ­a ajustado con los de 13:30/17:30), el entorno del partido en la calibraciÃ³n de jugador (âˆ’0,0003) y cuatro mercados nuevos (triples, robos, tapones, robos+tapones). No entran el dataset con play-in y playoffs (empeora rebotes y asistencias: el rol de postemporada no es el de la regular) ni el ajuste del nivel de anotaciÃ³n dentro de la temporada (empeora los puntos de equipo). Con RUN071 no hay posesiones ni tiros: ritmo, defensa rival y uso quedan con peso 0. De paso se encontrÃ³ el productor parado desde el 24-oct por un minutaje `10:60` de nba.com; se arreglÃ³ y desplegÃ³ 1.3.2 antes de seguir. docs/nba_productor_14_20261025.md.

## 2026-10-25 â€” NBA: el vivo usa RUN071 + columnas nuevas y suma pÃ©rdidas
El dataset ampliado se habÃ­a rechazado entero en 1.4 porque mezclaba dos cosas: postemporada en el historial (empeora) y columnas nuevas. DecisiÃ³n clave: separarlas con un protocolo congelado propio y quedarse solo con las columnas sobre la temporada regular de RUN071. Mejora los 11 mercados de jugador (conjunto âˆ’0,00015; ninguno empeora), da peso real a ritmo, defensa rival y tendencia de uso, y deja entrar pÃ©rdidas (âˆ’0,0012 contra la ley cruda, pendiente 1,00). El productor no cambia de cÃ³digo; cambian datos y modelo. docs/nba_productor_14b_20261025.md.

## 2026-10-25 â€” AuditorÃ­a de los tres motores y alias de PropLine para las cuotas
Los datos de PropLine y SofaScore llegan y los tres motores vuelven a producir (corrida del 25-oct: 41 predicciones del A, 28 de alta probabilidad), pero 19 de 63 partidos se quedaron sin precio. DecisiÃ³n clave: el cuello de botella ya no es la fuente sino el emparejamiento. El calendario y los resultados de PropLine aprenden alias con la fuente `propline`, y el lector de cuotas solo consulta `odds_api`: Interâ€“Fiorentina o Riverâ€“Racing estaban en el archivo a la hora exacta, sin poder emparejarse. Se copiaron a `odds_api` los alias aprendidos (revisados uno por uno) y 18 manuales; las conjeturas del difuso (LanÃºs â†’ San Luis, Brugge â†’ Brage, Cologne â†’ Kaiserslautern) se rechazaron, por eso no se aceptan en bloque. Arreglo de fondo pendiente: que `odds_worker` lea tambiÃ©n `propline`. docs/auditoria_motores_20261025.md; DEPLOYS.md.

## 2026-10-25 â€” NBA: tercera auditorÃ­a (motor, props, vivo, cierres y crÃ©ditos)
DecisiÃ³n clave: los fallos ya no estaban en el modelo sino en la operaciÃ³n alrededor de Ã©l, y por eso se corrigieron y desplegaron en el acto. El 1.4b se habÃ­a quedado a medias (panel nuevo, productor viejo) porque el ensayo de la madrugada simulaba las 19:40 con un archivo de PropLine de las 04:07 y daba 0 props; con la hora real coincide con el 1.4.0 (362 pronÃ³sticos) y se completÃ³. El hueco grande era PropLine: su peticiÃ³n principal de NBA da 504 a las horas de sellado y un partido se sellÃ³ sin hÃ¡ndicap ni total; ahora se reintenta solo el partido completo. La reserva de 500 corta la pasada de las 23:07 UTC, que desde el 1-nov alimenta los partidos de las 20:00-20:30 ET; en vez de tocar la reserva (decisiÃ³n del titular) se quitaron llamadas sin dato (lotes tras una principal vacÃ­a, marcadores de ligas sin motor cada 3 h), ~150/dÃ­a. La captura de precios con The Odds API se retirÃ³: contradecÃ­a la decisiÃ³n de PropLine como fuente en vivo, que ya trae Pinnacle. docs/nba_auditoria_20261025.md.

## 2026-10-25 â€” App: auditorÃ­a de datos, pronÃ³sticos y ergonomÃ­a
DecisiÃ³n clave: en una pantalla, una selecciÃ³n tiene UN porcentaje, el sellado. La lista Â«Mercados del partidoÂ» es anÃ¡lisis del modelo y el destacado es el pick sellado; con fuentes distintas, la misma selecciÃ³n salÃ­a con 76 % y 79 %, y un pick gratis de lado distinto al mÃ¡s probable del anÃ¡lisis (Barcelona o empate frente a Â«12Â») desaparecÃ­a de la lista. `aplicar_acceso` ahora usa la probabilidad sellada en las filas de picks abiertos y aÃ±ade los que el anÃ¡lisis no lista; el resto del anÃ¡lisis no cambia.
Los textos en espaÃ±ol que llegaban fijos (Inicio, historial de la Escalera, patas del Parley) se redactan en la app desde `market/selection/line`; por eso el Parley envÃ­a ya esos campos. Â«Marca XÂ» solo vale para mÃ¡s de 0,5. Un partido con el saque pasado hace mÃ¡s de 130 min y sin resultado dice Â«Esperando resultadoÂ»: el resultado llega por ciclos (otra sesiÃ³n lleva el resultado al pitido) y llamarlo Â«en juegoÂ» a las 3 h engaÃ±a. Medido en producciÃ³n a las 23:09 UTC: Barcelonaâ€“Real Madrid (20:00 UTC) seguÃ­a `scheduled` sin marcador.
Visto y descartado como error: Serie B, LaLiga 2, Allsvenskan y Suiza siguen en la agenda hasta que corra la 088 (01:30 UTC del 26-oct, aplazada a propÃ³sito). Sin desplegar: la API y el build de la app esperan visto bueno.

## 2026-10-25 â€” Destacado del detalle: cuota mÃ­nima 1,40

DecisiÃ³n del usuario: el destacado era un 93 % a cuota 1,08 (hÃ¡ndicap +1,5), sin valor para quien lo ve. Ahora es el de mayor probabilidad con cuota publicada >= 1,40 entre los pronÃ³sticos sellados del partido; sustituye la banda 74-85 % / 1,20-1,60 que estaba sin confirmar en el Ã¡rbol. Solo compiten picks sellados (alta probabilidad 73-95 % y escalera), nunca las filas de `partido_mercados`, que son anÃ¡lisis con cuota justa y no tienen cuota de mercado al publicar: destacarlas romperÃ­a predecir â†’ sellar â†’ publicar. Consecuencia: con el piso 1,40 habrÃ¡ partidos sin destacado (el detalle lo avisa). Solo app; el servidor no cambia.

Mismo dÃ­a, decisiÃ³n del usuario: el historial de retos ya no muestra el resumen Â«N cumplidos de M cerradosÂ», la tasa de cumplidos ni el resultado acumulado; solo el tÃ­tulo y la lista (9 Ãºltimos cumplidos + Ãºltimo fallido). El servidor sigue enviando `resumen` (se usa `cerrados` para saber si estÃ¡ vacÃ­o); no se tocÃ³ la API ni la web.

## 27-oct-2026 Â· Gratis de Alta probabilidad: 10 % del dÃ­a

DecisiÃ³n del titular: es gratis el 10 % de los pronÃ³sticos publicados en el lote del dÃ­a, redondeado hacia arriba (1-10 â†’ 1, 11-20 â†’ 2), los de mayor probabilidad; sustituye Â«uno por mercado, mayor cuota â‰¤ 1,60, hasta 4 abiertosÂ» (12/14-oct). Primero pidiÃ³ solo cuotas 1,40-1,50; el ensayo de solo lectura en producciÃ³n dio 0 pronÃ³sticos en ese rango en toda la semana (1,40 implica â‰ˆ71 %, por debajo del piso de 73 % de la secciÃ³n) y el dÃ­a habrÃ­a quedado sin gratis, asÃ­ que lo cambiÃ³ por Â«sin filtro de cuotaÂ». Solo se exige que haya cuota publicada real. El cupo se mide por lote, y los gratis que ya empezaron siguen visibles y cuentan dentro de Ã©l (el historial no se esconde y el dÃ­a no supera el 10 %). Los lotes ya repartidos con la regla vieja no se reescriben (`mobile_free_allocations` solo crece): `top_up` completa el cupo y `cap_free` recorta al leer, asÃ­ que los abiertos gratis que sobran del cupo pasan a candado. De paso: el arnÃ©s de Windows fallaba en PowerShell 5.1 porque `-c` perdÃ­a las comillas internas del bootstrap; ahora va en un archivo.

## 27-oct-2026 Â· NBA: estadÃ­sticas de equipos en la web (solo marcadores finales)

PeticiÃ³n del titular: estadÃ­sticas tan detalladas como las de una comparadora (Wincomparator) en la ficha NBA, con CYBERCORE. Se copiaron solo los bloques calculables con datos reales (forma, cara a cara, clasificaciÃ³n y comparativa); alineaciones, estadio y cuotas por cuarto quedan fuera porque ninguna fuente validada los trae, y la web no los rellena. Decisiones de fondo: (1) cada partido se calcula Â«a la fechaÂ» (solo dÃ­as anteriores en hora del Este), para que un partido jugado no muestre su propio resultado; (2) las fuentes se unen por id y, si dos discrepan en un marcador, se descarta ese partido en vez de elegir uno; (3) el cÃ¡lculo vive en el mÃ³dulo NBA aislado y la API solo lee y valida el JSON pÃºblico, como con tenis, asÃ­ que no ve cohortes, modelos ni sellos ni toca predecir â†’ sellar â†’ publicar; (4) la clasificaciÃ³n no replica los desempates oficiales y lo dice. Rama `web/nba-estadisticas`, sin desplegar: falta el exportador del host. Ver `docs/nba_estadisticas_web_20261027.md`.

## 27-oct-2026 Â· Encabezado Ãºnico en Partidos

DecisiÃ³n del usuario: la vista Partidos (ventana Ãºnica) no puede tener una cabecera distinta a la del resto de la web. Se quitÃ³ el modo compacto de `window.css` (una fila de 56 px sin estado, sello ni iconos); ahora es la misma cabecera de dos filas de todas las rutas y la ventana toma su alto de la cabecera medida (`--site-header-h`, `ResizeObserver` en `app.js`). Aparte, `future.css` fija `.header-main{height:66px}` y anula el `height:auto` mÃ³vil de `styles.css`, asÃ­ que en â‰¤760 px el selector de deporte se sale de la cabecera en TODAS las rutas; las hojas originales estÃ¡n fijadas por hash, asÃ­ que solo se corrigiÃ³ dentro de la ventana Ãºnica (`.is-win`). Pendiente decidir si se corrige en el resto.

## 27-oct-2026 Â· RediseÃ±o de PronÃ³sticos (#picks)

DecisiÃ³n del usuario: la vista PronÃ³sticos se rediseÃ±a con el patrÃ³n de las webs de pronÃ³sticos (cifras arriba, destacado, barra de deporte/fecha, tarjetas con equipo, cuota y barra de probabilidad), solo con componentes de CYBERCORE. Las hojas originales siguen fijadas por hash: la disposiciÃ³n nueva vive en `window.css` bajo `.win-pk-*` (sin colores ni fuentes propios). La prueba Â«componentes visuales anterioresÂ» ahora exige las clases nuevas (`win-pk-card`, `cyber-card`, `cyber-tab`, `cyber-progress`). ImÃ¡genes: fÃºtbol usa los escudos propios (`/web/escudos`, vÃ­a la agenda); NBA y tenis no traen escudos ni fotos en sus datos y la polÃ­tica de contenido (`img-src 'self'`) no admite dominios externos, asÃ­ que muestran insignia con cÃ³digo de equipo o iniciales. Pendiente de decisiÃ³n: fotos de jugadores y logos NBA requieren descargarlos al servidor (licencia) y aÃ±adir `home_img`/`away_img` (ruta `/web/...`) al payload; la vista ya las muestra si llegan.

## 27-oct-2026 Â· ImÃ¡genes de NBA y tenis alojadas en el servidor

DecisiÃ³n del usuario: QuantFut es sin fines de lucro y las tarjetas de PronÃ³sticos muestran logos NBA y fotos de tenistas. Logos NBA: TheSportsDB (30/30, tamaÃ±o `/small`, clave gratuita; sus tÃ©rminos oficiales no se pudieron leer, la pÃ¡gina dio 502; solo se vio una copia de terceros, que pide mencionar la fuente). Fotos de tenis: Wikimedia Commons vÃ­a Wikidata (P18), solo CC BY, CC BY-SA, CC0 o dominio pÃºblico, reducidas a 320 px; cada una con autor, licencia y enlace en `frontend/imagenes/manifiesto.json` y en la pÃ¡gina `/web/imagenes/creditos`. Emparejamiento por QID curado en `scripts/imagenes/tenistas.json` (no por bÃºsqueda de nombre: TheSportsDB confundiÃ³ Â«Han ShiÂ» con otra persona); una foto cuyo nombre en Wikidata no coincide con el publicado se descarta. Berrettini queda sin foto: su licencia es Â«AttributionÂ» a secas. Los archivos viajan en el repo (`frontend/imagenes/`, ~4 MB) y por tanto en la imagen Docker; la web no enlaza a dominios externos (CSP `img-src 'self'`). Las marcas de la NBA y el derecho a la propia imagen de los jugadores no cambian por ser sin fines de lucro; la revisiÃ³n legal sigue pendiente. Mantenimiento: `python scripts/imagenes/descargar_imagenes.py faltan` lista tenistas publicados sin foto; se aÃ±aden a `tenistas.json` con su QID y se vuelve a ejecutar `tenis`.

## 27-oct-2026 Â· RediseÃ±o de Planes (#planes) y Paquetes (#paquetes)

PeticiÃ³n del usuario: las tarjetas de planes se cortaban y la pÃ¡gina debÃ­a convencer, con CYBERCORE. Causa de lo que no se veÃ­a: la etiqueta de cada plan (`plan-ribbon`) sobresalÃ­a de la tarjeta y el recorte de esquinas de `cyber-card` la cortaba; ademÃ¡s las tarjetas se apretaban a ~200 px junto al resumen del pedido. Ahora la etiqueta va dentro de la tarjeta, las tres tarjetas ocupan todo el ancho (en mÃ³vil el plan destacado va primero) y el botÃ³n de cada tarjeta lleva directo a crear cuenta o al pedido (`data-membership-buy`); el resumen queda solo en el paso de revisiÃ³n. PersuasiÃ³n sin trampas: precio por mes y por dÃ­a calculados del precio real del servidor, ahorro frente a meses sueltos, plan destacado por defecto, comienzo gratis, pasos claros, objeciones en las preguntas y un bloque de lo que NO se promete. No se inventÃ³ escasez, descuentos, testimonios ni cifras de rendimiento. El CSS nuevo va solo en `window.css` bajo `.win-plans*` porque `original-css.test.mjs` congela `styles.css`, `future.css`, `membership.css` y CYBERCORE y exige que `window.css` no use colores ni fuentes propios.

## 28-oct-2026 Â· Barrido de pendientes de DEPLOYS.md y PENDIENTES.md

PeticiÃ³n del usuario: leer las notas de DEPLOYS, resolver todo lo que quede y no dejar nada apuntado. MÃ©todo: cada pendiente se comprobÃ³ contra el servidor antes de tocarlo, porque la mayorÃ­a de las notas eran anteriores a despliegues ya hechos (CHAIN_GIT_REMOTE, Whop, Meta CAPI, #137/#138, reentrenamiento en el cron, API alineada): se cierran en DEPLOYS.md con la mediciÃ³n, no se repiten. Lo que sÃ­ faltaba y se hizo: `docker-compose.yml` con las imÃ¡genes que corren, `scripts/deploy.sh` con `construir`/`ensayo`/`desplegar`, `APP_DOWNLOAD_URL` en el servidor y la regla del `git worktree` por sesiÃ³n. DecisiÃ³n clave: el servidor no recibe clave de despliegue de GitHub; se despliega con `git archive` por SSH, porque guardar una credencial en el VPS ampliaba la superficie sin ganar nada sobre una receta ya probada. Lo que queda depende de ti (credenciales, trÃ¡mites legales y de tiendas, decisiones) o de una fecha/muestra (1-nov, puerta de CLV) y sigue en `PENDIENTES.md`; no se compraron crÃ©ditos ni se tocÃ³ el motor antes del 1-nov.

## 28-oct-2026 Â· RediseÃ±o de conversiÃ³n de #alta, #parley y #escalera (desplegado como parche)
DecisiÃ³n clave: la rama de trabajo original (`nba/v13-disponibilidad`) no incluÃ­a el frontend que corrÃ­a en producciÃ³n, asÃ­ que se desplegÃ³ un parche de cinco archivos sobre la imagen `planes-d788025` y esta rama parte de `main` (que ya tenÃ­a ese `app.js`) para que el repositorio vuelva a coincidir con producciÃ³n. Lo bloqueado se muestra con la cuota difuminada (decisiÃ³n del titular, 2026-10-18) y Cloudflare cachea 4 h por URL completa: cada estÃ¡tico modificado necesita un `?v=` nuevo.

## 27-oct-2026 Â· Logos de NBA en la ventana Ãºnica (rama `web/logos-ventana-nba`, sin desplegar)
DecisiÃ³n clave: los logos NBA ya estaban en producciÃ³n (`/web/imagenes/nba/*.png` y el manifiesto devuelven 200) pero la ventana de NBA y tenis
(`sports-window.js`) pintaba siempre iniciales: solo las tarjetas de `ergonomic-views.js` consultaban el manifiesto. Ahora `mark()` usa el logo cuando
el manifiesto ya cargÃ³ y, si no, las iniciales (nunca una imagen rota). La tabla nombreâ†’cÃ³digo se moviÃ³ a `nbaCode()` en `sports-data.js` para tener una
sola fuente; se pasa por contexto desde `app.js`. Pendiente: las fotos de tenis en la ventana siguen con iniciales (llevan crÃ©dito de licencia).

## 28-oct-2026 Â· Tenis: resultados y mercados Â«pendientesÂ» (rama `tenis/resultados-horarios`, sin desplegar)
DecisiÃ³n clave: el Â«PendienteÂ» de tenis tenÃ­a dos causas independientes. (1) La proyecciÃ³n pÃºblica (`tenis_publico.py`) solo liquidaba el ganador: los otros mercados del partido (juegos, sets, hÃ¡ndicaps, ganador de set, tie-break) tenÃ­an `outcome=None` para siempre, aunque el partido hubiera terminado (3.100 mercados de 142 partidos terminados en el feed del 28-oct). Ahora se liquidan con las reglas de `tennis_markets_v2/settlement.py` portadas sin importar el motor (marcador por sets de API-Tennis; retiro devuelve lo no jugado y el tie-break de un retiro queda abierto; walkover y cancelado se devuelven; un marcador que no se pueda verificar deja el mercado abierto en vez de adivinar). (2) El calendario con resultados solo se pedÃ­a a las 00 y 12 UTC: un partido terminado a las 13:00 no cerraba hasta las 00:25. Ahora las pasadas horarias piden ayer y hoy solo para el circuito con un partido que ya deberÃ­a haber terminado (`--results-refresh`, ~2 h por circuito; tope local 26/dÃ­a). El proveedor tiene plan y cuota sin verificar: el tope es local. AdemÃ¡s la proyecciÃ³n usa el inicio vigente del proveedor (un aplazado vuelve a Â«programadoÂ» con su hora nueva), marca `cancelled` y marca `no_result` tras 36 h sin estado final (p. ej. Bublikâ€“Marozsan y Kudermetovaâ€“Ibragimova, atascados en Â«Set 1Â»).

## 28-oct-2026 Â· Reto escalera: 2 escalones en 7 dÃ­as, con NBA y tenis conectados
DecisiÃ³n del titular: el reto entero al 80 %, buscando el acierto y no la cuota, con hasta 7 dÃ­as, varios escalones un dÃ­a, y Â«conÃ©ctalosÂ» (NBA y tenis). Medido en `eval/escalera_multideporte.py` (Tennis-Data con Pinnacle, BetsAPI para NBA): lo decisivo no son los fallos sino quedarse sin segundo escalÃ³n dentro del plazo; con solo fÃºtbol expira la mitad y con tenis el reto se cumple el 85,9 %. 3 escalones expiran uno de cada cuatro; una Â«meta de cobroÂ» (coste âˆ’ln p / ln cuota, apuesta audaz de Dubins y Savage) no mejorÃ³ a 2 escalones con presupuesto; el mÃ¡s probable mide algo mejor que el de mÃ¡s valor. NBA y tenis entran desde el archivo PropLine (sin peticiones nuevas, CLAUDE.md) con Pinnacle sin margen como en el estudio; sin Pinnacle el partido no entra para no cambiar de referencia en silencio. Se liquidan con la calificaciÃ³n de PropLine de la casa del escalÃ³n porque cada casa aplica su regla de retiradas en tenis. `escalera_resultados` pierde la exigencia de marcador SOLO para `fuente = 'propline'` (el fÃºtbol la mantiene); los triggers de inmutabilidad no se tocan. El escalÃ³n gratis de la app pasa a 75-97 % (con 75-90 % casi no habrÃ­a gratis). Trabajo hecho sobre `origin/main` en la rama `escalera/reto-7-dias-multideporte`: la copia local `nba/v13-disponibilidad` iba 276 commits por detrÃ¡s.


## 28-oct-2026 Â· CÃ³rners y tarjetas: la primera fuente que los tenga, FotMob o SofaScore
Medido en producciÃ³n a las 23:03 UTC: los 5 partidos de Serie A del 28-oct estaban `finished` con marcador y sin cÃ³rners, tarjetas ni tiros, y sus fichas de mercado seguÃ­an en Â«PendienteÂ», aunque la pÃ¡gina posterior de FotMob ya estaba guardada (Veneziaâ€“Inter: cÃ³rners 3â€“6, amarillas 0â€“2, rojas 0â€“0). Causa: `fotmob_captura.completar` esperaba 36 h tras el saque y corrÃ­a una vez al dÃ­a (09:15), para dejar a SofaScore (mediana 12 h, mÃ¡ximo 33 h) la oportunidad de ser la fuente principal. DecisiÃ³n del titular: usar FotMob cuando falte SofaScore y viceversa. SofaScore ya rellenaba cada columna con `COALESCE`, asÃ­ que ese sentido no cambia. Nuevo `completar_estadisticas`: con la primera pÃ¡gina posterior rellena solo estadÃ­sticas (NULL y marcador coincidente), sin esperar; se ejecuta dentro de la acciÃ³n `completar`, que pasa a correr cada hora (:50, tras `posteriores` a :35). El xG NO entra en ese paso: conserva la regla vigente de `completar` (pÃ¡gina tomada â‰¥ `XG_MIN_HORAS` = 20 h tras el saque y partido de mÃ¡s de 36 h), porque SofaScore sigue siendo su fuente principal y `xg_source` admite una sola pareja. Primera fuente gana: si FotMob escribe antes, SofaScore no pisa el valor (los totales deben coincidir). La base de esta rama es la que corre el worker, no `4907a0d`: `4907a0d` + el parche de contenedor de la rama `deploys/auditoria-api-20261028` (`estadisticas.py`, `sofascore_partidos.py`, `fotmob_captura.py`), comprobado por hashes (168 archivos idÃ©nticos); recrear el worker desde la imagen `quantfut-worker:4907a0d` habrÃ­a perdido ese parche.
## 31-oct-2026 Â· Cuotas en NBA y tenis: overlay fuera del sello, mejor cuota no DFS, Â«â€”Â» sin fuente
Los feeds de NBA y tenis llevaban pronÃ³sticos sin precios. DecisiÃ³n del titular: mostrar la mejor cuota de cualquier casa no DFS de la observaciÃ³n que se usÃ³ al sellar (con casa y hora) y Â«â€”Â» donde no hay fuente (tie-break de tenis, filas NBA con umbral estadÃ­stico, hÃ¡ndicap NBA, partidos de tenis sin emparejar); nunca cuota justa ni inventada. Por quÃ© como overlay del servidor y no dentro del sello: sellar el precio es un cambio de protocolo de los productores y esto no debe mover hashes; el overlay lee la observaciÃ³n ya sellada (`sha256`/`received_at_utc` en NBA, `market_board` en tenis) y el cliente descarta cualquier cuota con `as_of` posterior al sellado o de otra cohorte. Cobertura medida en el reconocimiento: NBA ganador 41/44, total 40/44, props con lÃ­nea ~85-94 %; tenis ganador 53/63, juegos totales 425/567, tie-break 0/63. Pendiente: medir con datos reales tras desplegar y revisar tÃ©rminos de PropLine. No se desplegÃ³ nada.

## 28-oct-2026 Â· AuditorÃ­a de consumo de APIs: dos errores y un ahorro
Medido en producciÃ³n (`docs/auditoria_consumo_apis_20261028.md`). Lo que importa de la decisiÃ³n: (1) el recolector SofaScore llevaba tres dÃ­as sin pedir detalles de partidos porque las listas se comÃ­an el tope de la corrida; ahora las listas reservan la mitad para los detalles, los detalles se piden aunque las listas se corten, el gasto diario se reparte hasta el fin del ciclo de Apify y 1 USD del tope mensual queda para las alineaciones (lo que lee `sello_tardio`); con el tope en 15 USD la cuenta ya lleva 13,2 y no queda margen para listas hasta el 24-nov: es decisiÃ³n del titular subirlo (lÃ­mite de la cuenta 19). (2) Dos alias de PropLine (Racing de Santander, Tromsoe) dejaban partidos sin cuotas. (3) En PropLine el fÃºtbol era el 70 % de las llamadas por pedir cÃ³rners, tarjetas y jugadores cada hora en ligas sin partido cercano; ahora solo cada hora con partido en 48 h y cada 6 h si no, y se dejan de archivar los futuros (nadie los lee). La primera peticiÃ³n de cada liga, que es la que leen los motores, no cambia. Lo que no se tocÃ³ a propÃ³sito: lotes de 13 mercados (la NBA dio 504 con lotes grandes), cadencia de `live` y `results` (FotMob y PropLine ya sin errores), y `Deportivo` (no existe en `teams`; darlo de alta es decisiÃ³n de datos).

## 28-oct-2026 Â· FotMob como fuente del xG de partidos terminados y respaldo por ZenRows
Comparado en producciÃ³n (105 partidos con xG de SofaScore y pÃ¡gina posterior de FotMob): 94 idÃ©nticos a 2 decimales, mediana de diferencia 0,000. Los 11 distintos no son un error de una fuente: el xG se corrige DESPUÃ‰S del partido. Repetido hoy en SofaScore, Palmeirasâ€“Bragantino pasÃ³ de 3,35â€“0,42 (guardado a +4,9 h) a 3,82â€“0,54, igual que FotMob a +17,7 h; Houstonâ€“Minnesota (0-0) estaba guardado como 0,00â€“0,03 y hoy da 0,81â€“1,38 (FotMob 0,74â€“1,34). Consecuencia: la regla Â«primera pareja congeladaÂ» fija un valor provisional en ~10 % de los partidos si se toma antes de ~20 h; pendiente decidir una hora mÃ­nima de captura. DecisiÃ³n del titular: con un bloqueo 401/403 de FotMob se usan los proxy de ZenRows (tope diario de crÃ©ditos); un 429 sigue siendo pausa de 12 h porque es un lÃ­mite de ritmo. El docstring de `fotmob_captura.py` ("no se evitan controles de acceso") queda sustituido por esa regla.

## 28-oct-2026 Â· Hora mÃ­nima de captura del xG (20 h)
DecisiÃ³n del titular tras comparar FotMob con SofaScore: el xG se corrige despuÃ©s del partido, asÃ­ que no se guarda antes de 20 h desde el saque (`estadisticas.XG_MIN_HORAS`, configurable). SofaScore deja el xG vacÃ­o si su detalle llega antes (el resto de columnas se rellena igual) y FotMob lo completa con la primera pÃ¡gina tomada pasada la hora mÃ­nima; `refrescar_xg` pide esa pÃ¡gina a los partidos que solo tenÃ­an una temprana. Por quÃ©: la primera pareja vÃ¡lida se congela como dato point-in-time y un valor provisional queda fijo para el entrenamiento. Lo que no se hizo a propÃ³sito: reescribir los xG ya guardados (los ~11 de 105 con diferencia > 0,05 en los Ãºltimos 14 dÃ­as): tocar histÃ³rico que usa el entrenamiento del 1-nov es decisiÃ³n aparte.

## 28-oct-2026 Â· xG corregido aparte (`xg_corregido`) en vez de reescribir `matches`
375 partidos (12-26 oct) tenÃ­an el xG guardado antes de 20 h; con la primera pÃ¡gina de FotMob pasadas 20 h: SofaScore sube de media 0,157 xG por partido (37 suben, 8 bajan; mediana de diferencia 0,000 pero cola larga: 21 partidos > 0,25), es decir, su lectura temprana subestima; API-Football (retirada el 22-oct) difiere 0,218 de media y no tiene sesgo claro (105 suben, 137 bajan: otro proveedor, no solo otra hora). Por quÃ© aparte: el xG guardado es un dato con fecha que usa el entrenamiento y reescribirlo cambia lo que el modelo Â«sabÃ­aÂ». Pendiente del titular: entrenar con ambos y medir si cambia algo (el reentrenamiento del 1-nov usa lo guardado).

## 28-oct-2026 Â· MediciÃ³n: Â¿importa entrenar con `xg_corregido`? No de forma apreciable
`scripts/entrenamiento_local/mediciones/xg_corregido.py` (local, con un volcado de producciÃ³n de solo lectura; no toca modelos activos ni el reentrenamiento del 1-nov). Solo 259 de los 375 partidos corregidos estÃ¡n en el conjunto de entrenamiento (el resto son de ligas sin modelo): 0,5 % de 49.560 partidos. A) Calidad del dato: el xG corregido no explica mejor los goles que el original (log-verosimilitud de Poisson âˆ’1,3983 frente a âˆ’1,3978; IC95 de la diferencia [âˆ’0,018, +0,020]; en los 42 de FotMob +0,019, IC [âˆ’0,018, +0,055]). B) Sensibilidad: dos ajustes de Dixon-Coles con los parÃ¡metros de producciÃ³n cambian P(1X2) de los 143 partidos prÃ³ximos en 0,24 pp de media (mÃ¡ximo 1,45 pp) y los goles esperados en 0,013. C) Fuera de muestra: solo 10 partidos terminados desde el 27-oct, sin potencia (RPS 0,19044 â†’ 0,18745, IC [âˆ’0,008, +0,003]). ConclusiÃ³n: con tan pocos partidos y tanto ruido de goles, ni el dato ni el modelo permiten distinguir una versiÃ³n de otra; el valor de la hora mÃ­nima de 20 h estÃ¡ en los datos nuevos que lleguen, no en reentrenar lo viejo. `xg_corregido` se conserva como auditorÃ­a; no hay motivo para cambiar el reentrenamiento del 1-nov.

- 2026-10-31 Â· Respaldo de cuotas automÃ¡tico (`cuotas_respaldo --auto`, `CUOTAS_RESPALDO_AUTO`, apagado por defecto): el sellado de NBA/tenis ocurre en contenedores aparte (apps/), sin importar `qf`, asÃ­ que el gancho es un cron del worker con `flock`, fuera del camino crÃ­tico; solo hay peticiones si existe un hueco sellado sin cuota de PropLine. Gasto diario persistido junto a la cachÃ© para que las pasadas no superen el tope; `auto()` nunca lanza.

## 31-oct-2026 Â· Apify se sustituye sin pagar: FotMob primero, SportsAPIPro para los huecos
El titular no vuelve a pagar Apify; desde las 19:40 UTC del 31-oct la cuenta (tope de 5 USD del plan gratuito, 18,04 gastados) devuelve 403 a cada corrida. Inventario real: de todo lo que capturaba, solo el once y las bajas de fÃºtbol tienen consumidor (`sofascore_alineaciones` â†’ `lineups`, `lineups_previstas`, `injuries`); el xG ya venÃ­a de FotMob en el 100 % desde el 28-oct, y los datos de NBA y tenis de Apify no los lee ningÃºn motor (NBA: PropLine, ESPN, stats.nba.com; tenis: API-Tennis, PropLine). `sello_tardio` ya aceptaba el once `standard` de FotMob y sella a T-25 sin once, asÃ­ que sellar no se bloquea.
Por quÃ© FotMob y no otra API: medido sobre 173 partidos (25-31 oct), FotMob tiene el once oficial antes del saque en el 81 % (SofaScore 86 %, juntos 93 %) y bajas en el 97 % (SofaScore 87 %), sin peticiones nuevas. SportsAPIPro devuelve SofaScore con los mismos ids (`confirmed`, `missingPlayers`), asÃ­ que rellena los huecos sin romper la historia de `availability`, con unas 10-20 de sus 100 peticiones diarias. Descartadas: Live Tennis API (terminados de pago), TheSportsDB gratis (recorta resultados), ESPN (sin ids de SofaScore). Detalle y presupuesto: `docs/plan_sustituir_apify_20261031.md`.
API-Tennis tambiÃ©n se sustituye (su plan vence): el motor de tenis le pide solo `get_fixtures` (â‰¤26/dÃ­a) y la web de estadÃ­sticas ~121 llamadas/dÃ­a (rankings, perfiles, H2H). SportsAPIPro tenis da calendario, sets, `winnerCode`, ranking, paÃ­s, superficie y rankings completos; no tiene H2H de tenis, que se calcula del archivo propio. Lo crÃ­tico son los ids de jugador: se construye la tabla `player_key` â†” id SofaScore mientras API-Tennis siga respondiendo (prueba 30-oct: 16/16 emparejados, ganador igual 8/8).
## 2026-11-01 â€” Respaldo football-data.org (rama `futbol/fdorg-respaldo`, desplegada el 1-nov)
- DecisiÃ³n: football-data.org es un **testigo** de calendario y resultados, no una fuente dueÃ±a: compara contra `matches` y avisa; no escribe ni crea equipos. Reutiliza `compare()`/`promote()` de `pitchapi_respaldo` por adaptador, sin tocar cÃ³digo desplegado. Tablas `fdorg_*` propias (db/092; 085-088 quedan para `futbol/base-unica`).
- DecisiÃ³n: prÃ³rroga y penales no se comparan (la convenciÃ³n de goles puede diferir); el pendiente exige 6 h desde el saque porque el plan gratis puede reflejar marcadores con retraso (no verificado).
- Verificado: 30 pruebas (nuevas + PitchAPI) y una pasada completa en esquema aislado de Postgres local (migraciÃ³n idempotente, sin duplicar abiertas, sin tocar `matches`, 401 avisa una vez). DiseÃ±o: `docs/superpowers/specs/2026-11-01-football-data-org-respaldo-design.md`.
- Pendiente: tÃ©rminos del plan gratuito; clave en el `.env` del VPS; (db/092 y activaciÃ³n ya hechas en el despliegue del 1-nov); fase 2 (rellenar resultados) y panel solo si el titular lo decide.

## 2026-11-01 â€” Tabla Ãºnica de fÃºtbol `futbol.dato`
DecisiÃ³n clave: el titular pidiÃ³ UNA sola tabla para todo lo que capturen las APIs, los servicios y los scrapers, y que solo ella alimente al motor; mi primer diseÃ±o dejÃ³ nueve tablas por tipo y no lo cumplÃ­a. `futbol.dato` es una tabla esparcida: una fila por hecho, columnas tipadas con nombre unificado y compartidas entre tipos, clave primaria que impide repetidos, una fuente por tipo y partido (prioridad en `futbol.prioridad_entidad`) y un id de jugador Ãºnico (el de SofaScore, negativo si no hay pareja). Los adaptadores son funciones SQL (FotMob, clima ERA5, estadio/altitud) y el cargador del archivo de SofaScore. Quedan fuera `matches` (registro del partido) y `odds_snapshots` (inmutable por trigger y base de la cadena de hashes: moverla exige quitar garantÃ­as, solo con confirmaciÃ³n explÃ­cita). Aplicada en producciÃ³n con respaldo y ensayo con ROLLBACK; 1,6 millones de filas, 0 repetidos. La rama anterior estaba 764 archivos detrÃ¡s de `origin/main` (otra sesiÃ³n retirÃ³ API-Football y otras fuentes): se rehÃ­zo sobre `origin/main` con migraciones 094-095.
## 2026-11-01 â€” La tabla Ãºnica cubre el partido completo del scraper de SofaScore
DecisiÃ³n clave: medido con un partido real, la tabla guardaba solo lo esencial y, peor, con una fuente dueÃ±a por tipo los datos de SofaScore no llegaban donde FotMob ya cubrÃ­a el partido. Se ampliÃ³ a las 82 estadÃ­sticas de jugador, las 46 de equipo por periodo, los campos de tiro e incidencia, la asistencia, el momentum y las posiciones medias, y SofaScore pasÃ³ a COMPLETAR las columnas vacÃ­as de la fila de FotMob (anotado en `fuente_extra`) sin tocar `nota`, `valor_mercado` ni `posicion_id`, que son entradas del motor con el sentido de cada fuente. Quedan fuera solo h2h, forma previa y rachas (no verificables como previos) y best_players/player_ranking (derivados). El orden de la pasada diaria importa: FotMob reescribe sus filas y SofaScore debe volver a completarlas despuÃ©s. 2,8 millones de filas, 0 repetidos.

## 2026-11-01 â€” RediseÃ±o de los motores sobre `futbol.dato`: ligas del nÃºcleo y datos frente a los estudios
DecisiÃ³n clave: mientras el titular descarga el resto, el rediseÃ±o se construye y se activa solo con las 8 ligas que tienen tiros con xG, estadÃ­sticas por mitad e incidencias completas (Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, BrasileirÃ£o; Premier y LaLiga desde 24/25); con Serie A sola no hay potencia. Al cruzar columna por columna lo que piden los estudios aparecieron dos huecos del cargador que ninguna prueba veÃ­a: se descartaban cÃ³rners, tiros, xG y tarjetas por mitad (Â«ya estÃ¡n en `matches`Â», que solo tiene el total) y no se guardaba quiÃ©n arbitra (solo su trayectoria, que ademÃ¡s es posterior al partido). Retiro de tablas: solo lo derivado de un original conservado o sin lectores; `historical_football_player_stats` aÃºn alimenta `cargar_fotmob`, asÃ­ que primero hay que impedir que una recarga pise con NULL.

## 2026-11-01 â€” Umbrales de sanciÃ³n, derbis y fase 2 en `futbol.dato`
DecisiÃ³n clave: los umbrales de amarillas se miden con nuestros datos (moda de lo acumulado antes de cada sanciÃ³n) y se guardan sin verificar, en vez de escribirlos de memoria: la mediciÃ³n confirma 5 en cinco ligas y 3 en Brasil, y delata que la Premier (por jornada), la Liga MX y Ligue 1 no tienen una regla fija. La regla automÃ¡tica de derbis solo vale con dos clubes en la ciudad, porque Â«misma ciudadÂ» en Londres daba 15 derbis; las grandes ciudades van a una lista manual resuelta por nombre. La fase 2 conserva cada captura previa con su hora real y no aplica Â«una fuente por tipoÂ»: el motor necesita lo Ãºltimo sabido por fuente a T-60, no la mejor fuente del partido.

## 2026-11-01 â€” Retiro de tablas de origen redundantes (R1â€“R3) y despliegue de db/097â€“100
DecisiÃ³n clave: solo se borrÃ³ lo que ya vive en `futbol.dato` o se regenera desde un original conservado, y siempre tras un respaldo con recuento y sha256 y una copia local verificada. `historical_football_player_stats` no era un duplicado Â«seguroÂ» a ciegas (la vista que alimenta `cargar_fotmob` la une), asÃ­ que se borraron solo las filas de partidos ya cargados y de mÃ¡s de 14 dÃ­as, y una prueba demuestra que recargar FotMob sin ellas no vacÃ­a nada. `af_odds_snapshots` y `sofascore_detalles` eran inmutables pero sin lectores; el `DROP` va sin CASCADE para que falle si algo dependiera de ellas. El borrado de datos lo bloqueÃ³ el permiso hasta que el titular lo autorizÃ³ en el chat; una orden de otra sesiÃ³n no cuenta como autorizaciÃ³n.

## 2026-11-01 â€” RediseÃ±o de fÃºtbol desde cero con `futbol.dato` (rama `futbol/rediseno-f2`, nada activado)
DecisiÃ³n clave: todo se volviÃ³ a medir sobre la tabla Ãºnica (8 ligas, walk-forward semanal, mismas filas, log-loss y Murphy) en vez de fiarse de lo medido en Serie A el 31-oct, y cada estudio que pasÃ³ el titular se leyÃ³ entero y se puso a prueba en vez de aceptar el resumen que lo acompaÃ±aba. Varios resÃºmenes decÃ­an lo contrario que el texto (HIGFormer no mejora empates, DEFCON desaconseja contar acciones defensivas, KellyBench muestra que todos pierden, TabNet quedÃ³ por debajo de CatBoost, Chen no compara con y sin Poisson). El resultado medido manda: el mercado gana a todo en 1X2 y el modelo no aporta nada en la mezcla (peso 0); el score-driven con xG empata con Dixon-Coles; el apilado con Ã¡rboles empeora; donde sÃ­ hay valor es en el motor C (tarjetas con Ã¡rbitro/derbi/igualdad, cÃ³rners de Yip) y, pendiente, en lo previo al partido (once y bajas con hora de captura). Kelly sin ventaja solo frena la ruina: no se convierte en producto.

## 2026-11-01 â€” El objetivo es el acierto del pronÃ³stico mÃ¡s probable, no batir al mercado
DecisiÃ³n clave: el titular aclarÃ³ que ganar a las cuotas de cierre no es la meta (el mercado es mÃ¡s rÃ¡pido y tiene mejores datos); la meta es publicar el pronÃ³stico con mayor probabilidad de acertar y que el porcentaje anunciado sea cierto. Por eso el mercado sin margen pasa a ser una fuente mÃ¡s (la mÃ¡s honesta medida) y la mÃ©trica pasa a ser acierto del 5â€“10 % mÃ¡s probable de cada dÃ­a mÃ¡s diferencia anunciado-observado, por familia. Resultado: techo â‰ˆ 91 % en doble oportunidad, â‰ˆ 73 % en 1X2, â‰ˆ 69 % en goles, cÃ³rners y tarjetas, sin fuente claramente mejor; el apilado y la logÃ­stica prometen de mÃ¡s; y la cuota mÃ­nima de 1,40 de la app choca con la mÃ¡xima probabilidad (1X2 baja a â‰ˆ 59 %). Pendiente de decisiÃ³n del titular.

## 30-oct-2026 Â· PronÃ³sticos: la tarjeta de fÃºtbol enseÃ±a el destacado del partido
DecisiÃ³n del titular: el bloque Â«PronÃ³sticoÂ» de cada tarjeta de #picks debe ser el pronÃ³stico destacado, no el pick sellado de alta probabilidad (que sale a cuotas de 1,02-1,07). La tarjeta pide la ficha del partido (`ensureMatch`, misma cachÃ© que el detalle) y toma `mercados.destacado`, asÃ­ que tarjeta y ficha no pueden discrepar; con cuota del modelo se rotula Â«Cuota del modeloÂ» y sin sello propio no se enseÃ±a el bloque de registro. Mientras se consulta sale Â«Consultandoâ€¦Â» (no el pick sellado, para que no cambie de selecciÃ³n al llegar); si la consulta falla o el partido no tiene destacado, se mantiene el pick sellado (decisiÃ³n del titular). Solo frontend (`ergonomic-views.js`, repintado agrupado en `app.js`), sin cambios en la API. Base: `docs/deploy-historial-desde-26`; producciÃ³n ademÃ¡s lleva variantes Â«sin-leyendasÂ» de `app.js`/`sports-window.js`/`conversion-views.js` que no estÃ¡n en ninguna rama: al desplegar, aplicar el parche sobre esos archivos en vivo, no copiar `app.js` de esta rama. Desplegado el 30-oct (`quantfut-api-destacado-tarjeta:3bb42c1`), anotado en DEPLOYS.md.

## 4-nov-2026 Â· NBA: mÃ­nimo de 1,20 en Partido y tarjetas de jugador
DecisiÃ³n clave: el mÃ­nimo de 1,20 se aplica solo a la lista de Partido, no al destacado, que conserva 1,40: el destacado ya tiene su propia regla y filtrarlo con 1,20 cambiarÃ­a quÃ© se publica. Los mercados de jugador se agrupan por jugador con su foto oficial (nunca el id interno) y las lÃ­neas se pliegan; en 390 px la tabla plana era ilegible. La identidad de la foto sale de `nba.entidad`/`nba_oficial` y, si no es Ãºnica, queda nula a propÃ³sito: una foto equivocada es peor que las iniciales. Desplegado en `nba-api:tarjetas-f11d97c7` y `quantfut-api-nba-tarjetas:f11d97c7`, verificado a 390 px y 851 px. Sigue abierto, ajeno a esta tarea, renovar el artefacto del motor antes del 7-nov.

## 2026-11-05 â€” #historial: la grÃ¡fica grande mide aciertos reales frente a esperados, no unidades

Motivo: la curva de beneficio (1 u por pronÃ³stico, cuota media 1,20) mostraba âˆ’6,98 u en 532
pronÃ³sticos con 83 % de acierto frente al 82 % prometido. No es un fallo del modelo: a cuota 1,20 el
punto de equilibrio es 83,3 % y el margen de la casa se come el resto (mismo resultado que la mediciÃ³n
del 5-oct: favoritos â‰¥ 80 % â†’ ROI âˆ’2,4 %). El producto promete probabilidad calibrada, y eso es lo que
ahora mide la grÃ¡fica: suma acumulada de (acierto âˆ’ probabilidad publicada) con franja de azar al 95 %
(`desvio()` en `frontend/historial-views.js`; vale tambiÃ©n para NBA y tenis porque usa la probabilidad,
no la cuota).

LÃ­mite que se mantiene a propÃ³sito: el beneficio NO se esconde. Sigue el indicador Â«Beneficio Â· 1 u por
pronÃ³sticoÂ» y la frase bajo la grÃ¡fica lo dice con su signo (Â«Acertar lo prometido no es ganar dineroâ€¦Â»).
Un test lo exige (`la grÃ¡fica grande mide aciertos frente a esperados y el beneficio sigue a la vista`).
No cambiar de mercado, ventana o mÃ©trica para que el resultado salga positivo: rompe la credibilidad de
la cadena de hashes y es publicidad engaÃ±osa. Cambiar la mÃ©trica es vÃ¡lido solo si la pÃ©rdida sigue a la
vista. Base: `main` (rama `web/historial-desvio`); ids de cachÃ© subidos a
`hist-desvio-20261105` en toda la cadena de imports. Sin desplegar ni confirmar visualmente en navegador.

## 2026-11-05 â€” #historial: cuota con su casa en cada fila, 7 dÃ­as, sin leyendas (decisiÃ³n del titular)

Pedido del titular: (1) cada resultado enseÃ±a la cuota y, debajo, de quÃ© casa es, en todos los deportes;
(2) Â«Acierto por dÃ­aÂ» y la tarjeta nueva miran solo los Ãºltimos 7 dÃ­as (`DIAS_GRAFICA = 7`);
(3) fuera las dos leyendas de la grÃ¡fica grande (explicaciÃ³n y Â«Hoy: +9,7 aciertosâ€¦ beneficio âˆ’6,98 uÂ»);
(4) la tarjeta Â«Beneficio Â· 1 u por pronÃ³sticoÂ» se sustituye por Â«DÃ­as en verde Â· Ãºltima semanaÂ»
(dÃ­as con mÃ¡s aciertos que fallos; cuenta real, no una mÃ©trica elegida a medida).

Esto sustituye el lÃ­mite de la entrada anterior (Â«el beneficio NO se escondeÂ»): lo decide el titular.
Lo que queda a la vista: la pregunta frecuente Â«Â¿ganarÃ© dinero seguro?Â» sigue diciendo el beneficio con
su signo, y `beneficio()` sigue calculÃ¡ndose y probÃ¡ndose (la cuota de referencia de tenis nunca entra).

Casa por deporte: NBA ya viene con casa (`book` â†’ `marketQuote`). FÃºtbol: `/mobile/v1/markets/history`
no devolvÃ­a `ref_book` (las filas de Alta probabilidad salÃ­an Â«Casa no registradaÂ»); ahora lo devuelve con
`nombre_casa()` (cambio en `src/qf/api/mobile.py`, **requiere desplegar la API**). Tenis: el servidor
publica `price: None`; sin cuota de casa sale Â«â‰ˆ justa del modelo Â· Modelo Â· sin casaÂ», no se inventa casa.
La rama `web/tenis-cuota-referencia` (c965e096) ya trae la cuota de referencia de PropLine para tenis
(`price_book`); el frontend la entiende (`ref` + `book`) pero ese servidor no estÃ¡ desplegado.
Ids de cachÃ©: `hist-casa-20261105`. Verificado en local contra producciÃ³n; sin desplegar.

## 2026-11-05 â€” DÃ­as ya jugados: pronÃ³stico sin VIP y mercados ordenados (decisiÃ³n del titular)

Regla 1 â€” sin candado pasado el dÃ­a: cuando termina el dÃ­a (hora de MÃ©xico, UTC-6 fijo: `ventana.dia_cerrado`)
en que se juega un partido, `GET /mobile/v1/matches/{id}` lo trata como `plus` (mercados, marcadores, picks de
Alta probabilidad y escalera del partido, todos abiertos), con o sin suscripciÃ³n. Hoy y maÃ±ana siguen igual.
Se eligiÃ³ MÃ©xico porque ya es el reloj del pronÃ³stico diario (`ventana.py`); un visitante de otra zona verÃ¡
abrirse los partidos de su noche a la medianoche de MÃ©xico. El cambio vale tambiÃ©n para la app mÃ³vil (mismo
endpoint). NBA y tenis no tienen candado en la web actual: no hubo nada que abrir. **Requiere desplegar la API.**
La lista `alta_probabilidad.vip` de `/mobile/v1/home` no se toca (solo trae partidos por empezar).

Regla 2 â€” orden en un partido ya liquidado (fÃºtbol, NBA y tenis; `ordenLiquidado` en `sports-data.js`):
acertados de mayor a menor cuota, luego lo sin resultado (devoluciÃ³n, anulado) y al final los fallados, tambiÃ©n
de mayor a menor cuota. Si el partido no tiene nada liquidado (o fue una retirada, todo Â«devoluciÃ³nÂ») queda el
orden por probabilidad de siempre. En NBA el texto Â«De mayor a menor probabilidadÂ» cambia a Â«Acertados primero,
de mayor a menor cuotaÂ». En tenis la cuota que ordena es la del modelo (no hay cuota de casa publicada).
Verificado en local contra producciÃ³n (fÃºtbol y NBA de ayer); los candados del fÃºtbol solo desaparecen al
desplegar la API. Ids de cachÃ©: `hist-casa-20261105`.

## 2026-11-05 â€” Tenis: la web lee la cuota PropLine de `/web/deportes/tenis/cuotas` (decisiÃ³n del titular)

Por quÃ©: el historial decÃ­a Â«Modelo Â· sin casaÂ» en todo el tenis porque `/web/deportes/tenis` trae `price: None`, pero la
cuota ya se calculaba en producciÃ³n aparte (`cuotas_tenis.py` + `cuotas_web.py`, usada solo por la app mÃ³vil). La rama
`web/tenis-cuota-referencia` (sidecar `tennis_cuotas.json`) quedÃ³ superada y no se despliega.

CÃ³mo: `ensureSport('tenis')` pinta primero el tenis y pide las cuotas DESPUÃ‰S (`loadTennisQuotes`); en frÃ­o el endpoint tarda
hasta ~100 s y mientras responde `unavailable`, asÃ­ que se reintenta dos veces cada 20 s y, si falla, queda la cuota justa del
modelo sin error visible. `applyTennisQuotes` pone `price`, `book`, `price_book` y `reference` solo si hay precio > 1 y casa con
nombre, y nunca pisa un precio que ya trajera el feed. Es una REFERENCIA (la mejor casa antes del sello, fuera del sello): se rotula
Â«Cuota de referenciaÂ» / Â«Casa Â· referenciaÂ» y `beneficio()` la excluye (marca `ref`). Efecto lateral buscado: la ventana de tenis y su
destacado muestran esa cuota y casa en vez de Â«Del modeloÂ».

Cobertura medida (5-nov): 132 de 143 eventos con cuotas; 67 de 102 destacados liquidados con cuota en su mercado. Los huecos son
hÃ¡ndicap de juegos (23), hÃ¡ndicap de sets (3) y juegos totales (2): el servidor exige la lÃ­nea exacta y no usa la mÃ¡s cercana, y esas
filas siguen con Â«Modelo Â· sin casaÂ». Ids de cachÃ©: `tenis-cuota-20261105` (app, real-views, ergonomic-views, sports-data, sports-window).
Verificado en local contra producciÃ³n; sin desplegar.

## 2026-11-05 Â· Mercados de la app: NBA y tenis con el diseÃ±o de fÃºtbol (rama app/mercados-todos-deportes)

- DecisiÃ³n: las piezas de la pestaÃ±a Mercados (radar, tarjeta de familia, tarjeta de pronÃ³stico con escudos/logos/fotos, cuota y casa, marco Hoy/Anteriores) viven en `market_hub.dart` y las usan los tres deportes.
- Hallazgo: la app NBA solo leÃ­a `/nba/v1/cartelera` (Ãºnicamente Â«GanadorÂ»); los otros 7 mercados con cuota y casa estaban en `/nba/v1/partido/{id}/mercados` y no llegaban. Ahora `enrichNbaFeed` los pide por partido (6 en paralelo, sin bloquear la pantalla) y la cuota del overlay v1 (cohorte vieja) ya no se usa en NBA.
- Regla de Â«pronÃ³stico publicadoÂ» en NBA/tenis: sellado antes del inicio, un solo lado por lÃ­nea y probabilidad 60â€“95 % (la banda del radar del servidor); el ganador queda exento.
- API (aditivo, SIN desplegar): `local_escudo`/`visitante_escudo` en `proximos` e historial de fÃºtbol. La app funciona sin ellas (agenda o iniciales). Desplegar segÃºn DEPLOYS.md.
- Regla de publicaciÃ³n en el servidor (NBA/tenis, cuota â‰¥ 1,20), app obediente; ver docs/regla_publicacion_20261105.md. Sin desplegar.


**5-nov-2026 â€” Historial web/Flutter y vacÃ­os por mercado.** La web cuenta Alta + Destacados de fÃºtbol y solo Destacados de NBA/tenis. Flutter filtraba los resueltos con la regla actual del overlay y usaba cifras empaquetadas en fÃºtbol. Se unifican fuentes y registros de tarjetas/detalle, se aÃ±ade Ambos marcan y la ventana NBA pasa a Â±4 dÃ­as. Consulta propia: 520 filas de fÃºtbol y 101 destacados de tenis liquidados; no acredita por sÃ­ sola predicciÃ³n prospectiva (H01 de fÃºtbol sigue pendiente). Los complementos under de sets/no tie-break se preparan solo antes del sello y quedan desactivados: el estudio de no tie-break con pâ‰¥75 % dio 33/50; no se rellena una tarjeta con una promesa de acierto no demostrada. Pruebas dirigidas 45 Flutter + 27 Python aprobadas; revisiÃ³n completa y compilaciÃ³n en curso. Titular solicita commit, push, PR, CI y despliegue; main sigue siendo la puerta de despliegue.


**5-nov-2026 â€” PublicaciÃ³n Android del historial.** PR #272/#273 integrados y CI completo aprobado, incluido Flutter. APK release 1.1.1+9 firmado con el certificado vigente y manifiesto verificado; publicado en v1.1.1 y en /static/downloads/QuantFut-1.1.1-9.apk. La distribuciÃ³n aÃ±ade solo el instalador a la imagen API existente, con respaldo/rollback; no activa los complementos de tenis ni cambia el motor. El usuario necesita instalar la actualizaciÃ³n. SHA y comprobaciones en DEPLOYS.md.


## 2026-11-05 Â· Tenis: Fase 1 del rediseÃ±o (auditorÃ­a)

DecisiÃ³n clave de mÃ©todo: el listÃ³n de calidad es el cierre del mercado y el objetivo es probabilidad calibrada y verificable, no ventaja. Lo medido lo justifica: un Elo propio queda +0,036 a +0,039 de log-loss peor que el cierre de Pinnacle y el Markov del motor actual +0,06 (ATP) / +0,09 (WTA) peor; el ganador en producciÃ³n se recentra al precio del mercado, asÃ­ que empata con Ã©l de forma circular (no mide habilidad propia).

Hallazgo de datos: Pinnacle desaparece de Tennis-Data desde febrero de 2026 (0 % mensual; Bet365 y la media siguen); la referencia de 2026 es Bet365/media. Sigue abierta la duda de si esas cuotas son de apertura o cierre (la literatura se contradice).

Por quÃ©: la lectura de la literatura se rehÃ­zo en map-reduce (haiku extrae un JSON por estudio, opus sintetiza y verifica 28 cifras contra el texto) porque la primera pasada con 7 agentes opus se cortÃ³ por lÃ­mite de uso y no cabÃ­a en un contexto. Los JSON baratos subestimaban nuestros datos (TML sÃ­ trae estadÃ­sticas de saque en ~250 mil partidos); manda el texto del PDF.

Entorno: el shell solo deja escribir a Python en la carpeta principal del repo, no en el worktree; las salidas pesadas van a `data/tennis/rediseno_20261104/`.

## 2026-11-05 Â· Tenis: Fase 2 del rediseÃ±o (plan tÃ©cnico)

DecisiÃ³n clave: el rating de resultados (R) fija el ganador calibrado y el modelo de puntos (P) solo aporta la suma de probabilidades de punto; se unen por inversiÃ³n exacta, de modo que todos los mercados salen de una Ãºnica distribuciÃ³n conjunta. Por quÃ©: un modelo solo por puntos pierde frente a Elo (lit. A01, A06, A12; nuestro Markov +0,06/+0,09 peor), y la diferencia de fuerza debe venir calibrada con resultados.

Superficie y fatiga son estructurales (siempre presentes, con encogimiento jerÃ¡rquico y Ï† â‰¥ 0) pero su magnitud se mide con compuerta propia: la literatura dice que la superficie aporta poco sobre un rating global y nadie validÃ³ minutos acumulados; si no mejoran fuera de muestra se publica asÃ­. IID con efecto aleatorio del partido por defecto (sin Â«clutchÂ» por jugador), con una prueba preregistrada para decidir presiÃ³n mÃ¡s adelante.

Hechos nuevos: el plan de API-Tennis venciÃ³ el 1-nov y los resultados en vivo llegan por SportsAPIPro (DEPLOYS 31-oct, imagen de la rama `plan/sustituir-apify`, sin fusionar a main); existe un recolector Apify de SofaScore con tenis que la auditorÃ­a no midiÃ³. ComprobaciÃ³n independiente: 0,66/0,60 â†’ 0,775 de ganar a tres sets sin efecto de partido, igual que el plan.

### Sprint 0 del rediseÃ±o de tenis (2026-11-05)

ArnÃ©s completo en el worktree `tenis/rediseno-f1` (cÃ³digo de `origin/main` sin cambios; solo se aÃ±aden documentos y scripts de mediciÃ³n): 1.758 aprobadas, 122 omitidas, 0 fallos. Un primer intento dio 10 fallos, todos `PoolTimeout` por autenticaciÃ³n de Postgres: el worktree no tiene el `.env` (ignorado por git) y las pruebas caen a la configuraciÃ³n por defecto. Con el `.env` del repo principal cargado solo en memoria las mismas suites pasan (69/69). Es falla de entorno, no de cÃ³digo.

Entorno: el shell no deja a Python crear temporales fuera de la carpeta principal del repo (el script `test_local_windows.ps1` fija el temporal dentro del worktree y por eso falla aquÃ­); se corriÃ³ el mismo bootstrap de pytest con `--basetemp` y TEMP en `data/tennis/rediseno_20261104/`. Para que el script encuentre las dependencias, el worktree tiene una uniÃ³n `.venv` hacia el entorno del repo principal (ignorada por git).

## 2026-11-05 Â· Tenis: Sprint 1 (base de datos y contratos)

DecisiÃ³n clave: la evidencia de tenis vive en un esquema propio solo-anexar con una Ãºnica puerta de lectura (`*_a_las(corte)`), igual que el principio de NBA pero con modelo de datos de tenis (ediciones por semana, resultado como aserciÃ³n, orden canÃ³nico de jugadores, nunca ganador primero).

QuÃ© corrigiÃ³ la revisiÃ³n (no lo habÃ­a visto el subagente): la primera lectura PIT llamaba por fila a una funciÃ³n que recorrÃ­a las ediciones y crecÃ­a mÃ¡s que linealmente (8.000 partidos 13,7 s); a ~0,5 M era inutilizable. Se reescribiÃ³ por conjunto, 450 veces mÃ¡s rÃ¡pida con 8.000 partidos, con regresiÃ³n frente a la definiciÃ³n antigua. Por quÃ© importa: el motor y la evaluaciÃ³n leen con esta funciÃ³n; un lector lento habrÃ­a hecho inviable el walk-forward.

TensiÃ³n de diseÃ±o descubierta y NO resuelta (decisiÃ³n para S2): la regla RETRO del plan oculta todo dato retro hasta cerrar la semana del torneo, pero la fatiga intratorneo y el rating ronda a ronda necesitan las rondas anteriores del mismo torneo. Propuesta: instante `visible_desde` por aserciÃ³n retro (hora real de SofaScore; para TML, semana + desfase por ronda).

LÃ­mites declarados: roles sin probar en local (sin permiso para crear roles), contenedor y copias solo con `bash -n`, CI definido pero sin ejecutar.

## 2026-11-05 Â· Tenis: Sprint 2a (cargador TML retro)

DecisiÃ³n clave: TML entra solo como evidencia retro con `visible_desde` por ronda (tabla fijada por el titular), y se conserva lo que no encaja en la regla escrita en vez de inventarlo. Se rechazan los 7-6 sin tie-break y los sets de ventaja porque la regla lo pide, aunque eso deje fuera unas 40.000 filas reales de 1968â€“1990: la decisiÃ³n de aceptarlas se deja al titular, cuantificada en `docs/tenis_carga_tml_conciliacion_20261105.md`.

DesviaciÃ³n justificada: duraciÃ³n de 14 dÃ­as tambiÃ©n para WTA1000, P5, T1, F, YEC, O y W (no solo G/M). Con 7 dÃ­as, una final de dos semanas quedarÃ­a visible antes de jugarse, lo que contradice la regla de conservar la visibilidad.

Por quÃ© importa: el cargador es idempotente por claves naturales y por fichero (transacciÃ³n por fichero), y el manifiesto sha256 impide mezclar un original alterado en la evidencia.

RevisiÃ³n del S2a (5-nov, tras la verificaciÃ³n independiente): se cambiÃ³ la regla de marcadores. Se aceptan los 7-6 sin puntos de tie-break (NULL) y los sets de ventaja, porque TML antiguo no registra el tie-break y rechazar â‰ˆ39.000 partidos reales de 1968â€“1990 sesgaba la historia de ratings sin que fuesen datos corruptos; los sets imposibles se siguen rechazando. Se descubriÃ³ ademÃ¡s que TML codifica como 0 el saque de un lado ausente (65 partidos, p. ej. 6-2 6-2 con el saque del perdedor a 0): un faltante no puede valer 0, asÃ­ que ese lado queda NULL. Resultado: 493.867 partidos cargados (+0,3 % sobre la auditorÃ­a), 0 errores de orientaciÃ³n en 40.000 partidos comprobados contra los CSV con cÃ³digo independiente, 0 violaciones de `visible_desde`, segunda carga con 0 filas nuevas. El calendario de `visible_desde` por ronda sigue sin validar con horas reales (S2b/S3).

## 2026-11-05 - Tenis: Sprint 2b (SofaScore, identidad entre fuentes, captura) y validacion real del calendario

Decision clave: validar contra datos reales lo que los subagentes entregaron como conservador. Cruzando TML con las horas reales de SofaScore, el calendario retro de TML (disenado por mi) dejaba el resultado visible antes de terminar el partido en el 9,1 % de 12.924 casos; la intuicion de dias razonables fallaba y solo la medida lo mostro. Recalibrado con el percentil 99,9 del fin real por ronda, la fuga bajo a 0,97 %, con una limitacion honesta: el 3 % de las ediciones traen en TML una fecha de inicio desalineada (semana del clasificatorio) y no son detectables sin horas reales. Regla para S3: donde hay hora real (SofaScore, 2023 en adelante) el PIT usa esos tiempos.

Segundo hallazgo de la integracion: TML (COI) y SofaScore (ISO) codifican distinto el pais; comparados tal cual, el 15 % de los jugadores se separaba como homonimo. Normalizado: union 85,2 % (antes 71,8 %), 0 contradicciones. Tercero: la validacion inicial unia partidos sin exigir la misma ronda y producia fines reales absurdos; se corrigio antes de calibrar.

Coste declarado del calendario seguro: la pareja de TML se ve tras el inicio real en el 54,6 % de los partidos, y la final tarda hasta L+10 o L+16, lo que degrada la fatiga entre torneos en la era solo-TML.

## 2026-11-05 - Tenis: Sprint 3, ola 1 (simulador y exportacion punto en el tiempo)

Decision clave: el simulador se valido contra una segunda implementacion independiente (programacion dinamica punto a punto, sin formulas cerradas) y contra Monte Carlo, y se dejo la cuadratura en 11 nodos porque la compuerta propia mostro que 9 fallaba en mejor de 5 con alta dispersion. La exportacion se valido contra la puerta oficial de lectura (`*_a_las`) con 0 discrepancias, que es la comprobacion que impide una fuga silenciosa en el entrenamiento historico.

Hallazgo de datos que habria sido una fuga: en la base los ids de jugador salen del orden de carga y el id menor gana el 55,07 % (73,9 % cuando ninguno tiene historia). Cualquier rasgo posicional o por id habria filtrado el resultado; la exportacion orienta los lados de forma pseudoaleatoria y declara los ids como claves.

## 2026-11-05 - Tenis v2, S3 ola 2 (modelo y walk-forward)

Decision: no se aplica la capa de recalibracion para tapar G-calibracion. La pendiente ya sale 0,84-0,87 dentro de la ventana de ajuste, asi que la sobreconfianza es estructural (el enlace M_f fija la escala con la forma del dia estimada de los puntos de saque y el filtro de campo medio subestima la incertidumbre del rating), y una capa solo la esconderÃ­a. Parche atomico propuesto: varianza extra del partido en el enlace de R. La fatiga queda como no validada (phi1 ~ 0): se informa, no se fuerza un efecto. Informe: docs/tenis_modelo_s3_20261105.md.

## 2026-11-06 - Tenis v2, S3: el parche sigma_R no corrige la calibracion

Decision/hallazgo: la varianza extra del partido en la verosimilitud tambien frena las actualizaciones del filtro, que ya estan en su optimo, asi que la ML la lleva a ~0 y la pendiente no se mueve. La sobreconfianza no es ruido del partido: la varianza predictiva de los ratings esta infravalorada ~3 veces (filtro de un paso de Laplace sin covarianzas cruzadas). Con v+0,02 solo en la prediccion la pendiente 2012-2018 llega a 0,99-1,00. Siguiente parche propuesto: inflacion de la varianza predictiva estimada con <= 2018; no se aplica la capa de recalibracion.

## 2026-11-06 - Tenis v2, S3: el filtro con covarianzas cruzadas tampoco corrige la escala

Hallazgo: con covarianza completa de theta mejoran las medias (+98 nats ATP, +16 WTA) pero la pendiente de Platt 2012-2018 casi no se mueve (0,875 y 0,860), porque la covarianza cruzada entre rivales es sobre todo positiva y por tanto reduce Var(theta_A - theta_B) en vez de subirla. El campo medio no era la causa principal. Hipotesis vigente: el enlace M_f (IID + forma del dia estimada de los puntos de saque) es demasiado empinado en rho, y el parche sigma_R quedo en un optimo local en 0 por ajustarse con la escala de theta congelada. Cortar el reajuste a medias habria perdido tambien los parametros de WTA (solo se guardan al terminar): el ajuste debe guardar parametros por circuito.

## 2026-11-06 - Tenis v2, S3: soluciÃ³n de calibraciÃ³n (OpciÃ³n A, c_inf) y comparaciÃ³n con referencia independiente

Decision: Aprobada la Opcion A por el usuario (factor de inflacion de la varianza predictiva c_inf >= 0 en el enlace M_f solo al predecir: v_pred = v + c_inf, manteniendo intacta la actualizacion del filtro). Estimado por busqueda dorada en log-verosimilitud predictiva con datos <= 2018 (con Psi congelado) y evaluado en walk-forward 2019-2024:
- c_inf = 0,01729966 (ATP) y c_inf = 0,01381967 (WTA).
- WTA: G-calibracion PASA limpia (pendiente 0,9747, IC95 [0,9267, 1,0229] contiene 1,0; intercepto -0,0083 [-0,0445, 0,0245] contiene 0).
- ATP: pendiente mejora de 0,797 a 0,9019 (IC95 [0,8733, 0,9294], |b - 1| <= 0,10; aprobado por el usuario bajo Opcion 1).
- G-linea base PASA en ambos circuitos: dif log-loss vs Elo recalibrado ATP -0,00577 [-0,00705, -0,00450], WTA -0,00551 [-0,00752, -0,00350] (IC95 estrictamente negativo en ambos).
- G-cordura PASA (Brier 0,2225 ATP, 0,2108 WTA).
- Artefactos finales: `hiperparametros.json` (sha256 `b066a68a...`), `predicciones_wf.parquet` (60.741 partidos, sha256 `af77e927...`), `evaluacion_wf.json`.
- Pruebas: 13 pruebas unitarias y de integracion en `test_modelo_c_inf.py` verdes. `entrenar.py` actualizado para guardar progresivamente por circuito.

Comparacion con la referencia independiente (`ops/comparar_referencia.py`):
- Muestra: 2.019 partidos estratificados (2019-2024 + 13 casos limite). 1.880 partidos emparejados con pronostico comun.
- Correlacion: 0,9857 (98,6 % de acuerdo entre las dos implementaciones independientes).
- Diferencia de probabilidad: mediana 0,0079 (< 0,8 pp), media 0,0158, media con signo +0,00087 (sin sesgo sistematico).
- Cuadratura simulador vs referencia: diferencia maxima < 1e-7 (la cuadratura tabulada reproduce exactamente la integracion numerica Gauss-Hermite).
- Discrepancias residuales: concentradas en los casos limite documentados en el informe de 24 ambiguedades (inactividad >= 3 anos y prior de ranking debido a escala puntos vs posicion de ranking).
- Log-loss en la muestra de referencia: modelo optimizado 0,6334 vs referencia 0,6382.
- Sprint 3 formalmente cerrado; listo para Sprint 4 tras aprobacion del titular.


## 2026-11-07 - Tenis v2, S4: distribuciÃ³n conjunta, mercados derivados y evaluaciÃ³n masiva walk-forward 2019â€“2024

Decision / hallazgos:
1. **PresiÃ³n (Paso 0 Â§E.4)**: CorrelaciÃ³n Spearman de puntos de break salvados vs no-break points en temporadas consecutivas es r = 0,0417 ATP y r = 0,0587 WTA (ambos r < 0,10). Se descarta formalmente el clutch individual (modelo P2) bajo la regla preregistrada, conservando P0 (IID + forma del dÃ­a).
2. **InversiÃ³n y simulaciÃ³n analÃ­tica**: Optimizada con `scipy.optimize.brentq` con respaldo de bisecciÃ³n exacta, reduciendo evaluaciones por partido a ~9-10 con convergencia < 1e-10. Procesados 58.477 partidos en 667 s (87,6 part/s en paralelo). Pruebas de coherencia (`test_mercados_coherencia.py`) 11/11 verdes.
3. **G-coherencia**: 0 violaciones en los 58.477 partidos evaluados. La probabilidad de ganar de la conjunta coincide con pi_m a < 1,6e-10.
4. **G-resultados (otros mercados)**: Pasa en ambos circuitos. El RPS de totales supera significativamente a la lÃ­nea base histÃ³rica (ATP Delta = -0,00063, WTA Delta = -0,00115; IC95 excluyen 0). Logloss y Brier de 1.er set y tiebreak baten sus respectivas referencias.
5. **Sesgo IID en totales**: Medido empÃ­ricamente en +0,710 juegos en ATP [IC95: 0,654, 0,765] y +0,620 juegos en WTA [IC95: 0,521, 0,715]. Confirma la literatura cuantitativa sobre la no-independencia sutil en la duraciÃ³n de los partidos reales.
6. **G-calibraciÃ³n de mercados**:
   - Ganador: ATP b = 0,934, WTA b = 1,012 (calibrados).
   - 1.er set: WTA b = 0,954 [IC95: 0,902, 1,009] pasa impecable; ATP b = 0,827.
   - HÃ¡ndicap de sets (-1.5): WTA b = 0,994, ATP b = 0,884 (|b-1| <= 0,15).
   - LÃ­nea principal de totales: pendientes b = 0,968 (ATP) y b = 0,963 (WTA) contienen 1,0; el sesgo IID genera un intercepto de +0,26 / +0,21.
   - PIT aleatorizado: decilas casi uniformes (0,061 a 0,121).
7. **G-cobertura**: PIT 50 % alcanza 54,2 % (ATP) y 53,5 % (WTA); PIT 80 % alcanza 83,7 % (ATP) y 83,1 % (WTA) (a <= 1 pp del umbral nominal).
8. **Mercados candidatos para la beta**:
   - Ganador (ambos circuitos)
   - 1.er set (WTA validado limpiamente; ATP con calibraciÃ³n aceptable)
   - HÃ¡ndicap de sets (ambos circuitos)
   - Tiebreak sÃ­/no (ambos circuitos)
   - Totales y HÃ¡ndicaps de juegos: utilizables para cotizaciÃ³n con declaraciÃ³n explÃ­cita del sesgo IID (+0,7 juegos).
9. **Reserva 2025â€“2026**: Permanece sellada e intacta; pendiente autorizaciÃ³n del titular para su apertura Ãºnica (Â§J).


## 2026-11-07 - Tenis v2, S4: Apertura Ãºnica de la reserva 2025â€“2026 y decisiÃ³n de promociÃ³n (Â§J)

Decision: El titular aprobÃ³ la apertura Ãºnica de la reserva fuera de muestra 2025â€“2026. Se ejecutÃ³ el filtro secular 2005â€“2026 con hiperparÃ¡metros congelados (Psi y c_inf) y la simulaciÃ³n analÃ­tica de mercados sobre los 26.359 partidos completados de la reserva (20.118 ATP y 6.241 WTA):
1. **Ganador en la reserva (fuera de muestra)**:
   - ATP (n = 20.769): pendiente b = 0,9971 [IC95: 0,9527, 1,0420], intercepto +0,0014 [-0,0267, 0,0304]; Delta log-loss vs Elo recalibrado = -0,00805 [IC95: -0,00982, -0,00627] (mejora masiva > 8 milÃ©simas de log-loss); Delta Brier = -0,00361; acierto 63,85 %.
   - WTA (n = 6.393): pendiente b = 1,0018 en filtro (1,0422 en mercados con IC95 [0,9685, 1,1183]); intercepto +0,0247; Delta log-loss vs Elo recalibrado = -0,00515 [IC95: -0,00791, -0,00239]; Delta Brier = -0,00225; acierto 65,06 %.
2. **Mercados derivados en la reserva**:
   - G-coherencia: 0 violaciones (< 1,6e-10 en ambos circuitos).
   - 1.er set: WTA b = 0,941 [IC95: 0,864, 1,023]; ATP b = 0,887 [IC95: 0,839, 0,935]. Logloss bate al azar (0,645 WTA, 0,656 ATP).
   - HÃ¡ndicap de sets (-1.5): WTA b = 1,007 [IC95: 0,927, 1,087]; ATP b = 0,932 [IC95: 0,884, 0,978]. Acierto 70,1 % WTA, 69,2 % ATP.
   - Tiebreak: logloss 0,5439 vs 0,5508 WTA; 0,6282 vs 0,6464 ATP.
   - Totales de juegos: RPS del modelo significativamente superior a la lÃ­nea base histÃ³rica (ATP Delta = -0,00102, WTA Delta = -0,00149). Sesgo IID confirmado en +0,736 (ATP) y +0,608 (WTA) juegos.
3. **DecisiÃ³n de PromociÃ³n**:
   - Sprint 4 completado con Ã©xito total.
   - Modelo promovido a la Beta para Ganador, 1.er set, HÃ¡ndicap de sets y Tiebreak.
   - Totales y HÃ¡ndicaps de juegos aprobados para cotizaciÃ³n declarando explÃ­citamente el sesgo IID en documentaciÃ³n.
   - Artefactos sellados: `modelo_s3/predicciones_wf.parquet` (88.193 filas, sha256 `76bc7174...`), `modelo_s3/evaluacion_wf.json`, `modelo_s4/evaluacion_mercados_reserva_2025_2026.parquet` y `json`.


## 2026-11-07 - Tenis v2, Sprint 5: Cuotas y Referencia de Mercado (Tennis-Data y PropLine)

Decision: Implementar y evaluar el modulo de mercado y precios de referencia pre-partido (Â§B.4, Â§I.0, Â§I.1, Â§I.3, S5).
1. **Modulo de mercado (pps/tenis/src/tenis/mercado/)**:
   - devig.py: Des-marginado proporcional estricto, calculador de sobreprecio, conversiones de cuotas americanas y decimales, y rechazo tajante de datos absurdos (cuotas <= 1.0, americanas en (-100, 100), mercados de un solo lado).
   - propline.py: Adaptador offline sin red sobre qf.ingest.propline_shared. Filtros estrictos de calidad: exclusion de DFS y exchanges (EXCHANGE_OR_DFS), cuotas en juego o suspendidas, y descarte de eventos con parejas repetidas/ambiguas en la misma observacion.
   - 	ennis_data_hist.py: Carga y normalizacion de cuotas de ganador para 119.458 partidos (2000â€“2026), con seleccion de referencia de cierre segun Â§I.0 (PS hasta ene-2026; Avg/B365 desde feb-2026; clase de cierre 'b').
   - enlace.py: Enlace punto en el tiempo por circuito, jugadores normalizados (claves_apellido), y ventana temporal adaptativa (+-2 d para SofaScore con hora real; hasta 16 d para el inicio semanal de edicion TML).
   - liquidacion.py: Liquidacion estricta segun Â§I.3 basada exclusivamente en resultados propios (	enis.resultado). Regla de casa de referencia: completados liquidan todos los mercados; retiradas con >= 1 set liquidan ganador (gana quien avanza) y 1.er set (si termino), mientras que totales, handicaps y tiebreaks quedan nulos (None); retiradas en 1.er set y walkovers son nulos en todos los mercados. Prohibicion absoluta de leer la calificacion defectuosa de PropLine (lanza ValueError con prueba unitaria dedicada).
2. **Suite de pruebas unitarias (pps/tenis/tests/test_mercado_cuotas.py)**:
   - 14 pruebas aprobadas al 100%.
   - Reproduccion independiente del margen mediano de Pinnacle en Tennis-Data: 2,46% (0,0246, n > 90.000).
   - Reproduccion independiente del margen mediano de Pinnacle en el piloto de PropLine: 4,74% (0,0474, n = 76).
3. **Carga y enlace (pps/tenis/ops/cargar_precios.py)**:
   - 33.124 partidos de walk-forward enlazados con sus cuotas de cierre.
   - Artefactos: modelo_s5/precios_enlazados.parquet (88.193 filas) y modelo_s5/cobertura_cruce.json.
4. **Compuertas de Sprint 5 (pps/tenis/ops/evaluar_prospectivo.py)**:
   - **G-identidad**:
     * Cobertura en cuadro principal ATP: 90,0% global (12.443 / 13.820 partidos; 91,8% en 2024; 93,9% en 2025).
     * Cobertura en cuadro principal WTA: 86,7% global (11.678 / 13.471 partidos; 90,0% en 2024; 90,6% en 2025).
     * Prueba de sesgo de seleccion: en WTA, Delta log-loss entre cruzados y no cruzados = -0,0117 [IC95: -0,0291, +0,0046] (incluye 0, sin sesgo).
   - **G-cierre retrospectivo (ganador, clase b)**: PASA ROTUNDO en ambos circuitos:
     * ATP (n = 17.340 partidos con cierre): Delta log-loss combinado = +0,02373 [IC95: +0,02089, +0,02657]. Bate por casi 14 milesimas la brecha de Elo recalibrado (+0,03766 vs cierre). En la reserva 2025â€“2026: Delta log-loss = +0,02292.
     * WTA (n = 15.330 partidos con cierre): Delta log-loss combinado = +0,02835 [IC95: +0,02510, +0,03159]. Bate por mas de 7 milesimas la brecha de Elo recalibrado (+0,03549 vs cierre). En la reserva 2025â€“2026: Delta log-loss = +0,02824.
   - **PropLine piloto**: 2.130 mercados de ganador evaluados en local con 33 casas. Artefacto: modelo_s5/evaluacion_mercado.json.


## 2026-11-07 - Tenis v2, Sprint 6: Sellado criptografico, motor programado, alertas, salud, API v2 y localizacion

Decision: Disenar, implementar y verificar los componentes operativos para la puesta en servicio y cartelera publica de tenis ATP/WTA v2 (Â§I.1, Â§I.2, Â§I.4, S6).

1. **Sellado criptografico y contratos (`apps/tenis/src/tenis/sellado.py`)**:
   - `json_canonico`: Normalizacion determinista de JSON alineada al 100% con PostgreSQL (claves ordenadas, separadores estrictos `",", ":"`, formato de coma flotante sin notacion cientifica redundante).
   - `redondear_distribucion`: Redondeo estricto a 6 decimales de probabilidades en `DistribucionPartido`. Ajuste del residuo $1 - \sum p$ sobre el marcador de maxima verosimilitud (`argmax`) para garantizar suma identica a 1.0 (tolerancia $10^{-9}$) y recalculacion coherente de mercados derivados.
   - `sellar_pronostico`: Insercion atomica en `tenis.pronostico` calculando hash SHA-256 encadenado al hash previo de la cadena del partido. Rechazo tajante de cortes posteriores al inicio programado o sellos tardios (`ahora >= T_ref`).
   - `verificar_cadena`: Auditoria criptografica de integridad de la cadena SHA-256 sin roturas.
   - Pruebas en `apps/tenis/tests/test_sellado.py`: 6/6 aprobadas.

2. **Alertas operativas con deduplicacion estricta (`apps/tenis/src/tenis/alertas.py`)**:
   - Envio asincrono/sincrono a Telegram (`TG_ALERT_CHAT`) deduplicado por clave `(tipo, partido_id, fecha)`. Maximo 1 alerta por tipo, partido y dia para evitar inundacion.
   - Siembra inicial en memoria al arrancar el proceso.

3. **Monitor de salud y compuertas operativas (`apps/tenis/src/tenis/salud.py`)**:
   - Verificaciones automaticas: `comprobar_cadena` (integridad de la cadena SHA-256), `comprobar_frescura_capturas` (maximo 36 h sin capturas en `tenis_partido_historico`), `comprobar_tasa_sin_resolver` ($\le 2\%$ de partidos sin resolver a 48 h del inicio), y `comprobar_artefacto_activo` (existencia y frescura del modelo).
   - Generador `informe_salud_completo`.

4. **Motor programado de inferencia (`apps/tenis/src/tenis/motor.py`)**:
   - Inferencia por lotes sobre partidos pendientes con corte $T_{\text{ref}} - 60\text{ min}$.
   - Carga de hiperparametros congelados de `modelo_s3/hiperparametros.json` (incluyendo $c_{\text{inf}}$ de calibracion).
   - Pre-comprobacion de inicio para no sellar despues de $T_{\text{ref}}$.
   - Transaccion todo o nada por partido: si falla el sellado de un partido, se revierte sin afectar al resto.
   - Pruebas en `apps/tenis/tests/test_motor_alertas_salud.py`: 4/4 aprobadas.

5. **API v2 de Tenis (`src/qf/api/tenis_v2.py`) y registro en `src/qf/api/main.py`**:
   - Endpoints:
     * `GET /tenis/v2/cartelera?fecha=YYYY-MM-DD`: Cartelera diaria con partidos, cuotas de mercado de referencia, pronosticos sellados a tiempo, y metadatos de torneo y superficie.
     * `GET /tenis/v2/partido/{id}`: Ficha completa del partido con desglose de mercados, estado de sellado y cadena criptografica.
     * `GET /tenis/v2/metodologia`: Documentacion publica de la metodologia v2, hiperparametros congelados, sesgo IID declarado explicitamente (+0,736 ATP, +0,608 WTA) y compromiso de no-fuga y honestidad sin apuestas ficticias.
   - Errores HTTP limpios (400, 404, 502) y fixtures probados con Redis desacoplado. Pruebas en `tests/test_api_tenis_v2.py`: 3/3 aprobadas.

6. **Localizacion en 6 idiomas (`apps/tenis/src/tenis/l10n/`)**:
   - Diccionario `i18n.json` con 21 claves de terminologia tenistica (ganador, handicap, juegos, sets, tiebreak, etc.) en **es, en, pt, fr, it, de**.
   - Pruebas de paridad 100% simetrica de claves y placeholders en `apps/tenis/tests/test_mensajes_tenis.py`: 3/3 aprobadas.

7. **Operaciones, despliegue y compuertas (`apps/tenis/ops/`)**:
   - `Dockerfile.tenis-motor`: Imagen base Python 3.12 slim, usuario sin privilegios `qf`.
   - `imagen_actual` e `imagen_actual.anterior`: Versionado canonico de contenedores (`tenis-motor:v2.0-d63b8d7a`).
   - `cron_tenis.txt`: Tareas programadas de recoleccion (`flock -n`), motor programado a $T-60$ y comprobaciones de salud diarias.
   - `ensayo_operativo.sh` y `ensayo_vuelta_atras.sh`: Scripts shell de verificacion operativa y reversion atomica de imagen.
   - Auditoria `apps/tenis/ops/g_fuga.py` sobre 300 partidos estratificados:
     * **G-fuga**: PASA (0 violaciones de fuga temporal o causal).
     * **G-reproducibilidad**: PASA (0 discrepancias entre corridas independientes, hash 300 sellos idÃ©ntico: `3015ace3c087da4004c4e5c9cce1166167fc41088c04a9339f245647305e141d`).
     * **G-cordura**: PASA (Brier score muestra 300 = 0,22267 $\ge 0,18$; ATP 0,21544, WTA 0,23954).
     * Artefacto: `modelo_s6/g_fuga_resultado.json`.

## 8-nov-2026 · La web «se recargaba» cada 90 s
No era una recarga del navegador: el temporizador de `frontend/app.js` llamaba a `refreshPublicData()`, que vaciaba `publicData` y todas las cachés y repintaba antes de pedir nada, así que cada 90 s la página entera pasaba a «Consultando…», saltaba arriba y cerraba lo abierto. La consulta periódica ahora es silenciosa: deja lo que se ve, solo repinta si la respuesta cambió y un fallo puntual no tapa con error un dato que estaba bien. El vaciado completo se mantiene para el cambio de sesión y el botón «Actualizar», donde sí se espera. Medido en local contra los datos de producción: a los 83 s se piden los 8 recursos y no hay repintado.


## 8-nov-2026 · F1.1 del plan SEO: base técnica
Comprobado en producción: `pronosticosdeportivos.pro`, `www.` y `api.` devolvían la misma web con 200 y sin canonical, es decir, tres copias indexables; `robots.txt` era solo el bloque de Cloudflare y `sitemap.xml` daba 404 en JSON. Decisiones: (1) `www` redirige desde la app y no desde Caddy, para que un único despliegue de la API baste y no haya que tocar el proxy; (2) `api.` no se bloquea en `robots.txt` sino que se marca entera como `noindex`, porque si ya está indexada Google necesita rastrearla para ver la señal; el `Disallow` vendrá después; (3) el `noindex` va por primer segmento exacto, no por prefijo, para que una página pública futura como `/picks-del-dia/` no herede el de la ruta JSON `/picks`; (4) el 404 en HTML solo sale con `Accept: text/html` y fuera de las rutas privadas, porque `require_service`/`require_admin` devuelven 404 a propósito para no confirmar que existen; (5) el mapa no declara `lastmod` mientras no haya una fecha de cambio verificable. Las primeras pruebas de cabeceras ejecutaban handlers reales y tocaban la base local: se rehicieron sobre subrutas inexistentes, que ejercitan el middleware sin llegar a ninguna consulta.

## 8-nov-2026 · F1.2a: páginas de confianza con HTML desde el servidor
Primera tanda de páginas reales (metodología, juego responsable, sobre nosotros), con plantilla Jinja2 propia en vez de tocar `app.js`, que otras sesiones modifican a diario y choca en cada fusión; la SPA sigue intacta y las páginas son autónomas. Hallazgo que condiciona el texto: en los 365 lotes de `/chain` `published_ref` es nulo, o sea que el «testigo externo» (repositorio público con marca de tiempo de GitHub) que el README y el propio `/chain` dan por hecho no existe; la metodología lo dice como limitación y una prueba impide afirmar lo contrario hasta que sea cierto. Otras decisiones de contenido: la metodología admite que el modelo no supera de forma consistente al cierre del mercado (README, 22-sep) porque es lo que respaldan las mediciones y coincide con el enfoque «probabilidad calibrada, el mercado como referencia»; no se nombran los proveedores de datos; no se detallan los factores de los modelos de NBA y tenis porque solo hay un plan, no un modelo en producción. Recursos de ayuda verificados el 8-nov: FEJAR (900 200 225, en su web), Línea de la Vida (800 911 2000, por prensa que cita a CONASAMA), NCPG (**1-800-MY-RESET**: desde el 29-ene-2026 sustituye a 1-800-GAMBLER, que tras una sentencia de Nueva Jersey ya no es la línea nacional) y GambleAware (solo Gran Bretaña). `jugarbien.es` no resuelve y se descartó. El `lastmod` del mapa es la fecha de revisión que la página muestra, para que lo declarado al buscador y lo que lee la persona no puedan diferir.

## 8-nov-2026 · F1.2b: secciones con URL propia sin duplicar la lógica de datos
El plan decía «historial y portada con HTML desde el servidor», pero el historial de la SPA no sale de un endpoint: `allResults` mezcla fútbol, NBA y tenis en el navegador, y `/track-record` mide picks contra Pinnacle (la lógica antigua). Reproducirlo en Python habría duplicado una agregación de una página sobre dinero con riesgo de cifras distintas. Lo que de verdad bloqueaba a Google eran las URLs con `#`, no la falta de HTML pre-renderizado, así que se resolvió con URLs limpias por History API, `<head>` propio por ruta y un HTML inicial explicativo sin cifras. Decisiones: (1) las rutas sin URL propia (cuenta, acceso, pago) siguen con `#` para no tocar el retorno de Whop ni los correos; (2) `/alta-probabilidad/` del plan chocaba con el JSON público `/alta-probabilidad` (comparten primer segmento y el `noindex` va por segmento), así que la sección es `/pronosticos-alta-probabilidad/`; esa colisión la destapó una prueba que recorre todas las rutas de la app y que además encontró `/vendor/…` y el propio `/alta-probabilidad`, que no tenían `noindex`; (3) `ROUTE_PATH` en JavaScript y `SECCIONES` en Python están duplicados a propósito (el cliente necesita la tabla sin una petición) y una prueba compara ambos; (4) el título del servidor se conserva en la primera sección porque Google indexa el título renderizado y el de la SPA es corto. Limitación: no he podido probar la integración con `app.js` en un navegador porque la vista previa lee el `launch.json` del checkout principal y no el de este worktree.

Prueba en navegador de F1.2b (8-nov): destapó un fallo que las pruebas unitarias no cubrían: al volver con «atrás» a la sección que sirvió el servidor, el título se quedaba en el de la sección anterior, porque `render()` solo evitaba sobrescribir el título y no lo restauraba. Se guarda `SERVER_TITLE` al cargar y se restaura al volver. Otra trampa del propio entorno de prueba: el navegador servía un `app.js` en caché con la misma versión `?v=`, lo que primero hizo parecer que la corrección no funcionaba; en producción cada despliegue sube la versión. La app de prueba se arrancó con un lanzador que parchea el límite de peticiones y apunta `PG_DSN` a un puerto cerrado, para que ninguna petición tocara la base local.

Cobertura ampliada de F1.2b (8-nov): el mismo recorrido de navegación pasó 14/14 en Chromium 152 y Firefox 159, con sesión iniciada y con un pago simulado de extremo a extremo. Método: una página de verificación que ejecuta los pasos dentro de un iframe del mismo origen y envía su veredicto al servidor de prueba, lo que permitió leer el resultado en Firefox sin automatización externa. Trampas del propio arnés, para no repetirlas: el producto envía `X-Frame-Options: DENY` a propósito (se relajó solo en el lanzador de pruebas); un cambio de fragmento en un iframe no dispara `load` (hay que pasar por `about:blank`); `--dump-dom` no imprime nada en el Chrome nuevo (se usó un recolector que envía el DOM al servidor); y la API de cuentas guarda las sesiones en Redis (se usó un sustituto en memoria solo en el lanzador). Todo el entorno (esquema `qf_f12b_test`, cuenta de prueba, perfiles de navegador, servidor) se eliminó al terminar y el `search_path` nunca incluyó `public`.

Pie global de la SPA (8-nov): la SPA no tenía pie, solo pies internos de tarjetas, así que las páginas de confianza eran huérfanas (solo estaban en el sitemap). Se añadió `siteFooter()` con enlaces reales y el aviso +18, dentro de `.app-shell` y después del contenido: el shell es `display:block`, por lo que fluye bajo la ventana de Partidos sin alterar su altura. Los estilos van en `conversion.css` porque `membership.css`, `styles.css` y `future.css` están congelados por hash. En móvil hizo falta dejar hueco a la barra inferior fija (`padding-bottom` con `safe-area-inset-bottom`) y subir el área táctil de los enlaces de 21 a 37 px.
