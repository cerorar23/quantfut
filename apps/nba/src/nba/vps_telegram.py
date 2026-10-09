"""Authorized operational test using VPS credentials that never leave the VPS."""
from datetime import UTC,datetime
import json
import subprocess
from .clock_policy import remote_deadline

REMOTE = r'''
import json,urllib.request,urllib.error
from pathlib import Path
from datetime import timezone,datetime
UTC=timezone.utc
request=REQUEST_JSON
def run():
    values={}
    for raw in Path('/home/qf/quantfut/.env').read_text().splitlines():
        line=raw.strip().removeprefix('export ')
        if line.startswith('#') or '=' not in line:continue
        key,value=line.split('=',1);key=key.strip()
        if key not in {'TG_BOT_TOKEN','TG_ALERT_CHAT'}:continue
        if key in values:raise ValueError('duplicate authorized field')
        value=value.strip()
        if value[:1] in {'"',"'"}:
            quote=value[0];end=value.find(quote,1)
            if end<0 or value[end+1:].strip() and not value[end+1:].strip().startswith('#'):raise ValueError('nonliteral config')
            value=value[1:end]
        else:value=value.split(' #',1)[0].strip()
        if '$' in value or '`' in value:raise ValueError('nonliteral config')
        values[key]=value
    if not values.get('TG_BOT_TOKEN') or not values.get('TG_ALERT_CHAT'):
        return dict(state='rejected',reason='authorized_config_missing')
    expires=datetime.fromisoformat(request['expires_at_utc'])
    if expires.tzinfo is None or datetime.now(UTC)>=expires:
        return dict(state='rejected',reason='expired_on_VPS',send_attempted=False)
    text=request['text']
    if not text.startswith('PRUEBA TÉCNICA NBA'):raise ValueError('operational text required')
    payload=json.dumps(dict(chat_id=values['TG_ALERT_CHAT'],text=text)).encode()
    http=urllib.request.Request('https://api.telegram.org/bot'+values['TG_BOT_TOKEN']+'/sendMessage',
        data=payload,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(http,timeout=10) as response:body=json.loads(response.read())
    except urllib.error.HTTPError as error:
        return dict(state='rejected' if error.code<500 else 'unknown',error_code=error.code,automatic_retry=False)
    result=body.get('result',{});mid=result.get('message_id')
    if body.get('ok') is True and type(mid) is int and mid>0:
        destination_matches=str(result.get('chat',{}).get('id'))==values['TG_ALERT_CHAT']
        return dict(state='sent',message_id=mid,telegram_server_date=result.get('date'),
            destination_matches_authorized_chat=destination_matches,
            VPS_response_at_utc=datetime.now(UTC).isoformat(),subscriber_receipt_verified=False)
    return dict(state='unknown',reason='unconfirmed_Telegram_result',automatic_retry=False)
try:outcome=run()
except Exception:outcome=dict(state='unknown',reason='remote_transport_uncertain',automatic_retry=False)
print(json.dumps(outcome))
'''


def vps_sender(expires_at_utc, clock_bounds=None):
    """One SSH/POST per invocation; an ambiguous outcome is never retried here."""
    def send(text):
        if not text.startswith('PRUEBA TÉCNICA NBA'):
            raise ValueError('operational test text required')
        try:admission=remote_deadline(expires_at_utc,datetime.now(UTC).isoformat(),clock_bounds)
        except (ValueError,KeyError,TypeError):admission=dict(admitted=False,reason='clock_or_expiry_invalid')
        if not admission['admitted']:
            return dict(state='rejected',reason=admission['reason'],send_attempted=False,automatic_retry=False,
                transport_kind='live_VPS_Telegram_operational_test')
        request=dict(text=text,expires_at_utc=admission['remote_expires_at_utc'])
        code=REMOTE.replace('REQUEST_JSON',repr(request),1)
        try:
            result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','quantfut','python3 -'],
                input=code,encoding='utf-8',capture_output=True,timeout=25,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode!=0:raise ValueError('SSH failed')
            outcome=json.loads(result.stdout)
            allowed={'state','reason','send_attempted','error_code','automatic_retry','message_id','telegram_server_date',
                     'destination_matches_authorized_chat','VPS_response_at_utc','subscriber_receipt_verified'}
            if set(outcome)-allowed or outcome.get('state') not in {'sent','rejected','unknown'}:
                raise ValueError('invalid remote result')
            if outcome['state']=='sent':
                if type(outcome.get('message_id')) is not int or outcome['message_id']<=0 or outcome.get('destination_matches_authorized_chat') is not True:
                    raise ValueError('message or destination unverified')
                outcome['acknowledged_at_utc']=datetime.now(UTC).isoformat()
            outcome['transport_kind']='live_VPS_Telegram_operational_test'
            return outcome
        except Exception:
            return dict(state='unknown',reason='SSH_or_transport_uncertain',automatic_retry=False,
                        transport_kind='live_VPS_Telegram_operational_test')
    return send
