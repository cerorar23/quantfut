"""Casillas por receta, comprobación de cifras y bloque `analisis` del destacado de fútbol (sin base ni red)."""
from qf.api import analisis_futbol as af


def bloque(n=10, **kw):
    base = {"n": n, "goles_favor": 1.5, "goles_contra": 1.0, "xg_favor": 1.6, "xg_contra": 1.1,
            "pct_victorias": 60.0, "pct_empates": 15.0, "pct_marca": 90.0, "pct_ambos_marcan": 55.0,
            "pct_mas_2_5": 52.0}
    return {**base, **kw}


def ficha(**kw):
    def equipo(nombre, casa, fuera, puntos=11):
        return {"nombre": nombre, "forma": {"resumen": {"puntos": puntos, "n": 5}},
                "promedios": {"todos": bloque(), "casa": casa, "fuera": fuera}}
    f = {"local": equipo("Albacete", bloque(5), bloque(5), 13),
         "visitante": equipo("Celta II", bloque(5), bloque(5, pct_empates=10.0), 8),
         "partido": {"liga": {"pct_empates": 28.0}}}
    f.update(kw)
    return f


def pick(market="double_chance", **kw):
    return {"market": market, "selection": "12", "line": None, "texto": "Albacete o Celta II (sin empate)",
            "prob": 0.78, "ref_price": 1.23, **kw}


def test_resultado_prioriza_xg_empate_y_forma():
    receta, cs = af.casillas(pick(), ficha(), (1.6, 0.9, 0.0))
    assert receta == "resultado"
    assert [c["id"] for c in cs] == ["xg", "empate", "forma"]
    assert cs[0]["total"] == 2.5 and cs[1]["liga"] == 28 and cs[1]["b"] == 10


def test_sin_xg_la_casilla_no_queda_vacia_sino_que_sube_la_siguiente():
    _, cs = af.casillas(pick(), ficha(), None)
    assert [c["id"] for c in cs] == ["empate", "forma", "xgd"]


def test_goles_usa_tendencia_solo_en_la_linea_2_5():
    _, cs = af.casillas(pick("totals", line=2.5), ficha(), (1.6, 1.4, 0.0))
    assert [c["id"] for c in cs] == ["xg", "tendencia", "ambos"]
    _, cs = af.casillas(pick("totals", line=3.5), ficha(), (1.6, 1.4, 0.0))
    assert "tendencia" not in [c["id"] for c in cs]


def test_equipo_toma_la_proyeccion_del_equipo_del_mercado():
    receta, cs = af.casillas(pick("team_totals_away"), ficha(), (1.6, 0.9, 0.0))
    assert receta == "equipo" and cs[0] == {"id": "xg_equipo", "a": 0.9, "equipo": "b"}


def test_mercado_sin_receta_usa_el_dato_generico():
    receta, cs = af.casillas(pick("corners"), ficha(), (1.6, 0.9, 0.0))
    assert receta == "general" and [c["id"] for c in cs][:2] == ["locvis", "forma"]


def test_pocos_partidos_no_dan_porcentaje():
    f = ficha()
    f["local"]["promedios"]["casa"] = bloque(2)
    _, cs = af.casillas(pick(), f, (1.6, 0.9, 0.0))
    assert "empate" not in [c["id"] for c in cs]


def test_cifras_validas_acepta_los_datos_y_rechaza_ajenos():
    h = af.hechos_de(pick(), ficha(), "resultado", [{"id": "empate", "a": 15, "b": 10, "liga": 28}])
    assert af.cifras_validas("Hay un 78 % de probabilidad. 1X2.", h)
    assert "cuota_justa" not in h and "cuota_publicada" not in h and "precio" not in h
    assert not af.cifras_validas("La cuota (1,23) queda bajo la justa (1,28).", h)
    assert af.cifras_validas("Empata el 15 % en casa y el 10 % fuera frente al 28 % de la liga.", h)
    assert af.cifras_validas("Se esperan más de 2,5 goles.", af.hechos_de(pick("totals", line=2.5, texto="Más de 2,5 goles"), ficha(), "goles", []))
    assert not af.cifras_validas("Tiene un 91 % de probabilidad.", h)
    assert not af.cifras_validas("La cuota justa es 1,50.", h)


