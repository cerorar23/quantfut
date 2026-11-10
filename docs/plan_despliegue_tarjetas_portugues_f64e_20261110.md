# F6.4e — Tarjetas para redes en portugués (`/og/pt/…`) — plan, 2026-11-10

## Qué es
Las páginas portuguesas de partido y de pilar (NBA, futebol y tênis) declaran su propia imagen social (`og:image`) en portugués:
- Partido: `/og/pt/{deporte}/{ruta}-{previa|final}.jpg`. Pilar: `/og/pt/{deporte}/pilar.jpg`.
- En la URL, el fútbol usa el segmento `futebol` (`/og/pt/futebol/…`); internamente es `futbol`, igual que en el resto del código.
- Textos de la imagen: «PREVISÃO ANTES DO JOGO», «FINAL», «ACERTO», «ERRO», «Empate», «+18 · Estimativa estatística, não uma garantia», «Previsões da NBA», «Previsões de futebol», «Previsões de tênis».
- Etiquetas: NBA, FUTEBOL, TÊNIS. Fechas: `8 de novembro de 2026`. Marcadores de tenis: `0 – 2 em sets`.
- Las tarjetas en español y en inglés no cambian: la ruta `/og/…` se generalizó a una sola función por idioma (`_tarjeta_idioma`) y las pruebas existentes siguen en verde.

## Reglas
- `/og/pt/…` responde 404 con `pt=off` (aunque la URL se conozca) y funciona en `pt=preview` (la página ya lleva `noindex`).
- El estado de la imagen coincide con el de la partida (`previa` ↔ `final`), igual que en español e inglés.
- Sin Pillow, las páginas portuguesas no declaran imagen y la ruta responde 404. Nunca se rompe una página.

## Cambios técnicos
- `src/qf/api/og.py`: `TEXTOS["pt"]`, `DEPORTES_PT`, `TITULOS_PILAR_PT`, `SEGMENTO` (segmento de URL → clave interna), `url_pilar_pt()`, y `_tarjeta_idioma()` que sustituye a `_tarjeta_en()`.
- `src/qf/api/nba_pt.py`: `tarjeta()`, `tarjeta_de_la_url()`, `prob_local` numérico, y `og_imagen` en el pilar y en el partido.
- `src/qf/api/futbol_pt.py` y `src/qf/api/tenis_pt.py`: lo mismo.
- Plantillas: ninguna. `main.py` y `seo.py`: sin cambios.

## Pruebas
- `tests/test_og_pt.py` (11): textos con las mismas claves en los tres idiomas; textos portugueses; tarjetas de NBA, fútbol (usa «Empate») y tenis; imágenes con el portugués abierto y apagado; imagen de fútbol con el segmento `futebol` (y `futbol` da 404); pilares; la página declara su imagen en portugués; las imágenes en inglés y en español siguen igual.
- Regresión SEO completa: **526 en verde**.

## Puntos que el titular debe revisar antes de `pt=on`
1. El texto de las tarjetas lo redactó el asistente, sin revisión humana (igual que el resto del portugués).
2. Pillow tiene que estar instalado en el contenedor (se instaló con pip el 9-nov; se pierde si el contenedor se recrea).

## Despliegue (cuando se apruebe; no es visible al público: el estado por defecto es `off`)
Solo API. Archivos: `og.py`, `nba_pt.py`, `futbol_pt.py`, `tenis_pt.py`. Sin `main.py` ni plantillas.
1. Pre-vuelo: sha256 de los cuatro archivos de producción = los del último despliegue de cada uno (`og.py` como en el despliegue del inglés de preview; `nba_pt.py`, `futbol_pt.py` y `tenis_pt.py` solo si ya están desplegados — si no, son nuevos); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de los cuatro; `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar con `pt` ausente: `/og/pt/nba/pilar.jpg` → 404; las tarjetas en español e inglés siguen 200.
4. Con `pt=preview`: `/og/pt/nba/pilar.jpg` → 200.

## Vuelta atrás
Restaurar los cuatro archivos desde el respaldo (o borrar los nuevos si no existían); reiniciar fuera de :11 y :41. Las imágenes `pt-*.jpg` del volumen pueden borrarse sin efecto en otros idiomas.
