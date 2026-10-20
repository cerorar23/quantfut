"""Conservative alias bridge for one-off provider IDs; writes a NEW canonical version only.

An ID is merged into a base ID only when the same normalized name, same circuit, a long base history,
a tiny alias footprint inside the base's active span, no shared tournament and compatible attributes
all hold. Anything else stays in quarantine. Frozen artifacts are never read for writing.
"""
import hashlib,json,unicodedata
from pathlib import Path
import pandas as pd

RULES={'base_min_rows':30,'alias_max_rows':10,'base_ratio_min':5,'span_grace_days':120,'attributes':['ioc','hand'],
       'merge_by':'identical normalized name + stated structural checks; no fuzzy matching'}


def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(value)).casefold()
                           if not unicodedata.combining(c) and (c.isalnum() or c.isspace())).split())


def long_form(df):
    parts=[]
    for side in ('winner','loser'):
        part=df[['circuit','period','tourney_id',side+'_id',side+'_name',side+'_ioc',side+'_hand']].copy()
        part.columns=['circuit','period','tourney_id','id','name','ioc','hand'];parts.append(part)
    out=pd.concat(parts,ignore_index=True);out['n']=out.name.map(norm);return out


def find_aliases(df):
    rows=long_form(df);accepted,rejected={},[]
    for (circuit,name),group in rows.groupby(['circuit','n']):
        if group.id.nunique()<2:continue
        stats=group.groupby('id').agg(k=('period','size'),first=('period','min'),last=('period','max'))
        base=stats.k.idxmax();b=stats.loc[base]
        for pid,s in stats.drop(index=base).iterrows():
            reasons=[]
            if b.k<RULES['base_min_rows']:reasons.append('base history too short')
            if s.k>RULES['alias_max_rows']:reasons.append('alias footprint too large')
            if b.k<RULES['base_ratio_min']*s.k:reasons.append('base/alias ratio too small')
            if not (b['first']<=s['first'] and pd.Timestamp(s['last'])<=pd.Timestamp(b['last'])+pd.Timedelta(days=RULES['span_grace_days'])):reasons.append('alias outside base active span (+grace)')
            events=lambda i:set(group.loc[group.id.eq(i),'tourney_id'].astype(str)+'|'+group.loc[group.id.eq(i),'period'].astype(str))
            if events(pid)&events(base):reasons.append('same tournament-week as base')
            for attr in RULES['attributes']:
                x,y=set(group.loc[group.id.eq(pid),attr].dropna()),set(group.loc[group.id.eq(base),attr].dropna())
                if x and y and not x&y:reasons.append('conflicting '+attr)
            entry={'circuit':circuit,'name':name,'alias':pid,'base':base,'alias_rows':int(s.k),'base_rows':int(b.k),
                   'alias_first':s['first'],'alias_last':s['last']}
            if reasons:rejected.append({**entry,'reasons':reasons})
            else:accepted[pid]=entry
    return accepted,rejected


def build(source,output):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('New version directory required')
    df=pd.read_parquet(source)
    accepted,rejected=find_aliases(df)
    out=df.copy()
    for side in ('winner','loser'):
        out[side+'_id_original']=out[side+'_id']
        out[side+'_id']=out[side+'_id'].map(lambda x:accepted[x]['base'] if x in accepted else x)
    if (out.winner_id==out.loser_id).any():raise ValueError('Alias merge created a self-match')
    (output/'canonical').mkdir(parents=True)
    out.to_parquet(output/'canonical/matches.parquet',index=False)
    report={'schema':'tennis-identity-bridge-v2','rules':RULES,'source':str(source.resolve()),
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'output_sha256':hashlib.sha256((output/'canonical/matches.parquet').read_bytes()).hexdigest(),
            'rows':len(df),'aliases_merged':len(accepted),
            'rows_rewritten':int(sum((df[s+'_id']!=out[s+'_id']).sum() for s in ('winner','loser'))),
            'still_ambiguous':len(rejected),'alias_map':accepted,'rejected':rejected,
            'scope':'Current-knowledge bridge; does not prove the alias was resolvable before each match. Models are not retrained.'}
    (output/'alias_report.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    return report
