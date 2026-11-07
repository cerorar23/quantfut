"""ResolutorMultifuente sobre un esquema aislado: casos absurdos, idempotencia, anulación, contexto y cola."""
from datetime import date, timedelta

import pytest

from db_util import insertar, nuevo_recibo, ts
from tenis.identidad import cola
from tenis.identidad.resolver import ResolutorMultifuente, cargar_equivalencias

F = date(2022, 3, 1)                      # fecha de los partidos de TML en estas pruebas
RECIBIDO = "2026-01-05"


def _nac(edad: float, fecha: date = F) -> str:
    """Fecha de nacimiento que da esa edad en `fecha` (para la fuente que llega)."""
    return (fecha - timedelta(days=round(edad * 365.25))).isoformat()


def _tml(db, circuito, id_, nombre, pais, edades=()):
    """Jugador de TML ya cargado: alias 'tml', nombre y país. Devuelve (jugador_id, edades) para el proveedor."""
    rid = nuevo_recibo(db, "tml", RECIBIDO, retro=True)
    jid = insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) RETURNING jugador_id",
                   (circuito, rid, ts(RECIBIDO)))
    db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
               "VALUES ('tml', %s, %s, 'id_exacto', %s, %s)", (id_, jid, rid, ts(RECIBIDO)))
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 'nombre', %s, 'tml', %s, %s)", (jid, nombre, rid, ts(RECIBIDO)))
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 'pais', %s, 'tml', %s, %s)", (jid, pais, rid, ts(RECIBIDO)))
    return jid, [(F, e) for e in edades]


def _proveedor(*pares):
    """Proveedor de edades de TML: pares (jugador_id, [(fecha, edad)])."""
    mapa = {jid: datos for jid, datos in pares}
    return lambda jid: mapa.get(jid, ())


def _llamar(r, rid, **kw):
    base = dict(fuente="sofascore", id_fuente="s1", circuito="atp", nombre="Carlos Alcaraz",
                fecha_nacimiento=_nac(18.0), pais="ESP", mano=None, altura_cm=None,
                recibo_id=rid, recibido_en=ts(RECIBIDO), contexto=None)
    base.update(kw)
    return r.resolver(**base)


def _motivo(db, id_fuente="s1"):
    return [f[0] for f in db.execute("SELECT motivo FROM sin_resolver WHERE id_fuente = %s ORDER BY sin_id",
                                     (id_fuente,)).fetchall()]


@pytest.fixture
def base(esquema):
    db = esquema.conectar()
    return db, nuevo_recibo(db, "sofascore", RECIBIDO)


# ---- casos absurdos ----------------------------------------------------------------------------------------
def test_mismo_nombre_y_pais_distinto_no_se_unen(base):
    db, rid = base
    tml, _ = _tml(db, "atp", "T1", "Carlos Alcaraz", "ESP")
    r = ResolutorMultifuente(db, edades=_proveedor((tml, [(F, 18.0)])))
    jid = _llamar(r, rid, pais="FRA")
    assert jid != tml
    assert _motivo(db) == ["confirmado_distinto"]


def test_mismo_nombre_y_pais_con_edades_15_y_35_no_se_unen(base):
    db, rid = base
    tml, datos = _tml(db, "atp", "T2", "Pedro Gomez", "ESP", edades=[15.0])
    r = ResolutorMultifuente(db, edades=_proveedor((tml, datos)))
    jid = _llamar(r, rid, nombre="Pedro Gomez", fecha_nacimiento=_nac(35.0))
    assert jid != tml
    assert _motivo(db) == ["edad_contradictoria"]


def test_nombre_sin_pais_no_se_une_por_nombre(base):
    db, rid = base
    tml, datos = _tml(db, "atp", "T3", "Carlos Alcaraz", "ESP", edades=[18.0])
    r = ResolutorMultifuente(db, edades=_proveedor((tml, datos)))
    jid = _llamar(r, rid, pais=None)
    assert jid != tml
    assert _motivo(db) == ["sin_pais"]


