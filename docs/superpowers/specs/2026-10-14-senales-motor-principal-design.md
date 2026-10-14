# Señales nuevas en el motor principal — diseño

Fecha: 2026-10-14. Aprobado por el usuario en el chat, en este orden:

1. Puerta: una señal entra al motor principal **solo si gana** fuera de muestra.
2. El XI confirmado entra al motor principal (no solo en sombra).
3. Mecanismo: **capa de ajuste de lambdas** sobre Dixon-Coles.
4. Garantía anti-fraude relajada a **sellar tarde**: un sello por partido justo
   antes del inicio, con toda la información disponible a esa hora.

Punto de partida verificado (auditoría `docs/auditoria_datos_modelo_20261014.md`
y consulta al VPS el mismo día): modelo activo `2026.09.27-010508`, Dixon-Coles +
calibración, `META_BLEND_ENABLED=0`, `RESIDUAL_ENABLED=0`; supera a Elo y no al
mercado; `ready_for_commercial_picks=false` por CLV sin muestra.

## Objetivo

Que XI y valor de jugadores, bajas, tiros/PSxG/xG, árbitro, sede y clima, y el
movimiento de cuotas pasen de estar archivados a mover la probabilidad que
selecciona picks. Cada bloque de señales entra solo si mejora al motor sin él.

Éxito por bloque: mejora RPS, log-loss y ECE fuera de muestra, sobre las mismas
filas, en ≥2 ligas, frente al motor sin ese bloque. Éxito global: el sello tardío
en producción, sin romper la verificación de ningún lote ya sellado.

## 1. Flujo

```
08:00 UTC  lote DIARIO
  predicciones base (Dixon-Coles + bloques disponibles a esa hora) para la web
  y los productos de varios partidos (parley, escalera, alta probabilidad).
  SIN picks de valor.

cada 5 min  lote de PARTIDO, cuando el partido entra en ventana:
  disparo = XI de ambos lados capturado, o T-30, lo que llegue primero
  → predicción FINAL (núcleo + capa de ajuste con todos los bloques)
  → picks de valor con las cuotas de ese momento
  → sellar → publicar
```

- `predictions` gana una columna `etapa` (`diaria` | `final`). Los picks de
  valor solo cuelgan de predicciones `final`.
- `prediction_batches` gana `batch_kind` (`diario` | `partido`) y deja de ser
  uno por día. `_collect()` filtra por tipo y, para lotes de partido, por los
  partidos de ese lote. Los lotes anteriores al corte (`LOTE_POR_PARTIDO_DESDE`,
  mismo patrón que `LOTE_PARLEY_DESDE`) se regeneran con su formato original:
  `verify` tiene que seguir dando el mismo hash para todo lo ya sellado.
- No cambia: predecir → seleccionar → sellar → publicar dentro de cada lote,
  triggers de inmutabilidad, y nada se modifica después del inicio.
- Sin XI a T-30: se sella igual; el bloque `xi` no aporta y se anota en
  `data_completeness`.
- Consecuencia comercial aceptada: los picks de valor salen 30-60 min antes de
  cada partido, no a las 08:00.
- A verificar en el plan de F7: qué productos diarios leen `prediction_id` de
  la corrida de las 08:00 (parley, escalera, alta probabilidad) para que sigan
  leyendo predicciones `diaria`.

## 2. Capa de ajuste

Módulo nuevo `src/qf/model/ajuste.py`; generaliza `lineup_challenger.py`
(ajuste Poisson con offset, encogimiento, recorte).

```
λ = λ_base · exp(clip(shrink · Σ_b x_b·β_b^home, -1, 1))
μ = μ_base · exp(clip(shrink · Σ_b x_b·β_b^away, -1, 1))
```

- Núcleo intacto: Dixon-Coles, el término `strength` entre ligas
  (`tests/test_cross_league.py` a 1e-9) y la calibración. La calibración se
  aplica después del ajuste, a la probabilidad final.
- Contrato de un bloque: `construir(partidos, corte) -> DataFrame` con
  `match_id`, sus columnas y `feature_as_of`, que nunca es posterior al corte
  (hora del sello en vivo, `kickoff` del partido en el walk-forward).
- Dato ausente → mediana del ajuste (aporte 0). Nunca cero inventado.
- Un artefacto por versión del modelo, `ajuste_<version>.pkl`: bloques
  activos, β, medianas, escalas, encogimiento y el informe de validación de
  cada bloque. Un bloque que no ganó no está en el artefacto.
