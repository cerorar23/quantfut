# Rediseño NBA — Plan técnico (Fase 2)

> **Estado:** decisiones D1-D6 aprobadas por el titular el 2-nov-2026 (ver sección 1); el resto del plan está pendiente de su visto bueno final. Fase 1 cerrada. **No se escribe código ni se despliega nada hasta que el titular autorice la Fase 3 (sprints).**
>
> **Para quien ejecute (Fase 3):** usar `superpowers:subagent-driven-development` o `superpowers:executing-plans`; cada sprint de la sección 9 se convierte antes en su propio plan de tareas con pruebas.

**Objetivo:** reemplazar el flujo disperso de archivos y los motores v1.x por (a) una base única `nba.*` con recepción real en cada hecho, (b) un motor que produce una distribución conjunta calibrada por partido y por jugador, y (c) una web de pronósticos NBA que las muestra con sellado verificable.

**Arquitectura en una línea:** captura (originales en archivo + hash) → adaptadores idempotentes → `nba.dato`/`nba.cuota`/`nba.evento` solo-anexar → acceso punto-en-el-tiempo → motor v2 (disponibilidad → minutos → núcleo del marcador → props) → `nba.pronostico` sellado con cadena de hashes → API de lectura → web.

**Tecnología:** Python 3.12, paquete `nba` en `apps/nba` (aislado de `qf`), Postgres 16, numpy/scipy/statsmodels (ya en el entorno NBA), pytest. Entrenar en local; el VPS solo calcula con artefactos versionados.

**Spec que implementa:** [SINTESIS_FINAL.md](../ESTUDIOS/Pdf%20Estudio%20Nba/_analisis/SINTESIS_FINAL.md) (77 fichas), decisiones de datos y mercados de la Fase 1 (memoria `rediseno-nba-fase1-20261102`) y [nba_arquitectura_aislada.md](nba_arquitectura_aislada.md).

## Restricciones globales (valen para todo sprint)

- NBA no importa `qf`, no lee el `.env` de fútbol ni su base; solo configuración `NBA_*`. Base propia con nombre `nba_*` (el código `postgres_delivery.connect` ya lo exige).
- Todo hecho guardado lleva `recibido_en` real (UTC, `timestamptz`). Si el original no tiene recepción acreditada, `pit = 'reconstruido'` o `'no_acreditado'`; nunca se inventa.
- Solo-anexar: triggers que rechazan `UPDATE`/`DELETE`/`TRUNCATE` en `nba.dato`, `nba.cuota`, `nba.evento`, `nba.captura` y `nba.pronostico`. No se deshabilitan "para corregir rápido".
- Lo derivado (forma, rachas, descanso, margen de cuotas, líneas) no se guarda; se calcula en vistas/funciones.
- Fechas de juego en hora del Este (ET) como `fecha_juego_et`; instantes en UTC. Un partido que cruza medianoche UTC sigue siendo de su fecha ET.
- Orden de publicación intacto: predecir → sellar → publicar. Un pronóstico solo usa filas con `recibido_en <= objetivo_en`.
- Nada se promueve ni se publica por capturar datos o entrenar; promover = decisión del titular con el informe de la Fase 4.
- Textos visibles de web/app en los 6 idiomas (es, en, pt, fr, it, de) en el mismo cambio; sin tokens de servicio en JavaScript.
- Archivos nuevos con finales de línea LF; no normalizar archivos ajenos (hashes NBA).
- Despliegue: leer `DEPLOYS.md`, una sesión a la vez, comparar con `main`, anotar la vuelta atrás.

## 1. Decisiones D1-D6 (aprobadas el 2-nov-2026)

