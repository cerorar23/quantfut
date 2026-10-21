# Orden de identidades — medición en producción (18-oct-2026)

Medición hecha en solo lectura el 18-oct. **Después el titular autorizó ejecutar** las correcciones de Arsenal y
de los alias; lo aplicado, con cifras y vuelta atrás, está en `docs/datos_al_motor_20261018.md` y en `DEPLOYS.md`.
La §6 queda como registro de las decisiones que se tomaron.

## 1. Hallazgo principal: 33 partidos de Arsenal están a nombre de Arsenal de Sarandí

La tabla `team_aliases` tiene `('Arsenal', 'fbref') → 28402` (Arsenal de Sarandí, `ar.primera`).
En las copas, `match_team` sin liga acepta un alias que apunte a un solo club
(`_alias_valido`, `normalize.py:86`), así que el nombre «Arsenal» de FBref cae en el club argentino.

- **Alcance medido:** 33 partidos de `eu.ucl`/`eu.uel` entre 2014-09-16 y 2024-12-11 tienen a
  Arsenal de Sarandí (`team_id` 28402) como local o visitante (7 en 2024, de Champions
  contra Porto, Bayern, PSG, Sporting y Mónaco). Ninguno tiene predicciones, cuotas, `features_pit`,
  alineaciones ni archivo FotMob vinculado; **23 de los 33 tienen xG**, que sí entra al modelo.
- **Ya correcto desde 2025-09:** los partidos de copa de Arsenal posteriores usan `team_id` 3
  (ejemplo: `eu.ucl:2526:arsenal-bayernmunic:20251126`). El error está solo en el histórico.
- **Es el mismo tipo de error** que avisa CLAUDE.md (Rangers/Angers) y que el archivo FotMob ya
  detectó: son los 7 «conflictos de oponente cercano» de Arsenal.
- **Otros choques de nombre entre países dentro de las 23 ligas:** solo tres en total
  (Arsenal; Santos MX/BR; Vitória BR/PT). Santos y Vitória no afectan a las copas europeas.
- **Efecto sobre el modelo:** esperable pequeño (el decaimiento de 180 días deja los partidos de 2024
  con peso <0,1), pero no medido. Arsenal pierde 33 partidos de copa de su historial y Arsenal de
  Sarandí (liga modelada) recibe 33 resultados contra la élite europea.

**Corrección propuesta** (script con ensayo y reversión, sin ejecutar):
1. `UPDATE matches` de esos 33 `match_id` cambiando 28402 → 3 (lado local o visitante). El único
   trigger de `matches` es `trg_matches_retired` (solo bloquea ligas retiradas, no afecta a `eu.*`).
   Hay que respaldar y verificar que no exista ya otra fila de Arsenal para ese día; los `match_id`
   llevan el slug `arsenal-…` y no cambian.
2. Quitar o acotar el alias `('Arsenal','fbref')→28402` a `ar.primera`; añadir `('Arsenal','fbref')→3`
   dejaría el alias ambiguo en copas (dos clubes ⇒ no se adivina), que es lo deseable.
3. Reentrenar: el del 1-nov lo recoge solo, si la corrección se hace antes.

## 2. «379 identidades» son 379 partidos de 110 equipos, y ninguno se puede unir

| | FotMob | Sofascore |
|---|---|---|
| Partidos de copa sin vínculo | 379 | 34 |
| Equipos distintos | 110 | 52 |
| Con id probado en partidos de liga (único) | **67** | 18 |
| Sin id probado | 43 | 34 |
| Partidos con **ambos** equipos probados | **0** | 0 |
| Partidos con un solo equipo probado | 308 | 19 |
| Partidos sin ningún equipo probado | 71 | 15 |

- Los **67** equipos de FotMob son los clubes de nuestras ligas (Arsenal 9825, Barcelona 8634,
  Inter 8636, Bayern 9823…). Cada uno tiene entre 51 y 105 partidos de liga ya vinculados que lo
  confirman y apunta a un único `team_id`. Es seguro registrarlos como identidad conocida.
- Los **43** restantes son clubes de ligas que no cubrimos (Celtic, Club Brugge, Anderlecht,
  Salzburgo, Ferencváros, PAOK…). La coincidencia aproximada daría uniones falsas: «Pafos FC» →
  «Paris FC» (0,75) y «Rangers» → «Angers» (0,92). No se vinculan.
