# nba-motor: sellado de pronósticos por partido

Imagen `nba-motor:<commit>` (`ops/nba-motor/Dockerfile`: `nba-captura` más numpy y scipy). `python -m nba.v2.motor` se ejecuta una vez y termina.

**Qué hace:** para cada partido con salto programado en la próxima hora y sin sello, toma el corte `salto − 60 min`, arma la instantánea (`pit`),
pronostica (`motor_equipo`) y sella (`sellado`) con el usuario de base `nba_motor` (hereda `nba_lector` y `nba_escritor`: lee todo, solo inserta).
**Garantías:** el corte es fijo (un cron atrasado usa los mismos datos); nunca sella después del salto; si la historia está atrasada más de 7 días
omite en vez de sellar; un partido que falla no bloquea a los demás; sin hora de salto conocida lo lista en `sin_hora`; ignora juegos canónicos duplicados.
**Salida:** una línea JSON (`sellados`, `omitidos`, `sin_hora`, `errores`); código 1 si hubo errores, 2 si falta `NBA_DB_DSN`.

En el servidor (`~/nba-isolated/nba-captura/`): `motor.env` (modo 600, `NBA_DB_DSN` de `nba_motor`), `imagen_motor` (etiqueta), `ejecutar_motor.sh`.
Activar = añadir la línea de cron de `ejecutar.sh`; desactivar = quitarla (lo sellado es solo-anexar y se queda). `--simulacro` calcula sin escribir.

## Candidato 2.2: estado congelado y posesiones

La ruta activa carga `parametros/equipo.json` (o `NBA_ESTADO_EQUIPO_JSON`), proyecta posesiones y simula regulación más OT. No ajusta ratings en el VPS. El artefacto lleva recepción, fecha máxima de datos, receta y huellas; se rechaza si es futuro respecto al corte, incluye el día objetivo o supera 72 horas de antigüedad. Cada artefacto cambia la versión del modelo.

La renovación se ejecuta en local con `ops/exportar_equipo.py` y `ops/entrenar_equipo.py`, conservando salidas anteriores. Debe publicarse una versión nueva antes de vencer; no instalar estos entrenamientos en el cron del servidor. La API deriva la versión del artefacto compartido; `NBA_VERSION_MODELO_ACTIVA` permite un override explícito.

La mezcla con jugadores queda bloqueada sin evidencia para el objetivo de regulación. El estudio local de la candidata sin RAPM empeoró el Brier y no se promueve; tampoco se reutiliza sin validación el impacto antiguo sobre finales. El núcleo de equipo sigue disponible y registra el bloqueo en sus escenarios. Los props mantienen su ruta con corte temporal.

Antes de publicar: pruebas, migración `0009_recepcion_original.sql`, comparación del runtime, respaldo y registro/rollback según `DEPLOYS.md`. Evidencia y límites: `docs/nba_auditoria_correcciones.md` en la raíz del repositorio. Este README no acredita que el candidato se haya desplegado.
