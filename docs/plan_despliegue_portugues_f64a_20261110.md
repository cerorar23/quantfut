# F6.4a — Portugués (pt-BR): infraestructura de tres idiomas y las tres páginas de confianza — plan, 2026-11-10

## Qué es
Primera entrega de F6.4 (portugués de Brasil). Incluye:
- **Infraestructura de tres idiomas.** El hreflang ahora combina todas las versiones de una página (español, inglés y portugués) con `x-default` → español. Antes, cada familia de páginas devolvía solo su propio par.
- **Tres páginas de confianza en portugués,** con slugs en portugués: `/pt/metodologia/`, `/pt/jogo-responsavel/`, `/pt/sobre-nos/`. Tienen el mismo contenido y las mismas garantías que las versiones en español e inglés (no supera al mercado, no garantiza resultados, sin registro externo, razón social, teléfonos y correo iguales).
- Detrás del interruptor de idiomas (`activos.txt`): hoy `off` por defecto. Desplegarlo no cambia nada visible.

**Todavía no:** NBA, fútbol, tenis y equipos en portugués; tarjetas sociales en portugués; calibración y calculadora (F6.3) en ningún idioma extra. Serán F6.4b–F6.4e.

## Cambios técnicos
- `src/qf/api/idiomas.py`: `_equivalencias` combina el grupo de la página y los aportes de todos los traductores.
- `src/qf/api/paginas.py`: `PAGINAS_PT`, `MONTHS_PT` (fechas «10 de novembro de 2026»), `INICIO["pt"]`, entrada en `EN_POR_IDIOMA`.
- Plantillas nuevas: `paginas/base_pt.html`, `paginas/pt_metodologia.html`, `paginas/pt_jogo_responsavel.html`, `paginas/pt_sobre_nos.html`.
- `tests/test_idiomas_pt.py` (nuevo), y dos correcciones de pruebas existentes (ver abajo).

## Puntos que el titular tiene que revisar antes de `pt=on`
1. **El texto portugués lo redactó el asistente, sin revisión humana.** Hace falta una persona de Brasil que lo lea.
2. **Teléfonos de Brasil.** La fila de Brasil no lista ningún teléfono: remite al SUS, al CAPS de la ciudad y a Jogadores Anônimos, sin URL. Los demás países usan los mismos números que la versión en español (España, México y Estados Unidos), y el Reino Unido, el mismo sitio que en inglés. **No se han verificado en esta entrega** y ninguna cifra nueva se ha añadido. Antes de abrir el portugués conviene confirmar la red de ayuda brasileña.
3. **Términos y privacidad** solo existen en español; el pie los marca «(em espanhol)». Igual que con el inglés, la traducción necesita revisión legal para público de Brasil.
4. La versión en portugués no lleva tarjeta social propia: las páginas de confianza no declaran imagen.

## Pruebas
- `tests/test_idiomas_pt.py` (17 con sus parametrizaciones): apagado (404, fuera del mapa), vista previa (`noindex`, sin caché), cabeza (`pt-BR`, `pt_BR`, canonical, robots, título, descripción de 120–165 caracteres, JSON-LD), fechas en portugués, títulos únicos entre los tres idiomas, hreflang con español y portugués sin inglés, hreflang con los tres, selector, sin redirección por idioma, sin barra, texto sin palabras españolas exclusivas, garantías de contenido, y teléfonos y correo iguales a los del español.
- Regresión SEO completa: **466 en verde**.

## Correcciones de pruebas existentes (no de la página)
- `tests/test_futbol_paginas.py` (y por consecuencia `tests/test_futbol_en.py`): la prueba del sitemap usaba la agenda del **día real**, mientras que sus datos son del 8-nov. Desde el 10-nov fallaba en `origin/main` (no por esta rama). Ahora fija el día al de `AHORA`.
- `tests/test_rutas_web.py`: el prefijo `pt` se declara como página pública, igual que `en`.

## Despliegue (cuando se apruebe; no es visible al público: el estado por defecto es `off`)
1. Pre-vuelo: sha256 de `idiomas.py`, `paginas.py` y `paginas/base.html` de producción = los del último despliegue (`idiomas.py` y `base.html`, F6.2a; `paginas.py`, CSP del correo); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de `idiomas.py`, `paginas.py` y las cuatro plantillas nuevas (`base_pt.html`, `pt_*.html`). Sin `main.py`: las rutas se registran desde `paginas.py`.
3. `docker restart quantfut-api-1` fuera de :11 y :41.
4. Verificar con el archivo `activos.txt` sin `pt`: `/pt/metodologia/` → 404; sitemap sin `/pt/`; las páginas en español y en inglés sin cambios.
5. Con `pt=preview` (después): las tres páginas → 200, `noindex`, `no-store`.
6. El titular lee el portugués y solo entonces `pt=on`.

## Vuelta atrás
`pt=off` en `activos.txt` cierra el portugués en ≤ 20 s. Código: restaurar `idiomas.py` y `paginas.py` desde el respaldo y borrar las cuatro plantillas nuevas; reiniciar fuera de :11 y :41.
