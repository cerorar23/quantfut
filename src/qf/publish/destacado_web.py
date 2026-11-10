"""Selección congelada en `predictions.data_completeness`, protegida por su inmutabilidad y su sello."""
from __future__ import annotations

from datetime import datetime, timezone
from ..db import query_one


def obtener(match_id: str, sellado: bool = True, consulta=None) -> dict | None:
    condicion = """AND EXISTS (SELECT 1 FROM prediction_batches b
        WHERE b.created_at >= p.generated_at AND
        ((p.etapa='diaria' AND b.batch_kind='diario'
          AND b.batch_date=(p.generated_at AT TIME ZONE 'UTC')::date)
         OR (p.etapa='final' AND b.batch_kind='partido' AND b.match_id=p.match_id)))""" if sellado else ''
    row = (consulta or query_one)(f"""SELECT p.data_completeness->'web_destacado' AS snapshot
        FROM predictions p JOIN matches m USING(match_id)
        WHERE p.match_id=%s AND p.generated_at < m.kickoff_utc
          AND jsonb_typeof(p.data_completeness->'web_destacado'->'fila')='object'
          {condicion} ORDER BY p.generated_at, p.prediction_id LIMIT 1""", (match_id,))
    snapshot = row.get('snapshot') if row else None
    if not isinstance(snapshot, dict) or snapshot.get('version') != 1:
        return None
    try:
        at = datetime.fromisoformat(snapshot['decidido_en'])
        ko = datetime.fromisoformat(snapshot['kickoff_utc'])
        if at.tzinfo is None or ko.tzinfo is None or at >= ko:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return snapshot


def congelar(partido: dict, lam: tuple[float, float, float], ahora=None) -> dict | None:
    from ..api import partido_mercados as pm
    reloj_explicito = ahora is not None
    ahora = ahora or datetime.now(timezone.utc)
    if ahora >= partido['kickoff_utc']:
        return None
    anterior = obtener(partido['match_id'], sellado=False)
    if anterior:
        return anterior
    filas, marcadores = pm.filas_goles(*lam, partido['home_team'], partido['away_team'])
    filas += pm.filas_primer_tiempo(lam[0], lam[1], partido.get('league_id') or pm.liga_de_partido(partido['match_id']))
    corners, cards = pm.lambdas_estadisticas(partido['match_id'])
    filas += pm.filas_estadisticas(corners, cards)
    filas += pm.filas_complementarias(*lam, partido['home_team'], partido['away_team'], {f['id'] for f in filas})
    filas = pm.con_cuotas_casas(filas, pm.cuotas_casas(partido['match_id'], con_respaldo=False))
    _, _, destacado = pm.aplicar_acceso_web(filas, marcadores, {}, False)
    ahora = ahora if reloj_explicito else datetime.now(timezone.utc)
    if ahora >= partido['kickoff_utc']:
        return None
    return {'version': 1, 'decidido_en': ahora.isoformat(), 'kickoff_utc': partido['kickoff_utc'].isoformat(),
            'regla': {'cuota_min': pm.RANGO_DESTACADO[0], 'cuota_max': pm.RANGO_DESTACADO[1]},
            'fila': destacado}
