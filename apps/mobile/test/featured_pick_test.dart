// Un partido muestra UNA sola tarjeta destacada, elegida por valor esperado: entre los de cuota
// publicada >= 1,20 y probabilidad >= 55 %, la de mayor probabilidad × cuota; si empatan, la de
// mayor probabilidad (misma regla que el servidor y la web).
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/featured_rule.dart';
import 'package:gobet/product/live_forecast.dart';

Map<String, dynamic> pick(String market, double? prob, [double? price]) => {
  'market': market,
  'prob': prob,
  'ref_price': price,
};

void main() {
  test(
    'cuota 1,80 con 70 % gana a cuota 1,20 con 75 % por su valor esperado',
    () {
      final seguro = pick('seguro', .75, 1.20); // 0,90
      final valor = pick('valor', .70, 1.80); // 1,26
      for (final orden in [
        [seguro, valor],
        [valor, seguro],
      ]) {
        expect(featuredPick(orden)?['market'], 'valor');
      }
      expect(featuredScore(.75, 1.20), closeTo(.90, 1e-9));
      expect(featuredScore(.70, 1.80), closeTo(1.26, 1e-9));
    },
  );

  test('si empatan en valor esperado, gana la mayor probabilidad', () {
    final best = featuredPick([
      pick('a', .60, 1.50), // 0,90
      pick('b', .75, 1.20), // 0,90
    ]);
    expect(best?['market'], 'b');
    expect(
      featuredPick([pick('b', .75, 1.20), pick('a', .60, 1.50)])?['market'],
      'b',
    );
  });

  test('un empate total conserva el primero de la lista', () {
    expect(
      featuredPick([pick('x', .60, 1.50), pick('y', .60, 1.50)])?['market'],
      'x',
    );
  });

  test(
    'el ruido de coma flotante no decide empates entre cuotas del modelo',
    () {
      final probs = [.57, .58, .59, .61, .63, .67, .71, .77, .81];
      final items = [for (final p in probs) pick('p$p', p, 1 / p)];
      expect(featuredPick(items)?['market'], 'p0.81');
      expect(featuredPick(items.reversed.toList())?['market'], 'p0.81');
    },
  );

  test('una cuota enorme con poca probabilidad nunca es destacado', () {
    expect(
      featuredPick([pick('loteria', .20, 5.0), pick('segura', .90, 1.10)]),
      isNull,
    );
    final best = featuredPick([pick('baja', .50, 2.50), pick('ok', .60, 1.40)]);
    expect(best?['market'], 'ok'); // 1,25 > 0,84, pero 'baja' no llega al 55 %
  });

  test('incluye los extremos exactos: cuota 1,20 y probabilidad 55 %', () {
    expect(featuredPick([pick('valid', .55, 1.20)]), isNotNull);
    for (final invalid in [
      pick('a', .5499, 3.0),
      pick('b', .60, 1.1999),
      pick('c', double.nan, 1.40),
      pick('d', .80, double.infinity),
      pick('e', .80),
      pick('f', null, 1.5),
    ]) {
      expect(featuredPick([invalid]), isNull);
    }
  });

  test('los que no traen probabilidad o cuota no compiten', () {
    final best = featuredPick([pick('a', null, 1.3), pick('b', .74, 1.2)]);
    expect(best?['market'], 'b');
    expect(featuredPick([pick('a', .75), pick('b', .75, 1.2)])?['market'], 'b');
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
