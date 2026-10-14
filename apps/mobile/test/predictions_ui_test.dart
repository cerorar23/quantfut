// Menú de Predicciones, Alta probabilidad (acierto, días, candados agrupados) y Parley.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_parley.dart';
import 'package:gobet/product/live_picks.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/predictions_switcher.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

String iso(DateTime day, int hour) =>
    DateTime(day.year, day.month, day.day, hour).toUtc().toIso8601String();

Map<String, dynamic> pick(
  String home,
  String away,
  String text,
  double prob,
  double price,
  String kickoff, {
  bool locked = false,
  bool free = true,
}) => {
  'match_id': '$home-$away',
  'local': home,
  'visitante': away,
  'texto': text,
  'prob': prob,
  'ref_price': price,
  'ref_book': 'betano',
  'kickoff_utc': kickoff,
  'league_id': 'eu.ucl',
  'free': free && !locked,
  'locked': locked,
};

Map<String, dynamic> report(DateTime today) {
  final tomorrow = today.add(const Duration(days: 1));
  return {
    'estado': 'activa',
    'historial': {'n': 141, 'aciertos': 114, 'acierto_real': 80.9, 'acierto_prometido': 82.4},
    'proximos': [
      pick('Lens', 'Sporting CP', 'Marca Lens', .8, 1.22, iso(today, 18)),
      pick('Galatasaray', 'Barcelona', 'Gana Barcelona', .76, 1.3, iso(today, 20)),
      pick('Leipzig', 'PSV', 'Más de 2,5 goles', .73, 1.34, iso(tomorrow, 20)),
    ],
    'vip': [
      {...pick('Inter', 'Benfica', '', 0, 0, iso(today, 21), locked: true), 'cuota': 1.35},
      {...pick('Milan', 'Roma', '', 0, 0, iso(tomorrow, 19), locked: true), 'cuota': null},
    ],
  };
}

Future<void> pump(
  WidgetTester tester,
  Widget body, {
  Size size = const Size(390, 900),
  String? code,
}) async {
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
      home: Scaffold(
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: body,
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 400));
}

class _ParleyApi extends QuantFutApi {
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async => {
    'activo': true,
    'reglas': {
      'escalones': [
        {'escalon': 1, 'cuota_min': 1.9, 'cuota_max': 2.2},
        {'escalon': 5, 'cuota_min': 4.3, 'cuota_max': 5.0},
      ],
    },
    'dias': [
      {
        'dia': '2026-10-13',
        'tickets': [
          {
            'escalon': 2,
            'cuota_total': 2.45,
            'prob_total': .31,
            'outcome': null,
            'patas': [
              {'local': 'Nice', 'visitante': 'Strasbourg', 'texto': 'Más de 1,5 goles', 'price': 1.28, 'prob': .8, 'outcome': 'win', 'marcador': '2-1'},
              {'local': 'Galatasaray', 'visitante': 'Barcelona', 'texto': 'Gana Barcelona', 'price': 1.3, 'prob': .76, 'outcome': null, 'kickoff_utc': '2026-10-13T19:00:00+00:00'},
              {'local': 'Leipzig', 'visitante': 'PSV', 'texto': 'Más de 2,5 goles', 'price': 1.34, 'prob': .73, 'outcome': null, 'kickoff_utc': '2026-10-13T19:00:00+00:00'},
            ],
          },
        ],
      },
    ],
    'resumen': {'total': {'n': 0}},
  };
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

  group('menú de secciones', () {
    test('deslizar a la izquierda avanza y a la derecha retrocede, sin salirse', () {
      expect(PredictionsSwitcher.swipe('high', -800), 'ladder');
      expect(PredictionsSwitcher.swipe('ladder', -800), 'parley');
      expect(PredictionsSwitcher.swipe('parley', -800), 'parley');
      expect(PredictionsSwitcher.swipe('parley', 800), 'ladder');
      expect(PredictionsSwitcher.swipe('high', 800), 'high');
      expect(PredictionsSwitcher.swipe('ladder', 100), 'ladder'); // roce corto
    });

    testWidgets('tocar cambia de sección, mueve el indicador y muestra los contadores', (tester) async {
      var value = 'high';
      late StateSetter set;
      await pump(
        tester,
        StatefulBuilder(
          builder: (context, setState) {
            set = setState;
            return PredictionsSwitcher(
              value: value,
              onChanged: (v) => set(() => value = v),
              badges: const {'high': 5, 'ladder': 4},
            );
          },
        ),
        code: 'es',
      );
      expect(find.text('5'), findsOneWidget);
      expect(find.text('4'), findsOneWidget);
      final first = tester.getTopLeft(find.byKey(const ValueKey('streams-indicator'))).dx;
      await tester.tap(find.byKey(const ValueKey('streams-parley')));
      await tester.pump(); // arranca la animación
      await tester.pump(const Duration(milliseconds: 400));
      expect(value, 'parley');
      expect(
        tester.getTopLeft(find.byKey(const ValueKey('streams-indicator'))).dx,
        greaterThan(first + 100),
      );
    });
  });

