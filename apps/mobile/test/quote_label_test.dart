// Cuota de referencia en NBA y tenis: solo del mercado, línea y lado mostrados; «—» si no hay;
// formato por idioma; una leyenda por ficha; sin desbordes a 320 dp; fútbol sin cuotas.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/home_sport.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/sport_detail.dart';
import 'package:gobet/product/sport_images.dart';
import 'package:gobet/product/sport_predictions.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';
import 'package:gobet/product/sports_quotes.dart';
import 'package:intl/intl.dart';

class _Api extends QuantFutApi {
  _Api() : super(base: Uri.parse('https://x.test'));
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async => throw const ApiFailure('sin datos', 404);
}

final api = _Api();
final sealed = DateTime.utc(2026, 10, 30, 10);
const asOf = '2026-10-30T09:00:00+00:00';

SportMarket mk(
  String id, {
  required String? market,
  required String selection,
  double? line,
  String? player,
  String? playerId,
  double p = .7,
}) => SportMarket(
  id: id,
  label: 'L $id',
  selection: selection,
  probability: p,
  sealedAt: sealed,
  eligible: true,
  market: market,
  player: player,
  playerId: playerId,
  rowPlayerId: playerId,
  line: line,
);

SportEvent nbaEvent() => SportEvent(
  id: 'E1',
  sport: SportKind.nba,
  home: 'Miami Heat',
  away: 'New York Knicks',
  league: 'NBA',
  start: DateTime.utc(2026, 11, 2, 19),
  status: 'scheduled',
  seal: 'abc',
  sealedAt: sealed,
  markets: [
    mk('w', market: 'winner', selection: 'Miami Heat', p: .8),
    mk('t', market: 'game_total', selection: 'Total', line: 224.5, p: .6),
    mk('p', market: 'player_points', selection: 'Ana', line: 24.5, player: 'Ana', playerId: 'p9', p: .65),
  ],
);

SportEvent tennisEvent() => SportEvent(
  id: 'E2',
  sport: SportKind.tennis,
  home: 'Liudmila Samsonova',
  away: 'Heather Watson',
  league: 'WTA',
  start: DateTime.utc(2026, 11, 2, 19),
  status: 'scheduled',
  seal: 'abc',
  sealedAt: sealed,
  markets: [
    mk('winner', market: null, selection: 'Liudmila Samsonova', p: .82),
    mk('games_total-2', market: null, selection: 'Más de 21,5', p: .6),
  ],
);

Map<String, Object> q(double price, String book) => {
  'price': price,
  'book': book,
  'as_of': asOf,
  'books': 3,
};

/// Ganador local 1,62 (draftkings); total 224.5 SOLO el lado `under`; puntos de Ana 24.5 over 1,90.
QuotesOverlay nbaOverlay() => QuotesOverlay.fromJson(SportKind.nba, {
  'state': 'ok',
  'events': {
    'E1': {
      'cohort': 'abc',
      'quotes': {
        'winner||': {'home': q(1.62, 'draftkings')},
        'game_total||224.5': {'under': q(1.89, 'fanduel')},
        'player_points|p9|24.5': {'over': q(1.9, 'fanduel')},
      },
    },
  },
});

QuotesOverlay tennisOverlay() => QuotesOverlay.fromJson(SportKind.tennis, {
  'state': 'ok',
  'events': {
    'E2': {'winner': q(1.21, 'pinnacle')},
  },
});

String hhmm() => localDate(DateFormat.Hm, DateTime.parse(asOf).toLocal());

