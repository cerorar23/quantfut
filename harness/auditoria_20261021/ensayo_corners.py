"""Ensayo en seco: córners por equipo de los próximos partidos con y sin la supremacía del A (código en /tmp/qfa)."""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/tmp/qfa/src")
import qf  # noqa: E402
from qf.db import query  # noqa: E402
from qf.model import estadisticas_mercado as em  # noqa: E402
from qf.publish import escalera_datos as ed  # noqa: E402

assert qf.__file__.startswith("/tmp/qfa/")
now = datetime.now(timezone.utc)
modelos = ed.Modelos(now)
filas = query("""SELECT match_id, league_id, home_team_id, away_team_id FROM matches
                 WHERE match_id IN (SELECT match_id FROM predictions WHERE generated_at > now() - interval '30 hours') ORDER BY kickoff_utc""")
n = con = 0
for m in filas:
    acc = modelos.de(m["league_id"], "corners")
    lam = acc.lambdas(now, m["home_team_id"], m["away_team_id"]) if acc else None
    if lam is None:
        continue
    n += 1
    sup = ed.supremacia_modelo(m["match_id"])
    if sup is None:
        continue
    con += 1
    if con <= 8:
        print(f"{m['match_id'][:48]:48s} s={sup:+.2f} local {lam[0]:.2f}->{em.media_equipo('corners_home', lam, sup):.2f} "
              f"visit {lam[1]:.2f}->{em.media_equipo('corners_away', lam, sup):.2f} | local +3,5: "
              f"{em.prob('corners_home', lam, 'over', 3.5):.3f}->{em.prob('corners_home', lam, 'over', 3.5, sup):.3f}")
print(f"partidos con modelo de córners: {n}; con supremacía del A: {con}")
print("escalera (ensayo):", {k: v for k, v in ed.select_and_persist(now=now, dry_run=True).items() if k != "detalle"} if hasattr(ed, "select_and_persist") else "-")
