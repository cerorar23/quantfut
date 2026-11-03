# Auditoría de datos de los tres motores de fútbol: PropLine, SofaScore, BetsAPI y reentrenamiento (25-oct-2026, 14–17 h UTC)

Pregunta del titular: ¿reciben los tres motores todos los datos de Apify (SofaScore) y PropLine, y de forma correcta?
¿Se capturan cierres y alineaciones? ¿Se sigue lo recomendado en los documentos de investigación? ¿Hay data suficiente
para reentrenar y qué ligas están completas? ¿Qué data disponible (incluida la descarga de BetsAPI) conviene acoplar?
Continúa `docs/auditoria_motores_20261025.md` (madrugada del mismo día). **Solo lectura**: SELECT a la base, registros
del worker y de los recolectores, y lectura del archivo de PropLine en un contenedor desechable sin red y con el volumen
en solo lectura. Worker `117feb7`, crontab igual a `main` (`99f219b`).

**Cambios en `main` durante la auditoría** (#121–#124, worker `e5a29a7`/`2db3f61`): Serie B, LaLiga 2, Allsvenskan y
Super League suiza se retiran (db/088, se aplica a las 22:30 UTC del 25-oct; quedan 15 ligas + 2 copas); FotMob vuelve
como complemento diario (solo rellena NULL a > 36 h) y como respaldo de resultados. Re-medido a las 15:44 UTC: siguen
0 cierres desde el 22-oct; SofaScore sigue sin ningún evento de MLS ni Liga MX; FotMob ya puso xG en 2 de 14 partidos
de MLS. Las cifras de las secciones 1 y 4 son de antes de esos cambios.

## Resumen

| # | Gravedad | Hallazgo |
|---|---|---|
| 1 | **crítica** | **Ningún cierre de cuotas entra a la base desde el 22-oct 18:50 UTC.** El recolector de PropLine SÍ guarda los cierres (`/odds/closing`): 185 partidos del 21 al 25-oct, 182 con 1X2 de Pinnacle limpio, mediana **11 min antes del inicio**, también córners y tarjetas. Nadie los carga a `odds_snapshots`. Sin ellos: CLV, sombra, puerta comercial y la comparación con el mercado del reentrenamiento siguen congelados |
| 2 | **alta** | **MLS y Liga MX no tienen ningún partido en el archivo de SofaScore** (0 eventos descubiertos). Desde el 22-oct: MLS 0/12 con xG, tarjetas, árbitro y tiros; Liga MX 0/10 desde SofaScore. Probable causa: id de torneo/temporada (Liga MX `11620`; MLS en eliminatorias). No verificado con petición. FotMob (complemento desde #121) tapa parte: xG en 2 de 14 de MLS a las 15:44 |
| 3 | alta | Bajas y once previsto se capturan bien (42 de 64 partidos de las próximas 72 h; oficiales en 33 partidos hoy, mediana 39 min antes del inicio) pero **ningún motor los lee** (`injuries`, `lineups_previstas` sin consumidores). El ajuste del once usa ids de API-Football; con ids de SofaScore no hay historia y queda en «insuficiente» |
| 4 | alta | Las estadísticas de SofaScore (faltas, centros, posesión, paradas…) quedan en `sofascore_detalles`; `matches.stats` no se llena desde el 22-oct. El Motor C pierde la serie que los documentos piden ampliar (faltas, centros) |
| 5 | alta | Históricamente casi **no hay cierres de totales, hándicap, córners ni tarjetas**: el cierre de Pinnacle de totales cubre el 0–6 % de los partidos desde jul-2023 (1X2: 92 %). Los mercados que más vende B/C se calibran sin su propio cierre |
| 6 | media | La sombra sharp ve `offers_seen: 0`: PropLine casi no trae las casas blandas de `SOFT_BOOKS` |
| 7 | media | Clima: ERA5 con 175 errores por pasada; el pronóstico en vivo dependía de los previos de FotMob (reactivados en #121, sin comprobar aquí) |
| 8 | media | Calendario de otras competiciones (descanso) venía de API-Football (`calendario_equipo`), retirado: el factor «descanso y calendario» que los documentos ponen primero queda sin fuente |

Lo que funciona: cuotas horarias de PropLine (154.502 filas y 203 partidos el 25-oct: Pinnacle 1X2, totales, hándicap,
ambos marcan, córners, tarjetas y totales por equipo, más 1xbet), resultados de PropLine (1 solo huérfano en ligas
activas), xG de SofaScore con hora de recepción propia (~14 h tras el inicio, punto en el tiempo correcto) y los tres
motores producen (25-oct: 60 predicciones del A, 28 de alta probabilidad, 133 de tarjetas/córners).

## 1. ¿Llegan los datos y llegan bien?

### 1.1 Partidos terminados desde el 22-oct (ligas activas)

| Liga | Fin | xG | Córners | Tarjetas | Árbitro | Detalle SofaScore |
|---|---|---|---|---|---|---|
| Argentina | 7 | 7 | 7 | 7 | 7 | 6 |
| Brasil | 8 | 8 | 8 | 8 | 8 | 8 |
| Bundesliga | 7 | 7 | 7 | 7 | 6 | 6 |
| 2. Bundesliga | 6 | 6 | 6 | 6 | 4 | 4 |
| LaLiga | 5 | 5 | 5 | 5 | 4 | 4 |
| LaLiga 2 | 3 | **0** | 3 | 3 | 3 | 3 |
| Europa League | 4 | 4 | 4 | 4 | 4 | 0 (aún API-Football) |
| Ligue 1 | 2 | 2 | 2 | 2 | 2 | 1 |
| Championship | 12 | 12 | 12 | 12 | 12 | 11 |
| Premier | 5 | 5 | 5 | 5 | 5 | 4 |
| Serie A | 5 | 5 | 5 | 5 | 5 | 4 |
| Liga MX | 10 | 6 | 7 | 6 | 5 | **0** |
| Eredivisie | 4 | 4 | 4 | 4 | 4 | 3 |
| Primeira | 4 | 4 | 4 | 4 | 4 | 3 |
| Allsvenskan | 6 | 4 | 6 | 6 | 6 | 4 |
| Süper Lig | 3 | 3 | 3 | 3 | 2 | 2 |
| **MLS** | 12 | **0** | 2 | **0** | **0** | **0** |
| **Total** | 105 | 84 | 92 | 89 | 83 | 65 |

Las cifras de Liga MX y Europa League con dato son del 22-oct (última pasada de API-Football). LaLiga 2: SofaScore no
publica xG. El detalle se captura una vez al día (07:40, tope 40): quedan 1–2 partidos pendientes por liga.

### 1.2 Cuotas y cierres

- Última fila `window_tag='close'`: The Odds API, **22-oct 18:50 UTC**. PropLine escribe solo `hourly:N` (correcto: no
  fabrica cierres).
- Con PropLine horario, solo el ~60 % de los partidos tiene una foto de Pinnacle en la última hora antes del inicio.
- Archivo de cierres de PropLine (`/odds/closing`, ya pagado dentro del límite diario): ver tabla.

| Competición PropLine | Partidos | Fechas | 1X2 Pinnacle limpio | Córners | Tarjetas |
|---|---|---|---|---|---|
| UCL / UEL / Conference | 9 / 18 / 18 | 21–22 oct | 9 / 18 / 18 | 9 / 18 / 18 | 9 / 18 / 4 |
| MLS | 14 | 21–25 oct | 14 | 12 | 12 |
| Liga MX | 10 | 22–25 oct | 10 | 10 | 0 |
| Championship | 10 | 23–24 oct | 10 | 10 | 10 |
| Big-5 (EPL, LaLiga, Serie A, Bundesliga, Ligue 1) | 20 | 21–24 oct | 20 | 20 | 20 |
| Brasil / Argentina | 7 / 7 | 23–25 oct | 7 / 7 | 7 / 7 | 7 / 0 |
| Resto (2. BL, Eredivisie, Primeira, Süper Lig, Suecia, Noruega, Serie B, LaLiga 2) | 25 | 23–24 oct | 23 | 23 | 1 |

`closing_at` de Pinnacle 1X2: p10 1,4 min, mediana 11,2 min, p90 16,4 min antes del inicio. Sirve como cierre justo
con la misma regla `es_cierre_real()`.

### 1.3 Alineaciones y bajas (SofaScore, desde el 25-oct)

- Previstas: 72 capturas; 42 de los 64 partidos de las próximas 72 h. Sin previsto: Brasil, Liga MX, MLS (2.º hallazgo).
- Oficiales: 33 partidos hoy, entre 24 y ~65 min antes (mediana 39). El sello tardío ya puede usar el once oficial.
- Bajas: 665 filas de 62 partidos (`source='sofascore'`), con tipo, motivo y fecha de regreso.
- Consumo: ningún módulo de `model/`, `publish/` o `eval/` lee `injuries` ni `lineups_previstas`. `ajuste_xi` está en
  sombra y su medición hacia adelante va en contra (RPS con once 0,21873 frente a 0,21754 sin él; no listo).

## 2. ¿Se sigue lo recomendado en los documentos de investigación?

Documentos: «Recomendaciones para mejorar los tres motores» y «Revisión del plan F1–F7» (15-oct), con sus fuentes:
Egidi, Pauli y Torelli (históricos + cuotas), Bilalić, Gula y Vaci (localía y público, Sci. Rep. 2021), estrés térmico
en el Mundial 2014, cambio de entrenador y regresión a la media; y la base del README: Dixon-Coles (1997) y de-vig de Shin.

| Recomendación | Estado medido |
|---|---|
| Conservar Dixon-Coles y meter factores en λ/μ, no filtros | Sí en diseño (`ajuste`, `contexto`); en producción solo entra la altitud |
| Validación cronológica, solo datos conocidos al publicar | Sí: walk-forward, `features_pit`, `xg_recorded_at` = recepción real (SofaScore ~14 h tras el partido) |
| Combinar A con mercado (Egidi y col.) sin doble conteo | `meta.py`; el peso óptimo medido del A fue 0 (24-oct). Coherente con la evidencia |
| Anclar B con 1X2 **y** totales | Hecho (`alta_prob.py`) |
| Alineación y reemplazos (F4) | Datos llegan desde hoy; el modelo no puede usarlos hasta tener historia con ids de SofaScore |
| Lesiones sin doble conteo (F3) | Datos llegan; sin consumidor |
| Descanso y calendario primero | Vista `v_descanso_equipo` existe; la fuente de copas y otras competiciones se retiró con API-Football |
| Clima y altitud sin efecto supuesto (estudio 2014) | Altitud sí; ERA5 con errores; sin pronóstico en vivo |
| Localía por liga, no bono general (Bilalić) | Sí: ventaja local por liga en Dixon-Coles |
| Entrenador sin bono automático | Sin fuente; correcto no inventarlo |
| Motor C con faltas, centros, rival, árbitro | Árbitro sí; faltas y centros se reciben (SofaScore, BetsAPI) pero no se guardan donde C los lee |
| F7: revisar al confirmarse el once sin reescribir lo vendido | Activo desde el 20-oct; ahora con once oficial de SofaScore |
| F9: evaluar a volumen constante contra B del mismo momento | Sin empezar (depende de F7 y de cierres) |

## 3. ¿Hay data suficiente para el reentrenamiento del 1-nov?

- La puerta de frescura pasa: el último cierre sharp es del 22-oct; el 1-nov tendrá ~10 días (< 30). **Fallará hacia
  el 21-nov** si no se cargan cierres nuevos.
- El modelo entrena 12 años: los ~150 partidos posteriores al 22-oct pesan poco; lo que falta (xG de MLS, cierres) no
  rompe el 1-nov pero sí la validación sobre el periodo limpio (posterior al 22-oct), que es la única muestra no vista.
- No reentrenar ni promover por tener datos nuevos (decisión del 23-oct); sí cargar los cierres antes del 1-nov.

## 4. Completitud por liga (terminados jul-2023 → 21-oct-2026)

| Liga | n | xG | Córners | Tarjetas | Árbitro | Cierre 1X2 | Cierre totales | XI hist. | Bajas | xG desde | Córners desde |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Premier | 1.210 | 100 | 100 | 100 | 100 | 100 | 2 | 34 | 73 | 2017 | 2014 |
| LaLiga | 1.229 | 100 | 100 | 100 | 85 | 91 | 2 | 35 | 68 | 2017 | 2014 |
| Serie A | 1.210 | 100 | 100 | 100 | 85 | 91 | 2 | 35 | 75 | 2017 | 2014 |
| Bundesliga | 972 | 100 | 100 | 100 | 85 | 100 | 2 | 34 | 76 | 2017 | 2014 |
| Ligue 1 | 981 | 100 | 100 | 100 | 84 | 100 | 2 | 34 | 63 | 2017 | 2014 |
| Eredivisie | 1.008 | 100 | 100 | 100 | 86 | 90 | 2 | 34 | 70 | 2018 | 2017 |
| Primeira | 990 | 100 | 100 | 100 | 86 | 90 | 1 | 35 | 67 | 2018 | 2017 |
| Championship* | 1.801 | 100 | 100 | 100 | 100 | 87 | 0 | 0 | 70 | 2021 | 2014 |
| 2. Bundesliga* | 990 | 100 | 100 | 100 | 81 | 84 | 0 | 0 | 67 | 2021 | 2017 |
| Süper Lig* | 1.100 | 100 | 100 | 100 | 82 | 89 | 0 | 0 | 63 | 2022 | 2017 |
| Brasil | 1.329 | 100 | 80 | 80 | 67 | 100 | 2 | 35 | 53 | 2019 | 2024 |
| MLS | 1.755 | 100 | 86 | 86 | 82 | 100 | 4 | 30 | 43 | 2019 | 2024 |
| Liga MX | 1.126 | 99 | 84 | 84 | 61 | 86 | 3 | 33 | 57 | 2018 | 2024 |
| Argentina | 1.828 | 77 | 73 | 73 | 71 | 100 | 2 | 31 | 44 | 2016 | 2024 |
| UCL | 383 | 96 | 84 | 80 | 80 | 75 | 6 | 0 | 70 | 2017 | 2024 |
| UEL | 225 | 95 | 89 | 88 | 87 | 86 | 1 | 0 | 72 | 2017 | 2024 |
| Suiza* | 746 | 100 | 85 | 85 | 85 | 82 | 0 | 0 | 65 | 2021 | 2024 |
| Noruega* | 819 | 99 | 81 | 81 | 81 | 93 | 0 | 0 | 34 | 2021 | 2024 |
| Suecia* | 816 | 100 | 82 | 82 | 68 | 97 | 0 | 0 | 38 | 2021 | 2024 |
| LaLiga 2* | 1.514 | 69 | 100 | 100 | 78 | 88 | 0 | 0 | 57 | 2024 | 2017 |
| Serie B* | 1.239 | 37 | 100 | 100 | 64 | 79 | 0 | 0 | 64 | 2025 | 2017 |

`*` = sin modelo propio (`model_enabled = false`). Porcentajes sobre `n`.

**Lectura para entrenar:**
- **Completas** (todo el bloque, años de xG y córners): Premier, LaLiga, Serie A, Bundesliga, Ligue 1; casi completas
  Eredivisie y Primeira.
- **Candidatas a encender el Motor A** (hoy solo sharp): **Championship** (la más completa fuera del modelo),
  **2. Bundesliga** y **Süper Lig**. Necesitan que SofaScore las siga cubriendo (hoy sí) y pasar la puerta como
  cualquier otra.
- **Entrenables con huecos**: Brasil, MLS, Liga MX, Argentina (córners y tarjetas solo desde 2024; MLS y Liga MX sin
  SofaScore hoy). Copas: muestra pequeña y cierres incompletos.
- **No convienen hoy para un modelo con xG**: LaLiga 2 y Serie B (xG 69 % y 37 %, SofaScore no lo publica en LaLiga 2);
  Noruega y Suecia (bajas < 40 %, córners solo desde 2024). LaLiga 2, Serie B, Suecia y Suiza quedan retiradas por
  db/088. Con el xG de BetsAPI (sección 5) LaLiga 2 y Serie B pasarían a ~100 % desde 2023: solo importa si algún día se
  reactivan.
- Ninguna liga tiene historia de cierres de totales, córners o tarjetas: es el hueco común.

## 5. BetsAPI de fútbol (descarga del 23–25 oct en el VPS)

Archivo crudo en `~/betsapi/data/football/<liga>/{list,odds,prematch,upcoming}` (no está en la base). Leído en el host,
solo lectura: 23 competiciones, **~25.600 partidos terminados de jul/ago-2023 a oct-2026**.

| Qué trae | Cobertura medida |
|---|---|
| Estadísticas por partido | xG 90–100 % (Serie B y LaLiga 2 **100 %**), córners, tarjetas, faltas y centros ~100 % (Ligue 2 sin faltas), más tiros a puerta/fuera, ataques peligrosos, paradas, posesión, saques |
| Cuotas bet365 antes del inicio, con trayectoria | `1_1` 1X2, `1_2` hándicap asiático, `1_3` línea de goles, `1_4` córners asiáticos, `1_5`–`1_7` lo mismo del 1.er tiempo, `1_8` resultado al descanso: 94–100 % de los partidos |
| Última cuota antes del inicio (1X2) | mediana 4–16 min antes según liga (Premier 15, LaLiga 12,6, Argentina 4) |
| Mercados completos (`prematch`) | solo ~1 mes atrás (bet365 los borra) |

Comparación con nuestra base (emparejado por liga, hora ±1 h y marcador; 8 ligas):

| Liga | Emparejados | Corr. xG | Error mediano xG/equipo | xG que rellena | Córners iguales | Amarillas iguales |
|---|---|---|---|---|---|---|
| Premier | 1.065 | 0,972 | 0,09 | 0 | 95 % | 89 % |
| LaLiga | 1.203 | 0,974 | 0,08 | 0 | 98 % | 82 % |
| Championship | 1.295 | 0,961 | 0,11 | 0 | 95 % | 89 % |
| MLS | 1.307 | 0,957 | 0,12 | 0 | 98 % | 85 % |
| Brasil | 1.183 | 0,969 | 0,09 | 2 | 99 % | 56 % |
| Argentina | 1.335 | 0,947 | 0,12 | 0 | 99 % | 55 % |
| **LaLiga 2** | 1.453 | 0,964 | 0,10 | **450** | 98 % | 81 % |
| **Serie B** | 1.019 | 0,972 | 0,10 | **639** | 97 % | 85 % |

Lectura: el xG de BetsAPI es de otro proveedor pero muy parecido al nuestro (r ≈ 0,95–0,97) y **cierra casi todos los
huecos de xG de Serie B y LaLiga 2** (≈1.090 partidos). Córners coinciden; **tarjetas no** (55 % en Brasil/Argentina):
no mezclar amarillas de dos fuentes sin entender la diferencia (doble amarilla, banquillo). El emparejado simple deja
fuera 3–28 %; para cargar hay que emparejar por alias de equipo.

Límites: bet365 es una casa blanda, no Pinnacle (no sustituye al cierre sharp ni al CLV); la descarga se hizo el 23–25
oct, así que la **recepción original es desconocida** (vale para entrenar y calibrar, no como dato «disponible a tiempo»
ni para reescribir nada sellado); **la licencia de BetsAPI no está leída** y el producto es comercial; el plan caducó el
25-oct 05:15 UTC.

## 6. Recomendaciones (orden)

1. **Cargar los cierres de PropLine** a `odds_snapshots` (`window_tag='close'`, fuente propia, solo `closing_at` ≤
   inicio y sin `stale_close`, sin mezclar con las horarias), con ensayo en seco y antes del 1-nov. Reabre CLV, sombra,
   puerta comercial y frescura; incluye córners y tarjetas de Pinnacle, que nunca hemos tenido.
2. **Arreglar el descubrimiento de SofaScore en MLS y Liga MX** (comprobar ids de torneo/temporada y eliminatorias con
   una petición) y añadir una segunda captura de detalle por la tarde: hoy solo a las 07:40 con tope 40.
3. **Copiar las estadísticas de SofaScore a `matches.stats`** con las mismas claves (faltas, centros, tiros bloqueados,
   paradas, posesión, fueras de juego) para que el Motor C no pierda la serie.
4. **Histórico de onces de SofaScore** (ids de SofaScore) para `availability()` y `ajuste_xi`: sin él, el once y las
   bajas que ya llegan no pueden entrar al modelo. Empezar por las 7 ligas completas, 2 temporadas.
5. **Acoplar BetsAPI al historial** (sección 5), tras leer su licencia: (a) xG como relleno con
   `xg_source='betsapi'` y sin `xg_recorded_at` (histórico sin recepción acreditada) donde falte en las ligas activas
   (Argentina) y en Serie B/LaLiga 2 solo si se reactivan; (b) cuotas bet365 de hándicap, goles y córners (apertura y última antes del inicio) para calibrar B/C en los
   mercados que no tienen cierre; (c) faltas y centros para el Motor C. Carga a una tabla propia (como
   `historical_football_*`), nunca encima de lo sellado.
6. Sustituir la fuente del calendario de otras competiciones (descanso) y del pronóstico de clima; revisar los 175
   errores de ERA5.
7. Revisar `SOFT_BOOKS` frente a las casas de PropLine para que la sombra vuelva a ver ofertas.
