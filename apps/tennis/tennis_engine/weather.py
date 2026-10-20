"""Archived Open-Meteo forecasts with real availability, never invented issue time.

Sources: https://open-meteo.com/en/docs. UTC unix timestamps and explicit SI
units avoid timezone/unit ambiguity. A returned grid cell is not a court sensor.
"""
from datetime import datetime,timezone
import hashlib,json,math
from pathlib import Path
from typing import Any,Callable
from uuid import uuid4
import requests
from .context import haversine_km
from .operations import now,utc

ENDPOINT='https://api.open-meteo.com/v1/forecast'
VARIABLES=('temperature_2m','relative_humidity_2m','wind_speed_10m','precipitation_probability')
UNITS={'time':'unixtime','temperature_2m':'°C','relative_humidity_2m':'%','wind_speed_10m':'km/h','precipitation_probability':'%'}

def _point(venue:dict[str,Any])->tuple[float,float]:
    if not venue.get('venue_id'):raise ValueError('Venue identity required')
    if any(isinstance(venue.get(k),bool) or not isinstance(venue.get(k),(int,float)) for k in ('lat','lon')):raise ValueError('Verified coordinate pair required')
    point=(venue['lat'],venue['lon']);haversine_km(point,point);return point

def capture_forecast(root:Path,venues:list[dict[str,Any]],*,transport:Callable=requests.get,clock:Callable=now)->Path:
    """One bounded public request for 1..16 venues; no retry or paid credentials."""
    if not 1<=len(venues)<=16 or len({v['venue_id'] for v in venues})!=len(venues):raise ValueError('One to sixteen unique venues required')
    points=[_point(v) for v in venues]
    params=dict(latitude=','.join(str(p[0]) for p in points),longitude=','.join(str(p[1]) for p in points),
        hourly=','.join(VARIABLES),temperature_unit='celsius',wind_speed_unit='kmh',precipitation_unit='mm',
        timeformat='unixtime',timezone='UTC',forecast_days=3)
    folder=Path(root)/uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    receipt=dict(schema='tennis-open-meteo-forecast-v1',url=ENDPOINT,params=params,
        requested_at=clock(),venues=[dict(venue_id=v['venue_id'],lat=p[0],lon=p[1]) for v,p in zip(venues,points)],
        kind='forecast',provider_issue_time=None,availability_basis='local_response_receipt',
        attribution='Open-Meteo.com, CC BY 4.0; noncommercial public API')
    rp=folder/'receipt.json'
    try:
        response=transport(ENDPOINT,params=params,timeout=(10,35),allow_redirects=False)
    except Exception as exc:
        receipt.update(received_at=clock(),error_type=type(exc).__name__)
        with rp.open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
        raise RuntimeError('Weather request failed; receipt retained') from None
    raw=response.content;source=folder/'response.json'
    with source.open('xb') as f:f.write(raw)
    receipt.update(http_status=response.status_code,received_at=clock(),source_path=str(source.resolve()),sha256=hashlib.sha256(raw).hexdigest())
    with rp.open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
    load_forecasts(rp)
    return rp

