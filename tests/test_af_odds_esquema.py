"""
Esquema de db/041: el UNIQUE viejo de 016 no lleva la línea y, si quedara vivo,
el primer INSERT con dos líneas del mismo lado tumbaría toda la pasada de
`af_odds` (también el 1X2). Estos tests fijan, sobre el texto de los archivos,
lo que la migración tiene que garantizar y que su índice sea el mismo que usa
el `ON CONFLICT` del INSERT.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SQL = (RAIZ / "db" / "041_af_odds_totales.sql").read_text(encoding="utf-8")
CODIGO = (RAIZ / "src" / "qf" / "ingest" / "af_odds.py").read_text(encoding="utf-8")


def _columnas(lista: str) -> list[str]:
    return [c.strip() for c in lista.split(",") if c.strip()]


def test_indice_unico_con_la_linea_y_nulls_not_distinct():
    assert "CREATE UNIQUE INDEX IF NOT EXISTS af_odds_snapshots_uq_linea" in SQL
    assert "NULLS NOT DISTINCT" in SQL


def test_la_migracion_se_niega_a_terminar_si_queda_un_unique_sin_linea():
    # Mantiene el DROP por nombre (idempotente) pero no confía en el nombre.
    assert "DROP CONSTRAINT IF EXISTS af_odds_snapshots_match_id_bookmaker_market_selection_provi_key" in SQL
    assert "RAISE EXCEPTION" in SQL
    assert "contype = 'u'" in SQL
    # La guardia va antes del COMMIT: si salta, la migración entera se revierte.
    assert SQL.index("RAISE EXCEPTION") < SQL.rindex("COMMIT;")


def test_el_indice_nuevo_es_un_indice_y_no_una_restriccion():
    # La guardia busca restricciones `contype = 'u'`: si el nuevo fuera un
    # `ADD CONSTRAINT ... UNIQUE`, la propia guardia haría fallar la migración.
    assert "ADD CONSTRAINT" not in SQL.upper().replace("DROP CONSTRAINT", "")
    assert "CREATE UNIQUE INDEX" in SQL


def test_columnas_del_indice_son_las_del_on_conflict_del_insert():
    indice = re.search(r"CREATE UNIQUE INDEX[^(]*ON af_odds_snapshots\s*\(([^)]*)\)", SQL)
    conflicto = re.search(r"ON CONFLICT\s*\(([^)]*)\)", CODIGO)
    assert indice and conflicto
    columnas = _columnas(indice.group(1))
    assert columnas == ["match_id", "bookmaker", "market", "selection", "line",
                        "provider_updated_at"]
    # Mismas columnas y en el mismo orden: si divergen, ON CONFLICT no encuentra
    # el índice y PostgreSQL rechaza el INSERT.
    assert _columnas(conflicto.group(1)) == columnas
