"""`/control/deportes`: deportes y familias de mercados que gobiernan web y app (Fase 2, parte D).

Solo edita lo que ya existe (no hay alta de deportes: sin adaptador no pueden encenderse). Las guardas viven en
`comercial/catalogo.py`; aquí solo se capturan sus `ValueError` y se muestran. `deporte_id` y `familia_id` van en la
URL y nunca en el formulario.
"""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg import errors as pgerr

from . import apimart, console, panel, web_config
from ..comercial import catalogo

router = APIRouter(prefix="/control", include_in_schema=False)

ICONOS = ('generico', 'futbol', 'baloncesto', 'tenis', 'beisbol', 'hockey', 'rugby', 'futbol_americano',
          'voleibol', 'golf', 'mma', 'motor')
_ERRORES = (ValueError, pgerr.CheckViolation, pgerr.RaiseException)


def _error(destino: str, texto: str) -> RedirectResponse:
    query = urlencode({"m": "catalogo_error", "err": (texto or "Datos no válidos.")[:240]})
    return RedirectResponse(f"{destino}?{query}", status_code=303)


def _deporte(deporte_id: str) -> dict:
    for d in catalogo.todos():
        if d["deporte_id"] == deporte_id:
            return d
    raise HTTPException(404, "Deporte no encontrado")


def _textos(prefijo: str, form, idiomas) -> dict:
    return {lg: str(form.get(f"{prefijo}_{lg}", "")).strip() for lg in idiomas}


@router.get("/deportes", response_class=HTMLResponse)
def deportes_page(request: Request, user: str = Depends(console.require_console)):
    catalogo.invalidar_cache()
    return panel._render(request, "deportes.html", user, "deportes", deportes=catalogo.todos(),
                         err=request.query_params.get("err", ""))


@router.get("/deportes/{deporte_id}", response_class=HTMLResponse)
def deporte_editar_page(request: Request, deporte_id: str, user: str = Depends(console.require_console)):
    catalogo.invalidar_cache()
    return panel._render(request, "deportes_editar.html", user, "deportes", d=_deporte(deporte_id),
                         idiomas=catalogo.IDIOMAS_APP, idiomas_web=catalogo.IDIOMAS_WEB,
                         secciones=catalogo.SECCIONES, estados=catalogo.ESTADOS, iconos=ICONOS,
                         err=request.query_params.get("err", ""))


@router.post("/deportes/{deporte_id}")
async def deporte_guardar(request: Request, deporte_id: str, user: str = Depends(console.require_console)):
    form = await request.form()
    panel._check_post(request, user, str(form.get("csrf", "")))
    _deporte(deporte_id)
    destino = f"/control/deportes/{deporte_id}"
    datos = {"nombre": _textos("nombre", form, catalogo.IDIOMAS_APP),
             "slug": _textos("slug", form, catalogo.IDIOMAS_WEB),
             "icono": str(form.get("icono", "")), "color": str(form.get("color", "")).strip().lower(),
             "secciones": list(form.getlist("secciones")),
             "estado_web": str(form.get("estado_web", "")), "estado_app": str(form.get("estado_app", ""))}
    try:
        if datos["icono"] not in ICONOS:
            raise ValueError("Icono no válido: elige uno de la lista.")
        catalogo.guardar_deporte(deporte_id, datos, panel._actor(request, user))
    except _ERRORES as exc:
        return _error(destino, str(exc))
    return panel._back(destino, "catalogo_guardado")


