# Plan SEO y redes sociales para toda la web — pronosticosdeportivos.pro

Fecha: 8-nov-2026. Estado: **borrador para que lo apruebe el titular**. No se ha tocado código.

Este documento corrige y completa el «Plan Arquitectónico» propuesto por el titular. Cada
corrección cita la documentación oficial leída el 8-nov (Google Search Central, Meta, X).
Donde una fuente oficial no dice nada, se indica como práctica habitual, no como regla.

---

## 0. Punto de partida (comprobado el 8-nov en producción y en el repo)

| Hecho | Consecuencia para el SEO |
|---|---|
| La web es una sola página con rutas `#` (`location.hash` en `frontend/app.js`); el HTML que sirve `/` es `<div id="app"></div>` vacío. | Google dice «don't use fragments to load different page content»: hoy **solo existe una URL indexable** (`/`). Inicio, Partidos, Picks, Historial, Alta, Parley, Escalera, Paquetes, Planes y Cuenta son invisibles para el buscador. |
| No hay etiquetas `og:`, `twitter:`, `canonical` ni JSON-LD. | WhatsApp, Facebook, Telegram, X y LinkedIn leen el HTML sin ejecutar JavaScript: cualquier enlace compartido sale sin imagen y con el título genérico. |
| `/sitemap.xml` → 404. `robots.txt` es solo el bloque de «content signals» de Cloudflare, sin reglas ni línea `Sitemap:`. | Google no tiene mapa del sitio. |
| `/metodologia`, `/historial`, etc. devuelven 404 **en JSON** (`application/json`). | Los errores tienen que ser páginas HTML con estado 404 real. |
| Legal vive en `/legal/terminos`, `/legal/privacidad`, `/legal/eliminar-cuenta`. | Se conservan esas URLs. |
| HSTS ya activo (`max-age=31536000`, sin `includeSubDomains` ni `preload`), `X-Frame-Options: DENY`, Cloudflare delante. | Parte de la Fase 6.4 ya está hecha. |
| El Pixel de Meta (`frontend/meta-pixel.js`) ya tenía un aviso con Rechazar/Aceptar, pero en modo opt-out (decisión del titular, 15-oct): el Pixel disparaba `PageView` antes de elegir y un «Rechazar» solo se guardaba en el navegador, mientras el servidor seguía enviando a Meta los eventos de registro y compra (CAPI). *(Corrección del 8-nov: la primera versión de este plan decía «sin banner», lo cual era inexacto.)* | Incumple el consentimiento previo que exige la UE/Reino Unido (ya hoy, con tráfico de España) y no respetaba un rechazo. **Corregido en F0** (rama `seo/f0-consentimiento`, §10). |
| No hay página de metodología ni de juego responsable en la web; no hay aviso +18. | Es lo primero que mira un evaluador de calidad en un tema YMYL. |
| La web solo está en español; la app ya tiene los 6 idiomas. | Se puede reutilizar el glosario y el proceso de traducción de la app. |
| «Pinnacle» aparece 21 veces en la web. | Mostrar casas de apuestas por su nombre puede contar como publicidad de juego en varios países (ver §11). |
| El frontend en vivo sale de la rama `docs/deploy-estado-mercados`, no de `main` (ver memoria y DEPLOYS.md). | Antes de construir nada hay que alinear `main` con lo que corre, o el primer despliegue SEO pisará la web. |

---

## 1. Errores del plan original y su corrección

