// Definición de pantallas (Fase 4 · 4.5): lectura tolerante de `pantallas`, deporte concreto contra `'*'`, avisos con
// idioma y caída a español, parámetro `build` y tolerancia del almacén del catálogo.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/screen_definition.dart';
import 'package:gobet/product/sport_catalog_store.dart';
import 'package:gobet/product/sports.dart';

Map<String, Object?> sec(String id, String seccion, {bool visible = true}) => {
  'id': id,
  'tipo': 'seccion',
  'seccion': seccion,
  'visible': visible,
  'params': <String, Object?>{},
  'build_min_app': null,
};

Map<String, Object?> aviso(String id, Map<String, Object?> texto, {String? tono, String? enlace, bool visible = true}) => {
  'id': id,
  'tipo': 'aviso',
  'visible': visible,
  'params': {'texto': texto, 'tono': ?tono, 'enlace': ?enlace},
};

Map<String, Object?> sport(String id, int orden) => {
  'id': id,
  'orden': orden,
  'estado': 'on',
  'nombre': {'es': id},
  'icono': 'generico',
  'color': '#123456',
  'secciones': ['high'],
  'familias': <Object?>[],
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('lectura de pantallas', () {
    test('ausente o inservible: null (el orden de hoy)', () {
      expect(ScreenDefinitions.fromJson(null), isNull);
      expect(ScreenDefinitions.fromJson('x'), isNull);
      expect(ScreenDefinitions.fromJson({'deporte': []}), isNull);
      expect(ScreenDefinitions.fromJson({'deporte': {'*': 'no es lista'}}), isNull);
      expect(SportCatalog.builtIn.screens, isNull);
      expect(SportCatalog.fromJson({'deportes': [sport('golf', 1)]})!.screens, isNull);
    });

    test('deporte concreto gana sobre «*»', () {
      final defs = ScreenDefinitions.fromJson({
        'deporte': {
          '*': [sec('a', 'partidos'), sec('b', 'dias')],
          'golf': [sec('c', 'destacado')],
        },
      })!;
      expect(defs.resolve('deporte', 'golf')!.map((b) => b.section), ['destacado']);
      expect(defs.resolve('deporte', 'rugby')!.map((b) => b.section), ['partidos', 'dias']);
      expect(defs.resolve('partido', 'golf'), isNull);
    });

    test('tipo, sección y parámetros desconocidos se ignoran', () {
      final defs = ScreenDefinitions.fromJson({
        'deporte': {
          '*': [
            {'id': 'raro', 'tipo': 'carrusel', 'visible': true},
            sec('mala', 'inventada'),
            sec('ok', 'partidos'),
            {...sec('con_params', 'dias'), 'params': {'color': 'rojo', 'otro': 3}, 'extra': true},
            {'id': 'MAL ID', 'tipo': 'seccion', 'seccion': 'resumen'},
            'basura',
          ],
        },
      })!;
      expect(defs.resolve('deporte', 'golf')!.map((b) => b.id), ['ok', 'con_params']);
    });

    test('una sección repetida cuenta una vez y se recortan 20 bloques', () {
      final defs = ScreenDefinitions.fromJson({
        'deporte': {
          '*': [sec('a', 'partidos'), sec('b', 'partidos'), sec('c', 'dias')],
        },
      })!;
      expect(defs.resolve('deporte', 'golf')!.map((b) => b.id), ['a', 'c']);
      final muchos = ScreenDefinitions.fromJson({
        'deporte': {
          '*': [for (var i = 0; i < 25; i++) aviso('av$i', {'es': 'x'}), sec('tarde', 'partidos')],
        },
      });
      expect(muchos, isNull, reason: 'la sección quedó más allá del bloque 20: sin secciones visibles');
    });

    test('una lista sin secciones visibles equivale a no tener definición', () {
      expect(
        ScreenDefinitions.fromJson({
          'deporte': {
            '*': [sec('a', 'partidos', visible: false), aviso('av', {'es': 'x'})],
          },
        }),
        isNull,
      );
      // Una lista inservible no tapa a la de «*».
      final defs = ScreenDefinitions.fromJson({
        'deporte': {
          '*': [sec('a', 'partidos')],
          'golf': [sec('a', 'partidos', visible: false)],
        },
      })!;
      expect(defs.resolve('deporte', 'golf')!.single.section, 'partidos');
    });

    test('el catálogo trae las pantallas y el almacén las guarda en disco', () async {
      final body = {
        'version': 1,
        'deportes': [sport('golf', 1)],
        'pantallas': {
          'deporte': {
            '*': [sec('a', 'partidos')],
          },
        },
      };
      final disk = <String, String>{};
      final target = ValueNotifier<SportCatalog>(SportCatalog.builtIn);
      final store = SportCatalogStore(
        target: target,
        read: (k) async => disk[k],
        write: (k, v) async => disk[k] = v,
        fetch: ({required lang, etag}) async => SportCatalogReply(200, body: body, etag: 'e1'),
        loadFactory: () async => null,
        currentLang: () => 'es',
      );
      expect(await store.refresh(), isTrue);
      expect(target.value.screens!.resolve('deporte', 'golf'), isNotNull);

      // Reinicio sin red: el disco devuelve las pantallas.
      final again = ValueNotifier<SportCatalog>(SportCatalog.builtIn);
      await SportCatalogStore(
        target: again,
        read: (k) async => disk[k],
        write: (k, v) async => disk[k] = v,
        fetch: ({required lang, etag}) async => throw Exception('sin red'),
        loadFactory: () async => null,
      ).loadLocal();
      expect(again.value.screens!.resolve('deporte', 'golf'), isNotNull);
    });

    test('una respuesta inválida o sin deportes conserva el catálogo y sus pantallas', () async {
      final good = {
        'deportes': [sport('golf', 1)],
        'pantallas': {
          'deporte': {
            '*': [sec('a', 'partidos')],
          },
        },
      };
      final replies = <Object>[
        SportCatalogReply(200, body: good, etag: 'e1'),
        const SportCatalogReply(200, body: 'no es json de catálogo'),
        const SportCatalogReply(200, body: {'deportes': []}),
        const SportCatalogReply(500),
        Exception('sin red'),
      ];
      final target = ValueNotifier<SportCatalog>(SportCatalog.builtIn);
      final store = SportCatalogStore(
        target: target,
        read: (k) async => null,
        write: (k, v) async {},
        fetch: ({required lang, etag}) async {
          final next = replies.removeAt(0);
          if (next is Exception) throw next;
          return next as SportCatalogReply;
        },
        loadFactory: () async => null,
      );
      expect(await store.refresh(), isTrue);
      final kept = target.value;
      for (var i = 0; i < 4; i++) {
        expect(await store.refresh(), isFalse);
        expect(identical(target.value, kept), isTrue);
      }
      expect(target.value.screens, isNotNull);
    });

    test('si el servidor deja de publicar pantallas, se vuelve al orden de hoy', () async {
      final target = ValueNotifier<SportCatalog>(SportCatalog.builtIn);
      final replies = [
        {
          'deportes': [sport('golf', 1)],
          'pantallas': {
            'deporte': {
              '*': [sec('a', 'partidos')],
            },
          },
        },
        {
          'deportes': [sport('golf', 1)],
        },
      ];
      final store = SportCatalogStore(
        target: target,
        read: (k) async => null,
        write: (k, v) async {},
        fetch: ({required lang, etag}) async => SportCatalogReply(200, body: replies.removeAt(0)),
        loadFactory: () async => null,
      );
      await store.refresh();
      expect(target.value.screens, isNotNull);
      expect(await store.refresh(), isTrue);
      expect(target.value.screens, isNull);
    });
  });

  group('avisos', () {
    ScreenBlock block(Map<String, Object?> raw) =>
        ScreenDefinitions.fromJson({
          'deporte': {
            '*': [raw, sec('s', 'partidos')],
          },
        })!.resolve('deporte', 'golf')!.first;

    test('texto en el idioma pedido y caída a español', () {
      final b = block(aviso('av', {'es': 'Hola', 'en': 'Hello', 'de': '  '}));
      expect(noticeData(b, 'en')!.text, 'Hello');
      expect(noticeData(b, 'de')!.text, 'Hola', reason: 'alemán vacío → español');
      expect(noticeData(b, 'fr')!.text, 'Hola');
    });

    test('tono desconocido es info y el enlace debe ser una ruta relativa', () {
      expect(noticeData(block(aviso('av', {'es': 'x'}, tono: 'peligro')), 'es')!.tone, 'peligro');
      expect(noticeData(block(aviso('av', {'es': 'x'}, tono: 'neon')), 'es')!.tone, 'info');
      expect(noticeData(block(aviso('av', {'es': 'x'}, enlace: '/planes/')), 'es')!.link, '/planes/');
      expect(noticeData(block(aviso('av', {'es': 'x'}, enlace: 'https://malo.test')), 'es')!.link, isNull);
      expect(noticeData(block(aviso('av', {'es': 'x'}, enlace: '//malo.test')), 'es')!.link, isNull);
    });

    test('sin texto utilizable no hay aviso', () {
      expect(noticeData(block(aviso('av', {'en': 'Only English'})), 'de'), isNull);
    });
  });

  group('pantalla efectiva', () {
    test('sin definición: el orden de hoy; con ella, solo lo visible y lo que la pantalla sabe pintar', () {
      expect(
        effectiveScreen(null, 'deporte', 'golf', defaultSportSections, genericSportSections).map((b) => b.section),
        ['destacado', 'dias', 'resumen', 'partidos'],
      );
      final defs = ScreenDefinitions.fromJson({
        'partido': {
          '*': [sec('a', 'sello'), sec('b', 'h2h'), sec('c', 'cabecera', visible: false), sec('d', 'mercados'), aviso('av', {'es': 'x'})],
        },
      });
      final blocks = effectiveScreen(defs, 'partido', 'golf', defaultMatchSections, {'cabecera', 'pronostico', 'mercados', 'contenido', 'sello'});
      expect(blocks.map((b) => b.id), ['a', 'd', 'av'], reason: 'h2h se ignora en un deporte nuevo; cabecera oculta');
    });
  });
}
