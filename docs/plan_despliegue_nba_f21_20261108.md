# Despliegue de F2.1 (páginas NBA) — plan, 2026-11-08

Qué se despliega: `/nba/` y `/nba/<local>-vs-<visitante>-<AAAA-MM-DD>/` (PR de la rama `seo/f2-1-nba-paginas`). **Las páginas se sirven dentro de la propia app** (mismo shell de la SPA que las secciones de F1.2b): el HTML inicial lleva el texto para Google y las redes, y la persona ve la app, que arranca en ese partido. Por eso hay también cambio de frontend.
Método: el mismo que el despliegue SEO del 8-nov (`docs/plan_despliegue_seo_20261108.md`): `docker cp` + `docker restart` sobre
`quantfut-api-1`. **No recrear el contenedor, no `docker commit`, no `scripts/deploy.sh construir api`** (ver DEPLOYS.md).
Solo despliega una sesión a la vez y se compara lo desplegado con `main` antes de sobrescribir.

## 0. Por qué hay dos cambios de infraestructura
- La API no resuelve `nba-api` (comprobado el 8-nov: `Temporary failure in name resolution`; Caddy sí). Hay que conectarla a `nba-api-red`.
- Caddy redirige hoy `/nba` y `/nba/*` con 302 a `/nba/v2/`. Para que las páginas lleguen a la API hay que quitar ese redireccionamiento. **Se hace al final**: hasta entonces la API ya tiene el código, pero nadie lo ve.

## 1. Pre-vuelo (solo lectura)
1. `main` contiene el PR; `git rev-parse origin/main`.
2. Los archivos que se tocan en el contenedor siguen siendo los de la entrada anterior de DEPLOYS.md (`seo.py`, `rutas_web.py`, `paginas/base.html` y `main.py` de producción): compara su `sha256sum` con el de `main` en el commit del despliegue SEO (`10188cd2`) más los cambios de este PR. Si otra sesión los cambió, parar.
3. `docker ps` sano; `docker exec quantfut-api-1 getent hosts nba-api` → sin resolución (estado inicial).
4. Respaldo de lo que se va a sobrescribir en `~/respaldos/nba_f21_<fecha>/` con `SHA256SUMS`: `seo.py`, `rutas_web.py`, `main.py`, `paginas/base.html`, `index.html`, `app.js`, `rutas.js`, `sports-window.js` y el `Caddyfile`.

## 2. API (el sitio sigue igual porque Caddy aún redirige)
1. `docker network connect nba-api-red quantfut-api-1` (en caliente, reversible con `docker network disconnect`). Comprobar:
   `docker exec quantfut-api-1 python -c "import urllib.request as u; print(u.urlopen('http://nba-api:8000/nba/v1/cartelera?fecha=<hoy>', timeout=4).status)"` → 200.
2. `docker cp` de: `nba_datos.py`, `nba_paginas.py`, `seo.py`, `rutas_web.py` a `/app/src/qf/api/`; `paginas/base.html`, `paginas/nba_cartelera.html`, `paginas/nba_partido.html` a `/app/src/qf/api/paginas/`.
   Frontend (mismas rutas de destino que en el despliegue del 8-nov, ver DEPLOYS.md): `index.html`, `app.js`, `rutas.js`, `sports-window.js`. Cambian tres versiones `?v=` a `nba-20261108` (`app.js` en `index.html`; `rutas.js` y `sports-window.js` en `app.js`) para saltar la caché de Cloudflare. Se copian ANTES de abrir Caddy (§3): hasta entonces nadie entra por `/nba/…`, y las secciones de siempre siguen igual (el HTML nuevo solo cambia la versión de `app.js`).
3. `main.py` de producción (difiere de `main`): dos cambios, nada más.
   - línea `from . import mensajes, paginas, rutas_web, seo` → `from . import mensajes, nba_paginas, paginas, rutas_web, seo`
   - tras `app.include_router(paginas.router)` añadir `app.include_router(nba_paginas.router)`
   Se aplica con `sed` sobre una copia y `python -m py_compile` antes de copiarla; dejar el diff en el respaldo.
4. `docker restart quantfut-api-1`; esperar `health` 200; log sin errores.
5. Ensayo sin tocar a nadie, saltándose Caddy desde dentro: `docker exec quantfut-api-1 python -c` pidiendo `/nba/` y una página de partido real al propio uvicorn en `127.0.0.1:8000` con `Host: pronosticosdeportivos.pro` y `Accept: text/html`. Esperado: 200, `<title>` con los equipos, probabilidades en el HTML.

## 3. Caddy (el paso que lo hace visible)
1. En `~/quantfut/Caddyfile`: quitar el `handle @nba { redir * /nba/v2/ 302 }` y su `@nba path /nba /nba/*`; añadir dentro de `handle @nba_v2` la línea `header X-Robots-Tag noindex`.
2. `docker exec quantfut-caddy-1 caddy validate --config /etc/caddy/Caddyfile` → «Valid configuration»; después `caddy reload`. Se hace con el respaldo del `Caddyfile` ya guardado.
3. Alinear el `Caddyfile` del repo con el de producción en un PR aparte (como #291).

## 4. Verificación en el dominio real
Con consultas únicas (`?v=chequeo$(date +%s)`), por la trampa de la caché de Cloudflare:
- `/nba/` 200 con enlaces `<a href="/nba/…">`; una página de partido 200 con el título, las probabilidades y el hash en el HTML (`curl`, sin JavaScript).
- En un navegador real: abrir una página de partido → la app aparece en NBA con ese partido seleccionado, la barra de direcciones conserva `/nba/…`, «Historial» lleva a `/historial/` y «atrás» vuelve al partido. Comprobar los hashes de `app.js`, `rutas.js` y `sports-window.js` servidos con consulta única.
- `/nba/v2/` y `/nba/v1/cartelera?fecha=…` siguen 200 y ahora llevan `X-Robots-Tag: noindex`.
- `/nba/inexistente/` → 404 HTML con `noindex`; `/nba` → 301 a `/nba/`.
- `/sitemap-paginas.xml` incluye `/nba/` y los partidos con sello; `/robots.txt`, `/`, `/historial/`, `/planes/`, `/app/v1/plans` siguen 200.
- Log de la API sin errores; con `nba-api` parado un momento (no se hace en producción) las pruebas ya cubren el 503.
- Facebook Sharing Debugger / `@WebpageBot`: la tarjeta saldrá sin imagen hasta F2.3; es esperado.

## 5. Vuelta atrás
- Visibilidad: restaurar el `Caddyfile` del respaldo y `caddy reload` (vuelve el 302 y las páginas dejan de verse al instante).
- Código: restaurar los 4 archivos de la API y los 4 del frontend del respaldo con `docker cp`, borrar `nba_datos.py`, `nba_paginas.py` y las dos plantillas, `docker restart quantfut-api-1`. Respaldar también `index.html`, `app.js`, `rutas.js` y `sports-window.js` en el paso 1.4.
- Red: `docker network disconnect nba-api-red quantfut-api-1`.

## 6. Riesgos conocidos
- `docker network connect` y los archivos copiados **se pierden si alguien recrea el contenedor** (igual que los 8 archivos anteriores). Anotarlo en DEPLOYS.md.
- El sello llega ~60 min antes del inicio, así que cada página de partido existe desde entonces: casi todo el rastreo será posterior al partido. No se cambia el pipeline por esto.
- Si `nba-api` se cae, las páginas dan 503 con `Retry-After` (no 404) y se sirve la copia guardada mientras exista.
