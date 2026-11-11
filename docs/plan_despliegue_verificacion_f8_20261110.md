# F8 / §2 — Página pública `/verificacion/` (`/en/verification/`, `/pt/verificacao/`) — plan, 2026-11-10

## Qué incluye
1. **Rutas públicas indexables (`src/qf/api/verificacion.py`):**
   - `/verificacion/` (`es`, abierta), `/en/verification/` (`en`, detrás de `idiomas.puerta("en")`), `/pt/verificacao/` (`pt`, detrás de `idiomas.puerta("pt")`), con redirecciones `301` desde las rutas sin barra final y entrada condicional + `hreflang` recíproco en `/sitemap-paginas.xml` (`src/qf/api/seo.py`).
   - CSP estricta propia: `default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'` (sin scripts en línea ni conexiones de terceros; solo consulta `/chain` del mismo origen).
   - Verificación desde servidor sobre los últimos lotes reales de `prediction_batches` (sin fabricar hashes ni cifras si no hay conexión o la tabla está vacía).
2. **Auditoría en navegador (`src/qf/api/static/verificar-cadena.js`):**
   - Módulo ES sin dependencias que consulta `/chain?limit=365` (o lee JSON pegado / archivo local) y recalcula `sha256(prev_sha256 + payload_sha256) == chain_sha256` mediante Web Crypto (`crypto.subtle`) en el navegador del visitante.
3. **Plantillas y enlaces internos:**
   - Nuevas: `paginas/verificacion.html`, `paginas/en_verificacion.html`, `paginas/pt_verificacao.html`.
   - Navegación y cruce: `base.html`, `base_en.html`, `base_pt.html`, `metodologia.html`, `en_methodology.html`, `pt_metodologia.html` enlazan al verificador conservando intacta la declaración de que aún no existe registro externo independiente de terceros.
   - Pruebas: `tests/test_verificacion.py` y `frontend/verificar-cadena.test.mjs` (en `frontend/package.json` `npm run check`).

## Despliegue (cuando se apruebe)
1. Pre-vuelo: `sha256` de `main.py`, `seo.py`, `base*.html` y `metodologia*.html` en el contenedor; respaldo con `SHA256SUMS`.
2. Copiar `verificacion.py`, `seo.py`, `static/verificar-cadena.js`, las plantillas nuevas y modificadas, e incluir `verificacion.router` en `main.py` justo después de `cuota_justa.router`.
3. Reiniciar `quantfut-api-1` fuera de `:11` y `:41`.
4. Comprobar `/verificacion/` (`200`, CSP con `connect-src 'self'`, `script-src 'self'`), `/static/verificar-cadena.js` (`200`), prueba real del botón «Verificar `/chain` en este navegador» en `/verificacion/` y estado `preview`/`off` en `/en/verification/` y `/pt/verificacao/`.

## Vuelta atrás
`en=off` / `pt=off` en `activos.txt` desactiva las versiones traducidas en ≤ 20 s; restaurar `main.py`, `seo.py` y las plantillas respaldadas, retirar `verificacion.router` y reiniciar `quantfut-api-1`.
