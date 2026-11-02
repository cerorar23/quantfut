# Rediseño NBA — Sprint 1: captura, adaptadores y backfill

> **Para quien ejecute:** `superpowers:executing-plans`. Implementa la sección 3 del [plan técnico](nba_rediseno_plan_tecnico_20261102.md). S0 (base `nba_datos`) ya está desplegada y vacía.

**Objetivo:** que todo lo que se captura llegue a `nba.*` con recepción real, sin duplicar, con el original guardado, la identidad resuelta sin falsas fusiones y los conflictos marcados; y cargar el histórico ya normalizado.

**Reparto (decidido al detallar S1):** el sprint es grande; se divide para poder verificar y desplegar por partes.

| Parte | Entrega | Necesita créditos / producción |
|---|---|---|
| **S1a** (este plan, tareas 1-5) | Núcleo de carga, equipos canónicos, adaptadores Rotowire y ESPN (`run57`) con fixtures reales, todo probado contra Postgres desechable | No |
| **S1b** | Parte oficial NBA (PDF), `cdn.nba.com`/`stats.nba.com` (final), cuotas (archivo PropLine / The Odds API), backfill desde `.local/normalized` | Scrapfly/ZenRows |
| **S1c** | Contenedor `nba-captura` + cron en el VPS, usuarios de login, respaldo diario fuera del VPS | Despliegue (confirmación del titular) |

## Restricciones globales
Las del plan técnico. Además: ningún adaptador hace peticiones por sí mismo; reciben una función `obtener(url) -> bytes` (inyectable en pruebas). Las claves no se escriben en archivos ni en logs.

## Task 1: Núcleo de carga (`nba.v2.carga`)
**Files:** Create `apps/nba/src/nba/v2/carga.py`; Test `apps/nba/tests/v2/test_carga.py`.
**Interfaces — Produces:**
- `@dataclass(frozen=True) DatoNuevo(partido_id: int, entidad_id: int, metrica: str, fase: str, fuente: str, recibido_en: datetime, periodo: int = 0, valor: float | None = None, etiqueta: str | None = None, captura_id: int | None = None, pit: str = "posterior")`
- `guardar_datos(db, filas: Iterable[DatoNuevo]) -> int`: inserta las que no existen (idempotente por la clave única); marca `conflicto = true` en la fila nueva si otra fuente ya tiene un valor numérico distinto (más allá de `TOLERANCIA[metrica]`, 0 por omisión) para una métrica de resolución `prioridad`; devuelve cuántas insertó.
- `guardar_original(raiz: Path, fuente: str, cuerpo: bytes, recibido_en: datetime) -> tuple[str, str]`: escribe `<raiz>/<fuente>/<aaaa-mm-dd>/<sha256>` si no existe y devuelve `(ruta_relativa, sha256)`.
- `registrar_captura(db, *, fuente: str, objetivo: str, fase: str, solicitado_en: datetime, ok: bool, recibido_en: datetime | None = None, http_status: int | None = None, sha256: str | None = None, bytes_: int | None = None, ruta: str | None = None, error: str | None = None, creditos: float = 0, partido_id: int | None = None) -> int`
- `guardar_cuotas(db, filas: Iterable[CuotaNueva]) -> int` (idempotente por la clave única de `nba.cuota`).
- [ ] Pruebas: `test_guardar_datos_es_idempotente`, `test_conflicto_se_marca_en_la_fila_nueva_solo_si_difiere`, `test_tolerancia_de_minutos`, `test_metrica_desconocida_falla_sin_insertar_nada`, `test_guardar_original_es_idempotente_y_hash_coincide`, `test_registrar_captura_devuelve_id_y_guarda_error`, `test_guardar_cuotas_es_idempotente`.

## Task 2: Equipos canónicos e identidades (`nba.v2.equipos`, `nba.v2.identidad`)
**Files:** Create `equipos.py`, `identidad.py`; Test `test_identidad.py`.
**Interfaces — Produces:**
- `equipos.TRICODES: dict[str, str]` (30 códigos oficiales → nombre) y `equipos.canonico(fuente: str, abreviatura: str) -> str` (ESPN `GS→GSW`, `NO→NOP`, `NY→NYK`, `SA→SAS`, `UTAH→UTA`, `WSH→WAS`; lanza `KeyError` si no existe).
- `identidad.equipo(db, tricode: str) -> int`; `identidad.jugador(db, fuente: str, id_en_fuente: str, nombre: str) -> int`; `identidad.arbitro(db, fuente, id_en_fuente, nombre) -> int`; `identidad.partido(db, fuente, id_en_fuente, fecha_et: date, local: int, visitante: int, temporada: str) -> int`.
- Reglas: ya existe `(fuente, id_en_fuente, tipo)` ⇒ devuelve su `canonica_id`; si no, y existe **un único** jugador canónico con el mismo nombre normalizado (sin acentos, mayúsculas ni sufijos Jr./Sr./II/III/IV) ⇒ crea un alias; si hay 0 ⇒ crea fila canónica; si hay más de uno ⇒ crea fila canónica nueva con `atributos = {"ambiguo": true}` (nunca fusiona por duda). Un partido de otra fuente con la misma fecha ET y los mismos equipos local/visitante es alias del existente.
- [ ] Pruebas: `test_canonico_de_alias_espn`, `test_equipo_es_idempotente`, `test_jugador_alias_por_nombre_normalizado`, `test_nombre_ambiguo_no_se_fusiona`, `test_dos_jugadores_mismo_nombre_distinto_id_misma_fuente_no_se_fusionan`, `test_partido_de_otra_fuente_es_alias`, `test_partido_de_otra_fecha_no_es_alias`.

