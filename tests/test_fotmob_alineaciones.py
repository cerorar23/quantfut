"""Bajas y once desde FotMob: copia a las tablas de siempre, solo el `standard` completo va a `lineups`."""
from datetime import datetime, timezone

from qf.ingest import fotmob_alineaciones as fa, lineups

AT = datetime(2026, 10, 31, 18, 15, tzinfo=timezone.utc)


def jug(side, n, titular=True):
    return {"side": side, "jugador_id": 100 + n + (0 if side == "home" else 50), "nombre": "J%d" % n, "titular": titular}


def once(side, n=11):
    return [jug(side, i) for i in range(n)] + [jug(side, 90, titular=False)]


def baja(side="home", i=1):
    return {"side": side, "jugador_id": 900 + i, "nombre": "B%d" % i, "tipo": "injured", "regreso_texto": "Ankle",
            "regreso_fecha": datetime(2026, 11, 10, tzinfo=timezone.utc)}


def cap(tipo="standard", mins=44.9):
    return {"match_id": "m1", "capturado_en": AT, "mins_to_kickoff": mins, "tipo_alineacion": tipo,
            "formacion_local": "4-3-3", "formacion_visita": "4-2-3-1"}


class Conn:
    def __init__(self, ya_hay_lineups=False):
        self.sqls, self.ya = [], ya_hay_lineups

    def execute(self, sql, params=()):
        self.sqls.append((" ".join(sql.split()), params))
        ya = self.ya

        class R:
            rowcount = 1

            def fetchone(self):
                return {"x": 1} if ya and "FROM lineups WHERE" in sql else None
        return R()

    def tabla(self, nombre):
        return [p for s, p in self.sqls if s.startswith("INSERT INTO " + nombre + " (")]


def test_titulares_ignora_suplentes_y_marca_la_fuente():
    xi = fa.titulares(once("home"), "home")
    assert len(xi) == 11 and all(p["src"] == "fotmob" for p in xi)


def test_once_oficial_completo_va_a_lineups_con_los_minutos_al_saque():
    c = Conn()
    r = fa.aplicar(c, cap(), once("home") + once("away"), [baja()])
    assert r == {"bajas": 1, "oficial": True, "previsto": False}
    assert len(c.tabla("lineups")) == 2 and c.tabla("lineups")[0][5] == 45
    prev = c.tabla("lineups_previstas")
    assert len(prev) == 2 and prev[0][4] is True        # confirmed
    assert c.tabla("injuries")[0][-1].isoformat() == "2026-11-10"


def test_once_previsto_nunca_entra_en_lineups():
    c = Conn()
    r = fa.aplicar(c, cap("predicted", 1559), once("home") + once("away"), [])
    assert r["oficial"] is False and r["previsto"] is True
    assert c.tabla("lineups") == [] and c.tabla("lineups_previstas")[0][4] is False
    assert len(c.tabla("injuries_capture_log")) == 1    # comprobado sin bajas


def test_once_incompleto_o_de_un_solo_lado_no_es_oficial():
    c = Conn()
    assert fa.aplicar(c, cap(), once("home") + once("away", 9), [])["oficial"] is False
    assert c.tabla("lineups") == []


def test_no_pisa_un_lineups_ya_guardado():
    c = Conn(ya_hay_lineups=True)
    fa.aplicar(c, cap(), once("home") + once("away"), [])
    assert c.tabla("lineups") == []


def test_captura_sin_tipo_solo_guarda_bajas():
    c = Conn()
    fa.aplicar(c, cap(None), [], [baja()])
    assert c.tabla("lineups_previstas") == [] and len(c.tabla("injuries")) == 1


def test_availability_distingue_la_fuente_fotmob():
    assert lineups._fuente(fa.titulares(once("home"), "home")) == "fotmob"
    assert lineups._fuente([{"player_id": 1, "src": "sofascore"}]) == "sofascore"
    assert lineups._fuente([{"player_id": 1}]) == "api"