- `lineup_challenger.py` y `shadow.py` siguen funcionando hasta que F4 y F7
  los sustituyan.

## 3. Fases

| Fase | Contenido | Bloque |
|---|---|---|
| F0 | Integrar a tablas principales lo ya archivado: amarillas (8.118 parejas), árbitro, tiros, PSxG; huecos xG con fuente acreditada; tabla `estadios` con sede y coordenadas | — |
| F1 | Reentrenar con los xG recibidos después del 27-sep; `ajuste.py` con cero bloques y su walk-forward: línea base | — |
| F2 | Apertura y cierre de Pinnacle, CLV, movimiento de cuota antes del sello | `mercado` |
| F3 | Bajas y sanciones → minutos esperados perdidos ponderados por importancia del jugador; duda ≠ baja segura | `bajas` |
| F4 | Puente de identidades FotMob/API-Football; XI con valor de jugador | `xi` |
| F5 | Árbitro: penaltis, expulsiones y tarjetas por partido, con muestra efectiva | `arbitro` |
| F6 | Sede real, distancia, husos, altitud; clima con pronóstico emitido antes del sello (API: Open-Meteo, ver "F6: clima") | `sede_clima` |
| F7 | Sello tardío en producción | — |

Cada fase tiene su propio plan en `docs/superpowers/plans/`. F7 puede adelantarse
porque mejora los picks por sí sola (cuotas de último momento).

### F6: clima con Open-Meteo (elegida por el usuario el 2026-10-14)

Documentación leída el mismo día (open-meteo.com/en/terms, /pricing, /docs):

- **Licencia — bloqueante antes de producción.** El plan gratuito (600/min,
  5.000/h, 10.000/día, 300.000/mes) es solo **no comercial**, y sus términos
  cuentan como comercial los sitios con suscripciones y "integrar el servicio
  en productos comerciales". QuantFut vende suscripciones, así que hace falta un
  plan de pago. Los precios no están publicados (aparecen en el pago o por
  info@open-meteo.com).
- **Planes:** Standard (1 M llamadas/mes) y Professional (5 M). Según su tabla,
  las APIs históricas (Historical Forecast, Previous Runs) requieren
  **Professional**; la celda del plan gratuito es ilegible en la página, así que
  se confirma con ellos antes de contratar.
- **En vivo:** API de pronóstico con las coordenadas de la sede, una llamada por
  partido en el momento del sello (T-30). El volumen es trivial frente a
  cualquier plan.
- **Para entrenar y validar sin fuga:** *Historical Forecast API*
  (`historical-forecast-api.open-meteo.com/v1/forecast`, desde 2022) encadena las
  primeras horas de cada corrida del modelo, que es lo que habría visto el sello
  de T-30. *Previous Runs API* (`previous-runs-api.open-meteo.com/v1/forecast`,
  desde enero de 2024) da el pronóstico emitido 1 a 7 días antes
  (`temperature_2m_previous_day1`...). Nunca se entrena con el clima observado
  después del partido.
- **Coordenadas:** salen de `estadios` (F0). Para un partido futuro se usa el
  estadio más reciente del club local; las finales y los campos neutrales se
  marcan aparte.
- **Atribución:** los datos son CC-BY 4.0; hay que citar la fuente en la web.
- La tabla de pronósticos guarda `emitido_en` y `valido_para`: así la puerta de
  entrada puede comprobar que el clima usado en un sello existía antes de él.

## 4. Puerta de entrada

- Walk-forward sobre las mismas filas: motor con el bloque frente a motor sin él.
- Entra si mejora RPS, log-loss y ECE en ≥2 ligas. `check_leakage()` siempre.
- Bloque que pierde: queda en el repo, desactivado, con su informe.
- La puerta comercial de `promotion.py` (cierre y CLV) no cambia.

## 5. Pruebas

- Por bloque: ninguna feature con `feature_as_of` posterior al corte; ausentes
  no se convierten en cero.
- Invariante entre ligas a 1e-9 sin tocar.
- Regeneración idéntica de lotes diarios ya sellados.
- Prueba de punta a punta del lote de partido: disparo por XI y por T-30.
- `./scripts/harness_check.sh` al final de cada fase.
