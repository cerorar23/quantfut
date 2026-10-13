import 'dart:math' as math;

import 'live_api.dart';

/// Un reto sigue vivo en una de dos fases: con un escalón esperando resultado, o a la
/// espera de que se elija el siguiente.
enum LadderPhase { inPlay, toPick }

/// Avance de un reto del Reto Escalera, calculado solo con lo que entrega el servidor.
class LadderProgress {
  const LadderProgress({
    required this.goal,
    required this.won,
    required this.phase,
    required this.chance,
    required this.multiplier,
  });

  /// Probabilidad que se supone a un escalón cuando no hay una media fiable: lo medido
  /// para cuotas de 1,25 a 1,40 (72,6 %), ver `publish/escalera.py`.
  static const fallbackStepProbability = .73;

  /// Con menos escalones liquidados que esto la media del servidor no es fiable.
  static const minSampleForAverage = 5;

  final int goal;
  final int won;
  final LadderPhase phase;

  /// Probabilidad estimada (0–1) de completar el reto desde aquí; `null` si no se puede.
  final double? chance;

  /// Valor del reto frente a lo invertido (saldo + lo retirado) / stake; `null` sin stake.
  final double? multiplier;

  int get remaining => math.max(0, goal - won);
  double get fraction => goal <= 0 ? 0 : (won / goal).clamp(0, 1).toDouble();

  /// Media de probabilidad de los escalones ya liquidados (0–1), si hay muestra suficiente.
  static double? averageProbability(JsonMap stats) {
    final n = stats['n'];
    final mean = stats['prob_media'];
    if (n is! num || n < minSampleForAverage || mean is! num || !mean.isFinite) {
      return null;
    }
    return (mean / 100).clamp(0, 1).toDouble();
  }

  static double? _number(dynamic value) =>
      value is num ? value.toDouble() : double.tryParse('$value');

  /// Valor del reto como múltiplo de su stake. En un reto fallido queda lo ya retirado.
  static double? multiplierOf(JsonMap challenge) {
    final stake = _number(challenge['stake_inicial']);
    if (stake == null || stake <= 0) return null;
    final value =
        (_number(challenge['saldo']) ?? 0) + (_number(challenge['retirado']) ?? 0);
    return value / stake;
  }

  factory LadderProgress.of(JsonMap challenge, {double? averageProbability}) {
    final goal = (challenge['pasos_objetivo'] as num?)?.toInt() ?? 0;
    final won = (challenge['ganados'] as num?)?.toInt() ?? 0;
    final phase = challenge['estado'] == 'esperando'
        ? LadderPhase.inPlay
        : LadderPhase.toPick;
    final step = averageProbability ?? fallbackStepProbability;
    final remaining = math.max(0, goal - won);
    double? chance;
    if (goal > 0) {
      if (remaining == 0) {
        chance = 1;
      } else if (phase == LadderPhase.inPlay) {
        // El escalón en juego aporta su propia probabilidad si es visible; si no, la media.
        final pending = jsonRows(challenge['pasos'])
            .where((p) => p['outcome'] == null && p['prob'] is num)
            .map((p) => (p['prob'] as num).toDouble())
            .firstOrNull;
        chance = (pending ?? step) * math.pow(step, remaining - 1);
      } else {
        chance = math.pow(step, remaining).toDouble();
      }
    }
    return LadderProgress(
      goal: goal,
      won: won,
      phase: phase,
      chance: chance,
      multiplier: multiplierOf(challenge),
    );
  }
}

/// Primero los retos con un escalón en juego, luego los más avanzados; a igualdad, por número.
List<JsonMap> sortLadder(List<JsonMap> challenges) {
  final sorted = [...challenges];
  sorted.sort((a, b) {
    final pa = LadderProgress.of(a), pb = LadderProgress.of(b);
    final phase = pa.phase.index.compareTo(pb.phase.index);
    if (phase != 0) return phase;
    final progress = pb.fraction.compareTo(pa.fraction);
    if (progress != 0) return progress;
    return ((a['reto_id'] as num?) ?? 0).compareTo((b['reto_id'] as num?) ?? 0);
  });
  return sorted;
}
