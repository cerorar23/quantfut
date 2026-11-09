# Despliegue de F3.2 (páginas de tenis dentro de la app) — plan, 2026-11-09

Qué se despliega: `/tenis/` y `/tenis/<torneo>/<jugador-a>-vs-<jugador-b>-<AAAA-MM-DD>/`, dentro del shell de la SPA, con datos del feed
público que ya sirve `/web/deportes/tenis`. **Solo servidor: no cambia ningún archivo de frontend** (el arranque por URL de tenis
`winEvent = tenis:<id>` ya está en producción desde F3.0/F2.1) **y no hay cambios de red ni de Caddy** (`/tenis/…` cae en el
`reverse_proxy api:8000` por defecto). Método: `docker cp` + `docker restart quantfut-api-1` (igual que F2.1 y F3.1). No recrear el
contenedor, no `docker commit`, no `scripts/deploy.sh construir api`. Solo despliega una sesión a la vez y `main` debe contener el PR.

## Lo único delicado: el orden de los routers en `main.py`
`/tenis/v2/metodologia` y `/tenis/v2/cartelera` encajan también en `/tenis/{torneo}/{slug}`. Starlette responde con la **primera** ruta que
encaja, así que `app.include_router(tenis_paginas.router)` tiene que ir **después** de `app.include_router(tenis_v2_router)`. En el repo ya
es así (línea posterior); en el `main.py` de producción hay que comprobarlo antes de parchear (`grep -n "tenis_v2_router" main.py`) y
poner la línea nueva justo detrás de la de `tenis_v2_router`, no detrás de la de `futbol_paginas`. La prueba
`test_el_motor_de_tenis_gana_a_las_paginas` lo exige en el repo; en producción se comprueba a mano en el ensayo interno (§2.4).

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F3.1 (`DEPLOYS.md`, 9-nov 03:00 UTC): comparar `sha256sum` en el contenedor con los blobs de
   `19edb461` para `src/qf/api/{seo.py, rutas_web.py}` y `src/qf/api/paginas/base.html`. `main.py` de producción: sha256 `dc1bdac8…` (tras F3.1).
3. `/health` 200; `GET /web/deportes/tenis` con `state` `ok` o `partial` y eventos (si el feed está caducado o ausente las páginas dan 503 a propósito).
4. Respaldo en `~/respaldos/tenis_f32_<fecha>/` con `SHA256SUMS`: `seo.py`, `rutas_web.py`, `base.html` y `main.py`.

## 2. Copia y reinicio
1. `docker cp` de: `tenis_datos.py`, `tenis_paginas.py` (nuevos), `seo.py`, `rutas_web.py` a `/app/src/qf/api/`; `paginas/{tenis_cartelera.html,
   tenis_partido.html}` (nuevos) y `base.html` a `/app/src/qf/api/paginas/`. Los archivos salen de blobs de `origin/main` (LF) y se comparan por sha256.
2. `main.py` de producción (CRLF): dos cambios con `\r` en `sed` — añadir `tenis_paginas` al `from . import …` y `app.include_router(tenis_paginas.router)`
   justo después de `app.include_router(tenis_v2_router)`. Comprobar que el diff son solo esas 2 líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores.
4. Ensayo interno desde el VPS contra `127.0.0.1:8000` con `Host: pronosticosdeportivos.pro`: `/tenis/`, una página de partido real (la primera del pilar), un 404,
   `/tenis` → 301, el sitemap, y **`/tenis/v2/metodologia` y `/tenis/v2/cartelera` siguen respondiendo el motor** (JSON, no HTML de página ni 404 de página).

## 3. Verificación en el dominio real (consultas únicas, por la caché de Cloudflare)
- `/tenis/` y una página de partido: 200, título, canonical, un solo `robots` (index), probabilidades, sello y JSON-LD en el HTML sin JavaScript.
- Partido con resultado: «ganó X por A-B en sets» y acierto/fallo solo si coinciden mercado y sets; sin cuotas inventadas.
- `/tenis/v2/…` sigue con `X-Robots-Tag: noindex` y las páginas sin él; `/nba/…` y `/futbol/…` sin cambios.
- En un navegador real (con `qf_ads=no` antes y borrado después): la app abre en Tenis con ese partido seleccionado y la URL se conserva; «Historial» y «atrás» funcionan.
- Sitemap con `/tenis/` y los partidos de la ventana (-3..+3 días); regresión de `/`, `/nba/`, `/futbol/`, `/historial/`, `/planes/`, `/app/v1/plans`, `/picks/free`, `/escalera`,
  `/parley`, `/robots.txt` en 200; 0 errores en el log de la API.

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_tenis_f32)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 4 archivos; borrar `tenis_datos.py`, `tenis_paginas.py` y las dos
plantillas del contenedor; `docker restart quantfut-api-1`. Las páginas `/tenis/…` pasan a 404; nada que deshacer en Caddy ni en la red.

## 5. Riesgos conocidos
- Si el feed de tenis caduca (más de 2 h sin exportarse) o falta el volumen, las páginas dan 503 con `Retry-After` (nunca 404) y el sitemap solo lleva el pilar.
- Resultados «en revisión»: hoy 2 de 113 partidos terminados del feed real (marcador 1-1 por sets, probable retirada). No se les muestra acierto ni fallo.
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores y la red `nba-api-red`).
