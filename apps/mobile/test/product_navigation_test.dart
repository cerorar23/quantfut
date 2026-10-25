import 'dart:io';
import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_shell.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_rewards.dart';
import 'package:gobet/product/live_vip.dart';
import 'package:gobet/product/live_forecast.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/l10n/app_locale.dart';

class FixtureApi extends QuantFutApi {
  bool fail = false;
  bool richDetail = false;
  bool detailLocked = false;
  JsonMap? wallet;
  List<JsonMap> detailPicks = [];
  List<JsonMap> extraAgenda = [];
  JsonMap? modelo, mercados;
  int homes = 0;
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
  }) async => {
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
    await tester.pumpAndSettle();
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

  testWidgets('home uses API calendar and all five tabs including Coins', (
    tester,
  ) async {
    final api = FixtureApi();
    await open(tester, ProductShell(api: api));
    expect(api.homes, 1);
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
    expect(find.text('Ver acceso VIP'), findsOneWidget);
    await capture(tester, 'predictions');
    await tester.tap(find.text('Ver acceso VIP'));
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
  testWidgets('sin cuota de 1.40 o más no muestra destacado', (tester) async {
    final api = FixtureApi()
      ..richDetail = true
      ..detailPicks = [
        {'market': 'corners', 'texto': 'Más de 6,5 córners', 'prob': .85, 'ref_price': 1.12},
        {'market': 'totals', 'texto': 'Más de 1,5 goles', 'prob': .86, 'ref_price': 1.39},
      ];
    await open(tester, LiveMatchDetail(api: api, id: 'real-match', onVip: () {}));
    expect(find.byType(ForecastPanel), findsNothing);
    expect(find.textContaining('No hay un pronóstico destacado con cuota de 1.40 o más'), findsOneWidget);
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
    expect(find.text('≈ \$9,00/mes'), findsOneWidget);
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
