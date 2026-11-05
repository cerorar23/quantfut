"""Primera pasada: valores por torneo y por edición (torneo × temporada), con sus conflictos. Puro.

Regla: fecha y superficie de la edición = la primera fila en orden de carga; cada valor distinto es un conflicto.
Categoría del torneo: única si todas las filas coinciden; si hay varias, queda vacía y se registra el conflicto.
"""
class Agregado:
    def __init__(self):
        self.torneos: dict = {}
        self.ediciones: dict = {}

    def sumar(self, a) -> None:
        t = self.torneos.setdefault((a.circuito, a.clave), {"cat": [], "nombre": ""})
        if a.categoria and a.categoria not in t["cat"]:
            t["cat"].append(a.categoria)
        t["nombre"] = t["nombre"] or a.nombre
        e = self.ediciones.setdefault((a.circuito, a.clave, a.anio), {
            "inicios": [], "sup": [], "indoor": [], "dias": 7, "equipos": False})
        for lista, valor in ((e["inicios"], a.inicio), (e["sup"], a.superficie), (e["indoor"], a.indoor)):
            if valor is not None and valor not in lista:
                lista.append(valor)
        e["dias"] = max(e["dias"], a.dias)
        e["equipos"] = e["equipos"] or a.por_equipos

    def finalizar(self) -> list[str]:
        """Congela los valores y devuelve la lista de conflictos (texto)."""
        conflictos = []
        for (circ, clave), t in self.torneos.items():
            if len(t["cat"]) > 1:
                conflictos.append(f"categoria_conflicto;{circ};{clave};{'|'.join(t['cat'])}")
            t["categoria"] = t["cat"][0] if len(t["cat"]) == 1 else None
        for (circ, clave, anio), e in self.ediciones.items():
            if not e["inicios"]:
                e["inicio"] = None
            else:
                e["inicio"] = min(e["inicios"])
                if len(e["inicios"]) > 1:
                    conflictos.append(f"fecha_distinta;{circ};{clave};{anio}")
            if len(e["sup"]) > 1:
                conflictos.append(f"superficie_distinta;{circ};{clave};{anio}")
            e["superficie"] = e["sup"][0] if e["sup"] else None
            e["indoor_v"] = e["indoor"][0] if e["indoor"] else None
        return conflictos
