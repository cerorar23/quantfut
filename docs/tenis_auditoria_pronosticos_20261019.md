# Auditoría del motor y primeros pronósticos contrastados

19 de octubre de 2026 UTC / 18 de octubre, México.

**Resultado:** el motor puede emitir probabilidades de investigación para encuentros que superen sus controles. En esta ejecución quedaron sellados ocho pronósticos ATP reales antes del límite horario oficial revisado. No hay evidencia suficiente para aprobar apuestas con dinero ni una garantía de rentabilidad. El archivo conserva los pronósticos originales, no probabilidades reconstruidas al conocer el resultado.

Los ocho están en `C:/Users/huye/Documents/apuesta proyec/data/tennis/forecast_audit_20261019/pronosticos.md`; su registro íntegro, modelos, fuentes, identidades y sellos en `research_emission_v1/predictions.json` del mismo directorio.

## Qué se comprobó

- 214 originales conservados y 492.251 encuentros canónicos: integridad aprobada, cero fallos. Los 12 artefactos de modelo congelados permanecen idénticos.
- Nueva captura API-Tennis: 66 eventos, de los cuales 58 estaban programados sin verificación oficial, tres completados, tres en juego y dos cancelados. Dos consultas; no se consultaron cuotas ni consumieron créditos de The Odds API.
- Cuatro programas oficiales actuales descargados, archivados con SHA y revisados visualmente: Almaty, Bruselas, Osaka y Ningbo. La revisión conserva la celda y la cancha de cada pareja; no busca dos apellidos que podrían pertenecer a canchas o partidos distintos.
- Veinte parejas individuales revisadas. Ocho pronósticos ATP emitidos, ocho exclusiones porque el límite inferior previsto ya había transcurrido y cuatro por nombres canónicos ambiguos. Cobertura: 40 % de las parejas revisadas y 12,1 % del calendario capturado. No se afirma cobertura universal.
- 246 pruebas específicas aprobadas: 225 existentes y 21 nuevas para la emisión revisada. La comprobación general inicial aprobó 1.315 pruebas, con 95 omitidas y dos avisos. Los resultados finales se conservan en el manifiesto de entrega.

Los programas pueden cambiar o mover partidos. La fuente y el horario estaban contrastados al sellar cada pronóstico; no constituyen una constancia perpetua de que el encuentro siga sin empezar. La herramienta exige fuentes recibidas antes de la decisión, antigüedad máxima de 15 minutos y otro control tras calcular la probabilidad. Un uso posterior requiere observaciones nuevas.

## Hallazgo adicional relevante: identidades internas ambiguas

