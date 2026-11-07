"""Propuestas de equivalencias entre ids de TML (ids alternos de una misma persona). Puro: no escribe en la base.

Evidencia fuerte, toda a la vez: mismo nombre normalizado y mismo país en el mismo circuito; al menos una fila con
edad válida en cada id y al menos MIN_FILAS_EDAD entre los dos; fecha de nacimiento estimada (fecha del torneo − edad) con
diferencia ≤ 0,2 años entre los dos ids; el principal aparece en un fichero ANTERIOR al alias (el cargador exige que
el principal ya exista). Cualquier otra cosa queda en «dudosas» con su motivo; diferencia > 1 año = «distintos».

Principal: el id que aparece primero en la carga (el cargador exige que el principal exista antes que el alias), luego
el de más filas con edad válida, luego el de más filas; después, el que no tiene forma de alias WTA (3xxxxx).
"""
import csv
import re
from collections import defaultdict
from statistics import median

from .normalizar import nombre_clave

MIN_FILAS_EDAD = 2
TOLERANCIA_ANIOS = 0.2
CONTRADICCION_ANIOS = 1.0
_ALIAS_WTA = re.compile(r"3\d{5}")


def _es_alias_wta(circuito: str, id_: str) -> bool:
    return circuito == "wta" and _ALIAS_WTA.fullmatch(id_) is not None


def proponer(filas, orden) -> dict:
    """filas: dicts de `enlazar.filas_tml`. orden(fichero) -> clave de orden de carga (menor = antes).

    Devuelve {"propuestas": [...], "dudosas": [(circ, nombre, pais, id, motivo)], "distintos": [...]}.
    """
    grupos = defaultdict(dict)                      # (circ, nombre_clave, pais) -> id -> estadística
    ids_por_circuito = defaultdict(set)
    for f in filas:
        if not f["pais"]:
            continue
        ids_por_circuito[f["circ"]].add(f["id"])
        st = grupos[(f["circ"], nombre_clave(f["nombre"]), f["pais"])].setdefault(
            f["id"], {"n": 0, "nv": 0, "nac": [], "orden": None, "nombre": f["nombre"]})
        st["n"] += 1
        o = orden(f["fichero"])
        st["orden"] = o if st["orden"] is None or o < st["orden"] else st["orden"]
        if f["edad"] is not None and 14 <= f["edad"] <= 50:
            st["nv"] += 1
            st["nac"].append(f["fecha"].toordinal() - f["edad"] * 365.25)
    propuestas, dudosas, distintos = [], [], []
    for (circ, nk, pais), ids in grupos.items():
        if len(ids) < 2:
            continue
        principal = min(ids, key=lambda i: (ids[i]["orden"], -ids[i]["nv"], -ids[i]["n"], _es_alias_wta(circ, i), i))
        sp = ids[principal]
        for alias, sa in sorted(ids.items()):
            if alias == principal:
                continue
            ref = (circ, sa["nombre"], pais, alias)
            if sa["nv"] < 1 or sp["nv"] < 1 or sa["nv"] + sp["nv"] < MIN_FILAS_EDAD:
                dudosas.append((*ref, f"sin_edad_suficiente({sa['nv']}/{sp['nv']})"))
                continue
            dif = abs(median(sa["nac"]) - median(sp["nac"])) / 365.25
            if dif > CONTRADICCION_ANIOS:
                distintos.append({"circ": circ, "nombre": sa["nombre"], "pais": pais, "id": alias,
                                  "principal": principal, "dif_anios": round(dif, 2)})
                continue
            if dif > TOLERANCIA_ANIOS:
                dudosas.append((*ref, f"diferencia_{dif:.2f}_anios"))
                continue
            if sp["orden"] >= sa["orden"]:
                dudosas.append((*ref, "principal_no_carga_antes"))
                continue
            if any(alias in s for c, s in ids_por_circuito.items() if c != circ):
                dudosas.append((*ref, "id_tambien_en_otro_circuito"))
                continue
            propuestas.append({
                "fuente": "tml", "id_alias": alias, "id_principal": principal, "circ": circ, "nombre": sa["nombre"],
                "pais": pais, "n_alias": sa["n"], "nv_alias": sa["nv"], "n_principal": sp["n"],
                "nv_principal": sp["nv"], "dif_anios": round(dif, 3),
                "evidencia": (f"mismo nombre normalizado y país ({pais}), circuito {circ}; edad TML compatible: "
                              f"diferencia {dif:.2f} años con {sa['nv']} y {sp['nv']} filas con edad válida; "
                              f"principal {principal} carga antes.")})
    principales_alias = {p["id_principal"] for p in propuestas} & {p["id_alias"] for p in propuestas}
    if principales_alias:
        cadena = [p for p in propuestas if p["id_principal"] in principales_alias]
        propuestas = [p for p in propuestas if p["id_principal"] not in principales_alias]
        dudosas += [(p["circ"], p["nombre"], p["pais"], p["id_alias"], "cadena_de_equivalencias") for p in cadena]
    return {"propuestas": sorted(propuestas, key=lambda p: (p["circ"], p["id_alias"])), "dudosas": dudosas,
            "distintos": distintos}


def escribir_csv(propuestas: list[dict], ruta) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fuente", "id_alias", "id_principal", "evidencia"])
        for p in propuestas:
            w.writerow([p["fuente"], p["id_alias"], p["id_principal"], p["evidencia"]])
