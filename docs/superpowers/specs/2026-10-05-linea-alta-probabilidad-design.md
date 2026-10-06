# Línea de alta probabilidad — diseño

Fecha: 2026-10-05 · Estado: aprobado por el usuario sección a sección, pendiente
de revisión del documento.

## Por qué

Los clientes del usuario valoran acertar más que batir a la casa, y no toman
todos los picks. El criterio de valor actual acierta ~25-30 % a cuota media
~3,9; para un cliente que toma unos pocos picks es casi una moneda al aire
(simulación: 45-51 % de clientes en ganancia tras 10-100 picks).

Se crea una línea **aparte** de pronósticos con probabilidad real ≥ 80 %. No
sustituye a los picks de valor ni toca su puerta comercial.

Lo que ya está medido (football-data, 7 ligas, 2019/20-2024/25, 14.294
partidos, firma `d5cbc3151164`):

| Candidato ≥ 80 % | % de partidos | Prob. media | Acierto real |
|---|---|---|---|
| Favorito 1X2 | 5,2 % | 84,6 % | 84,8 % |
| Doble oportunidad (mejor de 1X/X2/12) | 40,7 % | 87,2 % | 87,8 % |

Las probabilidades de Pinnacle sin margen están calibradas: lo prometido se
cumple. Con las casas de los clientes, estos pronósticos **no tienen valor**
(favorito ≥ 80 %: ROI −2,4 %, EV al cierre −2,6 %; 0 casos con casa pagando
≥ 2 % sobre el justo). La línea es de acierto, no de rentabilidad, y se
comunica así.

## Alcance

Dentro:
- Mercados: 1X2, doble oportunidad (1X, X2, 12) y goles (más de 1,5; menos de
  3,5; menos de 4,5).
- Publicación inmediata, sellada en la cadena de hashes, gratis y pública en
  la web (cuentas y cobros siguen fuera de alcance).
- Historial público de acierto prometido frente a real.
- Pausa automática si el acierto real queda claramente por debajo del
  prometido.

Fuera:
- Cambios en `picks`, `v_track_record`, la puerta de CLV o
  `PUBLISH_PICKS_ENABLED`.
- Probabilidades del modelo propio (Dixon-Coles): no deciden nada aquí.
- Combinadas, stakes, tiers gratis/pago.
- Telegram como canal de estos pronósticos (solo alertas operativas, como hoy).

## 1. Selección

### Fuente de probabilidad

Siempre Pinnacle sin margen, con `settings.devig_method` (Shin):

- **1X2:** probabilidad justa de cada resultado del snapshot de Pinnacle.
- **Doble oportunidad:** suma exacta de dos resultados del 1X2 devigado
  (`1X = p_local + p_empate`, etc.).
- **Goles:** goles esperados de mercado. Se buscan `λ_local`, `λ_visita` tales
  que el modelo Dixon-Coles con la `rho` del artefacto activo reproduzca las
  probabilidades justas de Pinnacle del 1X2 y de UNA línea de totales de
  medio gol (2,5 preferente; 3,5 si no hay 2,5), por mínimos cuadrados. Con
  esas λ se calculan más de 1,5, menos de 3,5 y menos de 4,5.
  - Sin línea de medio gol de Pinnacle en el snapshot, ese partido no tiene
    candidatos de goles. Sin relleno con el modelo.
  - Las líneas de cuarto de gol (2,25; 2,75…) no se usan para el ajuste.
  - Si el ajuste no reproduce las entradas (error absoluto > 0,01 en alguna
    probabilidad), no hay candidatos de goles para ese partido.
  - Un mercado de goles solo se habilita si pasa la prueba histórica de la
    sección 4.1.

### Regla de elección

Por partido:

1. Candidatos = todas las selecciones de los mercados habilitados con
   probabilidad en **[0,80; 0,95]**. El tope evita obviedades (p. ej. menos
   de 5,5 goles al 98 %).
2. Se publica el candidato de **menor** probabilidad (el más informativo y el
   que más paga sin bajar del 80 %). Empate exacto: 1X2 > goles > doble
   oportunidad.
