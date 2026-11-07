"""Sellado criptográfico, inmutabilidad y verificación de cadena (plan §H.3, Sprint 6).

Garantías:
1. Corte fijo anterior al sellado (`corte <= sellado_en`).
2. Sello previo al inicio programado (`sellado_en < inicio_programado_utc`, G-tiempo).
3. Redondeo estricto de todas las probabilidades a 6 decimales antes de serializar (reproducibilidad Windows/Linux).
4. Cadena inmutable de hashes SHA-256 enlazada desde el génesis (64 ceros).
5. Contratos Pydantic: `DistribucionPartido` validada antes de sellar; `PronosticoSellado` validado antes de servir.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Jsonb

from tenis.contratos.salida import DistribucionPartido, PronosticoSellado

GENESIS = "0" * 64


class ErrorSellado(Exception):
    """Error base del módulo de sellado."""


class SelloTardioError(ErrorSellado):
    """El partido ya inició o la hora programada ya llegó."""


class CorteFuturoError(ErrorSellado):
    """El corte no puede ser posterior al momento del sellado."""


class InicioDesconocidoError(ErrorSellado):
    """El partido no tiene inicio programado conocido o tiene horas indefinidas."""


class CadenaRotaError(ErrorSellado):
    """Discrepancia en la cadena de hashes o alteración detectada."""


class ContratoInvalidoError(ErrorSellado):
    """El contenido del sello no satisface el contrato Pydantic."""


def json_canonico(valor: Any) -> str:
    """Serialización canónica documentada en 0006_sellado.sql (tenis.json_canonico)."""
    if isinstance(valor, dict):
        partes = [
            json.dumps(k, ensure_ascii=False) + ":" + json_canonico(valor[k])
            for k in sorted(valor, key=lambda s: s.encode("utf-8"))
        ]
        return "{" + ",".join(partes) + "}"
    if isinstance(valor, list):
        return "[" + ",".join(json_canonico(x) for x in valor) + "]"
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, str):
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, float):
        r = repr(valor)
        if "e" in r or "E" in r:
            # PostgreSQL jsonb numeric prints small numbers without scientific notation
            s = f"{valor:.6f}".rstrip("0")
            return s if s else "0"
        return r
    raise TypeError(f"Tipo no serializable: {type(valor)}")


def instante_iso(dt: datetime) -> str:
    """Formato ISO UTC canónico con microsegundos: AAAA-MM-DDTHH:MM:SS.USZ."""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def calcular_hash_sello(
    partido_id: int,
    version_modelo: str,
    version_datos: str,
    corte: datetime,
    sellado_en: datetime,
    entradas: dict,
    distribucion: dict,
    referencia: dict,
    hash_previo: str,
) -> str:
    """Recalcula el hash SHA-256 independiente de PostgreSQL."""
    cuerpo = [
        partido_id,
        version_modelo,
        version_datos,
        instante_iso(corte),
        instante_iso(sellado_en),
        entradas,
        distribucion,
        referencia,
        hash_previo,
    ]
    return hashlib.sha256(json_canonico(cuerpo).encode("utf-8")).hexdigest()


def redondear_distribucion(dist: DistribucionPartido | dict) -> DistribucionPartido:
    """Redondea estrictamente a 6 decimales todas las probabilidades de la distribución.

    Ajusta el residuo de suma en la entrada más probable para garantizar suma == 1.0 exacto,
    y recalcula los mercados para preservar coherencia matemática (TOLERANCIA <= 1e-9).
    """
    if isinstance(dist, DistribucionPartido):
        d = dist.model_dump()
    else:
        d = dict(dist)

    mejor_de = d["mejor_de"]
    regla_decisivo = d["regla_decisivo"]
    entradas_raw = d["entradas"]

    # 1. Redondear entradas
    entradas_red = []
    for e in entradas_raw:
        sets_data = e["sets"]
        p = round(float(e["probabilidad"]), 6)
        entradas_red.append({"sets": sets_data, "probabilidad": p})

    # 2. Ajuste de residuo para sumar 1.0 exacto
    tot = round(sum(e["probabilidad"] for e in entradas_red), 6)
    diff = round(1.0 - tot, 6)
    if diff != 0.0 and entradas_red:
        max_idx = max(range(len(entradas_red)), key=lambda i: entradas_red[i]["probabilidad"])
        entradas_red[max_idx]["probabilidad"] = round(entradas_red[max_idx]["probabilidad"] + diff, 6)

    entradas_finales = [e for e in entradas_red if e["probabilidad"] > 0.0]
    total_final = sum(e["probabilidad"] for e in entradas_finales)
    if abs(total_final - 1.0) > 1e-9:
        raise ValueError(f"Suma de masa tras redondeo {total_final:.12f} != 1.0")

    # 3. Recalcular mercados desde entradas_finales
    def _ganados(sets):
        a = sum(1 for s in sets if (s.juegos_a if hasattr(s, "juegos_a") else s["juegos_a"]) >
                                   (s.juegos_b if hasattr(s, "juegos_b") else s["juegos_b"]))
        return a, len(sets) - a

    def _juegos_tot(sets):
        return sum((s.juegos_a if hasattr(s, "juegos_a") else s["juegos_a"]) +
                   (s.juegos_b if hasattr(s, "juegos_b") else s["juegos_b"]) for s in sets)

    def _prob(cond):
        return round(sum(e["probabilidad"] for e in entradas_finales if cond(e["sets"])), 6)

    mercados_in = d.get("mercados", {})
    if hasattr(mercados_in, "model_dump"):
        mercados_in = mercados_in.model_dump()

    mercados_nuevos = {
        "gana_a": _prob(lambda s: _ganados(s)[0] > _ganados(s)[1]),
        "primer_set_a": _prob(lambda s: (s[0].juegos_a if hasattr(s[0], "juegos_a") else s[0]["juegos_a"]) >
                                         (s[0].juegos_b if hasattr(s[0], "juegos_b") else s[0]["juegos_b"])),
        "sets_mas_de": {},
        "juegos_mas_de": {},
        "handicap_sets": {},
    }

    for k in mercados_in.get("sets_mas_de", {}):
        L = float(k)
        mercados_nuevos["sets_mas_de"][k] = _prob(lambda s, L=L: len(s) > L)

    for k in mercados_in.get("juegos_mas_de", {}):
        L = float(k)
        mercados_nuevos["juegos_mas_de"][k] = _prob(lambda s, L=L: _juegos_tot(s) > L)

    for k in mercados_in.get("handicap_sets", {}):
        h = float(k)
        mercados_nuevos["handicap_sets"][k] = _prob(lambda s, h=h: _ganados(s)[0] - _ganados(s)[1] + h > 0)

    return DistribucionPartido.model_validate({
        "mejor_de": mejor_de,
        "regla_decisivo": regla_decisivo,
        "entradas": entradas_finales,
        "mercados": mercados_nuevos,
    })


def sellar_pronostico(
    db: Any,
    partido_id: int,
    version_modelo: str,
    version_datos: str,
    corte: datetime,
    entradas: dict,
    distribucion: DistribucionPartido | dict,
    referencia_mercado: dict | None = None,
) -> str:
    """Valida los contratos y sella el pronóstico mediante `tenis.sellar_pronostico` en Postgres.

    Rechaza:
    - Corte futuro respecto a la hora actual.
    - Sellado posterior al inicio programado del partido (G-tiempo).
    - Partidos sin inicio programado conocido.
    - Distribuciones que no satisfagan `DistribucionPartido`.
    """
    if not corte.tzinfo:
        corte = corte.replace(tzinfo=timezone.utc)
    ahora_utc = datetime.now(timezone.utc)

    if corte > ahora_utc:
        raise CorteFuturoError(f"Corte {corte.isoformat()} es posterior al sellado {ahora_utc.isoformat()}")

    # Validar y redondear a 6 decimales
    dist_valida = redondear_distribucion(distribucion)
    dist_dict = dist_valida.model_dump()

    # Pre-comprobación de horario en programa si la conexión lo permite
    row = db.execute(
        "SELECT min(inicio_programado_utc), count(*) FILTER (WHERE inicio_programado_utc IS NULL) "
        "FROM programa WHERE partido_id = %s",
        (partido_id,),
    ).fetchone()
    if not row or row[0] is None or (row[1] is not None and row[1] > 0):
        raise InicioDesconocidoError(f"partido {partido_id} sin inicio programado conocido: no se sella")

    inicio_utc = row[0]
    if not inicio_utc.tzinfo:
        inicio_utc = inicio_utc.replace(tzinfo=timezone.utc)
    if ahora_utc >= inicio_utc:
        raise SelloTardioError(f"sellado tardio del partido {partido_id}: el inicio programado ya llego")

    ref = referencia_mercado or {}

    try:
        res = db.execute(
            "SELECT sellar_pronostico(%s, %s, %s, %s, %s, %s, %s)",
            (
                partido_id,
                version_modelo,
                version_datos,
                corte,
                Jsonb(entradas),
                Jsonb(dist_dict),
                Jsonb(ref),
            ),
        ).fetchone()
        return res[0]
    except Exception as e:
        msg = str(e).lower()
        if "tardio" in msg:
            raise SelloTardioError(str(e)) from e
        if "futuro" in msg:
            raise CorteFuturoError(str(e)) from e
        if "sin inicio programado" in msg:
            raise InicioDesconocidoError(str(e)) from e
        raise ErrorSellado(f"Fallo en sellar_pronostico: {e}") from e


def verificar_cadena(db: Any, desde_id: int | None = None) -> dict:
    """Verifica la integridad de la cadena criptográfica de sellos en `tenis.pronostico`.

    Recalcula la huella SHA-256 de cada fila, verifica el enlace con `hash_previo` y
    valida el contrato Pydantic `DistribucionPartido`. Falla en la primera ruptura.
    """
    consulta = (
        "SELECT pronostico_id, partido_id, version_modelo, version_datos, corte, sellado_en, "
        "entradas, distribucion, referencia_mercado, hash_previo, hash "
        "FROM pronostico "
    )
    params = ()
    if desde_id is not None:
        consulta += "WHERE pronostico_id >= %s "
        params = (desde_id,)
    consulta += "ORDER BY pronostico_id ASC"

    filas = db.execute(consulta, params).fetchall()
    columnas = [
        "pronostico_id",
        "partido_id",
        "version_modelo",
        "version_datos",
        "corte",
        "sellado_en",
        "entradas",
        "distribucion",
        "referencia_mercado",
        "hash_previo",
        "hash",
    ]

    registros = [dict(zip(columnas, f)) for f in filas]

    previo = GENESIS
    if desde_id is not None and desde_id > 1:
        # Obtener el hash del registro anterior inmediato
        ant = db.execute(
            "SELECT hash FROM pronostico WHERE pronostico_id < %s ORDER BY pronostico_id DESC LIMIT 1",
            (desde_id,),
        ).fetchone()
        if ant:
            previo = ant[0]

    for reg in registros:
        pid = reg["pronostico_id"]
        # 1. Validar enlace de hash_previo
        if reg["hash_previo"] != previo:
            raise CadenaRotaError(
                f"Ruptura de cadena en pronostico_id {pid}: hash_previo esperado {previo}, "
                f"encontrado {reg['hash_previo']}"
            )

        # 2. Recalcular hash independiente
        hash_calc = calcular_hash_sello(
            partido_id=reg["partido_id"],
            version_modelo=reg["version_modelo"],
            version_datos=reg["version_datos"],
            corte=reg["corte"],
            sellado_en=reg["sellado_en"],
            entradas=reg["entradas"],
            distribucion=reg["distribucion"],
            referencia=reg["referencia_mercado"],
            hash_previo=reg["hash_previo"],
        )
        if hash_calc != reg["hash"]:
            raise CadenaRotaError(
                f"Huella corrupta en pronostico_id {pid}: calculado {hash_calc}, almacenado {reg['hash']}"
            )

        # 3. Validar contrato Pydantic si es una distribución completa
        if "mejor_de" in reg["distribucion"]:
            try:
                DistribucionPartido.model_validate(reg["distribucion"])
            except Exception as e:
                raise ContratoInvalidoError(
                    f"Contrato corrupto en pronostico_id {pid}: {e}"
                ) from e

        previo = reg["hash"]

    return {
        "integra": True,
        "total_sellos": len(registros),
        "ultimo_hash": registros[-1]["hash"] if registros else None,
    }


def cargar_pronostico_sellado(
    db: Any, partido_id: int, version_modelo: str | None = None
) -> PronosticoSellado:
    """Recupera un pronóstico sellado y valida el contrato `PronosticoSellado` antes de servir.

    Si el contrato está roto, lanza `ContratoInvalidoError` (mapeado a 502 por la API).
    """
    consulta = (
        "SELECT pronostico_id, partido_id, version_modelo, corte, sellado_en, "
        "distribucion, hash_previo, hash "
        "FROM pronostico WHERE partido_id = %s "
    )
    params = [partido_id]
    if version_modelo:
        consulta += "AND version_modelo = %s "
        params.append(version_modelo)
    consulta += "ORDER BY pronostico_id DESC LIMIT 1"

    row = db.execute(consulta, params).fetchone()
    if not row:
        raise LookupError(f"No existe pronóstico sellado para el partido {partido_id}")

    pronostico_id, p_id, v_mod, corte, sellado_en, dist, h_previo, h = row

    posicion = pronostico_id  # índice secuencial en la base
    hash_prev = None if h_previo == GENESIS else h_previo

    try:
        return PronosticoSellado.model_validate(
            {
                "partido_id": p_id,
                "version_modelo": v_mod,
                "posicion": posicion,
                "corte": corte,
                "sellado_en": sellado_en,
                "hash_previo": hash_prev,
                "hash": h,
                "distribucion": dist,
            }
        )
    except Exception as e:
        raise ContratoInvalidoError(
            f"PronosticoSellado inválido en partido {partido_id}: {e}"
        ) from e
