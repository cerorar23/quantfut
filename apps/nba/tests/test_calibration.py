import pytest

from nba.calibration import diagnostics, calibration_report


def test_discrete_interval_mass_differs_from_nominal():
    result=diagnostics([.2,.3,.5],1,"game:player")
    assert result["interval_mass"] == 1.0
    assert result["covered80"] == 1
    assert .2 <= result["randomized_pit"] <= .5
    assert diagnostics([.2,.3,.5],1,"game:player") == result
    assert diagnostics([.2,.3,.5],1,"another:player")["randomized_pit"] != result["randomized_pit"]


@pytest.mark.parametrize("pmf,actual", [([.2,.2],0),([.5,-.2,.7],1),([1.0],2),([float('nan')],0)])
def test_invalid_distribution_rejected(pmf,actual):
    with pytest.raises(ValueError):
        diagnostics(pmf,actual,"test")


def test_diagnostic_rejects_altered_truth_before_scoring():
    actual=dict(game_id="1",player_id=2,date="2025-10-22",season="2025-26",rebounds=3,minutes=20)
    prediction=dict(game_id="1",player_id=2,date="2025-10-22",season="2025-26",actual_rebounds=4,actual_minutes=20)
    with pytest.raises(ValueError,match="integrity mismatch"):
        calibration_report([actual],[prediction],{})
