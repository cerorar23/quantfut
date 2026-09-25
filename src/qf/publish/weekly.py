"""
Resumen semanal público. Se publica SIEMPRE, también las semanas en pérdida.

Ocultar las semanas malas es exactamente lo que hace que nadie crea a nadie en
este sector. Publicarlas es barato y es tu diferenciador.
"""
from __future__ import annotations

import logging

from ..eval.clv import summary
from . import telegram as tg

log = logging.getLogger(__name__)


def run() -> dict:
    s = summary(7)
    if s["n"] == 0:
        log.info("Sin picks liquidados esta semana.")
        return s
    tg.publish_results(s)
    log.info("Resumen semanal publicado: %s", s)
    return s


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
