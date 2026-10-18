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


def test_sin_dispositivo_conocido_se_manda_extinfo_minimo_con_version_y_so():
    ev = meta_capi.build_event(_row(), ACC, None)
    assert ev["app_data"]["advertiser_tracking_enabled"] == 0
    assert len(ev["app_data"]["extinfo"]) == 16 and ev["app_data"]["extinfo"][0] == "a2"


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


def test_extinfo_de_reserva_lleva_version_del_so_que_meta_acepta():
    # Meta devuelve 400 (2804043) si la versión del SO va vacía: se vio en producción el 18-oct.
    from qf.comercial import meta_datos
    for platform in ("android", "ios"):
        ext = meta_capi._minimal_extinfo(platform)
        assert ext[1] == "com.saptain.quantfut" and ext[2] and ext[4]
        assert meta_datos.valid_extinfo(ext, platform) == ext
    ev = meta_capi.build_event(_row(), ACC, None)
    assert ev["app_data"]["extinfo"][4]