| # | Lo que dice el plan | Lo que dice la documentación | Corrección |
|---|---|---|---|
| 1 | IndexNow para «avisar a los motores» al publicar. | IndexNow lo usan Bing, Yandex, Naver, Seznam y Yep. **Google no lo admite.** | Mantenerlo (es barato y Bing alimenta a Copilot y a otros buscadores), pero para Google la vía es: sitemap con `lastmod` verídico + enlace desde la portada (que Google rastrea a menudo). |
| 2 | (Tentación habitual) usar la Indexing API de Google. | «The Indexing API can only be used to crawl pages with either JobPosting or BroadcastEvent embedded in a VideoObject.» | **No usarla.** Usarla para partidos es abuso de la API. |
| 3 | `<lastmod>` «actualizado por minuto». | Google lo usa solo «if it's consistently and verifiably … accurate» y debe reflejar «the last significant update». Cambiar fechas sin cambio real es una señal de contenido hecho para buscadores. | `lastmod` = instante del último cambio real: publicación del pronóstico sellado, cambio de estado (en juego, final, aplazado), liquidación. Nunca un reloj. |
| 4 | Sitemap «today» + «archive». | Google ignora `priority` y `changefreq`; límite 50.000 URLs / 50 MB; índice de sitemaps permitido. | Índice `/sitemap.xml` → `sitemap-hoy.xml` (próximas 48 h), `sitemap-paginas.xml` (pilares, ligas, equipos, metodología), `sitemap-AAAA-MM.xml` por mes para partidos terminados. Así Search Console mide cada bloque por separado. |
| 5 | «Googlebot revisa el RSS más rápido que el sitemap». | Google acepta RSS 2.0 y Atom 1.0 como sitemap y recomienda WebSub para los feeds; no promete más rapidez. El ping de sitemaps ya no existe (la página solo lista Search Console, su API, `robots.txt` y WebSub). | Feed Atom de las próximas 24 h, enviado como sitemap y con WebSub. Sin ping. |
| 6 | Canonical `…/celtics-vs-lakers-hoy/`, URL `…/celtics-vs-lakers-28-octubre-2026/` y migas con una tercera ruta. | Una página debe tener un único canonical estable. | **Una sola URL por partido, con fecha y para siempre** (§3). Nada de «-hoy» en el slug. |
| 7 | Título de 45-55 caracteres (los ejemplos tienen 65-70). | Google no fija un número de caracteres; corta por ancho. | Lo importante al principio y ≈ 60 caracteres como guía. Sin emojis en `<title>` (sí se permiten en `og:title`). |
| 8 | «Edge +8,6 %», «valor», «pick recomendado» en título y OG. | Discover: evitar clickbait y sensacionalismo. YMYL: «highly accurate and consistent with established expert consensus». Meta exige autorización para anuncios cuya página de destino promueva apuestas. | Titular con la probabilidad y el partido («Celtics vs Lakers: 63,8 % de probabilidad local según el modelo»). El «edge» va dentro de la página, con su explicación. Es coherente con la decisión del 30-oct: probabilidad calibrada, el mercado como referencia. |
| 9 | `SportsEvent` para obtener resultado enriquecido. | El resultado enriquecido de eventos exige eventos «bookable to the general public», con `location` y `address`, y no admite contenido que no sea el propio evento. Una página de pronóstico no es la página del evento. | Usar `SportsEvent` solo como descripción del tema (`WebPage` → `about`), **sin esperar fragmentos enriquecidos**, y con datos reales. Si no tenemos el estadio verificado, no se inventa (§7). |
| 10 | Twitter Cards «(Telegram)». | Telegram lee Open Graph; X lee `twitter:*` y recurre a `og:` si faltan. | Open Graph completo para todos + `twitter:card` para X (§6). |
| 11 | WhatsApp: imagen ≤ 300 KB. | No hay documentación oficial pública de WhatsApp sobre esto. | Mantener ≈ 300 KB como regla práctica, no como norma oficial. |
| 12 | Imagen 1200×630 «para Discover». | Discover pide ≥ 1200 px de ancho, más de 300.000 píxeles, **16:9** y `max-image-preview:large`; no exige datos estructurados. | Dos recortes de la misma plantilla: 1200×630 para `og:image` y 1200×675 (16:9) como imagen principal de la página y del JSON-LD. |
| 13 | «Pogo-sticking», «el clic detiene el reloj de rebote». | La documentación habla de experiencia de página en conjunto; no confirma ningún reloj de permanencia. | Construir herramientas porque sirven al lector, no para engañar a una métrica. |
| 14 | Calculadora de Kelly «cuántos dólares apostar». | YMYL + juego responsable: decirle a alguien cuánto dinero apostar es lo más arriesgado que puede publicar la web. | Sustituir por una **calculadora de cuota justa ↔ probabilidad** (incluido el margen de la casa) y por el gráfico de calibración. Sin importes de apuesta. |
| 15 | Enlazar automáticamente cada mención de un equipo. | Las guías de enlazado piden enlaces útiles y texto de anclaje natural. | Enlazar la primera mención de cada equipo/liga, no todas. |
| 16 | Blogabet/Betstamp/Tipstrr «para un perfil dofollow». | Buscar enlaces para posicionar es lo que describe la política de enlaces; además esos perfiles suelen ser `nofollow`/`ugc`. | Usarlos como **verificación externa del historial** (confianza), no como enlaces. |
| 17 | README del GitHub propio. | — | El repositorio `cerorar23/quantfut` es **privado**: un enlace desde ahí no lo ve nadie. Solo serviría un repositorio público aparte (metodología o datos abiertos), si el titular lo quiere. |
| 18 | Reddit (r/sportsbook, r/nba_analytics). | Política de spam: enlaces optimizados en foros = enlace spam. | Solo estudios con valor por sí mismos, respetando las normas de cada subforo (r/sportsbook limita la autopromoción); el enlace a la fuente al final, sin anclas optimizadas. |
| 19 | HSTS `preload` «Google te ve incorruptible». | HTTPS es la señal; HSTS/CSP no posicionan. | Son buenas por seguridad. `preload` se revierte con mucha dificultad e `includeSubDomains` rompe cualquier subdominio sin HTTPS: revisar los subdominios antes. |
| 20 | CSP `default-src 'self'`. | — | Rompería el Pixel de Meta, Google Sign-In, Whop, Firebase y Cloudflare. Empezar con `Content-Security-Policy-Report-Only` y la lista real de orígenes (§10). |
| 21 | hreflang `es-MX`/`es-ES` (6.1) y a la vez 6 idiomas (7). | Solo código de idioma está permitido (`es`); **`es-419` no está soportado**; el país solo no vale; deben ser recíprocos, absolutos y con `x-default`. | Una versión `es` mientras el texto sea el mismo para todos los países. Variantes regionales solo cuando el contenido cambie de verdad (p. ej. «momios» en México). |
| 22 | Slugs traducidos «premiados por Google». | La documentación no dice que se premien. | Opcional. Recomendación: mismo slug tras el prefijo de idioma (`/en/nba/celtics-vs-lakers-2026-10-28/`): menos errores y hreflang más simple. |
| 23 | Traducir los 6 idiomas con un LLM «en la misma llamada». | Spam: «generate many pages without adding value» y traducir en masa con poco valor = abuso de contenido a escala. Traducir solo la plantilla y dejar el contenido en otro idioma da mala experiencia. | Una versión se publica solo si **todo** su contenido está en ese idioma y tiene datos propios. Despliegue por fases y muestra revisada por idioma (§9). |
| 24 | Caja de autor «[Tu nombre], analista…». | «Who»: autoría clara; las credenciales o perfiles inventados son engaño. | Persona real si el titular quiere firmar; si no, `Organization` + metodología + cadena de hashes verificable. Nunca un autor ficticio. |
| 25 | Informe de 120-150 palabras. | «We don't [have a preferred word count].» | Sin objetivo de palabras: el texto dice lo que dicen los datos y se detiene. Aviso «How»: texto generado automáticamente a partir de los datos del modelo. |
| 26 | «Brier Score residual: 0,18» por partido. | — | En un partido el Brier es (p − resultado)²; rotularlo «Brier de este pronóstico» y mostrar la calibración acumulada en el historial, que es lo que da confianza. |
| 27 | Juego responsable: Jugar Bien, FEJAR, BeGambleAware. | — | Son de España y Reino Unido. Recursos por versión y país (§11). |
| 28 | Imágenes OG con los escudos. | CLAUDE.md: las marcas de equipos y ligas se revisan aparte; el derecho a la imagen de jugadores también. | Plantilla tipográfica con colores y nombres, sin escudos ni fotos hasta tener la licencia. |
| 29 | Next.js / `.htaccess` / `next.config.js`. | — | No es nuestra pila. Un único FastAPI sirve la web (decisión del 23-sep): plantillas en el servidor dentro del mismo FastAPI y cabeceras en el middleware o en Cloudflare. |
| 30 | «En vivo» durante el partido. | — | Solo si hay marcador real en vivo; si no, «En juego, resultado pendiente». |

