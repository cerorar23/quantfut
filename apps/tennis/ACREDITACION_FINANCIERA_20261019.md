# Estado verificable de rentabilidad del motor de tenis

Revisión: 19 de octubre de 2026. **Rentabilidad no acreditada. No hay aprobación para apostar dinero real.**

Se completó la auditoría financiera que puede realizarse con la evidencia existente. No se generaron resultados, selecciones retrospectivas ni operaciones ficticias para aprobarla. El motor calcula probabilidades y precios; la existencia de esos cálculos no demuestra beneficio realizable.

## Resultado observado

| Comprobación | Resultado |
|---|---|
| Originales de cuotas examinados | 227 respuestas válidas, sin errores de archivo |
| Observaciones de cuotas | 12.420, incluidas capturas repetidas y las anteriores a las dos pruebas de 500 créditos |
| Eventos distintos en esos originales | 11; no son 12.420 apuestas independientes |
| Casas distintas | 56 |
| Observaciones todavía vigentes en la revisión | 0 |
| Registros antiguos del capturador | 6 sellados localmente, 1 sin sello; fuera del periodo financiero actual |
| Otros pronósticos conservados | 8 de investigación y 10 archivos de prueba de integración, algunos repetidos entre cuentas |
| Órdenes financieras prospectivas válidas | 0 |
| Órdenes liquidadas / cierres financieros | 0 / 0 |
| ROI y CLV financieros acreditables | Desconocidos; no se presentan como cero ni como positivos |
| Candidato y modelos congelados | Conservados; 37 módulos y 12 artefactos comprobados |
| Nuevos créditos / apuestas realizadas | 0 / 0 |

Fuentes reproducibles: `data/tennis/financial_accreditation_20261019/audit_v2.json` y `run_config.json`. El informe incluye las huellas de sus entradas. Las cantidades cubren las tres raíces de archivo configuradas; no incluyen proveedores o archivos no registrados como si se hubieran auditado.

## Trabajo completado

Se entregó `tennis_finance_v2`, independiente del candidato congelado. Ejecuta el evaluador financiero existente, reconstruye las cuotas desde los originales, comprueba las versiones de modelos y código, evita duplicar raíces de archivo, excluye fuentes futuras y genera informes nuevos sin sobrescribir los anteriores. Una carpeta de órdenes inexistente provoca un error: no se confunde con un estudio vacío válido.

La evaluación mantiene pendientes, anulaciones y retiros en la cobertura. Compara cada circuito por separado y conserva los requisitos de cierres y bloques de competición. Añade sensibilidad a costes adicionales de 0, 0,5, 1 y 2 % del importe inicialmente comprometido; son supuestos de estrés, no gastos medidos. Con liquidaciones pendientes no publica ROI de toda la cartera. El denominador incluye el importe originalmente comprometido de las anulaciones y se distingue del ROI calculado solo sobre apuestas con acción.

Se preparó un registro explícito en `ledger/orders`, `ledger/results.json` y `ledger/closings.json`. Está vacío porque no hay órdenes que cumplan el estudio actual. El comando `seal-paper` permite incorporar exclusivamente órdenes que pasen las comprobaciones existentes; no coloca apuestas ni rescata retrospectivamente selecciones de las pruebas de API.

