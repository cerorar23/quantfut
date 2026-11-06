import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';
import 'package:gobet/product/sports_quotes.dart';

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

  group('destacado de tenis: probabilidad máxima segura', () {
    Map<String, dynamic> match([Map<String, dynamic>? extra]) => {
      'id': '1',
      'sport': 'tenis',
      'home': 'A',
      'away': 'B',
      'start': '2026-10-27T20:00:00Z',
      'seal': 'abc',
      'markets': [
        {'id': 'alto', 'label': 'G', 'selection': 'A', 'probability': .80},
        {'id': 'medio', 'label': 'G', 'selection': 'B', 'probability': .78},
        {'id': 'corto', 'label': 'G', 'selection': 'C', 'probability': .95},
      ],
      ...?extra,
    };
    SportEvent read(Map<String, dynamic> e) => tennisEvents({
      'state': 'ok',
      'events': [e],
    }).single;

    test('sin campo del servidor se aplica la regla con la cuota del modelo', () {
      // .95 paga 1,05 (< 1,20): la mayor probabilidad que aún paga 1,20 es .80
      expect(featuredMarket(read(match()))?.id, 'alto');
    });

    test('el destacado del servidor manda aunque otro sea más probable', () {
      final e = read(
        match({
          'destacado': {'id': 'medio', 'score_destacado': 1.0},
        }),
      );
      expect(e.serverFeatured, isTrue);
      expect(featuredMarket(e)?.id, 'medio');
    });

    test(
      'el servidor dice que no hay destacado, o apunta a un mercado ausente',
      () {
        expect(featuredMarket(read(match({'destacado': null}))), isNull);
        expect(
          featuredMarket(
            read(
              match({
                'destacado': {'id': 'no-existe'},
              }),
            ),
          ),
          isNull,
        );
      },
    );
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
      '/nba/v1/cartelera': () => throw Exception('red'),
      '/web/deportes/tenis': () => _fixture('tennis_feed.json'),
    });
    final nba = await loadSport(api, SportKind.nba);
    final tennis = await loadSport(api, SportKind.tennis);
    expect(nba.ready, isFalse);
    expect(nba.events, isEmpty);
    expect(tennis.ready, isTrue);
    expect(tennis.events, isNotEmpty);
    expect(api.calls, [
      ...List.filled(7, '/nba/v1/cartelera'),
      '/web/deportes/tenis',
    ]);
  });

  group('NBA v2 (/nba/v1/cartelera)', () {
    JsonMap game(
      int id, {
      JsonMap? pick,
      JsonMap? result,
      String start = '2026-11-02T00:00:00Z',
    }) => {
      'id': id,
      'fecha': '2026-11-01',
      'local': {'codigo': 'BOS', 'nombre': 'Boston Celtics'},
      'visitante': {'codigo': 'NYK', 'nombre': 'New York Knicks'},
      'inicio_utc': start,
      'sello_previsto': '2026-11-01T23:00:00+00:00',
      'resultado': result,
      'pronostico': pick,
    };
    JsonMap pick(String sealed, [double p = .7]) => {
      'hash': 'abc',
      'p_local': p,
      'sellado_en': sealed,
    };

    test('los partidos sin pronóstico salen con mercados vacíos y su hora de sellado; el resultado se evalúa', () {
      final events = nbaV2Events([
        game(1),
        game(
          2,
          pick: pick('2026-11-01T23:00:00Z'),
          result: {'local': 100.0, 'visitante': 90.0},
        ),
        game(
          3,
          pick: pick('2026-11-01T23:00:00Z', .3),
          result: {'local': 100.0, 'visitante': 90.0},
        ),
      ]);
      expect(events.map((e) => e.id), ['1', '2', '3']);
      final pending = events.first, win = events[1], loss = events.last;
      expect(pending.markets, isEmpty);
      expect(pending.seal, isEmpty);
      expect(pending.plannedSeal, DateTime.utc(2026, 11, 1, 23));
      expect(featuredMarket(pending), isNull);
      expect(win.markets.single.selection, 'Boston Celtics');
      expect(win.markets.single.probability, .7);
      expect(win.markets.single.outcome, 'win');
      expect(win.status, 'finished');
      expect(win.score, '100.0 – 90.0');
      expect(win.seal, 'abc');
      expect(loss.markets.single.selection, 'New York Knicks');
      expect(loss.markets.single.probability, closeTo(.7, 1e-9));
      expect(loss.markets.single.outcome, 'loss');
    });

    test(
      'un sello posterior al inicio es revisión: no cuenta ni se evalúa',
      () {
        final e = nbaV2Events([
          game(
            1,
            pick: pick('2026-11-02T00:30:00Z'),
            result: {'local': 100.0, 'visitante': 90.0},
          ),
        ]).single;
        expect(e.markets.single.eligible, isFalse);
        expect(e.markets.single.outcome, isNull);
        expect(featuredMarket(e), isNull);
      },
    );

    test('un pronóstico mal formado se trata como ausente y un partido inválido se descarta', () {
      expect(
        nbaV2Events([game(1, pick: pick('2026-11-01T23:00:00Z', 1.4))])
            .single
            .markets,
        isEmpty,
      );
      expect(
        nbaV2Events([
          game(
            1,
            pick: {
              'hash': '',
              'p_local': .6,
              'sellado_en': '2026-11-01T23:00:00Z',
            },
          ),
        ]).single.markets,
        isEmpty,
      );
      expect(
        nbaV2Events([
          {...game(1, pick: pick('2026-11-01T23:00:00Z')), 'id': 'x'},
        ]),
        isEmpty,
      );
      expect(
        nbaV2Events([
          {...game(1), 'inicio_utc': null},
        ]),
        isEmpty,
      );
    });

    test('un día que falla no tumba los demás; si fallan todos el feed no está listo', () async {
      var n = 0;
      final api = _Api({
        '/nba/v1/cartelera': () {
          if (n++ == 0) throw Exception('red');
          return {
            'partidos': [game(2, pick: pick('2026-11-01T23:00:00Z'))],
          };
        },
      });
      final feed = await loadSport(api, SportKind.nba);
      expect(feed.ready, isTrue);
      expect(feed.events.map((e) => e.id), ['2']);
      expect(feed.events.single.markets, isNotEmpty);
      expect(api.calls, List.filled(7, '/nba/v1/cartelera'));
      final broken = _Api({
        '/nba/v1/cartelera': () => {'otro': 1},
      });
      expect((await loadSport(broken, SportKind.nba)).ready, isFalse);
    });
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
        {
          ..._row,
          'market': 'player_points',
          'market_label': 'Puntos',
          'player': 123,
          'player_id': 'p1',
          'line': 20.5,
        },
        _row,
      ]),
    );
    expect(events, hasLength(1));
    final markets = events.single.markets;
    expect(markets, hasLength(2));
    expect(markets.where((m) => m.player != null), isEmpty);
  });

  group('NBA v2: todos los mercados del partido (/nba/v1/partido/{id}/mercados)', () {
    final start = DateTime.utc(2026, 11, 5, 0);
    SportEvent game({String score = '110 – 100', String status = 'finished'}) => SportEvent(
      id: '11330',
      sport: SportKind.nba,
      home: 'Detroit Pistons',
      away: 'Philadelphia 76ers',
      league: 'NBA',
      start: start,
      status: status,
      seal: 'h',
      sealedAt: start,
      markets: const [],
      score: score,
    );
    Map<String, dynamic> row(
      String id,
      String market,
      String side,
      double p, {
      double? line,
      String? team,
      String? player,
      int? playerId,
      double? price = 1.9,
      String? book = 'fanduel',
      String? outcome,
      String sealed = '2026-11-04T23:00:00+00:00',
    }) => {
      'id': id,
      'market': market,
      'side': side,
      'team': team ?? 'Detroit Pistons',
      'line': line,
      'probability': p,
      'player': player,
      'player_id': playerId,
      'sealed_at': sealed,
      'price': price,
      'book': book,
      'odds_at': '2026-11-04T21:07:32+00:00',
      'outcome': outcome,
    };

    test('queda el lado de mayor probabilidad por línea, dentro de la banda, con cuota y casa', () {
      final rows = nbaGameMarkets({
        'partido_id': 11330,
        'markets': [
          row('w-l', 'winner', 'local', .55, team: 'Detroit Pistons', outcome: 'win'),
          row('w-v', 'winner', 'visit', .45, team: 'Philadelphia 76ers', outcome: 'loss'),
          row('t-o', 'game_total', 'over', .35, line: 220.5),
          row('t-u', 'game_total', 'under', .65, line: 220.5, outcome: 'win'),
          row('far', 'game_total', 'over', .99, line: 150.5),
          row('p-o', 'player_threes', 'over', .72, line: 1.5, player: 'Daniss Jenkins', playerId: 212),
          row('h-l', 'handicap', 'local', .40, line: -3.5, outcome: 'loss'),
          row('h-v', 'handicap', 'visit', .60, line: 3.5, team: 'Philadelphia 76ers', outcome: 'win'),
        ],
      }, game());
      final byId = {for (final m in rows) m.id: m};
      // Ganador: siempre el lado favorito, aunque no llegue al 60 %.
      expect(byId['w-l']!.probability, .55);
      expect(byId.containsKey('w-v'), isFalse);
      // Total: el «menos de» (65 %) y no el «más de»; el 99 % queda fuera de la banda.
      expect(byId['t-u']!.side, 'under');
      expect(byId.containsKey('t-o'), isFalse);
      expect(byId.containsKey('far'), isFalse);
      // Hándicap: -3,5 local y +3,5 visitante son la misma línea; gana el visitante (60 %).
      expect(byId['h-v']!.team, 'Philadelphia 76ers');
      expect(byId.containsKey('h-l'), isFalse);
      final jenkins = byId['p-o']!;
      expect(jenkins.player, 'Daniss Jenkins');
      expect(jenkins.price, 1.9);
      expect(jenkins.book, 'fanduel');
      expect(jenkins.quotedAt, DateTime.utc(2026, 11, 4, 21, 7, 32));
      expect(jenkins.eligible, isTrue);
    });

    test('resultado: el del servidor, o se calcula del marcador en total y hándicap', () {
      final rows = nbaGameMarkets({
        'partido_id': 11330,
        'markets': [
          row('t-u', 'game_total', 'under', .70, line: 220.5), // 210 puntos: gana
          row('t-o', 'game_total', 'over', .70, line: 200.5), // 210: gana
          row('h', 'handicap', 'local', .70, line: -9.5), // gana por 10: gana
          row('h2', 'handicap', 'local', .70, line: -10.0), // empata el hándicap: push
          row('tp', 'team_points', 'over', .70, line: 115.5, team: 'Philadelphia 76ers'), // 100: pierde
          row('s', 'player_points', 'over', .70, line: 10.5, player: 'A', playerId: 1, outcome: 'win'),
        ],
      }, game());
      final by = {for (final m in rows) m.id: m.outcome};
      expect(by, {
        't-u': 'win',
        't-o': 'win',
        'h': 'win',
        'h2': 'push',
        'tp': 'loss',
        's': 'win',
      });
    });

    test('un sello posterior al inicio no es pronóstico previo ni resultado', () {
      final rows = nbaGameMarkets({
        'partido_id': 11330,
        'markets': [
          row('late', 'game_total', 'over', .70, line: 200.5, sealed: '2026-11-05T01:00:00+00:00'),
        ],
      }, game());
      expect(rows.single.eligible, isFalse);
      expect(rows.single.outcome, isNull);
    });

    test('filas mal formadas se descartan; otro partido o formato lanza', () {
      final rows = nbaGameMarkets({
        'partido_id': 11330,
        'markets': [
          row('sin-linea', 'game_total', 'over', .70),
          row('lado-malo', 'game_total', 'sideways', .70, line: 200.5),
          row('prob-nan', 'game_total', 'over', double.nan, line: 200.5),
          row('jugador-sin-id', 'player_points', 'over', .70, line: 10.5, player: 'A'),
          row('mercado-raro', 'player_blocks', 'over', .70, line: 1.5, player: 'A', playerId: 1),
          row('ok', 'game_total', 'over', .70, line: 200.5, price: null, book: null),
        ],
      }, game());
      expect(rows.map((m) => m.id), ['ok']);
      expect(rows.single.price, isNull); // sin cuota: nunca se inventa
      expect(() => nbaGameMarkets({'partido_id': 1, 'markets': []}, game()), throwsFormatException);
      expect(() => nbaGameMarkets({'partido_id': 11330}, game()), throwsFormatException);
    });

    test('el destacado del servidor se conserva aunque pase del 95 %', () {
      final rows = nbaGameMarkets({
        'partido_id': 11330,
        'destacado': {'id': 'top'},
        'markets': [row('top', 'game_total', 'over', .97, line: 150.5)],
      }, game());
      expect(rows.single.id, 'top');
    });

    test('quoteFor usa la cuota y casa del propio mercado, sin overlay', () {
      final m = nbaGameMarkets({
        'partido_id': 11330,
        'markets': [row('x', 'game_total', 'over', .70, line: 200.5, book: 'draftkings')],
      }, game()).single;
      final q = quoteFor(game(), m, QuotesOverlay.empty)!;
      expect(q.price, 1.9);
      expect(q.book, 'DraftKings');
    });

    test('enrichNbaFeed suma los mercados a los partidos con pronóstico y tolera fallos', () async {
      final base = SportFeed(
        ready: true,
        events: [
          game().withMarkets([
            SportMarket(
              id: 'winner-11330',
              label: 'Ganador del partido',
              selection: 'Detroit Pistons',
              probability: .7,
              sealedAt: start.subtract(const Duration(hours: 1)),
              eligible: true,
              market: 'winner',
            ),
          ]),
          SportEvent(
            id: '999',
            sport: SportKind.nba,
            home: 'A',
            away: 'B',
            league: 'NBA',
            start: start,
            status: 'scheduled',
            seal: '',
            sealedAt: start,
            markets: const [],
          ),
        ],
      );
      final api = _Api({
        '/nba/v1/partido/11330/mercados': () => {
          'partido_id': 11330,
          'markets': [row('t', 'game_total', 'over', .70, line: 200.5)],
        },
      });
      final updates = <SportFeed>[];
      await enrichNbaFeed(api, base, onUpdate: updates.add, current: () => true);
      // El partido sin pronóstico no se pide.
      expect(api.calls, ['/nba/v1/partido/11330/mercados']);
      expect(updates.last.events.first.markets.single.id, 't');
      expect(updates.last.events.last.markets, isEmpty);

      // Si el feed base ya no es el vigente, no se publica nada.
      final stale = <SportFeed>[];
      await enrichNbaFeed(api, base, onUpdate: stale.add, current: () => false);
      expect(stale, isEmpty);

      // Un partido que falla conserva su ganador.
      final failing = _Api({});
      final kept = <SportFeed>[];
      await enrichNbaFeed(failing, base, onUpdate: kept.add, current: () => true);
      expect(kept.isEmpty || kept.last.events.first.markets.single.id == 'winner-11330', isTrue);
    });
  });
}
