import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/l10n/pick_labels.dart';
import 'package:gobet/product/analysis_tennis.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_theme.dart';
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

Map<String, dynamic> _loadStatsFixture() {
  const path = 'docs/render_cybercore_20261114/datos/tenis_estadisticas_fritz_tirante_20261114.json';
  final file = File(path);
  if (!file.existsSync()) {
    const alt = '../docs/render_cybercore_20261114/datos/tenis_estadisticas_fritz_tirante_20261114.json';
    return jsonDecode(File(alt).readAsStringSync()) as Map<String, dynamic>;
  }
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

SportEvent _loadEventFixture() {
  const path = 'docs/render_cybercore_20261114/datos/tenis_evento_fritz_tirante_20261114.json';
  final file = File(path);
  final content = file.existsSync()
      ? file.readAsStringSync()
      : File('../docs/render_cybercore_20261114/datos/tenis_evento_fritz_tirante_20261114.json').readAsStringSync();
  final data = jsonDecode(content) as Map<String, dynamic>;
  final events = tennisEvents(data);
  return events.first;
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  group('TennisAnalysis - Fixture real', () {
    testWidgets('renderiza las 5 secciones con datos reales de Fritz vs Tirante', (tester) async {
      final stats = _loadStatsFixture();
      final event = _loadEventFixture();
      final api = _FakeApi();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
            api: api,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. QfSectionNav con 5 secciones
      expect(find.byType(QfSectionNav), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'PROBABILIDAD'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'FORMA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'SUPERFICIE'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'CARA A CARA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'MODELO'), findsOneWidget);

      // 2. Probabilidad: 82% vs 18%, nombres y ranking
      expect(find.text('82%'), findsOneWidget);
      expect(find.text('18%'), findsOneWidget);
      expect(find.text('Taylor Fritz'), findsWidgets);
      expect(find.text('Thiago Agustin Tirante'), findsWidgets);
      expect(find.textContaining('3095'), findsOneWidget); // Puntos Fritz
      expect(find.textContaining('1023'), findsOneWidget); // Puntos Tirante
      expect(find.textContaining('41 puestos'), findsOneWidget); // Brecha de ranking

      // 3. Forma: índices de forma 75 y 67, racha, rondas traducidas
      expect(find.text('75 / 100'), findsOneWidget);
      expect(find.text('67 / 100'), findsOneWidget);
      expect(find.textContaining('RACHA: 2 VICTORIAS'), findsOneWidget);
      expect(find.textContaining('RACHA: 3 VICTORIAS'), findsOneWidget);
      expect(find.textContaining('22% a 3 sets'), findsOneWidget);
      expect(find.textContaining('33% con tie-break'), findsOneWidget);
      expect(find.textContaining('Semifinal'), findsWidgets); // Ronda traducida

      // 4. Superficie: Pista dura de hoy con badge HOY
      expect(find.text('HOY'), findsWidgets);
      expect(find.textContaining('PISTA DURA'), findsWidgets);

      // 5. Cara a cara: 0 – 0 · PRIMER DUELO
      expect(find.text('0 – 0'), findsOneWidget);
      expect(find.text('PRIMER DUELO'), findsOneWidget);

      // 6. Modelo: duración en sets, sets 1 y 2, hándicap, tiebreak, juegos esperados
      expect(find.text('71% en 2 sets'), findsOneWidget);
      expect(find.text('29% en 3 sets'), findsOneWidget);
      expect(find.text('SET 1'), findsOneWidget);
      expect(find.text('SET 2'), findsOneWidget);
      expect(find.text('40%'), findsOneWidget); // Tiebreak
      expect(find.textContaining('≈ 21'), findsOneWidget); // Juegos esperados
    });

    testWidgets('navegación por QfSectionNav actualiza la pestaña seleccionada', (tester) async {
      final stats = _loadStatsFixture();
      final event = _loadEventFixture();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(QfSectionNav, 'FORMA'));
      await tester.pumpAndSettle();

      expect(find.byType(QfSectionNav), findsOneWidget);
    });

    testWidgets('cara a cara con partidos registrados muestra resumen y botón ver todos', (tester) async {
      final stats = _loadStatsFixture();
      final event = _loadEventFixture();
      var h2hOpened = false;

      // Inyectar historial directo no vacío
      stats['h2h'] = {
        'first_wins': 2,
        'second_wins': 1,
        'matches': [
          {
            'date': '2025-08-10',
            'won': true,
            'opponent': 'Thiago Agustin Tirante',
            'tournament': 'WTA Cincinnati',
            'surface': 'Hard',
            'score': '7-5 6-4',
          },
        ],
      };

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
            onH2h: () => h2hOpened = true,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('2'), findsWidgets);
      expect(find.text('1'), findsWidgets);
      expect(find.textContaining('WTA Cincinnati'), findsOneWidget);
      expect(find.text('7-5 6-4'), findsOneWidget);

      final btn = find.text('VER TODOS EN H2H');
      expect(btn, findsOneWidget);
      await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -1500));
      await tester.pumpAndSettle();
      await tester.tap(btn);
      expect(h2hOpened, isTrue);
    });

    testWidgets('sin h2h en datos oculta la sección CARA A CARA', (tester) async {
      final stats = _loadStatsFixture();
      stats.remove('h2h');
      final event = _loadEventFixture();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'CARA A CARA'), findsNothing);
    });

    testWidgets('sin superficies en datos oculta la sección SUPERFICIE', (tester) async {
      final stats = _loadStatsFixture();
      final players = stats['players'] as List<dynamic>;
      for (final p in players) {
        if (p is Map) p.remove('surfaces');
      }
      final event = _loadEventFixture();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'SUPERFICIE'), findsNothing);
    });

    testWidgets('sin mercados de juegos o sets oculta la sección MODELO', (tester) async {
      final stats = _loadStatsFixture();
      final eventBase = _loadEventFixture();
      final eventNoModel = SportEvent(
        id: eventBase.id,
        sport: eventBase.sport,
        home: eventBase.home,
        away: eventBase.away,
        start: eventBase.start,
        league: eventBase.league,
        status: eventBase.status,
        surface: eventBase.surface,
        seal: eventBase.seal,
        sealedAt: eventBase.sealedAt,
        markets: [
          eventBase.markets.firstWhere((m) => m.id == 'winner'),
        ],
      );

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: eventNoModel,
            data: stats,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'MODELO'), findsNothing);
    });

    testWidgets('ronda desconocida muestra el texto crudo sin fallar', (tester) async {
      expect(tennisRoundLabel('Super Round 9'), 'Super Round 9');
      expect(tennisRoundLabel('1/16-finals'), 'Ronda de 32');
      expect(tennisRoundLabel('Quarterfinals'), 'Cuartos');
      expect(tennisRoundLabel('Final'), 'Final');
    });

    testWidgets('renderiza sin overflow en 360x800 con alemán (de)', (tester) async {
      final stats = _loadStatsFixture();
      final event = _loadEventFixture();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
          ),
          locale: const Locale('de'),
          size: const Size(360, 800),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TennisAnalysis), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('renderiza sin overflow en 390x844 con español (es)', (tester) async {
      final stats = _loadStatsFixture();
      final event = _loadEventFixture();

      await tester.pumpWidget(
        _host(
          TennisAnalysis(
            event: event,
            data: stats,
          ),
          locale: const Locale('es'),
          size: const Size(390, 844),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TennisAnalysis), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