Se obtuvo un sello RFC3161 de DigiCert a las **16:22:52 UTC del 19-oct-2026**, antes del periodo de evaluación. Tras un rechazo inicial de permisos, el usuario autorizó explícitamente ese destino; se envió únicamente una huella criptográfica y un nonce, sin archivos ni credenciales. La firma, la cadena de confianza, el nonce y la correspondencia con el archivo se verificaron; las entradas del conjunto sellado permanecen intactas. Se comprobó además que alterar una copia y recalcular su hash local no permite pasar la verificación criptográfica. El sello demuestra existencia a la hora de la autoridad; no acredita horas locales anteriores, resultados correctos, futuras órdenes ni rentabilidad. Pruebas en `timestamp_preregistration`, `preregistration_proof_summary.json` y `timestamp_tamper_check.json`. [Documentación oficial de DigiCert](https://knowledge.digicert.com/general-information/rfc3161-compliant-time-stamp-authority-server).

## Criterio financiero que permanece vigente

El protocolo `operational_readiness_20261018/financial_policy_v2.json` fue fijado antes del periodo **20-oct-2026 00:00 UTC a 1-jul-2027 00:00 UTC**. Evalúa únicamente ganador de partido en Pinnacle, una unidad simulada por evento, con las versiones congeladas. No se cambió el periodo para obtener un resultado favorable.

El cierre exige, por circuito, al menos 500 órdenes liquidadas en 30 bloques de competición, cobertura completa de cierres, ausencia de rechazos y límites inferiores positivos de los intervalos de ROI y CLV. El informe puede actualizarse para revisar errores operativos, pero mirar repetidamente el resultado no permite declarar éxito antes del cierre ni ajustar las reglas con esa muestra.

Esos mínimos **no garantizan potencia estadística**. Como ilustración analítica, detectar un ROI del 5 % con apuestas independientes a cuota 2, sin anulaciones ni costes, puede requerir unas 3.132 observaciones para alfa bilateral 5 % y potencia 80 %; con un ROI del 3 %, unas 8.714. La dependencia entre jugadores y torneos puede elevarlas. Esta ilustración no modifica el protocolo congelado ni prescribe un número de apuestas reales.

La liquidación de ganador conserva retiros: en las reglas publicadas de Pinnacle, un set completo basta para que haya acción; sin set completo se anula. Otros mercados dependen de la finalización de su periodo específico. [Reglas oficiales consultadas el 19-oct-2026](https://support.pinnacle.com/hc/en-us/articles/46732820954385-How-does-Pinnacle-grade-tennis-matches-in-the-event-of-retirement-or-disqualification).

## Qué falta y cómo se acredita

1. **Capturas prospectivas elegibles.** Identidades inequívocas, estado oficial reciente, reglas documentadas y predicción sellada antes de solicitar la cuota. Resolver antes los calendarios contradictorios; no contar simultáneamente las dos propuestas de rival de Sara Bejlek.
2. **Cuotas nuevas y cierres comparables.** Las actuales ya caducaron. Los permisos de prueba de 500 créditos por clave se consumieron. La segunda clave correspondía a la cuenta principal; su saldo observado de 4.606 estaba por debajo de la reserva configurada de 6.000. No se gastaron más créditos ni se modificó esa reserva.
3. **Resultados y liquidaciones posteriores.** Archivar fuentes y comprobar que los campos de resultado se corresponden con ellas. El evaluador actual exige horas físicas de inicio y cierre para resultados no walkover; no se sustituyen por horas programadas ni por la hora local de recepción. Si el proveedor no las acredita, hace falta una nueva versión de evaluación con límites temporales justificables, registrada antes de su estudio; no se modifica silenciosamente la existente.
4. **Terminar y evaluar la muestra.** Aplicar las reglas congeladas, conservar pérdidas, retiros y anulaciones, y evaluar incertidumbre y sensibilidad a costes. Si el resultado no pasa, se rechaza el candidato; no se declara acreditado por haber llegado a una cantidad mínima.
5. **Ejecución real verificable.** Incluso un estudio simulado positivo no acredita disponibilidad en una cuenta, importes aceptados, límites, deslizamiento, comisiones o beneficio neto real. No se generaron recibos ficticios ni se habilitó un endpoint de apuestas. Esta fase requiere registros reales y una autorización específica de ejecución.

Las diez familias matemáticas no heredan aprobación del ganador: los mercados adicionales necesitan reglas, cobertura y validación financiera propias. No se selecciona retrospectivamente la familia ganadora entre muchas pruebas. El estudio actual tampoco incorpora viajes, clima o carga: la falta de campus de Palm Hills o techo no bloquea este candidato sin esas variables, y resolverlos por sí solo no demuestra rentabilidad.

## Uso reproducible

Desde el motor entregado, con su directorio en `PYTHONPATH`:

```powershell
python -m tennis_finance_v2 audit --config "C:/Users/huye/Documents/apuesta proyec/data/tennis/financial_accreditation_20261019/run_config.json" --output "C:/Users/huye/Documents/apuesta proyec/data/tennis/financial_accreditation_20261019/revision_NUEVA.json"
```

Para registrar una selección **simulada** ya elegible:

```powershell
python -m tennis_finance_v2 seal-paper --config RUTA_CONFIG --record RUTA_REGISTRO --quote-receipt RUTA_RECIBO --event-id ID_EVENTO --selection "NOMBRE_EXACTO"
```

No usar ejemplos como evidencia real. Los resultados y cierres se suministran con el contrato de `tennis_engine.paper_validation`; se conservan sus fuentes originales y se crean revisiones nuevas, sin editar archivos ya utilizados para justificar un informe previo. No se programó un servicio automático ni se prometió capturar futuros resultados en segundo plano.

Validación de entrega: **312 pruebas del motor aprobadas**, incluidas 18 nuevas del control de evidencia; arnés general inicial y final: **1.315 aprobadas, 95 omitidas y dos advertencias**. Docker no disponible. La comprobación criptográfica real y su prueba negativa se realizaron adicionalmente, sin modificar las pruebas unitarias ni los originales.

Un informe positivo de simulación pasaría a revisión de ejecución. Ninguna herramienta de esta entrega convierte un resultado histórico en una garantía de beneficio futuro.
