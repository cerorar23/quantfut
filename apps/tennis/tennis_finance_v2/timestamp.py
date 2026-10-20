"""RFC3161 proof of bundle existence, not proof of financial performance."""
from pathlib import Path
import subprocess
import certifi
import requests
from tennis_engine.operations import now
from tennis_engine.paper_validation import digest
from .audit import read, write_new

TSA_URL = "http://timestamp.digicert.com"


def _run(openssl: Path, arguments: list[str]) -> str:
    result = subprocess.run([str(openssl), *arguments], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError("Timestamp verification command failed")
    return result.stdout


def verify_timestamp(root: Path, openssl: Path) -> dict:
    root = Path(root)
    receipt = read(root/'receipt.json')
    for name, expected in receipt['sha256'].items():
        if Path(name).name != name or digest(root/name) != expected:
            raise ValueError("Timestamp proof file changed")
    for arguments in (
        ['-queryfile', str(root/'request.tsq')],
        ['-data', str(root/'bundle.json')],
    ):
        _run(openssl, ['ts', '-verify', '-in', str(root/'response.tsr'),
                       '-CAfile', certifi.where(), *arguments])
    text = _run(openssl, ['ts', '-reply', '-in', str(root/'response.tsr'), '-text'])
    stamp = next((line.split('Time stamp:', 1)[1].strip() for line in text.splitlines() if 'Time stamp:' in line), None)
    if not stamp:
        raise ValueError("Verified timestamp has no readable generation time")
    return dict(cryptographic_verification=True, tsa_generation_time=stamp,
                verification_ca_bundle_sha256=digest(Path(certifi.where())),
                archived_ca_bundle_sha256=digest(root/'trusted-ca.pem'),
                proves='This exact bundle existed by TSA generation time',
                does_not_prove=['Earlier local creation times', 'Correctness of data',
                               'Prospective existence of later orders', 'Profitability'])


def timestamp_bundle(bundle: dict, root: Path, openssl: Path) -> dict:
    """One bounded TSA request sends only a SHA256 imprint and random nonce.

    No API credentials, source files or bundle contents leave the machine.
    Response signature and nonce are verified against the copied CA bundle.
    HTTP is the provider's documented endpoint; signed token is authenticated
    cryptographically. Incomplete attempts remain for inspection, not reused.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    write_new(root/'bundle.json', bundle)
    _run(openssl, ['ts', '-query', '-data', str(root/'bundle.json'), '-sha256',
                   '-cert', '-out', str(root/'request.tsq')])
    started = now()
    response = requests.post(TSA_URL, data=(root/'request.tsq').read_bytes(),
                             headers={'Content-Type': 'application/timestamp-query'}, timeout=30,
                             allow_redirects=False)
    response.raise_for_status()
    if response.headers.get('Content-Type', '').split(';')[0] != 'application/timestamp-reply':
        raise ValueError('Unexpected timestamp response type')
    (root/'response.tsr').write_bytes(response.content)
    (root/'trusted-ca.pem').write_bytes(Path(certifi.where()).read_bytes())
    write_new(root/'receipt.json', dict(requested_at=started, received_at=now(), endpoint=TSA_URL,
        sha256={name: digest(root/name) for name in ('bundle.json', 'request.tsq', 'response.tsr', 'trusted-ca.pem')},
        sent_document_contents=False, sent_api_credentials=False))
    verified = verify_timestamp(root, openssl)
    write_new(root/'verification.json', verified)
    return verified
