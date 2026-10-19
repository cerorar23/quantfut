"""Disparo del sello tardío: cuándo toca sellar un partido y que el job no haga nada mientras el corte esté apagado."""
from datetime import date, datetime, timedelta, timezone

import pytest

from qf.publish import hashchain, sello_tardio as st

KO = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("minutos,lados,esperado", [
    (120, 2, False),    # aún lejos aunque haya alineación
    (90, 2, True),      # con las dos alineaciones, en cuanto entra en la ventana
    (89, 1, False),     # una sola alineación no basta
    (60, 0, False),     # sin alineación se espera a T-45
    (45, 0, True),
    (44, 2, True),
    (1, 0, True),
    (0, 2, False),      # ya empezó: nada que sellar
    (-5, 2, False),
])
def test_toca_sellar(minutos, lados, esperado):
    assert st.toca_sellar(KO, KO - timedelta(minutes=minutos), lados) is esperado


def test_apagado_si_no_hay_corte(monkeypatch):
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", None)
    monkeypatch.setattr(st, "candidatos", lambda ahora: pytest.fail("no debe consultar nada"))
    assert st.run(KO) == {"estado": "apagado"}


def test_sella_solo_los_que_tocan_y_un_fallo_no_detiene_a_los_demas(monkeypatch):
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", date(2026, 10, 1))
    ahora = KO - timedelta(minutes=40)
    filas = [{"match_id": "a", "kickoff_utc": KO, "lados_xi": 0},                              # T-40: toca
             {"match_id": "b", "kickoff_utc": KO + timedelta(hours=2), "lados_xi": 0},        # lejos: no toca
             {"match_id": "c", "kickoff_utc": KO + timedelta(minutes=5), "lados_xi": 2}]      # toca y falla
    monkeypatch.setattr(st, "candidatos", lambda a: filas)

    def sellar(m, a):
        if m["match_id"] == "c":
            raise RuntimeError("boom")
        return {"chain_sha256": "x"}

    monkeypatch.setattr(st, "sellar", sellar)
    monkeypatch.setattr(st.tg, "alert", lambda *a, **k: None)
    assert st.run(ahora) == {"sellados": ["a"], "fallos": ["c"]}


def test_un_partido_anterior_al_corte_no_se_sella(monkeypatch):
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", date(2026, 10, 21))
    monkeypatch.setattr(st, "candidatos", lambda a: [{"match_id": "a", "kickoff_utc": KO, "lados_xi": 2}])
    monkeypatch.setattr(st, "sellar", lambda m, a: pytest.fail("anterior al corte"))
    assert st.run(KO - timedelta(minutes=30)) == {"sellados": [], "fallos": []}
