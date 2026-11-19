"""Credenciales de pasarelas de pago guardadas desde /control (spec 2026-11-16).

Dos modos por proveedor: `live` (producción) y `sandbox` (pruebas). Las claves se cifran con
`cifrado.py`; el contexto AAD liga cada valor a su proveedor, modo y campo. En `live` las variables de
entorno de siempre siguen valiendo como respaldo, así que nada cambia hasta que alguien guarde claves.

Regla de seguridad: el sandbox NUNCA es global. Solo las cuentas de `pasarela_cuentas_prueba` pagan en él;
con la tarjeta de prueba un visitante cualquiera obtendría acceso Plus gratis.
"""
from __future__ import annotations

import logging
import os

from ..db import conn
from . import cifrado
from .auditoria import audit

log = logging.getLogger(__name__)
PROVEEDOR = "whop"
MODOS = ("live", "sandbox")
CAMPOS = ("api_key", "webhook_secret")
SANDBOX_API = "https://sandbox-api.whop.com/api/v1"


class PasarelaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def api_base(modo: str) -> str:
    if modo == "sandbox":
        return SANDBOX_API
    return os.getenv("WHOP_API_BASE", "https://api.whop.com/api/v1")


def _ctx(modo: str, campo: str) -> str:
    return f"pasarela:{PROVEEDOR}:{modo}:{campo}"


def mascara(valor: str | None) -> str:
    if not valor:
        return ""
    return "••••" + valor[-4:] if len(valor) > 8 else "••••"


def _fila(modo: str) -> dict | None:
    with conn() as c:
        return c.execute("SELECT * FROM pasarela_config WHERE proveedor = %s AND modo = %s",
                         (PROVEEDOR, modo)).fetchone()


def credenciales(modo: str) -> dict | None:
    """{'api_key','webhook_secret','account_id'} (cada uno puede faltar) o None si el modo no tiene ninguna clave."""
    if modo not in MODOS:
        return None
    try:
        fila = _fila(modo)
    except Exception:  # noqa: BLE001 — sin base (arranque, pruebas): en producción vale el entorno
        if modo != "live":
            raise
        fila = None
    claves: dict = {"account_id": (fila or {}).get("account_id") or None}
    for campo in CAMPOS:
        token = (fila or {}).get(f"{campo}_enc")
        try:
            claves[campo] = cifrado.descifrar(token, _ctx(modo, campo)) if token else None
        except cifrado.CifradoError:  # clave maestra cambiada o dato alterado: se trata como no guardado
            log.error("pasarela %s/%s: no se pudo descifrar %s", PROVEEDOR, modo, campo)
            claves[campo] = None
    if modo == "live":  # respaldo: el entorno de siempre
        claves["api_key"] = claves["api_key"] or os.getenv("WHOP_API_KEY") or None
        claves["webhook_secret"] = claves["webhook_secret"] or os.getenv("WHOP_WEBHOOK_SECRET") or None
        claves["account_id"] = claves["account_id"] or os.getenv("WHOP_ACCOUNT_ID") or None
    return claves if claves["api_key"] or claves["webhook_secret"] else None


def estado(modo: str) -> dict:
    """Lo que ve el panel: nunca el valor, solo si está y sus últimos 4 caracteres."""
    fila = _fila(modo) or {}
    out = {"modo": modo, "actualizado_por": fila.get("actualizado_por"),
           "actualizado_en": fila.get("actualizado_en"), "account_id": fila.get("account_id") or ""}
    for campo in CAMPOS:
        token = fila.get(f"{campo}_enc")
        try:
            valor = cifrado.descifrar(token, _ctx(modo, campo)) if token else None
        except cifrado.CifradoError:
            valor = None
        out[campo] = mascara(valor)
        out[f"{campo}_ok"] = bool(valor)
    return out


