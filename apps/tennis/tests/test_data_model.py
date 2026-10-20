import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from tennis_engine.ingest import save_json
from tennis_engine.normalize import normalize,standard_score
from tennis_engine.model import fit,ServeModel,training_rows
from tennis_engine.evaluate import observed_markets


def test_scores_reject_retirements_short_sets_and_extra_sets():
    assert standard_score('7-6(4) 6-4',3)
    assert standard_score('6-4 4-6 6-3 2-6 7-6(8)',5)
    for score in ('6-4 2-1 RET','W/O','4-1 4-2','6-4 4-6 [10-8]','6-4 6-4 6-4'):
        assert not standard_score(score,3)


def test_observed_market_side_matches_winner_first_source():
    from types import SimpleNamespace
    row=SimpleNamespace(score='6-7(3) 6-3 6-2')
    a=observed_markets(row,True);b=observed_markets(row,False)
    assert a['over_22_5_games']==b['over_22_5_games']==1
    assert a['any_tiebreak']==b['any_tiebreak']==1
    assert a['first_set_A']==0 and b['first_set_A']==1
    assert a['A_minus_3_5_games']==1 and b['A_minus_3_5_games']==0


def test_normalization_quarantines_conflicts_and_preserves_missing_counts(tmp_path):
    base=dict(tourney_id='2025-x',tourney_date='20250106',tourney_level='A',round='F',winner_id='1',loser_id='2',winner_name='Alice',loser_name='Bob',surface='Hard',score='6-4 6-4',best_of=3,minutes=90)
    for p in ['w','l']:
        base.update({p+'_svpt':60,p+'_1stIn':40,p+'_1stWon':28,p+'_2ndWon':10})
    rows=[base,{**base,'w_1stWon':29},{**base,'tourney_id':'2025-y','w_svpt':None},{**base,'tourney_id':'2027-future','tourney_date':'20270101'}]
    path=tmp_path/'tml/originals/2025.csv';path.parent.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(path,index=False)
    save_json(tmp_path/'download_manifest.json',{'files':[{'source':'tml','name':'2025.csv','status':'ok','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'received_at':'2026-10-16T00:00:00Z'}]})
    normalize(tmp_path)
    d=pd.read_parquet(tmp_path/'canonical/matches.parquet')
    assert len(d)==1 and not d.iloc[0].eligible_model
    quarantine=json.loads((tmp_path/'canonical/quarantine.json').read_text())
    assert {r['reason'] for r in quarantine}=={'conflicting_duplicate','invalid_identity_date_surface_or_format'}


def test_temporal_cutoff_has_event_embargo(tmp_path):
    path=tmp_path/'canonical';path.mkdir()
    pd.DataFrame({'circuit':['ATP']*3,'eligible_model':[True]*3,'period':['2025-10-01','2025-12-01','2026-01-01']}).to_parquet(path/'matches.parquet')
    assert training_rows(tmp_path,'ATP','2026-01-01').period.tolist()==['2025-10-01']


def test_binomial_recovery_and_posterior_uncertainty(tmp_path):
    rng=np.random.default_rng(21)
    records=[]
    for i in range(150):
        records.append({'winner_id':'atp:a','loser_id':'atp:b','winner_name':'Alice','loser_name':'Bob','surface':'Hard','period':'2025-01-01',
                        'w_svpt':80,'w_1stWon':int(rng.binomial(80,.67)),'w_2ndWon':0,
                        'l_svpt':80,'l_1stWon':int(rng.binomial(80,.59)),'l_2ndWon':0})
    fit(pd.DataFrame(records),'ATP','2025-03-01',tmp_path)
    model=ServeModel(tmp_path)
    p=model.predict('atp:a','atp:b','Hard')
    assert p['p']==pytest.approx(.67,abs=.025)
    assert p['q']==pytest.approx(.59,abs=.025)
    assert np.linalg.eigvalsh(p['covariance']).min()>0
    unknown=model.predict('atp:new','atp:other','Hard')
    assert np.trace(unknown['covariance'])>np.trace(p['covariance'])
    assert model.resolve('Alice')=='atp:a'
    with pytest.raises(ValueError): model.predict('atp:a','atp:a','Hard')
