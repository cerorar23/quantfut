# NBA — auditoría del motor de pronóstico, segunda pasada (23-oct-2026)

Alcance: lo que corre en el servidor (`multimarket_v13_live` + `multimarket_v13_live_producer`, desplegados el 21-oct
según `DEPLOYS.md` de `main`), el código local de la rama `nba/v13-disponibilidad`, los resultados de v1.4/v1.4b/v1.5
y el piloto de PropLine del 23-oct. No se gastó ningún crédito, no se tocó el servidor ni ningún pronóstico sellado.
Primera auditoría: `docs/nba_auditoria_motor_20261021.md` (no se repite aquí).

**Enfoque (aclaración del titular, 23-oct):** el motor busca probabilidades estadísticas bien calibradas y muchos
pronósticos en varios mercados; **no** busca ganarle a las cuotas. Por eso la medida de certeza es la calidad de la
probabilidad frente al resultado real (Brier, log loss, calibración, cobertura de los rangos), no la comparación con
Pinnacle, que queda solo como dato de referencia.

## Punto de partida (2024-25 / 2025-26, frente al resultado real)
| Mercado | Brier | Lectura |
| --- | --- | --- |
| Ganador | 0,204 / 0,201 (acierto 68-69 %, sesgo ≤0,012) | Bien calibrado; es el mercado más sólido. |
| Puntos de equipo | 0,232 / 0,222 | Señal moderada. |
| Total del partido | 0,241 / 0,231 (moneda = 0,250) | Casi sin señal; sesgo por temporada de −0,03 a +0,04 sin recalibrar. |
| Puntos de jugador | 0,243 | Sobreconfiado: pendiente de calibración 0,42; el rango 80 % cubre el 73 %. |

- **Lesiones, agotado para equipo:** v1.4, v1.4b y v1.5 no mueven ganador ni puntos de equipo; sí mejoran los seis
  mercados de jugador (v1.5: puntos −0,002 de Brier, participación 0,45-0,49 → 0,31-0,38 de log loss).
- Hoy se sellan **4 pronósticos por partido** (ganador, puntos de cada equipo, total) sobre un solo umbral por
  mercado (`floor(media de 10)+0,5`), solo temporada regular y solo partidos después de las 17:35 ET.

## Errores encontrados (código en vivo)

### 1. Alta — Los partidos de tarde no se pronostican nunca
El productor sella una vez al día a partir de las 17:35 ET y `upcoming()` descarta los partidos ya empezados. Medido con
las horas reales: **97, 87 y 91 partidos** de 2022-23, 2023-24 y 2024-25 empiezan antes de las 17:35 ET (7-8 %:
fines de semana, festivos, Navidad, MLK). No aparecen en ninguna cohorte.

### 2. Alta — Los partidos de 18:00-18:45 ET se sellan sin lesiones aunque haya reporte válido
Se descarga **un solo reporte por cohorte** (el último ≤ ahora, 17:30) y luego se exige, por partido, que su hora y
nuestra recepción sean ≤ salto − 60 min. Para un partido de las 18:00 o 18:30 el reporte de 17:30 (recibido 17:35-17:45)
no vale y el partido queda «sin_reporte_valido», aunque el de 16:30 sí valdría. **45-56 partidos por temporada** (~4 %).
En el histórico esos partidos sí tenían reporte (el de 13:30): desajuste entrenamiento/vivo.
**Arreglo:** elegir el reporte por partido (último publicado ≤ salto − 60) en lugar de uno por cohorte.

### 3. Media — La hora de sellado y la de recepción del reporte se anotan antes de tiempo
`run()` toma `now` al empezar, luego recoge resultados de todas las cohortes, descarga los box scores de la temporada y
el reporte, y escribe `sealed_at_utc = now` y `first_received_at_utc = now`. Con la versión desplegada (sin caché) eso
son ~1.200 páginas en abril: el sello puede figurar minutos antes de lo real. En un producto cuya garantía es el sello,
la hora debe tomarse al escribir el bundle, y la de recepción después de la descarga.

### 4. Media — El servidor corre `completed()` sin caché
La caché y el fallo explícito ante partidos no finales están en la rama local, no en el productor: cada día se vuelve a
bajar toda la temporada y un partido no final se salta en silencio. Riesgo de bloqueo de nba.com (y entonces no se sella
nada). Desplegarlo exige el modelo `nba_f6_live13_model_20261021b` (parámetros idénticos).

### 5. Media — Un bloqueo de nba.com se confunde con «no hay reporte»
`capture_report()` trata cualquier respuesta distinta de 200 como «no existe» y retrocede hasta 96 franjas. Si el
bucket responde 403 por bloqueo, todos los partidos se sellan «sin_reporte_valido» sin ninguna alarma. El backfill ya
resolvió esto con un archivo de control conocido; falta aplicarlo en vivo.

### 6. Media — El valor de los jugadores sigue congelado en 2025-26 (punto 7 de la primera auditoría, sin arreglar)
`history_index()` solo usa los box scores históricos; `completed()` guarda solo los puntos del equipo. En febrero los
valores tienen 4-8 meses, y quien no jugó en 2025-26 vale 0. En el ensayo, 12 de 74 jugadores listados (16 %) no
tenían historia: todos novatos (p. ej. AJ Dybantsa, «Out»). **Arreglo:** guardar también las filas de jugador del mismo
box score que ya se descarga (`homeTeam.players`) y añadirlas a la historia.

### 7. Media — Sin play-in ni playoffs
`CARD` solo acepta identificadores `002` (temporada regular). Desde mediados de abril (~85 partidos más la final de la
Copa NBA) no se pronostica nada, y Elo y forma no reciben esos partidos.

