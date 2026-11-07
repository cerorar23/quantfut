"""Reglas puras de SofaScore (tenis): ronda, categoría, superficie, estado, sets, duración, visibilidad,
estadística del partido (periodo ALL) y punto a punto. Sin base de datos ni E/S.

Convenciones: todo lo que sale de aquí está codificado en LOCAL (1 = jugador local/home de SofaScore). La
orientación canónica (jugador_1 < jugador_2 por id) la aplica el escritor, que conoce los ids de la base.
"""
import re
from datetime import datetime, timedelta, timezone

NEUTRA = "250"
MINUTO = 60
PASO_ESTIMADO_FIN = timedelta(minutes=30)   # margen sobre el fin estimado de un partido
FIN_SIN_DURACIONES = timedelta(hours=6)     # sin duraciones: el fin se supone 6 h después del inicio (más tarde)
VENTANA_PARTIDO = timedelta(hours=12)       # el partido (programa) es visible 12 h antes del inicio
VENTANA_EDICION = timedelta(days=7)         # la edición es visible 7 días antes del inicio del torneo

_RONDAS = {
    "round of 128": "R128", "round of 64": "R64", "round of 32": "R32", "round of 16": "R16",
    "quarterfinals": "QF", "quarterfinal": "QF", "semifinals": "SF", "semifinal": "SF",
    "final": "F", "round robin": "RR",
    # Última ronda del clasificatorio (2 o 3 rondas según el torneo): etiqueta propia «QL», NUNCA «QF» (cuartos).
    "qualification final": "QL",
}
_RONDA_CLASIFICACION = re.compile(r"qualification round ([1-3])")

_EQUIPOS = re.compile(r"davis|billie jean|bjk|fed cup|united cup|laver cup|hopman", re.IGNORECASE)
_FINALES = re.compile(r"\b(atp|wta)?\s*finals\b|tour finals|nitto|year.end|next gen", re.IGNORECASE)
_JJOO = re.compile(r"olymp", re.IGNORECASE)

# groundType de SofaScore -> (superficie de la base, indoor). Valores vistos en la muestra: 6 (ver LEEME).
_SUPERFICIES = {
    "hardcourt outdoor": ("hard", False),
    "hardcourt indoor": ("hard", True),
    "red clay": ("clay", False),
    "red clay indoor": ("clay", True),
    "green clay": ("clay", False),
    "grass": ("grass", False),
}

# status.code → estado de la base (plan §I.9). Medido en el archivo completo: 100 Ended, 92 Retired, 91 Walkover,
# 97 y 98 Defaulted (descalificado).
_ESTADO_POR_CODIGO = {100: "completado", 92: "retirada", 91: "walkover", 97: "descalificado", 98: "descalificado"}


def ronda(nombre: str | None) -> str | None:
    """Código de ronda de la base, o None si está vacía o no se reconoce (rechazo `ronda_desconocida`)."""
    n = (nombre or "").strip().lower()
    if n in _RONDAS:
        return _RONDAS[n]
    m = _RONDA_CLASIFICACION.fullmatch(n)
    return f"Q{m.group(1)}" if m else None


def categoria(circuito: str, puntos: int | None, nombre: str) -> tuple[str, str | None]:
    """(categoría de la base, aviso). Equipos y finales por nombre; el resto por tennisPoints (2000 GS, 1000, 500, 250)."""
    if _EQUIPOS.search(nombre or ""):
        return "equipos", None
    if _JJOO.search(nombre or ""):
        return "JJOO", None
    if _FINALES.search(nombre or ""):
        return "Finales", None
    if puntos == 2000:
        return "GS", None
    if puntos == 1000:
        return ("M1000" if circuito == "atp" else "WTA1000"), None
    if puntos == 500:
        return "500", None
    if puntos == 250:
        return "250", None
    return NEUTRA, f"categoria_neutra:{puntos}"


def superficie(ground: str | None) -> tuple[str | None, bool | None, str | None]:
    """(superficie, indoor, aviso). Desconocida → NULL y aviso (nunca se inventa)."""
    n = (ground or "").strip().lower()
    if n in _SUPERFICIES:
        return (*_SUPERFICIES[n], None)
    if n.startswith("carpet"):
        return "carpet", "indoor" in n, None
    return None, None, f"superficie_desconocida:{ground}"


def estado_base(status: dict | None) -> str | None:
    """Estado de la base por status.code; `canceled` por tipo; descalificado por descripción. None = desconocido."""
    st = status or {}
    codigo = st.get("code")
    if codigo in _ESTADO_POR_CODIGO:
        return _ESTADO_POR_CODIGO[codigo]
    if (st.get("type") or "").lower() == "canceled":
        return "cancelado"
    if "disqualif" in (st.get("description") or "").lower():
        return "descalificado"
    return None


