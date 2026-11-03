# NBA: plantillas actuales y fuerza individual — 26-oct-2026

Solicitud: corregir y recalibrar el modelo en vivo para reflejar altas, bajas y cambios de equipo, especialmente estrellas y arranque de temporada.

Base: commit `03f4ada`, productor 1.5.0. La copia inicial del chat era antigua; se trabaja en una copia aislada de la versión actual.

1. Verificar y archivar plantillas NBA actuales con IDs oficiales, temporada, recepción real y hash. Una pertenencia actual no acredita disponibilidad ni minutos.
2. Resolver pertenencia de jugadores por esa evidencia en vez del último equipo de su historial. Conservar su historial individual a través de traspasos; excluir al jugador del equipo que deja incluso si aún no debutó en el nuevo.
3. Ajustar un candidato de fuerza de jugadores y rotación, con minutos limitados a 240 por equipo; medir ganador, puntos de equipo y total frente al productor. El valor de un jugador no será el Elo de su antiguo equipo.
4. Validación cronológica: ajuste/selección en 2024-25 y evaluación descriptiva en 2025-26 (ya observada en otras investigaciones). Ninguna fila del mismo día o futura entra en las variables. Sin plantillas históricas previas al primer partido no se atribuye cobertura retrospectiva de traspasos de verano antes del debut.
5. Ejecutar pruebas de traspaso al rival, salida/llegada de estrella, pertenencia duplicada/temporada caducada/recepción tardía, minutos y fuga temporal; guardar parámetros, métricas e insumos.
6. Integrar únicamente correcciones verificadas y candidatos con evidencia. Antes de desplegar: comparar servidor/base, protocolo versionado, modelo ajustado con el código exacto, ensayo y reversión en DEPLOYS.md. Las cohortes ya selladas permanecen intactas.
