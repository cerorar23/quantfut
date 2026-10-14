# F0 — Archivo FotMob integrado a las tablas principales (14-oct-2026)

Primera fase de [la spec de señales del motor](superpowers/specs/2026-10-14-senales-motor-principal-design.md);
plan: [2026-10-14-f0-integrar-archivo.md](superpowers/plans/2026-10-14-f0-integrar-archivo.md).
Código: `src/qf/ingest/archivo_a_matches.py`; migración `db/067_f0_archivo_a_matches.sql`.

## Qué se hizo

Se pasó a `matches` lo ya archivado en `historical_football_*`, solo en columnas
vacías y con la procedencia de cada campo en `matches_enriquecimiento`
(122.798 filas, `captured_at` = recepción real del original).

| Dato | Partidos rellenados (desde 2024-01-01) | Hueco antes → después |
|---|---|---|
| Amarillas y rojas | 8.118 | 8.412 → 294 |
| Marcador al descanso | 7.085 | 7.325 → 240 |
| xGOT (`home_xgot`/`away_xgot`, nuevas) | 18.321 | 20.854 → 2.533 |
| Árbitro (`referee_fotmob`, nueva) | 19.183 | `referee` vacío 18.280 → 1.429 con algún nombre |
| Sede (`stadium_id`, tabla `estadios` nueva) | 20.331 | 20.854 → 523 |
| Córners, tiros, tiros a puerta | 0 | sin cambio (250 / 247 / 245): FotMob no los cubre |

`estadios`: 758 sedes con nombre, ciudad, país, coordenadas, capacidad y
superficie. Las coordenadas son las que usará el clima (F6).

## Decisiones

- **Solo se rellena NULL**, nunca se pisa un valor, y un par local/visita entra
  completo o no entra. Un dato ausente o inválido (negativo, NaN, decimal en un
  conteo) queda NULL, nunca 0.
- **xGOT no es PSxG.** Columnas propias; `home_psxg` no se toca.
- **El árbitro de FotMob va a `referee_fotmob`.** `matches.referee` conserva el
  formato de API-Football que lee el motor de tarjetas. El id de árbitro de
  FotMob aparece en 18 de 300 originales: no sirve para identificarlo.
- **Marcador distinto entre archivo y partido ⇒ se omite.** Resultado real: 0
  omitidos.
- **El simulacro previo fue de solo lectura**, sin DDL: `ALTER TABLE matches`
  toma un bloqueo exclusivo hasta el final de la transacción y habría frenado
  API y workers.

## Contraste de FotMob con los valores que ya había

Sobre los partidos donde coinciden las dos fuentes (≈12.200 en tarjetas):

| Dato | Coincide | Si difiere |
|---|---|---|
| Descanso | 100 % | — |
| Córners | 99,5 % | ±1 |
| Tiros a puerta | ~95 % | ±1 |
| Tiros | ~91 % | ±1 a 3 |
| Rojas | ~99,6 % | FotMob da +1 |
| Amarillas | ~94 % | FotMob da +1 |

La definición de tarjeta no es idéntica entre fuentes. Efecto práctico: las
ligas que casi no tenían amarillas (Argentina 15→1.306 partidos, Brasil 14→1.050,
Europa League 0→195, Suiza, Dinamarca, Champions 7→290) pasan a tener muestra
real, y su media baja (Argentina 4,87→3,49, porque la de 15 partidos era ruido).
En las ligas que ya tenían historial el cambio es casi nulo. El motor de tarjetas
y el reto escalera leen estas columnas, así que sus probabilidades se mueven en
las ligas con muestra nueva. Los campos de FotMob son identificables en
`matches_enriquecimiento`.

## Aplicación y verificación

1. Respaldo de `matches`: `~/backups/matches_pre_f0_20261014.sql.gz` (VPS, 3,9 MB).
2. `db/067` aplicada con `lock_timeout = 10s`.
3. Relleno con `aplicar()` ejecutado por stdin en el contenedor `api` (no se dejó
   código nuevo en el contenedor).
4. Segunda pasada: `rellenados = {}`.
5. Modelo activo sin cambios (`2026.09.27-010508`), API 200, servicios arriba,
   cero descansos mayores que el marcador final.

## Reversión

Un campo rellenado se vuelve a vaciar con
`UPDATE matches SET <col> = NULL WHERE match_id IN (SELECT match_id FROM matches_enriquecimiento WHERE campo = '<col>')`
y borrando esas filas de `matches_enriquecimiento`. El respaldo completo está en
el servidor.

## Pendiente de F0

- Los huecos de xG (1.222 desde 2024) no se cierran con este archivo; el informe
  por competición es `huecos_xg()`. Fuente nueva: decisión del usuario.
- Tiros y córners restantes (≈250) no están en FotMob.