def leer_sets(marcador_local: dict, marcador_visitante: dict) -> list[list]:
    """[[games_local, games_visitante, tb_local, tb_visitante], …] para period1..period5, en orden y sin huecos.
    El tie-break va en cada lado (periodNTieBreak); None si no hay."""
    sets = []
    for n in range(1, 6):
        gl = marcador_local.get(f"period{n}")
        gv = marcador_visitante.get(f"period{n}")
        if gl is None or gv is None:
            break
        sets.append([gl, gv, marcador_local.get(f"period{n}TieBreak"), marcador_visitante.get(f"period{n}TieBreak")])
    return sets


def valida_set(gl, gv, tbl, tbv, ultimo: bool) -> tuple[int | None, str | None]:
    """(ganador del set 1/2 local, motivo). Reglas: 6-0…6-4; 7-5; 7-6 con tie-break ≥7 y ventaja 2; súper tie-break
    1-0 solo en el último set; en el último set, ventaja (k+2)-k con k ≥ 6 sin tie-break. Un 8-6 con tie-break es
    incoherente."""
    if gl is None or gv is None:
        return None, "set_incompleto"
    if gl == gv:
        return None, "set_empatado"
    ganador = 1 if gl > gv else 2
    gw, gp = (gl, gv) if ganador == 1 else (gv, gl)
    tbw, tbp = (tbl, tbv) if ganador == 1 else (tbv, tbl)
    hay_tb = tbl is not None or tbv is not None
    if not hay_tb:
        if gw == 6 and gp <= 4:
            return ganador, None
        if gw == 7 and gp == 5:
            return ganador, None
        if gw == 7 and gp == 6:
            # El set existe; SofaScore a veces no informa los puntos del tie-break: NULL, no inválido (como TML).
            return ganador, None
        if ultimo and gp >= 6 and gw == gp + 2:
            return ganador, None
        return None, "set_invalido"
    if tbl is None or tbv is None:
        return None, "tiebreak_incompleto"
    if gw == 7 and gp == 6:
        if tbw >= 7 and tbw - tbp >= 2:
            return ganador, None
        return None, "tiebreak_invalido"
    if ultimo and gw == 1 and gp == 0 and tbw >= 10 and tbw - tbp >= 2:
        return ganador, None
    return None, "set_invalido"


def sets_ganados(sets_validos: list[int]) -> tuple[int, int]:
    return sets_validos.count(1), sets_validos.count(2)


def duracion_min(tiempo: dict, n_sets: int) -> int | None:
    """Minutos = suma de time.period1..N / 60 (redondeo). None si falta alguna duración o no está en 1..600 (nunca 0)."""
    if n_sets == 0:
        return None
    segundos = [tiempo.get(f"period{n}") for n in range(1, n_sets + 1)]
    if any(s is None for s in segundos):
        return None
    minutos = round(sum(segundos) / MINUTO)
    return minutos if 1 <= minutos <= 600 else None


def fin_estimado(inicio: int, tiempo: dict, n_sets: int) -> datetime:
    """Fin CONSERVADOR (UTC): max(inicio + Σ duraciones, inicio del periodo actual + duración del último set) + 30 min.
    Sin duraciones completas: inicio + 6 h. Siempre ≥ el fin real (nunca más temprano)."""
    segundos = [tiempo.get(f"period{n}") for n in range(1, n_sets + 1)]
    if n_sets == 0 or any(s is None for s in segundos):
        return instante(inicio) + FIN_SIN_DURACIONES
    base = inicio + sum(segundos)
    actual = tiempo.get("currentPeriodStartTimestamp")
    if actual is not None:
        base = max(base, actual + segundos[-1])
    return instante(base) + PASO_ESTIMADO_FIN


def instante(segundos: int) -> datetime:
    return datetime.fromtimestamp(int(segundos), tz=timezone.utc)


def dia_utc(segundos: int):
    return instante(segundos).date()


