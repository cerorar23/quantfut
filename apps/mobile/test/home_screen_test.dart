// Inicio: tira de días, partidos agrupados por día en orden cronológico, boletos del día,
// resumen y menú «Más» con la guía. Sin filtros de horas ni atajos duplicados arriba.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/home_agenda.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_home.dart';
import 'package:gobet/product/live_more.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

class _Api extends QuantFutApi {
  _Api({this.parley = true});
  final bool parley;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    if (path == '/mobile/v1/rewards') {
      return {
        'wallet': {'balance': 240},
      };
    }
    if (path == '/parley') {
      if (!parley) throw const ApiFailure('sin parley');
      return {
        'activo': true,
        'dias': [
          {
            'tickets': [
              {
                'cuota_total': 3.2,
                'prob_total': .45,
                'patas': [<String, dynamic>{}, <String, dynamic>{}],
              },
            ],
          },
        ],
      };
    }
    return {};
  }
}

DateTime day(int offset) {
  final n = DateTime.now();
  return DateTime(n.year, n.month, n.day + offset);
}

Map<String, dynamic> match(
  String id,
  String home,
  DateTime day,
  int hour, {
  String league = 'Liga de prueba',
  Map<String, dynamic>? probabilities,
  bool noForecast = false,
  DateTime? unlock,
}) => {
  'match_id': id,
  'kickoff_utc': DateTime(day.year, day.month, day.day, hour, 30)
      .toUtc()
      .toIso8601String(),
  'estado': 'scheduled',
  'local': {'nombre': home},
  'visitante': {'nombre': 'Rival de $home'},
  'liga': {'nombre': league},
  'probabilities': noForecast
      ? null
      : probabilities ?? {'home': .43, 'draw': .26, 'away': .31},
  if (unlock != null) 'pronostico_desde': unlock.toUtc().toIso8601String(),
};

Map<String, dynamic> pick(String id, double prob, {bool locked = false}) => {
  'match_id': id,
  'local': 'Lens',
  'visitante': 'Sporting',
  'market': 'totals',
  'selection': 'over',
  'line': 1.5,
  'texto': 'Más de 1,5 goles',
  'prob': prob,
  'ref_price': 1.3,
  'locked': locked,
};

Map<String, dynamic> homeData({
  List<Map<String, dynamic>>? agenda,
  List<Map<String, dynamic>>? picks,
  bool history = true,
}) => {
  'config': {
    'features': {
      for (final k in ['agenda', 'alta_probabilidad', 'escalera'])
        k: {'enabled': true, 'message': ''},
    },
  },
  // Desordenado a propósito: la pantalla debe ordenarlo.
  'agenda':
      agenda ??
      [
        match('b2', 'Mañana B', day(1), 20),
        match('a2', 'Hoy Tarde', day(0), 21),
        match('b1', 'Mañana A', day(1), 12),
        match('a1', 'Hoy Pronto', day(0), 9),
        match('c1', 'Pasado', day(3), 15),
      ],
  'alta_probabilidad': {
    'proximos':
        picks ?? [pick('a1', .78), pick('b1', .91), pick('b2', .85, locked: true)],
    'vip': <Map<String, dynamic>>[],
    if (history) 'historial': {'acierto_real': 78.2, 'n': 40, 'aciertos': 31},
  },
};

