"""
Chequeo diario de salud. El seguro contra el fallo silencioso.

El escenario que esto previene: FBref cambia su HTML o API-Football cambia un
ID de liga, tu scraper devuelve 0 filas con status 200, el modelo sigue
entrenando con datos congelados y te enteras tres meses después mirando por
qué el CLV se hundió.

Cada chequeo devuelve (ok, mensaje). Si alguno falla, va al chat privado de
alertas de Telegram (`TG_ALERT_CHAT`); el cron guarda además cada pasada en
`health_runs`.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

from ..db import execute, query

log = logging.getLogger(__name__)


# Mismo horizonte que ingiere `fixtures.run(days_ahead=21)`. Ver el docstring.
HORIZON_DAYS = 21


def check_fixtures_horizon() -> tuple[bool, str]:
    """
    Debe haber partidos programados en los próximos días.

    Solo se avisa de una competición que ESTÉ EN JUEGO, es decir, que tenga
    algún partido terminado en las últimas 3 semanas. Sin esa condición la
    alerta salta siempre: la MLS para todo el invierno y las copas europeas
    tienen huecos de meses entre eliminatorias. Una alerta que salta cada día
    por algo normal se deja de leer, y entonces tampoco se lee el día que sí
    significa que la ingesta está rota.

    El horizonte es el MISMO que ingiere `fixtures.run(days_ahead=21)`, y no
    uno más corto. Con 10 días la alerta saltaba en 10 competiciones a la vez
    cada parón de selecciones (medido el 2026-09-22: con el calendario recién
    ingerido y correcto, todas las ligas europeas más Brasil y Argentina
    tenían su próximo partido pasados esos 10 días). Preguntar por una ventana
    más corta que la que se ingiere no puede distinguir "no hay partidos" de
    "no se han traído": solo puede dar falsos positivos.
    """
    rows = query(
        """SELECT l.league_id,
                  count(m.match_id) FILTER (
                      WHERE m.kickoff_utc BETWEEN now()
                                             AND now() + make_interval(days => %s)
                        AND m.status = 'scheduled') AS upcoming,
                  count(m.match_id) FILTER (
                      WHERE m.kickoff_utc BETWEEN now() - interval '21 days' AND now()
                        AND m.status = 'finished') AS recientes
           FROM leagues l LEFT JOIN matches m ON m.league_id = l.league_id
           WHERE l.active GROUP BY l.league_id""",
        (HORIZON_DAYS,),
    )
    activas = [r for r in rows if r["recientes"] > 0]
    empty = [r["league_id"] for r in activas if r["upcoming"] == 0]
    if empty:
        return False, (f"Sin partidos programados en {HORIZON_DAYS} días para: "
                       + ", ".join(empty)
                       + " (puede ser parón de selecciones o ingesta rota)")
    paradas = len(rows) - len(activas)
    return True, (f"Calendario OK en {len(activas)} competiciones en juego"
                  + (f" ({paradas} fuera de temporada)" if paradas else ""))


def check_orphan_matches() -> tuple[bool, str]:
    """Partidos que pasaron hace rato y siguen sin cerrar."""
    n = query(
        """SELECT count(*) AS n FROM matches
           WHERE status IN ('scheduled', 'live')
             AND kickoff_utc < now() - interval '8 hours'
             AND kickoff_utc > now() - interval '30 days'"""
    )[0]["n"]
    if n > 3:
        return False, f"{n} partidos terminaron hace >8h y siguen abiertos"
    return True, f"{n} partidos huérfanos (tolerable)"


def check_odds_freshness() -> tuple[bool, str]:
    """El worker de cuotas tiene que haber escrito algo recientemente."""
    row = query(
        "SELECT max(captured_at) AS last FROM odds_snapshots "
        "WHERE source = 'the_odds_api'"
    )[0]
    if not row["last"]:
        return False, "Nunca se han capturado cuotas en vivo"
    hrs = query(
        "SELECT EXTRACT(EPOCH FROM (now() - %s)) / 3600 AS h", (row["last"],)
    )[0]["h"]
    if hrs > 24:
        return False, f"Última captura de cuotas hace {hrs:.0f} horas"
    return True, f"Cuotas frescas (hace {hrs:.1f} h)"


def check_unresolved_names() -> tuple[bool, str]:
    """
    Solo alarma lo que se puede arreglar. Un nombre visto únicamente en una
    copa europea es un club de una liga fuera del catálogo: irresoluble por
    diseño (nunca se da de alta bajo `eu.ucl`/`eu.uel`). Contarlo dejaba la
    alarma en rojo para siempre. Sin competición anotada, alarma: no se sabe.
    """
    rows = query(
        """SELECT count(*) FILTER (WHERE NOT coalesce(l.cross_league, FALSE)) AS n,
                  sum(u.occurrences) FILTER (WHERE NOT coalesce(l.cross_league, FALSE))
                      AS occ,
                  count(*) FILTER (WHERE l.cross_league) AS copa
           FROM unresolved_names u
           LEFT JOIN leagues l USING (league_id)
           WHERE NOT u.resolved"""
    )[0]
    copa = int(rows["copa"] or 0)
    nota = (f"; {copa} de clubes fuera del catálogo en copas europeas "
            "(esperado)") if copa else ""
    if (rows["n"] or 0) > 0:
        return False, (f"{rows['n']} nombres sin emparejar "
                       f"({rows['occ']} apariciones){nota}. Corre "
                       "scripts/bootstrap_aliases.py")
    return True, f"Todos los nombres emparejados{nota}"


def check_settlement_lag() -> tuple[bool, str]:
    """Picks de partidos ya terminados que siguen sin liquidar."""
    n = query(
        """SELECT count(*) AS n FROM picks p
           JOIN matches m USING (match_id)
           LEFT JOIN pick_results r USING (pick_id)
           WHERE r.pick_id IS NULL AND m.status = 'finished'
             AND m.kickoff_utc < now() - interval '12 hours'"""
    )[0]["n"]
    if n > 0:
        return False, f"{n} picks sin liquidar de partidos ya terminados"
    return True, "Liquidación al día"


INJURIES_LOOKBACK_DAYS = 30

# Bajo esta muestra, cero bajas reportadas es normal (racha de suerte, liga
# recién arrancada). A partir de aquí, cero en TODOS los partidos comprobados
# de una liga entera dentro de un mes deja de ser plausible y es la misma
# firma de "array vacío con status 200" que ya se documentó para el xG de
# este proveedor.
INJURIES_MIN_MATCHES = 15

# Confirmado 2026-09-22 (ver README.md): estas tres devuelven 0 en la
# temporada 2026 en curso pese a tener partidos de sobra terminados, con
# season=2025 sí hay datos. Es un hueco de cobertura del proveedor, no un
# fallo de ingesta, así que no tiene sentido alertar cada día por algo que
# ya se investigó y no se puede arreglar desde este lado.
KNOWN_INJURY_COVERAGE_GAPS = {"mx.liga_mx", "ar.primera", "pt.primeira"}


def check_injuries_coverage() -> tuple[bool, str]:
    """
    Detecta el mismo fallo silencioso de API-Football ya visto en el xG:
    una liga sin cobertura para `/injuries` no da error, da 0 resultados con
    status 200. Sin este chequeo, una liga nueva con ese mismo hueco pasaría
    desapercibida hasta que alguien note que su feature de disponibilidad
    siempre está vacía.

    No se dispara con muestra pequeña (`INJURIES_MIN_MATCHES`): un partido o
    dos sin bajas es lo normal, no un indicio de nada. Las ligas ya
    confirmadas como huecas (`KNOWN_INJURY_COVERAGE_GAPS`) no alertan de
    nuevo cada día, solo se cuentan en el mensaje.
    """
    rows = query(
        """SELECT m.league_id,
                  count(DISTINCT c.match_id) AS checked,
                  coalesce(sum(c.n_reported), 0) AS total_reported
           FROM injuries_capture_log c
           JOIN matches m ON m.match_id = c.match_id
           WHERE c.captured_at > now() - make_interval(days => %s)
           GROUP BY m.league_id""",
        (INJURIES_LOOKBACK_DAYS,),
    )
    nuevos = [r["league_id"] for r in rows
              if r["checked"] >= INJURIES_MIN_MATCHES and r["total_reported"] == 0
              and r["league_id"] not in KNOWN_INJURY_COVERAGE_GAPS]
    if nuevos:
        # Del 22-sep al 2-oct-2026 esta alerta saltó por un error nuestro
        # (las bajas se descartaban al asignarlas a un lado), no del
        # proveedor: el mensaje no debe dar por hecho ninguna de las dos.
        return False, (f"Sin NINGUNA baja guardada en {INJURIES_MIN_MATCHES}+ "
                       "partidos comprobados de: " + ", ".join(nuevos)
                       + ". Antes de darlo por hueco del proveedor, descartar "
                       "un error nuestro: pedir /injuries de un partido y "
                       "comparar con lo guardado en `injuries`")
    activos = {r["league_id"] for r in rows}
    conocidos = KNOWN_INJURY_COVERAGE_GAPS & activos
    msg = "Cobertura de bajas OK"
    if conocidos:
        msg += f" ({len(conocidos)} liga(s) con hueco ya conocido, ver README.md)"
    return True, msg


# Una liga con partidos jugados en los últimos XG_RECENT_DAYS cuyo último xG
# es más viejo que XG_MAX_GAP_DAYS está "parada". La fuente publica por lotes
# semanales, así que tres semanas ya no son un retraso normal.
XG_RECENT_DAYS = 30
XG_MAX_GAP_DAYS = 21

# Paradas ya el 2-oct-2026 (worldfootballR_data sin actualizar desde el
# 18-sep-2025; ver README). Reconocidas, no olvidadas: dejan de fallar solo
# hasta esta fecha, para que la decisión sobre la fuente de xG (tareas.md) no
# se quede sin tomar. Una liga que se pare DESPUÉS falla en el acto.
XG_PARADO_CONOCIDO = {
    "ar.primera", "br.serie_a", "de.bundesliga", "es.laliga", "eu.ucl",
    "eu.uel", "fr.ligue_1", "gb.premier_league", "it.serie_a", "mx.liga_mx",
    "nl.eredivisie", "pt.primeira", "us.mls",
}
XG_PARADO_RECONOCIDO_HASTA = date(2026, 11, 1)


def check_xg_freshness(now: datetime | None = None) -> tuple[bool, str]:
    """
    El job semanal del xG respondía `ok` con 0 filas mientras su fuente
    llevaba un año sin publicar. Esto mira el dato, no el job.
    """
    now = now or datetime.now(timezone.utc)
    rows = query(
        """SELECT m.league_id,
                  max(m.kickoff_utc) FILTER (WHERE m.status = 'finished')
                      AS ult_jugado,
                  max(m.kickoff_utc) FILTER (WHERE m.home_xg IS NOT NULL)
                      AS ult_xg
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id AND l.model_enabled
           GROUP BY m.league_id"""
    )
    # Una liga que nunca tuvo xG y no tiene fuente no se ha "parado": no hay
    # nada que vigilar (las 10 activadas el 2026-10-11 se entrenan con goles).
    from .xg_worldfootball import ASSETS, RDS_ASSETS
    con_fuente = set(ASSETS) | set(RDS_ASSETS) | XG_PARADO_CONOCIDO
    parados = []
    for r in rows:
        jugado, xg = r["ult_jugado"], r["ult_xg"]
        if jugado is None or (now - jugado).days > XG_RECENT_DAYS:
            continue
        if xg is None and r["league_id"] not in con_fuente:
            continue
        if xg is None or (jugado - xg).days > XG_MAX_GAP_DAYS:
            parados.append(r["league_id"])
    reconocidos = sorted(set(parados) & XG_PARADO_CONOCIDO)
    nuevos = sorted(set(parados) - XG_PARADO_CONOCIDO)
    vigente = now.date() <= XG_PARADO_RECONOCIDO_HASTA
    if nuevos or (reconocidos and not vigente):
        malos = nuevos + ([] if vigente else reconocidos)
        return False, (f"xG parado (>{XG_MAX_GAP_DAYS} días sin xG con partidos "
                       f"jugados) en: {', '.join(malos)}")
    if reconocidos:
        return True, (f"xG parado en {len(reconocidos)} liga(s) reconocida(s) "
                      f"hasta {XG_PARADO_RECONOCIDO_HASTA:%d-%m-%Y}, pendiente de "
                      f"decidir fuente: {', '.join(reconocidos)}")
    return True, "xG al día"


def check_model_freshness() -> tuple[bool, str]:
    row = query(
        """SELECT model_version,
                  EXTRACT(EPOCH FROM (now() - trained_at)) / 86400 AS days
           FROM model_artifacts WHERE is_active LIMIT 1"""
    )
    if not row:
        return False, "No hay ningún modelo activo"
    d = row[0]["days"]
    if d > 45:
        return False, f"Modelo {row[0]['model_version']} entrenado hace {d:.0f} días"
    return True, f"Modelo {row[0]['model_version']} ({d:.0f} días)"


CHECKS = [
    ("calendario", check_fixtures_horizon),
    ("partidos huérfanos", check_orphan_matches),
    ("frescura de cuotas", check_odds_freshness),
    ("nombres sin emparejar", check_unresolved_names),
    ("cobertura de bajas", check_injuries_coverage),
    ("frescura del xG", check_xg_freshness),
    ("liquidación", check_settlement_lag),
    ("modelo activo", check_model_freshness),
]


def _persist(ok: bool, results: list[dict]) -> None:
    execute("INSERT INTO health_runs (ok, results) VALUES (%s, %s)",
            (ok, json.dumps(results, ensure_ascii=False)))


def run(alert_on_fail: bool = True, persist: bool = False) -> dict:
    """
    `persist` solo desde el cron diario: el panel y /admin/health calculan la
    salud al vuelo y no deben llenar el historial.
    """
    results, failures = [], []
    for name, fn in CHECKS:
        try:
            ok, msg = fn()
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, f"el chequeo falló: {exc}"
        results.append({"check": name, "ok": ok, "message": msg})
        if not ok:
            failures.append(f"• {name}: {msg}")

    if persist:
        # El log del cron vive dentro del contenedor y se pierde en cada
        # despliegue: el historial va a la base (db/037).
        try:
            _persist(not failures, results)
        except Exception as exc:  # noqa: BLE001 — que no tape la alerta
            log.error("No se pudo guardar el chequeo diario: %s", exc)
            failures.append(f"• historial de salud: no se pudo guardar ({exc})")

    if failures and alert_on_fail:
        from ..publish.telegram import alert
        alert("Chequeo diario con fallos:\n" + "\n".join(failures))

    return {"ok": not failures, "results": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run(persist=True)
    for r in res["results"]:
        print(f"{'OK   ' if r['ok'] else 'FALLO'} {r['check']:24s} {r['message']}")
    raise SystemExit(0 if res["ok"] else 1)
