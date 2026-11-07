"""ResolutorMultifuente: asigna cada id de una fuente a un jugador (plan técnico tenis, B.1).

Orden (de más a menos fiable; el primero que decide gana):
  1. alias vigente de (fuente, id_fuente);
  2. nombre (claves apellido/inicial) + circuito + PAÍS igual + edad compatible. Sin país o sin fecha de nacimiento no
     se une por nombre. La edad compara la fecha de nacimiento de la fuente con (a) las fechas de nacimiento ya
     asertadas de la persona y (b) la edad que TML declara en sus partidos (`edades`, ver enlazar.py);
  3. contexto del partido (rival ya resuelto, fecha ±3 días, torneo opcional) cuando (2) no decidió;
  4. equivalencias manuales (config/equivalencias.csv) cuando nada anterior decidió.
Si nada decide: jugador NUEVO y fila en `sin_resolver` con motivo.

Una unión escribe `jugador_alias` (con su método) y una aserción de fecha de nacimiento. Todo es idempotente: la clave
natural y `ON CONFLICT DO NOTHING` hacen que repetir la misma recepción no añada filas. Un alias erróneo se anula con
`anular()`, que añade una fila con `anula_a`; nunca se borra.

Requisitos de uso: un único escritor por proceso (el índice en memoria no se relee), y `search_path` fijado en la
conexión (como hace el cargador de TML). El llamador confirma la transacción.
"""
import csv
from collections import Counter
from datetime import date, timedelta

from . import cola
from .normalizar import claves_apellido, nombre_clave
from .paises import iso3

UMBRAL_OK_ANIOS = 0.2        # tolerancia de una comparación de edad
UMBRAL_CONTRADICCION = 1.0   # una sola comparación por encima de esto = personas distintas
VENTANA_DIAS = 3             # fecha del partido, para el contexto
CIRCUITOS = ("atp", "wta")
MANO = {"R": "D", "L": "Z", "D": "D", "Z": "Z", "U": "U"}
_PRIORIDAD_MOTIVO = ("confirmado_distinto", "edad_contradictoria", "ambiguo", "contexto_ambiguo", "edad_dudosa",
                     "sin_edad", "sin_pais", "sin_candidato")


def _fecha(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor))


def _anios(dias: float) -> float:
    return dias / 365.25


def _veredicto(diferencias: list[float]) -> str:
    """Compatibilidad de una persona candidata con la fecha de nacimiento que llega."""
    if not diferencias:
        return "sin_edad"
    if any(d > UMBRAL_CONTRADICCION for d in diferencias):
        return "contradictoria"
    dentro = sum(d <= UMBRAL_OK_ANIOS for d in diferencias)
    return "compatible" if 2 * dentro >= len(diferencias) else "dudosa"


def _motivo_final(*motivos):
    presentes = [m for m in motivos if m]
    if not presentes:
        return "sin_candidato"
    return min(presentes, key=lambda m: _PRIORIDAD_MOTIVO.index(m) if m in _PRIORIDAD_MOTIVO else 99)