Future<void> pump(
  WidgetTester tester, {
  JsonMap? data,
  QuantFutApi? api,
  Size size = const Size(390, 844),
  String code = 'es',
  String banner = '',
  bool maintenance = false,
  ValueChanged<String>? onMatch,
  ValueChanged<String>? onPredictions,
  VoidCallback? onCoins,
  ValueChanged<DateTime>? onPickDate,
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
      home: Scaffold(
        body: HomeTab(
          api: api ?? _Api(),
          data: data ?? homeData(),
          selected: day(0),
          busy: false,
          banner: banner,
          maintenance: maintenance,
          onRefresh: () async {},
          onPickDate: onPickDate ?? (_) {},
          onOpenMatch: onMatch ?? (_) {},
          onOpenPredictions: onPredictions ?? (_) {},
          onOpenCoins: onCoins ?? () {},
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 300));
}

Finder get scroller => find
    .descendant(
      of: find.byKey(const ValueKey('home-scroll')),
      matching: find.byType(Scrollable),
    )
    .first;

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

  test('groupAgenda ordena por hora y agrupa por día local', () {
    final days = groupAgenda([
      match('3', 'C', day(1), 8),
      match('1', 'A', day(0), 22),
      match('2', 'B', day(0), 7),
      {'match_id': 'x', 'kickoff_utc': 'no es una fecha'},
    ]);
    expect(days.map((d) => d.matches.map((m) => m['match_id']).toList()).toList(), [
      ['2', '1'],
      ['3'],
    ]);
    expect(days.first.key, dateKey(day(0)));
  });

  testWidgets('arriba no hay atajos ni filtros de horas', (tester) async {
    await pump(tester);
    expect(find.text('ALTA PROBABILIDAD'), findsOneWidget); // solo la tarjeta del boleto
    expect(find.text('Alta probabilidad'), findsNothing);
    expect(find.text('Reto Escalera'), findsNothing);
    for (final chip in ['+48 h', '+1 h', '+3 h', '+6 h', '+12 h']) {
      expect(find.text(chip), findsNothing);
    }
    expect(find.byType(ChoiceChip), findsNothing);
  });

  testWidgets('partidos por día, en orden cronológico y con su resultado más probable', (
    tester,
  ) async {
    await pump(tester);
    await tester.scrollUntilVisible(find.text('Mañana A'), 200, scrollable: scroller);
    expect(find.textContaining('Hoy ·'), findsOneWidget);
    expect(find.textContaining('Mañana ·'), findsOneWidget);
    expect(find.text('Hoy Pronto'), findsOneWidget);
    expect(find.text('Hoy Tarde'), findsOneWidget);
    double y(String t) => tester.getTopLeft(find.text(t)).dy;
    expect(y('Hoy Pronto'), lessThan(y('Hoy Tarde')));
    expect(y('Hoy Tarde'), lessThan(y('Mañana A')));
    expect(find.text('Local 43 %'), findsWidgets);
    expect(find.text('2 enfrentamientos'), findsWidgets);
  });

  testWidgets('tocar un día de la tira salta a sus partidos; uno vacío avisa', (tester) async {
    await pump(tester);
    expect(tester.widget<DayStrip>(find.byType(DayStrip)).active, dateKey(day(0)));
    await tester.tap(find.byKey(ValueKey('day-${dateKey(day(3))}')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));
    expect(tester.widget<DayStrip>(find.byType(DayStrip)).active, dateKey(day(3)));
    expect(find.text('Pasado'), findsOneWidget);
    // El día 2 no tiene partidos.
    await tester.tap(find.byKey(ValueKey('day-${dateKey(day(2))}')));
    await tester.pump();
    expect(find.text('No hay partidos este día.'), findsOneWidget);
  });

  testWidgets('al desplazarse, el día activo de la tira sigue a la lista', (tester) async {
    await pump(tester);
    await tester.scrollUntilVisible(find.text('Pasado'), 200, scrollable: scroller);
    await tester.pump(const Duration(milliseconds: 300));
    final strip = tester.widget<DayStrip>(find.byType(DayStrip));
    expect(strip.active == dateKey(day(0)), isFalse);
    expect(strip.counts.keys, containsAll([dateKey(day(0)), dateKey(day(1)), dateKey(day(3))]));
  });

  testWidgets('el buscador filtra por equipo o liga', (tester) async {
    await pump(tester);
    expect(find.byKey(const ValueKey('home-search')), findsNothing); // plegado
    await tester.tap(find.byKey(const ValueKey('day-search')));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.enterText(find.byKey(const ValueKey('home-search')), 'pasado');
    await tester.pump();
    await tester.scrollUntilVisible(find.text('Pasado'), 200, scrollable: scroller);
    expect(find.text('Hoy Pronto'), findsNothing);
    expect(find.text('Mañana A'), findsNothing);
    await tester.enterText(find.byKey(const ValueKey('home-search')), 'zzz');
    await tester.pump();
    expect(find.text('No hay enfrentamientos para estos filtros.'), findsOneWidget);
    // Cerrar la búsqueda la limpia y vuelven todos los partidos.
    await tester.tap(find.byKey(const ValueKey('day-search')));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byKey(const ValueKey('home-search')), findsNothing);
    expect(find.text('No hay enfrentamientos para estos filtros.'), findsNothing);
  });

  testWidgets('los días futuros enseñan el partido con candado hasta que se calcula', (
    tester,
  ) async {
    final future = DateTime.utc(day(3).year, day(3).month, day(3).day, 9); // 03:00 MX
    await pump(
      tester,
      data: homeData(
        agenda: [
          match('a1', 'Hoy Con', day(0), 15),
          match('c1', 'Futuro Sin', day(3), 15, noForecast: true, unlock: future),
          // Ya pasó su hora de cálculo y sigue sin probabilidad: no se finge un candado.
          match(
            'c2',
            'Pasado Sin',
            day(3),
            17,
            noForecast: true,
            unlock: DateTime.now().subtract(const Duration(hours: 1)),
          ),
        ],
        picks: [],
      ),
    );
    await tester.scrollUntilVisible(find.text('Futuro Sin'), 200, scrollable: scroller);
    expect(find.byIcon(Icons.lock_clock), findsNWidgets(2)); // icono + etiqueta
    expect(find.textContaining('Pronóstico el '), findsOneWidget);
    expect(find.textContaining('3:00 en México'), findsOneWidget);
    Finder likely(String id) => find.descendant(
      of: find.byKey(ValueKey('match-$id')),
      matching: find.text('Local 43 %'),
    );
    expect(likely('c1'), findsNothing);
    expect(likely('c2'), findsNothing);
    expect(likely('a1'), findsOneWidget);
  });

  testWidgets('abre el partido al tocarlo', (tester) async {
    String? opened;
    await pump(tester, onMatch: (id) => opened = id);
    await tester.scrollUntilVisible(find.text('Hoy Pronto'), 200, scrollable: scroller);
    await tester.tap(find.text('Hoy Pronto'));
    expect(opened, 'a1');
  });

  testWidgets('boletos del día: el pronóstico de mayor probabilidad y el parley', (tester) async {
    String? stream;
    String? opened;
    await pump(tester, onPredictions: (s) => stream = s, onMatch: (id) => opened = id);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Boletos del día'), findsOneWidget);
    // De los abiertos gana el de 91 %, no el bloqueado ni el de 78 %.
    expect(find.text('91 %'), findsOneWidget);
    expect(find.text('Más de 1,5 goles'), findsOneWidget);
    expect(find.text('Cuota 3,20'), findsOneWidget);
    expect(find.text('2 selecciones'), findsOneWidget);
    expect(find.text('Prob. conjunta 45 %'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('ticket-high')));
    expect(opened, 'b1');
    await tester.tap(find.byKey(const ValueKey('ticket-parley')));
    expect(stream, 'parley');
    await tester.tap(find.text('Ver todo'));
    expect(stream, 'high');
  });

  testWidgets('sin parley ni pronósticos las tarjetas lo dicen', (tester) async {
    await pump(tester, api: _Api(parley: false), data: homeData(picks: [], history: false));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Aún no hay boletos hoy'), findsNWidgets(2));
    // Sin historial liquidado no se enseña una tarjeta de acierto vacía.
    expect(find.byKey(const ValueKey('home-hit')), findsNothing);
  });

  testWidgets('resumen: monedas reales y acierto histórico real', (tester) async {
    var coins = 0;
    String? stream;
    await pump(tester, onCoins: () => coins++, onPredictions: (s) => stream = s);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('240'), findsOneWidget);
    expect(find.text('78,2 %'), findsOneWidget);
    expect(find.text('31 de 40 pronósticos'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('home-coins')));
    expect(coins, 1);
    await tester.tap(find.byKey(const ValueKey('home-hit')));
    expect(stream, 'high');
  });

  testWidgets('el aviso de Remote Config se puede cerrar y el de mantenimiento se ve', (
    tester,
  ) async {
    await pump(tester, banner: 'Aviso real', maintenance: true);
    expect(find.text('Aviso real'), findsOneWidget);
    expect(find.byIcon(Icons.build_circle_outlined), findsOneWidget);
    await tester.tap(find.byTooltip('Cerrar aviso'));
    await tester.pump();
    expect(find.text('Aviso real'), findsNothing);
  });

  testWidgets('el calendario completo entrega la fecha elegida', (tester) async {
    DateTime? picked;
    await pump(tester, onPickDate: (d) => picked = d);
    await tester.tap(find.byKey(const ValueKey('day-picker')));
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining(RegExp('aceptar', caseSensitive: false)));
    await tester.pumpAndSettle();
    expect(picked, isNotNull);
  });

  testWidgets('menú Más: guía, evaluar, compartir y documentos legales', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await AppLocale.instance.select('es');
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () => showMoreSheet(context),
              child: const Text('abrir'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('abrir'));
    await tester.pumpAndSettle();
    for (final label in [
      'Guía de pronósticos',
      'Evaluar la app',
      'Compartir la app',
      'Términos de uso',
      'Política de privacidad',
    ]) {
      expect(find.text(label), findsOneWidget, reason: label);
    }
    await tester.tap(find.byKey(const ValueKey('more-guide')));
    await tester.pumpAndSettle();
    expect(find.text('Aprende a leer los datos antes de decidir.'), findsOneWidget);
    expect(find.text('Una probabilidad no es una certeza'), findsOneWidget);
    await tester.scrollUntilVisible(find.textContaining('no es una casa de apuestas'), 300);
    expect(find.textContaining('no es una casa de apuestas'), findsOneWidget);
    expect(find.textContaining('garantiza'), findsNothing); // la guía no promete ganancias
  });

  for (final code in languages) {
    testWidgets('Inicio se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 844), Size(320, 640)]) {
        await pump(
          tester,
          size: size,
          code: code,
          banner: 'Aviso',
          maintenance: true,
        );
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$code $size arriba');
        await tester.scrollUntilVisible(find.text('Pasado'), 300, scrollable: scroller);
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$code $size lista');
      }
    });
  }
}
