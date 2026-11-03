"""Exportador del host de estadísticas NBA: contenedor aislado de solo lectura y escritura solo si hay eventos."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / 'scripts' / 'publicar_nba_estadisticas.py'


def cargar():
    spec = importlib.util.spec_from_file_location('publicar_nba_estadisticas', RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class Hecho:
    def __init__(self, salida=b'', codigo=0, error=b''):
        self.stdout, self.returncode, self.stderr = salida, codigo, error


def feed(eventos):
    return json.dumps({'generated_at': '2026-10-27T12:00:00+00:00', 'games_used': 7, 'events': eventos}).encode()


def test_el_contenedor_va_aislado_y_con_los_datos_en_solo_lectura(monkeypatch):
    m = cargar()
    llamadas = []
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: llamadas.append(cmd) or Hecho(feed({'0022600130': {}})))
    assert m.build()['events'] == {'0022600130': {}}
    cmd = llamadas[0]
    assert cmd[cmd.index('--network') + 1] == 'none' and '--read-only' in cmd and '--cap-drop' in cmd
    assert all(v.endswith(':ro') for v in cmd if v.startswith(str(m.LIVE)))
    assert cmd[-2:] == ['--output', '-']


def test_un_fallo_o_una_salida_vacia_no_publican_nada(monkeypatch):
    m = cargar()
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: Hecho(codigo=1, error=b'boom'))
    with pytest.raises(SystemExit):
        m.build()
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: Hecho(feed({})))
    with pytest.raises(SystemExit):
        m.build()


def test_dry_run_no_escribe_en_la_api(monkeypatch, tmp_path):
    m = cargar()
    m.HERE = tmp_path
    llamadas = []
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: llamadas.append(cmd) or Hecho(feed({'0022600130': {}})))
    monkeypatch.setattr('sys.argv', ['publicar', '--dry-run'])
    m.main()
    assert len(llamadas) == 1 and (tmp_path / 'ultima_prueba.json').exists()
    monkeypatch.setattr('sys.argv', ['publicar'])
    m.main()
    assert llamadas[-1][:3] == ['docker', 'exec', '-i']


def test_el_escritor_exige_eventos_y_reemplaza_de_forma_atomica():
    m = cargar()
    assert 'os.replace' in m.WRITER and "value['events']" in m.WRITER and 'nba_stats.json' in m.WRITER
