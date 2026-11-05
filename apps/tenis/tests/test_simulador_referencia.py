"""Referencia INDEPENDIENTE del simulador: programación dinámica hacia delante a nivel de PUNTO (tabla de estados
memoizada por paso), sin ninguna fórmula cerrada ni código de `tenis.simulador`.

- Juego, tiebreak y set avanzan punto a punto con los marcadores reales (sin colapsar el deuce ni la igualdad
  del tiebreak); la masa que queda viva al cortar y la podada (< PODA) se devuelven como cota del error.
- El saque alterna juego a juego (el tiebreak cuenta como un juego) y el sacador del set siguiente se LEE del
  estado final, no se deduce por paridad: comprueba la regla del plan G.2 por otro camino.
- El partido se compone recorriendo con recursión todas las secuencias de sets (otro camino que el tensorial).
Las pruebas de este archivo comparan cada pieza cerrada con esta referencia.
"""
import pytest

from tenis.simulador import Formato, distribucion_partido
from tenis.simulador.juego import distribucion_juego, ganar_juego
from tenis.simulador.set_ import tabla_set
from tenis.simulador.tiebreak import distribucion_tiebreak, ganar_tiebreak

PODA = 1e-20
PASOS = 4000


def _avanzar(vivos: dict, paso, fin: dict) -> tuple[dict, float]:
    nuevo, podado = {}, 0.0
    for estado, m in vivos.items():
        for sig, pm in paso(estado):
            masa = m * pm
            if isinstance(sig, tuple) and sig and sig[0] == "FIN":
                fin[sig[1]] = fin.get(sig[1], 0.0) + masa
            elif masa < PODA:
                podado += masa
            else:
                nuevo[sig] = nuevo.get(sig, 0.0) + masa
    return nuevo, podado


def _correr(inicial, paso):
    vivos, fin, error = {inicial: 1.0}, {}, 0.0
    for _ in range(PASOS):
        if not vivos:
            break
        vivos, podado = _avanzar(vivos, paso, fin)
        error += podado
    return fin, error + sum(vivos.values())


def ref_juego(p):
    """Marcador final de puntos del juego (sacador, restador) → prob."""
    def paso(e):
        a, b = e
        for x, y, pm in ((a + 1, b, p), (a, b + 1, 1 - p)):
            if max(x, y) >= 4 and abs(x - y) >= 2:
                yield ("FIN", (x, y)), pm
            else:
                yield (x, y), pm
    return _correr((0, 0), paso)


