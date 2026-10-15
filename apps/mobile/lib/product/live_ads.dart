import 'dart:async';
import 'dart:io' show Platform;

import 'package:google_mobile_ads/google_mobile_ads.dart';

import 'live_api.dart';

enum AdShow { earned, dismissed, failedToLoad }

/// Frontera con el SDK de anuncios: permite probar el flujo sin plugin ni red.
abstract class RewardedAdGateway {
  /// Consentimiento (UMP) e inicialización. `false` si no se pueden pedir anuncios.
  Future<bool> prepare();
  Future<AdShow> show({
    required String unitId,
    required String userId,
    required String customData,
  });
}

enum AdResult { credited, pending, dismissed, unavailable, limit, waiting }

class AdOutcome {
  const AdOutcome(this.result, [this.coins = 0]);
  final AdResult result;
  final int coins;
}

/// Pide ticket, muestra el anuncio y espera a que el SERVIDOR acredite. La app nunca
/// acredita ni elige el importe: la celebración sale de la diferencia de saldo.
class RewardedAdFlow {
  RewardedAdFlow({
    required this.api,
    required this.gateway,
    String? platform,
    this.pollEvery = const Duration(seconds: 2),
    this.pollFor = const Duration(seconds: 10),
    this.onVerifying,
  }) : platform = platform ?? (Platform.isIOS ? 'ios' : 'android');

  final QuantFutApi api;
  final RewardedAdGateway gateway;
  final String platform;
  final Duration pollEvery, pollFor;

  /// Se llama cuando el video terminó y se espera la confirmación del servidor.
  final void Function()? onVerifying;

  Future<num> _balance() async {
    final wallet = jsonMap(
      jsonMap(await api.request('/mobile/v1/rewards'))['wallet'],
    );
    return (wallet['balance'] as num?) ?? 0;
  }

  Future<void> _cancel(String nonce) async {
    try {
      await api.request('/mobile/v1/rewards/ads/cancel', body: {'nonce': nonce});
    } catch (_) {
      /* el ticket caduca solo a los 5 minutos */
    }
  }

  Future<AdOutcome> run() async {
    if (!await gateway.prepare()) return const AdOutcome(AdResult.unavailable);
    final before = await _balance();
    final JsonMap ticket;
    try {
      ticket = jsonMap(
        await api.request(
          '/mobile/v1/rewards/ads/ticket',
          body: {'platform': platform},
        ),
      );
    } on ApiFailure catch (e) {
      switch (e.code) {
        case 'limite_diario':
          return const AdOutcome(AdResult.limit);
        case 'anuncio_en_espera':
        case 'anuncio_en_curso':
          return const AdOutcome(AdResult.waiting);
      }
      rethrow;
    }
    final nonce = '${ticket['nonce']}';
    final AdShow shown;
    try {
      shown = await gateway.show(
        unitId: '${ticket['unit_id']}',
        userId: '${ticket['user_id']}',
        customData: nonce,
      );
    } catch (_) {
      await _cancel(nonce);
      return const AdOutcome(AdResult.unavailable);
    }
    if (shown != AdShow.earned) {
      await _cancel(nonce);
      return AdOutcome(
        shown == AdShow.failedToLoad
            ? AdResult.unavailable
            : AdResult.dismissed,
      );
    }
    onVerifying?.call();
    final deadline = DateTime.now().add(pollFor);
    while (true) {
      final now = await _balance();
      if (now > before) {
        return AdOutcome(AdResult.credited, (now - before).round());
      }
      if (!DateTime.now().isBefore(deadline)) {
        return const AdOutcome(AdResult.pending);
      }
      await Future<void>.delayed(pollEvery);
    }
  }
}

/// Implementación real con `google_mobile_ads` 9.x (firmas comprobadas en el paquete).
class AdMobGateway implements RewardedAdGateway {
  bool _ready = false;

  @override
  Future<bool> prepare() async {
    if (_ready) return true;
    final consent = Completer<void>();
    ConsentInformation.instance.requestConsentInfoUpdate(
      ConsentRequestParameters(),
      () async {
        await ConsentForm.loadAndShowConsentFormIfRequired((_) {});
        if (!consent.isCompleted) consent.complete();
      },
      (_) {
        if (!consent.isCompleted) consent.complete();
      },
    );
    await consent.future;
    if (!await ConsentInformation.instance.canRequestAds()) return false;
    await MobileAds.instance.initialize();
    return _ready = true;
  }

  @override
  Future<AdShow> show({
    required String unitId,
    required String userId,
    required String customData,
  }) async {
    final loaded = Completer<RewardedAd?>();
    RewardedAd.load(
      adUnitId: unitId,
      request: const AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: loaded.complete,
        onAdFailedToLoad: (_) => loaded.complete(null),
      ),
    );
    final ad = await loaded.future.timeout(
      const Duration(seconds: 20),
      onTimeout: () => null,
    );
    if (ad == null) return AdShow.failedToLoad;
    await ad.setServerSideOptions(
      ServerSideVerificationOptions(userId: userId, customData: customData),
    );
    var earned = false;
    final closed = Completer<void>();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (_) => closed.complete(),
      onAdFailedToShowFullScreenContent: (_, _) => closed.complete(),
    );
    await ad.show(onUserEarnedReward: (_, _) => earned = true);
    await closed.future;
    await ad.dispose();
    return earned ? AdShow.earned : AdShow.dismissed;
  }
}