---

## 2. Mapa de TODAS las páginas de la web

Español en la raíz (`/`), sin prefijo. Otros idiomas con prefijo (`/en/…`) cuando se aprueben (§9).

| Tipo | URL | Indexar | En sitemap | Datos estructurados | Imagen social |
|---|---|---|---|---|---|
| Portada | `/` | sí | paginas | `WebSite`, `Organization`, `BreadcrumbList` | marca 1200×630 |
| Pilar deporte | `/futbol/`, `/nba/`, `/tenis/` | sí | paginas | `CollectionPage`, `BreadcrumbList` | por deporte |
| Liga / torneo | `/futbol/laliga/`, `/futbol/champions/`, `/tenis/roland-garros/` | sí | paginas | `CollectionPage`, `BreadcrumbList` | por liga, sin logotipo |
| Equipo | `/futbol/equipos/real-madrid/`, `/nba/equipos/boston-celtics/` | sí, con umbral (§3.3) | paginas | `WebPage` + `about: SportsTeam` | plantilla equipo |
| Jugador de tenis | `/tenis/jugadores/carlos-alcaraz/` | sí, con umbral | paginas | `WebPage` + `about: Person` | sin foto |
| Partido | `/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/`, `/futbol/laliga/real-madrid-vs-sevilla-2026-11-09/`, `/tenis/atp-finals/sinner-vs-alcaraz-2026-11-12/` | sí, desde que el pronóstico está sellado | hoy → mes | `WebPage` + `about: SportsEvent`, `BreadcrumbList` | por partido y por estado |
| Herramientas del día | `/alta-probabilidad/`, `/parley-del-dia/`, `/reto-escalera/`, `/pronosticos/` (antes «Picks»), `/partidos/` | sí | paginas | `CollectionPage` | por herramienta |
| Historial | `/historial/`, `/historial/futbol/`, `/historial/nba/`, `/historial/tenis/` | sí | paginas | `Dataset` (solo si hay descarga real de datos) | gráfico de calibración |
| Verificación | `/verificacion/` (cómo comprobar la cadena de hashes) | sí | paginas | `WebPage` | — |
| Confianza | `/metodologia/` (+ `/metodologia/futbol/`, `/nba/`, `/tenis/`), `/sobre-nosotros/`, `/juego-responsable/`, `/contacto/` | sí | paginas | `AboutPage`, `ContactPage` | marca |
| Comercial | `/planes/`, `/paquetes/` | sí | paginas | ninguno con precio hasta que el precio sea siempre exacto | marca |
| Legal | `/legal/terminos`, `/legal/privacidad`, `/legal/eliminar-cuenta` | sí | paginas | — | — |
| Cuenta y flujos | `/cuenta/`, `/verificar`, `/restablecer`, `/i/{code}`, pago | **no** (`noindex`) | no | — | — |
| Panel | `/control/*` | **no** (`X-Robots-Tag: noindex` + login) | no | — | — |
| API | `/app/v1/*`, `/mobile/v1/*`, `/nba/v1/*`, `/web/*` (JSON), `/escudos/*` | **no** (`X-Robots-Tag: noindex`) | no | — | — |
| Errores | cualquier ruta desconocida | — | — | — | — |

