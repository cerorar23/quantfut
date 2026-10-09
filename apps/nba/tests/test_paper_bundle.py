from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tarfile

import pytest

from nba import paper_bundle,paper_followup
from nba.audit import Ledger,digest,write_json
from test_paper import NOW,TIP
from test_paper_followup import planned
from test_paper import cohort

PROJECT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('paper_worker',PROJECT/'apps/nba/ops/paper_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


@pytest.fixture
def portable(planned,monkeypatch):
    data=json.loads((planned/'cohort.json').read_bytes())
    for row in data['rows']:row['registration']='run'
    write_json(planned/'portable_cohort.json',data)
    monkeypatch.chdir(planned)
    paper_followup.build_plan('portable_cohort.json','receipts.json','blobs','portable_plan')
    paper_followup.advance('portable_plan','initial.sqlite','before_bundle')
    shutil.copytree(PROJECT/'apps/nba/src',planned/'apps/nba/src')
    shutil.copytree(PROJECT/'apps/nba/ops',planned/'apps/nba/ops')
    shutil.copyfile(PROJECT/'apps/nba/pyproject.toml',planned/'apps/nba/pyproject.toml')
    return planned


def test_bundle_preserves_bytes_and_verifies_after_extract(portable,monkeypatch):
    result=paper_bundle.build_bundle('portable_plan','initial.sqlite','bundle')
    assert result['units']==3 and not result['credentials_included']
    extracted=portable/'extracted';extracted.mkdir()
    with tarfile.open('bundle/bundle.tar.gz') as archive:archive.extractall(extracted,filter='data')
    assert digest(extracted/'run/seal.json')==digest('run/seal.json')
    monkeypatch.chdir(extracted)
    config,plan=worker.verify_bundle(extracted)
    assert plan['unique_units']==3 and config['total_closing_credit_cap']==2
    (extracted/'apps/nba/src/nba/paper.py').write_text('changed')
    with pytest.raises(ValueError,match='bundle changed'):worker.verify_bundle(extracted)


def test_bundle_rejects_nonportable_original_references(planned):
    with pytest.raises(ValueError,match='already be relative'):
        paper_bundle.build_bundle(planned/'plan',planned/'state.sqlite',planned/'bad',workspace=planned)


def test_claimed_state_cannot_be_copied_into_second_worker(portable):
    with sqlite3.connect('initial.sqlite') as db:db.execute('INSERT INTO claims VALUES (?,?)',('claimed',NOW.isoformat()))
    with pytest.raises(ValueError,match='already claimed'):paper_bundle.build_bundle('portable_plan','initial.sqlite','bad')


def prepared_worker(portable,monkeypatch):
    paper_bundle.build_bundle('portable_plan','initial.sqlite','bundle')
    # The bundle's manifest is intentionally stored at its runtime workspace root.
    shutil.copyfile('bundle/bundle_manifest.json','bundle_manifest.json')
    shutil.copyfile('bundle/worker_config.json','worker_config.json')
    shutil.copyfile('bundle/initial_state.sqlite','initial_state.sqlite')
    return portable


def test_waiting_worker_does_not_read_key_or_query(portable,monkeypatch):
    prepared_worker(portable,monkeypatch)
    def never(*args):pytest.fail('no job due')
    for _ in range(2):
        health,done=worker.tick(portable,portable/'data','absent_key',clock=lambda:NOW,runner=never)
        assert health['state']=='waiting' and not done
    assert not (portable/'data/runs').exists()


def test_worker_deadline_never_collects_and_clock_rollback_holds(portable,monkeypatch):
    prepared_worker(portable,monkeypatch)
    health,done=worker.tick(portable,portable/'deadline','absent_key',clock=lambda:paper_followup.utc('2026-10-22T12:00:00Z'),runner=lambda *a:pytest.fail('deadline'))
    assert done and health['state']=='deadline_exhausted'
    worker.tick(portable,portable/'clock','absent_key',clock=lambda:NOW)
    health,done=worker.tick(portable,portable/'clock','absent_key',clock=lambda:NOW-timedelta(seconds=1))
    assert done and health['state']=='clock_hold'


def test_worker_due_uses_persistent_claims_and_survives_next_instance(portable,monkeypatch):
    prepared_worker(portable,monkeypatch)
    clock=TIP-timedelta(minutes=1)
    monkeypatch.setattr(paper_followup,'now_utc',lambda:clock)
    calls=[]
    # A missing-key close is still claimed once. Free capture rejects explicitly.
    monkeypatch.setattr(paper_followup,'capture',lambda *args:(_ for _ in ()).throw(ValueError('synthetic failure')))
    def runner(*args):calls.append(1);return paper_followup.advance(*args)
    worker.tick(portable,portable/'data','absent_key',clock=lambda:clock,runner=runner)
    worker.tick(portable,portable/'data','absent_key',clock=lambda:clock,runner=runner)
    assert calls==[1]
    assert Ledger(portable/'data/state.sqlite').verify()['events']==4


def test_interpret_windows_separator_without_rewriting_sealed_plan(portable):
    assert paper_followup.portable_path('apps\\nba\\plan.json').as_posix()=='apps/nba/plan.json'
    path=Path('portable_plan/plan.json');plan=json.loads(path.read_bytes())
    # Synthetic Windows-authored plan with unchanged referenced payload bytes.
    plan['input_hashes']={name.replace('/','\\'):hashed for name,hashed in plan['input_hashes'].items()}
    write_json(path,plan);write_json('portable_plan/seal.json',dict(plan_sha256=digest(path)))
    before=path.read_bytes()
    assert paper_followup.verify_plan('portable_plan')['unique_units']==3
    assert path.read_bytes()==before


def test_retired_local_cli_cannot_issue_another_close(portable,monkeypatch,capsys):
    from nba import cli
    write_json('initial.owner.json',dict(retired_local_executor=True,owner='VPS'))
    monkeypatch.setattr('sys.argv',['nba','paper-advance','--plan','portable_plan','--state','initial.sqlite',
        '--output-dir','duplicate','--key-file','missing-secret-file'])
    with pytest.raises(SystemExit) as error:cli.main()
    assert error.value.code==2
    assert 'retired after VPS' in capsys.readouterr().err
    assert not Path('duplicate').exists()
