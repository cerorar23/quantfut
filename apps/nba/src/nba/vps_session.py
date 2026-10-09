"""Finite operational tests over one SSH process, never an automatic retry."""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import json
import shlex
import subprocess
import time

from .vps_telegram import REMOTE
from .clock_policy import remote_deadline


def remote_program():
    prefix = REMOTE.split('try:outcome=run()')[0].replace('request=REQUEST_JSON', 'request={}', 1)
    return prefix + '''
import sys,time
print(json.dumps(dict(ready=True)),flush=True)
for line in sys.stdin:
    began=time.monotonic()
    try:
        request=json.loads(line)
        outcome=run()
    except Exception:
        outcome=dict(state='unknown',reason='remote_transport_uncertain',automatic_retry=False)
    outcome['remote_elapsed_seconds']=time.monotonic()-began
    print(json.dumps(dict(request_id=request.get('request_id'),outcome=outcome)),flush=True)
    if outcome['state']=='unknown':break
'''


class OperationalSession:
    """Caller must durably seal and claim each ID. Uncertainty poisons this session."""
    def __init__(self, max_messages=3, process_factory=subprocess.Popen, remote_code=None):
        if type(max_messages) is not int or not 1 <= max_messages <= 3:
            raise ValueError('one to three authorized technical tests only')
        self.limit, self.used, self.poisoned = max_messages, 0, False
        self.executor = ThreadPoolExecutor(max_workers=1)
        started = time.monotonic()
        self.process = process_factory(
            ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'quantfut',
             'python3 -u -c ' + shlex.quote(remote_code if remote_code is not None else remote_program())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            if json.loads(self._read()) != {'ready': True}:
                raise ValueError('invalid ready handshake')
        except Exception:
            self.close()
            raise RuntimeError('operational SSH session unavailable') from None
        self.startup_seconds = time.monotonic() - started
        self.ready_at_utc = datetime.now(UTC).isoformat()

    def _read(self):
        return self.executor.submit(self.process.stdout.readline).result(timeout=15)

    def sender(self, identifier, expires_at_utc, clock_bounds=None):
        def send(text):
            if not text.startswith('PRUEBA TÉCNICA NBA'):
                raise ValueError('operational test text required')
            if self.poisoned or self.used >= self.limit:
                raise ValueError('closed or exhausted finite session')
            try:
                admission=remote_deadline(expires_at_utc,datetime.now(UTC).isoformat(),clock_bounds)
            except (ValueError,KeyError,TypeError):
                admission=dict(admitted=False,reason='clock_or_expiry_invalid')
            if not admission['admitted']:
                return dict(state='rejected',reason=admission['reason'],send_attempted=False,automatic_retry=False,
                    transport_kind='live_VPS_reused_SSH_operational_test')
            self.used += 1
            try:
                self.process.stdin.write(json.dumps(dict(request_id=identifier, text=text,
                    expires_at_utc=admission['remote_expires_at_utc'])) + '\n')
                self.process.stdin.flush()
                envelope = json.loads(self._read())
                if set(envelope) != {'request_id', 'outcome'} or envelope['request_id'] != identifier:
                    raise ValueError('response identity mismatch')
                outcome = envelope['outcome']
                allowed = {'state','reason','send_attempted','error_code','automatic_retry','message_id',
                    'telegram_server_date','destination_matches_authorized_chat','VPS_response_at_utc',
                    'subscriber_receipt_verified','remote_elapsed_seconds'}
                if set(outcome) - allowed or outcome.get('state') not in {'sent','rejected','unknown'}:
                    raise ValueError('invalid remote response')
                duration = outcome.get('remote_elapsed_seconds')
                if type(duration) not in {int,float} or not 0 <= duration < 15:
                    raise ValueError('invalid remote timing')
                if outcome['state'] == 'sent':
                    if (type(outcome.get('message_id')) is not int or outcome['message_id'] <= 0
                            or outcome.get('destination_matches_authorized_chat') is not True):
                        raise ValueError('unverified message or destination')
                    outcome['acknowledged_at_utc'] = datetime.now(UTC).isoformat()
                if outcome['state'] == 'unknown':
                    self.poisoned = True
                return dict(outcome, transport_kind='live_VPS_reused_SSH_operational_test')
            except Exception:
                self.poisoned = True
                return dict(state='unknown', reason='session_transport_uncertain', automatic_retry=False,
                    transport_kind='live_VPS_reused_SSH_operational_test')
        return send

    def close(self):
        self.poisoned = True
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.executor.shutdown(wait=False, cancel_futures=True)

