# Plan de despliegue — SEO, consentimiento y páginas públicas (PR #283, #286 y #287)

Preparado el 8-nov-2026. **Es un plan, no un despliegue: nada de esto se ha ejecutado en el servidor.** Sigue
DEPLOYS.md: una sola sesión despliega a la vez, se compara lo desplegado con `main` antes de sobrescribir, se
respalda, se verifica y se anota la entrada con su vuelta atrás.

## 1. Qué se despliega y por qué se hace así

| PR | Contenido | CI en GitHub |
|---|---|---|
| #286 | `robots.txt`, sitemaps, `noindex`, `www`→dominio sin `www`, 404 en HTML, páginas `/metodologia/`, `/juego-responsable/`, `/sobre-nosotros/` | verde · **fusionado el 8-nov 22:02 UTC (`e54511b1`)** |
| #287 | Secciones con URL propia (`/historial/`, `/pronosticos/`…), `rutas.js`, History API en `app.js`, pie global | verde · **fusionado el 8-nov 22:07 UTC (`dfad23c6`)** |
| #283 | Consentimiento de la medición (opt-in en Europa), `db/104`, plan SEO | verde |

**Prueba del conjunto** (worktree aparte, sin subir): fusionados #286+#287 y después #283 sobre `main`, la suite completa
de Python da **2.104 pasan, 126 omitidas, 0 fallos** y el frontend **157/157**. Los conflictos reales entre PR están en §3.

> **Estado (8-nov 22:10 UTC):** #286 y #287 ya están en `main` (por squash; `main` es idéntico al árbol que pasó el CI). 
> Queda #283, al que se le aplicó la resolución de §3 al ponerlo al día con `main`. Sigue sin desplegarse nada.

### Hallazgos que obligan a un método concreto (comprobados el 8-nov en el servidor, solo lectura)

1. **El contenedor `quantfut-api-1` tiene 9 archivos que NO están en su imagen** (`docker diff`): `frontend/{app.js,
   index.html, conversion-views.js, historial-views.js, conversion-views.test.mjs}`, `src/qf/api/main.py` y
   `src/qf/publish/{escalera.py, escalera_datos.py}`. Por tanto **no se recrea el contenedor ni se reconstruye la imagen**:
   se pierden esos cambios. Y **no se usa `docker commit`**: el contenedor lleva `/run/secrets/*.json` en su capa y
   quedarían incrustados en una imagen. Método: `docker cp` + `docker restart`, como en todos los despliegues del 8-nov.
2. **`scripts/deploy.sh construir api` no sirve**: construye desde `main` y revertiría lo anterior.
3. **`src/qf/api/main.py` de producción ≠ el de `main`** (38 líneas distintas, parches del 8-nov que aún no están en
   `main`). **Se parchea, no se copia**: el cambio de nuestros PR son 11 líneas (`main_py.patch`, junto a este
   documento). Comprobado: se aplica limpio sobre el `main.py` de producción y compila.
4. Los otros 11 archivos existentes que tocan los PR **son idénticos a `main`** en producción (se comprobó por sha256),
   salvo `frontend/package.json`, que no se sirve y no se despliega.
5. Imagen actual: `quantfut-api-mobile:tenis-v2-65fb5b1a`. El compose **no se toca** (conserva la red `tenis_net`).

### Archivos que se llevan al contenedor (`/app/…`)

- Nuevos: `src/qf/api/{seo.py, paginas.py, rutas_web.py}`, `src/qf/api/paginas/{base,metodologia,juego_responsable,sobre_nosotros}.html`,
  `src/qf/comercial/meta_consent.py`, `frontend/rutas.js`.
- Existentes idénticos a `main`: `src/qf/api/{cuentas.py, web.py, whop.py}`, `src/qf/comercial/{meta_capi.py, whop.py}`,
  `frontend/{app.js, conversion.css, index.html, membership.js, meta-pixel.js}`.
