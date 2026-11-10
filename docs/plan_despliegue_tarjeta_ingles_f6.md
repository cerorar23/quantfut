# Tarjeta para redes en inglés (F6, `/og/en/…`) — plan, 2026-11-09

## Qué cambia
Las páginas inglesas de partido y de pilar (NBA, fútbol y tenis) declaran ahora su propia imagen social (`og:image`) en inglés.
- Tarjetas de partido: `/og/en/{deporte}/{ruta}-{previa|final}.jpg`. Pilar: `/og/en/{deporte}/pilar.jpg`.
- Textos de la imagen en inglés: «FORECAST BEFORE THE MATCH», «FINAL», «HIT», «MISS», «Draw», «+18 · Statistical estimate, not a guarantee», «NBA predictions», etc.
- Etiquetas: NBA, FOOTBALL, TENNIS. Fechas: «Nov 8, 2026». Porcentajes sin espacio: «62%».
- La tarjeta de marca (`/og/marca.jpg`) sigue solo en español: las páginas de confianza y de equipo no declaran imagen (igual que antes).
- Las tarjetas españolas no cambian (mismos textos y mismo dibujo; `test_og.py` sigue en verde).

## Reglas
- `/og/en/…` responde 404 con el inglés en `off` (aunque la URL se conozca) y funciona en `preview` (la página ya lleva `noindex`).
- El estado de la imagen tiene que coincidir con el del partido (`previa` ↔ `final`), igual que en español: no se puede fabricar un «final».
- Sin Pillow, `disponible()` es False: las páginas inglesas no declaran `og:image` y la ruta responde 404. Nunca se rompe una página.

## Cambios técnicos
- `src/qf/api/og.py`: campo `idioma` en `Tarjeta`; `TEXTOS` por idioma; `DEPORTES_EN`, `TITULOS_PILAR_EN`; `url_pilar_en()`; ruta `/og/en/…` (`_tarjeta_en`).
- `nba_en.py`, `futbol_en.py`, `tenis_en.py`: `tarjeta()` y `tarjeta_de_la_url()` en inglés; cada página inglesa pasa `og_imagen`. `nba_en` expone `prob_local` numérico.
- Plantillas: ninguna.
- `main.py` y `seo.py`: sin cambios.

## Pruebas
`tests/test_og_en.py` (9): textos con las mismas claves y sin acentos; tarjetas en inglés de NBA (acierto), fútbol («Draw», fallo) y tenis (sets); imágenes con el inglés abierto, con el inglés apagado (404), pilar en inglés, la página inglesa declara su imagen, y la imagen española sigue igual. Regresión SEO completa: 449 en verde.

## Despliegue (cuando se apruebe)
Solo API. Archivos: `og.py`, `nba_en.py`, `futbol_en.py`, `tenis_en.py`. Sin `main.py`, sin plantillas, sin `seo.py`.
1. Pre-vuelo: sha256 de los cuatro archivos de producción = los del último despliegue de cada módulo; `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de los cuatro; `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar: `/og/en/nba/pilar.jpg` → 404 con `en=preview`? No: con `preview` la imagen sí se sirve (la página ya es `noindex`); con `off`, 404. Comprobar también `/og/nba/…` español sin cambios.
4. Los archivos JPEG se generan bajo demanda y se guardan en `/srv/quantfut/artifacts/og`; las claves nuevas (`en-…`) no pisan las españolas.

## Vuelta atrás
Restaurar los cuatro archivos desde el respaldo del último despliegue y reiniciar fuera de :11 y :41. Las imágenes `en-*.jpg` ya guardadas pueden borrarse del volumen sin efecto en el español.

## Riesgos
- Depende de Pillow dentro del contenedor (se instaló con pip el 9-nov; se pierde si el contenedor se recrea). Sin él, las páginas inglesas siguen funcionando sin imagen.
- Las tarjetas inglesas hacen las mismas consultas a los datos que las españolas; si los datos caen, 503 con `Retry-After`.
