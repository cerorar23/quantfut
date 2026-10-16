"""Read-only Play API verification; never print credentials or purchase tokens."""
import os
from qf.comercial.tiendas.google_play import _session, BASE, package

response = _session().get(f'{BASE}/{package()}/subscriptions/quantfut_plus', timeout=25)
print('PLAY_SUBSCRIPTION_HTTP', response.status_code)
if response.ok:
    data = response.json()
    print('PRODUCT', data.get('productId'))
    for plan in data.get('basePlans', []):
        print('PLAN', plan.get('basePlanId'), plan.get('state'))
else:
    print('ERROR_STATUS', response.json().get('error', {}).get('status'))
print('PURCHASES_ENABLED', os.getenv('STORE_PURCHASES_ENABLED', '0'))
response.raise_for_status()
