"""Política pública de versiones; solo el panel autenticado puede modificarla."""
import re
from urllib.parse import urlsplit

from psycopg.errors import UndefinedTable

from ..db import query_one

DEFAULTS = dict(app_version_android='', app_version_ios='', min_build_android=0,
                min_build_ios=0, force_update_app=False, app_link='', ios_app_link='')


def configuration():
    try:
        row = query_one('SELECT app_version_android, app_version_ios, min_build_android, '
                        'min_build_ios, force_update_app, app_link, ios_app_link '
                        'FROM mobile_update_settings WHERE id=1')
    except UndefinedTable:
        return dict(DEFAULTS)
    return dict(DEFAULTS) | (row or {})


def validate(values):
    for platform, link_key, host in [('android', 'app_link', 'play.google.com'),
                                      ('ios', 'ios_app_link', 'apps.apple.com')]:
        version = values[f'app_version_{platform}']
        link = values[link_key]
        minimum = values[f'min_build_{platform}']
        match = re.fullmatch(r'\d+\.\d+\.\d+\+([1-9]\d*)', version) if version else None
        if version and not match:
            raise ValueError(f'Versión {platform}: usa el formato 1.0.0+71.')
        if minimum < 0 or minimum > 2147483647:
            raise ValueError('El build mínimo debe ser un entero positivo o cero.')
        if minimum and (not match or minimum > int(match[1])):
            raise ValueError(f'El mínimo de {platform} no puede superar la última versión.')
        parsed = urlsplit(link)
        if link and (parsed.scheme != 'https' or parsed.netloc != host or parsed.path in ('', '/')):
            raise ValueError(f'El enlace de {platform} debe ser una ficha HTTPS de {host}.')
        if version and not link:
            raise ValueError(f'Falta el enlace de la tienda para {platform}.')
