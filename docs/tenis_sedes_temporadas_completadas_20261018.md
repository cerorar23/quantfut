# Tenis: sedes y temporadas revisadas, 18 de octubre de 2026

## Resultado y alcance

Se enlazaron los 126 encuentros pendientes con el recinto principal publicado de su edición. La muestra archivada contiene ahora **228/228 encuentros con sede identificada**, repartidos en 35 recintos y 52 enlaces exactos de proveedor/modalidad/temporada. No es una validación independiente de participantes, horarios, estados en vivo o pista individual.

Las **48 discrepancias de temporada** recibieron una corrección explícita de metadatos de edición: Guangzhou 22, Lisboa 18 y Cali 8. El proveedor decía 2025; las fuentes de las ediciones revisadas acreditan 2026 y sus ventanas publicadas. Se conserva `provider_season=2025`, junto con `season=2026`, motivo, fuentes, fecha y digest del evento. No se aplicó una regla general de reemplazar el año por el de la fecha.

| Comprobación | Resultado |
|---|---:|
| Encuentros del archivo original | 228 |
| Con sede principal identificada | 228 |
| Nuevos enlaces de encuentros antes pendientes | 126 |
| Discrepancias de temporada corregidas | 48 |
| Discrepancias de temporada aún sin revisar en esta muestra | 0 |
| Con coordenadas verificadas | 102 |
| Con elevación de terreno estimada | 102 |

**Límite geográfico pendiente:** los 27 recintos nuevos tienen identidad y zona horaria revisadas, pero sus coordenadas y elevaciones siguen desconocidas. Los 126 encuentros nuevos no pueden alimentar todavía cálculos de distancia/altitud/clima. La extracción cartográfica acotada no devolvió datos utilizables: se conservaron errores HTTP/timeout y no se sustituyeron por centros de ciudad. Identificar una sede no equivale a georreferenciarla.

## Ediciones y recintos revisados

| Torneo del proveedor | Modalidad | Recinto principal |
|---|---|---|
| Florence (Italy) - Qualification | Masculina | Match Ball Firenze Country Club |
| Florence | Masculina | Match Ball Firenze Country Club |
| Fort Worth (Usa) | Masculina | Bayard H. Friedman Tennis Center |
| Cali | Masculina | Club Campestre Farallones |
| Guangzhou | Masculina | Nansha International Tennis Center |
| Lisbon | Masculina | Club Internacional de Foot-ball (CIF) |
| Lisbon (Portugal) - Qualification | Femenina | Club Internacional de Foot-ball (CIF) |
| Catania (Italy) - Qualification | Masculina | Tennis School Monte Ka Tira |
| Jinan | Masculina | Jinan Olympic Sports Center Tennis Venue |
| M15 Bol | Masculina | TK Zlatni rat |
| W15 Bol | Femenina | TK Zlatni rat |
| M15 Heraklion 8 | Masculina | Lyttos Beach Sportscenter |
| W35 Heraklion 2 | Femenina | NANA Tennis & Sports Club |
| M15 Monastir 35 | Masculina | Magic Hotel Skanes Family Monastir |
| W35 Monastir 7 | Femenina | Magic Hotel Skanes Family Monastir |
| M15 Sharm ElSheikh 13 | Masculina | Soho Square Tennis Complex |
| ITF W15 Sharm ElSheikh 15 Women | Femenina | Soho Square Tennis Complex |
| M15 Szabolcsveresmart | Masculina | HNTA |
| M25 Luanda | Masculina | Academia de Tenis Kikuxi Villas Club |
| M25 Qian Daohu | Masculina | Qiandaohu Tennis Park |
| M25 Solapur (India) | Masculina | MSLTA Tennis Centre, District Sports Complex |
| Maia | Masculina | Complexo Municipal de Tenis da Maia |
| Mallorca | Femenina | Polideportivo Municipal de Magaluf |
| Olbia | Masculina | Tennis Club Terranova |
| Roanne | Masculina | Halle Andre Vacheresse |
| Rovereto | Femenina | PalaBaldresca / Circolo Tennis Rovereto |
| W15 Chisinau 2 (Moldova) | Femenina | National Tennis Center, Bacioi |
| W15 Shenzhen | Femenina | GuangMing QunZhong Sports Center |
| W35 Redding, CA | Femenina | Sun Oaks Club |
| W35 Santa Margherita di Pula 10 | Femenina | ASD Fortevillage |
| W50 Quebec City (Canada) | Femenina | Club Avantage / Academie Aliassime |
| W50 Stara Zagora (Bulgaria) | Femenina | Tennis Club Avgusta Trayana |

Los encuentros masculinos de Heraklion se enlazan a Lyttos Beach y los femeninos a NANA, según sus fichas ITF de esa semana. Mallorca se enlaza a Magaluf, con evidencia de la sede central y del comunicado de 2026 que concentra allí la competición. La página vigente de sedes de Roanne respalda Halle André Vacheresse como recinto principal; el gimnasio auxiliar y las referencias históricas al Scarabée no se convierten en prueba de la pista de cada final.

## Evidencia y artefactos

