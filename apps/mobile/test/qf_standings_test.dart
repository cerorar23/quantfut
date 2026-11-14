// Pruebas unitarias de tabla de clasificación CyberCore: QfStandingsTable.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_standings.dart';
import 'package:gobet/product/qf_theme.dart';

Widget _host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('QfStandingsTable renderiza filas, callout y zonas', (tester) async {
    final rows = [
      const QfStandingRow(
        position: 1,
        teamId: 'rma',
        teamName: 'Real Madrid',
        played: 20,
        diffGoals: 25,
        points: 50,
        form: 'GGGEG',
        zoneColor: QfColors.cyan,
      ),
      const QfStandingRow(
        position: 2,
        teamId: 'bar',
        teamName: 'Barcelona',
        played: 20,
        diffGoals: 22,
        points: 48,
        form: 'GGEEG',
        zoneColor: QfColors.cyan,
      ),
      const QfStandingRow(
        position: 18,
        teamId: 'cad',
        teamName: 'Cádiz',
        played: 20,
        diffGoals: -15,
        points: 16,
        form: 'PPPEP',
        zoneColor: QfColors.magenta,
      ),
    ];

    await tester.pumpWidget(
      _host(
        QfStandingsTable(
          rows: rows,
          highlightIds: const {'rma'},
          calloutText: 'El líder recibe al 18º clasificado',
        ),
      ),
    );

    expect(find.text('El líder recibe al 18º clasificado'), findsOneWidget);
    expect(find.text('Real Madrid'), findsOneWidget);
    expect(find.text('Barcelona'), findsOneWidget);
    expect(find.text('Cádiz'), findsOneWidget);
    expect(find.text('POS'), findsOneWidget);
    expect(find.text('PTS'), findsOneWidget);
  });
}
