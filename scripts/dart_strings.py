"""Inventario de cadenas literales de Dart (para el trabajo de traducciones).

Uso:  python scripts/dart_strings.py <archivo.dart>... [--json salida.json]

Tokeniza cadenas '...' y "..." (con escapes, interpolacion ${...}/$id, prefijo r y
comillas triples), ignora comentarios y devuelve (linea, texto_sin_comillas, raw).
No decide que es texto de interfaz: eso lo filtra `ui_candidates`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BS = chr(92)


def strings(src: str):
    i, n, line = 0, len(src), 1
    out = []
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += src.count("\n", i, j)
            i = j
        elif c in "'\"" or (c == "r" and i + 1 < n and src[i + 1] in "'\"" and (i == 0 or not (src[i - 1].isalnum() or src[i - 1] == "_"))):
            raw = c == "r"
            start = i + 1 if raw else i
            q = src[start]
            triple = src.startswith(q * 3, start)
            qlen = 3 if triple else 1
            j = start + qlen
            depth = 0
            buf = []
            while j < n:
                ch = src[j]
                if not raw and ch == BS:
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if not raw and ch == "$" and j + 1 < n and src[j + 1] == "{":
                    depth, k = 1, j + 2
                    while k < n and depth:
                        depth += {"{": 1, "}": -1}.get(src[k], 0)
                        k += 1
                    buf.append(src[j:k])
                    j = k
                    continue
                if depth == 0 and src.startswith(q * qlen, j):
                    break
                if ch == "\n" and not triple:
                    break
                buf.append(ch)
                j += 1
            text = "".join(buf)
            out.append((line, text))
            line += src.count("\n", i, j)
            i = j + qlen
        else:
            i += 1
    return out


NOT_UI = re.compile(
    r"^(?:[a-z][a-z0-9_]*|[A-Z][A-Z0-9_]*|[a-z]+(?:[.:/_-][a-zA-Z0-9_]+)+|https?://\S+|/\S*|#\S*|Gilroy\S*"
    r"|X-\S+|Bearer \$\S+|\^.*\$|[\W\d_]*|\.?[a-z]+)$"
)


def ui_candidates(items):
    keep = []
    for line, t in items:
        if len(t.strip()) < 2 or not re.search("[A-Za-zÀ-ÿ]{2}", t):
            continue
        if NOT_UI.match(t) and " " not in t:
            continue
        keep.append((line, t))
    return keep


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    jout = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if jout:
        args = [a for a in args if a != jout]
    res = {}
    for f in args:
        found = ui_candidates(strings(Path(f).read_text(encoding="utf-8")))
        if found:
            res[f.replace(BS, "/")] = found
    if jout:
        Path(jout).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        for f, v in res.items():
            print("##", f)
            for ln, t in v:
                print(f"  {ln}: {t[:120]}")
    print(f"total: {sum(len(v) for v in res.values())} en {len(res)} archivos", file=sys.stderr)
