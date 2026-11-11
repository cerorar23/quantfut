# F6.3 — Calibración y calculadora de odd/cuota justa en inglés y portugués (pt-BR) — plan, 2026-11-10

## Qué es
Completa en código la fase F6 (`docs/plan_seo_redes_web_20261108.md`), añadiendo versiones completas en inglés (`en`) y portugués de Brasil (`pt-BR`) detrás de las compuertas existentes de `idiomas.py`:
- **Calibración:** `/en/calibration/` y `/pt/calibracao/` (más redirección 301 sin barra final). Misma generación automática desde `calibration_runs` y `/nba/v1/calibracion`, gráficos SVG accesibles sin JavaScript y veredicto honesto derivado de los datos.
  - Inglés (`en`): punto decimal (`0.2091`), coma de miles (`3,222`), porcentajes sin espacio (`45.8%`), fechas cortas en tabla (`Nov 9, 2026`) y largas (`November 9, 2026`), traducción de `estado_evidencia` (`descriptive`, `preliminary`, `certified`, `insufficient`).
  - Portugués (`pt-BR`): coma decimal (`0,2091`), punto de miles (`3.222`), porcentajes sin espacio (`45,8%`), fechas `DD/MM/AAAA` y largas (`9 de novembro de 2026`).
- **Calculadora de cuota/odd justa:** `/en/fair-odds-calculator/` y `/pt/calculadora-odd-justa/` (más 301 sin barra). Mismo módulo único `src/qf/api/static/cuota-justa.js` (mismo cálculo Shin / proporcional / potencia y tolerancia en la entrada `.` o `,`), detectando idioma desde `<html lang>` sin scripts en línea ni `connect-src`. Mantiene intacto el formato de salida español por defecto.
- **Navegación y enlaces internos:** actualizados `base_en.html`, `base_pt.html`, `en_methodology.html` y `pt_metodologia.html` para enlazar directamente a las nuevas rutas en lugar de apuntar a la calculadora española.

## Cambios técnicos
- `src/qf/api/calibracion.py`: tabla `_TEXTOS`, formateo por idioma (`_num`, `n3`, `n4`, `pct`, `entero`, `_fecha_tabla`, `_rango`), `svg_fiabilidad(..., idioma=...)`, `construir(..., idioma=...)`, `entradas_sitemap()` condicional por `idiomas.estado(...)`, rutas `/en/calibration/` y `/pt/calibracao/` protegidas por `idiomas.puerta()`.
- `src/qf/api/cuota_justa.py`: `_PAGINAS` (`es`, `en`, `pt`), `_NOMBRES_EJEMPLO`, `n2`/`pct`/`ejemplo` parametrizados por idioma, `entradas_sitemap()` condicional, rutas `/en/fair-odds-calculator/` y `/pt/calculadora-odd-justa/` con `paginas.CSP` (`script-src 'self'`).
- `src/qf/api/static/cuota-justa.js`: `idiomaBase`, `textosDe`, parámetro opcional `idioma = "es"` en `fmtNum`, `fmtPct` y `formatear` (con español por defecto para compatibilidad), `iniciar()` adaptado a `document.documentElement.lang`.
- Plantillas nuevas: `paginas/en_calibracion.html`, `paginas/pt_calibracao.html`, `paginas/en_cuota_justa.html`, `paginas/pt_cuota_justa.html`.
- Plantillas actualizadas: `paginas/base_en.html`, `paginas/base_pt.html`, `paginas/en_methodology.html`, `paginas/pt_metodologia.html`.
- Pruebas nuevas y actualizadas: `tests/test_f63_idiomas.py`, `tests/test_idiomas.py` (ajusta `/calibracion/` -> `/historial/` al existir versión inglesa), `frontend/cuota-justa.test.mjs`.

## Lo que sigue pendiente antes de abrir (`on`)
1. Revisión humana del inglés y del portugués (redacción generada por asistente) y verificación de la red de ayuda de Brasil en `/pt/jogo-responsavel/`.
2. Sin impacto mientras `en` esté en `preview` y `pt` en `off`: los idiomas apagados siguen devolviendo 404 y no aparecen en `/sitemap-paginas.xml` ni en el selector del español.

## Despliegue (cuando se apruebe)
1. Pre-vuelo: `sha256` de `calibracion.py`, `cuota_justa.py`, `static/cuota-justa.js` y plantillas `base_*.html`, `en_methodology.html`, `pt_metodologia.html`; respaldo con `SHA256SUMS`.
2. Copiar los archivos modificados y las cuatro plantillas nuevas al contenedor de la API (las rutas se registran desde `calibracion.py` y `cuota_justa.py`, sin cambios en `main.py`). El `?v=<hash>` de `/static/cuota-justa.js` invalida automáticamente la caché de Cloudflare.
3. Reiniciar `quantfut-api-1` fuera de `:11` y `:41`.
4. Comprobar `/en/calibration/` y `/en/fair-odds-calculator/` (en `preview`: 200, `X-Robots-Tag: noindex`, `no-store`) y `/pt/calibracao/` + `/pt/calculadora-odd-justa/` (en `off`: 404).

## Vuelta atrás
`en=off` / `pt=off` en `activos.txt` desactiva el acceso en ≤ 20 s; restauración de código con la copia de seguridad y reinicio de `quantfut-api-1`.
