import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_profile.dart';
import 'package:gobet/product/live_shell.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_rewards.dart';
import 'package:gobet/product/live_vip.dart';
import 'package:gobet/product/live_forecast.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/sport_selector.dart';
import 'package:gobet/product/sports.dart';

class FixtureApi extends QuantFutApi {
  Completer<void>? gate;
  bool fail = false;
  bool richDetail = false;
  bool detailLocked = false;
  JsonMap? wallet;
  List<JsonMap> detailPicks = [];
  List<JsonMap> extraAgenda = [];
  JsonMap? modelo, mercados;
  int homes = 0;
  final paths = <String>[];
  // Feeds de NBA y tenis; null: responde otra cosa y el feed queda «no listo».
  JsonMap? nbaFeed, tennisFeed;
  final flags = {
    for (final k in [
      'agenda',
      'alta_probabilidad',
      'escalera',
      'estadisticas',
      'h2h',
      'vip',
    ])
      k: {'enabled': true, 'message': 'Modelo en entrenamiento'},
  };
  JsonMap get config => {'features': flags};
  @override
  Future<JsonMap> home(DateTime date) async {
    homes++;
    if (gate != null) await gate!.future;
    if (fail) throw const ApiFailure('Sin conexión');
    return {
      'config': config,
      'rewards': {'enabled': true, 'unlock_cost': 100},
      'plans': [
        {
          'name': 'Plus 1 mes',
          'price_cents': 1499,
          'currency': 'USD',
          'duration_days': 30,
        },
      ],
      'agenda': [
        {
          'match_id': 'test-1',
          'kickoff_utc': DateTime.now()
              .add(const Duration(hours: 2))
              .toUtc()
              .toIso8601String(),
          'local': {'nombre': 'Equipo A'},
          'visitante': {'nombre': 'Equipo B'},
          'liga': {'nombre': 'Liga de prueba'},
          'probabilities': {'home': .6, 'draw': .25, 'away': .15},
        },
        ...extraAgenda,
      ],
      'alta_probabilidad': {
        'estado': 'activa',
        'historial': {
          'n': 20,
          'aciertos': 16,
          'acierto_real': 80,
          'por_mercado': {},
        },
        'proximos': [
          {
            'match_id': 'test-1',
            'pick_key': 'test-1',
            'local': 'Equipo A',
            'visitante': 'Equipo B',
            'texto': 'Más de 1,5 goles',
            'prob': .8,
            'ref_price': 1.5,
            'ref_book': 'Fuente de prueba',
            'free': true,
          },
        ],
        'vip': [
          {
            'match_id': 'test-2',
            'pick_key': 'test-2',
            'local': 'Equipo C',
            'visitante': 'Equipo D',
            'locked': true,
          },
        ],
      },
      'escalera': {'activo': true, 'actuales': []},
    };
  }

