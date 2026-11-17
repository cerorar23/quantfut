"""Extrae del archivo compartido de PropLine los eventos de tenis y los imprime como un documento JSON (17-nov-2026).

Corre DENTRO del contenedor worker, que ya monta el archivo (`/srv/quantfut/artifacts/propline_shared`) y trae
`qf.ingest.propline_shared`; no hace peticiones a PropLine (lectura sin red del último lote horario). Lo consume
`python -m tenis.captura.propline_calendario --stdin`. Uso: docker exec -i quantfut-worker-1 python - < este_archivo

Salida: {"recibido_en": <recepción real del lote>, "sha256": <huella del contenido>, "eventos": [...]}.
Código 3 si no hay un lote reciente (el colector horario falló): no se inventa nada.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

RAIZ = os.environ.get("PROPLINE_RAIZ", "/srv/quantfut/artifacts/propline_shared")
RUTA = "/v1/sports/tennis/odds"
EDAD_MAXIMA = 7200          # s: un lote de hace más de 2 h ya no es «el calendario de ahora»
CAMPOS = ("id", "commence_time", "home_team", "away_team", "tournament", "tour", "live", "is_outright")


def extraer(newest, ahora: datetime) -> dict | None:
    eventos, recibo = newest(RAIZ, RUTA, ahora, max_age_seconds=EDAD_MAXIMA)
    if recibo is None or eventos is None:
        return None
    mini = sorted(({k: e.get(k) for k in CAMPOS} for e in eventos), key=lambda e: str(e["id"]))
    cuerpo = {"recibido_en": recibo["received_at"], "eventos": mini}
    huella = hashlib.sha256(json.dumps(cuerpo, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"recibido_en": recibo["received_at"], "sha256": huella, "eventos": mini}


def main() -> int:
    sys.path.insert(0, "/app/src")
    from qf.ingest import propline_shared as ps
    doc = extraer(ps.newest, datetime.now(timezone.utc))
    if doc is None:
        print(json.dumps({"error": "sin_lote_reciente"}))
        return 3
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
