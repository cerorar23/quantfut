// Ficha de partido de NBA y tenis: pestañas, estadísticas que pueden faltar (404),
// disponibilidad con insignia + texto y crédito de las fotos de tenis.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_shapes.dart';
import 'package:gobet/product/sport_detail.dart';
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

/// API falsa: responde las rutas dadas y 404 al resto (como el servidor sin estadísticas).
class _Api extends QuantFutApi {
  _Api([this.routes = const {}]) : super(base: Uri.parse('https://x.test'));
  final Map<String, JsonMap> routes;
  final paths = <String>[];
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    paths.add(path);
    final r = routes[path];
    if (r == null) throw const ApiFailure('Sin estadísticas', 404);
    return r;
  }
}

SportMarket market(
  String id,
  double p, {
  String? market = 'winner',
  String selection = 'Miami Heat',
  String label = 'Ganador',
  String? player,
  String? playerId,
  double? line,
  bool eligible = true,
}) => SportMarket(
  id: id,
  label: label,
  selection: selection,
  probability: p,
  sealedAt: DateTime.utc(2026, 10, 30, 12),
  eligible: eligible,
  market: market,
  player: player,
  playerId: playerId,
  line: line,
);

List<SportMarket> nbaMarkets() => [
  market('w', .62, selection: 'Dallas Mavericks'),
  market(
    't',
    .55,
    market: 'game_total',
    selection: 'Total',
    label: 'Total del partido',
    line: 224.5,
  ),
  market(
    'p',
    .68,
    market: 'player_points',
    selection: 'Luka Doncic',
    label: 'Puntos de jugador',
    player: 'Luka Doncic',
    playerId: '1629029',
    line: 28.5,
  ),
];

SportEvent nbaEvent({JsonMap? availability, List<SportMarket>? markets}) =>
    SportEvent(
      id: '0022600021',
      sport: SportKind.nba,
      home: 'Dallas Mavericks',
      away: 'Houston Rockets',
      league: 'NBA',
      start: DateTime.utc(2026, 10, 31, 0),
      status: 'scheduled',
      seal: '9f3a1234567890c21e',
      sealedAt: DateTime.utc(2026, 10, 30, 12),
      availability: availability,
      markets: markets ?? nbaMarkets(),
    );

SportEvent tennisEvent() => SportEvent(
  id: '12173711',
  sport: SportKind.tennis,
  home: 'Liudmila Samsonova',
  away: 'Heather Watson',
  league: 'WTA · Tokyo',
  surface: 'Clay',
  start: DateTime.utc(2026, 10, 24, 1, 30),
  status: 'scheduled',
  seal: 'd14cc5f14aaa98a086368f33ff6ee4082aeeecef77c54fe092c89c2271fbee99',
  sealedAt: DateTime.utc(2026, 10, 23, 10, 30),
  markets: [
    market(
      'winner',
      .82,
      market: null,
      selection: 'Liudmila Samsonova',
      label: 'Ganador del partido',
    ),
  ],
);

final catalog = ImageCatalog.fromManifest({
  'tenis': {
    'Liudmila Samsonova': {
      'f': 'liudmila-samsonova.jpg',
      'a': 'Autora Uno',
      'l': 'CC BY-SA 4.0',
      'p': 'https://commons.wikimedia.org/wiki/File:Samsonova.jpg',
    },
    'Heather Watson': {
      'f': 'heather-watson.jpg',
      'a': 'Autor Dos',
      'l': 'CC BY-SA 2.0',
      'p': 'https://commons.wikimedia.org/wiki/File:Watson.jpg',
    },
  },
  'nba': {
    'DAL': {'f': 'DAL.png'},
    'HOU': {'f': 'HOU.png'},
  },
});

