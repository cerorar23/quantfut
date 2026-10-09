import copy
import json
import pytest

from nba.minutes_benchmark import forecast_minutes, replay_minutes, sample_scores, regulation_labels, validate_rows, verified_namespace_overlay
from nba.audit import digest


PROTOCOL=dict(version='test',history_window=20,minimum_appearances=2,baseline_window=2,
              recent_window=1,shrinkage_pseudo_games=1,evaluation_seasons=['2025-26'],
              seed=12,bootstrap_replicates=20,chronological_blocks=3)


def row(gid, day, value, pid=1, season='2025-26'):
    return dict(game_id=gid,player_id=pid,id_namespace='nba',team_id=10,season=season,
                season_type='regular',date=day,regulation_minutes=value)


def test_empirical_continuous_crps_known_value_and_perfect_point():
    assert sample_scores([0,2],1)['crps']==pytest.approx(0.5)
    assert sample_scores([12,12],12)['crps']==0


@pytest.mark.parametrize('samples,truth',[([],1),([float('nan')],1),([-1],1),([49],1),([1],49)])
def test_distribution_support_rejected(samples,truth):
    with pytest.raises(ValueError):sample_scores(samples,truth)


def test_today_and_future_and_other_season_excluded():
    prior=[row('1','2025-10-01',20),row('2','2025-10-02',30)]
    bad=prior+[row('3','2025-10-03',48),row('4','2025-10-04',48),row('0','2025-09-01',48,season='2024-25')]
    assert forecast_minutes(prior,'2025-10-03','2025-26',PROTOCOL)==forecast_minutes(bad,'2025-10-03','2025-26',PROTOCOL)


def test_every_game_on_target_date_predicted_before_any_label_added():
    rows=[row('1','2025-10-01',20),row('2','2025-10-02',30),row('3','2025-10-03',25),row('4','2025-10-03',35)]
    _,first,_=replay_minutes(rows,PROTOCOL);changed=copy.deepcopy(rows);changed[2]['regulation_minutes']=47
    _,second,_=replay_minutes(changed,PROTOCOL)
    assert first==second
    assert first[0]['history_game_ids']==first[1]['history_game_ids']==['1','2']
    assert 'actual_regulation_minutes' not in first[0]


def test_appearance_zero_does_not_become_positive_history():
    out=forecast_minutes([row('1','2025-10-01',0),row('2','2025-10-02',30)],'2025-10-03','2025-26',PROTOCOL)
    assert out['status']=='abstain' and out['history_count']==1


@pytest.mark.parametrize('kind',['duplicate','namespace','nonfinite','metadata'])
def test_identity_and_metadata_rejection(kind):
    rows=[row('1','2025-10-01',20),row('1','2025-10-01',30,pid=2)]
    if kind=='duplicate':rows.append(copy.deepcopy(rows[0]))
    if kind=='namespace':rows[0]['id_namespace']='espn'
    if kind=='nonfinite':rows[0]['regulation_minutes']=float('inf')
    if kind=='metadata':rows[1]['date']='2025-10-02'
    with pytest.raises(ValueError):validate_rows(rows)


def court_fixture():
    boxes=[dict(row('1','2025-10-01',48,pid=p),team_id=10 if p<=5 else 20,
                minutes=53,participated=True,status='') for p in range(1,11)]
    stints=[dict(period=period,team_id=tid,nba_player_ids=list(range(1,6) if tid==10 else range(6,11)),
                 start_elapsed_seconds=(period-1)*720 if period<=4 else 2880,
                 end_elapsed_seconds=period*720 if period<=4 else 3180)
            for period in range(1,6) for tid in [10,20]]
    return boxes,[dict(game_id='1',periods=5,chronological_lineups=stints)]


def test_regulation_labels_exclude_overtime_without_rescaling():
    boxes,games=court_fixture();labels=regulation_labels(boxes,games)
    assert all(r['regulation_minutes']==48 and r['box_minutes']==53 for r in labels)
    assert sum(r['regulation_minutes'] for r in labels)==480


@pytest.mark.parametrize('kind',['gap','foreign','duplicate_floor','DNP','missing_game'])
def test_bad_court_sources_cannot_make_labels(kind):
    boxes,games=court_fixture()
    if kind=='gap':games[0]['chronological_lineups'][0]['start_elapsed_seconds']=1
    if kind=='foreign':games[0]['chronological_lineups'][0]['nba_player_ids'][0]=11
    if kind=='duplicate_floor':games[0]['chronological_lineups'][0]['nba_player_ids'][0]=2
    if kind=='DNP':boxes[0]['status']='DNP - coach'
    if kind=='missing_game':games=[]
    with pytest.raises(ValueError):regulation_labels(boxes,games)


@pytest.mark.parametrize('kind',['valid','hash','person','team','stats'])
def test_missing_namespace_requires_exact_source_proof(tmp_path,kind):
    rows=[dict(row('1','2025-10-01',20),points=4,rebounds=2,assists=1,status='')]
    rows[0].pop('id_namespace')
    source=dict(boxScoreTraditional=dict(gameId='1',homeTeam=dict(teamId=10,players=[dict(personId=1,comment='',statistics=dict(points=4,reboundsTotal=2,assists=1))]),awayTeam=dict(teamId=20,players=[])))
    p=tmp_path/'official.json';p.write_text(json.dumps(source),encoding='utf-8');expected=digest(p)
    if kind=='hash':p.write_text('{}',encoding='utf-8')
    if kind=='person':rows[0]['player_id']=2
    if kind=='team':rows[0]['team_id']=20
    if kind=='stats':rows[0]['points']=5
    if kind=='valid':
        result=verified_namespace_overlay(rows,p,expected)
        assert result[0]['id_namespace']=='nba' and result[0]['namespace_proof']['exact_match']
        assert 'id_namespace' not in rows[0]
    else:
        with pytest.raises(ValueError):verified_namespace_overlay(rows,p,expected)