| # | Decisión | Recomendación | Alternativa |
|---|---|---|---|
| D1 | Dónde vive la base | **Aprobada.** Contenedor Postgres propio `nba-db` en el VPS, base `nba_datos`, roles separados (migración / escritura / lectura) | Base `nba_datos` en `quantfut-db-1` con rol propio: ahorra memoria, pero comparte proceso y disco con fútbol (el diseño del 3-oct lo desaconseja) |
| D2 | Cómo conviven v1.x y v2 | **Aprobada.** Subpaquete nuevo `nba.v2` y tablas `nba.*`; el piloto vivo (`nba-dashboard-run69`, v1.x) no se toca hasta que v2 pase la Fase 4. **Condición del titular: cuando v2 esté aprobada, v1 deja de existir en el VPS** (se retiran contenedores, imágenes y rutas de v1; se conservan sus originales y reportes como archivo, se anota en `DEPLOYS.md` con vuelta atrás) | Modificar v1.5 en sitio: mezcla pruebas viejas y nuevas y rompe la reproducibilidad del piloto |
| D3 | Núcleo del marcador | **Aprobada.** v2.0 paramétrico por periodos: normal bivariada de puntos (colas t) con correlación estimada, deriva = fuerza esperada; v2.1 simulación por posesiones solo si la Fase 4 muestra mejora | Simulación por posesiones desde el inicio (más caro, sin evidencia previa de ganancia: fichas 75, 77) |
| D4 | Entrenamiento | **Aprobada.** Siempre local; artefacto (parámetros + `sha256` + versión de datos) subido al VPS; el VPS solo infiere | Entrenar en el VPS: prohibido por decisión previa |
| D5 | Web | **Aprobada.** API de lectura propia en `apps/nba` (`nba.api`, contenedor propio); el FastAPI único (cuentas, planes, bloqueo) la consume por red interna y sirve `/nba` | Leer la base NBA desde `qf`: viola el aislamiento |
| D6 | Créditos de captura final | **Aprobada con respaldo.** Scrapfly para `cdn.nba.com` solo hacia adelante: ≈ 2 créditos/partido (resumen + jugada a jugada) ⇒ ≈ 900/mes en temporada; si se agotan, el titular autoriza **ZenRows, pero ZenRows NO pasa `cdn.nba.com` (422 medido el 2-nov)**: el respaldo es `stats.nba.com` por ZenRows básico (1 crédito, medido) con los endpoints de box score y jugada a jugada, y el adaptador `nba_oficial` debe aceptar ambos formatos. Saldos al 2-nov: Scrapfly Free 1.000 (30-oct a 30-nov), 328 usados; ZenRows Free 5.000/mes, 3.961 usados, renueva el 6-nov, compartido con el scraper del VPS. En la prueba, 14 de 30 peticiones a cdn fallaron y se cobraron: reintentos con tope. **Verificar saldos antes del Sprint 1** | Capturar solo el resumen (1 crédito/partido) y pedir jugada a jugada a SofaScore/ESPN |

## 2. Esquema de datos (`apps/nba/db/`, migraciones propias)

Identificadores en español, como `futbol.dato`. Todas las tablas del esquema `nba`. `periodo`: 0 = partido, 1–4 cuartos, 5+ prórrogas, 101/102 = 1.ª/2.ª mitad.

