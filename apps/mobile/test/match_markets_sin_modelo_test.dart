import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_match_markets.dart';

Future<void> open(WidgetTester tester, Map<String, dynamic> data) async {
  tester.view.physicalSize = const Size(390, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      home: Scaffold(
        body: SingleChildScrollView(
          child: MatchMarkets(data: data, onVip: () {}),
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  const locks = [
    {'id': 'k1', 'grupo': 'DOBLE OPORTUNIDAD', 'locked': true},
    {'id': 'k2', 'grupo': 'CÓRNERS', 'locked': true},
  ];

  testWidgets('sin modelo de goles: candados por categoría y sin marcadores', (
    tester,
  ) async {
    await open(tester, {
      'filas': locks,
      'marcadores': null,
      'abiertas': 0,
      'total': 2,
      'sin_modelo': true,
    });
    expect(find.textContaining('CÓRNERS · 1 mercado'), findsOneWidget);
    expect(find.textContaining('DOBLE OPORTUNIDAD · 1 mercado'), findsOneWidget);
    expect(find.text('Marcadores más probables'), findsNothing);
  });

  testWidgets('con modelo: los candados siguen trayendo los marcadores', (
    tester,
  ) async {
    await open(tester, {
      'filas': locks,
      'marcadores': null,
      'abiertas': 0,
      'total': 2,
    });
    expect(find.text('Marcadores más probables'), findsOneWidget);
  });
}
