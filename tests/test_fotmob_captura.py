import gzip
import io
import json
import urllib.error
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from qf.ingest import fotmob_captura as fc

KICKOFF = datetime(2026, 10, 19, 19, 0, tzinfo=timezone.utc)


def _previo():
    def equipo(coach, base, bajas):
        return {"formation": "4-2-3-1", "totalStarterMarketValue": 200_000_000, "coach": {"id": 1, "name": coach},
                "starters": [{"id": base + i, "name": f"J{i}", "positionId": 11, "marketValue": 1_000_000}
                             for i in range(11)],
                "unavailable": [{"id": base + 90 + i, "name": f"B{i}", "marketValue": 5_000_000,
                                 "unavailability": {"injuryId": 7, "type": "injury", "expectedReturn": "Doubtful"}}
                                for i in range(bajas)]}
    return {"general": {"matchId": "5795484", "started": False, "finished": False},
            "content": {"lineup": {"lineupType": "predicted", "homeTeam": equipo("De Zerbi", 100, 2),
                                   "awayTeam": equipo("Lampard", 200, 1)},
                        "weather": {"temperature": 12, "windSpeed": 2, "relativeHumidity": 81, "precipChance": 7,
                                    "precipitation": 0, "cloudCover": 88, "apiUsed": "forecast",
                                    "lastUpdated": "2026-10-18T13:00:04Z"}}}


def test_ventanas_de_captura():
    assert fc.ventana_de(1440) == "dia" and fc.ventana_de(1000) == "dia"
    assert fc.ventana_de(200) == "horas"
    assert fc.ventana_de(70) == "final" and fc.ventana_de(50) == "final"
    assert fc.ventana_de(40) == "cierre" and fc.ventana_de(25) == "cierre"
    for fuera in (10, 24.9, 46, 49.9, 76, 149, 301, 899, 1561):
        assert fc.ventana_de(fuera) is None


def test_ventana_tarde_se_solapa_con_cierre_y_se_toma_la_primera_pendiente():
    assert fc.ventanas_de(30) == ["cierre", "tarde"] and fc.ventanas_de(40) == ["cierre"]
    assert fc.ventanas_de(33) == ["cierre", "tarde"] and fc.ventanas_de(24) == []
    assert fc.ventana_de(30) == "cierre"


class _Filas:
    def __init__(self, filas):
        self.filas = filas

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None


def test_candidatos_toma_cierre_y_despues_tarde():
    from datetime import datetime, timedelta, timezone
    ahora = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    partido = {"match_id": "m1", "kickoff_utc": ahora + timedelta(minutes=30), "fotmob_match_id": "1", "mins": 30.0}
    hechas = set()

    class C:
        def execute(self, sql, params=None):
            if "FROM matches" in sql:
                return _Filas([partido])
            return _Filas([(1,)] if (params[0], params[1]) in hechas else [])

    assert [x["ventana"] for x in fc.candidatos_previos(C(), ahora)] == ["cierre"]
    hechas.add(("m1", "cierre"))
    assert [x["ventana"] for x in fc.candidatos_previos(C(), ahora)] == ["tarde"]
    hechas.add(("m1", "tarde"))
    assert fc.candidatos_previos(C(), ahora) == []


def test_datos_previo_conserva_pronostico_alineacion_y_bajas():
    d = fc.datos_previo(_previo(), KICKOFF)
    assert d["tipo_alineacion"] == "predicted" and d["clima_api"] == "forecast"
    assert d["clima_prob_precipitacion"] == 7.0 and d["clima_precipitacion"] == 0.0   # 0 es un dato real
    assert d["entrenador_local"] == "De Zerbi" and d["valor_xi_visita"] == 200_000_000
    assert len([j for j in d["jugadores"] if j["titular"]]) == 22
    assert sorted((b["side"], b["jugador_id"]) for b in d["bajas"]) == [("away", 290), ("home", 190), ("home", 191)]
    assert d["clima_actualizado"].isoformat().startswith("2026-10-18T13:00:04")


def test_datos_previo_sin_clima_ni_alineacion_deja_none():
    d = fc.datos_previo({"general": {"matchId": "1"}, "content": {}}, KICKOFF)
    assert d["clima_temperatura_c"] is None and d["clima_prob_precipitacion"] is None
    assert d["tipo_alineacion"] is None and d["jugadores"] == [] and d["bajas"] == []


