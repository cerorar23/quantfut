# NBA 1.7.0 — recalibración con la temporada actual, fuerza individual activa y revisiones de lo publicado

Instrucción del titular (26-oct-2026): recalibrar todo aunque ya esté sellado o publicado, dejar el ajuste de fuerza
activo en el motor en vivo, entrenar con los partidos y jugadores de la nueva temporada, auditar que toda la data esté
dentro del motor y corregir en el momento lo que aparezca.

## Datos que entran al motor

| Conjunto | Partidos | Filas de jugador | Columnas faltantes |
|---|---|---|---|
| Histórico consolidado 2021-22 a 2025-26 (regular, play-in, playoffs) | 6.509 | 169.138 | 0 |
| Temporada 2026-27 hasta el 25-oct (cajas oficiales finales) | 43 | 1.489 (524 jugadores) | 0 |
| Total del reajuste | 6.552 | 170.627 (1.125 jugadores) | 0 |

- Las 95 cajas que faltaban se cerraron: 86 recuperadas por proxy y 9 en cuarentena reparadas con la caja oficial
  (`official_repairs.py`): siete con segundos `:60`, un duplicado vacío que ocultaba a Lester Quiñones y dos tiros
  libres de Bol Bol con 0:00. Los originales no se editan; cada corrección queda en el informe.
- La auditoría encontró que las cajas de la temporada actual descartaban `fgm`, `ftm`, `fg3a`, `dreb`, `pf` y `+/-`
  (969 filas). Ahora se leen y la caché 1.4-1.6 se descarga de nuevo: 0 columnas faltantes.
- Reporte de lesiones: 18 reportes de la temporada actual, 329 filas, 0 nombres sin resolver (antes «Udeh, Jr.,
  Ernest» no se enlazaba por el sufijo separado).

## Qué cambia en el modelo

- Entrenamiento con las dos temporadas completas previas más todos los partidos validados de la actual anteriores al
  corte (26-oct; nada del mismo día ni futuro). Indicador de postemporada en equipo y jugadores.
- Fuerza individual (ridge 25, peso 0,25) **activa** en ganador, puntos de equipo y total, con plantillas oficiales y
  actualización con cada partido nuevo. Su mejora histórica sigue sin ser concluyente; se activa por instrucción.
- Rol actual: los minutos recientes en el equipo actual actualizan el rol; pocos partidos añaden varianza.
- Hallazgo y corrección: con los playoffs ya en la base, al inicio de temporada los últimos 20 partidos de cada jugador
  eran casi todos de playoffs (Brunson 19 de 20). Un partido de temporada regular usa ahora solo partidos de temporada
  regular para el historial individual; los playoffs siguen en el ajuste de equipo y de fuerza.

## Revisiones de lo ya publicado

Cada recálculo es una revisión aparte en `cohorts/<cohorte>/updates/<fecha>/` con sello propio: el original sellado
no se toca. Reglas verificadas al leer:

- Un partido ya iniciado se recalcula con el modelo nuevo pero **solo con información anterior a su fecha** (incluida
  la fuerza individual reajustada a esa fecha), conserva exactamente los pronósticos publicados y queda marcado
  «recalculado después del inicio: no cuenta en el marcador».
- El marcador de aciertos cuenta, por pronóstico, la versión más reciente calculada antes del salto.
- Un partido pendiente se actualiza en vivo (cada pasada del productor, después de sellar) y puede ganar pronósticos.
- Una revisión idéntica a la anterior se descarta (cada revisión guarda ~2,4 MB de plantillas).
- Una cohorte con evidencia rota no detiene las demás; el error queda en el registro de la pasada.

Fuga conocida y declarada: los parámetros del modelo se entrenaron con los 43 partidos ya jugados, así que un
recálculo posterior de esos partidos no es una prueba independiente. Por eso nunca cuenta en el marcador.

## Comparación con los resultados oficiales (ensayo sobre copia de las 18 cohortes)

1.061 pronósticos con resultado (Brier, menor es mejor):

| Mercado | n | Original | 1.7 |
|---|---|---|---|
| Total del partido | 36 | 0,2215 | 0,2041 |
| Puntos de equipo | 72 | 0,2062 | 0,2097 |
| Ganador | 36 | 0,2019 | 0,2119 |
| Puntos de jugador | 129 | 0,2740 | 0,2714 |
| Rebotes | 120 | 0,2527 | 0,2518 |
| Asistencias | 105 | 0,2584 | 0,2560 |
| Puntos + asistencias | 94 | 0,2509 | 0,2575 |
| Puntos + rebotes | 116 | 0,2593 | 0,2623 |
| Todos | 1.061 | 0,2482 | 0,2490 |

Sin la corrección de roles de temporada regular el total era 0,2518. Una semana de partidos no distingue estas
diferencias del azar; el total del partido es la mejora más clara y el ganador la peor. El seguimiento prospectivo
(solo versiones previas al salto) es lo que decidirá.
