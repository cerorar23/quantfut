import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sport_props.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';
import 'package:gobet/product/sports_quotes.dart';

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

final _api = _Api();
final _sealed = DateTime.utc(2026, 11, 14, 12);
const _asOf = '2026-11-14T11:00:00+00:00';

SportMarket _prop({
  required String id,
  required String market,
  required String player,
  required String playerId,
  required double line,
  String side = 'over',
  String? team,
  double prob = 0.61,
  int? last5,
  bool locked = false,
  String? outcome,
  double? price,
}) => SportMarket(
  id: id,
  label: player,
  selection: player,
  probability: prob,
  sealedAt: _sealed,
  eligible: true,
  market: market,
  player: player,
  playerId: playerId,
  rowPlayerId: playerId,
  line: line,
  side: side,
  team: team,
  last5: last5,
  locked: locked,
  outcome: outcome,
  price: price,
);

SportEvent _event(List<SportMarket> markets, {String status = 'scheduled'}) => SportEvent(
  id: 'NBA-01',
  sport: kNba,
  home: 'Miami Heat',
  away: 'Detroit Pistons',
  league: 'NBA',
  start: DateTime.utc(2026, 11, 14, 20),
  status: status,
  seal: 'seal-123',
  sealedAt: _sealed,
  markets: markets,
);

QuotesOverlay _quotes() => QuotesOverlay.fromJson(kNba, {
  'state': 'ok',
  'events': {
    'NBA-01': {
      'cohort': 'seal-123',
      'quotes': {
        'player_points|1630165|25.5': {
          'over': {
            'price': 1.88,
            'book': 'fanduel',
            'as_of': _asOf,
            'books': 3,
          },
        },
      },
    },
  },
});

