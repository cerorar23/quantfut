import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

class _Api extends QuantFutApi {
  _Api(this.routes);
  final Map<String, dynamic Function()> routes;
  final calls = <String>[];

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add(path);
    return routes[path]!();
  }
}

JsonMap _fixture(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync())
        as Map<String, dynamic>;

final _event = {
  'event_id': '1',
  'tipoff_utc': '2026-10-27T20:00:00Z',
  'home_team': 'A',
  'away_team': 'B',
  'status': 'evaluated',
  'final': {'home': 99, 'away': 102},
};
final _row = {
  'event_id': '1',
  'player_id': 'winner',
  'market': 'winner',
  'market_label': 'Ganador',
  'probability_over': .3,
  'probability_under': .7,
  'sealed_at_utc': '2026-10-27T19:00:00Z',
  'result': {'status': 'evaluated', 'actual': 0},
};
JsonMap _nba([List<Map<String, dynamic>>? rows]) => {
  'live_v13': <String, dynamic>{
    'cohorts': <dynamic>[
      {
        'cohort': 'real',
        'created_at_utc': '2026-10-27T19:00:00Z',
        'events': [_event],
        'predictions': rows ?? [_row],
      },
    ],
  },
};

void main() {
  test(
    'NBA usa el lado y la probabilidad publicados, con resultado previo válido',
    () {
      final e = nbaEvents(_nba()).single;
      final m = e.markets.single;
      expect(m.selection, 'B');
      expect(m.probability, .7);
      expect(m.outcome, 'win');
      expect(m.eligible, isTrue);
      expect(e.sport, SportKind.nba);
      expect(e.score, '99 – 102');
      expect(e.status, 'finished');
      expect(e.seal, 'real');
    },
  );

  test('una revisión posterior al inicio no se cuenta como acierto previo', () {
    for (final changed in [
      {'performance_eligible': false},
      {'sealed_at_utc': '2026-10-27T20:01:00Z'},
    ]) {
      final m = nbaEvents(
        _nba([
          {..._row, ...changed},
        ]),
      ).single.markets.single;
      expect(m.outcome, isNull);
      expect(m.eligible, isFalse);
    }
  });

  test('NBA descarta cuarentena y probabilidades ausentes; conserva la revisión más reciente', () {
    expect(
      nbaEvents(
        _nba([
          {..._row, 'probability_over': null},
        ]),
      ),
      isEmpty,
    );
    final v = _nba();
    v['live_v13']['cohorts'][0]['events'][0] = {
      ..._event,
      'status': 'validation_hold',
    };
    expect(nbaEvents(v), isEmpty);
    final updated = _nba();
    final cohorts = updated['live_v13']['cohorts'] as List<dynamic>;
    cohorts.add({
      ...cohorts[0] as Map<String, dynamic>,
      'recalculated_at_utc': '2026-10-28T01:00:00Z',
      'predictions': [
        {..._row, 'probability_over': .8},
      ],
    });
    final events = nbaEvents(updated);
    expect(events, hasLength(1));
    expect(events.single.markets.single.selection, 'A');
  });

  test('NBA: jugadores y total llevan línea, jugador y empuje', () {
    final rows = [
      {
        ..._row,
        'market': 'player_points',
        'market_label': 'Puntos',
        'player': 'Ana',
        'player_id': 'p1',
        'probability_over': .6,
        'line': 20.5,
        'result': {'status': 'evaluated', 'actual': 20.5},
      },
      {
        ..._row,
        'market': 'game_total',
        'player_id': 'total',
        'probability_over': .55,
        'line': 200,
        'result': {'status': 'evaluated', 'actual': 210},
      },
    ];
    final ms = nbaEvents(_nba(rows)).single.markets;
    expect(ms[0].player, 'Ana');
    expect(ms[0].playerId, 'p1');
    expect(ms[0].line, 20.5);
    expect(ms[0].outcome, 'push');
    expect(ms[0].selection, 'Ana');
    expect(ms[1].selection, 'Total');
    expect(ms[1].outcome, 'win');
    expect(ms[1].player, isNull);
  });

  test('tenis exige estado ok/partial, sello y probabilidad', () {
    final e = {
      'id': '1',
      'sport': 'tenis',
      'home': 'A',
      'away': 'B',
      'start': '2026-10-27T20:00:00Z',
      'seal': 'abc',
      'markets': [
        {'id': 'winner', 'label': 'G', 'selection': 'A', 'probability': .65},
        {'id': 'x', 'label': 'G', 'selection': 'A', 'probability': 1.2},
      ],
    };
    final one = tennisEvents({
      'state': 'ok',
      'events': [e],
    });
    expect(one, hasLength(1));
    expect(one.single.markets, hasLength(1));
    expect(
      tennisEvents({
        'state': 'ok',
        'events': [
          {...e, 'seal': null},
        ],
      }),
      isEmpty,
    );
    expect(
      () => tennisEvents({
        'events': [e],
      }),
      throwsFormatException,
    );
  });

  test('un feed caído no tumba al otro', () async {
    final api = _Api({
      '/nba/api/data': () => throw Exception('red'),
      '/web/deportes/tenis': () => _fixture('tennis_feed.json'),
    });
    final nba = await loadSport(api, SportKind.nba);
    final tennis = await loadSport(api, SportKind.tennis);
    expect(nba.ready, isFalse);
    expect(nba.events, isEmpty);
    expect(tennis.ready, isTrue);
    expect(tennis.events, isNotEmpty);
    expect(api.calls, ['/nba/api/data', '/web/deportes/tenis']);
  });

  test('un estado no disponible o el fútbol devuelven feed no listo', () async {
    final api = _Api({
      '/web/deportes/tenis': () => {'state': 'unavailable', 'events': []},
    });
    expect((await loadSport(api, SportKind.tennis)).ready, isFalse);
    expect((await loadSport(api, SportKind.football)).ready, isFalse);
  });

  test('fixtures reales se leen sin errores', () {
    for (final events in [
      nbaEvents(_fixture('nba_feed.json')),
      tennisEvents(_fixture('tennis_feed.json')),
    ]) {
      expect(events, isNotEmpty);
      for (final e in events) {
        expect(e.markets, isNotEmpty);
      }
    }
  });

  test('destacado: mayor probabilidad entre los elegibles', () {
    final e = nbaEvents(
      _nba([
        {
          ..._row,
          'probability_over': .9,
          'sealed_at_utc': '2026-10-27T20:30:00Z',
        },
        {..._row, 'probability_over': .2},
        {..._row, 'probability_over': .35},
      ]),
    ).single;
    final f = featuredMarket(e)!;
    expect(f.probability, .8);
    expect(f.eligible, isTrue);
  });

  test('NBA: un jugador que no es texto no tumba el feed; el resto se lee', () {
    final events = nbaEvents(
      _nba([
        {..._row, 'market': 'player_points', 'market_label': 'Puntos', 'player': 123, 'player_id': 'p1', 'line': 20.5},
        _row,
      ]),
    );
    expect(events, hasLength(1));
    final markets = events.single.markets;
    expect(markets, hasLength(2));
    expect(markets.where((m) => m.player != null), isEmpty);
  });
}
