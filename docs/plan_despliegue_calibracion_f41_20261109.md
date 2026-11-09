# Despliegue de F4.1 (`/calibracion/`) — plan, 2026-11-09

## Qué se despliega
Una página de transparencia, `/calibracion/`, **generada automáticamente** con las mediciones que la web ya publica (`/calibration` de fútbol, desde `calibration_runs`, y `/nba/v1/calibracion` de NBA):
gráfico de fiabilidad en SVG (sin JavaScript, con los mismos números en tabla), comparación del modelo con el mercado y el estado de la evidencia. **Ninguna cifra se escribe a mano** y la frase «el modelo no supera al
mercado» se calcula con los datos (si algún día el modelo gana, la página lo dirá). Una prueba automática comprueba que **todas las cifras del texto salen de los datos** (criterio de terminado de F4) y que esa
comprobación detecta una cifra inventada. Lleva aviso visible de que se genera automáticamente (plan §8). Va en la navegación de las páginas de confianza y en el HTML inicial de la app, y en el sitemap con `lastmod` = fecha de la última medición.

Solo servidor, sin frontend, red ni Caddy. Archivos: `src/qf/api/{calibracion.py (nuevo), nba_datos.py, seo.py, rutas_web.py}`, `src/qf/api/paginas/{calibracion.html (nuevo), base.html}`.
`main.py` de producción: **2 líneas** (`calibracion` en el `from . import …` y `app.include_router(calibracion.router)` justo después de `app.include_router(nba_equipos.router)`).

## Lo que muestra con los datos reales de hoy (9-nov)
- **Fútbol** (3.222 partidos, 9-nov-2025 a 9-nov-2026): RPS del modelo 0,2091 frente a 0,2009 del mercado → **el modelo no supera al mercado**; 9 de 10 tramos de fiabilidad dentro de 2 errores estándar.
- **NBA, temporada 2025-26 medida hacia adelante** (1.269 partidos): Brier 0,2063 frente a 0,1981 del mercado → el modelo no supera al mercado; pendiente de calibración 1,070.
- **NBA desde el sellado:** 17 partidos con resultado, evidencia «descriptiva», calibración **no certificada** («todavía son pocos partidos para sacar conclusiones»).
Es la página más franca de la web: dice abiertamente que el modelo no vence al mercado. Está en línea con la página de metodología, que ya lo reconoce.

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F3.3/F2.2 (`DEPLOYS.md`, 9-nov 14:11 UTC): comparar `sha256sum` en el contenedor con los blobs de `32175c00` para `src/qf/api/{nba_datos.py, seo.py, rutas_web.py}` y
   `src/qf/api/paginas/base.html`. `main.py` de producción: sha256 `42cb0b6a…`.
3. `/health` 200; `GET /calibration` y `GET /nba/v1/calibracion` responden 200 (de ahí salen los datos).
4. Respaldo en `~/respaldos/calib_f41_<fecha>/` con `SHA256SUMS`: los 4 archivos anteriores + `main.py`.

## 2. Copia y reinicio
1. `docker cp` de `calibracion.py` (nuevo), `nba_datos.py`, `seo.py`, `rutas_web.py` a `/app/src/qf/api/`; `paginas/calibracion.html` (nuevo) y `base.html` a `/app/src/qf/api/paginas/`. Blobs de `origin/main` (LF), sha256 antes y después.
2. `main.py` (CRLF): dos cambios con `\r` en `sed`; comprobar que el diff son solo esas 2 líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. **No reiniciar en los minutos :11 y :41 de la hora del servidor** (el cron de IndexNow). `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores. Calentar pidiendo `/sitemap-paginas.xml` y `/calibracion/`.

## 3. Verificación en el dominio real (consultas únicas por la caché de Cloudflare)
- `/calibracion/`: 200, título, canonical, `robots` = index, aviso «Página generada automáticamente», las cifras de arriba, 2 gráficos SVG con `role="img"`, `<title>` y `<desc>`, y las tablas; `Content-Security-Policy` estricta de las páginas de confianza.
- **Las cifras de la página = las de `/calibration` y `/nba/v1/calibracion` servidas en ese momento** (comprobar a mano 3 o 4: n de partidos, RPS del modelo y del mercado, Brier).
- `/calibracion` → 301; el sitemap incluye `/calibracion/` con `lastmod` = fecha de la última medición; la navegación de `/metodologia/` y el HTML de `/` enlazan a `/calibracion/`.
- Regresión de las rutas habituales en 200; 0 errores en el log; el cron de IndexNow envía la URL nueva en su siguiente pase (`enviadas: 1`).
- En un navegador real: el gráfico se ve entero (sin desbordes) y los puntos y barras coinciden con la tabla.

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_calib_f41)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 4 archivos y `main.py`; borrar `calibracion.py` y `calibracion.html` del contenedor; `docker restart quantfut-api-1`. La página pasa a 404.

## 5. Riesgos conocidos
- Si la base de fútbol cae, la página sale solo con NBA; si cae también `nba-api`, 503 con `Retry-After` (nunca 404). Los datos se cachean 5-10 min.
- Es una página que muestra con claridad que el modelo no supera al mercado: es una decisión de transparencia coherente con la metodología, pero conviene que el titular la lea antes de promocionarla.
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores).

## 6. Lo que queda de F4
La calculadora de cuota justa (una herramienta interactiva: exige JavaScript propio y una política de seguridad que lo permita) queda como F4.2. El texto desde datos de los partidos y el enlazado interno ya existen (F2.1, F3.1, F3.2, F2.2 y F3.3).
