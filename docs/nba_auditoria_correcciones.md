# Correcciones de la auditoría NBA — 4 de noviembre de 2026

## Alcance y estado

Autorización: «necesito que arregles todo lo que encontraste en la auditoría». Rama `codex/nba-auditoria-20261104`, basada en `main` `8676e72`. Se preservaron el checkout antiguo, las observaciones originales y la cadena de pronósticos. **Los cambios están en esta rama; todavía no se han publicado en el VPS.**

Se volvió a consultar el VPS: motor `nba-motor:d73c7c5`, API `nba-api:1c7fd93`. No se ejecutaron entrenamientos, migraciones ni escrituras en producción. Las pruebas SQL usan bases `nba_test_*` en un PostgreSQL 16 local dedicado. Tras autorización expresa del titular se exportaron 143.256 cajas de jugadores (ID, partido, equipo, minutos, más/menos y recepción) mediante SELECT y cuenta lectora; el archivo comprimido queda local, fuera del repositorio.

## Matriz de correcciones

| ID | Severidad | Corrección y evidencia ejecutable |
|---|---|---|
| C01 | CRÍTICO | `plantilla_pit.py`: minutos, afiliación y sus originales respetan el corte. `test_auditoria_sql.py::test_exists_de_minutos_no_usa_recepcion_futura` reproduce el join en PostgreSQL. |
| C02 | CRÍTICO | `sellado.py`: comprueba el reloj real después del candado y condiciona el propio INSERT a estar antes del salto. Regresiones de salto pasado y cruce durante el hash; el segundo no inserta ninguna fila. |
| C03 | CRÍTICO | `contratos_apuesta.py`, `mercados.py`, `props.py`: gana/push/pierde/void separados; cuota justa condicionada a acción, EV con devolución. Nunca se inventa 50% para un contrato siempre devuelto. |
| C04 | CRÍTICO | API: los sellos nuevos se valoran con masas exactas; los históricos sin PMF se identifican como aproximaciones. Un átomo no se interpola como continuo; un contrato siempre devuelto produce probabilidades condicionadas nulas. La web muestra «—». |
| C05 | CRÍTICO | `plantilla.py`: asignación acotada, suma 240 y máximo individual `48 × p_juega`. Una plantilla sin capacidad suficiente devuelve vacío y el híbrido usa el núcleo de equipo. |
| C06 | CRÍTICO | `props.py`: soporte adaptativo con cola comprobada ≤1e-10; rechaza superar el presupuesto de soporte. La regresión de media 35 conserva el 4,1461% situado por encima de 70 y conserva la media. |
| C07 | CRÍTICO | `estado_equipo.py`: primero proyecta posesiones y después multiplica las eficiencias por exposición. La prueba de sensibilidad aumenta el ritmo 10% y exige que aumenten las medias en esa proporción. |
| M01 | MAYOR | `pit.combinar_huellas`: SHA-256 con dominio, todas las entradas y orden. Las regresiones cambian cada entrada y permutan su orden. |
| M02 | MAYOR | Se eliminó la exención temporal para reconstruidos. La migración `0009` exige además recepción visible del original; el importador histórico ya no convierte publicación del parte en recepción. Prueba SQL sobre un parte antiguo capturado tarde. No se inventan recepciones históricas inexistentes. |
| M03 | MAYOR | Contratos comprueban masas, medias, cuantiles y probabilidad del ganador. La tolerancia de seis decimales solo se aplica a PMF efectivamente redondeadas. PMF y cuantiles del marcador comparten una CDF para evitar discrepancias de acumulación flotante. |
| M04 | MAYOR | `simular_con_ot`: ley de regulación + rama OT explícita, posesiones compartidas y periodos adicionales hasta deshacer el empate. Dispersión ajustada únicamente con finales sin OT. Se corrigió también la confusión entre 48/53 minutos de partido y 240/265 minutos acumulados. |
| M05 | MAYOR | API: Brier, log-loss y fiabilidad por versión, un partido por versión. Las métricas antiguas no acreditan la versión activa. Se incluyen evaluación temporal y hashes; la calibración prospectiva permanece sin certificar. |
| M06 | MAYOR | `evaluacion.ic_diferencia`: exige grupos declarados y remuestrea fechas completas, preservando el promedio por observación. Se actualizaron sus llamadores y se prueba el cambio de incertidumbre con observaciones dependientes. |
| M07 | MAYOR | Inferencia carga ratings/ritmo congelados en JSON; no llama a `actualizar`. Entrenamiento separado en `ops/entrenar_equipo.py`, ejecutado localmente. Se rechazan artefactos futuros, del día objetivo o caducados; la disponibilidad del artefacto no se retrofecha al momento de la exportación. La historia SQL filtra equipos/fechas antes de resolver versiones, evitando ordenar estadísticas de todos los jugadores. |
| MN01 | MENOR | Cuatro distribuciones por marcador; los 199 cuantiles salen de la misma CDF agregada. El benchmark conserva la ley y detecta explícitamente las diferencias de frontera numérica del código anterior. |

