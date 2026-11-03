// Piezas visuales v3: barra segmentada, de probabilidad, sello y tarjeta con corte.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_shapes.dart';
import 'package:gobet/product/qf_theme.dart';

Widget _host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('SegmentedBar pinta filled de total', (tester) async {
    await tester.pumpWidget(
      _host(const SegmentedBar(total: 6, filled: 3, color: QfColors.nba)),
    );
    final segments = find.byKey(const ValueKey('qf-segment'));
    expect(segments, findsNWidgets(6));
    final colored = tester
        .widgetList<DecoratedBox>(segments)
        .where((b) => (b.decoration as BoxDecoration).color == QfColors.nba);
    expect(colored.length, 3);
  });

  testWidgets('ProbabilityBar acepta 2 y 3 partes y rechaza otras', (tester) async {
    expect(() => ProbabilityBar(parts: [('A', 1.0)]), throwsAssertionError);
    expect(
      () => ProbabilityBar(parts: [('A', .1), ('B', .2), ('C', .3), ('D', .4)]),
      throwsAssertionError,
    );
    await tester.pumpWidget(
      _host(ProbabilityBar(parts: [('LAL', .41), ('BOS', .59)])),
    );
    expect(find.text('LAL 41 %'), findsOneWidget);
    expect(find.text('BOS 59 %'), findsOneWidget);
    await tester.pumpWidget(
      _host(ProbabilityBar(parts: [('1', .3), ('X', .3), ('2', .4)])),
    );
    expect(find.text('X 30 %'), findsOneWidget);
  });

  testWidgets('SealLine acorta el hash', (tester) async {
    await tester.pumpWidget(
      _host(SealLine(seal: '9f3a1234567890c21e', publishedAt: DateTime.utc(2026, 10, 30, 9, 5))),
    );
    expect(find.textContaining('9f3a…c21e'), findsOneWidget);
    expect(find.textContaining('SELLO'), findsOneWidget);
    expect(find.text('> PUBLICADO 09:05 UTC · VERIFICADO'), findsOneWidget);
  });

  testWidgets('QfCard es pulsable a 44 dp o más', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      _host(QfCard(accent: QfColors.football, onTap: () => taps++, child: const Text('x'))),
    );
    expect(tester.getSize(find.byType(InkWell)).height, greaterThanOrEqualTo(44));
    await tester.tap(find.byType(InkWell));
    expect(taps, 1);
  });

  testWidgets('QfBadge pone la etiqueta en mayúsculas', (tester) async {
    await tester.pumpWidget(_host(const QfBadge('nba', color: QfColors.nba)));
    expect(find.text('NBA'), findsOneWidget);
  });
}
