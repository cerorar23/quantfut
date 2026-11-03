# NBA — comparación con Pinnacle: lo que queda listo para el 1-nov-2026

Objetivo: saber si la probabilidad de ganador de la v1.3 aporta información que Pinnacle (sin margen) no tiene. **No genera apuestas, stakes ni picks.** El modelo vivo no se toca y el tema de lesiones queda cerrado (v1.5: sin efecto probado en equipo).

Piezas: `nba.odds_history` (plan, compra acotada, carga), `nba.market_compare` (comparación), protocolo `apps/nba/nba_vs_market_protocol.json` congelado **antes de comprar ningún precio** (hash en `apps/nba/.local/normalized/nba_f6_market_20261101/protocol_frozen.json`, con la enmienda registrada; el programa se niega a correr si el protocolo cambia).

## Qué se encontró al revisar el código existente (todo corregido, con pruebas)
1. **Los Clippers se habrían perdido en silencio.** The Odds API dice «Los Angeles Clippers»; el histórico, «LA Clippers». Era el único de 30 nombres que no coincidía (comprobado con los eventos reales ya descargados). Habría descartado ~5,5 % de los partidos como `unmatched_event`. Ahora hay un alias explícito.
2. **Un precio de la víspera podía entrar como si fuera del día.** Cada snapshot lista también partidos de días siguientes; si fallaba la compra de un día, ese partido se emparejaba con un precio de casi 24 h antes, porque el filtro de antigüedad mira la actualización del libro frente al snapshot y no frente al salto. Ahora el snapshot debe caer en el mismo día ET del partido (`snapshot_other_day` en las estadísticas de carga).
3. **Comparación sesgada a favor del modelo.** El snapshot se toma 30 min antes del *primer* salto del día; en un partido de noche el mercado tiene un precio de hace horas mientras el modelo usa reportes hasta T-60. Ahora hay dos brazos: **alineado** (principal: el modelo solo ve información hasta la hora del snapshot) y **tminus60** (secundario: la regla publicada; solo para medir esa diferencia).
4. Faltaban: regla de decisión previa, intervalos del «peso de información», sensibilidad al método de quitar el margen (se añadió el de potencia), estratos por minutos al salto y una prueba de cobertura mínima.

## Qué mide y cómo se decide (protocolo congelado)
- Mercado: Pinnacle `h2h`, un snapshot por día de partidos (30 min antes del primer salto), margen quitado de forma proporcional (potencia como sensibilidad).
- Modelo: v1.3 tal como está publicada, entrenada solo con temporadas anteriores a la evaluada. Temporadas 2024-25 y 2025-26.
- Métricas: Brier y log loss; diferencias pareadas con bootstrap por fechas (400, semilla 20261101). **Peso de información** *c* en `logit p = logit(mercado) + c·(logit(modelo) − logit(mercado))`: 0 = basta el mercado, 1 = basta el modelo; con IC95. Peso ajustado en 2024-25 y aplicado a 2025-26 (walk-forward).
- Cobertura mínima: ≥ 85 % de los partidos con salto conocido emparejados con un precio válido, o esa temporada es «inconclusa».
- Decisión: *mejor que el mercado* si el límite superior de (Brier modelo − Brier mercado) < 0 en ambas temporadas; *aporta información* si el límite inferior de *c* > 0 en ambas y el walk-forward gana al mercado en 2025-26; si no, **sin evidencia de información añadida** (el resultado esperable en un mercado eficiente y válido). Aun si aporta información, es necesario pero no suficiente para uso comercial.
- Descriptivo: estratos por minutos al salto, bins de la brecha modelo-mercado, sensibilidad a la potencia, overround.

## Ensayo de punta a punta (sintético)
Con 325 snapshots **sintéticos** (esquema real de The Odds API, precios inventados, en el directorio temporal; no es resultado): 2.415 precios emparejados (cobertura 100 %, Clippers incluidos), los dos brazos, bootstrap, regla de decisión y salida. El mercado sintético es ruido, por lo que el modelo «gana»: valida el cableado, no dice nada del modelo. Pruebas: `tests/test_market_compare.py` (10), `tests/test_odds_history.py` (9).

## Qué hacer el 1-nov (en `apps/nba`, entorno `.venv`, `PYTHONPATH=src`)
Presupuesto: 3.250 créditos (325 × 10) con `--cap 3300`; con el saldo de 20.000 tras el reset y `--reserve 14500` quedan 16.750. Fútbol gasta ~300/día, ver `docs/nba_cuotas_historicas_plan_20261021.md`. Bloqueado por código antes del 1-nov.
```bash
N=.local/normalized
# 1) prueba de 20 snapshots (200 créditos) y revisar la carga
python -m nba.odds_history fetch --data $N/nba_f6_run71_20261009/data --api-dir .local/raw/api_nba_20261006 \
  --cache .local/raw/nba_odds_h2h_202611 --plan-file $N/nba_f6_odds_plan_20261021/plan_h2h.json --key-file ../../.env --limit 20
python -m nba.odds_history load --data $N/nba_f6_run71_20261009/data --api-dir .local/raw/api_nba_20261006 \
  --cache .local/raw/nba_odds_h2h_202611 --plan-file $N/nba_f6_odds_plan_20261021/plan_h2h.json
# esperar: matched ≈ partidos de esos días; unmatched_event y no_pinnacle ≈ 0; snapshot_other_day solo de días futuros;
# si salen muchos «invalid_or_stale_price», no seguir y revisar antes de gastar más.
# 2) resto (omitir --limit); lo ya descargado no se vuelve a pagar
# 3) comparación
python -m nba.market_compare --data $N/nba_f6_run71_20261009/data --protocol nba_vs_market_protocol.json \
  --v12-protocol multimarket_v12_protocol.json --injuries $N/nba_complete_injury_final_20261006/reports.jsonl.gz \
  --api-dir .local/raw/api_nba_20261006 --plan-file $N/nba_f6_odds_plan_20261021/plan_h2h.json \
  --cache .local/raw/nba_odds_h2h_202611 --output $N/nba_f6_market_20261101
```
La salida (`market_comparison.json`, `inputs_market.json`) queda en esa carpeta, con el veredicto en `decision`.

## Límites
- No es el cierre: el precio es el de ~30 min antes del primer salto del día; no hay CLV real. El brazo alineado lo trata de forma justa, pero un mercado cercano al cierre sería más exigente para el modelo.
- Solo ganador (h2h). Totales y puntos de equipo, en diciembre con otros 3.250 créditos.
- Retrospectivo y exploratorio; las temporadas ya se inspeccionaron con v1.1-v1.5.

## Mejora recomendada (no implementada): prueba prospectiva
Capturar el precio actual de Pinnacle en el momento de sellar cada cohorte (≈1 crédito por día con el endpoint de cuotas actuales) y compararlo con los pronósticos ya sellados. Es la única prueba sin sesgo de selección y cuesta ~30 créditos al mes. Pendiente de decisión del titular.
