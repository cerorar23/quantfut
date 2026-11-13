"""`/control/pantallas`: orden, visibilidad y avisos de las pantallas `deporte` y `partido` (Fase 4, db/113).

Las reglas de validación viven en `comercial/pantallas.py`; aquí solo se arma el formulario, se llama allí y se
muestra su mensaje tal cual. Publicar y volver atrás crean versiones nuevas (la tabla es de solo inserción).
"""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg import errors as pgerr

from . import console, panel
from ..comercial import catalogo, pantallas

router = APIRouter(prefix="/control", include_in_schema=False)
_ERRORES = (ValueError, pgerr.CheckViolation, pgerr.RaiseException)
FILAS_VACIAS = 3          # filas en blanco al final del editor para añadir bloques
MAX_FILAS = 60            # tope de filas que se leen de un formulario


def _clave(origen) -> tuple[str, str, str]:
    pantalla, deporte, cliente = (str(origen.get(k, "")) for k in ("pantalla", "deporte", "cliente"))
    try:
        pantallas.validar_clave(pantalla, deporte, cliente)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    return pantalla, deporte, cliente


def _destino(clave: tuple[str, str, str]) -> str:
    return "/control/pantallas/editar?" + urlencode(dict(zip(("pantalla", "deporte", "cliente"), clave)))


def _volver_al_editor(clave, codigo: str) -> RedirectResponse:
    return RedirectResponse(f"{_destino(clave)}&{urlencode({'m': codigo})}", status_code=303)


def _entero(texto: str):
    texto = texto.strip()
    if not texto:
        return None
    return int(texto) if texto.isdigit() else texto    # un valor raro llega a `validar`, que lo rechaza


def _bloques_de_formulario(form) -> list[dict]:
    """Del formulario a la lista cruda de bloques; no valida (eso es de `pantallas.validar`)."""
    try:
        n = min(int(form.get("n", "0")), MAX_FILAS)
    except ValueError:
        n = 0
    filas = []
    for i in range(n):
        p = f"b{i}_"
        tipo = str(form.get(p + "tipo", "")).strip()
        if not tipo or form.get(p + "quitar"):
            continue
        seccion = str(form.get(p + "seccion", "")).strip()
        bid = str(form.get(p + "id", "")).strip() or (
            seccion if tipo == "seccion" else "vip" if tipo == "vip" else f"aviso_{i + 1}")
        bloque = {"id": bid, "tipo": tipo, "visible": bool(form.get(p + "visible")),
                  "params": {}, "build_min_app": _entero(str(form.get(p + "build", "")))}
        if tipo == "seccion":
            bloque["seccion"] = seccion
        elif tipo == "aviso":
            bloque["params"] = {"texto": {lg: str(form.get(f"{p}t_{lg}", "")) for lg in pantallas.IDIOMAS_APP},
                                "tono": str(form.get(p + "tono", ""))}
            enlace = str(form.get(p + "enlace", "")).strip()
            if enlace:
                bloque["params"]["enlace"] = enlace
        try:
            orden = float(str(form.get(p + "orden", "")).replace(",", "."))
        except ValueError:
            orden = float(i)
        filas.append((orden, i, bloque))
    return [b for _, _, b in sorted(filas, key=lambda f: (f[0], f[1]))]


def _filas_para_editor(bloques: list[dict]) -> list[dict]:
    """Un bloque por fila, con todos los campos que el formulario necesita (también los de un aviso)."""
    filas = []
    for b in bloques:
        params = b.get("params") or {}
        texto = params.get("texto") if isinstance(params.get("texto"), dict) else {}
        filas.append({"id": b.get("id", ""), "tipo": b.get("tipo", ""), "seccion": b.get("seccion") or "",
                      "visible": bool(b.get("visible", True)),
                      "build": "" if b.get("build_min_app") is None else b.get("build_min_app"),
                      "tono": params.get("tono", "info"), "enlace": params.get("enlace", ""),
                      "texto": {lg: texto.get(lg, "") for lg in pantallas.IDIOMAS_APP}})
    return filas


