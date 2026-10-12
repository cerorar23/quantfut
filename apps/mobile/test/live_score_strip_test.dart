import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_forecast.dart';

Map<String, dynamic> _ficha(Map<String, dynamic>? vivo) => {
  'partido': {'vivo': ?vivo},
  'local': {'nombre': 'Antigua GFC'},
  'visitante': {'nombre': 'Coban Imperial'},
};

Widget _host(Map<String, dynamic> ficha) => MaterialApp(
  home: Scaffold(body: LiveScoreStrip(ficha: ficha)),
);

void main() {
  testWidgets('muestra marcador, minuto y antigüedad del dato', (tester) async {
    await tester.pumpWidget(
      _host(
        _ficha({
          'marcador': [1, 0],
          'minuto': 48,
          'estado': '2H',
          'actualizado': DateTime.now()
              .subtract(const Duration(minutes: 12))
              .toUtc()
              .toIso8601String(),
        }),
      ),
    );
    expect(find.text("48'"), findsOneWidget);
    expect(find.text('1 — 0'), findsOneWidget);
    expect(find.text('Antigua GFC'), findsOneWidget);
    expect(find.textContaining('hace 12 min'), findsOneWidget);
  });

  testWidgets('descanso se muestra como tal', (tester) async {
    await tester.pumpWidget(
      _host(
        _ficha({
          'marcador': [0, 0],
          'minuto': 45,
          'estado': 'HT',
        }),
      ),
    );
    expect(find.text('DESCANSO'), findsOneWidget);
  });

  testWidgets('sin partido.vivo no dibuja nada', (tester) async {
    await tester.pumpWidget(_host(_ficha(null)));
    expect(find.byType(Container), findsNothing);
  });
}
