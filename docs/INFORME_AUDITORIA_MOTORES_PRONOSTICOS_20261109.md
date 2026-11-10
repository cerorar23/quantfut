# INFORME DE AUDITORÍA INTEGRAL Y FORENSE: MOTORES DE PRONÓSTICOS, MERCADOS Y SISTEMAS DE APUESTAS

**Fecha de emisión:** 9 de noviembre de 2026  
**Alcance:** Fútbol, Tenis y NBA — Arquitectura de software, modelos matemáticos y científicos, cobertura de ligas, catálogo de mercados y *player props*, mecánica del mercado de cuotas y viabilidad del Reto Escalera y Parleys.  
**Repositorio auditado:** `c:/Users/huye/Documents/apuesta proyec`

---

## FE DE ERRATAS Y ESTADO FRENTE A `main` (9-nov-2026)

El informe lo elaboró otra IA. Se contrastó con el código de `origin/main`. El texto original se conserva debajo sin cambios; estas correcciones prevalecen:

1. **Escalera (§1.4, §6.1, §6.3, §7):** no es «2 escalones, freeroll a ×2,5 y 80 %». La regla vigente (`src/qf/publish/escalera.py`, constantes del 7-nov-2026) tiene hasta `MAX_ESCALONES` = 6 escalones con objetivos de `TARGETS` (2,0 a 20,0), cuota por escalón 1,25–2,10, probabilidad por escalón entre `PROB_MIN` = 0,69 y `PROB_MAX` = 0,95, presupuesto `PROB_RETO` = 0,4761, un escalón al día, expiración a `DIAS_MAX` = 10 días y freeroll a `FREEROLL_X` = 2,5. Las cifras de §6.1 (16,4 %, −23,7 %) son válidas como historia de la regla de partida. El 85,9 % y el 84,3 % de cumplimiento corresponden a la regla de 28-oct, no a la vigente.
2. **Fútbol, vida media (§2.1):** el informe dice 180 días. El valor por defecto en `src/qf/config.py` (`decay_halflife_days`) es 270 días, y su comentario recoge la comparación 120/180/220/270/365. Antes de citar 180, hay que confirmar cuál está activo en producción.
3. **Fútbol, calibración (§1.1, §2.1):** «perfectamente calibrado» es excesivo. El ECE es bajo en la validación de 1.149 partidos, pero el propio proyecto registró que Dixon-Coles subestima goles en el tramo de ago–nov 2026 (memoria del 9-nov, «sesgo de goles apagado»).
4. **NBA, hallazgos C02, C03 y C05 (§7):** están corregidos en `main` desde el commit `7bc9424f` (4-nov-2026). En `props.py`, `mercados.py` y `distribucion.py` ya no aparece la fórmula `P(victoria) + 0,5·P(push)`. `plantilla.py` limita a `MINUTOS_COMPLETOS` = 48 por jugador. `sellado.py` compara con `clock_timestamp()` de la base de datos. No se ha verificado que la imagen desplegada en el VPS incluya ese commit.
5. **Tenis (§2.2, §7.4):** el 54,5 % son 24 de 44 partidos con resultado, con intervalo de 40–68 % (`data/tennis/RESUMEN_TENIS_20261022.md`). Es una señal a vigilar, no concluyente. El Elo de superficie daba 64,2 % (ATP) y 64,8 % (WTA) en esa misma muestra.
6. **§5 (sección de latencia):** describe un arbitraje por latencia que el producto no ejecuta. Los picks de valor están apagados y la casa de referencia es Pinnacle sin margen.
7. **No verificado:** «más de 70 investigaciones académicas» (§1.3) y la lista de 26 competiciones con sus claves.

---

## ÍNDICE GENERAL

