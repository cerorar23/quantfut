// Tarjetas del Reto Escalera: avance, estado, probabilidad estimada, escalones plegables
// e historial de retos cerrados, con la forma real de los datos del servidor.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/ladder_progress.dart';
import 'package:gobet/product/live_ladder.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];
const average = .791;

Map<String, dynamic> step(String outcome, String home, String away, String text, String score) => {
  'outcome': outcome,
  'local': home,
  'visitante': away,
  'texto': text,
  'marcador': score,
  'prob': .78,
};

Map<String, dynamic> challenge(
  int id, {
  required int goal,
  required int won,
  required String estado,
  String saldo = '15.63',
  List<Map<String, dynamic>> pasos = const [],
  String ganancia = '0.00',
}) => {
  'reto_id': id,
  'pasos_objetivo': goal,
  'ganados': won,
  'estado': estado,
  'stake_inicial': '10.00',
  'saldo': saldo,
  'retirado': '0.00',
  'ganancia': ganancia,
  'pasos': pasos,
};

final inPlay = challenge(
  3,
  goal: 4,
  won: 2,
  estado: 'esperando',
  pasos: [
    step('win', 'Nice', 'Strasbourg', 'Más de 1,5 goles', '2-1'),
    step('win', 'Burgos', 'Granada', 'Menos de 3,5 goles', '0-1'),
    {'outcome': null, 'prob': .76, 'local': 'Lens', 'visitante': 'Sporting CP'},
  ],
);
final toPick = challenge(
  1,
  goal: 3,
  won: 2,
  estado: 'en_curso',
  saldo: '15.75',
  pasos: [step('win', 'Cobresal', 'U. de Concepción', 'Más de 1,5 goles', '1-1')],
);

/// Escalón de un reto cerrado, con los campos que el servidor publica (`_paso_publico`).
Map<String, dynamic> closedStep(
  int n,
  String outcome,
  String home,
  String away,
  String market,
  String selection,
  double? line,
  double price,
  String score,
) => {
  'paso': n,
  'outcome': outcome,
  'local': home,
  'visitante': away,
  'market': market,
  'selection': selection,
  'line': line,
  'texto': 'texto-del-servidor',
  'price': price,
  'marcador': score,
  'kickoff_utc': '2026-10-10T18:00:00Z',
};

final closedReport = {
  'resumen': {
    'cerrados': 2,
    'completados': 1,
    'tasa_completados': 50.0,
    'invertido': '20.00',
    'ganancia': '6.00',
    'roi': 30.0,
  },
  'historial': [
    challenge(
      8,
      goal: 4,
      won: 2,
      estado: 'fallido',
      saldo: '0.00',
      pasos: [
        closedStep(2, 'win', 'Lens', 'Nice', 'totals', 'over', 1.5, 1.4, '2-1'),
        closedStep(1, 'win', 'Burgos', 'Granada', 'totals', 'under', 3.5, 1.3, '0-1'),
        closedStep(3, 'loss', 'Leeds', 'Hull', 'corners', 'over', 8.5, 1.5, '1-0'),
      ],
    ),
    challenge(
      7,
      goal: 3,
      won: 3,
      estado: 'completado',
      saldo: '26.00',
      ganancia: '16.00',
      pasos: [
        closedStep(1, 'win', 'Roma', 'Lazio', 'btts', 'no', null, 1.7, '1-0'),
        closedStep(2, 'push', 'Ajax', 'PSV', 'spreads', 'home', -1, 1.9, '2-1'),
        closedStep(3, 'win', 'Cádiz', 'Elche', 'h2h', 'home', null, 1.6, '2-0'),
      ],
    ),
  ],
};

/// Más cerrados de los que se enseñan: 12 cumplidos y 3 fallidos, el más reciente primero.
Map<String, dynamic> longReport() => {
  'resumen': {
    'cerrados': 15,
    'completados': 12,
    'tasa_completados': 80.0,
    'invertido': '150.00',
    'ganancia': '40.00',
    'roi': 26.7,
  },
  'historial': [
    challenge(30, goal: 3, won: 1, estado: 'fallido', saldo: '0.00'),
    for (var i = 29; i >= 18; i--)
      challenge(i, goal: 3, won: 3, estado: 'completado', saldo: '26.00', ganancia: '16.00'),
    challenge(17, goal: 3, won: 0, estado: 'fallido', saldo: '0.00'),
    challenge(16, goal: 4, won: 1, estado: 'fallido', saldo: '0.00'),
  ],
};

const emptyReport = {
  'resumen': {'cerrados': 0, 'completados': 0, 'tasa_completados': null, 'roi': null},
  'historial': <Map<String, dynamic>>[],
};