def test_validar_exige_el_mismo_id():
    assert fc._validar({"general": {"matchId": "5795484"}}, "5795484")
    assert not fc._validar({"general": {"matchId": "999"}}, "5795484")
    assert not fc._validar({}, "5795484")


def _http_error(codigo):
    return urllib.error.HTTPError("https://x", codigo, "err", {}, io.BytesIO(b""))


@pytest.mark.parametrize("codigo", [401, 403, 429])
def test_un_bloqueo_detiene_la_captura_sin_reintentar(codigo):
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=_http_error(codigo)) as op:
        with pytest.raises(fc.AccesoDenegado):
            cli.get("matchDetails", {"matchId": 1})
    assert op.call_count == 1          # nada de insistir contra un bloqueo


def test_un_404_no_es_un_bloqueo():
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=_http_error(404)) as op:
        with pytest.raises(urllib.error.HTTPError):
            cli.get("matchDetails", {"matchId": 1})
    assert op.call_count == 1


class _Resp:
    headers = {"Content-Encoding": "gzip"}

    def __init__(self, cuerpo):
        self.cuerpo = gzip.compress(json.dumps(cuerpo).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.cuerpo


def test_respuesta_valida_incluye_el_original_para_guardarlo():
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", return_value=_Resp({"general": {"matchId": "5"}})):
        d = cli.get("matchDetails", {"matchId": 5})
    assert json.loads(d["__raw__"])["general"]["matchId"] == "5"


# --- respaldo con ZenRows ante un bloqueo de FotMob (28-oct-2026) -------------------------------

class _ZResp:
    """Respuesta de ZenRows: JSON sin comprimir y el coste de la petición en la cabecera."""
    def __init__(self, cuerpo, coste="1"):
        self.cuerpo, self.headers = json.dumps(cuerpo).encode(), {"X-Request-Cost": coste}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.cuerpo


def _con_zenrows(monkeypatch, tmp_path, **extra):
    monkeypatch.setenv("ZENROWS_API_KEY", "k" * 32)
    monkeypatch.setenv("FOTMOB_ZENROWS_ESTADO", str(tmp_path / "estado.json"))
    for k, v in extra.items():
        monkeypatch.setenv(k, str(v))
    return fc.Cliente(espera_s=0)


def _red(zenrows, directo=403):
    """urlopen simulado: FotMob directo da `directo`; ZenRows responde con lo que diga la lista `zenrows`."""
    llamadas = {"fotmob": [], "zenrows": []}

    def urlopen(req, timeout=0):
        url = req.full_url
        if "api.zenrows.com" in url:
            llamadas["zenrows"].append(url)
            r = zenrows.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        llamadas["fotmob"].append(url)
        raise _http_error(directo)
    return urlopen, llamadas


def test_un_bloqueo_se_resuelve_por_zenrows_basico_si_hay_clave(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path)
    red, llamadas = _red([_ZResp({"general": {"matchId": "5"}})])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        d = cli.get("matchDetails", {"matchId": 5})
    assert d["__via__"] == "zenrows" and json.loads(d["__raw__"])["general"]["matchId"] == "5"
    assert len(llamadas["zenrows"]) == 1 and "premium_proxy" not in llamadas["zenrows"][0]
    assert "fotmob.com%2Fapi%2Fdata%2FmatchDetails" in llamadas["zenrows"][0]


def test_zenrows_escala_a_proxy_premium_si_el_basico_falla(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path)
    red, llamadas = _red([_http_error(422), _ZResp({"general": {"matchId": "5"}}, coste="10")])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        d = cli.get("matchDetails", {"matchId": 5})
    assert d["__via__"] == "zenrows"
    assert "premium_proxy" not in llamadas["zenrows"][0] and "premium_proxy=true" in llamadas["zenrows"][1]


def test_tras_un_bloqueo_no_se_insiste_en_directo_durante_la_pausa(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path)
    red, llamadas = _red([_ZResp({"general": {}}), _ZResp({"general": {}})])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        cli.get("matchDetails", {"matchId": 5})
        fc.Cliente(espera_s=0).get("matchDetails", {"matchId": 6})     # otra pasada del cron: el estado persiste
    assert len(llamadas["fotmob"]) == 1 and len(llamadas["zenrows"]) == 2


def test_el_tope_diario_de_creditos_de_zenrows_vuelve_a_ser_un_bloqueo(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path, FOTMOB_ZENROWS_MAX_DIA=1)
    # ZenRows informa el coste en dólares (0,001 = 1 crédito): contar 0 dejaría el tope sin efecto.
    red, llamadas = _red([_ZResp({"general": {}}, coste="0.001"), _ZResp({"general": {}})])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        cli.get("matchDetails", {"matchId": 5})                          # gasta el crédito del día
        with pytest.raises(fc.AccesoDenegado):
            cli.get("matchDetails", {"matchId": 6})
    assert len(llamadas["zenrows"]) == 1


def test_si_zenrows_tampoco_responde_es_un_bloqueo_y_la_clave_no_se_filtra(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path)
    red, _ = _red([_http_error(422), _http_error(422)])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        with pytest.raises(fc.AccesoDenegado) as exc:
            cli.get("matchDetails", {"matchId": 5})
    assert "k" * 32 not in str(exc.value)


def test_un_429_es_limite_de_ritmo_y_no_se_esquiva_con_zenrows(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path)
    red, llamadas = _red([], directo=429)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        with pytest.raises(fc.AccesoDenegado):
            cli.get("matchDetails", {"matchId": 5})
    assert llamadas["zenrows"] == [] and len(llamadas["fotmob"]) == 1


def test_zenrows_apagado_por_configuracion_no_se_usa(monkeypatch, tmp_path):
    cli = _con_zenrows(monkeypatch, tmp_path, FOTMOB_ZENROWS="0")
    red, llamadas = _red([])
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=red):
        with pytest.raises(fc.AccesoDenegado):
            cli.get("matchDetails", {"matchId": 5})
    assert llamadas["zenrows"] == []


