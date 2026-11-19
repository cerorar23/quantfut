# Tenis v2: fechas de nacimiento desde las edades de TML y capa de edad 2.2 (17-nov-2026)

## Problema

La capa de edad (`docs/tenis_capa_edad_20261117.md`) no actuaba en producción: `entradas.edad_dif` salía `null`. `tenis-db` solo tiene TML y TML no guarda
fechas de nacimiento; las de SofaScore cubren apenas el 7 % de los jugadores de la copia de desarrollo (1.249 de 16.241).

## Solución

Cada partido de TML trae `winner_age` y `loser_age`: la edad decimal (3 decimales, ≈ 0,4 días) en `tourney_date`. `nacimiento = tourney_date − edad × 365,25 d`, mediana por jugador.
`carga/nacimientos_tml.py` lo hace con estas reglas (lo dudoso se descarta y se cuenta, nunca se inventa):

- Solo edades de 12 a 60 años. Un jugador con estimaciones inconsistentes (p90 − p10 > 30 días) se descarta (8 de 13.205).
- No toca jugadores que ya tengan fecha de cualquier fuente (SofaScore es exacta y manda). Un id de TML con más de un jugador no anulado es ambiguo y se descarta.
- Aserción `fecha_nacimiento` de fuente `tml` con recibo **retro** (la exportación PIT solo usa aserciones retro), cuyo original es la lista de estimaciones con su n y dispersión.
- Idempotente; `--ensayo` cuenta sin escribir. Se encadena a la carga semanal de TML (`ops/nacimientos_tml.sh`, lunes 12:00 con el candado del motor).

### Validación (1.135 jugadores con fecha exacta de SofaScore y edades de TML)

| | error absoluto |
|---|---|
| mediana | 0,0 días |
| p90 / p99 | 0,2 / 0,4 días |
| máximo | 9 días (un jugador con 2 partidos) |

`ATP_Database.csv` (también en el snapshot de TML) se descartó como fuente: solo cubre ATP y mezcla fechas exactas con marcadores de año (`19810101`).

## Efecto en el modelo (walk-forward 2019-24, ajuste con temporadas anteriores, reserva 2025-26 intacta)

Con las edades de TML la cobertura pasa de 62-73 % (ATP) y 73-85 % (WTA) a 99,5-99,8 %, y la capa se reajusta con todo. Predicciones base idénticas (sha256 `af77e927…`).

| | ATP | WTA |
|---|---|---|
| Δ log-loss vs capa de pendiente | **−0,0038** [−0,0045; −0,0030], 6/6 temporadas | **−0,0033** [−0,0043; −0,0024], 5/6 (2022: +0,0019) |
| antes (solo SofaScore) | −0,0022 | −0,0026 |
| Δ vs Elo recalibrado | −0,0097 | −0,0086 |
| Pendiente de calibración | 0,902 → 0,939 [0,910; 0,965] | 0,975 → 1,016 [0,967; 1,062] |
| Coeficientes congelados | b 0,9902, β −0,1715, escala 6,02 | b 0,9913, β −0,1373, escala 6,05 |

Artefacto `apps/tenis/artefactos/tenis-2.2-capa-edad.json` (`sha256` `b6d243c3…`, `tenis-2.2+b6d243c306a2`): los mismos hiperparámetros base que el 2.1 y solo cambia la capa.
Informe: `evaluacion_wf_capa_edad_tml.json`. El 2.1 se conserva en la carpeta para la vuelta atrás.

## Cómo se midió

1. Las 10.289 fechas estimadas se cargaron en `tenis_dev` con el propio cargador (solo-anexar; segunda ejecución: 0 escritas).
2. Reexportación PIT a una carpeta nueva (124 s; mismas 260.165 claves). `evaluar_wf.py` ahora acepta `--export`.
3. `evaluar_wf.py --export …` y `congelar_capa_edad.py`.

## Límites

- La edad estimada de un jugador con pocos partidos puede errar unos días: irrelevante frente a la desviación de 6 años de la diferencia de edad.
- Jugadores sin ningún partido con edad en TML (o sin alias de TML en la base) siguen sin fecha; la capa no actúa para esos partidos (solo la pendiente).
