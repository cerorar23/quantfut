import pytest
from nba.clock_policy import clock_bounds,expiry_admission,remote_deadline

def bounds():return clock_bounds([dict(local_start_utc='2026-10-08T18:00:00Z',local_end_utc='2026-10-08T18:00:00.2Z',remote_utc='2026-10-08T17:59:59.2Z',local_monotonic_elapsed_seconds=.2)])

def test_offset_interval_and_conservative_expiry():
    b=bounds();assert b['remote_minus_local_lower_seconds']==-1 and b['remote_minus_local_upper_seconds']==-.8
    result=expiry_admission('2026-10-08T18:00:10Z','2026-10-08T18:00:00Z','2026-10-08T18:00:01Z',b)
    assert result['admitted'] and result['remaining_lower_seconds']==9

def test_clock_uncertainty_near_expiry_rejects_send():
    b=bounds();result=expiry_admission('2026-10-08T18:00:01Z','2026-10-08T18:00:00Z','2026-10-08T18:00:01Z',b,guard_seconds=0)
    assert not result['admitted'] and result['remaining_lower_seconds']==0 and result['remaining_upper_seconds']==pytest.approx(.2)

@pytest.mark.parametrize('now',['2026-10-08T18:01:00Z','2026-10-08T17:59:59Z'])
def test_stale_or_future_clock_witness_rejected(now):
    assert not expiry_admission('2026-10-08T18:05:00Z','2026-10-08T18:00:00Z',now,bounds())['admitted']

def test_missing_bounds_and_wall_jump_do_not_assume_sync():
    assert not expiry_admission('2026-10-08T18:05:00Z','2026-10-08T18:00:00Z','2026-10-08T18:00:01Z',None)['admitted']
    with pytest.raises(ValueError):clock_bounds([dict(local_start_utc='2026-10-08T18:00:00Z',local_end_utc='2026-10-08T18:00:10Z',remote_utc='2026-10-08T18:00:01Z',local_monotonic_elapsed_seconds=.2)])

def test_contradictory_offsets_rejected():
    a=dict(local_start_utc='2026-10-08T18:00:00Z',local_end_utc='2026-10-08T18:00:00.2Z',remote_utc='2026-10-08T18:00:00.1Z',local_monotonic_elapsed_seconds=.2)
    with pytest.raises(ValueError):clock_bounds([a,dict(a,remote_utc='2026-10-08T18:00:10Z')])


def test_safe_remote_deadline_uses_earliest_offset_and_rejects_stale_bounds():
    result=remote_deadline('2026-10-08T18:00:10Z','2026-10-08T18:00:01Z',bounds())
    assert result['admitted'] and result['remote_expires_at_utc']=='2026-10-08T18:00:08+00:00'
    assert not remote_deadline('2026-10-08T18:05:00Z','2026-10-08T18:01:00Z',bounds())['admitted']
