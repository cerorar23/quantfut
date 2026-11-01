import json
from datetime import datetime, timezone

from qf.ingest import tenis_equivalencias as te

T0 = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
TS = int(datetime(2026, 10, 30, 14, tzinfo=timezone.utc).timestamp())


def jugador(i, corto, nombre):
    return {"id": i, "shortName": corto, "name": nombre}


def evento_ss(i, local, visita, torneo="Basel", categoria="ATP"):
    return {"id": i, "startTimestamp": TS, "homeTeam": local, "awayTeam": visita,
            "tournament": {"name": torneo, "category": {"name": categoria}, "uniqueTournament": {"id": 2400}}}


def evento_at(k, a, ka, b, kb, tipo="Atp Singles", hora="14:30"):
    return {"event_key": k, "event_date": "2026-10-30", "event_time": hora, "event_first_player": a,
            "first_player_key": ka, "event_second_player": b, "second_player_key": kb, "event_type_type": tipo,
            "tournament_key": 1700, "tournament_name": "Basel"}


def test_nombres_con_guion_e_iniciales_distintas_son_el_mismo_jugador():
    assert te.mismo_jugador("J-L. Struff", "J. Struff")
    assert te.mismo_jugador("K. Rakhimova", "K. Rakhimova")
    assert not te.mismo_jugador("A. Zverev", "M. Zverev")
    assert not te.mismo_jugador("Struff", "J. Struff")  # sin inicial no basta


def test_empareja_con_candidato_unico_en_cualquier_orientacion():
    ss = [evento_ss(1, jugador(10, "J. Struff", "Jan-Lennard Struff"), jugador(11, "N. Borges", "Nuno Borges"))]
    pares = te.emparejar([evento_at(5, "N. Borges", 77, "J-L. Struff", 78)], ss)
    assert len(pares) == 1 and pares[0][2] is False  # el local de SofaScore es el segundo de API-Tennis


def test_ambiguo_o_fuera_de_ventana_no_empareja():
    a, b = jugador(10, "J. Struff", "J Struff"), jugador(11, "N. Borges", "N Borges")
    assert te.emparejar([evento_at(5, "J. Struff", 78, "N. Borges", 77)],
                        [evento_ss(1, a, b), evento_ss(2, a, b)]) == []
    viejo = dict(evento_ss(3, a, b), startTimestamp=TS - 5 * 86400)
    assert te.emparejar([evento_at(5, "J. Struff", 78, "N. Borges", 77)], [viejo]) == []


class FakeHttp:
    def __init__(self, eventos):
        self.urls, self.eventos = [], eventos

    def __call__(self, url, key, timeout=60):
        self.urls.append(url)
        return 200, json.dumps({"success": True, "events": self.eventos}).encode()


def preparar(tmp_path, eventos_at):
    raiz, api = tmp_path / "eq", tmp_path / "at"
    (api / "r1").mkdir(parents=True)
    (api / "r1" / "response.json").write_text(json.dumps({"result": eventos_at}), encoding="utf-8")
    eventos = [evento_ss(1, jugador(10, "J. Struff", "Jan-Lennard Struff"), jugador(11, "N. Borges", "Nuno Borges")),
               evento_ss(2, jugador(20, "A. Doble", "A Doble"), jugador(21, "B. Doble", "B Doble"), "Basel, Doubles"),
               evento_ss(3, jugador(30, "X. Chall", "X Chall"), jugador(31, "Y. Chall", "Y Chall"), "Challenger", "Challenger")]
    f = FakeHttp(eventos)
    return raiz, api, f


def test_la_peticion_no_lleva_el_user_agent_de_urllib(monkeypatch):
    visto = {}

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(te.urllib.request, "urlopen", lambda req, timeout=0: visto.update(h=dict(req.header_items())) or R())
    te.http("https://x/y", "clave")
    assert "urllib" not in visto["h"]["User-agent"].lower() and visto["h"]["X-api-key"] == "clave"


def test_captura_tres_fechas_y_archiva_con_recepcion_real(tmp_path):
    raiz, api, f = preparar(tmp_path, [])
    hechos = te.capture(raiz, "k", call=f, clock=lambda: T0)
    assert [h[0] for h in hechos] == ["2026-10-30", "2026-10-31", "2026-11-01"]
    assert [u.rsplit("/", 1)[1] for u in f.urls] == ["2026-10-30", "2026-10-31", "2026-11-01"]
    db = te.connect(raiz)
    assert db.execute("SELECT received_at FROM receipts").fetchone()[0] == T0.isoformat()
    try:
        db.execute("DELETE FROM receipts")
        assert False
    except Exception as exc:
        assert "immutable" in str(exc)


def test_match_llena_la_tabla_una_sola_vez_y_ignora_dobles_y_challenger(tmp_path):
    raiz, api, f = preparar(tmp_path, [evento_at(5, "J-L. Struff", 78, "N. Borges", 77),
                                       evento_at(6, "A. Doble", 90, "B. Doble", 91, "Atp Doubles"),
                                       evento_at(7, "X. Chall", 92, "Y. Chall", 93)])
    te.capture(raiz, "k", call=f, clock=lambda: T0)
    assert te.match(raiz, api, clock=lambda: T0)["emparejados_nuevos"] == 1
    db = te.connect(raiz)
    assert {(r[0], r[1]) for r in db.execute("SELECT player_key, sofascore_id FROM equivalencias")} == {(78, 10), (77, 11)}
    assert te.match(raiz, api, clock=lambda: T0)["emparejados_nuevos"] == 0  # ya emparejado
    assert db.execute("SELECT partidos FROM equivalencias WHERE player_key=78").fetchone()[0] == 1
    s = te.status(raiz)
    assert s["jugadores"] == 2 and s["player_key_con_varios_ids"] == 0


def test_guarda_orientacion_y_torneo_y_rehace_los_antiguos_sin_duplicar_jugadores(tmp_path):
    raiz, api, f = preparar(tmp_path, [evento_at(5, "N. Borges", 77, "J-L. Struff", 78)])
    te.capture(raiz, "k", call=f, clock=lambda: T0)
    te.match(raiz, api, clock=lambda: T0)
    db = te.connect(raiz)
    r = db.execute("SELECT first_key, second_key, directo, tournament_key, utid FROM partidos_emparejados").fetchone()
    assert tuple(r) == (77, 78, 0, 1700, 2400)                       # el local de SofaScore es el segundo
    assert tuple(db.execute("SELECT tournament_key, utid, partidos FROM torneos").fetchone()) == (1700, 2400, 1)
    with db:                                                          # fila antigua, de antes de guardar la orientación
        db.execute("UPDATE partidos_emparejados SET first_key=NULL")
    assert te.match(raiz, api, clock=lambda: T0)["emparejados_nuevos"] == 0
    assert db.execute("SELECT first_key FROM partidos_emparejados").fetchone()[0] == 77
    assert db.execute("SELECT partidos FROM equivalencias WHERE player_key=77").fetchone()[0] == 1
