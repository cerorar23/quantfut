// Un partido muestra UNA sola tarjeta destacada, «probabilidad máxima segura»: entre los de cuota
// publicada >= 1,20 y probabilidad >= 75 %, la de mayor probabilidad; si empatan, la de mayor cuota
// (misma regla que el servidor y la web). La cuota no multiplica nada.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/featured_rule.dart';
import 'package:gobet/product/live_forecast.dart';

Map<String, dynamic> pick(String market, double? prob, [double? price]) => {
  'market': market,
  'prob': prob,
  'ref_price': price,
};

void main() {
  test('gana la mayor probabilidad aunque otra pague más', () {
    final segura = pick('segura', .82, 1.22);
    final rentable = pick('rentable', .81, 1.60);
    for (final orden in [
      [segura, rentable],
      [rentable, segura],
    ]) {
      expect(featuredPick(orden)?['market'], 'segura');
    }
  });

  test('una cuota larga con menos de 75 % no es candidata', () {
    expect(
      featuredPick([
        pick('valor', .70, 1.80),
        pick('seguro', .75, 1.20),
      ])?['market'],
      'seguro',
    );
    expect(featuredPick([pick('valor', .70, 1.80)]), isNull);
    expect(
      featuredPick([pick('loteria', .20, 5.0), pick('segura', .90, 1.10)]),
      isNull,
    );
  });

  test('si empatan en probabilidad, gana la mayor cuota', () {
    final a = pick('a', .80, 1.25), b = pick('b', .80, 1.45);
    expect(featuredPick([a, b])?['market'], 'b');
    expect(featuredPick([b, a])?['market'], 'b');
  });

  test('un empate total conserva el primero de la lista', () {
    expect(
      featuredPick([pick('x', .80, 1.30), pick('y', .80, 1.30)])?['market'],
      'x',
    );
  });

  test('incluye los extremos exactos: cuota 1,20 y probabilidad 75 %', () {
    expect(featuredPick([pick('valid', .75, 1.20)]), isNotNull);
    for (final invalid in [
      pick('a', .7499, 3.0),
      pick('b', .80, 1.1999),
      pick('c', double.nan, 1.40),
      pick('d', .80, double.infinity),
      pick('e', .80),
      pick('f', null, 1.5),
      pick('g', .55, 2.0),
    ]) {
      expect(featuredPick([invalid]), isNull);
    }
  });

  test('los que no traen probabilidad o cuota no compiten', () {
    expect(
      featuredPick([pick('a', null, 1.3), pick('b', .76, 1.2)])?['market'],
      'b',
    );
    expect(featuredPick([pick('a', .80), pick('b', .78, 1.2)])?['market'], 'b');
  });

  test('con cuota del modelo el tope de 1,20 deja la franja 75 %-83,3 %', () {
    final items = [
      for (final p in [.95, .90, .84, .83, .78, .74])
        pick('p$p', p, modelPrice(p)),
    ];
    expect(featuredPick(items)?['market'], 'p0.83');
    expect(featuredPick(items.reversed.toList())?['market'], 'p0.83');
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
