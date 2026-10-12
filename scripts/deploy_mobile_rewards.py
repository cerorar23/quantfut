"""Package a narrow API update on the existing server image, preserving worker.

Prepare downloads only deployed main/panel/base files and applies explicit
patches. Deploy checks the original image ID, adds migrations, runs rollback-only
transaction checks, then replaces the API service alone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'docs'/'validation'/'mobile_rewards_release_20261011'
REMOTE='/home/qf/quantfut/releases/mobile-rewards-20261011'
IMAGE='quantfut-api-mobile-rewards:20261011'


def ssh(command, *, capture=False, data=None):
    r=subprocess.run(['ssh','quantfut',command],input=data,stdout=subprocess.PIPE if capture else None,check=True)
    return r.stdout if capture else None


def prepare():
    LOCAL.mkdir(parents=True,exist_ok=True)
    meta=json.loads(ssh("docker inspect quantfut-api-1 --format '{{json .}}'",capture=True))
    base=meta['Config']['Image']
    assert re.fullmatch(r'[a-zA-Z0-9_./:-]+',base)
    files={}
    for name in ('main.py','panel.py','templates/base.html'):
        raw=ssh('docker exec quantfut-api-1 cat '+shlex.quote('/app/src/qf/api/'+name),capture=True)
        backup=LOCAL/'original'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(raw)
        files[name]=raw.decode()
    main=files['main.py']
    assert 'mobile_router' not in main
    main=main.replace('HTTPException, Query, Request\n','HTTPException, Query, Request, Response\n',1)
    main=main.replace('from .web import router as web_router', 'from .web import router as web_router\nfrom .mobile import router as mobile_router\nfrom .rewards import router as rewards_router',1)
    for old,new in [('from ..publish import alta_prob_datos\n    return alta_prob_datos.informe_publico()',"from .mobile import high_probability\n    response.headers['Cache-Control'] = 'no-store'\n    return high_probability()"),('from ..publish import escalera_datos\n    return escalera_datos.informe_publico()',"from .mobile import ladder\n    response.headers['Cache-Control'] = 'no-store'\n    return ladder()")]:
        assert main.count(old)==1,old
        main=main.replace(old,new)
    main=main.replace('def escalera():','def escalera(response: Response):',1).replace('def alta_probabilidad():','def alta_probabilidad(response: Response):',1)
    main=main.replace('app.include_router(fichas_router)','app.include_router(fichas_router)\napp.include_router(mobile_router)\napp.include_router(rewards_router)',1)
    files['main.py']=main
    panel=files['panel.py'];old='    "sin_cambios": ("info", "No había nada que cambiar."),'
    assert old in panel
    files['panel.py']=panel.replace(old,old+'\n    "mobile_guardado": ("success", "Configuración guardada."),',1)
    basehtml=files['templates/base.html'];old="('sistema', '/control/sistema'"
    if old not in basehtml:
        raise RuntimeError('Inspect deployed navigation before modifying')
    pos=basehtml.index(old);line=basehtml.rfind('\n',0,pos)+1
    files['templates/base.html']=basehtml[:line]+"          ('mobile', '/control/configuracion-app', 'device-desktop-analytics', 'Configuración de la app'),\n          ('rewards', '/control/recompensas', 'coins', 'Monedas y referidos'),\n"+basehtml[line:]
    for name in ('mobile.py','rewards.py','templates/mobile_config.html','templates/rewards.html'):
        files[name]=(ROOT/'src/qf/api'/name).read_text(encoding='utf-8')
    for name,content in files.items():
        p=LOCAL/'api'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8',newline='\n')
    for name in ('054_app_mobile.sql','055_monedas_referidos.sql'):
        (LOCAL/name).write_bytes((ROOT/'db'/name).read_bytes())
    (LOCAL/'Dockerfile').write_text(f'FROM {base}\nCOPY api/ /app/src/qf/api/\nCOPY transaction_check.py /tmp/transaction_check.py\n',encoding='utf-8')
    (LOCAL/'override.yml').write_text(f'services:\n  api:\n    image: {IMAGE}\n',encoding='utf-8')
    (LOCAL/'manifest.json').write_text(json.dumps({'original_image':base,'original_image_id':meta['Image'],'image':IMAGE,'files':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in files.items()}},indent=2),encoding='utf-8')
    print('Prepared narrow release:',LOCAL)


def deploy():
    manifest=json.loads((LOCAL/'manifest.json').read_text())
    live=ssh("docker inspect quantfut-api-1 --format '{{.Image}}'",capture=True).decode().strip()
    assert live==manifest['original_image_id'],'Server image changed; prepare again before deploying'
    ssh('mkdir -p '+shlex.quote(REMOTE))
    subprocess.run(['scp','-r',str(LOCAL)+ '/.','quantfut:'+REMOTE+'/'],check=True)
    ssh('docker build -t '+IMAGE+' '+REMOTE)
    for name in ('054_app_mobile.sql','055_monedas_referidos.sql'):
        ssh('docker exec -i quantfut-db-1 psql -v ON_ERROR_STOP=1 -U qf -d quantfut',data=(LOCAL/name).read_bytes())
    ssh('docker run --rm --network quantfut_default --env-file /home/qf/quantfut/.env '+IMAGE+' python /tmp/transaction_check.py')
    before=ssh("docker inspect quantfut-worker-1 --format '{{.Id}}'",capture=True).decode().strip()
    ssh('cd /home/qf/quantfut && docker compose -f docker-compose.yml -f '+REMOTE+'/override.yml up -d --no-deps --no-build api')
    after=ssh("docker inspect quantfut-worker-1 --format '{{.Id}}'",capture=True).decode().strip()
    assert before==after,'Worker unexpectedly changed'
    persist_image()
    print('API deployed. Worker unchanged. Previous image:',manifest['original_image'])


def persist_image():
    """Keep normal future compose runs on the verified API image."""
    script = '''from pathlib import Path
p=Path('/home/qf/quantfut/docker-compose.yml')
raw=p.read_text()
old='image: quantfut-api-menu70:20261009'
new='image: quantfut-api-mobile-rewards:20261011'
if new not in raw:
    assert raw.count(old)==1
    backup=Path('/home/qf/quantfut/releases/mobile-rewards-20261011/docker-compose.before.yml')
    if not backup.exists(): backup.write_bytes(p.read_bytes())
    p.write_text(raw.replace(old,new,1))
assert p.read_text().count(new)==1
print('API image persisted in compose configuration')
'''
    ssh('python3 -',data=script.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','deploy','persist']);args=p.parse_args()
    {'prepare':prepare,'deploy':deploy,'persist':persist_image}[args.action]()
