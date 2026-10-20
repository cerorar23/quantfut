"""Context features from explicitly timed observations, without invented dates."""
import hashlib
import math
from pathlib import Path
from datetime import timedelta
from .operations import utc


def source_valid(observation,decision_at):
    try:
        received=utc(observation['received_at'])
        if received>utc(decision_at):return False
        raw=Path(observation['source_path']).read_bytes()
        return hashlib.sha256(raw).hexdigest()==observation['source_sha256']
    except (KeyError,OSError,ValueError,TypeError):return False


def haversine_km(a,b):
    coordinates=[float(a[0]),float(a[1]),float(b[0]),float(b[1])]
    if not all(math.isfinite(x) for x in coordinates) or abs(coordinates[0])>90 or abs(coordinates[2])>90 or abs(coordinates[1])>180 or abs(coordinates[3])>180:
        raise ValueError('Invalid latitude/longitude')
    lat1,lon1,lat2,lon2=map(math.radians,coordinates)
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2*6371.0088*math.asin(math.sqrt(min(1.,max(0.,h))))


def player_context(player_id,start_at,decision_at,past_matches,venue=None):
    """Daily workload requires both known start AND end. Coverage remains explicit."""
    start=utc(start_at);decision=utc(decision_at)
    if decision>=start:raise ValueError('Context must be prepared before match start')
    history=[];excluded=0
    for row in past_matches:
        if player_id not in row.get('player_ids',[]):continue
        try:
            played=utc(row['actual_start']);ended=utc(row['actual_end'])
            valid=(row.get('date_precision')=='actual_utc' and source_valid(row,decision_at)
                   and played<ended<=decision and row.get('status') in ('completed','retired','disqualified'))
        except (KeyError,ValueError,TypeError):valid=False
        if valid:history.append(row)
        else:excluded+=1
    history.sort(key=lambda r:utc(r['actual_end']))
    result={'player_id':player_id,'as_of':decision_at,'target_start':start_at,
            'usable_past_matches':len(history),'excluded_uncertain_matches':excluded,
            'history_complete':False,'travel_km':None,'timezone_offset_change_hours':None,
            'altitude_change_m':None,'surface_changed':None,'rest_hours':None,
            'travel_status':'requires_reviewed_intertournament_transition',
            'workload_is_lower_bound':True,'personal_itinerary_known':False}
    for days in (7,14,30):
        rows=[r for r in history if utc(r['actual_end'])>=start-timedelta(days=days)]
        minutes=[r.get('minutes') for r in rows];sets=[r.get('sets_played') for r in rows]
        valid_minutes=[v for v in minutes if isinstance(v,(int,float)) and math.isfinite(v) and v>=0]
        valid_sets=[v for v in sets if isinstance(v,int) and not isinstance(v,bool) and 0<=v<=5]
        result[f'minutes_{days}d']=sum(valid_minutes) if len(valid_minutes)==len(rows) and rows else None
        result[f'sets_{days}d']=sum(valid_sets) if len(valid_sets)==len(rows) and rows else None
        result[f'observed_matches_{days}d']=len(rows)
    if history:
        last=history[-1];result['rest_hours']=(start-utc(last['actual_end'])).total_seconds()/3600
        previous=last.get('venue')
        if venue and previous:
            # Consecutive matches do not establish consecutive tournaments or
            # departure after doubles. Use travel.InterTournamentTravelExtractor
            # for exposures supported by edition and participation evidence.
            if venue.get('surface') and previous.get('surface'):
                result['surface_changed']=venue['surface']!=previous['surface']
    return result


def weather_features(observation,start_at,decision_at,indoor):
    """Forecasts must have existed at decision time; reanalysis is never a forecast."""
    if indoor is True:return {'status':'indoor','temperature_c':None,'humidity_pct':None,'wind_kmh':None}
    if indoor is not False:return {'status':'unknown_roof_or_indoor','temperature_c':None,'humidity_pct':None,'wind_kmh':None}
    if observation.get('kind')!='forecast' or not source_valid(observation,decision_at):
        return {'status':'missing_prior_forecast'}
    try:
        if utc(observation['issued_at'])>utc(decision_at):return {'status':'future_forecast_rejected'}
        rows=observation['hourly'];target=utc(start_at)
        nearest=min(rows,key=lambda r:abs((utc(r['time'])-target).total_seconds()))
        if abs((utc(nearest['time'])-target).total_seconds())>3600:return {'status':'forecast_outside_window'}
        values={k:float(nearest[k]) for k in ('temperature_c','humidity_pct','wind_kmh')}
        if not all(math.isfinite(v) for v in values.values()) or not 0<=values['humidity_pct']<=100 or values['wind_kmh']<0:
            return {'status':'invalid_weather_values'}
        return {'status':'prior_forecast','source_time':nearest['time'],**values}
    except (KeyError,TypeError,ValueError):return {'status':'invalid_forecast'}
