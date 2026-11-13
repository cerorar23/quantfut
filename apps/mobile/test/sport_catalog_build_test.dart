// El número de compilación viaja como `build` al pedir el catálogo (el servidor quita los bloques de pantalla con
// `build_min_app` mayor). Archivo aparte: usa un servidor local real, sin el enlace de pruebas de widgets.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/sport_catalog_store.dart';

void main() {
  test('el número de compilación viaja al pedir el catálogo y se omite si no se puede leer', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final queries = <Map<String, String>>[];
    server.listen((req) async {
      queries.add(req.uri.queryParameters);
      req.response.headers.contentType = ContentType.json;
      req.response.write(jsonEncode({'deportes': []}));
      await req.response.close();
    });
    final api = QuantFutApi(base: Uri.parse('http://127.0.0.1:${server.port}'));
    addTearDown(() async {
      api.dispose();
      await server.close(force: true);
    });
    await fetchSportCatalogFromApi(lang: 'pt', api: api, build: () async => 12);
    await fetchSportCatalogFromApi(lang: 'pt', api: api, build: () async => null);
    expect(queries[0], {'cliente': 'app', 'contrato': '1', 'lang': 'pt', 'build': '12'});
    expect(queries[1], {'cliente': 'app', 'contrato': '1', 'lang': 'pt'});
  });
}
