// Contrato común `/deportes/v1` en la app (Fase 4 · 4.5): conversión a eventos y mercados, familias del catálogo,
// bloques de contenido y lectura de lista y detalle.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/home_sport.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sport_contract.dart';
import 'package:gobet/product/sports.dart';
import 'package:gobet/product/sports_feed.dart';

Map<String, Object?> mercado(
  String id, {
  String label = 'Demo · Más de 2.5',
  double p = .55,
  String family = 'totales',
  bool eligible = true,
  String? outcome,
  bool principal = false,
  Object? price,
  String? reference,
}) => {
  'id': id,
  'label': label,
  'selection': 'over',
  'probability': p,
  'sealed_at': '2026-11-13T10:00:00Z',
  'eligible': eligible,
  'market': 'clave_$id',
  'family': family,
  'outcome': outcome,
  'principal': principal,
  'price': price,
  'reference': reference,
};

Map<String, Object?> evento(
  String id, {
  List<Object?>? markets,
  String status = 'scheduled',
  Object? destacado,
  Map<String, Object?>? imagenes,
}) => {
  'id': id,
  'sport': 'golf',
  'home': 'Equipo A',
  'away': 'Equipo B',
  'league': 'Demostración',
  'start': '2026-11-14T18:00:00Z',
  'status': status,
  'seal': 'abcdef123456',
  'sealed_at': '2026-11-13T10:00:00Z',
  'score': null,
  'bloqueados': 0,
  'imagenes': imagenes,
  'markets': markets ?? [mercado('m1', principal: true)],
  'destacado': destacado ?? 'm1',
};

Map<String, Object?> cartelera(List<Object?> eventos, {String deporte = 'golf'}) => {
  'contrato': 1,
  'deporte': deporte,
  'desde': '2026-11-10',
  'dias': 7,
  'eventos': eventos,
};

Map<String, Object?> golfEntry() => {
  'id': 'golf',
  'orden': 4,
  'estado': 'preview',
  'nombre': {'es': 'Golf', 'en': 'Golf'},
  'icono': 'golf',
  'color': '#00aa55',
  'secciones': ['high'],
  'familias': [
    {'id': 'resultado', 'orden': 1, 'nombre': {'es': 'Resultado', 'en': 'Result'}},
    {'id': 'totales', 'orden': 2, 'nombre': {'es': 'Totales', 'en': 'Totals'}},
  ],
};

class _Api extends QuantFutApi {
  _Api(this.routes) : super(base: Uri.parse('https://x.test'));
  final Map<String, Object?> routes;
  final calls = <(String, JsonMap?)>[];
  @override
  Future<dynamic> request(String path, {JsonMap? query, JsonMap? body, bool retry = true}) async {
    calls.add((path, query));
    final r = routes[path];
    if (r == null) throw const ApiFailure('no', 404);
    if (r is Exception) throw r;
    return r;
  }
}

