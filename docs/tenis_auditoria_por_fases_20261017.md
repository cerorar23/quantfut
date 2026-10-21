# Auditoría del motor de tenis por fases

Actualización posterior: se ejecutó la [ampliación de calendario oficial, histórico de pago, calibración y seguimiento](tenis_ampliacion_motor_20261017.md). Ese informe documenta el presupuesto de 2.000 créditos mensuales confirmado por el titular y los resultados nuevos; esta auditoría conserva el estado anterior.

Fecha: 17 de octubre de 2026. Alcance: conversación original completa, implementación local, originales descargados, modelos, pruebas, cuotas y registros. Estado: motor de investigación construido; alcance avanzado y producción pendientes. El diseño es cuantitativo bayesiano/Markov, sin algoritmo de computación cuántica.

## Dictamen

No está al 100% de todo lo planteado en el chat. Hay una base matemática ejecutada y datos suficientes para investigar. Faltan fuentes y experimentos para afirmar que todos los factores se usan, que todos los mercados están calibrados o que existe una ventaja financiera. Tampoco existe una garantía universal de 100% de acierto o rentabilidad.

La auditoría volvió a verificar los 214 originales: 171 TML y 43 MCP, 593.347.344 bytes, sin fallos de hash. Los 492.251 partidos canónicos conservan IDs únicos, 249.938 partidos aptos y conteos dentro de límites. Los dos modelos coinciden con el hash canónico, cantidad de filas y embargo de sus recibos.

## Matriz de alcance

| Fase | Implementado y comprobado | Pendiente para cerrar la fase |
|---|---|---|
| 1. Requisitos | Tenis individual prepartido; ATP/WTA separados; múltiples mercados; límites documentados | Definir un protocolo final de promoción, con mercados, cortes y comparaciones antes de ver resultados futuros |
| 2. Datos | Descarga reproducible, originales, hashes, conflictos, retiros archivados, conteos de saque | Cobertura independiente del calendario y recepción histórica; no basta con descargar hoy resultados antiguos |
| 3. Contexto | Nueva versión conserva 24 campos de edad, lateralidad, pista cubierta, ranking, aces, dobles faltas y quiebres; linaje por archivo/fila | Usarlos como variables solo con disponibilidad temporal comprobada y pruebas de aporte incremental |
| 4. Modelo base | Binomial logit de saque/resto, rival, superficie, regularización, MAP/Laplace, Elo e híbrido de ganador | Habilidades dinámicas y efectos de torneo/edición; separar indoor/outdoor dentro del modelo; incertidumbre completa del híbrido |
| 5. Puntuación | Deuce/tie-break sin corte arbitrario; continuidad de saque; distribución conjunta, mejor de 3/5; marginal del segundo set | Formatos históricos, super-tie-break sustitutivo, sets cortos y riesgo de retiro; aces/duración requieren otros modelos |
| 6. Cuotas y mercados | Ganador, primero/segundo set, juegos totales/hándicaps y alternativas enlazados con líneas reales; margen y devolución separados | Cobertura de mercados/casas y jurisdicción de cada cuenta; calibración de derivados; comisiones y responsabilidad lay |
| 7. Evaluación | Comparaciones temporales 2025/2026, Elo calibrado, Brier/log-loss y controles mensuales | Muestra futura intacta; comparación con mercado sin margen y costes; 2026 retrospectivo queda como desarrollo |
| 8. Operación | Registro anterior a la consulta de precios, controles de tiempo, fuente archivada, límites/créditos e idempotencia de ventana | Fuente de calendario/estado automatizada y probada; servicio supervisado; registro externo de hora; operación continua |
| 9. Liquidación y riesgo | Pinnacle con fuente y fecha; distingue ganar/perder/devolver/anular y conserva retiros | Reglas de otras casas, predicción de retiro y límites conjuntos por jugador, partido y cartera |
| 10. Panel | Informe HTML local con estado por fase y muestra de mercados filtrable | Panel diario conectado, autenticado, con resultados y supervisión; el informe actual es una auditoría local |

## Fallos encontrados y corregidos

