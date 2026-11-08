"""Consentimiento de la medición publicitaria web: régimen por país, puerta única de la cola de Meta
y propagación de la decisión hasta el webhook de compra. Sin base ni red (la parte con Postgres está en
test_whop.py, al final)."""
import pytest

from qf.api import cuentas as accounts_api
from qf.comercial import meta_capi, meta_consent, whop


# --- régimen y decisión ------------------------------------------------------------------------------

@pytest.mark.parametrize("pais", ["ES", "FR", "DE", "IT", "PT", "GB", "CH", "NO", "es", " fr "])
def test_europa_exige_aceptar_antes_de_medir(pais):
    assert meta_consent.regimen(pais) == "opt-in"


@pytest.mark.parametrize("pais", ["MX", "CO", "AR", "CL", "PE", "US", "BR", "EC"])
def test_resto_del_mundo_mantiene_la_medicion_activa_salvo_rechazo(pais):
    assert meta_consent.regimen(pais) == "opt-out"


@pytest.mark.parametrize("pais", [None, "", "XX", "T1"])
def test_sin_pais_se_trata_como_europa(pais):
    # No se puede afirmar que la visita no sea europea: se elige el régimen más estricto.
    assert meta_consent.regimen(pais) == "opt-in"


def test_paises_extra_por_configuracion(monkeypatch):
    assert meta_consent.regimen("BR") == "opt-out"
    monkeypatch.setenv("META_OPTIN_EXTRA", "br, ca")
    assert meta_consent.regimen("BR") == "opt-in" and meta_consent.regimen("CA") == "opt-in"


def test_matriz_de_decision():
    ok = meta_consent.ads_consent
    # opt-in: solo «si» mide
    assert ok(None, country="ES") is False
    assert ok("si", country="ES") is True
    assert ok("no", country="ES") is False
    # opt-out: mide salvo «no»
    assert ok(None, country="MX") is True
    assert ok("si", country="MX") is True
    assert ok("no", country="MX") is False
    # basura en la cookie no cuenta como aceptar
    assert ok("quizas", country="ES") is False
    assert ok("quizas", country="MX") is True


@pytest.mark.parametrize("pais, cookie", [("MX", None), ("MX", "si"), ("ES", "si")])
def test_senal_de_privacidad_del_navegador_gana_siempre(pais, cookie):
    assert meta_consent.ads_consent(cookie, country=pais, gpc="1") is False
    assert meta_consent.ads_consent(cookie, country=pais, dnt="1") is False
    assert meta_consent.ads_consent(cookie, country=pais, gpc="0", dnt="0") is (pais == "MX" or cookie == "si")


# --- petición de FastAPI ----------------------------------------------------------------------------

def _request(headers: dict, cookies: str | None = None):
    from starlette.requests import Request
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    if cookies:
        raw.append((b"cookie", cookies.encode()))
    return Request({"type": "http", "headers": raw, "client": ("203.0.113.9", 4000), "method": "POST", "path": "/"})


WEB = {"x-qf-client": "web", "user-agent": "UA/1.0", "referer": "https://pronosticosdeportivos.pro/"}


def test_contexto_web_sin_consentimiento_no_lleva_datos_del_navegador():
    req = _request({**WEB, "cf-ipcountry": "ES"}, "_fbp=fb.1.1.2; _fbc=fb.1.1.AbC")
    assert accounts_api.web_context(req) == {"ads_consent": False}


def test_contexto_web_con_rechazo_explicito_en_latam():
    req = _request({**WEB, "cf-ipcountry": "MX"}, "qf_ads=no; _fbp=fb.1.1.2")
    assert accounts_api.web_context(req) == {"ads_consent": False}


def test_contexto_web_con_consentimiento_conserva_lo_de_siempre_y_lo_marca():
    req = _request({**WEB, "cf-ipcountry": "ES"}, "qf_ads=si; _fbp=fb.1.1.2")
    ctx = accounts_api.web_context(req)
    assert ctx["ads_consent"] is True and ctx["fbp"] == "fb.1.1.2" and ctx["user_agent"] == "UA/1.0"
    ctx = accounts_api.web_context(_request({**WEB, "cf-ipcountry": "MX"}, "_fbp=fb.1.1.2"))
    assert ctx["ads_consent"] is True and ctx["fbp"] == "fb.1.1.2"


