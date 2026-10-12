"""Record public production checks without customer or administrator tokens."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).parent
BASE='https://pronosticosdeportivos.pro'
report={}
for name,path in [('health','/health'),('web','/'),('config','/mobile/v1/config'),
                  ('home','/mobile/v1/home?fecha=2026-10-11&tz=-360'),
                  ('rewards','/mobile/v1/rewards'),('alta','/alta-probabilidad'),('escalera','/escalera')]:
    with urlopen(Request(BASE+path,headers={'User-Agent':'QuantFut/1.0 (Android; Flutter)'}),timeout=45) as response:
        body=response.read()
        report[name]={'status':response.status,'cache_control':response.headers.get('Cache-Control')}
        if name!='web':
            data=json.loads(body)
            (ROOT/f'{name}_real.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        assert response.status==200
        if name in ('config','home','rewards','alta','escalera'):
            assert response.headers.get('Cache-Control')=='no-store'
        if name in ('home','alta'):
            high=data['alta_probabilidad'] if name=='home' else data
            for row in high['vip']:
                assert not set(row).intersection({'prob','market','selection','ref_price','price','texto','line'})
        if name=='home':
            report[name].update(agenda=len(data['agenda']),public_picks=len(high['proximos']),vip_picks=len(high['vip']))
            steps=[p for r in data['escalera']['actuales'] for p in r['pasos'] if p['outcome'] is None and p.get('free')]
            assert len(steps)<=1
            report[name]['free_ladder_steps']=len(steps)
        if name=='rewards':
            assert data['wallet'] is None
            assert not any(p['available'] for p in data['providers'])
            report[name]['providers_pending']=len(data['providers'])
(ROOT/'public_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
