"""Análisis de un evento de SofaScore (tenis) sin base de datos: decide aceptar, rechazar (con motivo) o excluir.

Campos prohibidos como rasgo (plan §A.4, aud. §5.1): `firstToServe`, `ranking`/`currentRanking`/`prizeCurrent`/
`userCount` de los jugadores, `homeScore.point`/`awayScore.point`, `changes`, `h2h` y `team_streaks`. Este módulo no los
lee; las pruebas lo comprueban.
"""
from datetime import datetime, timezone

from . import sofascore_reglas as r

CIRCUITOS = ("atp", "wta")
MEJOR_DE = (3, 5)
ESTADOS_CON_DESENLACE = ("completado", "retirada")


def _rechazo(motivo: str) -> dict:
    return {"rechazo": motivo, "excluido": None, "avisos": []}


def _excluido(motivo: str) -> dict:
    return {"rechazo": None, "excluido": motivo, "avisos": []}


def _es_doble(ev: dict) -> bool:
    for lado in ("homeTeam", "awayTeam"):
        equipo = ev.get(lado) or {}
        if equipo.get("subTeams") or "/" in (equipo.get("name") or ""):
            return True
        if equipo.get("type") not in (None, 1):
            return True
    return "doubles" in str((ev.get("season") or {}).get("name", "")).lower()


def _jugador(equipo: dict) -> dict:
    info = equipo.get("playerTeamInfo") or {}
    nacimiento = info.get("birthDateTimestamp")
    altura = info.get("height")
    plays = (info.get("plays") or "").lower()
    pais = (equipo.get("country") or {}).get("alpha3") or ""
    return {
        "id_fuente": str(equipo.get("id")),
        "nombre": equipo.get("fullName") or equipo.get("name"),
        "fecha_nacimiento": r.dia_utc(nacimiento).isoformat() if nacimiento is not None else None,
        "pais": pais if len(pais) == 3 and pais.isalpha() and pais.isupper() else None,
        "mano": "Z" if "left" in plays else "D" if "right" in plays else None,
        "altura_cm": str(round(altura * 100)) if isinstance(altura, (int, float)) and 1.0 <= altura <= 2.5
        else None,
    }


def resumen(ev: dict) -> dict | None:
    """Campos mínimos para la primera pasada (edición y torneo). None si no es un partido individual de tenis ATP/WTA."""
    torneo = ev.get("tournament") or {}
    if ((torneo.get("category") or {}).get("sport") or {}).get("slug") != "tennis" or _es_doble(ev):
        return None
    circuito = ((torneo.get("category") or {}).get("slug") or "").lower()
    ut = torneo.get("uniqueTournament") or {}
    if circuito not in CIRCUITOS or ut.get("id") is None or ev.get("startTimestamp") is None:
        return None
    temporada = (ev.get("season") or {}).get("year")
    cat, _ = r.categoria(circuito, ut.get("tennisPoints"), ut.get("name") or "")
    sup, indoor, _ = r.superficie(ev.get("groundType") or ut.get("groundType"))
    return {
        "circuito": circuito, "clave": str(ut["id"]), "nombre": ut.get("name") or "",
        "categoria": cat, "temporada": _anio(temporada), "inicio_torneo": torneo.get("startTimestamp"),
        "fin_torneo": torneo.get("endTimestamp"), "superficie": sup, "indoor": indoor,
        "inicio_partido": int(ev["startTimestamp"]), "equipos": cat == "equipos",
    }