  @override
  Future<JsonMap> detail(String id) async => richDetail
      ? {
          ...jsonMap(
            jsonDecode(
              File('test/fixtures/match_statistics_real.json')
                  .readAsStringSync(),
            ),
          ),
          'config': config,
          'picks': detailPicks,
          'locked': detailLocked,
          if (modelo != null || mercados != null)
            'ficha': {
              ...jsonMap(
                jsonMap(
                  jsonDecode(
                    File('test/fixtures/match_statistics_real.json')
                        .readAsStringSync(),
                  ),
                )['ficha'],
              ),
              if (modelo != null) 'modelo': modelo,
              if (mercados != null) 'mercados': mercados,
            },
        }
      : {
          'config': config,
          'locked': id == 'test-2',
          'picks': [],
          'ficha': {
            'partido': {
              'liga': {'nombre': 'Liga de prueba'},
            },
            'local': {
              'nombre': 'Equipo A',
              'promedios': {
                'todos': {'n': 0},
              },
            },
            'visitante': {
              'nombre': 'Equipo B',
              'promedios': {
                'todos': {'n': 0},
              },
            },
            'cara_a_cara': {'partidos': []},
          },
        };
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    paths.add(path);
    if (path == '/nba/api/data' && nbaFeed != null) return nbaFeed;
    if (path == '/web/deportes/tenis' && tennisFeed != null) return tennisFeed;
    return _rewards;
  }

  JsonMap get _rewards => {
    'settings': {
      'enabled': true,
      'unlock_cost': 100,
      'attendance_coins': [30, 35, 35, 40, 40, 45, 50],
      'referrer_coins': 200,
      'invitee_coins': 100,
      'referral_min_coins': 100,
    },
    'signed_in': wallet != null,
    if (wallet != null) 'wallet': wallet,
    'providers': [
      {'name': 'BitLabs', 'provider': 'bitlabs', 'available': false},
    ],
    'ledger': [],
    'terms': 'Monedas sin valor monetario.',
  };
}

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
  final boundary = GlobalKey();
  Future<void> open(
    WidgetTester tester,
    Widget child, {
    double scale = 1,
    bool settle = true,
  }) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      RepaintBoundary(
        key: boundary,
        child: MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: AppLocale.instance.locale,

          theme: liveTheme(),
          debugShowCheckedModeBanner: false,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              disableAnimations: true,
              textScaler: TextScaler.linear(scale),
            ),
            child: child!,
          ),
          home: child,
        ),
      ),
    );
    if (settle) await tester.pumpAndSettle();
  }

  Future<void> capture(WidgetTester tester, String name) async {
    const destination = String.fromEnvironment('UI_CAPTURE_DIR');
    if (destination.isEmpty) return;
    await tester.runAsync(() async {
      final img =
          await (boundary.currentContext!.findRenderObject()!
                  as RenderRepaintBoundary)
              .toImage(pixelRatio: 1);
      final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
      await Directory(destination).create(recursive: true);
      await File('$destination/$name.png')
          .writeAsBytes(bytes!.buffer.asUint8List());
      img.dispose();
    });
  }

  Future<void> navigate(WidgetTester tester, String label) async {
    await tester.tap(
      find.descendant(
        of: find.byType(BottomNavigationBar),
        matching: find.text(label),
      ),
    );
    await tester.pumpAndSettle();
  }

  // El destacado del día ocupa la parte alta de Inicio: la agenda queda más abajo.
  Future<void> scrollToAgenda(WidgetTester tester) => tester.scrollUntilVisible(
    find.text('Equipo A'),
    200,
    scrollable: find
        .descendant(
          of: find.byKey(const ValueKey('home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first,
  );

  SportPrefs memoryPrefs([Map<String, String>? store]) {
    final map = store ?? <String, String>{};
    return SportPrefs(
      read: (k) async => map[k],
      write: (k, v) async => map[k] = v,
    );
  }

  Finder selectedMark(String id) => find.descendant(
    of: find.byKey(ValueKey('sport-$id')),
    matching: find.byKey(const ValueKey('sport-selected-mark')),
  );

  testWidgets('el selector aparece en Inicio, Predicciones y Mercados y no en Coins ni Perfil', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    for (final (label, shown) in [
      ('Inicio', true),
      ('Predicciones', true),
      ('Mercados', true),
      ('Coins', false),
      ('Perfil', false),
    ]) {
      await navigate(tester, label);
      expect(
        find.byType(SportSelector),
        shown ? findsOneWidget : findsNothing,
        reason: label,
      );
    }
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('en NBA el switcher solo muestra Alta prob.', (tester) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    await navigate(tester, 'Predicciones');
    expect(find.byKey(const ValueKey('streams-ladder')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('streams-high')), findsOneWidget);
    expect(find.byKey(const ValueKey('streams-ladder')), findsNothing);
    expect(find.byKey(const ValueKey('streams-parley')), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('cambiar de deporte no cambia de pestaña y se recuerda', (tester) async {
    final api = FixtureApi();
    final store = <String, String>{};
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs(store)));
    await navigate(tester, 'Predicciones');
    await tester.tap(find.byKey(const ValueKey('sport-tenis')));
    await tester.pumpAndSettle();
    expect(store['sports_last'], 'tenis');
    expect(find.byKey(const ValueKey('streams-switcher')), findsOneWidget);
    expect(selectedMark('tenis'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('al abrir se elige el último deporte guardado', (tester) async {
    final api = FixtureApi();
    await open(
      tester,
      ProductShell(api: api, sportPrefs: memoryPrefs({'sports_last': 'nba'})),
    );
    expect(selectedMark('nba'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('deslizar cambia de tipo, no de deporte', (tester) async {
    final api = FixtureApi();
    final store = <String, String>{};
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs(store)));
    await navigate(tester, 'Predicciones');
    final indicator = find.byKey(const ValueKey('streams-indicator'));
    final before = tester.getTopLeft(indicator).dx;
    await tester.fling(find.byType(RefreshIndicator), const Offset(-300, 0), 1500);
    await tester.pumpAndSettle();
    expect(tester.getTopLeft(indicator).dx, greaterThan(before + 50));
    expect(selectedMark('futbol'), findsOneWidget);
    expect(store.containsKey('sports_last'), isFalse);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  for (final code in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('a 360 dp las etiquetas del selector no se recortan ($code)', (tester) async {
      await AppLocale.instance.select(code);
      addTearDown(AppLocale.instance.reset);
      for (final active in SportKind.values) {
        await open(
          tester,
          Scaffold(
            body: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SportSelector(
                sports: SportKind.values,
                value: active,
                onChanged: (_) {},
              ),
            ),
          ),
        );
        addTearDown(tester.view.resetPhysicalSize);
        tester.view.physicalSize = const Size(360, 640);
        await tester.pumpAndSettle();
        for (final sport in SportKind.values) {
          final text = find.descendant(
            of: find.byKey(ValueKey('sport-${sport.id}')),
            matching: find.byType(Text),
          );
          final paragraph = tester.renderObject<RenderParagraph>(text.first);
          expect(paragraph.didExceedMaxLines, isFalse, reason: '$code $active ${sport.id}');
        }
      }
    });
  }
  testWidgets('si el fútbol falla, el selector sigue y NBA no muestra el error', (tester) async {
    final api = FixtureApi()..fail = true;
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    expect(find.byType(SportSelector), findsOneWidget);
    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pumpAndSettle();
    // El Inicio de NBA tiene su propio hueco: sin el error del fútbol.
    expect(find.byKey(const ValueKey('sport-home-nba')), findsOneWidget);
    expect(find.text('Sin conexión'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('sport-futbol')));
    await tester.pumpAndSettle();
    expect(find.text('Sin conexión'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('mientras carga el fútbol, el selector se ve y NBA se puede tocar', (tester) async {
    final api = FixtureApi()..gate = Completer<void>();
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()), settle: false);
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.byType(SportSelector), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pump();
    await tester.pump();
    expect(find.byKey(const ValueKey('sport-home-nba')), findsOneWidget);
    expect(find.byKey(const ValueKey('football-loading')), findsNothing);
    api.gate!.complete();
    await tester.pumpAndSettle();
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('feed NBA caído: aviso y reintento solo en NBA; fútbol y tenis siguen', (
    tester,
  ) async {
    // FixtureApi no sirve el feed NBA (responde otra cosa): loadSport lo da por no listo.
    final api = FixtureApi();
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    expect(api.paths.where((p) => p == '/nba/api/data'), isEmpty); // carga perezosa
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pumpAndSettle();
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsOneWidget);
    expect(api.paths.where((p) => p == '/nba/api/data').length, 1);
    await tester.tap(find.byKey(const ValueKey('sport-feed-retry')));
    await tester.pumpAndSettle();
    expect(api.paths.where((p) => p == '/nba/api/data').length, 2);
    await tester.tap(find.byKey(const ValueKey('sport-futbol')));
    await tester.pumpAndSettle();
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsNothing);
    await scrollToAgenda(tester);
    expect(find.text('Equipo A'), findsWidgets);
    // Volver a NBA no repite la petición: el estado se guarda por deporte.
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pumpAndSettle();
    expect(api.paths.where((p) => p == '/nba/api/data').length, 2);
    // Tenis carga su propio feed sin heredar el aviso de NBA.
    api.tennisFeed = jsonMap(
      jsonDecode(File('test/fixtures/tennis_feed.json').readAsStringSync()),
    );
    await tester.tap(find.byKey(const ValueKey('sport-tenis')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('home-sport-tenis')), findsOneWidget);
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsNothing);
    expect(find.byKey(const ValueKey('sport-feed-retry')), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('un refresco fallido conserva el feed NBA bueno', (tester) async {
    final soon = DateTime.now().add(const Duration(hours: 3)).toUtc().toIso8601String();
    final now = DateTime.now().toUtc().toIso8601String();
    final api = FixtureApi()
      ..nbaFeed = {
        'live_v13': {
          'cohorts': [
            {
              'cohort': 'c1',
              'created_at_utc': now,
              'events': [
                {
                  'event_id': 'g1',
                  'home_team': 'Miami Heat',
                  'away_team': 'New York Knicks',
                  'tipoff_utc': soon,
                  'status': 'scheduled',
                },
              ],
              'predictions': [
                {
                  'event_id': 'g1',
                  'player_id': 'winner',
                  'market': 'winner',
                  'market_label': 'Ganador',
                  'probability_over': .61,
                  'sealed_at_utc': now,
                  'result': {'status': 'pending'},
                },
              ],
            },
          ],
        },
      };
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    await tester.tap(find.byKey(const ValueKey('sport-nba')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('sport-event-g1')), findsOneWidget);
    api.nbaFeed = null; // el siguiente refresco falla
    await tester.tap(find.byIcon(Icons.refresh));
    await tester.pumpAndSettle();
    expect(api.paths.where((p) => p == '/nba/api/data').length, 2);
    expect(find.byKey(const ValueKey('sport-event-g1')), findsOneWidget);
    expect(find.text('No se pudieron cargar los datos de este deporte.'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('una lectura inicial tardía no pisa la elección del usuario', (tester) async {
    final api = FixtureApi();
    final read = Completer<String?>();
    final store = <String, String>{};
    final prefs = SportPrefs(
      read: (k) => k == 'sports_last' ? read.future : Future.value(store[k]),
      write: (k, v) async => store[k] = v,
    );
    await open(tester, ProductShell(api: api, sportPrefs: prefs), settle: false);
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('sport-tenis')));
    await tester.pump();
    read.complete('nba');
    await tester.pumpAndSettle();
    expect(selectedMark('tenis'), findsOneWidget);
    expect(selectedMark('nba'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('el menú abre Mis deportes en Perfil y ocultar el deporte actual lo cambia', (
    tester,
  ) async {
    final api = FixtureApi();
    final store = {'sports_last': 'nba'};
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs(store)));
    expect(selectedMark('nba'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('home-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('more-sports')));
    await tester.pumpAndSettle();
    final section = find.byKey(const ValueKey('my-sports'));
    expect(section, findsOneWidget);
    expect(tester.getTopLeft(section).dy, lessThan(844));
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-nba')));
    await tester.pumpAndSettle();
    expect(store['sports_hidden'], 'nba');
    await navigate(tester, 'Inicio');
    expect(find.byKey(const ValueKey('sport-nba')), findsNothing);
    expect(selectedMark('futbol'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('el foco de Mis deportes se consume: volver a Perfil lo abre arriba', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api, sportPrefs: memoryPrefs()));
    ScrollPosition profileScroll() => tester
        .state<ScrollableState>(
          find
              .descendant(
                of: find.byType(LiveProfileScreen),
                matching: find.byType(Scrollable),
              )
              .first,
        )
        .position;
    final title = find.text('Perfil y configuración');
    final section = find.byKey(const ValueKey('my-sports'));
    Future<void> viaMenu() async {
      await tester.tap(find.byKey(const ValueKey('home-menu')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('more-sports')));
      await tester.pumpAndSettle();
    }

    await viaMenu();
    // El menú desplaza: la sección queda arriba y el título del Perfil fuera de la vista.
    expect(profileScroll().pixels, greaterThan(0));
    expect(tester.getTopLeft(section).dy, lessThan(200));
    expect(title.hitTestable(), findsNothing);

    for (final other in ['Inicio', 'Coins']) {
      await navigate(tester, other);
      await navigate(tester, 'Perfil');
      expect(profileScroll().pixels, 0, reason: 'tras $other');
      expect(title.hitTestable(), findsOneWidget, reason: 'tras $other');
    }

    // Una petición nueva del menú vuelve a desplazar, también estando ya en Perfil.
    await viaMenu();
    expect(profileScroll().pixels, greaterThan(0));
    profileScroll().jumpTo(0);
    await tester.pump();
    await viaMenu();
    expect(profileScroll().pixels, greaterThan(0));
    expect(tester.getTopLeft(section).dy, lessThan(200));
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('home uses API calendar and all five tabs including Coins', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api));
    expect(api.homes, 1);
    await scrollToAgenda(tester);
    expect(find.text('Equipo A'), findsOneWidget);
    expect(find.text('Liga de prueba'), findsOneWidget);
    await capture(tester, 'home');
    for (final label in [
      'Predicciones',
      'Mercados',
      'Coins',
      'Perfil',
      'Inicio',
    ]) {
      await navigate(tester, label);
      expect(tester.takeException(), isNull);
    }
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('los partidos terminados no salen en Inicio, los de en juego sí', (
    tester,
  ) async {
    JsonMap match(String home, String status, {List<int>? score}) => {
      'match_id': home,
      'kickoff_utc': DateTime.now()
          .subtract(const Duration(hours: 1))
          .toUtc()
          .toIso8601String(),
      'estado': status,
      'marcador': score,
      'local': {'nombre': home},
      'visitante': {'nombre': 'Rival de $home'},
      'liga': {'nombre': 'Liga de prueba'},
    };
    final api = FixtureApi()
      ..extraAgenda = [
        match('Terminado FC', 'finished', score: [5, 0]),
        match('Directo FC', 'live'),
      ];
    await open(tester, ProductShell(api: api));
    await tester.scrollUntilVisible(
      find.text('Equipo A'),
      200,
      scrollable: find
          .descendant(
            of: find.byKey(const ValueKey('home-scroll')),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('Equipo A'), findsOneWidget); // por jugar
    expect(find.text('Directo FC'), findsOneWidget); // en juego
    expect(find.text('Terminado FC'), findsNothing);
    expect(find.textContaining('Resultado: 5'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('la cabecera muestra las monedas disponibles y abre Coins', (
    tester,
  ) async {
    final api = FixtureApi()..wallet = {'balance': -5, 'spendable': 0};
    await open(tester, ProductShell(api: api));
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('header-coins')),
        matching: find.text('0'),
      ),
      findsOneWidget,
    );
    api.wallet = {'balance': 120, 'spendable': 120};
    await tester.tap(find.byIcon(Icons.refresh));
    await tester.pumpAndSettle();
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('header-coins')),
        matching: find.text('120'),
      ),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('header-coins')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('coins-hero')), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('sin cuenta la cabecera no inventa saldo', (tester) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api));
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('header-coins')),
        matching: find.text('—'),
      ),
      findsOneWidget,
    );
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('VIP card opens actual plans; no sample prices', (tester) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api));
    await navigate(tester, 'Predicciones');
    expect(find.text('Más de 1,5 goles'), findsOneWidget);
    // Los pronósticos de candado van en una sola tarjeta con el acceso VIP.
    expect(find.text('1 pronóstico más con VIP'), findsOneWidget);
    expect(find.text('Acceso VIP'), findsOneWidget);
    await capture(tester, 'predictions');
    await tester.tap(find.text('Acceso VIP'));
    await tester.pumpAndSettle();
    expect(find.text(r'$14,99'), findsOneWidget);
    expect(find.text('USD'), findsOneWidget);
    expect(find.text('999.00 MXN'), findsNothing);
    await capture(tester, 'vip');
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('real details distinguish unavailable statistics and lineups', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, LiveMatchDetail(api: api, id: 'test-2', onVip: () {}));
    expect(find.text('Este partido tiene un pronóstico VIP'), findsOneWidget);
    await tester.tap(find.text('Análisis'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Promedios de 0'), findsOneWidget);
    expect(find.byType(RadarChart), findsNothing);
    expect(find.text('0 %'), findsNothing);
    await capture(tester, 'stats');
    await tester.tap(find.text('H2H'));
    await tester.pumpAndSettle();
    expect(find.text('Alineaciones todavía no confirmadas.'), findsOneWidget);
    expect(
      find.text('No hay una comprobación de bajas disponible.'),
      findsOneWidget,
    );
    await capture(tester, 'h2h');
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('disabled section shows backend legend', (tester) async {
    final api = FixtureApi();
    api.flags['alta_probabilidad'] = {
      'enabled': false,
      'message': 'Modelo calibrándose',
    };
    await open(tester, ProductShell(api: api));
    await navigate(tester, 'Predicciones');
    expect(find.text('Modelo calibrándose'), findsOneWidget);
    expect(find.text('Más de 1,5 goles'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('statistics plots real response without requiring missing xG', (
    tester,
  ) async {
    final api = FixtureApi()..richDetail = true;
    await open(
      tester,
      LiveMatchDetail(api: api, id: 'real-match', onVip: () {}),
    );
    await tester.tap(find.text('Análisis'));
    await tester.pumpAndSettle();
    expect(find.text('RESUMEN DE PREDICCIÓN'), findsOneWidget);
    expect(find.text('37 %'), findsOneWidget);
    expect(find.byType(RadarChart), findsOneWidget);
    final radar = tester.widget<RadarChart>(find.byType(RadarChart));
    expect(radar.data.titleCount, 6);
    expect(radar.data.dataSets.first.dataEntries.first.value, 100);
    expect(
      radar.data.dataSets.last.dataEntries.first.value,
      closeTo(.9 / 1.1 * 100, .001),
    );
    await capture(tester, 'stats_real_summary');
    await tester.ensureVisible(find.text('ESTADÍSTICAS DEL EQUIPO'));
    await tester.pumpAndSettle();
    await capture(tester, 'stats_real_radar');
    await tester.ensureVisible(find.text('COMPARACIÓN DE EQUIPOS'));
    await tester.pumpAndSettle();
    await capture(tester, 'stats_real_comparison');
    await tester.ensureVisible(find.text('CARA A CARA'));
    await tester.pumpAndSettle();
    await capture(tester, 'stats_real_h2h');
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('sin candidatos en rango no muestra un destacado fuera de limites', (tester) async {
    final api = FixtureApi()
      ..richDetail = true
      ..detailPicks = [
        {'market': 'corners', 'texto': 'Más de 6,5 córners', 'prob': .85, 'ref_price': 1.12},
        {'market': 'totals', 'texto': 'Más de 1,5 goles', 'prob': .86, 'ref_price': 1.40},
      ];
    await open(tester, LiveMatchDetail(api: api, id: 'real-match', onVip: () {}));
    expect(find.byType(ForecastPanel), findsNothing);
    expect(find.textContaining('Ningún pronóstico de este partido entra en el destacado (cuota de 1,20 a 1,60'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('forecast tab shows featured pick with real indicators only', (
    tester,
  ) async {
    final api = FixtureApi()
      ..richDetail = true
      ..detailLocked = true
      ..modelo = {
        'fuente': 'mercado',
        'mas_2_5': .61,
        'ambos': .63,
        'mas_1_5': .8,
        'local': .43,
        'empate': .27,
        'visita': .3,
        'goles_local': [.77, .44, .2],
        'goles_visita': [.67, .32, null],
      }
      ..mercados = {
        'abiertas': 1,
        'total': 3,
        'filas': [
          {
            'id': 'totals:over:1.5',
            'grupo': 'GOLES',
            'titulo': 'Goles totales',
            'seleccion': 'Más de 1,5 goles',
            'prob': .83,
            'nivel': 'alta',
            'cuota': 1.2,
            'cuota_tipo': 'justa',
            'nota': 'Goles esperados: 3,06',
            'locked': false,
          },
          {'id': 'corners:over:8.5', 'grupo': 'CÓRNERS', 'locked': true},
        ],
        'marcadores': [
          {'marcador': '2-0', 'prob': .11},
          {'marcador': '1-0', 'prob': .1},
        ],
      }
      ..detailPicks = [
        {
          'match_id': 'real-match',
          'market': 'totals',
          'texto': 'Más de 2,5 goles',
          'prob': .79,
          'ref_price': 1.45,
          'ref_book': 'Fuente de prueba',
          'free': true,
          'locked': false,
          'xg': {'local': 2.2, 'visita': .86, 'total': 3.06},
        },
        {
          'match_id': 'real-match',
          'market': 'h2h',
          'texto': 'Gana el local',
          'prob': .76,
          'locked': false,
        },
      ];
    await open(
      tester,
      LiveMatchDetail(api: api, id: 'real-match', onVip: () {}),
    );
    expect(find.text('Más de 2,5 goles'), findsOneWidget);
    expect(find.text('@1,45'), findsOneWidget);
    // Una sola tarjeta «Análisis estadístico» (la de mayor probabilidad: 79 % frente a 76 %)
    // con los 4 indicadores, y sin chips de mercado.
    expect(find.byType(ForecastPanel), findsOneWidget);
    expect(find.byType(ChoiceChip), findsNothing);
    expect(find.text('ANÁLISIS ESTADÍSTICO'), findsOneWidget);
    expect(find.text('CUOTAS DEL MERCADO'), findsOneWidget);
    expect(
      find.text('61 %'),
      findsOneWidget,
    ); // tendencia: más de 2,5 según el modelo
    expect(find.text('43 %'), findsOneWidget); // favorito 1X2
    expect(
      find.textContaining('esta liga no tiene modelo propio'),
      findsOneWidget,
    );
    expect(find.textContaining('3,06 goles esperados'), findsOneWidget);
    // Lista de mercados del partido: el abierto con su nivel y cuota justa, el otro con candado.
    expect(find.text('Mercados del partido'), findsOneWidget);
    expect(find.text('1 abierto · 1 con candado'), findsOneWidget);
    expect(find.text('Más de 1,5 goles'), findsOneWidget);
    expect(find.text('@1,20'), findsOneWidget);
    expect(find.text('cuota justa'), findsOneWidget);
    expect(find.text('ALTA PROB.'), findsWidgets);
    expect(find.byIcon(Icons.lock_outline), findsOneWidget);
    expect(
      find.textContaining('CÓRNERS · 1 mercado'),
      findsOneWidget,
    ); // candados agrupados por categoría
    expect(find.text('Marcadores más probables'), findsOneWidget);
    expect(find.text('2-0'), findsOneWidget);
    expect(find.textContaining('DICTAMEN DEL MODELO'), findsOneWidget);
    await capture(tester, 'forecast_panel');
    expect(find.text('Gana el local'), findsNothing);
    // Con un pronóstico abierto no se ofrece VIP arriba aunque el partido tenga otros bloqueados,
    // y la tarjeta ya no lleva el botón de estadísticas.
    expect(find.text('Este partido tiene un pronóstico VIP'), findsNothing);
    expect(find.text('Ver estadísticas del partido'), findsNothing);
    await tester.tap(find.text('Análisis'));
    await tester.pumpAndSettle();
    expect(find.text('RESUMEN DE PREDICCIÓN'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('vip screen shows server plans and no invented figures', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(
      tester,
      LiveVipScreen(
        api: api,
        data: {
          'config': {
            'features': {
              'compras': {
                'enabled': false,
                'message': 'Compras en preparación',
              },
            },
            'probability_min': .75,
            'probability_max': .9,
          },
          'alta_probabilidad': {
            'historial': {'n': 114, 'aciertos': 89, 'acierto_real': 78.1},
          },
          'plans': [
            {
              'name': 'Plus · 1 mes',
              'price_cents': 1499,
              'currency': 'USD',
              'duration_days': 30,
            },
            {
              'name': 'Plus · 3 meses',
              'price_cents': 3399,
              'currency': 'USD',
              'duration_days': 90,
            },
            {
              'name': 'Plus · 6 meses',
              'price_cents': 5399,
              'currency': 'USD',
              'duration_days': 180,
            },
          ],
        },
      ),
    );
    expect(find.text('QuantFut VIP'), findsOneWidget);
    expect(find.text('78,1 %'), findsOneWidget);
    expect(find.text('89/114'), findsOneWidget);
    expect(find.text('\$14,99'), findsOneWidget);
    expect(find.text('\$53,99'), findsOneWidget);
    expect(find.text('★ MEJOR PRECIO'), findsOneWidget);
    // Equivalente mensual con la moneda del servidor, sin suponer «$».
    expect(find.text('≈ 9,00 USD/mes'), findsOneWidget);
    expect(find.textContaining(RegExp(r'≈ \$')), findsNothing);
    await capture(tester, 'vip_screen');
    await tester.ensureVisible(find.text('Activar acceso VIP'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Activar acceso VIP'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Compras en preparación'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('network failure never falls back to demo', (tester) async {
    final api = FixtureApi()..fail = true;
    await open(tester, ProductShell(api: api));
    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.text('Equipo A'), findsNothing);
    api.fail = false;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(api.homes, 2);
    await scrollToAgenda(tester);
    expect(find.text('Equipo A'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('coins shows guest state and seven configured rewards', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api));
    await navigate(tester, 'Coins');
    expect(find.byType(RewardsScreen), findsOneWidget);
    expect(find.text('Menú'), findsNothing);
    expect(find.text('Monedas'), findsNothing);
    expect(find.text('Coins'), findsNWidgets(2));
    expect(find.text('Inicia sesión'), findsOneWidget);
    expect(find.text('Día 7'), findsOneWidget);
    await capture(tester, 'coins');
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
  testWidgets('navigation tolerates larger text', (tester) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api), scale: 1.3);
    await navigate(tester, 'Predicciones');
    expect(tester.takeException(), isNull);
    await navigate(tester, 'Coins');
    expect(find.text('Mis monedas'), findsOneWidget);
    await capture(tester, 'coins_large_text');
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.dispose();
  });
}
