"""Sello por partido (F7): verify y revelado con lotes de partido mezclados con los diarios. Sin base de datos."""
import subprocess
from datetime import date, datetime, timedelta, timezone

import pytest

from qf.publish import hashchain as hc

KO = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)
R9 = hc._ruta_partido("m9", date(2026, 10, 20))


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    remoto, trabajo = tmp_path / "remoto.git", tmp_path / "chain"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remoto))
    trabajo.mkdir()
    _git(trabajo, "init", "-b", "main")
    _git(trabajo, "config", "user.email", "t@t")
    _git(trabajo, "config", "user.name", "t")
    _git(trabajo, "remote", "add", "origin", str(remoto))
    return remoto, trabajo


def _escribir(ruta_base, payload, prev, extra=None):
    ruta_base.parent.mkdir(parents=True, exist_ok=True)
    body = hc.canonical_json(payload)
    ph = hc.sha256_hex(body)
    ch = hc.sha256_hex(prev + ph)
    ruta_base.with_name(ruta_base.name + ".json").write_text(body, encoding="utf-8")
    ruta_base.with_name(ruta_base.name + ".receipt.json").write_text(hc.canonical_json(
        {"payload_sha256": ph, "prev_sha256": prev, "chain_sha256": ch, **(extra or {})}), encoding="utf-8")
    return ch


def _diario(d, dia, prev):
    return _escribir(d / dia.isoformat(), {"batch_date": dia.isoformat(), "predictions": [{"match_id": "m1"}]}, prev)


def _partido(d, dia, mid, prev):
    return _escribir(d / hc._ruta_partido(mid, dia),
                     {"batch_kind": "partido", "match_id": mid, "predictions": [{"match_id": mid}],
                      "picks": [{"match_id": mid}]}, prev, {"batch_kind": "partido", "match_id": mid})


def _cadena_mixta(d):
    """diario 20 -> partido zz -> partido aa -> diario 21: el nombre del archivo no da el orden de la cadena."""
    c1 = _diario(d, date(2026, 10, 20), hc.GENESIS)
    c2 = _partido(d, date(2026, 10, 20), "zz-b", c1)
    c3 = _partido(d, date(2026, 10, 20), "aa-a", c2)
    _diario(d, date(2026, 10, 21), c3)


def test_verify_sigue_el_orden_de_la_cadena_con_lotes_de_partido(tmp_path):
    _cadena_mixta(tmp_path)
    ok, errores = hc.verify(str(tmp_path))
    assert ok, errores


def test_verify_detecta_un_lote_de_partido_alterado(tmp_path):
    _cadena_mixta(tmp_path)
    (tmp_path / (hc._ruta_partido("aa-a", date(2026, 10, 20)) + ".json")).write_text('{"match_id":"aa-a"}', encoding="utf-8")
    ok, errores = hc.verify(str(tmp_path))
    assert not ok and any("CONTENIDO ALTERADO" in e for e in errores)


def test_verify_detecta_un_lote_de_partido_quitado_de_la_cadena(tmp_path):
    _cadena_mixta(tmp_path)
    (tmp_path / (hc._ruta_partido("zz-b", date(2026, 10, 20)) + ".receipt.json")).unlink()
    (tmp_path / (hc._ruta_partido("zz-b", date(2026, 10, 20)) + ".json")).unlink()
    ok, errores = hc.verify(str(tmp_path))
    assert not ok and any("CADENA ROTA" in e for e in errores)


def test_verify_acepta_lote_de_partido_solo_comprometido(tmp_path):
    _cadena_mixta(tmp_path)
    (tmp_path / (hc._ruta_partido("aa-a", date(2026, 10, 20)) + ".json")).unlink()
    ok, errores = hc.verify(str(tmp_path))
    assert ok, errores


def test_ruta_de_partido_rechaza_nombres_peligrosos():
    ruta = hc._ruta_partido("mx_liga_mx:2026:abc-1", date(2026, 10, 20))
    assert ruta.startswith("partido/2026-10-20/mx_liga_mx_2026_abc-1-") and ":" not in ruta
    assert ruta != hc._ruta_partido("mx_liga_mx_2026_abc-1", date(2026, 10, 20))     # ids distintos, archivos distintos
    for malo in ("", "../x", "a/b", "a b", "a\\b", "a..b"):
        with pytest.raises(ValueError):
            hc._ruta_partido(malo, date(2026, 10, 20))


def test_el_compromiso_de_un_partido_sube_el_recibo_y_no_el_json(repo):
    remoto, d = repo
    c1 = _diario(d, date(2026, 10, 20), hc.GENESIS)
    ch = _partido(d, date(2026, 10, 20), "m9", c1)
    (d / "LEDGER.md").write_text("# registro\n", encoding="utf-8")
    hc._git_comprometer(d, date(2026, 10, 20), ch)
    subidos = set(_git(remoto, "ls-tree", "-r", "--name-only", "main").split())
    assert R9 + ".receipt.json" in subidos and R9 + ".json" not in subidos


def test_el_partido_se_revela_cuando_termina_y_pasa_el_margen(repo):
    remoto, d = repo
    c1 = _diario(d, date(2026, 10, 20), hc.GENESIS)
    ch = _partido(d, date(2026, 10, 20), "m9", c1)
    (d / "LEDGER.md").write_text("# registro\n", encoding="utf-8")
    hc._git_comprometer(d, date(2026, 10, 20), ch)

    def estado(ids):
        return KO, True

    assert hc.revelables_partido(d, KO + timedelta(hours=1), estado) == []
    ahora = KO + hc.REVELAR_TRAS
    assert hc.revelables_partido(d, ahora, estado) == [R9 + ".json"]
    hc._git_revelar(d, ahora, estado)
    assert R9 + ".json" in set(_git(remoto, "ls-tree", "-r", "--name-only", "main").split())
    assert hc.revelables_partido(d, ahora, estado) == []        # ya subido


def test_el_corte_por_defecto_no_sella_por_partido():
    assert hc.LOTE_POR_PARTIDO_DESDE is None and not hc.lote_por_partido(date(2030, 1, 1))
