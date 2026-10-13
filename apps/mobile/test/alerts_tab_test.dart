// Pestaña «Alertas» del análisis del partido: bajas reales por equipo, ventaja/desventaja,
// estados sin dato y su sitio en el detalle.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_alerts.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

Map<String, dynamic> row(String player, String type, String reason) => {
  'jugador': player,
  'tipo': type,
  'motivo': reason,
};

Map<String, dynamic> ficha({Map<String, dynamic>? bajas, bool withBajas = true}) => {
  'partido': {
    'kickoff_utc': '2099-10-13T11:45:00+00:00',
    'liga': {'nombre': 'UEFA Champions League'},
  },
  'local': {'nombre': 'RC Lens'},
  'visitante': {'nombre': 'Sporting CP'},
  if (withBajas)
    'bajas':
        bajas ??
        {
          'comprobada': '2026-10-13T09:00:00+00:00',
          'home': [row('A. Sima', 'Missing Fixture', 'Muscle Injury')],
          'away': [
            row('R. Zalazar', 'Questionable', 'Injury'),
            row('N. Santos', 'Missing Fixture', 'Muscle Injury'),
          ],
        },
};

class _Api extends QuantFutApi {
  _Api(this.payload);
  final Map<String, dynamic> payload;

  @override
  Future<JsonMap> detail(String id) async => {
    'config': {
      'features': {
        for (final k in ['agenda', 'alta_probabilidad', 'escalera', 'estadisticas', 'h2h', 'vip'])
          k: {'enabled': true, 'message': ''},
      },
    },
    'picks': <Map<String, dynamic>>[],
    'ficha': payload,
  };
}

Future<void> pump(
  WidgetTester tester,
  Widget body, {
  Size size = const Size(390, 1500),
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
      home: Scaffold(body: SingleChildScrollView(padding: const EdgeInsets.all(16), child: body)),
    ),
  );
  await tester.pump(const Duration(milliseconds: 800));
}

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

  testWidgets('equipo local: ventaja = bajas del rival, desventaja = las propias', (tester) async {
    await pump(tester, AlertsTab(ficha: ficha(), api: _Api({})));
    final advantage = find.byKey(const ValueKey('alerts-advantage'));
    final disadvantage = find.byKey(const ValueKey('alerts-disadvantage'));
    expect(find.descendant(of: advantage, matching: find.text('N. Santos')), findsOneWidget);
    expect(find.descendant(of: advantage, matching: find.text('R. Zalazar')), findsOneWidget);
    expect(find.descendant(of: disadvantage, matching: find.text('A. Sima')), findsOneWidget);
    expect(find.text('Bajas de Sporting CP'), findsOneWidget);
    expect(find.text('Bajas de RC Lens'), findsOneWidget);
    expect(find.text('Lesión muscular'), findsNWidgets(2));
    expect(find.text('Duda'), findsOneWidget);
    expect(find.text('No disponible'), findsNWidgets(2));
    expect(find.text('1 baja · 0 dudas'), findsOneWidget); // Lens
    expect(find.text('1 baja · 1 duda'), findsOneWidget); // Sporting
  });

  testWidgets('al elegir el otro equipo se invierten las secciones', (tester) async {
    await pump(tester, AlertsTab(ficha: ficha(), api: _Api({})));
    await tester.tap(find.byKey(const ValueKey('alerts-team-away')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));
    final advantage = find.byKey(const ValueKey('alerts-advantage'));
    final disadvantage = find.byKey(const ValueKey('alerts-disadvantage'));
    expect(find.descendant(of: advantage, matching: find.text('A. Sima')), findsOneWidget);
    expect(find.descendant(of: disadvantage, matching: find.text('N. Santos')), findsOneWidget);
    expect(find.descendant(of: disadvantage, matching: find.text('R. Zalazar')), findsOneWidget);
  });

  testWidgets('deslizar hacia la izquierda pasa al equipo visitante', (tester) async {
    await pump(tester, AlertsTab(ficha: ficha(), api: _Api({})));
    await tester.fling(find.byKey(const ValueKey('alerts-disadvantage')), const Offset(-300, 0), 1200);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));
    final disadvantage = find.byKey(const ValueKey('alerts-disadvantage'));
    expect(find.descendant(of: disadvantage, matching: find.text('N. Santos')), findsOneWidget);
  });

  testWidgets('comprobado y sin bajas: lo dice, no inventa nada', (tester) async {
    await pump(
      tester,
      AlertsTab(
        ficha: ficha(bajas: {'comprobada': '2026-10-13T09:00:00+00:00', 'home': [], 'away': []}),
        api: _Api({}),
      ),
    );
    expect(find.text('Sin ventajas reportadas.'), findsOneWidget);
    expect(find.text('Sin desventajas reportadas.'), findsOneWidget);
    expect(find.text('Fuente: API-Football'), findsOneWidget);
  });

  testWidgets('sin comprobación: explica que no significa «sin lesionados»', (tester) async {
    await pump(tester, AlertsTab(ficha: ficha(withBajas: false), api: _Api({})));
    expect(find.byKey(const ValueKey('alerts-no-check')), findsOneWidget);
    expect(find.textContaining('no significa que no haya lesionados'), findsOneWidget);
    expect(find.byKey(const ValueKey('alerts-advantage')), findsNothing);
  });

  testWidgets('el detalle del partido tiene la pestaña Alertas con el total de bajas', (tester) async {
    await pump(tester, SizedBox(height: 1400, child: LiveMatchDetail(api: _Api(ficha()), id: 'm1', onVip: () {})));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('Alertas'), findsOneWidget);
    expect(find.byKey(const ValueKey('alerts-tab-badge')), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    await tester.tap(find.text('Alertas'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.byKey(const ValueKey('alerts-team-home')), findsOneWidget);
    expect(find.text('Ventaja'.toUpperCase()), findsOneWidget);
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 1500), Size(320, 1500)]) {
        await pump(tester, AlertsTab(ficha: ficha(), api: _Api({})), size: size, code: code);
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }
}
