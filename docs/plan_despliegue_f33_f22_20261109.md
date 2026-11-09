# Despliegue de F3.3 (enlaces entre deportes) y F2.2 (páginas de equipo de NBA) — plan, 2026-11-09

## Qué se despliega
**F3.3 — enlaces reales entre deportes.**
- App: el selector de deporte de la cabecera pasa de `href="#picks"` (los tres iguales, sin valor para Google) a `/futbol/`, `/nba/`, `/tenis/`; el clic sigue interceptado (`preventDefault`), así que el
  comportamiento de la app no cambia. El pie lleva una barra con los tres pilares.
- Servidor: bloque «Otros deportes» en los tres pilares y una línea «Más pronósticos» en las tres páginas de partido.

**F2.2 — `/nba/equipos/<equipo>/`.** Cada página reúne los pronósticos SELLADOS de ese equipo (de `nba-api`): cuántos acertó el modelo, los últimos 10 partidos con su resultado, el próximo y la
situación del equipo (récord, últimos 6, racha). **Umbral:** indexable solo con ≥ 5 pronósticos sellados en los últimos 45 días; por debajo, la página existe pero lleva `noindex, follow` y no entra en el
sitemap ni se enlaza desde los partidos. Se abre dentro de la app (arranca en NBA). JSON-LD `SportsTeam`.

### Lo que hay que saber antes de desplegar
- **Hoy NINGÚN equipo supera el umbral.** Con datos reales (9-nov): 36 partidos sellados en 5 días (2 a 8-nov), 30 equipos, entre 1 y 4 pronósticos cada uno. Las 30 páginas existirían pero con `noindex`; el sitemap no cambia.
  Empezarán a entrar solas, equipo a equipo, a medida que el motor selle más (probablemente en una semana). El plan decía 12 meses; el motor NBA solo selló su primer pronóstico el 2-nov-2026, así que la ventana
  es de 45 días (`nba_equipos.DIAS_HISTORIA`) y se medirá cuántos equipos la superan antes de ampliarla.
- **La primera petición tras reiniciar tarda ~13 s** (hay que pedir a `nba-api` la cartelera de cada día desde el 2-nov; con caché de 6 h para los días de hace más de 3). Después, instantánea, y el cron de IndexNow (que
  pide el sitemap cada 30 min) la mantiene caliente. Crece con los días de temporada, acotado a 45.
- **Límite conocido de la app (anterior a esto):** al cambiar de deporte o de partido dentro de la app, la barra de direcciones sigue mostrando la URL con la que se entró. La página servida (canonical, título, HTML) es la correcta;
  actualizar la URL en cada selección es una mejora de la app para otra tarea.

## Alcance técnico
Servidor + frontend, sin red ni Caddy. Archivos: `src/qf/api/{nba_equipos.py (nuevo), nba_datos.py, nba_paginas.py, rutas_web.py, seo.py}`; `src/qf/api/paginas/{nba_equipo.html (nuevo), nba_partido.html, nba_cartelera.html,
futbol_cartelera.html, futbol_partido.html, tenis_cartelera.html, tenis_partido.html}`; `frontend/{app.js, rutas.js, index.html}` (`app.js?v=equipos-20261109`, `rutas.js?v=equipos-20261109`).
`main.py` de producción: **2 líneas** (`nba_equipos` en el `from . import …` y `app.include_router(nba_equipos.router)` justo después de `app.include_router(nba_paginas.router)`).

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F5 (`DEPLOYS.md`, 9-nov 04:48 UTC) y F3.x: comparar `sha256sum` en el contenedor con los blobs de `db0e50d4` para `src/qf/api/{nba_datos.py, nba_paginas.py, rutas_web.py, seo.py}`,
   las 7 plantillas existentes y `frontend/{app.js, rutas.js, index.html}`. `main.py` de producción: sha256 `833a2394…`.
3. `/health` 200; `nba-api` responde (`/nba/v1/cartelera?fecha=<hoy>` 200).
4. Respaldo en `~/respaldos/f33_f22_<fecha>/` con `SHA256SUMS`: los 14 archivos anteriores + `main.py`.

## 2. Copia y reinicio (cuidado: frontend y servidor juntos)
1. Copiar PRIMERO el servidor y las plantillas (`docker cp`; blobs de `origin/main`, LF, sha256 antes y después) y, justo después, el frontend (`index.html`, `app.js`, `rutas.js`): el HTML nuevo apunta a las versiones `?v=equipos-20261109`.
2. `main.py` (CRLF): dos cambios con `\r` en `sed`; comprobar que el diff son solo esas 2 líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores.
4. **Calentar la caché** antes de abrir nada: `curl` a `/sitemap-paginas.xml` desde el VPS (tarda ~13 s la primera vez).

## 3. Verificación en el dominio real (consultas únicas por la caché de Cloudflare)
- `/nba/equipos/chicago-bulls/` (o cualquier equipo): 200, `robots` = `noindex, follow` mientras no pase el umbral, canonical correcto, JSON-LD `SportsTeam`, y la app arranca en NBA con la URL conservada.
  `/nba/equipos/no-existe-fc/` y `/nba/equipos/` → 404; `/nba/equipos/chicago-bulls` → 301.
- El sitemap **no** incluye ninguna página de equipo mientras no pasen el umbral (y las incluye con `lastmod` cuando lo pasen; no hace falta tocar nada).
- Enlaces: la cabecera y el pie de la app llevan `/futbol/`, `/nba/`, `/tenis/` (hrefs reales); el clic en el selector de deporte sigue cambiando de deporte sin recargar; los tres pilares y las tres páginas de partido enlazan a los otros dos deportes.
- Hashes de `app.js`, `rutas.js` e `index.html` servidos con consulta única = los de `main`. Regresión de las rutas habituales en 200, incluida la portada y `/planes/`; 0 errores en el log; el cron de IndexNow sigue sin fallos.
- En un navegador real (con `qf_ads=no` antes y borrado después): la app arranca, «Historial» y «atrás» funcionan.

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_f33_f22)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 14 archivos y `main.py`; borrar `nba_equipos.py` y `nba_equipo.html` del contenedor;
`docker restart quantfut-api-1`. Las páginas de equipo pasan a 404 y los enlaces nuevos desaparecen; el frontend anterior no depende de nada nuevo. Las URLs `?v=equipos-20261109` quedan 4 h en la caché de Cloudflare.

## 5. Riesgos conocidos
- La caché de `nba-api` crece (192 entradas) y la primera petición tras reiniciar es lenta (arriba). Si `nba-api` cae, las páginas de equipo dan 503 con `Retry-After` (nunca 404) y el sitemap solo omite los equipos.
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores).
- Una página con pocos partidos puede parecer escasa: por eso lleva `noindex` hasta tener ≥ 5 y dice claramente «las cifras todavía no dicen nada».
