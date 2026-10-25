// Textos de pronósticos en el idioma del usuario (auditoría 2026-10-25): goles de
// equipo con su línea, tarjetas y patas del Parley; casas con su nombre comercial y
// el «esperando resultado» de un partido que ya debió terminar.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/l10n/pick_labels.dart';
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
}
