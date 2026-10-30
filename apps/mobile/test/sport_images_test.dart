import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/sport_images.dart';

class _Http404 extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) => _Client404();
}

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

  test('id NBA inválido no produce URL', () {
    expect(nbaPlayerPhoto('0'), '');
    expect(nbaPlayerPhoto('../x'), '');
    expect(nbaPlayerPhoto('2544'), '/web/imagenes/jugadores/nba/2544.png');
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
        home: QfAvatar(name: 'Boston Celtics', countryCode: 'ZZZ'),
      ),
    );
    expect(find.text('BC'), findsOneWidget);
    expect(find.byKey(const ValueKey('qf-flag-ZZZ')), findsNothing);
  });
}
