"""Una fila de TML → registro analizado (puro, sin base). Orientación y ids de la base los pone el escritor.

Todo lo que no se puede cargar devuelve `motivo` (rechazo de la fila). Los avisos son datos cargados sin algún
campo (duración fuera de rango, entrada no listada, nivel sin verificar...): se cuentan, no rechazan.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

from . import tml_campos as campos
from .tml_reglas import categoria, dias_de_edicion, lunes_de, por_equipos
from .tml_score import Marcador, parsear_marcador

RONDA = re.compile(r"^[A-Z]{1,2}[0-9]*$")
CLAVE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SUPERFICIES = {"hard": "hard", "clay": "clay", "grass": "grass", "carpet": "carpet"}


@dataclass
class Analisis:
    fichero: str
    motivo: str | None = None
    doble: bool = False
    avisos: list = field(default_factory=list)
    circuito: str = ""
    anio: int = 0
    clave: str = ""
    nombre: str = ""
    nivel: str = ""
    categoria: str | None = None
    por_equipos: bool = False
    dias: int = 7
    inicio: object = None          # date de tourney_date
    superficie: str | None = None
    indoor: bool | None = None
    ids: tuple = ("", "")          # (ganador, perdedor) según TML
    nombres: tuple = ("", "")
    manos: tuple = (None, None)
    alturas: tuple = (None, None)
    paises: tuple = (None, None)
    entradas: tuple = (None, None)
    ronda: str = ""
    mejor_de: int = 0
    marcador: Marcador | None = None
    duracion: int | None = None
    stats: tuple | None = None     # (dict_ganador, dict_perdedor) de TML
    stat_motivo: str | None = None
    ranking: list = field(default_factory=list)   # [(id_tml, posicion, puntos)]
    lunes: object = None           # lunes de tourney_date (ranking)


def _rechazar(a: Analisis, motivo: str) -> Analisis:
    a.motivo = motivo
    return a


def _torneo(a: Analisis, tourney_id: str) -> None:
    m = re.search(r"(\d{4})", tourney_id)
    a.anio = int(m.group(1)) if m else 0
    resto = tourney_id[5:] if re.match(r"^\d{4}-", tourney_id) else tourney_id
    a.clave = resto.lower()


def _mano_altura_pais(a: Analisis, fila: dict) -> None:
    a.manos = (campos.mano(fila["winner_hand"]), campos.mano(fila["loser_hand"]))
    a.alturas = (campos.altura(fila["winner_ht"]), campos.altura(fila["loser_ht"]))
    a.paises = (campos.pais(fila["winner_ioc"]), campos.pais(fila["loser_ioc"]))
    if fila["winner_hand"].strip() == "A" or fila["loser_hand"].strip() == "A":
        a.avisos.append("mano_ambidiestro_no_escrita")


def _duracion(a: Analisis, minutos: str) -> None:
    v = (minutos or "").strip()
    if v == "":
        a.avisos.append("duracion_ausente")
    elif campos.entero(v) is None:
        a.avisos.append("duracion_no_numerica")
    elif 1 <= int(v) <= 600:
        a.duracion = int(v)
    else:
        a.avisos.append("duracion_fuera_de_rango")


def _estadisticas(a: Analisis, fila: dict) -> None:
    if a.marcador.estado not in ("completado", "retirada"):
        return
    w, l = campos.estadisticas(fila, "w"), campos.estadisticas(fila, "l")
    if a.marcador.estado == "completado":
        # Un lado con 0 puntos de saque en un partido TERMINADO es imposible: TML codifica así el faltante (medido el
        # 5-nov: 65 partidos, p. ej. un 6-2 6-2 con todo el saque del perdedor a 0). Faltante ≠ 0: ese lado queda sin
        # estadística (NULL, no se escribe fila) y se avisa. En retiradas muy tempranas (1-0 RET) el 0 sí es posible.
        vacio = {k: None for k in w}
        if w["puntos_saque"] == 0:
            w = dict(vacio)
            a.avisos.append("estadistica_cero_imposible")
        if l["puntos_saque"] == 0:
            l = dict(vacio)
            a.avisos.append("estadistica_cero_imposible")
    if campos.sin_datos(w) and campos.sin_datos(l):
        a.avisos.append("estadistica_sin_datos")
        return
    a.stat_motivo = campos.violacion_estadistica(w) or campos.violacion_estadistica(l)
    if a.stat_motivo is None:
        a.stats = (w, l)


def _ranking(a: Analisis, fila: dict) -> None:
    for id_, col_r, col_p in ((a.ids[0], "winner_rank", "winner_rank_points"),
                              (a.ids[1], "loser_rank", "loser_rank_points")):
        pos = campos.entero(fila.get(col_r, ""))
        if pos is not None and pos >= 1:
            a.ranking.append((id_, pos, campos.entero(fila.get(col_p, ""))))


def analizar_fila(fila: dict, fichero: str) -> Analisis:
    a = Analisis(fichero=fichero, circuito="wta" if "_wta" in fichero else "atp")
    a.nombres = (fila["winner_name"].strip(), fila["loser_name"].strip())
    if "/" in a.nombres[0] or "/" in a.nombres[1]:
        a.doble = True
        return a
    a.ids = (fila["winner_id"].strip(), fila["loser_id"].strip())
    if "" in a.ids:
        return _rechazar(a, "id_jugador_vacio")
    if a.ids[0] == a.ids[1]:
        return _rechazar(a, "mismo_jugador")
    _torneo(a, fila["tourney_id"].strip())
    if not CLAVE.match(a.clave):
        return _rechazar(a, "torneo_clave_no_valida")
    if not 1968 <= a.anio <= 2100:
        return _rechazar(a, "temporada_anterior_al_esquema")
    try:
        a.inicio = datetime.strptime(fila["tourney_date"].strip(), "%Y%m%d").date()
    except ValueError:
        return _rechazar(a, "fecha_no_valida")
    a.ronda = fila["round"].strip()
    if not RONDA.match(a.ronda):
        return _rechazar(a, "ronda_no_valida")
    try:
        a.mejor_de = int(fila["best_of"].strip())
    except ValueError:
        a.mejor_de = 0
    if a.mejor_de not in (3, 5):
        return _rechazar(a, "formato_no_valido")
    a.marcador = parsear_marcador(fila["score"], a.mejor_de)
    if a.marcador.motivo:
        return _rechazar(a, a.marcador.motivo)
    if a.marcador.super_tiebreak:
        a.avisos.append("super_tiebreak_final")
    a.nivel = fila["tourney_level"].strip()
    a.nombre = fila["tourney_name"].strip()
    a.categoria, aviso = categoria(a.circuito, a.nivel, a.nombre)
    if aviso:
        a.avisos.append(aviso)
    a.por_equipos, a.dias = por_equipos(a.nivel, a.nombre), dias_de_edicion(a.nivel)
    sup = fila["surface"].strip().lower()
    a.superficie = SUPERFICIES.get(sup)
    a.indoor = {"I": True, "O": False}.get(fila.get("indoor", "").strip())
    _mano_altura_pais(a, fila)
    a.entradas = (campos.entrada(fila["winner_entry"]), campos.entrada(fila["loser_entry"]))
    if any(e.strip() and campos.entrada(e) is None for e in (fila["winner_entry"], fila["loser_entry"])):
        a.avisos.append("entrada_no_mapeada")
    _duracion(a, fila["minutes"])
    _estadisticas(a, fila)
    _ranking(a, fila)
    a.lunes = lunes_de(a.inicio)
    return a