Reglas para todo el mapa:

- **Rutas viejas con `#`.** Un fragmento no llega al servidor: el JavaScript de la portada traduce `/#historial` → `location.replace('/historial/')` para no romper enlaces ya compartidos.
- **404 de verdad.** Página HTML con estado 404 (no JSON, no 200 con «no encontrado»).
- **Una barra final siempre** (`/nba/`), y 301 desde la versión sin barra.
- **No bloquear en `robots.txt` lo que lleva `noindex`**: si se bloquea, Google no ve el `noindex`. `robots.txt` solo añade `Sitemap: https://pronosticosdeportivos.pro/sitemap.xml`. El bloque de «content signals» de Cloudflare es decisión del titular (§12).
- **Navegación con `<a href>` reales** (Google lo pide para descubrir enlaces); los botones `data-route` actuales no se rastrean.

---

## 3. URL de partido y ciclo de vida

### 3.1 Formato

`/{deporte}/[{competición}/]{local}-vs-{visitante}-{AAAA-MM-DD}/` con la fecha local del estadio.
Si un partido se aplaza y cambia de día: 301 de la URL vieja a la nueva y la página explica el cambio.

### 3.2 Estados

| Estado | Qué muestra | `robots` | `lastmod` cambia | Imagen social |
|---|---|---|---|---|
| Sin pronóstico sellado | la página no existe (404) o no se enlaza | — | — | — |
| Publicado (sellado) | probabilidades por mercado, cuota de referencia, hora del sello y hash, bajas, contexto | index | sí (al sellar) | `…/og/{partido}-previa.jpg` |
| En juego | estado y, si hay, marcador | index | sí | igual |
| Final y liquidado | resultado, acierto/fallo de **todos** los pronósticos de ese partido, Brier del pronóstico, enlace al historial | index | sí | `…/og/{partido}-final.jpg` (URL nueva) |
| Aplazado / suspendido / cancelado | estado y explicación; los pronósticos sellados no se tocan | index | sí | igual |

Garantías que no se negocian:

- La web **solo lee** lo ya sellado. La generación de páginas va después de `predecir → seleccionar → sellar → publicar` (`publish/daily.py`) y no lo reordena.
- Lo sellado nunca se edita en la página: se muestra igual que en la cadena, con el hash para comprobarlo.
- Los fallos se muestran igual que los aciertos. Es la prueba de confianza más fuerte que tiene la web.
- **Contenido VIP:** nunca va en el HTML público, ni oculto ni difuminado con CSS (el difuminado actual debe venir de datos que el servidor no envía). Así no hay encubrimiento posible y no hace falta marcado de muro de pago. Si algún día se sirve el contenido completo a Google y no al visitante, entonces es obligatorio `isAccessibleForFree: false` con `hasPart`/`cssSelector` (solo selectores de clase).
- Recomendación de confianza: cuando el partido termina, el pick VIP se revela en el historial (decisión del titular, §13).

### 3.3 Evitar páginas zombi (index bloat)

- Solo hay página de partido si hay pronóstico sellado. El tenis tiene miles de partidos al año: solo los que el motor publica.
- Equipo/jugador indexable solo con ≥ 5 pronósticos sellados en los últimos 12 meses (umbral a revisar); por debajo, `noindex` y fuera del sitemap.
- Páginas de herramientas (Parley, Escalera, Alta) son pilares que cambian cada día; los días pasados viven dentro del historial, no como páginas sueltas por fecha.
- Revisar cada mes en Search Console «Descubierta: actualmente sin indexar» y «Rastreada: actualmente sin indexar»; si crece, subir umbrales.

---

## 4. Renderizado

- **HTML completo desde el servidor** para todas las páginas indexables: plantillas en el mismo FastAPI (Jinja2), con los datos ya en el HTML. Sin esto ninguna otra fase funciona: ni Google ni ningún bot de redes sociales ejecuta de forma fiable el JavaScript actual.
- El JavaScript existente queda para lo interactivo (filtros, cuenta, compras, pestañas), con rutas por History API, no `#`.
- `title`, `description`, `canonical`, `robots`, `og:*` y JSON-LD salen del servidor, nunca inyectados con JavaScript (Google: el `noindex` cambiado por JS puede no procesarse).
- Caché en Cloudflare de las páginas públicas con vida corta (p. ej. 60 s) y purga al sellar o liquidar; las páginas con sesión no se cachean.
- Comprobar con la Inspección de URLs de Search Console que el HTML renderizado contiene las probabilidades.

---

