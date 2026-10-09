# NBA: pendientes resueltos y cierre programado — RUN066

Se conservan los registros RUN065 y sus 15 unidades únicas, 21 versiones y dos
entradas hipotéticas. Esta sesión resuelve el enlace oficial y ejecuta una
prueba del seguimiento sobre esa misma cohorte. No se reciben todavía
resultados futuros ni se habilitan apuestas. No se añaden copias periódicas.

## Partidos verificados

Tres páginas NBA recibidas con HTTP200 prueban IDs, equipos y hora exactamente
iguales a los del proveedor. La evidencia se incorpora después del sello de
las predicciones; no se presenta como información conocida en aquel momento.

| Partido | ID NBA | Inicio, Ciudad de México, 20/10/2026 | Revisión previa |
|---|---|---|---|
| Boston en Detroit | 0022600001 | 13:00 | 12:58 |
| Philadelphia en New York | 0022600002 | 17:00 | 16:58 |
| Oklahoma City en San Antonio | 0022600003 | 19:30 | 19:28 |

Fuentes oficiales: [Boston–Detroit](https://www.nba.com/game/bos-vs-det-0022600001),
[Philadelphia–New York](https://www.nba.com/game/phi-vs-nyk-0022600002) y
[Oklahoma City–San Antonio](https://www.nba.com/game/okc-vs-sas-0022600003).
Las convocatorias actuales están vacías; no acreditan disponibilidad.

## Seguimiento activado

La automatización `cierre-del-piloto-nba-octubre-20-y-21` continúa este chat
únicamente el 20 y 21 de octubre y termina antes del plazo del 22/10 a las
12:00 UTC. Ejecuta el trabajador probado, sin modificar código, con un diario
de tareas inmutable y carpetas nuevas por ejecución. Cada tarea se reclama
antes de consultar: una caída o respuesta incierta no inicia un reintento.
El máximo es tres tareas de red por ejecución; las restantes quedan sin
reclamar hasta una ejecución siguiente en su ventana. Los avisos se reservan
a resultados, fallos relevantes o acciones necesarias.

Es una automatización local: requiere este equipo encendido y Codex abierto.
La ejecución puntual y la respuesta de las fuentes no están garantizadas.
Si se pierde una ventana, queda registrada como perdida y no se reconstruye
su recepción retroactivamente. El primer ensayo real de `paper-advance`
verificó el plan y devolvió cero tareas debidas y cero consultas de pago.

Cada partido tiene una observación NBA en los dos minutos anteriores al
inicio. `Available` explícito se registra como observado; `Out` o inactivo
explícitos se conservan. Estar en una plantilla, `Active`, un estado ausente
o no aparecer en lesiones no prueba salud. Una observación previa no garantiza
participación futura. El resultado final permite distinguir participación y
DNP, pero no convierte retroactivamente en disponible a un jugador.

Las dos entradas Sportsbet del primer partido tienen una sola consulta nueva
de cierre, limitada a dos mercados y **dos créditos totales futuros**. La
sesión actual consumió cero créditos y tres consultas públicas gratuitas.
El presupuesto acotado es adicional a las consultas ya documentadas en RUN065;
no se compra un plan ni se amplía la fuente. Un cierre sólo es comparable si
coinciden casa, partido, jugador, mercado y línea, se recibió en los últimos
cinco minutos y su fuente y recepción tienen como máximo 60 segundos al
compararlo. Una línea cambiada queda sin CLV comparable. Esta captura es una
referencia cercana al inicio, no una garantía de la última cotización.

Se reciben boxscores NBA a las cuatro, seis, doce y veinticuatro horas después
del inicio, únicamente en ventanas fijadas de dos horas y hasta obtener el
primer final válido por evento. Se verifican ID, equipos, hora, finalización,
jugadores y sumas de estadísticas. La evaluación usa los archivos originales;
el resumen rechaza versiones duplicadas. Los fallos quedan como evidencia y
no como resultados. El diario vivo queda fuera de los hashes fijos del registro
maestro; cada ejecución produce evidencia nueva que se puede registrar aparte.

## Lectura y criterios

`reading_protocol.json` congela la lectura descriptiva antes de los resultados:
CRPS candidato menos baseline por mercado, con NLL, MAE, cobertura al 80%,
Brier, faltantes y DNP separados. Las tres observaciones de partido son
dependientes; las 15 unidades no se presentan como 15 partidos independientes.
Las ganancias son hipotéticas. El CLV muestra por separado la razón entre
precio de entrada y cierre y una referencia sin margen proporcional a ambos
lados; no acredita reglas de una cuenta ni rentabilidad comercial.

También queda preparado un borrador para una confirmación futura de rebotes:
efecto mínimo de 0,05 CRPS, alfa unilateral 0,025, potencia objetivo 80%,
mínimo 112 días de partido y 300 partidos distintos. La varianza de planificación
usa exclusivamente entrenamiento 2022–23: 145 días y 1087 partidos, con el
máximo entre varianza diaria y ajuste Bartlett de 14 retardos. Es una estimación
de planificación con un modelo histórico de referencia, no una prueba de
potencia efectiva del piloto actual. Antes de abrir otra confirmación faltan
fijar candidato y exposición exactos, calendario, revisión externa y requisitos
de cobertura. No se abre F7 confirmatoria ni se promueve G7 por este borrador.

## Qué sigue dependiendo de evidencia nueva

- Convocatorias y estados próximos al inicio; pueden permanecer desconocidos.
- Cuotas comparables de cierre y resultados oficiales de estos tres partidos.
- Una confirmación científica separada que cumpla los requisitos del plan.
- Reglas de una cuenta y jurisdicción concretas antes de operar comercialmente.
- Recepción histórica original: sin tickets o archivos contemporáneos sigue
  sin acreditarse; descargar hoy un histórico no crea aquel recibo.

Estos puntos tienen controles y condiciones de cierre, pero no se declaran
obtenidos antes de que exista la evidencia. Los requisitos comerciales del
plan maestro permanecen separados del seguimiento exploratorio.
