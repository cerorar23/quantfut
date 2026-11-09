# Despliegue de F2.3 (tarjetas para redes: `og:image`) — plan, 2026-11-09

Qué se despliega: una imagen 1200×630 para cada página (partidos de NBA, fútbol y tenis, sus pilares, la portada, las secciones y las páginas de
confianza), con `og:image`, `twitter:card=summary_large_image` y sus tamaños y texto alternativo. Se **dibujan bajo demanda** la primera vez que un
rastreador pide la imagen (`/og/…`) y se guardan en disco; la URL lleva el estado (`…-previa.jpg`, `…-final.jpg`) para que las redes no sirvan la
tarjeta vieja. Solo texto y formas, sin escudos ni logotipos. Detalle de diseño: `src/qf/api/og.py`.

## Cambio respecto a lo decidido el 8-nov (D3)
D3 proponía pre-generar las imágenes fuera del servidor. No es viable por partido (habría que dibujar cada una al sellar, en un proceso aparte con acceso a
tres fuentes de datos). Se dibuja dentro de la API, bajo demanda, con **Pillow instalado en el contenedor en marcha** (`pip`, la rueda `cp312 manylinux`
se descargó con éxito desde el contenedor el 9-nov). Sigue sin haber logotipos ni dependencia de terceros en tiempo de petición.

## Por qué el despliegue es reversible al instante
`og.disponible()` comprueba en cada petición si Pillow se puede importar. **Sin Pillow** las páginas no declaran `og:image` (siguen con `summary`, como hoy) y
`/og/…` responde 404. Por eso el orden es: (1) copiar el código y reiniciar, **sin cambios visibles**; (2) instalar Pillow, que **enciende** las tarjetas sin reiniciar;
(3) verificar. Vuelta atrás de lo visible: `pip uninstall -y pillow` (las páginas vuelven a `summary` al instante).

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F3.2 (`DEPLOYS.md`, 9-nov 03:19 UTC): comparar `sha256sum` en el contenedor con los blobs de `06ec91e7` para
   `src/qf/api/{seo.py, rutas_web.py, paginas.py, nba_paginas.py, futbol_paginas.py, tenis_paginas.py}` y `src/qf/api/paginas/base.html`. `main.py` de producción: sha256 `4f2df653…`.
3. `/health` 200; `docker exec quantfut-api-1 python -c "import PIL"` → `ModuleNotFoundError` (estado inicial); `docker exec quantfut-api-1 pip --version`.
4. Comprobar el directorio de tarjetas: `docker exec quantfut-api-1 sh -c 'mkdir -p /srv/quantfut/artifacts/og && touch /srv/quantfut/artifacts/og/.t && rm /srv/quantfut/artifacts/og/.t'`.
   Si no se puede escribir, la API usa `/tmp/qf_og` (se pierde al reiniciar, y las tarjetas se redibujan: funciona igual).
5. Respaldo en `~/respaldos/og_f23_<fecha>/` con `SHA256SUMS`: los 7 archivos anteriores + `main.py`.

## 2. Código (invisible)
1. `docker cp` de `og.py` (nuevo), `seo.py`, `rutas_web.py`, `paginas.py`, `nba_paginas.py`, `futbol_paginas.py`, `tenis_paginas.py` a `/app/src/qf/api/`; `fuentes/DejaVuSans-Bold.ttf` y
   `fuentes/LICENCIA-DejaVu.txt` (nuevos) a `/app/src/qf/api/fuentes/` (crear la carpeta); `base.html` a `/app/src/qf/api/paginas/`. Blobs de `origin/main` (LF), sha256 antes y después.
2. `main.py` de producción (CRLF): dos cambios con `\r` en `sed` — añadir `og` al `from . import …` y `app.include_router(og.router)` justo después de `app.include_router(tenis_paginas.router)`.
   Comprobar que el diff son solo esas 2 líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores. Comprobar que **nada cambió a la vista**: `og:image` ausente en `/nba/` y `/og/marca.jpg` → 404.

