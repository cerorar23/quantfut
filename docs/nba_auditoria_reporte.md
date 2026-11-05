# Auditoría forense del motor NBA publicado

> La auditoría original se conserva a continuación. Tras la autorización posterior del titular se implementaron correcciones en una rama aislada: [estado, pruebas y límites de las correcciones](nba_auditoria_correcciones.md). Esta nota no acredita un despliegue.

Fecha: **4 de noviembre de 2026**. Modalidad: **solo lectura**. Alcance corregido con la indicación del titular: auditar **la última versión efectivamente publicada en el VPS**, no suponer que el checkout local coincide con ella.

## 1. Dictamen y alcance comprobado

**No se acredita que el motor esté libre de fugas, sobreajuste o errores de valoración.** Se identificaron **7 hallazgos CRÍTICOS, 7 MAYORES y 1 MENOR**. La severidad se refiere al componente afectado; no significa que todos los fallos hayan ocurrido ya en un pronóstico real.

Los principales resultados reproducidos son: un join que permite información recibida después del corte; una carrera temporal que permite sellar después del salto; probabilidades incorrectas para contratos con devolución por push; una CDF discreta mal reconstruida; minutos físicamente imposibles; y truncamiento de masa probabilística sin control de tolerancia.

La falta de una proyección explícita de posesiones se clasifica CRÍTICA **siguiendo el criterio solicitado por el titular**. Por sí sola, esta ausencia no constituye una demostración matemática de que toda predicción directa de puntos sea inválida.

### Identidad del despliegue

| Elemento | Evidencia observada en el VPS |
|---|---|
| Imagen que ejecuta el cron del motor | `nba-motor:d73c7c5` |
| ID de esa imagen | `sha256:b35c3cb2da067e617799c3680217719c4b32530db2a71969d3ef0067e4e864d8` |
| Entrada del motor | `python -m nba.v2.motor`, cada cinco minutos, desde `ejecutar_motor.sh` |
| Versión anunciada por las últimas ejecuciones | `equipo-2.1`; impacto `c5757c3c8f0e`; props `6323d806ed81` |
| API activa | `nba-api:1c7fd93`, entrada `nba.api.app:app_desde_entorno` |
| ID de imagen de la API | `sha256:bfa7f61cb3875ae543558fde26852294ca0a349ccbba8bb90e3a61c252a24900` |
| Parámetros incluidos en el motor | `impacto.json` y `props.json`, ambos con `datos_hasta=2026-11-02` |
| Pronósticos existentes al consultar | 192: **4 de equipo v2.0 y 188 de props v2.0** |
| Pronósticos de equipo v2.1 guardados | **0** en la base consultada |

La versión ejecutable publicada es v2.1; la evidencia prospectiva almacenada todavía corresponde a versiones anteriores. Las diez últimas ejecuciones inspeccionadas, de 14:05 a 14:50 UTC del 4 de noviembre, anunciaban v2.1 y no registraban errores ni nuevos sellos. Esto no prueba una avería: ninguna de esas pasadas, por sí misma, acredita que hubiera un partido que debiera sellarse.

### Preservación

- No se modificó código base, configuración, parámetros, cron, servicios ni datos de producción. No se hicieron commits ni despliegues.
- Se copiaron **101 archivos de la imagen del motor y 136 de la API**, con SHA-256 por archivo. Los diagnósticos verificaron que las copias conservaran esos hashes.
- Se verificó que los **139 archivos del checkout local** inicialmente inventariados conservaran sus hashes.
- Las consultas usaron la cuenta `nba_api`, con `default_transaction_read_only=on`; el servidor confirmó `transaction_read_only=on`, PostgreSQL 16.15.
- La reproducción SQL del join futuro utilizó exclusivamente `SELECT` y CTE con `VALUES`. No insertó filas de prueba.
- La imagen del motor se leyó mediante un contenedor temporal sin red, sin volúmenes, con raíz de solo lectura y entrada Python de diagnóstico. No se ejecutó su proceso de pronósticos.

