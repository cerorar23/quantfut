// El GET condicional del catálogo contra un servidor local real: ETag, 304 y estados de error.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';

void main() {
  late HttpServer server;
  late QuantFutApi api;
  final seen = <HttpRequest>[];
  var status = 200;

  setUp(() async {
    seen.clear();
    status = 200;
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    api = QuantFutApi(base: Uri.parse('http://127.0.0.1:${server.port}'));
    server.listen((req) async {
      seen.add(req);
      if (status == 200 && req.headers.value(HttpHeaders.ifNoneMatchHeader) == 'W/"v1"') status = 304;
      req.response.statusCode = status;
      if (status == 200) {
        req.response.headers.set(HttpHeaders.etagHeader, 'W/"v1"');
        req.response.headers.contentType = ContentType.json;
        req.response.write(
          jsonEncode({
            'deportes': [
              {'id': 'golf', 'orden': 1, 'estado': 'on', 'nombre': {'es': 'Golf'}, 'icono': 'golf', 'color': '#00ff00', 'secciones': ['high']},
            ],
          }),
        );
      }
      await req.response.close();
    });
  });

  tearDown(() async {
    api.dispose();
    await server.close(force: true);
  });

  test('200 trae cuerpo y ETag; con If-None-Match llega 304', () async {
    final first = await api.requestConditional('/cliente/v1/config', query: {'cliente': 'app', 'contrato': 1, 'lang': 'es'});
    expect(first.status, 200);
    expect(first.etag, 'W/"v1"');
    expect((first.data as Map)['deportes'], hasLength(1));
    expect(seen.single.uri.queryParameters, {'cliente': 'app', 'contrato': '1', 'lang': 'es'});

    final second = await api.requestConditional('/cliente/v1/config', etag: first.etag);
    expect(second.status, 304);
    expect(second.etag, 'W/"v1"');
    expect(seen.last.headers.value(HttpHeaders.ifNoneMatchHeader), 'W/"v1"');
  });

  test('un 500 lanza y el almacén lo trata como «sin novedades»', () async {
    status = 500;
    await expectLater(api.requestConditional('/cliente/v1/config'), throwsA(isA<ApiFailure>()));
  });
}