def guardar(modo: str, actor: str, *, api_key: str = "", webhook_secret: str = "",
            account_id: str = "") -> list[str]:
    """Guarda solo lo que se escribió (vacío = conservar). Devuelve los campos cambiados."""
    if modo not in MODOS:
        raise PasarelaError("modo_invalido", "Modo desconocido")
    nuevos = {"api_key": api_key.strip(), "webhook_secret": webhook_secret.strip()}
    if (nuevos["api_key"] or nuevos["webhook_secret"]) and not cifrado.disponible():
        raise PasarelaError("sin_clave_maestra",
                            "Falta QF_SECRETS_KEY en el servidor: no se pueden guardar claves")
    if nuevos["api_key"] and not nuevos["api_key"].startswith("apik_"):
        raise PasarelaError("clave_invalida", "La API key de Whop empieza por «apik_»")
    if nuevos["webhook_secret"] and not nuevos["webhook_secret"].startswith("ws_"):
        raise PasarelaError("secreto_invalido", "El secreto del webhook de Whop empieza por «ws_»")
    cambiados = [k for k, v in nuevos.items() if v]
    if account_id.strip():
        cambiados.append("account_id")
    if not cambiados:
        return []
    with conn() as c:
        c.execute("INSERT INTO pasarela_config (proveedor, modo) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                  (PROVEEDOR, modo))
        for campo, valor in nuevos.items():
            if valor:
                c.execute(f"UPDATE pasarela_config SET {campo}_enc = %s WHERE proveedor = %s AND modo = %s",
                          (cifrado.cifrar(valor, _ctx(modo, campo)), PROVEEDOR, modo))
        if account_id.strip():
            c.execute("UPDATE pasarela_config SET account_id = %s WHERE proveedor = %s AND modo = %s",
                      (account_id.strip(), PROVEEDOR, modo))
        c.execute("UPDATE pasarela_config SET actualizado_por = %s, actualizado_en = now() "
                  "WHERE proveedor = %s AND modo = %s", (actor, PROVEEDOR, modo))
        audit(c, actor, "pasarela.guardar", None, {"proveedor": PROVEEDOR, "modo": modo, "campos": cambiados})
    return cambiados


# --- Cuentas autorizadas para el sandbox -------------------------------------------------------------

def cuentas_prueba() -> list[dict]:
    with conn() as c:
        return c.execute("""SELECT p.account_id, a.email, p.agregada_por, p.creada_en
                            FROM pasarela_cuentas_prueba p JOIN accounts a USING (account_id)
                            ORDER BY p.creada_en""").fetchall()


def es_cuenta_prueba(c, account_id: int) -> bool:
    return c.execute("SELECT 1 FROM pasarela_cuentas_prueba WHERE account_id = %s",
                     (account_id,)).fetchone() is not None


def agregar_cuenta_prueba(email: str, actor: str) -> int:
    with conn() as c:
        fila = c.execute("SELECT account_id FROM accounts WHERE email = %s", (email.strip(),)).fetchone()
        if not fila:
            raise PasarelaError("cuenta_inexistente", "No existe una cuenta con ese correo")
        c.execute("INSERT INTO pasarela_cuentas_prueba (account_id, agregada_por) VALUES (%s, %s) "
                  "ON CONFLICT DO NOTHING", (fila["account_id"], actor))
        audit(c, actor, "pasarela.cuenta_prueba_alta", fila["account_id"], {"proveedor": PROVEEDOR})
        return fila["account_id"]


def quitar_cuenta_prueba(account_id: int, actor: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM pasarela_cuentas_prueba WHERE account_id = %s", (account_id,))
        audit(c, actor, "pasarela.cuenta_prueba_baja", account_id, {"proveedor": PROVEEDOR})


def plan_sandbox(plan_code: str, plan_id: str, actor: str) -> bool:
    plan_id = plan_id.strip() or None
    if plan_id and not plan_id.startswith("plan_"):
        raise PasarelaError("plan_invalido", "El identificador de plan de Whop empieza por «plan_»")
    with conn() as c:
        ok = c.execute("UPDATE plans SET whop_plan_id_sandbox = %s WHERE plan_code = %s RETURNING 1",
                       (plan_id, plan_code)).fetchone()
        if ok:
            audit(c, actor, "pasarela.plan_sandbox", None, {"plan_code": plan_code, "plan_id": plan_id})
        return bool(ok)
