# Tenis v2, S3-B: exportación punto en el tiempo (5-nov-2026)

Código: `apps/tenis/src/tenis/datos/` (`reglas.py`, `lectura.py`, `visibilidad.py`, `fusion.py`, `exportar_pit.py`, `equivalencia.py`) y `apps/tenis/ops/exportar_pit_cli.py`. Pruebas: `apps/tenis/tests/test_datos_reglas.py`, `test_datos_pit_db.py` (mundo sintético de casos absurdos), `test_datos_pit_real.py` (TML 2024 + SofaScore ene-feb 2024 reales). Plan: §A.4, §B.2, §C.4–C.6, §D.3, §D.6, §F.

Uso: `python apps/tenis/ops/exportar_pit_cli.py --esquema tenis_dev --desde 2005-01-01 [--verificar 300 --hilos 8]`. Solo lectura (transacción `READ ONLY`); nunca escribe en la base. Salida por omisión: `data/tennis/rediseno_20261104/export_pit/`.

## Qué produce

| Fichero | Contenido |
|---|---|
| `partidos.parquet` | Una fila por partido del mundo real (TML y SofaScore fusionados). Entradas «as of» del corte; etiquetas con prefijo `y_` y `visible_resultado_utc` (lista `columnas_etiqueta` del manifiesto) |
| `eventos_resultado.parquet` | Resultados como eventos ordenados por `visible_resultado_utc` (columna `orden`), con minutos por lado, `minutos_origen`, `minutos_estimados` y `actualiza_rating` (solo completados) |
| `ranking_asof.parquet` | Ranking y puntos de cada lado con la regla de `ranking_a_las(corte, fecha_partido)` |
| `estadisticas_saque.parquet` | Puntos de saque y ganados por lado, solo completados, con `visible_desde` |
| `visibilidad_filas.parquet` | Auditoría: instante de visibilidad de cada fila fuente (partido, programa, resultado, estadística); es lo que se compara con la puerta |
| `calidad.json`, `manifiesto.json` | Recuentos, fusión, exclusiones, marcas; versiones, sha256 de contenido (flujo IPC de Arrow sin metadatos) y de fichero, reglas, excepciones y advertencias |

## Reglas (también en el manifiesto)

