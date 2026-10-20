"""TML canonical observations; raw results never become same-match features."""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import pandas as pd
from .ingest import save_json

COUNTS = ['svpt','1stIn','1stWon','2ndWon']
SURFACES = {'Hard','Clay','Grass','Carpet'}
CONTEXT = ['tourney_name','indoor','winner_age','loser_age','winner_hand','loser_hand',
           'winner_ht','loser_ht','winner_ioc','loser_ioc','winner_rank','loser_rank',
           'winner_rank_points','loser_rank_points','w_ace','l_ace','w_df','l_df',
           'w_bpSaved','l_bpSaved','w_bpFaced','l_bpFaced','w_SvGms','l_SvGms']


def classify(name):
    if re.fullmatch(r'\d{4}\.csv',name) or name=='ongoing_tourneys.csv': return 'ATP','tour'
    if re.fullmatch(r'\d{4}_challenger\.csv',name) or name=='challenger_ongoing_tourneys.csv': return 'ATP','challenger'
    if re.fullmatch(r'\d{4}_wta\.csv',name) or name=='wta_ongoing_tourneys.csv': return 'WTA','tour'
    if re.fullmatch(r'atp_quali/\d{4}_atp_quali\.csv',name): return 'ATP','qualifying'
    return None,None


def normalize(root, as_of='2026-10-16', output_root=None):
    root=Path(root)
    manifest=json.loads((root/'download_manifest.json').read_text(encoding='utf-8'))
    frames, excluded, file_reports=[],[],[]
    for receipt in manifest['files']:
        if receipt['source']!='tml' or receipt['status']!='ok': continue
        name=receipt['name']
        circuit,group=classify(name)
        path=root/'tml/originals'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
            raise ValueError('Modified source: '+name)
        if circuit is None:
            file_reports.append({'file':name,'status':'archived_not_classified'})
            continue
        df=pd.read_csv(path,dtype=str,keep_default_na=False,on_bad_lines='error')
        required=['tourney_id','tourney_date','tourney_level','round','winner_id','loser_id','winner_name','loser_name','surface','score','best_of']
        if not set(required).issubset(df):
            file_reports.append({'file':name,'status':'unsupported_schema','rows':len(df)})
            continue
        df=df.assign(circuit=circuit,source_group=group,source_file=name,source_row=range(2,len(df)+2),received_at=receipt['received_at'])
        dt=pd.to_datetime(df.tourney_date,format='%Y%m%d',errors='coerce')
        valid=dt.notna() & dt.le(pd.Timestamp(as_of)) & df.surface.isin(SURFACES)
        for col in ['tourney_id','round','winner_id','loser_id','winner_name','loser_name']:
            valid &= df[col].str.strip().ne('')
        valid &= df.winner_id.ne(df.loser_id) & df.best_of.isin(['3','5'])
        for r in df.loc[~valid,['source_file','source_row']].to_dict('records'):
            excluded.append({**r,'reason':'invalid_identity_date_surface_or_format'})
        df=df.loc[valid].copy()
        df['period']=dt.loc[valid].dt.strftime('%Y-%m-%d')
        df['best_of']=df.best_of.astype(int)
        for c in [f'{prefix}_{s}' for prefix in ['w','l'] for s in COUNTS]+['minutes']:
            df[c]=pd.to_numeric(df[c],errors='coerce') if c in df else float('nan')
        for c in CONTEXT:
            if c not in df: df[c]=pd.NA
            else: df[c]=df[c].replace('',pd.NA)
            if c not in ['tourney_name','indoor','winner_hand','loser_hand','winner_ioc','loser_ioc']:
                df[c]=pd.to_numeric(df[c],errors='coerce')
        for side in ['winner','loser']:
            df[side+'_id']=df.circuit.str.lower()+':'+df[side+'_id'].str.strip()
        pairs=[tuple(sorted((a,b))) for a,b in zip(df.winner_id,df.loser_id)]
        df['match_id']=[hashlib.sha256('|'.join((c,t,r,*p)).encode()).hexdigest()[:24]
                         for c,t,r,p in zip(df.circuit,df.tourney_id,df['round'],pairs)]
        df['source_lineage']=[json.dumps([{'file':name,'row':int(row),'received_at':receipt['received_at'],
                                           'sha256':receipt['sha256']}]) for row in df.source_row]
        keep=required+['circuit','source_group','source_file','source_row','received_at','source_lineage','period','match_id','minutes']+CONTEXT+[f'{p}_{s}' for p in ['w','l'] for s in COUNTS]
        frames.append(df[list(dict.fromkeys(keep))])
        file_reports.append({'file':name,'status':'parsed','rows':len(valid),'identity_valid':int(valid.sum())})
    if not frames: raise ValueError('No supported data')
    all_rows=pd.concat(frames,ignore_index=True)
    duplicate=all_rows.match_id.duplicated(keep=False)
    unique=all_rows.loc[~duplicate].copy()
    resolved=[]
    core=['winner_id','loser_id','score','surface','best_of']+[f'{p}_{s}' for p in ['w','l'] for s in COUNTS]
    for mid,group in all_rows.loc[duplicate].groupby('match_id',sort=False):
        if any(group[c].dropna().nunique()>1 for c in core):
            excluded.append({'match_id':mid,'reason':'conflicting_duplicate','sources':group[['source_file','source_row']].to_dict('records')})
            continue
        row=group.iloc[0].copy()
        for c in core+['minutes']+CONTEXT:
            known=group[c].dropna()
            if len(known): row[c]=known.iloc[0]
        row['period']=min(group.period)
        row['source_file']=';'.join(sorted(set(group.source_file)))
        # A combined row is only available once all constituent observations arrived.
        row['received_at']=max(group.received_at,key=lambda t:pd.Timestamp(t))
        row['source_lineage']=json.dumps([item for value in group.source_lineage for item in json.loads(value)])
        resolved.append(row)
    df=pd.concat([unique,pd.DataFrame(resolved)],ignore_index=True)
    df['completed_standard']=[standard_score(score,best_of) for score,best_of in zip(df.score,df.best_of)]
    df['valid_serve_counts']=True
    for p in ['w','l']:
        n,first,fw,sw=(df[f'{p}_{s}'] for s in COUNTS)
        ok=n.gt(0)&first.between(0,n)&fw.between(0,first)&sw.between(0,n-first)
        ok &= pd.concat([n,first,fw,sw],axis=1).notna().all(axis=1)
        ok &= pd.concat([n,first,fw,sw],axis=1).mod(1).eq(0).all(axis=1)
        df['valid_serve_counts'] &= ok
    df['eligible_model']=df.completed_standard & df.valid_serve_counts
    df['date_precision']='tournament_week_or_source_date; match_time_not_verified'
    df=df.sort_values(['period','match_id']).reset_index(drop=True)
    output=Path(output_root) if output_root is not None else root/'canonical'
    output.mkdir(parents=True,exist_ok=True)
    df.to_parquet(output/'matches.parquet',index=False)
    save_json(output/'quarantine.json',excluded)
    save_json(output/'coverage.json',{'as_of':as_of,'rows_before_dedup':len(all_rows),'canonical_matches':len(df),
              'eligible_serve_matches':int(df.eligible_model.sum()),'conflicting_matches':sum(r['reason']=='conflicting_duplicate' for r in excluded),
              'raw_invalid_rows':sum(r['reason']!='conflicting_duplicate' for r in excluded),
              'by_circuit':df.groupby('circuit').agg(matches=('match_id','size'),eligible=('eligible_model','sum')).astype(int).to_dict('index'),
              'by_year':df.assign(year=df.period.str[:4]).groupby(['circuit','year']).agg(matches=('match_id','size'),eligible=('eligible_model','sum')).reset_index().to_dict('records'),
              'files':file_reports,'temporal_limit':'Historical receipt/publication not established; period is not precise match time.'})
    save_json(output/'context_coverage.json',{
        'as_of':as_of,'fields_preserved':CONTEXT,'active_model_features':['serve','return','surface','recency'],
        'context_features_fitted':False,
        'coverage':[{'circuit':circuit,'field':column,'known':int(group[column].notna().sum()),
                     'total':len(group),'fraction_known':float(group[column].notna().mean())}
                    for circuit,group in df.loc[df.period.ge('2025-01-01')].groupby('circuit') for column in CONTEXT],
        'limits':['Age and rankings are source-reported match metadata, not proven pre-match observations.',
                  'Indoor retains source encoding without guessing unknown values.',
                  'Weekly dates cannot measure daily fatigue, rest, travel or jet lag.']})
    return {'canonical_matches':len(df),'eligible_serve_matches':int(df.eligible_model.sum()),'output':str(output)}


def standard_score(value,best_of=None):
    """Only fully reported conventional completed sets, no retirement/short-set/supertiebreak."""
    if not isinstance(value,str) or not value.strip(): return False
    sets=value.split()
    if not 2<=len(sets)<=5: return False
    won=lost=0
    need=best_of//2+1 if best_of in (3,5) else None
    for i,token in enumerate(sets):
        match=re.fullmatch(r'(\d+)-(\d+)(?:\(\d+\))?',token)
        if not match: return False
        a,b=map(int,match.groups())
        if not ((max(a,b)==6 and min(a,b)<=4) or (max(a,b)==7 and min(a,b) in (5,6))):
            return False
        won+=a>b; lost+=b>a
        if need and max(won,lost)==need and i!=len(sets)-1: return False
    return won>lost and (won==need if need else won in (2,3))
