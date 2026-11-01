# Fútbol: auditoría de duplicados y camino a una base única (31-oct-2026)

> **Nota del 1-nov-2026:** esta auditoría (31-oct) sigue valiendo para lo medido (equipos y partidos sin duplicados; temporadas con formato raro, ya corregidas con db/086 de la rama anterior). El plan por fases A-E quedó superado por la tabla única `futbol.dato`: ver `docs/futbol_modelo_canonico_20261101.md`.


Solo lectura sobre la base del VPS (`quantfut-db-1`, 3,6 GB, 97 GB de disco con 46 GB libres). No se borró ni cambió nada. Fecha de la medición: 31-oct-2026.

## 1. Lo que NO está duplicado (verificado)

| Comprobación | Resultado |
|---|---|
| Equipos (`teams`, 643 en 21 ligas) con el mismo nombre normalizado en la misma liga | 0 |
| Equipos con el mismo nombre en ligas distintas | 0 |
| Equipos dados de alta bajo `eu.ucl` / `eu.uel` | 0 |
| Partidos (`matches`, 93.258) con los mismos equipos y mismo sentido a menos de 36 h | 0 |
| Mismos equipos con local y visitante invertidos a menos de 36 h | 0 |
| Un equipo con dos partidos a menos de 20 h en la misma liga | 0 |
| `external_ids` repetidos entre dos partidos | 0 |
| Terminados sin marcador / con marcador sin estar terminados | 0 / 0 |
| Alias duplicados | 2 (`arsenal`, `santos`), ambos legítimos: clubes distintos de países distintos |

Los motores no ven partidos ni equipos repetidos.

## 2. Lo que sí hay, con su efecto

1. **Estandarización de temporada (103 partidos con `YYYY/YYYY` y 19 con `match_id` `fotmob:`).** Partidos creados por la importación de FotMob (`match_id = fotmob:NNN`; 103 con ese formato y 19 más con formato raro) llevan la temporada como `2023/2024` en lugar de `2324`: Championship, Serie B, LaLiga 2, Eredivisie, Champions, Europa League y Superliga danesa (playoffs y fases previas). Una consulta por temporada los trata como otra temporada. No son duplicados. `matches.match_id` lo referencian 36 tablas: **no se renombran ids**; solo `season` es corregible.
2. **Bajas repetidas en `injuries` (efecto visible).** 580 grupos jugador-partido-lado (3.395 filas) los informan dos fuentes (API-Football, FotMob, SofaScore). Ocurre en la ventana 29-31 oct, cuando FotMob y SofaScore empezaron a capturar mientras API-Football ya había parado (25-oct). La ficha del partido (`api/fichas.py:292`) lista todo lo insertado entre las dos últimas capturas sin deduplicar entre fuentes, así que un jugador puede salir dos veces. Las repeticiones dentro de una misma fuente son capturas sucesivas, no duplicados.
3. **Dos fuentes de estadísticas de jugador en motores distintos.** `estadisticas_jugador` (API-Football, 161.476 filas, 5.189 partidos) la lee `model/player_value.py`; `fotmob_jugador_partido` (885.743 filas, 21.120 partidos) la leen `model/jugadores.py` y `model/ajuste_xi.py`. 5.168 de los 5.189 partidos están en las dos. No es un registro duplicado, son dos fuentes para el mismo hecho; API-Football ya no se renueva.
4. **Cuatro tablas de once** con propósito distinto (en vivo, previstas, históricas de API-Football, FotMob). Solo hay solape de partidos: 175 entre `lineups` y `lineups_previstas`, 21 entre `lineups` e históricas. Ninguna tabla repite filas.

## 3. Corrección a lo dicho antes: `historical_football_player_stats` NO es un duplicado seguro

El 31-oct se anotó que esos 1,1 GB se recuperaban «si ningún consumidor lee el JSONB». Revisado en `main`:

