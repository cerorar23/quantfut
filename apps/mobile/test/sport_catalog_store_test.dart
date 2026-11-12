// Carga del catálogo de deportes: red → disco → copia de fábrica, ETag y tolerancia a respuestas malas.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/sport_catalog_store.dart';
import 'package:gobet/product/sports.dart';

Map<String, Object?> sport(String id, int orden, {String estado = 'on', Map<String, Object?>? nombre, String icono = 'generico'}) => {
  'id': id,
  'orden': orden,
  'estado': estado,
  'nombre': nombre ?? {'es': id, 'en': id},
  'icono': icono,
  'color': '#123456',
  'secciones': ['high'],
  'familias': <Object?>[],
};

class Harness {
  Harness({this.lang = 'es'}) {
    store = SportCatalogStore(
      target: target,
      read: (k) async => disk[k],
      write: (k, v) async => disk[k] = v,
      fetch: ({required lang, etag}) async {
        calls.add((lang: lang, etag: etag));
        final next = replies.removeAt(0);
        if (next is Exception) throw next;
        return next as SportCatalogReply;
      },
      currentLang: () => lang,
    );
  }

  String lang;
  final target = ValueNotifier<SportCatalog>(SportCatalog.builtIn);
  final disk = <String, String>{};
  final calls = <({String lang, String? etag})>[];
  final replies = <Object>[];
  late final SportCatalogStore store;
}

