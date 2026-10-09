# NBA: MVP, ejecución y capacidad de distribución

Fecha: 3 de octubre de 2026. Estado: revisión de la sugerencia del usuario; diseño, sin implementación ni rentabilidad demostrada.

La secuencia de trabajo y cierre de fases se consolida en el [plan maestro auditable F0–F9](nba_plan_fases_auditable.md). Esta revisión conserva el fundamento operativo y comercial.

La sugerencia mejora el enfoque operativo: el producto solo ofrece utilidad si sus clientes pueden tomar el contrato y precio recomendados. Sus cifras concretas de límites y reacción no se aceptan como hechos sin medición. La prioridad de props sigue siendo una hipótesis de investigación, no evidencia de que sea el mercado más fácil de batir.

## 1. Qué está respaldado y qué falta verificar

| Afirmación | Evaluación |
|---|---|
| The Odds API actualiza props cada 60 s | El proveedor publica 60 s para props, alternativos y periodos, antes y durante el partido. Es cadencia del proveedor, no retraso fijo de cada noticia ni garantía de ejecución. [Documentación](https://the-odds-api.com/sports-odds-data/update-intervals.html). |
| Límites entre USD 20 y 250 y cambio de línea en menos de 45 s con 50–100 clientes | Riesgo de capacidad plausible, pero rangos no corroborados por las fuentes primarias revisadas. Separar stake máximo por cuenta, volumen agregado, exposición del operador y velocidad de cambio. Un feed de cuotas no revela automáticamente esos límites. |
| Ganar y batir cierre implica limitar cualquier cuenta a céntimos en semanas | Excesivamente categórico. Las restricciones son un riesgo documentable; no encontramos una regla universal de plazo, importe o causa. Caliente permite rechazar apuestas y restringir niveles de apuesta; eso no cuantifica la probabilidad de limitar a un cliente. [Reglas generales](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/apuestas-generales/). |
| Casas suspenden en 5–30 s y secundarios permanecen 2–5 min | Hipótesis no respaldada por un benchmark verificable en esta revisión. Puede haber ajustes conjuntos, anticipación de noticias, suspensiones o ausencia de oferta. E7/E17 deben medir ventana y cobertura, incluyendo los casos sin oportunidad. |
| Cuota mínima, contrato exacto y varias casas | Recomendación pertinente. Cada oferta debe ser contemporánea, accesible y tener reglas compatibles. El ejemplo 1,83 del plan no es un mínimo fijo de todas las señales. |
| Ejecutar 27 experimentos antes del inicio | No es el objetivo del plan: son un backlog científico. Reducir el MVP es razonable; la validación económica prospectiva necesitará más tiempo que la fecha de apertura. |

La NBA confirma inicio regular el **20 de octubre de 2026**. Quedan 17 días desde esta revisión; la meta propuesta es captura y sombra para esa fecha, condicionada a disponibilidad técnica. No garantiza picks rentables desde el primer día. [Calendario oficial](https://www.nba.com/news/2026-27-nba-regular-season-schedule).

## 2. Reglas y precio: cambios necesarios

La cuota mínima depende de la probabilidad del contrato y del margen objetivo:

```text
o_min = (1 − p_devolución + τ) / p_ganar
```

Las probabilidades son de categorías disjuntas del pago real; `τ` es un umbral de EV propuesto. Estimar incertidumbre y seleccionar el umbral fuera del test. Cambiar over 7,5 a over 8,5 cambia el contrato: recalcular la distribución y emitir una nueva decisión sellada; no trasladar la cuota mínima anterior. La alerta original conserva su historial y puede quedar invalidada.

Diversificar operadores puede ampliar disponibilidad, pero las casas pueden copiar una fuente común. No contar cotizaciones clonadas como fuentes independientes ni suponer que multiplicar casas multiplica capacidad. Registrar precio, timestamp, jurisdicción, línea, periodo, overtime, DNP, push, lesión y condición promocional por oferta.

Un detalle importante: una protección por lesión puede ofrecer un bono, no devolver efectivo. La descripción oficial de bet365 en EE. UU. distingue Bonus Bets para ciertos sencillos; no extrapolar ese producto a México ni asignarle valor de efectivo igual al stake. [Descripción del operador](https://news.bet365.com/en-us/article/does-bet365-have-injury-protection-for-the-nba-nhl-nfl-season/2025102320535837744).

Caliente exige participación del jugador en sus props y diferencia contratos que incluyen prórroga de cuartos que la excluyen. Estas reglas consultadas no bastan para declarar una protección universal si juega 12 segundos y se lesiona. Archivar las condiciones exactas de la oferta y su vigencia. [Reglas de básquetbol](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/basquetbol/).

Además, sus reglas generales contienen cláusulas sobre selecciones repetidas, grupos y colusión. Revisar su alcance en el producto de distribución; no concluir automáticamente que todos los suscriptores independientes forman un sindicato ni que esa cláusula se aplicará a todos. No confundir dispersar ofertas entre operadores con una garantía contractual.

## 3. Noticias y beneficiarios secundarios: experimento, no ventaja asumida

Precalcular escenarios es útil porque reduce tiempo de cálculo y hace explícitas las hipótesis. Una baja puede cambiar minutos, uso, selección de tiro y oportunidades de todos los compañeros, pero el supuesto beneficiario puede heredar minutos de otra posición, peores quintetos o menor eficiencia.

Extender **E7/E8**, conservando el mismo universo de anuncios:

- Jugador ausente, sustituto directo y compañeros secundarios, definidos por rol previo y escenarios anteriores a la noticia; no escoger beneficiarios después de observar su rendimiento.
- Modelo congelado, actualización solo de minutos y actualización de minutos más tasas/rol.
- Ofertas observadas desde primera recepción de la noticia; duración, suspensión, movimiento y retorno posterior. Incluir noticias sin cambio y cambios horarios placebo.
- Evitar fuga: conservar primera publicación/recepción, estado disponible y revisiones; una página final de lesiones no reconstruye su historia.

Con snapshots cada 60 s, los cambios se conocen entre observaciones. No afirmar suspensión en 18 s o duración de 45 s con esa resolución; declarar intervalo de incertidumbre. Consultar cada segundo una fuente que actualiza cada minuto no crea datos nuevos ni independencia. Un feed más rápido se justifica solo tras medir coste y supervivencia de oportunidades.

El tiempo de recepción de noticias y el de cuotas son procesos separados. Una noticia reciente no vuelve reciente un precio antiguo. Revalidar después de recibir la noticia; si falta observación suficiente de disponibilidad, registrar la oferta como incierta y abstenerse según la política.

## 4. MVP revisado y prioridades

Mantener la aplicación aislada descrita en `nba_arquitectura_aislada.md`. Empezar con **una familia de props prepartido** escogida por cobertura; inicialmente 2–3 operadores con acceso real y reglas verificadas. Estos números son límites de alcance propuestos, no una prueba de capacidad.

| Paso | Entregable mínimo | Experimentos asociados |
|---|---|---|
| 1 | Captura versionada, identidad y contrato/pago correctos, presupuesto independiente | E0 y E18 desde el comienzo |
| 2 | Distribución de minutos y tasa productiva encogida; distribución liquidable de la prop | E1 y versión básica de E8 |
| 3 | Comparación temporal y calibración de probabilidades, referencia contemporánea de mercado y selección con abstención | Parte mínima E22/E23; E18 permanente |
| 4 | Disponibilidad, demora y cuota aprovechable por operador y reacción del cliente | E5 y parte básica E17 |
| 5 | Escenarios de baja y redistribución precalculados si la noticia aporta información incremental | E7/E8; después de contar con el núcleo anterior |
| 6 | Sellado, outbox durable, revalidación, caducidad y resiliencia; piloto de pruebas | Parte indispensable de E19 |

No evaluar solo minutos: aproximadamente `media_prop = minutos × tasa_por_minuto`, pero la probabilidad de superar una línea necesita también dispersión y dependencias. Una buena estimación de minutos con una tasa o cola incorrecta puede producir una mala apuesta.

Tampoco exigir «minutos implícitos del mercado» como verdad observable: una línea de prop mezcla minutos, tasa, distribución y precio. La descomposición no es identificable a partir de esa línea por sí sola. Comparar minutos con baselines observables y después evaluar la distribución completa frente al mercado. Mejorar minutos es valioso, pero no es condición matemática necesaria ni suficiente de rentabilidad.

E18 no es una comprobación única después de E1: los guards point-in-time acompañan todos los pasos. La forma mínima de E22 y E19 permanece en el MVP porque precio justo y entrega válida son parte del producto, no extras de investigación.

E15/E20 y challengers complejos quedan diferidos. E24 puede esperar cobertura e historial. Reabrirlos por una necesidad medida —interacciones residuales o cambio de régimen—, no exclusivamente por llegar al verano. Las versiones completas de los 27 experimentos siguen en el backlog; no se ejecutan todos para arrancar captura.

## 5. Cómo medir un producto de picks sostenible

Extender **E5/E19** con una evaluación de capacidad de distribución:

1. Disponibilidad del mismo contrato a cuota suficiente tras demoras realistas, medidas o simuladas e identificadas como tales.
2. Proporción de alertas con oferta accesible por casa; rechazos, cambios y suspensiones separados.
3. Cuota y stake realmente aceptados cuando el usuario los confirme voluntariamente; envío o lectura de Telegram no equivalen a aceptación de la casa.
4. Retorno del historial editorial frente al retorno de ejecuciones confirmadas, separados y con tasa de datos faltantes. La participación voluntaria puede sesgar esa muestra.
5. Límites observados por cuenta/contrato cuando se informen; no pedir credenciales de clientes ni inferirlos de un snapshot.

Como planificación, para ejecuciones `i` de un cliente `c`:

```text
beneficio esperado neto_c
  = Σ_i stake_aceptado_i · EV_estimado_i(precio y contrato aceptados)
    − precio_suscripción − costes_adicionales
```

Es expectativa bajo el modelo, no beneficio garantizado. Debe incluir incertidumbre y sesgo de selección de clientes que reportan. En un ejemplo propio, volumen mensual de MXN 5.000 con ROI neto de apuestas del 2% implica MXN 100 esperados; una suscripción de MXN 300 dejaría −MXN 200 antes de otros costes. No recomendar elevar stakes para compensar la tarifa; comprobar que el producto ofrece utilidad a su público real.

No abrir 100 plazas por asumir que 100 alertas equivalen a 100 ejecuciones. La capacidad comercial se estima con datos del piloto, margen de seguridad y seguimiento continuo. No existen aún observaciones para fijar un cupo sostenible. Un replay sin apuestas puede estimar disponibilidad histórica; no estima el impacto adicional de los suscriptores sobre los precios. Correlación entre envío y movimiento tampoco identifica causalidad: otras noticias y apostadores actúan al mismo tiempo.

## 6. Continuar, reformular o detener

- **Continuar captura/sombra:** cobertura, contratos y trazabilidad suficientes; se pueden medir resultados sin depender de precios inventados.
- **Reformular mercado/ventana:** mejora predictiva que desaparece con retraso, disponibilidad insuficiente o margen que no cubre tarifa/costes del cliente objetivo. Probar ventanas más largas o mercados más amplios sin presuponer que son rentables.
- **Detener ese candidato:** fugas, reglas no verificables, mejora que no replica o retorno dependiente de pocas observaciones no accesibles. Conservar el resultado negativo.
- **Promoción comercial:** evidencia prospectiva, calibración, ejecución, capacidad y utilidad económica bajo política preregistrada. Mantener las puertas NBA; apertura de temporada y unas victorias no sustituyen esa evidencia.

No se implementó NBA, activó Telegram, gastaron créditos ni se realizaron apuestas o pruebas de presión del mercado. Esta revisión integra la crítica operativa y mantiene separados fútbol y NBA.
