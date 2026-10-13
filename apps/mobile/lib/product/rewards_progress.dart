import 'live_api.dart';

/// Estado de la asistencia diaria calculado con la fecha real (UTC), como lo hace el servidor.
///
/// El servidor guarda la última fecha marcada y la racha, pero la racha solo se reinicia al marcar
/// de nuevo: si el usuario falló un día, el número guardado ya no es vigente. Aquí se ve como 0.
class AttendanceState {
  const AttendanceState({
    required this.claimedToday,
    required this.streak,
    required this.claimedDays,
    required this.nextIndex,
    required this.nextCoins,
    required this.untilReset,
  });

  /// La asistencia de hoy (UTC) ya se marcó.
  final bool claimedToday;

  /// Racha vigente: 0 si se rompió.
  final int streak;

  /// Días ya cobrados del ciclo de 7 (los de color verde).
  final int claimedDays;

  /// Índice (0–6) del siguiente día a cobrar: hoy si no se marcó, mañana si ya se marcó.
  final int nextIndex;
  final int? nextCoins;

  /// Tiempo hasta las 00:00 UTC, cuando se puede volver a marcar.
  final Duration untilReset;

  /// Índice del día de hoy en la fila de 7 días: el cobrado hoy, o el que toca cobrar.
  int get todayIndex => claimedToday ? claimedDays - 1 : nextIndex;

  static DateTime? _date(dynamic value) {
    final parsed = DateTime.tryParse('$value');
    return parsed == null ? null : DateTime.utc(parsed.year, parsed.month, parsed.day);
  }

  factory AttendanceState.of(JsonMap wallet, List<num> coins, DateTime now) {
    final utc = now.toUtc();
    final today = DateTime.utc(utc.year, utc.month, utc.day);
    final last = _date(wallet['last_attendance']);
    final claimedToday = last == today;
    final alive = claimedToday || last == today.subtract(const Duration(days: 1));
    final saved = (wallet['streak'] as num?)?.toInt() ?? 0;
    final streak = alive ? saved : 0;
    final cycle = coins.length;
    var claimed = 0;
    var next = 0;
    if (cycle > 0 && streak > 0) {
      claimed = claimedToday ? ((streak - 1) % cycle) + 1 : streak % cycle;
      next = streak % cycle;
    }
    return AttendanceState(
      claimedToday: claimedToday,
      streak: streak,
      claimedDays: claimed,
      nextIndex: next,
      nextCoins: cycle == 0 ? null : coins[next].toInt(),
      untilReset: today.add(const Duration(days: 1)).difference(utc),
    );
  }

  /// `05:12:30` para la cuenta atrás.
  static String clock(Duration d) {
    final total = d.isNegative ? 0 : d.inSeconds;
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(total ~/ 3600)}:${two(total % 3600 ~/ 60)}:${two(total % 60)}';
  }
}

/// Avance hacia el siguiente desbloqueo (0–1) y monedas que faltan.
({double fraction, int missing}) unlockProgress(num balance, num? cost) {
  if (cost == null || cost <= 0) return (fraction: 0, missing: 0);
  final value = balance < 0 ? 0 : balance;
  return (
    fraction: (value / cost).clamp(0, 1).toDouble(),
    missing: (cost - value).clamp(0, cost).toInt(),
  );
}
