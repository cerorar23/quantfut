// Interpretación de las bajas del proveedor: tipo, motivo, orden y el caso «sin comprobación».
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/alerts_model.dart';

Map<String, dynamic> row(String player, String type, String? reason) => {
  'jugador': player,
  'tipo': type,
  'motivo': reason,
};

void main() {
  group('Absence.of', () {
    test('Missing Fixture es baja confirmada y Questionable es duda', () {
      expect(Absence.of(row('A', 'Missing Fixture', 'Muscle Injury')).kind, AbsenceKind.out);
      expect(Absence.of(row('A', 'Questionable', 'Injury')).kind, AbsenceKind.doubt);
      expect(Absence.of(row('A', 'Missing Fixture', 'Red Card')).kind, AbsenceKind.suspended);
      expect(Absence.of(row('A', 'Suspended', null)).kind, AbsenceKind.suspended);
    });

    test('agrupa el motivo y conserva el texto original cuando no encaja', () {
      AbsenceReason reason(String r) => Absence.of(row('A', 'Missing Fixture', r)).reason;
      expect(reason('Muscle Injury'), AbsenceReason.muscle);
      expect(reason('Hamstring Injury'), AbsenceReason.muscle);
      expect(reason('Knee Injury'), AbsenceReason.knee);
      expect(reason('Ankle Injury'), AbsenceReason.foot);
      expect(reason('Knock'), AbsenceReason.knock);
      expect(reason('Illness'), AbsenceReason.illness);
      expect(reason('Injury'), AbsenceReason.injury);
      expect(reason('Red Card'), AbsenceReason.suspension);
      final other = Absence.of(row('A', 'Missing Fixture', 'Coach decision'));
      expect(other.reason, AbsenceReason.other);
      expect(other.rawReason, 'Coach decision');
      expect(Absence.of(row('A', 'Missing Fixture', null)).reason, AbsenceReason.unknown);
      expect(Absence.of(row('A', 'Missing Fixture', '  ')).reason, AbsenceReason.unknown);
    });
  });

  group('MatchAlerts.fromFicha', () {
    test('sin comprobación (bajas nulo) no es lo mismo que sin bajas', () {
      expect(MatchAlerts.fromFicha({'bajas': null}), isNull);
      expect(MatchAlerts.fromFicha({}), isNull);
      final none = MatchAlerts.fromFicha({
        'bajas': {'comprobada': '2026-10-13T09:00:00+00:00', 'home': [], 'away': []},
      });
      expect(none, isNotNull);
      expect(none!.total, 0);
      expect(none.checked, isNotNull);
    });

    test('quita duplicados, pone las confirmadas antes que las dudas y cuenta', () {
      final alerts = MatchAlerts.fromFicha({
        'bajas': {
          'comprobada': '2026-10-13T09:00:00+00:00',
          'home': [row('A. Sima', 'Missing Fixture', 'Muscle Injury')],
          'away': [
            row('R. Zalazar', 'Questionable', 'Injury'),
            row('N. Santos', 'Missing Fixture', 'Muscle Injury'),
            row('N. Santos', 'Missing Fixture', 'Muscle Injury'),
          ],
        },
      })!;
      expect(alerts.away.map((a) => a.player), ['N. Santos', 'R. Zalazar']);
      expect(alerts.confirmedCount('away'), 1);
      expect(alerts.doubtCount('away'), 1);
      expect(alerts.total, 3);
    });

    test('ventaja es lo del rival y desventaja lo propio', () {
      final alerts = MatchAlerts.fromFicha({
        'bajas': {
          'comprobada': '2026-10-13T09:00:00+00:00',
          'home': [row('A. Sima', 'Missing Fixture', 'Muscle Injury')],
          'away': [row('N. Santos', 'Missing Fixture', 'Muscle Injury')],
        },
      })!;
      expect(alerts.of('home').single.player, 'A. Sima'); // desventaja del local
      expect(alerts.against('home').single.player, 'N. Santos'); // ventaja del local
      expect(alerts.against('away').single.player, 'A. Sima');
    });
  });
}
