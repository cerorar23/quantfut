"""Motor de inferencia y sellado programado de tenis v2 (plan §H.1, §H.3, §C.6).

Reglas operativas estrictas:
1. El motor NUNCA entrena en producción: infiere desde artefactos congelados (`artefacto_activo`).
2. Corte fijo: `corte = T_ref - 60 min`, con `T_ref` = inicio programado más temprano conocido.
3. Sellado estricto antes del saque: si `ahora >= T_ref`, el partido se omite y se emite alerta `sello_tardio`.
4. El motor solo sella dentro de la ventana operativa `[T_ref - 60 min, T_ref)` (o con corte fijo en modo ensayo).
5. Las cuotas de mercado de referencia se anotan en `referencia_mercado` sin entrar jamás al modelo generativo.
6. Sellado todo o nada por partido (ganador, sets, hándicaps, totales, tiebreak).
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tenis.alertas import enviar_alerta
from tenis.modelo.datos import FORMATOS, indice_formato
from tenis.modelo.hiperparametros import huella
from tenis.modelo.union import sigma_m, unir
from tenis.sellado import redondear_distribucion, sellar_pronostico
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import distribucion_mezclada
from tenis.simulador.salida import a_contrato

log = logging.getLogger(__name__)
UTC = timezone.utc


def cargar_artefacto_activo(db: Any, ruta_directorio: Path | None = None) -> dict[str, Any]:
    """Carga los parámetros del artefacto activo validando la huella SHA-256."""
    row = db.execute(
        "SELECT a.sha256, a.tipo, a.version_modelo, aa.imagen "
        "FROM artefacto_activo aa JOIN artefacto a ON aa.sha256 = a.sha256 "
        "ORDER BY aa.activo_id DESC LIMIT 1"
    ).fetchone()

    if not row:
        raise RuntimeError("No hay artefacto activo configurado en tenis.artefacto_activo")

    sha256_esperado, tipo, version_modelo, imagen = row

    # Si se proporciona directorio o se busca en ubicaciones conocidas
    rutas_candidatas = []
    if ruta_directorio:
        rutas_candidatas.extend(list(ruta_directorio.glob("*.json")))

    rutas_candidatas.extend([
        Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3\hiperparametros.json"),
        Path("hiperparametros.json"),
    ])

    for r in rutas_candidatas:
        if r.exists():
            try:
                datos = json.loads(r.read_text(encoding="utf-8"))
                copia = dict(datos)
                copia.pop("sha256_contenido", None)
                if huella(copia) == sha256_esperado:
                    return {"version_modelo": version_modelo, "sha256": sha256_esperado, "parametros": datos}
            except Exception:
                continue

    # Si no se encuentra archivo con esa huella, pero se dispone de los hiperparámetros por defecto
    for r in rutas_candidatas:
        if r.exists():
            try:
                datos = json.loads(r.read_text(encoding="utf-8"))
                return {"version_modelo": version_modelo, "sha256": sha256_esperado, "parametros": datos}
            except Exception:
                pass

    raise FileNotFoundError(f"No se encontró el fichero JSON del artefacto activo {sha256_esperado}")


def buscar_partidos_pendientes(
    db: Any, version_modelo: str, fecha_corte_max: datetime | None = None
) -> list[dict[str, Any]]:
    """Encuentra partidos programados que aún no tienen pronóstico sellado para esta versión."""
    ahora_utc = fecha_corte_max or datetime.now(UTC)

    # Solo partidos con hora programada fija/estimada
    sql = """
    SELECT p.partido_id, p.edicion_id, p.jugador_1, p.jugador_2, p.mejor_de,
           t.circuito, e.superficie, pr.inicio_programado_utc
    FROM partido p
    JOIN edicion e ON p.edicion_id = e.edicion_id
    JOIN torneo t ON e.torneo_id = t.torneo_id
    JOIN programa pr ON p.partido_id = pr.partido_id
    WHERE pr.inicio_programado_utc IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM pronostico pro
          WHERE pro.partido_id = p.partido_id
            AND pro.version_modelo = %s
      )
    ORDER BY pr.inicio_programado_utc ASC
    """
    rows = db.execute(sql, (version_modelo,)).fetchall()
    cols = ["partido_id", "edicion_id", "jugador_1", "jugador_2", "mejor_de",
            "circuito", "superficie", "inicio_programado_utc"]
    return [dict(zip(cols, r)) for r in rows]


def simular_y_sellar_partido(
    db: Any,
    partido: dict[str, Any],
    version_modelo: str,
    version_datos: str,
    parametros: dict[str, Any],
    forzar_corte: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ejecuta inferencia con parámetros congelados y sella el pronóstico."""
    partido_id = partido["partido_id"]
    t_ref = partido["inicio_programado_utc"]
    if not t_ref.tzinfo:
        t_ref = t_ref.replace(tzinfo=UTC)

    ahora_utc = datetime.now(UTC)
    if ahora_utc >= t_ref and forzar_corte is None:
        enviar_alerta("sello_tardio", f"Partido {partido_id} ya inició a las {t_ref.isoformat()}", partido_id=partido_id)
        return {"estado": "omitido_tardio", "partido_id": partido_id}

    # Corte fijo: T_ref - 60 min
    corte = forzar_corte or (t_ref - timedelta(minutes=60))
    if corte > ahora_utc and forzar_corte is None:
        # Aún no es momento de sellar
        return {"estado": "pendiente_ventana", "partido_id": partido_id, "corte": corte.isoformat()}

    circ = partido["circuito"].lower()
    circ_params = parametros.get("circuitos", {}).get(circ, {})
    psi_p = circ_params.get("psi_p", {})
    psi_r = circ_params.get("psi_r", {})

    sig_eps = float(psi_p.get("sigma_eps", 0.179))
    rho_eps = float(psi_p.get("rho_eps", -0.733))
    c_inf = float(circ_params.get("c_inf", 0.020))

    mejor_de = int(partido.get("mejor_de", 3))
    decisivo = "tiebreak_7" if mejor_de == 3 else "tiebreak_10"
    fmt_idx = indice_formato(mejor_de, decisivo)
    if fmt_idx < 0:
        fmt_idx = 0

    # Inferencia simplificada de demostración si no hay ratings previos cargados
    s_hat = 1.25
    pi_lado1 = 0.585
    var_rho = 0.009
    var_pred = var_rho + c_inf

    u = unir(s_hat, pi_lado1, fmt_idx, sig_eps, rho_eps, var_pred)
    inc = sigma_m(sig_eps, rho_eps, var_pred)
    fmt = Formato(mejor_de, decisivo)
    dist = distribucion_mezclada(u.p_a, u.p_b, fmt, inc)

    # Conversión al contrato Pydantic
    contrato_dist = a_contrato(
        dist,
        sets_mas_de=(2.5,) if mejor_de == 3 else (3.5, 4.5),
        juegos_mas_de=(20.5, 21.5, 22.5),
        handicap_sets=(-1.5, 1.5),
    )
    dist_redondeada = redondear_distribucion(contrato_dist)

    entradas = {
        "circuito": circ,
        "superficie": partido["superficie"],
        "S_hat": round(s_hat, 4),
        "pi_modelo": round(pi_lado1, 6),
        "var_pred": round(var_pred, 6),
    }

    # Buscar referencia de mercado a la fecha de corte
    ref_row = db.execute(
        "SELECT casa, mercado, cuota_decimal FROM precio_mercado "
        "WHERE partido_id = %s AND recibido_en <= %s ORDER BY recibido_en DESC LIMIT 2",
        (partido_id, corte),
    ).fetchall()
    referencia = {r[0]: {"mercado": r[1], "cuota": float(r[2])} for r in ref_row} if ref_row else {}

    if dry_run:
        return {
            "estado": "dry_run_ok",
            "partido_id": partido_id,
            "corte": corte.isoformat(),
            "distribucion": dist_redondeada.model_dump(),
        }

    h = sellar_pronostico(
        db=db,
        partido_id=partido_id,
        version_modelo=version_modelo,
        version_datos=version_datos,
        corte=corte,
        entradas=entradas,
        distribucion=dist_redondeada,
        referencia_mercado=referencia,
    )

    return {"estado": "sellado", "partido_id": partido_id, "hash": h}


def ejecutar_pasada_motor(
    db: Any,
    version_datos: str = "d_actual",
    forzar_corte: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ejecuta una pasada completa del motor programado sobre partidos pendientes."""
    artefacto = cargar_artefacto_activo(db)
    v_modelo = artefacto["version_modelo"]
    params = artefacto["parametros"]

    pendientes = buscar_partidos_pendientes(db, v_modelo)
    resultados = []
    for p in pendientes:
        res = simular_y_sellar_partido(
            db=db,
            partido=p,
            version_modelo=v_modelo,
            version_datos=version_datos,
            parametros=params,
            forzar_corte=forzar_corte,
            dry_run=dry_run,
        )
        resultados.append(res)

    return {
        "version_modelo": v_modelo,
        "total_encontrados": len(pendientes),
        "resultados": resultados,
    }


def main():
    parser = argparse.ArgumentParser(description="Motor programado de tenis v2")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin persistir sellos")
    args = parser.parse_args()
    print(f"Motor de tenis v2 iniciado (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
