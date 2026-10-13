// Primera pantalla: elegir idioma antes de la bienvenida y del acceso. Sale solo mientras
// no haya un idioma elegido, guarda la elección y la app pasa sola al flujo normal.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/l10n/language_selection_screen.dart';
import 'package:gobet/main.dart';
import 'package:gobet/onbonding_screen/splesh_screen.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

Future<void> _phone(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// Las animaciones se repiten sin fin: `pumpAndSettle` no terminaría nunca.
Future<void> _settle(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 1500));
}

void main() {
  // Fuentes reales de la app: con la fuente de prueba (Ahem) todo desborda.
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('sale primero si no hay idioma elegido y la app sigue al elegir', (
    tester,
  ) async {
    await _phone(tester, const Size(390, 844));
    AppLocale.instance.reset();
    expect(AppLocale.instance.chosen, isFalse);
    await tester.pumpWidget(const QuantFutApp());
    await _settle(tester);

    expect(find.byType(LanguageSelectionScreen), findsOneWidget);
    expect(find.byType(Splesh_Screen), findsNothing);
    expect(find.text('Selecciona tu idioma'), findsOneWidget);
    for (final code in languages) {
      expect(find.byKey(ValueKey('first-language-$code')), findsOneWidget);
    }

    await tester.tap(find.byKey(const ValueKey('first-language-en')));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pump();

    expect(AppLocale.instance.chosen, isTrue);
    expect(AppLocale.instance.code, 'en');
    expect(find.byType(LanguageSelectionScreen), findsNothing);
    expect(find.byType(Splesh_Screen), findsOneWidget);
  });

  testWidgets('no sale si ya hay un idioma elegido', (tester) async {
    await _phone(tester, const Size(390, 844));
    await AppLocale.instance.select('pt');
    await tester.pumpWidget(const QuantFutApp());
    await tester.pump();

    expect(find.byType(LanguageSelectionScreen), findsNothing);
    expect(find.byType(Splesh_Screen), findsOneWidget);
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en pantallas pequeñas', (
      tester,
    ) async {
      for (final size in const [Size(390, 844), Size(320, 568)]) {
        await _phone(tester, size);
        AppLocale.instance.reset();
        await tester.pumpWidget(
          MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale(code),
            theme: liveTheme(),
            home: const LanguageSelectionScreen(),
          ),
        );
        await _settle(tester);
        final l10n = lookupAppLocalizations(Locale(code));

        expect(find.text(l10n.languageFirstTitle), findsOneWidget);
        expect(find.text(l10n.languageFirstHint), findsOneWidget);
        expect(find.text(l10n.languageFirstBadge.toUpperCase()), findsOneWidget);
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }

  testWidgets('con «reducir animaciones» no hay animación en bucle', (
    tester,
  ) async {
    await _phone(tester, const Size(390, 844));
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: const LanguageSelectionScreen(),
      ),
    );
    // Sin controladores en marcha, la pantalla se asienta de verdad.
    await tester.pumpAndSettle();
    expect(find.text('Selecciona tu idioma'), findsOneWidget);
  });
}
