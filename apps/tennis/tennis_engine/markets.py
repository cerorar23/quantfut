"""Map actual bookmaker lines to the declared joint completed-match model."""
import math
from collections import defaultdict
from .scoring import Rules, match_distribution, market, price, set_winner


SUPPORTED={'h2h','h2h_s1','h2h_s2','spreads','alternate_spreads','totals','alternate_totals'}


def compare_offered(event,prediction,gates=None):
    """All observations stay non-executable. Unsupported markets remain visible."""
    sides={event['home_team']:'A',event['away_team']:'B'}
    dist=None;rows=[]
    checks={(g['bookmaker'],g['market']):g for g in (gates or [])}
    for book in event.get('bookmakers',[]):
        for offered in book.get('markets',[]):
            key=offered['key']
            gate=checks.get((book['key'],key),{'data_eligible':False,'reasons':['no_freshness_evidence']})
            for outcome in offered.get('outcomes',[]):
                row={'bookmaker':book['key'],'market':key,'selection':outcome.get('name'),
                     'description':outcome.get('description'),'line':outcome.get('point'),
                     'decimal_odds':outcome.get('price'),'status':'unsupported_market',
                     'data_eligible':gate['data_eligible'],'data_reasons':gate['reasons'],
                     'executable':False,'scope':'Conditional on completed match; retirement risk not priced'}
                rows.append(row)
                if key not in SUPPORTED: continue
                odd=outcome.get('price')
                if isinstance(odd,bool) or not isinstance(odd,(int,float)) or not math.isfinite(odd) or odd<=1:
                    row['status']='invalid_price';continue
                if not prediction: row['status']='missing_prediction';continue
                name=outcome.get('name')
                try:
                    if key=='h2h':
                        side=sides[name];prob=prediction['winner_'+side]
                        if not math.isfinite(prob) or not 0<=prob<=1: raise ValueError()
                        probabilities={'win':prob,'push':0.,'loss':1-prob}
                        row['model']='hybrid_winner_only'
                        spec=None
                    elif key=='h2h_s2':
                        probabilities=set_winner(prediction['serve']['p'],prediction['serve']['q'],2,
                            Rules(prediction['best_of'],deciding_tiebreak=prediction['deciding_tiebreak']),sides[name])
                        row['model']='joint_markov_MAP_uncalibrated'
                        spec=None
                    else:
                        if dist is None:
                            dist=match_distribution(prediction['serve']['p'],prediction['serve']['q'],
                                Rules(prediction['best_of'],deciding_tiebreak=prediction['deciding_tiebreak']))
                        if key=='h2h_s1': spec=('first_set',None,sides[name])
                        elif key in ('totals','alternate_totals'):
                            spec=('games_total',outcome.get('point'),{'Over':'over','Under':'under'}[name])
                        else: spec=('games_handicap',outcome.get('point'),sides[name])
                        probabilities=market(dist,*spec)
                        row['model']='joint_markov_MAP_uncalibrated'
                    quoted=price(probabilities,odd)
                    # Never label this as unconditional betting EV: retirement risk is absent.
                    quoted['conditional_expected_return']=quoted.pop('expected_return')
                    row.update(quoted,status='priced_research')
                    if spec is not None and prediction.get('derivative_calibrators'):
                        from .calibration import apply_contract
                        overlay=apply_contract(probabilities,*spec,prediction['derivative_calibrators'])
                        if overlay:
                            row.update(overlay)
                            row['experimental_calibrated_return_completed_match']=overlay['experimental_calibrated_win']*odd-1
                except (KeyError,ValueError,TypeError):
                    row['status']='unsupported_selection_line_or_model'
    # Remove margin only within a complete complementary pair at the SAME book/line.
    pairs=defaultdict(list)
    for row in rows:
        if row['status']!='priced_research': continue
        key=row['market'];line=row['line']
        if key in ('spreads','alternate_spreads') and row['selection']==event['away_team']:
            line=-line
        pairs[(row['bookmaker'],key,row['description'],line)].append(row)
    for group in pairs.values():
        if len(group)!=2 or len({r['selection'] for r in group})!=2: continue
        total=sum(1/r['decimal_odds'] for r in group)
        for row in group:
            # Integer-line odds express probability conditional on no push.
            fair=(1/row['decimal_odds'])/total
            conditional=row['win']/(1-row['push']) if row['push']<1 else None
            row.update(overround=total,de_vig_probability_no_push=fair,
                       model_probability_no_push=conditional,
                       probability_edge_no_push=conditional-fair if conditional is not None else None)
    # Best price among fresh, comparable observations only. All remain research.
    best={}
    for i,row in enumerate(rows):
        row['best_fresh_price']=False
        if row['status']!='priced_research' or not row['data_eligible']: continue
        key=(row['market'],row['selection'],row['description'],row['line'])
        if key not in best or row['decimal_odds']>rows[best[key]]['decimal_odds']: best[key]=i
    for i in best.values(): rows[i]['best_fresh_price']=True
    return rows
