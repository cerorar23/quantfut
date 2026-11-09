# F6.2a — NBA en inglés (`/en/nba/` y `/en/nba/{slug}/`) — plan, 2026-11-09

## Qué es
El pilar de NBA y las páginas de partido en inglés, como **páginas independientes** (no dentro de la aplicación de una sola página, que se vuelve española al cargar el JavaScript).
Reutilizan los datos y las reglas de `nba_paginas.py` (estado del partido, veredicto, ventana de la cartelera); solo cambian la redacción, el formato (`50%`, `0.25`, `Nov 8, 2026`) y el idioma.
El español **no se toca** (sus 397 pruebas SEO siguen en verde). Mismo slug tras el prefijo: `/nba/<slug>/` ↔ `/en/nba/<slug>/`.

Va detrás del interruptor de idiomas de F6.1 (`/srv/quantfut/artifacts/idiomas/activos.txt`): hoy está en `preview`, así que al desplegar las páginas son visibles solo para quien conozca la URL, con `noindex`,
y **no entran en el sitemap ni en el hreflang hasta `en=on`**.

## Cambios técnicos
- `src/qf/api/nba_en.py` (nuevo) + `paginas/en_nba_cartelera.html` y `en_nba_partido.html` (nuevas), sobre `base_en.html` (enlace «NBA» en la navegación inglesa).
- `idiomas.py`: **traductores dinámicos** (`registrar_traductor`) para familias de páginas que no se enumeran de antemano (un partido); `puerta()` (404 si apagado, `noindex` y sin caché en vista previa).
  El hreflang del sitemap y el selector de idioma funcionan por equivalencias español ↔ inglés: pilar y cada partido con sello (los mismos que enumera el español, con el mismo `lastmod`). Lo que no tiene versión inglesa (páginas de equipo `/nba/equipos/…`) no lleva hreflang.
- `base.html`: un bloque más (`revision_p`) para sustituir la línea «Última revisión» por «Forecast sealed … · scheduled start …».
- `seo.py`: el sitemap incluye `nba_en.entradas_sitemap()` (vacío salvo `en=on`). `main.py`: **2 líneas** (importar `nba_en` y `app.include_router(nba_en.router)` tras `cuota_justa.router`).

## Lo que NO incluye (a propósito)
- Páginas de equipo de NBA en inglés (`/nba/equipos/…`), fútbol y tenis en inglés (F6.2b y F6.2c), tarjeta social en inglés (la imagen está escrita en español: las páginas usan la tarjeta `summary`).
- La versión española de NBA vive dentro de la app de una sola página, que no incluye el selector de idioma: el inglés enlaza al español, pero desde el español solo apunta el hreflang del sitemap.

## Pruebas (`tests/test_nba_en.py`, 16)
Apagado (404 y sin rastro en el sitemap), vista previa (`noindex`, sin caché, fuera del sitemap), página final con todas las cifras y frases, un fallo dicho igual, partido previo, sin sello/inexistente → 404, motor caído → 503, pilar, redirección sin barra,
**las dos versiones calculan lo mismo** (estado, veredicto, probabilidades, hash, contexto y los mismos enlaces que el español con prefijo `/en`), hreflang recíproco con `x-default` para el pilar y cada partido, selector, y
el texto inglés sin palabras vacías españolas ni acentos con todos los enlaces a páginas inglesas o marcados `lang="es"`.

## Despliegue (cuando se apruebe; no es visible al público: el estado actual es `preview`)
1. Pre-vuelo: sha256 de `idiomas.py`, `seo.py`, `base.html`, `base_en.html` y `main.py` de producción = los del último despliegue; `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` + `main.py` (CRLF, 2 líneas con `\r`, `ast.parse`) + `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar en el dominio real: `/en/nba/` y un partido → 200, `noindex`, `no-store`; el sitemap sin `/en/nba`; el español idéntico; regresión de rutas.
4. El titular revisa el inglés (también NBA) y solo entonces `en=on`.

## Vuelta atrás
`en=off` cierra todo el inglés (≤ 20 s). Quitar el código: restaurar desde `~/respaldos/ingles_nba_f62a_<fecha>/`, borrar `nba_en.py` y las dos plantillas, reiniciar fuera de :11 y :41.

## Riesgos
- La cartelera y el sitemap en inglés dependen de la misma `nba-api` que el español; si cae, 503 con `Retry-After` (nunca 404).
- Una vez en `on`, el sitemap crece con una URL inglesa por cada partido español; IndexNow las enviará sin intervención.