Los archivos nuevos se limitan a este informe y a evidencia/diagnósticos en `tmp/nba_auditoria_20261104/`.

## 2. Cómo reproducir y localizar la evidencia

Las referencias siguientes son **líneas de las copias exactas del VPS**, no archivos equivalentes del checkout antiguo:

| Prefijo usado en el informe | Ubicación local |
|---|---|
| `M/` | `tmp/nba_auditoria_20261104/motor/src/nba/` |
| `A/` | `tmp/nba_auditoria_20261104/api/src/nba/` |

Dentro de la imagen, esas rutas corresponden a `/app/src/nba/`. Los manifiestos `motor_hashes.json` y `api_hashes.json` fijan sus bytes.

Evidencia principal:

- `runtime_metadata.json`: imagen activa, comando y resúmenes operativos sin secretos.
- `database_readonly.json`: consultas, versiones, pronósticos, resultados y función PIT observada.
- `database_probes.json`: prueba SQL del join futuro, constraints y triggers reales de sellado.
- `diagnostics_v2.py` / `diagnostics_v2.json`: reproducciones sobre el código publicado.
- `supplement_v2.py` / `supplement_v2.json`: CDF no degenerada, comprobación SQL, dependencia estadística e integridad.
- `calibracion_v2_publicada.json`: copia del resumen histórico que sirve la API.
- `queries_readonly.sql`: consultas de inspección exportadas para revisión.

Reproducción **sin conexión al VPS**, desde la raíz del proyecto y con las copias ya conservadas:

```powershell
$auditPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $auditPython -B tmp/nba_auditoria_20261104/diagnostics_v2.py
& $auditPython -B tmp/nba_auditoria_20261104/supplement_v2.py
```

Esos scripts bloquean conexiones de red y escriben únicamente resultados de diagnóstico. La prueba del sellado emplea las funciones reales del motor y de sellado con una conexión SQL simulada; no llama a producción.

**Pruebas iniciales del checkout:** 242 pruebas existentes pasaron en 23,40 segundos, sin intentos de conexión de red. Correspondían al árbol local anterior a v2 y **no certifican v2.1**. Sus resultados y los diagnósticos preliminares se conservan como antecedentes; los hallazgos siguientes se basan en las imágenes publicadas.

## 3. Hallazgos CRÍTICOS

### C01. Join del futuro en la comprobación de participación de la plantilla

**Dimensión:** temporalidad. **Estado:** reproducido mediante SQL real con datos sintéticos.

**Código:** `M/v2/plantilla_pit.py:43`, subconsulta `EXISTS` de `Q_ULTIMO_EQUIPO`.

La fila de equipo `t` exige visibilidad temporal, pero la fila de minutos `dm` que demuestra que el jugador participó **no exige `dm.recibido_en <= corte` ni una política PIT equivalente**. Una observación de participación recibida después del corte puede cambiar el último equipo admitido y, por tanto, la plantilla.

**Prueba V15:** para un corte del 2 de noviembre se definió una afiliación recibida el día 1 y la única evidencia de minutos recibida el día 3. La consulta original devolvió `[(7, 10)]`; la misma consulta con guardia de recepción devolvió `[]`. Se ejecutó en PostgreSQL 16, en solo lectura, sustituyendo únicamente las tablas por CTE sintéticas.

**Impacto:** el replay deja de ser invariante frente a información futura. La existencia de fechas de partido anteriores no resuelve una recepción posterior al corte.

**Criterio de cierre:** todas las dependencias de la subconsulta deben respetar la misma política temporal y superar esta prueba. No se aplicó ningún cambio.

### C02. El proceso puede sellar después del tip-off si el cálculo cruza esa hora

**Dimensión:** temporalidad y servidor. **Estado:** reproducción de la carrera; no se observó ocurrencia en los sellos reales consultados.

**Código:** `M/v2/motor.py:54`, `:69` y `:96`; `M/v2/sellado.py:47`.

`ahora` se fija al comienzo de la ejecución. El control `ahora >= inicio` usa ese valor aunque las consultas y el cálculo terminen más tarde. `sellar()` consulta el reloj real de la base, pero solo comprueba `objetivo_en <= ahora`; no conoce ni valida el tip-off.

