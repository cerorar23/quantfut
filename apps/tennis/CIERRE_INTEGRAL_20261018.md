# Tenis: cierre de la revisión integral y estado del motor

La revisión cubre **las 73 entradas pendientes completas**. Se acreditaron 72 referencias; una conserva ambigüedad de campus y permanece excluida. Se integraron los datos, se repitió la evaluación probabilística y se auditaron los originales y los modelos. El motor funciona como herramienta de investigación; estos resultados no justifican activarlo para apuestas.

| Comprobación | Resultado |
|---|---:|
| Archivos originales conservados | 214 |
| Partidos canónicos conservados | 492.251 |
| Entradas revisadas en esta ejecución | 73 de 73 |
| Referencias geográficas nuevas acreditadas, incluidos alias | 72 |
| Registro georreferenciado total | 239 de 240 entradas |
| Destinos con coordenadas | 11.237 de 11.240 (99,97 %) |
| Casos con variables espaciales completas para ambos jugadores | 7.002 |
| Casos aptos tras controles de resultado y partición | 6.568 |
| Casos aptos excluyendo referencias de más de 1 km | 6.250 |
| Fuentes del registro verificadas por SHA-256 | 413 |
| Créditos de The Odds API consumidos en esta ejecución | 0 |

## Resultado probabilístico

Entrenamiento: 3.353 partidos de 2024. Evaluación común: 3.215 partidos de 2025, el 59,78 % de los 5.378 objetivos de ese año. Cada competición se mantiene en un único bloque. 2025 es exploratorio porque ya se inspeccionó; no se ha seleccionado una variante ni un parámetro usando sus resultados.

| Métrica | Base | Base + espaciales |
|---|---:|---:|
| Log-Loss | 0,6355017455 | 0,6354896454 |
| Brier | 0,2230228847 | 0,2230218362 |
| ECE, 10 intervalos | 0,0230183773 | 0,0230861881 |

La diferencia de Log-Loss es −0,0000121001; su intervalo descriptivo del 95 % por bloques de competición es [−0,0001324963; +0,0001126904]. Incluye cero y la ECE empeora ligeramente. **No hay mejora predictiva acreditada.** El remuestreo por competición no captura toda la dependencia entre jugadores ni corrige comparaciones múltiples.

La sensibilidad sin referencias de más de 1 km utiliza 3.207 casos de entrenamiento y 3.043 de evaluación: Log-Loss 0,6321622367 frente a 0,6321320708; el intervalo también incluye cero. Los dos escenarios se publican; no se elige el más favorable. Se añadieron comparaciones sobre los mismos 3.120 IDs del bloque anterior y los 2.833 originales, conservando etiquetas, variables y probabilidades base.

![Calibración e incertidumbre](C:/Users/huye/Documents/apuesta%20proyec/data/tennis/historical_geography_complete_20261018/comparison/calibration_comparison.png)

## Lo que significa la cobertura

Los 283 destinos recuperados no equivalen a 283 observaciones nuevas aptas: solo 126 casos adicionales pasan todos los filtros. Las fechas semanales, las ediciones anteriores sin sede, los cambios de huso ambiguos y los resultados no estándar mantienen exclusiones. Los 201 partidos de frontera siguen en cuarentena. No se salta una ubicación anterior desconocida para encontrar otra utilizable.

La distancia es geodésica entre torneos observados. No acredita una ruta personal, un vuelo ni el momento de llegada. El cambio de huso se calcula con zonas IANA y horario de verano; no es una medida fisiológica de jet lag. La elevación procede del terreno DEM; no mide la altura exacta de una pista, un edificio o una instalación subterránea. Las referencias amplias conservan un margen explícito y se excluyen en la sensibilidad.

## Única identidad histórica no resuelta

**Palm Hills, Líbano–Barbados, 12–13 septiembre de 2025: tres partidos individuales.** El proveedor del torneo da el nombre genérico del club. El propietario publica dos campus distintos, October y New Cairo, y fecha la apertura de New Cairo en mayo de 2025. Los puntos están separados por unos 60 km. No se hereda sin prueba el campus de 2024 ni se fusionan estas dos entradas. Se necesita una fuente específica de esta eliminatoria que identifique el campus; las dos alternativas están conservadas en el registro y no alimentan las probabilidades.

