import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_markets.dart';
import 'package:gobet/product/market_catalog.dart';
import 'package:gobet/l10n/app_locale.dart';

class _Api extends QuantFutApi {
  final paths = <String>[];
  JsonMap? lastQuery;
  bool fail = false;
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    paths.add(path);
    lastQuery = query;
    if (fail) throw const ApiFailure('sin red');
    final now = DateTime.now().toUtc().toIso8601String();
    return {
      'items': [
        {
          'local': 'Cuiaba',
          'visitante': 'Avai',
          'market': 'corners_home',
          'texto': 'Más de 3,5 córners de Cuiaba',
          'prob': .82,
          'outcome': 'win',
          'home_goals': 4,
          'away_goals': 4,
          'home_corners': 6,
          'away_corners': 3,
          'kickoff_utc': DateTime.now()
              .subtract(const Duration(days: 2))
              .toUtc()
              .toIso8601String(),
        },
        {
          'local': 'Pumas',
          'visitante': 'Cruz Azul',
          'market': 'totals',
          'texto': 'Más de 1,5 goles',
          'prob': .81,
          'outcome': 'win',
          'home_goals': 2,
          'away_goals': 1,
          'kickoff_utc': now,
        },
        {
          'local': 'Tigres',
          'visitante': 'Santos',
          'market': 'totals',
          'texto': 'Más de 1,5 goles',
          'prob': .8,
          'outcome': 'loss',
          'home_goals': 0,
          'away_goals': 1,
          'kickoff_utc': DateTime.now()
              .subtract(const Duration(days: 1))
              .toUtc()
              .toIso8601String(),
        },
      ],
    };
  }
}

/// Avanza la animación de página sin `pumpAndSettle`: el radar nunca se detiene.
Future<void> advance(WidgetTester tester) async {
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 200));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late MarketCatalog catalog;
  setUpAll(() async => catalog = await MarketCatalog.load());

  final alta = {
    'historial': {
      'n': 114,
      'aciertos': 89,
      'por_mercado': {
        'totals': {'n': 30, 'aciertos': 24},
        'corners_home': {'n': 10, 'aciertos': 9},
      },
    },
    'vip': [
      {
        'market': 'totals',
        'local': 'Cruz Azul',
        'visitante': 'Toluca',
        'kickoff_utc': DateTime.now()
            .add(const Duration(hours: 8))
            .toUtc()
            .toIso8601String(),
        'locked': true,
      },
      {
        'market': 'spreads',
        'local': 'Otro',
        'visitante': 'Equipo',
        'kickoff_utc': DateTime.now()
            .add(const Duration(hours: 9))
            .toUtc()
            .toIso8601String(),
        'locked': true,
      },
    ],
    'proximos': [
      {
        'market': 'totals',
        'texto': 'Más de 2,5 goles · Tigres - Leon',
        'local': 'Tigres',
        'visitante': 'Leon',
        'prob': .78,
        'ref_price': 1.5,
        'kickoff_utc': DateTime.now()
            .add(const Duration(hours: 5))
            .toUtc()
            .toIso8601String(),
      },
    ],
  };

  Future<_Api> open(WidgetTester tester, {bool reduce = false}) async {
    final api = _Api();
    tester.view.physicalSize = const Size(390, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,

        home: MediaQuery(
          data: MediaQueryData(disableAnimations: reduce),
          child: Scaffold(
            body: SingleChildScrollView(
              child: MarketsDashboard(api: api, alta: alta),
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 1300));
    return api;
  }

  testWidgets('tarjeta por familia con cifras del servidor, no del archivo', (
    tester,
  ) async {
    await open(tester);
    final football = catalog.forSport('Fútbol');
    for (final family in football) {
      expect(find.text(family.title), findsOneWidget, reason: family.id);
    }
    expect(find.text('${football.length}'), findsOneWidget);
    expect(find.textContaining('89/114 publicados'), findsOneWidget);
    expect(find.text('Publicado 24/30'), findsOneWidget);
    expect(find.textContaining('no alertas en vivo'), findsNothing);   // nota retirada a pedido del titular
    expect(find.textContaining('Rendimiento registrado'), findsNothing);
  });

  testWidgets('entrar a un mercado: Hoy abierto y Anteriores con resultados', (
    tester,
  ) async {
    final api = await open(tester);
    await tester.tap(find.text('Goles del partido'));
    await advance(tester);
    expect(api.paths, ['/mobile/v1/markets/history']);
    expect(api.lastQuery!['market'], 'totals');
    expect(find.text('Tasa de acierto'), findsOneWidget);
    expect(find.text('Hoy (2)'), findsOneWidget); // 1 abierto + 1 VIP
    expect(find.text('Cruz Azul'), findsOneWidget);
    expect(find.byIcon(Icons.lock_outline), findsOneWidget);
    expect(find.text('Otro'), findsNothing); // otro mercado (hándicap)
    expect(find.text('Más de 2,5 goles · Tigres - Leon'), findsOneWidget);
    expect(find.text('24/30'), findsOneWidget); // General, del servidor
    expect(find.text('1/1'), findsOneWidget); // Hoy: el de hoy acertó

    await tester.tap(find.text('Anteriores'));
    await advance(tester);
    expect(find.text('Acertó'), findsNWidgets(2));
    expect(find.text('Falló'), findsOneWidget);
    expect(find.text('2-1'), findsOneWidget);
    expect(find.text('Ayer'), findsOneWidget);
    // Mercado de córners: se muestran los córners reales, no los goles 4-4.
    expect(find.text('6-3'), findsOneWidget);
    expect(find.text('córners · total 9'), findsOneWidget);
    expect(find.text('4-4'), findsNothing);
  });

  testWidgets('si falla el historial se ofrece reintentar', (tester) async {
    final api = await open(tester);
    api.fail = true;
    await tester.tap(find.text('Tarjetas'));
    await advance(tester);
    await tester.tap(find.text('Anteriores'));
    await advance(tester);
    expect(find.text('Reintentar'), findsOneWidget);
  });

  testWidgets('con movimiento reducido no hay animación continua', (
    tester,
  ) async {
    await open(tester, reduce: true);
    await tester.pumpAndSettle();
  });
}
