"""Descarga única de imágenes para la web: logos NBA (TheSportsDB) y fotos de tenistas (Wikimedia Commons).

Se ejecuta a mano, fuera de producción. Guarda los archivos en `frontend/imagenes/`, escribe
`manifiesto.json` (autor, licencia y enlace de cada foto) y regenera `creditos.html`.
La web no enlaza a dominios externos: todo se sirve desde el propio servidor.

    python scripts/imagenes/descargar_imagenes.py nba
    python scripts/imagenes/descargar_imagenes.py tenis [--seco]     # --seco: solo verifica, no descarga
    python scripts/imagenes/descargar_imagenes.py faltan             # tenistas publicados sin foto

Fotos de tenis: solo licencias CC BY, CC BY-SA, CC0 o dominio público (la atribución sale en
creditos.html y en el atributo title de cada foto). Una foto cuyo nombre en Wikidata no coincide
con el publicado se descarta hasta que alguien la revise.
"""
import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DESTINO = RAIZ / "frontend" / "imagenes"
UA = {"User-Agent": "QuantFutImagenes/1.0 (https://pronosticosdeportivos.pro; proyecto sin fines de lucro; descarga unica)"}
TSDB = "https://www.thesportsdb.com/api/v1/json/123/"
MAX_BYTES = 300_000
ANCHO_TENIS = 320


def norm(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)).lower()).strip()


_TRANSLIT = str.maketrans({"đ": "dj", "ð": "d", "ø": "o", "ł": "l", "ß": "ss", "æ": "ae", "œ": "oe", "-": " ", "'": ""})


def fichas(texto):
    """Conjunto de palabras comparable: sin acentos, sin guiones y con las transcripciones habituales (ä/ae, đ/dj)."""
    t = norm(str(texto or "").lower().translate(_TRANSLIT))
    t = re.sub(r"(?<=[aou])e", "", t)
    return frozenset(t.split())


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", norm(texto)).strip("-")


def pedir(url, params=None, pausa=1.2, binario=False):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    error = None
    for intento in range(4):
        time.sleep(pausa * (1 + intento * 3 if intento else 1))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                cuerpo = r.read(MAX_BYTES + 1 if binario else 5_000_000)
                return cuerpo if binario else json.loads(cuerpo)
        except Exception as exc:  # 429/502 ocasionales
            error = exc
    raise RuntimeError(f"{url[:90]}: {error}")


def extension(cuerpo):
    if cuerpo.startswith(b"\x89PNG"):
        return "png"
    if cuerpo.startswith(b"\xff\xd8"):
        return "jpg"
    if cuerpo[:4] == b"RIFF" and cuerpo[8:12] == b"WEBP":
        return "webp"
    return None


def leer_manifiesto():
    ruta = DESTINO / "manifiesto.json"
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {"version": 1, "generado": "", "nba": {}, "tenis": {}}


def guardar_manifiesto(m):
    m["generado"] = date.today().isoformat()
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "manifiesto.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    escribir_creditos(m)


def escribir_creditos(m):
    e = html.escape
    filas = "".join(
        f'<tr><td>{e(v["n"])}</td><td>{e(v["a"])}</td><td><a href="{e(v["lu"])}" rel="noopener">{e(v["l"])}</a></td>'
        f'<td><a href="{e(v["p"])}" rel="noopener">{e(v.get("fuente", "Wikimedia Commons"))}</a></td></tr>'
        for _, v in sorted(m["tenis"].items(), key=lambda kv: kv[1]["n"]))
    equipos = ", ".join(e(v["n"]) for _, v in sorted(m["nba"].items()))
    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Créditos de imágenes · QuantFut</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;background:#0b132b;color:#f8fafc}}