```sql
-- nba.fuente: prioridad GLOBAL (oficial > SofaScore > resto)
fuente(fuente TEXT PK, prioridad SMALLINT UNIQUE NOT NULL, descripcion TEXT NOT NULL)
-- filas iniciales: nba_oficial 1, sofascore 2, espn 3, basketball_reference 4, rotowire 5,
--                  propline 6, the_odds_api 7, sharpapi 8, betsapi 9

-- nba.metrica: catálogo (nombre canónico, definición, nombre nativo por fuente)
metrica(metrica_id SMALLINT PK, nombre TEXT UNIQUE NOT NULL, nivel TEXT CHECK (nivel IN ('partido','equipo','jugador','arbitro')),
        unidad TEXT, definicion TEXT NOT NULL, nombres_nativos JSONB NOT NULL DEFAULT '{}', es_proyeccion BOOLEAN NOT NULL DEFAULT false)

-- nba.entidad: identidad. Una fila canónica (canonica_id = entidad_id) y una por alias de fuente.
entidad(entidad_id BIGINT IDENTITY PK, tipo TEXT CHECK (tipo IN ('partido','equipo','jugador','arbitro','pabellon')),
        canonica_id BIGINT NOT NULL, fuente TEXT NOT NULL REFERENCES fuente, id_en_fuente TEXT NOT NULL, nombre TEXT NOT NULL,
        fecha_juego_et DATE, temporada TEXT,            -- solo tipo 'partido' (hechos inmutables)
        atributos JSONB NOT NULL DEFAULT '{}', creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (fuente, id_en_fuente, tipo))

-- nba.captura: registro de cada petición; el original vive como archivo con hash
captura(captura_id BIGINT IDENTITY PK, fuente TEXT NOT NULL REFERENCES fuente, objetivo TEXT NOT NULL,   -- URL o contrato
        fase TEXT CHECK (fase IN ('pre','cierre','final','historico')), partido_id BIGINT REFERENCES entidad,
        solicitado_en TIMESTAMPTZ NOT NULL, recibido_en TIMESTAMPTZ, http_status INT, ok BOOLEAN NOT NULL,
        sha256 TEXT, bytes INT, ruta TEXT, error TEXT, creditos NUMERIC(6,2) NOT NULL DEFAULT 0)

-- nba.dato: UNA tabla en formato largo para todo lo que no es cuota ni jugada
dato(dato_id BIGINT IDENTITY PK, partido_id BIGINT NOT NULL REFERENCES entidad, entidad_id BIGINT NOT NULL REFERENCES entidad,
     periodo SMALLINT NOT NULL DEFAULT 0, metrica_id SMALLINT NOT NULL REFERENCES metrica,
     valor DOUBLE PRECISION, etiqueta TEXT, CHECK (valor IS NOT NULL OR etiqueta IS NOT NULL),
     fase TEXT NOT NULL CHECK (fase IN ('pre','cierre','final')), fuente TEXT NOT NULL REFERENCES fuente,
     captura_id BIGINT REFERENCES captura, recibido_en TIMESTAMPTZ NOT NULL,
     pit TEXT NOT NULL DEFAULT 'posterior' CHECK (pit IN ('posterior','reconstruido','no_acreditado')),
     conflicto BOOLEAN NOT NULL DEFAULT false,
     UNIQUE (partido_id, entidad_id, periodo, metrica_id, fase, fuente, captura_id))

-- nba.cuota: un precio de un contrato en un instante
cuota(cuota_id BIGINT IDENTITY PK, partido_id BIGINT NOT NULL REFERENCES entidad, fuente TEXT NOT NULL REFERENCES fuente,
      casa TEXT NOT NULL, mercado TEXT NOT NULL, periodo SMALLINT NOT NULL DEFAULT 0, entidad_id BIGINT REFERENCES entidad,
      linea NUMERIC(6,2), lado TEXT NOT NULL, cuota NUMERIC(8,3) NOT NULL CHECK (cuota > 1),
      contrato_id TEXT NOT NULL, fase TEXT NOT NULL CHECK (fase IN ('pre','cierre')),
      captura_id BIGINT REFERENCES captura, recibido_en TIMESTAMPTZ NOT NULL,
      UNIQUE (fuente, casa, contrato_id, lado, recibido_en))

-- nba.evento: jugada a jugada (con coordenadas y quinteto en pista)
evento(partido_id BIGINT NOT NULL, fuente TEXT NOT NULL, secuencia INT NOT NULL, periodo SMALLINT NOT NULL, reloj_s REAL NOT NULL,
       equipo_id BIGINT, jugador_id BIGINT, tipo TEXT NOT NULL, subtipo TEXT, x REAL, y REAL, acierto BOOLEAN, puntos SMALLINT,
       marcador_local SMALLINT, marcador_visit SMALLINT, en_pista_local BIGINT[], en_pista_visit BIGINT[],
       captura_id BIGINT REFERENCES captura, recibido_en TIMESTAMPTZ NOT NULL, PRIMARY KEY (partido_id, fuente, secuencia))

-- nba.pronostico: salida sellada del motor, cadena de hashes
pronostico(pronostico_id BIGINT IDENTITY PK, partido_id BIGINT NOT NULL REFERENCES entidad, mercado TEXT NOT NULL,
           periodo SMALLINT NOT NULL DEFAULT 0, entidad_id BIGINT REFERENCES entidad,
           version_modelo TEXT NOT NULL, version_datos TEXT NOT NULL,            -- sha256 del conjunto de filas visibles
           objetivo_en TIMESTAMPTZ NOT NULL, sellado_en TIMESTAMPTZ NOT NULL,
           escenarios JSONB NOT NULL, distribucion JSONB NOT NULL,                -- ver nba.v2.distribucion
           hash_previo TEXT NOT NULL, hash TEXT NOT NULL UNIQUE,
           UNIQUE NULLS NOT DISTINCT (partido_id, mercado, periodo, entidad_id, version_modelo, objetivo_en))  -- Postgres 16
```

