"""Artificial fixtures only."""
import json
import pandas as pd
import pytest
from tennis_intake_v1 import provider_key, Directory, rules_for, result_of, fixtures


def canon():
    rows = [dict(circuit='WTA', period='2026-09-01', tourney_name='Ningbo', surface='Hard', tourney_level='P', winner_id='w1', winner_name='Daria Snigur',
                 loser_id='w2', loser_name='Kaja Juvan'),
            dict(circuit='WTA', period='2026-09-08', tourney_name='Ningbo Open', surface='Hard', tourney_level='P', winner_id='w3', winner_name='Dana Snigur',
                 loser_id='w4', loser_name='Ena Shibahara'),
            dict(circuit='ATP', period='2026-01-12', tourney_name='Australian Open', surface='Hard', tourney_level='G', winner_id='a1',
                 winner_name='Alex de Minaur', loser_id='a2', loser_name='Juan Manuel Cerundolo')]
    return pd.DataFrame(rows)


def test_provider_names_parse_and_resolve_strictly():
    assert provider_key('D. Snigur') == ('snigur', 'd')
    assert provider_key('J. M. Cerundolo') == ('cerundolo', 'j')
    assert provider_key('J-L. Struff') == ('struff', 'j')
    d = Directory(canon(), '2026-10-20')
    assert d.player('ATP', 'A. De Minaur') == 'a1'
    assert d.player('WTA', 'E. Shibahara') == 'w4'
    with pytest.raises(ValueError, match='ambiguous'):
        d.player('WTA', 'D. Snigur')  # Daria and Dana
    with pytest.raises(ValueError, match='unknown'):
        d.player('WTA', 'Z. Nobody')


def test_tournament_rules_and_ambiguity():
    d = Directory(canon(), '2026-10-20')
    assert d.tournament('WTA', 'Ningbo').surface == 'Hard'  # exact name wins over 'Ningbo Open'
    extra = canon()._append(dict(circuit='ATP', period='2026-05-01', tourney_name='Lyon Open', surface='Clay', tourney_level='A', winner_id='a3',
        winner_name='X Y', loser_id='a4', loser_name='Z W'), ignore_index=True) if hasattr(pd.DataFrame, '_append') else None
    extra = pd.concat([extra, extra.iloc[[-1]].assign(tourney_name='Lyon Challenger', tourney_level='C')], ignore_index=True)
    with pytest.raises(ValueError, match='ambiguous'):
        Directory(extra, '2026-10-20').tournament('ATP', 'Lyon (France) - Qualification')
    slam = d.tournament('ATP', 'Australian Open')
    assert rules_for(dict(circuit='ATP', event_qualification='False', tournament_name='Australian Open'), slam) == dict(surface='Hard', best_of=5, deciding_tiebreak=10)
    assert rules_for(dict(circuit='ATP', event_qualification='True', tournament_name='Australian Open'), slam)['best_of'] == 3


def test_results_are_oriented_and_latest_fixture_wins(tmp_path):
    e = dict(event_key=1, event_status='Finished', event_winner='Second Player', scores=[dict(score_set='1', score_first='6', score_second='2'),
             dict(score_set='2', score_first='4', score_second='6'), dict(score_set='3', score_first='6.0', score_second='7.0')], received_at='t')
    r = result_of(e)
    assert r['a_won'] is False and r['score_A_B'] == '6-2 4-6 6-7' and r['completed_sets'] == 3
    assert result_of(dict(e, event_status='1')) is None
    for i, (status, at) in enumerate([('', '2026-10-20T01:00:00+00:00'), ('Finished', '2026-10-20T09:00:00+00:00')]):
        folder = tmp_path / 'originals' / str(i); folder.mkdir(parents=True)
        (folder / 'response.json').write_text(json.dumps(dict(result=[dict(e, event_status=status)])))
        (folder / 'receipt.json').write_text(json.dumps(dict(method='get_fixtures', http_status=200, params=dict(event_type_key='266'),
            source_path=str(folder / 'response.json'), received_at=at, sha256='x')))
    assert fixtures(tmp_path)['1']['event_status'] == 'Finished'


