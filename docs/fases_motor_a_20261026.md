# Fases del Motor A: qué señales pasan con el modelo `2026.10.26-020600` (26-oct-2026)

Pedido del titular: mejorar las fases del Motor A. Todo se midió **en local**, sobre la copia de producción
(`scripts/entrenamiento_local/`), con el mismo walk-forward del modelo nuevo (4.264 predicciones fuera de muestra, 13 ligas,
un año) y la misma puerta de siempre (`qf.model.ajuste`): mejora RPS y log-loss, no empeora la calibración, mejora en varias
ligas y es significativa en un remuestreo pareado. **Ninguna de estas mediciones cambia producción.**

El modelo está a 0,0096 de RPS del mercado (0,20370 frente a 0,19409 sobre 2.045 partidos con cuota). Todo lo de abajo se
mide contra esa distancia.

## 1. Señales de contexto (`qf.model.contexto`, validación en el 30 % final, 1.280 partidos)

| Bloque | ΔRPS | p95 | Ligas que mejoran | ¿Pasa? |
|---|---:|---:|---:|---|
| Altitud (sede y salto) | −0,00049 | −0,00014 | 11/13 | **Sí** |
| Altitud, solo el salto | −0,00029 | −0,00001 | 10/13 | Sí, por poco |
| Impacto del once (total) | −0,00051 | −0,00014 | 9/13 | **Sí** |
| Impacto del once (por líneas) | −0,00056 | −0,00013 | 10/13 | **Sí** |
| Clima (ERA5, observado) | −0,00021 | +0,00001 | 10/13 | No |
| Bajas (FotMob) | −0,00011 | +0,00005 | 10/13 | No |
| Descanso y carga | +0,00017 | +0,00040 | 4/13 | No (empeora) |
| Valor del once | +0,00015 | +0,00023 | 2/13 | No (empeora) |
| Valor del once habitual | +0,00022 | +0,00071 | 6/13 | No (empeora) |
| **Altitud + impacto del once (por líneas)** | **−0,00105** | **−0,00051** | **12/13** | **Sí** |

Respecto a la medición del 19-oct (`docs/contexto_en_el_motor_20261019.md`): altitud sigue pasando (ahora mejor) y el
**impacto del once** pasa también con estos datos. Clima y bajas se acercan sin llegar.

### Solidez: la misma puerta con cuatro particiones (20/30/40/50 % final)

| Bloque | 20 % | 30 % | 40 % | 50 % |
|---|---|---|---|---|
| Altitud | no | **sí** | **sí** | **sí** |
| Altitud, solo salto | no | sí | sí | no |
| Impacto del once (total) | **sí** | **sí** | no | no |
| Impacto del once (por líneas) | **sí** | **sí** | no | no |
| Clima | no | no | no | no |
| Bajas | no | no | no | no |
| Altitud + impacto del once (total) | **sí** | **sí** | **sí** | **sí** |
| Altitud + impacto del once (por líneas) | **sí** (−0,00079) | **sí** (−0,00105) | **sí** (−0,00071) | **sí** (−0,00067) |

La **combinación** altitud + impacto del once es la única estable en las cuatro particiones, con ΔRPS entre −0,0007 y −0,0010,
significativa en todas y favorable en 10 a 12 de 13 ligas. Por separado, el once pierde fuerza con las particiones más largas.
Eso solo dice que lo ganado es pequeño: una décima parte de la brecha con el mercado.

### Hacia adelante (partidos reales ya jugados, en sombra)

| Señal | Partidos con efecto | ΔRPS | p95 |
|---|---:|---:|---:|
| Altitud, predicciones diarias | 32 | +0,0010 | +0,0057 |
| Altitud, sellos finales | 12 | +0,0048 | +0,0131 |
| Impacto del once (medición del 25-oct) | 21 | +0,0012 | +0,0045 |

Con tan pocos partidos el intervalo es de ±0,005: no confirma ni descarta una mejora de 0,001. Siguen en **sombra**; la regla
de los 150 partidos con efecto no se ha cumplido (hoy 32 y 21).

## 2. Más ligas en el Motor A (`train.py --incluir`, 16 ligas, 63.877 partidos)

| Liga | Partidos OOS | Con cuota | RPS modelo | RPS mercado | Diferencia |
|---|---:|---:|---:|---:|---:|
| Championship | 556 | 274 | 0,22289 | 0,21772 | +0,0052 |
| 2. Bundesliga | 300 | 84 | 0,21620 | 0,21345 | +0,0028 |
| Süper Lig | 300 | 128 | 0,20872 | 0,19003 | **+0,0187** |

Las 13 ligas de siempre apenas cambian al añadirlas (RPS 0,20633 con ellas frente a 0,20627 sin ellas). Championship y
2. Bundesliga quedan a la distancia habitual del mercado; la Süper Lig, no. **No se activan**: el Motor A no vence al mercado
en ninguna liga, y añadir una solo da predicciones propias, no más precisión.

## 3. Sesgos del modelo y su corrección

Sobre las 4.264 predicciones: empates 25,1 % previstos frente a 26,2 % reales (el sesgo es del mismo signo en los cinco tramos
de probabilidad de empate; las copas lo sobreestiman y la Premier y la Eredivisie lo subestiman en 4 a 6 puntos) y goles totales
2,73 previstos frente a 2,82 reales (−3 %). Pruebas en el 30 % final, ajustando en el 70 % antiguo:

| Corrección | ΔRPS | p95 |
|---|---:|---:|
| Inflación diagonal (Karlis y Ntzoufras), d = 0,013 | −0,00007 | +0,00006 |
| Nivel de goles común (×1,014) | +0,00003 | +0,00007 |
| Las dos | −0,00008 | +0,00003 |

Ninguna es significativa y la ganancia es de 0,00007: **no se aplica**. Estos sesgos existen pero casi no cuestan RPS.

## Conclusión

- Con este modelo, los datos nuevos de cada fase suman como máximo ~0,001 de RPS de los 0,0096 que lo separan del mercado. Cerrar
  esa brecha con señales de contexto no es realista: el mercado ya las descuenta.
- Lo único robusto es **altitud + impacto del once** (−0,0007 a −0,0010). Falta confirmarlo hacia adelante; la altitud en
  sombra no lo muestra todavía.
- El impacto del once solo existe a T-60 (once confirmado), es decir, solo en el sello tardío (F7).
- Descanso, clima, bajas, valor del once, más ligas y las dos correcciones de sesgo no pasan o no valen la pena.

## Lo que no se subió y por qué

Los artefactos de sombra regenerados (`ajuste_altitud` y `ajuste_xi` con el OOS nuevo) no se subieron: el del once que corre
hoy (`ajuste_xi_ampliado-2024-01-01_2026-10-19.pkl`) está ajustado con 11.920 filas frente a las 4.264 de un año de OOS, y reemplazarlo
sería un paso atrás; el de altitud es equivalente al vigente (β del local 0,0279 frente a 0,0273 y del visitante −0,0181
frente a −0,0159).
