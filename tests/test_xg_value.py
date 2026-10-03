"""
¿Merece el xG una fuente nueva? (decisión pendiente, 1-nov-2026)

La regla se fija ANTES de ver resultados: el xG aporta si, en el periodo en
que existía, mejora el RPS con el IC95 por semanas entero por debajo de cero
y en al menos la mitad de las ligas. Estos tests fijan la parte pura: mismas
filas en los dos brazos y el veredicto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qf.eval import xg_value


def _oos(n_semanas=12, p_local=0.5, ligas=("a", "b"), desplaza=0):
    filas = []
    for s in range(n_semanas):
        for j, liga in enumerate(ligas):
            for k in range(3):
                filas.append({
                    "match_id": f"{liga}-{s}-{k}",
                    "kickoff_utc": pd.Timestamp("2024-01-01", tz="UTC")
                    + pd.Timedelta(weeks=s, hours=k),
                    "league_id": liga,
                    "p_home": p_local, "p_draw": 0.25, "p_away": 0.75 - p_local,
                    "outcome": 0})
    df = pd.DataFrame(filas)
    return df.iloc[desplaza:].reset_index(drop=True)


def test_solo_compara_los_partidos_de_ambos_brazos():
    r = xg_value.compare(_oos(p_local=0.6), _oos(p_local=0.5, desplaza=5))
    assert r["n"] == len(_oos()) - 5


def test_mejor_en_todas_las_ligas_es_xg_aporta():
    r = xg_value.compare(_oos(p_local=0.6), _oos(p_local=0.5))
    assert r["rps_delta"] < 0                       # negativo favorece al xG
    assert r["rps_delta_ci95"][1] < 0
    assert r["ligas_mejoran"] == r["ligas"] == 2
    assert xg_value.veredicto(r) == "xg_aporta"


def test_peor_o_igual_no_demuestra_nada():
    igual = xg_value.compare(_oos(p_local=0.5), _oos(p_local=0.5))
    assert xg_value.veredicto(igual) == "xg_no_demostrado"
    peor = xg_value.compare(_oos(p_local=0.4), _oos(p_local=0.5))
    assert peor["rps_delta"] > 0
    assert xg_value.veredicto(peor) == "xg_no_demostrado"


def test_sin_semanas_suficientes_no_hay_veredicto_positivo():
    r = xg_value.compare(_oos(n_semanas=3, p_local=0.6), _oos(n_semanas=3))
    assert r["rps_delta_ci95"] is None
    assert xg_value.veredicto(r) == "xg_no_demostrado"


def test_los_brazos_difieren_solo_en_la_mezcla_de_xg(monkeypatch):
    llamadas = []

    def wf(df, start, **kw):
        llamadas.append(kw)
        return _oos()

    monkeypatch.setattr(xg_value, "walk_forward_oos", wf)
    df = pd.DataFrame({"kickoff_utc": pd.to_datetime(["2023-01-01", "2025-06-01"], utc=True)})
    xg_value.ventana(df, "2023-07-01", "2025-02-01")
    assert [k["xg_blend"] for k in llamadas] == [pytest.approx(0.65), 0.0]
    sin_mezcla = [{k: v for k, v in c.items() if k != "xg_blend"} for c in llamadas]
    assert sin_mezcla[0] == sin_mezcla[1]
