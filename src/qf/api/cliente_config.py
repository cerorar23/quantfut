"""Configuración común para web y app: `GET /cliente/v1/config` (provisional, `contrato: 0`).

Ningún cliente lo consume todavía; la forma definitiva se decide en la Fase 2. Lo que queda asentado aquí es la
lista blanca de campos (PUBLICAS / PRIVADAS por tabla) y la maquinaria de `ETag`.

Garantías: (1) el cuerpo se construye campo a campo, nunca volcando una fila; (2) el modelo de respuesta rechaza
campos que no declara (`extra='forbid'`); (3) `tests/test_cliente_config.py` compara las columnas reales de cada tabla
con PUBLICAS/PRIVADAS y falla si aparece una sin clasificar. La respuesta no mira `Authorization` ni cookies.
"""
from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Any, Literal

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, ConfigDict

from ..comercial import acceso_reglas, mobile_updates
from . import idiomas, mobile, web_config

router = APIRouter(tags=['cliente'])

# Todo lo que no esté en PUBLICAS es privado. La prueba de clasificación exige que cada columna real esté en una de las dos.
PUBLICAS: dict[str, frozenset[str]] = {
    'web_site_settings': frozenset({
        'brand_name', 'legal_name', 'hero_badge', 'support_email', 'disclaimer_text', 'maintenance_banner',
        'social_x', 'social_instagram', 'social_telegram', 'social_facebook', 'social_youtube', 'social_tiktok',
        'lang_selector_enabled', 'lang_states'}),
    'mobile_update_settings': frozenset({
        'app_version_android', 'app_version_ios', 'min_build_android', 'min_build_ios', 'force_update_app',
        'app_link', 'ios_app_link'}),
    'mobile_features': frozenset({'section', 'enabled', 'message'}),
    'acceso_reglas': frozenset({'prob_min', 'prob_max', 'free_fraction'}),
    'cliente_ajustes': frozenset({'dias_agenda'}),
}
PRIVADAS: dict[str, frozenset[str]] = {
    'web_site_settings': frozenset({
        'apimart_base_url', 'apimart_model', 'apimart_key_enc', 'translation_target_langs', 'default_robots',
        'content_signal', 'public_cache_seconds', 'indexnow_enabled', 'updated_by', 'updated_at', 'id'}),
    'mobile_update_settings': frozenset({'id', 'updated_at'}),
    'mobile_features': frozenset({'updated_at'}),
    'acceso_reglas': frozenset({'regla_id', 'stream', 'vigente_desde', 'creado_por', 'creado_en', 'nota'}),
    'cliente_ajustes': frozenset({'id', 'updated_by', 'updated_at'}),
}

_LANG_RE = re.compile(r'^[a-z]{2}$')


class Cliente(str, Enum):
    web = 'web'
    app = 'app'


