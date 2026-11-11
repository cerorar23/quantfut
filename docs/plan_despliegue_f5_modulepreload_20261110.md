# F5 / §7 / F8 — Cierre técnico seguro (`modulepreload`, `contactPoint` JSON-LD y verificador público `/chain`), 2026-11-10

## Qué incluye este paquete (código listo, sin desplegar)
1. **F5 Core Web Vitals (`frontend/index.html` + `frontend/rutas.test.mjs`):**
   - Añade `<link rel="modulepreload" href="./...">` para los 15 módulos ES estáticos alcanzables desde `app.js` (los 10 directos de `app.js` y sus 5 transitivos locales: `ergonomic-views.js`, `historial-views.js`, `google-auth.js`, `meta-pixel.js`, `whop-checkout.js`), con el parámetro `?v=...` exacto que importa la aplicación para evitar descargas duplicadas y evitar el efecto cascada en arranque frío.
   - `src/qf/api/rutas_web.py` (`_RELATIVOS`) y `frontend/server.mjs` ya reescriben `href="./` a `href="/` en rutas anidadas (`/historial/`, `/nba/...`, `/futbol/...`, `/tenis/...`), de modo que los `modulepreload` resuelven correctamente tanto en raíz como en subrutas.
   - No se modifica ninguna hoja CSS ni el orden de carga (`frontend/original-css.test.mjs` intacto).
   - Prueba automática en `frontend/rutas.test.mjs` que recorre el grafo estático desde `app.js` y falla si alguna versión `?v=` o un `import` estático nuevo deja de coincidir 1:1 con `frontend/index.html`.
   - `tests/test_rutas_web.py` comprueba además que todas las secciones HTML reciben los `modulepreload` con ruta absoluta `/` sin `./` residual y que cada archivo JS responde `200`.

2. **§7 Datos estructurados (`src/qf/api/rutas_web.py` + `tests/test_rutas_web.py`):**
   - Completa el bloque `Organization` del JSON-LD de portada añadiendo `"contactPoint"` (`@type: ContactPoint`, `contactType: "customer support"`, `email: "admin@pronosticosdeportivos.pro"`).
   - No se inventa `sameAs` (sigue pendiente de que el titular facilite los usuarios reales de redes) ni se añade `logo` mientras no exista icono cuadrado específico.

3. **F8 Herramienta pública sin dependencias (`scripts/verificar_cadena_publica.py` + `tests/test_f8_cadena_publica.py`):**
   - Script de Python 3 usando exclusivamente biblioteca estándar (`hashlib`, `json`, `urllib.request`, `argparse`, `pathlib`) para que cualquier tercero verifique la integridad de la cadena SHA-256 sin instalar dependencias del proyecto ni acceder a PostgreSQL.
   - Modos soportados:
     - `--url` (por defecto `https://pronosticosdeportivos.pro/chain?limit=365`) y `--archivo`: verifica el enlace `prev_sha256` consecutivo y `sha256(prev_sha256 + payload_sha256) == chain_sha256` idéntico a `src/qf/publish/hashchain.py`.
     - `--dir`: verifica un directorio local de recibos `*.receipt.json` y archivos `.json` revelados (diarios, `partido/` y `escalera/`), contando los pendientes de revelar por compromiso y detectando contenido alterado, enlaces rotos o `.json` sin recibo.
     - `--desde-genesis` y `--json` para auditoría automatizada o CI.

## Lo que NO se toca todavía (por calendario o dependencia externa)
- **Paso de `csp.py` de `Content-Security-Policy-Report-Only` a `Content-Security-Policy` coercitiva:** `docs/plan_despliegue_csp_f5_20261109.md` exige al menos 7 días completos de informes reales en producción desde el despliegue del 9-nov-2026 (~**16-nov-2026**) antes de bloquear scripts/recursos en `frontend/index.html` y evitar regresiones en Google Sign-In o Whop Checkout.
- **Regla de caché de Cloudflare** (cachear GET públicos `/nba/`, `/futbol/`, `/tenis/`, excluyendo `/nba/v1/...`, `/tenis/v2/...`, `/cuenta*`, `/auth*`, `/admin*`): acción de panel en Cloudflare por el titular.
- **Métricas Web Vitals post-despliegue e Inspección de URLs en Search Console:** medir después de desplegar los cambios en producción.

## Despliegue (cuando se apruebe)
1. Pre-vuelo: `sha256` de `frontend/index.html`, `src/qf/api/rutas_web.py` y `scripts/verificar_cadena_publica.py`; respaldo con `SHA256SUMS`.
2. Desplegar los archivos modificados en el contenedor (`quantfut-api-1`) y reiniciar fuera de `:11` y `:41`.
3. Comprobar tras el reinicio:
   - `GET /` y `GET /futbol/` contienen los 15 `<link rel="modulepreload" href="/...js?v=...">` sin `./` y `contactPoint` en el JSON-LD de `/`.
   - `python3 scripts/verificar_cadena_publica.py --url https://pronosticosdeportivos.pro/chain?limit=365` devuelve código `0` y `OK`.

## Vuelta atrás
Restaurar `frontend/index.html` y `src/qf/api/rutas_web.py` desde la copia de seguridad y reiniciar `quantfut-api-1`. `scripts/verificar_cadena_publica.py` es un utilitario independiente y no afecta al runtime web.
