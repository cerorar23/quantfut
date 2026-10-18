"""Comprometer-revelar: al repo público va el hash antes de los partidos y el JSON después."""
import subprocess
import dataclasses
from datetime import date, datetime, timedelta, timezone

import pytest

from qf.publish import hashchain as hc

KO = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


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


def _sellar(d, dia, prev):
    """Lote mínimo escrito como lo hace seal(), sin base de datos."""
    payload = {"batch_date": dia.isoformat(),
               "predictions": [{"match_id": "m1"}], "picks": [{"match_id": "m2"}]}
    body = hc.canonical_json(payload)
    ph = hc.sha256_hex(body)
    ch = hc.sha256_hex(prev + ph)
    (d / f"{dia}.json").write_text(body, encoding="utf-8")
    (d / f"{dia}.receipt.json").write_text(hc.canonical_json(
        {"batch_date": dia.isoformat(), "payload_sha256": ph, "prev_sha256": prev,
         "chain_sha256": ch}), encoding="utf-8")
    (d / "LEDGER.md").write_text("# registro\n", encoding="utf-8")
    return ch


def _archivos_remotos(remoto):
    return set(_git(remoto, "ls-tree", "-r", "--name-only", "main").split())


def _estado(ultimo, terminados=True):
    return lambda ids: (ultimo, terminados)


def test_el_compromiso_no_sube_el_json(repo):
    remoto, d = repo
    ch = _sellar(d, date(2026, 10, 20), hc.GENESIS)
    hc._git_comprometer(d, date(2026, 10, 20), ch)
    assert _archivos_remotos(remoto) == {"2026-10-20.receipt.json", "LEDGER.md"}


def test_no_se_revela_antes_de_que_terminen_los_partidos(repo):
    _, d = repo
    ch = _sellar(d, date(2026, 10, 20), hc.GENESIS)
    hc._git_comprometer(d, date(2026, 10, 20), ch)
    # a mitad de partido, y con el margen aún sin cumplir
    assert hc.revelables(d, KO + timedelta(hours=1), _estado(KO, False)) == []
    assert hc.revelables(d, KO + hc.REVELAR_TRAS - timedelta(minutes=1), _estado(KO)) == []
    # margen cumplido pero un partido sigue sin constar terminado
    assert hc.revelables(d, KO + timedelta(hours=6), _estado(KO, False)) == []


def test_se_revela_cuando_terminaron_y_pasó_el_margen(repo):
    remoto, d = repo
    ch = _sellar(d, date(2026, 10, 20), hc.GENESIS)
    hc._git_comprometer(d, date(2026, 10, 20), ch)
    ahora = KO + hc.REVELAR_TRAS
    assert hc._git_revelar(d, ahora, _estado(KO)) == [date(2026, 10, 20)]
    assert "2026-10-20.json" in _archivos_remotos(remoto)
    # ya subido: no se vuelve a revelar
    assert hc.revelables(d, ahora, _estado(KO)) == []


def test_el_tope_libera_un_lote_con_partido_aplazado(repo):
    _, d = repo
    ch = _sellar(d, date(2026, 10, 20), hc.GENESIS)
    hc._git_comprometer(d, date(2026, 10, 20), ch)
    assert hc.revelables(d, KO + hc.REVELAR_TOPE, _estado(KO, False)) == [date(2026, 10, 20)]


def test_ids_de_partidos_recoge_todos_los_bloques():
    payload = {"predictions": [{"match_id": "a"}], "picks": [{"match_id": "b"}],
               "alta_ext": [{"match_id": "c"}], "escalera": {"pasos": [{"match_id": "d"}]},
               "parley": {"patas": [{"match_id": "e"}]}}
    assert hc._ids_de_partidos(payload) == ["a", "b", "c", "d", "e"]


def test_verify_acepta_lotes_sin_revelar(tmp_path):
    ch1 = _sellar(tmp_path, date(2026, 10, 20), hc.GENESIS)
    _sellar(tmp_path, date(2026, 10, 21), ch1)
    (tmp_path / "2026-10-21.json").unlink()      # lote solo comprometido
    ok, errores = hc.verify(str(tmp_path))
    assert ok, errores


def test_verify_detecta_json_alterado_y_cadena_rota(tmp_path):
    ch1 = _sellar(tmp_path, date(2026, 10, 20), hc.GENESIS)
    _sellar(tmp_path, date(2026, 10, 21), ch1)
    (tmp_path / "2026-10-20.json").write_text('{"batch_date":"2026-10-20"}', encoding="utf-8")
    ok, errores = hc.verify(str(tmp_path))
    assert not ok and any("CONTENIDO ALTERADO" in e for e in errores)

    ch1 = _sellar(tmp_path, date(2026, 10, 20), hc.GENESIS)
    _sellar(tmp_path, date(2026, 10, 21), "f" * 64)   # enlace que no es el anterior
    ok, errores = hc.verify(str(tmp_path))
    assert not ok and any("CADENA ROTA" in e for e in errores)


def test_seal_sin_remoto_no_toca_git(monkeypatch):
    monkeypatch.setattr(hc, "settings", dataclasses.replace(hc.settings, chain_git_remote=""))
    llamado = []
    monkeypatch.setattr(hc, "_git_revelar", lambda *a, **k: llamado.append(1))
    monkeypatch.setattr(hc, "query_one", lambda *a, **k: {"batch_id": 1, "chain_sha256": "x" * 64})
    hc.seal(date(2026, 10, 20))
    assert llamado == []
