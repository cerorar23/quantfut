# Tenis, Sprint 2b (parte C): captura del ranking oficial, candado, cursores y colector

Fecha: 5-nov-2026. Rama: `tenis/rediseno-f1`. Sin red, sin VPS, sin crédito de pago, sin commit.

## Qué se hizo

| Fichero | Contenido |
|---|---|
| `apps/tenis/src/tenis/captura/ranking.py` | Analizador puro de la respuesta, captura con transporte inyectable `obtener(ruta) -> (estado, bytes)`, resolver inyectable, recibo con `almacen.guardar_objeto`, observaciones `oficial_capturado` con `visible_desde` NULL, `sin_resolver` para jugadores no resueltos. |
| `apps/tenis/src/tenis/captura/presupuesto.py` | `reservar`, `confirmar`, `devolver`, `fijar_tope` sobre `tenis_op.presupuesto`. Tope NULL o fila ausente = sin permiso. Tope semanal (`TOPE_SEMANAL`, SportsAPIPro = 2) además del diario. Candado de transacción por fuente. |
| `apps/tenis/src/tenis/captura/cursor.py` | `leer` y `ejecutar_lote`: lote y avance del cursor en una sola transacción. |
| `apps/tenis/src/tenis/captura/candado.py` | Candado exclusivo no bloqueante (`fcntl` en Linux, `msvcrt` en Windows). `intentar` devuelve «ocupado». |
| `apps/tenis/src/tenis/captura/calendario.py` | `Protocol` del proveedor, contrato `EventoCalendario` (estricto, inmutable, instantes con zona) y `ProveedorFalso` en memoria. Sin implementación real. |
| `apps/tenis/ops/colector.sh` | `flock -n` sobre `$TENIS_LOCK_DIR/tenis-<fuente>.lock`; ocupado sale con 0; log `$TENIS_LOG_DIR/<fuente>.log` con inicio, fin y código. No registra argumentos ni entorno. |
| `apps/tenis/tests/test_captura_*.py` | 6 ficheros, ver abajo. |

No se ha tocado migraciones, `LEEME.md`, `harness/`, `apps/tennis/`, `src/tenis/carga/` ni `src/tenis/identidad/`.

## Formato del ranking: NO PROBADO CONTRA RESPUESTA REAL

- No hay muestra real de SportsAPIPro en el repositorio ni en las carpetas buscadas (worktree `apify-detalles-huecos`, `docs/`, `harness/`). Solo hay código que la consume.
- Forma conocida, tomada de `scripts/publicar_tenis_estadisticas.py` y `src/qf/ingest/tenis_estadisticas_respaldo.py` del worktree `apify-detalles-huecos`: `{"data": {"rankings": [{ranking, points, previousRanking, team: {id, name, country}, rowName, country}]}}`. Rutas: ATP `rankings/type/5` y WTA `rankings/wta` (base `https://api.sportsapipro.com/api/`).
- Autenticación: cabecera `x-api-key`. No se leyó ningún valor de clave.
- El `team.id` es el id de SofaScore (mismo id que el resto de SportsAPIPro).
- **No está verificado:** que `points` llegue como entero (el motor viejo lo convierte con `str()`), y si existe un campo de fecha de la clasificación. El analizador busca `rankingDate` o `date` en `data`. Si existe y es lunes, se usa; si existe y no es lunes, la respuesta se rechaza (`fecha_no_lunes`). Si no existe, regla conservadora `lunes_captura`: lunes anterior o igual a la fecha de captura.
- El fixture `SINTETICO` de `test_captura_ranking.py` está inventado y etiquetado como tal.

## Pruebas

Comando: `correr_pytest_tenis.ps1 apps/tenis/tests` (suite completa, sin `-k`).

