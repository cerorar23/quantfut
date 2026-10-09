from pathlib import Path
import hashlib,io,json,sqlite3,tarfile
import pytest

from nba.audit import Ledger
from nba.capture_backup import create_backup,verify_archive,prune_generated_backups


def seed(root):
    (root/'blobs').mkdir(parents=True)
    raw=b'original public capture';h=hashlib.sha256(raw).hexdigest();(root/'blobs'/h).write_bytes(raw)
    Ledger(root/'receipts.sqlite').append('public_response_received',dict(raw_sha256=h))
    return h


def test_archive_has_consistent_ledger_and_original_hashes(tmp_path):
    source=tmp_path/'data';h=seed(source);result=create_backup(source,tmp_path/'backups','2026-10-08')
    assert result['result']=='passed' and result['manifest']['ledger']['events']==1
    assert result['manifest']['files']['blobs/'+h]==h
    assert verify_archive(result['archive_path'])['archive_sha256']==result['archive_sha256']


def test_corrupt_body_prevents_backup(tmp_path):
    source=tmp_path/'data';h=seed(source);(source/'blobs'/h).write_bytes(b'tampered')
    with pytest.raises(ValueError):create_backup(source,tmp_path/'backups','2026-10-08')


def test_bad_archive_member_hash_rejected(tmp_path):
    p=tmp_path/'bad.tar.gz'
    manifest=dict(files={'receipts.sqlite':'0'*64})
    with tarfile.open(p,'w:gz') as tar:
        for name,raw in [('manifest.json',json.dumps(manifest).encode()),('receipts.sqlite',b'wrong')]:
            i=tarfile.TarInfo(name);i.size=len(raw);tar.addfile(i,io.BytesIO(raw))
    with pytest.raises(ValueError):verify_archive(p)


def test_path_traversal_archive_rejected(tmp_path):
    p=tmp_path/'bad.tar.gz';name='../outside'
    raw=b'payload';manifest=dict(files={name:hashlib.sha256(raw).hexdigest()})
    with tarfile.open(p,'w:gz') as tar:
        for n,b in [('manifest.json',json.dumps(manifest).encode()),(name,raw)]:
            i=tarfile.TarInfo(n);i.size=len(b);tar.addfile(i,io.BytesIO(b))
    with pytest.raises(ValueError):verify_archive(p)


def test_retention_keeps_two_newest_and_unrelated_files(tmp_path):
    source=tmp_path/'data';seed(source);folder=tmp_path/'backups'
    for day in ['2026-10-06','2026-10-07','2026-10-08']:create_backup(source,folder,day)
    (folder/'notes.txt').write_text('preserve')
    assert prune_generated_backups(folder,2)==['backup-2026-10-06.tar.gz']
    assert (folder/'notes.txt').read_text()=='preserve' and len(list(folder.glob('*.tar.gz')))==2


def test_invalid_keep_never_deletes(tmp_path):
    with pytest.raises(ValueError):prune_generated_backups(tmp_path,1)