void main() {
  tearDown(() => sportCatalogNotifier.value = SportCatalog.builtIn);

  test('quién es genérico: todo menos fútbol, NBA y tenis', () {
    expect([kFootball, kNba, kTennis].any(isGenericSport), isFalse);
    expect(isGenericSport('golf'), isTrue);
  });

  test('un evento del contrato se convierte al SportEvent de la app', () {
    final e = contractEvent(
      evento('e1', imagenes: {'home': '/web/img/a.png', 'away': 'https://otro.test/x.png'}),
      'golf',
    )!;
    expect([e.id, e.sport, e.home, e.away, e.league, e.status], ['e1', 'golf', 'Equipo A', 'Equipo B', 'Demostración', 'scheduled']);
    expect(e.start, DateTime.utc(2026, 11, 14, 18));
    expect(e.generic, isTrue);
    expect(e.serverFeatured, isTrue);
    expect(e.featuredId, 'm1');
    expect(e.imageHome, '/web/img/a.png');
    expect(e.imageAway, isNull, reason: 'solo imágenes propias del servidor');
    final m = e.markets.single;
    expect([m.id, m.label, m.family, m.principal, m.eligible, m.publishable], ['m1', 'Demo · Más de 2.5', 'totales', true, true, true]);
    expect(m.probability, .55);
    expect(featuredMarket(e)!.id, 'm1');
  });

  test('un evento o mercado mal formado se descarta; el estado desconocido es programado', () {
    expect(contractEvent({'id': 'x'}, 'golf'), isNull);
    expect(contractEvent({...evento('e1'), 'start': 'ayer'}, 'golf'), isNull);
    final e = contractEvent(
      evento(
        'e1',
        status: 'suspendido',
        markets: [
          mercado('ok'),
          mercado('cero', p: 0),
          mercado('uno', p: 1),
          {...mercado('sineligible'), 'eligible': null},
          'basura',
          {...mercado('sinlabel'), 'label': ''},
        ],
      ),
      'golf',
    )!;
    expect(e.status, 'scheduled');
    expect(e.markets.map((m) => m.id), ['ok']);
  });

  test('resultado válido y cuota solo con su origen', () {
    final e = contractEvent(
      evento('e1', markets: [
        mercado('a', outcome: 'win', price: 1.9, reference: ' Pinnacle '),
        mercado('b', outcome: 'raro', price: 1.9),
        mercado('c', price: 1.0, reference: 'X'),
        mercado('d', family: ''),
      ]),
      'golf',
    )!;
    final a = e.markets[0], b = e.markets[1], c = e.markets[2], d = e.markets[3];
    expect([a.outcome, a.price, a.book], ['win', 1.9, 'Pinnacle']);
    expect([b.outcome, b.price, b.book], [null, null, null]);
    expect(c.price, isNull);
    expect(d.family, otherFamily, reason: 'sin familia → otros');
  });

  test('cartelera: exige contrato 1 y el mismo deporte; ordena por inicio', () {
    expect(() => contractEvents(cartelera([], deporte: 'tenis'), 'golf'), throwsFormatException);
    expect(() => contractEvents({...cartelera([]), 'contrato': 2}, 'golf'), throwsFormatException);
    expect(() => contractEvents(null, 'golf'), throwsFormatException);
    final late = {...evento('tarde'), 'start': '2026-11-15T10:00:00Z'};
    final events = contractEvents(cartelera([late, evento('pronto'), 'basura']), 'golf');
    expect(events.map((e) => e.id), ['pronto', 'tarde']);
  });

  test('loadContractSport pide 7 días desde tres antes, con la zona horaria', () async {
    final api = _Api({'/deportes/v1/golf/cartelera': cartelera([evento('e1')])});
    final feed = await loadContractSport(api, 'golf', now: DateTime(2026, 11, 13, 9));
    expect(feed.ready, isTrue);
    expect(feed.events.single.id, 'e1');
    final (path, query) = api.calls.single;
    expect(path, '/deportes/v1/golf/cartelera');
    expect(query!['cliente'], 'app');
    expect(query['contrato'], 1);
    expect(query['desde'], '2026-11-10');
    expect(query['dias'], 7);
    expect(query['tz'], DateTime(2026, 11, 13).timeZoneOffset.inMinutes);
  });

  test('loadSport: un deporte nuevo va por el contrato y un fallo es feed no listo', () async {
    final ok = await loadSport(_Api({'/deportes/v1/golf/cartelera': cartelera([evento('e1')])}), 'golf');
    expect(ok.ready, isTrue);
    expect(ok.events, hasLength(1));
    expect((await loadSport(_Api({}), 'golf')).ready, isFalse);
    expect((await loadSport(_Api({'/deportes/v1/golf/cartelera': cartelera([], deporte: 'otro')}), 'golf')).ready, isFalse);
  });

  group('familias', () {
    SportMarket m(String id, String? family) => contractMarket(
      mercado(id, family: family ?? ''),
      eventSealedAt: DateTime.utc(2026),
    )!;

    test('orden del catálogo, desconocidas por llegada y otros al final; las vacías no salen', () {
      final groups = contractFamilies(
        [m('1', 'totales'), m('2', 'rara'), m('3', 'resultado'), m('4', null), m('5', 'otra_rara')],
        ['resultado', 'totales'],
      );
      expect(groups.map((g) => g.id), ['resultado', 'totales', 'rara', 'otra_rara', 'otros']);
      expect(groups.map((g) => g.markets.length), [1, 1, 1, 1, 1]);
    });

    test('con las del endpoint de mercados se respeta su agrupación y lo suelto va a otros', () {
      final groups = contractFamilies(
        [m('1', 'totales'), m('2', 'totales'), m('3', 'resultado')],
        ['resultado', 'totales'],
        served: [('totales', ['1', 'inexistente']), ('resultado', [])],
      );
      expect(groups.map((g) => g.id), ['totales', 'otros']);
      expect(groups[1].markets.map((x) => x.id), ['2', '3']);
    });

    test('nombres del catálogo en el idioma actual, caída a es y otros traducido', () async {
      sportCatalogNotifier.value = SportCatalog.fromJson({
        'deportes': [golfEntry()],
      })!;
      await AppLocale.instance.select('en');
      final en = AppLocale.instance.l10n;
      expect(contractFamilyTitle(en, 'golf', 'resultado'), 'Result');
      expect(contractFamilyTitle(en, 'golf', otherFamily), 'Other');
      expect(contractFamilyTitle(en, 'golf', 'sin_nombre_x'), 'Sin nombre x');
      await AppLocale.instance.select('de');
      expect(contractFamilyTitle(AppLocale.instance.l10n, 'golf', 'totales'), 'Totales', reason: 'sin alemán → español');
      await AppLocale.instance.select('es');
    });
  });

  group('bloques de contenido', () {
    final tabla = {
      'id': 'demo_tabla', 'tipo': 'tabla', 'titulo': 'Tabla',
      'columnas': ['Equipo', 'Valor'],
      'filas': [['Equipo A', 12], ['Equipo B', null], ['C', 1234.5]],
    };
    final barras = {
      'id': 'demo_barras', 'tipo': 'barras', 'titulo': 'Barras',
      'items': [{'etiqueta': 'A', 'valor': .6, 'nota': 'n'}, {'etiqueta': 'B', 'valor': 0}],
    };
    final pares = {
      'id': 'demo_pares', 'tipo': 'pares', 'titulo': 'Pares',
      'items': [{'etiqueta': 'A', 'valor': 7}, {'etiqueta': 'B', 'valor': 'Equipo B'}, {'etiqueta': 'C', 'valor': null}],
    };
    final texto = {'id': 'demo_aviso', 'tipo': 'texto', 'titulo': 'Nota', 'cuerpo': 'Es una <b>demo</b> & ya'};

    test('los cuatro tipos se leen en orden, con celdas ya como texto', () {
      final blocks = contentBlocks([tabla, barras, pares, texto]);
      expect(blocks.map((b) => b.runtimeType), [TableBlock, BarsBlock, PairsBlock, TextBlock]);
      final t = blocks[0] as TableBlock;
      expect(t.columns, ['Equipo', 'Valor']);
      expect(t.rows[0], ['Equipo A', '12']);
      expect(t.rows[1], ['Equipo B', '—']);
      expect(t.rows[2][1], '1.234,5');
      expect((blocks[1] as BarsBlock).items.first.note, 'n');
      expect((blocks[2] as PairsBlock).items.map((i) => i.value), ['7', 'Equipo B', '—']);
      expect((blocks[3] as TextBlock).body, 'Es una <b>demo</b> & ya', reason: 'texto plano: no se interpreta');
    });

    test('un tipo desconocido se ignora y los demás siguen', () {
      final blocks = contentBlocks([
        {'id': 'futuro', 'tipo': 'mapa', 'titulo': 'Mapa', 'puntos': []},
        tabla,
      ]);
      expect(blocks.map((b) => b.id), ['demo_tabla']);
    });

    test('un bloque mal formado se ignora (sin lanzar)', () {
      final malos = <Object?>[
        'basura',
        {...tabla, 'id': 'MAYUS'},
        {...tabla, 'id': 'sin_titulo', 'titulo': ''},
        {...tabla, 'id': 'ancho_mal', 'filas': [['solo uno']]},
        {...tabla, 'id': 'celda_mala', 'filas': [['a', {'x': 1}]]},
        {...barras, 'id': 'fuera_de_rango', 'items': [{'etiqueta': 'A', 'valor': 1.5}]},
        {...pares, 'id': 'sin_etiqueta', 'items': [{'valor': 1}]},
        {...texto, 'id': 'vacio', 'cuerpo': ''},
        {...texto, 'id': 'largo', 'cuerpo': 'x' * 601},
        {...tabla, 'id': 'sin_columnas', 'columnas': <String>[], 'filas': <Object>[]},
      ];
      expect(contentBlocks([...malos, texto]).map((b) => b.id), ['demo_aviso']);
      expect(contentBlocks(null), isEmpty);
      expect(contentBlocks('x'), isEmpty);
    });

    test('un id repetido se ignora', () {
      expect(contentBlocks([texto, texto]), hasLength(1));
    });
  });

  group('detalle', () {
    const base = '/deportes/v1/golf/partido/e1';
    Map<String, Object?> partido({List<Object?>? bloques, String deporte = 'golf'}) => {
      'contrato': 1,
      'deporte': deporte,
      'evento': evento('e1', markets: [mercado('m1', family: 'totales', principal: true), mercado('m2', family: 'resultado')]),
      'bloques': bloques ?? [],
    };

    test('evento, familias del endpoint de mercados y bloques; pide el idioma de la app', () async {
      sportCatalogNotifier.value = SportCatalog.fromJson({'deportes': [golfEntry()]})!;
      final api = _Api({
        base: partido(bloques: [
          {'id': 't', 'tipo': 'texto', 'titulo': 'Nota', 'cuerpo': 'Hola'},
        ]),
        '$base/mercados': {
          'contrato': 1,
          'deporte': 'golf',
          'evento_id': 'e1',
          'familias': [
            {'id': 'resultado', 'mercados': [mercado('m2')]},
            {'id': 'totales', 'mercados': [mercado('m1')]},
          ],
        },
      });
      final d = await loadContractDetail(api, 'golf', 'e1', lang: 'pt');
      expect(d.event.markets, hasLength(2));
      expect(d.families.map((f) => f.id), ['resultado', 'totales']);
      expect(d.blocks.single, isA<TextBlock>());
      final detail = api.calls.firstWhere((c) => c.$1 == base).$2!;
      expect(detail['lang'], 'pt');
      expect(detail['cliente'], 'app');
    });

    test('si solo falla /mercados, las familias salen de los propios mercados', () async {
      sportCatalogNotifier.value = SportCatalog.fromJson({'deportes': [golfEntry()]})!;
      final d = await loadContractDetail(_Api({base: partido()}), 'golf', 'e1', lang: 'es');
      expect(d.families.map((f) => f.id), ['resultado', 'totales']);
    });

    test('si falla /partido o es de otro deporte, lanza', () async {
      expect(loadContractDetail(_Api({}), 'golf', 'e1', lang: 'es'), throwsA(anything));
      expect(loadContractDetail(_Api({base: partido(deporte: 'tenis')}), 'golf', 'e1', lang: 'es'), throwsFormatException);
    });
  });

  test('el texto del pronóstico de un deporte nuevo es la etiqueta del contrato', () {
    final m = contractMarket(mercado('m1', label: 'Demo · Más de 2.5'), eventSealedAt: DateTime.utc(2026))!;
    expect(sportPickText(AppLocale.instance.l10n, m), 'Demo · Más de 2.5');
  });
}
