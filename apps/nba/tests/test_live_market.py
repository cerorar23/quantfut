from datetime import UTC, datetime, timedelta
import json

import numpy as np
import pytest

from nba import live_market as lm
from nba import odds_history as oh
from nba.audit import digest, write_json
from nba.multimarket_live_dashboard import LiveCohort
from nba import multimarket_v13_live as live

from test_multimarket_v13_live import GID, TIP, box_html, cohort  # noqa: F401  (cohort is a fixture)

SEAL = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)  # the fixture seals at this moment
STATS = dict(bootstrap=100, seed=3)


@pytest.fixture(autouse=True)
def open_the_gate(monkeypatch):
    monkeypatch.setattr(oh, 'NOT_BEFORE', datetime(2026, 10, 1, tzinfo=UTC))


def event(home='Bbb Club', away='Aaa Club', start=TIP, updated=None, home_price=1.6, away_price=2.4, book='pinnacle'):
    updated = (updated or SEAL + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return dict(id='x', commence_time=start.strftime('%Y-%m-%dT%H:%M:%SZ'), home_team=home, away_team=away, bookmakers=[
        dict(key=book, last_update=updated, markets=[dict(key='h2h', last_update=updated, outcomes=[
            dict(name=home, price=home_price), dict(name=away, price=away_price)])])])


class Reply:
    def __init__(self, events, status=200, last=1, remaining=19000):
        self.content, self.status_code = json.dumps(events).encode(), status
        self.headers = {'x-requests-last': str(last), 'x-requests-remaining': str(remaining)}


class Client:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def get(self, url, params, timeout):
        self.calls.append((url, dict(params)))
        return self.replies.pop(0)


def test_nothing_is_requested_before_the_gate(cohort, monkeypatch):
    folder, _ = cohort
    monkeypatch.setattr(oh, 'NOT_BEFORE', datetime(2026, 11, 1, tzinfo=UTC))
    client = Client(Reply([event()]))
    with pytest.raises(PermissionError):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=2))
    assert client.calls == [] and not (folder / 'market').exists()


def test_seal_capture_is_stored_write_once_with_hash_and_one_request(cohort):
    folder, _ = cohort
    client = Client(Reply([event()]), Reply([event()]))
    out = lm.capture(folder, 'secret', client, SEAL + timedelta(minutes=2))
    assert out == dict(stored=True, stop=None, credits=1, remaining=19000) and len(client.calls) == 1
    url, params = client.calls[0]
    assert url == lm.ENDPOINT and params['bookmakers'] == 'pinnacle' and params['markets'] == 'h2h'
    receipt = json.loads((folder / 'market' / 'seal.json').read_bytes())
    assert receipt['raw_sha256'] == digest(folder / 'market' / 'seal_raw.json') and 'secret' not in json.dumps(receipt)
    assert 'secret' not in (folder / 'market' / 'attempts.jsonl').read_text()
    with pytest.raises(ValueError, match='already captured'):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=3))
    assert len(client.calls) == 1
    LiveCohort(folder)  # the extra folder does not disturb the sealed cohort


def test_a_late_seal_price_is_refused_before_a_credit_is_spent(cohort):
    folder, _ = cohort
    client = Client(Reply([event()]))
    with pytest.raises(lm.LateCapture):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=16))
    with pytest.raises(ValueError, match='before the cohort is sealed'):
        lm.capture(folder, 'k', client, SEAL - timedelta(minutes=1))
    with pytest.raises(ValueError, match='has started'):
        lm.capture(folder, 'k', client, TIP + timedelta(minutes=1))
    assert client.calls == []


def test_close_phase_needs_the_seal_price_and_is_not_bound_by_the_gap(cohort):
    folder, _ = cohort
    with pytest.raises(ValueError, match='needs the seal-phase price'):
        lm.capture(folder, 'k', Client(Reply([event()])), TIP - timedelta(minutes=20), phase='close')
    lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=1))
    out = lm.capture(folder, 'k', Client(Reply([event(home_price=1.5, away_price=2.7, updated=TIP - timedelta(minutes=25))])), TIP - timedelta(minutes=20), phase='close')
    assert out['stored'] is True and (folder / 'market' / 'close.json').exists()


