# Despliegue de F5 (parte 1): CSP en modo informe y caché con renovación en segundo plano — plan, 2026-11-09

Qué se despliega (solo servidor, sin frontend, red ni Caddy):
1. **CSP en MODO INFORME** (`src/qf/api/csp.py`): cabecera `Content-Security-Policy-Report-Only` en las páginas HTML públicas y `POST /csp-report` que guarda
   informes saneados. **No bloquea nada**: solo enseña qué bloquearía una política, para aplicarla más adelante con datos de una semana real (un `Content-Security-Policy`
   aplicado a ciegas rompería el pago con Whop o el acceso con Google).
2. **`nba_datos`: servir lo caducado al instante y renovarlo en segundo plano.** Medido el 9-nov: la primera petición de `/nba/` tras un rato en reposo tardaba **5,5 s**
   (la cartelera de cada día es lenta en `nba-api`) y las siguientes 0,6 s. Ahora un dato de menos de 1 h se sirve YA y se renueva aparte; solo se espera si no hay copia.

## Medición de partida (lab, 9-nov 04:32 UTC; móvil emulado: CPU ×4, 1,6 Mbps y 150 ms de latencia, sin caché; medido con Chromium controlado)
| Página | TTFB | LCP | TBT | CLS | Peticiones | Transferido |
|---|---|---|---|---|---|---|
| `/` | 1,0 s | 3,7 s | **2,6 s** (11 tareas largas) | 0 | 50 | 1,9 MB |
| `/nba/` | **4,2 s** (caché fría) | 6,5 s | 0,26 s | 0 | 50 | 1,0 MB |
| partido NBA | 1,4 s | 3,7 s | 0,08 s | 0 | 48 | 0,9 MB |
| `/futbol/` | 2,9 s | 5,0 s | 0,29 s | 0 | 44 | 1,4 MB |

Umbrales «buenos» de Google: LCP ≤ 2,5 s, CLS ≤ 0,1, INP ≤ 200 ms (el TBT es solo su sustituto de laboratorio). **CLS es 0 en todas** (el HTML inicial se sustituye sin saltos).
LCP queda fuera en este perfil lento; **no son datos de campo** (CrUX no tiene tráfico suficiente todavía) y el perfil es más duro que un móvil medio. Tiempo de servidor medido
sin limitación desde fuera: 0,35–1,1 s en todas las páginas, incluso en la estática `/metodologia/` (HTML sin caché de borde: `Cache-Control: no-cache, must-revalidate`, `cf-cache-status: DYNAMIC`).

Lo que NO se arregla aquí y queda propuesto (cada punto, con su propio permiso):
- **Cloudflare:** una regla de caché para `/`, `/historial/`, `/planes/`, `/metodologia/`, `/nba/*`, `/futbol/*`, `/tenis/*` con TTL de borde de 60 s bajaría el TTFB a decenas de ms
  y protegería el origen de los rastreadores. Es una acción en el panel de Cloudflare (solo la puede hacer el titular) y exige comprobar antes que ninguna de esas páginas varía por cookie.
- **La SPA:** 17 módulos ES en cascada y 7 hojas de estilo que bloquean el pintado (TBT de `/` = 2,6 s). `modulepreload` aplana la cascada; es un cambio de frontend con riesgo moderado.

## 1. Pre-vuelo (solo lectura)
1. `origin/main` contiene el PR; anotar `git rev-parse origin/main`.
2. Los archivos que se sobrescriben siguen siendo los de F2.4 (`DEPLOYS.md`, 9-nov 04:16 UTC): comparar `sha256sum` en el contenedor con los blobs de `ad6f7c2e` para
   `src/qf/api/{nba_datos.py, seo.py, indexnow.py}`. `main.py` de producción: sha256 `a808ad0a…`.
3. `/health` 200; `docker exec quantfut-api-1 ls /srv/quantfut/artifacts` (el directorio `csp` no existe todavía).
4. Respaldo en `~/respaldos/csp_f5_<fecha>/` con `SHA256SUMS`: los 3 archivos anteriores + `main.py`.

## 2. Copia y reinicio
1. `docker cp` de `csp.py` (nuevo), `nba_datos.py`, `seo.py`, `indexnow.py` a `/app/src/qf/api/` (blobs de `origin/main`, LF, sha256 antes y después).
2. `main.py` de producción (CRLF), **tres cambios** con `\r` en `sed`: añadir `csp` al `from . import …`; añadir `csp.aplicar_cabeceras(request, response)` justo después de la línea
   `seo.aplicar_cabeceras(request, response)` del middleware `security_middleware`; y `app.include_router(csp.router)` justo después de `app.include_router(og.router)` (y antes del de `indexnow`,
   que debe seguir siendo el último). Comprobar que el diff son solo esas líneas y la sintaxis con `ast.parse` (sin `py_compile`).
3. `docker restart quantfut-api-1`; esperar `/health` 200; log sin errores.

## 3. Verificación en el dominio real (consultas únicas por la caché de Cloudflare)
- `/`, `/nba/`, `/futbol/`, `/tenis/`, un partido y `/historial/` llevan `Content-Security-Policy-Report-Only` y `Reporting-Endpoints`, **y no** `Content-Security-Policy`;
  `/metodologia/` (con su CSP propia), `/robots.txt`, `/sitemap.xml`, JSON, imágenes y `/control/` no llevan la de informe.
- **Nada se rompe** en un navegador real con la política en modo informe: la app arranca, `/planes/` carga el selector de planes y no hay errores nuevos en la consola (solo avisos de CSP, que es lo esperado).
  Si algún flujo cambia de comportamiento, es un fallo: se quita la línea de `main.py` y se reinicia.
- `POST /csp-report` con un informe de prueba → 204 y una línea saneada en `/srv/quantfut/artifacts/csp/informes.jsonl` (sin consulta ni URL completa); basura → 204 sin escribir; cuerpo > 8 KB → 413.
- Tras unas horas: `docker exec quantfut-api-1 python -m qf.api.csp` resume qué se bloquearía, por directiva y host.
- `/nba/` en frío: pedirla tras ≥ 5 minutos de reposo y comprobar que ya no tarda segundos (la primera tras el reinicio sí espera: todavía no hay copia).
- Regresión de las rutas habituales en 200; 0 errores en el log; el cron de IndexNow sigue funcionando (el reinicio no lo afecta).

## 4. Vuelta atrás
`R=$(cat ~/respaldos/.ultimo_csp_f5)`: `(cd $R && sha256sum -c SHA256SUMS)`; restaurar con `docker cp` los 3 archivos y `main.py`; borrar `csp.py` del contenedor; `docker restart quantfut-api-1`. Lo visible
(la cabecera y la ruta) desaparece al reiniciar. `rm -rf /srv/quantfut/artifacts/csp` borra los informes.

## 5. Siguiente paso (otra tarea, con la política ya medida)
Después de ≥ 7 días de informes: ajustar la lista de hosts, quitar lo que sobre, y pasar a `Content-Security-Policy` aplicada con un plan de vuelta atrás propio. No se aplica nada en esta tarea.

## 6. Riesgos conocidos
- Cada navegador envía informes: tope de 400 líneas por hora y proceso, 8 KB por cuerpo y 5 MB de archivo; cualquier tercero puede enviar basura al receptor (se descarta o se sanea).
- Los archivos copiados se pierden si alguien recrea el contenedor (igual que los anteriores).
- Los flujos que solo ocurren con interacción (acceso con Google, pago con Whop) no se ejercitan en la verificación: sus hosts están en la política por el código, y los informes dirán si falta alguno.