a{{color:#38bdf8}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border-bottom:1px solid #3a506b;padding:6px 8px;text-align:left;vertical-align:top}}
small{{color:#94a3b8}}</style></head><body>
<h1>Créditos de imágenes</h1>
<p>Imágenes alojadas en este servidor para identificar a los equipos y deportistas de cada encuentro.</p>
<h2>Fotos de tenistas</h2>
<p>Fotografías de <a href="https://commons.wikimedia.org" rel="noopener">Wikimedia Commons</a> con sus licencias Creative Commons indicadas por fila,
y retratos de <a href="https://api-tennis.com/documentation" rel="noopener">API-Tennis</a>, identificados como imágenes del proveedor.
Los retratos de API-Tennis no se atribuyen una licencia Creative Commons. Se recortan visualmente en la interfaz.</p>
<table><thead><tr><th>Jugador</th><th>Autor</th><th>Licencia</th><th>Fuente</th></tr></thead><tbody>{filas}</tbody></table>
<h2>Escudos de fútbol</h2>
<p>Escudos de clubes de <a href="https://www.api-football.com" rel="noopener">API-Football</a>, descargados una vez y servidos desde este servidor.</p>
<h2>Retratos de futbolistas y jugadores NBA</h2>
<p>Retratos de API-Football y del CDN oficial de <a href="https://www.nba.com" rel="noopener">NBA.com</a>, vinculados por el identificador del jugador y guardados en caché.
No se atribuye una licencia Creative Commons a estas imágenes. Si la fuente no proporciona foto, se muestra una marca de imagen no disponible.</p>
<h2>Logos de equipos NBA</h2>
<p>Logos obtenidos de <a href="https://www.thesportsdb.com" rel="noopener">TheSportsDB</a>: {equipos}.
Los nombres y logos de la NBA y de sus equipos son marcas de NBA Properties, Inc. y de los equipos; QuantFut no está afiliado ni respaldado por ellos
y los usa solo para identificar a los equipos de cada pronóstico.</p>
<p><small>Generado el {m["generado"]}. Los nombres de las personas fotografiadas se usan solo para identificarlas en el pronóstico de su partido.</small></p>
</body></html>
"""
    (DESTINO / "creditos.html").write_text(doc, encoding="utf-8")


# ------------------------------------------------------------------ NBA

def nba(forzar):
    equipos = json.loads((AQUI / "nba_equipos.json").read_text(encoding="utf-8"))
    m = leer_manifiesto()
    carpeta = DESTINO / "nba"
    carpeta.mkdir(parents=True, exist_ok=True)
    for codigo, nombre in equipos.items():
        destino = carpeta / f"{codigo}.png"
        if destino.exists() and not forzar and codigo in m["nba"]:
            continue
        r = pedir(TSDB + "searchteams.php", {"t": nombre}, pausa=4.0)
        filas = [x for x in (r.get("teams") or []) if x.get("strLeague") == "NBA"]
        url = filas[0].get("strBadge") if filas else None
        if not url:
            print("SIN LOGO", codigo, nombre)
            continue
        cuerpo = None
        for variante in (url + "/small", url):
            try:
                cuerpo = pedir(variante, binario=True)
            except RuntimeError:
                continue
            if extension(cuerpo) == "png" and len(cuerpo) <= MAX_BYTES:
                break
            cuerpo = None
        if not cuerpo:
            print("DESCARTADO (no PNG o demasiado grande)", codigo)
            continue
        destino.write_bytes(cuerpo)
        m["nba"][codigo] = {"f": f"{codigo}.png", "n": nombre, "fuente": "TheSportsDB"}
        print("ok", codigo, len(cuerpo), "bytes")
    guardar_manifiesto(m)


# ------------------------------------------------------------------ tenis

LIBRES = (("cc0", "CC0"), ("public domain", "Dominio público"), ("pd ", "Dominio público"))


def licencia_libre(texto):
    s = (texto or "").lower().strip()
    if s.startswith("cc by-sa") or s.startswith("cc-by-sa"):
        return True
    if (s.startswith("cc by") or s.startswith("cc-by")) and "-nc" not in s and "-nd" not in s and " nc" not in s and " nd" not in s:
        return True
    return any(s.startswith(p) or p in s for p, _ in LIBRES)


def tenis(seco):
    jugadores = json.loads((AQUI / "tenistas.json").read_text(encoding="utf-8"))
    m = leer_manifiesto()
    qids = sorted(set(jugadores.values()))
    ent = {}
    for i in range(0, len(qids), 50):
        r = pedir("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]), "props": "claims|labels|aliases", "languages": "mul|en|es|fr|de|it|pt", "format": "json"}, pausa=0.5)
        ent.update(r.get("entities", {}))
    plan = {}
    revisar = []
    for nombre, q in jugadores.items():
        e = ent.get(q, {})
        nombres = {norm(v["value"]) for v in e.get("labels", {}).values()}
        for lista in e.get("aliases", {}).values():
            nombres |= {norm(v["value"]) for v in lista}
        archivo = None
        for c in e.get("claims", {}).get("P18", []):
            archivo = c["mainsnak"]["datavalue"]["value"]
            break
        if not archivo:
            revisar.append((nombre, q, "sin imagen P18"))
        elif fichas(nombre) not in {fichas(n) for n in nombres}:
            revisar.append((nombre, q, "el nombre no coincide con Wikidata: " + ", ".join(sorted(nombres))[:80]))
        else:
            plan[nombre] = (q, archivo)
    info = {}
    archivos = sorted({a for _, a in plan.values()})
    for i in range(0, len(archivos), 40):
        r = pedir("https://commons.wikimedia.org/w/api.php", {"action": "query", "titles": "|".join("File:" + a for a in archivos[i:i + 40]), "prop": "imageinfo",
                  "iiprop": "extmetadata|url", "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit", "format": "json", "redirects": 1}, pausa=0.5)
        desde = {t["to"]: t["from"] for t in r["query"].get("redirects", [])}
        norma = {t["to"]: t["from"] for t in r["query"].get("normalized", [])}
        for p in r["query"]["pages"].values():
            ii = (p.get("imageinfo") or [{}])[0]
            md = {k: v.get("value") for k, v in (ii.get("extmetadata") or {}).items()}
            clave = desde.get(p["title"], p["title"])
            clave = norma.get(clave, clave)
            info[clave[5:]] = {"md": md, "pagina": ii.get("descriptionurl")}
    carpeta = DESTINO / "tenis"
    carpeta.mkdir(parents=True, exist_ok=True)
    hechos = 0
    for nombre, (q, archivo) in plan.items():
        i = info.get(archivo.replace("_", " ")) or info.get(archivo)
        md = (i or {}).get("md", {})
        if not i or not licencia_libre(md.get("LicenseShortName")):
            revisar.append((nombre, q, "licencia no libre o desconocida: " + str(md.get("LicenseShortName"))))
            continue
        clave = norm(nombre)
        autor = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", md.get("Artist") or md.get("Credit") or "")).split())[:120] or "Autor no indicado"
        entrada = {"f": None, "n": nombre, "a": autor, "l": md["LicenseShortName"], "lu": md.get("LicenseUrl") or i["pagina"], "p": i["pagina"], "q": q}
        if seco:
            print("verificado", nombre, md["LicenseShortName"])
            continue
        existente = m["tenis"].get(clave)
        if existente and (carpeta / existente["f"]).exists():
            continue
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(archivo.replace(" ", "_")) + f"?width={ANCHO_TENIS}"
        try:
            cuerpo = pedir(url, binario=True, pausa=1.5)
        except RuntimeError as exc:
            revisar.append((nombre, q, "descarga fallida: " + str(exc)[:80]))
            continue
        ext = extension(cuerpo)
        if ext not in ("jpg", "png") or len(cuerpo) > MAX_BYTES:
            revisar.append((nombre, q, f"formato o tamaño no válido ({ext}, {len(cuerpo)} bytes)"))
            continue
        entrada["f"] = f"{slug(nombre)}.{ext}"
        (carpeta / entrada["f"]).write_bytes(cuerpo)
        m["tenis"][clave] = entrada
        hechos += 1
        print("ok", nombre, ext, len(cuerpo), "bytes")
    if not seco:
        guardar_manifiesto(m)
    print(f"\nlistas {len(m['tenis'])} fotos ({hechos} nuevas); {len(revisar)} para revisar a mano:")
    for r in revisar:
        print(" -", *r)


def faltan():
    m = leer_manifiesto()
    datos = pedir("https://pronosticosdeportivos.pro/web/deportes/tenis")
    nombres = sorted({n for e in datos["events"] for n in (e["home"], e["away"])})
    sin = [n for n in nombres if norm(n) not in m["tenis"]]
    print(f"{len(sin)} de {len(nombres)} tenistas publicados sin foto:")
    for n in sin:
        print(" -", n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tarea", choices=["nba", "tenis", "faltan"])
    ap.add_argument("--seco", action="store_true", help="solo verificar emparejamientos y licencias")
    ap.add_argument("--forzar", action="store_true")
    a = ap.parse_args()
    if a.tarea == "nba":
        nba(a.forzar)
    elif a.tarea == "tenis":
        tenis(a.seco)
    else:
        faltan()
