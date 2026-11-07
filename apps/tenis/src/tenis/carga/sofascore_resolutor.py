"""Resolución de jugadores para la carga de SofaScore.

El cargador recibe el resolutor por parámetro. `ResolutorPorId` crea un `jugador` por (circuito, `team.id`) con alias
`id_exacto` y escribe las aserciones que cambian (nombre, fecha de nacimiento, mano, altura, país). Otro resolutor con la
misma firma (multifuente, de `src/tenis/identidad/`) puede sustituirlo sin tocar el cargador.
"""
from datetime import datetime
from typing import Protocol


class ResolutorJugador(Protocol):
    def resolver(self, *, fuente: str, id_fuente: str, circuito: str, nombre: str | None,
                 fecha_nacimiento: str | None, pais: str | None, mano: str | None, altura_cm: str | None,
                 recibo_id: int, recibido_en: datetime, contexto: dict) -> int:
        """Devuelve el jugador_id de la persona; crea el jugador si no existe."""
        ...


class ResolutorPorId:
    """Clave: (circuito, id de SofaScore). Caché en memoria cargada una vez: sin consultas por fila."""

    CAMPOS = ("nombre", "fecha_nacimiento", "mano", "altura_cm", "pais")

    def __init__(self, cur, fuente: str = "sofascore"):
        self._cur = cur
        self._fuente = fuente
        self._mapa: dict[tuple[str, str], int] = {}
        self._ultimo: dict[tuple[int, str], str] = {}
        cur.execute("SELECT a.id_fuente, j.circuito, a.jugador_id FROM jugador_alias a "
                    "JOIN jugador j ON j.jugador_id = a.jugador_id WHERE a.fuente = %s AND a.metodo = 'id_exacto'",
                    (fuente,))
        for id_fuente, circuito, jid in cur.fetchall():
            self._mapa[(circuito, id_fuente)] = jid
        cur.execute("SELECT x.jugador_id, x.campo, x.valor FROM jugador_asercion x "
                    "JOIN jugador_alias a ON a.jugador_id = x.jugador_id AND a.fuente = %s "
                    "AND a.metodo = 'id_exacto' WHERE x.fuente = %s ORDER BY x.recibido_en, x.asercion_id",
                    (fuente, fuente))
        for jid, campo, valor in cur.fetchall():
            self._ultimo[(jid, campo)] = valor

    def resolver(self, *, fuente: str, id_fuente: str, circuito: str, nombre: str | None,
                 fecha_nacimiento: str | None, pais: str | None, mano: str | None, altura_cm: str | None,
                 recibo_id: int, recibido_en: datetime, contexto: dict) -> int:
        cur = self._cur
        jid = self._mapa.get((circuito, id_fuente))
        if jid is None:
            cur.execute("INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) "
                        "RETURNING jugador_id", (circuito, recibo_id, recibido_en))
            jid = cur.fetchone()[0]
            cur.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
                        "VALUES (%s, %s, %s, 'id_exacto', %s, %s) ON CONFLICT DO NOTHING",
                        (fuente, id_fuente, jid, recibo_id, recibido_en))
            self._mapa[(circuito, id_fuente)] = jid
        valores = {"nombre": nombre, "fecha_nacimiento": fecha_nacimiento, "mano": mano,
                   "altura_cm": altura_cm, "pais": pais}
        for campo in self.CAMPOS:
            valor = valores[campo]
            if valor and self._ultimo.get((jid, campo)) != valor:
                cur.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (jid, campo, valor, fuente, recibo_id, recibido_en))
                self._ultimo[(jid, campo)] = valor
        return jid
