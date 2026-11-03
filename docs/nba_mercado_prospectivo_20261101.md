# NBA — prueba prospectiva contra Pinnacle (captura del precio al sellar cada cohorte)

Complementa la comparación retrospectiva (`docs/nba_comparacion_pinnacle_20261101.md`). Aquí el pronóstico se sella con hash antes del salto y el precio lo captura un paso aparte que no puede influir en él. Es la única prueba sin sesgo de selección: las temporadas retrospectivas ya se inspeccionaron con v1.1-v1.5. **No genera apuestas, stakes ni picks.**

Código: `apps/nba/src/nba/live_market.py` (`capture`, `report`). Pruebas: `tests/test_live_market.py` (13). Protocolo: `apps/nba/nba_vs_market_live_protocol.json`, congelado antes de existir ningún precio (hash en `.local/normalized/nba_f6_live13_market/protocol_frozen.json`; `report` se niega a correr si cambia). **No se ha llamado a la API**: la captura está bloqueada en código antes del 2026-11-01.

## Qué hace
- **`capture`**: una petición al endpoint de cuotas actuales de The Odds API (`basketball_nba`, `bookmakers=pinnacle`, `h2h`, decimal; ~1 crédito). Guarda la respuesta cruda sin tocar (`market/seal_raw.json`), su recibo (hora de recepción, sha256, créditos, saldo, hash del `bundle.json` sellado) y un registro de intentos. **Escribe una sola vez** por fase y cohorte; un error HTTP se registra y no se reintenta; un coste distinto de 1 se marca. No se imprime ni guarda la clave.
- **Fase `seal`** (obligatoria): inmediatamente después de `forecast`; se acepta solo si `recepción − sellado` está entre 0 y 15 min, y una captura tardía se rechaza **antes de gastar el crédito** (si no, el precio y el pronóstico no describirían el mismo momento).
- **Fase `close`** (opcional, +1 crédito/día): antes del primer salto de la cohorte; solo sirve para describir si el mercado se mueve hacia el modelo (CLV), no entra en la decisión.
- **`report`**: lee todas las cohortes selladas (verificando sellos y recibos de resultado con `LiveCohort`), empareja precio y pronóstico de ganador por partido (nombres con alias de los Clippers, salto a ±10 min, Pinnacle, no iniciado, actualización del libro de ≤30 min y no futura) y calcula con el mismo código que el retrospectivo: Brier/log loss de modelo, mercado y mezcla, peso de información *c* con IC por fechas, sensibilidad a la potencia, minutos al salto y el bloque CLV. Una cohorte rota se lista en `problems` y no oculta a las demás.

## Regla de decisión (congelada)
Se decide **una vez cuando haya 400 partidos evaluados con precio válido y otra al final de la temporada regular** (la final prevalece); entre medias son lecturas interinas sin veredicto. Cobertura mínima 85 % (partidos evaluados con precio válido / evaluados). *Mejor que el mercado* si el límite superior de (Brier modelo − Brier mercado) < 0; *aporta información* si el límite inferior de *c* > 0; si no, *sin evidencia de información añadida* (resultado válido y esperable). El CLV es descriptivo.

## Rutina diaria (desde 1-nov, en `apps/nba`, `PYTHONPATH=src`, entorno `.venv`)
```bash
N=.local/normalized
# 1) sellar (ya existente)
python -m nba.multimarket_v13_live forecast --model $N/nba_f6_live13_model_20261021b ... --output $N/nba_f6_live13_cohorts/AAAA-MM-DD
# 2) en los 15 min siguientes: precio al sellar (~1 crédito)
python -m nba.live_market capture --cohort $N/nba_f6_live13_cohorts/AAAA-MM-DD --key-file ../../.env
# 3) opcional, antes del primer salto: precio cercano al cierre (~1 crédito)
python -m nba.live_market capture --cohort $N/nba_f6_live13_cohorts/AAAA-MM-DD --key-file ../../.env --phase close
# 4) tras los partidos (ya existente): resultados oficiales
python -m nba.multimarket_v13_live results --cohort $N/nba_f6_live13_cohorts/AAAA-MM-DD
# 5) informe acumulado
python -m nba.live_market report --cohorts $N/nba_f6_live13_cohorts --protocol nba_vs_market_live_protocol.json --output $N/nba_f6_live13_market
```
Coste: 30-60 créditos al mes (1 o 2 por día de partidos). `--reserve` (por defecto 2.000) impide gastar si el último saldo conocido quedaría por debajo.

## Ensayo
Con la cohorte real de ensayo del 21-oct (copiada al directorio temporal; respuesta de la API **sintética**, sin red): 11 de 11 partidos con precio válido, incluido «LA Clippers» como local. No hay resultado de mercado: el ensayo valida el emparejado y la captura. Pendiente de datos reales desde el 1-nov.

## Límites y decisiones abiertas
- **Dónde corre la captura.** Decidido (22-oct): en el servidor, en un contenedor propio y de corta vida (cron cada 5 min, `nba-live13-price`), con su propio archivo de clave de solo lectura, las cohortes en solo lectura y un libro de presupuesto de 2 peticiones/día y 70 créditos/mes; incluye la fase `close`. El productor no se toca. Implementado y no desplegado: ver `docs/nba_captura_precio_servidor_propuesta_20261022.md` (runbook, vuelta atrás). En los comandos de arriba, `capture` solo sirve para pruebas manuales; en el servidor lo hace `capture-pending`, y `report` lee de `--market-root`.
- La cohorte se sella por la mañana y el precio es de esa hora, no el cierre: el CLV descriptivo mide cuánto se mueve el mercado después.
- Con ~10 partidos por día, 400 partidos son unos 40 días de juego.
- Solo ganador. Totales y puntos de equipo necesitarían su propia captura y línea (otros mercados en la misma petición costarían créditos adicionales).
