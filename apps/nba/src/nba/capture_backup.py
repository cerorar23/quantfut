"""Verified research capture archives; retention affects generated backups only."""
from datetime import UTC,datetime
from contextlib import closing
import hashlib,json,re,sqlite3,tarfile,tempfile
from pathlib import Path

from .audit import Ledger,digest,write_json


def verify_archive(path):
    with tarfile.open(path,'r:gz') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)) or any(not m.isfile() for m in members):raise ValueError('invalid archive members')
        if 'manifest.json' not in names:raise ValueError('manifest missing')
        manifest=json.load(archive.extractfile('manifest.json'))
        files=manifest['files']
        if set(names)!={'manifest.json',*files}:raise ValueError('archive/file manifest mismatch')
        for name,expected in files.items():
            if name!='receipts.sqlite' and not re.fullmatch(r'blobs/[0-9a-f]{64}',name):raise ValueError('unsafe member path')
            h=hashlib.sha256()
            with archive.extractfile(name) as source:
                for chunk in iter(lambda:source.read(65536),b''):h.update(chunk)
            if h.hexdigest()!=expected:raise ValueError('backup hash mismatch')
    return dict(result='passed',files_verified=len(files),manifest=manifest,archive_sha256=digest(path))


def create_backup(capture_root,backup_folder,day=None):
    capture_root,backup_folder=Path(capture_root),Path(backup_folder)
    backup_folder.mkdir(parents=True,exist_ok=True)
    day=day or datetime.now(UTC).strftime('%Y-%m-%d')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise ValueError('invalid archive day')
    target=backup_folder/f'backup-{day}.tar.gz'
    if target.exists():return verify_archive(target)
    ledger=Ledger(capture_root/'receipts.sqlite');chain=ledger.verify()
    with tempfile.TemporaryDirectory() as scratch:
        scratch=Path(scratch);dbcopy=scratch/'receipts.sqlite'
        with closing(sqlite3.connect(ledger.path)) as source,closing(sqlite3.connect(dbcopy)) as destination:source.backup(destination)
        with closing(sqlite3.connect(dbcopy)) as db:
            needed={json.loads(r[0])['raw_sha256'] for r in db.execute("SELECT payload FROM events WHERE kind='public_response_received'")}
        files={'receipts.sqlite':digest(dbcopy)}
        for hashed in sorted(needed):
            if not re.fullmatch('[0-9a-f]{64}',hashed) or digest(capture_root/'blobs'/hashed)!=hashed:raise ValueError('capture blob invalid')
            files['blobs/'+hashed]=hashed
        manifest=dict(version='nba-capture-backup-v1',created_at_utc=datetime.now(UTC).isoformat(),files=files,ledger=chain)
        write_json(scratch/'manifest.json',manifest)
        temporary=backup_folder/f'backup-{day}.tar.gz.partial'
        with tarfile.open(temporary,'w:gz') as archive:
            archive.add(scratch/'manifest.json',arcname='manifest.json')
            archive.add(dbcopy,arcname='receipts.sqlite')
            for hashed in sorted(needed):archive.add(capture_root/'blobs'/hashed,arcname='blobs/'+hashed)
        result=verify_archive(temporary)
        temporary.replace(target)
    return dict(result,archive_path=str(target))


def prune_generated_backups(folder,keep=7):
    if type(keep) is not int or keep<2:raise ValueError('keep at least two verified backups')
    folder=Path(folder).resolve()
    candidates=sorted(p for p in folder.iterdir() if re.fullmatch(r'backup-\d{4}-\d{2}-\d{2}\.tar\.gz',p.name))
    removed=[]
    for path in candidates[:-keep]:
        if path.is_symlink() or path.resolve().parent!=folder:raise ValueError('retention target outside backup directory')
        verify_archive(path)
        path.unlink();removed.append(path.name)
    return removed
