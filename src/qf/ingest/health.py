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
    """Partidos que pasaron hace rato y siguen sin cerrar (solo de competiciones activas)."""
    n = query(
        """SELECT count(*) AS n FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active
           WHERE m.status IN ('scheduled', 'live')
             AND m.kickoff_utc < now() - interval '8 hours'
             AND m.kickoff_utc > now() - interval '30 days'"""
    )[0]["n"]
    if n > 3:
        return False, f"{n} partidos terminaron hace >8h y siguen abiertos"
    return True, f"{n} partidos huérfanos (tolerable)"


def check_odds_freshness() -> tuple[bool, str]:
    """El worker de cuotas tiene que haber escrito algo recientemente, del proveedor activo."""
    from ..config import settings
    row = query(
        "SELECT max(captured_at) AS last FROM odds_snapshots WHERE source = %s",
        (settings.odds_provider,),
    )[0]
    if not row["last"]:
        return False, "Nunca se han capturado cuotas en vivo"
    hrs = query(
        "SELECT EXTRACT(EPOCH FROM (now() - %s)) / 3600 AS h", (row["last"],)
    )[0]["h"]
    # PropLine archiva cada hora: seis horas sin filas ya es un recolector parado.
    limite = 6 if settings.odds_provider == "propline" else 24
    if hrs > limite:
        return False, f"Última captura de cuotas hace {hrs:.0f} horas"
    return True, f"Cuotas frescas (hace {hrs:.1f} h)"


CIERRE_MIN_PARTIDOS = 10
CIERRE_MIN_COBERTURA = 0.5


def check_closing_coverage() -> tuple[bool, str]:
    """
    Los partidos ya jugados tienen que tener el cierre de Pinnacle (`window_tag='close'`).
    Del 22 al 25-oct-2026 no entró ninguno (PropLine los archivaba, nadie los cargaba) y el
    chequeo seguía en verde: CLV, sombra y la puerta comercial se quedaron sin muestra.
    La ventana empieza a las 12 h porque `propline_cierres` espera 6 h tras el saque.
    """
    from ..config import settings
    from ..eval.cierre import es_cierre_real
    row = query(
        f"""SELECT count(*) AS n,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM odds_snapshots o
                       WHERE o.match_id = m.match_id AND o.bookmaker = %s AND o.market = 'h2h'
                         AND o.window_tag = 'close' AND {es_cierre_real("o")})) AS con_cierre
            FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active
            WHERE m.status = 'finished'
              AND m.kickoff_utc BETWEEN now() - interval '3 days' AND now() - interval '12 hours'""",
        (settings.sharp_book,),
    )[0]
    n, con = int(row["n"] or 0), int(row["con_cierre"] or 0)
    if n < CIERRE_MIN_PARTIDOS:
        return True, f"Cierres: solo {n} partidos jugados en la ventana"
    if con / n < CIERRE_MIN_COBERTURA:
        return False, (f"Cierre de {settings.sharp_book} en {con} de {n} partidos jugados (12 h a 3 días): "
                       "revisar propline_cierres")
    return True, f"Cierre de {settings.sharp_book} en {con} de {n} partidos jugados"


def check_results_freshness() -> tuple[bool, str]:
    """
    Con partidos jugados hace más de 8 h tiene que haber resultados recientes.
    El 22-oct-2026 API-Football pasó al plan gratuito: cada consulta devolvía
    200 con un error de plan y el chequeo seguía diciendo «liquidación al día»,
    porque sin partidos cerrados no hay nada que liquidar.
    """
    row = query(
        """SELECT (SELECT max(result_recorded_at) FROM matches) AS ultimo,
                  (SELECT count(*) FROM matches
                    WHERE kickoff_utc BETWEEN now() - interval '3 days'
                                          AND now() - interval '8 hours') AS jugados"""
    )[0]
    if not row["jugados"]:
        return True, "Sin partidos jugados en los últimos 3 días"
    if row["ultimo"] is None:
        return False, "Nunca se ha registrado un resultado"
    hrs = query("SELECT EXTRACT(EPOCH FROM (now() - %s)) / 3600 AS h", (row["ultimo"],))[0]["h"]
    if hrs > 24:
        return False, (f"Ningún resultado nuevo en {hrs:.0f} h con {row['jugados']} partidos "
                       "jugados: revisar el proveedor de resultados")
    return True, f"Resultados al día (último hace {hrs:.1f} h)"


