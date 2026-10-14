"""Fetch oficial con coste por respuesta, presupuesto compartido y clave en env."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading

from qf.ingest.soccerdata_transport import validated_url


class CreditBudget:
    def __init__(self, available, max_requests, reserve=100):
        self.remaining=available
        self.max_requests=max_requests
        self.reserve=reserve
        self.calls=0
        self.blocked=None
        self.lock=threading.Lock()

    def acquire(self):
        with self.lock:
            if self.blocked or self.calls>=self.max_requests or self.remaining<self.reserve+25:
                raise RuntimeError('request_or_credit_budget_exhausted')
            self.remaining-=25
            self.calls+=1

    def settle(self,cost):
        # Missing/error cost stays reserved at 25. Never infer free failures.
        if not isinstance(cost,(int,float)) or isinstance(cost,bool) or not 0<=cost<=25:
            return
        with self.lock:
            self.remaining+=25-cost

    def halt(self,reason):
        with self.lock:self.blocked=reason


class ZenRowsCLI:
    def __init__(self,workspace,budget,*,country=None):
        self.workspace=Path(workspace).resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        (self.workspace/'.zenrows').mkdir(exist_ok=True)
        self.budget=budget
        self.country=country
        self.secret=os.environ.get('ZENROWS_API_KEY')
        if not self.secret:
            raise RuntimeError('explicit_task_key_required')

    def scrape(self,url):
        validated_url(url)
        if self.country is not None and not re.fullmatch('[A-Z]{2}',self.country):
            raise ValueError('invalid_proxy_country')
        self.budget.acquire()
        key=hashlib.sha256(url.encode()).hexdigest()
        body_path=self.workspace/(key+'.response')
        cmd=[shutil.which('npx.cmd' if os.name=='nt' else 'npx'),'-y','@zenrows/cli@1.5.0',
             'fetch',url,'--no-signup','--json','--original-status','--output','html',
             '--out',str(body_path),'--timeout','120000']
        if self.country:
            cmd+=['--proxy-country',self.country]
        started=datetime.now(timezone.utc).isoformat()
        try:
            completed=subprocess.run(cmd,cwd=self.workspace,env=os.environ.copy(),
                capture_output=True,text=True,encoding='utf-8',timeout=135)
        except subprocess.TimeoutExpired:
            raise TimeoutError('cli_timeout_no_retry') from None
        stdout=completed.stdout.replace(self.secret,'[REDACTED]')
        try:result=json.loads(stdout)
        except ValueError:raise ValueError('invalid_cli_metadata') from None
        error_code=(result.get('error') or {}).get('code')
        if error_code in {'AUTH_INVALID','AUTH_MISSING','CREDITS_EXHAUSTED','KEY_CREDIT_CAP_REACHED',
                          'POLICY_MAX_CREDITS_EXCEEDED'}:
            self.budget.halt(error_code)
        cost=result.get('costCredits')
        self.budget.settle(cost)
        status=result.get('httpStatus')
        failed=completed.returncode!=0 or not result.get('ok') or status!=200
        if body_path.exists():
            raw=body_path.read_bytes().replace(self.secret.encode(),b'[REDACTED]')
        else:
            raw=json.dumps(result,ensure_ascii=False).encode()
        if len(raw)>24_000_000:
            raise ValueError('source_response_too_large')
        receipt={'url':url,'started_at':started,'received_at':datetime.now(timezone.utc).isoformat(),
            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'provider_error':failed,
            'transport':'ZenRows CLI 1.5.0','mode':'adaptive','http_status':status,
            'cost_credits':cost,'run_id':result.get('runId'),
            'parameters':{'response_type':'html','original_status':True}}
        if error_code:
            receipt['error_code']=error_code
        if self.country:receipt['parameters']['proxy_country']=self.country
        return raw,receipt