Directorio: `data/tennis/venues_completion_20261017/`.

- `reviewed_editions.json`: revisión manual de 31 ediciones y 37 alias exactos.
- `originals/`: respuestas y recibos de fuentes oficiales. Los bloqueos HTTP 200 de Incapsula se detectaron como páginas de error, no como fichas válidas.
- `web_*extract*.json`, `web_lisbon_atp.json`, `web_sources.json`: extracciones de la herramienta web, etiquetadas como tales, con URL y recepción; se distinguen de los bytes HTTP originales.
- `registry_seed_completed.json`: semilla completa y fuentes por campo.
- `season_reviews.json`: 48 revisiones específicas con digest de la fila original.
- `calendar_completed_v2.json`: informe final reproducido usando el código entregado. El primer ensayo se conserva.

El registro compartido de sedes está en `data/tennis/venues_20261017/venues.sqlite`. Las tablas de versiones y de revisiones son de solo adición. La semilla inicial y las respuestas originales no se sobrescribieron.

Código entregado en el checkout aislado, bajo `apps/tennis/`:

- `tennis_engine/fixture_reviews.py`: registro, validación contra archivo de entrada, consulta por disponibilidad y enriquecimiento con original/corrección separados.
- `scripts/build_venues_complete.py`: reproducción sin red desde la semilla y los recibos archivados.
- `tests/test_fixture_reviews.py`: diez pruebas nuevas.

Para enriquecer calendarios con correcciones se utiliza `FixtureReviews(registry).enrich_calendar(...)`; llamar directamente al método anterior de VenueRegistry mantiene el comportamiento original y no aplica revisiones implícitas. La normalización rechaza una fila que haya cambiado desde la revisión, evidencias alteradas, revisiones contradictorias y filas en cuarentena. Las revisiones solo son visibles estrictamente después de registrarse.

Reproducción desde el proyecto principal, con PYTHONPATH dirigido a `apps/tennis` del checkout:

```text
python <checkout>/apps/tennis/scripts/build_venues_complete.py --root data/tennis/venues_completion_20261017 --base-seed data/tennis/venues_20261017/registry_seed_open_meteo_v2.json --probe-root .local/api_tennis_probe/20261017T211250Z --registry data/tennis/venues_20261017/venues.sqlite --report <nuevo_informe.json>
```

No requiere red ni credenciales. El informe debe tener un nombre nuevo; no se sobrescriben resultados previos.

## Validación y consumo

126 pruebas de tenis aprobadas desde el checkout entregado (116 anteriores y 10 nuevas). Arnés general final: 1.300 aprobadas, 88 omitidas y dos avisos en 79,88 s; Docker no disponible. Verificados los hashes de las 65 fuentes de la semilla, la muestra de 228 filas, las 48 revisiones únicas y los doce artefactos congelados del modelo. No se alteraron probabilidades ni se promovió un modelo nuevo.

No hubo consultas deportivas ni gasto de créditos de The Odds API. Se usaron dos consultas al transporte ZenRows existente para recuperar las páginas oficiales de Cali y Jinan; el resto procede de consultas públicas y archivos locales. El acceso gratuito sin clave de Open-Meteo para el proyecto de tenis no comercial permanece registrado.

## Fuentes principales

- [Florence Open, organizador 2026](https://florenceopen.matchballfirenze.it/).
- [Fort Worth, calendario de TCU](https://calendar.tcu.edu/event/tcu-mens-tennis-vs-fort-worth-challenger).
- [Cali, Alcaldía y edición 2026](https://www.cali.gov.co/boletines/publicaciones/194969/presentan-el-kia-open-cali-2026-arranca-el-18-de-octubre-en-el-club-campestre-farallones/).
- [Cali, Federación Colombiana](https://padel.fedecoltenis.com/site/3886?galeria=1).
- [Guangzhou Nansha, fuente del centro de medios del distrito](https://huacheng.gz-cmc.com/pages/2026/10/13/a7fcad5c57494c41a0fcb457989bfacd.html).
- [Lisboa, calendario ATP](https://www.atptour.com/en/tournaments/lisbob/7742/overview).
- [Lisboa, sede y edición WTA](https://www.wtatennis.com/tournaments/1168/lisbon-125/2026).
- [Heraklion masculino, ITF](https://www.itftennis.com/en/tournament/m15-heraklion/gre/2026/m-itf-gre-2026-012/fact-sheet/).
- [Heraklion femenino, ITF](https://www.itftennis.com/en/tournament/w35-heraklion/gre/2026/w-itf-gre-2026-011/fact-sheet/).
- [Roanne, sedes vigentes](https://openderoanne.com/les-sites/).
- [Mallorca, organizador](https://www.mallorcawomenschampionships.com/en/tournament/news/mallorca-womens-championships-2026).

Las fichas ITF y demás URLs específicas están identificadas por campo en la semilla y en `reviewed_editions.json`. Los datos de geometría que ya existían conservan su atribución a OpenStreetMap (ODbL 1.0); las elevaciones anteriores conservan atribución a Open-Meteo y Copernicus DEM.
