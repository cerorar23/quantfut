"""
Calendario de partidos futuros. MÓDULO BLOQUEANTE DE LA FASE 1.

Sin esto, `matches` solo contiene partidos terminados, el odds_worker no
encuentra nada con status='scheduled' y el job diario no tiene qué predecir.

Se ejecuta 2 veces al día. Es idempotente: reingiere el mismo rango y solo
actualiza lo que cambió (reprogramaciones, cambios de horario).

Ojo con las reprogramaciones: un partido movido de fecha cambia su kickoff, y
si no lo actualizas el odds_worker captura las ventanas equivocadas y el CLV
compara contra un "cierre" que no lo era.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..normalize import slugify

log = logging.getLogger(__name__)


def current_season(season_style: str, now: datetime | None = None) -> int:
    """
    Año de inicio de la temporada.
      - europea: 2025/26 -> 2025 (la temporada arranca en julio)
      - calendario / apertura-clausura: el año en curso
    """
    now = now or datetime.now(timezone.utc)
    if season_style == "european":
        return now.year if now.month >= 7 else now.year - 1
    return now.year


def _season_label(league: dict, ko: datetime) -> str:
    """
    Etiqueta de temporada para la columna `season`: la MISMA que pone el
    histórico cargado de football-data.

      european / apertura_clausura  2026/27 -> '2627' (Apertura 2026 y
                                    Clausura 2027 van juntos, como en MEX.csv)
      calendar                      2026    -> '2627' (BRA/ARG/USA.csv: '2026')

    Antes el año natural salía '2026' y Liga MX '2026A'/'2027C': la misma
    temporada quedaba con dos etiquetas según qué fuente creó cada partido.
    """
    style = league["season_style"]
    if style == "calendar":
        y = ko.year
    else:
        y = ko.year if ko.month >= 7 else ko.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _build_match_id(league_id: str, season: str, home: str, away: str,
                    ko: datetime) -> str:
    return (f"{league_id}:{season}:"
            f"{slugify(home)[:12].replace(' ', '')}-"
            f"{slugify(away)[:12].replace(' ', '')}:"
            f"{ko.strftime('%Y%m%d')}")


def run(days_ahead: int = 21) -> dict:
    """Calendario de partidos futuros desde el archivo de PropLine (25-oct-2026)."""
    from .propline_partidos import calendario
    return calendario()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