def test_http_error_and_unexpected_cost_are_logged_and_never_retried(cohort):
    folder, _ = cohort
    client = Client(Reply([], status=429), Reply([event()], last=10))
    assert lm.capture(folder, 'k', client, SEAL + timedelta(minutes=1)) == dict(stored=False, stop='http_429')
    assert not (folder / 'market' / 'seal.json').exists() and len(client.calls) == 1
    again = lm.capture(folder, 'k', client, SEAL + timedelta(minutes=2))  # a person re-runs it; the response is stored and flagged
    assert again['stop'] == 'unexpected_cost' and again['credits'] == 10
    lines = (folder / 'market' / 'attempts.jsonl').read_text().splitlines()
    assert [json.loads(x)['http_status'] for x in lines] == [429, 200]


def test_the_reserve_stops_a_capture_when_the_last_known_balance_is_low(cohort):
    folder, _ = cohort
    lm.capture(folder, 'k', Client(Reply([], status=500, remaining=2000)), SEAL + timedelta(minutes=1))
    client = Client(Reply([event()]))
    with pytest.raises(ValueError, match='reserve'):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=2), reserve=2000)
    assert client.calls == []


GAME = dict(event_id='e1', home_team='LA Clippers', away_team='Boston Celtics', tipoff_utc='2026-10-21T23:00:00+00:00')


def rows_for(events, received=SEAL + timedelta(minutes=2)):
    return lm.price_rows(events, received, [GAME])


def test_price_rows_match_names_start_time_and_book():
    good = event('Los Angeles Clippers', 'Boston Celtics')
    out, why = rows_for([good])
    row = out['e1']
    assert why == {} and row['home_no_vig'] == pytest.approx((1 / 1.6) / (1 / 1.6 + 1 / 2.4)) and row['minutes_to_tipoff'] == pytest.approx(510 - 2 + 0, abs=1)
    assert 0 < row['overround'] < .1 and row['home_no_vig_power'] != row['home_no_vig']
    for bad, reason in ((event('Los Angeles Clippers', 'Boston Celtics', book='bet365'), 'no_pinnacle'),
                        (event('Los Angeles Clippers', 'Miami Heat'), 'no_event'),
                        (event('Los Angeles Clippers', 'Boston Celtics', start=TIP + timedelta(minutes=30)), 'no_event'),
                        (event('Los Angeles Clippers', 'Boston Celtics', start=SEAL), 'no_event'),
                        (event('Los Angeles Clippers', 'Boston Celtics', updated=SEAL - timedelta(hours=2)), 'invalid_or_stale_price'),
                        (event('Los Angeles Clippers', 'Boston Celtics', updated=SEAL + timedelta(hours=1)), 'invalid_or_stale_price'),
                        (event('Los Angeles Clippers', 'Boston Celtics', home_price=1.0), 'invalid_or_stale_price')):
        out, why = rows_for([bad])
        assert out == {} and why == {reason: 1}, (reason, why)
    out, why = rows_for([good, good])
    assert out == {} and why == {'ambiguous_event': 1}


def test_a_game_that_started_before_the_price_is_not_priced():
    started = GAME | dict(tipoff_utc='2026-10-21T14:30:00+00:00')
    out, why = lm.price_rows([event('Los Angeles Clippers', 'Boston Celtics', start=datetime(2026, 10, 21, 14, 30, tzinfo=UTC))],
                             SEAL + timedelta(minutes=5), [started])
    assert out == {} and why == {'already_started': 1}


def finish(folder, monkeypatch, home=110, away=104):
    now = TIP + timedelta(hours=4)

    def result(game_id, destination, game_slug=None):
        destination.mkdir(parents=True)
        (destination / 'boxscore.html').write_bytes(box_html(3, home, away))
        write_json(destination / 'receipt.json', dict(
            url=f'https://www.nba.com/game/{game_slug}/box-score', game_id=game_id, http_status=200, error=None,
            raw_sha256=digest(destination / 'boxscore.html'), requested_at_utc=now.isoformat(),
            first_received_at_utc=now.isoformat(), raw_file='boxscore.html'))
        return destination / 'receipt.json'
    monkeypatch.setattr('nba.paper.capture_official_result', result)
    live.capture_results(folder, now)
    return now + timedelta(minutes=5)


