from contextlib import contextmanager

import pytest
from fastapi import HTTPException, Response
from psycopg.errors import UndefinedTable
from starlette.requests import Request

from qf.api import mobile
from qf.comercial import mobile_updates as updates


def policy(**changes):
    return dict(updates.DEFAULTS) | dict(app_version_android='1.0.0+71',
        app_link='https://play.google.com/store/apps/details?id=pro.quantfut') | changes


@pytest.mark.parametrize('changes', [
    {'app_version_android': '1.0.0'}, {'min_build_android': 72},
    {'min_build_android': -1}, {'app_link': ''},
    {'app_link': 'https://evil.example/app'},
    {'app_link': 'https://play.google.com@evil.example/app'},
    {'app_link': 'http://play.google.com/store/apps/details?id=test'},
    {'app_version_ios': '1.0.0+81', 'ios_app_link': 'https://play.google.com/app'},
])
def test_invalid_policy(changes):
    with pytest.raises(ValueError):
        updates.validate(policy(**changes))


def test_valid_and_unconfigured_policy():
    updates.validate(dict(updates.DEFAULTS))
    updates.validate(policy(min_build_android=65))


def test_missing_migration_disables_updates(monkeypatch):
    def missing(*args):
        raise UndefinedTable()
    monkeypatch.setattr(updates, 'query_one', missing)
    assert updates.configuration() == updates.DEFAULTS


def test_public_configuration_and_no_cache(monkeypatch):
    monkeypatch.setattr(mobile, 'features', lambda: {})
    monkeypatch.setattr(updates, 'configuration', lambda: policy(min_build_android=65))
    response = Response()
    result = mobile.mobile_config(response)
    assert result['min_build_android'] == 65
    assert result['app_version_android'] == '1.0.0+71'
    assert response.headers['cache-control'] == 'no-store'


def test_save_is_csrf_protected_and_audited(monkeypatch):
    request = Request({'type': 'http', 'headers': [], 'query_string': b''})
    calls, checks, audits = [], [], []

    class Connection:
        def execute(self, sql, params=None):
            calls.append((sql, params))

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(mobile, 'conn', connection)
    monkeypatch.setattr(mobile.panel, '_actor', lambda *_: 'operador')
    monkeypatch.setattr(mobile.panel, '_check_post', lambda *args: checks.append(args))
    monkeypatch.setattr(mobile, 'audit', lambda *args, **kwargs: audits.append(kwargs['detail']))
    values = policy(min_build_android=65)
    response = mobile.updates_save(request, csrf='token', user='operador',
                                  **(values | {'force_update_app': '1'}))
    assert checks[0][2] == 'token'
    assert response.status_code == 303
    assert len(calls) == 2
    assert audits[0]['force_update_app'] is True
    assert audits[0]['min_build_android'] == 65
    calls.clear()
    with pytest.raises(HTTPException) as exc:
        mobile.updates_save(request, csrf='token', user='operador',
                            **(values | {'force_update_app': '1', 'min_build_android': 99}))
    assert exc.value.status_code == 422
    assert not calls