def test_correr_pasa_las_opciones_de_relleno_y_respeta_el_enfriamiento():
    from unittest.mock import MagicMock, patch

    c = MagicMock()
    with patch.object(fc, "en_enfriamiento", return_value=False), \
            patch.object(fc, "capturar_posteriores", return_value={"guardados": 0}) as f, \
            patch.object(fc, "_log"):
        fc.correr(c, "posteriores", cli=object(), dias_atras=20, maximo=500)
    assert f.call_args.kwargs == {"dias_atras": 20, "maximo": 500}
    with patch.object(fc, "en_enfriamiento", return_value=True), \
            patch.object(fc, "capturar_posteriores") as f:
        assert "omitido" in fc.correr(c, "posteriores", cli=object())
    f.assert_not_called()


class _Refresco:
    """Conexión falsa de `refrescar_xg`: devuelve los candidatos y anota cada consulta."""

    def __init__(self, filas):
        self.filas, self.sql = filas, []

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split()), params))
        return _Filas(self.filas)

    def commit(self):
        pass


class _Cli:
    def __init__(self, payload):
        self.payload, self.pedidos = payload, []

    def get(self, endpoint, params):
        self.pedidos.append((endpoint, params))
        return self.payload


def test_refrescar_xg_pide_otra_pagina_a_quien_solo_tiene_una_temprana():
    c = _Refresco([{"match_id": "m1", "fotmob_match_id": "9"}])
    cli = _Cli({"general": {"matchId": "9", "finished": True}, "__raw__": b"{}"})
    with patch.object(fc, "_guardar_original", return_value=(1, KICKOFF)) as g:
        r = fc.refrescar_xg(c, cli)
    assert r == {"candidatos": 1, "guardados": 1, "descartados": 0}
    assert cli.pedidos == [("matchDetails", {"matchId": "9"})]
    assert g.call_args.args[1:4] == ("m1", "9", "posterior")       # otra página original; fotmob_partido no se toca
    sql, params = c.sql[0]
    assert "home_xg IS NULL" in sql and "capturado_en >= m.kickoff_utc + %s * interval '1 hour'" in sql
    assert params[2] == fc.XG_MIN_HORAS == 20.0


def test_refrescar_xg_descarta_la_pagina_de_otro_partido_o_sin_terminar():
    c = _Refresco([{"match_id": "m1", "fotmob_match_id": "9"}, {"match_id": "m2", "fotmob_match_id": "10"}])
    cli = _Cli({"general": {"matchId": "9", "finished": False}, "__raw__": b"{}"})
    with patch.object(fc, "_guardar_original") as g:
        r = fc.refrescar_xg(c, cli)
    assert r["guardados"] == 0 and r["descartados"] == 2
    g.assert_not_called()


def test_completar_solo_usa_paginas_tomadas_pasada_la_hora_minima():
    class Registra(_Completar):
        def execute(self, sql, params=None):
            if sql.lstrip().startswith("SELECT"):
                self.consulta = (" ".join(sql.split()), params)
            return super().execute(sql, params)
    c = Registra([_fila("m1", _posterior())])
    fc.completar(c)
    sql, params = c.consulta
    assert "o.capturado_en >= m.kickoff_utc + %s * interval '1 hour'" in sql
    assert params[-1] == 20.0


