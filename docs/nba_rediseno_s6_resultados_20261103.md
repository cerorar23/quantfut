# NBA v2 — Sprint 6: API de lectura y web NBA (2026-11-03)

Código: `apps/nba/src/nba/api/` (API FastAPI + web estática), `apps/nba/ops/nba-api/Dockerfile`. **No está desplegado ni expuesto**: el piloto v1 (`/nba`, `nba-dashboard-run69`) sigue intacto y nada de v2 es público hasta que lo apruebes.

## API de lectura (`/nba/v1`, solo lectura)

| Ruta | Qué devuelve |
|---|---|
| `GET /cartelera?fecha=` | partidos del día con hora, resultado final si existe, pronóstico sellado más reciente (probabilidad de ganar, marcador proyectado, rango 10–90 % de margen y total) y estado del sello («sellado hh:mm · #hash» o «se sella a las…», 60 min antes del salto) |
| `GET /partido/{id}` | lo anterior más las cuatro distribuciones (margen, total, puntos de cada equipo) como 199 cuantiles de 0,5 % a 99,5 % |
| `GET /partido/{id}/linea?mercado=&valor=` | P(más de) y P(menos de) para cualquier línea; fuera del rango estimado se acota a 0,5 %–99,5 % y se marca `extremo` |
| `GET /partido/{id}/jugador/{id}` | pronósticos de jugador sellados (hoy 404 `sin_pronostico_jugador`: aún no se sellan) |
| `GET /sello/{hash}` | recalcula el hash del contenido, comprueba el enlace con el sello anterior y la regla corte ≤ sello; con `?cadena=true` verifica toda la cadena |
| `GET /calibracion` | prueba histórica 2025-26 (de los Sprints 3 y 4) y registro prospectivo desde que se sella (Brier del ganador y tabla de fiabilidad por tramos) |

Cada conexión se abre en modo solo lectura (`default_transaction_read_only`); los errores devuelven un código (`{"codigo": "sin_pronostico"}`) y el servidor no manda texto visible: la web lo traduce.

## Web (`/nba/v2/`, 6 idiomas)

Cartelera por fecha, página de partido (Equipo con histograma, selector de mercado y control deslizante de línea que pide la probabilidad al servidor; Jugador y Especiales como aviso «próximamente»; pie con el sello verificable y botón «Verificar sello») y página «Cómo acertamos». Estética CyberCore (cian/verde/magenta sobre grafito), tema claro automático, sin desbordamiento horizontal a 375 px. Idiomas es, en, pt, fr, it, de en `i18n.json`; una prueba comprueba que los seis tienen las mismas claves, que cada clave usada en el código existe y que cada código de error del servidor tiene texto en los seis. Sin claves ni tokens en el navegador; todo texto de datos se inserta con `textContent`.

Verificado en el navegador con datos de demostración (liga de 6 equipos en una base desechable, 10 pronósticos sellados): cartelera, partido, cambio de mercado y línea, verificación del sello (íntegro, lugar 3 en la cadena), cambio de idioma a alemán y página de calibración, sin errores de consola.

## Pruebas

8 pruebas de la API (cartelera con y sin sello, coherencia de `linea` — monótona, suma 1, extremos acotados —, 404 con código, verificación pública del sello y de la cadena, calibración prospectiva, web estática, traducciones) y la suite completa de v2: 200 pruebas pasan.

## Cambios al motor para servir la API

La distribución sellada pasa de 9 cuantiles a 199 (paso de 0,5 %, arreglos en vez de diccionarios) para poder calcular la probabilidad de cualquier línea sin repetir la simulación. Nada se había sellado en producción, así que no hay cadena que rehacer.

## Lo que falta para que esto sea visible (decisiones tuyas y trabajo pendiente)

1. **El motor por partido (`nba-motor`) aún no existe como proceso:** hace falta un ejecutable que cada pocos minutos busque partidos que empiezan en la próxima hora sin sello, arme la instantánea, pronostique y selle. Hoy el sellado solo se ha probado en bases desechables. Es lo primero para llenar la web.
2. **Boceto:** sigo sin tu opinión del boceto de la Fase 1; esta web lo sigue (cartelera, partido, calibración) y se ajusta cuando la veas.
3. **Exposición:** hay que decidir la ruta pública (p. ej. `pronosticosdeportivos.pro/nba/v2` o sustituir `/nba` al aprobar v2) y cómo entra en la web única con cuentas y bloqueo de contenido de pago.
4. **Rol de solo lectura en la base** (`nba_lector` con login) para la API en producción; la API ya abre cada conexión en solo lectura, pero el usuario de la base también debe serlo.
5. **Jugadores y especiales:** la pestaña muestra «próximamente»; se llena cuando el motor selle props (S3b/S4 aún no leen de la instantánea).