### 8. Baja — Tres pruebas caducadas
`tests/test_paper_bundle.py` (piloto RUN071): las pruebas usan `NOW = datetime.now()` y el bundle fija
`deadline_utc = 2026-10-22T12:00Z`, así que fallan desde el 22-oct. No es un fallo del motor; hay que fijar el reloj.

## Problemas de modelo
- **Ganador y puntos incoherentes** (punto 5 de la primera auditoría): el ganador sale del Elo y los puntos de medias
  de 20 partidos sin ajuste de rival; la página puede dar favorito a quien proyecta menos puntos, y no hay margen
  (hándicap) porque no existe una distribución única del marcador.
- **Arranque de temporada:** la forma de estos días son los últimos 20 partidos de 2025-26 (abril: descansos y tanking)
  y el Elo solo regresa un 25 %. Brier del ganador en oct-nov ~0,01 peor que el resto. El vivo está justo en esa fase.
- **Total y puntos de equipo sin recalibrar:** la anotación de la liga cambia entre temporadas y el sesgo llega a ±0,04.
  La recalibración móvil de v1.2 solo se aplicó al ganador.
- **Jugadores sobreconfiados**: los puntos llegan de 1, 2 y 3 en 3, y un Poisson por minuto subestima la varianza ~2,3×.
- **Tabla de participación entrenada con reportes de 13:30/17:30** y servida con reportes T-60 («Questionable» 0,48).

## Mejoras para tener más certeza (probabilidad frente al resultado real)
1. **Sellar cada partido cerca de T-60**, no una cohorte a las 17:35: más información de lesiones confirmadas en la
   probabilidad, y arregla de paso los errores 1 y 2. Exige enmendar el protocolo vivo.
2. **Un solo modelo del marcador:** posesiones × eficiencia con ataque/defensa ajustados por rival y ritmo (Kalman o
   ridge con decaimiento, como `src/qf/model/kalman.py` en fútbol). De una sola distribución salen ganador, margen,
   total y puntos de cada equipo, coherentes y a cualquier umbral.
3. **Recalibración móvil de total y puntos de equipo** (la misma idea que ya funcionó en el ganador en v1.2).
4. **Prior de pretemporada estadístico:** valor de la plantilla nueva por minutos esperados de cada jugador (traspasos y
   novatos incluidos), con más peso en los primeros 15-20 partidos; sacar de la forma los últimos ~10 días de abril.
5. **Jugadores:** puntos como 2P/3P/TL o binomial negativa con dispersión ajustada por estadística; minutos
   condicionados a las bajas del equipo; adoptar para jugadores lo que v1.4 (relativo) y v1.5 (T-60) ya probaron que
   mejora; rangos sacados de la distribución calibrada y con su cobertura publicada.
6. **Medir siempre la calibración por mercado** (pendiente, sesgo, curva por deciles, cobertura de rangos 80 %) además
   del Brier, y mostrarla en la página: es la prueba de certeza de un motor estadístico.

## Más pronósticos en más mercados (sin depender de casas)
Con una distribución completa por partido y por jugador, cada partido da muchos pronósticos sin pedir nada a nadie:
- **Equipo:** ganador; margen por rangos (p. ej. gana por 1-5, 6-10, >10) y a varios umbrales; total y puntos de cada
  equipo a varios umbrales (no uno solo); primera mitad y cuartos si se modela el reparto del marcador por periodo.
- **Jugadores:** puntos, rebotes, asistencias, triples, P+R+A, doble-doble, robos y tapones. El protocolo los dejó
  fuera porque «no hay lista verificada de quién juega»; estadísticamente se resuelve dando la **probabilidad de jugar**
  (tabla del reporte oficial, ya medida) y la distribución condicionada a jugar, y evaluando cada parte por separado.
  Rotación probable = jugadores con minutos recientes que no figuran «Out».
- Orden de magnitud: de 4 a **~80-100 pronósticos por partido** (≈10 jugadores × 8 estadísticas + 10-15 de equipo),
  unos **800-1.000 por noche**.
- PropLine (archivo común, ya capturado cada hora) sirve solo como referencia opcional: trae los umbrales que el público
  consulta y los identificadores oficiales NBA (`nba:1629614`), útiles para elegir qué umbrales mostrar y para
  emparejar jugadores sin nombres. No es un requisito del motor.

## Decisiones que dependen del titular
- Enmendar el protocolo vivo para sellar por partido y corregir los errores 1-6: cambia el hash del módulo, exige
  reajustar el modelo y redesplegar el productor.
- Incluir los mercados de jugador en vivo con probabilidad de jugar explícita (cambio de protocolo).
- La captura de precios `live_market` (`nba-live13-price`, The Odds API) **sí está desplegada** desde el 22-oct (cron
  cada 5 min, bloqueada en código hasta el 1-nov; entrada en `DEPLOYS.md` de `main`). Una primera versión de esta
  auditoría decía lo contrario por leer el `DEPLOYS.md` de una rama atrasada. Con este enfoque ya no es necesaria:
  decidir antes del 1-nov si se retira su línea de cron.

## Orden recomendado
1. Errores 1-6 en el productor, en un solo despliegue.
2. Recalibración móvil de total/puntos de equipo y prior de pretemporada (afectan ya a la cohorte de octubre).
3. Modelo único del marcador → margen, total y puntos a varios umbrales, con medias partes.
4. Jugadores con probabilidad de jugar y distribución corregida.
5. Play-in y playoffs antes de mediados de abril.
