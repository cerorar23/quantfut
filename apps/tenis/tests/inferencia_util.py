"""Ayudas de prueba para la inferencia del motor: parámetros sintéticos y mundo mínimo con ranking para ambos jugadores."""
from tenis.modelo.puntos import PsiP
from tenis.modelo.sintetico import LBAR, RHO_EPS, SIGMA_EPS, psi_prueba

from db_util import insertar, ts


def params_prueba(capa_edad: dict | None = None, c_inf: float = 0.02) -> dict:
    """Artefacto sintético con la estructura de `hiperparametros.json` (solo lo que usa la inferencia)."""
    psi_p = PsiP(0.25, 0.05, 0.01, 0.01, 0.01, (1.0, 1.0, 1.0, 1.0), SIGMA_EPS, RHO_EPS, 0.01)
    cfg = {"psi_r": psi_prueba(c_inf=c_inf).como_dict(), "psi_p": psi_p.como_dict(), "lbar": [LBAR] * 4}
    if capa_edad:
        cfg["capa_edad"] = capa_edad
    return {"circuitos": {"atp": cfg}}


def ranking(db, jugador: int, posicion: int, puntos: int | None = None, fecha="2026-03-02") -> int:
    r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
    return insertar(db, "INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, fuente, "
                        "recibo_id, recibido_en) VALUES ('atp', %s, %s, %s, %s, 'oficial_capturado', 'sofascore', %s, %s) "
                        "RETURNING ranking_id", (fecha, jugador, posicion, puntos or max(10000 - 50 * posicion, 100), r, ts("2026-01-05")))


def partido_futuro(db, m: dict, j1: int, j2: int, ronda: str = "SF", inicio: str = "2099-01-01T14:00:00Z") -> int:
    """Partido programado en el futuro entre j1 y j2 (lado 1 = j1) en la edición del mundo mínimo."""
    r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
    p = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
                     "VALUES (%s, %s, %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
                 (m["edicion"], ronda, j1, j2, r, ts("2026-01-05")))
    db.execute("INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, recibido_en) "
               "VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s)", (p, ts(inicio), r, ts("2026-01-05")))
    return p
