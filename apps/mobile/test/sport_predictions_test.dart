// Predicciones y Mercados de NBA y tenis: acierto por familia (solo eligible win/loss),
// cuota solo con overlay (ver quote_label_test), pestaña Jugadores solo con player_*, y error de feed solo en su hueco.
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
import 'package:gobet/product/sports_quotes.dart';

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
  String? featuredId,
  bool serverFeatured = false,
}) => SportEvent(
  id: id,
  sport: sport,
  home: 'Miami Heat',
  away: 'New York Knicks',
  league: sport == SportKind.nba ? 'NBA' : 'ATP',
  start: (start ?? DateTime.utc(2026, 11, 2, 19)).toUtc(),
  status: 'scheduled',
  seal: 'abc',
  featuredId: featuredId,
  serverFeatured: serverFeatured,
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

Widget markets(
  SportKind sport,
  SportFeed feed, {
  Future<void> Function()? onRetry,
}) => SportMarkets(
  api: api,
  sport: sport,
  feed: feed,
  images: ImageCatalog.empty,
  onRetry: onRetry,
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

  test(
    'hitRateByFamily cuenta solo eligible con outcome win/loss; push no cuenta',
    () {
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
    },
  );

  testWidgets(
    'Predicciones y Mercados de NBA/tenis sin overlay: «—» y nunca un @ inventado',
    (tester) async {
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
        await pump(tester, markets(sport, feed));
        expect(allTexts(tester).where((t) => t.contains('@')), isEmpty);
      }
    },
  );

  testWidgets('tarjeta de acierto solo con al menos un resuelto', (
    tester,
  ) async {
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

  testWidgets(
    'NBA: una tarjeta por familia con el mismo diseño que fútbol, también las vacías',
    (tester) async {
      final feed = SportFeed(
        ready: true,
        events: [
          ev('1', [
            mk('w', market: 'winner', outcome: 'win', p: .8),
            mk('t', market: 'game_total', outcome: 'loss', p: .66, line: 224.5),
            mk(
              'lejos',
              market: 'player_points',
              outcome: 'win',
              p: .98,
              line: 3.5,
              player: 'X',
            ),
          ]),
          ev('2', [
            mk('t', market: 'game_total', outcome: 'loss', p: .8, line: 224.5),
          ]),
        ],
      );
      await pump(tester, markets(SportKind.nba, feed));
      for (final title in [
        'Ganador del partido',
        'Hándicap del partido',
        'Total de puntos del partido',
        'Puntos por equipo',
        'Puntos del jugador',
        'Rebotes del jugador',
        'Asistencias del jugador',
        'Triples del jugador',
      ]) {
        expect(find.text(title), findsOneWidget, reason: title);
      }
      expect(find.text('8'), findsOneWidget); // familias en el radar
      expect(find.text('MODELO ACTIVO'), findsOneWidget);
      // Solo cuentan los publicados: el 98 % queda fuera de la banda 60–95 %.
      expect(find.text('Publicado 1/1'), findsOneWidget);
      expect(find.text('Publicado 0/1'), findsOneWidget);
      expect(find.text('Sin publicaciones aún'), findsNWidgets(6));
      expect(find.text('1/2 publicados acertados · 50,0 %'), findsOneWidget);
    },
  );

  testWidgets(
    'tenis: sus siete familias y entrar a una muestra pronóstico, cuota y casa',
    (tester) async {
      final feed = SportFeed(
        ready: true,
        events: [
          ev(
            't',
            [
              mk('winner', label: 'Ganador del partido', outcome: 'win'),
              mk('games_total-2', label: 'Juegos totales', outcome: 'win'),
              mk('tiebreak-1', label: 'Tie-break', p: .3),
            ],
            sport: SportKind.tennis,
            serverFeatured: true,
            featuredId: 'games_total-2',
          ),
          ev(
            't2',
            [mk('winner', outcome: 'win')],
            sport: SportKind.tennis,
            serverFeatured: true,
            featuredId: 'winner',
          ),
        ],
      );
      await pump(tester, markets(SportKind.tennis, feed));
      for (final title in [
        'Ganador del partido',
        'Juegos totales',
        'Hándicap de juegos',
        'Ganador del set',
        'Hándicap de sets',
        'Total de sets',
        'Tie-break',
      ]) {
        expect(find.text(title), findsOneWidget, reason: title);
      }
      expect(find.text('7'), findsOneWidget);
      expect(find.text('Abiertos 0 · Resueltos 1'), findsNWidgets(2));
      await tester.tap(find.text('Juegos totales'));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('Tasa de acierto'), findsOneWidget);
      expect(find.text('Hoy (0)'), findsOneWidget);
      await tester.tap(find.text('Anteriores'));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('Acertó'), findsOneWidget);
      expect(find.text('Miami Heat'), findsOneWidget);
      expect(find.text('New York Knicks'), findsOneWidget);
      expect(find.text('—'), findsOneWidget); // sin cuota: nunca un @ inventado
    },
  );

  testWidgets('feed caído: aviso y Reintentar solo en su hueco', (
    tester,
  ) async {
    var retries = 0;
    await pump(
      tester,
      predictions(
        SportKind.nba,
        const SportFeed(ready: false, events: []),
        onRetry: () async => retries++,
      ),
    );
    expect(
      find.text('No se pudieron cargar los datos de este deporte.'),
      findsOneWidget,
    );
    await tester.tap(find.text('Reintentar'));
    expect(retries, 1);
    await pump(
      tester,
      markets(
        SportKind.nba,
        const SportFeed(ready: false, events: []),
        onRetry: () async => retries++,
      ),
    );
    expect(find.text('Reintentar'), findsOneWidget);
  });

  testWidgets(
    'Predicciones y Mercados rotulan la ventana de resueltos sobre la que se calcula',
    (tester) async {
      final feed = SportFeed(
        ready: true,
        events: [
          ev(
            '1',
            [
              mk('a', market: 'winner', outcome: 'win'),
              mk('b', market: 'winner', outcome: 'loss'),
              mk('c', market: 'winner', outcome: 'win'),
              mk('d', market: 'winner', outcome: 'win', eligible: false),
            ],
            serverFeatured: true,
            featuredId: 'a',
          ),
        ],
      );
      await pump(tester, predictions(SportKind.nba, feed));
      expect(find.text('Sobre los últimos 3 resueltos'), findsOneWidget);
      await pump(tester, markets(SportKind.nba, feed));
      expect(find.text('Sobre los últimos 1 resueltos'), findsOneWidget);
    },
  );

  test('la regla del servidor manda: publicable (NBA) y publicables (tenis); sin ella, la banda de respaldo', () async {
    await AppLocale.instance.select('es');
    final l10n = AppLocale.instance.l10n;
    SportMarket nba(String id, bool? flag, {double p = .7}) => SportMarket(
      id: id,
      label: 'L',
      selection: 's',
      probability: p,
      sealedAt: DateTime.utc(2026, 10, 30, 10),
      eligible: true,
      market: 'game_total',
      line: 200,
      outcome: 'win',
      publishable: flag,
    );
    final feed = SportFeed(
      ready: true,
      events: [
        ev(
          '1',
          [
            nba('si', true, p: .5),
            nba('no', false, p: .9),
            nba('sin-regla', null),
          ],
          serverFeatured: true,
          featuredId: 'no',
        ),
      ],
    );
    final total = familyPicks(
      l10n,
      SportKind.nba,
      feed,
    ).firstWhere((f) => f.family == 'game_total');
    expect(total.settled.map((p) => p.$2.id), [
      'no',
    ]); // El historial conserva el destacado, independiente de la regla actual.

    final quotes = QuotesOverlay.fromJson(SportKind.tennis, {
      'state': 'partial',
      'events': <String, dynamic>{},
      'publicables': {
        't': ['games_total-2'],
      },
    });
    expect(quotes.publishes('t', 'games_total-2'), isTrue);
    expect(quotes.publishes('t', 'winner'), isFalse);
    expect(quotes.publishes('otro', 'winner'), isFalse);
    expect(QuotesOverlay.empty.publishes('t', 'winner'), isNull);
    final tennis = SportFeed(
      ready: true,
      events: [
        ev(
          't',
          [mk('winner', outcome: 'win'), mk('games_total-2', outcome: 'win')],
          sport: SportKind.tennis,
          serverFeatured: true,
          featuredId: 'games_total-2',
        ),
      ],
    );
    final games = familyPicks(l10n, SportKind.tennis, tennis, quotes);
    expect(games.firstWhere((f) => f.family == 'games_total').resolved, 1);
    expect(games.firstWhere((f) => f.family == 'winner').resolved, 0);
  });
}
