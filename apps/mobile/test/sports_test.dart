import 'dart:ui' show Tristate;
// Deportes, preferencias de orden/ocultos y selector.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/sport_selector.dart';
import 'package:gobet/product/sports.dart';

SportPrefs prefsOn(Map<String, String> store) => SportPrefs(
  read: (key) async => store[key],
  write: (key, value) async => store[key] = value,
);

void main() {
  test('id desconocido o orden corrupto vuelve a fútbol', () async {
    expect(await prefsOn({'sports_order': 'baloncesto,???'}).initial(), kFootball);
    expect(await prefsOn({}).initial(), kFootball);
    expect(sportCatalog.find('nba')?.id, kNba);
    expect(sportCatalog.find(null), isNull);
  });

  test('abre el primer deporte del orden, no el último usado', () async {
    final store = {'sports_last': 'tenis'};
    final prefs = prefsOn(store);
    await prefs.save(
      order: [kNba, kFootball, kTennis],
      hidden: {},
    );
    expect(await prefs.initial(), kNba);
  });

  test('no se pueden ocultar todos', () async {
    final prefs = prefsOn({});
    await prefs.save(
      order: sportCatalog.ids,
      hidden: sportCatalog.ids.toSet(),
    );
    final hidden = await prefs.hidden();
    expect(hidden.length, 2);
    expect(hidden.contains(sportCatalog.ids.first), isFalse);
  });

  test('si el por defecto está oculto, abre el primero visible', () async {
    final prefs = prefsOn({});
    await prefs.save(
      order: [kNba, kFootball, kTennis],
      hidden: {kNba},
    );
    expect(await prefs.initial(), kFootball);
    await prefs.save(
      order: [kNba, kFootball, kTennis],
      hidden: {kNba, kFootball},
    );
    expect(await prefs.initial(), kTennis);
  });

  testWidgets('SportSelector marca el seleccionado y avisa al tocar', (
    tester,
  ) async {
    SportId? tapped;
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('es'),
        home: Scaffold(
          body: SportSelector(
            sports: sportCatalog.ids,
            value: kNba,
            onChanged: (s) => tapped = s,
          ),
        ),
      ),
    );
    final semantics = tester.getSemantics(find.bySemanticsLabel(RegExp('NBA')));
    expect(semantics.flagsCollection.isSelected, Tristate.isTrue);
    await tester.tap(find.text('TENIS'));
    expect(tapped, kTennis);
  });

  Widget host(SportId value, ValueChanged<SportId> on) => MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    locale: const Locale('es'),
    home: Scaffold(
      body: SportSelector(
        sports: sportCatalog.ids,
        value: value,
        onChanged: on,
      ),
    ),
  );

  testWidgets('un chip se activa por accesibilidad (acción táctil)', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    SportId? tapped;
    await tester.pumpWidget(host(kNba, (s) => tapped = s));
    tester.semantics.tap(find.semantics.byLabel(RegExp('Tenis')));
    expect(tapped, kTennis);
    handle.dispose();
  });

  testWidgets('la marca no cromática existe solo en el chip activo', (
    tester,
  ) async {
    await tester.pumpWidget(host(kNba, (_) {}));
    final mark = find.byKey(const ValueKey('sport-selected-mark'));
    expect(mark, findsOneWidget);
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('sport-nba')),
        matching: mark,
      ),
      findsOneWidget,
    );
    expect(
      tester.getSize(find.byKey(const ValueKey('sport-nba'))).height,
      greaterThanOrEqualTo(44),
    );
  });
}