1. [Resumen Ejecutivo y Dictamen Global](#1-resumen-ejecutivo-y-dictamen-global)
2. [Auditoría Científica y Matemática por Deporte](#2-auditoría-científica-y-matemática-por-deporte)
   - 2.1 [Motor de Fútbol (Arquitectura Tripartita)](#21-motor-de-fútbol-arquitectura-tripartita)
   - 2.2 [Motor de Tenis (Procesos Markovianos Punto a Punto)](#22-motor-de-tenis-procesos-markovianos-punto-a-punto)
   - 2.3 [Motor de NBA (Procesos Estocásticos y Residuo de Mercado)](#23-motor-de-nba-procesos-estocásticos-y-residuo-de-mercado)
3. [Cobertura de Ligas y Competiciones](#3-cobertura-de-ligas-y-competiciones)
4. [Matriz Exhaustiva de Mercados: Hándicap, Totales y Props de Jugadores](#4-matriz-exhaustiva-de-mercados-hándicap-totales-y-props-de-jugadores)
5. [Funcionamiento Técnico del Mercado de Cuotas](#5-funcionamiento-técnico-del-mercado-de-cuotas)
6. [Auditoría Matemática del Reto Escalera y Parleys](#6-auditoría-matemática-del-reto-escalera-y-parleys)
   - 6.1 [Reto Escalera: Vicios Tradicionales y Solución Dubins-Savage](#61-reto-escalera-vicios-tradicionales-y-solución-dubins-savage)
   - 6.2 [Parleys: Optimización Combinatoria Beam Search y Probabilidad Prudente](#62-parleys-optimización-combinatoria-beam-search-y-probabilidad-prudente)
   - 6.3 [Veredicto: Certeza vs. Cuotas Altas](#63-veredicto-certeza-vs-cuotas-altas)
7. [Hallazgos Críticos, Límites y Recomendaciones de Ingeniería](#7-hallazgos-críticos-límites-y-recomendaciones-de-ingeniería)

---

## 1. RESUMEN EJECUTIVO Y DICTAMEN GLOBAL

El ecosistema auditado opera como una plataforma cuantitativa institucional multideporte. Los hallazgos principales determinan que:

1. **Fútbol:** Opera con tres motores desacoplados:
   - **Motor A (Dixon-Coles propio):** Bien calibrado pero **no supera al mercado sharp** (RPS 0.1991 vs. 0.1935 de Pinnacle). Por esta razón, **no decide pronósticos comerciales**.
   - **Motor B (Pinnacle sin margen vía Shin):** Es la fuente de la que nacen los productos reales (Alta Probabilidad, Escalera y Parley).
   - **Motor C (Binomial Negativa):** Modela córners y tarjetas con ajuste bayesiano por árbitro.
2. **Tenis:** Aplica modelos jerárquicos bayesianos y cadenas de Markov punto a punto (Spanias, Ingram, Kovalchik). Genera una distribución conjunta estricta para juegos y sets, aunque en pruebas de producción recientes exhibió un acierto del 54.5% en ganador (frente a 64.5% del Elo de superficie), evidenciando sensibilidad a la frescura de datos de lesiones y rankings.
3. **NBA:** Es el motor con mayor granularidad estadística y **el único que opera un ecosistema masivo de *player props*** (puntos, rebotes, asistencias, triples, combinadas PRA, robos, tapones y dobles-dobles) basado en más de 70 investigaciones académicas (Harvard, UC Merced, Iowa State) y regresión residual anclada al logit de mercado (*Hubáček-Šír*). La auditoría forense identificó 7 hallazgos críticos de cálculo (destacando el tratamiento erróneo de los *pushes* en líneas enteras).
4. **Reto Escalera y Parley:** Han sido rediseñados desde fundamentos científicos. La escalera abandona la falacia de los 7 pasos y aplica el **Teorema de Dubins-Savage** (2 escalones, freeroll a $2.5\times$ y presupuesto dinámico de probabilidad $\ge 80\%$). El parley implementa un **Beam Search logarítmico** que garantiza independencia estricta (1 pata por evento, cero eventos repetidos entre tickets), castiga la incertidumbre mediante la cota inferior bootstrap ($p_{\text{prudente}}$) y descarta mercados con margen usurero ($1\text{T } 1\text{X}2$).

---

## 2. AUDITORÍA CIENTÍFICA Y MATEMÁTICA POR DEPORTE

```mermaid
flowchart TD
    subgraph Futbol["Fútbol (Arquitectura Tripartita)"]
        FA["Motor A: Dixon-Coles + xG Blend<br>(dixon_coles.py / pricing.py)"]
        FB["Motor B: De-vig Shin sobre Pinnacle<br>(devig.py / market_anchor.py)"]
        FC["Motor C: Binomial Negativa<br>(estadisticas_mercado.py)"]
    end
    subgraph Tenis["Tenis (Markov Estocástico)"]
        TA["Binomial Jerárquico Saque/Resto<br>(Spanias / Ingram / Kovalchik)"]
        TB["Programación Dinámica Markoviana<br>Puntos -> Juegos -> Sets -> Match"]
    end
    subgraph NBA["NBA (Procesos Estocásticos & Props)"]
        NA["Rotaciones y Minutos Markovianos<br>(Huang 2018 / Cervone 2016)"]
        NB["Marcador: Normal Bivariada / Colas t"]
        NC["Player Props: Residuo Logit de Mercado<br>(Hubáček-Šír)"]
    end

    FA --> OutF["Matriz de Marcadores 13x13<br>(~150 Mercados Coherentes)"]
    FB --> OutF
    FC --> OutF
    TA --> OutT["Distribución Conjunta Completa<br>(Juegos, Sets, Hándicaps)"]
    TB --> OutT
    NA --> OutN["Distribución de Puntos & Props<br>(Puntos, Rebotes, Asistencias, Triples)"]
    NB --> OutN
    NC --> OutN
```

---

### 2.1 MOTOR DE FÚTBOL (ARQUITECTURA TRIPARTITA)

El fútbol en QuantFut opera con tres motores independientes:

#### A. Motor A: Modelo Dixon-Coles Modificado con xG
* **Módulos clave:** [`src/qf/model/dixon_coles.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/dixon_coles.py), [`src/qf/model/calibration.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/calibration.py), [`src/qf/model/pricing.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/pricing.py), [`src/qf/model/train.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/train.py).
* **Formulación Teórica:** Basado en Dixon y Coles (1997). Modela los goles anotados por el equipo local ($X$) y visitante ($Y$) mediante variables Poisson cuyas intensidades dependen de parámetros latentes de ataque ($\alpha$), defensa ($\beta$), ventaja de campo ($\gamma$) y una base de liga ($\text{base}_L$):
  $$\lambda = \exp(\alpha_i + \beta_j + \gamma + \text{base}_L)$$
  $$\mu = \exp(\alpha_j + \beta_i + \text{base}_L)$$
* **Corrección $\tau$ en Marcadores Bajos:**
  $$P(X=x, Y=y) = \tau(x, y, \lambda, \mu, \rho) \cdot \frac{\lambda^x e^{-\lambda}}{x!} \cdot \frac{\mu^y e^{-\mu}}{y!}$$
  donde el factor $\tau$ ajusta la correlación en marcadores con pocos goles:
  $$\tau(0,0) = 1 - \lambda \mu \rho$$
  $$\tau(1,0) = 1 + \mu \rho$$
  $$\tau(0,1) = 1 + \lambda \rho$$
  $$\tau(1,1) = 1 - \rho$$
  El parámetro de correlación global activo en producción es $\rho = -0.0613$.
* **Ponderación con Expected Goals ($xG$ Blend):** Para reducir el ruido aleatorio de la baja frecuencia de goles, el modelo entrena con una combinación lineal de goles observados y goles esperados:
  $$\text{Objetivo} = 0.65 \cdot xG + 0.35 \cdot \text{Goles reales}$$
  configurado en `Settings.xg_blend = 0.65`.
* **Decaimiento Temporal y Regularización:** Ponderación exponencial $w(\Delta t) = \exp(-\xi \cdot \Delta t)$ con **vida media de 180 días**. Penalización ridge ($\lambda_{\text{ridge}} = 0.02$) con restricción de suma cero por liga ($\sum \alpha = 0, \sum \beta = 0$) y muestra efectiva mínima de 5 partidos equivalentes.
* **Calibrador Afín:** Realiza una regresión en el espacio log-intensidad ($\log \lambda_{\text{cal}} = a_0 + a_1 \log \lambda_{\text{raw}}$).
* **Evaluación Fuera de Muestra ($n = 1,149$):**
  * Pinnacle sin margen (Mercado): RPS = 0.19345 | Log-loss = 0.96809 | Brier = 0.57605
  * **Motor A (Dixon-Coles):** RPS = 0.19910 | Log-loss = 0.98841 | Brier = 0.58893
  * Elo: RPS = 0.19932 | Log-loss = 0.99374 | Brier = 0.59152
  * *Conclusión:* El Motor A está perfectamente calibrado pero discrimina menos que Pinnacle; **no tiene ventaja demostrada frente al cierre sharp**.

#### B. Motor B: Mercado Sharp / Pinnacle sin Margen
* **Módulos clave:** [`src/qf/model/devig.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/devig.py), [`src/qf/model/market_anchor.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/market_anchor.py), [`src/qf/publish/alta_prob.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/alta_prob.py).
* **Metodología:** Toma la cuota de Pinnacle como verdad fundamental. Elimina la comisión usando el método de **Shin (1993)**. Luego, mediante `market_anchor.py`, resuelve por optimización numérica las intensidades $(\lambda, \mu)$ de Dixon-Coles que reproducen exactamente las probabilidades 1X2 sin margen, utilizando el valor $\rho = -0.0613$ del Motor A.
* **Salida:** De esas intensidades ajustadas al mercado genera toda la matriz de marcadores para derivar hándicaps, totales, ambos marcan y dobles oportunidades. **Este motor alimenta los productos comerciales reales.**

#### C. Motor C: Estadístico de Córners y Tarjetas
* **Módulo:** [`src/qf/model/estadisticas_mercado.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/estadisticas_mercado.py).
* **Distribución:** Binomial Negativa ($\text{NB}(\mu, \phi)$) que modela la sobredispersión estadística de eventos secundarios.
* **Factor de Árbitro:** Para tarjetas, incorpora el sesgo del árbitro designado (`referee`), aplicando un estimador bayesiano contraído hacia la media general con peso `PRIOR_ARBITRO = 10`.

---

### 2.2 MOTOR DE TENIS (PROCESOS MARKOVIANOS PUNTO A PUNTO)

* **Ubicación y literatura:** [`data/tennis/rediseno_20261104/`](file:///c:/Users/huye/Documents/apuesta%20proyec/data/tennis/rediseno_20261104/), [`apps/tennis/`](file:///c:/Users/huye/Documents/apuesta%20proyec/apps/tennis/).
* **Autores de Referencia:** Demetris Spanias (Tesis Doctoral, *Imperial College London*, 2015), Martin Ingram (*NESSIS*, 2017), Stephanie Kovalchik (2016).
* **Modelo Jerárquico de Saque/Resto:** Para el jugador $i$ frente al oponente $j$ en el encuentro $m$, superficie $s$ y fecha $t$:
  $$Y_{i,m} \mid N_{i,m}, p_{i,m} \sim \text{Binomial}(N_{i,m}, p_{i,m})$$
  $$\text{logit}(p_{i,m}) = \mu_{\text{circuito}} + S_{i,t} - R_{j,t} + U_{i,s} - V_{j,s} + C_{\text{torneo}} + \beta^T X$$
  donde $S_i$ representa la habilidad latente de saque, $R_j$ la habilidad de resto, $U_i, V_j$ las desviaciones por superficie (arcilla, hierba, pista dura, cubierta), y $X$ factores de contexto (horas de viaje, días de descanso, altitud con Open-Meteo).
* **Programación Dinámica Markoviana:** Con las probabilidades fundamentales de servicio ($p_A$ y $p_B$):
  1. **Juego:** Se resuelve la cadena de Markov con estados deuce absorbentes:
     $$P(\text{Juego } A) = \frac{p_A^4 (15 - 34 p_A + 28 p_A^2 - 8 p_A^3)}{1 - 2 p_A (1 - p_A)}$$
  2. **Tie-Break:** Resuelto analíticamente para secuencias a 7 o 10 puntos (mínimo diferencia de 2).
  3. **Set y Partido:** Se ensambla la probabilidad recursiva de marcadores (6-0 a 7-6) en partidos al mejor de 3 (BO3) o mejor de 5 sets (BO5).
* **Desempeño Observado en Producción:**  
  Evaluación en el VPS (44 partidos reales sellados): acierto de **54.5%** (ATP: 53.6%, WTA: 56.3%). Log-loss en ATP fue de 0.729 (peor que el 0.693 de lanzar una moneda y peor que el 64.5% de un Elo de superficie base). Las líneas extremas aciertan por su baja varianza natural, pero en líneas intermedias (22.5 juegos, hándicap 0) el modelo ronda el 50%, requiriendo mayor profundidad de datos.

---

### 2.3 MOTOR DE NBA (PROCESOS ESTOCÁSTICOS Y RESIDUO DE MERCADO)

* **Ubicación y literatura:** [`docs/nba_matriz_mercados_y_estudios_20261024.md`](file:///c:/Users/huye/Documents/apuesta%20proyec/docs/nba_matriz_mercados_y_estudios_20261024.md), [`apps/nba/`](file:///c:/Users/huye/Documents/apuesta%20proyec/apps/nba/), [`ESTUDIOS/Pdf Estudio Nba/`](file:///c:/Users/huye/Documents/apuesta%20proyec/ESTUDIOS/Pdf%20Estudio%20Nba/).
* **Base Científica Multirresolución:**
  * **Cervone et al. (Harvard, JASA 2016):** Modelado de posesiones como procesos estocásticos de microestados.
  * **Huang (UC Merced 2018):** Minutos y rotaciones modelados como cadenas de Markov de sustitución de quintetos (*stints*).
  * **Alameda-Basora (Iowa State 2019):** Redes bayesianas para totales de puntos en vivo y por cuarto (Q1, Q2, Q3, Q4).
  * **Hubáček & Šír:** Modelo de pérdida anclado en la cuota de mercado (*market-anchored logit loss*).
* **Pipeline de 4 Fases en la Versión v2:**
  1. **Disponibilidad:** Procesamiento continuo de reportes de lesiones oficiales NBA (PDF) y feeds de Rotowire/ESPN para clasificar a los jugadores en estados probabilísticos (*Available, Probable, Questionable, Doubtful, Out*).
  2. **Minutos:** Proyección de rotaciones mediante cadenas de Markov, escaladas para cerrar en 240 minutos de equipo (48 min $\times$ 5 jugadores).
  3. **Marcador de Equipo:** Modelo paramétrico bivariado de puntos con colas pesadas ($t$-Student) para absorber prórrogas y ritmos de posesión.
  4. **Player Props (Props de Jugador):** Ajuste de regresión sobre las líneas de mercado, estimando el residuo empírico individual sobre la oferta de casas de apuestas.

---

## 3. COBERTURA DE LIGAS Y COMPETICIONES

El sistema abarca formalmente **26 competiciones deportivas** en producción:

| Deporte | Total | Competiciones Detalladas | Mecanismo de Predicción |
| :--- | :---: | :--- | :--- |
| **Fútbol** | **23** | **13 Ligas con Motor Propio (A + B):**<br>1. Inglaterra: Premier League (`gb.premier_league`)<br>2. España: LaLiga (`es.laliga`)<br>3. Italia: Serie A (`it.serie_a`)<br>4. Alemania: Bundesliga (`de.bundesliga`)<br>5. Francia: Ligue 1 (`fr.ligue_1`)<br>6. Portugal: Primeira Liga (`pt.primeira`)<br>7. Países Bajos: Eredivisie (`nl.eredivisie`)<br>8. México: Liga MX (`mx.liga_mx`)<br>9. Brasil: Brasileirão Série A (`br.serie_a`)<br>10. Argentina: Liga Profesional (`ar.primera`)<br>11. EE. UU.: Major League Soccer (`us.mls`)<br>12. Europa: UEFA Champions League (`uefa.champions`)<br>13. Europa: UEFA Europa League (`uefa.europa`)<br><br>**10 Ligas en Modalidad "Solo Sharp" (Motor B):**<br>14. España: LaLiga 2 (`es.laliga2`)<br>15. Italia: Serie B (`it.serie_b`)<br>16. Inglaterra: Championship (`gb.championship`)<br>17. Alemania: 2. Bundesliga (`de.bundesliga2`)<br>18. Francia: Ligue 2 (`fr.ligue_2`)<br>19. Suiza: Super League (`ch.super_league`)<br>20. Dinamarca: Superliga (`dk.superliga`)<br>21. Noruega: Eliteserien (`no.eliteserien`)<br>22. Suecia: Allsvenskan (`se.allsvenskan`)<br>23. Turquía: Süper Lig (`tr.super_lig`)<br>*(Nota: Chile Primera y Brasil Série B fueron dadas de baja por directriz técnica).* | • 13 Ligas: Dixon-Coles bivariado con goles/xG, calibración y derivación analítica.<br>• 10 Ligas: Cuota Pinnacle Sharp sin margen (Shin) y captura de sombra sin entrenamiento propio. |
| **Tenis** | **2** | 24. **ATP Tour** (Grand Slams, Masters 1000, ATP 500, ATP 250)<br>25. **WTA Tour** (Grand Slams, WTA 1000, WTA 500, WTA 250)<br>*(Históricos de validación incluyen ATP Challenger vía MCP/Tennis-Data).* | Modelo estocástico unificado punto a punto con cadenas de Markov y superficies. |
| **NBA** | **1** | 26. **NBA** (Temporada Regular, Torneo Play-In, Playoffs y Finales). | Base de datos dedicada (`nba.*`), procesos de posesión, rotaciones y modelos residuales de props. |

---

## 4. MATRIZ EXHAUSTIVA DE MERCADOS: HÁNDICAP, TOTALES Y PROPS DE JUGADORES

### A. Cobertura de Hándicaps y Totales
**SÍ, de forma completa en los tres deportes.**
* **Fútbol:** Hándicap Asiático (líneas enteras y medias: $+1.5, +1.0, +0.5, 0.0, -0.5, -1.0, -1.5$), Hándicap Europeo (3 opciones), Totales de goles Over/Under ($0.5, 1.5, 2.5, 3.5, 4.5, 5.5$), Totales por equipo (local/visitante) y Totales de Córners y Tarjetas.
* **Tenis:** Hándicap de juegos del partido ($-5.5$ a $+5.5$), Hándicap de juegos por set, Totales de juegos del partido (líneas enteras y medias), Totales de juegos por set y Totales de sets (Over/Under 2.5).
* **NBA:** Hándicap de puntos del partido (*spreads*), Hándicap en 1.ª mitad, Hándicap en 1.er cuarto (Q1), Totales de puntos del partido (*totals* Over/Under), Totales de puntos en 1.ª mitad y Totales por cuartos individuales.

### B. Cobertura de Props de Jugadores (*Player Props*)

| Mercado Específico de Jugador | Fútbol | Tenis | NBA |
| :--- | :---: | :---: | :---: |
| **Puntos de Jugador** | ❌ No | ⚠️ Solo juegos ganados (*player games*) | ✅ **SÍ** (`player_points`) |
| **Rebotes de Jugador** | ❌ No aplica | ❌ No aplica | ✅ **SÍ** (`player_rebounds`) |
| **Asistencias de Jugador** | ❌ No | ❌ No aplica | ✅ **SÍ** (`player_assists`) |
| **Triples Anotados** | ❌ No aplica | ❌ No aplica | ✅ **SÍ** (`player_threes`) |
| **Combos: P+R, P+A, R+A, PRA** | ❌ No | ❌ No aplica | ✅ **SÍ** (Capturado vía PropLine) |
| **Robos, Tapones, Pérdidas** | ❌ No | ❌ No aplica | ✅ **SÍ** (Capturado vía PropLine) |
| **Doble-Doble / Triple-Doble** | ❌ No aplica | ❌ No aplica | ✅ **SÍ** (Capturado vía PropLine) |
| **Primer Enceste / Tiro Anotado** | ❌ No aplica | ❌ No aplica | ✅ **SÍ** (En histórico PBP) |
| **Tiros a Puerta / Goleador** | ⚠️ Descartado (margen > 10%) | ❌ No aplica | ❌ No aplica |
| **Aces y Dobles Faltas** | ❌ No aplica | ❌ No (no derivables de $p, q$) | ❌ No aplica |

> **Veredicto Técnico sobre Props:**  
> **NBA es el único deporte con un ecosistema completo y activo de *player props* en producción.** En fútbol, los props de futbolistas están explícitamente apagados por dos razones cuantitativas: las casas imponen márgenes predatorios ($> 10\% - 15\%$) y la varianza en bajas frecuencias destruye el valor esperado. En tenis, los props individuales (aces, faltas) se rechazaron formalmente porque no son deducibles de la probabilidad de saque sin introducir parámetros empíricos arbitrarios.

---

## 5. FUNCIONAMIENTO TÉCNICO DEL MERCADO DE CUOTAS

Para tasar apuestas con ventaja matemática, el sistema audita cómo se forman y distorsionan las cuotas:

```mermaid
sequenceDiagram
    autonumber
    participant Pinnacle as Casa Sharp (Pinnacle)
    participant Engine as Motor Cuantitativo (QuantFut)
    participant Soft as Casa Soft (bet365, Caliente, etc.)

    Pinnacle->>Engine: Cuota Sharp con margen mínimo (ej. 1.95 - 1.95)
    Note over Engine: Aplica De-vig Shin (1993)<br>Parámetro z de apostadores informados
    Engine->>Engine: Probabilidad real pura: p = 50.0% (Cuota justa = 2.00)
    Soft->>Engine: Cuota desactualizada por latencia: 2.08
    Note over Engine: Cálculo de Edge:<br>EV = (0.50 * 2.08) - 1 = +4.0%
    Engine-->>Engine: Valida puerta CLV e incertidumbre bootstrap
    Engine->>User: Publicación de Pick / Inclusión en Ticket
```

### 1. Cuota Decimal y Margen de la Casa (*Overround*)
Una cuota decimal $O$ ofrecida por una casa refleja una probabilidad implícita con comisión:
$$q_i = \frac{1}{O_i}$$
En cualquier mercado real, la suma de las probabilidades implícitas supera la unidad ($1.00$):
$$\sum_{j=1}^k q_j = 1 + M \quad (M = \text{Margen de la casa, habitualmente } 4\% - 9\%)$$

### 2. Casas *Sharp* vs. Casas *Soft*
* **Casas *Sharp* (Pinnacle, Circa, Betfair Exchange):** Operan con márgenes reducidos ($1.5\% - 2.5\%$), aceptan altos volúmenes y no limitan a usuarios ganadores. Su cuota antes del pitido inicial (**Closing Line Value o CLV**) es la medida más eficiente y libre de sesgo disponible del resultado real.
* **Casas *Soft* (bet365, Caliente, 1xBet, Codere, Betano):** Tienen márgenes más altos ($5\% - 9\%$), enfocadas en el público recreativo. Presentan **latencia**: cuando una lesión o información mueve la línea en Pinnacle, las casas *soft* tardan minutos u horas en reaccionar. Esa diferencia temporal es donde existe el valor esperado positivo ($+EV$).

### 3. Algoritmo de De-vigging de Shin (1993) ([`src/qf/model/devig.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/model/devig.py))
Para calcular la probabilidad real a partir de las cuotas de Pinnacle, el sistema descarta la división proporcional simple (que falla por el sesgo favorito-*longshot*) y aplica el modelo microeconómico de **H. S. Shin**:
$$p_i = \frac{\sqrt{z^2 + 4(1-z) \frac{q_i}{\sum q_j}} - z}{2(1-z)}$$
donde $z$ modela la fracción de dinero apostado por participantes con información perfecta. Esto extrae la verdadera probabilidad matemática subyacente.

---

## 6. AUDITORÍA MATEMÁTICA DEL RETO ESCALERA Y PARLEYS

El usuario formula la pregunta medular:  
*«¿El reto escalera y parley están correctamente hechos de manera correcta para escoger los pronósticos con mayor certeza para llegar a las cuotas?»*

### 6.1 RETO ESCALERA: VICIOS TRADICIONALES Y SOLUCIÓN DUBINS-SAVAGE

#### El Defecto Mortal de la Escalera Convencional
En la comunidad tradicional de apuestas, el "reto escalera" consiste en apostar el saldo acumulado en 5 a 7 pasos sucesivos a cuotas de $1.25$ a $1.40$.  
La auditoría matemática sobre los datos históricos del proyecto demostró que **este esquema es matemáticamente ruinoso**:
* A cuota media de $1.30$, la probabilidad real de acierto es $\approx 74\%$.
* La probabilidad conjunta de completar 6 escalones consecutivos es:
  $$P(\text{éxito}) = (0.74)^6 \approx 16.4\%$$
* Dado que la casa descuenta su margen en cada escalón, el reto amplifica la ventaja de la casa: en las pruebas retrospectivas (`eval/escalera_prueba.py`), un reto a 6 pasos produce un **$-23.7\%$ de retorno esperado por reto**.

#### La Solución Implementada ([`src/qf/publish/escalera.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/escalera.py))
1. **Teorema de Dubins y Savage (1965):** *En un entorno donde la casa cobra comisión, la estrategia óptima para alcanzar un objetivo multiplicativo con la menor probabilidad de ruina es minimizar el número total de jugadas.*
2. **Reducción Estricta a 2 Escalones:** Se eliminaron las escaleras largas. El reto actual consta de **únicamente 2 escalones** con una ventana de espera máxima de 7 a 10 días (`DIAS_MAX = 10`, `POR_DIA = 1`).
3. **Presupuesto Dinámico de Probabilidad:** Para garantizar que el reto completo mantenga un estándar de cumplimiento global $\ge 80\%$, el sistema calcula dinámicamente:
   $$p_k \ge \left( \frac{\text{PROB\_RETO}}{\prod p_{\text{elegidos}}} \right)^{\frac{1}{\text{escalones restantes}}}$$
   Si el primer escalón es de extrema solidez ($p = 0.95$), el segundo escalón exige $p \ge 0.842$.
4. **Mecanismo de Freeroll a $2.5\times$:** Al multiplicar el saldo por $2.5\times$, se retira obligatoriamente el $100\%$ de la inversión inicial (\$10.00) y se continúa únicamente con la ganancia neta, eliminando matemáticamente el riesgo sobre el capital principal.
5. **Selección Defensiva de Mercados:** No se buscan cuotas forzadas; se priorizan hándicaps asiáticos protectores ($+1.0, +1.5, +2.0, +2.5$ al underdog) y totales extremos validados en calibración.

---

### 6.2 PARLEYS: OPTIMIZACIÓN COMBINATORIA BEAM SEARCH Y PROBABILIDAD PRUDENTE

#### Los Vicios del Parley Común
Un parley tradicional multiplica cuotas y márgenes:
$$Q_{\text{ticket}} = \prod Q_i, \quad \text{Margen acumulado} = 1 - \prod (1 - M_i)$$
Un parley de 4 selecciones con $5\%$ de margen acumula una desventaja del $18.55\%$ en contra del apostador. Combinar patas del mismo partido sin matriz conjunta distorsiona gravemente el riesgo.

#### La Ingeniería de Parley v2 ([`src/qf/publish/parley_v2.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/parley_v2.py))
* **Búsqueda Combinatoria Simultánea (*Beam Search*):** Resuelve simultáneamente los cuatro tickets del día en un espacio logarítmico:
  $$\log Q = \sum \log q_i, \quad \log P = \sum \log p_i$$
  evaluando hasta 2,000,000 de combinaciones posibles para no consumir los mejores pronósticos en un solo ticket.
* **Cuatro Targets Estrictos ($\pm 2\%$):**
  * **Target 1 (Cuota 2.10):** Rango $[2.058 - 2.142]$ (mínimo 2 patas).
  * **Target 2 (Cuota 3.10):** Rango $[3.038 - 3.162]$ (mínimo 2 patas).
  * **Target 3 (Cuota 8.20):** Rango $[8.036 - 8.364]$ (mínimo 4 patas).
  * **Target 4 (Cuota 12.10):** Rango $[11.858 - 12.342]$ (mínimo 5 patas).
* **Independencia Absoluta de Eventos:**
  * Máximo **1 sola pata por partido**.
  * **Cero eventos repetidos:** Los 4 tickets diarios exigen al menos 13 partidos completamente distintos. Queda prohibido solapar partidos entre tickets.
* **Penalización por Incertidumbre ($p_{\text{prudente}}$):** El algoritmo no utiliza la probabilidad media esperada; toma el **límite inferior del intervalo de confianza bootstrap** (`Calibracion.p_prudente`). Mercados con escaso soporte empírico son fuertemente castigados y quedan fuera.
* **Exclusión de Mercados Usureros:** Excluye formalmente mercados como el 1X2 al descanso (*1T 1X2*), tras verificar que las casas aplican márgenes confiscatorios de entre el $9\%$ y el $11\%$.
* **Filtro de Anomalías (*Outlier Guard*):** Si la mejor cuota supera por más del $5\%$ a la segunda cuota disponible (con $\ge 3$ casas), se asume un error de lectura de la casa y se rechaza para prevenir cancelaciones.
* **Estados de Emisión Controlados:** Si no existe una combinación que cumpla con los estándares probabilísticos, el sistema emite `abstencion` en lugar de forzar un boleto sin valor.

---

### 6.3 VEREDICTO: CERTEZA VS. CUOTAS ALTAS

| Criterio Evaluado | Estado Técnico | Veredicto |
| :--- | :--- | :---: |
| **Metodología de Selección** | Algorítmica, matemática y sin sesgos emocionales. | **ÓPTIMA** |
| **Independencia Estadística** | Garantizada: 1 pata por evento, cero repetición entre tickets. | **ESTRICTA** |
| **Control de Incertidumbre** | Descuenta la varianza muestral mediante bootstrap ($p_{\text{prudente}}$). | **RIGUROSO** |
| **Viabilidad en Cuotas Bajas (2.10 y 3.10 y Escalera)** | Tasas de acierto elevadas ($50\% - 75\%$), ideales para control de riesgo. | **ALTAMENTE EFICIENTE** |
| **Realidad Matemática en Cuotas Altas (8.20 y 12.10)** | Una cuota de 12.10 tiene una probabilidad intrínseca de ocurrir de solo el **$7\% - 10\%$**. Aunque el sistema elija la combinación matemáticamente más probable de todo el mercado, **no existe certeza en una cuota 12.10**. Las leyes de la probabilidad no pueden burlarse. | **INELUDIBLEMENTE PROBABILÍSTICO** |

---

## 7. HALLAZGOS CRÍTICOS, LÍMITES Y RECOMENDACIONES DE INGENIERÍA

Durante la auditoría forense del código desplegado, se identificaron los siguientes puntos de atención prioritaria:

1. **Gestión de Pushes en NBA (Hallazgo Crítico C03):**  
   En `props.py` y `mercados.py` de NBA, el código calcula:
   $$\text{Probabilidad expuesta} = P(\text{victoria}) + 0.5 \cdot P(\text{push})$$
   Esto es un error de valoración: en líneas enteras con devolución (ej. hándicap $-4.0$ o total $220.0$), un empate devuelve el dinero intacto. La probabilidad condicionada correcta debe ser:
   $$P(\text{victoria} \mid \text{no push}) = \frac{P(\text{victoria})}{1 - P(\text{push})}$$
2. **Capacidad de Minutos en Plantillas NBA (Hallazgo Crítico C05):**  
   La función de renormalización de minutos escala a 240 minutos sin imponer un techo individual por jugador, permitiendo en casos extremos proyectar hasta 128 minutos a una figura. Se debe imponer una restricción física de $\le 42$ minutos por jugador en tiempo reglamentario.
3. **Condición de Carrera en el Tip-off NBA (Hallazgo Crítico C02):**  
   La variable `ahora` se fija al inicio de la ejecución. Si el cálculo tarda varios minutos, el pronóstico puede insertarse en base de datos después del salto inicial. Se requiere un constraint SQL que contraste contra el reloj del servidor inmediatamente antes del `INSERT`.
4. **Recalibración del Motor de Tenis:**  
   El rendimiento del motor de tenis en ganador ($54.5\%$) requiere incorporar mayor profundidad en el historial de enfrentamientos directos y verificar la latencia de cuotas en torneos menores para evitar pronósticos con cuotas caducadas.

---

**Conclusión General:** El sistema QuantFut cuenta con una arquitectura cuantitativa avanzada y honesta. No promete ganancias irreales; traduce la información más eficiente del mercado sharp y resuelve con optimización combinatoria rigurosa la mejor forma matemática de aproximarse a cuotas objetivo.
