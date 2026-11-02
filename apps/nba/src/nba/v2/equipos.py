"""Los 30 equipos con su código oficial (tricode de la NBA) y los alias de cada fuente."""

TRICODES = {
    "ATL": "Atlanta Hawks", "BKN": "Brooklyn Nets", "BOS": "Boston Celtics", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors", "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}

# Abreviaturas que una fuente escribe distinto del código oficial.
ALIAS = {
    "espn": {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"},
}


def canonico(fuente: str, abreviatura: str) -> str:
    codigo = ALIAS.get(fuente, {}).get(abreviatura, abreviatura)
    if codigo not in TRICODES:
        raise KeyError(f"equipo desconocido en {fuente}: {abreviatura}")
    return codigo

# Identificador numérico de equipo en ESPN → código oficial (medido en el marcador del 2-nov-2026).
ESPN_IDS = {
    "1": "ATL", "17": "BKN", "2": "BOS", "30": "CHA", "4": "CHI", "5": "CLE", "6": "DAL", "7": "DEN", "8": "DET",
    "9": "GSW", "10": "HOU", "11": "IND", "12": "LAC", "13": "LAL", "29": "MEM", "14": "MIA", "15": "MIL",
    "16": "MIN", "3": "NOP", "18": "NYK", "25": "OKC", "19": "ORL", "20": "PHI", "21": "PHX", "22": "POR",
    "24": "SAS", "23": "SAC", "28": "TOR", "26": "UTA", "27": "WAS",
}

# Identificador de equipo de la NBA (stats.nba.com / cdn.nba.com) → código oficial.
NBA_IDS = {
    1610612737: "ATL", 1610612738: "BOS", 1610612739: "CLE", 1610612740: "NOP", 1610612741: "CHI", 1610612742: "DAL",
    1610612743: "DEN", 1610612744: "GSW", 1610612745: "HOU", 1610612746: "LAC", 1610612747: "LAL", 1610612748: "MIA",
    1610612749: "MIL", 1610612750: "MIN", 1610612751: "BKN", 1610612752: "NYK", 1610612753: "ORL", 1610612754: "IND",
    1610612755: "PHI", 1610612756: "PHX", 1610612757: "POR", 1610612758: "SAC", 1610612759: "SAS", 1610612760: "OKC",
    1610612761: "TOR", 1610612762: "UTA", 1610612763: "MEM", 1610612764: "WAS", 1610612765: "DET", 1610612766: "CHA",
}
