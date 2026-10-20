"""Second identity pass: birth dates implied by (tournament date - age) settle same-name ID pairs.

The source gives age to the day, so each ID carries a birth date. Two IDs with the same normalized name merge
only if their median birth dates differ by at most BIRTH_TOLERANCE_DAYS, each estimate is internally stable and
they never meet in the same tournament-week. Pairs whose birth dates differ by more than a year are recorded
as confirmed distinct people. Everything else stays unresolved. Writes a NEW canonical version only.
"""
import hashlib
import json
from pathlib import Path
import pandas as pd
from tennis_identity_v2 import long_form

BIRTH_TOLERANCE_DAYS = 3
DISTINCT_DAYS = 365
STABLE_SPREAD_DAYS = 10
PLACEHOLDER_NAMES = {'unknown unknown'}


def birth_dates(df):
    parts = []
    for side in ('winner', 'loser'):
        x = df[[side + '_id', 'tourney_date', side + '_age']].dropna()
        x.columns = ['id', 'td', 'age']
        x = x[x.age.between(12, 50)]
        x['birth'] = pd.to_datetime(x.td.astype(str), format='%Y%m%d') - pd.to_timedelta(x.age * 365.25, unit='D')
        parts.append(x)
    b = pd.concat(parts).groupby('id').birth.agg(['median', 'min', 'max', 'count'])
    b['spread'] = (b['max'] - b['min']).dt.days
    return b


def resolve(df):
    rows, births = long_form(df), birth_dates(df)
    merged, distinct, unresolved = {}, [], []
    for (circuit, name), group in rows.groupby(['circuit', 'n']):
        ids = group.id.unique()
        if len(ids) < 2 or name in PLACEHOLDER_NAMES:
            continue
        counts = group.id.value_counts()
        base = counts.index[0]
        weeks = lambda i: set(group.loc[group.id.eq(i), 'tourney_id'].astype(str) + '|' + group.loc[group.id.eq(i), 'period'].astype(str))
        for other in counts.index[1:]:
            entry = dict(circuit=circuit, name=name, id=other, base=base, rows=int(counts[other]), base_rows=int(counts[base]))
            if base not in births.index or other not in births.index:
                unresolved.append(dict(entry, reason='birth date unavailable')); continue
            gap = abs((births.loc[base, 'median'] - births.loc[other, 'median']).days)
            stable = max(births.loc[base, 'spread'], births.loc[other, 'spread']) <= STABLE_SPREAD_DAYS
            entry['birth_gap_days'] = int(gap)
            if gap > DISTINCT_DAYS:
                distinct.append(entry)
            elif gap <= BIRTH_TOLERANCE_DAYS and stable and not weeks(base) & weeks(other):
                merged[other] = entry
            else:
                unresolved.append(dict(entry, reason='birth evidence inconclusive or same tournament-week'))
    return merged, distinct, unresolved


def build(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('New version directory required')
    df = pd.read_parquet(source)
    merged, distinct, unresolved = resolve(df)
    out = df.copy()
    for side in ('winner', 'loser'):
        out[side + '_id'] = out[side + '_id'].map(lambda x: merged[x]['base'] if x in merged else x)
    if (out.winner_id == out.loser_id).any():
        raise ValueError('Merge created a self-match')
    (output / 'canonical').mkdir(parents=True)
    out.to_parquet(output / 'canonical/matches.parquet', index=False)
    report = dict(schema='tennis-identity-birthdate-v3', source=str(source.resolve()),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        output_sha256=hashlib.sha256((output / 'canonical/matches.parquet').read_bytes()).hexdigest(),
        rules=dict(birth_tolerance_days=BIRTH_TOLERANCE_DAYS, distinct_days=DISTINCT_DAYS, stable_spread_days=STABLE_SPREAD_DAYS),
        merged=list(merged.values()), confirmed_distinct=distinct, unresolved=unresolved,
        rows_rewritten=int(sum((df[s + '_id'] != out[s + '_id']).sum() for s in ('winner', 'loser'))),
        scope='Birth dates derived from source ages; current-knowledge bridge, models not retrained by this step.')
    (output / 'identity_report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    return report