- Existente distinto de `main`: `src/qf/api/main.py` → **el de producción + `main_py.patch`**.
- Base de datos: `db/104_whop_checkout_consentimiento.sql` (una columna con valor por defecto; aditiva).
- **No cambia el worker**: solo envía a Meta lo ya encolado; el filtro de consentimiento está en `enqueue`, que ejecuta la API.

## 2. Antes de empezar (decisiones tuyas, no técnicas)

- [ ] **Lectura de los textos** (son contenido sobre dinero): las 3 páginas de confianza y las 9 secciones. Sobre todo
  «no afirmamos superar al mercado» y la limitación del registro externo en la metodología.
- [ ] **El consentimiento ya no es teórico**: en producción el Pixel está activo (`2253…`) y `META_CAPI_ENABLED=1`. Al
  desplegar, un visitante de Europa o con país desconocido deja de medirse hasta aceptar (menos conversiones atribuidas
  de ese tráfico). El resto de países se mantiene como hoy (opt-out, decisión del 15-oct).
- [ ] **`/legal/privacidad` sigue diciendo que la medición «viene activada»**: queda más permisiva que la práctica.
  Conviene actualizarla en este mismo despliegue o justo después (es un texto legal versionado: lo revisas tú).
- [ ] **Quien tenga sesión en `www.pronosticosdeportivos.pro` tendrá que entrar de nuevo** (la cookie es del host).
- [ ] Hora: evitar **08:30–09:30 UTC** (el daily corre a las 09:00 UTC). `docker restart` deja la API sin servicio ~10–20 s.
- [ ] Nadie más desplegando: `~/quantfut/releases/deploy.lock` (hoy vacío) y las últimas entradas de DEPLOYS.md.

## 3. Orden de fusión y conflictos (resueltos en la prueba)

1. Fusionar **#286**. Sin conflictos.
2. **#287** se re-apunta solo a `main` al fusionar #286; esperar a que su CI termine en verde y fusionar. Sin conflictos.
3. **#283** (rama `seo/f0-consentimiento`): chocará con lo anterior en 6 archivos. Resolución, ya probada:
   - `frontend/app.js`: conservar **las dos** importaciones (`membership.js?v=consentimiento-20261108` y `rutas.js?v=rutas-20261108`).
   - `frontend/conversion.css`, `harness/tareas.md`, `harness/progreso.md`: conservar **ambos** bloques (los dos añaden al final).
   - `frontend/index.html`: versiones nuevas y únicas, porque cambia el contenido de ambos archivos:
     `conversion.css?v=consentimiento-pie-20261108` y `app.js?v=consentimiento-rutas-pie-20261108`.
   - `frontend/package.json`: partir de la línea de `check` de #287 y añadir `node --check meta-pixel.js` y
     `meta-pixel.test.mjs` (la de #283 añade esos dos; la de #287 `rutas.js` y `rutas.test.mjs`; deben estar los cuatro).
   - Tras resolver: `npm run check` en `frontend/` (157/157) y la suite de Python.
4. **Comprobar `main`**: la versión de `app.js` en `index.html` es la que se desplegará; si otra sesión la subió entre
   tanto, se vuelve a resolver igual y se usa un sufijo propio.

Si una de las fusiones se retrasa, los PR son **independientes en funcionamiento**: #286 sin #287 funciona (el sitemap
solo lista lo que existe) y #283 sin los otros también.

## 4. Pre-vuelo (solo lectura; si algo no cuadra, PARAR)

```bash
git fetch origin && git switch --detach origin/main        # la fuente de lo que se despliega es main
scripts/deploy.sh estado                                    # worker y API frente a main (informativo: la API ya difiere en main.py)
ssh quantfut 'cat ~/quantfut/releases/deploy.lock; ls -1t ~/quantfut/releases | head -3'
```

Los 12 archivos que se van a reemplazar deben seguir **idénticos a `main`** (excepto `main.py`):

