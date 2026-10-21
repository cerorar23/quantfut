"""Bounded manual collection: two calendar requests and six public sources.

Preserves receipt time and bytes; never treats a schedule as a physical start.
No Odds API credits and no wagering operations.
"""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from pypdf import PdfReader
from tennis_engine.operations import now
from tennis_engine.state_capture import TennisStateCapture

SOURCES={
 'almaty_op':'https://www.protennislive.com/posting/2026/9410/op.pdf',
 'brussels_op':'https://www.protennislive.com/posting/2026/7485/op.pdf',
 'osaka_op':'https://wtafiles.wtatennis.com/pdf/draws/2026/405/OP.pdf',
 'ningbo_op':'https://wtafiles.wtatennis.com/pdf/draws/2026/2092/OP.pdf',
 'palm_hills_tie':'https://legacy-daviscup.itftennis.com/en/draws-results/tie.aspx?id=M-DC-2025-WG2-M-LBN-BAR-01',
 'api_tennis_docs':'https://api-tennis.com/documentation'}

def write(path,value):
 with Path(path).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--credential-file',type=Path,required=True)
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 values=dict(line.strip().split('=',1) for line in args.credential_file.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
 key=values['API_TENNIS_KEY'];client=TennisStateCapture(args.output/'state_capture',key,daily_limit=2)
 captures=[]
 for tour in ('265','266'):
  result=client.capture('get_fixtures',dict(date_start='2026-10-19',date_stop='2026-10-21',event_type_key=tour,timezone='UTC'))
  captures.append(dict(receipt_id=result['receipt']['id'],rows=result['observations_added']))
 public=[]
 for label,url in SOURCES.items():
  folder=args.output/'sources'/label;folder.mkdir(parents=True)
  receipt=dict(url=url,requested_at=now(),label=label,accepted_document=False)
  try:
   response=requests.get(url,timeout=(10,35),allow_redirects=False)
   receipt.update(received_at=now(),http_status=response.status_code)
   if len(response.content)>5000000:raise ValueError('Public document exceeds bound')
   source=folder/('source.pdf' if response.content.startswith(b'%PDF') else 'source.html');source.write_bytes(response.content)
   receipt.update(source_path=str(source.resolve()),sha256=hashlib.sha256(response.content).hexdigest())
   if response.status_code==200 and response.content.startswith(b'%PDF'):
    reader=PdfReader(source)
    if len(reader.pages)>3:raise ValueError('Unexpected schedule page count')
    text='\n'.join(page.extract_text(extraction_mode='layout') for page in reader.pages)
    (folder/'source.txt').write_text(text,encoding='utf8');receipt.update(accepted_document=True,pages=len(reader.pages))
  except Exception as error:
   receipt.update(error_type=type(error).__name__,received_at=now())
  write(folder/'receipt.json',receipt);public.append(receipt)
 report=dict(schema='tennis-audit-evidence-capture-v1',captured_at=now(),api_tennis_requests=2,public_requests=len(SOURCES),
  api_captures=captures,state_summary=client.store.summary(now()),public_sources=public,
  provider_quota_confirmed=False,odds_api_requests=0,odds_credits=0,actual_wagers_placed=0)
 write(args.output/'capture_report.json',report)
 print(json.dumps(dict(state_summary=report['state_summary'],accepted_schedules=[r['label'] for r in public if r['accepted_document']],odds_credits=0)))

if __name__=='__main__':main()
