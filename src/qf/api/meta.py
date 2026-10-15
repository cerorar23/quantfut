"""Datos del dispositivo para Conversions API (db/071). La app los manda tras iniciar
sesión y al arrancar; el servidor añade IP y user agent de la propia petición."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import cuentas as api
from .ratelimit import client_ip
from ..comercial import meta_datos
from ..db import execute

router = APIRouter(prefix="/app/v1/meta", tags=["app"], dependencies=[Depends(api.require_enabled)])
_UUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


class DispositivoIn(BaseModel):
    anon_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-:.]+$")
    platform: Literal["android", "ios"]
    madid: str | None = Field(default=None, pattern=_UUID)
    advertiser_tracking_enabled: bool
    extinfo: list[str] = Field(min_length=16, max_length=16)


def _save(**row) -> None:
    execute(
        """INSERT INTO meta_identities (account_id, anon_id, platform, madid,
               advertiser_tracking_enabled, extinfo, client_ip, user_agent)
           VALUES (%(account_id)s, %(anon_id)s, %(platform)s, %(madid)s,
                   %(advertiser_tracking_enabled)s, %(extinfo_json)s, %(client_ip)s, %(user_agent)s)
           ON CONFLICT (account_id, anon_id) DO UPDATE SET platform = EXCLUDED.platform,
               madid = EXCLUDED.madid, advertiser_tracking_enabled = EXCLUDED.advertiser_tracking_enabled,
               extinfo = EXCLUDED.extinfo, client_ip = EXCLUDED.client_ip,
               user_agent = EXCLUDED.user_agent, updated_at = now()""",
        {**row, "extinfo_json": json.dumps(row["extinfo"])})


@router.post("/dispositivo", status_code=204)
def dispositivo(body: DispositivoIn, request: Request, acc: dict = Depends(api.current_account)):
    try:
        extinfo = meta_datos.valid_extinfo(body.extinfo, body.platform)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    _save(account_id=acc["account_id"], anon_id=body.anon_id, platform=body.platform,
          madid=body.madid, advertiser_tracking_enabled=body.advertiser_tracking_enabled,
          extinfo=extinfo, client_ip=client_ip(request),
          user_agent=(request.headers.get("user-agent") or "")[:300] or None)
    return Response(status_code=204)