def estadistica(items: dict, lado: str) -> tuple[dict | None, str | None]:
    """Fila de `estadistica` para un lado (`lado` = 'home' o 'away') desde los items del periodo ALL (clave → item).

    Definiciones (medidas en la muestra): puntos_saque = total de firstServeAccuracy; primeros_dentro = su valor;
    primeros_ganados = firstServePointsAccuracy.valor; segundos_ganados = secondServePointsAccuracy.valor;
    bp_salvados/bp_afrontados = breakPointsSaved valor/total. Comprobaciones de definición: los totales de
    primer/segundo saque deben cuadrar. Un lado con 0 puntos de saque es un faltante (sin fila)."""
    def val(clave):
        it = items.get(clave)
        return None if it is None else it.get(f"{lado}Value")

    def tot(clave):
        it = items.get(clave)
        return None if it is None else it.get(f"{lado}Total")

    ps = tot("firstServeAccuracy")
    pd = val("firstServeAccuracy")
    pg = val("firstServePointsAccuracy")
    sg = val("secondServePointsAccuracy")
    if ps is not None and ps == 0:
        return None, "cero_imposible"
    if ps is not None and pd is not None:
        if tot("firstServePointsAccuracy") not in (None, pd):
            return None, "definicion_incoherente"
        if tot("secondServeAccuracy") not in (None, ps - pd):
            return None, "definicion_incoherente"
        if tot("secondServePointsAccuracy") not in (None, ps - pd):
            return None, "definicion_incoherente"
    bp_s = val("breakPointsSaved")
    bp_a = tot("breakPointsSaved")
    fila = {
        "aces": val("aces"),
        "dobles_faltas": val("doubleFaults"),
        "puntos_saque": ps,
        "primeros_dentro": pd,
        "primeros_ganados": pg,
        "segundos_ganados": sg,
        "juegos_saque": val("serviceGamesTotal"),
        "bp_salvados": bp_s,
        "bp_afrontados": bp_a,
    }
    if all(v is None for v in fila.values()):
        return None, "sin_datos"
    if any(v is not None and v < 0 for v in fila.values()):
        return None, "negativa"
    if pd is not None and ps is not None and pd > ps:
        return None, "incoherente"
    if pg is not None and pd is not None and pg > pd:
        return None, "incoherente"
    if bp_s is not None and bp_a is not None and bp_s > bp_a:
        return None, "incoherente"
    return fila, None


def estadisticas_all(stats_json: dict) -> dict:
    """clave → item del periodo ALL (el resto de periodos se ignoran: 1ST/2ND… no son del partido completo)."""
    items = {}
    for per in stats_json.get("statistics", []):
        if per.get("period") != "ALL":
            continue
        for grupo in per.get("groups", []):
            for it in grupo.get("statisticsItems", []):
                items.setdefault(it.get("key"), it)
    return items


# ---------- Punto a punto ----------

_ETIQ = {0: "0", 1: "15", 2: "30", 3: "40"}


def _pantalla(h: int, a: int):
    """Marcador visible de un juego regular (0/15/30/40/A) o None si la posición no es visible (juego terminado)."""
    if h >= 3 and a >= 3:
        if h == a:
            return ("40", "40")
        if h - a == 1:
            return ("A", "40")
        if a - h == 1:
            return ("40", "A")
        return None
    if h <= 3 and a <= 3:
        return (_ETIQ[h], _ETIQ[a])
    return None


def _terminal(h: int, a: int) -> bool:
    return max(h, a) >= 4 and abs(h - a) >= 2


def _tb_terminal(h: int, a: int) -> bool:
    return max(h, a) >= 7 and abs(h - a) >= 2


def _juego_regular(puntos: list, ganador_juego: int) -> tuple[list[int] | None, str | None]:
    """Ganador de cada punto (1 local / 2 visitante) de un juego regular. El último punto (el que cierra el juego)
    NO aparece en el listado de SofaScore: se deduce del ganador del juego, y debe ser el único que lo cierre."""
    h = a = 0
    ganadores = []
    for par in puntos:
        if _terminal(h, a):
            return None, "pbp_punto_tras_fin"
        candidatos = []
        for w in (1, 2):
            nh, na = (h + 1, a) if w == 1 else (h, a + 1)
            if _terminal(nh, na):
                continue
            if _pantalla(nh, na) == tuple(par):
                candidatos.append((w, nh, na))
        if len(candidatos) != 1:
            return None, "pbp_transicion_invalida"
        w, h, a = candidatos[0]
        ganadores.append(w)
    nh, na = (h + 1, a) if ganador_juego == 1 else (h, a + 1)
    if not _terminal(nh, na):
        return None, "pbp_final_no_deducible"
    ganadores.append(ganador_juego)
    return ganadores, None


