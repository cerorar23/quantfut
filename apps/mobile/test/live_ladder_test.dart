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
    challenge(8, goal: 4, won: 2, estado: 'fallido', saldo: '0.00'),
    challenge(7, goal: 3, won: 3, estado: 'completado', saldo: '26.00', ganancia: '16.00'),
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

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 900), Size(320, 640)]) {
        await pump(tester, cards(closedReport), size: size, code: code);
        await tester.tap(find.byKey(const ValueKey('ladder-toggle-3')));
        await tester.pump();
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }
}
