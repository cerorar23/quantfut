# Tenis: preparación operativa y validación financiera

Actualización: 18 de octubre de 2026, México / 19 de octubre UTC.

El motor tiene una ampliación implementada y probada para archivar pronósticos meteorológicos y evaluar selecciones simuladas prospectivas. **No está acreditado para apostar con ventaja ni existe una garantía de rentabilidad.** La implementación no coloca apuestas. No se ha habilitado publicación de picks ni modificado el modelo congelado.

## Entrega y evidencia

- Código nuevo: `tennis_engine/weather.py`, `tennis_engine/paper_validation.py` y `scripts/operational_validation.py`, dentro del motor independiente `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis`.
- Evidencia local: `data/tennis/operational_readiness_20261018/`. Los archivos anteriores se conservan; los informes nuevos indican su versión.
- 225 pruebas específicas aprobadas: 194 existentes y 31 nuevas. Las nuevas verifican disponibilidad temporal, unidades, techo desconocido, integridad del archivo, cuotas originales, retiros, versiones de modelo y prohibición de aprobar el estudio anticipadamente.
- Comprobación general final aprobada: 1.315 pruebas, 95 omitidas y dos avisos, en 93,32 segundos. Docker no está disponible y su comprobación se omitió. El primer intento no llegó a ejecutarse por el límite temporal de la revisión de permisos; el reintento posterior se autorizó y terminó correctamente.
- Las 12 piezas del modelo congelado y el archivo canónico de 492.251 encuentros permanecen intactos. No se reentrenó con los resultados exploratorios de 2025/2026.

## Qué datos se consiguieron realmente

| Componente | Evidencia | Límite vigente |
|---|---|---|
| Calendario API-Tennis | Dos consultas; 66 eventos: 64 programados sin verificación oficial y dos cancelados | Horarios estimados; ninguna hora física de inicio o fin acreditada; plan y cuota del proveedor desconocidos |
| Sedes contemporáneas | 66/66 eventos enlazados con recintos y coordenadas revisados | Identificar el recinto no acredita la cancha ni el estado del techo |
| Pronóstico Open-Meteo | Una consulta pública para cinco puntos; respuesta original archivada a las 00:37:57 UTC del 19-oct | Pronóstico de una celda meteorológica, no sensor de la pista; no se inventa fecha de emisión |
| Disponibilidad del pronóstico | Informe v3: 64 candidatos futuros; informe v4, a las 04:11:58 UTC: 58 todavía futuros | Seis horarios previstos ya habían transcurrido; los dos cancelados se excluyen. No hubo nuevas consultas al producir v4 |
| Techo y exposición | Cero observaciones verificadas de techo | La rama principal conserva valores desconocidos; la sensibilidad exterior no entra al modelo |
| Palm Hills, septiembre de 2025 | Tres individuales identificados, campus todavía ambiguo | Se mantienen excluidos del análisis espacial; no se sustituyen coordenadas por similitud de nombre |
| Validación financiera | Registro y evaluador implementados; cero selecciones prospectivas y cero resultados financieros | ROI e intervalos son `null`, no cero ni rentabilidad demostrada |

La hora de recepción de una transición de estado describe cuándo vimos al proveedor. No acredita el instante real del partido cuando se desconoce la latencia. Tampoco se imputan horas arbitrarias para fabricar descanso exacto.

## Reglas meteorológicas implementadas

El recibo y la respuesta original se verifican mediante SHA-256. Se comprueban unidades explícitas, UTC, orden y unicidad de horas, longitudes de vectores, rangos y correspondencia con el punto solicitado. La celda devuelta debe estar a menos de 50 km; se registra su distancia, sin afirmar precisión de cancha.

Una variable candidata exige recepción estrictamente anterior a la decisión, decisión anterior al encuentro, archivo de hasta seis horas y hora de pronóstico a no más de 30 minutos del inicio previsto. Faltantes y techo desconocido siguen siendo desconocidos. Un techo cerrado impide aplicar automáticamente el clima exterior. No hay coeficientes fisiológicos manuales ni modificación de probabilidades congeladas.

## Estudio financiero nuevo, separado del protocolo anterior

`financial_policy_v2.json` fija anticipadamente el periodo **20-oct-2026 00:00 UTC a 1-jul-2027 00:00 UTC**, modelo y código exactos. El protocolo original que terminaba el 1-ene-2027 sigue intacto. El periodo adicional es amplio para reunir competiciones de ambos circuitos; no promete completar la muestra ni demostrar ventaja en una fecha concreta.