Future<void> pump(
  WidgetTester tester,
  SportEvent event, {
  _Api? api,
  ImageCatalog images = ImageCatalog.empty,
}) async {
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
      home: Scaffold(
        body: SportDetail(api: api ?? _Api(), event: event, images: images),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

Future<void> openTab(WidgetTester tester, String label) async {
  await tester.tap(find.text(label));
  // Dos cuadros: el FutureBuilder resuelve un futuro ya completo en el siguiente.
  await tester.pump(const Duration(milliseconds: 100));
  await tester.pump(const Duration(milliseconds: 100));
}

Iterable<String> texts(WidgetTester tester) => [
  for (final t in tester.widgetList<Text>(find.byType(Text)))
    t.data ?? t.textSpan?.toPlainText() ?? '',
];

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
      'Rajdhani': 'fonts/Rajdhani-Bold.ttf',
      'JetBrains Mono': 'fonts/JetBrainsMono-Medium.ttf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('estadísticas 404: Análisis avisa y Pronósticos sigue', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      final api = _Api();
      await pump(tester, nbaEvent(), api: api);
      expect(api.paths, ['/web/deportes/nba/estadisticas/0022600021']);
      // Pronósticos funciona: ganador, total, jugador con «Más de» y sello.
      expect(find.textContaining('Dallas Mavericks'), findsWidgets);
      expect(find.textContaining('Más de 224,5'), findsOneWidget);
      expect(find.textContaining('Luka Doncic · Más de 28,5'), findsOneWidget);
      expect(find.byType(SealLine), findsOneWidget);
      await openTab(tester, 'Análisis');
      expect(
        find.text('Aún no hay estadísticas para este partido.'),
        findsOneWidget,
      );
      // H2H sin datos: mensaje neutro existente; el resto de la ficha sigue.
      await openTab(tester, 'H2H');
      expect(
        find.text('No hay enfrentamientos registrados para este partido.'),
        findsOneWidget,
      );
      await openTab(tester, 'Pronósticos');
      expect(find.textContaining('Más de 224,5'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('NBA con estadísticas: Análisis por equipo y H2H por nombre', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      final api = _Api({
        '/web/deportes/nba/estadisticas/0022600021': fixture('nba_stats.json'),
      });
      await pump(tester, nbaEvent(), api: api);
      await openTab(tester, 'Análisis');
      expect(find.text('Dallas Mavericks'), findsWidgets);
      expect(find.text('Temporada'), findsWidgets);
      await openTab(tester, 'H2H');
      expect(find.textContaining('Houston Rockets 128'), findsWidgets);
      expect(find.textContaining('Dallas Mavericks 110'), findsWidgets);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('tenis muestra el crédito de cada foto usada', (tester) async {
    await HttpOverrides.runZoned(() async {
      await pump(tester, tennisEvent(), images: catalog);
      expect(find.textContaining('Autora Uno'), findsOneWidget);
      expect(find.textContaining('CC BY-SA 4.0'), findsOneWidget);
      expect(find.textContaining('Autor Dos'), findsOneWidget);
      expect(find.textContaining('CC BY-SA 2.0'), findsOneWidget);
      expect(find.textContaining('File:Samsonova.jpg'), findsOneWidget);
      // Superficie conocida en texto, no solo el valor del feed.
      expect(find.text('ARCILLA'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('tenis sin foto en el catálogo no inventa crédito', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      await pump(tester, tennisEvent());
      expect(find.textContaining('CC BY-SA'), findsNothing);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('tenis: Análisis, H2H y Alertas con estadísticas', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      final api = _Api({
        '/web/deportes/tenis/estadisticas/12173711': fixture(
          'tennis_stats.json',
        ),
      });
      await pump(tester, tennisEvent(), api: api);
      await openTab(tester, 'Análisis');
      expect(find.text('Heather Watson'), findsWidgets);
      expect(find.text('Ranking'), findsWidgets);
      await openTab(tester, 'H2H');
      expect(find.textContaining('WTA Cincinnati'), findsOneWidget);
      await openTab(tester, 'Alertas');
      expect(find.text('Sin avisos para este partido.'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('NBA lista disponibilidad con insignia y texto, no solo color', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      await pump(
        tester,
        nbaEvent(
          availability: {
            'state': 'reporte_aplicado',
            'listed': 12,
            'used': 10,
            'missing_minutes_home': 66.0,
            'missing_minutes_away': 107.1,
            'report_timestamp_utc': '2026-10-30T22:45:00+00:00',
            'teams_not_submitted': ['Houston Rockets'],
          },
        ),
      );
      await openTab(tester, 'Alertas');
      expect(find.text('REPORTE DE LESIONES APLICADO'), findsOneWidget);
      expect(find.text('12 jugadores en el reporte'), findsOneWidget);
      expect(find.text('Houston Rockets no envió su reporte'), findsOneWidget);
      // Cada estado lleva icono además de texto.
      final badge = tester.widget<QfBadge>(
        find.ancestor(
          of: find.text('REPORTE DE LESIONES APLICADO'),
          matching: find.byType(QfBadge),
        ),
      );
      expect(badge.icon, isNotNull);
      expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('NBA sin disponibilidad: mensaje neutro en Alertas', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      await pump(tester, nbaEvent());
      await openTab(tester, 'Alertas');
      expect(find.text('Sin avisos para este partido.'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('cabecera NBA «VIS @ LOC»; nunca texto de precio con @', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      await pump(tester, nbaEvent(), images: catalog);
      expect(find.text('HOU @ DAL'), findsOneWidget);
      for (final t in texts(tester)) {
        expect(RegExp(r'@\s*\d').hasMatch(t), isFalse, reason: t);
      }
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('mercados no elegibles (sellados tras el inicio) no se listan', (
    tester,
  ) async {
    await HttpOverrides.runZoned(() async {
      await pump(
        tester,
        nbaEvent(
          markets: [
            ...nbaMarkets(),
            market(
              'late',
              .9,
              market: 'player_points',
              selection: 'Jugador Tardio',
              player: 'Jugador Tardio',
              line: 10.5,
              eligible: false,
            ),
          ],
        ),
      );
      expect(find.textContaining('Jugador Tardio'), findsNothing);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('showSportDetail abre la hoja inferior', (tester) async {
    await HttpOverrides.runZoned(() async {
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
          home: Builder(
            builder: (context) => Scaffold(
              body: TextButton(
                onPressed: () => showSportDetail(
                  context,
                  api: _Api(),
                  event: nbaEvent(),
                  images: ImageCatalog.empty,
                ),
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('abrir'));
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.byType(SportDetail), findsOneWidget);
      expect(find.text('HOU @ DAL'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('el id del evento va codificado en la URL de estadísticas', (tester) async {
    await HttpOverrides.runZoned(() async {
      final api = _Api();
      final e = nbaEvent();
      await pump(
        tester,
        SportEvent(
          id: 'a b/c?d',
          sport: e.sport,
          home: e.home,
          away: e.away,
          league: e.league,
          start: e.start,
          status: e.status,
          seal: e.seal,
          sealedAt: e.sealedAt,
          markets: e.markets,
        ),
        api: api,
      );
      expect(api.paths, ['/web/deportes/nba/estadisticas/a%20b%2Fc%3Fd']);
    }, createHttpClient: (_) => _Client404());
  });

  testWidgets('una superficie desconocida no se muestra en crudo; las conocidas, traducidas', (tester) async {
    await HttpOverrides.runZoned(() async {
      SportEvent withSurface(String s) {
        final e = tennisEvent();
        return SportEvent(
          id: e.id,
          sport: e.sport,
          home: e.home,
          away: e.away,
          league: e.league,
          surface: s,
          start: e.start,
          status: e.status,
          seal: e.seal,
          sealedAt: e.sealedAt,
          markets: e.markets,
        );
      }

      await pump(tester, withSurface('Carpet'));
      expect(find.text('Carpet'), findsNothing);
      await pump(tester, withSurface('Clay'));
      expect(find.text('Clay'), findsNothing);
      expect(find.text('ARCILLA'), findsOneWidget);
    }, createHttpClient: (_) => _Client404());
  });
}
