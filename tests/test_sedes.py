from qf.ingest.sedes import decidir

NUEVO = {"name": "Estadio Banorte", "city": "Ciudad de México", "lat": 19.3029, "lon": -99.1505}


def _e(i, name, city, lat, lon):
    return {"stadium_id": i, "name": name, "city": city, "lat": lat, "lon": lon}


def test_reutiliza_el_estadio_con_otro_nombre_si_esta_en_las_mismas_coordenadas():
    existentes = [_e(1, "Estadio Azteca", "Ciudad de México (D.F.)", 19.3030, -99.1504)]
    assert decidir(existentes, NUEVO) == 1                      # mismo recinto renombrado


def test_prefiere_el_mismo_nombre_aunque_otro_este_mas_cerca():
    existentes = [_e(1, "Otro Recinto", "X", 19.3029, -99.1505), _e(2, "Estadio Banorte", "Ciudad de México", 19.3040, -99.1510)]
    assert decidir(existentes, NUEVO) == 2


def test_lejos_o_vacio_da_de_alta_uno_nuevo():
    assert decidir([], NUEVO) is None
    assert decidir([_e(1, "Estadio Azteca", "CDMX", 19.40, -99.10)], NUEVO) is None   # a >10 km


def test_empate_de_distancia_elige_el_id_menor():
    existentes = [_e(9, "Estadio Banorte", "A", 19.3030, -99.1505), _e(3, "Estadio Banorte", "B", 19.3030, -99.1505)]
    assert decidir(existentes, NUEVO) == 3


def test_sin_coordenadas_exige_mismo_nombre_y_ciudad():
    sin = {"name": "Estadio X", "city": "Lima", "lat": None, "lon": None}
    assert decidir([_e(5, "estadio x", "Lima", None, None)], sin) == 5
    assert decidir([_e(5, "Estadio X", "Quito", None, None)], sin) is None
    assert decidir([_e(5, "Estadio Y", "Lima", None, None)], sin) is None
