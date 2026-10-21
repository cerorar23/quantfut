# Cobertura histórica de tenis: ampliación del 18 de octubre de 2026

Las tres colas originales quedaron resueltas: 52 ediciones individuales enlazadas con evidencia de su temporada, 17 recintos georreferenciados y 233 bloques por equipos revisados. Esto completa aquella revisión; todavía no completa toda la geografía ni demuestra una mejora predictiva del motor.

## Resultado reproducido

| Indicador | Resultado |
|---|---:|
| Partidos objetivo de 2024/2025 | 11.240 |
| Partidos con identidad de sede | 11.240 (100 %) |
| Partidos con coordenadas de destino | 10.510 (93,51 %) |
| Partidos con variables espaciales completas para ambos jugadores | 6.126 |
| Cohorte apta, tras filtros de resultado y partición | 5.798 (51,58 %) |
| Cohorte anterior reproducida con el código actualizado | 2.982 (26,53 %) |
| Aptos excluyendo referencias de recinto de más de 1 km de tolerancia | 5.569 |
| Fuentes archivadas y verificadas por huella | 280 |
| Bloques de fuente / bloques de competición indivisibles | 472 / 384 |

La cohorte apta contiene 2.965 partidos de desarrollo 2024 (ATP 1.264; WTA 1.701) y 2.833 exploratorios de 2025 (ATP 1.264; WTA 1.569). Se mantienen 201 partidos en cuarentena de frontera temporal. Los 5.798 son partidos con datos aptos, no una intersección de predicciones ya evaluada.

## Qué se resolvió

Las 52 ediciones WTA antes sin enlace tienen ahora evidencia específica de 2024 o 2025. Se archivaron 36 PDF válidos de torneos; el resto utiliza publicaciones de organizadores, gobiernos, WTA y extractos del lector web. Palermo 2024 y Cleveland 2025 tienen extractos de PDF obtenidos mediante el lector web, no PDF originales descargados. Hua Hin 2024 utiliza un extracto gubernamental. Seúl 2024 combina evidencia de edición y corroboración estructurada: esa calidad se distingue en el registro. No se reinterpretan errores HTTP como descargas válidas.

Los 17 recintos originales son Kempes, SMU, Santiago, Marrakech, Mallorca, Devonshire, Båstad, Gstaad, Atlanta, Umag, Jiujiang, Nautica, Bogotá, Guadalajara, Praga, Homburg y Ciric. Todos tienen referencia WGS84, zona horaria y elevación de terreno. La elevación procede de Open-Meteo/Copernicus GLO-90; no es una medición topográfica de la pista.

Las coordenadas conservan tolerancia y procedencia. Córdoba/Kempes es una referencia al complejo con tolerancia de 1.800 m; Jiujiang, de 1.600 m. Nautica/Jacobs Pavilion conserva 700 m para pistas temporales. No se presentan como centros de pista medidos. Se descartaron coordenadas urbanas genéricas, un estadio de fútbol próximo y coordenadas GCJ-02 sin conversión verificable. La sensibilidad puede excluir `coarse_venue_reference_used`.

Los 233 bloques por equipos se desglosan en 225 bloques bilaterales de Davis, dos ediciones de finales BJK y seis bloques multicidad con 178 enlaces por partido. No quedan partidos sin identidad de sede en esa revisión. United Cup se enlaza por sede de grupo y ronda de cada edición; BJK por eliminatoria. Los partidos de una misma competición ITF comparten `comparison_block_id` para impedir que distintos rubbers de la misma competición se repartan entre entrenamiento y evaluación.

Se documentaron seis revisiones conservando los originales: un identificador Davis Suecia/Argentina corresponde por jugadores y eliminatoria oficial a Suecia/Australia; dos partidos United Cup 2025 figuraban como fase de grupos y corresponden a semifinales en Sydney; en tres cruces BJK el país del perfil de la jugadora difiere del país representado. Esto último no se trata como cambio de nacionalidad: el enlace usa la representación acreditada en la eliminatoria. No se reescriben los CSV de origen.

