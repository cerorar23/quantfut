"""Códigos de país: TML usa los del COI (GER, SUI, NED…) y SofaScore los ISO alpha-3 (DEU, CHE, NLD…).

Comparados tal cual, el mismo jugador sale «de otro país» y se separa como homónimo: medido el 5-nov sobre datos reales,
132 de 860 jugadores de SofaScore con nombre idéntico en TML (15 %) diferían solo por el código. Todo país se lleva a ISO
alpha-3 antes de comparar. Solo están los códigos del COI que difieren del ISO; los demás pasan sin cambio.
"""
IOC_A_ISO3 = {
    "ALG": "DZA", "ANG": "AGO", "ANT": "ATG", "ARU": "ABW", "BAH": "BHS", "BAN": "BGD", "BAR": "BRB", "BER": "BMU",
    "BIZ": "BLZ", "BOT": "BWA", "BRU": "BRN", "BUL": "BGR", "BUR": "BFA", "CAM": "KHM", "CAY": "CYM", "CGO": "COG",
    "CHI": "CHL", "CRC": "CRI", "CRO": "HRV", "DEN": "DNK", "ESA": "SLV", "FIJ": "FJI", "GAM": "GMB", "GBS": "GNB",
    "GER": "DEU", "GEQ": "GNQ", "GRE": "GRC", "GRN": "GRD", "GUA": "GTM", "GUI": "GIN", "HAI": "HTI", "HON": "HND",
    "INA": "IDN", "IRI": "IRN", "ISV": "VIR", "IVB": "VGB", "KSA": "SAU", "KUW": "KWT", "LAT": "LVA", "LBA": "LBY",
    "LES": "LSO", "LIB": "LBN", "MAD": "MDG", "MAS": "MYS", "MAW": "MWI", "MGL": "MNG", "MON": "MCO", "MRI": "MUS",
    "MYA": "MMR", "NCA": "NIC", "NED": "NLD", "NEP": "NPL", "NGR": "NGA", "NIG": "NER", "OMA": "OMN", "PAR": "PRY",
    "PHI": "PHL", "PLE": "PSE", "POR": "PRT", "RSA": "ZAF", "SAM": "WSM", "SEY": "SYC", "SIN": "SGP", "SKN": "KNA",
    "SLO": "SVN", "SOL": "SLB", "SRI": "LKA", "SUD": "SDN", "SUI": "CHE", "TAN": "TZA", "TGA": "TON", "TOG": "TGO",
    "TPE": "TWN", "TRI": "TTO", "UAE": "ARE", "URU": "URY", "VAN": "VUT", "VIE": "VNM", "VIN": "VCT", "ZAM": "ZMB",
    "ZIM": "ZWE",
}


def iso3(codigo):
    """Código de país en ISO alpha-3 y mayúsculas; None si no hay (nunca un valor inventado)."""
    c = (codigo or "").strip().upper()
    return IOC_A_ISO3.get(c, c) or None