**Prueba V06:** inicio de ejecución `01:00:00`, salto `01:00:01`, reloj SQL al insertar `01:00:03`: el flujo real aceptó el sello, sin errores. Se simuló únicamente la conexión SQL y el tiempo consumido por el predictor.

**Contraste V16:** los triggers reales de `nba.pronostico` impiden UPDATE/DELETE/TRUNCATE; no hay trigger de INSERT ni constraint que contraste la hora del sello con el salto. **En los 192 sellos reales examinados hubo 0 posteriores al tip-off conocido al sellar.**

**Impacto:** la garantía declarada «nunca se sella después del salto» no está asegurada hasta la persistencia. La prueba no demuestra que se hayan usado resultados futuros en un sello real.

**Criterio de cierre:** comprobar la hora efectiva inmediatamente antes de persistir, incluyendo procesos lentos y esperas de bloqueo.

### C03. Los pushes se convierten en media victoria al mostrar probabilidades

**Dimensión:** matemáticas y liquidación. **Estado:** reproducido en funciones usadas por la API.

**Código:** `M/v2/props.py:60`, `M/v2/mercados.py:20`, `M/v2/distribucion.py:35`; consumo en `A/api/app.py:210`.

Las funciones calculan `P(victoria) + 0,5·P(push)` y presentan el complemento como la otra dirección. Esa cantidad no es `P(victoria)` ni, en general, la probabilidad de victoria condicionada a que la apuesta no se devuelva.

**Prueba V02:** con victoria 15 %, push 80 % y derrota 5 %, tanto props como hándicap devuelven **55 %**. Para una apuesta con devolución, `P(victoria | no push)=75 %`; la cuota decimal justa es `(1−0,80)/0,15=1,3333`, no `1/0,55=1,8182`.

**Impacto:** las líneas enteras no pueden valorarse correctamente invirtiendo la probabilidad expuesta. La salida pierde la masa de devolución como resultado separado. Esto no prueba que un libro de apuestas real haya liquidado un push como derrota: no se localizó ese liquidador en el flujo activo.

**Criterio de cierre:** distinguir victoria, devolución y derrota, y declarar qué probabilidad se expone y se usa para valorar el contrato.

### C04. La API reconstruye incorrectamente la CDF cuando se repiten cuantiles

**Dimensión:** matemáticas y calibración. **Estado:** reproducido con distribución degenerada y con simulación no degenerada.

**Código:** `A/api/app.py:34`, especialmente `:39` y `:44`.

La API añade una perturbación a los cuantiles repetidos para interpolarlos como si fueran valores continuos. Esa perturbación no conserva correctamente la masa de una distribución discreta.

**Prueba V03:** 199 cuantiles iguales a 5 y línea 5 producen `p_mas=0,995`. Para esa distribución, `P(X>5)=0` y `P(push)=1`.

**Prueba V14:** con 100.000 marcadores generados por el propio núcleo, media de margen 4 y línea 4, la API devuelve **51,00 %**; las muestras dan `P(margen>4)=48,396 %`, push 2,964 % y probabilidad condicionada sin push 49,874 %. El error frente a la probabilidad estricta documentada es **2,604 puntos porcentuales**, sin bandera de extremo.

**Impacto:** la probabilidad servida no reproduce la ley simulada ni una regla consistente de devolución.

**Criterio de cierre:** contrastar la consulta de líneas contra frecuencias/masas originales, especialmente en valores repetidos y extremos.

### C05. La plantilla puede asignar 128 minutos esperados a un jugador

**Dimensión:** matemáticas y lesiones. **Estado:** reproducido con probabilidades del artefacto publicado.

**Código:** `M/v2/plantilla.py:86`; uso en `M/v2/equipo_jugadores.py:23` y `:42`.

`minutos_esperados()` reescala proporcionalmente los minutos para sumar 240, pero no impone capacidad por jugador. Tener ocho candidatos no garantiza una asignación físicamente válida.

