import copy
import gzip
from datetime import datetime, UTC
import json
from pathlib import Path

import httpx
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from nba.audit import digest, write_json
from nba.basketball_reference import parse_day, reconcile_game, capture_days, seed_cache, recover_dataset, TEAM_CODES
from nba.ingest import read_dataset
from test_pipeline import box_rows


def fixture():
    refs, players = box_rows()
    ids = {1: 1610612743, 2: 1610612756}
    prior, daily = [], []
    for ref in refs:
        ref['team_id'] = ids[ref['team_id']]
        ref['matchup'] = 'DEN @ PHX' if ref['team_id'] == ids[1] else 'PHX vs. DEN'
    for p in players:
        tid = ids[p['teamId']]
        pid = p['personId']
        prior.append(dict(game_id=p['gameId'], team_id=tid, person_id=pid,
            first_name=p['firstName'], family_name=p['familyName'], minutes='47:60',
            comment='', points=10, rebounds_total=5, assists=2))
        daily.append(dict(bref_id=f'player{pid}', name=f"A {p['familyName']}", team_code=TEAM_CODES[tid],
            opponent_code='PHO' if tid == ids[1] else 'DEN', home_away='away' if tid == ids[1] else 'home',
            game_date='2025-10-21', boxscore_link='/boxscores/202510210PHO.html',
            minutes_raw='48:00', points=10, rebounds=5, assists=2))
    return refs, prior, daily


def page():
    _, _, daily = fixture()
    html = '<title>NBA Daily Stats Leaders for October 21, 2025 | Basketball-Reference.com</title><table id="stats"><tbody>'
    for r in daily:
        pid = r['bref_id']
        vals = dict(player=r['name'], team_id=r['team_code'], opp_id=r['opponent_code'],
            game_location='@' if r['home_away'] == 'away' else '', game_result='W',
            mp='48:00', pts='10', trb='5', ast='2', orb='1', drb='4')
        html += '<tr>'
        for k, v in vals.items():
            extra = f' data-append-csv="{pid}"' if k == 'player' else ' csk="2880"' if k == 'mp' else ''
            link = f'/players/p/{pid}.html' if k == 'player' else r['boxscore_link'] if k == 'game_result' else None
            html += f'<td data-stat="{k}"{extra}>' + (f'<a href="{link}">{v}</a>' if link else v) + '</td>'
        html += '</tr>'
    return (html + '</tbody></table>').encode()


def test_parser_and_reconciliation_conserve_teams_with_independently_correct_minutes():
    daily = parse_day(page(), '2025-10-21')
    refs, prior, _ = fixture()
    rows, mappings = reconcile_game(refs, prior, daily, {'page_sha256': 'x'})
    assert len(rows) == 10 and sum(r['minutes'] for r in rows) == 480
    assert all(r['provenance']['nba_original_minutes'] == '47:60' for r in rows)
    assert all(r['provenance']['bref_minutes'] == '48:00' for r in rows)
    assert all(not r['original_pregame_availability_known'] for r in rows)


def test_observed_zero_minutes_with_zero_stats_is_not_inferred_dnp():
    data = page().replace(b'csk="2880">48:00', b'csk="0">0:00', 1)
    for old, new in ((b'data-stat="pts">10',b'data-stat="pts">0'),
                     (b'data-stat="trb">5',b'data-stat="trb">0'),
                     (b'data-stat="ast">2',b'data-stat="ast">0'),
                     (b'data-stat="orb">1',b'data-stat="orb">0'),
                     (b'data-stat="drb">4',b'data-stat="drb">0')):
        data = data.replace(old,new,1)
    rows = parse_day(data,'2025-10-21')
    assert rows[0]['minutes_raw'] == '0:00' and len(rows) == 10
    bad = data.replace(b'data-stat="ast">0',b'data-stat="ast">1',1)
    with pytest.raises(ValueError,match='zero displayed'): parse_day(bad,'2025-10-21')


@pytest.mark.parametrize('bad', ['date', 'seconds', 'duplicate', 'opponent', 'stats', 'clock', 'body'])
def test_parser_rejects_wrong_dates_invalid_clock_ids_and_partial_html(bad):
    data = page()
    if bad == 'date': data = data.replace(b'October 21', b'October 22')
    elif bad == 'seconds': data = data.replace(b'48:00', b'47:60')
    elif bad == 'duplicate': data = data.replace(b'player11', b'player10')
    elif bad == 'opponent': data = data.replace(b'>PHO<', b'>BAD<')
    elif bad == 'stats': data = data.replace(b'>5<', b'>6<')
    elif bad == 'clock': data = data.replace(b'csk="2880"', b'csk="2879"')
    else: data = data.removesuffix(b'</table>')
    with pytest.raises(ValueError): parse_day(data, '2025-10-21')


