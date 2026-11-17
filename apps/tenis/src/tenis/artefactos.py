"""Registro y activación de artefactos del motor (plan §H.1, §H.2, §H.4).

- `validar`: comprueba un artefacto de hiperparámetros ANTES de registrarlo (huella, estructura, compuertas del informe) y
  construye el plan de registro. No toca la base.
- `registrar`: inserta el artefacto y su activación en una sola transacción. Exige el texto del OK del titular en el chat
  (`aprobado_en_chat`) y una imagen `tenis-motor:<tag>`. Solo anexa filas (las tablas son inmutables).
- `reactivar`: vuelta atrás = OTRA fila de activación que apunta a un artefacto ya registrado (plan §H.4).
La base solo la escribe un rol administrador; el motor (`tenis_motor`) únicamente lee estas tablas.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tenis.modelo import hiperparametros as hp
from tenis.modelo.capa_edad import CapaEdad
from tenis.modelo.parametros import Psi
from tenis.modelo.puntos import PsiP

IMAGEN = re.compile(r"^tenis-motor:[A-Za-z0-9._-]+$")
TIPO = "modelo"


def version_modelo(sha256: str, menor: int) -> str:
    """Plan §H.2: `tenis-2.<menor>+<sha12>`."""
    return f"tenis-2.{int(menor)}+{sha256[:12]}"


def _base_sin_capa(contenido: dict) -> dict:
    """El mismo contenido sin la capa de edad: debe coincidir con el artefacto que se evaluó."""
    base = json.loads(json.dumps(contenido))
    base.pop("nota_capa_edad", None)
    for cfg in base["circuitos"].values():
        cfg.pop("capa_edad", None)
    return base


def validar(ruta_json: Path, ruta_informe: Path, menor: int = 1) -> dict[str, Any]:
    """Plan de registro de un artefacto. Lanza ValueError si algo impide registrarlo; las advertencias no bloquean."""
    contenido = hp.leer(Path(ruta_json))                         # falla si la huella declarada no coincide
    sha = hp.huella(contenido)
    advertencias: list[str] = []
    resumen: dict[str, Any] = {}
    for c, cfg in contenido["circuitos"].items():
        for clave in ("psi_r", "psi_p", "lbar"):
            if clave not in cfg:
                raise ValueError(f"{c}: falta {clave}")
        Psi.desde_dict(cfg["psi_r"])
        PsiP(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in cfg["psi_p"].items()})
        resumen[c] = {"capa_edad": CapaEdad.desde_dict(cfg["capa_edad"]).como_dict() if cfg.get("capa_edad") else None}

    informe = json.loads(Path(ruta_informe).read_text(encoding="utf-8"))
    if informe["sha256_hiperparametros"] != hp.huella(_base_sin_capa(contenido)):
        raise ValueError("el informe de compuertas no corresponde a los hiperparámetros base de este artefacto")
    compuertas: dict[str, Any] = {}
    for c, r in informe["circuitos"].items():
        g = r["compuertas"]
        if not g["G_linea_base"]["pasa"] or not g["G_cordura"]["pasa"]:
            raise ValueError(f"{c}: no pasa G_linea_base o G_cordura")
        if resumen.get(c, {}).get("capa_edad") and not g.get("G_capa_edad", {}).get("capa_activa"):
            raise ValueError(f"{c}: el artefacto trae capa de edad pero no pasa G_capa_edad")
        if not g["G_calibracion"]["pasa"]:
            advertencias.append(f"{c}: G_calibracion no pasa (pendiente {r['calibracion']['pi_lado1']['pendiente']:.3f} antes de la capa)")
        compuertas[c] = {k: v for k, v in g.items() if k != "G_recalibracion"} | {
            "n_evaluados": r["n_evaluados"], "no_fuga_violaciones": r["no_fuga"]["violaciones"]}
    informe_compuertas = {"sha256_hiperparametros_base": informe["sha256_hiperparametros"], "eval_rango": informe["eval_rango"],
                          "sha256_predicciones_base": informe["sha256_predicciones_total"], "circuitos": compuertas}
    return {"sha256": sha, "version_modelo": version_modelo(sha, menor), "tipo": TIPO, "informe_compuertas": informe_compuertas,
            "capa_edad": {c: v["capa_edad"] for c, v in resumen.items()}, "advertencias": advertencias}


def activo(db: Any) -> dict | None:
    fila = db.execute("SELECT a.sha256, a.version_modelo, aa.imagen, aa.activado_en FROM artefacto_activo aa "
                      "JOIN artefacto a ON a.sha256 = aa.sha256 ORDER BY aa.activo_id DESC LIMIT 1").fetchone()
    return None if not fila else {"sha256": fila[0], "version_modelo": fila[1], "imagen": fila[2], "activado_en": fila[3]}


def _exigir_aprobacion(aprobado_en_chat: str, imagen: str) -> None:
    if not aprobado_en_chat or not aprobado_en_chat.strip():
        raise ValueError("falta el OK del titular en el chat (aprobado_en_chat)")
    if not IMAGEN.match(imagen or ""):
        raise ValueError("imagen debe ser el nombre completo tenis-motor:<tag>")


def registrar(db: Any, plan: dict, imagen: str, aprobado_en_chat: str) -> dict:
    """Inserta el artefacto (si no existe) y su activación, en una transacción. Devuelve el artefacto activo resultante."""
    _exigir_aprobacion(aprobado_en_chat, imagen)
    previo = activo(db)
    if previo and previo["sha256"] == plan["sha256"] and previo["imagen"] == imagen:
        raise ValueError("ese artefacto ya está activo con esa imagen")
    with db.transaction():
        db.execute("INSERT INTO artefacto (sha256, tipo, version_modelo, informe_compuertas) VALUES (%s, %s, %s, %s::jsonb) "
                   "ON CONFLICT (sha256) DO NOTHING",
                   (plan["sha256"], plan["tipo"], plan["version_modelo"], json.dumps(plan["informe_compuertas"])))
        db.execute("INSERT INTO artefacto_activo (sha256, aprobado_en_chat, imagen) VALUES (%s, %s, %s)",
                   (plan["sha256"], aprobado_en_chat.strip(), imagen))
    ahora = activo(db)
    if not ahora or ahora["sha256"] != plan["sha256"]:
        raise RuntimeError("la activación no quedó registrada")
    return ahora | {"anterior": previo}


def reactivar(db: Any, sha256: str, imagen: str, aprobado_en_chat: str) -> dict:
    """Vuelta atrás: activa de nuevo un artefacto YA registrado (otra fila, nunca un UPDATE)."""
    _exigir_aprobacion(aprobado_en_chat, imagen)
    if not db.execute("SELECT 1 FROM artefacto WHERE sha256 = %s", (sha256,)).fetchone():
        raise ValueError("ese artefacto no está registrado")
    previo = activo(db)
    db.execute("INSERT INTO artefacto_activo (sha256, aprobado_en_chat, imagen) VALUES (%s, %s, %s)",
               (sha256, aprobado_en_chat.strip(), imagen))
    return activo(db) | {"anterior": previo}
