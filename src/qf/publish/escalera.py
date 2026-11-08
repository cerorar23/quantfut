"""
Reto escalera: cada escalón apuesta TODO el saldo a un pronóstico; el reto se
completa al ganar sus escalones (3 a 6) y se pierde al fallar uno (pedido del
usuario, 2026-10-08). Es una apuesta combinada en la que cada partido se elige
cuando el anterior ya terminó.

LO QUE DECÍA LA REGLA DE PARTIDA Y LO QUE SE MIDIÓ
---------------------------------------------------
La regla del usuario: cuotas de 1,25 a 1,40, de 5 a 7 pasos, retirar la
inversión al llegar a ×2,5 y no forzar escalones. La probabilidad que daba
salía de la cuota (1 / cuota), es decir, CON el margen de la casa.

Medido sobre football-data (7 ligas, 2019-2025, pre-cierre, mejor de bet365 y
1xBet; `eval/escalera_prueba.py`): en 1,25-1,40 la probabilidad real (Pinnacle
sin margen) es 72,6 % y se acierta el 74,3 %, pero cada escalón pierde un
−3,4 % de valor esperado, y la escalera lo multiplica: 6 pasos se completan el
15,7 % de las veces y dejan −23,7 % por reto (−19,2 % retirando a ×2,5).

LA REGLA DESDE EL 2026-10-08 (decisión del usuario)
--------------------------------------------------
Se elige el escalón MÁS PROBABLE con cuota 1,25-1,40, sin filtro de valor:
con el filtro (cuota ≥ precio justo) salían muy pocos. Medido antes de
cambiarlo (`eval/escalera_prueba.py`, regla "rango_mas_probable"): −11,5 %
por reto a 3 pasos y −26 % a 6, porque el margen de la casa se queda en cada
escalón. Se publica igual, con su historial entero, y el valor esperado de
cada escalón se guarda y se enseña.

1. Probabilidad real: de Pinnacle sin margen (1X2, goles, ambos anotan,
   hándicap) o, en córners y tarjetas, del modelo estadístico
   `model/estadisticas_mercado.py` (equipos, liga y árbitro, sin cuotas).
   Solo líneas que pasaron la prueba de calibración.
2. `EV_MIN` = None: sin filtro de valor (se puede volver a poner un número).
3. La cuota es la mejor de las casas de la lista (`SOFT_BOOKS`) en el mismo
   instante: es la que se puede tomar y la que sube el saldo.
4. Un escalón al día como máximo por reto y solo cuando el anterior está
   liquidado. Si ningún partido cumple, no se apuesta: un reto puede durar semanas.
5. Freeroll: al llegar a `FREEROLL_X` veces el stake se retira la inversión y
   el resto sigue sin riesgo propio.
6. Retos de 3 a 6 escalones, varios a la vez (decisión del usuario,
   2026-10-08): `longitud_nuevo`. Acortar sube el % de retos completados pero
   NO el valor esperado (con escalones a precio justo es el mismo a cualquier
   longitud): solo cambia la varianza.
7. Hándicap asiático protector (+1, +1,5, +2...) solo en las líneas que
   pasaron la prueba de calibración (`eval/escalera_handicap.py`).

Lo que NO promete: elegir por probabilidad sube el acierto por escalón, no
el valor esperado; con el margen de la casa, la escalera pierde de media.

LA REGLA DESDE EL 2026-10-28 (decisión del usuario): RETO AL 80 % EN 7 DÍAS
---------------------------------------------------------------------------
El usuario pide que el reto COMPLETO se cumpla al menos el 80 % de las veces,
que busque el acierto y no la cuota, que pueda esperar al pronóstico seguro y
que dure como mucho 7 días (varios escalones un día o terminar en 2-3 días).

Matemática. Con escalones independientes y calibrados, P(completar) = ∏ p_i.
Con el mercado calibrado P × cobro ≈ 1 − margen: no hay combinación que suba P
sin bajar el cobro (Dubins y Savage: en un juego desfavorable, menos apuestas
es mejor). Por eso el reto tiene DOS escalones y un presupuesto de
probabilidad: cada escalón exige p ≥ (PROB_RETO / ∏ p elegidos)^(1/faltan)
(`umbral`), de modo que al terminar ∏ p ≥ 0,80 siempre; un primer escalón muy
seguro deja margen al segundo (0,95 → 0,842). Lo que más resta no son los
fallos sino quedarse sin segundo escalón en la ventana (`DIAS_MAX`): pasado
el plazo el reto queda «expirado» (no pierde dinero, no cuenta como cumplido).

- 2 escalones, hasta `POR_DIA` = 2 el mismo día en partidos distintos (es lo
  mismo que una combinada de los dos) y como mucho `DIAS_MAX` = 7 días.
- El MÁS PROBABLE primero (mide algo mejor que el de más valor: 85,9 % frente
  a 84,3 % de retos cumplidos con fútbol + tenis 2019-2025).
- Cuota ≥ 1,03 y como mucho 95 % por escalón (`PROB_MAX`, lo calibrado en
  fútbol; el tenis está calibrado hasta 0,97).
- Un reto abierto a la vez: el siguiente empieza cuando se cierra.
- Los retos abiertos con una regla anterior (`prob_objetivo` NULL) terminan
  con su rango de cuota y el más probable.

Medido (`python -m qf.eval.escalera_multideporte`; football-data 7 ligas,
NBA ganador al cierre de bet365 vía BetsAPI, tenis ATP/WTA de Tennis-Data con
Pinnacle sin margen y la cuota de bet365; el plazo cuenta desde el primer
escalón): fútbol + tenis 2019-2025, 539 retos, 85,9 % cumplidos, 10,6 %
fallidos, 3,5 % expirados, 2,0 días de media, cobro ×1,14 (+1,8 % por reto,
sin valor demostrado). Fútbol + NBA + tenis oct-2023 a may-2025: 230 retos,
84,3 % cumplidos, 0,9 % expirados, −3,3 % por reto. Con 3 escalones expira
uno de cada cuatro (63 % cumplidos). Solo fútbol con 1X2 y goles 2,5: 41 %
cumplidos y 52 % expirados: la regla necesita tenis y NBA, o las líneas de
vivo (hándicap, goles 1,5/3,5, córners), para no expirar.

Este módulo es la parte pura. La base de datos está en `escalera_datos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .alta_prob import Candidato

TARGETS: tuple[float, ...] = (2.0, 2.8, 4.5, 7.5, 12.0, 20.0)
MAX_ESCALONES: int = 6
CUOTA_MIN = 1.25
CUOTA_MAX = 2.10
# Probabilidad mínima por escalón (decisión del usuario, 2026-11-07).
PROB_MIN = 0.69
# Probabilidad de presupuesto base para umbral dinámico.
PROB_RETO = 0.4761
# Tope por escalón: lo calibrado en fútbol y alta probabilidad.
PROB_MAX = 0.95
# Objetivos posibles por orden (reemplaza las longitudes fijas anteriores).
LONGITUDES: tuple[float | int, ...] = TARGETS
# Escalones de un mismo reto que se pueden elegir el mismo día (partidos distintos).
POR_DIA = 1
# Días que un reto puede seguir abierto desde que se crea; luego, «expirado».
DIAS_MAX = 10
STAKE = Decimal("10.00")
# Freeroll: al llegar a 2.5x el stake inicial se retira la inversión y el resto sigue a riesgo cero.
FREEROLL_X: float | None = 2.5
# None: sin filtro de valor (regla del 2026-10-08). Con 0.0 se vuelve a exigir cuota ≥ precio justo.
EV_MIN: float | None = None
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Líneas de goles candidatas: incluye extremos y suelos de baja varianza.
LINEAS_GOLES: tuple[tuple[str, float], ...] = (
    ("over", 0.5), ("over", 1.5), ("under", 2.5), ("over", 2.5),
    ("under", 3.5), ("under", 4.5), ("under", 5.5))
# Hándicap asiático: líneas enteras y medias, con protección masiva al underdog (+1 a +3).
LINEAS_HANDICAP: tuple[float, ...] = (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
MERCADOS = ("h2h", "totals", "team_totals_home", "team_totals_away", "spreads",
            "btts", "corners", "cards", "corners_home", "corners_away",
            "double_chance", "player_points", "player_rebounds", "player_assists",
            "player_threes", "handicap_games", "total_games")
# Mercados del modelo estadístico (se liquidan con la estadística del partido).
ESTADISTICOS = ("corners", "cards", "corners_home", "corners_away")
# Ambos anotan desde el ajuste de goles de Pinnacle.
BTTS_LADOS: tuple[str, ...] = ("yes",)
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Opcion:
    """Un candidato con la cuota que de verdad se puede tomar."""
    match_id: str
    cand: Candidato
    price: float
    book: str
    odds_source: str = ""
    odds_as_of: datetime | None = None

    @property
    def ev(self) -> float:
        return self.cand.prob * self.price - 1.0


def prob_handicap(p: dict[str, float], m, lado: str, linea: float) -> float | None:
    """
    Probabilidad justa de `lado` con hándicap asiático `linea`, condicionada a
    que no haya devolución. 0 y ±0,5 salen exactas del 1X2; el resto, de la
    matriz de marcadores `m` del ajuste de goles (None si el ajuste falló).
    """
    if linea == 0.0:
        return p[lado] / (p["home"] + p["away"])
    if linea == 0.5:
        return p[lado] + p["draw"]
    if linea == -0.5:
        return p[lado]
    if m is None:
        return None
    from ..model.pricing import market_asian_handicap
    return market_asian_handicap(m, linea if lado == "home" else -linea)[lado]


def candidatos_handicap(p: dict[str, float], m, lineas: tuple[float, ...] | None = None
                        ) -> list[Candidato]:
    lineas = LINEAS_HANDICAP if lineas is None else lineas
    out = []
    for lado in ("home", "away"):
        for linea in lineas:
            prob = prob_handicap(p, m, lado, linea)
            if prob is not None:
                out.append(Candidato("spreads", lado, linea, prob))
    return out


def texto_handicap(selection: str, line: float, local: str, visitante: str) -> str:
    equipo = local if selection == "home" else visitante
    if line == 0:
        return f"{equipo} gana (empate devuelve)"
    if line == 0.5:
        return f"{equipo} o empate"
    if line == -0.5:
        return f"Gana {equipo}"
    return f"{equipo} {'+' if line > 0 else ''}{f'{line:g}'.replace('.', ',')} (hándicap asiático)"


def target_nuevo(abiertos: list[float | int]) -> float | None:
    """
    Próximo objetivo de cuota de TARGETS que no esté ya abierto.
    Como mucho un reto abierto de cada objetivo (5.5, 10.2, 15.3, 20.5, 30.3, 40.2).
    """
    abiertos_set = {float(x) for x in abiertos}
    return next((t for t in TARGETS if t not in abiertos_set), None)


def longitud_nuevo(abiertos: list[int | float]) -> float | int | None:
    """Compatibilidad: retorna el próximo objetivo de cuota disponible."""
    return target_nuevo(abiertos)


@dataclass(frozen=True)
class Abierto:
    """Un reto que necesita escalón (`reto_id` None: uno nuevo hacia `target_cuota`)."""
    reto_id: int | None
    ganados: int
    objetivo: int = MAX_ESCALONES
    prob_ganada: float = 1.0           # ∏ p de los escalones elegidos que cuentan
    prob_objetivo: float | None = PROB_RETO   # None: regla anterior (rango de cuota)
    cuota_min: float = CUOTA_MIN
    cuota_max: float = CUOTA_MAX
    target_cuota: float | None = None
    saldo_actual: Decimal = STAKE


def umbral(prob_objetivo: float, prob_ganada: float, restantes: int) -> float:
    """
    Probabilidad mínima del siguiente escalón para que el reto entero quede en
    ≥ `prob_objetivo`: lo que falta se reparte a partes iguales entre los
    `restantes`. No baja nunca de PROB_MIN.
    """
    if restantes <= 0:
        return PROB_MIN
    calc = (prob_objetivo / prob_ganada) ** (1.0 / restantes)
    return max(PROB_MIN, calc)


def valida(o: Opcion, cuota_min: float = CUOTA_MIN, cuota_max: float = CUOTA_MAX,
           ev_min: float | None = EV_MIN, prob_min: float = PROB_MIN, prob_max: float = PROB_MAX) -> bool:
    return (o.cand.market in MERCADOS and cuota_min <= o.price <= cuota_max
            and prob_min <= o.cand.prob <= prob_max and (ev_min is None or o.ev >= ev_min))


def _orden(o: Opcion) -> tuple:
    """El más probable; a igualdad, el de más valor y la cuota más alta."""
    return (round(o.cand.prob, 6), round(o.ev, 6), o.price)


def elegir(opciones: list[Opcion], reto: Abierto,
           usados: set[str] = frozenset()) -> Opcion | None:
    """El escalón de `reto` entre las opciones de partidos no `usados`."""
    if reto.target_cuota is not None or reto.prob_objetivo is None:
        prob_min, prob_max = PROB_MIN, PROB_MAX
    else:
        restantes = max(1, reto.objetivo - reto.ganados)
        prob_min = max(PROB_MIN, umbral(reto.prob_objetivo, reto.prob_ganada, restantes))
        prob_max = PROB_MAX
    dentro = [o for o in opciones if o.match_id not in usados
              and valida(o, reto.cuota_min, reto.cuota_max, prob_min=prob_min, prob_max=prob_max)]
    return max(dentro, key=_orden, default=None)


def _del_dia(opciones: list[Opcion], reto: Abierto, usados: set[str]) -> list[Opcion]:
    """
    Los escalones de `reto` hoy: hasta POR_DIA en partidos distintos (uno solo
    en los retos de la regla anterior). Cada uno gasta su parte del presupuesto
    como si el anterior ya se hubiera ganado: es lo que hace falta para cobrar.
    """
    tope = POR_DIA if reto.prob_objetivo is not None else 1
    out: list[Opcion] = []
    saldo = reto.saldo_actual
    target = reto.target_cuota
    target_cobro = (STAKE * Decimal(str(target))) if target is not None else None

    while len(out) < tope and reto.ganados < reto.objetivo:
        if target_cobro is not None and saldo >= target_cobro:
            break
        o = elegir(opciones, reto, usados)
        if o is None:
            break
        usados.add(o.match_id)
        out.append(o)
        nuevo_saldo = _q(saldo * Decimal(str(o.price)))
        reto = Abierto(reto.reto_id, reto.ganados + 1, reto.objetivo,
                       reto.prob_ganada * o.cand.prob, reto.prob_objetivo,
                       reto.cuota_min, reto.cuota_max,
                       target_cuota=reto.target_cuota,
                       saldo_actual=nuevo_saldo)
    return out


def planificar(en_curso: list[Abierto], abiertos: list[int | float], opciones: list[Opcion],
               ocupados: set[str] = frozenset()
               ) -> list[tuple[int | None, int | float | None, list[Opcion]]]:
    """
    Reparto del día: [(reto_id, None, escalones)] para los retos que necesitan
    escalón y [(None, target_o_pasos, escalones)] para los retos nuevos.

    - `en_curso`: los retos que esperan su siguiente escalón (no vencidos); se
      sirven primero, el más avanzado antes. Si alguno se queda sin escalón,
      no se abre ningún reto nuevo ese día.
    - `abiertos`: targets (o pasos) de los retos abiertos.
    - Un partido no se repite el mismo día ni coincide con un escalón aún sin
      liquidar (`ocupados`): dos retos no dependen del mismo resultado.
    """
    usados = set(ocupados)
    plan: list[tuple[int | None, int | float | None, list[Opcion]]] = []
    sin_escalon = False
    for reto in sorted(en_curso, key=lambda r: -r.ganados):
        escalones = _del_dia(opciones, reto, usados)
        if not escalones:
            sin_escalon = True
            continue
        plan.append((reto.reto_id, None, escalones))
    if sin_escalon:
        return plan
    abiertos_list = list(abiertos)
    while (t := target_nuevo(abiertos_list)) is not None:
        escalones = _del_dia(opciones, Abierto(None, 0, objetivo=MAX_ESCALONES, target_cuota=t), usados)
        if not escalones:
            break
        plan.append((None, t, escalones))
        abiertos_list.append(t)
    return plan


@dataclass(frozen=True)
class Paso:
    paso: int
    price: float
    outcome: str | None        # None: sin liquidar · 'win' · 'loss' · 'void'


def _q(x: Decimal) -> Decimal:
    return x.quantize(_CENT, rounding=ROUND_HALF_UP)


def estado(stake: Decimal, objetivo: int, freeroll_x: float | None,
           pasos: list[Paso], vencido: bool = False,
           target_cuota: float | None = None) -> dict:
    """
    El estado de un reto a partir de sus escalones, sin guardar nada:

    - 'esperando': el último escalón no está liquidado (`en_juego` es lo apostado).
    - 'en_curso': hace falta elegir el siguiente escalón.
    - 'completado' / 'fallido': cerrado; `ganancia` = lo cobrado − stake.
    - 'expirado': `vencido` (pasó DIAS_MAX) sin escalón pendiente ni completar;
      se cobra el saldo y no cuenta como cumplido.

    Un escalón 'void' (aplazado) o 'push' (hándicap entero devuelto) no cuenta
    y no mueve el saldo.
    """
    stake = Decimal(stake)
    saldo, retirado, ganados = stake, Decimal("0"), 0
    meta_payout = _q(stake * Decimal(str(target_cuota))) if target_cuota is not None else None

    for p in sorted(pasos, key=lambda p: p.paso):
        if p.outcome is None:
            return {"estado": "esperando", "saldo": _q(saldo), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": _q(saldo), "ganancia": None,
                    "target_cuota": target_cuota}
        if p.outcome in ("void", "push"):
            continue
        if p.outcome == "loss":
            return {"estado": "fallido", "saldo": Decimal("0.00"), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": None, "ganancia": _q(retirado - stake),
                    "target_cuota": target_cuota}
        saldo = _q(saldo * Decimal(str(p.price)))
        ganados += 1
        if freeroll_x and retirado == 0 and saldo >= Decimal(str(freeroll_x)) * stake:
            retirado, saldo = stake, saldo - stake

        completado = False
        if meta_payout is not None:
            if (saldo + retirado) >= meta_payout or ganados >= objetivo:
                completado = True
        elif ganados >= objetivo:
            completado = True

        if completado:
            return {"estado": "completado", "saldo": _q(saldo), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": None,
                    "ganancia": _q(saldo + retirado - stake),
                    "target_cuota": target_cuota}

    if vencido:
        return {"estado": "expirado", "saldo": _q(saldo), "retirado": _q(retirado),
                "ganados": ganados, "en_juego": None, "ganancia": _q(saldo + retirado - stake),
                "target_cuota": target_cuota}
    return {"estado": "en_curso", "saldo": _q(saldo), "retirado": _q(retirado),
            "ganados": ganados, "en_juego": None, "ganancia": None,
            "target_cuota": target_cuota}


CERRADOS = ("completado", "fallido", "expirado")


def resumen(retos: list[dict]) -> dict:
    """Historial de retos cerrados (también los expirados): cuántos se completan y lo que dejan."""
    cerrados = [r for r in retos if r["estado"] in CERRADOS]
    if not cerrados:
        return {"cerrados": 0, "completados": 0, "expirados": 0, "tasa_completados": None,
                "invertido": "0.00", "ganancia": "0.00", "roi": None}
    invertido = sum(Decimal(str(r["stake_inicial"])) for r in cerrados)
    ganancia = sum(Decimal(str(r["ganancia"])) for r in cerrados)
    completados = sum(1 for r in cerrados if r["estado"] == "completado")
    return {"cerrados": len(cerrados), "completados": completados,
            "expirados": sum(1 for r in cerrados if r["estado"] == "expirado"),
            "tasa_completados": round(completados / len(cerrados) * 100, 1),
            "invertido": str(_q(invertido)), "ganancia": str(_q(ganancia)),
            "roi": round(float(ganancia / invertido) * 100, 1)}


def texto_total(market: str, selection: str, line: float,
                local: str = "", visitante: str = "") -> str:
    cosa = {"corners": "córners", "cards": "tarjetas",
            "corners_home": f"córners de {local}",
            "corners_away": f"córners de {visitante}"}[market]
    return f"{'Más' if selection == 'over' else 'Menos'} de {f'{line:g}'.replace('.', ',')} {cosa}"


def texto_btts(selection: str) -> str:
    return "Ambos equipos marcan" if selection == "yes" else "No marcan los dos"
