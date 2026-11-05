# apps/tennis/ops/lit_validar_json.py
"""Valida los JSON del Paso A (un JSON por texto limpio): existencia, claves exactas, tipos y campos vacíos.
Imprime los que faltan o están mal para relanzar solo esos. Solo lectura."""
import json
from pathlib import Path

BASE = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
CLAVES = {"codigo", "titulo", "modelo", "formulas_clave", "datos", "validacion", "resultado", "limites", "replicable", "mercado"}


def main():
    esperados = {Path(l).stem for p in sorted((BASE / "literatura_txt").glob("lote_*.txt")) for l in p.read_text(encoding="utf-8").split()}
    hechos = {p.stem: p for p in (BASE / "literatura_json").glob("*.json")}
    faltan = sorted(esperados - set(hechos))
    malos = []
    for k, p in hechos.items():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            malos.append((k, f"JSON inválido: {e}")); continue
        if set(d) != CLAVES:
            malos.append((k, f"claves: faltan {sorted(CLAVES - set(d))} sobran {sorted(set(d) - CLAVES)}")); continue
        if not isinstance(d["formulas_clave"], list) or any(not isinstance(d[c], str) or not d[c].strip() for c in CLAVES - {"formulas_clave"}):
            malos.append((k, "tipos o campos vacíos"))
    print(f"esperados {len(esperados)}; escritos {len(hechos)}; faltan {len(faltan)}; malos {len(malos)}")
    for f in faltan:
        print("FALTA", f)
    for k, m in malos:
        print("MAL", k, m)


if __name__ == "__main__":
    main()