class _Modelo(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Red(_Modelo):
    key: str
    label: str
    url: str


class General(_Modelo):
    brand_name: str
    legal_name: str
    hero_badge: str
    support_email: str
    disclaimer_text: str
    maintenance_banner: str
    social: list[Red]


class Idiomas(_Modelo):
    selector: bool
    estados: dict[str, str]


class Acceso(_Modelo):
    probability_min: float
    probability_max: float
    high_probability_free_fraction: float
    ladder_free_count: int
    dias_agenda: int


class Versiones(_Modelo):
    app_version_android: str
    app_version_ios: str
    min_build_android: int
    min_build_ios: int
    force_update_app: bool
    app_link: str
    ios_app_link: str


class Seccion(_Modelo):
    enabled: bool
    message: str


class App(_Modelo):
    versiones: Versiones
    secciones: dict[str, Seccion]


class SeccionWeb(_Modelo):
    path: str
    title: str
    description: str
    h1: str
    migas: str
    paragraphs: list[str]


class Web(_Modelo):
    ui: dict[str, str]
    sections: dict[str, SeccionWeb]


class Respuesta(_Modelo):
    contrato: Literal[0] = 0
    cliente: Cliente
    lang: str
    general: General
    idiomas: Idiomas
    acceso: Acceso
    app: App | None = None
    web: Web | None = None


def _idioma(lang: str) -> str:
    return lang if lang in web_config.IDIOMAS_VALIDOS and idiomas.estado(lang) != 'off' else 'es'


def _secciones_web(lang: str) -> dict[str, SeccionWeb]:
    out: dict[str, SeccionWeb] = {}
    for slug, paths in web_config.SPA_LOCALIZED_PATHS.items():
        ov = web_config.get_spa_section_override(slug, lang)
        if not ov and lang == 'es':
            base = web_config.catalog_defaults().get((f'spa:{slug}', 'es'))
            if base:
                ov = {**base, 'parrafos': tuple(web_config._html_to_paragraphs(base.get('body_html') or ''))}
        if ov:
            out[slug] = SeccionWeb(path=paths[lang], title=ov['title'], description=ov['description'],
                                   h1=ov['h1'], migas=ov['migas'], paragraphs=list(ov['parrafos']))
    return out


def componer(cliente: Cliente, lang: str) -> Respuesta:
    cfg = web_config.get_settings()
    regla = acceso_reglas.vigente()   # la de hoy (UTC)
    resp = Respuesta(
        cliente=cliente, lang=lang,
        general=General(
            brand_name=cfg['brand_name'], legal_name=cfg['legal_name'], hero_badge=cfg['hero_badge'],
            support_email=cfg['support_email'], disclaimer_text=cfg['disclaimer_text'],
            maintenance_banner=cfg['maintenance_banner'],
            social=[Red(key=s['key'], label=s['label'], url=s['url']) for s in web_config.social_links(cfg)]),
        idiomas=Idiomas(selector=bool(cfg['lang_selector_enabled']),
                        estados={c: idiomas.estado(c) for c in web_config.IDIOMAS_VALIDOS}),
        acceso=Acceso(probability_min=regla.prob_min, probability_max=regla.prob_max,
                      high_probability_free_fraction=regla.free_fraction, ladder_free_count=1,
                      dias_agenda=acceso_reglas.dias_agenda()))
    if cliente is Cliente.app:
        v = mobile_updates.configuration()
        resp.app = App(
            versiones=Versiones(**{k: v[k] for k in Versiones.model_fields}),
            secciones={k: Seccion(enabled=bool(f['enabled']), message=f['message'])
                       for k, f in mobile.features().items()})
    else:
        resp.web = Web(ui=web_config.get_ui_dict(lang), sections=_secciones_web(lang))
    return resp


def _etag(cuerpo: dict[str, Any]) -> str:
    canonico = json.dumps(cuerpo, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return 'W/"' + hashlib.sha256(canonico.encode('utf-8')).hexdigest() + '"'


def _coincide(cabecera: str | None, etag: str) -> bool:
    if not cabecera:
        return False
    if cabecera.strip() == '*':
        return True
    debil = lambda t: t.strip().removeprefix('W/')   # noqa: E731
    return any(debil(t) == debil(etag) for t in cabecera.split(','))


@router.get('/cliente/v1/config', response_model=Respuesta, response_model_exclude_none=True)
def cliente_config(request: Request, cliente: Cliente = Query(...),
                   lang: str = Query('es', pattern=_LANG_RE.pattern)):
    lang = _idioma(lang)
    cuerpo = componer(cliente, lang).model_dump(mode='json', exclude_none=True)
    etag = _etag(cuerpo)
    if cliente is Cliente.web:
        cache = f"public, max-age={int(web_config.get_settings()['public_cache_seconds'])}"
    else:
        cache = 'no-cache'
    cabeceras = {'ETag': etag, 'Cache-Control': cache}
    if _coincide(request.headers.get('if-none-match'), etag):
        return Response(status_code=304, headers=cabeceras)
    return Response(json.dumps(cuerpo, ensure_ascii=False, separators=(',', ':')).encode('utf-8'),
                    media_type='application/json', headers=cabeceras)
