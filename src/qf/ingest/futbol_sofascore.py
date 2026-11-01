"""Adaptador del archivo SofaScore (formato del scraper) hacia la tabla única `futbol.dato`.

Cada partido emparejado con `matches` aporta, desde sus bloques originales, diez tipos de dato: jugador, equipo (por
periodo), baja, alineación, entrenador, contexto, tiro, incidencia, momentum y posición media. Quedan fuera a
propósito `h2h`, `pregame_form` y `team_streaks` (no verificables como previos al partido) y `best_players` /
`player_ranking` (los calcula el propio descargador a partir de lo ya guardado). Los originales completos siguen
como archivos; en la base solo su índice (`futbol.original`).

Reglas de la tabla única (db/094-096):
  * un partido de una fuente apunta a UN solo `match_id` (`futbol.partido_fuente`);
  * cada tipo de un partido tiene UNA fuente dueña (columna `fuente` de `futbol.dato`) y la prioridad sale de
    `futbol.prioridad_entidad` (jugador, baja, alineación y entrenador: FotMob > SofaScore > API-Football);
  * si el dueño actual es mejor, SofaScore no pisa nada; en `jugador` y `baja` solo COMPLETA las columnas que la
    fila de la fuente dueña tiene vacías (xG del jugador, pases clave, penaltis...) y lo anota en `fuente_extra`.
    Nunca completa `nota`, `valor_mercado` ni `posicion_id`: son entradas del motor con el sentido de cada fuente;
  * un tipo sin filas no se adueña del partido (si SofaScore no trae bajas, siguen las de FotMob);
  * el id canónico de un jugador de SofaScore es su propio id; cada jugador se registra en `futbol.jugador` y
    `futbol.jugador_fuente_id` para que las demás fuentes se enlacen con él;
  * recargar el mismo original (mismo `raw_sha256`) no hace nada, salvo con `--forzar`.

Línea de órdenes (simulacro salvo `--aplicar`; solo lee `matches`, `teams` y alias):
    python -m qf.ingest.futbol_sofascore --archive ~/sofascore-scraper/data/v3 --league it.serie_a \\
        --workdir /tmp/futbol_it [--since 2026-10-31] [--forzar] [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from .fotmob_import import records, timestamp
from .sofascore_history import positive_id
from .sofascore_local import match_dir, normalize_archive, read_match, snapshot_sql, verify_plan

FUENTE = 'sofascore'
LOCK_ID = 61013085
BATCH = 50
SMALL = 32767
TIPOS = ('alineacion', 'jugador', 'baja', 'entrenador', 'contexto', 'tiro', 'incidencia', 'equipo', 'momentum',
         'posicion')

# Columnas con decimales; el resto de las numéricas son enteros (SMALLINT).
REAL = {'minutos', 'nota', 'xa', 'xg', 'xgot', 'goles_evitados', 'km', 'vel_max', 'distancia_conduccion',
        'mejor_conduccion', 'progresion_total', 'distancia_progresiva', 'km_alta_velocidad', 'km_carrera',
        'km_esprint', 'valor_parada', 'valor_defensivo', 'valor_regate', 'valor_porteria', 'valor_pase', 'valor_tiro',
        'nota_alternativa', 'posesion', 'pct_duelos_aereos', 'pct_regates', 'pct_duelos', 'pct_duelos_suelo',
        'pct_entradas'}

JUGADOR = {  # columna de futbol.dato -> clave de SofaScore en `statistics` del jugador
    'minutos': 'minutesPlayed', 'nota': 'rating', 'goles': 'goals', 'asistencias': 'goalAssist',
    'xa': 'expectedAssists', 'xg': 'expectedGoals', 'xgot': 'expectedGoalsOnTarget',
    'goles_evitados': 'goalsPrevented', 'tiros_puerta': 'onTargetScoringAttempt', 'tiros_fuera': 'shotOffTarget',
    'tiros_bloq': 'blockedScoringAttempt', 'tiros_totales': 'totalShots',
    'grandes_ocasiones_creadas': 'bigChanceCreated', 'grandes_ocasiones_falladas': 'bigChanceMissed',
    'pases': 'totalPass', 'pases_acertados': 'accuratePass', 'pases_clave': 'keyPass',
    'balones_largos': 'totalLongBalls', 'balones_largos_acertados': 'accurateLongBalls',
    'centros': 'totalCross', 'centros_acertados': 'accurateCross', 'duelos_ganados': 'duelWon',
    'duelos_perdidos': 'duelLost', 'aereos_ganados': 'aerialWon', 'aereos_perdidos': 'aerialLost',
    'entradas': 'totalTackle', 'entradas_ganadas': 'wonTackle', 'intercepciones': 'interceptionWon',
    'despejes': 'totalClearance', 'recuperaciones': 'ballRecovery', 'perdidas': 'possessionLostCtrl',
    'perdidas_balon': 'dispossessed', 'faltas': 'fouls', 'faltas_recibidas': 'wasFouled',
    'fuera_juego': 'totalOffside', 'toques': 'touches', 'paradas': 'saves', 'km': 'kilometersCovered',
    'sprints': 'numberOfSprints', 'vel_max': 'topSpeed', 'conducciones': 'ballCarriesCount',
    'conducciones_progresivas': 'progressiveBallCarriesCount', 'distancia_conduccion': 'totalBallCarriesDistance',
    'mejor_conduccion': 'bestBallCarryProgression', 'progresion_total': 'totalProgression',
    'distancia_progresiva': 'totalProgressiveBallCarriesDistance', 'km_alta_velocidad': 'metersCoveredHighSpeedRunningKm',
    'km_carrera': 'metersCoveredRunningKm', 'km_esprint': 'metersCoveredSprintingKm', 'error_gol': 'errorLeadToAGoal',
    'error_tiro': 'errorLeadToAShot', 'penaltis_ganados': 'penaltyWon', 'penaltis_cometidos': 'penaltyConceded',
    'penaltis_parados': 'penaltySave', 'penaltis_enfrentados': 'penaltyFaced', 'goles_propia': 'ownGoals',
    'palos': 'hitWoodwork', 'despejes_linea': 'clearanceOffLine', 'ultimo_hombre': 'lastManTackle',
    'bloqueos': 'outfielderBlock', 'regates_intentados': 'totalContest', 'regates_ganados': 'wonContest',
    'regates_perdidos': 'challengeLost', 'toques_fallidos': 'unsuccessfulTouch',
    'pases_propio_campo': 'totalOwnHalfPasses', 'pases_propio_campo_acertados': 'accurateOwnHalfPasses',
    'pases_campo_rival': 'totalOppositionHalfPasses', 'pases_campo_rival_acertados': 'accurateOppositionHalfPasses',
    'salidas_portero': 'totalKeeperSweeper', 'salidas_portero_acertadas': 'accurateKeeperSweeper',
    'paradas_dentro_area': 'savedShotsFromInsideTheBox', 'centros_no_atrapados': 'crossNotClaimed',
    'atrapadas_altas': 'goodHighClaim', 'punos': 'punches', 'valor_parada': 'keeperSaveValue',
    'valor_defensivo': 'defensiveValueNormalized', 'valor_regate': 'dribbleValueNormalized',
    'valor_porteria': 'goalkeeperValueNormalized', 'valor_pase': 'passValueNormalized',
    'valor_tiro': 'shotValueNormalized',
}

EQUIPO = {  # columna de futbol.dato -> clave de la estadística de equipo
    'posesion': 'ballPossession', 'xgot': 'expectedGoalsOnTarget', 'grandes_ocasiones_creadas': 'bigChanceCreated',
    'grandes_ocasiones_falladas': 'bigChanceMissed', 'tiros_fuera': 'shotsOffGoal',
    'tiros_bloq': 'blockedScoringAttempt', 'tiros_dentro_area': 'totalShotsInsideBox',
    'tiros_fuera_area': 'totalShotsOutsideBox', 'paradas': 'goalkeeperSaves', 'goles_evitados': 'goalsPrevented',
    'faltas': 'fouls', 'tiros_libres': 'freeKicks', 'fuera_juego': 'offsides', 'pases': 'passes',
    'pases_acertados': 'accuratePasses', 'balones_largos_acertados': 'accurateLongBalls',
    'centros_acertados': 'accurateCross', 'entradas': 'totalTackle', 'intercepciones': 'interceptionWon',
    'recuperaciones': 'ballRecovery', 'despejes': 'totalClearance', 'perdidas_balon': 'dispossessed',
    'toques_area_rival': 'touchesInOppBox', 'entradas_ultimo_tercio': 'finalThirdEntries',
    'saques_banda': 'throwIns', 'saques_puerta': 'goalKicks', 'km': 'kilometersCovered', 'sprints': 'numberOfSprints',
    'pases_filtrados': 'accurateThroughBall', 'pct_duelos_aereos': 'aerialDuelsPercentage',
    'paradas_estiradas': 'diveSaves', 'pct_regates': 'dribblesPercentage', 'pct_duelos': 'duelWonPercent',
    'errores_tiro': 'errorsLeadToShot', 'fase_ultimo_tercio': 'finalThirdPhaseStatistic',
    'faltas_ultimo_tercio': 'fouledFinalThird', 'pct_duelos_suelo': 'groundDuelsPercentage',
    'atrapadas_altas': 'highClaims', 'palos': 'hitWoodwork', 'pct_entradas': 'wonTacklePercent',
}
# Del partido completo ya viven en `matches` y no se repiten; por mitad solo existen aquí (mercados 1T/2T).
EN_MATCHES = {'xg': 'expectedGoals', 'corners': 'cornerKicks', 'tiros_totales': 'totalShotsOnGoal',
              'tiros_puerta': 'shotsOnGoal', 'amarillas': 'yellowCards', 'rojas': 'redCards'}
PERIODO = {'ALL': 0, '1ST': 1, '2ND': 2}  # `evento` de las filas de tipo equipo

# Lo que SofaScore puede completar en una fila que posee otra fuente de mejor prioridad.
NO_COMPLETAR = {'nota', 'valor_mercado', 'posicion_id'}
COMPLETAR = {
    'jugador': [c for c in JUGADOR if c not in NO_COMPLETAR] + ['nota_alternativa', 'edad', 'posicion', 'camiseta'],
    'baja': ['motivo_codigo', 'descripcion'],
}


def num(value, integer=False):
    """Número finito o None; los enteros fuera de smallint se descartan en vez de reventar la carga."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float('inf'), float('-inf')):
        return None
    if integer:
        return int(round(out)) if abs(out) <= SMALL else None
    return out


