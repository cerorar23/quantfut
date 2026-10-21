from qf.ingest.arbitros_equivalencia import elegir, regla_nombre


def test_regla_de_nombre():
    assert regla_nombre("A Taylor", "Anthony Taylor")
    assert regla_nombre("A Madley", "Andy Madley")
    assert regla_nombre("J Gillett", "Jarred Gillett")
    assert regla_nombre("S López", "Santiago Lopez")            # acentos
    assert regla_nombre("A De Burgh", "Anthony De Burgh")        # apellido compuesto
    assert not regla_nombre("A Kitchen", "Joshua Smith")
    assert not regla_nombre("A Taylor", "Paul Taylor")           # otra inicial
    assert not regla_nombre("Taylor", "Anthony Taylor")          # sin inicial no hay regla


def test_acepta_la_pareja_dominante_y_descarta_el_ruido():
    pares = [("A Kitchen", "Andrew Kitchen", 68), ("A Kitchen", "Joshua Smith", 1),
             ("D Webb", "David Webb", 64), ("D Webb", "Robert Madley", 1)]
    got = {(x["arbitro_af"], x["arbitro_fotmob"]) for x in elegir(pares)}
    assert got == {("A Kitchen", "Andrew Kitchen"), ("D Webb", "David Webb")}


def test_rechaza_pocos_partidos_y_nombres_repartidos():
    assert elegir([("X Uno", "Xavier Uno", 4)]) == []                       # menos de 5
    repartido = [("M Oliver", "Michael Oliver", 30), ("M Oliver", "Mark Oliver", 25)]
    assert elegir(repartido) == []                                            # ninguno llega al 90 %
    # un nombre de FotMob que se reparte entre dos de API-Football tampoco es 1 a 1
    assert elegir([("A Smith", "Alan Smith", 20), ("B Smith", "Alan Smith", 20)]) == []


def test_marca_si_el_par_no_encaja_con_la_regla_de_nombre():
    x = elegir([("R Jones", "Robert Jones", 60), ("K Friend", "Kevin Friend", 9),
                ("P Tierney", "Paul Tierney", 8), ("Z Raro", "Otro Nombre", 12)])
    por = {r["arbitro_af"]: r["regla_nombre"] for r in x}
    assert por["R Jones"] and por["K Friend"] and por["P Tierney"] and not por["Z Raro"]
