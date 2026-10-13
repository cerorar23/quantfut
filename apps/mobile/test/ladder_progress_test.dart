// Avance, probabilidad estimada y orden de los retos del Reto Escalera.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/ladder_progress.dart';

Map<String, dynamic> challenge(
  int id, {
  required int goal,
  required int won,
  required String estado,
  String saldo = '10.00',
  String retirado = '0.00',
  List<Map<String, dynamic>> pasos = const [],
}) => {
  'reto_id': id,
  'pasos_objetivo': goal,
  'ganados': won,
  'estado': estado,
  'stake_inicial': '10.00',
  'saldo': saldo,
  'retirado': retirado,
  'pasos': pasos,
};

void main() {
  const q = .791; // media real del servidor: 79,1 %

  test('la media del servidor solo vale con muestra suficiente', () {
    expect(
      LadderProgress.averageProbability({'n': 9, 'prob_media': 79.1}),
      closeTo(q, 1e-9),
    );
    expect(LadderProgress.averageProbability({'n': 4, 'prob_media': 90.0}), isNull);
    expect(LadderProgress.averageProbability({'n': 0, 'prob_media': null}), isNull);
    expect(LadderProgress.averageProbability({}), isNull);
  });

  test('en juego: la probabilidad del escalón visible por la media de los que faltan', () {
    final p = LadderProgress.of(
      challenge(
        3,
        goal: 4,
        won: 2,
        estado: 'esperando',
        saldo: '15.63',
        pasos: [
          {'outcome': 'win', 'prob': .8},
          {'outcome': 'win', 'prob': .78},
          {'outcome': null, 'prob': .76},
        ],
      ),
      averageProbability: q,
    );
    expect(p.phase, LadderPhase.inPlay);
    expect(p.remaining, 2);
    expect(p.fraction, .5);
    expect(p.chance, closeTo(.76 * q, 1e-9));
    expect(p.multiplier, closeTo(1.563, 1e-9));
  });

  test('en juego sin escalón visible (candado) usa la media también para ese', () {
    final p = LadderProgress.of(
      challenge(3, goal: 4, won: 2, estado: 'esperando'),
      averageProbability: q,
    );
    expect(p.chance, closeTo(q * q, 1e-9));
  });

  test('por elegir: la media elevada a los escalones que faltan', () {
    final one = LadderProgress.of(
      challenge(1, goal: 3, won: 2, estado: 'en_curso'),
      averageProbability: q,
    );
    expect(one.phase, LadderPhase.toPick);
    expect(one.chance, closeTo(q, 1e-9));
    final three = LadderProgress.of(
      challenge(2, goal: 6, won: 3, estado: 'en_curso'),
      averageProbability: q,
    );
    expect(three.chance, closeTo(q * q * q, 1e-9));
    expect(three.fraction, .5);
  });

  test('sin media fiable se usa la probabilidad medida del 73 %', () {
    final p = LadderProgress.of(challenge(1, goal: 3, won: 2, estado: 'en_curso'));
    expect(p.chance, closeTo(LadderProgress.fallbackStepProbability, 1e-9));
  });

  test('el multiplicador cuenta lo ya retirado y un reto fallido queda en lo retirado', () {
    expect(
      LadderProgress.multiplierOf(
        challenge(1, goal: 3, won: 2, estado: 'en_curso', saldo: '5.00', retirado: '10.00'),
      ),
      1.5,
    );
    expect(
      LadderProgress.multiplierOf(
        challenge(1, goal: 3, won: 1, estado: 'fallido', saldo: '0.00'),
      ),
      0,
    );
    expect(LadderProgress.multiplierOf({'stake_inicial': '0.00'}), isNull);
  });

  test('orden: primero el que tiene un escalón en juego, luego el más avanzado', () {
    final sorted = sortLadder([
      challenge(1, goal: 3, won: 2, estado: 'en_curso'),
      challenge(2, goal: 6, won: 3, estado: 'en_curso'),
      challenge(3, goal: 4, won: 2, estado: 'esperando'),
      challenge(4, goal: 5, won: 2, estado: 'en_curso'),
    ]);
    expect(sorted.map((c) => c['reto_id']), [3, 1, 2, 4]);
  });
}