def cell(column, value):
    """Valor de una columna numérica con el tipo que le toca (entero o real)."""
    return num(value, integer=column not in REAL)


def player_ref(block):
    block = block or {}
    pid = block.get('id')
    return (pid if positive_id(pid) else None), block.get('name')


def age_at(birth_timestamp, kickoff_iso):
    """Años cumplidos el día del partido, o None."""
    if not isinstance(birth_timestamp, (int, float)) or isinstance(birth_timestamp, bool):
        return None
    born = datetime.fromtimestamp(birth_timestamp, timezone.utc)
    when = timestamp(kickoff_iso)
    years = when.year - born.year - ((when.month, when.day) < (born.month, born.day))
    return years if 10 <= years <= 60 else None


def base(match_id, tipo, side='', jugador_id=0, evento=0, **columnas):
    """Fila de `futbol.dato` con sus claves y los valores dados (las columnas no nombradas quedan NULL)."""
    return {'match_id': match_id, 'tipo': tipo, 'side': side, 'jugador_id': jugador_id, 'evento': evento,
            'fuente': FUENTE, 'pit': 'reconstruido' if tipo == 'baja' else 'posterior', **columnas}


def compact_network(actions):
    """Pases que llevaron al gol: [jugador, tipo, minuto, x, y, x_fin, y_fin]."""
    out = []
    for step in actions or []:
        pid, _ = player_ref(step.get('player'))
        spot, end = step.get('playerCoordinates') or {}, step.get('passEndCoordinates') or {}
        out.append([pid, step.get('eventType'), step.get('time'), spot.get('x'), spot.get('y'), end.get('x'), end.get('y')])
    return out or None


