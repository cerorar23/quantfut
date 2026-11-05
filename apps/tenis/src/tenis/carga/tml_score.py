"""Marcador de TML → estado y sets. Puro (sin base).

Los sets vienen desde el punto de vista del GANADOR del partido (convención de TML). Cada set se guarda como
(a, b, tb_a, tb_b): a y b son juegos del ganador y del perdedor; tb_* son los puntos del tie-break (None si no hubo).
El tie-break va entre paréntesis y son los puntos del que PERDIÓ el set; el ganador del set tiene max(7, t+2).
Un super tie-break final «[x-y]» es un set 1-0 con tb x/y (el mayor gana el set).
"""
import re
from dataclasses import dataclass

TOKEN_SET = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")
TOKEN_SUPER = re.compile(r"^\[(\d+)-(\d+)\]$")
PALABRAS_SIN_MARCADOR = ("abd", "ab.", "unfinished", "abandon", "played", "&nbsp;", "wea")
RETIRO = {"ret", "ret.", "ret"}


@dataclass(frozen=True)
class Marcador:
    estado: str                     # completado | retirada | walkover | descalificado | cancelado
    sets: tuple | None              # ((a, b, tb_a, tb_b), ...) desde el ganador del partido
    sets_completos: int | None
    super_tiebreak: bool = False
    motivo: str | None = None       # no None = rechazo


def _rechazo(motivo: str) -> Marcador:
    return Marcador("rechazo", None, None, motivo=motivo)


def _set_normal(a: int, b: int, t: int | None) -> tuple[tuple, bool]:
    """(set, válido). Válido solo si el resultado de juegos es de set terminado y el tie-break encaja."""
    if a == b:
        return (a, b, None, None), False
    hi, lo = max(a, b), min(a, b)
    if t is None:
        # Set terminado normal; 7-6 SIN puntos de tie-break (TML antiguo no los registra: dato faltante = NULL, no
        # inválido); set de ventaja (8-6, 9-7…: formatos históricos sin tie-break, p. ej. set decisivo hasta 2021).
        valido = ((hi == 6 and lo <= 4) or (hi == 7 and lo in (5, 6)) or (hi >= 8 and hi - lo == 2))
        return (a, b, None, None), valido
    if (hi, lo) != (7, 6):
        return (a, b, None, None), False
    ganador_tb = max(7, t + 2)
    tb = (t, ganador_tb) if a < b else (ganador_tb, t)
    return (a, b, tb[0], tb[1]), True


def _set_super(x: int, y: int) -> tuple[tuple, bool]:
    if x == y:
        return (0, 0, x, y), False
    valido = max(x, y) >= 10 and abs(x - y) >= 2
    return ((1, 0, x, y) if x > y else (0, 1, x, y)), valido


def _partes(tokens: list[str]):
    for tok in tokens:
        m = TOKEN_SET.match(tok)
        if m:
            t = m.group(3)
            yield "n", int(m.group(1)), int(m.group(2)), (int(t) if t is not None else None)
            continue
        m = TOKEN_SUPER.match(tok)
        if m:
            yield "s", int(m.group(1)), int(m.group(2)), None
            continue
        yield None, None, None, None


def parsear_marcador(texto: str, mejor_de: int) -> Marcador:
    t = (texto or "").strip()
    bajo = t.lower()
    if t == "":
        return Marcador("cancelado", None, None)
    if bajo in ("w/o", "wo", "walkover"):
        return Marcador("walkover", None, None)
    tokens = t.split()
    estado = "completado"
    if tokens and tokens[-1].lower() in RETIRO:
        estado, tokens = "retirada", tokens[:-1]
    elif tokens and tokens[-1].upper() == "DEF":
        estado, tokens = "descalificado", tokens[:-1]
    partes = list(_partes(tokens))
    hay_sets = any(p[0] for p in partes)
    if any(p[0] is None for p in partes):
        if not hay_sets and any(p in bajo for p in PALABRAS_SIN_MARCADOR):
            return Marcador("cancelado", None, None)
        if any(tok.lower() in ("w/o", "wo") for tok in tokens):
            return _rechazo("walkover_con_marcador")
        if hay_sets:
            return _rechazo("marcador_ilegible")
        return _rechazo("marcador_ilegible")
    if any(p in bajo for p in ("wea", "abd", "ab.")) and hay_sets:
        return _rechazo("estado_con_marcador")
    sets, validos, superts = [], 0, False
    for i, (kind, a, b, tb) in enumerate(partes):
        ultimo = i == len(partes) - 1
        if kind == "s":
            conv, ok = _set_super(a, b)
            superts = superts or ok
        else:
            conv, ok = _set_normal(a, b, tb)
        sets.append(conv)
        if ok:
            validos += 1
        elif not (ultimo and estado in ("retirada", "descalificado")):
            return _rechazo("set_invalido")
    if len(sets) > mejor_de:
        return _rechazo("mas_sets_que_formato")
    if estado == "completado":
        if len(sets) < 2:
            return _rechazo("completado_de_un_set")
        need = mejor_de // 2 + 1
        gana = sum(1 for s in sets if s[0] > s[1])
        pierde = sum(1 for s in sets if s[1] > s[0])
        if gana != need or pierde >= need:
            return _rechazo("completado_incoherente")
    return Marcador(estado, tuple(sets), validos, superts)
