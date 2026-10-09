"""Compatible finite remote program with TLS verification and reusable HTTPS."""
from .vps_session import remote_program


def keepalive_program():
    original=remote_program()
    marker='        with urllib.request.urlopen(http,timeout=10) as response:body=json.loads(response.read())'
    if original.count(marker)!=1:
        raise ValueError('remote template version changed')
    replacement='''        connection.request('POST',http.selector,body=payload,headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        raw=response.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('response too large')
        if response.status>=400:
            return dict(state='rejected' if response.status<500 else 'unknown',error_code=response.status,automatic_retry=False)
        body=json.loads(raw)'''
    original=original.replace(marker,replacement)
    # Establish TLS before the ready handshake, separately measured as startup.
    return "import http.client\nconnection=http.client.HTTPSConnection('api.telegram.org',timeout=10)\nconnection.connect()\n"+original