def test_cohort_rows_join_the_sealed_forecast_the_official_result_and_the_price(cohort, monkeypatch):
    folder, _ = cohort
    lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=2))
    lm.capture(folder, 'k', Client(Reply([event(home_price=1.4, away_price=3.1, updated=TIP - timedelta(minutes=35))])), TIP - timedelta(minutes=30), phase='close')
    after = finish(folder, monkeypatch)
    rows, cover = lm.cohort_rows(folder, after)
    (row,) = rows
    sealed = [f for f in json.loads((folder / 'bundle.json').read_bytes())['forecasts'] if f['market'] == 'winner'][0]
    assert row['model'] == sealed['probability_over'] and row['y'] == 1 and row['date'] == '2026-10-21'
    assert row['market'] == pytest.approx((1 / 1.6) / (1 / 1.6 + 1 / 2.4)) and row['market_close'] > row['market']
    assert cover == dict(sealed=1, evaluated=1, evaluated_with_price=1, price_reasons={}, captured=['close', 'seal'])
    # before the result exists nothing is evaluated, so nothing is compared
    assert lm.cohort_rows(folder, TIP - timedelta(hours=1))[0] == []


def test_a_changed_response_or_a_price_from_another_cohort_is_an_error(cohort, monkeypatch):
    folder, _ = cohort
    lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=2))
    after = finish(folder, monkeypatch)
    (folder / 'market' / 'seal_raw.json').write_text('[]')
    with pytest.raises(ValueError, match='response changed'):
        lm.cohort_rows(folder, after)
    (folder / 'market' / 'seal_raw.json').write_bytes(json.dumps([event()]).encode())
    receipt = json.loads((folder / 'market' / 'seal.json').read_bytes())
    write_json(folder / 'market' / 'seal.json', dict(receipt, raw_sha256=digest(folder / 'market' / 'seal_raw.json'), bundle_sha256='0' * 64))
    with pytest.raises(ValueError, match='does not belong'):
        lm.cohort_rows(folder, after)
    write_json(folder / 'market' / 'seal.json', dict(receipt, raw_sha256=digest(folder / 'market' / 'seal_raw.json'),
                                                      received_at_utc=(SEAL + timedelta(minutes=40)).isoformat()))
    with pytest.raises(ValueError, match='too late'):
        lm.cohort_rows(folder, after)


def test_report_lists_a_broken_cohort_without_hiding_the_good_one_and_is_interim_below_the_minimum(cohort, monkeypatch):
    folder, _ = cohort
    lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=2))
    after = finish(folder, monkeypatch)
    broken = folder.parent / 'cohorts' / 'broken'
    broken.mkdir(parents=True)
    write_json(broken / 'bundle.seal.json', dict(sha256='0' * 64))
    write_json(broken / 'bundle.json', {})
    out = lm.report(folder.parent, after)  # the root contains 'cohort' (good) only; 'cohorts/broken' is one level deeper
    assert out['games'] == 1 and out['decision']['verdict'] == 'interim' and out['actionable'] is False
    broken_root = folder.parent / 'only_broken'
    (broken_root).mkdir()
    (broken_root / 'bad').mkdir()
    write_json(broken_root / 'bad' / 'bundle.seal.json', dict(sha256='0' * 64))
    write_json(broken_root / 'bad' / 'bundle.json', {})
    bad = lm.report(broken_root, after)
    assert bad['games'] == 0 and bad['problems'][0]['cohort'] == 'bad' and bad['comparison'] == dict(n=0)


def synthetic(n=600, informative=0., seed=2, close=True):
    rng = np.random.default_rng(seed)
    market = np.clip(rng.uniform(.25, .75, n), .05, .95)
    model = np.clip(market + rng.normal(0, .07, n), .03, .97)
    p = 1 / (1 + np.exp(-(np.log(market / (1 - market)) + informative * (np.log(model / (1 - model)) - np.log(market / (1 - market))))))
    y = (rng.uniform(size=n) < p).astype(int)
    moved = np.clip(market + informative * (model - market) * .5 + rng.normal(0, .01, n), .03, .97)
    return [dict(game_id=str(i), date=f'2026-{11 + i % 4:02d}-{i % 27 + 1:02d}', model=float(m), y=int(o), market=float(k), overround=.03,
                 minutes_to_tipoff=500., market_close=float(c) if close else None)
            for i, (m, o, k, c) in enumerate(zip(model, y, market, moved))]


