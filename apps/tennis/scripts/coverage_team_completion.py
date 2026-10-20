"""Exact tie/season joins and explicit match-level host locations."""
import json,re,unicodedata
from pathlib import Path
from datetime import date
import pandas as pd

def extend(reg,source,add_site,bind,venues,links,root):
    review=json.loads((root/'team_links_review.json').read_text());official=json.loads((root/'official_team_ties.json').read_text())
    for l in links.values():
        if l.get('official_tie_id'):
            t=next(t for t in official if t['kind']=='dc' and t['tie_id']==l['official_tie_id'])
            l['competition_group_id']=f"ATP:ITF-event:{t['year']}:"+t['event_id']
    add_site('manchester_ao','AO Arena','Manchester','United Kingdom','Europe/London')
    add_site('martin_carpena','Martin Carpena Arena','Malaga','Spain','Europe/Madrid')
    add_site('vilnius_seb','SEB Arena','Vilnius','Lithuania','Europe/Vilnius')
    add_site('palm_hills','Palm Hills Sports Club','Cairo','Egypt','Africa/Cairo')
    add_site('megasaray_belek','Megasaray Club Belek','Belek, Antalya','Turkiye','Europe/Istanbul')
    def walk(v):
        if isinstance(v,dict):
            yield v
            for x in v.values():yield from walk(x)
        elif isinstance(v,list):
            for x in v:yield from walk(x)
    for ed in review['unresolved']:
        if '-M-DC-' not in ed['tourney_id']:continue
        candidates=ed.get('candidates',[])
        assert len(candidates)==1,ed['tourney_id'];t=candidates[0]
        sid=source('tie_'+t['tie_id'])
        raw=json.loads((root/'originals'/('tie_'+t['tie_id'])/'response.bin').read_bytes())['data']['tie']
        ids=[];tid=ed['tourney_id']
        if '2024-FLS-4-M-D-' in tid:
            assert {m.get('court',{}).get('name') for m in raw['matches'] if m.get('court')}=={'AO Arena'}
            key='manchester_ao';ids=[sid,source('dc_manchester_2024')]
        elif '2024-FLS-M-' in tid:
            key='martin_carpena';ids=[sid,source('dc_2024_final')]
        elif '2025-QLS-M-ISR-GER' in tid:
            assert any(x.get('name','').lower()=='seb arena vilnius' for x in walk(raw))
            key='vilnius_seb';ids=[sid]
        elif '2025-WG2-R1-LBN-BAR' in tid:
            key='palm_hills';ids=[sid,source('dc_2025_sep_release')]
        elif '2025-WG2-R1-UKR-DOM' in tid:
            key='megasaray_belek';ids=[sid,source('dc_2025_sep_release')]
        else:raise ValueError('Unreviewed bilateral tie: '+tid)
        year=int(tid[:4]);bind(year,tid[5:],key,ids,'Reviewed official tie record and season venue evidence',circuit='ATP',
            official_tie_id=t['tie_id'],competition_group_id=f"ATP:ITF-event:{year}:"+t['event_id'])
    for year in (2024,2025):
        finals=[t for t in official if t['kind']=='bjkc' and t['year']==year and t['bucket']=='Finals']
        sites={t['venue']['id']:t['venue'] for t in finals if t.get('venue')}
        assert len(sites)==1 and all(t.get('venue') for t in finals),(year,sites)
        v=next(iter(sites.values()));key='martin_carpena' if year==2024 else 'bjkc_shenzhen_bay'
        if year==2025:add_site(key,v['name'],v['city'],v['country']['name'],'Asia/Shanghai')
        bind(year,f'W-FC-{year}-FLS',key,[source('bjkc_draws_'+str(year))],
             'All official ITF Finals ties in this season identify the same venue',circuit='WTA',
             competition_group_id=f'WTA:ITF-Finals:{year}')

    add_site('perth_rac','RAC Arena','Perth','Australia','Australia/Perth')
    add_site('sydney_kenrosewall','Ken Rosewall Arena','Sydney','Australia','Australia/Sydney')
    # Physical identity only; edition evidence comes from its own season notes.
    known=next(v for v in venues.values() if v['name']=='Ken Rosewall Arena' and v.get('lat') is not None)
    venues['sydney_kenrosewall'].update({k:known.get(k) for k in ['lat','lon','coordinate_scope','coordinate_precision_m','coordinate_sources','altitude_m','altitude_sources','coordinate_feature']})
    canonical=pd.read_parquet('data/tennis/full_20261016/canonical/matches.parquet')
    target_ids={e['tourney_id'] for e in review['unresolved'] if e['review']=='requires_match_level_location' and (e['circuit'],'tour',e['tourney_id']) not in links}
    selected=canonical[canonical.tourney_id.isin(target_ids)]
    rawroot=Path('data/tennis/full_20261016/tml/originals');raws={}
    match_links=[];unresolved=[]
    identity_reviews=[]
    norm=lambda x:re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower())
    represented_country_reviews={
        '0f9e3961285846cf0744ab99':({'POL','ROU'},'00532ff6-6538-4119-a620-bb929e1a1e21'),
        '1d6e0117fed95fb4cf9d337d':({'CAN','MEX'},'c6db2b09-4d8a-4df9-97e6-1dfed16a8be6'),
        '7d4b9679c5313f401b18f68d':({'TUR','BEL'},'31bf0461-3c25-4c94-97c5-d5054de791bc')}
    perth={2024:{'POL','ESP','BRA','AUS','USA','GBR','CZE','CHN','SRB'},2025:{'USA','CAN','CRO','GRE','KAZ','ESP','CHN','GER','BRA'}}
    sydney={2024:{'FRA','ITA','GER','NED','NOR','CRO','GRE','CAN','CHI'},2025:{'POL','CZE','NOR','ITA','FRA','SUI','GBR','AUS','ARG'}}
    for r in selected.itertuples(index=False):
        filename=r.source_file
        if filename not in raws:raws[filename]=pd.read_csv(rawroot/filename,dtype=str)
        row=raws[filename].iloc[int(r.source_row)-2];assert row.tourney_id==r.tourney_id
        year=int(r.tourney_id[:4]);pair={str(row.winner_ioc),str(row.loser_ioc)}
        key=None;sids=[];fact=None
        if 'United' in row.tourney_name:
            if r.match_id in ('0de0be3163e4df8883933402','ae00bfe157830c426a412297'):
                key='sydney_kenrosewall'
                identity_reviews.append(dict(match_id=r.match_id,original_round=row['round'],reviewed_round='SF',
                    evidence=source('uc2025_sf_schedule'),original_preserved=True))
            elif row['round'] in ('SF','F'):key='sydney_kenrosewall'
            elif pair<=perth[year]:key='perth_rac'
            elif pair<=sydney[year]:key='sydney_kenrosewall'
            if key:
                sids=[source('uc_2024_preview' if year==2024 else 'uc2025_preview')]
                if year==2024:sids.append(source('uc2024_schedule'))
                if r.match_id in ('0de0be3163e4df8883933402','ae00bfe157830c426a412297'):sids.append(source('uc2025_sf_schedule'))
                fact=f'United Cup {year}: group host city from season notes; semifinals/final in Sydney; no inferred hours'
        else:
            day=date.fromisoformat(r.period)
            review_pair=represented_country_reviews.get(r.match_id)
            review_source=None
            if review_pair:
                reviewed,identity=review_pair;review_source=source('tie_'+identity)
                raw=json.loads((root/'originals'/('tie_'+identity)/'response.bin').read_bytes())
                # Both exact normalised player names must appear in this one
                # official tie, not merely in a general roster for the season.
                strings={norm(x) for obj in walk(raw) for x in obj.values() if isinstance(x,str)}
                assert norm(row.winner_name) in strings and norm(row.loser_name) in strings,(r.match_id,row.winner_name,row.loser_name)
                identity_reviews.append(dict(match_id=r.match_id,original_country_pair=sorted(pair),reviewed_represented_country_pair=sorted(reviewed),
                    evidence=review_source,original_preserved=True))
                pair=reviewed
            candidates=[t for t in official if t['kind']=='bjkc' and t['year']==year and {t['home'],t['away']}==pair and t.get('start') and abs((date.fromisoformat(t['start'])-day).days)<=3]
            if len(candidates)==1 and candidates[0].get('venue') and candidates[0]['venue'].get('name'):
                t=candidates[0];v=t['venue'];key='bjkc_'+v['id'];add_site(key,v['name'],v.get('city'),v.get('country',{}).get('name'),None)
                sids=[source('bjkc_draws_'+str(year))];fact='Official ITF BJK tie: unique season, country pair and source-day interval; '+t['event_name']
                if review_source:sids.append(review_source)
        if key:
            match_links.append(dict(match_id=r.match_id,circuit=r.circuit,phase=r.source_group,tourney_id=r.tourney_id,
                venue_id=key,evidence_season=year,edition_sources=sids,edition_fact=fact,reconstruction_only=True))
        else:unresolved.append(dict(match_id=r.match_id,tourney_id=r.tourney_id,country_pair=sorted(pair),source_day=r.period,reason='unique_match_level_venue_not_yet_accredited'))
    reg['match_links']=match_links
    reg['team_review_summary']={'original_blocks':233,'bilateral_davis_blocks_linked':225,'bjkc_finals_editions_linked':2,
        'match_level_locations':len(match_links),'unresolved_match_locations':unresolved,
        'match_identity_reviews':identity_reviews,
        'source_identity_reviews':[{'original_id':'2025-M-DC-2025-QLS-M-SWE-ARG-01','original_name':'Davis Cup QLS R1: SWE vs ARG',
        'reviewed_country_pair':['SWE','AUS'],'basis':'All three raw rubbers identify Australian and Swedish players; official ITF season tie corroborates the pair and dates',
        'original_preserved':True}]}
    return reg
