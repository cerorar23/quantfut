# NBA: revisión de 1xBet y Novibet México — RUN061

Fecha: 8 de octubre de 2026. Revisión de fuentes públicas y controles de admisión; misma autoría, sin aprobación independiente. El usuario pidió revisar estas dos casas mientras se resolvían fuentes de props y disponibilidad. Nuevas copias periódicas excluidas.

## Resultado para las dos casas

| Casa | Comprobación pública | Resultado para props individuales |
|---|---|---|
| Novibet México | Boston–Cleveland, evento e48091472: ganador, hándicap, totales del partido y de cada equipo; vista principal y creador revisados. Normativa mexicana legible en navegador. | Cero pares individuales PTS/REB/AST verificados en las vistas consultadas. No acredita ausencia en todos sus partidos ni en temporada regular. |
| 1xBet México | Catálogo NBA/pretemporada y eventos Boston–Cleveland y Lakers–Sacramento accesibles; reglamento español de baloncesto legible. PDF recuperado con HTTP200 y hash. | La interfaz anuncia numerosos mercados, pero las selecciones individuales no resultaron legibles. Estado: mercados sin verificar, no «no existen». Precios de combinadas promocionales excluidos. |

Fuentes: [partido Novibet](https://www.novibet.mx/apuestas-deportivas/preseason/bos-celtics-cle-cavaliers/e48091472), [normativa Novibet](https://www.novibet.mx/info/rules), [reglamento 1xBet](https://1xbet.com.mx/es/information/rules/10#4), [PDF 1xBet México](https://1xbet.com.mx/agreements-legacy-api/rulespdf), [Lakers–Sacramento 1xBet](https://1xbet.com.mx/es/line/basketball/12645-nba-preseason-matches/377552964-los-angeles-lakers-sacramento-kings).

## Reglas comprobadas y límites

En la sección de baloncesto de Novibet, los props de jugadores exigen entrar en cancha: una participación breve mantiene la apuesta aunque el jugador después sea sustituido o se retire; ninguna participación la anula. La prórroga cuenta salvo indicación contraria. En mercados de dos opciones, el empate con la línea devuelve la apuesta simple y liquida esa selección a 1.00 en una combinada. Los resultados proceden de la autoridad oficial y los cambios posteriores no modifican la liquidación. Los mercados de primer cuarto/primer anotador tienen requisitos específicos de titularidad; no se extrapolan a PTS/REB/AST de partido completo. La introducción da prioridad interpretativa al griego; esto se conserva como condición observada, sin resolver aquí su aplicabilidad contractual.

En 1xBet México, las estadísticas incluyen prórroga salvo excepción; la sección también distingue tiempo reglamentario, cuartos y mitades. No quedó acreditada una regla de no participación o retiro anticipado vinculada a un mercado individual PTS/REB/AST concreto. El PDF inglés y la sección española se conservan como fuentes distintas: no se supone equivalencia completa entre versiones. El PDF tiene 278 páginas; se extrajeron las páginas 35–37 y se inspeccionó visualmente la 35.

La normativa revisada todavía debe enlazarse con un mercado, jugador, partido, período, línea y ambas cuotas capturadas, con sus relojes. No se habilitó liquidación automática ni se declaró ningún contrato operativo verificado.

## Qué se recuperó para disponibilidad

La respuesta oficial de [NBA Boston–Cleveland](https://www.nba.com/game/bos-vs-cle-0012600011), recibida a 22:04:25 UTC antes del inicio oficial de 23:00 UTC, contiene 42 jugadores listados: 21 por equipo. Se preservaron sus IDs, nombres, equipo, partido y evidencia exacta. Un nombre incluye un carácter de sustitución en la propia fuente y queda señalado, sin corregirlo silenciosamente.

La lista no incluye confirmación individual de aptitud ni titularidad. Ambas listas de inactivos están vacías; eso no prueba que todos puedan jugar. ACTIVE tampoco equivale a autorización médica. El módulo rechaza evidencia de otro partido, IDs duplicados, equipos incompatibles, hashes incorrectos, recibos futuros y cortes desde el inicio.

El informe de revisión posterior conserva la lista previa, pero cierra la ventana de admisión de Boston–Cleveland porque ya comenzó. Las observaciones posteriores no se retrofechan. La siguiente captura admisible debe corresponder a un nuevo evento antes de su propio inicio.

## Otras comprobaciones y acceso

Betsson México mostró mercados de equipos para Detroit–Boston del 20 de octubre; no quedaron verificados props individuales en esa vista. El endpoint oficial NBA de boxscore respondió 403, mientras la página oficial del partido respondió 200. El PDF de La Bolita falló por conexión; el enlace de lesiones 2025–26 descubierto en la portada oficial expiró por tiempo de espera. No se infiere contenido inexistente de esos fallos.

Novibet fue legible en navegador, pero las solicitudes directas a partido, normativa y términos devolvieron 403. Esto permite una revisión manual y todavía no acredita un recolector automático funcional. No se gastaron créditos ZenRows ni OddsAPI en esta corrida. No se hicieron apuestas, registros de cuenta, compras, mensajes o cambios en el VPS.

El README de [kambi-sports-book](https://github.com/pdmuinck/kambi-sports-book), fijado al commit f1eee7a9e3f5885f38f1768329eebf999c6b76f4, documenta BetPlay Colombia; no se presentó como solución ya probada para México ni se ejecutó código del repositorio.

## Entrega reproducible y pendientes

El comando local `audit-event-listing` produce la lista oficial y un informe por evento/casa con los bloqueos concretos. Exige entrada cruda con hash, recibo, partido, corte previo, observaciones y directorio vacío; conserva salidas existentes. Complementa los controles de cuotas actuales, sin sustituirlos ni promover gates.

Persisten tres condiciones para una fuente operativa de props mexicanos: pares individuales con reloj verificable, reglas vinculadas al mercado concreto y disponibilidad explícita por jugador/partido. Ninguna casa revisada las reúne todavía. Las capturas actuales tampoco reconstruyen tickets ni recepción original histórica del usuario.

F6 permanece abierta; F7 y decisiones de gates sin promoción. Pruebas de esta entrega: 61 comprobaciones pertinentes, incluidos 16 controles nuevos del listado/revisión/comando. El cierre registra el resultado del arnés general y verifica todas las evidencias previas. Las observaciones del navegador son transcripciones de revisión, no cuerpos HTTP originales ni reloj del proveedor.

Evidencias: `apps/nba/.local/normalized/nba_f6_run61_20261008/`; controles en `apps/nba/src/nba/event_listing.py`. Se conservan las respuestas fallidas y los intentos locales fallidos. El sello externo anterior cubre el manifiesto RUN058; esta corrida tiene integridad local y no hereda ese sello.
