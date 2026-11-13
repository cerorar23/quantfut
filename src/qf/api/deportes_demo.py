"""Adaptador de DEMOSTRACIÓN del contrato `/deportes/v1`: datos sintéticos fijos bajo cualquier id de deporte del
catálogo cuyo `adaptador` sea `prueba`.

El router ve el método `para(deporte_id)` y liga el adaptador a ese id, así el `sport` de los eventos coincide con el
deporte pedido. Todo está marcado como demostración (liga, etiquetas y un bloque de texto) para que nadie lo confunda
con un pronóstico real. Nada aleatorio: solo cambia el desplazamiento de horas respecto de `ahora`.

Alta de un deporte de prueba: `catalogo.guardar_deporte({... 'deporte_id': 'golf_prueba', 'adaptador': 'prueba', ...})`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import deportes_v1 as dv

# (id, desplazamiento en minutos, estado, marcador)
_EVENTOS = (
    ('demo-1', -150, 'finished', '2-1'),
    ('demo-2', -60, 'finished', '0-3'),
    ('demo-3', 90, 'scheduled', None),
    ('demo-4', 20 * 60, 'scheduled', None),
)
# (clave de mercado, familia, etiqueta, selección, probabilidad, resultado si el evento terminó)
_MERCADOS = (
    ('demo_ganador_a', 'demo_resultado', 'Demo · Gana Equipo A', 'a', 0.45, 'win'),
    ('demo_ganador_b', 'demo_resultado', 'Demo · Gana Equipo B', 'b', 0.35, 'loss'),
    ('demo_empate', 'demo_resultado', 'Demo · Empate', 'x', 0.20, 'loss'),
    ('demo_total_mas', 'demo_totales', 'Demo · Más de 2.5', 'over', 0.55, 'win'),
    ('demo_total_menos', 'demo_totales', 'Demo · Menos de 2.5', 'under', 0.45, 'loss'),
    ('demo_ambos_si', 'demo_especiales', 'Demo · Ambos anotan', 'yes', 0.60, 'win'),
    ('demo_ambos_no', 'demo_especiales', 'Demo · No ambos anotan', 'no', 0.40, 'loss'),
)
_FAMILIA = {m[0]: m[1] for m in _MERCADOS}

_BLOQUES = [
    {'id': 'demo_tabla', 'tipo': 'tabla', 'titulo': '@demo_tabla', 'columnas': ['@equipo', '@demo_valor'],
     'filas': [['Equipo A', 12], ['Equipo B', 9]]},
    {'id': 'demo_barras', 'tipo': 'barras', 'titulo': '@demo_barras',
     'items': [{'etiqueta': '@demo_dato_a', 'valor': 0.6}, {'etiqueta': '@demo_dato_b', 'valor': 0.3},
               {'etiqueta': '@demo_dato_c', 'valor': 0.1}]},
    {'id': 'demo_pares', 'tipo': 'pares', 'titulo': '@demo_pares',
     'items': [{'etiqueta': '@demo_dato_a', 'valor': 7}, {'etiqueta': '@demo_dato_b', 'valor': 'Equipo B'}]},
    {'id': 'demo_aviso', 'tipo': 'texto', 'titulo': '@demo_titulo', 'cuerpo': '@demo_aviso'},
]


class _Ligado:
    """El adaptador de demostración atado a un id de deporte."""

    def __init__(self, deporte: str):
        self.deporte = deporte

    def _evento(self, fila, ahora: datetime) -> dv.Evento:
        id, minutos, estado, marcador = fila
        terminado = estado == 'finished'
        mercados = [dv.Mercado(
            id=f'{id}:{clave}', label=etiqueta, selection=sel, probability=p, eligible=True, market=clave,
            family=fam, outcome=res if terminado else None, principal=clave == 'demo_ganador_a')
            for clave, fam, etiqueta, sel, p, res in _MERCADOS]
        return dv.Evento(
            id=id, sport=self.deporte, home='Equipo A', away='Equipo B', league='Demostración',
            start=ahora + timedelta(minutes=minutos), status=estado, seal=None, score=marcador, bloqueados=0,
            imagenes=None, markets=mercados, destacado=mercados[0].id)

    def cartelera(self, inicio: datetime, fin: datetime) -> list[dv.Evento]:
        ahora = datetime.now(timezone.utc)
        return [e for e in (self._evento(f, ahora) for f in _EVENTOS) if inicio <= e.start < fin]

    def partido(self, id: str) -> dv.Evento | None:
        fila = next((f for f in _EVENTOS if f[0] == id), None)
        return self._evento(fila, datetime.now(timezone.utc)) if fila else None

    def familia_de(self, market: str) -> str:
        return _FAMILIA.get(market, dv.FAMILIA_OTROS)

    def bloques(self, id: str) -> list[dict]:
        return [dict(b) for b in _BLOQUES]


class AdaptadorDemo:
    def para(self, deporte_id: str) -> _Ligado:
        return _Ligado(deporte_id)


dv.ADAPTADORES['prueba'] = AdaptadorDemo()
