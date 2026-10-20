# Comparacion espacial: implementacion, sensibilidad y ejecucion real

18 de octubre de 2026. Investigacion experimental; no modifica probabilidades publicadas ni los doce artefactos congelados.

## Que se implemento

El checkout aislado de tenis incorpora `tennis_engine/spatial_experiment.py`. `SpatialExperiment.run` recibe filas de entrenamiento y prueba separadas, predicciones base prepartido y transiciones por jugador. Las exposiciones espaciales se calculan mediante el extractor ya auditado y las versiones de sede disponibles antes de cada decision. No basta con tener coordenadas conocidas hoy.

Compara tres familias:

1. Base: probabilidad prepartido suministrada por el modelo existente.
2. Base + espaciales: correccion logistica regularizada sobre diferencias A-B de distancia, cambio de altitud y cambio horario firmado.
3. Experimental: misma correccion espacial mas diferencia de intervalo salida-debut estimado bajo escenarios explicitamente declarados.

La rama espacial no imputa horas. Los datos originales, su precision y los valores desconocidos permanecen intactos. La rama experimental exige dias de partido/participacion verificados: una fecha de semana de torneo no sirve como fecha real de eliminacion. Los horarios conocidos y respaldados se conservan; solo se sustituyen los ausentes dentro de cada escenario.

Los nueve escenarios combinan cierres a las 12, 18 o 23 horas para cada jugador por separado, asignados segun el orden canonico de sus IDs para conservar simetria al intercambiar A y B. El debut hipotetico comun es a las 14 horas cuando su hora falta. Son pruebas de sensibilidad, no distribuciones empiricas de horarios. Aplicar un mismo desplazamiento horario a los dos jugadores puede cancelarse en una diferencia; por eso se perturban los cierres independientemente. El reloj de debut es compartido porque se trata del mismo encuentro. Se rechazan horas locales ambiguas o inexistentes por horario de verano.

## Entrenamiento y evaluacion

La escala RMS y los coeficientes ridge se ajustan exclusivamente con entrenamiento. No se centran las diferencias ni se incorpora intercepto, preservando la simetria de jugadores. La penalizacion 1,0 se declara de antemano; no se busca la mejor en prueba. El minimo operativo de 20 filas es una guarda numerica, no garantia de potencia estadistica.

Se rechazan eventos repetidos entre entrenamiento y prueba, etiquetas recibidas a partir del ajuste, decisiones de prueba previas al ajuste y evidencia futura o alterada. Se mantiene el contrato del evaluador comun de partidos completados y cronologia prepartido acreditada. Las tres familias y todos los escenarios se puntuan en la misma interseccion de casos, con cobertura, log-loss, Brier y ECE de diez intervalos. Se registran coeficientes, escalas, IDs, hashes de fuentes y del conjunto de entrenamiento. Se reporta todo el rango de escenarios, sin escoger uno utilizando resultados de prueba. Ese rango no es un intervalo de confianza.

## Resultado de la ejecucion sobre archivos reales

Artefactos finales: `data/tennis/spatial_trial_20261018_v3/protocol.json` y `report.json`. Las versiones anteriores conservan ejecuciones de auditoria durante el desarrollo; la v3 corresponde al codigo entregado.

| Familia | Entrenamiento comun apto | Prueba comun apta | Log-loss / Brier / ECE |
|---|---:|---:|---|
| Base, en esta comparacion | 0 | 0 | No calculados |
| Base + espaciales | 0 | 0 | No calculados |
| Experimental, nueve escenarios | 0 | 0 | No calculados |

El estado es `insufficient_common_training_or_test_sample`. No se entrenaron modelos nuevos ni se ejecutaron las metricas o sensibilidad sobre resultados reales. Los once ensayos automatizados del comparador usan datos sinteticos de prueba, sin atribuirles evidencia predictiva.

La auditoria encontro:

- El archivo historico contiene 492.251 partidos y su corte es el 16-oct-2026. La primera incorporacion de coordenadas al registro es posterior a ese corte. Ninguna fila de ese archivo puede utilizar esas versiones como informacion ya disponible en su decision historica. Un estudio con metadatos reconstruidos retrospectivamente requeriria un protocolo separado y no equivaldria a evidencia prospectiva.
- Los 228 encuentros tienen coordenadas y terreno de su sede, pero proceden de una captura de calendario recibida el 17-oct a las 21:12:56 UTC. El historial de estados archivado no contiene resultados completados de esos objetivos; no se descargaron resultados nuevos durante esta fase.
- La auditoria de participacion encontro historial candidato para 183/456 filas jugador-encuentro, pero cero transiciones completas verificadas. No se transformo ese historial candidato en afirmaciones de debut, viaje directo, salida tras dobles o descanso real.

La muestra comun real tiene cobertura 0/228. Este resultado describe elegibilidad de datos; no significa que el modelo base o las variables espaciales sean mejores o peores. Tampoco implica que falten los datos generales de tenis: falta su enlace temporal verificable para este experimento.

## Lo que falta para obtener resultados predictivos

Construir y revisar participaciones por jugador/edicion, cubrir clasificacion y dobles, acreditar cierre y debut, y acumular predicciones con las fuentes espaciales disponibles antes de decidir y sus resultados posteriores. Los dias verificados permiten los escenarios; las fechas semanales no se convierten en dias ni horas de partido. La rama espacial no exige inventar descanso para representar distancia, altitud o huso, pero la comparacion triple necesita una muestra comun elegible.

El holdout ya reservado del motor congelado no se reutiliza para elegir esta nueva variante. Despues de disponer de entrenamiento suficiente, una seleccion confirmatoria requiere otro periodo futuro intacto. Ningun escenario ni coeficiente fue seleccionado con etiquetas de prueba en esta ejecucion.

Cero consultas deportivas nuevas y cero creditos de The Odds API. Sin programador automatico, cambios de produccion ni apuestas.

## Verificacion

154 pruebas de tenis aprobadas sobre el codigo entregado, once nuevas del comparador. Comprueban escalado solo con entrenamiento, independencia respecto de etiquetas y covariables de prueba, muestra comun, fechas semanales, disponibilidad, simetria, horarios conocidos y conflictos de horario de verano. Los doce hashes del modelo congelado permanecen intactos.

Verificacion general final: 1.300 pruebas aprobadas, 88 omitidas y dos avisos en 139,58 segundos. Docker no disponible. Diffcheck del checkout de tenis correcto; codigo entregado, protocolo y reporte coinciden por hash.