3. Sin candidatos, ese partido no tiene pronóstico. No se fuerza uno.

Constantes en un único sitio (`publish/alta_prob.py`): `PROB_MIN = 0.80`,
`PROB_MAX = 0.95`, `MAX_EDAD_PRECIO = 6 h`, `HORIZONTE = 36 h`, y
`MIN_LEAD = picks.MIN_LEAD` (15 min), la misma guarda que la publicación.

### Cuándo

- Dentro del job diario de las 08:00 UTC (`publish/daily.py`), para partidos
  `scheduled` de competiciones activas con kickoff en las próximas 36 h.
- Snapshot de Pinnacle: el último disponible con `as_of ≥ ahora − 6 h` y
  `kickoff − as_of ≥ 15 min`. Fuentes: las mismas funciones de snapshot que
  usa la sombra sharp (`picks._odds_api_snapshot` / `picks._af_snapshot`);
  los totales solo existen en The Odds API.
- Un pronóstico por partido para siempre (`UNIQUE(match_id)`): si un partido
  ya tiene pronóstico, el job del día siguiente no lo repite.
- Entran todas las competiciones activas con Pinnacle en el 1X2, incluidas las
  ligas "solo sharp" y las copas europeas.

## 2. Datos y sellado

### Migración `db/040_alta_probabilidad.sql`

`alta_prob_picks`:

| Columna | Tipo | Nota |
|---|---|---|
| `alta_id` | UUID PK | `gen_random_uuid()` |
| `match_id` | TEXT NOT NULL UNIQUE | FK `matches` |
| `market` | TEXT NOT NULL | `'1x2'` / `'doble'` / `'goles'` |
| `selection` | TEXT NOT NULL | `home`/`draw`/`away`, `1X`/`X2`/`12`, `over`/`under` |
| `line` | REAL | solo goles (1,5 / 3,5 / 4,5) |
| `prob` | REAL NOT NULL | Pinnacle sin margen, en [0,80; 0,95] |
| `fair_price` | REAL NOT NULL | `1 / prob` |
| `ref_price` | REAL | mejor cuota de `SOFT_BOOKS` para esa selección en el mismo snapshot; NULL en doble oportunidad (ningún proveedor la da) |
| `ref_book` | TEXT | casa de `ref_price` |
| `odds_source` | TEXT NOT NULL | `'the_odds_api'` / `'api_football'` |
| `odds_as_of` | TIMESTAMPTZ NOT NULL | hora del precio de Pinnacle |
| `fit` | JSONB | solo goles: `λ_local`, `λ_visita`, `rho`, línea usada, error del ajuste |
| `decided_at` | TIMESTAMPTZ NOT NULL | `now()` |

`alta_prob_results`: `alta_id` (PK, FK), `outcome` (`'win'`/`'loss'`),
`home_goals`, `away_goals`, `settled_at`.

Ambas con el trigger `deny_mutation()` (bloquea UPDATE y DELETE), igual que
`picks`. Permisos de lectura para el rol de Grafana como el resto (`004`).

Liquidación: 1X2 y doble oportunidad por resultado final; goles por suma de
goles frente a la línea (sin push posible: líneas de medio gol). Se encadena
al cierre de partidos existente (`eval/clv.settle_pending`), igual que la
sombra sharp.

### Sellado

- `daily.run()` llama a `alta_prob.select_and_persist()` **antes** de
  `seal()`, en todas las ramas que sellan (con y sin picks de valor).
- `hashchain._collect()` añade el bloque `alta_probabilidad` (todas las filas
  de `alta_prob_picks` con `decided_at` en la fecha UTC del lote) a partir de
  `LOTE_ALTA_PROB_DESDE`, con el mismo patrón de fecha de corte que
  `LOTE_SIN_CONSENSO_DESDE`. La fecha es la del despliegue y se fija en ese
  mismo commit; desde entonces el bloque va siempre, vacío mientras
  `ALTA_PROB_ENABLED=0`. El recibo añade `n_alta_prob`. Los lotes
  anteriores no cambian; `verify` recalcula desde el JSON guardado.