def build_entities(match_id, blocks, row):
    """Filas de `futbol.dato` por tipo (dicts con los nombres de columna de la tabla). No toca la base."""
    out = {tipo: [] for tipo in TIPOS}
    lineup = blocks.get('lineups') or {}
    confirmed = lineup.get('confirmed') is True
    for item in row.get('lineups') or []:
        out['alineacion'].append(base(match_id, 'alineacion', item['side'], formacion=item.get('formation'),
                                      confirmada=confirmed, completa=bool(item.get('complete'))))
    seen = set()
    for side in ('home', 'away'):
        for entry in (lineup.get(side) or {}).get('players') or []:
            pid, name = player_ref(entry.get('player'))
            if pid is None or not name or pid in seen:
                continue
            seen.add(pid)
            stats = entry.get('statistics') if isinstance(entry.get('statistics'), dict) else {}
            who = entry.get('player') or {}
            market = (who.get('proposedMarketValueRaw') or {}).get('value')
            fila = base(match_id, 'jugador', side, pid, nombre=name, id_en_fuente=pid, posicion=entry.get('position'),
                        titular=entry.get('substitute') is False,  # el suplente sin minutos se conserva: plantilla del día
                        camiseta=str(entry.get('jerseyNumber') or entry.get('shirtNumber') or '') or None,
                        edad=age_at(who.get('dateOfBirthTimestamp'), row['kickoff_utc']),
                        valor_mercado=int(market) if isinstance(market, (int, float)) and not isinstance(market, bool)
                        and market > 0 else None)
            for column, key in JUGADOR.items():
                fila[column] = cell(column, stats.get(key))
            fila['nota_alternativa'] = num((stats.get('ratingVersions') or {}).get('alternative'))
            out['jugador'].append(fila)
    for absent in row.get('absences') or []:
        data = absent.get('availability') or {}
        reason = data.get('reason')
        out['baja'].append(base(match_id, 'baja', absent['side'], absent['source_player_id'],
                                nombre=absent['player_name'], id_en_fuente=absent['source_player_id'],
                                estado=str(data.get('type') or 'missing'),
                                motivo_codigo=reason if isinstance(reason, int) else None,
                                descripcion=data.get('description')))
    managers = blocks.get('managers') or {}
    for side, key in (('home', 'homeManager'), ('away', 'awayManager')):
        mid, name = player_ref(managers.get(key))
        if mid is not None:
            out['entrenador'].append(base(match_id, 'entrenador', side, nombre=name, id_en_fuente=mid))
    event = blocks.get('event') or {}
    event = event.get('event', event)
    referee = event.get('referee') or {}
    time_info = event.get('time') or {}
    home_score, away_score = event.get('homeScore') or {}, event.get('awayScore') or {}
    if referee or event.get('attendance'):
        # La trayectoria del árbitro (partidos, tarjetas) se contó al descargar: es posterior al partido.
        out['contexto'].append(base(
            match_id, 'contexto', nombre=referee.get('name'),
            id_en_fuente=referee.get('id') if positive_id(referee.get('id')) else None,
            arbitro_partidos=num(referee.get('games'), True),
            arbitro_amarillas=num(referee.get('yellowCards'), True), arbitro_rojas=num(referee.get('redCards'), True),
            arbitro_doble_amarilla=num(referee.get('yellowRedCards'), True),
            arbitro_pais=(referee.get('country') or {}).get('alpha2'),
            ronda=num((event.get('roundInfo') or {}).get('round'), True),
            descuento_1t=num(time_info.get('injuryTime1'), True), descuento_2t=num(time_info.get('injuryTime2'), True),
            goles_local_1t=num(home_score.get('period1'), True), goles_visita_1t=num(away_score.get('period1'), True),
            asistencia=num(event.get('attendance'), True) if not isinstance(event.get('attendance'), bool) else None))
    for shot in (blocks.get('shotmap') or {}).get('shotmap') or []:
        if not positive_id(shot.get('id')):
            continue
        pid, name = player_ref(shot.get('player'))
        gk_id, gk_name = player_ref(shot.get('goalkeeper'))
        mouth, spot = shot.get('goalMouthCoordinates') or {}, shot.get('playerCoordinates') or {}
        block = shot.get('blockCoordinates') or {}
        out['tiro'].append(base(
            match_id, 'tiro', 'home' if shot.get('isHome') else 'away', pid or 0, shot['id'], nombre=name,
            minuto=num(shot.get('time'), True), segundo=num(shot.get('timeSeconds'), True),
            anadido=num(shot.get('addedTime'), True), segundos_periodo=num(shot.get('periodTimeSeconds'), True),
            resultado=shot.get('shotType'), situacion=shot.get('situation'), parte_cuerpo=shot.get('bodyPart'),
            x=num(spot.get('x')), y=num(spot.get('y')), boca=shot.get('goalMouthLocation'), boca_x=num(mouth.get('x')),
            boca_y=num(mouth.get('y')), boca_z=num(mouth.get('z')), bloqueo_x=num(block.get('x')),
            bloqueo_y=num(block.get('y')), bloqueo_z=num(block.get('z')), tipo_gol=shot.get('goalType'),
            portero_id=gk_id, portero=gk_name, xg=num(shot.get('xg')), xgot=num(shot.get('xgot'))))
    for order, item in enumerate((blocks.get('incidents') or {}).get('incidents') or []):
        kind = item.get('incidentType')
        if not kind or order > SMALL:
            continue
        if kind == 'substitution':
            first, second = item.get('playerOut'), item.get('playerIn')
        else:
            first, second = item.get('player'), item.get('assist1') or item.get('playerIn')
        pid, name = player_ref(first)
        pid2, name2 = player_ref(second)
        added = num(item.get('addedTime'), True)
        side = item.get('isHome')
        out['incidencia'].append(base(
            match_id, 'incidencia', '' if side is None else ('home' if side else 'away'), pid or 0, order,
            subtipo=kind, clase=item.get('incidentClass'), minuto=num(item.get('time'), True),
            anadido=added if added is not None and added < 900 else None, nombre=name or item.get('playerName'),
            jugador2_id=pid2, jugador2=name2, razon=item.get('reason') or item.get('description'),
            texto=item.get('text'), marcador_local=num(item.get('homeScore'), True),
            marcador_visita=num(item.get('awayScore'), True),
            lesion=item.get('injury') if isinstance(item.get('injury'), bool) else None,
            duracion=num(item.get('length'), True),
            anulada=item.get('rescinded') if isinstance(item.get('rescinded'), bool) else None,
            confirmada=item.get('confirmed') if isinstance(item.get('confirmed'), bool) else None,
            red_pases=compact_network(item.get('footballPassingNetworkAction'))))
    for period in (blocks.get('statistics') or {}).get('statistics') or []:
        if period.get('period') not in PERIODO:
            continue
        stats = {}
        for group in period.get('groups') or []:
            for item in group.get('statisticsItems') or []:
                stats.setdefault(item.get('key'), (item.get('homeValue'), item.get('awayValue')))
        if not stats:
            continue
        for index, side in enumerate(('home', 'away')):
            fila = base(match_id, 'equipo', side, evento=PERIODO[period['period']])
            for column, key in {**EQUIPO, **EN_MATCHES}.items():  # todas las filas con las mismas columnas
                pair = None if fila['evento'] == 0 and column in EN_MATCHES else stats.get(key)
                fila[column] = cell(column, pair[index]) if pair else None
            out['equipo'].append(fila)
    for point in (blocks.get('momentum') or {}).get('graphPoints') or []:
        minute = num(point.get('minute'))
        if minute is None:
            continue
        out['momentum'].append(base(match_id, 'momentum', evento=int(round(minute * 2)), minuto=int(minute),
                                    minuto_decimal=minute, momentum=num(point.get('value'))))
    positions = blocks.get('average_positions') or {}
    for side in ('home', 'away'):
        for entry in positions.get(side) or []:
            pid, name = player_ref(entry.get('player'))
            if pid is None:
                continue
            out['posicion'].append(base(match_id, 'posicion', side, pid, nombre=name, pos_x=num(entry.get('averageX')),
                                        pos_y=num(entry.get('averageY')),
                                        puntos=num(entry.get('pointsCount'), True)))
    return out


