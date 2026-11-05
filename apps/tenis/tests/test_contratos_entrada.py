"""Contratos base y de entrada: casos absurdos rechazados y casos límite aceptados."""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tenis.contratos.base import Contrato, DuracionMin, Hash256, ProbPunto
from tenis.contratos.entrada import EstadoJugador, ParametrosPunto, PartidoPrevio

UTC = timezone.utc
INICIO = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)


def partido(**cambios):
    datos = dict(
        partido_id=1, jugador_1=10, jugador_2=20, mejor_de=3, regla_decisivo="tiebreak_7",
        superficie="Clay", indoor=False, corte=INICIO - timedelta(hours=2),
        inicio_programado_mas_temprano=INICIO,
    )
    datos.update(cambios)
    return datos


class _Punto(Contrato):
    p: ProbPunto


class _Duracion(Contrato):
    d: DuracionMin


def test_probabilidad_de_punto_abierta_rechaza_0_y_1():
    with pytest.raises(ValidationError):
        _Punto(p=0.0)
    with pytest.raises(ValidationError):
        _Punto(p=1.0)
    assert _Punto(p=0.5).p == 0.5


@pytest.mark.parametrize("valor", [0.0, 0.01, 0.99, 1.0, float("nan"), float("inf"), float("-inf")])
def test_parametros_punto_rechaza_fuera_de_rango_y_no_finitos(valor):
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=valor, p2=0.6, covarianza=[[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=0.6, p2=valor, covarianza=[[1.0, 0.0], [0.0, 1.0]])


def test_parametros_punto_acepta_limites_0_02_y_0_98():
    for p in (0.02, 0.98):
        assert ParametrosPunto(p1=p, p2=p, covarianza=[[1.0, 0.0], [0.0, 1.0]]).p1 == p


def test_parametros_punto_covarianza_asimetrica_o_no_definida_se_rechaza():
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=0.6, p2=0.6, covarianza=[[1.0, 0.1], [0.2, 1.0]])
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=0.6, p2=0.6, covarianza=[[1.0, 2.0], [2.0, 1.0]])
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=0.6, p2=0.6, covarianza=[[1.0, 1.0], [1.0, 1.0]])
    with pytest.raises(ValidationError):
        ParametrosPunto(p1=0.6, p2=0.6, covarianza=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def test_parametros_punto_acepta_covarianza_3x3_definida_positiva():
    m = [[1.0, 0.3, 0.1], [0.3, 1.0, 0.2], [0.1, 0.2, 1.0]]
    assert len(ParametrosPunto(p1=0.5, p2=0.5, covarianza=m).covarianza) == 3


def test_instante_sin_zona_se_rechaza():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(corte=datetime(2026, 11, 10, 12, 0)))


def test_campo_de_mas_se_rechaza():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(campo_extra=1))


def test_jugadores_iguales_se_rechazan():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(jugador_2=10))


def test_mejor_de_4_se_rechaza():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(mejor_de=4))


def test_regla_decisiva_inexistente_en_formato_se_rechaza():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(mejor_de=5, regla_decisivo="tiebreak_7"))


def test_indoor_exige_coherencia_con_superficie():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(superficie="Indoor", indoor=False))
    assert PartidoPrevio(**partido(superficie="Indoor", indoor=True)).superficie == "Indoor"


def test_corte_debe_ser_anterior_al_inicio_mas_temprano():
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(corte=INICIO))
    with pytest.raises(ValidationError):
        PartidoPrevio(**partido(corte=INICIO + timedelta(minutes=1)))


def test_partido_previo_valido_y_congelado():
    p = PartidoPrevio(**partido(indoor=None))
    assert p.indoor is None and p.mejor_de == 3
    with pytest.raises(ValidationError):
        p.mejor_de = 5


@pytest.mark.parametrize("campo", ["media", "varianza"])
@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_estado_jugador_no_finitos_se_rechazan(campo, valor):
    datos = dict(jugador_id=1, media=0.0, varianza=1.0, n_partidos_previos=3, minutos_96h=0.0)
    datos[campo] = valor
    with pytest.raises(ValidationError):
        EstadoJugador(**datos)


@pytest.mark.parametrize("varianza", [0.0, -1.0])
def test_estado_jugador_varianza_no_positiva_se_rechaza(varianza):
    with pytest.raises(ValidationError):
        EstadoJugador(jugador_id=1, media=0.0, varianza=varianza, n_partidos_previos=0, minutos_96h=0.0)


def test_estado_jugador_minutos_nulos_solo_con_fatiga_desconocida():
    with pytest.raises(ValidationError):
        EstadoJugador(jugador_id=1, media=0.0, varianza=1.0, n_partidos_previos=0, minutos_96h=None)
    e = EstadoJugador(jugador_id=1, media=0.0, varianza=1.0, n_partidos_previos=0,
                      minutos_96h=None, fatiga_desconocida=True)
    assert e.minutos_96h is None


def test_estado_jugador_partidos_previos_negativos_se_rechazan():
    with pytest.raises(ValidationError):
        EstadoJugador(jugador_id=1, media=0.0, varianza=1.0, n_partidos_previos=-1, minutos_96h=0.0)


@pytest.mark.parametrize("valor", [0, -5])
def test_duracion_no_positiva_se_rechaza(valor):
    with pytest.raises(ValidationError):
        _Duracion(d=valor)
    assert _Duracion(d=95).d == 95


@pytest.mark.parametrize("valor", ["", "A" * 63, "a" * 63, "A" * 64, "g" * 64])
def test_hash_mal_formado_se_rechaza(valor):
    class _H(Contrato):
        h: Hash256
    with pytest.raises(ValidationError):
        _H(h=valor)


def test_hash_valido_pasa():
    class _H(Contrato):
        h: Hash256
    assert _H(h="a" * 64).h == "a" * 64
