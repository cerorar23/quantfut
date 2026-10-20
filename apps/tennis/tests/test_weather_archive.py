from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
import pytest
from tennis_engine.weather import capture_forecast,load_forecasts,forecast_features,UNITS

VENUE={'venue_id':'v','lat':48.2,'lon':16.3}
TARGET='2026-10-20T10:00:00Z';DECISION='2026-10-20T08:00:00Z'

def payload():
 return dict(latitude=48.2,longitude=16.3,utc_offset_seconds=0,hourly_units=UNITS.copy(),
  hourly=dict(time=[int(datetime.fromisoformat(TARGET.replace('Z','+00:00')).timestamp())],temperature_2m=[22.],relative_humidity_2m=[55.],wind_speed_10m=[11.],precipitation_probability=[25.]))

def capture(tmp_path,body=None,received='2026-10-20T07:00:01Z'):
 clock=iter(['2026-10-20T07:00:00Z',received]);data=payload() if body is None else body
 class Response:status_code=200;content=json.dumps(data).encode()
 return capture_forecast(tmp_path,[VENUE],transport=lambda *a,**k:Response(),clock=lambda:next(clock))

def test_real_availability_is_separate_from_unknown_provider_issue_time(tmp_path):
 p=capture(tmp_path);r=forecast_features(p,VENUE,TARGET,DECISION,'open')
 assert r['status']=='available_prior_forecast' and r['temperature_c']==22.
 assert r['provider_issue_time'] is None and not r['court_sensor'] and not r['physiological_penalty_applied']
 assert forecast_features(p,VENUE,TARGET,'2026-10-20T07:00:01Z','open')['status']=='forecast_not_available_before_decision'

@pytest.mark.parametrize('roof,expected',[('unknown','unknown_roof_no_exposure_assumed'),('closed','closed_roof_external_weather_not_applied')])
def test_unknown_or_closed_roof_does_not_assume_outdoor_exposure(tmp_path,roof,expected):
 r=forecast_features(tmp_path/'absent.json',VENUE,TARGET,DECISION,roof)
 assert r['status']==expected and r['temperature_c'] is None

@pytest.mark.parametrize('change',[lambda b:b['hourly_units'].update(wind_speed_10m='mph'),lambda b:b['hourly']['time'].append(b['hourly']['time'][0]),lambda b:b['hourly'].update(relative_humidity_2m=[101.]),lambda b:b['hourly'].update(wind_speed_10m=[-1.]),lambda b:b.update(latitude=0.),lambda b:b.update(utc_offset_seconds=3600)])
def test_units_duplicate_times_invalid_values_and_distant_grid_rejected(tmp_path,change):
 body=payload();change(body)
 with pytest.raises(ValueError):capture(tmp_path,body)
 assert list(tmp_path.glob('*/receipt.json'))

def test_missing_weather_value_remains_missing(tmp_path):
 body=payload();body['hourly']['temperature_2m']=[None];p=capture(tmp_path,body)
 assert forecast_features(p,VENUE,TARGET,DECISION,'open')['status']=='forecast_variable_missing'

def test_wrong_coordinate_and_changed_bytes_cannot_be_reused(tmp_path):
 p=capture(tmp_path)
 with pytest.raises(ValueError):forecast_features(p,{**VENUE,'lat':49.},TARGET,DECISION,'open')
 receipt=json.loads(p.read_text());Path(receipt['source_path']).write_bytes(b'{}')
 with pytest.raises(ValueError):load_forecasts(p)

def test_stale_forecast_and_post_start_decision_rejected(tmp_path):
 p=capture(tmp_path)
 assert forecast_features(p,VENUE,TARGET,DECISION,'open',max_age_seconds=60)['status']=='stale_forecast'
 with pytest.raises(ValueError):forecast_features(p,VENUE,TARGET,TARGET,'open')

def test_network_failure_is_archived_once_without_retry(tmp_path):
 calls=[]
 def fail(*a,**k):calls.append(1);raise RuntimeError('untrusted transport text')
 with pytest.raises(RuntimeError,match='receipt retained'):capture_forecast(tmp_path,[VENUE],transport=fail)
 assert len(calls)==1 and len(list(tmp_path.glob('*/receipt.json')))==1
