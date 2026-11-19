import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sport_images.dart';

class _Client404 implements HttpClient {
  @override
  dynamic noSuchMethod(Invocation i) {
    if (i.memberName == #getUrl || i.memberName == #openUrl) {
      return Future<HttpClientRequest>.value(_Req404());
    }
    return null;
  }
}

class _Req404 implements HttpClientRequest {
  @override
  final headers = _Headers();
  @override
  Future<HttpClientResponse> close() => Future.value(_Res404());
  @override
  Future<HttpClientResponse> get done => close();
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

class _Headers implements HttpHeaders {
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

class _Res404 extends Stream<List<int>> implements HttpClientResponse {
  @override
  int get statusCode => 404;
  @override
  int get contentLength => 0;
  @override
  HttpClientResponseCompressionState get compressionState =>
      HttpClientResponseCompressionState.notCompressed;
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => const Stream<List<int>>.empty().listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );
  @override
  dynamic noSuchMethod(Invocation i) => null;
}

void main() {
  test('manifiesto inválido da catálogo vacío', () {
    expect(ImageCatalog.fromManifest(null), same(ImageCatalog.empty));
    expect(ImageCatalog.fromManifest({'nba': []}), same(ImageCatalog.empty));
    expect(ImageCatalog.fromManifest({'tenis': 'x'}), same(ImageCatalog.empty));
  });

  test('tenis encuentra por nombre con tildes y mayúsculas', () {
    final c = ImageCatalog.fromManifest({
      'nba': {
        'LAL': {'f': 'LAL.png'},
      },
      'tenis': {
        'carlos alcaraz': {
          'f': 'carlos-alcaraz.jpg',
          'a': 'X',
          'l': 'CC BY-SA 4.0',
          'p': 'https://commons...',
        },
      },
    });
    final p = c.tennisPhoto('Carlos Alcaraz');
    expect(p?.path, '/web/imagenes/tenis/carlos-alcaraz.jpg');
    expect(p?.author, 'X');
    expect(p?.license, 'CC BY-SA 4.0');
    expect(c.tennisPhoto('CARLOS ALCARÁZ')?.author, 'X');
    expect(c.tennisPhoto('Jannik Sinner'), isNull);
    expect(c.nbaLogo('LAL'), '/web/imagenes/nba/LAL.png');
    expect(c.nbaLogo('XXX'), isNull);
  });

  test('normaliza como el servidor (NFD sin marcas, sin transliterar)', () {
    final pl = String.fromCharCodes([73, 103, 97, 32, 0x15a, 119, 105, 0x105, 116, 101, 107]);
    final dj = String.fromCharCodes([78, 111, 118, 97, 107, 32, 0x110, 111, 107, 111, 118, 105, 0x107]);
    final cz = String.fromCharCodes([80, 101, 116, 114, 97, 32, 75, 118, 105, 116, 111, 118, 0xe1]);
    final m = <String, dynamic>{
      'tenis': {
        'iga swiatek': {'f': 'iga.jpg'},
        // el servidor no transcribe la d cruzada: queda como esta en su clave
        'novak ${String.fromCharCode(0x111)}okovic': {'f': 'nd.jpg'},
        'petra kvitova': {'f': 'pk.jpg'},
      },
    };
    final cat = ImageCatalog.fromManifest(m);
    expect(cat.tennisPhoto(pl)?.path, '/web/imagenes/tenis/iga.jpg');
    expect(cat.tennisPhoto(dj)?.path, '/web/imagenes/tenis/nd.jpg');
    expect(cat.tennisPhoto(cz)?.path, '/web/imagenes/tenis/pk.jpg');
    expect(cat.tennisPhoto('Novak Djokovic'), isNull);
  });

  test('preferencia de bloque tenis_sofascore sobre tenis clásico', () {
    final c = ImageCatalog.fromManifest({
      'tenis': {
        'carlos alcaraz': {
          'f': 'carlos-alcaraz-wiki.jpg',
          'a': 'Wiki Author',
          'l': 'CC BY-SA 4.0',
        },
        'jannik sinner': {
          'f': 'sinner-wiki.jpg',
          'a': 'Wiki Sinner',
        },
      },
      'tenis_sofascore': {
        'carlos alcaraz': {
          'id': 275923,
          'f': 'carlos-alcaraz.webp',
          'pais': 'ESP',
          'genero': 'M',
          'ranking': 3,
        },
      },
    });

    // Alcaraz tiene ambos bloques: debe preferir sofascore
    final alcaraz = c.tennisPhoto('Carlos Alcaraz');
    expect(alcaraz?.path, '/web/imagenes/tenis/carlos-alcaraz.webp');
    expect(alcaraz?.id, 275923);
    expect(alcaraz?.country, 'ESP');

    // Sinner solo está en wiki: fallback al bloque tenis
    final sinner = c.tennisPhoto('Jannik Sinner');
    expect(sinner?.path, '/web/imagenes/tenis/sinner-wiki.jpg');
  });

  test('nombre invertido (Alcaraz Carlos, Alcaraz, Carlos, De Minaur Alex)', () {
    final c = ImageCatalog.fromManifest({
      'tenis': {
        'carlos alcaraz': {'f': 'alcaraz.jpg'},
        'alex de minaur': {'f': 'de-minaur.jpg'},
      },
    });

    // Nombre invertido simple
    expect(c.tennisPhoto('Alcaraz Carlos')?.path, '/web/imagenes/tenis/alcaraz.jpg');
    // Nombre invertido con coma
    expect(c.tennisPhoto('Alcaraz, Carlos')?.path, '/web/imagenes/tenis/alcaraz.jpg');
    // Nombre compuesto invertido
    expect(c.tennisPhoto('De Minaur Alex')?.path, '/web/imagenes/tenis/de-minaur.jpg');
    expect(c.tennisPhoto('De Minaur, Alex')?.path, '/web/imagenes/tenis/de-minaur.jpg');
  });

  test('duplicados en tenis_sofascore (Coleman Wong) devuelven null (iniciales)', () {
    final c = ImageCatalog.fromManifest({
      'tenis': {
        // En wiki pudiera existir una entrada antigua, pero sofascore detecta duplicado
        'coleman wong': {'f': 'wong-wiki.jpg'},
      },
      'tenis_sofascore': {
        'coleman wong': [
          {'id': 289106, 'f': 'coleman-1.webp'},
          {'id': 406729, 'f': 'coleman-2.webp'},
        ],
      },
    });

    // Nunca mostrar la foto de otra persona si hay duplicado -> iniciales (null)
    expect(c.tennisPhoto('Coleman Wong'), isNull);
    expect(c.tennisPhoto('Wong Coleman'), isNull);
  });

  test('sin foto en catálogo (Ruien Zhang) devuelve null para iniciales', () {
    final c = ImageCatalog.fromManifest({
      'tenis': {
        'carlos alcaraz': {'f': 'alcaraz.jpg'},
      },
    });

    expect(c.tennisPhoto('Ruien Zhang'), isNull);
  });

  test('serverImageUrl y archivos inseguros', () {
    final api = QuantFutApi(base: Uri.parse('https://x.test'));
    expect(serverImageUrl(api, null), isNull);
    expect(serverImageUrl(api, ''), isNull);
    expect(
      serverImageUrl(api, '/web/imagenes/nba/NYK.png'),
      'https://x.test/web/imagenes/nba/NYK.png',
    );
    expect(
      ImageCatalog.fromManifest({
        'tenis': {'a b': {'f': '..'}, 'c d': {'f': '.'}},
      }),
      same(ImageCatalog.empty),
    );
  });

  test('id NBA inválido no produce URL', () {
    expect(nbaPlayerPhoto('0'), '');
    expect(nbaPlayerPhoto('../x'), '');
    expect(nbaPlayerPhoto('2544'), '/web/imagenes/jugadores/nba/2544.png');
  });

  testWidgets('persona: círculo con aro cian 2 dp y tipografía Rajdhani 700 cian en iniciales', (t) async {
    await t.pumpWidget(
      const MaterialApp(
        home: QfAvatar(
          name: 'Carlos Alcaraz',
          kind: QfAvatarKind.person,
          size: 40,
        ),
      ),
    );

    expect(find.text('CA'), findsOneWidget);
    final text = t.widget<Text>(find.text('CA'));
    expect(text.style?.fontFamily, qfTitleFont);
    expect(text.style?.fontWeight, FontWeight.w700);
    expect(text.style?.color, QfColors.cyan);

    // Contenedor circular con aro cian
    final containers = t.widgetList<Container>(find.byType(Container));
    final circle = containers.firstWhere((c) =>
        c.decoration is BoxDecoration &&
        (c.decoration as BoxDecoration).shape == BoxShape.circle);
    final deco = circle.decoration as BoxDecoration;
    expect(deco.shape, BoxShape.circle);
    expect(deco.border, isNotNull);
    expect((deco.border as Border).top.color, QfColors.cyan);
    expect((deco.border as Border).top.width, 2.0);
  });

  testWidgets('logo: cuadrado con padding y tipografía mono en iniciales sin aro', (t) async {
    await t.pumpWidget(
      const MaterialApp(
        home: QfAvatar(
          name: 'Real Madrid',
          kind: QfAvatarKind.logo,
          size: 40,
        ),
      ),
    );

    expect(find.text('RM'), findsOneWidget);
    final text = t.widget<Text>(find.text('RM'));
    expect(text.style?.fontFamily, qfMono);
    expect(text.style?.color, QfColors.text2);

    // Contenedor de logo no tiene shape circle ni borde
    final containers = t.widgetList<Container>(find.byType(Container));
    for (final c in containers) {
      if (c.decoration is BoxDecoration) {
        final deco = c.decoration as BoxDecoration;
        expect(deco.shape, BoxShape.rectangle);
        expect(deco.border, isNull);
      }
    }
  });

  testWidgets('imagen que falla muestra iniciales, no icono roto', (t) async {
    await HttpOverrides.runZoned(() async {
      await t.pumpWidget(
        const MaterialApp(
          home: QfAvatar(
            url: 'https://x.test/no-existe.png',
            name: 'Jannik Sinner',
            countryCode: 'ITA',
          ),
        ),
      );
      await t.pump();
      await t.pump(const Duration(milliseconds: 50));
      expect(find.text('JS'), findsOneWidget);
      expect(find.byIcon(Icons.broken_image), findsNothing);
      expect(find.byKey(const ValueKey('qf-flag-ITA')), findsOneWidget);
    }, createHttpClient: (c) => _Client404());
  });

  testWidgets('sin url muestra iniciales; código desconocido sin bandera', (
    t,
  ) async {
    await t.pumpWidget(
      const MaterialApp(
        home: Column(
          children: [
            QfAvatar(name: 'Boston Celtics', countryCode: 'ZZZ'),
            QfAvatar(name: 'Dane', countryCode: 'DEN'),
          ],
        ),
      ),
    );
    expect(find.byKey(const ValueKey('qf-flag-DEN')), findsNothing);
    expect(find.text('BC'), findsOneWidget);
    expect(find.byKey(const ValueKey('qf-flag-ZZZ')), findsNothing);
  });
}