## 3. Encender las tarjetas
1. `docker exec quantfut-api-1 pip install --no-cache-dir pillow==11.3.0` (sin reiniciar). Comprobar `python -c "import PIL; print(PIL.__version__)"`.
2. Ensayo interno desde el VPS contra `127.0.0.1:8000` con `Host: pronosticosdeportivos.pro`: `/og/marca.jpg`, `/og/nba/pilar.jpg`, la tarjeta de un partido real de cada deporte (la URL sale del
   `og:image` de su página) → 200 `image/jpeg`, firma `FFD8FF`, 1200×630, < 150 KB; un estado que el partido no tiene → 404.

## 4. Verificación en el dominio real (consultas únicas por la caché de Cloudflare)
- Las páginas declaran `og:image`, `og:image:width/height/type/alt`, `twitter:card=summary_large_image` y `twitter:image`; cada URL de imagen responde 200 `image/jpeg` con `cache-control: public, max-age=31536000, immutable`
  y `X-Robots-Tag: noindex`; la segunda petición sale de la caché de Cloudflare (`cf-cache-status: HIT`).
- **Rastreadores contra Cloudflare** (`curl -A`): `facebookexternalhit/1.1`, `Twitterbot`, `TelegramBot (like TwitterBot)`, `WhatsApp/2`, `LinkedInBot/1.0`, `Discordbot/2.0` piden la página y su imagen → 200 (Bot Fight Mode o WAF no deben bloquearlos).
- Una tarjeta de cada deporte abierta y revisada a ojo (texto legible, sin desbordes, estado correcto; el fallo se anuncia igual que el acierto).
- Regresión: `/`, `/nba/`, `/futbol/`, `/tenis/`, `/historial/`, `/planes/`, `/metodologia/`, `/app/v1/plans`, `/picks/free`, `/escalera`, `/parley`, `/robots.txt`, `/sitemap.xml` en 200; 0 errores en el log; CPU y memoria de la API sin cambios apreciables.
- **Lo que solo puede hacer el titular** (necesita sesión): Facebook Sharing Debugger («Scrape Again» con una URL de partido y con la portada), `@WebpageBot` en Telegram, LinkedIn Post Inspector y redactar un post de X con el enlace. La documentación y los pasos están en `docs/plan_seo_redes_web_20261108.md` §6.

## 5. Vuelta atrás
- **Visible, al instante:** `docker exec quantfut-api-1 pip uninstall -y pillow` → las páginas vuelven a `summary` y `/og/…` a 404.
- **Código:** `R=$(cat ~/respaldos/.ultimo_og_f23)`; `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 7 archivos + `main.py`; borrar `og.py` y `fuentes/` del contenedor; `docker restart quantfut-api-1`;
  opcional: `rm -rf /srv/quantfut/artifacts/og`.

## 6. Riesgos conocidos
- El paquete de Pillow instalado con `pip` y los archivos copiados **se pierden si alguien recrea el contenedor** (igual que los anteriores): las páginas siguen funcionando sin tarjeta. `requirements.txt` ya lleva `pillow==11.3.0`, así que una imagen reconstruida desde `main` lo incluye.
- Carga: cada tarjeta nueva cuesta unos 50 ms de CPU una sola vez y ~60–80 KB en disco; se borran las de más de 30 días. Un rastreador que recorra miles de partidos solo genera las de partidos con página.
- Las tarjetas del estado «previa» muestran las probabilidades selladas, que no cambian; la de «final» sale cuando el resultado está confirmado. Si Facebook ya cacheó una URL de «previa», la página apunta a la de «final» y no hace falta forzar nada.
- Falta decidir los nombres de usuario de X, Instagram, Telegram y Facebook (`twitter:site`, `sameAs`): no se declara ninguno hasta que existan.
