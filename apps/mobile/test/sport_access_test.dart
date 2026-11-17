// Cupos de gratis por deporte (`acceso.cupos` de `/cliente/v1/config`, menú `/control/cupos`).
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_match_markets.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

final _now = DateTime(2026, 11, 16, 10);

SportMarket _m(String id, double p) => SportMarket(
  id: id,
  label: 'Mercado $id',
  selection: 'Sel $id',
  probability: p,
  sealedAt: DateTime.utc(2026, 11, 1),
  eligible: true,
);

SportEvent _e(String id, int day, Map<String, double> probs, {String featured = 'a'}) => SportEvent(
  id: id,
  sport: kNba,
  home: 'H',
  away: 'A',
  league: 'NBA',
  start: DateTime(2026, 11, day, 20),
  status: 'scheduled',
  seal: 'x',
  sealedAt: DateTime.utc(2026, 11, 1),
  markets: [for (final p in probs.entries) _m(p.key, p.value)],
  serverFeatured: true,
  featuredId: featured,
);

List<String> _ids(SportEvent e) => [for (final m in e.markets) m.id];

void main() {
  orderTests();
  test('con VIP, sin cupo o sin límites no cambia nada', () {
    final list = [_e('1', 16, {'a': .8, 'b': .7})];
    const zero = SportQuota(featuredPerDay: 0, marketsPerMatch: 0);
    for (final (quota, plus) in [(zero, true), (null, false), (const SportQuota(), false)]) {
      final e = applyQuota(list, quota, plus: plus, now: _now).single;
      expect(_ids(e), ['a', 'b']);
      expect(e.vipCount, 0);
      expect(featuredMarket(e)?.id, 'a');
    }
  });

  test('las familias que el cupo deja para VIP se cuentan para pintar filas bloqueadas', () {
    final e = SportEvent(
      id: '9',
      sport: kTennis,
      home: 'H',
      away: 'A',
      league: 'ATP',
      start: DateTime(2026, 11, 16, 20),
      status: 'scheduled',
      seal: 'x',
      sealedAt: DateTime.utc(2026, 11, 1),
      markets: [
        SportMarket(id: 'winner', label: 'G', selection: 'H', probability: .6, sealedAt: DateTime.utc(2026, 11, 1), eligible: true, family: 'winner'),
        SportMarket(id: 'games_total-2', label: 'J', selection: 'Más', probability: .7, sealedAt: DateTime.utc(2026, 11, 1), eligible: true, family: 'games_total'),
        SportMarket(id: 'games_total-3', label: 'J', selection: 'Más', probability: .5, sealedAt: DateTime.utc(2026, 11, 1), eligible: true, family: 'games_total'),
        SportMarket(id: 'set_winner-1', label: 'S', selection: 'H', probability: .4, sealedAt: DateTime.utc(2026, 11, 1), eligible: true, family: 'set_winner'),
      ],
      serverFeatured: true,
      featuredId: 'winner',
    );
    final out = applyQuota([e], const SportQuota(marketsPerMatch: 1), plus: false, now: _now).single;
    expect(_ids(out), ['winner']);
    expect(out.vipCount, 3);
    expect(out.vipFamilies, {'games_total': 2, 'set_winner': 1});
    final full = applyQuota([e], null, plus: false, now: _now).single;
    expect(full.vipFamilies, isEmpty);
  });

  test('el destacado va abierto solo en los N partidos del día con mayor probabilidad', () {
    final list = [_e('1', 16, {'a': .80}), _e('2', 16, {'a': .90}), _e('3', 16, {'a': .85}), _e('4', 17, {'a': .76})];
    final out = applyQuota(list, const SportQuota(featuredPerDay: 2), plus: false, now: _now);
    expect([for (final e in out) e.featuredVip], [true, false, false, false]);
    expect(featuredMarket(out[0]), isNull);
    expect(out[0].markets, isEmpty);
    expect(out[0].vipCount, 1);
  });

  test('por partido se abren los M de mayor probabilidad; el destacado abierto cuenta como uno', () {
    final e = applyQuota(
      [_e('1', 16, {'a': .80, 'b': .95, 'c': .60, 'd': .90})],
      const SportQuota(marketsPerMatch: 2),
      plus: false,
      now: _now,
    ).single;
    expect(_ids(e), ['a', 'b']);
    expect(e.vipCount, 2);
    expect(e.featuredVip, isFalse);
    final locked = applyQuota(
      [_e('1', 16, {'a': .80, 'b': .95})],
      const SportQuota(featuredPerDay: 0, marketsPerMatch: 1),
      plus: false,
      now: _now,
    ).single;
    expect(_ids(locked), ['b']);
    expect(locked.featuredVip, isTrue);
  });

  test('un día ya pasado se ve entero y withMarkets conserva el acceso del partido', () {
    const none = SportQuota(featuredPerDay: 0, marketsPerMatch: 0);
    final out = applyQuota([_e('1', 15, {'a': .8, 'b': .7}), _e('2', 16, {'a': .8, 'b': .7})], none, plus: false, now: _now);
    expect(out[0].markets, hasLength(2));
    expect(out[0].vipCount, 0);
    expect(out[1].markets, isEmpty);
    final detail = out[1].withMarkets([_m('a', .8), _m('z', .99), _m('y', .5)], featured: 'a', serverFeaturedField: true);
    expect(detail.markets, isEmpty);
    expect(detail.vipCount, 3);
    expect(detail.featuredVip, isTrue);
    expect(applyAccess(detail, null).vipCount, 0);
  });

  test('el catálogo lee acceso.cupos y un deporte ausente va sin límite', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [
        {
          'id': 'nba',
          'orden': 1,
          'estado': 'on',
          'nombre': {'es': 'NBA'},
          'icono': 'nba',
          'color': '#ff7a00',
          'secciones': ['high'],
          'familias': [],
        },
      ],
      'acceso': {
        'cupos': {
          'nba': {'destacados_gratis_dia': 3, 'mercados_gratis_partido': 0},
          'tenis': {},
          'raro': {'destacados_gratis_dia': -1, 'mercados_gratis_partido': 'x'},
        },
      },
    });
    expect(catalog, isNotNull);
    expect(catalog!.quotas['nba']!.featuredPerDay, 3);
    expect(catalog.quotas['nba']!.marketsPerMatch, 0);
    expect(catalog.quotas['tenis']!.unlimited, isTrue);
    expect(catalog.quotas['raro']!.unlimited, isTrue);
    expect(catalog.quotas['futbol'], isNull);
    expect(SportCatalog.builtIn.quotas, isEmpty);
  });
}

void orderTests() {
  test('mercados de un partido jugado: acertados por cuota, luego pendientes, al final los fallados', () {
    final rows = <Map<String, dynamic>>[
      {'id': 'perdida', 'resultado': 'loss', 'cuota': 3.0, 'prob': .9},
      {'id': 'pendiente', 'cuota': 2.0, 'prob': .8},
      {'id': 'gana_baja', 'resultado': 'win', 'cuota': 1.3, 'prob': .8},
      {'id': 'gana_alta', 'resultado': 'win', 'cuota': 2.4, 'prob': .6},
    ];
    expect([for (final r in orderSettledRows(rows)) r['id']], ['gana_alta', 'gana_baja', 'pendiente', 'perdida']);
    final open = <Map<String, dynamic>>[{'id': 'a', 'cuota': 1.2, 'prob': .7}, {'id': 'b', 'cuota': 2.0, 'prob': .9}];
    expect(orderSettledRows(open), open);   // sin resultados liquidados: orden del servidor
  });
}
