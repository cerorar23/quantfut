# Protocolo prospectivo NBA 2.2

Este documento se registra antes de publicar 2.2. No convierte un backtest en evidencia prospectiva.

- Solo entran pronósticos sellados antes del salto, con cadena íntegra, versión/artefacto identificados y resultado oficial final disponible. Sin predicción anterior al partido, no se rellena después.
- La API informa Brier, log-loss, fiabilidad y tamaño de muestra **por versión completa**. Las cifras de 2.0/2.1 no acreditan 2.2. Una actualización del artefacto conserva su identidad propia; no se agrupan versiones silenciosamente para alcanzar un mínimo.
- Para una acreditación empírica se requiere un plan independiente de evaluación, muestra suficiente por tramo y estimación de incertidumbre por fechas. Como mínimo de revisión: 500 partidos, 60 fechas y 50 observaciones en cada tramo evaluado; estos mínimos por sí solos no acreditan calibración.
- Se usarán cinco tramos fijos de probabilidad (0–20%, …, 80–100%), diferencia entre frecuencia observada y probabilidad media e intervalos simultáneos del 95% mediante bootstrap de fechas (2.000 réplicas). Se predeclara una tolerancia de ±10 puntos porcentuales: todos los intervalos evaluables deberán quedar dentro de ella. No se omiten a posteriori tramos que fallen.
- Cualquier agrupación futura de artefactos de una misma receta deberá registrarse antes de observar sus resultados, incluyendo algoritmo, código, política de actualización y población. No acredita retrospectivamente una cohorte elegida por sus aciertos.
- No se ajustan parámetros con la ventana que se utiliza para acreditar. Cambiar la receta abre una evaluación nueva. La acreditación de ganador no se extrapola a props, hándicap o totales ni demuestra rentabilidad.

Estado al preparar el despliegue: **sin acreditación de 2.2**. El endpoint `/nba/v1/calibracion` conserva `calibracion_certificada=false`; ese estado solo puede revisarse con resultados reales suficientes, sin forzar una bandera para satisfacer una solicitud.