def test_sin_fecha_de_nacimiento_no_se_une_por_edad(base):
    db, rid = base
    tml, datos = _tml(db, "atp", "T4", "Luis Diaz", "ESP", edades=[25.0])
    r = ResolutorMultifuente(db, edades=_proveedor((tml, datos)))
    jid = _llamar(r, rid, nombre="Luis Diaz", fecha_nacimiento=None)
    assert jid != tml
    assert _motivo(db) == ["sin_edad"]


def test_dos_candidatos_igual_de_buenos_es_ambiguo(base):
    db, rid = base
    a, da = _tml(db, "atp", "T5", "Ana Ruiz", "ESP", edades=[20.0])
    b, dbb = _tml(db, "atp", "T6", "Ana Ruiz", "ESP", edades=[20.0])
    r = ResolutorMultifuente(db, edades=_proveedor((a, da), (b, dbb)))
    jid = _llamar(r, rid, nombre="Ana Ruiz", fecha_nacimiento=_nac(20.0))
    assert jid not in (a, b)
    assert _motivo(db) == ["ambiguo"]


def test_fuente_desconocida_es_error(base):
    db, rid = base
    with pytest.raises(ValueError, match="fuente desconocida"):
        _llamar(ResolutorMultifuente(db), rid, fuente="nadie")


def test_circuito_desconocido_es_error(base):
    db, rid = base
    with pytest.raises(ValueError, match="circuito"):
        _llamar(ResolutorMultifuente(db), rid, circuito="itf")


# ---- uniones correctas --------------------------------------------------------------------------------------
@pytest.mark.parametrize("nombre_tml, pais, nombre_fuente", [
    ("Carlos Alcaraz", "ESP", "Alcaraz C."),
    ("Carlos Alcaraz", "ESP", "Carlos Alcaraz"),
    ("Alexandre Müller", "FRA", "Muller Alexandre"),
    ("Felix Auger-Aliassime", "CAN", "Auger-Aliassime F."),
    ("Christopher O'Connell", "AUS", "O'Connell C."),
    ("Roberto Carreño Busta", "ESP", "Carreno Busta R."),
    ("Alex De Minaur", "AUS", "De Minaur A."),
    ("Alex De Minaur", "AUS", "Alex de Minaur"),
])
def test_union_por_nombre_fecha_nac_con_formatos(base, nombre_tml, pais, nombre_fuente):
    db, rid = base
    tml, datos = _tml(db, "atp", "T9", nombre_tml, pais, edades=[18.0, 18.0])
    r = ResolutorMultifuente(db, edades=_proveedor((tml, datos)))
    jid = _llamar(r, rid, nombre=nombre_fuente, pais=pais, fecha_nacimiento=_nac(18.0))
    assert jid == tml
    assert r.ultimo == ("nombre_fecha_nac", None)
    alias = db.execute("SELECT metodo FROM jugador_alias WHERE fuente = 'sofascore' AND id_fuente = 's1'").fetchall()
    assert alias == [("nombre_fecha_nac",)]
    fecha = db.execute("SELECT valor FROM jugador_asercion WHERE jugador_id = %s AND campo = 'fecha_nacimiento' "
                       "AND fuente = 'sofascore'", (tml,)).fetchall()
    assert len(fecha) == 1


def test_contexto_del_partido_une_cuando_el_nombre_no_decide(base):
    db, rid = base
    # Mundo mínimo: el partido de prueba enfrenta a los jugadores a y b en la edición 2026-03-02.
    from db_util import cargar_minimo
    mundo = cargar_minimo(db)
    a, b = mundo["jugadores"][0], mundo["jugadores"][1]
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 'nombre', 'Jan Novak', 'tml', %s, %s)", (a, rid, ts(RECIBIDO)))
    r = ResolutorMultifuente(db)
    jid = _llamar(r, rid, nombre="Novak J.", pais=None, fecha_nacimiento=None,
                  contexto={"rival_jugador_id": b, "fecha": "2026-03-04"})
    assert jid == a
    assert r.ultimo == ("contexto_partido", None)


