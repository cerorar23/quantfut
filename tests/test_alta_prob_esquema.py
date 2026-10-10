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


SQL47 = (Path(__file__).resolve().parents[1] / "db" / "047_alta_prob_ampliacion.sql").read_text(encoding="utf-8")


def test_047_admite_los_mercados_y_resultados_nuevos():
    from qf.publish import alta_prob as ap
    for mercado in ("btts", "spreads", "corners"):
        assert f"'{mercado}'" in SQL47
    assert "CHECK (outcome IN ('win', 'loss', 'push', 'void'))" in SQL47
    assert "DROP CONSTRAINT IF EXISTS alta_prob_results_outcome_check" in SQL47
    assert SQL47.count("RAISE EXCEPTION") == 2
    assert SQL47.index("BEGIN;") < SQL47.index("DO $$") < SQL47.index("COMMIT;")


SQL48 = (Path(__file__).resolve().parents[1] / "db" / "048_corners_equipo.sql").read_text(encoding="utf-8")


def test_048_admite_todos_los_mercados_que_se_pueden_elegir():
    from qf.publish import alta_prob as ap
    from qf.publish import escalera as es
    alta, escalera = SQL48.split("ALTER TABLE alta_prob_picks DROP", 1)[1], SQL48.split("ALTER TABLE alta_prob_picks DROP", 1)[0]
    for mercado in ap._PRIORIDAD:
        assert f"'{mercado}'" in alta.split("COMMENT ON")[0]
    for mercado in es.MERCADOS:
        assert f"'{mercado}'" in escalera
    assert SQL48.count("RAISE EXCEPTION") == 2
