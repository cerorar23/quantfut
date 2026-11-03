# Auditoría de los tres motores de fútbol, fuentes nuevas y backtest temporal (24-oct-2026)

Pregunta del titular: ¿usan ya los tres motores las APIs nuevas de cuotas e historial? ¿Entró la data nueva? Calibrar y
validar con backtest temporal sin trampas (RPS, log-loss, Brier, ROI con Kelly fraccional cuando P_modelo > P_mercado).
Continúa la auditoría del 21-oct (`docs/auditoria_motores_20261021.md`). **Solo lectura**: no se cambió nada en
producción. Consultas SELECT a la base, registros del worker y walk-forward descargado. Scripts y salidas en
`harness/auditoria_20261024/`.

## Resumen

| # | Gravedad | Hallazgo | Efecto |
|---|---|---|---|
| 1 | **crítica** | **API-Football pasó al plan gratuito** el 22-oct ~21:45 UTC (`Free plans do not have access to the Ids parameter` / `…this season`). Fallan resultados, calendario, clasificación y, con ellos, el xG y las estadísticas de partido | 0 partidos cerrados desde el 22-oct; 76 huérfanos; calendario sin altas nuevas (el último programado es el 9-nov); nada se liquida |
| 2 | **crítica** | El worker `quantfut-worker-propline:a521569` mezcla versiones: `estadisticas_mercado.py` es la de `ba66746` y `alta_prob.py` la de `8be381b`, anteriores a #72/#74, mientras `alta_prob_datos.py` y `escalera_datos.py` son las de `main` | El diario del 24-oct falló en alta probabilidad, ampliada, escalera y parley (`AttributeError: … 'disponible'`). El 23-oct no hubo precio (27 partidos `sin_precio`: The Odds API sin créditos). **Dos días sin pronósticos del Motor B/C** |
| 3 | alta | PropLine nunca escribe `window_tag='close'` (decisión de diseño correcta: no fabricar cierres), pero **nadie carga los cierres de PropLine** (`/odds/closing`, ya archivados) a `odds_snapshots` | CLV, sombra sharp, sombra de retadores y comparación con el mercado del entrenamiento sin cierres desde el 22-oct 18:50 UTC. La puerta comercial (CLV ≥ 300) está congelada |
| 4 | alta | De las 8 casas de `SOFT_BOOKS` solo **1xbet** está en PropLine (no hay bet365, Betano, William Hill, 888, Betsson ni Coolbet; Betway solo como `betway_za`) | Cuota de referencia de los pronósticos casi sin casas; la sombra sharp ve `offers_seen: 0` |
| 5 | media | El chequeo diario da «calendario OK», «xG al día» y «liquidación al día» con el proveedor caído; solo «huérfanos» falla | Falsa tranquilidad |
| 6 | media | La data nueva (SofaScore/Apify: xG y alineaciones; PropLine: box score, cierres, liquidaciones) **solo se archiva**: no llega a `matches` ni al Motor A | Correcto según la decisión del 23-oct (no reentrenar por capturar); hoy es además la única vía para sustituir a API-Football |
| 7 | baja | `httpx` en nivel INFO escribe la URL de Telegram con el token del bot en `daily.log`, `health.log` y `fixtures.log` | — |

## 1. ¿Usan los motores las APIs nuevas?

| Motor | Cuotas en vivo | Historial / cierres | Estadísticas |
|---|---|---|---|
| **A** (Dixon-Coles) | No las necesita para predecir. El consenso de mercado de `predictions` lee `odds_snapshots` | Entrena contra `window_tag='close'`: **sin cierres nuevos desde el 22-oct** (último de The Odds API). La frescura (≤ 30 días) aún pasa el 1-nov; fallaría hacia el 21-nov | Goles y xG de API-Football: **cortados desde el 22-oct** |
| **B** (Pinnacle sin margen) | **Sí, PropLine** desde el 24-oct 01:38 UTC (`ODDS_PROVIDER=propline`): 1X2, totales, hándicap, ambos marcan, córners y tarjetas de Pinnacle; 195.315 filas, 192 partidos | Liquida con resultados de API-Football: **parado** | — |
| **C** (córners/tarjetas) | Precio de córners de PropLine (mismo lector que B) | — | Córners/tarjetas de API-Football: **parados** |

Lo que entra de PropLine a `odds_snapshots`: solo `pinnacle` y `onexbet` (filtro `SOFT_BOOKS + SHARP_BOOK`). Faltan en
`odds_snapshots`: doble oportunidad (0 filas) y córners por equipo (0 filas), aunque el adaptador los contempla. Ligas sin
archivo en la última pasada: Dinamarca y Ligue 2.