**Prueba V04:** ocho candidatos con estado `Available`, uno con 40 minutos previstos y siete con 5 minutos, usando la probabilidad `Available` real del artefacto, producen **128 minutos para el primero y 16 para cada otro**. Suman 240 y superan el requisito de ocho candidatos del modelo v2.1.

**Impacto:** esos minutos alimentan directamente la contribución de jugadores al margen. Una lesión o plantilla incompleta puede inflar el impacto de una estrella sin que la validación de la distribución final detecte el problema.

**Criterio de cierre:** validar capacidad individual y colectiva y definir qué ocurre cuando la plantilla no sostiene una asignación admisible.

### C06. Se elimina masa de la cola de props y se renormaliza sin comprobarla

**Dimensión:** matemáticas y calibración. **Estado:** reproducido con la sobredispersión publicada.

**Código:** `M/v2/props.py:13`, `:51`; `M/v2/motor_jugadores.py:43` y `:44`.

La ley de puntos se corta en 70 y se divide por la masa restante. Así se obtiene una distribución condicionada artificialmente a no superar el techo, sin reportar ni limitar la masa eliminada.

**Prueba V10:** con `alfa_puntos=0,22715` del artefacto y 35 minutos constantes:

| Media antes del corte | Masa eliminada por encima de 70 |
|---:|---:|
| 25 | 0,4477 % |
| 35 | **4,1461 %** |
| 45 | **12,9012 %** |

Son escenarios numéricos controlados, no recuentos de jugadores afectados en producción. El caso de media 35 ya supera ampliamente una tolerancia de truncamiento numérico pequeña.

**Impacto:** todas las probabilidades restantes cambian; los resultados superiores al techo pasan a ser imposibles en la PMF publicada. La suma igual a uno deja de ser evidencia de que se conservó la ley original.

**Criterio de cierre:** medir y registrar la masa omitida y demostrar una tolerancia admisible antes de aceptar la distribución.

### C07. El núcleo de totales no proyecta posesiones

**Dimensión:** ritmo. **Estado:** comprobado por código y prueba de insensibilidad; severidad según el criterio del encargo.

**Código:** `M/v2/nucleo.py:36`; `M/v2/motor_equipo.py:36`; `M/v2/equipo_jugadores.py:49`.

La media sale de nivel de puntos de la liga, ataque, defensa y localía. El total v2.1 conserva el núcleo de equipo. No aparece una proyección explícita de posesiones ni una composición posesiones × eficiencia.

**Prueba V07:** introducir hechos propios visibles distintos en la instantánea, representando ritmos 80 y 120, no cambia ninguna salida del predictor de equipo. El predictor usa la historia de puntos e ignora esas filas propias.

**Impacto:** no puede inspeccionarse ni estresarse por separado la exposición de puntos al ritmo. Las medias históricas pueden absorber ritmo de forma implícita; esta prueba no cuantifica el deterioro predictivo atribuible a esa omisión.

**Criterio de cierre:** acreditar una proyección de posesiones o una excepción explícita y validada al requisito del titular.

## 4. Hallazgos MAYORES

### M01. `version_datos` descarta silenciosamente la mitad de sus entradas

**Código:** `M/v2/motor.py:90`, `:104` y `:107`. **Prueba:** V05.

Para equipo se usa `(inst.version_datos + pl.version_datos)[:64]`. Como cada hash ya tiene 64 caracteres, el resultado es exactamente el hash de la instantánea: **la plantilla se descarta**. En props ocurre lo inverso: `(pl.version_datos + inst.version_datos)[:64]` descarta la instantánea.

**Impacto:** `version_datos` no identifica todas las entradas que el código pretende combinar. La cadena sigue protegiendo el contenido efectivamente sellado; este hallazgo no demuestra que su hash criptográfico se pueda falsificar.

**Criterio de cierre:** una modificación de cualquiera de las entradas declaradas debe cambiar la versión combinada.

### M02. La reconstrucción histórica no equivale a disponibilidad original de los datos

