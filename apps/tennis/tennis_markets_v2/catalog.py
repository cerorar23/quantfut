"""Coherent Markov market probabilities, including pushes and numbered sets."""
from dataclasses import dataclass,asdict
from collections import defaultdict
from math import isfinite
from tennis_engine.scoring import Rules,match_distribution,set_distribution,market,price

KINDS={'winner','set_winner','games_total','games_handicap','sets_total','sets_handicap','tiebreak','correct_score','set_games_total','set_games_handicap'}
LINE_KINDS={'games_total','games_handicap','sets_total','sets_handicap','set_games_total','set_games_handicap'}
PERIOD_KINDS={'set_winner','set_games_total','set_games_handicap'}

@dataclass(frozen=True)
class Contract:
 kind:str
 selection:str
 line:float|None=None
 set_number:int|None=None
 score:tuple[int,int]|None=None

 def __post_init__(self):
  if isinstance(self.score,list):object.__setattr__(self,'score',tuple(self.score))

 def validate(self,rules):
  if self.kind not in KINDS:raise ValueError('Unsupported market family')
  allowed=('over','under') if 'total' in self.kind else ('yes','no') if self.kind=='tiebreak' else ('exact',) if self.kind=='correct_score' else ('A','B')
  if self.selection not in allowed:raise ValueError('Invalid selection')
  if self.kind in LINE_KINDS:
   if isinstance(self.line,bool) or not isinstance(self.line,(int,float)) or not isfinite(self.line) or abs(self.line*2-round(self.line*2))>1e-10:raise ValueError('Integer and half lines required; quarter contracts not supported')
   if 'total' in self.kind and self.line<0:raise ValueError('Total cannot be negative')
  elif self.line is not None:raise ValueError('Unexpected line')
  if self.kind in PERIOD_KINDS:
   if type(self.set_number) is not int or not 1<=self.set_number<=rules.best_of:raise ValueError('Explicit valid set number required')
  elif self.set_number is not None:raise ValueError('Unexpected set number')
  if self.kind=='correct_score':
   need=rules.best_of//2+1
   if not isinstance(self.score,tuple) or len(self.score)!=2 or any(type(v) is not int or v<0 for v in self.score) or max(self.score)!=need or min(self.score)>=need:raise ValueError('Invalid final set score')
  elif self.score is not None:raise ValueError('Unexpected exact score')
  return self

class MarketEngine:
 """One joint MAP model for every marginal; hybrid winner kept separate."""
 def __init__(self,p,q,rules=Rules(),first_server=None):
  if first_server not in (None,0,1) or isinstance(first_server,bool):raise ValueError('Invalid first server')
  self.p,self.q,self.rules,self.first_server=p,q,rules,first_server
  self.joint=match_distribution(p,q,rules,first_server=first_server)
  if abs(sum(self.joint.values())-1)>1e-9 or any(v<0 for v in self.joint.values()):raise ArithmeticError('Joint mass invalid')
  self.periods={}

 def period(self,number):
  if type(number) is not int or not 1<=number<=self.rules.best_of:raise ValueError('Invalid numbered set')
  if number in self.periods:return self.periods[number]
  need=self.rules.best_of//2+1
  states={(0,0,s):w for s,w in ([(0,.5),(1,.5)] if self.first_server is None else [(self.first_server,1.)])}
  result=defaultdict(float);unplayed=0.
  kernels={(t,s):set_distribution(self.p,self.q,s,t,self.rules.no_ad) for t in {7,self.rules.deciding_tiebreak} for s in (0,1)}
  for step in range(1,number+1):
   nxt=defaultdict(float)
   for (sa,sb,server),mass in states.items():
    if max(sa,sb)==need:unplayed+=mass;continue
    target=self.rules.deciding_tiebreak if sa==sb==need-1 else 7
    for (ga,gb,ns,_),chance in kernels[target,server].items():
     weight=mass*chance;won=int(ga>gb)
     if step==number:result[ga,gb]+=weight
     else:nxt[sa+won,sb+1-won,ns]+=weight
   states=nxt
  if abs(sum(result.values())+unplayed-1)>1e-9:raise ArithmeticError('Period mass invalid')
  self.periods[number]=(result,unplayed);return result,unplayed

 def probabilities(self,contract):
  c=contract.validate(self.rules)
  if c.kind in PERIOD_KINDS:
   distribution,push=self.period(c.set_number);win=0.
   for (a,b),mass in distribution.items():
    value=(a-b)*(1 if c.selection=='A' else -1) if c.kind=='set_winner' else (a+b-c.line)*(1 if c.selection=='over' else -1) if c.kind=='set_games_total' else (a-b if c.selection=='A' else b-a)+c.line
    win+=mass*(value>0);push+=mass*(abs(value)<1e-12)
   return dict(win=win,push=push,loss=max(0.,1-win-push))
  if c.kind=='correct_score':
   win=sum(m for (a,b,*_),m in self.joint.items() if (a,b)==c.score)
   return dict(win=win,push=0.,loss=1-win)
  return market(self.joint,c.kind,c.line,c.selection)

 def quote(self,contract,decimal_odds=None):
  result=price(self.probabilities(contract),decimal_odds)
  if 'expected_return' in result:result['conditional_expected_return_completed_match']=result.pop('expected_return')
  return dict(contract=asdict(contract),**result,model='joint_markov_MAP_v2',calibration_status='uncalibrated_marginal',
   unplayed_set_is_push=True if contract.kind in PERIOD_KINDS else None,production_approved=False,executable=False)

 def standard_board(self):
  rows=[]
  for side in ('A','B'):
   rows.append(self.quote(Contract('winner',side)))
   for number in (1,2):rows.append(self.quote(Contract('set_winner',side,set_number=number)))
  for side in ('yes','no'):rows.append(self.quote(Contract('tiebreak',side)))
  need=self.rules.best_of//2+1
  for loser in range(need):
   for score in ((need,loser),(loser,need)):rows.append(self.quote(Contract('correct_score','exact',score=score)))
  for kind,lines in [('games_total',[18.5,20.5,21.5,22.5,23.5,24.5,26.5]),('games_handicap',[-5.5,-3.5,-1.5,0,1.5,3.5,5.5]),('sets_total',[2.5] if need==2 else [3.5,4.5]),('sets_handicap',[-1.5,1.5])]:
   for line in lines:
    for side in (('over','under') if 'total' in kind else ('A','B')):rows.append(self.quote(Contract(kind,side,line)))
  for number in (1,2):
   for line in (8.5,9.5,10.5,12.5):
    for side in ('over','under'):rows.append(self.quote(Contract('set_games_total',side,line,number)))
   for line in (-2.5,-1.5,1.5,2.5):
    for side in ('A','B'):rows.append(self.quote(Contract('set_games_handicap',side,line,number)))
  return rows
