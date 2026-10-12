# API-NBA: acceso efectivo de la cuenta gratuita — 9 de octubre de 2026

La credencial facilitada coincide con la configuración privada local ya existente en `apps/nba/.local/api_nba.env`, excluida de Git. Se verificó autenticación y plan Free activo. No se imprimió la clave, no se modificaron credenciales de fútbol ni se trasladó la clave al sitio público.

## Resultado observado

| Consulta | HTTP | Resultado de aplicación |
|---|---:|---|
| `/status`, inicial y final | 200 | Free activo, límite 100/día; ambas consultas declararon consumo cero. Se retiraron los datos de identidad de cuenta de las respuestas guardadas. |
| `/seasons` | 200 | 12 temporadas enumeradas. Enumerar una temporada no acredita permiso para acceder a sus datos. |
| `/games`, temporada 2026, fecha 2026-10-09 | 200 | Rechazo: `Free plans do not have access to this season, try from 2022 to 2024.` |
| `/games`, temporada 2025, fecha 2026-04-12 | 200 | Mismo rechazo de temporada. |
| `/games`, temporada 2024, fecha 2025-04-13 | 200 | Rechazo del filtro de fecha: `Free plans do not have access to this date, try from 2026-10-09 to 2026-10-11.` |
| `/games`, temporada 2024, sin filtro de fecha | 200 | 1.406 partidos; sin errores. Cabecera final: 99 solicitudes disponibles y máximo 10/minuto. |

Se realizaron cinco solicitudes de datos y dos comprobaciones de estado, sin reintentos automáticos. El estado de cuenta y las cabeceras no coinciden exactamente en consumo; se conservan ambos sin suponer que cada intento fue facturado. Las consultas principales se espacian al menos 6,4 segundos. No se solicitaron estadísticas individuales nuevas: la consulta histórica con fecha fue rechazada y la última solicitud autorizada se dedicó a comprobar el calendario de una temporada expresamente permitida.

Originales sanitizados, recibos, tiempos y SHA-256: `apps/nba/.local/operations/api_nba_access_20261010T000417Z/`. El nombre usa UTC; la ejecución ocurrió el 9 de octubre en Ciudad de México. La consulta adicional de temporada permitida consta en `supplemental_receipt.json`, junto con el total de cinco solicitudes; el manifiesto inicial de cuatro intentos permanece intacto.

## Decisión operativa

La estimación anterior de 85 solicitudes/día es un presupuesto de volumen, **no una prueba de acceso a la temporada actual**. La documentación pública del proveedor no reemplaza los permisos observados en esta cuenta. Con este plan no se puede alimentar la pretemporada ni la temporada 2026–27 mediante las consultas probadas.

No se activó una tarea recurrente que consumiría cuota sin datos actuales, ni se contrató una suscripción. Para integrar API-NBA como fuente actual hace falta acceso efectivo a la temporada 2026 y comprobar boxscores/estadísticas individuales antes de conectarla a modelos. Las fuentes NBA/ESPN existentes pueden continuar su cometido; este diagnóstico no modifica su operación, los pronósticos sellados, las puertas científicas ni el despliegue.

Comprobaciones del proyecto previa y posterior: 808 pruebas aprobadas, 16 omitidas en cada ejecución; Docker no disponible para validar Compose. Se verificaron los SHA-256 de siete recibos, ausencia de clave en la evidencia e identidad de cuenta retirada de ambos estados. Este trabajo es un diagnóstico de acceso; no desarrolla un nuevo modelo ni recupera segundos individuales, lesiones o props.
