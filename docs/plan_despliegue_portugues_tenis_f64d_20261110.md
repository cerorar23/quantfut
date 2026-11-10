# F6.4d — Tênis en portugués (pt-BR): pilar y partidos — plan, 2026-11-10

## Qué es
- `/pt/tenis/` (agenda) y `/pt/tenis/{torneo}/{slug}/` (partida con pronóstico sellado). La URL usa el mismo segmento `tenis` que el español (ASCII, sin acento).
- Páginas independientes sobre `base_pt.html`. Reutilizan la lógica del español (`tenis_paginas.py`): la salvaguarda de que el ganador del mercado y los SETS coincidan, el veredicto y el estado. El español no se toca.
- Etiquetas de mercado traducidas (tabla pequeña de los tipos que publica el motor): «Vencedor da partida», «Total de games», «Mais de X», «Menos de X». Superficies: quadra dura, saibro, grama, carpete. Resultados: Acerto, Erro, Reembolsado.
- Un tipo de mercado nuevo sin traducción se mostraría en español hasta añadirlo a `ETIQUETAS`/`seleccion()`.
- Detrás del interruptor de idiomas (`activos.txt`, clave `pt`): hoy `off` por defecto.

**Todavía no:** tarjetas sociales en portugués (F6.4e), calibración y calculadora.

## Cambios técnicos
- `src/qf/api/tenis_pt.py` (nuevo): equivalencias español ↔ portugués, construcción de partida y pilar, sitemap solo con `on`, rutas y redirecciones.
- Plantillas nuevas: `paginas/pt_tenis_partido.html`, `paginas/pt_tenis_cartelera.html`.
- `paginas/base_pt.html`: enlace «Tênis» en la navegación portuguesa.
- `seo.py`: el sitemap incluye `tenis_pt.entradas_sitemap()` (vacío mientras `pt` no esté `on`).
- `main.py`: **2 líneas** — `tenis_pt` en el import y `app.include_router(tenis_pt.router)` tras `futbol_pt.router`.

## Pruebas
- `tests/test_tenis_pt.py` (17 casos): apagado (404 y fuera del mapa), vista previa (`noindex`, sin caché), partida final (título, resultado por sets, error del favorito, Brier 0,184, mercados traducidos, Acerto/Erro, superficie), el error del favorito dicho igual, la trampa del mercado (no se anuncia acierto), previa, cancelada y walkover, sin pronóstico/inexistente ⇒ 404, datos caídos ⇒ 503, pilar, redirección sin barra, mismas cifras que el español, hreflang recíproco y texto sin palabras españolas exclusivas.
- Regresión SEO completa: **515 en verde**.

## Puntos que el titular debe revisar antes de `pt=on`
1. **El texto lo redactó el asistente, sin revisión humana.** Hace falta una persona de Brasil que lo lea, sobre todo los términos «vencedor da partida», «total de games», «piso»/«quadra dura» y «W.O.».
2. La salvaguarda de sets se hereda del español: si una partida tiene ganador del mercado y sets que no coinciden, la página no dice quién ganó.

## Despliegue (cuando se apruebe; no es visible al público: el estado por defecto es `off`)
Archivos: `tenis_pt.py`, las dos plantillas `pt_tenis_*`, `base_pt.html`, `seo.py`, y `main.py` (2 líneas con `\r`).
1. Pre-vuelo: sha256 de `seo.py`, `base_pt.html` y `main.py` de producción = los del último despliegue; `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp`; `main.py` con el parche (CRLF, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar con `pt` ausente: `/pt/tenis/` → 404; sitemap sin `/pt/tenis`; español e inglés sin cambios.
4. Con `pt=preview`: el pilar y una partida → 200 con `noindex`.
5. El titular lee el portugués y solo entonces `pt=on`.

## Vuelta atrás
`pt=off` cierra el portugués en ≤ 20 s. Código: restaurar `seo.py`, `base_pt.html` y `main.py` desde el respaldo, borrar `tenis_pt.py` y las plantillas nuevas; reiniciar fuera de :11 y :41.
