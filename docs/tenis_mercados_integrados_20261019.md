# Mercados de tenis: ampliación operativa y pruebas reales

19 de octubre de 2026. La ampliación está implementada para calcular, comparar y evaluar contratos de mercados. **No constituye una aprobación de apuestas ni una rentabilidad demostrada.** Los 37 módulos del candidato congelado y sus 12 artefactos se conservan; la ampliación vive aparte, en `tennis_markets_v2`.

## Qué quedó implementado

| Familia | Cálculo | Conexión de cuotas |
|---|---|---|
| Ganador del partido | Win/push/loss y cuota justa | `h2h`, observado |
| Ganador del primer y segundo set | Distribución del set con orden del servicio | `h2h_s1`, `h2h_s2`, observados |
| Total de juegos | Líneas enteras y medias | `totals`, `alternate_totals`, observados |
| Hándicap de juegos | Líneas enteras y medias; devolución explícita | `spreads`, `alternate_spreads`, observados |
| Total de sets | Líneas enteras y medias | `alternate_set_totals`, conectado; no observado en estas capturas |
| Hándicap de sets | Líneas enteras y medias | `alternate_set_spreads`, conectado; no observado |
| Habrá tiebreak | Sí/no | Contrato local; sin clave de tenis acreditada en The Odds API |
| Marcador por sets | Todos los marcadores finales válidos BO3/BO5 | Contrato local; no se reutiliza la clave de marcador de fútbol |
| Total de juegos de un set | Primero/segundo set, líneas y devoluciones | `totals_s1`, `alternate_totals_s1`, `alternate_totals_s2`, conectados; no observados |
| Hándicap de juegos de un set | Periodo explícito, líneas y devoluciones | `spreads_s1`, conectado; no observado |

Son **diez familias y trece claves documentadas del proveedor**. La implementación acepta las líneas reales enteras y medias; no se limita a los ejemplos de la tabla. Las líneas de cuarto necesitan otro contrato de liquidación y se rechazan explícitamente. Aces, dobles faltas, apuestas en contra de bolsa y otros mercados ajenos al modelo quedan visibles como no soportados.

Todos los mercados de esta versión salen de una misma distribución Markov de partido completo. No se mezclan silenciosamente sus marginales con el ganador híbrido: ese pronóstico anterior se conserva como referencia separada. El modelo contempla reglas BO3/BO5 y tiebreak final; sigue siendo un modelo de parámetros estáticos, sin riesgo de retiro integrado en sus probabilidades.

Se generan **78 contratos de ejemplo por encuentro BO3**; el archivo de ocho encuentros contiene **624 filas**. Las cuotas justas son teóricas. Las líneas ilustrativas no se presentan como ofertas reales, y esta expansión, calculada después del sello original del ganador, no se retrofecha como pronóstico previo de los otros mercados.

## Pruebas con las claves autorizadas

El usuario autorizó primero una comprobación compartida de hasta 14 créditos, manteniendo un mínimo de 5.104. Consumo real: **6 créditos**, 80 ofertas y cinco tipos de mercado; saldo observado al terminar:5.108. La autorización quedó consumida y no se reutilizó como permiso ilimitado.

Después autorizó500 créditos de cada una de dos claves. Los registros confirman:

| Clave suministrada | Consumo confirmado de esta prueba | Saldo observado al terminar | Identidad de cuenta |
|---|---:|---:|---|
| Primera | 500 | 0 | Distinta de la cuenta compartida |
| Segunda | 500 | 4.606 | **Es la misma clave de la cuenta principal compartida** |

La segunda clave fue inicialmente etiquetada como una demo separada. La comparación de credenciales demostró que coincide con la principal. Debió comprobarse antes de capturar. Los500 consumidos estaban dentro de la autorización expresa para esa clave; se incorporaron al registro central de tenis y se conservaron las fuentes originales. `account_identity_correction.json` corrige la etiqueta sin ocultar los informes iniciales. Los scripts ahora detectan esa coincidencia antes de iniciar una prueba como cuenta separada.

Consumo de la ejecución: **1.000 créditos de las dos pruebas ampliadas, más los 6 de la comprobación previa**. De esos1.006,506 corresponden a la cuenta compartida y500 a la otra cuenta. El registro central mensual de tenis contabiliza **583 confirmados y595 reservados**, dentro del límite de 2.000; la diferencia corresponde a reservas conservadoras previas. Los17 créditos de recibos antiguos con `actual_cost` nulo en SQL se incluyen mediante su recibo, no se pierden en una suma SQL incompleta.

La configuración general de reserva continúa en 6.000. Los consumos autorizados fueron excepciones acotadas, no un cambio permanente de esa configuración. Los saldos son observaciones de la captura; otros consumidores de la cuenta pueden modificarlos. No se enviaron órdenes de apuestas y no quedan créditos de estas autorizaciones pendientes de consumir.

## Datos obtenidos y cobertura real

