# F6.4b — NBA en portugués (pt-BR): pilar, partidos y equipos — plan, 2026-11-10

## Qué es
- `/pt/nba/` (agenda), `/pt/nba/{slug}/` (partido con pronóstico sellado) y `/pt/nba/equipos/{equipo}/` (equipo, con el mismo umbral que el español: 5 pronósticos sellados en 45 días).
- Páginas independientes sobre `base_pt.html`, como el inglés. Mismos datos y reglas que el español (`nba_paginas.py`, `nba_equipos.py`); cambian la redacción, las cifras (coma decimal: `0,137`), el formato de fecha (`8 de novembro de 2026`), el glosario (mandante/visitante, campanha, sequência, descanso) y el idioma. El español no se toca.
- Enfrentamientos escritos como «x» (uso brasileño): «Chicago Bulls x Philadelphia 76ers».
- Detrás del interruptor de idiomas (`activos.txt`, clave `pt`): hoy `off` por defecto.

**Todavía no:** tarjetas sociales en portugués (F6.4e), fútbol (F6.4c), tenis (F6.4d), calibración y calculadora.

## Cambios técnicos
- `src/qf/api/nba_pt.py` (nuevo): equivalencias español ↔ portugués (se combinan con las del inglés gracias a `_equivalencias`), construcción del partido y del pilar, sitemap solo con `on`, rutas y redirecciones.
- `src/qf/api/nba_equipo_pt.py` (nuevo): equipos en portugués, mismo umbral y mismas reglas de indexación.
- Plantillas nuevas: `paginas/pt_nba_partido.html`, `paginas/pt_nba_cartelera.html`, `paginas/pt_nba_equipo.html`.
- `paginas/base_pt.html`: enlace «NBA» en la navegación portuguesa.
- `seo.py`: el sitemap incluye ambos módulos (vacíos mientras `pt` no esté `on`).
- `main.py`: **4 líneas** — `nba_pt` y `nba_equipo_pt` en el import, y `app.include_router` de cada uno tras `nba_equipo_en.router`.

## Pruebas
- `tests/test_nba_pt.py` (17 casos): apagado (404 y fuera del mapa), vista previa (`noindex`, sin caché), partido final con todas las cifras y frases (37%/63%, Brier 0,137, sequências, descanso, margen con coma), un erro dicho igual, partido previo, sin selo/inexistente ⇒ 404, motor caído ⇒ 503, pilar con datas em português, redirección sin barra, mismas cifras que el español en partidos y en equipos (con datos reales de equipos, no un índice vacío), equipo bajo umbral con `noindex`, hreflang recíproco con `x-default`, y texto sin palabras españolas exclusivas.
- Regresión SEO completa: **483 en verde**.

## Puntos que el titular debe revisar antes de `pt=on`
1. **El texto lo redactó el asistente, sin revisión humana.** Hace falta una persona de Brasil que lo lea (especialmente los términos «mandante», «campanha», «sequência» y «previsão»).
2. Igual que en F6.4a: términos y privacidad solo existen en español.
3. Los equipos solo serán indexables cuando superen el umbral; hoy, con el motor NBA desde el 2-nov, es probable que ninguno lo supere (igual que el español).

## Despliegue (cuando se apruebe; no es visible al público: el estado por defecto es `off`)
Archivos: `nba_pt.py`, `nba_equipo_pt.py`, las tres plantillas `pt_nba_*`, `base_pt.html`, `seo.py`, y `main.py` (4 líneas con `\r`).
1. Pre-vuelo: sha256 de `seo.py`, `base_pt.html` y `main.py` de producción = los del último despliegue (F6.2a y el correo); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp`; `main.py` con `patch_main.py` (CRLF, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar con `pt` ausente: `/pt/nba/` → 404; sitemap sin `/pt/nba`; español e inglés sin cambios.
4. Con `pt=preview`: `/pt/nba/` y un partido → 200 con `noindex`.
5. El titular lee el portugués y solo entonces `pt=on`.

## Vuelta atrás
`pt=off` cierra el portugués en ≤ 20 s. Código: restaurar `seo.py` y `main.py` desde el respaldo y borrar los módulos y plantillas nuevos; reiniciar fuera de :11 y :41.
