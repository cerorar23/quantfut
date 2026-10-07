"""Esquema y configuración de la línea de alta probabilidad."""
from pathlib import Path

from qf.config import settings

SQL = (Path(__file__).resolve().parents[1] / "db" / "040_alta_probabilidad.sql").read_text(encoding="utf-8")


def test_tablas_inmutables():
    assert SQL.count("EXECUTE FUNCTION deny_mutation()") == 2
    assert "BEFORE UPDATE OR DELETE ON alta_prob_picks" in SQL
    assert "BEFORE UPDATE OR DELETE ON alta_prob_results" in SQL


def test_un_pronostico_por_partido_y_rango_en_la_base():
    assert "match_id     TEXT NOT NULL UNIQUE REFERENCES matches(match_id)" in SQL
    assert "CHECK (prob >= 0.80 AND prob <= 0.95)" in SQL
    assert "CHECK (market IN ('h2h', 'double_chance', 'totals'))" in SQL


def test_apagada_por_defecto():
    assert settings.alta_prob_enabled is False
    assert settings.alta_prob_control_desde == ""


SQL42 = (Path(__file__).resolve().parents[1] / "db" / "042_alta_prob_equipo.sql").read_text(encoding="utf-8")


def test_042_amplia_los_mercados_y_comprueba_que_no_queda_el_check_viejo():
    assert "'team_totals_home'" in SQL42 and "'team_totals_away'" in SQL42
    assert "DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check" in SQL42
    assert "RAISE EXCEPTION" in SQL42


def test_042_documenta_la_columna_line_dentro_de_la_transaccion():
    # `line` ya no es solo la línea de goles del partido: también los goles de un
    # equipo. Los COMMENT son idempotentes y van antes de la guardia y del COMMIT.
    for tabla in ("af_odds_snapshots", "alta_prob_picks"):
        i = SQL42.index(f"COMMENT ON COLUMN {tabla}.line IS")
        assert SQL42.index("BEGIN;") < i < SQL42.index("DO $$") < SQL42.index("COMMIT;")
    assert "goles de un equipo" in SQL42 and "de un equipo (0,5)" in SQL42