  group('Alta probabilidad', () {
    testWidgets('acierto histórico, pronósticos por día y el mejor marcado', (tester) async {
      final today = DateTime.now();
      var opened = '';
      await pump(
        tester,
        HighProbabilityView(
          report: report(today),
          minPercent: 73,
          maxPercent: 95,
          onOpen: (p) => opened = '${p['texto']}',
          onVip: () {},
        ),
        code: 'es',
      );
      expect(find.text('80,9 %'), findsOneWidget);
      expect(find.text('114 de 141 pronósticos'), findsOneWidget);
      expect(find.text('Prometido: 82,4 %'), findsOneWidget);
      expect(find.text('Gratis · 3'), findsOneWidget);
      expect(find.text('Hoy'), findsOneWidget);
      expect(find.text('Mañana'), findsOneWidget);
      expect(find.text('Mayor probabilidad'), findsOneWidget);
      expect(find.text('Marca Lens'), findsOneWidget);
      expect(find.text('@1,22'), findsOneWidget);
      expect(find.text('80 %'), findsOneWidget);
      expect(find.textContaining('Champions League'), findsWidgets);
      await tester.tap(find.text('Marca Lens'));
      expect(opened, 'Marca Lens');
    });

    testWidgets('los candados van en una tarjeta plegable y no una por pronóstico', (tester) async {
      var vip = 0;
      final unlocked = <String>[];
      await pump(
        tester,
        HighProbabilityView(
          report: report(DateTime.now()),
          minPercent: 73,
          maxPercent: 95,
          onOpen: (_) {},
          onVip: () => vip++,
          onUnlock: (p) => unlocked.add('${p['local']}'),
          unlockCost: 100,
        ),
        code: 'es',
      );
      expect(find.text('2 pronósticos más con VIP'), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline), findsOneWidget); // solo el de la tarjeta
      expect(find.text('Inter · Benfica'), findsNothing);
      final toggle = find.byKey(const ValueKey('high-locked-toggle'));
      await tester.ensureVisible(toggle);
      await tester.tap(toggle);
      await tester.pump();
      expect(find.text('Inter · Benfica'), findsOneWidget);
      expect(find.text('Milan · Roma'), findsOneWidget);
      // La cuota publicada se ve en el candado; si el servidor no la manda, no se inventa.
      expect(find.byKey(const ValueKey('locked-quote')), findsOneWidget);
      expect(find.text('@1,35'), findsOneWidget);
      await tester.tap(find.text('100 monedas').first);
      expect(unlocked, ['Inter']);
      await tester.tap(find.text('Ver acceso VIP'));
      expect(vip, 1);
    });

    testWidgets('sin pronósticos liquidados no hay tarjeta de acierto', (tester) async {
      final r = report(DateTime.now())..['historial'] = {'n': 0};
      await pump(tester, HighProbabilityView(report: r, minPercent: 73, maxPercent: 95, onOpen: (_) {}, onVip: () {}), code: 'es');
      expect(find.byKey(const ValueKey('high-trust')), findsNothing);
    });
  });

  for (final code in languages) {
    testWidgets('Alta probabilidad y Parley en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 900), Size(320, 640)]) {
        await pump(
          tester,
          Column(
            children: [
              HighProbabilityView(
                report: report(DateTime.now()),
                minPercent: 73,
                maxPercent: 95,
                onOpen: (_) {},
                onVip: () {},
                onUnlock: (_) {},
                unlockCost: 100,
              ),
              ParleyTab(api: _ParleyApi()),
            ],
          ),
          size: size,
          code: code,
        );
        await tester.pump(const Duration(milliseconds: 400));
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }

  testWidgets('el parley se ve como boleto con sus patas y las reglas en una hoja', (tester) async {
    await pump(tester, ParleyTab(api: _ParleyApi()), code: 'es');
    expect(find.byKey(const ValueKey('parley-ticket-0')), findsOneWidget);
    expect(find.text('@2,45'), findsOneWidget);
    expect(find.text('Nice · Strasbourg'), findsOneWidget);
    expect(find.text('Leipzig · PSV'), findsOneWidget);
    expect(find.text('Hasta 2 parlays · cuota 1,90–5,00'), findsOneWidget);
    expect(find.byKey(const ValueKey('parley-no-history')), findsNothing);
    await tester.tap(find.byKey(const ValueKey('parley-rules-button')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('parley-rules')), findsOneWidget);
  });
}
