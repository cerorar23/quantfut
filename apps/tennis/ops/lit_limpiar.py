# apps/tennis/ops/lit_limpiar.py
"""Limpieza local de los PDFs de la biblioteca de tenis -> .txt destilado (0 tokens).

pdftotext -layout; luego: quita la lista de referencias (último encabezado References/Bibliografía en el último 40 %),
líneas de solo números de página, cabeceras/pies repetidos (>=4 veces), junta palabras partidas por guion de fin de línea
y colapsa blancos. Escribe un manifiesto con tamaños antes/después y si se encontró el corte de referencias.
No usa red. Uso: python lit_limpiar.py [--origen DIR] [--destino DIR]
"""
import argparse
import json
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ORIGEN = Path(r"C:\Users\huye\Documents\Codex\2026-11-01\quieor-que-busques-en-todo-internet-2\outputs\BIBLIOTECA_TENIS_COMPLETA\pdfs")
DESTINO = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\literatura_txt")
ENC_REF = re.compile(r"^\s*(\d+\.?\s*)?(references|reference list|bibliography|referencias|referências|bibliografia|bibliografía|literatura|literature cited|works cited)\s*:?\s*$", re.I)


def extraer(pdf: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, timeout=300)
    return r.stdout.decode("utf-8", "replace")


def limpiar(texto: str):
    lineas = [re.sub(r"[ \t]{3,}", "  ", l).rstrip() for l in texto.replace("\f", "\n").split("\n")]
    frec = Counter(l.strip() for l in lineas if 3 < len(l.strip()) < 90)
    repetidas = {l for l, c in frec.items() if c >= 4 and not re.search(r"[=<>]|\d\.\d", l)}
    lineas = [l for l in lineas if l.strip() not in repetidas and not re.fullmatch(r"\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*", l, re.I)]
    corte = None
    for i in range(len(lineas) - 1, int(len(lineas) * 0.6), -1):
        if ENC_REF.match(lineas[i]):
            corte = i
            break
    if corte is not None:
        lineas = lineas[:corte]
    t = "\n".join(lineas)
    t = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip() + "\n", corte is not None


def procesar(pdf: Path):
    crudo = extraer(pdf)
    limpio, hubo_ref = limpiar(crudo)
    dest = DESTINO / f"{pdf.stem}.txt"
    dest.write_text(limpio, encoding="utf-8")
    return dict(archivo=pdf.name, carpeta=pdf.parent.name, caracteres_crudo=len(crudo), caracteres_limpio=len(limpio),
                reduccion=round(1 - len(limpio) / max(1, len(crudo)), 3), corto_referencias=hubo_ref, vacio=len(crudo.strip()) < 2000)


def main():
    global DESTINO
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", default=str(ORIGEN))
    ap.add_argument("--destino", default=str(DESTINO))
    a = ap.parse_args()
    DESTINO = Path(a.destino)
    DESTINO.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(Path(a.origen).glob("*/*.pdf"))
    with ThreadPoolExecutor(4) as ex:
        filas = list(ex.map(procesar, pdfs))
    (DESTINO / "manifiesto.json").write_text(json.dumps(filas, indent=1, ensure_ascii=False), encoding="utf-8")
    vac = [f["archivo"] for f in filas if f["vacio"]]
    print(f"{len(filas)} PDFs; crudo {sum(f['caracteres_crudo'] for f in filas):,} -> limpio {sum(f['caracteres_limpio'] for f in filas):,} caracteres; "
          f"sin corte de referencias: {sum(not f['corto_referencias'] for f in filas)}; vacíos/escaneados: {vac}")


if __name__ == "__main__":
    main()