@router.post("/deportes/{deporte_id}/orden")
def deporte_orden(request: Request, deporte_id: str, sentido: str = Form(""), csrf: str = Form(""),
                  user: str = Depends(console.require_console)):
    """Sube o baja un deporte intercambiando `orden` con su vecino."""
    panel._check_post(request, user, csrf)
    if sentido not in ("subir", "bajar"):
        raise HTTPException(422, "sentido debe ser subir o bajar")
    lista = catalogo.todos()
    ids = [d["deporte_id"] for d in lista]
    if deporte_id not in ids:
        raise HTTPException(404, "Deporte no encontrado")
    i = ids.index(deporte_id)
    j = i - 1 if sentido == "subir" else i + 1
    if not 0 <= j < len(lista):
        return panel._back("/control/deportes", "sin_cambios")
    a, b = lista[i], lista[j]
    actor = panel._actor(request, user)
    try:
        if a["orden"] != b["orden"]:
            catalogo.guardar_deporte(a["deporte_id"], {"orden": b["orden"]}, actor)
            catalogo.guardar_deporte(b["deporte_id"], {"orden": a["orden"]}, actor)
        else:  # empate: basta con pasar al deporte por delante o por detrás de su vecino
            catalogo.guardar_deporte(a["deporte_id"], {"orden": b["orden"] + (1 if sentido == "bajar" else -1)}, actor)
    except _ERRORES as exc:
        return _error("/control/deportes", str(exc))
    return panel._back("/control/deportes", "catalogo_guardado")


@router.post("/deportes/{deporte_id}/traducir")
def deporte_traducir(request: Request, deporte_id: str, csrf: str = Form(""),
                     user: str = Depends(console.require_console)):
    """Rellena fr/it/de del nombre a partir del español con APIMart (solo el nombre corto)."""
    panel._check_post(request, user, csrf)
    d = _deporte(deporte_id)
    destino = f"/control/deportes/{deporte_id}"
    try:
        rt = web_config.get_apimart_runtime_config()
        res = apimart._chat_completion(
            api_key=rt["api_key"], base_url=rt["base_url"], model=rt["model"], expect_json=True,
            messages=[{"role": "system", "content": "Translate a short sports category name from Spanish into "
                       "French (fr), Italian (it) and German (de). Return strictly a JSON object with keys fr, it, de."},
                      {"role": "user", "content": d["nombre"]["es"]}])
        out = apimart._extract_json_object(res["content"])
        nombre = {**d["nombre"], **{lg: str(out.get(lg) or "").strip() for lg in ("fr", "it", "de")}}
        catalogo.guardar_deporte(deporte_id, {"nombre": nombre}, panel._actor(request, user))
    except (apimart.ApimartError, *_ERRORES) as exc:
        return _error(destino, str(exc))
    return panel._back(destino, "catalogo_traducido")


@router.get("/deportes/{deporte_id}/mercados", response_class=HTMLResponse)
def mercados_page(request: Request, deporte_id: str, user: str = Depends(console.require_console)):
    catalogo.invalidar_cache()
    return panel._render(request, "deportes_mercados.html", user, "deportes", d=_deporte(deporte_id),
                         idiomas=catalogo.IDIOMAS_APP, err=request.query_params.get("err", ""))


@router.post("/deportes/{deporte_id}/mercados/{familia}")
async def mercado_guardar(request: Request, deporte_id: str, familia: str,
                          user: str = Depends(console.require_console)):
    form = await request.form()
    panel._check_post(request, user, str(form.get("csrf", "")))
    d = _deporte(deporte_id)
    if familia not in {f["familia_id"] for f in d["familias"]}:
        raise HTTPException(404, "Familia no encontrada")
    destino = f"/control/deportes/{deporte_id}/mercados"
    try:
        try:
            orden = int(str(form.get("orden", "")).strip())
        except ValueError:
            raise ValueError("El orden debe ser un entero.") from None
        catalogo.guardar_familia(deporte_id, familia, {
            "nombre": _textos("nombre", form, catalogo.IDIOMAS_APP),
            "subtitulo": _textos("subtitulo", form, catalogo.IDIOMAS_APP), "orden": orden,
            "visible_web": form.get("visible_web") == "1", "visible_app": form.get("visible_app") == "1"},
            panel._actor(request, user))
    except _ERRORES as exc:
        return _error(destino, str(exc))
    return panel._back(destino, "catalogo_guardado")