Future<void> pump(
  WidgetTester tester,
  Widget body, {
  String code = 'es',
  Size size = const Size(390, 2400),
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
      home: Scaffold(body: body),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

Widget predictions(SportKind sport, List<SportEvent> events, QuotesOverlay quotes) =>
    SportPredictions(
      api: api,
      sport: sport,
      feed: SportFeed(ready: true, events: events),
      images: ImageCatalog.empty,
      quotes: quotes,
      onOpen: (_) {},
      now: DateTime(2020),
    );

Widget sheet(SportEvent e, QuotesOverlay quotes) =>
    SportDetail(api: api, event: e, images: ImageCatalog.empty, quotes: quotes);

Widget home(QuotesOverlay quotes) => HomeSport(
  api: api,
  sport: SportKind.nba,
  feed: SportFeed(ready: true, events: [nbaEvent()]),
  images: ImageCatalog.empty,
  quotes: quotes,
  now: DateTime(2026, 10, 30, 12),
  onOpen: (_) {},
  onRetry: () async {},
);

Iterable<String> texts(WidgetTester tester) => [
  for (final t in tester.widgetList<Text>(find.byType(Text))) t.data ?? t.textSpan?.toPlainText() ?? '',
];

Finder inCard(String key, Finder f) =>
    find.descendant(of: find.byKey(ValueKey(key)), matching: f);

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

  testWidgets('Predicciones NBA: cuota y casa solo en SU mercado; otro lado -> «—»', (tester) async {
    await pump(tester, predictions(SportKind.nba, [nbaEvent()], nbaOverlay()));
    expect(inCard('sport-pick-E1-w', find.text('@1,62')), findsOneWidget);
    expect(inCard('sport-pick-E1-w', find.text('draftkings · ${hhmm()}')), findsOneWidget);
    expect(inCard('sport-pick-E1-p', find.text('@1,90')), findsOneWidget);
    // El overlay solo trae `under` del total: «Más de» no recibe ese precio.
    expect(inCard('sport-pick-E1-t', find.text('—')), findsOneWidget);
    expect(inCard('sport-pick-E1-t', find.textContaining('@')), findsNothing);
    expect(texts(tester).where((t) => t.contains('1,89')), isEmpty);
    expect(
      find.byWidgetPredicate((w) => w is Semantics && w.properties.label == 'Sin cuota'),
      findsOneWidget,
    );
    // La probabilidad sigue siendo visible.
    expect(inCard('sport-pick-E1-t', find.text('60 %')), findsOneWidget);
  });

  testWidgets('sin overlay: «—» y jamás un @ en NBA y tenis', (tester) async {
    await pump(tester, predictions(SportKind.nba, [nbaEvent()], QuotesOverlay.empty));
    expect(find.text('—'), findsNWidgets(3));
    expect(texts(tester).where((t) => t.contains('@')), isEmpty);
    await pump(tester, predictions(SportKind.tennis, [tennisEvent()], QuotesOverlay.empty));
    expect(find.text('—'), findsNWidgets(2));
    expect(texts(tester).where((t) => t.contains('@')), isEmpty);
  });

  testWidgets('tenis: cuota por id de mercado; el otro mercado queda en «—»', (tester) async {
    await pump(tester, predictions(SportKind.tennis, [tennisEvent()], tennisOverlay()));
    expect(inCard('sport-pick-E2-winner', find.text('@1,21')), findsOneWidget);
    expect(inCard('sport-pick-E2-winner', find.text('pinnacle · ${hhmm()}')), findsOneWidget);
    expect(inCard('sport-pick-E2-games_total-2', find.text('—')), findsOneWidget);
  });

  testWidgets('el formato decimal sigue el idioma: 1,62 en es y 1.62 en en', (tester) async {
    await pump(tester, predictions(SportKind.nba, [nbaEvent()], nbaOverlay()), code: 'en');
    expect(find.text('@1.62'), findsOneWidget);
    expect(find.text('@1,62'), findsNothing);
  });

  testWidgets('ficha NBA: cuotas por fila y UNA sola leyenda de referencia', (tester) async {
    await pump(tester, sheet(nbaEvent(), nbaOverlay()));
    expect(find.text('@1,62'), findsOneWidget);
    expect(find.text('@1,90'), findsOneWidget);
    expect(find.text('—'), findsOneWidget);
    expect(
      find.text('Cuota de referencia de la captura usada al sellar el pronóstico'),
      findsOneWidget,
    );
  });

  testWidgets('ficha sin cuotas: «—» en cada fila y la leyenda sigue una vez', (tester) async {
    await pump(tester, sheet(nbaEvent(), QuotesOverlay.empty));
    expect(find.text('—'), findsNWidgets(3));
    expect(texts(tester).where((t) => RegExp(r'@\s*\d').hasMatch(t)), isEmpty);
    expect(
      find.text('Cuota de referencia de la captura usada al sellar el pronóstico'),
      findsOneWidget,
    );
  });

  testWidgets('Inicio NBA: la tarjeta de jugador muestra su cuota «Más de»', (tester) async {
    await pump(tester, home(nbaOverlay()));
    expect(find.text('@1,90'), findsOneWidget);
    expect(find.text('fanduel · ${hhmm()}'), findsOneWidget);
  });

  test('fútbol: el overlay siempre queda vacío (no hay cuotas de referencia)', () {
    expect(
      QuotesOverlay.fromJson(SportKind.football, {
        'state': 'ok',
        'events': {'E1': {}},
      }).isEmpty,
      isTrue,
    );
  });

  for (final code in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('cuotas sin desbordes a 320 dp ($code)', (tester) async {
      const size = Size(320, 2000);
      final overlay = QuotesOverlay.fromJson(SportKind.nba, {
        'state': 'ok',
        'events': {
          'E1': {
            'cohort': 'abc',
            'quotes': {
              'winner||': {'home': q(10.5, 'Casa con un nombre larguísimo')},
              'game_total||224.5': {'over': q(1.89, 'fanduel')},
              'player_points|p9|24.5': {'over': q(1.9, 'fanduel')},
            },
          },
        },
      });
      await pump(tester, predictions(SportKind.nba, [nbaEvent()], overlay), code: code, size: size);
      expect(tester.takeException(), isNull, reason: 'predicciones $code');
      await pump(tester, sheet(nbaEvent(), overlay), code: code, size: size);
      expect(tester.takeException(), isNull, reason: 'ficha $code');
      await pump(tester, home(overlay), code: code, size: size);
      expect(tester.takeException(), isNull, reason: 'inicio $code');
    });
  }
}
