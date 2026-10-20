"""Synthetic contracts only; these observations are not empirical tennis results."""
import numpy as np
import pandas as pd
import pytest
from tennis_engine.historical_comparison import (FEATURES,attach_baseline,HistoricalSpatialCorrection,compare_historical)


@pytest.fixture
def cohort():
    rng=np.random.default_rng(42);records=[];pred=[]
    for i in range(160):
        train=i<120;year=2024 if train else 2025
        row=dict(match_id=str(i),player_a='a',player_b='b',y=i%2,circuit='ATP',
            partition='development_2024' if train else 'exploratory_2025',
            comparison_block_id=f'{year}-{i//10}',historical_reconstruction=True,genuine_asof_validation=False,
            eligible_spatial_probability_cohort=True,completed_standard=True,coarse_venue_reference_used=i%13==0,
            edition_source_period_first=f'{year}-06-01',edition_source_period_last=f'{year}-06-07')
        row.update(dict(zip(FEATURES,rng.normal(size=3))))
        records.append(row)
        pred.append(dict(match_id=str(i),player_a='a',player_b='b',y=i%2,baseline_probability=.4+.2*(i%2),
            origin=f'{year}-01-01',training_latest_period=f'{year-1}-11-20',pool_latest_period=f'{year-1}-11-19'))
    return pd.DataFrame(records),pd.DataFrame(pred)


def test_future_baseline_training_and_calibration_are_rejected(cohort):
    d,p=cohort
    for col in ('training_latest_period','pool_latest_period'):
        bad=p.copy();bad.loc[0,col]='2024-01-01'
        with pytest.raises(ValueError,match='embargo'):attach_baseline(d,bad)


def test_orientation_and_duplicate_predictions_fail(cohort):
    d,p=cohort
    bad=p.copy();bad.loc[0,'player_a']='other'
    with pytest.raises(ValueError,match='orientation'):attach_baseline(d,bad)
    with pytest.raises(ValueError,match='Duplicate'):attach_baseline(d,pd.concat([p,p.iloc[:1]]))


def test_correction_cannot_fit_test_labels(cohort):
    d,p=cohort;joined=attach_baseline(d,p)
    with pytest.raises(ValueError,match='development'):HistoricalSpatialCorrection().fit(joined)


def test_player_swap_complements_probability_and_preserves_beta(cohort):
    d,p=cohort;joined=attach_baseline(d,p).iloc[:120].copy()
    model=HistoricalSpatialCorrection();a=model.fit(joined)
    swapped=joined.copy();swapped[list(FEATURES)]=-swapped[list(FEATURES)]
    swapped['y']=1-swapped.y;swapped['baseline_probability']=1-swapped.baseline_probability
    other=HistoricalSpatialCorrection();b=other.fit(swapped)
    np.testing.assert_allclose(a['beta'],b['beta'],atol=1e-9)
    np.testing.assert_allclose(model.predict(joined),1-other.predict(swapped),atol=1e-10)


def test_future_labels_and_feature_scale_do_not_change_training_fit(cohort):
    d,p=cohort
    first,report=compare_historical(d,p)
    changed=d.copy();mask=changed.partition.eq('exploratory_2025')
    changed.loc[mask,'y']=1-changed.loc[mask,'y'];changed.loc[mask,list(FEATURES)]*=10000
    changed_p=p.copy();changed_p.loc[changed_p.match_id.isin(changed.loc[mask,'match_id']),'y']=changed.loc[mask,'y'].to_numpy()
    _,later=compare_historical(changed,changed_p)
    assert report['artifact']==later['artifact']
    expected=np.sqrt(np.mean(d.iloc[:120][list(FEATURES)].to_numpy()**2,axis=0))
    np.testing.assert_allclose(report['artifact']['rms_train'],expected)
    assert len(first)==40 and report['metrics']['base']['n']==report['metrics']['base_plus_spatial']['n']==40


def test_missing_baseline_uses_identical_intersection(cohort):
    d,p=cohort
    scored,r=compare_historical(d,p.loc[p.match_id.ne('159')])
    assert len(scored)==39 and r['coverage']==39/40
    assert r['metrics']['base']['n']==r['metrics']['base_plus_spatial']['n']==39


def test_indivisible_competition_cannot_cross_partitions(cohort):
    d,p=cohort;bad=d.copy();bad.loc[120,'comparison_block_id']=bad.loc[0,'comparison_block_id']
    with pytest.raises(ValueError,match='Competition split'):compare_historical(bad,p)


def test_spatial_missing_or_operational_mislabel_fails(cohort):
    d,p=cohort;joined=attach_baseline(d,p).iloc[:120].copy()
    joined.loc[0,FEATURES[0]]=np.nan
    with pytest.raises(ValueError,match='Missing spatial'):HistoricalSpatialCorrection().fit(joined)
    bad=d.copy();bad.loc[0,'genuine_asof_validation']=True
    with pytest.raises(ValueError,match='retrospective only'):compare_historical(bad,p)


def test_coarse_sensitivity_refits_only_filtered_training(cohort):
    d,p=cohort;scored,r=compare_historical(d,p,exclude_coarse=True)
    expected=d.loc[d.partition.eq('development_2024') & ~d.coarse_venue_reference_used]
    assert set(r['artifact']['training_event_ids'])==set(expected.match_id)
    assert not scored.coarse_venue_reference_used.any()
