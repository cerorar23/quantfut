# Despliegue de F2.4 (IndexNow para Bing) — plan, 2026-11-09

Qué se despliega: la ruta `/<clave>.txt` (prueba de que el sitio es nuestro) y un comando que avisa a IndexNow de las URLs nuevas o cambiadas del sitemap
(`python -m qf.api.indexnow`). **Google no usa IndexNow**: esto es para Bing y los buscadores que participan (Yandex, Seznam, Naver…). Google se sigue
alimentando con el sitemap y Search Console. Diseño y reglas de «qué cambió» en `src/qf/api/indexnow.py`.

## Tres escalones, cada uno con su permiso
1. **Código y clave (sin contacto con terceros):** copiar `indexnow.py`, parchear `main.py`, instalar la clave y comprobar que `https://pronosticosdeportivos.pro/<clave>.txt` la sirve.
2. **Primer envío (contacta con un tercero):** manda las URLs públicas del sitemap (~154 la primera vez) a `https://api.indexnow.org/IndexNow`. Es información pública y no lleva datos
   de personas, pero es una publicación hacia fuera: **se hace solo con el visto bueno expreso del titular**, tras ver la simulación.
3. **Cron en el host (automatización permanente):** `*/30 * * * *`. También **solo con el visto bueno expreso del titular**.

Sin el escalón 2 y 3 el sitio queda exactamente igual que hoy, salvo un archivo `.txt` con una clave que no usa nadie.

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F2.3 (`DEPLOYS.md`, 9-nov 03:59 UTC): comparar `sha256sum` en el contenedor con los blobs de `c669d309` para `src/qf/api/{og.py, tenis_paginas.py}`.
   `main.py` de producción: sha256 `d147b701…`.
3. `/health` 200; `docker exec quantfut-api-1 ls /srv/quantfut/artifacts` (el directorio de `indexnow` no existe todavía).
4. Respaldo en `~/respaldos/indexnow_f24_<fecha>/` con `SHA256SUMS`: `og.py`, `tenis_paginas.py`, `main.py`, y la salida de `crontab -l` (solo para el escalón 3).

## 2. Código y clave
1. `docker cp` de `indexnow.py` (nuevo), `og.py` y `tenis_paginas.py` a `/app/src/qf/api/` (blobs de `origin/main`, LF, sha256 antes y después).
2. `main.py` de producción (CRLF): dos cambios con `\r` en `sed` — añadir `indexnow` al `from . import …` y `app.include_router(indexnow.router)` **al final** de los `include_router` de las páginas, justo después de `app.include_router(og.router)`.
   Comprobar que el diff son solo esas 2 líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. Clave: `docker exec quantfut-api-1 sh -c 'mkdir -p /srv/quantfut/artifacts/indexnow && python -c "import secrets; print(secrets.token_hex(16))" > /srv/quantfut/artifacts/indexnow/clave.txt'` y leerla.
4. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores.
5. Comprobar en el dominio real (consulta única): `GET /<clave>.txt` → 200 `text/plain` con exactamente la clave y `X-Robots-Tag: noindex`; `GET /otra.txt` → 404; `/robots.txt` y `/sitemap.xml` sin cambios; regresión de las rutas habituales en 200.

## 3. Simulación (todavía sin contacto con nadie)
`docker exec quantfut-api-1 python -m qf.api.indexnow` (sin `--enviar`): imprime cuántas URLs enviaría y una muestra; no envía ni escribe nada. Esperado la primera vez: todas las del sitemap pendientes.

## 4. Primer envío (con permiso expreso del titular)
`docker exec quantfut-api-1 python -m qf.api.indexnow --enviar` → `lotes: [200]` o `[202]`, `fallidas: 0`. Si responde 403, la clave no es alcanzable desde fuera (revisar el paso 2.5); 422, alguna URL no es del dominio;
429, demasiadas peticiones (reintenta solo en el siguiente pase). El pase siguiente, sin cambios en el sitemap, envía 0 URLs (se comprueba ejecutándolo otra vez).

## 5. Cron (con permiso expreso del titular)
Respaldar y **añadir** (no reemplazar) una línea al `crontab` del usuario `qf`:
`(crontab -l; echo '*/30 * * * * docker exec quantfut-api-1 python -m qf.api.indexnow --enviar >> /home/qf/indexnow.log 2>&1') | crontab -`.
Vigilar el primer día `~/indexnow.log`: pocas URLs por pase (los partidos nuevos y los que acaban de terminar, más cada pilar una vez cada 6 h).

## 6. Vuelta atrás
- **Cron:** `crontab -l | grep -v qf.api.indexnow | crontab -` (o restaurar el respaldo). **Clave:** borrar `/srv/quantfut/artifacts/indexnow/clave.txt` → la ruta responde 404 y el comando no envía nada.
- **Código:** restaurar `og.py`, `tenis_paginas.py` y `main.py` del respaldo, borrar `indexnow.py` del contenedor y `docker restart quantfut-api-1`. Lo ya enviado no se puede retirar; IndexNow solo recibe URLs públicas que ya están en el sitemap.

## 7. Riesgos conocidos
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores): el cron fallaría con `No module named qf.api.indexnow` hasta volver a desplegar; la clave y el estado viven en el volumen y sobreviven.
- IndexNow desaconseja reenviar URLs sin cambios: el estado (`estado.json`) lo evita y los pilares solo se reenvían cada 6 horas. Un fallo no se da por hecho y se reintenta; un 429 detiene el pase.
- No mide nada: para saber si Bing las indexa hay que mirar Bing Webmaster Tools (el titular puede dar de alta el sitio con la misma clave); no se promete tiempo de indexación.