- **Consecuencia:** como el rival de cada uno de esos 379 partidos siempre es un club externo,
  resolver los 67 no libera ninguno. Se puede cerrar el pendiente como «no resoluble por diseño»
  (la regla del proyecto es no dar de alta equipos bajo `eu.ucl` ni `eu.uel`). Para incluirlos
  habría que registrar esos clubes con una liga doméstica propia: decisión de alcance, no de datos.
- Conflictos: 18 de FotMob y 2 de Sofascore (el pendiente decía 21). De los de FotMob, 7 son los de
  Arsenal (§1), 2 de copa por marcador o estado (Atlético–Inter y Marsella–Benfica 2024, que
  terminaron en prórroga o penaltis; sin confirmar) y 9 de liga (Argentina 5, Suecia 3, MLS 1). Por
  revisar uno a uno; no se fuerzan.

## 3. Alias de Champions y Europa League para los cierres (103 partidos)

Los snapshots ya están descargados (`/srv/quantfut/artifacts/odds_hist`): 107 nombres distintos,
73 con alias y 34 sin. De esos 34, **solo 4 son clubes nuestros**:

| Nombre en The Odds API | Equipo | `team_id` |
|---|---|---|
| Bayern München | Bayern Munich | 61440 |
| Internazionale Milano | Inter | 12102 |
| LOSC Lille | Lille | 68864 |
| Young Boys | BSC Young Boys | 85077 |

Simulado en memoria con `cargar(..., aplicar=False)` (cero créditos, cero escrituras):

| Competición | Pendientes | Cierres cargables hoy | Con los 4 alias |
|---|---|---|---|
| Champions | 81 | 0 | **35** |
| Europa League | 22 | 0 | **4** |

Quedan **64** sin cierre: enfrentan a clubes externos (los otros 30 nombres). No se pueden recuperar
sin esos alias de clubes que no modelamos. Efecto: baja de 103 a 64 los partidos de copa sin cierre
y no cuesta créditos.

## 4. Árbitros (F5)

- API-Football escribe «A Taylor» (inicial y apellido); FotMob, «Anthony Taylor».
- Desde 2024: 376 nombres distintos de API-Football y 847 de FotMob; 2.332 partidos tienen ambos.
- Cruce por coincidencia dentro de esos 2.332 partidos: **67** nombres de API-Football aparecen
  emparejados con algún nombre FotMob; **42** con uno solo (limpios) y **25** con una pareja
  dominante más pares sueltos de 1 partido (ruido, p. ej. «A Kitchen» con Andrew Kitchen en 68
  partidos y Joshua Smith en 1).
- Regla propuesta: aceptar el par si tiene ≥5 partidos y ≥90 % de los de ese nombre; el resto se
  revisa a mano. Aplicaría a 132 partidos con árbitro FotMob y sin árbitro API-Football que ya
  tienen par; los otros 783 nombres de FotMob (ligas sin árbitro en API-Football) no tienen
  equivalente y quedan con su nombre completo.
- Hasta que se unifique, el factor de árbitro de tarjetas solo ve el formato API-Football
  (2.799 partidos desde 2024 frente a 19.183 con árbitro FotMob).

## 5. Jugadores (F4)

- 4.869 partidos tienen jugadores en las dos fuentes. De 151.467 filas de API-Football en ellos,
  **132.676 (87,6 %)** tienen una fila FotMob con el mismo partido, lado y nombre normalizado.
- Quedan 18.791 (12,4 %) sin nombre exacto: habrá que cruzar por inicial más apellido y minutos.
- Jugadores únicos: 8.373 (API-Football) y 22.125 (FotMob). Un puente por identificador necesita que
  cada `player_id` de API-Football caiga en un único `source_player_id` de FotMob en varios partidos.
  Pendiente de calcular y de umbral; es parte de F4.

## 6. Decisiones (resueltas el 18-oct)

1. **Arsenal (§1) — hecho:** ¿corregir los 33 partidos y el alias antes del 1-nov, para que el reentrenamiento
   los use bien? Cambia datos de entrenamiento; con respaldo, ensayo y anotación en `DEPLOYS.md`.
2. **4 alias de The Odds API (§3) — hechos (+45 cierres):** ¿registrarlos y cargar los 39 cierres? Escribe en
   `team_aliases` y en `odds_snapshots` (tabla inmutable, sin DELETE).
3. **43 clubes externos (§2) — siguen fuera** (sin decisión contraria): se registran con una liga propia solo si se pide.
4. Los 67 equipos de FotMob (§2) y el cruce de árbitros (§4) son ordenar sin tocar el motor; irían
   después de F7 salvo que se pidan antes.