Future<void> pump(WidgetTester tester, Widget body, {Size size = const Size(390, 900), String? code}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  if (code != null) await AppLocale.instance.select(code);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: Scaffold(body: SingleChildScrollView(padding: const EdgeInsets.all(16), child: body)),
    ),
  );
  await tester.pump(const Duration(milliseconds: 900));
}

Widget cards(Map<String, dynamic> report) => Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    for (final c in sortLadder([toPick, inPlay]))
      LadderChallengeCard(
        challenge: c,
        averageProbability: average,
        pending: [if (c['estado'] == 'esperando') const Text('pendiente-3')],
      ),
    LadderHistoryCard(report: report),
  ],
);

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('el reto en juego muestra avance, estado, probabilidad y saldo', (tester) async {
    await pump(tester, cards(emptyReport), code: 'es');

    expect(find.text('Reto #3 · 4 escalones'), findsOneWidget);
    expect(find.text('2 de 4 ganados · faltan 2'), findsOneWidget);
    expect(find.text('En juego'), findsOneWidget);
    expect(find.text('50 %'), findsOneWidget);
    expect(find.text('≈ 60 %'), findsOneWidget); // 76 % del escalón en juego × 79,1 %
    expect(find.text('×1,56'), findsOneWidget);
    expect(find.text('Hay un escalón esperando resultado. El reto sigue vivo.'), findsOneWidget);
    expect(find.text('pendiente-3'), findsOneWidget);
    for (var i = 0; i < 4; i++) {
      expect(find.descendant(of: find.byKey(const ValueKey('ladder-card-3')), matching: find.byKey(ValueKey('ladder-step-$i'))), findsOneWidget);
    }
    // El reto en juego va primero aunque el otro esté más avanzado.
    expect(
      tester.getTopLeft(find.byKey(const ValueKey('ladder-card-3'))).dy,
      lessThan(tester.getTopLeft(find.byKey(const ValueKey('ladder-card-1'))).dy),
    );
  });

  testWidgets('un reto sin escalón en juego dice que falta elegir el siguiente', (tester) async {
    await pump(tester, cards(emptyReport), code: 'es');
    expect(find.text('Por elegir'), findsOneWidget);
    expect(find.text('2 de 3 ganados · falta 1'), findsOneWidget);
    expect(find.text('67 %'), findsOneWidget);
    expect(find.text('≈ 79 %'), findsOneWidget);
    expect(find.textContaining('puede tardar días'), findsOneWidget);
  });

  testWidgets('los escalones liquidados se pliegan y se despliegan', (tester) async {
    await pump(tester, cards(emptyReport), code: 'es');
    expect(find.textContaining('Más de 1,5 goles · Acertado'), findsNothing);
    final toggle = find.byKey(const ValueKey('ladder-toggle-3'));
    await tester.ensureVisible(toggle);
    await tester.tap(toggle);
    await tester.pump();
    expect(find.textContaining('Más de 1,5 goles · Acertado'), findsOneWidget);
    expect(find.text('Ocultar escalones'), findsOneWidget);
    await tester.tap(toggle);
    await tester.pump();
    expect(find.textContaining('Más de 1,5 goles · Acertado'), findsNothing);
  });

  testWidgets('tocar la probabilidad explica que es una estimación', (tester) async {
    await pump(tester, cards(emptyReport), code: 'es');
    final chance = find.byKey(const ValueKey('ladder-chance-3'));
    await tester.ensureVisible(chance);
    await tester.tap(chance);
    await tester.pump();
    expect(find.textContaining('Estimación'), findsOneWidget);
    expect(find.textContaining('media de los demás (79 %)'), findsOneWidget);
    expect(find.textContaining('No es una garantía'), findsOneWidget);
  });

  testWidgets('historial vacío: invita en vez de disculparse', (tester) async {
    await pump(tester, cards(emptyReport), code: 'es');
    expect(find.text('Historial de retos'), findsOneWidget);
    expect(find.text('0 cumplidos de 0 cerrados'), findsOneWidget);
    expect(find.textContaining('Aún no hay retos cerrados'), findsOneWidget);
  });

  testWidgets('historial con cerrados: tasa, resultado y los fallidos también', (tester) async {
    await pump(tester, cards(closedReport), code: 'es');
    expect(find.text('1 cumplidos de 2 cerrados'), findsOneWidget);
    expect(find.text('Tasa de cumplidos: 50 %'), findsOneWidget);
    expect(find.text('Resultado acumulado: +30,0 %'), findsOneWidget);
    final header = find.text('Historial de retos');
    await tester.ensureVisible(header);
    await tester.tap(header);
    await tester.pump();
    expect(find.text('Cumplido · 3 de 3 ganados'), findsOneWidget);
    expect(find.text('Falló en el escalón 3'), findsOneWidget);
    expect(find.text('×2,60'), findsOneWidget); // reto cumplido: 26,00 sobre 10,00
    expect(find.text('×0,00'), findsOneWidget); // reto fallido sin nada retirado
  });

  Future<void> openHistory(WidgetTester tester) async {
    // Entre dos `pump` seguidos el estado de la tarjeta se conserva: no la cierres.
    if (find.byKey(const ValueKey('ladder-history-list')).evaluate().isNotEmpty) return;
    final header = find.byKey(const ValueKey('ladder-history')).first;
    await tester.ensureVisible(header);
    await tester.tap(find.descendant(of: header, matching: find.byIcon(Icons.emoji_events_outlined)));
    await tester.pump();
  }

  /// Toca la cabecera del reto (su centro cae en los escalones cuando está desplegado).
  Future<void> tapRow(WidgetTester tester, int id) async {
    final row = find.byKey(ValueKey('ladder-history-row-$id'));
    await tester.ensureVisible(row);
    await tester.tapAt(tester.getTopLeft(row) + const Offset(24, 24));
    await tester.pump();
  }

  testWidgets('un reto cerrado enseña sus escalones: partido, selección, cuota y marcador', (tester) async {
    await pump(tester, cards(closedReport), code: 'es');
    await openHistory(tester);
    // Plegado por defecto: no hay detalle hasta tocar el reto.
    expect(find.text('Roma · Lazio'), findsNothing);
    await tapRow(tester, 7);
    expect(find.text('Roma · Lazio'), findsOneWidget);
    expect(find.text('No marcan los dos · Cuota 1,70 · 1-0'), findsOneWidget);
    expect(find.textContaining('Cuota 1,90 · 2-1 · Reembolso'), findsOneWidget);
    expect(find.text('Cádiz · Elche'), findsOneWidget);
  });

  testWidgets('solo un reto desplegado a la vez, y los escalones salen en orden', (tester) async {
    await pump(tester, cards(closedReport), code: 'es');
    await openHistory(tester);
    await tapRow(tester, 8);
    expect(find.text('Burgos · Granada'), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('Burgos · Granada')).dy,
      lessThan(tester.getTopLeft(find.text('Lens · Nice')).dy),
    );
    expect(find.textContaining('Más de 8,5 córners'), findsOneWidget);
    await tapRow(tester, 7);
    expect(find.text('Burgos · Granada'), findsNothing);
    expect(find.text('Roma · Lazio'), findsOneWidget);
    await tapRow(tester, 7);
    expect(find.text('Roma · Lazio'), findsNothing);
  });

  testWidgets('el detalle sale en el idioma del usuario, no en el del servidor', (tester) async {
    await pump(tester, cards(closedReport), code: 'en');
    await openHistory(tester);
    await tapRow(tester, 7);
    expect(find.textContaining('Odds 1.70'), findsOneWidget);
    expect(find.text('texto-del-servidor'), findsNothing);
  });

  testWidgets('enseña los 9 últimos cumplidos y el último fallido, y lo avisa', (tester) async {
    await pump(tester, cards(longReport()), size: const Size(390, 6000), code: 'es');
    await openHistory(tester);
    bool shown(int id) => find.byKey(ValueKey('ladder-history-row-$id')).evaluate().isNotEmpty;
    // El último fallido (30) y los 9 cumplidos más recientes (29 a 21).
    expect([for (var i = 30; i >= 21; i--) shown(i)], everyElement(isTrue));
    // Los cumplidos más antiguos y los otros fallidos no salen.
    expect([20, 19, 18, 17, 16].map(shown), everyElement(isFalse));
    expect(find.byKey(const ValueKey('ladder-history-row-30')), findsOneWidget);
    expect(find.text('Se muestran los últimos cumplidos y el último fallido.'), findsOneWidget);
    expect(find.text('12 cumplidos de 15 cerrados'), findsOneWidget); // el resumen cuenta todos
  });

  testWidgets('el fallido sale en su sitio por fecha, no al final', (tester) async {
    await pump(tester, cards(closedReport), code: 'es');
    await openHistory(tester);
    // closedReport: primero el fallido (8) y luego el cumplido (7).
    expect(
      tester.getTopLeft(find.byKey(const ValueKey('ladder-history-row-8'))).dy,
      lessThan(tester.getTopLeft(find.byKey(const ValueKey('ladder-history-row-7'))).dy),
    );
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 900), Size(320, 640)]) {
        await pump(tester, cards(closedReport), size: size, code: code);
        await tester.tap(find.byKey(const ValueKey('ladder-toggle-3')));
        await tester.pump();
        expect(tester.takeException(), isNull, reason: '$code $size');
        await openHistory(tester);
        await tapRow(tester, 7);
        await tapRow(tester, 8);
        expect(tester.takeException(), isNull, reason: '$code $size detalle');
      }
    });
  }
}
