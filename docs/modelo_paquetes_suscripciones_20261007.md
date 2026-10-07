# QuantFut: paquetes, suscripciones y cuenta

7 de octubre de 2026. Adaptación local del diseño y modelo comercial público
de [TennisPredictions](https://tennispredictions.ai/es/subscriptions), conforme
a la aclaración del usuario: «Paquetes y suscripciones».

## Modelo adaptado

Un paquete completo, QuantFut Plus, vendido por periodo de acceso. Explorador
mantiene los partidos y la evidencia pública gratuitos. Los periodos cambian
el precio y la duración, no la calidad ni la cantidad garantizada de picks.

| Modalidad | Periodo | Total de referencia USD | Equivalente mensual USD | Ahorro frente a meses sueltos |
| --- | --- | ---: | ---: | ---: |
| Básico | 1 mes | 14.99 | 14.99 | — |
| Estándar | 3 meses | 33.99 | 11.33 | 10.98 |
| Premium | 6 meses | 53.99 | 9.00 aprox. | 35.95 |
| Club QuantFut | De por vida, propuesta | 179.99 | — | — |

Los totales proceden de la página pública consultada. Los equivalentes
mensuales de la referencia no coincidían exactamente con sus totales: aquí
se calculan desde el importe total en centavos, sin propagar la discrepancia.
Son precios ilustrativos, no tarifas aprobadas para QuantFut. Moneda comercial,
impuestos y condiciones deberán definirse antes de habilitar contratación.

## Diseño y recorrido entregado

- Suscripciones: tres tarjetas y Club, estado seleccionado, resumen, cupón
  ilustrativo, beneficios y preguntas frecuentes.
- Paquetes: comparación Explorador/Plus y estructura de entrega del pick
  con selección, precio, mínimo, fecha y resultado.
- Acceso: login, registro y recuperación con identidad sintética de solo
  lectura. No recibe contraseñas reales ni envía correo.
- Mi cuenta: resumen, preferencias, favoritos demo, suscripción/transacciones
  y seguridad. Se conserva el formato de cuotas y filtro de ligas del proyecto.
- Pedido: plan → perfil demo → revisión del total. El cobro queda deshabilitado;
  elegir un plan no crea orden ni otorga derechos. Recargar borra la sesión visual.

Paleta solicitada: azul noche, tarjetas pizarra, blanco hielo y esmeralda.
Los formularios y paneles comparten el diseño de la portada de esta misma fase.
Se usó SingleFile CLI 2.18.0 para conservar referencias públicas en la carpeta
ignorada `.local/design-reference/`: `suscripciones.html`, `iniciar-sesion.html`
y sus manifiestos. La captura de acceso se hizo sin la sesión de la referencia.
No se guardaron los datos personales del panel de cuenta consultado.

## Propuesta comercial para QuantFut

Mantener un solo paquete Plus y descontar por duración hace la comparación
clara. Conviene lanzar primero 1/3/6 meses y reservar Club hasta definir su
alcance y coste de mantenimiento. El historial público sirve para evaluar el
servicio antes de elegir. La ficha de cada pick debe conservar mínimo, cuota
registrada y hora de publicación; el historial debe conservar también pérdidas.

La cuenta futura necesitará identidad verificada, sesiones seguras,
autorización en servidor, órdenes y confirmación de pago mediante webhook.
Renovaciones, cancelaciones y devoluciones se definirán explícitamente.
El contrato técnico existente permanece en `frontend/ACCESS_FLOW.md`.

## Verificación

13 pruebas de frontend, incluyendo importes y descuentos; 11 pruebas del
servidor web, incluyendo los dos nuevos archivos públicos. Recorrido en navegador:
selección, recuperación, registro/login demo, preferencias, favoritos, facturación
sin activación y pedido bloqueado. Revisión responsive en 320/390/768 px y escritorio.
La vista previa Node muestra la falta de API como estado no disponible.
No se desplegó ni se habilitaron cuentas o cobros reales.
