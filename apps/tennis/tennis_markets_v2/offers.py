"""Actual documented Odds API keys, exact complementary lines and freshness."""
from collections import defaultdict
from dataclasses import asdict
import json,math
from tennis_engine.operations import utc
from .catalog import Contract

API_KEYS={'h2h','h2h_s1','h2h_s2','spreads','alternate_spreads','totals','alternate_totals','spreads_s1','totals_s1','alternate_totals_s1','alternate_totals_s2','alternate_set_spreads','alternate_set_totals'}

def from_api(key,outcome,event):
 if key not in API_KEYS:raise ValueError('Provider market not mapped for tennis')
 if outcome.get('description') not in (None,''):raise ValueError('Unreviewed description/participant scope')
 name=outcome['name'];sides={event['home_team']:'A',event['away_team']:'B'}
 if len(sides)!=2:raise ValueError('Distinct participants required')
 if key in ('h2h','h2h_s1','h2h_s2'):
  if outcome.get('point') is not None:raise ValueError('Unexpected winner line')
  return Contract('winner',sides[name]) if key=='h2h' else Contract('set_winner',sides[name],set_number=int(key[-1]))
 if key in ('totals','alternate_totals','alternate_set_totals','totals_s1','alternate_totals_s1','alternate_totals_s2'):
  side={'Over':'over','Under':'under'}[name]
  kind='sets_total' if key=='alternate_set_totals' else 'set_games_total' if '_s' in key else 'games_total'
  return Contract(kind,side,outcome['point'],int(key[-1]) if kind=='set_games_total' else None)
 kind='sets_handicap' if key=='alternate_set_spreads' else 'set_games_handicap' if key=='spreads_s1' else 'games_handicap'
 return Contract(kind,sides[name],outcome['point'],1 if kind=='set_games_handicap' else None)

def pair_key(c):
 """Equivalent opposing handicaps have opposite signed lines."""
 line=-c.line if 'handicap' in c.kind and c.selection=='B' else c.line
 return c.kind,c.set_number,line

def price_offers(event,engine,received_at,decision_at):
 rows=[]
 for book in event.get('bookmakers',[]):
  for offered in book.get('markets',[]):
   for outcome in offered.get('outcomes',[]):
    row=dict(bookmaker=book.get('key'),provider_market=offered.get('key'),selection=outcome.get('name'),line=outcome.get('point'),
     decimal_odds=outcome.get('price'),status='unsupported',quote_fresh=False,best_fresh_observed_price=False,executable=False)
    rows.append(row)
    try:
     odd=outcome['price']
     if isinstance(odd,bool) or not isinstance(odd,(int,float)) or not math.isfinite(odd) or odd<=1:raise ValueError('Invalid price')
     c=from_api(offered['key'],outcome,event).validate(engine.rules)
     row.update(engine.quote(c,odd),status='priced_research')
     update=offered.get('last_update') or book.get('last_update')
     age=(utc(decision_at)-utc(received_at)).total_seconds();update_age=(utc(decision_at)-utc(update)).total_seconds()
     row['quote_fresh']=bool(0<=age<=900 and 0<=update_age<=900 and utc(update)<=utc(received_at)<=utc(decision_at)<utc(event['commence_time']))
     row['scope']='Observed price; not proof of account execution or verified live fixture'
    except (ValueError,TypeError,KeyError) as error:
     row.update(reason=str(error),status='unmapped_or_invalid_offer' if row['status']!='priced_research' else 'priced_without_valid_freshness')
 groups=defaultdict(list)
 for row in rows:
  if row['status']=='priced_research':groups[(row['bookmaker'],row['provider_market'],pair_key(Contract(**row['contract'])))].append(row)
 for group in groups.values():
  if len(group)!=2:continue
  sides={r['contract']['selection'] for r in group}
  if sides not in ({'A','B'},{'over','under'}):continue
  denominator=sum(1/r['decimal_odds'] for r in group)
  for row in group:
   row.update(overround=denominator,de_vig_probability_no_push=(1/row['decimal_odds'])/denominator,
    model_probability_no_push=row['win']/(1-row['push']) if row['push']<1 else None)
 best={}
 for i,row in enumerate(rows):
  if row['status']!='priced_research' or not row['quote_fresh']:continue
  key=json.dumps(row['contract'],sort_keys=True)
  if key not in best or rows[best[key]]['decimal_odds']<row['decimal_odds']:best[key]=i
 for i in best.values():rows[i]['best_fresh_observed_price']=True
 return rows
