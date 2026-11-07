"""Comprobaciones de salud y diagnóstico operativo del motor de tenis (plan §H.4, Sprint 6)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tenis.alertas import enviar_alerta
from tenis.modelo.hiperparametros import huella
from tenis.sellado import CadenaRotaError, verificar_cadena

log = logging.getLogger(__name__)


def comprobar_cadena(db: Any) -> dict[str, Any]:
    """Valida la integridad de la cadena criptográfica de sellos."""
    try:
        res = verificar_cadena(db)
        return {"estado": "ok", "total_sellos": res["total_sellos"], "ultimo_hash": res["ultimo_hash"]}
    except CadenaRotaError as e:
        enviar_alerta("cadena_rota", f"Cadena criptográfica rota: {e}")
        return {"estado": "error", "error": str(e)}
    except Exception as e:
        return {"estado": "error_desconocido", "error": str(e)}


def comprobar_frescura_capturas(db: Any, max_horas: int = 36) -> dict[str, Any]:
    """Comprueba que haya recibos recientes (umbral 36 horas antes de alertar, plan §L)."""
    ahora_utc = datetime.now(timezone.utc)
    row = db.execute("SELECT max(recibido_en) FROM recibo").fetchone()
    if not row or row[0] is None:
        return {"estado": "sin_datos", "mensaje": "No hay recibos registrados en la base"}

    ultimo_recibo = row[0]
    if not ultimo_recibo.tzinfo:
        ultimo_recibo = ultimo_recibo.replace(tzinfo=timezone.utc)

    delta = ahora_utc - ultimo_recibo
    horas_antiguedad = delta.total_seconds() / 3600.0

    if horas_antiguedad > max_horas:
        enviar_alerta(
            "colector_parado",
            f"Último recibo tiene {horas_antiguedad:.1f} horas de antigüedad (> {max_horas} h)",
        )
        return {
            "estado": "alerta",
            "horas_antiguedad": round(horas_antiguedad, 1),
            "ultimo_recibo": ultimo_recibo.isoformat(),
        }

    return {
        "estado": "ok",
        "horas_antiguedad": round(horas_antiguedad, 1),
        "ultimo_recibo": ultimo_recibo.isoformat(),
    }


def comprobar_tasa_sin_resolver(db: Any) -> dict[str, Any]:
    """Verifica que la tasa de entidades sin resolver en el cuadro principal sea <= 2% (G-identidad)."""
    tot_partidos = db.execute(
        "SELECT count(*) FROM partido WHERE fuente IN ('sofascore', 'tml')"
    ).fetchone()[0]
    tot_sin_resolver = db.execute("SELECT count(*) FROM sin_resolver").fetchone()[0]

    tasa = (tot_sin_resolver / tot_partidos) if tot_partidos > 0 else 0.0
    tasa_pct = round(tasa * 100, 2)

    if tasa > 0.02:
        enviar_alerta(
            "sin_resolver_alto",
            f"Tasa de sin_resolver {tasa_pct}% supera el umbral del 2% (total {tot_sin_resolver})",
        )
        return {"estado": "alerta", "tasa_pct": tasa_pct, "sin_resolver": tot_sin_resolver}

    return {"estado": "ok", "tasa_pct": tasa_pct, "sin_resolver": tot_sin_resolver}


def comprobar_artefacto_activo(db: Any, ruta_artefacto: Path | None = None) -> dict[str, Any]:
    """Comprueba que el artefacto activo en la base coincida con el fichero local."""
    row = db.execute(
        "SELECT a.sha256, a.tipo, a.version_modelo, aa.imagen "
        "FROM artefacto_activo aa JOIN artefacto a ON aa.sha256 = a.sha256 "
        "ORDER BY aa.activo_id DESC LIMIT 1"
    ).fetchone()

    if not row:
        return {"estado": "sin_artefacto_activo"}

    sha_db, tipo, version_modelo, imagen = row

    if ruta_artefacto and ruta_artefacto.exists():
        import json
        datos = json.loads(ruta_artefacto.read_text(encoding="utf-8"))
        # Si trae sha256_contenido, se calcula sobre el resto
        if "sha256_contenido" in datos:
            copia = dict(datos)
            copia.pop("sha256_contenido")
            sha_calc = huella(copia)
        else:
            sha_calc = huella(datos)

        if sha_calc != sha_db:
            enviar_alerta("contrato_roto", f"Huella local {sha_calc} no coincide con artefacto activo {sha_db}")
            return {"estado": "descuadre_huella", "db": sha_db, "local": sha_calc}

    return {
        "estado": "ok",
        "sha256": sha_db,
        "tipo": tipo,
        "version_modelo": version_modelo,
        "imagen": imagen,
    }


def informe_salud_completo(db: Any, ruta_artefacto: Path | None = None) -> dict[str, Any]:
    """Genera un reporte integral de salud de la plataforma de tenis."""
    return {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "cadena": comprobar_cadena(db),
        "frescura": comprobar_frescura_capturas(db),
        "identidad": comprobar_tasa_sin_resolver(db),
        "artefacto": comprobar_artefacto_activo(db, ruta_artefacto),
    }
