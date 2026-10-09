"""Allowlisted public snapshots with new own receipts, including failed HTTP."""
from datetime import UTC,datetime
import hashlib
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl
import urllib.request,urllib.error

from .audit import Ledger,digest


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('redirect rejected before another URL is requested')


def public_url(url,allowed):
    parts=urlsplit(url)
    if (url not in allowed or parts.scheme!='https' or parts.username or parts.password or parts.fragment
            or any(k not in {'dates','limit','season','event'} for k,v in parse_qsl(parts.query))):
        raise ValueError('explicit public URL without secret query parameters required')
    return url


def capture(root,url,allowed,timeout=15):
    public_url(url,allowed)
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    started=datetime.now(UTC).isoformat()
    headers={};status=None;error=None;raw=b''
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 NBA research receipt capture','Accept':'application/json,text/html'})
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
            raw=response.read(20_000_001);status=response.status
            headers={k:response.headers.get(k) for k in ['Date','Last-Modified','Content-Type']}
    except urllib.error.HTTPError as e:
        status=e.code;raw=e.read(20_000_001);error='HTTPError'
    except Exception as e:error=type(e).__name__
    received=datetime.now(UTC).isoformat()
    if len(raw)>20_000_000:raise ValueError('response too large')
    hashed=hashlib.sha256(raw).hexdigest();blobs=root/'blobs';blobs.mkdir(exist_ok=True);path=blobs/hashed
    if path.exists():
        if digest(path)!=hashed:raise ValueError('raw body integrity mismatch')
    else:
        with path.open('xb') as f:f.write(raw)
    receipt=dict(url=url,requested_at_utc=started,first_received_at_utc=received,http_status=status,error=error,
        raw_sha256=hashed,raw_bytes=len(raw),headers=headers,source_updated_at_utc=None,
        original_historical_receipt_known=False,actionable=False)
    receipt['receipt_event_hash']=Ledger(root/'receipts.sqlite').append('public_response_received',receipt)
    return receipt
