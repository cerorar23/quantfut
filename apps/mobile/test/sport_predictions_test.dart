// Predicciones y Mercados de NBA y tenis: acierto por familia (solo eligible win/loss),
// nunca cuota, pestaña Jugadores solo con player_*, y error de feed solo en su hueco.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/sport_images.dart';
import 'package:gobet/product/sport_markets.dart';
import 'package:gobet/product/sport_predictions.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

JsonMap fixture(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as JsonMap;

final api = QuantFutApi(base: Uri.parse('https://x.test'));

SportMarket mk(
  String id, {
  String? market,
  String? outcome,
  bool eligible = true,
  double p = .7,
  String? player,
  double? line,
  String label = 'L',
}) => SportMarket(
  id: id,
  label: label,
  selection: 'Sel $id',
  probability: p,
  sealedAt: DateTime.utc(2026, 10, 30, 10),
  eligible: eligible,
  market: market,
  outcome: outcome,
  player: player,
  line: line,
);

SportEvent ev(
  String id,
  List<SportMarket> markets, {
  SportKind sport = SportKind.nba,
  DateTime? start,
}) => SportEvent(
  id: id,
  sport: sport,
  home: 'Miami Heat',
  away: 'New York Knicks',
  league: sport == SportKind.nba ? 'NBA' : 'ATP',
  start: (start ?? DateTime.utc(2026, 11, 2, 19)).toUtc(),
  status: 'scheduled',
  seal: 'abc',
  sealedAt: DateTime.utc(2026, 10, 30),
  markets: markets,
);

Future<void> pump(WidgetTester tester, Widget body) async {
  tester.view.physicalSize = const Size(390, 2400);
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
      home: Scaffold(body: body),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

Widget predictions(
  SportKind sport,
  SportFeed feed, {
  ValueChanged<SportEvent>? onOpen,
  Future<void> Function()? onRetry,
}) => SportPredictions(
  api: api,
  sport: sport,
  feed: feed,
  images: ImageCatalog.empty,
  onOpen: onOpen ?? (_) {},
  onRetry: onRetry ?? () async {},
  now: DateTime(2020),
);

Iterable<String> allTexts(WidgetTester tester) => tester
    .widgetList<Text>(find.byType(Text))
    .map((t) => t.data ?? t.textSpan?.toPlainText() ?? '');

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  test('hitRateByFamily cuenta solo eligible con outcome win/loss; push no cuenta', () {
    final rates = hitRateByFamily([
      ev('1', [
        mk('a', market: 'winner', outcome: 'win'),
        mk('b', market: 'winner', outcome: 'loss'),
        mk('c', market: 'winner', outcome: 'push'),
        mk('d', market: 'winner'),
        mk('e', market: 'winner', outcome: 'win', eligible: false),
        mk('f', market: 'player_points', outcome: 'win'),
        mk('g', market: 'game_total'),
      ]),
      ev('2', [mk('h', market: 'winner', outcome: 'win')]),
    ]);
    final tennis = hitRateByFamily([
      ev('3', [
        mk('winner', outcome: 'win'),
        mk('games_total-2', outcome: 'loss'),
        mk('games_total-3', outcome: 'win'),
      ], sport: SportKind.tennis),
    ]);
    expect(rates['winner'], (won: 2, resolved: 3));
    expect(rates['player_points'], (won: 1, resolved: 1));
    expect(rates['game_total'], (won: 0, resolved: 0));
    expect(tennis['games_total'], (won: 1, resolved: 2));
    expect(tennis['winner'], (won: 1, resolved: 1));
  });

  testWidgets('Predicciones y Mercados de NBA/tenis nunca muestran cuota', (tester) async {
    for (final (sport, file) in [
      (SportKind.nba, 'nba_feed.json'),
      (SportKind.tennis, 'tennis_feed.json'),
    ]) {
      final events = sport == SportKind.nba
          ? nbaEvents(fixture(file))
          : tennisEvents(fixture(file));
      final feed = SportFeed(ready: true, events: events);
      await pump(tester, predictions(sport, feed));
      expect(find.textContaining('Sellado'), findsWidgets);
      expect(allTexts(tester).where((t) => t.contains('@')), isEmpty);
      await pump(tester, SportMarkets(sport: sport, feed: feed));
      expect(allTexts(tester).where((t) => t.contains('@')), isEmpty);
    }
  });

  testWidgets('tarjeta de acierto solo con al menos un resuelto', (tester) async {
    final none = SportFeed(
      ready: true,
      events: [
        ev('1', [mk('a', market: 'winner')]),
      ],
    );
    await pump(tester, predictions(SportKind.nba, none));
    expect(find.byKey(const ValueKey('sport-hit-rate')), findsNothing);
    final some = SportFeed(
      ready: true,
      events: [
        ev('1', [
          mk('a', market: 'winner', outcome: 'win'),
          mk('b', market: 'winner', outcome: 'push'),
        ]),
      ],
    );
    await pump(tester, predictions(SportKind.nba, some));
    expect(find.byKey(const ValueKey('sport-hit-rate')), findsOneWidget);
    expect(find.text('1/1 publicados'), findsOneWidget);
  });

  testWidgets('pestaña Jugadores solo lista mercados player_*', (tester) async {
    final feed = SportFeed(ready: true, events: nbaEvents(fixture('nba_feed.json')));
    await pump(tester, SportMarkets(sport: SportKind.nba, feed: feed));
    expect(find.text('Total del partido'), findsOneWidget);
    expect(find.text('Asistencias de jugador'), findsNothing);
    await tester.tap(find.text('Jugadores'));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Asistencias de jugador'), findsOneWidget);
    expect(find.text('Tapones de jugador'), findsOneWidget);
    expect(find.text('Total del partido'), findsNothing);
    expect(find.text('Ganador'), findsNothing);
  });

  testWidgets('tenis: Partido | Juegos y familia sin resueltos en revisión', (tester) async {
    final feed = SportFeed(
      ready: true,
      events: [
        ev('t', [
          mk('winner', label: 'Ganador del partido', outcome: 'win'),
          mk('games_total-2', label: 'Juegos totales', outcome: 'win'),
          mk('tiebreak-1', label: 'Tie-break'),
        ], sport: SportKind.tennis),
      ],
    );
    await pump(tester, SportMarkets(sport: SportKind.tennis, feed: feed));
    expect(find.text('Ganador del partido'), findsOneWidget);
    expect(find.text('Tie-break'), findsOneWidget);
    expect(find.text('Juegos totales'), findsNothing);
    // Tie-break sin resueltos: sin barra y con «En revisión».
    expect(find.textContaining('En revisión'), findsOneWidget);
    await tester.tap(find.text('Juegos'));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Juegos totales'), findsOneWidget);
    expect(find.text('Ganador del partido'), findsNothing);
    expect(find.text('1/1 publicados'), findsOneWidget);
  });

  testWidgets('feed caído: aviso y Reintentar solo en su hueco', (tester) async {
    var retries = 0;
    await pump(
      tester,
      predictions(
        SportKind.nba,
        const SportFeed(ready: false, events: []),
        onRetry: () async => retries++,
      ),
    );
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    expect(retries, 1);
    await pump(
      tester,
      SportMarkets(
        sport: SportKind.nba,
        feed: const SportFeed(ready: false, events: []),
        onRetry: () async => retries++,
      ),
    );
    expect(find.text('Reintentar'), findsOneWidget);
  });
}
