// Asistencia diaria: racha real, día de hoy y cuenta atrás, con la misma regla del servidor.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/rewards_progress.dart';

const coins = <num>[30, 35, 35, 40, 40, 45, 50];
final now = DateTime.utc(2026, 10, 13, 18, 30); // faltan 5 h 30 min para las 00:00 UTC

Map<String, dynamic> wallet(String? last, int streak) => {
  'last_attendance': last,
  'streak': streak,
};

void main() {
  test('sin asistencia: nada cobrado y toca el día 1', () {
    final s = AttendanceState.of(wallet(null, 0), coins, now);
    expect(s.claimedToday, isFalse);
    expect(s.streak, 0);
    expect(s.claimedDays, 0);
    expect(s.nextIndex, 0);
    expect(s.nextCoins, 30);
    expect(s.todayIndex, 0);
  });

  test('marcada hoy: el día de hoy queda cobrado y mañana toca el siguiente', () {
    final s = AttendanceState.of(wallet('2026-10-13', 3), coins, now);
    expect(s.claimedToday, isTrue);
    expect(s.streak, 3);
    expect(s.claimedDays, 3);
    expect(s.todayIndex, 2);
    expect(s.nextIndex, 3);
    expect(s.nextCoins, 40);
    expect(s.untilReset, const Duration(hours: 5, minutes: 30));
  });

  test('marcada ayer: la racha sigue viva y hoy toca el día siguiente', () {
    final s = AttendanceState.of(wallet('2026-10-12', 3), coins, now);
    expect(s.claimedToday, isFalse);
    expect(s.streak, 3);
    expect(s.claimedDays, 3);
    expect(s.todayIndex, 3);
    expect(s.nextCoins, 40);
  });

  test('un día perdido rompe la racha aunque el servidor aún guarde el número', () {
    final s = AttendanceState.of(wallet('2026-10-11', 5), coins, now);
    expect(s.streak, 0);
    expect(s.claimedDays, 0);
    expect(s.nextIndex, 0);
    expect(s.nextCoins, 30);
  });

  test('al completar el día 7 el ciclo queda lleno y al día siguiente vuelve a empezar', () {
    final full = AttendanceState.of(wallet('2026-10-13', 7), coins, now);
    expect(full.claimedDays, 7);
    expect(full.todayIndex, 6);
    expect(full.nextIndex, 0);
    final fresh = AttendanceState.of(wallet('2026-10-12', 7), coins, now);
    expect(fresh.claimedDays, 0);
    expect(fresh.nextIndex, 0);
    expect(fresh.nextCoins, 30);
  });

  test('sin lista de monedas no revienta', () {
    final s = AttendanceState.of(wallet('2026-10-13', 2), const [], now);
    expect(s.nextCoins, isNull);
    expect(s.claimedDays, 0);
  });

  test('la cuenta atrás se escribe como reloj', () {
    expect(AttendanceState.clock(const Duration(hours: 5, minutes: 12, seconds: 30)), '05:12:30');
    expect(AttendanceState.clock(const Duration(seconds: -4)), '00:00:00');
  });

  test('avance hacia el desbloqueo', () {
    expect(unlockProgress(60, 100), (fraction: .6, missing: 40));
    expect(unlockProgress(150, 100), (fraction: 1.0, missing: 0));
    expect(unlockProgress(-20, 100), (fraction: 0.0, missing: 100));
    expect(unlockProgress(10, null), (fraction: 0.0, missing: 0));
  });
}
