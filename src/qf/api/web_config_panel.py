"""Rutas administrativas `/control/configuracion*` para gestionar la web y APIMart."""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import apimart, panel, web_config
from .console import require_console

router = APIRouter(prefix="/control", include_in_schema=False)


def _redirect_with(path: str, *, msg: str = "", err: str = "", extra: dict[str, str] | None = None) -> RedirectResponse:
    params: dict[str, str] = {}
    if msg:
        params["msg"] = msg
    if err:
        params["err"] = err[:240]
    if extra:
        params.update(extra)
    qs = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(f"{path}{qs}", status_code=303)


@router.get("/configuracion", response_class=HTMLResponse)
def web_config_home(request: Request, user: str = Depends(require_console)):
    overview = web_config.build_catalog_overview(seed_if_needed=True)
    grouped: list[dict] = []
    seen: dict[str, list[dict]] = {}
    for row in overview["rows"]:
        seen.setdefault(row["kind_label"], []).append(row)
    for label, items in seen.items():
        grouped.append({"label": label, "items": items})

    return panel._render(
        request,
        "web_config.html",
        user,
        "web_config",
        cfg=overview["settings"],
        db_ok=overview["db_ok"],
        key_origin=overview["key_origin"],
        groups=grouped,
        social_specs=overview["social_specs"],
        modelos_sugeridos=apimart.MODELOS_SUGERIDOS,
        robots_options=web_config.ROBOTS_OPTIONS,
        estados_idioma=web_config.ESTADOS_IDIOMA,
        idiomas_f7=web_config.IDIOMAS_BLOQUEADOS_F7,
        err=request.query_params.get("err", ""),
        ok_detalle=request.query_params.get("detalle", ""),
    )


