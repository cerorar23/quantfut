# Despliegue de F3.0 + F3.1 (páginas de fútbol dentro de la app) — plan, 2026-11-09

Qué se despliega: `/futbol/` y `/futbol/<competición>/<local>-vs-<visitante>-<AAAA-MM-DD>/`, dentro del shell de la SPA (igual que
NBA en F2.1), más el arranque por URL generalizado de F3.0 (`deporteBoot`) y la corrección de la ventana de fútbol que ya no
borra el partido pedido mientras carga la agenda. **No hay cambio de red ni de Caddy**: el fútbol se sirve desde la propia API
(`/futbol/…` cae en el `reverse_proxy api:8000` por defecto) y lee la base directamente. Método: el mismo de F2.1
(`docs/plan_despliegue_nba_f21_20261108.md`): `docker cp` + `docker restart quantfut-api-1`. **No recrear el contenedor, no
`docker commit`, no `scripts/deploy.sh construir api`.** Solo despliega una sesión a la vez y `main` debe contener el PR.

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene F3.0 y F3.1; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F2.1 (`DEPLOYS.md`, 9-nov 01:26 UTC): comparar `sha256sum` en el contenedor con los
   blobs de `e3bbc31e` (F2.1) para `src/qf/api/{seo.py, rutas_web.py, nba_paginas.py}`, `src/qf/api/paginas/base.html`,
   `frontend/{index.html, app.js, rutas.js}`. Si cambió alguno, parar. `main.py` de producción: sha256 `6db68440…` (tras F2.1).
3. `/health` 200; `docker exec quantfut-api-1 python -c "from qf.api import mobile; print(mobile.features().get('estadisticas'))"` → habilitada
   (si estuviera apagada, las páginas darían 404 a propósito).
4. Respaldo en `~/respaldos/futbol_f31_<fecha>/` con `SHA256SUMS`: los 8 archivos anteriores + `main.py`.

## 2. Copia y reinicio
1. `docker cp` de: `futbol_datos.py`, `futbol_paginas.py` (nuevos), `nba_paginas.py`, `seo.py`, `rutas_web.py` a `/app/src/qf/api/`;
   `paginas/{futbol_cartelera.html, futbol_partido.html}` (nuevos) y `base.html` a `/app/src/qf/api/paginas/`; `index.html`, `app.js`,
   `rutas.js` a `/app/frontend/`. Los archivos salen de blobs de `origin/main` (LF) y se comparan por sha256 antes y después.
2. `main.py` de producción (CRLF): dos cambios con `\r` en `sed` — `from . import futbol_paginas, mensajes, nba_paginas, paginas, rutas_web, seo` y
   `app.include_router(futbol_paginas.router)` tras el de `nba_paginas`. Comprobar el diff (solo esas 2 líneas) y la sintaxis con `ast.parse`
   (sin `py_compile`: deja `.pyc` en el contenedor).
3. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores.
4. Ensayo interno desde el VPS contra `127.0.0.1:8000` con `Host: pronosticosdeportivos.pro` y `Accept: text/html`: `/futbol/`, una página de partido
   real (la primera del pilar), un 404, `/futbol` → 301 y el sitemap.

## 3. Verificación en el dominio real (consultas únicas, por la caché de Cloudflare)
- `/futbol/` y una página de partido: 200, título, canonical, un solo `robots` (index), 1X2, marcador si lo hay y JSON-LD en el HTML sin JavaScript;
  partido sin pronóstico o competición equivocada → 404 HTML con `noindex`.
- **Sin VIP:** el HTML no contiene «cuota», mercados ni picks (la prueba automática ya lo exige; comprobarlo también a mano con `curl`).
- En un navegador real (con `qf_ads=no` puesto antes): la app abre en Fútbol con ese partido seleccionado y la URL se conserva; el día y la liga
  son los del partido; «Historial» y «atrás» funcionan.
- Sitemap con `/futbol/` y los partidos con pronóstico; hashes de `app.js`, `rutas.js`, `index.html` servidos = `main`; regresión
  (`/`, `/nba/`, `/historial/`, `/planes/`, `/app/v1/plans`, `/picks/free`, `/escalera`, `/parley`, `/robots.txt`) en 200; `/nba/…` sigue igual.

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_futbol_f31)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 8 archivos + `main.py`; borrar
`futbol_datos.py`, `futbol_paginas.py` y las dos plantillas del contenedor; `docker restart quantfut-api-1`. Las páginas `/futbol/…` pasan a 404 al
instante; no hay nada en Caddy ni en la red que deshacer.

## 5. Riesgos conocidos
- Carga: el pilar hace 5 consultas de agenda y 5 de pronósticos (caché de 120 s en memoria); una página de partido, 2–3. Vigilar el log y la CPU de la
  base la primera hora.
- Si la base cae, las páginas dan 503 con `Retry-After` (nunca 404). Si `estadisticas` se apaga en `/control/configuracion-app`, dan 404 a propósito.
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los 8 anteriores y la red `nba-api-red`).
