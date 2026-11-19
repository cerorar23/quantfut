import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/sport_detail_tabs.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

Map<String, dynamic> _fixture(String name) {
  final file = File('test/fixtures/$name');
  if (file.existsSync()) {
    return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
  }
  final alt = File('../test/fixtures/$name');
  return jsonDecode(alt.readAsStringSync()) as Map<String, dynamic>;
}

Future<void> _pump(
  WidgetTester tester,
  Widget body, {
  Size size = const Size(390, 844),
  String code = 'es',
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select(code);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: Scaffold(
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: body,
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 500));
}

Future<void> _pumpScreen(WidgetTester tester, Widget screen) async {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select('es');
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: screen,
    ),
  );
  await tester.pump(const Duration(milliseconds: 500));
}

SportEvent _tennisEvent() => SportEvent(
      id: '9017489481',
      sport: kTennis,
      home: 'Taylor Fritz',
      away: 'Thiago Tirante',
      league: 'ATP · ESTOCOLMO · FINAL',
      surface: 'Hard',
      start: DateTime.utc(2026, 11, 14, 12),
      status: 'scheduled',
      seal: 'mock-seal-tennis',
      sealedAt: DateTime.utc(2026, 11, 14, 11),
      markets: const [],
    );

SportEvent _nbaEvent() => SportEvent(
      id: '0022600021',
      sport: kNba,
      home: 'Houston Rockets',
      away: 'Dallas Mavericks',
      league: 'NBA · TEMPORADA REGULAR',
      start: DateTime.utc(2026, 11, 14, 20),
      status: 'scheduled',
      seal: 'mock-seal-nba',
      sealedAt: DateTime.utc(2026, 11, 14, 19),
      markets: const [],
    );

class _ApiMock extends QuantFutApi {
  _ApiMock(this.ficha);
  final Map<String, dynamic> ficha;

