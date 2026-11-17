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
      child: SportForecastPanel(
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

  testWidgets('NBA: casillas de total proyectado, ritmo y cara a cara', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        home: Scaffold(
          body: SingleChildScrollView(
            child: SportForecastPanel(
              nba: true,
              analisis: {
                'receta': 'total',
                'mercado_id': 'totals-None-230.5-over',
                'casillas': [
                  {'id': 'proy_total', 'total': 234.3, 'a': 121.9, 'b': 112.4},
                  {'id': 'ritmo', 'pos': 101.3},
                  {'id': 'h2h_total', 'avg': 226.8, 'n': 4},
                ],
                'resumen': {
                  AppLocale.instance.code: 'Se esperan puntos de sobra.',
                },
              },
              pickText: 'Más de 230,5 puntos',
              probability: 0.62,
              quote: const SizedBox.shrink(),
              home: 'Cleveland Cavaliers',
              away: 'Chicago Bulls',
            ),
          ),
        ),
      ),
    );
    expect(find.text('234,3'), findsOneWidget);
    expect(find.text('101,3'), findsOneWidget);
    expect(find.text('226,8'), findsOneWidget);
    expect(find.textContaining('4 partidos'), findsOneWidget);
    expect(find.text('Se esperan puntos de sobra.'), findsOneWidget);
    expect(find.textContaining('—'), findsNothing);
  });

  testWidgets('NBA: ganador con forma y diferencial, y equipo con su ataque', (
    tester,
  ) async {
    Widget host(List<Map<String, dynamic>> casillas) => MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      home: Scaffold(
        body: SingleChildScrollView(
          child: SportForecastPanel(
            nba: true,
            analisis: {'casillas': casillas},
            pickText: 'Cleveland Cavaliers',
            probability: 0.75,
            quote: const SizedBox.shrink(),
            home: 'Cleveland Cavaliers',
            away: 'Chicago Bulls',
          ),
        ),
      ),
    );
    await tester.pumpWidget(
      host([
        {'id': 'proy_margen', 'margen': 9.5, 'a': 121.9, 'b': 112.4},
        {'id': 'forma', 'a_w': 4, 'a_l': 2, 'b_w': 3, 'b_l': 3, 'n': 6},
        {'id': 'dif', 'a': 1.6, 'b': -7.4, 'n_a': 14, 'n_b': 14},
      ]),
    );
    expect(find.text('+9,5'), findsOneWidget);
    expect(find.text('4-2 · 3-3'), findsOneWidget);
    expect(find.text('+1,6 · -7,4'), findsOneWidget);
    await tester.pumpWidget(
      host([
        {'id': 'proy_equipo', 'a': 112.4, 'equipo': 'b', 'linea': 112.5},
        {'id': 'ataque_defensa', 'a': 110.6, 'b': 115.9, 'equipo': 'b'},
        {'id': 'bajas', 'a': 2, 'b': 1},
      ]),
    );
    expect(find.text('112,4'), findsOneWidget);
    expect(find.text('110,6 vs 115,9'), findsOneWidget);
    expect(find.text('2 · 1'), findsOneWidget);
    expect(find.text('Chicago Bulls'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