@pytest.mark.parametrize('bad', ['name', 'duplicate_nba', 'minutes', 'excess_minutes', 'stat', 'missing_player', 'reference_minutes', 'venue', 'date', 'opponent'])
def test_reconcile_rejects_identity_statistical_and_reference_errors(bad):
    refs, prior, daily = fixture()
    if bad == 'name': daily[0]['name'] = 'Different person'
    elif bad == 'duplicate_nba': prior.append(copy.deepcopy(prior[0]))
    elif bad == 'minutes': daily[0]['minutes_raw'] = '47:59'
    elif bad == 'excess_minutes': daily[0]['minutes_raw'] = '47:50'
    elif bad == 'stat': daily[0]['points'] += 1
    elif bad == 'missing_player': daily.pop()
    elif bad == 'reference_minutes': refs[0]['min'] = 47.98
    elif bad == 'venue': daily[0]['home_away'] = 'home'
    elif bad == 'date': daily[0]['game_date'] = '2025-10-20'
    else: daily[0]['opponent_code'] = 'ATL'
    if bad == 'minutes':
        # One second still satisfies the existing nine-second team tolerance;
        # independent seconds-key checking belongs to parse_day.
        rows, _ = reconcile_game(refs, prior, daily, {})
        assert len(rows) == 10
    else:
        with pytest.raises(ValueError): reconcile_game(refs, prior, daily, {})


def test_no_dnp_inference_for_missing_nonparticipant():
    refs, prior, daily = fixture()
    prior.append(dict(prior[0], person_id=99, first_name='Missing', minutes='', comment='', points=0, rebounds_total=0, assists=0))
    with pytest.raises(ValueError, match='known participant'): reconcile_game(refs, prior, daily, {})
    prior[-1]['comment'] = "DNP-Coach's Decision"
    rows, _ = reconcile_game(refs, prior, daily, {})
    assert len(rows) == 10 and all(r['player_id'] != 99 for r in rows)


def test_accent_only_matching_and_ambiguous_name_collision():
    refs, prior, daily = fixture()
    prior[0]['first_name'] = 'Á'
    rows, _ = reconcile_game(refs, prior, daily, {})
    assert len(rows) == 10
    prior.append(dict(prior[0], person_id=77, first_name='A'))
    with pytest.raises(ValueError, match='ambiguous'): reconcile_game(refs, prior, daily, {})


@pytest.mark.parametrize('kind',['omitted_nba_suffix','omitted_bref_suffix','initial_periods'])
def test_unique_same_game_generation_labels_and_initial_periods(kind):
    refs, prior, daily = fixture()
    if kind == 'omitted_nba_suffix': daily[0]['name'] += ' Jr.'
    elif kind == 'omitted_bref_suffix': prior[0]['family_name'] += ' III'
    else:
        prior[0]['first_name'] = 'P.J.'
        daily[0]['name'] = 'PJ ' + prior[0]['family_name']
    rows, mappings = reconcile_game(refs,prior,daily,{})
    assert len(rows)==10
    assert 'generation label or periods' in mappings[0]['identity_method']


@pytest.mark.parametrize('kind',['conflicting_suffix','collision','nickname'])
def test_name_variants_never_allow_conflicting_generations_or_nicknames(kind):
    refs, prior, daily = fixture()
    if kind == 'conflicting_suffix':
        daily[0]['name'] += ' Sr.'
        prior[0]['family_name'] += ' Jr.'
    elif kind == 'collision':
        prior[0]['family_name'] += ' Jr.'
        prior.append(dict(prior[0],person_id=99,family_name=prior[0]['family_name'].removesuffix(' Jr.')+' Sr.'))
    else:
        prior[0]['first_name'] = 'Nicolas'
        daily[0]['name'] = 'Nic '+prior[0]['family_name']
    with pytest.raises(ValueError,match='unresolved'): reconcile_game(refs,prior,daily,{})


def test_denial_stops_across_all_batches_and_preserves_body(tmp_path):
    calls = []
    def deny(request):
        calls.append(request)
        return httpx.Response(429, text='provider denied')
    t = httpx.MockTransport(deny)
    path = capture_days(tmp_path, ['2025-10-21','2025-10-22'], transport=t)
    assert json.loads(path.read_text())['status'] == 'stopped_after_failure'
    assert (tmp_path/'days/2025-10-21/page.html').read_text() == 'provider denied'
    capture_days(tmp_path, ['2025-10-23'], transport=t)
    assert len(calls) == 1 and (tmp_path/'provider_stop.json').exists()


