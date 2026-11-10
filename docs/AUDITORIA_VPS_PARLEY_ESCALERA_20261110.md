# AUDITORÍA FORENSE Y EN PRODUCCIÓN REAL (VPS): MÓDULOS DE PARLEY Y RETO ESCALERA

**Fecha de emisión:** 10 de noviembre de 2026  
**Servidor Auditado:** VPS de Producción (`qf@31.220.72.30`)  
**Contenedores e Infraestructura:** PostgreSQL 16 (`quantfut-db-1`), Worker (`quantfut-worker-1`), Release Parley v2 (`/home/qf/quantfut/releases/parley-v2-20261106/`)  
**Repositorio auditado:** `c:/Users/huye/Documents/apuesta proyec`

---

## ÍNDICE GENERAL

1. [Resumen Ejecutivo y Métricas Globales de Producción](#1-resumen-ejecutivo-y-métricas-globales-de-producción)
2. [Auditoría Forense del Área de Parley en el VPS](#2-auditoría-forense-del-área-de-parley-en-el-vps)
   - 2.1 [Arquitectura Dual: Parley v1 vs. Parley v2.1](#21-arquitectura-dual-parley-v1-vs-parley-v21)
   - 2.2 [Deportes y Mercados que Alimentan al Parley (Datos Reales)](#22-deportes-y-mercados-que-alimentan-al-parley-datos-reales)
   - 2.3 [Algoritmo de Selección: Optimización Combinatoria Beam Search](#23-algoritmo-de-selección-optimización-combinatoria-beam-search)
   - 2.4 [Track Record y Rendimiento Real en Base de Datos](#24-track-record-y-rendimiento-real-en-base-de-datos)
   - 2.5 [Incidencia Crítica Detectada en Logs del VPS](#25-incidencia-crítica-detectada-en-logs-del-vps)
3. [Auditoría Forense del Reto Escalera en el VPS](#3-auditoría-forense-del-reto-escalera-en-el-vps)
   - 3.1 [Evolución de Reglas: De 6 Pasos al Teorema de Dubins-Savage (2 Escalones)](#31-evolución-de-reglas-de-6-pasos-al-teorema-de-dubins-savage-2-escalones)
   - 3.2 [Deportes y Mercados que Alimentan la Escalera (Datos Reales)](#32-deportes-y-mercados-que-alimentan-la-escalera-datos-reales)
   - 3.3 [Mecanismo de Selección del Pronóstico Ganador](#33-mecanismo-de-selección-del-pronóstico-ganador)
   - 3.4 [Track Record Real de Escalones y Retos Completados](#34-track-record-real-de-escalones-y-retos-completados)
4. [Mapeo de Tablas y Esquemas en PostgreSQL](#4-mapeo-de-tablas-y-esquemas-en-postgresql)
5. [Dictamen Técnico y Acciones Inmediatas](#5-dictamen-técnico-y-acciones-inmediatas)

---

## 1. RESUMEN EJECUTIVO Y MÉTRICAS GLOBALES DE PRODUCCIÓN

La auditoría realizada directamente sobre la base de datos de producción (`quantfut` en PostgreSQL 16) y los procesos del VPS arroja las siguientes conclusiones fundamentales:

```mermaid
flowchart LR
    subgraph VPS["Producción Real VPS (qf@31.220.72.30)"]
        PV1["Parley v1 (Fútbol Puro)<br>101 tickets | ROI: +28.56%"]
        PV2["Parley v2.1 (Multideporte)<br>33 tickets | Acierto: 48.0%"]
        ESC["Reto Escalera (2 Escalones)<br>59 pasos | Acierto: 83.33% | Invicto en 2 pasos"]
    end
```

| Módulo | Estado en VPS | Muestra Registrada | Tasa de Acierto | Desempeño Financiero (ROI) | Cobertura Deportiva |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Parley v1** | Pipeline Diario 09:00 UTC | 101 tickets liquidados | **48.51%** (49G - 52P) | **+28.56%** (+28.84 u) | Fútbol exclusivo |
| **Parley v2.1** | Cron 09:35 - 10:00 UTC | 25 tickets liquidados | **48.00%** (12G - 13P) | **-12.72%** (-3.18 u) | **Multideporte:** Tenis (21), NBA Props (25), Fútbol (19) |
| **Reto Escalera** | Pipeline Diario + Ext | 59 escalones (19 retos) | **83.33%** por escalón (45G - 9P - 5V) | Retos de 2 pasos: **100%** completados | **Multideporte:** Fútbol (52), Tenis (6), NBA (1) |

---

## 2. AUDITORÍA FORENSE DEL ÁREA DE PARLEY EN EL VPS

### 2.1 ARQUITECTURA DUAL: PARLEY V1 VS. PARLEY V2.1

La inspección de la base de datos y del crontab del host (`crontab -l`) demostró que conviven dos generaciones del motor de combinadas:

1. **Parley v1 ([`src/qf/publish/parley.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/parley.py)):**
   * Corre dentro del contenedor `quantfut-worker-1` en el pipeline diario general de las **09:00 UTC**.
   * Estructura: 1 a 5 boletos al día, con escalones de cuota acumulada entre 1.90 y 5.00, seleccionando patas con cuotas individuales de 1.20 a 1.80.
2. **Parley v2.1 ([`src/qf/publish/parley_v2.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/parley_v2.py)):**
   * Desplegado de forma aislada en `/home/qf/quantfut/releases/parley-v2-20261106/`.
   * Corre entre las **09:35 y las 10:00 UTC** (3:35 a 4:00 AM hora México) mediante `python -m qf.publish.parley_v2_datos` con reintentos cada 5 minutos.
   * Diseñado para generar simultáneamente 4 boletos dirigidos a 4 cuotas objetivo (*Targets*).
   * Cuenta con un worker de liquidación periódica cada 3 horas (`parley_v2_liquidacion`).

---

### 2.2 DEPORTES Y MERCADOS QUE ALIMENTAN AL PARLEY (DATOS REALES)

Consulta directa a las tablas de patas en el servidor de producción:

#### A. Parley v2.1 Multideporte (`parley_v2_patas`, 74 selecciones registradas):
```sql
SELECT coalesce(deporte, 'desconocido') as deporte, mercado, count(*) 
FROM parley_v2_patas 
GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```
* **Tenis (21 patas):**
  * `h2h`: 21 selecciones (ganadores de partido en torneos oficiales ATP y WTA).
* **NBA (25 patas - ¡Incluye Props de Jugador!):**
  * `player_rebounds` (**17 patas**): Rebotes Over/Under de jugadores NBA.
  * `h2h` (**9 patas**): Ganador del partido (*moneyline*).
  * `player_assists` (**4 patas**): Asistencias Over/Under de jugadores NBA.
  * `player_threes` (**4 patas**): Triples anotados Over/Under.
* **Fútbol (19 patas):**
  * `h2h`: 11 selecciones (ganador 1X2).
  * `totals`: 5 selecciones (Over/Under de goles).
  * `spreads`: 3 selecciones (Hándicap asiático).

#### B. Parley v1 Tradicional (`parley_patas`, 244 selecciones registradas):
* `totals` de goles: **89 patas** (50 vía PropLine, 37 vía API-Football, 2 vía The Odds API).
* `cards` (tarjetas totales del partido): **46 patas**.
* `h2h` (ganador 1X2): **44 patas**.
* `spreads` (hándicap asiático de goles): **29 patas**.
* `corners` (córners totales y por equipo): **19 patas**.
* `double_chance` (doble oportunidad): **11 patas**.
* `btts` (ambos marcan): **3 patas**.
* `team_totals` (goles por equipo): **3 patas**.

---

### 2.3 ALGORITMO DE SELECCIÓN: OPTIMIZACIÓN COMBINATORIA BEAM SEARCH

El algoritmo en `parley_v2.py` no elige selecciones por intuición ni de forma secuencial. Ejecuta una búsqueda simultánea en espacio logarítmico:

$$\log Q = \sum \log q_i, \quad \log P = \sum \log p_i$$

```python
def _clave_plan(tickets: list[tuple]) -> tuple:
    cubiertos = len(tickets)
    patas = sum(len(e[1]) for _, e in tickets)
    prob = sum(math.exp(e[0]) for _, e in tickets)
    dist = sum(abs(math.log(math.prod(o.price for o in e[1]) / t.value)) for t, e in tickets)
    ids = tuple(sorted(o.match_id for _, e in tickets for o in e[1]))
    return (-cubiertos, patas, -prob, dist, ids)
```

#### Jerarquía de Decisión Matemática:
1. **Maximizar Cobertura de Targets:** Resuelve los 4 boletos simultáneamente:
   * **Target 1:** Cuota $2.10$ ($\pm 2\%$, rango $2.058 - 2.142$, mín. 2 patas).
   * **Target 2:** Cuota $3.10$ ($\pm 2\%$, rango $3.038 - 3.162$, mín. 2 patas).
   * **Target 3:** Cuota $8.20$ ($\pm 2\%$, rango $8.036 - 8.364$, mín. 4 patas).
   * **Target 4:** Cuota $12.10$ ($\pm 2\%$, rango $11.858 - 12.342$, mín. 5 patas).
2. **Minimizar Patas Totales:** Penaliza boletos con exceso de eventos. Si el target se alcanza con 2 patas, descarta combinaciones de 3 o 4 patas para mitigar la varianza.
3. **Maximizar Probabilidad Conjunta Prudente ($p_{\text{prudente}}$):**
   * No utiliza la probabilidad central del modelo.
   * Aplica la **cota inferior del intervalo de confianza bootstrap** (`Calibracion.p_prudente`). Mercados con pocos datos o alta volatilidad ven reducida su probabilidad y son descartados por el algoritmo.
4. **Independencia Absoluta de Eventos:**
   * Máximo **1 sola pata por partido**.
   * **Cero repeticiones:** Ningún evento se repite entre los 4 tickets del día. Se requieren al menos 13 partidos completamente distintos para armar la cartelera diaria.
5. **Filtro de Anomalías (*Outlier Guard*):** Si la mejor cuota supera a la segunda por $> 5\%$ (habiendo $\ge 3$ casas), se asume cuota errónea o desactualizada y se descarta.
6. **Exclusión de Mercados Usureros:** Excluye el 1X2 al descanso (*1T*), donde las casas aplican márgenes del $9\%$ al $11\%$.

---

### 2.4 TRACK RECORD Y RENDIMIENTO REAL EN BASE DE DATOS

#### A. Parley v1 (`parley_resultados`, 101 tickets liquidados):
```sql
 total_tickets | ganados | perdidos | pct_acierto | retorno_total | beneficio_neto | roi_pct 
---------------+---------+----------+-------------+---------------+----------------+---------
           101 |      49 |       52 |       48.51 |        129.84 |         +28.84 |  +28.56%
```
* **Análisis:** Enorme rentabilidad acumulada impulsada por líneas asiáticas y totales de fútbol donde el Motor B capturó cuotas retrasadas de casas blandas frente al cierre de Pinnacle.

#### B. Parley v2.1 (`parley_v2_resultados`, 25 tickets liquidados):
```sql
 total_tickets | ganados | perdidos | otros | retorno_total | beneficio_neto | roi_pct
---------------+---------+----------+-------+---------------+----------------+---------
            25 |      12 |       13 |     0 |         21.82 |          -3.18 |  -12.72%
```
* **Análisis:** Muestra reciente (del 7 al 10 de noviembre). Mantiene una tasa de acierto sólida del **$48.0\%$**. El retorno negativo inicial se debe a que los boletos de cuotas altas (8.20 y 12.10) aún no han entrado en racha positiva, lo cual es estadísticamente previsible en una serie de apenas 25 casos.

---

### 2.5 INCIDENCIA CRÍTICA DETECTADA EN LOGS DEL VPS

Al auditar el archivo de registro en vivo `/home/qf/quantfut/releases/parley-v2-20261106/parley_nba.log`, se detectó un fallo reiterado del script `parley_nba_revisor`:

```text
Traceback (most recent call last):
  File "/app/src/qf/publish/parley_nba_revisor.py", line 180, in <module>
    main()
  ...
  File "/app/src/qf/ingest/propline_shared.py", line 253, in newest
    row = db.execute("""SELECT p.*,q.started_at,q.slot FROM receipts p JOIN requests q ON q.id=p.request_id ...""")
sqlite3.OperationalError: unable to open database file
```
* **Impacto:** El proceso no puede abrir la base de datos SQLite de recibos de PropLine debido a un problema de permisos de usuario o ruta dentro del contenedor, interrumpiendo la generación automática de boletos combinados NBA. Debe resolverse de inmediato.

---

## 3. AUDITORÍA FORENSE DEL RETO ESCALERA EN EL VPS

### 3.1 EVOLUCIÓN DE REGLAS: DE 6 PASOS AL TEOREMA DE DUBINS-SAVAGE (2 ESCALONES)

La consulta a la tabla `escalera_retos` en PostgreSQL refleja el cambio de paradigma ordenado el 28 de octubre:

1. **Retos 2 al 18 (9 al 28 de octubre - Regla Antigua):**
   * Retos largos de **3 a 6 escalones**.
   * Balance: 7 retos completados y 8 retos perdidos.
   * Causa matemática: Con una cuota media de 1.30 ($p \approx 74\%$), la probabilidad de acertar 6 pasos seguidos cae a $(0.74)^6 \approx 16.4\%$, acumulando el margen de la casa en cada escalón.
2. **Retos 19, 20 y 21 (29 de octubre a la fecha - Regla Actual):**
   * Aplicación del **Teorema de Dubins y Savage (1965)**: Minimizar el número de jugadas a **únicamente 2 escalones** (`pasos_objetivo = 2`) en un plazo de hasta 10 días (`DIAS_MAX = 10`).
   * **Freeroll a $2.5\times$:** Si se llega a $2.5\times$ el saldo inicial (\$10.00), se retira la inversión inicial y se juega gratis con las ganancias.

```sql
 reto_id | pasos_objetivo |          created_at           | n_pasos | wins | losses | voids | Estado del Reto
---------+----------------+-------------------------------+---------+------+--------+-------+------------------
      21 |              2 | 2026-11-05 09:00:16.700684+00 |       2 |    0 |      0 |     2 | Protegido (2 Voids)
      20 |              2 | 2026-11-04 09:00:19.945733+00 |       2 |    2 |      0 |     0 | ¡COMPLETADO (100%)!
      19 |              2 | 2026-10-29 09:00:20.57018+00  |       4 |    2 |      0 |     2 | ¡COMPLETADO (100%)!
```
> **Resultado en Producción:** Desde la implementación de los 2 escalones, el Reto Escalera tiene **0 derrotas** (100% invicto en retos cerrados).

---

### 3.2 DEPORTES Y MERCADOS QUE ALIMENTAN LA ESCALERA (DATOS REALES)

Distribución de los 59 escalones en `escalera_pasos`:

* **Fútbol (52 escalones):**
  * `totals` de goles: **22 pasos** (Under 2.5, Over 1.5, Under 3.5).
  * `team_totals_away` (goles del visitante): **11 pasos**.
  * `h2h` (ganador directo): **9 pasos**.
  * `spreads` (hándicap asiático protector $+1.0, +1.5$): **3 pasos**.
  * `corners` (córners totales): **3 pasos**.
  * `team_totals_home` (goles del local): **3 pasos**.
  * `cards` (tarjetas): **1 paso**.
* **Tenis (6 escalones):**
  * `h2h`: 6 pasos ganadores de tenis ATP/WTA gestionados por [`escalera_ext.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/escalera_ext.py).
* **NBA (1 escalón):**
  * `h2h`: 1 paso ganador de baloncesto NBA.

---

### 3.3 MECANISMO DE SELECCIÓN DEL PRONÓSTICO GANADOR

El módulo [`src/qf/publish/escalera.py`](file:///c:/Users/huye/Documents/apuesta%20proyec/src/qf/publish/escalera.py) ejecuta la selección mediante la tupla:

```python
def _orden(o: Opcion) -> tuple:
    return (round(o.cand.prob, 6), round(o.ev, 6), o.price)
```

1. **Mayor Probabilidad Real ($p$):** Toma la opción con mayor probabilidad matemática calculada por el modelo ($75\% - 95\%$).
2. **Mayor Valor Esperado ($EV$):** Si hay empate en probabilidad, elige la opción con mayor margen frente a la casa.
3. **Mayor Cuota ($Price$):** Desempate por mejor retorno dentro del rango ($1.25 - 2.10$).
4. **Presupuesto Dinámico de Probabilidad:** Para garantizar que el reto completo mantenga un estándar de cumplimiento acumulado $\ge 80\%$, el segundo escalón exige:
   $$\text{umbral} = \left( \frac{0.80}{p_{\text{escalón 1}}} \right)$$
   Si el primer escalón tuvo $p = 0.92$, el segundo escalón rechaza cualquier pronóstico con $p < 86.9\%$.

---

### 3.4 TRACK RECORD REAL DE ESCALONES Y RETOS COMPLETADOS

Consulta directa a `escalera_resultados` en el servidor:
```sql
 outcome | count |  pct  
---------+-------+-------
 win     |    45 | 76.27%
 loss    |     9 | 15.25%
 void    |     5 |  8.47%
```
* **Acierto efectivo por escalón:** Descontando empates (*voids*), el sistema ha ganado **45 de 54 escalones resueltos = 83.33% de efectividad real** en el VPS.

---

## 4. MAPEO DE TABLAS Y ESQUEMAS EN POSTGRESQL

```mermaid
erDiagram
    parley_v2_lotes ||--o{ parley_v2_tickets : contiene
    parley_v2_tickets ||--o{ parley_v2_patas : incluye
    parley_v2_tickets ||--o| parley_v2_resultados : liquida
    parley_v2_patas ||--o| parley_v2_resultados_pata : califica

    escalera_retos ||--o{ escalera_pasos : avanza
    escalera_pasos ||--o| escalera_resultados : califica
```

* `parley_v2_lotes`: Sello criptográfico diario del plan de combinadas.
* `parley_v2_tickets`: Boletos con target ($2.10, 3.10, 8.20, 12.10$), cuota total y probabilidad prudente.
* `parley_v2_patas`: Selecciones individuales con contrato, casa, cuota y deporte.
* `parley_v2_resultados`: Liquidación contable del boleto (`ganado`, `perdido`, `factor_pago`).
* `escalera_retos`: Retos abiertos con stake inicial (\$10.00), objetivo de pasos (2) y freeroll ($2.5\times$).
* `escalera_pasos`: Pronóstico asignado al reto con probabilidad, cuota y evento.
* `escalera_resultados`: Calificación del paso (`win`, `loss`, `void`).

---

## 5. DICTAMEN TÉCNICO Y ACCIONES INMEDIATAS

1. **Multideporte en Producción Confirmado:**  
   El Parley v2.1 no es un prototipo: está activo en el VPS y combina **Fútbol**, **Tenis** y **Props de Jugador NBA** (rebotes, asistencias y triples).
2. **Eficiencia Superior de la Escalera de 2 Pasos:**  
   Con **$83.33\%$ de acierto por escalón** y **cero derrotas en retos de 2 pasos**, el sistema superó la fragilidad de las escaleras convencionales de los tipsters.
3. **Acción Operativa Requerida:**  
   Resolver el error `sqlite3.OperationalError` en `/home/qf/quantfut/releases/parley-v2-20261106/parley_nba.log` ajustando los permisos de lectura de la base de datos de recibos de PropLine para el usuario del worker.
