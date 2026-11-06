# Regla de publicación NBA y tenis (5-nov-2026)

Decisión del titular: la regla vive en el servidor; la app solo pinta. Cuota mínima 1,20.

- Módulo: `src/qf/publish/regla_publicacion.py` (copia aislada en `apps/nba/src/nba/api/publicacion.py`; mantener iguales).
- Regla: sin props de jugador NBA; cuota de referencia ≥ 1,20; probabilidad 78–95 %; un lado por línea; 1 por familia y partido.
- NBA: `/nba/v1/partido/{id}/mercados` marca cada mercado con `publicable`. Tenis: `/web/deportes/tenis/cuotas` trae `publicables` {evento: [mercados]}.
- Umbrales por entorno (reinicio): QF_PUB_PROB_MIN, QF_PUB_PROB_MAX, QF_PUB_PRICE_MIN, QF_PUB_EXCLUDE, QF_PUB_PER_FAMILY.
- Medición (14.509 resueltos, fútbol 6 días, NBA 2 días/18 partidos): prob ≥ .78 y cuota ≥ 1,20 → ~81 % (LB95 ~77 %). Sin cuota mínima ~92 % pero con cuotas ~1,05. Props NBA: modelo ~67 %, real 49–61 %.
- Sin desplegar. Fútbol no cambia (ya filtra 73–95 % en el servidor). Re-medir semanalmente.
