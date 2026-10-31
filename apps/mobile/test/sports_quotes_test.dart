import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';
import 'package:gobet/product/sports_quotes.dart';

class _Api extends QuantFutApi {
  _Api(this.answer);
  final dynamic Function(String path) answer;
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async => answer(path);
}

JsonMap _fx(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as JsonMap;

List<SportEvent> _nba() => nbaEvents(_fx('nba_feed.json'));
List<SportEvent> _tennis() => tennisEvents(_fx('tennis_feed.json'));
SportEvent _ev(List<SportEvent> l, String id) => l.firstWhere((e) => e.id == id);
SportMarket _mk(SportEvent e, String market) =>
    e.markets.firstWhere((m) => m.market == market);

QuotesOverlay _nbaOverlay() =>
    QuotesOverlay.fromJson(SportKind.nba, _fx('quotes_nba.json'));

SportMarket _teamPoints(SportMarket base, String teamId) => SportMarket(
  id: 'tp-$teamId',
  label: 'x',
  selection: 'Atlanta Hawks',
  probability: .6,
  sealedAt: base.sealedAt,
  eligible: true,
  market: 'team_points',
  rowPlayerId: teamId,
  line: 110.0,
);

void main() {
  test('lineKey quita el .0 final como el servidor', () {
    expect(lineKey(221.0), '221');
    expect(lineKey(24.5), '24.5');
    expect(lineKey(null), '');
  });

  group('fromJson tolerante', () {
    test('nulo, listas y tipos raros dan empty', () {
      final malos = <Object?>[
        null,
        <Object>[],
        'x',
        3,
        true,
        {'state': 'ok'},
        {'state': 'ok', 'events': []},
        {'state': 'unavailable', 'events': {'a': {}}},
      ];
      for (final bad in malos) {
        expect(QuotesOverlay.fromJson(SportKind.nba, bad).isEmpty, isTrue, reason: '$bad');
        expect(QuotesOverlay.fromJson(SportKind.tennis, bad).isEmpty, isTrue, reason: '$bad');
      }
    });

    test('precio no valido, sin casa o sin fecha se descarta', () {
      Object? one(Map<String, Object?> q) => {
        'state': 'ok',
        'events': {
          '12173711': {'winner': q},
        },
      };
      const ok = <String, Object?>{
        'price': 1.5,
        'book': 'x',
        'as_of': '2026-10-23T10:00:00+00:00',
        'books': 2,
      };
      expect(QuotesOverlay.fromJson(SportKind.tennis, one(ok)).isEmpty, isFalse);
      final malos = <Map<String, Object?>>[
        {...ok, 'price': 1.0},
        {...ok, 'price': 0.5},
        {...ok, 'price': double.nan},
        {...ok, 'price': double.infinity},
        {...ok, 'price': true},
        {...ok, 'price': '1.5'},
        {...ok, 'book': ''},
        {...ok, 'book': 3},
        {...ok}..remove('book'),
        {...ok, 'as_of': 'ayer'},
        {...ok}..remove('as_of'),
      ];
      for (final bad in malos) {
        expect(QuotesOverlay.fromJson(SportKind.tennis, one(bad)).isEmpty, isTrue, reason: '$bad');
      }
    });
  });

  group('NBA', () {
    final events = _nba();
    final overlay = _nbaOverlay();
    final e144 = _ev(events, '0022600144');

    test('ganador: el precio sale del lado elegido', () {
      final m = _mk(e144, 'winner');
      // p(local) < .5 en el feed: la seleccion mostrada es el visitante.
      expect(m.selection, e144.away);
      expect(quoteFor(e144, m, overlay)!.price, 2.35);
      final e145 = _ev(events, '0022600145');
      final m2 = _mk(e145, 'winner');
      expect(m2.selection, e145.home);
      expect(quoteFor(e145, m2, overlay)!.price, 1.5);
    });

    test('Mas de usa el lado over; jugador usa su id crudo', () {
      expect(quoteFor(e144, _mk(e144, 'game_total'), overlay)!.price, 1.91);
      final q = quoteFor(e144, _mk(e144, 'player_assists'), overlay)!;
      expect(q.price, 1.87);
      expect(q.book, 'fanduel');
      expect(q.books, 3);
    });

    test('team_points usa el id del equipo de la fila cruda', () {
      final base = _mk(e144, 'game_total');
      expect(quoteFor(e144, _teamPoints(base, '1610612737'), overlay)!.price, 1.95);
      expect(quoteFor(e144, _teamPoints(base, '1610612740'), overlay), isNull);
    });

    test('cuota posterior al sello de la fila se descarta', () {
      final e145 = _ev(events, '0022600145');
      final m = _mk(e145, 'player_assists');
      expect(DateTime.utc(2026, 10, 29, 23, 55).isAfter(m.sealedAt), isTrue);
      expect(quoteFor(e145, m, overlay), isNull);
    });

    test('si la cohorte no es el seal del evento no hay cuotas', () {
      final other = SportEvent(
        id: e144.id,
        sport: e144.sport,
        home: e144.home,
        away: e144.away,
        league: e144.league,
        start: e144.start,
        status: e144.status,
        seal: 'otra-cohorte',
        sealedAt: e144.sealedAt,
        markets: e144.markets,
      );
      for (final m in other.markets) {
        expect(quoteFor(other, m, overlay), isNull);
      }
    });

    test('overlay vacio o de otro deporte: sin cuota', () {
      expect(quoteFor(e144, _mk(e144, 'winner'), QuotesOverlay.empty), isNull);
      final tenis = QuotesOverlay.fromJson(SportKind.tennis, _fx('quotes_tennis.json'));
      expect(quoteFor(e144, _mk(e144, 'winner'), tenis), isNull);
    });
  });

  group('tenis', () {
    final events = _tennis();
    final overlay = QuotesOverlay.fromJson(SportKind.tennis, _fx('quotes_tennis.json'));
    final e = _ev(events, '12173711');

    test('une por id de mercado', () {
      final w = e.markets.firstWhere((m) => m.id == 'winner');
      expect(quoteFor(e, w, overlay)!.price, 1.21);
      final g = e.markets.firstWhere((m) => m.id == 'games_total-2');
      expect(quoteFor(e, g, overlay)!.price, 1.88);
      final sin = e.markets.firstWhere((m) => m.id == 'tiebreak-1');
      expect(quoteFor(e, sin, overlay), isNull);
    });

    test('cuota recibida tras el sello del evento se descarta', () {
      final tarde = QuotesOverlay.fromJson(SportKind.tennis, {
        'state': 'partial',
        'events': {
          '12173711': {
            'winner': {
              'price': 1.3,
              'book': 'x',
              'as_of': '2026-10-23T11:00:00+00:00',
              'books': 1,
            },
          },
        },
      });
      final w = e.markets.firstWhere((m) => m.id == 'winner');
      expect(quoteFor(e, w, tarde), isNull);
    });
  });

  group('carga', () {
    test('loadQuotes nunca lanza y usa la ruta del deporte', () async {
      final paths = <String>[];
      final ok = await loadQuotes(
        _Api((p) {
          paths.add(p);
          return _fx('quotes_nba.json');
        }),
        SportKind.nba,
      );
      expect(paths, ['/web/deportes/nba/cuotas']);
      expect(ok.isEmpty, isFalse);
      final caido = _Api((p) {
        paths.add(p);
        throw const ApiFailure('caido');
      });
      expect((await loadQuotes(caido, SportKind.tennis)).isEmpty, isTrue);
      expect(paths.last, '/web/deportes/tenis/cuotas');
      expect((await loadQuotes(_Api((_) => 'basura'), SportKind.nba)).isEmpty, isTrue);
      expect((await loadQuotes(_Api((_) => throw 1), SportKind.football)).isEmpty, isTrue);
    });

    test('un overlay fallido no pisa uno bueno', () {
      final good = _nbaOverlay();
      expect(identical(mergeQuotes(good, QuotesOverlay.empty), good), isTrue);
      expect(identical(mergeQuotes(null, QuotesOverlay.empty), QuotesOverlay.empty), isTrue);
      final nuevo = QuotesOverlay.fromJson(SportKind.tennis, _fx('quotes_tennis.json'));
      expect(identical(mergeQuotes(good, nuevo), nuevo), isTrue);
    });

    test('feed bien y endpoint de cuotas caido: los eventos son los mismos', () async {
      final api = _Api((p) {
        if (p == '/nba/api/data') return _fx('nba_feed.json');
        throw const ApiFailure('caido');
      });
      final feed = await loadSport(api, SportKind.nba);
      final q = await loadQuotes(api, SportKind.nba);
      expect(feed.ready, isTrue);
      expect(feed.events.length, _nba().length);
      expect(q.isEmpty, isTrue);
      for (final e in feed.events) {
        for (final m in e.markets) {
          expect(quoteFor(e, m, q), isNull);
        }
      }
    });
  });
}
