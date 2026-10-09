# Props NBA: captura funcional y reutilizable — 2026-10-08

El suministro de datos individuales queda resuelto para investigación: el
proyecto tiene una captura reutilizable que obtuvo 36 pares completos nuevos,
con línea, precio Over, precio Under, jugador, partido, mercado, reloj del
proveedor y recepción propia. Ya no depende de una muestra manual aislada.

| Fuente que respondió | Pares completos |
|---|---:|
| FanDuel | 15 |
| Sportsbet Australia | 15 |
| Fanatics | 6 |
| Total | 36 |

Cobertura de esta captura: 12 pares de puntos, 12 de rebotes y 12 de asistencias,
cinco jugadores y tres partidos regulares. Se consultaron ocho eventos futuros
de temporada regular y pretemporada. Hubo 19 respuestas API correctas y consumo
de 17/32 créditos, sin reintentos ni reservas pendientes. 33 pares tenían una
antigüedad de mercado inferior o igual a 60 segundos al recibirse; esa frescura
no se garantiza después de la captura.

Los 36 pares tienen ID NBA verificado: 23 mediante evidencia oficial ya
recibida y 13 mediante perfiles oficiales de Cade Cunningham y Shai
Gilgeous-Alexander consultados después de los precios. Se conserva esa
diferencia temporal; los nuevos perfiles no se presentan como conocidos en el
instante anterior del precio. Identidad no significa aptitud para jugar.

La captura histórica existente de 2617 pares permanece disponible, con sus
hashes y limitaciones originales: recepción nueva de datos históricos,
validación retrospectiva y sin recepción original acreditada antes del partido.

Los archivos reutilizables se encuentran en
`apps/nba/.local/normalized/nba_f6_run64_20261008`:

- `pairs_identified.json`: los 36 pares nuevos con identificadores y pruebas.
- `dataset_manifest.json`: enlaces y hashes del conjunto actual e histórico.
- `feed/coverage.json`: cobertura y ausencias por evento.
- `feed/raw/manifest.json`: recibos y consumo de cuenta.
- `identity_reference.json`: referencia oficial para la siguiente captura.

La ruta pública del programa es:

```text
python -m nba capture-props --credit-cap 32 --max-events 8 --key-file .env --output-dir CARPETA_NUEVA --identity-file apps/nba/.local/normalized/nba_f6_run64_20261008/identity_reference.json
```

Lee exclusivamente la clave del proveedor indicada; conserva cuerpos originales
sin secretos, limita créditos, selecciona partidos futuros y exporta pares.
No activa consultas periódicas ni cambia el VPS. Las cuatro versiones europeas
solicitadas siguen como selección independiente de mercados de equipos.

También se recuperaron cuatro páginas oficiales de Sportsbet y reglas de
Fanatics Nueva Jersey. La [guía de Sportsbet sobre mercados individuales](https://helpcentre.sportsbet.com.au/hc/en-us/articles/18431749993229-Player-Performance-Markets-Stats)
identifica los tres mercados y fuentes de resultados; sus guías acreditan
[anulación si no participa](https://helpcentre.sportsbet.com.au/hc/en-us/articles/18431742362125-My-Player-Did-Not-Play-What-Happens-To-My-Bet)
y [acción tras entrar, con prórroga incluida](https://helpcentre.sportsbet.com.au/hc/en-us/articles/18431779609101-Injured-And-Ejected-Players-In-NBA).
La [normativa de Fanatics NJ](https://sportsbook.fanatics.com/legal/nj/house-rules/)
incluye posibles anulaciones discrecionales por lesión; no se equipara a un
contrato sin esa excepción. FanDuel NY fue legible en la consulta web oficial,
pero la descarga directa devolvió 403, preservado en su recibo. No se atribuye
una cuenta o estado concreto a un feed estadounidense agregado.

El pendiente de fuente de precios queda cerrado con prueba real y programa
reutilizable. La admisión comercial sigue separada: las versiones US/AU no
acreditan contratos mexicanos; la disponibilidad final de eventos del 20–21 de
octubre se conocerá cerca del inicio; falta validación prospectiva. No se
relajaron validadores ni se publicaron apuestas. F6 sigue abierta por esos
requisitos; F7 permanece sin iniciar. Nuevas copias periódicas excluidas.

Verificación: reproducción offline de 19 recibos API, 36 pares, 36 identidades y
ocho recibos públicos; 40 pruebas pertinentes correctas. Arnés general: 798 pruebas
correctas y 16 omitidas. Revisión por el mismo autor; no aprobación independiente.