def _posterior(goles=(2, 1), xg=(1.4, 0.6)):
    items = [{"key": "yellow_cards", "stats": [3, 1]}, {"key": "corners", "stats": [7, 2]}]
    if xg:
        items.append({"key": "expected_goals", "stats": list(xg)})
    return {"general": {"matchId": "9"},
            "header": {"teams": [{"score": goles[0]}, {"score": goles[1]}]},
            "content": {"stats": {"Periods": {"All": {"stats": [{"title": "Top", "stats": items}]}}}}}


class _Completar:
    """Conexión falsa: devuelve las filas pedidas y guarda cada escritura."""

    def __init__(self, filas):
        self.filas, self.escrituras = filas, []

    def execute(self, sql, params=None):
        if sql.lstrip().startswith("SELECT"):
            return _Filas(self.filas)
        self.escrituras.append((sql, params))

        class R:
            rowcount = 1
        return R()

    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()

    def commit(self):
        pass


def _fila(match_id, payload, goles=(2, 1), **ya):
    from qf.ingest.archivo_a_matches import COLUMNAS_MATCHES
    fila = {k: None for k in COLUMNAS_MATCHES}
    fila.update(match_id=match_id, home_goals=goles[0], away_goals=goles[1], home_xg=None, away_xg=None,
                fotmob_match_id="9", capturado_en=KICKOFF, payload_gz=gzip.compress(json.dumps(payload).encode()))
    fila.update(ya)
    return fila


def test_completar_rellena_solo_lo_vacio_con_procedencia_y_xg_de_fotmob():
    c = _Completar([_fila("m1", _posterior(), home_corners=4, away_corners=2)])
    r = fc.completar(c)
    assert r["completados"] == 1 and r["con_xg"] == 1
    update = next(p for s, p in c.escrituras if "COALESCE" in s)
    assert update["home_yellow"] == 3 and update["away_yellow"] == 1
    assert "home_corners" not in update                         # ya tenía dato: no se toca
    xg = next(p for s, p in c.escrituras if "xg_source = 'fotmob'" in s)
    assert xg[:3] == (1.4, 0.6, KICKOFF)                        # hora real de captura de la página
    campos = {p[1] for s, p in c.escrituras if "matches_enriquecimiento" in s}
    assert campos == {"home_yellow", "away_yellow", "stats", "xg"}
    assert update["stats"].obj["home"] == {"amarillas": 3, "corners": 7, "xg": 1.4, "rojas": 0}


def test_completar_no_pisa_stats_de_otra_fuente():
    c = _Completar([_fila("m1", _posterior(), stats={"home": {"faltas": 9}, "away": {"faltas": 8}})])
    fc.completar(c)
    update = next(p for s, p in c.escrituras if "COALESCE" in s)
    assert "stats" not in update


def test_completar_no_aplica_con_marcador_distinto_ni_inventa_xg():
    c = _Completar([_fila("m1", _posterior(goles=(0, 0))), _fila("m2", _posterior(xg=None), home_xg=1.1, away_xg=0.3)])
    r = fc.completar(c)
    assert r["conflicto_marcador"] == 1 and r["con_xg"] == 0
    assert not any("xg_source" in s for s, _ in c.escrituras)
    assert all(p.get("match_id") != "m1" for s, p in c.escrituras if "COALESCE" in s)


def test_completar_espera_36_horas_desde_el_saque():
    c = _Completar([])
    vistos = []
    c.execute = lambda sql, params=None: vistos.append(params) or _Filas([])
    fc.completar(c)
    desde, hasta, horas_min_xg = vistos[0]
    assert horas_min_xg == 20.0
    assert (datetime.now(timezone.utc) - hasta).total_seconds() >= 36 * 3600 - 5


def test_referencias_no_pide_competiciones_retiradas():
    from qf.league_policy import RETIRED_LEAGUES

    pedidas = []

    class Cli:
        def get(self, endpoint, params):
            pedidas.append(params["id"])
            return {"fixtures": {"allMatches": []}}

    class C:
        def execute(self, sql, params=None):
            return iter([])

        def commit(self):
            pass

    fc.actualizar_referencias(C(), Cli())
    retiradas = {fc.COMPETITIONS[l][0] for l in RETIRED_LEAGUES if l in fc.COMPETITIONS}
    assert pedidas and not retiradas & set(pedidas)