- **Regla dura:** la API solo muestra pronósticos cuya fecha de lote existe en
  `prediction_batches`. Si un día el sellado se omite (sin predicciones del
  modelo), esos pronósticos no se muestran nunca y salta una alerta de
  Telegram. Lo no sellado no se publica.

## 3. API y web

### `GET /alta-probabilidad` (público)

En el router público existente, con el mismo límite de peticiones y
`Cache-Control` que el resto. Respuesta:

```json
{
  "estado": "activa" | "pausada" | "desactivada",
  "motivos": ["..."],
  "proximos": [{
    "match_id": "...", "league_id": "...", "kickoff_utc": "...",
    "local": "...", "visitante": "...",
    "market": "doble", "selection": "1X", "line": null,
    "texto": "Cruzeiro o empate",
    "prob": 0.87, "fair_price": 1.15,
    "ref_price": null, "ref_book": null,
    "batch_date": "2026-10-06", "chain_sha256": "..."
  }],
  "historial": {
    "n": 0, "aciertos": 0,
    "acierto_prometido": null, "acierto_real": null, "diferencia_ic95": null,
    "por_mercado": {}, "por_mes": [],
    "rendimiento_ref": {"n": 0, "roi": null}
  }
}
```

- `proximos`: solo sellados y con kickoff futuro.
- `acierto_prometido` = media de `prob` de los liquidados;
  `acierto_real` = aciertos / n; `diferencia_ic95` = IC95 de
  `(acertado − prob)` con remuestreo por semanas (`_weekly_ci`).
- `rendimiento_ref`: solo pronósticos con `ref_price`, ROI a esa cuota.
  Secundario, con texto que explica que acierto alto ≠ ganar dinero.
- `texto`: frase en español generada en el servidor ("Gana Cruzeiro",
  "Cruzeiro o empate", "Más de 1,5 goles", …).

### Web

- Nueva ruta "Alta probabilidad" en el menú (grupo EXPLORAR) y en la
  navegación móvil.
- Bloque de historial arriba: "Prometido X % · real Y % en N pronósticos",
  desglose por mercado.
- Una tarjeta por pronóstico: `texto` grande, probabilidad con
  `probabilityLabel` ("87 % · sale 9 de cada 10"), hora, cuota justa, cuota de
  referencia y casa si existen, enlace al lote sellado.
- Nota fija: línea de acierto, no de valor; con estas cuotas la casa suele
  dejar poco o nada a largo plazo.
- Si `estado` ≠ `activa`, se muestra el motivo y no hay tarjetas nuevas.
- Datos solo de `/alta-probabilidad` (público). Nada de tokens en JS. Todo
  texto del servidor pasa por `esc()`. Responsive, sin scroll horizontal a
  375 px. Hashes de caché `?v=` actualizados.

## 4. Control de calidad

### 4.1 Prueba histórica de los goles (antes del arranque)

`src/qf/eval/alta_prob_calibracion.py`, sobre los CSV de football-data
(`soft_vs_sharp.load_csvs`, caché `.local/fd_cache`), con el 1X2 (`PSH/PSD/PSA`)
y el 2,5 (`P>2.5`/`P<2.5`) de Pinnacle pre-cierre:

1. Reproduce la sección 1 (mismo ajuste, misma regla de elección) partido a
   partido.
2. Por mercado y por tramo de probabilidad (80-85, 85-90, 90-95 %): n,
   prometido, real, error estándar.
3. Imprime la firma sha256 del dataset.

Criterio, fijado antes de ver los resultados: un mercado de goles se habilita
si (a) en cada tramo con n ≥ 100, `real ≥ prometido − 2·SE`, y (b) en
conjunto `real − prometido ≥ −1` punto. Se pasa la misma prueba al 1X2 y a la
doble oportunidad para dejar constancia. Los mercados de goles habilitados se
fijan en código (`MERCADOS_GOLES_HABILITADOS`), no en configuración: cambiar
la lista exige repetir la prueba. Resultado y firma en `harness/progreso.md`.

