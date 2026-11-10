# F6.4c — Futebol en portugués (pt-BR): pilar y partidos — plan, 2026-11-10

## Qué es
- `/pt/futebol/` (agenda de los días -1 a +3) y `/pt/futebol/{competição}/{slug}/` (partido con pronóstico generado antes del inicio).
- Páginas independientes sobre `base_pt.html`, como el inglés y la NBA en portugués. Reutilizan los datos y las reglas del español (`futbol_paginas.py`, `futbol_datos.py`): el veredicto, la forma, la clasificación y el cara a cara. El español no se toca.
- Glosario: mandante/visitante (home/away), forma V/E/D (vitória, empate, derrota), classificação (standings), confronto direto (head to head), previsão (forecast). Los nombres de competición y de equipo se dejan como están.
- Cifras con coma decimal; posiciones ordinales `2º`; fechas `8 de novembro de 2026`.
- **Una sola URL portuguesa para el fútbol:** `/pt/futebol/…`. Un único helper (`ruta_pt`) genera todas las rutas para que el hreflang y los enlaces coincidan.
- Detrás del interruptor de idiomas (`activos.txt`, clave `pt`): hoy `off` por defecto.

**Todavía no:** tenis (F6.4d), tarjetas sociales en portugués (F6.4e), calibración y calculadora.

## Cambios técnicos
- `src/qf/api/futbol_pt.py` (nuevo): equivalencias español ↔ portugués (combinadas con las demás por `_equivalencias`), construcción del partido y del pilar, sitemap solo con `on`, rutas y redirecciones.
- Plantillas nuevas: `paginas/pt_futbol_partido.html`, `paginas/pt_futbol_cartelera.html`.
- `paginas/base_pt.html`: enlace «Futebol» en la navegación portuguesa.
- `seo.py`: el sitemap incluye `futbol_pt.entradas_sitemap()` (vacío mientras `pt` no esté `on`).
- `main.py`: **2 líneas** — `futbol_pt` en el import y `app.include_router(futbol_pt.router)` tras `nba_equipo_pt.router`.

## Pruebas
- `tests/test_futbol_pt.py` (15 casos): apagado (404 y fuera del mapa), vista previa (`noindex`, sin caché), partido final (título, marcador, error del favorito, Brier 1,138, forma `VVDEV`/`DDEVD`, posiciones `2º`/`9º`, cara a cara con plural correcto), partido previo con modelo propio y con mercado como referencia, sin pronóstico/inexistente ⇒ 404, datos caídos ⇒ 503, pilar, redirección sin barra, mismas cifras y aciertos que el español, hreflang recíproco (pilar y dos partidos), selector, y texto sin palabras españolas exclusivas.
- Regresión SEO completa: **498 en verde**.

## Puntos que el titular debe revisar antes de `pt=on`
1. **El texto lo redactó el asistente, sin revisión humana.** Hace falta una persona de Brasil que lo lea, sobre todo: «previsão», «mandante», «classificação» y «confronto direto».
2. El pie de página y los enlaces a la agenda y al histórico en español siguen en español (marcados `lang="es"`).
3. Como en el español, los partidos con pronóstico se generan en la corrida diaria de las 03:00 (hora de México); la página aparece cuando el pronóstico existe.

## Despliegue (cuando se apruebe; no es visible al público: el estado por defecto es `off`)
Archivos: `futbol_pt.py`, las dos plantillas `pt_futbol_*`, `base_pt.html`, `seo.py`, y `main.py` (2 líneas con `\r`).
1. Pre-vuelo: sha256 de `seo.py`, `base_pt.html` y `main.py` de producción = los del último despliegue; `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` de los archivos; `main.py` con el parche (CRLF, `ast.parse`); `docker restart quantfut-api-1` fuera de :11 y :41.
3. Verificar con `pt` ausente: `/pt/futebol/` → 404; sitemap sin `/pt/futebol`; español e inglés sin cambios.
4. Con `pt=preview`: el pilar y un partido → 200 con `noindex`.
5. El titular lee el portugués y solo entonces `pt=on`.

## Vuelta atrás
`pt=off` cierra el portugués en ≤ 20 s. Código: restaurar `seo.py`, `base_pt.html` y `main.py` desde el respaldo, borrar `futbol_pt.py` y las plantillas nuevas; reiniciar fuera de :11 y :41.
