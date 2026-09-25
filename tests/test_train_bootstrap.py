from datetime import datetime, timedelta, timezone

from qf.model import train
from qf.model.promotion import MARKET_MAX_AGE_DAYS, evaluate_base_promotion

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def _db(monkeypatch, active: bool, last_market):
    def fake(sql, params=None):
        if "is_active" in sql:
            return {"x": 1} if active else None
        return {"last_match": NOW, "last_market": last_market}
    monkeypatch.setattr(train, "query_one", fake)


def test_no_entrena_si_ya_hay_modelo_activo(monkeypatch):
    _db(monkeypatch, active=True, last_market=NOW)
    assert train.bootstrap_status()[0] is False


def test_no_entrena_sin_ningun_cierre_sharp(monkeypatch):
    _db(monkeypatch, active=False, last_market=None)
    assert train.bootstrap_status()[0] is False


def test_no_entrena_con_mercado_que_la_puerta_rechazaria(monkeypatch):
    _db(monkeypatch, active=False,
        last_market=NOW - timedelta(days=MARKET_MAX_AGE_DAYS + 1))
    assert train.bootstrap_status()[0] is False


def test_entrena_en_el_limite_que_la_puerta_acepta(monkeypatch):
    _db(monkeypatch, active=False,
        last_market=NOW - timedelta(days=MARKET_MAX_AGE_DAYS))
    assert train.bootstrap_status()[0] is True


def test_el_limite_coincide_con_el_de_la_puerta():
    comparison = {"models": {"dixon_coles": {"rps": 0.19}, "elo": {"rps": 0.20},
                             "market": {"rps": 0.18}}}
    ok = evaluate_base_promotion({}, None, {**comparison,
                                            "market_age_days": MARKET_MAX_AGE_DAYS})
    stale = evaluate_base_promotion({}, None, {**comparison,
                                               "market_age_days": MARKET_MAX_AGE_DAYS + 1})
    assert ok.checks["market_data_fresh"] is True
    assert stale.checks["market_data_fresh"] is False
