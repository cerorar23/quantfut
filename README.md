# QuantFut

Sistema cuantitativo de predicción de fútbol para **11 ligas y 2 copas
europeas**. Publica picks en una web propia y corre entero en un VPS de
Contabo por ~$60/mes.

Sin MARL, sin tracking data, sin Transformer. El mercado como referencia y la
infraestructura de credibilidad desde la primera línea.

---

## Fuentes de datos vigentes (1-nov-2026)

Verificado en el VPS el 1-nov-2026 con los crons, los registros y `ingest_health`. Las secciones de más abajo conservan el
historial de decisiones y mediciones: donde nombran API-Football, Apify, PitchAPI, BetsAPI, worldfootballR o football-data
como fuente activa, describen una etapa anterior (todas salvo football-data, que solo aportó histórico, retiradas por el
titular; sus datos ya cargados se conservan).

| Fuente | Qué aporta |
|---|---|
| **PropLine** | Cuotas horarias y cierres (Pinnacle y casas), resultados y calendario. Es la fuente fija de cuotas. |
| **FotMob** (ZenRows de respaldo) | xG, once, bajas, árbitro, sedes, clima, resultados al pitido y marcador en vivo. |
| **SportsAPIPro** | Huecos de once y bajas, con ids de SofaScore. |
| **Scraper SofaScore del VPS** | Archivo de partidos en disco (no escribe en tablas). |
| **Copernicus ERA5** y **OpenTopoData** | Clima histórico por partido y altitud de estadios. |
| **football-data.org** | Testigo de calendario y resultados en 10 ligas (`fdorg_respaldo`): solo avisa, nunca escribe en `matches`. |
| **The Odds API** | Solo respaldo manual por lotes (huecos de cuotas de NBA y tenis, históricos ya autorizados). |

El descanso y la carga (`v_descanso_equipo`, db/093) se calculan con `calendario_equipo` hasta su última carga (22-oct-2026) y
con los partidos terminados de `matches` después.

## Estado de las fases

| Fase | Qué es | Estado | Falta |
|---|---|---|---|
| **0** Captura de cuotas | El activo del negocio | ✅ **100%** | — |
| **1** Ingesta y modelo base | Datos + Dixon-Coles | 🟡 **95%** | xG reciente de FotMob (100 % de lo nuevo desde el 28-oct-2026); falta medir cobertura sostenida y obtener un candidato que supere Elo. El entrenamiento del 12-oct terminó y quedó inactivo: RPS 0,19873 frente a Elo 0,19657 en 1.051 partidos comunes (menor es mejor). Histórico previo sin primera recepción acreditada. 11 ligas + 2 copas en el modelo; 4 ligas adicionales solo sharp (Championship, 2. Bundesliga, Turquía, Noruega). El 25-oct se retiraron Serie B, LaLiga 2, Allsvenskan, Super League suiza, Ligue 2 y Superliga danesa (historial conservado). |
| **2** Validación y calibración | ¿Funciona de verdad? | 🟡 **88%** | Muestra: 300 apuestas publicables en sombra liquidadas con el IC del CLV al cierre sin margen por encima de cero (puerta de 2.A); al 2026-10-08, 24 de 300 (IC [−0,11, +6,03] %, 0 de 3 ligas con muestra propia). Primer modelo activo desde el 2026-09-27 y sellado diario en marcha |
| **3** Publicación y web | Lo que vendes | 🟡 **80%** | Cobros (elegir procesador). Hecho el 7-oct: cuentas, web conectada, correo Proton, panel `/control` |
| **4** Alineaciones y GBM | Segunda generación | 🟡 **40%** | Usar el XI para ajustar lambda |
| **5** Movimiento de línea | Producto defendible | ❌ **0%** | Todo (necesita 12 meses de datos) |

El 13-oct-2026 el titular retiró Chile y Brasil B y autorizó borrar su historial
protegido. Quedan 23 competiciones; Brasileirão Série A permanece. Se eliminaron
sus datos operativos y los productos compuestos afectados, con respaldo y
protecciones restauradas. Los lotes sellados originales conservan su evidencia.
Detalle: [eliminación verificada](docs/eliminacion_chile_brasil_b_20261013.md).

**Las fases 2, 4 y 5 ya no están bloqueadas por los datos: están esperando
MUESTRA.** Con el plan Pro de API-Football contratado (2026-09-22) el
calendario de la temporada en curso se ingiere sin problema —173 partidos
programados en 12 competiciones en la primera pasada— y de ahí cuelgan la
captura de cuotas, las alineaciones a T-60 y el CLV. Lo que falta ahora es
tiempo corriendo: los challengers no se pueden promover hasta acumular
histórico point-in-time, y la fase 5 necesita 12 meses de snapshots. Eso no se
acelera con código.

### El edge del modelo no es cero: es NEGATIVO (2026-09-22)

Medido point-in-time sobre **12.183 filas y 4.061 partidos** (tres cortes
temporales, ajuste solo con lo anterior a cada corte, cierre real como precio):

| quintil de edge | edge medio | ROI realizado | IC95 |
|---|---|---|---|
| 1 | 2,10% | **+1,65%** | [−7,3, +11,3] |
| 2 | 7,11% | −2,78% | [−12,8, +7,2] |
| 3 | 14,08% | −5,04% | [−16,0, +5,4] |
| 4 | 25,20% | −15,90% | [−25,8, −4,6] |
| 5 | 57,26% | −14,43% | [−26,9, −1,8] |

**Cuanto mayor dice el modelo que es su ventaja, peor va.** La correlación del
edge con el acierto es **−0,123** sobre 4.880 candidatos: unas 8,6 desviaciones
típicas de cero. Es selección adversa en estado puro — donde el modelo más
discrepa del cierre, más se equivoca.

Dos consecuencias que hay que tener presentes al leer el resto del README:

1. **Cualquier filtro construido sobre esa cantidad hereda el signo.** Por eso
   la zona de abstención no se pudo calibrar: no es que el mecanismo falle, es
   que el insumo es una anti-señal.
2. **`publish/picks.find_candidates` ordenaba por esa cantidad.** Publicar
   picks con ese criterio era publicar pérdidas. **Sustituido el
   2026-09-23:** el modelo ya no elige picks. Se eligen casas donde apuestan
   los suscriptores (Bet365, Betano, 1xBet, William Hill…) cuando pagan al
   menos un 2% por encima del precio justo de Pinnacle en el MISMO snapshot,
   con Pinnacle verificado contra el consenso de las demás casas, y el stake
   sale del edge esperado al cierre (edge × persistencia medida por casa).
   **Desde 2026-10-03** ese stake se multiplica además por `ρ²/(ρ²+SE²)`
   (Baker y McHale, 2013): la persistencia es una estimación, y la de Bet365
   (0,13, IC95 [−0,15, 0,41]) no se distingue de cero. Solo cambia cuánto se
   recomienda apostar: qué oferta es publicable se sigue decidiendo sin el
   factor, así que la muestra de la puerta no cambia (decisión del usuario).
   Cada pick publica su cuota mínima aceptable (`min_price`) y la hora de su
   precio. La publicación sigue pausada (`PUBLISH_PICKS_ENABLED=0`) hasta que
   el criterio pase la puerta en sombra: `qf.publish.shadow_sharp` registra
   cada hora lo que se habría recomendado, lo liquida contra el cierre sin
   margen y publica el estado en `/model-card` (`sombra_criterio_sharp`),
   con desglose por antelación, casa, fuente y liga. El informe incluye las
   ofertas aún pendientes de resultado, pero solo las que tienen cierre justo
   cuentan para las 300 de la puerta. El job diario vuelve a comprobar esa
   puerta aunque `PUBLISH_PICKS_ENABLED` se active por error.
   **Desde 2026-09-28** (para acelerar la muestra sin rebajar la puerta): la
   sombra mide TODAS las casas no exchange del snapshot, pero la puerta solo
   cuenta las de `SOFT_BOOKS` (ampliada con Betsson y Coolbet, confirmadas
   por el usuario); ninguna oferta sale de un snapshot a menos de 15 min del inicio
   (se liquidaría contra sí misma); la persistencia por casa se recalibra con
   la sombra con una regla fijada de antemano (`picks.mezclar`: la previa
   pesa como 100 partidos); y diez ligas más alimentan la sombra (db/033).

Lo que NO falla es la probabilidad: el modelo está bien calibrado dentro de
±0,02 en todos los tramos con muestra, y `p_model` correlaciona **+0,312** con
el acierto. El modelo sabe de fútbol. Lo que no sabe es más que el cierre.

### La medición que importa (2026-09-22)

Sobre **30.457 partidos reales** (football-data.co.uk, 7 ligas, 2014-2026, con
96.7% de cuotas de cierre de Pinnacle), evaluación secuencial fuera de muestra,
**n = 28.128 predicciones**:

| Liga | n | RPS modelo | RPS mercado | Delta |
|---|---|---|---|---|
| mx.liga_mx | 3.568 | 0.21280 | 0.20795 | −0.00485 |
| gb.premier_league | 4.142 | 0.19934 | 0.19388 | −0.00546 |
| ar.primera | 4.848 | 0.21482 | 0.20878 | −0.00604 |
| es.laliga | 4.144 | 0.19561 | 0.18857 | −0.00704 |
| br.serie_a | 4.077 | 0.20815 | 0.20103 | −0.00712 |
| nl.eredivisie | 3.218 | 0.19304 | 0.18568 | −0.00736 |
| it.serie_a | 4.131 | 0.19627 | 0.18837 | −0.00790 |
| **TOTAL** | **28.128** | **0.20327** | **0.19674** | **−0.00653** |

**El modelo pierde contra el mercado en las siete ligas, sin excepción.**

Ampliar a 11 ligas **no cambió esto**, y era lo esperable. Remedido con el
motor Kalman (mismo protocolo secuencial que el resto de comparaciones de este
README), el delta por liga se mueve como mucho en la cuarta cifra decimal, y la
MLS aterriza donde las demás:

| liga | n | RPS modelo | RPS mercado | Delta |
|---|---|---|---|---|
| us.mls | 5.004 | 0.21454 | 0.20864 | −0.00590 |
| *(las 7 anteriores)* | 28.718 | 0.20330 | 0.19680 | −0.00650 |

Añadir competiciones **amplía el catálogo, no crea ventaja**. Es la misma
conclusión que para los mercados derivados: los ~150 salen de las mismas dos
lambdas, y más ligas son más partidos de la misma calidad de predicción.

Y el número que lo resume: el peso óptimo modelo/mercado estimado sobre estos
mismos datos es **w_model = 0.0001**. Cero. El mercado ya incorpora todo lo que
el modelo sabe. (Solo Premier League sale a 0.065, y a esa escala es ruido.)

**Tampoco frente a la cuota temprana (2026-10-03).** Medido contra la cuota de
Pinnacle de uno a tres días antes (`PSH`, 14.110 partidos, 7 ligas, 2019/20-
2024/25, `python -m qf.eval.early_vs_close`): `w_model` sale otra vez 0,0001, y
el mercado no se mueve hacia el modelo entre esa cuota y el cierre (pendiente
0,003, IC95 [−0,008, +0,014]). La prueba sí detecta señal cuando la hay: con la
media de las casas como "modelo" la pendiente es 0,38 [0,29, 0,46] en las 7
ligas. Apostar al precio temprano cuando el modelo ve ≥2 % de ventaja da −4,9 %
contra el cierre justo, peor que apostar a todo sin criterio (−3,9 %). No hay
ventana temporal en la que la información del modelo llegue antes que el
mercado.

**Ni entrenándolo para apartarse del mercado (2026-10-03).** El método de
Hubáček y Šír (IJF 2023), que gana en la NBA con un modelo peor que el
mercado, aplicado a los mismos partidos con walk-forward por temporadas
(`python -m qf.eval.decorrelacion`): EV contra el cierre −3,5 % [−3,8, −3,2]
en 0 de 7 ligas. Apartarse del mercado gana 0,3 puntos y no cubre el margen,
y la ventaja que el modelo cree ver sigue correlacionando en negativo con el
valor real.

Se descartaron por medición, no por intuición:

- *"Gana en las ligas latinoamericanas, que son mercados más blandos."* Falso.
  Liga MX tiene el hueco más pequeño pero sigue siendo negativo. No hay
  ninguna liga donde apostar con ventaja.
- *"Falta calibrar / ajustar hiperparámetros."* El barrido de `process_var`
  mueve el RPS en la cuarta cifra decimal.
- *"Falta xG."* Sí ayuda —RPS 0.20424 → 0.20336 al activarlo— pero cierra solo
  el 12% del hueco.
- *"Es cuestión de técnica de modelado."* Dos motores independientes
  (Dixon-Coles con decaimiento y filtrado bayesiano) aterrizan en el mismo
  sitio.