def test_la_app_nunca_pasa_por_el_consentimiento_web():
    assert accounts_api.web_context(_request({"user-agent": "app", "cf-ipcountry": "ES"})) is None


def test_gpc_en_la_peticion_corta_la_medicion():
    req = _request({**WEB, "cf-ipcountry": "MX", "sec-gpc": "1"})
    assert accounts_api.web_context(req) == {"ads_consent": False}


# --- puerta única de la cola -------------------------------------------------------------------------

class _Fila:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Conexion:
    """Base simulada: `firebase_preferences` sin fila (medición permitida) y un INSERT que sí inserta."""

    def __init__(self):
        self.sql = []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        return _Fila({"event_id": "e1"} if "INSERT INTO meta_events" in sql else None)

    @property
    def inserts(self):
        return [s for s in self.sql if "INSERT INTO meta_events" in s]


def test_enqueue_descarta_el_evento_web_sin_consentimiento(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    c = _Conexion()
    assert meta_capi.enqueue(c, 7, "CompleteRegistration", "reg:7",
                             **meta_capi.web_kwargs({"ads_consent": False})) is False
    assert c.inserts == []


def test_enqueue_encola_con_consentimiento_y_sin_marca(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    for ctx in ({"ads_consent": True, "fbp": "fb.1.1.2"}, {"fbp": "fb.1.1.2"}):   # la 2.ª: filas anteriores
        c = _Conexion()
        assert meta_capi.enqueue(c, 7, "CompleteRegistration", "reg:7", **meta_capi.web_kwargs(ctx)) is True
        assert len(c.inserts) == 1
    c = _Conexion()          # evento de app: no tiene contexto web ni consentimiento web que consultar
    assert meta_capi.enqueue(c, 7, "Purchase", "pur:1") is True


# --- compra: el webhook respeta la decisión del checkout ---------------------------------------------

class _ConexionCompra(_Conexion):
    def __init__(self, ultimo=None):
        super().__init__()
        self.ultimo = ultimo

    def execute(self, sql, params=()):
        if "FROM whop_checkouts" in sql:
            self.sql.append(sql)
            return _Fila(self.ultimo)
        return super().execute(sql, params)


DATOS_PAGO = {"id": "pay_1", "currency": "usd", "total": {"amount": "14.99"}, "ip_address": "198.51.100.4"}


def _compra(c, checkout, renovacion=False):
    whop._enqueue_meta(c, 7, "plus_1m", DATOS_PAGO, checkout, 1499, "USD", renovacion)


def test_purchase_y_subscribe_no_salen_si_el_checkout_rechazo_la_medicion(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    c = _ConexionCompra()
    _compra(c, {"event_id": "purchase:ch_1", "ads_consent": False, "fbp": None})
    assert c.inserts == []


def test_purchase_y_subscribe_salen_si_el_checkout_acepto_o_es_anterior(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    for checkout in ({"event_id": "purchase:ch_1", "ads_consent": True, "fbp": "fb.1.1.2"},
                     {"event_id": "purchase:ch_1", "fbp": "fb.1.1.2"}):
        c = _ConexionCompra()
        _compra(c, checkout)
        assert len(c.inserts) == 2


def test_renovacion_sin_checkout_hereda_la_decision_del_ultimo_checkout(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    c = _ConexionCompra(ultimo={"ads_consent": False})
    _compra(c, None, renovacion=True)
    assert c.inserts == []
    c = _ConexionCompra(ultimo={"ads_consent": True})
    _compra(c, None, renovacion=True)
    assert len(c.inserts) == 1                 # una renovación solo manda Purchase, no Subscribe
    c = _ConexionCompra(ultimo=None)           # cuenta sin checkouts guardados: comportamiento previo
    _compra(c, None, renovacion=True)
    assert len(c.inserts) == 1
