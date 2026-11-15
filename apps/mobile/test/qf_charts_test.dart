// Pruebas unitarias de gráficos CyberCore: QfRing, QfRadar, QfDivergingRow, QfDominanceDots,
// QfFormPills, QfMarginBars, QfStackedBar, QfSeasonTrack, QfPips, QfSegmentedChart.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/qf_theme.dart';

Widget _host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('QfRing muestra el porcentaje formateado', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfRing(
          value: 0.72,
          size: 60,
        ),
      ),
    );
    expect(find.text('72%'), findsOneWidget);
  });

  testWidgets('QfRadar requiere 5 etiquetas y se dibuja correctamente', (tester) async {
    expect(
      () => QfRadar(
        labels: const ['A', 'B'],
        a: const [0.5, 0.5],
        b: const [0.5, 0.5],
      ),
      throwsAssertionError,
    );

    await tester.pumpWidget(
      _host(
        QfRadar(
          labels: const ['ATAQUE', 'DEFENSA', 'POSESIÓN', 'RITMO', 'EFICACIA'],
          a: const [0.8, 0.6, 0.9, 0.7, 0.75],
          b: const [0.5, 0.8, 0.6, 0.8, 0.65],
          size: 200,
        ),
      ),
    );
    expect(find.byType(QfRadar), findsOneWidget);
  });

  testWidgets('QfDivergingRow muestra etiquetas y valores comparativos', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfDivergingRow(
          label: 'Tiros de campo',
          a: 48.5,
          b: 44.2,
          formatA: '48.5%',
          formatB: '44.2%',
        ),
      ),
    );
    expect(find.text('TIROS DE CAMPO'), findsOneWidget);
    expect(find.text('48.5%'), findsOneWidget);
    expect(find.text('44.2%'), findsOneWidget);
  });

  testWidgets('QfDominanceDots calcula resumen de dominio', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfDominanceDots(
          winners: [1, 1, -1, 1, 0, 1],
          homeName: 'Real Madrid',
          awayName: 'Barcelona',
        ),
      ),
    );
    expect(find.text('Real Madrid mejor en 4 de 6'), findsOneWidget);
  });

  testWidgets('QfFormPills renderiza píldoras de forma con último partido', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfFormPills(
          results: [
            QfFormResult(result: 'G', score: '2-1', opponent: 'RMA', isHome: true),
            QfFormResult(result: 'E', score: '1-1', opponent: 'ATM', isHome: false),
            QfFormResult(result: 'P', score: '0-2', opponent: 'SEV', isHome: true),
            QfFormResult(result: 'G', score: '3-0', opponent: 'VAL', isHome: false, isLast: true),
          ],
        ),
      ),
    );
    expect(find.text('G'), findsNWidgets(2));
    expect(find.text('E'), findsOneWidget);
    expect(find.text('P'), findsOneWidget);
  });

  testWidgets('QfMarginBars dibuja barras proporcionales', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfMarginBars(
          margins: [12, -5, 8, 15, -3],
        ),
      ),
    );
    expect(find.byType(QfMarginBars), findsOneWidget);
  });

  testWidgets('QfStackedBar suma partes y muestra leyenda', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfStackedBar(
          parts: [
            ('Local', 15.0, QfColors.cyan),
            ('Empate', 8.0, QfColors.slate),
            ('Visitante', 10.0, QfColors.chrome),
          ],
        ),
      ),
    );
    expect(find.textContaining('Local (15)'), findsOneWidget);
    expect(find.textContaining('Empate (8)'), findsOneWidget);
    expect(find.textContaining('Visitante (10)'), findsOneWidget);
  });

  testWidgets('QfSeasonTrack posiciona local y visitante', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfSeasonTrack(
          homeRank: 2,
          awayRank: 8,
          homeCode: 'BOS',
          awayCode: 'MIA',
        ),
      ),
    );
    expect(find.text('BOS'), findsOneWidget);
    expect(find.text('MIA'), findsOneWidget);
  });

  testWidgets('QfPips renderiza casillas de balance', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfPips(
          total: 10,
          filled: 6,
          spend: 2,
          missing: 1,
        ),
      ),
    );
    expect(find.byType(QfPips), findsOneWidget);
  });

  testWidgets('QfSegmentedChart muestra barras verticales y etiquetas', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfSegmentedChart(
          bars: [
            ('1er Set', 6.0, '6'),
            ('2do Set', 4.0, '4'),
            ('3er Set', 7.0, '7'),
          ],
        ),
      ),
    );
    expect(find.text('1er Set'), findsOneWidget);
    expect(find.text('2do Set'), findsOneWidget);
    expect(find.text('3er Set'), findsOneWidget);
  });
}
