# Tenis: primera fase de evaluación común y carga observable

Fecha: 17 de octubre de 2026. Estado: implementación experimental probada, sin promoción de modelo. El checkout de tenis sigue separado del motor de fútbol.

## Evaluación de la propuesta

Trabajar por fases facilita verificar contratos y resultados. No es cierto que una tarea grande necesariamente produzca funciones simuladas o fugas temporales. Un prompt es una especificación inicial; no sustituye inspección del repositorio, pruebas ni evidencia empírica.

Correcciones adoptadas:

- Corte en la hora de decisión, además de comprobar que el pronóstico preceda al inicio. El resultado anterior y sus estadísticas deben estar disponibles estrictamente antes de la decisión; un resultado antiguo descargado hoy no acredita disponibilidad en el pasado.
- Ventanas [decisión − días, decisión). El ancla se documenta: no se desplaza con cambios posteriores del horario del partido.
- Muestra común por caso (evento/fase/decisión) y orientación de participantes. Se informa denominador total y elegibles terminados. Retiros y walkovers quedan en cobertura, fuera del contrato de probabilidad de partido terminado.
- ECE usa diez intervalos de anchura igual, incluyendo p=1 en el último. Es una descripción dependiente de la muestra, no una garantía de calibración ni una prueba suficiente para seleccionar modelo.
- El ajuste de carga usa un offset en log-odds del modelo actual y diferencias entre jugadores. No suma puntos Elo directamente a log-odds. Normalización y ajuste se calculan exclusivamente con entrenamiento anterior.
- Todos los resultados nuevos son experimentales. No se modificó el protocolo prospectivo congelado ni se utilizó 2026 como prueba final nueva.

## Implementación

Archivos en `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/`:

- `tennis_engine/benchmark.py`: contratos tipados, BenchmarkEvaluator, log-loss, Brier, ECE y diez intervalos de calibración. Rechaza duplicados, probabilidades inválidas, participantes invertidos y decisiones que no preceden al inicio real. Sin muestra común devuelve métricas nulas.
- `tennis_engine/recent_load.py`: RecentLoadExtractor para puntos/juegos/sets de tres y siete días y set decisivo de cinco días. Revisa disponibilidad, versiones por evento y exclusión del propio objetivo. Conserva contadores desconocidos y ambigüedad temporal; no equipara ausencia de datos a carga cero. Incluye normalizador de respuestas archivadas de API-Tennis con comprobación SHA-256.
- `tennis_engine/load_runner.py`: ModelRunner conectado mediante una función al modelo actual; LoadCorrection implementa un ajuste logístico ridge real, sin intercepto y con escala RMS del entrenamiento para conservar simetría. Recalcula las variables de cada fila de entrenamiento a su propia hora de decisión y exige etiquetas recibidas antes del ajuste. Impide reutilizar eventos de entrenamiento como objetivos de prueba. No contiene probabilidades simuladas ni ajuste inventado por falta de datos.
- `scripts/phase1_load.py`: ejecución sin red sobre los dos encuentros revisados y la captura autenticada anterior. Usa hybrid_forecast del modelo actual. Los cuatro enlaces de jugadores del ejemplo se restringen a esas parejas revisadas; no escriben alias automáticos en el registro.
- `tests/test_benchmark_load.py`: 24 pruebas nuevas, incluyendo fronteras de ventana, recepción tardía, actualizaciones, duplicados, retiro/WO, datos faltantes, probabilidades 0/1, cálculo analítico de métricas y simetría al intercambiar jugadores. Las muestras artificiales se usan solo para verificar código, no para afirmar mejora predictiva.

Los contratos de entrada son una frontera de confianza: los conectores deben verificar fuente y procedencia de resultados, probabilidades base y horas antes de construirlos. Estos objetos no reemplazan la verificación de recibos del flujo prospectivo existente. El normalizador incluido sí verifica el hash de la captura de API-Tennis. No se activó una publicación o tarea recurrente.

## Prueba real y resultado

Original usado: `.local/api_tennis_probe/20261017T211250Z/`, con su manifiesto de consultas y hashes. No se hicieron solicitudes nuevas a proveedores ni se consumieron créditos de The Odds API.

Se normalizaron 104 observaciones de individuales ATP/WTA/Challenger: 96 terminados, siete retirados y un walkover. La recepción del estado terminado da un límite superior de finalización. La fecha programada no demuestra un límite inferior del inicio o final reales, por lo que el normalizador deja ese límite desconocido. Los contadores presentes no se asignan artificialmente a ventanas exactas. Partidos al mejor de cinco, marcadores no estándar o incompletos no se convierten por suposición en sets/juegos completos; los puntos pueden usarse si existen ambos denominadores de saque del partido.

Se ejecutó el modelo híbrido actual sobre Davidovich Fokina/Jodar y Chwalinska/Kartal, con calendario e identidades contrastados en la fase anterior. Resultado:

| Indicador | Resultado |
|---|---:|
| Pronósticos del modelo actual | 2 |
| Ajuste de carga entrenado con datos temporalmente válidos | No |
| Predicciones de la variante con carga | 0, abstención explícita |
| Resultados futuros disponibles para esos encuentros | 0 |
| Muestra común evaluable | 0 |
| Log-loss, Brier y ECE comparativos | No disponibles |

Esto demuestra conexión y funcionamiento de controles, no superioridad de la carga. La variante no copia la probabilidad base para aparentar una comparación completa. Los mínimos de entrenamiento y la penalización son parámetros explícitos; el mínimo operativo de 20 filas no es una garantía de potencia estadística.

Informe reproducible: `data/tennis/load_phase1_20261017_v2/report.json`. Contiene fuentes, hashes del código, casos, probabilidades base, variables, abstenciones y cobertura. El primer ensayo también queda conservado en `load_phase1_20261017/`.

## Verificación y siguiente paso

Pasaron 75 pruebas específicas de tenis: 51 existentes y 24 nuevas. Los 12 hashes del protocolo futuro original siguen coincidiendo. El arnés general inicial pasó 1.300 pruebas y omitió 88 con dos avisos; esas pruebas generales no equivalen a 1.300 pruebas del modelo de tenis. Docker no está disponible en este entorno.

Para entrenar y comparar la variante hacen falta observaciones históricas con límites temporales suficientes y disponibilidad acreditada, o acumularlas prospectivamente. El siguiente trabajo es conectar la captura periódica de estados/resultados con recibos, conservando incertidumbre por frecuencia de consulta y latencia del proveedor. Cuando la muestra permita ajustar, se congelará ese candidato antes de su prueba futura. Weighted Elo, viajes, clima, selección de hiperparámetros y ablaciones adicionales quedan para sus fases respectivas.

Verificacion general final: 1.300 aprobadas, 88 omitidas y dos avisos en 226,35 s; arnes correcto. Docker omitido por ausencia del programa. Hashes del codigo entregado coinciden con el informe ejecutado; cero apariciones de la clave en los nuevos entregables.
