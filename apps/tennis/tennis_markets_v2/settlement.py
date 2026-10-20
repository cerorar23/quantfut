"""Explicit Pinnacle profile; uncertain retirement props stay pending."""
import re,math
from tennis_engine.scoring import Rules
from tennis_engine.normalize import standard_score
from tennis_engine.settlement import PINNACLE_RULE,SOURCE
from tennis_engine.operations import utc
from .catalog import Contract,PERIOD_KINDS

def settle_contract(bet,result):
 c=Contract(**bet['contract']);rules=Rules(result['best_of']);c.validate(rules)
 stake,odd=bet['stake'],bet['decimal_odds']
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (stake,odd)) or stake<=0 or odd<=1:raise ValueError('Invalid stake/odds')
 response=dict(status='pending',profit=None,rule_source=SOURCE,retirements_excluded=False)
 if bet.get('bookmaker')!='pinnacle' or bet.get('rule_id')!=PINNACLE_RULE or utc(bet['placed_at'])<utc('2026-10-16T00:00:00Z'):return dict(response,reason='Rule applicability unverified')
 status=result['status'];completed=result['completed_sets']
 if type(completed) is not int or not 0<=completed<=rules.best_of:raise ValueError('Invalid completed set count')
 def finish(value):
  return dict(response,status=value,profit=stake*(odd-1) if value=='win' else -stake if value=='loss' else 0.)
 if status=='walkover':
  if completed:raise ValueError('Walkover cannot contain completed sets')
  return finish('void')
 if status not in ('completed','retired','disqualified'):return response
 if status=='completed':
  full=result.get('score_A_B','')
  if not full.split() or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?',s) for s in full.split()):return response
  tokens=[tuple(map(int,t)) for t in re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',full)]
  reverse=' '.join(f'{b}-{a}' for a,b in tokens)
  if len(tokens)!=completed or not (standard_score(full,rules.best_of) or standard_score(reverse,rules.best_of)):return response
  actual_winner='A' if sum(a>b for a,b in tokens)>sum(a<b for a,b in tokens) else 'B'
  if result.get('official_winner')!=actual_winner:return dict(response,reason='Official winner and completed score differ')
 if c.kind=='winner':
  if not completed:return finish('void') if status!='completed' else response
  winner=result.get('official_winner')
  return finish('win' if winner==c.selection else 'loss') if winner in ('A','B') else response
 period=c.kind in PERIOD_KINDS
 if status!='completed' and not period:
  if c.kind=='tiebreak':return dict(response,reason='Retirement tiebreak prop needs a specific completed-market rule')
  return finish('void')
 if period and completed<c.set_number:return finish('void')
 score=result.get('score_A_B','')
 if not score.split() or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?',s) for s in score.split()):return response
 sets=[tuple(map(int,pair)) for pair in re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',score)]
 if len(sets)<completed:return response
 closed=sets[:completed]
 if any(not ((max(a,b)==6 and min(a,b)<=4) or (max(a,b)==7 and min(a,b) in (5,6))) for a,b in closed):return response
 if status=='completed':
  reversed_score=' '.join(f'{b}-{a}' for a,b in sets)
  if len(sets)!=completed or not (standard_score(score,rules.best_of) or standard_score(reversed_score,rules.best_of)):return response
 if period:
  a,b=closed[c.set_number-1]
  value=(a-b)*(1 if c.selection=='A' else -1) if c.kind=='set_winner' else (a+b-c.line)*(1 if c.selection=='over' else -1) if c.kind=='set_games_total' else (a-b if c.selection=='A' else b-a)+c.line
 else:
  a=sum(x>y for x,y in closed);b=completed-a;ga=sum(x for x,y in closed);gb=sum(y for x,y in closed)
  if c.kind=='correct_score':value=1 if (a,b)==c.score else -1
  elif c.kind=='tiebreak':value=1 if any(max(x,y)==7 and min(x,y)==6 for x,y in closed)==(c.selection=='yes') else -1
  elif c.kind=='sets_total':value=(a+b-c.line)*(1 if c.selection=='over' else -1)
  elif c.kind=='sets_handicap':value=(a-b if c.selection=='A' else b-a)+c.line
  elif c.kind=='games_total':value=(ga+gb-c.line)*(1 if c.selection=='over' else -1)
  else:value=(ga-gb if c.selection=='A' else gb-ga)+c.line
 return finish('push' if abs(value)<1e-12 else 'win' if value>0 else 'loss')