```bash
for f in src/qf/api/cuentas.py src/qf/api/web.py src/qf/api/whop.py src/qf/comercial/meta_capi.py src/qf/comercial/whop.py \
         frontend/app.js frontend/conversion.css frontend/index.html frontend/membership.js frontend/meta-pixel.js; do
  # OJO: tras fusionar, main ya trae la versión NUEVA; compara con la versión de main ANTES de los PR (commit 06981ccd)
  prod=$(ssh quantfut "docker exec quantfut-api-1 sha256sum /app/$f" | cut -c1-64)
  base=$(git show 06981ccd:$f | tr -d '\r' | sha256sum | cut -c1-64)
  [ "$prod" = "$base" ] && echo "OK    $f" || echo "DIFIERE $f   <-- PARAR y averiguar"
done
```

Y el parche de `main.py` debe seguir aplicándose sobre el `main.py` que haya EN ESE MOMENTO en producción:

```bash
rm -rf /tmp/seo && mkdir -p /tmp/seo/src/qf/api && ssh quantfut 'docker exec quantfut-api-1 cat /app/src/qf/api/main.py' > /tmp/seo/src/qf/api/main.py
cp docs/despliegue_seo_20261108/main_py.patch /tmp/seo/
(cd /tmp/seo && git apply --check main_py.patch && echo "el parche se aplica limpio")   # cualquier otra salida: PARAR
```

## 5. Despliegue

Todo con el servidor como `qf` (`ssh quantfut`). Sustituye `R` por la carpeta de respaldo.

**5.1 Respaldo** (archivos tal como están en el contenedor y la tabla):
```bash
R=~/respaldos/seo_f0_f1_$(date -u +%Y%m%d%H%M); mkdir -p $R
for f in src/qf/api/cuentas.py src/qf/api/main.py src/qf/api/web.py src/qf/api/whop.py src/qf/comercial/meta_capi.py \
         src/qf/comercial/whop.py frontend/app.js frontend/conversion.css frontend/index.html frontend/membership.js \
         frontend/meta-pixel.js; do mkdir -p $R/$(dirname $f); docker cp quantfut-api-1:/app/$f $R/$f; done
cd ~/quantfut && docker compose exec -T db pg_dump -U qf -d quantfut -t whop_checkouts > $R/whop_checkouts_antes_104.sql
(cd $R && find . -type f ! -name SHA256SUMS -exec sha256sum {} + > SHA256SUMS)
```

**5.2 Migración `db/104`** (antes que el código; el código anterior la tolera porque la columna tiene valor por defecto):
```bash
ssh quantfut "cd ~/quantfut && docker compose exec -T -e PGOPTIONS='-c lock_timeout=5000' db psql -U qf -d quantfut -v ON_ERROR_STOP=1" \
  < db/104_whop_checkout_consentimiento.sql
ssh quantfut "cd ~/quantfut && docker compose exec -T db psql -U qf -d quantfut -c \"SELECT column_name, column_default FROM information_schema.columns WHERE table_name='whop_checkouts' AND column_name='ads_consent'\""
```

**5.3 Preparar los archivos** (desde `main` ya fusionado; el `main.py` es el de producción + parche):
```bash
git archive origin/main src/qf/api/cuentas.py src/qf/api/web.py src/qf/api/whop.py src/qf/api/seo.py src/qf/api/paginas.py \
  src/qf/api/rutas_web.py src/qf/api/paginas src/qf/comercial/meta_capi.py src/qf/comercial/whop.py src/qf/comercial/meta_consent.py \
  frontend/app.js frontend/conversion.css frontend/index.html frontend/membership.js frontend/meta-pixel.js frontend/rutas.js \
  | ssh quantfut 'rm -rf ~/quantfut/releases/seo-f0-f1 && mkdir -p ~/quantfut/releases/seo-f0-f1 && tar -x -C ~/quantfut/releases/seo-f0-f1'
# main.py = producción + parche, validado antes (§4) y compilado:
(cd /tmp/seo && git apply main_py.patch && python -m py_compile src/qf/api/main.py && echo "main.py parcheado: compila")
scp /tmp/seo/src/qf/api/main.py quantfut:~/quantfut/releases/seo-f0-f1/src/qf/api/main.py
```

