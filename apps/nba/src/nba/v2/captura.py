"""Ejecutor de capturas a `nba_datos`: `python -m nba.v2.captura rotowire|espn|parte|nba` (lo lanza el cron del VPS).

Entorno: NBA_DB_DSN (obligatorio), NBA_CAPTURA_DIR (originales y estado, por omisión /datos),
NBA_RUN57_DIR (carpeta captures de run57, solo para espn), ZENROWS_API_KEY y NBA_ZENROWS_TOPE_DIARIO (respaldo de pago
de Rotowire), SCRAPFLY_API_KEY y NBA_SCRAPFLY_TOPE_DIARIO (final del partido en cdn.nba.com, por omisión 25 créditos al día).
"""
from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

from . import migrar
from .fuentes import espn, nba_cdn, parte_oficial, rotowire


LOTE_ESPN = 200


class FaltaVariable(Exception):
    """Variable de entorno obligatoria ausente."""


def _guardar_estado(ruta: Path, seq: int) -> None:
    """El estado avanza solo después de confirmar el lote; escritura atómica."""
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps({"seq": seq}))
    temporal.replace(ruta)


def _directo(url: str) -> tuple[int, bytes]:
    return rotowire.obtener_http(url)


def ejecutar(fuente: str, entorno: Mapping[str, str], ahora: datetime, obtener=None) -> dict:
    dsn = entorno.get("NBA_DB_DSN")
    if not dsn:
        raise FaltaVariable("NBA_DB_DSN")
    raiz = Path(entorno.get("NBA_CAPTURA_DIR", "/datos"))
    raiz.mkdir(parents=True, exist_ok=True)
    with migrar.conectar(dsn) as db:
        if fuente == "rotowire":
            if obtener is None:
                clave = entorno.get("ZENROWS_API_KEY")
                tope = float(entorno.get("NBA_ZENROWS_TOPE_DIARIO", "100"))
                pago = (lambda url: rotowire.obtener_zenrows(url, clave)) if clave else None
                obtener = rotowire.con_respaldo(_directo, pago, lambda: rotowire.gastado_hoy(db, ahora) < tope)
            resumen = rotowire.capturar(db, obtener, raiz / "originales", ahora)
        elif fuente == "espn":
            if "NBA_RUN57_DIR" not in entorno:
                raise FaltaVariable("NBA_RUN57_DIR")
            carpeta = Path(entorno["NBA_RUN57_DIR"])
            estado = raiz / "estado_espn.json"
            desde = json.loads(estado.read_text())["seq"] if estado.exists() else 0
            resumen = {"ok": True, "ultimo_seq": desde, "calendario": 0, "lesiones": 0, "omitidos": 0}
            while True:  # por lotes: cada uno se confirma y avanza el estado, así un fallo no pierde todo el avance
                ultimo, parcial = espn.cargar_ledger(db, carpeta / "receipts.sqlite", carpeta / "blobs", resumen["ultimo_seq"],
                                                     limite=LOTE_ESPN)
                db.commit()
                _guardar_estado(estado, ultimo)
                for clave, valor in parcial.items():
                    resumen[clave] += valor
                if ultimo == resumen["ultimo_seq"]:
                    break
                resumen["ultimo_seq"] = ultimo
        elif fuente == "parte":
            resumen = parte_oficial.capturar(db, obtener or parte_oficial.obtener_http, raiz / "originales", ahora)
        elif fuente == "nba":
            if obtener is None:
                clave = entorno.get("SCRAPFLY_API_KEY")
                if not clave:
                    raise FaltaVariable("SCRAPFLY_API_KEY")
                obtener = lambda url: nba_cdn.obtener_scrapfly(url, clave)
            resumen = nba_cdn.capturar(db, obtener, raiz / "originales", ahora,
                                       tope_diario=float(entorno.get("NBA_SCRAPFLY_TOPE_DIARIO", "25")))
        else:
            raise ValueError(f"fuente desconocida: {fuente}")
        db.commit()
    return resumen


def principal(argv: list[str] | None = None, entorno: Mapping[str, str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    entorno = os.environ if entorno is None else entorno
    if len(argv) != 1 or argv[0] not in ("rotowire", "espn", "parte", "nba"):
        print("uso: python -m nba.v2.captura rotowire|espn|parte|nba", file=sys.stderr)
        return 2
    try:
        resumen = ejecutar(argv[0], entorno, datetime.now(UTC))
    except FaltaVariable as e:
        print(f"falta la variable {e}", file=sys.stderr)
        return 2
    except Exception as e:  # el cron registra el fallo; no se reintenta aquí
        print(json.dumps({"fuente": argv[0], "ok": False, "error": f"{type(e).__name__}: {e}"}))
        return 1
    print(json.dumps({"fuente": argv[0], **resumen}))
    return 0 if resumen.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(principal())