## 2. Backtest temporal del Motor A (sin trampas)

**Diseño.** Walk-forward de la configuración de producción (`wf_prodnuevo`, la del 22-oct): cada 30 días se reajusta
solo con partidos anteriores al corte y se predice el bloque siguiente. Calibración y peso de mezcla se estiman cada mes
**solo con partidos anteriores** (ventana creciente, mínimo 1.500). Apuestas al **cierre de Pinnacle con margen**,
una por partido (la de mayor EV) y solo si `p_modelo > p_mercado` y EV > 0; Kelly 0,25 con tope 5 %. IC95 por
bootstrap de días. `check_leakage`: el xG de cada partido se registra después del partido (es su resultado; no entra en
su propia predicción); el 38 % de los inicios coincide exactamente con otro (jornadas), no fecha sin hora.

**Sesgo conocido:** media vida, ridge y suma cero se eligieron el 21-oct mirando estos mismos 11.920 partidos. Las cifras
del A son por tanto algo optimistas; la prueba limpia es el periodo posterior al 22-oct, que todavía no tiene resultados.

### 2.1 Probabilidades (n = 8.131 con capas, 2024-05 → 2026-10)

| | RPS | Log-loss | Brier | ECE |
|---|---|---|---|---|
| Mercado (Pinnacle Shin, cierre) | **0,19665** | **0,97648** | **0,58191** | **0,0090** |
| Motor A | 0,20319 | 0,99746 | 0,59575 | 0,0131 |
| Motor A + temperatura (pasado) | 0,20293 | 0,99675 | 0,59532 | 0,0106 |
| Mezcla A + mercado (peso del pasado) | 0,19665 | 0,97648 | 0,58191 | 0,0090 |

- ΔRPS A − mercado: **+0,0065, IC95 [+0,0053, +0,0078]**. El mercado gana en las 13 competiciones (de +0,0043 en
  Premier y Argentina a +0,021 en Europa League).
- El peso óptimo del A en la mezcla log-lineal, estimado cada mes con el pasado, es **0,00** en todos los meses: el
  ensemble de-vigged es el propio mercado. Coincide con `meta.py` (0,108 en su día) y con la literatura reciente: el
  cierre sin margen es la referencia más difícil.
- Fiabilidad: el A es algo **tímido con los favoritos** (local 70-80 %: promete 74,4 %, ocurre 80,1 %; > 80 %: 84,5 %
  frente a 89,3 %).

### 2.2 ROI con Kelly fraccional cuando P_modelo > P_mercado

| Regla | Apuestas | Acierto | Cuota media | ROI plano | IC95 | Banca Kelly 0,25 |
|---|---|---|---|---|---|---|
| EV > 0 | 7.612 | 26,7 % | 4,49 | **−11,0 %** | [−15,1 %, −7,1 %] | → 0 (ruina) |
| EV > 3 % | 6.701 | 25,1 % | 4,69 | **−12,0 %** | [−16,2 %, −8,0 %] | → 0 (ruina) |

Las discrepancias del A con el mercado son ruido, y caen sobre todo en visitantes y empates a cuota alta (la timidez
con los favoritos lo empuja hacia ellos). **No hay alfa.** En el último año del modelo activo (validación del
2026.10.22, n = 421 apuestas) el ROI es −23,9 %, IC95 [−38,6 %, −9,3 %].

### 2.3 Calibración probada (coherente con los ~150 mercados)

La temperatura del 1X2 rompe la coherencia de la matriz de marcadores. Se probó su equivalente coherente: estirar la
supremacía `(log λ − log μ)/2` por `k` conservando el total, con `k` elegido cada mes por la verosimilitud del marcador
exacto (n = 10.374):

| | Δ | IC95 |
|---|---|---|
| RPS 1X2 | −0,00016 | [−0,00031, −0,00000] |
| Log-loss 1X2 | −0,00061 | [−0,00114, −0,00004] |
| Log-loss más/menos 2,5 | −0,00018 | [−0,00039, +0,00005] |
| Log-loss ambos marcan | +0,00008 | [−0,00008, +0,00023] |

`k` ≈ 0,97-0,98 (encoge, al revés que la temperatura del 1X2, que pide afilar). El efecto se reduce a la mitad en la
segunda mitad del periodo (ΔRPS −0,00009). **No se recomienda promover**: es una mejora en el límite del ruido. La brecha
con el mercado (0,0065) es de información, no de calibración; ningún reescalado monótono la cierra.

## 3. Motores B y C en producción (calibración real, tramo 73-95 %)