**Vistas y funciones (el único camino de lectura del motor):**
- `nba.dato_a_las(corte timestamptz)` → filas `dato` con `recibido_en <= corte`, una por (partido, entidad, periodo, métrica, fase) elegida por prioridad de fuente y luego por `recibido_en` más reciente. Es el acceso punto-en-el-tiempo; el motor no lee `nba.dato` directo.
- `nba.dato_vigente`: lo mismo con `corte = now()`. `nba.conflicto`: filas con `conflicto = true` y la fuente alternativa.
- `nba.cuota_cierre`: última `cuota` con `fase='cierre'` por contrato; `nba.cuota_margen`: suma de probabilidades implícitas − 1 por grupo (no se guarda el margen: regla de derivados).
- **Reconciliación de la ficha 67:** el método de quitado de margen NO se guarda en `cuota`; se registra en `nba.pronostico.version_modelo` y en los informes.

**Refinamientos hechos en el Sprint 0:** `nba.metrica.resolucion` (`prioridad`/`por_fuente`) decide cómo `dato_a_las` resuelve fuentes; `nivel` admite `equipo_jugador`; la clave única de `nba.dato` incluye `recibido_en` (versiones horarias sin colisión); `nba.migracion` es infraestructura del ejecutor; las tablas de evidencia rechazan cambios con disparadores por sentencia.

**Disponibilidad y árbitros** no tienen tabla propia: son métricas de `nba.dato` con `fase='pre'` (estado oficial como `etiqueta` + probabilidad de jugar en `valor`; `rotowire`/`espn`/`nba_oficial` como fuentes distintas; árbitro asignado con `entidad_id` del árbitro). Cada versión del parte queda como fila nueva (ficha 61).

**Conflictos:** el cargador compara la fila nueva con la vigente de otra fuente; si difiere más que la tolerancia de la métrica (columna `tolerancia` en el catálogo de adaptadores, no en la tabla), marca `conflicto = true` en ambas inserciones. Nunca se sobrescribe. Rebotes de equipo = suma de jugadores (`reboundsPersonal`), como en la Fase 1.

## 3. Captura (qué entra, cuándo, de dónde)

Cada colector escribe primero el original en `apps/nba/.local/captura/<fuente>/<aaaa-mm-dd>/<sha256>` y una fila en `nba.captura`; el adaptador convierte a filas de `dato`/`cuota`/`evento` en una transacción (idempotente: reintentar no duplica por la clave única).

| Colector | Fase | Frecuencia | Qué trae | Estado |
|---|---|---|---|---|
| ESPN (`run57`, ya en el VPS) | pre | cada 15 min / lesiones cada hora | calendario, plantillas, lesiones (Out/Day-To-Day/Suspension) | **Corre ya**; el adaptador lee su ledger SQLite `receipts.sqlite` + `blobs/` (solo lectura) |
| Parte oficial NBA (PDF) | pre | cada hora desde 5 PM ET (según el calendario del parte) | estado por jugador y partido (Out/Doubtful/Questionable/Probable/Available) | Código existente `injury_pdf.py`/`injury_t60.py`; falta captura continua |
| Rotowire | pre | cada hora desde 6 h antes del primer salto, cada 15 min en la última hora | quinteto esperado, `MAY NOT PLAY`, probabilidad de jugar (5 niveles), árbitros, minutos proyectados (`get-projected-minutes.php?team=`) | Probado 2-nov, directo (ZenRows solo si bloquean); revisar términos |
| PropLine (archivo compartido) | pre / cierre | lo que ya capture el recolector horario | cuotas de partido y props | **Leer el archivo; no hacer peticiones duplicadas** |
| The Odds API / SharpAPI | cierre | solo faltantes del cierre, con tope de créditos | cuotas de cierre | Orden fijado por el titular |
| `cdn.nba.com` vía Scrapfly | final | una vez por partido ≈ 20 min tras el final, reintento a los 60 | resumen (box score, árbitros, asistencia) y jugada a jugada | Solo hacia adelante; D6 |
| SofaScore | final / histórico | solo lo que suba el titular | 6 temporadas históricas; respaldo manual | Sin captura diaria |

