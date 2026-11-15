import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/analysis_nba.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

class _FakeApi extends QuantFutApi {
  @override
  Uri get base => Uri.parse('https://pronosticosdeportivos.pro');
}

Widget _host(
  Widget child, {
  Locale locale = const Locale('es'),
  Size size = const Size(390, 844),
}) {
  return MediaQuery(
    data: MediaQueryData(size: size),
    child: MaterialApp(
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: QfColors.bg,
      ),
      home: Scaffold(
        body: SingleChildScrollView(
          child: child,
        ),
      ),
    ),
  );
}

Map<String, dynamic> _loadRealFixture() {
  const path = 'docs/render_cybercore_20261114/datos/nba_estadisticas_heat_pistons_20261114.json';
  final file = File(path);
  if (!file.existsSync()) {
    const alt = '../docs/render_cybercore_20261114/datos/nba_estadisticas_heat_pistons_20261114.json';
    return jsonDecode(File(alt).readAsStringSync()) as Map<String, dynamic>;
  }
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

SportEvent _createNbaEvent({
  JsonMap? availability,
  List<SportMarket>? markets,
  String seal = '9f3a1234567890c21e',
}) {
  return SportEvent(
    id: '18608',
    sport: kNba,
    home: 'Miami Heat',
    away: 'Detroit Pistons',
    league: 'NBA',
    start: DateTime.utc(2026, 11, 15, 1),
    status: 'scheduled',
    seal: seal,
    sealedAt: DateTime.utc(2026, 11, 14, 23),
    markets: markets ??
        [
          SportMarket(
            id: 'w',
            market: 'winner',
            label: 'Ganador',
            selection: 'Detroit Pistons',
            probability: 0.56,
            sealedAt: DateTime.utc(2026, 11, 14, 23),
            eligible: true,
          ),
        ],
    availability: availability ??
        const {
          'state': 'official',
          'missing_minutes_home': 42.0,
          'missing_minutes_away': 15.0,
          'listed': 3,
          'teams_not_submitted': [],
        },
  );
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  group('NbaAnalysis - Fixture real', () {
    testWidgets('renderiza las 6 secciones con datos de Heat vs Pistons', (tester) async {
      final fixture = _loadRealFixture();
      final event = _createNbaEvent();
      final api = _FakeApi();
      var h2hTapped = false;

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: event,
            data: fixture,
            api: api,
            onH2h: () => h2hTapped = true,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. QfSectionNav presente con 6 secciones
      expect(find.byType(QfSectionNav), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'PROBABILIDAD'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'COMPARATIVA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'FORMA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'CARA A CARA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'CLASIFICACIÓN'), findsOneWidget);
      // Desplazar el nav horizontal para ver el sexto chip
      await tester.drag(find.byType(QfSectionNav), const Offset(-200, 0));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(QfSectionNav, 'DISPONIBILIDAD'), findsOneWidget);

      // 2. Sección Probabilidad
      expect(find.text('PROBABILIDAD DE GANAR'), findsOneWidget);
      expect(find.text('56%'), findsOneWidget); // Detroit prob
      expect(find.text('44%'), findsOneWidget); // Miami prob
      expect(find.text('FACTORES DEL PARTIDO'), findsOneWidget);

      // 3. Sección Comparativa
      expect(find.text('COMPARATIVA'), findsWidgets);
      expect(find.byType(QfDominanceDots), findsOneWidget);
      expect(find.byType(QfDivergingRow), findsNWidgets(7));
      expect(find.text('RÉCORD'), findsOneWidget);
      expect(find.text('VISITANTE · LOCAL'), findsOneWidget);
      expect(find.text('PUNTOS A FAVOR'), findsOneWidget);
      expect(find.text('PUNTOS EN CONTRA'), findsOneWidget);
      expect(find.text('DIFERENCIAL'), findsOneWidget);
      expect(find.text('ÚLTIMOS 6'), findsOneWidget);
      expect(find.text('DESCANSO (DÍAS)'), findsOneWidget);

      // 4. Sección Forma
      expect(find.text('// ÚLTIMOS 6 PARTIDOS'), findsOneWidget);
      expect(find.text('MARGEN EN VICTORIA'), findsOneWidget);
      expect(find.text('MARGEN EN DERROTA'), findsOneWidget);
      expect(find.text('ÚLTIMO'), findsNWidgets(2));
      expect(find.textContaining('3 VICTORIAS'), findsOneWidget); // Racha Miami
      expect(find.textContaining('2 VICTORIAS'), findsOneWidget); // Racha Detroit

      // 5. Sección Cara a cara
      expect(find.text('// ÚLTIMOS 10 PARTIDOS'), findsOneWidget);
      expect(find.text('VICTORIAS'), findsOneWidget);
      expect(find.text('PUNTOS TOTALES POR PARTIDO'), findsOneWidget);
      expect(find.text('230.7'), findsOneWidget); // Promedio total

      // Botón "VER TODOS EN H2H"
      final viewAllBtn = find.text('VER TODOS EN H2H');
      expect(viewAllBtn, findsOneWidget);
      await tester.ensureVisible(viewAllBtn);
      await tester.tap(viewAllBtn);
      await tester.pumpAndSettle();
      expect(h2hTapped, isTrue);

      // 6. Sección Clasificación
      expect(find.text('// CONFERENCIA ESTE · 15 EQUIPOS'), findsOneWidget);
      expect(find.byType(QfSeasonTrack), findsOneWidget);
      expect(find.text('3.º de 15'), findsOneWidget); // Detroit Pistons
      expect(find.text('6.º de 15'), findsOneWidget); // Miami Heat
      expect(find.textContaining('Detroit Pistons está 3 puestos por encima de Miami Heat'), findsOneWidget);

      // 7. Sección Disponibilidad
      expect(find.text('// REPORTE OFICIAL DE LESIONES'), findsOneWidget);
      expect(find.text('DISPONIBILIDAD'), findsWidgets);
      expect(find.text('15 min de bajas'), findsOneWidget); // Detroit (<20)
      expect(find.text('42 min de bajas'), findsOneWidget); // Miami (20-50)
      expect(find.text('BACK-TO-BACK · JUGÓ AYER'), findsOneWidget); // Miami
      expect(find.text('DESCANSÓ 1 DÍA'), findsOneWidget); // Detroit
    });
  });

  group('NbaAnalysis - Variantes y casos extremos', () {
    testWidgets('sin disponibilidad oculta la sección y el acceso en nav', (tester) async {
      final fixture = _loadRealFixture();
      final event = _createNbaEvent(availability: const {});

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: event,
            data: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'DISPONIBILIDAD'), findsNothing);
      expect(find.text('// REPORTE OFICIAL DE LESIONES'), findsNothing);
    });

    testWidgets('sin standing oculta la sección de clasificación', (tester) async {
      final fixture = jsonDecode(jsonEncode(_loadRealFixture())) as Map<String, dynamic>;
      final teams = fixture['teams'] as List;
      for (final t in teams) {
        (t as Map).remove('standing');
      }

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: _createNbaEvent(),
            data: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'CLASIFICACIÓN'), findsNothing);
      expect(find.byType(QfSeasonTrack), findsNothing);
    });

    testWidgets('sin form oculta la sección de forma', (tester) async {
      final fixture = jsonDecode(jsonEncode(_loadRealFixture())) as Map<String, dynamic>;
      final teams = fixture['teams'] as List;
      for (final t in teams) {
        (t as Map).remove('form');
      }

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: _createNbaEvent(),
            data: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'FORMA'), findsNothing);
      expect(find.text('MARGEN EN VICTORIA'), findsNothing);
    });

    testWidgets('sin mercado ganador muestra pronóstico pendiente', (tester) async {
      final fixture = _loadRealFixture();
      final event = _createNbaEvent(markets: []);

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: event,
            data: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CUÁNDO SE AGREGA EL PRONÓSTICO'), findsOneWidget);
      expect(find.text('Pronóstico pendiente'), findsOneWidget);
    });

    testWidgets('sin h2h oculta o muestra mensaje vacío', (tester) async {
      final fixture = jsonDecode(jsonEncode(_loadRealFixture())) as Map<String, dynamic>;
      fixture.remove('h2h');

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: _createNbaEvent(),
            data: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'CARA A CARA'), findsNothing);
      expect(find.text('Sin duelos directos registrados esta temporada'), findsNothing);
    });
  });

  group('NbaAnalysis - Responsividad y localización', () {
    testWidgets('no desborda en 360x800 con alemán (de)', (tester) async {
      final fixture = _loadRealFixture();
      final event = _createNbaEvent();

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: event,
            data: fixture,
            api: _FakeApi(),
          ),
          locale: const Locale('de'),
          size: const Size(360, 800),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('no desborda en 390x844 con español (es)', (tester) async {
      final fixture = _loadRealFixture();
      final event = _createNbaEvent();

      await tester.pumpWidget(
        _host(
          NbaAnalysis(
            event: event,
            data: fixture,
            api: _FakeApi(),
          ),
          locale: const Locale('es'),
          size: const Size(390, 844),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });
  });
}
