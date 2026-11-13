"""Configuración común para web y app: `GET /cliente/v1/config` (`contrato: 1`, Fase 2 parte B).

Dentro de un contrato solo se añaden campos; quitar o cambiar uno exige `contrato: 2` (hoy `?contrato=2` da 422).
`pantallas` (Fase 4, `comercial/pantallas.py`) solo sale si hay algo publicado; `?build=N` quita los bloques con
`build_min_app` mayor y, al cambiar el cuerpo, cambia el `ETag` (que es el hash del cuerpo).
`deportes` viene de `comercial/catalogo.py` (`deportes_para`), que ya filtra `off`, familias ocultas y campos privados.
Aquí vive la lista blanca de campos (PUBLICAS / PRIVADAS por tabla) y la maquinaria de `ETag`.

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

from ..comercial import acceso_reglas, catalogo, mobile_updates, pantallas
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
    'deportes': frozenset({'deporte_id', 'orden', 'icono', 'color', 'secciones', 'nombre', 'slug', 'estado_web',
                           'estado_app'}),
    'deporte_mercados': frozenset({'deporte_id', 'familia_id', 'orden', 'nombre', 'subtitulo', 'visible_web',
                                   'visible_app'}),
    'pantalla_publicaciones': frozenset({'pantalla', 'deporte', 'cliente', 'version', 'bloques', 'publicado_en'}),
    'pantalla_borradores': frozenset(),   # el borrador entero es privado
}
PRIVADAS: dict[str, frozenset[str]] = {
    'web_site_settings': frozenset({
        'apimart_base_url', 'apimart_model', 'apimart_key_enc', 'translation_target_langs', 'default_robots',
        'content_signal', 'public_cache_seconds', 'indexnow_enabled', 'updated_by', 'updated_at', 'id'}),
    'mobile_update_settings': frozenset({'id', 'updated_at'}),
    'mobile_features': frozenset({'updated_at'}),
    'acceso_reglas': frozenset({'regla_id', 'stream', 'vigente_desde', 'creado_por', 'creado_en', 'nota'}),
    'cliente_ajustes': frozenset({'id', 'updated_by', 'updated_at'}),
    'deportes': frozenset({'adaptador', 'updated_by', 'updated_at'}),
    'deporte_mercados': frozenset({'updated_by', 'updated_at'}),
    'pantalla_publicaciones': frozenset({'publicado_por', 'nota'}),
    'pantalla_borradores': frozenset({'pantalla', 'deporte', 'cliente', 'bloques', 'updated_by', 'updated_at'}),
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


class Familia(_Modelo):
    id: str
    orden: int
    nombre: dict[str, str]
    subtitulo: dict[str, str]


class Deporte(_Modelo):
    id: str
    orden: int
    estado: Literal['preview', 'on']
    nombre: dict[str, str]
    slug: dict[str, str]
    icono: str
    color: str
    secciones: list[str]
    familias: list[Familia]


class BloquePantalla(_Modelo):
    id: str
    tipo: Literal['seccion', 'aviso', 'vip']
    seccion: str | None = None
    visible: bool
    params: dict[str, Any]
    build_min_app: int | None = None


class Respuesta(_Modelo):
    contrato: Literal[1] = 1
    cliente: Cliente
    lang: str
    general: General
    idiomas: Idiomas
    acceso: Acceso
    deportes: list[Deporte]
    app: App | None = None
    web: Web | None = None
    # {pantalla: {deporte|'*': [bloque]}}; ausente mientras no haya nada publicado (la respuesta es la de siempre).
    pantallas: dict[str, dict[str, list[BloquePantalla]]] | None = None


def _idioma(lang: str, cliente: Cliente) -> str:
    if cliente is Cliente.app:
        return lang if lang in catalogo.IDIOMAS_APP else 'es'
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


def _pantallas(cliente: Cliente, lang: str, build: int | None) -> dict[str, dict[str, list[BloquePantalla]]] | None:
    idiomas_cliente = pantallas.IDIOMAS_APP if cliente is Cliente.app else pantallas.IDIOMAS_WEB
    salida: dict[str, dict[str, list[BloquePantalla]]] = {}
    for pantalla, por_deporte in pantallas.para_entrega(cliente.value, build).items():
        for deporte, bloques in por_deporte.items():
            lista = []
            for b in bloques:
                params = b.get('params') or {}
                if b['tipo'] == 'aviso':   # la web solo usa es, en y pt
                    params = {**params, 'texto': {lg: params['texto'][lg] for lg in idiomas_cliente}}
                lista.append(BloquePantalla(id=b['id'], tipo=b['tipo'], seccion=b.get('seccion'),
                                            visible=b['visible'], params=params,
                                            build_min_app=b.get('build_min_app')))
            salida.setdefault(pantalla, {})[deporte] = lista
    return salida or None


def componer(cliente: Cliente, lang: str, build: int | None = None) -> Respuesta:
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
                      dias_agenda=acceso_reglas.dias_agenda()),
        deportes=[Deporte(**d) for d in catalogo.deportes_para(cliente.value)],
        pantallas=_pantallas(cliente, lang, build))
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
                   lang: str = Query('es', pattern=_LANG_RE.pattern),
                   contrato: int = Query(1, ge=1, le=1), build: int | None = Query(None, ge=0)):
    lang = _idioma(lang, cliente)
    cuerpo = componer(cliente, lang, build).model_dump(mode='json', exclude_none=True)
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
