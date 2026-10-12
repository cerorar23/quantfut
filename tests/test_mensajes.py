"""Mensajes de la API por idioma (src/qf/api/mensajes.py).

Regla del proyecto: todo mensaje que pueda verse en la app lleva sus traducciones.
"""
import ast
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from qf.api import mensajes
from qf.api.mensajes import CATALOGO, IDIOMAS, PATRONES

RAIZ = Path(__file__).resolve().parents[1] / "src" / "qf"
ARCHIVOS = [RAIZ / "api" / "rewards.py", RAIZ / "api" / "cuentas.py", RAIZ / "api" / "firebase.py",
            RAIZ / "api" / "mobile.py", RAIZ / "api" / "main.py",
            RAIZ / "comercial" / "cuentas.py", RAIZ / "comercial" / "firebase.py"]

# Mensajes que NO ve una persona en la app (webhooks de proveedores y panel de administración).
SOLO_ADMIN = {
    "Importe inválido", "Fecha inválida", "Usuario no disponible",
    "Transacción duplicada con datos distintos", "La reversión no coincide con el crédito",
    "Proveedor no configurado", "Firma inválida", "Estado de oferta no válido",
    "Origen no autorizado", "Un crédito no puede ser negativo", "Estado inválido",
    "Transacción inválida", "Indica siete recompensas enteras entre 0 y 1000000",
    "Proveedor inválido", "Identificador público inválido", "Lista de IP no válida",
    "Faltan credenciales o la integración de este proveedor", "Evento duplicado con datos distintos",
    "Falta QF_SECRETS_KEY en el servidor: no se puede guardar la secret key cifrada",
    "Secret key no válida para este proveedor", "Sección no válida",
}


def test_cada_mensaje_tiene_las_cinco_traducciones():
    for es, tr in CATALOGO.items():
        assert len(tr) == len(IDIOMAS) - 1, es
        assert all(t.strip() for t in tr), es
        assert all(t != es for t in tr if len(es) > 30), f"sin traducir: {es}"
    for es, tr in PATRONES.items():
        assert len(tr) == len(IDIOMAS) - 1
        for t in tr:
            assert "{a}" in t and "{b}" in t, es


def test_idioma_de_accept_language():
    assert mensajes.idioma(None) == "es"
    assert mensajes.idioma("de-DE,de;q=0.9,en;q=0.8") == "de"
    assert mensajes.idioma("ja,fr;q=0.5") == "fr"
    assert mensajes.idioma("ja,zh") == "es"
    assert mensajes.idioma("EN-us") == "en"


def test_traducir_catalogo_patron_y_desconocidos():
    assert mensajes.traducir("Inicia sesión", "en") == "Sign in"
    assert mensajes.traducir("Inicia sesión", "es") == "Inicia sesión"
    assert mensajes.traducir("Inicia sesión", "ja") == "Inicia sesión"
    assert (mensajes.traducir("La contraseña debe tener entre 10 y 200 caracteres", "pt")
            == "A senha deve ter entre 10 e 200 caracteres")
    assert mensajes.traducir("Mensaje que no está en el catálogo", "de") == "Mensaje que no está en el catálogo"
    assert mensajes.traducir_detalle({"code": "x", "message": "Cuenta suspendida"}, "it") == {
        "code": "x", "message": "Account sospeso"}


def _mensajes_del_codigo():
    encontrados = {}
    for archivo in ARCHIVOS:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = getattr(nodo.func, "id", getattr(nodo.func, "attr", ""))
            if nombre not in ("HTTPException", "CuentaError"):
                continue
            candidatos = list(nodo.args[1:2]) if nombre == "HTTPException" else list(nodo.args[1:2])
            for c in candidatos:
                if isinstance(c, ast.Constant) and isinstance(c.value, str):
                    encontrados[c.value] = f"{archivo.name}:{nodo.lineno}"
                elif isinstance(c, ast.Dict):
                    for k, v in zip(c.keys, c.values):
                        if getattr(k, "value", None) == "message" and isinstance(v, ast.Constant):
                            encontrados[v.value] = f"{archivo.name}:{nodo.lineno}"
                elif isinstance(c, ast.JoinedStr):  # f-strings (p. ej. longitud de contraseña)
                    pass
    return encontrados


def test_todo_mensaje_visible_en_la_app_esta_en_el_catalogo():
    faltan = {m: donde for m, donde in _mensajes_del_codigo().items()
              if m not in CATALOGO and m not in SOLO_ADMIN}
    assert not faltan, (
        "Mensajes sin traducir (añádelos a src/qf/api/mensajes.py con sus 5 traducciones, "
        "o a SOLO_ADMIN si no los ve nadie en la app):\n"
        + "\n".join(f"  {donde}: {m}" for m, donde in faltan.items()))


def test_el_manejador_traduce_y_conserva_el_espanol_por_defecto():
    from qf.api.main import http_exception_handler
    app = FastAPI()
    app.add_exception_handler(HTTPException.__mro__[1], http_exception_handler)

    @app.get("/texto")
    def texto():
        raise HTTPException(401, "Inicia sesión para usar monedas")

    @app.get("/dict")
    def dic():
        raise HTTPException(429, {"code": "demasiados_intentos",
                                  "message": "Demasiados intentos, espera un momento"},
                            headers={"Retry-After": "5"})

    c = TestClient(app)
    assert c.get("/texto").json() == {"detail": "Inicia sesión para usar monedas"}
    r = c.get("/texto", headers={"Accept-Language": "de"})
    assert r.status_code == 401 and r.json() == {"detail": "Melde dich an, um Münzen zu nutzen"}
    r = c.get("/dict", headers={"Accept-Language": "fr-FR"})
    assert r.status_code == 429 and r.headers["retry-after"] == "5"
    assert r.json()["detail"] == {"code": "demasiados_intentos",
                                  "message": "Trop de tentatives, veuillez patienter"}