**Backfill (una vez, Sprint 1):** importar lo ya normalizado en `apps/nba/.local/normalized` (cajas completas, rotaciones, partes oficiales 2021-26: 816 + 1.910 PDF, 238 faltantes conocidos; cuotas bet365/BetsAPI 34.713 filas; h2h Odds API 325 snapshots). Todas las filas históricas con `pit = 'reconstruido'` y `recibido_en` = fecha del propio parte/descarga, nunca "ahora". El backfill no cambia el original ni los hashes.

**Respaldo:** copia diaria de la base y de `captura/` fuera del VPS (hoy no existe; es un hueco de `run57`).

## 4. Motor v2 (`apps/nba/src/nba/v2/`)

Firmas exactas; los cuerpos los decide quien implemente, guiado por las fichas citadas.

```python
# distribucion.py — objeto común de salida
@dataclass(frozen=True)
class Distribucion:
    tipo: Literal["muestras", "pmf"]          # "pmf" para conteos pequeños; "muestras" para continuos
    valores: np.ndarray                         # soporte o muestras ordenadas
    pesos: np.ndarray | None
    def prob_mas_de(self, linea: float) -> float: ...     # P(X > linea), empate repartido en lineas enteras
    def prob_menos_de(self, linea: float) -> float: ...
    def cuantil(self, p: float) -> float: ...
    def a_json(self) -> dict: ...               # cuantiles 0,5..99,5 % para sellar y servir

# pit.py
@dataclass(frozen=True)
class Instantanea: partido_id: int; corte: datetime; filas: pd.DataFrame; version_datos: str
def instantanea(db, partido_id: int, corte: datetime) -> Instantanea: ...   # solo filas visibles en `corte`

# disponibilidad.py   (fichas 17, 18, 61, 73)
@dataclass(frozen=True)
class Escenario: prob: float; ausentes: frozenset[int]; titulares: tuple[int, ...]
def escenarios(inst: Instantanea, equipo_id: int, max_escenarios: int = 8) -> list[Escenario]: ...  # suma prob == 1

# minutos.py          (fichas 9, 11, 18, 52, 58)
def minutos(inst: Instantanea, jugador_id: int, esc: Escenario) -> Distribucion: ...  # mezcla: juega normal + salida temprana (~1/30) + no juega

# nucleo.py           (fichas 1, 4, 7, 35, 44)
@dataclass(frozen=True)
class Marcador: muestras: np.ndarray        # (n, n_periodos, 2): puntos local/visitante por periodo (4 + hasta 3 prórrogas)
def simular_marcador(inst: Instantanea, esc_local: Escenario, esc_visit: Escenario, n: int, semilla: int) -> Marcador: ...
def mezcla_escenarios(partes: Sequence[tuple[float, Marcador]]) -> Marcador: ...

# mercados.py
Mercado = Literal["ganador", "handicap", "total", "total_equipo", "margen_victoria"]
def derivar(m: Marcador, mercado: Mercado, periodo: int, linea: float | None, equipo: Literal["local", "visit"] | None = None) -> float | Distribucion: ...

# props.py            (fichas 12, 13, 41, 46, 62, 72, 73)
Estadistica = Literal["pts", "reb", "ast", "tres", "stl", "blk", "r_a", "pra"]
def simular_jugador(inst: Instantanea, jugador_id: int, esc: Escenario, m: Marcador, n: int, semilla: int) -> dict[Estadistica, Distribucion]: ...
def dobles(sim: dict[Estadistica, Distribucion]) -> dict[Literal["doble_doble", "triple_doble"], float]: ...
def primer_anotador(inst: Instantanea, esc_local: Escenario, esc_visit: Escenario, n: int, semilla: int) -> dict[int, float]: ...

# referencia.py       (fichas 5, 22, 23, 67)
def quitar_margen(cuotas: Sequence[float], metodo: Literal["proporcional", "potencia", "shin"]) -> list[float]: ...  # suma 1

# evaluacion.py       (fichas 5, 34, 64)
def informe_binario(p: np.ndarray, y: np.ndarray, base: np.ndarray | None, estratos: pd.DataFrame | None) -> dict: ...
def informe_conteo(dist: Sequence[Distribucion], y: np.ndarray, base_media: np.ndarray) -> dict: ...  # cobertura 80/50, MASE, Mincer-Zarnowitz

# sellado.py
def sellar(db, p: PronosticoNuevo) -> str: ...        # hash; cadena con candado de aviso; rechaza si objetivo_en > sellado_en
def verificar_cadena(db) -> int: ...                  # nº de filas verificadas; lanza si hay ruptura
```