def test_clv_description_sees_a_market_that_moves_toward_an_informative_model():
    follows = lm.clv(synthetic(informative=1.), STATS)
    ignores = lm.clv(synthetic(informative=0.), STATS)
    assert follows['n'] == 600 and follows['same_direction_share'] > .7 and follows['slope_ci95'][0] > 0
    assert ignores['same_direction_share'] < .6 and ignores['slope_ci95'][0] <= 0 <= ignores['slope_ci95'][1] + .5
    assert lm.clv(synthetic(close=False), STATS) == dict(n=0)


def report_for(rows, evaluated=None, priced=None):
    comparison = __import__('nba.market_compare', fromlist=['x']).compare_to_market(rows, STATS)
    n = len(rows)
    return dict(games=n, coverage=dict(evaluated=evaluated or n, evaluated_with_price=priced or n), comparison=comparison)


def test_decision_waits_for_the_minimum_checks_coverage_and_applies_the_frozen_rule():
    assert lm.decide(report_for(synthetic(n=100)))['verdict'] == 'interim'
    assert lm.decide(report_for(synthetic(n=600), evaluated=1000, priced=700))['verdict'] == 'inconclusive'
    assert lm.decide(report_for(synthetic(n=3000, informative=1., seed=4)))['adds_information'] is True
    assert lm.decide(report_for(synthetic(n=3000, informative=0., seed=5)))['verdict'] == 'no_evidence_of_added_information'


# ---- server mode: key file, separate price folder, shared budget, idempotent tick -------------------------------

import shutil
import sys


def tree(folder):
    return {p.relative_to(folder).as_posix(): digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def test_key_file_accepts_the_servers_single_key_and_an_env_line_and_never_echoes_junk(tmp_path):
    (tmp_path / 'a').write_text('abcdefghijklmnopqrstuvwxyz012345')
    (tmp_path / 'b').write_text('OTHER=1\nODDS_API_KEY="abcdefghijklmnopqrstuvwxyz012345"\n')
    (tmp_path / 'c').write_text('SECRET with spaces')
    assert lm.read_key(tmp_path / 'a') == lm.read_key(tmp_path / 'b') == 'abcdefghijklmnopqrstuvwxyz012345'
    with pytest.raises(ValueError) as error:
        lm.read_key(tmp_path / 'c')
    assert 'SECRET' not in str(error.value)


def test_prices_can_live_outside_a_read_only_cohort_and_the_cohort_is_never_touched(cohort, monkeypatch, tmp_path):
    folder, _ = cohort
    before = tree(folder)
    root = tmp_path / 'price'
    out = lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=2), market_root=root)
    assert out['stored'] is True and (root / folder.name / 'seal.json').exists() and not (folder / 'market').exists()
    assert tree(folder) == before
    after = finish(folder, monkeypatch)
    finished = tree(folder)  # the official result is stored by the producer, not by the price step
    rows, cover = lm.cohort_rows(folder, after, root)
    assert len(rows) == 1 and cover['captured'] == ['seal'] and tree(folder) == finished
    assert lm.report(folder.parent, after, root)['games'] == 1
    assert lm.report(folder.parent, after)['games'] == 0  # without the folder there are no prices


def ledger_lines(ledger):
    return [json.loads(x) for x in (ledger / 'requests.jsonl').read_text().splitlines()]


