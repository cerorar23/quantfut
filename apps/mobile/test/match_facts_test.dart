// «Datos del partido»: último resultado, último once conocido y bajas, debajo de la probabilidad de
// victoria en la pestaña Análisis. Todo con datos guardados; lo que falta se dice.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_match_facts.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

Map<String, dynamic> played(String rival, String res, int gf, int gc, String competition, String date) => {
  'match_id': '$rival-$date',
  'fecha': date,
  'competicion': competition,
  'rival': rival,
  'res': res,
  'gf': gf,
  'gc': gc,
};

Map<String, dynamic> once() => {
  'fecha': '2026-10-09T18:45:00+00:00',
  'rival': 'Lyon',
  'competicion': 'Ligue 1',
  'formacion': '3-4-2-1',
  'titulares': [
    {'nombre': 'F. Thauvin', 'pos': 'F', 'numero': 28},
    {'nombre': 'R. Risser', 'pos': 'G', 'numero': 1},
    {'nombre': 'J. Gradit', 'pos': 'D', 'numero': 24},
  ],
};

Map<String, dynamic> ficha({bool withOnce = true, bool withMatches = true}) => {
  'partido': {
    'kickoff_utc': '2099-10-13T11:45:00+00:00',
    'liga': {'nombre': 'UEFA Champions League'},
  },
  'probabilities': {'home': .43, 'draw': .26, 'away': .32},
  'local': {
    'id': 1,
    'nombre': 'Lens',
    'forma': {
      'partidos': withMatches
          ? [
              played('Lyon', 'G', 2, 1, 'Ligue 1', '2026-10-09T18:45:00+00:00'),
              played('Slavia Praga', 'G', 3, 2, 'UEFA Champions League', '2026-09-30T19:00:00+00:00'),
            ]
          : [],
    },
    'ultimo_once': withOnce ? once() : null,
  },
  'visitante': {
    'id': 2,
    'nombre': 'Sporting CP',
    'forma': {
      'partidos': withMatches
          ? [played('Galatasaray', 'G', 3, 1, 'UEFA Champions League', '2026-09-30T19:00:00+00:00')]
          : [],
    },
    'ultimo_once': null,
  },
  'bajas': {
    'comprobada': '2026-10-13T09:00:00+00:00',
    'home': [
      {'jugador': 'A. Sima', 'tipo': 'Missing Fixture', 'motivo': 'Muscle Injury'},
    ],
    'away': [
      {'jugador': 'N. Santos', 'tipo': 'Missing Fixture', 'motivo': 'Muscle Injury'},
      {'jugador': 'R. Zalazar', 'tipo': 'Questionable', 'motivo': 'Injury'},
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
  Size size = const Size(390, 1800),
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
  await tester.pump(const Duration(milliseconds: 500));
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

  testWidgets('último resultado de cada equipo y el de la competición si es otro partido', (tester) async {
    await pump(tester, MatchFacts(ficha: ficha(), api: _Api({})));
    expect(find.text('DATOS DEL PARTIDO'), findsOneWidget);
    expect(find.text('2-1 contra Lyon'), findsOneWidget);
    expect(find.text('Último partido · Ligue 1 · 9 oct'), findsOneWidget);
    // Lens: su partido de Champions es distinto del último → segunda fila.
    expect(find.text('3-2 contra Slavia Praga'), findsOneWidget);
    expect(find.textContaining('En UEFA Champions League'), findsNWidgets(1));
    // Sporting: su último partido ya es de Champions → una sola fila.
    expect(find.text('3-1 contra Galatasaray'), findsOneWidget);
    expect(find.text('Ganó'), findsNWidgets(3));
  });

  testWidgets('último once conocido con su fecha y la aclaración de que no es una predicción', (tester) async {
    await pump(tester, MatchFacts(ficha: ficha(), api: _Api({})));
    expect(find.text('Último once conocido'), findsOneWidget);
    expect(find.text('3-4-2-1'), findsOneWidget);
    expect(find.text('contra Lyon · 9 oct'), findsOneWidget);
    expect(find.text('R. Risser'), findsNothing); // plegado
    final toggle = find.byKey(const ValueKey('facts-lineup-toggle-1'));
    await tester.ensureVisible(toggle);
    await tester.tap(toggle);
    await tester.pump();
    expect(find.text('1 R. Risser'), findsOneWidget);
    expect(find.text('24 J. Gradit'), findsOneWidget);
    expect(find.textContaining('no una predicción'), findsOneWidget);
    // Orden por posición: portero, defensa, delantero.
    final g = tester.getTopLeft(find.text('1 R. Risser'));
    final d = tester.getTopLeft(find.text('24 J. Gradit'));
    final f = tester.getTopLeft(find.text('28 F. Thauvin'));
    expect((g.dy < d.dy || g.dx < d.dx), isTrue);
    expect(f.dy > g.dy || f.dx > d.dx, isTrue);
  });

  testWidgets('sin alineación ni partidos previos lo dice en vez de rellenar', (tester) async {
    await pump(tester, MatchFacts(ficha: ficha(withOnce: false, withMatches: false), api: _Api({})));
    expect(find.text('Aún no hay una alineación guardada.'), findsNWidgets(2));
    expect(find.text('Sin partidos previos registrados.'), findsNWidgets(2));
    expect(find.text('Último once conocido'), findsNothing);
  });

  testWidgets('resumen de bajas con acceso a la pestaña de alertas', (tester) async {
    var opened = 0;
    await pump(tester, MatchFacts(ficha: ficha(), api: _Api({}), onAlerts: () => opened++));
    expect(find.text('Lens: 1 baja · 0 dudas'), findsOneWidget);
    expect(find.text('Sporting CP: 1 baja · 1 duda'), findsOneWidget);
    final row = find.byKey(const ValueKey('facts-alerts'));
    await tester.ensureVisible(row);
    await tester.tap(row);
    expect(opened, 1);
  });

  testWidgets('en Análisis va justo debajo de la probabilidad de victoria', (tester) async {
    await pump(tester, SizedBox(height: 1700, child: LiveMatchDetail(api: _Api(ficha()), id: 'm1', onVip: () {})));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('Análisis'), findsOneWidget);
    expect(find.text('Estadísticas'), findsNothing);
    await tester.tap(find.text('Análisis'));
    await tester.pump(const Duration(milliseconds: 600));
    final probability = tester.getTopLeft(find.textContaining('1X2').first).dy;
    final facts = tester.getTopLeft(find.text('DATOS DEL PARTIDO')).dy;
    expect(facts, greaterThan(probability));
    // Pulsar «Ver alertas» abre la pestaña Alertas.
    final alerts = find.byKey(const ValueKey('facts-alerts'));
    await tester.ensureVisible(alerts);
    await tester.tap(alerts);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.byKey(const ValueKey('alerts-team-home')), findsOneWidget);
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 1800), Size(320, 1800)]) {
        await pump(tester, MatchFacts(ficha: ficha(), api: _Api({}), onAlerts: () {}), size: size, code: code);
        final toggle = find.byKey(const ValueKey('facts-lineup-toggle-1'));
        await tester.ensureVisible(toggle);
        await tester.tap(toggle);
        await tester.pump();
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }
}