def _saca_primero_tb(n):
    return ((n + 1) // 2) % 2 == 0


def ref_tiebreak(pa, pb, k, primero):
    """Tiebreak a k: marcador final (A, B) → prob. primero ∈ {'A', 'B'}."""
    def paso(e):
        a, b = e
        saca = primero if _saca_primero_tb(a + b) else ("B" if primero == "A" else "A")
        w = pa if saca == "A" else 1 - pb
        for x, y, pm in ((a + 1, b, w), (a, b + 1, 1 - w)):
            if max(x, y) >= k and abs(x - y) >= 2:
                yield ("FIN", (x, y)), pm
            else:
                yield (x, y), pm
    return _correr((0, 0), paso)


def ref_set(pa, pb, primero, regla, max_juegos=10**6):
    """Set a nivel de punto. Estado: (juegos A, juegos B, puntos A, puntos B, sacador del juego, en_tb, objetivo,
    sacador del 1.er punto del tb). Final: (ga, gb, tb, sacador del juego siguiente) → prob; los sets de ventaja
    que superan max_juegos se cortan como ('cola', ganador_pendiente) con su masa."""
    otro = {"A": "B", "B": "A"}

    def termina_set(ga, gb, tb):
        hi, lo = max(ga, gb), min(ga, gb)
        if tb:
            return True
        if regla == "ventaja":
            return hi >= 6 and hi - lo >= 2
        return (hi == 6 and lo <= 4) or (hi == 7 and lo == 5)

    def paso(e):
        ga, gb, a, b, srv, tb, obj, tb1 = e
        if tb:
            saca = tb1 if _saca_primero_tb(a + b) else otro[tb1]
        else:
            saca = srv
        w = pa if saca == "A" else 1 - pb
        for gana_a, pm in ((True, w), (False, 1 - w)):
            x, y = (a + 1, b) if gana_a else (a, b + 1)
            meta = obj if tb else 4
            if not (max(x, y) >= meta and abs(x - y) >= 2):
                yield (ga, gb, x, y, srv, tb, obj, tb1), pm
                continue
            nga, ngb, nsrv = ga + (x > y), gb + (y > x), otro[srv]          # el saque pasa al otro
            if regla == "ventaja" and max(nga, ngb) > max_juegos:
                yield ("FIN", ("cola", nga - ngb, nsrv)), pm
            elif termina_set(nga, ngb, tb):
                yield ("FIN", (nga, ngb, tb, nsrv)), pm
            elif nga == 6 and ngb == 6 and regla != "ventaja":
                yield (nga, ngb, 0, 0, nsrv, True, 10 if regla == "tiebreak_10" else 7, nsrv), pm
            else:
                yield (nga, ngb, 0, 0, nsrv, False, 0, None), pm

    if regla == "super_tiebreak_10":
        fin, err = _correr((0, 0, 0, 0, primero, True, 10, primero), paso)
        return {(1 if a > b else 0, 1 if b > a else 0, True, s): m for (a, b, _, s), m in fin.items()}, err
    return _correr((0, 0, 0, 0, primero, False, 0, None), paso)


def ref_partido(pa, pb, formato: Formato):
    """Marcador completo → prob (primer sacador 50/50), componiendo las tablas de ref_set por recursión."""
    tablas = {}
    for s in "AB":
        for regla in {"tiebreak_7", formato.decisivo}:
            tablas[(s, regla)] = ref_set(pa, pb, s, regla)[0]
    need, out = formato.sets_para_ganar, {}

    def rec(pref, sa, sb, srv, prob):
        if sa == need or sb == need:
            out[pref] = out.get(pref, 0.0) + prob
            return
        regla = formato.decisivo if len(pref) == formato.mejor_de - 1 else "tiebreak_7"
        for (x, y, tb, sig), pm in tablas[(srv, regla)].items():
            rec(pref + ((x, y, tb),), sa + (x > y), sb + (y > x), sig, prob * pm)

    rec((), 0, 0, "A", 0.5)
    rec((), 0, 0, "B", 0.5)
    return out


PARES = [(0.5, 0.5), (0.65, 0.62), (0.60, 0.55), (0.72, 0.58), (0.30, 0.45), (0.95, 0.95), (0.98, 0.02),
         (0.02, 0.02)]


@pytest.mark.parametrize("p", [0.02, 0.3, 0.5, 0.65, 0.9, 0.98])
def test_juego_cerrado_igual_a_referencia_de_puntos(p):
    fin, err = ref_juego(p)
    assert err < 1e-15
    assert abs(ganar_juego(p) - sum(m for (a, b), m in fin.items() if a > b)) < 1e-14
    d = distribucion_juego(p, rondas=40)
    for marcador, m in d.puntos.items():
        assert abs(m - fin.get(marcador, 0.0)) < 1e-15


@pytest.mark.parametrize("pa,pb", PARES)
@pytest.mark.parametrize("k", [7, 10])
@pytest.mark.parametrize("primero", ["A", "B"])
def test_tiebreak_cerrado_igual_a_referencia_de_puntos(pa, pb, k, primero):
    fin, err = ref_tiebreak(pa, pb, k, primero)
    ref_gana = sum(m for (a, b), m in fin.items() if a > b)
    assert abs(ganar_tiebreak(pa, pb, k, primero) - ref_gana) < 1e-12 + err
    d = distribucion_tiebreak(pa, pb, k, primero, rondas=30)
    peor = max(abs(m - fin.get(mc, 0.0)) for mc, m in d.puntos.items())
    assert peor < 1e-14
    assert abs(sum(d.puntos.values()) + d.cola_a + d.cola_b - 1.0) < 1e-12


@pytest.mark.parametrize("pa,pb", PARES)
@pytest.mark.parametrize("regla", ["tiebreak_7", "tiebreak_10", "super_tiebreak_10"])
@pytest.mark.parametrize("primero", ["A", "B"])
def test_set_cerrado_igual_a_referencia_de_puntos(pa, pb, regla, primero):
    ref, err = ref_set(pa, pb, primero, regla)
    assert err < 1e-12
    t = tabla_set(pa, pb, primero, regla)
    for (a, b, tb), m, sig in zip(t.marcadores, t.prob, t.siguiente_saca):
        assert abs(m - ref.get((a, b, tb, sig), 0.0)) < 1e-13, (a, b, tb, sig)
    assert abs(sum(t.prob) - sum(ref.values())) < 1e-12


@pytest.mark.parametrize("pa,pb", [(0.55, 0.52), (0.65, 0.62), (0.40, 0.60)])
@pytest.mark.parametrize("primero", ["A", "B"])
def test_set_de_ventaja_con_cola_igual_a_referencia(pa, pb, primero):
    max_j = 12
    ref, _ = ref_set(pa, pb, primero, "ventaja", max_juegos=max_j)
    t = tabla_set(pa, pb, primero, "ventaja", max_juegos=max_j)
    for (a, b, tb), m, sig in zip(t.marcadores, t.prob, t.siguiente_saca):
        assert abs(m - ref.get((a, b, tb, sig), 0.0)) < 1e-13
    cola_ref = sum(m for k, m in ref.items() if k[0] == "cola")
    assert abs(t.cola_a + t.cola_b - cola_ref) < 1e-13


def test_set_de_ventaja_cola_cerrada_igual_a_referencia_sin_cortar():
    """La cola geométrica cerrada reparte bien el ganador: referencia de puntos sin límite de juegos."""
    t = tabla_set(0.65, 0.62, "B", "ventaja", max_juegos=12)
    ref_completo, err = ref_set(0.65, 0.62, "B", "ventaja")
    assert err < 1e-12
    assert abs(t.gana_a - sum(m for (a, b, *_), m in ref_completo.items() if a > b)) < 1e-12
    assert abs(t.cola_a - sum(m for (a, b, *_), m in ref_completo.items() if a > b and a > 12)) < 1e-12


@pytest.mark.parametrize("pa,pb", [(0.64, 0.62), (0.58, 0.66), (0.95, 0.95)])
@pytest.mark.parametrize("formato", [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"),
                                     Formato(3, "super_tiebreak_10")])
def test_partido_igual_a_referencia_compuesta(pa, pb, formato):
    ref = ref_partido(pa, pb, formato)
    d = distribucion_partido(pa, pb, formato).marcadores()
    assert set(d) == set(ref)
    assert max(abs(d[k] - ref[k]) for k in ref) < 1e-13


def test_partido_mejor_de_5_igual_a_referencia_compuesta():
    f = Formato(5, "tiebreak_10")
    ref = ref_partido(0.66, 0.63, f)
    d = distribucion_partido(0.66, 0.63, f).marcadores()
    assert set(d) == set(ref)
    assert max(abs(d[k] - ref[k]) for k in ref) < 1e-13
