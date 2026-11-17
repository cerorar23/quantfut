// Orden de los mercados calificados: igual en todos los deportes (acertados por cuota, luego el resto, al final los fallados).
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/sport_markets.dart';
import 'package:gobet/product/sports_feed.dart';

SportMarket _m(String id, double p, {String? outcome, double? price}) => SportMarket(
  id: id,
  label: id,
  selection: id,
  probability: p,
  sealedAt: DateTime.utc(2026, 11, 1),
  eligible: true,
  outcome: outcome,
  price: price,
);

List<String> _ids(List<SportMarket> l) => [for (final m in l) m.id];
double? _price(SportMarket m) => m.price;

void main() {
  test('sin resultados calificados la lista queda como llegó', () {
    final list = [_m('a', .6), _m('b', .9)];
    expect(_ids(orderSettledMarkets(list, price: _price)), ['a', 'b']);
  });

  test('acertados por cuota de mayor a menor, luego el resto (también por cuota), al final los fallados', () {
    final list = [
      _m('falla-alta', .95, outcome: 'loss', price: 3.0),
      _m('pendiente', .7),
      _m('gana-baja', .95, outcome: 'win', price: 1.13),
      _m('devuelto', .6, outcome: 'push', price: 2.0),
      _m('gana-alta', .61, outcome: 'win', price: 2.30),
      _m('falla-baja', .66, outcome: 'loss', price: 1.66),
    ];
    expect(_ids(orderSettledMarkets(list, price: _price)), [
      'gana-alta',
      'gana-baja',
      'devuelto',
      'pendiente',
      'falla-alta',
      'falla-baja',
    ]);
  });

  test('un acertado sin cuota va después de los que la tienen; el empate se decide por probabilidad', () {
    final list = [
      _m('sin-cuota', .9, outcome: 'win'),
      _m('con-cuota', .6, outcome: 'win', price: 1.2),
      _m('empate-baja', .6, outcome: 'win', price: 1.2),
      _m('empate-alta', .8, outcome: 'win', price: 1.2),
    ];
    expect(_ids(orderSettledMarkets(list, price: _price)), ['empate-alta', 'con-cuota', 'empate-baja', 'sin-cuota']);
  });
}