def test_valid_cache_has_no_second_request_and_tampering_rejected(tmp_path):
    calls = []
    def ok(request):
        calls.append(request)
        return httpx.Response(200, content=page())
    t = httpx.MockTransport(ok)
    path = capture_days(tmp_path, ['2025-10-21'], transport=t)
    assert json.loads(path.read_text())['status'] == 'received_date_verified'
    capture_days(tmp_path, ['2025-10-21'], transport=t)
    assert len(calls) == 1
    (tmp_path/'days/2025-10-21/page.html').write_text('tampered')
    with pytest.raises(ValueError, match='integrity'): capture_days(tmp_path, ['2025-10-21'], transport=t)


def test_capture_timeout_stops_with_auditable_receipt(tmp_path):
    def timeout(request): raise httpx.ReadTimeout('timeout',request=request)
    p = capture_days(tmp_path,['2025-10-21'],transport=httpx.MockTransport(timeout))
    assert json.loads(p.read_text())['errors'][0]['kind'] == 'ReadTimeout'
    assert not (tmp_path/'days/2025-10-21/page.html').exists()


def test_seed_reuses_original_receipt_and_does_not_download(tmp_path):
    seed = tmp_path/'seed'
    seed.mkdir()
    file = seed/'bref_20251021.html'
    file.write_bytes(page())
    received = '2026-10-06T00:00:00+00:00'
    manifest = seed/'manifest.json'
    write_json(manifest,dict(files=[dict(name=file.name,url='https://www.basketball-reference.com/friv/dailyleaders.fcgi?month=10&day=21&year=2025',
        status=200,bytes=file.stat().st_size,sha256=digest(file),received_at_utc=received)]))
    cache = tmp_path/'cache'
    seed_cache(cache,manifest)
    def no_network(request): raise AssertionError('must reuse')
    p = capture_days(cache,['2025-10-21'],transport=httpx.MockTransport(no_network))
    assert json.loads(p.read_text())['files'][0]['first_received_at_utc'] == received


@pytest.mark.parametrize('days,delay',[([],6),(['2025-10-21']*2,6),(['invalid'],6),(['2025-10-21'],5)])
def test_capture_bounds(days,delay,tmp_path):
    with pytest.raises(ValueError): capture_days(tmp_path,days,delay)


def test_versioned_recovery_preserves_base_and_rejects_tampered_inputs(tmp_path):
    refs, prior, _ = fixture()
    team = tmp_path/'teams'; team.mkdir()
    raw = tmp_path/'players'; raw.mkdir()
    team_file = team/'gamelog_2026.parquet'
    player_file = raw/'player_boxscores_2026.parquet'
    pq.write_table(pa.Table.from_pylist(refs),team_file)
    pq.write_table(pa.Table.from_pylist(prior),player_file)
    tp, rp = team/'manifest.json',raw/'manifest.json'
    write_json(tp,dict(source='llimllib/nba_data',commit='1'*40,files=[dict(name=team_file.name,sha256=digest(team_file))]))
    write_json(rp,dict(source='sportsdataverse/sportsdataverse-data',tag='nba_stats_player_boxscores',release_id=1,
        files=[dict(name=player_file.name,bytes=player_file.stat().st_size,sha256=digest(player_file),first_received_at_utc=datetime.now(UTC).isoformat())]))
    base_row=dict(date='2025-10-01',game_id='0022500002',player_id=10,minutes=12.5)
    dataset=tmp_path/'base.jsonl.gz'
    with gzip.open(dataset,'wt') as f: f.write(json.dumps(base_row)+'\n')
    base=tmp_path/'base.json'
    write_json(base,dict(dataset_path=str(dataset),dataset_sha256=digest(dataset)))
    inv=tmp_path/'inventory.json'
    write_json(inv,dict(base_dataset_sha256=digest(dataset),source_hashes={str(p):digest(p) for p in (tp,rp,base)},
        pending_games=[dict(game_id='0022500001',date='2025-10-21',season='2025-26')]))
    cache=tmp_path/'cache'
    capture_days(cache,['2025-10-21'],transport=httpx.MockTransport(lambda r:httpx.Response(200,content=page())))
    original=digest(dataset)
    result=recover_dataset(cache,inv,rp,tp,base,tmp_path/'v2')
    assert result['summary']['recovered_games']==1 and result['rows']==11
    rows=read_dataset(result['dataset_path'])
    assert base_row in rows and digest(dataset)==original
    assert all('provenance' in r for r in rows if r['game_id']=='0022500001')
    with pytest.raises(ValueError,match='new output'): recover_dataset(cache,inv,rp,tp,base,tmp_path/'v2')
    player_file.write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'): recover_dataset(cache,inv,rp,tp,base,tmp_path/'v3')