1. La captura evaluaba las cuotas usando una hora anterior a su recepción: una cotización nueva podía rechazarse siempre. Ahora se evalúa después de recibirla y se vuelve a comprobar la ventana.
2. El bucle operativo podía omitir el bloqueo por metadatos del torneo. Ahora exige formato/superficie, edición vigente y predicción válida antes de gastar.
3. Una frase y dos booleanos se aceptaban como estado verificado. Ahora se vinculan evento, circuito, participantes y hora del proveedor con un archivo fuente, hash, dominio oficial admitido y observación reciente. La interpretación de ese archivo todavía requiere revisión o un adaptador de fuente comprobado.
4. El pronóstico se escribía después de las consultas pagadas: un fallo podía perder el registro. Ahora se archiva antes y el fallo deja un recibo final con la reserva retenida.
5. Repetir una ventana podía duplicar gastos. Una reclamación SQLite única por torneo/evento/hora/fase impide el segundo intento automático, incluso después de un fallo.
6. Un cambio de participantes u hora entre calendario y cuotas podía reutilizar una orientación vieja. Ahora bloquea esa respuesta y conserva el original para revisión.
7. El total denominado cobro real incluía reservas conservadoras. Ahora informa reservas y créditos confirmados por separado.
8. Los duplicados combinados podían conservar una recepción anterior a los datos que aportaron campos. La normalización v2 conserva todas las fuentes y usa la recepción más tardía; se corrigieron dos filas en una versión nueva.
9. El entrenamiento podía sobrescribir un modelo ya evaluado. Ahora exige un directorio de versión nuevo si existen sus artefactos.
10. La capa de cuotas solo comparaba ganador. Se añadió el adaptador para siete claves reales de mercado, incluyendo segundo set y líneas alternativas. Los demás contratos quedan explícitamente pendientes.

La nota de estado del primer registro del 17-oct tenía `observed_at` posterior a la hora del registro. No sirve como evidencia temporal. El registro original permanece conservado, con la anomalía señalada por la auditoría; sus dos eventos ya estaban bloqueados. Un hash local demuestra coincidencia con el recibo conservado, pero no certifica la hora mediante un tercero ni vuelve inalterable el disco.

La prueba real posterior, a las 20:09:39 UTC, guardó dos eventos con el flujo corregido, cero errores y cero consultas de pago. Los recibos históricos confirman **17 créditos realmente cobrados** (3 de descubrimiento y 14 de cuotas), frente a **29 reservados** conservadoramente. Esto corrige la cifra anterior de 19 que se había atribuido por diferencia de saldo: una cuenta compartida no permite asignar todo movimiento al motor de tenis. Saldo observado: **6.122**, inferior a la reserva de **6.200**; las siguientes consultas pagadas quedan bloqueadas mientras esa condición persista.

## Datos recuperados para las extensiones

Se generó `data/tennis/audit_20261017_v1/canonical_v2/`, sin reemplazar la tabla que alimentó los modelos actuales. Sus 492.251 resultados deportivos coinciden exactamente con la versión anterior; contiene 24 campos de contexto adicionales y trazabilidad completa. Cobertura de 2025 en adelante (incluye los grupos disponibles del circuito; no solo cuadros principales):

| Campo | ATP, 20.604 partidos | WTA, 4.818 partidos |
|---|---:|---:|
| Pista cubierta conocida | 98,84% | 14,07% |
| Edad de la ganadora/jugador ganador | 99,80% | 99,56% |
| Lateralidad de la ganadora/jugador ganador | 99,58% | 96,68% |
| Aces y dobles faltas del ganador | 98,33% | 99,23% |

Estos campos son datos reportados por la fuente; no acreditan que estuvieran publicados antes de cada partido. La fecha semanal no permite medir con exactitud minutos en los últimos 7 días, descanso diario o viajes. No se tratará el indoor desconocido de WTA como pista al aire libre.

## Prueba de conexión de cuotas

Se reprodujeron dos snapshots archivados con 288 cotizaciones: 284 obtuvieron probabilidades y cuatro ofertas lay quedaron pendientes. Se incluyen ocho tipos observados; siete están conectados al modelo. Todas las ofertas siguen marcadas como no ejecutables y vencidas para uso actual. Esta reproducción fue calculada después de archivar las cuotas y no se presenta como pronóstico emitido a aquella hora ni como rentabilidad.

