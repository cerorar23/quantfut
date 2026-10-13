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
    final best = featuredPick([pick('a', null, 3.0), pick('b', .62, 1.1)]);
    expect(best?['market'], 'b');
  });

  test('si ninguno trae probabilidad se muestra el primero', () {
    final best = featuredPick([pick('a', null), pick('b', null)]);
    expect(best?['market'], 'a');
  });

  test('sin pronósticos no hay tarjeta', () {
    expect(featuredPick([]), isNull);
  });
}