## 5. Plantilla del `<head>` (corregida)

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Celtics vs Lakers (28 oct): pronóstico NBA y probabilidades | QuantFut</title>
  <meta name="description" content="El modelo da un 63,8 % al local frente al 58,1 % que implica la cuota de referencia. Bajas confirmadas, ritmo proyectado y resultado verificable tras el partido.">
  <link rel="canonical" href="https://pronosticosdeportivos.pro/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">

  <!-- Solo cuando existan las versiones traducidas: recíprocas, absolutas y con x-default -->
  <link rel="alternate" hreflang="es" href="https://pronosticosdeportivos.pro/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/">
  <link rel="alternate" hreflang="en" href="https://pronosticosdeportivos.pro/en/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/">
  <link rel="alternate" hreflang="x-default" href="https://pronosticosdeportivos.pro/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/">

  <!-- Open Graph: Facebook, WhatsApp, Telegram, LinkedIn, Discord -->
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="QuantFut">
  <meta property="og:locale" content="es_ES">
  <meta property="og:locale:alternate" content="en_US">
  <meta property="og:url" content="https://pronosticosdeportivos.pro/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/">
  <meta property="og:title" content="🏀 Celtics vs Lakers: 63,8 % para el local según el modelo">
  <meta property="og:description" content="Probabilidades por mercado, bajas y ritmo. El resultado y su verificación se publican en esta misma página.">
  <meta property="og:image" content="https://pronosticosdeportivos.pro/og/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28-previa.jpg">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Probabilidades del modelo para Boston Celtics contra Los Angeles Lakers">
  <meta property="article:published_time" content="2026-10-28T14:05:00Z">
  <meta property="article:modified_time" content="2026-10-29T03:40:00Z">
  <!-- fb:app_id solo si se usan las estadísticas de Meta (la documentación lo pide para Insights) -->

  <!-- X -->
  <meta name="twitter:card" content="summary_large_image">
  <!-- twitter:site solo si existe la cuenta oficial -->
  <!-- X recurre a og:title, og:description y og:image: no duplicar salvo que el texto cambie -->

  <link rel="preload" as="image" href="/og/nba/…-portada-1200x675.webp" fetchpriority="high"> <!-- solo si esa imagen es el LCP -->
  <script type="application/ld+json">{ … §7 … }</script>
