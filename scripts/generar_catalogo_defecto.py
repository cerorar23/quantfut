"""Escribe `apps/mobile/assets/model/cliente_config_defecto.json`: la copia de fábrica del catálogo de la app.

Es `catalogo.deportes_para('app')` aplicado a la semilla del código (nunca a la base): lo que la app muestra
sin red y sin disco. Ejecutar tras tocar `src/qf/comercial/catalogo_semilla.py`; `tests/test_catalogo.py`
falla si el archivo no coincide con la semilla.

    PYTHONPATH=src python scripts/generar_catalogo_defecto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from qf.comercial import catalogo  # noqa: E402

DESTINO = RAIZ / 'apps' / 'mobile' / 'assets' / 'model' / 'cliente_config_defecto.json'


def contenido() -> str:
    """Texto exacto del archivo (UTF-8, LF, sangría de 2, salto final)."""
    deportes = catalogo.deportes_para_semilla('app')
    return json.dumps({'deportes': deportes}, ensure_ascii=False, indent=2) + '\n'


def main() -> None:
    DESTINO.write_text(contenido(), encoding='utf-8', newline='\n')
    print(f'Escrito {DESTINO.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
