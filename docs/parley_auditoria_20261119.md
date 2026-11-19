# Auditoría del parley v2.1 y rediseño por probabilidad (19-nov-2026)

Pedido del titular: hay muchos parleys perdidos y la página enseña sobre todo «solo referencia». Todo lo de abajo se
midió en el VPS con lecturas (lotes del 7 al 18-nov).

## Qué se midió

| Escalón (cuota objetivo) | Probabilidad prometida | Real |
|---|---|---|
| 2,10 | 46 % | 5 de 10 |
| 3,10 | 30 % | 3 de 12 |
| 8,20 | 11 % | 0 de 11 |
| 12,10 | 7 % | 0 de 9 |
| Total | 24 % | 8 de 42, ROI −53,6 % (resumen público) |

- **Las probabilidades se cumplen; el diseño falla.** El artefacto «aprobado» usa `metodo: mercado` en sus 15
  categorías: la p de cada pata es el consenso de casas sin margen. Con una cuota objetivo fija, el boleto acierta
  ≈ 1/cuota y ningún filtro lo cambia. 8,20 y 12,10 están hechos para perder 9 de cada 10 veces.
- El tenis ocupa 86 de 121 patas diarias, a una cuota media de 1,93 (una moneda al aire). El fútbol solo entra con
  1X2, hándicap y totales: la doble oportunidad y los goles por equipo son «sin_medir» en el artefacto y el filtro
  por categoría los descarta.
- `alta_prob_ext` (fútbol, desde el 1-oct, n = 4.931) está calibrado: promete 76,4 % y acierta 76,7 %. Sobrepromete
  ambos marcan (65,9 % frente a 55,8 %) y córners (−8 % de rendimiento).
- Simulación sobre `alta_prob_ext`, con una pata por partido de 0,78 a 0,92 (hándicap, doble oportunidad, totales y
  1X2) y cuota ≥ 1,15: 2 patas aciertan 69 % a cuota 1,54 (26 días) y 3 patas, 54 % a 1,83 (24 días). La muestra es
  chica; el rendimiento positivo es ruido.

## Errores corregidos

1. **El lote NBA de varios partidos nunca se selló.** El CHECK `parley_v2_lotes_ambito_check` (db/098) solo admitía
   `diario` y `partido`, y el revisor sella `nba_dia`: dio 37 `CheckViolation`. Las pruebas no lo vieron porque
   simulan la base. Se corrige con `db/119`, y `tests/test_parley_prob.py` cruza ahora los ámbitos del código con el
   último CHECK.
2. **«Solo referencia» llenaba la página.** 76 de 124 boletos eran same-game NBA, que por diseño no pueden
   publicarse: no hay cuota del paquete ni modelo conjunto. `informe_publico_v2` solo enseña `diario` y `nba_dia` de
   la estrategia publicada. El same-game se sigue sellando.
3. **Dos cifras distintas en la web.** El héroe (`parleyV2View`) contaba los `solo_referencia` con una cuota que
   ninguna casa paga; el resumen del servidor no. Ahora la web cuenta solo `publicado`, como el servidor.
4. **19 patas sin liquidar.** Todas eran de tenis ITF/UTR (PropLine no los califica y SportsAPIPro casi nunca los
   trae) o de NBA. El parley ya no elige tenis fuera de ATP, WTA y Challenger, ni dobles (`parley_ext.tenis_liquidable`).
   Un partido aplazado pasa a nulo si una observación hecha ≥ 48 h después del inicio aún dice «aplazado»
   (`tenis_resultados.APLAZADO_NULO`). Las patas viejas que no tienen fuente siguen sin liquidar y avisan por Telegram
   a las 72 h; no se anulan a ciegas.
5. **El cron no corría desde `main`.** Usaba `releases/parley-v2-20261106` montado sobre
   `quantfut-worker-segura:53b1e5ed`. Se corrige al desplegar (ver `DEPLOYS.md`).

## Rediseño en sombra: `publish/parley_prob.py`

Primero la probabilidad del boleto y después la cuota.

| Nivel | Patas | p conjunta mínima | Cuota total mínima |
|---|---|---|---|
| Seguro | 2 | 0,60 | 1,40 |
| Medio | 3 | 0,45 | 1,80 |
| Arriesgado | 4 | 0,33 | 2,40 |

- **Patas:** p prudente entre 0,72 y 0,93, con cuota ≥ 1,15.
- **Mercados que cumplen lo prometido:**
  - Fútbol: 1X2, doble oportunidad, hándicap, totales y goles por equipo.
  - NBA: ganador, hándicap, totales, puntos, rebotes y triples.
  - Tenis: ganador solo con p ≥ 0,75, más juegos y hándicap.
- **Fuera:** ambos marcan, córners, tarjetas y asistencias NBA (58 % frente a 71 % prometido, n = 24).
- **Búsqueda:** máxima probabilidad conjunta, con una pata por evento y sin repetir eventos entre niveles; se resuelve
  del nivel seguro al arriesgado.
- **Dónde se guarda:** en el mismo sellado y la misma cadena que el v2, con su propia estrategia
  (`parley_probabilidad`, `v3-sombra`) y ámbito (`sombra`, `sombra_nba`). Los boletos quedan `solo_referencia`, la
  liquidación los cierra como al v2 y la API no los publica.
- **Qué patas recibe:** las del v2 antes del filtro por categoría. Usa la p prudente del artefacto si existe y, si
  no, la del consenso de casas.
- **Puerta para sustituir el v2:** ≥ 30 días de sombra con el acierto real dentro de lo prometido en cada nivel. Se
  consulta con `python -m qf.publish.parley_v2_datos comparar 30`.
- **Lo que no se promete:** acertar más seguido baja la cuota de cada boleto. Con probabilidades de mercado no hay
  ventaja a largo plazo; el objetivo es que se cumpla lo que se promete y que se acierte más a menudo.

En el NBA multipartido, la sombra no revalida a los jugadores de sus propias patas: solo se quitan las que el v2
ya descartó.
