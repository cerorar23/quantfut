# Tenis: registro de sedes por edición

17 de octubre de 2026. Se implementó y ejecutó el registro solicitado, usando el calendario UTC de API-Tennis ya descargado. No se hicieron nuevas consultas a API-Tennis ni a The Odds API y no se modificaron las probabilidades del motor.

## Resultado real

| Indicador | Resultado |
|---|---:|
| Ediciones de torneos principales enlazadas | 7 |
| Recintos físicos registrados | 8 |
| Enlaces exactos por proveedor, modalidad y vigencia | 15 |
| Fuentes archivadas y hashes comprobados | 24 |
| Encuentros del calendario completo | 228 |
| Encuentros ATP/WTA presentes en esa muestra | 102 |
| ATP/WTA con sede y coordenadas enlazadas | **102/102** |
| Cobertura del calendario completo, incluidos circuitos inferiores | **102/228 = 44,74 %** |
| Encuentros sin sede verificada | 126, agrupados en 37 entradas de torneo/modalidad/temporada |
| Filas cuya temporada declarada es 2025 y su fecha es 2026 | 48, marcadas para revisión |

La cobertura del 100 % se refiere solo a los encuentros ATP/WTA del archivo consultado, no al circuito mundial. Las entradas de Challenger/ITF y temporadas dudosas no se asignan por similitud del nombre de la ciudad.

## Recintos incorporados

Coordenadas representativas del recinto; no son una medición exacta de cada pista. La precisión espacial y la fuente quedan guardadas por registro.

| Edición | Recinto | Latitud | Longitud | Zona IANA |
|---|---|---:|---:|---|
| Almaty 2026 | Almaty Arena | 43,263767 | 76,817551 | Asia/Almaty |
| Lyon 2026 | LDLC Arena, Décines-Charpieu | 45,769346 | 4,979854 | Europe/Paris |
| Bruselas 2026, 17–22 oct. | ING Arena / Palais 12 | 50,901102 | 4,342211 | Europe/Brussels |
| Bruselas 2026, 23–25 oct. | Brussels Expo / Palais 5 | 50,899687 | 4,337208 | Europe/Brussels |
| Shanghai 2026 | Qizhong Tennis Center | 31,042086 | 121,355585 | Asia/Shanghai |
| Wuhan 2026 | Optics Valley International Tennis Center | 30,475576 | 114,456183 | Asia/Shanghai |
| Ningbo 2026 | Ningbo Yinzhou Tennis Center | 29,813180 | 121,554030 | Asia/Shanghai |
| Osaka 2026 | Morita Tennis Center Utsubo | 34,684662 | 135,492026 | Asia/Tokyo |

El organizador confirma que Bruselas cambia de Palais 12 a Palais 5 desde el 23 de octubre. Por eso una sola sede por torneo/año no basta: se guarda la vigencia de cada asignación. Lyon también se verifica como LDLC Arena, sin reutilizar la antigua ubicación de Marsella.

Superficie: Hard en los enlaces revisados. La clasificación indoor del catálogo del proveedor se conserva para Almaty, Lyon y Bruselas; la clasificación outdoor se contrasta con WTA para Wuhan, Ningbo y Osaka. Shanghai permanece con indoor desconocido en este registro y estado de techo desconocido: la geometría cartográfica indica cubierta móvil, lo que no demuestra cómo estará durante el encuentro. En ningún caso la clasificación estática demuestra el estado real del techo de una pista concreta.

## Implementación y garantías

Checkout: `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/`.

- `tennis_engine/venues.py`: registro relacional SQLite con fuentes, versiones de recintos y enlaces de torneos. Las tres tablas son de solo adición. Las correcciones generan revisiones, sin sobrescribir las anteriores.
- Cada campo conocido debe tener evidencia; coordenadas sin par completo, valores no finitos, zonas inválidas, ausencia de fuente y coordenadas etiquetadas como centro de ciudad se rechazan.
- La resolución requiere proveedor, ID, modalidad y temporada exactos. Usa la fecha local programada del encuentro y el intervalo de vigencia [inicio, fin), además de la versión registrada antes de la decisión.
- Enlaces solapados se devuelven como ambiguos. Una revisión posterior no cambia lo que podía saberse en una decisión anterior. No se retrodata la recepción de fuentes descargadas ahora.
- El enriquecimiento exige calendario explícitamente UTC y recepción anterior a la decisión. El constructor comprueba el hash del archivo y el recibo de API-Tennis.
- La sede obtenida es el recinto principal publicado del torneo. No acredita pista individual, presencia del jugador, itinerario, vuelo, hora de llegada, descanso ni estado del techo.
- Los datos nuevos se añaden como contexto separado. Los modelos y doce hashes del protocolo futuro anterior permanecen intactos.