def _anio(valor) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def analizar(ev: dict, est_json: dict | None, pbp_json: dict | None) -> dict:
    """Decisión y datos de un evento. Claves: rechazo, excluido, avisos y, si se acepta, los bloques
    torneo, edicion, partido, jugadores (local, visitante), resultado, estadistica (local, visitante) y pbp."""
    torneo = ev.get("tournament") or {}
    if ((torneo.get("category") or {}).get("sport") or {}).get("slug") != "tennis":
        return _excluido("no_tenis")
    if _es_doble(ev):
        return _excluido("doble")
    circuito = ((torneo.get("category") or {}).get("slug") or "").lower()
    if circuito not in CIRCUITOS:
        return _rechazo("circuito_desconocido")
    ut = torneo.get("uniqueTournament") or {}
    if ut.get("id") is None:
        return _rechazo("torneo_sin_identidad")
    if ev.get("startTimestamp") is None:
        return _rechazo("sin_inicio")
    temporada = _anio((ev.get("season") or {}).get("year"))
    if temporada is None or not 1968 <= temporada <= 2100:
        return _rechazo("temporada_fuera_de_rango")
    local, visitante = ev.get("homeTeam") or {}, ev.get("awayTeam") or {}
    if local.get("id") is None or visitante.get("id") is None:
        return _rechazo("id_jugador_vacio")
    if str(local["id"]) == str(visitante["id"]):
        return _rechazo("mismo_jugador")
    ronda = r.ronda((ev.get("roundInfo") or {}).get("name"))
    if ronda is None:
        return _rechazo("ronda_desconocida")
    mejor_de = ev.get("defaultPeriodCount")
    if mejor_de not in MEJOR_DE:
        return _rechazo("mejor_de_no_valido")
    estado = r.estado_base(ev.get("status"))
    if estado is None:
        return _rechazo("estado_desconocido")
    inicio = int(ev["startTimestamp"])
    tiempo = ev.get("time") or {}
    cat, aviso_cat = r.categoria(circuito, ut.get("tennisPoints"), ut.get("name") or "")
    sup, indoor, aviso_sup = r.superficie(ev.get("groundType") or ut.get("groundType"))
    avisos = [a for a in (aviso_cat, aviso_sup) if a]

    marcador_l, marcador_v = ev.get("homeScore") or {}, ev.get("awayScore") or {}
    sets = r.leer_sets(marcador_l, marcador_v)
    ganador = ev.get("winnerCode")
    resultado, motivo = _resultado(estado, ganador, sets, mejor_de, avisos)
    if motivo:
        return _rechazo(motivo)

    fin = r.fin_estimado(inicio, tiempo, len(sets))
    resultado["duracion_min"] = r.duracion_min(tiempo, len(sets))
    if resultado["duracion_min"] is None and sets:
        avisos.append("duracion_ausente")
    resultado["visible_desde"] = fin

    estad = {"local": None, "visitante": None}
    pbp_filas = None
    if pbp_json is not None and estado in ESTADOS_CON_DESENLACE:
        pbp_filas, motivo_pbp = r.juegos_pbp(pbp_json, sets)
        if motivo_pbp:
            avisos.append(f"pbp_no_derivable:{motivo_pbp}")
    if est_json is not None and estado in ESTADOS_CON_DESENLACE:
        items = r.estadisticas_all(est_json)
        for lado, clave in (("local", "home"), ("visitante", "away")):
            fila, motivo_e = r.estadistica(items, clave)
            if motivo_e:
                avisos.append(f"estadistica_{lado}:{motivo_e}")
            estad[lado] = fila
    elif est_json is not None:
        avisos.append("estadistica_no_aplica_al_estado")

    return {
        "rechazo": None, "excluido": None, "avisos": avisos,
        "torneo": {"circuito": circuito, "clave": str(ut["id"]), "nombre": ut.get("name") or "",
                   "categoria": cat},
        "edicion": {"temporada": temporada, "superficie": sup, "indoor": indoor,
                    "inicio_torneo": torneo.get("startTimestamp"), "fin_torneo": torneo.get("endTimestamp"),
                    "equipos": cat == "equipos"},
        "partido": {"ronda": ronda, "mejor_de": mejor_de, "inicio": inicio,
                    "visible_desde": datetime.fromtimestamp(inicio, tz=timezone.utc) - r.VENTANA_PARTIDO,
                    "fecha_inicio": r.dia_utc(inicio)},
        "jugadores": {"local": _jugador(local), "visitante": _jugador(visitante)},
        "resultado": resultado,
        "estadistica": estad,
        "pbp": pbp_filas,
        "circuito": circuito,
    }


def _resultado(estado, ganador, sets, mejor_de, avisos) -> tuple[dict, str | None]:
    """Resultado en codificación local. (dict, None) o ({}, motivo de rechazo)."""
    necesarios = mejor_de // 2 + 1
    if any({gl, gv} == {6, 7} and tbl is None and tbv is None for gl, gv, tbl, tbv in sets):
        avisos.append("tiebreak_sin_puntos")
    if estado == "completado":
        if ganador not in (1, 2):
            return {}, "ganador_ausente"
        validos = []
        for i, (gl, gv, tbl, tbv) in enumerate(sets):
            g, motivo = r.valida_set(gl, gv, tbl, tbv, i == len(sets) - 1)
            if motivo:
                return {}, motivo
            validos.append(g)
        sw, sp = r.sets_ganados(validos)
        ganados = sw if ganador == 1 else sp
        perdidos = sp if ganador == 1 else sw
        if len(sets) < 2 or ganados != necesarios or perdidos >= necesarios:
            return {}, "completado_incoherente"
        return {"estado": "completado", "ganador": ganador, "retira": None, "sets": sets,
                "sets_completos": len(sets)}, None
    if estado == "retirada":
        if ganador not in (1, 2):
            return {}, "ganador_ausente"
        validos = []
        for i, (gl, gv, tbl, tbv) in enumerate(sets):
            g, motivo = r.valida_set(gl, gv, tbl, tbv, i == len(sets) - 1)
            if motivo:
                if i == len(sets) - 1:
                    avisos.append(f"set_parcial_excluido:{motivo}")
                    break
                return {}, motivo
            validos.append([gl, gv, tbl, tbv])
        return {"estado": "retirada", "ganador": ganador, "retira": 3 - ganador, "sets": validos,
                "sets_completos": len(validos)}, None
    if estado == "walkover":
        if sets:
            return {}, "walkover_con_marcador"
        avisos.append("walkover_sin_ganador_en_base")
        return {"estado": "walkover", "ganador": None, "retira": None, "sets": None, "sets_completos": None}, None
    if estado == "descalificado":
        avisos.append("descalificado_sin_ganador_en_base")
        return {"estado": "descalificado", "ganador": None, "retira": None, "sets": None,
                "sets_completos": None}, None
    return {"estado": "cancelado", "ganador": None, "retira": None, "sets": None, "sets_completos": None}, None