Fuentes: [clubes y coordenadas del propietario](https://www.palmhillsdevelopments.com/en-us/clubs/listing), [noticias y apertura de New Cairo](https://www.palmhillsdevelopments.com/en-us/media-center/news). Los vínculos de las ediciones históricas permanecen intactos.

## Auditoría de todo el motor

| Componente | Estado comprobado y límite |
|---|---|
| Ingesta e identidades | Originales, normalización y registro de alias implementados; los nombres ambiguos no se convierten automáticamente en identidad verificada. |
| Matemática | Saque/resto en escala logit, Markov de puntuación, incertidumbre y combinación Elo implementados; modelo estadístico clásico, sin computación cuántica. |
| Weighted Elo | Implementado con ecuaciones publicadas y adaptación declarada por bloques semanales. Ensayo conservado; sin promoción. |
| Evaluación común | Intersección de casos, cobertura, Log-Loss, Brier, ECE y controles temporales implementados. |
| Carga reciente | Extractor estricto 3/7 días y ajuste regularizado implementados. La muestra API-Tennis archivada tiene 152 terminales sin límite inferior finito de cierre; no permite estimar esas ventanas. |
| Carga por rondas | Ensayo histórico ejecutado sobre 1.957 casos comunes; mejora incierta. Es una variable distinta de carga diaria. |
| Espaciales | Revisión integral, husos, DEM, conjunto retrospectivo, sensibilidad y métricas ejecutados. No activados al no superar claramente la referencia. |
| Clima | Contratos de contexto y tratamiento de observaciones disponibles; falta una muestra meteorológica contemporánea validada y un ensayo que acredite valor. No se imputa techo abierto cuando es desconocido. |
| Cuotas | Cliente y archivo de The Odds API, selección dinámica por cobertura y siete claves de mercado conectados. Cobertura de la API y calibración no garantizan todos los mercados. |
| Liquidación | Perfil documentado de Pinnacle y tratamiento separado de retiros; otras casas/jurisdicciones necesitan reglas acreditadas antes de ROI. |
| Captura temporal | Captura acotada y sellado local implementados. API-Tennis figura como prueba/plan desconocido y sin cuota confirmada; no hay servicio automático activo. |
| Validación futura | Protocolo y doce artefactos congelados conservados. Hacen falta pronósticos emitidos antes del partido, cuotas ejecutables, cierres y resultados futuros. |

El conjunto retrospectivo usa evidencia recuperada en 2026; no demuestra disponibilidad de cada dato en 2024/2025. Los mercados derivados conservan calibración parcial y no forman con el híbrido de ganador una distribución conjunta recalibrada. No se puede afirmar rentabilidad, CLV positivo ni operación al 100 % con esta evidencia.

La comprobación integral de conservación pasó sin fallos. Conserva tres advertencias históricas: dos observaciones de calendario posteriores a un registro antiguo y la ausencia de linaje completo en el canónico antiguo. Las anomalías no se borran ni se convierten en muestras temporales válidas; existe una normalización v2 separada.

## Entrega y reproducción

Los scripts del motor aislado son `build_complete_geography.py`, `prepare_historical_dataset.py`, `compare_complete_geography.py`, `audit_complete_geography.py` `render_complete_geography.py`, `audit_engine_completion.py` y `smoke_complete_engine.py`. El constructor verifica fuentes, objetos exactos, puntos publicados, geometrías, dependencias de alias y el orden de las elevaciones. Los registros y experimentos exigen rutas de versión nuevas.

Carpeta de resultados: `data/tennis/historical_geography_complete_20261018/`. Contiene el registro, las 73 revisiones individuales, el conjunto de partidos, el protocolo previo al ajuste, predicciones, métricas, calibración y auditorías. `engine_integrity/audit.json` es la comprobación actual de originales/modelos; su inventario genérico de fases heredado queda sustituido por esta tabla y `engine_readiness.json`.

The Odds API sigue registrada como **plan de pago y límite de 2.000 créditos mensuales de tenis**, con la reserva de la cuenta compartida. Esta fase no consultó The Odds API ni API-Tennis. Se utilizó una consulta agrupada de Open-Meteo para 59 puntos nuevos; los alias reutilizan elevaciones verificadas. Fuentes cartográficas: OpenStreetMap contributors (ODbL), mapas publicados por operadores y coordenadas estructuradas contrastadas. Ningún resultado de búsqueda fallido se acepta como prueba.

Validación específica: **194 pruebas de tenis aprobadas**. Además, una prueba sin red con los modelos entrenados ATP y WTA verificó inferencia real, simetría al invertir los jugadores y conservación de la masa de la distribución conjunta. Sus parejas son hipotéticas; no son pronósticos para encuentros programados ni apuestas. El resultado está en `engine_smoke.json`. El arnés general aprobó **1.315 pruebas**, omitió 95 y produjo dos avisos en 127,50 segundos; Docker no está disponible. La igualdad de archivos entregados y las comprobaciones se registran en `engine_readiness.json` y `completion_manifest.json`.

## Registro completo de las 73 decisiones

| Recinto | Ciudad | Decisión | Margen espacial |
|---|---|---|---|
| SEB Arena | Vilnius | Alias con referencia acreditada | 500 m |
| Monte-Carlo Country Club | Roquebrune-Cap-Martin | Alias con referencia acreditada | 600 m |
| Domain Tennis Centre | Hobart | Alias con referencia acreditada | 700 m |
| National Tennis Center (Beeline Arena) | Astana | Alias con referencia acreditada | 700 m |
| Pat Rafter Arena | Brisbane, Australia | Alias con referencia acreditada | 600 m |
| Sportcampus Zuiderpark | The Hague, Netherlands | Referencia acreditada | 600 m |
| RT TORAX Arena | Ostrava, Czechia | Referencia acreditada | 600 m |
| Arena Gorzow | Gorzow Wielkopolski | Referencia acreditada | 500 m |
| Arena Varazdin | Varazdin | Referencia acreditada | 600 m |
| Peugeot Arena | Bratislava, Slovakia | Referencia acreditada | 600 m |
| RT Torax Arena - Sareza | Ostrava | Alias con referencia acreditada | 600 m |
| Peugeot Arena | Bratislava, Slovakia | Alias con referencia acreditada | 600 m |
| El Gezira Sporting Club | Cairo | Referencia acreditada | 1400 m |
| Radomskie Centrum Sportu | Radom, Poland | Referencia acreditada | 600 m |
| Tatabányai Multifunkcionális Sportcsarnok | Tatabánya | Referencia acreditada | 600 m |
| Tennis Club de l'Avenir Sportif de la Marsa | Tunis | Referencia acreditada | 700 m |
| Partille Arena | Gothenburg | Referencia acreditada | 600 m |
| Cordoba Lawn Tennis Club | Cordoba | Referencia acreditada | 600 m |
| S M Krishna Tennis Stadium | Bengaluru | Referencia acreditada | 600 m |
| Guangzhou Development District International Tennis School | Guangzhou | Referencia acreditada | 800 m |
| Carrasco Lawn Tennis Club | Montevideo | Referencia acreditada | 700 m |
| TENIS ESKRIM DAGCILIK KULÜBÜ (TED Club) | Istanbul | Referencia acreditada | 700 m |
| Courts de tennis de la cité nationale sportive el menzah | Tunis | Referencia acreditada | 700 m |
| Courts de Tennis - Cité Nationale Sportive El Menzah | Tunis | Alias con referencia acreditada | 700 m |
| Centro Nacional De Tenis Parque Del Este | Santo Domingo Este | Referencia acreditada | 700 m |
| Hacienda San Javier | Guadalajara | Referencia acreditada | 700 m |
| Forus Tennisecenter Tondi | Tallinn | Referencia acreditada | 600 m |
| Nadderud Arena | Oslo | Referencia acreditada | 600 m |
| The Royal Tennis Hall (Kungl. Tennishallen) | Stockholm | Referencia acreditada | 600 m |
| Sport Ireland National Indoor Arena | Dublin | Referencia acreditada | 700 m |
| Gjovik Olympic Cavern Hall | Gjovik | Referencia acreditada | 700 m |
| Kalev Sports Hall | Tallinn | Referencia acreditada | 600 m |
| National Tennis Center | Bridgetown | Referencia acreditada | 700 m |
| Net Tennis Academy | Riyadh | Referencia acreditada | 500 m |
| Polsat Puls Arena | Gdynia | Referencia acreditada | 600 m |
| Las Palmas Country Club | Santa Cruz Barrio Las Palmas | Referencia acreditada | 1200 m |
| Groenkloof Tennis Club | Pretoria | Referencia acreditada | 500 m |
| Royal Tennis Club de Marrakech | Marrakech | Alias con referencia acreditada | 600 m |
| Sri Lanka Lawn Tennis Association Complex | Colombo | Referencia acreditada | 700 m |
| Tennis Club Ismaning | Ismaning | Referencia acreditada | 650 m |
| TC Lokomotiv | Plovdiv | Referencia acreditada | 650 m |
| Tennis Club Lokomotiv | Plovdiv | Alias con referencia acreditada | 650 m |
| Court Central, Estadio Nacional | Santiago | Referencia acreditada | 500 m |
| Parque Deportivo Estadio Nacional, Court Central, Anita Lizana | Santiago | Alias con referencia acreditada | 500 m |
| UL Sport Arena | Limerick | Referencia acreditada | 700 m |
| O.A.K.A. - Spyros Louis - Stadio 2020 | Athens | Referencia acreditada | 900 m |
| Liossia Olympic Sports Hall | Athens | Referencia acreditada | 700 m |
| Sportaktivpark Bad Waltersdorf | Bad Waltersdorf | Referencia acreditada | 600 m |
| Coque | Luxenbourg | Referencia acreditada | 900 m |
| Megasaray Club Belek | Belek, Antalya | Referencia acreditada | 2300 m |
| Alex Metreveli Tennis Complex "Mziuri" | Tbilisi | Referencia acreditada | 600 m |
| Ace Tennis Club | Athens | Referencia acreditada | 650 m |
| Cancha Estadio Rafael Arévalo | Santa Tecla | Alias con referencia acreditada | 700 m |
| Federación Salvadoreña de Tenis | Santa Tecla | Alias con referencia acreditada | 700 m |
| Eric Bell National Tennis Centre | Kingston 5 | Referencia acreditada | 500 m |
| Pakistan Sports Complex | Islamabad | Referencia acreditada | 650 m |
| Stade de tennis FTT | LOME | Referencia acreditada | 700 m |
| Club de Tenis Puente Romano | Marbella | Referencia acreditada | 600 m |
| Vitality Slezsko | Trinec | Referencia acreditada | 900 m |
| Club Bellavista Colsubsidio | Bogota | Referencia acreditada | 800 m |
| Bourbon Beans Dome | Miki | Referencia acreditada | 600 m |
| Chuncheon Songam Sports Park Tennis Court | Chuncheon | Referencia acreditada | 900 m |
| DLTA Complex | New Delhi | Referencia acreditada | 700 m |
| Sport Hall Ibar Kraljevo | Kraljevo | Referencia acreditada | 650 m |
| Sakhovat Sport Servis | Tashkent | Referencia acreditada | 900 m |
| Smash Sporting Club | Cairo | Referencia acreditada | 800 m |
| Central Tennis Club | Windhoek | Referencia acreditada | 800 m |
| Complejo de Raquetas | Ibague | Referencia acreditada | 1000 m |
| Olympic Tennis School | Tashkent | Referencia acreditada | 900 m |
| New Sport Palace | Tbilisi | Referencia acreditada | 900 m |
| Salinas Golf y Tenis Club | Salinas | Referencia acreditada | 1000 m |
| Palm Hills Sports Club | Cairo | Referencia acreditada | 1000 m |
| Palm Hills Sports Club | Cairo | Campus histórico ambiguo; excluido | No asignado |
