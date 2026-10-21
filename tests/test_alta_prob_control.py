"""Control de calidad e historial de la línea de alta probabilidad."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from qf.eval import soft_vs_sharp as svs
from qf.publish import alta_prob as ap

T0 = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)


def _filas(n, prob, tasa, market="double_chance", semanas=10, ref=None):
    aciertos = round(n * tasa)
    return [{"market": market, "prob": prob, "ref_price": ref,
             "outcome": "win" if i < aciertos else "loss",
             "kickoff_utc": T0 + timedelta(weeks=i % semanas)}
            for i in range(n)]


def test_sin_muestra_no_bloquea():
    assert ap.control([])["bloqueados"] == []
    assert ap.control(_filas(40, 0.87, 0.5))["bloqueados"] == []


def test_promete_de_mas_bloquea_todo_y_su_mercado():
    out = ap.control(_filas(120, 0.87, 0.60))
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]


def test_cumpliendo_no_bloquea():
    assert ap.control(_filas(300, 0.87, 0.87))["bloqueados"] == []


def test_calibrada_con_doce_semanas_no_bloquea():
    out = ap.control(_filas(300, 0.87, 0.87, semanas=12))
    assert out["bloqueados"] == []
    assert not any("grosero" in m or "IC99" in m for m in out["motivos"])


def test_solo_el_mercado_que_falla():
    # El conjunto cumple (z ≈ 0) y los goles fallan a lo grande (z ≈ −7): la
    # red de fallo grosero bloquea solo ese mercado.
    filas = _filas(400, 0.87, 0.92) + _filas(60, 0.86, 0.55, market="totals")
    out = ap.control(filas)
    assert out["bloqueados"] == ["totals"]
    assert any(m.startswith("totals: fallo grosero") for m in out["motivos"])


def _z(filas):
    """z = Σ(acertado − prob) / sqrt(Σ prob·(1 − prob)), a mano, sin tocar `ap`."""
    dif = sum((f["outcome"] == "win") - f["prob"] for f in filas)
    return dif / np.sqrt(sum(f["prob"] * (1 - f["prob"]) for f in filas))


def test_deficit_moderado_con_pocas_semanas_no_bloquea():
    # 120 pronósticos prometiendo 0,87 que aciertan 0,80: z ≈ −2,3, no es un
    # fallo grosero; y con 9 semanas el IC todavía no puede pausar (hacen falta 10).
    filas = _filas(120, 0.87, 0.80, semanas=9)
    assert _z(filas) > ap.Z_GROSERO
    out = ap.control(filas)
    assert out["bloqueados"] == []
    assert any("menos de 10 semanas" in m for m in out["motivos"])


def test_fallo_grosero_bloquea_aunque_haya_pocas_semanas():
    filas = _filas(120, 0.87, 0.40, semanas=3)
    assert _z(filas) <= ap.Z_GROSERO
    out = ap.control(filas)
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]
    assert any("fallo grosero" in m and "z -" in m for m in out["motivos"])


def test_fallo_grosero_exige_la_muestra_minima():
    filas = _filas(40, 0.87, 0.10, semanas=3)
    assert _z(filas) <= ap.Z_GROSERO
    assert ap.control(filas)["bloqueados"] == []


def test_deficit_claro_con_diez_semanas_bloquea_por_ic99():
    # 300 al 0,87 que aciertan 0,80: z ≈ −3,6 (no es grosero) pero el IC99 por
    # semanas queda entero bajo cero. Con 9 semanas no; con 10 sí.
    nueve = _filas(300, 0.87, 0.80, semanas=9)
    diez = _filas(300, 0.87, 0.80, semanas=10)
    assert _z(diez) > ap.Z_GROSERO
    assert ap.control(nueve)["bloqueados"] == []
    out = ap.control(diez)
    assert "todo" in out["bloqueados"]
    assert any("IC99" in m for m in out["motivos"])


def test_todo_motivo_de_bloqueo_dice_por_debajo():
    # `daily._alta` avisa por Telegram de un bloqueo de MERCADO buscando
    # "por debajo" en los motivos: tanto el fallo grosero como el IC99 tienen
    # que seguir diciéndolo, o la alerta se queda muda.
    grosero = ap.control(_filas(120, 0.87, 0.40, semanas=3))
    por_ic = ap.control(_filas(300, 0.87, 0.80, semanas=10))
    for out in (grosero, por_ic):
        assert out["bloqueados"]
        assert all("por debajo" in m for m in out["motivos"] if "muestra" not in m)


def test_el_nivel_del_ic_se_puede_elegir_y_el_defecto_no_cambia():
    valores = np.array([(-1.0) ** i * 0.1 + 0.02 for i in range(120)])
    semanas = np.array([f"s{i % 12}" for i in range(120)])
    ic95 = svs._weekly_ci(valores, semanas)
    assert svs._weekly_ci(valores, semanas, level=0.95) == ic95
    ic99 = svs._weekly_ci(valores, semanas, level=0.99)
    assert ic99[0] <= ic95[0] and ic99[1] >= ic95[1] and ic99 != ic95


def test_historial():
    filas = _filas(20, 0.85, 0.90, ref=1.20) + _filas(10, 0.90, 0.80, market="h2h")
    h = ap.historial(filas)
    assert h["n"] == 30 and h["aciertos"] == 26
    assert h["acierto_prometido"] == pytest.approx(86.7, abs=0.05)
    assert h["acierto_real"] == pytest.approx(86.7, abs=0.05)
    assert h["por_mercado"]["h2h"]["n"] == 10
    assert h["rendimiento_ref"]["n"] == 20
    assert h["rendimiento_ref"]["roi"] == pytest.approx((18 * 0.2 - 2) / 20 * 100)
    assert h["diferencia_ic95"] is not None


def test_historial_vacio():
    h = ap.historial([])
    assert h["n"] == 0 and h["acierto_real"] is None and h["por_mercado"] == {}


def test_marca_local_y_visitante_se_vigilan_como_un_grupo():
    # Decisión del usuario (2026-10-07): los dos lados son UN grupo de control.
    # Cada lado tiene solo 30 pronósticos (< MIN_N_CONTROL) y por separado no
    # se pausaría; juntos suman 60, prometen 0,86 y aciertan 0,55 (z ≈ −7), y el
    # resto de la línea cumple, así que "todo" no se bloquea.
    assert ap.grupo_control("team_totals_home") == ap.grupo_control("team_totals_away") == "team_totals"
    assert ap.grupo_control("totals") == "totals" and ap.grupo_control("h2h") == "h2h"
    filas = (_filas(400, 0.87, 0.92)
             + _filas(30, 0.86, 0.55, market="team_totals_home")
             + _filas(30, 0.86, 0.55, market="team_totals_away"))
    out = ap.control(filas)
    assert out["bloqueados"] == ["team_totals"]
    assert any(m.startswith("team_totals: fallo grosero") and "60 pronósticos" in m
               for m in out["motivos"])
    assert not any(m.startswith("team_totals_") for m in out["motivos"])


def test_un_lado_suelto_sin_muestra_no_pausa_el_grupo():
    # Un solo lado con 30 pronósticos: el grupo no llega a la muestra mínima.
    filas = _filas(400, 0.87, 0.92) + _filas(30, 0.86, 0.55, market="team_totals_home")
    out = ap.control(filas)
    assert out["bloqueados"] == []
    assert any(m.startswith("team_totals: muestra insuficiente (30 < 50)")
               for m in out["motivos"])


# --- picks del mismo partido: el control mide por partido (19-oct-2026) ---
def _por_partido(partidos, por_partido, prob, tasa_partidos, market="corners", semanas=9):
    """`partidos` partidos con `por_partido` picks cada uno que ganan o pierden JUNTOS; `tasa_partidos` de ellos aciertan."""
    ganan = round(partidos * tasa_partidos)
    return [{"match_id": f"m{i}", "market": market, "prob": prob, "ref_price": None,
             "outcome": "win" if i < ganan else "loss", "kickoff_utc": T0 + timedelta(weeks=i % semanas)}
            for i in range(partidos) for _ in range(por_partido)]


def test_cuatro_picks_por_partido_no_bloquean_por_ruido():
    filas = _por_partido(40, 4, 0.87, 0.75)                   # 160 picks = 40 partidos; z independiente < −4
    sin_partido = [{k: v for k, v in f.items() if k != "match_id"} for f in filas]
    assert _z(sin_partido) <= ap.Z_GROSERO                     # contando picks como independientes, parecía un fallo grosero
    out = ap.control(filas)
    assert out["bloqueados"] == [] and not any("grosero" in m for m in out["motivos"])


def test_un_fallo_real_en_muchos_partidos_sigue_bloqueando_con_match_id():
    out = ap.control(_por_partido(160, 1, 0.87, 0.60))        # 160 partidos distintos que aciertan 60 % prometiendo 87 %
    assert "corners" in out["bloqueados"] or "todo" in out["bloqueados"]


def test_la_varianza_por_partido_nunca_baja_de_la_independiente():
    import pandas as pd
    # Dentro de un partido los picks se compensan (uno gana y otro pierde): la varianza agrupada sería casi 0, pero no se toma.
    filas = [{"match_id": "a", "market": "x", "prob": 0.5, "outcome": o, "kickoff_utc": T0} for o in ("win", "loss")] * 30
    f = ap._marco(filas)
    assert ap._varianza(f) == pytest.approx(float((f["prob"] * (1 - f["prob"])).sum()))


def test_el_historial_muestra_los_partidos_distintos_y_el_margen_por_partido():
    h = ap.historial(_por_partido(60, 4, 0.8, 0.8))
    bloque = h["por_mercado"]["corners"]
    assert bloque["n"] == 240 and bloque["partidos"] == 60
    assert bloque["margen_ee"] > 0
    sin = ap.historial([{k: v for k, v in f.items() if k != "match_id"} for f in _por_partido(60, 4, 0.8, 0.8)])
    assert "partidos" not in sin["por_mercado"]["corners"]       # sin partido, el formato de siempre