</head>
```

Notas: `og:locale` sale de la versión (`es_ES` hoy; `en_US`, `pt_BR`, `fr_FR`, `it_IT`, `de_DE` después). Escapar siempre los valores en HTML en lugar de «prohibir comillas». `og:image:secure_url` es redundante si `og:image` ya es HTTPS.

---

## 6. Redes sociales: WhatsApp, Facebook, Instagram, Telegram, X, LinkedIn, Discord

| Red | Qué lee | Imagen | Caché y cómo refrescar | Notas |
|---|---|---|---|---|
| Facebook / Messenger | Open Graph; rastreador `facebookexternalhit/1.1` (exige gzip/deflate) | 1200×630 | «Images are cached based on the URL and won't be updated unless the URL changes»; refrescar con Sharing Debugger | por eso la imagen de previa y la de final tienen URLs distintas |
| WhatsApp | Open Graph | 1200×630, JPEG ≈ ≤ 300 KB (práctica) | caché propia, sin herramienta pública | probar enviando el enlace a un chat propio |
| Instagram | no muestra vistas previas en publicaciones; enlace en la bio y en historias | 1080×1920 para historias | — | generar una versión vertical del resultado para historias, a mano o desde la misma plantilla |
| Telegram | Open Graph (bot `TelegramBot`) | 1200×630 | `@WebpageBot` para refrescar | el canal de picks sigue vacío a propósito (CLAUDE.md); aquí solo importa la vista previa cuando alguien comparte |
| X | `twitter:*` con respaldo en `og:*` | 2:1 (1200×630 vale), < 5 MB (fuentes no oficiales; la documentación de X no fue accesible el 8-nov) | sin validador público; probar redactando un post | `twitter:site` solo si existe la cuenta |
| LinkedIn | Open Graph | 1200×627 | Post Inspector | — |
| Discord, Slack, Bluesky | Open Graph | 1200×630 | caché propia | — |

Comprobaciones obligatorias:

- **Cloudflare no debe bloquear** `facebookexternalhit`, `Twitterbot`, `TelegramBot`, `WhatsApp`, `LinkedInBot`, `Discordbot` (Bot Fight Mode y reglas WAF). Probar con `curl -A "<agente>"`.
- Imágenes OG generadas en el servidor desde una plantilla (texto, probabilidad, estado), con URL versionada por estado, servidas como JPEG y con caché larga.
- **Anuncios en Meta.** Compartir es libre, pero anunciar requiere autorización: Meta pide autorización previa para anuncios cuya página de destino promueva juego online «even if there is no opportunity to gamble … on that page», nombra a los sitios afiliados y agregadores, y prohíbe dirigirlos a menores de 18. La página oficial no menciona expresamente los pronósticos; fuentes secundarias dicen que sí entran. Que el proyecto sea sin ánimo de lucro no lo exime. Antes de cualquier campaña: pedir la autorización en Meta Business Suite o llevar los anuncios a páginas sin cuotas (metodología, historial).
- **Consentimiento antes del Pixel y de la CAPI** (§10).
- Cuentas oficiales: si se crean, van en `sameAs` del `Organization`.

---

## 7. Datos estructurados por tipo de página

Validar siempre con la Prueba de resultados enriquecidos y con validator.schema.org.

- **Portada:** `WebSite` (nombre, URL) + `Organization` (nombre, logo, `sameAs` de las cuentas reales, `contactPoint` con el correo de contacto).
- **Todas las páginas:** `BreadcrumbList` con las mismas URLs que el canonical.
- **Partido:**

```json
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "@id": "https://pronosticosdeportivos.pro/nba/boston-celtics-vs-los-angeles-lakers-2026-10-28/",
  "name": "Pronóstico Boston Celtics vs Los Angeles Lakers",
  "datePublished": "2026-10-28T14:05:00Z",
  "dateModified": "2026-10-29T03:40:00Z",
  "inLanguage": "es",
  "publisher": { "@id": "https://pronosticosdeportivos.pro/#organization" },
  "primaryImageOfPage": "https://pronosticosdeportivos.pro/og/nba/…-1200x675.jpg",
  "about": {
    "@type": "SportsEvent",
    "name": "Boston Celtics vs Los Angeles Lakers",
    "startDate": "2026-10-28T19:30:00-04:00",
    "eventStatus": "https://schema.org/EventScheduled",
    "sport": "Basketball",
    "homeTeam": { "@type": "SportsTeam", "name": "Boston Celtics", "url": "https://pronosticosdeportivos.pro/nba/equipos/boston-celtics/" },
    "awayTeam": { "@type": "SportsTeam", "name": "Los Angeles Lakers", "url": "https://pronosticosdeportivos.pro/nba/equipos/los-angeles-lakers/" }
  }
}
```

  `location` solo si el estadio está en nuestros datos y verificado; `eventStatus` sigue el estado real (`EventPostponed`, `EventCancelled`…).
- **Historial:** `Dataset` solo si hay descarga pública (CSV de picks sellados con hashes). Si no, `WebPage`.
- **Metodología y sobre nosotros:** `AboutPage`; `Person` solo si el titular firma con su identidad real.
- **No usar:** `Review`/`AggregateRating` sobre nosotros mismos (no son elegibles), `FAQPage` buscando fragmentos (Google los restringió en 2023 a sitios de gobierno y salud), `Product` con precio que pueda quedar desfasado, ni el resultado enriquecido de `Event` (§1, punto 9).

---

## 8. Contenido generado desde los datos (Data-to-Text)

- El valor de cada página son **los datos propios**: probabilidades por mercado, cuota justa, calibración histórica de ese mercado, bajas, ritmo, últimos partidos. El texto solo los explica.
- El generador recibe un JSON cerrado y **toda cifra del texto se comprueba contra ese JSON** antes de publicar; si no cuadra, se publica la página sin texto, nunca con una cifra inventada.
- Prohibido: «pick seguro», «ganancia», «dinero fácil», promesas, clichés. Probabilidades como probabilidades («el modelo estima», «la cuota implica»).
- Sin número de palabras. Si no hay nada que decir, no se dice.
- Aviso visible «Texto generado automáticamente a partir de los datos del modelo. Metodología» (pregunta «How» de Google).
- Glosario por idioma reutilizando el de la app (cuotas/momios, hándicap/spread, over/under, CLV, valor esperado). Términos de baloncesto: Net Rating, ritmo (pace), OffRtg/DefRtg, back-to-back, TS %. Fútbol: xG, Dixon-Coles, local/visitante, tarjetas, córners. Tenis: superficie, % de servicio, Elo por superficie.
- Encabezados `<h2>` por secciones reales de datos («Probabilidades por mercado», «Bajas confirmadas», «Historial directo y ritmo», «Puntos y triples de [jugador]» solo si el motor publica esa prop).
- Enlaces internos: primera mención de equipo → página del equipo; liga → página de la liga; cada partido → herramientas del día; cada página → metodología e historial del deporte. Ninguna página sin salida.
- Coste: una llamada por partido y por idioma publicado; la generación va después del sello y no bloquea la publicación.

---

## 9. Internacional (6 idiomas), por fases

1. **Español primero** en la raíz, hasta que las fases técnicas estén verdes en Search Console.
2. **Inglés** (`/en/`), después **portugués** (`/pt/`, pensando en Brasil: `og:locale` `pt_BR`).
3. **Francés, italiano y alemán** solo tras la revisión legal de §11 (Italia prohíbe casi toda publicidad de juego).

Reglas:

- Una versión se activa solo cuando el 100 % de su contenido (plantilla + texto + glosario) está en ese idioma y una muestra la ha revisado una persona.
- hreflang con un único método (preferible en el sitemap con `xhtml:link` para no cargar el `<head>`), recíproco, absoluto, autorreferente y con `x-default` → español.
- Si un partido no tiene versión en un idioma, esa versión no se enumera en el hreflang.
- **Sin redirección por IP ni por `Accept-Language`** (Google: «Avoid automatically redirecting users…», «Don't use IP analysis to adapt your content»; Googlebot rastrea casi siempre desde EE. UU.). Solo un aviso discreto que sugiere el idioma y un selector de idioma con enlaces normales en la cabecera y el pie.
- Nada de widgets de traducción en el navegador.
- Las cadenas de interfaz salen del mismo proceso de traducción que la app (6 idiomas en el mismo cambio, como exige CLAUDE.md para `apps/mobile`).

---

## 10. Velocidad, consentimiento y cabeceras

**Core Web Vitals** (LCP < 2,5 s, INP < 200 ms, CLS < 0,1):
- Hoy se cargan 7 hojas de estilo y un módulo grande: unir y minificar el CSS crítico, diferir el resto.
- Tablas de cuotas con `min-height` reservado o ya renderizadas desde el servidor (el SSR elimina casi todo el CLS).
- Filtros sin peticiones de red: los datos ya vienen en el HTML.
- Imágenes WebP/AVIF con `width`/`height`; `preload` solo de la imagen que sea el LCP.
- Medir con Search Console (CrUX) y PageSpeed Insights; medición propia solo con consentimiento.

**Consentimiento (hecho en F0, rama `seo/f0-consentimiento`, sin desplegar):**
- El servidor dice el régimen por el país de Cloudflare (`CF-IPCountry`): **opt-in** en EEE, Reino Unido, Suiza y país desconocido (el Pixel no carga hasta pulsar «Aceptar»); **opt-out** en el resto, respetando la decisión del 15-oct (activo salvo «Rechazar»). Países extra por `META_OPTIN_EXTRA`.
- «Rechazar» y «Aceptar» con el mismo peso visual; GPC y Do Not Track cortan siempre; rechazar borra `_fbp`/`_fbc`.
- La elección vive en la cookie propia `qf_ads` (`si`/`no`) para que también la lea el servidor: `meta_capi.enqueue` descarta los eventos web sin consentimiento, y el checkout de Whop guarda la decisión (`db/103`) para que el webhook de compra (Purchase/Subscribe) y las renovaciones la respeten.
- Pendiente fuera del código: el texto de `/legal/privacidad` sigue diciendo que la medición «viene activada»; es un texto legal versionado y lo revisa el titular. Falta además un enlace «Preferencias de medición» en el pie (`openPreferences()` ya existe) y comprobar tras desplegar que Cloudflare envía `CF-IPCountry` (si no, todos serían opt-in).
- Si se añade Google Analytics o Ads: Consent Mode v2.

**Cabeceras** (middleware de FastAPI o reglas de Cloudflare):
- HSTS: ya está. Añadir `includeSubDomains` tras comprobar que todos los subdominios van por HTTPS; `preload` solo si el titular lo decide sabiendo que revertirlo tarda meses.
- `Content-Security-Policy-Report-Only` con los orígenes reales (Meta `connect.facebook.net`, Google Sign-In `accounts.google.com`/`gstatic.com`, Whop, Firebase, Cloudflare); cuando no haya avisos durante dos semanas, pasar a `Content-Security-Policy`. Los bloques `application/ld+json` no son scripts ejecutables y no los bloquea.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` restrictiva.
- `X-Robots-Tag: noindex` en `/control`, `/app/v1`, `/mobile/v1`, `/nba/v1`, `/web/*` JSON.

