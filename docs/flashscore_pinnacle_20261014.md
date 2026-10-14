# Ensayo Flashscore con ZenRows — 14 de octubre de 2026

**Los dos scrapers leyeron cuotas, pero las muestras no aportaron ningún cierre
de Pinnacle. No se completó la lista de 6.185 partidos.** La descarga anterior de
OddsTrader conserva 272 candidatas anteriores al inicio, todavía sin acreditar
como cierre definitivo; las otras 5.913 filas siguen sin candidato.

Los datos encontrados se guardaron por petición del usuario en
[`data/pinnacle_recovery/20261014/`](../data/pinnacle_recovery/20261014/README.md),
con originales y manifiesto; las marcas de cierre sin verificar se mantienen.

Se usó el archivo existente `.local/cierres_faltantes_20261014.csv`, con hash
`3a418b365b51409bed24842cb7897ae5dea146b1740f4d778c80cbedaf9b1eaf`.
La ruta escrita después por el usuario omitía el separador antes de `.local`;
se utilizó el archivo que ya se había abierto y validado. No se sobrescribió.
No se escribió en producción ni se entrenó ningún modelo.

## Repositorios ejecutados

1. [omkarcloud/flashscore-scraper](https://github.com/omkarcloud/flashscore-scraper),
   commit `b1c54af09d893a5a56a52398f76845a111b4235e`.
   Se ejecutó su función `matches.get_odds` sin modificar los extractores,
   filtrando `HOME_DRAW_AWAY` y `FULL_TIME`. El JSON separa `value` de
   `opening_value`; no se tomó apertura como cierre. Para el ensayo con proxy,
   las tres consultas del scraper pasaron por ZenRows Universal Scraper API,
   `premium_proxy=true`, país Chile y encabezados de la fuente conservados.
   Se limitó a un intento por consulta y se archivó cada cuerpo y recibo.
2. [M3MONs/FlashscoreScraper](https://github.com/M3MONs/FlashscoreScraper),
   commit `334033fd2c273bf6c91c496fc230970a8f275a93`.
   Se ejecutó `scrape_odds` con Playwright conectado por CDP a ZenRows Browser
   Sessions, `proxy_country=cl` y sesión de tres minutos. La ruta que construye
   el repositorio para el enlace corto devolvía una página de error con resultado
   vacío. Se repitió con un adaptador local que conserva la URL canónica, el
   parámetro `mid` del partido histórico y el mercado de tiempo completo.
   Esta segunda ejecución sí produjo cinco casas y cinco ternas.

El segundo repositorio declara Python >=3.13; sus fuentes se ejecutaron en el
entorno aislado disponible de Python 3.12 con Playwright 1.63.0 y curl_cffi
0.14.0. La prueba no acredita compatibilidad de toda la aplicación con 3.12.
Los paquetes adicionales se instalaron bajo `.local/flashscore_trials_20261014/deps`.
No se cambiaron las dependencias de QuantFut ni los clones descargados.

Documentación del transporte:
[rotación residencial de ZenRows](https://docs.zenrows.com/fetch/features/premium-proxy)
y [conexión Playwright](https://docs.zenrows.com/browser-sessions/get-started/playwright).
La conexión WSS mantuvo verificación TLS; el contexto del sitio remoto usó
`ignore_https_errors=True`, igual que el ensayo anterior con OddsHarvester.

## Muestras

| Partido | Flashscore ID | Comprobación | Pinnacle |
| --- | --- | --- | ---: |
| Manchester United–Manchester City, 17-ene-2026 | Q5AqCTPG | Fila exacta pendiente; omkarcloud directo CA/CL y las tres consultas con proxy CL; M3MONs con navegador CL | 0 |
| UNAM Pumas–Cruz Azul, 25-may-2026 | ERoDGdUs | Fila exacta pendiente; omkarcloud, catálogo CL | 0 |
| Fulham–Manchester City, 25-may-2025 | QJFTcmK7 | Control antiguo con Pinnacle conocido en Football-data; seis catálogos regionales | 0 |
| Boca Juniors–Racing, 7-dic-2025 | veXijSYG | Control de Argentina, fuera de la lista exacta; omkarcloud, catálogo CL | 0 |

Para United–City se comprobaron los catálogos de Canadá, Chile, Finlandia, Perú,
Sudáfrica, India y México. El barrido adicional de países cambia `geoIpCode` de
la consulta pública de Flashscore y usa conexión directa; no son siete IP de
proxy comprobadas. Las pruebas explícitas de proxy y navegador usaron Chile.
El control de Fulham repitió FI/PE/ZA/IN/MX/CL.

Las regiones devolvieron casas como bet365, 1xBet, Unibet, Betfair, bwin,
William Hill, Sports Interaction, Caliente y Betano, según el país. No se usó
ninguna como sustituto de Pinnacle. En United–City, el scraper HTTP devolvió
seis mercados 1X2 y el scraper de interfaz cinco ternas; las cinco coinciden
exactamente por casa y selección con el JSON del primero.

La hora de la final de Liga MX difiere en una hora entre la lista y Flashscore;
se conservó la discrepancia y no se modificó ningún inicio canónico. La prueba
solo registra ausencia de Pinnacle en esa ficha, sin asociar precios ajenos.

Los accesos exitosos muestran que el bloqueo de IP no es la única limitación:
la respuesta leída debe contener la casa pedida. Estas muestras no demuestran
ausencia de Pinnacle en toda fecha, país, cuenta o interfaz de Flashscore. No se
ejecutaron 6.185 consultas individuales ni se declaró revisado cada partido allí.
Con las muestras actuales no se acreditó cobertura para completar el lote.

## Archivos y verificación

Directorio: `.local/flashscore_trials_20261014/`.

- `omkar-*/`: respuestas, recibos y JSON extraído, incluido el ensayo con proxy.
- `m3mons-cl-Q5AqCTPG/`: resultado inicial vacío y HTML que acredita la ruta fallida.
- `m3mons-cl-Q5AqCTPG-fixed-route/`: HTML y resultado de la repetición correcta.
- `geo-Q5AqCTPG/`, `geo-QJFTcmK7/`: originales y catálogos de seis regiones.
- `muestras.csv`, `verification.json`: resultados e integridad de 30 originales;
  cinco ternas comprobadas entre los dos extractores, cero Pinnacle nuevo.
- `pendientes_probados.json`: identifica las dos filas exactas de la lista
  comprobadas individualmente. Los controles adicionales están separados.
- `trial_omkar.py`, `trial_m3mons.py`, `geo_sweep.py`, `verify_trials.py`:
  adaptadores y comprobaciones reproducibles, con credencial solo en memoria.

El archivo con las 6.185 filas y los resultados de ambas investigaciones está
en `.local/sbr_pinnacle_20261014/cierres_faltantes_resultado_busqueda.csv`.
Sus columnas originales de cierre permanecen vacías. Las cuotas candidatas de
OddsTrader están en columnas aparte; Flashscore tiene estado, ID, regiones y URL
solo en las dos filas consultadas. Las demás señalan `sin_consulta_individual`.
Los hashes y recuentos finales están en `resultado_lista_usuario.json`.

Saldo observado de la cuenta compartida a las 21:46:56 UTC: límite 5.000,
usados 4.692, restantes 308. No se atribuye todo el uso de la cuenta a esta
investigación y no se compraron créditos.