### 4.2 Pausa automática en vivo

Antes de elegir los pronósticos del día, `alta_prob.control()` evalúa lo ya
liquidado:

- Con n ≥ 50 liquidados (global, y por mercado con n ≥ 50 en ese mercado): si
  el límite **superior** del IC95 de `(acertado − prob)` es < 0, se bloquea
  (todo o ese mercado). Alerta por `telegram.alert()`.
- Si el IC no se puede calcular (menos de 8 semanas con liquidados,
  `MIN_WEEKS` de `_weekly_ci`), no se bloquea: se informa "muestra
  insuficiente" en `motivos`.
- Mientras se cumpla la condición no se elige nada nuevo de lo bloqueado. Como
  una pausa no genera muestra nueva, la reanudación es decisión explícita del
  usuario: `ALTA_PROB_CONTROL_DESDE` (fecha) reinicia la ventana que evalúa
  el control. No se borra ni se oculta el historial anterior.
- Interruptor general `ALTA_PROB_ENABLED` (defecto 0 hasta el despliegue; se
  activa en el `.env` del servidor al arrancar).
- `/alta-probabilidad` expone `estado` y `motivos`; `/control` muestra el
  mismo estado.

### 4.3 Errores

- Snapshot viejo, sin Pinnacle o con selecciones incompletas → ese partido no
  tiene pronóstico (se cuenta en el log del job, sin alerta).
- Fallo del módulo entero → alerta de Telegram, y el job diario sigue
  sellando las predicciones (la línea nueva no puede romper lo existente).
- Lote no sellado → los pronósticos no se muestran y hay alerta (sección 2).

## 5. Pruebas

- Regla de elección: menor dentro de [0,80; 0,95]; nada si ninguno entra;
  tope superior; desempate.
- Doble oportunidad = suma exacta del 1X2 devigado.
- Ajuste de goles: reproduce las entradas con error < 0,01; sin línea de
  medio gol o con ajuste fallido no hay candidatos de goles.
- Guardas: precio de más de 6 h, menos de 15 min al inicio, partido ya con
  pronóstico.
- Inmutabilidad de las dos tablas.
- `_collect` incluye `alta_probabilidad` solo desde `LOTE_ALTA_PROB_DESDE`; un
  lote anterior sellado y verificado sigue verificando.
- API: no devuelve pronósticos sin lote sellado; calcula prometido/real/IC;
  `estado` refleja el interruptor y el control.
- Control: bloquea con el IC entero bajo cero, no bloquea con n < 50, bloquea
  solo el mercado afectado.
- Frontend: render y escape de la tarjeta, estado pausado, tests de
  `public-data.test.mjs` para la nueva fuente.
- `./scripts/harness_check.sh` y la suite completa en verde.

## 6. Puesta en marcha

1. **Sincronizar el servidor con HEAD (paso previo, aparte).** El repo del
   servidor y los contenedores van por detrás de HEAD (`promotion.py`,
   `clv.py`, `dixon_coles.py`, `api_football.py`…). Esta línea toca
   `daily.py` y `hashchain.py` (worker), así que no se despliega copiando
   archivos sueltos. Se muestra al usuario la lista exacta de cambios que
   llegarían a producción y, con su visto bueno, se sincroniza, se reconstruye
   y se verifica (salud, job diario, `/control`, web).
2. Correr la prueba 4.1 y fijar `MERCADOS_GOLES_HABILITADOS`.
3. Fijar `LOTE_ALTA_PROB_DESDE` a la fecha del despliegue, aplicar `db/040`,
   desplegar con `ALTA_PROB_ENABLED=0` y comprobar que el job diario sella
   (con el bloque vacío) y que `hashchain verify` cuadra.
4. Activar `ALTA_PROB_ENABLED=1`; verificar el primer lote con pronósticos
   (`hashchain verify`), la API y la web.
5. Actualizar `README.md` (sección de la línea y su naturaleza: acierto, no
   valor), `harness/tareas.md` y `harness/progreso.md`.
