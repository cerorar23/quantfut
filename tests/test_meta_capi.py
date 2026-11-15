"""Construcción y envío de eventos CAPI con transporte simulado (sin BD ni red)."""
import json
from datetime import datetime, timezone

import httpx

from qf.comercial import meta_capi


ACC = {"account_id": 7, "email": "a@b.co", "display_name": "Ana Pérez"}
IDENT = {"anon_id": "XZ1", "platform": "android", "madid": None,
         "advertiser_tracking_enabled": True,
         "extinfo": ["a2", "com.saptain.quantfut", "1.0.0", "1", "14", "", "", "", "", "", "",
                     "", "", "", "", ""],
         "client_ip": "203.0.113.9", "user_agent": "QuantFut/1.0"}


def _row(**kw):
    base = {"event_id": "pur:GPA.1", "account_id": 7, "event_name": "Purchase",
            "event_time": datetime(2026, 10, 15, 12, tzinfo=timezone.utc),
            "custom_data": {"currency": "COP", "value": 54900.0, "content_ids": ["plus_1m"]}}
    return {**base, **kw}


def test_evento_de_app_lleva_action_source_app_data_y_event_id():
    ev = meta_capi.build_event(_row(), ACC, IDENT)
    assert ev["action_source"] == "app"
    assert ev["event_id"] == "pur:GPA.1"
    assert ev["event_name"] == "Purchase"
    assert ev["event_time"] == 1792065600          # 2026-10-15 12:00 UTC
    assert ev["app_data"] == {"advertiser_tracking_enabled": 1, "application_tracking_enabled": 1,
                              "extinfo": IDENT["extinfo"]}
    assert ev["user_data"]["anon_id"] == "XZ1"
    assert ev["custom_data"]["currency"] == "COP"


def test_sin_dispositivo_no_se_inventa_extinfo_y_sale_como_other():
    # Auditoría 15-nov: 6 de 6 registros de la app salieron con un extinfo genérico (Android 14, 1.0.0).
    ev = meta_capi.build_event(_row(), ACC, None)
    assert ev["action_source"] == "other" and "app_data" not in ev
    assert set(ev["user_data"]) == {"external_id", "em", "fn", "ln"}


def test_pais_de_la_compra_va_a_user_data_y_no_a_custom_data():
    ev = meta_capi.build_event(_row(custom_data={"value": 1.0, "_country": "CO"}), ACC, IDENT)
    assert "country" in ev["user_data"] and "_country" not in ev["custom_data"]


def test_moneda_sin_decimales_conserva_el_valor_exacto():
    # 54.900 pesos colombianos = 54_900_000_000 micros: Meta debe recibir 54900.0, no 549.0.
    assert meta_capi.value(54_900_000_000) == 54900.0
    assert meta_capi.value(4_990_000) == 4.99


def test_envio_en_lote_con_token_y_codigo_de_prueba(monkeypatch):
    monkeypatch.setenv("META_DATASET_ID", "123")
    monkeypatch.setenv("META_CAPI_TOKEN", "secreto")
    monkeypatch.setenv("META_TEST_EVENT_CODE", "TEST42")
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"events_received": 1})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    received = meta_capi._post([meta_capi.build_event(_row(), ACC, IDENT)], client)
    assert received == 1
    assert seen["url"] == "https://graph.facebook.com/v24.0/123/events"
    assert seen["body"]["access_token"] == "secreto"
    assert seen["body"]["test_event_code"] == "TEST42"
    assert seen["body"]["data"][0]["event_id"] == "pur:GPA.1"


def test_cobro_web_sin_navegador_va_como_system_generated():
    # Meta exige client_user_agent en `website`: una renovación llega por webhook, sin navegador.
    row = _row(action_source="website", web_context={"client_ip": "203.0.113.9"})
    ev = meta_capi.build_event(row, ACC, None)
    assert ev["action_source"] == "system_generated"
    assert "client_user_agent" not in ev["user_data"] and "app_data" not in ev
    con_navegador = _row(action_source="website", web_context={"user_agent": "Mozilla/5.0"})
    assert meta_capi.build_event(con_navegador, ACC, None)["action_source"] == "website"


def test_error_de_meta_conserva_el_motivo_sin_el_token(monkeypatch):
    monkeypatch.setenv("META_DATASET_ID", "123")
    monkeypatch.setenv("META_CAPI_TOKEN", "secreto")
    monkeypatch.delenv("META_TEST_EVENT_CODE", raising=False)
    body = {"error": {"message": "Invalid parameter", "error_subcode": 2804050}}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(400, json=body)))
    try:
        meta_capi._post([meta_capi.build_event(_row(), ACC, IDENT)], client)
    except meta_capi.MetaError as exc:
        assert exc.status == 400 and "2804050" in str(exc) and "secreto" not in str(exc)
    else:
        raise AssertionError("debía fallar")