def test_contexto_fuera_de_la_ventana_no_une(base):
    db, rid = base
    from db_util import cargar_minimo
    mundo = cargar_minimo(db)
    a, b = mundo["jugadores"][0], mundo["jugadores"][1]
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 'nombre', 'Jan Novak', 'tml', %s, %s)", (a, rid, ts(RECIBIDO)))
    r = ResolutorMultifuente(db)
    jid = _llamar(r, rid, nombre="Novak J.", pais=None, fecha_nacimiento=None,
                  contexto={"rival_jugador_id": b, "fecha": "2026-06-01"})
    assert jid != a


def test_manual_une_a_la_equivalencia(base, tmp_path):
    db, rid = base
    r0 = ResolutorMultifuente(db)
    principal = _llamar(r0, rid, id_fuente="X0", nombre="Pepe Roca", pais="ESP", fecha_nacimiento=None)
    ruta = tmp_path / "eq.csv"
    ruta.write_text("fuente,id_alias,id_principal,evidencia\nsofascore,X1,X0,revisado a mano\n", encoding="utf-8")
    r = ResolutorMultifuente(db, equivalencias=cargar_equivalencias(ruta))
    jid = _llamar(r, rid, id_fuente="X1", nombre="Otro Nombre", pais="ESP", fecha_nacimiento=None)
    assert jid == principal
    assert r.ultimo == ("manual", None)


# ---- idempotencia y anulación -------------------------------------------------------------------------------
def _conteos(db):
    return tuple(db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                 for t in ("jugador", "jugador_alias", "jugador_asercion", "sin_resolver"))


def test_resolver_dos_veces_no_añade_filas(base):
    db, rid = base
    tml, datos = _tml(db, "atp", "T10", "Carlos Alcaraz", "ESP", edades=[18.0])
    prov = _proveedor((tml, datos))
    _llamar(ResolutorMultifuente(db, edades=prov), rid)                       # unión
    _llamar(ResolutorMultifuente(db, edades=prov), rid, id_fuente="s2", nombre="Nadie Raro", pais="ESP",
            fecha_nacimiento=None)                                              # nuevo + sin_resolver
    antes = _conteos(db)
    _llamar(ResolutorMultifuente(db, edades=prov), rid)
    _llamar(ResolutorMultifuente(db, edades=prov), rid, id_fuente="s2", nombre="Nadie Raro", pais="ESP",
            fecha_nacimiento=None)
    assert _conteos(db) == antes


def test_cola_es_idempotente(base):
    db, rid = base
    with db.cursor() as cur:
        assert cola.registrar(cur, fuente="sofascore", id_fuente="z1", nombre="Z", motivo="ambiguo",
                              contexto={}, recibo_id=rid, recibido_en=ts(RECIBIDO)) is True
        assert cola.registrar(cur, fuente="sofascore", id_fuente="z1", nombre="Z", motivo="ambiguo",
                              contexto={}, recibo_id=rid, recibido_en=ts(RECIBIDO)) is False
        assert len(cola.leer(cur, motivo="ambiguo")) == 1
        with pytest.raises(ValueError, match="motivo"):
            cola.registrar(cur, fuente="sofascore", id_fuente="z2", nombre="Z", motivo="inventado",
                           contexto={}, recibo_id=rid, recibido_en=ts(RECIBIDO))


