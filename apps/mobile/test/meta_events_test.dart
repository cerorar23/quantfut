import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/meta_events.dart';
import 'package:gobet/product/live_api.dart';

class FakeSink implements MetaSink {
  final calls = <String>[];
  final logs = <(String, Map<String, Object>, double?)>[];
  @override
  Future<void> start({required bool tracking}) async =>
      calls.add('start:$tracking');
  @override
  Future<void> stop() async => calls.add('stop');
  @override
  Future<void> identify(String externalId, String? email) async =>
      calls.add('identify:$externalId:$email');
  @override
  Future<void> forget() async => calls.add('forget');
  @override
  Future<void> log(
    String name,
    Map<String, Object> parameters, {
    double? valueToSum,
  }) async => logs.add((name, parameters, valueToSum));
  @override
  Future<String?> anonymousId() async => 'XZ1';
}

void main() {
  test(
    'Sin configurar (sin App ID) no arranca el SDK aunque el ajuste esté activo',
    () async {
      final sink = FakeSink();
      final meta = MetaEvents(sink, configured: false);
      await meta.apply(true);
      await meta.viewVip();
      expect(sink.calls, isEmpty);
      expect(sink.logs, isEmpty);
    },
  );

  test('Activo: arranca y registra eventos estándar con nombres de Meta', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.viewMatch('m-1');
    await meta.initiateCheckout('plus_1m', 4.99, 'USD');
    expect(sink.calls, ['start:true']);
    expect(sink.logs[0].$1, 'fb_mobile_content_view');
    expect(sink.logs[0].$2, {
      'fb_content_type': 'product',
      'fb_content_id': 'match:m-1',
    });
    expect(sink.logs[1].$1, 'fb_mobile_initiated_checkout');
    expect(sink.logs[1].$2['fb_currency'], 'USD');
    expect(sink.logs[1].$3, 4.99);
  });

  test('Desactivar para el SDK y deja de registrar', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.apply(false);
    await meta.search('barcelona');
    expect(sink.calls, ['start:true', 'stop']);
    expect(sink.logs, isEmpty);
  });

  test('La búsqueda se recorta a 100 caracteres', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.search('x' * 150);
    expect((sink.logs.single.$2['fb_search_string'] as String).length, 100);
  });

  test('Identificar usa el external_id del servidor, no el id de cuenta', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.identify({
      'account': {'account_id': 7, 'email': 'a@b.co'},
      'meta_external_id': 'abc123',
    });
    expect(sink.calls.last, 'identify:abc123:a@b.co');
  });

  test('extinfo tiene 16 posiciones en el orden de Meta', () {
    final values = extinfo(
      ios: false,
      package: 'com.saptain.quantfut',
      version: '1.0.0',
      build: '1',
      os: '14',
      model: 'Pixel 8',
      locale: 'es_CO',
      tzAbbr: 'COT',
      width: 1080,
      height: 2400,
      density: 2.75,
      cores: 8,
      tzName: 'America/Bogota',
    );
    expect(values.length, 16);
    expect(values[0], 'a2');
    expect(values[4], '14');
    expect(values[9], '1080');
    expect(values[15], 'America/Bogota');
  });

  test('Sin sesión no se manda el dispositivo', () async {
    final api = QuantFutApi(base: Uri.parse('https://example.invalid'));
    await api.syncMetaDevice();
    expect(api.signedIn, isFalse);
  });
}
