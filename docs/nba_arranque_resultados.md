# NBA: primer incremento ejecutado

Fecha del cliente: 2026-10-04. Plan maestro 1.1 **en implementación**;
ninguna puerta G0–G9 aprobada por este incremento.

## Entregables comprobados

- `apps/nba`: paquete, entorno, configuración y datos separados de fútbol.
- Descarga versionada de fuentes gratuitas, tamaño/hashes y primera recepción.
- Auditoría de box scores: IDs, duplicados, DNP, dos equipos, sumas de minutos,
  puntos/rebotes/asistencias y cuarentena de partidos inconsistentes.
- Replay temporal: ningún resultado del día objetivo entra en sus features.
- Baselines de minutos/rebotes, referencia Gamma-Poisson y escenarios
  hipotéticos con probabilidad de push separada; no son picks publicados.
- Ledger SQLite local inmutable por triggers y cadena verificable, con las
  limitaciones de un archivo controlado localmente y sin anclaje externo.
- 22 pruebas NBA correctas; 606 pruebas de fútbol correctas después del
  primer incremento. Docker no disponible: no se verificó despliegue/BD.

## Resultado retrospectivo de referencia

Protocolo `apps/nba/protocol.json`, `research-v0.1`, fijado antes de evaluar.
Regular 2024-25 y 2025-26, historial de misma temporada; mínimo 10 apariciones.
39.334 predicciones evaluadas en 2.048 partidos, separadas por temporada y
tres bloques cronológicos. Comparación sobre exactamente las mismas filas.

| Métrica | Referencia minutos+tasa | Media móvil de 10 apariciones |
|---|---:|---:|
| CRPS de rebotes (menor mejora) | 1,3510 | 1,3947 |
| NLL (menor mejora) | 2,2027 | 2,3562 |
| Error absoluto medio de rebotes | 1,9337 | 1,9674 |
| Error absoluto medio de minutos | 4,9723 | 5,0773 |
| Cobertura de intervalo central nominal 80% | 86,16% | 79,21% |

Diferencia CRPS candidato–baseline: intervalo bootstrap por partido
[-0,0478; -0,0404], 500 réplicas, semilla 20261004. Es diagnóstico
condicional al conjunto evaluado; el bootstrap no corrige dependencia
temporal entre partidos o jugadores. La cobertura superior al 80% puede
reflejar discreción e intervalos amplios; no prueba calibración por umbral.
Se excluyeron 10.779 apariciones por historial insuficiente y 11.145 filas
sin participación. La población todavía se define por participación observada.

Los mismos números siguen vigentes tras ampliar el informe de cobertura:
esa corrección conserva en el denominador los partidos raw con duración
inválida y no cambia las filas del dataset evaluado. SHA256 del dataset:
`e4dc38b0b4e355da6d095a8dd1f67b140679d5663629f70a196dfaeebeb300c9`.

## Interpretación y puertas pendientes

La mejora contra una referencia simple justifica continuar la investigación,
sin aprobar producción ni ventas. Los raw descargados hoy no reconstruyen
noticias/rosters conocidos históricamente; el replay no es evidencia de PIT
prospectivo. La cuarentena también puede modificar la población evaluada.
No se dispone de líneas/cuotas, por lo que no se estiman EV, CLV, ROI o
porcentaje de apuestas ganadoras. No se comparó con minutos implícitos de mercado.

La infraestructura de producción Postgres/Redis, recuperación, calendario y
rosters actuales, disponibilidad/minutos por rol, ritmo/rival, calibración
por umbral, reglas de operadores, outbox y Telegram siguen pendientes.
Telegram está inactivo; no se usan credenciales de fútbol. El servicio continuo
y una latencia de dos segundos no se han medido. F7 necesita observaciones
prospectivas reales; descargar históricos no reemplaza esa etapa.

Fuentes/cobertura y descargas se detallan en `docs/nba_fuentes_github.md`.
Resultados reproducibles: `apps/nba/.local/reports/backtest.json`, filas de
replay, manifiestos raw, informes de cobertura y `audit.sqlite`. Código y
parámetros tienen hashes en `apps/nba/.local/reports/code_manifest.json`.
El registro maestro incluye evidencia de ejecución y mantiene revisión
explícita de las puertas completas.