**Código:** `M/v2/pit.py:22`; `M/v2/plantilla_pit.py:53`. **Evidencia:** V11 y consulta `input_modes`.

Las filas `pit='reconstruido'` se admiten aunque su recepción sea posterior al corte, siempre que la fecha del partido sea anterior. La base consultada tenía **5.423.163 filas reconstruidas y 33.806 posteriores**; esas cifras describen toda `nba.dato`, no todas las features de un pronóstico.

Es una suposición explícita del diseño, no una fuga oculta demostrada en cada fila. Sin embargo, permite incorporar correcciones de partidos pasados que todavía no existían al corte histórico. Tener el día del partido correcto no acredita la versión original conocida entonces.

**Impacto:** el backtest reconstruido no prueba un replay prospectivo estricto. Debe distinguirse de la prueba C01, que sí reproduce un join futuro para filas `posterior`.

**Criterio de cierre:** separar resultados reconstruidos de evidencia con recepción/versiones originales y medir sensibilidad a correcciones.

### M03. Pydantic valida la forma de la PMF, pero no sus resúmenes matemáticos

**Código:** `M/contratos/base.py:38`; `M/contratos/paso_c.py:50`. **Prueba:** V09.

Existen contratos estrictos: campos extra prohibidos, NaN/inf rechazados y validación antes de sellar y servir. No corresponde acusar a v2 de carecer de tipado.

Pero `DistribucionJugador` acepta una PMF con toda la masa en cero, `media=999` y cuantiles 3/4/5. Se verifica la suma y el orden, no que la media y los cuantiles coincidan con la PMF.

**Impacto:** diferentes partes de la API pueden mostrar magnitudes contradictorias de una misma distribución y superar el contrato.

**Criterio de cierre:** comprobar las invariantes entre PMF y resúmenes con tolerancias declaradas.

### M04. La corrección de empate no constituye un modelo explícito de OT

**Código:** `M/v2/nucleo.py:85`. **Prueba:** V08.

Cuando los puntos enteros simulados empatan, se sortea el ganador y se añade **un punto** a ese equipo. En la prueba de 100.000 simulaciones, el 2,804 % empató antes de la corrección y recibió exactamente ese incremento. No hay parámetro de probabilidad, duración ni anotación adicional de OT.

**Límite importante:** el núcleo se ajusta a marcadores finales de partido completo. Sus medias y varianzas pueden incluir OT implícitamente; la frecuencia de empates por redondeo no es una estimación de la frecuencia real de OT. No se justifica añadir automáticamente puntos extra a una ley ya ajustada a finales.

**Impacto:** no se acredita la calibración específica de la cola de totales en OT ni una semántica explícita de inclusión/exclusión por contrato. La etiqueta de comentario «la prórroga rompe el empate» no resuelve esa validación.

**Criterio de cierre:** definir el objetivo full-game y validar por separado partidos con/sin OT, sin contar dos veces su efecto.

### M05. La evidencia pública de calibración no identifica adecuadamente la versión v2.1

**Código:** `A/api/app.py:240` y `:254`. **Evidencia:** V01/V12, artefacto de calibración copiado y versiones consultadas.

El endpoint combina un resumen histórico estático sin hash de modelo/entradas con métricas prospectivas que agregan todos los pronósticos de equipo, sin separar versiones. El resumen histórico tampoco publica log-loss, aunque la librería sí lo implementa.

Se recalcularon independientemente los únicos cuatro resultados prospectivos de equipo disponibles: **Brier 0,258148; log-loss 0,710000**. Son v2.0. Con cuatro partidos no se puede decidir calibración, habilidad ni sobreajuste, y no deben atribuirse a v2.1.

El artefacto público informa para 2025-26 Brier de ganador 0,2063 frente a 0,1981 del mercado; hándicap 0,2597 frente a 0,2499; total 0,2605 frente a 0,2500. Estos valores se verificaron como contenido del artefacto publicado: **no se regeneró su backtest histórico v2**. Ser peor en Brier no demuestra por sí solo sobreajuste.

