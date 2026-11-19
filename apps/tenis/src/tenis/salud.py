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


def comprobar_calendario(db: Any, max_horas: float = 3.0) -> dict[str, Any]:
    """El colector de calendario de PropLine corre cada hora: si su último recibo tiene más de `max_horas`, está parado.

    Sin ningún recibo de PropLine (aún no se ha puesto en marcha) no se avisa."""
    row = db.execute("SELECT max(recibido_en) FROM recibo WHERE fuente = 'propline' AND recurso LIKE '%calendario%'").fetchone()
    if not row or row[0] is None:
        return {"estado": "sin_datos"}
    ultimo = row[0] if row[0].tzinfo else row[0].replace(tzinfo=timezone.utc)
    horas = (datetime.now(timezone.utc) - ultimo).total_seconds() / 3600.0
    if horas > max_horas:
        enviar_alerta("colector_parado", f"El calendario de PropLine lleva {horas:.1f} h sin recibos (> {max_horas:g} h)")
        return {"estado": "alerta", "horas_antiguedad": round(horas, 1), "ultimo_recibo": ultimo.isoformat()}
    return {"estado": "ok", "horas_antiguedad": round(horas, 1), "ultimo_recibo": ultimo.isoformat()}


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
        # Un fichero concreto o una carpeta de artefactos (la imagen lleva varios: el activo y los anteriores).
        ficheros = sorted(ruta_artefacto.glob("*.json")) if ruta_artefacto.is_dir() else [ruta_artefacto]
        huellas = []
        for f in ficheros:
            try:
                datos = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            copia = dict(datos)
            copia.pop("sha256_contenido", None)          # la huella se calcula sobre el resto
            huellas.append(huella(copia))
        if sha_db not in huellas:
            local = huellas[0] if huellas else None
            enviar_alerta("contrato_roto", f"Ningún artefacto local tiene la huella del activo {sha_db}")
            return {"estado": "descuadre_huella", "db": sha_db, "local": local}

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
        "calendario": comprobar_calendario(db),
        "identidad": comprobar_tasa_sin_resolver(db),
        "artefacto": comprobar_artefacto_activo(db, ruta_artefacto),
    }


def main(argv=None) -> int:
    """`python -m tenis.salud`: imprime el informe en JSON; código 1 si algo no está bien (los avisos ya salieron por Telegram)."""
    import argparse
    import json
    import os
    import re
    import sys

    import psycopg
    from tenis import alertas

    ap = argparse.ArgumentParser(description="Salud del motor de tenis v2")
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--artefactos", type=Path, default=None, help="carpeta (o fichero) de artefactos a comparar con el activo")
    a = ap.parse_args(argv)
    if not a.dsn or not re.fullmatch(r"[a-z_][a-z0-9_]*", a.esquema):
        print("falta --dsn o PG_DSN, o esquema no válido", file=sys.stderr)
        return 1
    alertas.cargar_estado()
    with psycopg.connect(a.dsn, autocommit=True) as db:
        db.execute(f"SET search_path TO {a.esquema}, public")
        informe = informe_salud_completo(db, a.artefactos)
    print(json.dumps(informe, ensure_ascii=False, default=str))
    bien = all(v.get("estado") in ("ok", "sin_datos") for k, v in informe.items() if isinstance(v, dict))
    return 0 if bien else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
