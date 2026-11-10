# F6.2c — Tenis en inglés (`/en/tenis/` y `/en/tenis/{torneo}/{slug}/`) — plan, 2026-11-09

## Qué es
El pilar de tenis y las páginas de partido en inglés, como páginas independientes sobre `base_en.html` (igual que NBA y fútbol).
Reutilizan la lógica del español (`tenis_paginas.resultado`, `veredicto`, `estado`, `mercado_ganador`): la salvaguarda de que el ganador del
mercado y los SETS coincidan se aplica igual en las dos versiones. El español **no se toca** (429 pruebas en verde, incluidas las de regresión).
Mismo slug tras el prefijo: `/tenis/{torneo}/{slug}/` ↔ `/en/tenis/{torneo}/{slug}/`.

Las etiquetas de mercado y las selecciones vienen del feed en español; se traducen con una tabla pequeña de los tipos que publica hoy el motor
(«Ganador del partido» → Match winner; «Juegos totales» → Total games; «Más de X» → Over X; «Menos de X» → Under X; superficies Hard/Clay/Grass/Carpet).
Un tipo de mercado nuevo sin traducción se mostraría en español: **hay que añadirlo a la tabla** en cuanto el motor lo publique.

Detrás del interruptor de idiomas: hoy `preview` ⇒ `noindex`, sin caché, fuera del sitemap y del hreflang hasta `en=on`.

## Cambios técnicos
- `src/qf/api/tenis_en.py` (nuevo): equivalencias español ↔ inglés registradas en `idiomas.py`; construcción del partido y del pilar en inglés; sitemap solo con `on`; rutas y redirecciones.
- `paginas/en_tenis_partido.html`, `paginas/en_tenis_cartelera.html` (nuevas), sobre `base_en.html`.
- `paginas/base_en.html`: enlace «Tennis» en la navegación inglesa.
- `seo.py`: el sitemap incluye `tenis_en.entradas_sitemap()` (vacío salvo `en=on`).
- `main.py`: **2 líneas** — `tenis_en` en el `from . import …` y `app.include_router(tenis_en.router)` tras `futbol_en.router`.

## Pruebas (`tests/test_tenis_en.py`, 17)
Apagado (404 y fuera del mapa), vista previa (`noindex`, sin caché), partido final (ganador por sets, Brier 0,184, mercados traducidos,
«Hit»/«Miss», superficie), **fallo del favorito dicho igual**, **la trampa del mercado** (ganador del mercado y sets no coinciden ⇒
«Result under review», sin acierto ni fallo), previo, cancelado y walkover, sin pronóstico/inexistente ⇒ 404, feed caído ⇒ 503, pilar,
redirección sin barra, mismos resultados y aciertos que el español, hreflang recíproco con `x-default`, selector, y texto inglés sin palabras
españolas (con enlaces ingleses o marcados `lang="es"`).

## Lo que NO incluye
- Páginas de equipo de NBA en inglés y tarjeta social en inglés (siguen pendientes).
- Jugadores como páginas propias (no existen en el español).

## Despliegue (cuando se apruebe; no es visible al público: el estado actual es `preview`)
1. Pre-vuelo: sha256 de `seo.py`, `base_en.html` y `main.py` de producción = los del último despliegue (`cb08ac8a`, o `futbol` si ya se desplegó); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de `tenis_en.py`, `seo.py`, `base_en.html`, `en_tenis_partido.html`, `en_tenis_cartelera.html`; `main.py` (CRLF, 2 líneas con `\r`, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar en el dominio real: `/en/tenis/` y un partido → 200 con `noindex` y `no-store`; el sitemap sin `/en/tenis`; el español idéntico; probabilidades inglesas = españolas.
4. El titular revisa el inglés y solo entonces `en=on`.

## Vuelta atrás
`en=off` cierra todo el inglés (≤ 20 s). Código: restaurar desde el respaldo del despliegue, borrar `tenis_en.py` y las dos plantillas, reiniciar fuera de :11 y :41.

## Riesgos
- Si el feed de tenis cae, el pilar y los partidos responden 503 con `Retry-After` (nunca 404).
- Un tipo de mercado nuevo sin traducción aparece en español hasta añadirlo a `ETIQUETAS`/`seleccion()`.