Future<void> _pump(
  WidgetTester tester,
  Widget body, {
  String code = 'es',
  Size size = const Size(390, 1800),
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
      home: Scaffold(
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: body,
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

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

  testWidgets('con y sin cuota de referencia', (tester) async {
    final mWithQuote = _prop(
      id: 'p1',
      market: 'player_points',
      player: 'Cade Cunningham',
      playerId: '1630165',
      line: 25.5,
      team: 'Detroit Pistons',
    );
    final mNoQuote = _prop(
      id: 'p2',
      market: 'player_rebounds',
      player: 'Jalen Duren',
      playerId: '1631105',
      line: 10.5,
      team: 'Detroit Pistons',
    );
    final event = _event([mWithQuote, mNoQuote]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: _quotes(),
      ),
    );

    // Con cuota
    expect(find.text('@1,88'), findsOneWidget);
    expect(find.textContaining('FanDuel'), findsOneWidget);
    expect(find.text('Cade Cunningham'), findsOneWidget);
    expect(find.textContaining('Puntos · Más de 25,5'), findsOneWidget);

    // Sin cuota
    expect(find.text('—'), findsOneWidget);
    expect(find.text('Jalen Duren'), findsOneWidget);
    expect(find.textContaining('Rebotes · Más de 10,5'), findsOneWidget);
  });

  testWidgets('sin foto o id inválido: no rompe y muestra iniciales', (tester) async {
    final m = _prop(
      id: 'p-invalid',
      market: 'player_points',
      player: 'Sin Foto',
      playerId: 'not-a-number',
      line: 15.5,
      team: 'Miami Heat',
    );
    final event = _event([m]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: QuotesOverlay.empty,
      ),
    );

    expect(find.text('Sin Foto'), findsOneWidget);
    expect(find.text('SF'), findsOneWidget); // iniciales
  });

  testWidgets('jugador bloqueado: muestra VIP y opción de desbloquear', (tester) async {
    var vipOpened = 0;
    final mLocked = _prop(
      id: 'p-vip',
      market: 'player_assists',
      player: 'Tyler Herro',
      playerId: '1629639',
      line: 5.5,
      team: 'Miami Heat',
      locked: true,
    );
    final event = _event([mLocked]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: QuotesOverlay.empty,
        onVip: () => vipOpened++,
      ),
    );

    expect(find.text('VIP'), findsOneWidget);
    expect(find.text('con monedas o VIP'), findsOneWidget);

    await tester.tap(find.text('VIP'));
    expect(vipOpened, 1);
  });

  testWidgets('filtro por estadística en chips (TODOS · PUNTOS · REBOTES · ASIST. · TRIPLES)', (tester) async {
    final pPoints = _prop(id: '1', market: 'player_points', player: 'Player A', playerId: '1', line: 20.5);
    final pRebounds = _prop(id: '2', market: 'player_rebounds', player: 'Player B', playerId: '2', line: 8.5);
    final pAssists = _prop(id: '3', market: 'player_assists', player: 'Player C', playerId: '3', line: 6.5);
    final pThrees = _prop(id: '4', market: 'player_threes', player: 'Player D', playerId: '4', line: 2.5);
    final event = _event([pPoints, pRebounds, pAssists, pThrees]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: QuotesOverlay.empty,
      ),
    );

    // Inicialmente TODOS: se ven los 4
    expect(find.text('Player A'), findsOneWidget);
    expect(find.text('Player B'), findsOneWidget);
    expect(find.text('Player C'), findsOneWidget);
    expect(find.text('Player D'), findsOneWidget);

    // Filtro PUNTOS
    await tester.tap(find.byKey(const ValueKey('props-filter-points')));
    await tester.pump();
    expect(find.text('Player A'), findsOneWidget);
    expect(find.text('Player B'), findsNothing);
    expect(find.text('Player C'), findsNothing);
    expect(find.text('Player D'), findsNothing);

    // Filtro REBOTES
    await tester.tap(find.byKey(const ValueKey('props-filter-rebounds')));
    await tester.pump();
    expect(find.text('Player A'), findsNothing);
    expect(find.text('Player B'), findsOneWidget);
    expect(find.text('Player C'), findsNothing);
    expect(find.text('Player D'), findsNothing);

    // Filtro ASIST.
    await tester.tap(find.byKey(const ValueKey('props-filter-assists')));
    await tester.pump();
    expect(find.text('Player A'), findsNothing);
    expect(find.text('Player B'), findsNothing);
    expect(find.text('Player C'), findsOneWidget);
    expect(find.text('Player D'), findsNothing);

    // Filtro TRIPLES
    await tester.tap(find.byKey(const ValueKey('props-filter-threes')));
    await tester.pump();
    expect(find.text('Player A'), findsNothing);
    expect(find.text('Player B'), findsNothing);
    expect(find.text('Player C'), findsNothing);
    expect(find.text('Player D'), findsOneWidget);

    // Volver a TODOS
    await tester.tap(find.byKey(const ValueKey('props-filter-all')));
    await tester.pump();
    expect(find.text('Player A'), findsOneWidget);
    expect(find.text('Player B'), findsOneWidget);
    expect(find.text('Player C'), findsOneWidget);
    expect(find.text('Player D'), findsOneWidget);
  });

  testWidgets('filtro sin resultados muestra mensaje de aviso', (tester) async {
    final pPoints = _prop(id: '1', market: 'player_points', player: 'Player A', playerId: '1', line: 20.5);
    final event = _event([pPoints]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: QuotesOverlay.empty,
      ),
    );

    await tester.tap(find.byKey(const ValueKey('props-filter-rebounds')));
    await tester.pump();
    expect(find.text('No hay props disponibles en esta categoría.'), findsOneWidget);
  });

  testWidgets('últimos 5 partidos: si existe se dibuja, si no existe se omite', (tester) async {
    final withLast5 = _prop(
      id: '1',
      market: 'player_points',
      player: 'Player With Last5',
      playerId: '1',
      line: 20.5,
      last5: 4,
    );
    final withoutLast5 = _prop(
      id: '2',
      market: 'player_rebounds',
      player: 'Player Without Last5',
      playerId: '2',
      line: 10.5,
      last5: null,
    );
    final event = _event([withLast5, withoutLast5]);

    await _pump(
      tester,
      SportPropsTab(
        api: _api,
        event: event,
        quotes: QuotesOverlay.empty,
      ),
    );

    expect(find.text('4 de los últimos 5'), findsOneWidget);
    // Solo hay 1 mención de "últimos 5", la del que lo tiene
    expect(find.textContaining('últimos 5'), findsNWidgets(1));
  });

  testWidgets('orden: probabilidad antes del partido; acertados por cuota al terminar, con su resultado', (tester) async {
    final ms = [
      _prop(id: 'a', market: 'player_points', player: 'Baja Prob', playerId: '1', line: 10.5, prob: .55, outcome: 'win', price: 1.5),
      _prop(id: 'b', market: 'player_points', player: 'Alta Prob', playerId: '2', line: 10.5, prob: .80, outcome: 'loss', price: 1.2),
      _prop(id: 'c', market: 'player_points', player: 'Acierto Cuota Alta', playerId: '3', line: 10.5, prob: .60, outcome: 'win', price: 2.4),
    ];
    double y(WidgetTester t, String n) => t.getTopLeft(find.text(n)).dy;

    await _pump(tester, SportPropsTab(api: _api, event: _event(ms), quotes: QuotesOverlay.empty));
    expect(y(tester, 'Alta Prob') < y(tester, 'Acierto Cuota Alta'), isTrue);
    expect(y(tester, 'Acierto Cuota Alta') < y(tester, 'Baja Prob'), isTrue);

    await _pump(tester, SportPropsTab(api: _api, event: _event(ms, status: 'finished'), quotes: QuotesOverlay.empty));
    expect(y(tester, 'Acierto Cuota Alta') < y(tester, 'Baja Prob'), isTrue);
    expect(y(tester, 'Baja Prob') < y(tester, 'Alta Prob'), isTrue);
    expect(find.text('Acertado'), findsNWidgets(2));
    expect(find.text('Fallado'), findsOneWidget);
  });

  for (final lang in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('se pinta en $lang sin desbordes a 320 px', (tester) async {
      final p = _prop(
        id: '1',
        market: 'player_points',
        player: 'Cade Cunningham',
        playerId: '1630165',
        line: 25.5,
        last5: 3,
      );
      await _pump(
        tester,
        SportPropsTab(
          api: _api,
          event: _event([p]),
          quotes: _quotes(),
        ),
        code: lang,
        size: const Size(320, 1800),
      );
      expect(tester.takeException(), isNull);

});
  }
}
