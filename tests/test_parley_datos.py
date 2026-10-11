"""Parley del día: migración, base de datos, liquidación e informe."""
import re
from pathlib import Path

from qf.publish import escalera as es

SQL = Path(__file__).resolve().parents[1] / "db" / "053_parley.sql"


def test_migracion_inmutable_y_con_los_mercados_de_la_escalera():
    t = SQL.read_text(encoding="utf-8")
    for tabla in ("parley_tickets", "parley_patas", "parley_resultados_pata", "parley_resultados"):
        assert f"CREATE TABLE IF NOT EXISTS {tabla}" in t
        assert re.search(rf"BEFORE UPDATE OR DELETE ON {tabla}\s+FOR EACH ROW EXECUTE FUNCTION deny_mutation\(\)", t)
    for m in es.MERCADOS:
        assert f"'{m}'" in t
    assert "double_chance" not in t
    assert "UNIQUE (dia, escalon)" in t and "UNIQUE (ticket_id, match_id)" in t
