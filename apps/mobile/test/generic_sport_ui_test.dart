// Pantalla genérica de un deporte del catálogo (Fase 4 · 4.5): lista y ficha alimentadas por el contrato, mercados por
// familia, bloques de contenido, definición de pantallas y paridad con NBA.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/home_agenda.dart';
import 'package:gobet/product/home_sport.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_shapes.dart';
import 'package:gobet/product/sport_contract.dart';
import 'package:gobet/product/sport_detail.dart';
import 'package:gobet/product/sport_images.dart';
import 'package:gobet/product/sport_markets.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

import 'sport_contract_test.dart' show evento, golfEntry, mercado;

final api = QuantFutApi(base: Uri.parse('https://x.test'));
final now = DateTime(2026, 11, 13, 9);

Map<String, Object?> sec(String id, String seccion, {bool visible = true}) => {
  'id': id,
  'tipo': 'seccion',
  'seccion': seccion,
  'visible': visible,
  'params': <String, Object?>{},
};

Map<String, Object?> aviso(String id, Map<String, Object?> texto, {String? tono}) => {
  'id': id,
  'tipo': 'aviso',
  'visible': true,
  'params': {'texto': texto, 'tono': ?tono},
};

Map<String, Object?> vip(String id) => {'id': id, 'tipo': 'vip', 'visible': true, 'params': <String, Object?>{}};

void useCatalog({Map<String, Object?>? pantallas}) {
  sportCatalogNotifier.value = SportCatalog.fromJson({
    'deportes': [
      {'id': 'futbol', 'orden': 1, 'estado': 'on', 'nombre': {'es': 'Fútbol'}, 'icono': 'futbol', 'color': '#00ff88', 'secciones': ['high', 'ladder', 'parley']},
      {'id': 'nba', 'orden': 2, 'estado': 'on', 'nombre': {'es': 'NBA'}, 'icono': 'baloncesto', 'color': '#ff8800', 'secciones': ['high']},
      golfEntry(),
    ],
    'pantallas': ?pantallas,
  })!;
}

SportEvent golfEvent(String id, {int hours = 30, List<Object?>? markets, String status = 'scheduled'}) =>
    contractEvent(
      {
        ...evento(id, markets: markets, status: status),
        'start': now.toUtc().add(Duration(hours: hours)).toIso8601String(),
        'sealed_at': '2026-11-12T10:00:00Z',
      },
      'golf',
    )!;

Future<void> pumpApp(WidgetTester tester, Widget body, {String code = 'es'}) async {
  tester.view.physicalSize = const Size(390, 2600);
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
      home: Scaffold(body: body),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}

Future<void> pumpHome(
  WidgetTester tester, {
  SportId sport = 'golf',
  required SportFeed feed,
  ValueChanged<SportEvent>? onOpen,
  VoidCallback? onVip,
  Future<void> Function()? onRetry,
  String code = 'es',
}) => pumpApp(
  tester,
  HomeSport(
    api: api,
    sport: sport,
    feed: feed,
    images: ImageCatalog.empty,
    now: now,
    onOpen: onOpen ?? (_) {},
    onRetry: onRetry ?? () async {},
    onVip: onVip,
  ),
  code: code,
);

List<Object?> blocksJson() => [
  {'id': 'futuro', 'tipo': 'mapa', 'titulo': 'Mapa del futuro'},
  {
    'id': 'demo_tabla', 'tipo': 'tabla', 'titulo': 'Tabla demo',
    'columnas': ['Equipo', 'Valor'],
    'filas': [['Equipo A', 12], ['Equipo B', 9]],
  },
  {
    'id': 'demo_barras', 'tipo': 'barras', 'titulo': 'Barras demo',
    'items': [{'etiqueta': 'Dato A', 'valor': .6}, {'etiqueta': 'Dato B', 'valor': .3, 'nota': 'nota b'}],
  },
  {
    'id': 'demo_pares', 'tipo': 'pares', 'titulo': 'Pares demo',
    'items': [{'etiqueta': 'Rachas', 'valor': 7}, {'etiqueta': 'Líder', 'valor': 'Equipo B'}],
  },
  {'id': 'demo_texto', 'tipo': 'texto', 'titulo': 'Nota demo', 'cuerpo': 'Es una <b>demo</b> & nada más'},
  {'id': 'roto', 'tipo': 'barras', 'titulo': 'Roto', 'items': [{'etiqueta': 'X', 'valor': 5}]},
];

ContractDetail detailFor(SportEvent e, {List<Object?>? blocks}) => ContractDetail(
  event: e,
  families: contractFamilies(e.markets, catalogFamilyIds('golf')),
  blocks: contentBlocks(blocks ?? blocksJson()),
);

