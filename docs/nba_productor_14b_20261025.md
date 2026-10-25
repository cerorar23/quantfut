# NBA — productor vivo 1.4.0 con RUN071 + columnas nuevas y mercado de pérdidas (25-oct-2026)

En la validación de 1.4 (`docs/nba_productor_14_20261025.md`) el dataset ampliado se rechazó entero: con play-in y playoffs en el historial
empeoraban rebotes y asistencias. Con eso, ritmo, defensa rival y tendencia de uso quedaron con valor 0 (RUN071 no trae posesiones ni tiros) y
pérdidas no se podía probar. Esta variante separa las dos cosas: **conserva el historial de temporada regular de RUN071 y solo le añade las
columnas nuevas** de esos mismos partidos. Protocolo congelado antes de correr: `apps/nba/nba_live14b_protocol.json`
(sha256 `cb74f1a1…`, en `apps/nba/.local/normalized/nba_live14b_20261025/protocol_frozen.json`).

## Datos (`nba.live14b_data`)
- Cada fila de jugador de RUN071 toma `tov`, `fga`, `fta` y `oreb` de la misma (partido, jugador, equipo) del dataset ampliado; cada partido, la
  `possessions_estimate` de cada lado. No se añade ni quita ninguna fila, partido ni tipo de temporada (solo `regular`).
- Las 156.571 filas copiadas coinciden con RUN071 en puntos, rebotes, asistencias, triples, robos y tapones (si una no coincide, la construcción se para).
- 1.391 filas (los 53 partidos que el ampliado puso en cuarentena) quedan sin las columnas; 6.055 de 6.108 partidos tienen posesiones.
- El módulo reproduce byte a byte los archivos validados (`players.jsonl.gz` `e5326b7f…`, `games.json` `c2c13b36…`).

## Validación (`nba.live14b_check`)
Referencia = configuración 1.4.0 desplegada (RUN071, reportes antiguos + T-60, BASE + ENV, 11 mercados). Candidata = la misma sobre los datos nuevos.
Mismo `fit_model` del productor como si el objetivo fuera 2025-26, mismas unidades (rejilla de la referencia), bootstrap por fechas (400, semilla 20261030).

| Mercado | Unidades | Brier 1.4.0 | Brier variante | Diferencia (IC 99,55 %) |
| --- | ---: | ---: | ---: | --- |
| Puntos | 169.400 | 0,21977 | 0,21956 | −0,00020 [−0,00033; −0,00007] |
| Rebotes | 155.076 | 0,16835 | 0,16831 | −0,00004 [−0,00007; −0,00001] |
| Asistencias | 136.365 | 0,14731 | 0,14715 | −0,00016 [−0,00025; −0,00009] |
| P+R | 172.315 | 0,22610 | 0,22592 | −0,00018 [−0,00031; −0,00007] |
| P+A | 171.075 | 0,22314 | 0,22282 | −0,00032 [−0,00046; −0,00016] |
| R+A | 166.083 | 0,18855 | 0,18840 | −0,00015 [−0,00022; −0,00009] |
| P+R+A | 172.914 | 0,22865 | 0,22838 | −0,00027 [−0,00042; −0,00013] |
| Triples | 119.435 | 0,11772 | 0,11769 | −0,00004 [−0,00009; +0,00001] |
| Robos | 108.121 | 0,10398 | 0,10393 | −0,00005 [−0,00008; −0,00001] |
| Tapones | 102.793 | 0,07200 | 0,07199 | −0,00001 [−0,00004; +0,00001] |
| Robos + tapones | 118.871 | 0,12502 | 0,12496 | −0,00006 [−0,00010; −0,00001] |
| **Conjunto (IC 95 %)** | 1.592.448 | | | **−0,00015 [−0,00021; −0,00010]** |

**Entran los datos**: mejora el conjunto y ningún mercado empeora. Ritmo, defensa rival y tendencia de uso ya tienen peso
(en puntos 0,11 / 0,10 / 0,12). La ganancia es pequeña: lo grueso de 1.4 sigue siendo los reportes T-60.

**Pérdidas entra** (81.118 unidades de 2025-26): la calibración viva le gana a la ley cruda en −0,0012 [−0,0015; −0,0008] (IC 99 %),
Brier 0,1200 frente a 0,1212, pendiente 0,996 e intercepto −0,017.

## Qué cambia en producción
- La carpeta de datos del servidor pasa a RUN071 + columnas (la anterior se conserva para volver atrás) y el modelo se ajusta con ella y las
  opciones aceptadas (12 mercados de jugador). El código del productor no cambia (`multimarket_v13_live.py` igual, versión 1.4.0); el modelo nuevo
  se distingue por su sha256 en cada sellado.
- El panel añade la pestaña **Pérdidas** (los resultados oficiales ya leían `turnovers`).
- Un jugador cuyo historial reciente toca uno de los 53 partidos sin columnas no recibe pronóstico de pérdidas ni tendencia de uso (vale 0) hasta que ese
  partido sale de su ventana.

## Límites
- Retrospectivo sobre 2025-26; la prueba real es el registro prospectivo.
- Sigue fuera: play-in/playoffs en el historial, ajuste de anotación dentro de la temporada, doble-doble, cuartos 3-4 y márgenes por rangos.
