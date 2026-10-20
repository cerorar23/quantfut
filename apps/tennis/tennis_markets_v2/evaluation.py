"""Settlement coverage and probability metrics per exact market contract."""
from collections import defaultdict
import json
import math
from tennis_engine.benchmark import probability_metrics
from .settlement import settle_contract

def evaluate_rows(rows):
 """Explicit input ledger; this function does not certify source availability."""
 groups=defaultdict(list);identities=set()
 for item in rows:
  bet=item['bet'];identity=bet['bet_id']
  if identity in identities:raise ValueError('Duplicate bet identity')
  identities.add(identity)
  settled=settle_contract(bet,item['result']);prob=item.get('probabilities')
  if prob is not None:
   values=[prob[k] for k in ('win','push','loss')]
   if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in values) or abs(sum(values)-1)>1e-9:raise ValueError('Invalid forecast mass')
   if settled['status'] in ('win','loss') and prob['push']>=1:raise ValueError('Binary score incompatible with guaranteed push')
  group=json.dumps(dict(circuit=item['circuit'],contract=bet['contract']),sort_keys=True)
  groups[group].append(dict(bet_id=identity,stake=bet['stake'],**settled,probabilities=prob))
 result=[]
 for group,values in groups.items():
  pending=sum(r['status']=='pending' for r in values);action=[r for r in values if r['status'] in ('win','loss','push')]
  binary=[r for r in values if r['status'] in ('win','loss') and r['probabilities'] is not None]
  # Pushes are outside the conditional binary contract, but remain in the ledger.
  metrics=probability_metrics([int(r['status']=='win') for r in binary],
   [r['probabilities']['win']/(1-r['probabilities']['push']) for r in binary]) if binary else None
  stake=sum(r['stake'] for r in action);profit=sum(r['profit'] for r in values if r['profit'] is not None)
  result.append(dict(**json.loads(group),rows=values,total=len(values),pending=pending,void=sum(r['status']=='void' for r in values),
   push=sum(r['status']=='push' for r in values),metrics=metrics,metric_coverage=len(binary)/len(values),
   settled_profit=profit,roi_on_action_stake=profit/stake if stake and not pending else None,production_approved=False))
 return dict(groups=result,financial_evidence_verified=False,production_approved=False,
  limit='Metrics describe supplied rows, not a prospective profitability certificate; evidence and model protocol are external requirements.')