---

## 11. Cumplimiento (juego responsable y publicidad del juego)

No es asesoría legal: necesita la revisión de un profesional por país.

- **En todas las páginas:** aviso +18, «Los modelos estiman probabilidades, no garantizan resultados», «Contenido informativo; no es asesoramiento financiero», enlace a `/juego-responsable/`.
- **Recursos por versión** (comprobar nombre, enlace y teléfono de cada uno antes de publicarlo): España (Jugar Bien, FEJAR), México (Línea de la Vida), Colombia, Argentina, Chile y Perú según el tráfico real; Reino Unido (BeGambleAware/GamCare); Brasil (canal oficial del Ministerio de Hacienda bajo la Ley 14.790/2023); Francia (Joueurs Info Service); Italia (Telefono Verde Nazionale gioco d'azzardo); Alemania (BZgA «Check dein Spiel»).
- **Publicidad del juego:** España (RD 958/2020), Italia (Decreto Dignità, prohibición amplia que alcanza a afiliados y pronosticadores), Francia (ANJ), Alemania (GlüStV 2021), Brasil (normas de la Secretaría de Premios y Apuestas). Mostrar cuotas con el nombre de una casa (Pinnacle) o enlazar a casas puede contar como publicidad. Decidir por versión si se muestran nombres de casas o solo «cuota de referencia del mercado».
- Sin enlaces de afiliado a casas de apuestas; si algún día los hay, `rel="sponsored"` y aviso visible.
- Ninguna herramienta que sugiera importes de apuesta (§1, punto 14).

---

## 12. Autoridad fuera de la web (corregido)

1. **Verificación externa del historial**: registrar los picks en una plataforma de seguimiento independiente y enlazarla desde `/historial/`; el valor es la confianza del lector, no el enlace.
2. **Estudios con datos propios** («cómo afecta un back-to-back al rating defensivo en 2026», «calibración real del over 2.5 en el arranque de temporada»), publicados primero en la web y difundidos donde las normas lo permitan; citar la fuente sin anclas optimizadas.
3. **Repositorio público opcional** con la metodología y la verificación de la cadena de hashes (no el repo privado).
4. **Prensa y comunidades de analítica** (blogs de estadística deportiva, podcasts) con los estudios.
5. **Nunca**: comprar enlaces, granjas de directorios, firmas de foro optimizadas, contenido de terceros alojado para aprovechar el dominio (abuso de reputación).
6. Robots de IA: el `robots.txt` de Cloudflare ya incluye las «content signals» sin valores; el titular decide si permite `search`, `ai-input` y `ai-train`.

---

## 13. Decisiones que necesita el titular antes de empezar

1. ¿Se revela el pick VIP en el historial cuando termina el partido? (Recomendado: sí.)
2. ¿Firma una persona real o solo la organización?
3. ¿Habrá anuncios de pago en Meta o Google hacia la web? (Si sí: autorización de Meta y certificación de Google para juego.)
4. Países y orden de idiomas tras el español (recomendado: en → pt-BR → resto tras revisión legal).
5. ¿Se muestran nombres de casas de apuestas en la web pública o «cuota de referencia»?
6. ¿Se permite texto generado por un LLM en las páginas de partido? ¿Con qué proveedor y presupuesto?
7. Cuentas oficiales en X, Instagram, Telegram o Facebook (para `sameAs` y `twitter:site`).
8. Content signals de IA en `robots.txt`.

---

## 14. Orden de ejecución y criterio de terminado

| Fase | Qué | Terminado cuando |
|---|---|---|
| F0 | Consentimiento **hecho** (rama `seo/f0-consentimiento`, sin desplegar). Alinear `main` con producción: **hecho** en la misma rama, gana producción por decisión del titular (ver `harness/progreso.md` 8-nov). Decisiones de §13. | `main` = producción; Pixel solo con consentimiento donde la ley lo exige. |
| F1 | Plantillas en el servidor + rutas reales + 404 HTML + redirección de `#` + `robots.txt` + índice de sitemaps + `noindex` de cuenta/panel/API. Primero las páginas estáticas: `/metodologia/`, `/sobre-nosotros/`, `/juego-responsable/`, `/historial/`, legal y portada. | Inspección de URLs muestra el contenido en el HTML; cero URLs con `#`; Search Console con el sitemap aceptado. |
| F2 | Piloto NBA: pilares, equipos y partidos con ciclo de vida, `<head>` completo, imágenes OG por estado, JSON-LD, IndexNow (Bing). | Sharing Debugger, `@WebpageBot`, LinkedIn Post Inspector y un post de X muestran la tarjeta; Prueba de resultados enriquecidos sin errores; partidos indexados antes del inicio. |
| F3 | Fútbol (13 competiciones, respetando competición ≠ liga del equipo) y tenis. Herramientas del día. | Igual que F2; umbral de equipos aplicado; sin crecimiento de «sin indexar». |
| F4 | Texto desde datos, enlazado interno, calculadora de cuota justa, gráficos de calibración. | 0 cifras del texto fuera del JSON en la prueba automática; aviso de automatización visible. |
| F5 | CWV y cabeceras (CSP en modo informe → aplicada). | LCP, INP y CLS en verde en CrUX/PSI para portada, pilar y partido. |
| F6 | Inglés y portugués. | hreflang sin errores en Search Console; muestra revisada por idioma. |
| F7 | Francés, italiano y alemán. | Revisión legal por país hecha. |
| F8 | Autoridad fuera de la web (§12). | Primer estudio publicado; historial verificado por terceros enlazado. |

Cada fase: pruebas en `tests/` y en `frontend/*.test.mjs`, `./scripts/test_local_windows.ps1 -Suite all`, despliegue anotado en DEPLOYS.md con su vuelta atrás, y verificación en el dominio real.

---

## Fuentes leídas (8-nov-2026)

- Google, sitemaps: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- Google, JavaScript y SEO: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Google, políticas de spam: https://developers.google.com/search/docs/essentials/spam-policies
- Google, contenido útil, E-E-A-T y YMYL: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Google, Discover: https://developers.google.com/search/docs/appearance/google-discover
- Google, datos de eventos: https://developers.google.com/search/docs/appearance/structured-data/event
- Google, contenido de pago: https://developers.google.com/search/docs/appearance/structured-data/paywalled-content
- Google, sitios multirregionales: https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
- Google, hreflang: https://developers.google.com/search/docs/specialty/international/localized-versions
- Google, Indexing API: https://developers.google.com/search/apis/indexing-api/v3/quickstart
- Meta, Open Graph para webmasters: https://developers.facebook.com/docs/sharing/webmasters/
- Meta, anuncios de juego online: https://transparency.meta.com/policies/ad-standards/restricted-goods-services/gambling-games
- IndexNow: https://www.indexnow.org/documentation (Google no figura entre los buscadores participantes)
- X, tarjetas: la documentación oficial devolvió 402 el 8-nov; tamaños tomados de fuentes secundarias y marcados como tales.