def test_the_ledger_caps_requests_per_day_and_credits_per_month(cohort, tmp_path):
    folder, _ = cohort
    ledger = tmp_path / 'ledger'
    other = tmp_path / 'other'
    shutil.copytree(folder, other)  # a second, still unpriced cohort
    client = Client(Reply([event()]), Reply([event()]), Reply([event()]))
    lm.capture(folder, 'k', client, SEAL + timedelta(minutes=1), ledger=ledger)
    lm.capture(folder, 'k', client, TIP - timedelta(minutes=20), phase='close', ledger=ledger)
    with pytest.raises(lm.LedgerRefusal, match='daily limit'):
        lm.capture(other, 'k', client, SEAL + timedelta(minutes=2), ledger=ledger)
    assert len(client.calls) == 2 and len(ledger_lines(ledger)) == 2
    # the month still counts on a new day
    month = tmp_path / 'month'
    month.mkdir()
    (month / 'requests.jsonl').write_text(json.dumps(dict(at_utc='2026-10-02T00:00:00+00:00', credits=70, remaining=19000)) + '\n')
    with pytest.raises(lm.LedgerRefusal, match='monthly limit'):
        lm.capture(other, 'k', client, SEAL + timedelta(minutes=2), ledger=month)
    last_month = tmp_path / 'last_month'
    last_month.mkdir()
    (last_month / 'requests.jsonl').write_text(json.dumps(dict(at_utc='2026-09-30T00:00:00+00:00', credits=70, remaining=19000)) + '\n')
    assert lm.capture(other, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=2), ledger=last_month)['stored'] is True


def test_a_failure_halts_every_later_capture_until_a_person_removes_the_halt_file(cohort, tmp_path):
    folder, _ = cohort
    ledger = tmp_path / 'ledger'
    assert lm.capture(folder, 'k', Client(Reply([], status=429)), SEAL + timedelta(minutes=1), ledger=ledger) == dict(stored=False, stop='http_429')
    halt = json.loads((ledger / 'halt').read_bytes())
    assert halt['reason'] == 'http_429' and halt['cohort'] == folder.name
    client = Client(Reply([event()]))
    with pytest.raises(lm.LedgerRefusal, match='halted'):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=2), ledger=ledger)
    assert client.calls == []
    (ledger / 'halt').unlink()
    assert lm.capture(folder, 'k', Client(Reply([event()])), SEAL + timedelta(minutes=3), ledger=ledger)['stored'] is True


def test_an_unexpected_cost_halts_but_keeps_the_stored_response(cohort, tmp_path):
    folder, _ = cohort
    ledger = tmp_path / 'ledger'
    out = lm.capture(folder, 'k', Client(Reply([event()], last=10)), SEAL + timedelta(minutes=1), ledger=ledger)
    assert out['stored'] is True and out['stop'] == 'unexpected_cost'
    assert json.loads((ledger / 'halt').read_bytes())['reason'] == 'unexpected_cost'


def test_a_transport_failure_counts_against_the_caps_without_halting_or_retrying(cohort, tmp_path):
    folder, _ = cohort
    ledger = tmp_path / 'ledger'

    class Down:
        calls = 0

        def get(self, url, params, timeout):
            Down.calls += 1
            raise TimeoutError('no answer')
    with pytest.raises(TimeoutError):
        lm.capture(folder, 'k', Down(), SEAL + timedelta(minutes=1), ledger=ledger)
    assert Down.calls == 1 and ledger_lines(ledger)[0]['credits'] == 1 and not (ledger / 'halt').exists()
    assert not (folder / 'market' / 'seal.json').exists()


def test_the_ledgers_last_known_balance_enforces_the_reserve(cohort, tmp_path):
    folder, _ = cohort
    ledger = tmp_path / 'ledger'
    ledger.mkdir()
    (ledger / 'requests.jsonl').write_text(json.dumps(dict(at_utc='2026-10-20T00:00:00+00:00', credits=1, remaining=2000)) + '\n')
    client = Client(Reply([event()]))
    with pytest.raises(lm.LedgerRefusal, match='reserve'):
        lm.capture(folder, 'k', client, SEAL + timedelta(minutes=1), reserve=2000, ledger=ledger)
    assert client.calls == []


def copies(folder, tmp_path, n):
    root = tmp_path / 'cohorts_copy'
    root.mkdir()
    for i in range(n):
        shutil.copytree(folder, root / f'c{i}')
    return root