def test_editions_by_calendar_initials_and_level_separate_namesakes():
    rows = [dict(circuit='ATP', period='2026-05-18', tourney_date=20260518, tourney_name='Lyon', surface='Clay', tourney_level='250',
                 winner_id='a1', winner_name='Brandon Nakashima', loser_id='a2', loser_name='Alex Paz'),
            dict(circuit='ATP', period='2025-10-20', tourney_date=20251020, tourney_name='Lyon', surface='Hard', tourney_level='C',
                 winner_id='a3', winner_name='Bryce Nakashima', loser_id='a4', loser_name='Leo Ruiz'),
            dict(circuit='WTA', period='2026-09-01', tourney_date=20260901, tourney_name='Ningbo', surface='Hard', tourney_level='500',
                 winner_id='w1', winner_name='Xinyu Wang', loser_id='w2', loser_name='Xiyu Wang')]
    d = Directory(pd.DataFrame(rows), '2026-10-26')
    assert d.tournament('ATP', 'Lyon (France) - Qualification', pd.Timestamp('2026-10-21')).surface == 'Hard'
    assert d.tournament('ATP', 'Lyon', pd.Timestamp('2026-05-20')).surface == 'Clay'
    with pytest.raises(ValueError, match='edition unknown'):
        d.tournament('ATP', 'Lyon', pd.Timestamp('2026-08-01'))
    assert d.player('WTA', 'Xin. Wang') == 'w1'
    with pytest.raises(ValueError, match='ambiguous'):
        d.player('WTA', 'X. Wang')
    assert d.player('ATP', 'B. Nakashima', '500') == 'a1' and d.player('ATP', 'B. Nakashima', 'C') == 'a3'
    with pytest.raises(ValueError, match='ambiguous'):
        d.player('ATP', 'B. Nakashima')


class FakeMotor:
    def __init__(self, priced):
        self.priced, self.config = priced, dict(odds_provider='propline')
        self.canonical = pd.DataFrame([dict(circuit='WTA', period='2026-10-05', tourney_date=20261005, tourney_name='Tokyo', surface='Hard',
                                            tourney_level='500', winner_id='w1', winner_name='Ana Paz', loser_id='w2', loser_name='Eva Sol')])

    def forecast(self, circuit, a, b, surface, date, best_of, tiebreak):
        return dict(players=['Ana Paz', 'Eva Sol'], winner=dict(final_winner=.6, source='live_snapshot' if self.priced else 'v7_stack'),
                    odds_used=self.priced)


def fixture_archive(tmp_path, start):
    folder = tmp_path / 'cap' / 'originals' / '0'
    folder.mkdir(parents=True)
    e = dict(event_key=7, event_date=start[:10], event_time=start[11:16], event_status='', event_first_player='A. Paz',
             event_second_player='E. Sol', tournament_name='Tokyo', tournament_round='R16')
    (folder / 'response.json').write_text(json.dumps(dict(result=[e])))
    (folder / 'receipt.json').write_text(json.dumps(dict(method='get_fixtures', http_status=200, params=dict(event_type_key='266'),
                                                         received_at='2026-10-26T00:00:00+00:00', sha256='x')))
    return tmp_path / 'cap'


def test_sealing_waits_for_the_window_and_for_a_market_price(tmp_path):
    from tennis_intake_v1 import seal_new
    cap = fixture_archive(tmp_path, '2026-10-26T14:00')
    at = lambda stamp: (lambda: stamp)
    built = []
    factory = lambda: built.append(1) or FakeMotor(priced=False)
    r = seal_new(tmp_path / 'a', cap, factory, at('2026-10-26T10:25:00+00:00'))
    assert r['waiting'] == 1 and not r['sealed'] and not built  # the motor is not even loaded
    r = seal_new(tmp_path / 'a', cap, factory, at('2026-10-26T12:25:00+00:00'))
    assert r['deferred_no_market'] == 1 and not r['sealed']  # one more hourly run remains before the start
    r = seal_new(tmp_path / 'a', cap, factory, at('2026-10-26T13:25:00+00:00'))
    assert len(r['sealed']) == 1  # last run: sealed without a price rather than not at all
    r = seal_new(tmp_path / 'b', cap, FakeMotor(priced=True), at('2026-10-26T12:25:00+00:00'))
    assert len(r['sealed']) == 1