def test_completar_no_depende_del_enfriamiento_porque_no_pide_nada():
    from unittest.mock import MagicMock

    with patch.object(fc, "en_enfriamiento", return_value=True), \
            patch.object(fc, "completar", return_value={"completados": 0}) as f, patch.object(fc, "_log"):
        assert fc.correr(MagicMock(), "completar", cli=object()) == {"completados": 0}
    f.assert_called_once()


def _final(razon="FT", local=8226, visita=9748, goles=(3, 0)):
    return {"general": {"matchId": "6112350", "finished": True},
            "header": {"status": {"finished": True, "cancelled": False, "awarded": False, "reason": {"short": razon}},
                       "teams": [{"id": local, "score": goles[0]}, {"id": visita, "score": goles[1]}]},
            "content": {"stats": {"Periods": {"All": {"stats": [{"title": "Top", "stats": [
                {"key": "corners", "stats": [6, 4]}]}]}}}}}


class _Huerfanos:
    """Conexión falsa para el respaldo de resultados."""

    def __init__(self):
        from qf.ingest.archivo_a_matches import COLUMNAS_MATCHES
        self.escrituras = []
        self.partido = {"match_id": "eu.uel:hoffenheim-lyon", "kickoff_utc": KICKOFF, "home_team_id": 61452,
                        "away_team_id": 68872, "fotmob_match_id": "6112350"}
        self.actual = {k: None for k in COLUMNAS_MATCHES}
        self.actual.update(match_id="eu.uel:hoffenheim-lyon", home_goals=3, away_goals=0, home_xg=None, away_xg=None)

    def execute(self, sql, params=None):
        if "JOIN fotmob_referencia" in sql:
            return _Filas([self.partido])
        if "FROM fotmob_equipo" in sql:
            return _Filas([{"fotmob_team_id": 8226, "team_id": 61452}, {"fotmob_team_id": 9748, "team_id": 68872}])
        if "INSERT INTO fotmob_original" in sql:
            return _Filas([{"id": 1, "capturado_en": KICKOFF}])
        if sql.lstrip().startswith("SELECT m.match_id, m.home_goals"):
            return _Filas([self.actual])
        self.escrituras.append((sql, params))

        class R:
            rowcount = 1
        return R()

    def cursor(self):
        from contextlib import nullcontext
        return nullcontext(None)

    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()

    def commit(self):
        pass


def _cli(payload):
    class Cli:
        def get(self, endpoint, params):
            return {**payload, "__raw__": json.dumps(payload).encode()}
    return Cli()


def test_resultados_cierra_con_fotmob_y_liquida():
    c = _Huerfanos()
    with patch.object(fc.fm, "insertar"), patch("qf.eval.clv.settle_pending", return_value={"picks": 1}) as liq, \
            patch("qf.ingest.api_football.record_health"):
        r = fc.cerrar_huerfanos(c, _cli(_final()))
    assert r["cerrados"] == 1 and r["settled"] == {"picks": 1}
    cierre = next(p for s, p in c.escrituras if "status = 'finished'" in s)
    assert cierre[:3] == (3, 0, "6112350")
    liq.assert_called_once()
    corners = next(p for s, p in c.escrituras if "COALESCE" in s)
    assert (corners["home_corners"], corners["away_corners"]) == (6, 4)


@pytest.mark.parametrize("payload,motivo", [(_final(razon="AET"), "abiertos"), (_final(razon="Pen"), "abiertos"),
                                            (_final(local=9748, visita=8226), "equipos_distintos")])
def test_resultados_no_cierra_prorroga_penaltis_ni_equipos_cambiados(payload, motivo):
    c = _Huerfanos()
    with patch.object(fc.fm, "insertar"), patch("qf.eval.clv.settle_pending") as liq, \
            patch("qf.ingest.api_football.record_health"):
        r = fc.cerrar_huerfanos(c, _cli(payload))
    assert r[motivo] == 1 and r["cerrados"] == 0
    assert not any("status = 'finished'" in s for s, _ in c.escrituras)
    liq.assert_not_called()


def test_marcador_final_rechaza_valores_raros():
    assert fc._marcador_final(_final()) == (3, 0)
    assert fc._marcador_final(_final(goles=(True, 0))) is None
    assert fc._marcador_final(_final(goles=("3", 0))) is None
    p = _final()
    p["header"]["status"]["cancelled"] = True
    assert fc._marcador_final(p) is None
