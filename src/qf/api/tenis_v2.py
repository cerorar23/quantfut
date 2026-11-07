"""API pública v2 de tenis (plan §H.3, Sprint 6).

Rutas:
- GET /tenis/v2/cartelera?fecha=AAAA-MM-DD
- GET /tenis/v2/partido/{id}
- GET /tenis/v2/metodologia

Reglas:
- Solo códigos de error limpios (la capa cliente traduce a 6 idiomas).
- 404 si el partido no existe; 400 si la fecha o parámetros son inválidos.
- 502 si el contrato `PronosticoSellado` está roto o corrupto (falla de integridad).
- Sin Kelly, stakes ni ROI: brecha frente al mercado siempre declarada y honesta.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from tenis.sellado import ContratoInvalidoError, cargar_pronostico_sellado
from ..db import query, query_one

router = APIRouter(prefix="/tenis/v2", tags=["tenis_v2"])
UTC = timezone.utc


def _resolver_conexion(db_conn: Any = None):
    """Permite inyectar una conexión para pruebas unitarias sin tocar el pool."""
    return db_conn


@router.get("/cartelera")
def cartelera(fecha: str | None = Query(None, description="Fecha de los partidos (AAAA-MM-DD)")):
    """Lista de partidos programados y pronósticos sellados para una fecha en UTC."""
    if fecha is None:
        fecha = datetime.now(UTC).strftime("%Y-%m-%d")

    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_invalida")

    # Partidos de la fecha en UTC según programa
    sql = """
    SELECT p.partido_id, t.circuito, t.nombre AS torneo_nombre, t.categoria,
           e.superficie, e.temporada, p.ronda, p.mejor_de,
           pr.inicio_programado_utc, pr.tipo_hora, pr.pista, pr.estado AS estado_programa,
           p.jugador_1 AS j1_id, p.jugador_2 AS j2_id,
           pro.pronostico_id, pro.version_modelo, pro.corte, pro.sellado_en,
           pro.hash, pro.distribucion, pro.referencia_mercado
    FROM tenis.partido p
    JOIN tenis.edicion e ON p.edicion_id = e.edicion_id
    JOIN tenis.torneo t ON e.torneo_id = t.torneo_id
    JOIN tenis.programa pr ON p.partido_id = pr.partido_id
    LEFT JOIN LATERAL (
        SELECT pronostico_id, version_modelo, corte, sellado_en, hash, distribucion, referencia_mercado
        FROM tenis.pronostico
        WHERE partido_id = p.partido_id
        ORDER BY pronostico_id DESC LIMIT 1
    ) pro ON true
    WHERE (pr.inicio_programado_utc AT TIME ZONE 'UTC')::date = %s::date
    ORDER BY pr.inicio_programado_utc ASC, p.partido_id ASC
    """
    try:
        filas = query(sql, (fecha,))
    except Exception as e:
        # Fallback para esquemas de prueba o sin prefijo tenis
        sql_alt = sql.replace("tenis.", "")
        filas = query(sql_alt, (fecha,))

    # Recolectar nombres de jugadores
    j_ids = set()
    for f in filas:
        j_ids.add(f["j1_id"])
        j_ids.add(f["j2_id"])

    nombres = {}
    if j_ids:
        try:
            sql_j = """
            SELECT DISTINCT ON (jugador_id) jugador_id, valor AS nombre
            FROM tenis.jugador_asercion
            WHERE campo = 'nombre' AND jugador_id = ANY(%s)
            ORDER BY jugador_id, recibido_en DESC
            """
            rows_j = query(sql_j, (list(j_ids),))
        except Exception:
            sql_j_alt = """
            SELECT DISTINCT ON (jugador_id) jugador_id, valor AS nombre
            FROM jugador_asercion
            WHERE campo = 'nombre' AND jugador_id = ANY(%s)
            ORDER BY jugador_id, recibido_en DESC
            """
            rows_j = query(sql_j_alt, (list(j_ids),))

        for rj in rows_j:
            nombres[rj["jugador_id"]] = rj["nombre"]

    partidos = []
    for f in filas:
        p_id = f["partido_id"]
        inicio_utc = f["inicio_programado_utc"]
        if inicio_utc and hasattr(inicio_utc, "isoformat"):
            inicio_iso = inicio_utc.isoformat()
        else:
            inicio_iso = str(inicio_utc) if inicio_utc else None

        sellado = f["pronostico_id"] is not None
        sello_data = None
        if sellado:
            dist = f["distribucion"]
            if isinstance(dist, str):
                dist = json.loads(dist)
            ref = f["referencia_mercado"]
            if isinstance(ref, str):
                ref = json.loads(ref)

            sello_data = {
                "hash": f["hash"],
                "version_modelo": f["version_modelo"],
                "corte": f["corte"].isoformat() if hasattr(f["corte"], "isoformat") else str(f["corte"]),
                "sellado_en": f["sellado_en"].isoformat() if hasattr(f["sellado_en"], "isoformat") else str(f["sellado_en"]),
                "mercados": dist.get("mercados", {}) if isinstance(dist, dict) else {},
                "referencia_mercado": ref if isinstance(ref, dict) else {},
            }

        partidos.append({
            "partido_id": p_id,
            "circuito": f["circuito"].upper(),
            "torneo": f["torneo_nombre"],
            "categoria": f["categoria"],
            "superficie": f["superficie"],
            "ronda": f["ronda"],
            "mejor_de": f["mejor_de"],
            "inicio_programado_utc": inicio_iso,
            "pista": f["pista"],
            "jugador_1": {"id": f["j1_id"], "nombre": nombres.get(f["j1_id"], f"Jugador {f['j1_id']}")},
            "jugador_2": {"id": f["j2_id"], "nombre": nombres.get(f["j2_id"], f"Jugador {f['j2_id']}")},
            "sellado": sellado,
            "sello": sello_data,
        })

    return {
        "fecha": fecha,
        "total": len(partidos),
        "partidos": partidos,
    }


@router.get("/partido/{partido_id}")
def detalle_partido(partido_id: int):
    """Detalle de un partido, mercados completos y verificación criptográfica."""
    sql = """
    SELECT p.partido_id, t.circuito, t.nombre AS torneo_nombre, t.categoria,
           e.superficie, e.temporada, p.ronda, p.mejor_de,
           pr.inicio_programado_utc, pr.tipo_hora, pr.pista, pr.estado AS estado_programa,
           p.jugador_1 AS j1_id, p.jugador_2 AS j2_id
    FROM tenis.partido p
    JOIN tenis.edicion e ON p.edicion_id = e.edicion_id
    JOIN tenis.torneo t ON e.torneo_id = t.torneo_id
    LEFT JOIN tenis.programa pr ON p.partido_id = pr.partido_id
    WHERE p.partido_id = %s
    """
    try:
        f = query_one(sql, (partido_id,))
    except Exception:
        sql_alt = sql.replace("tenis.", "")
        f = query_one(sql_alt, (partido_id,))

    if not f:
        raise HTTPException(status_code=404, detail="partido_no_encontrado")

    # Obtener sello si existe
    sql_sello = """
    SELECT pronostico_id, partido_id, version_modelo, version_datos, corte, sellado_en,
           distribucion, referencia_mercado, hash_previo, hash
    FROM tenis.pronostico
    WHERE partido_id = %s
    ORDER BY pronostico_id DESC LIMIT 1
    """
    try:
        sello_row = query_one(sql_sello, (partido_id,))
    except Exception:
        sql_sello_alt = sql_sello.replace("tenis.", "")
        sello_row = query_one(sql_sello_alt, (partido_id,))

    sello_obj = None
    if sello_row:
        # Validar el contrato Pydantic PronosticoSellado antes de servir
        try:
            # Crear mock/adaptador si query_one devolvió dict
            from psycopg.types.json import Jsonb
            from tenis.contratos.salida import PronosticoSellado
            dist = sello_row["distribucion"]
            if isinstance(dist, str):
                dist = json.loads(dist)
            h_prev = None if sello_row["hash_previo"] == "0" * 64 else sello_row["hash_previo"]

            pron_valido = PronosticoSellado.model_validate({
                "partido_id": sello_row["partido_id"],
                "version_modelo": sello_row["version_modelo"],
                "posicion": sello_row["pronostico_id"],
                "corte": sello_row["corte"],
                "sellado_en": sello_row["sellado_en"],
                "hash_previo": h_prev,
                "hash": sello_row["hash"],
                "distribucion": dist,
            })
            sello_obj = {
                "hash": pron_valido.hash,
                "posicion": pron_valido.posicion,
                "version_modelo": pron_valido.version_modelo,
                "corte": pron_valido.corte.isoformat(),
                "sellado_en": pron_valido.sellado_en.isoformat(),
                "mercados": pron_valido.distribucion.mercados.model_dump(),
                "distribucion_resumen": {
                    "total_marcadores": len(pron_valido.distribucion.entradas),
                    "mejor_de": pron_valido.distribucion.mejor_de,
                    "regla_decisivo": pron_valido.distribucion.regla_decisivo,
                },
                "referencia_mercado": sello_row["referencia_mercado"],
            }
        except Exception as e:
            raise HTTPException(status_code=502, detail="contrato_roto") from e

    return {
        "partido_id": f["partido_id"],
        "circuito": f["circuito"].upper(),
        "torneo": f["torneo_nombre"],
        "superficie": f["superficie"],
        "ronda": f["ronda"],
        "mejor_de": f["mejor_de"],
        "inicio_programado_utc": f["inicio_programado_utc"].isoformat() if f["inicio_programado_utc"] else None,
        "jugadores": [f["j1_id"], f["j2_id"]],
        "sellado": sello_obj is not None,
        "pronostico": sello_obj,
    }


@router.get("/metodologia")
def metodologia():
    """Declaración metodológica transparente, compuertas de calidad y sesgos conocidos."""
    return {
        "sistema": "QuantFut Tenis v2 (Beta)",
        "version_modelo": "tenis-2.0+sprint6",
        "mision": "Modelado probabilístico honesto y sin fines de lucro para tenis profesional ATP y WTA.",
        "arquitectura": {
            "componente_R": "Rating dinámico bayesiano con efectos estructurales de superficie y fatiga.",
            "componente_P": "Probabilidades de servicio y resto con incertidumbre bivariada conjunta.",
            "componente_C": "Inversión matemática analítica de la probabilidad del partido para coherencia exacta entre mercados.",
            "calibracion": "Varianza predictiva inflada (c_inf) ajustada en periodos anteriores a 2019 para garantizar calibración fuera de muestra.",
        },
        "principios_inmutables": [
            "Sin apuestas, sin apuestas de valor simuladas, sin Kelly, stakes ni métricas de retorno financiero engañoso.",
            "El mercado NUNCA entra al modelo generativo (independencia estricta de predicción).",
            "Liquidación siempre con resultados propios verificados, jamás con calificaciones de terceros.",
            "Sellado criptográfico inmutable previo al inicio con corte fijo (T_ref - 60 min).",
        ],
        "compuertas_validadas": {
            "G-linea_base": "Supera ampliamente al Elo recalibrado en ATP y WTA (Delta log-loss combinado < 0, IC95 negativo).",
            "G-calibracion": "Pendiente de calibración con IC95 que incluye 1.0 tras corrección c_inf.",
            "G-coherencia": "0 violaciones matemáticas entre mercados derivados (todos provienen de la misma distribución conjunta).",
            "G-cierre": "Bate la brecha de Elo frente al mercado de cierre: Delta log-loss ATP +0.0237 [0.0209, 0.0266], WTA +0.0284 [0.0251, 0.0316].",
            "G-identidad": "Cobertura en cuadro principal ATP 90.0% y WTA 86.7% sin sesgo de selección.",
        },
        "sesgos_conocidos_declarados": {
            "totales_juegos_sesgo_iid": (
                "La distribución conjunta asume independencia condicional entre puntos del partido. "
                "Esto genera un sesgo empírico documentado de +0.736 juegos en ATP y +0.608 juegos en WTA "
                "respecto al promedio real, el cual se declara públicamente para conocimiento del usuario."
            ),
            "fatiga_intratorneo": (
                "La acumulación de minutos de juego en rondas recientes no mostró señal estadísticamente "
                "significativa en la muestra histórica (phi_1 aprox 0). Se mantiene en la formulación pero sin forzar un efecto espurio."
            ),
        },
    }
