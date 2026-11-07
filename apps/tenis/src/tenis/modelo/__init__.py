"""Modelo de tenis v2 (plan §D): pieza R (rating de resultados con superficie y fatiga), pieza P (puntos al
saque/resto), pieza C (unión por inversión), recalibración opcional, línea base Elo y evaluación walk-forward.

Reglas transversales: el mercado nunca entra; los ids de jugador son CLAVES (se convierten a índices internos y nunca
a rasgos); faltante ≠ 0; un formato desconocido no se pronostica; el filtro consume los resultados en el orden de
`visible_resultado_utc` y nunca usa un evento con visibilidad ≥ corte del partido.
"""