- *"Dixon-Coles es de 1997; hay distribuciones mejores."* Medido el
  2026-09-24 (`qf.model.structure`, 2.641 partidos fuera de muestra):
  Poisson bivariante, Conway-Maxwell-Poisson, conteo Weibull con cópula y
  probit ordenado no mejoran al `tau` de Dixon-Coles con ningún intervalo por
  encima de cero, y CMP y Weibull empeoran el 1X2. Sus parámetros quedan
  pegados a Poisson: no hay sobredispersión que corregir.

**El diagnóstico es que falta INFORMACIÓN, no técnica.** El modelo sabe goles y
xG. El mercado sabe además lesiones, alineaciones, rotación, motivación,
clima, fichajes y cambios de entrenador. Ninguna sofisticación matemática sobre
"goles marcados" fabrica información que no está ahí.

**La puerta de la fase 2 NO se cumple**, y la fase 3 (vender) no debe
arrancarse hasta que se cumpla. Esa puerta existe precisamente para este
momento.

#### Lo que esta medición NO puede responder

Todo lo anterior compara contra el **cierre**, que es el precio más afilado que
existe. Un modelo peor que el cierre todavía podría ser rentable si encuentra
precios equivocados en casas blandas ANTES de que converjan — eso es el CLV, y
es la métrica principal de este sistema.

**Corrección (2026-09-23):** aquí se afirmaba que football-data.co.uk solo trae
cuotas de cierre y que por eso el CLV histórico era inmedible. Es falso para
las 7 ligas del formato PRINCIPAL (Premier, LaLiga, Serie A, Eredivisie,
Bundesliga, Ligue 1, Primeira): sus CSV traen, además del cierre, cuotas
**pre-cierre** (tomadas días antes del partido) de Pinnacle, Bet365, Bwin,
William Hill, 1xBet, Betfair Exchange, máximo y media del mercado, para 1X2,
over/under 2,5 y hándicap asiático. `history_fd.py` las descartaba: se queda
con la primera familia de columnas y hace `break`. Sí es cierto para el formato
"extra" (Liga MX, Argentina, Brasil, MLS), que solo trae cierre; para esas
ligas el camino es el endpoint histórico de The Odds API (plan de pago, datos
desde junio de 2020).

**Backtest "casa blanda contra precio sharp"** (`python -m qf.eval.soft_vs_sharp`,
dataset `d5cbc315…`: 42 CSV, 14.294 partidos, 7 ligas, 2019/20-2024/25). Se
apuesta en la casa blanda cuando su cuota pre-cierre supera el precio justo de
Pinnacle en ese momento; se mide contra el cierre de Pinnacle sin margen, la
misma vara de la puerta comercial. IC por remuestreo de semanas.

| estrategia (1X2, umbral 2%) | n | EV al cierre justo | IC95 | persistencia |
|---|---|---|---|---|
| mejor cuota entre casas reales* | 1.378 | **+2,09%** | [1,21, 2,91] | 0,42 |
| 1xBet | 280 | +2,78% | [1,41, 3,95] | 0,68 |
| Interwetten | 204 | +2,23% | [0,67, 3,82] | 0,55 |
| Bet365 | 415 | +0,56% | [−0,70, 1,79] | 0,13 |
| control: Pinnacle en todo, sin criterio | 42.882 | −3,90% | — | — |

\* Bet365, Bwin, William Hill, 1xBet, Interwetten, BetVictor. Positivo en las 7
ligas. *Persistencia* = qué fracción del edge visto antes del cierre sigue
siendo valor en el cierre: menos de la mitad, y muy distinta por casa. El ROI
realizado no es concluyente (IC95 [−10,2, +15,1]). Es lo contrario de lo que
pasa seleccionando por el edge del modelo.

**Over/under 2,5: sin oportunidades verificables en casas reales.** El "máximo
del mercado" sale positivo, pero no es una casa donde se pueda apostar. Y en
over/under hay precios de Pinnacle rotos (congelados, o de otra línea) que
fabricaban "edges" del 10-13% que parecían persistir hasta el cierre, porque el
cierre de referencia estaba igual de roto. La guarda `MAX_SHARP_DEVIATION`
descarta el mercado cuando Pinnacle se aparta más de 3 puntos de la media de
las casas, usando solo precios anteriores al cierre. Detalle en
`harness/progreso.md`.

**Liga MX, Brasil, Argentina y MLS con el histórico de The Odds API**
(`python -m qf.ingest.odds_history`, 2025, 1.681 partidos con Pinnacle antes y
al cierre, hasta 26 casas de la región `eu`; precio temprano 24-48 h antes,
cierre 5 min antes; 16.560 créditos). Umbral 2%:

| casas | n | valor esperado al cierre justo | IC95 |
|---|---|---|---|
| todas | 317 | +2,78% | [1,79, 3,78] |
| accesibles a los suscriptores (1xBet, William Hill, 888sport) | 127 | +3,83% | [2,36, 5,20] |

El valor accesible es **una sola casa** (126 de 127 apuestas son de 1xBet) y
sobre todo **MLS** (85). En Liga MX, con esas casas, hay 7 apuestas en el año y
salen negativas; su valor estaba en Coolbet y Unibet, casas europeas. Depender
de una casa es frágil: es la primera que limita la cuenta de quien gana.

**Qué casas hay en cada fuente.** The Odds API no tiene ninguna casa mexicana
ni Bet365 (solo `bet365_au`); Betway solo en la región `uk`. API-Football, ya
contratado, sí trae **Bet365, Betano, 1xBet y William Hill junto a Pinnacle**
en 12 de nuestras 13 competiciones (consultado el 2026-09-23), pero refresca
cada ~3 h y solo guarda 7 días de histórico.

Para el CLV de los picks reales sigue haciendo falta `qf.ingest.odds_worker`
capturando a lo largo del tiempo.

### MLS, Champions, Europa League y las tres grandes que faltaban (2026-09-22)

Se pasa de 7 ligas a **11 ligas + 2 copas**, de 31.041 a **50.079 partidos**.

| competición | partidos | xG | cuotas de cierre | ¿apostable? |
|---|---|---|---|---|
| `us.mls` | 6.203 | 44,0% | sí, Pinnacle desde 2012 | sí |
| `fr.ligue_1` | 4.282 | 61,9% | sí, Pinnacle | sí |
| `pt.primeira` | 3.734 | 51,6% | sí, Pinnacle | sí |
| `de.bundesliga` | 3.708 | 62,5% | sí, Pinnacle | sí |
| `eu.ucl` | 722 | 75,2% | **ninguna** | todavía no |
| `eu.uel` | 389 | 70,7% | **ninguna** | todavía no |

**Las cuatro ligas entran completas** y sin sorpresas. Bundesliga, Ligue 1 y
Primeira están en el formato PRINCIPAL de football-data.co.uk (columnas ricas:
tiros, córners, tarjetas, faltas, árbitro) y la MLS en el "extra", el mismo que
Brasil y Argentina. Las cuatro tienen fichero tiro a tiro en FBref.

Bundesliga, Ligue 1 y Primeira **no se añadieron por sí mismas**, aunque
también son apostables: se añadieron porque eran las que más partidos de copa
estaban tirando a la basura (ver más abajo).

**Las copas europeas entran a medias, y hay que decirlo claro.** No existe
histórico gratuito de cuotas de Champions ni de Europa League en ninguna parte:
football-data.co.uk solo cubre ligas domésticas y el release de copas de
`worldfootballR_data` da resultado y xG pero ni un precio. Sin cuotas de cierre
no hay baseline de mercado, así que esos partidos **no se pueden evaluar, ni
calibrar, ni usar para medir CLV**. Entran como datos de ENTRENAMIENTO. Que la
Champions sea apostable depende de que `odds_worker` acumule cierres propios
(`soccer_uefa_champs_league`), no de la ingesta histórica.

#### Competición y liga dejan de ser lo mismo

Hasta aquí todos los partidos de una liga los jugaban equipos de esa liga.
Meter la Champions rompe ese supuesto, y romperlo mal habría sido caro: dar de
alta equipos bajo `league_id='eu.ucl'` crearía un Real Madrid de Champions
distinto del de LaLiga, con una docena de partidos y ningún rival en común.

La separación (`db/007_competiciones.sql`) es:

- `matches.league_id` → la **competición** donde se juega el partido.
- `teams.league_id` → la **liga doméstica** del equipo.

`ingest/uefa_cups.py` NUNCA crea equipos: si no reconoce a los dos, descarta el
partido. Y `ingest/fixtures.py`, en competiciones marcadas `cross_league`, solo
acepta coincidencias **exactas**, nunca difusas: buscando a la vez en las once
ligas, un difuso puede colocar un club europeo encima de uno latinoamericano de
nombre parecido y contaminar dos historiales sin dar ningún error.

#### Lo que las copas aportan de verdad: comparar ligas entre sí

Es su valor real, y no tiene que ver con apostarlas. El modelo impone **suma
cero de ataque y defensa dentro de cada liga**, así que un ataque de 0,3 en
Eredivisie y uno de 0,3 en LaLiga no están en la misma escala: dentro de los
datos domésticos no hay absolutamente nada que las conecte. Los cruces europeos
son la **única** información que identifica esa diferencia.

`model/dixon_coles.py` añade un término `strength` por liga que entra con signo
opuesto en las dos intensidades:

```
log lam = base[comp] + ha[comp] + (atk[h] + str[lg_h]) - (dfn[a] + str[lg_a])
log mu  = base[comp]            + (atk[a] + str[lg_a]) - (dfn[h] + str[lg_h])
```

En un partido doméstico `lg_h == lg_a` y el término **se cancela exactamente**.
Esa propiedad es lo que permitió añadirlo sin volver a validar las ocho ligas, y
está fijada por test (`tests/test_cross_league.py`): se recalcula la lambda a
mano sin el término y tiene que salir idéntica a 1e-9.

Verificado sobre datos simulados con dos ligas de nivel deliberadamente
distinto: con 400 cruces recupera una diferencia de **0,32** frente a la 0,40
sembrada. El encogimiento es a propósito (`POOL_STRENGTH = 300`), porque la
muestra real de cruces es pequeña.

#### Por qué se añadieron Bundesliga, Ligue 1 y Primeira

De los partidos de copa desde 2015 **solo se aprovechan aquellos con los dos
equipos en el catálogo**. Con 7 ligas eran **406 de 3.308**. Los países que más
partidos tiraban:

| país | partidos perdidos | ¿dado de alta? |
|---|---|---|
| Alemania | 633 | ✅ `de.bundesliga` |
| Francia | 464 | ✅ `fr.ligue_1` |
| Portugal | 380 | ✅ `pt.primeira` |
| Bélgica | 264 | ❌ |
| Rusia | 252 | ❌ |
| Ucrania | 235 | ❌ |
| Turquía | 230 | ❌ |
| Grecia | 180 | ❌ |

Añadirlas llevó los cruces utilizables de **406 a 1.111** (×2,7). Es el único
motivo por el que se dieron de alta: son ligas apostables, sí, pero lo que se
buscaba era muestra para identificar `strength`.

El siguiente escalón es mucho más plano: Bélgica, Rusia, Ucrania, Turquía y
Grecia sumarían ~1.160 partidos más, pero son cinco ligas en vez de tres, tres
de ellas fuera del formato principal de football-data, y con clubes que rotan
más en Europa. **Hay rendimientos decrecientes claros y aquí es donde conviene
parar** salvo que se quieran esas ligas por sí mismas.

### Huecos concretos que quedan

**Fase 2 — Elo implementado y medido, puerta aún sin superar.** `model/elo.py`
predice 1X2 secuencialmente con empate, localía y tratamiento de equipos
nuevos. `eval/comparison.py` compara Elo, Dixon-Coles y Pinnacle sin margen
sobre la misma intersección de partidos. En la ventana histórica con cuotas
disponibles (1.907 observaciones, julio de 2025–enero de 2026), el RPS fue
0,20245 para Dixon-Coles, 0,20533 para Elo y 0,19561 para Pinnacle. Dixon-Coles
mejora Elo, pero **pierde contra el mercado**. La última cuota histórica sharp
es del 14 de enero de 2026: faltan cuotas recientes y la puerta de promoción
bloquea comparaciones con mercado de más de 30 días de antigüedad. El bootstrap
por semanas estima una ventaja de RPS de Dixon-Coles sobre Elo de 0,00288
(IC 95 %: 0,00053 a 0,00506), pero una desventaja frente a Pinnacle de
0,00684 (IC 95 %: 0,00350 a 0,01061). La regresión deportiva mejora al modelo
en su holdout; las ablaciones Elo/tiros sobre el cierre muestran diferencias
pequeñas y diagnósticas, no una señal operable a T-60.

**La puerta de la fase 2 cambió el 2026-09-22: ya no es batir al cierre.**
Son dos afirmaciones distintas y solo una es alcanzable: *"mi probabilidad es
mejor que el consenso de cierre"* no la consigue casi nadie, y además no es lo
que se cobra; *"el precio que tomé era mejor que el cierre que vino"* sí es
medible, y eso es el CLV. La autorización comercial
(`promotion.evaluate_clv_gate`, publicada en `/model-card`) exige ahora las
tres a la vez: 300 apuestas liquidadas, intervalo de confianza del 95% del CLV
ENTERO por encima de cero, y al menos 3 ligas con muestra propia. La última no
es adorno: un CLV que solo vive en una liga es un hallazgo sobre esa liga —o
sobre una casa— y es lo primero que desaparece cuando esa casa limita la
cuenta. Batir al cierre en RPS se sigue reportando; ya no veta.

