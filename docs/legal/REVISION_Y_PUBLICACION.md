# Documentos legales de QuantFut — control de publicación

## Estado (2026-10-12)

Los textos `TERMINOS_QUANTFUT.md`, `PRIVACIDAD_QUANTFUT.md` y
`ELIMINAR_CUENTA_QUANTFUT.md` son la **versión final de contenido** (2026-10-12):
sin marcadores, con los datos del titular y con la retención que el servidor
aplica de verdad. Los `*_BORRADOR.md` son la redacción previa y se conservan
solo como historial; no son fuente de nada.
Las páginas públicas están en `src/qf/api/legal_pages/` (generadas con
`scripts/build_legal_pages.cjs`, que se niega a compilar un texto con marcadores
o con la palabra «Borrador») y las sirve `src/qf/api/legal.py` en `/legal/terminos`,
`/legal/privacidad` y `/legal/eliminar-cuenta`. **Aún no están desplegadas**: el
servidor responde 404 hasta que el titular decida publicarlas.

Datos confirmados por el titular: **Saptain LTD**, constituida en **Seychelles**,
**E Coast Rd, Victoria, Seychelles**, edad mínima **18 años**, mercados **Estados
Unidos, toda Europa y Latinoamérica**, servidor Contabo en Berlín y correo
Proton Mail. El contacto de privacidad es **admin@pronosticosdeportivos.pro**
(el titular lo corrigió desde `.com`; `tests/test_legal.py` impide que vuelva).

El procedimiento de solicitudes (acceso, corrección, eliminación) es manual y
está en `OPERACION_PRIVACIDAD.md`. La app y la web no borran la cuenta por sí
solas: el texto público lo dice así y no promete lo contrario.

## Lo que solo el titular puede aportar

- Revisión por un profesional habilitado, sobre todo del contenido de
  pronósticos y de los futuros cobros. La redacción no acredita autorización
  para operar apuestas ni cumplimiento general en cada país.
- Confirmar que atiende el buzón de contacto a diario (el procedimiento lo supone).
- País contractual efectivo de Contabo y de Proton, y los contratos/DPA
  correspondientes (aceptarlos es decisión suya).
- Plazos legales de conservación de registros comerciales por categoría y
  país: el texto remite a «la obligación legal o prescripción aplicable» sin
  inventar un plazo universal.
- Representación EEE/Reino Unido y salvaguardas de transferencias, si se
  atiende de verdad a esos mercados.
- Condiciones de cobro, cancelación y devoluciones cuando se elija procesador.

## Antes de publicar

- Desplegar el backend con las páginas y comprobar `/legal/*` desde el dominio.
- Mantener alineadas la versión de los textos y `CONSENT_VERSION`
  (`src/qf/comercial/firebase.py`); la prueba `tests/test_legal.py` lo exige.
- No registrar aceptaciones ni activar Google (`FIREBASE_AUTH_ENABLED`,
  `qf_google_auth_enabled`) hasta que el titular apruebe la versión.
- Los textos legales siguen solo en español; traducirlos exige revisión jurídica.

## Fuentes primarias consultadas

- [Privacidad y seguridad de Firebase](https://firebase.google.com/support/privacy):
  categorías técnicas de datos, funciones de proveedores y ciclos de retirada.
- [Condiciones de tratamiento de Firebase](https://firebase.google.com/terms/data-processing-terms/):
  responsabilidades del cliente y proveedor.
- [Data Protection Act, 2023, texto oficial de Seychelles](https://www.infocom.sc/wp-content/uploads/2024/01/Act-24-2023-Data-Protection-Act-2023.pdf).
- [Information Commission, autoridad de datos de Seychelles](https://www.infocom.sc/data-protection/).
- [Fair Trading Act, 2022 y autoridad de consumo](https://ftc.gov.sc/fair-trading-act-2022/).
- [RGPD, texto oficial](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng):
  ámbito territorial, bases jurídicas, información, derechos, representación y transferencias.
- [EDPB, atención de derechos](https://www.edpb.europa.eu/sme/be-compliant/respect-individuals-rights_en):
  procedimiento, gratuidad y plazo general de un mes.
- [California Attorney General, CCPA](https://oag.ca.gov/privacy/ccpa):
  derechos y ámbito condicionado a los requisitos legales.
- [ICO, transferencias internacionales](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/).

Seychelles es el país de constitución indicado por el titular, no una
verificación registral de la sociedad. Si el titular opera desde otro país o dirige
el servicio a otros mercados, se revisarán sus fuentes oficiales antes de
cerrar la versión publicable. La constitución en Seychelles no excluye las
normas de los mercados de destino ni equivale a una licencia de juego.
