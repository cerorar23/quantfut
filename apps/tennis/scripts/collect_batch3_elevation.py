from pathlib import Path
from datetime import datetime,timezone
import requests,json,hashlib
root=Path('data/tennis/historical_geography_batch3_20261018');folder=root/'originals/elevation'
folder.mkdir(exist_ok=True);rp=folder/'receipt.json'
reg=json.loads((root/'registry_pre_elevation.json').read_text())
ids=[r['venue_id'] for r in reg['geography_review']];sites={v['venue_id']:v for v in reg['venues']}
assert all(sites[k]['lat'] is not None and sites[k]['altitude_m'] is None for k in ids)
if not rp.exists():
    params={key:','.join(str(sites[k][field]) for k in ids) for key,field in [('latitude','lat'),('longitude','lon')]}
    started=datetime.now(timezone.utc).isoformat()
    r=requests.get('https://api.open-meteo.com/v1/elevation',params=params,timeout=40)
    f=folder/'response.bin';f.write_bytes(r.content)
    receipt=dict(source_id='geo3_elevation',url=r.url,requested_at=started,received_at=datetime.now(timezone.utc).isoformat(),
        http_status=r.status_code,source_path=str(f.resolve()),sha256=hashlib.sha256(r.content).hexdigest(),
        venue_ids=ids,venue_coordinates={k:[sites[k]['lat'],sites[k]['lon']] for k in ids},
        dataset='Copernicus DEM GLO-90 via Open-Meteo; terrain at representative point, not measured court altitude',
        usage='noncommercial research',attribution='Open-Meteo; Copernicus')
    rp.write_text(json.dumps(receipt,indent=2));r.raise_for_status()
receipt=json.loads(rp.read_text());print(json.dumps(dict(status=receipt['http_status'],venue_ids=receipt['venue_ids'],
    elevation=json.loads(Path(receipt['source_path']).read_bytes())['elevation'])))