def _bloques_iniciales(clave) -> tuple[list[dict], str]:
    pantalla, deporte, cliente = clave
    guardado = pantallas.borrador(pantalla, deporte, cliente)
    if guardado:
        return guardado["bloques"], "borrador"
    versiones = pantallas.historial(pantalla, deporte, cliente)
    if versiones:
        return versiones[0]["bloques"], "publicada"
    return [{"id": s, "tipo": "seccion", "seccion": s, "visible": True, "params": {}, "build_min_app": None}
            for s in pantallas.PANTALLAS[pantalla]], "nueva"


def _editor(request: Request, user: str, clave, bloques: list[dict], origen: str, err: str = "",
            ok: str = "", status: int = 200) -> HTMLResponse:
    pantalla, deporte, cliente = clave
    resp = panel._render(
        request, "pantallas_editar.html", user, "pantallas", clave=clave, destino_clave=_destino(clave),
        filas=_filas_para_editor(bloques), vacias=FILAS_VACIAS, origen=origen, err=err, ok=ok,
        secciones=pantallas.PANTALLAS[pantalla], tipos=pantallas.TIPOS, tonos=pantallas.TONOS,
        idiomas=pantallas.IDIOMAS_APP, versiones=pantallas.historial(pantalla, deporte, cliente),
        max_bloques=pantallas.MAX_BLOQUES)
    resp.status_code = status
    return resp


@router.get("/pantallas", response_class=HTMLResponse)
def pantallas_lista(request: Request, user: str = Depends(console.require_console)):
    pantallas.invalidar_cache()
    deportes = [pantallas.TODOS] + [d["deporte_id"] for d in catalogo.todos()]
    return panel._render(request, "pantallas.html", user, "pantallas", claves=pantallas.claves(),
                         pantallas_cerradas=list(pantallas.PANTALLAS), deportes=deportes,
                         clientes=pantallas.CLIENTES)


@router.get("/pantallas/editar", response_class=HTMLResponse)
def pantallas_editar(request: Request, user: str = Depends(console.require_console)):
    clave = _clave(request.query_params)
    bloques, origen = _bloques_iniciales(clave)
    return _editor(request, user, clave, bloques, origen)


async def _formulario(request: Request, user: str):
    form = await request.form()
    panel._check_post(request, user, str(form.get("csrf", "")))
    return form, _clave(form)


@router.post("/pantallas/validar")
async def pantallas_validar(request: Request, user: str = Depends(console.require_console)):
    form, clave = await _formulario(request, user)
    bloques = _bloques_de_formulario(form)
    try:
        limpios = pantallas.validar(clave[0], bloques)
    except _ERRORES as exc:
        return _editor(request, user, clave, bloques, "formulario", err=str(exc), status=422)
    return _editor(request, user, clave, limpios, "formulario",
                   ok=f"Válido: {len(limpios)} bloques. Aún no está guardado ni publicado.")


@router.post("/pantallas/guardar")
async def pantallas_guardar(request: Request, user: str = Depends(console.require_console)):
    form, clave = await _formulario(request, user)
    bloques = _bloques_de_formulario(form)
    try:
        pantallas.guardar_borrador(*clave, bloques, panel._actor(request, user))
    except _ERRORES as exc:
        return _editor(request, user, clave, bloques, "formulario", err=str(exc), status=422)
    return _volver_al_editor(clave, "pantallas_guardada")


@router.post("/pantallas/publicar")
async def pantallas_publicar(request: Request, user: str = Depends(console.require_console)):
    form, clave = await _formulario(request, user)
    bloques = _bloques_de_formulario(form)
    nota = str(form.get("nota", ""))
    actor = panel._actor(request, user)
    try:
        if not nota.strip():
            raise ValueError("La nota es obligatoria para publicar.")
        pantallas.guardar_borrador(*clave, bloques, actor)
        pantallas.publicar(*clave, nota, actor)
    except _ERRORES as exc:
        return _editor(request, user, clave, bloques, "formulario", err=str(exc), status=422)
    return _volver_al_editor(clave, "pantallas_publicada")


@router.post("/pantallas/volver")
async def pantallas_volver(request: Request, user: str = Depends(console.require_console)):
    form, clave = await _formulario(request, user)
    try:
        pantallas.volver_a(*clave, int(str(form.get("version", ""))), str(form.get("nota", "")),
                           panel._actor(request, user))
    except _ERRORES as exc:
        bloques, origen = _bloques_iniciales(clave)
        return _editor(request, user, clave, bloques, origen, err=str(exc), status=422)
    return _volver_al_editor(clave, "pantallas_vuelta")
