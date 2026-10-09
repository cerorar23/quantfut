"""Bounded remote expiry admission; never assume two host UTC clocks coincide."""
import math
from datetime import timedelta
from .context import utc


def clock_bounds(samples,max_wall_jump_seconds=.25):
    if not samples:raise ValueError('clock samples required')
    lowers=[];uppers=[];observed=[]
    for sample in samples:
        a,b,remote=(utc(sample[k]) for k in ['local_start_utc','local_end_utc','remote_utc'])
        elapsed=sample['local_monotonic_elapsed_seconds'];wall=(b-a).total_seconds()
        if type(elapsed) not in {float,int} or not math.isfinite(elapsed) or elapsed<0 or wall<0 or abs(wall-elapsed)>max_wall_jump_seconds:
            raise ValueError('wall-clock discontinuity or invalid sample')
        lowers.append((remote-b).total_seconds());uppers.append((remote-a).total_seconds());observed.append(b)
    lower,upper=max(lowers),min(uppers)
    if lower>upper:raise ValueError('no stable offset intersection')
    return dict(remote_minus_local_lower_seconds=lower,remote_minus_local_upper_seconds=upper,
        observed_at_local_utc=max(observed).isoformat(),samples=len(samples),assumption='Offset stable during samples and admission interval; no NTP synchronization claim')


def expiry_admission(expires_at_local_utc,now_remote_utc,as_of_local_utc,bounds,maximum_age_seconds=30,guard_seconds=1):
    if bounds is None:return dict(admitted=False,reason='clock_bounds_missing')
    if (type(maximum_age_seconds) not in {int,float} or not math.isfinite(maximum_age_seconds) or maximum_age_seconds<=0
            or type(guard_seconds) not in {int,float} or not math.isfinite(guard_seconds) or guard_seconds<0):raise ValueError('invalid clock policy')
    age=(utc(as_of_local_utc)-utc(bounds['observed_at_local_utc'])).total_seconds()
    if not 0<=age<=maximum_age_seconds:return dict(admitted=False,reason='clock_bounds_stale_or_future')
    lower,upper=(bounds[k] for k in ['remote_minus_local_lower_seconds','remote_minus_local_upper_seconds'])
    if not all(type(v) in {int,float} and math.isfinite(v) for v in [lower,upper]) or lower>upper:raise ValueError('invalid offset interval')
    difference=(utc(expires_at_local_utc)-utc(now_remote_utc)).total_seconds()
    remaining_lower=difference+lower;remaining_upper=difference+upper
    return dict(admitted=remaining_lower>guard_seconds,reason='safely_before_expiry' if remaining_lower>guard_seconds else 'expiry_uncertain_or_too_close',
        remaining_lower_seconds=remaining_lower,remaining_upper_seconds=remaining_upper,guard_seconds=guard_seconds,
        original_historical_receipt_proved=False)


def remote_deadline(expires_at_local_utc,as_of_local_utc,bounds,guard_seconds=1):
    if bounds is None:return dict(admitted=False,reason='clock_bounds_missing')
    # Evaluate against the latest remote clock compatible with the measured interval.
    remote_upper=utc(as_of_local_utc)+timedelta(seconds=bounds['remote_minus_local_upper_seconds'])
    result=expiry_admission(expires_at_local_utc,remote_upper.isoformat(),as_of_local_utc,bounds,guard_seconds=guard_seconds)
    if result['admitted']:
        result['remote_expires_at_utc']=(utc(expires_at_local_utc)+timedelta(seconds=bounds['remote_minus_local_lower_seconds']-guard_seconds)).isoformat()
    return result
