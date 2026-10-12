import contextlib

from qf.comercial import cuentas, cuentas_mantenimiento as m


class FakeConn:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))

        class R:
            rowcount = 1
        return R()


def run(monkeypatch):
    fake = FakeConn()
    monkeypatch.setattr(m, "conn", contextlib.contextmanager(lambda: (yield fake)))
    return m.clean(), fake.calls


def test_borra_tokens_retirados_antes_que_sus_sesiones(monkeypatch):
    _, calls = run(monkeypatch)
    tablas = [c[0].split("FROM ")[1].split()[0] for c in calls]
    assert tablas == ["session_retired_tokens", "session_retired_tokens", "sessions", "email_tokens"]


def test_plazos_y_ttl_del_refresh_enlazado(monkeypatch):
    res, calls = run(monkeypatch)
    params = calls[0][1]
    assert params == {"s": 30, "e": 7, "r": cuentas.REFRESH_TTL_DAYS}
    assert res == {"sessions": 1, "retired_tokens": 2, "email_tokens": 1}


def test_nunca_toca_cuentas_ni_auditoria(monkeypatch):
    _, calls = run(monkeypatch)
    for sql, _ in calls:
        assert sql.startswith("DELETE FROM")
        for prohibida in ("accounts", "admin_audit", "subscriptions", "reward_", "firebase_"):
            assert prohibida not in sql
