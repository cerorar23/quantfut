"""Fotos de tenistas de SofaScore (150x150; webp o PNG según los bytes) -> `frontend/imagenes/tenis/` + bloque `tenis_sofascore` del manifiesto.

Se ejecuta a mano, fuera de producción. No borra los JPG de Wikimedia ni el bloque `tenis` viejo: la web
y la app prefieren `tenis_sofascore` cuando existe y caen al bloque anterior si no.

    python scripts/imagenes/tenistas_sofascore.py [--origen RUTA] [--seco]

Bloque generado: nombre normalizado (misma `norm()` que descargar_imagenes) ->
{id, f, pais, genero, ranking}; si dos tenistas comparten nombre, la clave guarda una lista.
Subir al VPS y desplegar requiere confirmación del titular; creditos.html no se toca hasta que este
bloque sea el activo.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from descargar_imagenes import DESTINO, norm  # noqa: E402

ORIGEN = Path(r"C:\Users\huye\Documents\SOFASCORE\data\images\tenistas")


def slug(nombre):
    return re.sub(r"[^a-z0-9]+", "-", norm(nombre)).strip("-")[:70]


def extension(cabecera):
    """Extensión real según los bytes: 73 «webp» de SofaScore son PNG y se servirían con tipo erróneo."""
    if cabecera[:8] == bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]):
        return "png"
    if cabecera[:3] == bytes([0xFF, 0xD8, 0xFF]):
        return "jpg"
    return "webp" if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP" else None


def construir(filas, tipo):
    """filas: metadatos del JSON; tipo(archivo)->extensión real o None si no existe/no es imagen.
    Devuelve (bloque, copias[(archivo, f)])."""
    grupos = {}
    for r in filas:
        ext = tipo(r.get("archivo")) if r.get("archivo") else None
        if not ext:
            continue
        r = {**r, "_ext": ext}
        clave = norm(r["nombre"])
        if clave:
            grupos.setdefault(clave, []).append(r)
    bloque, copias = {}, []
    for clave, rs in sorted(grupos.items()):
        entradas = []
        for r in sorted(rs, key=lambda r: int(r["id"])):
            base = slug(r["nombre"])
            f = f"{base}-{int(r['id'])}.{r['_ext']}" if len(rs) > 1 else f"{base}.{r['_ext']}"
            entradas.append({"id": int(r["id"]), "f": f, "pais": r.get("pais_codigo") or None,
                             "genero": r.get("genero") or None,
                             "ranking": int(r["posicion"]) if str(r.get("posicion") or "").isdigit() else None})
            copias.append((r["archivo"], f))
        bloque[clave] = entradas if len(entradas) > 1 else entradas[0]
    return bloque, copias


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", type=Path, default=ORIGEN)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args()
    filas = json.loads((a.origen / "tenistas_metadata.json").read_text(encoding="utf-8"))
    def tipo(f):
        ruta = a.origen / f
        return extension(ruta.read_bytes()[:12]) if ruta.is_file() else None

    bloque, copias = construir(filas, tipo)
    print(f"{len(bloque)} nombres, {len(copias)} fotos")
    if a.seco:
        return
    destino = DESTINO / "tenis"
    destino.mkdir(parents=True, exist_ok=True)
    for archivo, f in copias:
        shutil.copyfile(a.origen / archivo, destino / f)
    ruta = DESTINO / "manifiesto.json"
    m = json.loads(ruta.read_text(encoding="utf-8"))
    m["tenis_sofascore"] = bloque
    m["generado"] = date.today().isoformat()
    ruta.write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
