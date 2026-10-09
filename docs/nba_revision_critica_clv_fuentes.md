# NBA — revisión crítica del texto sobre CLV, fuentes y modelos cuánticos

**Versión:** 1.0 · **Fecha del cliente:** 4 de octubre de 2026.
**Estado:** complemento metodológico documentado; implementación pendiente.

Analiza el texto aportado por el usuario el 4 de octubre y complementa el
[plan maestro](nba_plan_fases_auditable.md), con trazabilidad en el
[registro](nba_plan_fases_auditoria.json). Conserva sus fases y puertas.
Ninguna recomendación del texto aprueba G0–G9 ni demuestra beneficio.

## Dictamen

Son razonables la prioridad de datos/PIT, aislamiento, probabilidades e
incertidumbre, la comparación de fuentes y el aplazamiento de E20. Requieren
corrección las garantías implícitas de rentabilidad, debilidad universal de
props, equivalencia entre CLV y éxito predictivo, categorías fijas sharp/soft
y ventajas generales de QNN. El elogio «99%» carece de muestra o benchmark.

Las menciones a tesis de Stanford/Leiden carecen de autor, título, fecha,
repositorio y página que respalde cada afirmación. Los enlaces suministrados
son redirecciones de búsqueda/grounding; no bastan como referencia académica
auditable. Registrar esos apoyos como no verificados, sin afirmar que tales
tesis no existen. Se aportan abajo fuentes primarias identificables.

## F0: probabilidades y evaluación económica

Mantener el objetivo de distribuciones calibradas y añadir explícitamente un
análisis económico separado cuando existan precios comparables. Mucho
acierto no implica valor esperado favorable: también importa el pago.

Para un contrato de dos resultados sin push/void, con cuota decimal `d` y
probabilidad `p`, el beneficio esperado por unidad es `p*d - 1`. Esta es una
identidad matemática, no un procedimiento para certificar `p`. Si hay
devoluciones, usar `p_win*(d-1) - p_loss`, dejando explícita su probabilidad.
Una ventaja calculada con probabilidades mal estimadas puede desaparecer.

## F2/F6/F7: cierre como benchmark complementario

Incorporar CLV en la auditoría de mercado de F6/F7. Conservar en F5 pérdidas
propias de evaluación probabilística, calibración y comparación temporal con
baselines. [Gneiting y Raftery (2007)](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)
fundamentan reglas de puntuación para evaluar distribuciones frente a
resultados observados. El CLV compara precios; su validez como aproximación
de valor depende de la calidad del benchmark de cierre.

Definir antes del test:

- Fuente de referencia por familia y política de cierre: última observación
  recibida antes del inicio real, frescura máxima y tratamiento de suspensión
  o cierre ausente. Conservar hora del proveedor y recepción propia.
- Misma identidad, línea, lado, periodo y reglas de participación/prórroga.
  No comparar Over 7.5 con Over 8.5 como si fuese el mismo contrato.
- Registrar ambas cuotas contemporáneas y método de eliminación de margen.
  En un mercado exhaustivo de dos resultados sin push, una normalización
  posible es `p_close=(1/d_side)/(1/d_side+1/d_opposite)`. Es una convención,
  no identificación de probabilidad verdadera.
- Bajo esos supuestos, `d_observed*p_close - 1` es un diagnóstico con cierre
  como referencia. `d_observed/d_close - 1` es una comparación bruta de precio;
  no presentarla como ROI ni como estimación ajustada por margen.
- Push/void, contratos discontinuados y cambio de línea requieren tratamiento
  propio. Sin cierre comparable, reportar ausente/incomparable; no imputar
  automáticamente un benchmark favorable.
- Reportar cobertura del cierre, concentración por fuente/partido/jugador,
  incertidumbre por bloques y sensibilidad a referencias alternativas.
- Los precios de cierre son resultados de evaluación. Nunca deben entrar
  como features en un pronóstico emitido antes de ese cierre.

