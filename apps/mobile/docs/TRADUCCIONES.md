# Traducciones de la app (es, en, pt, fr, it, de)

**Regla del proyecto:** cualquier texto visible que se añada o cambie en la app (o en un
mensaje del servidor que la app muestre) se traduce a los 6 idiomas **en el mismo
cambio**. Las pruebas lo exigen; no hay excepciones por prisa.

## Cómo funciona

- **Idioma:** `lib/l10n/app_locale.dart` (`AppLocale`). Orden: elección guardada en el
  dispositivo → idioma del dispositivo si está soportado → español. Funciona sin
  Firebase; si hay cuenta, `FirebaseServices` lo sincroniza como preferencia.
- **Selector:** `lib/l10n/language_picker.dart` (botón 🌐 en bienvenida y acceso,
  Perfil → Idioma, Privacidad y preferencias). Cambia el idioma al instante.
- **Textos:** archivos ARB en `lib/l10n/` (`app_es.arb` es la plantilla). Flutter genera
  `app_localizations*.dart` con `flutter gen-l10n` (se ejecuta solo al compilar).
  En un widget: `context.l10n.clave`. Sin contexto (errores, formatos): `AppLocale.instance.l10n`.
- **Pronósticos y mercados:** el servidor envía textos en español (`texto`, `titulo`,
  `seleccion`, `grupo`, `nota`) junto a los campos que los originan (`market`, `selection`,
  `line`, equipos). `lib/l10n/pick_labels.dart` los reconstruye en el idioma actual con las
  mismas reglas que `alta_prob.texto` y `partido_mercados.py`. Un mercado nuevo en el
  backend hay que añadirlo ahí y a los ARB.
- **Catálogo de mercados** (`assets/model/market_evidence.json`): familias y líneas se
  traducen por identificador (`MarketFamily.localTitle`, `MarketLine.localLabel`).
- **Fechas, números y porcentajes:** `kickoffText`, `decimalText`, `realPercent`,
  `percentText` (en `live_api.dart`) usan el idioma actual. Porcentaje con espacio en
  es/fr/de («65 %») y sin él en en/pt/it («65%»).
- **Mensajes del servidor:** la app envía `Accept-Language`. `src/qf/api/mensajes.py`
  traduce los errores (`HTTPException`), los términos de las monedas y el mensaje de
  recompensas desactivadas. Los avisos push ya se redactan por idioma en
  `firebase_notificaciones.py`. Los mensajes por defecto de cada sección (tabla
  `mobile_features`) se traducen en `featureMessage` (app).

## Añadir o cambiar un texto

1. Escribe un JSON con las 6 traducciones (ejemplo en la cabecera de `tool/l10n_add.py`):

   ```json
   {"navHome": {"es": "Inicio", "en": "Home", "pt": "Início", "fr": "Accueil",
                "it": "Home", "de": "Start"}}
   ```

   Para parámetros añade `"meta": {"placeholders": {"count": {"type": "int"}}}`; usa
   `{count, plural, one{…} other{…}}` para plurales y `{side, select, over{…} other{…}}`.
2. `python tool/l10n_add.py nuevos.json` (escribe los 6 ARB; falla si falta un idioma).
3. Usa `context.l10n.clave` en el código. **No escribas cadenas visibles en el código.**
4. `flutter test test/l10n_test.dart test/l10n_runtime_test.dart`.

Si es un mensaje de error o un texto que genera el backend y se ve en la app, añádelo a
`src/qf/api/mensajes.py` con sus 5 traducciones (`pytest tests/test_mensajes.py`).

## Qué comprueban las pruebas

- `test/l10n_test.dart`: mismas claves en los 6 ARB, sin textos vacíos, parámetros
  presentes, ninguna traducción copiada del español, y **ninguna cadena fija visible** en
  la interfaz (con o sin acentos). Excepciones solo con `// l10n-ignore` (una línea) o un
  bloque `l10n-ignore-start/end`, y solo para identificadores de datos.
- `test/l10n_runtime_test.dart`: las 5 pestañas se pintan en los 6 idiomas sin errores ni
  desbordes de texto (con las fuentes reales), y el idioma cambia en caliente sin perder la
  navegación.
- `tests/test_mensajes.py` (backend): catálogo completo y todo mensaje del código que
  pueda verse en la app está traducido (análisis con `ast`).

## Estilo de las traducciones

Registro cercano: tú en es/it/de, «você» en pt, «vous» en fr. Términos: *pronóstico* =
prediction/prognóstico/pronostic/pronostico/Prognose; *cuota* = odds/odd/cote/quota/Quote;
*parley* = parlay/múltipla/combiné/multipla/Kombiwette; *Reto Escalera* = Ladder Challenge/
Desafio Escada/Défi Escalier/Sfida Scala/Treppen-Challenge. Son traducciones de calidad de
trabajo hechas por un modelo: **antes de publicar, deben revisarlas hablantes nativos**
(sobre todo portugués, francés, italiano y alemán, y los textos de apuestas/legales).

## Límites conocidos

- Código heredado de la plantilla (`lib/sign_in`, `lib/forget_password`, `lib/log_in`…) y 5
  archivos de `lib/product` no están conectados a `main.dart` y no se traducen
  (lista en `test/l10n_test.dart`).
- Los textos legales públicos (`/legal/terminos`, `/legal/privacidad`) y los correos de
  cuenta siguen en su idioma original; su traducción exige revisión jurídica.
- Un mensaje de error del servidor que no esté en el catálogo se muestra en español.
- Los nombres de equipos, ligas y jugadores vienen de los datos y no se traducen.
