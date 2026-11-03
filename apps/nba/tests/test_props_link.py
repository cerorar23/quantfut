from nba import props_link as pl

PLAYERS = [
    dict(game_id='g1', name='Jaren Jackson Jr.', player_id=1, team_id=10, participated=True, minutes=30., points=20, rebounds=5, assists=2, threes=3),
    dict(game_id='g1', name='Nikola Jokić', player_id=2, team_id=11, participated=True, minutes=35., points=30, rebounds=12, assists=9, threes=1),
    dict(game_id='g1', name='Marcus Morris', player_id=3, team_id=10, participated=False, minutes=0., points=0, rebounds=0, assists=0, threes=0),
    dict(game_id='g1', name='Marcus Morris Sr.', player_id=4, team_id=11, participated=True, minutes=9., points=4, rebounds=1, assists=0, threes=0),
]


def quote(player, market='player_points', game='g1'):
    return dict(game_id=game, player=player, market=market, line=20.5)


def test_exact_accent_and_suffix_matches_attach_the_realised_stat():
    rows, stats, unmatched = pl.link([quote('Nikola Jokic', 'player_rebounds'), quote('Jaren Jackson'), quote('Jaren Jackson Jr.')], PLAYERS)
    assert [(r['player_id'], r['actual']) for r in rows] == [(2, 12), (1, 20), (1, 20)]
    assert stats == dict(exact=2, suffix=1) and not unmatched


def test_unknown_name_stays_unmatched_and_absent_player_keeps_quote_without_outcome():
    rows, stats, unmatched = pl.link([quote('Unknown Guy'), quote('Nikola Jokic', game='g2'), quote('Marcus Morris')], PLAYERS)
    assert [(r['player_id'], r['actual'], r['participated']) for r in rows] == [(2, None, None), (3, 0, False)]
    assert stats == dict(unmatched=1, no_box_row=1, exact=1) and sum(unmatched.values()) == 1


def test_alias_applies_only_inside_the_games_roster():
    roster = [dict(PLAYERS[0], name='Bub Carrington', player_id=9)]
    rows, stats, _ = pl.link([quote('Carlton Carrington')], roster)
    assert rows[0]['player_id'] == 9 and rows[0]['actual'] == 20 and stats == dict(exact=1)
