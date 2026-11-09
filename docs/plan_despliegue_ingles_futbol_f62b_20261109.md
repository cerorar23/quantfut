# F6.2b — Fútbol en inglés (`/en/futbol/` y `/en/futbol/{competición}/{slug}/`) — plan, 2026-11-09

## Qué es
El pilar de fútbol y las páginas de partido en inglés, como páginas independientes sobre `base_en.html` (igual que NBA en F6.2a).
Reutilizan las reglas del español (`futbol_paginas.estado`, la forma, el cara a cara y la posición). Cambian la redacción, el formato
(`62%`, `2.67`, `Nov 8, 2026`), la forma (G/E/P → W/D/L) y el idioma. El español **no se toca** (412 pruebas de regresión SEO en verde).
Mismo slug tras el prefijo: `/futbol/{comp}/{slug}/` ↔ `/en/futbol/{comp}/{slug}/`.

Glosario: pronóstico → forecast; empate → draw; local/visitante → home/away; forma → form; posición → league position.
Competiciones y nombres de equipo se dejan tal cual (son nombres propios).

Detrás del interruptor de idiomas (`activos.txt`): hoy `preview` ⇒ `noindex`, sin caché, fuera del sitemap y del hreflang hasta `en=on`.

## Cambios técnicos
- `src/qf/api/futbol_en.py` (nuevo): equivalencias español ↔ inglés registradas en `idiomas.py`, veredicto en inglés, forma y posición con ordinales, pilar y partido, sitemap solo con `on`.
- `paginas/en_futbol_partido.html`, `paginas/en_futbol_cartelera.html` (nuevas), sobre `base_en.html`.
- `paginas/base_en.html`: enlace «Football» en la navegación inglesa.
- `seo.py`: el sitemap incluye `futbol_en.entradas_sitemap()` (vacío salvo `en=on`).
- `main.py`: **2 líneas** nuevas — `futbol_en` en el `from . import …` y `app.include_router(futbol_en.router)` tras `nba_en.router`.

## Pruebas (`tests/test_futbol_en.py`, 15)
Apagado (404 y fuera del mapa), vista previa (`noindex`, sin caché), partido final (marcador, fallo del favorito, Brier 1,138, forma `LLDWL`/`WWLDW`,
posición con ordinales, cara a cara), partido previo con modelo propio y con mercado como referencia, sin pronóstico/inexistente → 404, base caída → 503,
pilar, redirección sin barra, mismos aciertos y mismos partidos que el español, hreflang recíproco con `x-default`, selector en los dos sentidos,
y texto inglés sin palabras vacías españolas con enlaces ingleses o marcados `lang="es"`.

## Lo que NO incluye
- Tenis en inglés (F6.2c), páginas de equipo de NBA en inglés, tarjeta social en inglés.
- Las ligas de copa muestran la posición de la liga doméstica del equipo, igual que el español (regla de competición ≠ liga del equipo).

## Despliegue (cuando se apruebe; no es visible al público: el estado actual es `preview`)
1. Pre-vuelo: sha256 de `seo.py`, `base_en.html` y `main.py` de producción = los del último despliegue (`cb08ac8a`); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de `futbol_en.py`, `seo.py`, `base_en.html`, `en_futbol_partido.html`, `en_futbol_cartelera.html`; `main.py` (CRLF, 2 líneas con `\r`, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar en el dominio real: `/en/futbol/` y un partido → 200 con `noindex` y `no-store`; el sitemap sin `/en/futbol`; el español idéntico; probabilidades inglesas = españolas.
4. El titular revisa el inglés y solo entonces `en=on`.

## Vuelta atrás
`en=off` cierra todo el inglés (≤ 20 s). Código: restaurar desde `~/respaldos/ingles_futbol_f62b_<fecha>/`, borrar `futbol_en.py` y las dos plantillas, reiniciar fuera de :11 y :41.

## Riesgos
- Si la base de fútbol cae, el pilar y los partidos responden 503 con `Retry-After` (nunca 404) y el sitemap conserva el pilar.
- Una vez en `on`, el sitemap crece con una URL inglesa por cada partido español con pronóstico.