SportCatalogReply ok(List<Map<String, Object?>> sports, {String? etag}) =>
    SportCatalogReply(200, body: {'version': 1, 'deportes': sports}, etag: etag);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('sin red ni disco: la copia de fábrica con los tres deportes', () async {
    final h = Harness()..replies.add(Exception('sin red'));
    await h.store.loadLocal();
    expect(h.target.value.ids, [kFootball, kNba, kTennis]);
    expect(await h.store.refresh(), isFalse);
    expect(h.target.value.ids, [kFootball, kNba, kTennis]);
    expect(h.disk, isEmpty);
  });

  test('con respuesta de red válida: manda el orden y los nombres del servidor, y se guarda', () async {
    final h = Harness()
      ..replies.add(
        ok([
          sport('tenis', 1, nombre: {'es': 'Tenis!', 'en': 'Tennis!'}),
          sport('futbol', 2),
        ], etag: 'W/"a"'),
      );
    await h.store.loadLocal();
    expect(await h.store.refresh(), isTrue);
    expect(h.target.value.ids, ['tenis', 'futbol']);
    expect(h.target.value.spec('tenis').names['en'], 'Tennis!');
    expect(h.disk[SportCatalogStore.etagKey], 'W/"a"');
    expect(h.disk[SportCatalogStore.langKey], 'es');
    expect(h.calls.single.etag, isNull);
  });

  test('el siguiente arranque usa lo guardado sin red y revalida con If-None-Match; 304 no cambia nada', () async {
    final first = Harness()..replies.add(ok([sport('nba', 1), sport('futbol', 2)], etag: 'W/"b"'));
    await first.store.loadLocal();
    await first.store.refresh();

    // «Otro arranque»: mismo disco, catálogo nuevo en memoria.
    final second = Harness()
      ..disk.addAll(first.disk)
      ..replies.add(const SportCatalogReply(304, etag: 'W/"b"'));
    await second.store.loadLocal();
    expect(second.target.value.ids, ['nba', 'futbol'], reason: 'disco antes que fábrica, sin esperar a la red');
    var notified = 0;
    second.target.addListener(() => notified++);
    expect(await second.store.refresh(), isFalse);
    expect(second.calls.single.etag, 'W/"b"');
    expect(second.target.value.ids, ['nba', 'futbol']);
    expect(notified, 0);
  });

  test('el ETag guardado de otro idioma no se envía', () async {
    final first = Harness()..replies.add(ok([sport('nba', 1)], etag: 'W/"es"'));
    await first.store.loadLocal();
    await first.store.refresh();
    final second = Harness(lang: 'de')
      ..disk.addAll(first.disk)
      ..replies.add(ok([sport('nba', 1)], etag: 'W/"de"'));
    await second.store.loadLocal();
    await second.store.refresh();
    expect(second.calls.single.etag, isNull);
    expect(second.calls.single.lang, 'de');
  });

  test('si la red trae lo mismo no se vuelve a avisar a las pantallas', () async {
    final h = Harness()..replies.addAll([ok([sport('nba', 1)], etag: '1'), ok([sport('nba', 1)], etag: '2')]);
    await h.store.loadLocal();
    expect(await h.store.refresh(), isTrue);
    expect(await h.store.refresh(), isFalse);
    expect(h.calls.last.etag, '1');
    expect(h.disk[SportCatalogStore.etagKey], '2');
  });

  for (final (name, bad) in <(String, Object)>[
    ('sin deportes', const SportCatalogReply(200, body: {'version': 1})),
    ('con la lista vacía', const SportCatalogReply(200, body: {'deportes': []})),
    ('con todo apagado o raro', SportCatalogReply(200, body: {'deportes': [sport('golf', 1, estado: 'off'), sport('x', 2, estado: 'zzz')]})),
    ('que no es un mapa', const SportCatalogReply(200, body: [1, 2])),
    ('sin cuerpo', const SportCatalogReply(200)),
    ('con un estado inesperado', const SportCatalogReply(500)),
    ('que falla', Exception('boom')),
  ]) {
    test('respuesta $name: se conserva lo anterior y no se guarda', () async {
      final h = Harness()..replies.addAll([ok([sport('nba', 1), sport('tenis', 2)], etag: 'W/"ok"'), bad]);
      await h.store.loadLocal();
      await h.store.refresh();
      final saved = Map.of(h.disk);
      expect(await h.store.refresh(), isFalse);
      expect(h.target.value.ids, ['nba', 'tenis']);
      expect(h.disk, saved);
    });
  }

  test('respuesta mala en el primer arranque: se queda con la copia de fábrica, nunca sin deportes', () async {
    final h = Harness()..replies.add(const SportCatalogReply(200, body: {'deportes': []}));
    await h.store.loadLocal();
    await h.store.refresh();
    expect(h.target.value.sports, isNotEmpty);
    expect(h.target.value.ids, [kFootball, kNba, kTennis]);
  });

  test('disco ilegible o sin deportes: se ignora y vale la copia de fábrica', () async {
    for (final junk in ['no es json', '{"deportes": []}', '[]', '']) {
      final h = Harness()..disk[SportCatalogStore.bodyKey] = junk;
      await h.store.loadLocal();
      expect(h.target.value.ids, [kFootball, kNba, kTennis], reason: junk);
    }
  });

  test('NBA apagada en el catálogo: sale del catálogo pero no se rompe nada', () async {
    final h = Harness()..replies.add(ok([sport('futbol', 1), sport('tenis', 2)], etag: 'x'));
    await h.store.loadLocal();
    await h.store.refresh();
    expect(h.target.value.ids, ['futbol', 'tenis']);
    expect(h.target.value.contains(kNba), isFalse);
    expect(h.target.value.spec(kNba).icon, sportIcons['generico'], reason: 'un id suelto recibe la especificación genérica');
  });

  test('una respuesta con un deporte nuevo (golf, icono desconocido) se muestra con icono genérico', () async {
    final h = Harness()
      ..replies.add(
        ok([
          sport('futbol', 1),
          sport('golf', 2, icono: 'golf_2031', estado: 'preview', nombre: {'es': 'Golf', 'en': 'Golf'}),
        ]),
      );
    await h.store.loadLocal();
    await h.store.refresh();
    final golf = h.target.value.spec('golf');
    expect(golf.icon, sportIcons['generico']);
    expect(golf.isBeta, isTrue);
    expect(golf.accent, const Color(0xff123456));
  });
}