def test_anulacion_de_alias_visible_en_lectura_pit(base):
    db, rid = base
    a, da = _tml(db, "atp", "T11", "Carlos Alcaraz", "ESP", edades=[18.0])
    b, db_ = _tml(db, "atp", "T12", "Otro Tenista", "ESP", edades=[30.0])
    prov = _proveedor((a, da), (b, db_))
    assert _llamar(ResolutorMultifuente(db, edades=prov), rid) == a
    r = ResolutorMultifuente(db, edades=prov)
    r.anular(fuente="sofascore", id_fuente="s1", jugador_id=b, recibo_id=rid, recibido_en=ts(RECIBIDO))
    vigente = db.execute("SELECT jugador_id FROM jugador_alias_a_las(%s) WHERE fuente = 'sofascore' "
                         "AND id_fuente = 's1'", (ts("2099-01-01"),)).fetchall()
    assert vigente == [(b,)]
    assert db.execute("SELECT count(*) FROM jugador_alias WHERE fuente = 'sofascore' AND id_fuente = 's1'"
                      ).fetchone()[0] == 2                                      # nada se borra
    assert ResolutorMultifuente(db, edades=prov).resolver(
        fuente="sofascore", id_fuente="s1", circuito="atp", nombre="Carlos Alcaraz", fecha_nacimiento=_nac(18.0),
        pais="ESP", mano=None, altura_cm=None, recibo_id=rid, recibido_en=ts(RECIBIDO)) == b


# ---- equivalencias ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("contenido, mensaje", [
    ("fuente,id_alias,id_principal,evidencia\ntml,A,A,x\n", "circular"),
    ("fuente,id_alias,id_principal,evidencia\ntml,A,B,x\ntml,B,C,x\n", "cadena"),
    ("fuente,id_alias,id_principal,evidencia\ntml,A,B,x\ntml,B,A,x\n", "cadena"),
    ("fuente,id_alias,id_principal,evidencia\ntml,A,B,\n", "sin evidencia"),
    ("fuente,id_alias,id_principal,evidencia\ntml,A,B,x\ntml,A,C,x\n", "duplicado"),
])
def test_equivalencias_mal_formadas_son_error(tmp_path, contenido, mensaje):
    ruta = tmp_path / "eq.csv"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(ValueError, match=mensaje):
        cargar_equivalencias(ruta)


# ---- países: COI (TML) frente a ISO alpha-3 (SofaScore) -----------------------------------------------------------
def test_los_codigos_del_coi_y_del_iso_son_el_mismo_pais(base):
    """Medido con datos reales: 132 de 860 jugadores (15 %) salían «de otro país» solo por GER/DEU, SUI/CHE, CRO/HRV…"""
    db, rid = base
    tml, _ = _tml(db, "atp", "T1", "Alexander Zverev", "GER")           # TML: código del COI
    r = ResolutorMultifuente(db, edades=_proveedor((tml, [(F, 18.0)])))
    jid = _llamar(r, rid, nombre="Alexander Zverev", pais="DEU")        # SofaScore: ISO alpha-3
    assert jid == tml
    assert _motivo(db) == []


@pytest.mark.parametrize("coi,iso", [("GER", "DEU"), ("SUI", "CHE"), ("CRO", "HRV"), ("NED", "NLD"), ("BUL", "BGR"),
                                     ("POR", "PRT"), ("TPE", "TWN"), ("GRE", "GRC"), ("DEN", "DNK"), ("CHI", "CHL"),
                                     ("SLO", "SVN"), ("LAT", "LVA"), ("RSA", "ZAF"), ("INA", "IDN"), ("PAR", "PRY")])
def test_el_mapa_coi_a_iso_cubre_los_casos_medidos(coi, iso):
    from tenis.identidad.paises import iso3
    assert iso3(coi) == iso and iso3(iso) == iso


def test_codigos_ya_iso_o_desconocidos_no_se_inventan():
    from tenis.identidad.paises import iso3
    assert iso3("esp") == "ESP" and iso3("USA") == "USA" and iso3("  ") is None and iso3(None) is None


def test_homonimos_de_paises_realmente_distintos_siguen_separados(base):
    """Con el mapa, GER y FRA siguen siendo países distintos: el homónimo de otro país no se une."""
    db, rid = base
    tml, _ = _tml(db, "atp", "T1", "Alexander Zverev", "GER")
    r = ResolutorMultifuente(db, edades=_proveedor((tml, [(F, 18.0)])))
    jid = _llamar(r, rid, nombre="Alexander Zverev", pais="FRA")
    assert jid != tml
    assert _motivo(db) == ["confirmado_distinto"]
