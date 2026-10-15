// Flujo del video con recompensa: ticket → SDK → espera del saldo, sin red ni plugin.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_ads.dart';
import 'package:gobet/product/live_api.dart';

class _Api extends QuantFutApi {
  _Api({this.balances = const [0, 10], this.ticketError});
  final List<num> balances;
  final ApiFailure? ticketError;
  final calls = <String>[];
  int _i = 0;

  @override
  bool get signedIn => true;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add(path);
    if (path == '/mobile/v1/rewards/ads/ticket') {
      if (ticketError != null) throw ticketError!;
      return {'user_id': 'u1', 'nonce': 'n1', 'unit_id': 'unit', 'expires_at': 'x'};
    }
    if (path == '/mobile/v1/rewards/ads/cancel') return {'cancelled': true};
    final b = balances[_i < balances.length ? _i : balances.length - 1];
    _i++;
    return {
      'wallet': {'balance': b},
    };
  }
}

class _Gateway implements RewardedAdGateway {
  _Gateway(this.result, {this.ready = true});
  final AdShow result;
  final bool ready;
  Map<String, String>? shown;

  @override
  Future<bool> prepare() async => ready;

  @override
  Future<AdShow> show({
    required String unitId,
    required String userId,
    required String customData,
  }) async {
    shown = {'unit': unitId, 'user': userId, 'custom': customData};
    return result;
  }
}

RewardedAdFlow _flow(
  _Api api,
  _Gateway gw, {
  Duration? pollFor,
  void Function()? onVerifying,
}) => RewardedAdFlow(
  api: api,
  gateway: gw,
  platform: 'android',
  pollEvery: Duration.zero,
  pollFor: pollFor ?? const Duration(seconds: 1),
  onVerifying: onVerifying,
);

void main() {
  test('video completo: pasa uid y nonce al SDK y celebra por diferencia de saldo', () async {
    final api = _Api(balances: [100, 100, 110]);
    final gw = _Gateway(AdShow.earned);
    final out = await _flow(api, gw).run();
    expect(out.result, AdResult.credited);
    expect(out.coins, 10);
    expect(gw.shown, {'unit': 'unit', 'user': 'u1', 'custom': 'n1'});
    expect(api.calls, isNot(contains('/mobile/v1/rewards/ads/cancel')));
  });

  test('avisa de que está verificando solo cuando el video se completó', () async {
    var avisos = 0;
    await _flow(
      _Api(balances: [0, 10]),
      _Gateway(AdShow.earned),
      onVerifying: () => avisos++,
    ).run();
    expect(avisos, 1);
    await _flow(_Api(), _Gateway(AdShow.dismissed), onVerifying: () => avisos++).run();
    expect(avisos, 1);
  });

  test('cerrar antes de tiempo cancela el ticket y no celebra', () async {
    final api = _Api();
    final out = await _flow(api, _Gateway(AdShow.dismissed)).run();
    expect(out.result, AdResult.dismissed);
    expect(api.calls, contains('/mobile/v1/rewards/ads/cancel'));
  });

  test('si el anuncio no carga se cancela el ticket', () async {
    final api = _Api();
    final out = await _flow(api, _Gateway(AdShow.failedToLoad)).run();
    expect(out.result, AdResult.unavailable);
    expect(api.calls, contains('/mobile/v1/rewards/ads/cancel'));
  });

  test('sin consentimiento o SDK no se pide ticket', () async {
    final api = _Api();
    final out = await _flow(api, _Gateway(AdShow.earned, ready: false)).run();
    expect(out.result, AdResult.unavailable);
    expect(api.calls, isEmpty);
  });

  test('tope diario y pausa vienen del servidor', () async {
    Future<AdResult> con(String code) async => (await _flow(
      _Api(ticketError: ApiFailure('x', 409, code)),
      _Gateway(AdShow.earned),
    ).run()).result;
    expect(await con('limite_diario'), AdResult.limit);
    expect(await con('anuncio_en_espera'), AdResult.waiting);
    expect(await con('anuncio_en_curso'), AdResult.waiting);
  });

  test('otro error del servidor se propaga', () async {
    expect(
      _flow(_Api(ticketError: const ApiFailure('x', 500)), _Gateway(AdShow.earned)).run(),
      throwsA(isA<ApiFailure>()),
    );
  });

  test('si el saldo no sube en el plazo queda pendiente, sin cancelar', () async {
    final api = _Api(balances: [50]);
    final out = await _flow(
      api,
      _Gateway(AdShow.earned),
      pollFor: const Duration(milliseconds: 30),
    ).run();
    expect(out.result, AdResult.pending);
    expect(api.calls, isNot(contains('/mobile/v1/rewards/ads/cancel')));
  });
}
