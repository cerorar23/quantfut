# xG API-Football conectado al entrenamiento — 12 de octubre de 2026

Decisión del usuario: conectar el xG actual de API-Football al entrenamiento.
La fuente ya entrega valores recientes en las once ligas y las dos copas del
catálogo; su cobertura no es completa. La consulta directa confirmó que el
proveedor también corrige valores después de que el resultado se haya cerrado.

## Resultado en producción

- Conexión desplegada en el worker, persistida en `quantfut-worker:latest`.
- Primera pasada de 35 días: **182 consultas, 149 parejas válidas, 33 ausentes,
  cero errores**, sin alcanzar la reserva de cuota.
- El cargador de entrenamiento recibe **148** de las 149 parejas. Sporting–
  Galatasaray queda fuera por el filtro previo de liga doméstica: Turquía aún
  no tiene el modelo habilitado. No se cambia esa regla para aumentar el conteo.
- Conjunto de entrenamiento comprobado: 49.505 partidos; protección temporal
  verificada sobre todas las filas de la nueva fuente.
- El modelo activo sigue siendo `2026.09.27-010508`. Por autorización del
  usuario, el entrenamiento `2026.10.12-221104` terminó a las 20:55 CDMX del
  12-oct, tras 4 h 44 min. Usó 49.504 partidos y las 148 parejas de esta fuente,
  pero no se activó: RPS 0,19873 frente a Elo 0,19657 en 1.051 partidos comunes
  (menor es mejor). Conserva las puertas existentes y quedó registrado como
  candidato. Ver `entrenamiento_xg_20261012.md`.

| Competición | Parejas de xG capturadas |
|---|---:|
| Argentina | 23 |
| Brasil A | 18 |
| Bundesliga | 9 |
| LaLiga | 9 |
| Champions | 5 |
| Europa League | 2 |
| Ligue 1 | 9 |
| Premier League | 10 |
| Serie A | 10 |
| Liga MX | 13 |
| Eredivisie | 9 |
| Primeira | 9 |
| MLS | 23 |

Estas cantidades describen la primera carga elegible, no porcentajes de
cobertura de todos los partidos históricos. Solo se reconsultan partidos
terminados con ID API-Football y equipos identificados. No se han atribuido
IDs a partidos antiguos por aproximación ni descargado todo el histórico.

## Captura y disponibilidad

`ingest/results.py` aprovecha la misma respuesta de estadísticas que ya pedía
al cerrar el partido: cero consultas adicionales. `ingest/xg_api_football.py`
exige ambos equipos, una sola entrada por equipo/tipo y valores finitos no
negativos; cero es válido, null no. Guarda decimales sin convertirlos a entero.

La migración aditiva `db/061_api_football_xg.sql` añade `xg_source` y
`xg_api_checked_at`. Se guardan ambos xG juntos, únicamente si los dos campos
siguen vacíos y el partido está terminado. `xg_source=api_football` distingue
las nuevas observaciones; `xg_recorded_at=now()` acredita su recepción real.
Una revisión posterior del proveedor no sobrescribe la primera observación,
y tampoco se reemplaza el xG histórico anterior.

La reconsulta diaria está instalada a **12:10 UTC / 06:10 Ciudad de México**,
antes del sellado diario de las 07:00. Revisa los últimos 35 días, máximo 100
partidos por pasada, espera 20 horas entre intentos y reserva el 15% de la cuota.
Un bloqueo advisory evita dos pasadas simultáneas. Si el presupuesto es
desconocido o insuficiente, se detiene; los fallos se registran y no se sigue
consumiendo con presupuesto sin verificar. El resumen queda en `ingest_health`.

## Entrenamiento y evaluación

El cargador incorpora `xg_source` y `xg_recorded_at`, por lo que ambos forman
parte del hash del dataset. La huella del código incluye la nueva protección
de disponibilidad y los módulos de más-menos/valor de jugadores.

- Dixon-Coles usa la nueva fuente solo si su captura es anterior o igual al
  corte del ajuste. Una captura posterior o sin timestamp usa goles en ese
  ajuste. El mismo control se aplica al ajuste final y a cada paso del backtest.
- Más-menos de jugadores calcula el objetivo de cada reajuste con el xG que
  estaba disponible en ese corte; el cargador del challenger conserva el origen.
- El replay secuencial de Kalman aún no procesa eventos de llegada tardía:
  usa goles para las filas de API-Football. No inyecta en el pasado el xG recién
  descargado. No se cambió su método para el histórico anterior.

El xG anterior conserva su tratamiento previo y su origen queda NULL. No se
acredita retrospectivamente la primera recepción de esos datos; este cambio
protege la nueva fuente, no convierte todo el histórico en point-in-time.

## Verificación y despliegue

- 970 pruebas aprobadas, 22 omitidas y dos advertencias de dependencias.
- 79 pruebas dirigidas al entrenamiento/modelos y ocho escenarios en
  PostgreSQL con tablas temporales y rollback, sin alterar filas reales.
- 117 módulos Python comprobados sintácticamente. Arnés del proyecto ejecutado.
- Paquete cotejado contra el código vigente del worker antes de modificarlo;
  ocho archivos verificados también dentro de la imagen persistida.
- `hashchain verify`: **14 lotes correctos**. Configuración, calendario móvil y
  ficha del modelo responden 200. No se modificaron picks, lotes sellados ni API.
- Evidencia local: `.local/xg_api_20261012/verification_live.json`, snapshots
  anteriores, paquete/manifest y pruebas PostgreSQL en esa misma carpeta.

Paquete y respaldos del servidor:
`/home/qf/quantfut/deployments/xg-api-20261012/`; imagen anterior:
`quantfut-worker:xg-before-20261012`. Se actualizó el worker en marcha y su
imagen, sin reiniciarlo ni alterar servicios NBA o la API. El checkout antiguo
del VPS continúa sin reconciliar: una reconstrucción debe conservar las fuentes
exactas desplegadas o partir de la imagen vigente.

Para retirar la captura, restaurar solo `ingest/results.py` y el crontab desde
`before/` y persistir esa retirada. Conservar la migración y las protecciones
del entrenamiento mientras existan filas de la nueva fuente: restaurar un
entrenador antiguo sobre esos datos perdería su control de disponibilidad.

Pendientes: vigilar cobertura sostenida, recuperar más histórico si se decide
su alcance y evaluar el siguiente candidato con las puertas habituales. La fase
1 no se marca al 100% por conectar una fuente y el criterio comercial no cambia.
