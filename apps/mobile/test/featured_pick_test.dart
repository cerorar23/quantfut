// Un partido muestra UNA sola tarjeta destacada: la de mayor probabilidad; si empatan,
// la de cuota más alta.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_forecast.dart';

Map<String, dynamic> pick(String market, double? prob, [double? price]) => {
  'market': market,
  'prob': prob,
  'ref_price': price,
};

void main() {
  test('gana la mayor probabilidad aunque otra tenga mejor cuota', () {
    final best = featuredPick([
      pick('totals', .70, 1.90),
      pick('team_goals', .78, 1.25),
      pick('corners', .66, 2.40),
    ]);
    expect(best?['market'], 'team_goals');
  });

  test('si empatan en probabilidad, gana la cuota más alta', () {
    final best = featuredPick([
      pick('a', .75, 1.30),
      pick('b', .75, 1.45),
      pick('c', .75, 1.20),
    ]);
    expect(best?['market'], 'b');
  });

  test('un empate sin cuota no desplaza al que sí la tiene', () {
    final best = featuredPick([pick('a', .75), pick('b', .75, 1.2)]);
    expect(best?['market'], 'b');
  });

  test('los que no traen probabilidad no compiten', () {
    final best = featuredPick([pick('a', null, 1.3), pick('b', .74, 1.2)]);
    expect(best?['market'], 'b');
  });

  test('sin probabilidad válida no hay destacado', () {
    final best = featuredPick([pick('a', null), pick('b', null)]);
    expect(best, isNull);
  });

  test('excluye la cuota 1.12 aunque tenga 85 por ciento', () {
    final best = featuredPick([
      pick('corners', .85, 1.12),
      pick('goals', .80, 1.40),
      pick('other', .86, 1.50),
    ]);
    expect(best?['market'], 'goals');
  });

  test('incluye extremos exactos de cuota y probabilidad', () {
    for (final prob in [.74, .85]) {
      for (final price in [1.20, 1.60]) {
        expect(featuredPick([pick('valid', prob, price)]), isNotNull);
      }
    }
    for (final invalid in [
      pick('a', .7399, 1.40),
      pick('b', .8501, 1.40),
      pick('c', .80, 1.1999),
      pick('d', .80, 1.6001),
      pick('e', double.nan, 1.40),
      pick('f', .80, double.infinity),
      pick('g', .80),
    ]) {
      expect(featuredPick([invalid]), isNull);
    }
  });

  test('acepta price si no existe ref_price y no modifica la lista', () {
    final picks = [
      pick('invalid', .85, 1.12),
      {'market': 'valid', 'prob': .80, 'price': 1.40},
    ];
    expect(featuredPick(picks)?['market'], 'valid');
    expect(picks.first['market'], 'invalid');
    expect(picks.length, 2);
  });

  test('sin pronósticos no hay tarjeta', () {
    expect(featuredPick([]), isNull);
  });
}
