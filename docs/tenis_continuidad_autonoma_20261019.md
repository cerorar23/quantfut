# Continuidad autónoma de la validación predictiva

19 de octubre de 2026. Seguimiento **ACTIVO** en este mismo chat. Automatización: `continuidad-de-validaci-n-predictiva-de-tenis`. Comprueba avances cada dos horas y captura datos como máximo cada cuatro horas. Se verificaron el estado activo, la frecuencia y el identificador del chat en la configuración de la aplicación.

La tarea continuará sin confirmaciones rutinarias. Informará de pronósticos nuevos, resultados evaluables, cambios materiales de calidad/cobertura o fallos que necesiten atención. No repetirá avisos idénticos ni declarará rentabilidad o certeza sin evidencia. Las ejecuciones locales necesitan el equipo encendido, la aplicación abierta y acceso a los archivos y servicios. [Documentación oficial de tareas programadas](https://learn.chatgpt.com/docs/automations?surface=app).

## Primera pasada ejecutada

- Dos consultas reales a API-Tennis, cuatro programas oficiales archivados y revisados visualmente.
-112 eventos observados:50 programados sin verificar físicamente,49 finalizados,5 cancelados,5 retiros y3 en juego. Los partidos anteriores no se cuentan como resultados del nuevo estudio.
-29 parejas individuales distintas revisadas; **18 pronósticos sellados:11 ATP y7 WTA**. Once exclusiones después de corregir dos rectángulos y una abreviatura de iniciales. Las correcciones no se contabilizan como partidos adicionales.
-Cero resultados confirmatorios y cero apuestas. No se consumieron créditos de The Odds API.
-Una segunda invocación del capturador comprobó la espera de cuatro horas: cero consultas nuevas.

La lista legible está en `data/tennis/continuous_quality_20261019/PRIMEROS_PRONOSTICOS.md`; sus horarios son estimaciones convertidas aCiudad de México. Los primeros encuentros están previstos para esta noche local, aunque su fecha del torneo/UTC sea20 de octubre. No se confunden con horas físicas.

Se rechazó expresamente Boulter–Sakatsume: el programa muestra un marcador parcial yTBF, por lo que es una reanudación, no un encuentro nuevo. La fuente actual de Ningbo acredita Bejlek–Parks para el20 de octubre, compatible con el calendario actualizado. La oferta antigua frente a Xiyu Wang se conserva como archivo, pero no se admite para ese encuentro. `schedule_reconciliation.json` conserva la evidencia.

## Límites y registros

Configuración operativa: `data/tennis/continuous_quality_20261019/config.json`. Módulo: `tennis_continuous_v1`, separado de los candidatos congelados.

El capturador usa un único registro compartido de ciclos y el mismo registroAPI-Tennis. La reserva del ciclo es atómica y dura al menos cuatro horas, incluso si falla una petición. No se borran reservas ni se cambian carpetas para repetir consultas. El máximo es **12 intentosAPI-Tennis por díaUTC**; es un límite local, no la confirmación de la cuota contratada del proveedor. Un401, 403 o 429 detiene la segunda consulta del ciclo y activa espera de 24 horas. Las claves se leen del archivo local dedicado y nunca se imprimen ni se guardan en informes. Las respuestas que contengan accidentalmente la clave se redactan antes de archivarse.

La configuración autoriza **cero créditos de The Odds API**. Sus pruebas anteriores se agotaron y la reserva compartida sigue vigente. No hay endpoints de apuestas ni publicación de picks. No se envían nuevos contenidos o huellas a terceros durante cada ciclo por el mero hecho de estar programado.

## Procedimiento de cada ejecución

1. Leer esta guía y los informes recientes. Para cambios de código, respetar primero CLAUDE.md y sus comprobaciones. No repetir todas las pruebas en una pasada que solo consulta datos e incorpora archivos nuevos.
2. Verificar el protocolo y utilizar el capturador. Si responde que aún no corresponde o que el proveedor está en espera, no forzarlo; continuar el trabajo independiente de revisión, resultados o identidades.
3. Si hay documentos nuevos, aplicar la habilidad PDF: renderizar, revisar visualmente parejas, fecha, pista y hora mínima, y generar un archivo nuevo de celdas revisadas. Si los bytes del programa son idénticos, pueden reutilizarse las celdas acreditadas, vinculándolas a un recibo fresco y verificando de nuevo fecha/pareja/vigencia.
4. Compilar las revisiones con `emit`. Se exigen oposición exacta dentro de una celda, fecha del programa, calendario reciente, nombres y parámetros entrenados inequívocos. El tiempo estimado del proveedor no puede anteceder la cota oficial. No se admiten reanudaciones. Si la hora mínima oficial ya pasó, hace falta otra fuente oficial de estado en vivo; el calendario programado no basta. No inventar dicha fuente ni marcarla como verificada.
5. Conservar las exclusiones y la cobertura. Ampliar fuentes de torneos únicamente con enlaces oficiales y metadatos contrastados, creando versiones de configuración. Los cuatro adaptadores iniciales no equivalen a cobertura universal del circuito. No resolver una abreviatura por una coincidencia difusa; los guiones e iniciales compuestas se comparan de forma determinista y deben conservar todos los componentes del nombre.
6. Buscar resultados de eventos ya pronosticados y preservar fuentes originales. Guardar observaciones terminales todavía inadmisibles en una carpeta separada. **No usar como horas físicas las horas programadas, la recepción local ni una duración estimada.** El contrato congelado requiere evidencia temporal adecuada: si no existe, el resultado queda pendiente de evaluación.
7. Preparar listas nuevas de resultados admitidos, por ejemplo en `results/accepted_FECHA_ID.json`, y evaluar con ese archivo. No sobrescribir `future_results.json`, los informes previos o los sellos: la lista inicial vacía forma parte de una entrega histórica. Conservar todas las pérdidas y exclusiones; no seleccionar resultados por conveniencia.
8. Generar un informe nuevo y un resumen legible que interprete la evidencia disponible. Informar solo si existe un cambio significativo. Al concluir el periodo, no añadir eventos fuera de él; completar resultados pendientes, evaluar honestamente y detener el seguimiento al cerrar la revisión final.

El agente puede investigar autónomamente puentes de identidad con fuentes primarias y preparar versiones experimentales nuevas. No puede fusionar los 52 grupos en cuarentena por nombre, reentrenar el candidato congelado con esta muestra ni activar una variante porque resulte favorable en los datos de evaluación.

## Comandos operativos

Utilizar el intérprete del proyecto y el motor aislado como directorio de módulos:

```powershell
$env:PYTHONPATH='C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis'
& .venv/Scripts/python.exe -m tennis_continuous_v1 capture --config data/tennis/continuous_quality_20261019/config.json
& .venv/Scripts/python.exe -m tennis_continuous_v1 emit --config RUTA_CONFIG --reviews RUTA_REVISION_NUEVA --output RUTA_INFORME_NUEVO
& .venv/Scripts/python.exe -m tennis_quality_v3 evaluate --protocol RUTA_PROTOCOLO --predictions-root RUTA_PRONOSTICOS --results RUTA_RESULTADOS_ADMITIDOS --output RUTA_INFORME_NUEVO
```

Ciclo inicial: `cycles/9f9f8c1bea124f0696b12fa5e1e06be9/`. Incluye recibos, programas,29revisiones iniciales y dos adendas explícitas. El módulo crea18registros del protocolo existente en `data/tennis/predictive_quality_v3_20261019_v3/future_predictions/`; cada uno conserva las seis variantes, las fuentes y su hora de sello local.

Los sellos DigiCert anteriores acreditan sus protocolos, no estos pronósticos posteriores. No se modificaron los37 módulos originales, los12 artefactos previos, los cuatro módulos de calidad ni los criterios sellados. Mantener una automatización activa no garantiza disponibilidad continua del proveedor ni acredita por anticipado los futuros resultados.

## Ampliación autorizada: diez mercados

Desde el19-oct se añade el estudio independiente descrito en docs/tenis_validacion_todos_mercados_20261019.md. Después de emitir/revisar ganadores, ejecutar tennis_allmarkets_v1 seal sobre todos los padres y guardar un informe nuevo. Al incorporar resultados admitidos, ejecutar también tennis_allmarkets_v1 evaluate, conservando listas e informes anteriores. Protocolo data/tennis/all_markets_prospective_20261019/protocol.json, registros predictions/ de esa raíz. Primera emisión18partidos/990tareas/110grupos, cero resultados. No modificar los cuatro módulos nuevos ni tennis_markets_v2 congelados; las líneas del mismo partido no son observaciones independientes. La fecha nueva de emisión nunca se retrodata al ganador. No hay sello externo nuevo ni acreditación de calidad/rentabilidad. Automatización existente actualizada y verificada activa, con los mismos límites y reglas de silencio.

## Incorporación automática de resultados

Desde el19-oct, ejecutar también tennis_evidence_v1 reconcile como indica docs/tenis_resultados_y_evidencia_20261019.md. Genera listas nuevas de resultados y ambos informes sin tocar protocolos congelados. Fuente temporal real y pareja vinculadas a campos nativos; no imputa horas. La primera revisión18:35UTC encontró18partidos aún futuros, primer inicio estimado22:15México,0terminalesdeellos y59terminalesajenos. Histórico legible separado2788partidos/39grupos/diezfamilias. La auditoría financiera conserva0órdenes: el seguimiento predictivo no activa por sí solo una prueba de ROI. No afirmar rentabilidad en marcha, ni ampliar permisos de cuotas. Automatización existente actualizada con estas instrucciones.
