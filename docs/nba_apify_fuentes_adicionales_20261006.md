# Recuperación NBA con Apify — 6 de octubre de 2026

Se ejecutaron seis capturas acotadas en la cuenta existente. Se incorporó **un partido de pretemporada y 40 filas**; el dataset ahora contiene **159,643 filas**. Las 159,603 filas anteriores permanecen idénticas. No se entrenó el modelo ni se publicaron picks.

## Resultado y cobertura

| Componente | Resultado de este lote | Pendiente |
|---|---|---|
| Temporada regular | 6,055/6,150 partidos aceptados; sin ampliación en este lote | 95 boxscores |
| Pretemporada 2025–26 | 14/71 partidos aceptados; Clippers–Nuggets 0012500052 agregado | 57 boxscores |
| Calendario alternativo | 71 partidos únicos; 68 cruces exactos con calendario NBA por fecha Eastern, códigos local/visitante y marcador | Tres códigos extranjeros sin cruce exacto; no se forzaron alias |
| Rotaciones | Se mantienen 5,161 partidos/217,334 tramos previamente aceptados | 891 separados y tres regulares nuevos aún sin procesar; este actor no acredita quintetos cronológicos |
| Lesiones históricas | Se mantienen 486 PDFs; ninguna lesión histórica nueva aceptada | 330 fechas, cortes intradía y 13 nombres sin ID del lote anterior |
| Props prepartido | Se mantienen 20 partidos/40 snapshots/2,961 pares de rebotes de Odds API | Más partidos, puntos/asistencias y temporadas, con timestamp y reglas de liquidación |

No se certifica el histórico completo ni una plantilla histórica completa de DNP. El inventario de 71 pretemporadas corresponde a 2025–26, no a todas las temporadas históricas.

## Fuentes y gasto observado

| Captura | Registros exportados | Máximo por ejecución USD | Importe mostrado USD |
|---|---:|---:|---:|
| Action Network, 21/oct/2025, dos partidos | 2 juegos, con bloques anidados | 0.25 | 0.126 |
| Basketball API, búsqueda de competiciones NBA | 12 | 0.15 | 0.140 |
| Basketball API, temporadas de pretemporada | 9 | 0.40 | 0.185 |
| Basketball API, calendario de pretemporada 2025 | 71 | 1.40 | 1.115 |
| Basketball API, Pelicans–Melbourne | 15 jugadores, un solo equipo | 0.60 | 0.275 |
| Basketball API, Clippers–Nuggets | 30 participantes | 0.60 | 0.500 |

**Total mostrado: US$2.341**, cubierto con el crédito gratuito existente. Saldo mostrado: aproximadamente **US$0.45**. Cero créditos The Odds API consumidos, sin recargas ni suscripciones nuevas. Son importes observados en consola, no una factura auditada; la consola redondea el saldo a dos decimales.

Actores: [Basketball API Scraper](https://apify.com/sian.agency/basketball-api-scraper), [Action Network Scraper](https://apify.com/parseforge/action-network-scraper). Sus anuncios de cobertura no sustituyen las comprobaciones sobre los resultados capturados.

## Partido aceptado: identidad, reloj y conciliación

Clippers–Nuggets del 12/oct/2025, NBA `0012500052`, ESPN `401812709`, actor `14408858`: los 30 participantes incluyen `secondsPlayed`, además de minutos redondeados. Se usan los segundos explícitos; no se reconstruyen a partir de las décimas. Cada equipo suma exactamente 14,400 segundos y sus totales P/R/A coinciden con la referencia NBA. El marcador 94–102 y los cuartos coinciden entre calendario NBA, calendario alternativo y ESPN. Los minutos enteros ESPN corroboran el intervalo de un minuto, no cada segundo de forma independiente.

Las identidades se resuelven con nombres completos únicos y sufijos no contradictorios del archivo NBA; ambos equipos y cada participante se corroboran con ESPN. Se agregan diez DNP expresamente señalados por ESPN. No se infiere lesión a partir de DNP. Ocho controles de corrupción rechazan alteraciones de puntos, segundos, lado, duplicados, ID de partido, fecha, nombre y participación.

Hay **13 `teamId` contradictorios** en el segundo boxscore. Ese atributo se conserva como etiqueta no confiable de la ficha del jugador y **no determina su equipo en el partido ni se usa como variable prepartido**. El lado del boxscore se une con el calendario y la pertenencia histórica ESPN. No se afirma que todos esos atributos representen afiliaciones actuales sin verificarlo. El primer piloto también tiene etiquetas contradictorias y falta todo el equipo de Melbourne: sus 15 filas se preservan como candidatos, sin importar un partido incompleto.

## Props y lesiones: por qué este actor no completa sus históricos

Action Network devolvió 1,622 bloques de mercados anidados. Tras separar puntos/rebotes/asistencias y excluir las etiquetas de consenso/apertura como operadores ejecutables, quedan **385 precios candidatos de cuatro casas**, con **186 pares aritméticos Over/Under**. Se preservan aparte: no tienen el timestamp original de cada cuota, y una misma entidad presenta varias líneas sin cronología verificable. `scrapedAt` es la captura actual. El movimiento de líneas solicitado regresó vacío en ambos juegos. **Cero cuotas nuevas aceptadas para T60/T15, CLV o backtest prepartido**; no se califican como cierres confirmados ni se calcula ROI.

De 19 lesiones anexas a los dos partidos de octubre de 2025, **18 tienen actualización posterior al partido**. La restante tampoco acredita un reporte completo archivado a un corte prepartido. El bloque médico se excluye íntegramente como disponibilidad histórica. Las plantillas anexas tampoco certifican pertenencia histórica. Descargar este mismo actor masivamente no corrige esas carencias temporales.

## Evidencia y continuación

Originales completos, entradas, recibos, IDs de ejecuciones y hashes: `apps/nba/.local/raw/apify/additional_20261006/manifest.json`. Dataset y diagnóstico: `apps/nba/.local/normalized/apify_additional_20261006/`. Los informes del 5/oct permanecen sellados; este lote tiene su propio checkpoint, NBA-RUN-034.

Arnés antes/después: 609 pruebas, una advertencia; Docker no disponible. Se verifican los 39 archivos NBA congelados, el modelo/configuración y todas las evidencias anteriores. Revisión propia; hashes locales sin anclaje externo. G0–G9 siguen pendientes.

El servicio de boxscores es candidato para un lote mayor tras conciliar sus identidades y etiquetas; al precio observado en esta cuenta, 30 filas por partido cuestan US$0.50 incluyendo inicio. Diez partidos similares serían aproximadamente US$5, con tope propuesto US$6. Para 152 pendientes sería aproximadamente US$76 si todos tuvieran 30 filas; el número real de jugadores, duplicaciones, errores y tarifas por plan cambian el coste. **No garantiza cerrar esos 152 partidos**: las identidades NBA faltantes, los equipos extranjeros y las discrepancias siguen siendo requisitos independientes. El saldo actual no cubre ese siguiente lote; no se contrató otro plan ni se compró saldo.

La ampliación de props requiere una fuente que conserve tiempos de publicación/snapshots y mercados verificables. Las lesiones necesitan versiones históricas del reporte y las rotaciones necesitan sustituciones y quintetos, no únicamente anotaciones. Apify puede ejecutar conectores; no crea los datos históricos que el sitio fuente nunca conservó.
