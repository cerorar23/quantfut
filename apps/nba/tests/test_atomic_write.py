import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from nba.audit import write_json


def windows_lock():
    error=PermissionError('synthetic Windows sharing violation');error.winerror=32;return error


def test_transient_windows_lock_preserves_previous_until_atomic_replace(tmp_path,monkeypatch):
    path=tmp_path/'state.json';write_json(path,dict(value='old'))
    original=Path.replace;attempts=[]
    def locked(source,target):
        attempts.append(source)
        if len(attempts)<3:
            assert json.loads(path.read_bytes())==dict(value='old')
            raise windows_lock()
        return original(source,target)
    monkeypatch.setattr(Path,'replace',locked)
    write_json(path,dict(value='new'))
    assert len(attempts)==3 and json.loads(path.read_bytes())==dict(value='new')
    assert not list(tmp_path.glob('*.tmp'))


def test_terminal_failure_retains_prior_and_complete_recovery_file(tmp_path,monkeypatch):
    path=tmp_path/'state.json';write_json(path,dict(value='old'));attempts=[]
    def fail(*args):attempts.append(1);raise windows_lock()
    monkeypatch.setattr(Path,'replace',fail)
    with pytest.raises(PermissionError):write_json(path,dict(value='new'))
    assert len(attempts)==6 and json.loads(path.read_bytes())==dict(value='old')
    temporary=list(tmp_path.glob('*.tmp'));assert len(temporary)==1 and json.loads(temporary[0].read_bytes())==dict(value='new')


def test_concurrent_writers_never_share_temporary_or_mix_json(tmp_path):
    path=tmp_path/'state.json'
    def writer(i):write_json(path,dict(index=i,body=[i]*500))
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(writer,range(20)))
    value=json.loads(path.read_bytes());assert value['body']==[value['index']]*500
    assert not list(tmp_path.glob('*.tmp'))


def test_non_windows_permission_error_not_retried(tmp_path,monkeypatch):
    attempts=[]
    def fail(*args):attempts.append(1);raise PermissionError('real permission failure')
    monkeypatch.setattr(Path,'replace',fail)
    with pytest.raises(PermissionError):write_json(tmp_path/'state.json',{})
    assert len(attempts)==1
