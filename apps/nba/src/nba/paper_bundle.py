"""Portable copies of sealed paper inputs; never rewrite paths inside evidence."""
import io
import json
from pathlib import Path
import tarfile

from .audit import digest, write_json
from .paper_followup import verify_plan


def build_bundle(plan_folder, initial_state, destination, workspace=None):
    workspace=Path(workspace or Path.cwd()).resolve();folder=Path(plan_folder)
    plan=verify_plan(folder)
    if any(Path(name).is_absolute() for name in [plan['cohort_path'],*plan['input_hashes'],*(m['registration'] for m in plan['mappings'])]):
        raise ValueError('sealed references must already be relative; never rewrite sealed paths')
    def relative(path):
        path=Path(path);resolved=(workspace/path).resolve() if not path.is_absolute() else path.resolve()
        try:name=resolved.relative_to(workspace).as_posix()
        except ValueError:raise ValueError('bundle inputs must stay inside workspace') from None
        if not resolved.is_file() or resolved.is_symlink():raise ValueError('regular bundle file required')
        return name,resolved
    files={}
    paths=[folder/'plan.json',folder/'seal.json',*map(Path,plan['input_hashes'])]
    for mapping in plan['mappings']:
        root=Path(mapping['registration']);seal=json.loads((root/'seal.json').read_bytes())
        paths.extend(root/name for name in seal['files'])
    paths.extend(p for p in (workspace/'apps/nba/src/nba').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.sql'))
    paths.extend(workspace/'apps/nba/ops'/name for name in ('paper_worker.py','Dockerfile.paper'))
    paths.append(workspace/'apps/nba/pyproject.toml')
    for path in paths:
        name,resolved=relative(path);files[name]=resolved
    from .audit import Ledger
    if Ledger(initial_state).verify()['events']!=0:raise ValueError('transfer requires unclaimed initial state')
    import sqlite3
    with sqlite3.connect(initial_state) as db:
        if db.execute('SELECT COUNT(*) FROM claims').fetchone()[0]:raise ValueError('initial state already claimed')
    root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    state_copy=root/'initial_state.sqlite';state_copy.write_bytes(Path(initial_state).read_bytes())
    files['initial_state.sqlite']=state_copy
    config=dict(plan=relative(folder/'plan.json')[0].removesuffix('/plan.json'),
        deadline_utc='2026-10-22T12:00:00+00:00',total_closing_credit_cap=2,
        maximum_jobs_per_run=3,production_ready=False,periodic_copies=False)
    write_json(root/'worker_config.json',config);files['worker_config.json']=root/'worker_config.json'
    manifest=dict(version='nba-paper-vps-bundle-1',files={n:digest(p) for n,p in sorted(files.items())},
        original_plan_sha256=digest(folder/'plan.json'),original_inputs_unchanged=True,credentials_included=False)
    write_json(root/'bundle_manifest.json',manifest);files['bundle_manifest.json']=root/'bundle_manifest.json'
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
        for name,path in sorted(files.items()):
            member=tarfile.TarInfo(name);body=path.read_bytes();member.size=len(body);member.mode=0o444
            archive.addfile(member,io.BytesIO(body))
    (root/'bundle.tar.gz').write_bytes(buffer.getvalue())
    return dict(files=len(files),bytes=len(buffer.getvalue()),sha256=digest(root/'bundle.tar.gz'),
        units=plan['unique_units'],events=len(plan['mappings']),initial_state_events=0,credentials_included=False)
