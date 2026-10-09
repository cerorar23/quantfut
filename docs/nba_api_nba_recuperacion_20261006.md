# NBA: captura y conciliación de API-NBA — 6 de octubre de 2026

La clave proporcionada permite autenticación, pero su suscripción NBA efectiva es **Free**. Se capturaron **72 boxscores de 2022–23 a 2024–25 y 1,543 registros individuales**. **Ningún partido nuevo superó la conciliación completa**. El dataset aceptado sigue con **159,643 filas**; faltan **95 regulares y 57 de pretemporada**. Descargar candidatos no equivale a completar el histórico validado.

## Acceso real y presupuesto

`/status` inicial confirmó plan Free activo, cuota de 100 consultas diarias y consumo declarado cero. Dos consultas a temporada 2025 devolvieron HTTP 200 con error de aplicación: “Free plans do not have access to this season, try from 2022 to 2024.” No se reintentaron con otro mecanismo. Este bloqueo afecta **80 pendientes de 2025–26: 23 regulares y 57 de pretemporada**.

La consulta `/players/statistics?season=2024` también fue rechazada: la temporada no puede usarse sola. Se pasó a consultas por partido. Los tres calendarios accesibles contienen 1,391, 1,390 y 1,406 partidos respectivamente. Los 72 pendientes se cruzaron de forma única por temporada, fecha Eastern, nombres y localía; posteriormente se contrastaron marcador, duración y referencias.

Se realizaron **83 consultas a endpoints de datos**, incluyendo tres errores de aplicación, y dos comprobaciones `/status`. El máximo local era 95; las llamadas estuvieron separadas por al menos 6.3 segundos dentro de cada ejecución. La comprobación final del proveedor declaró **70/100 consultas consumidas**, equivalente a 30 disponibles en ese momento. Sus cabeceras de cuota fueron no monótonas y no coinciden exactamente con el recuento local; se conservan ambas medidas sin inventar una conciliación. La disponibilidad declarada por la guía pública no sustituye estos permisos observados.

**Sin suscripciones nuevas, cargos autorizados, ejecuciones Apify ni créditos The Odds API.** La captura usó el plan gratuito existente. La primera conexión desde el entorno restringido falló; la consulta autorizada con acceso de red funcionó. El error de transporte y ambos estados sanitizados se preservan.

## Precisión y resultado de validación

| Componente | Resultado |
|---|---|
| Boxscores capturados | 72 partidos; 1,543 registros individuales |
| Minutos individuales | Los 1,543 valores son enteros en formato string; cero incluyen segundos |
| Calendario | 72 cruces únicos; IDs API-Sports separados de IDs NBA |
| Totales de equipo de diagnóstico | Tres partidos; dos conflictos de rebotes conservados |
| Partidos incorporados al dataset | **0** |
| Histórico aceptado | 159,643 filas previas intactas; 6,055/6,150 regulares y 14/71 pretemporadas del inventario 2025–26 |
| Pendientes finales | **95 regulares y 57 pretemporadas** |

No se agregó `:00` a los minutos enteros, no se reparó `33:60` o `38:60` mediante esa información y no se infirió DNP desde la ausencia de una fila. Los minutos enteros solo corroboran un intervalo; los segundos de fuentes anteriores deben conservarse válidos o comprobarse mediante el adaptador congelado de la captura decimal de Flashscore. Este último sigue rechazando discrepancias con relojes previos válidos.

Se contrastaron las filas de jugador con identidades NBA del mismo partido/equipo y las filas independientes ESPN. Solo se normalizó la posición de un sufijo explícito que el proveedor coloca en el nombre, por ejemplo `Craig Jr. Porter` → `Craig Porter Jr.`. No se expandieron iniciales ni se adivinaron apodos. Se mantuvieron separados casos como `R. Rupert`, nombres contradictorios y filas sin identidad canónica inequívoca.

Persisten discrepancias individuales, por ejemplo Aaron Wiggins con 7 rebotes en API-NBA frente a 8 en ESPN, y Zeke Nnaji con 1 frente a 0. En los diagnósticos de equipo, API-NBA da Oklahoma City 53 rebotes frente a 54 en la referencia NBA/ESPN, y Denver 40 frente a 39. No se sobrescribieron referencias canónicas con la suma de jugadores o un solo proveedor. Los motivos de rechazo por partido están conservados en `recovery.json`.

## Evidencia y continuación

Originales, fechas de recepción, consultas sin encabezados secretos, hashes y estados de suscripción sin datos personales: `apps/nba/.local/raw/api_nba_20261006/`. Candidatos y conciliación: `apps/nba/.local/normalized/api_nba_20261006/`. La clave se configura exclusivamente en un archivo local excluido de Git; no figura en el informe, ledger, manifests ni snapshots de código.

Diez controles de corrupción verifican juego, equipo, nombre de equipo, duplicación, conteos negativos, descomposición de puntos/rebotes, reloj inválido, nombre ausente y equipo faltante. Se verifican las 181 evidencias anteriores y los 39 archivos NBA congelados. La revisión es propia; los hashes no tienen anclaje externo. NBA-RUN-035 registra este lote de investigación, sin entrenamiento, promoción de puertas, picks, Telegram o cambios de fútbol.

Arnés antes/después: **693 pruebas aprobadas** en ambas ejecuciones, una advertencia; Docker no disponible. Los cinco scripts de investigación compilan. Se conservaron los recibos, todos los originales capturados y snapshots de investigación en manifiestos separados de la credencial.

Para acceder a los 80 pendientes de 2025–26 hace falta permiso de temporada en API-NBA. **Pagar resolvería ese acceso, pero no acredita segundos individuales ni garantiza cerrar los boxscores.** Los 72 candidatos disponibles todavía requieren resolver relojes, identidades y discrepancias con una fuente que proporcione evidencia suficiente. Lesiones históricas, rotaciones y cuotas de props mantienen los huecos del informe anterior; no se recuperaron con estos endpoints.