- **Visibilidad.** Un dato es visible en el corte c si y solo si c > vis. En vivo: vis = `recibido_en` − 1 µs; retro con `visible_desde`: ese instante; retro sin él: `lunes_semana` de la edición VIGENTE en c + 7 días. Es la lógica de `visible_a_las` / `retro_visible` / `lunes_por_partido_a_las` de `db/0004`, reimplementada por conjunto. Si la edición vigente cambiara con c de forma que la visibilidad no fuera un único intervalo, la fila se marca `no_monotona` y se excluye (0 casos). Las versiones múltiples de un resultado o estadística se cuentan y excluyen (0 casos).
- **Corte.** Con hora real de SofaScore: inicio − 60 min (`fuente_tiempo = sofascore`). Sin ella: `visible_desde` de la pareja de TML + 1 s (`tml_calendario` en el plan; aquí `fuente_tiempo = tml`). Para todo partido fusionado manda SofaScore: el calendario de TML no se usa.
- **`visible_resultado_utc`**: el de la fila de resultado de la fuente del tiempo. Si fuese < corte, el partido se excluye (`resultado_visible_en_su_corte`: 10 casos, los partidos por el bronce olímpico, ronda `BR` fuera de la tabla de TML: pareja y resultado comparten la regla por semana).
- **Fusión TML–SofaScore** (`fusion.py`): (1) estricta por (jugador_1, jugador_2, ronda, inicio de SofaScore en [L, fecha_fin + 1 d)); (2) por edición enlazada (biyectiva en las estrictas) sin ventana, para las ediciones de TML fechadas en la semana del clasificatorio; (3) pareja única en ediciones enlazadas sin mirar la ronda (no RR), porque SofaScore etiqueta algunas previas como «Round of 16/32». «QL» ↔ ronda Q más alta de la edición de TML. Una fila solo se fusiona con un candidato único recíproco; los ambiguos se cuentan.
- **Orden de los lados: NO por id (desviación deliberada de la petición).** El id de un jugador sale del orden de carga: TML carga la gira principal de todos los años antes que WTA, challengers y previas, y en cada fila crea antes al ganador. Medido en `tenis_dev`: el id menor gana el **55,07 %** de 258.892 partidos con ganador; cuando ninguno tenía historia gana el 73,9 % (505); con diferencia de ids ≥ 1.000, el 66,1 %. Eso revela el resultado (y el éxito futuro), así que la exportación ordena los lados con un bit del sha256 de `partido_key` (determinista, independiente del resultado): lado 1 gana el **49,99 %**. Todas las columnas por lado, `y_ganador`, `y_retira`, `y_sets` y los `lado` de ranking y estadísticas siguen ese orden. Advertencia en el manifiesto: `jugador_id` es clave, nunca rasgo numérico.
- **Atributos «as of»**: `mejor_de`, entradas, superficie e indoor solo de filas fuente cuyas filas de partido y edición son visibles en el corte (SofaScore antes que TML). Identidad (sin `visible_desde`): circuito, torneo, temporada, categoría, ronda (la de TML si está fusionado) y huso de la sede.
- **Superficie** (§B.2): Clay, Grass, Hard, Indoor. Tierra bajo techo = Clay con `indoor=True`; moqueta = Indoor salvo `indoor=False` (sin categoría); indoor desconocido = la categoría de su superficie con `indoor` NULL y marca `indoor_desconocido`.
- **Formato del set decisivo** (`reglas.formato_decisivo`, regla escrita): AO ventaja hasta 2018 y tiebreak a 10 desde 2019; RG ventaja hasta 2021; Wimbledon ventaja hasta 2018, 2019-2021 tiebreak a 7 en 12-12 → `desconocido` (fuera del catálogo y del simulador); US Open tiebreak a 7 hasta 2021; todos los GS tiebreak a 10 desde 2022 (también previas); previas de GS antes de 2022 → `desconocido`; gira y Challenger desde 1990 → tiebreak a 7; Finales tiebreak a 7 salvo NextGen; Laver Cup supertiebreak a 10; resto de equipos y JJOO → `desconocido`. Categoría vacía (TML la deja vacía cuando el nivel del torneo cambió entre años: Indian Wells WTA, Cincinnati, Basilea…): se decide por el nombre (GS, JJOO, equipos, NextGen) y si no, tiebreak a 7.
- **Ranking** (§C.4): por fecha de publicación, la mejor fila visible (prioridad, `recibido_en` desc, id desc); la publicación más reciente con `fecha_publicacion <= fecha_partido`. `fecha_partido`: con hora real, fecha local de la sede (sin sede cargada, UTC; hoy no hay sedes); sin hora, el inicio L de la edición de TML (nunca después del partido real, para no usar un ranking publicado durante el torneo, que ya incluiría sus puntos). Sin ranking → NULL y marca.
- **Edad**: (fecha_partido − fecha de nacimiento vigente) / 365,25; las fechas de nacimiento solo vienen de SofaScore (TML no persiste edades) → NULL si falta.
- **n_prev** (§D.6): eventos completados o retiradas del jugador con `visible_resultado_utc` < corte, con toda la historia de la base; < 20 → marca `historia_corta_k` (no se descarta).
- **Minutos**: la duración del partido para los dos lados; faltante = NULL, nunca 0; no hay regresión documentada, así que no se estima nada (`minutos_estimados` NULL). Walkover: sin minutos.
- **Estadísticas de saque**: solo completados; la fila de la fuente del tiempo o, si falta, la de la otra fuente fusionada, visible desde max(su instante, `visible_resultado_utc`); `puntos_saque = 0` se descartaría (0 casos: ya llegan como NULL).
- **Semana previa a GS** (§F.1): inicio de la edición entre 3 y 9 días antes del inicio del cuadro principal de un GS del mismo circuito. **Excepción declarada a la regla 1**: la fecha del GS es calendario publicado con meses de antelación, pero su edición retro es visible en la base después del corte.
- Campos prohibidos de SofaScore (ranking «de hoy», `firstToServe`, `h2h`, `team_streaks`): no existen en la evidencia y la lectura solo pide columnas nombradas.

## Exportación real sobre `tenis_dev` desde 2005

Fuente: `tenis_dev` (TML del 2-nov + SofaScore, identidad unida; 514.704 filas de partido). Fecha de corte de los datos (máximo `recibido_en`): 2026-11-05T03:07Z. Exportación en 163 s.

| | |
|---|---:|
| Partidos del mundo real desde 2005 (fecha_partido ≥ 2005-01-01) | **260.165** (238.940 anteriores fuera de rango) |
| ATP con hora TML / SofaScore | 187.694 / 10.015 (ATP incluye challengers y previas de TML) |
| WTA con hora TML / SofaScore | 52.806 / 9.650 |
| Fusionados TML–SofaScore | **15.599 de 19.665 filas de SofaScore (79,3 %)**: 13.087 estrictos, 2.488 por edición enlazada (219 ediciones), 24 por pareja única |
| Ambiguos sin fusionar | 25 (estricta); 0 en los otros pasos; 2 ediciones de TML sin enlace por conflicto |
| Conflictos en fusionados | 1 de ganador, 1 de estado (se usa SofaScore) |
| Posibles duplicados sin fusionar | 205 |
| Excluidos (`excluir_motivo`) | 10 (`resultado_visible_en_su_corte`, bronce olímpico) |
| Marcas | indoor desconocido 144.684; formato desconocido 19.614; superficie desconocida 685; moqueta indoor supuesto 2.807; historia corta 29.752 / 29.823 (lado 1 / 2); sin ranking 3.167 / 3.152 |
| Formato decisivo | tiebreak_7 219.447; ventaja 11.068; tiebreak_10 9.967; supertiebreak_10 69; desconocido 19.614 |
| Superficie | Hard 123.345; Clay 98.336; Grass 18.967; Indoor 18.832; NULL 685 |
| Eventos / estadísticas de saque / ranking as-of | 260.165 / 421.864 filas / 520.330 lados (6.319 NULL) |
| Orden de lados | id menor gana 55,07 % → lado 1 gana 49,99 % |
| Multiversión, no monótonos, ceros imposibles | 0, 0, 0 |
| Ranking por el camino lento (varias filas visibles en la semana) | 145 consultas |

