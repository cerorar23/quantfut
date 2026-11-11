"""F8 del plan SEO: herramienta pública sin dependencias para verificar /chain y recibos."""
from __future__ import annotations

import ast
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

from qf.publish import hashchain as hc

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verificar_cadena_publica.py"


def _cargar_verificador():
    spec = importlib.util.spec_from_file_location("verificar_cadena_publica", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


def _construir_lotes(n: int = 4) -> list[dict]:
    """Genera n lotes diarios en el orden cronológico de sellado."""
    prev = hc.GENESIS
    cron = []
    for dia in range(1, n + 1):
        fecha = f"2026-11-{dia:02d}"
        body = hc.canonical_json({"batch_date": fecha, "predictions": [{"id": dia}], "picks": []})
        ph = hc.sha256_hex(body)
        ch = hc.sha256_hex(prev + ph)
        cron.append({
            "batch_date": fecha,
            "batch_kind": "diario",
            "match_id": None,
            "n_predictions": 1,
            "n_picks": 0,
            "payload_sha256": ph,
            "prev_sha256": prev,
            "chain_sha256": ch,
            "_body": body,
        })
        prev = ch
    return cron


def _api_chain_desc(cron: list[dict]) -> list[dict]:
    """Imita SELECT ... ORDER BY seq DESC de /chain."""
    return [{k: v for k, v in lote.items() if k != "_body"} for lote in reversed(cron)]


def test_el_script_solo_usa_biblioteca_estandar_y_coincide_con_hashchain():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    modulos = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modulos.add(node.module.split(".")[0])
    assert "qf" not in modulos
    assert modulos <= (sys.stdlib_module_names | {"typing"})

    vcp = _cargar_verificador()
    assert vcp.GENESIS == hc.GENESIS
    assert vcp.sha256_hex("abc" + "def") == hc.sha256_hex("abc" + "def")


def test_verificar_lotes_desde_chain_desc_y_ventana_parcial():
    vcp = _cargar_verificador()
    cron = _construir_lotes(4)
    lotes_desc = _api_chain_desc(cron)

    ok, errores, resumen = vcp.verificar_lotes(lotes_desc, exigir_genesis=True)
    assert ok and not errores
    assert resumen["total"] == 4
    assert resumen["desde_genesis"] is True
    assert resumen["ultimo_hash"] == cron[-1]["chain_sha256"]

    # Ventana parcial (los 2 últimos lotes, como ?limit=2 cuando ya existen 4)
    parcial_desc = lotes_desc[:2]
    ok_p, errs_p, res_p = vcp.verificar_lotes(parcial_desc, exigir_genesis=False)
    assert ok_p and not errs_p and res_p["desde_genesis"] is False

    ok_g, errs_g, _ = vcp.verificar_lotes(parcial_desc, exigir_genesis=True)
    assert not ok_g and any("génesis" in e for e in errs_g)


@pytest.mark.parametrize("campo", ["payload_sha256", "prev_sha256", "chain_sha256"])
def test_verificar_lotes_detecta_cualquier_alteracion(campo):
    vcp = _cargar_verificador()
    cron = _construir_lotes(3)
    lotes_desc = _api_chain_desc(cron)
    # lotes_desc[1] es el lote intermedio (#2)
    lotes_desc[1][campo] = "f" * 64

    ok, errores, _ = vcp.verificar_lotes(lotes_desc, exigir_genesis=True)
    assert not ok and errores


def test_verificar_lotes_rechaza_entrada_vacia_o_malformada():
    vcp = _cargar_verificador()
    assert not vcp.verificar_lotes([])[0]
    ok, errores, _ = vcp.verificar_lotes([{"batch_date": "2026-11-01", "payload_sha256": "no-hex"}])
    assert not ok and "64 hex" in errores[0]


def test_verificar_directorio_con_revelados_y_solo_compromiso(tmp_path):
    vcp = _cargar_verificador()
    cron = _construir_lotes(3)
    # Lote 1 diario revelado, lote 2 partido revelado, lote 3 escalera solo compromiso
    (tmp_path / "2026-11-01.json").write_text(cron[0]["_body"], encoding="utf-8")
    (tmp_path / "2026-11-01.receipt.json").write_text(
        hc.canonical_json({k: v for k, v in cron[0].items() if k != "_body"}), encoding="utf-8"
    )
    pdir = tmp_path / "partido" / "2026-11-02"
    pdir.mkdir(parents=True)
    (pdir / "m1.json").write_text(cron[1]["_body"], encoding="utf-8")
    (pdir / "m1.receipt.json").write_text(
        hc.canonical_json({k: v for k, v in cron[1].items() if k != "_body"}), encoding="utf-8"
    )
    edir = tmp_path / "escalera" / "2026-11-03"
    edir.mkdir(parents=True)
    (edir / "e1.receipt.json").write_text(
        hc.canonical_json({k: v for k, v in cron[2].items() if k != "_body"}), encoding="utf-8"
    )

    ok_hc, err_hc = hc.verify(str(tmp_path))
    ok_vcp, err_vcp, resumen = vcp.verificar_directorio(tmp_path)
    assert ok_hc and not err_hc
    assert ok_vcp and not err_vcp
    assert resumen["total"] == 3 and resumen["revelados"] == 2 and resumen["solo_compromiso"] == 1

    # Alterar el JSON revelado debe fallar en ambos verificadores
    (pdir / "m1.json").write_text('{"alterado":true}', encoding="utf-8")
    assert not hc.verify(str(tmp_path))[0]
    ok_alt, errs_alt, _ = vcp.verificar_directorio(tmp_path)
    assert not ok_alt and any("CONTENIDO ALTERADO" in e for e in errs_alt)


def test_verificar_directorio_detecta_json_sin_recibo(tmp_path):
    vcp = _cargar_verificador()
    cron = _construir_lotes(1)
    (tmp_path / "2026-11-01.json").write_text(cron[0]["_body"], encoding="utf-8")
    (tmp_path / "2026-11-01.receipt.json").write_text(
        hc.canonical_json({k: v for k, v in cron[0].items() if k != "_body"}), encoding="utf-8"
    )
    (tmp_path / "2026-11-02.json").write_text("{}", encoding="utf-8")
    ok, errores, _ = vcp.verificar_directorio(tmp_path)
    assert not ok and any("falta el recibo" in e for e in errores)


def test_cli_archivo_url_y_directorio(tmp_path, capsys, monkeypatch):
    vcp = _cargar_verificador()
    cron = _construir_lotes(2)
    payload = {"lotes": _api_chain_desc(cron), "como_verificar": []}
    archivo = tmp_path / "chain.json"
    archivo.write_text(json.dumps(payload), encoding="utf-8")

    assert vcp.main(["--archivo", str(archivo), "--desde-genesis", "--json"]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["ok"] is True and salida["resumen"]["total"] == 2

    class _FakeResp:
        def __init__(self, data: bytes):
            self._buf = io.BytesIO(data)

        def read(self) -> bytes:
            return self._buf.read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        vcp.urllib.request,
        "urlopen",
        lambda req, timeout=15.0: _FakeResp(json.dumps(payload).encode("utf-8")),
    )
    assert vcp.main(["--url", "https://ejemplo.invalid/chain", "--desde-genesis"]) == 0
    assert "OK: 2 lotes verificados" in capsys.readouterr().out

    # JSON roto devuelve código 2
    roto = tmp_path / "roto.json"
    roto.write_text("{no json", encoding="utf-8")
    assert vcp.main(["--archivo", str(roto)]) == 2
