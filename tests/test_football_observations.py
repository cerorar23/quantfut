from copy import deepcopy

import pytest

from qf.ingest.football_observations import validate_identity


def identity():
    row={'source_match_id':'123','league_id':'it.serie_b',
         'kickoff_utc':'2025-05-09T18:30:00Z','home_goals':2,'away_goals':1,
         'home_source_team_id':'10','away_source_team_id':'20'}
    decision={'mapping_status':'matched','match_id':'existing',
              'home_team_id':1,'away_team_id':2}
    parent={**deepcopy(row),'match_id':'existing','status':'finished',
            'home_team_id':1,'away_team_id':2,'external_ids':{'sofascore':'123'}}
    return row,decision,parent


@pytest.mark.parametrize('change,reason',[
    ({'away_goals':2},'teams_or_score_changed'),
    ({'home_team_id':2,'away_team_id':1},'teams_or_score_changed'),
    ({'home_source_team_id':'11'},'teams_or_score_changed'),
    ({'league_id':'it.serie_a'},'identity_changed'),
    ({'external_ids':{'sofascore':'124'}},'identity_changed'),
    ({'kickoff_utc':'2025-05-12T18:30:00Z'},'kickoff_changed'),
])
def test_new_capture_cannot_reassign_the_frozen_original(change,reason):
    row,decision,parent=identity()
    validate_identity(row,decision,parent)
    parent.update(change)
    with pytest.raises(ValueError,match=reason):validate_identity(row,decision,parent)


def test_unresolved_or_missing_parent_is_never_enriched():
    row,decision,parent=identity()
    with pytest.raises(ValueError,match='requires_existing_mapping'):
        validate_identity(row,decision,None)
    decision['mapping_status']='unresolved'
    with pytest.raises(ValueError,match='requires_existing_mapping'):
        validate_identity(row,decision,parent)