- **12.052 ofertas en capturas repetidas**, correspondientes a56 casas distintas y9 identificadores de evento de Ningbo.
- **6.796 filas** pudieron recibir probabilidad y precio teórico; las otras quedaron sin precio de modelo o como mercado no soportado. No se escogió un ID ambiguo para rellenarlas.
- Siete claves soportadas aparecieron en respuestas reales: `h2h`, `h2h_s1`, `h2h_s2`, `spreads`, `alternate_spreads`, `totals`, `alternate_totals`. La bolsa `h2h_lay` también apareció; se conserva sin modelar su responsabilidad de apuesta en contra.
- Las seis claves restantes tienen adaptador y pruebas, pero no aparecieron en estas capturas. Gastar más créditos no acredita una cuota que el proveedor no devuelve.
- Se archivan respuestas, recibos, cargos, parámetros y versiones. El conjunto guarda todos los snapshots y también el último bloque completo de mercado por evento/casa. No se reconstruyen pares de cuotas mezclando momentos diferentes.

El calendario muestra a **Sara Bejlek contra dos rivales diferentes el20-oct**, con una hora entre los horarios previstos. No se afirma que ambos encuentros sean independientes y aptos: requieren conciliación con el programa oficial. Ese conflicto no se corrige cambiando nombres ni eliminando una fila sin evidencia. Persisten asimismo las ambigüedades históricas de identidades señaladas en la auditoría anterior.

Las capturas repetidas **no son 12.052 apuestas ni resultados futuros**. Se usan para cobertura de casas, contratos y comparación de precios, no para inflar la muestra de rentabilidad.

## Evaluación probabilística histórica

Se ejecutó un protocolo fijo sobre los archivos ya existentes de 2026, usando los modelos con origen **1-ene-2026**, no los actuales de octubre para predecir partidos anteriores. Las líneas se fijaron antes del cálculo; no se eligieron mirando beneficios.

| Circuito | Partidos disponibles | Evaluados con parámetros e identidades admitidos |
|---|---:|---:|
| ATP | 2.451 | 2.207 |
| WTA | 2.146 | 1.291 |
| Total | 4.597 | 3.498 |

Son **56.804 probabilidades de contratos fijos**, con Log-Loss, Brier y ECE por contrato y formato. Los pushes se mantienen en cobertura y se separan de la métrica binaria condicional. Las exclusiones por identidad o parámetro ausente se registran por circuito.

Esta es una evaluación **exploratoria**:2026 ya se inspeccionó y la disponibilidad histórica de algunas fuentes no está completamente acreditada. Las marginales de esta ampliación aún no tienen calibración completa por contrato. El informe aporta mediciones, no demuestra superioridad frente al mercado ni rentabilidad. No utiliza cuotas inexistentes para calcular ROI.

## Comparación y liquidación

La comparación usa la misma selección, periodo y línea; normaliza signos de hándicap y solo elimina margen ante un par complementario completo de una misma casa. El mejor precio se marca entre observaciones frescas equivalentes. Un precio observado no acredita disponibilidad o ejecución en una cuenta.

La liquidación aplica el perfil verificado de Pinnacle: ganador con un set completado; mercados de partido que exigen finalización se anulan ante retiro; mercados de un set completado se liquidan con ese periodo. Las reglas desconocidas y los props de tiebreak ante retiro quedan pendientes cuando el contrato no esté acreditado. No se excluyen retiros para mejorar artificialmente el ROI. Las líneas con devolución conservan su resultado push.

La evaluación del ledger produce cobertura, anulaciones, devoluciones, métricas y ROI solo cuando corresponde a los datos suministrados. No certifica por sí misma que las apuestas sean prospectivas ni ejecutadas. El estudio financiero congelado anterior se conserva intacto.

## Entrega y uso

Motor independiente: `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis`.

- `tennis_markets_v2`: contratos, distribución, adaptadores, comparación, liquidación y evaluación; presupuestos y detección de claves compartidas.
- Scripts acotados de captura, reproducción de archivos y evaluación histórica. Las pruebas de 500 ya se consumieron; no repetirlas con otro directorio para crear un presupuesto ficticio nuevo.
- `data/tennis/markets_integration_20261019/mercados.md`: tabla de contratos y precios teóricos.
- `delivery_summary.json`: cobertura y consumo consolidado; `all_demo_offer_snapshots.parquet`: las 12.052 observaciones; `latest_whole_market_snapshots.json`: últimos bloques completos.
- `data/tennis/markets_backtest_v2_20261019/report.json`: resultados por contrato, cobertura y límites de la evaluación histórica.

Ejemplo de exportación **sin consumir API** desde el checkout independiente:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'apps/tennis')
python -m tennis_markets_v2 --predictions 'C:/Users/huye/Documents/apuesta proyec/data/tennis/forecast_audit_20261019/research_emission_v1/predictions.json' --output 'C:/Users/huye/Documents/apuesta proyec/.local/mercados_exportacion_manual.json'
```

El destino debe ser nuevo. El comando conserva fecha de derivación y distingue el sello anterior; no promete que los encuentros del archivo sigan futuros.

**294 pruebas específicas aprobadas**. La comprobación general final aprobó 1.315, con 95 omitidas y dos avisos, en 112,12 segundos; Docker no disponible. El manifiesto de entrega verifica archivos, modelos, fuentes y consumos.

Fuentes de contrato: [mercados documentados de The Odds API](https://the-odds-api.com/sports-odds-data/betting-markets.html), [endpoints, cobertura y costes](https://the-odds-api.com/liveapi/guides/v4/), [liquidación de retiros de Pinnacle](https://support.pinnacle.com/hc/en-us/articles/46732820954385-How-does-Pinnacle-grade-tennis-matches-in-the-event-of-retirement-or-disqualification). La documentación describe claves disponibles; la cobertura efectiva depende del evento y la casa.
