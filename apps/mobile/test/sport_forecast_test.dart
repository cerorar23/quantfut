import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/sport_forecast.dart';

Map<String, dynamic> _analisis({Map<String, dynamic>? resumen}) => {
  'receta': 'ganador',
  'mercado_id': 'winner',
  'casillas': [
    {'id': 'saque', 'a': 95, 'b': 92, 'n_a': 25, 'n_b': 53, 'sup': 'hard'},
    {'id': 'h2h', 'a': 11, 'b': 4, 'n': 15},
    {'id': 'resto', 'a': 26, 'b': 19, 'n_a': 25, 'n_b': 53, 'sup': 'todas'},
  ],
  'resumen': ?resumen,
};

Widget _host(Map<String, dynamic> analisis) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  home: Scaffold(
    body: SingleChildScrollView(
      child: TennisForecastPanel(
        analisis: analisis,
        pickText: 'Jannik Sinner',
        probability: 0.74,
        quote: const SizedBox.shrink(),
        home: 'Jannik Sinner',
        away: 'Alexander Zverev',
      ),
    ),
  ),
);

void main() {
  testWidgets('pinta las casillas del servidor y su resumen redactado', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        _analisis(
          resumen: {AppLocale.instance.code: 'Sinner parte como favorito.'},
        ),
      ),
    );
    expect(find.text('MODELO ALGORÍTMICO'), findsWidgets);
    expect(find.textContaining('RESUMEN DEL PRONÓSTICO'), findsOneWidget);
    expect(find.text('95 % · 92 %'), findsOneWidget);
    expect(find.text('11 – 4'), findsOneWidget);
    expect(find.text('26 % · 19 %'), findsOneWidget);
    expect(find.textContaining('Sinner · Zverev'), findsWidgets);
    expect(find.textContaining('Dura'), findsOneWidget);
    expect(find.textContaining('todas las superficies'), findsOneWidget);
    expect(find.textContaining('15 partidos'), findsOneWidget);
    expect(find.text('Sinner parte como favorito.'), findsOneWidget);
    expect(find.textContaining('—'), findsNothing);
  });

  testWidgets('sin resumen redactado usa la plantilla con la probabilidad', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_analisis()));
    expect(
      find.textContaining('Jannik Sinner con probabilidad calculada'),
      findsOneWidget,
    );
  });

  testWidgets('con pocas casillas no deja huecos vacíos ni falla', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host({
        'casillas': [
          {'id': 'h2h', 'a': 3, 'b': 2, 'n': 5},
        ],
      }),
    );
    expect(find.text('3 – 2'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