Ejemplo hipotético: observar 2.00 y luego 1.80 en el mismo contrato representa
un movimiento favorable de precio. Si la probabilidad real fuera 0.45, el
beneficio esperado al precio 2.00 sería -0.10 por unidad. Ese contraejemplo
demuestra que el movimiento no garantiza expectativa positiva. Tampoco un
resultado individual puede certificar calibración o éxito del modelo.

## F2/F6/F8: comparar operadores y reacción a noticias

Usar características medidas por fuente y mercado: cobertura, frescura,
reglas, disponibilidad, duplicación y liderazgo observado. Las etiquetas
sharp/soft pueden ser descriptivas y provisionales; no fijan una verdad para
todas las props ni garantizan accesibilidad o retrasos aprovechables.

La documentación de [Sportradar Player Markets](https://docs.sportradar.com/uof/data-and-features/player-markets)
confirma productos especializados y un feed común para operadores. No
revela una fórmula universal de precios ni demuestra que las props sean
débiles. Varias marcas tampoco equivalen a varias fuentes independientes.

Extender E17 y E7 dentro de sus fases existentes: seleccionar fuentes y
universo antes del resultado, capturar anuncios y contratos comparables,
registrar movimientos/suspensiones/faltantes y analizar tiempos por noticia.
Comparar cambios deportivos y de precio como objetos distintos. El feed
puede ser la causa del desfase observado; no atribuirlo automáticamente a la
casa ni afirmar que el líder conoce la probabilidad verdadera.

Añadir primera recepción UTC, timestamp de publicación cuando exista,
revisiones y precisión/offset del reloj; usar reloj monotónico para duraciones
locales. «Segundo exacto» significa precisión del registro local, no conocer
el instante del hecho o del ajuste externo. [The Odds API](https://the-odds-api.com/sports-odds-data/update-intervals.html)
publica intervalos de 60 s para props: tratar la reacción como censurada por
intervalo cuando el feed solo permita esa resolución.

## F4/F8: separar minutos, uso y oportunidades

USG% mide posesiones finalizadas, no minutos. [Glosario NBA](https://www.nba.com/stats/help/glossary?hidenav=true).
Mantener modelos distintos de disponibilidad, minutos, producción por
minuto/posesión y oportunidades de rebote/asistencia. Una baja no redistribuye
esas magnitudes de manera idéntica ni garantiza que mejore la proyección de
un suplente. Preservar la ablación baseline/minutos/tasa/ambos de F8.

## F9/E20: afirmaciones cuánticas y comparación clásica

No incorporar como hecho que QNN evita mínimos locales o acelera el problema
NBA. [McClean et al. (2018)](https://www.nature.com/articles/s41467-018-07090-4)
demuestran problemas de gradientes pequeños en familias de circuitos
parametrizados; no todos los circuitos comparten las mismas limitaciones.
[Bowles, Ahmed y Schuld (2024)](https://arxiv.org/abs/2403.07059) encontraron
baselines clásicos superiores en conjunto en sus tareas de clasificación
pequeñas. Esto justifica exigir benchmarking; no demuestra imposibilidad de
ventaja cuántica ni constituye un experimento NBA.

Conservar E20 diferido, con igualdad de datos, cortes, presupuesto de ajuste
y medición del coste completo, incluida codificación/simulación/hardware.
NGBoost sigue como candidato clásico: su
[artículo original](https://proceedings.mlr.press/v119/duan20a.html) presenta
predicción probabilística mediante natural gradient boosting; no prueba una
ventaja en NBA. El texto menciona «F18», fase que no existe: E18 es el control
temporal transversal y no una fase de boosting.

## Efecto sobre implementación

Se mantiene el arranque arnés → aislamiento → cobertura → captura → modelo
básico → entrega experimental → confirmación. Las especificaciones aceptadas
arriba se aplican a sus fases, sin ampliar el MVP a todos los experimentos.
No convertir este dictamen en una promesa de beneficio, calendario o acceso.
La preparación del plan autoriza describirlo como implementable; el estado
operativo se acredita mediante ejecuciones y puertas reales.
