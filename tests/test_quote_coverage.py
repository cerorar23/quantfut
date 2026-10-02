"""La auditoría de cuotas distingue primera observación de apertura real."""
from datetime import datetime, timedelta, timezone

from qf.eval import quote_coverage as coverage


def test_primera_terna_y_antiguedad_del_proveedor():
    kickoff = datetime(2026, 9, 26, 18, tzinfo=timezone.utc)
    base = {"match_id": "m1", "league_id": "es.laliga",
            "kickoff_utc": kickoff, "source": "api_football",
            "bookmaker": "pinnacle"}
    rows = [
        {**base, "observed_at": kickoff - timedelta(hours=30),
         "provider_at": kickoff - timedelta(hours=50)},
        {**base, "observed_at": kickoff - timedelta(hours=90),
         "provider_at": kickoff - timedelta(hours=91)},
        {**base, "observed_at": kickoff + timedelta(minutes=1),
         "provider_at": kickoff - timedelta(hours=1)},
    ]
    report = coverage.summarize(rows, {"es.laliga": 2})
    assert len(report) == 1
    assert report[0]["matches_with_complete_1x2"] == 1
    assert report[0]["coverage_pct"] == 50
    assert report[0]["first_seen_lead_hours_median"] == 90
    assert report[0]["first_seen_at_least_72h"] == 1
    assert report[0]["provider_age_at_first_seen_hours_median"] == 1


def test_no_usa_precio_cuya_actualizacion_es_futura():
    kickoff = datetime(2026, 9, 26, 18, tzinfo=timezone.utc)
    row = {"match_id": "m1", "league_id": "es.laliga",
           "kickoff_utc": kickoff, "source": "api_football",
           "bookmaker": "pinnacle",
           "observed_at": kickoff - timedelta(hours=4),
           "provider_at": kickoff - timedelta(hours=3)}
    assert coverage.summarize([row], {"es.laliga": 1}) == []


def test_edad_desconocida_no_se_reporta_como_cero():
    kickoff = datetime(2026, 9, 26, 18, tzinfo=timezone.utc)
    row = {"match_id": "m1", "league_id": "es.laliga",
           "kickoff_utc": kickoff, "source": "the_odds_api",
           "bookmaker": "pinnacle",
           "observed_at": kickoff - timedelta(hours=72),
           "provider_at": None}
    result = coverage.summarize([row], {"es.laliga": 1})
    assert result[0]["provider_age_at_first_seen_hours_median"] is None