Además, `M/v2/equipo_jugadores.py:1` documenta decisiones de mezcla tras comparar validación y prueba 2025-26. Esa prueba ya inspeccionada no acredita un holdout nuevo para el modelo final.

**Criterio de cierre:** vincular métricas a versión, parámetros, población y hashes de datos; conservar una evaluación temporal no utilizada para seleccionar la variante. No se declara a v2.1 calibrada ni sobreajustada con esta muestra.

### M06. Los intervalos de evaluación binaria remuestrean filas, no partidos o fechas

**Código:** `M/v2/evaluacion.py:44`. **Prueba:** V18.

`ic_diferencia()` remuestrea índices de observaciones y no recibe identificadores de partido/fecha. Si se le pasan props de varios jugadores del mismo partido, sus observaciones dependientes se tratan como independientes.

En una prueba con 20 grupos independientes y 50 filas idénticas dentro de cada grupo, la misma diferencia media 0,09 obtiene IC95 **[0,0720; 0,1092]** por filas y **[−0,0300; 0,21075]** por grupos.

**Impacto:** el helper puede producir confianza excesiva con observaciones dependientes. Este ejemplo demuestra el mecanismo; no estima cuánto se estrecharon los intervalos históricos publicados, cuyos call sites/datos completos no se regeneraron.

**Criterio de cierre:** declarar el estimando y la unidad independiente y conservar juntas las observaciones que comparten partido/fecha.

### M07. El VPS vuelve a ajustar los ratings de equipo al recorrer la historia

**Código:** `M/v2/motor_equipo.py:18`; `M/v2/nucleo.py:50`.

Los parámetros globales de props e impacto se cargan desde JSON entrenados en local, lo cual cumple la separación para esas capas. No se encontró un ajuste ridge de impacto ni búsqueda de hiperparámetros dentro del cron activo.

Sin embargo, `_ratings()` empieza con `Ratings()` y recorre la historia en cada pronóstico, llamando a `nucleo.actualizar()`. Esta función modifica ataque, defensa, nivel de liga y localía mediante el error observado y una tasa de aprendizaje. Es **ajuste online reconstruido en el VPS**, no únicamente evaluación de ratings ya persistidos.

**Impacto:** bajo la regla estricta del encargo —VPS solo inferencia sobre artefactos cargados— esa capa incumple la frontera. También repite el recorrido de la historia por partido. No debe confundirse con reentrenar toda la regresión de jugadores.

**Criterio de cierre:** explicitar y aprobar la política de actualización de estado, o demostrar inferencia a partir de ratings versionados sin volver a aprenderlos en cada ejecución.

## 5. Hallazgo MENOR

### MN01. Se reconstruyen y ordenan 400 distribuciones para un pronóstico

**Código:** `M/v2/motor_equipo.py:50`; `M/v2/equipo_jugadores.py:55`; `M/v2/nucleo.py:81`. **Prueba:** V07.

El Monte Carlo sí genera vectores NumPy de 100.000 simulaciones; no hay un bucle Python por simulación. El coste innecesario aparece después: `m.puntos(lado)` vuelve a construir y ordenar la misma distribución dentro de cada comprensión de 199 cuantiles.

Se contaron **400 construcciones**: dos para margen/total y 398 para puntos de ambos equipos. Bastarían cuatro distribuciones reutilizables. El pronóstico completo, con un único partido de historia, tardó **4,21 segundos en la máquina local**; no es una medición del VPS ni una prueba de saturación. Se clasifica MENOR como optimización medida, sin afirmar que el cron de cinco minutos esté saturado.

**Criterio de cierre:** comparar resultados idénticos y coste tras reutilizar las distribuciones, sin modificar hoy la implementación.

## 6. Respuestas a las cuatro dimensiones solicitadas