  @override
  Future<JsonMap> detail(String id) async => {
        'config': {
          'features': {
            'h2h': {'enabled': true, 'message': ''},
          },
        },
        'ficha': ficha,
      };
}

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });

  group('F4g H2H CyberCore', () {
    testWidgets('tenis 0–0 muestra estado «primer duelo» con dos tarjetas en 0 y fila especial', (
      tester,
    ) async {
      final realStats = _fixture('tenis_estadisticas_real.json');
      final event = _tennisEvent();

      await _pump(
        tester,
        SportH2h(
          stats: Future.value(realStats),
          event: event,
        ),
      );

      // Verificación de tarjetas de resumen con 0
      expect(find.text('FRITZ'), findsWidgets);
      expect(find.text('TIRANTE'), findsWidgets);
      expect(find.text('0'), findsNWidgets(2));

      // Verificación de sección de últimos enfrentamientos
      expect(find.text('ÚLTIMOS ENFRENTAMIENTOS'), findsOneWidget);

      // Fila de primer duelo coincidente con PartidoTenis.png
      expect(find.text('—'), findsOneWidget);
      expect(find.text('Primer duelo entre ambos'), findsOneWidget);
      expect(find.text('0–0'), findsOneWidget);

      // Al ser 0-0 no hay barra apilada
      expect(find.byType(QfStackedBar), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('tenis con partidos muestra victorias, QfStackedBar y marcador', (
      tester,
    ) async {
      final tennisStats = _fixture('tennis_stats.json');
      final event = SportEvent(
        id: '12173711',
        sport: kTennis,
        home: 'Liudmila Samsonova',
        away: 'Heather Watson',
        league: 'WTA Cincinnati',
        surface: 'Clay',
        start: DateTime.utc(2026, 10, 24),
        status: 'scheduled',
        seal: 'mock-seal-samsonova',
        sealedAt: DateTime.utc(2026, 10, 23, 10),
        markets: const [],
      );

      await _pump(
        tester,
        SportH2h(
          stats: Future.value(tennisStats),
          event: event,
        ),
      );

      // Tarjetas de resumen
      expect(find.text('SAMSONOVA'), findsWidgets);
      expect(find.text('WATSON'), findsWidgets);
      expect(find.text('2'), findsOneWidget);
      expect(find.text('1'), findsOneWidget);

      // Barra apilada
      expect(find.byType(QfStackedBar), findsOneWidget);

      // Lista de partidos
      expect(find.text('ÚLTIMOS ENFRENTAMIENTOS'), findsOneWidget);
      expect(find.textContaining('WTA Cincinnati'), findsOneWidget);
      expect(find.textContaining('6-3 6-4'), findsOneWidget);
      expect(find.textContaining('WTA Indian Wells'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('NBA H2H muestra resumen, QfStackedBar y lista con puntos', (
      tester,
    ) async {
      final nbaStats = _fixture('nba_stats.json');
      final event = _nbaEvent();

      await _pump(
        tester,
        SportH2h(
          stats: Future.value(nbaStats),
          event: event,
        ),
      );

      // Códigos de equipo
      expect(find.text('HOU'), findsWidgets);
      expect(find.text('DAL'), findsWidgets);

      // Barra apilada y partidos
      expect(find.byType(QfStackedBar), findsOneWidget);
      expect(find.text('ÚLTIMOS ENFRENTAMIENTOS'), findsOneWidget);
      expect(find.textContaining('Houston Rockets 128'), findsWidgets);
      expect(find.textContaining('Dallas Mavericks 110'), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('fútbol H2H muestra 3 tarjetas (local, empates, visitante), QfStackedBar y lista', (
      tester,
    ) async {
      final realFicha = _fixture('ficha_futbol_real.json');
      final api = _ApiMock(realFicha);

      await _pumpScreen(
        tester,
        LiveMatchDetail(
          api: api,
          id: 'test-futbol',
          onVip: () {},
        ),
      );

      // Cambiar a pestaña H2H (tab index 2)
      await tester.tap(find.text('H2H'));
      await tester.pump(const Duration(milliseconds: 500));

      // 3 tarjetas de resumen
      expect(find.text('MALLORCA'), findsWidgets);
      expect(find.text('EMPATES'), findsOneWidget);
      expect(find.text('CORDOBA'), findsWidgets);
      expect(find.text('2'), findsWidgets); // victorias local
      expect(find.text('1'), findsWidgets); // empates
      expect(find.text('3'), findsWidgets); // victorias visitante

      // Barra apilada con 3 partes
      expect(find.byType(QfStackedBar), findsOneWidget);

      // Lista de cruces
      expect(find.text('ÚLTIMOS ENFRENTAMIENTOS'), findsOneWidget);
      expect(find.textContaining('3-2'), findsWidgets);
      expect(find.textContaining('3-0'), findsWidgets);
      expect(find.textContaining('1-1'), findsWidgets);
      expect(find.text('EMP'), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('responsive a 320, 360 y 390 dp sin desbordamientos', (
      tester,
    ) async {
      final realStats = _fixture('tenis_estadisticas_real.json');
      final event = _tennisEvent();

      for (final width in [320.0, 360.0, 390.0]) {
        await _pump(
          tester,
          SportH2h(
            stats: Future.value(realStats),
            event: event,
          ),
          size: Size(width, 844),
        );
        expect(tester.takeException(), isNull);
      }
    });

    testWidgets('traducciones en los 6 idiomas para elementos de H2H', (
      tester,
    ) async {
      final realStats = _fixture('tenis_estadisticas_real.json');
      final event = _tennisEvent();

      const expectedFirstDuel = {
        'es': 'Primer duelo entre ambos',
        'en': 'First head-to-head matchup',
        'pt': 'Primeiro confronto direto',
        'fr': 'Première confrontation directe',
        'it': 'Primo scontro diretto',
        'de': 'Erstes Aufeinandertreffen',
      };

      const expectedRecent = {
        'es': 'ÚLTIMOS ENFRENTAMIENTOS',
        'en': 'RECENT MATCHUPS',
        'pt': 'ÚLTIMOS CONFRONTOS',
        'fr': 'DERNIÈRES CONFRONTATIONS',
        'it': 'ULTIMI SCONTRI DIRETTI',
        'de': 'LETZTE DIREKTDUELLE',
      };

      for (final lang in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
        await _pump(
          tester,
          SportH2h(
            stats: Future.value(realStats),
            event: event,
          ),
          code: lang,
        );

        expect(find.text(expectedFirstDuel[lang]!), findsOneWidget);
        expect(find.text(expectedRecent[lang]!), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });
  });
}
