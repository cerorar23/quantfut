"""Esquema de db/067: aditivo, en una transacción y sin tocar triggers existentes."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "db" / "067_f0_archivo_a_matches.sql").read_text(encoding="utf-8")


def test_una_transaccion_y_aditiva():
    assert SQL.lstrip().startswith("--") or SQL.lstrip().startswith("BEGIN")
    assert SQL.count("BEGIN;") == 1 and SQL.count("COMMIT;") == 1
    for peligro in ("DROP TABLE", "DROP TRIGGER", "DISABLE TRIGGER", "DELETE FROM", "UPDATE "):
        assert peligro not in SQL


def test_tabla_estadios_con_coordenadas_validadas():
    assert "CREATE TABLE IF NOT EXISTS estadios" in SQL
    assert "lat BETWEEN -90 AND 90" in SQL.replace("  ", " ")
    assert "lon BETWEEN -180 AND 180" in SQL.replace("  ", " ")
    assert "NULLS NOT DISTINCT" in SQL


def test_columnas_nuevas_en_matches():
    for col in ("stadium_id", "home_xgot", "away_xgot", "referee_fotmob"):
        assert f"ADD COLUMN IF NOT EXISTS {col}" in SQL


def test_procedencia_se_borra_junto_con_el_partido():
    # Las retiradas de ligas (063) borran partidos: la procedencia no puede bloquearlas.
    assert "CREATE TABLE IF NOT EXISTS matches_enriquecimiento" in SQL
    assert "ON DELETE CASCADE" in SQL
    assert "PRIMARY KEY (match_id, campo)" in SQL


def test_no_mezcla_xgot_con_psxg():
    # Los comentarios pueden nombrar home_psxg para advertir; ninguna sentencia lo toca.
    assert "ADD COLUMN IF NOT EXISTS home_psxg" not in SQL
    assert "SET home_psxg" not in SQL
