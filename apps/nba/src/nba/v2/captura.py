"""Ejecutor de capturas a `nba_datos`: `python -m nba.v2.captura rotowire|espn|espn_directo|parte|nba|propline|historico` (lo lanza el cron del VPS).
`espn` lee el ledger de `run57` (v1, en retirada); `espn_directo` pide ESPN por su cuenta y lo sustituye.

Entorno: NBA_DB_DSN (obligatorio), NBA_CAPTURA_DIR (originales y estado, por omisión /datos),
NBA_RUN57_DIR (carpeta captures de run57, solo para espn),
NBA_PROPLINE_DIR (archivo compartido de PropLine) con NBA_PROPLINE_LOTES y NBA_PROPLINE_DESDE, ZENROWS_API_KEY y NBA_ZENROWS_TOPE_DIARIO (respaldo de pago
de Rotowire), SCRAPFLY_API_KEY y NBA_SCRAPFLY_TOPE_DIARIO (final del partido en cdn.nba.com, por omisión 40 créditos al día),
NBA_SOFASCORE_DIR (árbol `data/v3` del scraper de SofaScore, solo lectura) y NBA_SOFASCORE_DIAS (ventana de partidos recientes, 4).
"""
from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

from . import migrar
from .fuentes import espn, historico_cuotas, historico_partidos, historico_rotaciones, nba_cdn, parte_oficial, propline, rotowire, sofascore_arbol


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
        elif fuente == "espn_directo":
            resumen = espn.capturar(db, obtener or espn.obtener_http, raiz / "originales", ahora)
        elif fuente == "propline":
            if "NBA_PROPLINE_DIR" not in entorno:
                raise FaltaVariable("NBA_PROPLINE_DIR")
            desde = entorno.get("NBA_PROPLINE_DESDE")
            resumen = propline.capturar(db, Path(entorno["NBA_PROPLINE_DIR"]), ahora,
                                        max_lotes=int(entorno.get("NBA_PROPLINE_LOTES", "40")),
                                        desde_id=int(desde) if desde else None)
        elif fuente == "historico":
            if "NBA_HISTORICO_DIR" not in entorno:
                raise FaltaVariable("NBA_HISTORICO_DIR")
            carpeta = Path(entorno["NBA_HISTORICO_DIR"])
            pasos = set(entorno.get("NBA_HISTORICO_PASOS", "juegos,betsapi,props,h2h,cajas,partes").split(","))
            resumen = {"ok": True}
            for paso, ruta, cargar in (("juegos", "games.json", historico_cuotas.cargar_juegos),
                                       ("betsapi", "betsapi_odds.jsonl.gz", historico_cuotas.cargar_betsapi),
                                       ("props", "props_linked.jsonl.gz", historico_cuotas.cargar_props),
                                       ("h2h", "oddsapi_h2h", historico_cuotas.cargar_h2h)):
                if paso in pasos and (carpeta / ruta).exists():
                    resumen[paso] = cargar(db, carpeta / ruta)
            if "cajas" in pasos and (carpeta / "games.json").exists() and (carpeta / "players.jsonl.gz").exists():
                resumen["cajas"] = historico_partidos.cargar_cajas(db, carpeta)
            if "rotaciones" in pasos and (carpeta / "rotaciones.jsonl.gz").exists():
                indice, total = (int(x) for x in entorno.get("NBA_HISTORICO_FRAGMENTO", "0/1").split("/"))
                resumen["rotaciones"] = historico_rotaciones.cargar_rotaciones(db, carpeta, (indice, total))
            partes = [r for r in (carpeta / "partes_final.jsonl.gz", carpeta / "partes_t60.jsonl.gz") if r.exists()]
            if "partes" in pasos and partes:
                resumen["partes"] = historico_partidos.cargar_partes(db, partes)
        elif fuente == "parte":
            resumen = parte_oficial.capturar(db, obtener or parte_oficial.obtener_http, raiz / "originales", ahora)
        elif fuente == "sofascore":
            if "NBA_SOFASCORE_DIR" not in entorno:
                raise FaltaVariable("NBA_SOFASCORE_DIR")
            resumen = sofascore_arbol.cargar_recientes(db, Path(entorno["NBA_SOFASCORE_DIR"]), raiz / "sofascore", ahora,
                                                       dias=int(entorno.get("NBA_SOFASCORE_DIAS", "4")))
        elif fuente == "nba":
            if obtener is None:
                clave = entorno.get("SCRAPFLY_API_KEY")
                if not clave:
                    raise FaltaVariable("SCRAPFLY_API_KEY")
                obtener = lambda url: nba_cdn.obtener_scrapfly(url, clave)
            resumen = nba_cdn.capturar(db, obtener, raiz / "originales", ahora,
                                       tope_diario=float(entorno.get("NBA_SCRAPFLY_TOPE_DIARIO", "40")))
        else:
            raise ValueError(f"fuente desconocida: {fuente}")
        db.commit()
    return resumen


def principal(argv: list[str] | None = None, entorno: Mapping[str, str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    entorno = os.environ if entorno is None else entorno
    if len(argv) != 1 or argv[0] not in ("rotowire", "espn", "espn_directo", "parte", "nba", "sofascore", "propline", "historico"):
        print("uso: python -m nba.v2.captura rotowire|espn|espn_directo|parte|nba|sofascore|propline|historico", file=sys.stderr)
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
