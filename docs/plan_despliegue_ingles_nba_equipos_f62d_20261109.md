# F6.2d — Equipos de NBA en inglés (`/en/nba/equipos/{equipo}/`) — plan, 2026-11-09

## Qué es
Las páginas de equipo de NBA en inglés, como páginas independientes sobre `base_en.html`. Reutilizan el índice, el UMBRAL (5 pronósticos
sellados en 45 días) y las reglas de `nba_equipos.py` (qué partidos cuentan, qué es un acierto, cuándo una página es indexable), así que
las dos versiones de un equipo siempre dicen lo mismo. El español **no se toca** (439 pruebas en verde, incluidas las de regresión).
Mismo slug: `/nba/equipos/{slug}/` ↔ `/en/nba/equipos/{slug}/`.

Reglas de indexación (idénticas al español, más una):
- Indexable ⇔ el equipo supera el UMBRAL **y** el inglés está en `on`.
- Bajo el umbral: existe, con `noindex`, fuera del sitemap.
- Vista previa (`preview`): siempre `noindex` y sin caché, aunque supere el umbral.
- Apagado (`off`): 404.

Detrás del interruptor de idiomas (`activos.txt`). Hoy está en `preview`.

## Cambios técnicos
- `src/qf/api/nba_equipo_en.py` (nuevo): equivalencias español ↔ inglés registradas en `idiomas.py`; construcción de la página en inglés con las mismas cifras; sitemap solo con `on` y solo para equipos que superan el umbral; redirección sin barra.
- `paginas/en_nba_equipo.html` (nueva), sobre `base_en.html`.
- `seo.py`: el sitemap incluye `nba_equipo_en.entradas_sitemap()` (vacío salvo `en=on`).
- `main.py`: **2 líneas** — `nba_equipo_en` en el `from . import …` y `app.include_router(nba_equipo_en.router)` tras `tenis_en.router`.

## Pruebas (`tests/test_nba_equipo_en.py`, 10)
Apagado (404 y fuera del mapa), vista previa (`noindex` aunque supere el umbral), equipo sobre el umbral (indexable, título, canonical),
equipo bajo el umbral (`noindex`, fuera del sitemap), inexistente y sin barra, NBA caída ⇒ 503, **las cifras coinciden con el español** (total, aciertos, victorias,
indexabilidad y resultados de cada fila), sitemap solo con indexables y hreflang recíproco con `x-default`, selector, y texto inglés sin palabras
españolas con enlaces ingleses o marcados `lang="es"`.

## Lo que NO incluye
- La tarjeta social en inglés (sigue pendiente; las páginas usan la tarjeta de marca sin texto en inglés).

## Despliegue (cuando se apruebe; no es visible al público: el estado actual es `preview`)
1. Pre-vuelo: sha256 de `seo.py` y `main.py` de producción = los del último despliegue; `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de `nba_equipo_en.py`, `seo.py`, `en_nba_equipo.html`; `main.py` (CRLF, 2 líneas con `\r`, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar en el dominio real: un equipo bajo el umbral → 200 con `noindex`; el equipo sobre el umbral → `noindex` mientras esté en `preview`; sitemap sin `/en/nba/equipos`; el español idéntico.
4. El titular revisa el inglés y solo entonces `en=on`. Con `on`, los equipos que superan el umbral entran en el sitemap (hoy ninguno lo supera en el español: el motor solo lleva desde el 2-nov).

## Vuelta atrás
`en=off` cierra todo el inglés (≤ 20 s). Código: restaurar desde el respaldo, borrar `nba_equipo_en.py` y la plantilla, reiniciar fuera de :11 y :41.

## Riesgos
- Si la NBA cae, la página responde 503 con `Retry-After` (nunca 404).
- Con el umbral actual, es posible que ningún equipo sea indexable todavía: la página existe y el sitemap no cambia. La revisión del umbral está programada para el 16-nov.