**5.4 Copiar al contenedor y a la copia del host** (mismo patrón que los despliegues del 8-nov):
```bash
D=~/quantfut/releases/seo-f0-f1
for f in $(cd $D && find src frontend -type f ! -path '*/paginas/*'); do docker cp $D/$f quantfut-api-1:/app/$f; done
docker cp $D/src/qf/api/paginas quantfut-api-1:/app/src/qf/api/        # crea /app/src/qf/api/paginas
cp -p $D/frontend/* ~/quantfut/frontend/                                  # copia del host, para que coincida
```

**5.5 Ensayo antes de reiniciar** (un proceso nuevo importa lo copiado; no toca al servidor en marcha):
```bash
docker exec quantfut-api-1 python -c "import qf.api.main as m; print([r.path for r in m.app.routes if 'sitemap' in getattr(r,'path','') or 'metodologia' in getattr(r,'path','')])"
```
Si falla: **no reiniciar**; restaurar desde `$R` (§7) y parar.

**5.6 Reinicio y salud**:
```bash
docker restart quantfut-api-1 && sleep 8 && curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health   # 200
docker logs --since 2m quantfut-api-1 2>&1 | grep -iE "error|traceback" | head
```

## 6. Verificación (en el dominio real)

```bash
B=https://pronosticosdeportivos.pro
curl -s $B/robots.txt                                   # debe traer el bloque de Cloudflare Y nuestras líneas (User-agent, Content-Signal, Allow, Sitemap)
curl -s $B/sitemap.xml; curl -s $B/sitemap-paginas.xml  # índice y 14 URLs (3 base + 8 secciones + 3 páginas), sin '#'
curl -sI $B/app/v1/plans | grep -i x-robots-tag          # noindex
curl -sI https://www.pronosticosdeportivos.pro/historial/ | grep -iE "^HTTP|location"      # 301 → dominio sin www
curl -s -A "Mozilla/5.0" -H "Accept: text/html" $B/historial/ | grep -oE "<title>[^<]*|rel=\"canonical\"[^>]*"
curl -s $B/rutas.js | head -2; curl -s -o /dev/null -w "%{http_code}\n" -H "Accept: text/html" $B/no-existe/   # 404 en HTML
curl -s $B/app/v1/whop/config                            # incluye "consentRegime": "opt-out" desde un país no europeo (p. ej. México); "opt-in" = Cloudflare no envía CF-IPCountry
for p in metodologia juego-responsable sobre-nosotros; do curl -s -o /dev/null -w "$p %{http_code}\n" $B/$p/; done
```

- [ ] **`consentRegime`**: si desde un país no europeo sale `opt-in`, Cloudflare **no está enviando `CF-IPCountry`**
  (Cloudflare → Network → «IP Geolocation»). Hasta activarlo, todo el mundo vería el aviso en modo estricto.
- [ ] **`robots.txt`**: confirmar que el bloque de «content signals» de Cloudflare no duplica ni contradice el nuestro; si
  choca, se ajusta en Cloudflare (Security → Bots → robots.txt gestionado), no en el código.
- [ ] **Navegador** (ventana nueva, sin sesión): `/historial/` carga, navegar entre secciones, atrás/adelante, `/#historial`
  → `/historial/`, el pie con los tres enlaces, y el aviso de medición (en Europa: sin Pixel hasta aceptar; comprobar en
  Red que `fbevents.js` no se pide antes). Después **con sesión**: iniciar, recargar en `/planes/`, abrir «Mi cuenta».