**sha256 de la exportación** (sha256 de los sha256 de contenido): `fd4be4661a4c869a3920654b4e7514722159f3224f0e6efa4c8c3bd0c4e3a881`. Segunda exportación independiente (`export_pit_determinismo/`): mismo `sha256_export` y mismos sha256 de fichero en los cinco Parquet.

**Equivalencia con la puerta oficial en `tenis_dev`** (`equivalencia_puerta.json`): 300 partidos al azar (semilla 20261105), conjuntos completos en cada corte: 110,2 M filas de partido, 110,2 M de resultado, 83,7 M de estadística y 38,0 M eventos comparados. **0 discrepancias** en partido, programa, resultado, estadística, ranking, eventos y estadísticas de saque; **0 fugas** (evento propio, resultado propio en la puerta, evento posterior al corte). 39 min con 8 conexiones.

## Pruebas

- `test_datos_reglas.py` (sin base): superficie en 4 categorías, formato del set decisivo por torneo y año, unión de intervalos de visibilidad, fusión (par repetido en semanas consecutivas, ambigüedad, edición desalineada con QL).
- `test_datos_pit_db.py` (esquema aislado, mundo sintético construido con las reglas de los cargadores): partido cuya edición no se ve a tiempo, walkover, duración 0 (la base la rechaza; faltante = NULL), jugador sin ranking, GS de dos semanas con la mitad de los datos en TML, par repetido en dos torneos consecutivos, edición desalineada, edición de SofaScore no visible en el corte, fecha local de Melbourne, ranking oficial en vivo frente a TML, orden de lados y etiquetas, fuga, equivalencia con la puerta en TODOS los partidos y determinismo.
- `test_datos_pit_real.py` (esquema aislado con TML 2024 ATP+WTA y 1.100 eventos de SofaScore de ene-feb 2024, cargadores reales y resolutor multifuente; 6.026 partidos, 513 fusionados): equivalencia con la puerta en 300 partidos al azar (semilla 20261105, 0 discrepancias), fuga (resultado propio nunca visible; con hora real fin estimado > inicio − 60 min; ranking con `visible_desde < corte` y `fecha_publicacion <= fecha_partido`; estadísticas tras el evento), orden de lados (lado 1 gana ≈ 50 %) y determinismo.
- Mismas comprobaciones sobre `tenis_dev` con `exportar_pit_cli.py --verificar 300` (arriba).

## Limitaciones y lo que no se cumplió

- **Orden de lados distinto del pedido** (ver arriba): era la única forma de cumplir la regla 2.
- **Duplicados no fusionados**: 205 filas de SofaScore sin fusionar tienen una fila de TML de la misma pareja en la ventana ampliada ± 7 días; el filtro de rating las vería dos veces. Las 4.066 filas de SofaScore sin fusionar son sobre todo previas WTA (TML no tiene previas WTA) y jugadores de SofaScore no unidos con TML (15 % en S2b).
- **Indoor desconocido en el 55,6 %** de los partidos (TML no trae `indoor` en la mayoría): queda como nivel propio, no se imputa (imputarlo desde otros años del torneo sería otra regla, sin hacer).
- **Formato desconocido en el 7,5 %** (equipos, JJOO, previas de GS antes de 2022, Wimbledon 2019-21): se marca, no se descarta aquí; el modelo debe dejarlos fuera (§F.3).
- **Sin sedes**: la fecha local usa UTC. **Sin edades de TML**. **Ranking de TML** = última observación del jugador (función escalón), con el lunes de TML sin verificar (§C.4).
- **Calendario de TML** (S2b): fuga residual 0,97 % medida en 2023-2026 y no verificable hacia atrás; el corte retro cae tras el inicio real en ~55 % de los partidos (efecto de segundo orden en ratings). En los partidos fusionados la puerta oficial sí deja ver el resultado de TML antes que el de SofaScore en algunos casos; la exportación no (usa SofaScore), y la prueba de equivalencia lo cuenta aparte.
- La prueba de equivalencia sobre `tenis_dev` compara conjuntos completos (≈ 0,5 M filas por tabla y corte) en 300 cortes; la de pytest lo hace sobre el esquema de datos reales reducido.
