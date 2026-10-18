"""Clima histórico de cada partido desde ERA5 (Copernicus CDS), db/082.

Una petición por celda de 0,25° (los estadios de una misma ciudad comparten celda) con las seis variables horarias
de todo el periodo. Cada respuesta se guarda en disco antes de tocar la base: cualquier reprocesado reutiliza el
archivo sin volver a pedirlo. El token personal llega por la variable de entorno CDS_API_TOKEN, nunca por archivo.

ERA5 publica con ~5 días de retraso: los partidos más recientes se completan en una pasada posterior.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import logging
import math
import os
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

BASE = "https://cds.climate.copernicus.eu/api/retrieve/v1"
DATASET = "reanalysis-era5-single-levels-timeseries"
VARIABLES = ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind", "10m_v_component_of_wind",
             "total_precipitation", "total_cloud_cover"]
REJILLA = 0.25
RETRASO_DIAS = 7
CONCURRENCIA = 4
DESDE = date(2023, 7, 1)


def celda(lat: float, lon: float) -> tuple[float, float]:
    return round(lat / REJILLA) * REJILLA, round(lon / REJILLA) * REJILLA


def humedad_relativa(t_c: float, td_c: float) -> float:
    """Humedad relativa (%) por la aproximación de Magnus, acotada a 0-100."""
    a, b = 17.625, 243.04
    rh = 100.0 * math.exp(a * td_c / (b + td_c)) / math.exp(a * t_c / (b + t_c))
    return max(0.0, min(100.0, rh))


def leer_csv(texto: str) -> dict[datetime, dict[str, float]]:
    """valid_time (UTC) -> variables; filas con algún valor ausente o no finito se descartan."""
    out: dict[datetime, dict[str, float]] = {}
    for fila in csv.DictReader(io.StringIO(texto)):
        try:
            t = datetime.fromisoformat(fila["valid_time"]).replace(tzinfo=timezone.utc)
            v = {k: float(fila[k]) for k in ("t2m", "d2m", "u10", "v10", "tcc", "tp")}
        except (KeyError, ValueError, TypeError):
            continue
        if all(math.isfinite(x) for x in v.values()):
            out[t] = v
    return out


def caracteristicas(serie: dict[datetime, dict[str, float]], saque: datetime) -> dict | None:
    """Clima en la ventana del partido, o None si falta alguna de las horas necesarias."""
    h0 = saque.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    horas = [h0 + timedelta(hours=i) for i in range(3)]
    acumuladas = [h0 + timedelta(hours=i) for i in range(1, 4)]
    if any(h not in serie for h in horas + acumuladas):
        return None
    n = len(horas)
    t = sum(serie[h]["t2m"] for h in horas) / n - 273.15
    td = sum(serie[h]["d2m"] for h in horas) / n - 273.15
    viento = sum(math.hypot(serie[h]["u10"], serie[h]["v10"]) for h in horas) / n
    return {"temperatura_c": round(t, 2), "humedad_pct": round(humedad_relativa(t, td), 1),
            "viento_ms": round(viento, 2),
            "precipitacion_mm": round(max(0.0, sum(serie[h]["tp"] for h in acumuladas) * 1000.0), 3),
            "nubosidad_pct": round(sum(serie[h]["tcc"] for h in horas) / n * 100.0, 1)}


# --------------------------------------------------------------------------------------------- descarga CDS
class Cds:
    def __init__(self, token: str):
        self.h = {"PRIVATE-TOKEN": token, "Content-Type": "application/json", "Accept": "application/json",
                  "User-Agent": "QuantFut/1.0"}

    def _call(self, url: str, data: dict | None = None, espera_base_s: float = 5.0) -> dict:
        """Reintenta errores 5xx y de red (3 intentos, espera creciente); un 4xx no se reintenta."""
        for intento in range(3):
            req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                         headers=self.h)
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                if exc.code < 500 or intento == 2:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if intento == 2:
                    raise
            time.sleep(espera_base_s * (intento + 1))
        raise RuntimeError("inalcanzable")

    def serie(self, lat: float, lon: float, desde: date, hasta: date, max_espera_s: int = 3600) -> str:
        inp = {"variable": VARIABLES, "location": {"longitude": lon, "latitude": lat},
               "date": [f"{desde.isoformat()}/{hasta.isoformat()}"], "data_format": "csv"}
        job = self._call(f"{BASE}/processes/{DATASET}/execution", {"inputs": inp})["jobID"]
        t0 = time.time()
        while True:
            time.sleep(8)
            estado = self._call(f"{BASE}/jobs/{job}")["status"]
            if estado == "successful":
                break
            if estado in ("failed", "rejected"):
                raise RuntimeError(f"CDS {estado} para ({lat}, {lon})")
            if time.time() - t0 > max_espera_s:
                raise TimeoutError(f"CDS sin terminar tras {max_espera_s} s para ({lat}, {lon})")
        href = self._call(f"{BASE}/jobs/{job}/results")["asset"]["value"]["href"]
        raw = urllib.request.urlopen(urllib.request.Request(href, headers={"User-Agent": "QuantFut/1.0"}),
                                     timeout=300).read()
        if raw[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(raw))
            raw = z.read(z.namelist()[0])
        return raw.decode("utf-8")


# --------------------------------------------------------------------------------------------- orquestación
def _celdas(c) -> dict[tuple[float, float], dict]:
    filas = c.execute(
        """SELECT m.match_id, m.kickoff_utc, e.stadium_id, e.lat, e.lon FROM matches m
           JOIN estadios e ON e.stadium_id = m.stadium_id
           WHERE e.lat IS NOT NULL AND e.lon IS NOT NULL AND m.kickoff_utc >= %s
             AND NOT EXISTS (SELECT 1 FROM clima_era5_partido x WHERE x.match_id = m.match_id)""",
        (datetime.combine(DESDE, datetime.min.time(), tzinfo=timezone.utc),)).fetchall()
    celdas: dict[tuple[float, float], dict] = {}
    for f in filas:
        k = celda(f["lat"], f["lon"])
        celdas.setdefault(k, {"partidos": []})["partidos"].append(f)
    return celdas


def _archivo(carpeta: Path, k: tuple[float, float]) -> Path:
    return carpeta / f"era5_{k[0]:+.2f}_{k[1]:+.3f}.csv.gz"


def procesar_celda(c, k, partidos, serie) -> int:
    n = 0
    with c.cursor() as w:
        for p in partidos:
            x = caracteristicas(serie, p["kickoff_utc"])
            if x is None:
                continue
            w.execute("""INSERT INTO clima_era5_partido (match_id, stadium_id, celda_lat, celda_lon, temperatura_c,
                             humedad_pct, viento_ms, precipitacion_mm, nubosidad_pct)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (match_id) DO NOTHING""",
                      (p["match_id"], p["stadium_id"], k[0], k[1], x["temperatura_c"], x["humedad_pct"],
                       x["viento_ms"], x["precipitacion_mm"], x["nubosidad_pct"]))
            n += w.rowcount
    c.commit()
    return n


def cargar(c, carpeta: Path, token: str | None, limite_celdas: int | None = None) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    celdas = _celdas(c)
    hasta = date.today() - timedelta(days=RETRASO_DIAS)
    r = {"celdas": len(celdas), "descargadas": 0, "desde_disco": 0, "partidos_guardados": 0, "errores": 0}
    pendientes = []
    for k, d in sorted(celdas.items()):
        arch = _archivo(carpeta, k)
        if arch.exists():
            serie = leer_csv(gzip.decompress(arch.read_bytes()).decode("utf-8"))
            r["desde_disco"] += 1
            r["partidos_guardados"] += procesar_celda(c, k, d["partidos"], serie)
        else:
            pendientes.append(k)
    if limite_celdas is not None:
        pendientes = pendientes[:limite_celdas]
    if pendientes and not token:
        raise SystemExit("falta CDS_API_TOKEN para descargar las celdas pendientes")
    cds = Cds(token) if pendientes else None
    with ThreadPoolExecutor(max_workers=CONCURRENCIA) as ex:
        futuros = {}
        for k in pendientes:
            kicks = [p["kickoff_utc"].date() for p in celdas[k]["partidos"]]
            desde = max(DESDE, min(kicks) - timedelta(days=1))
            futuros[ex.submit(cds.serie, k[0], k[1], desde, min(max(kicks) + timedelta(days=1), hasta))] = k
        for fut in as_completed(futuros):
            k = futuros[fut]
            try:
                texto = fut.result()
            except Exception as exc:  # noqa: BLE001 — una celda caída no detiene las demás
                r["errores"] += 1
                log.warning("celda %s: %s", k, exc)
                continue
            tmp = _archivo(carpeta, k).with_suffix(".tmp")
            tmp.write_bytes(gzip.compress(texto.encode("utf-8")))
            tmp.replace(_archivo(carpeta, k))
            r["descargadas"] += 1
            r["partidos_guardados"] += procesar_celda(c, k, celdas[k]["partidos"], leer_csv(texto))
            log.info("ERA5: %s", r)
    return r


def main(argv=None) -> None:
    import argparse

    from ..config import settings
    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limite-celdas", type=int, default=None)
    ap.add_argument("--carpeta", default=f"{settings.artifact_dir}/era5")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        print(json.dumps(cargar(c, Path(a.carpeta), os.environ.get("CDS_API_TOKEN"), a.limite_celdas), indent=1))


if __name__ == "__main__":
    main()