| Pregunta | Resultado de la auditoría del despliegue |
|---|---|
| ¿Usa minutos/puntos reales del partido objetivo como feature? | Las consultas principales excluyen la fecha objetivo y sus filas finales (`M/v2/pit.py:31` y `:38`). No se probó esa fuga directa. Sí se reprodujo el join temporal C01. |
| ¿Usa cuota de cierre como input en producción? | No se encontró lectura de `nba.cuota` en el camino activo equipo/props analizado. Los módulos antiguos de investigación sí usan cierres; no se les atribuye a v2.1 por coexistir en la imagen. |
| ¿Las lesiones tienen corte válido? | `Q_PARTE`, `plantilla_pit.py:31`, exige recepción `<= corte`, por partido y fuente oficial. Persisten C01 en la plantilla y M02 en reconstrucción histórica. No se encontró uso de la alineación final objetivo en la ruta revisada. |
| ¿Solo se evalúa ROI? | No: `M/v2/evaluacion.py:16` y `:20` implementan Brier y log-loss. La API prospectiva publica Brier y fiabilidad. No corresponde la deficiencia crítica «solo ROI». M05/M06 limitan lo que esa evidencia acredita. |
| ¿Cuando predice 70 % ocurre cerca de 70 %? | No puede certificarse para v2.1: aún no había resultados de esa versión en la base consultada. Hay herramientas de pendiente/intercepto y fiabilidad, pero no una muestra prospectiva suficiente de esta versión. |
| ¿Proyecta ritmo/posesiones? | No de forma explícita: C07. |
| ¿Modela OT? | Ley de finales con efecto histórico potencialmente implícito; corrección de empate de un punto, sin simulación explícita de OT: M04. |
| ¿El push devuelve? | El cálculo de probabilidad divide su masa por mitades: C03/C04. No se acreditó un liquidador monetario activo que haga la devolución. |
| ¿Un DNP se registra como cero/pérdida? | Los props activos se declaran condicionados a jugar y exponen `p_juega` aparte (`motor_jugadores.py:3`). Eso no equivale a liquidar un DNP como derrota. No se localizó un backtester monetario v2 completo que permita certificar la anulación de tickets; en el esquema inspeccionado no hay tabla de apuestas/liquidaciones. |
| ¿Hay contratos fuertes? | Sí, Pydantic estricto y dataclasses; validación antes de sellado/salida. M03 identifica invariantes matemáticas faltantes. |
| ¿Está vectorizado el Monte Carlo? | Sí en su generación principal. MN01 mide un coste repetido en el cálculo de cuantiles. |
| ¿El VPS solo infiere? | Carga parámetros versionados de props/impacto; vuelve a aprender/reconstruir ratings por error de puntos en ejecución: M07. El formato JSON es un artefacto válido; no se penaliza por no ser `.joblib` u `.onnx`. |

## 7. Orden de atención y límites

Antes de confiar en probabilidades de apuestas o ampliar publicación, deben cerrarse C01–C06: temporalidad, persistencia antes del salto, devolución por push, reconstrucción discreta, capacidad de minutos y conservación de masa. C07 requiere resolver expresamente el requisito de posesiones. Cada cierre debe superar la reproducción correspondiente sin cambiar su resultado esperado para ocultar el defecto.

Después corresponde completar procedencia de datos, invariantes de contratos y evaluación por versión, con incertidumbre que respete la dependencia. No se propone reescribir archivos completos ni se entrega una refactorización.

Límites de las conclusiones:

- Las carreras y escenarios extremos son vulnerabilidades reproducidas; **no se presentan como pérdidas o fugas históricas ya ocurridas**.
- Los 192 sellos examinados no mostraron sellado posterior al salto. La ausencia de casos observados no elimina la carrera reproducida.
- No se ejecutaron apuestas, mensajes, capturas pagadas, cambios de esquema, entrenamientos persistentes ni alteraciones del motor.
- No se regeneró el entrenamiento/backtest histórico completo de v2.1 ni se dispone de un holdout nuevo sin inspección previa. El sobreajuste **no queda descartado**.
- La revisión inicial del checkout antiguo y sus 242 pruebas no sustituyen los diagnósticos sobre las imágenes verificadas del VPS.

**Entrega:** auditoría documentada y reproducible; lógica base y producción preservadas. La calibración y la ausencia de leakage del motor publicado siguen sin quedar certificadas.