## Cobertura que sigue faltando

Al identificar las 52 ediciones y las eliminatorias aparecieron otras sedes. El registro ampliado contiene 240 entradas de sede, incluidas entradas equivalentes de una misma instalación: 152 tienen coordenadas y 88 aún no. Esas 88 no son los 17 recintos de la cola original; la ampliación las deja explícitas. Afectan a 730 partidos de destino. La cola de ediciones afectadas está en `pending_editions.json` y contiene 154 bloques de fuente; una sede puede abarcar varios bloques.

También falta localizar antecedentes, especialmente historia 2023, qualies y challengers, y resolver periodos solapados. El motor no salta un antecedente desconocido para escoger otro más lejano que sí tenga sede. Si un jugador tiene varias sedes observadas en la competición anterior, conserva origen ambiguo. Por eso la cobertura de destino del 93,51 % no implica una cobertura de transiciones del 93,51 %.

## Protección temporal y próximos cálculos

Este es un conjunto retrospectivo: las fuentes se recibieron realmente en octubre de 2026. No se simula que estuvieran disponibles antes de los partidos. 2025 sigue siendo exploratorio; no es un holdout intacto. La guarda de periodos de fuente y las particiones por competición completa permanecen activas. La última sede observada no prueba el itinerario, fecha de llegada, eliminación definitiva incluyendo dobles ni descanso exacto. No se imputaron horas.

No se ajustaron modelos ni se modificaron probabilidades. Log-Loss, Brier y calibración quedan pendientes de la comparación Base/Base + Espaciales sobre la misma intersección de predicciones válidas, con ajuste exclusivamente en entrenamiento. Conviene incluir la sensibilidad de 5.569 partidos sin referencias geográficas amplias. ROI y CLV requieren cuotas históricas ejecutables y reglas de liquidación; no se infieren de esta cobertura.

## Archivos y reproducción

El resultado separado se guarda en `data/tennis/historical_coverage_20261018/`: registro, fuentes originales y recibos, conjunto completo, cohorte apta, catálogo, cola pendiente, particiones, informe y `delivery_audit.json`. La etapa anterior permanece en `historical_venues_20261018/`.

En el motor aislado `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis` se entregaron el módulo `tennis_engine/historical_dataset.py`, sus pruebas y los scripts de reconstrucción. Desde la raíz del proyecto, usando el Python del entorno y los archivos ya archivados:

```powershell
& ./.venv/Scripts/python.exe 'C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/scripts/build_coverage_registry.py'
& ./.venv/Scripts/python.exe 'C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/scripts/prepare_historical_dataset.py' --registry data/tennis/historical_coverage_20261018/registry.json --canonical data/tennis/full_20261016/canonical/matches.parquet --raw-root data/tennis/full_20261016/tml/originals --output data/tennis/historical_coverage_20261018
```

Ambos pasos son locales y no consumen créditos. El constructor necesita su auxiliar `coverage_team_completion.py` en el mismo directorio. Recrear los archivos actualiza la fecha del resultado y sus huellas; los recibos de adquisición conservan su fecha original.

Validación: 173 pruebas de tenis aprobadas; ocho pruebas nuevas cubren sedes por partido, procedencia multicidad, desconocidos, identidad canónica y partición indivisible. La auditoría verifica las fuentes, originales, las tres colas resueltas, la regresión de 2.982 partidos y los 12 artefactos congelados sin cambios. No se consumieron créditos de The Odds API ni se consultó API-Tennis. La consulta pública adicional de elevación agrupó 69 puntos.

La suite entregada volvió a aprobar sus 173 pruebas. La verificación general final del proyecto aprobó 1.308 pruebas, omitió 88 y emitió dos avisos; Docker no estaba disponible para su comprobación. La diferencia respecto a las 1.300 pruebas generales iniciales proviene de cambios de otra sesión. La revisión de formato de los cambios entregados también pasó.
