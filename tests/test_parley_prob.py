"""Parley por probabilidad mínima (rediseño de la auditoría del 19-nov-2026, en sombra)."""
import math
from datetime import datetime, timezone
from pathlib import Path
import re

from qf.publish import parley_prob as pp
from qf.publish import parley_v2 as v2
from qf.publish.alta_prob import Candidato
from qf.publish.parley_ext import OpcionExterna

T = datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc)


def op(ev, p, precio, mercado="h2h", sel="home", deporte="futbol", linea=None):
    return OpcionExterna(match_id=f"{deporte}:{ev}", cand=Candidato(mercado, sel, linea, p), price=precio, book="b",
                         odds_source="t", odds_as_of=T, deporte=deporte, evento=(str(ev), deporte, T, "L", "V"))


def test_filtro_de_patas_por_probabilidad_cuota_y_mercado():
    assert pp.elegible(op(1, .80, 1.22))
    assert not pp.elegible(op(1, .70, 1.40))                            # bajo P_PATA
    assert not pp.elegible(op(1, .95, 1.05))                            # cuota que no aporta
    assert not pp.elegible(op(1, .80, 1.22, mercado="btts", sel="yes"))  # sobrepromete 10 pp
    assert not pp.elegible(op(1, .80, 1.22, mercado="corners"))
    assert not pp.elegible(op(1, .80, 1.22, mercado="player_assists", deporte="nba"))
    assert pp.elegible(op(1, .80, 1.22, mercado="player_rebounds", deporte="nba"))
    assert not pp.elegible(op(1, .73, 1.30, deporte="tenis"))            # ganador de tenis: solo favoritos claros
    assert pp.elegible(op(1, .78, 1.25, deporte="tenis"))


def test_tres_niveles_sin_repetir_eventos_y_maxima_probabilidad():
    ops = [op(i, p, c) for i, (p, c) in enumerate(
        [(.90, 1.20), (.88, 1.22), (.86, 1.25), (.84, 1.28), (.82, 1.30), (.80, 1.33), (.79, 1.35),
         (.78, 1.38), (.77, 1.40), (.76, 1.42), (.75, 1.45)])]
    plan = pp.a_plan(ops)
    assert [t.target for t in plan.tickets] == [n.cuota_min for n in pp.NIVELES]
    usados = [o.match_id for t in plan.tickets for o in t.legs]
    assert len(usados) == len(set(usados)) == 2 + 3 + 4
    for t, n in zip(plan.tickets, pp.NIVELES):
        assert len(t.legs) == n.patas and t.quote >= n.cuota_min and t.p_prudente >= n.p_min
        assert t.estrategia == pp.ESTRATEGIA and t.version == pp.VERSION and t.estado == "solo_referencia"
    seguro = plan.tickets[0]
    # El seguro necesita cuota ≥ 1,40 con 2 patas: la mejor pareja que llega, no las dos más probables (1,20 × 1,22 < 1,40).
    assert math.prod(o.price for o in seguro.legs) >= 1.40
    mejor = max((a.cand.prob * b.cand.prob, a, b) for a in ops for b in ops
                if a.match_id < b.match_id and a.price * b.price >= 1.40)[0]
    assert abs(seguro.p_prudente - mejor) < 1e-9


def test_se_abstiene_si_no_llega_a_la_probabilidad_minima_o_faltan_eventos():
    plan = pp.a_plan([op(1, .75, 1.30), op(2, .74, 1.30)])
    assert [t.target for t in plan.tickets] == []      # .75 × .74 = .555 < .60 y no hay más eventos
    motivos = {a.target: a.motivo for a in plan.abstenciones}
    assert set(motivos) == {1.40, 1.80, 2.40} and "p ≥ 0.60" in motivos[1.40]


def test_una_pata_por_evento_aunque_el_evento_tenga_varias():
    ops = [op(1, .90, 1.20), op(1, .85, 1.30, mercado="totals", sel="over", linea=1.5), op(2, .88, 1.25)]
    t = pp.a_plan(ops).tickets[0]
    assert len({o.match_id for o in t.legs}) == 2


def test_resumen_del_ticket_lleva_la_estrategia_de_la_sombra():
    t = pp.a_plan([op(i, .85, 1.25) for i in range(3)]).tickets[0]
    r = v2.resumen(t)
    assert r["estrategia"] == "parley_probabilidad" and r["version"] == "v3-sombra" and r["n_patas"] == 2


def test_el_check_de_ambito_admite_todos_los_ambitos_que_sella_el_codigo():
    """El CHECK de db/098 no admitía `nba_dia` y las pruebas (con la base simulada) no lo vieron: 37 fallos en producción."""
    db = Path(__file__).resolve().parents[1] / "db"
    ultimo = None
    for f in sorted(db.glob("*.sql")):
        for m in re.finditer(r"parley_v2_lotes_ambito_check\s+CHECK\s*\(\s*ambito IN \(([^)]*)\)", f.read_text(encoding="utf-8")):
            ultimo = set(re.findall(r"'([a-z_]+)'", m.group(1)))
    ultimo = ultimo or {"diario", "partido"}
    src = Path(pp.__file__).resolve().parent
    usados = set()
    for f in ("parley_v2_datos.py", "parley_nba_revisor.py", "parley_nba_datos.py"):
        usados |= set(re.findall(r'ambito(?::\s*str)?\s*=\s*"([a-z_]+)"', (src / f).read_text(encoding="utf-8")))
        usados |= set(re.findall(r'"(sombra[a-z_]*)"\)', (src / f).read_text(encoding="utf-8")))
    assert {"diario", "partido", "nba_dia", "sombra", "sombra_nba"} <= usados
    assert usados <= ultimo
