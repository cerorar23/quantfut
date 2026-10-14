"""Cliente del MCP ZenRows configurado: sin compras, secretos ni reintentos."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import re

from qf.ingest.soccerdata_transport import validated_url


class ZenRowsMCP:
    def __init__(self, root, reserve=100, max_requests=80, *, default_country='GB'):
        server = json.loads((Path(root)/'.mcp.json').read_text())['mcpServers']['zenrows']
        if server['command'] != 'npx' or server['args'] != ['-y', '@zenrows/mcp@2.4.0']:
            raise ValueError('unexpected_mcp_version')
        # Task-specific credentials override the shared configuration in memory.
        self.secret = os.environ.get('ZENROWS_API_KEY') or server['env']['ZENROWS_API_KEY']
        env = dict(os.environ, **server['env'])
        env['ZENROWS_API_KEY'] = self.secret
        env.pop('ZENROWS_JS_RENDER', None)
        env.pop('ZENROWS_PREMIUM_PROXY', None)
        executable = shutil.which('npx.cmd' if os.name == 'nt' else 'npx')
        self.process = subprocess.Popen([executable, *server['args']], cwd=root, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8')
        self.messages = queue.Queue()
        self.sequence = self.calls = 0
        self.reserve, self.max_requests = reserve, max_requests
        self.default_country = default_country
        self.remaining_floor = None
        self.usage_last = None
        def read_stdout():
            for line in self.process.stdout:
                if len(line) > 26_000_000:
                    self.messages.put({'fatal': True})
                    continue
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    continue
        def discard_stderr():
            for _ in self.process.stderr:
                pass
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=discard_stderr, daemon=True).start()
        self.rpc('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
            'clientInfo':{'name':'QuantFut-soccerdata','version':'1'}})
        self.send({'jsonrpc':'2.0','method':'notifications/initialized'})

    def send(self, value):
        self.process.stdin.write(json.dumps(value)+'\n')
        self.process.stdin.flush()

    def rpc(self, method, params):
        self.sequence += 1
        seq = self.sequence
        self.send({'jsonrpc':'2.0','id':seq,'method':method,'params':params})
        deadline = time.monotonic()+110
        while time.monotonic() < deadline:
            try:
                response = self.messages.get(timeout=1)
            except queue.Empty:
                if self.process.poll() is not None:
                    raise RuntimeError('mcp_process_exited')
                continue
            if response.get('fatal'):
                raise ValueError('mcp_response_too_large')
            if response.get('id') != seq:
                continue
            if 'error' in response:
                raise RuntimeError('mcp_protocol_error')
            return json.loads(json.dumps(response['result']).replace(self.secret,'[REDACTED]'))
        raise TimeoutError('mcp_timeout_no_retry')

    def usage(self):
        result = self.rpc('tools/call', {'name':'account_usage','arguments':{}})
        if result.get('isError'):
            raise RuntimeError('account_usage_unavailable')
        content = [x['text'] for x in result['content'] if x['type']=='text']
        data = json.loads(content[0])
        # Use only quota fields; never persist customer/account identifiers.
        if 'credit_limit' not in data or 'usage_credits' not in data:
            raise ValueError('unexpected_account_usage_shape')
        safe = {k:data[k] for k in ('credit_limit','usage_credits','status') if k in data}
        api_product=((data.get('plan') or {}).get('products') or {}).get('api') or {}
        concurrency=api_product.get('concurrency') or {}
        if isinstance(concurrency.get('limit'),int):
            safe['concurrency_limit']=concurrency['limit']
        if isinstance(concurrency.get('usage'),int):
            safe['concurrency_in_use']=concurrency['usage']
        remaining = safe['credit_limit']-safe['usage_credits']
        caps=(data.get('api_key') or {}).get('caps') or []
        for cap in caps:
            if cap.get('unavailable'):
                raise RuntimeError('key_credit_cap_unavailable')
            if isinstance(cap.get('remaining_credits'),(int,float)):
                remaining=min(remaining,cap['remaining_credits'])
        self.remaining_floor = remaining if self.remaining_floor is None else min(remaining,self.remaining_floor)
        self.usage_last = dict(safe, checked_at=datetime.now(timezone.utc).isoformat(),
                               remaining_floor=self.remaining_floor)
        return self.usage_last

    def scrape(self, url, *, country=None):
        validated_url(url)
        selected_country=country if country is not None else getattr(self,'default_country','GB')
        if selected_country is not None and not re.fullmatch('[A-Z]{2}',selected_country):
            raise ValueError('invalid_proxy_country')
        self.usage()
        if self.calls >= self.max_requests or self.remaining_floor < self.reserve+25:
            raise RuntimeError('request_or_credit_budget_exhausted')
        # Deduct the maximum cost immediately: billing can lag account_usage.
        self.remaining_floor -= 25
        self.calls += 1
        started = datetime.now(timezone.utc).isoformat()
        args = {'url':url, 'response_type':'html'}
        if selected_country is not None and 'sofascore.com/' in url:
            args['proxy_country'] = selected_country
        result = self.rpc('tools/call', {'name':'scrape','arguments':args})
        raw = '\n'.join(x['text'] for x in result.get('content',[]) if x.get('type')=='text').encode()
        return raw, dict(url=url, started_at=started,
            received_at=datetime.now(timezone.utc).isoformat(),
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
            provider_error=bool(result.get('isError')), transport='ZenRows MCP 2.4.0',
            error_codes=sorted(set(re.findall(r'\b(?:AUTH|RESP|REQ)[0-9]{3}\b',raw.decode(errors='replace'))))[:8],
            parameters={k:v for k,v in args.items() if k!='url'}, mode='adaptive')

    def close(self):
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(self.process.pid),'/T','/F'],capture_output=True)
        else:
            self.process.terminate()
