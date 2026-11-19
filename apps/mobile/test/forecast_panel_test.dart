import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_forecast.dart';

final _ficha = {
  'local': {'nombre': 'Albacete'},
  'visitante': {'nombre': 'Celta II'},
};

Map<String, dynamic> _pick({Map<String, dynamic>? analisis}) => {
  'market': 'double_chance',
  'selection': '12',
  'texto': 'Albacete o Celta II (sin empate)',
  'prob': 0.78,
  'ref_price': 1.23,
  'free': true,
  'analisis': ?analisis,
};

Widget _host(Map<String, dynamic> pick) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  home: Scaffold(
    body: SingleChildScrollView(
      child: ForecastPanel(pick: pick, ficha: _ficha),
    ),
  ),
);

void main() {
  testWidgets('pinta las casillas que eligió el servidor y su resumen', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        _pick(
          analisis: {
            'receta': 'resultado',
            'casillas': [
              {'id': 'xg', 'total': 2.5, 'a': 1.6, 'b': 0.9},
              {'id': 'empate', 'a': 15, 'b': 10, 'liga': 28},
              {'id': 'forma', 'a': 13, 'b': 8, 'n_a': 5, 'n_b': 5},
            ],
            'resumen': {
              AppLocale.instance.code:
                  'Un partido que rara vez termina en tablas.',
            },
          },
        ),
      ),
    );
    expect(find.text('MODELO ALGORÍTMICO'), findsWidgets);
    expect(find.textContaining('RESUMEN DEL PRONÓSTICO'), findsOneWidget);
    expect(find.text('15 % · 10 %'), findsOneWidget);
    expect(find.text('13 – 8'), findsOneWidget);
    expect(find.textContaining('rara vez termina en tablas'), findsOneWidget);
    // La frase del precio la pone la app (cuota 1,23 por debajo de la justa 1,28), no la IA.
    expect(
      find.textContaining('queda por debajo de la cuota justa'),
      findsOneWidget,
    );
    expect(find.textContaining('—'), findsNothing);
  });

  testWidgets('sin análisis del servidor conserva las casillas de siempre', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_pick()));
    expect(
      find.textContaining(RegExp('probabilidad', caseSensitive: false)),
      findsWidgets,
    );
    expect(
      find.textContaining(RegExp('tendencia goles', caseSensitive: false)),
      findsOneWidget,
    );
    expect(find.textContaining('78'), findsWidgets);
  });
}