- Ningún código de `src/` ni `scripts/` la lee, pero la vista `v_fotmob_jugador_partido` (db/075) la une para sacar **`minutos` y `estadisticas`**, que `fotmob_jugador_partido` no tiene.
- No son copias exactas: de 20.329 partidos comparados, 601 difieren en número de jugadores; hay 966 jugadores solo en la histórica y 2.103 solo en la tipada.
- `fotmob_a_motor` rellena `fotmob_jugador_partido` y `fotmob_baja` desde `historical_football_matches.raw_payload_gzip` (el original, 509 MB). Las hijas (`player_stats` 1.102 MB, `lineups` 134 MB, `absences` 11 MB) son derivadas de ese original.
- `historical_football_absences` sí coincide con `fotmob_baja` (0 diferencias en 47.140 filas).

Conclusión: no se borra nada hoy. Con 46 GB libres el peso no pone en riesgo el disco; el riesgo real para los motores son los puntos 2 y 3.

## 4. Hallazgo de proceso que condiciona el arreglo

La rama de trabajo actual (`nba/v13-disponibilidad`) está **101 commits por detrás de `main`** y **no contiene** `db/075`-`db/084`, `fotmob_a_motor.py`, `fotmob_captura.py` ni `puentes_jugadores.py`. Además el cargador SofaScore escrito hoy usa números de migración (`073_`, `074_`) que en `main` ya están ocupados (`main` llega a `084_sello_por_partido.sql`). Todo arreglo de base debe hacerse desde un `git worktree` creado desde `main`, con migraciones desde `085`.

## 5. Plan por fases (de menor a mayor riesgo)

| Fase | Qué | Toca datos | Riesgo |
|---|---|---|---|
| A | Vistas de lectura únicas: `v_bajas_unicas` (una fila por jugador-partido-lado, prioridad FotMob > SofaScore > API-Football, usando `puente_jugador` para la identidad) y `v_jugador_partido_unico`; la ficha lee de la vista | No, solo vistas | Bajo |
| B | Corregir `season` de los 122 partidos a `AABB` (sin tocar `match_id`) | Sí, 122 filas de `matches` | Medio: comprobar que ninguna consulta dependa de la etiqueta rara |
| C | `player_value` pasa a leer `fotmob_jugador_partido` y se retira `estadisticas_jugador` del camino del motor | Cambia el motor | Alto: cambia predicciones, exige evaluación antes y después |
| D | Esquema `futbol` del archivo SofaScore con migraciones desde `085`, originales solo como archivos | Tablas nuevas | Bajo-medio |
| E | Compactar `historical_football_player_stats` (quitar el JSONB redundante conservando `minutes`) | Sí, 1,1 GB | Medio; solo si hace falta disco |

## 6. Estado de las fases (1-nov-2026)

| Fase | Estado |
|---|---|
| A | **Hecha en la base** (db/085): `futbol.v_baja_previa_unica`, `v_baja`, `v_jugador_partido`. La ficha del partido (`api/fichas.py`) ya deduplica las bajas entre fuentes en la rama `futbol/base-unica`; **falta desplegar la API** |
| B | **Hecha** (db/086): 103 temporadas pasan a `AABB`; el importador FotMob ya las crea así. Quedan 19 `match_id` `fotmob:` (no se renombran) |
| D | **Hecha**: esquema `futbol` con el formato del scraper y 9.489 partidos de 9 ligas cargados desde el archivo del VPS (442 MB); una fuente dueña por entidad y partido, prioridad SofaScore > FotMob > API-Football |
| C | **No aplicada, a propósito.** Los motores leen `fotmob_jugador_partido` con ids de jugador de FotMob (`ajuste_xi` arrastra la fuerza de cada jugador por ese id). Pasar a SofaScore mezcla ids y cambia predicciones: exige el puente de ids (`puente_jugador` ya tiene FotMob <-> API-Football, falta SofaScore) y medir antes y después |
| E | **No necesaria**: con 45 GB libres no hay riesgo de disco |

