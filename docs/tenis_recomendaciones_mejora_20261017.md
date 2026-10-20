# Recomendaciones para mejorar el motor de tenis

## Prioridad 1: construir evidencia prospectiva

1. Capturar calendario, estado del partido, probabilidades y cuotas con recibos UTC antes de cada encuentro. El dato debe quedar sellado y no reescribirse.
2. Usar dos momentos declarados, por ejemplo T−120 y T−15 respecto de la hora estimada, conservando ambos cuando el encuentro se retrase. `commence_time` no sustituye el inicio real ni el cierre de cada casa.
3. Reservar el siguiente periodo cronológico sin usarlo para ajustar pesos, calibración, mercados o umbrales. La revisión de 2026 queda etiquetada como desarrollo.

## Prioridad 2: mejorar probabilidad de ganador

1. Mantener el híbrido aprendido como candidato. Es mejor que sumar puntos Elo arbitrariamente a la probabilidad de saque y conserva la simetría entre jugadores.
2. Ajustar el peso y la calibración con ventanas móviles anteriores al origen, y comparar siempre con Elo calibrado, Markov calibrado y probabilidad de mercado sin margen.
3. Evaluar log-loss, Brier, curvas de calibración y estabilidad por circuito, superficie y rango de probabilidad. La promoción exige mejora repetida, no solo mayor acierto.
4. Probar después un modelo de estado dinámico para saque y resto. La semivida fija actual es útil, pero no representa cambios de forma con un proceso temporal explícito.

## Prioridad 3: otros mercados

1. No trasladar el híbrido de ganador a totales, hándicaps o sets. Cada mercado necesita calibración propia sobre la distribución conjunta.
2. Priorizar hándicap de juegos y primer set, que mostraron señales iniciales frente a referencias sencillas. Totales no avanzan hasta corregir su desempeño.
3. Comparar cada predicción con la misma línea ofrecida. Una cuota Over 22,5 nunca se mezcla con Over 23,5.

## Prioridad 4: cuotas y ejecución

1. Consultar dinámicamente hasta diez casas por grupo. La muestra recomienda comenzar con LeoVegas, Pinnacle y Coolbet: LeoVegas tuvo la mayor amplitud, mientras Pinnacle ofreció el mejor precio en 46 de 116 selecciones comparables. Escoger la mayor cuota solo para una selección y línea idénticas.
2. Confirmar que la casa está disponible para la cuenta y jurisdicción del titular. Una cuota del agregador no demuestra que pueda ejecutarse.
3. Medir apertura, precio usado y cierre, descontando margen. ROI, CLV y valor esperado solo se calculan sobre precios realmente disponibles y reglas de liquidación verificadas.
4. Mantener un presupuesto explícito. El sistema ya bloquea solicitudes que superen el límite o consuman la reserva compartida.

## Prioridad 5: identidades, formatos y liquidación

1. Conservar alias con evidencia; no aprobar automáticamente aunque el nombre sea idéntico. Usar identificadores oficiales cuando el proveedor los exponga.
2. Añadir reglas por casa, mercado, jurisdicción y fecha. Nunca excluir retiros después de conocer el resultado.
3. Incorporar formatos faltantes —super-tie-break, sets cortos y reglas históricas— únicamente con pruebas y metadatos de torneo.

## Puerta de producción propuesta

El motor puede avanzar a sombra cuando todos los eventos tengan identidad y estado verificados. Puede considerarse para publicación después de una muestra futura suficiente con mejora probabilística estable frente a Elo calibrado y mercado sin margen, reglas completas para la casa usada y resultados financieros que incluyan retiros, anulaciones y límites reales. Hasta entonces, toda salida permanece como investigación.

## Avance prospectivo del 17 de octubre

Ya existe el flujo sellado de sombra con objetivos T−120 y T−15. El primer registro congeló dos probabilidades antes de los partidos: Davidovich Fokina 46,2824% frente a Jodar y Chwalinska 36,1980% frente a Kartal. No se descargaron cuotas pagadas y ninguna salida quedó habilitada para apostar.

Shanghai está bloqueado porque ATP confirma torneo, fecha y superficie, pero la página verificada no expone el cruce y la hora exactos. Wuhan está bloqueado porque WTA confirma a Chwalinska y Kartal en la final, pero la hora publicada no coincide con el `commence_time` de The Odds API. La solución aplicada exige una lectura oficial con menos de 15 minutos, participantes exactos y hora reconciliada antes de gastar créditos.

Los objetivos del 18 de octubre, hora de Ciudad de México, son 00:30 y 02:15 para Shanghai, y 02:30 y 04:15 para Wuhan. El saldo observado fue 6.285 créditos, con reserva recomendada de 6.200 y tope local acumulado de 80 para las cuatro ventanas. El registro inmutable está en `data/tennis/operations_20261016/shadow/`.
