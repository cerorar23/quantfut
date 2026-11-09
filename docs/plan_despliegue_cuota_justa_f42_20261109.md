# Despliegue de F4.2 (`/calculadora-cuota-justa/`) — plan, 2026-11-09

## Qué se despliega
Una herramienta educativa: convierte cuota ↔ probabilidad (decimal, fraccionaria, americana) y quita el margen de la casa de un mercado de 2 o 3 resultados (Shin, proporcional, potencia). **No calcula importes ni «valor»** (plan §2, fila 14).
Todo ocurre en el navegador: no se envía ni se guarda nada. Sin JavaScript se ve un ejemplo resuelto calculado por el servidor.

Es la primera página pública con **JavaScript propio**. Su política de seguridad es la estricta de las páginas de confianza más `script-src 'self'`: sin scripts en línea, sin `unsafe-eval`, sin `connect-src`, sin Pixel de Meta.

Archivos: `src/qf/api/cuota_justa.py` (nuevo), `src/qf/api/paginas/cuota_justa.html` (nuevo), `src/qf/api/static/cuota-justa.js` (nuevo), y modificados `src/qf/api/{seo.py, rutas_web.py}`, `src/qf/api/paginas/{base.html, metodologia.html}`.
`main.py` de producción: **2 líneas** (`cuota_justa` en el `from . import …` y `app.include_router(cuota_justa.router)` justo después de `app.include_router(calibracion.router)`).

## Pruebas hechas
- Python (46): vectores compartidos al día, coincidencia con `qf.model.devig` (proporcional, Shin, potencia) a 1e-7, cuotas inválidas, CSP, un único script propio con hash, ejemplo del servidor = cálculo, etiquetas, sitemap, redirección.
- Node (66, en `npm run check`): los mismos vectores contra el JS, análisis de los tres formatos, formateo, ida y vuelta.
- Navegador (copia local): la tabla que repinta el JS es idéntica a la del servidor; cambio de cuotas, dato inválido (`aria-invalid`), 2 resultados, cambio de formato, probabilidad fuera de rango, método proporcional; consola vacía (sin avisos de CSP); sin desborde horizontal a 390 px.
- Regresión de páginas SEO (351 pruebas) y `npm run check` (231) en verde.

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben (`seo.py`, `rutas_web.py`, `base.html`, `metodologia.html`) siguen iguales por sha256 a los de `02af47a4`; `main.py` de producción: sha256 `0f009b92…`.
3. `/health` 200; `/static/panel.js` responde 200 (la ruta `/static` está montada y Caddy la manda a `api`).
4. Respaldo en `~/respaldos/cuota_f42_<fecha>/` con `SHA256SUMS`: los 4 archivos modificados + `main.py`.

## 2. Copia y reinicio
1. `docker cp` de `cuota_justa.py`, `seo.py`, `rutas_web.py` a `/app/src/qf/api/`; `paginas/{cuota_justa.html,base.html,metodologia.html}` a `/app/src/qf/api/paginas/`; `static/cuota-justa.js` a `/app/src/qf/api/static/`. Blobs de `origin/main` (LF), sha256 antes y después.
2. `main.py` (CRLF): dos cambios con `\r` en `sed`; solo esas 2 líneas; sintaxis con `ast.parse`.
3. **No reiniciar en los minutos :11 y :41 de la hora del servidor** (cron de IndexNow). `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores. Calentar `/sitemap-paginas.xml` y la página.

## 3. Verificación en el dominio real (URL con consulta única por la caché de Cloudflare)
- `/calculadora-cuota-justa/`: 200, `Content-Security-Policy` con `script-src 'self'`, canonical, `robots` = index, un solo `<script type="module">` propio con `?v=<hash>`.
- `/static/cuota-justa.js?v=…` 200 con tipo JavaScript, **mismo sha256 que el blob de `main`** (es lo que comprobarán los navegadores).
- En un navegador real contra el dominio (con `qf_ads=no`): consola sin errores ni avisos de CSP; la tabla del JS idéntica a la del servidor; cambiar una cuota actualiza la tabla.
- Sitemap con la URL nueva y `lastmod` 2026-11-09; `/metodologia/`, `/calibracion/` y `/` enlazan a la herramienta; regresión de rutas en 200; 0 errores en el log; el cron de IndexNow envía la URL nueva (`enviadas: 1`).
- `/csp-report`: a los pocos minutos, sin informes nuevos de esta ruta.

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_cuota_f42)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 4 archivos modificados y `main.py`; borrar `cuota_justa.py`, `cuota_justa.html` y `static/cuota-justa.js` del contenedor; `docker restart quantfut-api-1` (fuera de :11 y :41). La página pasa a 404.

## 5. Riesgos conocidos
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores).
- Cloudflare guarda los `.js` por URL completa: la URL lleva el hash del contenido, así que una versión nueva se pide sola.
- Al cambiar de formato, las cuotas escritas se redondean (la página lo avisa): −111 ↔ 1,90 no son exactamente iguales.
- Primer JavaScript propio en una página pública: si el navegador lo bloqueara por una política mal escrita, la página sigue mostrando el ejemplo resuelto (por eso se verifica en el dominio real, no solo en local).