**Qué CLV (corregido el 2026-09-23).** La puerta mide el **valor esperado
contra el cierre sin margen**: `ev_close_pct = cuota × p_cierre_justa − 1`, con
la probabilidad sacada de un único snapshot de cierre de Pinnacle con el grupo
de selecciones completo (en hándicap, local −0,5 se empareja con visitante
+0,5). Antes medía `clv_pct = cuota / cierre − 1` contra la cuota CON margen,
que sale inflada por ese margen: apostar a Pinnacle en todo, sin criterio, da
`clv_pct` −0,32% cuando su valor real es −3,90% (14.294 partidos). Con esa vara
la puerta podía autorizar una estrategia perdedora. `clv_pct` se sigue
guardando y publicando en `/track-record`; ya no decide. Las apuestas en
mercados sin precio sharp (BTTS, doble oportunidad, totales por equipo) no
cuentan para la puerta: no hay cierre justo contra el que medirlas.
Migración `db/015_ev_cierre.sql`.

El límite real del negocio que esto define no es el modelo: es que las casas
blandas limitan cuentas. Conviene saberlo antes.

**Fase 3 — la API no maneja usuarios, y es una decisión, no un hueco
(2026-09-22).** No hay suscripciones, login ni cobros en este repo. Un único
backend de confianza (el de tu frontend) llama a `/v1/*` con `SERVICE_TOKEN`
y recibe TODOS los picks; ese backend es quien tiene la base de suscriptores,
cobra, y decide qué le muestra a cada usuario final (además de armar los
prompts del LLM con los números que le pidió a esta API). Ni la web ni la
futura app Flutter le hablan a esta API directamente — un secreto embebido en
un cliente que corre en el dispositivo del usuario siempre se puede extraer;
uno que vive solo en un servidor, no. Detalle de diseño y de la reversión
del intento anterior (auth de suscriptor por JWT) en `harness/progreso.md`.

**Actualización de arquitectura (2026-09-23):** el prototipo web se entrega
ahora desde este mismo FastAPI en `/`, y `/control` ofrece un panel interno
de solo lectura con contraseña propia (salud, puerta comercial calculada con
el mismo `shadow_sharp.report()` que decide reactivar la publicación, último
entrenamiento con los motivos de su puerta, modelo activo y nombres sin
resolver). Los paneles de CLV de Grafana leen `pick_results`, vacía mientras
la publicación siga pausada: la muestra previa se sigue en `/control`. La propuesta anterior de un BFF como
segundo servicio queda sustituida por módulos dentro de un único backend.
Esto no activa cuentas de cliente, pagos ni contenido premium: siguen
pospuestos hasta la validación de CLV. `SERVICE_TOKEN` y `ADMIN_TOKEN`
permanecen solo en el servidor; el JavaScript de la demo no los utiliza.

**Fase 3 — existe un prototipo visual con evidencia pública, no la web comercial.** `frontend/`
contiene ocho vistas navegables; inicio, picks e historial consultan los
endpoints públicos y separan sus cifras reales de la maqueta ficticia. La
interfaz no implementa login, pagos o acceso privado.
**Partidos y estadísticas** (2026-09-27) es contenido real: agenda del día y
ficha con forma, cara a cara, promedios, estadísticas del partido,
clasificación, alineaciones y bajas, servida por `/web/partidos` y
`/web/partidos/{id}` (`api/fichas.py`). No lleva cuotas, precio justo ni la
opinión del modelo: publicar el precio justo de Pinnacle de cada partido
dejaría a cualquiera reproducir el criterio de picks.
El backend expone `/track-record`, `/calibration`, `/chain`, `/picks/free`,
`/v1/picks`, `/v1/fair-price/{id}` (privado desde 2026-09-28: dice qué casa
paga por encima del justo, que es el criterio), `/leagues`, `/teams`,
`/matches/{id}` y las rutas `/web/*`. La integración de datos
privados y suscripciones queda para después de la validación, en módulos del
mismo FastAPI que conserven `SERVICE_TOKEN` fuera del navegador.

**Fase 3 — faltan los cobros.** Webhook del procesador → alta en `subscribers`.
El código es pequeño; lo lento es la aprobación del procesador, que conviene
empezar a gestionar mucho antes (ver "Procesadores de pago").

**Control operativo de la sombra.** `/control` incluye el recorrido por liga de
las ofertas capturadas y las primeras candidatas: programadas, en juego,
resultado atrasado, liquidación pendiente, liquidadas sin cierre sharp completo
y liquidadas con cierre justo. La misma auditoría JSON está en
`/admin/shadow-audit`, protegida con `ADMIN_TOKEN`. Es de solo lectura y no
altera la puerta comercial; ayuda a distinguir falta de tiempo de fallos de
ingesta o cierre. Encima, la tabla de los picks que se habrían publicado
(uno por partido, el más reciente primero) con cuota, cierre de Pinnacle, EV
al cierre y resultado: sale de `shadow_sharp.publishable`, la misma selección
que cuenta la puerta, y solo vive tras el login del panel porque enseña el
criterio de selección. El recorrido ilustrativo de cuentas y cobros se documenta en
`frontend/ACCESS_FLOW.md`; todavía no concede suscripciones ni cobra.

**Fase 4 — las alineaciones se capturan y pueden evaluarse en sombra.**
`qf.ingest.lineups` consulta el XI desde T-90 y `availability()` expone cuántos
titulares habituales faltan, por posición, y la continuidad del XI. En la
práctica API-Football lo publica hacia **T-25** (22 de 22 partidos de MLS y
Liga MX, oct-2026), cuando Pinnacle ya ha ajustado. El XI de hoy sale solo de
lo capturado antes del inicio; la historia de cada equipo (sus últimos XI)
sale además de `lineups_historicas` desde el 2-oct-2026 (db/036, decisión del
usuario), igual que en el entrenamiento: sin eso, las ligas europeas no
tendrían 3 XI previos hasta finales de octubre. El
challenger de `model/lineup_challenger.py` estima ajustes separados sobre
`log(lambda_home)` y `log(lambda_away)` y se entrena en el reentreno mensual
con esas alineaciones históricas. `model/shadow.py` guarda tanto
la predicción base a T-60 como el ajuste de XI y sus CLV en tablas separadas,
sin modificar picks publicados. Solo podrá promoverse si mejora RPS/log-loss,
calibración y CLV frente a la base, con incertidumbre y varias ligas. También queda
para esa etapa estimar una zona de abstención propia: si el edge está dentro de
la variación del modelo entre reentrenamientos o remuestras, no se publica como
señal aunque sea nominalmente positivo.

Resultado del 1-oct-2026 (3.650 partidos con XI, alineaciones históricas solo
para entrenar): el XI simple mejora RPS (0,21817 → 0,21678), log-loss y 8 de 11
ligas, y la calibración solo empeora dentro de su ruido (ECE 0,03041 →
0,03096; IC95 del cambio [−0,0074, +0,0058]). Desde el 1-oct la puerta de ECE
del XI usa ese remuestreo en vez de comparar dos números sueltos (decisión del
usuario), así que el XI simple queda validado offline y entra en la sombra; sigue
sin publicarse hasta demostrar CLV. La fuerza por jugador (`model/player_ratings.py`,
`model/player_value.py`) se midió sobre las mismas filas: "XI con valor"
empeora incluso a la base (RPS 0,21912) y no se usa; la comparación se repite
en cada reentreno mensual. El más-menos regularizado (`model/masmenos.py`,
2026-10-03), que valora al jugador por cómo le va al equipo con él en el campo
en vez de por sus estadísticas, tampoco: RPS 0,21838 frente a 0,21826 de la
base y 0,21686 del XI simple. Con un año de datos, saber QUIÉN falta no añade
nada a saber CUÁNTOS habituales faltan, se mida como se mida.

### Lo que ya está resuelto y antes figuraba como hueco

- **Calibración** (`model/calibration.py`): corrección afín sobre las lambdas
  —no isotónica sobre el 1X2— para que los ~150 mercados sigan siendo
  coherentes entre sí. Con puerta de validación que la descarta si no mejora.
- **Peso modelo/mercado** (`model/meta.py`): estima `w_model` por log-loss
  fuera de muestra, con pesos por liga encogidos hacia el global.
- **Modelo por liga**: Dixon-Coles con ventaja de local e intercepto de goles
  POR LIGA, con pooling parcial. Verificado recuperando ventajas de local
  distintas sembradas a propósito.
- **Riesgo de portafolio correlacionado** (`publish/picks.py`): sigma conjunta
  con matriz de correlación en vez de sumar stakes como si fueran
  independientes.
- **GBM sobre el residuo del mercado** (`model/residual.py`), desactivado por
  defecto: corrige solo el 1X2 y rompería la coherencia con el resto.
- **Ancla de mercado** (`model/market_anchor.py`): invierte el 1X2 sin margen a
  las intensidades que lo reproducen. Es la lectura útil de `w_model = 0.0001`
  —el modelo sirve para la FORMA (la matriz de marcadores, de la que salen ~150
  mercados coherentes), el mercado para el NIVEL— y es lo que permite aplicar
  un ajuste por información nueva ENCIMA del precio vigente en vez de encima de
  una estimación peor. Devuelve siempre el residuo: la familia no representa
  cualquier terna 1X2 y cuando no llega hay que saberlo.
- **Incertidumbre del edge** (`model/uncertainty.py`), desactivada por defecto:
  el error estándar de cada parámetro sale del ajuste y se propaga por Monte
  Carlo hasta el edge. De esa sola medida salen dos cosas que antes eran
  constantes a ojo: la zona de abstención (si `media − Z·sd ≤ 0`, la ventaja no
  se distingue de cero y no se apuesta) y el encogimiento del edge, que pasa a
  ser `floor/media` por apuesta en vez del 0,55 fijo que encogía igual a un
  equipo con veinte partidos recientes que a uno con tres. No crea ventaja:
  elimina apuestas de EV negativo. Sube el ROI realizado y **no** el RPS.
- **Ratings dinámicos** (`model/kalman.py`): la fuerza como estado latente.
  96× más rápido de evaluar que el walk-forward.

---

## Arquitectura: dónde encaja cada cosa

```
  FUENTES                    VPS CONTABO                     TÚ Y TUS CLIENTES
  ───────                    ───────────                     ─────────────────

  PropLine            ─┐
  FotMob              ─┤                                    ┌─ Web pública
  SportsAPIPro        ─┼──▶ workers ──▶ Postgres ──▶ API ───┼─ App móvil
  SofaScore, ERA5     ─┘      (cron)        │        (interna) └─ Alertas Telegram
                                            │
                                            └──▶ Grafana ──────── Solo tú
```

**Un solo FastAPI, cuatro niveles (fase comercial desde 2026-10-07).** Las
cuentas de clientes viven en este mismo backend y las consumen la web y la
app Flutter. Ningún cliente que corre en el dispositivo del usuario lleva
secretos: cada persona se autentica con su cuenta y el servidor decide qué
picks ve. Rate limiting por IP en TODAS las rutas.

| Nivel | Auth | Para qué |
|---|---|---|
| **Público** | ninguna | Track record, calibración, cadena de hashes, picks gratis |
| **Clientes** `/app/v1` | cuenta propia: bearer opaco de 15 min + refresh rotatorio de 30 días | Registro, login, perfil, planes y picks según suscripción (web y app Flutter). Esquema: `/app/v1/openapi.json` |
| **Servicio** `/v1` | `SERVICE_TOKEN` en `X-Service-Token`, solo servidor a servidor | Todos los picks y probabilidades, sin recorte |
| **Admin** `/admin`, `/control` | Cloudflare Access + token / usuario del panel | Operación y administración comercial |

