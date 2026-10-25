"""Bajas y once de SofaScore: parseo, emparejamiento, solo el oficial a `lineups`, y fuente de ids."""
from datetime import datetime, timezone

from qf.ingest import lineups, sofascore_alineaciones as sa

KO = datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc)
RECIBO = {"id": 7, "received_at": "2026-10-25T13:10:00+00:00", "sha256": "x"}


def jugador(i, sub=False, pos="M"):
    return {"substitute": sub, "shirtNumber": i, "position": pos,
            "player": {"id": 1000 + i, "name": "J%d" % i}}


def lado(n=11, bajas=(), formacion="4-2-3-1"):
    return {"formation": formacion, "players": [jugador(i) for i in range(n)] + [jugador(99, sub=True)],
            "missingPlayers": list(bajas)}


def baja(i, tipo="missing", desc="Hamstring Injury", fin="2026-10-31T00:00:00+00:00"):
    return {"type": tipo, "reason": 1, "description": desc, "expectedEndDate": fin,
            "player": {"id": 5000 + i, "name": "B%d" % i}}


def fila(confirmed=False, local=None, visita=None):
    return {"kind": "event_detail", "sport": "football", "id": 16363899, "uniqueTournamentId": 17,
            "startTimestamp": int(KO.timestamp()), "statusType": "notstarted",
            "homeTeam": "Manchester United", "awayTeam": "Brighton",
            "lineups": {"confirmed": confirmed, "home": local or lado(), "away": visita or lado()}}


class Conn:
    """Registra las sentencias; `existe` simula filas ya guardadas por (tabla)."""

    def __init__(self, existe=()):
        self.sqls, self.existe = [], set(existe)

    def execute(self, sql, params=()):
        self.sqls.append((" ".join(sql.split()), params))
        outer = self

        class R:
            rowcount = 1

            def fetchone(self):
                if "FROM lineups_previstas" in sql:
                    return {"x": 1} if "previstas" in outer.existe else None
                if "FROM lineups WHERE" in sql:
                    return {"x": 1} if "lineups" in outer.existe else None
                if "kickoff_utc FROM matches" in sql:
                    return {"kickoff_utc": KO}
        return R()

    def tablas(self, nombre):
        return [p for s, p in self.sqls if s.startswith("INSERT INTO " + nombre)]


def test_titulares_ignora_suplentes_y_marca_la_fuente():
    xi = sa.titulares(lado())
    assert len(xi) == 11 and all(p["src"] == "sofascore" for p in xi)
    assert xi[0]["player_id"] == 1000 and xi[0]["pos"] == "M"


def test_bajas_con_motivo_y_fecha_de_regreso():
    b = sa.bajas({"missingPlayers": [baja(1), baja(2, "doubtful", "Knock Injury", fin=None)]})
    assert [(x["status_type"], x["reason"]) for x in b] == [("missing", "Hamstring Injury"), ("doubtful", "Knock Injury")]
    assert str(b[0]["expected_return"]) == "2026-10-31" and b[1]["expected_return"] is None


def test_previsto_guarda_bajas_y_previsto_pero_nunca_lineups():
    c = Conn()
    r = sa.aplicar(c, RECIBO, fila(False, lado(bajas=[baja(1)]), lado(bajas=[baja(2)])), "m1")
    assert r == {"nuevo": True, "bajas": 2, "oficial": False, "previsto": True}
    assert len(c.tablas("injuries ")) == 2 and len(c.tablas("lineups_previstas")) == 2
    assert c.tablas("lineups ") == []                      # el previsto jamás cuenta como alineación oficial
    assert len(c.tablas("injuries_capture_log")) == 1


def test_oficial_completo_copia_a_lineups_con_minutos_al_saque():
    c = Conn()
    r = sa.aplicar(c, RECIBO, fila(True), "m1")
    assert r["oficial"] and len(c.tablas("lineups ")) == 2
    assert c.tablas("lineups ")[0][-1] == 50               # 14:00 - 13:10


def test_oficial_incompleto_no_entra_en_lineups():
    c = Conn()
    r = sa.aplicar(c, RECIBO, fila(True, lado(n=10)), "m1")
    assert not r["oficial"] and c.tablas("lineups ") == []


def test_oficial_no_pisa_un_lado_ya_guardado():
    c = Conn(existe={"lineups"})
    sa.aplicar(c, RECIBO, fila(True), "m1")
    assert c.tablas("lineups ") == []


def test_mismo_recibo_dos_veces_no_duplica():
    c = Conn(existe={"previstas"})
    assert sa.aplicar(c, RECIBO, fila(True), "m1") == {"nuevo": False}
    assert c.tablas("injuries ") == []


def candidatos(monkeypatch, partidos, nombres):
    monkeypatch.setattr(sa, "query", lambda q, p=(): partidos)
    monkeypatch.setattr(sa, "_nombres", lambda ids: {i: {n} for i, n in nombres.items()})


def test_empareja_un_unico_partido_programado(monkeypatch):
    p = dict(match_id="gb:1", status="scheduled", home_team_id=1, away_team_id=2)
    candidatos(monkeypatch, [p], {1: "manchester-united", 2: "brighton"})
    assert sa.emparejar(fila()) == ("gb:1", "ok")


def test_partido_ya_empezado_no_se_toca(monkeypatch):
    p = dict(match_id="gb:1", status="finished", home_team_id=1, away_team_id=2)
    candidatos(monkeypatch, [p], {1: "manchester-united", 2: "brighton"})
    assert sa.emparejar(fila()) == (None, "ya_empezado")


def test_competicion_fuera_de_catalogo(monkeypatch):
    assert sa.emparejar({**fila(), "uniqueTournamentId": 999999}) == (None, "competicion_fuera_de_catalogo")


def test_disponibilidad_no_mezcla_ids_de_sofascore_con_los_de_api_football(monkeypatch):
    hoy = [{"player_id": 1000 + i, "src": "sofascore"} for i in range(11)]
    historia = [{"starters": [{"player_id": i} for i in range(11)], "historico": False}] * 4

    def query(sql, params=None):
        if "WHERE l.match_id = %s" in sql:
            return [{"side": "home", "starters": hoy, "home_team_id": 10, "away_team_id": 20}]
        return historia

    monkeypatch.setattr(lineups, "query", query)
    out = lineups.availability("hoy")
    assert out["home"]["missing_regulars"] is None and out["home"]["reason"] == "historia insuficiente"
