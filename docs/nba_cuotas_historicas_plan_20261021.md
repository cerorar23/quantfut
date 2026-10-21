# NBA — plan de compra de cuotas históricas de partido (The Odds API)

Código: `apps/nba/src/nba/odds_history.py` (comandos `plan`, `fetch`, `load`). Pruebas: `apps/nba/tests/test_odds_history.py`. Plan generado: `apps/nba/.local/normalized/nba_f6_odds_plan_20261021/plan_h2h.json`. **No se ha gastado ningún crédito.**

## Para qué
Es lo único que falta para saber si el modelo (v1.3) aporta algo frente al mercado: comparar sus probabilidades de ganador contra la probabilidad sin margen de Pinnacle, y medir CLV. Hoy no hay cuotas históricas de partido en ninguna fuente ya descargada: ESPN no devuelve líneas pasadas y los CSV de GitHub son muestras de props sin partido.

## Qué se compra
- 325 snapshots (un día de partidos cada uno) de 2024-25 y 2025-26, región `eu` (incluye Pinnacle), mercado `h2h`. Coste: 10 créditos por snapshot = **3.250 créditos**.
- Hora de cada snapshot: 30 min antes del primer salto del día (hora real de salto en los 325 días; ningún día usa hora estimada).
- Limitación: el snapshot sirve a todos los partidos del día, pero los de noche se ven con la línea de hace horas, no el cierre. Se guarda `minutes_to_tipoff` y la antigüedad del precio (máximo 6 h) para medirlo. No es CLV de cierre real.

## Por qué no ahora
Saldo real el 21-oct: 4.092 créditos; fútbol gasta ~300/día hasta el reset del 1-nov. Presupuesto de noviembre: 20.000 − ~9.000 del vivo − 5.270 de los 527 snapshots de fútbol ya previstos = ~5.700 libres. Por eso el plan es **por fases**: ahora solo `h2h` (3.250); los totales (otros 3.250) en diciembre.

## Salvaguardas en el código
- `fetch` lanza `PermissionError` antes del 2026-11-01 (verificado hoy).
- Tope por ejecución (`--cap`, por defecto 3.300) y reserva (`--reserve`, por defecto 14.500: se detiene si el saldo bajaría de ahí).
- Cada respuesta se escribe a disco y se anota en `manifest.jsonl` (sha256, créditos, saldo) antes de pedir la siguiente; lo ya descargado nunca se vuelve a pagar.
- Se detiene a la primera respuesta distinta de 200 o si un snapshot cuesta algo distinto de lo previsto. Sin reintentos.
- Solo lee `ODDS_API_KEY` del archivo indicado con `--key-file`; no imprime la clave.

## Cómo se ejecuta (a partir del 1-nov)
```
python -m nba.odds_history fetch --data <RUN071>/data --api-dir <api_nba> --injuries <reports.jsonl.gz> --cache <cache> --plan-file <plan_h2h.json> --key-file .env --limit 20
python -m nba.odds_history load  ... --output odds_h2h.jsonl.gz
```
Conviene empezar con `--limit 20` y revisar `load` (partidos emparejados, precios descartados) antes de seguir.

## Pendiente después
Cuando haya datos: exportar las probabilidades de ganador de v1.3 por partido y comparar Brier/logloss con `home_no_vig` de Pinnacle en las mismas filas, con el mismo bootstrap por fechas. Eso decide si hay algo que vender.
