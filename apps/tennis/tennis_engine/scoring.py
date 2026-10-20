"""Exact conditional scoring, with joint games/sets and no probability truncation."""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from math import comb, isfinite
import numpy as np


def probability(p):
    if not isfinite(p) or not 0 < p < 1:
        raise ValueError('Serve probabilities must be strictly between zero and one')
    return float(p)


def hold(p, no_ad=False):
    p = probability(p)
    early = sum(comb(3+k, k)*p**4*(1-p)**k for k in range(3))
    reach = comb(6, 3)*p**3*(1-p)**3
    deuce = p if no_ad else p*p/(p*p+(1-p)**2)
    return early + reach*deuce


def tiebreak(p, q, first_server=0, target=7):
    p, q = probability(p), probability(q)
    if first_server not in (0, 1) or target not in (7, 10):
        raise ValueError('Unsupported tiebreak configuration')

    def a_point(k):
        server = first_server if k == 0 or ((k-1)//2)%2 else 1-first_server
        return p if server == 0 else 1-q

    # Beyond target-1 all tied scores have the same modulo-4 service phase.
    x, y = a_point(2*(target-1)), a_point(2*(target-1)+1)
    win_deuce = x*y/(x*y+(1-x)*(1-y))

    @lru_cache(None)
    def rec(a, b):
        if max(a,b) >= target and abs(a-b) >= 2:
            return float(a>b)
        if a == b == target-1:
            return win_deuce
        v = a_point(a+b)
        return v*rec(a+1,b)+(1-v)*rec(a,b+1)
    return rec(0,0)


@dataclass(frozen=True)
class Rules:
    best_of: int = 3
    no_ad: bool = False
    deciding_tiebreak: int = 7

    def __post_init__(self):
        if self.best_of not in (3,5) or self.deciding_tiebreak not in (7,10):
            raise ValueError('Supports best of 3/5 and final-set tiebreak at 6-all to 7/10')


def set_distribution(p, q, first_server=0, target=7, no_ad=False):
    p, q = probability(p), probability(q)
    if first_server not in (0,1):
        raise ValueError('Invalid first server')
    a_hold, b_hold = hold(p,no_ad), hold(q,no_ad)
    states, out = {(0,0,first_server):1.0}, defaultdict(float)
    while states:
        nxt = defaultdict(float)
        for (a,b,server), mass in states.items():
            if max(a,b)>=6 and abs(a-b)>=2:
                out[(a,b,server,0)] += mass
                continue
            if a==b==6:
                win=tiebreak(p,q,server,target)
                out[(7,6,1-server,1)] += mass*win
                out[(6,7,1-server,1)] += mass*(1-win)
                continue
            win = a_hold if server==0 else 1-b_hold
            nxt[(a+1,b,1-server)] += mass*win
            nxt[(a,b+1,1-server)] += mass*(1-win)
        states=nxt
    return dict(out)


def match_win(p, q, rules=Rules(), first_server=None):
    """Efficient winner marginal; first_server=None integrates a 50/50 toss."""
    if first_server not in (None,0,1): raise ValueError('Invalid first server')
    need=rules.best_of//2+1
    kernels={}
    for target in {7,rules.deciding_tiebreak}:
        for server in (0,1):
            dist=set_distribution(p,q,server,target,rules.no_ad)
            grouped=defaultdict(float)
            for (ga,gb,next_server,_), mass in dist.items():
                grouped[(int(ga>gb),next_server)]+=mass
            kernels[(target,server)]=grouped

    @lru_cache(None)
    def rec(a,b,server):
        if a==need or b==need:
            return float(a==need)
        target=rules.deciding_tiebreak if a==b==need-1 else 7
        return sum(mass*rec(a+won,b+1-won,next_server)
                   for (won,next_server),mass in kernels[(target,server)].items())
    return (rec(0,0,0)+rec(0,0,1))/2 if first_server is None else rec(0,0,first_server)


def match_distribution(p, q, rules=Rules(), first_server=None):
    """Keys: setsA,setsB,gamesA,gamesB,tiebreaks,first_set_winner(0/1)."""
    if first_server not in (None,0,1): raise ValueError('Invalid first server')
    need=rules.best_of//2+1
    kernels={(target,server):set_distribution(p,q,server,target,rules.no_ad)
             for target in {7,rules.deciding_tiebreak} for server in (0,1)}
    servers=[(0,.5),(1,.5)] if first_server is None else [(first_server,1.)]
    states={(0,0,0,0,0,-1,s):weight for s,weight in servers}
    out=defaultdict(float)
    for _ in range(rules.best_of):
        nxt=defaultdict(float)
        for (sa,sb,ga,gb,tbs,fw,server), mass in states.items():
            target=rules.deciding_tiebreak if sa==sb==need-1 else 7
            for (a,b,ns,tb), chance in kernels[(target,server)].items():
                won=int(a>b)
                na,nb=sa+won,sb+1-won
                first=(0 if won else 1) if fw==-1 else fw
                key=(na,nb,ga+a,gb+b,tbs+tb,first)
                if na==need or nb==need:
                    out[key]+=mass*chance
                else:
                    nxt[(*key,ns)]+=mass*chance
        states=nxt
    if states or abs(sum(out.values())-1)>1e-10:
        raise ArithmeticError('Distribution failed conservation check')
    return dict(out)


def set_winner(p,q,set_number,rules=Rules(),selection='A',first_server=None):
    """Marginal for a numbered set; an unplayed set is a push in this research contract."""
    if not isinstance(set_number,int) or isinstance(set_number,bool) or not 1<=set_number<=rules.best_of:
        raise ValueError('Invalid set number')
    if selection not in ('A','B') or first_server not in (None,0,1): raise ValueError('Invalid set selection/server')
    need=rules.best_of//2+1
    states={(0,0,s):w for s,w in ([(0,.5),(1,.5)] if first_server is None else [(first_server,1.)])}
    wins=losses=pushes=0.
    kernels={(target,server):set_distribution(p,q,server,target,rules.no_ad)
             for target in {7,rules.deciding_tiebreak} for server in (0,1)}
    for number in range(1,set_number+1):
        nxt=defaultdict(float)
        for (sa,sb,server),mass in states.items():
            if max(sa,sb)==need: pushes+=mass;continue
            target=rules.deciding_tiebreak if sa==sb==need-1 else 7
            for (ga,gb,ns,_),chance in kernels[target,server].items():
                won=int(ga>gb);weight=mass*chance
                if number==set_number:
                    if bool(won)==(selection=='A'):wins+=weight
                    else:losses+=weight
                else:nxt[(sa+won,sb+1-won,ns)]+=weight
        states=nxt
    if abs(wins+losses+pushes-1)>1e-10:raise ArithmeticError('Set probability mass mismatch')
    return {'win':wins,'push':pushes,'loss':losses}


def market(dist, kind, line=None, selection='A'):
    """Return win/push/loss; completed matches only, no retirement pricing."""
    allowed={'winner':('A','B'),'first_set':('A','B'),'tiebreak':('yes','no'),
             'games_total':('over','under'),'sets_total':('over','under'),
             'games_handicap':('A','B'),'sets_handicap':('A','B')}
    if kind not in allowed or selection not in allowed[kind]: raise ValueError('Invalid market or selection')
    if kind in ('games_total','sets_total','games_handicap','sets_handicap'):
        if line is None or not isfinite(line) or abs(2*line-round(2*line))>1e-10:
            raise ValueError('Only integer and half lines supported; quarter lines require split settlement')
    wins=pushes=0.
    for (sa,sb,ga,gb,tb,first),mass in dist.items():
        if kind=='winner': value=1 if (sa>sb)==(selection=='A') else -1
        elif kind=='first_set': value=1 if first==(0 if selection=='A' else 1) else -1
        elif kind=='tiebreak': value=1 if (tb>0)==(selection=='yes') else -1
        elif kind=='games_total': value=(ga+gb-float(line))*(1 if selection=='over' else -1)
        elif kind=='sets_total': value=(sa+sb-float(line))*(1 if selection=='over' else -1)
        elif kind=='games_handicap': value=(ga-gb if selection=='A' else gb-ga)+float(line)
        elif kind=='sets_handicap': value=(sa-sb if selection=='A' else sb-sa)+float(line)
        else: raise ValueError('Unknown market')
        wins+=mass*(value>0)
        pushes+=mass*(abs(value)<1e-12)
    return {'win':wins,'push':pushes,'loss':max(0.,1-wins-pushes)}


def price(probabilities, decimal_odds=None):
    w,p,l=(probabilities[k] for k in ('win','push','loss'))
    result={**probabilities,'fair_decimal_odds':(1-p)/w if w>0 else None}
    if decimal_odds is not None:
        if not isfinite(decimal_odds) or decimal_odds<=1:
            raise ValueError('Invalid decimal odds')
        result['expected_return']=w*(decimal_odds-1)-l
    return result
