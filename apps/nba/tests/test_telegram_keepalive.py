import io,json
from datetime import UTC,datetime,timedelta

import pytest

from nba.telegram_keepalive import keepalive_program


@pytest.mark.parametrize('status',[200,429,500])
def test_two_requests_reuse_https_without_urllib_or_retry(monkeypatch,status):
    import pathlib,urllib.request,http.client
    monkeypatch.setattr(pathlib.Path,'read_text',lambda _:'TG_BOT_TOKEN=test\nTG_ALERT_CHAT=123')
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('urllib used'))
    calls=[]
    class Response:
        def __init__(self):self.status=status
        def read(self,n):return json.dumps(dict(ok=True,result=dict(message_id=7,chat=dict(id=123)))).encode()
    class Connection:
        def __init__(self,host,timeout):calls.append('new')
        def connect(self):calls.append('connect')
        def request(self,method,path,body,headers):calls.append(method)
        def getresponse(self):return Response()
    monkeypatch.setattr(http.client,'HTTPSConnection',Connection)
    req=dict(request_id='a',text='PRUEBA TÉCNICA NBA',expires_at_utc=(datetime.now(UTC)+timedelta(minutes=1)).isoformat())
    monkeypatch.setattr('sys.stdin',io.StringIO((json.dumps(req)+'\n')*2))
    output=io.StringIO();monkeypatch.setattr('sys.stdout',output)
    exec(compile(keepalive_program(),'<remote>','exec'),{})
    results=[json.loads(line) for line in output.getvalue().splitlines()[1:]]
    assert calls[:2]==['new','connect'] and calls.count('new')==1
    if status==500:
        assert len(results)==1 and calls.count('POST')==1 and results[0]['outcome']['state']=='unknown'
    else:
        assert len(results)==2 and calls.count('POST')==2
        assert all(r['outcome']['state']==('sent' if status==200 else 'rejected') for r in results)