def _juego_tiebreak(puntos: list, ganador_juego: int) -> tuple[list[int] | None, str | None]:
    """Tie-break: el último punto SÍ aparece (medido 110/110) y debe cerrarlo el ganador del juego."""
    h = a = 0
    ganadores = []
    for par in puntos:
        vh, va = int(par[0]), int(par[1])
        if (vh, va) == (h + 1, a):
            w = 1
        elif (vh, va) == (h, a + 1):
            w = 2
        else:
            return None, "pbp_tiebreak_transicion_invalida"
        ganadores.append(w)
        h, a = vh, va
    if not ganadores or not _tb_terminal(h, a):
        return None, "pbp_tiebreak_no_cierra"
    if ganadores[-1] != ganador_juego:
        return None, "pbp_tiebreak_ganador_no_cuadra"
    return ganadores, None


def _sacador_tiebreak(primero: int, i: int) -> int:
    """Sacador del punto i (0-based) de un tie-break: el primero saca 1 punto y luego cada jugador saca 2 seguidos."""
    if i == 0:
        return primero
    grupo = (i + 1) // 2
    return (3 - primero) if grupo % 2 == 1 else primero


def juegos_pbp(pbp_json: dict, marcador: list[list]) -> tuple[list[dict] | None, str | None]:
    """Filas de juego_pbp (local-codificadas) o (None, motivo). Solo si todo cuadra: sets 1..N con el marcador, juegos
    1..G, cada juego de puntos con ganador deducible, cuenta de juegos = marcador, alternancia del saque y tie-break
    que cierra con el ganador del juego. Cualquier fallo deja el partido sin punto a punto."""
    sets = sorted(pbp_json.get("pointByPoint", []), key=lambda s: s.get("set", 0))
    if [s.get("set") for s in sets] != list(range(1, len(marcador) + 1)):
        return None, "pbp_sets_no_cuadran"
    filas = []
    ultimo_saque = None
    for n, (s, (gl, gv, tbl, tbv)) in enumerate(zip(sets, marcador), start=1):
        juegos = sorted(s.get("games", []), key=lambda g: g.get("game", 0))
        if [g.get("game") for g in juegos] != list(range(1, len(juegos) + 1)):
            return None, "pbp_juegos_no_consecutivos"
        if len(juegos) != gl + gv:
            return None, "pbp_juegos_no_cuadran"
        hay_tb = tbl is not None or tbv is not None
        cuenta_l = cuenta_v = 0
        for j, g in enumerate(juegos, start=1):
            pts = g.get("points", [])
            sc = g.get("score") or {}
            ganador = sc.get("scoring")
            saque = sc.get("serving")
            es_tb = j == len(juegos) and hay_tb
            if ganador not in (1, 2) or not pts:
                return None, "pbp_juego_sin_datos"
            if es_tb:
                # El campo `serving` del tie-break NO es fiable (medido: coincide con el juego anterior en el 56 %).
                # Regla del tie-break: saca primero quien no sacó el último juego regular; tras el tie-break el set
                # siguiente empieza con el sacador de ese último juego (medido: 187 de 187).
                if ultimo_saque is None:
                    return None, "pbp_tiebreak_sin_juego_previo"
                saque = 3 - ultimo_saque
            elif saque not in (1, 2):
                return None, "pbp_juego_sin_datos"
            if ultimo_saque is not None and saque == ultimo_saque:
                return None, "pbp_saque_no_alterna"
            ultimo_saque = saque
            if es_tb:
                if any(not str(p["homePoint"]).isdigit() for p in pts):
                    return None, "pbp_tiebreak_sin_numeros"
                par = [(p["homePoint"], p["awayPoint"]) for p in pts]
                ganadores, motivo = _juego_tiebreak(par, ganador)
                if motivo:
                    return None, motivo
                filas.append({"set_n": n, "juego_n": j, "sacador": saque, "es_tiebreak": True,
                              "puntos": "".join("S" if _sacador_tiebreak(saque, i) == w else "R"
                                                for i, w in enumerate(ganadores))})
            else:
                if any(not _es_visible(p) for p in pts):
                    return None, "pbp_punto_no_visible"
                par = [(p["homePoint"], p["awayPoint"]) for p in pts]
                ganadores, motivo = _juego_regular(par, ganador)
                if motivo:
                    return None, motivo
                filas.append({"set_n": n, "juego_n": j, "sacador": saque, "es_tiebreak": False,
                              "puntos": "".join("S" if w == saque else "R" for w in ganadores)})
            if ganador == 1:
                cuenta_l += 1
            else:
                cuenta_v += 1
        if (cuenta_l, cuenta_v) != (gl, gv):
            return None, "pbp_marcador_no_cuadra"
    return filas, None


_ETIQ_VISIBLES = {"0", "15", "30", "40", "A"}


def _es_visible(punto: dict) -> bool:
    return punto.get("homePoint") in _ETIQ_VISIBLES and punto.get("awayPoint") in _ETIQ_VISIBLES