## Evidencia cuantitativa

- Exportación de solo lectura: 6.748 partidos; entrenamiento local con 6.161 exposiciones verificables y 587 descartes explícitos. Datos hasta 2-nov-2026; huella de la exportación en el artefacto. El original permanece fuera del repositorio.
- Evaluación retrospectiva por fecha: dispersión y OT ajustadas hasta 30-jun-2024; ventana del 1-oct-2025 al 30-abr-2026, **1.235 partidos**, sin actualizar con resultados del mismo día antes de predecirlos. Esa ventana terminó utilizándose para rechazar una variante híbrida: ya no se presenta como confirmación independiente de la selección final.
- Ganador: **Brier 0,20550**, **log-loss 0,59795**; referencia constante entrenada antes de la prueba: Brier 0,24626. Diferencia −0,04076, IC95 por 179 fechas [−0,04994; −0,03122]. Pendiente de calibración 1,0735 e intercepto 0,0828, descriptivos.
- OT en la prueba: probabilidad media 5,4701%, frecuencia observada 4,5344% (56 partidos). No se impuso la aproximación 6–8% como constante ni se sumó OT sobre una distribución ya ajustada a finales completos.
- Totales, condicionando solo para diagnóstico a la presencia de OT: cobertura nominal 80% observada 79,05% sin OT (1.179 partidos) y 89,29% con OT (56); RMSE 18,56 y 18,38 respectivamente. La muestra OT es pequeña y no certifica calibración.
- El simulador supera pruebas de frecuencia, empate al terminar regulación en la rama OT, suma de puntos, múltiples prórrogas, ausencia de empate final y rama sin OT intacta. Los bucles recorren periodos/lotes, nunca una iteración por simulación.
- Serialización de 100.000 muestras: 14,418 s → 0,0751 s en esta máquina, **≈192×**. Un cuantil entre 796 cambió por la acumulación flotante anterior; se verificó su coherencia con la PMF, sin exigir conservar un error numérico.

Evidencia versionada: [evaluación temporal](nba_auditoria_evidencia/evaluacion_equipo_20261104.json) y [rendimiento](nba_auditoria_evidencia/rendimiento_20261104.json). El evaluador informa totales con/sin OT y distingue intervalos incondicionales de intervalos condicionados a OT; conocer después que hubo OT no convierte esa información en una entrada disponible antes del salto.

### El híbrido no se activa por defecto

Se entrenó localmente una candidata de regulación sin prior RAPM, con ridge 10 y vida 730 días fijados antes de evaluar, coeficientes congelados por temporada y 1.063 jugadores. Se excluyeron partidos OT del ajuste de impacto para no inventar minutos de regulación por jugador. En 1.235 partidos produjo **Brier 0,21061 / log-loss 0,60919**, frente a **0,20568 / 0,59837** del núcleo comparable; ΔBrier +0,00494, IC95 por fecha [+0,00126; +0,00848]. [Resultado completo](nba_auditoria_evidencia/evaluacion_hibrido_20261104.json).

**Decisión:** la candidata queda rechazada, conservada localmente y sin publicar. El impacto antiguo entrenado sobre finales tampoco acredita el nuevo objetivo de regulación. `parametros.cargar_impacto` exige objetivo, aprobación explícita, procedencia, muestra y un intervalo temporal que no demuestre empeoramiento; una bandera aislada no basta. Sin esa aprobación, el motor usa el núcleo de equipo y registra `impacto_bloqueado`. Los props conservan su modelo y los partes con corte válido. El resultado de esta candidata sin RAPM no demuestra que el antiguo híbrido RAPM sea peor.

Después de fijar esa decisión se evaluó el núcleo en una ventana separada de playoffs (1-may a 30-jun-2026): **43 partidos**, Brier **0,20506**, log-loss **0,59599**, pendiente descriptiva 1,506. [Confirmación separada](nba_auditoria_evidencia/confirmacion_playoffs_20261104.json). La muestra es pequeña y de playoffs; no se utilizó para reajustar o escoger otra variante. La ventana alternativa oct–nov-2026 solo aportaba un grupo de fecha con exposición verificable y el bootstrap la rechazó, sin fabricar un IC.