def load_forecasts(receipt_path:Path)->list[dict[str,Any]]:
    """Derive all values again from original bytes, validating units and arrays."""
    receipt=json.loads(Path(receipt_path).read_text(encoding='utf8'))
    if receipt.get('schema')!='tennis-open-meteo-forecast-v1' or receipt.get('kind')!='forecast' or receipt.get('url')!=ENDPOINT or receipt.get('http_status')!=200:raise ValueError('Successful forecast receipt required')
    if utc(receipt['requested_at'])>utc(receipt['received_at']):raise ValueError('Invalid receipt chronology')
    raw=Path(receipt['source_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise ValueError('Weather source changed')
    data=json.loads(raw);data=data if isinstance(data,list) else [data]
    if len(data)!=len(receipt['venues']):raise ValueError('Weather response/venue count mismatch')
    result=[]
    for venue,body in zip(receipt['venues'],data,strict=True):
        point=_point(venue);grid=(body['latitude'],body['longitude'])
        distance=haversine_km(point,grid)
        if distance>50:raise ValueError('Returned grid too far from requested venue')
        if body.get('utc_offset_seconds')!=0 or any(body['hourly_units'].get(k)!=v for k,v in UNITS.items()):raise ValueError('Unexpected weather time/unit')
        arrays=body['hourly'];times=arrays['time']
        if not times or any(type(t) is not int for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Unique ascending unix timestamps required')
        if any(len(arrays[k])!=len(times) for k in VARIABLES):raise ValueError('Weather arrays differ in length')
        rows=[]
        for i,t in enumerate(times):
            values={k:arrays[k][i] for k in VARIABLES}
            if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)) for v in values.values()):raise ValueError('Invalid weather number')
            for key in ('relative_humidity_2m','precipitation_probability'):
                if values[key] is not None and not 0<=values[key]<=100:raise ValueError('Invalid weather percentage')
            if values['wind_speed_10m'] is not None and values['wind_speed_10m']<0:raise ValueError('Negative wind speed')
            rows.append(dict(time=datetime.fromtimestamp(t,timezone.utc).isoformat(),temperature_c=values['temperature_2m'],humidity_pct=values['relative_humidity_2m'],wind_kmh=values['wind_speed_10m'],precipitation_probability_pct=values['precipitation_probability']))
        result.append(dict(venue=venue,grid_cell_distance_km=distance,grid_cell=list(grid),available_at=receipt['received_at'],
            provider_issue_time=None,receipt_path=str(Path(receipt_path).resolve()),receipt_sha256=hashlib.sha256(Path(receipt_path).read_bytes()).hexdigest(),source_sha256=receipt['sha256'],hourly=rows))
    return result

def forecast_features(receipt_path:Path,venue:dict[str,Any],start_at:str,decision_at:str,roof_state:str,*,max_age_seconds:int=21600)->dict[str,Any]:
    """Candidates only. Roof state must be verified separately by the fixture adapter."""
    decision=utc(decision_at);target=utc(start_at)
    if decision>=target:raise ValueError('Weather decision must precede target')
    if type(max_age_seconds) is not int or not 0<max_age_seconds<=86400:raise ValueError('Explicit forecast freshness limit required')
    if roof_state not in ('open','closed','unknown'):raise ValueError('Explicit roof state required')
    empty=dict(temperature_c=None,humidity_pct=None,wind_kmh=None,precipitation_probability_pct=None)
    if roof_state=='closed':return dict(status='closed_roof_external_weather_not_applied',**empty)
    if roof_state=='unknown':return dict(status='unknown_roof_no_exposure_assumed',**empty)
    point=_point(venue);rows=load_forecasts(receipt_path);obs=next((r for r in rows if r['venue']['venue_id']==venue['venue_id']),None)
    if obs is None or tuple(obs['venue'][k] for k in ('lat','lon'))!=point:raise ValueError('Forecast does not bind this venue coordinate pair')
    available=utc(obs['available_at'])
    if not available<decision:return dict(status='forecast_not_available_before_decision',**empty)
    if (decision-available).total_seconds()>max_age_seconds:return dict(status='stale_forecast',**empty)
    row=min(obs['hourly'],key=lambda r:abs((utc(r['time'])-target).total_seconds()))
    if abs((utc(row['time'])-target).total_seconds())>1800:return dict(status='forecast_outside_half_hour_window',**empty)
    if any(row[k] is None for k in empty):return dict(status='forecast_variable_missing',**empty)
    return dict(status='available_prior_forecast',**row,available_at=obs['available_at'],provider_issue_time=None,
        receipt_path=obs['receipt_path'],receipt_sha256=obs['receipt_sha256'],source_sha256=obs['source_sha256'],grid_cell_distance_km=obs['grid_cell_distance_km'],
        court_sensor=False,physiological_penalty_applied=False)