La política v1 fue una preparación sin selecciones ni resultados y quedó marcada como sustituida antes de comenzar su periodo. La versión v2 vincula los archivos del código que realmente se ejecuta, impide detener anticipadamente el estudio y amplía su ventana prospectiva. No se ha elegido una regla usando beneficios observados.

Reglas de esta evaluación:

1. Ganador del partido (`h2h`), perfil de liquidación Pinnacle; no acredita todas las casas ni mercados. Los otros mercados conservan su estado experimental.
2. Una selección por evento, primera orden sellada, retorno condicional del modelo positivo y una unidad simulada fija. Predicción sellada antes de solicitar la cuota; cuota tomada de su archivo original, no de una cifra copiada.
3. Identidades, estado oficial y horario reconciliados y frescos. El calendario API-Tennis por sí solo no satisface esta verificación. Los adaptadores oficiales existentes no cubren universalmente cada torneo actual.
4. Los retiros se liquidan según el contrato verificado y se mantienen en la rentabilidad. Los partidos completos forman la muestra común para Log-Loss, Brier y ECE frente al mercado sin margen observado al mismo momento.
5. Cierre comparable anterior al inicio físico acreditado, con las mismas partes y contrato; frescura máxima de 30 minutos. Sin prueba de inicio real no se fabrica CLV.
6. Al terminar el periodo: al menos 500 selecciones liquidadas y 30 competiciones por circuito, todos los cierres comparables, sin evidencia rechazada y límite inferior positivo en intervalos de ROI y retorno al cierre calculados por bloques de competición. Esos mínimos no son un análisis de potencia ni garantizan ausencia de dependencia entre jugadores.
7. Comisiones y coste por selección se fijan en cero como **supuesto declarado de simulación**. Los precios observados no acreditan ejecución, disponibilidad en una cuenta, límites, deslizamiento ni costes reales. Incluso superar el estudio solo habilita una revisión de ejecución; nunca activa apuestas automáticamente.

Las variables de clima, viajes o carga que el modelo base no usa no bloquean su evaluación. Una variante que sí las use necesita datos y validación propios. Cambiar la versión o la selección durante este estudio invalida su interpretación confirmatoria; una modificación exige un protocolo nuevo y un periodo futuro distinto.

## Uso reproducible

Desde la raíz del checkout independiente, con el entorno Python del proyecto:

```powershell
$engine = 'apps/tennis/scripts/operational_validation.py'
$audit = 'C:/Users/huye/Documents/apuesta proyec/data/tennis/operational_readiness_20261018'
# La salida debe ser un archivo nuevo: no sobrescribir evaluaciones previas.
python $engine evaluate-paper --policy "$audit/financial_policy_v2.json" --orders "$audit/paper_orders" --results "$audit/empty_results.json" --output "$audit/financial_report_manual_001.json"
```

Este ejemplo reproduce la ausencia de evidencia; no inventa resultados. Cuando existan selecciones válidas, se registran con `seal-paper`, un registro de predicción sellado y el recibo original de cuotas. Los resultados y cierres deben aportar sus archivos y contratos verificables. `--help` enumera los argumentos de captura, sello y evaluación.

La captura de estados ya existente conserva su límite local y los secretos fuera de los argumentos. No hay servicio automático nuevo activo. No se consumieron créditos de The Odds API en esta ampliación; su presupuesto autorizado sigue siendo **2.000 créditos mensuales para tenis** en la cuenta de pago compartida.

## Qué impide declarar aptitud para apostar

Faltan observaciones temporales físicas y de techo cuando una variante las requiera; cobertura oficial fresca de los eventos a seleccionar; cuotas y cierres prospectivos con sus resultados; y evidencia financiera fuera de muestra seguida de verificación de ejecución y límites de exposición. Los tres casos históricos de Palm Hills no explican por sí solos esta falta de evidencia ni bloquean todos los demás eventos.

La preparación informática puede verificarse hoy. La rentabilidad futura necesita datos que todavía no existen; no se puede sustituir por más código, más pruebas unitarias ni una promesa de precisión del 100 %.

Fuentes de contrato: [Open-Meteo](https://open-meteo.com/en/docs), [API-Tennis](https://api-tennis.com/documentation), [The Odds API v4](https://the-odds-api.com/liveapi/guides/v4/), [liquidación de retiros de Pinnacle](https://support.pinnacle.com/hc/en-us/articles/46732820954385-How-does-Pinnacle-grade-tennis-matches-in-the-event-of-retirement-or-disqualification).
