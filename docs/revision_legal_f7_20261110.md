# F7 (`fr` / `it` / `de`) y F8 — Lista de revisión legal y bloqueos externos, 2026-11-10

## Por qué NO se codifica F7 todavía
Según `docs/plan_seo_redes_web_20261108.md` (§9, §11, §13 #4 y §14), el código de `fr/`, `it/` y `de/` **no debe escribirse ni publicarse sin revisión legal previa país por país**. Con `idiomas.py` ya parametrizado en tres idiomas (`es`, `en`, `pt-BR`), las traducciones técnicas quedan desbloqueadas en cuanto el titular firme las decisiones jurídicas abajo indicadas.

---

## Checklist de aprobación legal antes de codificar F7

### 1. Italia (`/it/` — *Decreto Dignità*)
- **Delimitación editorial vs. promoción comercial:** confirmar con asesoría legal italiana si el enlace global hacia `/planes/`, las menciones a cuotas/casas de apuestas o los botones de suscripción (`Whop`) dentro de páginas informativas en italiano incurren en la prohibición de publicidad directa o indirecta de juegos con premios en dinero (*Decreto Dignità*).
- **Uso del nombre `Pinnacle` y enlaces a casas:** validar si nombrar explícitamente operadores (como referencia estadística de mercado sin margen) exige suprimir cualquier mención de marca en `/it/` o sustituirlo por formulación genérica («cuotas de mercado internacional»).
- **Red de ayuda verificada:** obtener teléfono e institución oficial italiana verificados directamente por el titular para la página equivalente a `/juego-responsavel/`.
- **Textos legales:** definir si `/legal/terminos` y `/legal/privacidad` requieren traducción jurada/revisada al italiano antes de `it=on` (actualmente solo están en español).

### 2. Francia (`/fr/` — *Autorité Nationale des Jeux · ANJ*)
- **Régimen de pronosticadores (*pronostics sportifs*):** confirmar con asesoría francesa las menciones obligatorias respecto a edad mínima (+18), ausencia de garantía de ganancia, riesgo financiero y prohibición de presentar el análisis como inversión o ingreso seguro.
- **Flujo hacia `/planes/` y `Whop`:** revisar cómo pueden presentarse planes de pago y alertas sin infringir las restricciones de la ANJ sobre captación comercial y operadores autorizados en Francia.
- **Red de ayuda verificada:** confirmar el número y organismo nacional oficial vigente en Francia para ayuda contra la ludopatía.
- **Textos legales:** decidir si los términos y privacidad deben existir en francés antes de abrir `/fr/` (`fr=on`).

### 3. Alemania (`/de/` — *GlüStV 2021 / GGL*)
- **Alcance territorial y publicidad (*Glücksspielstaatsvertrag 2021*):** confirmar si un sitio editorial de modelos probabilísticos con suscripción de pago entra en supuestos de autorización o restricción publicitaria si enlaza o compara cuotas de operadores sin licencia GGL (especialmente referencias a casas internacionales no licenciadas localmente).
- **Separación de `/planes/` y avisos obligatorios:** confirmar texto de advertencia legal en alemán (+18, riesgo de pérdida, no es casa de apuestas) y red nacional oficial verificada.
- **Textos legales:** confirmar traducción de términos, privacidad y pie legal (*Impressum* si aplica por orientación al mercado alemán).

---

## Bloqueos previos del titular ya abiertos en F6 (`en` y `pt-BR`) y F8

### Pendientes para pasar `en` y `pt-BR` de `preview` / `off` a `on`
1. **Revisión humana del texto** de inglés (actualmente `preview`) y portugués de Brasil (actualmente `off`).
2. **Red de ayuda de Brasil** en `/pt/jogo-responsavel/` (`src/qf/api/paginas/pt_jogo_responsavel.html`): confirmar teléfono oficial verificado antes de pasar `pt` a `on`.
3. **Decisión sobre `/legal/terminos` y `/legal/privacidad`:** actualmente solo existen en español (el pie de `en` y `pt` enlaza a esas rutas marcando el idioma español); decidir si se traducen antes de abrir `en=on` / `pt=on`.

### Pendientes externos del titular para F8 (autoridad y redes)
1. **Cuentas sociales (`sameAs` y `twitter:site`):** aportar los usuarios reales en X, Instagram, Telegram, Facebook y canales activos; hasta tenerlos confirmados no se añaden al JSON-LD `Organization` ni a `<meta name="twitter:site">`.
2. **Verificación independiente en terceros:** crear y alimentar cuentas verificadas en **Blogabet** o **Betstamp** enviando selecciones antes del inicio de los partidos como prueba externa complementaria a `/chain`.
3. **Estudios con datos propios y repositorio público espejo de `/chain`:**
   - El verificador local sin dependencias ya está disponible en `scripts/verificar_cadena_publica.py` para enlazarlo o publicarlo en un repositorio público aparte junto con los recibos sellados (`*.receipt.json`) y lotes revelados cuando el titular cree el repo en GitHub.
   - Publicar estudios con datos reales del archivo histórico (p. ej. eficiencia de cierre o comparación de margen/calibración tras acumular muestra suficiente) sin fabricar cifras.

### Pendientes de operación y medición en producción (F2 / F5)
1. **~16-nov-2026:** revisar los registros recogidos por `/csp-report` (`Content-Security-Policy-Report-Only`) tras ≥ 7 días de tráfico real y decidir si se permite `static.cloudflareinsights.com` en páginas de confianza antes de activar `Content-Security-Policy` coercitiva.
2. **~16-nov-2026:** comprobar cuántos equipos de NBA superan ya el umbral de 5 pronósticos en 45 días para evaluar ampliar la ventana de `/nba/equipos/.../`.
3. **Cloudflare Dashboard:** configurar la regla de caché pública de HTML sin afectar a `/nba/v1/...`, `/tenis/v2/...`, `/cuenta*`, `/auth*` ni `/admin*`.
4. **Search Console:** enviar los sitemaps tras el despliegue y usar *Inspección de URLs → HTML renderizado* en `/`, `/historial/` y páginas pilar deportivas.