def check_unresolved_names() -> tuple[bool, str]:
    """
    Solo alarma lo que se puede arreglar. Un nombre visto únicamente en una
    copa europea es un club de una liga fuera del catálogo: irresoluble por
    diseño (nunca se da de alta bajo `eu.ucl`/`eu.uel`). Contarlo dejaba la
    alarma en rojo para siempre. Sin competición anotada, alarma: no se sabe.
    """
    # Solo competiciones activas y nombres vistos en las dos últimas semanas: un nombre de una
    # liga retirada (Ligue 2, Superliga danesa...) o que ya no aparece en ningún feed no se
    # puede ni hace falta arreglar, y mantenía la alarma en rojo cada día.
    rows = query(
        """SELECT count(*) FILTER (WHERE NOT coalesce(l.cross_league, FALSE)) AS n,
                  sum(u.occurrences) FILTER (WHERE NOT coalesce(l.cross_league, FALSE))
                      AS occ,
                  count(*) FILTER (WHERE l.cross_league) AS copa
           FROM unresolved_names u
           LEFT JOIN leagues l USING (league_id)
           WHERE NOT u.resolved AND (l.league_id IS NULL OR l.active)
             AND u.last_seen > now() - interval '14 days'"""
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


def check_injuries_coverage() -> tuple[bool, str]:
    """
    Cobertura de bajas y once de los partidos próximos. Desde el 25-oct-2026 llegan
    de SofaScore y FotMob (db/087); ver `check_sofascore_lineups`.
    """
    return check_sofascore_lineups()


ONCE_MIN_PARTIDOS = 10
ONCE_MIN_COBERTURA = 0.5


def check_sofascore_lineups() -> tuple[bool, str]:
    """
    Bajas y once de SofaScore o FotMob (db/087): los partidos de las próximas 36 h tienen que tener
    bajas u once previsto, y los ya empezados en las últimas 24 h su once oficial.
    Con muestra pequeña (día sin partidos) no se alarma.
    """
    row = query(
        """SELECT count(*) FILTER (WHERE m.kickoff_utc BETWEEN now() AND now() + interval '36 hours'
                                     AND m.status = 'scheduled') AS prox,
                  count(*) FILTER (WHERE m.kickoff_utc BETWEEN now() AND now() + interval '36 hours'
                                     AND m.status = 'scheduled'
                                     AND (EXISTS (SELECT 1 FROM lineups_previstas p WHERE p.match_id = m.match_id)
                                          OR EXISTS (SELECT 1 FROM injuries i WHERE i.match_id = m.match_id
                                                                                AND i.source IN ('sofascore', 'fotmob'))))
                      AS prox_con,
                  count(*) FILTER (WHERE m.kickoff_utc BETWEEN now() - interval '24 hours'
                                                           AND now() - interval '15 minutes') AS emp,
                  count(*) FILTER (WHERE m.kickoff_utc BETWEEN now() - interval '24 hours'
                                                           AND now() - interval '15 minutes'
                                     AND EXISTS (SELECT 1 FROM lineups x WHERE x.match_id = m.match_id))
                      AS emp_con
           FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active"""
    )[0]
    prox, prox_con, emp, emp_con = (int(row[k] or 0) for k in ("prox", "prox_con", "emp", "emp_con"))
    msg = (f"SofaScore: bajas u once previsto en {prox_con} de {prox} partidos de las próximas 36 h; "
           f"once oficial en {emp_con} de {emp} empezados en 24 h")
    bajo = [n >= ONCE_MIN_PARTIDOS and con / n < ONCE_MIN_COBERTURA
            for con, n in ((prox_con, prox), (emp_con, emp))]
    if any(bajo):
        return False, msg + " (revisar fotmob_captura previos y fotmob_alineaciones; Apify está cortado desde el 31-oct)"
    return True, msg


XG_COBERTURA_MIN = 0.7
XG_COBERTURA_MIN_PARTIDOS = 5


def check_xg_coverage() -> tuple[bool, str]:
    """
    Cuántos partidos terminados de cada liga con modelo tienen xG. `check_xg_freshness` solo
    mira el ÚLTIMO xG de la liga: el 25-oct-2026 decía «xG al día» con el 26 % de los partidos
    del día con xG. Ventana de 36 h a 10 días: SofaScore lo da ~14 h tras el partido y FotMob
    rellena a las 36 h.
    """
    rows = query(
        """SELECT m.league_id, count(*) AS n, count(*) FILTER (WHERE m.home_xg IS NOT NULL) AS con
           FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active AND l.model_enabled
           WHERE m.status = 'finished'
             AND m.kickoff_utc BETWEEN now() - interval '10 days' AND now() - interval '36 hours'
           GROUP BY m.league_id"""
    )
    bajas = [f"{r['league_id']} {r['con']}/{r['n']}" for r in rows
             if r["n"] >= XG_COBERTURA_MIN_PARTIDOS and r["con"] / r["n"] < XG_COBERTURA_MIN]
    total, con = sum(r["n"] for r in rows), sum(r["con"] for r in rows)
    if bajas:
        return False, f"xG en menos del {XG_COBERTURA_MIN:.0%} de los partidos de: " + ", ".join(bajas)
    return True, f"xG en {con} de {total} partidos terminados (36 h a 10 días)"


# Una liga con partidos jugados en los últimos XG_RECENT_DAYS cuyo último xG
# es más viejo que XG_MAX_GAP_DAYS está "parada": tres semanas ya no son un
# retraso normal.
XG_RECENT_DAYS = 30
XG_MAX_GAP_DAYS = 21

# Paradas ya el 2-oct-2026 (su fuente de entonces dejó de publicar el
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
    con_fuente = XG_PARADO_CONOCIDO
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
    ("resultados", check_results_freshness),
    ("frescura de cuotas", check_odds_freshness),
    ("cierres", check_closing_coverage),
    ("nombres sin emparejar", check_unresolved_names),
    ("cobertura de bajas", check_injuries_coverage),
    ("frescura del xG", check_xg_freshness),
    ("cobertura del xG", check_xg_coverage),
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