- [ ] **Pago real**: solo tú (no se introducen datos de tarjeta desde aquí); idealmente con el modo de pruebas de Whop.
  Comprobar que tras el cobro se activa el acceso y que, rechazando la medición, no se encola `Purchase` en `meta_events`.
- [ ] **Search Console**: propiedad de dominio verificada → enviar `https://pronosticosdeportivos.pro/sitemap.xml` →
  «Inspección de URLs → HTML renderizado» de `/historial/` y `/metodologia/`. Revisar en 3–7 días «Páginas»: que `www.` y
  `api.` pasen a «excluidas por noindex/redirección» y que no aparezcan URLs de `/app/v1/…`.

## 7. Vuelta atrás

El despliegue es **solo archivos en el contenedor + una columna aditiva**, así que la vuelta atrás es completa:

```bash
R=~/respaldos/seo_f0_f1_<fecha>                       # la carpeta del respaldo (5.1)
(cd $R && sha256sum -c SHA256SUMS)                     # el respaldo está íntegro
for f in $(cd $R && find src frontend -type f); do docker cp $R/$f quantfut-api-1:/app/$f; done
cp -p $R/frontend/* ~/quantfut/frontend/
# los archivos NUEVOS (seo.py, paginas.py, paginas/, rutas_web.py, meta_consent.py, rutas.js) pueden quedarse: sin el
# main.py anterior nadie los importa. Si se quieren quitar: docker exec quantfut-api-1 rm -rf /app/src/qf/api/paginas ...
docker restart quantfut-api-1
```

- La columna `whop_checkouts.ads_consent` **no se revierte** (valor por defecto `true`, el código anterior la ignora).
- Si solo falla una parte, se puede revertir **solo** el frontend (restaurar los 5 archivos de `frontend/` y reiniciar no es
  necesario: se sirven desde disco) o **solo** la API (`main.py`) sin tocar lo demás.
- Cloudflare: las URLs de `app.js`/`conversion.css` llevan `?v=` nuevo, así que no hay que purgar; si se revierte, las
  anteriores siguen en caché con su versión.

## 8. Riesgos conocidos y qué observar durante 48 h

1. **Parches que solo viven en el contenedor** (los 9 de §1): cualquier `docker compose up --force-recreate` los
   pierde, también estos. Es una deuda anterior a este despliegue; la salida es que `main` alcance a producción y se
   reconstruya la imagen entera (ver DEPLOYS.md, «lo que corre en producción es lo que dice `main`»).
2. **Consentimiento**: vigilar en `meta_events` el volumen de eventos `website` (debe bajar solo para tráfico europeo) y
   que no haya errores en el log de la API al crear checkouts (`ads_consent`).
3. **Redirección de `www`**: cualquier integración que aún apunte a `www.` (correos antiguos, Firebase, Whop) recibirá un
   301; los POST reciben 308 y conservan el método.
4. **Indexación**: es lento. No esperar efectos antes de 1–2 semanas; lo que sí debe verse ya es el sitemap aceptado.
5. **Lo que NO se ha probado**: Safari, un cobro real y el renderizado real de Google (solo posible con la URL pública).

## 9. Entrada para DEPLOYS.md (rellenar al terminar)

```
### 2026-11-DD HH:MM UTC · SEO: robots/sitemaps/noindex, páginas públicas, secciones con URL propia y consentimiento de medición · API + db/104 (PR #283, #286, #287)
- Método: archivos al contenedor en marcha (`docker cp`) + `docker restart`; NO recreado (9 archivos solo en el contenedor).
- `main.py` = el de producción + parche de 11 líneas (docs/despliegue_seo_20261108/main_py.patch); el resto, idéntico a `main` (`<commit>`).
- db/104 con lock_timeout 5s. Respaldo: ~/respaldos/seo_f0_f1_<fecha>/ (archivos + whop_checkouts).
- Verificado: <resultados de §6>.
- Vuelta atrás: ver docs/plan_despliegue_seo_20261108.md §7.
```
