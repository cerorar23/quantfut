"""RFC3161 proof of existence of a manifest, never proof of past receipt."""
from datetime import UTC,datetime
from pathlib import Path
import subprocess
import urllib.request

from .audit import digest,write_json

TSA_URL='http://timestamp.digicert.com'
CHAIN_URL='https://knowledge.digicert.com/content/dam/kb/attachments/time-stamp/DigiCertTrustedG4TimeStampingRSA4096SHA2562025CA1.pem'


def command(openssl,args):
    return subprocess.run([str(openssl),*map(str,args)],capture_output=True,timeout=20,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def verify(openssl,folder,manifest):
    folder=Path(folder);checks={}
    for label,params in [('query_and_nonce',['-queryfile',folder/'request.tsq']),('manifest_imprint',['-data',manifest])]:
        p=command(openssl,['ts','-verify',*params,'-in',folder/'response.tsr','-CAfile',folder/'trust.pem','-untrusted',folder/'chain.pem'])
        checks[label]=p.returncode==0 and b'Verification: OK' in p.stdout
    return checks


def stamp(openssl,trust_bundle,manifest,folder):
    """One TSA POST; transmit hash/nonce only. Certificate chain must verify."""
    manifest,folder=Path(manifest),Path(folder);folder.mkdir(exist_ok=False)
    before=digest(manifest)
    (folder/'trust.pem').write_bytes(Path(trust_bundle).read_bytes())
    p=command(openssl,['ts','-query','-data',manifest,'-sha256','-cert','-out',folder/'request.tsq'])
    if p.returncode:raise RuntimeError('timestamp query generation failed')
    with urllib.request.urlopen(CHAIN_URL,timeout=15) as response:
        chain=response.read(100_001)
        if response.url!=CHAIN_URL or len(chain)>100_000:raise ValueError('unexpected chain response')
    (folder/'chain.pem').write_bytes(chain)
    request=urllib.request.Request(TSA_URL,data=(folder/'request.tsq').read_bytes(),
        headers={'Content-Type':'application/timestamp-query'},method='POST')
    with urllib.request.urlopen(request,timeout=15) as response:
        raw=response.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('timestamp response too large')
    (folder/'response.tsr').write_bytes(raw)
    checks=verify(openssl,folder,manifest)
    assert digest(manifest)==before,'manifest changed during timestamp submission'
    p=command(openssl,['ts','-reply','-in',folder/'response.tsr','-text'])
    (folder/'response.txt').write_bytes(p.stdout)
    result=dict(state='verified' if all(checks.values()) and p.returncode==0 else 'unverified',checks=checks,
        manifest_sha256=before,query_sha256=digest(folder/'request.tsq'),response_sha256=digest(folder/'response.tsr'),
        trust_bundle_sha256=digest(folder/'trust.pem'),chain_sha256=digest(folder/'chain.pem'),
        local_response_received_at_utc=datetime.now(UTC).isoformat(),TSA=TSA_URL,
        proof_scope='Manifest bytes existed no later than signed TSA generation time, subject to trusted CA/TSA.',
        original_historical_receipt_proved=False,independent_authority=all(checks.values()),automatic_retry=False)
    write_json(folder/'result.json',result)
    return result
