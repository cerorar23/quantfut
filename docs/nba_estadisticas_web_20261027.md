# NBA: estadísticas de equipos en la ventana de la web (27-oct-2026)

Petición del titular: que la ficha de un partido de NBA tenga estadísticas tan detalladas como las de una comparadora de
pronósticos (referencia: Wincomparator, Boston–Brooklyn), con el diseño CYBERCORE CSS que ya usa la web. Se copian los bloques
que se pueden calcular con datos reales; los demás no se inventan.

## Qué se añadió (rama `web/nba-estadisticas`, sin desplegar)

Cuatro pestañas nuevas en la ventana de NBA (`frontend/sports-window.js`), entre Resumen y Disponibilidad:

| Pestaña | Contenido | Equivale en la referencia a |
|---|---|---|
| Comparativa | récord, posición en la conferencia, últimos 6, local en casa / visitante fuera, puntos a favor y en contra, diferencial, racha, descanso (back-to-back), récord de la temporada pasada | «Victorias / Derrotas» |
| Forma | últimos 6 partidos de cada equipo con filtro Todos / En casa / Fuera, marcadores y rival | «Forma» |
| Cara a cara | últimos 6 enfrentamientos (incluye temporadas anteriores), victorias de cada lado y total medio | «Enfrentamientos H2H» |
| Clasificación | fila de cada equipo: posición, J, V, D, %, PF, PC, racha | «Clasificación» |

**No se copia, porque ninguna fuente validada lo trae:** alineaciones y plantilla del partido, estadio y capacidad, y cuotas por
cuarto/mitad de casas de apuestas. La web lo dice en vez de rellenarlo.

## Cómo se calcula

- `apps/nba/src/nba/web_stats.py` (puro, sin red): resume marcadores finales de `data/games.json` (2021-22 a hoy), de
  `completed_games.json` de cada cohorte sellada y de los resultados oficiales que el panel ya verifica
  (`LiveCohort.data`). Si dos fuentes discrepan en un marcador, el partido se descarta (no se elige uno).
- Cada partido se calcula **a la fecha**: solo cuentan partidos de días anteriores (fecha del Este), así que un partido ya
  jugado muestra lo que se sabía antes de empezar y no su propio resultado.
- La clasificación solo cuenta temporada regular; la forma y el cara a cara incluyen play-in y eliminatorias, no pretemporada.
  La posición ordena la conferencia por % de victorias y luego victorias: no replica los desempates oficiales de la NBA.
- El descanso solo se informa si el último partido fue hace ≤ 10 días (no hay «descanso» tras el receso ni al abrir la temporada).
- `src/qf/api/nba_estadisticas.py` solo **lee** el JSON público (`QF_NBA_STATS_FEED`, por defecto
  `/srv/quantfut/artifacts/public-sports/nba_stats.json`); vence a las 6 h, descarta eventos mal formados o con números no
  finitos y lo sirve en `GET /web/deportes/nba/estadisticas/{id}` (10 dígitos, `Cache-Control: no-store`). No ve cohortes, modelos
  ni sellos. No toca el pipeline predecir → sellar → publicar.

Comprobado con datos reales (solo lectura del servidor): 6.552 partidos en la base + 43 de 2026-27, 45 eventos, 288 KB de feed
(≈ 6 KB por partido). Boston–Chicago del 26-oct: forma, 6 cara a cara de 2024-25 a 2026 y clasificación calculados sin errores; no se contrastaron una a una con nba.com.

## Pruebas

- `apps/nba/tests/test_web_stats.py` (14), `tests/test_nba_estadisticas.py` (4), `frontend/nba-stats.test.mjs` (5, añadido a
  `npm run check`). Suite del frontend 65/65.
- Vista previa en el navegador con el feed real: las 8 pestañas, el filtro de forma y el escape de nombres; a 375 px la
  clasificación oculta PF y PC para no desbordar.

## Despliegue (PENDIENTE; requiere confirmación del titular y `DEPLOYS.md`)

1. PR a `main` con arnés verde; reconstruir la imagen de la API (ruta nueva + `frontend/`) con el flujo de `DEPLOYS.md`.
2. Exportador en el host (nuevo, aparte): ejecutar `python -m nba.web_stats --cohorts <cohortes> --data <data> --output <tmp>` en
   un contenedor con la imagen NBA de `main` (necesita numpy/scipy; el módulo importa el panel para verificar las cohortes),
   `--network none`, cohortes y datos en solo lectura; después escribir `nba_stats.json` en el volumen de artefactos como ya hace
   el exportador de tenis (`os.replace`). Cron sugerido cada 30 min (el feed vence a las 6 h).
3. Sin el exportador la web muestra «Todavía no hay estadísticas publicadas para este partido»: la ruta nueva no rompe nada.
4. Vuelta atrás: quitar la línea de cron y borrar `nba_stats.json`; la imagen anterior de la API sigue sirviendo la ventana sin
   esas pestañas.
