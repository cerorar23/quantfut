// Un partido muestra UNA sola tarjeta destacada: entre los de cuota 1.40 o más, la de
// mayor probabilidad; si empatan, la de cuota más alta.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_forecast.dart';

Map<String, dynamic> pick(String market, double? prob, [double? price]) => {
  'market': market,
  'prob': prob,
  'ref_price': price,
};

void main() {
  test('gana la mayor probabilidad entre las de cuota 1.40 o más', () {
    final best = featuredPick([
      pick('totals', .70, 1.90),
      pick('team_goals', .78, 1.45),
      pick('corners', .66, 2.40),
    ]);
    expect(best?['market'], 'team_goals');
  });

  test('descarta la de mayor probabilidad si su cuota es menor de 1.40', () {
    final best = featuredPick([
      pick('handicap', .93, 1.08),
      pick('double_chance', .88, 1.39),
      pick('totals', .76, 1.42),
      pick('btts', .74, 1.60),
    ]);
    expect(best?['market'], 'totals');
  });

  test('sin tope de probabilidad: 93 % con cuota 1.40 es válido', () {
    final best = featuredPick([pick('a', .93, 1.40), pick('b', .80, 1.70)]);
    expect(best?['market'], 'a');
  });

  test('si empatan en probabilidad, gana la cuota más alta', () {
    final best = featuredPick([
      pick('a', .75, 1.40),
      pick('b', .75, 1.55),
      pick('c', .75, 1.45),
    ]);
    expect(best?['market'], 'b');
  });

  test('los que no traen probabilidad o cuota no compiten', () {
    final best = featuredPick([
      pick('a', null, 1.50),
      pick('b', .80),
      pick('c', .74, 1.40),
    ]);
    expect(best?['market'], 'c');
  });

  test('límite exacto de cuota', () {
    expect(featuredPick([pick('valid', .80, 1.40)]), isNotNull);
    for (final invalid in [
      pick('a', .80, 1.3999),
      pick('b', double.nan, 1.50),
      pick('c', .80, double.infinity),
      pick('d', .80),
    ]) {
      expect(featuredPick([invalid]), isNull);
    }
  });

  test('acepta price si no existe ref_price y no modifica la lista', () {
    final picks = [
      pick('invalid', .90, 1.12),
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