def originals_index(states, source_match_id):
    return [(FUENTE, source_match_id, name, meta['sha256'], meta.get('bytes'), timestamp(meta['fetched_at']))
            for name, meta in states.items() if meta.get('state') == 'ok']


def players_of(entities):
    """(id, nombre) de todos los jugadores de SofaScore que aparecen en las filas de un partido."""
    found = {}
    for tipo in ('jugador', 'baja', 'tiro', 'incidencia', 'posicion'):
        for row in entities.get(tipo, []):
            if row['jugador_id']:
                found.setdefault(row['jugador_id'], row.get('nombre'))
            if row.get('jugador2_id'):
                found.setdefault(row['jugador2_id'], row.get('jugador2'))
    return found


def register_players(connection, found):
    """Alta en la identidad única: el id canónico de un jugador de SofaScore es su propio id."""
    for pid, name in found.items():
        connection.execute("INSERT INTO futbol.jugador (jugador_id, nombre) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                           (pid, name or '?'))
        connection.execute("""INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia)
                              VALUES (%s,%s,%s,'id_canonico') ON CONFLICT DO NOTHING""", (FUENTE, pid, pid))


def insert_rows(connection, rows, received):
    """INSERT de filas del mismo tipo (mismas columnas), con los JSONB envueltos."""
    dicts = [dict(r, recibido_en=received) for r in rows]
    columns = list(dicts[0])
    values = [[Jsonb(d[c]) if c == 'red_pases' and d[c] is not None else d[c] for c in columns] for d in dicts]
    with connection.cursor() as cursor:
        cursor.executemany('INSERT INTO futbol.dato (%s) VALUES (%s)' % (','.join(columns), ','.join(['%s'] * len(columns))),
                           values)


def complete_rows(connection, match_id, tipo, rows):
    """Rellena las columnas vacías de las filas que posee otra fuente. Devuelve cuántas columnas se completaron."""
    columns = COMPLETAR[tipo]
    current = {(r[0], r[1]): dict(zip(columns, r[2:])) for r in connection.execute(
        'SELECT side, jugador_id, %s FROM futbol.dato WHERE match_id=%%s AND tipo=%%s' % ','.join(columns),
        (match_id, tipo))}
    filled = 0
    for row in rows:
        have = current.get((row['side'], row['jugador_id']))
        if have is None:
            continue
        diff = {c: row.get(c) for c in columns if have[c] is None and row.get(c) is not None}
        if not diff:
            continue
        assignments = ','.join('%s=%%s' % c for c in diff)
        connection.execute('UPDATE futbol.dato SET %s, fuente_extra=%%s WHERE match_id=%%s AND tipo=%%s AND side=%%s '
                           'AND jugador_id=%%s' % assignments,
                           [*diff.values(), FUENTE, match_id, tipo, row['side'], row['jugador_id']])
        filled += len(diff)
    return filled


def apply_batch(connection, batch, force=False):
    """Carga un lote de partidos en una transacción. `batch`: lista de dicts con match_id, row, entities, states.
    La prioridad de cada tipo sale de `futbol.prioridad_entidad`. Con `force` recarga aunque el original no cambie."""
    totals = Counter()
    priority = {(e, f): p for e, f, p in connection.execute(
        'SELECT entidad, fuente, prioridad FROM futbol.prioridad_entidad')}
    for item in batch:
        match_id, row = item['match_id'], item['row']
        known = connection.execute(
            "SELECT match_id, raw_sha256 FROM futbol.partido_fuente WHERE fuente=%s AND source_match_id=%s",
            (FUENTE, row['source_match_id'])).fetchone()
        if known and known[0] != match_id:
            raise ValueError('source_match_points_to_other_match:' + row['source_match_id'])
        if known and known[1] == row['raw_sha256'] and not force:
            totals['sin_cambios'] += 1
            continue
        received = timestamp(row['captured_at'])
        connection.execute(
            """INSERT INTO futbol.partido_fuente (match_id, fuente, source_match_id, raw_sha256, recibido_en)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, fuente) DO UPDATE SET source_match_id=EXCLUDED.source_match_id,
                 raw_sha256=EXCLUDED.raw_sha256, recibido_en=EXCLUDED.recibido_en""",
            (match_id, FUENTE, row['source_match_id'], row['raw_sha256'], received))
        register_players(connection, players_of(item['entities']))
        connection.execute("DELETE FROM futbol.original WHERE fuente=%s AND source_match_id=%s",
                           (FUENTE, row['source_match_id']))
        for entry in originals_index(item['states'], row['source_match_id']):
            connection.execute("""INSERT INTO futbol.original
                (fuente, source_match_id, bloque, sha256, bytes, recibido_en) VALUES (%s,%s,%s,%s,%s,%s)""", entry)
        for tipo, rows in item['entities'].items():
            if not rows:
                continue
            owner = connection.execute("SELECT fuente FROM futbol.dato WHERE match_id=%s AND tipo=%s LIMIT 1",
                                       (match_id, tipo)).fetchone()
            if owner and owner[0] != FUENTE and priority.get((tipo, owner[0]), 99) < priority.get((tipo, FUENTE), 99):
                totals['tipo_de_mejor_fuente'] += 1  # el dueño actual es mejor (p. ej. FotMob)
                if tipo in COMPLETAR:
                    totals['columnas_completadas'] += complete_rows(connection, match_id, tipo, rows)
                continue
            connection.execute('DELETE FROM futbol.dato WHERE match_id=%s AND tipo=%s', (match_id, tipo))
            insert_rows(connection, rows, received)
            totals['filas_' + tipo] += len(rows)
        totals['partidos'] += 1
    return totals


def items_from_plan(archive, normalized, reviewed, skipped):
    """Genera los partidos emparejados con sus entidades; los no emparejados se cuentan en `skipped`."""
    for row in records(normalized):
        decision = reviewed['decisions'].get(row['source_match_id'])
        if not decision or decision.get('mapping_status') != 'matched':
            skipped['sin_partido_en_matches'] += 1
            continue
        blocks, states, _manifest = read_match(match_dir(archive, row['source_match_id']))
        yield {'match_id': decision['match_id'], 'row': row, 'states': states,
               'entities': build_entities(decision['match_id'], blocks, row)}


def snapshot_from_database(connection, league, since):
    sql = snapshot_sql(league, since).rstrip(';')
    return connection.execute(sql).fetchone()[0]


def run(connection, archive, league, workdir, since, apply, force=False):
    from .fotmob_import import plan
    workdir = Path(workdir)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    report = normalize_archive(archive, league, workdir / 'norm', since)
    normalized = workdir / 'norm' / 'normalized.jsonl.gz'
    if report['valid'] == 0:  # nada nuevo desde `since`: no hay nada que emparejar
        return {'liga': league, 'normalizados': 0, 'rechazados': report['errors'][:5],
                'n_rechazados': len(report['errors']), 'sin_partidos_nuevos': True, 'aplicado': apply}
    snapshot = snapshot_from_database(connection, league, since or '2000-01-01')
    snapshot_path = workdir / 'snapshot.json'
    snapshot_path.write_text(json.dumps(snapshot, default=str), encoding='utf-8')
    plan_path = workdir / 'plan.json'
    plan(normalized, snapshot_path, plan_path)
    check = verify_plan(plan_path, normalized, snapshot_path)
    result = {'liga': league, 'normalizados': report['valid'], 'rechazados': report['errors'][:5],
              'n_rechazados': len(report['errors']), 'plan': check['totals'], 'plan_ok': check['ok'],
              'problemas_plan': check['problems'][:5]}
    reviewed = json.loads(plan_path.read_text(encoding='utf-8'))
    totals, batch = Counter(), []
    if apply:
        connection.execute('SELECT pg_advisory_lock(%s)', (LOCK_ID,))
    try:
        for item in items_from_plan(archive, normalized, reviewed, totals):
            if not apply:
                totals['partidos_a_cargar'] += 1
                for tipo, rows in item['entities'].items():
                    totals['filas_' + tipo] += len(rows)
                continue
            batch.append(item)
            if len(batch) == BATCH:
                with connection.transaction():
                    totals.update(apply_batch(connection, batch, force))
                batch = []
        if batch:
            with connection.transaction():
                totals.update(apply_batch(connection, batch, force))
    finally:
        if apply:
            connection.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
    result['totales'] = dict(totals)
    result['aplicado'] = apply
    return result


def main():
    import os
    import psycopg
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--league', required=True)
    parser.add_argument('--workdir', required=True)
    parser.add_argument('--since')
    parser.add_argument('--forzar', action='store_true', help='recarga aunque el original no haya cambiado')
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    with psycopg.connect(os.environ['PG_DSN']) as connection:
        print(json.dumps(run(connection, args.archive, args.league, args.workdir, args.since, args.aplicar, args.forzar),
                         ensure_ascii=True, default=str))


if __name__ == '__main__':
    main()