@router.post("/configuracion/idiomas")
def web_config_idiomas_post(
    request: Request,
    en_state: str = Form("off"),
    pt_state: str = Form("off"),
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    try:
        web_config.save_language_states(en_state, pt_state, panel._actor(request, user))
    except Exception as exc:
        return _redirect_with("/control/configuracion", err=str(exc))
    return _redirect_with("/control/configuracion", msg="web_idiomas_guardado")


@router.post("/configuracion/general")
async def web_config_general_post(request: Request, user: str = Depends(require_console)):
    form = await request.form()
    panel._check_post(request, user, str(form.get("csrf") or ""))
    payload = {
        "brand_name": form.get("brand_name", ""),
        "legal_name": form.get("legal_name", ""),
        "hero_badge": form.get("hero_badge", ""),
        "support_email": form.get("support_email", ""),
        "disclaimer_text": form.get("disclaimer_text", ""),
        "maintenance_banner": form.get("maintenance_banner", ""),
        "social_x": form.get("social_x", ""),
        "social_instagram": form.get("social_instagram", ""),
        "social_telegram": form.get("social_telegram", ""),
        "social_facebook": form.get("social_facebook", ""),
        "social_youtube": form.get("social_youtube", ""),
        "social_tiktok": form.get("social_tiktok", ""),
        "default_robots": form.get("default_robots", "index,follow"),
        "content_signal": form.get("content_signal", ""),
        "public_cache_seconds": form.get("public_cache_seconds", "300"),
        "indexnow_enabled": form.get("indexnow_enabled") == "1",
        "lang_selector_enabled": form.get("lang_selector_enabled") == "1",
    }
    try:
        web_config.save_general_settings(payload, panel._actor(request, user))
    except Exception as exc:
        return _redirect_with("/control/configuracion", err=str(exc))
    return _redirect_with("/control/configuracion", msg="web_guardado")


@router.post("/configuracion/apimart")
async def web_config_apimart_post(request: Request, user: str = Depends(require_console)):
    form = await request.form()
    panel._check_post(request, user, str(form.get("csrf") or ""))
    targets = [str(v) for v in form.getlist("target_langs")]
    try:
        web_config.save_apimart_settings(
            base_url=str(form.get("apimart_base_url") or ""),
            model=str(form.get("apimart_model") or ""),
            new_api_key=str(form.get("apimart_api_key") or ""),
            clear_api_key=form.get("clear_api_key") == "1",
            target_langs=targets,
            actor=panel._actor(request, user),
        )
    except Exception as exc:
        return _redirect_with("/control/configuracion", err=str(exc))
    return _redirect_with("/control/configuracion", msg="web_apimart_guardado")


@router.post("/configuracion/apimart/probar")
def web_config_apimart_probar(
    request: Request,
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    rt = web_config.get_apimart_runtime_config()
    try:
        probe = apimart.test_connection(
            api_key=rt["api_key"],
            base_url=rt["base_url"],
            model=rt["model"],
        )
    except Exception as exc:
        return _redirect_with("/control/configuracion", err=str(exc))
    return _redirect_with(
        "/control/configuracion",
        msg="web_apimart_ok",
        extra={"detalle": f"Modelo {probe['model']} respondió en {probe['latency_ms']} ms."},
    )


@router.post("/configuracion/traducir-lote")
def web_config_traducir_lote(
    request: Request,
    mode: str = Form("pending"),
    target_lang: str = Form(""),
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    res = web_config.translate_pending_batch(
        target_lang=target_lang if target_lang in web_config.IDIOMAS_SECUNDARIOS else None,
        force_all=(mode == "all"),
        actor=panel._actor(request, user),
    )
    if res["errors"]:
        return _redirect_with(
            "/control/configuracion",
            err=f"Traducidas: {res['done']}, omitidas: {res['skipped']}. Errores: {'; '.join(res['errors'][:3])}",
        )
    return _redirect_with(
        "/control/configuracion",
        msg="web_traduccion_lote",
        extra={"detalle": f"{res['done']} traducciones completadas ({res['skipped']} ya vigentes)."},
    )


@router.get("/configuracion/pagina/{page_key}", response_class=HTMLResponse)
def web_config_page_edit(
    page_key: str,
    request: Request,
    lang: str = "es",
    user: str = Depends(require_console),
):
    if lang not in web_config.IDIOMAS_VALIDOS:
        lang = "es"
    order_map = {item["page_key"]: item for item in web_config.catalog_order()}
    meta = order_map.get(page_key)
    if meta is None:
        raise HTTPException(404)

    overview = web_config.build_catalog_overview(seed_if_needed=True)
    current = web_config.get_page(page_key, lang, use_cache=False)
    default_item = web_config.catalog_defaults().get((page_key, lang))
    es_ref = web_config.get_page_or_default(page_key, "es", use_cache=False) or {}
    routes = web_config.catalog_route_paths().get(page_key, {})

    form_data = current or default_item or {
        "page_key": page_key,
        "lang": lang,
        "kind": meta["kind"],
        "route_path": routes.get(lang, "/"),
        "title": "",
        "description": "",
        "h1": "",
        "migas": "",
        "body_html": "",
        "revision_date": "",
        "is_auto_translated": False,
        "reviewed": True,
        "source_sha256": "",
        "translation_model": "",
        "updated_by": "",
        "updated_at": None,
    }
    is_stale = bool(
        lang != "es"
        and current
        and current.get("is_auto_translated")
        and current.get("source_sha256")
        and es_ref
        and current.get("source_sha256") != web_config.content_sha256(es_ref)
    )
    return panel._render(
        request,
        "web_config_page.html",
        user,
        "web_config",
        meta=meta,
        lang=lang,
        langs=web_config.IDIOMAS_VALIDOS,
        routes=routes,
        page=form_data,
        es_ref=es_ref,
        has_db_row=current is not None,
        has_default=default_item is not None,
        is_stale=is_stale,
        key_origin=overview["key_origin"],
        err=request.query_params.get("err", ""),
        ok_detalle=request.query_params.get("detalle", ""),
    )


@router.post("/configuracion/pagina/{page_key}/guardar")
def web_config_page_save(
    page_key: str,
    request: Request,
    lang: str = Form("es"),
    title: str = Form(""),
    description: str = Form(""),
    h1: str = Form(""),
    migas: str = Form(""),
    body_html: str = Form(""),
    revision_date: str = Form(""),
    reviewed: str | None = Form(None),
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    try:
        web_config.save_page(
            page_key=page_key,
            lang=lang,
            title=title,
            description=description,
            h1=h1,
            migas=migas,
            body_html=body_html,
            revision_date=revision_date,
            reviewed=(reviewed == "1") or (lang == "es"),
            actor=panel._actor(request, user),
        )
    except Exception as exc:
        return _redirect_with(
            f"/control/configuracion/pagina/{page_key}",
            err=str(exc),
            extra={"lang": lang},
        )
    return _redirect_with(
        f"/control/configuracion/pagina/{page_key}",
        msg="web_pagina_guardada",
        extra={"lang": lang},
    )


@router.post("/configuracion/pagina/{page_key}/traducir")
def web_config_page_translate(
    page_key: str,
    request: Request,
    target_lang: str = Form(...),
    return_to: str = Form("page"),
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    dest = "/control/configuracion" if return_to == "home" else f"/control/configuracion/pagina/{page_key}"
    try:
        res = web_config.translate_page_db(page_key, target_lang, panel._actor(request, user))
    except Exception as exc:
        extra = {} if return_to == "home" else {"lang": target_lang}
        return _redirect_with(dest, err=str(exc), extra=extra)
    extra = {"detalle": f"Traducido con {res.get('translation_model') or 'APIMart'}."}
    if return_to != "home":
        extra["lang"] = target_lang
    return _redirect_with(dest, msg="web_traduccion_ok", extra=extra)


@router.post("/configuracion/pagina/{page_key}/restaurar")
def web_config_page_restore(
    page_key: str,
    request: Request,
    lang: str = Form("es"),
    csrf: str = Form(...),
    user: str = Depends(require_console),
):
    panel._check_post(request, user, csrf)
    try:
        web_config.restore_page_default(page_key, lang, panel._actor(request, user))
    except Exception as exc:
        return _redirect_with(
            f"/control/configuracion/pagina/{page_key}",
            err=str(exc),
            extra={"lang": lang},
        )
    return _redirect_with(
        f"/control/configuracion/pagina/{page_key}",
        msg="web_pagina_restaurada",
        extra={"lang": lang},
    )