El registro verifica integridad y cronología; la correspondencia semántica entre un campo y su fuente depende de la revisión explícita de la semilla. No pretende demostrar automáticamente que cualquier texto de internet es correcto.

## Fuentes y precisión

Las sedes y fechas se contrastaron con los organizadores, WTA y páginas oficiales municipales. Las coordenadas LDLC proceden de los datos estructurados del recinto oficial. Para los demás recintos se archivaron dos pequeñas extracciones de entidades OpenStreetMap y se revisaron sus nombres, IDs y geometrías. Se calculó un punto representativo de su extensión; el valor de precisión es una escala conservadora del recinto, no un certificado de exactitud topográfica. No se usó el centro de la ciudad ni una API de geocodificación genérica.

Geometría: **© OpenStreetMap contributors, ODbL 1.0**, [atribución y licencia](https://www.openstreetmap.org/copyright). Zonas horarias: tabla IANA archivada y validación con ZoneInfo. Las zonas se asignaron según la ubicación revisada; no se usaron offsets UTC fijos.

**Altitud (actualización posterior):** Open-Meteo respondió correctamente para los ocho recintos, mediante su endpoint gratuito sin clave. El usuario aclara que este proyecto de tenis no está monetizado; se utiliza el acceso no comercial y no se requiere contratar ni aportar una credencial. La referencia previa a Standard correspondía a otro contexto del repositorio y no es un requisito para este trabajo. Los valores son estimaciones del modelo Copernicus DEM 2021 GLO-90 (resolución horizontal de 90 m), no cotas medidas de la pista. Véase la actualización de Open-Meteo enlazada al final. La consulta anterior a Open Topo Data falló; no se utilizó para imputar valores.

Fuentes principales:

- [Almaty Open, organizador](https://almatyopen.ktf.kz/en/).
- [Grand Prix Auvergne-Rhône-Alpes, organizador](https://www.grandprix-auvergnerhonealpes.com/).
- [Bruselas: recintos y fechas](https://europeanopen.be/fr/infos-pratiques/).
- [Shanghai: información municipal de la edición 2026](https://english.shanghai.gov.cn/en-SportsEvents/20260930/192417b9890e468f83a85ff2478ba3a7.html).
- [Wuhan, WTA 2026](https://www.wtatennis.com/tournaments/1075/wuhan/2026).
- [Ningbo, WTA 2026](https://www.wtatennis.com/tournaments/2092/ningbo/2026).
- [Osaka, organizador 2026](https://www.japanopentennis.com/wta/en/tickets/).

## Archivos entregados y reproducción

En `data/tennis/venues_20261017/`:

- `registry_seed.json`: ocho recintos, quince enlaces, fuentes por campo, fechas de registro, alcance y atribución.
- `venues.sqlite`: registro relacional consultable por hora de decisión.
- `calendar_report_v2.json`: calendario enriquecido, cobertura y grupos pendientes. El ensayo v1 queda conservado.
- `originals/`: fuentes y recibos; `research_manifest.json` resume las páginas consultadas.

Desde el proyecto principal, con PYTHONPATH apuntando al directorio apps/tennis del checkout:

```text
python <checkout>/apps/tennis/scripts/build_venues.py --root data/tennis/venues_20261017 --probe-root .local/api_tennis_probe/20261017T211250Z --report <archivo_nuevo.json>
```

El comando reproduce la semilla existente sin red, verifica fuentes y no sobrescribe informes. Los archivos de datos quedan excluidos de Git.

## Validación y continuación

Pasaron **116 pruebas de tenis**, incluidas veinte nuevas. Cubren cambio de recinto a medianoche local, horario de verano, versiones, revisión de vigencia, enlaces ambiguos, modalidades/temporadas exactas, datos ausentes, alteración de fuentes y recepción del calendario posterior a la decisión. Los 24 hashes de fuentes se verificaron y no se encontró la clave de API-Tennis en estos entregables.

Actualización: las altitudes de los ocho recintos ya están incorporadas; véase [Open-Meteo y alcance no comercial](tenis_open_meteo_20261017.md). Sigue pendiente verificar recintos de circuitos inferiores y resolver las 48 discrepancias de temporada. Para viajes y clima, el registro ya proporciona contexto de sede; aún deben implementarse y evaluarse esas variables sin afirmar itinerarios reales ni convertir datos meteorológicos posteriores en previsiones históricas.

Verificacion general final: 1.300 aprobadas, 88 omitidas y dos avisos en 116,35 s; arnes correcto. Docker no disponible. El hash del modulo entregado y la semilla coinciden con calendar_report_v2.json.

Actualización 18-oct: los 126 encuentros pendientes ya tienen sede principal identificada y las 48 temporadas tienen corrección auditada. Véase [informe de cierre](tenis_sedes_temporadas_completadas_20261018.md). Las coordenadas nuevas siguen pendientes.
