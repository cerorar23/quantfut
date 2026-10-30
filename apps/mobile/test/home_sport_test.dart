// Inicio de NBA y tenis: destacado, agenda con miniaturas, jugadores con pronóstico (NBA),
// crédito de fotos (tenis), aviso de feed caído solo en su deporte y agrupación por día local.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/home_agenda.dart';
import 'package:gobet/product/home_hero.dart';
import 'package:gobet/product/home_sport.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/sport_images.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

// Cliente HTTP que responde 404 a todo: ninguna imagen real, el avatar cae a iniciales.
class _Client404 implements HttpClient {
  @override
  dynamic noSuchMethod(Invocation i) {
    if (i.memberName == #getUrl || i.memberName == #openUrl) {
      return Future<HttpClientRequest>.value(_Req404());
    }
    return null;
  }
}

class _Req404 implements HttpClientRequest {
  @override
  final headers = _Headers();
  @override
  Future<HttpClientResponse> close() => Future.value(_Res404());
  @override
  Future<HttpClientResponse> get done => close();
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

class _Headers implements HttpHeaders {
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

class _Res404 extends Stream<List<int>> implements HttpClientResponse {
  @override
  int get statusCode => 404;
  @override
  int get contentLength => 0;
  @override
  HttpClientResponseCompressionState get compressionState =>
      HttpClientResponseCompressionState.notCompressed;
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => const Stream<List<int>>.empty().listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

JsonMap fixture(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as JsonMap;

final api = QuantFutApi(base: Uri.parse('https://x.test'));

SportMarket market(
  String id,
  double p, {
  String market = 'winner',
  String selection = 'Home',
  String? player,
  String? playerId,
  double? line,
}) => SportMarket(
  id: id,
  label: id,
  selection: selection,
  probability: p,
  sealedAt: DateTime.utc(2020),
  eligible: true,
  market: market,
  player: player,
  playerId: playerId,
  line: line,
);

SportEvent event(
  String id,
  DateTime start,
  List<SportMarket> markets, {
  SportKind sport = SportKind.nba,
  String home = 'Miami Heat',
  String away = 'New York Knicks',
  String league = 'NBA',
  String status = 'scheduled',
}) => SportEvent(
  id: id,
  sport: sport,
  home: home,
  away: away,
  league: league,
  start: start.toUtc(),
  status: status,
  seal: 'abc',
  sealedAt: DateTime.utc(2020),
  markets: markets,
);

Future<void> pump(
  WidgetTester tester, {
  required SportKind sport,
  required SportFeed feed,
  ImageCatalog images = ImageCatalog.empty,
  ValueChanged<SportEvent>? onOpen,
  Future<void> Function()? onRetry,
  DateTime? now,
  Size size = const Size(390, 2400),
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
        body: HomeSport(
          api: api,
          sport: sport,
          feed: feed,
          images: images,
          now: now,
          onOpen: onOpen ?? (_) {},
          onRetry: onRetry ?? () async {},
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

Iterable<String?> avatarUrls(WidgetTester tester) =>
    tester.widgetList<QfAvatar>(find.byType(QfAvatar)).map((a) => a.url);

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

  test('tabla NBA: 30 siglas únicas y cada nombre completo da la suya', () {
    const expected = {
      'ATL', 'BKN', 'BOS', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', //
      'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
      'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS',
    };
    expect(nbaTeams.length, 30);
    expect(nbaTeams.keys.toSet(), expected);
    expect(nbaTeams.values.toSet().length, 30);
    for (final MapEntry(:key, :value) in nbaTeams.entries) {
      expect(nbaTricode(value), key, reason: value);
    }
  });

  test('siglas NBA por nombre completo o corto; desconocido sin sigla', () {
    expect(nbaTricode('New York Knicks'), 'NYK');
    expect(nbaTricode('  new york   KNICKS '), 'NYK');
    expect(nbaTricode('Knicks'), 'NYK');
    expect(nbaTricode('LA Clippers'), 'LAC');
    expect(nbaTricode('Philadelphia 76ers'), 'PHI');
    expect(nbaTricode('Equipo Raro'), isNull);
  });

  testWidgets('NBA muestra logos en la agenda y fotos en jugadores', (tester) async {
    await HttpOverrides.runZoned(() async {
      final real = nbaEvents(fixture('nba_feed.json'));
      final knicks = event('kn', DateTime(2026, 10, 30, 19), [
        market('winner', .64, selection: 'New York Knicks'),
        market(
          'pts',
          .71,
          market: 'player_points',
          selection: 'Jalen Brunson',
          player: 'Jalen Brunson',
          playerId: '1628973',
          line: 24.5,
        ),
      ]);
      final images = ImageCatalog.fromManifest({
        'nba': {
          for (final k in ['NYK', 'MIA', 'ATL', 'CLE']) k: {'f': '$k.png'},
        },
      });
      await pump(
        tester,
        sport: SportKind.nba,
        feed: SportFeed(ready: true, events: [...real, knicks]),
        images: images,
        now: DateTime(2026, 10, 29),
      );
      final urls = avatarUrls(tester).toList();
      expect(urls, contains('https://x.test/web/imagenes/nba/NYK.png'));
      expect(urls, contains('https://x.test/web/imagenes/nba/ATL.png'));
      expect(urls, contains('https://x.test/web/imagenes/jugadores/nba/1628973.png'));
      expect(find.text('JUGADORES CON PRONÓSTICO'), findsOneWidget);
      expect(find.text('Más de 24,5'), findsWidgets);
      // Sin logo en el catálogo: iniciales, nunca otra imagen.
      expect(urls.where((u) => u != null && u.contains('SAC')), isEmpty);
      await tester.pump(const Duration(milliseconds: 50));
      expect(find.byIcon(Icons.broken_image), findsNothing);
      expect(tester.takeException(), isNull);
    }, createHttpClient: (c) => _Client404());
  });

  testWidgets('tenis muestra foto y bandera, y el crédito al pie', (tester) async {
    await HttpOverrides.runZoned(() async {
      final events = tennisEvents(fixture('tennis_feed.json'));
      final images = ImageCatalog.fromManifest({
        'tenis': {
          'liudmila samsonova': {'f': 'liudmila-samsonova.jpg', 'a': 'X', 'l': 'CC BY-SA 4.0'},
        },
      });
      await pump(
        tester,
        sport: SportKind.tennis,
        feed: SportFeed(ready: true, events: events),
        images: images,
        now: DateTime(2026, 10, 23),
      );
      final photo = tester
          .widgetList<QfAvatar>(find.byType(QfAvatar))
          .where((a) => a.url == 'https://x.test/web/imagenes/tenis/liudmila-samsonova.jpg');
      expect(photo, isNotEmpty);
      expect(photo.first.shape, AvatarShape.circle);
      // Sin foto en el catálogo: iniciales (la foto de 404 también cae a iniciales).
      expect(find.text('HW'), findsWidgets);
      // El feed de tenis no trae país: no se inventa bandera.
      expect(find.byWidgetPredicate((w) => w.key is ValueKey && '${(w.key as ValueKey).value}'.startsWith('qf-flag-')), findsNothing);
      // Encabezado del torneo y crédito CC BY-SA al pie.
      expect(find.text(events.first.league), findsOneWidget);
      expect(
        find.text('Fotos: Wikimedia Commons (CC BY-SA). Autores en la ficha de cada partido.'),
        findsOneWidget,
      );
    }, createHttpClient: (c) => _Client404());
  });

  testWidgets('feed NBA caído: aviso y reintento solo en NBA', (tester) async {
    var retries = 0;
    await pump(
      tester,
      sport: SportKind.nba,
      feed: const SportFeed(ready: false, events: []),
      onRetry: () async => retries++,
    );
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('sport-feed-retry')));
    await tester.pump();
    expect(retries, 1);
    expect(find.byType(HomeHero), findsNothing);
  });

  // Zona fija, independiente de la de la máquina (en CI suele ser UTC).
  DateTime Function(DateTime) zone(int hours) =>
      (d) => d.toUtc().add(Duration(hours: hours));

  test('partido 23:30 local del día 30 que en UTC es el 31 se agrupa el 30 (UTC-6)', () {
    // 23:30 del 30 en UTC-6 = 05:30 UTC del 31.
    final late = event('late', DateTime.utc(2026, 10, 31, 5, 30), [market('w', .6)]);
    final early = event('early', DateTime.utc(2026, 10, 31, 1), [market('w', .6)]); // 19:00 del 30
    final next = event('next', DateTime.utc(2026, 10, 31, 7), [market('w', .6)]); // 01:00 del 31
    final days = groupSportAgenda([late, next, early], toLocal: zone(-6));
    expect(days.map((d) => d.key).toList(), ['2026-10-30', '2026-10-31']);
    expect(days.first.groups.expand((g) => g.events).map((e) => e.id), ['early', 'late']);
    // NBA: un grupo por hora local.
    expect(days.first.groups.map((g) => g.hour?.hour), [19, 23]);
    // Con agrupación en UTC los tres caerían el 31: la prueba lo distingue en cualquier máquina.
    expect(groupSportAgenda([late, next, early], toLocal: zone(0)).map((d) => d.key), [
      '2026-10-31',
    ]);
  });

  test('por delante de UTC (UTC+9): las 08:00 del 31 (23:00 UTC del 30) van el 31', () {
    final morning = event('m', DateTime.utc(2026, 10, 30, 23), [market('w', .6)]);
    final days = groupSportAgenda([morning], toLocal: zone(9));
    expect(days.single.key, '2026-10-31');
    expect(days.single.groups.single.hour?.hour, 8);
  });

  // Camino real (zona de la máquina): la tira cuenta por día local.
  testWidgets('partido 23:30 local del día 30 se cuenta el 30 en la tira', (
    tester,
  ) async {
    await pump(
      tester,
      sport: SportKind.nba,
      feed: SportFeed(
        ready: true,
        events: [event('late', DateTime(2026, 10, 30, 23, 30), [market('w', .6)])],
      ),
      now: DateTime(2026, 10, 30, 8),
    );
    final strip = tester.widget<DayStrip>(find.byType(DayStrip));
    expect(strip.counts, {'2026-10-30': 1});
  });

  test('tenis se agrupa por torneo dentro del día', () {
    final a = event('a', DateTime(2026, 10, 30, 10), [market('w', .6)],
        sport: SportKind.tennis, league: 'ATP Paris');
    final b = event('b', DateTime(2026, 10, 30, 11), [market('w', .6)],
        sport: SportKind.tennis, league: 'WTA Tokyo');
    final c = event('c', DateTime(2026, 10, 30, 12), [market('w', .6)],
        sport: SportKind.tennis, league: 'ATP Paris');
    final days = groupSportAgenda([a, b, c]);
    expect(days.single.groups.map((g) => g.tournament), ['ATP Paris', 'WTA Tokyo']);
    expect(days.single.groups.first.events.map((e) => e.id), ['a', 'c']);
  });

  testWidgets('el destacado abre el partido', (tester) async {
    SportEvent? opened;
    final now = DateTime(2026, 10, 30, 8);
    final low = event('low', DateTime(2026, 10, 30, 19), [market('w', .62)]);
    final best = event('best', DateTime(2026, 10, 30, 21), [
      market('w', .58),
      market('t', .81, market: 'game_total', selection: 'Total', line: 221.5),
    ], home: 'Boston Celtics', away: 'Los Angeles Lakers');
    // Terminado o en juego: no pueden ser el destacado aunque tengan más probabilidad.
    final done = event('done', DateTime(2026, 10, 30, 7), [market('w', .95)],
        status: 'finished');
    final live = event('live', DateTime(2026, 10, 30, 9), [market('w', .93)],
        status: 'live');
    await pump(
      tester,
      sport: SportKind.nba,
      feed: SportFeed(ready: true, events: [low, best, done, live]),
      now: now,
      onOpen: (e) => opened = e,
    );
    expect(find.byType(HomeHero), findsOneWidget);
    expect(
      find.descendant(of: find.byType(HomeHero), matching: find.text('81 %')),
      findsOneWidget,
    );
    await tester.tap(find.byType(HomeHero));
    expect(opened?.id, 'best');
    // Una fila de la agenda también abre su partido.
    await tester.tap(find.byKey(const ValueKey('sport-event-low')));
    expect(opened?.id, 'low');
  });

  for (final code in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('Inicio NBA y tenis sin desbordes a 320 px ($code)', (tester) async {
      final nba = nbaEvents(fixture('nba_feed.json'));
      final tennis = tennisEvents(fixture('tennis_feed.json'));
      for (final (sport, events) in [(SportKind.nba, nba), (SportKind.tennis, tennis)]) {
        await pump(
          tester,
          sport: sport,
          feed: SportFeed(ready: true, events: events),
          now: DateTime(2026, 10, 20),
          size: const Size(320, 1600),
          code: code,
        );
        expect(tester.takeException(), isNull, reason: '$code $sport');
      }
    });
  }
}