## Pruebas

Las reproducciones iniciales fallaron con el código anterior. Resultado final desde el worktree completo: **1.224 aprobadas, 18 omitidas**, cero fallos, con PostgreSQL 16 real (832,30 s). Las omisiones son 17 pruebas de entrega legacy sin su DSN independiente y una de privilegio de enlaces Windows; las regresiones SQL v2 sí se ejecutaron.

Tras los cambios de contratos, sellado y textos se repitieron **94 pruebas: todas aprobadas** (44,57 s). Tras incorporar la puerta del híbrido, **359 pruebas v2 con PostgreSQL: todas aprobadas** (245,53 s). Las pruebas adicionales cubren predicciones antes de resultados del mismo día, rechazo de eventos/recepciones futuros, exclusión de identidades contradictorias, minutos objetivo ausentes de la entrada predictiva y bloqueo de impacto sin validación. JavaScript supera `node --check` y el diff supera `git diff --check`.

Revalidación de la última versión de filtros SQL, identificación automática del modelo y puerta del híbrido: **55/55 aprobadas**, cero omitidas (73,12 s), incluidos todos los escenarios de estrés de `test_estres.py`. [Manifiesto de archivos y validación](nba_auditoria_evidencia/validacion_20261104.json).

El baseline de fútbol previo a estas correcciones tenía **10 fallos, 1.748 aprobadas y 122 omitidas**. No se atribuyen esos fallos a NBA ni se declara verde el arnés general. Una corrida intermedia sobre una copia parcial carecía de `scripts/propline_shared.py`; la validación final debe ejecutarse desde el worktree completo.

Se comprobó además que el workflow publicado de `main` `8676e72` estaba verde; eso no acredita todavía esta rama. El job NBA se refuerza con PostgreSQL 16 para ejecutar las regresiones SQL en CI, que antes se omitían por falta de DSN.

## Entrenamiento y publicación

1. En local, exportar con una conexión lectora y transacción `READ ONLY`: `python apps/nba/ops/exportar_equipo.py exportacion_nueva.json` (`NBA_DB_DSN_LECTOR` fuera del repositorio).
2. En local: `python apps/nba/ops/entrenar_equipo.py exportacion_nueva.json equipo_nuevo.json`. La salida debe ser nueva; se conservan las anteriores para replay.
3. Evaluar por fechas con `ops/evaluar_equipo_congelado.py`; el entrenamiento actual no es su propia prueba. Para investigar otro híbrido: `ops/exportar_plantilla.py` y `ops/entrenar_hibrido.py`. La candidata evaluada aquí queda bloqueada; no activar el impacto antiguo o la candidata rechazada por cambiar una bandera.
4. Antes de promover el núcleo, integrar en `main`, exigir los controles del repositorio, respaldar y comparar el runtime con el commit anterior. Aplicar `0009` sin modificar filas históricas ni desactivar triggers; construir solo motor/API desde `main` y ensayar `--simulacro` con usuario lector. La API deriva la versión activa del artefacto; `NBA_VERSION_MODELO_ACTIVA` permite un override explícito.
5. Registrar imágenes/huellas y rollback en `DEPLOYS.md`. Vuelta atrás de imágenes: conservar `nba-motor:d73c7c5` y `nba-api:1c7fd93`; la migración refuerza lecturas y no altera la cadena. No retroceder silenciosamente las garantías temporales.

El artefacto de equipo caduca a las 72 horas: requiere renovación **local** y publicación versionada antes de vencer. No se instaló un entrenamiento en el VPS para ocultar esa necesidad.

El antiguo `ops/g_fuga.py` compara contra ratings reaprendidos de puntos finales. Ahora rechaza acreditar el núcleo 2.2 con esa referencia incompatible, en vez de emitir un pase vacío o dividir entre cero; las nuevas regresiones SQL y de artefactos son los controles ejecutables disponibles.

## Límites que no se pueden cerrar con código

No se puede recuperar una recepción original que nunca fue registrada ni fabricar una muestra prospectiva. La evaluación retrospectiva incluida usa resultados reconstruidos y lo declara; no certifica disponibilidad histórica punto en el tiempo, ausencia universal de sobreajuste, rentabilidad ni calibración del híbrido 2.2. La corrección de atribución y las guardias están implementadas; la certificación estadística y la promoción operativa permanecen pendientes. Los registros históricos erróneos de OT no se reescribieron: el nuevo entrenamiento deriva exposición directamente de minutos validados.
