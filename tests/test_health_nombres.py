"""La alarma de nombres solo cuenta lo que se puede arreglar."""
from qf.ingest import health


def _db(monkeypatch, n, copa):
    monkeypatch.setattr(health, "query", lambda sql, *a: [
        {"n": n, "occ": n * 2 or None, "copa": copa}])


def test_clubes_de_copa_fuera_del_catalogo_no_alarman(monkeypatch):
    _db(monkeypatch, n=0, copa=35)
    ok, msg = health.check_unresolved_names()
    assert ok and "35" in msg


def test_un_nombre_de_liga_domestica_alarma(monkeypatch):
    _db(monkeypatch, n=1, copa=35)
    ok, msg = health.check_unresolved_names()
    assert not ok and msg.startswith("1 nombres")


def test_la_consulta_excluye_solo_competiciones_cross_league(monkeypatch):
    seen = []
    monkeypatch.setattr(health, "query", lambda sql, *a: seen.append(sql) or [
        {"n": 0, "occ": None, "copa": 0}])
    health.check_unresolved_names()
    assert "cross_league" in seen[0] and "LEFT JOIN leagues" in seen[0]
    # Ligas retiradas y nombres que ya no aparecen en ningún feed no alarman.
    assert "l.active" in seen[0] and "last_seen" in seen[0]