El ganador utiliza el híbrido; los demás mercados utilizan Markov MAP sin calibración adicional. Por ello no se puede sumar su supuesta ventaja ni construir una cartera como si todas las probabilidades pertenecieran a la misma distribución conjunta calibrada.

## Lo que se necesita ahora

1. **Agenda/estado con IDs y horas:** probar una fuente independiente con la cuenta del titular. Live Tennis API documenta `/fixtures`, `/matches` y marcadores en FREE; aún no tenemos una prueba autenticada de calidad y cobertura. También se pueden archivar fuentes oficiales ATP/WTA; el motor exige su evidencia reciente.
2. **Tiempos reales y sedes:** necesarios para fatiga diaria, descanso, desplazamientos y clima. Las coordenadas del torneo aproximan viajes entre sedes, no itinerarios personales. Las lesiones necesitan noticias o registros oficiales fechados; rumores o diagnósticos emocionales no son variables válidas.
3. **Cuotas observadas antes de los resultados y cierres:** permiten comparar mercado, CLV y economía con las reglas de cada casa. The Odds API publica cobertura de Grand Slams, ATP/WTA 1000/500; no garantiza Challenger/ITF ni todos los mercados. La selección dinámica de casa trabaja dentro de la cobertura efectivamente recibida.
4. **Resultados futuros y protocolo congelado:** reservar un periodo continuo y comparar híbrido, Elo calibrado y mercado sin margen; publicar cobertura, retiros, calibración, Brier/log-loss e incertidumbre por bloques. Un objetivo de 500 partidos por circuito es de planificación, no garantía de potencia estadística ni de rentabilidad. No se reajusta el modelo con los resultados de ese periodo para luego llamarlo test intacto.

## Repositorios comprobados y su utilidad

- [Tennismylife/TML-Database](https://github.com/Tennismylife/TML-Database): fuente e historial de cambios de la base; ya se usó su distribución de CSV. No hace falta otra descarga masiva igual.
- [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject): útil para estudiar estilos, puntos y presión con cobertura selectiva. Los 43 archivos ya están archivados. Su licencia CC BY-NC-SA requiere separar investigación de uso comercial.
- [gmalbert/tennis-predictions](https://github.com/gmalbert/tennis-predictions): referencia de ingesta, caché y Streamlit. No sustituye nuestra capa probabilística ni su validación. GitHub declara GPL-3.0 aunque su README afirma código permisivo; no se copió código suyo.
- [SDK oficial Live Tennis API en GitLab](https://gitlab.com/livetennisapi/livetennisapi-python): candidato a completar calendario/estado. La URL GitHub propuesta inicialmente no es el enlace oficial documentado. Sus planes y endpoints están en la [documentación del proveedor](https://docs.livetennisapi.com/llms.txt).

Fuentes de cobertura y liquidación: [The Odds API tenis](https://the-odds-api.com/sports/tennis-odds.html), [Pinnacle ante retiros](https://support.pinnacle.com/hc/en-us/articles/46732820954385-How-does-Pinnacle-grade-tennis-matches-in-the-event-of-retirement-or-disqualification).

## Evidencia reproducible

- `data/tennis/audit_20261017_v2/audit.json`: auditoría final de originales, canonical, modelos, recibos y anomalías. La v1 se conserva como primera pasada.
- `data/tennis/audit_20261017_v2/audit.html`: informe local filtrable.
- `data/tennis/audit_20261017_v1/market_replay.json`: reproducción de las 288 cotizaciones.
- `data/tennis/audit_20261017_v1/normalization_comparison.json`: igualdad de datos deportivos y cambios de trazabilidad.
- `data/tennis/audit_20261017_v1/canonical_v2/context_coverage.json`: cobertura de contexto por circuito.

Pruebas específicas tras integrar los cambios en el worktree: **41 aprobadas**. El arnés general inicial y final aprobó **1.300 pruebas**, omitió **88** y produjo dos avisos. La ejecución final duró 137,36 segundos. Docker no está disponible; su comprobación se omitió. Ningún servicio se considera promovido por el simple hecho de que pasen las pruebas del programa.
