"""Añade o actualiza textos en los 6 ARB (es, en, pt, fr, it, de) de una sola vez.

Regla del proyecto: todo texto nuevo o modificado se traduce a los 6 idiomas en el
mismo cambio. Uso:

    python tool/l10n_add.py nuevos.json

`nuevos.json`:
{
  "navHome": {"es": "Inicio", "en": "Home", "pt": "Início", "fr": "Accueil",
              "it": "Home", "de": "Start"},
  "matchesCount": {"es": "{count} enfrentamientos", "en": "{count} matches", ...,
                   "meta": {"description": "...", "placeholders": {"count": {"type": "int"}}}}
}

- Faltar un idioma es un error (no se escribe nada).
- `meta` (descripción y placeholders) va en la plantilla `app_es.arb`; los demás ARB
  solo llevan el texto, como espera `flutter gen-l10n`.
- Tras ejecutar: `flutter gen-l10n` (o `flutter pub get`) y `flutter test test/l10n_test.dart`.
"""
import json
import sys
from pathlib import Path

LANGS = ("es", "en", "pt", "fr", "it", "de")
ARB_DIR = Path(__file__).resolve().parent.parent / "lib" / "l10n"


def load(lang: str) -> dict:
    f = ARB_DIR / f"app_{lang}.arb"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"@@locale": lang}


def save(lang: str, data: dict) -> None:
    head = {"@@locale": data["@@locale"]}
    rest = {k: v for k, v in data.items() if k != "@@locale"}
    names = sorted({k.lstrip("@") for k in rest})
    ordered = dict(head)
    for k in names:
        if k in rest:
            ordered[k] = rest[k]
        if "@" + k in rest:
            ordered["@" + k] = rest["@" + k]
    (ARB_DIR / f"app_{lang}.arb").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(path: str) -> None:
    new = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = []
    for key, entry in new.items():
        missing = [l for l in LANGS if not str(entry.get(l, "")).strip()]
        if missing:
            problems.append(f"{key}: faltan {', '.join(missing)}")
    if problems:
        sys.exit("No se escribió nada:\n  " + "\n  ".join(problems))
    ARB_DIR.mkdir(parents=True, exist_ok=True)
    data = {l: load(l) for l in LANGS}
    for key, entry in new.items():
        for l in LANGS:
            data[l][key] = entry[l]
        if entry.get("meta"):
            data["es"]["@" + key] = entry["meta"]
    for l in LANGS:
        save(l, data[l])
    print(f"{len(new)} textos escritos en {len(LANGS)} idiomas")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
