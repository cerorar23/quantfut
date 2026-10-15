# F2 — Cierres de Pinnacle: football-data y The Odds API (15-oct-2026)

Código: `src/qf/ingest/history_fd.py` (`completar_cierres`, `cargar_ternas`, `insertar_cierre`) y
`src/qf/ingest/cierres_odds_api.py`. Plan: [2026-10-14-f2-cierres-pinnacle.md](superpowers/plans/2026-10-14-f2-cierres-pinnacle.md).

## Punto de partida
6.185 partidos terminados desde 2024 sin cierre de Pinnacle. Entre el 14 y el 15 de octubre otra
sesión cargó 2.918 reconstruidos de OddsPapi (`oddspapi_reconstructed`), dejando **3.267** (1.861 en
las 13 ligas modeladas).

## Football-data no aporta nada
Ensayo de solo lectura en producción: de 11.923 filas de Pinnacle de football-data desde 2024,
**las 11.923 ya estaban cargadas** (0 sin partido, 0 por insertar). Football-data dejó de traer
Pinnacle de Europa hacia enero de 2026. Quedó un emparejador por id de equipo (los clubes ascendidos
o descendidos tienen su fila en otra división) que se puede reejecutar si football-data cambia.

## The Odds API (histórico)
- Un snapshot de la región `eu` cuesta 10 créditos y sirve a todos los partidos de esa competición
  con la misma hora de inicio. Se pide el de 5 minutos antes del inicio.
- Un cierre solo se acepta si el snapshot está a ≤30 min del inicio y el precio de Pinnacle se
  actualizó ≤30 min antes del snapshot (`terna_de_evento`).
- Plan completo para las 13 modeladas: 1.328 snapshots = 13.280 créditos.
- **Fase 1 (15-oct):** 801 snapshots, 8.000 créditos, saldo 7.367 (el reparto estaba autorizado:
  ~8.000 antes del 1-nov con reserva de 6.000 para la captura en vivo).
- Cada respuesta se guarda en `/srv/quantfut/artifacts/odds_hist` antes de pagar la siguiente.

### Carga
Ensayo, integridad, respaldo y escritura:
- Emparejados 1.197 partidos, **1.164 cierres válidos** (6,9 créditos por cierre); 33 con precio
  demasiado antiguo y 92 partidos sin evento emparejado (casi todos nombres de Champions sin alias
  de The Odds API: Bayern München, Internazionale Milano, LOSC Lille, Young Boys...).
- **Integridad:** con esas cuotas sin margen el RPS es **0,1987** frente a 0,2357 de la
  probabilidad uniforme, coherente en todas las ligas (0,185-0,223). Margen medio 3,6 %; antigüedad
  mediana del precio 0,3 min.
- Respaldo: `~/backups/odds_snapshots_pre_f2b_20261015.sql.gz` (VPS, 5,1 MB, 454.486 líneas).
- Escritas 3.492 cuotas (1.164 × 3), `source='the_odds_api_hist'`. Segunda ejecución: 0.
  Todos sus partidos tienen exactamente 3 filas y ningún otro cierre. Modelo activo, predicciones
  (281) y picks (0) sin cambios; API 200.

## Estado de los huecos
| | Antes | Hoy |
|---|---|---|
| Sin cierre, todas las ligas | 3.267 | 2.103 |
| Sin cierre, 13 modeladas | 1.861 | **697** |

Por liga (modeladas): México 157, LaLiga 112, Serie A 112, Eredivisie 100, Primeira 97,
Champions 81, Europa League 22; el resto, ≤6. Los partidos de México, LaLiga, Serie A,
Eredivisie y Primeira son los **527 snapshots que faltan por comprar** (~5.270 créditos), previstos
tras la renovación del 1-nov. Champions y Europa League (103) esperan alias de nombres.

## Hallazgos ajenos a la carga
- **5.574 partidos de football-data tienen cada cuota de cierre duplicada** (filas idénticas del
  histórico antiguo, p. ej. 2017). No las creó esta carga; las consultas que toman la última fila no
  se ven afectadas. `odds_snapshots` no admite DELETE, así que se convive con ello.
- Las cuotas `oddspapi_reconstructed` están cortadas, en el 74 % de los casos, 60 minutos antes del
  inicio: no son cierres. **Filtradas el 15-oct (autorizado por el usuario, antes del reentrenamiento
  del 1-nov)**, ver la sección siguiente.

## F2c — Filtro del cierre reconstruido

`qf.eval.cierre.es_cierre_real()` es la regla única de las seis lecturas del cierre (`train.py` x2,
`eval/clv.py` x2, `model/shadow.py`, `publish/shadow_sharp.py` x2): se excluye una fila de
`oddspapi_reconstructed` con `mins_to_kickoff > 5`. Los 739 cortes al inicio se conservan y los 2.155 de
60 minutos quedan fuera del mercado de referencia y del CLV (siguen en la base como precio a la hora del XI,
útil para el futuro bloque `mercado`). Pruebas de comportamiento con Postgres real (entrenamiento, CLV y
liquidación en sombra) y una guarda sobre el código fuente; una mutación del filtro las hace fallar.

Efecto medido en producción: partidos de ligas modeladas con cierre completo de Pinnacle **49.951 → 48.338**
(se descartan 1.613 cierres de 60 min); un partido solo con cierre T-60 ya no devuelve cierre ni en CLV ni en la
liquidación en sombra.

**Despliegue (solo worker, donde corre el reentrenamiento):** `docker cp` de `eval/cierre.py`, `eval/clv.py`,
`model/train.py`, `model/shadow.py` y `publish/shadow_sharp.py` el 15-oct; hashes verificados contra el
repositorio. Respaldo de lo anterior y de lo nuevo en `~/quantfut/deployments/f2c-filtro-cierre/{antes,despues}`.
Vuelta atrás: copiar `antes/` de vuelta con `docker cp`. Cambia el contenedor, no la imagen: **un
`docker compose up --force-recreate` o una reconstrucción lo pierde.**

**La API NO se tocó:** su `train.py` y su `clv.py` (y las del árbol `~/quantfut/src`) son versiones más antiguas
que las del repositorio y el worker (faltan `alta_prob_ext`, `tarjetas_seg`, `parley` y `xg_source`). Reconstruir
cualquier imagen desde ese árbol sin sincronizarlo antes revertiría código.