Pronósticos sellados y liquidados (base + ampliada), a 22-oct:

| Producto | Mercado | n | Prometido | Real | ROI a la cuota de referencia | Log-loss | Brier |
|---|---|---|---|---|---|---|---|
| Ampliada | hándicap (B) | 601 | 85,5 % | 88,7 % | +1,8 % | 0,341 | 0,098 |
| Ampliada | doble oportunidad (B) | 340 | 78,8 % | 80,3 % | −2,2 % | 0,498 | 0,159 |
| Ampliada | córners (C) | 387 | 80,5 % | 79,6 % | −8,5 % | 0,502 | 0,161 |
| Ampliada | goles (B) | 318 | 82,0 % | 81,1 % | −3,0 % | 0,483 | 0,153 |
| Base | doble oportunidad (B) | 65 | 82,1 % | 76,9 % | −6,7 % | 0,549 | 0,181 |
| **Total** | | **2.214** | **82,2 %** | **83,1 %** | **−3,1 %** | 0,446 | 0,139 |

- Bien calibrados en conjunto (diferencia +0,9 puntos, z ≈ +1,1). Ninguna desviación por mercado es significativa;
  la doble oportunidad de la base (−5,2 puntos, n = 65) es la que hay que vigilar.
- El hándicap sale **por encima** de lo prometido en base y ampliada (+3,2/+3,4 puntos): posible sesgo conservador del
  anclaje en hándicap asiático; con más muestra, revisar la conversión.
- ROI negativo esperado en una línea de acierto (se paga el margen de la casa). Córners: probabilidad bien calibrada
  pero −8,5 % a la cuota de referencia: las cuotas de córners de esas casas son malas.

## 4. Modelos de la lista del titular

| Modelo | Estado en QuantFut | Veredicto con nuestros datos |
|---|---|---|
| Dixon-Coles (1997) | Motor A en producción, con xG, decaimiento 270 días y encogimiento | Bien calibrado; −0,0065 RPS frente al cierre |
| Poisson bivariado / inflado en diagonal (Karlis-Ntzoufras) | Probado el 21-oct | Bivariado: peor que DC. Diagonal: −0,0005 log-loss del 1X2 (A6 pendiente) |
| Jerarquía bayesiana / EM | El A ya hace encogimiento parcial por liga (empírico-bayesiano) | Lo útil es un prior para ascendidos (21-oct: RPS 0,2333 → 0,2136 en equipos poco conocidos) |
| Redes bayesianas (Constantinou) | Equivale a F3/F12 (bajas, fatiga, motivación) | Viable solo con datos de bajas/XI fiables; hoy dependen de API-Football, caído |
| T-GNN / ST-GNN | No | Sin evidencia de que bata a DC + mercado antes del partido con ~50 mil partidos; solo investigación |
| Hawkes en juego | No | Es para apuestas en vivo; no tenemos producto en vivo ni flujo de eventos |
| VAEP / Atomic-VAEP | No | Exige eventos acción a acción (Opta/StatsBomb/Wyscout); SofaScore no basta |
| Ensembles de-vigged | Motor B + `meta.py` | Medido arriba: el peso óptimo del A es 0; el ensemble es el mercado |

## 5. Qué hay que hacer (orden)

1. **Titular:** renovar el plan de API-Football o decidir sustituirlo (resultados y calendario con PropLine `/scores` y
   `/results`; xG y alineaciones con SofaScore/Apify). Sin esto no hay liquidación ni entrenamiento útil el 1-nov.
2. **Claude, con visto bueno:** desplegar el worker con `estadisticas_mercado.py` y `alta_prob.py` de `main` (el resto ya
   coincide salvo `config.py`, `propline_*` y `api/main.py`, que hay que revisar antes). Ensayo con `--dry-run` del
   diario antes de las 09:00 UTC.
3. **Claude:** cargador de cierres de PropLine a `odds_snapshots` (`window_tag='close'`, fuente propia, solo líneas con
   `closing_at` ≤ inicio, sin mezclar con capturas horarias) para reabrir CLV, sombra y comparación con el mercado.
4. **Titular:** revisar `SOFT_BOOKS` frente a las 97 casas de PropLine en las que apuestan sus clientes.
5. **Claude:** que el chequeo diario detecte el plan gratuito y el calendario sin altas; bajar `httpx` a WARNING.
6. Motor A: no reentrenar ni calibrar ahora. Tras el 1-nov y con resultados restablecidos: prior de ascendidos y A6;
   repetir este backtest sobre el periodo posterior al 22-oct, que es la única muestra no vista por la selección de
   hiperparámetros.