def test_capture_pending_waits_for_the_gate_and_asks_for_nothing_when_nothing_is_due(cohort, monkeypatch, tmp_path):
    folder, _ = cohort
    client = Client()
    monkeypatch.setattr(oh, 'NOT_BEFORE', datetime(2026, 11, 1, tzinfo=UTC))
    assert lm.capture_pending(folder.parent, tmp_path / 'p', 'k', client, SEAL + timedelta(minutes=1), tmp_path / 'l') == [dict(blocked_until='2026-11-01')]
    monkeypatch.setattr(oh, 'NOT_BEFORE', datetime(2026, 10, 1, tzinfo=UTC))
    # sealed 20 minutes ago and no seal price: the moment has passed, so nothing is asked
    assert lm.capture_pending(folder.parent, tmp_path / 'p', 'k', client, SEAL + timedelta(minutes=20), tmp_path / 'l') == []
    # long before the close window
    assert lm.capture_pending(folder.parent, tmp_path / 'p', 'k', client, SEAL + timedelta(hours=3), tmp_path / 'l') == []
    assert client.calls == [] and not (tmp_path / 'l').exists()


def test_capture_pending_takes_the_seal_price_once_then_the_close_price_in_its_window(cohort, tmp_path):
    folder, _ = cohort
    root, ledger = tmp_path / 'p', tmp_path / 'l'
    client = Client(Reply([event()]), Reply([event(home_price=1.5, away_price=2.7, updated=TIP - timedelta(minutes=25))]))
    tick = lambda when: lm.capture_pending(folder.parent, root, 'k', client, when, ledger)
    first = tick(SEAL + timedelta(minutes=1))
    assert [(r['cohort'], r['phase'], r['stored']) for r in first] == [('cohort', 'seal', True)]
    assert tick(SEAL + timedelta(minutes=11)) == []  # the next 10-minute tick: nothing due
    assert tick(TIP - timedelta(minutes=45)) == [] and tick(TIP - timedelta(minutes=5)) == []  # outside the close window
    closing = tick(TIP - timedelta(minutes=20))
    assert [(r['phase'], r['stored']) for r in closing] == [('close', True)]
    assert tick(TIP - timedelta(minutes=19)) == [] and len(client.calls) == 2
    assert [e['phase'] for e in ledger_lines(ledger)] == ['seal', 'close']
    assert (root / 'cohort' / 'seal.json').exists() and (root / 'cohort' / 'close.json').exists() and not (folder / 'market').exists()


def test_capture_pending_stops_at_the_budget_and_lists_broken_cohorts_without_stopping_for_them(cohort, tmp_path):
    folder, _ = cohort
    cohorts = copies(folder, tmp_path, 3)
    broken = cohorts / 'broken'
    broken.mkdir()
    write_json(broken / 'bundle.seal.json', dict(sha256='0' * 64))
    (broken / 'bundle.json').write_text('not json')
    client = Client(Reply([event()]), Reply([event()]), Reply([event()]))
    out = lm.capture_pending(cohorts, tmp_path / 'p', 'k', client, SEAL + timedelta(minutes=1), tmp_path / 'l')
    assert [r.get('skipped') for r in out if r['cohort'] == 'broken'] == ['unreadable_bundle']
    stored = [r['cohort'] for r in out if r.get('stored')]
    refused = [r for r in out if 'refused' in r]
    assert stored == ['c0', 'c1'] and len(refused) == 1 and refused[0]['cohort'] == 'c2' and 'daily limit' in refused[0]['refused']
    assert len(client.calls) == 2


def test_the_command_line_does_not_read_the_key_or_call_anything_before_the_gate(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(oh, 'NOT_BEFORE', datetime(2999, 1, 1, tzinfo=UTC))
    monkeypatch.setattr(sys, 'argv', ['live_market', 'capture-pending', '--cohorts', str(tmp_path), '--market-root', str(tmp_path / 'p'),
                                       '--ledger', str(tmp_path / 'l'), '--key-file', str(tmp_path / 'does_not_exist')])
    lm.main()
    out = json.loads(capsys.readouterr().out)
    assert out['results'] == [dict(blocked_until='2999-01-01')] and not (tmp_path / 'p').exists() and not (tmp_path / 'l').exists()
