# NBA v2 — Fase 4, F4.4: ensayo operativo (2026-11-03)

Se ensayó en serio lo que se hará el día que algo falle: restaurar, volver atrás y detectar manipulación. Scripts reutilizables: `ops/ensayo_operativo.sh` y `.py`, `ops/ensayo_vuelta_atras.sh`. Nada se tocó en `nba_datos`.

## 1. Restaurar el respaldo más reciente (copia en una base aparte `nba_ensayo`, borrada al terminar)

- Respaldo: `nba_datos_20261103T081501Z.dump` (78 MB, el automático de las 09:15 UTC). **Restauración completa en 47 s**, sin errores.
- La copia es idéntica en lo que importa: 5.452.836 datos, 4.325.867 cuotas, 17.861 entidades, 8.521 capturas, 6.436 eventos y los 192 pronósticos sellados.
- **Los 6 disparadores de inmutabilidad vienen con la copia** (`captura`, `cuota`, `dato`, `entidad`, `evento`, `pronostico`) y un `UPDATE` a `nba.dato` se rechaza («evidencia inmutable de NBA»). La lectura punto en el tiempo funciona.
- La cadena de sellos restaurada se verifica entera: **192 de 192 en 0,01 s**.

## 2. Manipular la copia y comprobar que se detecta

Con los disparadores desactivados (solo en la copia desechable):
- Alterar el contenido de un sello → `verificar_cadena` lo detecta: «pronóstico 97 alterado: su hash no coincide con su contenido».
- Borrar un eslabón → lo detecta: «cadena rota en el pronóstico 97: hash_previo no coincide con la fila anterior».
(En producción nadie puede hacer ninguna de las dos cosas sin desactivar los disparadores, y la API valida el hash de cualquier sello que se le pide.)

## 3. Vuelta atrás de la imagen, con la ruta real del cron

Con `imagen_motor` apuntando a la imagen anterior (`nba-motor:6b85093`): el motor corre por `ejecutar_motor.sh` sin errores y **el cambio es efectivo en 1 s** (un archivo de una línea); el script restaura la imagen en uso (`d73c7c5`) aunque algo falle. Además, la imagen más antigua con props (`nba-motor:233e372`) también corre en simulacro contra la base de hoy sin errores (omite 0), así que cualquier punto de la historia sirve de destino. Se hizo sin partidos en ventana de sellado.

## 4. Canal de alertas

Credenciales verificadas sin enviar ningún mensaje: el bot existe (`getMe` ok) y el chat privado es alcanzable (`getChat` ok). El envío de un mensaje real sigue sin probarse a propósito (necesita tu visto bueno).

## 5. Copia fuera del servidor — HALLAZGO

La copia del PC (`Documents\respaldos_nba`) solo tenía el respaldo de 370 KB del 2-nov, es decir, **antes de cargar los datos y de sellar nada**; todo lo posterior habría dependido del VPS. Se trajo ahora el respaldo más reciente (78 MB) y el del 3-nov; el PC tiene ya los tres. El traer la copia es manual y no está programado.

## Riesgos que quedan (de más a menos grave)

1. **Pérdida de sellos entre respaldos.** El respaldo es diario (09:15 UTC) y el único que guarda los sellos irrepetibles es la base: un fallo del disco justo antes del respaldo perdería hasta 24 horas de sellos. Propuesta: respaldo cada 6 horas durante la temporada (≈ 80 MB, segundos de coste) y que cada respaldo conserve más de 7 copias en días de partido.
2. **La copia fuera del VPS depende de que alguien la traiga.** Propuesta: tarea programada diaria en el PC con `scripts/respaldo_nba_vps.ps1` (solo agrega, no borra).
3. **Un solo servidor y un solo disco** (62 GB de 97 usados al 64 %): sin réplica. Aceptable para esta fase; el informe final lo señala.
4. Las alertas aún no se han visto salir de verdad.
