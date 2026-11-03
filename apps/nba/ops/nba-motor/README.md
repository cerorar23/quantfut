# nba-motor: sellado de pronósticos por partido

Imagen `nba-motor:<commit>` (`ops/nba-motor/Dockerfile`: `nba-captura` más numpy y scipy). `python -m nba.v2.motor` se ejecuta una vez y termina.

**Qué hace:** para cada partido con salto programado en la próxima hora y sin sello, toma el corte `salto − 60 min`, arma la instantánea (`pit`),
pronostica (`motor_equipo`) y sella (`sellado`) con el usuario de base `nba_motor` (hereda `nba_lector` y `nba_escritor`: lee todo, solo inserta).
**Garantías:** el corte es fijo (un cron atrasado usa los mismos datos); nunca sella después del salto; si la historia está atrasada más de 7 días
omite en vez de sellar; un partido que falla no bloquea a los demás; sin hora de salto conocida lo lista en `sin_hora`; ignora juegos canónicos duplicados.
**Salida:** una línea JSON (`sellados`, `omitidos`, `sin_hora`, `errores`); código 1 si hubo errores, 2 si falta `NBA_DB_DSN`.

En el servidor (`~/nba-isolated/nba-captura/`): `motor.env` (modo 600, `NBA_DB_DSN` de `nba_motor`), `imagen_motor` (etiqueta), `ejecutar_motor.sh`.
Activar = añadir la línea de cron de `ejecutar.sh`; desactivar = quitarla (lo sellado es solo-anexar y se queda). `--simulacro` calcula sin escribir.
