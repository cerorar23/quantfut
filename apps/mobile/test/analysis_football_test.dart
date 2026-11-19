import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/analysis_football.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_standings.dart';
import 'package:gobet/product/qf_theme.dart';

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
  final path = 'docs/render_cybercore_20261114/datos/ficha_futbol_mallorca_cordoba_20261114.json';
  final file = File(path);
  if (!file.existsSync()) {
    // Intentar desde la raíz del worktree o apps/mobile
    final alt = '../docs/render_cybercore_20261114/datos/ficha_futbol_mallorca_cordoba_20261114.json';
    return jsonDecode(File(alt).readAsStringSync()) as Map<String, dynamic>;
  }
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  group('FootballAnalysis - Fixture real', () {
    testWidgets('renderiza las 4 secciones con datos de Mallorca vs Córdoba', (tester) async {
      final fixture = _loadRealFixture();
      final api = _FakeApi();
      var h2hTapped = false;

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: api,
            onH2h: () => h2hTapped = true,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. QfSectionNav presente con 4 secciones
      expect(find.byType(QfSectionNav), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'RESUMEN'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'FORMA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'CARA A CARA'), findsOneWidget);
      expect(find.widgetWithText(QfSectionNav, 'TABLA'), findsOneWidget);

      // 2. Sección Resumen «Cómo llegan»
      expect(find.text('CÓMO LLEGAN'), findsOneWidget);
      expect(find.text('TODOS'), findsOneWidget);
      expect(find.text('CASA · FUERA'), findsOneWidget);
      expect(find.text('ÚLTIMOS 10 · 10'), findsOneWidget);
      expect(find.byType(QfDominanceDots), findsOneWidget);
      expect(find.byType(QfRadar), findsOneWidget);
      expect(find.byType(QfDivergingRow), findsNWidgets(10));

      // 3. Toggle TODOS | CASA · FUERA
      await tester.tap(find.text('CASA · FUERA'));
      await tester.pumpAndSettle();
      expect(find.text('EN CASA · FUERA'), findsOneWidget);

      await tester.tap(find.text('TODOS'));
      await tester.pumpAndSettle();
      expect(find.text('ÚLTIMOS 10 · 10'), findsOneWidget);

      // 4. Sección Forma
      expect(find.text('// ÚLTIMOS 5 PARTIDOS'), findsOneWidget);
      expect(find.text('5 SIN PERDER'), findsOneWidget); // Racha de Mallorca
      expect(find.text('4 SIN PERDER'), findsOneWidget); // Racha de Córdoba
      expect(find.text('9 PTS DE 15'), findsOneWidget);
      expect(find.text('10 PTS DE 15'), findsOneWidget);
      expect(find.text('ÚLTIMO'), findsNWidgets(2)); // Etiqueta en el último partido de cada equipo

      // 5. Sección Cara a cara
      expect(find.text('// 6 PARTIDOS'), findsOneWidget);
      expect(find.byType(QfStackedBar), findsOneWidget);
      expect(find.text('2,8'), findsOneWidget); // Goles media
      expect(find.text('50%'), findsNWidgets(2)); // Ambos marcan y +2.5

      // Botón «VER LOS 6 PARTIDOS»
      final viewAllBtn = find.text('VER LOS 6 PARTIDOS');
      expect(viewAllBtn, findsOneWidget);
      await tester.ensureVisible(viewAllBtn);
      await tester.tap(viewAllBtn);
      await tester.pumpAndSettle();
      expect(h2hTapped, isTrue);

      // 6. Sección Clasificación
      expect(find.text('CLASIFICACIÓN'), findsOneWidget);
      expect(find.textContaining('Mallorca 5.º'), findsOneWidget);
      expect(find.textContaining('+3 sobre Cordoba'), findsOneWidget);
      expect(find.byType(QfStandingsTable), findsOneWidget);
    });
  });

  group('FootballAnalysis - Variantes y casos extremos', () {
    testWidgets('sin tabla oculta la sección y el acceso en nav', (tester) async {
      final fixture = Map<String, dynamic>.from(_loadRealFixture());
      fixture.remove('tabla');

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('TABLA'), findsNothing);
      expect(find.text('CLASIFICACIÓN'), findsNothing);
      expect(find.byType(QfStandingsTable), findsNothing);
    });

    testWidgets('sin cara a cara oculta la sección y el botón', (tester) async {
      final fixture = Map<String, dynamic>.from(_loadRealFixture());
      fixture.remove('cara_a_cara');

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CARA A CARA'), findsNothing);
      expect(find.byType(QfStackedBar), findsNothing);
      expect(find.textContaining('VER LOS'), findsNothing);
    });

    testWidgets('sin forma oculta la sección', (tester) async {
      final fixture = Map<String, dynamic>.from(_loadRealFixture());
      final local = Map<String, dynamic>.from(fixture['local'] as Map);
      local.remove('forma');
      final away = Map<String, dynamic>.from(fixture['visitante'] as Map);
      away.remove('forma');
      fixture['local'] = local;
      fixture['visitante'] = away;

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(QfSectionNav, 'FORMA'), findsNothing);
      expect(find.text('// ÚLTIMOS 5 PARTIDOS'), findsNothing);
      expect(find.textContaining('PTS DE 15'), findsNothing);
    });

    testWidgets('sin promedios casa/fuera oculta el interruptor', (tester) async {
      final fixture = Map<String, dynamic>.from(_loadRealFixture());
      final local = Map<String, dynamic>.from(fixture['local'] as Map);
      final lProm = Map<String, dynamic>.from(local['promedios'] as Map);
      lProm.remove('casa');
      local['promedios'] = lProm;
      fixture['local'] = local;

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CÓMO LLEGAN'), findsOneWidget);
      expect(find.text('TODOS'), findsNothing);
      expect(find.text('CASA · FUERA'), findsNothing);
    });

    testWidgets('datos parciales con xG null muestra guión y no falla', (tester) async {
      final fixture = Map<String, dynamic>.from(_loadRealFixture());
      final local = Map<String, dynamic>.from(fixture['local'] as Map);
      final lProm = Map<String, dynamic>.from(local['promedios'] as Map);
      final lTodos = Map<String, dynamic>.from(lProm['todos'] as Map);
      lTodos['xg_favor'] = null;
      lTodos['xg_contra'] = null;
      lProm['todos'] = lTodos;
      local['promedios'] = lProm;
      fixture['local'] = local;

      final away = Map<String, dynamic>.from(fixture['visitante'] as Map);
      final aProm = Map<String, dynamic>.from(away['promedios'] as Map);
      final aTodos = Map<String, dynamic>.from(aProm['todos'] as Map);
      aTodos['xg_favor'] = null;
      aTodos['xg_contra'] = null;
      aProm['todos'] = aTodos;
      away['promedios'] = aProm;
      fixture['visitante'] = away;

      await tester.pumpWidget(
        _host(
          FootballAnalysis(
            ficha: fixture,
            api: _FakeApi(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(QfRadar), findsOneWidget);
      expect(find.text('—'), findsWidgets);
      expect(tester.takeException(), isNull);
    });
  });

  group('FootballAnalysis - Responsividad y localización', () {
    for (final (locale, size) in [
      (const Locale('es'), const Size(390, 844)),
      (const Locale('es'), const Size(360, 800)),
      (const Locale('de'), const Size(360, 800)),
      (const Locale('en'), const Size(360, 800)),
      (const Locale('fr'), const Size(360, 800)),
      (const Locale('it'), const Size(360, 800)),
      (const Locale('pt'), const Size(360, 800)),
    ]) {
      testWidgets('no se desborda en ${locale.languageCode} a ${size.width}x${size.height}', (tester) async {
        final fixture = _loadRealFixture();
        await tester.pumpWidget(
          _host(
            FootballAnalysis(
              ficha: fixture,
              api: _FakeApi(),
              onH2h: () {},
            ),
            locale: locale,
            size: size,
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  });
}