SportEvent richEvent() => golfEvent(
  'e1',
  markets: [
    mercado('m1', label: 'Demo · Más de 2.5', family: 'totales', principal: true),
    mercado('m2', label: 'Demo · Gana Equipo A', family: 'resultado', p: .45),
    mercado('m3', label: 'Demo · Ambos anotan', family: 'especiales', p: .6),
    mercado('m4', label: 'Demo · Sin sellar a tiempo', family: 'resultado', eligible: false),
  ],
);

Future<void> pumpDetail(
  WidgetTester tester, {
  ContractDetailLoader? loader,
  VoidCallback? onVip,
  String code = 'es',
}) => pumpApp(
  tester,
  GenericSportDetail(
    api: api,
    event: richEvent(),
    images: ImageCatalog.empty,
    onVip: onVip,
    loader: loader ?? (e, lang) async => detailFor(richEvent()),
  ),
  code: code,
);

double top(WidgetTester tester, Finder f) => tester.getTopLeft(f).dy;

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
  setUp(useCatalog);
  tearDown(() {
    sportCatalogNotifier.value = SportCatalog.builtIn;
    AppLocale.instance.reset();
  });

  group('lista (HomeSport)', () {
    SportFeed feed() => SportFeed(ready: true, events: [golfEvent('e1'), golfEvent('e2', hours: 50)]);

    testWidgets('sin definición: el orden de hoy con destacado, tira de días y partidos; tocar abre el evento', (tester) async {
      SportEvent? opened;
      await pumpHome(tester, feed: feed(), onOpen: (e) => opened = e);
      expect(find.byType(DayStrip), findsOneWidget);
      expect(find.byKey(const ValueKey('sport-event-e1')), findsOneWidget);
      expect(find.byKey(const ValueKey('sport-event-e2')), findsOneWidget);
      expect(find.text('Equipo A'), findsWidgets);
      expect(find.text(AppLocale.instance.l10n.homeFeatured.toUpperCase()), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('sport-event-e2')));
      expect(opened!.id, 'e2');
      expect(opened!.sport, 'golf');
    });

    testWidgets('feed caído: aviso con «Reintentar» (nunca en blanco) y reintenta', (tester) async {
      var retried = 0;
      await pumpHome(tester, feed: const SportFeed(ready: false, events: []), onRetry: () async => retried++);
      expect(find.text(AppLocale.instance.l10n.homeFeedError), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('sport-feed-retry')));
      expect(retried, 1);
    });

    testWidgets('definición: orden, sección oculta, aviso con idioma, llamada VIP', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            'golf': [
              aviso('av', {'es': 'Aviso en español', 'en': 'Notice in English'}, tono: 'aviso'),
              sec('s1', 'partidos'),
              vip('vip1'),
              sec('s2', 'dias', visible: false),
              sec('s3', 'destacado', visible: false),
              {'id': 'raro', 'tipo': 'carrusel', 'visible': true},
              sec('s4', 'inventada'),
            ],
          },
        },
      );
      var vips = 0;
      await pumpHome(tester, feed: feed(), onVip: () => vips++);
      expect(find.byType(DayStrip), findsNothing, reason: 'dias oculta');
      expect(find.text(AppLocale.instance.l10n.homeFeatured.toUpperCase()), findsNothing, reason: 'destacado oculto');
      expect(find.text('Aviso en español'), findsOneWidget);
      expect(top(tester, find.text('Aviso en español')), lessThan(top(tester, find.byKey(const ValueKey('sport-event-e1')))));
      expect(top(tester, find.byKey(const ValueKey('sport-event-e1'))), lessThan(top(tester, find.byKey(const ValueKey('sport-vip-call')))));
      await tester.tap(find.byKey(const ValueKey('sport-vip-call')));
      expect(vips, 1);
    });

    testWidgets('aviso en inglés y caída a español en un idioma sin traducción', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            '*': [aviso('av', {'es': 'Hola', 'en': 'Hello'}), sec('s', 'partidos')],
          },
        },
      );
      await pumpHome(tester, feed: feed(), code: 'en');
      expect(find.text('Hello'), findsOneWidget);
      await pumpHome(tester, feed: feed(), code: 'de');
      expect(find.text('Hola'), findsOneWidget);
    });

    testWidgets('el deporte concreto gana sobre «*»', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            '*': [aviso('general', {'es': 'Para todos'}), sec('s', 'partidos')],
            'golf': [aviso('propio', {'es': 'Solo golf'}), sec('s', 'partidos')],
          },
        },
      );
      await pumpHome(tester, feed: feed());
      expect(find.text('Solo golf'), findsOneWidget);
      expect(find.text('Para todos'), findsNothing);
    });

    testWidgets('resumen oculto quita el encabezado de cada día; los partidos siguen', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            '*': [sec('a', 'dias'), sec('b', 'resumen', visible: false), sec('c', 'partidos')],
          },
        },
      );
      await pumpHome(tester, feed: feed());
      expect(find.byType(DayStrip), findsOneWidget);
      expect(find.text(AppLocale.instance.l10n.calendarMatchesCount(1)), findsNothing);
      expect(find.byKey(const ValueKey('sport-event-e1')), findsOneWidget);
    });

    testWidgets('una lista sin secciones visibles se trata como sin definición', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            '*': [sec('a', 'partidos', visible: false), aviso('av', {'es': 'No debe verse'})],
          },
        },
      );
      await pumpHome(tester, feed: feed());
      expect(find.byType(DayStrip), findsOneWidget);
      expect(find.text('No debe verse'), findsNothing);
    });
  });

  group('ficha (GenericSportDetail)', () {
    testWidgets('cabecera, pronóstico, mercados por familia con nombres del catálogo, bloques y sello', (tester) async {
      await pumpDetail(tester);
      await tester.pumpAndSettle();
      expect(find.text('DEMOSTRACIÓN'), findsOneWidget);
      expect(find.text('Equipo A'), findsWidgets);
      // Destacado y principal, con la etiqueta del contrato.
      expect(find.text('Demo · Más de 2.5'), findsWidgets);
      // Familias del catálogo en orden, con `especiales` (fuera del catálogo) y sin la que solo tiene mercados no elegibles.
      final result = find.byKey(const ValueKey('generic-family-resultado'));
      final totals = find.byKey(const ValueKey('generic-family-totales'));
      final special = find.byKey(const ValueKey('generic-family-especiales'));
      expect(result, findsOneWidget);
      expect((tester.widget<Text>(result).data), 'RESULTADO');
      expect(top(tester, result), lessThan(top(tester, totals)));
      expect(top(tester, totals), lessThan(top(tester, special)));
      expect((tester.widget<Text>(special).data), 'ESPECIALES');
      expect(find.text('Demo · Sin sellar a tiempo'), findsNothing, reason: 'solo lo sellado antes del inicio');
      // Bloques de contenido: los cuatro, sin el tipo desconocido ni el mal formado.
      expect(find.text('Tabla demo'), findsOneWidget);
      expect(find.byType(Table), findsOneWidget);
      expect(find.text('Barras demo'), findsOneWidget);
      expect(find.text('nota b'), findsOneWidget);
      expect(find.text('Pares demo'), findsOneWidget);
      expect(find.text('Líder'), findsOneWidget);
      expect(find.text('Equipo B'), findsWidgets);
      expect(find.text('Nota demo'), findsOneWidget);
      expect(find.text('Mapa del futuro'), findsNothing);
      expect(find.text('Roto'), findsNothing);
      // Texto plano: nada de HTML interpretado.
      expect(find.text('Es una <b>demo</b> & nada más'), findsOneWidget);
      expect(find.byType(SealLine), findsOneWidget);
      // Nada de NBA ni de tenis: sin pestañas de análisis, H2H ni alertas.
      expect(find.text(AppLocale.instance.l10n.detailTabH2h), findsNothing);
      expect(find.text(AppLocale.instance.l10n.detailTabAlerts), findsNothing);
    });

    testWidgets('en inglés usa los nombres de familia en inglés y cae a español donde falta', (tester) async {
      await pumpDetail(tester, code: 'en');
      await tester.pumpAndSettle();
      expect(tester.widget<Text>(find.byKey(const ValueKey('generic-family-resultado'))).data, 'RESULT');
      expect(tester.widget<Text>(find.byKey(const ValueKey('generic-family-especiales'))).data, 'ESPECIALES');
    });

    testWidgets('pide el detalle en el idioma de la app', (tester) async {
      final langs = <String>[];
      await pumpDetail(tester, code: 'pt', loader: (e, lang) async {
        langs.add(lang);
        return detailFor(e);
      });
      await tester.pumpAndSettle();
      expect(langs, ['pt']);
    });

    testWidgets('definición de partido: orden, ocultas, aviso, VIP y secciones de NBA/tenis ignoradas', (tester) async {
      useCatalog(
        pantallas: {
          'partido': {
            'golf': [
              sec('a', 'contenido'),
              aviso('av', {'es': 'Aviso del partido'}, tono: 'peligro'),
              sec('b', 'h2h'),
              sec('c', 'mercados'),
              sec('d', 'cabecera', visible: false),
              sec('e', 'pronostico', visible: false),
              sec('f', 'sello', visible: false),
              vip('v'),
            ],
          },
        },
      );
      var vips = 0;
      await pumpDetail(tester, onVip: () => vips++);
      await tester.pumpAndSettle();
      expect(find.text('DEMOSTRACIÓN'), findsNothing, reason: 'cabecera oculta');
      expect(find.byType(SealLine), findsNothing, reason: 'sello oculto');
      expect(find.text('Demo · Más de 2.5'), findsOneWidget, reason: 'pronóstico oculto: queda solo la fila de la familia');
      final content = find.text('Tabla demo'), notice = find.text('Aviso del partido'), families = find.byKey(const ValueKey('generic-family-resultado'));
      expect(top(tester, content), lessThan(top(tester, notice)));
      expect(top(tester, notice), lessThan(top(tester, families)));
      expect(top(tester, families), lessThan(top(tester, find.byKey(const ValueKey('sport-vip-call')))));
      await tester.tap(find.byKey(const ValueKey('sport-vip-call')));
      expect(vips, 1);
    });

    testWidgets('sin mercados elegibles: nota neutra, nunca en blanco', (tester) async {
      final e = golfEvent('e9', markets: [mercado('x', eligible: false)]);
      await pumpApp(
        tester,
        GenericSportDetail(api: api, event: e, images: ImageCatalog.empty, loader: (ev, lang) async => detailFor(e, blocks: [])),
      );
      await tester.pumpAndSettle();
      expect(find.text(AppLocale.instance.l10n.detailNoPicks), findsOneWidget);
    });

    testWidgets('si el contrato falla: error con «Reintentar» y, al reintentar, el contenido', (tester) async {
      var calls = 0;
      await pumpDetail(tester, loader: (e, lang) async {
        if (++calls == 1) throw const ApiFailure('503', 503);
        return detailFor(e);
      });
      await tester.pumpAndSettle();
      expect(find.text(AppLocale.instance.l10n.sportDetailError), findsOneWidget);
      expect(find.text('DEMOSTRACIÓN'), findsOneWidget, reason: 'la cabecera del evento de la lista sigue a la vista');
      await tester.tap(find.byKey(const ValueKey('sport-detail-retry')));
      await tester.pumpAndSettle();
      expect(find.text(AppLocale.instance.l10n.sportDetailError), findsNothing);
      expect(find.byKey(const ValueKey('generic-family-totales')), findsOneWidget);
      expect(calls, 2);
    });
  });

  group('mercados por familia (pestaña Mercados)', () {
    testWidgets('familias del catálogo con sus nombres y «otros» al final', (tester) async {
      await AppLocale.instance.select('en');
      final feed = SportFeed(ready: true, events: [richEvent()]);
      final families = familyPicks(AppLocale.instance.l10n, 'golf', feed);
      expect(families.map((f) => f.family), ['resultado', 'totales', 'especiales']);
      expect(families.map((f) => f.title), ['Result', 'Totals', 'Especiales']);
      final other = golfEvent('e5', markets: [mercado('z', family: '')]);
      final withOther = familyPicks(AppLocale.instance.l10n, 'golf', SportFeed(ready: true, events: [richEvent(), other]));
      expect(withOther.last.family, otherFamily);
      expect(withOther.last.title, 'Other');
    });

    testWidgets('la pestaña se pinta con una tarjeta por familia y error con «Reintentar» si el feed falla', (tester) async {
      await pumpApp(tester, SportMarkets(api: api, sport: 'golf', feed: SportFeed(ready: true, events: [richEvent()]), images: ImageCatalog.empty));
      expect(find.text('Resultado'), findsWidgets);
      expect(find.text('Totales'), findsWidgets);
      await pumpApp(tester, SportMarkets(api: api, sport: 'golf', feed: const SportFeed(ready: false, events: []), images: ImageCatalog.empty));
      expect(find.byKey(const ValueKey('sport-feed-retry')), findsOneWidget);
    });
  });

  group('paridad con NBA', () {
    testWidgets('una definición de pantallas no cambia la lista de NBA', (tester) async {
      useCatalog(
        pantallas: {
          'deporte': {
            '*': [aviso('av', {'es': 'No para NBA'}), sec('s', 'partidos'), sec('d', 'dias', visible: false)],
          },
        },
      );
      final e = SportEvent(
        id: '1',
        sport: kNba,
        home: 'Miami Heat',
        away: 'New York Knicks',
        league: 'NBA',
        start: now.toUtc().add(const Duration(hours: 30)),
        status: 'scheduled',
        seal: 'abc',
        sealedAt: DateTime.utc(2020),
        markets: [
          SportMarket(id: 'w', label: 'w', selection: 'Miami Heat', probability: .7, sealedAt: DateTime.utc(2020), eligible: true, market: 'winner'),
        ],
      );
      await pumpHome(tester, sport: kNba, feed: SportFeed(ready: true, events: [e]));
      expect(find.byType(DayStrip), findsOneWidget);
      expect(find.text('No para NBA'), findsNothing);
      expect(find.byKey(const ValueKey('sport-event-1')), findsOneWidget);
    });
  });
}
