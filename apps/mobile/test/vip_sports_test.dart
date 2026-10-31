// VIP: acierto registrado por deporte, beneficio de NBA y tenis y una sola acción ámbar.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_vip.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

SportMarket mk(String id, String? outcome, {bool eligible = true}) => SportMarket(
  id: id,
  label: 'L',
  selection: 'Sel',
  probability: .7,
  sealedAt: DateTime.utc(2026, 10, 30, 10),
  eligible: eligible,
  market: 'player_points',
  outcome: outcome,
);

SportEvent ev(SportKind sport, List<SportMarket> markets) => SportEvent(
  id: 'e-${sport.id}',
  sport: sport,
  home: 'A',
  away: 'B',
  league: 'L',
  start: DateTime.utc(2026, 11, 2, 19),
  status: 'final',
  seal: 'abc',
  sealedAt: DateTime.utc(2026, 10, 30),
  markets: markets,
);

final data = <String, dynamic>{
  'config': {
    'features': {
      'compras': {'enabled': false, 'message': 'Compras en preparación'},
    },
  },
  'alta_probabilidad': {
    'historial': {'n': 114, 'aciertos': 89, 'acierto_real': 78.1},
  },
  'plans': [
    {'plan_code': 'm1', 'price_cents': 1499, 'currency': 'USD', 'duration_days': 30},
    {'plan_code': 'm6', 'price_cents': 5399, 'currency': 'USD', 'duration_days': 180},
  ],
};

Future<void> pump(WidgetTester tester, Map<SportKind, SportFeed> feeds) async {
  tester.view.physicalSize = const Size(390, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select('es');
  final api = QuantFutApi();
  addTearDown(api.dispose);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: LiveVipScreen(api: api, data: data, sportFeeds: feeds),
    ),
  );
  await tester.pumpAndSettle();
}

Finder card(String id) => find.byKey(ValueKey('vip-sport-$id'));

void main() {
  tearDown(() => AppLocale.instance.reset());

  testWidgets('acierto por deporte: fútbol del servidor, NBA del feed y tenis sin resueltos', (tester) async {
    await pump(tester, {
      SportKind.nba: SportFeed(ready: true, events: [
        ev(SportKind.nba, [
          mk('1', 'win'),
          mk('2', 'win'),
          mk('3', 'loss'),
          mk('4', 'win', eligible: false), // sellado tarde: no cuenta
          mk('5', 'push'),
        ]),
      ]),
      SportKind.tennis: SportFeed(ready: true, events: [ev(SportKind.tennis, [mk('t', null)])]),
    });
    expect(find.text('ACIERTO REGISTRADO POR DEPORTE'), findsOneWidget);
    expect(find.descendant(of: card('futbol'), matching: find.text('78,1 %')), findsOneWidget);
    expect(find.descendant(of: card('futbol'), matching: find.text('89/114')), findsOneWidget);
    expect(find.descendant(of: card('nba'), matching: find.text('67 %')), findsOneWidget);
    expect(find.descendant(of: card('nba'), matching: find.text('2/3')), findsOneWidget);
    expect(find.descendant(of: card('tenis'), matching: find.text('—')), findsOneWidget);
    expect(find.textContaining('fútbol, NBA y tenis'), findsOneWidget);
    expect(find.text('NBA y tenis incluidos'), findsOneWidget);
  });

  testWidgets('un feed sin cargar o caído no inventa acierto', (tester) async {
    await pump(tester, {
      SportKind.nba: SportFeed(ready: false, events: [ev(SportKind.nba, [mk('1', 'win')])]),
    });
    expect(find.descendant(of: card('nba'), matching: find.text('—')), findsOneWidget);
    expect(find.descendant(of: card('tenis'), matching: find.text('—')), findsOneWidget);
  });

  testWidgets('una sola acción ámbar (Suscribirme) y el mejor precio con borde ámbar', (tester) async {
    await pump(tester, const {});
    final amber = tester
        .widgetList<FilledButton>(find.byType(FilledButton))
        .where((b) => b.style?.backgroundColor?.resolve(<WidgetState>{}) == QfColors.cta)
        .toList();
    expect(amber, hasLength(1));
    expect(amber.single.key, const ValueKey('vip-subscribe'));
    final best = find.byKey(const ValueKey('vip-plan-best'));
    expect(best, findsOneWidget);
    expect(find.descendant(of: best, matching: find.text('★ MEJOR PRECIO')), findsOneWidget);
    // Precios del servidor, nunca escritos en la app.
    expect(find.text('\$14,99'), findsOneWidget);
    expect(find.text('\$53,99'), findsOneWidget);
    expect(find.text('≈ 9,00 USD/mes'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('sin moneda del servidor el equivalente mensual va sin símbolo', (tester) async {
    for (final plan in data['plans'] as List) {
      (plan as Map).remove('currency');
    }
    addTearDown(() {
      for (final plan in data['plans'] as List) {
        (plan as Map)['currency'] = 'USD';
      }
    });
    await pump(tester, const {});
    expect(find.text('≈ 9,00/mes'), findsOneWidget);
    expect(find.textContaining(RegExp(r'≈ \$')), findsNothing);
  });
}
