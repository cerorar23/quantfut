"""Configure the existing server compose without rebuilding any image."""
from pathlib import Path
import shutil
import yaml

root = Path('/home/qf/quantfut')
compose = root / 'docker-compose.yml'
backup = root / 'deployments/play-credentials-20261016'
backup.mkdir(parents=True, exist_ok=True)
saved = backup / 'docker-compose.before.yml'
if not saved.exists():
    shutil.copy2(compose, saved)
config = yaml.safe_load(compose.read_text())
api = config['services']['api']
assert api['image'] == 'quantfut-api-admob:20261015b', 'Unexpected API image'
mount = '/home/qf/.config/quantfut/google-play.json:/run/secrets/quantfut-play.json:ro'
if mount not in api.setdefault('volumes', []):
    api['volumes'].append(mount)
api.setdefault('environment', {}).update({
    'PLAY_SERVICE_ACCOUNT_FILE': '/run/secrets/quantfut-play.json',
    'PLAY_PACKAGE_NAME': 'com.saptain.quantfut',
    'PLAY_RTDN_AUDIENCE': 'https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn',
    'PLAY_RTDN_SERVICE_ACCOUNT': 'quantfut-play@pronosticos-deportivos-85ffa.iam.gserviceaccount.com',
    'STORE_PURCHASES_ENABLED': '0',
})
compose.write_text(yaml.safe_dump(config, sort_keys=False))
print('Play configured; purchases disabled; original API image preserved.')