La auditoría encontró **50 nombres completos WTA y uno ATP asociados a varios IDs en los modelos existentes**. No se deben fusionar solo porque el nombre coincida. Por ejemplo, el modelo incluye Katie Boulter con los IDs `wta:211107` y `wta:319125`; el [perfil oficial WTA](https://www.wtatennis.com/players/319125/katie-boulter) identifica el segundo como ID del circuito, pero eso por sí solo no documenta cómo deben consolidarse todas las observaciones históricas del primero.

Los cuatro pronósticos WTA que todavía cumplían el límite horario fueron excluidos ante esa ambigüedad. No se eligió el ID con más partidos, el ID mayor ni se promediaron probabilidades. El listado completo está en `identity_ambiguities.json`. Los ocho ATP emitidos tienen un nombre canónico único y todos los parámetros de jugador/superficie presentes; eso no elimina otras incertidumbres del modelo.

Para ampliar la cobertura: acreditar los puentes de identidad con perfiles/biografías y observaciones originales; consolidar en una **nueva versión** del dataset; entrenar y calibrar un candidato distinto; y evaluarlo sin alterar el candidato ni el estudio financiero congelados. El historial ya inspeccionado sigue siendo exploratorio. Este hallazgo impide afirmar que el motor esté perfecto para toda WTA.

## Palm Hills: conclusión de la nueva búsqueda

Se contrastaron de nuevo la ficha Davis Cup, noticias contemporáneas de septiembre de 2025 y una publicación de un empleado del club. Las fuentes consultadas identifican Palm Hills Sports Club / Cairo, pero no acreditan con una dirección o punto verificable cuál de los dos campus alojó la eliminatoria Líbano–Barbados. El intento adicional contra la ficha histórica ITF devolvió HTTP 502; se archivó como intento fallido, no como evidencia.

**No se ha resuelto el campus.** `palm_hills_disposition.json` conserva los tres IDs de partido y su exclusión espacial explícita. No se proyectan hacia 2025 las coordenadas de otra edición ni se usa la ubicación laboral de un empleado como dirección del evento.

Esto no bloquea los ocho pronósticos emitidos: son otros partidos y el modelo base no utiliza esa sede histórica. La exclusión debe permanecer hasta obtener una fuente específica del evento; la conclusión honesta de la búsqueda no es una acreditación ficticia.

## Horarios físicos y techo: requisito por uso

| Uso | Requisito |
|---|---|
| Probabilidad base previa del ganador | Identidades, torneo, superficie y reglas, fuentes actuales y exclusión de partidos que podrían haber empezado; no usa descanso exacto ni clima |
| Descanso exacto o carga diaria que dependa del cierre | Instantes físicos acreditados o intervalos conservadores suficientes; la hora de recepción del estado no es el instante del partido |
| Impacto del clima | Exposición y techo acreditados cuando correspondan, pronóstico disponible antes de decidir y efecto probado fuera de muestra |
| Cierre financiero / CLV | Hora de inicio físico acreditada y cuota comparable archivada antes del inicio |

API-Tennis aporta calendario, estado, marcador y estadísticas conforme a su [documentación](https://api-tennis.com/documentation). En las capturas examinadas no se acreditaron instantes físicos completos de inicio/fin ni techo. No se convierte `event_time` en una hora física ni se inventan horas para dar por cerrado el pendiente. Los programas oficiales contienen horas previstas, turnos seguidos y límites «no antes de»; se conservan esas distinciones.

## Resultados financieros futuros

Se revisaron siete registros antiguos: los pronósticos de las dos finales estaban fuera de las ventanas predeclaradas de captura, y hay dos advertencias de observaciones posteriores a un registro antiguo. No se retrofechan ni se cuentan como prueba financiera confirmatoria. El canónico antiguo conserva además una advertencia de linaje incompleto; su integridad de bytes no acredita disponibilidad histórica perfecta.

El estudio financiero v2 continúa intacto: comienza el 20-oct-2026 UTC. A esta auditoría tiene **cero selecciones financieras prospectivas; ROI desconocido**. Los ocho registros nuevos son emisiones de investigación separadas, no apuestas ni una modificación retroactiva de las reglas de ese estudio.

No es posible obtener hoy resultados de partidos que todavía no se jugaron. Sí quedó creado el primer archivo contrastado que podrá compararse después con los resultados. La prueba financiera exige además precios realmente ofrecidos, cierres comparables, liquidación de retiros y costes; acertar ganadores sin cuotas no demuestra rentabilidad.

## Recomendación operativa concreta

Empezar con el archivo de pronósticos base de los partidos que superen los controles, mantener una muestra íntegra y evaluar resultados sin modificar predicciones pasadas. Para apostar, primero resolver identidades afectadas, reunir la evidencia prospectiva exigida y verificar ejecución, límites de exposición y supervisión. No ampliar mercados ni activar clima, viajes o penalizaciones manuales para compensar falta de evidencia.

La nueva herramienta se entrega como `scripts/reviewed_forecasts.py`, con su capturador acotado y pruebas. Solo acepta las ediciones/fuentes revisadas del 19-oct-2026: **no es un adaptador universal ni un servicio diario automático**. Otra fecha o torneo requiere revisar su documento y estructura; no se reutiliza el mismo programa cambiando únicamente la fecha.

Fuentes de programas: [Almaty ATP](https://www.protennislive.com/posting/2026/9410/op.pdf), [Bruselas ATP](https://www.protennislive.com/posting/2026/7485/op.pdf), [Osaka WTA](https://wtafiles.wtatennis.com/pdf/draws/2026/405/OP.pdf), [Ningbo WTA](https://wtafiles.wtatennis.com/pdf/draws/2026/2092/OP.pdf). Las copias originales consultadas y sus imágenes están archivadas; los enlaces públicos pueden actualizarse.
