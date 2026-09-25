"""
Chequeo diario de salud. El seguro contra el fallo silencioso.

El escenario que esto previene: FBref cambia su HTML o API-Football cambia un
ID de liga, tu scraper devuelve 0 filas con status 200, el modelo sigue
entrenando con datos congelados y te enteras tres meses después mirando por
qué el CLV se hundió.

Cada chequeo devuelve (ok, mensaje). Si alguno falla, va a Telegram.
"""
from __future__ import annotations

import logging

from ..db import query

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
        return False, (f"Sin NINGUNA baja reportada en {INJURIES_MIN_MATCHES}+ "
                       "partidos comprobados de: " + ", ".join(nuevos)
                       + " (mismo patrón de cobertura silenciosa que ya tienen "
                       "mx.liga_mx/ar.primera/pt.primeira, ver README.md)")
    activos = {r["league_id"] for r in rows}
    conocidos = KNOWN_INJURY_COVERAGE_GAPS & activos
    msg = "Cobertura de bajas OK"
    if conocidos:
        msg += f" ({len(conocidos)} liga(s) con hueco ya conocido, ver README.md)"
    return True, msg


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
    ("liquidación", check_settlement_lag),
    ("modelo activo", check_model_freshness),
]


def run(alert_on_fail: bool = True) -> dict:
    results, failures = [], []
    for name, fn in CHECKS:
        try:
            ok, msg = fn()
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, f"el chequeo falló: {exc}"
        results.append({"check": name, "ok": ok, "message": msg})
        if not ok:
            failures.append(f"• {name}: {msg}")

    if failures and alert_on_fail:
        from ..publish.telegram import alert
        alert("Chequeo diario con fallos:\n" + "\n".join(failures))

    return {"ok": not failures, "results": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run()
    for r in res["results"]:
        print(f"{'OK   ' if r['ok'] else 'FALLO'} {r['check']:24s} {r['message']}")
    raise SystemExit(0 if res["ok"] else 1)
