"""Respaldo de resultados de tenis con SportsAPIPro (`/v2/tennis/schedule/{fecha}`).

Solo hace peticiones bajo demanda cuando PropLine aún no calificó un partido de tenis y ya pasaron al menos
``MIN_EDAD`` horas desde su inicio programado. Primero consulta lo ya archivado en
``artifact_dir/sportsapipro_tenis_resultados`` (y opcionalmente ``TENIS_EQUIVALENCIAS_DIR`` en solo lectura); sin
patas pendientes ni partidos vencidos no consume cuota.

Reglas de liquidación conservadoras:
  * ``Ended``: ``h2h`` por ``winnerCode``; ``total_games``/``totals`` y ``handicap_games``/``spreads`` sumando los
    juegos de ``period1..period5`` cuando todos los sets jugados están completos y en rango normal (0..7).
  * ``Canceled`` o ``Walkover``: ``void``.
  * ``Retired`` y estados no definitivos (``inprogress``, ``postponed``, ``notstarted``): ``None`` para esperar la
    calificación por casa de PropLine o revisión manual, pues cada casa aplica distinta regla de retirada.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import sqlite3
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..config import settings
from . import cuotas_sportsapipro as cs

log = logging.getLogger(__name__)

API = "https://api.sportsapipro.com/v2/tennis/schedule/%s"
UTC = timezone.utc
DIARIO = 15                                 # peticiones propias/día (del plan gratuito compartido de 100/día)
MIN_EDAD = timedelta(hours=2, minutes=30)   # antes de esto un partido suele seguir en juego o esperando a PropLine
COOLDOWN_FECHA = timedelta(minutes=45)      # evita repetir la misma fecha en crons seguidos (:05/:20)
VENTANA = timedelta(hours=36)               # tolera aplazamientos/lluvia frecuentes en torneos ITF/Challenger
MERCADOS_SOPORTADOS = ("h2h", "totals", "total_games", "spreads", "handicap_games")


def _sp():
    """Import perezoso para no arrastrar dependencias pesadas o de BD al importar este módulo."""
    from . import sportsapipro_alineaciones as sp
    return sp


def carpeta() -> Path:
    return Path(settings.artifact_dir) / "sportsapipro_tenis_resultados"


def dir_equivalencias() -> Path | None:
    ruta = os.getenv("TENIS_EQUIVALENCIAS_DIR") or os.getenv("SPORTSAPIPRO_TENIS_DIR") or ""
    return Path(ruta) if ruta else None


def _es_dobles(e: dict) -> bool:
    h = (e.get("homeTeam") or {}).get("name") or ""
    a = (e.get("awayTeam") or {}).get("name") or ""
    tour = (e.get("tournament") or {}).get("name") or ""
    return "/" in h or "/" in a or "doubles" in cs.norm(tour).split()


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _conectar_rw(raiz: Path) -> sqlite3.Connection | None:
    try:
        db = _sp().abrir(raiz)
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS alertas (ref TEXT PRIMARY KEY, ultimo TEXT NOT NULL)")
        return db
    except (OSError, sqlite3.Error):
        return None


def _conectar_ro(raiz: Path) -> sqlite3.Connection | None:
    idx = raiz / "index.sqlite"
    if not idx.is_file():
        return None
    try:
        db = sqlite3.connect(f"file:{idx.resolve().as_posix()}?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    except sqlite3.Error:
        return None


def _filas_calendario(db: sqlite3.Connection, desde: datetime) -> list[sqlite3.Row]:
    cols = {r[1] for r in db.execute("PRAGMA table_info(receipts)")}
    corte = (desde - timedelta(days=2)).isoformat()
    if "fecha" in cols:
        return db.execute(
            "SELECT id, received_at, fecha, status, body_path FROM receipts "
            "WHERE received_at >= ? ORDER BY received_at ASC, id ASC",
            (corte,),
        ).fetchall()
    return db.execute(
        "SELECT id, received_at, ref AS fecha, status, body_path FROM receipts "
        "WHERE kind = 'calendario' AND received_at >= ? ORDER BY received_at ASC, id ASC",
        (corte,),
    ).fetchall()


def _leer_eventos_body(body: bytes) -> list[dict]:
    try:
        doc = json.loads(body)
    except ValueError:
        return []
    return [e for e in cs._eventos_de(doc) if not _es_dobles(e) and e.get("id") is not None]


def _juegos(e: dict) -> tuple[int, int] | None:
    """Suma de juegos (home_ss, away_ss) cuando todos los sets están completos y sin supertiebreak ambiguo."""
    hs = e.get("homeScore") or {}
    as_ = e.get("awayScore") or {}
    gh = ga = n_sets = 0
    for i in range(1, 6):
        sh, sa = hs.get(f"period{i}"), as_.get(f"period{i}")
        if sh is None and sa is None:
            continue
        if sh is None or sa is None:
            return None
        try:
            ih, ia = int(sh), int(sa)
        except (TypeError, ValueError):
            return None
        # Juegos mayores a 7 suelen corresponder a supertiebreaks a 10 puntos (regla variable según casa).
        if ih < 0 or ia < 0 or ih > 7 or ia > 7:
            return None
        gh += ih
        ga += ia
        n_sets += 1
    if n_sets == 0:
        return None
    cur_h, cur_a = hs.get("current"), as_.get("current")
    if cur_h is not None and cur_a is not None:
        try:
            if int(cur_h) + int(cur_a) != n_sets:
                return None
        except (TypeError, ValueError):
            return None
    return gh, ga


def buscar_evento(eventos: dict[int, tuple[datetime, str, dict]], local: str, visitante: str,
                  inicio_utc: datetime) -> tuple[dict, bool, str] | None:
    """Único partido individual que coincide en rivales (en cualquier orden) y ventana de ±36 h."""
    inicio = _utc(inicio_utc)
    buenos = []
    for _rec_at, fecha_vista, e in eventos.values():
        if _es_dobles(e):
            continue
        try:
            h = e["homeTeam"]["name"]
            a = e["awayTeam"]["name"]
            ts = datetime.fromtimestamp(int(e["startTimestamp"]), UTC)
        except (KeyError, TypeError, ValueError):
            continue
        if abs(ts - inicio) > VENTANA:
            continue
        directo = cs.mismo_jugador(h, local) and cs.mismo_jugador(a, visitante)
        inverso = cs.mismo_jugador(h, visitante) and cs.mismo_jugador(a, local)
        if directo and inverso:
            continue  # homónimos simétricos ambiguos: nunca adivinar
        if directo or inverso:
            buenos.append((e, inverso, fecha_vista))
    return buenos[0] if len(buenos) == 1 else None


def calificar_evento(e: dict, invertido: bool, mercado: str, seleccion: str, linea=None) -> str | None:
    """Traduce un evento de SportsAPIPro a ``win`` / ``loss`` / ``push`` / ``void``, o ``None``."""
    if mercado not in MERCADOS_SOPORTADOS:
        return None
    st = e.get("status") or {}
    tipo = str(st.get("type") or "").lower()
    desc = str(st.get("description") or "").lower()
    if tipo in ("canceled", "cancelled"):
        return "void"
    if tipo == "finished" and "walk" in desc:
        return "void"
    if tipo != "finished" or "ended" not in desc:
        return None
    winner = e.get("winnerCode")
    if winner not in (1, 2):
        return None
    if mercado == "h2h":
        if seleccion not in ("home", "away"):
            return None
        ganador = ("away" if invertido else "home") if winner == 1 else ("home" if invertido else "away")
        return "win" if seleccion == ganador else "loss"
    if linea is None:
        return None
    try:
        punto = float(linea)
    except (TypeError, ValueError):
        return None
    marcas = _juegos(e)
    if marcas is None:
        return None
    g_local, g_visit = (marcas[1], marcas[0]) if invertido else marcas
    if mercado in ("totals", "total_games"):
        if seleccion not in ("over", "under"):
            return None
        diff = (g_local + g_visit) - punto
        if abs(diff) < 1e-9:
            return "push"
        return ("win" if diff > 0 else "loss") if seleccion == "over" else ("win" if diff < 0 else "loss")
    if seleccion not in ("home", "away"):
        return None
    g_sel, g_opp = (g_local, g_visit) if seleccion == "home" else (g_visit, g_local)
    diff = (g_sel + punto) - g_opp
    if abs(diff) < 1e-9:
        return "push"
    return "win" if diff > 0 else "loss"


def _es_terminal(e: dict) -> bool:
    tipo = str((e.get("status") or {}).get("type") or "").lower()
    return tipo in ("finished", "canceled", "cancelled")


def _fechas_objetivo(inicio_utc: datetime, now: datetime, vista: str | None, estado_tipo: str | None) -> list[str]:
    ny_ini = _utc(inicio_utc).astimezone(cs.NY).date()
    cands: list[date] = []
    if vista:
        try:
            cands.append(date.fromisoformat(vista))
        except ValueError:
            pass
    cands.extend([ny_ini, ny_ini + timedelta(days=1), ny_ini - timedelta(days=1)])
    if (_utc(now) - _utc(inicio_utc)) > timedelta(hours=20):
        cands.append(_utc(now).astimezone(cs.NY).date())
    # Orden estable deduplicado; si ya vimos el partido vivo sin aplazamiento, basta refrescar su fecha.
    out: list[str] = []
    for d in cands:
        s = d.isoformat()
        if s not in out:
            out.append(s)
    if vista and estado_tipo not in ("postponed", "delayed", "interrupted"):
        return [out[0]]
    return out


class RespaldoTenis:
    """Sesión compartida por corrida para leer archivo local y consultar SportsAPIPro bajo demanda."""

    def __init__(self, key: str | None = None, *, raiz: Path | None = None,
                 eq_raiz: Path | None = None, call: Callable[[str, str], tuple[int, bytes]] | None = None,
                 clock: Callable[[], datetime] | None = None, tope: int = DIARIO, solo_archivo: bool = False):
        self.key = (settings.sportsapipro_key or "") if key is None else key
        self.raiz = carpeta() if raiz is None else Path(raiz)
        self.eq_raiz = dir_equivalencias() if eq_raiz is None else Path(eq_raiz)
        self.call = call
        self.clock = clock or (lambda: datetime.now(UTC))
        self.tope = tope
        self.solo_archivo = solo_archivo
        self.agotado = False
        self.peticiones = 0
        self.hits_archivo = 0
        self.hits_api = 0
        self._db: sqlite3.Connection | None = None
        self._escribible = False
        self._db_iniciada = False
        self._cargado_desde: datetime | None = None
        self._eventos: dict[int, tuple[datetime, str, dict]] = {}
        self._ultimas_fechas: dict[str, datetime] = {}

    def __enter__(self) -> "RespaldoTenis":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _registrar_eventos(self, fecha: str, recibido: datetime, eventos: list[dict]) -> None:
        for e in eventos:
            eid = int(e["id"])
            prev = self._eventos.get(eid)
            if prev is None or recibido >= prev[0]:
                self._eventos[eid] = (recibido, fecha, e)

    def _iniciar_db(self) -> None:
        if self._db_iniciada:
            return
        self._db_iniciada = True
        if not self.solo_archivo and self.key:
            db = _conectar_rw(self.raiz)
            if db is not None:
                self._db, self._escribible = db, True
                return
        self._db = _conectar_ro(self.raiz)
        self._escribible = False

    def _cargar_archivo(self, desde: datetime) -> None:
        self._iniciar_db()
        if self._cargado_desde is not None and desde >= self._cargado_desde:
            return
        observaciones: list[tuple[str, int, str, int, Path, datetime]] = []
        bases = []
        if self.eq_raiz is not None:
            bases.append((self.eq_raiz, _conectar_ro(self.eq_raiz), False))
        if self._db is not None:
            bases.append((self.raiz, self._db, True))
        try:
            for orden, (base, db, es_propia) in enumerate(bases):
                if db is None:
                    continue
                for r in _filas_calendario(db, desde):
                    rec_at = _utc(datetime.fromisoformat(r["received_at"]))
                    prev = self._ultimas_fechas.get(r["fecha"])
                    if prev is None or rec_at > prev:
                        self._ultimas_fechas[r["fecha"]] = rec_at
                    if r["status"] == 200:
                        observaciones.append((r["received_at"], orden, r["fecha"], r["id"],
                                              base / r["body_path"], rec_at))
                if not es_propia:
                    db.close()
        except sqlite3.Error as exc:
            log.warning("SportsAPIPro tenis resultados: fallo leyendo caché SQLite: %s", exc)
        for _rat, _ord, fecha, _rid, path, rec_at in sorted(observaciones, key=lambda x: (x[0], x[1], x[3])):
            try:
                evs = _leer_eventos_body(gzip.decompress(path.read_bytes()))
            except (OSError, ValueError):
                continue
            self._registrar_eventos(fecha, rec_at, evs)
        self._cargado_desde = desde

    def usadas_hoy(self, ahora: datetime) -> int:
        self._iniciar_db()
        if self._db is None:
            return self.peticiones
        return max(_sp().usadas_hoy(self._db, _utc(ahora)), self.peticiones)

    def _consultar_fecha(self, fecha: str, ahora: datetime) -> bool:
        ultimo = self._ultimas_fechas.get(fecha)
        if ultimo and (_utc(ahora) - ultimo) < COOLDOWN_FECHA:
            return False
        if self.agotado or self.solo_archivo or not self.key:
            return False
        if self.tope and self.usadas_hoy(ahora) >= self.tope:
            self.agotado = True
            return False
        fetcher = self.call or _sp().http
        status, body = fetcher(API % fecha, self.key)
        recibido = _utc(self.clock())
        self.peticiones += 1
        self._ultimas_fechas[fecha] = recibido
        if self._escribible and self._db is not None:
            try:
                _sp().archivar(self.raiz, self._db, "calendario", fecha, status, body, recibido)
            except (OSError, sqlite3.Error) as exc:
                log.warning("No se pudo archivar recibo de tenis %s: %s", fecha, exc)
        if status == 429:
            self.agotado = True
            return False
        if status != 200:
            return False
        self._registrar_eventos(fecha, recibido, _leer_eventos_body(body))
        return True

    def resolver(self, local: str, visitante: str, inicio_utc: datetime, mercado: str, seleccion: str,
                 linea=None, *, now: datetime | None = None, jugador_id=None) -> str | None:
        """Devuelve ``win`` / ``loss`` / ``push`` / ``void`` o ``None``; 0 peticiones si no procede."""
        if jugador_id or mercado not in MERCADOS_SOPORTADOS or not local or not visitante:
            return None
        ahora = _utc(now or self.clock())
        inicio = _utc(inicio_utc)
        self._cargar_archivo(inicio)
        hallado = buscar_evento(self._eventos, local, visitante, inicio)
        if hallado and _es_terminal(hallado[0]):
            res = calificar_evento(hallado[0], hallado[1], mercado, seleccion, linea)
            if res:
                self.hits_archivo += 1
            return res
        if self.solo_archivo or not self.key or self.agotado or ahora < inicio + MIN_EDAD:
            return None
        vista = hallado[2] if hallado else None
        estado_tipo = str(((hallado[0].get("status") or {}).get("type") or "")).lower() if hallado else None
        for fecha in _fechas_objetivo(inicio, ahora, vista, estado_tipo):
            self._consultar_fecha(fecha, ahora)
            hallado = buscar_evento(self._eventos, local, visitante, inicio)
            if hallado:
                if _es_terminal(hallado[0]):
                    res = calificar_evento(hallado[0], hallado[1], mercado, seleccion, linea)
                    if res:
                        self.hits_api += 1
                    return res
                # Ya localizamos el partido pero sigue activo: no gastar peticiones en fechas vecinas.
                if str(((hallado[0].get("status") or {}).get("type") or "")).lower() not in (
                        "postponed", "delayed", "interrupted"):
                    break
        return None

    def resolver_pata(self, pata: dict, now: datetime) -> str | None:
        if pata.get("deporte") != "tenis":
            return None
        evento = pata.get("evento") or []
        if len(evento) < 5:
            return None
        return self.resolver(evento[3], evento[4], pata["inicio_utc"], pata["mercado"],
                             pata["seleccion"], pata.get("linea"), now=now, jugador_id=pata.get("jugador_id"))

    def resolver_paso(self, paso: dict, now: datetime) -> str | None:
        if paso.get("deporte") != "tenis":
            return None
        return self.resolver(paso["evento_local"], paso["evento_visitante"], paso["evento_inicio"],
                             paso.get("market") or "h2h", paso["selection"], paso.get("line"), now=now)

    def debe_alertar(self, ref: str, ahora: datetime, cada: timedelta = timedelta(hours=24)) -> bool:
        """Limita a una alerta por día por pata cuando hay almacenamiento SQLite escribible."""
        self._iniciar_db()
        if not self._escribible or self._db is None:
            return True
        now_u = _utc(ahora)
        row = self._db.execute("SELECT ultimo FROM alertas WHERE ref = ?", (ref,)).fetchone()
        if row is not None and now_u - _utc(datetime.fromisoformat(row["ultimo"])) < cada:
            return False
        with self._db:
            self._db.execute("INSERT INTO alertas(ref, ultimo) VALUES(?, ?) "
                             "ON CONFLICT(ref) DO UPDATE SET ultimo = excluded.ultimo",
                             (ref, now_u.isoformat()))
        return True

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
            self._db_iniciada = False


def respaldo_solo_archivo(*, raiz: Path | None = None, eq_raiz: Path | None = None) -> RespaldoTenis:
    return RespaldoTenis(key="", raiz=raiz, eq_raiz=eq_raiz, solo_archivo=True)
