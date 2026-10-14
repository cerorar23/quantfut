# Búsqueda de Pinnacle sobre la lista exacta de 6.185 partidos

Fecha: 14 de octubre de 2026. Ensayo de captura y asociación; cero escrituras
en producción. El archivo original del usuario permanece intacto.

Copia guardada y versionada por petición del usuario:
[`data/pinnacle_recovery/20261014/`](../data/pinnacle_recovery/20261014/README.md).
Contiene las 272 candidatas, las 586 ternas, la lista completa, originales,
evidencia de asociación y un manifiesto de integridad; siguen sin ser cierres
definitivos aprobados para carga.

## Resultado

Entrada: `.local/cierres_faltantes_20261014.csv`, 6.185 filas únicas de 23
competiciones. SHA-256:
`3a418b365b51409bed24842cb7897ae5dea146b1740f4d778c80cbedaf9b1eaf`.
Sus identificadores coinciden exactamente con los pendientes de la instantánea
de producción del 14-oct a las 19:01:51 UTC.

Se obtuvieron 586 ternas históricas del proveedor 20, mercado 1X2 de partido
completo, con precios decimales válidos y actualizaciones anteriores al inicio
en las últimas 24 horas. De ellas, **272 encajan con partidos del archivo**:

| Competición | Candidatos | Pendientes originales |
| --- | ---: | ---: |
| Champions League | 147 | 305 |
| Europa League | 114 | 208 |
| Championship | 9 | 389 |
| Liga MX | 2 | 282 |
| Otras 19 competiciones | 0 | 5.001 |
| Total | 272 | 6.185 |

Los candidatos abarcan del 13-feb-2024 al 27-ago-2025. **No se consiguieron
candidatos nuevos de 2026**. Quedan 5.913 filas sin candidato; en la base siguen
faltando los 6.185 cierres porque no se cargó nada ni se acreditó todavía que
las últimas cuotas archivadas sean el cierre definitivo.

La consulta `currentLines` devuelve la última cuota archivada de cada selección.
Eso no acredita por sí solo la integridad del historial ni que no falten cambios
posteriores. Los CSV señalan `close_verified=False` y
`price_type=latest_archived_pre_match_currentLines`; no son un archivo de cierres
finales aprobado para entrenamiento. La fecha de recepción corresponde a la
captura real de 2026, no se retrocede al día del partido.

## PySBR y los proxies

Se instaló `python-sbr==0.3.2` en un directorio aislado, sin cambiar las
dependencias de la aplicación. Su `Sportsbook().id('Pinnacle')` devuelve 20.
La llamada real `CurrentLines` del paquete, con un transporte adaptado, devolvió
tres cuotas que coinciden exactamente con la descarga histórica de control.

El endpoint original de SBR devuelve 404; añadir un proxy no corrige una dirección
retirada. La adaptación usa el GraphQL de OddsTrader:
`https://www.oddstrader.com/odds-v2/odds-v2-service`.

La prueba explícita utilizó ZenRows Universal Scraper API con
`premium_proxy=true` y `proxy_country=gb`, conforme a su documentación de
rotación residencial. Devolvió HTTP 200 y tres cuotas. Una segunda prueba con
`proxy_country=nl` devolvió HTTP 422, código RESP001; no se oculta ese fallo ni
se declara éxito en ambas regiones. No se compraron créditos ni se cambiaron
suscripciones. Se utilizaron las credenciales existentes sin incluirlas en archivos
de resultados.

Los recibos `pysbr-residential-gb.*` y `pysbr-residential-nl.*` conservan país,
parámetros, URL de destino, recepción y hash del cuerpo. La IP concreta de salida
no se observó; la rotación automática es la función documentada del proveedor.

El catálogo antiguo de PySBR identifica Pinnacle como proveedor 20; el proveedor
10 corresponde a Bookmaker/betcris en esa configuración. Existe una contradicción
con el mapeo de `sbrscrape 0.0.12`, que etiqueta 10 como Pinnacle. Se conservó el
control del 25-may-2025 contra PSCH/PSCD/PSCA de Football-data, favorable al
proveedor 20, y sus metadatos `leagueid`/`periodNumber`. El catálogo actual de
casas no responde, por lo que también debe conservarse esta limitación al revisar
las candidatas; no se utilizó el proveedor 10 como sustituto de Pinnacle.