## Task 3: Adaptador Rotowire (`nba.v2.fuentes.rotowire`)
**Files:** Create `fuentes/__init__.py`, `fuentes/rotowire.py`; Test `test_rotowire.py`; fixtures `fixtures/rotowire_lineups.html` (2 partidos recortados), `fixtures/rotowire_minutos_OKC.json`.
**Interfaces — Produces:**
- `parsear_lineups(html: str) -> list[PartidoRW]` con `PartidoRW(visitante: str, local: str, hora_et: str, arbitros: list[tuple[str, str]], equipos: dict[str, EquipoRW])` y `EquipoRW(titulares: list[JugadorRW], ausentes: list[JugadorRW])`; `JugadorRW(id_rw: str, nombre: str, posicion: str, prob_jugar: float, estado: str | None)`.
- `parsear_minutos(texto_json: str) -> list[MinutosRW]` (`id_rw, proy, promedio, minimo, maximo, desviacion, lineup`).
- `a_filas(db, partido: PartidoRW, minutos: dict[str, list[MinutosRW]], fecha_et: date, recibido_en: datetime, captura_id: int) -> list[DatoNuevo]`: `estado_disponibilidad` (etiqueta = estado de la fuente, `valor` = probabilidad de jugar 0-1), `titular_esperado`, `minutos_proyectados` y sus cuatro variantes, `arbitro_asignado`; todas con `fase='pre'`, `fuente='rotowire'`.
- `capturar(db, obtener, raiz, ahora) -> dict`: pide la página, guarda el original, registra la captura, pide los minutos de los equipos que juegan, carga y devuelve un resumen; si algo falla registra `ok=false` y **no escribe ningún dato imputado**.
- [ ] Pruebas con los fixtures: nº de partidos y de titulares (5 por equipo), probabilidades `is-pct-play-*` → 0/0,25/0,5/0,75/1, árbitros con su id, minutos, idempotencia al cargar dos veces, `test_pagina_sin_partidos_no_escribe_datos`, `test_error_http_registra_captura_fallida`.

## Task 4: Adaptador ESPN sobre el ledger de `run57` (`nba.v2.fuentes.espn`)
**Files:** Create `fuentes/espn.py`; Test `test_espn.py`; fixtures `espn_scoreboard.json`, `espn_lesiones.json` (recortados), un ledger SQLite mínimo creado en la prueba.
**Interfaces — Produces:**
- `parsear_scoreboard(texto: str) -> list[PartidoESPN]`; `parsear_lesiones(texto: str) -> list[LesionESPN]` (id del jugador tomado de `athlete.links[].href` cuando falta `athlete.id`).
- `cargar_ledger(db, ruta_sqlite: Path, raiz_blobs: Path, desde_seq: int) -> int`: lee en modo solo lectura los recibos nuevos del ledger de `run57`, y por cada respuesta 200 de calendario o lesiones crea la captura (con el `sha256` ya conocido) y las filas; devuelve el último `seq` procesado. Estados de lesión → `estado_disponibilidad` con etiqueta original (`Out`, `Day-To-Day`, `Suspension`), `valor` vacío.
- Marcador de calendario → `inicio_programado_utc`, `estado_partido`, `equipo_local`/`equipo_visitante`, `asistencia` (cuando > 0).
- [ ] Pruebas: partidos y equipos del fixture, hora UTC correcta, un recibo con `http_status` ≠ 200 se salta, jugador sin `athlete.id` se resuelve por enlace, reanudar desde `desde_seq` no duplica, cargar dos veces no duplica.

## Task 5: Registro
- [ ] Anotar S1a en `harness/tareas.md` y `harness/progreso.md`; actualizar memoria; informar al titular qué falta (S1b/S1c) y qué requiere su confirmación.

## Review Focus de S1a
1. Dos jugadores distintos con el mismo nombre (p. ej. mismo nombre en dos equipos): nunca se fusionan.
2. Página de Rotowire sin partidos (día sin juegos) o con plantilla parcial: cero filas y captura `ok = true` con `n_partidos = 0`, no un error.
3. Jugador ausente en la lista de minutos: no se inventa 0; solo existen las filas que la fuente trae.
4. Partido de ESPN con hora `date` en UTC que cruza medianoche: `fecha_juego_et` se calcula en ET.
5. Reproceso del mismo recibo del ledger: no duplica datos ni capturas.
