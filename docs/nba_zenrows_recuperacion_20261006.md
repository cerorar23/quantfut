# NBA: recuperación mediante ZenRows — 6 de octubre de 2026

**Se usó ZenRows realmente para obtener fuentes públicas que fallaban desde este host. Basketball Reference funciona en la prueba; no se eliminaron todos los fallos.** El MCP instalado anteriormente solo había pasado el arranque/listado de herramientas. Esta ejecución llamó `account_usage` y `scrape` por stdio con el servidor configurado del proyecto y registró la descarga.

| Fuente probada | Resultado real por ZenRows |
|---|---|
| Basketball Reference: 17-dic-2022, endpoint `.cgi` del scraper | HTML de379060bytes; título/fecha correctos;152jugadores. Scraper upstream y parser propio coinciden. |
| CDN NBA: boxscore0012500012 | MCP devuelve ZenRows422/RESP001: el proveedor no pudo obtener contenido. No se declara desbloqueado. |
| Internet Archive: CDX de reportes2021 | Timeout del tool a110segundos; sin captura útil. La cancelación del cliente no prueba el resultado final del servidor remoto. |
| PDF NBA: Injury-Report_2023-10-24_01PM.pdf | ZenRows422/RESP001,148bytes JSON de error; no es PDF y no se importa. |

Los errores422 son respuestas de ZenRows; no se presentan como un nuevo403 del origen. No se puede distinguir con esta prueba entre un bloqueo persistente y una URL/archivo no disponible. Que GitHub permita descargar un repositorio tampoco garantiza acceso a las páginas de las que depende su scraper.

## Lo recuperado

Se incorpora Memphis–Oklahoma City, GameID`0022200443`, fecha17-dic-2022:23filas,22participantes y unDNP explícito del rosterNBA. La versión separada contiene161569filas y preserva las161546anteriores sin cambios. La cobertura regular sube a6056/6150; quedan94regulares y4pretemporadas.

La antigua referencia de Oklahoma City tenía54rebotes. El total actualNBAStats y los jugadores deBasketballReference coinciden en53. Se registra un overlay explícito `reference_overlay.json`:54→53, conservando el Parquet y la referencia antigua. No se reduce el umbral de reconciliación. IDs, equipo, fecha, localía y PRA individuales deben coincidir por nombre completo único dentro del partido; minutosMM:SS vienen deBasketballReference. El DNP se conserva únicamente porque está declarado por NBAStats, no por ausencia de la tabla diaria.

## Transporte y reproducción

El scraper original `jaebradley/basketball_reference_web_scraper` sigue intacto. El adaptador `run_bref_via_zenrows_20261006.py` intercepta su GET y obtiene elHTML mediante `scrape` del MCP, conserva recibo/hash, valida fecha y entrega el cuerpo al parser upstream. La captura de prueba se reutilizó para comprobar el adaptador sin repetir consumo. Nuevas fechas se guardan como staging y requieren auditoría antes de incorporarlas; no se importan automáticamente.

Ejemplo desde la raíz del proyecto, usando el runtime Python del entorno de trabajo:

```powershell
& 'C:\Users\huye\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' apps/nba/.local/reports/run_bref_via_zenrows_20261006.py 2023-11-02
```

Cada invocación admite1–4fechas distintas y como máximo4solicitudes nuevas/100créditos; no reintenta automáticamente ni compra saldo. No ejecutar una fecha ya producida sin revisar su recibo: las salidas existentes se preservan. El adaptador muestra el ámbito concreto conectado; instalar un MCP no redirige automáticamente todos los clientes Python/R de otros repositorios. Los scripts antiguos mantienen sus bloqueos registrados como evidencia histórica.

Se usó el modo adaptativo del servicio. La [documentación primaria de ZenRows](https://docs.zenrows.com/fetch/api-reference) indica que `mode=auto` selecciona rendering/proxies cuando hace falta y cobra la configuración exitosa. Las pruebas no acreditan quéIP se utilizó ni garantizan acceso universal.

La cuenta autenticada declara planFree/TRIALING,5000créditos de límite y uso observado final1:4999restantes al momento de la consulta. Límite local del piloto100créditos,cuatro solicitudes de scraping reservadas. El consumo puede reflejarse con demora y no se atribuye con precisión a un target solo por la primera consulta inmediata. No hubo compra, suscripción nueva o cambio de plan.

Para preservar bytes del PDF se usó ZenRows Fetch directamente con la misma credencial, además de los tres targets víaMCP: el servidorMCP2.4.0 decodifica todas las respuestas noimagen comoUTF8 y esa ruta no permite conservar unPDF original. No se acepta un PDF renderizado nuevo como reporte oficial histórico.

## Verificación y límites

Preservación exacta del dataset anterior, rosterNBA completo del nuevo partido,152acuerdos entre parsers y seis controles adversariales: referencia antigua aún se rechaza, desajustes entre fuentes, rebotes alterados, identidad desconocida, ausencia sinDNP y segundos60.39archivos propios NBA congelados y 304evidencias previas verifican. Harness706antes/706después; Docker no disponible. La suiteNBA172de la ejecución anterior corresponde al código propio que permanece intacto; en este lote se ejecutan controles del adaptador/dataset, no se atribuye una nueva ejecución de esa suite.

Se conserva el intento exploratorio de parserv1: el scraper devuelve tiros y no un campo`points`; la versiónv2 deriva puntos con2FGM+3PM+FTM para contrastar el campoPTS independiente. No se cambió código upstream o sus valores. El resultado aceptado es `zenrows_bref_v2_20261006`.

Artefactos:

- `apps/nba/.local/raw/zenrows_recovery_20261006/`: HTML,MCP responses,errores,recibos y consultas de uso sanitizadas.
- `apps/nba/.local/normalized/zenrows_bref_v2_20261006/player_games.jsonl.gz`: dataset combinado161569filas.
- `apps/nba/.local/normalized/zenrows_bref_v2_20261006/new_player_games.jsonl.gz`:23filas nuevas.
- `apps/nba/.local/normalized/zenrows_bref_v2_20261006/reference_overlay.json`:corrección corroborada y valores anteriores.
- `apps/nba/.local/normalized/zenrows_bref_v2_20261006/verification.json`:preservación y controles.

Se registra NBA-RUN-038 en el ledger local, sin modificar checkpoints previos, entrenamiento, modelo, puertas o picks. Las credenciales se leen de la configuración local ignorada y no aparecen en evidencias. Persisten la cobertura médica/props/rotaciones pendientes; acceder aHTML no acredita por sí solo que los datos estén completos o correctos.