def cargar_equivalencias(ruta) -> dict:
    """{(fuente, id_alias): (id_principal, evidencia)}. Rechaza alias circulares, cadenas y filas sin evidencia."""
    salida = {}
    with open(ruta, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fuente, alias = r["fuente"].strip(), r["id_alias"].strip()
            principal, evidencia = r["id_principal"].strip(), r["evidencia"].strip()
            if not (fuente and alias and principal):
                raise ValueError("equivalencia incompleta")
            if alias == principal:
                raise ValueError(f"alias circular: {fuente}:{alias} apunta a sí mismo")
            if not evidencia:
                raise ValueError(f"equivalencia {fuente}:{alias} sin evidencia")
            if (fuente, alias) in salida:
                raise ValueError(f"alias duplicado: {fuente}:{alias}")
            salida[(fuente, alias)] = (principal, evidencia)
    for (fuente, alias), (principal, _) in salida.items():
        if (fuente, principal) in salida:
            raise ValueError(f"cadena o circularidad: {fuente}:{alias} -> {principal} (el principal es alias)")
    return salida


class ResolutorMultifuente:
    def __init__(self, conn, *, equivalencias: dict | None = None, edades=None):
        self.cur = conn.cursor()
        self.equivalencias = equivalencias or {}
        self.edades = edades or (lambda jugador_id: ())   # jugador_id -> [(fecha, edad_en_anios)]
        self.ultimo = None                                  # (metodo, motivo) de la última llamada
        self.conteo = Counter()
        self._idx = None

    # ---- índice en memoria -------------------------------------------------------------------------------
    def _indice(self) -> dict:
        if self._idx is None:
            idx = {"circ": {}, "claves": {}, "exactos": {}, "paises": {}, "nacs": {}}
            self.cur.execute("SELECT jugador_id, circuito FROM jugador")
            idx["circ"] = dict(self.cur.fetchall())
            self._idx = idx
            self.cur.execute("SELECT jugador_id, valor FROM jugador_asercion WHERE campo = 'nombre'")
            for jid, nombre in self.cur.fetchall():
                self._indexar(jid, "nombre", nombre)
            self.cur.execute("SELECT jugador_id, campo, valor FROM jugador_asercion "
                             "WHERE campo IN ('pais', 'fecha_nacimiento')")
            for jid, campo, valor in self.cur.fetchall():
                self._indexar(jid, campo, valor)
        return self._idx

    def _indexar(self, jid: int, campo: str, valor: str) -> None:
        idx = self._idx
        if campo == "nombre":
            circ = idx["circ"][jid]
            for clave in claves_apellido(valor):
                idx["claves"].setdefault((circ, *clave), set()).add(jid)
            idx["exactos"].setdefault((circ, nombre_clave(valor)), set()).add(jid)
        elif campo == "pais":
            idx["paises"].setdefault(jid, set()).add(iso3(valor))   # TML trae códigos del COI, SofaScore ISO alpha-3
        elif campo == "fecha_nacimiento":
            idx["nacs"].setdefault(jid, set()).add(_fecha(valor))

    def _candidatos(self, circuito: str, nombre: str) -> set[int]:
        idx = self._indice()
        salida: set[int] = set(idx["exactos"].get((circuito, nombre_clave(nombre)), ()))
        for clave in claves_apellido(nombre):
            salida |= idx["claves"].get((circuito, *clave), set())
        return salida

    def _diferencias(self, jid: int, nac: date) -> list[float]:
        idx = self._indice()
        dif = [_anios(abs((n - nac).days)) for n in idx["nacs"].get(jid, ())]
        dif += [abs(edad - _anios((f - nac).days)) for f, edad in self.edades(jid)]
        return dif

    # ---- pasos -------------------------------------------------------------------------------------------
    def _alias_vigente(self, fuente: str, id_fuente: str):
        self.cur.execute(
            "SELECT a.alias_id, a.jugador_id FROM jugador_alias a WHERE a.fuente = %s AND a.id_fuente = %s "
            "AND NOT EXISTS (SELECT 1 FROM jugador_alias x WHERE x.anula_a = a.alias_id) "
            "ORDER BY a.recibido_en DESC, a.alias_id DESC LIMIT 1", (fuente, id_fuente))
        fila = self.cur.fetchone()
        return fila if fila else (None, None)

    def _por_nombre(self, circuito, nombre, pais, nac):
        if not pais:
            return None, None, "sin_pais"
        idx = self._indice()
        cands = self._candidatos(circuito, nombre)
        igual = [c for c in cands if pais in idx["paises"].get(c, ())]
        otro = [c for c in cands if idx["paises"].get(c) and pais not in idx["paises"][c]]
        if not igual:
            return None, None, ("confirmado_distinto" if otro else "sin_candidato")
        if nac is None:
            return None, None, "sin_edad"
        veredictos = {c: _veredicto(self._diferencias(c, nac)) for c in igual}
        compatibles = [c for c, v in veredictos.items() if v == "compatible"]
        if len(compatibles) == 1:
            return compatibles[0], "nombre_fecha_nac", None
        if len(compatibles) > 1:
            return None, None, "ambiguo"
        valores = set(veredictos.values())
        if "contradictoria" in valores:
            return None, None, "edad_contradictoria"
        if "dudosa" in valores:
            return None, None, "edad_dudosa"
        return None, None, "sin_edad"

    def _por_contexto(self, circuito, nombre, pais, contexto):
        rival, fecha, torneo = contexto.get("rival_jugador_id"), _fecha(contexto.get("fecha")), contexto.get("torneo")
        if rival is None or fecha is None:
            return None, None, None
        idx = self._indice()
        cands = [c for c in self._candidatos(circuito, nombre)
                 if not pais or not idx["paises"].get(c) or pais in idx["paises"][c]]
        if not cands:
            return None, None, "sin_candidato"
        ini, fin = fecha - timedelta(days=VENTANA_DIAS), fecha + timedelta(days=VENTANA_DIAS)
        cuenta = {}
        for c in cands:
            self.cur.execute(
                "SELECT count(*) FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id "
                "JOIN torneo t ON t.torneo_id = e.torneo_id "
                "WHERE ((p.jugador_1 = %s AND p.jugador_2 = %s) OR (p.jugador_1 = %s AND p.jugador_2 = %s)) "
                "AND COALESCE(e.fecha_fin, e.lunes_semana + 6) >= %s AND e.lunes_semana <= %s "
                "AND (%s::text IS NULL OR t.clave = %s)",
                (c, rival, rival, c, ini, fin, torneo, torneo))
            cuenta[c] = self.cur.fetchone()[0]
        con_partido = [c for c in cands if cuenta[c] > 0]
        if not con_partido:
            return None, None, "sin_candidato"
        if len(con_partido) == 1 and cuenta[con_partido[0]] == 1:
            return con_partido[0], "contexto_partido", None
        return None, None, "contexto_ambiguo"

    def _manual(self, fuente, id_fuente, circuito):
        eq = self.equivalencias.get((fuente, id_fuente))
        if eq is None:
            return None, None, None
        _, jid = self._alias_vigente(fuente, eq[0])
        if jid is None:
            return None, None, "manual_sin_principal"
        if self._indice()["circ"][jid] != circuito:
            raise ValueError(f"equivalencia {fuente}:{id_fuente} cruza circuitos")
        return jid, "manual", None

    # ---- escritura ---------------------------------------------------------------------------------------
    def _aserta(self, jid, campo, valor, fuente, recibo_id, recibido_en) -> None:
        self.cur.execute(
            "INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (jid, campo, valor, fuente, recibo_id, recibido_en))
        if self._idx is not None:
            self._indexar(jid, campo, valor)

    def _unir(self, fuente, id_fuente, jid, metodo, nac, recibo_id, recibido_en) -> None:
        self.cur.execute(
            "INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (fuente, id_fuente, jid, metodo, recibo_id, recibido_en))
        if nac is not None:
            self._aserta(jid, "fecha_nacimiento", nac.isoformat(), fuente, recibo_id, recibido_en)

    def _nuevo(self, fuente, id_fuente, circuito, nombre, nac, pais, mano, altura, recibo_id, recibido_en,
               motivo, contexto) -> int:
        self.cur.execute("INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) "
                         "RETURNING jugador_id", (circuito, recibo_id, recibido_en))
        jid = self.cur.fetchone()[0]
        self._indice()["circ"][jid] = circuito
        self._unir(fuente, id_fuente, jid, "id_exacto", None, recibo_id, recibido_en)
        for campo, valor in (("nombre", nombre), ("pais", pais), ("mano", MANO.get(mano or "")),
                             ("altura_cm", str(altura) if altura else None)):
            if valor:
                self._aserta(jid, campo, valor, fuente, recibo_id, recibido_en)
        if nac is not None:
            self._aserta(jid, "fecha_nacimiento", nac.isoformat(), fuente, recibo_id, recibido_en)
        cola.registrar(self.cur, fuente=fuente, id_fuente=id_fuente, nombre=nombre, motivo=motivo,
                       contexto=contexto, recibo_id=recibo_id, recibido_en=recibido_en)
        return jid

    def anular(self, *, fuente, id_fuente, jugador_id, recibo_id, recibido_en, metodo="manual") -> int:
        """Corrige un alias: una fila nueva que apunta a `jugador_id` y anula la vigente. Devuelve su alias_id."""
        alias_anterior, _ = self._alias_vigente(fuente, id_fuente)
        if alias_anterior is None:
            raise ValueError(f"no hay alias vigente que anular: {fuente}:{id_fuente}")
        self.cur.execute(
            "INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, anula_a, recibo_id, recibido_en) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING alias_id",
            (fuente, id_fuente, jugador_id, metodo, alias_anterior, recibo_id, recibido_en))
        return self.cur.fetchone()[0]

    def resolver(self, *, fuente, id_fuente, circuito, nombre, fecha_nacimiento, pais, mano, altura_cm,
                 recibo_id, recibido_en, contexto=None) -> int:
        """jugador_id de un registro de la fuente; crea el jugador si ninguna regla decide. Ver docstring del módulo."""
        self.cur.execute("SELECT 1 FROM fuente WHERE fuente = %s", (fuente,))
        if self.cur.fetchone() is None:
            raise ValueError(f"fuente desconocida: {fuente}")
        if circuito not in CIRCUITOS:
            raise ValueError(f"circuito desconocido: {circuito}")
        _, jid = self._alias_vigente(fuente, id_fuente)
        if jid is not None:
            self.ultimo = ("existente", None)
            self.conteo["existente"] += 1
            return jid
        nac = _fecha(fecha_nacimiento)
        pais = iso3(pais)
        contexto = contexto or {}
        jid, met, m2 = self._por_nombre(circuito, nombre, pais, nac)
        m3 = None
        if jid is None:
            jid, met, m3 = self._por_contexto(circuito, nombre, pais, contexto)
        m4 = None
        if jid is None:
            jid, met, m4 = self._manual(fuente, id_fuente, circuito)
        if jid is not None:
            self._unir(fuente, id_fuente, jid, met, nac, recibo_id, recibido_en)
            self.ultimo = (met, None)
            self.conteo[met] += 1
            return jid
        motivo = _motivo_final(m2, m3, m4)
        jid = self._nuevo(fuente, id_fuente, circuito, nombre, nac, pais, mano, altura_cm, recibo_id,
                          recibido_en, motivo, {"candidatos_nombre": len(self._candidatos(circuito, nombre))})
        self.ultimo = ("nuevo", motivo)
        self.conteo[f"nuevo:{motivo}"] += 1
        return jid
