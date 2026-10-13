# Entrenamiento con xG de API-Football — 12 de octubre de 2026

Orden del usuario: realizar el entrenamiento después de conectar el xG de
API-Football. Se ejecutó en el worker de producción y terminó correctamente.
El candidato no superó la puerta de activación frente a Elo; el modelo anterior
permanece activo.

## Resultado final verificado

- Fin: **12-oct-2026, 20:55:22 Ciudad de México** / 13-oct, 02:55:22 UTC.
- Duración: **4 h 44 min 18 s**. Estado `completed`; `activated=false`.
- Candidato registrado: `2026.10.12-221104`, con los 49.504 partidos y las
  148 parejas de la nueva fuente disponibles en el corte del ajuste final.
- Activo conservado: `2026.09.27-010508`.
- Comparación común: **1.051 partidos**. RPS y log-loss menores son mejores.

| Modelo | RPS | Log-loss |
|---|---:|---:|
| Candidato Dixon-Coles | 0,19873 | 0,98694 |
| Referencia Elo | 0,19657 | 0,98686 |
| Mercado sin margen | 0,19147 | 0,96547 |

El veto de activación es `beats_elo_same_rows=false`. El mercado es reciente
(`market_age_days=0`); el candidato tampoco lo supera. El champion histórico
tiene otra firma de observaciones, por lo que no se comparan directamente sus
métricas de una ventana distinta. La puerta comercial registra
`ready_for_commercial_picks=false`: el `clv_report` de este entrenamiento tiene
0 observaciones elegibles frente al mínimo de 300; no es el conteo de cierres
sharp de otros informes del sistema.

Hubo 12 ajustes históricos en las 13 ventanas mensuales previstas: se omite
la ventana sin partidos de prueba. Se guardaron 4.192 predicciones fuera de
muestra; 3.141 no tienen mercado para la comparación común. El ajuste 13 fue
el final, cuyo corte es 13-oct a las 02:32:16 UTC. La calibración superó su
control propio; eso no revoca el rechazo del candidato base. Las otras etapas
también terminaron y sus resultados están en `result.json`.

Verificación posterior: dataset y configuración recalculados desde el input
guardado; coincidencia con el hash del resultado y la fila de `model_artifacts`.
Las métricas almacenadas coinciden con el resultado. Diez artefactos existentes
con hashes registrados; Dixon-Coles carga con 49.504 partidos, 13 competiciones
y mezcla xG 0,65. Las 148 parejas son finitas y están disponibles en su corte.
La copia de fuentes coincide con la huella de lanzamiento. `/model-card`
interno y público responden 200. No se modificaron código ni puertas.

Evidencia final local en `.local/xg_api_20261012/training-2026.10.12-221104/`:
`completion-audit.json`, `artifact-verification.json`, `result.json`,
`status.json` y `training.log`; estos tres últimos se recuperaron byte a byte
y sus hashes coinciden con el VPS. El seguimiento se detiene tras este resultado.

## Estado al inicio

- Versión al lanzamiento: `2026.10.12-221104`.
- Inicio: 2026-10-12 22:11:04 UTC / 16:11:04 Ciudad de México.
- Dataset efectivamente leído: **49.504 partidos** y **148 parejas nuevas de xG**,
  disponibles a la fecha del ajuste final. Trece competiciones: once ligas y
  Champions/Europa League. No se incluyen ligas adicionales.
- Último partido del dataset: 12-oct, 19:15 UTC. Ventana histórica del cargador:
  doce años respecto a la hora real de carga. El preflight tenía 49.505 filas;
  Godoy Cruz–Tigre del 15-oct-2014 a las 22:10 UTC dejó de entrar al avanzar
  ese límite temporal antes del lanzamiento, comprobado contra la base.
- Modelo activo al inicio: `2026.09.27-010508`.
- Primer ajuste de validación confirmado: corte 2025-10-12 19:15 UTC,
  45.312 partidos; proceso vivo dentro del worker.
- Preflight: ningún entrenamiento activo, 79,71 GiB de disco libres y
  6.668 MiB de memoria disponible. Comprobación obligatoria: **972 pruebas
  aprobadas, 22 omitidas, 2 advertencias**.

## Validación y activación

Se ejecutó `train_and_register` con la configuración y las puertas vigentes:
365 días de validación walk-forward; comparación con Elo y mercado, ajuste
final, calibración, mezclador, residuo, logística, ablaciones y challengers
de alineación/jugadores. Un candidato se activa únicamente si la puerta normal
lo permite; un rechazo conserva el modelo anterior y registra el candidato.
No se omiten etapas ni se fuerza una promoción.

El xG recibido hoy no entra en ajustes cuyo corte era anterior a su recepción.
Por ello, este entrenamiento incorpora la nueva fuente al ajuste final, pero
su validación histórica no demuestra retrospectivamente una mejora por esos
148 datos. La contribución de la nueva fuente requiere seguimiento futuro.

Se limita cada biblioteca numérica a un hilo y el proceso tiene prioridad
reducida para convivir con los trabajos diarios. No se reinició ningún servicio.
Un bloqueo de archivo y revisión de procesos evitan duplicar este lanzamiento.

## Evidencia y seguimiento

Dentro del worker, los archivos persistentes están en:

`/srv/quantfut/artifacts/training-runs/xg-2026.10.12-221104/`

- `status.json`: estado, etapa, ajuste actual, cortes temporales, identificadores,
  proceso y señal de vida actualizada cada 30 segundos.
- `training.log`: etapas y progreso del walk-forward.
- `training_input.pkl`: copia de los datos efectivamente entregados al entrenador.
- `sources/`: copia de las fuentes del modelo vigentes al lanzamiento.
- `result.json`: guardado al terminar correctamente; contiene las métricas
  y la decisión de activación del pipeline.

Hash del dataset y configuración:
`84fb8a90acd52a17508c9582c5f29d8b48dbf46527bc356a768a30bd085d8ae2`.

Hash de fuentes:
`b2ad52ba4958aa16e566307613ca374df468193e839ce5005f393e781bfa0006`.

El lanzador operativo no modifica las fórmulas ni las puertas del entrenador.
Solo guarda evidencia y registra etapas alrededor de las mismas llamadas;
copia en `/home/qf/quantfut/deployments/xg-api-20261012/train_xg_runner.py` y
evidencia local ignorada en `.local/xg_api_20261012/`.

El usuario pidió aviso al terminar. Seguimiento creado y verificado en este
chat: automatización `resultado-del-entrenamiento-con-xg`, cada 15 minutos.
No reporta progreso repetitivo: avisa del resultado o fallo y se detiene. El
seguimiento requiere este equipo encendido y Codex abierto; el entrenamiento
del VPS continúa independientemente. Documentación oficial:
https://learn.chatgpt.com/docs/automations?surface=app.

Comprobados `result.json`, la fila correspondiente en `model_artifacts`,
el modelo activo, los artefactos y las respuestas del servicio.
Un estado antiguo que diga `running` con proceso inexistente requiere revisar
el log antes de lanzar de nuevo; no atribuirle éxito por haber arrancado.
