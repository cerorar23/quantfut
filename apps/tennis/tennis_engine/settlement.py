"""Retirements remain in the ledger. Unknown rules block a complete ROI."""
import math
import re
from .operations import utc
from .normalize import standard_score

PINNACLE_RULE='pinnacle_tennis_verified_2026-10-16'
SOURCE='https://support.pinnacle.com/hc/en-us/articles/46732820954385-How-does-Pinnacle-grade-tennis-matches-in-the-event-of-retirement-or-disqualification'


def settle(bet):
    stake=float(bet['stake']); odds=float(bet['decimal_odds'])
    if not math.isfinite(stake) or stake<=0 or not math.isfinite(odds) or odds<=1:
        raise ValueError('Positive stake and decimal odds above one required')
    result={'bet_id':bet['bet_id'],'status':'pending','profit':None,'stake':stake,
            'rule_id':bet.get('rule_id'),'reason':'Unsupported or unverified rule/market'}
    # A rule observed today cannot certify its historical applicability.
    verified=(bet.get('bookmaker')=='pinnacle' and bet.get('rule_id')==PINNACLE_RULE
              and utc(bet['placed_at'])>=utc('2026-10-16T00:00:00Z'))
    if not verified or bet.get('market') not in ('h2h','first_set','totals','spreads'): return result
    status=bet.get('match_status')
    completed=bet.get('completed_sets')
    if not isinstance(completed,int) or isinstance(completed,bool) or not 0<=completed<=5:
        raise ValueError('Completed set count must be an integer from zero to five')
    selection=bet.get('selection')
    if selection not in (('over','under') if bet['market']=='totals' else ('A','B')):
        raise ValueError('Invalid market selection')
    outcome=None
    if status=='walkover':
        if completed: raise ValueError('Walkover cannot contain played sets')
        outcome='void'
    elif status in ('completed','retired','disqualified'):
        if bet['market'] in ('totals','spreads'):
            if status!='completed':
                # Pinnacle full-match total/spread profile: period must complete.
                outcome='void'
            else:
                score=bet.get('score_A_B',''); best_of=bet.get('best_of',3)
                # Source validator expects winner-first scores. Accept either orientation.
                if not score.split() or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?',s) for s in score.split()): return result
                tokens=re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',score)
                if not tokens: return result
                reverse=' '.join(f'{b}-{a}' for a,b in tokens)
                if not (standard_score(score,best_of) or standard_score(reverse,best_of)): return result
                ga=sum(int(a) for a,b in tokens);gb=sum(int(b) for a,b in tokens)
                line=bet.get('line')
                if not isinstance(line,(int,float)) or not math.isfinite(line) or line*2!=round(line*2):
                    raise ValueError('Integer or half lines required')
                if bet['market']=='totals':
                    value=ga+gb-line
                    if selection=='under': value=-value
                else: value=(ga-gb if selection=='A' else gb-ga)+line
                outcome='push' if value==0 else 'win' if value>0 else 'loss'
        elif bet['market']=='first_set':
            winner=bet.get('first_set_winner')
            if completed and winner in ('A','B'): outcome='win' if winner==selection else 'loss'
            elif not completed and status!='completed': outcome='void'
        elif status in ('retired','disqualified') and not completed:
            outcome='void'
        elif completed:
            winner=bet.get('official_winner')
            if winner in ('A','B'): outcome='win' if winner==selection else 'loss'
    if outcome:
        result.update(status=outcome,profit=stake*(odds-1) if outcome=='win' else -stake if outcome=='loss' else 0.,
                      reason='Settled by explicit verified profile',rule_source=SOURCE)
    return result


def ledger(bets):
    ids=[b['bet_id'] for b in bets]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate bet IDs')
    results=[settle(b) for b in bets]
    pending=sum(r['status']=='pending' for r in results)
    profit=sum(r['profit'] for r in results if r['profit'] is not None)
    turnover=sum(r['stake'] for r in results if r['status'] in ('win','loss','push'))
    return {'bets':results,'count':len(results),'pending':pending,
            'void':sum(r['status']=='void' for r in results),'settled_profit':profit,
            'push':sum(r['status']=='push' for r in results),
            'settled_action_stake':turnover,'total_submitted_stake':sum(r['stake'] for r in results),
            'complete_roi_on_action_stake':profit/turnover if not pending and turnover else None,
            'financial_evaluation_complete':not pending and bool(results),
            'retirements_excluded':False}