**Reglas del núcleo (v2.0):** deriva = fuerza esperada del equipo (rating lento tipo Elo/Kalman + cuatro factores suavizados, localía y descanso estimados por temporada) ajustada por ausencias (suma de minutos esperados × impacto regularizado); ritmo esperado = f(ritmo de ambos); correlación entre puntos de los dos equipos estimada por temporada (ficha 4: ~0,4 en su época, a remedir); colas t; último cuarto con deriva casi nula y correlación negativa con el tercero (ficha 7); prórroga como periodos 5–7 cuando hay empate al final del 4.º. Hándicap/total de mitades y cuartos salen del mismo `Marcador` (coherencia por construcción: ficha 27/28).

**Reglas de props:** puntos = minutos × tasa (binomial negativa con encogimiento jerárquico por rol, ficha 62); correlaciones entre estadísticas del mismo jugador por cópula gaussiana condicionada a minutos, estimadas por rol (ficha 12); rebotes en dos etapas con efecto de alineación (ficha 73); línea base ingenua obligatoria (media de 5 partidos ajustada por minutos y media de temporada).

**Referencia del mercado:** solo como comparación y como ancla opcional; nunca se publica una referencia fuera de 10–90 % (ficha 16). Método de quitado de margen elegido por mercado con log-loss (Sprint 5).

## 5. Pruebas y puertas de aceptación (las ejecuta la Fase 4)

Umbrales **propuestos**, a aprobar. Evaluación hacia adelante (ajuste ≤ 2024-25, prueba 2025-26 y lo prospectivo), con intervalo.

| Puerta | Criterio |
|---|---|
| G-fuga | Reproducibilidad puntual: en 200 partidos pasados, regenerar a la hora del sello con `instantanea` y obtener el mismo `version_datos` y distribución; 0 diferencias. Ganador con Brier < 0,18 ⇒ revisar fuga antes de celebrar |
| G-coherencia | 0 violaciones: ganador ≥ hándicap favorito; escaleras de líneas monótonas; probabilidad conjunta entre cotas de Fréchet; suma de periodos = partido |
| G-equipo | Pendiente de calibración 0,9–1,1 en cada mercado de equipo; Brier no peor que el motor v1.5 (referencia: margen 0,1845, total 0,1911 en 2025-26) ni que la climatología; diferencia contra el cierre con IC (sin diferencia significativa es resultado válido) |
| G-props | Cobertura del rango 80 % ∈ [77 %, 83 %] (hoy 73 %); MASE ≤ 1,00 frente a la media de 5 partidos; log-pérdida ≤ línea base; sin sesgo por rango de minutos |
| G-disponibilidad | Escenarios suman 1 en todos los partidos de prueba; probabilidad condicionada a jugar vs. sin jugar separada y publicada |
| G-operación | Cálculo de un día completo en el VPS dentro de la ventana definida por el calendario (medir en el Sprint 3); recuperación desde respaldo comprobada |
| Montecarlo | 20.000 simulaciones por partido; semilla fija; error de Montecarlo de las probabilidades < 0,5 pp |
| Estrés | Día de 15 partidos con 30 fuentes caídas simuladas: nunca se publica un pronóstico con datos faltantes imputados como 0 |

Pruebas por capa: unitarias de cada función de la sección 4 (casos con valores exactos), integración contra Postgres efímero (`nba_test_<uuid>`) para esquema, triggers de inmutabilidad y `dato_a_las`, contratos de adaptadores con originales congelados.

## 6. API y web

- **API de lectura** (`nba.api`, solo `SELECT` con rol de lectura): `GET /nba/v1/cartelera?fecha=`, `GET /nba/v1/partido/{id}` (resumen + mercados de equipo), `GET /nba/v1/partido/{id}/jugador/{id}` (distribuciones por estadística y control de línea), `GET /nba/v1/sello/{hash}` (verificación), `GET /nba/v1/calibracion` ("Cómo acertamos").
- **Web:** pestaña NBA dentro de la web única; cartelera por partido (probabilidad de ganar, marcador proyectado, estado del sello), página de partido (Equipo / Jugador / Especiales / pie con sello), página de calibración. Diseño final tras tus comentarios al boceto; estética CyberCore; bloqueo de contenido de pago con las mismas reglas de cuentas que fútbol.
- Mostrar siempre rangos (p10–p90) y "si juega: x %"; sin "picks", stakes ni notificaciones de apuesta (ficha 24, 68).

