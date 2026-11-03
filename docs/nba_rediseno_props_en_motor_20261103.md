# NBA v2 — Props de jugador en el motor, alertas y G-fuga con jugadores (2026-11-03)

## Qué se conectó

- **Plantilla en un punto en el tiempo** (`plantilla_pit.py`): para un partido y un corte, quién puede jugar, su último parte oficial visible en el corte y sus últimos 30 partidos jugados. Candidatos de un equipo: quienes jugaron en sus 10 últimos partidos con ese equipo y cuyo último partido fue con él, más los nombrados en el parte; mínimo 5 partidos. Misma regla de visibilidad que `pit.instantanea` (partidos de fecha anterior; `reconstruido` por fecha, `posterior` con `recibido_en ≤ corte`).
- **Artefacto entrenado en local** (`parametros/props.json`, generado por `ops/entrenar_props.py`): prior de tasa por nivel de rol, residuos de minutos, sobredispersión por estadística y probabilidades de jugar (por estado del parte y, sin parte, por tramo de minutos). El servidor no entrena (D4). Su huella forma parte de `version_modelo` (`props-2.0;<huella>;k=30;dec=0.97`); la huella ignora los finales de línea del sistema.
- **`motor_jugadores`**: puntos, rebotes, asistencias y triples de cada jugador de rotación (probabilidad de jugar ≥ 15 % y ≥ 8 minutos esperados) como distribución completa (pmf) condicionada a jugar, más `p_juega`, minutos si juega (p10/p50/p90) y estado del parte.
- **`nba-motor`**: además del partido, sella los pronósticos de jugador de ese partido con el mismo corte (`salto − 60 min`), todo o nada por partido; si fallan, el sello del equipo se conserva y el siguiente cron completa los props. Imagen `nba-motor:06d13f2`, activa en el cron desde las 02:30 UTC del 3-nov: 192 sellos (4 de equipo, 188 de jugador, 4 partidos) con la cadena verificada.
- **Alertas** (`alertas.py`): errores, partidos que empezaron sin sello y captura atrasada, por el canal privado de alertas existente; una vez por tipo, partido y día (estado en `datos/estado_alertas.json`, ya sembrado con lo ocurrido antes de la activación para no inundar). El envío se probó con un transporte simulado; no se mandó ningún mensaje de prueba real.
- **API y web**: `GET /partido/{id}/jugadores`, `/partido/{id}/jugador/{id}/linea`; pestaña Jugador (selector de jugador y mercado, línea con probabilidad «si juega», parte oficial, minutos esperados) con 14 textos nuevos en los 6 idiomas. La API no está desplegada.

## G-fuga con jugadores (VPS, solo lectura, 60 partidos de 2025-26)

0 diferencias de repetibilidad; 0 diferencias entre la plantilla y una reconstrucción independiente (consulta distinta, sin punto en el tiempo); 5.676 pronósticos; cobertura del rango 80 % de los puntos reales 81,5 % (n = 1.161). Las dos primeras corridas fallaron: una por la comprobación (contaba a los equipos como jugadores) y otra por una diferencia real: la plantilla solo miraba 500 días atrás mientras el modelo validado usa los últimos 30 partidos sin límite de edad; corregido (2.200 días = todo el archivo).

## Lo que NO está conectado

- **Los jugadores no entran en el pronóstico del equipo**: el núcleo sellado sigue siendo el de ratings de equipo (v2.0). La mezcla con el modelo de jugadores del Sprint 3b (error del margen 14,49 → 14,32) necesita las alineaciones y los minutos esperados de toda la plantilla dentro del cálculo y un artefacto de impacto reajustado cada 21 días; queda como mejora del equipo, con su propia versión.
- **Especiales** (primer anotador, dobles) y combos (R+A, PRA): sin cierres de mercado suficientes para evaluarlos.
- **Un hueco de datos conocido**: las cajas por jugador de 2026-27 (desde el 21-oct hasta el 2-nov) no existen (las cajas de cdn.nba.com llegan solo hacia adelante). Los jugadores se pronostican con sus últimos 30 partidos, que para muchos terminan en abril de 2026; mejora sola a medida que cdn.nba.com aporta cajas.
