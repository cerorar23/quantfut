# F6.1 — Idiomas: infraestructura e inglés de las páginas de confianza (plan, 2026-11-09)

## Alcance de esta entrega (y lo que NO es)
F6 del plan (§9) pide inglés y portugués. Esta primera entrega es **la infraestructura de idiomas y las tres páginas de confianza en inglés**
(`/en/methodology/`, `/en/responsible-gambling/`, `/en/about/`), por orden de dependencia: cualquier página inglesa de partido tendrá que enlazar a estas.

**No hay todavía páginas inglesas de NBA, fútbol ni tenis, ni de calibración ni de la calculadora, ni portugués.** Motivos:
- Las páginas de deporte se sirven dentro de la aplicación de una sola página, que pinta todo en español en cuanto carga el JavaScript: una versión inglesa que se vuelve española
  al cargar incumpliría la regla del plan (§9: «100 % del contenido en ese idioma»). Hace falta servirlas como páginas independientes en inglés (plantillas y textos de `nba_paginas.py`,
  `futbol_paginas.py`, `tenis_paginas.py` y `nba_equipos.py` con idioma) → F6.2.
- `/calibracion/` y la calculadora llevan formato numérico, textos en Python y JavaScript propios que hay que parametrizar por idioma → F6.3.
- Portugués (pt-BR) → F6.4, con el mismo mecanismo.

## Cómo funciona (`src/qf/api/idiomas.py`)
Cada idioma distinto del español tiene un **estado** que se cambia **sin reiniciar la API**, editando `/srv/quantfut/artifacts/idiomas/activos.txt` (se relee cada 20 s):

| Estado | Qué pasa |
|---|---|
| `off` (por defecto, y si el archivo no existe) | `/en/…` responde 404; ni sitemap ni selector ni hreflang; el español no lo menciona. |
| `preview` | `/en/…` responde 200 con `noindex` (meta + `X-Robots-Tag`), `Cache-Control: no-store`; **no** está en el sitemap, no hay hreflang y el español no enlaza al inglés. Es para que el titular revise el texto en producción. |
| `on` | Indexable. hreflang recíproco en el **sitemap** con `xhtml:link` (es, en, `x-default` → español, absolutos y autorreferentes); selector de idioma con enlaces normales en la cabecera de ambas versiones. |

Sin redirección por IP ni por `Accept-Language` (una prueba lo comprueba). El español sigue en la raíz, sin cambios de URL.
`base.html` pasa a tener bloques (`lang`, `og_locale`, `nav`, `pie`, `saltar`, `revision`…) con el español como valor por defecto: **las páginas en español salen idénticas** (las pruebas SEO previas siguen en verde);
`base_en.html` los sobrescribe. La tarjeta social de marca se omite en inglés (está escrita en español) y la tarjeta es `summary`.

## Lo que el titular debe saber antes de abrir el inglés (`on`)
1. **El texto inglés lo ha redactado el asistente y no lo ha leído una persona**: el plan exige una muestra revisada (§9). Por eso el estado inicial es `off` y el paso intermedio es `preview`.
2. **Los términos y la política de privacidad solo existen en español**; el pie inglés los enlaza como «Terms (in Spanish)» y «Privacy (in Spanish)». Si se abre el inglés a público de EE. UU. o Reino Unido
   conviene traducirlos tras revisión legal (§11); el plan no lo da por hecho.
3. Las páginas inglesas enlazan además a la calculadora y al historial de la portada, que siguen en español, marcados con `lang="es"` (una prueba exige que todo enlace del inglés vaya a una página inglesa o esté marcado).
4. Los teléfonos de ayuda son los mismos que en español (EE. UU., Reino Unido, España, México); no se añadieron números nuevos que no se hayan verificado.
5. Casas de apuestas por nombre: la metodología no nombra ninguna casa.

## Pruebas
`tests/test_idiomas.py` (25): lector de estados; `off` sin rastro; `preview` noindex y sin sitemap; `on` con cabeza completa, hreflang recíproco/absoluto/con `x-default`, selector en los dos sentidos, sin redirección por idioma,
enlaces internos, **el texto inglés no trae palabras vacías españolas ni caracteres acentuados**, mismas garantías de contenido (no supera al mercado, sin registro externo, teléfonos, razón social), mismos teléfonos/correo/URLs externas que el español.

## Despliegue (cuando se apruebe; el estado inicial es `off`, así que no cambia nada visible)
Solo API. Archivos: nuevos `src/qf/api/idiomas.py`, `paginas/{base_en,en_methodology,en_responsible_gambling,en_about}.html`; modificados `paginas.py`, `seo.py`, `paginas/base.html`.
`main.py` **no cambia** (las rutas nuevas cuelgan del router de `paginas.py`).
1. Pre-vuelo: sha256 de los archivos que se sobrescriben = los de `d6ff0ef4` (`paginas.py`, `seo.py`, `base.html`); `/health` 200; respaldo con `SHA256SUMS`.
2. `docker cp` + `docker restart quantfut-api-1` fuera de los minutos :11 y :41 (hora del servidor).
3. Verificar en el dominio real: con el archivo ausente, `/en/methodology/` → 404, el sitemap no cambia, el español idéntico (`/metodologia/` mismo HTML salvo nada) y regresión de rutas.
4. Crear `activos.txt` con `en=preview` (en el host: `/srv/quantfut/artifacts/idiomas/`), comprobar que el contenedor lo ve y que `/en/…` responde 200 con `noindex`.
5. El titular revisa las tres páginas. Solo entonces, `en=on`: comprobar hreflang en el sitemap, el selector, y que IndexNow envía las URLs nuevas.

## Vuelta atrás
Para cerrar el inglés basta con `en=off` en `activos.txt` (≤ 20 s). Para quitar el código: restaurar los 3 archivos desde `~/respaldos/idiomas_f61_<fecha>/` y borrar los 5 nuevos del contenedor; reiniciar fuera de :11 y :41.

## Riesgos
- Si `activos.txt` no se puede leer, el inglés queda `off` (falla cerrando, no abriendo).
- Una vez en `on`, Google puede tardar semanas en emparejar las versiones: se mira la cobertura de las URLs `/en/` en Search Console.
