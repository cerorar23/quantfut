// Textos de pronósticos en el idioma del usuario (auditoría 2026-10-25): goles de
// equipo con su línea, tarjetas y patas del Parley; casas con su nombre comercial y
// el «esperando resultado» de un partido que ya debió terminar.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/l10n/pick_labels.dart';
import 'package:gobet/product/alerts_model.dart';
import 'package:gobet/product/live_api.dart';

void main() {
  tearDown(() => AppLocale.instance.reset());

  test('«marca» solo es más de 0,5; otra línea o el menos se dicen enteros', () async {
    await AppLocale.instance.select('es');
    JsonMap tt(String side, String sel, double line) => {
      'market': 'team_totals_$side',
      'selection': sel,
      'line': line,
      'local': 'Udinese',
      'visitante': 'AC Milan',
      'texto': 'Marca X',
    };
    expect(pickText(tt('away', 'over', .5)), 'Marca AC Milan');
    expect(pickText(tt('home', 'over', 1.5)), 'Más de 1,5 goles de Udinese');
    expect(pickText(tt('away', 'under', 1.5)), 'Menos de 1,5 goles de AC Milan');
    await AppLocale.instance.select('en');
    expect(pickText(tt('home', 'over', 1.5)), 'Over 1.5 Udinese goals');
  });

  test('las tarjetas del Parley se traducen y no salen en español', () async {
    await AppLocale.instance.select('en');
    final leg = {
      'market': 'cards',
      'selection': 'under',
      'line': 4.5,
      'texto': 'Menos de 4,5 tarjetas',
    };
    expect(pickText(leg), 'Under 4.5 cards');
    // Sin selección ni línea (API antigua) se conserva el texto del servidor.
    expect(pickText({'market': 'cards', 'texto': 'Menos de 4,5 tarjetas'}),
        'Menos de 4,5 tarjetas');
  });

  test('córners de un equipo en la lista de mercados', () async {
    await AppLocale.instance.select('es');
    final row = {
      'market': 'corners_home',
      'selection': 'under',
      'line': 7.5,
      'seleccion': 'x',
    };
    expect(rowSelection(row, 'Rennes', 'Strasbourg'), 'Menos de 7,5 córners de Rennes');
  });

  test('las casas salen con su nombre comercial', () {
    expect(bookName('betonlineag'), 'BetOnline');
    expect(bookName('bovada'), 'Bovada');
    expect(bookName('Pinnacle'), 'Pinnacle');
    expect(bookName('casa_nueva'), 'casa_nueva');
  });

  test('pasado el tiempo de juego, el partido espera resultado', () {
    final ko = DateTime.utc(2026, 10, 25, 20);
    expect(awaitingResult(ko.toIso8601String(), ko.add(const Duration(minutes: 100))), isFalse);
    expect(awaitingResult(ko.toIso8601String(), ko.add(matchSpan)), isTrue);
    expect(awaitingResult(null), isFalse);
  });

  group('interpretReturnDate y motivos de bajas', () {
    test('interpreta fechas de regreso en inglés (Early/Mid/Late) y con año futuro', () async {
      await AppLocale.instance.select('es');
      expect(interpretReturnDate('Early December 2026'), 'principios de dic.');
      expect(interpretReturnDate('Mid November 2026'), 'mediados de nov.');
      expect(interpretReturnDate('Late November 2026'), 'finales de nov.');
      expect(interpretReturnDate('Early May 2027'), 'principios de may. 2027');
      expect(interpretReturnDate('Texto desconocido 123'), 'Texto desconocido 123');

      await AppLocale.instance.select('en');
      expect(interpretReturnDate('Early December 2026'), 'early Dec');
      expect(interpretReturnDate('Mid November 2026'), 'mid-Nov');
      expect(interpretReturnDate('Late November 2026'), 'late Nov');
      expect(interpretReturnDate('Early May 2027'), 'early May 2027');
    });

    test('absenceReturnText formatea selección, regreso y vuelta a entrenamientos', () async {
      await AppLocale.instance.select('es');
      final valjent = Absence.of({
        'jugador': 'Martin Valjent',
        'tipo': 'internationalDuty',
        'motivo': 'Mid November 2026',
      });
      expect(absenceReturnText(valjent), 'Con su selección · vuelve a mediados de nov.');

      final morlanes = Absence.of({
        'jugador': 'Manu Morlanes',
        'tipo': 'injury',
        'motivo': 'Early December 2026',
      });
      expect(absenceReturnText(morlanes), 'Vuelve a principios de dic.');

      final medina = Absence.of({
        'jugador': 'Kevin Medina',
        'tipo': 'injury',
        'motivo': 'Back in training',
      });
      expect(absenceReturnText(medina), 'Ya entrena con el grupo');

      final sima = Absence.of({
        'jugador': 'A. Sima',
        'tipo': 'Missing Fixture',
        'motivo': 'Muscle Injury',
      });
      expect(absenceReturnText(sima), isNull);
    });

    test('insignias de baja: LESIÓN, SELECCIÓN, SANCIÓN, DUDA, VUELVE', () async {
      await AppLocale.instance.select('es');
      final l10n = AppLocale.instance.l10n;

      final injury = Absence.of({'jugador': 'A', 'tipo': 'injury', 'motivo': 'Early December 2026'});
      expect(absenceBadgeLabel(injury, l10n), 'LESIÓN');

      final duty = Absence.of({'jugador': 'B', 'tipo': 'internationalDuty', 'motivo': 'Mid November 2026'});
      expect(absenceBadgeLabel(duty, l10n), 'SELECCIÓN');

      final susp = Absence.of({'jugador': 'C', 'tipo': 'suspension', 'motivo': 'Red Card'});
      expect(absenceBadgeLabel(susp, l10n), 'SANCIÓN');

      final doubt = Absence.of({'jugador': 'D', 'tipo': 'injury', 'motivo': 'Doubtful'});
      expect(absenceBadgeLabel(doubt, l10n), 'DUDA');

      final returns = Absence.of({'jugador': 'E', 'tipo': 'injury', 'motivo': 'Back in training'});
      expect(absenceBadgeLabel(returns, l10n), 'VUELVE');
    });
  });
}