Referencias: [PySBR, archivado en 2022](https://github.com/JeMorriso/PySBR),
[Premium Proxy y rotación](https://docs.zenrows.com/fetch/features/premium-proxy),
[sbrscrape](https://github.com/nkgilley/sbrscrape).

## Cobertura y controles

Se consultaron 149 combinaciones de competición y mes que contienen huecos,
correspondientes a 13 identificadores de liga documentados o comprobados. Se
agruparon en 25 consultas, con coste comunicado de un crédito cada una. Se
archivaron los 25 originales y sus recibos; las consultas devolvieron 3.624
eventos únicos. Ningún bloque alcanzó el límite de 1.000 eventos.

- 2.994 eventos no traían líneas del proveedor 20.
- 32 no estaban terminados.
- 12 tenían al menos una cuota con más de 24 horas de antigüedad.
- 586 pasaron esos filtros: 272 pendientes asociados, 39 con cierre ya existente,
  266 sin partido exacto y nueve discrepancias de marcador reglamentario.

La asociación exige competición, equivalencias explícitas de nombres o alias
registrados, partido único dentro de ±36 horas y mismo marcador a 90 minutos.
No usa similitud difusa. Las equivalencias adicionales están en
`equivalencias_revisadas.json` y su traducción a IDs en
`equivalencias_con_ids.json`. Son locales al ensayo; no modifican equipos ni
alias en producción. Las nueve discrepancias, principalmente partidos con
prórroga, se excluyeron de los candidatos; no se cambió el marcador de la base.

Para las 6.185 filas, el resultado distingue:

| Estado de búsqueda SBR | Filas |
| --- | ---: |
| Candidato anterior al inicio, cierre sin verificar | 272 |
| Mes consultado, sin candidato validado | 2.419 |
| Mes consultado, sin eventos devueltos | 773 |
| Identificador de competición SBR sin resolver | 2.721 |

La última categoría comprende Argentina, Suiza, Bundesliga 2, Dinamarca, LaLiga 2,
Ligue 2, Serie B, Noruega, Suecia y Turquía. Los catálogos/buscadores antiguos
devuelven errores de servicios internos ausentes. No se inventaron sus IDs ni
se presentan como búsquedas individuales realizadas en SBR. Los 773 sin eventos
corresponden a Brasil, Países Bajos y Portugal; un resultado vacío tampoco prueba
ausencia universal de datos.

El ensayo previo de los CSV de Football-data cubrió las 21 ligas domésticas y no
aportó cierres nuevos. Champions y Europa League no tienen CSV en ese ensayo.
Ver `docs/pinnacle_recuperacion_20261014.md` para los 60 originales y su validación.

También se ejecutó el repositorio `moeinsh/football-odds-scraper`: produjo diez
partidos futuros con cuotas genéricas; no identifica Pinnacle ni recupera cierres.
Se amplió el ensayo leyendo la ficha y la consulta pública de cuotas de
Manchester United–Manchester City del 17-ene-2026, primer pendiente de Premier.
BetExplorer devolvió otras casas, ninguna Pinnacle, tanto por conexión local como
por ZenRows residencial de Canadá. Ambos cuerpos de cuotas coinciden en hash.
Es una prueba de esa ficha, no prueba de ausencia en todo BetExplorer.

## Archivos

Todos los resultados están en `.local/sbr_pinnacle_20261014/`:

- `cierres_faltantes_resultado_busqueda.csv`: las 6.185 filas, columnas originales
  intactas, estado de búsqueda y columnas separadas para cuotas candidatas.
- `pinnacle_candidatos_pendientes.csv`: 272 ternas asociadas, nombres originales
  de la fuente, horas UTC por selección, URL, captura y hash.
- `cierres_sin_candidato.csv`: las otras 5.913 filas.
- `cobertura_por_liga.csv`: las 23 competiciones y los recuentos por estado.
- `pinnacle_ternas_historicas.csv`: las 586 ternas válidas, incluidas las que no
  encajan o ya estaban completas en la base.
- `resultado_lista_usuario.json`: integridad de la entrada y hashes/recuentos de
  los cinco CSV finales; `normalization-report.json`: filtros y exclusiones.
- `collection/`: originales y recibos por consulta; scripts locales reproducen
  la descarga acotada, normalización, prueba de PySBR y cruce con la lista.

Las comprobaciones verifican unicidad de partido, inclusión de los 272 IDs en
la lista exacta, precios válidos, suma 272 + 5.913 = 6.185, hashes de originales,
ausencia de truncamiento y conservación de los campos de cierre originales
vacíos. No se declaró desbloqueado el modelo de residuo.

Ampliación posterior: también se probaron los dos repositorios Flashscore
solicitados, con transporte residencial/navegador de ZenRows. Cero cierres
Pinnacle nuevos en sus muestras; detalle en `docs/flashscore_pinnacle_20261014.md`.
El resultado por fila añade el estado de la muestra Flashscore y diferencia
las dos filas consultadas de las que no se consultaron individualmente allí.