## 7. Operación

Procesos del VPS: `nba-db` (Postgres), `nba-captura` (colectores), `nba-motor` (inferencia + sellado por partido a la hora objetivo), `nba-api`. Alertas operativas por el canal de alertas existente. Cada despliegue se anota en `DEPLOYS.md` con su vuelta atrás. Entrenamiento y backtest en local (`scripts/entrenamiento_local/`), con `check_leakage`-equivalente propio (G-fuga).

## 8. Revisión de casos límite (Review Focus)

Cada línea tiene su prueba en el sprint indicado.

1. **Prórroga:** total y ganador incluyen prórroga; mercados de mitad y cuarto no. Probar un partido con 2 prórrogas (S3).
2. **Aplazado, suspendido o sin resultado:** el mercado se anula (no entra en la evaluación ni cuenta como acierto/fallo) (S5).
3. **Identidad de jugador:** traspaso a mitad de temporada, mismo nombre en dos jugadores, cambio de id en una fuente; el alias no parte el historial (S1).
4. **Fuente caída en captura final:** se registra `ok = false`; no se escribe ningún `dato` con 0 imputado; el motor degrada o se niega a sellar según la métrica (S1, S2).
5. **Líneas extremas:** línea fuera del soporte ⇒ probabilidad acotada a [0,001; 0,999] y marcada; nunca NaN ni 0/1 exactos (S3, S4).
6. **Zona horaria:** partido ET que cruza medianoche UTC conserva su `fecha_juego_et`; los cortes del sello se calculan en UTC (S1).

## 9. Sprints propuestos (Fase 3; no empiezan sin aprobación)

| Sprint | Entregable verificable | Depende de |
|---|---|---|
| S0 | `nba-db` local y en VPS (vacío), migraciones con triggers, roles, `nba.metrica`/`fuente` sembradas, pruebas de inmutabilidad y `dato_a_las` | D1 |
| S1 | Colectores (ESPN-lectura, parte oficial, Rotowire, cdn) + adaptadores idempotentes + backfill desde `.local`; informe de cobertura y conflictos; respaldo diario fuera del VPS | S0, D6 |
| S2 | Disponibilidad (escenarios) y minutos con cola de salida temprana; evaluación en retrospectiva contra minutos reales | S1 |
| S3 | Núcleo del marcador y mercados de equipo (ganador, hándicap y total del partido y de mitad, total de equipo, margen) con coherencia por construcción; G-equipo y G-coherencia | S1, S2 |
| S4 | Props: puntos, rebotes, asistencias, triples, R+A, PRA, robos, tapones, dobles, primer anotador; G-props | S2, S3 |
| S5 | Referencia de mercado (`quitar_margen`), módulo único de evaluación, sellado en cadena, G-fuga | S3, S4 |
| S6 | `nba.api` + web NBA (6 idiomas) + página de calibración | S5, boceto aprobado |
| S7 | Fase 4 completa (Montecarlo, estrés, reproducibilidad), informe para el titular y propuesta de promoción | S0–S6 |

S1 y S2 pueden avanzar en paralelo tras S0 si trabajan archivos distintos (colectores vs. `v2/`).

## 10. Riesgos y pendientes

- Términos de uso de Rotowire sin confirmar; ProSportsTransactions descartado (sin créditos).
- Saldo de Scrapfly desconocido hoy (D6); el plan Free de ZenRows (5.000/mes) está compartido con el scraper del VPS.
- Deriva de anotación (2025-26 +1,7 a +3,9 puntos sobre la tendencia, `docs/nba_calibracion_motor_20261024.md`): el núcleo debe reestimar niveles por ventana móvil; no se corrige con un intercepto fijo.
- Los umbrales de la sección 5 y las constantes de la sección 4 (≈ 1/30 de salida temprana, correlación ~0,4) vienen de la literatura y deben remedirse con 2021-26 antes de congelarse.
- El piloto vivo (v1.x) sigue sirviendo mientras tanto; su retirada es una decisión posterior.
