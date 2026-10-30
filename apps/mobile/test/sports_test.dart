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
  test('id desconocido vuelve a fútbol', () async {
    final store = {'sports_last': 'baloncesto'};
    expect(await prefsOn(store).initial(), SportKind.football);
    expect(SportKind.fromId('nba'), SportKind.nba);
    expect(SportKind.fromId(null), isNull);
  });

  test('no se pueden ocultar todos', () async {
    final prefs = prefsOn({});
    await prefs.save(
      order: SportKind.values,
      hidden: SportKind.values.toSet(),
    );
    final hidden = await prefs.hidden();
    expect(hidden.length, 2);
    expect(hidden.contains(SportKind.values.first), isFalse);
  });

  test('si el por defecto está oculto, abre el primero visible', () async {
    final prefs = prefsOn({});
    await prefs.save(
      order: [SportKind.nba, SportKind.football, SportKind.tennis],
      hidden: {SportKind.nba},
    );
    expect(await prefs.initial(), SportKind.football);
  });

  testWidgets('SportSelector marca el seleccionado y avisa al tocar', (
    tester,
  ) async {
    SportKind? tapped;
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('es'),
        home: Scaffold(
          body: SportSelector(
            sports: SportKind.values,
            value: SportKind.nba,
            onChanged: (s) => tapped = s,
          ),
        ),
      ),
    );
    final semantics = tester.getSemantics(find.bySemanticsLabel(RegExp('NBA')));
    expect(semantics.flagsCollection.isSelected, Tristate.isTrue);
    await tester.tap(find.text('TENIS'));
    expect(tapped, SportKind.tennis);
  });

  Widget host(SportKind value, ValueChanged<SportKind> on) => MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    locale: const Locale('es'),
    home: Scaffold(
      body: SportSelector(
        sports: SportKind.values,
        value: value,
        onChanged: on,
      ),
    ),
  );

  testWidgets('un chip se activa por accesibilidad (acción táctil)', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    SportKind? tapped;
    await tester.pumpWidget(host(SportKind.nba, (s) => tapped = s));
    tester.semantics.tap(find.semantics.byLabel(RegExp('Tenis')));
    expect(tapped, SportKind.tennis);
    handle.dispose();
  });

  testWidgets('la marca no cromática existe solo en el chip activo', (
    tester,
  ) async {
    await tester.pumpWidget(host(SportKind.nba, (_) {}));
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