- Resultado: **887 aprobadas, 9 omitidas, 0 fallidas** (código de salida 0).
- Omitidas: 3 de `test_db_roles.py` (ya omitidas antes: el usuario local no puede crear roles) y 6 de `test_captura_colector.py` (requieren `flock`; en Windows no existe, **no probado en Windows**; CI Linux lo ejercita).
- Cubiertas por `test_captura_*.py` (todas en verde):
  - Absurdas: posición 0, negativa, `True` o texto; posición duplicada; jugador duplicado; puntos negativos o texto; id o nombre ausentes; fecha de martes; fecha mal formada; JSON roto, `[]`, `{"data": null}`, lista vacía.
  - HTTP 500, 503 o cuerpo vacío: no escribe nada y devuelve la cuota (`usadas` vuelve a 0).
  - Tope agotado: el transporte no se llama.
  - Jugador sin resolver: va a `sin_resolver`, no se crea ningún `jugador`.
  - Mismo contenido dos veces: un objeto en disco, dos recibos y el doble de observaciones.
  - Recuento independiente: segundo cálculo sobre el mismo texto; coinciden 4 filas, suma de puntos 22650 (faltantes excluidos).
  - Presupuesto: sin fila, tope NULL, tope 0, tope diario, tope semanal (dos peticiones en la semana, la tercera falla, la semana siguiente vuelve a abrir), `devolver` sin bajar de cero, `confirmar` sin reserva, y dos reservas simultáneas con hilos (no pasan del tope).
  - Cursor: avance con el lote; fallo a mitad de lote deja cursor y evidencia iguales; repetir el lote no duplica filas; lote que no avanza devuelve el valor previo.
  - Candado: dos instancias en el mismo proceso; proceso hijo tenedor y segundo proceso que sale como «ocupado» sin trabajar; el candado se libera al morir el tenedor.
  - Calendario: contrato estricto (extra, sin zona, mismo jugador, circuito, estado, ronda y ids inválidos, texto en lugar de entero) e inmutabilidad; proveedor falso filtra por intervalo.
  - PIT: una observación con `recibido_en` posterior al corte no aparece en `ranking_a_las(corte, NULL)`; con `p_fecha_partido` anterior al lunes de publicación tampoco aparece; con el lunes correcto sí.

## Supuestos y decisiones

1. **Una fila mal formada rechaza la respuesta entera**, no solo esa fila. Una clasificación con huecos no se escribe.
2. **Respuesta recibida con cuerpo válido gasta cuota aunque se rechace.** Solo se devuelve la cuota si el estado no es 200 o el cuerpo está vacío.
3. **`usadas` cuenta lo reservado (incluido lo que está en vuelo).** `confirmar` no cambia el contador; solo verifica que hubo reserva.
4. **Tope semanal en código** (`TOPE_SEMANAL`), no en tabla: las migraciones no se editan en este sprint.
5. **Respuestas rechazadas se guardan como recibo y objeto** (para auditoría), sin observaciones y sin mover el cursor.
6. **El cursor guarda la `fecha_publicacion` del último lote aceptado** (`ranking_<circuito>`).
7. **SQL sin esquema explícito**, como el cargador TML. El llamador debe fijar `search_path` con `tenis` y `tenis_op`. Las pruebas lo hacen así.
8. **Sin transporte real.** `ranking.py` solo define el protocolo; ninguna llamada de red existe en el paquete.

## Lo que no se ha cumplido

- Verificar el formato real: falta una respuesta de SportsAPIPro. Hace falta una captura aprobada por el titular antes de dar el analizador por bueno (una petición de las 2 semanales).
- Implementación real del transporte y del resolver contra la base de identidad (`identidad/` está en manos de otro agente).
- Implementación de `calendario` (decisión D3): solo interfaz.
- `colector.sh` sin probar en Windows. Sin probar en VPS (`/var/lock` y `/var/log/tenis` deben existir y tener permisos).
- No hay `confirmar` real contra el libro de gasto del proveedor: el control es local.
- Sin commit.