`ACCOUNTS_ENABLED=1` abre `/app/v1`; sin él responde 503 (un despliegue sin
decidirlo no abre altas). El derecho Plus sale SIEMPRE de `subscriptions` en
el servidor; una suscripción no se borra ni se edita, solo se revoca una vez
(trigger de `db/043`). El refresh se rota en cada uso y, si un refresh ya
usado reaparece, se revoca la sesión entera. Correo transaccional
(verificación y restablecimiento) con Proton Mail por SMTP: envío SMTP
oficial (`smtp.protonmail.ch`, token SMTP, dominio propio) o Proton Mail
Bridge (servicio opcional `protonmail-bridge`, perfil `proton-bridge`, de
[shenxn/protonmail-bridge-docker](https://github.com/shenxn/protonmail-bridge-docker)).
Guía para la app:
[docs/app_api_flutter.md](docs/app_api_flutter.md).

El nivel público **no lleva auth a propósito**. Un comprador escéptico tiene que
poder auditar tu historial sin registrarse. Si le pides email para ver si eres
de fiar, no vuelve.

### Dos paneles, no uno

Son cosas distintas y conviene no mezclarlas:

**Grafana (`panel.tudominio.com`) — privado, solo tú.** Operación del sistema:
salud de la ingesta, CLV rodante, calibración, crecimiento del histórico de
cuotas, cadena de hashes. Se conecta directo a Postgres con un usuario de solo
lectura. Gratis, ya provisionado en este repo.

**Página pública de track record — tu argumento de venta.** No la hagas con
Grafana: necesita tu marca, tu dominio, tu copy y estar embebida en tu web de
ventas. Consume `/track-record`, `/calibration` y `/chain`.

La regla: Grafana sirve para mirar tu sistema, no para vender tu producto.

**Panel `/control` — administración del negocio.** Dashboard con KPIs de
clientes, suscripciones y operación; fichas de cliente (conceder o revocar
planes, suspender, cerrar sesiones), planes y precios, auditoría inmutable
(`admin_audit`) y la vista de sistema de solo lectura. Hecho con
[Tabler](https://github.com/tabler/tabler), [Tabler Icons](https://github.com/tabler/tabler-icons)
y [Chart.js](https://github.com/chartjs/Chart.js), servidos desde el propio
dominio (`src/qf/api/static/vendor/`) con CSP `'self'`. Cada formulario lleva
token CSRF (Basic auth viaja sola en cada petición). El pipeline sigue siendo
intocable desde aquí: el panel no lanza jobs ni publica picks.

---

## Arranque

### Día 1 — antes que cualquier otra cosa

El worker de cuotas. Cada día que no corre es un día de datos irrecuperable, y
es el insumo del CLV, del backtest realista y del producto de fase 5.

```bash
git clone <tu-repo> && cd quantfut
cp .env.example .env && nano .env
export PG_PASSWORD='...' GRAFANA_PASSWORD='...' GRAFANA_DB_PASSWORD='...'
./scripts/setup_fase1.sh
docker compose up -d
```

`setup_fase1.sh` corre los 6 pasos en orden y **se detiene** en el paso 4 hasta
que dejes vacía la lista de nombres sin emparejar. Esa parada es intencional:
un equipo sin emparejar son partidos que el sistema nunca verá, sin dar ningún
error.

### Puertas de avance

No pases de fase sin cumplir la puerta. Es la única defensa contra construir
seis meses sobre un modelo que no funciona.

| Fase | Puerta |
|---|---|
| 0 | 7 días seguidos capturando cuotas sin intervención |
| 1 | 30 días publicando predicciones verificables sin tocar nada |
| 2 | Calibración plana en todos los deciles y RPS cerca del cierre |
| 3 | 90 días de track record público verificable |
| 4 | CLV positivo en 300+ picks |

En la fase 2, **si el backtest te da ROI de dos dígitos, hay una fuga**.
`check_leakage()` busca las tres más comunes; no encontrar nada no garantiza que
no las haya.

---

## Calendario de procesos

| Proceso | Frecuencia | Módulo |
|---|---|---|
| Captura de cuotas (desde 2026-10-03 guarda también `book_updated_at`, cuándo cambió cada casa su precio) | cada 10 min | `qf.ingest.odds_worker` |
| Ráfagas 1X2 para medir la latencia de las casas blandas: T-6 h a T-15 min, ligas de `RAFAGAS_LIGAS`, tabla aparte `odds_rafagas`, tope `RAFAGAS_MAX_CREDITOS_MES` (3.000); se leen con `python -m qf.eval.latencia` | cada 5 min | `qf.ingest.rafagas` |
| Cuotas de API-Football (Bet365, Betano, 1xBet, William Hill + Pinnacle), tabla `af_odds_snapshots` | retirado el 25-oct (API-Football) | `qf.ingest.af_odds` |
| Sombra del criterio de picks: registra lo que se habría recomendado (no publica); se liquida con `qf.eval.clv` | cada hora, :25 | `qf.publish.shadow_sharp capture` |
| Calendario de partidos | 05:15 y 17:15 | `qf.ingest.fixtures` |
| Cierre de partidos + liquidación (guarda también `matches.stats` completo para las fichas, misma petición) | cada 3 h | `qf.ingest.results` |
| Clasificación de cada liga para las fichas de la web, calculada con nuestros resultados (sin peticiones), y escudos nuevos (una vez por equipo, volumen `escudos`, servidos en `/web/escudos/{team_id}.png`) | cada hora, :50 | `qf.ingest.standings` |
| Marcador en juego para la app: listado diario de FotMob, una petición por pasada y solo con partidos en ventana | cada 5 min | `qf.ingest.live` |
| xG histórico | retirado el 25-oct | `qf.ingest.xg_worldfootball` |
| Histórico de copas europeas | retirado el 25-oct | `qf.ingest.uefa_cups` |
| Alineaciones a T-60 (API-Football; las sustituye `sofascore_alineaciones`) | retirado el 25-oct | `qf.ingest.lineups` |
| Challenger de XI en sombra | cada 5 min, después de la captura | `qf.model.shadow` |
| Chequeo de salud | 07:00 | `qf.ingest.health` |
| Predicciones, picks, sellado, publicación (picks apagados con `PUBLISH_PICKS_ENABLED=0`: solo predice y sella) | 08:00 | `qf.publish.daily` |
| CLV de respaldo | 02:30, 10:30, 18:30 | `qf.eval.clv` |
| Resumen semanal público | lunes 09:00 | `qf.publish.weekly` |
| Verificación de la cadena | 06:00 | `qf.publish.hashchain verify` |
| Reentrenamiento | día 1 del mes | `qf.model.train` |
| Arranque sin modelo activo (sale en segundos si hay modelo o el mercado es viejo) | días 2-31, 01:05 | `qf.model.train --bootstrap` |

El job diario tiene un orden estricto: predecir → seleccionar → **sellar** →
publicar. Si el sellado falla no se publica nada ese día. Mejor no publicar que
publicar sin prueba.

### Evaluación de challengers

Para investigar **más picks sin cambiar el criterio publicado**:

```bash
PYTHONPATH=src python -m qf.eval.quote_coverage --days 30
PYTHONPATH=src python -m qf.eval.sharp_challengers
```

El primer comando lee el Postgres operativo y mide la primera cuota 1X2
completa *observada*, no la apertura real del mercado. El segundo usa solo
los CSV ya guardados en `.local/fd_cache`: compara Shin/Power y varios
umbrales sobre los mismos partidos; todos se miden contra el cierre justo de
Pinnacle calculado con Shin. Es un análisis histórico exploratorio, sin
disponibilidad de cuota al cliente ni autorización de publicación. Las
decisiones y los límites de la muestra están en `harness/progreso.md`.

`python scripts/evaluate_challengers.py --years 6 --validation-days 180 --compact`
ejecuta en **solo lectura** el walk-forward de Dixon-Coles, Elo secuencial,
comparación con Pinnacle, dos regresiones multinomiales y ablaciones de Elo,
descanso, forma y tiros. Requiere `PYTHONPATH=src` y la configuración normal de
Postgres. El resultado es JSON; ninguna métrica de un challenger lo activa.
Si las cuotas sharp terminan antes que los resultados, el experimento usa la
última ventana histórica con mercado completo y marca el resultado como no
apto para promoción actual.
La regresión anclada al mercado histórico usa cuotas de **cierre** y es solo
diagnóstica: para operar a T-60 hará falta entrenar de nuevo con snapshots de
cuotas disponibles en esa ventana.

En una base ya creada, aplicar `db/012_shadow_challengers.sql` antes de arrancar
el cron de sombra. `setup_fase1.sh` también lo aplica en una instalación nueva.
Las tablas `shadow_predictions`, `shadow_picks` y `shadow_results` son
independientes de las predicciones y picks publicados. El CLV de sombra solo se
calcula entre una cuota `post_xi` (T-45..T-15, solo con ambos XI capturados)
y una cuota de Pinnacle capturada en la ventana `close`; si no existe,
el registro queda pendiente y no se inventa un cierre. La puerta de promoción
exige al menos 300 selecciones liquidadas, un intervalo de CLV positivo, mejora
frente al modelo base a T-60 y evidencia en varias ligas.

---

## Lo que hace distinto a este sistema

| Pieza | Por qué está aquí |
|---|---|
| **Cadena de hashes SHA-256** | Prueba criptográfica de que no revisas predicciones. Es el producto, no un extra |
| **Triggers de inmutabilidad** | La base de datos te impide "corregir" un pick fallido aunque quieras |
| **CLV como métrica principal** | Converge en cientos de apuestas; el ROI necesita miles |
| **Shrinkage del edge (0.55)** | El edge crudo está sesgado al alza por selección adversa |
| **De-vig con Shin** | El reparto proporcional que usa todo el mundo calibra peor en underdogs |
| **Pricing en forma cerrada** | ~150 mercados por partido en 0.3 ms, sin GPU |
| **Trigger point-in-time** | La base rechaza cualquier feature con `as_of > kickoff` |
| **Emparejamiento con revisión manual** | Prefiere fallar y avisar antes que fusionar dos equipos distintos |
| **No degradar en silencio** | Un reentrenamiento peor que el activo no se despliega |

---

## Parley del día (desde 2026-10-11, apagado hasta el visto bueno)

Pestaña "Parley" y ruta pública `GET /parley`. Cada día (de 08:00 a 08:00
UTC, la jornada americana entera) se arman de 1 a 5 parlays, uno por escalón
de cuota total: ≈2,0 (1,90-2,20), ≈2,5 (2,20-2,70), ≈3,0 (2,70-3,40), ≈4,0
(3,40-4,30) y ≈5,0 (4,30-5,00). En cada escalón entra la combinación MÁS
PROBABLE de los mercados de la escalera (1X2, goles, goles por equipo, ambos
marcan, hándicap y córners/tarjetas validados), de 2 a 6 patas de cuota
de 1,20 a 1,80 (desde el sellado del 14-oct; antes ≥ 1,15 sin techo), un partido por parlay y ninguno repetido en el día. Reglas en
`src/qf/publish/parley.py`; diseño en
`docs/superpowers/specs/2026-10-11-parley-design.md`.

Lo que NO promete (decisión del usuario: solo probabilidad, sin filtro de
valor): el margen de la casa se paga en CADA pata y se multiplica; a la larga
los parlays pierden aunque acierten lo prometido. El historial publica
unidades y ROI a 1 unidad por parlay, también los perdidos.

**Pendiente (a la espera de más casos):** hoy el parley elige solo por probabilidad calculada; el acierto real por mercado solo sirve para pausar un escalón. Ponderar la elección por el acierto real de cada mercado queda para cuando haya ~50 liquidados POR mercado (el 2026-10-13 hay entre 5 y 41 en Alta probabilidad: con esos n, 73 % frente a 100 % puede ser azar). Ver `harness/tareas.md`, sección Parley.

- Se eligen antes de `seal()` y entran en el lote del día desde
  `LOTE_PARLEY_DESDE`: un parlay fuera de un lote sellado no se enseña.
- La búsqueda es una mochila sobre ln(cuota) con celdas de 0,2 % y sin podar
  patas "dominadas" (con techo de cuota la más barata puede ser la única que
  cabe): exacta salvo combinaciones pegadas al borde de un escalón (test
  contra fuerza bruta). Fuera las cuotas erróneas (`prob · cuota − 1 > 0,25`).
- Tickets y patas del día en una transacción con candado: nunca un ticket a
  medias, que sería inmutable. Pata no jugada a su hora original (±48 h):
  nula a las 48 h de esa hora, aunque `fixtures` la reprograme.
- Sin doble oportunidad: ningún proveedor capturado la cotiza.
- Una pata aplazada o devuelta cuenta ×1,00. El acierto se compara con la
  probabilidad EFECTIVA (producto de las patas que contaron), para que un nulo
  no haga parecer peor el escalón.
- Control por escalón como la alta probabilidad (50 liquidados, 10 semanas,
  IC99; fallo grosero z ≤ −4): un escalón que acierta por debajo de lo
  prometido se pausa solo.

## Reto escalera (desde 2026-10-08)

Pestaña propia en la web (`/escalera`): retos de 3 a 6 escalones que empiezan
con 10 unidades; cada escalón apuesta todo el saldo, ganarlos todos completa
el reto y fallar uno lo cierra. Puede haber varios abiertos a la vez (uno de
cada longitud): 3 por defecto, 6 como mucho 3 veces al mes, 4 y 5 cuando ya
hay otro abierto (decisión del usuario). Reglas en
`src/qf/publish/escalera.py`; cada escalón se sella en el lote del día antes
del partido (`LOTE_ESCALERA_DESDE`) y las tablas (`db/045`) son inmutables:
el saldo se deriva, no se guarda.

La regla de partida (cuota 1,25-1,40, retirar la inversión a ×2,5) se midió
antes de construir nada (`python -m qf.eval.escalera_prueba`, football-data,
7 ligas, 2019-2025, firma `d5cbc3151164`, mejor de bet365 y 1xBet):

| Escalones | Rango 1,25-1,40: completados · por reto | + cuota ≥ justa: completados · por reto (n) |
|---|---|---|
| 3 | 39,9 % · **−11,5 %** | 56 % · +29 % (25) |
| 4 | 31,0 % · −10,2 % | 48 % · +43 % (21) |
| 5 | 21,6 % · −19,0 % | 31 % · +21 % (16) |
| 6 | 15,3 % · **−26,2 %** | 31 % · +62 % (16) |

En el rango, la probabilidad está calibrada (72,3 % prometido, 72,5 % real)
pero cada escalón pierde −3,3 % por el margen, y la escalera lo multiplica.
Acortar sube los completados y no la ganancia esperada. Por eso solo se dan
escalones con cuota ≥ precio justo de Pinnacle sin margen; son pocos y la
muestra con filtro (75 escalones) no demuestra beneficio.

Hándicap asiático (protector incluido) como mercado de escalón, con la
probabilidad sacada del ajuste de goles de Pinnacle
(`python -m qf.eval.escalera_handicap`, mismo criterio que alta
probabilidad): pasan −1, −0,5, 0, +0,5, +1, +1,5 y +2; −1,5 no (66,7 %
prometido, 64,2 % real). Las cuotas de las casas en las líneas protectoras
llevan mucho margen (Santos +1,5 a 1,36 el 8-oct: −8 %): el filtro de valor
las descarta casi siempre.

### Escalera por probabilidad (desde 2026-10-08, decisión del usuario)

La escalera deja el filtro de valor: elige el pronóstico MÁS PROBABLE con
cuota 1,25-1,40 (con el filtro salían muy pocos). Con esa forma de elegir, el
histórico da −11,5 % por reto a 3 escalones y −26 % a 6: la web lo dice.
Mercados nuevos, cada uno solo en las líneas que pasaron la prueba de
calibración (`python -m qf.eval.escalera_estadistica [--goles]`, φ en
2019-21, encogimiento elegido en 2021/22, criterio solo en 2022-25):

- **Córners** (modelo estadístico de equipos y liga, `model/estadisticas_mercado.py`):
  pasan más de 7,5 / 8,5 / 9,5 y menos de 9,5 / 10,5 / 11,5.
- **Tarjetas** (amarillas + rojas, con árbitro): prometen 1-3 puntos de más;
  solo pasa menos de 6,5. El árbitro solo existe en la Premier en el
  histórico; desde el 8-oct se guarda de API-Football para todas las ligas.
- **Ambos marcan**: "sí" pasa (62,8 % prometido, 65,3 % real); "no" no
  (62,7 → 58,1).

Cuotas de esos mercados: bets 8, 45 y 80 de la respuesta de API-Football que
ya se pedía.
Desde el 2026-10-09 también más de 6,5 córners y córners de cada equipo
(local más de 1,5 / 4,5 / 5,5 y menos de 5,5; visitante más de 3,5 / 4,5 y
menos de 4,5 / 7,5), las líneas que pasan con el criterio de la escalera
(`python -m qf.eval.escalera_estadistica --fijos`). El modelo por equipo está
peor calibrado que el de totales (varias líneas fallan en el tramo 60-80 %).

**Revisión con los datos completos (2026-10-10).** Las pruebas del 8 y el 9 de
octubre perdían en silencio 2024/25 entera y la Premier 2021/22: esos CSV de
football-data traen BOM y, leídos en latin-1, la columna `Div` salía como
`ï»¿Div` (arreglado en `soft_vs_sharp.load_csvs`). Con 13.555 partidos en vez de
10.842 la escalera queda así: fuera más de 6,5 y 9,5 córners y visitante menos
de 7,5 (fallan en el tramo 70-80 %, justo el de la escalera); dentro menos de
4,5 y 5,5 tarjetas. Córners totales: más de 7,5 / 8,5 y menos de 9,5 / 10,5 /
11,5. El árbitro en Inglaterra (`python -m qf.eval.tarjetas_arbitro`, Premier +
Championship, árbitro en el 100 % de los partidos) mejora la pérdida
logarítmica de tarjetas solo 0,0011 por partido (z=1,07; en la Premier
empeora): no hay regla propia para Inglaterra.

**Probabilidad prudente en córners y tarjetas (2026-10-09, decisión del
usuario).** La primera vista previa con cuotas reales (madrugada del 9-oct)
habría abierto los 4 retos con «menos de 6,5 tarjetas» y «más de 7,5
córners», con el modelo 11-13 puntos por encima de la propia casa sin margen
(p. ej. 82 % frente a 69 %). Elegir el máximo entre cientos de candidatos
premia los errores del modelo hacia arriba, y la prueba histórica no puede
verlo: football-data no trae cuotas de esos mercados. Desde entonces cuenta
`min(modelo, mercado sin margen)` (`escalera_datos.prudente`; Pinnacle si
cotiza los dos lados, si no la media de las casas de la lista) y sin los dos
lados cotizados el candidato no entra. Tarjetas y árbitro históricos: `python -m qf.ingest.history_fd tarjetas`.

### Reto al 80 % en 7 días, con NBA y tenis (desde 2026-10-28, decisión del usuario)

El usuario pide que el reto ENTERO se cumpla al menos el 80 % de las veces, buscando
el acierto y no la cuota, con hasta 7 días para completarlo. Con escalones
independientes y calibrados, P(completar) = ∏ p, y con el mercado calibrado
probabilidad × cobro ≈ 1 − margen: un 80 % paga ≈ ×1,15. Regla (`escalera.py`):
2 escalones; cada uno exige p ≥ (0,80 / ∏ p elegidos)^(1/faltan) (89,4 % el primero;
con un 95 % el segundo basta con 84,2 %); como mucho 95 % en fútbol y NBA y 97 % en
tenis (lo calibrado); el más probable primero; cuota ≥ 1,03, sin freeroll; hasta 2
el mismo día en partidos distintos; 7 días como máximo y luego «expirado» (cobra su
saldo, no cuenta como cumplido). Un reto a la vez. `db/089`: `prob_objetivo` y
`dias_max` en `escalera_retos`; los retos anteriores (NULL) terminan con su regla.

NBA y tenis (`publish/escalera_ext.py`): ganador del partido leído del archivo
PropLine compartido sin peticiones nuevas; probabilidad de Pinnacle sin margen (sin
Pinnacle en la observación, el partido no entra); cuota, la mejor de `SOFT_BOOKS`;
liquidación con la calificación de PropLine de la casa del escalón (cada casa aplica
su regla de retiradas en tenis) y, sin ella, la de Pinnacle; nulo a las 72 h sin
calificar. El escalón guarda el evento de PropLine (`escalera_pasos.deporte`,
`evento_*`, sin `match_id`) y su resultado va con `fuente = 'propline'`, sin
marcador. En el archivo de prueba del 23-oct Pinnacle cotizaba 74 de 146 partidos de
tenis; de la lista, Bovada, Strendus y BetOnline (bet365 no está en PropLine).

Medido (`python -m qf.eval.escalera_multideporte`: football-data, NBA ganador al
cierre de bet365 vía BetsAPI, Tennis-Data ATP/WTA con Pinnacle sin margen y cuota de
bet365; el plazo cuenta desde el primer escalón):

| Datos | Retos | Cumplidos | Fallidos | Expirados | Días | Cobro | Por reto |
|---|---|---|---|---|---|---|---|
| Fútbol + tenis 2019-2025 | 539 | **85,9 %** | 10,6 % | 3,5 % | 2,0 | ×1,14 | +1,8 % |
| Fútbol + NBA + tenis oct-23 a may-25 | 230 | **84,3 %** | 14,8 % | 0,9 % | 1,6 | ×1,14 | −3,3 % |
| Solo fútbol (1X2 y goles 2,5) | 29 | 41,4 % | 6,9 % | 51,7 % | 5,0 | ×1,19 | +5,7 % |
| 3 escalones (fútbol + tenis) | 195 | 63,1 % | 7,7 % | 29,2 % | 4,2 | ×1,15 | +3,8 % |

Calibración del tenis (Pinnacle sin margen, 2019-2026): 90-95 % prometido 92,3 %, real
94,1 % (n=1.128); 95-100 %: 95,8 % y 98,0 % (n=201). Lo que más resta no son los
fallos sino quedarse sin segundo escalón: con solo fútbol expira la mitad. Ningún
resultado demuestra ganancia (−3 % a +2 % por reto). Literatura: Dubins y Savage
(apuesta audaz en juegos desfavorables), sesgo favorito-longshot (Snowberg y Wolfers
2010; tenis: Forrest y McHale 2007, Lahvička 2014; fútbol: Angelini y De Angelis 2019);
ninguno encuentra beneficio en cuotas bajas sin ventaja sobre el precio (Kaunitz et al.
2017).

## Línea de alta probabilidad (desde 2026-10-06)

Una línea aparte de los picks de valor, pedida por el usuario: los clientes
valoran acertar más que batir a la casa. Un pronóstico por partido, solo si
su probabilidad real está entre el 80 % y el 95 %. **Es una línea de acierto,
no de valor**: con las casas de los suscriptores estos resultados no tienen
valor esperado positivo (favorito ≥ 80 % en football-data 2019-2025: ROI
−2,4 %, EV al cierre −2,6 %). La web y `/alta-probabilidad` lo dicen.

- **Probabilidad:** siempre Pinnacle sin margen (Shin), nunca el modelo
  propio. 1X2 y doble oportunidad salen directos del 1X2; los goles (más de
  1,5 y menos de 3,5; "menos de 4,5" pasó la prueba pero se excluye por
  decisión del usuario, 2026-10-06, por pagarse a 1,09-1,17) y "marca el
  local / el visitante" (más de 0,5 goles de un equipo, 2026-10-07; prueba
  histórica 2026-10-07: local 86,97→88,52, visitante 86,10→87,45) salen de un
  ajuste Dixon-Coles que reproduce el
  1X2 y la línea de goles de Pinnacle (`model/market_anchor`, con push en
  líneas enteras y de cuarto). Es decir, la de goles y la de un equipo son
  probabilidades derivadas, no la cuota de Pinnacle de ese mercado. La cuota
  de referencia de "marca un equipo" sale de las casas blandas de
  API-Football (bets 16/17, misma respuesta que el 1X2).
- **Regla:** de los candidatos en [80 %, 95 %], el de MENOR probabilidad (el
  más informativo); el tope evita obviedades. Precio de Pinnacle de ≤ 6 h y
  ≥ 15 min antes del inicio; horizonte 36 h; un pronóstico por partido para
  siempre (`UNIQUE`).
- **Solo con cuota (desde 2026-10-25, decisión del usuario):** un candidato
  sin cuota de una casa de `SOFT_BOOKS` para ese mercado, lado y línea no
  entra, ni aquí ni en la ampliada; se descarta ANTES de elegir, así que el
  partido se queda con el siguiente que sí cotiza. La captura usada es la más
  reciente (≤ 6 h) que trae a Pinnacle y a alguna casa de los suscriptores:
  PropLine trae solo a Pinnacle casi todas las horas y las casas cada ~3 h, y
  la del 25-oct a las 08:00 UTC dejó 18 de 22 pronósticos sin cuota. "Marca
  un equipo" toma su cuota de la misma captura de PropLine (`_equipos`).
- **Prueba histórica** (`eval/alta_prob_calibracion.py`, 14.305 partidos,
  firma `d5cbc3151164`), con la regla desplegada el 2026-10-07 (sin "menos
  de 4,5", con "marca un equipo"): pronóstico en 9.021 de 14.216 partidos
  (63 %), prometido 82,62 %, real 83,23 %; todos los mercados y tramos pasan
  (la regla del 6-oct daba 84,45 / 84,60). Solo valida la línea 2,5 de goles (football-data no trae
  otras).
- **Sellado:** `daily` elige y guarda ANTES de `seal()`; el lote del día lleva
  el bloque `alta_probabilidad` desde `LOTE_ALTA_PROB_DESDE` (7-oct-2026).
  Una sola fuente de verdad, `hashchain.lote_lleva_alta`, la usan el lote,
  el job y la API: lo que no está en un lote sellado no se publica.
  Tablas inmutables `alta_prob_picks` / `alta_prob_results` (`db/040`).
- **Público:** `/alta-probabilidad` da la probabilidad a punto porcentual
  entero (con decimales permitía reconstruir el precio justo que usan los
  picks de valor); el lote conserva el valor exacto. Ojo si algún día se
  configura `CHAIN_GIT_REMOTE`: el lote publicado lleva la probabilidad
  exacta y el ajuste de goles.
- **Pausa automática:** con ≥ 50 liquidados, IC99 por semanas (mínimo 10
  semanas) de `acertado − prometido` entero bajo cero, o z ≤ −4 (fallo
  grosero, desde el principio). En conjunto y por grupo de mercado:
  "marca el local" y "marca el visitante" se vigilan como UN solo grupo
  (`team_totals`, decisión del usuario 2026-10-07) y, si se pausa, se
  excluyen los dos lados. Simulado (revisión final 2026-10-07, mezcla
  realista de mercados elegidos, 26 semanas): ~16 % de líneas con alguna
  pausa de grupo en falso y ~5 % con la línea entera pausada en falso; un
  déficit real de 3 puntos se detecta en ~82 % de las líneas (algún grupo) y
  ~73 % (la línea entera). Las cifras anteriores (9,7 % / 3 % / 88 %)
  suponían probabilidades uniformes y 4 grupos. Reanudar es decisión del
  usuario: `ALTA_PROB_CONTROL_DESDE`. Interruptor general `ALTA_PROB_ENABLED`.
- **Goles desde API-Football (2026-10-06):** a las 08:00 UTC el precio de
  ≤ 6 h suele venir de API-Football; `ingest/af_odds` guarda, con la misma
  petición, sus líneas de goles (todas las de Pinnacle; 1,5/2,5/3,5/4,5 de
  las casas de la lista; `db/041`), y la línea las lee de la MISMA respuesta
  que el 1X2. Prueba en vivo: goles en 15 de 22 partidos (antes 0).

- **Ampliación del 2026-10-09 (pedida por el usuario):** más de 2,5 goles,
  hándicap asiático (−1, 0, +1, +1,5, +2, del mismo ajuste de goles; una
  devolución no cuenta, la probabilidad es la de ganar sin devolución) y
  córners (menos de 11,5 y 12,5). Córners es la única excepción a "siempre
  Pinnacle": sale del modelo de córners recortado a la probabilidad sin
  margen de la propia casa (`min(modelo, mercado)`, como la escalera), y sin
  los dos lados cotizados no entra; si no hay estadística 72 h después, nulo.
  Ambos marcan se midió pero nunca llega al 80 % en las 7 ligas: no se publica.
  Más de 7,5 córners no pasó. Regla completa: pronóstico en 12.128 de 14.216
  partidos (antes 9.021), prometido 82,35 %, real 82,89 %. Migración `db/047`
  (mercados nuevos, resultados `push`/`void`, `valor` = córners).
- **Córners de cada equipo y más de 6,5 (2026-10-09, segunda ampliación):**
  mismo acumulador de córners, con un φ propio por equipo (1,5455, 2019-21);
  cuotas de API-Football bets 57/58 en la respuesta que ya se pedía (`db/048`).
  En alta probabilidad entran más de 6,5 totales, local más de 2,5 / 3,5 y
  menos de 7,5, visitante más de 2,5 y menos de 6,5. Regla completa: 12.557
  partidos, 81,89 % → 82,64 %. Ojo: dentro de lo elegido, "local más de 2,5"
  queda 3 puntos por debajo (n=680); lo vigila el control por grupo.
  Con los datos completos (2026-10-10, ver la escalera) "local más de 2,5"
  falla el tramo 80-85 % (82,84 → 81,35, n=3.368) y sale de alta probabilidad.

## La cadena de hashes en la práctica

Crea un repo público separado (`quantfut-registro-publico`), móntalo en
`CHAIN_DIR` y apunta `CHAIN_GIT_REMOTE` ahí. Cada día el sistema serializa
predicciones y picks a JSON canónico, calcula `payload_sha256`, encadena con
`chain_sha256 = sha256(prev_sha256 || payload_sha256)`, hace commit al repo
público (el timestamp de GitHub es el testigo externo) y publica los primeros
16 caracteres en Telegram.

```bash
python -m qf.publish.hashchain verify
```

Si alteras un carácter de una predicción pasada, todos los hashes posteriores
dejan de cuadrar. Eso es exactamente lo que quieres poder demostrar.

---

## Despliegue en Contabo

Desplegado el 2026-09-24 en `31.220.72.30` (Ubuntu 22.04, Docker ya
preinstalado por Contabo), código en `/home/qf/quantfut`, dominio
`pronosticosdeportivos.pro` detrás de Cloudflare (ver "Proxy con TLS").
Contabo tiene E/S de disco más lenta que Hetzner y no hace backups.

Lo aplicado en el host:

- Usuario `qf` (grupos `sudo`, `docker`), swap de 4 GB, `fail2ban`.
- `PermitRootLogin no` en `/etc/ssh/sshd_config.d/10-quantfut.conf` (se
  activa cuando `qf` tenga contraseña). El login por contraseña se mantiene
  para `qf` (decisión del usuario).
- `ufw`: solo 22 entrante. **ufw no filtra los puertos que publica Docker**
  (Docker inserta sus reglas antes), así que 80/443 se cierran aparte:
  `/usr/local/sbin/qf-cf-firewall` rellena la cadena `QF-CF` y la engancha a
  `DOCKER-USER` (IPv4 e IPv6) para que solo acepten conexiones nuevas desde
  los rangos de Cloudflare. Lo ejecuta `qf-cf-firewall.service` al arrancar y
  `cron.weekly` para refrescar los rangos; si la descarga falla, reutiliza la
  última lista en `/etc/qf-cf-ips-v4|v6`.
- `/etc/cron.daily/qf-backup`: `pg_dump -Fc` (el formato que lee
  `restore_db.sh`) a `/var/backups/quantfut`, 14 días. **Todavía sin copia
  fuera del servidor**: si el VPS se pierde, se pierden los backups.

Ajustes de Postgres para el disco de Contabo (sin aplicar aún):
`random_page_cost = 1.5`, `effective_io_concurrency = 100`,
`shared_buffers = 2GB`, `work_mem = 32MB`.

### Llevar la base local al servidor y arrancar (2026-09-23)

En vez de rehacer el backfill en el servidor (`setup_fase1.sh`, horas y alias
a mano), se restaura la base local, que ya tiene los partidos, las cuotas y
los alias revisados.

1. En local: `pg_dump -Fc --no-owner --no-privileges` → `quantfut.dump`, y un
   `.env.server` con hosts de compose (`db`, `cache`), rutas `/srv/quantfut` y
   secretos propios. Copiar el repo (sin `.venv`, `.local`, `pyton`), el
   volcado y el `.env.server` (como `.env`) al servidor.
2. En el servidor: `docker compose build`, luego
   `./scripts/restore_db.sh ~/quantfut.dump`: arranca Postgres, se niega a
   pisar una base con datos sin `--force`, restaura, aplica las migraciones
   014-020 (idempotentes) y arregla el rol de Grafana (el `004` lo crea con una
   contraseña por defecto que no es `GRAFANA_DB_PASSWORD`).
3. `docker compose up -d`, entrenar el primer modelo
   (`docker compose exec worker python -m qf.model.train`, ~3,5 h en el VPS
   de 4 vCPU: sin modelo activo el job de las 08:00 falla) y cargar el
   calendario (`python -m qf.ingest.fixtures`). Con una base restaurada cuyo
   último cierre sharp tiene más de 30 días, ese primer modelo se guarda
   **sin activar**: la puerta exige mercado reciente. No hay que forzarlo; el
   job `train --bootstrap` (diario, 01:05 UTC) entrena solo cuando no hay
   modelo activo y los cierres capturados en vivo ya pasarían esa
   comprobación, y si no, sale en segundos.

**Dos fallos del cron del contenedor corregidos antes del primer despliegue**,
ambos mudos: el worker copiaba a `/etc/environment` solo ciertos prefijos y
dejaba fuera `API_FOOTBALL_*` (calendario, resultados, alineaciones, lesiones
y cuotas de API-Football habrían fallado siempre), y el crontab no fijaba
`PATH`, con lo que cron no encontraba `python` en `/usr/local/bin`. Para
comprobar que el cron funciona: `docker compose exec worker tail
/var/log/af_odds.log` pasada la hora y 20.

### Proxy con TLS

Cloudflare hace de proxy (registros `A` de `@`, `www`, `api` y `panel` con
nube naranja) con SSL **Full (strict)**. Caddy sirve el *Origin Certificate*
de Cloudflare, montado desde `/etc/ssl/quantfut/` del host (fuera del repo,
válido hasta 2041); no pide certificados a Let's Encrypt.

Dos cosas que cambian por tener Cloudflare delante, ambas en el `Caddyfile`:

- **IP del cliente.** Caddy ve siempre una IP de Cloudflare. Con
  `trusted_proxies` (rangos de Cloudflare) y `client_ip_headers
  CF-Connecting-IP` recupera la real, y la pasa a la API como
  `X-Forwarded-For: {client_ip}`. Sin eso, el rate limit de `main.py`
  contaría por nodo de Cloudflare y no por visitante.
- **Acceso de operación.** Ya no se filtra por IP (`GRAFANA_ALLOWED_IP`
  desaparece): `panel.`, `/control` y `/admin` los protege **Cloudflare
  Access** (Zero Trust). Caddy responde 404 si la petición no trae
  `Cf-Access-Jwt-Assertion`, es decir, si no pasó por Access. Solo se
  comprueba que la cabecera exista, no su firma: es suficiente porque el
  origen solo acepta tráfico de Cloudflare y la reescritura de `Host` hacia
  un origen ajeno no está disponible fuera del plan Enterprise. `/control`
  exige además su propio usuario y contraseña (`ADMIN_CONSOLE_USER` y el hash
  de `python scripts/hash_admin_password.py`); sin ellos responde 503. El
  hash lleva `$` (formato `pbkdf2_sha256$iteraciones$sal$digest`): en el
  `.env` que lee `docker compose` hay que escribirlo con `$` doblado
  (`$$`), o `docker compose` los interpreta como interpolación de variables
  y corta el valor en el primer `$` sin más aviso que un "variable is not
  set" que no señala dónde está el problema.

`reverse_proxy` apunta a los nombres de servicio (`api`, `grafana`), no a
`localhost`: Caddy los resuelve por la red interna de Docker Compose.

---

## APIs y costes

| Servicio | Plan | Coste | Para qué |
|---|---|---|---|
| The Odds API | 20K créditos | $30/mes | Cuotas, Pinnacle, Betfair Exchange |
| Fuentes vigentes | ver «Fuentes de datos vigentes» | — | PropLine, FotMob, SportsAPIPro, SofaScore, ERA5 |
| football-data.org (v4) | `qf.ingest.fdorg_respaldo` | gratis, 10 peticiones/min | testigo de calendario y resultados en 10 ligas; solo avisa, nunca escribe en `matches` |
| VPS Contabo | 4 vCPU / 8 GB | ~$9/mes | Todo |
| Dominio + backups | — | ~$2/mes | — |
| **Total** | | _pendiente de recalcular_ | Las fuentes de pago retiradas ya no cuentan |

**The Odds API cobra en créditos, no en llamadas**: cada llamada cuesta
`n_mercados × n_regiones`.

**Recálculo con las 13 competiciones (2026-09-22, con clave real).** Ya no es
una estimación: se leyó el calendario anunciado de las 13 competiciones con el
endpoint `/events` (que cuesta 0 créditos) y se simuló `_pending_windows` sobre
esos partidos reales. Una llamada por (competición, ventana, bucket de 10 min
en que algún partido entra en esa ventana), que es exactamente lo que hace el
worker con el cron `*/10`:

| configuración | créditos/llamada | créditos/mes |
|---|---|---|
| `eu` × `h2h` | 1 | ~1.935 |
| `eu` × `h2h,totals` | 2 | ~3.870 |
| `eu` × `h2h,totals,spreads` | 3 | **~5.800** ← en uso desde 2026-09-23 |
| `eu,us` × `h2h,totals,spreads` | 6 | ~11.610 |

~1.935 llamadas/mes. La cifra de ~2.160 créditos que figuraba aquí para 7 ligas
se quedaba corta por un factor de cinco: el coste no lo manda el número de
partidos sino **cuántos huecos de 10 minutos distintos** hay, y repartir los
mismos partidos entre más competiciones los dispersa. LaLiga y la Serie A, con
20 partidos en 14 días, salen más caras que la MLS con 33, porque la MLS
concentra kickoffs. Las copas son las más baratas: juegan todas a la vez.

Consecuencias: el plan de $30/mes (20.000 créditos) **sí** cubre las 13
competiciones con los tres mercados, pero con 1,7× de margen, no "de sobra"; y
el plan gratuito de 500 no alcanza ni en la configuración más barata, así que
con él el worker se ejecuta a mano para demostrar el motor, nunca desde el
cron. La región `eu` es la que trae Pinnacle y Betfair
Exchange, que son la referencia sharp de todo el sistema. Nunca la quites.

**Configuración vigente (2026-09-23): plan de 20.000 créditos, solo `eu`.** La
región `us` duplicaba el coste sin aportar casas que usen los suscriptores. Con
`eu` × tres mercados el worker en vivo gasta ~5.800 créditos/mes y quedan
~14.000 para el endpoint histórico (`/v4/historical/...`, solo en planes de
pago, datos desde junio de 2020, snapshots cada 5 min desde septiembre de
2022, **10 créditos** por mercado y región en cada llamada). Ese histórico es
lo que permite validar el criterio de selección en Liga MX, Argentina, Brasil
y MLS, donde football-data solo trae cierre.

> Etapa anterior: API-Football se retiró el 25-oct-2026 (ver «Fuentes de datos vigentes»). Lo que sigue describe esa etapa.

**El plan de API-Football decide si el sistema puede operar, y no por la
cuota.** Lo que descarta el plan Free no son sus 100 peticiones diarias sino
que solo da acceso a las temporadas **2022–2024**: pedir la temporada en curso
devuelve `Free plans do not have access to this season`. Sin temporada en curso
no hay calendario (`ingest/fixtures.py`), y sin calendario no hay ventanas de
cuotas, ni alineaciones a T-60, ni CLV. Sirve para verificar IDs de competición
y formas de respuesta, nada más.

Contratado el plan **Pro** (2026-09-22): 300 req/min, 7.500/día y temporada en
curso incluida. Los límites del plan viven en `API_FOOTBALL_RPM` y
`API_FOOTBALL_DAILY` porque el cliente deriva de ellos su intervalo entre
llamadas; con los valores del Free puestos contra un plan Pro el sistema
funciona igual, solo que 30 veces más lento de lo que podría.

Consumo real de la ingesta operativa, muy por debajo del plan: 13 llamadas por
pasada de calendario (2/día), 1 por partido terminado y 1 por partido en la
ventana de alineaciones.

**22-oct-2026: el plan volvió al Free** y desde entonces no entraron resultados
ni calendario (76 partidos sin cerrar al detectarlo el 24-oct; el chequeo diario
seguía en verde). Decisión del titular (24-oct): **sustituirlo**. Con
`RESULTS_PROVIDER=propline`, `fixtures` y `results` leen `/scores` del archivo
compartido de PropLine (`ingest/propline_partidos.py`, sin peticiones; córners
del box score) y el xG, tiros, tarjetas y árbitro salen de SofaScore vía Apify
(`ingest/sofascore_partidos.py`, solo las 13 ligas con modelo, tope 15 USD/mes y
40 partidos/día). PropLine publica a veces el mismo cruce con local y visitante
invertidos: el calendario nunca crea un partido si ese cruce ya existe en
cualquier sentido, y un resultado solo se aplica a un evento con los dos equipos
en su lado. SofaScore solo escribe si su marcador coincide con el nuestro, lo que
de paso verifica a PropLine. Comprobado con peticiones reales el 25-oct:
- API-Football responde `Free plans do not have access to this season` y agota
  sus 100 peticiones diarias: clasificación parada desde el 22-oct 06:40 UTC y
  marcador en vivo desde el 22-oct 20:00; las bajas solo entran en la primera
  pasada tras el reinicio del cupo (40-70 partidos al día).
- FotMob cubre alineaciones y bajas previas en las 13 ligas con modelo (63/63
  partidos del 23-24 oct con captura previa, 53 con el once oficial antes del
  inicio) y en ninguna de las otras 10.
- SofaScore sí publica xG de las ligas con modelo, Argentina incluida (Talleres
  0,77 – Defensa y Justicia 0,78, 24-oct); partidos de abril de 2026 no lo tenían.
  El histórico SofaScore cargado tiene 0/30 con xG en Premier, LaLiga, Serie A,
  Bundesliga, Ligue 1, Eredivisie y Primeira pese a que la fuente lo publica: revisar esa carga.
- PropLine no tiene Ligue 2 ni la Superliga danesa (catálogo de 36 competiciones): el titular las retiró de los
  motores el 25-oct (db/086, desactivadas con su historial sellado intacto).
- Fuentes desde el 25-oct (decisión del titular): SofaScore vía Apify (rl1987 fútbol, scrapesage NBA y tenis;
  `azzouzana` sigue roto), PropLine y FotMob como complemento. Conectado el 25-oct: once previsto y bajas de SofaScore;
  clasificación calculada con nuestros resultados (contra la última foto de API-Football coincide equipo a equipo en las
  19 ligas, salvo las sanciones de puntos, que van a mano en `standings.SANCIONES`); marcador en vivo del listado diario
  de FotMob (una petición cada 5 min: el `/scores` de PropLine también lo tiene, pero cada consulta sale del presupuesto
  diario compartido, que ya va justo con las cuotas). Ningún job de API-Football queda en el cron.

**xG de API-Football habilitado el 12-oct-2026, por decisión del usuario.**
La exclusión anterior queda revocada. Su cobertura sigue siendo variable:
una respuesta vacía o un valor null no se convierte en cero. Se conserva
la primera pareja válida con su fecha real y se reconsulta el dato tardío;
ver la sección de conexión al entrenamiento más abajo.

**El endpoint `/injuries` tiene el mismo problema de cobertura silenciosa,
verificado 2026-09-22 contra las 13 competiciones con clave real.** 10 de 13
devuelven datos con normalidad (por `league`+`season` actual y por `fixture`).
Tres NO: `mx.liga_mx`, `ar.primera` y `pt.primeira` devuelven 0 resultados
para la temporada 2026 en curso —tanto agregado por liga como por partido
concreto— a pesar de tener partidos terminados de sobra esa misma temporada
(79, 400 y 62 respectivamente), así que no es que no haya lesionados: el
proveedor simplemente no tiene el dato para esas tres ligas este ciclo. Con
`season=2025` (temporada anterior, ya cerrada) sí hay datos, lo que descarta
un parámetro mal puesto. `src/qf/ingest/injuries.py` sigue llamando al
endpoint para las 13 —no hay forma de distinguir "liga sin cobertura" de
"liga sana sin bajas" sin acumular ciclos y comparar—, pero cualquier feature
de disponibilidad que se construya encima debe tratar esas tres ligas como
dato ausente, no como "sin lesionados".

**Y no raspes FBref directamente.** Está detrás de Cloudflare y devuelve 403
("Just a moment...") incluso cuando `soccerdata` intenta evadirlo con un
navegador automatizado. Como fuente operativa no es fiable (el módulo que lo
intentaba, `xg_fbref.py`, y su dependencia `soccerdata` se retiraron el
2026-09-24).

El xG se toma de los datasets que `JaseZiv/worldfootballR_data` publica en sus
releases de GitHub: son los mismos datos de FBref ya raspados, se descargan por
HTTPS normal en segundos y sin clave (`qf.ingest.xg_worldfootball`). Hay **dos
rutas, y son disjuntas a propósito**:

| ruta | release | qué trae | ligas |
|---|---|---|---|
| tiro a tiro (`.csv`) | `fb_match_shooting` | xG, remates, a puerta, PSxG, distancia, minuto | las 7 con fichero de tiros |
| partido (`.rds`) | `match_results` | solo el xG agregado | `ar.primera` |
| copas (`.rds`) | `match_results_cups` | resultado + xG + árbitro | `eu.ucl`, `eu.uel` |

Límites conocidos: no hay Parquet, los releases de resultados y de copas **no
publican ni un CSV** (de ahí la dependencia `pyreadr`), y los datasets se
publican por lotes, así que van por detrás del presente. Sirven para entrenar
con histórico, no para cerrar el xG del partido de anoche.

**Corrección (2026-10-02): no van "por detrás", están PARADOS.** Ningún
fichero que usamos se ha actualizado después del 18-sep-2025 (fecha de
`updated_at` de los assets en GitHub). Último xG guardado por liga: Premier y
Argentina sep-2025; LaLiga, Serie A, Bundesliga y Ligue 1 feb-2025;
Eredivisie y Primeira ene-2025; Brasil, Liga MX y MLS dic-2024. Las copas
(`match_results_cups`) acaban en dic-2024 y con ellas los RESULTADOS de
Champions y Europa League: en la base no hay ni un partido de copa entre
dic-2024 y los programados de oct-2026. El job semanal responde `ok` con 0
filas, así que nada lo detectaba. Consecuencias: desde esas fechas el modelo
entrena solo con goles (Dixon-Coles cae a goles cuando el xG es NaN), y el
término de fuerza entre ligas no veía ningún partido de copa de 2025/26.

**Copas recuperadas (2-oct-2026)** desde API-Football:
`python -m qf.ingest.fixtures --copas-ensayo 2024-12-13 2024 2025 2026`
(no escribe) y luego `--copas` con los mismos argumentos. 351 partidos (215 de
Champions, 136 de Europa League), cerrados por `results.close_recent()` con
marcador y estadísticas, sin xG. Solo entran partidos con los DOS equipos en
el catálogo por coincidencia exacta; ningún equipo se da de alta en copa. Y
`health.check_xg_freshness()` mira ahora el dato y no el job: las 13
competiciones paradas quedan reconocidas hasta el 1-nov-2026, y desde
entonces vuelven a alertar si no se ha decidido la fuente de xG.

---

### xG reciente conectado al entrenamiento (12-oct-2026)

Por decisión del usuario se adopta API-Football para el xG reciente. El cierre
guarda la primera pareja válida en `home_xg`/`away_xg`, sin peticiones extra,
con `xg_source=api_football` y la fecha real de recepción en `xg_recorded_at`.
La captura diaria vuelve a pedir los terminados sin xG de los últimos 35 días:
máximo 100 consultas, espera de 20 horas entre intentos y reserva del 15% de
cuota. No se reemplazan el xG previo ni las observaciones ya guardadas.

El entrenamiento incorpora origen y timestamp al dataset y su hash. Dixon-Coles
y más-menos usan este xG solo cuando ya existía en el corte evaluado; el replay
secuencial de Kalman conserva goles para esta fuente hasta implementar llegadas
tardías. La recepción original del histórico previo sigue sin acreditarse.
La conexión no activa otro modelo ni demuestra rentabilidad. Detalle operativo
y comprobaciones: [docs/xg_api_football_20261012.md](docs/xg_api_football_20261012.md).

El entrenamiento `2026.10.12-221104` terminó el mismo día a las 20:55 CDMX:
49.504 partidos y 148 parejas de la nueva fuente, pero no superó la puerta
frente a Elo. El candidato queda registrado inactivo y continúa
`2026.09.27-010508`. Resultado verificado:
[docs/entrenamiento_xg_20261012.md](docs/entrenamiento_xg_20261012.md).

### Archivo FotMob integrado a las tablas principales (14-oct-2026)

Primera fase de llevar al motor las señales que estaban archivadas (spec:
[docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md](docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md)).
`qf.ingest.archivo_a_matches` rellenó solo columnas vacías de `matches`: amarillas
y rojas (huecos 8.412 a 294), marcador al descanso (7.325 a 240), xGOT, árbitro de
FotMob y sede con coordenadas (tabla `estadios`, 758 sedes), con la procedencia de
cada campo en `matches_enriquecimiento`. No cambia el modelo activo ni las
predicciones; usar estas columnas en el motor es de las fases siguientes. FotMob
cuenta las tarjetas un poco distinto (~6 % de partidos, +1), que mueve las
probabilidades de tarjetas en ligas con poco historial. Detalle y reversión:
[docs/f0_archivo_a_matches_20261014.md](docs/f0_archivo_a_matches_20261014.md).

**Tarjetas a cero de FotMob (corregido el 25-oct-2026).** En Argentina, Brasil y
parte de México, FotMob deja el bloque de estadísticas de tarjetas en `[0, 0]` en
2026 aunque la cronología trae cada tarjeta: el relleno guardó ceros falsos (media de
la liga argentina de 5,0 a 0,5 tarjetas) y el modelo de tarjetas llegó a dar 1,7 en
un Independiente–Boca, con «menos de 6,5» al 100 %. Ahora, si el bloque trae las
amarillas a cero (a veces con la roja bien), `extraer` cuenta la cronología para las
cuatro columnas (sin las del cuerpo técnico; doble amarilla = roja), y si la cronología
no tiene descanso o trae un tipo desconocido deja NULL. `--reparar-tarjetas` corrigió 776
partidos ya guardados (ar 409, br 279, mx 83 y 5 de otras ligas) en dos pasadas: 607 con
las cuatro a cero y 169 con amarillas a cero y alguna roja; 150 siguen igual porque la
cronología coincide (sin amarillas). Contra API-Football, la
cronología sin cuerpo técnico coincide en amarillas en ~92-97 % de partidos y en rojas
en ~99 %.

### Capa de ajuste por bloques de señales (14-oct-2026)

`qf.model.ajuste` decide qué señales entran al motor principal: un bloque se acepta
solo si mejora al modelo sin él, sobre las mismas filas, en RPS, log-loss y ECE, en
al menos 2 ligas y con una mejora significativa de RPS (remuestreo pareado). La
puerta antigua dejaba pasar ruido puro en 8 de 40 pruebas y atribuía al primer
bloque el mérito de re-nivelar las lambdas; ambas cosas están corregidas. Con
datos reales, el XI simple pasa: RPS 0,2133 a 0,2120 y 9 de 12 ligas mejoran, aún
en sombra hasta que haya CLV y sello tardío. Detalle:
[docs/f1_capa_de_ajuste_20261014.md](docs/f1_capa_de_ajuste_20261014.md).

### Cierres de Pinnacle: de 6.185 huecos a 2.103 (15-oct-2026)

Football-data ya no trae Pinnacle de Europa ni puede rellenar nada más; el cierre histórico faltante se
compra a The Odds API (10 créditos por snapshot de 5 minutos antes del inicio, que sirve a todos los
partidos con la misma hora). Una primera fase de 8.000 créditos añadió 1.164 cierres validados (RPS 0,1987
con esas cuotas, coherente con un mercado real); quedan 697 huecos en las 13 ligas modeladas. Las cuotas
`oddspapi_reconstructed` no son cierres sino precios de 60 minutos antes. Detalle:
[docs/f2_cierres_pinnacle_20261015.md](docs/f2_cierres_pinnacle_20261015.md).

## Expectativas realistas

- Un ROI sostenido de **1-4% sobre el volumen** es un resultado profesional
  fuerte en fútbol.
- Para distinguir un ROI de 2% de cero hacen falta **miles de apuestas**. Por
  eso `summary()` devuelve siempre el intervalo de confianza bootstrap, y por
  eso el CLV va primero en todos los reportes.
- Si tu CLV medio es negativo durante 300+ picks, el modelo no tiene edge.
  Mejor saberlo en el mes 3 que en el año 2.
- **Corregido (2026-09-22):** este README afirmaba que Liga MX, Brasileirão y
  Argentina "no tienen xG en las fuentes gratuitas" y que eso estaba en el
  `model-card` "a propósito, no es un error a arreglar". Era falso para las
  tres: vía `worldfootballR_data` hay xG para todas (Argentina por otra ruta,
  ver el punto siguiente).

  Lo que de verdad limita la cobertura **no es la liga sino la fecha en que
  FBref empezó a cubrirla**. Medido sobre el histórico cargado:

  | liga | primer xG | cobertura total |
  |---|---|---|
  | gb.premier_league | ago 2017 | 64.4% |
  | it.serie_a | ago 2017 | 63.0% |
  | es.laliga | ago 2017 | 62.9% |
  | de.bundesliga | ago 2017 | 62.5% |
  | **ar.primera** | ene 2017 | **62.5%** |
  | fr.ligue_1 | ago 2017 | 61.9% |
  | pt.primeira | ago 2018 | 51.6% |
  | nl.eredivisie | ago 2018 | 45.1% |
  | mx.liga_mx | jul 2018 | 44.9% |
  | us.mls | 2018 | 44.0% |
  | br.serie_a | abr 2019 | 41.8% |

  Que no es un asunto de continente lo demuestra la Eredivisie: es europea y
  tiene la misma cobertura que Liga MX. El corte separa las tres grandes, que
  FBref cubre desde 2017, del resto, que cubre desde 2018-19. Las columnas de
  cobertura total salen bajas solo porque el histórico arranca en 2014, antes
  de que existiera el dato.

- **Corregido otra vez (2026-09-22): Argentina SÍ tiene xG.** La línea de
  arriba decía 0%. Ahora está al 62,5%, por encima de las otras tres ligas
  latinoamericanas.

  El razonamiento anterior no era falso, era obsoleto: Argentina solo existe en
  `.rds`, leerlo exige `pyreadr`, y no compensaba pagar esa dependencia por una
  sola liga. Lo que cambió es el otro lado de la balanza. Champions y Europa
  League **tampoco** tienen CSV en ese repositorio, así que añadirlas obligaba
  a `pyreadr` de todos modos. Con la dependencia ya dentro, Argentina entró
  gratis: 2.304 partidos con xG en una sola pasada.

  La lección, que es general: una decisión de "no compensa" caduca en cuanto
  cambia el coste de la alternativa. Merece la pena re-revisar las que están
  escritas en los módulos cuando el alcance se amplía.

  Lo que Argentina sigue sin tener es el fichero **tiro a tiro**: solo el xG ya
  agregado del partido. Así que no tiene PSxG, ni distancia de remate, ni
  ajuste por estado del partido (`ingest/game_state.py`). Sigue siendo la liga
  con menos features, pero ya no la liga sin xG.

  Para los partidos anteriores a esas fechas el modelo trabaja solo con goles,
  que tienen más ruido, y **eso sí** está en el `model-card`.

- Los datasets de `worldfootballR_data` se publican por lotes y cada liga va
  con distinto retraso (a fecha de hoy, Premier llega a septiembre de 2025;
  Liga MX y Brasileirão, a diciembre de 2024). Afecta solo al ENTRENAMIENTO:
  el xG es el objetivo del modelo de fuerza, no una feature de predicción, así
  que un partido futuro no necesita xG para ser predicho.

- **El xG es el mejor objetivo disponible, y está comprobado.** Del mismo
  fichero tiro a tiro se extraen también remates, remates a puerta, PSxG y
  distancia media (`db/006_shot_stats.sql`). Probando cada variante como
  objetivo del modelo de fuerza sobre n=28.718:

  | objetivo | RPS |
  |---|---|
  | goles + xG (el actual) | **0.20330** |
  | goles + media(xG, PSxG) | 0.20340 |
  | goles + PSxG en vez de xG | 0.20368 |

  El PSxG **empeora**. Es coherente: solo cubre los remates que van a puerta,
  así que como medida de creación de ocasiones está sesgado, y además mezcla
  la colocación del disparo, que es más ruidosa que la calidad de la ocasión.
  No busques mejoras por ahí.

  Lo que sí aportó exprimir ese fichero: Liga MX y Brasileirão pasaron de
  **cero** datos de remates a tenerlos (el formato "extra" de
  football-data.co.uk no los trae), y quedan disponibles para el modelo de
  residuo y para trabajo futuro aunque el modelo de fuerza no los use.

- **El ajuste por estado del partido tampoco mejora, y el motivo es
  instructivo.** `ingest/game_state.py` reconstruye el marcador minuto a
  minuto desde los remates y calcula el xG que cada equipo generó ganando,
  empatando y perdiendo. La premisa habitual es que un equipo que va ganando
  se repliega y su xG infravalora su calidad. **Los datos dicen lo contrario**
  (12.928 partidos reconstruidos):

  | estado | xG por minuto (empate = 1.0) |
  |---|---|
  | perdiendo | 1.135 |
  | empatado | 1.000 |
  | **ganando** | **1.177** |

  Ir ganando está **correlacionado con ser mejor equipo**, así que el estado
  "ganando" no mide repliegue: mide calidad. Normalizar por ese ratio elimina
  justamente la señal de fuerza que el modelo busca, y el RPS empeora
  (0.20330 → 0.20344 en total; 0.20075 → 0.20108 restringiendo a los partidos
  con ajuste disponible). Hacerlo bien exigiría estimar el efecto de estado
  DENTRO de estratos de calidad de equipo, o conjuntamente con el modelo de
  fuerza; a la vista del tamaño del efecto no compensa.

  El módulo se conserva porque la reconstrucción del marcador sí es útil como
  *feature* del modelo de residuo (algo distinto de usarla para corregir el
  objetivo) y porque su validación contra autogoles es infraestructura
  reutilizable: el marcador se deriva de los remates que acabaron en gol, y un
  autogol no es un remate del que anota. En el 7,8% de los partidos la
  reconstrucción no cuadra, y ahí se devuelve `None` en vez de un estado
  inventado.

---

## Estructura

```
db/              001 esquema · 002 ligas · 003 (tablas de la primera fuente de alineaciones) · 004 Grafana
                 005 alias de FBref (revisados a mano, ver el propio archivo)
                 006 estadísticas de remates
                 007 MLS + copas europeas (competición != liga del equipo)
                 008 alias de MLS · 009 alias de Argentina
                 010 Bundesliga, Ligue 1, Primeira · 011 sus alias
                 012 tablas de challengers en sombra
grafana/         provisioning + dashboard de operación
scripts/         setup_fase1.sh · bootstrap_aliases.py · crontab
                 evaluate_challengers.py (evaluación de solo lectura)
                 harness_check.sh  (sintaxis + tests + compose, antes de tocar nada)
tests/           casos sobre datos simulados: recuperación de parámetros,
                 ausencia de fugas point-in-time, unidades del stake
src/qf/
  ingest/        odds_worker · fixtures · results · health
                 propline_*         cuotas, cierres, resultados y calendario de PropLine
                 fotmob_*           captura, alineaciones y resultados de FotMob
                 sportsapipro_alineaciones  huecos de once y bajas
                 sofascore_carga    escribe bajas y once con ids de SofaScore
                 lineups            disponibilidad de titulares (`availability`)
                 game_state         xG por estado del marcador (ver arriba)
  model/         dixon_coles   efectos por liga + fuerza relativa entre ligas
                 kalman        ratings dinámicos (estado latente)
                 elo           baseline secuencial 1X2
                 features      descanso, Elo, forma y tiros point-in-time
                 multinomial   challengers deportivos y anclados a Pinnacle
                 lineup_challenger · shadow · promotion
                 structure     formas alternativas de la matriz (solo informe)
                 calibration   corrección afín sobre las lambdas
                 meta          peso óptimo modelo/mercado
                 residual      GBM sobre el residuo (desactivado por defecto)
                 pricing · devig · train
  publish/       daily · picks · hashchain · telegram · weekly
  eval/          clv · metrics · backtest · comparison
  api/           main (público + servicio + admin) · cuentas (/app/v1, clientes)
                 panel (/control, Jinja2 + Tabler) · console (auth y vista de sistema)
  comercial/     cuentas y sesiones · suscripciones · métricas del panel · entrega de picks
  normalize.py   emparejamiento de nombres entre fuentes
```

### Un equipo puede estar en el modelo sin estar MEDIDO

Distinción que cuesta dinero si se pasa por alto, y que se destapó al precificar
cuotas reales el 2026-09-22. Hay dos situaciones que parecen la misma y no lo
son:

- **Ascendido sin historia**: no está en el índice, así que `lambdas()` lo lleva
  a la media de su liga. Es SEGURO.
- **Club que vuelve tras años fuera**: sí está en el índice, así que NO cae a la
  media. Carga los `attack`/`defence` que le dejaron el ridge y el centrado de
  la liga —valores extremos— y el modelo los sostiene con total confianza.

La magnitud que los separa no es el número de partidos sino la **muestra
efectiva**: la suma de los pesos de decaimiento. Con media vida de 180 días, un
equipo que dejó de jugar en 2017 tiene cientos de partidos en la base y una
muestra efectiva de 0,0000. En el modelo entrenado, **95 de 362 equipos están
por debajo de 1**.

Sin esa medida el sistema producía su stake MÁXIMO justo donde menos sabía:
Hull salió a 0,9061 contra un mercado de 0,4659, "edge" del 97%, tier `high`.

**Causa medida en la auditoría del 2026-10-21** (`docs/auditoria_motores_20261021.md`): la suma cero por liga
promedia también a los equipos sin datos, que el optimizador usa de holgura (por eso quedan extremos), y el ridge
de 0,02 se diluye con la normalización de los pesos hasta valer ~0,001 partidos. Además el ajuste no converge
(tope de evaluaciones de L-BFGS-B). La guarda de muestra efectiva los saca de los picks, pero la agenda de la app
sigue mostrando su 1X2. La corrección propuesta (suma cero ponderada, ridge en partidos equivalentes, gradiente
analítico) está implementada en la rama `auditoria/motores-20261021` junto con la media vida de 270 días
(`DECAY_HALFLIFE_DAYS`), el ridge en partidos equivalentes (`RIDGE_PARTIDOS`, 0,5), un calibrador ajustado con
la verosimilitud del marcador y la agenda de la app mostrando el mercado cuando el modelo no conoce a un equipo.
Entra en producción con el próximo despliegue y reentrenamiento confirmados.
Las tres guardas existentes miraban otra cosa —`knows()` comprobaba pertenencia
al índice, `_confidence()` contaba partidos de toda la vida, y el encogimiento
de edge recortaba el 97% a un 53% que seguía saturando el tope—. Ahora
`DCParams.effective_n` la mide, `MIN_EFFECTIVE_MATCHES` (5 por defecto) la
exige, y por debajo del umbral la predicción se guarda y se sirve con tier
`low`, que es lo que `run()` ya excluye del universo de picks.

### Dos motores de fuerza, no uno

`dixon_coles` trata la fuerza como fija y compensa pesando menos lo viejo.
`kalman` la trata como un estado latente que evoluciona, lo que captura
parones, ascendidos y cambios bruscos de plantilla que el decaimiento no puede
expresar. En la medición de arriba empatan en precisión; Kalman gana por
velocidad (51 s frente a 4.888 s para la misma evaluación fuera de muestra),
lo que convierte el ajuste de hiperparámetros en rutina.

### Antes de tocar código

```bash
./scripts/harness_check.sh      # sintaxis, tests y validez del compose
pip install -r requirements-dev.txt
```

En Windows, si `.venv` conserva los paquetes pero apunta a una instalación de
Python 3.12 que ya no existe, `powershell -File scripts/test_local_windows.ps1`
ejecuta la suite con otro Python 3.12 compatible sin modificar `.venv`. Acepta
`-PythonPath` para indicar el intérprete; crea los temporales de pytest bajo
`.local/pytest-runs`, fuera del contexto Docker.

El contexto operativo para agentes está en `CLAUDE.md`; las decisiones ya
tomadas y por qué, en `harness/progreso.md`.
