# NBA: scrapers, datos adicionales y auditoría — 2026-10-05

Se revisaron **10 repositorios con commits fijados** y se verificaron 52 archivos descargados mediante tamaño, Git blob SHA-1 y SHA-256. No se ejecutó código de terceros ni se instalaron sus dependencias. El incremento se limita a la aplicación NBA; las 100 pruebas NBA y las 606 de fútbol pasan. F2–F4 avanzan, con todas las puertas G0–G9 todavía pendientes.

## Fuentes y decisiones

| Repositorio | Qué ofrece y decisión |
|---|---|
| [dblackrun/pbpstats](https://github.com/dblackrun/pbpstats/tree/e7ccf2fb6326da630a3cf1665aac964a1e108f4c) | PBP, posesiones y quintetos. Se comprobó su [API pública](https://api.pbpstats.com/docs) y se integró un piloto de agregados por cuarto. Código MIT; esto no acredita derechos comerciales sobre los datos del servicio. |
| [mxufc29/nbainjuries](https://github.com/mxufc29/nbainjuries/tree/57603738fb28185e3c1bf4d71d75af0f85514ac1) | Parser de PDF oficiales, con Java/tabula-py. Su código contempla distintos nombres de archivos antes/después de diciembre de 2025. La muestra oficial actual dio 403: no se recibió ni verificó ningún PDF. |
| [jaebradley/basketball_reference_web_scraper](https://github.com/jaebradley/basketball_reference_web_scraper/tree/1ec892df21e7f206ab253ed0a3ade3fc4be2e16e) | Estadísticas, plantillas y calendarios; IDs Basketball Reference. Referencia útil, sin integración automática a IDs NBA o disponibilidad médica. |
| [sferik/nba-ruby](https://github.com/sferik/nba-ruby/tree/aefdc5429aac1e297ae330ab1a7cc277a82e903a) | Cliente del endpoint oficial GameRotation. Sigue dependiendo del acceso a stats.nba.com; no sustituye un archivo histórico. |
| [mrees002/nba-injury-database](https://github.com/mrees002/nba-injury-database/tree/9fa2a23439cb9899b513033b42f4b5c8b1445a64) | Calendarios fuente descargados: 1,230 partidos en cada una de 2024–25 y 2025–26. IDs/fechas útiles; **no contienen horas de inicio**. |
| [EllAchE/nba-tipoff-scraper](https://github.com/EllAchE/nba-tipoff-scraper/tree/b1fb92f10d61b94e44bb3d760e9ac269c706a7ab) | Seis JSON históricos de 2021: primer anotador/tipoff, sin zona horaria verificable. Contienen etiquetas jsonpickle, leídas como JSON simple. No son contratos P/R/A; no se importan al modelo. |
| [proplineapi/propline-python](https://github.com/proplineapi/propline-python/tree/3faaa01ec6cd627ee8d0543ee9803d62c269dd7d) | SDK que requiere clave de proveedor; no es un archivo gratuito de cuotas. Sin registro, contratación o llamadas al proveedor. |
| [agad495/DKscraPy](https://github.com/agad495/DKscraPy/tree/667fab26b33123282c2de8bcbff830f6e6fc2816) | El árbol fijado solo incluye MLB/NFL. No se presenta como scraper NBA. |
| [petermartens98/NBA-Data-Analytics-Pipeline](https://github.com/petermartens98/NBA-Data-Analytics-Pipeline/tree/943f0d2b7b35ba984b4f42c4725ce618b838e712) | Notebook CBS/Selenium con ruta Chrome local y sin licencia declarada. Solo revisión; no ejecución o adopción. |
| [neeljshah/court-vision](https://github.com/neeljshah/court-vision/tree/9abbe1d8482e39246f42f142da9b35f182f7c62a) | LICENSE propietario: All Rights Reserved. El árbol fijado no incluye archivos con `stint` en el nombre. No se incorporan sus modelos, código o auditorías derivadas. |

El inventario completo, commits, licencias y hashes está en `apps/nba/.local/reports/scraper_repository_audit_20261005.json`. Las afirmaciones describen las versiones revisadas; un README o una licencia de código no garantizan cobertura, velocidad o permisos sobre un proveedor externo.

## F3: observaciones prospectivas de alineación

La página pública de [RotoWire](https://www.rotowire.com/basketball/nba-lineups.php), recibida a las **21:09:19 UTC**, proporciona cinco partidos, diez alineaciones **previstas** y 50 titulares previstos. Ninguna de esas diez alineaciones está confirmada. Contar palabras “Confirmed” en toda la página habría incluido textos de ayuda y producido un resultado incorrecto.

El adaptador separa titulares de “may not play”, conserva `rotowire:` como namespace propio y distingue `expected` de `confirmed_by_provider`. No convierte nombres, porcentajes editoriales o etiquetas Out/Ques en elegibilidad médica verificada. Un jugador omitido sigue con disponibilidad desconocida.

Los cinco cruces de equipos tienen candidatos en el calendario ESPN capturado para el mismo día. Se conserva la hora ET mostrada sin convertirla: el candidato aporta una hora UTC, pero la correspondencia de reloj y la identidad de jugadores RotoWire siguen sin validación independiente. Todas las observaciones se recibieron antes del inicio candidato. La recepción actual no demuestra cuándo se publicó originalmente la alineación.

## F4: quintetos por cuarto y exposición histórica

Se recibió una muestra inicial y 14 de los 20 partidos del lote seleccionado **antes** de descargarlo: los primeros partidos aceptados de 2025–26 ordenados por fecha/ID, excluyendo la muestra inicial. Seis peticiones devolvieron 503; no se reintentaron. El capturador actual detiene además el lote al primer 5xx, 403 o 429 y limita cada lote a 20 IDs, con solicitudes secuenciales y límite de tamaño.

Resultado: **15 partidos aceptados, 745 registros de quintetos por cuarto, un partido con dos prórrogas y cero partidos en cuarentena en la auditoría final**. Esto es un piloto, no una temporada completa ni 745 quintetos únicos.

Controles aplicados: fecha, temporada, tipo de competición, dos equipos correctos, cinco IDs oficiales distintos por quinteto, pertenencia al box score, exclusión de DNP, cuatro cuartos y prórrogas consecutivas, conservación de reloj, consistencia cuarto/partido y marcador exacto contra el box score individual independiente.

Los minutos MM:SS agregados conservan una tolerancia explícita de ±1 segundo por registro; el contraste con el box score admite además un segundo de precisión de referencia. No se reescalan minutos para forzar un ajuste. **Son agregados por cuarto, no intervalos cronológicos de sustitución.** Los rebotes PBP de equipo no se convierten en rebotes individuales. No se reentrenó ni promovió el modelo con este piloto.

Los calendarios mrees aportan dos temporadas de 1,230 partidos; las fechas coinciden en los 1,179 y 1,146 partidos presentes en nuestro dataset individual aceptado. Se excluye `WL` como feature prepartido. Estos CSV no resuelven el instante de inicio ni verifican lesiones anteriores al partido.

## Reproducción y evidencia

Desde el entorno NBA, los nuevos comandos son:

```powershell
python -m nba capture-lineups
python -m nba audit-lineups MANIFEST --context-manifest MANIFEST_ESPN --as-of ISO_UTC --output-dir CARPETA_NUEVA
python -m nba capture-rotations --game-ids ID_NBA_1 ID_NBA_2
python -m nba audit-rotations MANIFEST --dataset DATASET --output-dir CARPETA_NUEVA
```

Las salidas previas se preservan; cada captura conserva recepción original y hash. El ledger NBA sella capturas/resultados y los datos no se insertan en fútbol. Informes finales:

- `apps/nba/.local/reports/lineups_audit_20261005/lineups.json`.
- `apps/nba/.local/reports/rotations_combined_20261005.json` y las auditorías v2 que referencia.
- `apps/nba/.local/reports/schedule_reference_audit_20261005.json`.
- `apps/nba/.local/reports/scraper_repository_audit_20261005.json`.
- `apps/nba/.local/reports/scrapers_validation_20261005.json` y la instantánea propia de código que referencia.

Se conservaron los fallos de integración: exclusión inicial pendiente de tarjetas publicitarias explícitas; tres lecturas JSON con codificación Windows que se corrigieron a UTF-8; y una invocación del harness con PATH/temporales incorrectos. Las auditorías finales y el harness con temporales dentro del workspace pasan. Los informes anteriores no se reemplazaron ni se atribuyeron esos errores de lectura a defectos de los datos.

## Siguiente trabajo del plan

F2–F4 siguen en progreso: ampliar quintetos históricos con lotes auditados, obtener intervalos reales de sustitución desde PBP, validar reloj/identidades de alineaciones y capturar disponibilidad por partido con publicación verificable. Después se evalúa si el contexto mejora minutos/roles frente al baseline mediante un protocolo temporal nuevo.

Continúan pendientes cuotas actuales e históricas P/R/A con contrato, reglas y timestamps suficientes, evaluación prospectiva y límites compartidos de Telegram. La reutilización del bot/chat de fútbol está autorizada; las credenciales activas no están disponibles en este host y no hubo envío real. Ningún nuevo archivo acredita rentabilidad, liquidez, velocidad de entrega o autorización para emitir picks comerciales. No se realizó ninguna apuesta.