def test_construir_devuelve_resumen_guardado_y_no_llama_a_la_ia(monkeypatch):
    lanzado = []
    monkeypatch.setattr(af, "_leer", lambda *a: {"es": "texto"})
    monkeypatch.setattr(af, "_config", lambda: {"api_key": "x", "base_url": "u", "model": "m"})
    monkeypatch.setattr(af._POOL, "submit", lambda *a: lanzado.append(a))
    out = af.construir("m1", pick(), ficha(), (1.6, 0.9, 0.0))
    assert out["resumen"] == {"es": "texto"} and not lanzado


def test_construir_sin_resumen_lo_genera_fuera_de_la_peticion_una_sola_vez(monkeypatch):
    lanzado = []
    monkeypatch.setattr(af, "_leer", lambda *a: None)
    monkeypatch.setattr(af, "_config", lambda: {"api_key": "x", "base_url": "u", "model": "m"})
    monkeypatch.setattr(af._POOL, "submit", lambda *a: lanzado.append(a))
    af._en_curso.clear(); af._fallos.clear()
    assert af.construir("m2", pick(), ficha(), (1.6, 0.9, 0.0))["resumen"] is None
    af.construir("m2", pick(), ficha(), (1.6, 0.9, 0.0))
    assert len(lanzado) == 1


def test_construir_sin_clave_de_apimart_no_genera(monkeypatch):
    lanzado = []
    monkeypatch.setattr(af, "_leer", lambda *a: None)
    monkeypatch.setattr(af, "_config", lambda: None)
    monkeypatch.setattr(af._POOL, "submit", lambda *a: lanzado.append(a))
    af._en_curso.clear()
    assert af.construir("m3", pick(), ficha(), None)["casillas"] and not lanzado


def test_redactar_descarta_el_resumen_si_un_idioma_trae_cifras_ajenas(monkeypatch):
    monkeypatch.setattr(af, "_config", lambda: {"api_key": "x", "base_url": "u", "model": "m"})
    buenos = {k: "Un 78 % de probabilidad." for k in af.IDIOMAS}
    monkeypatch.setattr(af.apimart, "_chat_completion", lambda **k: {"content": __import__("json").dumps(buenos)})
    h = af.hechos_de(pick(), ficha(), "resultado", [])
    assert af.redactar(h) == buenos
    malos = {**buenos, "fr": "Un 91 % de probabilité."}
    monkeypatch.setattr(af.apimart, "_chat_completion", lambda **k: {"content": __import__("json").dumps(malos)})
    assert af.redactar(h) is None


def test_significado_deja_claro_el_pronostico_sin_ambiguedad_de_idioma():
    f = ficha()
    assert "NO draw" in af.significado(pick("double_chance", selection="12"), "Albacete", "Celta II")
    assert "Albacete wins or the match is drawn" in af.significado(pick("double_chance", selection="1X"), "Albacete", "Celta II")
    assert af.significado(pick("totals", selection="over", line=2.5), "A", "B") == "More than 2.5 total goals in the match"
    assert af.significado(pick("btts", selection="no"), "A", "B") == "At least one of the teams does not score"
    assert af.significado(pick("spreads", selection="home", line=0.0), "A", "B") == "A wins (a draw returns the stake)"
    assert af.significado(pick("corners", selection="over", line=9.5), "A", "B") is None
    h = af.hechos_de(pick("double_chance", selection="12"), f, "resultado", [])
    assert "NO draw" in h["significado"]
    assert af.cifras_validas("Un 78 % de probabilidad de que no haya empate.", h)
