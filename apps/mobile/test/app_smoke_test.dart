import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/main.dart' as app;
import 'package:gobet/onbonding_screen/second_screen.dart';
import 'package:gobet/onbonding_screen/splesh_screen.dart';
import 'package:gobet/product/market_catalog.dart';
import 'package:gobet/forget_password/create_account.dart';
import 'package:gobet/sign_in/home_screen/statistic/month.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:provider/provider.dart';

void main() {
  setUpAll(() async {
    await MarketCatalog.load();
    // Render with the app's actual fonts instead of the test-only Ahem font.
    for (final font in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'Gilroy Black': 'fonts/Gilroy-Black.ttf',
      'Gilroy Light': 'fonts/Gilroy-Light.ttf',
      'Gilroy Heavy': 'fonts/Gilroy-Heavy.ttf',
    }.entries) {
      final loader = FontLoader(font.key)..addFont(rootBundle.load(font.value));
      await loader.load();
    }
  });
  testWidgets('opens splash and navigates to onboarding', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const app.QuantFutApp());
    expect(find.byType(Splesh_Screen), findsOneWidget);
    await tester.pump(const Duration(seconds: 4));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(SecondScreen), findsOneWidget);
    expect(find.text('Fútbol y NBA,\ncon otra perspectiva'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('closing splash cancels delayed navigation', (tester) async {
    await tester.pumpWidget(const app.QuantFutApp());
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 5));
    expect(tester.takeException(), isNull);
  });

  for (final screen in <String, Widget>{
    'updated dotted border': const Create_accout(),
    'updated charts': const Month(),
  }.entries) {
    testWidgets('renders ${screen.key}', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => ColorNotifire(),
          child: MaterialApp(
            theme: ThemeData(useMaterial3: false, fontFamily: 'Gilroy Medium'),
            home: screen.value,
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }
}
